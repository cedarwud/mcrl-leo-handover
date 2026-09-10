Workspace: the current directory, `/home/sat/mcrl-v025-ceiling30-ws`. Read-only elsewhere. Interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, `nice -n 15`. Never modify `/home/sat/mcrl-leo-handover` or its virtual environment.

**Process limit: at most 3 concurrent workers.** **Time budget: aim to finish within twenty-five minutes.** Speed is the point of this task.

`DIAGNOSTIC_NOT_CLAIM` and explicitly **`FAST_LOOK_TWO_ANCHORS`**. This is a deliberately small sample run to establish the **shape** of an answer quickly. A companion job is running the same question properly on eight anchors under both provisioning rules. **Nothing here may be reported as the answer**; every table carries the fast-look label. No sealed constant, threshold, sign, seed, horizon, price, guard, acceptance rule or declared control law is changed.

# The question, in one paragraph

The power amplifier is about **94.8 %** of consumed power and its draw is set by the **power and mode control law**, not by which user attaches to which beam. Today's work measured the association layer's entire room at about **one per cent** above a certified local optimum, while repairing one defect in the control law moved pooled efficiency by about **+53 %**. **Nobody has measured how far the control law itself is from the best achievable.**

# What to do, fast

**Two real anchors. The corrected margin provisioning rule only.** Take the configuration the pipeline commits at each anchor and **hold the user assignment completely fixed**.

1. Record the declared law's outcome: pooled efficiency, served count, rate-target attainment.
2. Search over **per-beam radiated power and transmission mode** for the same fixed assignment, honouring the unchanged per-beam cap, the unchanged service guard and the unchanged rate target, with interference coupling evaluated exactly. Use whatever search fits the time budget — a coarse grid over power per beam with the discrete mode table is acceptable — and **state exactly what you searched and how coarse it was**.
3. Report the gap: how far the declared law sits below the best you found, per anchor.
4. Say in one line whether the improved settings appear to need **cross-beam** information or whether a **per-beam local rule** would reach them. A rough judgement with a reason is what is wanted, not a proof.

# Rules

- **Never call your result a ceiling.** It is a best-known value from a coarse search on two anchors. Say so in the first line.
- **If the declared law is already close to what you can find, say that first.** A negative here is as useful as a positive and arrives just as fast.
- If the coarse search cannot beat the declared law at all, report that plainly rather than refining until it does.
- State the wall time you used and what you would do differently with more.

Write `CONTROL-LAW-FAST-LOOK-2026-09-10.md` in the workspace root and print it in full as your final message. Lead with one line: the gap you found on two anchors, and whether it looks like it needs cross-beam information.
