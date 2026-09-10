# Pre-declaration — the gate that must pass before any training run

**2026-09-10, written BEFORE `FACTORIAL` and `C1REAL` report.** No sealed artefact, constant,
threshold, sign, seed, horizon, price, guard or acceptance rule is changed. This fixes the
condition for starting training while the deciding numbers do not yet exist.

## The wrong gate, and why I nearly used it

Earlier today I framed the training gate as: the corpus is real, and the sealed checkpoint
format can express the protocol. Both matter, but **neither is the gate.** The format
question is "can we write it down"; it says nothing about whether writing it down is worth
anything.

**The gate is the exact ceiling.** Every route's exact marginal is an upper bound on what a
learned head predicting that route can deliver: the exact term hands the selector the true
value, a head hands it an estimate. A route worth `x%` with exact terms is worth **at most**
`x%` with a head, and strictly less whenever the head errs.

Training before the exact marginals are known would measure a shortfall against an unknown
bound. That is the failure mode recorded earlier today — building a component before building
the contrast that gives it meaning.

## The gate

Training may be proposed only when **both** hold, and each is reported before the proposal:

**G1 — the exact marginals justify it.** `FACTORIAL` (dispatched 08:26 UTC) completes the
`2^3` factorial with exact terms on `FULLSPAN`'s catalogue, anchors, guard, tie-break,
provisioning, price and pooling, reporting `C1_ONLY`, `C2_ONLY`, `C3_ONLY`, the three `DROP`
arms, `FULL` and `BASELINE`, demand-capped. Against the owner's current bar — the three
together substantial, one or two contributing little acceptable — G1 passes when the joint
span is substantial **and** the report states plainly which single-route marginals are
positive and which are not. **No numerical pass mark is invented here; the magnitudes are
reported and the bar is the owner's.**

**G2 — the target is learnable.** `C1REAL` must show the ceiling on the declared target is
**architectural, not informational**. If a high-capacity model on the same 16 inputs also
fails, the limit is in the information, and no architecture, epoch count or seed repairs it.
**That conclusion is reachable without training and would make training pointless.**

## What happens under each outcome

- **G1 and G2 both pass** — propose five production arms, 500 epochs, cadence 100, on the
  exact corpus. That protocol is round-trip verified in the sealed format and resume is
  bit-exact. Its purpose is the one quantity nothing has measured: **how much of the exact
  ceiling a learned head recovers.** It is not the claim.
- **G1 passes, G2 fails** — do not train this decomposition. The targets change first; the two
  candidate replacements are already specified and their comparison metrics are pre-declared
  in `V025-CONTROLLER-PREDECLARATION-DECOMPOSITION-BAKEOFF-2026-09-10.md`.
- **G1 fails** — do not train. A ceiling that does not justify a head is not repaired by
  fitting one.
- **The residual-sign contradiction still unresolved when G1 reports** — `FACTORIAL`'s `C3`
  marginals are reported with both `RESIDTOGGLE`'s `+5.62%` and `C3REACH`'s `-60%` beside
  them, per the binding rule in
  `V025-CONTROLLER-OPEN-CONTRADICTION-RESIDUAL-SIGN-2026-09-10.md`. `SIGNFORK` is the
  discriminating measurement.

## What this gate is not

It is not a new scientific gate on any claim. It governs **whether to spend compute**, not
whether any hypothesis is accepted or rejected. No acceptance rule, threshold, sign or
estimand is created, moved or removed by it.

It also does not authorise contract v2, corpus substitution, or a panel. Those remain
separate and unauthorised.
