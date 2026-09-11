HANDOFF-SAFE: 2026-09-11T11:40Z (server clock) — 12 runs training detached on sat (tree f297334e); detached post-job PID 3438182 will evaluate + report into sat:/home/sat/mcrl-v025-cf3-pilot-ws/report/ (REPORT-DONE / REPORT-FAILED); takeover commands in .scratch/cf3-pilot/TAKEOVER.md

# CF3PILOT — progress (three-catfish short-episode pilot)

Agent: CF3PILOT. Declaration (frozen): `.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-DECLARATION-THREE-CATFISH-PILOT-2026-09-11.md` (commit c4f9ea82).
Local tree `/home/u24/papers/mcrl-leo-handover`; server ws `/home/sat/mcrl-v025-cf3-pilot-ws` (fresh, git init); python `/home/sat/mcrl-leo-handover/.venv/bin/python` (read-only use).
Dependency: `READY FOR PILOT:` line in `.scratch/b0-corrected/PROGRESS.md` — **SEEN 09:06 UTC**: `READY FOR PILOT: 363845e8 ; TLE archive /home/sat/mcrl-v025-b0-ws/tle-pinned-427e6a91 sha256 427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9` (local copy `/home/u24/mcrl-runtime/tle-pinned-427e6a91`). src/scripts/tests at HEAD b50cd087 are identical to 363845e8 (git diff empty).

RULE: a step is marked DONE only when its output exists; no numbers written before they are measured.

| # | Step | State | Output to check |
|---|------|-------|-----------------|
| 0 | Read declaration, frontier doc, codebase | DONE 09:20 UTC | — |
| 1 | Addendum for ambiguities (before launch) | PENDING | `.scratch/cf3-pilot/DECLARATION-ADDENDUM.md` |
| 2 | Implement cf_ratio learner + catfish sources + trainer (Amendment 1 applied) | DONE — worktree commit (see step 3) | `src/mcrl/algorithms/cf_ratio.py` |
| 3 | Tests (fail-then-pass) | DONE ~10:25 UTC: 13/13 green; each red under its named mutant (log below) | worktree `tests/test_cf_ratio.py` |
| 4 | Wait for READY FOR PILOT | DONE 09:06 UTC (commit 363845e8) | b0-corrected PROGRESS line 1 |
| 5 | Server ws setup at READY commit + pinned archive | DONE 09:56 UTC: `/home/sat/mcrl-v025-cf3-pilot-ws/tree` = git archive of worktree commit `b270592f` (= 363845e8 + CF3 commits 6bfebd8e, b270592f; tarball sha256 2424ec1b…97a0, scp hash verified); pinned TLE copied to `ws/tle-pinned-427e6a91` (373 files) | sat ws |
| 6 | eta_0 on calibration seeds + Amendment-1 item-4 source re-measurement (no training) | RUNNING since 09:57 UTC — see below | `sat:ws/premeasure/calibration.json` |
| 7 | Smoke: every arm 3 ep, one eta/lambda update, one eval; per-episode timing | DONE 10:04 (server): 6/6 complete (A1 s0-2, A0/A2/A3 s0); eta held ep0-1, updated at 2, final not applied; lambda update path run (stayed 0); batch rows 113:5:5:5; learning-check barrier exercised (smoke DECISION pass, 2-episode smoke calibration — not a reading); smoke eval of A2s0/A0s0 policies with --repeat launched 10:04 | `ws/smoke/` |
| 8 | Launch 12 runs (A0/A1/A2/A3 x seeds 0-2) x 1000 ep detached | **LAUNCHED 11:14:42 UTC** (server), tree f297334e, after PROCTEST PASS + coordinator GO | see LAUNCH-2 section |
| 9 | Evaluate final checkpoints | PENDING | eval json |
| 10 | Report | PENDING | `CF3-PILOT-2026-09-11.md` |

## Sub-agents (resume protocol)
- 09:05 UTC: CF3PILOT has spawned **no** sub-agents (no fork, no general-purpose). The three forks the coordinator saw are not mine.

