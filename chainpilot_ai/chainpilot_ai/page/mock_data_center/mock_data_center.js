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
      title: "供应计划验证工作台",
      single_column: true,
    });

    page.set_primary_action("运行优化", () => frappe.set_route("strategy-optimization-center"));
    page.set_secondary_action("采购决策", () => frappe.set_route("chainpilot-ai-command-center"));
    page.add_inner_button("SAP 连接", () => frappe.set_route("sap-integration-console"));
    page.add_inner_button("回测中心", () => frappe.set_route("strategy-optimization-center"));
    page.main.html(`<div class="chainpilot-shell"><div class="chainpilot-loading">正在加载计划场景...</div></div>`);
    load_dashboard(page);
  };

  async function load_dashboard(page) {
    try {
      const response = await frappe.call({
        method: "chainpilot_ai.snapshots.mock_dashboard.get_mock_data_dashboard",
        args: { history_days: 45 },
      });
      render_dashboard(page, response.message || {});
    } catch (error) {
      console.error(error);
      page.main.find(".chainpilot-shell").html(`<div class="chainpilot-empty">无法加载计划场景。</div>`);
    }
  }

  function render_dashboard(page, data) {
    const counts = data.counts || {};
    const planning = data.planning_workbench || {};
    const scenario = planning.scenario || {};
    const cash = data.cash_summary || {};
    const shortage = data.shortage_summary || {};
    const best = (data.backtests || []).find((row) => row.strategy_id === data.recommended_strategy_id) || (data.backtests || [])[0] || {};
    const totalRows = Object.values(counts).reduce((sum, value) => sum + Number(value || 0), 0);
    const relation = relationship_score(data.relationship_checks || []);
    const procurement = summary_by_label(data.business_summary || [], "采购未清");
    const supplier = summary_by_label(data.business_summary || [], "需求与履约");
    const inventoryTable = find_table(data.sample_tables || [], "库存与需求");
    const materialTable = find_table(data.sample_tables || [], "物料与计划参数");
    const prTable = find_table(data.sample_tables || [], "采购申请");
    const poTable = find_table(data.sample_tables || [], "采购订单");
    const supplierTable = find_table(data.sample_tables || [], "供应商履约");
    const demandTable = find_table(data.sample_tables || [], "需求与成品关联");

    page.main.find(".chainpilot-shell").html(`
      <div class="chainpilot-plan-layout">
        <aside class="chainpilot-plan-sidebar">
          <div class="chainpilot-scenario-card">
            <div class="chainpilot-eyebrow">计划场景</div>
            <h2>${chainpilot.escape(scenario.name || "基准模拟账套")}</h2>
            <div class="chainpilot-scenario-fields">
              ${scenario_item("计划周期", scenario.horizon || "未来 45 天")}
              ${scenario_item("计划层级", scenario.planning_level || "物料 / 工厂 / 供应商")}
              ${scenario_item("工厂", scenario.plants || "-")}
              ${scenario_item("产品线", scenario.product_lines || "-")}
            </div>
            <button type="button" class="chainpilot-primary-command" data-route="strategy-optimization-center">运行优化</button>
            <button type="button" class="chainpilot-secondary-command" data-route="sap-integration-console">配置 SAP 接入</button>
          </div>

          <div class="chainpilot-side-section">
            <h3>异常队列</h3>
            ${(planning.exception_pillars || []).map(exception_tile).join("")}
          </div>

          <div class="chainpilot-side-section">
            <h3>数据范围</h3>
            ${side_metric("明细行数", `${chainpilot.number(totalRows)} 行`)}
            ${side_metric("物料", `${chainpilot.number(counts.materials || 0)} 个`)}
            ${side_metric("采购申请", `${chainpilot.number(counts.pr_lines || 0)} 行`)}
            ${side_metric("采购订单", `${chainpilot.number(counts.po_lines || 0)} 行`)}
          </div>
        </aside>

        <main class="chainpilot-plan-main">
          <section class="chainpilot-plan-header">
            <div>
              <div class="chainpilot-eyebrow">供应计划</div>
              <h1 class="chainpilot-title">供应计划验证工作台</h1>
            </div>
            <div class="chainpilot-plan-status">
              ${chainpilot.badge(`关联完整率 ${chainpilot.percent(relation * 100)}`, relation >= 1 ? "green" : "amber")}
              ${chainpilot.badge(`求解状态 ${status_label(cash.solver_status)}`, "blue")}
              ${chainpilot.badge(`硬约束违规 ${chainpilot.number(best.hard_constraint_violations || 0)}`, (best.hard_constraint_violations || 0) ? "red" : "green")}
            </div>
          </section>

          <section class="chainpilot-plan-kpis">
            ${planning_kpi("缺料风险物料", chainpilot.number((data.shortage_rows || []).length), "未来 14 天", "red")}
            ${planning_kpi("预计减少资金占用", chainpilot.currency(cash.cash_release_total || 0), `${chainpilot.number(cash.selected_actions || 0)} 条建议`, "green")}
            ${planning_kpi("采购未清", procurement.value || "-", procurement.detail || "采购申请与采购订单", "blue")}
            ${planning_kpi("供应履约", supplier.detail || "-", "历史交付表现", "amber")}
          </section>

          <section class="chainpilot-planner-workspace">
            <nav class="chainpilot-plan-tabs" role="tablist" aria-label="供应计划工作区">
              ${tab_button("balance", "供需平衡", "周度")}
              ${tab_button("inventory", "库存策略", `${chainpilot.number(counts.materials || 0)} 物料`)}
              ${tab_button("procurement", "采购计划", `${chainpilot.number((counts.pr_lines || 0) + (counts.po_lines || 0))} 行`)}
              ${tab_button("supplier", "供应商履约", `${chainpilot.number(counts.supplier_performance || 0)} 条`)}
              ${tab_button("actions", "优化建议", `${chainpilot.number(cash.selected_actions || 0)} 条`)}
              ${tab_button("validation", "数据校验", chainpilot.percent(relation * 100))}
            </nav>

            <div class="chainpilot-plan-panel active" data-plan-panel="balance" role="tabpanel">
              <div class="chainpilot-plan-grid">
                <section class="chainpilot-plan-card span-2">
                  <div class="chainpilot-card-head">
                    <h2>周度供需平衡</h2>
                    ${chainpilot.badge("未来 6 周", "neutral")}
                  </div>
                  ${weekly_supply_chart(planning.weekly_supply_plan || [])}
                </section>
                <section class="chainpilot-plan-card">
                  <div class="chainpilot-card-head">
                    <h2>高风险物料</h2>
                    ${chainpilot.badge(`${chainpilot.number((data.shortage_rows || []).length)} 条`, "red")}
                  </div>
                  <div class="chainpilot-compact-list">
                    ${(data.shortage_rows || []).slice(0, 8).map(shortage_row).join("")}
                  </div>
                </section>
              </div>
              <section class="chainpilot-plan-card chainpilot-section-gap">
                <div class="chainpilot-card-head">
                  <h2>需求与成品关联</h2>
                  ${chainpilot.badge(`${chainpilot.number(demandTable.count || 0)} 行`, "neutral")}
                </div>
                ${business_table(demandTable)}
              </section>
            </div>

            <div class="chainpilot-plan-panel" data-plan-panel="inventory" role="tabpanel">
              <div class="chainpilot-plan-grid">
                <section class="chainpilot-plan-card">
                  <div class="chainpilot-card-head">
                    <h2>库存策略分层</h2>
                  </div>
                  ${inventory_policy_table(planning.inventory_policy_rows || [])}
                </section>
                <section class="chainpilot-plan-card span-2">
                  <div class="chainpilot-card-head">
                    <h2>物料库存工作表</h2>
                    ${chainpilot.badge(`${chainpilot.number(inventoryTable.count || 0)} 行`, "neutral")}
                  </div>
                  ${business_table(inventoryTable)}
                </section>
              </div>
              <section class="chainpilot-plan-card chainpilot-section-gap">
                <div class="chainpilot-card-head">
                  <h2>物料与计划参数</h2>
                  ${chainpilot.badge(`${chainpilot.number(materialTable.count || 0)} 行`, "neutral")}
                </div>
                ${business_table(materialTable)}
              </section>
            </div>

            <div class="chainpilot-plan-panel" data-plan-panel="procurement" role="tabpanel">
              <div class="chainpilot-plan-grid two">
                <section class="chainpilot-plan-card">
                  <div class="chainpilot-card-head">
                    <h2>采购申请</h2>
                    ${chainpilot.badge(`${chainpilot.number(prTable.count || 0)} 行`, "blue")}
                  </div>
                  ${business_table(prTable)}
                </section>
                <section class="chainpilot-plan-card">
                  <div class="chainpilot-card-head">
                    <h2>采购订单</h2>
                    ${chainpilot.badge(`${chainpilot.number(poTable.count || 0)} 行`, "blue")}
                  </div>
                  ${business_table(poTable)}
                </section>
              </div>
            </div>

            <div class="chainpilot-plan-panel" data-plan-panel="supplier" role="tabpanel">
              <section class="chainpilot-plan-card">
                <div class="chainpilot-card-head">
                  <h2>供应商履约记录</h2>
                  ${chainpilot.badge(`${chainpilot.number(supplierTable.count || 0)} 条`, "amber")}
                </div>
                ${business_table(supplierTable)}
              </section>
            </div>

            <div class="chainpilot-plan-panel" data-plan-panel="actions" role="tabpanel">
              <div class="chainpilot-plan-grid two">
                <section class="chainpilot-plan-card">
                  <div class="chainpilot-card-head">
                    <h2>资金占用处理清单</h2>
                    ${chainpilot.badge(`${chainpilot.number(cash.selected_actions || 0)} 条入选`, "green")}
                  </div>
                  <div class="chainpilot-action-list">
                    ${(data.selected_cash_rows || []).map(cash_row).join("")}
                  </div>
                </section>
                <section class="chainpilot-plan-card">
                  <div class="chainpilot-card-head">
                    <h2>不可处理原因</h2>
                  </div>
                  <div class="chainpilot-distribution-grid compact">
                    ${(data.blocked_reasons || []).map(reason_tile).join("")}
                  </div>
                </section>
              </div>
            </div>

            <div class="chainpilot-plan-panel" data-plan-panel="validation" role="tabpanel">
              <div class="chainpilot-plan-grid two">
                <section class="chainpilot-plan-card">
                  <div class="chainpilot-card-head">
                    <h2>跨表关联校验</h2>
                    ${chainpilot.badge(`完整率 ${chainpilot.percent(relation * 100)}`, relation >= 1 ? "green" : "amber")}
                  </div>
                  <div class="chainpilot-compact-list">
                    ${(data.relationship_checks || []).map(check_row).join("")}
                  </div>
                </section>
                <section class="chainpilot-plan-card">
                  <div class="chainpilot-card-head">
                    <h2>约束覆盖</h2>
                  </div>
                  <div class="chainpilot-compact-list">
                    ${(data.constraint_cases || []).map(constraint_row).join("")}
                  </div>
                </section>
              </div>
              <section class="chainpilot-plan-card chainpilot-section-gap">
                <div class="chainpilot-card-head">
                  <h2>审计信息</h2>
                </div>
                <div class="chainpilot-audit-grid">
                  ${audit_item("快照编号", (data.snapshot || {}).snapshot_id || "-")}
                  ${audit_item("快照时间", (data.snapshot || {}).snapshot_time || "-")}
                  ${audit_item("工厂范围", (data.snapshot || {}).plant_scope || "-")}
                  ${audit_item("求解器", cash.solver_name || "-")}
                  ${audit_item("求解状态", status_label(cash.solver_status))}
                  ${audit_item("MIP Gap", cash.mip_gap == null ? "-" : chainpilot.number(cash.mip_gap, 4))}
                  ${audit_item("预测 WAPE", shortage.avg_forecast_wape == null ? "-" : chainpilot.percent(shortage.avg_forecast_wape * 100))}
                  ${audit_item("推荐策略", data.recommended_strategy_name || "-")}
                </div>
              </section>
            </div>
          </section>
        </main>
      </div>
    `);

    bind_plan_tabs(page);
    bind_route_buttons(page);
  }

  function scenario_item(label, value) {
    return `<div><span>${chainpilot.escape(label)}</span><strong>${chainpilot.escape(value)}</strong></div>`;
  }

  function exception_tile(row) {
    return `
      <div class="chainpilot-exception-tile">
        <strong>${chainpilot.number(row.value || 0)}</strong>
        <span>${chainpilot.escape(row.label)}</span>
        <small>${chainpilot.escape(row.detail)}</small>
      </div>
    `;
  }

  function side_metric(label, value) {
    return `<div class="chainpilot-side-metric"><span>${chainpilot.escape(label)}</span><strong>${chainpilot.escape(value)}</strong></div>`;
  }

  function planning_kpi(label, value, detail, tone) {
    return `
      <article class="chainpilot-planning-kpi ${tone}">
        <span>${chainpilot.escape(label)}</span>
        <strong>${chainpilot.escape(value)}</strong>
        <small>${chainpilot.escape(detail)}</small>
      </article>
    `;
  }

  function tab_button(key, label, count, active = key === "balance") {
    return `
      <button class="chainpilot-plan-tab ${active ? "active" : ""}" type="button" data-plan-target="${chainpilot.escape(key)}" role="tab" aria-selected="${active ? "true" : "false"}">
        <span>${chainpilot.escape(label)}</span>
        <small>${chainpilot.escape(count)}</small>
      </button>
    `;
  }

  function weekly_supply_chart(rows) {
    if (!rows.length) {
      return `<div class="chainpilot-empty">暂无周度供需数据。</div>`;
    }
    const maxValue = Math.max(
      1,
      ...rows.flatMap((row) => [
        Number(row.demand_qty || 0),
        Number(row.firm_supply_qty || 0),
        Number(row.planned_supply_qty || 0),
        Math.abs(Number(row.net_gap_qty || 0)),
      ])
    );
    return `
      <div class="chainpilot-week-chart">
        <div class="chainpilot-week-head">
          <span>周期</span>
          <span>需求</span>
          <span>已确认供给</span>
          <span>计划供给</span>
          <span>净缺口</span>
        </div>
        ${rows.map((row) => weekly_row(row, maxValue)).join("")}
      </div>
    `;
  }

  function weekly_row(row, maxValue) {
    const gap = Number(row.net_gap_qty || 0);
    return `
      <div class="chainpilot-week-row">
        <div class="chainpilot-week-label">
          <strong>${chainpilot.escape(row.label)}</strong>
          <span>${chainpilot.escape(row.date_range)}</span>
        </div>
        ${bar_cell(row.demand_qty, maxValue, "demand")}
        ${bar_cell(row.firm_supply_qty, maxValue, "firm")}
        ${bar_cell(row.planned_supply_qty, maxValue, "planned")}
        ${bar_cell(Math.abs(gap), maxValue, gap > 0 ? "gap" : "covered", gap > 0 ? "缺口" : "覆盖")}
      </div>
    `;
  }

  function bar_cell(value, maxValue, tone, prefix = "") {
    const width = Math.max(4, Math.round((Number(value || 0) / maxValue) * 100));
    return `
      <div class="chainpilot-bar-cell">
        <div class="chainpilot-bar-track"><i class="${chainpilot.escape(tone)}" style="width: ${width}%"></i></div>
        <span>${chainpilot.escape(prefix ? `${prefix} ${chainpilot.number(value)}` : chainpilot.number(value))}</span>
      </div>
    `;
  }

  function inventory_policy_table(rows) {
    if (!rows.length) {
      return `<div class="chainpilot-empty">暂无库存策略数据。</div>`;
    }
    return `
      <div class="chainpilot-policy-list">
        ${rows.map((row) => `
          <div class="chainpilot-policy-row">
            <div>
              <strong>${chainpilot.escape(row.segment)}</strong>
              <span>${chainpilot.number(row.materials)} 个物料</span>
            </div>
            <div>${chainpilot.number(row.avg_coverage_days, 1)} 天</div>
            <div>${chainpilot.number(row.low_coverage)} / ${chainpilot.number(row.high_coverage)}</div>
            ${chainpilot.badge(row.policy, row.policy === "提高目标库存" ? "amber" : row.policy === "降低目标库存" ? "blue" : "green")}
          </div>
        `).join("")}
      </div>
    `;
  }

  function business_table(table) {
    if (!table || !(table.columns || []).length) {
      return `<div class="chainpilot-empty">暂无明细。</div>`;
    }
    const columns = table.columns || [];
    const template = columns.map((_, index) => (index === 1 ? "1.35fr" : "1fr")).join(" ");
    return `
      <div class="chainpilot-table chainpilot-table-scroll">
        ${table_row(columns, true, template)}
        ${(table.rows || []).map((row) => table_row(row, false, template)).join("")}
      </div>
    `;
  }

  function table_row(values, isHead, template) {
    return `
      <div class="chainpilot-table-row ${isHead ? "head" : ""}" style="grid-template-columns: ${chainpilot.escape(template)};">
        ${(values || []).map((value) => `<span>${chainpilot.escape(value)}</span>`).join("")}
      </div>
    `;
  }

  function shortage_row(row) {
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.escape(row.material_code)}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(row.plant || "-")} · ${chainpilot.escape(row.shortage_date_p50 || "-")} · 缺口 ${chainpilot.number(row.shortage_qty_p90 || 0)}</div>
        </div>
        ${chainpilot.badge(chainpilot.percent((row.shortage_probability_14d || 0) * 100), "red")}
      </div>
    `;
  }

  function cash_row(row) {
    return `
      <div class="chainpilot-action-card compact">
        <div class="chainpilot-action-main">
          <div class="chainpilot-action-id">${sap_object_label(row.sap_object_type)} ${chainpilot.escape(row.sap_doc_no)}/${chainpilot.escape(row.sap_item_no)}</div>
          <div class="chainpilot-action-title">${chainpilot.escape(row.material_code)} · ${action_label(row.action_type)}</div>
          <div class="chainpilot-action-subtitle">余量 ${chainpilot.number(row.material_headroom || 0)}，占用 ${chainpilot.number(row.capacity_consumed || 0)}</div>
        </div>
        ${metric_block("资金影响", chainpilot.currency(row.cash_impact))}
        ${metric_block("风险", chainpilot.percent((row.risk_after || 0) * 100))}
        <div>${chainpilot.badge(level_label(row.recommendation_level), row.recommendation_level === "L1_AUTO_RECOMMEND" ? "green" : "blue")}</div>
      </div>
    `;
  }

  function reason_tile(row) {
    const tone = row.label === "可处理" ? "green" : "amber";
    return `
      <article class="chainpilot-reason-tile">
        <strong>${chainpilot.number(row.count)}</strong>
        <span>${chainpilot.escape(row.label)}</span>
        ${chainpilot.badge(row.label === "可处理" ? "可入选" : "已排除", tone)}
      </article>
    `;
  }

  function check_row(row) {
    const tone = row.status === "通过" ? "green" : "red";
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.escape(row.label)}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(row.detail)}</div>
        </div>
        <div class="chainpilot-row-end">
          <div class="chainpilot-value">${chainpilot.escape(row.value)}</div>
          ${chainpilot.badge(row.status, tone)}
        </div>
      </div>
    `;
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

  function audit_item(label, value) {
    return `<div class="chainpilot-audit-item"><span>${chainpilot.escape(label)}</span><strong>${chainpilot.escape(value)}</strong></div>`;
  }

  function metric_block(label, value) {
    return `<div><div class="chainpilot-metric">${chainpilot.escape(value)}</div><div class="chainpilot-metric-label">${chainpilot.escape(label)}</div></div>`;
  }

  function bind_plan_tabs(page) {
    const root = page.main.find(".chainpilot-shell");
    root.find("[data-plan-target]").on("click", function () {
      const target = $(this).attr("data-plan-target");
      root.find("[data-plan-target]").removeClass("active").attr("aria-selected", "false");
      $(this).addClass("active").attr("aria-selected", "true");
      root.find("[data-plan-panel]").removeClass("active");
      root.find(`[data-plan-panel="${target}"]`).addClass("active");
    });
  }

  function bind_route_buttons(page) {
    page.main.find("[data-route]").on("click", function () {
      frappe.set_route($(this).attr("data-route"));
    });
  }

  function find_table(tables, title) {
    return tables.find((table) => table.title === title) || { title, columns: [], rows: [], count: 0 };
  }

  function relationship_score(rows) {
    let total = 0;
    let valid = 0;
    rows.forEach((row) => {
      const match = String(row.value || "").match(/^(\d+)\/(\d+)$/);
      if (match) {
        valid += Number(match[1]);
        total += Number(match[2]);
      }
    });
    return total ? valid / total : 0;
  }

  function summary_by_label(rows, label) {
    return rows.find((row) => row.label === label) || {};
  }

  function action_label(value) {
    const labels = { CANCEL_PR_LINE: "取消采购申请", REDUCE_PR_QTY: "下调采购申请", DELAY_UNCONFIRMED_PO: "延期采购订单" };
    return labels[value] || chainpilot.escape(value || "-");
  }

  function sap_object_label(value) {
    const labels = { PR: "采购申请", PO: "采购订单" };
    return labels[value] || chainpilot.escape(value || "-");
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
