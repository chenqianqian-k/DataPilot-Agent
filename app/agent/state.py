from operator import add
from typing import (
    Annotated,
    Any,
    TypedDict,
)

import pandas as pd

from app.schemas.analysis import (
    AnalysisPlan,
    ExecutionResult,
)
from app.schemas.dataset import (
    DatasetProfile,
)


class AnalysisAgentState(
    TypedDict,
    total=False,
):
    """
    DataPilot LangGraph共享状态。

    每个工作流节点都可以读取当前状态，
    并返回自己需要更新的字段。
    """

    # =========================
    # Task identity
    # =========================

    task_id: str
    dataset_id: str
    file_path: str
    question: str

    # =========================
    # Task status
    # =========================

    status: str
    error_message: str | None

    # =========================
    # Dataset
    # =========================

    dataframe: pd.DataFrame
    profile: DatasetProfile

    # =========================
    # Analysis planning
    # =========================

    plan: AnalysisPlan

    # =========================
    # Code generation
    # =========================

    current_code: str
    code_explanation: str

    # =========================
    # Code execution
    # =========================

    execution: ExecutionResult
    repair_count: int
    max_repair_attempts: int

    # =========================
    # Fault evaluation
    # =========================

    # 故障类型及其参数
    fault_injection: dict[
        str,
        Any,
    ]

    # 是否已经完成故障注入
    fault_injected: bool

    # Agent最初生成的正常代码
    original_code: str

    # 本次故障的说明
    fault_description: str

    # =========================
    # Final response
    # =========================

    answer: str

    # =========================
    # Execution trace
    # =========================

    execution_trace: Annotated[
        list[str],
        add,
    ]
