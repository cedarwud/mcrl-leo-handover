**MODQN is not physically collapsed: over 100 native V0.23 TRAIN profiles it has `modal_frac=0.04170`, `active=68.70` physical beams / `7.47` satellites, and `argmax_distinct=0.07470`, versus the zero-learning myopic control's `0.05010`, `63.32 / 6.47`, and `0.13920`; its physical distribution is far from the sibling's one-beam collapse and spread-like, while its local-slot diversity sits between the sibling's collapsed and spread examples.**

# MODQN concentration diagnosis — 2026-09-10

## Answer

**MODQN did not collapse to one physical beam in this rollout.** Its mean largest-beam occupancy was 4.17 users out of 100, its worst observed largest-beam occupancy was 7, and every profile selected 56–82 distinct physical beams. No profile had a no-op selection.

The qualification is important: the shared policy does concentrate on a small subset of its *local action-slot numbers*. A profile used 2–13 of the 28 slot numbers (`argmax_distinct=0.02–0.13`), and slots 7 and 21 together received 69.18% of all MODQN selections. But a slot number is user-relative: the native `SlotTable` maps it to a user-specific `(NORAD ID, cell ID)` physical beam ([action contract](/home/sat/mcrl-leo-handover-20260825-corrected/src/mcrl/env/action_contract.py:264)). Consequently that slot preference produced broad physical allocations rather than the sibling project's all-users-on-one-beam pathology.

This is therefore a plain negative answer to the motivating hypothesis: **this authenticated MODQN policy is not in the sibling project's physical shared-Q + argmax collapsed regime.** On local-slot diversity alone it is intermediate, not fully spread.

## Measurement design

- Environment: the native legacy/V0.23 training stack from `/home/sat/mcrl-leo-handover-20260825-corrected`, not the blocked V0.25 bridge.
- Split: native `TRAIN` only. The original factory constructs `ScenarioDriver`, `StepEnvironment`, and `EpisodeStartSampler(..., TRAIN)` ([training factory](/home/sat/mcrl-leo-handover-20260825-corrected/src/mcrl/runtime/training_pipeline.py:736)). No V0.25 evaluation-only claim-date inventory was opened.
- Scenarios: 10 frozen train-split P6 development scenarios. Seeds: `2026082401`, `2026082402`, `2026082403`, `2026082404`, `2026082405`, `2026082406`, `2026082407`, `2026082408`, `2026082409`, `2026082410`; the producer calls these the ten matched train-split evaluation seeds ([seed declaration](/home/sat/mcrl-leo-handover-20260825-corrected/src/mcrl/runtime/probe_p6.py:27)).
- Steps: 10 per scenario; 100 users; hence 100 physical profiles and 10,000 selections per policy.
- MODQN: authenticated 112-state, 28-action, three-Q-network checkpoint; weights `(0.5, 0.3, 0.2)`; lowest-index masked argmax. The adapter implements exactly that selector ([adapter](/home/sat/mcrl-v025-retrain-ws/.scratch/multi-catfish-v023-baseline-adapter/baseline_adapter.py:700)).
- Zero-learning myopic control: independently for each user, select the lowest-index legal argmax of the native **linear `channel_quality`**, which is the environment's current candidate SINR block; emit native `NO_OP` only for an empty mask. It has no fitted parameters, look-ahead, load coordination, or learning.
- Matching: each policy got a fresh environment for each same seed; the seed was split into the environment and mobility generators exactly as the legacy evaluation method does ([legacy evaluation](/home/sat/mcrl-leo-handover-20260825-corrected/src/mcrl/algorithms/modqn.py:622)). Each policy then induced its own valid state trajectory.

Definitions:

- `modal_frac`: largest selected non-null physical `(NORAD ID, cell ID)` occupancy divided by 100.
- `active`: distinct selected non-null physical beams, and distinct NORAD IDs.
- `argmax_distinct`: distinct selected non-null local action-slot numbers divided by 100. A local slot is not itself a global beam identity.
- “Pooled” below is the arithmetic mean over the 100 scenario-step profiles. Ranges are profile minima and maxima.
- Histogram notation `k→n` means `n` occupied physical beam/profile instances had exactly `k` selected users. It includes every observed tail value.

