# ChainPilot AI 功能实现研究

日期：2026-05-29

适用范围：重开 M3 真实 AI 能力，实现前端可演示、后端可审计、后续可替换真实 SAP 的 AI Agent。

## 1. 结论

当前系统已经有 Agent Run、Tool Log、Scenario、Recommendation、Evidence、Approval、Writeback Draft、Learning Signal 等业务对象，但 AI 仍是规则和模板模拟。下一步不能继续扩展“聊天页面”，而要把 AI 拆成固定任务，用 SOP 约束输入、工具、模型输出、校验和落库。

ChainPilot AI 的正确定位：

1. AI 不替代供应链优化算法，只负责理解业务目标、解释结果、生成业务文本、协同审批、监控异常和沉淀反馈。
2. AI 不直接写 SAP，不直接审批，不直接删除业务数据。
3. AI 输出必须是结构化 JSON 或绑定证据的中文文本，不能把自由发挥内容直接写入业务单据。
4. 没有证据时，不生成正式解释；没有审批时，不生成可执行回写草稿。
5. 每次模型调用都必须记录到审计日志，包含任务、模型、输入摘要、输出摘要、Schema 版本、耗时、错误和降级原因。

## 2. AI 可以处理的任务

| 任务代码 | 任务名称 | 触发入口 | AI 负责 | 规则/工具负责 | 主要产物 |
| --- | --- | --- | --- | --- | --- |
| `INTENT_TO_CONSTRAINTS` | 需求澄清 | 用户输入目标 | 把中文目标转成约束 JSON，识别缺失信息并提出澄清问题 | Schema 校验、默认值、权限边界 | Scenario Constraint |
| `DATA_DIAGNOSIS` | 数据体检 | 生成方案前、SAP 同步后 | 汇总数据异常影响和处理建议 | 快照新鲜度、缺失字段、预测偏差、交期、库存规则 | Data Quality Issue |
| `SCENARIO_DEBATE` | 方案比较 | 场景生成后 | 解释保守、推荐、激进方案差异和适用条件 | 优化结果、风险仿真、约束统计 | Scenario Result Summary |
| `ACTION_CARD_GENERATION` | 动作卡片生成 | 方案确认后 | 生成动作标题、业务说明、复核关注点 | 拆分 SAP 单据行、金额计算、约束校验 | Recommendation |
| `EVIDENCE_EXPLANATION` | 证据解释 | 打开建议详情、提交审批前 | 基于证据生成原因、风险、不执行影响和替代建议 | 证据检索、Evidence ID 校验、数字一致性校验 | AI Explanation |
| `APPROVAL_SUMMARY` | 审批摘要 | 创建审批包 | 生成审批摘要、决策选项、风险提示 | 审批路由、金额阈值、角色权限 | Approval Package |
| `SUPPLIER_COMMUNICATION` | 供应商沟通草稿 | PO 调期、确认供应商前 | 生成中文沟通草稿和待确认事项 | PO 行、供应商、交期、审批状态 | Supplier Communication Draft |
| `EXECUTION_MONITORING` | 执行监控 | 回写草稿生成后、定时任务 | 总结执行偏差和建议跟进动作 | SAP 当前快照、Execution Result、差异计算 | Execution Insight |
| `LEARNING_SIGNALING` | 闭环学习 | 采纳、拒绝、兑现、缺料事件后 | 归类拒绝原因、缺料根因，生成规则调权草稿说明 | 指标计算、权重上限、人工复核 | Learning Signal、Rule Weight Adjustment |

不做开放式“问答机器人”作为第一优先级。用户问“为什么建议改这张 PR”时，本质上调用 `EVIDENCE_EXPLANATION`；用户说“帮我释放 8000 万”时，本质上调用 `INTENT_TO_CONSTRAINTS` 和后续工具链。

## 3. 总体 SOP

每个 AI 任务都按同一条 SOP 执行：

