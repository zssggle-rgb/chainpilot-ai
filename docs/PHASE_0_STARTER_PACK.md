# ChainPilot AI 阶段 0 启动包

版本：v0.1  
日期：2026-05-28  
用途：进入开发前冻结 MVP 范围、数据契约、SAP 接口输入和第一周执行动作。  

## 1. 阶段 0 目标

阶段 0 不追求业务功能完整交付，只交付可开工的工程和业务契约：

1. MVP 范围冻结。
2. Demo 数据字段冻结。
3. SAP 只读接口清单冻结。
4. 核心 DocType 最小字段冻结。
5. 第一周工程任务排期冻结。

完成阶段 0 后，开发团队可以直接开始 M0 项目初始化和 M1 报告产品化。

## 2. 范围冻结

### 2.1 MVP 主闭环

```text
真实 SAP 分析结果
  -> Optimization Session
  -> Scenario Result
  -> Recommendation
  -> Evidence
  -> AI Explanation
  -> Approval Package
  -> SAP Writeback Draft
  -> Execution Result / Feedback / Learning Signal
```

### 2.2 第一版必须做

| 编号 | 范围 | 说明 |
| --- | --- | --- |
| S-001 | Frappe App 基座 | App 名 `chainpilot_ai`，使用 DocType、Workspace、权限、后台任务 |
| S-002 | Demo 数据导入 | 从真实 SAP 分析结果导入优化会话、方案、动作和证据 |
| S-003 | 控制塔 | 展示基线金额、机会金额、推荐方案、待审批动作 |
| S-004 | Action Inbox | 展示 Recommendation 列表、筛选、状态、风险标签 |
| S-005 | 动作详情 | 展示 SAP 单据行、原值/建议值、金额、风险、证据、约束 |
| S-006 | 证据解释 | 每条正式 AI Explanation 必须绑定 Evidence |
| S-007 | 审批包 | 多条 Recommendation 可打包审批 |
| S-008 | 回写草稿 | Approved Recommendation 可生成 SAP Writeback Draft |
| S-009 | 反馈学习 | 采纳、拒绝、供应商反馈、兑现结果可记录 |

### 2.3 第一版明确不做

| 编号 | 不做范围 | 原因 |
| --- | --- | --- |
| N-001 | 自动写 SAP 生产环境 | 风险高，需企业审批、DEV/QA 验证和灰度 |
| N-002 | 重写完整优化算法 | MVP 先封装已有结果和算法接口 |
| N-003 | 把 HTML 报告做成静态页面 | HTML 是现状参考，不是产品需求 |
| N-004 | 全量多组织权限模型 | MVP 先按角色和最小组织字段预留 |
| N-005 | 强自动化采购决策 | 第一版必须保留人工审批 |

## 3. Demo 数据契约

Demo 数据用于在没有真实 SAP OData 接入前演示主闭环。字段要足够支撑页面、解释、审批和回写草稿。

### 3.1 Optimization Session

| 字段 | 类型 | 必填 | 示例 | 说明 |
| --- | --- | --- | --- | --- |
| session_id | Data | 是 | CCO-202605-001 | 优化运行编号 |
| source_system | Data | 是 | AIPLAN_DB | 数据来源 |
| source_report | Data | 是 | may_procurement_optimization_report.html | 参考报告文件 |
| baseline_amount | Currency | 是 | 643568209 | 当前采购基线 |
| material_count | Int | 是 | 5015 | 涉及物料数 |
| sample_count | Int | 是 | 499 | 参数采样次数 |
| best_solution_count | Int | 是 | 84 | 最优解数量 |
| run_date | Date | 是 | 2026-05-15 | 优化日期 |
| status | Select | 是 | Imported | 导入状态 |

### 3.2 Scenario Result

