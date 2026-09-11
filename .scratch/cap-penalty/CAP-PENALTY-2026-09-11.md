**No: a per-satellite cap of 3 does not produce rank collapse here (the lowest head falls from about 41 to 34 of 50 at episodes 401–500, which is inside the declared ambiguous band, and the other two heads do not move), and the penalty does not prevent even that dip in general. It holds head 0 near 37, but at evaluation it lowers heads 1 and 2 by 3 to 7. The effect the owner remembers belongs to a different penalty, the sibling's capacity penalty L_cap, which is built from `k_cap` and has nothing to penalise without a cap.**

Date 2026-09-11. Agent CAPPENALTY. **500 episodes is not convergence**: the frozen reference run is 9,000 episodes, and training ε is still 0.753 at episode 500. **Capped cells are a different MDP** (§3). Evidence tags: **[V]** means I verified it this session, by running code or by reading the named file:line myself. **[S]** means a read-only subagent I dispatched transcribed it with a file:line and I did not re-open that line. **[I]** means inferred.

Accounting caveat (inherited from PENALTYARM): pooled EE here uses this simulator's per-beam power accounting, which takes a `max` over served users. The literature sums instead. All cells share the same accounting.

---

## 1. Part 1: the discrepancy in the record is resolved, and both sides were right

**PENALTYARM was right about the penalty it ported.** `q_row_decorrelation_penalty` and `srank_penalty` never ran beyond a 3-episode smoke. The 12-run Tier-1b wave was HELD [S, `archive/project-state/CURRENT-STATE-CHRONICLE-through-2026-07-22.md:1549, 1729-1744`]. The only artefacts under `artifacts/shared_q_isolation/tier1b/` are challenger-distinctness JSONs [S].

**The owner's memory is also right. It is about the capacity penalty L_cap** (also called 容量懲罰, M4, and later 懲罰塑形). L_cap ran in real training under `k_cap = 3`, with 6 seeds, in three waves.

**This matches the parallel HARVEST.** HARVEST reached the same answer independently: `.scratch/concept-harvest/CONCEPT-HARVEST-2026-09-11.md` row P1 (:140) and §"owner's recollection" (:342), and `parts/C-catfish-v2-late-july.md` C-1 (:63-80). At the coordinator's request I opened the files HARVEST cites and confirmed them at source [V]:
- `CLOSURE-M4-RESULT-2026-07-18.md:1, 12-30, 83-88`;
- `ABL9K-RESULT-2026-07-21.md:7-37`;
- `EP2K-RESULT-2026-07-20.md:65-75, 116-128, 178-184`;
- ABL9K metadata `k_cap: 3`.

Then I stopped searching.

**Estimand: this is not this project's pooled EE.** The sibling scored `argmax_EE`, "per-seed mean over 48 frozen eval episodes" [V `ABL9K-RESULT:7`], on the best-weighted-reward-on-eval checkpoint [V `CLOSURE-M4:12`]. The per-episode quantity was the July per-user **mean of ratios**, `η_u = R_u / (P_beam / N_beam)` averaged over users, in Mbit/J, with a radiated-RF-only denominator [S, erratum 28 §2 (`.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-ERRATUM-28-…`) and HARVEST C-1; I did not re-derive it from the scorer]. HARVEST [I] also records a concave load-share power model and zero handover energy. Under that estimand a cap-bumped user scores 0, so lifting served from 0.89 to 0.99 lifts the metric by construction. The sibling's +89 to +135 therefore cannot be compared in magnitude with any bit/J number here.

The three waves:

