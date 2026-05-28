frappe.pages["action-inbox"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __("Action Inbox"),
    single_column: true,
  });

  page.set_primary_action(__("Open Recommendation List"), () => {
    frappe.set_route("List", "Recommendation");
  });

  page.main.html(`
    <div class="frappe-card">
      <div class="h4">${__("Recommendation Actions")}</div>
      <p class="text-muted">${__("Phase 0 inbox skeleton. Use the list view for filtering and status review.")}</p>
      <div id="chainpilot-action-table"></div>
    </div>
  `);

  frappe.db
    .get_list("Recommendation", {
      fields: [
        "recommendation_id",
        "action_type",
        "sap_object_type",
        "sap_doc_no",
        "sap_item_no",
        "cash_release",
        "approval_status",
        "explanation_status",
      ],
      limit: 10,
      order_by: "cash_release desc",
    })
    .then((rows) => {
      const body = rows
        .map(
          (row) => `
            <tr>
              <td>${frappe.utils.escape_html(row.recommendation_id || "")}</td>
              <td>${frappe.utils.escape_html(row.action_type || "")}</td>
              <td>${frappe.utils.escape_html(row.sap_object_type || "")} ${frappe.utils.escape_html(row.sap_doc_no || "")}/${frappe.utils.escape_html(row.sap_item_no || "")}</td>
              <td class="text-right">${format_currency(row.cash_release || 0)}</td>
              <td>${frappe.utils.escape_html(row.approval_status || "")}</td>
              <td>${frappe.utils.escape_html(row.explanation_status || "")}</td>
            </tr>
          `,
        )
        .join("");
      page.main.find("#chainpilot-action-table").html(`
        <table class="table table-bordered">
          <thead>
            <tr>
              <th>${__("ID")}</th>
              <th>${__("Action")}</th>
              <th>${__("SAP Object")}</th>
              <th class="text-right">${__("Cash Release")}</th>
              <th>${__("Approval")}</th>
              <th>${__("Evidence")}</th>
            </tr>
          </thead>
          <tbody>${body}</tbody>
        </table>
      `);
    });
};
