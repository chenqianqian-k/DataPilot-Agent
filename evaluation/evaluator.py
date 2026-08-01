import json
import math
from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


EVALUATION_DIR = Path(__file__).resolve().parent
CASES_PATH = EVALUATION_DIR / "cases.json"


@dataclass
class EvaluationResult:
    """
    单道评估题的评分结果。
    """

    case_id: str
    dataset_file: str
    category: str

    passed: bool
    execution_success: bool
    result_correct: bool
    columns_correct: bool
    order_correct: bool
    chart_correct: bool

    repair_count: int
    error_message: str | None

    def to_dict(self) -> dict[str, Any]:
        """
        将评分结果转换为普通字典。
        """

        return asdict(self)


def load_evaluation_cases() -> list[dict[str, Any]]:
    """
    从cases.json读取全部评估题。
    """

    if not CASES_PATH.exists():
        raise FileNotFoundError(
            f"找不到评估题库：{CASES_PATH}，"
            "请先运行："
            "python -m evaluation.generate_cases"
        )

    with CASES_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        benchmark = json.load(file)

    return benchmark["cases"]


def convert_to_dict(
    value: Any,
) -> Any:
    """
    将Pydantic对象等结构转换为普通Python对象。

    DataPilot返回的AnalysisResponse和
    AnalysisExecution通常是Pydantic对象，
    需要先通过model_dump转换为字典。
    """

    if value is None:
        return None

    if hasattr(value, "model_dump"):
        return value.model_dump()

    if hasattr(value, "dict"):
        return value.dict()

    return value


def normalize_records(
    value: Any,
) -> list[dict[str, Any]]:
    """
    将Agent返回的不同形式结果统一转换为：

    [
        {"region": "华东", "total_sales": 1000},
        {"region": "华南", "total_sales": 800}
    ]

    支持：
    1. DataFrame
    2. list[dict]
    3. dict
    4. JSON字符串
    5. 包含records、data或result的嵌套字典
    """

    value = convert_to_dict(value)

    if value is None:
        return []

    if isinstance(value, pd.DataFrame):
        return value.to_dict(
            orient="records"
        )

    if isinstance(value, str):
        try:
            parsed_value = json.loads(
                value
            )

            return normalize_records(
                parsed_value
            )

        except json.JSONDecodeError:
            return []

    if isinstance(value, list):
        records = []

        for item in value:
            item = convert_to_dict(item)

            if isinstance(item, dict):
                records.append(item)

        return records

    if isinstance(value, dict):
        # 某些执行结果会再包装一层
        for key in [
            "records",
            "data",
            "result",
            "result_preview",
        ]:
            if key in value:
                nested_records = (
                    normalize_records(
                        value[key]
                    )
                )

                if nested_records:
                    return nested_records

        # 普通字典本身可以看作一行结果
        return [value]

    return []