1. 接收任务：前端或服务端只传任务代码、业务对象 ID 和用户输入，不把整库数据直接塞给模型。
2. 取上下文：按任务读取最小必要数据，例如 Scenario、Recommendation、Evidence、SAP Snapshot、Approval Package。
3. 执行工具：先用确定性代码完成数字计算、字段映射、SAP 对象定位、约束校验和证据检索。
4. 组装提示词：提示词只描述任务、边界、输出 Schema 和已检索证据，不允许模型自行假设 SAP 数据。
5. 调用模型：通过统一 Provider 调用 OpenAI、DeepSeek、Azure OpenAI 或企业网关；没有密钥时使用 Mock Provider。
6. 结构化校验：JSON 必须通过 Schema；枚举、金额、日期、SAP 对象和 Evidence ID 必须通过业务校验。
7. 风险拦截：发现无证据解释、越权审批、直接写 SAP、伪造金额、引用不存在 Evidence 时，任务失败或降级为待复核。
8. 落库审计：业务结果写入对应 DocType；模型调用写入 LLM Call Log；工具调用继续写 Agent Tool Log。
9. 展示结果：界面只展示中文业务结果、证据来源、校验状态和下一步按钮，不展示提示词过程语言。
10. 反馈闭环：用户采纳、拒绝、修改、供应商反馈和兑现情况写入 Feedback Record 和 Learning Signal。

## 4. 分任务 SOP

### 4.1 需求澄清器

目标：把计划经理的自然语言目标转为可执行约束。

输入：

- `user_goal`：用户原始中文目标。
- `planning_context`：公司、工厂、产品线、时间范围、当前基线金额。
- `allowed_actions`：当前角色允许发起的动作类型。

SOP：

1. 规则预处理：识别金额、产品线、PR/PO、安全库存、冻结期等显性信息。
2. LLM 解析：输出严格 JSON，包括目标类型、现金目标、保护对象、偏好动作、硬约束、软约束、缺失信息和置信度。
3. Schema 校验：拒绝未知字段，补齐默认值。
4. 业务校验：禁止 `sap_writeback_mode=direct_write`，禁止用户越权选择动作。
5. 澄清判断：如果缺少时间范围、工厂或目标冲突，返回澄清问题，不进入优化。
6. 落库：通过校验后写 Scenario 和 Agent Run。

输出示例：

```json
{
  "intent_type": "cash_release",
  "cash_release_target": 80000000,
  "protected_product_lines": ["空调"],
  "preferred_actions": ["REDUCE_PR_QTY"],
  "minimum_inventory_days": 28,
  "sap_writeback_mode": "draft_only",
  "clarification_needed": false,
  "clarification_questions": [],
  "assumptions": ["未指定工厂时默认使用当前用户有权限的主工厂"],
  "confidence": 0.86
}
```

### 4.2 数据侦探

目标：优化前先判断数据是否适合生成动作。

输入：

- SAP Material、Inventory、PR、PO 快照。
- 预测、历史消耗、供应商确认、主数据字段。

SOP：

1. 快照检查：校验同步时间、必填字段、单位、币种、数量异常。
2. 统计检查：识别预测偏差、库存覆盖异常、供应商交付恶化、交期主数据异常。
3. 严重级别判定：确定 Info、Low、Medium、High、Blocking。
4. LLM 摘要：只基于规则输出的问题生成中文摘要、影响范围和建议处理方式。
5. 阻塞规则：Blocking 问题存在时，不允许生成正式动作，只能生成待复核场景。
6. 落库：写 Data Quality Issue，并关联 source_id。

### 4.3 方案辩论器

目标：让管理者理解保守、推荐、激进方案之间的收益和风险。

输入：

- Scenario Constraint。
- 优化结果和风险仿真结果。
- 数据质量问题和约束校验统计。

SOP：

1. 工具生成方案：优化工具输出保守、推荐、激进三个 Scenario Result。
2. 规则计算：现金释放、缺料风险、审批动作数、供应商确认数、待复核数。
3. LLM 摘要：生成中文管理层摘要，说明推荐方案为什么被选中。
4. 数字校验：摘要中的金额、数量、风险数字必须来自 Scenario Result。
5. 落库：把摘要写入 Scenario Result，不覆盖原始指标。

### 4.4 动作生成器

目标：把方案拆成 SAP 单据行级动作。

输入：

- Scenario Result。
- SAP PR/PO/库存/物料快照。
- 约束校验规则。

SOP：

