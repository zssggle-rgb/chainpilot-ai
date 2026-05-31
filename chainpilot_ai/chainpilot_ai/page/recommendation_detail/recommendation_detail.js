(() => {
  frappe.pages["recommendation-detail"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
      parent: wrapper,
      title: "Line Item Detail",
      single_column: true,
    });
    page.set_primary_action("提交审批", () => frappe.set_route("action-inbox"));
    page.set_secondary_action("返回动作包", () => frappe.set_route("cash-release-action-package"));
    window.chainpilot.workspace.mount(page, "recommendation");
  };
})();
