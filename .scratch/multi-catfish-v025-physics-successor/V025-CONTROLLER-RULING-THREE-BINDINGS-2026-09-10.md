# Ruling — the three route bindings, and two proposals I am not adopting as written

Date: 2026-09-10 ~17:40Z · Controller
Source: `APPROACHING-THE-INSTRUMENTS-2026-09-10.md` (`/home/sat/mcrl-v025-approach-ws`),
verified over **all 16** `FULL` epoch-500 checkpoints, 12 development anchors, with the
evaluator rule asserted in code (scalar `evaluate` replaced by a raising stub, **zero** calls,
24/24 assertions passed, instrument endpoints reproduced to `rel_tol=1e-12`).

## The findings I accept as established

1. **Neither Q1 v2 nor Q2 v2 carries per-legal-option `nominal_gain`, nor primitives sufficient
   to reconstruct it.** The physical RSS action is present in **1,200/1,200** user-anchor action
   tables. The action is available; the value that would rank it is not.
2. **Median `a0`-to-`RSS_MAX` Hamming distance is 92.5 of 100 users.**
3. **Against `RSS_MAX`, every differing learned choice has lower nominal gain.** Systematic, not
   a tie-breaking effect.
4. **Against the crowded endpoint, 99.13% of differing learned choices land on a less-occupied
   beam**, and that endpoint differs on a median 93 users — far outside a catalogue that is
   98.13% `|A| <= 2`.
5. **Bindings: C1 = features, C2 = target, C3 = candidates. Optimisation is secondary but real
   in all three** (the sealed head loses to plain linear on level calibration in every route).

## C1 — ADOPT the feature addition, as a successor

Add one per-legal-option `decision_boundary_log_nominal_gain_db` scalar to the Q1 action row.

**Why this is not handing the head the answer.** `RSS_MAX` is a demand-blind greedy. A head
that can see gain is *able* to reproduce it but is not obliged to; the whole point of a learned
method is to use gain where gain decides and to deviate where demand, occupancy or interaction
decide. Removing a blindfold is not the same as supplying a policy.

**What I will not claim.** I have no evidence that the omission was an oversight rather than a
design choice, and I am not asserting it was. The schema carries other quantities; it does not
carry this one. That is the whole finding.

**Consequence, declared:** a new Q1 schema width and digest, a new corpus, new checkpoints, and
therefore a **successor learned arm**. The sealed five-arm inventory is **not** mutated in
place. `C3 = 1 + 2*(2*Q1 + 6) + 4*7 + (32*4 + 1) + 6` moves with Q1, and the derivation is
enforced fail-closed.

## C2 — HOLD, with a stated objection to the proposal as written

Proposed: redefine the label as *incremental future value after conditioning on / subtracting
the current-slot C1 contribution*.

**The objection.** Defining C2's target as "the residual C1 did not capture" puts the
decomposition into the structure where **a positive C2 marginal is least informative**, because
the target is constructed to be whatever the other route missed. It is not guaranteed positive
— the residual may be unlearnable or worth nothing in EE — but if it comes out positive I would
be unable to distinguish "C2 carries real horizon value" from "C2 fits C1's leftovers".

**This is not a rejection.** The report's sequencing argument is sound: while C1 cannot see
gain, C2's absolute persistence label is partly spent re-deriving the current choice, and the
two routes compete instead of composing.

**Ruling: hold C2's redefinition until C1's feature change has been made and measured.** Then
decide with the residual's actual size in view, and **declare in advance how a positive C2
marginal under a residual target would be distinguished from construction** — before that
number exists. If no such distinction can be stated, the redefinition is not adopted.

## C3 — ADOPT in principle, but not before `CEILING2` reports

Proposed: add one deterministic whole-profile `RSS_MAX` proposal to the bounded catalogue.

**Why it survives the obvious objection.** The row is offered to **every** arm, including
`DROP_C3` and `ALL_NEUTRAL_CONTROL`. It raises the floor for all of them, so the `FULL` minus
`DROP_C3` contrast still isolates C3's contribution rather than measuring the row. Putting a
known-good profile on the menu is not the same as putting it in one arm's pocket.

**What it does change, and must be reported:** the meaning of every ceiling computed over that
catalogue. A "coordination ceiling" measured with an `RSS_MAX` row present is a different
quantity from one measured without it, and the two must never be compared.

**Ruling: hold until `CEILING2` reports.** Its Part 2 is already sweeping catalogue coalition
support (`|A| <= 1, 2, 3, 4, 6`). If the ceiling **saturates** at `|A| = 2`, the candidate set
is not C3's binding constraint and this proposal is answering the wrong question. If it keeps
rising, add the row **and** report the support sweep beside it, since a single hand-chosen
profile and a genuinely wider support are different claims.

## Optimisation — a control, not a fix

After each binding is released, the **first** thing run is a calibrated linear head on the same
features, as the report recommends. The sealed head currently loses to plain linear on level
calibration in all three routes; until a change beats that control, "the head learned it" is
not established.

**A calibrated linear control cannot create absent gain information or absent configurations.**
So it is a control on the optimisation claim only, never a substitute for the feature or
candidate change.

## Sequence

1. **C1's feature addition** — the largest lever and the prerequisite for C2's question being
   well-posed. Held only until `EXACTTRAIN2` proves the exact-corpus path end to end, so the
   new corpus is built once on a proven pipeline rather than twice.
2. **`CEILING2` reports** → then rule on C3's catalogue row.
3. **C2's target** — last, and only with a pre-declared test that separates real horizon value
   from residual fitting.

## Every one of these creates a successor arm

None mutates the sealed five-arm inventory. Each is an owner-visible declared design change
with new schema digests, new corpora and new checkpoints, and each is recorded before it is
measured. The current five arms remain exactly as sealed, and the runs already completed
against them remain valid for what they measured.
