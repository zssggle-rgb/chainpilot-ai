(function () {
  const chainpilot = window.chainpilot || (window.chainpilot = {});
  chainpilot.escape = chainpilot.escape || function (value) {
    return frappe.utils.escape_html(value == null ? "" : String(value));
  };
  chainpilot.currency = chainpilot.currency || function (value) {
    const amount = Number(value || 0);
    if (Math.abs(amount) >= 10000) return `${(amount / 10000).toLocaleString(undefined, { maximumFractionDigits: 1 })} 万元`;
    return `${amount.toLocaleString(undefined, { maximumFractionDigits: 0 })} 元`;
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
  chainpilot.statusLabel = chainpilot.statusLabel || function (value) {
    const labels = {
      Draft: "草稿",
      Reviewed: "已复核",
      Applied: "已应用",
      Ignored: "已忽略",
      Sent: "已发送",
      Executed: "已执行",
      Failed: "失败",
      "Draft Ready": "草稿已生成",
      New: "新建",
      Open: "未关闭",
      Contained: "已控制",
      Closed: "已关闭",
    };
    return labels[value] || value || "";
  };
  chainpilot.actionLabel = chainpilot.actionLabel || function (value) {
    const labels = {
      DELAY_UNCONFIRMED_PO: "延后未确认采购订单",
      REVIEW_SAFETY_STOCK: "复核安全库存",
      REDUCE_PR_QTY: "下调采购申请数量",
    };
    return labels[value] || value || "";
  };

  frappe.pages["learning-center"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
      parent: wrapper,
      title: "学习中心",
      single_column: true,
    });

    page.set_primary_action("生成学习快照", () => seed_learning(page));
    page.add_inner_button("监控", () => frappe.set_route("execution-monitor"));
    page.add_inner_button("智能", () => frappe.set_route("ai-copilot"));
    page.main.html(`<div class="chainpilot-shell"><div class="chainpilot-loading">正在加载学习中心...</div></div>`);
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
      page.main.find(".chainpilot-shell").html(`<div class="chainpilot-empty">无法加载学习中心。</div>`);
    }
  }

  async function seed_learning(page) {
    frappe.show_alert({ message: "正在生成学习快照...", indicator: "blue" });
    const response = await frappe.call({
      method: "chainpilot_ai.learning.service.seed_learning_mock_data",
    });
    const result = response.message || {};
    frappe.show_alert({
      message: result.snapshot ? `学习快照已生成：${result.snapshot.snapshot_id}` : "学习指标已刷新",
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
          <div class="chainpilot-eyebrow">反馈学习</div>
          <h1 class="chainpilot-title">学习中心</h1>
          <p class="chainpilot-subtitle">
            汇总审批结果、供应商反馈、兑现结果和缺料事件。
          </p>
        </div>
        <div class="chainpilot-meta-grid">
          ${meta_item("学习快照", chainpilot.number(counts["Learning Metric Snapshot"] || 0))}
          ${meta_item("调权草稿", chainpilot.number(counts["Rule Weight Adjustment"] || 0))}
          ${meta_item("缺料事件", chainpilot.number(metrics.shortage_event_count || 0))}
          ${meta_item("反馈记录", chainpilot.number(counts["Feedback Record"] || 0))}
        </div>
      </section>

      <section class="chainpilot-kpi-grid">
        ${kpi_card("采纳率", percent(metrics.adoption_rate), "已批准审批包 / 全部审批包", metrics.adoption_rate)}
        ${kpi_card("供应商接受率", percent(metrics.supplier_acceptance_rate), "已接受反馈 / 供应商反馈", metrics.supplier_acceptance_rate)}
        ${kpi_card("兑现率", percent(metrics.realization_rate), `${chainpilot.currency(metrics.total_realized_cash || 0)} / ${chainpilot.currency(metrics.total_expected_cash || 0)}`, metrics.realization_rate)}
        ${kpi_card("拒绝率", percent(metrics.rejection_rate), clean_text(metrics.top_rejection_reason || "暂无拒绝"), 100 - Number(metrics.rejection_rate || 0))}
      </section>

      <section class="chainpilot-grid-2">
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">学习洞察</h2>
              <p class="chainpilot-panel-note">给下一轮建议排序提供依据。</p>
            </div>
            <button class="chainpilot-link-button" data-seed-learning="1">刷新快照</button>
          </div>
          <div class="chainpilot-compact-list">
            ${insights.map(insight_row).join("") || empty_state("暂无学习洞察。")}
          </div>
        </div>
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">指标快照</h2>
              <p class="chainpilot-panel-note">周期性记录采纳、供应商接受、兑现和缺料指标。</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${snapshots.map(snapshot_row).join("") || empty_state("尚无学习快照。")}
          </div>
        </div>
      </section>

      <section class="chainpilot-grid-2">
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">规则调权草稿</h2>
              <p class="chainpilot-panel-note">业务复核前不会影响推荐排序。</p>
            </div>
          </div>
          <div class="chainpilot-action-list">
            ${adjustments.map(adjustment_card).join("") || empty_state("尚无调权草稿。")}
          </div>
        </div>
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">拒绝原因</h2>
              <p class="chainpilot-panel-note">识别需要降权或补充证据的建议类型。</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${rejectionReasons.map(reason_row).join("") || empty_state("尚无拒绝原因。")}
          </div>
        </div>
      </section>

      <section class="chainpilot-grid-2">
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">供应商反馈</h2>
              <p class="chainpilot-panel-note">采购订单沟通结果会影响后续建议排序。</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${communications.map(communication_row).join("") || empty_state("尚无供应商反馈。")}
          </div>
        </div>
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">兑现结果</h2>
              <p class="chainpilot-panel-note">对比资金占用减少额和实际兑现。</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${executions.map(execution_row).join("") || empty_state("尚无兑现结果。")}
          </div>
        </div>
      </section>

      <section class="chainpilot-grid-2">
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">缺料事件</h2>
              <p class="chainpilot-panel-note">用于强化安全库存、冻结期和供应商确认规则。</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${shortageEvents.map(shortage_row).join("") || empty_state("尚无缺料事件。")}
          </div>
        </div>
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">学习信号</h2>
              <p class="chainpilot-panel-note">保留调权来源，便于审计。</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${signals.map(signal_row).join("") || empty_state("尚无学习信号。")}
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
          <div class="chainpilot-action-title">${clean_text(item.title)}</div>
          <div class="chainpilot-action-subtitle">${clean_text(item.body)}</div>
        </div>
        <div>${chainpilot.badge(tone_label(item.tone), item.tone || "blue")}</div>
      </div>
    `;
  }

  function snapshot_row(item) {
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.escape(item.snapshot_id)}</div>
          <div class="chainpilot-action-subtitle">${clean_text(item.summary || item.top_rejection_reason || "")}</div>
        </div>
        <div>
          <div class="chainpilot-metric">${percent(item.realization_rate)}</div>
          <div class="chainpilot-metric-label">兑现率</div>
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
          <div class="chainpilot-action-title">${target_label(item.target_type)} · ${chainpilot.actionLabel(item.target)}</div>
          <div class="chainpilot-action-subtitle">${clean_text(item.rationale || "")}</div>
        </div>
        <div>${metric(chainpilot.number(item.current_weight || 0, 2), "当前权重")}</div>
        <div>${metric(chainpilot.number(item.suggested_weight || 0, 2), "建议权重")}</div>
        <div>${chainpilot.badge(chainpilot.statusLabel(item.status || "Draft"), tone)}</div>
      </article>
    `;
  }

  function reason_row(item) {
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${clean_text(item.reason)}</div>
          <div class="chainpilot-action-subtitle">进入规则调权和证据补强。</div>
        </div>
        <div>${chainpilot.badge(`${chainpilot.number(item.count || 0)} 次`, "red")}</div>
      </div>
    `;
  }

  function communication_row(item) {
    const tone = item.status === "Sent" ? "green" : item.status === "Reviewed" ? "amber" : "blue";
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">采购订单 ${chainpilot.escape(item.sap_doc_no || "-")} 交期沟通</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(item.supplier || "-")} · ${chainpilot.escape(item.sap_doc_no || "")}</div>
        </div>
        <div>${chainpilot.badge(chainpilot.statusLabel(item.status) || "-", tone)}</div>
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
          <div class="chainpilot-action-subtitle">${clean_text(item.unrealized_reason || "")}</div>
        </div>
        <div>
          ${chainpilot.badge(chainpilot.statusLabel(item.status) || "-", tone)}
          <div class="chainpilot-metric">${chainpilot.currency(realized)}</div>
          <div class="chainpilot-metric-label">预计 ${chainpilot.currency(expected)}</div>
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
          <div class="chainpilot-action-subtitle">${clean_text(item.root_cause || "")}</div>
        </div>
        <div>
          ${chainpilot.badge(severity_label(item.severity), tone)}
          <div class="chainpilot-metric-label">${chainpilot.statusLabel(item.status) || ""}</div>
        </div>
      </div>
    `;
  }

  function signal_row(item) {
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${target_label(item.target_type)} · ${chainpilot.actionLabel(item.target)}</div>
          <div class="chainpilot-action-subtitle">${clean_text(item.reason || "")}</div>
        </div>
        <div>${metric(chainpilot.number(item.suggested_weight_delta || 0, 2), "权重变化")}</div>
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

  function clean_text(value) {
    const text = String(value || "");
    const labels = {
      "Realization discipline": "兑现纪律",
      "Supplier confirmation": "供应商确认",
      "Shortage guardrail": "缺料防线",
      "Rule adjustment queue": "规则调权队列",
      "Approval Rejected": "审批拒绝",
      "No rejection yet": "暂无拒绝",
      "Closed by M5 mock learning snapshot.": "已进入学习快照复盘。",
      "Supplier confirmation expired before manual SAP execution.": "供应商确认已过期，未执行。",
      "Awaiting approved manual SAP execution. Production SAP auto-write is disabled.": "等待人工执行，系统不会自动写入生产 SAP。",
      "M4 verification rejection: supplier confirmation missing and cash impact below threshold.": "供应商确认不足，资金占用减少额低于阈值。",
    };
    if (labels[text]) return chainpilot.escape(labels[text]);
    return chainpilot.escape(
      text
        .replace("Realized", "已兑现")
        .replace("of expected cash; keep manual SAP execution and Finance reconciliation visible.", "的资金占用减少额；请继续关注人工执行和财务对账。")
        .replace("Supplier acceptance is", "供应商接受率")
        .replace("; rank PO delay actions lower when confirmation is missing.", "；缺少确认时应降低采购订单延期建议优先级。")
        .replace("shortage events should feed safety stock and supplier lead-time weights before the next recommendation run.", "个缺料事件应进入安全库存和供应商交期权重。")
        .replace("draft adjustments are waiting for business review before applying to ranking.", "条调权草稿等待业务复核。")
        .replace("needs stronger confirmation before recommendation ranking.", "需要更强的确认依据。"),
    );
  }

  function target_label(value) {
    const labels = { "Action Type": "建议类型", Material: "物料", Supplier: "供应商", Rule: "规则" };
    return chainpilot.escape(labels[value] || value || "");
  }

  function severity_label(value) {
    const labels = { High: "高", Medium: "中", Low: "低", Critical: "严重" };
    return labels[value] || value || "";
  }

  function tone_label(value) {
    const labels = { green: "正常", amber: "关注", red: "风险", blue: "提示" };
    return labels[value] || "提示";
  }
})();
