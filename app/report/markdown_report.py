from datetime import datetime
from typing import Any


def _format_plan(
    plan: dict[str, Any] | None,
) -> str:
    """
    将分析计划转换为Markdown文本。
    """

    if not plan:
        return "暂无分析计划。"

    steps = plan.get(
        "steps",
        [],
    )

    if not steps:
        return "暂无分析步骤。"

    lines: list[str] = []

    for index, step in enumerate(
        steps,
        start=1,
    ):
        if isinstance(step, dict):
            step_id = step.get(
                "step_id",
                index,
            )

            title = (
                step.get("title")
                or step.get("name")
                or step.get("description")
                or f"分析步骤{step_id}"
            )

            description = step.get(
                "description"
            )

            lines.append(
                f"{step_id}. **{title}**"
            )

            if (
                description
                and description != title
            ):
                lines.append(
                    f"   - {description}"
                )

        else:
            lines.append(
                f"{index}. {step}"
            )

    return "\n".join(lines)


def _format_execution(
    execution: dict[str, Any] | None,
) -> str:
    """
    将代码执行信息转换为Markdown文本。
    """

    if not execution:
        return "暂无代码执行信息。"

    success = execution.get(
        "success",
        False,
    )

    success_text = (
        "成功"
        if success
        else "失败"
    )

    execution_time = execution.get(
        "execution_time_seconds"
    )

    if execution_time is None:
        execution_time = execution.get(
            "execution_time"
        )

    stdout = (
        execution.get("stdout")
        or execution.get("output")
        or ""
    )

    error = (
        execution.get("error_message")
        or execution.get("stderr")
        or ""
    )

    lines = [
        f"- 执行状态：{success_text}",
    ]

    if execution_time is not None:
        lines.append(
            f"- 执行时间：{execution_time} 秒"
        )

    if stdout:
        lines.extend(
            [
                "",
                "### 执行输出",
                "",
                "```text",
                str(stdout),
                "```",
            ]
        )

    if error:
        lines.extend(
            [
                "",
                "### 执行错误",
                "",
                "```text",
                str(error),
                "```",
            ]
        )

    return "\n".join(lines)


def build_markdown_report(
    result: dict[str, Any],
    dataset_name: str | None = None,
) -> str:
    """
    将DataPilot分析结果转换为Markdown报告。

    参数：
        result：
            Agent返回的完整分析结果。

        dataset_name：
            数据集文件名。
            如果不传，则使用dataset_id。

    返回：
        Markdown格式的字符串。
    """

    task_id = result.get(
        "task_id",
        "unknown",
    )

    dataset_id = result.get(
        "dataset_id",
        "unknown",
    )

    question = result.get(
        "question",
        "未提供分析问题",
    )

    status = result.get(
        "status",
        "unknown",
    )

    repair_count = result.get(
        "repair_count",
        0,
    )

    answer = result.get(
        "answer"
    )

    error_message = result.get(
        "error_message"
    )

    plan = result.get(
        "plan"
    )

    execution = result.get(
        "execution"
    )

    generated_code = (
        result.get("generated_code")
        or result.get("current_code")
        or ""
    )

    code_explanation = result.get(
        "code_explanation"
    )

    report_time = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    display_dataset = (
        dataset_name
        or dataset_id
    )

    status_text = {
        "completed": "分析成功",
        "failed": "分析失败",
        "running": "正在执行",
        "pending": "等待执行",
    }.get(
        status,
        status,
    )

    sections = [
        "# DataPilot 数据分析报告",
        "",
        "## 任务信息",
        "",
        f"- 任务ID：`{task_id}`",
        f"- 数据集：`{display_dataset}`",
        f"- 数据集ID：`{dataset_id}`",
        f"- 分析状态：{status_text}",
        f"- 代码修复次数：{repair_count}",
        f"- 报告生成时间：{report_time}",
        "",
        "## 用户问题",
        "",
        str(question),
        "",
        "## 分析计划",
        "",
        _format_plan(plan),
        "",
        "## 分析结论",
        "",
    ]

    if answer:
        sections.append(
            str(answer)
        )

    elif error_message:
        sections.append(
            f"分析任务执行失败：{error_message}"
        )

    else:
        sections.append(
            "暂无分析结论。"
        )

    sections.extend(
        [
            "",
            "## 代码说明",
            "",
            (
                str(code_explanation)
                if code_explanation
                else "暂无代码说明。"
            ),
            "",
            "## 生成的分析代码",
            "",
        ]
    )

    if generated_code:
        sections.extend(
            [
                "```python",
                str(generated_code),
                "```",
            ]
        )

    else:
        sections.append(
            "暂无生成代码。"
        )

    sections.extend(
        [
            "",
            "## 代码执行信息",
            "",
            _format_execution(
                execution
            ),
            "",
            "---",
            "",
            (
                "本报告由DataPilot"
                "可执行智能数据分析Agent生成。"
            ),
        ]
    )

    return "\n".join(sections)