import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from evaluation.evaluator import (
    evaluate_response,
)
from evaluation.fault_graph import (
    fault_evaluation_agent,
)
from evaluation.run_evaluation import (
    serialize_value,
)


EVALUATION_DIR = Path(
    __file__
).resolve().parent

DATASET_DIR = (
    EVALUATION_DIR / "datasets"
)

FAULT_CASES_PATH = (
    EVALUATION_DIR
    / "fault_cases.json"
)

RESULTS_DIR = (
    EVALUATION_DIR / "results"
)


def load_fault_cases(
) -> list[dict[str, Any]]:
    """
    读取故障评估题库。
    """

    if not FAULT_CASES_PATH.exists():
        raise FileNotFoundError(
            "找不到故障评估题库："
            f"{FAULT_CASES_PATH}"
        )

    with FAULT_CASES_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        benchmark = json.load(file)

    return benchmark[
        "fault_cases"
    ]


def select_fault_cases(
    cases: list[dict[str, Any]],
    case_id: str | None,
    limit: int | None,
) -> list[dict[str, Any]]:
    """
    根据参数选择需要运行的故障题。
    """

    selected_cases = cases

    if case_id:
        selected_cases = [
            case
            for case in selected_cases
            if (
                case["fault_case_id"]
                == case_id
            )
        ]

        if not selected_cases:
            raise ValueError(
                "找不到故障评估题："
                f"{case_id}"
            )

    if limit is not None:
        selected_cases = (
            selected_cases[:limit]
        )

    return selected_cases


def inspect_execution_trace(
    response_data: dict[str, Any],
    expected_error_type: str,
) -> dict[str, bool]:
    """
    检查LangGraph执行轨迹。

    判断是否经历了：

    故障注入
    → 执行失败
    → 代码修复
    → 重新执行成功
    """

    execution_trace = (
        response_data.get(
            "execution_trace",
            [],
        )
    )

    if not isinstance(
        execution_trace,
        list,
    ):
        execution_trace = []

    trace_text = "\n".join(
        str(message)
        for message
        in execution_trace
    )

    return {
        "fault_injected": (
            "故障注入完成"
            in trace_text
        ),
        "execution_failed": (
            "Python代码执行失败"
            in trace_text
        ),
        "repair_triggered": (
            "代码修复完成"
            in trace_text
        ),
        "execution_succeeded": (
            "Python代码执行成功"
            in trace_text
        ),
        "expected_error_matched": (
            expected_error_type
            in trace_text
        ),
    }


