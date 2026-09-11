# Amendment 3 — catfish sources as pre-generated pools, not streaming environments

Date: 2026-09-11. **Pre-result** (the 10:25 launch was stopped at 10:40 and is not a result; the fresh
launch has not happened). Owner asked why the available speed-up was not being used. It should be.

## Why this is equivalent for this pilot

The three sources (C1 `A m=2dB`, C2 `A m=12dB`, C3 `B1_NO_NEW_BEAM`) and the three NULL3 sources (uniform
random legal) are **fixed scripted policies**: their transitions do not depend on the learner at all.
Streaming them in parallel environment copies during training only decides *which* source episodes fill
each 50,000-row FIFO; it does not change their distribution (episodes start at i.i.d. epochs).

And the learner only ever draws **5 rows per source per update × ~10,000 updates ≈ 50,000 rows per source per
run**. A pre-generated pool of ≥ 100,000 transitions per source therefore supplies everything the streaming
version would, from the same distribution. It is also the DQfD-family convention (demonstrations collected
before training).

## What changes

- **Before training**, for every training seed and every source of A2 and A3, roll the source in its own
  environment for **100 episodes** (100 users x 10 steps x 100 = 100,000 transitions), on a **pool seed range
  disjoint from training, calibration and evaluation seeds**, pinned TLE archive, raw `(B, E, H)` stored.
  Generation runs in parallel across spare cores before launch.
- During training, each source buffer is **loaded once with its pool and never appended**; minibatch rows
  sampled uniformly from it. Composition unchanged: 113 main + 5 per source = 128.
- A2 and A3 pools are generated identically (same sizes, same pool-seed schedule), differing only in the
  source policy.

## The one behavioural difference, declared

With streaming, source buffers start empty and fill over the first ~50 episodes; with pools, **source rows are
available from the first update**. Early learning may therefore differ from the streaming design. This applies
equally to A2 and A3, so the A2-vs-A3 comparison is unaffected in kind; the A2-vs-A1 comparison now includes
source data from episode 0.

## Expected effect

A2/A3 per-episode cost falls from ~6.6 s to about A1's ~1.7-2 s (no extra environments during training), so
the pilot's wall time is set by all arms at A1 speed plus pool generation (~10 minutes, parallel).

## Checks before launch

Tests: pool size and seed range as declared and disjoint from training/calibration/evaluation seeds; batch
composition still 113:5:5:5; loading a pool does not touch the main environment's RNG; A1 and A2 main rollouts
bit-identical before the first source sample; A2 and A3 pools identical except in policy. A short
fresh-context agy review of **this diff only**. Everything else in the declaration and Amendments 1-2 stands.
