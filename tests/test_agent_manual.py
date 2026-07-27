from app.agent.analysis_agent import (
    data_analysis_agent,
)
from app.data.manager import dataset_manager


datasets = dataset_manager.list_datasets()

if not datasets:
    raise RuntimeError(
        "当前没有已管理的数据集"
    )

dataset = datasets[0]

print("========== 使用数据集 ==========")
print("ID：", dataset.dataset_id)
print("文件：", dataset.file_name)

result = (
    data_analysis_agent.analyze_dataset(
        dataset_id=dataset.dataset_id,
        question=(
            "分析不同地区的销售额差异，"
            "指出最高和最低的地区，"
            "并生成柱状图。"
        ),
    )
)

print("\n========== 任务状态 ==========")
print(result.status)

print("\n========== 执行轨迹 ==========")

for index, message in enumerate(
    result.execution_trace,
    start=1,
):
    print(f"{index}. {message}")

print("\n========== 最终代码 ==========")
print(result.generated_code)

print("\n========== 最终回答 ==========")
print(
    result.answer
    or result.error_message
)