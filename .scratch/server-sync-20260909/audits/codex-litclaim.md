Read papers and answer three questions that decide whether a project's claim structure is legitimate. The PDFs are in `/home/sat/litref-20260910/`. Workspace: the current directory; write your report here. Do not modify `/home/sat/mcrl-leo-handover` or its virtual environment.

`DIAGNOSTIC_NOT_CLAIM`. No code, no run. This is a reading task with a verdict.

Read at minimum, in full where they bear on the questions:
- `2025_07_CDRL_Catfish-Effect-Based_...RIS-Aided_6G_Networks.pdf`
- `2013_06_User_Association_for_Load_Balancing_in_Heterogeneous_Cellular_Networks.pdf`
- `2025_02_Multi-Agent_Reinforcement_Learning_for_Sequential_Satellite_Assignment_Problems.pdf`
- `2025_11_A_Distributed_Beam_Hopping_Strategy_With_Load_Balancing_and_Coordinated_Interference_Avoidance_...pdf`
- `2026_03_Jointly_Optimizing_Satellite_Handover_and_Power_Allocation_...Dual-Agent_Framework.pdf`
Skim the rest of the directory for anything that bears on the questions and say what you used.

## Context you need, stated neutrally
A project models LEO satellite handover. Users associate with beams; a per-beam power controller provisions transmit power to meet a per-user rate target under equal-airtime multiplexing and a discrete modulation-and-coding table; energy efficiency is total delivered bits over total joules, pooled across the network. The project's learned system has three components whose design is derived from the "catfish effect" paper above. The project's owner requires that each of the three components individually raise pooled energy efficiency by a stated margin.

Two measurements now bound the situation. Comparing a bounded joint (multi-user, simultaneous) association search against an iterated unilateral (one-user-at-a-time) search run to a certified fixed point, the joint search is worth **+0.51 %** in pooled energy efficiency. Comparing that same iterated unilateral fixed point against a geometry-only nearest-beam baseline, the gap is **+442 %**. The decision interval is 30.08 seconds; the iterated unilateral search takes 65 seconds on average to converge, and a five-second-budgeted version of it achieves nothing at all.

## Q1 — What does the catfish paper actually require of a component?
Read it closely. Answer:
- how it defines a "catfish" component and what role each plays;
- how it measures each component's contribution — ablation, marginal gain, something else — and whether it requires each component to show an individually positive effect on the headline metric;
- whether it reports any component with zero or negative marginal contribution, and if so how it treats that;
- what its ablation baseline is, and whether "drop component X" means removing a module, removing an input, or removing a training signal.
Then state plainly: **is "each of the three components must individually raise the headline metric" the source's own bar, a stricter bar, or a different bar altogether?** Quote the source.

## Q2 — Joint versus unilateral: what do others find, and when is the gap large?
Across the papers, find every case where a joint or coordinated assignment is compared against a greedy, iterative, or one-at-a-time procedure, and report the magnitude of the gap. Then answer the question the project actually needs: **under what conditions does that gap become large?** Load, interference coupling, cell overlap, power limits, number of users per beam — say which of these the literature identifies as making coordination worth more, with evidence. If the literature says the gap is generally small once a good iterative procedure has converged, say that plainly; it is the answer the project most needs to hear.

## Q3 — Does anyone evaluate under a decision-time budget?
The project is considering making its primary comparison "what each method achieves within the 30.08-second decision interval" rather than "what each method achieves at convergence". Determine whether the literature does this:
- do papers report per-decision computation time, and against what interval;
- does any compare methods under a common time budget rather than at convergence;
- is "our method reaches a good solution faster" a recognised contribution in this field, and how is it presented;
- would a referee regard a budgeted comparison as legitimate, or as choosing a comparator that flatters the method?
Be blunt. The project has already been warned that changing a comparator after seeing results is illegitimate; the mitigating fact is that the budgeted comparison was written into its own contract before these results existed. Say whether that mitigation is sufficient.

## Output
Write `LIT-CLAIM-STRUCTURE-2026-09-10.md` and print it in full as your final message. Lead with three one-line answers, one per question. Quote sources with paper and section for every substantive claim. Where the corpus does not answer a question, say so rather than generalising.
