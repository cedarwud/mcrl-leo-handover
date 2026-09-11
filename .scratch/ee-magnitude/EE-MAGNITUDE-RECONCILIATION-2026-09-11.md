**The dominant factor is the power denominator: the sibling's cited "argmax-EE" values (146–620) divide by radiated RF beam power only, while this project divides by PA supply plus circuit plus baseband power, which is ×7.60 larger on this project's own rollouts — and when this project's own trained checkpoint is scored with the sibling's July formula it reads 693.87 "Mbit/J" (RANDOM_MASKED 373.61), so the two sets of numbers are not comparable, and the "1/U" reading in the brief does not apply to any number that was cited.**

EEGAP — 2026-09-11. Read-only across both repos plus one scoring run (2 arms × 24 episodes, no `update()`,
local `.venv`, `nice -n 16`, 1 thread, wall 180.4 s). Tags: **[V]** = I read the code or ran it this session;
**[D]** = arithmetic on [V] numbers; **[I]** = inference, not measured; **[R]** = relayed from an existing record
that I did not re-check.

---

## 0. The brief's premise was wrong, and fixing it changes the reading

The brief says `argmax_EE` is the mean over users of `R_u / P_system`, so it would be system EE divided by U.
**For the current sibling code that is true. None of the cited numbers came from that code.**

- **[V]** At sibling HEAD, `family_b_eta_r1` → `family_b_system_ee_contribution`
  (`src/modqn_paper_reproduction/analysis/family_b_recalibration.py:120-143`) returns the env's
  `r1_system_ee_contribution`, which is `per_user_contributions_bits_per_j[uid]` of a system accounting
  (`env/family_b_step.py:1459-1461`). Those do sum to system EE. **At HEAD, a mean over users would be system EE / U.**
- **[V]** That definition landed in commit **`60807490` on 2026-08-05** ("r1 改為論文 (3.26)/(3.27)"). The diff
  deletes the earlier body.
- **[V]** Every cited number is dated **2026-07-11 to 2026-07-21**: 146.63 (`INJ-RUNG1-DISCUSSION/mech-probes/kcap_RESULT.md`,
  commit 116991aa, 07-11); 145.47 / 150.13 / 235.53 / 472.22 / 493.18 / 428.60
  (`analysis/family-b-collapse-diagnosis/COLLAPSE-ROOT-CAUSE-IS-LR-2026-07-20.md:34-41`); 146.6 → 357.1 (the July-14/15
  explainer records); 609.45 (`catfish-v2/ABL9K-RESULT-2026-07-21.md:16`). Over that window neither file changed:
  `family_b_recalibration.py` goes from `211a71a3` (07-04) straight to `60807490` (08-05), and `env/family_b_step.py`
  goes from `f33e9c46` (06-18) to `eba5ea4f` (08-03). `git diff f33e9c46 0082683d -- env/family_b_step.py` is empty, and
  `7a2a24dd` (07-15) touched only docstrings in other files.
- **[V]** The function **in force for those numbers** (rev `0082683d`, `family_b_recalibration.py:121-167`;
  introduced by `211a71a3`, 2026-07-04):

  ```
  beam_power_w      = result.slot_power_w[uid, assigned_slot]     # the beam's RADIATED power
  allocated_power_w = beam_power_w / max(beam_load, 1.0)          # :153  equal split
  p_tot_effective   = allocated_power_w                           # :158
  eta = R_u / p_tot_effective                                     # runtime/angle_aware_ee.py:487-488 (alpha = 1, p0 = 0)
  ```

  So **η_u = R_u · N_b / P_b**. The rate is `R_u = (B/3)/N_b · log₂(1+SINR_u)` (July `family_b_step.py:740`), so
  **N_b cancels, and η_u = (B/3)·log₂(1+SINR_u) / P_b**: each user is credited with its beam's whole band over its
  beam's whole radiated power. The mean over U users is then Σ_b (N_b/U)·EE_b, a **load-weighted average of per-beam
  RF efficiency, in which unserved users count as zero**. That is approximately served-fraction × (RF-only system
  EE). It is **not** system EE / U.
