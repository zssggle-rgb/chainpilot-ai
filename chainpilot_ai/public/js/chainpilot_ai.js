window.chainpilot_ai = window.chainpilot_ai || {};
window.chainpilot = window.chainpilot || {};

window.chainpilot.escape = function (value) {
  return frappe.utils.escape_html(value == null ? "" : String(value));
};

window.chainpilot.currency = function (value) {
  const amount = Number(value || 0);
  if (Math.abs(amount) >= 10000) {
    return `${(amount / 10000).toLocaleString(undefined, {
      minimumFractionDigits: 0,
      maximumFractionDigits: 1,
    })} 万元`;
  }
  return `${amount.toLocaleString(undefined, { maximumFractionDigits: 0 })} 元`;
};

window.chainpilot.number = function (value, decimals = 0) {
  return Number(value || 0).toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
};

window.chainpilot.percent = function (value) {
  return `${Number(value || 0).toFixed(1)}%`;
};

window.chainpilot.badge = function (label, tone = "neutral") {
  return `<span class="chainpilot-badge ${tone}">${window.chainpilot.escape(label)}</span>`;
};

window.chainpilot.riskTone = function (risk) {
  if (["High", "Critical", "高", "严重"].includes(risk)) return "red";
  if (["Medium", "中"].includes(risk)) return "amber";
  return "green";
};

window.chainpilot.verdictTone = function (verdict) {
  if (["BLOCK", "BLOCKED", "Failed", "Rejected", "Conflict", "失败", "已拒绝", "冲突"].includes(verdict)) return "red";
  if (["WARN", "PASS_WITH_APPROVAL", "Pending", "Draft", "Draft Ready", "Reviewed", "需审批", "待处理", "草稿"].includes(verdict)) return "amber";
  if (["PASS", "Approved", "Ready", "Success", "Executed", "Sent", "Match", "已批准", "已就绪", "成功", "已执行", "一致"].includes(verdict)) return "green";
  return "neutral";
};

window.chainpilot.actionLabel = function (actionType) {
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
};

window.chainpilot.statusLabel = function (value) {
  const labels = {
    Pending: "待处理",
    Approved: "已批准",
    Rejected: "已拒绝",
    Submitted: "已提交",
    Draft: "草稿",
    "Draft Ready": "草稿已生成",
    Ready: "已就绪",
    NEED_EVIDENCE: "缺少证据",
    Failed: "失败",
    Queued: "排队中",
    Running: "运行中",
    Success: "成功",
    Executed: "已执行",
    Sent: "已发送",
    Reviewed: "已复核",
    "Not Created": "未生成",
    "Not Run": "未运行",
    "Not Started": "未开始",
    "Mock Ready": "模拟连接可用",
    MOCK_READY: "模拟连接可用",
    DRY_RUN: "配置校验",
    "Dry Run": "配置校验",
    Enabled: "启用",
    Disabled: "停用",
    Match: "一致",
    Conflict: "冲突",
    PASS: "通过",
    WARN: "需关注",
    PASS_WITH_APPROVAL: "需审批",
    BLOCKED: "已阻断",
    BLOCK: "已阻断",
    L1_AUTO_RECOMMEND: "低风险可审批",
    L2_REVIEW: "计划员复核",
    L3_SUPPLIER_CONFIRM: "供应商确认",
    L4_WATCH_ONLY: "仅观察",
    New: "新建",
    Applied: "已应用",
    Ignored: "已忽略",
    Countered: "供应商还价",
    Accepted: "已接受",
    "Accepted with later ship date": "接受但要求调整交期",
    CREATED: "已创建",
    PARSE_USER_GOAL: "解析目标",
    BUILD_SCENARIO: "生成方案",
    BUILD_SCENARIO_CONSTRAINTS: "生成方案约束",
    CHECK_DATA_QUALITY: "检查数据质量",
    RUN_OPTIMIZATION: "运行优化",
    RUN_RISK_SIMULATION: "风险模拟",
    CHECK_CONSTRAINTS: "校验约束",
    GENERATE_ACTION_CARDS: "生成建议",
    GENERATE_ACTIONS: "生成建议",
    COLLECT_EVIDENCE: "收集证据",
    EXPLAIN_RECOMMENDATIONS: "生成说明",
    GENERATE_EXPLANATION: "生成说明",
    CREATE_APPROVAL_PACKAGE: "生成审批包",
    WAITING_FOR_APPROVAL: "等待审批",
    CREATE_WRITEBACK_DRAFT: "生成回写草稿",
    MONITOR_EXECUTION: "监控执行",
    LEARN_FROM_FEEDBACK: "沉淀反馈",
    COMPLETE: "完成",
    Open: "待处理",
  };
  return labels[value] || value || "";
};

window.chainpilot.riskLabel = function (risk) {
  const labels = { High: "高", Medium: "中", Low: "低", Critical: "严重" };
  return labels[risk] || risk || "";
};

window.chainpilot.strategyLabel = function (strategy) {
  const labels = {
    Recommended: "推荐方案",
    Conservative: "稳妥方案",
    Aggressive: "进取方案",
    "Agent 推荐方案": "智能推荐方案",
    "AI 推荐方案": "智能推荐方案",
    "Conservative Plan": "稳妥方案",
    "Recommended Plan": "推荐方案",
    "Aggressive Plan": "进取方案",
  };
  return labels[strategy] || strategy || "";
};

