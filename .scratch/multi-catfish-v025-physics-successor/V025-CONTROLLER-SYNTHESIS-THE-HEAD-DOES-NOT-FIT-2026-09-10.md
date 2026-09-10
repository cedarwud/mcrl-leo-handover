# Synthesis — three independent lines say the sealed head does not fit, and two "route is dead" readings depend on it

Date: 2026-09-10 ~16:26Z · Controller
**Cross-report synthesis. No single job could see this; each saw one line.**

## The three lines

**1. No learning rate converges.** `LR-CONVERGENCE-SWEEP-2026-09-10.md`, under a rule fixed
before it ran and computing no EE: **21 of 21** route x constant-lr cells fail at 500
full-batch updates; none of `1e-2` (C1), `1e-3` (C2), `1e-3` (C3) is admissible.

**2. No horizon and no batching fixes it.** `HORIZON-LEVER-2026-09-10.md`, same rule, 4,000-update
cap: full-batch `NONE`, minibatch `NONE`, and no minibatch advantage at equal wall time either.
Full-batch at the cap passes held-out R2, ordering and top-1 but fails the objective-motion
tolerance at **2.961%**, decaying with oscillation.

**3. The sealed head loses to plain linear regression.** Not once, and not on a broken schema:

| route | sealed head | plain linear | gap |
|---|---:|---:|---:|
| C2, Q1-v2 schema, LOAO ordering | 0.5131 | **0.6605** | **−0.1474** |
| C2, widened `(128,64,64)` | 0.5648 | 0.6605 | −0.0957 |
| C2, **repaired Q2-v2** (4 slots replaced, elevation added) | 0.5531 | **0.6477** | **−0.0946** |
| C1, level R2 | −0.272 | **−0.1506** | linear better |
| C1, high-capacity `16-256-256` random-feature ridge | — | **R2 +0.0933, ordering 0.6197** | best observed |

## What this does to two recorded conclusions

**A head that loses to plain linear on the same features has established nothing about the
target.** Linear regression is a head. If linear extracts more, the target carries more signal
than the sealed head reports.

- **C2's headline — "the declared C2 target must change rather than the features" — does not
  follow.** `Q2-SCHEMA-V2-AND-RETEST` is careful and says "the target **or the head**"; the
  earlier `C2-DECLARED-TARGET-LEARNABILITY-V2` headline foreclosed the head. **The honest
  statement is the disjunction, and lines 1 and 2 make the head branch the live one.**
- **C1's "the observed ceiling looks predominantly informational"** is weakened by its own
  body: a high-capacity fit on the same 16 slots reaches R2 `+0.0933` where the sealed head sits
  at `−0.272`. The report labels this an "architectural/optimization penalty" — lines 1 and 2
  now give that penalty a measured cause.

**Neither route is thereby alive.** C1's best observed R2 is `0.0933`, which is low in absolute
terms. The claim here is narrower and it is about *attribution*: **these were read as
information ceilings, and at least part of what was measured is a head that does not fit.**

## The preflight that was missing

**Before any declared target is called unlearnable, the head must be shown to fit at all.** The
cheapest sufficient check is the one already sitting in these reports: **does it beat plain
linear on the same features?** For C2 it does not, across three schema variants.

This is the same shape as the other preflights missed today — the arm-difference check
(`SCALE`), the evaluator-path declaration (`SURFACE`), the width derivation (`PANELFIX`). In
every case the information needed was cheap and the omission surfaced late.

## Sequencing — no new dispatch

`DECAY` is already testing the third lever, a decaying learning rate, against the **unchanged**
pre-declared rule. The residual shape in line 2 — held-out metrics stable, objective decaying
but oscillating — is the standard signature that lever addresses.

- If `DECAY` reaches admissibility, the C1 and C2 learnability screens must be **re-run on a
  converged head** before any target is called unlearnable.
- If all three levers return `NONE`, the problem is the **objective or the architecture**, and
  the sealed `(100,50,50)` / `(64,64)` heads losing to linear is then the primary evidence, not
  a footnote.

**Do not re-run the learnability screens before `DECAY` reports.** Re-running them now would
measure the same non-fitting head again.

## What is not claimed here

No EE quantity appears in any of the three lines. Loss values and held-out metrics are
convergence and fit diagnostics only. Nothing here says any route raises EE, and nothing here
overturns a kill — `KILLTRIAGE` buckets both C1 and C2 declared-target screens as **M**
(mechanism), and this synthesis does not move them; it questions which mechanism.
