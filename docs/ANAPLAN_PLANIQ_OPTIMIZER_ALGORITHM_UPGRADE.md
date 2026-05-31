# ChainPilot AI 对标 PlanIQ / Optimizer 的算法升级设计与验收

日期：2026-05-31

## 1. 对标依据

本轮只采用 Anaplan 官方公开资料作为产品能力参考：

- PlanIQ / Forecaster 支持多种预测算法、自动选择或配置算法、模型质量指标、回测和 Explainability。
  参考：https://help.anaplan.com/planiq-algorithms--b2a08e5a-156f-4bb9-8fcd-a85fa8169046
- PlanIQ 预测模型列表展示算法、预测周期、模型质量、回测、Explainability、错误或警告。
  参考：https://help.anaplan.com/forecast-models-list-in-planiq-97efc5eb-cfb3-42e8-9bff-fbee08cde564
- Explainability 应解释历史特征、相关数据特征及其对预测结果的影响。
  参考：https://help.anaplan.com/explainability-2fdb7217-4c60-4a04-bd60-daa61855f25f
- Optimizer 以目标函数、决策变量和约束求解最优或可行方案，常用于供应链、库存、网络、生产和资源分配。
  参考：https://help.anaplan.com/optimizer-e8eac6ea-bfac-43a1-abbb-3dad60cea523
- Optimizer 关键审计概念包括 MILP、MIP Gap、Feasibility、Objective、Variable、Constraint 和 Timeout。
  参考：https://help.anaplan.com/glossary-of-optimizer-terms-f97e794b-176d-4632-93c3-a15fa51e415a
- Optimizer 有不可行、超时、MIP Gap、线性/MILP 约束范围等限制，界面应暴露这些状态给业务用户。
  参考：https://help.anaplan.com/optimizer-limitations-094f15b5-9ef8-4618-b214-f97ab335fd3e

## 2. 升级目标

ChainPilot 不把 LLM 当作主决策引擎。生产决策路径是：

SAP 明细数据 -> 预测模型/优化器 -> 约束校验 -> 证据链 -> LLM 解释/摘要 -> 人工审批 -> SAP 回写草稿。

本轮算法升级聚焦两点：

- 缺料预测从“只有规则仿真”升级为“模型候选回测 + 最优模型选择 + Monte Carlo 风险仿真”。
- 现金释放从“求出动作包”升级为“暴露 Optimizer 式求解审计：目标函数、变量、约束、MIP Gap、约束利用率”。

## 3. 已实现设计

### 3.1 缺料风险预测

文件：`chainpilot_ai/algorithms/shortage_risk_14d.py`

实现方式：

- 对每个物料/工厂读取 SAP Mock 的历史消耗、未来计划需求、库存、采购订单和供应商履约。
- 对历史消耗做 holdout 回测。
- 候选预测模型：
  - 近四周移动平均。
  - 趋势修正组合。
  - 稳健中位数。
- 用 WAPE 和 MAE 选择最佳模型。
- 把最佳模型的预测误差、置信度、日均预测量、历史波动、候选模型指标写入 evidence。
- Monte Carlo 缺料仿真继续使用 SAP 计划需求和供应商延迟样本，预测模型用于补充需求波动不确定性。

输出新增字段：

- `forecast_model`
- `forecast_model_label`
- `forecast_wape`
- `forecast_mae`
- `forecast_confidence`
- `forecast_driver_summary`
- `forecast_model_candidates`

汇总新增字段：

- `forecast_model_counts`
- `avg_forecast_wape`
- `avg_forecast_confidence`
- `forecast_backtest_materials`

### 3.2 现金释放优化器

文件：`chainpilot_ai/algorithms/cash_release_pr_po.py`

实现方式：

- 仍先生成采购申请/采购订单候选动作，并过滤保护物料、冻结期、MOQ/MPQ、服务水平余量等硬约束。
- 对通过硬约束的动作建立二进制决策变量。
- 目标函数：最大化现金影响，扣除风险惩罚和供应商确认惩罚。
- 优先使用 SciPy HiGHS MILP；不可用时使用同一约束模型的精确整数枚举。
- 输出求解器名称、求解状态、MIP Gap、超时配置、求解消息、变量数量、约束数量、正收益候选数。
- 输出每条约束的使用量、上限、利用率和是否为紧约束。

输出新增字段：

- `mip_gap`
- `time_limit_seconds`
- `solver_message`
- `decision_variable_count`
- `binary_variable_count`
- `positive_score_count`
- `objective_components`
- `constraint_utilization`

### 3.3 算法质量验收

文件：

- `chainpilot_ai/algorithms/quality.py`
- `chainpilot_ai/scripts/verify_algorithm_quality.py`
- `tmp/algorithm_quality_report.json`

质量门禁：

| 维度 | 门槛 | 当前 mock 结果 |
| --- | --- | --- |
| 缺料召回率 | >= 0.90 | 0.9512 |
| 缺料预测准确率 | >= 0.90 | 0.9838 |
| 误干预率 | <= 0.05 | 0.0162 |
| 预测模型 WAPE | <= 0.12 | 0.0619 |
| 硬约束违规 | = 0 | 0 |
| 优化器求解状态 | OPTIMAL / FEASIBLE | OPTIMAL |
| MIP Gap | <= 0.001 | 0.0 |
| 资金动作包规模 | >= 15 条且金额 > 0 | 20 条 / 1416.96 万元 |
| 资金兑现率 | >= 0.80 | 0.86 |

## 4. Mock 数据质量说明

当前 mock 数据不是平铺样例，而是关联的 SAP 业务账套模拟：

- 180 个物料，覆盖工厂、产品线、ABC/XYZ、单价、保护物料、采购组。
- 180 条库存，包含可用库存、质检库存、冻结库存和安全库存。
- 320 行采购申请、280 行采购订单，包含交期、供应商、单价、未清数量和确认状态。
- 510 条未来计划需求，关联生产订单、销售订单和成品。
- 1440 条历史消耗，用于预测模型回测。
- 1080 条供应商履约，用于供应延迟和质量异常估计。
- 180 条 MRP 参数，覆盖安全库存、MOQ、MPQ、计划交货期。

因此 mock 阶段可以验证：

- 预测模型能否在历史消耗上回测并解释误差。
- 缺料仿真能否命中实际短缺结果。
- 优化器能否在服务水平、冻结期、保护物料、MOQ/MPQ、审批容量等约束下选动作包。
- 现金建议能否做到零硬约束违规。

## 5. 复现命令

运行算法质量验收：

```bash
python3 -m chainpilot_ai.scripts.verify_algorithm_quality
```

报告输出：

```text
tmp/algorithm_quality_report.json
```

运行自动测试：

```bash
pytest
```

## 6. 下一步真实数据接入

接入两年 SAP 历史数据后，建议按以下顺序上线：

1. 只读抽取历史消耗、需求、库存、PR、PO、供应商履约和 MRP 参数。
2. 用同一验收脚本替换 mock snapshot loader，先跑历史回测。
3. 按产品线/工厂分层看 WAPE、召回率、准确率、误干预率和硬约束违规。
4. 在训练优化页面由业务负责人确认阈值策略，不自动写 SAP。
5. 只生成审批包和 SAP 回写草稿，真实回写继续走人工审批。