| wave | run path | penalty (impl.) | metric, effect | seeds | control | `k_cap` |
|---|---|---|---|---|---|---|
| **M4** (12,000 ep) | scores `analysis/family-b-collapse-diagnosis/catfish-v2/teacher-matrix-m4-scores-2026-07-18/`; the training dirs are not on this machine [S] | L_cap, λ 0.05, τ 1 (`configs/shared_q_isolation/v3/offm4_capacity_lr001.yaml:14-18` [S]) | argmax EE 523.78 → **613.05 (+89.28, 6/6 seeds)**; served 0.892 → 0.991; min_cov 0.792 → 0.960; **cap_bump 0.108 → 0.009 (−92%)** [V `CLOSURE-M4-RESULT-2026-07-18.md:12-30`] | 6 | converge-probe OFF arm, reused from an earlier batch, not co-trained [S] | 3 (launcher passes none; runner default is 3) [S] |
| **ABL9K** (9,000 ep) | `artifacts/abl9k-2026-07-19/<arm>/seed-*/` | L_cap in L5, L6, L8, L9, L10 | L5 − L2 (penalty alone) **+134.59, CI [116.0, 153.2], 6/6** (descriptive); L6 − L4 +126.34, BENEFIT after Holm [V `ABL9K-RESULT-2026-07-21.md:12-37`] | 6 | L2, L4 | **3** [V `abl9k_capacity/seed-42/run_metadata.json:128`] |
| **EP2K** (2,000 ep) | `artifacts/ep2k-2026-07-20/`, `artifacts/ep2k-scores/*-TRAJ.json` [S] | L_cap in L5, L6, L8 | at every checkpoint the arms "split cleanly into two groups on ONE feature: whether they carry 容量懲罰" [V `EP2K-RESULT-2026-07-20.md:116-128`]; gaps inflated by undertrained controls, "Never quote +392 without this sentence" [V :178-184] | 6 | L2, L3, L4 | 3 [S] |

**What L_cap is, and why this settles the owner's hypothesis for it.** [V, reading `src/modqn_paper_reproduction/shared_q_isolation/capacity_penalty.py:1-9, 148-182`] L_cap penalises the softmax intent mass that falls outside each satellite's top-`k_cap` beams: `T_ℓ = Σ_c p_ℓc − TopKSum_{k_cap}(p_ℓ,·)`, which the module docstring calls "the tail the env actually drops". So its measured effect (cap_bump −92%, served +0.099) is the policy learning to stop getting darkened by the cap. **Without a cap there is no tail.** With `k ≥` beams per satellite, `topk` is the whole sum and `T_ℓ = 0` up to rounding. [I, from the code rather than a run.] For L_cap, "拿掉上限 penalty 就失效" is true by construction; it is not an empirical question.

**How the sibling later qualified L_cap.** [V where marked, otherwise S]
- Its codex review refuted every mediation chain. What stands is "the penalty changed training; coverage and EE improved together" [V `CLOSURE-M4:105-109`].
- λ was never swept, and λ = 0 versus λ > 0 also changes the number of optimiser updates, which confounds the comparison [S `LAMSWEEP-PREREG:14-17`].
- Every result predates the M-09 and M-14 fixes: "不再是現行實作的結果" [V `docs/capacity-penalty-explainer-package/04-measured-results.md:6-8`].
- ABL9K is marked "HISTORICAL — INVALID FOR CURRENT PROTOCOL" [V `CURRENT-STATE.md:167`].
- L_cap was dropped from the thesis on 2026-08-21, with no written reason found [S `thesis-mc/GENRE-RULES.md:56`].

**No L_cap arm was added here.** The coordinator ruled that out of scope. Under a cap, it would be repairing exactly the defect the cap creates.

**What was not measured.**
- The `modqn_faithful_ablation/capacity_penalty.py` copy never ran with the penalty on: every config sets `P_capacity_penalty: false` [S].
- No L_cap run measured any representation diagnostic, rank or otherwise [S].
- Places searched with no penalty performance measurement found, and the grep patterns used, are listed in §8.

## 2. Why this project has no cap (the ruling), and where the flag went

**The ruling's reasons.** [V, `tests/test_ruling_no_beam_count_cap.py:1-22`, `docs/R3-AND-EXECUTION-MASK-NOTES.md` §6, `src/mcrl/env/action_contract.py:60-64`]
1. Sun-2024's `V = 7` is the size of a non-spatial load-channel set. `Σ_v z = V` is an identity, not a bound, and the cap was the old repo's own invention.
2. With pointing and footprints, 7 cells reach a third of the service area at 550 km and a fifth at 485 km.
3. Demand-ranked darkening was measured to starve 68 of 100 users.
4. The cap fights `r3`: that reward pushes users toward quiet beams, which are the first beams a demand-ranked rule darkens.
5. Enforcing the cap in the decision mask would make the mask depend on the joint action, which breaks the per-user argmax that defines B1.

**Where the flag lives, and why.** Ruling §7.1–7.2 forbids the cap *and any socket for it* in `src/`, and a gate test scans `src/mcrl` for one. So the flag is in `.scratch/cap-penalty/beam_cap.py`, a `StepEnvironment` subclass (declared in `DECLARATION-2026-09-11.md` §2 before any run). This deviates from the brief in file location only. It is still the environment layer: it post-processes `resolve_service` at `src/mcrl/env/step.py:822`. The live tree is untouched, and so is `modqn.py`.

