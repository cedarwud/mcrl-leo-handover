# PROGRESS-A — lane A (engineering / training owner), MC2 round

Worktree: /home/u24/papers/mcrl-leo-handover-mc2  branch mc2/judge-override-20260912  base 6136c514
Contract: .scratch/mc2/MC2-CATFISH-IDENTITY-AND-INTERVENTION-CONTRACT-2026-09-12.md

## Steps
- [x] 0. read contract + code
- [ ] 1. implement cf_judge.py + arm 10 (MC2-JGO-v1) in cf_dev.py + seeds/launcher in dev_e0_common/launch
- [ ] 2. tests (10 contract tests + mutants)
- [ ] 3. local smoke (3 eps) per source set, timings
- [ ] 4. commit (named paths), read hash back
- [ ] 5. sync to sat /home/sat/mcrl-v025-mc2-ws/tree (tar + sha256), COMMIT file
- [ ] 6. check .scratch/mc2/B/CONTRACT-COSIGN.md -> launch or stop at READY
- [ ] 7. launch ep-100 matrix (8 then 2), verify /proc
- [x] 8. rule screen DROPPED by controller (controller runs its own P0 probe, cwd /home/sat/mcrl-v025-cf2s-multi-ws/tree, cmdline mc2_judge_probe.py; counts toward the 8 cap)
- [ ] 9. MC2-ARB-v2 code + tests (not launched)

## Log

- sat ws /home/sat/mcrl-v025-mc2-ws/ created by controller with controller-probe/ (DO NOT TOUCH). Lane A owns tree/ and runs-ep100/ beside it.
- sat runner facts: cd tree; PYTHONPATH=<tree>/src; MCRL_TLE_ROOT=/home/sat/mcrl-v025-cf3-pilot-ws/tle-pinned-427e6a91; threads=1; interp /home/sat/mcrl-leo-handover/.venv/bin/python (-> /usr/bin/python3.13); calibration /home/sat/mcrl-v025-cf3-pilot-ws/premeasure/calibration.json sha 59952214...
- step 1 code written (uncommitted): src/mcrl/algorithms/cf_judge.py (new), cf_dev.py (seeds 19, base 9_243_000, S1 forbidden by name, JudgeSpec, trainer wiring), scripts/dev_e0_common.py (arm 10), run_dev_e0.py (--sources), dev_e0_launch.py (rewritten: ARM:K:A+B grammar, k<=19, k=9 refused, --launch-limit, /proc worker cap 8), tests/test_cf_dev.py pinned (9_231_000,10)->(9_231_000,20)
- 2026-09-12 controller scope change -> contract r1: v1 and v2 run CONCURRENTLY at ep100. Arm 10 = ("MC2", equal_share) parameterised over (rule, source set):
  cells v1-A+B, v1-A+R, v2-A, v2-A+B, v2-A+R, shared B (rule-independent id MC2-B-ONLY-SHARED-v1; test: v1 and v2 paths give identical labels + params on {B}).
  ep-100 root runs-ep100: 16 runs = {1, 4, 10:B, 10:v1-A+B, 10:v1-A+R, 10:v2-A, 10:v2-A+B, 10:v2-A+R} x k=10,11; judge-heavy first, 8 workers, launch-limit waves.
  launch gate: first line of .scratch/mc2/B/CONTRACT-COSIGN.md == "STATUS: COSIGNED r1".
  v2 is implemented in the SAME commit as v1 (manifest needs all 16 hashes from one code identity).

## Receipts (2026-09-12)
- commit **11466998843d94424298d3a6dac0cb3eb5d38279** (read back from git; v1 + v2 + shared B in ONE commit, so the v2-before-any-ep100-DEVVAL ordering holds by construction)
- files: src/mcrl/algorithms/cf_judge.py (new), src/mcrl/algorithms/cf_dev.py, scripts/dev_e0_common.py, scripts/run_dev_e0.py, scripts/dev_e0_launch.py, tests/test_mc2_judge.py (new), tests/test_cf_dev.py
- tests: 87 passed (20 new MC2 + 67 pre-existing: test_cf_dev 24, test_cf_multid3 16+, test_cf_tnext), WALL 326.5 s, rc=0 -> .scratch/mc2/logs/clean-suite-r1.log
- mutants all RED -> .scratch/mc2/logs/mutants-lane-a.log: gate_ge (test_04), judge_advances_rng (test_02), b_no_abstain_final (test_04), null_reads_tnext (test_05 A+R), margin_refilled (test_02b), arb_ties_to_a (test_02b)
- smoke (local, 100 users, 3 eps + 2 DEVVAL, sequential) -> .scratch/mc2/logs/smoke-lane-a.log:
  cell            wall_s(train only)  evals/ep(eps1.0 -> 0.01)  judge_wall_s/ep   dose
  v1-A+B          84.4                1288 -> 902..930         26.4 -> 15.4      1.000
  v1-A+R          104.2               1675 -> 1401..1546       34.0 -> 24.6      1.000
  v2-A+B          99.5                1605 -> 1176..1278       34.0 -> 19.9      0.79 -> 0.67
  v2-A+R          112.8               1806 -> 1579..1641       36.2 -> 27.7      0.79 -> 0.61
  v2-A            62.0                969 -> 672..728          19.4 -> 12.0      0.68 -> 0.53
  B (shared)      60.4                867 -> 670..712          17.7 -> 11.0      0.69 -> 0.54
  D3-T0 (arm 4)   18.9                -                        -                 1.000
  override / challenger-win rates per 1000 decision rows: v1-A+B 366..330, v1-A+R 249..176,
  v2-A+B B-wins 292..225 (A-wins included in judge_overrides), B-only 471..341, v2-A 695..388 A-wins
