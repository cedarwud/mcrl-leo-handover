## Outcome

Stage 4 is not ready for 4b. Audit target is controller snapshot `bc7d35c0`; uncommitted stage-4b edits that appeared during this audit were excluded. The 151-test suite passed at that snapshot.

A later sealed controller decision, `V025-CONTROLLER-DECISIONS-SELECTION-TIME-APPROXIMATIONS-2026-09-08.md`, supersedes parts of items 2, 12, 23, 26, and 35; the stage-4 snapshot contradicts those newer requirements.

Evidence aliases below refer to `bc7d35c0`:

- `runner` = `.scratch/.../probe/run_v025_matrix_probe.py`
- `report` = `.scratch/.../V025-ENGINE-STAGE4-REPORT-2026-09-08.md`
- `seal` = `.scratch/.../probe/SEAL-PACKAGE-DRAFT-2026-09-08.md`
- I = independent KAT; T = tautological/self-derived KAT.

## Items 1–36

| # | Status | Evidence and KAT |
|---:|---|---|
| 1 | DONE | `runner:1912-1965,2002-2006,2601-2606`: 30 steps × three carriers, offsets 1–3, stride receipted and merge-enforced. KAT: none for exact 90-anchor/default-stride behavior. |
| 2 | CONTRADICTS | `runner:415-503` has the bounded union, but ranks top-K by option count at `447-454`, not nominal surplus. It also retains all legal unilaterals, contradicting the later top-8 shortlist decision lines 5–8. KAT: none. |
| 3 | DONE | `targets.py:310-339`; pair Ψ is interaction-only and split equally. KATs `test_stage4_contract.py:52-92` are I and prove Ψ=2, `(1,1)`, and C1+C3 no-double-counting. |
| 4 | DONE | `runner:1693-1789` implements the three numerical QoS margins. `test_stage4_contract.py:165-186` is I and makes only availability fail. |
| 5 | DONE | `provider_legacy.py:1-16`, provider installation at `runner:2395-2410`, and `report:52-64`. The 19 provider KATs, especially `test_provider_legacy.py:102-182,249-315`, are I against legacy or hand calculations. |
| 6 | NOT DONE | Formal R2 manifest, calibration, rehearsal, q, projection, and stride were not run: `report:91-94`. `_calibrate` uses only one decision step per calibration world at `runner:807-851`, not the full reference or a labelled five-step provisional fallback. KAT: none. |
| 7 | PARTIAL | Smoke labelling/exclusion exists at `runner:1977-1979,2566-2570,2737-2742`, but no smoke ran: `report:95-97`. KAT: none. |
| 8 | PARTIAL | Seal remains HOLD with pending worlds/calibration/stride at `seal:65-130,153-176`; launch command still contains `STRIDE_PENDING` at `seal:233`. KAT: none. |
| 9 | DONE | Report truthfully records 132 engine + 19 provider tests, dry-run digest, missing rehearsal/smoke, and blockers at `report:50-64,89-120`. KAT: N/A. |
| 10 | PARTIAL | `matched_anchor_decomposition` exists at `targets.py:422-463`, but A/I and Δ_joint are not emitted per anchor; admitted at `report:106-108`. `test_stage4_contract.py:119-135` is T because its RHS reuses returned `eta0` and checks an identity constructed internally. |
| 11 | PARTIAL | S_UNI iteration and timing exist at `runner:1128-1171,1476-1494,1531-1533`. FULL/DROP lack the same service guard, and no exact best-response oracle exists. `test_stage2_runner.py:26-38` is T for arm coverage because both lists derive from `ARMS`. |
| 12 | CONTRADICTS | Stage 4 uses 30.08 s at `runner:135-152,1433-1435`; later sealed decision line 11 requires 10 s. `test_contract_discriminators.py:151-166` is I for the fallback helper but does not exercise a real whole-path timeout. |
| 13 | PARTIAL | Correct Shapley helper at `targets.py:351-408`; `test_stage4_contract.py:95-116` is I enough to reject equal-share allocation. It is not wired into production selection: `runner:1024-1055`; `report:106-108`. |
| 14 | DONE | Exact admission wording appears at `seal:213-218`. KAT: none. |
| 15 | DONE | Per-chain identities flow through `tapes.py:125-150,485-533` and `architectures.py:297-316`. `test_provider_legacy.py:249-293` is I against the legacy interference helper; gain parity is independently checked at `102-122`. |
| 16 | DONE | Dense arrays and manifest bindings are at `tapes.py:536-580,731-770`; provider always prepares 33 steps and hashes generating inputs/k=0 state at `provider_legacy.py:168-181,890-943`. KATs `test_provider_legacy.py:364-398` are I/structural. |
| 17 | PARTIAL | Event-derived interruptions are wired at `runner:541-585,701-721`. `test_stage3_parity_uncertainty.py:230-251` is I, but required a-γ twin and pairwise-distinct-31 receipt KATs are absent. |
| 18 | CONTRADICTS | Same selector class exists at `runner:1087-1125,1489-1493`, but production C3 stores a maximum per `(user, action)` and reuses it across arbitrary coalitions at `1024-1055,1097-1107`, contradicting v1.5’s configuration-level Ψ/Shapley definition. Required nonzero/zero interaction KATs are absent. |
| 19 | PARTIAL | Beam-chain colour and cross-gain paths work, with I KATs at `test_architectures.py:111-144` and `test_provider_legacy.py:249-293`. No reciprocal-reuse-mask KAT and no real rehearsal rerun. |
| 20 | PARTIAL | Size guard and non-collapse exist at `runner:415-503`, but zero-legal users retain their incumbent identity in most bounded rows rather than always receiving NULL. Required 11-non-BASE-arm KAT: absent. |
| 21 | PARTIAL | Deadline KAT was repaired and several new physical oracles were added, but 15/151 current KATs remain tautological; the independent frozen-transcription ACM-row oracle and several required end-to-end discriminators remain absent. |
| 22 | PARTIAL | World-separation guard and I collision KAT: `runner:2257-2338`, `test_stage4_contract.py:189-214`. The batch path bypasses `resolve_configuration` at `runner:614-699`; C2 schema imports are unused; dry-run reports a helper identity rather than asserting every unit trajectory. |
| 23 | CONTRADICTS | Dense batch exists at `batch.py:67-364`, but has no scalar-equivalence KAT and its solver omits relative convergence/CONVERGED_SLOW handling at `batch.py:231-256`. Targets were missed (`report:76-87`), provider is rebuilt per unit at `runner:1930-1935`, and the later coarse-grid/two-stage decision is absent. |
| 24 | PARTIAL | Arithmetic is correct at `endpoint.py:143-164`, `calibration.py:128-133`, `targets.py:164-173,266-297`. Numeric KAT `test_stage4_contract.py:138-162` is I. No symbolic unit-carrying KAT, and serialized/API name `kappa_bits_per_user_s` incorrectly says per-second. |
| 25 | NOT DONE | No hidden-state dependency-allowlist KAT or explicit opening-state certificate. `report:109-112` acknowledges the missing discriminator. |
| 26 | CONTRADICTS | Capability text exists at `seal:201-211`, but falsely claims all set arms apply the service guard and records the superseded 30.08-s deadline rather than 10 s. KAT: none. |
| 27 | PARTIAL | Arm ledger uses the prior incumbent at `runner:1948-1960,1516-1521`; canonical rows carry prior/current identities at `1302-1354`. Only three event kinds are tested at `test_stage2_tapes_targets_state.py:347-357`; no five-kind three-step or per-arm closed-loop trajectory KAT. |
| 28 | PARTIAL | Hash-chained STARTED/DONE enforcement exists at `runner:198-255,2547-2577`, but registry path is engine-local at `runner:102`, not controller-hub-owned. KAT: none. |
| 29 | PARTIAL | Canonical rows include energy, service, identities/events, Φ, and digests at `runner:1319-1357`; merge reaggregation checks only bits/joules at `1362-1373`. Required independent bit-for-bit complete reaggregation KAT: absent. |
| 30 | PARTIAL | Dry-run and immutable receipts exist at `runner:2422-2440,2655-2673`, but there is no shared conformance suite over every comparative harness or complete authority-manifest KAT. Dry-run arm coverage KAT is T; write-once receipt KAT is I. |
| 31 | PARTIAL | Scalar and batch paths stop radiation on live mask loss at `tapes.py:793-807` and `batch.py:179-182`. Boundary-17 D2-release and 10°-crossing KATs are absent. |
| 32 | PARTIAL | Nominal forecasts, focal survival, INVALID propagation, and negative internal margins exist at `runner:882-949`; forecast rows/margins are not emitted or schema-stamped. Helper arithmetic KAT `test_stage2_tapes_targets_state.py:262-280` is I but not production-path coverage. |
| 33 | DONE | Full-roster denominators and distinct decoding/useful/partial/complete fields are at `runner:1251-1295`. `test_contract_discriminators.py:89-105` is T for the mask mapping, though its endpoint denominator check calls production code. |
| 34 | DONE | Twelve-chain census at `energy.py:119-130`; `test_energy_endpoint.py:70-84` is I with hand-calculated 12/11 idle-chain values. |
| 35 | CONTRADICTS | Timer begins before catalogue creation at `runner:1423-1438`, but deadline enforcement occurs before final arm evaluation/validation at `1501-1523`. It also retains 30.08 s versus the later sealed 10 s. Fallback-helper KAT is I but incomplete. |
| 36 | PARTIAL | R2 domains and world/learner seed fields exist at `tapes.py:36-39`, `runner:1981-2000`. Synthetic/KAT namespaces are absent, and merge pooling is incomplete. Domain-disjointness KAT `test_stage2_tapes_targets_state.py:86-93` is I. |