**The rule, copied from the sibling rather than chosen.** Per satellite (`norad_id`), rank beams by eligible load, ties to the lower cell id, keep the top 3, and darken the rest (sibling `env/family_b_step.py:834-844`). Only users on a kept beam are served (`:1039`). Darkened beams keep their pre-admission demand in the observation (`:851-853`). The cap is not in the mask. Darkened users are flagged separately from physical outage.

**Tests.** [V] `test_beam_cap.py`, 7/7 passing on the server tree:
- with the flag off, per-step outcomes over 2 episodes and the trained weights after 2 training episodes are bit-identical to the plain environment;
- a non-binding cap is a pure pass-through;
- k = 3 is enforced at every step and only removes service;
- step 0 matches the plain environment minus the darkened users, with the kept set equal to the top 3;
- the unit rule, including ties, holds;
- the live tree has no cap vocabulary.

## 3. This is a physics change

Turning the cap on defines a **different MDP**. It changes who is served, `U_{s,v}`, the radiating set, interference, power and every reward. Under k = 3, **42–47% of user-steps are darkened** (§5). Nothing measured in a capped cell describes the project's MDP.

## 4. Representation: rank and the four G-3 indicators

**Tree.** [V] PENALTYARM's server snapshot, copied unchanged: `src/**/*.py` sha256 identical over 157 files. The workspace `sat:/home/sat/mcrl-v025-cap-penalty-ws` has commits `c46091d` (snapshot) and `6f4c162` (cap flag, tests, driver). Seeds are 42/1337/7, lr 1e-3, and each arm ran 500 episodes as one process: CAP3_OFF 753 s, CAP3_PENALTY 764 s. The penalty is `TB-SRANK-kumar` at α = 1e-3, as in PENALTYARM.

