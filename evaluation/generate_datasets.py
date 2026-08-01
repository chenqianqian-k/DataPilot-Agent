from pathlib import Path

import numpy as np
import pandas as pd


# 当前文件所在目录：evaluation/
EVALUATION_DIR = Path(__file__).resolve().parent

# 数据集保存目录：evaluation/datasets/
DATASET_DIR = EVALUATION_DIR / "datasets"

# 固定随机种子，保证每次生成的数据完全一致
RANDOM_SEED = 42


def generate_sales_dataset() -> pd.DataFrame:
    """
    生成销售数据集。

    可用于评估：
    1. 不同地区销售额对比
    2. 月度销售趋势
    3. 产品类别销售排名
    4. 销售额和利润分析
    5. 柱状图、折线图、饼图生成
    """

    rng = np.random.default_rng(
        RANDOM_SEED
    )

    regions = [
        "华东",
        "华南",
        "华北",
        "西南",
    ]

    categories = [
        "电子产品",
        "办公用品",
        "家具",
    ]

    salespeople = [
        "张伟",
        "李娜",
        "王强",
        "赵敏",
        "陈晨",
        "刘洋",
    ]

    # 不同地区设置不同销售系数，
    # 保证地区之间存在明显差异
    region_factors = {
        "华东": 1.30,
        "华南": 1.15,
        "华北": 0.95,
        "西南": 0.80,
    }

    # 不同产品类别设置不同销售系数
    category_factors = {
        "电子产品": 1.40,
        "办公用品": 0.75,
        "家具": 1.10,
    }

    records = []

    order_number = 1

    # 生成2025年每个月的数据
    for month in range(1, 13):
        for region in regions:
            for category in categories:
                for _ in range(3):
                    quantity = int(
                        rng.integers(
                            5,
                            40,
                        )
                    )

                    unit_price = float(
                        rng.integers(
                            80,
                            800,
                        )
                    )

                    base_sales = (
                        quantity
                        * unit_price
                    )

                    sales_amount = (
                        base_sales
                        * region_factors[region]
                        * category_factors[category]
                    )

                    profit_rate = float(
                        rng.uniform(
                            0.08,
                            0.28,
                        )
                    )

                    profit = (
                        sales_amount
                        * profit_rate
                    )

                    order_date = pd.Timestamp(
                        year=2025,
                        month=month,
                        day=int(
                            rng.integers(
                                1,
                                25,
                            )
                        ),
                    )

                    records.append(
                        {
                            "order_id": (
                                f"S{order_number:04d}"
                            ),
                            "order_date": (
                                order_date.strftime(
                                    "%Y-%m-%d"
                                )
                            ),
                            "region": region,
                            "category": category,
                            "salesperson": (
                                rng.choice(
                                    salespeople
                                )
                            ),
                            "quantity": quantity,
                            "unit_price": round(
                                unit_price,
                                2,
                            ),
                            "sales_amount": round(
                                sales_amount,
                                2,
                            ),
                            "profit": round(
                                profit,
                                2,
                            ),
                        }
                    )

                    order_number += 1

    return pd.DataFrame(records)


def generate_employees_dataset() -> pd.DataFrame:
    """
    生成员工数据集。

    可用于评估：
    1. 部门人数统计
    2. 部门平均薪资比较
    3. 工作年限与薪资关系
    4. 员工绩效分布
    5. Excel文件读取与分析
    """

    rng = np.random.default_rng(
        RANDOM_SEED + 1
    )

    departments = {
        "研发部": {
            "count": 24,
            "salary_base": 18000,
        },
        "销售部": {
            "count": 18,
            "salary_base": 14000,
        },
        "市场部": {
            "count": 12,
            "salary_base": 13000,
        },
        "人力资源部": {
            "count": 8,
            "salary_base": 11000,
        },
        "财务部": {
            "count": 8,
            "salary_base": 12500,
        },
    }

    education_levels = [
        "本科",
        "硕士",
        "博士",
    ]

    cities = [
        "北京",
        "上海",
        "深圳",
        "杭州",
    ]

    records = []

    employee_number = 1

    for department, config in departments.items():
        for _ in range(config["count"]):
            experience_years = int(
                rng.integers(
                    1,
                    13,
                )
            )

            age = int(
                22
                + experience_years
                + rng.integers(
                    0,
                    8,
                )
            )

            education = str(
                rng.choice(
                    education_levels,
                    p=[
                        0.60,
                        0.33,
                        0.07,
                    ],
                )
            )

            education_bonus = {
                "本科": 0,
                "硕士": 2500,
                "博士": 5000,
            }[education]

            monthly_salary = (
                config["salary_base"]
                + experience_years * 650
                + education_bonus
                + rng.normal(
                    0,
                    1000,
                )
            )

            performance_score = float(
                np.clip(
                    rng.normal(
                        82,
                        8,
                    ),
                    60,
                    100,
                )
            )

            gender = str(
                rng.choice(
                    [
                        "男",
                        "女",
                    ]
                )
            )

            records.append(
                {
                    "employee_id": (
                        f"E{employee_number:03d}"
                    ),
                    "department": department,
                    "gender": gender,
                    "age": age,
                    "city": rng.choice(
                        cities
                    ),
                    "education": education,
                    "experience_years": (
                        experience_years
                    ),
                    "monthly_salary": round(
                        monthly_salary,
                        2,
                    ),
                    "performance_score": round(
                        performance_score,
                        1,
                    ),
                }
            )

            employee_number += 1

    return pd.DataFrame(records)