## Coordinator additions received 09:10 UTC (to be written into DECLARATION-ADDENDUM.md before launch)
- Learning check at the ep-500 eta update: A1 OFF greedy calibration pooled EE vs a RANDOM_MASKED reference on the same calibration seeds (computed once before training, recorded). If A1 fails to beat it on >= 2 of 3 seeds: stop A1/A2/A3 (A0 keeps running), keep checkpoints/logs, report with loss curves, eta/lambda trajectories, per-head reward means; do not debug or relaunch.
- Report calibration-seed greedy pooled EE of every arm at ep 250/500/750 in this file as they arrive (progress readings, not the result).

## 09:50 UTC — Amendment 1 received (`V025-CONTROLLER-AMENDMENT-1-THREE-CATFISH-PILOT-2026-09-11.md`); also CFSCREEN pairing fact
- Code moved to isolated worktree **`/home/u24/papers/mcrl-leo-handover-cf3`**, branch **`cf3/pilot-20260911`** based on `363845e8`. Shared tree now read-only for me (only `.scratch/cf3-pilot/` is written there). Files (uncommitted yet): `src/mcrl/algorithms/cf_sources.py`, `src/mcrl/algorithms/cf_ratio.py`, `tests/test_cf_ratio.py`.
- To implement before launch: gamma=1 + remaining-steps feature (A1-A3); common vector replay 8/9 main + 1/27 per source (all heads); eta held to ep 500 (updates 500, 750; lambda at 250/500/750); learning-check barrier at 500; per-episode reseeded evaluation + calibration (CFSCREEN pairing fact); pinned-archive source re-measurement (no training); C2 activation logging; dE_sys counterfactual diagnostic; amendment test list; 100-episode diagnostic run.

## Step 3 red/green log (CF_MUTANT=<name> pytest -k <test>; all 13 green with no mutant)
e_not_divided_by_u->reward sums RED; per_head_max_bootstrap->shared continuation RED; eta_frozen_at_init->target recomputed RED;
fraction_one_ninth_each->source fractions RED; min_one_source_sample->rho0==OFF RED; source_uses_main_env_rng->A1/A2 main rollout identical RED;
null_smaller_buffer->NULL3 only policy RED; null_biased_to_first_legal->NULL3 uniform RED; c2_margin_9db->FEASFRONT parity RED;
resume_forgets_catfish_rng->resume bit-identical RED; eta_every_quarter->eta/lambda boundaries RED; b1_incumbent_fallback->B1 restriction RED;
no_time_feature->remaining-steps feature RED.

## Detached: premeasure (step 6) — launched 09:57 UTC on sat
- cmd: `/home/sat/mcrl-v025-cf3-pilot-ws/premeasure.sh` (idempotent; skips arms whose json exists), cwd `ws/tree`, nice 10, MemoryMax 5G, threads 1, MCRL_TLE_ROOT=ws/tle-pinned-427e6a91
- PIDs: MAX_NOMINAL_GAIN 3407519, RANDOM_MASKED 3407520, TRAINED 3407521, C1_A_m2dB 3407522, C2_A_m12dB 3407523, C3_B1_NO_NEW_BEAM 3407524, HARNESS_PLACEBO 3407525
- out: `ws/premeasure/<ARM>.json` + `.log`; then `cf3_premeasure.py --merge --out ws/premeasure` -> `calibration.json`. Expected ~10 min.

