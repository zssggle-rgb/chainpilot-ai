(() => {
  const chainpilot = window.chainpilot || (window.chainpilot = chainpilot_utils());

  frappe.ui.form.on("Recommendation", {
    refresh(frm) {
      if (frm.is_new()) return;
      $(frm.wrapper).addClass("chainpilot-product-form");

      frm.page.set_primary_action(__("返回动作收件箱"), () => frappe.set_route("action-inbox"));
      if (frm.doc.result_id) {
        frm.add_custom_button(__("打开方案"), () => frappe.set_route("Form", "Scenario Result", frm.doc.result_id));
      }
      frm.add_custom_button(__("进入执行监控"), () => frappe.set_route("execution-monitor"));

      render_recommendation_detail(frm);
    },
  });

  async function render_recommendation_detail(frm) {
    const target = ensure_detail_panel(frm);
    target.html(`<div class="chainpilot-loading">${__("正在加载决策证据...")}</div>`);

    try {
      const [evidence, checks, scenario, aiPanel] = await Promise.all([
        frappe.db.get_list("Recommendation Evidence", {
          fields: ["evidence_id", "source_type", "source_id", "metric_name", "metric_value", "threshold_value", "verdict", "summary"],
          filters: { recommendation_id: frm.doc.name },
          limit: 20,
        }),
        frappe.db.get_list("Constraint Check Result", {
          fields: ["check_id", "rule_code", "verdict", "message", "evidence_id"],
          filters: { recommendation_id: frm.doc.name },
          limit: 20,
        }),
        frm.doc.result_id ? frappe.db.get_doc("Scenario Result", frm.doc.result_id).catch(() => null) : Promise.resolve(null),
        frappe.call({
          method: "chainpilot_ai.ai.service.get_recommendation_ai_panel_rpc",
          args: { recommendation_id: frm.doc.name },
        }).then((response) => response.message || {}).catch(() => ({ explanation: null, llm: null })),
      ]);
      target.html(detail_html(frm.doc, evidence, checks, scenario, aiPanel));
      target.find("[data-generate-llm]").on("click", () => generate_llm_explanation(frm, target));
    } catch (error) {
      target.html(`<div class="chainpilot-empty">${__("无法加载决策证据。")}</div>`);
      console.error(error);
    }
  }

  function ensure_detail_panel(frm) {
    const formLayout = $(frm.wrapper).find(".form-layout").first();
    formLayout.find(".chainpilot-detail-panel").remove();
    const panel = $(`
      <div class="chainpilot-shell chainpilot-detail-panel">
        <div class="chainpilot-panel" data-chainpilot-detail></div>
      </div>
    `);
    formLayout.prepend(panel);
    return panel.find("[data-chainpilot-detail]");
  }

  async function generate_llm_explanation(frm, target) {
    const button = target.find("[data-generate-llm]");
    button.prop("disabled", true).text(__("正在生成..."));
    frappe.show_alert({ message: __("正在调用真实模型生成说明..."), indicator: "blue" });
    try {
      const response = await frappe.call({
        method: "chainpilot_ai.ai.service.generate_recommendation_explanation_rpc",
        args: { recommendation_id: frm.doc.name },
      });
      const result = response.message || {};
      frappe.show_alert({ message: __("智能说明已生成。"), indicator: result.ok ? "green" : "orange" });
      await render_recommendation_detail(frm);
    } catch (error) {
      console.error(error);
      frappe.msgprint({
        title: __("生成失败"),
        message: __("模型调用或证据校验未通过，请查看 LLM Call Log。"),
        indicator: "red",
      });
      button.prop("disabled", false).text(__("生成智能说明"));
    }
  }

  function detail_html(doc, evidence, checks, scenario, aiPanel) {
    const actionTitle = `${chainpilot.actionLabel(doc.action_type)} · ${doc.material_name || doc.material_code}`;
    const explanation = aiPanel && aiPanel.explanation;
    const llm = (aiPanel && aiPanel.llm) || {};
    return `
      <div class="chainpilot-panel-header">
        <div>
          <div class="chainpilot-eyebrow">${__("建议详情")}</div>
          <h2 class="chainpilot-panel-title">${chainpilot.escape(actionTitle)}</h2>
          <p class="chainpilot-panel-note">
            ${chainpilot.escape(chainpilot.sapObjectLabel(doc.sap_object_type))} ${chainpilot.escape(doc.sap_doc_no)}/${chainpilot.escape(doc.sap_item_no)}
            · ${chainpilot.escape(doc.plant)} · ${chainpilot.escape(doc.supplier || "-")}
          </p>
        </div>
        <div>
          ${chainpilot.badge(chainpilot.statusLabel(doc.approval_status), chainpilot.verdictTone(doc.approval_status))}
          ${chainpilot.badge(chainpilot.statusLabel(doc.explanation_status), chainpilot.verdictTone(doc.explanation_status))}
        </div>
      </div>

      <div class="chainpilot-detail-grid">
        ${detail_metric(__("资金占用减少额"), chainpilot.currency(doc.cash_release), chainpilot.savingTypeLabel ? chainpilot.savingTypeLabel(doc.saving_type) : doc.saving_type)}
        ${detail_metric(__("数量变化"), `${chainpilot.number(doc.before_qty)} -> ${chainpilot.number(doc.after_qty)}`, __("调整前 / 调整后"))}
        ${detail_metric(__("日期变化"), `${doc.before_date || "-"} -> ${doc.after_date || "-"}`, __("调整前 / 调整后"))}
        ${detail_metric(__("库存覆盖"), `${chainpilot.number(doc.inventory_days_before, 1)} -> ${chainpilot.number(doc.inventory_days_after, 1)} ${__("天")}`, __("调整后必须高于阈值"))}
        ${detail_metric(__("缺料风险"), `${chainpilot.number(doc.shortage_risk_before, 1)} -> ${chainpilot.number(doc.shortage_risk_after, 1)}`, __("越低越好"))}
        ${detail_metric(__("置信度"), chainpilot.percent(Number(doc.confidence_score || 0) * 100), scenario ? scenario.strategy_name : __("方案结果"))}
      </div>

      <div class="chainpilot-evidence-grid">
        <div>
          <div class="chainpilot-panel-header">
            <div>
              <h3 class="chainpilot-panel-title">${__("证据")}</h3>
              <p class="chainpilot-panel-note">${__("让动作可解释、可审计的证据点。")}</p>
            </div>
          </div>
          ${evidence.map(evidence_item).join("") || empty_state(__("该建议尚未关联证据。"))}
        </div>
        <div>
          <div class="chainpilot-panel-header">
            <div>
              <h3 class="chainpilot-panel-title">${__("约束校验")}</h3>
              <p class="chainpilot-panel-note">${__("进入审批或生成回写草稿前必须通过的规则。")}</p>
            </div>
          </div>
          ${checks.map(check_item).join("") || empty_state(__("该建议尚未关联约束校验。"))}
        </div>
      </div>

      <div class="chainpilot-panel chainpilot-ai-panel" style="margin-top: 12px;">
        <div class="chainpilot-panel-header">
          <div>
            <div class="chainpilot-label">${__("智能说明")}</div>
            <h3 class="chainpilot-panel-title">${explanation ? __("基于证据生成") : __("等待生成")}</h3>
            <p class="chainpilot-panel-note">${chainpilot.escape(llm.configured ? `${llm.model} · ${llm.message}` : "未配置真实模型，无法生成正式智能说明。")}</p>
          </div>
          <button class="chainpilot-link-button" data-generate-llm="1">${explanation ? __("重新生成") : __("生成智能说明")}</button>
        </div>
        ${explanation ? explanation_block(explanation) : preview_block(doc, evidence, checks)}
      </div>
    `;
  }

  function detail_metric(label, value, note) {
    return `<div class="chainpilot-meta-item"><div class="chainpilot-label">${chainpilot.escape(label)}</div><div class="chainpilot-value">${chainpilot.escape(value)}</div><div class="chainpilot-action-subtitle">${chainpilot.escape(note || "")}</div></div>`;
  }

  function evidence_item(item) {
    return `
      <div class="chainpilot-evidence-item">
        <div class="chainpilot-action-id">${chainpilot.escape(item.evidence_id)} · ${chainpilot.escape(source_label(item.source_type))}</div>
        <div class="chainpilot-action-title">${chainpilot.escape(metric_label(item.metric_name))}: ${chainpilot.escape(metric_value(item.metric_value))} / ${chainpilot.escape(metric_value(item.threshold_value || "-"))}</div>
        <div class="chainpilot-action-subtitle">${chainpilot.escape(business_text(item.summary))}</div>
        <div style="margin-top: 8px;">${chainpilot.badge(chainpilot.statusLabel(item.verdict), chainpilot.verdictTone(item.verdict))}</div>
      </div>
    `;
  }

  function check_item(item) {
    return `
      <div class="chainpilot-evidence-item">
        <div class="chainpilot-action-id">${chainpilot.escape(item.check_id)} · ${chainpilot.escape(rule_label(item.rule_code))}</div>
        <div class="chainpilot-action-title">${chainpilot.escape(business_text(item.message))}</div>
        <div class="chainpilot-action-subtitle">${__("证据")}: ${chainpilot.escape(item.evidence_id || "-")}</div>
        <div style="margin-top: 8px;">${chainpilot.badge(chainpilot.statusLabel(item.verdict), chainpilot.verdictTone(item.verdict))}</div>
      </div>
    `;
  }

  function explanation_block(explanation) {
    return `
      <div class="chainpilot-ai-explanation">
        ${format_explanation(explanation.generated_text)}
        <div class="chainpilot-change-line" style="margin-top: 10px;">
          <span>${__("模型")}: ${chainpilot.escape(explanation.model_name || "-")}</span>
          <span>${__("证据")}: ${chainpilot.escape(explanation.evidence_ids_used || "-")}</span>
        </div>
      </div>
    `;
  }

  function preview_block(doc, evidence, checks) {
    const evidenceSummary = evidence[0] ? evidence[0].summary : __("暂无证据摘要");
    const approval = checks.some((check) => check.verdict === "PASS_WITH_APPROVAL") ? __("需要升级审批") : __("已通过当前约束");
    const text = __(
      "{0} 将调整 {1} {2}/{3}，物料 {4}。预计释放现金 {5}，调整后库存覆盖 {6} 天，并且{7}。主要证据：{8}",
      [
        chainpilot.actionLabel(doc.action_type),
        doc.sap_object_type,
        doc.sap_doc_no,
        doc.sap_item_no,
        doc.material_code,
        chainpilot.currency(doc.cash_release),
        chainpilot.number(doc.inventory_days_after, 1),
        approval,
        evidenceSummary,
      ],
    );
    return `<div class="chainpilot-action-subtitle">${chainpilot.escape(text)}</div>`;
  }

  function format_explanation(text) {
    return String(text || "")
      .split("\n")
      .filter(Boolean)
      .map((line) => `<p>${chainpilot.escape(line)}</p>`)
      .join("");
  }

  function source_label(value) {
    const labels = {
      Simulation: __("模拟测算"),
      Snapshot: __("快照证据"),
      Algorithm: __("算法结果"),
      SAP: __("SAP 数据"),
    };
    return labels[value] || value || "";
  }

  function metric_label(value) {
    const labels = {
      safety_stock_gap: __("安全库存缺口"),
      inventory_days_after: __("调整后库存覆盖"),
      confidence_score: __("置信度"),
      cash_impact: __("资金占用减少额"),
      shortage_probability_14d: __("十四天缺料概率"),
    };
    return labels[value] || value || "";
  }

  function metric_value(value) {
    const labels = { review: __("复核") };
    return labels[value] || value || "";
  }

  function rule_label(value) {
    const labels = {
      MASTER_DATA_REVIEW: __("主数据复核"),
      M3_SAFE_STOCK: __("安全库存校验"),
      CASH_RELEASE_CONSTRAINT: __("资金优化约束"),
      SHORTAGE_RISK_REVIEW: __("缺料风险复核"),
    };
    return labels[value] || value || "";
  }

  function business_text(value) {
    return String(value || "")
      .replaceAll("safety_stock_gap", __("安全库存缺口"))
      .replaceAll("review", __("复核"))
      .replaceAll("PASS_WITH_APPROVAL", __("需审批"))
      .replaceAll("WARN", __("需关注"));
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
          REDUCE_PR_QTY: __("下调采购申请数量"),
          DELAY_UNCONFIRMED_PO: __("延后未确认采购订单"),
          ADVANCE_RISK_MATERIAL: __("提前风险物料"),
          REVIEW_SAFETY_STOCK: __("复核安全库存"),
          REVIEW_SUPPLIER_LEAD_TIME: __("复核供应商交期"),
        };
        return labels[actionType] || actionType || "";
      },
      savingTypeLabel(savingType) {
        const labels = {
          "Cash Release": __("减少采购占用"),
          "Book Saving": __("账面节省"),
          "Purchase Deferral": __("采购延期"),
        };
        return labels[savingType] || savingType || "";
      },
    };
  }
})();
