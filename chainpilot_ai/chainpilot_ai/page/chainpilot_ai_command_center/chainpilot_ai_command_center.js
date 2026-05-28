(() => {
  const chainpilot = window.chainpilot || (window.chainpilot = chainpilot_utils());

  frappe.pages["chainpilot-ai-command-center"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
      parent: wrapper,
      title: __("ChainPilot AI Command Center"),
      single_column: true,
    });

    page.set_primary_action(__("打开动作收件箱"), () => frappe.set_route("action-inbox"));
    page.set_secondary_action(__("方案工作台"), () => frappe.set_route("scenario-studio"));
    page.add_inner_button(__("AI Copilot"), () => frappe.set_route("ai-copilot"));
    page.add_inner_button(__("SAP 集成台"), () => frappe.set_route("sap-integration-console"));
    page.main.html(`<div class="chainpilot-shell"><div class="chainpilot-loading">${__("正在加载 ChainPilot 决策台...")}</div></div>`);
    load_command_center(page);
  };

  async function load_command_center(page) {
    try {
      const [sessions, scenarios, recommendations, evidence, checks] = await Promise.all([
        frappe.db.get_list("Optimization Session", {
          fields: ["session_id", "source_system", "source_report", "baseline_amount", "material_count", "sample_count", "best_solution_count", "run_date", "status"],
          limit: 1,
          order_by: "run_date desc",
        }),
        frappe.db.get_list("Scenario Result", {
          fields: ["result_id", "strategy_name", "strategy_type", "purchase_amount", "cash_release", "cash_release_rate", "risk_level", "recommendation_count", "ai_recommendation"],
          limit: 20,
          order_by: "cash_release desc",
        }),
        frappe.db.get_list("Recommendation", {
          fields: ["name", "recommendation_id", "result_id", "action_type", "sap_object_type", "sap_doc_no", "sap_item_no", "material_code", "material_name", "plant", "supplier", "product_line", "before_qty", "after_qty", "before_date", "after_date", "cash_release", "saving_type", "inventory_days_after", "shortage_risk_after", "confidence_score", "approval_status", "explanation_status"],
          limit: 100,
          order_by: "cash_release desc",
        }),
        frappe.db.get_list("Recommendation Evidence", {
          fields: ["recommendation_id", "verdict"],
          limit: 500,
        }),
        frappe.db.get_list("Constraint Check Result", {
          fields: ["recommendation_id", "verdict", "rule_code", "message"],
          limit: 500,
        }),
      ]);

      render_command_center(page, {
        session: sessions[0] || {},
        scenarios,
        recommendations,
        evidence,
        checks,
      });
    } catch (error) {
      page.main.find(".chainpilot-shell").html(`<div class="chainpilot-empty">${__("无法加载 ChainPilot 决策台数据。")}</div>`);
      console.error(error);
    }
  }

  function render_command_center(page, data) {
    const { session, recommendations, evidence, checks } = data;
    const scenarioRank = { Recommended: 0, Aggressive: 1, Conservative: 2 };
    const scenarios = [...data.scenarios].sort((a, b) => (scenarioRank[a.strategy_type] ?? 9) - (scenarioRank[b.strategy_type] ?? 9));
    const recommended = scenarios.find((item) => item.strategy_type === "Recommended") || scenarios[0] || {};
    const totalCash = recommendations.reduce((sum, item) => sum + Number(item.cash_release || 0), 0);
    const pending = recommendations.filter((item) => item.approval_status === "Pending");
    const approvalRequired = checks.filter((item) => item.verdict === "PASS_WITH_APPROVAL").length;
    const riskActions = recommendations.filter((item) => Number(item.shortage_risk_after || 0) >= 2.5);
    const warnEvidence = evidence.filter((item) => item.verdict === "WARN").length;
    const baseline = Number(session.baseline_amount || 0);
    const releaseValue = Number(recommended.cash_release || totalCash);
    const releaseRate = baseline ? (releaseValue / baseline) * 100 : 0;

    page.main.find(".chainpilot-shell").html(`
      <section class="chainpilot-hero">
        <div>
          <div class="chainpilot-eyebrow">${__("SAP 报告到动作驾驶舱")}</div>
          <h1 class="chainpilot-title">${__("5月采购优化决策台")}</h1>
          <p class="chainpilot-subtitle">
            ${__("把导入的 SAP 优化结果转成方案选择、单据行级动作、证据约束和可审批的业务队列。当前运行在 mock/demo 数据层，后续可替换为 SAP 只读接口。")}
          </p>
        </div>
        <div class="chainpilot-meta-grid">
          ${meta_item(__("来源系统"), session.source_system || "-")}
          ${meta_item(__("运行日期"), session.run_date || "-")}
          ${meta_item(__("物料数"), chainpilot.number(session.material_count || 0))}
          ${meta_item(__("最优解数"), chainpilot.number(session.best_solution_count || 0))}
        </div>
      </section>

      <section class="chainpilot-kpi-grid">
        ${kpi_card(__("采购基线"), chainpilot.currency(session.baseline_amount), __("导入 SAP 采购金额基线"))}
        ${kpi_card(__("推荐释放现金"), chainpilot.currency(releaseValue), `${chainpilot.percent(releaseRate)} ${__("占基线比例")}`)}
        ${kpi_card(__("待审批动作"), chainpilot.number(pending.length), __("等待业务复核的建议动作"))}
        ${kpi_card(__("风险关注"), chainpilot.number(riskActions.length + warnEvidence + approvalRequired), __("需要升级复核的动作、证据或约束"))}
      </section>

      <section class="chainpilot-grid-2">
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">${__("方案组合")}</h2>
              <p class="chainpilot-panel-note">${__("对比导入优化结果中的保守、推荐和激进方案。")}</p>
            </div>
            <button class="chainpilot-link-button" data-route="scenario-studio">${__("打开方案工作台")}</button>
          </div>
          <div class="chainpilot-scenario-list">
            ${scenarios.map(scenario_card).join("") || empty_state(__("No scenarios imported."))}
          </div>
        </div>

        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">${__("管控异常")}</h2>
              <p class="chainpilot-panel-note">${__("创建 SAP 回写草稿前必须复核的审批和风险事项。")}</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${control_rows(riskActions, checks)}
          </div>
        </div>
      </section>

      <section class="chainpilot-panel" style="margin-top: 18px;">
        <div class="chainpilot-panel-header">
          <div>
            <h2 class="chainpilot-panel-title">${__("高价值动作")}</h2>
            <p class="chainpilot-panel-note">${__("按释放现金排序的单据行级 SAP 建议。")}</p>
          </div>
          <button class="chainpilot-link-button" data-route="action-inbox">${__("查看队列")}</button>
        </div>
        <div class="chainpilot-action-list">
          ${recommendations.slice(0, 5).map(action_card).join("") || empty_state(__("No actions imported."))}
        </div>
      </section>
    `);

    page.main.find("[data-route='action-inbox']").on("click", () => frappe.set_route("action-inbox"));
    page.main.find("[data-route='scenario-studio']").on("click", () => frappe.set_route("scenario-studio"));
    page.main.find("[data-recommendation]").on("click", function () {
      frappe.set_route("Form", "Recommendation", $(this).data("recommendation"));
    });
  }

  function meta_item(label, value) {
    return `<div class="chainpilot-meta-item"><div class="chainpilot-label">${chainpilot.escape(label)}</div><div class="chainpilot-value">${chainpilot.escape(value)}</div></div>`;
  }

  function kpi_card(label, value, note) {
    return `<div class="chainpilot-kpi"><div class="chainpilot-label">${chainpilot.escape(label)}</div><strong>${chainpilot.escape(value)}</strong><span>${chainpilot.escape(note)}</span></div>`;
  }

  function scenario_card(scenario) {
    const recommended = scenario.strategy_type === "Recommended";
    return `
      <div class="chainpilot-scenario ${recommended ? "is-recommended" : ""}">
        <div>
          <div class="chainpilot-scenario-name">${chainpilot.escape(scenario.strategy_name)}</div>
          <div class="chainpilot-scenario-text">${chainpilot.escape(scenario.ai_recommendation || "")}</div>
        </div>
        ${metric_block(__("采购金额"), chainpilot.currency(scenario.purchase_amount))}
        ${metric_block(__("释放现金"), chainpilot.currency(scenario.cash_release))}
        <div>
          ${metric_block(__("释放比例"), chainpilot.percent(scenario.cash_release_rate || 0))}
          <div style="margin-top: 6px;">${chainpilot.badge(scenario.risk_level || "-", chainpilot.riskTone(scenario.risk_level))}</div>
        </div>
      </div>
    `;
  }

  function metric_block(label, value) {
    return `<div><div class="chainpilot-metric">${chainpilot.escape(value)}</div><div class="chainpilot-metric-label">${chainpilot.escape(label)}</div></div>`;
  }

  function control_rows(riskActions, checks) {
    const approvalChecks = checks.filter((item) => item.verdict === "PASS_WITH_APPROVAL").slice(0, 4);
    const rows = [
      ...riskActions.slice(0, 3).map((item) => ({
        label: item.recommendation_id,
        note: `${chainpilot.actionLabel(item.action_type)} · ${item.material_name || item.material_code}`,
        badge: chainpilot.badge(__("风险 ") + chainpilot.number(item.shortage_risk_after, 1), "amber"),
        name: item.name,
      })),
      ...approvalChecks.map((item) => ({
        label: item.rule_code,
        note: item.message,
        badge: chainpilot.badge(__("需审批"), "blue"),
        name: item.recommendation_id,
      })),
    ];
    if (!rows.length) return empty_state(__("No elevated risk or approval exception found."));
    return rows
      .slice(0, 6)
      .map(
        (row) => `
          <div class="chainpilot-risk-row">
            <div>
              <div class="chainpilot-action-title">${chainpilot.escape(row.label)}</div>
              <div class="chainpilot-action-subtitle">${chainpilot.escape(row.note)}</div>
            </div>
            <button class="chainpilot-link-button" data-recommendation="${chainpilot.escape(row.name)}">${__("打开")}</button>
          </div>
        `,
      )
      .join("");
  }

  function action_card(item) {
    return `
      <div class="chainpilot-action-card">
        <div class="chainpilot-action-main">
          <div class="chainpilot-action-id">${chainpilot.escape(item.recommendation_id)}</div>
          <div class="chainpilot-action-title">${chainpilot.actionLabel(item.action_type)} · ${chainpilot.escape(item.material_name || item.material_code)}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(item.sap_object_type)} ${chainpilot.escape(item.sap_doc_no)}/${chainpilot.escape(item.sap_item_no)} · ${chainpilot.escape(item.plant)} · ${chainpilot.escape(item.supplier || "-")}</div>
          <div class="chainpilot-change-line">
            <span>${__("数量")}: ${chainpilot.number(item.before_qty)} -> ${chainpilot.number(item.after_qty)}</span>
            <span>${__("日期")}: ${chainpilot.escape(item.before_date || "-")} -> ${chainpilot.escape(item.after_date || "-")}</span>
          </div>
        </div>
        ${metric_block(__("释放现金"), chainpilot.currency(item.cash_release))}
        <div>
          ${chainpilot.badge(item.approval_status, chainpilot.verdictTone(item.approval_status))}
          ${chainpilot.badge(item.explanation_status, chainpilot.verdictTone(item.explanation_status))}
        </div>
        <button class="chainpilot-link-button" data-recommendation="${chainpilot.escape(item.name)}">${__("查看详情")}</button>
      </div>
    `;
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
      verdictTone(verdict) {
        if (["BLOCK", "BLOCKED", "Failed", "Rejected"].includes(verdict)) return "red";
        if (["WARN", "PASS_WITH_APPROVAL", "Pending"].includes(verdict)) return "amber";
        if (["PASS", "Approved", "Ready"].includes(verdict)) return "green";
        return "neutral";
      },
      actionLabel(actionType) {
        const labels = {
          REDUCE_PR_QTY: __("下调 PR 数量"),
          DELAY_UNCONFIRMED_PO: __("延后未确认 PO"),
          ADVANCE_RISK_MATERIAL: __("提前风险物料"),
          REVIEW_SAFETY_STOCK: __("复核安全库存"),
          REVIEW_SUPPLIER_LEAD_TIME: __("复核供应商交期"),
        };
        return labels[actionType] || actionType || "";
      },
    };
  }
})();
