(() => {
  const chainpilot = window.chainpilot || (window.chainpilot = chainpilot_utils());

  frappe.pages["scenario-studio"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
      parent: wrapper,
      title: __("Scenario Studio"),
      single_column: true,
    });

    page.set_primary_action(__("返回决策台"), () => frappe.set_route("chainpilot-ai-command-center"));
    page.set_secondary_action(__("动作收件箱"), () => frappe.set_route("action-inbox"));
    page.main.html(`<div class="chainpilot-shell"><div class="chainpilot-loading">${__("正在加载方案工作台...")}</div></div>`);
    load_scenario_studio(page);
  };

  async function load_scenario_studio(page) {
    try {
      const [sessions, scenarios, results, recommendations] = await Promise.all([
        frappe.db.get_list("Optimization Session", {
          fields: ["session_id", "source_system", "baseline_amount", "material_count", "run_date", "status"],
          limit: 10,
          order_by: "run_date desc",
        }),
        frappe.db.get_list("Scenario", {
          fields: ["name", "scenario_id", "session_id", "scenario_name", "business_goal", "target_cash_release", "planning_horizon_start", "planning_horizon_end", "constraint_json", "status", "owner_role"],
          limit: 20,
          order_by: "modified desc",
        }),
        frappe.db.get_list("Scenario Result", {
          fields: ["result_id", "scenario_id", "strategy_name", "strategy_type", "purchase_amount", "cash_release", "cash_release_rate", "risk_level", "recommendation_count", "ai_recommendation"],
          limit: 50,
        }),
        frappe.db.get_list("Recommendation", {
          fields: ["result_id", "recommendation_id", "cash_release", "approval_status", "shortage_risk_after"],
          limit: 200,
        }),
      ]);

      render_scenario_studio(page, { sessions, scenarios, results, recommendations });
    } catch (error) {
      page.main.find(".chainpilot-shell").html(`<div class="chainpilot-empty">${__("无法加载方案工作台。")}</div>`);
      console.error(error);
    }
  }

  function render_scenario_studio(page, data) {
    const session = data.sessions[0] || {};
    const scenarioIdsWithResults = new Set(data.results.map((item) => item.scenario_id).filter(Boolean));
    const scenario = data.scenarios.find((item) => scenarioIdsWithResults.has(item.scenario_id)) || data.scenarios[0] || {};
    const scenarioResults = data.results.filter((item) => !scenario.scenario_id || item.scenario_id === scenario.scenario_id);
    const target = Number(scenario.target_cash_release || 170000000);
    const bestRelease = Math.max(...scenarioResults.map((item) => Number(item.cash_release || 0)), 0);
    const attainment = target ? (bestRelease / target) * 100 : 0;

    page.main.find(".chainpilot-shell").html(`
      <section class="chainpilot-hero">
        <div>
          <div class="chainpilot-eyebrow">${__("场景生成工作台")}</div>
          <h1 class="chainpilot-title">${__("Scenario Studio")}</h1>
          <p class="chainpilot-subtitle">
            ${__("把业务目标转成可比较的方案组合。当前使用 mock/demo 数据模拟 SAP 快照，M2 将切换到 SAP 只读同步和快照表。")}
          </p>
        </div>
        <div class="chainpilot-meta-grid">
          ${meta_item(__("当前目标"), scenario.scenario_name || __("未创建"))}
          ${meta_item(__("目标释放现金"), chainpilot.currency(target))}
          ${meta_item(__("最佳方案释放"), chainpilot.currency(bestRelease))}
          ${meta_item(__("目标达成率"), chainpilot.percent(attainment))}
        </div>
      </section>

      <section class="chainpilot-grid-2">
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">${__("业务目标")}</h2>
              <p class="chainpilot-panel-note">${__("保存目标后，可作为后续 Agent 生成方案和动作的输入。")}</p>
            </div>
            ${chainpilot.badge(scenario.status || __("Draft"), scenario.status === "Generated" ? "green" : "amber")}
          </div>
          <div class="chainpilot-detail-grid">
            <div class="chainpilot-meta-item">
              <div class="chainpilot-label">${__("目标名称")}</div>
              <input class="form-control" data-field="scenario_name" value="${chainpilot.escape(scenario.scenario_name || "释放采购现金并保持供应稳定")}">
            </div>
            <div class="chainpilot-meta-item">
              <div class="chainpilot-label">${__("目标释放现金")}</div>
              <input class="form-control" type="number" data-field="target_cash_release" value="${chainpilot.escape(scenario.target_cash_release || 170000000)}">
            </div>
            <div class="chainpilot-meta-item">
              <div class="chainpilot-label">${__("来源会话")}</div>
              <input class="form-control" data-field="session_id" value="${chainpilot.escape(scenario.session_id || session.session_id || "")}">
            </div>
          </div>
          <div style="margin-top: 12px;">
            <div class="chainpilot-label">${__("业务目标描述")}</div>
            <textarea class="form-control" rows="3" data-field="business_goal">${chainpilot.escape(scenario.business_goal || "在不突破安全库存和关键物料缺料阈值的前提下，释放 1.7 亿采购现金。")}</textarea>
          </div>
          <div class="chainpilot-detail-grid" style="margin-top: 12px;">
            <div class="chainpilot-meta-item">
              <div class="chainpilot-label">${__("开始日期")}</div>
              <input class="form-control" type="date" data-field="planning_horizon_start" value="${chainpilot.escape(scenario.planning_horizon_start || "2026-06-01")}">
            </div>
            <div class="chainpilot-meta-item">
              <div class="chainpilot-label">${__("结束日期")}</div>
              <input class="form-control" type="date" data-field="planning_horizon_end" value="${chainpilot.escape(scenario.planning_horizon_end || "2026-07-31")}">
            </div>
            <div class="chainpilot-meta-item">
              <div class="chainpilot-label">${__("负责人角色")}</div>
              <input class="form-control" data-field="owner_role" value="${chainpilot.escape(scenario.owner_role || "ChainPilot Supply Chain Director")}">
            </div>
          </div>
          <div style="margin-top: 12px;">
            <div class="chainpilot-label">${__("约束 JSON")}</div>
            <textarea class="form-control" rows="4" data-field="constraint_json">${chainpilot.escape(scenario.constraint_json || "{\"minimum_inventory_days\":28,\"max_shortage_risk_after\":3.5,\"sap_writeback_mode\":\"draft_only\",\"freeze_window_days\":7}")}</textarea>
          </div>
          <div style="margin-top: 14px;">
            <button class="chainpilot-link-button" data-save-scenario="1">${__("保存为草稿目标")}</button>
          </div>
        </div>

        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">${__("SAP 快照上下文")}</h2>
              <p class="chainpilot-panel-note">${__("当前来自 mock/demo 层，保持未来 SAP 只读接口的字段边界。")}</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${meta_item(__("来源系统"), session.source_system || "-")}
            ${meta_item(__("采购基线"), chainpilot.currency(session.baseline_amount))}
            ${meta_item(__("物料数"), chainpilot.number(session.material_count || 0))}
            ${meta_item(__("快照日期"), session.run_date || "-")}
          </div>
        </div>
      </section>

      <section class="chainpilot-panel" style="margin-top: 18px;">
        <div class="chainpilot-panel-header">
          <div>
            <h2 class="chainpilot-panel-title">${__("方案对比")}</h2>
            <p class="chainpilot-panel-note">${__("比较现金释放、风险等级、动作数量和推荐理由。")}</p>
          </div>
          <button class="chainpilot-link-button" data-route="action-inbox">${__("进入动作队列")}</button>
        </div>
        <div class="chainpilot-scenario-list">
          ${scenarioResults.map((result) => scenario_result_card(result, data.recommendations)).join("") || empty_state(__("尚无方案结果。"))}
        </div>
      </section>
    `);

    page.main.find("[data-route='action-inbox']").on("click", () => frappe.set_route("action-inbox"));
    page.main.find("[data-save-scenario]").on("click", () => save_scenario(page));
  }

  async function save_scenario(page) {
    const read = (field) => page.main.find(`[data-field='${field}']`).val();
    let constraints = read("constraint_json") || "{}";
    try {
      JSON.parse(constraints);
    } catch {
      frappe.msgprint(__("约束 JSON 格式不正确。"));
      return;
    }
    const scenarioId = `SCN-${frappe.datetime.now_datetime().replace(/[-: ]/g, "").slice(0, 14)}`;
    try {
      await frappe.db.insert({
        doctype: "Scenario",
        scenario_id: scenarioId,
        session_id: read("session_id"),
        scenario_name: read("scenario_name"),
        business_goal: read("business_goal"),
        target_cash_release: Number(read("target_cash_release") || 0),
        planning_horizon_start: read("planning_horizon_start"),
        planning_horizon_end: read("planning_horizon_end"),
        constraint_json: constraints,
        status: "Draft",
        owner_role: read("owner_role"),
      });
      frappe.show_alert({ message: __("已保存场景目标"), indicator: "green" });
      load_scenario_studio(page);
    } catch (error) {
      frappe.msgprint(__("保存场景失败，请检查必填字段和权限。"));
      console.error(error);
    }
  }

  function scenario_result_card(result, recommendations) {
    const actionRows = recommendations.filter((item) => item.result_id === result.result_id);
    const pending = actionRows.filter((item) => item.approval_status === "Pending").length;
    const risk = actionRows.filter((item) => Number(item.shortage_risk_after || 0) >= 2.5).length;
    return `
      <div class="chainpilot-scenario ${result.strategy_type === "Recommended" ? "is-recommended" : ""}">
        <div>
          <div class="chainpilot-scenario-name">${chainpilot.escape(result.strategy_name)}</div>
          <div class="chainpilot-scenario-text">${chainpilot.escape(result.ai_recommendation || "")}</div>
        </div>
        ${metric_block(__("释放现金"), chainpilot.currency(result.cash_release))}
        ${metric_block(__("动作 / 待处理"), `${chainpilot.number(result.recommendation_count || actionRows.length)} / ${chainpilot.number(pending)}`)}
        <div>
          ${metric_block(__("风险关注"), chainpilot.number(risk))}
          <div style="margin-top: 6px;">${chainpilot.badge(result.risk_level || "-", chainpilot.riskTone(result.risk_level))}</div>
        </div>
      </div>
    `;
  }

  function meta_item(label, value) {
    return `<div class="chainpilot-meta-item"><div class="chainpilot-label">${chainpilot.escape(label)}</div><div class="chainpilot-value">${chainpilot.escape(value)}</div></div>`;
  }

  function metric_block(label, value) {
    return `<div><div class="chainpilot-metric">${chainpilot.escape(value)}</div><div class="chainpilot-metric-label">${chainpilot.escape(label)}</div></div>`;
  }

  function empty_state(message) {
    return `<div class="chainpilot-empty">${chainpilot.escape(message)}</div>`;
  }

  function chainpilot_utils() {
    return {
      escape(value) {
        return frappe.utils.escape_html(value == null ? "" : String(value));
      },
      currency(value) {
        return format_currency(value || 0, frappe.defaults.get_default("currency") || "USD", 0);
      },
      number(value, decimals = 0) {
        return Number(value || 0).toLocaleString(undefined, {
          minimumFractionDigits: decimals,
          maximumFractionDigits: decimals,
        });
      },
      percent(value) {
        return `${Number(value || 0).toFixed(1)}%`;
      },
      badge(label, tone = "neutral") {
        return `<span class="chainpilot-badge ${tone}">${this.escape(label)}</span>`;
      },
      riskTone(risk) {
        if (risk === "High") return "red";
        if (risk === "Medium") return "amber";
        return "green";
      },
    };
  }
})();
