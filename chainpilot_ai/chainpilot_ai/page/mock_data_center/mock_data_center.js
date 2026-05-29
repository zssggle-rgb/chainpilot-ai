(() => {
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
  chainpilot.currency = chainpilot.currency || function (value) {
    return Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 0 });
  };
  chainpilot.percent = chainpilot.percent || function (value) {
    return `${Number(value || 0).toFixed(1)}%`;
  };
  chainpilot.badge = chainpilot.badge || function (label, tone = "neutral") {
    return `<span class="chainpilot-badge ${tone}">${chainpilot.escape(label)}</span>`;
  };

  frappe.pages["mock-data-center"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
      parent: wrapper,
      title: "模拟数据中心",
      single_column: true,
    });

    page.set_primary_action("运行回测", () => frappe.set_route("strategy-optimization-center"));
    page.set_secondary_action("采购决策", () => frappe.set_route("chainpilot-ai-command-center"));
    page.add_inner_button("策略优化", () => frappe.set_route("strategy-optimization-center"));
    page.add_inner_button("SAP 连接", () => frappe.set_route("sap-integration-console"));
    page.main.html(`<div class="chainpilot-shell"><div class="chainpilot-loading">正在加载模拟数据...</div></div>`);
    load_dashboard(page);
  };

  async function load_dashboard(page) {
    try {
      const response = await frappe.call({
        method: "chainpilot_ai.snapshots.mock_dashboard.get_mock_data_dashboard",
        args: { history_days: 120 },
      });
      render_dashboard(page, response.message || {});
    } catch (error) {
      console.error(error);
      page.main.find(".chainpilot-shell").html(`<div class="chainpilot-empty">无法加载模拟数据。</div>`);
    }
  }

  function render_dashboard(page, data) {
    const counts = data.counts || {};
    const cash = data.cash_summary || {};
    const best = (data.backtests || []).find((row) => row.strategy_id === data.recommended_strategy_id) || (data.backtests || [])[0] || {};
    const totalRows = Object.values(counts).reduce((sum, value) => sum + Number(value || 0), 0);
    page.main.find(".chainpilot-shell").html(`
      <section class="chainpilot-hero">
        <div>
          <div class="chainpilot-eyebrow">生产约束验收集</div>
          <h1 class="chainpilot-title">模拟数据中心</h1>
          <p class="chainpilot-subtitle">当前模拟数据用于验证真实算法：冻结期、最小采购量、最小包装量、服务水平、供应商确认、同物料多单联动和审批容量都必须在这里体现。</p>
        </div>
        <div class="chainpilot-meta-grid">
          ${meta_item("快照编号", (data.snapshot || {}).snapshot_id || "-")}
          ${meta_item("明细行数", chainpilot.number(totalRows))}
          ${meta_item("求解器", solver_label(cash.solver_name))}
          ${meta_item("求解状态", status_label(cash.solver_status))}
        </div>
      </section>

      <section class="chainpilot-kpi-grid">
        ${kpi_card("物料", counts.materials)}
        ${kpi_card("采购申请", counts.pr_lines)}
        ${kpi_card("采购订单", counts.po_lines)}
        ${kpi_card("需求与历史", Number(counts.planned_demands || 0) + Number(counts.consumption_history || 0))}
      </section>

      <section class="chainpilot-kpi-grid">
        ${kpi_card("缺料召回率", chainpilot.percent((best.recall_rate || 0) * 100))}
        ${kpi_card("高风险准确率", chainpilot.percent((best.precision_rate || 0) * 100))}
        ${kpi_card("硬约束违规", chainpilot.number(best.hard_constraint_violations || 0))}
        ${kpi_card("预计兑现资金", chainpilot.currency(best.realized_cash_total || 0))}
      </section>

      <section class="chainpilot-grid-2">
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">约束覆盖</h2>
            <p class="chainpilot-panel-note">这些不是文案说明，而是当前快照里实际存在的验收案例。</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${(data.constraint_cases || []).map(constraint_row).join("")}
          </div>
        </div>

        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">阻断原因</h2>
              <p class="chainpilot-panel-note">算法不会把违规动作塞进建议清单。</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${(data.blocked_reasons || []).map(reason_row).join("")}
          </div>
        </div>
      </section>

      <section class="chainpilot-panel" style="margin-top: 18px;">
        <div class="chainpilot-panel-header">
          <div>
            <h2 class="chainpilot-panel-title">已选资金优化动作</h2>
            <p class="chainpilot-panel-note">这些动作由整数规划求解器在同物料约束和审批容量下选择。</p>
          </div>
          ${chainpilot.badge(`${chainpilot.number(cash.selected_actions || 0)} 条`, "green")}
        </div>
        <div class="chainpilot-action-list">
          ${(data.selected_cash_rows || []).map(cash_row).join("")}
        </div>
      </section>

      <section class="chainpilot-grid-2">
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">缺料风险标签</h2>
            <p class="chainpilot-panel-note">用于验证缺料预测在模拟历史上的命中效果。</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${(data.shortage_rows || []).map(shortage_row).join("")}
          </div>
        </div>
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">样例数据</h2>
              <p class="chainpilot-panel-note">展示 SAP 快照行，便于核对字段和业务含义。</p>
            </div>
          </div>
          ${sample_table(data.sample_tables || {})}
        </div>
      </section>
    `);
  }

  function constraint_row(row) {
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.escape(row.case)}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape((row.examples || []).join("、"))}</div>
        </div>
        ${chainpilot.badge(row.evidence || "已覆盖", "blue")}
      </div>
    `;
  }

  function reason_row(row) {
    const tone = row.label === "通过" ? "green" : "amber";
    return `
      <div class="chainpilot-risk-row">
        <div class="chainpilot-action-title">${chainpilot.escape(row.label)}</div>
        <div class="chainpilot-value">${chainpilot.number(row.count)}</div>
        ${chainpilot.badge(row.label, tone)}
      </div>
    `;
  }

  function cash_row(row) {
    return `
      <div class="chainpilot-action-card">
        <div class="chainpilot-action-main">
          <div class="chainpilot-action-id">${sap_object_label(row.sap_object_type)} ${chainpilot.escape(row.sap_doc_no)}/${chainpilot.escape(row.sap_item_no)}</div>
          <div class="chainpilot-action-title">${chainpilot.escape(row.material_code)} · ${action_label(row.action_type)}</div>
          <div class="chainpilot-action-subtitle">余量 ${chainpilot.number(row.material_headroom || 0)}，占用 ${chainpilot.number(row.capacity_consumed || 0)}</div>
        </div>
        ${metric_block("资金改善", chainpilot.currency(row.cash_impact))}
        ${metric_block("风险", chainpilot.percent((row.risk_after || 0) * 100))}
        <div>${chainpilot.badge(level_label(row.recommendation_level), row.recommendation_level === "L1_AUTO_RECOMMEND" ? "green" : "blue")}</div>
      </div>
    `;
  }

  function shortage_row(row) {
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.escape(row.material_code)}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(row.shortage_date_p50 || "-")} · 缺口 ${chainpilot.number(row.shortage_qty_p90 || 0)}</div>
        </div>
        ${chainpilot.badge(chainpilot.percent((row.shortage_probability_14d || 0) * 100), "red")}
      </div>
    `;
  }

  function sample_table(tables) {
    const rows = (tables.pr_lines || []).slice(0, 6);
    return `
      <div class="chainpilot-table">
        <div class="chainpilot-table-row head"><span>单据</span><span>物料</span><span>数量</span><span>日期</span></div>
        ${rows.map((row) => `<div class="chainpilot-table-row"><span>${chainpilot.escape(row.pr_no)}</span><span>${chainpilot.escape(row.material_code)}</span><span>${chainpilot.number(row.open_qty)}</span><span>${chainpilot.escape(row.delivery_date)}</span></div>`).join("")}
      </div>
    `;
  }

  function meta_item(label, value) {
    return `<div class="chainpilot-meta-item"><div class="chainpilot-label">${chainpilot.escape(label)}</div><div class="chainpilot-value">${chainpilot.escape(value)}</div></div>`;
  }

  function kpi_card(label, value) {
    return `<div class="chainpilot-kpi"><div class="chainpilot-label">${chainpilot.escape(label)}</div><strong>${chainpilot.escape(value)}</strong></div>`;
  }

  function metric_block(label, value) {
    return `<div><div class="chainpilot-metric">${chainpilot.escape(value)}</div><div class="chainpilot-metric-label">${chainpilot.escape(label)}</div></div>`;
  }

  function action_label(value) {
    const labels = { CANCEL_PR_LINE: "取消采购申请", REDUCE_PR_QTY: "下调采购申请", DELAY_UNCONFIRMED_PO: "延期采购订单" };
    return labels[value] || chainpilot.escape(value || "-");
  }

  function sap_object_label(value) {
    const labels = { PR: "采购申请", PO: "采购订单" };
    return labels[value] || chainpilot.escape(value || "-");
  }

  function solver_label(value) {
    const labels = { "HiGHS MILP": "混合整数规划", "精确整数枚举": "精确整数枚举" };
    return labels[value] || value || "-";
  }

  function status_label(value) {
    const labels = { OPTIMAL: "最优", FEASIBLE: "可行", TRUNCATED_OPTIMAL: "截断最优" };
    return labels[value] || value || "-";
  }

  function level_label(value) {
    const labels = { L1_AUTO_RECOMMEND: "常规审批", L2_REVIEW: "计划复核", L3_SUPPLIER_CONFIRM: "供应商确认" };
    return labels[value] || value || "-";
  }
})();
