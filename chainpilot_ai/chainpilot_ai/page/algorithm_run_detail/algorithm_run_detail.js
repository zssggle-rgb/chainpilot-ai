(() => {
  frappe.pages["algorithm-run-detail"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
      parent: wrapper,
      title: "优化运行",
      single_column: true,
    });
    page.set_primary_action("重新运行", async () => {
      await frappe.call({ method: "chainpilot_ai.algorithms.service.run_algorithm_runtime_rpc" });
      frappe.show_alert({ message: "算法运行完成", indicator: "green" });
      window.chainpilot.workspace.mount(page, "algorithm");
    });
    page.set_secondary_action("指挥中心", () => frappe.set_route("chainpilot-ai-command-center"));
    window.chainpilot.workspace.mount(page, "algorithm");
  };
})();
