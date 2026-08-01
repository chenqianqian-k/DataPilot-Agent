import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from app.agent.analysis_agent import (
    data_analysis_agent,
)
from evaluation.evaluator import (
    EvaluationResult,
    evaluate_response,
    load_evaluation_cases,
)


EVALUATION_DIR = Path(__file__).resolve().parent
DATASET_DIR = EVALUATION_DIR / "datasets"
RESULTS_DIR = EVALUATION_DIR / "results"


def serialize_value(
    value: Any,
) -> Any:
    """
    将Pydantic对象和Path等类型转换为
    可以写入JSON的普通Python对象。
    """

    if value is None:
        return None

    if hasattr(value, "model_dump"):
        return serialize_value(
            value.model_dump()
        )

    if hasattr(value, "dict"):
        return serialize_value(
            value.dict()
        )

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, dict):
        return {
            str(key): serialize_value(
                item
            )
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            serialize_value(item)
            for item in value
        ]

    if isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
        ),
    ):
        return value

    return str(value)


def select_cases(
    cases: list[dict[str, Any]],
    case_id: str | None,
    limit: int | None,
) -> list[dict[str, Any]]:
    """
    根据命令行参数选择需要运行的题目。
    """

    selected_cases = cases

    if case_id:
        selected_cases = [
            case
            for case in selected_cases
            if case["case_id"] == case_id
        ]

        if not selected_cases:
            raise ValueError(
                f"找不到评估题目：{case_id}"
            )

    if limit is not None:
        selected_cases = (
            selected_cases[:limit]
        )

    return selected_cases


def create_failed_result(
    case: dict[str, Any],
    error_message: str,
) -> EvaluationResult:
    """
    当调用Agent本身发生异常时，
    创建一个失败的评分结果。
    """

    return EvaluationResult(
        case_id=case["case_id"],
        dataset_file=(
            case["dataset_file"]
        ),
        category=case["category"],
        passed=False,
        execution_success=False,
        result_correct=False,
        columns_correct=False,
        order_correct=False,
        chart_correct=False,
        repair_count=0,
        error_message=error_message,
    )


