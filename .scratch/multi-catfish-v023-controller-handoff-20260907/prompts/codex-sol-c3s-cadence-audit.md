# Read-only audit (gpt-5.6-sol, high effort): comparator fairness and decision cadence in the C3-S v1 / diag2 harness

You are auditing, not fixing. Sandbox is read-only. Workspace: `/home/sat/mcrl-v023-codex-ws-c3s-baselines` (branch of the mcrl-leo-handover repo; the harness lives under `.scratch/multi-catfish-v023-c3s-screen/`; the environment under `src/mcrl/env/`, the deployable decoder / set-level machinery under `src/mcrl/ee_axis*` and `.scratch/multi-catfish-v023-c3s-screen/*.py`). Use `/home/sat/mcrl-leo-handover/.venv/bin/python` only for read-only inspection (imports, printing constants); do not run simulations.

## Observed facts you must explain (diag2 receipts, old physics, 4 worlds × 3 lineages × 30 steps, ≈ 100 users)
- LITE (deployable set-level decoder) vs BASE (masked argmax(Q1+Q2)): pooled EE +2.922 % with segment anchoring, **+3.327 % with the anchor ablated** (`--physics-override ablate_anchor`, 8/12 units so far, 8/8 positive); bits +1.5 %, joules −1.3…−1.8 %; lit beams 40.6 vs 41.2 per step; LITE changes only ≈ 2 user decisions per step relative to BASE; served identical.
- BASE_FORCED_RENEW_4: +0.494 % anchored, **exactly +0.000 % (bit-identical to BASE) with the anchor ablated** — the renewal premium is the anchor artefact; LITE's gain is not.
- RANDOM_RENEW: ≈ −1.1 % in both settings.
- **LITE's EE advantage grows monotonically with `dwell_phase_index`**: anchored 0:+1.36 %, 1:+1.70 %, 2:+3.86 %, 3:+9.84 %; ablated 0:+1.39 %, 1:+1.79 %, 2:+4.80 %, 3:+11.30 %.

## Questions (answer each with verified file:line evidence; label every statement VERIFIED / INFERRED / UNKNOWN)
1. What is `dwell_phase_index` exactly (what resets it, what N=4 governs — candidate refresh, minimum residence, D2 gate timing)? Which arms' decisions are constrained by it and how?
2. Decision cadence: at which steps may BASE change a user's association, and at which steps may LITE? Is there any step where LITE may re-decide (or re-select a beam/satellite) while BASE is structurally held (mask, candidate cache, hysteresis, "stay-if-possible" rule)? If yes, quantify how often across the phase cycle.
3. Candidate sets: are the catalogues / candidate slots scored by LITE identical to the masked action set available to BASE at the same step (same NORAD/beam identities, same masks, same D2 gate)? Any superset or refreshed geometry on the LITE side?
4. Information: does LITE consume anything BASE cannot see at decision time (realised fading, exact SINR after joint resolution, future geometry, other users' simultaneous choices resolved before its own decision)? Is BASE's Q-input snapshot older than LITE's geometry snapshot within a step?
5. Given 1–4, which of these explains the phase-monotone gain: (a) BASE's staleness within the refresh cycle (LITE = fresher re-evaluation), (b) genuine set-level coordination whose value rises as geometry drifts, (c) an accounting/phase-binning artefact (e.g., per-phase bits/joules attribution, phase index misaligned between arms), (d) something else? Rank with evidence.
6. Propose the **minimal** additional diagnostic arms (no more than three) that separate cadence/information from coordination — e.g. `LITE_PHASE0_ONLY` (LITE decides only when BASE's candidates refresh, holds otherwise), `BASE_FRESH` (BASE re-scored on refreshed candidates every step, if the env permits), `LITE_SAME_INFO` (LITE restricted to BASE's exact observation). For each, say precisely which code path would implement it and what result pattern would confirm (a) vs (b).

Deliverable: write `/home/sat/mcrl-v023-codex-audits/C3S-CADENCE-AUDIT-2026-09-08.md` (create the file with the final message if the sandbox forbids writing; the wrapper captures your last message to `-o`). Keep it under 250 lines. No fixes, no reruns, no new gates.
