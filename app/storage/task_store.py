import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import PROJECT_ROOT
from app.schemas.analysis import AnalysisResponse


class TaskStoreError(RuntimeError):
    """
    分析任务存储失败时抛出的异常。
    """


class TaskNotFoundError(TaskStoreError):
    """
    指定task_id不存在。
    """


class AnalysisTaskStore:
    """
    DataPilot分析任务存储器。

    负责：
    1. 创建SQLite任务表
    2. 保存完整AnalysisResponse
    3. 查询历史任务列表
    4. 查询指定任务详情
    5. 删除指定历史任务
    """

    def __init__(
        self,
        database_path: str | Path | None = None,
    ) -> None:
        """
        初始化任务数据库。
        """

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
        创建分析任务表。
        """

        sql = """
        CREATE TABLE IF NOT EXISTS analysis_tasks (
            task_id TEXT PRIMARY KEY,
            dataset_id TEXT NOT NULL,
            question TEXT NOT NULL,
            status TEXT NOT NULL,
            repair_count INTEGER NOT NULL DEFAULT 0,
            response_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """

        with self._connect() as connection:
            connection.execute(sql)

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_analysis_tasks_created_at
                ON analysis_tasks(created_at)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_analysis_tasks_dataset_id
                ON analysis_tasks(dataset_id)
                """
            )

            connection.commit()

    def save_task(
        self,
        response: AnalysisResponse,
    ) -> None:
        """
        保存或更新分析任务结果。
        """

        now = datetime.now(
            timezone.utc
        ).isoformat()

        response_json = (
            response.model_dump_json()
        )

        with self._connect() as connection:
            existing_row = connection.execute(
                """
                SELECT created_at
                FROM analysis_tasks
                WHERE task_id = ?
                """,
                (response.task_id,),
            ).fetchone()

            created_at = (
                existing_row["created_at"]
                if existing_row is not None
                else now
            )

            connection.execute(
                """
                INSERT INTO analysis_tasks (
                    task_id,
                    dataset_id,
                    question,
                    status,
                    repair_count,
                    response_json,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id)
                DO UPDATE SET
                    dataset_id = excluded.dataset_id,
                    question = excluded.question,
                    status = excluded.status,
                    repair_count = excluded.repair_count,
                    response_json = excluded.response_json,
                    updated_at = excluded.updated_at
                """,
                (
                    response.task_id,
                    response.dataset_id,
                    response.question,
                    response.status,
                    response.repair_count,
                    response_json,
                    created_at,
                    now,
                ),
            )

            connection.commit()

    def list_tasks(
        self,
        limit: int = 50,
        dataset_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        查询历史分析任务列表。

        可以通过dataset_id筛选某个数据集的任务。
        """

        if limit < 1:
            raise TaskStoreError(
                "limit必须大于等于1"
            )

        if limit > 200:
            raise TaskStoreError(
                "limit不能超过200"
            )

        with self._connect() as connection:
            if dataset_id:
                rows = connection.execute(
                    """
                    SELECT
                        task_id,
                        dataset_id,
                        question,
                        status,
                        repair_count,
                        created_at,
                        updated_at
                    FROM analysis_tasks
                    WHERE dataset_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (
                        dataset_id.strip(),
                        limit,
                    ),
                ).fetchall()

            else:
                rows = connection.execute(
                    """
                    SELECT
                        task_id,
                        dataset_id,
                        question,
                        status,
                        repair_count,
                        created_at,
                        updated_at
                    FROM analysis_tasks
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()

        return [
            {
                "task_id": row["task_id"],
                "dataset_id": row["dataset_id"],
                "question": row["question"],
                "status": row["status"],
                "repair_count": (
                    row["repair_count"]
                ),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    def get_task(
        self,
        task_id: str,
    ) -> AnalysisResponse:
        """
        查询指定任务的完整分析结果。
        """

        cleaned_task_id = task_id.strip()

        if not cleaned_task_id:
            raise TaskStoreError(
                "task_id不能为空"
            )

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT response_json
                FROM analysis_tasks
                WHERE task_id = ?
                """,
                (cleaned_task_id,),
            ).fetchone()

        if row is None:
            raise TaskNotFoundError(
                f"分析任务不存在："
                f"{cleaned_task_id}"
            )

        try:
            return (
                AnalysisResponse
                .model_validate_json(
                    row["response_json"]
                )
            )

        except Exception as exc:
            raise TaskStoreError(
                f"任务数据解析失败：{exc}"
            ) from exc

    def delete_task(
        self,
        task_id: str,
    ) -> bool:
        """
        删除指定分析任务。
        """

        cleaned_task_id = task_id.strip()

        if not cleaned_task_id:
            raise TaskStoreError(
                "task_id不能为空"
            )

        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM analysis_tasks
                WHERE task_id = ?
                """,
                (cleaned_task_id,),
            )

            connection.commit()

        if cursor.rowcount == 0:
            raise TaskNotFoundError(
                f"分析任务不存在："
                f"{cleaned_task_id}"
            )

        return True


analysis_task_store = AnalysisTaskStore()