def run_single_case(
    case: dict[str, Any],
    current_index: int,
    total_count: int,
) -> dict[str, Any]:
    """
    执行并评分单道评估题。
    """

    case_id = case["case_id"]
    dataset_file = case[
        "dataset_file"
    ]
    question = case["question"]

    dataset_path = (
        DATASET_DIR / dataset_file
    )

    print()
    print("=" * 70)
    print(
        f"[{current_index}/{total_count}] "
        f"运行评估题：{case_id}"
    )
    print(f"数据集：{dataset_file}")
    print(f"问题：{question}")
    print("=" * 70)

    if not dataset_path.exists():
        error_message = (
            f"评估数据集不存在："
            f"{dataset_path}"
        )

        evaluation = (
            create_failed_result(
                case,
                error_message,
            )
        )

        return {
            **evaluation.to_dict(),
            "question": question,
            "duration_seconds": 0.0,
            "agent_response": None,
        }

    start_time = time.perf_counter()

    response = None

    try:
        response = (
            data_analysis_agent.analyze(
                file_path=str(
                    dataset_path
                ),
                question=question,
            )
        )

        duration_seconds = (
            time.perf_counter()
            - start_time
        )

        evaluation = evaluate_response(
            case,
            response,
        )

    except Exception as exc:
        duration_seconds = (
            time.perf_counter()
            - start_time
        )

        evaluation = (
            create_failed_result(
                case,
                (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
            )
        )

    print(
        "执行状态：",
        (
            "成功"
            if evaluation.execution_success
            else "失败"
        ),
    )

    print(
        "结果正确：",
        (
            "是"
            if evaluation.result_correct
            else "否"
        ),
    )

    print(
        "图表检查：",
        (
            "通过"
            if evaluation.chart_correct
            else "未通过"
        ),
    )

    print(
        "修复次数：",
        evaluation.repair_count,
    )

    print(
        "最终评分：",
        (
            "PASS"
            if evaluation.passed
            else "FAIL"
        ),
    )

    print(
        "耗时：",
        f"{duration_seconds:.2f}秒",
    )

    if evaluation.error_message:
        print(
            "失败原因：",
            evaluation.error_message,
        )

    return {
        **evaluation.to_dict(),
        "question": question,
        "duration_seconds": round(
            duration_seconds,
            3,
        ),
        "agent_response": (
            serialize_value(response)
        ),
    }


def calculate_metrics(
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    根据全部题目结果计算总体指标。
    """

    total_cases = len(results)

    if total_cases == 0:
        return {
            "total_cases": 0,
        }

    passed_count = sum(
        result["passed"]
        for result in results
    )

    execution_success_count = sum(
        result["execution_success"]
        for result in results
    )

    result_correct_count = sum(
        result["result_correct"]
        for result in results
    )

    first_pass_success_count = sum(
        (
            result["passed"]
            and result["repair_count"] == 0
        )
        for result in results
    )

    repaired_case_count = sum(
        result["repair_count"] > 0
        for result in results
    )

    repair_success_count = sum(
        (
            result["passed"]
            and result["repair_count"] > 0
        )
        for result in results
    )

    chart_cases = [
        result
        for result in results
        if result["case_id"]
        in {
            "sales_001",
            "sales_002",
            "sales_004",
            "employees_001",
            "employees_003",
            "employees_005",
            "orders_001",
            "orders_003",
            "orders_005",
        }
    ]

    chart_success_count = sum(
        result["chart_correct"]
        for result in chart_cases
    )

    total_duration = sum(
        result["duration_seconds"]
        for result in results
    )

    total_repairs = sum(
        result["repair_count"]
        for result in results
    )

    def percentage(
        numerator: int,
        denominator: int,
    ) -> float:
        """
        计算百分比。
        """

        if denominator == 0:
            return 0.0

        return round(
            numerator
            / denominator
            * 100,
            2,
        )

    return {
        "total_cases": total_cases,
        "passed_cases": passed_count,
        "pass_rate": percentage(
            passed_count,
            total_cases,
        ),
        "execution_success_cases": (
            execution_success_count
        ),
        "execution_success_rate": (
            percentage(
                execution_success_count,
                total_cases,
            )
        ),
        "correct_result_cases": (
            result_correct_count
        ),
        "result_accuracy": percentage(
            result_correct_count,
            total_cases,
        ),
        "first_pass_success_cases": (
            first_pass_success_count
        ),
        "first_pass_success_rate": (
            percentage(
                first_pass_success_count,
                total_cases,
            )
        ),
        "repaired_cases": (
            repaired_case_count
        ),
        "repair_success_cases": (
            repair_success_count
        ),
        "repair_success_rate": (
            percentage(
                repair_success_count,
                repaired_case_count,
            )
        ),
        "chart_cases": len(
            chart_cases
        ),
        "chart_success_cases": (
            chart_success_count
        ),
        "chart_success_rate": (
            percentage(
                chart_success_count,
                len(chart_cases),
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
    在终端打印总体评估结果。
    """

    print()
    print("=" * 70)
    print("DataPilot自动评估结果")
    print("=" * 70)

    print(
        f"评估题数："
        f"{metrics['total_cases']}"
    )

    print(
        f"通过题数："
        f"{metrics['passed_cases']}"
    )

    print(
        f"总体通过率："
        f"{metrics['pass_rate']}%"
    )

    print(
        f"代码执行成功率："
        f"{metrics['execution_success_rate']}%"
    )

    print(
        f"结果正确率："
        f"{metrics['result_accuracy']}%"
    )

    print(
        f"首次执行成功率："
        f"{metrics['first_pass_success_rate']}%"
    )

    print(
        f"发生修复的题数："
        f"{metrics['repaired_cases']}"
    )

    print(
        f"修复成功率："
        f"{metrics['repair_success_rate']}%"
    )

    print(
        f"图表生成成功率："
        f"{metrics['chart_success_rate']}%"
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
    将详细评估结果保存为JSON报告。
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
        / f"evaluation_{timestamp}.json"
    )

    report = {
        "benchmark_name": (
            "DataPilot Basic Evaluation"
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
            "运行DataPilot自动评估"
        )
    )

    parser.add_argument(
        "--case-id",
        type=str,
        default=None,
        help=(
            "只运行指定题目，"
            "例如sales_001"
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "只运行前N道题，"
            "适合快速测试"
        ),
    )

    return parser.parse_args()


def main() -> None:
    """
    自动评估入口。
    """

    arguments = parse_arguments()

    all_cases = (
        load_evaluation_cases()
    )

    selected_cases = select_cases(
        cases=all_cases,
        case_id=arguments.case_id,
        limit=arguments.limit,
    )

    if not selected_cases:
        raise RuntimeError(
            "没有需要运行的评估题目"
        )

    print(
        "准备运行DataPilot自动评估"
    )

    print(
        f"本次题目数量："
        f"{len(selected_cases)}"
    )

    results = []

    for index, case in enumerate(
        selected_cases,
        start=1,
    ):
        result = run_single_case(
            case=case,
            current_index=index,
            total_count=len(
                selected_cases
            ),
        )

        results.append(result)

    metrics = calculate_metrics(
        results
    )

    print_summary(metrics)

    report_path = save_report(
        results,
        metrics,
    )

    print(
        f"详细评估报告已保存："
        f"{report_path}"
    )


if __name__ == "__main__":
    main()