**Found 0 INVALIDATES and 0 BIASES findings in the CF3 pilot launch control and Amendment 3 diff (3 COSMETIC observations noted); the launch may proceed.**

---

# Independent Expert Review: Three-Catfish (CF3) Pilot Launch Control & Amendment 3

**Reviewer Model**: Antigravity (Independent Context / Fresh Reviewer)  
**Date**: 2026-09-11  
**Target Repository**: `/home/u24/papers/mcrl-leo-handover-cf3`  
**Git Branch / Commit Range**: `cf3/pilot-20260911` (`e8a04ccf..f297334e`, commits `e28100b1`, `5938450b`, `99252ef8`, `d04d9dbe`, `f297334e`)  
**Governing Documents**:
- `docs/cf3-pilot/V025-CONTROLLER-DECLARATION-THREE-CATFISH-PILOT-2026-09-11.md`
- `docs/cf3-pilot/V025-CONTROLLER-AMENDMENT-1-THREE-CATFISH-PILOT-2026-09-11.md`
- `docs/cf3-pilot/V025-CONTROLLER-AMENDMENT-2-EE-ONLY-2026-09-11.md`
- `docs/cf3-pilot/V025-CONTROLLER-AMENDMENT-3-PREGENERATED-SOURCE-POOLS-2026-09-11.md`

---

## 1. Executive Summary

This independent code review directly inspects the diff `e8a04ccf..f297334e` gating the 12-run training launch (arms A0, A1, A2, A3 across seeds 0–2). The review evaluated the launch-control overhaul (manifest verification, single-writer atomic `DECISION.json`, process liveness detection, error propagation) and the architectural shift to pre-generated immutable source pools under **Amendment 3**.

Every line of the diff was reviewed against the declared requirements and tested against the live test suite (17/17 passed in 117.7s). **No invalidating defects and no methodological biases were found.** The 12-run training batch is protected by fail-closed cryptographic manifests, strict single-writer lock semantics on gate decisions, complete seed-space disjointness, and exact minibatch composition.

Three minor observations of **COSMETIC** severity are documented below.

---

## 2. Requirement-by-Requirement Verification

