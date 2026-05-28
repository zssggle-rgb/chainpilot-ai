# M5 进度报告

日期：2026-05-28

## 本次完成

- 新增 Learning Metric Snapshot，用于固化采纳率、供应商接受率、兑现率、缺料事件数和主要拒绝原因。
- 新增 Shortage Event，用于记录缺料事件、物料、工厂、严重级别、损失估计和根因。
- 新增 Rule Weight Adjustment，用于把 Learning Signal 转成待业务复核的调权草稿。
- 扩展 `learning.service`：可计算学习指标、生成调权草稿、seed mock 学习数据并输出 Learning Center dashboard。
- 新增 Learning Center 页面，展示 KPI、学习洞察、指标快照、规则调权队列、拒绝原因、供应商反馈、兑现结果、缺料事件和 Learning Signal。
- Workspace、Command Center、Action Inbox、Execution Monitor、AI Copilot 均增加 Learning Center 入口。
- 新增 `chainpilot_ai.scripts.verify_m5`，覆盖 M5 DocType、指标计算、调权草稿、页面入口和 mock seed。

## 运行态入口

- Learning Center：`http://chainpilot.localhost:8000/app/learning-center`
- 浏览器验收截图：`/Users/sjs/chainpilot-ai/tmp/m5-learning-center.png`

## 当前边界

- 当前学习数据来自 M4 mock 审批、供应商沟通和执行结果，不接真实 SAP 生产回写。
- Rule Weight Adjustment 只生成 Draft，不自动影响推荐排序。
- Shortage Event 当前由 mock seed 生成，真实接入后应由 SAP 缺料、生产延期或人工复盘事件写入。
- 供应商接受率当前根据 Supplier Feedback 计算，真实接入后可替换为邮件、SRM 或 SAP 确认状态。

## 验证命令

```bash
python3 -m chainpilot_ai.scripts.run_smoke_tests
python3 -m chainpilot_ai.scripts.verify_m5
bench --site chainpilot.localhost migrate
bench --site chainpilot.localhost execute chainpilot_ai.learning.service.seed_learning_mock_data
bench --site chainpilot.localhost execute chainpilot_ai.scripts.verify_m5.run
bench --site chainpilot.localhost run-tests --app chainpilot_ai
bench build --app chainpilot_ai
```

本轮实际验收结果：本地 smoke、M5 verify、`bench migrate`、M5 bench verify、Frappe app tests、`bench build` 均通过；Learning Center 当前页浏览器 console 无 warning/error。

## 下一步

MVP 主闭环已经覆盖到学习层。下一步建议做横向加固：权限矩阵、错误处理标准、GitHub CI、Demo 一键演示脚本，以及真实 SAP OData 字段映射接入准备。
