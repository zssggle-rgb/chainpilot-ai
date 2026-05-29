(() => {
  const chainpilot = window.chainpilot || (window.chainpilot = chainpilot_utils());

  frappe.pages["chainpilot-ai-command-center"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
      parent: wrapper,
      title: "采购决策",
      single_column: true,
    });

    page.set_primary_action("运行算法", async () => {
      await frappe.call({ method: "chainpilot_ai.algorithms.service.run_algorithm_runtime_rpc" });
      frappe.show_alert({ message: "三大算法已运行", indicator: "green" });
      load_command_center(page);
    });
    page.set_secondary_action("SAP 连接", () => frappe.set_route("sap-integration-console"));
    page.add_inner_button("建议", () => frappe.set_route("action-inbox"));
    page.add_inner_button("方案", () => frappe.set_route("scenario-studio"));
    page.add_inner_button("智能", () => frappe.set_route("ai-copilot"));
    page.add_inner_button("监控", () => frappe.set_route("execution-monitor"));
    page.add_inner_button("学习", () => frappe.set_route("learning-center"));
    page.main.html(`<div class="chainpilot-shell"><div class="chainpilot-loading">正在加载采购决策...</div></div>`);
    load_command_center(page);
  };

  async function load_command_center(page) {
    try {
      const response = await frappe.call({ method: "chainpilot_ai.algorithms.service.get_algorithm_runtime_dashboard" });
      render_command_center(page, response.message || {});
    } catch (error) {
      page.main.find(".chainpilot-shell").html(`<div class="chainpilot-empty">无法加载采购决策数据。</div>`);
      console.error(error);
    }
  }

  function render_command_center(page, data) {
    const shortage = data.shortage || [];
    const cash = data.cash || [];
    const blockedCash = data.blocked_cash || [];
    const masterData = data.master_data || [];
    const runs = data.runs || [];
    const recommendations = data.recommendations || [];
    const releaseValue = cash.reduce((sum, item) => sum + Number(item.cash_impact || 0), 0);

    page.main.find(".chainpilot-shell").html(`
      <section class="chainpilot-hero">
        <div>
          <div class="chainpilot-eyebrow">算法运行</div>
          <h1 class="chainpilot-title">供应链算法决策</h1>
          <p class="chainpilot-subtitle">
            基于 Mock SAP 明细快照运行缺料风险、现金释放和主数据体检算法。
          </p>
        </div>
        <div class="chainpilot-meta-grid">
          ${meta_item("数据快照", data.snapshot_id || "-")}
          ${meta_item("运行模式", data.mode === "frappe" ? "已落库" : "模拟预览")}
          ${meta_item("算法运行", chainpilot.number((data.counts || {})["Algorithm Run"] || runs.length))}
          ${meta_item("算法结果", chainpilot.number((data.counts || {})["Algorithm Result"] || 0))}
        </div>
      </section>

      <section class="chainpilot-kpi-grid">
        ${kpi_card("14 天缺料风险", chainpilot.number(shortage.length), "按缺料概率排序")}
        ${kpi_card("今日可释放现金", chainpilot.currency(releaseValue), "来自选中 PR/PO 动作")}
        ${kpi_card("主数据异常", chainpilot.number(masterData.length), "交期、安全库存、MOQ/MPQ")}
        ${kpi_card("已生成建议", chainpilot.number(recommendations.length), "均带算法来源和证据")}
      </section>

      <section class="chainpilot-grid-2">
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">未来 14 天缺料风险</h2>
              <p class="chainpilot-panel-note">概率、预计日期、P90 缺口和补救动作。</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${shortage.map(shortage_row).join("") || empty_state("暂无缺料风险。")}
          </div>
        </div>

        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">今日可调整单据</h2>
              <p class="chainpilot-panel-note">选中动作和被约束阻断的动作包。</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${cash.map(cash_row).join("") || empty_state("暂无可调整单据。")}
            ${blockedCash.length ? `<div class="chainpilot-empty">另有 ${chainpilot.number(blockedCash.length)} 条被约束阻断。</div>` : ""}
          </div>
        </div>
      </section>

      <section class="chainpilot-panel" style="margin-top: 18px;">
        <div class="chainpilot-panel-header">
          <div>
            <h2 class="chainpilot-panel-title">SAP 主数据体检</h2>
            <p class="chainpilot-panel-note">计划交货期、安全库存和 MOQ/MPQ 异常。</p>
          </div>
        </div>
        <div class="chainpilot-compact-list">
          ${masterData.map(master_data_row).join("") || empty_state("暂无主数据异常。")}
        </div>
      </section>

      <section class="chainpilot-panel" style="margin-top: 18px;">
        <div class="chainpilot-panel-header">
          <div>
            <h2 class="chainpilot-panel-title">最近算法运行</h2>
            <p class="chainpilot-panel-note">Algorithm Run 状态、耗时和结果摘要。</p>
          </div>
          <button class="chainpilot-link-button" data-route="action-inbox">查看建议</button>
        </div>
        <div class="chainpilot-action-list">
          ${runs.slice(0, 3).map(run_card).join("") || empty_state("尚未运行算法。")}
        </div>
      </section>
    `);

    page.main.find("[data-route='action-inbox']").on("click", () => frappe.set_route("action-inbox"));
    page.main.find("[data-route='scenario-studio']").on("click", () => frappe.set_route("scenario-studio"));
    page.main.find("[data-recommendation]").on("click", () => frappe.set_route("action-inbox"));
  }

  function shortage_row(item) {
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.escape(item.material_code)} · ${chainpilot.escape(item.suggested_action || "")}</div>
          <div class="chainpilot-action-subtitle">预计 ${chainpilot.escape(item.shortage_date_p50 || "-")} 缺料，P90 缺口 ${chainpilot.number(item.shortage_qty_p90)}</div>
        </div>
        ${chainpilot.badge(`概率 ${chainpilot.percent(Number(item.shortage_probability_14d || 0) * 100)}`, "amber")}
      </div>
    `;
  }

  function cash_row(item) {
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.actionLabel(item.action_type)} · ${chainpilot.escape(item.sap_doc_no)}/${chainpilot.escape(item.sap_item_no)}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(item.material_code)} · ${chainpilot.escape(item.supplier || "-")} · ${chainpilot.escape(item.constraint_verdict || "")}</div>
        </div>
        <div class="chainpilot-metric">${chainpilot.currency(item.cash_impact)}</div>
      </div>
    `;
  }

  function master_data_row(item) {
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.actionLabel(item.action_type)} · ${chainpilot.escape(item.material_code)}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(item.metric_name)}：${chainpilot.escape(item.before_value)} → ${chainpilot.escape(item.after_value)}，样本 ${chainpilot.number(item.sample_count)}</div>
        </div>
        ${chainpilot.badge(`置信 ${chainpilot.percent(Number(item.confidence_score || 0) * 100)}`, "blue")}
      </div>
    `;
  }

  function run_card(item) {
    let summary = {};
    try {
      summary = JSON.parse(item.summary_result_json || "{}");
    } catch (error) {
      summary = {};
    }
    return `
      <div class="chainpilot-action-card">
        <div class="chainpilot-action-main">
          <div class="chainpilot-action-id">${chainpilot.escape(item.algorithm_run_id || "")}</div>
          <div class="chainpilot-action-title">${algorithm_name(item.algorithm_code)}</div>
          <div class="chainpilot-action-subtitle">快照 ${chainpilot.escape(item.snapshot_id || "-")} · 耗时 ${chainpilot.number(item.duration_ms || 0)} ms</div>
        </div>
        ${metric_block("结果数", chainpilot.number(summary.result_count || summary.candidate_action_count || 0))}
        <div>${chainpilot.badge(chainpilot.statusLabel(item.status), chainpilot.verdictTone(item.status))}</div>
      </div>
    `;
  }

  function algorithm_name(code) {
    const labels = {
      SHORTAGE_RISK_14D_PROB: "14 天缺料风险",
      CASH_RELEASE_PR_PO_OPT: "现金释放动作包",
      MASTER_DATA_DIAGNOSIS_STAT: "主数据体检",
    };
    return labels[code] || code || "";
  }

  function meta_item(label, value) {
    return `<div class="chainpilot-meta-item"><div class="chainpilot-label">${chainpilot.escape(label)}</div><div class="chainpilot-value">${chainpilot.escape(value)}</div></div>`;
  }

  function kpi_card(label, value, note) {
    return `<div class="chainpilot-kpi"><div class="chainpilot-label">${chainpilot.escape(label)}</div><strong>${chainpilot.escape(value)}</strong><span>${chainpilot.escape(note)}</span></div>`;
  }

  function scenario_card(scenario) {
    const recommended = scenario.strategy_type === "Recommended";
    return `
      <div class="chainpilot-scenario ${recommended ? "is-recommended" : ""}">
        <div>
          <div class="chainpilot-scenario-name">${chainpilot.strategyLabel(scenario.strategy_name || scenario.strategy_type)}</div>
          <div class="chainpilot-scenario-text">${chainpilot.escape(business_text(scenario.ai_recommendation || ""))}</div>
        </div>
        ${metric_block("采购金额", chainpilot.currency(scenario.purchase_amount))}
        ${metric_block("资金占用减少额", chainpilot.currency(scenario.cash_release))}
        <div>
          ${metric_block("改善比例", chainpilot.percent(scenario.cash_release_rate || 0))}
          <div style="margin-top: 6px;">${chainpilot.badge(chainpilot.riskLabel(scenario.risk_level) || "-", chainpilot.riskTone(scenario.risk_level))}</div>
        </div>
      </div>
    `;
  }

  function metric_block(label, value) {
    return `<div><div class="chainpilot-metric">${chainpilot.escape(value)}</div><div class="chainpilot-metric-label">${chainpilot.escape(label)}</div></div>`;
  }

  function control_rows(riskActions, checks) {
    const approvalChecks = checks.filter((item) => item.verdict === "PASS_WITH_APPROVAL").slice(0, 4);
    const rows = [
      ...riskActions.slice(0, 3).map((item) => ({
        label: chainpilot.recommendationLabel(item.recommendation_id),
        note: `${chainpilot.actionLabel(item.action_type)} · ${item.material_name || item.material_code}`,
        badge: chainpilot.badge(`风险 ${chainpilot.number(item.shortage_risk_after, 1)}`, "amber"),
        name: item.name,
      })),
      ...approvalChecks.map((item) => ({
        label: rule_label(item.rule_code),
        note: business_text(item.message),
        badge: chainpilot.badge("需审批", "blue"),
        name: item.recommendation_id,
      })),
    ];
    if (!rows.length) return empty_state("暂无高风险或审批提示。");
    return rows
      .slice(0, 6)
      .map(
        (row) => `
          <div class="chainpilot-risk-row">
            <div>
              <div class="chainpilot-action-title">${chainpilot.escape(row.label)}</div>
              <div class="chainpilot-action-subtitle">${chainpilot.escape(row.note)}</div>
            </div>
            <button class="chainpilot-link-button" data-recommendation="${chainpilot.escape(row.name)}">处理</button>
          </div>
        `,
      )
      .join("");
  }

  function action_card(item) {
    return `
      <div class="chainpilot-action-card">
        <div class="chainpilot-action-main">
          <div class="chainpilot-action-id">${chainpilot.escape(chainpilot.recommendationLabel(item.recommendation_id))}</div>
          <div class="chainpilot-action-title">${chainpilot.actionLabel(item.action_type)} · ${chainpilot.escape(item.material_name || item.material_code)}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.sapObjectLabel(item.sap_object_type)} ${chainpilot.escape(item.sap_doc_no)}/${chainpilot.escape(item.sap_item_no)} · ${chainpilot.escape(item.plant)} · ${chainpilot.escape(item.supplier || "-")}</div>
          <div class="chainpilot-change-line">
            <span>数量：${chainpilot.number(item.before_qty)} → ${chainpilot.number(item.after_qty)}</span>
            <span>日期：${chainpilot.escape(item.before_date || "-")} → ${chainpilot.escape(item.after_date || "-")}</span>
          </div>
        </div>
        ${metric_block("资金占用减少额", chainpilot.currency(item.cash_release))}
        <div>
          ${chainpilot.badge(chainpilot.statusLabel(item.approval_status), chainpilot.verdictTone(item.approval_status))}
          ${chainpilot.badge(chainpilot.statusLabel(item.explanation_status), chainpilot.verdictTone(item.explanation_status))}
        </div>
        <button class="chainpilot-link-button" data-recommendation="${chainpilot.escape(item.name)}">查看详情</button>
      </div>
    `;
  }

  function rule_label(value) {
    const labels = {
      MASTER_DATA_REVIEW: "主数据复核",
      SUPPLIER_CONFIRMATION: "供应商确认",
      RISK_LIMIT: "风险阈值",
      M3_SAFE_STOCK: "安全库存校验",
    };
    return labels[value] || value || "";
  }

  function business_text(value) {
    return String(value || "")
      .replaceAll("PR 数量下调", "采购申请数量下调")
      .replaceAll("PO 延期", "采购订单延期")
      .replaceAll("PR", "采购申请")
      .replaceAll("PO", "采购订单")
      .replaceAll("MVP", "首版验证")
      .replaceAll("首版验证 推荐方案", "首版验证推荐方案")
      .replaceAll("作为 首版验证推荐方案", "作为首版验证推荐方案")
      .replaceAll("SAP writeback", "SAP 回写")
      .replaceAll("draft-only", "仅生成草稿");
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
        const amount = Number(value || 0);
        if (Math.abs(amount) >= 10000) return `${(amount / 10000).toLocaleString(undefined, { maximumFractionDigits: 1 })} 万元`;
        return `${amount.toLocaleString(undefined, { maximumFractionDigits: 0 })} 元`;
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
      statusLabel(value) {
        const labels = { Pending: "待处理", Approved: "已批准", Rejected: "已拒绝", Ready: "已就绪", Failed: "失败", Queued: "排队中", Running: "运行中", Success: "成功" };
        return labels[value] || value || "";
      },
      riskLabel(risk) {
        const labels = { High: "高", Medium: "中", Low: "低", Critical: "严重" };
        return labels[risk] || risk || "";
      },
      strategyLabel(strategy) {
        const labels = { Recommended: "推荐方案", Conservative: "稳妥方案", Aggressive: "进取方案", "Agent 推荐方案": "智能推荐方案", "AI 推荐方案": "智能推荐方案", "Recommended Plan": "推荐方案", "Conservative Plan": "稳妥方案", "Aggressive Plan": "进取方案" };
        return labels[strategy] || strategy || "";
      },
      sourceSystemLabel(sourceSystem) {
        const labels = { SAP_MOCK: "SAP 模拟快照", AIPLAN_DB: "采购分析报告导入", SAP: "SAP" };
        return labels[sourceSystem] || sourceSystem || "";
      },
      sapObjectLabel(objectType) {
        const labels = { PR: "采购申请", PO: "采购订单", MRP_PARAM: "MRP 参数", PLANNED_ORDER: "计划订单" };
        return labels[objectType] || objectType || "";
      },
      recommendationLabel(recommendationId) {
        const value = String(recommendationId || "");
        return value ? `建议 ${value.replace(/^REC-/, "")}` : "";
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
          REDUCE_PR_QTY: "下调采购申请数量",
          CANCEL_PR_LINE: "取消采购申请行",
          DELAY_UNCONFIRMED_PO: "延后未确认采购订单",
          SPLIT_PO_DELIVERY: "拆分采购订单交期",
          ADVANCE_RISK_MATERIAL: "提前风险物料采购",
          EXPEDITE_PO: "催交采购订单",
          CREATE_EMERGENCY_PR: "新建紧急采购申请",
          USE_SUBSTITUTE_MATERIAL: "启用替代料",
          REVIEW_SAFETY_STOCK: "复核安全库存",
          REVIEW_SUPPLIER_LEAD_TIME: "复核供应商交期",
          REVIEW_MOQ: "复核最小采购量",
          REVIEW_SUPPLIER_PARAMETER: "复核供应商参数",
        };
        return labels[actionType] || actionType || "";
      },
    };
  }
})();