| 字段 | 类型 | 必填 | 示例 | 说明 |
| --- | --- | --- | --- | --- |
| result_id | Data | 是 | RST-202605-001 | 方案结果编号 |
| session_id | Link | 是 | CCO-202605-001 | 来源优化会话 |
| strategy_name | Data | 是 | 精准分类方案 | 方案名称 |
| strategy_type | Select | 是 | Recommended | Conservative / Recommended / Aggressive |
| purchase_amount | Currency | 是 | 474000000 | 预计采购金额 |
| cash_release | Currency | 是 | 170000000 | 预计现金释放 |
| cash_release_rate | Percent | 是 | 26.4 | 相对基线释放比例 |
| risk_level | Select | 是 | Low | 风险等级 |
| recommendation_count | Int | 是 | 126 | 动作数量 |
| ai_recommendation | Text | 否 | 节省空间大且安全库存不变 | 推荐理由 |

### 3.3 Recommendation

| 字段 | 类型 | 必填 | 示例 | 说明 |
| --- | --- | --- | --- | --- |
| recommendation_id | Data | 是 | REC-202605-000123 | 动作编号 |
| result_id | Link | 是 | RST-202605-001 | 来源方案 |
| action_type | Select | 是 | REDUCE_PR_QTY | 动作类型 |
| sap_object_type | Select | 是 | PR | PR / PO / MRP_PARAM / PLANNED_ORDER |
| sap_doc_no | Data | 是 | 1000123456 | SAP 单据号 |
| sap_item_no | Data | 是 | 00010 | SAP 行号 |
| material_code | Data | 是 | MAT-0008891 | 物料编码 |
| material_name | Data | 否 | 控制板组件 | 物料名称 |
| plant | Data | 是 | CN01 | 工厂 |
| supplier | Data | 否 | S000982 | 供应商 |
| purchasing_group | Data | 否 | PG01 | 采购组 |
| product_line | Data | 否 | 空调 | 产品线 |
| before_qty | Float | 否 | 12000 | 原数量 |
| after_qty | Float | 否 | 9500 | 建议数量 |
| before_date | Date | 否 | 2026-06-15 | 原交期 |
| after_date | Date | 否 | 2026-06-28 | 建议交期 |
| cash_release | Currency | 是 | 860000 | 现金释放 |
| saving_type | Select | 是 | Cash Release | Cash Release / Book Saving / Purchase Deferral |
| inventory_days_before | Float | 否 | 48 | 调整前覆盖天数 |
| inventory_days_after | Float | 否 | 36 | 调整后覆盖天数 |
| shortage_risk_before | Percent | 否 | 1.8 | 调整前缺料风险 |
| shortage_risk_after | Percent | 否 | 2.4 | 调整后缺料风险 |
| confidence_score | Float | 否 | 0.87 | 推荐置信度 |
| approval_status | Select | 是 | Pending | Pending / Approved / Rejected |
| writeback_status | Select | 是 | Not Created | Not Created / Draft / Sent / Success / Failed |
| explanation_status | Select | 是 | Ready | Ready / NEED_EVIDENCE / Failed |

### 3.4 Recommendation Evidence

| 字段 | 类型 | 必填 | 示例 | 说明 |
| --- | --- | --- | --- | --- |
| evidence_id | Data | 是 | EVD-001 | 证据编号 |
| recommendation_id | Link | 是 | REC-202605-000123 | 关联动作 |
| source_type | Select | 是 | Snapshot | Snapshot / Report / Rule / Simulation |
| source_id | Data | 是 | SAP_INVENTORY_CN01_MAT-0008891 | 来源对象 |
| metric_name | Data | 是 | inventory_days_after | 指标名 |
| metric_value | Data | 是 | 36 | 指标值 |
| threshold_value | Data | 否 | 28 | 阈值 |
| verdict | Select | 是 | PASS | PASS / WARN / BLOCK |
| summary | Small Text | 是 | 调整后库存覆盖仍高于目标 | 证据摘要 |

### 3.5 Constraint Check Result

