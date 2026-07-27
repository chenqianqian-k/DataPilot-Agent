from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

from app.core.config import settings

from app.report.markdown_report import (
    build_markdown_report,
)


API_BASE_URL = (
    f"http://127.0.0.1:{settings.app_port}"
)

REQUEST_TIMEOUT_SECONDS = 300


st.set_page_config(
    page_title="DataPilot",
    page_icon="📊",
    layout="wide",
)


def api_get(
    path: str,
) -> Any:
    """
    向FastAPI发送GET请求。
    """

    response = requests.get(
        f"{API_BASE_URL}{path}",
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def api_post_json(
    path: str,
    payload: dict[str, Any],
) -> Any:
    """
    向FastAPI发送JSON POST请求。
    """

    response = requests.post(
        f"{API_BASE_URL}{path}",
        json=payload,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    response.raise_for_status()

    return response.json()

def api_delete(path: str) -> dict:
    """
    向FastAPI发送DELETE请求。
    """

    response = requests.delete(
        f"{API_BASE_URL}{path}",
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def upload_dataset(
    uploaded_file: Any,
) -> dict[str, Any]:
    """
    将Streamlit上传文件转发给FastAPI。
    """

    files = {
        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            uploaded_file.type
            or "application/octet-stream",
        )
    }

    response = requests.post(
        f"{API_BASE_URL}/datasets/upload",
        files=files,
        timeout=120,
    )

    response.raise_for_status()

    return response.json()


def show_api_error(
    error: Exception,
) -> None:
    """
    将接口错误显示在页面中。
    """

    if isinstance(
        error,
        requests.HTTPError,
    ):
        response = error.response

        try:
            detail = response.json().get(
                "detail",
                response.text,
            )
        except Exception:
            detail = response.text

        st.error(
            f"接口请求失败：{detail}"
        )

        return

    if isinstance(
        error,
        requests.ConnectionError,
    ):
        st.error(
            "无法连接FastAPI，请确认后端"
            f"{API_BASE_URL}已经启动。"
        )

        return

    st.error(
        f"请求失败："
        f"{type(error).__name__}: {error}"
    )


def render_dataset_profile(
    dataset_id: str,
) -> None:
    """
    显示数据集画像。
    """

    try:
        profile = api_get(
            f"/datasets/{dataset_id}/profile"
        )

    except Exception as exc:
        show_api_error(exc)
        return

    metric_columns = st.columns(4)

    metric_columns[0].metric(
        "数据行数",
        profile["row_count"],
    )

    metric_columns[1].metric(
        "字段数量",
        profile["column_count"],
    )

    metric_columns[2].metric(
        "缺失值",
        profile["total_missing_values"],
    )

    metric_columns[3].metric(
        "重复行",
        profile["duplicate_row_count"],
    )

    column_rows = []

    for column in profile["columns"]:
        column_rows.append(
            {
                "字段": column["name"],
                "Pandas类型": (
                    column["pandas_dtype"]
                ),
                "语义类型": (
                    column["semantic_type"]
                ),
                "非空数量": (
                    column["non_null_count"]
                ),
                "缺失数量": (
                    column["missing_count"]
                ),
                "唯一值数量": (
                    column["unique_count"]
                ),
                "示例": ", ".join(
                    str(value)
                    for value in column.get(
                        "examples",
                        [],
                    )
                ),
            }
        )

    st.dataframe(
        pd.DataFrame(column_rows),
        use_container_width=True,
        hide_index=True,
    )


def render_analysis_result(
    result: dict[str, Any],
) -> None:
    """
    展示Agent分析结果。
    """

    status = result.get("status")

    if status != "completed":
        st.error(
            result.get(
                "error_message",
                "分析任务执行失败",
            )
        )

    else:
        st.success("数据分析任务完成")

    summary_columns = st.columns(3)

    summary_columns[0].metric(
        "任务状态",
        status,
    )

    summary_columns[1].metric(
        "代码修复次数",
        result.get(
            "repair_count",
            0,
        ),
    )

    execution = result.get(
        "execution"
    ) or {}

    execution_time = execution.get(
        "execution_time_seconds",
        0,
    )

    summary_columns[2].metric(
        "执行时间",
        f"{execution_time:.4f} 秒",
    )

    st.subheader("Agent执行轨迹")

    execution_trace = result.get(
        "execution_trace",
        [],
    )

    for index, message in enumerate(
        execution_trace,
        start=1,
    ):
        st.write(f"{index}. {message}")

    plan = result.get("plan")

    if plan:
        with st.expander(
            "查看分析计划",
            expanded=False,
        ):
            st.write(
                f"**分析目标：** "
                f"{plan['objective']}"
            )

            st.write(
                "**所需字段：** "
                + "、".join(
                    plan.get(
                        "required_columns",
                        [],
                    )
                )
            )

            for step in plan.get(
                "steps",
                [],
            ):
                st.markdown(
                    f"**步骤{step['step_id']}："
                    f"{step['title']}**"
                )

                st.write(
                    step["description"]
                )

    generated_code = result.get(
        "generated_code"
    )

    if generated_code:
        with st.expander(
            "查看Agent生成的Python代码",
            expanded=False,
        ):
            st.code(
                generated_code,
                language="python",
            )

            explanation = result.get(
                "code_explanation"
            )

            if explanation:
                st.caption(explanation)

    result_preview = execution.get(
        "result_preview",
        [],
    )

    if result_preview:
        st.subheader("分析结果")

        st.dataframe(
            pd.DataFrame(
                result_preview
            ),
            use_container_width=True,
            hide_index=True,
        )

    generated_files = execution.get(
        "generated_files",
        [],
    )

    for file_path_text in generated_files:
        file_path = Path(
            file_path_text
        ).resolve()

        try:
            is_safe_output = (
                file_path.is_relative_to(
                    settings.output_path
                )
            )
        except ValueError:
            is_safe_output = False

        if (
            is_safe_output
            and file_path.exists()
            and file_path.suffix == ".html"
        ):
            st.subheader("数据可视化")

            html_content = (
                file_path.read_text(
                    encoding="utf-8"
                )
            )

            components.html(
                html_content,
                height=550,
                scrolling=True,
            )

    answer = result.get("answer")

    if answer:
        st.subheader("分析报告")
        st.markdown(answer)


st.title("📊 DataPilot")
st.caption(
    "基于LangGraph和DeepSeek的"
    "可执行智能数据分析Agent"
)


with st.sidebar:
    st.header("数据集管理")

    uploaded_file = st.file_uploader(
        "上传CSV或Excel",
        type=["csv", "xlsx"],
    )

    if st.button(
        "上传并解析",
        use_container_width=True,
        disabled=uploaded_file is None,
    ):
        try:
            with st.spinner(
                "正在上传并解析数据集..."
            ):
                upload_result = (
                    upload_dataset(
                        uploaded_file
                    )
                )

            st.success(
                upload_result["message"]
            )

            st.session_state[
                "selected_dataset_id"
            ] = upload_result[
                "dataset_id"
            ]

            st.rerun()

        except Exception as exc:
            show_api_error(exc)

    if st.button(
        "刷新数据集列表",
        use_container_width=True,
    ):
        st.rerun()

    # =========================
    # 历史分析任务
    # =========================

    st.divider()

    st.subheader("历史分析")

    try:
        history_tasks = api_get(
            "/tasks?limit=20"
        )

    except Exception as exc:
        history_tasks = []

        st.warning(
            f"历史任务加载失败：{exc}"
        )

    if not history_tasks:
        st.caption(
            "当前还没有历史分析记录"
        )

    else:
        # 将任务列表转换成：
        # task_id -> 任务信息
        task_map = {
            task["task_id"]: task
            for task in history_tasks
        }

        task_ids = list(
            task_map.keys()
        )

        def format_task_option(
            task_id: str,
        ) -> str:
            """
            设置历史任务在选择框中的显示文字。
            """

            task = task_map[
                task_id
            ]

            status = task.get(
                "status",
                "unknown",
            )

            question = task.get(
                "question",
                "未命名任务",
            )

            if len(question) > 18:
                question = (
                    question[:18]
                    + "..."
                )

            if status == "completed":
                status_text = "成功"

            elif status == "failed":
                status_text = "失败"

            else:
                status_text = status

            return (
                f"{status_text} | "
                f"{question} | "
                f"{task_id[-6:]}"
            )

        selected_task_id = (
            st.selectbox(
                "选择历史任务",
                options=task_ids,
                format_func=(
                    format_task_option
                ),
            )
        )

        history_col1, history_col2 = (
            st.columns(2)
        )

        with history_col1:
            restore_clicked = (
                st.button(
                    "恢复结果",
                    use_container_width=True,
                )
            )

        with history_col2:
            delete_clicked = (
                st.button(
                    "删除记录",
                    use_container_width=True,
                )
            )

        if restore_clicked:
            try:
                task_result = api_get(
                    (
                        "/tasks/"
                        f"{selected_task_id}"
                    )
                )

                # 保存历史分析结果
                st.session_state[
                    "analysis_result"
                ] = task_result

                # 同时切换到该任务对应的数据集
                history_dataset_id = (
                    task_result.get(
                        "dataset_id"
                    )
                )

                if history_dataset_id:
                    st.session_state[
                        "selected_dataset_id"
                    ] = history_dataset_id

                # 重新运行页面
                st.rerun()

            except Exception as exc:
                show_api_error(exc)

        if delete_clicked:
            try:
                api_delete(
                    (
                        "/tasks/"
                        f"{selected_task_id}"
                    )
                )

                current_result = (
                    st.session_state.get(
                        "analysis_result"
                    )
                )

                # 如果页面目前展示的正是
                # 被删除的任务，则一并清除
                if (
                    current_result
                    and current_result.get(
                        "task_id"
                    )
                    == selected_task_id
                ):
                    del st.session_state[
                        "analysis_result"
                    ]

                st.success(
                    "历史任务已删除"
                )

                st.rerun()

            except Exception as exc:
                show_api_error(exc)


# =========================
# 获取数据集列表
# =========================

try:
    datasets = api_get(
        "/datasets"
    )

except Exception as exc:
    show_api_error(exc)
    datasets = []


# =========================
# 主页面
# =========================

if not datasets:
    st.info(
        "当前还没有数据集，"
        "请先在左侧上传CSV或Excel文件。"
    )

else:
    dataset_options = {
        (
            f"{dataset['file_name']} "
            f"({dataset['row_count']}行 × "
            f"{dataset['column_count']}列)"
        ): dataset["dataset_id"]
        for dataset in datasets
    }

    option_labels = list(
        dataset_options.keys()
    )

    default_index = 0

    selected_dataset_id = (
        st.session_state.get(
            "selected_dataset_id"
        )
    )

    if selected_dataset_id:
        for index, label in enumerate(
            option_labels
        ):
            if (
                dataset_options[label]
                == selected_dataset_id
            ):
                default_index = index
                break

    selected_label = st.selectbox(
        "选择需要分析的数据集",
        options=option_labels,
        index=default_index,
    )

    selected_dataset_id = (
        dataset_options[
            selected_label
        ]
    )

    st.session_state[
        "selected_dataset_id"
    ] = selected_dataset_id

    with st.expander(
        "查看数据集画像",
        expanded=False,
    ):
        render_dataset_profile(
            selected_dataset_id
        )

    st.divider()

    st.subheader(
        "向DataPilot提出问题"
    )

    question = st.text_area(
        "数据分析问题",
        placeholder=(
            "例如：分析不同地区的销售额差异，"
            "指出最高和最低的地区，"
            "并生成柱状图。"
        ),
        height=120,
    )

    analyze_button = st.button(
        "开始分析",
        type="primary",
        use_container_width=True,
    )

    if analyze_button:
        if len(question.strip()) < 2:
            st.warning(
                "请输入有效的数据分析问题。"
            )

        else:
            try:
                with st.spinner(
                    "Agent正在制定计划、"
                    "生成代码并执行分析..."
                ):
                    analysis_result = (
                        api_post_json(
                            "/analysis",
                            {
                                "dataset_id": (
                                    selected_dataset_id
                                ),
                                "question": (
                                    question.strip()
                                ),
                            },
                        )
                    )

                st.session_state[
                    "analysis_result"
                ] = analysis_result

            except Exception as exc:
                show_api_error(exc)

    stored_result = (
        st.session_state.get(
            "analysis_result"
        )
    )

    if stored_result:
        st.divider()

        render_analysis_result(
            stored_result
        )

        # =========================
        # 生成Markdown分析报告
        # =========================

        report_dataset_id = (
            stored_result.get(
                "dataset_id"
            )
        )

        report_dataset_name = None

        # 根据dataset_id找到对应文件名
        for dataset in datasets:
            if (
                dataset.get("dataset_id")
                == report_dataset_id
            ):
                report_dataset_name = (
                    dataset.get(
                        "file_name"
                    )
                )
                break

        markdown_report = (
            build_markdown_report(
                result=stored_result,
                dataset_name=(
                    report_dataset_name
                ),
            )
        )

        report_task_id = (
            stored_result.get(
                "task_id",
                "analysis-report",
            )
        )

        st.download_button(
            label="下载Markdown分析报告",
            data=markdown_report,
            file_name=(
                f"datapilot-"
                f"{report_task_id}.md"
            ),
            mime="text/markdown",
            use_container_width=True,
        )