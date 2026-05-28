# ChainPilot AI MVP 实施 Backlog

版本：v0.1  
日期：2026-05-28  
依据：`docs/PRODUCT_DESIGN.md`  

## 1. MVP 目标

MVP 只验证一条主闭环：

> 真实 SAP 分析结果 -> 可浏览的优化场景 -> 单据行级 Recommendation -> 证据解释 -> 审批包 -> SAP 回写草稿 -> 执行反馈。

第一版不直接写 SAP 生产环境，不重写完整优化算法，不把 HTML 报告复刻成静态页面。HTML 报告只作为真实现状参考和 Demo 数据来源。

## 2. 交付节奏

| 阶段 | 周期 | 目标 | 退出标准 |
| --- | --- | --- | --- |
| M0 | 1 周 | 建立 Frappe App 骨架和交付基线 | App 可安装，核心模块目录、角色、Workspace、测试框架存在 |
| M1 | 2 周 | 把真实 SAP 分析结果产品化为场景和动作 | Demo 数据可导入，控制塔和动作详情可演示 |
| M2 | 3-5 周 | 建立 SAP OData 只读同步基础 | PR、PO、库存、物料任一 Endpoint 可配置同步并写日志 |
| M3 | 3-4 周 | Agent 生成场景、动作、证据解释 | 用户目标可生成 Scenario、Recommendation 和 Explanation |
| M4 | 4-6 周 | 审批、供应商沟通和回写草稿闭环 | Approved Recommendation 可生成 Writeback Draft 和 Execution Result |

## 3. 工作项约定

优先级说明：

| 优先级 | 含义 |
| --- | --- |
| P0 | MVP 闭环必需，缺失则无法演示主流程 |
| P1 | 增强业务可信度，MVP 可部分简化 |
| P2 | 后续迭代项，MVP 只预留结构 |

状态说明：

| 状态 | 含义 |
| --- | --- |
| Ready | 可直接开发 |
| Needs Input | 需要业务或 SAP 信息确认 |
| Blocked | 没有外部输入无法推进 |

## 4. M0 项目初始化

目标：建立可运行、可迁移、可测试的 Frappe App 基座。

| ID | 优先级 | 工作项 | 交付物 | 验收标准 | 状态 |
| --- | --- | --- | --- | --- | --- |
| M0-01 | P0 | 创建 `chainpilot_ai` Frappe App | App 目录、`hooks.py`、`modules.txt`、`patches.txt` | `bench install-app chainpilot_ai` 和 `bench migrate` 可通过 | Ready |
| M0-02 | P0 | 建立模块目录 | `sap_connector`、`snapshots`、`scenario`、`optimization`、`agent`、`recommendation`、`approval`、`writeback`、`monitoring`、`learning` | 每个模块有初始化文件和最小 service/test 文件 | Ready |
| M0-03 | P0 | 定义基础角色 | ChainPilot Admin、Supply Chain Director、Planning Manager、Procurement Manager、Planner、Buyer、Finance BP | 角色可在 Frappe 中分配 | Ready |
| M0-04 | P0 | 创建 Workspace | ChainPilot AI Workspace | Desk 中可进入 ChainPilot AI 工作区 | Ready |
| M0-05 | P0 | 建立测试基线 | `tests/`、基础 fixtures、测试运行命令 | 至少 1 个 smoke test 通过 | Ready |
| M0-06 | P1 | 编写 README 快速启动 | README、环境变量说明、安全声明 | 新开发者可按文档启动本地站点 | Ready |
| M0-07 | P1 | 建立开发数据目录 | `demo_data/`、导入说明 | Demo 数据路径和格式明确 | Ready |

### M0 验收清单

| 验收项 | 通过标准 |
| --- | --- |
| 安装 | App 可安装，迁移无错误 |
| 导航 | Desk 中可见 ChainPilot AI Workspace |
| 权限 | 基础角色存在 |
| 测试 | smoke test 可运行 |
| 文档 | README 包含启动、安全边界和模块说明 |

## 5. M1 报告产品化

目标：把真实 SAP 分析结果转为系统对象，而不是静态报告页面。

