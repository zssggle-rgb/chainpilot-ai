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
      Pending: "待处理",
      Approved: "已批准",
      Rejected: "已拒绝",
      Submitted: "已提交",
      Draft: "草稿",
      "Draft Ready": "草稿已生成",
      Ready: "已就绪",
      Executed: "已执行",
      Failed: "失败",
      Match: "一致",
      Conflict: "冲突",
      New: "新建",
    };
    return labels[value] || value || "";
  };
  chainpilot.sapObjectLabel = chainpilot.sapObjectLabel || function (objectType) {
    const labels = { PR: "采购申请", PO: "采购订单", MRP_PARAM: "MRP 参数", PLANNED_ORDER: "计划订单" };
    return labels[objectType] || objectType || "";
  };

  frappe.pages["execution-monitor"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
      parent: wrapper,
      title: "执行监控",
      single_column: true,
    });

    page.set_primary_action("生成审批包", () => create_package(page));
    page.add_inner_button("批准最新审批包", () => approve_latest(page));
    page.add_inner_button("拒绝最新审批包", () => reject_latest(page));
    page.add_inner_button("学习", () => frappe.set_route("learning-center"));
    page.add_inner_button("建议", () => frappe.set_route("action-inbox"));
    page.main.html(`<div class="chainpilot-shell"><div class="chainpilot-loading">正在加载执行监控...</div></div>`);
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
      page.main.find(".chainpilot-shell").html(`<div class="chainpilot-empty">无法加载执行监控。</div>`);
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
          <div class="chainpilot-eyebrow">审批与执行</div>
          <h1 class="chainpilot-title">执行监控</h1>
          <p class="chainpilot-subtitle">
            跟踪审批、供应商沟通、回写草稿和兑现结果。
          </p>
        </div>
        <div class="chainpilot-meta-grid">
          ${meta_item("审批包", chainpilot.number(counts["Approval Package"] || 0))}
          ${meta_item("回写草稿", chainpilot.number(counts["SAP Writeback Draft"] || 0))}
          ${meta_item("预计兑现", chainpilot.currency(expectedCash))}
          ${meta_item("最新状态", chainpilot.statusLabel(latestPackage.status || "Not Started"))}
        </div>
      </section>

      <section class="chainpilot-grid-2">
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">审批包</h2>
              <p class="chainpilot-panel-note">批量提交采购优化建议。</p>
            </div>
            <button class="chainpilot-link-button" data-create-package="1">生成审批包</button>
          </div>
          <div class="chainpilot-compact-list">
            ${packages.map(package_row).join("") || empty_state("尚无审批包。")}
          </div>
        </div>
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">审批任务</h2>
              <p class="chainpilot-panel-note">记录审批角色、结果和意见。</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${tasks.map(task_row).join("") || empty_state("尚无审批任务。")}
          </div>
        </div>
      </section>

      <section class="chainpilot-panel" style="margin-top: 18px;">
        <div class="chainpilot-panel-header">
          <div>
            <h2 class="chainpilot-panel-title">SAP 回写草稿</h2>
            <p class="chainpilot-panel-note">只生成草稿，不自动写入生产系统。</p>
          </div>
          <div>
            <button class="chainpilot-filter" data-approve-latest="1">批准最新包</button>
            <button class="chainpilot-filter" data-reject-latest="1">拒绝最新包</button>
          </div>
        </div>
        <div class="chainpilot-action-list">
          ${drafts.map(draft_card).join("") || empty_state("尚无回写草稿。")}
        </div>
      </section>

      <section class="chainpilot-grid-2">
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">供应商沟通草稿</h2>
              <p class="chainpilot-panel-note">采购订单交期沟通消息，不自动发送。</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${communications.map(communication_row).join("") || empty_state("尚无供应商沟通草稿。")}
          </div>
        </div>
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">执行结果</h2>
              <p class="chainpilot-panel-note">记录预计与实际兑现差异。</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${executions.map(execution_row).join("") || empty_state("尚无执行结果。")}
          </div>
        </div>
      </section>

      <section class="chainpilot-grid-2">
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">反馈记录</h2>
              <p class="chainpilot-panel-note">记录拒绝原因、供应商反馈和执行反馈。</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${feedback.map(feedback_row).join("") || empty_state("尚无反馈记录。")}
          </div>
        </div>
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">学习信号</h2>
              <p class="chainpilot-panel-note">用于后续建议排序和规则调权。</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${signals.map(signal_row).join("") || empty_state("尚无学习信号。")}
          </div>
        </div>
      </section>
    `);

    page.main.find("[data-create-package]").on("click", () => create_package(page));
    page.main.find("[data-approve-latest]").on("click", () => approve_latest(page));
    page.main.find("[data-reject-latest]").on("click", () => reject_latest(page));
  }

  async function create_package(page) {
    frappe.show_alert({ message: "正在生成审批包...", indicator: "blue" });
    const response = await frappe.call({
      method: "chainpilot_ai.approval.service.create_approval_package_rpc",
      args: { limit: 5 },
    });
    const result = response.message || {};
    frappe.show_alert({
      message: `审批包已生成：${result.package && result.package.package_id ? result.package.package_id : ""}`,
      indicator: result.ok ? "green" : "orange",
    });
    load_dashboard(page);
  }

  async function approve_latest(page) {
    frappe.show_alert({ message: "正在批准并生成回写草稿...", indicator: "blue" });
    const response = await frappe.call({
      method: "chainpilot_ai.approval.service.approve_package_rpc",
      args: { package_id: null },
    });
    const result = response.message || {};
    const drafts = (((result || {}).writeback || {}).drafts || []).length;
    frappe.show_alert({
      message: `已生成 ${chainpilot.number(drafts)} 个回写草稿`,
      indicator: result.ok ? "green" : "orange",
    });
    load_dashboard(page);
  }

  async function reject_latest(page) {
    frappe.show_alert({ message: "正在记录拒绝反馈...", indicator: "orange" });
    const response = await frappe.call({
      method: "chainpilot_ai.approval.service.reject_package_rpc",
      args: { package_id: null, reason: "业务复核未通过：供应商确认不足，资金占用减少额低于阈值。" },
    });
    const result = response.message || {};
    frappe.show_alert({
      message: `已记录 ${chainpilot.number((result.feedback || []).length)} 条反馈`,
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
          <div class="chainpilot-action-subtitle">包含 ${chainpilot.number(item.recommendation_count || 0)} 条建议，资金占用减少额 ${chainpilot.currency(item.total_cash_release || 0)}</div>
        </div>
        <div>
          ${chainpilot.badge(chainpilot.statusLabel(item.status) || "-", tone)}
          <div class="chainpilot-metric">${chainpilot.currency(item.total_cash_release || 0)}</div>
          <div class="chainpilot-metric-label">${chainpilot.number(item.recommendation_count || 0)} 条建议</div>
        </div>
      </div>
    `;
  }

  function task_row(item) {
    const tone = item.status === "Approved" ? "green" : item.status === "Rejected" ? "red" : "amber";
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${role_label(item.approval_role)}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(item.package_id)} · ${clean_text(item.decision_comment || "")}</div>
        </div>
        <div>${chainpilot.badge(chainpilot.statusLabel(item.status) || "-", tone)}</div>
      </div>
    `;
  }

  function draft_card(item) {
    const tone = item.conflict_status === "Conflict" ? "red" : "green";
    return `
      <article class="chainpilot-action-card">
        <div class="chainpilot-action-main">
          <div class="chainpilot-action-id">${chainpilot.escape(item.draft_id)} · 仅生成草稿</div>
          <div class="chainpilot-action-title">${chainpilot.sapObjectLabel(item.sap_object_type)} ${chainpilot.escape(item.sap_doc_no)}/${chainpilot.escape(item.sap_item_no)}</div>
          <div class="chainpilot-action-subtitle">目标接口：${chainpilot.escape(item.target_api || "")}</div>
        </div>
        <div>${metric(chainpilot.statusLabel(item.status), "状态")}</div>
        <div>${chainpilot.badge(chainpilot.statusLabel(item.conflict_status), tone)}</div>
        <div>${chainpilot.badge("不自动写入", "blue")}</div>
      </article>
    `;
  }

  function communication_row(item) {
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">采购订单 ${chainpilot.escape(item.sap_doc_no || "-")} 交期沟通</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(item.supplier || "-")} · 消息草稿待人工复核</div>
        </div>
        <div>${chainpilot.badge(chainpilot.statusLabel(item.status) || "-", "blue")}</div>
      </div>
    `;
  }

  function execution_row(item) {
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.escape(item.execution_id)}</div>
          <div class="chainpilot-action-subtitle">${clean_text(item.unrealized_reason || "")}</div>
        </div>
        <div>
          ${chainpilot.badge(chainpilot.statusLabel(item.status) || "-", item.status === "Executed" ? "green" : "amber")}
          <div class="chainpilot-metric">${chainpilot.currency(item.expected_cash_release || 0)}</div>
        </div>
      </div>
    `;
  }

  function feedback_row(item) {
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${feedback_label(item.feedback_type || item.feedback_id)}</div>
          <div class="chainpilot-action-subtitle">${clean_text(item.reason || "")} · ${clean_text(item.comment || "")}</div>
        </div>
        <div>${chainpilot.badge(item.recommendation_id || "-", "neutral")}</div>
      </div>
    `;
  }

  function signal_row(item) {
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${target_label(item.target_type)} · ${action_label(item.target)}</div>
          <div class="chainpilot-action-subtitle">${clean_text(item.reason || "")}</div>
        </div>
        <div>
          ${chainpilot.badge(chainpilot.statusLabel(item.status) || "-", "blue")}
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

  function role_label(role) {
    const labels = {
      "ChainPilot Planning Manager": "计划经理",
      "ChainPilot Procurement Manager": "采购经理",
      "ChainPilot Finance BP": "财务业务伙伴",
      "ChainPilot Supply Chain Director": "供应链总监",
    };
    return chainpilot.escape(labels[role] || role || "");
  }

  function feedback_label(value) {
    const labels = {
      Rejected: "审批拒绝",
      "Supplier Feedback": "供应商反馈",
      "Execution Feedback": "执行反馈",
      Accepted: "已采纳",
    };
    return chainpilot.escape(labels[value] || value || "");
  }

  function target_label(value) {
    const labels = { "Action Type": "建议类型", Material: "物料", Supplier: "供应商", Rule: "规则" };
    return chainpilot.escape(labels[value] || value || "");
  }

  function action_label(value) {
    return chainpilot.actionLabel ? chainpilot.actionLabel(value) : chainpilot.escape(value || "");
  }

  function clean_text(value) {
    const labels = {
      "Approval Rejected": "审批拒绝",
      "M4 verification rejection: supplier confirmation missing and cash impact below threshold.": "供应商确认不足，资金占用减少额低于阈值。",
      "Awaiting approved manual SAP execution. Production SAP auto-write is disabled.": "等待人工执行，系统不会自动写入生产 SAP。",
      "Closed by M5 mock learning snapshot.": "已进入学习快照复盘。",
      "Supplier confirmation expired before manual SAP execution.": "供应商确认已过期，未执行。",
    };
    return chainpilot.escape(labels[value] || value || "");
  }
})();
