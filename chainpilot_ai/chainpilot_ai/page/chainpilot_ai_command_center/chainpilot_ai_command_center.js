frappe.pages["chainpilot-ai-command-center"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __("ChainPilot AI Command Center"),
    single_column: true,
  });

  page.main.html(`
    <div class="chainpilot-command-center">
      <div class="frappe-card">
        <div class="h4">${__("Phase 0 Demo Control Tower")}</div>
        <p class="text-muted">${__("Shows imported optimization sessions, scenario results, and recommendation actions.")}</p>
      </div>
      <div class="row mt-4" id="chainpilot-kpis"></div>
    </div>
  `);

  const render = (counts) => {
    const items = [
      [__("Optimization Sessions"), counts.optimization_sessions || 0],
      [__("Scenario Results"), counts.scenario_results || 0],
      [__("Recommendations"), counts.recommendations || 0],
      [__("Evidence Records"), counts.evidence || 0],
    ];
    page.main.find("#chainpilot-kpis").html(
      items
        .map(
          ([label, value]) => `
            <div class="col-sm-3">
              <div class="frappe-card text-center">
                <div class="text-muted">${label}</div>
                <div class="h2 mt-2">${value}</div>
              </div>
            </div>
          `,
        )
        .join(""),
    );
  };

  Promise.all([
    frappe.db.count("Optimization Session"),
    frappe.db.count("Scenario Result"),
    frappe.db.count("Recommendation"),
    frappe.db.count("Recommendation Evidence"),
  ])
    .then(([optimization_sessions, scenario_results, recommendations, evidence]) => {
      render({ optimization_sessions, scenario_results, recommendations, evidence });
    })
    .catch(() => render({}));
};
