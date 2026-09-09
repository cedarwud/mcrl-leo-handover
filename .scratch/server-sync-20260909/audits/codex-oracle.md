# Perfect-knowledge ceiling: if the interaction value were known exactly, would energy efficiency improve at all?

`DIAGNOSTIC_NOT_CLAIM`. Budget 90 minutes. This is the cheapest possible test of whether the learner path is worth pursuing, and it needs no learner.

## The logic
A learned head estimates the interaction term `Psi_A`. If a selector that knows `Psi_A` **exactly** cannot beat the baseline on pooled energy efficiency, then no learner can, because learning can only approximate what the oracle has. Conversely a large oracle gain sets the ceiling that a learner is chasing and tells us whether the chase is worth the cost.

This separates two failures that have been confounded for months: "the mechanism has no value" and "the learner cannot find the value".

## Task
Create `/home/sat/mcrl-v025-oracle-ws` and populate it with `git -C /home/sat/mcrl-v025-codex-ws-engine archive 75c5c78c | tar -x -C /home/sat/mcrl-v025-oracle-ws`, then `git init` and commit it so codex trusts the directory. That is the corrected causal ACM. Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. Never write into `/home/sat/mcrl-leo-handover` or its venv, `/home/sat/mcrl-hub`, `/home/sat/mcrl-v025-codex-ws-engine`, `/home/sat/mcrl-v025-pilot-ws`, `/home/sat/mcrl-v025-prevalence-ws`, or `src/mcrl/env/`. At most 4 processes, `nice -n 10`.

Build **three selectors** and evaluate all of them on the same real anchors, same worlds, same everything:

* **BASELINE** — the incumbent carrier assignment, unchanged.
* **UNILATERAL** — iterated best single-user moves until no single move improves. This is what the C1 component can reach on its own.
* **ORACLE_SET** — from the certified unilateral optimum, exactly evaluate a bounded set of joint candidates and commit the best one that passes the service guard. Use the mechanism-based candidate families, not a ranking by the size of the single-user marginals: coalitions built from a beam's occupants, from a victim plus its top two and top three interference contributors, and from complete evacuations of a beam. **Ignore the ten-second decision deadline entirely** and say so; this measures the ceiling, not a deployable policy.

## Report energy efficiency
Pooled EE in bit/J for each of the three selectors, the relative gain of ORACLE_SET over UNILATERAL, and the relative gain of UNILATERAL over BASELINE. **The first of those two is the number that matters**: it is the headroom that belongs to set-level coordination rather than to unilateral optimisation.

Also report, per anchor: whether a qualifying coalition existed, its size, its EE gain, and the served count against the anchor's so it is visible whether any gain came from serving fewer users. Report the exact evaluation count so the cost of the oracle is on the record.

Cover as many anchors as the budget allows, at least 20, and say how many. Breadth beats depth.

## The finding I need either way
If ORACLE_SET barely beats UNILATERAL, the coordination component has little to offer even with perfect knowledge, and that is a decisive and publishable negative result reached in ninety minutes rather than in weeks of training. Say so plainly and early if that is what you find. Do not tune anything to raise the number.

Write `ORACLE-CEILING-2026-09-09.md` in the workspace root and print it as your final message.