- **[V]** Scorer at sibling HEAD (the file is unchanged since 2026-07-13): the per-user values are built at
  `score_argmax_endpoint.py:105`, averaged over users at **:110**, over steps at :119, over episodes at :120, and divided
  by 1e6 at :121. The brief's ":105/:118/:120" are one to two lines off.
- **[V, measured]** On this project's rollouts the July formula comes out at **0.980×** this project's own RF-only
  ratio of sums for TRAINED and 0.927× for RANDOM (§3). The estimand is close to neutral. It is not a factor of 1/U.
  Applied to the same rollouts, the current sibling formula gives **0.93** (TRAINED), which is about 1/100 as the
  brief expected. That formula simply never produced a cited number.

So the gap is not "far larger than it looks." It is about as large as it looks, and it comes from a different place.

---

## 1. Decomposition table

"Effect" is the multiplicative effect on the reported EE when you move from this project's setting to the sibling's.

| # | Factor | Sibling (as used for the July numbers) | This project (MODQN harness) | Effect on EE (sibling ÷ this) | File:line — sibling / this |
|---|---|---|---|---|---|
| 1a | **Estimand** | mean over (users → steps → episodes) of per-user η_u = R_u·N_b/P_b; unserved users = 0 | pooled: Σ bits / Σ joules, divided once | **×0.980** TRAINED, **×0.927** RANDOM (measured as C/B, §3). About served-fraction × load weighting (C/(served·B) = 0.982 / 0.990) **[V]** | scorer `:105,110,119-121`; July `family_b_recalibration.py:121-167`, `angle_aware_ee.py:487-488` / `runtime/energy_efficiency.py:114-144`; `.scratch/catfish-surface/CATFISH-ATTACHMENT-SURFACE-2026-09-11.md:527-531` |
| 1b | the `1/U` | **does not apply to the cited numbers**; applies only to post-2026-08-05 code | — | would be ×0.01. **Not in force** for 146–620 **[V]** | HEAD `family_b_recalibration.py:120-143`, `family_b_step.py:1459`; commit `60807490` |
| 1c | `/1e6` | bit/J → Mbit/J | the 53.06 / 93.11 figures are already Mbit/J | **×1**, a units label on both sides **[V]** | scorer `:121` |
| 2 | **Denominator: what counts as power** | **radiated RF only**: `P_b = min(0.25 + 0.35·√N_b, 10) W` per active beam, then a per-satellite cap of 20 W (not binding at ≤3 beams per satellite). No PA, no circuit, no baseband | **consumed**: `P^N = Σ_b p_b/ξ(p_b) + 0.338·beams + 0.2·active sats`, with `ξ = 0.35·√(p_b/5.218)` ≈ 0.138 at p_b ≈ 0.82 W. PA = **94.2%** of P^N, fixed = 5.8% | **×7.60** (measured consumed/RF on the same rollouts: 7.602 TRAINED, 7.597 RANDOM) **[V]** | July `family_b_geometry.py:49-53, 374-386`, July `family_b_step.py:510` / `env/link_budget.py:175,254-273,468-588`; `env/step.py:973-1022` |
| 3 | per-beam RF power level | ≈1.23–1.30 W at healthy loads of 8–9 users per beam (the concave rule) | **0.824 W** mean (TRAINED); p⁰ = 0.825 W, ceiling 1.65 W; beam power = max over its users | ×≈0.66 (this project radiates *less* per beam, which *favours* this project in RF-only EE) **[I]**: sibling value inferred from `served`/`beams`, not logged | July geo `:374-378` / `link_budget.py:175,213,439-465` |
| 4 | Numerator: bandwidth, U, rate law | B = 500 MHz, reuse 3 → **166.67 MHz** per beam; **U = 100**; `(B/3)/N·log₂(1+SINR)`; full buffer; no demand cap | **identical**: 166.67 MHz, U = 100, same Shannon law, full buffer, no demand cap | **×1** **[V]** | July `family_b_step.py:81,87,102-103,740` / `link_budget.py:21-28,590-615`, `training_pipeline.py:736-741` |
| 5 | SINR regime | G0 = **1e4 (40 dBi)**; noise −174 dBm/Hz + 1.2 dB NF; Walker-180 at 780 km; atmosphere ≈0.02 dB | G0 = **2000 (33 dBi)**; kT with T_sys = 242.3 K (noise **1.96 dB lower**); TLE constellation; 0.25 dB/sin(el) atmosphere | mean log₂(1+SINR) over served users: **3.51** TRAINED / 2.12 RANDOM here [V] vs **≈4.1–4.8** for sibling healthy arms [I] → about ×1.2–1.4 | July `family_b_step.py:79-85`, geo `:36-44` / `antenna.py:46`, `link_budget.py:35-50` |
| 6 | `dt` | 1 s slot; not used by the scorer | 30.08 s; multiplies both bits and joules | **×1**: cancels in a ratio **[V]** | July `family_b_step.py:88` / `env/constants.py:76` |
| 7 | **Environment: beam cap and active beams** | **k_cap = 3** per window satellite, 4 satellites → **≤12 beams**. Healthy arms average **9–12 beams at ≈8–9 users/beam**; the collapsed arm averages **3.00 beams** with served 0.297 | **no cap** (by ruling); **67.9 beams** over 7.6 satellites at **1.48 users/beam** (TRAINED); 76.6 beams / 1.22 users/beam (RANDOM) | **≈×1 at first order in both physics** [D/I], because each active beam carries the whole 166.67 MHz and costs roughly the same power however many users it holds. This project's EE ≈ (B/3)·SE/P_beam: 93.6 predicted vs 93.1 measured (TRAINED), 56.2 vs 53.1 (RANDOM). The cap cannot "remove PA and fixed power" in the sibling, because the sibling's July denominator contains none | July `family_b_step.py:75, 496-514` / `env/service.py:131-147`, `action_contract.py:60-64`; bridge `mean_beams`, `mean_load` |
| 8 | Where the cap *does* act | it causes overflow (`cap_bump`): unserved users count as 0 in the per-user mean. Collapsed served 0.297 → healthy 0.83–0.93 → capacity-teacher 0.99 | served 0.999 (TRAINED), 0.936 (RANDOM); the pooled estimand does not count unserved users as zeros | **×served** in the sibling's estimand only (×0.30 collapsed, ×0.89 healthy) **[V]** from sibling JSONs | sibling `catfish-v2/**/*.json` (`served`, `beams`), `kcap_RESULT.md` table |
| 9 | the `d(EE)/d(active) = −425,009.885` figure | — | it comes from the **V0.25 a-r0 TDM path** (CROWDCOST), **not the MODQN harness** | not transferable to this table **[R]** | memory `c3-global-view-physics-2026-09-08.md` (2026-09-10 correction) |

