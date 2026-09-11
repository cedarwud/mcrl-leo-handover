I have completed the hostile but fair peer review arguing against the proposed paper narrative using the provided `./evidence/` bundle. 

The complete review has been written to [`./ADVERSARY-REVIEW.md`](file:///home/u24/papers/mcrl-leo-handover/.scratch/reviews/agy-adversary/ADVERSARY-REVIEW.md).

### First-Line Verdict & Single Most Damaging Flaw

> **Verdict: Reject — The proposed narrative is constructed on post-hoc circular outcome-fitting and misrepresents learner-free static diagnostic constructions (a hand-crafted 8-beam minimum set cover and an unlearned RSS heuristic) as learned "routes" on a Pareto frontier, while the project's own empirical evidence demonstrates that the learned routes fail their necessity condition, compete destructively, and optimize a surrogate objective that actively penalizes system energy efficiency.**

---

### Core Adversarial Findings Summary

1. **Fictitious Pareto Attribution (The Smoking Gun):**
   - The offered non-dominated pair ($46.11\text{ Mbit/J}$ at $2.5\%$ attainment vs. $41.62\text{ Mbit/J}$ at $24.75\%$ attainment) was **not produced by any learned routes**. 
   - $46.11\text{ Mbit/J}$ is a learner-free combinatorial set cover (packing 100 users into 8 beams) from a diagnostic script ([`CROWDING-COST`](file:///home/u24/papers/mcrl-leo-handover/.scratch/reviews/agy-adversary/evidence/reports/CROWDING-COST-2026-09-10.md)), while $41.62\text{ Mbit/J}$ is the classical unlearned static heuristic `RSS_MAX` ([`STATIC-BASELINE-FAMILY-CLEANPATH`](file:///home/u24/papers/mcrl-leo-handover/.scratch/reviews/agy-adversary/evidence/reports/STATIC-BASELINE-FAMILY-CLEANPATH-2026-09-10.md)).
   - The learned Q1/Q2 networks **structurally cannot even represent** `RSS_MAX` because they lack per-option `nominal_gain` ([`APPROACHING-THE-INSTRUMENTS`](file:///home/u24/papers/mcrl-leo-handover/.scratch/reviews/agy-adversary/evidence/reports/APPROACHING-THE-INSTRUMENTS-2026-09-10.md)), and the C3 bounded catalogue ($98.13\%$ singletons/pairs) contains $0$ of the $5,814$ multi-user moves needed to reach crowded configurations.

2. **Empirical Failure of the Proposers' "Necessity Condition":**
   - **Route 3 (C3 / Interaction / "Energy side") actively harms EE:** Across all 16 seeds in primary evaluations ([`Z-VIEW-SCORING`](file:///home/u24/papers/mcrl-leo-handover/.scratch/reviews/agy-adversary/evidence/reports/Z-VIEW-SCORING-2026-09-10.md)), dropping C3 **increases** system EE (by $+10.04\text{ Mbit/J}$ in Q1 v1, $+1.20\text{ Mbit/J}$ in Q1 v2, and $+2.25\text{ Mbit/J}$ in z-view). Clean coordination ceiling is $<0.84\%$ ([`CEILING-CLEAN-AND-LEVERS`](file:///home/u24/papers/mcrl-leo-handover/.scratch/reviews/agy-adversary/evidence/reports/CEILING-CLEAN-AND-LEVERS-2026-09-10.md)), and unilateral moves ($k=1$) improve EE at $12/12$ anchors ([`COORDINATION-VALUE`](file:///home/u24/papers/mcrl-leo-handover/.scratch/reviews/agy-adversary/evidence/reports/COORDINATION-VALUE-2026-09-10.md)).
   - **Route 2 (C2 / Persistence / "Time side") has no demonstrable EE value:** In Q1 v2, dropping C2 increases EE across $15/16$ seeds. Oracle C2 adds $+0.68\%$ ($95\%\text{ CI } [-3.60\%, +5.73\%]$), degrades EE at 20 of 30 changed anchors, and produces $0.00\%$ under the sealed tie-break rule ([`C2-TARGET-VALUE`](file:///home/u24/papers/mcrl-leo-handover/.scratch/reviews/agy-adversary/evidence/reports/C2-TARGET-VALUE-2026-09-10.md)). Handover energy is physically unsourced ($E_{HO}=0$) and interruption time is diluted 47-fold ($0.2\%$ of a 30 s step) ([`R2-PHYS-PROVENANCE-MATRIX`](file:///home/u24/papers/mcrl-leo-handover/.scratch/reviews/agy-adversary/evidence/declarations/R2-PHYS-PROVENANCE-MATRIX-2026-08-26.md)).

3. **The Single-Judge Problem and Faux Pareto Trade-offs:**
   - In Q1 v2, `FULL` is **strictly Pareto-dominated** by the ablated arm `DROP_C2` across all primary metrics simultaneously: EE ($43.41$ vs. $42.26\text{ Mbit/J}$), served users ($31,965$ vs. $31,962$), and rate-target attainment ($27.47\%$ vs. $27.20\%$). Calling optimization degradation a "Pareto trade-off" is scientifically untenable.

4. **The Broken Objective & Dinkelbach Non-Sequitur:**
   - No linear price orders arms by EE ([`ETA-EXCHANGE-RATE`](file:///home/u24/papers/mcrl-leo-handover/.scratch/reviews/agy-adversary/evidence/reports/ETA-EXCHANGE-RATE-2026-09-10.md)). But at the Dinkelbach fixed point $\eta^* = 41.62\text{ Mbit/J}$, search **still descends away from `RSS_MAX` and EE still falls at 9 of 12 anchors**. The root cause is a **selection horizon mismatch** (boundary-0 snapshot vs. 48-boundary integral) and spatial heterogeneity, which an adaptive combination rule does not cure.

5. **Physical Contradiction with Baseline Load Balancing:**
   - MODQN's reward $r_3 = -U_{b_u}$ is a load-spreading term. But physical payload measurements ([`CROWDING-COST`](file:///home/u24/papers/mcrl-leo-handover/.scratch/reviews/agy-adversary/evidence/reports/CROWDING-COST-2026-09-10.md)) prove that spreading users across beams monotonically destroys EE ($d(\text{EE})/d(\text{active}) = -425,009\text{ bit/J}$ per added beam).
   - Furthermore, **no runnable external MODQN baseline exists on V0.25 physics** ([`BASELINE-MODQN-REFERENCE`](file:///home/u24/papers/mcrl-leo-handover/.scratch/reviews/agy-adversary/evidence/reports/BASELINE-MODQN-REFERENCE-2026-09-10.md)); the project evaluated a static heuristic (`carrier_base`) and labelled it `BASELINE`.

6. **Total In-Sample Contamination:**
   - $100\%$ of the scoring panel anchors in [`Z-VIEW-SCORING`](file:///home/u24/papers/mcrl-leo-handover/.scratch/reviews/agy-adversary/evidence/reports/Z-VIEW-SCORING-2026-09-10.md) are identical to the training anchors ([`CONVERGED-EXACT-SCORING`](file:///home/u24/papers/mcrl-leo-handover/.scratch/reviews/agy-adversary/evidence/reports/CONVERGED-EXACT-SCORING-2026-09-11.md)). Zero out-of-sample evidence exists.

7. **What Survives (The Honest Paper):**
   - Route 1 (focal link quality) reliably works ($+12.69\text{ Mbit/J}$, $16/16$ seeds positive).
   - An honest, publishable paper would discard the three-route Catfish Pareto narrative, present C1 as a decoupled link-quality optimizer, document the rigorous negative result on multi-user coordination (showing $k=1$ suffices and ceiling is $<0.84\%$), and analyze why terrestrial load-balancing objectives fail in LEO satellite payload economics.
