import json

from app.core.llm import LLMServiceError, llm_client
from app.schemas.analysis import (
    AnalysisPlan,
    ExecutionResult,
)


class ReportGenerationError(RuntimeError):
    """
    分析报告生成失败时抛出的业务异常。
    """


class AnalysisReporter:
    """
    DataPilot分析结果解释器。

    输入：
    1. 用户原始问题
    2. Agent生成的分析计划
    3. Python代码执行结果
    4. 代码逻辑说明

    输出：
    1. 用户可以直接阅读的数据分析结论
    """

    system_prompt = """
你是DataPilot的数据分析报告生成器。

你的任务是根据用户问题、分析计划和真实代码执行结果，
生成准确、清晰、简洁的数据分析结论。

请严格遵守以下规则：

1. 只能依据提供的代码执行结果进行分析。
2. 不得编造执行结果中不存在的数值或结论。
3. 必须直接回答用户最初提出的问题。
4. 重要数值必须准确引用。
5. 如果有明显的最高值、最低值、排序或差异，应当指出。
6. 如果结果数据不足以支持某个结论，应明确说明。
7. 不要讨论Python代码实现细节，除非用户明确询问。
8. 使用中文回答。
9. 使用简洁的Markdown格式。
10. 不要输出JSON。
""".strip()

    def generate_report(
        self,
        question: str,
        plan: AnalysisPlan,
        execution: ExecutionResult,
        code_explanation: str = "",
    ) -> str:
        """
        根据执行结果生成最终分析报告。
        """

        cleaned_question = question.strip()

        if len(cleaned_question) < 2:
            raise ReportGenerationError(
                "用户问题不能为空或过短"
            )

        if not execution.success:
            error_type = (
                execution.error_type
                or "UnknownError"
            )

            error_message = (
                execution.error_message
                or "没有具体错误信息"
            )

            raise ReportGenerationError(
                f"代码执行失败，无法生成分析报告："
                f"{error_type}: {error_message}"
            )

        if not execution.result_preview:
            raise ReportGenerationError(
                "代码执行成功，但没有可以解释的结果数据"
            )

        plan_json = json.dumps(
            plan.model_dump(exclude_none=True),
            ensure_ascii=False,
            indent=2,
        )

        execution_json = json.dumps(
            execution.model_dump(exclude_none=True),
            ensure_ascii=False,
            indent=2,
        )

        user_prompt = f"""
用户原始问题：

{cleaned_question}

分析计划：

{plan_json}

代码逻辑说明：

{code_explanation or "未提供"}

真实代码执行结果：

{execution_json}

请生成最终的数据分析结论。

建议采用以下结构：

## 分析结论

直接回答用户问题，并说明最重要的发现。

## 关键数据

列出支持结论的关键数值。

## 补充说明

仅在确有必要时说明数据范围、结果限制或注意事项。
""".strip()

        try:
            report = llm_client.chat(
                system_prompt=self.system_prompt,
                user_prompt=user_prompt,
                temperature=0,
            )
        except LLMServiceError as exc:
            raise ReportGenerationError(
                f"调用模型生成分析报告失败：{exc}"
            ) from exc

        if not report.strip():
            raise ReportGenerationError(
                "模型返回的分析报告为空"
            )

        return report.strip()


analysis_reporter = AnalysisReporter()