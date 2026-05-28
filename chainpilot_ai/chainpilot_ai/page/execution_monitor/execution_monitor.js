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

  frappe.pages["execution-monitor"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
      parent: wrapper,
      title: __("Execution Monitor"),
      single_column: true,
    });

    page.set_primary_action(__("生成审批包"), () => create_package(page));
    page.add_inner_button(__("批准最新审批包"), () => approve_latest(page));
    page.add_inner_button(__("拒绝最新审批包"), () => reject_latest(page));
    page.add_inner_button(__("学习中心"), () => frappe.set_route("learning-center"));
    page.add_inner_button(__("动作收件箱"), () => frappe.set_route("action-inbox"));
    page.main.html(`<div class="chainpilot-shell"><div class="chainpilot-loading">${__("正在加载执行监控...")}</div></div>`);
    load_dashboard(page);
  };

  async function load_dashboard(page) {
    try {
      const response = await frappe.call({
        method: "chainpilot_ai.monitoring.service.get_execution_dashboard",
      });
      render_dashboard(page, response.message || {});
    } catch (error) {
      console.error(error);
      page.main.find(".chainpilot-shell").html(`<div class="chainpilot-empty">${__("无法加载执行监控。")}</div>`);
    }
  }

  function render_dashboard(page, data) {
    const counts = data.counts || {};
    const packages = data.packages || [];
    const tasks = data.tasks || [];
    const drafts = data.drafts || [];
    const communications = data.communications || [];
    const executions = data.executions || [];
    const feedback = data.feedback || [];
    const signals = data.signals || [];
    const latestPackage = packages[0] || {};
    const expectedCash = executions.reduce((sum, item) => sum + Number(item.expected_cash_release || 0), 0);

    page.main.find(".chainpilot-shell").html(`
      <section class="chainpilot-hero">
        <div>
          <div class="chainpilot-eyebrow">${__("M4 Approval and Draft Execution")}</div>
          <h1 class="chainpilot-title">${__("Execution Monitor")}</h1>
          <p class="chainpilot-subtitle">
            ${__("把 Recommendation 推进到审批包、供应商沟通草稿、SAP 回写草稿和执行复盘。所有 SAP 变更只生成草稿，不自动写生产系统。")}
          </p>
        </div>
        <div class="chainpilot-meta-grid">
          ${meta_item(__("审批包"), chainpilot.number(counts["Approval Package"] || 0))}
          ${meta_item(__("回写草稿"), chainpilot.number(counts["SAP Writeback Draft"] || 0))}
          ${meta_item(__("待兑现现金"), chainpilot.currency(expectedCash))}
          ${meta_item(__("最新状态"), latestPackage.status || __("Not Started"))}
        </div>
      </section>

      <section class="chainpilot-grid-2">
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">${__("审批包")}</h2>
              <p class="chainpilot-panel-note">${__("多条 Recommendation 打包后先走人工审批，再生成回写草稿。")}</p>
            </div>
            <button class="chainpilot-link-button" data-create-package="1">${__("生成审批包")}</button>
          </div>
          <div class="chainpilot-compact-list">
            ${packages.map(package_row).join("") || empty_state(__("尚无审批包。"))}
          </div>
        </div>
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">${__("审批任务")}</h2>
              <p class="chainpilot-panel-note">${__("计划、采购、财务和总监审批可留痕。")}</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${tasks.map(task_row).join("") || empty_state(__("尚无审批任务。"))}
          </div>
        </div>
      </section>

      <section class="chainpilot-panel" style="margin-top: 18px;">
        <div class="chainpilot-panel-header">
          <div>
            <h2 class="chainpilot-panel-title">${__("SAP Writeback Draft")}</h2>
            <p class="chainpilot-panel-note">${__("只生成 DRAFT_ONLY payload、rollback payload 和二次读取校验结果。")}</p>
          </div>
          <div>
            <button class="chainpilot-filter" data-approve-latest="1">${__("批准最新包")}</button>
            <button class="chainpilot-filter" data-reject-latest="1">${__("拒绝最新包")}</button>
          </div>
        </div>
        <div class="chainpilot-action-list">
          ${drafts.map(draft_card).join("") || empty_state(__("尚无回写草稿。"))}
        </div>
      </section>

      <section class="chainpilot-grid-2">
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">${__("供应商沟通草稿")}</h2>
              <p class="chainpilot-panel-note">${__("PO 改期动作生成可复核消息草稿，不自动发送。")}</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${communications.map(communication_row).join("") || empty_state(__("尚无供应商沟通草稿。"))}
          </div>
        </div>
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">${__("执行结果")}</h2>
              <p class="chainpilot-panel-note">${__("草稿后的兑现状态和未兑现原因可复盘。")}</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${executions.map(execution_row).join("") || empty_state(__("尚无执行结果。"))}
          </div>
        </div>
      </section>

      <section class="chainpilot-grid-2">
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">${__("反馈记录")}</h2>
              <p class="chainpilot-panel-note">${__("拒绝原因、供应商反馈和执行反馈进入学习闭环。")}</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${feedback.map(feedback_row).join("") || empty_state(__("尚无反馈记录。"))}
          </div>
        </div>
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">${__("Learning Signal")}</h2>
              <p class="chainpilot-panel-note">${__("反馈沉淀为调权对象和建议权重变化。")}</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${signals.map(signal_row).join("") || empty_state(__("尚无学习信号。"))}
          </div>
        </div>
      </section>
    `);

    page.main.find("[data-create-package]").on("click", () => create_package(page));
    page.main.find("[data-approve-latest]").on("click", () => approve_latest(page));
    page.main.find("[data-reject-latest]").on("click", () => reject_latest(page));
  }

  async function create_package(page) {
    frappe.show_alert({ message: __("正在生成审批包..."), indicator: "blue" });
    const response = await frappe.call({
      method: "chainpilot_ai.approval.service.create_approval_package_rpc",
      args: { limit: 5 },
    });
    const result = response.message || {};
    frappe.show_alert({
      message: __("审批包已生成：{0}", [result.package && result.package.package_id ? result.package.package_id : ""]),
      indicator: result.ok ? "green" : "orange",
    });
    load_dashboard(page);
  }

  async function approve_latest(page) {
    frappe.show_alert({ message: __("正在批准并生成回写草稿..."), indicator: "blue" });
    const response = await frappe.call({
      method: "chainpilot_ai.approval.service.approve_package_rpc",
      args: { package_id: null },
    });
    const result = response.message || {};
    const drafts = (((result || {}).writeback || {}).drafts || []).length;
    frappe.show_alert({
      message: __("已生成 {0} 个回写草稿", [chainpilot.number(drafts)]),
      indicator: result.ok ? "green" : "orange",
    });
    load_dashboard(page);
  }

  async function reject_latest(page) {
    frappe.show_alert({ message: __("正在记录拒绝反馈..."), indicator: "orange" });
    const response = await frappe.call({
      method: "chainpilot_ai.approval.service.reject_package_rpc",
      args: { package_id: null, reason: __("M4 mock rejection for learning signal validation.") },
    });
    const result = response.message || {};
    frappe.show_alert({
      message: __("已记录 {0} 条反馈", [chainpilot.number((result.feedback || []).length)]),
      indicator: result.ok ? "green" : "orange",
    });
    load_dashboard(page);
  }

  function package_row(item) {
    const tone = item.status === "Approved" ? "green" : item.status === "Rejected" ? "red" : "blue";
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.escape(item.package_id)}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(item.approval_summary || item.risk_summary || "")}</div>
        </div>
        <div>
          ${chainpilot.badge(item.status || "-", tone)}
          <div class="chainpilot-metric">${chainpilot.currency(item.total_cash_release || 0)}</div>
          <div class="chainpilot-metric-label">${chainpilot.number(item.recommendation_count || 0)} ${__("actions")}</div>
        </div>
      </div>
    `;
  }

  function task_row(item) {
    const tone = item.status === "Approved" ? "green" : item.status === "Rejected" ? "red" : "amber";
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.escape(item.approval_role)}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(item.package_id)} · ${chainpilot.escape(item.decision_comment || "")}</div>
        </div>
        <div>${chainpilot.badge(item.status || "-", tone)}</div>
      </div>
    `;
  }

  function draft_card(item) {
    const tone = item.conflict_status === "Conflict" ? "red" : "green";
    return `
      <article class="chainpilot-action-card">
        <div class="chainpilot-action-main">
          <div class="chainpilot-action-id">${chainpilot.escape(item.draft_id)} · ${chainpilot.escape(item.safety_mode)}</div>
          <div class="chainpilot-action-title">${chainpilot.escape(item.sap_object_type)} ${chainpilot.escape(item.sap_doc_no)}/${chainpilot.escape(item.sap_item_no)}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(item.target_api || "")}</div>
        </div>
        <div>${metric(item.status || "-", __("状态"))}</div>
        <div>${chainpilot.badge(item.conflict_status || "-", tone)}</div>
        <div>${chainpilot.badge(__("不自动写 SAP"), "blue")}</div>
      </article>
    `;
  }

  function communication_row(item) {
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.escape(item.subject || item.communication_id)}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(item.supplier || "-")} · ${chainpilot.escape(item.message || "")}</div>
        </div>
        <div>${chainpilot.badge(item.status || "-", "blue")}</div>
      </div>
    `;
  }

  function execution_row(item) {
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.escape(item.execution_id)}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(item.unrealized_reason || "")}</div>
        </div>
        <div>
          ${chainpilot.badge(item.status || "-", item.status === "Executed" ? "green" : "amber")}
          <div class="chainpilot-metric">${chainpilot.currency(item.expected_cash_release || 0)}</div>
        </div>
      </div>
    `;
  }

  function feedback_row(item) {
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.escape(item.feedback_type || item.feedback_id)}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(item.reason || "")} · ${chainpilot.escape(item.comment || "")}</div>
        </div>
        <div>${chainpilot.badge(item.recommendation_id || "-", "neutral")}</div>
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
        <div>
          ${chainpilot.badge(item.status || "-", "blue")}
          <div class="chainpilot-metric">${chainpilot.number(item.suggested_weight_delta || 0, 2)}</div>
        </div>
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
