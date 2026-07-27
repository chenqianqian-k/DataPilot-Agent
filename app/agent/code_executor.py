import ast
import builtins
import io
import json
import signal
import time
from contextlib import redirect_stdout
from pathlib import Path
from types import FrameType
from typing import Any
from uuid import uuid4

import numpy as np
import pandas as pd
import plotly.express as px

from app.core.config import settings
from app.schemas.analysis import ExecutionResult


class CodeSecurityError(RuntimeError):
    """
    生成代码未通过安全检查。
    """


class CodeExecutionTimeoutError(TimeoutError):
    """
    代码执行时间超过限制。
    """


class AnalysisCodeExecutor:
    """
    DataPilot分析代码执行器。

    负责：
    1. 使用AST检查危险代码
    2. 建立受限执行环境
    3. 执行模型生成的代码
    4. 捕获标准输出和错误
    5. 提取result变量
    6. 保存Plotly图表
    7. 返回结构化执行结果
    """

    allowed_imports = {
        "pandas",
        "numpy",
        "plotly",
        "plotly.express",
        "plotly.graph_objects",
    }

    forbidden_names = {
        "eval",
        "exec",
        "compile",
        "open",
        "input",
        "breakpoint",
        "globals",
        "locals",
        "vars",
        "getattr",
        "setattr",
        "delattr",
    }

    forbidden_attributes = {
        "system",
        "popen",
        "spawn",
        "fork",
        "kill",
        "unlink",
        "rmdir",
        "read_text",
        "write_text",
        "read_bytes",
        "write_bytes",
        "read_csv",
        "read_excel",
        "read_pickle",
        "read_parquet",
        "to_csv",
        "to_excel",
        "to_pickle",
        "to_parquet",
    }

    def __init__(
        self,
        timeout_seconds: int = 15,
        preview_row_count: int = 20,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.preview_row_count = preview_row_count

    def execute(
        self,
        code: str,
        dataframe: pd.DataFrame,
    ) -> ExecutionResult:
        """
        检查并执行模型生成的分析代码。
        """

        start_time = time.perf_counter()

        try:
            self._validate_code_security(code)
        except CodeSecurityError as exc:
            return ExecutionResult(
                success=False,
                error_type="CodeSecurityError",
                error_message=str(exc),
                execution_time_seconds=round(
                    time.perf_counter() - start_time,
                    6,
                ),
            )

        execution_environment = (
            self._create_execution_environment(
                dataframe=dataframe
            )
        )

        stdout_buffer = io.StringIO()
        previous_handler = None

        try:
            previous_handler = signal.getsignal(
                signal.SIGALRM
            )

            signal.signal(
                signal.SIGALRM,
                self._handle_timeout,
            )

            signal.alarm(self.timeout_seconds)

            with redirect_stdout(stdout_buffer):
                compiled_code = compile(
                    code,
                    filename="<datapilot-generated-code>",
                    mode="exec",
                )

                exec(
                    compiled_code,
                    execution_environment,
                    execution_environment,
                )

            signal.alarm(0)

            if "result" not in execution_environment:
                raise RuntimeError(
                    "代码执行完成，但没有生成result变量"
                )

            result = execution_environment["result"]

            result_preview = self._build_result_preview(
                result
            )

            generated_files = self._save_figure_if_present(
                execution_environment
            )

            execution_time = (
                time.perf_counter() - start_time
            )

            return ExecutionResult(
                success=True,
                stdout=stdout_buffer.getvalue(),
                result_preview=result_preview,
                generated_files=generated_files,
                execution_time_seconds=round(
                    execution_time,
                    6,
                ),
            )

        except CodeExecutionTimeoutError as exc:
            return ExecutionResult(
                success=False,
                stdout=stdout_buffer.getvalue(),
                error_type=type(exc).__name__,
                error_message=str(exc),
                execution_time_seconds=round(
                    time.perf_counter() - start_time,
                    6,
                ),
            )

        except Exception as exc:
            return ExecutionResult(
                success=False,
                stdout=stdout_buffer.getvalue(),
                error_type=type(exc).__name__,
                error_message=str(exc),
                execution_time_seconds=round(
                    time.perf_counter() - start_time,
                    6,
                ),
            )

        finally:
            signal.alarm(0)

            if previous_handler is not None:
                signal.signal(
                    signal.SIGALRM,
                    previous_handler,
                )

    def _validate_code_security(
        self,
        code: str,
    ) -> None:
        """
        使用AST检查明显危险的代码结构。
        """

        try:
            syntax_tree = ast.parse(code)
        except SyntaxError as exc:
            raise CodeSecurityError(
                f"Python语法错误：第{exc.lineno}行，"
                f"{exc.msg}"
            ) from exc

        for node in ast.walk(syntax_tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._validate_import_name(
                        alias.name
                    )

            elif isinstance(node, ast.ImportFrom):
                if node.module is None:
                    raise CodeSecurityError(
                        "不允许使用相对导入"
                    )

                self._validate_import_name(
                    node.module
                )

            elif isinstance(node, ast.Call):
                self._validate_function_call(node)

            elif isinstance(node, ast.Attribute):
                self._validate_attribute(node)

    def _validate_import_name(
        self,
        module_name: str,
    ) -> None:
        """
        检查导入的模块是否位于白名单。
        """

        is_allowed = any(
            module_name == allowed
            or module_name.startswith(
                f"{allowed}."
            )
            for allowed in self.allowed_imports
        )

        if not is_allowed:
            raise CodeSecurityError(
                f"不允许导入模块：{module_name}"
            )

    def _validate_function_call(
        self,
        node: ast.Call,
    ) -> None:
        """
        检查是否调用了危险内置函数。
        """

        if isinstance(node.func, ast.Name):
            function_name = node.func.id

            if function_name in self.forbidden_names:
                raise CodeSecurityError(
                    f"不允许调用函数：{function_name}()"
                )

    def _validate_attribute(
        self,
        node: ast.Attribute,
    ) -> None:
        """
        检查危险属性和双下划线属性。
        """

        attribute_name = node.attr

        if attribute_name.startswith("__"):
            raise CodeSecurityError(
                f"不允许访问特殊属性："
                f"{attribute_name}"
            )

        if attribute_name in self.forbidden_attributes:
            raise CodeSecurityError(
                f"不允许调用文件或系统操作："
                f"{attribute_name}"
            )

    def _create_execution_environment(
        self,
        dataframe: pd.DataFrame,
    ) -> dict[str, Any]:
        """
        创建代码运行时可以访问的变量和函数。
        """

        safe_builtins = {
            "__import__": self._safe_import,
            "abs": abs,
            "all": all,
            "any": any,
            "bool": bool,
            "dict": dict,
            "enumerate": enumerate,
            "filter": filter,
            "float": float,
            "int": int,
            "len": len,
            "list": list,
            "map": map,
            "max": max,
            "min": min,
            "print": print,
            "range": range,
            "round": round,
            "set": set,
            "sorted": sorted,
            "str": str,
            "sum": sum,
            "tuple": tuple,
            "zip": zip,
        }

        return {
            "__builtins__": safe_builtins,
            "df": dataframe.copy(deep=True),
            "pd": pd,
            "np": np,
            "px": px,
        }

    def _safe_import(
        self,
        name: str,
        globals: dict[str, Any] | None = None,
        locals: dict[str, Any] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> Any:
        """
        只允许代码导入白名单中的模块。
        """

        self._validate_import_name(name)

        return builtins.__import__(
            name,
            globals,
            locals,
            fromlist,
            level,
        )

    def _handle_timeout(
        self,
        signum: int,
        frame: FrameType | None,
    ) -> None:
        """
        在代码运行超时时终止本次执行。
        """

        raise CodeExecutionTimeoutError(
            f"代码执行超过{self.timeout_seconds}秒"
        )

    def _build_result_preview(
        self,
        result: Any,
    ) -> list[dict[str, Any]]:
        """
        将执行结果转换成可以返回给前端的预览数据。
        """

        if isinstance(result, pd.DataFrame):
            preview = result.head(
                self.preview_row_count
            )

            return json.loads(
                preview.to_json(
                    orient="records",
                    force_ascii=False,
                    date_format="iso",
                )
            )

        if isinstance(result, pd.Series):
            result_name = (
                str(result.name)
                if result.name is not None
                else "value"
            )

            preview = (
                result
                .head(self.preview_row_count)
                .rename(result_name)
                .reset_index()
            )

            return json.loads(
                preview.to_json(
                    orient="records",
                    force_ascii=False,
                    date_format="iso",
                )
            )

        if isinstance(result, dict):
            safe_result = {
                str(key): self._make_json_safe(value)
                for key, value in result.items()
            }

            return [safe_result]

        if isinstance(result, (list, tuple)):
            return [
                {
                    "value": self._make_json_safe(value)
                }
                for value in result[
                    :self.preview_row_count
                ]
            ]

        return [
            {
                "value": self._make_json_safe(result)
            }
        ]

    @staticmethod
    def _make_json_safe(
        value: Any,
    ) -> Any:
        """
        将常见NumPy和Pandas类型转换成JSON类型。
        """

        if value is None:
            return None

        if isinstance(value, np.integer):
            return int(value)

        if isinstance(value, np.floating):
            value = float(value)

            if np.isnan(value) or np.isinf(value):
                return None

            return value

        if isinstance(value, np.bool_):
            return bool(value)

        if isinstance(value, pd.Timestamp):
            return value.isoformat()

        if isinstance(
            value,
            (str, int, float, bool),
        ):
            return value

        return str(value)

    def _save_figure_if_present(
        self,
        execution_environment: dict[str, Any],
    ) -> list[str]:
        """
        如果代码生成了fig，则保存为HTML文件。
        """

        figure = execution_environment.get("fig")

        if figure is None:
            return []

        if not hasattr(figure, "write_html"):
            raise RuntimeError(
                "fig变量不是有效的Plotly图表对象"
            )

        settings.output_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        file_name = (
            f"chart_{uuid4().hex}.html"
        )

        output_path: Path = (
            settings.output_path / file_name
        )

        figure.write_html(
            str(output_path),
            include_plotlyjs="cdn",
        )

        return [str(output_path)]



analysis_code_executor = AnalysisCodeExecutor()