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
    DELAY_UNCONFIRMED_PO: "延后未确认采购订单",
    ADVANCE_RISK_MATERIAL: "提前风险物料采购",
    REVIEW_SAFETY_STOCK: "复核安全库存",
    REVIEW_SUPPLIER_LEAD_TIME: "复核供应商交期",
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
    New: "新建",
    Applied: "已应用",
    Ignored: "已忽略",
    Countered: "供应商还价",
    Accepted: "已接受",
    "Accepted with later ship date": "接受但要求调整交期",
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
