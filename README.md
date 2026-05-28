# ChainPilot AI

SAP-connected supply chain AI decision and execution agent.

ChainPilot AI turns SAP supply chain planning data and optimization outputs into evidence-backed, approvable, line-level actions. The MVP focuses on the "report to action" loop: Optimization Session, Scenario Result, Recommendation, Evidence, Approval Package, SAP Writeback Draft, and execution feedback.

## Safety Boundary

- SAP remains the system of record.
- The MVP does not write to production SAP.
- AI cannot approve actions or directly modify SAP.
- Formal Recommendations must be tied to Evidence.
- Secrets such as SAP passwords, LLM keys, and API keys must stay in Frappe password fields or environment variables.

## Phase 0 Scope

This repository currently contains the Phase 0 implementation baseline:

- Frappe app skeleton: `chainpilot_ai`
- Core module directories
- Base roles and workspace fixtures
- M1 core DocType JSON files
- Demo data contract and seed file
- Demo import and Phase 0 verification scripts
- Local smoke tests for the static contract

## Local Static Checks

These checks do not require a Frappe bench:

```bash
python3 -m chainpilot_ai.scripts.import_demo_data
python3 -m chainpilot_ai.scripts.run_smoke_tests
python3 -m chainpilot_ai.scripts.verify_phase_0
```

## Bench Checks

The Phase 0 local bench was created at `/Users/sjs/chainpilot-ai-bench` with:

- Frappe: `15.109.0`
- bench: `5.29.1`
- site: `chainpilot.localhost`
- database: MariaDB `10.6.26` on `127.0.0.1:3316`
- app install mode: soft link to this repository as `chainpilot_ai`

From the bench directory:

```bash
bench --site chainpilot.localhost list-apps
bench --site chainpilot.localhost migrate
bench --site chainpilot.localhost run-tests --app chainpilot_ai
bench --site chainpilot.localhost execute chainpilot_ai.scripts.import_demo_data.run
bench --site chainpilot.localhost execute chainpilot_ai.scripts.verify_phase_0.run
```

## Documents

- `docs/PRODUCT_DESIGN.md`
- `docs/MVP_IMPLEMENTATION_BACKLOG.md`
- `docs/PHASE_0_STARTER_PACK.md`
- `docs/PHASE_0_COMPLETION_REPORT.md`