| ID | 优先级 | 工作项 | 交付物 | 验收标准 | 状态 |
| --- | --- | --- | --- | --- | --- |
| M1-01 | P0 | 定义 Optimization Session DocType | DocType、字段、权限、列表视图 | 可记录基线金额、物料数、采样次数、最优解数、来源 | Ready |
| M1-02 | P0 | 定义 Scenario DocType | DocType、constraint JSON 字段、状态字段 | 可创建“释放 8000 万现金”场景 | Ready |
| M1-03 | P0 | 定义 Scenario Result DocType | DocType、方案指标字段 | 可记录保守、推荐、激进方案的金额、风险、动作数 | Ready |
| M1-04 | P0 | 定义 Recommendation DocType | DocType、字段、权限、列表视图 | 可精确到 SAP 对象类型、单据号、行号、物料、工厂、供应商 | Ready |
| M1-05 | P0 | 定义 Recommendation Evidence DocType | DocType、来源类型、source_id、摘要、证据值 | Recommendation 可关联多条 Evidence | Ready |
| M1-06 | P0 | 编写 Demo 导入脚本 | `scripts/import_demo_report.py` 或 Frappe command | 可导入 Optimization Session、Scenario Result、Recommendation、Evidence 样例 | Needs Input |
| M1-07 | P0 | 控制塔首页 MVP | Desk Page 或 Dashboard | 显示基线、机会金额、推荐方案、待审批动作、风险提示 | Ready |
| M1-08 | P0 | Action Inbox MVP | List View、筛选器、状态标签 | 可按金额、风险、审批状态、供应商确认筛选 Recommendation | Ready |
| M1-09 | P0 | Recommendation Detail MVP | Form View、证据区、约束区、解释区 | 打开动作可看到 SAP 单据行、原值、建议值、金额、风险、证据 | Ready |
| M1-10 | P1 | Scenario Studio 方案对比 | 三方案对比表、推荐理由 | 可展示保守、推荐、激进方案对比 | Ready |
| M1-11 | P1 | Demo 数据校验 | 导入前字段校验和错误报告 | 缺少单据号、行号、证据时给出错误 | Needs Input |

### M1 数据输入要求

| 数据 | 最小字段 |
| --- | --- |
| Optimization Session | session_id、baseline_amount、material_count、sample_count、best_solution_count、source_report |
| Scenario Result | scenario_id、strategy_name、purchase_amount、cash_release、risk_level、recommendation_count |
| Recommendation | action_type、sap_object_type、sap_doc_no、sap_item_no、material_code、plant、supplier、before_qty、after_qty、cash_release |
| Evidence | evidence_id、recommendation_id、source_type、source_id、metric_name、metric_value、summary |

### M1 验收清单

| 验收项 | 通过标准 |
| --- | --- |
| Demo 导入 | 一条优化会话、至少三种方案、至少十条动作和证据可导入 |
| 控制塔 | 可从控制塔进入方案和动作 |
| 动作详情 | 每条正式动作至少有一条 Evidence |
| 边界 | HTML 报告未被当作产品页面硬编码 |

## 6. M2 SAP 只读接入

目标：建立可配置、可审计、可失败重试的 SAP OData 只读同步。

| ID | 优先级 | 工作项 | 交付物 | 验收标准 | 状态 |
| --- | --- | --- | --- | --- | --- |
| M2-01 | P0 | SAP Connection DocType | Single DocType、密码字段、测试连接按钮 | 可配置 Base URL、Client、认证方式、超时、SSL 校验 | Ready |
| M2-02 | P0 | SAP Endpoint DocType | Service、EntitySet、目标 DocType、字段、过滤器、分页 | 可配置 PR Endpoint 样例 | Ready |
| M2-03 | P0 | SAP Field Mapping DocType | Child Table、源字段、目标字段、转换函数 | Endpoint 可配置字段映射 | Ready |
| M2-04 | P0 | SAP Sync Job DocType | 同步状态、条数、错误、增量标记 | 每次同步都有任务记录 | Ready |
| M2-05 | P0 | SAP API Log DocType | 请求摘要、响应摘要、状态码、耗时、错误 | 测试连接和同步失败均写日志 | Ready |
| M2-06 | P0 | pyodata 客户端封装 | `sap_connector/service.py` | `test_connection`、`get_entity_set`、`sync_endpoint` 有受控输入输出 | Ready |
| M2-07 | P0 | Snapshot DocType - Material | SAP Material Snapshot | 可 upsert 物料主数据 | Ready |
| M2-08 | P0 | Snapshot DocType - Inventory | SAP Inventory Snapshot | 可 upsert 库存快照 | Ready |
| M2-09 | P0 | Snapshot DocType - PR Line | SAP PR Line | 可 upsert PR 行 | Ready |
| M2-10 | P0 | Snapshot DocType - PO Line | SAP PO Line | 可 upsert PO 行 | Ready |
| M2-11 | P1 | 增量同步预留 | last_change_token、filter builder | 支持后续按变更时间增量 | Needs Input |
| M2-12 | P1 | 同步失败重试 | enqueue job、retry count、错误摘要 | SAP 连接失败不影响主应用 | Ready |

