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

## Report written
`/home/u24/papers/mcrl-leo-handover/.scratch/catfish-surface/CATFISH-ATTACHMENT-SURFACE-2026-09-11.md`
Classification: **(b) bounded code, but at ~430-620 lines it is 1.5-2x the brief's ~300-line bar.**
Biggest failure reason: no demonstrator exists on the MODQN env at any budget.
