# ChainPilot AI Fiori Planner Workspace UI 重构说明

日期：2026-05-31

## 1. 参考来源

本轮 UI 重构参考以下公开项目和设计资料：

- UI5 Web Components ShellBar / SideNavigation / DynamicPage，用于确定企业应用壳、侧边导航和动态对象页布局。
  - https://ui5.github.io/webcomponents/components/fiori/ShellBar/
  - https://ui5.github.io/webcomponents/components/fiori/SideNavigation/
  - https://ui5.github.io/webcomponents/components/fiori/DynamicPage/
- SAP Fiori Dynamic Page Layout，用于约束页面结构：顶部对象标题、关键属性、全局动作、主内容区。
  - https://www.sap.com/design-system/fiori-design-web/v1-71/page-types/page-layouts/dynamic-page-layout/usage
- Frappe List View，用于保留 Frappe 原生对象列表、筛选、排序、行级按钮和表单跳转习惯。
  - https://docs.frappe.io/framework/user/en/api/list
- Ant Design Pro 的 Table List / Advanced Form / Workplace，用于参考现代企业后台的信息密度和表格优先工作方式。
  - https://github.com/ant-design/ant-design-pro

## 2. 设计原则

这次重构不再把首页当作 AI Dashboard 或算法报告页，而是改成供应链 Planner Workspace：

- 首页主视觉是 Recommendation 表格，不是 KPI 大卡片。
- 每一行必须回到 SAP 对象、物料、工厂、供应商和动作。
- 筛选栏放在表格上方，支持工厂、SAP 对象、处理状态、风险等级和搜索。
- 右侧是对象页预览，不是 AI 聊天框。
- 算法信息只作为证据链和求解状态出现，不占首页主视觉。
- 页面保留 Frappe Desk 顶部框架，但内容区按 Fiori List Report / Object Page 方式组织。

## 3. 已实现页面结构

文件：

- `chainpilot_ai/public/js/chainpilot_ai.js`
- `chainpilot_ai/public/css/chainpilot_ai.css`
- `chainpilot_ai/hooks.py`
- `chainpilot_ai/chainpilot_ai/page/chainpilot_ai_command_center/chainpilot_ai_command_center.js`
- `chainpilot_ai/chainpilot_ai/page/chainpilot_ai_command_center/chainpilot_ai_command_center.json`

首页结构：

1. Message Strip：说明当前为只读计划工作区，不直接写 SAP。
2. Object Header：展示计划员处理工作台、待处理对象、采购动作、缺料物料、主数据异常和全局动作。
3. Filter Bar：工厂、SAP 对象、处理状态、风险等级、搜索。
4. Recommendation Table：核心区域，列出优先级、SAP 对象、物料/工厂、供应商、推荐动作、当前值、建议值、资金影响、风险/缺口、约束和操作。
5. Object Inspector：右侧对象页预览，点击表格行后显示当前/建议、约束校验、证据链和操作按钮。
6. Object Lists：下方保留缺料风险、采购动作、主数据复核的对象清单入口。

## 4. 验收结果

浏览器验收地址：

```text
http://chainpilot.localhost:8000/app/chainpilot-ai-command-center
```

验收项：

| 项目 | 结果 |
| --- | --- |
| 首页不再显示旧的“供应计划目标设定 / 模型画布” | 通过 |
| 首页出现“计划员处理工作台” | 通过 |
| Recommendation 表格为主视觉 | 通过 |
| 表格展示 SAP 对象、物料、工厂、供应商、动作 | 通过 |
| 右侧对象页预览显示当前/建议、约束、证据链 | 通过 |
| 点击表格行后对象页预览更新 | 通过 |
| 首页没有 AI 聊天框 | 通过 |
| 首页没有 Algorithm Run 详情主视觉 | 通过 |

截图：

```text
docs/ui_screenshots/fiori_planner_workspace_1440.png
```

## 5. 缓存处理

为避免 Frappe Desk 继续加载旧前端资源，`hooks.py` 已给前端 CSS/JS 追加版本号：

```python
app_include_css = ["/assets/chainpilot_ai/css/chainpilot_ai.css?v=20260531-fiori-workspace-2"]
app_include_js = ["/assets/chainpilot_ai/js/chainpilot_ai.js?v=20260531-fiori-workspace-2"]
```

修改后已执行：

```bash
bench --site chainpilot.localhost clear-cache
```
