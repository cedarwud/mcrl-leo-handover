INCOMPLETE — the reusable instrument exists, but the required full panel is not yet sound; at the inherited 20-anchor, 12-seed, four-world scale under both rules its present measured-cost projection is **185.15 worker-hours + 15.5077 × E seconds** for caller-declared epoch count `E`.

# C3 panel harness — 2026-09-10

`DIAGNOSTIC_NOT_CLAIM`. This is an instrument build and smoke, not a production training run, policy run, acceptance run, or efficacy result. No epoch, anchor, seed, checkpoint, acceptance threshold, sign, price, horizon, service guard, or policy decision is selected here. The smoke uses already-declared fixtures solely to exercise code paths.

## Status

The reusable pieces are in `src/mcrl/stagec_v025/c3_panel.py`; the branch exercise is `scripts/run_c3_panel_smoke.py`; and the read-only sealed-rule bridge is `scripts/run_c3_rule_evaluator.py`. Contract tests are in `tests/stagec_v025/test_c3_panel_harness.py`.

The implementation is deliberately reported **incomplete**. Numeric realised evaluation now reaches both verified sealed `SEALED` and `MARGIN_Q` evaluators, but MARGIN_Q-specific proposal/catalogue construction is not integrated with the current exact-row workspace. The source tape and the sealed evaluator tape also have different authenticated digests. Those are material soundness failures, not documentation nits. H6 lists every known gap.

## H1 — arms

The requested intervention list is the complete binary factorial over three sources: eight learned arms, plus the external control, for nine total arm slots. The phrase “nine learned arms plus the external control” conflicts arithmetically with the combinations it enumerates and with the supporting nine-catalogue costing. I implemented the coherent complete factorial and did not invent a duplicate ninth learned treatment.

| arm | C1 training source | C2 training source | C3 training source | construction |
|---|---|---|---|---|
| `FULL` | informed | informed | informed | No source replacement. |
| `DROP_C1` | neutral | informed | informed | Replace only C1's source. |
| `DROP_C2` | informed | neutral | informed | Replace only C2's source. |
| `DROP_C3` | informed | informed | neutral | Replace only C3's source. |
| `ONLY_C1` | informed | neutral | neutral | Only C1 is informative. |
| `ONLY_C2` | neutral | informed | neutral | Only C2 is informative. |
| `ONLY_C3` | neutral | neutral | informed | Only C3 is informative. |
| `ALL_NEUTRAL_CONTROL` | neutral | neutral | neutral | Replace all three sources. |
| `BASELINE` | n/a | n/a | n/a | External geometry-only control; it has no learned heads. |

Every learned arm is cloned from the same production initialization. Every source epoch updates C1/Q1, C2/Q2 and C3/Psi in every learned arm, including a head trained on its neutral source. Deployment receipts reject zero epochs, a missing head, or an update count unequal to the completed source-epoch count. There are no knocked-out or zeroed deployed heads.

The successful smoke trained two source epochs using the first already-declared `LEARNER_SEEDS` entry. It recorded 2 updates for each of C1, C2 and C3 in each of the eight learned arms, and `all_learned_arms_retain_update_deploy_all_heads=true`. This is branch coverage only.

## H2 — exact rows

The smoke executes `_build_anchor_rows` through a private copy of its globals with `PILOT_PRIMITIVE_SOURCE_FALLBACK=False`. It does not mutate the module constant: the imported source value was true before and after the run. The repository's default path therefore remains exactly as found.

The non-fallback C1 branch now calls the production `c1_difference_surplus`; C2 calls the production `c2_persistence_forecast`; optional coalition generation calls the production coalition identity target. C1 is built from exact complete-profile totals and rekey-aware Phi. This refactor changes the arithmetic ordering from the prior inline C1 expression—decimal-rationalising complete totals before subtraction rather than decimal-rationalising already-subtracted binary64 values—so I do **not** claim that exact-branch C1 bytes are unchanged. The default fallback byte-identity proof is not touched.

On two real `V025_PROBE/world/1` source anchors, the smoke wrote 1,983 source rows and two coalition rows. Assertions executed were:

