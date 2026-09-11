# T0-REPR — representability screen of teacher T0 = LP-prev(c=1, m=0) — PROGRESS

Agent start: 2026-09-12 01:32:37 CST (= 2026-09-11 17:32:37 UTC). Measurement only: no learner training;
the two clones are measurement probes (as CFSCREEN), never the learner.
Inputs read: Amendment 3 §2–§3, Amendment 5 Part I §I.4, LP-PROBE-2026-09-11.md, CATFISH-SCREENS §1b–1c,
lp_common.py / lp_grid.py, bc_probe.py / bc_rollout.py, pilot worktree cf_ratio.py / cf_sources.py / cf3_common.py.
Not read (instructed): `.scratch/validity-audit/`, `.scratch/reviews/`.

Server `sat`, workspace `/home/sat/mcrl-v025-t0-repr-ws/` (mine only). Other agents' workspaces
(`mcrl-v025-h4-probe-ws`, `mcrl-v025-ceiling-ws`) are never touched.

## Steps
- [ ] 0. Stage workspace (tree tar sha256 both ends, PREREG, scripts, placebo targets)
- [ ] 1. Placebo: T0 on 24 evaluation + 24 calibration episodes bit-for-bit vs LP JSONs
- [ ] 2. Collect ≥ 100 training-like episodes (obs 113, mask, T0 action, T0 28-score vector)
- [ ] 3. Two clones (one-hot BC; soft distillation, τ chosen on VAL split and written here BEFORE closed loop)
- [ ] 4. Closed loop on evaluation + calibration; R_repr; held-out top-1/top-3; conditional entropy
- [ ] 5. Report `T0-REPRESENTABILITY-2026-09-12.md`; scripts + JSON copied back with sha256

## Log

### 2026-09-12 01:55 CST — Step 0 staging DONE
- ws `/home/sat/mcrl-v025-t0-repr-ws/` = {tree, scripts, results, data, models, logs, targets}.
- `tree/` = `git -C /home/u24/papers/mcrl-leo-handover-cf3 archive 102b2d4d src scripts tests artifacts/PREREG-FROZEN-2026-08-25-R2.json`
  (PREREG added: `assert_tle_archive_pinned()` and `pilot_config()` read it; the LP probe staged it too). Tarball
  `tree-102b2d4d-t0repr.tar` sha256 `12c341e5d19031d4377455121914a8857a6c9ce6619975700f2c82ffe3045cba`, 5,969,920 B,
  437 .py — **identical on both ends**; `tree/COMMIT` = 102b2d4d. PREREG sha256 `8bf13e28…4543` (= git blob at 102b2d4d).
- Staged verbatim (sha256 identical both ends): `scripts/lp_common.py` fc8d4f0b…4a27, `lp_grid.py` b3a011f5…ecc5,
  `bc_probe.py` cb80c4d7…310f, `bc_rollout.py` 838c84bf…4be (reference only; my scripts re-implement the probe method
  for the 113-dim ratio observation).