1. 候选动作生成：确定性代码按 SAP 单据行生成候选动作。
2. 约束校验：冻结期、MOQ/MPQ、安全库存、供应商确认、审批阈值。
3. 动作筛选：BLOCKED 不进入审批；PASS_WITH_APPROVAL 标记需复核。
4. LLM 辅助：生成中文动作标题、业务说明和复核关注点，不决定数值。
5. 落库：写 Recommendation、Constraint Check Result 和 Agent Tool Log。

### 4.5 证据解释器

目标：解释“为什么建议这么改”，并且每句话能追溯到证据。

输入：

- Recommendation。
- Recommendation Evidence。
- 相关 SAP Snapshot、约束校验、数据质量问题、历史反馈。

SOP：

1. 证据检索：读取单据行、库存覆盖、历史消耗、预测偏差、供应商确认、约束结果。
2. 证据包压缩：只把必要字段给模型，保留 evidence_id、source_type、source_id。
3. LLM 生成：输出结论、原因、风险、不执行影响、替代动作和复核条件。
4. 证据校验：每条原因必须引用已存在的 evidence_id。
5. 数字校验：解释里的金额、日期、数量必须与业务对象一致。
6. 缺证降级：没有 Evidence 时写 `NEED_EVIDENCE`，不展示正式解释。

输出结构：

```json
{
  "status": "READY",
  "summary": "建议下调该采购申请数量，以减少高库存物料的资金占用。",
  "reasons": [
    {
      "text": "调整后库存覆盖仍高于安全阈值。",
      "evidence_ids": ["EVD-001"]
    }
  ],
  "risks": [
    {
      "text": "若未来两周需求上调，需要重新评估缺料风险。",
      "evidence_ids": ["EVD-002"]
    }
  ],
  "review_required": false
}
```

### 4.6 协同代理

目标：让审批人和采购员能直接处理动作包，而不是阅读原始分析报告。

输入：

- 多条 Recommendation。
- 约束校验和证据解释。
- 审批角色、金额阈值、供应商信息。

SOP：

1. 分组：按场景、采购组、供应商、风险等级和审批角色打包。
2. 审批路由：规则决定审批角色，LLM 不决定审批权限。
3. 摘要生成：LLM 生成中文审批摘要、关键风险、需审批人确认的问题。
4. 供应商草稿：对 PO 调期或供应商确认事项生成沟通草稿。
5. 人工确认：草稿必须由用户点击发送或进入外部沟通系统。
6. 落库：写 Approval Package、Approval Task、Supplier Communication Draft。

### 4.7 执行监控代理

目标：审批后持续判断建议有没有兑现、有没有风险外溢。

输入：

- SAP Writeback Draft。
- Execution Result。
- 最新 SAP 快照或 mock 快照。
- 供应商反馈、缺料事件。

SOP：

1. 状态检查：草稿是否生成、是否冲突、是否人工执行。
2. 兑现计算：比较预计释放金额和实际释放金额。
3. 异常识别：未执行、部分兑现、供应商拒绝、缺料事件、SAP 当前值冲突。
4. LLM 摘要：生成中文异常说明和跟进建议。
5. 落库：写 Execution Result、Feedback Record、Learning Signal。

### 4.8 闭环学习器

目标：把采纳、拒绝、兑现、供应商反馈和缺料事件变成下一轮推荐权重。

输入：

- Approval Package。
- Feedback Record。
- Execution Result。
- Supplier Communication Draft。
- Shortage Event。

SOP：

1. 指标计算：采纳率、拒绝率、供应商接受率、兑现率、缺料事件数。
2. 原因归类：LLM 把拒绝原因、供应商反馈、未兑现原因归入固定分类。
3. 调权建议：规则生成权重变化上限，LLM 只生成解释。
4. 人工复核：Rule Weight Adjustment 先为 Draft，管理员确认后才能 Applied。
5. 版本记录：记录权重版本、理由、适用范围和回滚方式。

## 5. 技术实现

### 5.1 新增模块

建议新增 `chainpilot_ai/ai/`：

