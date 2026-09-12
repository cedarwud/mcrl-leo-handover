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
from mcrl.algorithms import cf_multi_sources as cfmulti
from mcrl.algorithms import cf_teacher as cft
from mcrl.algorithms.cf_ratio import CFRatioSettings, episode_seeds

REPO = C.REPO

# ---------------------------------------------------------------- seeds
DEV_TRAIN_BASE, DEV_ENV_BASE, DEV_MOB_BASE = 9_201_000, 9_202_000, 9_203_000
DEVVAL_ENV_BASE, DEVVAL_MOB_BASE = 9_211_000, 9_212_000
DEVVAL_RANDOM_BASE = 9_221_000
DEV_NULL_D2_BASE = 9_231_000
DEV_NULL_D3_BASE = 9_241_000
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
    7: ("D3-null", "equal_share"),
    # ---- Amendment 15 section 7, the k = 8 pairwise causal matrix -------------
    # 8 is PARAMETERISED over the teacher set: FULL{T0,Ti} for any candidate Ti,
    # and the singleton FULL{T0} which is the frozen D3-T0 (arm 4) by construction.
    # 9 is the MATCHED set-valued null, parameterised over the CARDINALITY only,
    # so one n = 2 null run is shared by every two-teacher candidate.
    8: ("D3-multi", "equal_share"),
    9: ("D3-multi-null", "equal_share"),
}
MULTI_ARMS: dict[int, str] = {8: "FULL", 9: "NULL"}
"""The MULTI-D3 arms of :data:`ARMS`, and which side of the matrix each one is."""

MATCHED_NULL_ARM: dict[int, int] = {4: 7, 8: 9}
"""Which arm is the declared matched null of a teacher arm.

The single-action ``D3-T0`` (4) is matched by the single-action ``D3-null`` (7); the
SET-VALUED ``FULL`` arm (8) is matched by the SET-VALUED null (9) and **never by arm
7** -- a set of size two is mechanically easier to satisfy than a set of size one, so
comparing a two-teacher set-valued loss against the one-action null would flatter the
FULL arm (Amendment 14 section 8).  (Pattern taken from the closed
``TDELTA-CANARY-PREP`` lane, commit ``ef8c866f``, whose arm 8 was the now-closed
``D3-T_DELTA`` and mapped to arm 7; that entry is REPLACED here, not extended.)
"""

TEACHER_OF = cfd.EXPECTED_TEACHER
"""Mechanism -> teacher IDENTITY.  Anything unlisted is T0.  (Alias of the library's
table, which :class:`~mcrl.algorithms.cf_dev.DevSettings` validates against; the name
matches the closed ``TDELTA-CANARY-PREP`` lane's so the two merge cleanly.)"""

# ---------------------------------------------------------------- k = 8 null
# Controller record CONTROLLER-K8-NULL-AND-READY-2026-09-12.md, commit 716f104e.
# The fixed two-proposal null is REJECTED as the k = 8 scientific comparator (Lane M
# demonstrated the cardinality-matching defect prospectively); the Bernoulli
# cardinality-matched null is selected, with p_singleton frozen and re-derived by the
# controller from the raw P0 artefact, not from a report.
P_SINGLETON_TNEXT_NUM: int = 9395
P_SINGLETON_TNEXT_DEN: int = 24000
P_SINGLETON_TNEXT: float = P_SINGLETON_TNEXT_NUM / P_SINGLETON_TNEXT_DEN
"""0.39145833333333335 -- the marginal |A_CF| = 1 rate of FULL{T0, T_NEXT} on the
frozen P0 collection.  A marginal, NOT a per-step rate: the controller's own
decomposition is t = 0 -> 0.2825, t = 1..8 -> 0.3290, t = 9 -> 1.0000 (T_NEXT's
mandatory final-step T0 fallback, singleton by construction, not agreement).  The
marginal is what the owner froze and it is implemented exactly; the divergence is
MEASURED and reported per step, never pre-empted."""