| 字段 | 类型 | 必填 | 示例 | 说明 |
| --- | --- | --- | --- | --- |
| check_id | Data | 是 | CHK-001 | 校验编号 |
| recommendation_id | Link | 是 | REC-202605-000123 | 关联动作 |
| rule_code | Data | 是 | SAFETY_STOCK | 规则 |
| verdict | Select | 是 | PASS | PASS / PASS_WITH_APPROVAL / BLOCKED |
| message | Small Text | 是 | 调整后不低于安全库存 | 业务说明 |
| evidence_id | Link | 否 | EVD-001 | 关联证据 |

## 4. SAP 只读接口准备清单

### 4.1 P0 接口

| SAP 对象 | 目标 DocType | 最小用途 | 必需字段 |
| --- | --- | --- | --- |
| 物料主数据 | SAP Material Snapshot | 物料、品类、采购组、MRP 参数 | Material、MaterialName、Plant、MRPType、PurchasingGroup、ProductLine |
| 库存 | SAP Inventory Snapshot | 库存覆盖和可用库存 | Material、Plant、StorageLocation、AvailableStock、QualityStock、BlockedStock、Unit |
| 采购申请 PR | SAP PR Line | PR 数量下调和提前采购 | PurchaseRequisition、PurchaseRequisitionItem、Material、Plant、RequestedQuantity、DeliveryDate |
| 采购订单 PO | SAP PO Line | PO 改期和供应商确认 | PurchaseOrder、PurchaseOrderItem、Material、Plant、Supplier、OrderQuantity、DeliveryDate、ConfirmationStatus |

### 4.2 P1 接口

| SAP 对象 | 目标 DocType | 用途 |
| --- | --- | --- |
| 历史消耗 | SAP Consumption History | 预测偏差、需求波动、季节性 |
| 供应商绩效 | SAP Supplier Performance | OTIF、实际交期、延期接受率 |
| BOM/计划订单 | SAP BOM Component / Planned Order | 齐套风险和生产影响 |

### 4.3 SAP 负责人需提供

| 输入 | 格式 | 截止点 |
| --- | --- | --- |
| Base URL / CPI URL | 文本 | M2 开始前 |
| SAP Client | 文本 | M2 开始前 |
| 认证方式 | Basic / OAuth2 / Certificate | M2 开始前 |
| 只读技术用户 | 账号信息，不进入代码仓库 | M2 开始前 |
| P0 OData Service / EntitySet | 表格 | M2 第 1 周 |
| 字段映射 | 表格 | M2 第 1 周 |
| 示例响应 | JSON 或 CSV 脱敏样例 | M2 第 1 周 |

## 5. 核心 DocType 最小集合

阶段 0 冻结以下 MVP DocType，不在第一版新增无关对象。

| 分组 | DocType | 阶段 |
| --- | --- | --- |
| SAP 连接 | SAP Connection、SAP Endpoint、SAP Field Mapping、SAP Sync Job、SAP API Log | M2 |
| 快照 | SAP Material Snapshot、SAP Inventory Snapshot、SAP PR Line、SAP PO Line | M2 |
| 优化和场景 | Optimization Session、Scenario、Scenario Result | M1/M3 |
| 动作 | Recommendation、Recommendation Evidence、Constraint Check Result | M1/M3 |
| Agent | Agent Run、Agent Tool Log、Data Quality Issue | M3 |
| 审批 | Approval Package、Approval Task | M4 |
| 回写 | SAP Writeback Draft | M4 |
| 执行学习 | Execution Result、Feedback Record、Learning Signal | M4 |

## 6. 第一周执行计划

### Day 1：工程基线

| 任务 | 产出 |
| --- | --- |
| 创建 Frappe App `chainpilot_ai` | App 可安装 |
| 建立模块目录 | 模块结构与设计一致 |
| 建立 README 初稿 | 快速启动和安全边界 |

### Day 2：角色和 Workspace

| 任务 | 产出 |
| --- | --- |
| 创建基础角色 | 7 类角色可分配 |
| 创建 Workspace | Desk 入口可见 |
| 创建 smoke test | 测试框架可运行 |

### Day 3：M1 核心 DocType

| 任务 | 产出 |
| --- | --- |
| 创建 Optimization Session | 可记录基线和来源 |
| 创建 Scenario Result | 可记录方案指标 |
| 创建 Recommendation | 可记录单据行级动作 |

