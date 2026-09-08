# Slice F — evaluation, estimand, statistics, splits, ladders (independent second opinion)

Auditor: Claude Opus 5, fresh context, 2026-09-08. Read-only; no git state changed. Paths absolute under
`/home/u24/papers/mcrl-leo-handover` (the local checkout; codex audited `/home/sat/mcrl-leo-handover-e1`).
Light Python used only to (a) re-derive world seeds, (b) replay the frozen episode-start sampler for the 9000-world
plan, (c) recompute the C3-S v1 endpoint from its 12 sealed unit receipts.

## 0. Verdict on the codex F-slice claims

| Codex claim | My verdict | Basis |
|---|---|---|
| Stage-C's first 100 worlds are an opened prior panel | **VERIFIED, severity downgraded** | Seeds identical, but the prior panel emitted one non-successor arm and no contrast (below, F3) |
| All evaluation is on TRAIN | **VERIFIED** | `world_plan:19`, runner `:80`, sampler admission `physical_runner.py:1229-1238` |
| Full world identity depends on a prefix-carried age stream | **VERIFIED and sharpened** | Stream is spawned from **world 1's** seed, not world k's: `physical_runner.py:1529-1531` |
| Strict pooled inequalities → only finite-panel single-seed comparisons | **VERIFIED** | `physical_runner.py:907-951`; one train seed at `DEVELOPMENT-CONTRACT:75` |
| Pooled weighting can reverse matched-episode results | **VERIFIED in principle, REFUTED in magnitude on the only real data** | C3-S: pooled +2.8832 % vs mean-of-ratios +2.8887 % (0.006 pp apart) |
| The all-neutral factorial cell is missing | **VERIFIED** | `DEVELOPMENT-CONTRACT:70` states it explicitly; no `ALL_NEUTRAL` token anywhere in `src/` or the runner |
| HELD/FALSIFIED is a deterministic gate without margin/uncertainty/replication | **VERIFIED and strengthened** | Gate is strict float `>`/`<`; the service clause is *provably vacuous* under saturation |
| C3-S contract is DRAFT/unsealed, no authenticated result possible | **REFUTED (stale)** | Contract is `-r--r--r--` with a matching `.sha256`; 12 unit receipts + terminal receipt exist locally and reproduce |
| Only four C3-S world clusters → a single favourable world could carry it | **REFUTED empirically** | 12/12 units positive, world-clustered (n=4, df=3) 95 % CI **[+2.26 %, +3.52 %]** |
| Verifier is provenance-only | **VERIFIED, with one correction** | It *does* reimplement pooling and the disposition (`verify…:218-311`), but recomputes no physics and imports the producer module (`:73`) |

## 1. Ranked assumption table

