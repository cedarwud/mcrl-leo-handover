# Task (gpt-5.6-sol): C3-S diagnostic arms — harness placebo controls + hostile baselines (implementation only, no compute)

Workspace: `/home/sat/mcrl-v023-codex-ws-c3s-baselines` (clone of the E1 checkout at the hardened C3-S v2 runner commit a9702a08), branch `c3s/diagnostic-arms`. Do not touch other worktrees, sealed/read-only files or `*.sha256`. Commit at the end.

Why: the closed-loop kill screen v1 returned SUPPORT (FULL +2.88 %, LITE +2.92 % pooled EE vs the frozen learned BASE; served counts identical; coordinator deviated at all 360 decisions). Two independent red-teams and the owner now demand that (1) the harness be validated with placebo controls and (2) the mechanism be separated from "one-step nominal search merely repairs a weak learned baseline". Receipts (read-only): `/home/sat/mcrl-v023-c3s-run/.scratch/multi-catfish-v023-c3s-screen/runs/c3s-20260908-r1/`.

Read first: `.scratch/multi-catfish-v023-c3s-screen/V023-C3S-SET-LEVEL-COORDINATOR-KILL-SCREEN-CONTRACT-2026-09-08.md`, `c3s_policy.py`, `run_v023_c3s_screen.py`, the tests, `c3s_config.json`, and `.scratch/multi-catfish-v023-c3-existence-e1/e1_estimands.py`.

Implement a separate runner `run_v023_c3s_diagnostic_arms.py` (same unit/merge/dry-run/estimate CLI shape, same preflight/launch-authority pattern with its own builders, same 4 worlds × 3 lineages × 30 steps panel, own trajectories from identical initial states, identical exogenous fading keys) with these arms, each selectable via `--arms`:

**Harness validity (placebo) arms — expected outcomes are KNOWN in advance:**
- `NULL`: a coordinator that goes through the full C3-S code path (catalog, scoring, guard) but always executes BASE's proposal. Must reproduce the BASE arm's trajectory bit-for-bit (same actions, bits, joules, served per step; identical receipt digests apart from timing). Add an assertion mode `--assert-null-equals-base` that fails the unit if any step differs.
- `RANDOM_FEASIBLE`: at every decision, choose uniformly at random (seeded by the repo's world-seed rule on domain `C3S_DIAG/random/{world}/{lineage}/{step}`) among LITE-catalog configurations that satisfy the nominal service guard. Expected: pooled EE ≤ BASE (report the number; no threshold).
- `SHUFFLED_SCORE`: LITE catalog and guard, but the score vector is randomly permuted across candidates before argmax (same seeding rule, domain `C3S_DIAG/shuffle/...`). Expected ≈ RANDOM_FEASIBLE. This tests whether the nominal score carries the information.

**Hostile baselines — mechanism separation:**
- `HEUR`: a non-learned per-user baseline with no Q-heads: each user takes the feasible action with the highest nominal one-step SNR/rate (ties by the repo's canonical tie rule), masked exactly like BASE. Report its pooled EE vs BASE.
- `HEUR_C3S_LITE`: C3-S LITE on top of HEUR, where "top-2 per user" is by nominal one-step F contribution instead of Q1+Q2. If HEUR_C3S_LITE ≈ LITE (learned BASE + C3-S), the learned heads add nothing under the coordinator.
- `NOMINAL_MPC`: pure one-step nominal search with NO learned proposals and NO heuristic prior: catalog = all unilateral edits from the current association + whole-beam evacuations, scored by F with the guard (this is the "just use the simulator" baseline). Report cost.
- `LITE_UNILATERAL_ONLY` and `LITE_EVACUATION_ONLY`: LITE with the catalog restricted to unilateral edits only / evacuations only (V-U/V-J style), to attribute the gain between individual correction and joint moves in closed loop.

Also add an **offline attribution tool** `attribute_c3s_receipts.py` that reads the v1 unit receipts (read-only) and reports, per arm and pooled: counts of executed configuration types (BASE, unilateral, evacuation), number of users moved per decision, active-beam counts per step (if recoverable from actions + masks; otherwise say so), cumulative EE advantage vs BASE by step (to show whether gains are early, steady or concentrated at the end), and the FULL-vs-LITE divergence steps with nominal vs realised deltas at those steps. Output JSON + Markdown.

Constraints: no outcome-driven constants; TRAIN split only; no `sys.modules` aliasing; one-line provenance on every constant; `ALL_NEUTRAL_CONTROL` never relabelled `BASELINE`; tests < 3 min with synthetic fixtures (include: NULL ≡ BASE on a synthetic 3-step world; RANDOM_FEASIBLE respects the guard; HEUR is Q-free; catalog restrictions are exact). Report `.scratch/multi-catfish-v023-c3s-screen/DIAGNOSTIC-ARMS-REPORT-2026-09-08.md` with pytest summary, CLIs, `--estimate` per arm, and the attribution tool's output on the v1 receipts (this last part IS allowed to run now — it is offline reading of receipts, cheap).
