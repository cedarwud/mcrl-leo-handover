# V0.18 relational-ZR performance diagnosis

Date: 2026-09-04 (Asia/Taipei)

Scope: future source/learner preparation only.  The already-running sealed
V0.18 analytic panel continues with its authenticated server bytes; this issue
does not alter or reinterpret that outcome.

## Checkable completion criterion

On the existing three-user W173 synthetic fixture:

1. `check_nominal_call_budget.py` must change from its observed deterministic
   `FAIL full_network_interference_calls=11 budget=1` to PASS;
2. optimized nominal `delta` and `q3`, plus every relational observation
   tensor and mask, must be element-for-element equivalent to an independent
   retained reference implementation (float comparisons use a predeclared
   tolerance only where operation ordering changes);
3. W173--W176 and the full V0.18 dependency test set must remain green; and
4. a 100-user benchmark must demonstrate the wall-time reduction before the
   optimized code enters a new frozen contract.

## Reproduction and profile

Fast red loop:

```text
env PYTHONPATH=src .venv/bin/python \
  .scratch/multi-catfish-v018-relational-zr/perf/check_nominal_call_budget.py
FAIL full_network_interference_calls=11 budget=1
```

The isolated W173 nominal-surface test takes about 0.06 s for only three users.
A cProfile run attributes about 0.056/0.061 s of the public surface to eleven
calls of `_nominal_interference`.  This is the same code path used by the live
100-user runner.  On the server, the first 18 V0.18 shards were all runnable at
about one CPU core each with no I/O wait or swap-in/out, yet no shard had
finished after more than 17 minutes.  That rules out a deadlock, I/O stall, and
memory pressure as the primary explanation.

## Ranked falsifiable hypotheses

1. **Per-branch full-network rebuild.**  If this is primary, replacing
   `1 + sum(legal actions)` full interference reconstructions with one cached
   reference construction plus updates for the origin/candidate physical beam
   will make the red call-budget loop pass and dominate the speedup.
2. **Cross-public-call duplication.**  If important, a shared immutable
   nominal-anchor cache consumed by both the encoder and nominal surface will
   approximately halve repeated predecision work without changing arrays.
3. **Repeated physical coupling.**  If important, caching each physical
   beam-to-victim geometry/gain/path coefficient once per anchor will sharply
   reduce `transmit_gain_linear`, `look_angles`, and `link_power_factor` call
   counts while keeping the reference implementation numerically equivalent.
4. **Object/list churn.**  If important after 1--3, profiling the optimized
   path will still show `_branch_actions`, `_branch_keys`, and Python list/dict
   construction as material.  It is not the first fix.

No approximate fading model, reduced user set, reduced legal-action set, or
changed ZR formula is an acceptable performance fix.

## Local optimization checkpoint

The first two exact-cache changes are implemented locally but are deliberately
not synced into the already-running sealed panel:

- `check_nominal_call_budget.py` now reports
  `PASS full_network_interference_calls=1 budget=1`;
- W177 retains the original branch-by-branch implementation and verifies both
  nominal `(delta, q3)` and the encoder's interference-shift token against it;
- the encoder and nominal surface each build full-network interference once;
- W173--W177 report 44 passing tests, including an interleaved-anchor
  no-stale-state check; W140, W141, and W148 bring the focused cross-module
  total to 57; and
- on the small deterministic W173 fixture, median nominal-surface time changed
  from 0.052944 s to 0.024876 s (2.128x).  This is diagnostic only; criterion 4
  still requires the 100-user benchmark before reuse in a frozen run.

The 100-user checkpoint subsequently used the first already-declared V0.18
TRAIN world only to construct its initial predecision anchor; it executed no
action, exact teacher, learner, or TEST path.  The full 2,800-action cached
surface completed in 11.547 s and the cached encoder in 13.031 s.  Sixteen
branches spanning users 0, 1, 2, 10, 25, 50, 75, and 99 were recomputed with
the retained full-network reference; every non-focal rate and interference
entry agreed at the predeclared tolerances.  Those reference branches took
36.362 s, projecting to 6,363 s for a full legacy surface (projection, not an
observed completion); a separate full legacy attempt was interrupted after
more than three minutes without completing.  This establishes a real
100-user semantic differential plus a conservative large wall-time gap.  It
does not constitute C3 efficacy evidence.
