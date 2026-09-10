Workspace: the current directory, `/home/sat/mcrl-v025-harness-ws`. It holds the standing evaluation harness and today's anytime and reseeded-span work; **read `EVAL-HARNESS-2026-09-10.md`, `ANYTIME-UNILATERAL-2026-09-10.md` and `RESEEDED-SPAN-2026-09-10.md` first and reuse them.** Read-only elsewhere. Interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, `nice -n 15`. Never modify `/home/sat/mcrl-leo-handover` or its virtual environment.

**Process limit: at most 4 concurrent workers.**

`DIAGNOSTIC_NOT_CLAIM`. No learner, no training run, no policy run. No sealed constant, threshold, sign, seed, horizon, price, service guard or acceptance rule is changed.

# The defect in a number the project is making decisions on

Every association result rests on this figure: the bounded joint selector beats the certified unilateral fixed point by about **one per cent** under corrected physics. The owner has concluded, reasonably, that one per cent is not a meaningful result, and a possible change of research direction hangs on it.

An adjudication has just found that **the figure is certified against a different objective from the one it reports**:

- **selection** maximises `F = B − η_ref·E` at **realised boundary zero**, at a fixed price;
- **reporting** uses **pooled committed efficiency over all 48 realised boundaries**.

Its wording: *a local certificate for that fixed-price snapshot score is not a certificate for pooled committed efficiency; the reported roughly one per cent is not, merely by being attached to a certified local optimum or an exhaustive bounded catalogue, the association layer's entire room under the project's objective.*

**So the association layer's room may be larger than one per cent, and nobody knows by how much.**

# The measurement, chosen to be cheap

Do **not** re-run the whole search against the expensive objective. Test the neighbourhood of the endpoints that already exist.

**O1 — is the certified fixed point a local optimum under the reported objective?** For each anchor, take the converged unilateral endpoint and enumerate its legal single-user moves. Evaluate each under the **reported** objective — pooled committed efficiency over all 48 realised boundaries — with the unchanged service guard. Report the fraction of endpoints for which at least one single-user move **improves** the reported objective, and the size of the best available improvement, per anchor and pooled.

**O2 — the same for the joint selection.** Take the configuration the bounded joint selector commits and test whether any single-user move, and separately any catalogue row it rejected, is better under the reported objective. Report how often the selector's choice is not the catalogue's best under the objective actually reported.

**O3 — the corrected span.** Using the reported objective throughout for both arms, restate the joint-over-unilateral figure. If the endpoints move under O1, follow the improving moves to convergence **under the reported objective** and report that span too, stating the extra cost.

**O4 — how much of the mismatch is the price, and how much is the horizon?** The proxy differs from the objective in two ways: a fixed price `η_ref` instead of the realised ratio, and one boundary instead of forty-eight. Separate them: evaluate the same neighbourhoods under fixed-price-over-48-boundaries and under realised-ratio-at-boundary-zero, and say which of the two substitutions carries the discrepancy.

Run under **both** provisioning rules. Use the same twenty-anchor panel as the reseeded-span work, and the same first-improvement local search.

# Rules

- **If the certified endpoints are already local optima under the reported objective, say so in the first line.** That would confirm the one per cent and close the question, and it is just as valuable as finding a gap.
- Do not tune the objective, the price or the guard. This measures a mismatch that already exists.
- State the extra cost of evaluating the reported objective inside a search loop, since that is presumably why the proxy was adopted.
- Every number reproducible from a script left here with exact commands.

Write `OBJECTIVE-MISMATCH-2026-09-10.md` in the workspace root and print it in full as your final message. Lead with one line: whether the certified endpoints are locally optimal under the objective the project actually reports, and what the corrected span is.
