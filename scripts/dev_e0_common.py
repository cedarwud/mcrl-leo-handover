"""DEVHARNESS E0 shared constants, configuration and manifest (Amendment 6).

Development lane: every seed here is in a DEV / DEVVAL / DEV-NULL namespace
declared in Amendment 6 section 3 BEFORE any development result existed.  The
formal evaluation (9_111_000+i / 9_112_000+i), calibration (9_121_000+i /
9_122_000+i) and CONFIRM (9_311_000+i / 9_312_000+i) episodes are never touched;
``cf_dev.assert_dev_seed`` enforces it at every construction site and
``tests/test_cf_dev.py`` fails if any development path produces one of them.

The first E0 batch (Amendment 6 section 6, frozen): 300 episodes, epsilon
1.0 -> 0.01 over round(2000 * 300 / 9000) = 67 episodes then flat, eta fixed at
eta_0 (no eta update), lambda = 0, units s_B / s_E from the pilot's
``calibration.json``, everything else as CF3 A1, DEV triple k = 0 for every arm.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path

import cf3_common as C

import numpy as np

from mcrl.algorithms import cf_dev as cfd
from mcrl.algorithms import cf_teacher as cft
from mcrl.algorithms.cf_ratio import CFRatioSettings, episode_seeds

REPO = C.REPO

# ---------------------------------------------------------------- seeds
DEV_TRAIN_BASE, DEV_ENV_BASE, DEV_MOB_BASE = 9_201_000, 9_202_000, 9_203_000
DEVVAL_ENV_BASE, DEVVAL_MOB_BASE = 9_211_000, 9_212_000
DEVVAL_RANDOM_BASE = 9_221_000
DEV_NULL_D2_BASE = 9_231_000
N_DEVVAL = 24

# ---------------------------------------------------------------- batch
EPISODES = 300
DEVVAL_AT = (100, 200, 300)
CHECKPOINT_EVERY = 100
ARMS: dict[int, tuple[str, str]] = {
    1: ("D0", "equal_share"),
    2: ("D2-T0", "equal_share"),
    3: ("D2-null", "equal_share"),
    4: ("D3-T0", "equal_share"),
    5: ("D0", "lighting_price"),
    6: ("D2-T0", "lighting_price"),
}
ALPHA0, TAU0, TAU_S0, MARGIN0, LAMBDA_E0 = 1.0, 3.0, 1.0, 0.15, 1.0
ETA0_EXPECTED = 110_507_234.83444457
TLE_FILE_SET_SHA256 = "427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9"


def epsilon_decay_episodes(episodes: int) -> int:
    """The CF3 compression rule: round(2000 * episodes / 9000)."""
    return max(1, round(2000 * int(episodes) / 9000))


def arm_name(arm: int) -> str:
    mech, credit = ARMS[int(arm)]
    return f"E0-{int(arm)}-{mech}-{credit}"


def dev_triple(k: int) -> tuple[int, int, int]:
    """DEV training triple k (Amendment 6 section 3)."""
    triple = (DEV_TRAIN_BASE + int(k), DEV_ENV_BASE + int(k), DEV_MOB_BASE + int(k))
    for seed in triple:
        cfd.assert_dev_seed(seed, "DEV triple")
    return triple


def devval_seeds(n: int = N_DEVVAL):
    seeds = episode_seeds(DEVVAL_ENV_BASE, DEVVAL_MOB_BASE, n)
    cfd.assert_dev_seed_pairs(seeds, "DEVVAL")
    return seeds


def devval_at(episodes: int, smoke: bool = False) -> tuple[int, ...]:
    if smoke:
        return (1,)
    reads = [e for e in DEVVAL_AT if e <= int(episodes)]
    if int(episodes) not in reads:
        reads.append(int(episodes))
    return tuple(reads)


# ---------------------------------------------------------------- config
def e0_config(record, episodes: int):
    """The E0 trainer config: CF3 A1 with the E0 budget and epsilon compression."""
    cfg = C.pilot_config(record, "A1", int(episodes))
    return dataclasses.replace(
        cfg, epsilon_decay_episodes=epsilon_decay_episodes(episodes)
    )


def e0_cf_settings(calib: dict, credit_mode: str) -> CFRatioSettings:
    """CF-ratio settings for E0: eta fixed at eta_0, lambda 0, no sources.

    ``quarter_episodes`` / ``eta_first_update_episode`` are set beyond any E0
    budget AND :class:`~mcrl.algorithms.cf_dev.CFDevTrainer` refuses both calls
    outright; the calibration bases are zeroed so that no formal seed value
    appears anywhere in a development configuration.
    """
    return CFRatioSettings(
        source_kind="none", rho=1.0 / 9.0, alpha=1.0, h_cap_inter=0.6016,
        quarter_episodes=10**9, eta_first_update_episode=10**9,
        catfish_buffer_capacity=50_000,
        eta0=float(calib["eta0_bit_per_J"]),
        bits_scale=float(calib["bits_scale"]),
        joules_scale=float(calib["joules_scale"]),
        lambda0=0.0, dual_ascent=False,
        calibration_env_seed_base=0, calibration_mobility_seed_base=0,
        calibration_episodes=0, credit_mode=credit_mode,
    )


def e0_dev_settings(mechanism: str, k: int, *, devval_episodes: int = N_DEVVAL):
    if mechanism not in cft.MECHANISMS:
        raise SystemExit(f"unknown mechanism {mechanism!r}")
    return cfd.DevSettings(
        mechanism=mechanism,
        teacher="none" if mechanism == "D0" else "T0",
        alpha=ALPHA0, tau=TAU0, tau_s=TAU_S0, margin=MARGIN0, lambda_e=LAMBDA_E0,
        null_key=((DEV_NULL_D2_BASE, int(k)) if mechanism == "D2-null" else None),
        devval_env_base=DEVVAL_ENV_BASE, devval_mobility_base=DEVVAL_MOB_BASE,
        devval_episodes=int(devval_episodes),
    )


def arm_config_payload(record, calib: dict, arm: int, k: int, *, episodes: int,
                       devval_episodes: int, calibration_sha256: str) -> dict:
    """Everything that defines one arm's run, for its configuration hash."""
    mech, credit = ARMS[int(arm)]
    train_seed, env_seed, mob_seed = dev_triple(k)
    return {
        "arm": int(arm), "arm_name": arm_name(arm), "mechanism": mech,
        "credit_mode": credit, "seed_index": int(k),
        "seeds": {"train": train_seed, "env": env_seed, "mobility": mob_seed},
        "devval_seeds": [list(x) for x in devval_seeds(devval_episodes)],
        "trainer_config": dataclasses.asdict(e0_config(record, episodes)),
        "cf_settings": dataclasses.asdict(e0_cf_settings(calib, credit)),
        "dev_settings": dataclasses.asdict(
            e0_dev_settings(mech, k, devval_episodes=devval_episodes)
        ),
        "episodes": int(episodes),
        "devval_at": list(devval_at(episodes, smoke=(int(episodes) <= 3))),
        "calibration_sha256": calibration_sha256,
        "prereg_digest": record.digest,
        "tle_file_set_sha256": TLE_FILE_SET_SHA256,
    }


