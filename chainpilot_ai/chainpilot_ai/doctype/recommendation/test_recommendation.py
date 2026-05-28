import frappe
from frappe.tests.utils import FrappeTestCase


class TestRecommendation(FrappeTestCase):
    def setUp(self):
        for doctype, name in [
            ("Constraint Check Result", "TEST-CHK-001"),
            ("Recommendation Evidence", "TEST-EVD-001"),
            ("Recommendation", "TEST-REC-001"),
            ("Scenario Result", "TEST-RST-001"),
            ("Optimization Session", "TEST-CCO-001"),
        ]:
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=True)

    def test_recommendation_requires_evidence_for_ready_status(self):
        frappe.get_doc(
            {
                "doctype": "Optimization Session",
                "session_id": "TEST-CCO-001",
                "source_system": "TEST",
                "source_report": "phase0_test",
                "baseline_amount": 1000000,
                "material_count": 10,
                "sample_count": 3,
                "best_solution_count": 1,
                "run_date": "2026-05-28",
                "status": "Imported",
            }
        ).insert(ignore_permissions=True)

        frappe.get_doc(
            {
                "doctype": "Scenario Result",
                "result_id": "TEST-RST-001",
                "session_id": "TEST-CCO-001",
                "strategy_name": "Phase 0 Test",
                "strategy_type": "Recommended",
                "purchase_amount": 900000,
                "cash_release": 100000,
                "cash_release_rate": 10,
                "risk_level": "Low",
                "recommendation_count": 1,
            }
        ).insert(ignore_permissions=True)

        frappe.get_doc(
            {
                "doctype": "Recommendation",
                "recommendation_id": "TEST-REC-001",
                "result_id": "TEST-RST-001",
                "action_type": "REDUCE_PR_QTY",
                "sap_object_type": "PR",
                "sap_doc_no": "TEST-PR-001",
                "sap_item_no": "00010",
                "material_code": "TEST-MAT-001",
                "plant": "CN01",
                "cash_release": 100000,
                "saving_type": "Cash Release",
                "approval_status": "Pending",
                "writeback_status": "Not Created",
                "explanation_status": "Ready",
            }
        ).insert(ignore_permissions=True)

        frappe.get_doc(
            {
                "doctype": "Recommendation Evidence",
                "evidence_id": "TEST-EVD-001",
                "recommendation_id": "TEST-REC-001",
                "source_type": "Snapshot",
                "source_id": "TEST-SNAPSHOT",
                "metric_name": "inventory_days_after",
                "metric_value": "36",
                "threshold_value": "28",
                "verdict": "PASS",
                "summary": "Inventory coverage remains above threshold.",
            }
        ).insert(ignore_permissions=True)

        count = frappe.db.count("Recommendation Evidence", {"recommendation_id": "TEST-REC-001"})
        self.assertEqual(count, 1)