### M2 外部输入

| 输入 | 用途 | 负责人 |
| --- | --- | --- |
| SAP Gateway 或 CPI Base URL | 连接配置 | SAP 集成负责人 |
| SAP Client | OData 请求参数 | SAP 集成负责人 |
| 只读技术用户 | Basic/OAuth2/证书认证 | SAP 安全负责人 |
| PR/PO/库存/物料 OData Service 和 EntitySet | Endpoint 配置 | SAP 集成负责人 |
| 字段映射表 | Snapshot upsert | 供应链业务和 SAP 顾问 |

### M2 验收清单

| 验收项 | 通过标准 |
| --- | --- |
| 测试连接 | 成功和失败都可见，并写 SAP API Log |
| Endpoint 同步 | 至少一个 Endpoint 可同步到 Snapshot |
| 安全 | 密码不明文入库，不写日志 |
| 稳定性 | SAP 失败不阻塞 Frappe 主应用 |

## 7. M3 AI 场景与动作生成

目标：从自然语言业务目标生成结构化场景、候选动作、约束校验和证据解释。

| ID | 优先级 | 工作项 | 交付物 | 验收标准 | 状态 |
| --- | --- | --- | --- | --- | --- |
| M3-01 | P0 | Agent Run DocType | 状态、输入、输出、错误、关联场景 | Agent Run 可记录完整状态流转 | Ready |
| M3-02 | P0 | 意图解析工具 | `parse_user_goal` | 输入“释放 8000 万，不影响空调，优先改 PR”输出严格 JSON | Ready |
| M3-03 | P0 | Scenario Constraint Schema | JSON Schema、默认值、校验器 | 缺失字段可用默认策略补齐，非法字段被拒绝 | Ready |
| M3-04 | P0 | 优化工具封装 | `optimization/service.py` | 可从 Scenario 生成 Scenario Result 和候选动作 | Ready |
| M3-05 | P0 | 约束校验服务 | 冻结期、MOQ/MPQ、安全库存、供应商确认 | Candidate Action 可得到 PASS、PASS_WITH_APPROVAL、BLOCKED | Ready |
| M3-06 | P0 | 动作生成服务 | `generate_action_cards` | 通过校验的候选动作生成 Recommendation | Ready |
| M3-07 | P0 | 证据收集服务 | `collect_evidence` | Recommendation 至少绑定库存、预测或约束证据 | Ready |
| M3-08 | P0 | AI Explanation 服务 | `explain_recommendation` | 无 Evidence 时状态为 NEED_EVIDENCE，有证据时生成解释 | Ready |
| M3-09 | P0 | Agent Tool Log | 工具名、输入摘要、输出摘要、耗时、错误 | 每次工具调用可审计 | Ready |
| M3-10 | P1 | AI Copilot 页面 | 输入框、上下文、运行状态、结果链接 | 用户可发起 Agent Run 并进入结果 | Ready |
| M3-11 | P1 | Data Quality Issue | DocType、问题类型、严重级别、建议处理 | 优化前可提示数据异常 | Ready |

### M3 验收清单

| 验收项 | 通过标准 |
| --- | --- |
| 场景解析 | 自然语言目标转为 Scenario Constraint JSON |
| 动作生成 | 场景可生成至少 10 条 Recommendation |
| 约束 | BLOCKED 动作不能进入批量审批 |
| 解释 | 正式解释必须包含 evidence_id |
| 审计 | Agent Run 和 Tool Log 可追溯 |

## 8. M4 审批、沟通与回写草稿

目标：把 Recommendation 推进到可审批、可沟通、可回写草稿化和可复盘。