| # | Assumption | Implemented at | Docs | Standard practice | Distorts | Magnitude | Verdict |
|--:|---|---|---|---|---|---|---|
| F1 | The stage-C ladder can evidence "C1, C2 **and C3** each improve EE" | Arms fixed to 4 with no C3 route: `physical_runner.py:81,84`, `build_v023_c1c2_successor_world_plan.py:20` | The code's own ceiling string is `…_NO_C3_NO_TEST_NO_EFFICACY` (`physical_runner.py:89-92`) | A joint claim needs one common experiment | The claim has **no** common design: C1/C2 on a 10-step, 9000-world, `MCRL_V020_REPRICED_C3_GATE_V1` panel; C3 only on a 30-step, 4-world, `MCRL_V023_LCSRS_C3_OBSERVABILITY_V1` panel with a different base lineage family and an oracle-model coordinator | Structural | **FIX** |
| F2 | 9000 episodes are 9000 independent evaluation units | `ephemeris.py:421-427` (date index then time-of-day), `trainer_env.py:178` | Never stated | Cluster at the correlated unit; report design effect | Replayed: 9000 worlds land on **166 TLE dates**, 54.2/date (min 34, max 71); **75** worlds share an exact (date, epoch) with another world; rung-100 touches only **77/166** dates | Any i.i.d. episode interval is anticonservative; none is computed at all today | **FIX** |
| F3 | HELD/FALSIFIED is a statistical test | `physical_runner.py:907-951`; mirrored in `verify…:299-311` | Declaration `:117-129` | Margin + uncertainty + error control | Strict float `>`/`<`; ties in the last ulp decide; no null, no CI, no minimum effect | Unbounded | **FIX** |
| F4 | The `0.001` service clause protects service | `physical_runner.py:88,945-947` | Declaration `:117-119` | A non-inferiority margin must come from an operational loss | **Vacuous in practice**: C3-S served 35 971/36 000 in *all three* arms, bit-identical; service saturates at 100/100 on 352/360 BASE steps. It also never compares DROP to FULL2, so FULL2 may buy EE with up to 3 000 lost user-steps relative to a DROP arm and still pass | Clause carries ~0 information | **FIX** |
| F5 | DROP arms identify C1/C2 contributions | `physical_runner.py:488-493` (`neutral/informed` route mapping), `neutral-adapters/README.md:16-39` | `DEVELOPMENT-CONTRACT:65-70` | 2^k factorial + seed replication | Retrained equal-budget source ablations — **materially fair**, better than masking. But no `00` cell and one train seed ⇒ only *conditional* effects, no main effects, no interaction, no training-stochasticity estimate | High, unidentified | **DECLARE** |
| F6 | One train seed with identical epoch-0 bytes is adequate | `DEVELOPMENT-CONTRACT:73,75` | Declaration `:106` ("one lineage") | ≥3-5 seeds | Identical init across arms is **good** (common random numbers remove init variance from the contrast) but n=1 gives no sampling variance for that contrast | Cannot be bounded from the run | **FIX** |
| F7 | Pooled ratio-of-sums is the right estimand for attribution | `physical_runner.py:878-903` | Declaration `:115-116` says "the paired between-arm comparison uses the matched worlds" | Ratio-of-totals is a fine fleet estimand; attribution wants paired cluster effects | The declaration promises paired; the code computes **no paired statistic** — `_verify_matched_episode:2559-2572` only asserts equal world id and initial-state hash. Empirically the pooled/mean gap is 0.006 pp | Low numerically, high rhetorically | **FIX (free)** |
| F8 | Stage-C worlds are fresh and independent of learning | plan `:22,94,110`; prior panel `DROPC3-CONTRACT:37-40` | Successor declaration `:107-109` | An unopened panel, inventoried | Worlds 1-100 are byte-identical to the 2026-09-06 panel. **But** that panel ran one non-successor arm (`d40a0f30…`, `arms:["DROP_C3"]`, `between_arm_comparison_performed:false`) — no contrast was seen, so this is a disclosure defect, not selection bias. Source-training worlds are a **disjoint** seed family (`R7_WORLDS = 2026121801…2026121808`, fixtures `…-world-2026121708`), so no world-seed leak | 100/3000 = 3.3 % opened; 0 % seed collision with training | **DECLARE** |
| F9 | The 3000→9000 ladder replicates | `physical_runner.py:85,2295-2298,2496-2507`; addendum R2 `:29-30,92-97` | Declaration `:110-116` | Group-sequential or fixed panel | 3000 ⊂ 9000 and 3001-9000 runs **only after HELD**. The 9000 endpoint is a conditional extension of a panel selected for passing — never replication. Rungs 100/500/1500 do publish `pooled_by_arm` (`:2401-2413`) while only *stopping* is forbidden (R2 `:68-71`) | Systematic | **FIX** |
| F10 | World k is a standalone reproducible world | `step.py:527-535`; `physical_runner.py:1529-1534,1556-1566` | R2 `:34-38` (disclosed) | Reset streams derive from the episode's own domain | Segment ages are the k-th block of `integers(0,10,size=100)` from **one** stream spawned from `plan.worlds[0].world_seed`. World k cannot be replayed alone. Mitigating: the same stream is replayed identically for **every arm**, so the matched pairing on initial ages is preserved | Reproducibility only | **FIX (cheap)** |
| F11 | Ten-step reset episodes estimate continuing-system value | `physical_runner.py:86`; reset `step.py:504-540` | none | Burn-in / terminal value / horizon sensitivity | Cold reset + no terminal value; interacts directly with the segment-anchored renewal premium (see the EE-formula audit). C3-S already measures the interaction: EE advantage **+1.35 / +1.75 / +3.92 / +9.26 %** by dwell phase (`C3S-V1-RESULT-RECORD:Correction`) | Potentially dominant | **SENSITIVITY** |
| F12 | The verifier is scientifically independent | `verify_v023_c1c2_successor_stagec.py:73,218-311,900-918` | Declaration `:131-133` | Independent recomputation of observables | It reimplements pooling and disposition, but recomputes **no** `link_rate_bps` / `system_power_w`, and imports `v023_c1c2_successor_physical_runner` for policy loading and private readers | Shared physics bugs pass both | **DECLARE** |
| F13 | Block-alternating split licenses generalization | `ephemeris.py:183-303`, `:421-427` | `ephemeris.py:186-208` docstring | Embargo justified by measured autocorrelation; forward-time holdout for deployment | Nearest TRAIN/TEST dates are 2 calendar days; the "more than the ground-track repeat" claim (`:198-202`) has no measurement behind it. TEST is closed and must stay closed; every current result is TRAIN-development | Unknown | **DECLARE** |
| F14 | E1 → S0 → C3-S is confirmatory | E1 `E1-RESULT-RECORD`, S0 `PROBE-S0`, C3-S `C3S-V1-RESULT-RECORD` | E1/C3-S contracts disclose it | Adaptive development ≠ confirmation | S0 reuses the **opened** E1 panel (same 4 worlds, +1.81 % vs E1 ceiling +1.99/+2.22 %); C3-S uses 4 **fresh** worlds (`C3S_SCREEN/world/k`, verified disjoint from `C3_EXISTENCE_E1/world/k`) but was designed with S0 visible | Legitimate development, not confirmation | **DECLARE** |

