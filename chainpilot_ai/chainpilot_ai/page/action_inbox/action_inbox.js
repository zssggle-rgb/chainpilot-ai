(() => {
  const chainpilot = window.chainpilot || (window.chainpilot = chainpilot_utils());

  frappe.pages["action-inbox"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
      parent: wrapper,
      title: __("Action Inbox"),
      single_column: true,
    });

    page.set_primary_action(__("返回决策台"), () => frappe.set_route("chainpilot-ai-command-center"));
    page.set_secondary_action(__("建议清单"), () => frappe.set_route("List", "Recommendation"));
    page.main.html(`<div class="chainpilot-shell"><div class="chainpilot-loading">${__("正在加载建议动作...")}</div></div>`);
    load_action_inbox(page);
  };

  async function load_action_inbox(page) {
    try {
      const [recommendations, evidence, checks] = await Promise.all([
        frappe.db.get_list("Recommendation", {
          fields: ["name", "recommendation_id", "result_id", "action_type", "sap_object_type", "sap_doc_no", "sap_item_no", "material_code", "material_name", "plant", "supplier", "purchasing_group", "product_line", "before_qty", "after_qty", "before_date", "after_date", "cash_release", "saving_type", "inventory_days_before", "inventory_days_after", "shortage_risk_before", "shortage_risk_after", "confidence_score", "approval_status", "writeback_status", "explanation_status"],
          limit: 100,
          order_by: "cash_release desc",
        }),
        frappe.db.get_list("Recommendation Evidence", {
          fields: ["recommendation_id", "verdict", "summary"],
          limit: 500,
        }),
        frappe.db.get_list("Constraint Check Result", {
          fields: ["recommendation_id", "verdict", "rule_code", "message"],
          limit: 500,
        }),
      ]);

      const state = {
        recommendations,
        evidenceByRecommendation: group_by(evidence, "recommendation_id"),
        checksByRecommendation: group_by(checks, "recommendation_id"),
        filter: "all",
      };
      render_action_inbox(page, state);
    } catch (error) {
      page.main.find(".chainpilot-shell").html(`<div class="chainpilot-empty">${__("无法加载建议动作。")}</div>`);
      console.error(error);
    }
  }

  function render_action_inbox(page, state) {
    const totalCash = state.recommendations.reduce((sum, item) => sum + Number(item.cash_release || 0), 0);
    const elevated = state.recommendations.filter((item) => needs_review(item, state.checksByRecommendation[item.recommendation_id] || []));
    const filtered = filter_recommendations(state);

    page.main.find(".chainpilot-shell").html(`
      <section class="chainpilot-hero">
        <div>
          <div class="chainpilot-eyebrow">${__("动作队列")}</div>
          <h1 class="chainpilot-title">${__("推荐动作收件箱")}</h1>
          <p class="chainpilot-subtitle">
            ${__("在创建回写草稿前，按金额、缺料风险、审批要求和证据状态处理单据行级 SAP 动作。")}
          </p>
        </div>
        <div class="chainpilot-meta-grid">
          ${meta_item(__("动作数"), chainpilot.number(state.recommendations.length))}
          ${meta_item(__("待处理"), chainpilot.number(state.recommendations.filter((item) => item.approval_status === "Pending").length))}
          ${meta_item(__("升级复核"), chainpilot.number(elevated.length))}
          ${meta_item(__("释放现金"), chainpilot.currency(totalCash))}
        </div>
      </section>

      <div class="chainpilot-actions-toolbar">
        <div class="chainpilot-filter-group">
          ${filter_button("all", __("全部动作"), state.filter)}
          ${filter_button("cash", __("释放现金"), state.filter)}
          ${filter_button("approval", __("需审批"), state.filter)}
          ${filter_button("risk", __("风险关注"), state.filter)}
          ${filter_button("master", __("主数据复核"), state.filter)}
        </div>
        <button class="chainpilot-filter" data-refresh="1">${__("刷新")}</button>
      </div>

      <section class="chainpilot-action-list">
        ${filtered.map((item) => inbox_card(item, state)).join("") || empty_state(__("没有匹配当前筛选条件的动作。"))}
      </section>
    `);

    page.main.find("[data-filter]").on("click", function () {
      state.filter = $(this).data("filter");
      render_action_inbox(page, state);
    });
    page.main.find("[data-refresh]").on("click", () => load_action_inbox(page));
    page.main.find("[data-recommendation]").on("click", function () {
      frappe.set_route("Form", "Recommendation", $(this).data("recommendation"));
    });
  }

  function group_by(rows, key) {
    return rows.reduce((groups, row) => {
      const value = row[key];
      groups[value] = groups[value] || [];
      groups[value].push(row);
      return groups;
    }, {});
  }

  function filter_button(id, label, active) {
    return `<button class="chainpilot-filter ${active === id ? "active" : ""}" data-filter="${id}">${chainpilot.escape(label)}</button>`;
  }

  function filter_recommendations(state) {
    const rows = state.recommendations;
    if (state.filter === "cash") return rows.filter((item) => Number(item.cash_release || 0) > 0);
    if (state.filter === "approval") {
      return rows.filter((item) => (state.checksByRecommendation[item.recommendation_id] || []).some((check) => check.verdict === "PASS_WITH_APPROVAL"));
    }
    if (state.filter === "risk") {
      return rows.filter((item) => needs_review(item, state.checksByRecommendation[item.recommendation_id] || []));
    }
    if (state.filter === "master") return rows.filter((item) => item.action_type === "REVIEW_SAFETY_STOCK" || item.action_type === "REVIEW_SUPPLIER_LEAD_TIME");
    return rows;
  }

  function needs_review(item, checks) {
    return Number(item.shortage_risk_after || 0) >= 2.5 || checks.some((check) => check.verdict === "PASS_WITH_APPROVAL" || check.verdict === "BLOCKED");
  }

  function inbox_card(item, state) {
    const checks = state.checksByRecommendation[item.recommendation_id] || [];
    const evidence = state.evidenceByRecommendation[item.recommendation_id] || [];
    const primaryCheck = checks[0] || {};
    const primaryEvidence = evidence[0] || {};
    return `
      <article class="chainpilot-action-card">
        <div class="chainpilot-action-main">
          <div class="chainpilot-action-id">${chainpilot.escape(item.recommendation_id)} · ${chainpilot.escape(item.product_line || "-")}</div>
          <div class="chainpilot-action-title">${chainpilot.actionLabel(item.action_type)} · ${chainpilot.escape(item.material_name || item.material_code)}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(item.sap_object_type)} ${chainpilot.escape(item.sap_doc_no)}/${chainpilot.escape(item.sap_item_no)} · ${chainpilot.escape(item.plant)} · ${chainpilot.escape(item.supplier || "-")} · ${chainpilot.escape(item.purchasing_group || "-")}</div>
          <div class="chainpilot-change-line">
            <span>${__("数量")}: ${chainpilot.number(item.before_qty)} -> ${chainpilot.number(item.after_qty)}</span>
            <span>${__("日期")}: ${chainpilot.escape(item.before_date || "-")} -> ${chainpilot.escape(item.after_date || "-")}</span>
            <span>${__("库存覆盖")}: ${chainpilot.number(item.inventory_days_before, 1)} -> ${chainpilot.number(item.inventory_days_after, 1)} ${__("天")}</span>
          </div>
        </div>
        <div>
          ${metric_block(__("释放现金"), chainpilot.currency(item.cash_release))}
          <div style="margin-top: 7px;">${chainpilot.badge(item.saving_type || "-", "blue")}</div>
        </div>
        <div>
          ${metric_block(__("调整后风险"), chainpilot.number(item.shortage_risk_after, 1))}
          <div style="margin-top: 7px;">${chainpilot.badge(primaryCheck.verdict || __("无约束"), chainpilot.verdictTone(primaryCheck.verdict))}</div>
          <div style="margin-top: 6px;">${chainpilot.badge(primaryEvidence.verdict || __("无证据"), chainpilot.verdictTone(primaryEvidence.verdict))}</div>
        </div>
        <button class="chainpilot-link-button" data-recommendation="${chainpilot.escape(item.name)}">${__("查看详情")}</button>
      </article>
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