**Chain for TRAINED, measured end to end [V]:** this project's pooled EE **93.11** → switch the denominator to
radiated power (**×7.602**) → **707.82** → switch to the sibling's per-user estimand (**×0.980**) → **693.87** on the
sibling's scale. The residual between 693.87 and the sibling's 428–620 is rows 3, 5 and 8 (per-beam RF power, SINR,
served fraction under the cap). Those rows partly cancel one another, and none is larger than ~1.5×.

---

## 2. The bridge: this project on the sibling's estimand

Script `.scratch/ee-magnitude/eegap_bridge.py` (sha256 `95e23765…afd7031`), output `eegap_bridge.txt`
(`3cc45894…2b139b39c`). The trained arm loads `artifacts/training-2026-08-25-rerun01/main/final-checkpoint.pt`, sha256
`e6b063ef…1b09c28b`, greedy ε = 0. Frozen seeds 42/1337/7, a fresh environment per arm, 24 episodes × 10 steps.
Every quantity is read from `env.last_outcome` (`resolution`, `radiating.power_w`, `link_rate_bps`, `link_sinr`,
`system_power_w`, `fixed_power_w`), not rebuilt from reward fields.

**Harness validity [V]:** RANDOM A = **53,060,175.56** bit/J, bit-identical to the recorded value. TRAINED A =
**93,110,907.97**, identical to the anchor-ablation placebo (`CATFISH-ATTACHMENT-SURFACE-2026-09-11.md:648`). The
internal checks all came back 0: `P^N` = energy denominator = fixed + Σ supply; Σ rate = energy numerator; per-beam
served counts = `eligible_load_by_beam`.