## 2. Decisive evidence and known-answer tests

**F2 (new).** `EpisodeStartSampler.draw` (`ephemeris.py:421-427`) picks `available_dates[integers(0,166)]` then a second-of-day
floor-snapped to `DECISION_STEP_S = 30.08 s` (`constants.py:76`) — 2 873 slots/day, 476 918 (date, slot) pairs in TRAIN.
`_rngs(seed) = SeedSequence(seed).spawn(2)` (`run_v023_c1c2_successor_stage_c.py:43-47`) makes the epoch a pure function of
`world_seed = 2026090600 + k`, so I replayed all 9000 draws without touching the archive: **166/166 dates hit, 54.2 worlds/date,
75 exact epoch duplicates, 8 925 distinct epochs.** A hypothetical 9000-episode TRAIN training run shares **168** exact epochs
(theory 169.8) — i.e. ~1.9 % epoch overlap and 0 % world-seed overlap. So the TRAIN concern is *distributional*, not duplication.
**KAT:** episodes 1..9000 → date-index histogram must be multinomial(9000, 1/166); any interval that treats the 9000 as i.i.d.
must be compared against a date-clustered one on the same receipts. Expected design effect 1 + 53·ICC.

**F4 (new).** From the 12 sealed C3-S receipts I recomputed served counts: BASE = FULL = LITE = 35 971/36 000, exactly.
A margin that is satisfied by construction cannot falsify anything.
**KAT:** construct two arms whose served counts are equal and whose EE differ by 10 %; the service clause passes unchanged.
Replace it with a per-user floor plus outage run-length reporting.

**F7 (free fix).** `EpisodeReceipt` (`physical_runner.py:~700`) already persists `total_bits`, `total_energy_j`,
`served_user_steps`, `service_opportunities` **per episode per arm**. A paired world-level analysis therefore costs **zero
simulation** once the ladder has run. I demonstrated the whole pipeline on C3-S:

| statistic | FULL | LITE |
|---|---|---|
| pooled ratio-of-sums vs BASE | +2.8832 % | +2.9218 % |
| mean of per-unit ratios | +2.8887 % | +2.9297 % |
| per-unit sd (n=12) | 0.490 pp | 0.458 pp |
| sign count | 12/12 | 12/12 |
| world-clustered (n=4, df=3) 95 % CI | **[+2.26, +3.52] %** | **[+2.45, +3.41] %** |
| lineage-clustered (n=3, df=2) 95 % CI | [+2.36, +3.41] % | [+2.51, +3.35] % |
| naive n=12 t | 20.4 | 22.2 |

**F3.** **KAT:** `η_BASELINE = 100`, both drops `100 + 2⁻⁴⁰`, `FULL2 = 100 + 2⁻³⁹`, service equal → `HELD`. Conversely
`DROP_C1 = FULL2` exactly (a plausible outcome if C1 is inert) → `FALSIFIED` with no way to distinguish "no effect" from
"harmful effect".

