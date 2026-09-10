Workspace: the current directory, `/home/sat/mcrl-v025-arch-ws`. Read-only access to sibling `mcrl-v025-*-ws` is fine. Interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, `nice -n 15`. Never modify `/home/sat/mcrl-leo-handover` or its virtual environment.

**Process limit: at most 4 concurrent worker processes.** Shared machine; two jobs today drove it to load 64 and 70 with a gigabyte of memory left.

`DIAGNOSTIC_NOT_CLAIM`. No learner, no training run, no policy run. **No sealed constant, threshold, sign, seed, horizon, price, service guard, acceptance rule or declared control law is changed or replaced.** Any alternative policy is evaluated on a clearly separated copy and labelled as a diagnostic.

# The question, and why it has never been asked

The power amplifier accounts for about **94.8 %** of consumed power, and its draw is set by the **power and mode control law**, not by which user attaches to which beam.

Today the project measured the association layer's entire room: two local optima of the association search differ by about eight per cent, and an exhaustive bounded joint search sits about **one per cent** above the certified fixed point. Separately, repairing **one defect** in the control law moved pooled efficiency from 28.47 to 43.71 Mbit/J — about **+53 %**.

So a single defect in the control law cost more than the whole association layer can win. **Nobody has ever measured how far the control law itself is from the best achievable.** That is this task.

# The measurement

**Hold the assignment fixed. Vary only the power and mode policy.** This is the exact mirror of a companion job now measuring the association ceiling with the control law held fixed.

On at least eight real anchors, under **both** provisioning rules, for the configuration the current pipeline actually commits:

**C1 — the declared law's outcome.** Pooled efficiency, served counts and rate-target attainment as the sealed law produces them. This is the reference.

**C2 — the best achievable power and mode assignment for that same fixed user assignment.** Choose per-beam radiated power and transmission mode to maximise pooled efficiency subject to the unchanged per-beam cap, the unchanged service guard and the unchanged rate target, with the interference coupling honoured exactly. State your method and its optimality status precisely: exhaustive over the discrete mode table with an inner power solve, a bounded search, or a relaxation with a bound. **If you cannot certify optimality, say so and label the result a best-known value rather than a ceiling.**

**C3 — the gap.** How far the declared law sits below the best you found, per anchor and pooled, under both rules.

**C4 — where the gap lives.** Decompose it: is it concentrated in beams where the cap binds, at low occupancy, at high occupancy, at particular elevations or off-axis angles? A gap that is diffuse and a gap that sits in one identifiable regime imply very different remedies.

**C5 — is the better policy implementable?** For the improved settings you find, state what information they require. If they can be computed from the pre-decision state of one beam and its neighbours, the remedy is a better local rule. **If they require joint knowledge across beams, that is precisely where a learned coordinating component would have work to do**, and you should say so with the evidence rather than as an aspiration.

# Rules

- **If the declared law is already close to the best achievable, say so in the first line.** That is the outcome that would close this direction, and it must not be softened. It would mean the efficiency of this system is bounded by its physics rather than by its policies, which is itself a finding.
- Do not tune the declared law. Evaluate it as it stands and compare.
- Report both provisioning rules; a gap that exists only under the defective one is not evidence about the corrected system.
- Every number reproducible from a script left here with exact commands.
- Say plainly what you did not reach, and never present a non-certified search result as a ceiling.

Write `CONTROL-LAW-CEILING-2026-09-10.md` in the workspace root and print it in full as your final message. Lead with one line: how far the declared control law sits below the best achievable at fixed assignment, under each provisioning rule, and whether that best is certified or merely best-known.
