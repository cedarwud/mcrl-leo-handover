# Note — C2 is unmeasurable on a single-step endpoint; a prediction about the gain feature

Date: 2026-09-11 ~01:20Z · Controller

## C2 (from `C2-TARGET-VALUE-2026-09-10.md`, `/home/sat/mcrl-v025-c2target-ws`)

*Reference: exact-C1-only selection. Information class: learner-free oracle, 93 development
anchors (first 22 byte-identical to the 22-anchor corpus). Estimand: relative pooled-EE change.
Numerator: full-buffer.*

- Perfect oracle C2 added to exact C1 (additive, as the scorer does): **35.2347 -> 35.4734 Mbit/J,
  +0.68%, step-cluster 95% interval -3.60% to +5.73%**; 22-anchor subset **-2.10%**; worse at
  **20 of the 30** anchors where it changes the choice; per-anchor geometric mean **-1.39%**;
  the pooled positive comes almost entirely from four low-EE, high-energy anchors
  (006, 055, 056, 067). Served / attainment: C1-only 0.9858 / 0.2678, FULL 0.9871 / 0.2648.
- **Tie-break reading: exactly zero** — C1's maximum is unique at all 93 anchors.
- Not redundant with C1: argmax agreement 29.56%, Pearson ~0.42; C2 changes 34.20% of per-user
  choices. But when additive, **C2 dominates the choice** on the 30 changed anchors: C2 score
  median 154 kappa vs C1's forfeited median 16.7 kappa.

**The structural finding:** every endpoint is open-loop over step t's 48 boundaries; C2 declares
value at t+1..t+3. **No C2 marginal measured so far — learned or oracle — can be horizon value.**
`MULTISTEP` (dispatched 01:15Z) builds a continuation endpoint and re-runs the oracle-C2 test
with the marginal split into step-t and future-step parts.

**Residual C2 target: not adoptable yet.** A distinguishing test exists (time-segmented
attribution T1 + input-provenance ablation T2) but needs the multi-step endpoint.

## OWNER DECISION — C2 tie-break vs additive

Two sealed documents contradict each other: **priority declaration v1.6 §2 / v1.9 §5 say C2 enters
only as a tie-break; the stage-C contract and the implemented scorer add it.** Under tie-break,
C2's marginal is identically zero on these anchors. **This is the owner's call**, and every C2
number must state which reading it uses until it is made.

## Q1 v4 corpus (`Q1-SCHEMA-V4-2026-09-10.md`, `/home/sat/mcrl-v025-q1v4-ws`)

Ready to train: `both` width 19, digest `85fbcb42...`, C3 252, 93 anchors; subsets `none`
(= Q1 v2, 15/236), `gain_only` (= Q1 v3, 16/240), `congestion_only` (18/248), `both` (19/252),
each with its own digest, dry-run on the unmodified production runner. Three congestion fields
survived the derivability gate, seven rejected. **v2's two power fields are constant 1.0 on all
81,638 legal rows** — v2 carried no per-option power information at all.

## Pre-declared prediction, written before any gain-arm checkpoint exists

The candidate table is **constructed in decreasing-gain order** (slot 0 = reference, the
lowest-gain legal option; slots 1-8 by decreasing gain), so the gain field's cross-user Pearson
over 10-slot rows is **0.9958** (0.8897 without the null slot; rank agreement 1.0000).

**Prediction:** any head that relies on gain will show **high user-row Q collinearity** on the
`Q-ROW-COLLINEARITY` instrument. **This is predicted to be benign**, for the same reason MODQN's
slot-space concentration was: a shared preference for "my own best link" maps, through the
user-relative action encoding, to **different physical beams**. The test of benign-vs-pathological
is the **physical** concentration (`modal_frac`, active beams) and the EE, not the row correlation.
**If a gain arm shows high row collinearity AND physical collapse, the prediction is wrong.**