**How C maps onto the sibling:** η_u = R_u·N_b/p_b, with p_b the beam's radiated power and N_b its admitted load. That
is exactly `family_b_eta_r1` at `0082683d` (slot_power_w = radiated power of the served beam, beam_loads = post-admission
load), averaged over users, then steps, then episodes, then divided by 1e6. The one translation is that p_b is *this*
env's radiated beam power (max over served users) rather than the sibling's concave rule. That substitution is what
"this project's env outputs" means here, and it is why this is a bridge of estimands, not of physics.

| Estimand (Mbit/J) | RANDOM_MASKED | TRAINED e6b063ef |
|---|---:|---:|
| **A** pooled, consumed power (this project's declared) | **53.06** | **93.11** |
| B pooled, radiated power only | 403.10 | 707.82 |
| **C** sibling July `argmax_EE` (mean of R_u·N_b/p_b, /1e6) | **373.61** | **693.87** |
| C′ as C but per-beam consumed power | 49.02 | 91.57 |
| D sibling HEAD formula (mean of R_u/P^N = system EE / U) | 0.5535 | 0.9285 |
| E mean over steps of per-step consumed EE | 55.35 | 92.85 |
| F mean over steps of per-step RF EE | 414.19 | 703.44 |
| ratio B/A (denominator) | 7.597 | 7.602 |
| ratio C/B (estimand, RF) · C′/A (estimand, consumed) | 0.927 · 0.924 | 0.980 · 0.983 |
| PA share / fixed share of P^N | 94.3% / 5.7% | 94.2% / 5.8% |
| mean active beams · satellites · users per beam | 76.6 · 8.08 · 1.22 | 67.9 · 7.63 · 1.48 |
| served / 100 · mean log₂(1+SINR) served · mean p_b · mean supply per beam | 93.6 · 2.12 · 0.838 W · 5.95 W | 99.9 · 3.51 · 0.824 W · 5.89 W |
| per-episode sd of C | 13.85 | 37.59 |

The estimand factor is the same whichever denominator it is taken with (C/B ≈ C′/A), so rows 1a and 2 of the table
are separable, and their product is C/A = **7.04** (RANDOM) and **7.45** (TRAINED). **Scored on the sibling's formula,
this project's random policy reads 373.6 and its trained checkpoint reads 693.9.** That is a statement about the
formula, not a ranking. The physics under each number still differ (rows 3, 5, 7, 8).

**The reverse direction, inferred only [I]:** take the sibling's healthy OFF arms (EE 523.78, served 0.892, 10.93
beams; `converge-probe-scores-2026-07-17/OFF-*.json`). Under equal loads the per-served RF EE is about 587, the implied
P_b is about 1.25 W, and the implied SE is about 4.4. Pricing 1.25 W through *this* project's PA and fixed model gives
about 7.7 W per beam (×6.16). That puts sibling-healthy at **≈95 on this project's pooled-consumed estimand**, the same
order as this project's 93.11. The inference assumes equal beam loads (Jensen), ignores cap-bump structure, and borrows
this project's p_sat = 5.218 W, which is tied to p_max = 1.65 W while the sibling's P_MAX_W is 10 W. **Do not cite it
as a measurement.** It needs a run of the July sibling env with a consumed-power accountant, which I did not do (the
brief allowed one computation).

---

## 3. The sibling's "collapsed baseline MODQN"

