# M2 进度报告

日期：2026-05-28

## 本次完成

- 新增 SAP Connection、SAP Endpoint、SAP Field Mapping、SAP Sync Job、SAP API Log。
- 新增 SAP Material Snapshot、SAP Inventory Snapshot、SAP PR Line、SAP PO Line 四类 P0 快照对象。
- 扩展 `sap_connector.service`：支持 mock 连接测试、Endpoint dry-run、mock 同步、快照 upsert、同步任务和 API 日志。
- 新增 SAP Integration Console 页面，用于查看连接状态、Endpoint、快照计数、同步任务和 API 日志。
- Workspace 和 Command Center 增加 SAP 集成台入口。
- 新增 `chainpilot_ai.scripts.verify_m2`，用于检查 M2 DocType、页面入口、mock adapter 和快照 key 契约。

## 运行态入口

- SAP Integration Console：`http://chainpilot.localhost:8000/app/sap-integration-console`

## 当前边界

- 真实 SAP 尚未接入，M2 当前使用确定性 mock adapter。
- 非 mock 模式只返回 Dry Run，不访问外部 SAP。
- 不包含任何生产 SAP 写操作；写回草稿仍属于 M4。
- 真实 SAP Base URL、Client、认证方式、OData Service、EntitySet 和字段映射仍是外部输入项。

## 验证命令

```bash
python3 -m chainpilot_ai.scripts.run_smoke_tests
python3 -m chainpilot_ai.scripts.verify_m2
bench --site chainpilot.localhost migrate
bench --site chainpilot.localhost execute chainpilot_ai.sap_connector.service.ensure_mock_configuration
bench --site chainpilot.localhost execute chainpilot_ai.sap_connector.service.run_mock_sync --kwargs '{"endpoint_name":"all"}'
bench --site chainpilot.localhost execute chainpilot_ai.scripts.verify_m2.run
bench --site chainpilot.localhost run-tests --app chainpilot_ai
bench build --app chainpilot_ai
```

## 下一步

M2 后续可以接入真实 SAP 只读 OData 配置，或先进入 M3 Agent 方案生成与解释链路；在没有 SAP 凭据前，建议继续用 mock adapter 完成 M3/M4 的端到端产品验证。
