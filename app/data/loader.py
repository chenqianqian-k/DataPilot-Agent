from pathlib import Path
from typing import Any

import pandas as pd

from app.core.config import settings


class DatasetLoadError(RuntimeError):
    """
    数据集读取失败时抛出的业务异常。
    """


class UnsupportedFileTypeError(DatasetLoadError):
    """
    上传了不支持的文件类型。
    """


class DatasetLoader:
    """
    CSV和Excel数据集加载器。

    负责：
    1. 检查文件是否存在
    2. 检查文件格式
    3. 检查文件大小
    4. 尝试多种CSV编码
    5. 读取Excel工作表
    6. 返回数据集基础信息
    """

    supported_extensions = {".csv", ".xlsx"}

    csv_encodings = (
        "utf-8-sig",
        "utf-8",
        "gb18030",
        "gbk",
    )

    def validate_file(self, file_path: str | Path) -> Path:
        """
        检查文件路径、格式和大小。
        """

        path = Path(file_path).resolve()

        if not path.exists():
            raise DatasetLoadError(f"文件不存在：{path}")

        if not path.is_file():
            raise DatasetLoadError(f"目标路径不是文件：{path}")

        extension = path.suffix.lower()

        if extension not in self.supported_extensions:
            supported = ", ".join(sorted(self.supported_extensions))
            raise UnsupportedFileTypeError(
                f"不支持{extension or '未知'}格式，仅支持：{supported}"
            )

        file_size_mb = path.stat().st_size / (1024 * 1024)

        if file_size_mb > settings.max_upload_size_mb:
            raise DatasetLoadError(
                f"文件大小为{file_size_mb:.2f}MB，"
                f"超过{settings.max_upload_size_mb}MB限制"
            )

        if path.stat().st_size == 0:
            raise DatasetLoadError("文件内容为空")

        return path

    def load(
        self,
        file_path: str | Path,
        sheet_name: str | int = 0,
    ) -> pd.DataFrame:
        """
        根据文件类型加载数据集。

        Parameters
        ----------
        file_path:
            CSV或Excel文件路径。
        sheet_name:
            Excel工作表名称或下标，默认读取第一个工作表。
        """

        path = self.validate_file(file_path)

        if path.suffix.lower() == ".csv":
            dataframe = self._load_csv(path)
        else:
            dataframe = self._load_excel(path, sheet_name)

        if dataframe.empty:
            raise DatasetLoadError("文件可以读取，但数据集没有任何数据行")

        dataframe.columns = [
            str(column).strip()
            for column in dataframe.columns
        ]

        self._validate_columns(dataframe)

        return dataframe

    def _load_csv(self, file_path: Path) -> pd.DataFrame:
        """
        使用常见中英文编码依次尝试读取CSV。
        """

        encoding_errors: list[str] = []

        for encoding in self.csv_encodings:
            try:
                return pd.read_csv(
                    file_path,
                    encoding=encoding,
                    low_memory=False,
                )
            except UnicodeDecodeError:
                encoding_errors.append(encoding)
            except pd.errors.EmptyDataError as exc:
                raise DatasetLoadError("CSV文件中没有可读取的数据") from exc
            except pd.errors.ParserError as exc:
                raise DatasetLoadError(
                    f"CSV文件结构解析失败：{exc}"
                ) from exc
            except Exception as exc:
                raise DatasetLoadError(
                    f"CSV读取失败：{type(exc).__name__}: {exc}"
                ) from exc

        tried_encodings = ", ".join(encoding_errors)

        raise DatasetLoadError(
            f"无法识别CSV文件编码，已尝试：{tried_encodings}"
        )

    @staticmethod
    def _load_excel(
        file_path: Path,
        sheet_name: str | int,
    ) -> pd.DataFrame:
        """
        读取Excel中的指定工作表。
        """

        try:
            return pd.read_excel(
                file_path,
                sheet_name=sheet_name,
                engine="openpyxl",
            )
        except ValueError as exc:
            raise DatasetLoadError(
                f"Excel工作表不存在或格式错误：{exc}"
            ) from exc
        except Exception as exc:
            raise DatasetLoadError(
                f"Excel读取失败：{type(exc).__name__}: {exc}"
            ) from exc

    @staticmethod
    def _validate_columns(dataframe: pd.DataFrame) -> None:
        """
        检查字段名是否为空或重复。
        """

        if dataframe.columns.empty:
            raise DatasetLoadError("数据集中不存在字段")

        empty_columns = [
            index
            for index, column in enumerate(dataframe.columns)
            if not str(column).strip()
        ]

        if empty_columns:
            raise DatasetLoadError(
                f"数据集中存在空字段名，位置：{empty_columns}"
            )

        duplicated_columns = dataframe.columns[
            dataframe.columns.duplicated()
        ].tolist()

        if duplicated_columns:
            raise DatasetLoadError(
                f"数据集中存在重复字段：{duplicated_columns}"
            )

    @staticmethod
    def get_excel_sheet_names(
        file_path: str | Path,
    ) -> list[str]:
        """
        获取Excel文件中的全部工作表名称。
        """

        path = Path(file_path).resolve()

        try:
            with pd.ExcelFile(path, engine="openpyxl") as excel_file:
                return excel_file.sheet_names
        except Exception as exc:
            raise DatasetLoadError(
                f"无法获取Excel工作表：{exc}"
            ) from exc

    @staticmethod
    def get_basic_info(
        dataframe: pd.DataFrame,
        file_path: str | Path | None = None,
    ) -> dict[str, Any]:
        """
        获取可以直接返回给前端的数据集基础信息。
        """

        missing_values = {
            str(column): int(count)
            for column, count in dataframe.isna().sum().items()
        }

        data_types = {
            str(column): str(dtype)
            for column, dtype in dataframe.dtypes.items()
        }

        unique_values = {
            str(column): int(dataframe[column].nunique(dropna=True))
            for column in dataframe.columns
        }

        info: dict[str, Any] = {
            "row_count": int(dataframe.shape[0]),
            "column_count": int(dataframe.shape[1]),
            "columns": [str(column) for column in dataframe.columns],
            "data_types": data_types,
            "missing_values": missing_values,
            "total_missing_values": int(
                dataframe.isna().sum().sum()
            ),
            "unique_values": unique_values,
            "duplicate_row_count": int(
                dataframe.duplicated().sum()
            ),
            "memory_usage_bytes": int(
                dataframe.memory_usage(deep=True).sum()
            ),
        }

        if file_path is not None:
            path = Path(file_path).resolve()

            info.update(
                {
                    "file_name": path.name,
                    "file_extension": path.suffix.lower(),
                    "file_size_bytes": path.stat().st_size,
                }
            )

        return info


dataset_loader = DatasetLoader()