import json
from datetime import datetime
from pathlib import Path
from typing import Any


EVALUATION_DIR = Path(
    __file__
).resolve().parent

RESULTS_DIR = (
    EVALUATION_DIR / "results"
)

OUTPUT_PATH = (
    RESULTS_DIR
    / "EVALUATION_REPORT.md"
)


def load_json(
    file_path: Path,
) -> dict[str, Any]:
    """
    读取JSON报告。
    """

    with file_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def find_latest_file(
    pattern: str,
) -> Path:
    """
    查找指定类型的最新评估报告。
    """

    files = list(
        RESULTS_DIR.glob(pattern)
    )

    if not files:
        raise FileNotFoundError(
            "找不到评估报告："
            f"{pattern}"
        )

    return max(
        files,
        key=lambda path: (
            path.stat().st_mtime
        ),
    )


def status_text(
    value: bool,
) -> str:
    """
    将布尔值转换成报告状态。
    """

    return "PASS" if value else "FAIL"


def build_basic_table(
    results: list[dict[str, Any]],
) -> str:
    """
    生成基础评估明细表。
    """

    lines = [
        (
            "| Case | Dataset | Category | "
            "Execution | Result | Chart | "
            "Repairs | Time |"
        ),
        (
            "|---|---|---|---:|---:|"
            "---:|---:|---:|"
        ),
    ]

    for result in results:
        lines.append(
            "| "
            f"{result['case_id']} | "
            f"{result['dataset_file']} | "
            f"{result['category']} | "
            f"{status_text(result['execution_success'])} | "
            f"{status_text(result['result_correct'])} | "
            f"{status_text(result['chart_correct'])} | "
            f"{result['repair_count']} | "
            f"{result['duration_seconds']:.2f}s |"
        )

    return "\n".join(lines)


def build_fault_table(
    results: list[dict[str, Any]],
) -> str:
    """
    生成故障评估明细表。
    """

    lines = [
        (
            "| Case | Fault Type | "
            "Expected Error | Repair | "
            "Correct After Repair | "
            "Repairs | Time |"
        ),
        (
            "|---|---|---|---:|---:|"
            "---:|---:|"
        ),
    ]

    for result in results:
        lines.append(
            "| "
            f"{result['fault_case_id']} | "
            f"{result['fault_type']} | "
            f"{result['expected_error_type']} | "
            f"{status_text(result['repair_success'])} | "
            f"{status_text(result['result_correct_after_repair'])} | "
            f"{result['repair_count']} | "
            f"{result['duration_seconds']:.2f}s |"
        )

    return "\n".join(lines)


def build_failure_section(
    basic_results: list[
        dict[str, Any]
    ],
    fault_results: list[
        dict[str, Any]
    ],
) -> str:
    """
    汇总失败任务。
    """

    failures = []

    for result in basic_results:
        if not result["passed"]:
            failures.append(
                (
                    result["case_id"],
                    result.get(
                        "error_message"
                    ),
                )
            )

    for result in fault_results:
        if not result["passed"]:
            failures.append(
                (
                    result[
                        "fault_case_id"
                    ],
                    result.get(
                        "error_message"
                    ),
                )
            )

    if not failures:
        return (
            "本次基础评估与故障评估"
            "均未出现失败任务。"
        )

    return "\n".join(
        (
            f"- `{case_id}`："
            f"{error or '未知错误'}"
        )
        for case_id, error in failures
    )


