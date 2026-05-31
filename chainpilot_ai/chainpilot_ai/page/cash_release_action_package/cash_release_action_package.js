(() => {
  frappe.pages["cash-release-action-package"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
      parent: wrapper,
      title: "采购动作表",
      single_column: true,
    });
    page.set_primary_action("提交审批", () => frappe.set_route("recommendation-detail"));
    page.set_secondary_action("指挥中心", () => frappe.set_route("chainpilot-ai-command-center"));
    window.chainpilot.workspace.mount(page, "cash");
  };
})();
