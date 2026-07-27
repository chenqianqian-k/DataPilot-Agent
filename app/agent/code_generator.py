import ast
import json

from pydantic import ValidationError

from app.core.llm import LLMServiceError, llm_client
from app.schemas.analysis import (
    AnalysisPlan,
    CodeGenerationResult,
)
from app.schemas.dataset import DatasetProfile


class CodeGenerationError(RuntimeError):
    """
    分析代码生成失败时抛出的业务异常。
    """


class AnalysisCodeGenerator:
    """
    DataPilot数据分析代码生成器。

    输入：
    1. 用户原始问题
    2. Planner生成的分析计划
    3. 数据集画像

    输出：
    1. 可执行的Pandas代码
    2. 代码逻辑说明

    约定：
    1. 完整DataFrame已经存放在变量df中
    2. 最终分析结果必须保存到变量result中
    3. 如果生成图表，图表对象保存到变量fig中
    """

    system_prompt = """
你是DataPilot的Python数据分析代码生成器。

你的任务是根据用户问题、数据集画像和分析计划，
生成准确、简洁、可以执行的Python数据分析代码。

代码运行环境中已经存在一个名为df的Pandas DataFrame，
它包含需要分析的完整数据。

请严格遵守以下规则：

1. 只能使用数据集中真实存在的字段。
2. 不得虚构、修改或翻译字段名称。
3. 不要读取任何本地文件，因为数据已经位于df中。
4. 不要修改原始df，如需修改请先使用df.copy()。
5. 最终分析结果必须赋值给变量result。
6. 如果需要生成图表，可以使用Plotly Express。
7. Plotly图表对象必须赋值给变量fig。
8. 不要调用fig.show()。
9. 不要保存或删除任何文件。
10. 不要使用input()。
11. 不要使用eval()或exec()。
12. 不要执行Shell命令或系统命令。
13. 不要访问网络。
14. 不要使用未安装的第三方库。
15. 允许使用的主要库为pandas、numpy和plotly.express。
16. 代码中不要包含Markdown代码块标记。
17. 代码必须能够独立运行，但不要重新创建df。
""".strip()

    def generate_code(
        self,
        question: str,
        plan: AnalysisPlan,
        dataset_profile: DatasetProfile,
    ) -> CodeGenerationResult:
        """
        根据分析计划生成Pandas代码。
        """

        cleaned_question = question.strip()

        if len(cleaned_question) < 2:
            raise CodeGenerationError(
                "用户分析问题不能为空或过短"
            )

        plan_json = json.dumps(
            plan.model_dump(exclude_none=True),
            ensure_ascii=False,
            indent=2,
        )

        profile_json = json.dumps(
            dataset_profile.model_dump(
                exclude_none=True,
            ),
            ensure_ascii=False,
            indent=2,
        )

        user_prompt = f"""
用户原始问题：

{cleaned_question}

数据集画像：

{profile_json}

分析计划：

{plan_json}

请返回下面的JSON结构：

{{
  "language": "python",
  "code": "完整的Python分析代码",
  "explanation": "简要说明代码执行了哪些分析"
}}

注意：

1. code字段中必须是完整Python代码。
2. 最终结果必须保存到result变量。
3. 如果分析计划要求可视化，
   可以额外创建fig变量。
4. 不要输出Markdown代码块。
""".strip()

        try:
            raw_result = llm_client.chat_json(
                system_prompt=self.system_prompt,
                user_prompt=user_prompt,
                temperature=0,
            )
        except LLMServiceError as exc:
            raise CodeGenerationError(
                f"调用模型生成代码失败：{exc}"
            ) from exc

        if not isinstance(raw_result, dict):
            raise CodeGenerationError(
                "模型返回的代码结果不是JSON对象"
            )

        try:
            code_result = (
                CodeGenerationResult.model_validate(
                    raw_result
                )
            )
        except ValidationError as exc:
            raise CodeGenerationError(
                f"代码生成结果格式验证失败：{exc}"
            ) from exc

        self._validate_python_syntax(
            code_result.code
        )

        self._validate_result_assignment(
            code_result.code
        )

        return code_result

    @staticmethod
    def _validate_python_syntax(code: str) -> None:
        """
        使用Python AST检查代码语法是否正确。

        AST只解析代码，不会执行代码。
        """

        try:
            ast.parse(code)
        except SyntaxError as exc:
            raise CodeGenerationError(
                f"模型生成的Python代码存在语法错误："
                f"第{exc.lineno}行，{exc.msg}"
            ) from exc

    @staticmethod
    def _validate_result_assignment(
        code: str,
    ) -> None:
        """
        检查代码是否给result变量赋值。
        """

        syntax_tree = ast.parse(code)

        has_result_assignment = False

        for node in ast.walk(syntax_tree):
            if isinstance(node, ast.Name):
                if (
                    node.id == "result"
                    and isinstance(node.ctx, ast.Store)
                ):
                    has_result_assignment = True
                    break

        if not has_result_assignment:
            raise CodeGenerationError(
                "生成的代码没有把最终结果保存到result变量"
            )


analysis_code_generator = AnalysisCodeGenerator()