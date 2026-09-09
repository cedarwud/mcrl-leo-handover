# Implement the offline certified unilateral diagnostic that the contract already requires

`DIAGNOSTIC_NOT_CLAIM`. Budget 2 hours. This **implements an existing contract requirement**; it does not amend one.

## Authority
Contract v1.2 item 6 already calls the budget-limited arm an **operational comparator**, already requires a **completed-neighbourhood certificate** for any "beyond exhaustive unilateral improvement" claim, and already permits an **offline certified diagnostic**. Only the operational arm was ever built. Two independent adjudications reached the same conclusion: the missing offline arm is the one that can discharge the certified-unilateral requirement, and building it is implementation rather than amendment.

**Do not change the operational arm.** Do not touch its deadline, its guard, or its abort behaviour. Those are sealed and one of them, the discard on abort mandated by §C2's "atomic commit of the final profile only", is an open owner decision that this task must not pre-empt.

## Why it is needed
Profiling found the operational arm selects a BASE configuration at **90 of 90 anchors**: 79 by deadline fallback and 11 by certifying that the anchor itself is a local optimum. So `FULL > S_UNI` is arithmetically the same test as `FULL > BASELINE`, which is already plotted as its own curve. The attribution conjunct cannot fail for any reason connected to coordination.

The cause is structural, not a tuning matter. Each iteration re-evaluates every single-user deviation, about 2,748 exact solves per sweep at 6 to 11 seconds, and commits one move. An anchor therefore certifies within budget only if the first sweep finds no improving move. Uncensored iteration counts are bimodal at 0, 46, 50, 80, 86, 86 with nothing between 1 and 45, so no realistic budget change converts any anchor.

## What to build
A separate arm, `S_UNI_OFFLINE`, run **without any wall-clock deadline**, that iterates exact unilateral improvement to a certified local optimum and reports a completed-neighbourhood certificate: the final profile, the iteration count, the termination reason, and an explicit statement that every legal unilateral alternative was evaluated at the final iterate and none improves.

Considerations, in order:
* **Cost.** The naive form needs up to 86 sweeps at roughly 2,748 solves each. Consider a deterministic **sequential round-robin** best response, which both adjudications note is equally "iterated exact unilateral improvement to a local optimum" under the contract's wording and should reach a fixed point in far fewer passes. If you adopt it, **prove on a sample of anchors that it reaches the same fixed point** as the current global-argmax form, or report clearly where they differ. Different orders can give different fixed points, so this must be checked, not assumed.
* **Honesty about what it is.** A fixed point reached by one greedy path is an arbitrary local optimum, **not a ceiling** on unilateral reasoning. Say so in the report and in any field name. `FULL > S_UNI_OFFLINE` licenses only "not reproducible by this greedy path".
* **A non-degeneracy statistic.** Report the fraction of anchors where the offline arm's selection differs from the anchor. If that fraction is near zero the arm is uninformative and must be reported as such rather than as a pass.

## Also fix one vacuous test clause
Acceptance test T2 asserts that an additive placebo yields a near-zero interaction and that the deployed selector's decisions match the unilateral arm's. When both return the anchor, that clause passes **vacuously** and cannot detect the condition just measured. Strengthen it so it requires a case where the unilateral arm selects something other than the anchor, and demonstrate that the strengthened test fails against the current degenerate behaviour.

## Report
`OFFLINE-SUNI-2026-09-09.md` in the workspace root, printed as your final message. Lead with the non-degeneracy fraction and the per-anchor cost. Then the fixed-point agreement check if you changed the iteration order, then the T2 strengthening with its failure demonstration.

## Constraints
Workspace `/home/sat/mcrl-v025-offlinesuni-ws`, built with `git -C /home/sat/mcrl-v025-codex-ws-engine archive 75c5c78c | tar -x -C` it, then `git init` and commit. Never write into `/home/sat/mcrl-leo-handover` or its venv, `/home/sat/mcrl-hub`, `/home/sat/mcrl-v025-codex-ws-engine`, or any other `mcrl-v025-*-ws`. Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. Large files under `/home/sat/bigtmp`, never `/tmp`, a RAM-backed tmpfs here. At most 3 processes, `nice -n 12`.

Change no threshold, sign, seed, horizon, price, service guard or acceptance rule, and do not modify the operational arm.
