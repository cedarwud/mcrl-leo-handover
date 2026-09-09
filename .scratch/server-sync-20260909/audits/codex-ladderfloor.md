# Is the consolidation effect physics, or an artefact of where the mode table was truncated?

`DIAGNOSTIC_NOT_CLAIM`. Budget 2 hours. **This is load-bearing.** Two strategic reviews have just recommended making the consolidation mechanism the paper's contribution. A literature review then argued that the mechanism may be a boundary artefact. Settle it before anything else is built on it.

## The argument to test
At occupancy `n = 1` the required spectral efficiency is `r*/W`, the **lowest** it ever is. That selects the most robust mode, whose threshold is the **lowest** in the table. So at a given transmit power, occupancy 1 has the **largest** true link margin of any occupancy. Our model declares it unservable, which inverts the physics.

The power cap cannot explain it: if the cap bound at `n = 1` it would bind harder at `n = 3`, whose target mode has a higher threshold. So the pattern "1 fails, 3 succeeds" can only come from the **selection running off the bottom of the mode table**.

If that is right, the entire consolidation effect is a property of where the ladder was truncated, not of satellite physics.

## What to determine, in order
1. **Reproduce the mechanism exactly and name its cause.** Power is solved so nominal SINR lands exactly on `Gamma(n)`, then the transmitted mode is chosen from `q * SINR_nominal`. At `n = 1`, `Gamma(1)` is the lowest threshold in the table, so `q * Gamma(1) < Gamma(1)` and no mode qualifies. Confirm from the code that this is what happens, quote the lines, and state plainly whether the `NO_MODE` at low occupancy is the table floor or something else.
2. **Is the zero margin the deeper cause?** Because power is provisioned to land exactly on the target threshold, the nominal margin is zero at **every** occupancy by construction. The asymmetry is only that at higher occupancy there are lower modes to fall back to. Say whether that reading is correct, since it changes what the finding means: not "low occupancy is physically bad" but "we provision no margin and only high occupancy has somewhere to fall".
3. **Run the alternative formulation.** Provision power for `threshold + margin_dB` instead of exactly the threshold: choose the mode satisfying `SE >= r* n / W`, then require `SINR >= threshold(mode) + margin_dB`, solving power accordingly and capping as usual. Use margins equivalent to the current quantile at the relevant elevations, and state the mapping you used.
   **Then re-measure everything the consolidation claim rests on** on the same real anchors: the share of `NO_MODE` transmissions by occupancy, whether occupancy 1 and 2 remain unservable, and the pooled energy efficiency of BASELINE, the certified unilateral optimum and the bounded oracle set selector, with served counts.
4. **The decisive number:** does the **oracle-over-unilateral gain of +6.359 %** survive the alternative formulation, and does the occupancy-activation mechanism still fire? Report both formulations side by side.
5. **Two related checks the review raised.** Under demotion the realised margin equals the gap between adjacent mode thresholds, typically 0.5 to 1.5 dB, which may be far below a Ka-band rain margin; report the realised margin distribution. And a demoted mode delivers less than `r* n / W`, so the rate target is missed on every served beam; report whether the code credits bits at the demoted rate or at `r*`.

## How to report
If the effect survives the alternative formulation, say so and the mechanism stands. **If it does not, say that plainly and immediately**; that finding is worth more than the mechanism, because it would mean two strategic reviews just recommended building a paper on a truncation artefact. Do not soften either outcome.

Do not change any sealed value. The alternative formulation is a **variant evaluated on a copy**, not an amendment; the declared physics is unchanged by this task.

## Constraints
Workspace `/home/sat/mcrl-v025-ladder-ws`, built with `git -C /home/sat/mcrl-v025-codex-ws-engine archive 75c5c78c | tar -x -C` it, then `git init` and commit. Never write into `/home/sat/mcrl-leo-handover` or its venv, `/home/sat/mcrl-hub`, `/home/sat/mcrl-v025-codex-ws-engine`, or any other `mcrl-v025-*-ws`. Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. Large files under `/home/sat/bigtmp`, never `/tmp`, which is RAM-backed here. At most 3 processes, `nice -n 10`.

Write `LADDER-FLOOR-2026-09-10.md` in the workspace root and print it as your final message. Lead with one line: whether the consolidation effect survives.