```text
chainpilot_ai/ai/
  __init__.py
  contracts.py          # 任务代码、请求、响应、错误类型
  provider.py           # Provider 抽象和统一调用入口
  guardrails.py         # 越权、证据、金额、SAP 写入边界校验
  retrieval.py          # Evidence 和 SAP Snapshot 检索
  schemas.py            # JSON Schema 注册表
  sop.py                # 任务 SOP 注册表
  tasks/
    intent.py
    data_diagnosis.py
    scenario_debate.py
    action_cards.py
    explanation.py
    approval.py
    communication.py
    monitoring.py
    learning.py
  providers/
    mock_provider.py
    openai_provider.py
    deepseek_provider.py
    http_provider.py
```

`agent/service.py` 不再直接拼 mock 结果，而是变成编排器：

```text
run_agent
  -> run_ai_task(INTENT_TO_CONSTRAINTS)
  -> run_tool(DATA_DIAGNOSIS)
  -> run_tool(RUN_OPTIMIZATION)
  -> run_ai_task(SCENARIO_DEBATE)
  -> run_tool(ACTION_CARD_GENERATION)
  -> run_ai_task(EVIDENCE_EXPLANATION)
  -> persist result
```

### 5.2 新增 DocType

| DocType | 用途 | 关键字段 |
| --- | --- | --- |
| AI Provider Config | 配置模型供应商 | provider、base_url、model、api_key、enabled、timeout |
| AI Task Config | 配置任务使用哪个模型 | task_code、provider、model、temperature、schema_version、fallback_mode |
| AI Prompt Template | 管理提示词版本 | task_code、version、system_prompt、user_template、output_schema |
| LLM Call Log | 模型调用审计 | task_code、provider、model、input_hash、output_hash、schema_version、duration_ms、status、error |
| AI Evaluation Case | 回归测试集 | task_code、input_json、expected_json、required_evidence_ids、status |

密钥字段使用 Frappe Password 字段或环境变量，不写入日志。

### 5.3 Provider 设计

统一接口：

```python
class LLMProvider:
    def generate_json(
        self,
        task_code: str,
        system_prompt: str,
        user_payload: dict,
        schema: dict,
        temperature: float = 0,
    ) -> dict:
        ...
```

Provider 要求：

1. 支持 `generate_json`，返回 JSON、原始响应摘要、token 用量、耗时、模型名。
2. 支持 `health_check`，用于 SAP 接入配置页旁边的模型配置检查。
3. 失败时返回结构化错误，不把异常栈展示给业务用户。
4. 所有输出先进入 Schema 校验和业务校验，再落库。

首版可以用 `requests` 直接调用 OpenAI 兼容接口，减少 SDK 绑定。OpenAI 接入优先使用 Structured Outputs 或 function calling；DeepSeek 接入使用 JSON Output，并在本地执行 Schema 校验和重试。

### 5.4 RAG 与证据检索

MVP 不需要先上向量库。先做“结构化检索 + 小证据包”：

1. 按 Recommendation 读取 SAP 单据行、库存快照、物料快照、PO/PR、约束校验、数据质量问题。
2. 生成 Evidence Bundle，每条包含 `evidence_id`、`source_type`、`source_id`、`metric_name`、`metric_value`、`threshold_value`、`summary`。
3. LLM 只能引用 Evidence Bundle 里的证据。
4. 解释校验器检查所有 `evidence_ids` 是否存在。
5. 后续如果加入向量库，只用于检索历史报告、SOP 和供应商沟通记录，不替代结构化证据。

### 5.5 异步执行

长任务应使用 Frappe background job：

1. 前端创建 Agent Run。
2. 后端 `frappe.enqueue` 执行真实 Agent。
3. 前端轮询 Agent Run 和 Tool Log。
4. 每个步骤更新 `current_state`。
5. 失败时保留已完成步骤和错误摘要。

短任务，如打开 Recommendation 生成解释，可以同步执行，但仍要写 LLM Call Log。

## 6. 安全与边界

