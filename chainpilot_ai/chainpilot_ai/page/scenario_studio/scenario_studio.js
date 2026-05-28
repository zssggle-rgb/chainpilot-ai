(() => {
  const chainpilot = window.chainpilot || (window.chainpilot = chainpilot_utils());
  const DEFAULT_CONSTRAINT_JSON = "{\"minimum_inventory_days\":28,\"max_shortage_risk_after\":3.5,\"sap_writeback_mode\":\"draft_only\",\"freeze_window_days\":7}";

  frappe.pages["scenario-studio"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
      parent: wrapper,
      title: "方案工作台",
      single_column: true,
    });

    page.set_primary_action("返回", () => frappe.set_route("chainpilot-ai-command-center"));
    page.set_secondary_action("建议", () => frappe.set_route("action-inbox"));
    page.main.html(`<div class="chainpilot-shell"><div class="chainpilot-loading">正在加载方案工作台...</div></div>`);
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
      page.main.find(".chainpilot-shell").html(`<div class="chainpilot-empty">无法加载方案工作台。</div>`);
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
    const constraintJson = scenario.constraint_json || DEFAULT_CONSTRAINT_JSON;

    page.main.find(".chainpilot-shell").html(`
      <section class="chainpilot-hero">
        <div>
          <div class="chainpilot-eyebrow">方案测算</div>
          <h1 class="chainpilot-title">方案工作台</h1>
          <p class="chainpilot-subtitle">
            设置业务目标，比较稳妥、推荐和进取方案。
          </p>
        </div>
        <div class="chainpilot-meta-grid">
          ${meta_item("当前目标", scenario.scenario_name || "未创建")}
          ${meta_item("目标占用减少额", chainpilot.currency(target))}
          ${meta_item("最佳占用减少额", chainpilot.currency(bestRelease))}
          ${meta_item("目标达成率", chainpilot.percent(attainment))}
        </div>
      </section>

      <section class="chainpilot-grid-2">
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">业务目标</h2>
              <p class="chainpilot-panel-note">保存后用于生成候选方案和优化建议。</p>
            </div>
            ${chainpilot.badge(chainpilot.statusLabel(scenario.status || "Draft"), scenario.status === "Generated" ? "green" : "amber")}
          </div>
          <div class="chainpilot-detail-grid">
            <div class="chainpilot-meta-item">
              <div class="chainpilot-label">目标名称</div>
              <input class="form-control" data-field="scenario_name" value="${chainpilot.escape(scenario.scenario_name || "降低采购占用并保持供应稳定")}">
            </div>
            <div class="chainpilot-meta-item">
              <div class="chainpilot-label">目标占用减少额</div>
              <input class="form-control" type="number" data-field="target_cash_release" value="${chainpilot.escape(scenario.target_cash_release || 170000000)}">
            </div>
            <div class="chainpilot-meta-item">
              <div class="chainpilot-label">来源会话</div>
              <input class="form-control" data-field="session_id" value="${chainpilot.escape(scenario.session_id || session.session_id || "")}">
            </div>
          </div>
          <div style="margin-top: 12px;">
            <div class="chainpilot-label">业务目标描述</div>
            <textarea class="form-control" rows="3" data-field="business_goal">${chainpilot.escape(scenario.business_goal || "在不突破安全库存和关键物料缺料阈值的前提下，减少 1.7 亿采购资金占用。")}</textarea>
          </div>
          <div class="chainpilot-detail-grid" style="margin-top: 12px;">
            <div class="chainpilot-meta-item">
              <div class="chainpilot-label">开始日期</div>
              <input class="form-control" type="date" data-field="planning_horizon_start" value="${chainpilot.escape(scenario.planning_horizon_start || "2026-06-01")}">
            </div>
            <div class="chainpilot-meta-item">
              <div class="chainpilot-label">结束日期</div>
              <input class="form-control" type="date" data-field="planning_horizon_end" value="${chainpilot.escape(scenario.planning_horizon_end || "2026-07-31")}">
            </div>
            <div class="chainpilot-meta-item">
              <div class="chainpilot-label">负责人角色</div>
              <input class="form-control" data-field="owner_role" value="${chainpilot.escape(role_label(scenario.owner_role) || "供应链负责人")}">
            </div>
          </div>
          <div style="margin-top: 12px;">
            <div class="chainpilot-label">约束条件</div>
            <input type="hidden" data-field="constraint_json" value="${chainpilot.escape(constraintJson)}">
            ${constraint_summary(constraintJson)}
          </div>
          <div style="margin-top: 14px;">
            <button class="chainpilot-link-button" data-save-scenario="1">保存草稿</button>
          </div>
        </div>

        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">SAP 快照</h2>
              <p class="chainpilot-panel-note">来自当前模拟快照；真实接入后由 SAP 只读同步更新。</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${meta_item("来源系统", chainpilot.sourceSystemLabel(session.source_system) || "-")}
            ${meta_item("采购金额基线", chainpilot.currency(session.baseline_amount))}
            ${meta_item("物料数", chainpilot.number(session.material_count || 0))}
            ${meta_item("快照日期", session.run_date || "-")}
          </div>
        </div>
      </section>

      <section class="chainpilot-panel" style="margin-top: 18px;">
        <div class="chainpilot-panel-header">
          <div>
            <h2 class="chainpilot-panel-title">方案对比</h2>
            <p class="chainpilot-panel-note">比较减少资金占用、风险等级、建议数量和推荐理由。</p>
          </div>
          <button class="chainpilot-link-button" data-route="action-inbox">查看建议</button>
        </div>
        <div class="chainpilot-scenario-list">
          ${scenarioResults.map((result) => scenario_result_card(result, data.recommendations)).join("") || empty_state("尚无方案结果。")}
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
      frappe.msgprint("约束条件格式不正确。");
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
      frappe.show_alert({ message: "已保存场景目标", indicator: "green" });
      load_scenario_studio(page);
    } catch (error) {
      frappe.msgprint("保存场景失败，请检查必填字段和权限。");
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
          <div class="chainpilot-scenario-name">${chainpilot.strategyLabel(result.strategy_name || result.strategy_type)}</div>
          <div class="chainpilot-scenario-text">${chainpilot.escape(business_text(result.ai_recommendation || ""))}</div>
        </div>
        ${metric_block("占用减少额", chainpilot.currency(result.cash_release))}
        ${metric_block("建议 / 待处理", `${chainpilot.number(result.recommendation_count || actionRows.length)} / ${chainpilot.number(pending)}`)}
        <div>
          ${metric_block("风险关注", chainpilot.number(risk))}
          <div style="margin-top: 6px;">${chainpilot.badge(chainpilot.riskLabel(result.risk_level) || "-", chainpilot.riskTone(result.risk_level))}</div>
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

  function role_label(value) {
    const labels = {
      "ChainPilot Supply Chain Director": "供应链负责人",
      "ChainPilot Planner": "计划负责人",
    };
    return labels[value] || value || "";
  }

  function constraint_summary(raw) {
    let constraints = {};
    try {
      constraints = JSON.parse(raw || "{}");
    } catch {
      constraints = {};
    }
    const writebackMode = constraints.sap_writeback_mode === "draft_only" ? "仅生成草稿" : "人工复核后执行";
    return `
      <div class="chainpilot-detail-grid">
        ${meta_item("最低库存覆盖", `${chainpilot.number(constraints.minimum_inventory_days || 28)} 天`)}
        ${meta_item("最高缺料风险", chainpilot.number(constraints.max_shortage_risk_after || 3.5, 1))}
        ${meta_item("SAP 回写方式", writebackMode)}
        ${meta_item("冻结窗口", `${chainpilot.number(constraints.freeze_window_days || 7)} 天`)}
      </div>
    `;
  }

  function business_text(value) {
    return String(value || "")
      .replaceAll("PR 数量下调", "采购申请数量下调")
      .replaceAll("PO 延期", "采购订单延期")
      .replaceAll("PR", "采购申请")
      .replaceAll("PO", "采购订单")
      .replaceAll("MVP", "首版验证")
      .replaceAll("首版验证 推荐方案", "首版验证推荐方案")
      .replaceAll("作为 首版验证推荐方案", "作为首版验证推荐方案");
  }

  function chainpilot_utils() {
    return {
      escape(value) {
        return frappe.utils.escape_html(value == null ? "" : String(value));
      },
      currency(value) {
        const amount = Number(value || 0);
        if (Math.abs(amount) >= 10000) return `${(amount / 10000).toLocaleString(undefined, { maximumFractionDigits: 1 })} 万元`;
        return `${amount.toLocaleString(undefined, { maximumFractionDigits: 0 })} 元`;
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
      statusLabel(value) {
        const labels = { Draft: "草稿", Generated: "已生成", Approved: "已批准", Pending: "待处理" };
        return labels[value] || value || "";
      },
      riskLabel(risk) {
        const labels = { High: "高", Medium: "中", Low: "低", Critical: "严重" };
        return labels[risk] || risk || "";
      },
      strategyLabel(strategy) {
        const labels = { Recommended: "推荐方案", Conservative: "稳妥方案", Aggressive: "进取方案", "Agent 推荐方案": "智能推荐方案", "AI 推荐方案": "智能推荐方案", "Recommended Plan": "推荐方案", "Conservative Plan": "稳妥方案", "Aggressive Plan": "进取方案" };
        return labels[strategy] || strategy || "";
      },
      sourceSystemLabel(sourceSystem) {
        const labels = { SAP_MOCK: "SAP 模拟快照", AIPLAN_DB: "采购分析报告导入", SAP: "SAP" };
        return labels[sourceSystem] || sourceSystem || "";
      },
      riskTone(risk) {
        if (risk === "High") return "red";
        if (risk === "Medium") return "amber";
        return "green";
      },
    };
  }
})();
