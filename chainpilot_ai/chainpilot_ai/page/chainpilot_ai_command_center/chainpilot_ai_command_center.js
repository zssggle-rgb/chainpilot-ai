(() => {
  frappe.pages["chainpilot-ai-command-center"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
      parent: wrapper,
      title: "供应计划目标设定",
      single_column: true,
    });
    window.chainpilot.workspace.mount(page, "command");
  };
})();