### Day 4：证据和导入

| 任务 | 产出 |
| --- | --- |
| 创建 Recommendation Evidence | 动作可关联证据 |
| 创建 Constraint Check Result | 约束校验可记录 |
| 定义 demo CSV/JSON 模板 | Demo 数据可准备 |

### Day 5：页面骨架和演示脚本

| 任务 | 产出 |
| --- | --- |
| 控制塔骨架 | 可展示 Demo KPI |
| Action Inbox 骨架 | 可展示动作列表 |
| Demo 演示脚本 | 从导入到打开动作详情可跑通 |

## 7. 第一周验收

| 验收项 | 标准 |
| --- | --- |
| 工程 | App 可安装、迁移、启动 |
| 导航 | Workspace 可进入 |
| 权限 | 角色存在，DocType 基础权限存在 |
| 数据 | Demo 模板可导入至少 1 个会话、3 个方案、10 条动作、10 条证据 |
| 页面 | 控制塔和 Action Inbox 能展示 Demo 数据 |
| 质量 | smoke test 通过 |

## 8. 完成情况检查与验证

阶段 0 执行时必须同步记录检查结果。只要 P0 检查项没有通过，就不能进入 M1 正式开发；可以继续并行准备资料，但不能把范围视为已冻结。

### 8.1 检查状态定义

| 状态 | 含义 | 处理方式 |
| --- | --- | --- |
| Pass | 已完成并通过验证 | 记录证据路径或命令输出摘要 |
| Partial | 已完成部分内容，但仍有缺口 | 写清缺口、负责人和预计完成日期 |
| Fail | 已执行但验证失败 | 记录失败原因和修复动作 |
| Blocked | 依赖外部输入，当前无法验证 | 记录阻塞方、所需输入和截止时间 |
| Not Started | 尚未开始 | 不计入完成 |

### 8.2 阶段 0 总体验证表

| 编号 | 检查项 | 验证方式 | 通过标准 | 证据 |
| --- | --- | --- | --- | --- |
| V-001 | MVP 范围冻结 | 人工检查 `docs/PRODUCT_DESIGN.md`、`docs/MVP_IMPLEMENTATION_BACKLOG.md`、本文件 | 三份文档范围一致，HTML 明确为现状参考，不是需求来源 | 文档链接和评审记录 |
| V-002 | 工程基线 | 运行安装、迁移、启动检查 | `chainpilot_ai` 可安装，迁移无错误 | 命令输出摘要 |
| V-003 | 模块结构 | 检查 App 目录 | 设计中列出的核心模块目录存在 | 目录清单 |
| V-004 | 角色 | 在 Frappe 后台或 fixture 中检查角色 | 7 类基础角色存在 | 截图或 fixture |
| V-005 | Workspace | 在 Desk 中检查入口 | ChainPilot AI Workspace 可访问 | 截图 |
| V-006 | 核心 DocType | 检查 M1 最小 DocType | Optimization Session、Scenario Result、Recommendation、Recommendation Evidence、Constraint Check Result 存在 | DocType 清单 |
| V-007 | Demo 数据契约 | 校验 demo CSV/JSON 模板 | 字段覆盖本文件第 3 节，必填字段无缺失 | 模板路径和校验输出 |
| V-008 | Demo 导入 | 运行 demo 导入脚本 | 至少导入 1 个会话、3 个方案、10 条动作、10 条证据 | 导入日志 |
| V-009 | 页面骨架 | 打开控制塔和 Action Inbox | 能显示 Demo KPI 和动作列表 | 截图 |
| V-010 | 证据约束 | 检查 Recommendation 与 Evidence 关系 | 正式动作至少绑定 1 条 Evidence；无 Evidence 动作为 `NEED_EVIDENCE` | 查询结果 |
| V-011 | 安全边界 | 人工检查代码和文档 | 不存在生产 SAP 自动写入逻辑，不提交密码或 API Key | 检查记录 |
| V-012 | 测试 | 运行 smoke test | smoke test 通过 | 测试输出 |

