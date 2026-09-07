# Engineering-lane V4/V5/figures — Stage-C rehearsal report (2026-09-07)

**V4: PASS (non-terminal, 100/9000).  V5: NOT EXECUTED — pause boundary 200 is
not admitted (source-confirmed); stopped after step 2 per the instructed
fallback.  Figures smoke: refused by the loader's own contract (checkpoints
deliberately excluded).**

## Step 1 — baseline adapter fix
`rsync -a --exclude __pycache__ sat:/home/sat/mcrl-v023-codex-ws-baseline-20260907/.scratch/multi-catfish-v023-baseline-adapter/ .scratch/multi-catfish-v023-baseline-adapter/`.
`git diff --stat` confirms exactly 2 files: `baseline_adapter.py` +
`test_baseline_adapter.py`, 200 insertions/27 deletions total, nothing else
touched. Fix: `_validate_user_state` no longer rejects populated
`contract_fields`; new `_native_user_state`/`_encode_native_user_state` strip
them before `encode_state`, and `_assert_contract_fields_excluded` proves
contract data cannot change the encoded output (`CONTRACT_FIELDS_EXCLUDED =
True`). Local tests: `PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest
-q -p no:cacheprovider .scratch/multi-catfish-v023-baseline-adapter
.scratch/multi-catfish-v023-c1c2-successor-physical-evaluation
.scratch/multi-catfish-v023-five-arm-evaluation` → **60 passed, 0 failed**
(12+4+12+8+16+8). Pushed to shadow at the same relative path; `baseline_adapter.py`
sha256 identical both sides (`67e4c428…037`).

## Step 2 — V4: 100-episode four-arm rehearsal
New root `/home/sat/mcrl-v023-stageC-REHEARSAL-NONFORMAL-20260907T151800Z`.
Reused V3's three fresh exports unmodified (sha256 verified: FULL2
`4bff95c3…eca9e`, DROP_C1 `4f292b25…64558`, DROP_C2 `402e500d…b3889`) and the
shadow baseline (checkpoint `e6b063ef…`, status `3e980bc8…`) — no rebuild
needed. Plan: `build_v023_c1c2_successor_world_plan.py --output
<root>/world-plan.json` → `plan_sha256=866d28e05b04a361041f829e424a2417f49987239b7771ee94f43022d35e01bb`,
exact match to the declared digest; `--check` OK.
No CLI exists for the real four-arm adapter (the module is a library seam;
`run_v023_c1c2_successor_formal.py` is unrelated Stage-A training), so I wrote
a thin operator driver `run_stage_c_rehearsal.py` (staged under shadow
`.tmp/`, not added to the repo) that wires
`load_learned_two_route_checkpoint`/`load_baseline_policy`/`TleArchive` into
`FixedPolicyEpisodeAdapter`/`FixedPolicyEvaluationRunner` exactly as the
Stage-B plumbing diagnostic already does, plus an observational per-arm
wall-clock wrapper around `adapter.run_episode` — no producer/consumer logic
touched. Pre-flighted with a syntax check, `--help`, and one live real-adapter
episode (FULL2/world-1: 14.5 s, RSS 1.15 GB) before committing to the full
run. Command: `echo 1000 > /proc/self/oom_score_adj; OMP_NUM_THREADS=2
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.../src /usr/bin/time -v
/home/sat/mcrl-leo-handover/.venv/bin/python .../run_stage_c_rehearsal.py
--tle-root /home/sat/mcrl-runtime/tle-frozen-20260820 --plan
<root>/world-plan.json --output <root>/physical-evaluation-output --pause-at
100 [×3 --learned-checkpoint/--learned-sha256, --baseline-checkpoint
/--baseline-status/--baseline-status-sha256] --timing-out
<root>/timing-100.json`, launched detached (`nohup … </dev/null … &
disown`), logged to `<root>.log`.
**Result:** wall 1:10:37 (`run_wall_s=4235.1`), peak RSS 2,019,604 KB (~1.97
GiB, under the 4 GB budget), exit 0. Per-arm τ/episode: FULL2 13.63 s, DROP_C1
13.52 s, DROP_C2 13.54 s, BASELINE 1.66 s (BASELINE has no route heads, hence
cheaper). `checkpoints/checkpoint-000100.json` and `rungs/rung-000100.json`
both present (completed_episode=100, receipts=400, all four
`q3_evaluated/test_split_opened/episode_training/learner_update=false`, claim
ceiling matches); **no `result.json`** (confirmed absent). FULL2/DROP_C1/DROP_C2
pooled endpoints are bit-identical to each other — expected, not a defect:
the three exports share one untrained initialization seed (per the V3
report), so masked-Q1+Q2 argmax picks identical actions; not investigated
further per the engineering-lane claim ceiling.

## Step 3 — V5 interruption drill: NOT EXECUTED
`v023_c1c2_successor_physical_runner.py:72` fixes `PAUSE_BOUNDARIES = (100,
500, 1500, 3000)`; `run()` (~line 1199) rejects any `pause_at` outside that
set with `"pause boundary is outside the cumulative ladder"`. 200 is not an
admitted cumulative pause — confirmed from source, not assumed. Per the
instructed fallback, stopping after step 2 rather than substituting an
unauthorized ~4×-heavier 500-episode leg or a non-runner-mediated drill.

## Step 4 — figures smoke
`rsync -a sat:<root>/physical-evaluation-output/rungs/
/tmp/v4-rehearsal-root/rungs/` (checkpoints deliberately excluded, per
instruction). `PYTHONPATH=/usr/lib/python3/dist-packages ./.venv/bin/python
.scratch/multi-catfish-v023-ch5-figure-pipeline/render_v023_development_curves.py
--input-root /tmp/v4-rehearsal-root --output-dir /tmp/v4-figures
--allow-nonformal` → **does not render**: exit 2,
`FIGURE_PIPELINE_REFUSED: root must contain matching checkpoint and rung
histories` (`render_v023_development_curves.py:304`, `load_root`, which
hard-requires `checkpoints/` alongside `rungs/`). `/tmp/v4-figures` was never
created — no PNG/PDF/`FIGURE-MANIFEST.json` exists, so no watermark or
manifest digest to report. This is the loader's own input contract, not a
producer↔consumer defect.