## Step 6 DONE ~10:12 UTC — calibration + pre-launch source screen (no training), sat, pinned archive 427e6a91…8fe9
Measured on tree `1d8c3caf` (first attempt on `b270592f` superseded: its pooled sum used Python-3.12 compensated `sum()`, 1 ulp off the harness; moved to `ws/premeasure-superseded-sum-ulp-b270592f`).
`sat:/home/sat/mcrl-v025-cf3-pilot-ws/premeasure/calibration.json` sha256 `59952214a68469d9eccef292fa0eadf41e897ff74abd4b6cbff0635ee1a4562d`.
- **eta_0 = 110,507,234.83444457 bit/J** (MAX_NOMINAL_GAIN, 24 calibration episodes, per-episode reseeded). s_B = 13,329,082,278.45065 bits/user-step; s_E = 120.61728174105066 J/user-step (so eta~_0 = 1).
- **RANDOM_MASKED reference (learning check) = 51,866,475.48532767 bit/J** on the calibration seeds.
- Harness placebo (stream 42/1337/7, B0 convention): 52,420,510.0956937 — **bit-identical** to B0's pinned figure.
- Source screen (24 cal. episodes each): pooled EE / H_inter / H_intra / served / active beams / joules
  - TRAINED e6b063ef: 93,902,816.57 / 0.2260 / 0.0519 / 0.99867 / 66.63 / 3.0011e6
  - C1 A m=2dB: 112,195,917.54 / 0.5514 / 0.0354 / 0.99775 / 62.98 / 2.8926e6
  - C2 A m=12dB: 100,988,477.81 / 0.2280 / 0.0010 / 0.99663 / 71.55 / 3.2685e6
  - C3 B1_NO_NEW_BEAM: 104,190,378.68 / 0.3534 / 0.0758 / 0.99808 / 38.57 / 1.7867e6
  - RANDOM_MASKED: 51,866,475.49 / 0.6896 / 0.1806 / 0.93683 / 76.43 / 3.4673e6
  - MAX_NOMINAL_GAIN: 110,507,234.83 / 0.6546 / 0.0598 / 0.99842 / 62.98 / 2.8948e6
  - **Stop rule: no source violates C-H (all <= 0.6016) or C-S (served within 0.5 pp of TRAINED: C1 -0.09 pp, C2 -0.20 pp, C3 -0.06 pp) -> proceed.**

## Detached (server clock 10:02 UTC; the local clock runs ~10 min ahead — times below are server time)
- **Smoke (step 7)**: `ws/smoke.sh` (tree `c9df1f93`), root `ws/smoke`, PIDs A1s0 3409158, A1s1 3409159, A1s2 3409160, A0s0 3409161, A2s0 3409162, A3s0 3409163; logs `ws/smoke/<ARM>-s<K>.log`, status `ws/smoke/<ARM>-<NAME>-s<K>/status.json`. Expected ~10 min.
- **dE_sys diagnostic (Amendment 1 item 7)**: `tree/scripts/cf3_de_diag.py --out ../diag/dE_sys.json --episodes 3`, log `ws/diag/dE_sys.log`. Expected < 30 min. Non-blocking.

## 10:05 UTC (server) — 100-episode diagnostic stage launched (Amendment 1), production root `ws/runs`
- `ws/launch.sh --stop-after 100 A1:0 A2:0 A3:0` (tree `c9df1f93`); PIDs A1s0 3409938, A2s0 3409940, A3s0 3409942; logs `ws/runs/<ARM>-s0.log`; out `ws/runs/<ARM>-<NAME>-s0/` (resume.pt, policy-ep00100.pt, status.json `stopped-at`). Expected ~10 min.
- Then: `tree/scripts/cf3_diag100.py --out ../diag/diag100.json ../runs/A1-OFF-s0 ../runs/A2-CF3-s0 ../runs/A3-NULL3-s0`; then full launch `ws/launch.sh` (all 12; the three s0 runs resume from ep 100).
- Resume after any interruption: re-run `ws/launch.sh` (idempotent: skips finished/live runs, resumes from resume.pt).

