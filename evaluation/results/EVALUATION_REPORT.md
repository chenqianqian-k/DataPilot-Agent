# DataPilot Evaluation Report

> Automated evaluation for executable data analysis and code self-repair.

生成时间：`2026-07-31T18:13:21`

## 评估设计

DataPilot 使用固定数据集、预计算标准答案和规则化评分器，
评估 Agent 的分析规划、Python 代码生成、代码执行、
结构化结果正确性、排序一致性和图表生成能力。

系统还使用独立的故障评估 LangGraph，在代码生成与执行之间
注入字段拼写错误、缺失字段、未定义变量和类型错误，
验证代码诊断及自动修复能力。

## 基础能力评估

| Metric | Result |
|---|---:|
| Total Cases | 15 |
| Passed Cases | 15 |
| Pass Rate | 100.0% |
| Execution Success Rate | 100.0% |
| Result Accuracy | 100.0% |
| First-pass Success Rate | 100.0% |
| Chart Success Rate | 100.0% |
| Average Repair Count | 0.0 |
| Average Duration | 28.98s |

### 基础任务明细

| Case | Dataset | Category | Execution | Result | Chart | Repairs | Time |
|---|---|---|---:|---:|---:|---:|---:|
| sales_001 | sales.csv | group_aggregation | PASS | PASS | PASS | 0 | 24.66s |
| sales_002 | sales.csv | time_series | PASS | PASS | PASS | 0 | 24.14s |
| sales_003 | sales.csv | ranking | PASS | PASS | PASS | 0 | 37.75s |
| sales_004 | sales.csv | top_n | PASS | PASS | PASS | 0 | 18.88s |
| sales_005 | sales.csv | average | PASS | PASS | PASS | 0 | 45.60s |
| employees_001 | employees.xlsx | count | PASS | PASS | PASS | 0 | 70.96s |
| employees_002 | employees.xlsx | average | PASS | PASS | PASS | 0 | 17.49s |
| employees_003 | employees.xlsx | group_comparison | PASS | PASS | PASS | 0 | 27.99s |
| employees_004 | employees.xlsx | performance | PASS | PASS | PASS | 0 | 22.03s |
| employees_005 | employees.xlsx | distribution | PASS | PASS | PASS | 0 | 16.55s |
| orders_001 | orders.csv | distribution | PASS | PASS | PASS | 0 | 13.48s |
| orders_002 | orders.csv | filter_aggregation | PASS | PASS | PASS | 0 | 26.97s |
| orders_003 | orders.csv | filter_average | PASS | PASS | PASS | 0 | 32.68s |
| orders_004 | orders.csv | top_n | PASS | PASS | PASS | 0 | 24.73s |
| orders_005 | orders.csv | time_series | PASS | PASS | PASS | 0 | 30.80s |

## 故障注入与自动修复评估

故障评估工作流：

```text
generate_code
    ↓
inject_fault
    ↓
execute_code ── failure ──→ repair_code
    ↑                           │
    └───────────────────────────┘

```

## 故障评估指标

| Metric | Result |
|---|---:|
| Total Fault Cases | 8 |
| Passed Cases | 8 |
| Final Pass Rate | 100.0% |
| Fault Injection Rate | 100.0% |
| Failure Trigger Rate | 100.0% |
| Error Type Match Rate | 100.0% |
| Repair Trigger Rate | 100.0% |
| Repair Success Rate | 100.0% |
| Accuracy After Repair | 100.0% |
| Average Repair Count | 1.0 |
| Average Duration | 28.07s |

### 故障任务明细

| Case | Fault Type | Expected Error | Repair | Correct After Repair | Repairs | Time |
|---|---|---|---:|---:|---:|---:|
| fault_sales_001 | column_typo | KeyError | PASS | PASS | 1 | 15.96s |
| fault_sales_002 | type_error | TypeError | PASS | PASS | 1 | 45.31s |
| fault_sales_004 | undefined_variable | NameError | PASS | PASS | 1 | 15.34s |
| fault_employees_001 | missing_column | KeyError | PASS | PASS | 1 | 38.70s |
| fault_employees_002 | column_typo | KeyError | PASS | PASS | 1 | 27.45s |
| fault_orders_001 | undefined_variable | NameError | PASS | PASS | 1 | 33.91s |
| fault_orders_002 | column_typo | KeyError | PASS | PASS | 1 | 25.98s |
| fault_orders_005 | missing_column | KeyError | PASS | PASS | 1 | 21.91s |

## 自动评分规则

基础评估采用确定性规则完成评分：

- 检查Python代码是否执行成功；
- 检查结构化结果所需字段；
- 检查结果行数和分组对象；
- 在允许误差范围内比较数值；
- 检查排序是否符合问题要求；
- 检查图表文件是否成功生成。

故障评估还要求：

- 故障注入节点成功运行；
- 第一次代码执行产生预期异常；
- LangGraph进入repair_code节点；
- 修复后的代码重新执行成功；
- 修复后的结果仍与标准答案一致。

## 失败任务

本次基础评估与故障评估均未出现失败任务。

## 原始评估文件

- 基础评估：`evaluation_20260731_145445.json`
- 故障评估：`fault_evaluation_20260731_171136.json`

## 说明

本报告反映DataPilot在当前固定基础测试集与故障注入
测试集上的表现，不代表系统对任意数据和任意问题
都具有相同的准确率。
