# ChainPilot AI Demo Data

`phase0_demo.json` is the minimum Phase 0 data pack used to validate the report-to-action loop without a live SAP OData connection.

It contains:

- 1 Optimization Session
- 3 Scenario Results
- 10 Recommendations
- 10 Recommendation Evidence records
- 10 Constraint Check Result records

Run local validation:

```bash
python3 -m chainpilot_ai.scripts.import_demo_data
python3 -m chainpilot_ai.scripts.verify_phase_0
```
