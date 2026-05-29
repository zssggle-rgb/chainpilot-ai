# ChainPilot AI LLM Provider 配置说明

## 当前配置

本机 `chainpilot.localhost` 已配置 Volcengine Ark Plan：

| 配置项 | 值 |
| --- | --- |
| provider | `volcengine_openai` |
| OpenAI compatible base_url | `https://ark.cn-beijing.volces.com/api/plan/v3` |
| Anthropic compatible base_url | `https://ark.cn-beijing.volces.com/api/plan` |
| model | `glm-5.1` |
| timeout | `90` 秒 |
| thinking | `disabled` |

API Key 已写入本机 Frappe site config，不进入 Git、不写入日志。

## 代码入口

- Provider：`chainpilot_ai/ai/provider.py`
- 结构化输出与护栏：`chainpilot_ai/ai/guardrails.py`
- 证据绑定解释服务：`chainpilot_ai/ai/service.py`
- 真实连接测试：`chainpilot_ai/scripts/test_llm_provider.py`
- 审计 DocType：`LLM Call Log`

## 测试命令

```bash
cd /Users/sjs/chainpilot-ai-bench
bench --site chainpilot.localhost execute chainpilot_ai.scripts.test_llm_provider.run
```

当前测试结果：

```json
{
  "ok": true,
  "connection": {
    "ok": true,
    "provider": "volcengine_openai",
    "model": "glm-5.1"
  },
  "explanation": {
    "status": "Ready",
    "model_name": "glm-5.1",
    "prompt_version": "evidence-explanation-v1"
  }
}
```

`glm-5.1` 默认会消耗 token 输出 `reasoning_content`，可能导致 `message.content` 为空。当前 Provider 对 `glm-5` 系列默认发送 `thinking: {"type": "disabled"}`，用于稳定生成结构化业务 JSON。

## 安全边界

LLM 不能直接决策：

- 不计算金额、概率、库存天数、缺料数量。
- 不选择采购动作。
- 不决定审批通过。
- 不直接写 SAP。

LLM 只用于：

- 中文解释。
- 审批摘要。
- 目标解析。
- 供应商沟通草稿。
- 反馈归因分类。

所有输出必须通过：

- JSON Schema 校验。
- `evidence_id` 存在性校验。
- 禁止直接回写 SAP 的业务校验。
- 面向用户文案校验。

## 配置命令模板

不要把真实 key 写入仓库文件。需要重新配置时使用：

```bash
cd /Users/sjs/chainpilot-ai-bench
bench --site chainpilot.localhost set-config chainpilot_llm_provider volcengine_openai
bench --site chainpilot.localhost set-config chainpilot_llm_base_url https://ark.cn-beijing.volces.com/api/plan/v3
bench --site chainpilot.localhost set-config chainpilot_llm_model glm-5.1
bench --site chainpilot.localhost set-config chainpilot_llm_timeout_seconds 90
bench --site chainpilot.localhost set-config chainpilot_llm_disable_thinking true
bench --site chainpilot.localhost set-config chainpilot_llm_api_key "<YOUR_API_KEY>"
```