## Independent checks

- **(a) B2:** A constructed four-profile anchor using production `_set_select` gave `FULL=11`, `DROP_C3=00`. With realised endpoints 120/100 versus 100/100, the runner returned 20.0%, equal to the hand value `(1.2/1.0)-1 = 0.20`. This verifies the selector can respond to C3, but not the production factor generator: `_factor_scores` still misattributes pair interactions and has no required repository KAT.

- **(b) B1:** On a three-step synthetic world with an actual satellite handover, NOMINAL_GREEDY produced:

  - a-γ0: 68,749,061,200.00003 bits
  - a-γH: 68,724,803,815.49048 bits

  At the handover anchor, useful availability changed from `0.92021276596` to `0.91785239362`. B1’s runtime mechanism works; its complete KAT obligation does not.

- **(c) Zero-legal catalogue:** A bounded synthetic census with one zero-legal user yielded 134 rows, including 133 non-BASE rows, so it does not collapse. However, that user appeared as both incumbent `(9,9)` and `None`; the declared “explicit null action” invariant is not enforced across the catalogue.

- **(d) Per-chain interference:** Hand fixture produced 2 W same-satellite-chain + 3 W other-satellite-chain = 5 W total; the 4 W off-colour chain was excluded. This reaches `Transmission.interference_w` correctly.

