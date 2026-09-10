Workspace: the current directory, `/home/sat/mcrl-v025-c1c2suff-ws`. Read-only access to sibling `mcrl-v025-*-ws` workspaces is fine. Interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, `nice -n 15`. Never modify `/home/sat/mcrl-leo-handover` or its virtual environment, and modify nothing sealed.

`DIAGNOSTIC_NOT_CLAIM`. No production training run, no policy run, no acceptance test. Change no constant, threshold, sign, seed, horizon, price, guard or acceptance rule; modify no sealed artefact, manifest, contract or acceptance test. **Do not change `PILOT_PRIMITIVE_SOURCE_FALLBACK`; leave it exactly as you find it.**

# The defect, and why patching it is probably the wrong response

Two diagnostics in this workspace established that the pilot's row builder does not produce the production targets. `scripts/run_v025_pilot_c3.py:89` sets a fallback; `_build_anchor_rows` therefore dispatches to `_build_anchor_rows_primitive`, which never calls the production target functions. Instead it defines survival as geometric legality — future visibility, D2 eligibility, cell reachability — and writes that same boolean into **both** the validity and survival fields. The exact target uses a different predicate entirely: it evaluates the whole configuration and requires **every changed user** to be in the served set, and it applies an absorbing rule the encoded row does not.

Measured consequences: **822 of 1,784** valid non-reference rows across two anchors carry at least one wrong survival flag, and 1,022 of 1,784 are affected counting validity too. On the learnability side, a linear model reaches R² 0.598 on the surrogate label against **0.151 on the production target**, so every earlier read of learnability measured an easier problem.

A design review's conclusion was **not** to patch the surrogate but to stop using that path: *"no conclusion about learnability should be drawn from those rows."* A separate diagnostic noted that the **non-fallback source builder would pass the exact validity and survival values through correctly**.

**So the question is not how to fix the surrogate. It is whether the correct path is affordable for the panel that must be built next.**

# What to determine

**Q1. Confirm the correct path exists and is correct.** Read `_build_anchor_rows` and the non-fallback branch. Show, with `file:line`, that it calls the production target functions and passes exact validity and survival through. Identify precisely what it costs that the surrogate avoids — which evaluations, of what, how many per row.

**Q2. Measure the cost.** On a small number of real anchors, build rows both ways and report wall time, evaluation counts and peak memory per anchor for each path, with the ratio. Use the smallest configuration that exercises the real code path, and say what you used. Do not extrapolate a whole-panel figure from a single anchor without saying so.

**Q3. Project it.** The panel that must follow is nine arms over a set of anchors, with each arm keeping its own seed and catalogue and a shared physical cache. Given your measured per-anchor cost, state what the exact path implies for that panel, and what the surrogate path would have saved. Give the arithmetic, not an impression.

**Q4. Is there a middle?** For example: exact targets for the rows that actually enter training, with the cheaper path used only where the value provably cannot affect a label; or caching the coupled evaluation across rows that share a configuration. Say whether any such option is sound, and be explicit that a cheaper option which changes a label is **not** acceptable.

**Q5. What else the fallback path corrupts.** Both target routes were checked for survival and validity. Sweep the primitive builder for **any other field** it fills with a proxy rather than the production quantity, and list them with `file:line`. The project needs the full list before it decides which path to run.

# Rules

- **If the exact path is affordable, say so in the first line** with the number. That is the answer the project wants and it must be stated plainly.
- If it is not affordable, say what dominates the cost.
- Distinguish what you verified by running code from what you read and what you inferred.
- Every number reproducible from a script left here with exact commands.
- Say plainly what you did not reach.

Write `EXACT-ROW-PATH-COST-2026-09-10.md` in the workspace root and print it in full as your final message. Lead with one line: whether the exact row-building path is affordable for the coming panel, and the per-anchor cost ratio against the surrogate.
