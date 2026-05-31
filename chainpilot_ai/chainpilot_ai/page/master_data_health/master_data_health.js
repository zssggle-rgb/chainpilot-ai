(() => {
  frappe.pages["master-data-health"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
      parent: wrapper,
      title: "主数据输入",
      single_column: true,
    });
    page.set_primary_action("生成修正包", () => frappe.set_route("action-inbox"));
    page.set_secondary_action("指挥中心", () => frappe.set_route("chainpilot-ai-command-center"));
    window.chainpilot.workspace.mount(page, "master");
  };
})();
