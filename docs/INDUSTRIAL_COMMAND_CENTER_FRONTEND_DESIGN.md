# ChainPilot AI Industrial Command Center 前端设计

## 1. 产品定位

ChainPilot AI 前端定位为企业级供应链 Planner Workspace，而不是报告页、普通 Dashboard 或 AI 聊天页。页面主目标是让计划员、采购经理和供应链负责人在同一个工作台内完成：

- 识别今天的缺料风险。
- 找到可调整的 SAP 采购申请和采购订单。
- 复核影响算法判断的 SAP 主数据异常。
- 追溯每条建议的算法运行、证据链、约束校验和审批动作。

## 2. 风格基准

风格名：Anaplan-like Planning Model Canvas

参考方向：

- Anaplan UX：Board / Worksheet / Context Selector / Insights Panel。
- Anaplan Supply Planning：场景计划、物料约束、库存与产能、采购/生产订单建议。
- SAP IBP：供应链计划、供需平衡、物料和地点维度。
- SAP Fiori：企业软件密度、工作清单、对象页、审计信息下沉。
- Blue Yonder Supply Chain Planning：异常队列、计划动作包、可执行工作台。

视觉原则：

- 克制、高密度、可信、可执行。
- 不使用 emoji 作为业务图标。
- 不使用大面积渐变、玻璃拟态或营销式 Hero。
- AI 只作为证据解释抽屉，不占据主视觉。
- KPI 不超过 6 个，且必须连接具体物料、SAP 单据或动作。

## 2.0 Anaplan 参考规则

本轮界面验收不再只参考单张截图，而是按 Anaplan 公开产品和 Anapedia 文档抽象成可实现规则：

- 主页面必须像 Planning Model Canvas：顶部是计划上下文选择器，主体是表格、图表、KPI 和动作卡组成的模型画布。
- Worksheet 规则：中心必须有 primary grid，用于计划员分析、编辑或触发动作；右侧 Insights panel 只放相关洞察、快捷入口和补充卡片。
- Board 规则：卡片用于比较分析，允许 KPI、chart、grid、action、field 等卡片，但不能堆成普通 KPI 大屏。
- Context Selector 规则：计划周期、工厂、产品线、场景、版本放在顶部，切换后应影响全页数据语义。
- Supply Planning 规则：页面必须展示 BOM/物料、库存、需求、供应、约束、场景、订单建议，不只展示总数。
- AI 规则：AI 体现为预测、优化、解释、协同洞察，嵌入计划模型，不以聊天框或“AI 建议如下”作为主视觉。

参考来源：

- Anaplan Worksheet pages: https://help.anaplan.com/worksheet-pages-1cc11f1c-1447-4510-833d-cc393e8d9846
- Anaplan Board pages: https://help.anaplan.com/board-pages-1294b62a-4655-4bcd-a0c5-e9ebb53e4501
- Anaplan Worksheet or board: https://help.anaplan.com/worksheet-or-board-e080869d-92fe-4142-8755-e8deb2196819
- Anaplan Primary grids: https://help.anaplan.com/work-with-primary-grids-3485da86-6267-47d6-a2fa-48d8dffca974
- Anaplan Supply Planning application: https://www.anaplan.com/applications/supply-planning-app/
- Anaplan Intelligence: https://www.anaplan.com/platform/intelligence/
- Anaplan PlanIQ: https://www.anaplan.com/platform/anaplan-planiq/

## 2.1 AI 能力边界

ChainPilot 对标 Anaplan Intelligence 的方式不是把 LLM 聊天框放到主页面，而是把智能能力嵌入供应计划流程。实现上分四类：

| 能力 | 产品表达 | 当前实现 | 后续生产化 |
| --- | --- | --- | --- |
| 预测模型 | 缺料概率、P90 缺口、供应延迟、需求波动 | 概率仿真 + 统计特征 | 接入两年 SAP 历史后训练需求、交期和延迟预测模型 |
| 优化器 | 采购动作包、减少资金占用、服务水平约束 | HiGHS MILP 整数规划 / 精确枚举兜底 | 增加多场景、多目标和产能约束 |
| 驱动因素 | 库存、安全库存、需求、供应商延迟、约束状态 | 算法证据字段 + 约束校验 | 增加预测特征贡献和回测稳定性 |
| 协同助手 | 当前行问答、审批摘要、供应商沟通草稿 | 可配置 LLM，受证据边界约束 | 连接企业助手入口，支持场景级问答 |

