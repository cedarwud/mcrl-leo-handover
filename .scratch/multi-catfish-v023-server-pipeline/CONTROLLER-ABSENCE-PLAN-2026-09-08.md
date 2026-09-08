# CONTROLLER-ABSENCE-PLAN (written 2026-09-08 13:50 UTC) — what the server pipeline session executes autonomously while the controller session is interrupted

You are the server-resident Claude Code session (tmux `mcrl-pipeline`). The controller's local session will be interrupted for a while. Everything below is ENGINEERING / DIAGNOSTIC lane: you may execute it without waiting. Hard limits stay: never start the real stage-A training (PHYSICS-GO.txt is the only trigger), never edit sealed / read-only files or `*.sha256`, never touch `docs/`, never make or imply the physics decision, never open TEST, never launch the confirmatory ladder or Track B compute. Log every action in PIPELINE-LOG.md and keep STATUS.md current. You may dispatch codex (gpt-5.6-sol implementation in a scratch clone; gpt-6-astra read-only adjudication; binary `/home/sat/.npm-global/bin/codex`, `codex exec --model … -c model_reasoning_effort=high|xhigh --sandbox workspace-write|read-only --skip-git-repo-check -C <dir> -o <final.md> - < prompt.md`). If codex cannot commit because its sandbox blocks `.git`, review the diff and commit yourself with a message naming codex as the author of the change.

Poll every ~10 minutes. Tasks, in priority order:

## T1 — attempt #4 through the step-3 dry-run (already in progress)
Finish per ATTEMPT4-GO + HOLD-REAL-LAUNCH; write READY-FOR-REAL-LAUNCH.txt; then hold.

## T2 — decisive C3-S diagnostic set (churn-null + anchor ablation), development lane
Workspace `/home/sat/mcrl-v023-codex-ws-c3s-baselines` (branch `c3s/diagnostic-arms`). Codex is finishing a second pass; done marker `.tmp-prompts/CHAIN2-DONE`; report `.scratch/multi-catfish-v023-c3s-screen/DIAGNOSTIC-ARMS-REPORT-2026-09-08.md`.
1. When CHAIN2-DONE exists: if the workspace has uncommitted changes, review the diff (only the diagnostic package + tests; nothing under `src/` in place — an explicit copy of the physics path under the diagnostic package is allowed) and commit. Run the package's tests unsandboxed with `/home/sat/mcrl-leo-handover/.venv/bin/python -m pytest` (PYTHONPATH=<ws>/src, thread vars = 1). If any test fails: write `T2-STOP.md` with the failure and stop T2.
2. Follow the report's CLI to build the diagnostic preflight + launch authorities (same pattern as the C3-S screen: evidence manifest / census live in `.scratch/multi-catfish-v023-c3s-screen/` of that workspace — copy the sealed v1 `C3S-EVIDENCE-MANIFEST.*` and `C3S-WORLD-CENSUS.*` from `/home/sat/mcrl-v023-c3s-run/.scratch/multi-catfish-v023-c3s-screen/` if the builder needs them; sidecars for the variant-style builders are `X.sha256`, for the v1 runner `X.md.sha256`; all four OMP/OPENBLAS/MKL/NUMEXPR vars = 1). Run `--dry-run` for one unit.
3. Launch the decisive unit set on the v1 panel (4 worlds × 3 lineages): arms `BASE, LITE, NULL, RANDOM_RENEW, BASE_FORCED_RENEW_4` under `--physics-override none` AND `--physics-override ablate_anchor` (if the report exposes them as separate unit sets, launch both). Detached (`setsid nohup … </dev/null &`), ≤ 8 concurrent units at any time (the nine-arm matrix and other work share the box; check `cat /proc/loadavg` and keep it ≤ 20), logs under `/home/sat/mcrl-v023-c3s-diag-launch-20260908/`. Verify with `pgrep -fc "run_v023_c3s_diagnostic_arms.py --unit"` after launching.
4. When all units EXIT: run `--merge`, then write `/home/sat/mcrl-v023-c3s-diag-launch-20260908/DIAG-RESULT-SUMMARY.md`: pooled EE per arm vs BASE under both physics settings, NULL ≡ BASE check (must be byte/Fraction-identical; if not, say HARNESS_FAIL in capitals), handover counts, lit-beam counts, EE advantage by segment-age phase, and the handover-energy sensitivity table. No interpretation beyond the numbers.

## T3 — audits → astra round 3 consolidation
Six codex read-only audits run in `/home/sat/mcrl-v023-codex-audits/` (`chain.log`; outputs `*-final.md`). astra physics rounds run in `/home/sat/mcrl-v023-astra-physics/` (round 1 → `CHAIN-DONE`, round 2 → `ROUND2-DONE`).
1. As each audit `*-final.md` appears, copy it to `/home/sat/mcrl-v023-astra-physics/ROUND3-<name>.md`.
2. When ROUND2-DONE exists AND at least 4 of the 6 audits are present (or 60 min after ROUND2-DONE, whichever first): run astra round 3 with `/home/sat/mcrl-v023-astra-physics/PROMPT-ROUND3.md` (already staged) → `-o /home/sat/mcrl-v023-astra-physics/astra-physics-round3-final.md`; copy to `/home/sat/mcrl-v023-codex-astra/physics-round3-final.md`; touch `ROUND3-DONE`.

## T4 — summaries of finishing chains (no actions beyond summaries)
- Nine-arm variant matrix: `/home/sat/mcrl-v023-c3s-variants-launch-20260908/CHAIN-DONE` → read `variants-merge.log` and the terminal receipt under `/home/sat/mcrl-v023-codex-ws-c3s-variants/.scratch/multi-catfish-v023-c3s-variants/runs/variants-20260908-r1/`; write `MATRIX-RESULT-SUMMARY.md` (decision per arm, pooled EE vs BASE, latency ranking, LITE-vs-v1 equivalence check).
- Confirmatory-v2 codex (`/home/sat/mcrl-v023-codex-ws-c3s-confirm/.tmp-prompts-confirm/CHAIN-DONE`): commit if needed, run tests, write a 10-line summary in that dir. Do NOT seal or launch.
- Latency codex (`/home/sat/mcrl-v023-codex-ws-c3s-latency/.tmp-prompts/CHAIN-DONE`): commit if needed, run the equivalence tests, summarize.
- Track B multi-lever codex (`/home/sat/mcrl-v023-codex-iter2/.tmp-prompts-trackb/CHAIN-MULTI-DONE`): commit if needed, run tests, summarize. No probe compute.
- Diag/V-E (`/home/sat/mcrl-v023-codex-ws-c3s-diag`): already committed (11d601b1); astra review at `/home/sat/mcrl-v023-codex-astra/diag-ve-review-final.md` (SHADOW_FIX_FIRST | VE_AMEND_THEN_SEAL | LOW) — no action.

## T5 — when the controller returns
Keep a single file `/home/sat/mcrl-v023-pipeline-20260908/ABSENCE-DIGEST.md` updated with: what finished, where each summary is, anything that STOPped, current load. The controller reads that first.
