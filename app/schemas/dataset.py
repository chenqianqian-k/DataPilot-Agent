from typing import Any, Literal

from pydantic import BaseModel, Field


SemanticType = Literal[
    "numeric",
    "categorical",
    "datetime",
    "text",
    "boolean",
    "identifier",
]


class ColumnProfile(BaseModel):
    """
    单个字段的数据画像。
    """

    name: str = Field(
        min_length=1,
        description="字段名称",
    )

    pandas_dtype: str = Field(
        description="Pandas识别的原始数据类型",
    )

    semantic_type: SemanticType = Field(
        description="DataPilot推断出的字段语义类型",
    )

    non_null_count: int = Field(
        ge=0,
        description="非空数据数量",
    )

    missing_count: int = Field(
        ge=0,
        description="缺失值数量",
    )

    missing_ratio: float = Field(
        ge=0,
        le=1,
        description="缺失值比例",
    )

    unique_count: int = Field(
        ge=0,
        description="唯一值数量",
    )

    unique_ratio: float = Field(
        ge=0,
        le=1,
        description="唯一值比例",
    )

    examples: list[Any] = Field(
        default_factory=list,
        description="字段示例值",
    )

    statistics: dict[str, Any] | None = Field(
        default=None,
        description="数值字段统计信息",
    )

    value_distribution: list[dict[str, Any]] | None = Field(
        default=None,
        description="类别字段主要取值分布",
    )

    datetime_range: dict[str, Any] | None = Field(
        default=None,
        description="时间字段的起止范围",
    )

    text_statistics: dict[str, Any] | None = Field(
        default=None,
        description="文本字段长度统计",
    )


class DatasetProfile(BaseModel):
    """
    完整数据集画像。
    """

    dataset_name: str = Field(
        min_length=1,
        description="数据集名称",
    )

    row_count: int = Field(
        ge=0,
        description="数据行数",
    )

    column_count: int = Field(
        ge=0,
        description="字段数量",
    )

    total_missing_values: int = Field(
        ge=0,
        description="整个数据集的缺失值数量",
    )

    duplicate_row_count: int = Field(
        ge=0,
        description="重复数据行数量",
    )

    semantic_type_counts: dict[str, int] = Field(
        default_factory=dict,
        description="不同语义类型的字段数量",
    )

    columns: list[ColumnProfile] = Field(
        default_factory=list,
        description="各字段的详细画像",
    )


class DatasetUploadResponse(BaseModel):
    """
    文件上传成功后返回给前端的数据。
    """

    dataset_id: str = Field(
        min_length=1,
        description="数据集唯一标识",
    )

    file_name: str = Field(
        min_length=1,
        description="原始文件名",
    )

    file_type: str = Field(
        description="文件扩展名",
        examples=[".csv"],
    )

    file_size_bytes: int = Field(
        ge=0,
        description="文件大小",
    )

    message: str = Field(
        default="数据集上传并解析成功",
        description="上传结果说明",
    )

    profile: DatasetProfile = Field(
        description="数据集画像",
    )


class DatasetListItem(BaseModel):
    """
    数据集列表中的单条数据。
    """

    dataset_id: str
    file_name: str
    file_type: str
    file_size_bytes: int = Field(ge=0)
    row_count: int = Field(ge=0)
    column_count: int = Field(ge=0)


class DatasetDeleteResponse(BaseModel):
    """
    删除数据集后的响应。
    """

    dataset_id: str
    deleted: bool
    message: str