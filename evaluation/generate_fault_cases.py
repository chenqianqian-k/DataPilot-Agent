import json
from pathlib import Path
from typing import Any


EVALUATION_DIR = Path(
    __file__
).resolve().parent

BASIC_CASES_PATH = (
    EVALUATION_DIR / "cases.json"
)

FAULT_CASES_PATH = (
    EVALUATION_DIR
    / "fault_cases.json"
)


def load_basic_cases(
) -> dict[str, dict[str, Any]]:
    """
    读取基础评估题，并按照case_id建立索引。
    """

    if not BASIC_CASES_PATH.exists():
        raise FileNotFoundError(
            "找不到基础评估题库："
            f"{BASIC_CASES_PATH}"
        )

    with BASIC_CASES_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        benchmark = json.load(file)

    return {
        case["case_id"]: case
        for case in benchmark["cases"]
    }


def main() -> None:
    """
    生成故障注入专项评估题库。
    """

    basic_cases = load_basic_cases()

    fault_definitions = [
        {
            "fault_case_id": (
                "fault_sales_001"
            ),
            "base_case_id": "sales_001",
            "fault_injection": {
                "fault_type": (
                    "column_typo"
                ),
                "target_text": (
                    "sales_amount"
                ),
                "replacement_text": (
                    "sales_amout"
                ),
            },
            "expected_error_type": (
                "KeyError"
            ),
        },
        {
            "fault_case_id": (
                "fault_sales_002"
            ),
            "base_case_id": "sales_002",
            "fault_injection": {
                "fault_type": (
                    "type_error"
                ),
            },
            "expected_error_type": (
                "TypeError"
            ),
        },
        {
            "fault_case_id": (
                "fault_sales_004"
            ),
            "base_case_id": "sales_004",
            "fault_injection": {
                "fault_type": (
                    "undefined_variable"
                ),
            },
            "expected_error_type": (
                "NameError"
            ),
        },
        {
            "fault_case_id": (
                "fault_employees_001"
            ),
            "base_case_id": (
                "employees_001"
            ),
            "fault_injection": {
                "fault_type": (
                    "missing_column"
                ),
            },
            "expected_error_type": (
                "KeyError"
            ),
        },
        {
            "fault_case_id": (
                "fault_employees_002"
            ),
            "base_case_id": (
                "employees_002"
            ),
            "fault_injection": {
                "fault_type": (
                    "column_typo"
                ),
                "target_text": (
                    "monthly_salary"
                ),
                "replacement_text": (
                    "montly_salary"
                ),
            },
            "expected_error_type": (
                "KeyError"
            ),
        },
        {
            "fault_case_id": (
                "fault_orders_001"
            ),
            "base_case_id": "orders_001",
            "fault_injection": {
                "fault_type": (
                    "undefined_variable"
                ),
            },
            "expected_error_type": (
                "NameError"
            ),
        },
        {
            "fault_case_id": (
                "fault_orders_002"
            ),
            "base_case_id": "orders_002",
            "fault_injection": {
                "fault_type": (
                    "column_typo"
                ),
                "target_text": (
                    "order_amount"
                ),
                "replacement_text": (
                    "order_amout"
                ),
            },
            "expected_error_type": (
                "KeyError"
            ),
        },
        {
            "fault_case_id": (
                "fault_orders_005"
            ),
            "base_case_id": "orders_005",
            "fault_injection": {
                "fault_type": (
                    "missing_column"
                ),
            },
            "expected_error_type": (
                "KeyError"
            ),
        },
    ]

    fault_cases = []

    for definition in (
        fault_definitions
    ):
        base_case_id = definition[
            "base_case_id"
        ]

        if base_case_id not in basic_cases:
            raise ValueError(
                "基础题库中不存在题目："
                f"{base_case_id}"
            )

        base_case = basic_cases[
            base_case_id
        ]

        fault_case = {
            **base_case,
            **definition,
        }

        fault_cases.append(
            fault_case
        )

    output = {
        "benchmark_name": (
            "DataPilot Fault Injection "
            "Evaluation"
        ),
        "version": "1.0",
        "description": (
            "通过确定性故障注入评估"
            "DataPilot的代码诊断与"
            "自动修复能力"
        ),
        "total_cases": len(
            fault_cases
        ),
        "fault_cases": fault_cases,
    }

    with FAULT_CASES_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(
        "故障专项题库生成完成："
        f"{FAULT_CASES_PATH}"
    )

    print(
        "故障评估题数："
        f"{len(fault_cases)}"
    )

    print("\n故障分布：")

    for case in fault_cases:
        fault_type = case[
            "fault_injection"
        ]["fault_type"]

        print(
            f"- {case['fault_case_id']}: "
            f"{case['base_case_id']} → "
            f"{fault_type}"
        )


if __name__ == "__main__":
    main()