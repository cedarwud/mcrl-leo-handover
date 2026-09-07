# V0.18 source map

> **PROVISIONAL_V0.18_NO_LEARNED_OR_EFFICACY_CLAIM**

The Python files in this directory are byte-preserved copies for inspection;
they are not a second source of authority and must not be edited in this
package. The repository path shown below is the original path at the time of
packaging.

## Public method/runtime sources

| Package copy | Original repository path | Purpose |
|---|---|---|
| `ee_axis_relational_zr_c3_head.py` | `src/mcrl/algorithms/ee_axis_relational_zr_c3_head.py` | Pure structured relational Q3 scorer; shared victim scorer, signed aggregation, centring, native mask. |
| `ee_axis_relational_zr_c3.py` | `src/mcrl/runtime/ee_axis_relational_zr_c3.py` | Predecision V0.18 observation encoder, schema, physical-key relation, nominal field. |
| `ee_axis_ops3.py` | `src/mcrl/runtime/ee_axis_ops3.py` | Pure OPS-3 projected-persistence Q2 surface and centred target. |
| `ee_axis_ops3_live.py` | `src/mcrl/runtime/ee_axis_ops3_live.py` | Live adapter boundary for cloned native-clock/TLE projection. |
| `ee_surplus_targets.py` | `src/mcrl/runtime/ee_surplus_targets.py` | Canonical EE/surplus target helpers and units. |
| `keyed_fading.py` | `src/mcrl/env/keyed_fading.py` | Keyed common-random field boundary. |

## V0.18 learner-gate preparation copies

| Package copy | Original repository path | Purpose |
|---|---|---|
| `relational_source_schema.py` | `.scratch/multi-catfish-v018-relational-zr/next-learner-draft/relational_source_schema.py` | Immutable no-pickle structured source closure. |
| `relational_q3_learner.py` | `.scratch/multi-catfish-v018-relational-zr/next-learner-draft/relational_q3_learner.py` | One Q3 learner, zero-bootstrap pairwise loss, checkpoint helpers. |
| `relational_q3_gate.py` | `.scratch/multi-catfish-v018-relational-zr/next-learner-draft/relational_q3_gate.py` | Pure gate arithmetic and fixed threshold definitions. |
| `relational_source_bridge.py` | `.scratch/multi-catfish-v018-relational-zr/next-learner-r2/relational_source_bridge.py` | Predecision capture then exact-label attachment. |
| `relational_source_harvester.py` | `.scratch/multi-catfish-v018-relational-zr/next-learner-r2/relational_source_harvester.py` | Production-shaped source shard assembly and receipts. |
| `relational_simulator_source_adapter.py` | `.scratch/multi-catfish-v018-relational-zr/next-learner-r2/relational_simulator_source_adapter.py` | Simulator-to-source adapter boundary. |
| `relational_source_panel_config_builder.py` | `.scratch/multi-catfish-v018-relational-zr/next-learner-r2/relational_source_panel_config_builder.py` | Complete-world panel configuration. |
| `relational_run_config_builder.py` | `.scratch/multi-catfish-v018-relational-zr/next-learner-r2/relational_run_config_builder.py` | Learner run configuration and binding checks. |
| `relational_learner_runner.py` | `.scratch/multi-catfish-v018-relational-zr/next-learner-r2/relational_learner_runner.py` | Exact-update learner runner and receipts. |
| `relational_validation_report.py` | `.scratch/multi-catfish-v018-relational-zr/next-learner-r2/relational_validation_report.py` | Validation metrics and background sidecar handling. |
| `verify_relational_validation_report.py` | `.scratch/multi-catfish-v018-relational-zr/next-learner-r2/verify_relational_validation_report.py` | Independent validation verifier. |
| `relational_gate_orchestrator.py` | `.scratch/multi-catfish-v018-relational-zr/next-learner-r2/relational_gate_orchestrator.py` | Source-only orchestration; no episode training. |

These preparation copies describe the intended next gate, not a completed
learner result. The current V0.18 learner contract remains a draft until its
pre-outcome freeze.

## Reading caveats

- Code comments may contain implementation detail omitted from the paper and
  slides. Do not turn every field name into a public mathematical symbol.
- `z3_bits` is a label/receipt field. It is not a C3 forward feature.
- `background_q12` is an evaluation-only Q1+Q2 sidecar; it is not a second
  deployed decoder.
- The old smoke used an earlier schema before final code-manifest propagation.
  It is retained in `evidence/` only as a wiring/physics receipt.