**[V]** `COLLAPSE-ROOT-CAUSE-IS-LR-2026-07-20.md:3-6, 34-41`: the collapse is attributed to `lr = 0.01`. The
single-variable pair (`fulldqfd_OFF` vs `fulldqfd_OFF_lr001`, same wave, one leaf differing in `run_metadata`) moves
**235.53 → 472.22**. The plain raw-224 argmax MODQN at lr = 1e-3 scores **493.18** (waveE, n = 3) and **428.60**
(abl9k L1, n = 6). At lr = 0.01 the raw-argmax arm is **150.13** on all three seeds, with served 0.297 and 3.00 active
beams (`kcap_RESULT.md` table).

**[V] Once its learning rate was corrected, the sibling's baseline MODQN was in the same band as the methods, but not
equal to the best of them.** On the same frozen scorer (`ABL9K-RESULT-2026-07-21.md:11-20`):

| arm | argmax_EE | vs L1 |
|---|---:|---:|
| L1 baseline MODQN, raw, lr 1e-3 | 428.60 | 1.00× |
| L2 + z-score/concat | 485.14 | 1.13× |
| L4 strategy3+ACRM | 483.10 | 1.13× |
| L5 capacity teacher alone | 619.73 | 1.45× |
| L6 full MCCRL | 609.45 | 1.42× |
| catfish-argmax arm (`scfza_catfish_argmax`, teacher-matrix b4, n=6) | 477.31 | ≈1.11× |

**[D]** The collapse on the sibling's estimand is mostly a **served-fraction penalty**. EE per served user is
146.63/0.297 ≈ **494** collapsed, 523.78/0.892 ≈ **587** healthy OFF, and 613.05/0.991 ≈ **619** capacity teacher.
The collapsed policy's *served* users sit on beams about as RF-efficient as a healthy policy's. What it loses is the
70% of users bumped by `k_cap = 3`, who count as zeros in a per-user mean. On a pooled estimand, which does not count
unserved users as zeros, the collapse would look far smaller **[I]**. The best methods' +42–45% over L1 mostly lifts
served fraction under the cap (0.84–0.89 → 0.99).

So: **the "hundreds" were not produced by the catfish or MCCRL methods.** The corrected baseline was already at 428–493.
The methods added a real but smaller increment (+56.54 for z-score, +124.31 for full MCCRL over L2, 6/6 seeds), and
most of it is coverage under the cap. The ~150 "baseline" figure was a mis-tuned run, and the scorer's zero-counting of
bumped users amplified it.

---

## 4. Are the numbers comparable? No.

