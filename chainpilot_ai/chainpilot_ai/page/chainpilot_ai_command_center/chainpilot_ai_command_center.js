(() => {
  frappe.pages["chainpilot-ai-command-center"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
      parent: wrapper,
      title: "计划员处理工作台",
      single_column: true,
    });
    window.chainpilot.workspace.mount(page, "command");
  };
})();
