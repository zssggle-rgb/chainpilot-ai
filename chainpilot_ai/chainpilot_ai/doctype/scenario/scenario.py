from __future__ import annotations

import frappe
from frappe.model.document import Document


class Scenario(Document):
    def validate(self) -> None:
        if self.target_cash_release and self.target_cash_release < 0:
            frappe.throw("Target Cash Release cannot be negative.")
