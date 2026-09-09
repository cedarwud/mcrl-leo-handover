# Step outside the frame: is this project's research question still the right one?

You are being asked for a **strategic review with fresh eyes**. Two other reviewers, on different models, are doing the same independently. Do not try to anticipate them.

The controller who has been running this project has spent a full day inside it and has explicitly said its own judgement is now shaped by that day's path. It has been optimising **inside** a frame all day and has not questioned the frame. Your job is to question the frame, not the details.

**Do not audit the code. Do not look for more defects.** The project has found plenty. Read the record and ask whether the work is pointed at the right question.

## What to read
Sealed records and reports are under `/home/sat/mcrl-v025-codex-ws-engine/.scratch/multi-catfish-v025-physics-successor/` and `/home/sat/mcrl-v023-codex-audits/parallel-20260909/`. Start with `V025-CONTROLLER-FINDINGS-AFTERNOON-2026-09-09.md`, `V025-STAGES-6-8-CONTRACT-v1-2026-09-08.md`, and the reports named `ORACLE-CODEX`, `PREVALENCE-CODEX`, `PSI-WITNESS-CODEX`, `C1C2-CODEX`, `CERTPROFILE-CODEX`, `COALGEN-CODEX`, `CURVE-CODEX`. Read enough to orient; you are not required to read everything.

## The situation, stated plainly
The system is a LEO satellite handover controller with **three learned components** evaluated by ablation: per-user components C1 and C2, and a set-level coordination component C3. The primary outcome is pooled energy efficiency. The sealed success claim is an intersection: each of three FULL-minus-DROP contrasts must exceed +0.5 % relative with its lower bound above that, plus three quality-of-service non-inferiority conditions.

**What is measured and solid.** The coordination mechanism exists and was verified in the real engine on four separate mechanisms. Qualifying coalitions exist at 30 of 30 real anchors, with a median energy-efficiency gain of 9.1 %. A perfect-knowledge selector beats a certified unilateral optimum by **+6.36 %**, with the served count increased rather than decreased, and that gain is robust across 18 combinations of a disputed hardware constant, being **larger** when the constant is set to zero.

**The proportions.** Iterated unilateral optimisation beats the carrier baseline by **+664 %**. Set-level coordination then adds **+6.36 %** on top of that.

**What is not measured.** After a day of auditing, **no valid learned measurement exists for any of the three components**. Every prior result was taken under at least two confirmed defects: collapsed features, a corpus containing only two-user coalitions, proxy labels substituted for the contracted targets of C1 and C2 with one of them carrying the wrong sign, a degenerate comparator that returns the anchor at 90 of 90 decisions, and acceptance tests that cannot fail for the reason they exist.

**What is newly known about the mechanism.** The value comes from **consolidation**, not load balancing: moving users **onto** a beam so its occupancy reaches three activates a transmitted mode that one or two users cannot support, and emptying a beam entirely saves its fixed per-chain power. The one mechanism resembling load balancing fired at 0 of 30 anchors. The interaction is a threshold on summed occupancy, and a third-order remainder is material on 38.5 % of coalitions, so the current pairwise interaction model is provably misspecified.

**Constraints that will not move.** One independent ephemeris date is available in the completed evaluation; the claim panel wants about 160 and only about 142 are free. The coordinator has a 10 second decision budget inside a 30 second interval, and the certified unilateral comparator needs up to 876 seconds and 86 iterations to converge.

## The questions I actually want answered
1. **Is the three-component ablation still the right design?** It requires establishing that each component contributes more than half a percent in the complete system. Given that the unilateral layer takes +664 % and coordination adds +6.36 %, is that conjunction the claim worth making, or is the project holding on to a decomposition that no longer matches where the value is?

2. **Is the learned coordinator the contribution, or is the mechanism?** The mechanism discovery is clean, physical, counter-intuitive and verified: under a rate target with equal-airtime multiplexing, adding load to a beam can make it servable, so consolidation raises energy efficiency. Whether a neural network can learn to exploit it inside 10 seconds is a separate and much harder claim. Which of those is the paper, and is the project spending its remaining effort on the right one?

3. **What would you stop doing?** Name the specific efforts that are consuming time without changing what the paper can claim.

4. **What is the smallest credible result** this project could publish with what is already measured, if the learned components never work? Is there one, and what would its weakest point be under review?

5. **Is there a frame the controller has not considered at all?** A different objective, a different comparator, a different unit of analysis, a different claim structure.

## How to answer
Be blunt. The controller has been wrong repeatedly today and would rather hear it now. Lead with your answer to question 2 in one line. Do not hedge into a balanced summary; give a judgement and the reasoning that produces it.

Read-only. Change nothing. Write your review to `STRATEGIC-REVIEW-<yourname>-2026-09-10.md` in your working directory and print it as your final message.