| ID | 优先级 | 工作项 | 交付物 | 验收标准 | 状态 |
| --- | --- | --- | --- | --- | --- |
| M4-01 | P0 | Approval Package DocType | 汇总金额、动作数、风险摘要、审批人、状态 | 可从多条 Recommendation 生成审批包 | Ready |
| M4-02 | P0 | Approval Task DocType | 审批角色、审批人、结果、意见 | 计划、采购、财务审批可记录 | Ready |
| M4-03 | P0 | 审批摘要生成 | AI Summary 或模板摘要 | 审批包显示收益、风险、需确认事项 | Ready |
| M4-04 | P0 | SAP Writeback Draft DocType | 目标对象、old_value、new_value、payload、rollback_payload | Approved Recommendation 可生成草稿 | Ready |
| M4-05 | P0 | 二次读取校验 | 当前值读取和冲突检查 | SAP 当前值变化时草稿标记为 CONFLICT | Needs Input |
| M4-06 | P0 | Execution Result DocType | 执行状态、兑现值、未兑现原因 | 回写草稿后的执行结果可追踪 | Ready |
| M4-07 | P0 | Feedback Record DocType | 采纳、拒绝、供应商反馈、原因 | 拒绝建议可选择原因并留痕 | Ready |
| M4-08 | P0 | Learning Signal DocType | 调权对象、原因、建议权重 | 反馈可生成学习信号 | Ready |
| M4-09 | P1 | Supplier Communication Draft | 供应商消息草稿 | PO 改期动作可生成沟通草稿 | Ready |
| M4-10 | P1 | Execution Monitor 页面 | 审批、草稿、执行、兑现、异常 | 可查看闭环状态 | Ready |
| M4-11 | P1 | 审批权限矩阵 | 金额阈值、角色、风险等级 | 高金额或高风险动作要求更高审批 | Needs Input |

### M4 验收清单

| 验收项 | 通过标准 |
| --- | --- |
| 审批包 | 多条 Recommendation 可打包、提交、审批、拒绝 |
| 回写草稿 | 只有 Approved Recommendation 可生成 Writeback Draft |
| 安全 | 草稿不自动写 SAP 生产环境 |
| 反馈 | 拒绝原因和兑现结果可沉淀为 Learning Signal |
| 监控 | 可看到从建议到执行结果的状态链路 |

## 9. 跨阶段技术任务

| ID | 优先级 | 工作项 | 验收标准 |
| --- | --- | --- | --- |
| X-01 | P0 | 统一命名和状态枚举 | DocType、服务函数、测试使用同一套枚举 |
| X-02 | P0 | 权限和组织过滤 | 至少按角色控制读写权限 |
| X-03 | P0 | 错误处理标准 | 用户可见错误清晰，技术错误写日志 |
| X-04 | P0 | Secret 管理 | 密码和 API Key 不出现在代码、日志、Demo 数据 |
| X-05 | P0 | 测试覆盖 | service 层 public function 有单元测试 |
| X-06 | P1 | CI | lint、test、迁移检查可在 GitHub Actions 运行 |
| X-07 | P1 | Demo 脚本 | 一条命令 seed demo data，一条脚本演示主流程 |

## 10. MVP 完成定义

MVP 完成必须同时满足：

1. Frappe App 可安装、迁移、启动。
2. Demo 数据可导入真实 SAP 分析结果的优化会话、方案、动作和证据。
3. 控制塔可进入场景和动作列表。
4. 用户目标可生成 Scenario Constraint。
5. Recommendation 精确到 SAP 单据行或主数据对象。
6. 每条正式解释都绑定 Evidence。
7. 约束校验能阻断不应审批的动作。
8. 多条 Recommendation 可生成 Approval Package。
9. Approved Recommendation 可生成 SAP Writeback Draft。
10. 反馈和执行结果可形成 Learning Signal。

## 11. 推荐执行顺序

1. 先完成 M0-01 到 M0-07，建立工程基线。
2. 并行推进 M1 DocType 和 Demo 数据契约。
3. M1 控制塔与 Action Inbox 先用 Demo 数据打通。
4. M2 SAP 只读接入独立开发，不阻塞 M1 页面。
5. M3 Agent 先使用规则和模板实现，再接真实 LLM。
6. M4 审批和回写草稿在 Recommendation 稳定后接入。

## 12. 当前阻塞项

| 阻塞项 | 影响 | 解除方式 |
| --- | --- | --- |
| 真实优化结果字段结构未确认 | Demo 导入脚本无法最终定稿 | 导出 `trial.cco_session`、`trial.cco_suggestion` 字段样例 |
| SAP OData 对象未确认 | M2 Endpoint 无法连真实系统 | 提供 PR、PO、库存、物料 Service 和 EntitySet |
| 财务节省口径未确认 | cash_release 与 saving_type 口径可能争议 | 财务 BP 确认现金释放、账面节省、延期采购定义 |
| 审批权限矩阵未确认 | M4 审批流只能先做默认规则 | 提供金额阈值、角色、风险等级对应审批人 |
