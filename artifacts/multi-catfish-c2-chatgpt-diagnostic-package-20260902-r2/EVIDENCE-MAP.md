# Evidence map

## Binding/current orientation

- `docs/CURRENT-MULTI-CATFISH-AUTHORITY.md` — current supersession and gate
  status; later sealed evidence overrides older narrative.
- `docs/MULTI-CATFISH-EE-AXIS-REDESIGN-CONTRACT-V0.3-2026-08-31.md` — original
  fixed-lambda three-view formula and direct-sum deployment contract.
- `docs/MULTI-CATFISH-MCRL-V03-ALGORITHM-SPEC-2026-08-31.md` — algorithm-level
  method entry point; read with later supersession notices.
- `docs/MULTI-CATFISH-MCRL-V03-E1-INSTRUMENT-VALIDITY-CONTRACT-2026-08-31.md`,
  the action-shared amendment, and `docs/ADR-007-action-shared-three-q-instrument.md`
  — learner/instrument validity and action-shared architecture.
- `docs/MULTI-CATFISH-C2-PARALLEL-DESIGN-ADJUDICATION-2026-09-02.md` — common
  pre-outcome comparison rules for competing new C2 proposals.
- `docs/MULTI-CATFISH-C2-OPS3-FORMULA-PROBE-CONTRACT-2026-09-02.md` — current
  frozen OPS-3 formula, mechanics tests, unopened seed panel, and stop rules;
  this authorizes no learner or training.
- `CURRENT-C2-DIAGNOSIS.md` — compact supersession-aware status snapshot.

## Independent/current candidates

- `docs/MULTI-CATFISH-C2-FABLE-51-CLEANROOM-REVIEW-2026-09-02.md` — Fable 5.1
  clean-room diagnosis and option-value proposal.
- `docs/MULTI-CATFISH-C2-OPS3-FRESH-REVIEW-2026-09-02.md` — fresh-context Sol
  audit and formula-complete OPS-3 projected-persistence proposal; untested.
- `docs/MULTI-CATFISH-C2-PROJECTED-SHAPING-CANDIDATE-2026-09-02.md` — earlier
  Codex forecast-shaping draft retained to expose the defects OPS-3 corrected;
  not a live formula candidate by itself.

## C1/C3 and integration evidence

- `docs/MULTI-CATFISH-MCRL-C1-C3-PAPER-AUTHORING-DELTA-2026-09-01.md` — current
  C1/C3 formula/state/source description.
- `docs/MULTI-CATFISH-MCRL-V04-FIVE-ARM-ABLATION-RESULT-2026-09-01.md` — frozen
  five-arm development/confirmatory results and old-Q2 harm.
- `docs/MULTI-CATFISH-MCRL-V04-C3-CONFIRMATORY-RESULT-2026-09-01.md` — C3 result
  in its declared old-Q2 context.
- The packaged C3 victim-burden decision, screen result, and confirmatory
  preregistration explain how that route was selected and bounded.
- `docs/MULTI-CATFISH-MCRL-V04-ROUTE-INTERACTION-DIAGNOSTIC-2026-09-01.md` and
  `evidence/v04-route-interaction-result.json` — post-outcome route interactions,
  including C3's negative Q1-only-context marginal.

## C2 negative evidence

- `docs/MULTI-CATFISH-MCRL-V05-C2-CONTROLLED-TAPE-DISPOSITION-2026-09-01.md`
  and `evidence/v05-support-failure-receipt.json` — deterministic native-support
  failure for the common downstream action tape.
- `docs/MULTI-CATFISH-MCRL-V06-C2-K1-T1-FINAL-AUDIT-2026-09-02.md` — V0.6
  source/implementation audit.
- The packaged V0.4 C2 failure forensics and V0.6 K1 preregistrations document
  earlier hypotheses and prevent retrospective reinterpretation.
- `evidence/v06-d0-diagnostic.json` and `evidence/v06-loowo-diagnostic.json` —
  existing policy-cascade and held-out diagnostics.
- `evidence/v04-c2-failure-result.json` and its seal — raw old-Q2 failure
  receipt.
- `evidence/v06-bounded-evaluation-result.json` and its seal — raw V0.6 learned
  C2 evaluation receipt.
- `docs/MULTI-CATFISH-MCRL-V07-C2-FOCAL-NEXT-DESIGN-DECISION-2026-09-02.md` —
  V0.7 hypothesis and inherited failure diagnosis.
- `docs/MULTI-CATFISH-MCRL-V07-C2-BALANCED-DEVELOPMENT-GATE-RESULT-2026-09-02.md`
  — R13 near-zero outcome.
- `evidence/v07-r13-balanced.json` and `evidence/v07-r14-loao.json` — raw
  development receipts used for the R13/R14 conclusions.

## Simulator and learner authority

- `source/env/step.py` — action execution, recurrence segments, rate/power,
  reward-only handover field, no-commit evaluation.
- `source/env/link_budget.py` — recurrence power, feasibility, per-beam max,
  PA/fixed/system power, and Shannon rate.
- `source/env/scenario.py` and `source/env/candidates.py` — deterministic TLE
  projection, D2/dwell timing, candidate windows, and masks.
- `source/env/d2.py`, `source/env/geometry.py`, and
  `source/env/interference.py` — future D2 latch, cell/user geometry, and
  canonical co-channel interference seams required by OPS-3.
- `source/env/antenna.py`, `cells.py`, `constants.py`, `dwell.py`, and
  `keyed_fading.py` — supporting physical definitions needed to audit those
  seams.
- `source/runtime/ee_axis_v04_c3_state.py` — action-aligned C3 victim-burden
  state that made C3 learnable.
- `source/runtime/ee_axis_state.py`, `ee_surplus_targets.py`,
  `energy_efficiency.py`, and `outage_gate.py` — shared state, target, final EE,
  and service-gate authority.
- Packaged C1/C3 source, selector, schedule, dataset, and learnability modules
  provide the current route implementations.
- `source/runtime/ee_axis_v07_c2_state.py` and
  `source/runtime/ee_axis_v07_c2_focal_next.py` — failed V0.7 C2 state/target.
- `source/algorithms/ee_axis_pairwise.py` and
  `source/algorithms/ee_axis_v04_hybrid.py` — common scale, pairwise learner,
  and direct deployed Q sum.
- `source/runners/` — copied evaluation/adapter entry points used to interpret
  the receipts; these are evidence helpers, not a runnable self-contained repo.
- `IMPLEMENTATION-SEAM-AUDIT.md` — read-only feasibility map of which existing
  physical helpers can be reused and which old branch evaluators cannot.
