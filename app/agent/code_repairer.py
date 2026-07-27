import ast
import json

from pydantic import ValidationError

from app.core.llm import LLMServiceError, llm_client
from app.schemas.analysis import (
    AnalysisPlan,
    CodeGenerationResult,
    ExecutionResult,
)
from app.schemas.dataset import DatasetProfile


class CodeRepairError(RuntimeError):
    """
    分析代码修复失败时抛出的业务异常。
    """


class AnalysisCodeRepairer:
    """
    DataPilot分析代码修复器。

    输入：
    1. 用户原始问题
    2. 数据集画像
    3. 分析计划
    4. 执行失败的代码
    5. 代码执行错误

    输出：
    1. 修复后的Python代码
    2. 修复内容说明
    """

    system_prompt = """
你是DataPilot的Python数据分析代码修复器。

你的任务是根据数据集画像、分析计划、失败代码和错误信息，
诊断代码失败原因，并生成修复后的完整Python代码。

运行环境中已经存在名为df的Pandas DataFrame。

请严格遵守以下规则：

1. 只能使用数据集中真实存在的字段。
2. 不得虚构、翻译或修改字段名称。
3. 必须针对提供的错误信息修复代码。
4. 必须返回完整代码，不能只返回修改片段。
5. 最终分析结果必须赋值给result。
6. 如果生成图表，图表对象必须赋值给fig。
7. 不要调用fig.show()。
8. 不要读取、保存或删除文件。
9. 不要访问网络。
10. 不要调用open、eval、exec或input。
11. 不要执行Shell命令。
12. 允许使用pandas、numpy和plotly.express。
13. 不要重新创建或读取df。
14. 不要输出Markdown代码块。
""".strip()

    def repair_code(
        self,
        question: str,
        plan: AnalysisPlan,
        dataset_profile: DatasetProfile,
        failed_code: str,
        execution: ExecutionResult,
    ) -> CodeGenerationResult:
        """
        根据执行错误修复Python代码。
        """

        if execution.success:
            raise CodeRepairError(
                "代码已经执行成功，不需要修复"
            )

        if not failed_code.strip():
            raise CodeRepairError(
                "失败代码不能为空"
            )

        profile_json = json.dumps(
            dataset_profile.model_dump(
                exclude_none=True
            ),
            ensure_ascii=False,
            indent=2,
        )

        plan_json = json.dumps(
            plan.model_dump(
                exclude_none=True
            ),
            ensure_ascii=False,
            indent=2,
        )

        error_information = {
            "error_type": execution.error_type,
            "error_message": execution.error_message,
            "stdout": execution.stdout,
        }

        error_json = json.dumps(
            error_information,
            ensure_ascii=False,
            indent=2,
        )

        user_prompt = f"""
用户原始问题：

{question.strip()}

数据集画像：

{profile_json}

分析计划：

{plan_json}

执行失败的Python代码：

{failed_code}

真实执行错误：

{error_json}

请分析错误原因并返回修复后的完整代码。

返回以下JSON结构：

{{
  "language": "python",
  "code": "修复后的完整Python代码",
  "explanation": "错误原因和修复内容"
}}
""".strip()

        try:
            raw_result = llm_client.chat_json(
                system_prompt=self.system_prompt,
                user_prompt=user_prompt,
                temperature=0,
            )
        except LLMServiceError as exc:
            raise CodeRepairError(
                f"调用模型修复代码失败：{exc}"
            ) from exc

        if not isinstance(raw_result, dict):
            raise CodeRepairError(
                "模型返回的修复结果不是JSON对象"
            )

        try:
            repaired_result = (
                CodeGenerationResult.model_validate(
                    raw_result
                )
            )
        except ValidationError as exc:
            raise CodeRepairError(
                f"代码修复结果格式验证失败：{exc}"
            ) from exc

        self._validate_repaired_code(
            repaired_code=repaired_result.code,
            failed_code=failed_code,
        )

        return repaired_result

    @staticmethod
    def _validate_repaired_code(
        repaired_code: str,
        failed_code: str,
    ) -> None:
        """
        检查修复代码的语法和result赋值。
        """

        if repaired_code.strip() == failed_code.strip():
            raise CodeRepairError(
                "模型返回的修复代码与失败代码完全相同"
            )

        try:
            syntax_tree = ast.parse(
                repaired_code
            )
        except SyntaxError as exc:
            raise CodeRepairError(
                f"修复后的代码仍存在语法错误："
                f"第{exc.lineno}行，{exc.msg}"
            ) from exc

        has_result_assignment = False

        for node in ast.walk(syntax_tree):
            if (
                isinstance(node, ast.Name)
                and node.id == "result"
                and isinstance(node.ctx, ast.Store)
            ):
                has_result_assignment = True
                break

        if not has_result_assignment:
            raise CodeRepairError(
                "修复后的代码没有把结果保存到result变量"
            )


analysis_code_repairer = AnalysisCodeRepairer()