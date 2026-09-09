# Three timestamps: when is the winner found, and when is it certified?

`DIAGNOSTIC_NOT_CLAIM`. Budget 90 minutes. This is instrumentation and measurement, not optimisation. Do not speed anything up in this task.

## Why
The coordinator has a 10 second budget and measured decisions of 5.7 to 9.9 seconds, but nobody knows where the time goes. Two very different situations produce the same total, and they have opposite repairs:

* the eventual winner is **found late**, so candidate generation or search order is the problem;
* the eventual winner is **found early but certified late**, so the problem is eliminating competitors, and the repair is better bounds rather than better generation.

Until these are separated, any speedup work is guesswork.

## What to instrument
Workspace `/home/sat/mcrl-v025-certprofile-ws`: build it with `git -C /home/sat/mcrl-v025-codex-ws-engine archive 75c5c78c | tar -x -C /home/sat/mcrl-v025-certprofile-ws`, then `git init` and commit. Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. Never write into `/home/sat/mcrl-leo-handover` or its venv, `/home/sat/mcrl-hub`, `/home/sat/mcrl-v025-codex-ws-engine`, or any other `mcrl-v025-*-ws`. At most 4 processes, `nice -n 10`.

Record per decision, on a monotonic clock, from the true start of the budget and not after preprocessing:

1. **t_first**: when the first complete, feasible new candidate is available.
2. **t_winner**: when the candidate that eventually wins is first fully evaluated.
3. **t_certified**: when it is established that no remaining candidate can beat it, that is when the reference procedure's selection is fixed.
4. **t_total**: the whole decision.

Also record an exclusive wall-time ledger so no interval is double counted: input and precompute, candidate generation, search bookkeeping, the sum over unique oracle solves, validation and output, and any waiting. For parallel sections report the critical path, not the sum of overlapping times. Count proposed candidates, unique assignments, cache hits, exact solves and fixed-point iterations per decision.

## Run it on the hard cases
At least 20 anchors, and deliberately include the slowest ones rather than a random sample; the tail is the subject. **Run without the production cutoff** so a decision that would have been truncated is observed to completion. A latency distribution that contains only the decisions that finished is censored exactly where the question lives. Report how long the truncated ones actually needed.

## Report
`CERT-PROFILE-2026-09-09.md` in the workspace root, printed as your final message.

Lead with the single most decisive number: **the distribution of `t_certified - t_winner`**, that is how long is spent proving the winner has won after it has been found. Give p50, p95 and max, alongside `t_winner` itself.

Then: the exclusive time ledger as a table, the counts, and a plain statement of which of the two situations above we are in. If the answer is mixed, say which anchors fall in which case.

Add one paragraph on what a valid pruning bound would need here. Our score contains hard decode thresholds, so a Lipschitz enclosure around a fixed-point iterate is not automatically valid: the enclosure must account for a threshold crossing inside it. State whether the engine's structure admits such a bound at all, without implementing one.

## Explicitly out of scope
Do not change any threshold, sign, seed, horizon, price, service guard, acceptance rule, the 10 second budget or the 0.5 second guard. Do not attempt any speedup. Measurement only.
