import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.core.config import PROJECT_ROOT, settings
from app.data.loader import dataset_loader
from app.data.profiler import dataset_profiler
from app.schemas.dataset import (
    DatasetDeleteResponse,
    DatasetListItem,
    DatasetProfile,
    DatasetUploadResponse,
)


class DatasetManagerError(RuntimeError):
    """
    数据集保存、查询或删除失败时抛出的异常。
    """


class DatasetNotFoundError(DatasetManagerError):
    """
    指定dataset_id不存在。
    """


class DatasetManager:
    """
    DataPilot数据集管理器。

    负责：
    1. 保存用户上传的CSV和Excel
    2. 为数据集生成唯一ID
    3. 检测重复文件
    4. 生成并保存数据画像
    5. 查询数据集列表
    6. 根据dataset_id查找文件
    7. 删除数据集
    """

    def __init__(
        self,
        database_path: str | Path | None = None,
    ) -> None:
        if database_path is None:
            database_path = (
                PROJECT_ROOT
                / "data"
                / "database"
                / "datapilot.db"
            )

        self.database_path = Path(
            database_path
        ).resolve()

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        settings.upload_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._initialize_database()

    def _connect(self) -> sqlite3.Connection:
        """
        创建SQLite数据库连接。
        """

        connection = sqlite3.connect(
            self.database_path
        )

        connection.row_factory = sqlite3.Row

        return connection

    def _initialize_database(self) -> None:
        """
        创建数据集元信息表。
        """

        sql = """
        CREATE TABLE IF NOT EXISTS datasets (
            dataset_id TEXT PRIMARY KEY,
            original_name TEXT NOT NULL,
            stored_path TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_size_bytes INTEGER NOT NULL,
            file_hash TEXT NOT NULL UNIQUE,
            row_count INTEGER NOT NULL,
            column_count INTEGER NOT NULL,
            profile_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """

        with self._connect() as connection:
            connection.execute(sql)
            connection.commit()

    def save_dataset(
        self,
        original_name: str,
        content: bytes,
    ) -> DatasetUploadResponse:
        """
        保存上传文件，并写入数据集元信息。
        """

        safe_name = self._sanitize_filename(
            original_name
        )

        extension = Path(
            safe_name
        ).suffix.lower()

        if (
            extension
            not in dataset_loader.supported_extensions
        ):
            supported = ", ".join(
                sorted(
                    dataset_loader
                    .supported_extensions
                )
            )

            raise DatasetManagerError(
                f"不支持{extension or '未知'}格式，"
                f"仅支持：{supported}"
            )

        if not content:
            raise DatasetManagerError(
                "上传文件内容为空"
            )

        file_size_bytes = len(content)

        file_size_mb = (
            file_size_bytes / (1024 * 1024)
        )

        if (
            file_size_mb
            > settings.max_upload_size_mb
        ):
            raise DatasetManagerError(
                f"文件大小为{file_size_mb:.2f}MB，"
                f"超过"
                f"{settings.max_upload_size_mb}MB限制"
            )

        file_hash = hashlib.sha256(
            content
        ).hexdigest()

        existing_dataset = (
            self._get_by_hash(file_hash)
        )

        if existing_dataset is not None:
            profile = (
                DatasetProfile
                .model_validate_json(
                    existing_dataset[
                        "profile_json"
                    ]
                )
            )

            return DatasetUploadResponse(
                dataset_id=existing_dataset[
                    "dataset_id"
                ],
                file_name=existing_dataset[
                    "original_name"
                ],
                file_type=existing_dataset[
                    "file_type"
                ],
                file_size_bytes=existing_dataset[
                    "file_size_bytes"
                ],
                message=(
                    "相同文件已经上传，"
                    "已返回现有数据集"
                ),
                profile=profile,
            )

        dataset_id = (
            f"dataset-{uuid4().hex}"
        )

        stored_name = (
            f"{dataset_id}{extension}"
        )

        final_path = (
            settings.upload_path
            / stored_name
        )

        temporary_path = (
            settings.upload_path
            / f"{dataset_id}.tmp{extension}"
        )

        try:
            temporary_path.write_bytes(
                content
            )

            dataframe = dataset_loader.load(
                temporary_path
            )

            profile_dict = (
                dataset_profiler.profile(
                    dataframe=dataframe,
                    dataset_name=safe_name,
                )
            )

            profile = (
                DatasetProfile.model_validate(
                    profile_dict
                )
            )

            temporary_path.replace(
                final_path
            )

            relative_path = (
                final_path
                .relative_to(PROJECT_ROOT)
                .as_posix()
            )

            created_at = datetime.now(
                timezone.utc
            ).isoformat()

            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO datasets (
                        dataset_id,
                        original_name,
                        stored_path,
                        file_type,
                        file_size_bytes,
                        file_hash,
                        row_count,
                        column_count,
                        profile_json,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        dataset_id,
                        safe_name,
                        relative_path,
                        extension,
                        file_size_bytes,
                        file_hash,
                        profile.row_count,
                        profile.column_count,
                        profile.model_dump_json(),
                        created_at,
                    ),
                )

                connection.commit()

        except Exception:
            temporary_path.unlink(
                missing_ok=True
            )

            final_path.unlink(
                missing_ok=True
            )

            raise

        return DatasetUploadResponse(
            dataset_id=dataset_id,
            file_name=safe_name,
            file_type=extension,
            file_size_bytes=file_size_bytes,
            message=(
                "数据集上传并解析成功"
            ),
            profile=profile,
        )

    def list_datasets(
        self,
    ) -> list[DatasetListItem]:
        """
        查询所有已上传的数据集。
        """

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    dataset_id,
                    original_name,
                    file_type,
                    file_size_bytes,
                    row_count,
                    column_count
                FROM datasets
                ORDER BY created_at DESC
                """
            ).fetchall()

        return [
            DatasetListItem(
                dataset_id=row["dataset_id"],
                file_name=row["original_name"],
                file_type=row["file_type"],
                file_size_bytes=(
                    row["file_size_bytes"]
                ),
                row_count=row["row_count"],
                column_count=row["column_count"],
            )
            for row in rows
        ]

    def get_dataset_path(
        self,
        dataset_id: str,
    ) -> Path:
        """
        根据dataset_id获取真实文件路径。
        """

        row = self._get_dataset_row(
            dataset_id
        )

        stored_path = Path(
            row["stored_path"]
        )

        if not stored_path.is_absolute():
            stored_path = (
                PROJECT_ROOT / stored_path
            )

        resolved_path = stored_path.resolve()

        if not resolved_path.exists():
            raise DatasetManagerError(
                f"数据集记录存在，但文件已丢失："
                f"{dataset_id}"
            )

        return resolved_path

    def get_dataset_profile(
        self,
        dataset_id: str,
    ) -> DatasetProfile:
        """
        查询指定数据集的数据画像。
        """

        row = self._get_dataset_row(
            dataset_id
        )

        return DatasetProfile.model_validate_json(
            row["profile_json"]
        )

    def delete_dataset(
        self,
        dataset_id: str,
    ) -> DatasetDeleteResponse:
        """
        删除数据集文件和SQLite元信息。
        """

        row = self._get_dataset_row(
            dataset_id
        )

        stored_path = Path(
            row["stored_path"]
        )

        if not stored_path.is_absolute():
            stored_path = (
                PROJECT_ROOT / stored_path
            )

        stored_path = stored_path.resolve()

        with self._connect() as connection:
            connection.execute(
                """
                DELETE FROM datasets
                WHERE dataset_id = ?
                """,
                (dataset_id,),
            )

            connection.commit()

        stored_path.unlink(
            missing_ok=True
        )

        return DatasetDeleteResponse(
            dataset_id=dataset_id,
            deleted=True,
            message="数据集删除成功",
        )

    def _get_dataset_row(
        self,
        dataset_id: str,
    ) -> sqlite3.Row:
        """
        查询指定数据集的数据库记录。
        """

        cleaned_dataset_id = (
            dataset_id.strip()
        )

        if not cleaned_dataset_id:
            raise DatasetManagerError(
                "dataset_id不能为空"
            )

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM datasets
                WHERE dataset_id = ?
                """,
                (
                    cleaned_dataset_id,
                ),
            ).fetchone()

        if row is None:
            raise DatasetNotFoundError(
                f"数据集不存在："
                f"{cleaned_dataset_id}"
            )

        return row

    def _get_by_hash(
        self,
        file_hash: str,
    ) -> sqlite3.Row | None:
        """
        根据SHA-256查询重复文件。
        """

        with self._connect() as connection:
            return connection.execute(
                """
                SELECT *
                FROM datasets
                WHERE file_hash = ?
                """,
                (file_hash,),
            ).fetchone()

    @staticmethod
    def _sanitize_filename(
        filename: str,
    ) -> str:
        """
        清理用户上传的文件名。
        """

        safe_name = Path(
            filename
        ).name.strip()

        if not safe_name:
            raise DatasetManagerError(
                "上传文件名不能为空"
            )

        if len(safe_name) > 255:
            raise DatasetManagerError(
                "文件名长度不能超过255个字符"
            )

        return safe_name


dataset_manager = DatasetManager()