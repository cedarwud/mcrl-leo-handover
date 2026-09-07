# Multi-Catfish C2 cross-session merge checkpoint

Date: 2026-09-02  
Status: `CHALLENGER_EVIDENCE_MERGED__CURRENT_OPS3_OUTCOME_UNOPENED__PAUSED`  
Claim ceiling: development-direction evidence only; no learned C2 efficacy and
no Chapter 5 result

## Merge inputs

1. Current OPS-3 mechanics lane:
   `docs/MULTI-CATFISH-C2-OPS3-MECHANICS-CHECKPOINT-2026-09-02.md`.
2. Independent Fable 5.1 challenger package:
   `artifacts/fable-51-c2-cleanroom-20260902-r1/`.
3. Fable decision document:
   `docs/FABLE-51-C2-CLEANROOM-V08-DESIGN-DECISION-2026-09-02.md`.

`sha256sum -c artifacts/fable-51-c2-cleanroom-20260902-r1/MANIFEST.sha256`
passed for every listed file. The package receipt says no episode training, no
learned Q2, and no TEST split was opened. Its strict source-closure re-check did
not pass; the package therefore correctly limits itself to development evidence.
The package is internally checksum-complete but not independently
self-contained: its decision document lives in `docs/`, and its runner receipts
refer to external checkpoints, repository sources, and a temporary runner path.

## Evidence accepted from the challenger lane

The challenger independently found the same useful physical family: the chosen
action changes the segment reference gain, future recurrence-power trajectory,
network-power contribution, future rate, and infeasibility cliff. Its bounded
oracle screen reports:

| route used by challenger | C2 marginal over Q1+Q3 | lineages | worlds |
|---|---:|---:|---:|
| H-A controller formula | +11.700% | 3/3 positive | 6/6 positive |
| challenger's OPS-3 interpretation | +9.480% | 3/3 positive | 6/6 positive |

This is accepted as evidence that a deterministic segment-timing/projected-
persistence C2 is physically plausible and merits an exact implementation
screen. It is not evidence that a learned Q2 reproduces that ordering.

The same matched block also found a method interaction that must not be hidden:

| route used by challenger | C3 marginal in Q1+Q2 context | C1 marginal in Q2+Q3 context |
|---|---:|---:|
| H-A controller formula | -0.485% (0/3 positive) | +0.644% (3/3 positive) |
| challenger's OPS-3 interpretation | -2.687% (0/3 positive) | +5.892% (3/3 positive) |

Thus this block supports the local C2 direction but does not satisfy the final
three-positive-marginal method goal. The challenger's overall service guard
also failed. For the C2 comparison alone, its OPS-3 interpretation was
non-inferior in pooled served fraction and 3/3 lineages; H-A was lower by one
served user-step out of 18,000 and had 2/3 nonnegative lineages.

## Why the challenger OPS-3 number is not the current OPS-3 result

The Fable decision document explicitly says that its evaluated OPS-3 arms are
the controller's reading of the proposal and are **not** the OPS-3 lane's own
result. Inspection of its sealed runner confirms material protocol differences:

| dimension | current exact OPS-3 | challenger interpretation |
|---|---|---|
| D2 | cloned live tracker, 47 native 640-ms updates per future decision, projected eligibility included | no cloned native-clock D2 eligibility projection |
| visibility | future satellite-to-physical-cell-centre visibility | focal-user elevation above horizon |
| persistence | absorbing product from the first projected service loss | per-offset instantaneous feasibility; later recovery can contribute |
| interference | reconstructed frozen served background propagated with TLE geometry through canonical interference helpers | decision-time interference-plus-noise recovered from the observation and frozen |
| clock | exact canonical `47 * 0.64`, hex `0x1.e147ae147ae15p+4` | decimal 30.08 convention |
| gauge | exact Main-reference subtraction, bit-exact zero row | subtraction omitted from deployed oracle as argmax-invariant |
| worlds | unopened contract panel beginning at `2026104501` | `2026090221` through `2026090226` |

The gauge omission does not change an argmax, but the D2, visibility,
persistence, interference, and world-panel differences prevent numerical
substitution. In particular, `+9.480%` must never be labelled as a result of
`src/mcrl/runtime/ee_axis_ops3_live.py`.

## Merge ruling

1. Retain OPS-3 as the current provisional C2 candidate; the challenger result
   materially raises confidence that the underlying C2 direction is viable.
2. Do not promote OPS-3 to validated, do not create a learner, and do not start
   500/1500/3000/9000-episode training from the challenger result.
3. Record frozen C3 as context-dependent rather than silently carrying its old
   positive-old-Q2 claim into the new C2 context. This observation does not
   authorize changing C3 in the C2 mechanics stage.
4. Do not choose H-A over exact OPS-3 post hoc from these numbers; they were not
   implementations of one identical formula contract.

## Next gate when work resumes

Before an outcome run, resolve the one formula-level merge question already
recorded in the mechanics checkpoint: whether future persistence is conditional
on successful opening service at `h=0`. Then freeze the decision without
looking at the unopened OPS-3 worlds.

The next executable evidence gate is the current contract's exact-adapter
12-episode TRAIN-design smoke (one predeclared world, three frozen lineages,
four matched arms). It must use `ee_axis_ops3_live.py` directly and report at
least the C2 marginal, its per-lineage signs, raw ratio-of-sums bits/energy,
served-fraction comparison, action-flip exposure, and source receipts. It is
not a learner or an episode-training run. If a timing smoke projects more than
30 minutes of wall time, route this compute to the Ubuntu server.

Per controller instruction, no part of that next gate is launched from this
checkpoint. Work pauses here after the cross-session evidence merge.
