# Offline certified unilateral diagnostic — 2026-09-09

`DIAGNOSTIC_NOT_CLAIM`

## Result first

The offline arm selected a profile different from its anchor at **73 of 90 anchors: 0.811111 (81.11%)**. The remaining 17 anchors were certified local optima at the anchor. The arm is therefore non-degenerate on this panel and is marked `informative: true`; this is a diagnostic property, not a pass or efficacy claim.

Per-anchor search cost was:

| Cost | Mean | Median | Minimum | Maximum |
|---|---:|---:|---:|---:|
| wall time | 65.115 s | 55.497 s | 5.929 s | 253.286 s |
| physical boundary evaluations | 11,244.622 | 11,523 | 2,748 | 23,536 |

Across all anchors, the searches used 5,860.380 aggregate anchor-seconds and 1,012,016 physical boundary evaluations. They committed a mean 78.167 user moves in a mean 4.567 sequential passes. Two anchor workers were used, with one parent process: three processes total.

Every one of the 90 rows terminates with `CERTIFIED_LOCAL_OPTIMUM_COMPLETE_NEIGHBOURHOOD`. Every completion flag is true, and every final certificate states:

> Every legal unilateral alternative was evaluated at the final iterate and none improves the guarded coordinator k=0 objective.

The final neighborhood contains exactly 2,700 legal alternatives at every anchor. All were evaluated. There were no physically invalid alternatives; 45,819 alternatives were rejected by the unchanged service guard across the 90 final neighborhoods; and zero guarded alternatives improved at any final iterate.

Evidence: [90-anchor receipt](/home/sat/mcrl-v025-offlinesuni-ws/.scratch/multi-catfish-v025-physics-successor/probe/offline-suni-world1-90.json), file SHA-256 `7c20620826dde48f70102383cd56eeec3407de3bc0d506c24d20db39f85ee1fe`.

The bound input is `V025_PROBE_R2/world/1`, tape SHA-256 `a7d222eab02789c26de423f7cd87d7e2f677c574f64fb181bd98ec799fdec704`, with frozen a-r0 calibration SHA-256 `20a8574e76e8f803c1e8f7158404a3826f72dc462dbe3d45082b67f85d16f04f`.

## Fixed-point agreement after changing the iteration order

The implemented path is deterministic sequential round-robin: ascending user ID; exact best response for that user against the latest profile; stable configuration-ID tie-break among strict improvements; repeat until a complete zero-move pass. It uses the operational arm’s full legal options, exact k=0 evaluator and objective, incumbent-relative Phi term, frozen calibration, and served-user guard. It has no wall-clock deadline.

The completed real-anchor comparison is **3/3 agreement** with a deadline-free transcription of the current global-argmax path:

| Anchor | Step / carrier | Sequential moves | Global moves | Same fixed point |
|---:|---|---:|---:|---|
| 3 | 1 / nearest-eligible | 0 | 0 | yes |
| 4 | 1 / stay-if-possible | 0 | 0 | yes |
| 15 | 5 / nearest-eligible | 0 | 0 | yes |

These are all zero-move anchors, so this real-data agreement check is valid but weak. A separate controlled, non-anchor test makes both algorithms commit two moves and proves that they reach the same non-anchor fixed point.

A real moving-anchor comparison was attempted on anchor 0; the global path had not completed after about 15 minutes and the evidence run was stopped to respect the two-hour task budget. It produced no comparison receipt. Therefore agreement for a moving real anchor is **not established**, and no broader claim that the orders always agree is made.

Evidence: [real agreement sample](/home/sat/mcrl-v025-offlinesuni-ws/.scratch/multi-catfish-v025-physics-successor/probe/offline-suni-world1-agreement-sample.json) and [non-anchor agreement test](/home/sat/mcrl-v025-offlinesuni-ws/tests/physics_v025/test_offline_suni_diagnostic.py).

The fixed point is an arbitrary result of this greedy path, **not a ceiling on unilateral reasoning**. `FULL > S_UNI_OFFLINE` licenses only “not reproducible by this greedy path.”

## T2 strengthening and failure demonstration

T2 now requires all three conditions:

1. The additive placebo interaction is within the already supplied near-zero tolerance.
2. The unilateral arm selects a profile different from the anchor.
3. The deployed selector selects that same non-anchor profile.

The tolerance remains an input to the assertion; no threshold was changed. The current degenerate case `interaction = 0`, deployed = `BASE`, unilateral = `BASE` now fails with:

```text
T2 is vacuous: the unilateral arm must select a non-anchor profile
```

The executable demonstration is `test_t2_strengthening_rejects_current_degenerate_anchor_anchor_behavior`. The companion positive test uses a non-anchor `ALT/ALT` match, and another negative test rejects a deployed/unilateral mismatch.

## Implementation and verification

The standalone implementation is [run_v025_offline_suni.py](/home/sat/mcrl-v025-offlinesuni-ws/.scratch/multi-catfish-v025-physics-successor/probe/run_v025_offline_suni.py).

It imports the sealed evaluator/objective but does not call or modify the budgeted `_s_uni_select`. The operational runner’s current Git blob is `f5035355386ad19e22182aab0b49e55320b14176`, exactly equal to its `HEAD` blob; its deadline, guard, fallback, and abort/discard behavior are unchanged.

Verification used the required interpreter, `PYTHONPATH=src`, and `nice -n 12`:

```text
pytest tests/physics_v025/test_offline_suni_diagnostic.py
5 passed

pytest tests/physics_v025/test_contract_discriminators.py \
  tests/physics_v025/test_stage4_contract.py \
  tests/physics_v025/test_stage4b_contract.py \
  tests/physics_v025/test_stage4d_gate.py \
  tests/physics_v025/test_stage4e_gate.py \
  tests/physics_v025/test_stage4h_amendments.py \
  tests/physics_v025/test_offline_suni_diagnostic.py
58 passed
```

All 90 receipt rows were independently checked for the required termination reason, completed-neighborhood flag, and zero final improvements; the non-degeneracy numerator was independently recomputed as 73.

Full report: [OFFLINE-SUNI-2026-09-09.md](/home/sat/mcrl-v025-offlinesuni-ws/OFFLINE-SUNI-2026-09-09.md)
