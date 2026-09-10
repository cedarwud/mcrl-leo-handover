# Erratum 19 — the reference scale I corrected the record with is itself contaminated

Date: 2026-09-10 ~16:12Z · Controller
Source: `/home/sat/mcrl-v025-surface-ws/SELECTION-SURFACE-2026-09-10.md`

## What happened

At 15:30Z I issued erratum 18 saying a one-line rule beats the certified fixed point by
**3.099x**, and I built the afternoon's reasoning, a thesis section, and a memory rule on the
number **13.430253**.

`SURFACE` was dispatched to explain a 2.135x gap inside that table. It never got there: it
**stopped at its own parity gate**, because both published cells changed when `BASE` entered
through a fresh dense `evaluate_many` instead of a scalar `evaluate`.

| cell | published | fresh dense | parity |
|---|---:|---:|---|
| nominal / best / one sweep (`MYOPIC_GREEDY`) | 28.668530 | **31.078504** | **FAIL** |
| realised / first / converged (`FIRST_IMPROVEMENT_FP`) | 13.430253 | **31.028111** | **FAIL** |

**The 2.135x gap I was trying to explain becomes 1.0016x.** My selection-surface hypothesis —
that choosing on realised boundary-0 fading over-fits a transient — is **not established**; the
thing I was explaining was mostly an artefact.

**And the fixed point was barely a fixed point.** Clean path: it moved at **12/12 anchors,
4,210 moves, 9–14 passes**. As published: **2/12 anchors, 699 moves**. The contaminated `BASE`
made almost every improving move look non-improving.

## The mechanism was already on record

`EVALPATH-2026-09-10.md` says the evaluator **cache key omits field / path / boundary
semantics**, so a scalar-cached `BASE` can be compared against dense candidates, and it leaves
global path authority **UNDETERMINED**. I quoted that defect in erratum 17 this morning, wrote
"existing mixed-path S0 rows are invalid inputs", **and then spent the afternoon reasoning from
numbers produced on exactly that path.**

## What this does to STATICS

`STATIC-BASELINE-FAMILY-2026-09-10.md` passed both parity gates — 12/12 configuration IDs
against the sealed `PANELCEIL` receipt. **That parity faithfully reproduced the contamination.
It did not validate it.** Reproducing a contaminated number exactly is what a correct
reimplementation of a contaminated construction does.

**Provisionally, and pending `STATICS2`:**

- **Probably unaffected** — `RANDOM`, `ROUND_ROBIN`, `RSS_MAX`, `NEAREST_ELIGIBLE`. These are
  direct rules that never consult the objective, so they never build a selection evaluator.
  **This is an inference about code paths, not a verified fact, and `STATICS2` must confirm it
  arm by arm.**
- **Contaminated** — `MYOPIC_GREEDY` and `FIRST_IMPROVEMENT_FP`, the two search arms.

## What erratum 18 said, and what survives

| erratum 18 claim | status |
|---|---|
| `RSS_MAX` beats the certified fixed point by **3.099x** | **withdrawn** — computed against 13.430253. Against the clean 31.028111 the margin would be about **1.34x**, and even that is provisional until `STATICS2` re-measures every arm on one path. |
| The three ceilings are local to a ~1,159-row catalogue in a 5.18e144 space | **stands** — that is `KILLTRIAGE`'s structural finding about the builder, independent of evaluator path. |
| "At this operating point no learned method can be substantial" outruns its evidence | **stands** |
| `RANDOM` (11.233999) beats the geometric base (11.027760) | **provisional** — both are direct rules, but must be confirmed on the clean path |
| `ROUND_ROBIN` at 100 active beams is worst by 12.1x | **provisional**, same reason |

## The failure mode, stated plainly

**I found this defect, wrote it down, said it invalidates measurements — and then did not apply
it to the next measurement I commissioned.** `STATICS` was dispatched without an
evaluator-path requirement in its prompt. `SURFACE` had one only because I added
"use one fresh dense evaluator per selection comparison" to that prompt, and **that clause is
the only reason the contamination surfaced at all.**

The requirement now goes into **every** prompt that touches the evaluator, not into the ones I
happen to remember.

## Consequences applied

- `STATICS2` dispatched (16:09Z) to rebuild the whole six-arm family on a verified-clean path,
  reporting each arm published-vs-clean and stating which arms touch the selection evaluator.
- `.scratch/thesis-deltas/DELTA-CH5-COMPARISON-FAMILY-2026-09-10.md` marked **DO NOT USE**
  pending `STATICS2`.
- The memory rule "run non-learned baselines before measuring headroom" **stands and is
  strengthened**: run them, and run them on a declared evaluator path.
- One verified byproduct worth keeping: **the deployed selector uses nominal dense boundary 0.**
