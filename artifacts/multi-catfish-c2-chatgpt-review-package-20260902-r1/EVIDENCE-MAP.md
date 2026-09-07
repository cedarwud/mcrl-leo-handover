# Evidence map

Use the labels **verified fact**, **inference**, and **proposal** throughout.
Later receipts and code may correct older prose, but this package does not
change shared project authority.

## Package verification

- `CHATGPT-REVIEW-PROMPT.md` — package-grounded receipt/formula/project
  adjudication; no external research required.
- `CHATGPT-DEEP-RESEARCH-PROMPT.md` — separate primary-literature review of
  scalar-aligned three-head feasibility and complementary C3 design.
- `INTEGRATION-VERIFICATION.md` — package-level receipt, number, and OPS-3
  protocol cross-check; identifies the material discrepancy in the O-arm name.
- `verification/recompute_stage1b.py` — independently pools raw episode rows as
  total bits divided by total energy and reproduces all six primary directions.
- `MANIFEST.sha256` — one integrity manifest for every other packaged file.

## Current challenger evidence

- `fable-cleanroom-lane/FABLE-51-C2-CLEANROOM-V08-DESIGN-DECISION-2026-09-02.md`
  — full Fable clean-room decision, causal map, audit summary, hypotheses,
  census, Stage 1b results, decision, and un-applied patch plan.
- `fable-cleanroom-lane/FABLE-LANE-README.md` — lane-local reading order and
  scope warning.
- `fable-cleanroom-lane/oracle/stage1b-report.md` — generated arm tables,
  primary directions, service guard, decision strings, and diagnostics.
- `fable-cleanroom-lane/contracts/V08-C2-STAGE1B-ORACLE-SCREEN-CONTRACT-2026-09-02.md`
  — frozen H-A screen contract, hash
  `2ac39ce557ed23596728d9a83619ce585c9c30e308559bd20f48d08c0e6d1545`.
- `fable-cleanroom-lane/contracts/V08-C2-STAGE1B-ADDENDUM-OPS3-VARIANT-2026-09-02.md`
  — frozen second-surface addendum, hash
  `b538932006f7e597ee199fb0701a4473587afa81b4580ca76e1dff13f9ea7046`.
- The two matching contract `.sha256` files preserve their recorded
  pre-outcome hashes.
- `evidence/v08-stage1b-ha-result.json` — copied H-A result with raw episode
  rows and stored pooled/per-initialization summaries.
- `evidence/v08-stage1b-fable-ops3-reading-result.json` — copied O-arm result;
  this is the Fable lane's interpretation, not exact current OPS-3.
- `fable-cleanroom-lane/oracle/run_v08_c2_oracle_screen.py` and
  `make_stage1b_report.py` — copied challenger runner/report source used to
  audit the method and reconstruct its report.
- `fable-cleanroom-lane/receipt.json` and
  `RECEIPT-DIR-MANIFEST.sha256` — receipt summary and preserved manifest of the
  full challenger artifact directory. The package-wide manifest is separate.

## H-A mechanism census

- `fable-cleanroom-lane/census/census-report.md` — human-readable setup,
  prediction check, action spread, headroom, hold behavior, and limitations.
- `evidence/v08-ha-census-result.json` — copied machine-readable census result.
- `fable-cleanroom-lane/census/census-result.json` — lane-local copy of the
  same census result, retained with the challenger materials.
- `fable-cleanroom-lane/census/run_census.py` and `analyze.py` — copied census
  source for method review.

The large raw NPZ and row JSONL files remain in the original challenger
artifact and are authenticated by its preserved receipt manifest; they are not
needed to recompute the six primary directions because the packaged result
JSON files contain their raw episode rows.

## C1/C3 and causal audits

- `fable-cleanroom-lane/audit/c1c3-health-audit.md` — code/receipt audit,
  lambda0 provenance issue, and context-limit classification.
- `fable-cleanroom-lane/audit/ee-causal-map.md` — action-to-bits/energy paths.
- `fable-cleanroom-lane/audit/number-authentication.md` — independent
  recomputation of the older headline results.
- `docs/MULTI-CATFISH-MCRL-C1-C3-PAPER-AUTHORING-DELTA-2026-09-01.md` — current
  C1/C3 formula/state/source description, subject to the audit findings.
- `docs/MULTI-CATFISH-MCRL-V04-FIVE-ARM-ABLATION-RESULT-2026-09-01.md` — old-Q2
  five-arm result.