P0_DATASET_SHA256: str = (
    "881ed281f14f2233585f3ec50ec6f75b4caba4956ada427f36bbfadd9f3d6a0a"
)
"""Lane N ``results-lane-n/P0-DATASET.npz`` (21,600 rows, t = 1..9)."""

TNEXT_ACTION_TRACE_SHA256: str = (
    "0568b2220a02898527e2a3d4dbc609da0c0aaf2f24dca81a282f9d555fbd9bee"
)
"""The authoritative Lane N shared-trajectory action trace; the Lane M seam must
reproduce it exactly or the SEAM is repaired -- never T_NEXT."""

ALPHA0, TAU0, TAU_S0, MARGIN0, LAMBDA_E0 = 1.0, 3.0, 1.0, 0.15, 1.0
ETA0_EXPECTED = 110_507_234.83444457
TLE_FILE_SET_SHA256 = "427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9"


def epsilon_decay_episodes(episodes: int) -> int:
    """The CF3 compression rule: round(2000 * episodes / 9000)."""
    return max(1, round(2000 * int(episodes) / 9000))


def p_singleton_source_identity() -> str:
    """Where the frozen marginal came from, for the configuration hash."""
    src = cfmulti.tnext_identity()
    return (f"{src['source_id']}:{src['source_version']}"
            f"@P0-DATASET.npz:{P0_DATASET_SHA256}")


def bernoulli_null_kwargs() -> dict:
    """The SELECTED k = 8 matched null's frozen identity, in one place."""
    return {
        "null_id": cft.MULTI_NULL_BERNOULLI_ID,
        "p_singleton": P_SINGLETON_TNEXT,
        "p_singleton_numerator": P_SINGLETON_TNEXT_NUM,
        "p_singleton_denominator": P_SINGLETON_TNEXT_DEN,
        "p_singleton_rational": f"{P_SINGLETON_TNEXT_NUM}/{P_SINGLETON_TNEXT_DEN}",
        "p_singleton_source": p_singleton_source_identity(),
    }


def multi_spec(arm: int, teachers=None, *, n_proposals: int | None = None,
               bernoulli: bool = False):
    """The :class:`~mcrl.algorithms.cf_dev.MultiD3Spec` of a MULTI-D3 arm, or None.

    ``teachers`` names the FULL arm's teacher set (any iterable; it is canonicalised,
    so order never reaches the identity).  For the matched null pass either the
    cardinality ``n_proposals`` directly, or the FULL teacher set it is matched to
    and let the cardinality be read off it -- the null's identity keeps only the
    number, never the names.
    """
    a = int(arm)
    if a not in MULTI_ARMS:
        if teachers is not None or n_proposals is not None or bernoulli:
            raise SystemExit(f"arm {a} is not a MULTI-D3 arm; it takes no teacher set")
        return None
    if MULTI_ARMS[a] == "FULL":
        if n_proposals is not None or bernoulli:
            raise SystemExit("a FULL MULTI-D3 arm takes a teacher set, not a count")
        if teachers is None:
            raise SystemExit(f"arm {a} (FULL MULTI-D3) needs --teachers")
        return cfd.MultiD3Spec(teachers=cft.canonical_teacher_set(teachers))
    n = int(n_proposals) if n_proposals is not None else len(
        cft.canonical_teacher_set(teachers if teachers is not None else ())
    )
    if bernoulli:
        return cfd.MultiD3Spec(n_proposals=n, **bernoulli_null_kwargs())
    return cfd.MultiD3Spec(n_proposals=n, null_id=cft.MULTI_NULL_ID)


def spec_key(arm: int, k: int, teachers=None, *, n_proposals: int | None = None,
             bernoulli: bool = False) -> str:
    """The RUN-MANIFEST key of one run.  Arms 1-7 keep the historical ``ARM:K``."""
    a = int(arm)
    if a not in MULTI_ARMS:
        if teachers is not None or n_proposals is not None or bernoulli:
            raise SystemExit(f"arm {a} is not a MULTI-D3 arm; it takes no teacher set")
        return f"{a}:{int(k)}"
    spec = multi_spec(a, teachers, n_proposals=n_proposals, bernoulli=bernoulli)
    return f"{a}:{int(k)}:{spec.label()}"


