# Controller finding — the load-regime hypothesis was mine, and it is false
Recorded 2026-09-10 from the load-regime sweep. `DIAGNOSTIC_NOT_CLAIM`. The sealed per-user rate remains 50 Mbit/s; every row is a separate evaluation on a copied run setting and no sealed constant was changed.

## The hypothesis I proposed, and where it came from
When the owner asked whether I had used my own knowledge rather than only the papers, I offered this: the joint-over-unilateral gap is small in the current setting because the system is lightly loaded in the relevant sense, and the price-of-anarchy literature says such gaps concentrate in **constrained** regimes. I argued that offered load and the per-user rate target were a cleaner axis than antenna width, because moving them carries no "you chose a favourable antenna" objection.

**On this system it is false.**

## What was measured
Load axis at the sealed rate, corrected provisioning:

| users | joint over unilateral | negative anchors |
|---:|---:|---:|
| 100 | **−0.287 %** | 2/8 |
| 125 | +0.066 % | 3/8 |
| 150 | +0.581 % | 1/8 |
| 200 | +0.296 % | 1/8 |

Non-monotone and uniformly small. Pushing both axes together gives +0.400 %, +0.644 % and +0.978 % — the last on four anchors rather than eight — and **never crosses one per cent**. Under the sealed rule the joint sequence is also non-monotone: +3.116 %, +1.596 %, +2.661 %.

The rate axis spanned required spectral efficiencies of roughly 0.84 to 3.36 bit/s/Hz at a representative occupancy of seven, against a table maximum near 3.71. So the sweep did reach the constrained end of the ladder, and the gap did not open there.

## A calibration fact worth keeping
On the common eight-anchor subset the current operating point reads **−0.287 %**, where the twenty-anchor strict receipt reads **+0.513 %**. The report is explicit that this is a **sampling distinction, not a changed operating point** — the eight rows match the archived anchors exactly.

**Eight-anchor panels read systematically lower than the twenty-anchor panel here.** That matters for reading the five-width beam curve, which is also an eight-anchor panel.

## What this closes
Every exploratory direction on the coordination side is now measured and closed: the deadline comparator, removing the non-learned prefix, reparametrising the score, and now offered load and the rate target. The remaining axis is antenna width, and the provisioning adjudication has already ruled that the sealed width must be frozen for that comparison and that any antenna change requires its own separate design decision.

**The coordination span is what it is: small, positive, around one per cent. No regime was found that enlarges it.**

## What it does not touch
The owner's requirement is the §C3 source-training contrast, whose arms are compared with each other. Its marginals are not bounded by this span, because a leave-one-out arm can select worse than its own fallback. Nothing measured here bears on it, and it has still never been run at scale.
