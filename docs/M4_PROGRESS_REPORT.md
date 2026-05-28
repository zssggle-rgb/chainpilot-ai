# M4 进度报告

日期：2026-05-28

## 本次完成

- 新增 Approval Package、Approval Task、SAP Writeback Draft、Supplier Communication Draft。
- 新增 Execution Result、Feedback Record、Learning Signal，支撑执行复盘和学习闭环。
- 扩展 `approval.service`：可从多条 Recommendation 生成审批包、审批任务、批准或拒绝。
- 扩展 `writeback.service`：只有 Approved Recommendation 可生成 DRAFT_ONLY 回写草稿，并包含 payload、rollback payload 和二次读取校验状态。
- 修复 Frappe 日期字段进入 PO 回写草稿时的 JSON 序列化问题，确保日期型 delivery date 可生成 payload 和 rollback payload。
- 扩展 `monitoring.service`：汇总审批包、任务、回写草稿、供应商草稿、执行结果、反馈和学习信号。
- 新增 Execution Monitor 页面，提供生成审批包、批准最新审批包、拒绝最新审批包的 mock 操作入口。
- 新增 `chainpilot_ai.scripts.verify_m4`，检查 M4 DocType、审批摘要、回写安全边界、供应商沟通草稿和页面入口。

## 运行态入口

- Execution Monitor：`http://chainpilot.localhost:8000/app/execution-monitor`
- 浏览器验收截图：`/Users/sjs/chainpilot-ai/tmp/m4-execution-monitor.png`

## 当前边界

- 当前是人工审批和 mock 结果，不自动发送供应商消息。
- SAP Writeback Draft 只生成 DRAFT_ONLY payload，不调用生产 SAP 写接口。
- 二次读取校验当前基于 mock 当前值，真实 SAP 接入后需替换为 OData 当前值读取。
- 审批权限矩阵当前按默认规则：计划、采购必审；金额超过 500 万加财务；金额超过 2000 万或存在风险加供应链总监。

## 验证命令

```bash
python3 -m chainpilot_ai.scripts.run_smoke_tests
python3 -m chainpilot_ai.scripts.verify_m4
bench --site chainpilot.localhost migrate
bench --site chainpilot.localhost execute chainpilot_ai.approval.service.create_approval_package_rpc --kwargs '{"limit":5}'
bench --site chainpilot.localhost execute chainpilot_ai.approval.service.approve_package_rpc
bench --site chainpilot.localhost execute chainpilot_ai.approval.service.reject_package_rpc
bench --site chainpilot.localhost execute chainpilot_ai.scripts.verify_m4.run
bench --site chainpilot.localhost run-tests --app chainpilot_ai
bench build --app chainpilot_ai
```

本轮实际验收结果：本地 smoke、M1/M2/M3/M4 verify、`bench migrate`、M4 bench verify、Frappe app tests、`bench build` 均通过；Execution Monitor 当前页浏览器 console 无 warning/error。

## 下一步

继续推进 M5 学习闭环：采纳率、拒绝原因、供应商接受率、兑现率、缺料事件和规则调权逻辑。
