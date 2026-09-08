# C3-S diagnostic arms implementation report — 2026-09-08

## Status

Implementation is complete on `c3s/diagnostic-arms`. No physical unit or panel was executed. The only v1-result access was the permitted offline read of the 12 immutable unit receipts and terminal receipt.

The diagnostic runner keeps the original four TRAIN worlds, three E1 lineages, 100 users, 30 canonical steps, independent closed-loop trajectories, identical initial-state construction, and the same arm-independent keyed fading root. `BASE` is included automatically in every selected diagnostic panel.

The 12:50 UTC follow-up is also complete. The runner now accepts `BASE`, `FULL`, and `LITE` in the same `--arms` declaration, adds the three churn/renewal arms, persists per-step mechanism instrumentation for every arm, supports the digest-bound `none`/`ablate_anchor` physics pair, and performs optional offline handover-energy repricing at merge. `BASE` may be written explicitly in `--arms`; it is normalized to the one mandatory BASE trajectory rather than duplicated.

## Implemented arms

| Arm | Proposal/catalog | Selection |
|---|---|---|
| `NULL` | Frozen learned BASE proposal; full C3-S catalog | Runs catalog, nominal evaluation, guard, and exact-score selection, then executes BASE. |
| `RANDOM_FEASIBLE` | C3-S LITE catalog | Uniform over nominal-service-feasible rows using `C3S_DIAG/random/{world}/{lineage}/{step}`. |
| `SHUFFLED_SCORE` | C3-S LITE catalog | Permutes the complete score vector with `C3S_DIAG/shuffle/{world}/{lineage}/{step}`, then guarded argmax. |
| `HEUR` | No Q heads | Per-user maximum current-slot nominal unit-fading/zero-shadow SINR; lowest action-index tie. |
| `HEUR_C3S_LITE` | HEUR reference; one best physically distinct unilateral per user ranked by its complete-profile nominal marginal F, plus all evacuations | Original exact F objective and service guard. |
| `NOMINAL_MPC` | Current association projected to legal slots (lowest legal slot only when an incumbent is absent), all unilateral edits, and all evacuations; no learned or heuristic proposal | Original exact F objective and service guard. |
| `LITE_UNILATERAL_ONLY` | Exact LITE BASE + unilateral rows | Original exact F objective and service guard. |
| `LITE_EVACUATION_ONLY` | Exact LITE BASE + evacuation rows | Original exact F objective and service guard. |
| `RANDOM_RENEW` | Frozen BASE proposal plus one uniformly chosen legal non-BASE unilateral edit | No scoring and no service guard. Uses `C3S_DIAG/renew/{world}/{lineage}/{step}`. A physical alias of the incumbent is retained as an explicit renewal when legal. |
| `RANDOM_RENEW_K` | Frozen BASE proposal plus three distinct uniformly chosen users, each with a uniformly chosen legal non-BASE unilateral edit | Same unscored churn null. K = 3 brackets LITE's approximately one moved configuration per decision. |
| `BASE_FORCED_RENEW_4` | Frozen BASE proposal unchanged | Every legal user whose pre-decision association-segment age is at least four is forced onto a new segment at BASE's best current choice. Dwell N = 4 is the declared provenance. |

The runner records measured selector time, catalog size, nominal-evaluation census, selected profile, pooled exact EE/service, and exact EE relative to BASE. Placebo expectations are labels only; no outcome threshold or outcome-driven constant is introduced. `--assert-null-equals-base` compares the per-step action digest, bits, joules, served count, opportunities, and step index, and invalidates a unit at the first mismatch.

The HEUR selectors have no `physical` or `frozen` model handles and receipt rows explicitly record zero Q-head accesses. `HEUR_C3S_LITE` and `NOMINAL_MPC` use the existing detached nominal evaluator, exact service guard, and canonical tuple tie rules.

## Instrumentation and merge analysis

Every unit-receipt step now contains:

- literal association changes from the preceding realised step;
- native classified handovers, explicit same-link renewals, and their union;
- users whose executed physical association differs from BASE's proposal at that arm's state;
- active radiating-beam count;
- mean and full histogram of post-step association-segment ages;
- the sum of realised per-user link transmit powers;
- detached nominal and realised bits, joules, service, and opportunities; and
- the executed configuration type.

`association_changed_users` is literal and includes association/outage state changes after the opening step. `handover_count` is the simulator's native handover classification. `explicit_renewal_count` retains same-link renewals that the native classifier calls `NONE`. `handover_or_renewal_count` is their user-level union and is the count used by the offline energy sensitivity.

