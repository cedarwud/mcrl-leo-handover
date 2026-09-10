# Round 18 — Is a one-per-cent gap between a converged equilibrium and the coordinated optimum normal, and how is a mid-project model defect disclosed?

Two questions. The first is load-bearing for how a result is presented; the second decides how a correction is written up. Please answer from the literature with citations I can look up, and mark clearly where you are inferring rather than citing.

---

## Question 1 — the size of the equilibrium-to-optimum gap

### The setup, stated without domain detail

A set of users must each be assigned to one of several serving resources. The objective is a global ratio: total delivered bits over total consumed joules. Resources are **coupled** in two ways: users sharing one resource divide its airtime equally, so an additional occupant raises the transmission rate every occupant must sustain; and resources on the same frequency interfere, so one user's transmit power raises the interference seen by others.

Two solutions are compared on identical instances:

- **Unilateral**: iterated exact best response over single-user reassignments, run to a certified fixed point at which **no single user can improve the global objective by moving alone**. This is a Nash equilibrium of the association game under a common objective.
- **Coordinated**: a bounded search over *simultaneous multi-user* reassignments, seeded from that fixed point and ranked by exact evaluation.

### The measurement

On twenty anchors, both arms built from the same local search, the coordinated arm improves on the unilateral fixed point by **+1.29 %** in the pooled objective under corrected physics, and **+4.60 %** under an earlier variant. On a thirty-date panel the corrected figure is **+0.72 %** with a 95 % interval of [+0.44 %, +1.00 %]. On an eight-anchor panel at the current design point it is **+0.90 %**.

Attempts to enlarge it all failed. Offered load was pushed from 100 to 200 users and the per-user rate target from 20 to 80 Mbit/s — which drives the required spectral efficiency from 0.84 to 3.36 against a modulation table maximum of 3.71, so the constrained end of the ladder was reached. The gap stayed under one per cent throughout and was **non-monotone** in both axes. Widening the antenna beam raises it, but only by degrading service.

### What I want to know

**Q1a.** Is a gap of order one per cent between a converged unilateral equilibrium and a coordinated optimum **typical** for user-association or load-balancing problems of this kind, or is it unusually small? What magnitudes does the literature actually report, and for what objectives?

**Q1b.** Is *price of anarchy* the right frame? Our equilibrium is defined against a **common global objective** rather than individual utilities, so each user's "best response" already optimises the social objective. Does that make this a price-of-anarchy quantity at all, or something else — a *locality gap*, a *neighbourhood gap*, the gap between a local and a global optimum of one combinatorial problem? Name it correctly and cite the convention.

**Q1c.** Are there known bounds? For submodular or matroid-constrained assignment, local search over single-element moves has classical approximation guarantees. Do any apply here, and what would they predict for the size of the gap?

**Q1d.** When *is* the gap large? Which structural properties of an assignment problem make simultaneous multi-agent moves worth substantially more than iterated single-agent moves — and do coupled interference and equal-share resource division count among them, or work against them?

**Q1e.** How should a small gap be presented? If one per cent is the expected magnitude for this problem class, saying so is a finding about the problem rather than a weak result. Is that framing accepted, and are there exemplars that present a small optimality gap as a positive contribution?

---

## Question 2 — disclosing a modelling defect found mid-project

### What happened

A simulator was found, after most measurements had been taken, to contain a defect in its power-control law: transmit power was provisioned so the **nominal** signal-to-noise ratio met a threshold exactly, while the transmission mode was then selected from that same ratio **after** multiplying by a sub-unity fading quantile. The de-rating was applied at selection and never compensated at provisioning.

Consequences on a real panel: **207,607 of 275,616 transmission instances produced no transmitted mode**, including **all** single-occupant instances; **zero of two thousand users** attained the per-user rate target in any arm.

Complications:

- the two halves were each **separately declared** in sealed design documents, and one amendment states in terms that the margin **must not** be re-solved into transmit power, so correcting it reverses an explicit prior instruction;
- another declaration calls the rate target *nominal and synthetic* and expressly permits partial delivery, so "zero attainment" does not breach a stated promise;
- correcting it makes the project's headline **worse**: the coordinated-over-unilateral gap falls from about 6.4 % to about 1.3 %;
- separately, every comparison had been **mispaired**: the coordinated arm was compared against a local optimum that a different traversal order of the same neighbourhood improves upon.

### What I want to know

**Q2a.** What does the field expect when a modelling defect invalidates prior measurements? Retract, re-run and report both, report only the corrected results, or something else? Are there exemplars of papers that disclose a mid-project model correction well?

**Q2b.** How should a correction that **reverses an explicit prior design instruction** be framed so it reads as a justified change of modelling objective rather than as tuning the model until the results improve — especially when the correction makes the headline worse but a service metric better?

**Q2c.** How much of the pre-correction work can legitimately be carried forward — instruments, panels, comparators, negative results — and what must be regenerated?

**Q2d.** Is there an accepted way to report a quantity that was measured wrongly and then re-measured, when the error ran in **opposite directions** in different conditions? Ours was overstated by 1.75 points under one rule and understated by 0.75 under another, so no single ratio corrects the other figures.

**Q2e.** What disclosure would a referee consider sufficient, and what would they consider evasive?

---

## What I do not need

I do not need an explanation of why correctness matters, nor a general argument for transparency. I need the **conventions**: what magnitudes are normal for Q1, and what the accepted disclosure practice is for Q2, with sources.
