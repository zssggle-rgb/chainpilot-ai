# M3 进度报告

日期：2026-05-28

## 本次完成

- 新增 Agent Run、Agent Tool Log、Data Quality Issue 三个 M3 审计对象。
- 扩展 `scenario.service`：支持 `parse_user_goal`、默认约束补齐和约束 schema 校验。
- 扩展 `agent.service`：实现确定性 mock Agent Run，可生成 Scenario、Scenario Result、10 条 Recommendation、Evidence、Constraint Check、Tool Log 和 Data Quality Issue。
- 新增 AI Copilot 页面，可输入自然语言目标并触发动作生成。
- Workspace 和 Command Center 增加 AI Copilot 入口。
- 新增 `chainpilot_ai.scripts.verify_m3`，检查 M3 DocType、目标解析、约束校验、Agent Run 和页面入口。

## 运行态入口

- AI Copilot：`http://chainpilot.localhost:8000/app/ai-copilot`

## 当前边界

- 当前是确定性 mock Agent，不调用真实 LLM。
- Agent 不审批、不直接写 SAP、不生成生产回写；所有 SAP 写入仍保持 M4 回写草稿边界。
- 真实 LLM 接入后，仍应保留当前 Tool Log、Evidence 和 Constraint Check 契约。
- 真实 AI 能力已拆解到 `docs/AI_FUNCTION_IMPLEMENTATION_RESEARCH.md`，后续按 M3R 执行，不能再把 mock Agent 标记为真实 AI 完成。

## 验证命令

```bash
python3 -m chainpilot_ai.scripts.run_smoke_tests
python3 -m chainpilot_ai.scripts.verify_m3
bench --site chainpilot.localhost migrate
bench --site chainpilot.localhost execute chainpilot_ai.agent.service.run_agent_rpc --kwargs '{"user_goal":"释放 8000 万，不影响空调，优先改 PR，并保持安全库存不低于 28 天。"}'
bench --site chainpilot.localhost execute chainpilot_ai.scripts.verify_m3.run
bench --site chainpilot.localhost run-tests --app chainpilot_ai
bench build --app chainpilot_ai
```

## 下一步

进入 M4 审批包、供应商沟通草稿和 SAP Writeback Draft；在真实 SAP 未接入前，继续保持 draft-only 和人工审批边界。
