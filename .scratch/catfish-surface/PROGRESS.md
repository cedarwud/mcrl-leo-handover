# CATFISHSURFACE progress

Started 2026-09-11. Read-only audit. Output: CATFISH-ATTACHMENT-SURFACE-2026-09-11.md
**Reframed mid-task by coordinator: target mechanism is DQfD (Hester et al., AAAI 2018), not the RIS catfish.**
Q4 downgraded to one line; new Q8 (a)-(d) on the DQfD loss surface added at Q6 priority.

Companion facts doc read in full: `.scratch/catfish-facts/CATFISH-MECHANISM-FACTS-2026-09-11.md` (288 lines).

## Question status — ALL ANSWERED

- [x] Q1 trainer = `src/mcrl/algorithms/modqn.py:84` `MODQNTrainer`; step fn `update()` :511; config `TrainerConfig` `src/mcrl/runtime/trainer_spec.py:25`. Runnable today (verified import + env build in `.venv`); local `code_sha256` 817dc1a1… != frozen 544fcf07…
- [x] Q2 `ReplayBuffer` `src/mcrl/runtime/replay_buffer.py:13`, cap 50_000 (trainer_spec.py:68), sampled at modqn.py:527, pushed at :1270. Single buffer field :143; no interface assumption of singularity.
- [x] Q3 gamma = `cfg.discount_factor` at modqn.py:550, one scalar, dataclass field trainer_spec.py:49; shared by all 3 objective heads.
- [x] Q4 (low priority) one agent only; `VALID_POLICY_SHARING = frozenset({"shared"})` trainer_config_validation.py:39.
- [x] Q5 ACRM lives only in sibling: `catfish_faithful_familyb/trainer.py:480-497` `_apply_acrm_shaping`; presets.py:110-120/:138-150. NOT reachable from this project. **Runs DID enable it** — corrects facts-doc "not established".
- [x] Q6 no seeding path; tuple shape captured from replay_buffer.py:29-54 + _copy_transition :113-152.
- [x] Q7 1.5869 s/episode (main run status.json, 9000 ep / 14282.2 s). 3000 ep = 1.32 h.
- [x] Q8 n-step ABSENT, margin/supervised ABSENT, PER ABSENT, pre-training ABSENT (+ double-DQN absent, L2 absent).

## Follow-up round (coordinator, same session) — COMPLETE

Appended `## Follow-up: is there a demonstrator on the MODQN action space` to the report.

- [x] F4 (done first — it decides the rest) **PREMISE FAILS.** `41.28` is an *active-beam count*, not an EE (`/home/sat/mcrl-v025-probe-ws/BASE-COLLAPSE-DIAGNOSIS-2026-09-10.md:25,30`; `:5` "not a performance or EE claim"). The learner's EE on that panel was never measured — BEAMCOUNT Part 3 is "NOT COMPLETED", stopped by cost control, "none should be inferred" (`:279-289`). `62.502712` is a CAP_050 **search winner** (`winner_start = RSS_MAX_within_cap (polished)`, specprofile PROGRESS.md:47), selected on boundary-0 which the report says overstates; the best *declared rule* at C=50 is 52.042303. Both numbers are V0.25 physics, neither on the MODQN harness.
- [x] F1 MODQN action space = `a = 7l + j`, 4 sat slots x 7 **user-relative** cell slots = 28 (`action_contract.py:14-16,40,43,68`); obs 112 = 4x28 blocks built at `step.py:1125-1184`. Nominal gain **available** (block 2, `step.py:1151`). Active beam set **derived not chosen** (`step.py:1027`). Cap **does not exist by ruling** (`action_contract.py:60-64`). Other users' current-step choices **not available** (block 4 is t-1).
- [x] F3 **The two physics differ in action space.** V0.25 options are global `(norad_id, cell_id)`, 9 sats / 370 beams, set is an explicit capped decision variable (`run_v025_matrix_probe.py:435-439`). Only the max-gain clause is expressible in MODQN; that clause **is** `RSS_MAX` = 41.621560 Mbit/J, the *weakest* family member on V0.25. Second mismatch: GAIN_IN_SET does 98/100 handovers, Phi 59.5 (specprofile:33-35) vs MODQN's 0.3-weighted r2.
- [x] F2 **Ran it.** Scripted 5-arm probe, 8 ep each, frozen seeds, no gradient step. Random arm reproduces frozen episodes 0-7 to +2.4% (harness verified). **MAX_NOMINAL_GAIN r1 = 1.107376e+07 = +23.9% over the trained checkpoint's 8.938629e+06** — a real demonstrator on r1. **But calibrated scalar +0.0013 vs learner +0.8859** — it is worse on MODQN's actual objective. Generation cost measured: 4.5408 s/ep locally -> 500 ep = 37.8 min; <=13.2 min on the frozen run's host. Producer ~130-150 lines, inside the existing estimate.

