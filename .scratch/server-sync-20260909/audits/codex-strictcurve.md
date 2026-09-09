Workspace: the current directory, `/home/sat/mcrl-v025-beam-ws`. Interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, `nice -n 15`. Never modify `/home/sat/mcrl-leo-handover` or its virtual environment; read-only on sibling workspaces, never write into them.

`DIAGNOSTIC_NOT_CLAIM`. No training run, no learner, no policy run. **No sealed constant, threshold, sign, seed, horizon, price, service guard or acceptance rule is changed**, and the declared sealed provisioning rule is not being replaced. Every variant point is a separate diagnostic evaluation on a copy. The one-sided beam half-power angle stays at its sealed 1.66° for the sealed arm; other widths are diagnostic points only, exactly as the existing sweep already treated them.

# The defect in the existing evidence

An adversarial adjudication found that the project's margin-provisioning results come from **two different numerical implementations**, and that this has not been controlled:

- **Simple division** — `/home/sat/mcrl-v025-beam-ws/.scratch/beamwidth/margin_batch.py:18` divides the SINR target by the quantile and nothing more. This produced the published five-width curve.
- **Strict clearance** — `/home/sat/mcrl-v025-ladder-ws/.scratch/ladder-floor-20260910/cleared_margin_batch.py:394` adds a clearance loop that verifies both nominal `Γ/q` clearance and quantile-adjusted target-mode clearance.

Simple division leaves **1,179 uncapped occupancy-one no-mode attempts sitting only 5.76e-12 to 2.616e-9 dB below their threshold** — numerically induced failures, not physical ones. On the twenty-anchor panel the two implementations give joint-over-unilateral gaps of **+0.544766 %** and **+0.512537 %** respectively, with selectors reoptimised. On the eight-anchor beam panel at 1.66° they give **−0.302750 %** and **−0.176800 %**, and their committed assignments agree at only **18 of 24**.

**The five-width curve has never been produced under the strict implementation.** Every corrected-physics beam-width number the project holds is therefore from the implementation with the numerical defect.

# The task

**Produce the five-width curve under the strict-clearance implementation, and present all three curves side by side: sealed, simple-division margin, strict-clearance margin.**

Hold everything else exactly as the existing sweep did: the same eight anchors, `V025_PROBE_R2/world/1` and `/2`, steps 0–3, 100 users, the same seeds, the same neutral baseline, the same iterated unilateral procedure with its terminal certificate, the same bounded catalogue rules and caps, the same selection-then-commit separation over all 48 realised boundaries, the same pooled aggregation. Only the numerical clearance changes between the two margin arms.

Before running the sweep, establish two things and report them:

1. **Reproduction.** With the quantile divisor set to one, the strict implementation must reproduce the sealed receipts bit-identically on bits, transmissions, mode counts and maximum radiated power. State the assertion result. The adjudication notes this all-ones check establishes original-rule reproduction but **does not** establish correct target clearance when the divisor is the quantile, so also state what you did to check the latter.
2. **The clearance algorithm itself.** Describe precisely what the strict loop does, at which scalar and dense sites, its termination condition and its iteration budget, and whether the scalar and dense paths agree. The adjudication requires this to be part of any reviewed specification.

# Report, per width, for all three arms

- pooled efficiency for the neutral baseline, the certified unilateral fixed point and the bounded joint selector;
- the joint-over-unilateral gap and the number of anchors where it is negative;
- served counts **and, separately, rate-target attainment** — never merged;
- the number of occupancy-one no-mode attempts, and how many of those sit within 1e-8 dB of their threshold;
- committed-assignment agreement between the two margin implementations, per width.

Then answer directly: **does the strict implementation change the sign or the shape of the corrected beam-width curve?** Report where the two margin curves disagree and by how much.

# Rules

- Do not tune the clearance loop to change a sign. Take the existing implementation as it stands; if you must adapt it to this runner, say exactly what you changed and show that the adaptation is behaviour-preserving on the ladder panel.
- If the strict curve is also negative at the sealed 1.66° width, say so in the first line. That is the outcome that matters.
- Every number reproducible from a script left here with exact commands.
- Say plainly which widths you did not reach; reduce anchors before dropping widths.

Write `STRICT-CLEARANCE-CURVE-2026-09-10.md` in the workspace root and print it in full as your final message. Lead with one line: whether the strict implementation changes the sign or shape of the curve, and the strict gap at 1.66°.