- sync: tar sha256 87be702442709984e340fd9d4bb93341afc35e4f7048f331bec23883a3d71270 identical both ends;
  /home/sat/mcrl-v025-mc2-ws/tree unpacked, tree/COMMIT = 11466998843d94424298d3a6dac0cb3eb5d38279;
  tree/src/mcrl/algorithms/cf_tnext.py sha256 86f0d6ee... (pinned); cf_judge.py sha256 3de970b2... (== local)
- cosign gate: .scratch/mc2/B/CONTRACT-COSIGN.md first line = "STATUS: COSIGNED r1" -> launched without asking
- ep-100 root /home/sat/mcrl-v025-mc2-ws/runs-ep100, RUN-MANIFEST.json with all 16 specs, code digest ede2c580aaa9
- WAVE 1 launched 2026-09-12T05:59:03Z, 8 runs, PIDs 3777064..3777071, all /proc-verified
  (exe /usr/bin/python3.13, cwd /home/sat/mcrl-v025-mc2-ws/tree, cmdline ... --episodes 300 --stop-after 100 --cell X),
  identity verified 8/8 against the manifest (config hash, code digest, commit, calibration, TLE)
  3777064 10:10:v1-A+B  3777065 10:10:v2-A+B  3777066 10:10:v1-A+R  3777067 10:10:v2-A+R
  3777068 10:10:B       3777069 10:10:v2-A    3777070 10:11:v1-A+B  3777071 10:11:v2-A+B
- WAVE 2 pending (launch as slots free, same manifest, --launch-limit): 10:11:v1-A+R, 10:11:v2-A+R, 10:11:B,
  10:11:v2-A, 1:10, 4:10, 1:11, 4:11
- sat helpers (outside tree/, uncommitted): ep100.sh, ep300.sh (ep-300 prepared, NOT launched), verify_runs.py
- ep-300 roots: /home/sat/mcrl-v025-mc2-ws/runs-ep300 created, ep300.sh takes the primary (v1|v2) and builds
  primary cells at k=12,13,14 + fixed-order fallback at k=15,16,17 in ONE manifest; nothing launched
- wave 1 health at +185 s: RSS 0.92-1.04 GB per run (cap 4.5 GB, MemoryMax 5G), sat load 7.8 on 20 CPUs
- ep-300 prepared and validated locally for BOTH primary options: 33 specs each
  (v1 primary: 15 primary runs k=12,13,14 + 18 fallback k=15,16,17; v2 primary: 18 + 15), all fresh, no hash collision
- wave filling automated by .scratch/mc2/fill_waves.sh under a persistent Monitor: local loop, SHORT ssh calls
  (count live workers, then one ./ep100.sh --launch-limit <free slots>); exits when all 16 have a status.json
- 06:12:38Z wave filler round 7: slot freed -> launched 10:11:v1-A+R pid 3801582 (/proc-verified, identity OK)
  reason the slot freed: 10:10:B stopped cleanly at ep 100 (wall 805 s, rss 1.88 GB, devval written) and
  10:10:v2-A likewise (wall 770 s). The launcher's "stopped-at" state kept both from being relaunched.
  first raw DEVVAL ep100 readings (development lane, no verdict): B k10 ee=1.046408e8 served=0.99746 agreeT0=0.4578;
  v2-A k10 ee=1.088959e8 served=0.99842 agreeT0=0.5873
- measured sat pace with 8 concurrent: cheap judge cells (B, v2-A) ep100 in ~13 min; v1-A+B ~25 eps/5.8 min
