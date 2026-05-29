# Algorithm Runtime v2.0 改进实现说明

日期：2026-05-29

需求来源：`cankao/ChainPilot_AI_Algorithm_Runtime_改进开发需求_v2.0.pdf`

## 1. 改进要求结论

v2.0 的核心要求是把主线从“外部报告或静态 Demo 数据导入”改为：

```text
Mock SAP Snapshot -> Algorithm Run -> Algorithm Result -> Recommendation -> Evidence -> AI Explanation -> Approval / Writeback Draft
```

因此，后续页面、AI 解释和审批都必须追溯到 `snapshot_id`、`algorithm_run` 和 `algorithm_result`。AI 不能直接生成数量、金额或缺料概率，只能解释 Algorithm Result 和 Evidence。

## 2. 本次落地范围

### 2.1 Mock SAP Snapshot

新增 `demo_data/mock_sap_snapshot_v1.json`，按 SAP 业务对象建模：

- `materials`
- `inventory`
- `pr_lines`
- `po_lines`
- `bom_components`
- `planned_demands`
- `consumption_history`
- `supplier_performance`
- `mrp_parameters`

数据覆盖 v2.0 要求的三类场景：

- 未来 14 天缺料风险物料
- PR/PO 现金释放候选动作
- 计划交货期、安全库存、MOQ/MPQ 主数据异常

### 2.2 新增 DocType

新增 Algorithm Runtime 核心对象：

- `SAP Snapshot Run`
- `Algorithm Definition`
- `Algorithm Run`
- `Algorithm Result`
- `AI Explanation`

新增五类 SAP 明细快照对象，与已有 Material、Inventory、PR、PO 共同组成九类 Snapshot 明细：

- `SAP BOM Component Snapshot`
- `SAP Planned Demand Snapshot`
- `SAP Consumption History Snapshot`
- `SAP Supplier Performance Snapshot`
- `SAP MRP Parameter Snapshot`

同时增强 `Recommendation`：

- `snapshot_id`
- `algorithm_run`
- `algorithm_result`
- `scenario_id`
- `recommendation_level`
- `constraint_verdict`
- `blocked_reason`
- `evidence_count`
- `execution_owner`
- `actual_realized_amount`

## 3. 三大算法实现

### 3.1 `SHORTAGE_RISK_14D_PROB`

实现位置：`chainpilot_ai/algorithms/shortage_risk_14d.py`

实现方式：

- 基于库存、计划需求、PO、消耗历史和供应商交付历史。
- 使用确定性种子的 600 次轻量 Monte Carlo 仿真。
- 输出缺料概率、P50 缺料日期、P90 缺口、影响工单、影响成品和建议补救动作。

### 3.2 `CASH_RELEASE_PR_PO_OPT`

实现位置：`chainpilot_ai/algorithms/cash_release_pr_po.py`

实现方式：

- 生成 PR 减量/取消、PO 延期候选动作。
- 校验冻结期、保护物料、已确认 PO、MOQ/MPQ、安全库存等硬约束。
- 对可执行动作做风险收益排序，输出 selected 和 blocked 两类动作。
- 当前为 Professional-lite 贪心优化层，保留后续替换 OR-Tools / PuLP 的输入输出契约。

### 3.3 `MASTER_DATA_DIAGNOSIS_STAT`

实现位置：`chainpilot_ai/algorithms/master_data_diagnosis.py`

实现方式：

- 用供应商收货历史计算计划交货期 P50/P80/P95。
- 用消耗历史和交期波动计算服务水平安全库存建议。
- 检查 MOQ/MPQ 与实际消耗规模的偏差。
- 输出样本数、置信度、影响金额和建议修正值。

## 4. AI 与算法边界

已新增 `chainpilot_ai/agent/explanation_service.py`，当前采用证据绑定模板生成解释，严格遵守：

- 解释必须来自 Algorithm Result、Recommendation、Evidence 和 Constraint Check。
- 没有 Evidence 时返回 `NEED_EVIDENCE`。
- 解释中包含 algorithm_code、algorithm_version、snapshot_id、algorithm_run_id、recommendation_id 和 evidence_ids_used。
- 不生成算法数值，不改写数量、金额、概率。

后续接真实 LLM 时，应替换解释生成内部实现，但保持当前输入输出契约和证据校验。

## 5. 新增脚本

```bash
python3 -m chainpilot_ai.scripts.import_mock_sap_snapshot
python3 -m chainpilot_ai.scripts.seed_algorithm_definitions
python3 -m chainpilot_ai.scripts.run_mvp_algorithms
python3 -m chainpilot_ai.scripts.verify_algorithm_runtime
```

对应 bench 方式：

```bash
bench --site chainpilot.localhost execute chainpilot_ai.scripts.import_mock_sap_snapshot.run
bench --site chainpilot.localhost execute chainpilot_ai.scripts.seed_algorithm_definitions.run
bench --site chainpilot.localhost execute chainpilot_ai.scripts.run_mvp_algorithms.run
bench --site chainpilot.localhost execute chainpilot_ai.scripts.verify_algorithm_runtime.run
```

## 6. 当前验证结果

`python3 -m chainpilot_ai.scripts.verify_algorithm_runtime`：

- `AR-001` Pass：Mock SAP Snapshot 契约有效。
- `AR-002` Pass：Algorithm Runtime DocType JSON 存在且有效。
- `AR-003` Pass：三大算法均成功运行。
- `AR-004` Pass：Recommendation 均带 snapshot、algorithm_run、algorithm_result 和 evidence。

当前本地 dry-run 结果：

- Algorithm Run：3
- Algorithm Result：55
- 缺料风险结果：6
- 现金释放候选动作：26
- 现金释放选中动作：18
- 现金释放阻断动作：8
- 主数据异常：23
- 由算法结果生成的 Recommendation：47
- Evidence / Constraint Check / AI Explanation：均为 47

## 7. 页面改动

`Command Center` 已改为读取 `chainpilot_ai.algorithms.service.get_algorithm_runtime_dashboard`：

- 展示未来 14 天缺料风险 Top 10。
- 展示今日可调整 PR/PO 动作。
- 展示 SAP 主数据异常 Top 10。
- 展示最近 Algorithm Run。
- 主按钮改为“运行算法”，调用 `run_algorithm_runtime_rpc`。

## 8. 仍需后续加强

1. 当前现金释放优化为 Professional-lite 贪心实现，后续可替换 OR-Tools CP-SAT。
2. 当前 AI Explanation 是证据模板实现，后续接真实 LLM Provider。
3. 当前页面未新增独立 Shortage Radar、Cash Release Workbench、Master Data Health 页面，Command Center 已先承载三类结果。
4. 当前真实 SAP OData 仍未接入，后续只替换 Snapshot Loader，不重写 Algorithm Runtime。
