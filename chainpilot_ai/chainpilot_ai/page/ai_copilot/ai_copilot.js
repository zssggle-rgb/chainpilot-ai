(function () {
  const chainpilot = window.chainpilot || (window.chainpilot = {});
  chainpilot.escape = chainpilot.escape || function (value) {
    return frappe.utils.escape_html(value == null ? "" : String(value));
  };
  chainpilot.number = chainpilot.number || function (value, decimals = 0) {
    return Number(value || 0).toLocaleString(undefined, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  };
  chainpilot.badge = chainpilot.badge || function (label, tone = "neutral") {
    return `<span class="chainpilot-badge ${tone}">${chainpilot.escape(label)}</span>`;
  };

  frappe.pages["ai-copilot"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
      parent: wrapper,
      title: __("AI Copilot"),
      single_column: true,
    });

    page.set_primary_action(__("运行动作生成"), () => run_agent(page));
    page.add_inner_button(__("动作收件箱"), () => frappe.set_route("action-inbox"));
    page.add_inner_button(__("方案工作台"), () => frappe.set_route("scenario-studio"));
    page.main.html(`<div class="chainpilot-shell"><div class="chainpilot-loading">${__("正在加载 AI Copilot...")}</div></div>`);
    load_dashboard(page);
  };

  async function load_dashboard(page) {
    try {
      const response = await frappe.call({
        method: "chainpilot_ai.agent.service.get_agent_dashboard",
      });
      render_dashboard(page, response.message || {});
    } catch (error) {
      console.error(error);
      page.main.find(".chainpilot-shell").html(`<div class="chainpilot-empty">${__("无法加载 AI Copilot。")}</div>`);
    }
  }

  function render_dashboard(page, data) {
    const runs = data.runs || [];
    const logs = data.tool_logs || [];
    const issues = data.issues || [];
    const counts = data.counts || {};
    const latest = runs[0] || {};

    page.main.find(".chainpilot-shell").html(`
      <section class="chainpilot-hero">
        <div>
          <div class="chainpilot-eyebrow">${__("M3 Agent Run")}</div>
          <h1 class="chainpilot-title">${__("AI Copilot")}</h1>
          <p class="chainpilot-subtitle">
            ${__("从自然语言业务目标生成结构化场景、候选动作、约束校验、证据和解释。当前使用确定性 mock Agent，后续可替换为真实 LLM 工具调用。")}
          </p>
        </div>
        <div class="chainpilot-meta-grid">
          ${meta_item(__("Agent Run"), chainpilot.number(counts["Agent Run"] || 0))}
          ${meta_item(__("Tool Log"), chainpilot.number(counts["Agent Tool Log"] || 0))}
          ${meta_item(__("数据质量"), chainpilot.number(counts["Data Quality Issue"] || 0))}
          ${meta_item(__("最近状态"), latest.status || __("Not Run"))}
        </div>
      </section>

      <section class="chainpilot-grid-2">
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">${__("业务目标")}</h2>
              <p class="chainpilot-panel-note">${__("示例：释放 8000 万，不影响空调，优先改 PR。")}</p>
            </div>
            ${chainpilot.badge("Mock Agent", "blue")}
          </div>
          <textarea class="form-control" rows="5" data-agent-goal>${__("释放 8000 万，不影响空调，优先改 PR，并保持安全库存不低于 28 天。")}</textarea>
          <div style="margin-top: 14px;">
            <button class="chainpilot-link-button" data-run-agent="1">${__("生成场景和动作")}</button>
            <button class="chainpilot-filter" data-route="action-inbox">${__("查看动作队列")}</button>
          </div>
        </div>

        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">${__("最近输出")}</h2>
              <p class="chainpilot-panel-note">${__("Agent Run 会保留状态、约束和输出摘要。")}</p>
            </div>
          </div>
          ${latest.agent_run_id ? run_summary(latest) : empty_state(__("尚未运行 Agent。"))}
        </div>
      </section>

      <section class="chainpilot-grid-2">
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">${__("Agent Run 历史")}</h2>
              <p class="chainpilot-panel-note">${__("可追溯输入、状态、场景和输出。")}</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${runs.map(run_row).join("") || empty_state(__("尚无 Agent Run。"))}
          </div>
        </div>
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">${__("工具调用")}</h2>
              <p class="chainpilot-panel-note">${__("解析、校验、优化、动作生成、证据和解释都要留痕。")}</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${logs.map(tool_row).join("") || empty_state(__("尚无工具日志。"))}
          </div>
        </div>
      </section>

      <section class="chainpilot-panel" style="margin-top: 18px;">
        <div class="chainpilot-panel-header">
          <div>
            <h2 class="chainpilot-panel-title">${__("数据质量提示")}</h2>
            <p class="chainpilot-panel-note">${__("优化前暴露快照、映射和缺失字段风险。")}</p>
          </div>
        </div>
        <div class="chainpilot-action-list">
          ${issues.map(issue_card).join("") || empty_state(__("暂无数据质量问题。"))}
        </div>
      </section>
    `);

    page.main.find("[data-run-agent]").on("click", () => run_agent(page));
    page.main.find("[data-route='action-inbox']").on("click", () => frappe.set_route("action-inbox"));
  }

  async function run_agent(page) {
    const goal = page.main.find("[data-agent-goal]").val();
    frappe.show_alert({ message: __("正在运行 mock Agent..."), indicator: "blue" });
    const response = await frappe.call({
      method: "chainpilot_ai.agent.service.run_agent_rpc",
      args: { user_goal: goal },
    });
    const result = response.message || {};
    frappe.show_alert({
      message: __("Agent 已生成 {0} 条动作", [chainpilot.number((result.recommendations || []).length)]),
      indicator: result.ok ? "green" : "orange",
    });
    load_dashboard(page);
  }

  function run_summary(run) {
    return `
      <div class="chainpilot-compact-list">
        ${meta_item(__("Run ID"), run.agent_run_id || "-")}
        ${meta_item(__("场景"), run.scenario_id || "-")}
        ${meta_item(__("状态"), run.current_state || "-")}
        ${meta_item(__("输出"), run.output_summary || "-")}
      </div>
    `;
  }

  function run_row(run) {
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.escape(run.agent_run_id)}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(run.user_goal || "")}</div>
        </div>
        <div>
          ${chainpilot.badge(run.status || "-", run.status === "Success" ? "green" : "amber")}
          <div class="chainpilot-metric-label">${chainpilot.escape(run.current_state || "")}</div>
        </div>
      </div>
    `;
  }

  function tool_row(log) {
    const summary = (log.output_summary || "").length > 120 ? `${(log.output_summary || "").slice(0, 120)}...` : log.output_summary || "";
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.escape(log.tool_name || "")}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(summary)}</div>
        </div>
        <div>
          ${chainpilot.badge(log.status || "-", log.status === "Success" ? "green" : "red")}
          <div class="chainpilot-metric">${chainpilot.number(log.duration_ms || 0)}ms</div>
        </div>
      </div>
    `;
  }

  function issue_card(issue) {
    const tone = issue.severity === "High" || issue.severity === "Blocked" ? "red" : issue.severity === "Medium" ? "amber" : "blue";
    return `
      <div class="chainpilot-action-card">
        <div class="chainpilot-action-main">
          <div class="chainpilot-action-id">${chainpilot.escape(issue.issue_type || "")}</div>
          <div class="chainpilot-action-title">${chainpilot.escape(issue.message || "")}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(issue.recommendation || "")}</div>
        </div>
        <div>${metric(issue.object_type || "-", __("对象"))}</div>
        <div>${chainpilot.badge(issue.severity || "-", tone)}</div>
        <div>${chainpilot.badge(issue.status || "-", "neutral")}</div>
      </div>
    `;
  }

  function meta_item(label, value) {
    return `<div class="chainpilot-meta-item"><div class="chainpilot-label">${chainpilot.escape(label)}</div><div class="chainpilot-value">${chainpilot.escape(value)}</div></div>`;
  }

  function metric(value, label) {
    return `<div><div class="chainpilot-metric">${chainpilot.escape(value)}</div><div class="chainpilot-metric-label">${chainpilot.escape(label)}</div></div>`;
  }

  function empty_state(message) {
    return `<div class="chainpilot-empty">${chainpilot.escape(message)}</div>`;
  }
})();
