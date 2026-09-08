# C3-S variant matrix implementation report

Status: implementation and non-formal verification complete. No unit or merge run was launched.

## Delivered surface

- `variants_config.json` is the single declaration site for the nine-arm order, fixed panel, kill margin, reporting thresholds, and all seven variant lever values.
- `variant_policy.py` imports the RUNNING v1 `c3s_policy` and provides one generic hook record with catalog builder, exact objective, gate, and post-decision state functions.
- `run_v023_c3s_variants.py` imports the v1 environment/unit helpers and runs nine fresh closed-loop trajectories from the same authenticated initial state.
- `build_variant_preflight.py` accepts the v1 builder inputs `--evidence-manifest`, `--world-census`, `--freeze-timestamp-utc`, and `--reviewer`.
- `build_variant_launch_authority.py` binds one exact formal invocation to the sealed contract placeholder, preflight, code census, panel, freeze provenance, output root, and arguments.
- `test_variant_matrix.py` covers all variant rules, nine-arm/state independence, exact pooling helpers, refusal boundaries, reversals, and write-once sealing.

The controller-owned contract path is:

`V023-C3S-VARIANT-MATRIX-KILL-SCREEN-CONTRACT-2026-09-08.md`

Formal preflight/authority/unit/merge paths fail closed until that file and its matching `.sha256` sidecar are both mode `0444`.

## Variant semantics

| Arm | Reference plus exactly one change |
|---|---|
| BASE | Imported Q1+Q2 BASE policy |
| LITE | Imported v1 lite coordinator |
| V-J | Lite catalog filtered to BASE plus evacuation rows |
| V-U | Lite catalog filtered to BASE plus one Q-ranked physical alternative per user (top-2 including BASE), with no evacuations |
| V-M | Lite selection accepted only when exact objective improvement is at least `0.001 × B_BASE` |
| V-C | Lite coordination only at `t mod 3 = 0`; other decisions evaluate and execute BASE only |
| V-H | Coordinator-moved users are excluded from coordinator deviations at the next three decisions; BASE remains unrestricted |
| V-P | Lite objective subtracts `κ Σ(1-χ̂_u)`, where `χ̂_u` is the final absorbing OPS-3 persistence indicator over `H=min(3,T-1-t)` |
| V-L2 | Lite current nominal objective plus one projected BASE interval on a deep-cloned tracking/environment state with fading disabled; terminal decisions use the available current interval |

All objectives and gates compare `Fraction` values. All variants retain the imported nominal BASE service guard and BASE-first fixed tuple tie order.

## Reports emitted by a complete merge

For every arm the terminal receipt includes exact pooled total bits, energy, EE, service, a 30-point cumulative EE/service curve, per-world and per-lineage pooled breakdowns, action changes, association reversals within three steps, decision latency mean/median/p95/max plus counts above 30.08 seconds, and catalog-size min/mean/max. Each coordinator arm receives the same v1 kill rule independently: EE strictly above BASE and service no lower than BASE minus 0.001.

## Non-formal verification

Interpreter and environment:

`/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=<worktree>/src`, `TMPDIR=<worktree>/.tmp`, and all OMP/OpenBLAS/MKL/NumExpr thread variables set to `1`.

Tests: `42 passed` for the combined untouched v1 suite and variant suite.

Dry-run:

`C3S_VARIANTS_DRY_RUN_PASS arms=BASE,LITE,V-J,V-U,V-M,V-C,V-H,V-P,V-L2 units=12 contract=AWAITING_CONTROLLER_PLACEHOLDER`

The 12-unit estimate covers 108 episodes. Approximate nominal-evaluation worker hours per arm are BASE `0`, LITE `1.4260`, V-J `1.4260`, V-U `1.4260`, V-M `1.4260`, V-C `0.4753`, V-H `1.4260`, V-P `1.4260` plus unpriced OPS-3 projection cost, and V-L2 `2.8520`. V-J/V-U use the conservative v1 lite ratio despite their filtered catalogs.

`TASK_EXIT=DONE`