def extract_agent_result(
    response: Any,
) -> tuple[
    bool,
    list[dict[str, Any]],
    bool,
    int,
    str | None,
]:
    """
    从DataPilot的AnalysisResponse中提取评分信息。

    返回：
    execution_success
    actual_records
    chart_generated
    repair_count
    error_message
    """

    response_data = convert_to_dict(
        response
    )

    if not isinstance(
        response_data,
        dict,
    ):
        return (
            False,
            [],
            False,
            0,
            "Agent响应不是有效字典",
        )

    status = response_data.get(
        "status",
        "failed",
    )

    repair_count = int(
        response_data.get(
            "repair_count",
            0,
        )
        or 0
    )

    error_message = response_data.get(
        "error_message"
    )

    execution = convert_to_dict(
        response_data.get("execution")
    )

    if not isinstance(
        execution,
        dict,
    ):
        return (
            status == "completed",
            [],
            False,
            repair_count,
            error_message
            or "响应中缺少execution",
        )

    execution_success = bool(
        execution.get(
            "success",
            status == "completed",
        )
    )

    # 尝试从多个可能字段中提取分析结果
    actual_records = []

    result_field_names = [
        "result",
        "result_preview",
        "output",
        "data",
    ]

    for field_name in result_field_names:
        if field_name not in execution:
            continue

        actual_records = (
            normalize_records(
                execution[field_name]
            )
        )

        if actual_records:
            break

    # 如果execution中没有，则尝试响应顶层
    if not actual_records:
        for field_name in result_field_names:
            if field_name not in response_data:
                continue

            actual_records = (
                normalize_records(
                    response_data[
                        field_name
                    ]
                )
            )

            if actual_records:
                break

    # 检查是否生成图表
    # =========================
    # 检查是否生成图表
    # =========================

    chart_generated = False

    # 兼容其他可能使用的图表路径字段
    chart_field_names = [
        "chart_path",
        "chart_paths",
        "figure_path",
        "figure_paths",
        "visualization_path",
        "plot_path",
    ]

    for field_name in chart_field_names:
        field_value = execution.get(
            field_name
        )

        if field_value:
            chart_generated = True
            break

    # DataPilot实际使用generated_files
    # 保存生成的图表或报告文件路径
    generated_files = execution.get(
        "generated_files",
        [],
    )

    # 常见图表文件扩展名
    chart_extensions = {
        ".html",
        ".png",
        ".jpg",
        ".jpeg",
        ".svg",
        ".webp",
        ".pdf",
    }

    if isinstance(
        generated_files,
        str,
    ):
        generated_files = [
            generated_files
        ]

    if isinstance(
        generated_files,
        list,
    ):
        for generated_file in (
            generated_files
        ):
            if not generated_file:
                continue

            file_suffix = (
                Path(
                    str(generated_file)
                )
                .suffix
                .lower()
            )

            if (
                file_suffix
                in chart_extensions
            ):
                chart_generated = True
                break

    # 兼容可能使用artifacts保存文件的情况
    artifacts = execution.get(
        "artifacts"
    )

    if (
        not chart_generated
        and artifacts
    ):
        chart_generated = True

    return (
        execution_success,
        actual_records,
        chart_generated,
        repair_count,
        error_message,
    )


def values_are_equal(
    actual: Any,
    expected: Any,
    tolerance: float,
) -> bool:
    """
    比较两个值是否相等。

    数值使用允许误差比较；
    字符串使用去除首尾空格后的精确比较。
    """

    if actual is None:
        return expected is None

    if expected is None:
        return actual is None

    try:
        actual_number = float(actual)
        expected_number = float(expected)

        return math.isclose(
            actual_number,
            expected_number,
            rel_tol=0,
            abs_tol=tolerance,
        )

    except (
        TypeError,
        ValueError,
    ):
        return (
            str(actual).strip()
            == str(expected).strip()
        )


