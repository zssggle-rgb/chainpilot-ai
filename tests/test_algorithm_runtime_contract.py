from __future__ import annotations

import json
import unittest
from pathlib import Path

from chainpilot_ai.algorithms.registry import run_mvp_algorithms
from chainpilot_ai.algorithms.quality import evaluate_algorithm_quality
from chainpilot_ai.recommendation.result_to_recommendation import convert_algorithm_results
from chainpilot_ai.scripts.verify_algorithm_runtime import run as verify_algorithm_runtime
from chainpilot_ai.snapshots.mock_loader import DEFAULT_MOCK_SAP_SNAPSHOT_PATH, load_mock_sap_snapshot
from chainpilot_ai.snapshots.snapshot_service import build_snapshot_run
from chainpilot_ai.snapshots.validators import validate_mock_sap_snapshot

ROOT = Path(__file__).resolve().parents[1]


class AlgorithmRuntimeContractTest(unittest.TestCase):
    def test_mock_sap_snapshot_contract(self) -> None:
        data = load_mock_sap_snapshot()
        validation = validate_mock_sap_snapshot(data)
        self.assertTrue(validation["ok"], validation["errors"])
        self.assertGreaterEqual(validation["counts"]["materials"], 180)
        self.assertGreaterEqual(validation["counts"]["pr_lines"], 300)
        self.assertGreaterEqual(validation["counts"]["po_lines"], 250)
        self.assertGreaterEqual(validation["counts"]["planned_demands"], 500)
        self.assertEqual(DEFAULT_MOCK_SAP_SNAPSHOT_PATH.name, "mock_sap_snapshot_v1.json")
        self.assertEqual(data["snapshot"]["source_system"], "SAP_MOCK_REALISTIC")
        self.assertGreaterEqual(validation["counts"]["supplier_performance"], 1000)
        snapshot_run = build_snapshot_run(data)
        self.assertEqual(snapshot_run["snapshot_id"], data["snapshot"]["snapshot_id"])
        self.assertEqual(snapshot_run["record_count_mrp_parameters"], validation["counts"]["mrp_parameters"])

    def test_mock_sap_snapshot_references_are_consistent(self) -> None:
        data = load_mock_sap_snapshot()
        materials = {(row["material_code"], row["plant"]) for row in data["materials"]}
        for section in ("inventory", "mrp_parameters", "planned_demands", "consumption_history", "supplier_performance", "pr_lines", "po_lines"):
            missing = [
                (row["material_code"], row["plant"])
                for row in data[section]
                if (row["material_code"], row["plant"]) not in materials
            ]
            self.assertEqual(missing, [], section)

    def test_algorithm_runtime_outputs_required_counts(self) -> None:
        runtime = run_mvp_algorithms(load_mock_sap_snapshot())
        self.assertTrue(runtime["ok"])
        self.assertEqual(runtime["counts"]["algorithm_runs"], 3)
        self.assertGreaterEqual(runtime["counts"]["shortage_results"], 5)
        self.assertGreaterEqual(runtime["counts"]["cash_release_results"], 20)
        self.assertGreaterEqual(runtime["counts"]["master_data_results"], 15)
        cash_summary = next(run["summary"] for run in runtime["runs"] if run["run"]["algorithm_code"] == "CASH_RELEASE_PR_PO_OPT")
        shortage_summary = next(run["summary"] for run in runtime["runs"] if run["run"]["algorithm_code"] == "SHORTAGE_RISK_14D_PROB")
        self.assertLessEqual(shortage_summary["avg_forecast_wape"], 0.12)
        self.assertGreaterEqual(shortage_summary["avg_forecast_confidence"], 0.85)
        self.assertGreaterEqual(shortage_summary["forecast_backtest_materials"], 100)
        self.assertGreaterEqual(cash_summary["selected_actions"], 10)
        self.assertGreaterEqual(cash_summary["blocked_actions"], 1)
        self.assertIn(cash_summary["solver_name"], {"HiGHS MILP", "精确整数枚举"})
        self.assertIn(cash_summary["solver_status"], {"OPTIMAL", "FEASIBLE", "TRUNCATED_OPTIMAL"})
        self.assertIn("objective_components", cash_summary)
        self.assertIn("constraint_utilization", cash_summary)
        self.assertEqual(cash_summary["mip_gap"], 0.0)
        self.assertGreaterEqual(cash_summary["decision_variable_count"], cash_summary["selected_actions"])

    def test_algorithm_results_convert_to_traceable_recommendations(self) -> None:
        runtime = run_mvp_algorithms(load_mock_sap_snapshot())
        generated = convert_algorithm_results(runtime)
        self.assertGreaterEqual(len(generated["recommendations"]), 20)
        self.assertEqual(len(generated["recommendations"]), len(generated["evidence"]))
        self.assertEqual(len(generated["recommendations"]), len(generated["checks"]))
        self.assertEqual(len(generated["recommendations"]), len(generated["explanations"]))
        for recommendation in generated["recommendations"]:
            self.assertEqual(recommendation["snapshot_id"], runtime["snapshot_id"])
            self.assertTrue(recommendation["algorithm_run"])
            self.assertTrue(recommendation["algorithm_result"])
            self.assertGreater(recommendation["evidence_count"], 0)
            self.assertIn(recommendation["constraint_verdict"], {"PASS", "PASS_WITH_APPROVAL"})
        for explanation in generated["explanations"]:
            self.assertEqual(explanation["status"], "Ready")
            self.assertTrue(explanation["evidence_ids_used"])

    def test_doctype_json_files_include_algorithm_runtime(self) -> None:
        doctype_dir = ROOT / "chainpilot_ai" / "chainpilot_ai" / "doctype"
        required = [
            "sap_snapshot_run/sap_snapshot_run.json",
            "sap_bom_component_snapshot/sap_bom_component_snapshot.json",
            "sap_planned_demand_snapshot/sap_planned_demand_snapshot.json",
            "sap_consumption_history_snapshot/sap_consumption_history_snapshot.json",
            "sap_supplier_performance_snapshot/sap_supplier_performance_snapshot.json",
            "sap_mrp_parameter_snapshot/sap_mrp_parameter_snapshot.json",
            "algorithm_definition/algorithm_definition.json",
            "algorithm_run/algorithm_run.json",
            "algorithm_result/algorithm_result.json",
            "ai_explanation/ai_explanation.json",
        ]
        for relative in required:
            payload = json.loads((doctype_dir / relative).read_text(encoding="utf-8"))
            self.assertEqual(payload["doctype"], "DocType")
            self.assertEqual(payload["module"], "ChainPilot AI")

    def test_verify_algorithm_runtime_script_passes(self) -> None:
        report = verify_algorithm_runtime()
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["counts"]["Pass"], 4)

    def test_algorithm_quality_gates_pass_on_mock_history(self) -> None:
        report = evaluate_algorithm_quality(history_days=45, sample_interval_days=14)
        self.assertTrue(report["ok"], report["quality_gates"])
        self.assertLessEqual(report["forecast_quality"]["avg_wape"], 0.12)
        self.assertGreaterEqual(report["optimizer_quality"]["selected_actions"], 15)
        self.assertTrue(all(row["pass"] for row in report["quality_gates"]))


if __name__ == "__main__":
    unittest.main()
