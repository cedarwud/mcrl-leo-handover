# Package manifest

Package: `multi-catfish-v018-web-agent-package-20260904-r1`  
Status: `PROVISIONAL_V0.18_NO_LEARNED_OR_EFFICACY_CLAIM`  
Created: 2026-09-04 (Asia/Taipei)

This package is additive and self-contained for method authoring. It includes
copy-preserved source/evidence files and compact authoring instructions. The
hash manifest covers every regular file below except `MANIFEST.sha256` itself;
the manifest file is intentionally self-excluding so it can be regenerated
without a circular digest.

## Authoring files

- `START-HERE.md`
- `CLAIM-STATUS.md`
- `SUPERSESSION-MAP.md`
- `METHOD-BRIEF.md`
- `FIGURE-DECK-BRIEF.md`
- `WEB-AGENT-PROMPT.md`

## Contract and review copies

- `contracts/MULTI-CATFISH-MCRL-V018-ANALYTIC-DIAGNOSTIC-PREREG-2026-09-04.md`
- `contracts/MULTI-CATFISH-MCRL-V018-RELATIONAL-Q3-LEARNER-PREREG-DRAFT-2026-09-04.md`
- `contracts/POSTRESULT-CROSS-MODEL-ADJUDICATION-2026-09-04.md`
- `contracts/MULTI-CATFISH-C2-OPS3-FRESH-REVIEW-2026-09-02.md`
- `contracts/MULTI-CATFISH-C2-OPS3-FORMULA-PROBE-CONTRACT-2026-09-02.md`

## Evidence copies

- `evidence/analytic-panel-result.json`
- `evidence/analytic-panel-merge.log`
- `evidence/old-seed-smoke-metadata.json`
- `evidence/old-seed-smoke-bridge.json`
- `evidence/old-seed-smoke-harvest.json`
- `evidence/old-seed-smoke.log`
- `evidence/old-seed-smoke.complete`
- `evidence/bridge.sha256`
- `evidence/capture-sequence.sha256`
- `evidence/decision-context.sha256`
- `evidence/harvest.sha256`
- `evidence/source.sha256`

## Provenance copies

- `provenance/LOCAL-SEED-CENSUS.md`
- `provenance/SERVER-SEED-CENSUS.md`
- `provenance/NEXT-LEARNER-READINESS.md`
- `provenance/learner-seam-draft.md`
- `provenance/spec.md`

## Source copies

See `source-map/README.md` for original repository paths. The copied source
files are:

- `source-map/ee_axis_ops3.py`
- `source-map/ee_axis_ops3_live.py`
- `source-map/ee_axis_relational_zr_c3.py`
- `source-map/ee_axis_relational_zr_c3_head.py`
- `source-map/ee_surplus_targets.py`
- `source-map/keyed_fading.py`
- `source-map/relational_gate_orchestrator.py`
- `source-map/relational_learner_runner.py`
- `source-map/relational_q3_gate.py`
- `source-map/relational_q3_learner.py`
- `source-map/relational_run_config_builder.py`
- `source-map/relational_simulator_source_adapter.py`
- `source-map/relational_source_bridge.py`
- `source-map/relational_source_harvester.py`
- `source-map/relational_source_panel_config_builder.py`
- `source-map/relational_source_schema.py`
- `source-map/relational_validation_report.py`
- `source-map/verify_relational_validation_report.py`

`source-map/README.md` is also part of the copied source map. These files let
a web agent inspect tensor shapes and boundaries without guessing; they remain
provisional implementation copies.

## Regeneration

From the repository root:

```text
cd artifacts/multi-catfish-v018-web-agent-package-20260904-r1
find . -type f ! -name MANIFEST.sha256 -print0 | sort -z | xargs -0 sha256sum > MANIFEST.sha256
```
