# SOLO — PROGRESS (resume file)

Task: ONLY_X route-alone EE at oracle level (Level 1) and knockout level (Level 2); report
`SOLO-ROUTES-2026-09-11.md`. Development anchors only; no eval-only dates; no sealed artefact changed.

## Scripts (all in /home/sat/mcrl-v025-solo-ws/scripts)
- `solo_level1.py` (sha256 4d29338b…bb0) — Level 1 per-anchor oracle. Writes one JSON line per anchor.
  Refuses to overwrite an existing --out. Resume = run a NEW --out for the missing global range.
- `solo_level2.py` (sha256 cee4e5bc…b0db) — Level 2 knockout on FULL heads, IN-SAMPLE panels.
- `run_level1.sh` — launches A (0-35) and B (36-71) at once; C (72-92) after `ALL_DONE` appears in logs/level2.log.
- `run_level2.sh` — sequential Level 2 jobs: exact22, q1v3, q1v3_control, exact93 (4000), zq1v1, zq1v2, zview (500).
- `solo_aggregate.py` — reads .scratch/level1/part-{A,B,C}.jsonl + .scratch/level2/*.json -> .scratch/solo-aggregate.json

## Steps completed
1. Smoke of Level 1 on global 000: `.scratch/level1/smoke-000.jsonl` (buggy coalition index for world-2 mapping;
   superseded, not used). Timing ~115 s/anchor unloaded, ~260 s under load avg 27.
2. Level 2 exact22 @4000 (6 seeds): `.scratch/level2/exact22-epoch-4000.json` DONE 00:49Z.
   Per-seed pooled EE (Mbit/J), e.g. seed 6407676579069309528: NONE 11.4955, C1 43.71, C2 39.84, C3 18.69,
   C1+C2 44.64, C1+C3 27.51, C2+C3 34.00, C1+C2+C3 33.98; fullmismatch=0 vs unmodified scorer.

## Detached processes (launched 2026-09-11 ~00:36-00:40Z, cwd /home/sat/mcrl-v025-solo-ws)
- run_level2.sh: bash PID 3248067 -> logs/level2.log; outputs .scratch/level2/<tag>-epoch-<E>.json. Expected ~01:40Z.
- run_level1.sh: bash PID 3250976 -> python PIDs 3250977 (A, 0-35, .scratch/level1/part-A.jsonl, logs/level1-A.log)
  and 3250978 (B, 36-71, part-B.jsonl, logs/level1-B.log); C (72-92, part-C.jsonl) starts after Level 2 ALL_DONE.
  ~260 s/anchor under load -> A,B finish ~03:20Z; C ~03:30Z. Flag file logs/level1-done.flag when all done.

## Next steps
1. When all three parts exist and cover 0-92: run `solo_aggregate.py` (1 process, nice 15, thread pins 1).
2. Write SOLO-ROUTES-2026-09-11.md from .scratch/solo-aggregate.json (first line bold: ORACLE_C1/C2/C3 alone vs
   no route, rel pooled EE + served, and each route target's correlation with realised dEE). Include Pareto
   section (coordinator request) for oracle and knockout lattices, ETAFIX interpretation (Phi / horizon of
   each target), Level 3 proposal, four fields, verified/derived/inferred.

## Facts already established
- Level 1 parity at global 000: fresh C1/C2/C3 vs 93-corpus labels max abs 4.3e-13/5.7e-14/2.4e-13; the
  reconstructed deployed catalogue's multi-user set == coalition shard set (211 rows); 1004 profiles.
- Target construction (code): C1 targets.py:173 core/kappa+dPhi, nominal field, boundary 0 (pilot 550-560);
  C2 targets.py:309-310 (forecast surplus - kappa*lost)/kappa over offsets 1..3, nominal, boundary 0
  (engine 1612-1623, pilot line 87/110 override); C3 targets.py:599-611 Phi-inclusive interaction, nominal b0
  (coalgen build.py 618-635). EE is realised full-48 at the decision step only.
- No-route (BASE) is a weak reference: ~11.0-11.5 Mbit/J, served 69/100 at global 000.
