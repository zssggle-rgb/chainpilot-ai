(() => {
  frappe.pages["shortage-risk-war-room"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
      parent: wrapper,
      title: "缺料例外表",
      single_column: true,
    });
    page.set_primary_action("生成动作包", () => frappe.set_route("cash-release-action-package"));
    page.set_secondary_action("指挥中心", () => frappe.set_route("chainpilot-ai-command-center"));
    window.chainpilot.workspace.mount(page, "shortage");
  };
})();
