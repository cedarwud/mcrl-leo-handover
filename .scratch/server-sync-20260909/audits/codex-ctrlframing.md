You are reviewing the design of a measurement **while it runs**, so that a wrong framing is caught before its result is acted on. Workspace: the current directory, `/home/sat/mcrl-v025-witness-ws`. Read-only elsewhere. Never modify anything sealed.

`DIAGNOSTIC_NOT_CLAIM`. Design review. **At most 2 concurrent processes** if you run anything.

# What is being measured, and why

The project's efficiency objective is pooled bits over pooled joules. The power amplifier is about **94.8 %** of consumed power and its draw is set by the **power and mode control law**. Today's measurements found the association layer's total room to be about **one per cent** above a certified local optimum, while repairing **one defect** in the control law moved pooled efficiency by about **+53 %**.

A job now running measures the control law's own room: **hold the user assignment fixed at what the pipeline commits, and choose per-beam power and mode to maximise pooled efficiency** subject to the unchanged cap, service guard and rate target, with interference coupling honoured. Its prompt is `/home/sat/mcrl-v023-codex-audits/parallel-20260909/codex-controlceiling.md`; read it.

The project's owner has said plainly that a one per cent improvement is not a meaningful result, so this measurement is about to inform a possible change of research direction — pointing three learned components at power and mode decisions rather than at association decisions.

# What I want from you

**Is this measurement well posed, and will its answer mean what the project will take it to mean?**

1. **Is "hold the assignment fixed, optimise power and mode" the right isolation?** The two layers interact: a better power policy may make a different assignment optimal, so the sum of the two separately measured ceilings may not be the joint ceiling. Does that make the decomposition misleading, and if so how should it be stated?
2. **Is the objective well posed at fixed assignment?** Pooled efficiency is a ratio of sums. Maximising it over per-beam powers with an unchanged rate target and service guard — is that a well-defined problem here, is it convex or otherwise tractable, and what pathologies should the runner expect? In particular, can it be improved by *serving fewer users*, and does the guard actually prevent that?
3. **What would make the answer misleading?** Consider at least: a large gap that exists only because the optimiser exploits information no deployable policy could have; a gap concentrated entirely in the anchors where the cap binds; and a gap that vanishes once the same fading realisation is applied to both policies.
4. **If the gap is large, does it follow that learned components should be pointed at the control law?** State what else would have to be true. In particular, whether the improved settings need joint cross-beam information — because if a better *local* rule suffices, the finding is a control-law redesign and not a case for learning at all.
5. **Anything else.** Especially anything that would let this measurement produce an encouraging number that does not survive contact with deployment.

# Output

Write `CONTROL-CEILING-FRAMING-2026-09-10.md` and print it in full. **Lead with one line: whether the measurement is well posed, and if not, the single change that would fix it.** Be blunt; the project has spent a day discovering that four of its comparisons were mispaired, misimplemented or measured against the wrong reference.
