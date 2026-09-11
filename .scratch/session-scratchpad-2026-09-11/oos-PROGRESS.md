# OOSPANEL progress (resume file)

Last update: 2026-09-11 01:28 UTC

## 1. OOS anchor list and disjointness proof (DONE; gates everything)

- Declared rule (in `scripts/oospanel.py`, `panel_specs()`): the first 10 anchors in exact-source within-world order
  (step ascending; carriers nearest-eligible, stay-if-possible, random-masked) of
  `V025_PROBE/world/3` (panel idx 0-9, steps 0-3) and `V025_PROBE_R2/world/1` (panel idx 10-19, steps 0-3).
  Print them with `python scripts/oospanel.py specs`.
- Development declaration: `/home/sat/mcrl-v025-dates-ws/DATE-ALLOCATION-DECISION-2026-09-10.md` lines 49-52
  (world 3 = 2025-11-16, "Remains development evaluation"; PROBE_R2 dates "Remain development").
  The worker asserts that the tape start date is in that declared set and that the split is TRAIN (fail closed).
  The 48 evaluation-only claim dates were NOT read.
- World 2 was rejected: its date 2026-03-11 is a training-source date (exact93 trains on world-2 step 0; the sealed pilot corpus contains all 90 world-2 anchors).
- Disjointness proof: `out/disjointness.json` (script `scripts/check_disjointness.py`, log `logs/disjointness.log`).
  Overlap is 0 with the 22-anchor set (exact22), 0 with the 93-anchor set (exact93), and 0 with all 32 corpora found
  (every launch receipt, the EXACTGEN2 manifest, the sealed pilot corpora). No corpus contains world 3 or PROBE_R2 at all.

## 2. Encoding / clean-path validation on in-sample anchor 000 (DONE, EXIT 0, peak RSS 2,553,552,896 B)

- `scripts/validate_encoding.py` writes `out/validate-encoding-anchor000.json`; log `logs/validate-encoding.log`.
  It compares the OOS encoders against the training-corpus views (5 schemas), and the clean FP against the RANK2 clean receipt.
  Result: q1v1 992/992 rows bit-identical to the EXACTGEN2 view; q1v2/q1v3/control keys equal, max |dQ1| 1.31e-13
  (ECEF-resolver angle seam), Q2 identical; q1v2z max |dQ1| 5.43e-12. Clean FP == RANK2 clean FP (377 moves,
  10 passes, assignments/bits/joules equal), strict scalar calls 0.

## 3. Per-anchor physics + 5 encodings (RUNNING, resumable)

- Script: `scripts/oospanel.py worker --indices ...`. Launcher: `scripts/run_py.sh LOG ...` (nice 15, threads 1).
  Launch detached: `cd /home/sat/mcrl-v025-oospanel-ws && setsid nohup scripts/run_py.sh LOG scripts/oospanel.py worker --indices ... </dev/null >/dev/null 2>&1 &`
- Fragments: `.scratch/fragments/{core,q1v1,q1v2,q1v2z,q1v3,q1v3-control}/anchor-NN.json`.
  A worker skips any anchor whose 6 fragment files all exist (resume-safe). One world per worker process.
- Running (cwd /home/sat/mcrl-v025-oospanel-ws):
  - PID 3249926: `worker --indices 0 1 2 3 4 5 6` (world 3), log `logs/worker-w3a.log`
  - PID 3249925: `worker --indices 10 11 12 13 14 15 16` (PROBE_R2), log `logs/worker-r2a.log`
  - PID 3292609: `worker --indices 7 8 9` (world 3), log `logs/worker-w3b.log` (started 00:59Z)
  - Timing: anchor 0 took 2501.6 s wall at load ~30 (shortlist 854 s, full-legal 2900 rows/11208 physics calls,
    clean FP 44 s / 374 moves / 11 passes, 990 catalogue profiles, 48 missing actions regenerated), peak RSS 2.58 GB.
    Load fell to ~8 at 01:15Z, so later anchors should be faster. Fragments ~44 MB per anchor (5 schemas).
  - Anchor 0 checks: strict-surface scalar evaluate calls 0; scalar cache misses 0 everywhere;
    endpoint batch outcomes == catalogue outcomes for base/fixed/anytime; certified != anytime (196 of 374 moves by 10 s).
- Chain armed: PID 3307929 (`while kill -0 3292609; do sleep 30; done` then `worker --indices 17 18 19`,
  log `logs/worker-r2b.log`) starts the last PROBE_R2 anchors as soon as w3b exits. Never more than 3 python processes.
- If a slot frees later, a worker may be started on the TAIL indices of a running worker's list (e.g. `--indices 6`);
  completed anchors are skipped by the fragment check and fragment writes are atomic.

## 4. Assembly (TODO)

- `scripts/run_py.sh logs/assemble.log scripts/assemble_oos_panels.py` writes `artifacts/panel-oos-<schema>.json` (+ `.sha256`, `.receipt.json`)
  for schema in q1v1, q1v2, q1v2z, q1v3, q1v3-control. It refuses to overwrite.

## 5. Acceptance (TODO)

- `scripts/score_one.sh TAG CHECKPOINT PANEL RECEIPT PANEL_SHA` (unmodified scorer 8a83bc98..., digest gate).
  Checkpoints, all seed 6407676579069309528: exact22@4000 (q1v1; also exact93@4000), firstrun-v2@500 (q1v2),
  firstrun-v2z@500 (q1v2z), q1v3@4000, q1v3-control@4000. Output goes to `.scratch/acceptance/score-TAG`.
  Report only exit code, F6/F7/F8 counts and peak RSS. No route marginal.

## 6. Report (TODO)

- `OOS-PANELS-2026-09-11.md`.