| assertion | count |
|---|---:|
| Q2 `valid` and `survives` pass through each of three offsets exactly | 11,898 |
| C1 and C2 serialized labels equal their production target function outputs | 3,966 |
| `outage` equals absence from exact `served_phy` | 1,983 |
| exact Phi call carried the rekey-context argument | 3,966 |

The exact-versus-fallback differential witness counts were:

| audited field/group | differing rows/anchors |
|---|---:|
| C1 label | 1,783 |
| C2 label | 1,873 |
| current margin | 1,883 |
| required power/cap feature | 1,783 |
| previous-beam RF feature | 1,571 |
| current ACM SE | 1,983 |
| forecast margin | 1,983 |
| forecast ACM SE | 1,983 |
| forecast SE trend | 1,983 |
| validity/survival | 1,130 |
| outage | 68 |
| selected coalition identity | 2/2 anchors |
| C1 Phi value | **0** |

The C1 Phi *path* is asserted, but these dense-array anchors contain no observable cell-rekey event, so the required value differential was not demonstrated. H2 is therefore not complete.

## H3 — matched-anchor tier

`ArmPlan` owns an arm name, its starting physical assignment, its ordered scored catalogue, and its first-improvement declaration. The seed must occur exactly once in that catalogue and must pass the unchanged guards. Selection performs ordered first strict improvement over physical assignments that differ in exactly one user's action, repeating to a fixed point of that static bounded catalogue. It does not take a global maximum. This is not the authoritative exact unilateral algorithm, which regenerates the full one-user neighbourhood after every accepted move.

For the smoke, each trained model runs the production Q1+Q2 proposal. Because all eight raw proposals failed the unchanged “served-user count must not decrease versus BASE” guard after only two smoke epochs, each ran the production deterministic repair against exact guarded support. Each then built its own `bounded-union-v2` catalogue around the repaired seed. The eight learned catalogues each had 911 rows; the external baseline catalogue had 1,004. The smoke happened to produce only two physical seed families—one learned family and BASELINE—so it is not evidence of the disjoint catalogues observed in the supporting audit. All nine authenticated scored-catalogue hashes were distinct.

`PhysicalCacheKey` binds:

- tape digest and world identity;
- decision time;
- canonical complete physical assignment;
- physical-setting and run-setting digests;
- evaluator identity;
- nominal, margin, or realised field;
- boundary set;
- transition digest; and
- prefix-history digest.

`select_then_realise` first selects all nine choices without calling the cache, seals a barrier, forms the union of complete physical keys, then evaluates each unique key once. The smoke selected nine arm slots but realised four unique configurations under each rule.

`test_shared_physical_cache_cannot_leak_into_selection` is a teeth test: its cache raises unless all nine keys have already been constructed, and a direct pre-barrier access must raise `StageCContractError`. Moving a realised lookup into the arm selection loop makes the test fail. Another test mutates every required cache-key dimension independently and requires a different digest.

Both named rule adapters are selected with `--variant SEALED` or `--variant MARGIN_Q` inside the child bridge. The bridge verifies the sibling sealed manifest and loads the registered evaluator. It uses one long-lived child, not a pool; parent plus child is the observed peak of two worker processes.

Important limitation: the smoke constructs learned plans once with this workspace's inherited catalogue builder, then sends selected complete assignments to the two sealed numeric evaluators. It does not construct MARGIN_Q-specific arm catalogues. This is not full two-rule support.

## H4 — degeneracy report

`degeneracy_report` is reporting-only. It never filters its input anchors. It requires reference metadata declaring a head-independent fixed-point certificate and rejects malformed certificate identities. Below-reference status uses exact cross multiplication:

```text
arm_bits × reference_joules < reference_bits × arm_joules
```

There is no epsilon, tolerance, or threshold. Floats are converted to their exact binary64 rational values before comparison.

For every named pairwise contrast, the report returns both:

1. the ratio-of-sums pooled-EE marginal on all input anchors; and
2. the same marginal on the supplementary subset where both arms are at or above reference.

The all-anchor rows remain present. An empty restricted subset reports no marginal rather than altering the population.

Each arm also reports its below-reference count, fraction, and the ordered per-anchor positive shortfall distribution in bits/J (plus minimum and maximum). These are supplementary diagnostics; they do not gate or remove an anchor.

