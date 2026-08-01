from typing import Any

from langgraph.graph import (
    END,
    START,
    StateGraph,
)

from app.agent.analysis_agent import (
    DataAnalysisAgent,
)
from app.agent.graph import (
    route_after_execution,
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
from app.agent.state import (
    AnalysisAgentState,
)
from evaluation.fault_injection import (
    FaultInjectionError,
    inject_fault,
)


def inject_fault_node(
    state: AnalysisAgentState,
) -> dict[str, Any]:
    """
    向第一次生成的Python代码注入故障。

    该节点只会在故障评估Graph中使用。
    """

    if state.get(
        "fault_injected",
        False,
    ):
        return {
            "execution_trace": [
                "故障已经注入，跳过重复注入"
            ],
        }

    current_code = state[
        "current_code"
    ]

    fault_config = state.get(
        "fault_injection"
    )

    if not fault_config:
        raise FaultInjectionError(
            "故障评估工作流缺少"
            "fault_injection配置"
        )

    fault_type = fault_config.get(
        "fault_type"
    )

    if not fault_type:
        raise FaultInjectionError(
            "fault_injection中缺少"
            "fault_type"
        )

    target_text = fault_config.get(
        "target_text"
    )

    replacement_text = (
        fault_config.get(
            "replacement_text"
        )
    )

    injection_result = inject_fault(
        code=current_code,
        fault_type=fault_type,
        target_text=target_text,
        replacement_text=(
            replacement_text
        ),
    )

    return {
        "original_code": (
            injection_result.original_code
        ),
        "current_code": (
            injection_result.injected_code
        ),
        "fault_injected": True,
        "fault_description": (
            injection_result.description
        ),
        "status": "executing",
        "execution_trace": [
            (
                "故障注入完成："
                f"{injection_result.description}"
            )
        ],
    }


def build_fault_analysis_graph():
    """
    创建带故障注入节点的评估工作流。
    """

    builder = StateGraph(
        AnalysisAgentState
    )

    # 注册节点
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
        "inject_fault",
        inject_fault_node,
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

    # 固定流程
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

    # 在生成代码和执行代码之间注入故障
    builder.add_edge(
        "generate_code",
        "inject_fault",
    )

    builder.add_edge(
        "inject_fault",
        "execute_code",
    )

    # 根据执行结果进行条件路由
    builder.add_conditional_edges(
        "execute_code",
        route_after_execution,
        {
            "repair_code": (
                "repair_code"
            ),
            "report_result": (
                "report_result"
            ),
            "mark_failed": (
                "mark_failed"
            ),
        },
    )

    # 修复后直接重新执行，
    # 不能再次经过inject_fault
    builder.add_edge(
        "repair_code",
        "execute_code",
    )

    builder.add_edge(
        "report_result",
        END,
    )

    builder.add_edge(
        "mark_failed",
        END,
    )

    return builder.compile()


fault_analysis_graph = (
    build_fault_analysis_graph()
)


fault_evaluation_agent = (
    DataAnalysisAgent(
        max_repair_attempts=2,
        workflow=fault_analysis_graph,
    )
)