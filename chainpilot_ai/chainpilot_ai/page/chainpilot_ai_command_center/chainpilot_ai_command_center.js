(() => {
  const chainpilot = window.chainpilot || (window.chainpilot = chainpilot_utils());

  frappe.pages["chainpilot-ai-command-center"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
      parent: wrapper,
      title: "采购决策",
      single_column: true,
    });

    page.set_primary_action("查看建议", () => frappe.set_route("action-inbox"));
    page.set_secondary_action("SAP 连接", () => frappe.set_route("sap-integration-console"));
    page.add_inner_button("方案", () => frappe.set_route("scenario-studio"));
    page.add_inner_button("智能", () => frappe.set_route("ai-copilot"));
    page.add_inner_button("监控", () => frappe.set_route("execution-monitor"));
    page.add_inner_button("学习", () => frappe.set_route("learning-center"));
    page.main.html(`<div class="chainpilot-shell"><div class="chainpilot-loading">正在加载采购决策...</div></div>`);
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
      page.main.find(".chainpilot-shell").html(`<div class="chainpilot-empty">无法加载采购决策数据。</div>`);
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
          <div class="chainpilot-eyebrow">采购优化</div>
          <h1 class="chainpilot-title">5月采购优化</h1>
          <p class="chainpilot-subtitle">
            查看优化方案、待处理建议、风险事项和资金占用影响。
          </p>
        </div>
        <div class="chainpilot-meta-grid">
          ${meta_item("来源系统", chainpilot.sourceSystemLabel(session.source_system) || "-")}
          ${meta_item("运行日期", session.run_date || "-")}
          ${meta_item("物料数", chainpilot.number(session.material_count || 0))}
          ${meta_item("候选方案", chainpilot.number(session.best_solution_count || 0))}
        </div>
      </section>

      <section class="chainpilot-kpi-grid">
        ${kpi_card("采购金额基线", chainpilot.currency(session.baseline_amount), "导入数据中的采购金额")}
        ${kpi_card("资金占用减少额", chainpilot.currency(releaseValue), `${chainpilot.percent(releaseRate)} 占基线比例`)}
        ${kpi_card("待审批建议", chainpilot.number(pending.length), "等待业务复核")}
        ${kpi_card("需关注事项", chainpilot.number(riskActions.length + warnEvidence + approvalRequired), "风险、证据或审批提示")}
      </section>

      <section class="chainpilot-grid-2">
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">方案组合</h2>
              <p class="chainpilot-panel-note">对比稳妥、推荐和进取方案。</p>
            </div>
            <button class="chainpilot-link-button" data-route="scenario-studio">查看方案</button>
          </div>
          <div class="chainpilot-scenario-list">
            ${scenarios.map(scenario_card).join("") || empty_state("尚未导入方案。")}
          </div>
        </div>

        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">需关注事项</h2>
              <p class="chainpilot-panel-note">高风险、缺证据或需要审批的建议。</p>
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
            <h2 class="chainpilot-panel-title">高价值建议</h2>
            <p class="chainpilot-panel-note">按资金占用减少额排序。</p>
          </div>
          <button class="chainpilot-link-button" data-route="action-inbox">查看建议</button>
        </div>
        <div class="chainpilot-action-list">
          ${recommendations.slice(0, 5).map(action_card).join("") || empty_state("尚未导入建议。")}
        </div>
      </section>
    `);

    page.main.find("[data-route='action-inbox']").on("click", () => frappe.set_route("action-inbox"));
    page.main.find("[data-route='scenario-studio']").on("click", () => frappe.set_route("scenario-studio"));
    page.main.find("[data-recommendation]").on("click", () => frappe.set_route("action-inbox"));
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
          <div class="chainpilot-scenario-name">${chainpilot.strategyLabel(scenario.strategy_name || scenario.strategy_type)}</div>
          <div class="chainpilot-scenario-text">${chainpilot.escape(business_text(scenario.ai_recommendation || ""))}</div>
        </div>
        ${metric_block("采购金额", chainpilot.currency(scenario.purchase_amount))}
        ${metric_block("资金占用减少额", chainpilot.currency(scenario.cash_release))}
        <div>
          ${metric_block("改善比例", chainpilot.percent(scenario.cash_release_rate || 0))}
          <div style="margin-top: 6px;">${chainpilot.badge(chainpilot.riskLabel(scenario.risk_level) || "-", chainpilot.riskTone(scenario.risk_level))}</div>
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
        label: chainpilot.recommendationLabel(item.recommendation_id),
        note: `${chainpilot.actionLabel(item.action_type)} · ${item.material_name || item.material_code}`,
        badge: chainpilot.badge(`风险 ${chainpilot.number(item.shortage_risk_after, 1)}`, "amber"),
        name: item.name,
      })),
      ...approvalChecks.map((item) => ({
        label: rule_label(item.rule_code),
        note: business_text(item.message),
        badge: chainpilot.badge("需审批", "blue"),
        name: item.recommendation_id,
      })),
    ];
    if (!rows.length) return empty_state("暂无高风险或审批提示。");
    return rows
      .slice(0, 6)
      .map(
        (row) => `
          <div class="chainpilot-risk-row">
            <div>
              <div class="chainpilot-action-title">${chainpilot.escape(row.label)}</div>
              <div class="chainpilot-action-subtitle">${chainpilot.escape(row.note)}</div>
            </div>
            <button class="chainpilot-link-button" data-recommendation="${chainpilot.escape(row.name)}">处理</button>
          </div>
        `,
      )
      .join("");
  }

  function action_card(item) {
    return `
      <div class="chainpilot-action-card">
        <div class="chainpilot-action-main">
          <div class="chainpilot-action-id">${chainpilot.escape(chainpilot.recommendationLabel(item.recommendation_id))}</div>
          <div class="chainpilot-action-title">${chainpilot.actionLabel(item.action_type)} · ${chainpilot.escape(item.material_name || item.material_code)}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.sapObjectLabel(item.sap_object_type)} ${chainpilot.escape(item.sap_doc_no)}/${chainpilot.escape(item.sap_item_no)} · ${chainpilot.escape(item.plant)} · ${chainpilot.escape(item.supplier || "-")}</div>
          <div class="chainpilot-change-line">
            <span>数量：${chainpilot.number(item.before_qty)} → ${chainpilot.number(item.after_qty)}</span>
            <span>日期：${chainpilot.escape(item.before_date || "-")} → ${chainpilot.escape(item.after_date || "-")}</span>
          </div>
        </div>
        ${metric_block("资金占用减少额", chainpilot.currency(item.cash_release))}
        <div>
          ${chainpilot.badge(chainpilot.statusLabel(item.approval_status), chainpilot.verdictTone(item.approval_status))}
          ${chainpilot.badge(chainpilot.statusLabel(item.explanation_status), chainpilot.verdictTone(item.explanation_status))}
        </div>
        <button class="chainpilot-link-button" data-recommendation="${chainpilot.escape(item.name)}">查看详情</button>
      </div>
    `;
  }

  function rule_label(value) {
    const labels = {
      MASTER_DATA_REVIEW: "主数据复核",
      SUPPLIER_CONFIRMATION: "供应商确认",
      RISK_LIMIT: "风险阈值",
      M3_SAFE_STOCK: "安全库存校验",
    };
    return labels[value] || value || "";
  }

  function business_text(value) {
    return String(value || "")
      .replaceAll("PR 数量下调", "采购申请数量下调")
      .replaceAll("PO 延期", "采购订单延期")
      .replaceAll("PR", "采购申请")
      .replaceAll("PO", "采购订单")
      .replaceAll("MVP", "首版验证")
      .replaceAll("首版验证 推荐方案", "首版验证推荐方案")
      .replaceAll("作为 首版验证推荐方案", "作为首版验证推荐方案")
      .replaceAll("SAP writeback", "SAP 回写")
      .replaceAll("draft-only", "仅生成草稿");
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
        const labels = { Pending: "待处理", Approved: "已批准", Rejected: "已拒绝", Ready: "已就绪", Failed: "失败" };
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
      sapObjectLabel(objectType) {
        const labels = { PR: "采购申请", PO: "采购订单", MRP_PARAM: "MRP 参数", PLANNED_ORDER: "计划订单" };
        return labels[objectType] || objectType || "";
      },
      recommendationLabel(recommendationId) {
        const value = String(recommendationId || "");
        return value ? `建议 ${value.replace(/^REC-/, "")}` : "";
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
          REDUCE_PR_QTY: "下调采购申请数量",
          DELAY_UNCONFIRMED_PO: "延后未确认采购订单",
          ADVANCE_RISK_MATERIAL: "提前风险物料采购",
          REVIEW_SAFETY_STOCK: "复核安全库存",
          REVIEW_SUPPLIER_LEAD_TIME: "复核供应商交期",
        };
        return labels[actionType] || actionType || "";
      },
    };
  }
})();