**F5.** **KAT** (codex's, which I endorse): factorial EEs `EE₀₀₀=200, EE₀₁₁=EE₁₀₁=90, EE₁₁₁=101`. Both coded inequalities
report `101 > 90` and the ladder emits `HELD`, while each main effect is `−49.5`. Only the `000` cell exposes it.

**F10.** **KAT:** run world `2026090602` as episode 1 of a fresh root, then as episode 2. `world_seed`, mobility seed and keyed
field are unchanged; the initial segment ages — and `initial_world_sha256` — differ. Fix: spawn the age stream from
`world.world_seed`, not `plan.worlds[0].world_seed`.

**F11.** **KAT:** a policy that costs 1 J at step `H` and returns 10 bits·J⁻¹ at `H+1`. A 10-step endpoint prefers doing
nothing; an 11-step endpoint prefers the policy. Re-run the terminal rung at H ∈ {10, 20, 30} and report handovers-by-step,
especially the last two.

## 3. Code-vs-docs disagreements

1. **"Paired" is claimed, never computed.** Declaration `:115-116` promises a paired matched-world comparison; the
   implementation compares two pooled ratios and only *asserts* matching (`physical_runner.py:2559-2572`).
2. **"Independent verifier"** (Declaration `:131-133`) imports the producer module (`verify…:73`) and calls its private
   readers. Independent for pooling arithmetic; not independent for code provenance or physics.
3. **Ladder freshness.** Successor declaration `:107-109` says the world rule "extends the 2026-09-06 scheme"; it does not
   say the extension **starts inside** that scheme's opened 100 worlds.
4. **C3-S contract lifecycle.** The file is sealed (mode 0444, sidecar `1b19e0f4…` matches) yet its own line 3 still reads
   `狀態：DRAFT，尚未封存`. Same contradiction as the E1 contract. The E1/C3-S result records are otherwise consistent.
5. **Rung semantics.** R2 `:68-71` forbids "per-chunk scientific stopping" but rung files publish full `pooled_by_arm`
   (`physical_runner.py:2401-2413`), so the numbers are visible at 100/500/1500 and again before the 9000 continuation
   decision. Forbidding stopping does not blind the analyst.

## 4. The minimal design that would license "each of C1, C2, C3 improves pooled EE"

One experiment, six arms, five seeds, ~600 worlds, decision only at the terminal rung.

1. **One common panel.** Same worlds, same horizon, same keyed-fading component, same base learner family for all three
   components. C3 must enter as an arm of *this* design, not as a separate 4-world 30-step screen. Until it does, the joint
   claim is unsupportable regardless of statistics.
2. **Cells (6).** `FULL111`; `DROP_C1 (011)`; `DROP_C2 (101)`; `DROP_C3 (110)`; **`ALL_NEUTRAL (000)`**, retrained at equal
   budget; and the external `BASELINE` as a non-factorial reference. This one-factor-at-a-time knockout plus the null cell
   identifies each component's contribution *conditional on the other two present*, plus the joint effect of all three.
   Interactions stay unidentified — **declare that**, or escalate to the full 2³ = 8 cells (+33 % cost).
3. **Training seeds: 5 per arm.** Keep common random numbers (identical epoch-0 bytes across arms within a seed) so the
   contrast is paired at the initialization; vary the seed across the 5 replicates. Five all-positive seeds give a
   distribution-free one-sided sign p = 0.031 and a t-interval with df = 4. Three seeds (df = 2, |t|crit = 4.303) is the
   absolute floor and I would not defend it.
4. **World clusters: ~600 worlds per (arm, seed), clustered by TLE date.** 600 uniform draws cover ≈161 of the 166 TRAIN
   dates at ≈3.7 worlds/date — enough clusters for a well-behaved cluster-robust interval (the usual ≥30-40 cluster rule),
   and re-sizeable from the pilot rung's observed per-world sd. Fix the age stream per world (F10) first so worlds are
   exchangeable units.
5. **Paired world-level uncertainty.** Primary: pooled ratio-of-sums (keep it as the declared fleet estimand) with a
   **date-clustered bootstrap CI on the ratio itself** (10 000 resamples over dates). Secondary and mandatory:
   per-world paired `Δ_w = log EE_arm,w − log EE_ref,w`, date-clustered; the seed-level mean of `Δ` with its df = 4 interval;
   the sign count; and the numerator/denominator decomposition (Δbits, ΔJ) so a "gain" that is pure energy reduction is
   visible. All of this is computable from the existing `EpisodeReceipt` fields — **zero extra simulation**.
6. **Effect margin: δ = +0.5 pp of relative EE**, prespecified. Claim a component only if the lower cluster-bootstrap
   confidence bound exceeds δ **in every seed's direction** and the seed-level interval excludes δ. Replace the 0.001 served
   fraction with an operational criterion (per-user served floor + outage run-length tail), since the aggregate margin is
   demonstrably non-binding.
7. **Ladder discipline.** Rungs 100/500/1500 are **integrity-only**: they must not publish `pooled_by_arm` in the open, and
   the analyst must be blind to EE until the terminal rung. The decision is taken once, at the terminal rung, on a panel size
   fixed in advance. Drop the "continue to 9000 iff HELD at 3000" rule — nested conditional continuation is not replication.
   If a genuine sequential design is wanted, use an alpha-spending boundary or an anytime-valid confidence sequence so that
   looking is licensed, and say so before the run.
8. **Also required, cheap:** record the episode epoch (date + snapped second) in every receipt so date-clustered inference is
   possible from the sealed artifacts alone; today the date is recoverable only by replaying `_rngs`.

## 5. Cost multiplier

Measured basis (R2 `:99-101`): learned arm 13.6 s/episode, BASELINE 1.66 s/episode.
Current single-seed ladder — 3 learned + BASELINE × 3000 = **35.4 CPU-h**; the planned 9000 continuation = **106.2 CPU-h**.

| Design | Evaluation compute | vs 3000-rung | vs 9000 plan |
|---|---|---|---|
| Minimal design, C3 as a **learned head** (5 learned arms × 5 seeds × 600 worlds + one BASELINE pass) | **≈ 57 CPU-h** | **1.6×** | **0.54×** |
| Same, C3 as the **C3-S set-level coordinator** at its instrumentation-free 14.9 s/decision (3 of 5 arms carry C3) | ≈ 395 CPU-h | ≈ 11× | ≈ 3.7× |
| Full 2³ factorial variant (8 cells instead of 5, learned head) | ≈ 91 CPU-h | 2.6× | 0.86× |

Headline: **if C3 is a learned head, the statistically defensible design costs 1.6× the current 3000-episode rung and only
0.54× the 9000-world single-seed ladder already planned.** Replication buys more than panel size does; the current plan
spends its budget on the axis with the least inferential return. The 11× row is the real cost driver and makes the C3-S
latency work a *statistical* prerequisite, not an engineering nicety. Excluded above: source-row generation for a C3 route
(one-off, ~21-47 CPU-h at the r8 shard rate, and currently blocked by `STOP_PHYSICS_R7`); source training itself
(~1.25 s/epoch for three arms) is negligible even at 5 seeds × 5 arms.

## 6. The three assumptions I would overturn first

1. **"The stage-C ladder is evidence for the C1/C2/C3 claim."** It has no C3 arm at all — its own claim ceiling string is
   `TRAIN_DEVELOPMENT_..._NO_C3_NO_TEST_NO_EFFICACY` — and C3's only positive result lives on an incommensurable panel
   (30 vs 10 steps, 4 vs 9000 worlds, a different keyed-fading component, a different base lineage family, an oracle-model
   coordinator instead of a learned head). Two of the three components have no experiment in common with the third.
2. **"9000 episodes are 9000 independent units."** Replaying the frozen sampler shows they are 9000 draws over **166 TLE
   dates** (54.2/date, 75 exact epoch duplicates, rung-100 touching only 77 dates). The independent unit is the date. No
   uncertainty statement of any kind is currently computed, and the obvious per-episode one would be anticonservative.
3. **"HELD/FALSIFIED plus the service clause is a test."** The EE part is a strict float inequality with no margin; the
   service clause is vacuous under saturation (C3-S: 35 971/36 000 identical in all three arms) and never compares DROP to
   FULL2; rungs publish EE while only *stopping* is forbidden; and 3001-9000 runs only after HELD, so the larger panel is a
   conditional extension of a panel selected for passing, never a replication.
