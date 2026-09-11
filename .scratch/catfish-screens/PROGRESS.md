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

- [ ] collect.py written
- [ ] smoke (1 episode) passed
- [ ] 7 collection cells complete (A m=0, A m=2, A m=9, A m=12, B1, B2, TRAINED) + placebo vs frontier.out
- [ ] Screen 1 representability (BC probe, 3-fold by episode)
- [ ] Screen 1b closed-loop rollout of the held-out probes
- [ ] Screen 2 action disagreement
- [ ] Screen 3 state overlap (JSRL measure) + per-block
- [ ] Screen 4 margin scale
- [ ] Screen 5 C1/C2 split verdict
- [ ] Report written

## Detached processes

(none yet)

## Intermediate numbers

(none yet)