## dE_sys diagnostic DONE (Amendment 1 item 7; no training) — `sat:ws/diag/dE_sys.json`
C3 (B1_NO_NEW_BEAM) on 3 calibration episodes (3,000 user-steps); 847 user-steps where C3's choice differs from a legal incumbent. dE_sys = E(C3 choice) − E(incumbent), other users fixed, counterfactual `evaluate_actions` (CRN):
- quantiles (J/step): 1% −225.2, 5% −196.5, 10% −188.3, 25% −174.2, **50% −1.21**, 75% 0.0, 90% +4.5, 95% +175.3, 99% +188.5; mean −51.3 J.
- 35.8% exactly zero; **59.5% within ±1% of the step's joules**; 51.6% negative. Step joules mean 7,586.7 J (equal share 75.9 J/user).
- Reading (pre-declared rule): **most local contrasts are near zero**, so a negative C3 result would be uninterpretable as "C3 fails". The non-zero mass is bimodal at about ±1 beam (±188 J ≈ 6.267 W × 30.08 s).
- Smoke evaluation DONE (smoke policies only, not results): `ws/smoke/eval/A0s0.json`, `A2s0.json` — 24 eval episodes, per-episode reseeded, `--repeat`: **determinism placebo bit-identical for both**; **A0 and A2 share every episode's start epoch and t=0 observation hash (24/24)** -> pairing holds beyond episode 0. Eval wall ~83 s per checkpoint incl. repeat and pin check.