**Net change to the judgement:** classification (b) at ~470-640 lines UNCHANGED. The single biggest failure reason MOVES: not "no demonstrator exists" (that was about `src/` and under-answered) but "the only expressible better-than-learner demonstrator is better on r1 only and worse on the scalarized objective, so `J_E` would fight the reward." Cheapest unmeasured next thing: a myopic demonstrator built on the *scalarized* objective rather than r1.

## Scalarized-objective demonstrator round (coordinator) — COMPLETE

Appended `## Scalarized-objective demonstrator` to the report. Read-only, no `update()` call.

**HEADLINE: NO. No expressible arm beats the trained checkpoint's +0.8859 on the calibrated scalarized objective.**

Construction: score = 0.5*kappa*r1_hat + 0.3*r2_hat + 0.2*r3_hat/6, all three predicted from the
112-dim observation only. r2_hat exact from block 1 + `a//7` (PHI1=0.5/PHI2=1.0,
`action_contract.py:408,411`); r3_hat = -(load+1) from block 4 (t-1, stale); r1_hat = (B/(load+1))*log2(1+sinr)
per eq. 3.14 (`link_budget.py:590-615`), carrying ONE free constant kappa because P^N is unobservable.
kappa anchored at 8.394622e-10 (implies P_REF ~ 587 W) then **swept over 8 multipliers spanning 5 decades** —
single peak at m*=0.1 — so no constant choice can be blamed.

| arm (n=24 unless noted) | calibrated scalar | ho rate |
|---|---:|---:|
| GREEDY_R1R2 (best) | **+0.8750** +/- 0.0236 | 0.1412 |
| GREEDY_SCALARIZED | +0.8659 +/- 0.0232 | 0.1501 |
| MAX_NOMINAL_GAIN | -0.0866 +/- 0.0425 | 0.7115 |
| GREEDY_R1R3 (n=8) | -1.0587 | 0.9000 |
| RANDOM_MASKED (n=8, harness check) | -1.4037 | 0.8664 |
| **trained e6b063ef... last-100** | **+0.8859** +/- 0.0190 | **0.2490** |

Best arm delta = **-0.0109** vs last-100 (combined sem ~0.0303 -> not resolvable, point estimate BELOW);
**-0.0507** vs the 5-window plateau mean +0.9257 (ep 4000/6000/7000/8000/8900 windows: 0.9509/0.9259/0.9349/0.9311/0.8859
-> reference is stable, bounds the RNG-stream-position confound).
The n=8 pass had shown GREEDY_R1R2 at +0.8897 (above target); **that was noise and it reversed at n=24.**

Diagnostics as requested: **r2 carries it** (dropping it -> -1.0587, ho 0.90). **r3 does not**; its stale
t-1 prediction is mildly harmful — paired GREEDY_R1R2 - GREEDY_SCALARIZED = +0.0091, sem 0.0034 (~2.7 sem).
MAX_NOMINAL_GAIN's collapse confirmed to be r2: ho rate 0.7115 = 2.9x the learner's 0.2490.