### Item 1: Learning-Check Failure Path
- **Status**: **PASS**
- **Verification Method**: Verified by reading [`src/mcrl/algorithms/cf_ratio.py:682-693, 802-823`](file:///home/u24/papers/mcrl-leo-handover-cf3/src/mcrl/algorithms/cf_ratio.py#L682-L693) and [`scripts/run_cf3_pilot.py:334-362`](file:///home/u24/papers/mcrl-leo-handover-cf3/scripts/run_cf3_pilot.py#L334-L362), plus test `test_learning_check_failure_leaves_artifacts_ending_at_the_gate_episode`.
- **Findings**:
  - In `train_cf`, when `episode_done == st.eta_first_update_episode` (episode 500, or 2 in smoke mode), `quarter_update` triggers `self.learning_gate`. If the gate fails and raises `LearningCheckStop`, `quarter_update` sets `applied=False`, `kind="quarter-gate-failed"`, appends the row to `dual_trajectory`, and attaches `stop.row = row`.
  - In `train_cf`, the exception is caught, `log["quarter"] = stop.row`, the episode log dictionary is appended to `logs`, and `episode_callback(log)` is executed **before** `raise gate_stop`.
  - In `run_cf3_pilot.py:355-362`, the `except cfr.LearningCheckStop as stop:` block invokes `save(len(logs))`. Because episode 500 was fully logged, `len(logs) == 500`. `save(500)` writes `next_episode: 500` to `resume.pt`, 500 rows to `episode-logs.json`, and records `episodes_completed: 500` in `status.json`.
  - The previous synthesized episode count defect (`len(logs) + 1`) is completely eliminated. Saved status, resume state, and log counts agree at exactly 500.

### Item 2: Atomic Single-Writer `DECISION.json` & Loud Gate Failure
- **Status**: **PASS**
- **Verification Method**: Verified by reading [`scripts/run_cf3_pilot.py:51-54, 95-102, 258-309, 363-367`](file:///home/u24/papers/mcrl-leo-handover-cf3/scripts/run_cf3_pilot.py#L258-L309) and [`scripts/cf3_launch.py:136-145`](file:///home/u24/papers/mcrl-leo-handover-cf3/scripts/cf3_launch.py#L136-L145).
- **Findings**:
  - **Single Writer & Locking**: Process concurrency is controlled by `os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)`. Only the single process that acquires `DECISION.lock` computes and writes `DECISION.json`. Temp files are PID-unique (`DECISION.json.{os.getpid()}.tmp`) and replaced atomically (`os.replace`).
  - **Comprehensive Fingerprint**: Both individual `A1-s{k}.json` files and `DECISION.json` record the gate fingerprint `gfp`:
    - `code_digest` (manifest digest)
    - `calibration_sha256`
    - `tle_file_set_sha256`
    - `gate_episode` (500)
    - `random_reference_ee`
    - `gate_seeds` (`[0, 1, 2]`)
    - `code_commit`
    - `A1_measured_ee` values and seed indices
  - **Stale Rejection**: Stale `A1-s{j}.json` or stale `DECISION.json` files from prior runs with differing fingerprints are rejected immediately via `SystemExit("...; fail closed")`.
  - **Dead A1 Run / Gate Timeout**: If an A1 run dies before writing its reading, `gate()` waits up to `gate_timeout_s` (4 hours default) and raises `GateUnavailable("timed out waiting for the A1 gate readings")`. `GateUnavailable` inherits from `RuntimeError` (`Exception`). It is caught by `except Exception as err:`, writes `status="failed"` to `status.json`, and re-raises. It is **never** swallowed and **never** marked `stopped-learning-check`. In `cf3_launch.py`, `real_fail` requires `DECISION.json` with `pass: False`, so an incomplete or dead gate is planned as `"resume"`, never `"finished"`.

### Item 3: Code Manifest & Resume Fingerprint Security
- **Status**: **PASS**
- **Verification Method**: Verified by reading [`scripts/cf3_common.py:153-185`](file:///home/u24/papers/mcrl-leo-handover-cf3/scripts/cf3_common.py#L153-L185), [`scripts/cf3_launch.py:95-126`](file:///home/u24/papers/mcrl-leo-handover-cf3/scripts/cf3_launch.py#L95-L126), and [`scripts/run_cf3_pilot.py:106-115, 167-186`](file:///home/u24/papers/mcrl-leo-handover-cf3/scripts/run_cf3_pilot.py#L167-L186).
- **Findings**:
  - `code_manifest()` computes SHA-256 hashes of all 11 critical files (core algorithms `cf_ratio.py`, `cf_sources.py`, `modqn.py`, launcher `cf3_launch.py`, driver `run_cf3_pilot.py`, pool generator `cf3_pools.py`, `cf3_common.py`, and declaration + Amendments 1–3), plus a recursive hash of the entire `src/` tree and the repository commit ID.
  - `RUN-MANIFEST.json` binds the code manifest, calibration file SHA, TLE root, training seeds, run specs, and SHA-256 hashes of all pool files.
  - On launch, `cf3_launch.py` and `run_cf3_pilot.py` assert `RUN-MANIFEST.json` matches the executing code and pool files; mismatch aborts immediately ("fail closed").
  - On resume, `resume.pt` loads `fingerprint`, which includes `code`, `code_digest`, `calibration_sha256`, `tle_file_set_sha256`, and `pool_sha256`. Any code or pool modification causes an immediate `SystemExit("resume fingerprint does not match this run")`.

### Item 4: Process-Level Integration Testing
- **Status**: **PASS**
- **Verification Method**: Verified by reading [`scripts/cf3_proctest.py:1-127`](file:///home/u24/papers/mcrl-leo-handover-cf3/scripts/cf3_proctest.py#L1-L127).
- **Findings**:
  - `cf3_proctest.py` implements end-to-end integration tests through the real `cf3_launch.py` and `run_cf3_pilot.py` executing under `systemd-run --user --scope`.
  - **T1**: Tests an uninterrupted A3 seed 0 run vs. a run stopped cleanly at episode 2 (`--stop-after 2`) and resumed via `cf3_launch.py`. Verifies bit-identical Q-network weights (`torch.equal`), identical episode bits logs, contiguous logs `[0, 1, 2]`, identical `_catfish_rng` state, and verifies that a second launch while live starts no duplicate process.
  - **T2**: Injects an impossible random reference (`1e12`), forcing a learning-check failure across A1 seeds 0–2. Confirms all three runs stop cleanly at episode 2 with `status: "stopped-learning-check"`, logs `[0, 1]`, single `DECISION.lock`, `DECISION.json` with `pass: false`, and confirms `cf3_launch.py` subsequently plans them as `"finished"`.

### Item 5: Launcher Process Management & 12-Run Planning
- **Status**: **PASS**
- **Verification Method**: Verified by reading [`scripts/cf3_launch.py:41-65, 84-94, 152-182`](file:///home/u24/papers/mcrl-leo-handover-cf3/scripts/cf3_launch.py#L41-L65) and testing `/proc/{pid}/cmdline` execution under `systemd-run --user --scope`.
- **Findings**:
  - **Liveness Detection**: `is_live()` reads the PID file, inspects `/proc/{pid}/cmdline`, and checks `os.readlink("/proc/{pid}/cwd")`. It verifies that the PID exists, its command line contains `scripts/run_cf3_pilot.py --arm <ARM> --seed-index <K> --root <ROOT>`, and its working directory is strictly `C.REPO`. Because `systemd-run --scope` executes the target process in-place, `/proc/{pid}` belongs directly to the Python driver.
  - **Startup Verification**: After spawning, `cf3_launch.py` sleeps 10 seconds and verifies every launched process is still alive and matches `is_live()`. If any died or failed to start, it raises `SystemExit(f"FAILED TO START (or died within 10 s): {dead}")`.
  - **Planned Runs**: `DEFAULT_SPECS` plans exactly 12 runs: `A0:0..2`, `A1:0..2`, `A2:0..2`, `A3:0..2`. Duplicate specs and unexpected counts trigger immediate `SystemExit`.

### Item 6: Amendment 3 Pre-Generated Source Pools
- **Status**: **PASS**
- **Verification Method**: Verified by reading [`docs/cf3-pilot/V025-CONTROLLER-AMENDMENT-3-PREGENERATED-SOURCE-POOLS-2026-09-11.md`](file:///home/u24/papers/mcrl-leo-handover-cf3/docs/cf3-pilot/V025-CONTROLLER-AMENDMENT-3-PREGENERATED-SOURCE-POOLS-2026-09-11.md), [`src/mcrl/algorithms/cf_ratio.py:206-302, 577-600`](file:///home/u24/papers/mcrl-leo-handover-cf3/src/mcrl/algorithms/cf_ratio.py#L206-L302), [`scripts/cf3_pools.py:1-82`](file:///home/u24/papers/mcrl-leo-handover-cf3/scripts/cf3_pools.py#L1-L82), and automated unit tests.
- **Findings**:
  - **Pool Generation**: `cf3_pools.py` rolls each source policy in a fresh environment for 100 episodes (100,000 potential transitions) on deterministic pool seeds.
  - **Seed Disjointness**: Checked mathematically and empirically. Pool env seeds (`9_141_000 + 1000k + i`) and pool mobility seeds (`9_161_000 + 1000k + i`) are separated by 20,000 (resolving the previous collision in commit `d04d9dbe`) and are completely disjoint from calibration, evaluation, random action, and training seeds.
  - **Immutability**: `PoolBuffer` sets `write=False` on all underlying NumPy arrays (`states`, `actions`, `rewards_raw`, `next_states`, `masks`, `next_masks`, `dones`). The buffer has no push/append methods. Unit test `test_pool_seed_range_is_disjoint_and_pools_are_immutable` confirms writing raises `ValueError`.
  - **Minibatch Composition**: Exactly matches Amendment 1: 113 rows from main replay + 5 rows from source 0 + 5 rows from source 1 + 5 rows from source 2 = 128 total batch size.
  - **RNG Independence**: Pool loading does not instantiate training environments or touch the trainer's `_train_rng` or `_env_rng`. Pool sampling is driven exclusively by `_catfish_rng` (`train_seed + 70_001`). `test_a1_a2_main_rollouts_identical_before_first_source_sample` passes bit-for-bit.
  - **A2 vs. A3 Pool Generation Parity**: Both `cf3` (A2) and `null3` (A3) pools use the identical seeds, identical environment configurations, and identical transition filtering. They differ strictly in the source policy (`policy_factory` in `cf3_pools.py`). Initial states (`t0_obs_sha256`) match bit-for-bit.

---

## 3. Seed Space Collision Audit

A comprehensive disjointness check was executed across all five seed indices ($k \in \{0..4\}$) and all episode ranges:

| Seed Set | Formula / Range ($k \in \{0..4\}, i \in \{0..99\}$) | Min Seed | Max Seed | Disjoint from Others |
| :--- | :--- | :--- | :--- | :---: |
| **Training Seeds** | `TRAIN_SEEDS[k]` | 7 | 1,341 | **YES** |
| **Calibration Env** | `CAL_ENV_BASE + i` ($i \in \{0..23\}$) | 9,121,000 | 9,121,023 | **YES** |
| **Calibration Mob**| `CAL_MOB_BASE + i` ($i \in \{0..23\}$) | 9,122,000 | 9,122,023 | **YES** |
| **Evaluation Env** | `EVAL_ENV_BASE + i` ($i \in \{0..23\}$) | 9,111,000 | 9,111,023 | **YES** |
| **Evaluation Mob** | `EVAL_MOB_BASE + i` ($i \in \{0..23\}$) | 9,112,000 | 9,112,023 | **YES** |
| **Random Reference**| `RANDOM_ACTION_BASE + i` ($i \in \{0..999\}$) | 9,131,000 | 9,131,999 | **YES** |
| **Pool Env Seeds** | `9_141_000 + 1000*k + i` | 9,141,000 | 9,145,099 | **YES** |
| **Pool Mob Seeds** | `9_161_000 + 1000*k + i` | 9,161,000 | 9,165,099 | **YES** |
| **Pool NULL RNG**  | Tuple `(9_151_000, k, j, i)` (SeedSequence) | N/A (tuple) | N/A (tuple) | **YES** |

*Verification*: Direct execution of pairwise set intersections across all sets yielded `0` collisions.

---

## 4. Findings & Observations

### COSMETIC Findings

#### Finding C-01: `scripts/cf3_memtest.py` Missing `pools` Parameter Under Amendment 3
- **Severity**: **COSMETIC**
- **Location**: [`scripts/cf3_memtest.py:57-59`](file:///home/u24/papers/mcrl-leo-handover-cf3/scripts/cf3_memtest.py#L57-L59)
- **Status**: Verified by code reading.
- **Scenario**: `cf3_memtest.py` was authored in commit `e28100b1` for the pre-Amendment-3 streaming setup. It instantiates `CFRatioTrainer(factory(), TrainerConfig(**cfgd), st, ...)` without passing `pools`. Under Amendment 3 (commit `99252ef8`), `CFRatioTrainer` requires `pools` when `source_kind != "none"`. If an operator runs `cf3_memtest.py` against an A2 resume checkpoint, it will fail with `MCRLContractError: source_kind 'cf3' needs pools ...`.
- **Impact**: Zero impact on training launch. `cf3_memtest.py` is an uninvoked diagnostic utility not referenced by `cf3_launch.py`, `run_cf3_pilot.py`, `cf3_proctest.py`, or `RUN-MANIFEST.json`.

#### Finding C-02: Discrepancy Between Default Cgroup MemoryMax and Driver RSS Cap for CF Arms
- **Severity**: **COSMETIC**
- **Location**: [`scripts/cf3_launch.py:75-77, 160-166`](file:///home/u24/papers/mcrl-leo-handover-cf3/scripts/cf3_launch.py#L160-L166)
- **Status**: Verified by code reading.
- **Scenario**: In `cf3_launch.py`, `--memory-max` defaults to `5G` and `--memory-max-cf` defaults to `None`. When launching A2 and A3, the driver is invoked with `--rss-cap-gb 6.5`, but the cgroup `MemoryMax` is set to `5G`. If a CF run were to exceed 5.0 GB RSS, `systemd` would SIGKILL the cgroup before Python's internal memory cap triggers. Under Amendment 3, A2/A3 memory is < 2.0 GB RSS (pre-generated pools add only ~300 MB total and eliminate duplicate `TleArchive` caches), so neither limit is approached.
- **Impact**: Zero impact on normal training.

#### Finding C-03: `test_pool_seed_range_is_disjoint_and_pools_are_immutable` Only Asserts `range(3)`
- **Severity**: **COSMETIC**
- **Location**: [`tests/test_cf_ratio.py:458-461`](file:///home/u24/papers/mcrl-leo-handover-cf3/tests/test_cf_ratio.py#L458-L461)
- **Status**: Verified by code reading.
- **Scenario**: The test checks `pool = {x for k in range(3) for p in C.pool_seeds(k) for x in p}`. While the 12-run pilot only executes seeds 0..2, `C.TRAIN_SEEDS` defines 5 seed triples. Expanding the test assertion from `range(3)` to `range(5)` would provide complete coverage if seeds 3–4 are launched in a subsequent wave. Pairwise set checks confirmed seeds 3–4 are also fully disjoint.
- **Impact**: Test passes and covers the current 12-run launch.

---

## 5. Launch Gate Decision

| Check Category | Result |
| :--- | :---: |
| Invalidating Defects | **0** |
| Methodological Biases | **0** |
| Cosmetic Observations | **3** |
| Test Suite Status | **17/17 PASS** |
| Seed Space Integrity | **Verified Disjoint** |
| Fail-Closed Integrity | **Verified** |

**Recommendation: The 12-run CF3 pilot training launch may proceed immediately.**