At merge, paired arm/BASE ratio-of-sums EE is tabulated by frozen dwell phase index 0/1/2/3—the exact `step mod 4` decomposition used by the 2026-09-08 red-team—and by the arm's `handover_or_renewal_count`. With `--handover-energy-sensitivity`, merge reprices both each arm and BASE at E_HO = {0, 0.5, 1, 2, 5, 10} J per recorded event and reports the analytical nonnegative zero crossing, if one exists. This is report-only and introduces no threshold.

## Diagnostic physics override

`--physics-override none` is the frozen source behavior. `--physics-override ablate_anchor` passes an immutable override object into a diagnostic-only `StepEnvironment` subclass. Before committed and detached nominal physics evaluation, it refreshes continuing segment anchors to the current transmit gain and suppresses the opening warm anchor, making recurrence power p0 = 0.825 W each step. The canonical wanted-signal path already uses the current `field_now.transmit_gain`; the override preserves that current-gain path. Association ages are not reset by the physics ablation.

The override binding in panel, authority, unit, and terminal receipts includes its name, implementation path, implementation SHA-256, p0, current-gain rule, and diagnostic-only scope. Provenance: Gemini/Opus fresh-context physics reviews, 2026-09-08—fixed-EIRP forward links with ACM imply that segment-anchored gain inversion can manufacture a renewal premium; the ablation tests whether coordinator advantage and phase escalation collapse. No file under `src/` was edited or monkeypatched.

## Tests

Command:

```bash
PYTHONPATH=.scratch/multi-catfish-v023-c3s-screen:src \
  /home/sat/mcrl-leo-handover/.venv/bin/python -m pytest -q \
  .scratch/multi-catfish-v023-c3s-screen/test_c3s_screen.py \
  .scratch/multi-catfish-v023-c3s-screen/test_c3s_diagnostic_arms.py
```

Result: **49 passed**. This includes the original hardened v2 runner suite and sixteen diagnostic tests. New coverage proves that RANDOM_RENEW edits exactly one user per decision and retains same-link selection as an explicit renewal, BASE_FORCED_RENEW_4 renews only ages at least four, a synthetic three-step trajectory records the expected association/beam/age/power counts, all required step fields are present, the ablation holds served recurrence power at p0, merge strata plus the six-point energy grid consume the instrumented handover count, and estimates cover all three cheap arms under the ablation binding. Total test time remains below three minutes.

Additional checks passed:

```text
python -m py_compile <all five new executable Python modules>
git diff --check
diagnostic --dry-run --arms NULL HEUR NOMINAL_MPC --assert-null-equals-base
```

The dry run reported `BASE,NULL,HEUR,NOMINAL_MPC`, the fixed four worlds, three lineages, TRAIN, 100 users, and 30 steps.

## CLI

Requested single unit-set estimate on the v1 panel (`BASE` is explicit and normalized once):

```bash
PYTHONPATH=.scratch/multi-catfish-v023-c3s-screen:src \
  /home/sat/mcrl-leo-handover/.venv/bin/python \
  .scratch/multi-catfish-v023-c3s-screen/run_v023_c3s_diagnostic_arms.py \
  --estimate --estimate-units 12 \
  --physics-override none \
  --arms BASE,LITE,RANDOM_RENEW,RANDOM_RENEW_K,BASE_FORCED_RENEW_4,NULL
```

Decisive unit-set estimates for `{BASE,LITE,NULL,RANDOM_RENEW,BASE_FORCED_RENEW_4}` × `{none,ablate_anchor}` on the v1 panel:

```bash
for PHYSICS_OVERRIDE in none ablate_anchor; do
  PYTHONPATH=.scratch/multi-catfish-v023-c3s-screen:src \
    /home/sat/mcrl-leo-handover/.venv/bin/python \
    .scratch/multi-catfish-v023-c3s-screen/run_v023_c3s_diagnostic_arms.py \
    --estimate --estimate-units 12 \
    --physics-override "$PHYSICS_OVERRIDE" \
    --arms BASE,LITE,NULL,RANDOM_RENEW,BASE_FORCED_RENEW_4
done
```

For execution, use those exact arm and physics declarations in each of the 12 unit launch authorities and unit invocations, with separate output roots for `none` and `ablate_anchor`; build one matching merge authority per root. Add `--handover-energy-sensitivity` to the merge authority's bound launch arguments and the merge invocation when the offline sensitivity table is wanted. The flag is intentionally rejected on unit invocations.