The concentration runner is [scripts/measure_modqn_collapse.py](./scripts/measure_modqn_collapse.py). It maps selections through each native slot table before counting physical identities ([metric code](./scripts/measure_modqn_collapse.py:131)) and never invokes the V0.25 projection.

## Verified by running code

### Pooled results

| Policy | Profiles | `modal_frac` mean [range] | Active physical beams mean [range] | Active satellites mean [range] | `argmax_distinct` mean [range] | No-op users mean [range] |
|---|---:|---:|---:|---:|---:|---:|
| Authenticated MODQN | 100 | **0.04170** [0.03, 0.07] | **68.70** [56, 82] | **7.47** [4, 12] | **0.07470** [0.02, 0.13] | 0 [0, 0] |
| Zero-learning myopic | 100 | **0.05010** [0.03, 0.12] | **63.32** [38, 79] | **6.47** [4, 12] | **0.13920** [0.03, 0.27] | 0 [0, 0] |

The comparison is not one-dimensional. MODQN is less concentrated by physical `modal_frac` (`−0.00840`) and uses 5.38 more physical beams and 1.00 more satellite on average, but the myopic rule uses 6.45 more distinct local slot numbers per profile (`argmax_distinct +0.06450`). The differing signs are exactly why physical identity and slot identity must not be conflated.

### Per-step results

Each row is the mean over the 10 scenarios; brackets give the full scenario range for that step.

| Step | Policy | `modal_frac` | Active beams | Active satellites | `argmax_distinct` |
|---:|---|---:|---:|---:|---:|
| 0 | MODQN | 0.039 [0.03, 0.05] | 66.1 [59, 73] | 7.0 [4, 12] | 0.033 [0.02, 0.04] |
| 0 | Myopic | 0.036 [0.03, 0.05] | 73.9 [70, 79] | 6.6 [5, 10] | 0.058 [0.04, 0.08] |
| 1 | MODQN | 0.042 [0.03, 0.05] | 67.2 [59, 74] | 7.0 [4, 12] | 0.042 [0.03, 0.05] |
| 1 | Myopic | 0.040 [0.03, 0.05] | 69.6 [66, 73] | 7.0 [5, 12] | 0.154 [0.10, 0.22] |
| 2 | MODQN | 0.038 [0.03, 0.05] | 69.0 [62, 74] | 7.0 [4, 12] | 0.048 [0.03, 0.07] |
| 2 | Myopic | 0.050 [0.03, 0.07] | 62.9 [53, 71] | 7.0 [5, 12] | 0.183 [0.13, 0.26] |
| 3 | MODQN | 0.037 [0.03, 0.06] | 69.5 [64, 75] | 7.2 [4, 12] | 0.055 [0.04, 0.07] |
| 3 | Myopic | 0.061 [0.04, 0.09] | 55.0 [49, 62] | 7.1 [5, 12] | 0.216 [0.15, 0.27] |
| 4 | MODQN | 0.048 [0.04, 0.07] | 65.8 [56, 76] | 8.7 [6, 11] | 0.096 [0.06, 0.12] |
| 4 | Myopic | 0.041 [0.03, 0.05] | 70.4 [67, 74] | 5.3 [4, 7] | 0.062 [0.03, 0.10] |
| 5 | MODQN | 0.043 [0.03, 0.06] | 70.0 [58, 77] | 8.6 [7, 11] | 0.106 [0.08, 0.13] |
| 5 | Myopic | 0.046 [0.04, 0.06] | 64.9 [57, 73] | 6.4 [4, 8] | 0.146 [0.09, 0.22] |
| 6 | MODQN | 0.041 [0.03, 0.06] | 71.5 [62, 77] | 6.6 [5, 8] | 0.090 [0.07, 0.12] |
| 6 | Myopic | 0.058 [0.04, 0.08] | 56.8 [45, 63] | 6.0 [4, 8] | 0.179 [0.14, 0.22] |
| 7 | MODQN | 0.042 [0.03, 0.06] | 71.3 [62, 76] | 5.8 [5, 7] | 0.084 [0.07, 0.10] |
| 7 | Myopic | 0.081 [0.05, 0.12] | 43.6 [38, 54] | 5.5 [4, 7] | 0.190 [0.17, 0.21] |
| 8 | MODQN | 0.047 [0.04, 0.06] | 65.9 [57, 78] | 8.6 [5, 12] | 0.092 [0.08, 0.12] |
| 8 | Myopic | 0.042 [0.03, 0.07] | 71.1 [64, 78] | 6.8 [5, 9] | 0.052 [0.03, 0.08] |
| 9 | MODQN | 0.040 [0.03, 0.06] | 70.7 [63, 82] | 8.2 [5, 12] | 0.101 [0.06, 0.13] |
| 9 | Myopic | 0.046 [0.03, 0.06] | 65.0 [59, 68] | 7.0 [4, 9] | 0.152 [0.10, 0.22] |

