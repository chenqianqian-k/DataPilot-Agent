from typing import Any, Literal

from pydantic import BaseModel, Field


AnalysisOperation = Literal[
    "inspect",
    "clean",
    "filter",
    "aggregate",
    "calculate",
    "sort",
    "visualize",
    "summarize",
]

TaskStatus = Literal[
    "pending",
    "planning",
    "executing",
    "validating",
    "completed",
    "failed",
]


class AnalysisRequest(BaseModel):
    """
    用户提交的数据分析请求。
    """

    dataset_id: str = Field(
        min_length=1,
        description="需要分析的数据集ID",
    )

    question: str = Field(
        min_length=2,
        max_length=2000,
        description="用户的数据分析问题",
        examples=["分析不同地区的销售额差异"],
    )


class AnalysisStep(BaseModel):
    """
    分析计划中的单个步骤。
    """

    step_id: int = Field(
        ge=1,
        description="步骤编号，从1开始",
    )

    title: str = Field(
        min_length=1,
        description="步骤标题",
    )

    description: str = Field(
        min_length=1,
        description="步骤具体说明",
    )

    operation: AnalysisOperation = Field(
        description="该步骤执行的操作类型",
    )

    required_columns: list[str] = Field(
        default_factory=list,
        description=(
            "该步骤需要读取的数据集原始字段，"
            "不包含计算后产生的输出字段"
        ),
    )


class AnalysisPlan(BaseModel):
    """
    Agent生成的完整分析计划。
    """

    objective: str = Field(
        min_length=1,
        description="本次数据分析的总体目标",
    )

    required_columns: list[str] = Field(
        default_factory=list,
        description=(
            "整个任务需要读取的数据集原始字段，"
            "不包含聚合、计算或重命名后的输出字段"
        ),
    )

    steps: list[AnalysisStep] = Field(
        min_length=1,
        description="具体分析步骤",
    )

    expected_outputs: list[str] = Field(
        default_factory=list,
        description="预期输出结果",
    )

    needs_visualization: bool = Field(
        default=False,
        description="是否需要生成图表",
    )

    chart_type: str | None = Field(
        default=None,
        description="建议使用的图表类型",
    )


class CodeGenerationResult(BaseModel):
    """
    Agent生成的Python分析代码。
    """

    language: Literal["python"] = "python"

    code: str = Field(
        min_length=1,
        description="生成的Python代码",
    )

    explanation: str = Field(
        default="",
        description="代码逻辑说明",
    )


class ExecutionResult(BaseModel):
    """
    Python代码执行结果。
    """

    success: bool = Field(
        description="代码是否执行成功",
    )

    stdout: str = Field(
        default="",
        description="代码标准输出",
    )

    error_type: str | None = Field(
        default=None,
        description="错误类型",
    )

    error_message: str | None = Field(
        default=None,
        description="错误信息",
    )

    result_preview: list[dict[str, Any]] = Field(
        default_factory=list,
        description="结果数据预览",
    )

    generated_files: list[str] = Field(
        default_factory=list,
        description="生成的图表或报告文件",
    )

    execution_time_seconds: float = Field(
        default=0.0,
        ge=0,
        description="代码执行时间",
    )


class AnalysisResponse(BaseModel):
    """
    完整数据分析任务响应。
    """

    task_id: str = Field(
        min_length=1,
        description="分析任务唯一标识",
    )

    dataset_id: str = Field(
        min_length=1,
        description="被分析的数据集ID",
    )

    question: str = Field(
        min_length=1,
        description="用户原始问题",
    )

    status: TaskStatus = Field(
        description="任务最终状态",
    )

    plan: AnalysisPlan | None = Field(
        default=None,
        description="Agent生成的分析计划",
    )

    generated_code: str | None = Field(
        default=None,
        description="最终执行的Python分析代码",
    )

    code_explanation: str | None = Field(
        default=None,
        description="最终Python代码的逻辑说明",
    )

    execution: ExecutionResult | None = Field(
        default=None,
        description="Python代码执行结果",
    )

    repair_count: int = Field(
        default=0,
        ge=0,
        description="代码自动修复次数",
    )

    execution_trace: list[str] = Field(
        default_factory=list,
        description="LangGraph节点执行轨迹",
    )

    answer: str | None = Field(
        default=None,
        description="最终数据分析结论",
    )

    error_message: str | None = Field(
        default=None,
        description="任务失败时的错误信息",
    )

class AnalysisTaskSummary(BaseModel):
    """
    历史任务列表中的简要信息。
    """

    task_id: str = Field(
        min_length=1,
        description="分析任务唯一标识",
    )

    dataset_id: str = Field(
        min_length=1,
        description="被分析的数据集ID",
    )

    question: str = Field(
        min_length=1,
        description="用户分析问题",
    )

    status: TaskStatus = Field(
        description="任务最终状态",
    )

    repair_count: int = Field(
        default=0,
        ge=0,
        description="代码自动修复次数",
    )

    created_at: str = Field(
        description="任务创建时间",
    )

    updated_at: str = Field(
        description="任务最后更新时间",
    )


class AnalysisTaskDeleteResponse(BaseModel):
    """
    删除历史任务后的响应。
    """

    task_id: str = Field(
        min_length=1,
        description="被删除的任务ID",
    )

    deleted: bool = Field(
        description="是否删除成功",
    )

    message: str = Field(
        description="删除结果说明",
    )
