frappe.listview_settings["Recommendation"] = {
  add_fields: ["cash_release", "approval_status", "writeback_status", "explanation_status"],
  get_indicator(doc) {
    if (doc.explanation_status === "NEED_EVIDENCE") {
      return [__("Needs Evidence"), "orange", "explanation_status,=,NEED_EVIDENCE"];
    }
    if (doc.approval_status === "Approved") {
      return [__("Approved"), "green", "approval_status,=,Approved"];
    }
    if (doc.approval_status === "Rejected") {
      return [__("Rejected"), "red", "approval_status,=,Rejected"];
    }
    return [__("Pending"), "blue", "approval_status,=,Pending"];
  },
};