def main() -> None:
    """
    生成统一Markdown评估报告。
    """

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    basic_path = find_latest_file(
        "evaluation_*.json"
    )

    fault_path = find_latest_file(
        "fault_evaluation_*.json"
    )

    basic_report = load_json(
        basic_path
    )

    fault_report = load_json(
        fault_path
    )

    basic_metrics = basic_report[
        "metrics"
    ]

    fault_metrics = fault_report[
        "metrics"
    ]

    basic_results = basic_report[
        "results"
    ]

    fault_results = fault_report[
        "results"
    ]

    generated_time = (
        datetime.now().isoformat(
            timespec="seconds"
        )
    )

    report = f"""# DataPilot Evaluation Report

> Automated evaluation for executable data analysis and code self-repair.

生成时间：`{generated_time}`

## 评估设计

DataPilot 使用固定数据集、预计算标准答案和规则化评分器，
评估 Agent 的分析规划、Python 代码生成、代码执行、
结构化结果正确性、排序一致性和图表生成能力。

系统还使用独立的故障评估 LangGraph，在代码生成与执行之间
注入字段拼写错误、缺失字段、未定义变量和类型错误，
验证代码诊断及自动修复能力。

## 基础能力评估

| Metric | Result |
|---|---:|
| Total Cases | {basic_metrics['total_cases']} |
| Passed Cases | {basic_metrics['passed_cases']} |
| Pass Rate | {basic_metrics['pass_rate']}% |
| Execution Success Rate | {basic_metrics['execution_success_rate']}% |
| Result Accuracy | {basic_metrics['result_accuracy']}% |
| First-pass Success Rate | {basic_metrics['first_pass_success_rate']}% |
| Chart Success Rate | {basic_metrics['chart_success_rate']}% |
| Average Repair Count | {basic_metrics['average_repair_count']} |
| Average Duration | {basic_metrics['average_duration_seconds']}s |

### 基础任务明细

{build_basic_table(basic_results)}

## 故障注入与自动修复评估

故障评估工作流：

```text
generate_code
    ↓
inject_fault
    ↓
execute_code ── failure ──→ repair_code
    ↑                           │
    └───────────────────────────┘

```

## 故障评估指标

| Metric | Result |
|---|---:|
| Total Fault Cases | {fault_metrics['total_cases']} |
| Passed Cases | {fault_metrics['passed_cases']} |
| Final Pass Rate | {fault_metrics['pass_rate']}% |
| Fault Injection Rate | {fault_metrics['fault_injection_rate']}% |
| Failure Trigger Rate | {fault_metrics['failure_trigger_rate']}% |
| Error Type Match Rate | {fault_metrics['error_type_match_rate']}% |
| Repair Trigger Rate | {fault_metrics['repair_trigger_rate']}% |
| Repair Success Rate | {fault_metrics['repair_success_rate']}% |
| Accuracy After Repair | {fault_metrics['result_accuracy_after_repair']}% |
| Average Repair Count | {fault_metrics['average_repair_count']} |
| Average Duration | {fault_metrics['average_duration_seconds']}s |

### 故障任务明细

{build_fault_table(fault_results)}

## 自动评分规则

基础评估采用确定性规则完成评分：

- 检查Python代码是否执行成功；
- 检查结构化结果所需字段；
- 检查结果行数和分组对象；
- 在允许误差范围内比较数值；
- 检查排序是否符合问题要求；
- 检查图表文件是否成功生成。

故障评估还要求：

- 故障注入节点成功运行；
- 第一次代码执行产生预期异常；
- LangGraph进入repair_code节点；
- 修复后的代码重新执行成功；
- 修复后的结果仍与标准答案一致。

## 失败任务

{build_failure_section(
    basic_results,
    fault_results,
)}

## 原始评估文件

- 基础评估：`{basic_path.name}`
- 故障评估：`{fault_path.name}`

## 说明

本报告反映DataPilot在当前固定基础测试集与故障注入
测试集上的表现，不代表系统对任意数据和任意问题
都具有相同的准确率。
"""

    OUTPUT_PATH.write_text(
        report,
        encoding="utf-8",
    )

    print(
        "评估报告生成成功："
        f"{OUTPUT_PATH}"
    )

    print(
        "基础评估来源："
        f"{basic_path.name}"
    )

    print(
        "故障评估来源："
        f"{fault_path.name}"
    )


if __name__ == "__main__":
    main()
