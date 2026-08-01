from dataclasses import asdict
from dataclasses import dataclass
from typing import Any, Literal


FaultType = Literal[
    "undefined_variable",
    "missing_column",
    "type_error",
    "column_typo",
]


class FaultInjectionError(
    RuntimeError
):
    """
    故障注入失败时抛出的异常。
    """


@dataclass
class FaultInjectionResult:
    """
    故障注入结果。

    original_code：
    Agent原本生成的正确代码。

    injected_code：
    注入故障后的错误代码。

    fault_type：
    注入的故障类型。

    description：
    本次故障的具体说明。
    """

    fault_type: str
    description: str
    original_code: str
    injected_code: str

    def to_dict(
        self,
    ) -> dict[str, Any]:
        """
        转换为普通字典。
        """

        return asdict(self)


def inject_undefined_variable(
    code: str,
) -> FaultInjectionResult:
    """
    注入未定义变量错误。

    在代码开头访问一个不存在的变量，
    执行时会触发NameError。
    """

    fault_code = (
        "fault_injected_undefined_variable\n"
    )

    injected_code = (
        fault_code
        + code
    )

    return FaultInjectionResult(
        fault_type=(
            "undefined_variable"
        ),
        description=(
            "在代码开头访问未定义变量，"
            "预期触发NameError"
        ),
        original_code=code,
        injected_code=injected_code,
    )


def inject_missing_column(
    code: str,
) -> FaultInjectionResult:
    """
    注入不存在字段错误。

    强制访问一个不存在的DataFrame字段，
    执行时会触发KeyError。
    """

    fault_code = (
        'df["fault_injected_missing_column"]\n'
    )

    injected_code = (
        fault_code
        + code
    )

    return FaultInjectionResult(
        fault_type="missing_column",
        description=(
            "访问不存在的DataFrame字段，"
            "预期触发KeyError"
        ),
        original_code=code,
        injected_code=injected_code,
    )


def inject_type_error(
    code: str,
) -> FaultInjectionResult:
    """
    注入数据类型错误。

    故意将字符串与整数相加，
    执行时会触发TypeError。
    """

    fault_code = (
        '"fault_injection" + 1\n'
    )

    injected_code = (
        fault_code
        + code
    )

    return FaultInjectionResult(
        fault_type="type_error",
        description=(
            "执行字符串与整数相加，"
            "预期触发TypeError"
        ),
        original_code=code,
        injected_code=injected_code,
    )


def inject_column_typo(
    code: str,
    target_text: str,
    replacement_text: str,
) -> FaultInjectionResult:
    """
    注入字段拼写错误。

    例如：

    sales_amount
    修改为：
    sales_amout

    这种故障更接近真实的代码生成错误。
    """

    if not target_text:
        raise FaultInjectionError(
            "column_typo必须提供target_text"
        )

    if not replacement_text:
        raise FaultInjectionError(
            "column_typo必须提供"
            "replacement_text"
        )

    if target_text not in code:
        raise FaultInjectionError(
            "生成代码中找不到需要替换的内容："
            f"{target_text}"
        )

    injected_code = code.replace(
        target_text,
        replacement_text,
    )

    return FaultInjectionResult(
        fault_type="column_typo",
        description=(
            f"将字段{target_text}错误替换为"
            f"{replacement_text}，"
            "预期触发字段不存在错误"
        ),
        original_code=code,
        injected_code=injected_code,
    )


def inject_fault(
    code: str,
    fault_type: FaultType,
    target_text: str | None = None,
    replacement_text: str | None = None,
) -> FaultInjectionResult:
    """
    故障注入统一入口。

    根据fault_type选择对应的注入方式。
    """

    cleaned_code = code.strip()

    if not cleaned_code:
        raise FaultInjectionError(
            "需要注入故障的代码不能为空"
        )

    if (
        fault_type
        == "undefined_variable"
    ):
        return inject_undefined_variable(
            cleaned_code
        )

    if fault_type == "missing_column":
        return inject_missing_column(
            cleaned_code
        )

    if fault_type == "type_error":
        return inject_type_error(
            cleaned_code
        )

    if fault_type == "column_typo":
        return inject_column_typo(
            code=cleaned_code,
            target_text=(
                target_text or ""
            ),
            replacement_text=(
                replacement_text or ""
            ),
        )

    raise FaultInjectionError(
        f"不支持的故障类型：{fault_type}"
    )