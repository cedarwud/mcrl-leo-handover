# Pre-declaration — the first training run, and how its result will be read

**2026-09-10 11:50 UTC. Written before the corpus is finished and before any learned arm
exists.** No sealed constant, threshold, sign, seed, horizon, price, guard or acceptance rule
is changed.

---

## 0. Why this run exists

**No production training run scored on the reported endpoint has ever happened in this
project.** Every EE figure quoted today is from an oracle or an exact search:

| figure | source | learner involved |
|---|---|---|
| `+0.899%` / `+0.717%` coordination band | exact joint vs exact unilateral fixed point | **none** |
| `+100.7%` acceleration headroom at 10 s | anytime **search** curve | **none** |
| `+1.93%` control law | non-causal best-known search | **none** |

The one measurement involving trained heads is `C3REACH`, which used four epoch-2000 `FULL`
lineages and reported pooled EE `36.63 -> 15.84` Mbit/J under the pilot's boundary-0 scoring —
**negative**, and in unresolved contradiction with `RESIDTOGGLE`. The r8 panel smoke was
**2 source epochs, 1 retained anchor**, and carries `smoke_test_not_evidence: true`.

**So the quantity every argument today has turned on — what a trained system actually does to
pooled EE against a reference that can separate arms — does not exist.** This run produces it.

## 1. Gate before the run — the rule I wrote on 2026-09-08 and violated twice

**No arm pair runs without a fixture on which the arms must produce different numbers.**
Before training, on a checked-in fixture, demonstrate that `FULL`, each `DROP_Ci` and
`ALL_NEUTRAL_CONTROL` **can** select differently and produce different pooled EE. Report
PASS/FAIL per pair. **A FAIL stops the run.** This gate exists because `MARGIN_Q` produced
eight contrasts identical to 16 significant digits, and the C2 arms in `FACTORIAL` produced
three byte-identical pairs, and neither had such a fixture.

## 2. The run

| | |
|---|---|
| corpus | the **exact-path** corpus from `EXACTGEN2` — declared targets, **not** the shipped surrogate rows |
| feature schema | state which of v1 / v2 is used, and its digest, in the receipt |
| arms | the sealed five: `FULL`, `DROP_C1`, `DROP_C2`, `DROP_C3`, `ALL_NEUTRAL_CONTROL` (`learner.py:28`) |
| epochs | **500**, checkpoint cadence **100** |
| head literals | the sealed ones, unchanged: C1 `(8,)` relu lr `1.0e-2` gauge_beta `0.2`; C2 `(100,50,50)` tanh lr `1.0e-3` gauge_beta `0.1`; C3 `(64,64)` relu lr `1.0e-3`; Adam `(0.9, 0.999)` |
| seeds | state the count actually run; the code default is 12 and amendment v1.1 requires 16 — **report which was used, do not silently take the default** |

**500, not 2000, because resume is bit-exact** (round-trip verified by `PROTOFORM`), so
continuation costs nothing and a first look is ~52 minutes rather than ~3.5 hours.

## 3. Scoring

- **Reference: `ALL_NEUTRAL_CONTROL`.** `BASE` is **not** a reference on this run and is never
  relabelled as one — the r8 receipt shows eight contrasts against `BASE` collapsing to four
  distinct values with every arm sharing one repair seed.
- **Numerator: the declared full-buffer decodable throughput** (declaration v1.8 item 5). **No
  demand cap.** A cap would be a versioned model amendment, not a reporting choice.
- **Contrasts, at every one of the five checkpoints:** `FULL - ALL_NEUTRAL_CONTROL` (primary),
  and `FULL - DROP_Ci` for each route.
- **Co-reported, per contract:** rate-target attainment, service availability, handover rate,
  and deadline-miss rate.
- **Panel:** small and stated before the run — anchors, worlds, seeds, and the exact anchor
  list, fixed in the launch receipt. **This is a signal, not a claim panel.** No result from
  this run is a claim about efficacy.

## 4. The continuation rule, fixed now

Continue past 500 **only** if the primary contrast is still **moving monotonically across the
five checkpoints**, i.e. not yet converged.

