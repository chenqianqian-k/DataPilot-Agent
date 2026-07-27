from fastapi import (
    FastAPI,
    File,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.data.manager import (
    DatasetManagerError,
    DatasetNotFoundError,
    dataset_manager,
)
from app.schemas.dataset import (
    DatasetDeleteResponse,
    DatasetListItem,
    DatasetProfile,
    DatasetUploadResponse,
)

from app.agent.analysis_agent import (
    data_analysis_agent,
)
from app.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisTaskDeleteResponse,
    AnalysisTaskSummary,
)

from app.storage.task_store import (
    TaskNotFoundError,
    TaskStoreError,
    analysis_task_store,
)

app = FastAPI(
    title="DataPilot API",
    description=(
        "基于LangGraph和DeepSeek的"
        "可执行智能数据分析Agent"
    ),
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    """
    返回服务基本信息。
    """

    return {
        "name": settings.app_name,
        "message": "DataPilot API正在运行",
        "docs": "/docs",
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    """
    检查后端是否正常运行。
    """

    return {
        "status": "healthy",
        "service": settings.app_name,
        "model": settings.deepseek_model,
    }


@app.post(
    "/datasets/upload",
    response_model=DatasetUploadResponse,
)
async def upload_dataset(
    file: UploadFile = File(...),
) -> DatasetUploadResponse:
    """
    上传CSV或Excel数据集。
    """

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="上传文件缺少文件名",
        )

    try:
        content = await file.read()

        return dataset_manager.save_dataset(
            original_name=file.filename,
            content=content,
        )

    except DatasetManagerError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"数据集上传失败："
                f"{type(exc).__name__}: {exc}"
            ),
        ) from exc

    finally:
        await file.close()


@app.get(
    "/datasets",
    response_model=list[DatasetListItem],
)
def list_datasets() -> list[DatasetListItem]:
    """
    查询已经上传的数据集。
    """

    return dataset_manager.list_datasets()


@app.get(
    "/datasets/{dataset_id}/profile",
    response_model=DatasetProfile,
)
def get_dataset_profile(
    dataset_id: str,
) -> DatasetProfile:
    """
    查询指定数据集的数据画像。
    """

    try:
        return (
            dataset_manager
            .get_dataset_profile(dataset_id)
        )

    except DatasetNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except DatasetManagerError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@app.delete(
    "/datasets/{dataset_id}",
    response_model=DatasetDeleteResponse,
)
def delete_dataset(
    dataset_id: str,
) -> DatasetDeleteResponse:
    """
    删除指定数据集。
    """

    try:
        return dataset_manager.delete_dataset(
            dataset_id
        )

    except DatasetNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except DatasetManagerError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@app.post(
    "/analysis",
    response_model=AnalysisResponse,
)
async def analyze_dataset(
    request: AnalysisRequest,
) -> AnalysisResponse:
    """
    调用LangGraph执行数据分析任务。
    """

    result = (
        data_analysis_agent
        .analyze_dataset(
            dataset_id=request.dataset_id,
            question=request.question,
        )
    )

    return result

@app.get(
    "/tasks",
    response_model=list[AnalysisTaskSummary],
)
def list_analysis_tasks(
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="最多返回多少条历史任务",
    ),
    dataset_id: str | None = Query(
        default=None,
        description="按照数据集ID筛选任务",
    ),
) -> list[AnalysisTaskSummary]:
    """
    查询历史分析任务。
    """

    try:
        task_rows = (
            analysis_task_store.list_tasks(
                limit=limit,
                dataset_id=dataset_id,
            )
        )

        return [
            AnalysisTaskSummary.model_validate(
                row
            )
            for row in task_rows
        ]

    except TaskStoreError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@app.get(
    "/tasks/{task_id}",
    response_model=AnalysisResponse,
)
def get_analysis_task(
    task_id: str,
) -> AnalysisResponse:
    """
    查询指定任务的完整分析结果。
    """

    try:
        return analysis_task_store.get_task(
            task_id
        )

    except TaskNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except TaskStoreError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@app.delete(
    "/tasks/{task_id}",
    response_model=AnalysisTaskDeleteResponse,
)
def delete_analysis_task(
    task_id: str,
) -> AnalysisTaskDeleteResponse:
    """
    删除指定历史分析任务。
    """

    try:
        analysis_task_store.delete_task(
            task_id
        )

        return AnalysisTaskDeleteResponse(
            task_id=task_id,
            deleted=True,
            message="历史分析任务删除成功",
        )

    except TaskNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except TaskStoreError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc