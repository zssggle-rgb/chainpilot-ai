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
      CREATED: "已创建",
      PARSE_USER_GOAL: "解析目标",
      BUILD_SCENARIO: "生成方案",
      BUILD_SCENARIO_CONSTRAINTS: "生成方案约束",
      CHECK_DATA_QUALITY: "检查数据质量",
      RUN_OPTIMIZATION: "运行优化",
      RUN_RISK_SIMULATION: "风险模拟",
      CHECK_CONSTRAINTS: "校验约束",
      GENERATE_ACTION_CARDS: "生成建议",
      GENERATE_EXPLANATION: "生成说明",
      GENERATE_ACTIONS: "生成建议",
      COLLECT_EVIDENCE: "收集证据",
      EXPLAIN_RECOMMENDATIONS: "生成说明",
      COMPLETE: "完成",
      Open: "待处理",
    };
    return labels[value] || value || "";
  };

  frappe.pages["ai-copilot"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
      parent: wrapper,
      title: "智能协同",
      single_column: true,
    });

    page.set_primary_action("生成优化建议", () => run_agent(page));
    page.add_inner_button("建议", () => frappe.set_route("action-inbox"));
    page.add_inner_button("学习", () => frappe.set_route("learning-center"));
    page.add_inner_button("方案", () => frappe.set_route("scenario-studio"));
    window.chainpilot.workspace.mountLegacyShell(page, {
      route: "ai-copilot",
      title: "智能协同",
      subtitle: "业务目标解析 / 方案生成 / 证据摘要",
      loading: "正在加载智能协同工作台...",
    });
    load_dashboard(page);
  };

  async function load_dashboard(page) {
    try {
      const response = await frappe.call({
        method: "chainpilot_ai.agent.service.get_agent_dashboard",
      });
      render_dashboard(page, response.message || {});
    } catch (error) {
      console.error(error);
      page.main.find(".chainpilot-shell").html(`<div class="chainpilot-empty">无法加载智能助手。</div>`);
    }
  }

  function render_dashboard(page, data) {
    const runs = data.runs || [];
    const logs = data.tool_logs || [];
    const issues = data.issues || [];
    const counts = data.counts || {};
    const latest = runs[0] || {};
    const assistant = data.assistant || {};
    const llm = data.llm || {};

    page.main.find(".chainpilot-shell").html(`
      <section class="chainpilot-hero">
        <div>
          <div class="chainpilot-eyebrow">AI 工作台</div>
          <h1 class="chainpilot-title">业务目标到采购动作</h1>
          <p class="chainpilot-subtitle">
            输入资金、供应和审批目标，系统生成可复核的采购建议和执行材料。
          </p>
        </div>
        <div class="chainpilot-meta-grid">
          ${meta_item("交互框", assistant.label || "内置业务助手")}
          ${meta_item("模型", llm.configured ? llm.model : "未配置")}
          ${meta_item("运行次数", chainpilot.number(counts["Agent Run"] || 0))}
          ${meta_item("最近状态", chainpilot.statusLabel(latest.status || "Not Run"))}
        </div>
      </section>

      <section class="chainpilot-grid-2">
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">业务目标</h2>
              <p class="chainpilot-panel-note">${chainpilot.escape(assistant.description || "内置助手负责目标理解和业务材料生成。")}</p>
            </div>
            ${chainpilot.badge(llm.configured ? "真实模型" : "规则降级", llm.configured ? "green" : "amber")}
          </div>
          <textarea class="form-control" rows="5" data-agent-goal>减少 8000 万采购资金占用，不影响空调旺季生产，优先调整采购申请，并保持安全库存不低于 28 天。</textarea>
          <div style="margin-top: 14px;">
            <button class="chainpilot-link-button" data-run-agent="1">生成方案和建议</button>
            ${assistant.is_external && assistant.external_url ? `<button class="chainpilot-filter" data-open-assistant="${chainpilot.escape(assistant.external_url)}">打开${chainpilot.escape(assistant.label)}</button>` : ""}
            <button class="chainpilot-filter" data-route="action-inbox">查看建议</button>
          </div>
        </div>

        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">最近输出</h2>
              <p class="chainpilot-panel-note">资金影响、风险和待处理动作。</p>
            </div>
          </div>
          ${latest.agent_run_id ? run_summary(latest) : empty_state("尚未运行智能助手。")}
        </div>
      </section>

      <section class="chainpilot-grid-2">
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">运行历史</h2>
              <p class="chainpilot-panel-note">按目标追踪每次建议生成。</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${runs.map(run_row).join("") || empty_state("尚无运行记录。")}
          </div>
        </div>
        <div class="chainpilot-panel">
          <div class="chainpilot-panel-header">
            <div>
              <h2 class="chainpilot-panel-title">处理记录</h2>
              <p class="chainpilot-panel-note">模型理解、算法运行和证据准备。</p>
            </div>
          </div>
          <div class="chainpilot-compact-list">
            ${logs.map(tool_row).join("") || empty_state("尚无工具日志。")}
          </div>
        </div>
      </section>

      <section class="chainpilot-panel" style="margin-top: 18px;">
        <div class="chainpilot-panel-header">
          <div>
            <h2 class="chainpilot-panel-title">数据质量提示</h2>
            <p class="chainpilot-panel-note">影响建议可信度的数据问题。</p>
          </div>
        </div>
        <div class="chainpilot-action-list">
          ${issues.map(issue_card).join("") || empty_state("暂无数据质量问题。")}
        </div>
      </section>
    `);

    page.main.find("[data-run-agent]").on("click", () => run_agent(page));
    page.main.find("[data-route='action-inbox']").on("click", () => frappe.set_route("action-inbox"));
    page.main.find("[data-open-assistant]").on("click", function () {
      window.open($(this).data("open-assistant"), "_blank", "noopener,noreferrer");
    });
  }

  async function run_agent(page) {
    const goal = page.main.find("[data-agent-goal]").val();
    frappe.show_alert({ message: "正在生成优化建议...", indicator: "blue" });
    const response = await frappe.call({
      method: "chainpilot_ai.agent.service.run_agent_rpc",
      args: { user_goal: goal },
    });
    const result = response.message || {};
    frappe.show_alert({
      message: `已生成 ${chainpilot.number((result.recommendations || []).length)} 条建议`,
      indicator: result.ok ? "green" : "orange",
    });
    load_dashboard(page);
  }

  function run_summary(run) {
    return `
      <div class="chainpilot-compact-list">
        ${meta_item("运行编号", run.agent_run_id || "-")}
        ${meta_item("场景", run.scenario_id || "-")}
        ${meta_item("状态", chainpilot.statusLabel(run.current_state || "-"))}
        ${meta_item("输出", clean_text(run.output_summary) || "-")}
      </div>
    `;
  }

  function run_row(run) {
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.escape(run.agent_run_id)}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(run.user_goal || "")}</div>
        </div>
        <div>
          ${chainpilot.badge(chainpilot.statusLabel(run.status) || "-", run.status === "Success" ? "green" : "amber")}
          <div class="chainpilot-metric-label">${chainpilot.escape(chainpilot.statusLabel(run.current_state) || "")}</div>
        </div>
      </div>
    `;
  }

  function tool_row(log) {
    const cleaned = clean_text(log.output_summary);
    const summary = cleaned.length > 120 ? `${cleaned.slice(0, 120)}...` : cleaned;
    return `
      <div class="chainpilot-risk-row">
        <div>
          <div class="chainpilot-action-title">${chainpilot.escape(tool_label(log.tool_name))}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(summary)}</div>
        </div>
        <div>
          ${chainpilot.badge(chainpilot.statusLabel(log.status) || "-", log.status === "Success" ? "green" : "red")}
          <div class="chainpilot-metric">${chainpilot.number(log.duration_ms || 0)} 毫秒</div>
        </div>
      </div>
    `;
  }

  function issue_card(issue) {
    const tone = issue.severity === "High" || issue.severity === "Blocked" ? "red" : issue.severity === "Medium" ? "amber" : "blue";
    return `
      <div class="chainpilot-action-card">
        <div class="chainpilot-action-main">
          <div class="chainpilot-action-id">${chainpilot.escape(issue_type_label(issue.issue_type))}</div>
          <div class="chainpilot-action-title">${chainpilot.escape(clean_text(issue.message || ""))}</div>
          <div class="chainpilot-action-subtitle">${chainpilot.escape(clean_text(issue.recommendation || ""))}</div>
        </div>
        <div>${metric(object_label(issue.object_type) || "-", "对象")}</div>
        <div>${chainpilot.badge(severity_label(issue.severity), tone)}</div>
        <div>${chainpilot.badge(chainpilot.statusLabel(issue.status) || "-", "neutral")}</div>
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

  function tool_label(toolName) {
    const labels = {
      parse_user_goal: "解析业务目标",
      build_scenario_constraints: "生成方案约束",
      check_data_quality: "检查数据质量",
      run_optimization: "运行优化",
      validate_constraints: "校验约束",
      generate_scenario: "生成方案",
      optimize_recommendations: "优化建议",
      generate_action_cards: "生成建议卡片",
      collect_evidence: "收集证据",
      explain_recommendation: "生成说明",
      data_quality_check: "数据质量检查",
    };
    return labels[toolName] || toolName || "";
  }

  function severity_label(value) {
    const labels = { High: "高", Medium: "中", Low: "低", Blocked: "阻断" };
    return labels[value] || value || "";
  }

  function issue_type_label(value) {
    const labels = {
      "Stale Snapshot": "快照需复核",
      "Missing Field": "字段缺失",
      Outlier: "异常值",
      "Mapping Gap": "映射缺口",
    };
    return labels[value] || value || "";
  }

  function object_label(value) {
    const labels = {
      "SAP Mock Snapshot": "SAP 模拟快照",
      "SAP Snapshot": "SAP 快照",
    };
    return labels[value] || value || "";
  }

  function clean_text(value) {
    const text = String(value || "");
    const replacements = {
      "Generated 10 recommendations, 10 constraint checks, 10 evidence records.": "生成 10 条建议、10 条约束校验和 10 条证据。",
      "当前为 mock 快照，接入真实 SAP 后需复核快照日期和字段映射。": "当前为模拟快照，接入真实 SAP 后需复核快照日期和字段映射。",
      "上线真实 OData 前先运行 M2 同步并比对 PR/PO/库存字段。": "上线真实接口前先运行二阶段同步，并比对采购申请、采购订单和库存字段。",
    };
    let cleaned = replacements[text] || text;
    cleaned = cleaned
      .replace("目标释放", "目标占用减少额")
      .replace("目标资金改善", "目标占用减少额")
      .replace("预计释放", "资金占用减少额")
      .replace("预计资金改善", "资金占用减少额")
      .replace("优先动作", "优先建议类型")
      .replace("draft_only", "仅生成草稿")
      .replace("Low", "低")
      .replace("evidence_id", "证据")
      .replace("动作", "建议")
      .replace("mock", "模拟")
      .replace("OData", "接口")
      .replace("PR/PO", "采购申请/采购订单")
      .replace("REDUCE_PR_QTY", "下调采购申请数量")
      .replace("DELAY_UNCONFIRMED_PO", "延后未确认采购订单")
      .replace("ADVANCE_RISK_MATERIAL", "提前风险物料采购")
      .replace("REVIEW_SAFETY_STOCK", "复核安全库存")
      .replace("REVIEW_SUPPLIER_LEAD_TIME", "复核供应商交期");
    return cleaned;
  }
})();
