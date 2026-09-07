# V0.23 C3 contingency F1 implementation

This directory implements only the pre-outcome ladder's two-step F1 kill
screen. It does not authorize or perform a local simulator run, learner
update, TEST evaluation, or efficacy claim. The later heavy execution belongs
on the Ubuntu server under a separately frozen launch-authority JSON.

## Frozen bindings

- TRAIN world: `2026121721` only.
- Q1+Q2 lineage: `2026092101`, combined rung-003000 checkpoint
  `d40a0f3095f9bb9010d0146a88a77b3c8a824fb9bd3e5aee2205f3ae8be592dc`.
- Q1+Q2 authority body/file:
  `50d32dae11b2906bb23a25893f4ba5c11d0f88197ee94fe7cd216677e8703d48` /
  `a05ee801c8f9d640b55f8ec984d874f149c30b868d1706d998f7e2053520078e`.
- Canonical decision steps: exactly `0, 1`; the BASE Q1+Q2 action is committed
  between them, matching the source-stage background trajectory.
- One common keyed field:
  `KeyedFadingField.from_components("MCRL_V023_LCSRS_C3_OBSERVABILITY_V1", 2026121721)`.
- Claim ceiling:
  `TRAIN_DEVELOPMENT_C3_CONTINGENCY_F1_KILL_SCREEN_NO_EFFICACY_NO_TEST`.

The ladder names one common keyed field but does not spell out its component
string. The single open interpretation question is therefore the namespace.
This implementation uses the plainest reading of the brief's R7-source-stage
reference: carry forward R7's
`MCRL_V023_LCSRS_C3_OBSERVABILITY_V1` component and substitute only the
ladder-frozen F1 world. This choice is a fixed binding, not a CLI option.

The ladder also does not introduce a separate composition operator for `z`.
The only implemented rule is named by `F1_DEPLOYMENT_RULE`:
masked `argmax(Q1 + Q2 + z)` over the native legal mask, with NumPy's existing
first-index tie handling and no scaling, clipping, compatibility gate, sign
filter, or tuning knob. Here `z` is the literal raw-bit value returned by F0.
The frozen Q1/Q2 heads carry their existing normalized score convention, so
the dimensional interpretation of this literal unscaled sum remains an
authority-level open question; the implementation follows the task's explicit
"no scaling" instruction and does not introduce a conversion parameter.

## Tape and screen

For each of the two predecision anchors, the runner records the exact float32
Q1+Q2 surface, native action masks, physical identity of every action slot,
the BASE joint action/profile, and every legal non-NOOP unilateral physical
change in deterministic `(focal_user, action)` order. Each physical profile
contains link rates, per-user link power, realised service and serving
satellite/cell, active beams and their radiated link power, fixed/system
power, and interval. D and F are recomputed only through the existing F0
`compute_c3_targets` function.

The selected D/F joint actions are evaluated once at the same anchor and
field and included in the shared tape. The tape and manifest are created with
exclusive writes, changed to mode `0444`, reopened, hash-checked, and only
then screened. BASE, D, and F all pool interval bits and energy across the
same two tape steps; EE is one ratio of sums. A candidate survives only when
integrity, legal mutation, service `>= BASE - 0.001`, and EE `> BASE` all
pass. D is adjudicated before F.

## Preflight and later launch

Build the preflight once after code review:

```bash
./.venv/bin/python .scratch/multi-catfish-v023-c3-contingency-f1/build_f1_preflight_manifest.py
```

Then run the simulator-inert check:

```bash
./.venv/bin/python .scratch/multi-catfish-v023-c3-contingency-f1/run_v023_c3_contingency_f1.py --dry-run
```

The server controller must create a launch authority with schema
`multi-catfish-mcrl-v023-c3-contingency-f1-v1-launch-authority`, status
`FROZEN_LAUNCH_AUTHORITY`, the exact bindings and claim ceiling emitted by
the preflight, and the preflight path/digest. Only then may it invoke:

```bash
./.venv/bin/python .scratch/multi-catfish-v023-c3-contingency-f1/run_v023_c3_contingency_f1.py \
  --preflight-manifest .scratch/multi-catfish-v023-c3-contingency-f1/F1-PREFLIGHT-MANIFEST.json \
  --launch-authority /path/to/frozen-launch-authority.json \
  --tle-root /home/sat/mcrl-runtime/tle-frozen-20260820 \
  --output /fresh/server/output
```

The expected heavy wall time depends on the number of legal unilateral
profiles in the two 100-user anchors and must be measured on the server; no
such run was made during implementation.

## Unit tests

```bash
./.venv/bin/python -m pytest -q .scratch/multi-catfish-v023-c3-contingency-f1
```
