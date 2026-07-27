import json
import math
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd


class DatasetProfileError(RuntimeError):
    """
    数据画像生成失败时抛出的异常。
    """


class DatasetProfiler:
    """
    数据集画像分析器。

    负责：
    1. 判断字段语义类型
    2. 统计缺失值和唯一值
    3. 生成数值字段统计
    4. 生成类别字段分布
    5. 识别可能的时间字段
    6. 生成提供给Agent的数据上下文
    """

    def __init__(
        self,
        categorical_unique_limit: int = 50,
        categorical_ratio_limit: float = 0.2,
        identifier_ratio_threshold: float = 0.95,
        datetime_success_threshold: float = 0.8,
        example_limit: int = 5,
    ) -> None:
        self.categorical_unique_limit = categorical_unique_limit
        self.categorical_ratio_limit = categorical_ratio_limit
        self.identifier_ratio_threshold = identifier_ratio_threshold
        self.datetime_success_threshold = datetime_success_threshold
        self.example_limit = example_limit

    def profile(
        self,
        dataframe: pd.DataFrame,
        dataset_name: str | None = None,
    ) -> dict[str, Any]:
        """
        生成完整的数据集画像。
        """

        if dataframe.empty:
            raise DatasetProfileError("无法为空数据集生成数据画像")

        row_count = int(dataframe.shape[0])
        column_count = int(dataframe.shape[1])

        column_profiles: list[dict[str, Any]] = []

        semantic_type_counts = {
            "numeric": 0,
            "categorical": 0,
            "datetime": 0,
            "text": 0,
            "boolean": 0,
            "identifier": 0,
        }

        for column in dataframe.columns:
            column_profile = self._profile_column(
                series=dataframe[column],
                column_name=str(column),
                row_count=row_count,
            )

            semantic_type = column_profile["semantic_type"]
            semantic_type_counts[semantic_type] += 1
            column_profiles.append(column_profile)

        profile_result: dict[str, Any] = {
            "dataset_name": dataset_name or "unnamed_dataset",
            "row_count": row_count,
            "column_count": column_count,
            "total_missing_values": int(
                dataframe.isna().sum().sum()
            ),
            "duplicate_row_count": int(
                dataframe.duplicated().sum()
            ),
            "semantic_type_counts": semantic_type_counts,
            "columns": column_profiles,
        }

        return profile_result

    def _profile_column(
        self,
        series: pd.Series,
        column_name: str,
        row_count: int,
    ) -> dict[str, Any]:
        """
        生成单个字段的数据画像。
        """

        non_null_series = series.dropna()

        non_null_count = int(non_null_series.shape[0])
        missing_count = int(series.isna().sum())
        unique_count = int(non_null_series.nunique())

        missing_ratio = (
            missing_count / row_count
            if row_count > 0
            else 0.0
        )

        unique_ratio = (
            unique_count / non_null_count
            if non_null_count > 0
            else 0.0
        )

        semantic_type = self._infer_semantic_type(
            series=series,
            column_name=column_name,
            non_null_series=non_null_series,
            unique_count=unique_count,
            unique_ratio=unique_ratio,
        )

        profile: dict[str, Any] = {
            "name": column_name,
            "pandas_dtype": str(series.dtype),
            "semantic_type": semantic_type,
            "non_null_count": non_null_count,
            "missing_count": missing_count,
            "missing_ratio": round(missing_ratio, 6),
            "unique_count": unique_count,
            "unique_ratio": round(unique_ratio, 6),
            "examples": self._get_examples(non_null_series),
        }

        if semantic_type == "numeric":
            profile["statistics"] = self._numeric_statistics(
                non_null_series
            )

        elif semantic_type in {
            "categorical",
            "boolean",
        }:
            profile["value_distribution"] = (
                self._value_distribution(non_null_series)
            )

        elif semantic_type == "datetime":
            profile["datetime_range"] = self._datetime_statistics(
                non_null_series
            )

        elif semantic_type == "text":
            profile["text_statistics"] = self._text_statistics(
                non_null_series
            )

        return profile

    def _infer_semantic_type(
        self,
        series: pd.Series,
        column_name: str,
        non_null_series: pd.Series,
        unique_count: int,
        unique_ratio: float,
    ) -> str:
        """
        推断字段的语义类型。
        """

        if non_null_series.empty:
            return "text"

        if pd.api.types.is_bool_dtype(series):
            return "boolean"

        if pd.api.types.is_datetime64_any_dtype(series):
            return "datetime"

        column_name_lower = column_name.lower()

        identifier_keywords = {
            "id",
            "编号",
            "编码",
            "序号",
            "订单号",
            "用户号",
            "商品号",
        }

        looks_like_identifier = any(
            keyword in column_name_lower
            for keyword in identifier_keywords
        )

        if looks_like_identifier and (
            unique_ratio >= self.identifier_ratio_threshold
        ):
            return "identifier"

        if pd.api.types.is_numeric_dtype(series):
            if (
                unique_count <= self.categorical_unique_limit
                and unique_ratio <= self.categorical_ratio_limit
            ):
                return "categorical"

            return "numeric"

        if self._looks_like_datetime(
            non_null_series,
            column_name_lower,
        ):
            return "datetime"

        if unique_ratio >= self.identifier_ratio_threshold:
            if looks_like_identifier:
                return "identifier"

        if (
            unique_count <= self.categorical_unique_limit
            or unique_ratio <= self.categorical_ratio_limit
        ):
            return "categorical"

        return "text"

    def _looks_like_datetime(
        self,
        series: pd.Series,
        column_name_lower: str,
    ) -> bool:
        """
        判断字符串字段是否可能是时间字段。
        """

        datetime_keywords = {
            "date",
            "time",
            "year",
            "month",
            "日期",
            "时间",
            "年月",
            "年份",
            "月份",
        }

        name_has_datetime_keyword = any(
            keyword in column_name_lower
            for keyword in datetime_keywords
        )

        sample = series.astype(str).head(100)

        try:
            parsed = pd.to_datetime(
                sample,
                errors="coerce",
            )
        except Exception:
            return False

        success_ratio = float(parsed.notna().mean())

        if name_has_datetime_keyword:
            return success_ratio >= 0.6

        return success_ratio >= self.datetime_success_threshold

    @staticmethod
    def _numeric_statistics(
        series: pd.Series,
    ) -> dict[str, Any]:
        """
        计算数值字段统计信息。
        """

        numeric_series = pd.to_numeric(
            series,
            errors="coerce",
        ).dropna()

        if numeric_series.empty:
            return {}

        statistics = {
            "min": numeric_series.min(),
            "max": numeric_series.max(),
            "mean": numeric_series.mean(),
            "median": numeric_series.median(),
            "std": numeric_series.std(),
            "sum": numeric_series.sum(),
            "q25": numeric_series.quantile(0.25),
            "q75": numeric_series.quantile(0.75),
        }

        return {
            key: DatasetProfiler._make_json_safe(value)
            for key, value in statistics.items()
        }

    def _value_distribution(
        self,
        series: pd.Series,
    ) -> list[dict[str, Any]]:
        """
        返回类别字段出现次数最多的前10个值。
        """

        counts = series.value_counts(dropna=True).head(10)
        total = int(series.shape[0])

        distribution = []

        for value, count in counts.items():
            distribution.append(
                {
                    "value": self._make_json_safe(value),
                    "count": int(count),
                    "ratio": round(
                        int(count) / total,
                        6,
                    ) if total > 0 else 0.0,
                }
            )

        return distribution

    @staticmethod
    def _datetime_statistics(
        series: pd.Series,
    ) -> dict[str, Any]:
        """
        计算时间字段的起止范围。
        """

        parsed = pd.to_datetime(
            series,
            errors="coerce",
        ).dropna()

        if parsed.empty:
            return {}

        return {
            "min": parsed.min().isoformat(),
            "max": parsed.max().isoformat(),
        }

    @staticmethod
    def _text_statistics(
        series: pd.Series,
    ) -> dict[str, Any]:
        """
        计算文本字段长度统计信息。
        """

        lengths = series.astype(str).str.len()

        if lengths.empty:
            return {}

        return {
            "min_length": int(lengths.min()),
            "max_length": int(lengths.max()),
            "mean_length": round(
                float(lengths.mean()),
                4,
            ),
        }

    def _get_examples(
        self,
        series: pd.Series,
    ) -> list[Any]:
        """
        获取字段示例值。
        """

        examples = series.drop_duplicates().head(
            self.example_limit
        )

        return [
            self._make_json_safe(value)
            for value in examples.tolist()
        ]

    @staticmethod
    def _make_json_safe(value: Any) -> Any:
        """
        将NumPy、Pandas和时间类型转换成JSON兼容类型。
        """

        if value is None:
            return None

        if isinstance(value, (datetime, date, pd.Timestamp)):
            return value.isoformat()

        if isinstance(value, np.integer):
            return int(value)

        if isinstance(value, np.floating):
            value = float(value)

        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                return None

            return value

        if isinstance(value, np.bool_):
            return bool(value)

        return str(value) if not isinstance(
            value,
            (str, int, bool),
        ) else value

    def build_agent_context(
        self,
        dataframe: pd.DataFrame,
        dataset_name: str | None = None,
        sample_row_count: int = 5,
    ) -> str:
        """
        生成提供给LLM的数据集上下文。

        不传递完整数据，只传递数据画像和少量样例，
        避免大型数据集占用过多Token。
        """

        profile = self.profile(
            dataframe=dataframe,
            dataset_name=dataset_name,
        )

        sample_dataframe = (
            dataframe
            .head(sample_row_count)
            .astype(object)
            .where(pd.notna(dataframe.head(sample_row_count)), None)
        )

        sample_records = []

        for record in sample_dataframe.to_dict(
            orient="records"
        ):
            safe_record = {
                str(key): self._make_json_safe(value)
                for key, value in record.items()
            }
            sample_records.append(safe_record)

        context = {
            "dataset_profile": profile,
            "sample_rows": sample_records,
            "important_instruction": (
                "只能使用数据集中真实存在的字段，"
                "不得虚构字段名称。"
            ),
        }

        return json.dumps(
            context,
            ensure_ascii=False,
            indent=2,
        )


dataset_profiler = DatasetProfiler()