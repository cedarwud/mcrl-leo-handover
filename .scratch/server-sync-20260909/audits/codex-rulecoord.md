# A rule-based coordinator: capture the verified mechanism with no learning at all

`DIAGNOSTIC_NOT_CLAIM`. Budget 2 hours. This is a hedge against the learner gate failing, and it may be a result in its own right.

## Why this exists
The learned coordination component has three independently confirmed defects and is the gate most likely to fail. But the mechanism it is supposed to discover has already been **verified analytically and numerically**, so it can be written down as a rule instead of learned.

If a fixed rule captures a useful share of the headroom, the project has a deployable coordinator regardless of whether the learner ever works, and the paper can report both. If a rule capturing the exact verified mechanism yields nothing, that is strong evidence the mechanism is rare or its value is offset elsewhere, which is also decisive.

## The rule to implement
At each anchor, from the incumbent assignment, apply in this order and commit the first candidate that strictly improves the objective while passing the unchanged service guard:

1. **Occupancy activation.** At 10 degrees elevation the engine's quantile is `q10 = 0.42923539` and the lowest mode threshold is `0.7174947935`, so `q*Gamma(n)` clears only from occupancy 3. For each beam at occupancy exactly 1 whose users therefore select no transmitted mode, move in the nearest legal users to reach occupancy 3. Compute the activation threshold **from the engine's own tables at the actual elevation of each beam**, not from the 10-degree constant, and say how much the required occupancy varies across elevations.
2. **Multi-aggressor relief.** For each victim that is interference-limited and **not** rescued by removing its single strongest aggressor, move its top two, and separately top three, aggressors to their own best legal alternatives.
3. **Beam evacuation.** For each beam with two or three occupants, move all of them out, since the per-chain circuit power is saved only when the beam empties.

Score every candidate with the **real engine**, exactly, using the sealed calibration. No learning, no model, no head.

## Report energy efficiency, and compare against the right baselines
Evaluate on the real worlds and real anchors, at least 20 anchors, and report pooled EE in bit/J for:

* **BASELINE**, the incumbent assignment;
* **UNILATERAL**, iterated best single-user moves until none improves, which is what C1 alone reaches;
* **RULE**, this coordinator.

The number that matters is **RULE versus UNILATERAL**, because that is the part attributable to set-level coordination rather than to unilateral optimisation. Report the served count for every arm at every anchor so it is visible whether any gain came from serving fewer users; a gain bought that way does not count.

Also report, per rule family, how often it fired and what it contributed, so it is clear which of the three mechanisms carries the value.

## Deployability, measured not assumed
Record the wall time of the rule's decision at each anchor. The declared coordinator budget is 10 seconds. A rule that is both effective and fast is a deployable result; one that is effective and slow is a ceiling. Report which it is and do not change the budget.

## Workspace
`/home/sat/mcrl-v025-rule-ws`: build with `git -C /home/sat/mcrl-v025-codex-ws-engine archive 75c5c78c | tar -x -C /home/sat/mcrl-v025-rule-ws`, then `git init` and commit. Never write into `/home/sat/mcrl-leo-handover` or its venv, `/home/sat/mcrl-hub`, `/home/sat/mcrl-v025-codex-ws-engine`, or any other `mcrl-v025-*-ws`. Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. Large intermediates go under `/home/sat/bigtmp`, never `/tmp`, which is a RAM-backed tmpfs here. At most 4 processes, `nice -n 10`.

Change no threshold, sign, seed, horizon, price, service guard or acceptance rule. The rule is a candidate generator, not a change to the objective.

Write `RULE-COORDINATOR-2026-09-09.md` in the workspace root and print it as your final message. Lead with pooled EE for the three arms and the RULE-over-UNILATERAL relative gain, then the served counts, then the per-family breakdown, then the decision times.

## CORRECTION issued after this task started, apply it
The targeting criterion is **starting occupancy exactly 1**, not "1 or 2". A verified witness shows the sign of the interaction depends on the starting occupancy:

* start at occupancy 1, two arrivals are needed to activate the beam: `Psi = +1.962 Gb`;
* start at occupancy 2, one arrival already activates it, so the second is diminishing: `Psi = -0.778 Gb`.

Coalitions seeded from occupancy-2 beams therefore contribute **negative** interaction, the opposite of what is wanted. Build them from occupancy-1 beams. You may still include occupancy-2 cases, but label them as a separate family and report them separately so the negative population is visible rather than mixed in.

For context: in the census, occupancy 1 accounts for 5,760 of 10,848 beams, that is 53.1 %, so this is the largest bucket and not a corner case.

Compute the activation threshold from the engine tables at each beam's actual elevation rather than from the 10-degree constant, since the quantile varies with elevation.

## Scope reduction, after a first attempt produced nothing in three hours
The previous attempt spent three hours writing test scaffolding and produced no result. **Completion beats completeness.** Reduce scope until it finishes:

* **10 anchors is enough**, not 20. Say how many you covered.
* Implement **only the occupancy-activation rule** first, and only extend to beam evacuation and aggressor relief if it is already finished and time remains. Occupancy activation is the mechanism with the strongest evidence: it is admitted at 180 of 180 anchors in the rebuilt corpus and does not depend on the disputed per-chain circuit constant.
* **Do not write a test suite.** A single script that builds candidates, scores them with the real evaluator, and prints a table is the deliverable. Correctness comes from using the production evaluator, not from unit tests around your own scaffolding.
* If you have partial results at any point, write them to the report file immediately and keep extending it, rather than saving everything for the end.

Report the three pooled energy-efficiency figures, the RULE-over-UNILATERAL gain, the served counts, and the per-anchor decision wall time against the 10 second budget. Anything beyond that is optional.
