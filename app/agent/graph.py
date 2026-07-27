from typing import Literal

from langgraph.graph import (
    END,
    START,
    StateGraph,
)

from app.agent.nodes import (
    execute_code_node,
    generate_code_node,
    load_data_node,
    mark_failed_node,
    plan_analysis_node,
    profile_data_node,
    repair_code_node,
    report_result_node,
)
from app.agent.state import AnalysisAgentState


ExecutionRoute = Literal[
    "repair_code",
    "report_result",
    "mark_failed",
]


def route_after_execution(
    state: AnalysisAgentState,
) -> ExecutionRoute:
    """
    根据代码执行结果决定下一个节点。

    路由规则：

    1. 执行成功：
       前往report_result。

    2. 执行失败且未达到修复上限：
       前往repair_code。

    3. 执行失败且达到修复上限：
       前往mark_failed。
    """

    execution = state["execution"]

    if execution.success:
        return "report_result"

    repair_count = state.get(
        "repair_count",
        0,
    )

    max_repair_attempts = state.get(
        "max_repair_attempts",
        2,
    )

    if repair_count < max_repair_attempts:
        return "repair_code"

    return "mark_failed"


def build_analysis_graph():
    """
    创建并编译DataPilot LangGraph工作流。
    """

    builder = StateGraph(
        AnalysisAgentState
    )

    # =========================
    # 注册节点
    # =========================

    builder.add_node(
        "load_data",
        load_data_node,
    )

    builder.add_node(
        "profile_data",
        profile_data_node,
    )

    builder.add_node(
        "plan_analysis",
        plan_analysis_node,
    )

    builder.add_node(
        "generate_code",
        generate_code_node,
    )

    builder.add_node(
        "execute_code",
        execute_code_node,
    )

    builder.add_node(
        "repair_code",
        repair_code_node,
    )

    builder.add_node(
        "report_result",
        report_result_node,
    )

    builder.add_node(
        "mark_failed",
        mark_failed_node,
    )

    # =========================
    # 添加固定边
    # =========================

    builder.add_edge(
        START,
        "load_data",
    )

    builder.add_edge(
        "load_data",
        "profile_data",
    )

    builder.add_edge(
        "profile_data",
        "plan_analysis",
    )

    builder.add_edge(
        "plan_analysis",
        "generate_code",
    )

    builder.add_edge(
        "generate_code",
        "execute_code",
    )

    # =========================
    # 添加条件边
    # =========================

    builder.add_conditional_edges(
        "execute_code",
        route_after_execution,
        {
            "repair_code": "repair_code",
            "report_result": "report_result",
            "mark_failed": "mark_failed",
        },
    )

    # 修复后重新执行
    builder.add_edge(
        "repair_code",
        "execute_code",
    )

    # 成功报告后结束
    builder.add_edge(
        "report_result",
        END,
    )

    # 达到修复上限后结束
    builder.add_edge(
        "mark_failed",
        END,
    )

    return builder.compile()


analysis_graph = build_analysis_graph()