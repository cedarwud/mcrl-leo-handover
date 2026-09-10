# §C3 panel — the design decisions that can be fixed now, and the two that wait
Recorded 2026-09-10, before the panel exists and before any source-training contrast has been measured. `DIAGNOSTIC_NOT_CLAIM`. Nothing here changes an arm definition, a source, a target, a price, a guard or an acceptance criterion; it fixes construction and reporting.

## Fixed now

**Arms — nine, plus the external control.** The sealed six: the full arm, three leave-one-out arms by neutral-source substitution with all heads retained and deployed, the all-neutral control, and the external geometry-only baseline. Plus the three single-informative arms the owner's requirement needs and the contract lacks. The leave-one-in contrast is half the requirement; without those arms that half cannot be evaluated.

**Construction — each arm keeps its own seed and catalogue.** A measured probe found **zero** intersection between the full arm's and the first drop arm's catalogues at every anchor tested, so a shared catalogue is unsound the moment arms carry their own learned seeds. Instead a **shared physical cache** evaluates each configuration once per identical physical context, and for the one-step pooled comparison only the **union of chosen configurations** is realised — at most nine outcomes per anchor. Cached realised outcomes must never leak into selection, and cache keys bind tape, world, time, physical and run settings, evaluator identity, the nominal-versus-realised field, the boundary set and the prefix history; raw configuration identifiers are insufficient because base identifiers embed carrier names.

**Local search — one for every arm, and it is first-improvement.** Accepting the first strict improvement reaches a different and better fixed point than completing a best-improvement sweep, on all twenty anchors under both provisioning rules, at 8.13 % and 1.62 % higher pooled efficiency. This is a search-order choice rather than a physics change, it was found while measuring something else, and it is better for every arm equally, so declaring it is not outcome-selection. **It must be stated in the panel's declaration, because the same neighbourhood with a different traversal order reaches a different local optimum.**

**Reading — the degeneracy screen already pre-declared.** Below-reference is decided by exact sign against the head-independent certified fixed point; every contrast reports both the all-anchor marginal and the marginal over anchors where every arm in the contrast is at or above reference.

**An asymmetry that must appear in the results table.** Dropping the third route changes **zero** proposed assignments at every anchor tested; dropping the first changes 12 to 26 and the second 29 to 69. The third route's ablation acts through ranking alone, the first two also move the proposal. A table that does not say so invites the reader to assume the three are mechanistically alike.

**Seeds.** For a paired ordering test the learner seed is a nuisance replicate and the cluster is date by seed; with many dates most variance is across worlds. Three to five seeds are enough for the ordering on the added arms; the full seed count is reserved for the full arm and the three leave-one-out arms.

## Run under both provisioning rules
The provisioning decision is unresolved and is blocked on framing rather than evidence. **The panel does not have to wait for it.** The adjudication's own conditions already require publishing both rules, so running every arm under both discharges that condition and removes the dependency. It costs twice, and that is the honest price of not prejudging a decision that is not mine.

Running only under the sealed rule would measure the routes on a model that credits nothing on three quarters of its transmissions. Running only under the corrected rule would enact an unauthorised change to declared physics. Both is the only option that is neither.

## What waits, and on what
- **Row-building path.** Whether rows are built through the exact path or the surrogate is being costed now. The surrogate writes geometric legality into both the validity and survival fields and is wrong on 822 of 1,784 rows; a cheaper option that changes a label is not acceptable at any price.
- **Anchor and date allocation.** Waits on the same cost measurement.

## Standing
No panel is authorised by this note and no run is started. It exists so that the construction is fixed before any number exists, and so that a later reader can see which choices preceded the results.
