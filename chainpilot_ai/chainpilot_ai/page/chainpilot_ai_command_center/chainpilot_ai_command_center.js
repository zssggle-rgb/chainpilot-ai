(() => {
  frappe.pages["chainpilot-ai-command-center"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
      parent: wrapper,
      title: "Supply Planning Model",
      single_column: true,
    });
    page.set_primary_action("运行算法", async () => {
      await frappe.call({ method: "chainpilot_ai.algorithms.service.run_algorithm_runtime_rpc" });
      frappe.show_alert({ message: "算法运行完成", indicator: "green" });
      window.chainpilot.workspace.mount(page, "command");
    });
    page.set_secondary_action("SAP 连接", () => frappe.set_route("sap-integration-console"));
    window.chainpilot.workspace.mount(page, "command");
  };
})();