There is no within-episode march toward physical collapse: MODQN starts at 66.1 active beams / `modal_frac=0.039` and ends at 70.7 / `0.040`. Its slot diversity does rise from 3.3 to 10.1 distinct slot numbers on average, but it never approaches use of all 28 in a profile.

### Full physical-beam occupancy histograms

| Step | MODQN complete histogram | Myopic complete histogram |
|---:|---|---|
| 0 | `1→413, 2→177, 3→53, 4→16, 5→2` | `1→531, 2→163, 3→38, 4→6, 5→1` |
| 1 | `1→434, 2→172, 3→48, 4→12, 5→6` | `1→480, 2→145, 3→56, 4→13, 5→2` |
| 2 | `1→452, 2→181, 3→44, 4→11, 5→2` | `1→396, 2→141, 3→60, 4→24, 5→3, 6→4, 7→1` |
| 3 | `1→456, 2→186, 3→42, 4→10, 6→1` | `1→305, 2→135, 3→60, 4→24, 5→17, 6→3, 7→4, 9→2` |
| 4 | `1→428, 2→155, 3→49, 4→17, 5→8, 7→1` | `1→477, 2→173, 3→42, 4→9, 5→3` |
| 5 | `1→470, 2→177, 3→41, 4→8, 5→3, 6→1` | `1→403, 2→175, 3→43, 4→23, 5→4, 6→1` |
| 6 | `1→487, 2→186, 3→30, 4→10, 5→1, 6→1` | `1→313, 2→158, 3→54, 4→20, 5→15, 6→4, 7→2, 8→2` |
| 7 | `1→482, 2→190, 3→31, 4→7, 5→1, 6→2` | `1→187, 2→110, 3→63, 4→31, 5→18, 6→16, 7→4, 8→3, 9→1, 10→1, 11→1, 12→1` |
| 8 | `1→430, 2→155, 3→46, 4→19, 5→8, 6→1` | `1→490, 2→174, 3→31, 4→13, 5→2, 7→1` |
| 9 | `1→479, 2→178, 3→38, 4→10, 5→1, 6→1` | `1→414, 2→157, 3→54, 4→16, 5→8, 6→1` |
| **Pooled** | **`1→4531, 2→1757, 3→422, 4→120, 5→32, 6→7, 7→1`** | **`1→3996, 2→1531, 3→501, 4→179, 5→73, 6→29, 7→12, 8→5, 9→3, 10→1, 11→1, 12→1`** |

The weighted pooled histogram totals exactly 10,000 user selections for each policy. MODQN's entire physical tail ends at occupancy 7; the myopic tail ends at 12.

### Complete aggregate local-slot distribution

Notation is `slot→selections` over the 10,000 decisions. Zero-count slots are retained.