**This condition is about convergence, not direction.** If the contrast has flattened — at any
value, positive, zero or negative — the run stops at 500 and is reported as it stands. I will
not continue because a number is disappointing, and I will not stop because a number is
pleasing.

## 5. The reading, fixed now

- **`FULL - ALL_NEUTRAL_CONTROL` negative or zero at convergence**: the learned system does not
  beat neutral-source training on this corpus, schema and panel. That is the result. It is
  reported with the same detail as any other, and it does **not** license a further design
  change chosen to reverse it.
- **A route's `FULL - DROP_Ci` zero or negative**: reported as zero or negative. No ordering
  among routes is required.
- **A flat-zero contrast at 500 with no movement across checkpoints** is evidence the heads
  learned nothing usable on this corpus — a different finding from a converged negative, and
  reported as such.
- **Loss values are never evidence about EE**, in either direction, at any checkpoint.
- **Every reported number carries four fields**: reference, information class, estimand,
  numerator.

## 6. What this run cannot settle

- It is a **small panel**. It gives a sign and a magnitude, not an interval that meets the
  contract's decision bound.
- It measures the **current** decomposition. It says nothing about the two candidate
  replacements.
- It is on the **coordination axis**, not the acceleration axis pre-declared separately at
  11:40 UTC. Those two are never restated as one another.
- The `RESIDTOGGLE` / `C3REACH` sign contradiction remains open; `SIGNFORK` was killed and has
  not been re-run.

---

# AMENDMENT — one run, two axes. 2026-09-10 11:55 UTC, before the run.

**The coordination scoring and the acceleration scoring use the same checkpoints. They are one
training run, scored twice, not two runs.** Recording this as an amendment because I wrote them
as two separate pre-declarations an hour apart and did not notice they shared a training run
until the owner pressed on why I was not directing the work.

## The two scorings, from the same five checkpoints

| | axis A — coordination | axis B — acceleration |
|---|---|---|
| reference | `ALL_NEUTRAL_CONTROL` | `ALL_NEUTRAL_CONTROL`, **and** the anytime incumbent at the same budget, reported beside it |
| quantity | pooled EE | pooled EE **attained as a fraction of the certified fixed point's**, under the contract's **10 s** coordinator budget (contract v1 **F2**) |
| oracle ceiling | `+0.899%` (8 anchors) / `+0.717%` (30 dates) | `+100.7%` above the 10 s anytime incumbent (20-anchor panel) |
| numerator | declared full-buffer, no cap | declared full-buffer, no cap |
| contrasts | `FULL - ALL_NEUTRAL_CONTROL`; `FULL - DROP_Ci` | identical set, on recovered fraction |

**The owner's requirement is unchanged on both axes: each of C1, C2, C3 must raise EE.** What
differs is the reference the gain is measured against, and therefore how large a gain is even
available. The coordination axis has a measured oracle ceiling of about one per cent; the
acceleration axis has a measured oracle ceiling of about one hundred per cent. **Changing axis
is not changing the claim.**

## Two panel identities that must not be silently merged

The two oracle ceilings quoted above are **on different panels**: `+0.899%` is 8 anchors over
TLE dates `2025-07-28` and `2026-05-30`; `+100.7%` is the twenty-anchor anytime panel. They are
both relative pooled-EE gains, but against different references and on different anchor sets,
and **they may not be stacked into a single ladder** without a measurement on one common panel.

Related, and larger than the coordination band itself: search **traversal order** alone moves
the fixed point by `8.13%` (`SEALED`) and `1.62%` (`MARGIN_Q`) — first-improvement versus
best-improvement, on all 20 anchors, both rules
(`ANYTIME-UNILATERAL-2026-09-10.md:11`). **Which fixed point is the reference matters about
nine times more than the coordination gain above it.** Every reported figure names its fixed
point.

## Consequent requirement on the run

The launch receipt states, for each scoring: the reference object and its construction, the
information class, the estimand, the numerator, the panel identity (anchors, worlds, dates,
seeds), and the fixed-point traversal order. **A figure missing any of these is not reported.**
