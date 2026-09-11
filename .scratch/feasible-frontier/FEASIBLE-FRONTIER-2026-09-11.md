**No — the trained policy `e6b063ef…` is not on the Pareto frontier: the non-learned rule `A m=12dB` (hold the incumbent unless the best legal challenger's nominal gain beats it by 12 dB) has both a lower handover rate (0.2258 vs 0.2796) and a higher pooled EE (101,467,361.95 vs 93,137,893.02 bit/J, +8.9%), and it still dominates on both axes when re-run at n = 48 (handover −16.9 sem, pooled EE +6.7 sem).**

Date: 2026-09-11. FEASFRONT. Read-only plus scripted rollouts: **no training, no `update()` call, no gradient step, no optimizer touched.** The trained arm loads `artifacts/training-2026-08-25-rerun01/main/final-checkpoint.pt` read-only (sha256 `e6b063ef…1b09c28b`, checked in the previous round). `src/` was not edited or import-time patched. At most two python processes, `nice -n 16`, BLAS/OMP threads 1.

Evidence class per claim: **[V]** = I ran it or opened the file this session; **[I]** = inferred; **[D]** = arithmetic derived from [V] numbers.

---

## 1. Answer to the four questions

**1. Is the trained policy on the Pareto frontier of this set?** **No.** Two arms satisfy *both* handover rate ≤ 0.2796 *and* pooled EE ≥ 93,137,893.02:

| Arm | handover rate | pooled EE (bit/J) | vs declared trained EE | n |
|---|---:|---:|---:|---:|
| **`A m=12dB`** | **0.2258** | **101,467,361.95** | **+8.94%** | 24 |
| `A m=12dB` (re-run) | 0.2257 ± 0.0017 | 100,974,420.05 | +8.41% | 48 |
| **`A m=9dB`** | **0.2753** | **105,701,579.47** | **+13.49%** | 24 |
| `A m=9dB` (re-run) | 0.2762 ± 0.0021 | 105,478,123.93 | +13.25% | 48 |

`A m=12dB` is the one that carries the headline. `A m=9dB` dominates on point estimates, but its handover edge is thin, so I re-ran it at larger n (§4). At n = 48 its handover rate is 0.0040 below the trained policy's, which is −1.1 sem, so **on handover rate it is a statistical tie. It is not a resolvable improvement.** Its EE lead is +12.9 sem. `A m=12dB`'s handover edge is −0.0545 (−16.9 sem) and its EE edge +6.7 sem, so it dominates on both axes with room to spare. **[V]**

**2. Best pooled EE at or below the trained policy's handover rate.** The question assumed the answer would sit below the trained policy. It sits above. `A m=9dB` gives **105,701,579.47 bit/J at handover 0.2753**, which is **+12,563,686 bit/J (+13.49%) above** the trained policy. It is not below it. If you require a handover rate that is resolvably lower rather than tied, the answer is `A m=12dB`: **101,467,361.95 bit/J at 0.2258, +8.94%**. **[V, D]**

**3. Handover rate of the cheapest arm that matches or beats the trained policy's pooled EE.** This one also points the other way. The lowest-handover arm with pooled EE ≥ 93,137,893.02 is `A m=12dB` at **0.2258**, which is **0.0538 lower than 0.2796 (−19.2%)**. It is not higher. Matching the learner's EE costs no extra handovers at all. Across this set, the learner's EE comes with 24% *more* handovers than a rule needs to reach it. **[V, D]**

**4. The frontier, at every operating point**: §3 below.

---

## 2. What was run

**Harness: reused, not rebuilt.** I used the previous round's `anchor_ablation.py` pattern verbatim, from `.scratch/catfish-surface/CATFISH-ATTACHMENT-SURFACE-2026-09-11.md` §"Segment-anchor ablation". **[V]**

- **Estimand.** Pooled EE = (Σ over all steps of `system_throughput_bps · dt`) / (Σ over all steps of `system_consumed_power_w · dt`). These are two running totals over 24 episodes × 10 steps, divided **once**. `dt = DECISION_STEP_S = 30.08 s`. Both per-step quantities are the environment's own values, read from `env.last_outcome.energy` (`SystemEnergyEfficiency`, `runtime/energy_efficiency.py:37-49`). I did not reconstruct them.
- **Seeds.** `train_seed=42, env_seed=1337, mobility_seed=7`, the frozen run's seeds. Every arm uses the same 24 episodes at the same stream positions.
- **Fresh env per cell.** `_age_rng` spawns once and carries across episodes (`env/step.py:534-536`), so every cell builds its own environment. The env goes through `DiagnosticStepEnvironment.construct(..., physics_override="none")`, the wrapper the previous round showed to be transparent.
- **Handover split.** `r2_handover == −φ1 = −0.5` means **same satellite, different cell**. `r2_handover == −φ2 = −1.0` means **satellite change**, and that includes re-entry after an outage (`action_contract.py:422-457`). The script fails loudly on any other value. None appeared.
- **Mean active beams.** `energy.eff_beams` ("beams radiating this step, active ⟺ positive load"), averaged over steps.
- **Calibrated scalar.** The trained objective `Σ ωⱼ·rⱼ/cⱼ` with `(0.5, 0.3, 0.2)` and `(2029238.4328742754, 1.0, 6.0)`. The accumulation (`r/U` per episode, then the mean over episodes) is identical to the previous round's, so the numbers compare directly with its +0.9063 / −0.0867.

Scripts are in the session scratchpad: `frontier.py` (arms), `frontier.out` (n = 24 raw output), `confirm48.out` (n = 48 re-run). Wall time was 1457 s for the 16 cells and 506 s for the 3-cell re-run. **[V]**

### Arm definitions, as run

Every rule reads only the 112-dim observation at decision time: block 1 `access` (the incumbent's slot), block 2 `channel_quality` (per-candidate nominal SINR with previous-step interference), and block 4 `beam_loads` (`N_u(t−1)`). None uses realised current-step fading, future state, or another user's current-step choice. **All of them are realizable from the observation alone.** **[V]**

| Arm | Rule |
|---|---|
| `A m=X dB` | Let `best` = the legal option with maximum nominal gain. If the incumbent is legal, **hold it unless `gain[best] > gain[inc] · 10^(X/10)`**. If the incumbent is illegal or has left the candidate table, take `best`. At `m = 0` there is no incumbent preference, so it is **exactly** `MAX_NOMINAL_GAIN`, the unrestricted Family D anchor. |
| `B1_NO_NEW_BEAM` | Max gain among legal options whose beam carried demand last step (`beam_loads > 0`), so the choice lights no new beam. If none exists, fall back to unrestricted max gain. |
| `B2_PREFER_SHARED` | Max gain among legal options whose occupancy **excluding this user** is non-zero (`load − 1` at the incumbent slot, `load` elsewhere). If none exists, use B1's set. If that is empty too, use unrestricted. |
| `C1_SAT_LOCK` | Max gain restricted to the incumbent's satellite (`a // 7 == inc // 7`). Beam changes are allowed. If there is no incumbent, the choice is unrestricted. |
| `C2_SAT_LOCK_3DB` | C1's restriction plus the Family A hold at 3 dB. |
| `D_HOLD_WHILE_LEGAL` | Hold the incumbent whenever it is legal. Otherwise take max gain. |
| `RANDOM_MASKED` | `select_actions(..., ε=1.0)`, the harness check. |
| `TRAINED e6b063ef` | `select_actions(..., ε=0.0)`, the deployed greedy policy. |

**One implementation defect, caught in the smoke test and fixed before the counted run. [V]** My first `pick()` had every rule fall back to the incumbent whenever no allowed challenger beat it, even when the family restriction had excluded the incumbent. At `m = 0` that made B1 and B2 produce **identical** actions. Their 1-episode smoke outputs were identical to 7 significant figures, which is how I found it: B2's only difference from B1 is excluding a lone incumbent, and the fallback undid that exclusion. The fix was to make `m = 0` a plain restricted argmax with no incumbent preference, so restrictions are never undone. After the fix, B1 and B2 differ in the smoke test (ho 0.376 vs 0.486). No counted cell was run under the defective version.

---

## 3. The frontier table (n = 24, frozen seeds, fresh env per cell)

Sorted by handover rate. **FRONTIER** = no other arm has both handover ≤ and EE ≥ with at least one strict. **[V]** for measured columns, **[D]** for the last two.

| Arm | pooled bits | pooled joules | **pooled EE (bit/J)** | EE sem | **ho rate** | same-sat (φ1) | sat-change (φ2) | served | mean active beams | calibrated scalar | vs trained EE | status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `D_HOLD_WHILE_LEGAL` | 2.492815e+14 | 3.232088e+06 | 77,127,064.84 | 686,853 | **0.1427** | 0.0000 | 0.1427 | 0.9970 | 70.72 | +0.8371 | −17.2% | **FRONTIER** |
| **`A m=12dB`** | 3.367776e+14 | 3.319073e+06 | **101,467,361.95** | 934,201 | **0.2258** | 0.0010 | 0.2248 | 0.9964 | 72.48 | **+1.2232** | **+9.0%** | **FRONTIER** |
| **`A m=9dB`** | 3.355155e+14 | 3.174177e+06 | **105,701,579.47** | 621,024 | **0.2753** | 0.0052 | 0.2701 | 0.9987 | 69.21 | **+1.1309** | **+13.5%** | **FRONTIER** |
| ***`TRAINED e6b063ef`*** | 2.848622e+14 | 3.059385e+06 | ***93,110,907.97*** | 902,313 | ***0.2799*** | 0.0556 | 0.2243 | 0.9988 | 67.90 | ***+0.9033*** | — | *dominated by A m=9, A m=12* |
| `C2_SAT_LOCK_3DB` | 2.518928e+14 | 2.876703e+06 | 87,563,020.49 | 676,193 | 0.3068 | 0.1642 | 0.1426 | 0.9974 | 62.59 | +0.6405 | −6.0% | dominated |
| `A m=6dB` | 3.378691e+14 | 3.038839e+06 | 111,183,610.19 | 992,004 | 0.3643 | 0.0145 | 0.3498 | 0.9972 | 66.13 | +0.9538 | +19.4% | **FRONTIER** |
| `B1_NO_NEW_BEAM` | 1.816921e+14 | 1.755908e+06 | 103,474,767.67 | 405,143 | 0.4250 | 0.0744 | 0.3506 | 0.9978 | **37.86** | −0.3665 | +11.1% | dominated |
| `A m=4dB` | 3.303055e+14 | 2.946374e+06 | 112,105,740.75 | 1,088,001 | 0.4655 | 0.0239 | 0.4416 | 0.9970 | 64.16 | +0.6286 | +20.4% | **FRONTIER** |
| `B2_PREFER_SHARED` | 1.814005e+14 | 1.748332e+06 | 103,756,292.71 | 563,411 | 0.4849 | 0.0917 | 0.3931 | 0.9979 | **37.87** | −0.5124 | +11.4% | dominated |
| `C1_SAT_LOCK` | 2.406993e+14 | 2.758802e+06 | 87,247,763.92 | 694,306 | 0.5054 | 0.3636 | 0.1418 | 0.9981 | 59.77 | +0.2283 | −6.3% | dominated |
| `A m=3dB` | 3.310872e+14 | 2.945774e+06 | 112,393,947.90 | 980,252 | 0.5185 | 0.0264 | 0.4921 | 0.9978 | 64.13 | +0.4835 | +20.7% | **FRONTIER** |
| `A m=2dB` | 3.282673e+14 | 2.918995e+06 | **112,459,003.43** | 801,796 | 0.5860 | 0.0362 | 0.5497 | 0.9982 | 63.51 | +0.2845 | **+20.8%** | **FRONTIER** (max EE) |
| `A m=1dB` | 3.242342e+14 | 2.916785e+06 | 111,161,514.48 | 1,173,322 | 0.6613 | 0.0463 | 0.6150 | 0.9982 | 63.43 | +0.0328 | +19.4% | dominated |
| `A m=0.5dB` | 3.238183e+14 | 2.913353e+06 | 111,149,682.54 | 1,028,321 | 0.6820 | 0.0541 | 0.6279 | 0.9985 | 63.38 | −0.0197 | +19.4% | dominated |
| `A m=0dB` = `MAX_NOMINAL_GAIN` | 3.266731e+14 | 2.929683e+06 | 111,504,571.39 | 1,095,687 | 0.7120 | 0.0573 | 0.6546 | 0.9981 | 63.72 | −0.0885 | +19.8% | dominated |
| `RANDOM_MASKED` | 1.842866e+14 | 3.473162e+06 | 53,060,175.56 | 394,444 | 0.8680 | 0.1836 | 0.6844 | 0.9360 | 76.64 | −1.4104 | −43.0% | dominated |

**The Pareto frontier of this set** is `D_HOLD_WHILE_LEGAL` → `A m=12` → `A m=9` → `A m=6` → `A m=4` → `A m=3` → `A m=2`. Apart from the hold-everything anchor at the very low-handover end, every frontier point is a Family A hysteresis rule. **[D]**

### The room between the rules and the learner, at every operating point

For each handover budget: the best pooled EE any rule reaches within it, compared with the learner. **[D]**

| handover budget | best rule within budget | its pooled EE | learner (0.2799, 93.11 M) |
|---:|---|---:|---|
| ≤ 0.15 | `D_HOLD_WHILE_LEGAL` | 77.13 M | learner out of budget |
| ≤ 0.23 | `A m=12dB` | 101.47 M | learner out of budget, and the rule beats it anyway |
| **≤ 0.2796 (the learner's own)** | **`A m=9dB`** | **105.70 M** | **learner 11.9% below the frontier at its own handover rate** |
| ≤ 0.37 | `A m=6dB` | 111.18 M | learner 16.3% below |
| ≤ 0.47 | `A m=4dB` | 112.11 M | learner 16.9% below |
| ≤ 0.59 | `A m=2dB` | 112.46 M | learner 17.2% below |
| unbounded | `A m=2dB` | 112.46 M | learner 17.2% below |

At no handover budget does the learner sit on or above the frontier. **There is no operating point in this set where the learner occupies ground a rule cannot reach.** The frontier is also nearly flat from handover 0.36 to 0.71 (111.2–112.5 M). Hysteresis between 2 and 6 dB removes up to 49% of `MAX_NOMINAL_GAIN`'s handovers (0.7120 → 0.3643) for at most a 0.3% EE change (`A m=6` is −0.29% vs `m=0`; `A m=2` is +0.86%). **[D]**

---

## 4. Placebo, positive control, and the one re-run

**Placebo: three arms reproduce known figures bit-for-bit. [V]**

| Arm | this run | previous round (fresh env, same wrapper) | delta |
|---|---:|---:|---|
| `RANDOM_MASKED` | 53,060,175.561473 | 53,060,175.561473 | **bit-identical** |
| `A m=0dB` (= `MAX_NOMINAL_GAIN`) | 111,504,571.388934 | 111,504,571.39 | **bit-identical** (same handover 0.7120) |
| `TRAINED e6b063ef` | 93,110,907.973748 | 93,110,907.97 | **bit-identical** (same handover 0.2799) |

So the harness is the previous round's harness, and `A m=0` is exactly the `MAX_NOMINAL_GAIN` anchor. The 0.03% gap to the brief's declared reference values (93,137,893.02 / 0.2796) is the `_age_rng` shared-env confound the previous round disclosed. Those values come from its shared-env run, and these come from fresh envs. I answer the questions against the brief's declared numbers, and no conclusion changes if the fresh-env numbers are used instead.

**Positive control, built into the grid. [V]** The hysteresis sweep should push the handover rate down monotonically as `m` rises, with φ1 (same-satellite) handovers dying first because intra-satellite neighbours differ by small gain margins. It does both. Total handovers fall 0.7120 → 0.6820 → 0.6613 → 0.5860 → 0.5185 → 0.4655 → 0.3643 → 0.2753 → 0.2258, strictly monotone over all nine margins. φ1 falls 0.0573 → 0.0010. `D_HOLD_WHILE_LEGAL` has φ1 = 0.0000 exactly, as it must: it only moves when the incumbent becomes illegal. So the rules do what their definitions say.

**The one re-run, and why.** The `A m=9dB` result did not surprise me. Its handover margin over the learner (0.2753 vs 0.2799) was small enough that I would not state dominance on n = 24 alone. Per the brief's discipline, I re-ran `A m=9dB`, `A m=12dB` and `TRAINED` at **n = 48**. These are the same seeds, episodes 0–47, which is a superset of the original 24. I added per-episode handover-rate sems, which the first pass did not record. **I am reporting the re-run. It weakens `A m=9dB` and leaves `A m=12dB` intact. [V]**

| Arm (n = 48) | pooled bits | pooled joules | pooled EE | EE sem | ho rate ± sem | φ1 | φ2 | served | beams | scalar |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `A m=9dB` | 6.731476e+14 | 6.381870e+06 | 105,478,123.93 | 485,738 | 0.2762 ± 0.00213 | 0.0052 | 0.2710 | 0.9981 | 69.59 | +1.1271 |
| `A m=12dB` | 6.685911e+14 | 6.621391e+06 | 100,974,420.05 | 763,506 | 0.2257 ± 0.00169 | 0.0010 | 0.2247 | 0.9973 | 72.37 | +1.2101 |
| `TRAINED e6b063ef` | 5.683132e+14 | 6.059553e+06 | 93,787,980.20 | 760,950 | 0.2802 ± 0.00275 | 0.0559 | 0.2243 | 0.9985 | 67.20 | +0.9167 |

| comparison (n = 48, unpaired) | EE ratio | EE gap | handover gap |
|---|---:|---:|---:|
| `A m=9dB` − TRAINED | 1.1246 | **+12.9 sem** | −0.0040, **−1.1 sem (tie)** |
| `A m=12dB` − TRAINED | 1.0766 | **+6.7 sem** | −0.0545, **−16.9 sem** |

Both comparisons are unpaired. The arms share seeds and episodes, so a paired test would be tighter still. The unpaired figures already settle the question for `A m=12dB`, and I did not add a paired test.

---

## 5. What else the table says

1. **The frontier is carried by bits, not joules.** `A m=12dB` delivers 3.37e+14 bits against the learner's 2.85e+14 (1.182×) and spends *more* joules (3.32e+06 vs 3.06e+06, 1.085×). It wins on the numerator and loses on the denominator. Its mean active beams (72.5) are *higher* than the learner's (67.9). This is the same mechanism the previous round isolated: pointing each user at its highest-gain legal beam buys throughput. Hysteresis keeps that throughput while cutting the churn. **[V, D]**

2. **Consolidation (Family B) is a different operating point, not a better one.** B1/B2 light roughly **38 beams against 64–72** for everything else, and they halve both halves of the ratio: bits 1.82e+14 (0.64× the learner), joules 1.76e+06 (0.57×). Pooled EE comes out at 103.5–103.8 M (+11%) with served still 0.998. Users are packed onto fewer beams, and per-user rate falls through the `Bʷ/U` bandwidth split (eq. 3.14). Served users stay served, but each gets less. Both B arms are dominated by `A m=9dB` because they hand over far more (0.43–0.48). The joules saving from not lighting beams is real (the +6.267 W/beam motivation holds in the direction stated). Here it is bought with bits, not free. **[V, D]**

3. **Satellite lock (Family C) is worse on EE than unrestricted choice, and does not buy the handover reduction you would expect.** Locking the satellite cuts φ2 to 0.142 but inflates φ1 to 0.364 (C1), because users hop between cells on a satellite whose beams are drifting away. Pooled EE falls to 87.2–87.6 M (−6%). C2's 3 dB hold recovers some of the φ1 (0.164) but not the EE. Both are dominated. **[V]**

4. **The hysteresis rules also beat the learner on the learner's own training objective.** This goes beyond the brief's question, but it bears directly on it. The calibrated scalar is `A m=12dB` **+1.2232**, `A m=9dB` +1.1309, `A m=6dB` +0.9538, against `TRAINED` **+0.9033**, at the same seeds and stream positions. At n = 48 the figures are +1.2101 / +1.1271 vs +0.9167. **[V]** I did not instrument the per-episode scalar sem in this run. The previous round's per-episode scalar sems at n = 24 were 0.019–0.043 for comparable arms, and the gap here is 0.32. I give that as scale, not as a test. **This contradicts the verdict of the catfish-surface report's §"Scalarized-objective demonstrator"**: *"there is **no** better-than-learner source for the objective the learner is trained on"*. That search covered **myopic** rules (additive rate-vs-handover scores with one swept κ), and its best arm reached +0.8750. Hysteresis is still observation-only: the incumbent is in block 1 and the gain in block 2. It is a *multiplicative* gain-ratio hold rather than an additive rate trade, and it lies outside what that search covered. That verdict should now be read as scoped to myopic additive rules. It does not hold for expressible rules in general. **[V for the numbers; I for why the earlier search missed it]**

---

## 6. What this does and does not establish

**Established [V]:**
- On this harness, at these 24 (and 48) episodes and these seeds, a one-parameter observation-only hysteresis rule has a higher pooled EE than the trained checkpoint **at a lower handover rate, resolvably on both axes** (`A m=12dB`). It also has a higher calibrated training-objective scalar.
- The learner lies strictly inside the frontier of this set at every handover budget. At its own handover rate, the frontier is 11.9% above it (`A m=9dB`).
- Both harness placebos and the `m=0` anchor reproduce the previous round bit-for-bit.

**The implication for the design, stated as the brief asked, without softening:** the demonstration-RL design rests on the learner occupying ground no simple rule reaches: high EE at a low handover rate. **It does not occupy that ground.** A rule with one memory bit (the incumbent) and one threshold reaches higher EE at a lower handover rate. A demonstration-stimulated learner would first have to beat `A m=12dB` / `A m=9dB`, not `MAX_NOMINAL_GAIN`, before it had a demonstrated job. On this evidence that design direction is closed as currently framed. **[I, from the [V] table]**

**Not established:**
- Anything outside this set. The grid was declared before the run and I did not extend it: no margins above 12 dB, no margins between grid points, no combinations of families. I also did not look for the best hysteresis margin. The frontier here is the frontier *of this set*. A finer grid could only move it up, never down, so the dominance finding cannot be undone by grid resolution. **[I]**
- Robustness to other seeds, other user counts, or other physics (for example `ablate_anchor`). Everything here is anchored physics at `users=100`.
- Whether a *differently trained* learner (different objective weights, a pooled-EE reward) would sit on the frontier. This is one checkpoint.
- A paired statistical test. All sems are unpaired per-episode.

---

## Evidence classification

**Verified by running code, this session, read-only, no gradient step:** the 16-cell n = 24 panel (`frontier.out`), the 3-cell n = 48 re-run (`confirm48.out`), the 1-episode smoke tests (including the B1 = B2 defect and its fix), and the three bit-identical placebo reproductions.

**Verified by reading local source:** `runtime/energy_efficiency.py:37-49` (`eff_beams`, `served`); `env/action_contract.py:400-457` (`PHI1`/`PHI2`, `classify_handover`, re-entry charged φ2); `runtime/state_encoding.py` (block order `[access, snr, theta, loads]`); `algorithms/modqn.py:858-875` (`load_checkpoint` does not touch the RNG streams).

**Reused without re-verification:** the checkpoint sha256 and the `DiagnosticStepEnvironment` override's provenance and sha256, both verified in the previous round.

---

## JSRL guide-horizon coverage sweep

**Coverage is not flat in `h`, but it does not rise with `h` either. Every guide prefix `h ≥ 1` hands the learner states well outside its own reach: the novelty ratio is 1.39–2.20 against 1.00 at `h = 0`, and 28–74% of handed states lie beyond the learner's own 95th-percentile spread, against 5%. That happens as a single step at `h = 1`, after which coverage oscillates with no upward trend and the tail share *falls* (0.74 at `h = 2` → 0.28–0.42 for `h ≥ 4`). So the declared kill condition "flat" does not fire, and the declared survive condition "rises" is met only in the step sense.**

Added 2026-09-11 on the coordinator's instruction, after the frontier arms were complete and reported above. Same harness, same 24 episodes, same frozen seeds (42/1337/7), fresh env per cell. **No `update()` call, no gradient step.** The learner loads the frozen checkpoint read-only. Scripts are in the session scratchpad: `jsrl.py` (sweep), `jsrl.out` (raw), `jsrl_blocks.py` / `jsrl_blocks.out` (audit of the measure). Wall time 1019 s. **[V unless marked]**

### Design

For `h ∈ {0, 1, …, 10}`, `MAX_NOMINAL_GAIN` (the `A m=0` rule above, same code path) acts for steps `0 … h−1`. The trained `e6b063ef…` then acts greedily (ε = 0) for steps `h … 9`. `h = 0` is the learner alone and `h = 10` the guide alone. The checkpoint is loaded in every cell. `load_checkpoint` does not touch the RNG streams (`modqn.py:858-875`), so every cell sits at the same env stream positions. The grid is the declared eleven cells. I added none.

### Coverage measure, declared before the run (verbatim from the `jsrl.py` docstring, written before launch)

- **Handover states at `h`**: the 24 × 100 = 2400 per-user 112-dim encoded observations at step index `h`, i.e. exactly what the learner is handed.
- **Reference pool at `h`**: the 2400 encoded observations at the **same step index `h`** from the `h = 0` rollout. These are states the learner reaches on its own.
- Both are z-scored per dimension on the `h = 0` rollout's own mean and sd, pooled over all step indices (24,000 rows; 5 constant dimensions get sd = 1). Units therefore do not decide the metric.
- `d(h)` = mean Euclidean 1-NN distance from the handover states to the reference pool. `d0(h)` = mean **leave-one-out** 1-NN distance within the reference pool itself, i.e. how far apart the learner's own states are. Pool sizes are matched (2400 vs 2399).
- **`R(h) = d(h) / d0(h)`**, the novelty ratio. It is 1 at `h = 0` by construction.
- **`out95(h)`** = the fraction of handover states whose 1-NN distance exceeds the 95th percentile of the leave-one-out distribution. It is 0.05 at `h = 0` by construction.

**Limitations, declared with it:** (i) the encoding is a user-relative candidate ordering, so this is **observation-space** novelty (what the network sees), not physical-state novelty. (ii) 1-NN in 112 dimensions over 2400 points is sparse, so absolute distances mean nothing and only the ratio to the learner's own spread is read. (iii) the reference is one 24-episode rollout, not the learner's whole reachable set, so the pool under-covers. That biases R upward, but equally for the yardstick `d0` and the query `d`, because the pool sizes are matched.

### Results per `h` (n = 24 each)

| `h` | pooled bits | pooled joules | **pooled EE (bit/J)** | EE sem | ho rate | same-sat φ1 | sat-change φ2 | served | beams | scalar | **R(h)** | **out95(h)** |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 2.848622e+14 | 3.059385e+06 | 93,110,907.97 | 902,313 | 0.2799 | 0.0556 | 0.2243 | 0.9988 | 67.90 | +0.9033 | 1.0000 | 0.0500 |
| 1 | 3.111162e+14 | 3.271451e+06 | 95,100,368.03 | 1,057,755 | 0.2700 | 0.0418 | 0.2281 | 0.9963 | 72.18 | **+1.0270** | 1.5981 | 0.6567 |
| 2 | 3.080530e+14 | 3.126405e+06 | 98,532,664.68 | 1,247,164 | 0.3520 | 0.0498 | 0.3021 | 0.9967 | 70.05 | +0.8435 | **2.2025** | **0.7417** |
| 3 | 3.078087e+14 | 3.089456e+06 | 99,632,009.68 | 1,027,432 | 0.4267 | 0.0583 | 0.3683 | 0.9977 | 69.16 | +0.6357 | 2.0397 | 0.7358 |
| 4 | 3.083716e+14 | 3.057799e+06 | 100,847,574.63 | 1,303,673 | 0.4883 | 0.0694 | 0.4189 | 0.9970 | 68.24 | +0.4567 | 1.3979 | 0.3983 |
| 5 | 3.142595e+14 | 3.067883e+06 | 102,435,299.98 | 1,379,390 | 0.4607 | 0.0445 | 0.4161 | 0.9978 | 67.98 | +0.5380 | 1.4549 | 0.2846 |
| 6 | 3.116768e+14 | 3.024043e+06 | 103,066,272.67 | 1,342,989 | 0.5366 | 0.0550 | 0.4816 | 0.9981 | 66.69 | +0.3229 | 1.9346 | 0.3013 |
| 7 | 3.067107e+14 | 2.957484e+06 | 103,706,613.23 | 1,053,361 | 0.6167 | 0.0723 | 0.5444 | 0.9992 | 64.80 | +0.0860 | 2.0255 | 0.3787 |
| 8 | 3.170671e+14 | 2.942086e+06 | 107,769,494.41 | 1,036,017 | 0.6591 | 0.0733 | 0.5857 | 0.9975 | 64.18 | +0.0147 | 1.3853 | 0.4179 |
| 9 | 3.273152e+14 | 2.958438e+06 | 110,637,828.39 | 1,112,387 | 0.6465 | 0.0565 | 0.5900 | 0.9980 | 64.42 | +0.0958 | 1.4650 | 0.3604 |
| 10 | 3.266731e+14 | 2.929683e+06 | 111,504,571.39 | 1,095,687 | 0.7120 | 0.0573 | 0.6546 | 0.9981 | 63.72 | −0.0885 | n/a | n/a |

At `h = 10` the learner is never handed a state, so coverage is undefined there.

### Built-in placebo: both ends reproduce **bit-for-bit** [V]

- `h = 0`: **93,110,907.973748**, handover 0.2799. This is bit-identical to the frontier table's `TRAINED e6b063ef` cell.
- `h = 10`: **111,504,571.388934**, handover 0.7120. This is bit-identical to the frontier table's `A m=0dB` = `MAX_NOMINAL_GAIN` cell.
- Determinism: I re-ran all eleven cells once more to dump states for the audit below. The EE, handover and coverage lines are **identical** to the first run (`diff` of the two outputs is empty). The re-run exists only to instrument the measure. It replaces no number.

### Reading against the kill rule, as declared

- **"Coverage flat in `h`" → kill.** **Not met.** Coverage is 1.00 / 0.05 at `h = 0` and at least 1.39 / 0.28 at every `h ≥ 1`. The guide does hand the learner states it does not reach on its own, so JSRL's state-coverage assumption is not falsified by this measure.
- **"Coverage rises with `h`" → survives.** **Met only as a step, from `h = 0` to `h = 1`.** Across `h = 1 … 9`, `R(h)` oscillates between 1.39 and 2.20 with no upward trend, and `out95(h)` peaks at `h = 2–3` (0.74) and then *declines* to 0.28–0.42. The oscillation has a period of about 4 and sits at the step indices 4 and 8, where the within-pool spread `d0` also dips (4.27 and 4.33 against 5.4–6.0 elsewhere). That is consistent with an episode-wide handover cliff at those steps making states at those indices more alike under any policy. Two things are in line with this: an earlier gate reported such a cliff at steps 4 and 8, though I have not verified it on this harness, and `access` carries ≈ 0 of the distance at exactly `h = 4, 8` in the audit below. **[V for the numbers, I for the cliff attribution]**
- The declared two-branch rule did not anticipate a step-then-flat shape. I report the shape as measured. Which branch it counts as is the coordinator's call.
- **Pooled EE: no interior maximum.** Pooled EE rises monotonically at every step, from 93.11 M (`h = 0`) to 111.50 M (`h = 10`). Each extra guide step raises pooled EE: whatever state the learner is handed, handing it over lowers pooled EE for the rest of the episode relative to continuing with the guide. Adjacent-step increments (0.6–4.1 M) are mostly within one or two per-cell sems (1.0–1.4 M), so the monotonicity is a trend, not eleven individually resolved steps. **[V, D]**
- **One incidental observation, stated and not built on:** on the learner's **own calibrated scalar**, `h = 1` is an interior maximum (+1.0270 vs +0.9033 at `h = 0`). After that the scalar falls monotonically as the guide's handovers accumulate (φ2 rises 0.23 → 0.65). I did not instrument the scalar's per-episode sem, so I do not claim this is resolved.

### Audit of the measure: what the novelty is made of [V]

I z-scored the 112 dimensions so that units would not decide the metric. The worry was that z-scoring would instead let the sparse block-1 one-hot (`access`, the incumbent slot) dominate, making "new state" mean nothing more than "you are sitting on a different slot because the guide moved you". I checked this from the dumped states (`jsrl_blocks.out`). It is **not** what drives the result:

| `h` | share of squared 1-NN distance: `access` | `snr` | `theta` | `loads` | block-only `loads` R | block-only `snr` R | block-only `theta` R |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.103 | 0.273 | 0.163 | **0.462** | **5.38** | 1.15 | 1.30 |
| 2 | 0.145 | 0.272 | 0.162 | **0.421** | **5.64** | 1.34 | 1.45 |
| 3 | 0.115 | 0.284 | 0.160 | **0.442** | **5.53** | 1.59 | 1.59 |
| 4 | 0.000 | **0.406** | 0.269 | 0.325 | **8.78** | 1.09 | 1.16 |
| 5 | 0.128 | 0.272 | 0.183 | **0.418** | **3.76** | 1.11 | 1.26 |
| 6 | 0.069 | 0.296 | 0.197 | **0.438** | **4.48** | 1.20 | 1.37 |
| 7 | 0.063 | 0.258 | 0.176 | **0.503** | **4.99** | 1.41 | 1.40 |
| 8 | 0.001 | **0.391** | 0.241 | 0.368 | **8.61** | 1.16 | 1.17 |
| 9 | 0.108 | 0.274 | 0.191 | **0.428** | **3.95** | 1.10 | 1.30 |

- **The novelty lives mainly in block 4 `loads` (`N_u(t−1)`, the previous step's joint demand per beam): 32–50% of the distance, with a block-only novelty ratio of 3.8–8.8.** Block 2 `snr` (previous-step interference) is next at 26–41%. Both are **endogenous** blocks, set by the previous step's *joint* action. The guide hands the learner congestion and interference configurations its own policy does not produce. `access` carries 0–15%. (Its block-only R is degenerate, because identical one-hot rows make the leave-one-out distance ~0, so I do not report it.)
- **The novelty survives when the incumbent slot is the same.** On the rows whose `access` block is identical to the `h = 0` row at the same (episode, user, step), 341–1074 rows per `h`, `R` is 1.21–1.66 and `out95` 0.12–0.55. On the rows whose slot differs, `R` is 1.47–2.31 and `out95` 0.33–0.77. So a different incumbent adds to the novelty, but it is not the whole of it.
- **No handed state is identical to its `h = 0` counterpart.** The whole-row paired identity is 0.0000 at every `h ≥ 1`. Even `theta` (geometry) is identical in only 1–8% of paired rows. The candidate table itself differs, which I **infer** is because the table must retain the incumbent (`state_encoding.py`, `assert_incumbent_is_recoverable`), so a different association history reorders the slots. I did not verify that mechanism in the table-construction code.

**Limit of the audit, stated:** both dominant blocks describe step `t−1`. So this measures the novelty of the state *at the handover instant*. Whether the learner's trajectory stays in novel territory afterwards, or returns to its own state distribution within a step or two, is **not measured here**, and it is what decides whether the handed states are ones the learner would ever *learn from* rather than merely *pass through*.

### What this section does and does not establish

**Established [V]:** the guide-prefix states differ from the learner's own, at every `h ≥ 1`, mostly in the joint-action-dependent blocks, and the difference is not reducible to the incumbent slot. Coverage does not rise with `h` beyond `h = 1`. Pooled EE rises monotonically in `h` with no interior maximum. Both placebos reproduce bit-for-bit, and the whole sweep is deterministic under re-run.

**Not established:** whether the novelty persists after the hand-off; anything about a guide other than `MAX_NOMINAL_GAIN`; anything about JSRL *training*, since no gradient step was taken. I did not look for a rescue, and I have not proposed an alternative guide. I note only, as a fact from the frontier table and not as a proposal, that `MAX_NOMINAL_GAIN` is itself dominated on the handover axis by the hysteresis rules above.