The smoke reports SEALED and MARGIN_Q separately. However, its certificate is only a hash over the bounded smoke BASELINE neighbourhood and a head-independent score ordering. It does not invoke the pre-declared controller's authoritative full-neighbourhood certified reference builder. The certificate is therefore self-attested, and H4 remains incomplete despite the reporting arithmetic being correct.

## H5 — smoke and measured cost

Successful command:

```bash
PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python scripts/run_c3_panel_smoke.py --output .scratch/c3-panel-smoke-r8
```

The receipt is `.scratch/c3-panel-smoke-r8/smoke.json`. It is labelled `DIAGNOSTIC_NOT_CLAIM`, `smoke_test_not_evidence=true`, `production_training_run=false`, and `policy_run=false`. It uses two exact training-source anchors, one already-declared learner seed, two source epochs, all eight learned treatments plus BASELINE, one tier anchor, and both numeric realised-rule branches. The tier's one-anchor scope is another reason it is not a complete branch exercise of the requested “couple of anchors.”

The smoke's raw receipt says `processes_used=1`, meaning its parent worker. The actual measured peak was two workers while the single sealed-rule child was alive. The current script names this unambiguously as `worker_processes_used_peak=2`; no pool is created and the limit is four.

Measured costs:

| item | measurement |
|---|---:|
| exact row build, anchor 1 | 50.813266 s |
| exact row build, anchor 2 | 48.887026 s |
| exact row build mean | **49.850146 s/anchor** |
| eight-arm training, two epochs | 0.129231 s |
| training | **0.008076929 s/learned arm/epoch** on 1,983 rows |
| SEALED online first-improvement selection after plans exist | 0.215401 s/anchor |
| MARGIN_Q online first-improvement selection after plans exist | 0.213972 s/anchor |
| online selection mean | **0.214686 s/anchor/rule** |
| SEALED realisation, union of four | 3.494637 s/anchor |
| MARGIN_Q realisation, union of four | 3.498780 s/anchor |
| realisation mean | **3.496708 s/anchor/rule** for this four-configuration union |
| sealed rule/tape setup | 18.548685 / 18.708488 s |
| total smoke wall time, filesystem timestamps | 1,113.547478 s |
| residual arm proposal/repair/catalogue/scoring preparation | approximately **935.949514 s for the one tier anchor** |

The residual subtracts measured tape, row, fallback-comparison, training, rule setup, online selection, and realisation times from total wall time. It includes small shard/report overhead, so it is a conservative measurement of plan preparation, not a pure profiler sample. The dominant cost is no longer the four chosen outcomes; it is the deliberately reviewable, unoptimised repeated proposal repair, catalogue construction, guard evaluation, and learned scoring.

Let:

- `A` = caller-declared anchors per learner seed per rule;
- `S` = caller-declared learner seeds;
- `E` = caller-declared source epochs;
- `W` = worlds;
- `R=2` provisioning rules, `P=9` panel arms, and `L=8` learned arms.

Using the smoke measurements, assuming training scales linearly from its two-anchor batch and—because a sound MARGIN_Q catalogue is still missing—charging plan preparation independently to both rules:

```text
T_rows   = R × A × S × P × 49.850145773
T_plans  = R × A × S × 935.949513683
T_select = R × A × S × 0.214686478
T_real   = R × A × S × 3.496708335
T_train  = R × S × L × E × 0.008076929 × (A / 2)
T_setup  = R × W × 18.628586473
T_total  = sum of the six terms, in seconds
```

For the inherited audit illustration `A=20`, `S=12`, `W=4`—not a choice made by this instrument—and leaving `E` symbolic:

```text
T_rows   = 2 × 20 × 12 × 9 × 49.850145773 = 215,352.630 s = 59.820 h
T_plans  = 2 × 20 × 12 × 935.949513683    = 449,255.767 s = 124.793 h
T_select = 2 × 20 × 12 × 0.214686478      =     103.050 s = 0.029 h
T_real   = 2 × 20 × 12 × 3.496708335      =   1,678.420 s = 0.466 h
T_setup  = 2 × 4 × 18.628586473            =     149.029 s = 0.041 h
T_train  = 15.507704 × E s                 = 0.0043077 × E h
T_total  = 666,538.895 + 15.507704 × E s
         = 185.150 + 0.0043077 × E worker-hours
```

