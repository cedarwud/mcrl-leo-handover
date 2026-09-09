# The one-line policy nobody has measured: no beam below occupancy three

`DIAGNOSTIC_NOT_CLAIM`. Budget 2 hours. A strategic review called this the single highest-information cheap experiment available and noted that the project cannot currently say what it captures. Both possible outcomes are valuable, so report whichever you get without adjustment.

## The policy
Not a search heuristic and not a candidate generator. A **global invariant** applied to the whole assignment at an anchor:

> **No beam operates below occupancy three. Consolidate or empty.**

Concretely: for every active beam whose occupancy is 1 or 2, either move enough users in to reach 3, or move all of its occupants out and leave it empty. Choose deterministically, for example by whichever of the two is cheaper under the exact objective, and state the rule you used. Apply it as one pass over the assignment, then commit.

This differs from the rule coordinator already run today, which generated per-anchor candidates from three mechanism families and lost to the unilateral optimum by 89.7 per cent. This one is a policy over the whole assignment, not a candidate search.

## Why it might work
The measured mechanism is a property of a beam, not of a coalition. Under a rate target with equal-airtime multiplexing, a beam at occupancy 1 or 2 supports no transmitted mode after the fading margin, so its transmitter burns fixed power for zero credited bits. **About 61 per cent of active beam-anchor incidences sit in that regime**: roughly 35.3 per cent at occupancy 1 and 25.7 per cent at occupancy 2.

## What to measure
On the same real anchors used by the ceiling diagnostic, at least 20 anchors, with the exact evaluator on corrected physics from engine commit `75c5c78c`, report pooled energy efficiency for:

* **BASELINE**, the incumbent carrier assignment;
* **UNILATERAL**, iterated exact single-user best response to a certified local optimum, no deadline;
* **FLOOR**, this policy;
* **ORACLE_SET**, the bounded perfect-knowledge set selector, as the reference the others are measured against.

**The number that matters is what fraction of the oracle's gain over unilateral the floor policy captures**, that is `(FLOOR - UNILATERAL) / (ORACLE_SET - UNILATERAL)` on pooled energy efficiency. Report it explicitly.

Also report:
* served counts for every arm at every anchor, since a gain bought by serving fewer users does not count;
* the wall time of the floor policy's decision, since a sub-millisecond rule that beats an exhaustive optimiser is a different and stronger claim than an offline ceiling;
* how many beams the policy consolidated versus emptied, and the resulting occupancy histogram before and after;
* the anchors where the policy made things worse, if any, and why.

## Report honestly whichever way it goes
If the floor captures most of the headroom, say so plainly: that is a physically motivated deployable rule that beats an exhaustive unilateral optimiser, and it is a stronger result than a learned coordinator. If it captures little, say that plainly too: it establishes that the coordination structure is genuinely non-trivial, which the project currently asserts rather than shows. Do not tune the rule to improve the number; if you vary the occupancy threshold, report every value you tried.

## Constraints
Workspace `/home/sat/mcrl-v025-floor-ws`, built with `git -C /home/sat/mcrl-v025-codex-ws-engine archive 75c5c78c | tar -x -C` it, then `git init` and commit. Never write into `/home/sat/mcrl-leo-handover` or its venv, `/home/sat/mcrl-hub`, `/home/sat/mcrl-v025-codex-ws-engine`, or any other `mcrl-v025-*-ws`. Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. Large files under `/home/sat/bigtmp`, never `/tmp`, which is RAM-backed here. At most 3 processes, `nice -n 12`.

Change no threshold, sign, seed, horizon, price, service guard or acceptance rule.

Write `OCCUPANCY-FLOOR-2026-09-10.md` in the workspace root and print it as your final message. Lead with the captured fraction.