界面原则：

- 不显示“AI 建议如下”。
- 不让聊天框占据主视觉。
- 所有智能结果必须绑定物料、工厂、供应商或 SAP 单据。
- LLM 只能解释证据、生成摘要和草稿，不能替代优化器做生产决策。
- 预测和优化结果必须显示驱动因素、证据、约束和运行记录。

## 3. 全局布局

统一布局由 `window.chainpilot.workspace` 提供：

- 左侧固定导航：240px。
- 顶部 Header：56px。
- 主内容区：12 列栅格语义，实际实现为高密度 CSS Grid。
- 右侧 Evidence Drawer：360px，可折叠。
- 页面不限制报告宽度，适配 1440px 和 1920px 企业桌面屏。

Header 必须展示：

- 工厂范围。
- 计划周期。
- Snapshot 时间。
- Algorithm Run 状态。
- 数据源。

## 4. 页面结构

### 4.1 Supply Planning Model

回答三个问题：

- 今天有哪些风险？
- 哪些 SAP 单据能改？
- 哪些主数据错了？

首屏包含：

- 计划版本、场景、工厂和周期。
- 供应计划模型工作表。
- 缺料例外。
- 采购动作。
- 主数据输入。
- 预测、优化、驱动因素和协同助手的能力状态。

### 4.2 Shortage Exception Worksheet

布局：

- 左侧风险物料列表。
- 中间库存投影。
- 右侧 Evidence Drawer。

库存投影包含：

- 当前库存。
- 预计到货。
- 需求。
- 安全库存线。
- P90 缺口。

每条风险显示：

- 物料。
- 工厂。
- 预计缺料日。
- 缺口数量。
- 缺料概率。
- 影响工单。
- 建议动作。

### 4.3 Procurement Action Worksheet

顶部约束：

- 资金占用降低目标。
- 服务水平。
- 保护品类。
- 禁止动作。

动作包分组：

- 低风险可审批。
- 需供应商确认。
- 被阻断。

表格字段：

- SAP 对象。
- 物料。
- 原值。
- 建议值。
- 资金占用影响。
- 风险变化。
- 约束状态。

### 4.4 Master Data Health

展示主数据健康分，并按四类异常组织：

- 计划交货期。
- 安全库存。
- MOQ/MPQ。
- 供应商参数。

每条异常显示：

- 当前 SAP 值。
- 建议值。
- 样本数。
- P80/P95。
- 置信度。
- 影响金额。

### 4.5 Action Queue

按待办类型展示：

- 待审批动作。
- 缺料风险处理。
- 主数据复核。

### 4.6 Recommendation Detail

必须包含：

- Action Header。
- Before / After。
- Algorithm Trace。
- Evidence & Constraint。
- Approval / Writeback / Execution Timeline。
- 右侧 Evidence Drawer。

### 4.7 Algorithm Run Detail

展示：

- 算法运行列表。
- 运行状态。
- Snapshot。
- 结果数。
- 耗时。
- Summary 证据。

## 5. 复用组件

当前实现的组件：

- `CPMetricCard`
- `CPActionCard`
- `CPSeverityBadge`
- `CPSapObjectTag`
- `CPAlgorithmTrace`
- `CPEvidenceList`
- `CPConstraintChecklist`
- `CPBeforeAfter`
- `CPExecutionTimeline`
- `CPAiDrawer`

所有组件均使用 `cp-*` CSS 命名空间，避免和 Frappe 默认样式、旧页面样式互相污染。

## 6. CSS Token

实现使用以下 token：

```css
--cp-bg: #F5F7FA;
--cp-surface: #FFFFFF;
--cp-surface-subtle: #F9FAFB;
--cp-border: #E4E7EC;
--cp-text: #101828;
--cp-text-muted: #667085;
--cp-primary: #0B5CAB;
--cp-ai: #6D28D9;
--cp-success: #039855;
--cp-warning: #F79009;
--cp-danger: #D92D20;
--cp-info: #1570EF;
```

## 7. 验收点

- 页面不是 HTML 报告，而是可执行 Planner Workspace。
- 首屏展示具体物料、SAP 单据和动作，不只展示总数。
- 每条动作可以打开 Evidence Drawer。
- Evidence Drawer 串联 SAP 对象、算法运行、证据和约束。
- Recommendation Detail 包含 Algorithm Trace 和 Evidence。
- Command Center KPI 不超过 6 个。
- 无 emoji、无大面积渐变、无 AI 聊天框主视觉。
