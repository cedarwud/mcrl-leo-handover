# Controller state — 2026-09-10 07:45 UTC

`DIAGNOSTIC_NOT_CLAIM` throughout. Nothing sealed was modified today. Every number below is
from a receipt on the server; every ceiling is labelled as one.

## The bar, as it now stands

`FULL - BASELINE` must be substantial. One or two routes contributing little is acceptable;
all three together amounting to little is not. Recorded with its timing in
`V025-CONTROLLER-REQUIREMENT-CHANGE-2026-09-10.md`, including that it was set after
`RESIDTOGGLE` reported `+5.62%`.

## Against that bar

**`FULLSPAN`, demand-capped, 8 anchors, worlds 1 and 2, exact terms:**

| contrast | gain |
|---|---:|
| `BASELINE -> ADDITIVE_ONLY` | **+10.80%** |
| `ADDITIVE_ONLY -> WITH_RESIDUAL` | **+5.62%** |
| **`BASELINE -> WITH_RESIDUAL`** | **+17.03%** |

Positive at 8/8 anchors, `+13.60%` to `+28.44%`. Served `452 -> 503`, attained `174 -> 192`.
Span decomposition: `81.04%` extra credited bits, `18.96%` reduced energy.

**This is a ceiling.** It hands the selector exact terms, not predictions. What learned heads
recover from it is unmeasured, and the one measurement of a learned head's scale
(`C3REACH`) found it one to two orders of magnitude too large.

**The additive component does not depend on the open contradiction below.** Even if the
residual is worth nothing, `+10.80%` stands.

## Open contradiction, unresolved

`RESIDTOGGLE`/`FULLSPAN` put the exact residual at `+5.62%` demand-capped. `C3REACH` puts it
at `30.82 -> 12.30 Mbit/J` on world 3 with energy nearly doubling. Both receipts are complete.
Four candidate explanations are on record; none established. `SIGNFORK` (dispatched 07:28,
pre-declared) runs a 2x2 over price and the `contexts` gate on one fixed world, anchor set and
catalogue to discriminate. `OBJMISMATCH` is independent evidence on the price half.

**Rule bound in `V025-CONTROLLER-OPEN-CONTRADICTION-RESIDUAL-SIGN-2026-09-10.md`: both numbers
travel together until a discriminating measurement resolves it.**

## Settled today

- **C3 is reachable.** `RESIDTOGGLE` 8/8 anchors differ; `C3REACH` exact `Psi` flips 14/20,
  learned 20/20, with 0/80 tie-break flips and 0/80 top-two within 1 ULP. The
  structural-inertness reading is dead by two independent routes.
- **The shipped corpus carries surrogate labels.** All 176,223 rows; the declared path is
  unreachable as sealed but executable. `EXACTGEN` is calibrating and generating.
- **The learned interaction head is badly scaled** — 2,518-11,205 against an additive spread
  of 107-264 at the same anchor.
- **`contexts` is `None` on 79.164%** of legal rows, so the residual can reorder about a fifth
  of a catalogue.
- **Assignment headroom survives the reporting numerator**: `9.8698%` (`SEALED`),
  `3.5590%` (`MARGIN_Q`), 768 replayed fields with 0 above 1 ULP.
- **Causal mode selection**: `+78.02%` demand-capped at `0 dB` stale-CQI, `+76.64%` at `-1 dB`
  with decode failure `25.79% -> 13.46%`, net of failures, identical joules to the bit.
- **Sealed checkpoint format admits** five learned arms, 2,000 epochs, cadence 100,
  round-trip verified; resume is bit-exact. 3,000/9,000 and eight arms fail.
- **Two reviewers converged** on a better-conditioned decomposition existing, from opposite
  starting positions, and both withdrew their earlier impossibility arguments after erratum 15.

## Errata raised today against my own work

15 — I gave both reviewers the wrong selector.
16 — my own panel spine specified a move set that would have sterilised C3.
Plus: the replay parity gate I wrote demanded bit-exactness that floating-point summation
cannot deliver; and a non-regression invariant I asserted to `FULLSPAN` was checked and found
false (39 of 800 user-anchors decrease).

## Running

`OBJMISMATCH` 3h45m · `CTRLCEIL` 3h58m (report already in hand, still working) ·
`C1REAL` 1h58m · `EXACTGEN` 53m · `CTRLCAP` 45m · `SIGNFORK` 16m

## Not authorised by anything today

Contract v2, corpus substitution, a panel, or any training run.
