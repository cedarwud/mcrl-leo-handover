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

## Report written
`/home/u24/papers/mcrl-leo-handover/.scratch/catfish-surface/CATFISH-ATTACHMENT-SURFACE-2026-09-11.md`
Classification: **(b) bounded code, but at ~430-620 lines it is 1.5-2x the brief's ~300-line bar.**
Biggest failure reason: no demonstrator exists on the MODQN env at any budget.
