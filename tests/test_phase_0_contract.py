from __future__ import annotations

import json
import unittest
from pathlib import Path

from chainpilot_ai.agent.service import next_state
from chainpilot_ai.optimization.service import calculate_cash_release
from chainpilot_ai.recommendation.service import explanation_status
from chainpilot_ai.sap_connector.service import get_entity_set, sync_endpoint, test_connection, upsert_snapshot
from chainpilot_ai.scripts.import_demo_data import DEFAULT_DEMO_PATH, load_demo_data, validate_demo_data
from chainpilot_ai.scripts.verify_phase_0 import REQUIRED_DOCTYPES, REQUIRED_MODULES, ROOT


class Phase0ContractTest(unittest.TestCase):
    def test_demo_data_contract_is_valid(self) -> None:
        validation = validate_demo_data(load_demo_data(DEFAULT_DEMO_PATH))
        self.assertTrue(validation["ok"], validation["errors"])
        self.assertGreaterEqual(validation["counts"]["optimization_sessions"], 1)
        self.assertGreaterEqual(validation["counts"]["scenarios"], 1)
        self.assertGreaterEqual(validation["counts"]["scenario_results"], 3)
        self.assertGreaterEqual(validation["counts"]["recommendations"], 10)
        self.assertGreaterEqual(validation["counts"]["evidence"], 10)

    def test_ready_recommendations_have_evidence(self) -> None:
        data = load_demo_data(DEFAULT_DEMO_PATH)
        evidence_by_rec: dict[str, list[str]] = {}
        for evidence in data["evidence"]:
            evidence_by_rec.setdefault(evidence["recommendation_id"], []).append(evidence["evidence_id"])
        missing = [
            rec["recommendation_id"]
            for rec in data["recommendations"]
            if rec["explanation_status"] == "Ready" and not evidence_by_rec.get(rec["recommendation_id"])
        ]
        self.assertEqual(missing, [])

    def test_core_doctype_json_files_are_valid(self) -> None:
        for name, path in REQUIRED_DOCTYPES.items():
            self.assertTrue(path.exists(), f"{name} missing at {path}")
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["doctype"], "DocType")
            self.assertEqual(payload["name"], name)
            self.assertEqual(payload["module"], "ChainPilot AI")
        m2_doctypes = [
            "sap_connection/sap_connection.json",
            "sap_endpoint/sap_endpoint.json",
            "sap_field_mapping/sap_field_mapping.json",
            "sap_sync_job/sap_sync_job.json",
            "sap_api_log/sap_api_log.json",
            "sap_material_snapshot/sap_material_snapshot.json",
            "sap_inventory_snapshot/sap_inventory_snapshot.json",
            "sap_pr_line/sap_pr_line.json",
            "sap_po_line/sap_po_line.json",
        ]
        doctype_dir = ROOT / "chainpilot_ai" / "chainpilot_ai" / "doctype"
        for relative_path in m2_doctypes:
            path = doctype_dir / relative_path
            self.assertTrue(path.exists(), f"M2 DocType missing at {path}")
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["doctype"], "DocType")

    def test_module_directories_exist(self) -> None:
        missing = [module for module in REQUIRED_MODULES if not (ROOT / "chainpilot_ai" / module).is_dir()]
        self.assertEqual(missing, [])

    def test_page_skeletons_exist(self) -> None:
        pages = [
            ROOT / "chainpilot_ai" / "chainpilot_ai" / "page" / "chainpilot_ai_command_center" / "chainpilot_ai_command_center.js",
            ROOT / "chainpilot_ai" / "chainpilot_ai" / "page" / "action_inbox" / "action_inbox.js",
            ROOT / "chainpilot_ai" / "chainpilot_ai" / "page" / "scenario_studio" / "scenario_studio.js",
            ROOT / "chainpilot_ai" / "chainpilot_ai" / "page" / "sap_integration_console" / "sap_integration_console.js",
            ROOT / "chainpilot_ai" / "chainpilot_ai" / "doctype" / "scenario" / "scenario.json",
            ROOT / "chainpilot_ai" / "public" / "css" / "chainpilot_ai.css",
            ROOT / "chainpilot_ai" / "chainpilot_ai" / "doctype" / "recommendation" / "recommendation.js",
        ]
        self.assertTrue(all(path.exists() for path in pages))

    def test_service_helpers_are_deterministic(self) -> None:
        self.assertEqual(calculate_cash_release(100, 70), 30.0)
        self.assertEqual(explanation_status(["EVD-001"]), "Ready")
        self.assertEqual(explanation_status([]), "NEED_EVIDENCE")
        self.assertEqual(next_state("CREATED"), "PARSE_USER_GOAL")
        self.assertEqual(test_connection({"mode": "mock"})["status"], "MOCK_READY")
        self.assertEqual(test_connection(None)["status"], "NOT_CONFIGURED")
        rows = get_entity_set("purchase_requisition_items", {"mode": "mock", "plant": "CN01"})
        self.assertGreaterEqual(len(rows), 1)
        material_rows = get_entity_set("material_master", {"mode": "mock", "plant": "CN01"})
        self.assertGreaterEqual(len(material_rows), 1)
        sync_result = sync_endpoint("purchase_requisition_items", {"mode": "mock", "dry_run": True})
        self.assertEqual(sync_result["status"], "Success")
        self.assertEqual(sync_result["rows_upserted"], 2)
        self.assertEqual(get_entity_set("purchase_requisition_items"), [])
        self.assertEqual(upsert_snapshot("SAP Snapshot", {"doc": "100", "item": "10"}, ["doc", "item"]), "100::10")


if __name__ == "__main__":
    unittest.main()