- `docs/MULTI-CATFISH-MCRL-V04-C3-CONFIRMATORY-RESULT-2026-09-01.md` — C3
  confirmation in the old-Q2 context.
- `docs/MULTI-CATFISH-MCRL-V04-ROUTE-INTERACTION-DIAGNOSTIC-2026-09-01.md` and
  `evidence/v04-route-interaction-result.json` — old interaction evidence,
  including the Q2-free negative C3 direction.

## Exact current OPS-3

- `docs/MULTI-CATFISH-C2-OPS3-FORMULA-PROBE-CONTRACT-2026-09-02.md` — exact
  formula, native clock, D2, visibility, persistence, interference, gauge,
  feature, seed, arm, and stop rules.
- `docs/MULTI-CATFISH-C2-OPS3-MECHANICS-CHECKPOINT-2026-09-02.md` — 29 targeted
  and 92 nearby physics tests, corrected mechanics defects, hashes, and claim
  boundary.
- `docs/MULTI-CATFISH-C2-CROSS-SESSION-MERGE-CHECKPOINT-2026-09-02.md` — first
  cross-session comparison and explicit ruling that the Fable `+9.480%` is not
  an exact OPS-3 result.
- `source/runtime/ee_axis_ops3.py` — pure exact formula surface.
- `source/runtime/ee_axis_ops3_live.py` — cloned native-clock TLE/D2 adapter and
  frozen-background projection.
- `source/tests/test_w129_ee_axis_ops3.py` and
  `source/tests/test_w130_ee_axis_ops3_live.py` — copied mechanics tests.

The exact current OPS-3 outcome panel remains unopened and unrun.

## Design authority and unrun hypotheses

- `docs/CURRENT-MULTI-CATFISH-AUTHORITY.md` — copied project orientation; no
  shared-authority patch from the challenger was applied.
- `docs/MULTI-CATFISH-EE-AXIS-REDESIGN-CONTRACT-V0.3-2026-08-31.md` — original
  fixed-lambda/common-kappa and direct-sum constraints.
- `docs/MULTI-CATFISH-MCRL-V03-ALGORITHM-SPEC-2026-08-31.md`, the E1 validity
  contract/amendment, and `ADR-007-action-shared-three-q-instrument.md` —
  learner and architecture orientation.
- `docs/MULTI-CATFISH-C2-PARALLEL-DESIGN-ADJUDICATION-2026-09-02.md` — staged
  gate and candidate selection order.
- `docs/MULTI-CATFISH-C2-FABLE-51-CLEANROOM-REVIEW-2026-09-02.md` — separate
  unrun Fable option-value proposal.
- `docs/MULTI-CATFISH-C2-OPS3-FRESH-REVIEW-2026-09-02.md` — design rationale
  preceding the exact contract.
- `docs/MULTI-CATFISH-C2-PROJECTED-SHAPING-CANDIDATE-2026-09-02.md` — older
  predecessor retained only to expose defects corrected by exact OPS-3.

## Retired/negative C2 evidence

- `docs/MULTI-CATFISH-MCRL-V05-C2-CONTROLLED-TAPE-DISPOSITION-2026-09-01.md`
  and `evidence/v05-support-failure-receipt.json` — native-support divergence.
- V0.6 K1 documents plus `evidence/v06-d0-diagnostic.json` and
  `evidence/v06-loowo-diagnostic.json` — policy-cascade/unobservability evidence.
- V0.7 design/result documents plus `evidence/v07-r13-balanced.json` and
  `evidence/v07-r14-loao.json` — near-zero direction and failure versus the
  strongest null.

These files explain why realized-successor-residual C2 designs were retired;
their presence does not make them live candidates.

## Simulator and learner source snapshot

- `source/env/step.py` and `link_budget.py` — action execution, segment
  recurrence, rates, interference, network power, and the reward-only handover
  field.
- `source/env/scenario.py`, `candidates.py`, `ephemeris.py`, `mobility.py`, and
  `pointing.py` — TLE geometry, D2/dwell timing, candidates, masks, and motion.
- `source/runtime/ee_axis_state.py`, `ee_surplus_targets.py`,
  `energy_efficiency.py`, and `outage_gate.py` — common state, target units,
  endpoint, and service guard.
- `source/algorithms/ee_axis_pairwise.py` and related algorithm snapshots —
  shared scale, pairwise learner, and direct deployed Q sum.

The package is sufficient for formula/method adjudication, not a
self-contained simulator or training reproduction.
