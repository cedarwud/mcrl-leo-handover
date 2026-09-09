# Controller errata — everything I told the owner today that later measurement contradicted
Recorded 2026-09-10. Thirteen items. Each names what I said, what the evidence says, and what corrected it. `DIAGNOSTIC_NOT_CLAIM`.

## Physics and mechanism
**1. "The occupancy mechanism is novel."** I reported the first literature check's verdict that no paper reports consolidation beating spreading. True of that seven-paper corpus, but consolidation for energy is the standard answer in the wider network-energy literature — cell sleeping, cell DTX, cell zooming. *Corrected by my own knowledge, unprompted, after the owner asked whether I had used it.*

**2. "The interior occupancy optimum is caused by the discrete mode ladder."** A smooth model with no mode table at all produces an interior optimum at continuous occupancy **7.664**. The zero-fixed-cost test shows only that fixed costs are unnecessary. *Corrected by adversarial review.*

**3. "The efficiency-optimal partition moves with off-axis angle, so the owner's geometry requirement is satisfied."** With fixed costs removed there are **zero** angle switches and zero range switches out of 144 each, because geometry multiplies every amplifier cost by one common scalar. Seven of the eight remaining switches are the previous winner becoming infeasible against the cap. Geometry acts through **feasibility**, not efficiency. *Corrected by adversarial review.*

**4. "The square-root amplifier supply law is standard practice."** It appears **nowhere** in the twelve-paper corpus. It is a recognised model; it is not what this literature uses. *Corrected by the literature reading.*

## Numbers
**5. "Coordination headroom is +0.5448 %, and unilateral is +442 % over baseline."** Those came from an intermediate result file written at 17:29. The audited report written at 17:55 gives **+0.512537 %** and about +451 %. *Caught by an external round; source of the discrepancy identified afterwards.*

**6. "The split's condition number is 12."** The bound is **(|S|+|Ψ|)/|f| ≈ 23** for adversarial relative errors in both parts; my 12 was sensitivity to the additive part alone. And **on realised fits the amplification is 0.887, below one**, because the two components' errors correlate at −0.788 and cancel on 68 % of rows. *Corrected first by an external round, then by direct measurement.*

**7. "The interaction head's error of 50 exceeds the 40 being estimated, so no weighting saves it."** Invalid. An error of 50 can coexist with perfect ranking if it is a common pool offset; an error of 1 can be fatal if the top candidates differ by 0.1. The two figures also came from different measurements. The valid evidence is the argmax reversals. *Corrected by an external round.*

## Architecture and learning
**8. "The first head has no predictive value; held-out explained variance is negative."** That was a k-nearest-neighbour failure concentrated on one held-out step. Ridge reaches **+0.089** on the same split and beats the constant predictor on **10 of 10** leave-one-step-out folds, with a median of +0.180. The route has **zero** collision-bound variance. *Corrected by two independent estimator audits.*

**9. "The first two heads are target problems, and harder than the third."** The second head's target is **well posed**; its reviewer explicitly declined to redesign it. Only the first is `TARGET_REFORMULATE`. *Corrected by the target-design review.*

**10. "The selector's preference for the all-user coalition is a scale bias."** The exact winner **is** the all-user coalition at 26 of 30 held-out anchors. The oracle picks it too. *Corrected by the parametrisation comparison.*

**11. "Which half of the decomposition is to blame."** Not a well-formed question. Making either half exact makes the whole **much worse** — 9.04 and 9.65 against 3.62 — because it destroys the cancellation the other was fitted alongside. *Corrected by the parametrisation comparison.*

## Acceptance criteria
**12. "Three components each clearing +0.5 % out of a +0.51 % total is arithmetically impossible."** I had misread the owner's bar. Leave-one-out arms can fall **below** the unilateral fixed point, so their gaps are not bounded by the joint-search span. *Corrected by the owner.*

**13. "A full-minus-drop gap of +15.6 % is encouraging."** It is a **degeneracy signal**: since a ranker can add at most the joint-search span above the fixed point, any larger gap means the reference arm fell below it. *Corrected by the second design reviewer.*

## The pattern, stated plainly
Every one of these came from over-claiming on partial or single-source evidence, and every one was caught by adversarial review, independent replication, external reading, or the owner. Not one was caught by me reviewing my own reasoning.

The practical consequence for how my statements should be read: **a controller claim sourced from one model, one panel, or one intermediate file should be treated as a hypothesis until an independent line confirms it.** The findings that have survived all day are the ones with two independent sources — the provisioning defect, the pairwise decision reversals, and the comparator repair.

## Two repair obligations still owed
The code comment asserting that the beam-width constant retains a full half-power-beamwidth convention is **false**, now proved by substituting the source's own value into its own equation and obtaining exactly one half. It must be replaced with a declaration that the value is a chosen design parameter, together with an explicit statement of which convention the API stores. Separately, the claim that the ephemeris archive gives 124 times our usage is misleading; usable headroom is about 1.04 times.