window.chainpilot.sourceSystemLabel = function (sourceSystem) {
  const labels = {
    SAP_MOCK: "SAP 模拟快照",
    AIPLAN_DB: "采购分析报告导入",
    SAP: "SAP",
  };
  return labels[sourceSystem] || sourceSystem || "";
};

window.chainpilot.savingTypeLabel = function (savingType) {
  const labels = {
    "Cash Release": "减少采购占用",
    "Book Saving": "账面节省",
    "Purchase Deferral": "采购延期",
  };
  return labels[savingType] || savingType || "";
};

window.chainpilot.sapObjectLabel = function (objectType) {
  const labels = {
    PR: "采购申请",
    PO: "采购订单",
    MRP_PARAM: "MRP 参数",
    PLANNED_ORDER: "计划订单",
  };
  return labels[objectType] || objectType || "";
};

window.chainpilot.recommendationLabel = function (recommendationId) {
  const value = String(recommendationId || "");
  return value ? `建议 ${value.replace(/^REC-/, "")}` : "";
};

(() => {
  const cp = window.chainpilot;
  const workspace = (cp.workspace = cp.workspace || {});
  workspace.evidenceStore = {};

  const NAV_ITEMS = [
    ["chainpilot-ai-command-center", "Supply Planning Model", "计划模型"],
    ["shortage-risk-war-room", "Exception Worksheet", "缺料例外表"],
    ["cash-release-action-package", "Procurement Action Worksheet", "采购动作表"],
    ["master-data-health", "Master Data Inputs", "主数据输入"],
    ["action-inbox", "Action Queue", "动作队列"],
    ["recommendation-detail", "Line Item Detail", "行项目详情"],
    ["algorithm-run-detail", "Optimizer Runs", "优化运行"],
  ];

  const VIEW_TITLES = {
    command: "Supply Planning Model",
    shortage: "Shortage Exception Worksheet",
    cash: "Procurement Action Worksheet",
    master: "Master Data Inputs",
    inbox: "Action Queue",
    recommendation: "Line Item Detail",
    algorithm: "Optimizer Runs",
  };

  workspace.mount = async function (page, view) {
    page.main.html(`<div class="cp-workspace-shell"><div class="cp-loading">正在加载供应链计划数据...</div></div>`);
    try {
      const [runtimeResponse, mockResponse] = await Promise.all([
        frappe.call({ method: "chainpilot_ai.algorithms.service.get_algorithm_runtime_dashboard" }),
        frappe.call({
          method: "chainpilot_ai.snapshots.mock_dashboard.get_mock_data_dashboard",
          args: { history_days: 45 },
        }),
      ]);
      const data = normalizeData(runtimeResponse.message || {}, mockResponse.message || {});
      render(page, view, data);
    } catch (error) {
      console.error(error);
      page.main.find(".cp-workspace-shell").html(`<div class="cp-empty">无法加载工作台数据。</div>`);
    }
  };

  function normalizeData(runtime, mock) {
    const cash = runtime.cash || [];
    const blockedCash = runtime.blocked_cash || [];
    const shortage = runtime.shortage || [];
    const masterData = runtime.master_data || [];
    const runs = runtime.runs || [];
    const latestRun = runs[0] || {};
    const planning = mock.planning_workbench || {};
    const scenario = planning.scenario || {};
    return {
      runtime,
      mock,
      snapshotId: runtime.snapshot_id || (mock.snapshot || {}).snapshot_id || "-",
      snapshotTime: (mock.snapshot || {}).snapshot_time || "-",
      plants: scenario.plants || (mock.snapshot || {}).plant_scope || "CN01、CN02",
      horizon: scenario.horizon || "未来 45 天",
      latestRun,
      shortage,
      cash,
      blockedCash,
      masterData,
      recommendations: runtime.recommendations || [],
      runs,
      planning,
      aiCapabilities: mock.ai_capability_model || defaultAICapabilities(),
      relationScore: relationshipScore(mock.relationship_checks || []),
      cashValue: cash.reduce((sum, item) => sum + Number(item.cash_impact || 0), 0),
      selectedItem: shortage[0] || cash[0] || masterData[0] || {},
    };
  }

  function render(page, view, data) {
    workspace.evidenceStore = {};
    const body = renderView(view, data);
    const firstEvidence = initialEvidenceForView(view, data);
    page.main.find(".cp-workspace-shell").html(`
      <div class="cp-app-frame">
        ${renderNav(view)}
        <section class="cp-app-main">
          ${renderTopHeader(view, data)}
          <div class="cp-work-area">
            <main class="cp-page-content">${body}</main>
            ${CPAiDrawer(firstEvidence)}
          </div>
        </section>
      </div>
    `);
    bindWorkspace(page);
  }

  function renderView(view, data) {
    if (view === "shortage") return renderShortageWarRoom(data);
    if (view === "cash") return renderCashPackage(data);
    if (view === "master") return renderMasterDataHealth(data);
    if (view === "inbox") return renderActionInbox(data);
    if (view === "recommendation") return renderRecommendationDetail(data);
    if (view === "algorithm") return renderAlgorithmRunDetail(data);
    return renderCommandCenter(data);
  }

  function initialEvidenceForView(view, data) {
    if (view === "cash" || view === "recommendation") return data.cash[0] || data.blockedCash[0] || data.selectedItem;
    if (view === "master") return data.masterData[0] || data.selectedItem;
    if (view === "algorithm") return data.runs[0] || data.selectedItem;
    if (view === "inbox") return data.cash[0] || data.shortage[0] || data.masterData[0] || data.selectedItem;
    return data.shortage[0] || data.selectedItem;
  }

  function renderNav(view) {
    return `
      <aside class="cp-side-nav">
        <div class="cp-brand">
          <strong>ChainPilot AI</strong>
          <span>Planner Workspace</span>
        </div>
        <nav>
          ${NAV_ITEMS.map(([route, key, label]) => `
            <button type="button" class="${viewMatches(view, route) ? "active" : ""}" data-route="${route}">
              <span>${cp.escape(label)}</span>
              <small>${cp.escape(key)}</small>
            </button>
          `).join("")}
        </nav>
      </aside>
    `;
  }

  function viewMatches(view, route) {
    const map = {
      command: "chainpilot-ai-command-center",
      shortage: "shortage-risk-war-room",
      cash: "cash-release-action-package",
      master: "master-data-health",
      inbox: "action-inbox",
      recommendation: "recommendation-detail",
      algorithm: "algorithm-run-detail",
    };
    return map[view] === route;
  }

  function renderTopHeader(view, data) {
    const status = data.latestRun.status ? cp.statusLabel(data.latestRun.status) : "模拟预览";
    return `
      <header class="cp-top-header">
        <div>
          <h1>${cp.escape(VIEW_TITLES[view] || "计划模型")}</h1>
          <span>计划版本 基准模拟账套 · 场景 均衡策略 · 工厂 ${cp.escape(data.plants)} · ${cp.escape(data.horizon)} · Snapshot ${cp.escape(data.snapshotTime)}</span>
        </div>
        <div class="cp-header-meta">
          ${CPSeverityBadge(`优化运行 ${status}`, cp.verdictTone(data.latestRun.status || "Ready"))}
          ${CPSeverityBadge(`数据源 ${cp.sourceSystemLabel("SAP_MOCK")}`, "info")}
          <button type="button" class="cp-button primary" data-route="algorithm-run-detail">查看优化运行</button>
        </div>
      </header>
    `;
  }

  function renderCommandCenter(data) {
    const worksheetRows = planningWorksheetRows(data);
    return `
      <section class="cp-model-context">
        <div>
          <span>计划模型</span>
          <strong>供应计划基准模型</strong>
          <small>物料 / 工厂 / 供应商 / SAP 单据</small>
        </div>
        <div>
          <span>计划周期</span>
          <strong>${cp.escape(data.horizon)}</strong>
          <small>缺料预测窗口 14 天</small>
        </div>
        <div>
          <span>场景</span>
          <strong>均衡策略</strong>
          <small>服务水平约束不低于 98%</small>
        </div>
        <div>
          <span>优化运行</span>
          <strong>${cp.statusLabel(data.latestRun.status || "Success")}</strong>
          <small>${cp.escape(data.latestRun.algorithm_run_id || data.snapshotId)}</small>
        </div>
      </section>

      <section class="cp-kpi-strip">
        ${CPMetricCard("缺料例外", cp.number(data.shortage.length), "未来 14 天风险物料", "danger")}
        ${CPMetricCard("预计减少资金占用", cp.currency(data.cashValue), `${cp.number(data.cash.length)} 条可审批动作`, "success")}
        ${CPMetricCard("主数据异常", cp.number(data.masterData.length), "交期 / 安全库存 / MOQ", "warning")}
        ${CPMetricCard("关联完整率", cp.percent(data.relationScore * 100), "SAP 对象到证据链", "info")}
      </section>

      ${CPPlanningCapabilityPanel(data.aiCapabilities)}

      <section class="cp-worksheet-panel">
        <header>
          <div>
            <h2>供应计划工作表</h2>
            <span>按计划员工作流展示物料、库存、需求、SAP 单据、约束和下一步动作。</span>
          </div>
          <div>
            <button type="button" class="cp-button" data-route="shortage-risk-war-room">查看缺料例外</button>
            <button type="button" class="cp-button primary" data-route="cash-release-action-package">生成采购动作表</button>
          </div>
        </header>
        ${CPPlanningWorksheet(worksheetRows)}
      </section>

      <section class="cp-model-board">
        ${CPWorkSection("缺料例外", "查看工作表", "生成动作包", "shortage-risk-war-room", data.shortage.slice(0, 5).map((item) => CPActionCard(item, "shortage")).join(""))}
        ${CPWorkSection("采购动作", "查看工作表", "生成动作包", "cash-release-action-package", data.cash.slice(0, 5).map((item) => CPActionCard(item, "cash")).join(""))}
        ${CPWorkSection("主数据输入", "查看输入表", "生成修正包", "master-data-health", data.masterData.slice(0, 5).map((item) => CPActionCard(item, "master")).join(""))}
      </section>
    `;
  }

  function renderShortageWarRoom(data) {
    const selected = data.shortage[0] || {};
    return `
      <section class="cp-war-room">
        <aside class="cp-list-panel">
          <div class="cp-panel-title">风险物料</div>
          ${data.shortage.slice(0, 10).map((item) => CPActionCard(item, "shortage")).join("") || CPEmpty("暂无缺料风险")}
        </aside>
        <section class="cp-analysis-panel">
          <div class="cp-panel-title">库存投影</div>
          ${CPInventoryProjection(selected)}
          <div class="cp-detail-grid">
            ${CPMetricCard("预计缺料日", selected.shortage_date_p50 || "-", "P50 缺料日期", "danger")}
            ${CPMetricCard("P90 缺口", cp.number(selected.shortage_qty_p90 || 0), "最坏情形缺口", "danger")}
            ${CPMetricCard("缺料概率", cp.percent(Number(selected.shortage_probability_14d || 0) * 100), "14 天窗口", "warning")}
            ${CPMetricCard("影响工单", (selected.affected_production_orders || []).slice(0, 3).join("、") || "-", "生产订单", "info")}
          </div>
          <section class="cp-panel">
            <div class="cp-panel-title">建议动作</div>
            <div class="cp-action-toolbar">
              <button class="cp-button primary">催交采购订单</button>
              <button class="cp-button">启用替代料</button>
              <button class="cp-button">生成紧急采购申请</button>
            </div>
          </section>
        </section>
      </section>
    `;
  }

  function renderCashPackage(data) {
    const lowRisk = data.cash.filter((item) => item.recommendation_level === "L1_AUTO_RECOMMEND");
    const supplierConfirm = data.cash.filter((item) => item.recommendation_level === "L3_SUPPLIER_CONFIRM");
    return `
      <section class="cp-constraint-bar">
        ${CPMetricCard("资金占用降低目标", cp.currency(data.cashValue), "今日动作包", "success")}
        ${CPMetricCard("服务水平", "不低于 98%", "关键物料约束", "info")}
        ${CPMetricCard("保护品类", "保护物料不可动", "硬约束", "warning")}
        ${CPMetricCard("禁止动作", "冻结期 / 低于 MOQ", "自动阻断", "danger")}
      </section>
      <section class="cp-package-grid">
        ${CPActionTable("低风险可审批", lowRisk, "success")}
        ${CPActionTable("需供应商确认", supplierConfirm.length ? supplierConfirm : data.cash.slice(0, 3), "warning")}
        ${CPActionTable("被阻断", data.blockedCash, "danger")}
      </section>
    `;
  }

  function renderMasterDataHealth(data) {
    const score = Math.max(0, 100 - data.masterData.length * 2);
    return `
      <section class="cp-kpi-strip">
        ${CPMetricCard("主数据健康分", `${score}`, "按异常数量折算", score >= 85 ? "success" : "warning")}
        ${CPMetricCard("异常项", cp.number(data.masterData.length), "需要计划员复核", "warning")}
        ${CPMetricCard("影响金额", cp.currency(data.masterData.reduce((sum, item) => sum + Number(item.impact_amount || 0), 0)), "按物料单价估算", "danger")}
        ${CPMetricCard("样本覆盖", "6+ 样本", "供应商履约历史", "info")}
      </section>
      <section class="cp-md-tabs">
        ${CPMasterTab("计划交货期", data.masterData.filter((item) => item.action_type === "REVIEW_SUPPLIER_LEAD_TIME"))}
        ${CPMasterTab("安全库存", data.masterData.filter((item) => item.action_type === "REVIEW_SAFETY_STOCK"))}
        ${CPMasterTab("MOQ/MPQ", data.masterData.filter((item) => item.action_type === "REVIEW_MOQ"))}
        ${CPMasterTab("供应商参数", data.masterData.filter((item) => item.action_type === "REVIEW_SUPPLIER_PARAMETER"))}
      </section>
    `;
  }

  function renderActionInbox(data) {
    return `
      <section class="cp-command-grid">
        ${CPWorkSection("待审批动作", "查看全部", "提交审批", "cash-release-action-package", data.cash.slice(0, 8).map((item) => CPActionCard(item, "cash")).join(""))}
        ${CPWorkSection("缺料风险处理", "查看全部", "生成动作包", "shortage-risk-war-room", data.shortage.slice(0, 8).map((item) => CPActionCard(item, "shortage")).join(""))}
        ${CPWorkSection("主数据复核", "查看全部", "生成修正包", "master-data-health", data.masterData.slice(0, 8).map((item) => CPActionCard(item, "master")).join(""))}
      </section>
    `;
  }

  function renderRecommendationDetail(data) {
    const item = data.cash[0] || data.shortage[0] || data.masterData[0] || {};
    return `
      <section class="cp-detail-page">
        <div class="cp-action-header">
          <div>
            ${CPSapObjectTag(item)}
            <h2>${cp.escape(cp.actionLabel(item.action_type || item.suggested_action) || "处理建议")}</h2>
            <span>${cp.escape(item.material_code || "-")} · ${cp.escape(item.plant || "-")} · ${cp.escape(item.supplier || "-")}</span>
          </div>
          <div class="cp-action-toolbar">
            <button class="cp-button primary">提交审批</button>
            <button class="cp-button">生成回写草稿</button>
            <button class="cp-button">驳回</button>
          </div>
        </div>
        <div class="cp-detail-grid two">
          ${CPBeforeAfter(item)}
          ${CPAlgorithmTrace(item, data.runs)}
          ${CPEvidenceList(item)}
          ${CPConstraintChecklist(item)}
          ${CPExecutionTimeline(item)}
        </div>
      </section>
    `;
  }

  function renderAlgorithmRunDetail(data) {
    return `
      <section class="cp-detail-page">
        <div class="cp-action-header">
          <div>
            <h2>算法运行详情</h2>
            <span>Snapshot ${cp.escape(data.snapshotId)} · 数据源 ${cp.sourceSystemLabel("SAP_MOCK")}</span>
          </div>
          <button class="cp-button primary">重新运行算法</button>
        </div>
        <div class="cp-run-list">
          ${data.runs.map((run) => CPRunRow(run, data)).join("")}
        </div>
        <section class="cp-panel">
          <div class="cp-panel-title">关联 SAP 对象</div>
          <div class="cp-list-stack">
            ${[...data.cash.slice(0, 3), ...data.shortage.slice(0, 2)].map((item) => CPActionCard(item, item.result_type === "SHORTAGE_RISK" ? "shortage" : "cash")).join("")}
          </div>
        </section>
      </section>
    `;
  }

  function CPMetricCard(label, value, meta, tone = "info") {
    return `<article class="cp-metric-card ${tone}"><span>${cp.escape(label)}</span><strong>${cp.escape(value)}</strong><small>${cp.escape(meta)}</small></article>`;
  }

  function CPWorkSection(title, viewAll, action, route, rows) {
    return `
      <section class="cp-work-section">
        <header>
          <h2>${cp.escape(title)}</h2>
          <div>
            <button type="button" class="cp-button" data-route="${cp.escape(route)}">${cp.escape(viewAll)}</button>
            <button type="button" class="cp-button primary" data-route="${cp.escape(route)}">${cp.escape(action)}</button>
          </div>
        </header>
        <div class="cp-list-stack">${rows || CPEmpty("暂无记录")}</div>
      </section>
    `;
  }

  function CPPlanningCapabilityPanel(capabilities) {
    return `
      <section class="cp-capability-panel">
        <header>
          <div>
            <h2>智能计划能力</h2>
            <span>能力嵌入计划模型，不作为独立聊天页面展示。</span>
          </div>
        </header>
        <div class="cp-capability-grid">
          ${(capabilities || []).map((item) => `
            <article class="cp-capability-card">
              <strong>${cp.escape(item.label)}</strong>
              <span>${cp.escape(item.business_role)}</span>
              <small>${cp.escape(item.current_implementation)}</small>
            </article>
          `).join("")}
        </div>
      </section>
    `;
  }

  function CPPlanningWorksheet(rows) {
    return `
      <div class="cp-planning-worksheet">
        <div class="head">
          <span>物料 / 工厂</span>
          <span>SAP 对象</span>
          <span>可用库存</span>
          <span>安全库存</span>
          <span>缺料概率</span>
          <span>P90 缺口</span>
          <span>建议动作</span>
          <span>约束状态</span>
          <span>资金占用影响</span>
          <span>下一步</span>
        </div>
        ${rows.map((row) => {
          const key = registerEvidence(row.raw);
          return `
            <div data-evidence-key="${cp.escape(key)}">
              <span><strong>${cp.escape(row.material_code)}</strong><small>${cp.escape(row.plant)} · ${cp.escape(row.supplier || "-")}</small></span>
              <span>${CPSapObjectTag(row.raw)}</span>
              <span>${cp.number(row.inventory)}</span>
              <span>${cp.number(row.safety_stock)}</span>
              <span>${row.shortage_probability != null ? cp.percent(row.shortage_probability * 100) : "-"}</span>
              <span>${row.shortage_qty != null ? cp.number(row.shortage_qty) : "-"}</span>
              <span>${cp.escape(row.action)}</span>
              <span>${CPSeverityBadge(row.constraint, cp.verdictTone(row.constraint_code))}</span>
              <span>${row.cash_impact ? cp.currency(row.cash_impact) : "-"}</span>
              <span><button type="button" class="cp-row-action">行项目详情</button></span>
            </div>
          `;
        }).join("")}
      </div>
    `;
  }

  function planningWorksheetRows(data) {
    const shortageRows = data.shortage.slice(0, 6).map((item) => {
      const evidence = item.evidence || {};
      return {
        raw: item,
        material_code: item.material_code || "-",
        plant: item.plant || "-",
        supplier: item.supplier || "-",
        inventory: evidence.inventory || 0,
        safety_stock: evidence.safety_stock || 0,
        shortage_probability: Number(item.shortage_probability_14d || 0),
        shortage_qty: item.shortage_qty_p90 || 0,
        action: cp.actionLabel(item.suggested_action) || "处理缺料例外",
        constraint: "需处理",
        constraint_code: "WARN",
        cash_impact: 0,
      };
    });
    const cashRows = data.cash.slice(0, 6).map((item) => {
      const evidence = item.evidence || {};
      return {
        raw: item,
        material_code: item.material_code || "-",
        plant: item.plant || "-",
        supplier: item.supplier || "-",
        inventory: evidence.available_qty || 0,
        safety_stock: evidence.safety_stock || 0,
        shortage_probability: Number(item.risk_after || 0),
        shortage_qty: null,
        action: cp.actionLabel(item.action_type) || "调整采购单据",
        constraint: cp.statusLabel(item.constraint_verdict || "PASS"),
        constraint_code: item.constraint_verdict || "PASS",
        cash_impact: item.cash_impact || 0,
      };
    });
    return [...shortageRows, ...cashRows].slice(0, 10);
  }

  function CPActionCard(item, type) {
    const key = registerEvidence(item);
    const title = type === "shortage" ? item.material_code : type === "master" ? cp.actionLabel(item.action_type) : cp.actionLabel(item.action_type);
    const subtitle = type === "shortage"
      ? `${item.plant || "-"} · 缺料日 ${item.shortage_date_p50 || "-"} · 供应商 ${item.supplier || "-"}`
      : `${item.material_code || "-"} · ${item.plant || "-"} · ${item.supplier || item.sap_doc_no || "-"}`;
    const metric = type === "shortage"
      ? cp.percent(Number(item.shortage_probability_14d || 0) * 100)
      : type === "master"
        ? cp.currency(item.impact_amount || 0)
        : cp.currency(item.cash_impact || 0);
    const tone = type === "shortage" ? "danger" : type === "master" ? "warning" : "success";
    return `
      <article class="cp-action-card" data-evidence-key="${cp.escape(key)}">
        <div>
          ${CPSapObjectTag(item)}
          <strong>${cp.escape(title || "-")}</strong>
          <span>${cp.escape(subtitle)}</span>
        </div>
        <div class="cp-action-metric ${tone}">${cp.escape(metric)}</div>
        <button type="button" class="cp-row-action">证据</button>
      </article>
    `;
  }

  function CPSeverityBadge(label, tone = "neutral") {
    return `<span class="cp-severity ${tone}">${cp.escape(label)}</span>`;
  }

  function CPSapObjectTag(item) {
    const label = cp.sapObjectLabel(item.sap_object_type || (item.sap_doc_no ? "PO" : ""));
    const doc = item.sap_doc_no ? `${item.sap_doc_no}${item.sap_item_no ? `/${item.sap_item_no}` : ""}` : item.material_code || "-";
    return `<span class="cp-sap-tag">${cp.escape(label || "SAP 对象")} · ${cp.escape(doc)}</span>`;
  }

  function CPActionTable(title, rows, tone) {
    return `
      <section class="cp-table-panel">
        <header><h2>${cp.escape(title)}</h2>${CPSeverityBadge(`${cp.number(rows.length)} 条`, tone)}</header>
        <div class="cp-data-table">
          <div class="head"><span>SAP 对象</span><span>物料</span><span>原值</span><span>建议值</span><span>资金占用影响</span><span>风险变化</span><span>约束状态</span></div>
          ${rows.map((item) => {
            const key = registerEvidence(item);
            return `<div data-evidence-key="${cp.escape(key)}"><span>${CPSapObjectTag(item)}</span><span>${cp.escape(item.material_code || "-")}</span><span>${cp.number(item.before_qty || 0)}</span><span>${cp.number(item.after_qty || 0)}</span><span>${cp.currency(item.cash_impact || 0)}</span><span>${cp.percent(Number(item.risk_before || 0) * 100)} → ${cp.percent(Number(item.risk_after || 0) * 100)}</span><span>${CPSeverityBadge(cp.statusLabel(item.constraint_verdict), cp.verdictTone(item.constraint_verdict))}</span></div>`;
          }).join("") || `<div class="cp-table-empty">暂无记录</div>`}
        </div>
      </section>
    `;
  }

  function CPMasterTab(title, rows) {
    return `
      <section class="cp-table-panel">
        <header><h2>${cp.escape(title)}</h2>${CPSeverityBadge(`${cp.number(rows.length)} 条`, rows.length ? "warning" : "success")}</header>
        <div class="cp-data-table master">
          <div class="head"><span>物料</span><span>当前 SAP 值</span><span>建议值</span><span>样本数</span><span>P80/P95</span><span>置信度</span><span>影响金额</span></div>
          ${rows.map((item) => {
            const evidence = item.evidence || {};
            const key = registerEvidence(item);
            return `<div data-evidence-key="${cp.escape(key)}"><span>${cp.escape(item.material_code || "-")}</span><span>${cp.escape(item.before_value ?? "-")}</span><span>${cp.escape(item.after_value ?? "-")}</span><span>${cp.number(item.sample_count || 0)}</span><span>${cp.escape(evidence.lead_time_p80 || evidence.p80 || "-")} / ${cp.escape(evidence.lead_time_p95 || evidence.p95 || "-")}</span><span>${cp.percent(Number(item.confidence_score || 0) * 100)}</span><span>${cp.currency(item.impact_amount || 0)}</span></div>`;
          }).join("") || `<div class="cp-table-empty">暂无异常</div>`}
        </div>
      </section>
    `;
  }

  function CPInventoryProjection(item) {
    const evidence = item.evidence || {};
    const current = Number(evidence.inventory || 0);
    const safety = Number(evidence.safety_stock || 0);
    const shortage = Number(item.shortage_qty_p90 || 0);
    const demand = Math.max(current + shortage - safety, 1);
    const arrival = Math.max(demand * 0.45, 1);
    const maxValue = Math.max(current, safety, shortage, demand, arrival, 1);
    return `
      <div class="cp-projection">
        ${projectionBar("当前库存", current, maxValue, "info")}
        ${projectionBar("预计到货", arrival, maxValue, "success")}
        ${projectionBar("需求", demand, maxValue, "warning")}
        ${projectionBar("安全库存线", safety, maxValue, "neutral")}
        ${projectionBar("P90 缺口", shortage, maxValue, "danger")}
      </div>
    `;
  }

  function projectionBar(label, value, maxValue, tone) {
    const width = Math.max(3, Math.round((Number(value || 0) / maxValue) * 100));
    return `<div class="cp-projection-row"><span>${cp.escape(label)}</span><div><i class="${tone}" style="width:${width}%"></i></div><strong>${cp.number(value)}</strong></div>`;
  }

  function CPBeforeAfter(item) {
    return `<section class="cp-panel"><div class="cp-panel-title">当前 / 建议</div><div class="cp-before-after"><div><span>当前值</span><strong>${cp.escape(item.before_qty ?? item.before_value ?? "-")}</strong></div><div><span>建议值</span><strong>${cp.escape(item.after_qty ?? item.after_value ?? "-")}</strong></div><div><span>影响金额</span><strong>${cp.currency(item.cash_impact || item.impact_amount || 0)}</strong></div></div></section>`;
  }

  function CPAlgorithmTrace(item, runs) {
    const run = (runs || []).find((row) => row.algorithm_run_id === item.algorithm_run) || {};
    return `<section class="cp-panel"><div class="cp-panel-title">算法追踪</div><div class="cp-trace"><span>${cp.escape(algorithmName(item.algorithm_code || run.algorithm_code))}</span><span>版本 ${cp.escape(item.algorithm_version || run.algorithm_version || "-")}</span><span>运行 ${cp.escape(item.algorithm_run || run.algorithm_run_id || "-")}</span><span>状态 ${cp.statusLabel(run.status || "Success")}</span></div></section>`;
  }

  function CPEvidenceList(item) {
    const evidence = item.evidence || {};
    const entries = Object.entries(evidence).slice(0, 8);
    return `<section class="cp-panel"><div class="cp-panel-title">证据链</div><div class="cp-evidence-list">${entries.map(([key, value]) => `<div><span>${cp.escape(evidenceLabel(key))}</span><strong>${cp.escape(Array.isArray(value) ? value.join("、") : value)}</strong></div>`).join("") || CPEmpty("暂无证据")}</div></section>`;
  }

  function CPConstraintChecklist(item) {
    const status = item.constraint_verdict || "PASS";
    const checks = [
      ["SAP 对象", item.sap_doc_no || item.material_code],
      ["算法运行", item.algorithm_run],
      ["证据链", item.evidence ? "已收集" : "缺失"],
      ["约束状态", cp.statusLabel(status)],
      ["审批层级", cp.statusLabel(item.recommendation_level || "L2_REVIEW")],
    ];
    return `<section class="cp-panel"><div class="cp-panel-title">约束校验</div><div class="cp-checklist">${checks.map(([label, value]) => `<div><span>${cp.escape(label)}</span><strong>${cp.escape(value || "-")}</strong></div>`).join("")}</div></section>`;
  }

  function CPExecutionTimeline(item) {
    const steps = ["算法运行", "证据收集", "约束校验", "审批", "回写草稿", "执行监控"];
    return `<section class="cp-panel span-2"><div class="cp-panel-title">审批 / 回写 / 执行时间线</div><div class="cp-timeline">${steps.map((step, index) => `<div class="${index < 3 ? "done" : ""}"><strong>${cp.escape(step)}</strong><span>${index < 3 ? "完成" : "待处理"}</span></div>`).join("")}</div></section>`;
  }

  function CPAiDrawer(item) {
    return `
      <aside class="cp-ai-drawer" data-ai-drawer>
        <div class="cp-drawer-head">
          <span>行项目详情</span>
          <button type="button" data-drawer-close>收起</button>
        </div>
        <div data-drawer-body>${drawerBody(item)}</div>
      </aside>
    `;
  }

  function drawerBody(item) {
    if (!item || !Object.keys(item).length) return CPEmpty("请选择一条业务对象查看证据。");
    return `
      <div class="cp-drawer-section">
        <h3>${cp.escape(item.material_code || item.sap_doc_no || "业务对象")}</h3>
        ${CPSapObjectTag(item)}
      </div>
      ${CPPlanningIntelligence(item)}
      ${CPAlgorithmTrace(item, [])}
      ${CPEvidenceList(item)}
      ${CPConstraintChecklist(item)}
      <div class="cp-action-toolbar vertical">
        <button class="cp-button primary">生成动作包</button>
        <button class="cp-button">提交审批</button>
        <button class="cp-button">查看 SAP 来源</button>
      </div>
    `;
  }

  function CPPlanningIntelligence(item) {
    const type = item.result_type || "";
    const predictive = type === "SHORTAGE_RISK"
      ? `缺料概率 ${cp.percent(Number(item.shortage_probability_14d || 0) * 100)}，P90 缺口 ${cp.number(item.shortage_qty_p90 || 0)}`
      : `风险变化 ${cp.percent(Number(item.risk_before || 0) * 100)} 到 ${cp.percent(Number(item.risk_after || 0) * 100)}`;
    const optimizer = type === "CASH_RELEASE_ACTION"
      ? `动作 ${cp.actionLabel(item.action_type)}，资金占用影响 ${cp.currency(item.cash_impact || 0)}`
      : "该行作为计划输入进入优化运行。";
    return `
      <section class="cp-panel cp-intelligence-panel">
        <div class="cp-panel-title">计划智能</div>
        <div class="cp-intelligence-grid">
          <div><span>预测模型</span><strong>${cp.escape(predictive)}</strong></div>
          <div><span>优化器</span><strong>${cp.escape(optimizer)}</strong></div>
          <div><span>驱动因素</span><strong>${cp.escape(topDriverText(item))}</strong></div>
          <div><span>协同助手</span><strong>可基于当前行生成审批摘要和供应商沟通草稿。</strong></div>
        </div>
      </section>
    `;
  }

  function CPRunRow(run, data) {
    let summary = {};
    try {
      summary = JSON.parse(run.summary_result_json || "{}");
    } catch (error) {
      summary = {};
    }
    return `<section class="cp-panel"><div class="cp-run-row"><div><strong>${algorithmName(run.algorithm_code)}</strong><span>${cp.escape(run.algorithm_run_id || "-")}</span></div><div>${CPSeverityBadge(cp.statusLabel(run.status), cp.verdictTone(run.status))}</div><div><span>结果</span><strong>${cp.number(summary.result_count || summary.candidate_action_count || 0)}</strong></div><div><span>耗时</span><strong>${cp.number(run.duration_ms || 0)} ms</strong></div><button class="cp-button" data-evidence-key="${cp.escape(registerEvidence({ ...run, algorithm_run: run.algorithm_run_id, algorithm_code: run.algorithm_code, evidence: summary }))}">证据</button></div></section>`;
  }

  function registerEvidence(item) {
    const key = item.result_id || item.algorithm_run_id || `${item.sap_doc_no || item.material_code || "item"}-${Object.keys(workspace.evidenceStore).length}`;
    workspace.evidenceStore[key] = item;
    return key;
  }

  function bindWorkspace(page) {
    page.main.find("[data-route]").on("click", function () {
      frappe.set_route($(this).attr("data-route"));
    });
    page.main.find("[data-evidence-key]").on("click", function () {
      const key = $(this).attr("data-evidence-key");
      const item = workspace.evidenceStore[key] || {};
      page.main.find("[data-ai-drawer]").removeClass("collapsed");
      page.main.find("[data-drawer-body]").html(drawerBody(item));
    });
    page.main.find("[data-drawer-close]").on("click", function () {
      page.main.find("[data-ai-drawer]").toggleClass("collapsed");
    });
  }

  function relationshipScore(rows) {
    let total = 0;
    let valid = 0;
    (rows || []).forEach((row) => {
      const match = String(row.value || "").match(/^(\d+)\/(\d+)$/);
      if (match) {
        valid += Number(match[1]);
        total += Number(match[2]);
      }
    });
    return total ? valid / total : 0;
  }

  function topDriverText(item) {
    const evidence = item.evidence || {};
    const drivers = [];
    if (evidence.inventory != null && evidence.safety_stock != null && Number(evidence.inventory) < Number(evidence.safety_stock)) {
      drivers.push("库存低于安全库存");
    }
    if (evidence.demand_std != null) {
      drivers.push(`需求波动 ${evidence.demand_std}`);
    }
    if (Array.isArray(evidence.delay_samples) && evidence.delay_samples.length) {
      drivers.push(`供应延迟样本 ${evidence.delay_samples.slice(0, 3).join("、")}`);
    }
    if (evidence.headroom_qty != null) {
      drivers.push(`可用余量 ${cp.number(evidence.headroom_qty)}`);
    }
    if (item.blocked_reason) {
      drivers.push(item.blocked_reason);
    }
    return drivers.slice(0, 2).join("；") || "证据链已绑定当前 SAP 对象";
  }

  function defaultAICapabilities() {
    return [
      {
        label: "预测模型",
        business_role: "预测缺料概率、P90 缺口、供应延迟和需求波动。",
        current_implementation: "当前模拟阶段使用概率仿真和统计特征。",
      },
      {
        label: "优化器",
        business_role: "在业务约束下选择采购动作包。",
        current_implementation: "当前使用 HiGHS MILP 整数规划求解。",
      },
      {
        label: "驱动因素",
        business_role: "解释库存、需求、供应和约束如何影响结果。",
        current_implementation: "当前由算法证据字段和约束校验生成。",
      },
      {
        label: "协同助手",
        business_role: "围绕当前行生成摘要、草稿和问答。",
        current_implementation: "当前接入可配置 LLM，受证据边界约束。",
      },
    ];
  }

  function evidenceLabel(key) {
    const labels = {
      inventory: "当前库存",
      safety_stock: "安全库存",
      demand_std: "需求波动",
      service_level: "服务水平",
      simulation_count: "仿真次数",
      headroom_qty: "可用余量",
      available_qty: "可用库存",
      demand_horizon: "需求窗口",
      freeze_window_days: "冻结期",
      moq: "最小采购量",
      mpq: "最小包装量",
      lead_time_p50: "交期 P50",
      lead_time_p80: "交期 P80",
      lead_time_p95: "交期 P95",
      unit_price: "单价",
    };
    return labels[key] || key;
  }

  function algorithmName(code) {
    const labels = {
      SHORTAGE_RISK_14D_PROB: "14 天缺料风险",
      CASH_RELEASE_PR_PO_OPT: "资金动作包优化",
      MASTER_DATA_DIAGNOSIS_STAT: "主数据健康诊断",
    };
    return labels[code] || code || "-";
  }

  function CPEmpty(text) {
    return `<div class="cp-empty">${cp.escape(text)}</div>`;
  }
})();