def run_single_fault_case(
    case: dict[str, Any],
    current_index: int,
    total_count: int,
) -> dict[str, Any]:
    """
    运行单道故障注入评估题。
    """

    fault_case_id = case[
        "fault_case_id"
    ]

    base_case_id = case[
        "base_case_id"
    ]

    dataset_file = case[
        "dataset_file"
    ]

    question = case["question"]

    fault_config = case[
        "fault_injection"
    ]

    expected_error_type = case[
        "expected_error_type"
    ]

    dataset_path = (
        DATASET_DIR / dataset_file
    )

    print()
    print("=" * 70)

    print(
        f"[{current_index}/{total_count}] "
        f"故障评估：{fault_case_id}"
    )

    print(
        f"基础题目：{base_case_id}"
    )

    print(
        f"数据集：{dataset_file}"
    )

    print(
        "故障类型："
        f"{fault_config['fault_type']}"
    )

    print(
        "预期错误："
        f"{expected_error_type}"
    )

    print("=" * 70)

    start_time = time.perf_counter()

    try:
        response = (
            fault_evaluation_agent.analyze(
                file_path=str(
                    dataset_path
                ),
                question=question,
                fault_injection=(
                    fault_config
                ),
            )
        )

        duration_seconds = (
            time.perf_counter()
            - start_time
        )

        response_data = (
            serialize_value(response)
        )

        # 使用基础评估器检查修复后的
        # 数值、字段、排序和图表
        basic_evaluation = (
            evaluate_response(
                case=case,
                response=response,
            )
        )

        trace_checks = (
            inspect_execution_trace(
                response_data=(
                    response_data
                ),
                expected_error_type=(
                    expected_error_type
                ),
            )
        )

        repair_count = (
            basic_evaluation.repair_count
        )

        repair_success = (
            trace_checks[
                "fault_injected"
            ]
            and trace_checks[
                "execution_failed"
            ]
            and trace_checks[
                "repair_triggered"
            ]
            and trace_checks[
                "execution_succeeded"
            ]
            and repair_count > 0
            and basic_evaluation.passed
        )

        passed = (
            repair_success
            and trace_checks[
                "expected_error_matched"
            ]
        )

        error_message = (
            basic_evaluation.error_message
        )

        if not trace_checks[
            "fault_injected"
        ]:
            error_message = (
                "没有检测到故障注入节点"
            )

        elif not trace_checks[
            "execution_failed"
        ]:
            error_message = (
                "注入故障后没有触发"
                "代码执行失败"
            )

        elif not trace_checks[
            "expected_error_matched"
        ]:
            error_message = (
                "首次执行的错误类型"
                "与预期不一致"
            )

        elif not trace_checks[
            "repair_triggered"
        ]:
            error_message = (
                "执行失败后没有进入"
                "repair_code节点"
            )

        elif not basic_evaluation.passed:
            error_message = (
                basic_evaluation.error_message
                or
                "修复后的结果未通过"
                "基础任务评分"
            )

    except Exception as exc:
        duration_seconds = (
            time.perf_counter()
            - start_time
        )

        response_data = None

        trace_checks = {
            "fault_injected": False,
            "execution_failed": False,
            "repair_triggered": False,
            "execution_succeeded": False,
            "expected_error_matched": (
                False
            ),
        }

        repair_count = 0
        repair_success = False
        passed = False

        basic_evaluation = None

        error_message = (
            f"{type(exc).__name__}: "
            f"{exc}"
        )

    print(
        "故障注入：",
        (
            "成功"
            if trace_checks[
                "fault_injected"
            ]
            else "失败"
        ),
    )

    print(
        "首次执行失败：",
        (
            "是"
            if trace_checks[
                "execution_failed"
            ]
            else "否"
        ),
    )

    print(
        "错误类型匹配：",
        (
            "是"
            if trace_checks[
                "expected_error_matched"
            ]
            else "否"
        ),
    )

    print(
        "进入修复节点：",
        (
            "是"
            if trace_checks[
                "repair_triggered"
            ]
            else "否"
        ),
    )

    print(
        f"修复次数：{repair_count}"
    )

    print(
        "修复后结果正确：",
        (
            "是"
            if (
                basic_evaluation
                and basic_evaluation.passed
            )
            else "否"
        ),
    )

    print(
        "最终评估：",
        (
            "PASS"
            if passed
            else "FAIL"
        ),
    )

    print(
        f"耗时："
        f"{duration_seconds:.2f}秒"
    )

    if error_message:
        print(
            f"失败原因：{error_message}"
        )

    return {
        "fault_case_id": (
            fault_case_id
        ),
        "base_case_id": (
            base_case_id
        ),
        "dataset_file": (
            dataset_file
        ),
        "question": question,
        "fault_type": (
            fault_config["fault_type"]
        ),
        "expected_error_type": (
            expected_error_type
        ),
        **trace_checks,
        "repair_count": repair_count,
        "repair_success": (
            repair_success
        ),
        "result_correct_after_repair": (
            bool(
                basic_evaluation
                and basic_evaluation.passed
            )
        ),
        "passed": passed,
        "duration_seconds": round(
            duration_seconds,
            3,
        ),
        "error_message": error_message,
        "agent_response": response_data,
    }