- **(e) κ units:** With 1200 bits, 3 users, 4 decision steps, κ=100 bits/user-step; doubling Δt leaves 100, doubling bits leaves 200. A 100-bit C1 surplus becomes 1 κ, and Φ=−0.5 yields normalized C1=0.5; a 300-bit C2 surplus becomes 3. Arithmetic is dimensionally correct end-to-end, but field names and the missing symbolic unit fixture leave item 24 partial.

- **(f) Incumbent ledger:** At synthetic step 1, random-masked carrier, the NULL/BASE arm recorded prior `[80003,1]`, current `[80001,1]`, and `satellite_change`; current equalled the same-step BASE. Thus “before” is the previous incumbent, not the same-step BASE. Closed-loop per-arm trajectories remain absent.

- **(g) Smoke:** No smoke receipt exists. If produced, `status=SMOKE_NOT_MATRIX`; merge requires `status=COMPLETE`, so exclusion is by construction. The required smoke execution itself was not done.

- **(h) Timing:** No valid formal rehearsal exists. Development measurements are 4.292/128 = **0.03353125 s/catalogue-row**, with **>450 s/shared anchor** and 9.9–12.5 s provider construction per measured step. Because all 13 scientific arms share the catalogue, 450 s is not multiplied by 13: a-r0 is `4×90×>450/3600 = >45 core-hours`; ideal concurrency 20 gives `>2.25 h` wall. A naïve non-sharing calculation would be >585 core-hours, but contradicts the declared shared-catalogue design. The later unimplemented approximation target is about 11 s/shared anchor, or 1.1 core-hours.

## KAT debt

At least **15/151** tests are tautological: 13 of the prior audit’s 14 remain (only deadline fallback was genuinely rewritten), plus the self-derived matched-anchor identity and dry-run arm-list comparison. The stage-4 report’s implication that the requested tautology cleanup is complete is therefore unsupported.

## Standards

The code-review standards axis found no hard documented-standard violation and six judgment-call smells: misleading κ `_s` naming, primitive `field` strings, repeated object/array switches, duplicated scalar/batch solver logic with behavioral drift, provider access to `ScenarioDriver` internals, and the 2,700-line runner’s divergent responsibilities.

Review summary: Standards 0 hard/6 judgment findings; Spec 26 non-DONE items, with configuration-level C3 attribution and stale/deadline-incomplete selection behavior the worst failures.

VERDICT: STAGE4=NOT_READY:2,6-8,10-13,17-32,35-36 | DONE=10/36 | TAUTOLOGICAL_KATS=15 | AR0_PROJECTED_CORE_HOURS=>45.0