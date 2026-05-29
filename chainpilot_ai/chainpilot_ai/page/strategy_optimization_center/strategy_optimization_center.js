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
    return `${Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
  };
  chainpilot.percent = chainpilot.percent || function (value) {
    return `${Number(value || 0).toFixed(1)}%`;
  };
  chainpilot.badge = chainpilot.badge || function (label, tone = "neutral") {
    return `<span class="chainpilot-badge ${tone}">${chainpilot.escape(label)}</span>`;
  };

  frappe.pages["strategy-optimization-center"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
      parent: wrapper,
      title: "策略优化中心",
      single_column: true,
    });

    page.set_primary_action("运行回测", () => persist_backtest(page));
    page.set_secondary_action("采购决策", () => frappe.set_route("chainpilot-ai-command-center"));
    page.add_inner_button("模拟数据", () => frappe.set_route("mock-data-center"));
    page.add_inner_button("SAP 连接", () => frappe.set_route("sap-integration-console"));
    page.add_inner_button("建议", () => frappe.set_route("action-inbox"));
    page.main.html(`<div class="chainpilot-shell"><div class="chainpilot-loading">正在加载策略优化...</div></div>`);
    load_dashboard(page);
  };

  async function load_dashboard(page) {
    try {
      const response = await frappe.call({
        method: "chainpilot_ai.strategy.service.get_strategy_optimization_dashboard",
        args: { history_days: 120 },
      });
      render_dashboard(page, response.message || {});
    } catch (error) {
      console.error(error);
      page.main.find(".chainpilot-shell").html(`<div class="chainpilot-empty">无法加载策略优化数据。</div>`);
    }
  }

  async function persist_backtest(page, strategyId) {
    frappe.show_alert({ message: "正在运行并保存回测...", indicator: "blue" });
    const selected = strategyId || page.main.find("[data-strategy].is-selected").data("strategy") || "STRAT-BALANCED-MOCK";
    const response = await frappe.call({
      method: "chainpilot_ai.strategy.service.run_backtest_rpc",
      args: { strategy_id: selected, history_days: 120 },
    });
    const result = response.message || {};
    frappe.show_alert({
      message: result.ok ? "回测结果已保存" : "回测失败",
      indicator: result.ok ? "green" : "orange",
    });
    load_dashboard(page);
  }

  function render_dashboard(page, data) {
    const strategies = data.strategies || [];
    const backtests = data.backtests || [];
    const recommended = data.recommended_strategy_id;
    const best = backtests.find((item) => item.strategy_id === recommended) || backtests[0] || {};
    const segmentOrder = data.segment_order || [];
    const selectedStrategy = strategies.find((item) => item.strategy_id === recommended) || strategies[1] || strategies[0] || {};
    const selectedParams = selectedStrategy.parameter_json || {};
    const segmentPolicy = selectedParams.segment_policy || {};

    page.main.find(".chainpilot-shell").html(`
      <section class="chainpilot-hero">
        <div>
          <div class="chainpilot-eyebrow">回测调优</div>
          <h1 class="chainpilot-title">策略优化中心</h1>
          <p class="chainpilot-subtitle">用生产约束模拟快照回放三类算法，策略启用前必须人工确认；真实 SAP 历史接入后复用同一回测入口。</p>
        </div>
        <div class="chainpilot-meta-grid">
          ${meta_item("推荐策略", data.recommended_strategy_name || "-")}
          ${meta_item("历史窗口", `${chainpilot.number(data.history_days || 0)} 天`)}
          ${meta_item("求解器", (best.summary_json && solver_name(best.summary_json)) || "混合整数规划")}
          ${meta_item("回写方式", data.sap_writeback_mode === "draft_only" ? "仅生成草稿" : "人工审批")}
        </div>
      </section>

      <section class="chainpilot-kpi-grid">
        ${kpi_card("缺料召回率", chainpilot.percent((best.recall_rate || 0) * 100), "实际缺料提前识别")}
        ${kpi_card("高风险准确率", chainpilot.percent((best.precision_rate || 0) * 100), "预测命中比例")}
        ${kpi_card("预计兑现资金", chainpilot.currency(best.realized_cash_total), "模拟审批后兑现")}
        ${kpi_card("策略评分", chainpilot.number(best.score || 0, 1), "综合风险与收益")}
      </section>

      <section class="chainpilot-panel" style="margin-top: 18px;">
        <div class="chainpilot-panel-header">
          <div>
            <h2 class="chainpilot-panel-title">策略对比</h2>
            <p class="chainpilot-panel-note">系统推荐不自动生效，保存后进入策略版本和审批记录。</p>
          </div>
        </div>
        <div class="chainpilot-action-list">
          ${backtests.map((item) => strategy_card(item, strategies.find((strategy) => strategy.strategy_id === item.strategy_id), item.strategy_id === recommended)).join("")}
        </div>
      </section>

      <section class="chainpilot-grid-2">
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">参数配置</h2>
              <p class="chainpilot-panel-note">当前展示推荐策略的 ABC/XYZ 服务水平和缺料阈值。</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${segmentOrder.map((segment) => segment_row(segment, segmentPolicy[segment] || {})).join("")}
          </div>
        </div>

        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">回测样本</h2>
              <p class="chainpilot-panel-note">模拟历史快照重放结果，后续可替换为真实 SAP 两年历史。</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${(best.detail_rows || []).slice(0, 8).map(detail_row).join("") || empty_state("暂无回测明细。")}
          </div>
        </div>
      </section>

      <section class="chainpilot-panel" style="margin-top: 18px;">
        <div class="chainpilot-panel-header">
          <div>
            <h2 class="chainpilot-panel-title">上线闸门</h2>
            <p class="chainpilot-panel-note">模拟阶段验证产品效果，真实 SAP 历史接入后复用同一回测入口。</p>
          </div>
        </div>
        <div class="chainpilot-action-list">
          ${gate_card("硬约束违规", best.hard_constraint_violations === 0 ? "通过" : "需复核", best.hard_constraint_violations === 0 ? "green" : "red")}
          ${gate_card("人工确认", "必需", "blue")}
          ${gate_card("策略版本", selectedStrategy.version || "-", "neutral")}
          ${gate_card("真实数据", "待接入", "amber")}
        </div>
      </section>
    `);

    page.main.find("[data-strategy]").on("click", (event) => {
      page.main.find("[data-strategy]").removeClass("is-selected");
      $(event.currentTarget).addClass("is-selected");
    });
    page.main.find("[data-save-backtest]").on("click", (event) => persist_backtest(page, $(event.currentTarget).data("save-backtest")));
  }

  function strategy_card(backtest, strategy, selected) {
    strategy = strategy || {};
    const tone = selected ? "green" : backtest.status === "Needs Review" ? "amber" : "blue";
    return `
      <div class="chainpilot-action-card ${selected ? "is-selected" : ""}" data-strategy="${chainpilot.escape(backtest.strategy_id)}">
        <div class="chainpilot-action-main">
          <div class="chainpilot-action-id">${chainpilot.escape(strategy.strategy_type || backtest.strategy_type || "")}</div>
          <div class="chainpilot-action-title">${chainpilot.escape(backtest.strategy_name)}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(strategy.description || "")}</div>
        </div>
        ${metric_block("召回率", chainpilot.percent((backtest.recall_rate || 0) * 100))}
        ${metric_block("准确率", chainpilot.percent((backtest.precision_rate || 0) * 100))}
        ${metric_block("兑现资金", chainpilot.currency(backtest.realized_cash_total))}
        <div>
          ${chainpilot.badge(selected ? "推荐" : status_label(backtest.status), tone)}
          <button class="chainpilot-link-button" data-save-backtest="${chainpilot.escape(backtest.strategy_id)}">保存</button>
        </div>
      </div>
    `;
  }

  function segment_row(segment, policy) {
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.escape(segment)}</div>
          <div class="chainpilot-action-subtitle">服务水平 ${chainpilot.percent((policy.service_level || 0) * 100)}</div>
        </div>
        ${chainpilot.badge(`告警 ${chainpilot.percent((policy.shortage_alert_threshold || 0) * 100)}`, "blue")}
      </div>
    `;
  }

  function detail_row(row) {
    const tone = row.verdict === "命中" || row.verdict === "可执行" ? "green" : row.verdict === "误报" ? "amber" : "blue";
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.escape(row.metric_name)} · ${chainpilot.escape(row.material_code || "-")}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(row.expected_value || "")}</div>
        </div>
        ${chainpilot.badge(row.verdict || "-", tone)}
      </div>
    `;
  }

  function gate_card(label, value, tone) {
    return `
      <div class="chainpilot-action-card">
        <div class="chainpilot-action-main">
          <div class="chainpilot-action-title">${chainpilot.escape(label)}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(value)}</div>
        </div>
        <div>${chainpilot.badge(value, tone)}</div>
      </div>
    `;
  }

  function meta_item(label, value) {
    return `<div class="chainpilot-meta-item"><div class="chainpilot-label">${chainpilot.escape(label)}</div><div class="chainpilot-value">${chainpilot.escape(value)}</div></div>`;
  }

  function kpi_card(label, value, note) {
    return `<div class="chainpilot-kpi"><div class="chainpilot-label">${chainpilot.escape(label)}</div><strong>${chainpilot.escape(value)}</strong><span>${chainpilot.escape(note)}</span></div>`;
  }

  function metric_block(label, value) {
    return `<div><div class="chainpilot-metric">${chainpilot.escape(value)}</div><div class="chainpilot-metric-label">${chainpilot.escape(label)}</div></div>`;
  }

  function status_label(value) {
    const labels = { Pass: "通过", "Needs Review": "需复核", Failed: "失败" };
    return labels[value] || value || "";
  }

  function empty_state(message) {
    return `<div class="chainpilot-empty">${chainpilot.escape(message)}</div>`;
  }

  function solver_name(summaryJson) {
    try {
      const parsed = JSON.parse(summaryJson);
      return parsed.scenario ? "混合整数规划" : "";
    } catch (error) {
      return "";
    }
  }
})();
