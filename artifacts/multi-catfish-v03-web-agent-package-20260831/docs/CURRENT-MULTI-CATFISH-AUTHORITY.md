# Current Multi-Catfish MCRL authority

Date: 2026-08-31

## Binding authority

Use only the following for the current formula-first candidate:

- `docs/MULTI-CATFISH-EE-AXIS-REDESIGN-CONTRACT-V0.3-2026-08-31.md`
- `docs/MULTI-CATFISH-EE-AXIS-OPUS-MAX-CODESIGN-V0.3-2026-08-31.md`
- `docs/MULTI-CATFISH-MCRL-V03-ALGORITHM-SPEC-2026-08-31.md`
- `docs/MULTI-CATFISH-MCRL-V03-PAPER-AUTHORING-CONTRACT-2026-08-31.md`
- `docs/MULTI-CATFISH-MCRL-V03-FIGURE-DECK-HANDOFF-2026-08-31.md`
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

Paper Chapter 4, all non-result scientific figures, and the English algorithm
deck are **GO** using the current paper-authoring contract and figure/deck
handoff. The architecture, formulas, three Catfish roles, three-Q topology,
dataset routing, deployment rule, and ablation arm definitions are fixed for
authoring. Unsealed hyperparameters and every efficacy/result value must remain
visibly `TBD`; no slide may imply that EE improvement has already been proven.
The C2 temporal role and target formula are fixed. Its hold-expiry policy is
hold-while-legal followed by a monotone release to contemporaneous
candidate-branch Main. The isolated V0.3B implementation/test gate is complete
(256/256 targeted tests), but the fresh-seed physical-headroom receipt is not
sealed; keep result annotations editable and marked `TBD` until that receipt exists.

## Training boundary

Training is currently **NO-GO**. The sealed canonical-fading keyed-CRN C2
viability census is complete with outcome `INDETERMINATE`: its positive
replication condition passed in 5/5 seed worlds, but 14/41 fixed-hold branches
were right-censored by `focal_hold_expired`, leaving completion and censoring
each one trace outside the frozen gate. This is not a C2 efficacy result and
must not be relabelled `GO` by relaxing the old threshold. The
hold-while-legal V0.3B source rule is implemented and targeted-test green,
but it must be preregistered and sealed on a non-overlapping seed block before
a new C2 decision dataset is accepted for learning.

The three-online-Q pairwise learner, branch-independent keyed fading field,
StepEnvironment seam, reactive-release C2 fork, versioned
state/replay/runtime compatibility checks, gate adjudicator, and integrity
receipts are implemented and covered by targeted tests. A fresh reactive C2
physical-headroom gate and then a bounded learnability pilot remain required
before any short-EP ablation. No 9000-episode run is authorized. Any eventual run
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
