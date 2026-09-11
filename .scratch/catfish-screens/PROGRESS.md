# CFSCREEN progress

Started 2026-09-11. Zero-training screens for the three candidate catfish sources.
**No MODQN training, no `update()`, no gradient step on any Q-network.** The only fitted
model is a behaviour-cloning probe (Q-network architecture used as a classifier), trained on
logged rule actions; it never touches the MODQN learner.
Output report: `CATFISH-SCREENS-2026-09-11.md` (this directory).

Local, `.venv/bin/python`, <=2 processes, `nice -n 16`, 1 BLAS thread, RSS < 5 GB.

## Harness provenance

- Rules + harness: `.scratch/feasible-frontier/scripts/frontier.py`
  (sha256 `74e03c30…32fc6`), **exec'd verbatim up to its main loop**, not reimplemented.
  Its `run()` is called directly; logging is a wrapper around the arm function.
- `c3s_physics_override.py` copied into `scripts/` (sha256 `a5342447…f03a`, identical to the
  scratchpad copy frontier.py imports).
- Checkpoint `artifacts/training-2026-08-25-rerun01/main/final-checkpoint.pt`
  sha256 `e6b063ef…1b09c28b` (re-checked this session).

## Steps

- [x] collect.py written (`scripts/collect.py`)
- [x] smoke (1 episode, A0/B2/TR) passed: self-query mismatch 0 for all three (learner
      greedy re-computation == `select_actions`); B2 smoke ho 0.486 = FEASFRONT's smoke; ~4.5 s/episode
- [x] 7 collection cells complete (A m=0, A m=2, A m=9, A m=12, B1, B2, TRAINED) + placebo vs frontier.out
      -> `raw/{A0,A2,A9,A12,B1,B2,TR}.npz/.json`, `raw/collect_{A,B}.out`.
      Placebo: pooled EE, bits, joules, ho, phi1, phi2, served, beams **bit-identical to frontier.out
      for all 7**. Calibrated scalar differs by -0.005..-0.016 in every arm: src commit c00aca3e
      (16:23, D-2 per-step outage floor) landed after frontier.out (15:58); scalar not used here.
      Self-query mismatch 0 in all 7 (incl. learner greedy recompute == select_actions).
- bc_probe.py written; launched 16:41 as two detached processes (A-tags; B1,B2,TR,NULL) -> `raw/bc_*.out`
- [x] Screen 1 representability (BC probe, 3-fold by episode): `raw/bc_*.{npz,json,pt}`, metrics in `raw/screens.out`.
      Declared 100-epoch recipe + z variant; 400-epoch sensitivity added after reading (best epochs were late) —
      unchanged (plateau). Info ceiling (`scripts/obs_reconstruct.py` -> `raw/obs_reconstruct.out`): every rule
      is an exact function of the encoded obs + mask, 24000/24000 for all six.
- [x] Screen 1b closed-loop rollout of the held-out probes (`scripts/bc_rollout.py`, raw variant)
      -> `raw/bcroll_raw.out`, `raw/bcroll_<TAG>_raw.json`; all 7 done (see entry below)
- [x] Screen 2 action disagreement (`scripts/screens.py` -> `raw/screens.out`, `raw/screens.json`)
- [x] Screen 3 state overlap (JSRL measure) + per-block (same)
- [x] Screen 4 margin scale (same)
- Side finding [V]: only episode 0 is paired across cells; ep>=1 t=0 snr/theta differ in 100% of rows
  (env_rng draws the episode start, trainer_env.py:178; fading draw count is action-dependent [I]).
- [x] Screen 1b closed-loop rollouts complete (all 7) -> `raw/bcroll_*_raw.json`, `raw/bcroll_raw.out`
- [x] Screen 5 C1/C2 split verdict
- [x] Report written: `CATFISH-SCREENS-2026-09-11.md`
- [x] (after resume message) TLE-archive provenance added to report header: run used the UNPINNED local
      archive (`MCRL_TLE_ROOT` unset [V]; bit-identical to frontier.out [V]; file_set `e07f3e1e…` vs pinned
      `427e6a91…` coordinator-reported). EE figures not comparable to pinned-archive results. No re-collection.

**CFSCREEN complete.** Nothing detached is still running.

## Sub-agents

This agent (CFSCREEN) spawned **no** sub-agents (no Agent/fork calls). The three `fork`
sub-agents the coordinator observed are not from CFSCREEN.

## Detached processes

- 2026-09-11 ~16:37 local: `setsid nohup nice -n 16 .venv/bin/python scripts/collect.py 24 A0,A2,A9,A12`
  PID 318073 -> `raw/collect_A.out`; `... collect.py 24 B1,B2,TR` PID 318074 -> `raw/collect_B.out`.
  cwd `.scratch/catfish-screens`. Idempotent: an existing `raw/<TAG>.npz` is skipped. ETA ~8 min.

## Intermediate numbers

Held-out top-1 (raw, 100 ep): A0 .8117, A2 .8377, A9 .9199, A12 .9353, B1 .7141, B2 .6829,
TR (pos ctrl) .8766, NULL .0382 (chance .0386). Best trivial: A0 max-gain 1.0 (definitional), A2 max-gain .8755,
A9 incumbent .7478, A12 incumbent .8144, B1 incumbent .6558, B2 incumbent .5973.
D within: C1 .124, C2 .093, C3 .052; across C1-C2 .448 (.350-.547); C1-C3 .556; C2-C3 .574.
R(1..9): within C1 1.15-1.17, within C2 1.17-1.20; C1->C2 1.31-1.37 (out95 .20-.31); C2->C1 1.16-1.17 (out95 .05).
Learner already picks source action: A0 .254 A2 .363 A9 .640 A12 .663 B1 .224 B2 .165.