All arms (estimate is simulator-inert):

```bash
PYTHONPATH=.scratch/multi-catfish-v023-c3s-screen:src \
  /home/sat/mcrl-leo-handover/.venv/bin/python \
  .scratch/multi-catfish-v023-c3s-screen/run_v023_c3s_diagnostic_arms.py \
  --estimate --arms NULL RANDOM_FEASIBLE SHUFFLED_SCORE HEUR HEUR_C3S_LITE \
  NOMINAL_MPC LITE_UNILATERAL_ONLY LITE_EVACUATION_ONLY
```

Dry run:

```bash
.../run_v023_c3s_diagnostic_arms.py --dry-run \
  --arms NULL RANDOM_FEASIBLE --assert-null-equals-base
```

Build the diagnostic-specific preflight:

```bash
.../build_c3s_diagnostic_preflight_manifest.py \
  --output .scratch/multi-catfish-v023-c3s-screen/C3S-DIAGNOSTIC-PREFLIGHT-MANIFEST.json
```

Build an exact unit launch authority (the arguments after `--launch-arguments` are bound verbatim):

```bash
.../build_c3s_diagnostic_launch_authority.py \
  --preflight-manifest .scratch/multi-catfish-v023-c3s-screen/C3S-DIAGNOSTIC-PREFLIGHT-MANIFEST.json \
  --output-root .scratch/multi-catfish-v023-c3s-screen/diagnostic-run \
  --output .scratch/multi-catfish-v023-c3s-screen/unit-authority.json \
  --launch-arguments \
  --preflight-manifest .scratch/multi-catfish-v023-c3s-screen/C3S-DIAGNOSTIC-PREFLIGHT-MANIFEST.json \
  --launch-authority .scratch/multi-catfish-v023-c3s-screen/unit-authority.json \
  --output .scratch/multi-catfish-v023-c3s-screen/diagnostic-run \
  --unit 8464287092499831892:2026092101 \
  --arms NULL RANDOM_FEASIBLE --assert-null-equals-base
```

Unit and merge use the same runner shape as v1:

```bash
.../run_v023_c3s_diagnostic_arms.py --preflight-manifest ... \
  --launch-authority ... --output ... --unit WORLD:LINEAGE \
  --arms NULL RANDOM_FEASIBLE --assert-null-equals-base

.../run_v023_c3s_diagnostic_arms.py --preflight-manifest ... \
  --launch-authority ... --output ... --merge \
  --arms NULL RANDOM_FEASIBLE --assert-null-equals-base
```

Offline attribution:

```bash
PYTHONPATH=.scratch/multi-catfish-v023-c3s-screen:src \
  /home/sat/mcrl-leo-handover/.venv/bin/python \
  .scratch/multi-catfish-v023-c3s-screen/attribute_c3s_receipts.py \
  --receipts /home/sat/mcrl-v023-c3s-run/.scratch/multi-catfish-v023-c3s-screen/runs/c3s-20260908-r1 \
  --output-json .scratch/multi-catfish-v023-c3s-screen/C3S-V1-ATTRIBUTION-2026-09-08.json \
  --output-markdown .scratch/multi-catfish-v023-c3s-screen/C3S-V1-ATTRIBUTION-2026-09-08.md
```

## Per-arm estimates

Each arm was run separately through `--estimate --arms ARM` with 12 units. These are planning estimates, not executed compute or latency measurements.

| Arm | Estimated worker-hours | Ratio to v1 full nominal pass |
|---|---:|---:|
| `NULL` | 14.260229 | 1.0 |
| `RANDOM_FEASIBLE` | 1.426023 | 0.1 |
| `SHUFFLED_SCORE` | 1.426023 | 0.1 |
| `HEUR` | 0.000000 catalog hours | 0.0 |
| `HEUR_C3S_LITE` | 14.260229 | 1.0 |
| `NOMINAL_MPC` | 14.260229 | 1.0 |
| `LITE_UNILATERAL_ONLY` | 1.426023 | 0.1 |
| `LITE_EVACUATION_ONLY` | 1.426023 | 0.1 |
| `RANDOM_RENEW` | 0.000000 catalog hours | 0.0 |
| `RANDOM_RENEW_K` | 0.000000 catalog hours | 0.0 |
| `BASE_FORCED_RENEW_4` | 0.000000 catalog hours | 0.0 |