**Training-time srank_δ per head** (PENALTYARM's estimator: δ = 0.01, mean-centred penultimate Φ over the 128-sample TD minibatch, read-only; window means). [V, `results/training-readouts.json`]

| cell | ep 1–100 | ep 101–200 | ep 201–300 | ep 301–400 | **ep 401–500** |
|---|---|---|---|---|---|
| OFF (no cap) | 41.38 / 39.20 / 40.15 | 40.40 / 40.24 / 40.79 | 40.60 / 40.76 / 41.23 | 41.39 / 40.39 / 41.24 | **40.77 / 40.35 / 41.54** |
| PENALTY (no cap) | 38.02 / 39.14 / 42.40 | 38.07 / 39.44 / 42.03 | 38.34 / 39.82 / 40.61 | 38.77 / 39.68 / 39.89 | **38.59 / 39.38 / 39.75** |
| **CAP3_OFF** | 36.79 / 39.38 / 38.61 | **31.80** / 40.27 / 37.65 | **31.73** / 40.33 / 37.85 | 32.14 / 40.38 / 38.01 | **34.02 / 40.46 / 38.04** |
| **CAP3_PENALTY** | 37.42 / 39.32 / 41.28 | 37.59 / 38.96 / 41.15 | 37.71 / 38.21 / 39.57 | 37.50 / 38.05 / 38.16 | **37.13 / 37.22 / 37.09** |

CAP3_OFF's lowest single-episode value on head 0 is 26.0. For scale, the sibling's motivating collapse went from 60 to between 3 and 46.

**Evaluation srank_δ at the checkpoints** (20 fixed 128-state batches). "Own" means the cell's own greedy states. "Probe" means a common set of 24,000 states from the uncapped OFF policy, which removes the cap's shift in the input distribution. [V, `results/eval-main.json`, `results/eval-traj-*.json`]

| checkpoint | CAP3_OFF own | CAP3_OFF probe | CAP3_PENALTY own | CAP3_PENALTY probe |
|---|---|---|---|---|
| ep 100 | 34.65 / 39.25 / 36.80 | 36.20 / 39.65 / 36.80 | 36.65 / 38.00 / 41.60 | 36.65 / 37.45 / 41.00 |
| ep 200 | 34.00 / 40.85 / 36.10 | 37.70 / 41.10 / 36.10 | 36.00 / 35.30 / 39.05 | 36.80 / 35.85 / 39.20 |
| ep 300 | **29.15** / 40.00 / 36.35 | 31.80 / 40.85 / 36.80 | 36.85 / 35.45 / 36.75 | 36.95 / 35.50 / 36.40 |
| ep 400 | 32.90 / 40.75 / 37.25 | 34.55 / 41.15 / 37.05 | 35.55 / 33.80 / 34.80 | 36.00 / 34.20 / 35.35 |
| ep 500 | 35.80 / 40.55 / 37.10 | 37.20 / 41.20 / 37.15 | 36.05 / **34.45** / **34.15** | 36.00 / 34.10 / 34.00 |
| *ref. ep 500, no cap* | *OFF 40.05 / 38.40 / 40.20* | *(probe = own)* | *PENALTY 35.10 / 37.15 / 35.70* | *35.15 / 37.10 / 35.90* |

**Reading against the declaration** (`DECLARATION-2026-09-11.md` §5, fixed before any run). Collapse was defined as an ep 401–500 mean of ≤ 30 on any head; 30–36 is ambiguous; ≥ 36 on all heads is no collapse.
- **CAP3_OFF falls in the ambiguous branch.** [V] Head 0 reads 34.02, inside the band. Heads 1 and 2 read 40.46 and 38.04, which is no collapse.
- **The dip is transient, and on head 0 only.** [V] It bottoms at episodes 101–300: training window 31.7, and at evaluation 29.15 (own) or 31.8 (probe) at ep 300. It recovers to 34–37 by ep 500.
- **The penalty does not "hold rank" in general.** [V] It keeps head 0 at 35.5–37.7 throughout. But at evaluation it lowers heads 1 and 2 below CAP3_OFF at every checkpoint from ep 200 on (ep 500 own: 34.45 vs 40.55 and 34.15 vs 37.10), and it does the same without a cap (PENALTY vs OFF). This repeats PENALTYARM's finding that minimising Eq. (6) does not buy rank.
- **[I]** At n = 1 seed, a −7 dip on one head is about 2× the arm-to-arm spread PENALTYARM saw, so it does not reach the declared collapse bar.

**The four G-3 indicators at greedy evaluation, ep 500** (all steps). [V]

| cell | distinct action slots* | argmax agreement | q_margin (normalised) | q_entropy |
|---|---:|---:|---:|---:|
| OFF | 3.64 | 0.662 | 0.254 | 0.9973 |
| PENALTY | 3.99 | 0.679 | 0.245 | 0.9965 |
| CAP3_OFF | 5.10 | 0.604 | 0.158 | 0.9982 |
| CAP3_PENALTY | 5.97 | 0.707 | 0.213 | 0.9984 |

\*This is G-3's legacy `active_beam_count`: relative action slots out of 28, not physical beams.

[V] The cap does not concentrate the argmax. Agreement is lower and more slots are used. The Q-values are flatter, with a normalised margin of 0.158 against 0.254. **By G-3, the cap does not produce policy collapse either.**

## 5. EE and service, every cell (greedy, ep 500)

Four fields for every number in this table:
- **reference point:** OFF, the uncapped PENALTYARM checkpoint with the same seeds, episodes and tree;
- **information level:** a 500-episode pilot with one training seed per arm, not converged, evaluated over 24 episodes; capped rows are a different MDP;
- **estimator:** pooled bits over pooled joules, a ratio of sums divided once, with the sem taken over 24 per-episode ratios and excluding training-seed variance;
- **numerator:** full-buffer Shannon bits, `energy.system_throughput_bps × 30.08 s`; the denominator is consumed power.

[V, `results/eval-main.{json,log}`]

| cell | pooled bits | pooled J | **pooled EE (bit/J)** | sem | vs OFF | served | cap-darkened | handovers / user-step (intra / inter) | physical active beams (per active sat) |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| OFF | 2.389629e14 | 2.688149e6 | **88,894,962.36** | 1,222,940 | 1.000× | 0.9966 | 0 | 0.1774 (0.0002 / 0.1772) | 58.42 (8.65) |
| PENALTY | 2.450450e14 | 2.849465e6 | **85,996,841.88** | 1,487,797 | 0.967× | 0.9988 | 0 | 0.1752 (0.0029 / 0.1724) | 62.39 (7.39) |
| **CAP3_OFF** | 1.151677e14 | 1.114935e6 | **103,295,432.52** | 639,693 | **1.162×** | **0.5819** | 0.4138 | 0.1811 (0.0257 / 0.1553) | 24.17 (2.70) |
| **CAP3_PENALTY** | 1.342877e14 | 1.225118e6 | **109,612,038.14** | 534,135 | 1.233× | 0.6213 | 0.3780 | 0.1527 (0.0133 / 0.1393) | 26.44 (2.70) |
| OFF weights in the capped env *(eval only)* | 1.136477e14 | 9.895048e5 | 114,853,142.48 | 1,028,624 | 1.292× | 0.5266 | 0.4701 | 0.1543 | 21.33 (2.61) |
| CAP3_OFF weights, no cap *(eval only)* | 1.734129e14 | 2.428289e6 | 71,413,630.90 | 987,895 | 0.803× | 0.9970 | 0 | 0.2743 | 52.76 (6.70) |
| untrained, capped env | 2.991309e13 | 4.513765e5 | 66,270,816.89 | 1,038,244 | — | 0.3514 | 0.5634 | 0.1533 | 10.96 (2.67) |

[V] **Harness integrity:** OFF and PENALTY reproduce PENALTYARM's published endpoint EE to the cent.

## 6. What the cap itself does to pooled EE: a surprise, re-run at larger n

**The observation.** `CAP3_OFF` − `OFF` = **+14,400,470 bit/J (1.162×), 10.4 evaluation-sem**, with the four fields as in §5. That gap is **not** stable in size across checkpoints, but it is stable in sign. CAP3_OFF/OFF runs 1.399, 1.286, 1.286, 1.163, 1.162 at ep 100–500, so it is positive at 5 of 5 checkpoints; OFF's values are PENALTYARM's. [V] Against that, PENALTYARM's PENALTY/OFF changed sign across the same checkpoints.

**Why it counts as a surprise.** The coordinator's erratum 28 (received mid-task) says beam count cancels at first order on this harness, so a cap should not raise EE. My measurement contradicts that. Per the brief's re-run clause, I re-ran it at larger n, evaluation only, with no training and no new arm. The re-run used 96 episodes, of which the first 24 are the same episodes as §5 by RNG construction, and decomposed `EE = (bits per beam-step) ÷ (joules per beam-step)`. [V, `decompose_cap_ee.py`, `results/decomp-n96-{a,b}.{json,log}`]

Four fields for this table:
- **reference point:** OFF weights with no cap;
- **information level:** 96 evaluation episodes, one training seed;
- **estimator:** ratio of sums;
- **numerator:** as in §5.

| cell (n = 96) | pooled EE | × ref | bits / beam-step | J / beam-step | beam-mean SE (bit/Hz) | SINR dB (served) | interference W (served) | served |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| OFF weights, no cap | 88,747,527.44 | 1.000 | 1.7008e10 | 191.64 | 3.3925 | 8.79 | 3.294e-12 | 0.9974 |
| OFF weights, cap 3 | 113,133,905.96 | **1.275** | 2.1823e10 (1.283×) | 192.89 (1.007×) | 4.3530 (1.283×) | 12.63 | 3.790e-13 (**0.115×**) | 0.5425 |
| CAP3_OFF weights, cap 3 | 103,511,011.93 | 1.166 | 1.9899e10 (1.170×) | 192.24 (1.003×) | 3.9693 (1.170×) | 11.38 | 5.134e-13 (0.156×) | 0.5867 |
| CAP3_OFF weights, no cap | 73,208,284.77 | 0.825 | 1.4008e10 | 191.34 | 2.7941 | 6.40 | 3.809e-12 | 0.9962 |

**What the decomposition shows.**
- [V] **The erratum is right about power:** joules per beam-step are flat to within 0.7% across all four cells.
- [V] **It is not right about the numerator.** The cap removes about 60% of the radiating beams, so interference per served user falls 7–9×. Spectral efficiency, and with it bits per beam, rises 17–28%. The bits-per-beam ratio equals the spectral-efficiency ratio exactly, which is erratum 25's `R_beam = B · mean SE`.
- [V] **So beam count cancels in the denominator but not in the numerator.** Interference is gated by activation, which is the channel erratum 28 lists as "not measured". Its net sign under a cap is now measured, at one training seed: positive for pooled EE.
- [V] **The gain is bought with starvation.** Delivered bits fall to 0.48–0.49× while pooled EE rises, because 41–47% of user-steps are darkened.
- [I] **This matters beyond this arm.** Pooled EE as a ratio of sums, with no service floor, rewards darkening beams. It raised EE by 17–29% here while serving about half the users. Any EE claim in this project needs the served fraction beside it. The sibling's L_cap result, "EE up and served up under the cap", is a recovery from cap-induced darkening. An uncapped MDP has no darkening to recover from.
- I did not use the −425,009.885 bit/J slope; per erratum 28 it belongs to V0.25 only.

## 7. CAP3_PENALTY vs CAP3_OFF

**The observation.** +6,316,606 bit/J (1.061×, 7.6 evaluation-sem, four fields as in §5, reference CAP3_OFF). The penalty arm is at or above CAP3_OFF at 5 of 5 checkpoints (1.000, 1.083, 1.087, 1.022, 1.061) and serves more users at 5 of 5 (+1.6 to +7.3 points). [V]

**I do not claim an EE effect.** The reasons:
- one training seed;
- 500 episodes;
- serially correlated checkpoints;
- **no NULL_PENALTY arm under the cap**, and PENALTYARM found NULL ≈ PENALTY without the cap, so "any perturbation" is not excluded;
- the declared representation premise was not established (§4).

**What a resolvable test would take.** This is a scoping statement; the owner decides. [I]
- Three arms under the cap: CAP3_OFF, CAP3_PENALTY and CAP3_NULL.
- About 8 training seeds per arm. This assumes a paired between-seed SD of about 5%, taken from PENALTYARM's checkpoint swing, to detect about 5% at α = 0.05 with power 0.8. It is not a measured SD.
- Cost at about 1.55 s per episode: about **5 CPU-hours at 500 episodes**, or about **93 CPU-hours at 9,000 episodes**. That is **heavy**, so it belongs on the server.
- Resolving §4's ambiguity alone (CAP3_OFF and OFF, 5 seeds, 500 episodes) is about 2.2 CPU-hours.
- **Either test measures a different MDP.** Neither bears on the project's uncapped MDP unless the owner reopens the 2026-08-22 ruling.

## 8. Verified vs inferred, and where I looked

**Verified by running code:**
- the 7 cap tests, including bit-identity with the flag off;
- the two 500-episode pilots;
- the training-log rank extraction for all four cells;
- 7 + 8 greedy evaluation cells, with the integrity match to PENALTYARM;
- the n = 96 decomposition;
- src sha256 identity with PENALTYARM's tree.

**Verified by reading:**
- the ruling test and notes, and `action_contract.py:60-64`;
- the sibling's cap rule (`family_b_step.py:834-853, 1039`);
- `capacity_penalty.py`;
- `CLOSURE-M4:12-30, 105-109`, the `ABL9K-RESULT` table and contrasts, the ABL9K metadata `k_cap: 3`, `EP2K-RESULT:116-128, 178-184`, the explainer-package erratum, and `CURRENT-STATE.md:167`;
- erratum 28.

**Transcribed by the subagent [S]:**
- the M4 launcher and seed details;
- the EP2K `k_cap` metadata;
- the Tier-1b HELD status;
- the faithful-ablation copy never being enabled;
- the LAMSWEEP and thesis-removal records.

**Inferred:**
- L_cap being exactly zero without a cap (from the code, not a run);
- the dip being within single-seed noise;
- the seed and CPU-hour estimate;
- the design implication in §6.

**Not established:**
- anything at convergence or at more than one training seed;
- anything under standard (summed) per-beam accounting;
- anything with D-2 landed;
- anything about L_cap on this project (not ported, not run).

**Part 1 search coverage** [S]: `artifacts/` (including `_codex-logs`), `analysis/`, `configs/`, `docs/`, `thesis-mc/`, `archive/`, and all git refs, with the patterns `penal|srank|decorr|capacity_penalty|L_cap|lagrang|overload_penalty|load_penalty|handover_penalty|switch_cost|P_capacity_penalty.*true`. **Other penalty-like losses with a measured effect:** the DQfD margin loss (an imitation loss, with mixed signs across learning rates) and the r2 handover objective (never ablated in training). Neither is the remembered effect.

## 9. Files

- Report: `/home/u24/papers/mcrl-leo-handover/.scratch/cap-penalty/CAP-PENALTY-2026-09-11.md`
- Declaration, fixed before the runs: `.scratch/cap-penalty/DECLARATION-2026-09-11.md`
- Progress: `.scratch/cap-penalty/PROGRESS.md`
- Code: `.scratch/cap-penalty/{beam_cap.py, test_beam_cap.py, run_cap_pilot.py, eval_cap_cells.py, analyze_training_logs.py, decompose_cap_ee.py}`
- Results, local copy: `.scratch/cap-penalty/results/`
- Checkpoints and probe, server only: `sat:/home/sat/mcrl-v025-cap-penalty-ws/runs/`
- No file under `src/` was touched. No process is left running.
