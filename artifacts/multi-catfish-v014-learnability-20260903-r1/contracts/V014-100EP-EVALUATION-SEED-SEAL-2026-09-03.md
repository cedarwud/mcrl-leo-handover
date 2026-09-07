# V0.14 100-episode evaluation seed seal

Status: **FROZEN BEFORE LEARNER-GATE OUTCOME**

This additive seal fixes the next TRAIN-development physical evaluation seed
block before the V0.14 learner gate is complete. It neither modifies the
learnability contract nor authorizes evaluation by itself.

- paired evaluation seeds: every integer from `2026109001` through
  `2026109100`, inclusive (100 episodes)
- split: TRAIN-development only
- arms: `FULL`, `DROP_C1`, `DROP_C2`, `DROP_C3`, and independent `MAIN`
- route initializations: all three gate initializations at the single common
  deployment rung
- checkpoint receipt cadence: episode 100
- endpoint: pooled total bits divided by pooled total energy; service reported
  separately
- no TEST access, no learner update, no episode training, and no 9000-episode
  run

Before this seal, the seed pattern had no occurrence in `docs/`, `src/`,
`tests/`, or non-V0.14 `.scratch/` sources.

