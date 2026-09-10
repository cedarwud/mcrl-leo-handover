Workspace: the current directory, `/home/sat/mcrl-v025-ladder-ws`. Read-only access to sibling `mcrl-v025-*-ws` is fine, in particular `/home/sat/mcrl-v025-harness-ws` which holds today's anytime work and its first-improvement implementation. Interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, `nice -n 15`. Never modify `/home/sat/mcrl-leo-handover` or its virtual environment.

**Process limit: at most 4 concurrent worker processes.** This is a shared machine and two jobs today drove it to load 64 and 70 with a gigabyte of memory left. `nice` does not limit concurrency.

`DIAGNOSTIC_NOT_CLAIM`. No learner, no training run, no policy run. No sealed constant, threshold, sign, seed, horizon, price, service guard or acceptance rule is changed; no sealed artefact or frozen manifest is modified.

# The gap this fills

The project's entire improvement over its geometric baseline — roughly **+450 %** — comes from an iterated exact best-response search over single-user reassignments, run to a certified fixed point. Everything learned sits downstream of that and contends for a further **one per cent**.

**Nobody has ever asked how far that fixed point is from the best achievable assignment.** An adjudication stated the limitation plainly: the certificate establishes local optimality **in the specified neighbourhood**, and the bounded joint search establishes a maximum **over its bounded candidate family**; neither is a global optimum.

Today's anytime work gave a first hint of how local it is: merely accepting the **first** strict improvement instead of completing a best-improvement sweep reaches a fixed point **8.13 %** higher under the sealed rule, on all twenty anchors. **Two traversal orders of the same neighbourhood differ by eight per cent.** We have seen two local optima and have no idea how many there are or where the best one lies.

# What to measure

Use the **first-improvement** search that the anytime work implemented — cite its implementation digest and reuse it rather than reimplementing. Run under **both** provisioning rules, on a panel of at least eight real anchors; state which.

**M1 — multi-start spread.** Run the same search to convergence from **at least eight** distinct legal starting assignments per anchor: the nearest-eligible baseline, and the rest drawn by a stated deterministic randomisation over legal options with a stated seed. Report, per anchor and pooled: the endpoint efficiency of each start, the spread, the best-of-k, and **how much the best-of-k exceeds the single nearest-eligible start** — which is the quantity the project has been treating as its reference.

**M2 — is the fixed point even locally optimal under pairwise swaps?** The declared neighbourhood is single-user reassignment. Take each converged endpoint and test whether any **swap of two users' assignments** strictly improves the exact objective. Report the fraction of endpoints that are **not** 2-swap optimal and the size of the improvements available. If many endpoints fail this test, the declared neighbourhood is leaving value on the table that no learned ranker downstream can recover.

**M3 — a genuine upper bound, if one is cheaply obtainable.** On the smallest instance that is still real — few users, few beams — compute or bound the true optimum by exhaustive or exact means and state the method. If no exact bound is affordable, say so plainly and report the best value any method here found instead, labelled as a **best-known value, not a bound**.

**M4 — what this implies.** State how far the project's reference fixed point sits below the best value found, as a percentage, under both rules.

# Rules

- **If the multi-start spread is small and the endpoints are 2-swap optimal, say so in the first line.** That would mean the reference is close to the achievable ceiling and the learned layer's one-per-cent working range is a property of the problem, which is a useful and reassuring finding.
- If the spread is large, do not speculate about what a learner could do with it. Report the size of the gap.
- Do not tune the search. Use it exactly as implemented.
- Every number reproducible from a script left here with exact commands.
- Say plainly what you did not reach.

Write `MULTISTART-CEILING-2026-09-10.md` in the workspace root and print it in full as your final message. Lead with one line: the multi-start spread, the fraction of endpoints that are not 2-swap optimal, and how far the project's reference sits below the best value found.
