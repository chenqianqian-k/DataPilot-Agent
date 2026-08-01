import json
from pathlib import Path
from typing import Any

import pandas as pd


EVALUATION_DIR = Path(__file__).resolve().parent
DATASET_DIR = EVALUATION_DIR / "datasets"
CASES_PATH = EVALUATION_DIR / "cases.json"


def dataframe_to_records(
    dataframe: pd.DataFrame,
) -> list[dict[str, Any]]:
    """
    将DataFrame转换为可以写入JSON的记录列表。

    同时将Pandas、NumPy的数据类型转换为
    Python原生数据类型，避免JSON序列化报错。
    """

    dataframe = dataframe.copy()

    for column in dataframe.columns:
        if pd.api.types.is_float_dtype(
            dataframe[column]
        ):
            dataframe[column] = (
                dataframe[column].round(2)
            )

    return json.loads(
        dataframe.to_json(
            orient="records",
            force_ascii=False,
        )
    )


def build_sales_cases(
    sales: pd.DataFrame,
) -> list[dict[str, Any]]:
    """
    创建销售数据集对应的5道评估题。
    """

    sales["order_date"] = pd.to_datetime(
        sales["order_date"]
    )

    # 题目1：地区销售额
    region_sales = (
        sales.groupby(
            "region",
            as_index=False,
        )["sales_amount"]
        .sum()
        .rename(
            columns={
                "sales_amount": (
                    "total_sales"
                )
            }
        )
        .sort_values(
            "total_sales",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    # 题目2：月度销售趋势
    monthly_sales = (
        sales.assign(
            month=(
                sales["order_date"]
                .dt.strftime("%Y-%m")
            )
        )
        .groupby(
            "month",
            as_index=False,
        )["sales_amount"]
        .sum()
        .rename(
            columns={
                "sales_amount": (
                    "total_sales"
                )
            }
        )
        .sort_values("month")
        .reset_index(drop=True)
    )

    # 题目3：类别利润
    category_profit = (
        sales.groupby(
            "category",
            as_index=False,
        )["profit"]
        .sum()
        .rename(
            columns={
                "profit": "total_profit"
            }
        )
        .sort_values(
            "total_profit",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    # 题目4：销售人员销售额排名
    salesperson_sales = (
        sales.groupby(
            "salesperson",
            as_index=False,
        )["sales_amount"]
        .sum()
        .rename(
            columns={
                "sales_amount": (
                    "total_sales"
                )
            }
        )
        .sort_values(
            "total_sales",
            ascending=False,
        )
        .head(3)
        .reset_index(drop=True)
    )

    # 题目5：地区平均订单金额
    region_average = (
        sales.groupby(
            "region",
            as_index=False,
        )["sales_amount"]
        .mean()
        .rename(
            columns={
                "sales_amount": (
                    "average_sales"
                )
            }
        )
        .sort_values(
            "average_sales",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    return [
        {
            "case_id": "sales_001",
            "dataset_file": "sales.csv",
            "category": "group_aggregation",
            "question": (
                "统计不同地区的销售总额，"
                "按照销售总额从高到低排序，"
                "并生成柱状图。结果包含region和"
                "total_sales两列。"
            ),
            "expected": {
                "type": "table",
                "records": (
                    dataframe_to_records(
                        region_sales
                    )
                ),
                "key_columns": ["region"],
                "value_columns": [
                    "total_sales"
                ],
                "tolerance": 0.01,
            },
            "chart_required": True,
        },
        {
            "case_id": "sales_002",
            "dataset_file": "sales.csv",
            "category": "time_series",
            "question": (
                "统计每个月的销售总额，"
                "按照月份升序排列，并生成折线图。"
                "结果包含month和total_sales两列，"
                "month格式为YYYY-MM。"
            ),
            "expected": {
                "type": "table",
                "records": (
                    dataframe_to_records(
                        monthly_sales
                    )
                ),
                "key_columns": ["month"],
                "value_columns": [
                    "total_sales"
                ],
                "tolerance": 0.01,
            },
            "chart_required": True,
        },
        {
            "case_id": "sales_003",
            "dataset_file": "sales.csv",
            "category": "ranking",
            "question": (
                "统计不同产品类别的利润总额，"
                "按照利润从高到低排序。"
                "结果包含category和"
                "total_profit两列。"
            ),
            "expected": {
                "type": "table",
                "records": (
                    dataframe_to_records(
                        category_profit
                    )
                ),
                "key_columns": ["category"],
                "value_columns": [
                    "total_profit"
                ],
                "tolerance": 0.01,
            },
            "chart_required": False,
        },
        {
            "case_id": "sales_004",
            "dataset_file": "sales.csv",
            "category": "top_n",
            "question": (
                "找出销售总额最高的前3名销售人员，"
                "按照销售总额从高到低排序，并生成"
                "柱状图。结果包含salesperson和"
                "total_sales两列。"
            ),
            "expected": {
                "type": "table",
                "records": (
                    dataframe_to_records(
                        salesperson_sales
                    )
                ),
                "key_columns": ["salesperson"],
                "value_columns": [
                    "total_sales"
                ],
                "tolerance": 0.01,
            },
            "chart_required": True,
        },
        {
            "case_id": "sales_005",
            "dataset_file": "sales.csv",
            "category": "average",
            "question": (
                "计算不同地区的平均单笔销售额，"
                "按照平均销售额从高到低排序。"
                "结果包含region和average_sales两列。"
            ),
            "expected": {
                "type": "table",
                "records": (
                    dataframe_to_records(
                        region_average
                    )
                ),
                "key_columns": ["region"],
                "value_columns": [
                    "average_sales"
                ],
                "tolerance": 0.01,
            },
            "chart_required": False,
        },
    ]


def build_employee_cases(
    employees: pd.DataFrame,
) -> list[dict[str, Any]]:
    """
    创建员工数据集对应的5道评估题。
    """

    department_count = (
        employees.groupby(
            "department",
            as_index=False,
        )
        .size()
        .rename(
            columns={
                "size": "employee_count"
            }
        )
        .sort_values(
            "employee_count",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    department_salary = (
        employees.groupby(
            "department",
            as_index=False,
        )["monthly_salary"]
        .mean()
        .rename(
            columns={
                "monthly_salary": (
                    "average_salary"
                )
            }
        )
        .sort_values(
            "average_salary",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    education_salary = (
        employees.groupby(
            "education",
            as_index=False,
        )["monthly_salary"]
        .mean()
        .rename(
            columns={
                "monthly_salary": (
                    "average_salary"
                )
            }
        )
        .sort_values(
            "average_salary",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    department_performance = (
        employees.groupby(
            "department",
            as_index=False,
        )["performance_score"]
        .mean()
        .rename(
            columns={
                "performance_score": (
                    "average_performance"
                )
            }
        )
        .sort_values(
            "average_performance",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    city_count = (
        employees.groupby(
            "city",
            as_index=False,
        )
        .size()
        .rename(
            columns={
                "size": "employee_count"
            }
        )
        .sort_values(
            "employee_count",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    return [
        {
            "case_id": "employees_001",
            "dataset_file": "employees.xlsx",
            "category": "count",
            "question": (
                "统计每个部门的员工人数，"
                "按照人数从高到低排序，并生成柱状图。"
                "结果包含department和"
                "employee_count两列。"
            ),
            "expected": {
                "type": "table",
                "records": (
                    dataframe_to_records(
                        department_count
                    )
                ),
                "key_columns": ["department"],
                "value_columns": [
                    "employee_count"
                ],
                "tolerance": 0,
            },
            "chart_required": True,
        },
        {
            "case_id": "employees_002",
            "dataset_file": "employees.xlsx",
            "category": "average",
            "question": (
                "计算每个部门的平均月薪，"
                "按照平均月薪从高到低排序。"
                "结果包含department和"
                "average_salary两列。"
            ),
            "expected": {
                "type": "table",
                "records": (
                    dataframe_to_records(
                        department_salary
                    )
                ),
                "key_columns": ["department"],
                "value_columns": [
                    "average_salary"
                ],
                "tolerance": 0.01,
            },
            "chart_required": False,
        },
        {
            "case_id": "employees_003",
            "dataset_file": "employees.xlsx",
            "category": "group_comparison",
            "question": (
                "比较不同学历员工的平均月薪，"
                "按照平均月薪从高到低排序，"
                "并生成柱状图。结果包含education和"
                "average_salary两列。"
            ),
            "expected": {
                "type": "table",
                "records": (
                    dataframe_to_records(
                        education_salary
                    )
                ),
                "key_columns": ["education"],
                "value_columns": [
                    "average_salary"
                ],
                "tolerance": 0.01,
            },
            "chart_required": True,
        },
        {
            "case_id": "employees_004",
            "dataset_file": "employees.xlsx",
            "category": "performance",
            "question": (
                "计算各部门的平均绩效分数，"
                "按照平均绩效从高到低排序。"
                "结果包含department和"
                "average_performance两列。"
            ),
            "expected": {
                "type": "table",
                "records": (
                    dataframe_to_records(
                        department_performance
                    )
                ),
                "key_columns": ["department"],
                "value_columns": [
                    "average_performance"
                ],
                "tolerance": 0.01,
            },
            "chart_required": False,
        },
        {
            "case_id": "employees_005",
            "dataset_file": "employees.xlsx",
            "category": "distribution",
            "question": (
                "统计不同城市的员工人数，"
                "按照人数从高到低排序，并生成柱状图。"
                "结果包含city和employee_count两列。"
            ),
            "expected": {
                "type": "table",
                "records": (
                    dataframe_to_records(
                        city_count
                    )
                ),
                "key_columns": ["city"],
                "value_columns": [
                    "employee_count"
                ],
                "tolerance": 0,
            },
            "chart_required": True,
        },
    ]


def build_order_cases(
    orders: pd.DataFrame,
) -> list[dict[str, Any]]:
    """
    创建订单数据集对应的5道评估题。
    """

    orders["order_date"] = pd.to_datetime(
        orders["order_date"]
    )

    status_count = (
        orders.groupby(
            "order_status",
            as_index=False,
        )
        .size()
        .rename(
            columns={
                "size": "order_count"
            }
        )
        .sort_values(
            "order_count",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    completed_orders = orders[
        orders["order_status"]
        == "已完成"
    ].copy()

    category_revenue = (
        completed_orders.groupby(
            "category",
            as_index=False,
        )["order_amount"]
        .sum()
        .rename(
            columns={
                "order_amount": (
                    "total_revenue"
                )
            }
        )
        .sort_values(
            "total_revenue",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    customer_average = (
        completed_orders.groupby(
            "customer_type",
            as_index=False,
        )["order_amount"]
        .mean()
        .rename(
            columns={
                "order_amount": (
                    "average_order_amount"
                )
            }
        )
        .sort_values(
            "average_order_amount",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    top_customers = (
        completed_orders.groupby(
            "customer_id",
            as_index=False,
        )["order_amount"]
        .sum()
        .rename(
            columns={
                "order_amount": (
                    "total_order_amount"
                )
            }
        )
        .sort_values(
            "total_order_amount",
            ascending=False,
        )
        .head(5)
        .reset_index(drop=True)
    )

    monthly_orders = (
        completed_orders.assign(
            month=(
                completed_orders[
                    "order_date"
                ].dt.strftime("%Y-%m")
            )
        )
        .groupby(
            "month",
            as_index=False,
        )
        .size()
        .rename(
            columns={
                "size": "order_count"
            }
        )
        .sort_values("month")
        .reset_index(drop=True)
    )

    return [
        {
            "case_id": "orders_001",
            "dataset_file": "orders.csv",
            "category": "distribution",
            "question": (
                "统计不同订单状态的订单数量，"
                "按照数量从高到低排序，并生成柱状图。"
                "结果包含order_status和"
                "order_count两列。"
            ),
            "expected": {
                "type": "table",
                "records": (
                    dataframe_to_records(
                        status_count
                    )
                ),
                "key_columns": [
                    "order_status"
                ],
                "value_columns": [
                    "order_count"
                ],
                "tolerance": 0,
            },
            "chart_required": True,
        },
        {
            "case_id": "orders_002",
            "dataset_file": "orders.csv",
            "category": "filter_aggregation",
            "question": (
                "仅分析已完成订单，统计各产品类别的"
                "订单总金额，按照总金额从高到低排序。"
                "结果包含category和"
                "total_revenue两列。"
            ),
            "expected": {
                "type": "table",
                "records": (
                    dataframe_to_records(
                        category_revenue
                    )
                ),
                "key_columns": ["category"],
                "value_columns": [
                    "total_revenue"
                ],
                "tolerance": 0.01,
            },
            "chart_required": False,
        },
        {
            "case_id": "orders_003",
            "dataset_file": "orders.csv",
            "category": "filter_average",
            "question": (
                "仅分析已完成订单，比较不同客户类型的"
                "平均订单金额，按照平均金额从高到低"
                "排序，并生成柱状图。结果包含"
                "customer_type和"
                "average_order_amount两列。"
            ),
            "expected": {
                "type": "table",
                "records": (
                    dataframe_to_records(
                        customer_average
                    )
                ),
                "key_columns": [
                    "customer_type"
                ],
                "value_columns": [
                    "average_order_amount"
                ],
                "tolerance": 0.01,
            },
            "chart_required": True,
        },
        {
            "case_id": "orders_004",
            "dataset_file": "orders.csv",
            "category": "top_n",
            "question": (
                "仅分析已完成订单，找出订单总金额"
                "最高的前5名客户，按照总金额从高到低"
                "排序。结果包含customer_id和"
                "total_order_amount两列。"
            ),
            "expected": {
                "type": "table",
                "records": (
                    dataframe_to_records(
                        top_customers
                    )
                ),
                "key_columns": [
                    "customer_id"
                ],
                "value_columns": [
                    "total_order_amount"
                ],
                "tolerance": 0.01,
            },
            "chart_required": False,
        },
        {
            "case_id": "orders_005",
            "dataset_file": "orders.csv",
            "category": "time_series",
            "question": (
                "仅分析已完成订单，统计每个月的"
                "订单数量，按照月份升序排列，"
                "并生成折线图。结果包含month和"
                "order_count两列，month格式为YYYY-MM。"
            ),
            "expected": {
                "type": "table",
                "records": (
                    dataframe_to_records(
                        monthly_orders
                    )
                ),
                "key_columns": ["month"],
                "value_columns": [
                    "order_count"
                ],
                "tolerance": 0,
            },
            "chart_required": True,
        },
    ]


def main() -> None:
    """
    读取三个评估数据集，计算标准答案，
    最终生成cases.json。
    """

    sales_path = (
        DATASET_DIR / "sales.csv"
    )

    employees_path = (
        DATASET_DIR / "employees.xlsx"
    )

    orders_path = (
        DATASET_DIR / "orders.csv"
    )

    required_files = [
        sales_path,
        employees_path,
        orders_path,
    ]

    for file_path in required_files:
        if not file_path.exists():
            raise FileNotFoundError(
                f"找不到评估数据集：{file_path}"
            )

    sales = pd.read_csv(
        sales_path
    )

    employees = pd.read_excel(
        employees_path
    )

    orders = pd.read_csv(
        orders_path
    )

    cases = []

    cases.extend(
        build_sales_cases(sales)
    )

    cases.extend(
        build_employee_cases(
            employees
        )
    )

    cases.extend(
        build_order_cases(orders)
    )

    output = {
        "benchmark_name": (
            "DataPilot Basic Evaluation"
        ),
        "version": "1.0",
        "description": (
            "用于评估DataPilot数据分析Agent的"
            "基础分析、代码执行和图表生成能力。"
        ),
        "total_cases": len(cases),
        "cases": cases,
    }

    with CASES_PATH.open(
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
        f"评估题库生成完成：{CASES_PATH}"
    )
    print(
        f"评估题目数量：{len(cases)}"
    )

    print("\n题目分布：")

    for dataset_file in [
        "sales.csv",
        "employees.xlsx",
        "orders.csv",
    ]:
        count = sum(
            case["dataset_file"]
            == dataset_file
            for case in cases
        )

        print(
            f"- {dataset_file}: "
            f"{count}道"
        )


if __name__ == "__main__":
    main()