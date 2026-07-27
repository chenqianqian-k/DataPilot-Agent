from typing import Any

from app.agent.code_executor import (
    analysis_code_executor,
)
from app.agent.code_generator import (
    analysis_code_generator,
)
from app.agent.code_repairer import (
    analysis_code_repairer,
)
from app.agent.planner import analysis_planner
from app.agent.reporter import analysis_reporter
from app.agent.state import AnalysisAgentState
from app.data.loader import dataset_loader
from app.data.profiler import dataset_profiler
from app.schemas.dataset import DatasetProfile


def load_data_node(
    state: AnalysisAgentState,
) -> dict[str, Any]:
    """
    读取CSV或Excel文件。

    读取State：
    - file_path

    更新State：
    - dataframe
    - status
    - execution_trace
    """

    file_path = state["file_path"]

    dataframe = dataset_loader.load(
        file_path=file_path
    )

    return {
        "dataframe": dataframe,
        "status": "profiling",
        "execution_trace": [
            (
                f"数据集加载完成："
                f"{dataframe.shape[0]}行，"
                f"{dataframe.shape[1]}列"
            )
        ],
    }


def profile_data_node(
    state: AnalysisAgentState,
) -> dict[str, Any]:
    """
    生成并验证数据集画像。

    读取State：
    - dataframe
    - file_path

    更新State：
    - profile
    - status
    - execution_trace
    """

    dataframe = state["dataframe"]
    file_path = state["file_path"]

    dataset_name = file_path.replace(
        "\\",
        "/",
    ).split("/")[-1]

    profile_dict = dataset_profiler.profile(
        dataframe=dataframe,
        dataset_name=dataset_name,
    )

    profile = DatasetProfile.model_validate(
        profile_dict
    )

    return {
        "profile": profile,
        "status": "planning",
        "execution_trace": [
            "数据画像生成完成"
        ],
    }


def plan_analysis_node(
    state: AnalysisAgentState,
) -> dict[str, Any]:
    """
    根据用户问题和数据画像生成分析计划。

    读取State：
    - question
    - profile

    更新State：
    - plan
    - status
    - execution_trace
    """

    question = state["question"]
    profile = state["profile"]

    plan = analysis_planner.create_plan(
        question=question,
        dataset_profile=profile,
    )

    return {
        "plan": plan,
        "status": "generating",
        "execution_trace": [
            (
                f"分析计划生成完成，"
                f"共{len(plan.steps)}个步骤"
            )
        ],
    }


def generate_code_node(
    state: AnalysisAgentState,
) -> dict[str, Any]:
    """
    根据分析计划生成Python代码。

    读取State：
    - question
    - profile
    - plan

    更新State：
    - current_code
    - code_explanation
    - status
    - execution_trace
    """

    question = state["question"]
    profile = state["profile"]
    plan = state["plan"]

    code_result = (
        analysis_code_generator.generate_code(
            question=question,
            plan=plan,
            dataset_profile=profile,
        )
    )

    return {
        "current_code": code_result.code,
        "code_explanation": (
            code_result.explanation
        ),
        "status": "executing",
        "execution_trace": [
            "Python分析代码生成完成"
        ],
    }


def execute_code_node(
    state: AnalysisAgentState,
) -> dict[str, Any]:
    """
    执行当前Python代码。

    读取State：
    - current_code
    - dataframe

    更新State：
    - execution
    - status
    - execution_trace
    """

    current_code = state["current_code"]
    dataframe = state["dataframe"]

    execution = analysis_code_executor.execute(
        code=current_code,
        dataframe=dataframe,
    )

    if execution.success:
        status = "reporting"

        trace_message = (
            f"Python代码执行成功，耗时"
            f"{execution.execution_time_seconds}秒"
        )

    else:
        status = "execution_failed"

        trace_message = (
            f"Python代码执行失败："
            f"{execution.error_type}: "
            f"{execution.error_message}"
        )

    return {
        "execution": execution,
        "status": status,
        "execution_trace": [
            trace_message
        ],
    }


def repair_code_node(
    state: AnalysisAgentState,
) -> dict[str, Any]:
    """
    根据真实执行错误修复Python代码。

    读取State：
    - question
    - profile
    - plan
    - current_code
    - execution
    - repair_count

    更新State：
    - current_code
    - code_explanation
    - repair_count
    - status
    - execution_trace
    """

    question = state["question"]
    profile = state["profile"]
    plan = state["plan"]
    current_code = state["current_code"]
    execution = state["execution"]

    current_repair_count = state.get(
        "repair_count",
        0,
    )

    repaired_result = (
        analysis_code_repairer.repair_code(
            question=question,
            plan=plan,
            dataset_profile=profile,
            failed_code=current_code,
            execution=execution,
        )
    )

    new_repair_count = (
        current_repair_count + 1
    )

    return {
        "current_code": repaired_result.code,
        "code_explanation": (
            repaired_result.explanation
        ),
        "repair_count": new_repair_count,
        "status": "executing",
        "execution_trace": [
            (
                f"第{new_repair_count}次"
                f"代码修复完成"
            )
        ],
    }


def report_result_node(
    state: AnalysisAgentState,
) -> dict[str, Any]:
    """
    根据成功执行结果生成最终报告。

    读取State：
    - question
    - plan
    - execution
    - code_explanation

    更新State：
    - answer
    - status
    - execution_trace
    """

    question = state["question"]
    plan = state["plan"]
    execution = state["execution"]

    code_explanation = state.get(
        "code_explanation",
        "",
    )

    report = analysis_reporter.generate_report(
        question=question,
        plan=plan,
        execution=execution,
        code_explanation=code_explanation,
    )

    return {
        "answer": report,
        "status": "completed",
        "error_message": None,
        "execution_trace": [
            "数据分析报告生成完成"
        ],
    }


def mark_failed_node(
    state: AnalysisAgentState,
) -> dict[str, Any]:
    """
    达到最大修复次数后，将任务标记为失败。

    读取State：
    - execution
    - repair_count

    更新State：
    - status
    - error_message
    - execution_trace
    """

    execution = state["execution"]

    repair_count = state.get(
        "repair_count",
        0,
    )

    error_type = (
        execution.error_type
        or "UnknownError"
    )

    error_message = (
        execution.error_message
        or "没有具体错误信息"
    )

    final_error_message = (
        f"代码经过{repair_count}次修复后"
        f"仍然执行失败："
        f"{error_type}: {error_message}"
    )

    return {
        "status": "failed",
        "error_message": final_error_message,
        "execution_trace": [
            "达到最大代码修复次数，任务失败"
        ],
    }