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
  chainpilot.statusLabel = chainpilot.statusLabel || function (value) {
    const labels = {
      Success: "成功",
      Failed: "失败",
      "Not Run": "未运行",
      "Mock Ready": "模拟连接可用",
      MOCK_READY: "模拟连接可用",
      DRY_RUN: "配置校验",
      "Dry Run": "配置校验",
      Ready: "已就绪",
      Pending: "待处理",
    };
    return labels[value] || value || "";
  };

  frappe.pages["sap-integration-console"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
      parent: wrapper,
      title: "SAP 连接",
      single_column: true,
    });

    page.set_primary_action("同步", () => run_sync(page, "all"));
    page.add_inner_button("测试连接", () => test_connection(page));
    page.add_inner_button("返回", () => frappe.set_route("chainpilot-ai-command-center"));
    page.main.html(`<div class="chainpilot-shell"><div class="chainpilot-loading">正在加载 SAP 连接...</div></div>`);
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
      page.main.find(".chainpilot-shell").html(`<div class="chainpilot-empty">无法加载 SAP 连接。</div>`);
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
          <div class="chainpilot-eyebrow">只读接入</div>
          <h1 class="chainpilot-title">SAP 连接</h1>
          <p class="chainpilot-subtitle">
            当前使用模拟连接。接入真实 SAP 时，在这里配置接口地址、只读技术用户、接口、字段映射、同步任务和日志。
          </p>
        </div>
        <div class="chainpilot-meta-grid">
          ${meta_item("连接状态", chainpilot.statusLabel(connection.last_test_status || "Mock Ready"))}
          ${meta_item("快照记录", chainpilot.number(totalRows))}
          ${meta_item("接口数量", chainpilot.number(endpoints.length))}
          ${meta_item("最近同步", chainpilot.statusLabel(lastJob.status || "Not Run"))}
        </div>
      </section>

      <section class="chainpilot-grid-2">
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">连接配置</h2>
              <p class="chainpilot-panel-note">当前为模拟连接；真实账号通过平台密码字段或环境变量配置。</p>
            </div>
            ${chainpilot.badge(connection_mode_label(connection.mode), "blue")}
          </div>
          <div class="chainpilot-detail-grid">
            ${meta_item("模式", connection_mode_label(connection.mode))}
            ${meta_item("最后测试", connection.last_test_at || "-")}
            ${meta_item("测试结果", connection_message(connection))}
          </div>
          <div style="margin-top: 14px;">
            <button class="chainpilot-link-button" data-test-connection="1">测试连接</button>
            <button class="chainpilot-filter" data-sync-endpoint="all">同步</button>
          </div>
        </div>

        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">快照覆盖</h2>
              <p class="chainpilot-panel-note">物料、库存、采购申请和采购订单先同步到本地快照。</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${snapshot_count("物料主数据", counts["SAP Material Snapshot"])}
            ${snapshot_count("库存", counts["SAP Inventory Snapshot"])}
            ${snapshot_count("采购申请", counts["SAP PR Line"])}
            ${snapshot_count("采购订单", counts["SAP PO Line"])}
          </div>
        </div>
      </section>

      <section class="chainpilot-panel" style="margin-top: 18px;">
        <div class="chainpilot-panel-header">
          <div>
            <h2 class="chainpilot-panel-title">接口配置</h2>
            <p class="chainpilot-panel-note">每个接口绑定业务对象、SAP 实体集、目标快照表和字段映射。</p>
          </div>
        </div>
        <div class="chainpilot-action-list">
          ${endpoints.map(endpoint_card).join("") || empty_state("尚未配置接口。")}
        </div>
      </section>

      <section class="chainpilot-grid-2">
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">同步任务</h2>
              <p class="chainpilot-panel-note">记录同步状态、数量和错误摘要。</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${jobs.map(job_row).join("") || empty_state("尚无同步任务。")}
          </div>
        </div>
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">接口日志</h2>
              <p class="chainpilot-panel-note">保留请求摘要、响应摘要、耗时和错误信息。</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${logs.map(log_row).join("") || empty_state("尚无接口日志。")}
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
    frappe.show_alert({ message: "正在测试模拟连接...", indicator: "blue" });
    const response = await frappe.call({
      method: "chainpilot_ai.sap_connector.service.test_connection_rpc",
      args: { mode: "mock" },
    });
    const result = response.message || {};
    frappe.show_alert({
      message: result.ok ? "模拟连接可用" : "连接测试未通过",
      indicator: result.ok ? "green" : "orange",
    });
    load_dashboard(page);
  }

  async function run_sync(page, endpointName) {
    frappe.show_alert({ message: "正在执行只读模拟同步...", indicator: "blue" });
    const response = await frappe.call({
      method: "chainpilot_ai.sap_connector.service.run_mock_sync",
      args: { endpoint_name: endpointName },
    });
    const result = response.message || {};
    frappe.show_alert({
      message: `同步完成：${chainpilot.number(result.rows_upserted || 0)} 行`,
      indicator: result.ok ? "green" : "orange",
    });
    load_dashboard(page);
  }

  function endpoint_card(endpoint) {
    return `
      <div class="chainpilot-action-card">
        <div class="chainpilot-action-main">
          <div class="chainpilot-action-id">${chainpilot.escape(object_label(endpoint.business_object))}</div>
          <div class="chainpilot-action-title">${chainpilot.escape(endpoint_label(endpoint.endpoint_name))}</div>
          <div class="chainpilot-action-subtitle">标准接口实体已绑定</div>
        </div>
        <div>${metric(snapshot_label(endpoint.target_doctype), "目标快照表")}</div>
        <div>${metric(endpoint.enabled ? "启用" : "停用", "状态")}</div>
        <div>
          <button class="chainpilot-link-button" data-sync-endpoint="${chainpilot.escape(endpoint.endpoint_name || "")}">同步</button>
        </div>
      </div>
    `;
  }

  function job_row(job) {
    const tone = job.status === "Success" ? "green" : job.status === "Failed" ? "red" : "blue";
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.escape(endpoint_label(job.endpoint) || job.job_id || "")}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(job.started_at || "")}</div>
        </div>
        <div>
          ${chainpilot.badge(chainpilot.statusLabel(job.status) || "-", tone)}
          <div class="chainpilot-metric">${chainpilot.number(job.rows_upserted || 0)}</div>
          <div class="chainpilot-metric-label">写入/更新</div>
        </div>
      </div>
    `;
  }

  function log_row(log) {
    const failed = Number(log.status_code || 0) >= 400 || log.error_message;
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.escape(endpoint_label(log.endpoint) || log.api_log_id || "")}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(log_summary(log))}</div>
        </div>
        <div>
          ${chainpilot.badge(log.status_code || "0", failed ? "red" : "green")}
          <div class="chainpilot-metric">${chainpilot.number(log.duration_ms || 0)} 毫秒</div>
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

  function endpoint_label(value) {
    const labels = {
      material_master: "物料主数据",
      inventory_snapshots: "库存快照",
      purchase_requisition_items: "采购申请行",
      purchase_order_items: "采购订单行",
      all: "全部接口",
    };
    return labels[value] || value || "";
  }

  function object_label(value) {
    const labels = {
      Material: "物料",
      Inventory: "库存",
      PR: "采购申请",
      PO: "采购订单",
    };
    return labels[value] || value || "";
  }

  function snapshot_label(value) {
    const labels = {
      "SAP Material Snapshot": "物料快照",
      "SAP Inventory Snapshot": "库存快照",
      "SAP PR Line": "采购申请快照",
      "SAP PO Line": "采购订单快照",
    };
    return labels[value] || value || "-";
  }

  function connection_message(connection) {
    if ((connection.last_test_status || "") === "Mock Ready") return "模拟连接可用";
    if ((connection.last_test_status || "") === "Dry Run") return "真实连接未配置，当前仅校验配置";
    return connection.last_test_message || "模拟连接可用";
  }

  function connection_mode_label(value) {
    const labels = {
      mock: "模拟连接",
      Mock: "模拟连接",
      OData: "真实连接",
      "Dry Run": "配置校验",
    };
    return labels[value] || value || "-";
  }

  function log_summary(log) {
    if (log.error_message) return "接口请求失败，错误摘要已记录。";
    if (log.response_summary) return "接口返回摘要已记录。";
    return "接口请求已记录。";
  }
})();
