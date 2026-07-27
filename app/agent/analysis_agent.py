from pathlib import Path
from uuid import uuid4

from app.agent.graph import analysis_graph
from app.agent.state import AnalysisAgentState
from app.data.manager import dataset_manager
from app.schemas.analysis import AnalysisResponse

from app.storage.task_store import (
    analysis_task_store,
)


class DataAnalysisAgent:
    """
    DataPilot对外统一入口。

    负责：
    1. 检查和整理用户输入
    2. 创建LangGraph初始State
    3. 调用LangGraph执行完整分析
    4. 将最终State转换成AnalysisResponse
    """

    def __init__(
        self,
        max_repair_attempts: int = 2,
    ) -> None:
        """
        初始化DataPilot Agent。
        """

        if max_repair_attempts < 0:
            raise ValueError(
                "max_repair_attempts不能小于0"
            )

        self.max_repair_attempts = (
            max_repair_attempts
        )

    def analyze(
        self,
        file_path: str | Path,
        question: str,
        dataset_id: str | None = None,
    ) -> AnalysisResponse:
        """
        使用文件路径执行完整的数据分析任务。
        """

        task_id = f"task-{uuid4().hex}"

        path = Path(file_path).resolve()

        resolved_dataset_id = (
            dataset_id
            if dataset_id
            else f"dataset-{path.stem}"
        )

        cleaned_question = question.strip()

        if len(cleaned_question) < 2:
            return AnalysisResponse(
                task_id=task_id,
                dataset_id=resolved_dataset_id,
                question=(
                    cleaned_question
                    or "无有效问题"
                ),
                status="failed",
                error_message=(
                    "用户问题不能为空或过短"
                ),
            )

        initial_state: AnalysisAgentState = {
            "task_id": task_id,
            "dataset_id": resolved_dataset_id,
            "file_path": str(path),
            "question": cleaned_question,
            "status": "pending",
            "error_message": None,
            "repair_count": 0,
            "max_repair_attempts": (
                self.max_repair_attempts
            ),
            "execution_trace": [
                "LangGraph分析任务已创建"
            ],
        }

        try:
            final_state = analysis_graph.invoke(
                initial_state
            )

        except Exception as exc:
            return AnalysisResponse(
                task_id=task_id,
                dataset_id=resolved_dataset_id,
                question=cleaned_question,
                status="failed",
                execution_trace=[
                    (
                        "LangGraph执行异常："
                        f"{type(exc).__name__}"
                    )
                ],
                error_message=(
                    "LangGraph执行失败："
                    f"{type(exc).__name__}: {exc}"
                ),
            )

        response = self._build_response(
            final_state=final_state
        )

        analysis_task_store.save_task(
            response
        )

        return response

    def analyze_dataset(
        self,
        dataset_id: str,
        question: str,
    ) -> AnalysisResponse:
        """
        根据dataset_id执行数据分析。

        这是FastAPI和前端主要使用的入口。
        """

        cleaned_dataset_id = (
            dataset_id.strip()
        )

        cleaned_question = question.strip()

        if not cleaned_dataset_id:
            return AnalysisResponse(
                task_id=(
                    f"task-{uuid4().hex}"
                ),
                dataset_id="invalid-dataset",
                question=(
                    cleaned_question
                    or "无有效问题"
                ),
                status="failed",
                error_message=(
                    "dataset_id不能为空"
                ),
            )

        if len(cleaned_question) < 2:
            return AnalysisResponse(
                task_id=(
                    f"task-{uuid4().hex}"
                ),
                dataset_id=cleaned_dataset_id,
                question=(
                    cleaned_question
                    or "无有效问题"
                ),
                status="failed",
                error_message=(
                    "用户问题不能为空或过短"
                ),
            )

        try:
            file_path = (
                dataset_manager
                .get_dataset_path(
                    cleaned_dataset_id
                )
            )

        except Exception as exc:
            return AnalysisResponse(
                task_id=(
                    f"task-{uuid4().hex}"
                ),
                dataset_id=cleaned_dataset_id,
                question=cleaned_question,
                status="failed",
                error_message=(
                    "获取数据集失败："
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
            )

        return self.analyze(
            file_path=file_path,
            question=cleaned_question,
            dataset_id=cleaned_dataset_id,
        )

    @staticmethod
    def _build_response(
        final_state: AnalysisAgentState,
    ) -> AnalysisResponse:
        """
        将LangGraph最终State转换为API响应。
        """

        task_id = final_state["task_id"]
        dataset_id = final_state["dataset_id"]
        question = final_state["question"]

        status = final_state.get(
            "status",
            "failed",
        )

        plan = final_state.get("plan")

        execution = final_state.get(
            "execution"
        )

        generated_code = final_state.get(
            "current_code"
        )

        code_explanation = final_state.get(
            "code_explanation"
        )

        repair_count = final_state.get(
            "repair_count",
            0,
        )

        execution_trace = final_state.get(
            "execution_trace",
            [],
        )

        if status == "completed":
            return AnalysisResponse(
                task_id=task_id,
                dataset_id=dataset_id,
                question=question,
                status="completed",
                plan=plan,
                generated_code=generated_code,
                code_explanation=code_explanation,
                execution=execution,
                repair_count=repair_count,
                execution_trace=execution_trace,
                answer=final_state.get(
                    "answer"
                ),
                error_message=None,
            )

        return AnalysisResponse(
            task_id=task_id,
            dataset_id=dataset_id,
            question=question,
            status="failed",
            plan=plan,
            generated_code=generated_code,
            code_explanation=code_explanation,
            execution=execution,
            repair_count=repair_count,
            execution_trace=execution_trace,
            answer=None,
            error_message=final_state.get(
                "error_message",
                "分析任务执行失败",
            ),
        )


data_analysis_agent = DataAnalysisAgent(
    max_repair_attempts=2
)