def arm_name(arm: int, teachers=None, *, n_proposals: int | None = None,
             bernoulli: bool = False) -> str:
    mech, credit = ARMS[int(arm)]
    spec = multi_spec(arm, teachers, n_proposals=n_proposals, bernoulli=bernoulli)
    if spec is None:
        return f"E0-{int(arm)}-{mech}-{credit}"
    return f"E0-{int(arm)}-{mech}-{spec.label()}-{credit}"


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


def _null_key_for(mechanism: str, k: int):
    """The declared DEV-NULL generator identity of a matched null, or None."""
    base = cfd.NULL_BASE_FOR.get(mechanism)
    return None if base is None else (base, int(k))


def e0_dev_settings(mechanism: str, k: int, *, devval_episodes: int = N_DEVVAL,
                    tau: float | None = None):
    """``tau`` overrides the frozen teacher temperature (E0b's declared tau sweep;
    Amendment 6 section 7 allows the soft-distillation temperature to move on DEV /
    DEVVAL evidence).  Every other value stays frozen, and a different tau is a
    DIFFERENT VERSION: it changes the configuration hash."""
    if mechanism not in cft.MECHANISMS:
        raise SystemExit(f"unknown mechanism {mechanism!r}")
    return cfd.DevSettings(
        mechanism=mechanism,
        teacher=cfd.EXPECTED_TEACHER.get(mechanism, "T0"),
        alpha=ALPHA0, tau=(TAU0 if tau is None else float(tau)),
        tau_s=TAU_S0, margin=MARGIN0, lambda_e=LAMBDA_E0,
        null_key=_null_key_for(mechanism, k),
        devval_env_base=DEVVAL_ENV_BASE, devval_mobility_base=DEVVAL_MOB_BASE,
        devval_episodes=int(devval_episodes),
    )


def arm_config_payload(record, calib: dict, arm: int, k: int, *, episodes: int,
                       devval_episodes: int, calibration_sha256: str,
                       tau: float | None = None, teachers=None,
                       n_proposals: int | None = None,
                       bernoulli: bool = False) -> dict:
    """Everything that defines one arm's run, for its configuration hash.

    For a MULTI-D3 arm the payload additionally carries ``multi_spec``: the
    versioned MECHANISM identity, the CANONICAL TEACHER identities of a FULL arm,
    and the NULL identity plus cardinality of a matched null (Amendment 15 section
    6, requirement 9).  Arms 1-7 take no teacher set and their payload -- and so
    their configuration hash -- is byte-for-byte what it was before MULTI-D3
    existed (``tests/test_cf_multid3.py`` checks that against the base commit).
    """
    mech, credit = ARMS[int(arm)]
    spec = multi_spec(arm, teachers, n_proposals=n_proposals, bernoulli=bernoulli)
    train_seed, env_seed, mob_seed = dev_triple(k)
    extra: dict = {}
    if spec is not None:
        extra["multi_spec"] = dataclasses.asdict(spec)
        extra["multi_source_identities"] = {
            name: (cfmulti.tnext_identity() if name == cfmulti.T_NEXT_ID
                   else {"source_id": name})
            for name in spec.teachers
        }
    return {
        **extra,
        "arm": int(arm),
        "arm_name": arm_name(arm, teachers, n_proposals=n_proposals,
                             bernoulli=bernoulli),
        "mechanism": mech,
        "credit_mode": credit, "seed_index": int(k),
        "seeds": {"train": train_seed, "env": env_seed, "mobility": mob_seed},
        "devval_seeds": [list(x) for x in devval_seeds(devval_episodes)],
        "trainer_config": dataclasses.asdict(e0_config(record, episodes)),
        "cf_settings": dataclasses.asdict(e0_cf_settings(calib, credit)),
        "dev_settings": dataclasses.asdict(
            e0_dev_settings(mech, k, devval_episodes=devval_episodes, tau=tau)
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