### 8.3 建议验证命令

以下命令在 Frappe bench 环境内执行，`<site>` 替换为实际站点名。若阶段 0 尚未创建 App，则先记录为 `Not Started`，不要伪造通过结果。

```bash
bench --site <site> list-apps
bench --site <site> migrate
bench --site <site> run-tests --app chainpilot_ai
```

Demo 导入脚本实现后，补充执行：

```bash
bench --site <site> execute chainpilot_ai.scripts.import_demo_data.run
bench --site <site> execute chainpilot_ai.scripts.verify_phase_0.run
```

如果尚未实现 `verify_phase_0`，阶段 0 至少要用手工检查完成 V-001 到 V-012，并把证据写入完成报告。

### 8.4 完成报告模板

每次按 goal 模式执行阶段 0 时，在最终报告中使用以下结构：

```text
阶段 0 完成报告

执行日期：
执行人：
目标：

完成摘要：
- 已完成：
- 未完成：
- 阻塞项：

验证结果：
| 编号 | 状态 | 证据 | 备注 |
| --- | --- | --- | --- |
| V-001 | Pass / Partial / Fail / Blocked / Not Started |  |  |

关键命令输出摘要：
- bench --site <site> migrate:
- bench --site <site> run-tests --app chainpilot_ai:
- demo import:

Go / No-Go 结论：
- 结论：
- 进入下一阶段的条件：
```

### 8.5 Go / No-Go 标准

可以进入 M1 正式开发的条件：

1. V-001、V-002、V-003、V-006、V-007、V-010、V-011、V-012 必须为 Pass。
2. V-008 和 V-009 至少为 Partial，并且缺口明确到负责人和日期。
3. 所有 Blocked 项必须有外部输入负责人和截止时间。
4. 不得存在任何生产 SAP 自动写入能力。
5. 不得存在无 Evidence 的正式可审批 Recommendation。

不能进入 M1 的情况：

1. App 无法安装或迁移失败。
2. Demo 数据契约未冻结。
3. Recommendation 无法精确到 SAP 单据行或主数据对象。
4. Evidence 关系无法建立。
5. SAP 密码、LLM Key 或 API Key 出现在代码、日志、Demo 数据或文档中。

## 9. 业务确认清单

| 问题 | 决策项 | 默认建议 |
| --- | --- | --- |
| 第一版组织范围 | 单公司/单工厂还是多组织 | 先单公司/单工厂，字段预留公司和工厂 |
| 财务口径 | cash_release、book_saving、purchase_deferral 定义 | 财务 BP 先确认三类口径 |
| 审批阈值 | 金额和风险对应审批人 | 先按金额三档和风险两档 |
| 供应商确认 | 哪些 PO 改期需要供应商确认 | 已确认 PO 默认需要确认 |
| 冻结期规则 | PR/PO 在冻结期内是否允许建议 | 默认 BLOCKED |
| AI 部署 | 使用云模型、私有模型还是企业网关 | MVP 先抽象 provider，不绑定实现 |

## 10. 输出文件建议

阶段 0 完成后，仓库应至少包含：

| 文件 | 用途 |
| --- | --- |
| `README.md` | 项目定位、启动、安全边界 |
| `docs/PRODUCT_DESIGN.md` | 产品设计 |
| `docs/MVP_IMPLEMENTATION_BACKLOG.md` | 实施 backlog |
| `docs/PHASE_0_STARTER_PACK.md` | 阶段 0 启动包 |
| `demo_data/README.md` | Demo 数据格式 |
| `demo_data/*.csv` 或 `demo_data/*.json` | 可导入样例数据 |

## 11. 开工口径

阶段 0 开工时按以下口径执行：

1. 先用 Demo 数据打通主流程。
2. SAP 只读接入独立推进，不阻塞 M1 演示。
3. AI 能力先以规则和模板替代真实 LLM 调用，接口预留 provider。
4. 每个 public service 函数都要有测试。
5. 不引入生产 SAP 写操作。
