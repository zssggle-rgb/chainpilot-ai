(function () {
  const chainpilot = window.chainpilot || (window.chainpilot = {});
  chainpilot.escape = chainpilot.escape || function (value) {
    return frappe.utils.escape_html(value == null ? "" : String(value));
  };
  chainpilot.currency = chainpilot.currency || function (value) {
    return format_currency(value || 0, frappe.defaults.get_default("currency") || "USD", 0);
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

  frappe.pages["learning-center"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
      parent: wrapper,
      title: __("Learning Center"),
      single_column: true,
    });

    page.set_primary_action(__("生成学习快照"), () => seed_learning(page));
    page.add_inner_button(__("执行监控"), () => frappe.set_route("execution-monitor"));
    page.add_inner_button(__("AI Copilot"), () => frappe.set_route("ai-copilot"));
    page.main.html(`<div class="chainpilot-shell"><div class="chainpilot-loading">${__("正在加载学习闭环...")}</div></div>`);
    load_dashboard(page);
  };

  async function load_dashboard(page) {
    try {
      const response = await frappe.call({
        method: "chainpilot_ai.learning.service.get_learning_dashboard",
      });
      render_dashboard(page, response.message || {});
    } catch (error) {
      console.error(error);
      page.main.find(".chainpilot-shell").html(`<div class="chainpilot-empty">${__("无法加载学习闭环。")}</div>`);
    }
  }

  async function seed_learning(page) {
    frappe.show_alert({ message: __("正在生成学习快照..."), indicator: "blue" });
    const response = await frappe.call({
      method: "chainpilot_ai.learning.service.seed_learning_mock_data",
    });
    const result = response.message || {};
    frappe.show_alert({
      message: result.snapshot
        ? __("学习快照已生成：{0}", [result.snapshot.snapshot_id])
        : __("学习指标已刷新"),
      indicator: result.ok ? "green" : "orange",
    });
    render_dashboard(page, result);
  }

  function render_dashboard(page, data) {
    const metrics = data.metrics || {};
    const counts = data.counts || {};
    const insights = data.insights || [];
    const snapshots = data.snapshots || [];
    const adjustments = data.adjustments || [];
    const shortageEvents = data.shortage_events || [];
    const feedback = data.feedback || [];
    const executions = data.executions || [];
    const communications = data.communications || [];
    const signals = data.signals || [];
    const rejectionReasons = metrics.rejection_reasons || [];

    page.main.find(".chainpilot-shell").html(`
      <section class="chainpilot-hero">
        <div>
          <div class="chainpilot-eyebrow">${__("M5 Learning and Rule Tuning")}</div>
          <h1 class="chainpilot-title">${__("Learning Center")}</h1>
          <p class="chainpilot-subtitle">
            ${__("把审批、供应商反馈、兑现结果和缺料事件沉淀为可审计的学习指标。当前仍使用 mock 闭环，不自动改业务规则或写 SAP。")}
          </p>
        </div>
        <div class="chainpilot-meta-grid">
          ${meta_item(__("学习快照"), chainpilot.number(counts["Learning Metric Snapshot"] || 0))}
          ${meta_item(__("调权草稿"), chainpilot.number(counts["Rule Weight Adjustment"] || 0))}
          ${meta_item(__("缺料事件"), chainpilot.number(metrics.shortage_event_count || 0))}
          ${meta_item(__("反馈记录"), chainpilot.number(counts["Feedback Record"] || 0))}
        </div>
      </section>

      <section class="chainpilot-kpi-grid">
        ${kpi_card(__("采纳率"), percent(metrics.adoption_rate), __("Approved packages / all packages"), metrics.adoption_rate)}
        ${kpi_card(__("供应商接受率"), percent(metrics.supplier_acceptance_rate), __("Accepted supplier responses / supplier feedback"), metrics.supplier_acceptance_rate)}
        ${kpi_card(__("兑现率"), percent(metrics.realization_rate), `${chainpilot.currency(metrics.total_realized_cash || 0)} / ${chainpilot.currency(metrics.total_expected_cash || 0)}`, metrics.realization_rate)}
        ${kpi_card(__("拒绝率"), percent(metrics.rejection_rate), chainpilot.escape(metrics.top_rejection_reason || __("No rejection yet")), 100 - Number(metrics.rejection_rate || 0))}
      </section>

      <section class="chainpilot-grid-2">
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">${__("学习洞察")}</h2>
              <p class="chainpilot-panel-note">${__("把执行反馈转成下一次推荐排序的输入。")}</p>
            </div>
            <button class="chainpilot-link-button" data-seed-learning="1">${__("刷新快照")}</button>
          </div>
          <div class="chainpilot-compact-list">
            ${insights.map(insight_row).join("") || empty_state(__("暂无学习洞察。"))}
          </div>
        </div>
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">${__("指标快照")}</h2>
              <p class="chainpilot-panel-note">${__("按周期固化采纳、供应商接受、兑现和缺料指标。")}</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${snapshots.map(snapshot_row).join("") || empty_state(__("尚无学习快照。"))}
          </div>
        </div>
      </section>

      <section class="chainpilot-grid-2">
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">${__("Rule Weight Adjustment")}</h2>
              <p class="chainpilot-panel-note">${__("调权只生成 Draft，业务复核前不会影响推荐排序。")}</p>
            </div>
          </div>
          <div class="chainpilot-action-list">
            ${adjustments.map(adjustment_card).join("") || empty_state(__("尚无调权草稿。"))}
          </div>
        </div>
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">${__("拒绝原因")}</h2>
              <p class="chainpilot-panel-note">${__("用于识别哪些建议类型需要降权或补证据。")}</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${rejectionReasons.map(reason_row).join("") || empty_state(__("尚无拒绝原因。"))}
          </div>
        </div>
      </section>

      <section class="chainpilot-grid-2">
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">${__("供应商反馈")}</h2>
              <p class="chainpilot-panel-note">${__("PO 沟通结果会影响后续延期动作排序。")}</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${communications.map(communication_row).join("") || empty_state(__("尚无供应商反馈。"))}
          </div>
        </div>
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">${__("兑现结果")}</h2>
              <p class="chainpilot-panel-note">${__("预计现金释放和实际兑现的差异进入复盘。")}</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${executions.map(execution_row).join("") || empty_state(__("尚无兑现结果。"))}
          </div>
        </div>
      </section>

      <section class="chainpilot-grid-2">
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">${__("Shortage Event")}</h2>
              <p class="chainpilot-panel-note">${__("缺料事件用于强化安全库存、冻结期和供应商确认规则。")}</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${shortageEvents.map(shortage_row).join("") || empty_state(__("尚无缺料事件。"))}
          </div>
        </div>
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">${__("Learning Signal")}</h2>
              <p class="chainpilot-panel-note">${__("原始学习信号保留，方便审计调权来源。")}</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${signals.map(signal_row).join("") || empty_state(__("尚无 Learning Signal。"))}
          </div>
        </div>
      </section>
    `);

    page.main.find("[data-seed-learning]").on("click", () => seed_learning(page));
  }

  function kpi_card(label, value, note, score) {
    const width = Math.max(4, Math.min(100, Number(score || 0)));
    return `
      <div class="chainpilot-kpi">
        <div class="chainpilot-label">${chainpilot.escape(label)}</div>
        <strong>${chainpilot.escape(value)}</strong>
        <span>${chainpilot.escape(note)}</span>
        <div class="chainpilot-progress"><i style="width:${width}%"></i></div>
      </div>
    `;
  }

  function insight_row(item) {
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.escape(item.title)}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(item.body)}</div>
        </div>
        <div>${chainpilot.badge(item.tone || "Info", item.tone || "blue")}</div>
      </div>
    `;
  }

  function snapshot_row(item) {
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.escape(item.snapshot_id)}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(item.summary || item.top_rejection_reason || "")}</div>
        </div>
        <div>
          <div class="chainpilot-metric">${percent(item.realization_rate)}</div>
          <div class="chainpilot-metric-label">${__("兑现率")}</div>
        </div>
      </div>
    `;
  }

  function adjustment_card(item) {
    const delta = Number(item.suggested_weight || 0) - Number(item.current_weight || 0);
    const tone = delta < 0 ? "amber" : "green";
    return `
      <article class="chainpilot-action-card">
        <div class="chainpilot-action-main">
          <div class="chainpilot-action-id">${chainpilot.escape(item.adjustment_id)}</div>
          <div class="chainpilot-action-title">${chainpilot.escape(item.target_type)} · ${chainpilot.escape(item.target)}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(item.rationale || "")}</div>
        </div>
        <div>${metric(chainpilot.number(item.current_weight || 0, 2), __("当前权重"))}</div>
        <div>${metric(chainpilot.number(item.suggested_weight || 0, 2), __("建议权重"))}</div>
        <div>${chainpilot.badge(item.status || "Draft", tone)}</div>
      </article>
    `;
  }

  function reason_row(item) {
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.escape(item.reason)}</div>
          <div class="chainpilot-action-subtitle">${__("拒绝原因进入规则调权和证据补强。")}</div>
        </div>
        <div>${chainpilot.badge(`${chainpilot.number(item.count || 0)} ${__("次")}`, "red")}</div>
      </div>
    `;
  }

  function communication_row(item) {
    const tone = item.status === "Sent" ? "green" : item.status === "Reviewed" ? "amber" : "blue";
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.escape(item.subject || item.communication_id)}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(item.supplier || "-")} · ${chainpilot.escape(item.sap_doc_no || "")}</div>
        </div>
        <div>${chainpilot.badge(item.status || "-", tone)}</div>
      </div>
    `;
  }

  function execution_row(item) {
    const expected = Number(item.expected_cash_release || 0);
    const realized = Number(item.realized_cash_release || 0);
    const tone = item.status === "Executed" ? "green" : item.status === "Failed" ? "red" : "amber";
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.escape(item.execution_id)}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(item.unrealized_reason || "")}</div>
        </div>
        <div>
          ${chainpilot.badge(item.status || "-", tone)}
          <div class="chainpilot-metric">${chainpilot.currency(realized)}</div>
          <div class="chainpilot-metric-label">${__("of")} ${chainpilot.currency(expected)}</div>
        </div>
      </div>
    `;
  }

  function shortage_row(item) {
    const tone = item.severity === "High" || item.severity === "Critical" ? "red" : "amber";
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.escape(item.material_code || item.event_id)}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(item.root_cause || "")}</div>
        </div>
        <div>
          ${chainpilot.badge(item.severity || "-", tone)}
          <div class="chainpilot-metric-label">${chainpilot.escape(item.status || "")}</div>
        </div>
      </div>
    `;
  }

  function signal_row(item) {
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.escape(item.target_type)} · ${chainpilot.escape(item.target)}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(item.reason || "")}</div>
        </div>
        <div>${metric(chainpilot.number(item.suggested_weight_delta || 0, 2), __("权重变化"))}</div>
      </div>
    `;
  }

  function meta_item(label, value) {
    return `<div class="chainpilot-meta-item"><div class="chainpilot-label">${chainpilot.escape(label)}</div><div class="chainpilot-value">${chainpilot.escape(value)}</div></div>`;
  }

  function metric(value, label) {
    return `<div><div class="chainpilot-metric">${chainpilot.escape(value)}</div><div class="chainpilot-metric-label">${chainpilot.escape(label)}</div></div>`;
  }

  function percent(value) {
    return `${chainpilot.number(value || 0, 1)}%`;
  }

  function empty_state(message) {
    return `<div class="chainpilot-empty">${chainpilot.escape(message)}</div>`;
  }
})();
