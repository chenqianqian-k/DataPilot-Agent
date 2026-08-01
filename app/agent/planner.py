import json

from pydantic import ValidationError

from app.core.llm import (
    LLMServiceError,
    llm_client,
)
from app.schemas.analysis import (
    AnalysisPlan,
)
from app.schemas.dataset import (
    DatasetProfile,
)


class AnalysisPlanningError(
    RuntimeError
):
    """
    分析计划生成失败时抛出的业务异常。
    """


class AnalysisPlanner:
    """
    DataPilot分析规划器。

    输入：
    1. 用户的数据分析问题
    2. 数据集画像

    输出：
    1. 分析目标
    2. 所需原始字段
    3. 分析步骤
    4. 是否生成图表
    5. 建议图表类型
    """

    system_prompt = """
你是DataPilot的数据分析规划器。

你的任务是根据用户的数据分析问题和数据集画像，
制定准确、清晰、可以执行的数据分析计划。

你只负责制定分析计划，不需要编写Python代码，
也不要直接计算或虚构分析结果。

请遵守以下要求：

1. required_columns只允许填写数据集中原本存在的字段。

2. AnalysisPlan中的required_columns表示整个任务需要读取的
   原始数据字段。

3. AnalysisStep中的required_columns表示执行该步骤时需要读取的
   原始数据字段。

4. 聚合、计算、重命名后产生的新字段属于输出字段，
   不能写入任何required_columns。

5. 输出字段可以出现在步骤描述和expected_outputs中，
   但不能作为原始字段填写到required_columns中。

6. 不得修改或编造原始字段名称。

7. 分析步骤应当具体、合理并且顺序清晰。

8. 每个步骤都要说明需要使用哪些原始字段。

9. operation只能从以下值中选择：
   inspect、clean、filter、aggregate、calculate、
   sort、visualize、summarize。

10. 只有用户需求适合可视化时，
    needs_visualization才设置为true。

11. chart_type可以使用bar、line、pie、scatter、
    histogram、box，也可以为null。

12. 不要生成Python代码。

字段区分示例：

如果原始数据包含region和sales_amount，
用户要求按照region统计销售总额，
并把结果命名为total_sales。

正确写法：

required_columns：
["region", "sales_amount"]

步骤required_columns：
["region", "sales_amount"]

expected_outputs中可以写：
"生成包含region和total_sales的汇总结果"

错误写法：

required_columns：
["region", "sales_amount", "total_sales"]

原因是total_sales不是原始数据字段，
而是计算后产生的输出字段。
""".strip()

    def create_plan(
        self,
        question: str,
        dataset_profile: DatasetProfile,
    ) -> AnalysisPlan:
        """
        根据用户问题和数据画像生成分析计划。
        """

        cleaned_question = (
            question.strip()
        )

        if len(cleaned_question) < 2:
            raise AnalysisPlanningError(
                "数据分析问题不能为空或过短"
            )

        profile_json = json.dumps(
            dataset_profile.model_dump(
                exclude_none=True,
            ),
            ensure_ascii=False,
            indent=2,
        )

        available_columns = [
            column.name
            for column
            in dataset_profile.columns
        ]

        available_columns_json = (
            json.dumps(
                available_columns,
                ensure_ascii=False,
            )
        )

        user_prompt = f"""
用户的数据分析问题：

{cleaned_question}

数据集画像：

{profile_json}

当前数据集真实存在的原始字段：

{available_columns_json}

请返回以下JSON结构：

{{
  "objective": "本次分析的总体目标",
  "required_columns": [
    "任务需要读取的原始字段1",
    "任务需要读取的原始字段2"
  ],
  "steps": [
    {{
      "step_id": 1,
      "title": "步骤标题",
      "description": "这一步具体做什么，以及产生什么输出字段",
      "operation": "aggregate",
      "required_columns": [
        "该步骤需要读取的原始字段1",
        "该步骤需要读取的原始字段2"
      ]
    }}
  ],
  "expected_outputs": [
    "预期输出1",
    "预期输出2"
  ],
  "needs_visualization": true,
  "chart_type": "bar"
}}

请特别注意：

1. required_columns中的所有字段，都必须来自上述
   “当前数据集真实存在的原始字段”。

2. 用户指定的结果列名、别名、聚合列名和计算后字段，
   不得放入required_columns。

3. 新生成的输出字段只能写在description或
   expected_outputs中。

4. 如果用户要求将sales_amount求和后命名为total_sales，
   required_columns中填写sales_amount，
   不要填写total_sales。
""".strip()

        try:
            raw_plan = (
                llm_client.chat_json(
                    system_prompt=(
                        self.system_prompt
                    ),
                    user_prompt=user_prompt,
                    temperature=0,
                )
            )

        except LLMServiceError as exc:
            raise AnalysisPlanningError(
                "调用模型生成分析计划失败："
                f"{exc}"
            ) from exc

        if not isinstance(
            raw_plan,
            dict,
        ):
            raise AnalysisPlanningError(
                "模型返回的分析计划"
                "不是JSON对象"
            )

        try:
            plan = (
                AnalysisPlan.model_validate(
                    raw_plan
                )
            )

        except ValidationError as exc:
            raise AnalysisPlanningError(
                "分析计划格式验证失败："
                f"{exc}"
            ) from exc

        self._validate_plan_columns(
            plan=plan,
            dataset_profile=(
                dataset_profile
            ),
        )

        return plan

    @staticmethod
    def _validate_plan_columns(
        plan: AnalysisPlan,
        dataset_profile: DatasetProfile,
    ) -> None:
        """
        检查分析计划是否引用了不存在的原始字段。

        required_columns只能引用数据集加载时
        已经存在的原始字段。

        聚合、计算、重命名后产生的新字段，
        应该写在步骤描述或expected_outputs中，
        不应该写入required_columns。
        """

        available_columns = {
            column.name
            for column
            in dataset_profile.columns
        }

        referenced_columns = set(
            plan.required_columns
        )

        for step in plan.steps:
            referenced_columns.update(
                step.required_columns
            )

        unknown_columns = (
            referenced_columns
            - available_columns
        )

        if unknown_columns:
            unknown_text = "、".join(
                sorted(unknown_columns)
            )

            available_text = "、".join(
                sorted(available_columns)
            )

            raise AnalysisPlanningError(
                "分析计划的required_columns"
                "使用了不存在的原始字段："
                f"{unknown_text}。"
                "required_columns只能包含"
                "数据集中原本存在的字段。"
                f"可用原始字段为："
                f"{available_text}"
            )


analysis_planner = AnalysisPlanner()
