window.chainpilot_ai = window.chainpilot_ai || {};
window.chainpilot = window.chainpilot || {};

window.chainpilot.escape = function (value) {
  return frappe.utils.escape_html(value == null ? "" : String(value));
};

window.chainpilot.currency = function (value) {
  return format_currency(value || 0, frappe.defaults.get_default("currency") || "USD", 0);
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
  if (risk === "High") return "red";
  if (risk === "Medium") return "amber";
  return "green";
};

window.chainpilot.verdictTone = function (verdict) {
  if (["BLOCK", "BLOCKED", "Failed", "Rejected"].includes(verdict)) return "red";
  if (["WARN", "PASS_WITH_APPROVAL", "Pending"].includes(verdict)) return "amber";
  if (["PASS", "Approved", "Ready"].includes(verdict)) return "green";
  return "neutral";
};

window.chainpilot.actionLabel = function (actionType) {
  const labels = {
    REDUCE_PR_QTY: __("下调 PR 数量"),
    DELAY_UNCONFIRMED_PO: __("延后未确认 PO"),
    ADVANCE_RISK_MATERIAL: __("提前风险物料"),
    REVIEW_SAFETY_STOCK: __("复核安全库存"),
    REVIEW_SUPPLIER_LEAD_TIME: __("复核供应商交期"),
  };
  return labels[actionType] || actionType || "";
};