- MODQN: `0→359, 1→0, 2→36, 3→2, 4→2, 5→3, 6→0, 7→4342, 8→25, 9→132, 10→9, 11→605, 12→0, 13→0, 14→898, 15→280, 16→0, 17→40, 18→294, 19→14, 20→0, 21→2576, 22→79, 23→0, 24→246, 25→1, 26→51, 27→6`.
- Myopic: `0→1044, 1→46, 2→32, 3→30, 4→35, 5→38, 6→36, 7→2520, 8→108, 9→113, 10→80, 11→110, 12→111, 13→81, 14→2091, 15→137, 16→80, 17→82, 18→128, 19→90, 20→99, 21→2192, 22→136, 23→96, 24→79, 25→174, 26→104, 27→128`.

MODQN uses 21 slot numbers somewhere in the panel, but most choices occupy a few indices. The myopic rule uses all 28. This is genuine slot-index concentration, not physical-beam collapse.

## The requested V0.25 juxtaposition — not a ranking

| Environment and policy | `modal_frac` | Active beams / satellites | `argmax_distinct` |
|---|---:|---:|---:|
| **V0.23 native MODQN** (this run) | **0.04170** | **68.70 / 7.47** | **0.07470** |
| **V0.23 native myopic** (this run) | **0.05010** | **63.32 / 6.47** | **0.13920** |
| V0.25 learned `a0` | 0.05236 | 49.07 / 5.79 | 0.49070 |
| V0.25 myopic | 0.05500 | 51.68 / 5.18 | 0.51682 |

The V0.25 values are taken from [BASE-COLLAPSE-DIAGNOSIS-2026-09-10.md](/home/sat/mcrl-v025-probe-ws/BASE-COLLAPSE-DIAGNOSIS-2026-09-10.md:1).

**These are different environments:** V0.23 legacy for MODQN and V0.25 for `a0`. The action catalogues and physical candidate sets are also not interchangeable. Concentration statistics are policy properties that are **comparable in kind but not in physics**; the table is a juxtaposition, not one cross-environment ranking.

## Position relative to the sibling regimes

No new collapsed/not-collapsed threshold is introduced here. The comparison uses the sibling project's observed regimes:

- Its collapsed distance-only learned regime put all 100 users on one beam at every checkpoint: active beams `1.00`, `modal_frac=1.000` ([sibling verdict](/home/sat/route-c-wt/docs/research/paper-baseline-modqn-phaseb-verdict.md:29)). With 100 users, its one distinct choice corresponds on paper to `argmax_distinct=0.01`.
- Its antenna-enabled spread example reported active beams `13.36` and `modal_frac=0.192` ([sibling table](/home/sat/route-c-wt/docs/research/paper-baseline-modqn-phaseb-verdict.md:49)). If each reported beam is treated as one distinct selected action, `13.36/100=0.1336` is a derived beam-distinct fraction, not a separately reported sibling metric. The supplied cross-project spread proxy was also 5–7 active satellites.

MODQN's **physical** result—68.70 beams, `modal_frac=0.04170`, maximum occupancy 7—is far from the sibling's one-beam/`1.000` collapse and lies on the spread side of those observed physical descriptors. Its 7.47-satellite mean is just above the supplied 5–7 spread band (profile range 4–12). Its **local-slot** fraction `0.07470` lies between the sibling collapse's derived `0.01` and spread example's derived `0.1336`. So the honest placement is: **physically spread, locally slot-concentrated and intermediate—not collapsed.** Cross-project magnitudes are not physics rankings.

The zero-learning control does not simply dominate MODQN on every concentration statistic. It is more diverse in local slot indices, but it has a larger physical modal fraction and fewer active physical beams and satellites. That contrasts with the sibling's striking “trivial rule beats the learned baseline” case rather than reproducing it wholesale here.

## Was this the training environment?

**Yes—no distribution shift was detected for the environment implementation, TLE corpus, or numerical dependencies used here.** This conclusion is stronger than merely loading the checkpoint:

- The checkpoint status binds training source digest `544fcf078f7e0d74c38e79288081c60357bc64b59540120dbe4e30bffe014ec4`, TLE file-set digest `427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9`, and exact dependency versions ([checkpoint status](/home/sat/mcrl-leo-handover-20260825-corrected/artifacts/training-2026-08-25-rerun01/main/status.json:38)).
- Recomputing the producer's full source-closure algorithm over the archived training tree returned the same `544fcf…14ec4`. The algorithm covers every `src/mcrl/**/*.py`, the training launcher, and `pyproject.toml` ([hash closure](/home/sat/mcrl-leo-handover-20260825-corrected/src/mcrl/runtime/training_pipeline.py:385)).
- The frozen 373-file TLE set recomputed to the recorded `427e6a…38fe9`; the mandated interpreter reports the same Python 3.13.3, NumPy 2.5.2, SGP4 2.27, Torch 2.13.0, and PyYAML 6.0.3 versions as training.
- The runner explicitly puts the authenticated archived source tree first, reconstructs the original TRAIN factory, and asserts the live source and dependency fingerprints before loading the policy ([runner provenance checks](./scripts/measure_modqn_collapse.py:249)).

The later `/home/sat/mcrl-v025-retrain-ws` environment is changed: its aggregate source digest differs and the successor runner injects a keyed fading field and a new world-seed schedule. I did **not** use that runner. The adapter authenticates the policy but does not itself authenticate environment provenance, which is why the byte-matched archive was necessary. Full provenance evidence is in [.scratch/modqn-collapse/environment-provenance.md](./.scratch/modqn-collapse/environment-provenance.md).

## Resource and sealed-artifact receipt

Verified by the successful run:

```text
interpreter: /home/sat/mcrl-leo-handover/.venv/bin/python
concurrent Python processes launched: 1 (cap: 2)
nice: 16
OMP/OPENBLAS/MKL/NUMEXPR/VECLIB/BLIS threads: all 1
profiles: 100 MODQN + 100 myopic
elapsed wall time: 43.86 s
peak RSS: 805,003,264 bytes (767.71 MiB; /usr/bin/time maximum 786,136 KiB)
checkpoint SHA-256 before: e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b
checkpoint SHA-256 after:  e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b
adapter SHA-256: 67e4c4286ed7133c7d4d5ec53111f5ca5ba6aaf0b7c1c81fca07d26a6f580037
exit status: 0
```

The checkpoint, adapter, training archive, mandated interpreter, and `/home/sat/mcrl-leo-handover` were read-only. The before/after checkpoint digests are identical. Progress and peak RSS were printed after every scenario.

## Evidence classification

### Verified by running code

- All MODQN and myopic per-step and pooled statistics, histograms, slot totals, no-op counts, ranges, runtime dependency equality, source-fingerprint equality, checkpoint admission, resource receipt, and before/after checkpoint hashes.
- Native selections were mapped through the contemporaneous physical `SlotTable`; no V0.25 observation projection or action bridge was used.

### Derived on paper

- Mean differences between MODQN and myopic.
- The sibling fractions `1/100=0.01` and `13.36/100=0.1336`.
- The pooled histograms' weighted sums equal 10,000 selections per policy.
- The statement that slots 7 and 21 comprise 69.18% of MODQN selections: `(4342+2576)/10000`.

### Inferred

- “Not physically collapsed” follows directly from the observed separation from the sibling's all-users/one-physical-beam regime; it does not rely on a newly invented threshold.
- “Locally slot-concentrated/intermediate” is the bounded interpretation of the low local-slot diversity and the cross-regime placement. It is not an EE, efficacy, or physics-equivalence claim.
- The concentration evidence has normal development-panel limits: 10 frozen TRAIN seeds and 10 steps each, not a claim-panel estimate.

## Explicit exclusions

No EE was extracted, pooled, compared, or reported. The native environment performed only the ordinary transitions required to produce each next authentic state; this analysis never read its EE/reward outputs. No loss value was used as evidence. The EE gate remains blocked on the owner's comparator binding, exactly as [MODQN-BRIDGE-2026-09-10.md](/home/sat/mcrl-v025-bridge-ws/MODQN-BRIDGE-2026-09-10.md:1) records.