## 100-episode diagnostic DONE (Amendment 1; a check, not a result) — `sat:ws/diag/diag100.json`
Runs = A1/A2/A3 s0 stopped at ep 100 on tree c9df1f93 (pre-Amendment-2 fingerprint; lambda was 0 throughout), now in `ws/runs-diag100-preA2/`.
- Q scale (mean over legal actions on 2,000 main-replay states; heads' units): A1 Q_B 1.69 / Q_E 2.21 / Q_H 1.40; A2 1.85 / 2.14 / 1.43; A3 1.71 / 2.18 / 1.37. No blow-up.
- Term share at the greedy action: B ~0.49-0.52, E ~0.48-0.51, H 0.00 (lambda = 0; eta~ = 1). C2 argmax change without Q_H: 0.0 (lambda = 0).
- Batch composition over 999 updates: A2 and A3 both main 112,887 / 4,995 / 4,995 / 4,995 (= 113:5:5:5 exactly); A1 127,872 main.
- Source buffers (50,000 each): C1 buffer EE 111.5M, C2 100.1M, C3 104.4M (C3 raw E/user-step 73.9 J vs ~121-136); NULL1-3 ~52.0-52.6M (random). Losses finite (B 0.36-0.37, E 0.06-0.08, H 0.15-0.20).
- RSS: A2/A3 reached 3.9 GB at ep 100 (4.4 GB peak during save), still rising -> fixed by sharing one TleArchive per process (addendum F; tested bit-identical). Timing (unshared archive): A1 1.74 s/ep, A2/A3 6.57 s/ep.
- Smoke2 (tree aa77be8a, A1s3/A3s4/A0s1): complete; lambda exactly 0 in every trajectory row; ep-1 progress reading == ep-1 quarter reading (read-only measurement is deterministic).
- Addendum updated with Amendment 2 + seeds 3-4 + readings/AUC + H_intra + lambda* + shared archive, BEFORE launch.

## LAUNCH — 10:25:45 UTC (server clock), tree `e8a04ccf` (worktree branch cf3/pilot-20260911; tarball sha256 ce3e3128…03c1)
STATUS (SUPERSEDED — this launch was stopped at 10:40 UTC, see HOLD): training launched: 18 runs (A0 s0-2, A1/A2/A3 s0-4) x 1000 episodes; projected finish A0/A1 ~11:10-11:20 UTC, A2/A3 ~12:30 UTC (allow 13:15 under contention); ep-500 learning check expected ~10:45 (A1) — A2/A3 reach it ~11:25.**
- cmd: `/home/sat/mcrl-v025-cf3-pilot-ws/launch.sh` (idempotent; re-run it to resume after any interruption — skips complete/stopped/live runs, resumes from resume.pt)
- cwd `ws/tree`; python `/home/sat/mcrl-leo-handover/.venv/bin/python`; nice 10; threads 1; systemd-run scope MemoryMax=5G; MCRL_TLE_ROOT=ws/tle-pinned-427e6a91; calibration `ws/premeasure/calibration.json` (sha256 59952214…562d)
- out: `ws/runs/<ARM>-<NAME>-s<K>/` (status.json, readings.jsonl, episode-logs.json, resume.pt, policy-epNNNNN.pt every 100); logs `ws/runs/<ARM>-s<K>.log`; pid files `ws/runs/<ARM>-s<K>.pid`; learning check `ws/runs/learning-check/`
- PIDs: A0 s0 3416294, s1 3416296, s2 3416298 | A1 s0 3416300, s1 3416302, s2 3416304, s3 3416306, s4 3416308 | A2 s0 3416310, s1 3416312, s2 3416314, s3 3416316, s4 3416318 | A3 s0 3416320, s1 3416322, s2 3416324, s3 3416326, s4 3416328
- Load at launch 1.46, 88 GB available.

## Calibration-seed progress readings (greedy pooled EE; progress only, not the result)
(filled as `readings.jsonl` rows arrive; RANDOM reference 51,866,475.49; eta_0 110,507,234.83)

## HOLD — 10:40 UTC (server): the 10:25 launch is stopped; nothing of mine runs on sat
- Coordinator (external review) listed launch-control defects: (1) learning-check failure path off-by-one (499 logs vs next_episode 500) — **real**, I had noted it; (2) DECISION.json multi-writer race — **real**; (3) resume fingerprint lacks code identity — **real**; (4) no process-level resume test — true; (5) saturated-buffer calibration memory under 5G — to measure; (6) launch.sh hardening; (7) freeze + resync + fresh launch of all 18.
- All 18 processes TERM'd by exact verified PIDs (cmdline contains `scripts/run_cf3_pilot.py`, cwd = ws/tree); 0 remain. Moved to `ws/runs-aborted-e8a04ccf-hold/` — **not results; will not be resumed.** State at stop: A1 s1/s2/s3 had passed ep 100 (ep-100 progress readings 100.6M / 90.9M / 100.8M, recorded only for transparency); all others < 100.
- Measured under 18-way contention (A1, incl. its ep-100 reading): 4.9-6.7 s/episode vs 1.74 alone -> ~3x slowdown (CPU = Core Ultra 7 265KF: 8 P-cores + 12 E-cores, no SMT). A2/A3 projection must use ~3x their 6.6 s/ep.

## 10:50:57 UTC — Amendment 3 (pre-generated source pools): generation running on sat
- Code: worktree commit `99252ef8` (pools replace streaming source envs; tests being updated). Staged separately as `ws/tree-pools-99252ef8` (so restaging `ws/tree` cannot disturb it).
- cmd `ws/gen_pools.sh`: 18 processes = seeds 0-2 x {cf3, null3} x sources 0-2, 100 episodes each, pool seeds env 9_141_000+1000k+i / mobility 9_142_000+1000k+i, NULL actions default_rng((9_151_000,k,j,i)); nice 10, MemoryMax 5G.
- PIDs 3426334-3426351 (s0 cf3 0..2 = 3426334-6, s0 null3 = 3426337-9, s1 cf3 = 3426340-2, s1 null3 = 3426343-5, s2 cf3 = 3426346-8, s2 null3 = 3426349-51).
- out: `ws/pools/s{k}/{name}.npz` + `.json` (meta: seeds, transitions, pool sha256, t0 obs hashes, pool EE); logs `ws/pools/logs/`. Expected ~5-10 min.

## 11:00 UTC — must-fix items + Amendment 3 implemented (worktree branch cf3/pilot-20260911)
- Commits since the held launch (e8a04ccf): e28100b1 (gate failure path, single-writer DECISION, code manifest, python launcher), 5938450b (gate timeout = loud failure; StopAfter; 12-run default; report records its commit), 99252ef8 (Amendment 3 pools), d04d9dbe (pool mobility seed base 9_161_000 — first base collided with env seeds; first pool generation killed before any pool finished), f297334e (process-level tests; manifest covers Amendment 3 + pool generator).
- Tests: `tests/test_cf_ratio.py` 17/17 green locally; 16 named mutants each turn their test red (log `scratchpad/mutants2.log`): e_not_divided_by_u, per_head_max_bootstrap, eta_frozen_at_init, fraction_one_ninth_each, min_one_source_sample, source_uses_main_env_rng (pool load touching main RNG), null_biased_to_first_legal, c2_margin_9db, resume_forgets_catfish_rng, eta_every_quarter, gate_stop_before_log, b1_incumbent_fallback, no_time_feature, dual_ascent_on_by_default, shared_env_test_split, pool_seeds_overlap_calibration. (NULL3-vs-CF3 pool parity test has no natural single-defect mutant; it is a direct equality check.)
- Addendum sections H-K written (12 runs; pools; launch control; memory: A2/A3 MemoryMax 7G / RSS cap 6.5 GB, separate memtest not run).
- Pool generation (tree `tree-pools-d04d9dbe`, launched 10:55:45 UTC, PIDs 3427958-3427975) in progress; process-level tests (`scripts/cf3_proctest.py`) run as soon as pools exist.

REVIEW READY: f297334e

## 11:09 UTC — pools DONE: 18/18 in `sat:ws/pools/s{0,1,2}/` (1.7 GB), 100,000 transitions each (no P-03 drops)
Pool EE (bit/J) / H_inter rate per seed s0, s1, s2:
- C1_A_m2dB: 111.27M / 110.89M / 111.58M; H_inter 0.556-0.559
- C2_A_m12dB: 100.89M / 100.74M / 100.84M; H_inter 0.226-0.228
- C3_B1_NO_NEW_BEAM: 104.09M / 103.75M / 104.33M; H_inter 0.352-0.359
- NULL1/2/3: 52.0M-52.6M; H_inter 0.682-0.686
Metadata (seeds, sha256, t0 hashes) in each `.json`; generated by tree `d04d9dbe` (generator code identical in f297334e).
- 11:10 UTC: process-level tests launched: `ws/tree/scripts/cf3_proctest.py --base ../proctest-f297334e ...`, PID 3431825, log `ws/proctest-f297334e.log`, result `ws/proctest-f297334e/PROCTEST-RESULT.json`.

## 11:14 UTC — process-level tests PASS (`sat:ws/proctest-f297334e/PROCTEST-RESULT.json`, real launcher + driver + real pools)
- T1: A3 s0 stopped at ep 2 and resumed through the launcher -> final policy **bit-identical** to the uninterrupted run; logs [0,1,2], next_episode 3; source-sampling RNG state and pool states identical; policy loadable by cf3_eval; a second launch while live planned it as `live pid`, started nothing.
- T2: forced learning-check failure (RANDOM ref 1e12) -> A1 s0-2 `stopped-learning-check`, completed 2 = next_episode 2, logs [0,1]; one DECISION.lock, DECISION pass=false (written by A1s2); launcher then plans all three `finished`.
- Coordinator GO received (agy review of e8a04ccf..f297334e: 0 INVALIDATES, 0 BIASES). Final commit **f297334e** (no later commit).

## LAUNCH-2 — 11:14:42 UTC (server clock): 12 fresh runs, 1000 episodes each
STATUS: **training launched 11:14:42 UTC — 12 runs (A0/A1/A2/A3 x seeds 0-2), tree f297334e, manifest code digest 73668b206451; projected finish ~12:45 UTC (allow 13:15) — per-episode ~2 s alone, ~3-4 s under 12-way contention on 8P+12E cores, plus 5 calibration readings/run; ep-500 learning check expected ~11:45-12:00 UTC.**
- cmd (cwd `ws/tree`): `MCRL_TLE_ROOT=ws/tle-pinned-427e6a91 python scripts/cf3_launch.py --root ../runs --calibration ../premeasure/calibration.json --pools ../pools --init-manifest --expect 12 --memory-max 5G --memory-max-cf 7G`
- **Resume after any interruption**: same command without `--init-manifest` (the manifest must match; finished and live runs are skipped; others resume from resume.pt). Do NOT resume across a code change.
- RUN-MANIFEST: `ws/runs/RUN-MANIFEST.json` (commit f297334e, code digest 73668b206451…, calibration sha 59952214…, 18 pool hashes).
- PIDs: A0 s0 3432490, s1 3432491, s2 3432492 | A1 s0 3432493, s1 3432494, s2 3432495 | A2 s0 3432496, s1 3432497, s2 3432498 | A3 s0 3432499, s1 3432500, s2 3432501. All alive at +10 s.
- out: `ws/runs/<ARM>-<NAME>-s<K>/` (status.json, readings.jsonl, episode-logs.json, resume.pt, policy-epNNNNN.pt every 100; final = policy-ep01000.pt); logs `ws/runs/<ARM>-s<K>.log`; gate `ws/runs/learning-check/`.
- After completion: `ws/eval.sh` (per-episode reseeded eval of each final checkpoint, --repeat) then `cf3_report.py`.
- 11:16 UTC: verified all 12 status.json fingerprints carry the RUN-MANIFEST code digest (73668b206451…); all running.

## 11:25 UTC — pool sidecar provenance (coordinator request; no regeneration, no restart)
- `sat:ws/pools/POOL-SIDECAR-HASHES.json` (sha256 8ebbae8501e8e4ba5eebb3f5e7cab5f72f802567493a4627bb0723c0aa537c7c): sidecar + npz sha256 of all 18 pools; every npz hash equals RUN-MANIFEST.json's entry.
- Sidecar sha256 (s{k}/{name}.json): s0 C1 0ccc3452…205c, C2 948fc074…00b1, C3 c598c079…9424, NULL1 e1acf9b0…c6c8, NULL2 4fe5ab14…32a2, NULL3 3efd4762…8a07; s1 C1 696a395d…f6f0, C2 43ec4103…b081, C3 1e01038b…0512, NULL1 0ee8b887…edf5, NULL2 05a99755…6ee6, NULL3 6b54b18a…1ddf; s2 C1 81304445…b1d, C2 8769cf7c…8acc, C3 1d53770f…6a, NULL1 ba081b07…1f2c, NULL2 45f8e594…6107, NULL3 ac58cfc9…c37e (full hashes in the JSON).
- Generator identity: pools made by tree `d04d9dbe`, training runs `f297334e`. **Byte-identical** between the two trees: `cf_ratio.py` (10411e21…), `cf_sources.py` (c4906a7d…), `cf3_pools.py` (dd2fd92a…), `state_encoding.py` (fdb4675b…), and every other `src/**/*.py` (0 files differ). `cf3_common.py` differs only by two added MANIFEST_FILES entries (Amendment 3 doc, cf3_pools.py) — no generation code.
- Re-verification at evaluation time: `scripts/cf3_verify_pools.py` (worktree ff884b0e; copy `ws/diag/`) — hashes of every sidecar/npz vs the record and RUN-MANIFEST, and each A2/A3 run's loaded pool vs sidecar kind/head/source_index/seed_index/transitions=100000; exit 1 on any mismatch. `ws/eval.sh` runs it first and aborts on failure; `cf3_report.py` (ff884b0e, copy `ws/diag/`) refuses to run without an ok verification. Dry run now: **ok, 18 pools, 18 run bindings** (`ws/diag/POOL-VERIFY-at-launch.json`).

### Episode 100 (read-only; launch-2; server 11:24 UTC) — greedy calibration pooled EE (M bit/J) | H_inter | H_intra | served | active beams
| run | EE | H_inter | H_intra | served | beams |
|---|---:|---:|---:|---:|---:|
| A0 s0 / s1 / s2 | 75.72 / 75.47 / 78.39 | 0.158 / 0.159 / 0.162 | 0.006 / 0.040 / 0.036 | 0.9964 / 0.9988 / 0.9974 | 62.6 / 64.6 / 62.9 |
| A1 s0 / s1 / s2 | 98.00 / 100.60 / 90.90 | 0.479 / 0.500 / 0.387 | 0.073 / 0.071 / 0.041 | 0.9945 / 0.9984 / 0.9948 | 56.5 / 61.2 / 58.0 |
| A2 s0 / s1 / s2 | 93.57 / 93.75 / 99.19 | 0.591 / 0.391 / 0.549 | 0.024 / 0.046 / 0.043 | 0.9994 / 0.9932 / 0.9947 | 57.1 / 51.0 / 57.2 |
| A3 s0 / s1 / s2 | 93.78 / 97.00 / 85.27 | 0.560 / 0.447 / 0.374 | 0.030 / 0.118 / 0.051 | 0.9995 / 0.9979 / 0.9934 | 57.3 / 58.4 / 52.2 |
Arm means: A0 76.53, A1 96.50, A2 95.50, A3 92.02. Progress reading only (ε at ep 100 = 0.55); not the result. A1 s1 100.60 equals the aborted launch's A1 s1 ep-100 reading (same code path, deterministic).
Timing: ~3.3 s/episode per run under 12-way contention; RSS A0/A1 ~1.9 GB, A2/A3 ~2.2 GB. **Projected finish ~12:20-12:30 UTC.**

### Episode 250 (quarter; lambda fixed 0, eta held at eta_0 until 500) — greedy calibration pooled EE (M bit/J) | H_inter | H_intra | served | beams
| run | EE | H_inter | H_intra | served | beams |
|---|---:|---:|---:|---:|---:|
| A0 s0 / s1 / s2 | 93.79 / 93.84 / 97.77 | 0.191 / 0.188 / 0.195 | 0.001 / 0.001 / 0.007 | 0.9973 / 0.9982 / 0.9990 | 73.3 / 67.3 / 69.6 |
| A1 s0 / s1 / s2 | 103.41 / 99.75 / 101.43 | 0.582 / 0.521 / 0.486 | 0.057 / 0.105 / 0.085 | 0.9970 / 0.9982 / 0.9995 | 63.7 / 64.3 / 62.2 |
| A2 s0 / s1 / s2 | 92.79 / 97.66 / 101.08 | 0.490 / 0.519 / 0.648 | 0.110 / 0.073 / 0.044 | 0.9945 / 0.9985 / 0.9988 | 58.4 / 58.4 / 64.6 |
| A3 s0 / s1 / s2 | 99.91 / 101.96 / 102.91 | 0.608 / 0.582 / 0.532 | 0.060 / 0.066 / 0.048 | 0.9966 / 0.9968 / 0.9992 | 58.8 / 61.4 / 59.8 |
Arm means: A0 95.13, A1 101.53, A2 97.18, A3 101.59. Progress reading only; not the result.

## 11:37 UTC — agent-independent post-training job (coordinator request)
- `sat:ws/diag/cf3_postjob.py` (worktree commit 102b2d4d; sha256 d2e47f7c…00fd), **PID 3438182**, started 11:37:15 UTC via `setsid nohup ... diag/cf3_postjob.py --ws /home/sat/mcrl-v025-cf3-pilot-ws > diag/postjob.stdout`.
- Waits for all 12 runs terminal (complete / failed / stopped-learning-check with a failing DECISION / DEAD = status running but PID gone), up to 8 h; then evaluates every complete final checkpoint (tree `cf3_eval.py`, --repeat), re-verifies pools (`diag/cf3_verify_pools.py`) and generator identity (tree-pools-d04d9dbe vs tree), runs `diag/cf3_report.py` + `diag/cf3_render.py` (commit 102b2d4d), writes `ws/report/` + marker `REPORT-DONE` or `REPORT-FAILED`. Learning-check stop -> `LEARNING-CHECK-STOP.json` + REPORT-DONE(kind=learning-check-stop). Log `ws/report/postjob.log`.
- State detection checked live at 11:37: 12 x running (alive).
- Takeover guide: `.scratch/cf3-pilot/TAKEOVER.md`.
