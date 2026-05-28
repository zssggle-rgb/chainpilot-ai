(function () {
  const chainpilot = window.chainpilot || (window.chainpilot = {});
  chainpilot.escape = chainpilot.escape || function (value) {
    return frappe.utils.escape_html(value == null ? "" : String(value));
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

  frappe.pages["sap-integration-console"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
      parent: wrapper,
      title: __("SAP Integration Console"),
      single_column: true,
    });

    page.set_primary_action(__("同步全部 P0 快照"), () => run_sync(page, "all"));
    page.add_inner_button(__("测试 Mock 连接"), () => test_connection(page));
    page.add_inner_button(__("返回决策台"), () => frappe.set_route("chainpilot-ai-command-center"));
    page.main.html(`<div class="chainpilot-shell"><div class="chainpilot-loading">${__("正在加载 SAP 集成控制台...")}</div></div>`);
    load_dashboard(page);
  };

  async function load_dashboard(page) {
    try {
      const response = await frappe.call({
        method: "chainpilot_ai.sap_connector.service.get_sync_dashboard",
      });
      render_dashboard(page, response.message || {});
    } catch (error) {
      console.error(error);
      page.main.find(".chainpilot-shell").html(`<div class="chainpilot-empty">${__("无法加载 SAP 集成控制台。")}</div>`);
    }
  }

  function render_dashboard(page, data) {
    const connection = data.connection || {};
    const endpoints = data.endpoints || [];
    const jobs = data.jobs || [];
    const logs = data.logs || [];
    const counts = data.counts || {};
    const totalRows = Object.values(counts).reduce((sum, value) => sum + Number(value || 0), 0);
    const lastJob = jobs[0] || {};

    page.main.find(".chainpilot-shell").html(`
      <section class="chainpilot-hero">
        <div>
          <div class="chainpilot-eyebrow">${__("M2 Read-only SAP Layer")}</div>
          <h1 class="chainpilot-title">${__("SAP Integration Console")}</h1>
          <p class="chainpilot-subtitle">
            ${__("配置 SAP 只读 Endpoint、字段映射和同步审计。当前运行 mock adapter，用确定性数据验证未来 OData 接入的字段、日志和快照契约。")}
          </p>
        </div>
        <div class="chainpilot-meta-grid">
          ${meta_item(__("连接状态"), connection.last_test_status || __("Mock Ready"))}
          ${meta_item(__("快照记录"), chainpilot.number(totalRows))}
          ${meta_item(__("Endpoint"), chainpilot.number(endpoints.length))}
          ${meta_item(__("最近同步"), lastJob.status || __("Not Run"))}
        </div>
      </section>

      <section class="chainpilot-grid-2">
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">${__("连接配置")}</h2>
              <p class="chainpilot-panel-note">${__("M2 只读接入先验证连接契约；真实账号不得进入代码仓库。")}</p>
            </div>
            ${chainpilot.badge(connection.mode || "Mock", "blue")}
          </div>
          <div class="chainpilot-detail-grid">
            ${meta_item(__("模式"), connection.mode || "Mock")}
            ${meta_item(__("最后测试"), connection.last_test_at || "-")}
            ${meta_item(__("结果"), connection.last_test_message || __("Using ChainPilot deterministic mock SAP adapter."))}
          </div>
          <div style="margin-top: 14px;">
            <button class="chainpilot-link-button" data-test-connection="1">${__("测试 Mock 连接")}</button>
            <button class="chainpilot-filter" data-sync-endpoint="all">${__("同步全部 P0 快照")}</button>
          </div>
        </div>

        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">${__("Snapshot 覆盖")}</h2>
              <p class="chainpilot-panel-note">${__("四类 P0 对象先落本地快照，供优化和 Agent 读取。")}</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${snapshot_count(__("物料主数据"), counts["SAP Material Snapshot"])}
            ${snapshot_count(__("库存"), counts["SAP Inventory Snapshot"])}
            ${snapshot_count(__("采购申请 PR"), counts["SAP PR Line"])}
            ${snapshot_count(__("采购订单 PO"), counts["SAP PO Line"])}
          </div>
        </div>
      </section>

      <section class="chainpilot-panel" style="margin-top: 18px;">
        <div class="chainpilot-panel-header">
          <div>
            <h2 class="chainpilot-panel-title">${__("Endpoint 配置")}</h2>
            <p class="chainpilot-panel-note">${__("每个 Endpoint 绑定目标 DocType、EntitySet 和字段映射。")}</p>
          </div>
        </div>
        <div class="chainpilot-action-list">
          ${endpoints.map(endpoint_card).join("") || empty_state(__("尚未配置 Endpoint。"))}
        </div>
      </section>

      <section class="chainpilot-grid-2">
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">${__("同步任务")}</h2>
              <p class="chainpilot-panel-note">${__("成功、失败、重试和同步数量都要可审计。")}</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${jobs.map(job_row).join("") || empty_state(__("尚无同步任务。"))}
          </div>
        </div>
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">${__("API 日志")}</h2>
              <p class="chainpilot-panel-note">${__("测试连接和同步请求都保留摘要，避免暴露密码和完整业务数据。")}</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${logs.map(log_row).join("") || empty_state(__("尚无 API 日志。"))}
          </div>
        </div>
      </section>
    `);

    page.main.find("[data-test-connection]").on("click", () => test_connection(page));
    page.main.find("[data-sync-endpoint]").on("click", (event) => {
      run_sync(page, $(event.currentTarget).data("sync-endpoint"));
    });
  }

  async function test_connection(page) {
    frappe.show_alert({ message: __("正在测试 mock 连接..."), indicator: "blue" });
    const response = await frappe.call({
      method: "chainpilot_ai.sap_connector.service.test_connection_rpc",
      args: { mode: "mock" },
    });
    const result = response.message || {};
    frappe.show_alert({
      message: result.ok ? __("Mock 连接可用") : __("连接测试未通过"),
      indicator: result.ok ? "green" : "orange",
    });
    load_dashboard(page);
  }

  async function run_sync(page, endpointName) {
    frappe.show_alert({ message: __("正在执行只读 mock 同步..."), indicator: "blue" });
    const response = await frappe.call({
      method: "chainpilot_ai.sap_connector.service.run_mock_sync",
      args: { endpoint_name: endpointName },
    });
    const result = response.message || {};
    frappe.show_alert({
      message: __("同步完成：{0} 行", [chainpilot.number(result.rows_upserted || 0)]),
      indicator: result.ok ? "green" : "orange",
    });
    load_dashboard(page);
  }

  function endpoint_card(endpoint) {
    return `
      <div class="chainpilot-action-card">
        <div class="chainpilot-action-main">
          <div class="chainpilot-action-id">${chainpilot.escape(endpoint.business_object || "")}</div>
          <div class="chainpilot-action-title">${chainpilot.escape(endpoint.endpoint_name || "")}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(endpoint.entity_set || "")}</div>
        </div>
        <div>${metric(chainpilot.escape(endpoint.target_doctype || "-"), __("目标 DocType"))}</div>
        <div>${metric(endpoint.enabled ? __("Enabled") : __("Disabled"), __("状态"))}</div>
        <div>
          <button class="chainpilot-link-button" data-sync-endpoint="${chainpilot.escape(endpoint.endpoint_name || "")}">${__("同步")}</button>
        </div>
      </div>
    `;
  }

  function job_row(job) {
    const tone = job.status === "Success" ? "green" : job.status === "Failed" ? "red" : "blue";
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.escape(job.endpoint || job.job_id || "")}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(job.started_at || "")}</div>
        </div>
        <div>
          ${chainpilot.badge(job.status || "-", tone)}
          <div class="chainpilot-metric">${chainpilot.number(job.rows_upserted || 0)}</div>
          <div class="chainpilot-metric-label">${__("upserted")}</div>
        </div>
      </div>
    `;
  }

  function log_row(log) {
    const failed = Number(log.status_code || 0) >= 400 || log.error_message;
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.escape(log.endpoint || log.api_log_id || "")}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(log.response_summary || log.error_message || "")}</div>
        </div>
        <div>
          ${chainpilot.badge(log.status_code || "0", failed ? "red" : "green")}
          <div class="chainpilot-metric">${chainpilot.number(log.duration_ms || 0)}ms</div>
        </div>
      </div>
    `;
  }

  function snapshot_count(label, value) {
    return `<div class="chainpilot-risk-row"><div class="chainpilot-action-title">${chainpilot.escape(label)}</div><div class="chainpilot-value">${chainpilot.number(value || 0)}</div></div>`;
  }

  function meta_item(label, value) {
    return `<div class="chainpilot-meta-item"><div class="chainpilot-label">${chainpilot.escape(label)}</div><div class="chainpilot-value">${chainpilot.escape(value)}</div></div>`;
  }

  function metric(value, label) {
    return `<div><div class="chainpilot-metric">${value}</div><div class="chainpilot-metric-label">${chainpilot.escape(label)}</div></div>`;
  }

  function empty_state(message) {
    return `<div class="chainpilot-empty">${chainpilot.escape(message)}</div>`;
  }
})();