def compare_table_result(
    actual_records: list[
        dict[str, Any]
    ],
    expected_config: dict[str, Any],
) -> tuple[
    bool,
    bool,
    bool,
    str | None,
]:
    """
    对比Agent表格结果和标准答案。

    返回：
    result_correct
    columns_correct
    order_correct
    error_message
    """

    expected_records = (
        expected_config["records"]
    )

    key_columns = expected_config.get(
        "key_columns",
        [],
    )

    value_columns = expected_config.get(
        "value_columns",
        [],
    )

    tolerance = float(
        expected_config.get(
            "tolerance",
            0,
        )
    )

    required_columns = (
        key_columns
        + value_columns
    )

    if not actual_records:
        return (
            False,
            False,
            False,
            "Agent没有返回可比较的结构化结果",
        )

    # 检查每一行是否包含所需字段
    columns_correct = all(
        all(
            column in record
            for column in required_columns
        )
        for record in actual_records
    )

    if not columns_correct:
        actual_columns = sorted(
            {
                column
                for record in actual_records
                for column in record.keys()
            }
        )

        return (
            False,
            False,
            False,
            (
                "结果字段不正确。"
                f"需要字段：{required_columns}；"
                f"实际字段：{actual_columns}"
            ),
        )

    if (
        len(actual_records)
        != len(expected_records)
    ):
        return (
            False,
            True,
            False,
            (
                "结果行数不正确。"
                f"标准答案{len(expected_records)}行，"
                f"实际返回{len(actual_records)}行"
            ),
        )

    def build_key(
        record: dict[str, Any],
    ) -> tuple[str, ...]:
        """
        根据key_columns构造一行数据的唯一键。
        """

        return tuple(
            str(
                record.get(column)
            ).strip()
            for column in key_columns
        )

    expected_map = {
        build_key(record): record
        for record in expected_records
    }

    actual_map = {
        build_key(record): record
        for record in actual_records
    }

    if (
        set(actual_map.keys())
        != set(expected_map.keys())
    ):
        return (
            False,
            True,
            False,
            (
                "结果中的分组对象不正确。"
                f"标准键：{list(expected_map.keys())}；"
                f"实际键：{list(actual_map.keys())}"
            ),
        )

    # 检查各数值字段
    value_errors = []

    for record_key, expected_record in (
        expected_map.items()
    ):
        actual_record = actual_map[
            record_key
        ]

        for column in value_columns:
            actual_value = (
                actual_record.get(column)
            )

            expected_value = (
                expected_record.get(column)
            )

            if not values_are_equal(
                actual_value,
                expected_value,
                tolerance,
            ):
                value_errors.append(
                    (
                        f"{record_key}的{column}："
                        f"期望{expected_value}，"
                        f"实际{actual_value}"
                    )
                )

    expected_order = [
        build_key(record)
        for record in expected_records
    ]

    actual_order = [
        build_key(record)
        for record in actual_records
    ]

    order_correct = (
        actual_order
        == expected_order
    )

    if value_errors:
        return (
            False,
            True,
            order_correct,
            "；".join(
                value_errors[:5]
            ),
        )

    if not order_correct:
        return (
            False,
            True,
            False,
            "计算结果正确，但排序顺序不正确",
        )

    return (
        True,
        True,
        True,
        None,
    )


def evaluate_response(
    case: dict[str, Any],
    response: Any,
) -> EvaluationResult:
    """
    对DataPilot的一次完整响应进行评分。
    """

    (
        execution_success,
        actual_records,
        chart_generated,
        repair_count,
        execution_error,
    ) = extract_agent_result(
        response
    )

    expected_config = case[
        "expected"
    ]

    expected_type = (
        expected_config.get("type")
    )

    if expected_type == "table":
        (
            result_correct,
            columns_correct,
            order_correct,
            compare_error,
        ) = compare_table_result(
            actual_records,
            expected_config,
        )

    else:
        result_correct = False
        columns_correct = False
        order_correct = False
        compare_error = (
            "暂不支持的标准答案类型："
            f"{expected_type}"
        )

    chart_required = bool(
        case.get(
            "chart_required",
            False,
        )
    )

    chart_correct = (
        chart_generated
        if chart_required
        else True
    )

    passed = (
        execution_success
        and result_correct
        and chart_correct
    )

    error_parts = []

    if execution_error:
        error_parts.append(
            str(execution_error)
        )

    if compare_error:
        error_parts.append(
            compare_error
        )

    if (
        chart_required
        and not chart_generated
    ):
        error_parts.append(
            "题目要求生成图表，但未检测到图表"
        )

    error_message = (
        "；".join(error_parts)
        if error_parts
        else None
    )

    return EvaluationResult(
        case_id=case["case_id"],
        dataset_file=(
            case["dataset_file"]
        ),
        category=case["category"],
        passed=passed,
        execution_success=(
            execution_success
        ),
        result_correct=result_correct,
        columns_correct=columns_correct,
        order_correct=order_correct,
        chart_correct=chart_correct,
        repair_count=repair_count,
        error_message=error_message,
    )