- Placebo targets copied (read-only, sha256 identical both ends) into `targets/`: `LP-prev-evaluation-c1-m0.json`
  9c8630ed…3e99, `LP-prev-calibration-c1-m0.json` 98e68e88…faf0, `REF-C1_A_m2dB-evaluation.json` 3a2e4030…d973,
  `REF-C1_A_m2dB-calibration.json` 5497c117…5d0c (= LP report's files, `results-lp/SHA256SUMS`).
- Import check on sat: `mcrl.__file__` = ws/tree/src; TLE file_set = 427e6a91…8fe9; pilot config hidden (100,50,50)
  tanh, log1p / raw_radians / divide_by_num_users; `systemd-run --user --scope -p MemoryMax=5G` works.
- My scripts (local `.scratch/t0-repr/scripts/`, shipped by `cat | ssh sat 'cat > …'`, sha256 identical both ends):
  t0_common.py 3b8e29f9…c4e / full 3b8e29f984558fd6d0f485e1d2c24b31933ed81f71c58f1c18a2dd9371bc7d7f, t0_placebo.py e5f26602…4e72,
  t0_collect.py 6f2067ad…266e, t0_clone.py 04e8e4bd…4c4e, t0_select_tau.py 1735e275…c192, t0_closed.py 020ec384…d77f
  (full hashes recorded in each result JSON's `code` block).

### DECLARATIONS (written before any rollout, fit or closed-loop run)
- **Placebo gate (step 1)**: my T0 rollout (t0_common.rollout + t0_scores) on each set must equal the LP JSON on all 15
  fields (ee, bits, joules, served, h_inter, h_intra, beams, ee_ep[24], rate mean/p10/min, served_user_steps,
  user_steps, n_episodes, ho_per_user_min) with `==`; per decision my T0 action == `lp_common.lp_prev_rule_factory(1,0)`;
  `A m=2dB` re-rolled through the same loop == REF JSON (the R_repr reference); instrument check: loads decode exactly,
  remaining-steps feature exact, T0 recomputed from the observation alone (decoder) == T0 on every decision, and the
  decoder POLICY rolled through the clone path == T0 bit-for-bit. Any failure → stop.
- **Seed rule (step 2)**: training triples j=0,1,2 = (42,1337,7), (43,1338,8), (44,1339,9); **100 episodes per triple
  (300 total)**; the pilot trainer's schedule (one carried pair `default_rng(env)`, `default_rng(mobility)`; reset per
  episode, step with env_rng), T0 as behaviour; fresh env per episode with the env's `_age_rng` carried by the env's
  resume seam; `train` seed unused by T0. Check: first 3 episodes of triple 0 bit-identical single-env vs fresh-env.
  Disjointness: seed values disjoint from eval (9,111,000+i / 9,112,000+i), cal (9,121,000+i / 9,122,000+i), pools
  (9,141,000+1000k+i / 9,161,000+1000k+i); additionally no collected episode may share (start epoch, t=0 obs hash)
  with an evaluation or calibration episode (checked in aggregation).
- **Split by episode**: episode k of each triple → TEST if k%5==4 (60 ep), VAL if k%5==3 (60 ep), TRAIN otherwise (180 ep).
  Empty-mask decisions excluded, counted.
- **Clones** (measurement probes): DQNNetwork(113→100→50→50→28, tanh), pilot config; raw input; illegal logits −1e9;
  Adam 1e-3, batch 256, 100 epochs, torch seed 1000 (init + shuffle), same for both clones.
  BC: CE on T0 action. SOFT: CE toward softmax(T0 score/τ) over legal actions, **τ grid {0.01, 0.03, 0.1, 0.3, 1, 3}**.
  Epoch selection on VAL: min mean T0-score regret (score_T0[a_T0] − score_T0[a_clone]); tie → max VAL top-1 → earliest.
  **τ selection on VAL**: min VAL mean T0-score regret at each τ's selected epoch; tie → max VAL top-1 → smaller τ.
  TEST only reported (top-1, top-3, regret, CE), never used to select. τ is written here before any closed-loop run.
- **Closed loop**: each clone greedy (masked argmax, first index on ties) on 24 eval + 24 cal episodes (fresh env,
  per-episode reseed); R_repr = (EE(clone) − EE(A m=2dB)) / (EE(T0) − EE(A m=2dB)) per set, pooled EE, with EE(T0) and
  EE(A m=2dB) from my placebo-verified rollouts. Admission (Amendment 3 §3): R_repr ≥ 0.5 for at least one clone on
  both sets. Supplementary only: paired per-episode stats and a 10,000-resample episode-cluster bootstrap of R_repr.
- **Conditional entropy H(a_T0 | o)**: (i) exact decoder agreement over all collected decisions (100 % ⇒ T0 is a
  deterministic function of (o, mask) on the sample ⇒ H = 0); (ii) plug-in H on the finest binning (identical float32
  observation + mask) and a coarse binning (every observation dim rounded to 0.05 encoded units), with the fraction
  of decisions in shared bins; (iii) BC clone TEST cross-entropy in bits (variational upper bound on H(a|o)).
- **Resources**: ≤ 3 processes, `nice -n 16`, OMP/MKL/OPENBLAS = 1 + torch 1 thread, `systemd-run --user --scope -p
  MemoryMax=5G`, `setsid nohup … </dev/null > log 2>&1 &`, cwd = ws, python `/home/sat/mcrl-leo-handover/.venv/bin/python`,
  `MCRL_TLE_ROOT=/home/sat/mcrl-v025-cf3-pilot-ws/tle-pinned-427e6a91`.

### 2026-09-11 17:46:17 UTC — Step 1 placebo LAUNCHED (detached)
Launcher `ws/run.sh` (cwd ws; MCRL_TLE_ROOT pinned; OMP/MKL/OPENBLAS/NUMEXPR=1; `nice -n 16 systemd-run --user --scope
-q -p MemoryMax=5G /home/sat/mcrl-leo-handover/.venv/bin/python ws/scripts/<script>`), started with `setsid nohup … &`.
- PID 3537495: cwd `/home/sat/mcrl-v025-t0-repr-ws`, cmdline `…/.venv/bin/python …/scripts/t0_placebo.py --set evaluation`,
  log `logs/placebo-evaluation.log`, output `results/PLACEBO-evaluation.json`, expected finish ≈ 17:50 UTC (3 × 24-episode rollouts).
- PID 3537496: same, `--set calibration`, log `logs/placebo-calibration.log`, output `results/PLACEBO-calibration.json`, ≈ 17:50 UTC.

### 2026-09-11 17:48 UTC — Step 1 placebo v1 FINISHED: T0 gate passed on both sets; one derived-field mismatch in my extra REF check
- **T0 vs LP JSON, evaluation: all 15 fields bit-identical** — ee 114,129,570.58605178 (= target); **calibration: all 15
  bit-identical** — ee 117,528,214.54845703 (= target). Per decision (24,000 per set): my T0 action == lp_common
  LP-prev(1,0) on 24,000/24,000; decoder-from-observation == T0 on 24,000/24,000; loads decode exactly; remaining-steps
  feature exact; SINR decode max rel err 2.43e-7 (float32 log1p); 0 empty masks. Decoder POLICY rolled through the
  clone path == T0 bit-for-bit (15 fields + every episode's bits/joules/epoch/t=0 hash) on both sets.
- `A m=2dB` re-roll: calibration all 15 identical (ee 112,195,917.53568056). Evaluation: 14/15 identical (ee
  107,000,983.53410847, bits, joules, served, beams, h_inter, h_intra, ee_ep, rates all ==), **`ho_per_user_min` differs
  in the last ulp** (mine 1.2184175531914891 vs target ...894). Cause verified: it is a derived display field; lp_grid
  computes it with the literal `DT_S = 30.08`, my v1 used `cf_ratio.DT_S = DECISION_STEP_S = 30.080000000000002`
  (substeps × measurement step). Recomputing the target's h_inter/h_intra with 30.08 gives ...894 exactly. Bits/joules
  use `cfr.DT_S` in both codes (identical).
- Fix (no measured quantity touched): t0_common.rollout now derives ho_per_user_min with lp_grid's literal 30.08
  (t0_common.py sha256 35c42ae6…8176). v1 outputs kept as evidence: `results/PLACEBO-evaluation.v1-hoderiv.json`,
  `results/PLACEBO-calibration.v1.json`, `logs/placebo-*.v1.log`.

### 2026-09-11 17:49:16 UTC — Step 1 placebo v2 LAUNCHED (detached; same checks, fixed derivation)
- PID 3539246: cwd ws, `…/.venv/bin/python …/scripts/t0_placebo.py --set evaluation`, log `logs/placebo-evaluation.log`,
  output `results/PLACEBO-evaluation.json`, expected ≈ 17:52 UTC.
- PID 3539247: same `--set calibration`, log `logs/placebo-calibration.log`, output `results/PLACEBO-calibration.json`, ≈ 17:52 UTC.

### 2026-09-11 17:49:39 UTC — Step 2 collection triple 0 LAUNCHED (T0 code identical to the v1-verified T0 path)
- PID 3540041: cwd ws, `…/.venv/bin/python …/scripts/t0_collect.py --triple 0 --episodes 100 --seed-rule-check 3`,
  log `logs/collect-triple0.log`, output `data/T0-collect-triple0.{npz,json}`, expected ≈ 17:58 UTC
  (9 seed-rule-check episodes + 100 collected). Triples 1, 2 launch when the v2 placebo processes exit (≤ 3 processes).
- 17:51 UTC: seed-rule check (triple 0, first 3 episodes) **PASSED**: single carried env ≡ fresh env + carried `_age_rng`
  state on epoch, t=0 obs hash, actions hash, bits, joules, served, h_inter, h_intra for all 3 episodes. Negative control
  (fresh env WITHOUT the carried age state) differs on episodes [0: no, 1: yes, 2: yes] — the carry is load-bearing and
  the fresh-env collection reproduces the trainer's single-env schedule. Collector RSS ~0.74 GB after start-up.

### 2026-09-11 17:52 UTC — [x] Step 1 placebo v2 PASSED on both sets (the gate for everything below)
- `results/PLACEBO-evaluation.json` (sha256 351c97a3…8bc6, `ok: true`): T0 = 114,129,570.58605178 bit/J, all 15 fields
  == LP JSON; `A m=2dB` = 107,000,983.53410847, all 15 == REF JSON; decoder policy == T0 (15 fields + every episode);
  24,000/24,000 decisions: T0 == lp_common rule, decoder == T0; loads exact; SINR decode max rel err 2.43e-7; 0 empty masks.
- `results/PLACEBO-calibration.json` (sha256 6bef5a6c…dfa0, `ok: true`): T0 = 117,528,214.54845703, all 15 == LP JSON;
  `A m=2dB` = 112,195,917.53568056, all 15 == REF JSON; decoder policy == T0; same decision checks, 0 mismatches.

### 2026-09-11 17:52:18 UTC — Step 2 collection triples 1, 2 LAUNCHED (3 processes now)
- PID 3541996: cwd ws, `…/.venv/bin/python …/scripts/t0_collect.py --triple 1 --episodes 100`, log `logs/collect-triple1.log`,
  output `data/T0-collect-triple1.{npz,json}`, expected ≈ 17:57 UTC.
- PID 3541997: same `--triple 2`, log `logs/collect-triple2.log`, output `data/T0-collect-triple2.{npz,json}`, ≈ 17:57 UTC.
- PID 3540041 (triple 0) running, RSS ~1.3 GB at ep ~45 (grows ~14 MB/episode: the shared TleArchive parse cache;
  MemoryMax 5G cap in force).

### 2026-09-11 17:55:43 UTC — [x] Step 2 collection DONE
- 3 triples × 100 episodes = **300 episodes, 300,000 decisions, 0 empty masks**; T0 action legal on every row; mean legal
  set 26.3; price-active (T0 ≠ MAX_NOMINAL_GAIN) 19.8 % / 20.2 % / 20.1 % per triple.
- `data/T0-collect-triple0.npz` sha256 23cd918a…fcee5 (wall 192 s), `triple1.npz` 515bc53e…f991 (169 s),
  `triple2.npz` f419be02…4cc1 (167 s); metadata JSONs beside them (per-episode epoch, t=0 hash, bits, joules).
- T0 pooled EE on these training-like episodes (descriptive only, a different episode set from eval/cal; never
  compared with them): 117,812,417.08 / 116,655,602.82 / 117,084,038.97 bit/J per triple.

### 2026-09-11 17:55:59 UTC — Step 3 clones LAUNCHED (3 processes)
- PID 3544259: cwd ws, `…/.venv/bin/python …/scripts/t0_clone.py --kind bc`, log `logs/clone-bc.log`, output
  `models/BC.pt`, `results/CLONE-BC.json`, expected ≈ 18:00–18:05 UTC.
- PID 3544260: `t0_clone.py --kind soft --taus 0.01,0.03,0.1`, log `logs/clone-soft-a.log`, outputs `models/SOFT-tau{0.01,0.03,0.1}.pt`
  + `results/CLONE-SOFT-tau*.json`, ≈ 18:10 UTC.
- PID 3544261: `t0_clone.py --kind soft --taus 0.3,1,3`, log `logs/clone-soft-b.log`, outputs `models/SOFT-tau{0.3,1,3}.pt`
  + JSONs, ≈ 18:10 UTC.
- Then `t0_select_tau.py` (VAL only) → τ written here BEFORE any closed-loop run.
- 17:58 UTC first fits done (VAL/TEST open-loop only): BC best epoch 96/100; SOFT τ=0.01 96/100; SOFT τ=0.3 98/100.
  **SENSITIVITY DECLARED NOW (after reading these best-epoch positions, BEFORE any closed-loop run)**: because the
  VAL-selected epoch sits at the end of the declared 100-epoch budget (the probe may be under-trained, which would
  bias R_repr low), BC and the soft clone at the VAL-selected τ (τ fixed from the declared selection, not re-selected)
  are refit with **400 epochs**, everything else identical (same data, split, seed, VAL epoch rule); both are rolled
  out closed-loop on both sets and reported BESIDE the declared 100-epoch clones. **The admission verdict is read on
  the declared (100-epoch) clones**; if the 400-epoch sensitivity would change it, the report says so explicitly.
  Code: `t0_clone.py --epochs 400` (name suffix `-e400`; new file e0a18106…d432 shipped only after the running fits
  exit so that their `code` blocks record the version they ran, 04e8e4bd…4c4e).

### 2026-09-11 17:59:20 UTC — [x] Step 3 clones DONE; **τ SELECTED ON VAL = 3** (written before any closed-loop run)
`results/TAU-SELECTION.json` sha256 876930f5…0a32 (`t0_select_tau.py`, VAL split only; TEST and closed loop not read):

| τ | selected epoch | VAL mean T0-score regret | VAL top-1 | VAL top-3 |
|---|---:|---:|---:|---:|
| 0.01 | 96 | 0.017706 | 0.8970 | 0.9933 |
| 0.03 | 93 | 0.015245 | 0.9046 | 0.9952 |
| 0.1 | 93 | 0.010250 | 0.9188 | 0.9969 |
| 0.3 | 98 | 0.006252 | 0.9375 | 0.9985 |
| 1 | 96 | 0.006671 | 0.9293 | 0.9984 |
| **3** | 93 | **0.004101** | 0.9458 | 0.9991 |

**Soft clone for the closed loop = `SOFT-tau3`** (model `models/SOFT-tau3.pt`). Note: τ = 3 is the upper edge of the
declared grid; the grid is not extended (declared rule applied as written). BC (one-hot): best epoch 96, VAL regret
0.01969, VAL top-1 0.8917. Every fit ~55 s wall, peak RSS ~1.4 GB.

### 2026-09-11 17:59:57 UTC — Step 4 closed loop LAUNCHED + sensitivity fits (3 python processes; each chain runs one at a time)
- chain bash PID 3547848 → python PID 3547852 `t0_closed.py --clone BC --set evaluation` then `--set calibration`; cwd ws;
  log `logs/closed-BC.log`; outputs `results/CLOSED-BC-{evaluation,calibration}.json`; expected ≈ 18:03 UTC.
- chain bash PID 3547849 → python PID 3547853 `t0_closed.py --clone SOFT-tau3 --set evaluation` then calibration; log
  `logs/closed-SOFT-tau3.log`; outputs `results/CLOSED-SOFT-tau3-{evaluation,calibration}.json`; ≈ 18:03 UTC.
- chain bash PID 3547850 → python PID 3547854 `t0_clone.py --kind bc --epochs 400` then `--kind soft --taus 3 --epochs 400`;
  log `logs/clone-e400.log`; outputs `models/{BC-e400,SOFT-tau3-e400}.pt`, `results/CLONE-*-e400.json`; ≈ 18:08 UTC.

### 2026-09-11 18:02:24 UTC — declared closed-loop runs DONE (raw pooled EE; R_repr computed in aggregation)
- `CLOSED-BC-evaluation.json` (2a432f75…63ac): ee 113,632,227.01, served 0.99862, 57.279 beams, on-policy agree 0.8868.
- `CLOSED-BC-calibration.json` (d456d9d5…d82d): ee 117,272,460.05, served 0.99792, 57.846 beams, agree 0.8933.
- `CLOSED-SOFT-tau3-evaluation.json` (0622045c…a1): ee 113,960,161.83, served 0.99858, 56.958 beams, agree 0.9421.
- `CLOSED-SOFT-tau3-calibration.json` (4bd08dc0…323f): ee 117,807,343.84, served 0.99817, 57.125 beams, agree 0.9476.
- 18:02:35 UTC launched PID 3549253 `t0_entropy.py` (cwd ws, log `logs/entropy.log`, output `results/ENTROPY.json`, ≈ 18:05).
  e400 chain still running (PID 3547854 BC-e400).

### 2026-09-11 18:09 UTC — **ADMISSION VERDICT RECORDED (controller Amendment 6 instruction: verdict first)**
Aggregation `t0_aggregate.py BC SOFT-tau3` → `results/AGGREGATE.json` sha256 8e9f58de…bb52 (read-only over the JSONs below).
Declared 100-epoch clones, greedy, 24 episodes per set, fresh env per episode, pinned archive, sat; R_repr = (EE(clone) −
EE(A m=2dB)) / (EE(T0) − EE(A m=2dB)), pooled Σbits/ΣJ, EE(T0) and EE(A m=2dB) from my placebo-verified rollouts:

| set | EE(A m=2dB) | EE(T0) | BC EE | **BC R_repr** | SOFT-tau3 EE | **SOFT R_repr** |
|---|---:|---:|---:|---:|---:|---:|
| evaluation | 107,000,983.53 | 114,129,570.59 | 113,632,227.01 | **0.9302** (boot95 0.839–1.031) | 113,960,161.83 | **0.9762** (0.896–1.063) |
| calibration | 112,195,917.54 | 117,528,214.55 | 117,272,460.05 | **0.9520** (0.835–1.074) | 117,807,343.84 | **1.0523** (0.972–1.138) |

(the two rows are different episode sets and are not compared with each other). Every clone episode has the same start
epoch and t=0 observation as T0's and the reference's on that set. **Admission (R_repr ≥ 0.5 for ≥ 1 clone on both sets,
Amendment 3 §3): ADMITTED — both clones pass on both sets.** Verdict line written as line 1 of
`.scratch/t0-repr/T0-REPRESENTABILITY-2026-09-12.md`.
Copied back (sha256 identical both ends, 10 files) to `.scratch/t0-repr/results/`: AGGREGATE, PLACEBO ×2, CLOSED ×4,
TAU-SELECTION, CLONE-BC, CLONE-SOFT-tau3.

**State at pause (no t0-repr process running on sat):**
- DONE on sat, not yet in the report: `results/ENTROPY.json` (1e116ce6…d645), `CLONE-BC-e400.json` (10fe4ea3…449c),
  `CLONE-SOFT-tau3-e400.json` (cac34510…9a59), models `BC-e400.pt`, `SOFT-tau3-e400.pt`.
- PENDING on resume (idempotent): (1) closed loop of the e400 sensitivity clones — `run.sh t0_closed.py --clone BC-e400
  --set evaluation|calibration` and `--clone SOFT-tau3-e400 …` (≈ 1.5 min per chain); (2) `t0_aggregate.py BC SOFT-tau3
  BC-e400 SOFT-tau3-e400` into a separate file (keep AGGREGATE.json 8e9f58de… as the verdict's record — rename or add an
  output flag first); (3) report body (provenance header, all tables, entropy, sensitivity); (4) copy back all scripts +
  JSONs with sha256 verification.

### 2026-09-11 18:11:06 UTC — RESUMED (controller 18:15 message): pending items, ≤ 2 processes, nice 19
- `ws/run19.sh` = run.sh with `nice -n 19` (lower than the oracle / development lanes).
- chain bash PID 3555229 → python PID 3555232 `t0_closed.py --clone BC-e400 --set evaluation` then calibration; cwd ws; log
  `logs/closed-BC-e400.log`; outputs `results/CLOSED-BC-e400-{evaluation,calibration}.json`; expected ≈ 18:13 UTC.
- chain bash PID 3555230 → python PID 3555233 `t0_closed.py --clone SOFT-tau3-e400 …`; log `logs/closed-SOFT-tau3-e400.log`;
  outputs `results/CLOSED-SOFT-tau3-e400-{evaluation,calibration}.json`; ≈ 18:13 UTC.

### 2026-09-11 18:31 UTC — RESUMED after an opus session limit (~18:16 UTC); delta check first
- No t0-repr process alive on sat. `logs/closed-BC-e400.log` and `logs/closed-SOFT-tau3-e400.log` show **both chains had
  finished** at 18:12–18:13 UTC (all four `CLOSED-*-e400-*.json` present, verified by `ls`), so nothing was re-run.
- 18:32 UTC: shipped `t0_aggregate.py` f6a05cdc…0350 (adds `--out` / `--declared`; the verdict's `AGGREGATE.json`
  8e9f58de…bb52 is left untouched) and ran `run19.sh t0_aggregate.py --out AGGREGATE-WITH-SENSITIVITY.json --declared
  BC,SOFT-tau3 BC SOFT-tau3 BC-e400 SOFT-tau3-e400` → `results/AGGREGATE-WITH-SENSITIVITY.json` 80f7c394…94a4.
  Admission read on the declared clones: **admitted** (per-clone: BC ✓, SOFT-tau3 ✓, BC-e400 ✓, SOFT-tau3-e400 ✓).

### [x] Step 4b — 400-epoch sensitivity (declared 18:00 UTC, before any closed-loop run) — verdict UNCHANGED
| set | BC (declared, 100 ep) | BC-e400 | SOFT-τ3 (declared) | SOFT-τ3-e400 |
|---|---:|---:|---:|---:|
| evaluation R_repr | 0.9302 | 0.8902 (boot 0.806–0.995) | 0.9762 | 0.9461 (0.893–1.009) |
| calibration R_repr | 0.9520 | 0.9468 (0.857–1.061) | 1.0523 | 0.9840 (0.905–1.063) |
| TEST top-1 | 0.8929 | 0.9063 | 0.9448 | 0.9697 |
Longer training raises open-loop fidelity and does **not** raise closed-loop EE; all four values stay far above 0.5, so
the sensitivity would not change the admission. The verdict stays read on the declared 100-epoch clones.

### [x] Step 4c — conditional entropy: **H(a_T0 | observation, mask) = 0**
`results/ENTROPY.json` 1e116ce6…d645: T0 recomputed from the observation alone (`obs_snr/ln2 − 1·[obs_load == 0]`,
masked argmax) equals T0's logged action on **300,000/300,000** collected decisions (0 mismatches; also 24,000/24,000 on
each closed-loop set, §2 of the report). The requested fine-binning estimate is degenerate at this sample size (300,000
distinct bins for 300,000 decisions, 0 % shared, plug-in and Miller–Madow both 0 bits) — reported as such. Scales:
marginal H(a_T0) = 3.3168 bits, uniform-over-legal = 4.7090 bits, BC held-out CE = 0.4122 bits (variational bound).

### [x] Step 5 — report written, artefacts copied back
- `.scratch/t0-repr/T0-REPRESENTABILITY-2026-09-12.md`: first line = the verdict; provenance header [A] filled line by
  line; §2 placebo (incl. the `ho_per_user_min` derivation finding), §3 seed rule + disjointness, §4 clones + τ grid,
  §5 held-out accuracy, §6 entropy, §7 the two closed-loop tables (one per episode set, never compared), §8 files and
  cost, §9 what it does and does not establish.
- Copy-back: `tar` over ssh (never scp) of `results/`, `models/`, `logs/`, `data/*.json`, `run.sh`, `run19.sh`;
  **sha256 identical on both ends for all 55 files**. Not copied (> 20 MB, kept on sat, hashes recorded):
  `data/T0-collect-triple{0,1,2}.npz`, 70 MB each, 23cd918a…cee5 / 515bc53e…f991 / f419be02…4cc1.
- Workspace left intact on sat, no process running.