def config_hash(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()


# ---------------------------------------------------------------- manifest
MANIFEST_FILES = (
    "src/mcrl/algorithms/cf_dev.py",
    "src/mcrl/algorithms/cf_teacher.py",
    "src/mcrl/algorithms/cf_ratio.py",
    "src/mcrl/algorithms/cf_credit.py",
    "src/mcrl/algorithms/cf_sources.py",
    "src/mcrl/algorithms/modqn.py",
    "scripts/dev_e0_common.py",
    "scripts/run_dev_e0.py",
    "scripts/dev_e0_launch.py",
    "scripts/dev_e0_refs.py",
    "docs/dev-e0/V025-CONTROLLER-AMENDMENT-6-DEVELOPMENT-FIRST-TRAINING-2026-09-12.md",
)


def code_manifest() -> dict:
    """Code identity: commit, key-file hashes, whole-``src`` hash (cf3 pattern)."""
    commit_file = REPO / "COMMIT"
    commit = commit_file.read_text().strip() if commit_file.is_file() else "uncommitted-worktree"
    files = {f: C.sha256_file(REPO / f) for f in MANIFEST_FILES}
    h = hashlib.sha256()
    for p in sorted((REPO / "src").rglob("*.py")):
        h.update(str(p.relative_to(REPO)).encode())
        h.update(C.sha256_file(p).encode())
    return {"commit": commit, "files": files, "src_tree_sha256": h.hexdigest()}


def manifest_digest(code: dict) -> str:
    return hashlib.sha256(json.dumps(code, sort_keys=True).encode()).hexdigest()


# ---------------------------------------------------------------- runtime
def assert_environment() -> str:
    """Pinned TLE archive + this tree's ``mcrl`` + single-threaded BLAS."""
    import os

    import mcrl
    from mcrl.runtime import training_pipeline as tp

    if not str(Path(mcrl.__file__).resolve()).startswith(str((REPO / "src").resolve())):
        raise SystemExit(f"wrong mcrl tree: {mcrl.__file__}")
    for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        if os.environ.get(key) != "1":
            raise SystemExit(f"{key} must be 1")
    tle = tp.assert_tle_archive_pinned()
    if tle != TLE_FILE_SET_SHA256:
        raise SystemExit(f"TLE file set {tle} is not the pinned archive")
    return tle


# ---------------------------------------------------------------- references
def reference_policies() -> dict:
    """The DEVVAL rule references (Amendment 6 section 6), rolled once."""
    return {
        "A_m2dB": C.rule_policy("C1_A_m2dB"),
        "LP_prev_c1_m0": cft.t0_policy(),
        "MAX_NOMINAL_GAIN": C.rule_policy("MAX_NOMINAL_GAIN"),
    }


def random_reference_factory(base: int = DEVVAL_RANDOM_BASE):
    """RANDOM on DEVVAL: episode i draws from ``default_rng(9_221_000 + i)``."""
    from mcrl.algorithms import cf_sources as cfs

    def factory(i: int):
        cfd.assert_dev_seed(base + i, "DEVVAL RANDOM")
        fn = cfs.random_legal(np.random.default_rng(base + i))
        return lambda enc, masks, states: fn(states, masks)

    return factory
