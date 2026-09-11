# Ruling — the objective's mismatch with EE is structural, not an exchange rate

Date: 2026-09-11 ~01:05Z · Controller
Source: `ETA-EXCHANGE-RATE-2026-09-10.md` (`/home/sat/mcrl-v025-etafix-ws`), learner-free, parity
passed (41.62155981714534 / 31.028111070819413), raising `evaluate` stub with zero scalar calls
asserted, BASIN2's 31.812902 reproduced exactly at `eta_ref`.

## Established

- **In-force V0.25 `eta_ref` = `14235186615308645000000/1300834130903823` = 10.943122 Mbit/J.**
  The V0.23 value (124.08 Mbit/J) does not appear anywhere in V0.25.
- **No `eta >= 0` makes the exact-`F` order of the six clean non-learned arms equal their
  pooled-EE order, with or without `Phi`.** Without `Phi` the constraints `eta > 29.865312`
  (MYOPIC above FP) and `eta < 12.843834` (RANDOM above NEAREST) contradict; with `Phi`,
  RANDOM/NEAREST inverts at every `eta`. At least one pair is always inverted. **A single linear
  price cannot order configurations whose EE spans an order of magnitude.**
- Dinkelbach converges in one step, to `RSS_MAX` (41.621560).
- Correcting `eta` removes 92% of the pooled descent loss without `Phi` (9.81 -> 0.77 Mbit/J) and
  turns it into a +0.064394 (+0.155%) pooled rise with `Phi` — **but EE still falls at 9 of 12
  anchors under both definitions**; the pooled figure is a net of nine falls and three rises.
- **Two `F` definitions are in use**: `network_objective` without `Phi` (BASIN2, CLEANPATH,
  PANELCEIL, CEILING2) and with `Phi` (COORDVALUE). **`Phi`'s cost is 27-99% of pooled bits** — a
  first-order term that is not in EE.
- **Horizon mismatch**: `F` is scored at boundary 0; EE is realised over full-48. The descent
  endpoint has fewer bits (-3.03e10) **and** more energy (+11,297 J) over full-48 — no full-48
  price accepts it. At the best single boundary-0 price (~223 Mbit/J), 6,548/76,671 (8.5%) of
  move signs still disagree with EE; at full-48, at least 1,089.

## Corrections to my own earlier statements

- "`eta_ref` is ~11 and achievable is ~41, a 3.8x mis-set exchange rate, probably the cause" —
  **the cause is not the exchange rate.** Changing `eta` moves which pair is inverted.
- "The fixed point spends 2.35x the energy of `RSS_MAX`" — from a contaminated receipt; **clean
  figure 1.3170x**, same direction, about half the size.

## What this means for the design

The decision objective fails for **three separable reasons**, none fixable by a constant:

1. **It is a linear scalarisation of a ratio.** Ranking configurations by `B - eta*E` with one
   `eta` cannot reproduce ranking by `B/E` across an order of magnitude of EE. This is the
   concrete, measured instance of "fixed linear scalarisation is insufficient".
2. **It is scored on the wrong horizon** — boundary 0 for a commitment evaluated over 48.
3. **`Phi` is first-order and absent from the metric.** Up to 99% of pooled bits' worth of
   decision weight is spent on a preference the reported EE does not contain.

**Direction, to be designed and declared before it is measured (not adopted here):** a decision
score that is **ratio-consistent** (local Dinkelbach — price each decision at its own incumbent's
EE, iterated), scored on a **nominal full-commitment horizon** (geometry over the interval is
deployable; realised fading is not), with **`Phi` either given a physical justification or
removed** from the score. Note `ETAFIX`'s caution: pricing by each start's own realised full-48 EE
zeroes the mismatch only tautologically, because it is sorting by the metric; the deployable
version must use nominal, not realised, physics.

## Consequence for the owner's multi-objective framing

This **supports** the owner's proposed narrative — the three routes as distinct objectives traded
off to maximise EE — and constrains it: **the trade-off cannot be a fixed linear weighting.**
MODQN's fixed linear scalarisation of its three objectives is exactly the structure measured to
fail here. The combination must be ratio-consistent. `TRIOBJ` is testing both the decomposition
and the combination rule; it has been sent these findings.

## Re-measurement priced by ETAFIX (not authorised here)

Everything selected by `F` (MYOPIC, FP, PANELCEIL/CEILING2 ceilings, BASIN2, COORDVALUE Part 2)
and everything priced with `eta` (C1/C2/C3 labels, the exact-row corpus, `encode_c2_state`,
`reward_core`). The four direct-rule arms stand. A constant `eta*` is at least a versioned
successor (the sealed contract fixes `eta_ref = bits_ref/joules_ref` from two V025_CAL worlds);
an adaptive multiplier is a scientific redefinition.

**The route labels themselves are priced with `eta` and inherit this objective.** So the routes
have been learning targets built on a scalarisation that cannot order configurations by EE. That
is a candidate explanation for weak or negative route marginals that no amount of training fixes.
`SOLO` is measuring each route's target-to-EE correlation directly.