**Realizability: all arms ARE observation-only realizable** (argmax over affine combos of blocks 1/2/4,
no realised fading, no future state, no other user's current-step choice). So this is an ABSENCE, not a
representability failure. Per instruction: no rescue proposed, search not widened. Design decision is the coordinator's.

## Pooled EE round (coordinator) — COMPLETE 2026-09-11

Appended `## Pooled EE — the declared primary endpoint`. Read-only, no `update()` call.
All detached probes confirmed finished (`ps` clean) before writing; nothing relaunched.

**HEADLINE: `MAX_NOMINAL_GAIN` 111,553,182.85 bit/J (3.267020e+14 bits / 2.928666e+06 J) vs
TRAINED `e6b063ef...` 93,137,893.02 bit/J (2.850357e+14 bits / 3.060363e+06 J) — ratio 1.1977,
delta +1.8415e+07 bit/J, 13.2 sem. => PRE-DECLARED BRANCH 2: the trained objective and the
declared primary objective DISAGREE. A finding about the objective, NOT a reopening of the
demonstration line.**

Estimand: two running totals over 24 ep x 10 steps, divided once. `dt = DECISION_STEP_S = 30.08 s`
(`constants.py:76`). Per-step bits/joules from the env's own `energy.system_throughput_bps` /
`system_consumed_power_w` via `env.last_outcome` (`trainer_env.py:239-248`,
`energy_efficiency.py:37-49`) — not reconstructed.
Numerator convention: **full-buffer Shannon, NO demand cap** (`link_budget.py:590-615` eq. 3.14;
`step.py:964-970`); grep for demand_cap|rate_target|nominal_rate|setpoint|target_rate|min_rate|qos_rate
over `src/mcrl/env/` = **0 hits**, so **rate attainment has no referent in this env** — served rate
reported instead.

| arm (n=24) | pooled bits | pooled joules | pooled EE bit/J | served | ho | scalar |
|---|---:|---:|---:|---:|---:|---:|
| MAX_NOMINAL_GAIN | 3.267020e+14 | 2.928666e+06 | **111,553,182.85** | 0.9981 | 0.7117 | -0.0867 |
| TRAINED e6b063ef (greedy) | 2.850357e+14 | 3.060363e+06 | **93,137,893.02** | 0.9988 | 0.2796 | +0.9063 |
| GREEDY_R1R2 | 2.612398e+14 | 3.445650e+06 | 75,817,283.47 | 0.9960 | 0.1413 | +0.8743 |
| GREEDY_SCALARIZED | 2.614246e+14 | 3.473047e+06 | 75,272,421.21 | 0.9961 | 0.1502 | +0.8649 |
| RANDOM_MASKED (harness check) | 1.842866e+14 | 3.473162e+06 | 53,060,175.56 | 0.9360 | 0.8680 | -1.4104 |

**No stream-position caveat this round**: the local `final-checkpoint.pt` sha256 = e6b063ef...1b09c28b,
byte-identical to the frozen artefact, so the trained arm ran at the SAME stream positions 0-23 as
every scripted arm. No proxy substituted.

Key separation: the estimand defect (episode-level mean-of-ratios vs ratio-of-sums) is <=0.06% and
changes no ordering. The rank flip is a **weighting disagreement** — pooled EE prices r1 only; the
trained objective prices 0.5 r1 + 0.3 r2 + 0.2 r3, and MAX_NOMINAL_GAIN's handover rate is 0.7117 vs
the learner's 0.2796. MAX_NOMINAL_GAIN moves from LAST on the scalar to FIRST on pooled EE, and wins
on both halves of the ratio at once (most bits AND fewest joules). No arm buys EE by dropping service.
The two GREEDY_* arms that won the trained objective are the WORST non-random arms on pooled EE.

Not widened, no arms added, nothing swept. Design decision is the coordinator's.

## Segment-anchor ablation round (coordinator) — COMPLETE 2026-09-11

Appended `## Segment-anchor ablation`. Read-only; `src/` never edited or import-time patched.

**HEADLINE: anchored ratio 1.1975 -> ablated ratio 1.2222. The gap DOES NOT COLLAPSE; it WIDENS 11.3%.
=> PRE-DECLARED BRANCH 2: the renewal premium is NOT the explanation; the disagreement is real,
size restated at +22.2%. The +19.8% anchored figure stands and is NOT withdrawn.**

Ablation reused, not invented: diag2's `ablate_anchor`, declared verbatim at
`.scratch/multi-catfish-v023-controller-handoff-20260907/prompts/codex-sol-c3s-churn-null.md:16`
("make recurrence_power_w return p0 = 0.825 W at every step and let the wanted signal use the
CURRENT transmit gain"). Implementation fetched read-only from sat:
`/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-c3s-screen/c3s_physics_override.py`
sha256 a534244755f1df55ebc12b96a67fce93fe34e91c9b7d886aef4ae6276378f03a (137 lines).
**It is written against THIS repo's `mcrl.env.step.StepEnvironment`, so it ports unchanged**; applied
via its own `DiagnosticStepEnvironment.construct` subclass factory. Only one ablation is specified,
so there was no choice to declare.

| physics | arm | pooled bits | pooled joules | pooled EE | served | ho |
|---|---|---:|---:|---:|---:|---:|
| none | MAX_NOMINAL_GAIN | 3.266731e+14 | 2.929683e+06 | 111,504,571.39 | 0.9981 | 0.7120 |
| none | TRAINED e6b063ef | 2.848622e+14 | 3.059385e+06 | 93,110,907.97 | 0.9988 | 0.2799 |
| none | GREEDY_R1R2 | 2.617496e+14 | 3.454818e+06 | 75,763,635.84 | 0.9955 | 0.1418 |
| none | RANDOM_MASKED | 1.842866e+14 | 3.473162e+06 | 53,060,175.56 | 0.9360 | 0.8680 |
| **ablate_anchor** | **MAX_NOMINAL_GAIN** | 3.262056e+14 | 2.896868e+06 | **112,606,306.11** | 1.0000 | 0.7105 |
| **ablate_anchor** | **TRAINED e6b063ef** | 2.845606e+14 | 3.088655e+06 | **92,130,894.38** | 1.0000 | 0.2825 |
| ablate_anchor | GREEDY_R1R2 | 2.549917e+14 | 3.408890e+06 | 74,801,972.37 | 1.0000 | 0.1389 |
| ablate_anchor | RANDOM_MASKED | 1.904807e+14 | 3.691411e+06 | 51,601,064.62 | 1.0000 | 0.8655 |

**Positive control (ablation took effect):** under ablate_anchor 100.0% of served users transmit at
exactly p0 = 0.825 W every step, both arms. Under `none`, MAX_NOMINAL_GAIN 70-76% at p0 vs TRAINED
only 4-5% (range up to 1.63 W) — **so the review's mechanism IS real**; removing it just doesn't
move the result.
**Placebo (wrapper transparent):** `none` reproduces RANDOM_MASKED bit-identically; MAX -0.044%,
TRAINED -0.029% (cause found and disclosed: `_age_rng` spawns once and carries across arms,
`step.py:534-536`, so the previous shared-env run gave later arms different segment-age draws;
this test builds a fresh env per cell so arms are exactly matched).

**Why it didn't move:** bits ratio MAX/TRAINED = 1.1468 anchored, **1.1463 ablated — invariant**.
The anchor lives entirely in the denominator (joules ratio 0.9576 -> 0.9379, which WIDENS).
The advantage is ~14.6% more delivered bits from pointing at the highest-gain legal beam, a property
of the decision rule. Per-arm ablation effect: MAX +0.99%, TRAINED -1.05%, R1R2 -1.27%, RANDOM -2.75%
— sign is OPPOSITE to the prediction. diag2's cited result stays correct on its own terms: forced
renewal at FIXED association is +0.49% -> exactly 0. MAX_NOMINAL_GAIN changes WHICH beam, not merely
when the anchor resets — that is what the extrapolation missed.

**Disclosed limit:** the ablation raises served to 1.0000 for every arm (p0 pinning removes power
infeasibility), so anchored vs ablated are two operating points, not a decomposition.

## Report written
`/home/u24/papers/mcrl-leo-handover/.scratch/catfish-surface/CATFISH-ATTACHMENT-SURFACE-2026-09-11.md`
Classification: **(b) bounded code, but at ~430-620 lines it is 1.5-2x the brief's ~300-line bar.**
Biggest failure reason: no demonstrator exists on the MODQN env at any budget.