def calculate_metrics(
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    计算故障专项评估指标。
    """

    total_cases = len(results)

    if total_cases == 0:
        return {
            "total_cases": 0,
        }

    def count_true(
        field_name: str,
    ) -> int:
        return sum(
            bool(result[field_name])
            for result in results
        )

    def percentage(
        numerator: int,
        denominator: int,
    ) -> float:
        if denominator == 0:
            return 0.0

        return round(
            numerator
            / denominator
            * 100,
            2,
        )

    passed_cases = count_true(
        "passed"
    )

    fault_injected_cases = (
        count_true(
            "fault_injected"
        )
    )

    failure_triggered_cases = (
        count_true(
            "execution_failed"
        )
    )

    error_matched_cases = (
        count_true(
            "expected_error_matched"
        )
    )

    repair_triggered_cases = (
        count_true(
            "repair_triggered"
        )
    )

    repair_success_cases = (
        count_true(
            "repair_success"
        )
    )

    correct_after_repair = (
        count_true(
            "result_correct_after_repair"
        )
    )

    total_repairs = sum(
        int(result["repair_count"])
        for result in results
    )

    total_duration = sum(
        float(
            result["duration_seconds"]
        )
        for result in results
    )

    return {
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "pass_rate": percentage(
            passed_cases,
            total_cases,
        ),
        "fault_injected_cases": (
            fault_injected_cases
        ),
        "fault_injection_rate": (
            percentage(
                fault_injected_cases,
                total_cases,
            )
        ),
        "failure_triggered_cases": (
            failure_triggered_cases
        ),
        "failure_trigger_rate": (
            percentage(
                failure_triggered_cases,
                total_cases,
            )
        ),
        "error_type_matched_cases": (
            error_matched_cases
        ),
        "error_type_match_rate": (
            percentage(
                error_matched_cases,
                total_cases,
            )
        ),
        "repair_triggered_cases": (
            repair_triggered_cases
        ),
        "repair_trigger_rate": (
            percentage(
                repair_triggered_cases,
                total_cases,
            )
        ),
        "repair_success_cases": (
            repair_success_cases
        ),
        "repair_success_rate": (
            percentage(
                repair_success_cases,
                repair_triggered_cases,
            )
        ),
        "correct_after_repair_cases": (
            correct_after_repair
        ),
        "result_accuracy_after_repair": (
            percentage(
                correct_after_repair,
                total_cases,
            )
        ),
        "average_repair_count": round(
            total_repairs
            / total_cases,
            2,
        ),
        "average_duration_seconds": round(
            total_duration
            / total_cases,
            2,
        ),
        "total_duration_seconds": round(
            total_duration,
            2,
        ),
    }


def print_summary(
    metrics: dict[str, Any],
) -> None:
    """
    打印总体评估结果。
    """

    print()
    print("=" * 70)

    print(
        "DataPilot故障注入与"
        "自动修复评估"
    )

    print("=" * 70)

    print(
        f"评估题数："
        f"{metrics['total_cases']}"
    )

    print(
        f"最终通过率："
        f"{metrics['pass_rate']}%"
    )

    print(
        f"故障注入率："
        f"{metrics['fault_injection_rate']}%"
    )

    print(
        f"故障触发率："
        f"{metrics['failure_trigger_rate']}%"
    )

    print(
        f"错误类型匹配率："
        f"{metrics['error_type_match_rate']}%"
    )

    print(
        f"修复节点触发率："
        f"{metrics['repair_trigger_rate']}%"
    )

    print(
        f"自动修复成功率："
        f"{metrics['repair_success_rate']}%"
    )

    print(
        "修复后结果正确率："
        f"{metrics['result_accuracy_after_repair']}%"
    )

    print(
        f"平均修复次数："
        f"{metrics['average_repair_count']}"
    )

    print(
        f"平均耗时："
        f"{metrics['average_duration_seconds']}秒"
    )

    print("=" * 70)


def save_report(
    results: list[dict[str, Any]],
    metrics: dict[str, Any],
) -> Path:
    """
    保存故障评估JSON报告。
    """

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = (
        RESULTS_DIR
        / (
            "fault_evaluation_"
            f"{timestamp}.json"
        )
    )

    report = {
        "benchmark_name": (
            "DataPilot Fault Injection "
            "Evaluation"
        ),
        "benchmark_version": "1.0",
        "created_at": (
            datetime.now().isoformat(
                timespec="seconds"
            )
        ),
        "metrics": metrics,
        "results": results,
    }

    with report_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            ensure_ascii=False,
            indent=2,
        )

    return report_path


def parse_arguments() -> (
    argparse.Namespace
):
    """
    解析命令行参数。
    """

    parser = argparse.ArgumentParser(
        description=(
            "运行DataPilot故障注入评估"
        )
    )

    parser.add_argument(
        "--case-id",
        type=str,
        default=None,
        help=(
            "只运行指定故障题，例如"
            "fault_sales_001"
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="只运行前N道故障题",
    )

    return parser.parse_args()


def main() -> None:
    """
    故障评估程序入口。
    """

    arguments = parse_arguments()

    all_cases = load_fault_cases()

    selected_cases = (
        select_fault_cases(
            cases=all_cases,
            case_id=arguments.case_id,
            limit=arguments.limit,
        )
    )

    results = []

    for index, case in enumerate(
        selected_cases,
        start=1,
    ):
        result = (
            run_single_fault_case(
                case=case,
                current_index=index,
                total_count=len(
                    selected_cases
                ),
            )
        )

        results.append(result)

    metrics = calculate_metrics(
        results
    )

    print_summary(metrics)

    report_path = save_report(
        results=results,
        metrics=metrics,
    )

    print(
        "详细评估报告已保存："
        f"{report_path}"
    )


if __name__ == "__main__":
    main()