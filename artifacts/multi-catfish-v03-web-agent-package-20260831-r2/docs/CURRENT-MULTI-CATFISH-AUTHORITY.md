# Current Multi-Catfish MCRL authority

Date: 2026-08-31

## Binding authority

Use only the following for the current formula-first candidate:

- `docs/MULTI-CATFISH-EE-AXIS-REDESIGN-CONTRACT-V0.3-2026-08-31.md`
- `docs/MULTI-CATFISH-EE-AXIS-OPUS-MAX-CODESIGN-V0.3-2026-08-31.md`
- `docs/MULTI-CATFISH-MCRL-V03-ALGORITHM-SPEC-2026-08-31.md`
- `docs/MULTI-CATFISH-MCRL-V03-PAPER-AUTHORING-CONTRACT-2026-08-31.md`
- `docs/MULTI-CATFISH-MCRL-V03-FIGURE-DECK-HANDOFF-2026-08-31.md`
- `docs/MULTI-CATFISH-MCRL-V03-PRESENTATION-LAYER-2026-08-31.md`
- `docs/MULTI-CATFISH-MCRL-V03-10EP-ABLATION-AUDIT-2026-08-31.md`
- `docs/MULTI-CATFISH-MCRL-V03-OPUS-MAX-SOURCE-CONTROL-REVIEW-2026-08-31.md`
- `docs/MULTI-CATFISH-MCRL-V03-C2-GATE-CROSS-MODEL-REVIEW-2026-08-31.md`
- `docs/MULTI-CATFISH-MCRL-V03-C2-GATE-RESULT-2026-08-31.md`
- `docs/MULTI-CATFISH-MCRL-V03-C2-POSTGATE-DESIGN-DECISION-2026-08-31.md`
- `docs/MULTI-CATFISH-MCRL-V03-C2-REACTIVE-RELEASE-IMPLEMENTATION-2026-08-31.md`
- `docs/MULTI-CATFISH-C3-V03-FORMULA-FIRST-CENSUS-2026-08-31.md`
- `src/mcrl/algorithms/ee_axis_pairwise.py`
- `src/mcrl/env/keyed_fading.py`
- `src/mcrl/runtime/ee_surplus_targets.py`
- `tests/test_w37_ee_axis_pairwise_trainer.py`
- `tests/test_w38_keyed_fading.py`
- `tests/test_w39_c2_keyed_gate.py`
- `tests/test_w40_c2_gate_runner_integrity.py`
- `tests/test_w36_ee_surplus_targets_v03.py`
- `.scratch/ee-axis-redesign/run_c2_v03_deterministic_plumbing_probe.py`
- `.scratch/ee-axis-redesign/run_c2_v03_keyed_multiseed_gate.py`
- `.scratch/ee-axis-redesign/run_c3_focal_nonfocal_oracle_pilot.py`
- `.scratch/ee-axis-redesign/c2-v03-deterministic-plumbing-probe-smoke.json`
- `.scratch/ee-axis-redesign/c3-focal-nonfocal-oracle-pilot-v03-r1.json`
- `.scratch/c2-v03/` reactive-release implementation and targeted tests
- `artifacts/c2-v03-gate-20260831/prereg.json`
- `artifacts/c2-v03-gate-20260831/result.json`
- `artifacts/smc-er-c1-authority-20260828/` as the retained C1 EXP/ACRM
  lineage authority only; it is not an EE efficacy claim.

The canonical endpoint is unchanged ratio-of-sums EE. C1, C2, and C3 are the
V0.3 focal-now, everyone-later, and non-focal-now EE-surplus routes. Legacy
`r2`/`r3` values are not current objectives.

## Authoring boundary

The current main-text/main-deck compression contract is
`docs/MULTI-CATFISH-MCRL-V03-PRESENTATION-LAYER-2026-08-31.md`. It changes
presentation depth only; the EE-axis formula authority and implementation
contracts remain complete and binding.

Paper Chapter 4, all non-result scientific figures, and the English algorithm
deck are **GO** using the current paper-authoring contract and figure/deck
handoff. The architecture, formulas, three Catfish roles, three-Q topology,
dataset routing, and current deployment candidate are fixed for authoring;
the deployment observability gate remains unresolved and must be labelled as
such in evidence slides. Unsealed hyperparameters and every efficacy/result value must remain
visibly `TBD`; no slide may imply that EE improvement has already been proven.
The C2 temporal role and target formula are fixed. Its hold-expiry policy is
hold-while-legal followed by a monotone release to contemporaneous
candidate-branch Main. The sealed V0.3B fresh-seed physical-headroom gate
completed 41/41 traces and authorizes only a bounded learnability pilot; it is
not a Q2 or EE-efficacy result. Keep all efficacy annotations editable and
`TBD`.

## Training boundary

The first 10-episode matched ablation is formally
`VOID_UNINTERPRETABLE_INSTRUMENT`; see
`artifacts/multi-catfish-v03-10ep-matched-ablation-20260831/AUDIT-VOID.json`.
Its C1-negative and C2/C3-positive directional fields are not current
evidence. Before another EE ablation, a preregistered E1 instrument-validity
gate must show that the deployed three-Q score has state-conditional action
resolution and held-out pair generalization. This gate must not use EE as a
decision input.

Training is currently **NO-GO**. The old fixed-hold keyed-CRN census remains
sealed `INDETERMINATE`. Its successor,
`artifacts/c2-v03b-reactive-keyed-physical-headroom-gate-20260831`, is sealed
`GO_BOUNDED_LEARNABILITY_PILOT_ONLY`: 41/41 traces completed, 11 were
service-safe positive, and four of five seeds contained at least one positive
trace. That receipt proves bounded C2 physical opportunity only, not
learnability or EE efficacy.

The current C2 backend differs from the sealed source manifest only by the
later neutral-source provenance plumbing, not by the target formula; however,
the current checkout cannot reproduce the old manifest until it is resealed
and the C2 gate is rerun. Separately, the 10EP audit found that the deployed
three-Q score was dominated by state-independent action bias. Therefore the
next authorized scientific activity is a preregistered E1 instrument-validity
gate with no EE endpoint, followed by a bounded matched learnability pilot
only if E1 passes. No 9000-episode run is authorized. Any eventual run
must checkpoint every 100 episodes, and the user must be notified before
9000 EP.

## Archive boundary

`archive/multi-catfish-pre-v03-2026-08-31/` is historical evidence only. It
must never be used as a launch authority, checkpoint source, reward source,
or current method description. Its receipts retain old paths by design.

Do not restore or execute archived launchers merely because their filenames
contain `V0.3`, `R6`, or `R7`; first revalidate them against the current V0.3
contract and issue a new current receipt.

## Deliberately retained shared inputs

- `src/mcrl/**` shared simulator and MODQN runtime
- `tests/**` shared regression suite
- `artifacts/smc-er-c1-authority-20260828/`
- `artifacts/training-2026-08-24/`
- `artifacts/training-2026-08-25-rerun01/`
- `artifacts/PREREG-FROZEN-*.json`
- `chapter4-0826.pptx` and `chapter5-0826.pptx`

These were not archived because current C1 provenance, canonical baseline
comparison, or shared runtime behavior may depend on them.
