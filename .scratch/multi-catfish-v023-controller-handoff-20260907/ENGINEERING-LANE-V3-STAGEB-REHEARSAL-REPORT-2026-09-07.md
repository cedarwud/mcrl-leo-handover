# Engineering-lane V3 — Stage-B plumbing rehearsal report (2026-09-07)

**Result: FAIL — `STOP_PLUMBING_INTEGRITY`.** Learned-arm plumbing (checkpoint
schema round trip, keyed field, TLE binding, 10-step masked Q1+Q2 deployment)
verified clean for FULL2/DROP_C1/DROP_C2. BASELINE cannot run against the live
environment: a producer↔consumer mismatch, confirmed not a sync gap.

## Roots
- Shadow checkout (code unchanged; sha256-verified identical to local repo for
  every touched producer/consumer file): `/home/sat/mcrl-v023-successor-shadow-20260907`
- Rehearsal output root: `/home/sat/mcrl-v023-stageB-REHEARSAL-NONFORMAL-20260907T144352Z/`
  (`learned-exports/`, `plumbing-diagnostic-output/`)
- Log: `/home/sat/mcrl-v023-stageB-REHEARSAL-NONFORMAL-20260907T144352Z.log`
- Helper (not added to repo): local `/tmp/.../build_fresh_two_route_checkpoints.py`,
  synced to shadow `.tmp/build_fresh_two_route_checkpoints.py`

## Step 1 — fresh checkpoints
Built via the producer's own
`EEAxisTwoRouteModel(config, train_seed=2927175120652069826).checkpoint_state(update_count=200, route_update_counts={"C1":100,"C2":100})`
+ `torch.save` (never hand-built JSON). `initialization_bytes_sha256` is
identical across all 3 arms (untrained, same seed — expected/fine). Full-file
sha256 is pairwise distinct — FULL2 `4bff95c3…eca9e`, DROP_C1 `4f292b25…64558`,
DROP_C2 `402e500d…b3889` — satisfying the runner's alias guard.
Command: `OMP_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.../src /home/sat/mcrl-leo-handover/.venv/bin/python .tmp/build_fresh_two_route_checkpoints.py --shadow-root ... --model-config .../V023-C1C2-SUCCESSOR-MODEL-CONFIG.json --output-dir .../learned-exports`.
Peak RSS 773,140 KB; wall 1.57s.

## Step 2 — baseline artifacts
Absent from both `/home/sat/mcrl-leo-handover/` and the shadow checkout;
rsynced from the local repo into the shadow checkout at the same relative
path `artifacts/training-2026-08-25-rerun01/main/`. Checkpoint sha256
`e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b` matches the
expected digest exactly. status.json sha256
`3e980bc8c47087ff313c5f5589dab053e0f52440fff692d0c88153af4cce7fa1` (used as
`--baseline-status-sha256`).

## Step 3 — diagnostic
`/usr/bin/time -v .../.venv/bin/python v023_c1c2_successor_plumbing_diagnostic.py --tle-root /home/sat/mcrl-runtime/tle-frozen-20260820 --output .../plumbing-diagnostic-output --learned-checkpoint <FULL2.pt> --learned-sha256 <...> (×3, FULL2/DROP_C1/DROP_C2 order) --baseline-checkpoint <...> --baseline-status <...> --baseline-status-sha256 <...>` → exit 2.

**First failing boundary:** `.scratch/multi-catfish-v023-baseline-adapter/baseline_adapter.py:397-400`
(`_validate_user_state`), raises `BaselineAdapterError("contract_fields are
not part of the native 112-D state")`; reached from
`v023_c1c2_successor_physical_runner.py:944` (`run_episode`, BASELINE branch)
→ `select_actions` → `encode_states` → `encode_user_state`.
**Classification: (b) producer↔consumer mismatch.** `src/mcrl/env/candidates.py:260`
and `step.py:1185` now unconditionally populate `UserState.contract_fields`
with a real ndarray; the frozen baseline adapter still asserts it must be
`None`. Confirmed NOT a sync gap: `baseline_adapter.py`, `step.py`,
`candidates.py`, `step_types.py`, `action_contract.py`, `state_encoding.py`
are byte-identical between the local repo and the shadow checkout. No retry
attempted — no missing-sync condition exists to retry.

Baseline *admission* itself passed (checkpoint/status digest checks,
`BaselineAdapter.from_artifacts`, `FrozenBaselinePolicy.verify()` all ran
before this boundary); only runtime state encoding is broken.

## Timings / RSS (diagnostic)
`phase_wall_times_s`: `input_authentication_s=0.497`, `total_s=46.716` (no
`four_arm_execution_s`/`integrity_verification_s`/per-arm times — the STOP
payload doesn't carry them, only the PASS payload does).
`/usr/bin/time -v`: wall 0:47.89, peak RSS 1,251,008 KB (~1.2 GiB, under the
3 GB budget).

## Claim ceiling / descriptive_physical_endpoints
Not produced this run: STOP occurred before the four-arm loop finished, so no
`plumbing-receipt.json` was written — no `claim_ceiling` or
`descriptive_physical_endpoints` field exists. Only `plumbing-stop.json`
exists: `scientific_decision_emitted:false`,
`q3_evaluated/test_split_opened/episode_training/learner_update:false`. The
producer's defined claim ceiling for a PASS receipt is
`TRAIN_DEVELOPMENT_C1C2_SUCCESSOR_PHYSICAL_EVALUATION_NO_C3_NO_TEST_NO_EFFICACY`
(unreached).
