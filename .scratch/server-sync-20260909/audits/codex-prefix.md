Workspace: the current directory, `/home/sat/mcrl-v025-arch-ws`. Interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, `nice -n 15`. Never modify `/home/sat/mcrl-leo-handover` or its virtual environment, and never write into another `mcrl-v025-*-ws` (read-only access to them is fine).

`DIAGNOSTIC_NOT_CLAIM`. No training run, no learner, no policy run. No sealed constant, threshold, sign, seed, horizon, price, service guard or acceptance rule is changed; no sealed artefact or frozen manifest is modified. Every variant is a separate diagnostic evaluation on a copy.

# The structural question

The project's set-level selector is built as a three-stage pipeline:

1. an iterated unilateral best-response search is run to a certified fixed point;
2. a bounded candidate catalogue is generated **around that fixed point** by hand-written rules — same-beam occupant subsets of sizes 2 to 4 with a 1,024 generation cap, victim plus its top-two and top-three physical interference contributors, and complete-beam evacuations, under a global 4,096-configuration cap;
3. the catalogue is ranked and the best is taken, with the unilateral solution itself retained in the catalogue as a fallback.

Only stage 3 is ever learned. So the learned component's floor is the unilateral solution and its ceiling is the exact-ranked catalogue optimum. On the twenty-anchor panel, stage 1 is worth about `+442 %` over a geometry-only baseline and stage 3 is worth about `+6.36 %` under the sealed provisioning rule and about `+0.51 %` under the margin rule.

**The question: how much of the coordination value is reachable without the non-learned optimiser in front of it?**

Reference implementations you should read and reuse rather than rebuild: the panel runner and margin variant in `/home/sat/mcrl-v025-ladder-ws/.scratch/ladder-floor-20260910/` (read-only), and the sweep runner in `/home/sat/mcrl-v025-beam-ws/.scratch/beamwidth/` (read-only). Copy what you need here.

# Arms to measure, on the same anchors, under both the sealed and the margin provisioning rules

- **A0 `BASELINE`** — the nearest-eligible geometric assignment, unchanged.
- **A1 `UNILATERAL`** — the existing iterated best response to its certified fixed point.
- **A2 `ORACLE_FROM_UNI`** — the existing arm: catalogue generated around the unilateral fixed point, exact ranking.
- **A3 `ORACLE_FROM_BASE`** — the identical catalogue generation rules and identical caps, but seeded from **BASELINE** instead of from the unilateral fixed point, with BASELINE retained as the fallback. No unilateral search is run at all.
- **A4 `ORACLE_FROM_BASE_ITERATED`** — A3 applied repeatedly: regenerate the catalogue around the current selection and re-select, until no improvement or a declared iteration cap you state in advance. This tests whether set-level moves alone can reach a comparable endpoint without any unilateral stage.

For A3 and A4 the catalogue generation rules, the size caps, the tie-break, the objective, the price, and the served-count guard must be **identical** to A2. The only change is the configuration the catalogue is seeded from. State explicitly how the guard's reference count is set for each arm and keep it consistent.

# Report, per arm, per provisioning rule

- pooled energy efficiency, and the relative gap to A1 and to A0;
- served counts **and, separately, the count attaining the per-user rate target** — never merged;
- the number of anchors where each arm is worse than A1;
- the number of unique configuration evaluations and wall time per anchor, because the point of the unilateral prefix may be cost rather than quality;
- for A4, the number of iterations to termination.

At least eight anchors; say how many. Use the same anchors across all arms and both rules.

# The three questions to answer directly

1. **Does `ORACLE_FROM_BASE` reach anywhere near `UNILATERAL`?** If set-level moves from a raw geometric assignment recover most of the `+442 %`, then the unilateral stage is a convenience, not a necessity, and a learned selector has a far larger band to work in than `+0.51 %`.
2. **If it does not, what is missing?** Report which move types the unilateral search makes that the catalogue rules cannot express, with counts.
3. **Is the unilateral prefix buying quality or speed?** Compare evaluations and wall time at matched quality.

# Rules

- Do not tune the catalogue rules to improve A3 or A4. Use the existing rules exactly; if you believe a rule is the binding limitation, say so and quantify it, but do not change it.
- If `ORACLE_FROM_BASE` is far worse, say so in the first line. That is a clean answer and it tells the project its learned component is structurally confined.
- Every number reproducible from a script left here, with exact commands.
- Say plainly what you did not reach.

Write `PREFIX-ABLATION-2026-09-10.md` in the workspace root and print it in full as your final message. Lead with one line answering question 1.
