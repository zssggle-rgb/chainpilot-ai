# M1 进度报告

日期：2026-05-28

## 本次完成

- 将 Command Center 从阶段 0 统计骨架升级为产品化决策台，展示采购基线、推荐释放现金、待审批动作、风险关注、方案组合和高价值动作。
- 将 Action Inbox 从普通表格升级为动作队列，支持全部动作、释放现金、需审批、风险关注、主数据复核等筛选。
- 增强 Recommendation 表单详情，展示 SAP 单据行、原值/建议值、金额、库存覆盖、缺料风险、证据、约束校验和 AI 解释草稿。
- 补齐 `sap_connector` mock read adapter。当前无真实 SAP 连接时，接口可以返回确定性的 mock PR/PO/库存数据；非 mock 模式不访问外部 SAP。
- 新增 M1 静态验收脚本 `chainpilot_ai.scripts.verify_m1`。

## 运行态验收

- Command Center：`http://chainpilot.localhost:8000/app/chainpilot-ai-command-center`
- Action Inbox：`http://chainpilot.localhost:8000/app/action-inbox`
- Recommendation Detail：`http://chainpilot.localhost:8000/app/recommendation/REC-202605-000006`

浏览器验收结果：

- Command Center 显示 4 个核心 KPI、3 个方案、5 个高价值动作。
- Action Inbox 显示 10 张动作卡片、6 个筛选控件。
- Recommendation Detail 显示证据区、约束校验区和 AI 解释草稿。
- 浏览器未发现 console error 或 4xx 资源错误。

截图证据：

- `/Users/sjs/chainpilot-ai/tmp/m1-command-center.png`
- `/Users/sjs/chainpilot-ai/tmp/m1-action-inbox.png`
- `/Users/sjs/chainpilot-ai/tmp/m1-recommendation-detail.png`

## 验证命令

```bash
python3 -m chainpilot_ai.scripts.run_smoke_tests
python3 -m chainpilot_ai.scripts.verify_m1
bench build --app chainpilot_ai
bench --site chainpilot.localhost clear-cache
```

## M1 剩余项

- M1-02：正式 Scenario DocType 尚未创建，目前只完成 Scenario Result。
- M1-10：Scenario Studio 方案对比编辑页尚未完成。
- M1-11：Demo 导入错误报告可进一步产品化。

## 下一步

继续补齐 Scenario DocType 和 Scenario Studio，然后进入 M2 SAP 只读接入配置对象与同步日志。