def generate_orders_dataset() -> pd.DataFrame:
    """
    生成电商订单数据集。

    可用于评估：
    1. 订单状态分布
    2. 不同客户类型的消费差异
    3. 产品类别利润率分析
    4. 月度订单趋势
    5. Top-N客户或商品分析
    """

    rng = np.random.default_rng(
        RANDOM_SEED + 2
    )

    categories = [
        "数码",
        "服装",
        "食品",
        "家居",
        "图书",
    ]

    customer_types = [
        "普通客户",
        "会员客户",
        "企业客户",
    ]

    payment_methods = [
        "支付宝",
        "微信支付",
        "银行卡",
    ]

    order_statuses = [
        "已完成",
        "已取消",
        "已退款",
    ]

    records = []

    start_date = pd.Timestamp(
        "2025-01-01"
    )

    for index in range(1, 181):
        category = str(
            rng.choice(
                categories
            )
        )

        customer_type = str(
            rng.choice(
                customer_types,
                p=[
                    0.55,
                    0.35,
                    0.10,
                ],
            )
        )

        status = str(
            rng.choice(
                order_statuses,
                p=[
                    0.82,
                    0.10,
                    0.08,
                ],
            )
        )

        quantity = int(
            rng.integers(
                1,
                8,
            )
        )

        unit_price = float(
            rng.integers(
                30,
                1500,
            )
        )

        discount_rate = {
            "普通客户": 0.02,
            "会员客户": 0.08,
            "企业客户": 0.12,
        }[customer_type]

        order_amount = (
            quantity
            * unit_price
            * (
                1 - discount_rate
            )
        )

        cost_rate = float(
            rng.uniform(
                0.55,
                0.82,
            )
        )

        profit = (
            order_amount
            * (
                1 - cost_rate
            )
        )

        if status == "已取消":
            order_amount = 0.0
            profit = 0.0

        if status == "已退款":
            profit = -abs(
                order_amount * 0.05
            )

        order_date = (
            start_date
            + pd.Timedelta(
                days=int(
                    rng.integers(
                        0,
                        365,
                    )
                )
            )
        )

        records.append(
            {
                "order_id": (
                    f"O{index:04d}"
                ),
                "order_date": (
                    order_date.strftime(
                        "%Y-%m-%d"
                    )
                ),
                "customer_id": (
                    f"C{int(rng.integers(1, 51)):03d}"
                ),
                "customer_type": (
                    customer_type
                ),
                "category": category,
                "quantity": quantity,
                "unit_price": round(
                    unit_price,
                    2,
                ),
                "discount_rate": (
                    discount_rate
                ),
                "order_amount": round(
                    order_amount,
                    2,
                ),
                "profit": round(
                    profit,
                    2,
                ),
                "payment_method": (
                    rng.choice(
                        payment_methods
                    )
                ),
                "order_status": status,
            }
        )

    return pd.DataFrame(records)


def main() -> None:
    """
    生成并保存全部评估数据集。
    """

    DATASET_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    sales_df = (
        generate_sales_dataset()
    )

    employees_df = (
        generate_employees_dataset()
    )

    orders_df = (
        generate_orders_dataset()
    )

    sales_path = (
        DATASET_DIR / "sales.csv"
    )

    employees_path = (
        DATASET_DIR / "employees.xlsx"
    )

    orders_path = (
        DATASET_DIR / "orders.csv"
    )

    sales_df.to_csv(
        sales_path,
        index=False,
        encoding="utf-8-sig",
    )

    employees_df.to_excel(
        employees_path,
        index=False,
    )

    orders_df.to_csv(
        orders_path,
        index=False,
        encoding="utf-8-sig",
    )

    print("评估数据集生成完成：")
    print(
        f"1. {sales_path}："
        f"{len(sales_df)}行 × "
        f"{len(sales_df.columns)}列"
    )
    print(
        f"2. {employees_path}："
        f"{len(employees_df)}行 × "
        f"{len(employees_df.columns)}列"
    )
    print(
        f"3. {orders_path}："
        f"{len(orders_df)}行 × "
        f"{len(orders_df.columns)}列"
    )


if __name__ == "__main__":
    main()