HEUR and all three churn arms still incur committed episode execution, BASE-proposal/instrumentation work where applicable, and one nominal instrumentation evaluation per step; zero is specifically catalog-evaluation worker-hours. `HEUR_C3S_LITE` is estimated at a full pass because ranking the per-user alternatives by nominal marginal F first evaluates the complete unilateral set. Receipts report measured costs and should supersede these estimates after an authorized run.

## Offline v1 attribution

The complete machine-readable output is in `C3S-V1-ATTRIBUTION-2026-09-08.json`; the full human-readable tables, including every FULL/LITE divergence row, are in `C3S-V1-ATTRIBUTION-2026-09-08.md`.

### Selected configuration labels

| Arm | BASE | Unilateral | Evacuation |
|---|---:|---:|---:|
| BASE | 360 | 0 | 0 |
| FULL | 0 | 194 | 166 |
| LITE | 0 | 55 | 305 |
| Pooled | 360 | 249 | 471 |

These are selected catalog profile labels. V1 retained aliases, so different unilateral/evacuation labels can represent an identical executed vector.

Users moved are exactly recoverable as zero for BASE-labelled decisions and one for unilateral-labelled decisions. The exact member count for each of the 471 evacuation-labelled decisions is not recoverable: v1 receipts do not retain the action vectors or the origin membership. Active-beam counts are likewise **not recoverable**, because only aggregate action-trace digests—not per-step actions, physical-key tables, masks, or resolved beam sets—were retained.

### Cumulative pooled EE advantage vs BASE

| Through step | FULL | LITE |
|---:|---:|---:|
| 0 | 1.081252% | 1.081252% |
| 1 | 1.288479% | 1.288479% |
| 2 | 2.037378% | 2.037378% |
| 3 | 2.452899% | 2.452899% |
| 4 | 2.249897% | 2.249897% |
| 5 | 2.298523% | 2.270533% |
| 6 | 2.315491% | 2.303332% |
| 7 | 2.666813% | 2.693400% |
| 8 | 2.436907% | 2.462600% |
| 9 | 2.425197% | 2.454949% |
| 10 | 2.481562% | 2.498333% |
| 11 | 2.564389% | 2.567600% |
| 12 | 2.442784% | 2.443801% |
| 13 | 2.343766% | 2.352480% |
| 14 | 2.568181% | 2.533749% |
| 15 | 2.942694% | 2.943664% |
| 16 | 2.861028% | 2.854846% |
| 17 | 2.783466% | 2.767724% |
| 18 | 2.809821% | 2.779778% |
| 19 | 3.018736% | 2.993292% |
| 20 | 2.931792% | 2.898990% |
| 21 | 2.843053% | 2.796661% |
| 22 | 2.793537% | 2.746646% |
| 23 | 2.984346% | 2.961409% |
| 24 | 2.863850% | 2.839112% |
| 25 | 2.814707% | 2.796403% |
| 26 | 2.871275% | 2.884433% |
| 27 | 3.070603% | 3.098777% |
| 28 | 2.937460% | 2.983865% |
| 29 | **2.883167%** | **2.921776%** |

The gain appears throughout the episode rather than only at the endpoint: both arms are already above +1% after the first pooled step and generally remain between roughly +2.2% and +3.1% after step 3.

FULL and LITE have **173 divergent selected-profile-ID decisions**. The companion JSON and Markdown record every such world/lineage/step with FULL-minus-LITE nominal bits, energy, service and F, plus realised bits, joules and service. Per-step action-vector divergence itself is not recoverable from v1's aggregate action-trace digest. Several early divergences have zero nominal and realised deltas, consistent with retained catalog aliases; the output reports them rather than silently treating profile-ID divergence as action divergence.

## Files

- `run_v023_c3s_diagnostic_arms.py` — unit/merge/dry-run/estimate runner.
- `c3s_diagnostic_policy.py` — diagnostic selection and Q-free policy layer.
- `c3s_physics_override.py` — explicit digest-bound diagnostic physics path.
- `build_c3s_diagnostic_preflight_manifest.py` — diagnostic preflight builder.
- `build_c3s_diagnostic_launch_authority.py` — exact-invocation authority builder.
- `attribute_c3s_receipts.py` — offline JSON/Markdown attribution.
- `test_c3s_diagnostic_arms.py` — synthetic diagnostic tests.
- `C3S-V1-ATTRIBUTION-2026-09-08.json` and `.md` — generated v1 attribution outputs.

No existing sealed/read-only file or SHA-256 sidecar was modified, and no TEST split, training, learner update, or simulator unit compute was opened.