This is a current-instrument workload projection, not a runtime promise. It deliberately does not select `E`. It also does not assume the smoke's four-way union will remain four, or linearly extrapolate the supporting audit's small realised batches. A future authenticated cache may reduce duplicated exact work, but cached realised outcomes may never enter selection.

Verification commands:

```bash
PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python -m pytest tests/stagec_v025/test_c3_panel_harness.py -q

PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 nice -n 15 /home/sat/mcrl-leo-handover/.venv/bin/python -m pytest tests/stagec_v025 -q

PYTHONPATH=src /home/sat/mcrl-leo-handover/.venv/bin/python -m py_compile src/mcrl/stagec_v025/c3_panel.py scripts/run_c3_panel_smoke.py scripts/run_c3_rule_evaluator.py tests/stagec_v025/test_c3_panel_harness.py

git diff --check
```

The focused harness suite passed 9/9. After the final guard, adapter, and reporting refinements, the one-process Stage-C suite passed all 43 tests. Compilation and `git diff --check` also passed.

## H6 — deliberately not built, and remaining unsoundness

1. **No experiment was run.** There is no production training, policy rollout, acceptance decision, route-benefit estimate, checkpoint selection, or scientific claim.
2. **MARGIN_Q planning is incomplete.** Realised outcomes use the verified MARGIN_Q evaluator, but proposal repair and bounded catalogue construction are still performed once through this workspace's inherited SEALED-era builder and reused across rule branches. A sound full panel must rebuild each arm's own catalogue under each rule.
3. **The cross-workspace tape bridge is unauthenticated.** The exact-source tape digest was `09129e…d32e`; the sealed numeric-evaluator tape digest was `c949f8…64a6`. The adapter reconstructs and validates complete physical assignments, and its cache key binds the evaluator tape, but no proof establishes exogenous/context equivalence across those snapshots. Until that proof or a single-snapshot integration exists, pooled comparisons are unsound.
4. **The authoritative degeneracy reference is missing.** The reporting function is exact and non-filtering, but the smoke certificate is not the pre-declared controller's head-independent full-neighbourhood fixed-point certificate.
5. **No observed rekey/Phi differential exists.** The correct argument path was called 3,966 times, but the sampled dense anchors had no rekey event and C1 Phi differed on zero rows. H2's required value witness remains open.
6. **The tier smoke evaluates one physical anchor.** Two anchors feed exact source/training; only the first feeds proposal, selection, realisation, and screening.
7. **The learned search certificate is bounded.** First-improvement is genuine, but it operates on one static bounded catalogue; it does not regenerate the exact complete unilateral neighbourhood after every move and cannot substitute for the pre-declared exact reference search.
8. **C1 exact-branch arithmetic changed.** Routing C1 through the production target function is required by H2, but the rationalisation/subtraction order differs from the prior exact inline expression. It needs an explicit compatibility decision; no byte-identity claim is made.
9. **The cache is in-memory and per process.** Its schema and non-leak barrier are implemented and tested, but there is no persistent authenticated cache, crash recovery, or cross-job locking.
10. **There is no production-scale CLI.** This is intentional: the instrument does not offer a default epoch count, anchor count, seed count, or post-result checkpoint picker. An owner-supplied, predeclared run manifest and an authenticated checkpoint schedule are still required.
11. **No optimisation is certified.** Reusing repair support or route-local trained heads may be exact, but neither optimisation was installed because its authentication proof is not yet part of this instrument.
12. **Failed smoke directories remain.** `.scratch/c3-panel-smoke-r5`, `r6`, and `r7` are failed write-once diagnostics; `r8` is the successful receipt. They were not deleted or rewritten.
13. **No commit was made.** The worktree contained the user's encoder-seam and retraining changes before this task, and the repository metadata is read-only in this environment. Unrelated changes were preserved.

The correct next engineering step is not a production run. It is to unify exact row construction, arm-owned rule-specific catalogue construction, the pre-declared reference certificate, and both registered numeric evaluators on one authenticated tape/physics snapshot; then rerun the two-anchor smoke and obtain the missing rekey/Phi witness before any owner chooses `A`, `S`, or `E`.
