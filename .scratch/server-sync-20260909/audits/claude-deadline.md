# BLOCKER: the coordinator misses its decision deadline, so every arm falls back to BASE

This is the highest-priority engineering task in the project. Until it is fixed, the overnight matrix returns a null **by construction**: with a 100 % deadline-fallback rate every arm selects BASE, so FULL, DROP_C1, DROP_C2, DROP_C3, S0, UNI, ALL_NEUTRAL_CONTROL and NULL come out bit-identical and every marginal is exactly zero. That is a broken instrument, not a scientific result.

Workspace: `/home/sat/mcrl-v025-codex-ws-engine` (the stage-4h tree, corrected ACM). Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. Never modify `/home/sat/mcrl-leo-handover` or its venv, `/home/sat/mcrl-hub`, or anything under `src/mcrl/env/`. Do not edit sealed files under `.scratch/multi-catfish-v025-physics-successor/`.

## Step 1 — resolve the contradiction inside the stage-4h report (do this first, report before optimising)
`.scratch/multi-catfish-v025-physics-successor/V025-ENGINE-STAGE4H-REPORT-2026-09-09.md`:
* §6 reports a real-anchor gate PASS: decision wall mean 8.250 s, p95 9.816 s, max 9.921 s over **3 anchors**, against a 10 s budget.
* §7 reports a **10-anchor** SMOKE in which *every* coordinator decision missed the ten-second deadline and fell back to BASE, all arms bit-identical at 3.492094 Mbit/J.

Find both measurement sites in the code and the receipts. Determine which measures what, and answer precisely: **are they measuring the same thing under different conditions, or is one of them wrong?** Candidate explanations to test rather than assume: different anchor difficulty; different user counts; cold versus warm tape cache; a per-process versus wall-clock budget; the 0.5 s `S_UNI_BUDGET_GUARD_S` guard; contention from other jobs on the box while §7 ran; the batch kernel being reached in one path and not the other (`evaluate_ar_tdm_catalogue` is only reached when the tape carries compact arrays AND `setting.label == "a-r0"`). Report the answer with the evidence before you change anything.

## Step 2 — make the decision fit the budget at matrix scale
Target: the coordinator's selection completes inside its declared budget on a large majority of **real** anchors, demonstrated at a realistic anchor count (at least 20 anchors across at least 2 worlds), not at 3.

**Legitimate levers**, in the order I would try them:
1. Widen batch-kernel coverage so the fast path is reached for every architecture and view that the matrix actually runs, not only `a-r0`. The measured gap is 0.003 s versus 0.556 s per configuration, a factor of about 180.
2. Vectorise or cache inside the evaluator: memoise per-configuration physics that is invariant across candidates, hoist per-boundary work out of the candidate loop, reuse the k=0 nominal view where the sealed design already says the coordinator ranks there.
3. **Provably lossless pruning only**: a candidate may be skipped only if you can show it cannot be the argmax, for example by a bound that dominates it. Write the proof as a test with a counterexample search on synthetic data.
4. Process-level parallelism inside the decision, if the deployability story permits it, stated explicitly as an assumption.

**Illegitimate, do not do any of these**: raising the 10 s budget or the 0.5 s guard; changing `Δt`; shrinking the candidate catalogue in any way that can change which action is selected; changing any threshold, sign, seed, horizon, λ, κ, η_ref or acceptance rule; tuning anything against a measured energy-efficiency outcome. If you conclude the budget is unreachable without one of these, say so plainly and stop — that is a legitimate finding and I need it tonight, not a workaround.

## Step 3 — prove it did not change the answer
Add a test that, on a fixed set of anchors, the optimised path selects **the identical configuration** as the unoptimised path, for every arm. Bit-identical selection, not merely similar energy efficiency. If selection changes anywhere, that is a defect in your optimisation, not an improvement.

## Deliverable
`/home/sat/mcrl-v023-codex-audits/parallel-20260909/DEADLINE-FIX-REPORT-2026-09-09.md`, printed as your final message. Include: the resolution of the §6/§7 contradiction with evidence; a before/after table of decision wall time (mean, p95, max, fallback rate) at the demonstrated anchor count; what you changed and why each change is lossless; the selection-identity test result; and an HONEST LIMITS paragraph. Commit your work in the workspace. Budget 3 wall hours.
