import json

from pydantic import ValidationError

from app.core.llm import LLMServiceError, llm_client
from app.schemas.analysis import AnalysisPlan
from app.schemas.dataset import DatasetProfile


class AnalysisPlanningError(RuntimeError):
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
    2. 所需字段
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

1. 只能使用数据集中真实存在的字段。
2. 不得修改或编造字段名称。
3. 分析步骤应当具体、合理并且顺序清晰。
4. 每个步骤都要说明使用哪些字段。
5. operation只能从以下值中选择：
   inspect、clean、filter、aggregate、calculate、
   sort、visualize、summarize。
6. 只有用户需求适合可视化时，
   needs_visualization才设置为true。
7. chart_type可以使用bar、line、pie、scatter、
   histogram、box，也可以为null。
8. 不要生成Python代码。
""".strip()

    def create_plan(
        self,
        question: str,
        dataset_profile: DatasetProfile,
    ) -> AnalysisPlan:
        """
        根据用户问题和数据画像生成分析计划。
        """

        cleaned_question = question.strip()

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

        user_prompt = f"""
用户的数据分析问题：

{cleaned_question}

数据集画像：

{profile_json}

请返回以下JSON结构：

{{
  "objective": "本次分析的总体目标",
  "required_columns": [
    "字段1",
    "字段2"
  ],
  "steps": [
    {{
      "step_id": 1,
      "title": "步骤标题",
      "description": "这一步具体做什么",
      "operation": "aggregate",
      "required_columns": [
        "字段1",
        "字段2"
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
""".strip()

        try:
            raw_plan = llm_client.chat_json(
                system_prompt=self.system_prompt,
                user_prompt=user_prompt,
                temperature=0,
            )
        except LLMServiceError as exc:
            raise AnalysisPlanningError(
                f"调用模型生成分析计划失败：{exc}"
            ) from exc

        if not isinstance(raw_plan, dict):
            raise AnalysisPlanningError(
                "模型返回的分析计划不是JSON对象"
            )

        try:
            plan = AnalysisPlan.model_validate(raw_plan)
        except ValidationError as exc:
            raise AnalysisPlanningError(
                f"分析计划格式验证失败：{exc}"
            ) from exc

        self._validate_plan_columns(
            plan=plan,
            dataset_profile=dataset_profile,
        )

        return plan

    @staticmethod
    def _validate_plan_columns(
        plan: AnalysisPlan,
        dataset_profile: DatasetProfile,
    ) -> None:
        """
        检查模型是否使用了数据集中不存在的字段。
        """

        available_columns = {
            column.name
            for column in dataset_profile.columns
        }

        referenced_columns = set(plan.required_columns)

        for step in plan.steps:
            referenced_columns.update(step.required_columns)

        unknown_columns = (
            referenced_columns - available_columns
        )

        if unknown_columns:
            unknown_text = "、".join(
                sorted(unknown_columns)
            )

            available_text = "、".join(
                sorted(available_columns)
            )

            raise AnalysisPlanningError(
                f"分析计划使用了不存在的字段："
                f"{unknown_text}。"
                f"可用字段为：{available_text}"
            )


analysis_planner = AnalysisPlanner()