| 风险 | 控制方式 |
| --- | --- |
| 模型直接建议写 SAP | Prompt 禁止 + 业务校验禁止 `direct_write` |
| 模型编造金额或日期 | 数字必须来自业务对象；校验不通过则失败 |
| 无证据解释 | `evidence_ids` 为空时状态为 `NEED_EVIDENCE` |
| 英文或过程语言进入界面 | 输出 Schema 限制中文字段；UI 只展示业务字段 |
| 密钥泄露 | Password 字段或环境变量；日志只存 hash 和摘要 |
| 供应商沟通误发 | 只生成 Draft，必须人工确认 |
| 学习调权失控 | 权重变更先 Draft，管理员审核后 Applied |

## 7. 验收标准

| 编号 | 验收项 | 通过标准 |
| --- | --- | --- |
| AI-001 | 模型配置 | 可配置至少一个真实模型 Provider，测试连接结果可见 |
| AI-002 | 无密钥降级 | 没有模型密钥时使用 Mock Provider，并清楚标记为模拟 |
| AI-003 | 需求解析 | 20 条中文业务目标中，关键字段解析准确率不低于 90% |
| AI-004 | 结构化输出 | 所有 LLM 输出通过 JSON Schema；非法字段被拒绝 |
| AI-005 | 证据解释 | 正式解释 100% 包含有效 evidence_id |
| AI-006 | 数字一致性 | 解释中的金额、数量、日期不得与业务对象不一致 |
| AI-007 | 审计 | 每次模型调用都有 LLM Call Log 和 Agent Tool Log |
| AI-008 | 中文界面 | 前端业务文案不出现英文按钮、英文标题或过程解释语言 |
| AI-009 | SAP 边界 | AI 不能直接写 SAP，只能生成回写草稿 |
| AI-010 | 回归测试 | Mock Provider、Schema 校验、证据校验、失败降级均有自动化测试 |

## 8. 实施拆解

### M3R-01：AI 基础设施

- 新增 `chainpilot_ai/ai/` 模块。
- 新增 AI Provider Config、AI Task Config、AI Prompt Template、LLM Call Log。
- 实现 Mock、OpenAI 兼容 HTTP Provider、DeepSeek Provider。
- 增加模型健康检查。

### M3R-02：任务 Schema 和 SOP 注册表

- 定义九类 AI 任务代码。
- 为每类任务定义输入 Schema、输出 Schema、校验器和提示词模板。
- 把当前 `parse_user_goal` 改成规则预处理 + LLM 结构化解析 + 规则校验。

### M3R-03：证据解释闭环

- 实现 Evidence Bundle 检索。
- 实现 `EVIDENCE_EXPLANATION`。
- Recommendation 详情页展示“结论、证据、风险、复核条件”，不展示提示词过程。

### M3R-04：方案摘要和审批摘要

- 实现 `SCENARIO_DEBATE` 和 `APPROVAL_SUMMARY`。
- Scenario Studio 展示方案比较摘要。
- Approval Package 使用 LLM 生成中文审批摘要，但审批路由仍走规则。

### M3R-05：沟通、监控、学习

- 实现 `SUPPLIER_COMMUNICATION`、`EXECUTION_MONITORING`、`LEARNING_SIGNALING`。
- Supplier Communication Draft 只生成草稿。
- Learning Center 展示规则调权草稿和证据来源。

### M3R-06：验收与演示

- 准备 20 条中文目标解析评测集。
- 准备 20 条 Recommendation 证据解释评测集。
- 跑无密钥 Mock、真实模型、模型失败降级三组 smoke test。
- 更新 M3 进度报告，把“mock 完成”和“真实 AI 完成”分开。

## 9. 外部技术依据

- OpenAI Structured Outputs：用于让模型输出符合 JSON Schema 的结构化结果。
  https://developers.openai.com/api/docs/guides/structured-outputs
- OpenAI Function Calling：用于让模型通过 JSON Schema 描述的工具访问应用侧数据和能力。
  https://developers.openai.com/api/docs/guides/function-calling
- DeepSeek JSON Output：用于 OpenAI 兼容接口下输出有效 JSON，再由本地 Schema 校验。
  https://api-docs.deepseek.com/guides/json_mode
- Frappe Password Field：用于存储密码、密钥等敏感字段。
  https://docs.frappe.io/framework/user/en/basics/doctypes/fieldtypes
- Frappe Background Jobs：用于把长耗时 Agent Run 放入后台队列。
  https://docs.frappe.io/framework/user/en/api/background_jobs

