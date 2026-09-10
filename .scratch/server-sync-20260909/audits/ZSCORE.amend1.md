# AMENDMENT 1 to ZSCORE — issued 2026-09-10T15:2xZ, BEFORE any result is known

**Read this before reporting. It adds two control arms. It changes nothing already specified.**

## The defect this fixes

As dispatched, ZSCORE widens Q1 `15 -> 30` and Q2 `22 -> 44`. That **doubles the first-layer
parameter count**. A difference between `[raw || z]` and the existing non-z runs therefore
confounds **the normalisation** with **the extra capacity**. As written, a positive result
cannot distinguish them, and neither can a negative one.

I am adding the controls now, before any number exists, so that the reading rule is fixed in
advance rather than argued after the fact.

## Two control views, FULL arm only

Build these with the same view-layer machinery, the same corpus, the same runner, the same
500 epochs / cadence 100 / 16 seeds. **Only the `FULL` arm is needed for each** — the controls
answer an input question, not an ablation question. That is 2 extra runs, not 10.

**Control A — `raw_dup` (capacity control).** The view is `[raw || raw]`: the second block is a
verbatim copy. Identical width, identical parameter count, **zero new information**. If
`[raw || z]` does not beat `raw_dup`, the gain is capacity, not normalisation.

**Control B — `z_perm` (cross-user-coupling control).** Compute `mu, sigma` the same way, but
over a **permuted grouping**: partition the users of each anchor into the same-sized groups
using a fixed stated seed that ignores the true anchor membership, or draw the statistics from
a different anchor's user set. The block is still a normalised block with the same marginal
shape; what is destroyed is that a user is normalised **against the users it is actually
competing with at that step**. If `[raw || z]` does not beat `z_perm`, the gain is not the
cross-user coupling.

State the exact permutation rule you implement, and its seed, in the report.

## Reading rule, fixed now

Report the four `FULL` runs side by side on the same axis: **non-z**, `raw_dup`, `z_perm`,
`[raw || z]`, at equal optimisation budget.

- `[raw||z]` above **both** controls -> the cross-user normalisation itself carries the gain.
- `[raw||z]` ~= `raw_dup` -> the gain is capacity. Say so.
- `[raw||z]` ~= `z_perm` > non-z -> the gain is having a normalised block at all, **not**
  cross-user coupling. Say so; this is a materially different claim.
- All four ~= -> the intervention does not transfer to this project.

**Report whichever of these the numbers give.** Do not soften the capacity outcome.

## One more constraint, from a result that landed after you were dispatched

`LR-CONVERGENCE-SWEEP-2026-09-10.md` (`/home/sat/mcrl-v025-c1c2-ws`) finds that **all 21
route-learning-rate cells fail a pre-declared convergence rule at 500 epochs**, and that the
runner takes **one full-batch Adam update per epoch** — so "500 epochs" is 500 gradient steps,
with loss still moving 6.89-8.96% between step 400 and 500.

Therefore: **every arm here is compared at equal, and unconverged, optimisation budget.** The
paired comparison remains valid. Any statement of the form "the converged difference is X" is
not. Add one sentence to your report saying which of your conclusions would change if the
horizon were longer, and which would not.

## Unchanged

Everything else in the original ZSCORE prompt stands, including Part 3's requirement to report
learned `a0` pooled EE against the four panel reference points and `modal_frac` / `active` /
`argmax_distinct` for the z run and the two existing non-z runs.