The two numbers differ in the denominator (×7.6, measured), in the estimand (×0.93–0.98, measured; ×served in the
sibling's collapse regime), and in physics (G0, noise, RF power per beam, the beam cap, the constellation). Only the
first two can be removed by rescoring, and removing them (§2) puts this project's trained checkpoint at 693.87 on the
sibling's scale. What remains is a physics difference, and I did not measure it on a common env, so **neither project
can be ranked from these numbers.** Two further warnings:

- **[V]** The sibling moved too. At sibling HEAD, `FamilyBEnvConfig` has `g0_linear = 2000`,
  `effective_power_efficiency = 0.35`, `fixed_rf_chain_power_w = 0.338` and `fixed_baseband_power_per_active_satellite_w = 0.2`
  (`env/family_b_step.py:104-110`), and r1 is system-EE/U. **A sibling "argmax_EE" produced after 2026-08-05 is on a
  third scale** (about 1/100 of a pooled consumed EE). None of the cited numbers is from that era.
- **[V] on sat, read-only** The V0.25 panel (10–62) is a different physics again. It uses the same PA and fixed
  constants (`/home/sat/mcrl-v025-codex-ws-engine/src/mcrl/physics_v025/constants_v025.py:34-39`, rev 75c5c78c), plus
  a **50 Mbit/s per-user rate target** (`:47`), power control to a target SINR (`:45`), TDM and ACM. The MODQN harness
  delivers about 395 Mbit/s per user (TRAINED, 3.95e10 bit/s / 100) with no demand cap. **[I]** The demand cap on the
  numerator is the obvious first suspect for V0.25 < MODQN harness. I did not decompose that gap.

---

## 5. Answer to the owner (繁中)

**這個專案的 EE 並不「低」，是分母不一樣。** 舊專案 7 月那批「argmax-EE」（146、236、357、428、472、493、609）用的是
2026-07-04～08-05 期間的公式：每位使用者算 `R_u / (P_beam/N_beam)`，使用者數互相抵銷，等於「整支 beam 的頻寬速率 ÷ 那支 beam
的**射頻發射功率**」，再對 100 位使用者取平均（沒被服務的算 0）。分母只有天線射出去的 ~1.25 W，**沒有 PA 耗電、沒有電路與
基頻功率**。這個專案的分母是**實際耗電**：PA 供電（效率只有 ~14%）＋每束 0.338 W＋每顆衛星 0.2 W，PA 佔 94%。
同一批模擬回合裡，耗電是射頻功率的 **7.60 倍**，這就是主要差距。估計量本身（使用者平均 vs 比值加總）只差 2～7%。
brief 裡「除以 U」的說法**對現行 sibling 程式成立，但被引用的數字全都早於那次改動（2026-08-05），不適用**。
實測：拿舊專案的公式去算**這個專案**，訓練好的 checkpoint 是 **693.87**，連隨機策略都有 **373.61**，都比舊專案那個崩掉的
baseline（~146）高。所以兩邊的絕對數字不可比，也不能拿來排名。舊專案的 beam 上限 `k_cap = 3` 不是讓 EE 變高的原因：
每支 beam 都拿到完整 166.67 MHz、耗電也跟人數無關，所以 beam 數在比值裡一階抵銷，而且舊公式分母裡本來就沒有 PA／固定功率可以省。
cap 真正的作用是讓一部分使用者被擠掉、在平均裡算 0。最後，**舊專案的 baseline MODQN 把學習率從 0.01 改成 0.001 之後，
本身就有 428～493，跟其他方法同一個量級**（最好的 full MCCRL／capacity 約 610～620，比 baseline 高約 42～45%）。
所以那些「幾百」主要來自估計量、分母和學習率，不是 catfish 方法本身。方法增益是真的，但比較小，而且大多是在 cap 之下服務到更多人。

---

## 6. Verified vs inferred

**Verified by running code, this session:** the bridge table in §2 (both arms, 24 episodes, harness validity
reproduced to the bit, all internal accounting checks at 0) and the checkpoint's SHA-256.

**Verified by reading primary source:** the July `family_b_eta_r1` body and its dates (`git show 211a71a3`, `0082683d`,
`60807490`); the July env config, power rule, cap enforcement and rate law (`git show 0082683d:…family_b_step.py`,
`…family_b_geometry.py`, `…runtime/angle_aware_ee.py`); the scorer lines; the LR record; the abl9k table; the sibling
JSON `served`/`beams`/`argmax_EE` values; this project's `link_budget.py`, `step.py:973-1022`,
`energy_efficiency.py:114-144`; the sibling HEAD config; the V0.25 constants (on sat, read-only).

**Derived:** the per-served-user sibling values; this project's (B/3)·SE/P_beam check; the ratio chain in §1.

**Inferred, not measured:** the sibling's per-beam RF power and SE (from served/beams, equal-load assumption); the
"≈95 on this project's estimand" reverse bridge; the claim that the beam cap is roughly EE-neutral at first order in
the sibling (argued from the formula and consistent with `kcap_RESULT.md`, but not isolated there because that probe
used a policy trained at k_cap = 3); the V0.25 demand-cap attribution.

**Relayed:** the −425,009.885 bit/J/beam figure and its V0.25 a-r0 provenance (memory note, 2026-09-10 correction).

**Not established:** any comparison of the two *physics* on a common estimand and common power model. That would
need the July sibling env run with a consumed-power accountant, or this env with the sibling's concave RF rule. Either
is a second computation, and I did not run one.
