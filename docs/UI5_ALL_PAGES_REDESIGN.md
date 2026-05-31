# ChainPilot AI UI5/Fiori 全页面改造说明

日期：2026-05-31

## 参考原则

参考 UI5 Web Components / OpenUI5 的企业应用结构，而不是只复制视觉皮肤：

- ShellBar / SideNavigation：所有自定义页面进入统一应用外壳和左侧导航。
- Dynamic Page：顶部固定标题、业务上下文、全局动作。
- Message Strip：只读 SAP 快照、模拟账套、人工审批等关键状态用条幅提示。
- Filter Bar：页面筛选区保持紧凑、可扫描。
- Object Status：状态、风险、约束、审批等级统一为状态标签。
- Analytical Table / List Report：业务对象表格优先，避免 KPI 大屏。
- Object Page：推荐详情、证据、约束、算法追踪和执行时间线按对象页组织。

参考来源：

- https://github.com/UI5/webcomponents
- https://ui5.github.io/webcomponents/components/fiori/ShellBar/
- https://ui5.github.io/webcomponents/components/fiori/SideNavigation/
- https://ui5.github.io/webcomponents/components/fiori/DynamicPage/

## 覆盖页面

本轮不只改首页，所有 ChainPilot 自定义页面统一进入 Fiori shell：

- 计划员处理工作台：`/app/chainpilot-ai-command-center`
- 缺料例外表：`/app/shortage-risk-war-room`
- 采购动作表：`/app/cash-release-action-package`
- 主数据输入：`/app/master-data-health`
- 模拟数据中心：`/app/mock-data-center`
- SAP 接入配置：`/app/sap-integration-console`
- 策略优化训练：`/app/strategy-optimization-center`
- 方案测算：`/app/scenario-studio`
- 动作队列：`/app/action-inbox`
- 执行监控：`/app/execution-monitor`
- 学习中心：`/app/learning-center`
- 智能协同：`/app/ai-copilot`
- 对象详情：`/app/recommendation-detail`
- 优化运行：`/app/algorithm-run-detail`

## 实现方式

- `chainpilot_ai/public/js/chainpilot_ai.js`
  - 扩展左侧导航到所有自定义页面。
  - 新增 `workspace.mountLegacyShell`，把旧独立页面装入同一套 Fiori 外壳。
  - 保留原业务接口和按钮动作，不改变 SAP、LLM、算法、回测、审批的服务调用。

- `chainpilot_ai/public/css/chainpilot_ai.css`
  - 对旧 `.chainpilot-*` 页面元素增加 UI5/Fiori bridge 样式。
  - 将旧 hero 改为 Dynamic Page/Object Header 风格。
  - 将旧按钮、状态、表单、卡片、表格、Tab、列表统一为 UI5-like 密度和状态表达。
  - 所有页面取消报告宽度限制，适配 1440px/1920px 企业桌面。

- 独立页面入口：
  - `ai_copilot.js`
  - `execution_monitor.js`
  - `learning_center.js`
  - `mock_data_center.js`
  - `sap_integration_console.js`
  - `scenario_studio.js`
  - `strategy_optimization_center.js`

## 验收口径

- 每个页面都有统一左侧导航和顶部工作区标题。
- 旧的营销式大 hero 被替换成 Fiori Dynamic Page 标题区。
- 页面主要内容保留业务对象、表格、状态、证据、动作按钮。
- AI 助手不作为主视觉，只作为业务目标和协同入口。
- 不引入大面积渐变、玻璃拟态、emoji 图标或纯 KPI 大屏。

## 截图验收

已在 1440px 宽度下逐页截图，文件位于：

- `docs/ui_screenshots/ui5_all_pages_command.png`
- `docs/ui_screenshots/ui5_all_pages_shortage.png`
- `docs/ui_screenshots/ui5_all_pages_cash.png`
- `docs/ui_screenshots/ui5_all_pages_master.png`
- `docs/ui_screenshots/ui5_all_pages_mock.png`
- `docs/ui_screenshots/ui5_all_pages_sap.png`
- `docs/ui_screenshots/ui5_all_pages_strategy.png`
- `docs/ui_screenshots/ui5_all_pages_scenario.png`
- `docs/ui_screenshots/ui5_all_pages_inbox.png`
- `docs/ui_screenshots/ui5_all_pages_execution.png`
- `docs/ui_screenshots/ui5_all_pages_learning.png`
- `docs/ui_screenshots/ui5_all_pages_assistant.png`
- `docs/ui_screenshots/ui5_all_pages_recommendation.png`
- `docs/ui_screenshots/ui5_all_pages_algorithm.png`
