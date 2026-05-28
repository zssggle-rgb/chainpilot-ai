(() => {
  const chainpilot = window.chainpilot || (window.chainpilot = chainpilot_utils());

  frappe.pages["action-inbox"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
      parent: wrapper,
      title: "采购建议",
      single_column: true,
    });

    page.set_primary_action("返回", () => frappe.set_route("chainpilot-ai-command-center"));
    page.set_secondary_action("SAP 连接", () => frappe.set_route("sap-integration-console"));
    page.add_inner_button("监控", () => frappe.set_route("execution-monitor"));
    page.add_inner_button("学习", () => frappe.set_route("learning-center"));
    page.main.html(`<div class="chainpilot-shell"><div class="chainpilot-loading">正在加载采购建议...</div></div>`);
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
      page.main.find(".chainpilot-shell").html(`<div class="chainpilot-empty">无法加载建议数据。</div>`);
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
          <div class="chainpilot-eyebrow">采购优化</div>
          <h1 class="chainpilot-title">采购建议</h1>
          <p class="chainpilot-subtitle">
            集中查看采购建议、风险等级和资金占用影响。
          </p>
        </div>
        <div class="chainpilot-meta-grid">
          ${meta_item("建议总数", chainpilot.number(state.recommendations.length))}
          ${meta_item("待处理建议", chainpilot.number(state.recommendations.filter((item) => item.approval_status === "Pending").length))}
          ${meta_item("待复核建议", chainpilot.number(elevated.length))}
          ${meta_item("资金占用减少额", chainpilot.currency(totalCash))}
        </div>
      </section>

      <div class="chainpilot-actions-toolbar">
        <div class="chainpilot-filter-group">
          ${filter_button("all", "全部", state.filter)}
          ${filter_button("cash", "占用减少", state.filter)}
          ${filter_button("approval", "待审批", state.filter)}
          ${filter_button("risk", "风险关注", state.filter)}
          ${filter_button("master", "主数据", state.filter)}
        </div>
        <button class="chainpilot-filter" data-refresh="1">刷新</button>
      </div>

      <section class="chainpilot-action-list">
        ${filtered.map((item) => inbox_card(item, state)).join("") || empty_state("没有匹配当前筛选条件的建议。")}
      </section>
    `);

    page.main.find("[data-filter]").on("click", function () {
      state.filter = $(this).data("filter");
      render_action_inbox(page, state);
    });
    page.main.find("[data-refresh]").on("click", () => load_action_inbox(page));
    page.main.find("[data-detail-id]").on("click", function () {
      const recommendationId = $(this).data("detail-id");
      const item = state.recommendations.find((row) => row.recommendation_id === recommendationId);
      if (!item) return;
      frappe.msgprint({
        title: "建议详情",
        message: detail_message(item, state.checksByRecommendation[recommendationId] || [], state.evidenceByRecommendation[recommendationId] || []),
        wide: true,
      });
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
          <div class="chainpilot-action-id">${chainpilot.escape(chainpilot.recommendationLabel(item.recommendation_id))} · ${chainpilot.escape(item.product_line || "-")}</div>
          <div class="chainpilot-action-title">${chainpilot.actionLabel(item.action_type)} · ${chainpilot.escape(item.material_name || item.material_code)}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.sapObjectLabel(item.sap_object_type)} ${chainpilot.escape(item.sap_doc_no)}/${chainpilot.escape(item.sap_item_no)} · ${chainpilot.escape(item.plant)} · ${chainpilot.escape(item.supplier || "-")} · ${chainpilot.escape(item.purchasing_group || "-")}</div>
          <div class="chainpilot-change-line">
            <span>数量：${chainpilot.number(item.before_qty)} → ${chainpilot.number(item.after_qty)}</span>
            <span>日期：${chainpilot.escape(item.before_date || "-")} → ${chainpilot.escape(item.after_date || "-")}</span>
            <span>库存覆盖：${chainpilot.number(item.inventory_days_before, 1)} → ${chainpilot.number(item.inventory_days_after, 1)} 天</span>
          </div>
        </div>
        <div>
          ${metric_block("资金占用减少额", chainpilot.currency(item.cash_release))}
          <div style="margin-top: 7px;">${chainpilot.badge(chainpilot.savingTypeLabel(item.saving_type), "blue")}</div>
        </div>
        <div>
          ${metric_block("调整后缺料风险", chainpilot.number(item.shortage_risk_after, 1))}
          <div style="margin-top: 7px;">${chainpilot.badge(chainpilot.statusLabel(primaryCheck.verdict) || "无约束", chainpilot.verdictTone(primaryCheck.verdict))}</div>
          <div style="margin-top: 6px;">${chainpilot.badge(chainpilot.statusLabel(primaryEvidence.verdict) || "无证据", chainpilot.verdictTone(primaryEvidence.verdict))}</div>
        </div>
        <button class="chainpilot-link-button" data-detail-id="${chainpilot.escape(item.recommendation_id)}">查看详情</button>
      </article>
    `;
  }

  function detail_message(item, checks, evidence) {
    const primaryCheck = checks[0] || {};
    const primaryEvidence = evidence[0] || {};
    return `
      <div class="chainpilot-detail-grid">
        ${meta_item("建议编号", chainpilot.recommendationLabel(item.recommendation_id))}
        ${meta_item("建议类型", chainpilot.actionLabel(item.action_type))}
        ${meta_item("SAP 单据", `${chainpilot.sapObjectLabel(item.sap_object_type)} ${item.sap_doc_no}/${item.sap_item_no}`)}
        ${meta_item("资金占用减少额", chainpilot.currency(item.cash_release))}
        ${meta_item("审批状态", chainpilot.statusLabel(item.approval_status))}
        ${meta_item("证据状态", chainpilot.statusLabel(primaryEvidence.verdict) || "无证据")}
        ${meta_item("约束结果", chainpilot.statusLabel(primaryCheck.verdict) || "无约束")}
        ${meta_item("调整后库存覆盖", `${chainpilot.number(item.inventory_days_after, 1)} 天`)}
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
      riskTone(risk) {
        if (risk === "High") return "red";
        if (risk === "Medium") return "amber";
        return "green";
      },
      verdictTone(verdict) {
        if (["BLOCK", "BLOCKED", "Failed", "Rejected", "Conflict"].includes(verdict)) return "red";
        if (["WARN", "PASS_WITH_APPROVAL", "Pending", "Draft", "Draft Ready"].includes(verdict)) return "amber";
        if (["PASS", "Approved", "Ready", "Success", "Executed", "Match"].includes(verdict)) return "green";
        return "neutral";
      },
      statusLabel(value) {
        const labels = {
          Pending: "待处理",
          Approved: "已批准",
          Rejected: "已拒绝",
          Ready: "已就绪",
          Failed: "失败",
          PASS: "通过",
          WARN: "需关注",
          PASS_WITH_APPROVAL: "需审批",
          BLOCKED: "已阻断",
          BLOCK: "已阻断",
        };
        return labels[value] || value || "";
      },
      savingTypeLabel(savingType) {
        const labels = {
          "Cash Release": "减少采购占用",
          "Book Saving": "账面节省",
          "Purchase Deferral": "采购延期",
        };
        return labels[savingType] || savingType || "";
      },
      sapObjectLabel(objectType) {
        const labels = { PR: "采购申请", PO: "采购订单", MRP_PARAM: "MRP 参数", PLANNED_ORDER: "计划订单" };
        return labels[objectType] || objectType || "";
      },
      recommendationLabel(recommendationId) {
        const value = String(recommendationId || "");
        return value ? `建议 ${value.replace(/^REC-/, "")}` : "";
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
