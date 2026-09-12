"""S1 formal screen: the frozen arm list, namespaces and configuration hashes.

Governing: ``.scratch/multi-catfish-v025-physics-successor/
V025-CONTROLLER-AMENDMENT-13-S1-FROZEN-CONFIGURATION-2026-09-12.md`` (Amendment 13),
with Amendment 12 for ``D3-XEP`` and Amendment 8 section 3b for ``D3-null``.

**FORMAL LANE.**  Unlike the E0 / E1 development harness this spends the formal
evaluation episodes ``9_111_000+i / 9_112_000+i``.  Everything here is frozen before a
single number exists: six trained arms, three seeds, 1000 episodes, one terminal
evaluation read per run.

Seed isolation (Amendment 13 sections 4 and 5), enforced by
:func:`mcrl.algorithms.cf_dev.assert_s1_seed`:

* ``S1-TRAIN`` train / env / mobility ``9_251_000 / 9_252_000 / 9_253_000 + k``,
  k = 0, 1, 2 -- the SAME index triple for all six arms.  No DEV stream is reused.
* ``S1-NULL`` ``default_rng((9_261_000, k))`` for ``D3-null``.  The development
  ``(9_241_000, k)`` streams are refused outright in this lane.
* ``T0-XEP`` is the one declared exception: it keeps the sealed DEV-NULL reference
  trajectory of Amendment 12 and is never regenerated.

Evaluation is read ONCE, at the final episode.  Intermediate reads would spend the
formal set repeatedly for no declared purpose, so ``S1_EVAL_AT`` has one entry.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import cf3_common as C
import dev_e0_common as D

from mcrl.algorithms import cf_dev as cfd
from mcrl.algorithms.cf_ratio import CFRatioSettings, episode_seeds

REPO = C.REPO

# ---------------------------------------------------------------- namespaces
S1_TRAIN_BASE = cfd.S1_TRAIN_BASE      # 9_251_000
S1_ENV_BASE = cfd.S1_ENV_BASE          # 9_252_000
S1_MOB_BASE = cfd.S1_MOB_BASE          # 9_253_000
S1_NULL_BASE = cfd.S1_NULL_BASE        # 9_261_000
EVAL_ENV_BASE = cfd.FORMAL_EVAL_ENV_BASE   # 9_111_000
EVAL_MOB_BASE = cfd.FORMAL_EVAL_MOB_BASE   # 9_112_000
SEED_INDICES = (0, 1, 2)
N_EVAL = 24

# ---------------------------------------------------------------- budget
EPISODES = 1000
S1_EVAL_AT = (1000,)
CHECKPOINT_EVERY = 100
CREDIT_MODE = "equal_share"
ALPHA0, TAU_S0, MARGIN0, LAMBDA_E0 = D.ALPHA0, D.TAU_S0, D.MARGIN0, D.LAMBDA_E0
D2_TAU = 0.3
ETA0_EXPECTED = D.ETA0_EXPECTED
TLE_FILE_SET_SHA256 = D.TLE_FILE_SET_SHA256
FROZEN_MODQN_SHA256 = (
    "e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b"
)
"""The published 9000-episode MODQN eq-(16) reference, ROLLED ONCE, never trained."""


# ---------------------------------------------------------------- arms
@dataclass(frozen=True)
class S1Arm:
    name: str
    kind: str            # "cf" (the ratio learner + a teacher) | "modqn" (eq-(16))
    role: str
    mechanism: str | None = None
    tau: float | None = None


ARMS: dict[int, S1Arm] = {
    1: S1Arm("D0", "cf", "control, catfish off (paired causal comparator)", "D0"),
    2: S1Arm("D3-T0", "cf", "the frozen primary", "D3-T0"),
    3: S1Arm("D3-null", "cf", "matched hard null (Amendment 4 conjunctive gate)",
             "D3-null"),
    4: S1Arm("D3-XEP", "cf", "plausible-but-uninformative null (Amendment 12)",
             "D3-XEP"),
    5: S1Arm("D2-T0-tau0p3", "cf", "strongest soft comparator, no superiority claim",
             "D2-T0", D2_TAU),
    6: S1Arm("MODQN-eq16", "modqn", "same-budget win gate (Amendment 13 section 2)"),
}
"""Amendment 13 section 3, verbatim.  Six trained arms.  D1 / D4 / B2 / exact-DR stay
closed and are NOT resurrected to satisfy Amendment 6's superseded nine-arm count."""

SPECS: tuple[str, ...] = tuple(
    f"{arm}:{k}" for arm in sorted(ARMS) for k in SEED_INDICES
)
"""All 18 trained runs.  Amendment 13 section 7: the formal set is opened with the
complete matrix or not at all."""


def arm_name(arm: int) -> str:
    return f"S1-{int(arm)}-{ARMS[int(arm)].name}"


def s1_triple(k: int) -> tuple[int, int, int]:
    return cfd.s1_triple(k)


def eval_seeds(n: int = N_EVAL):
    seeds = episode_seeds(EVAL_ENV_BASE, EVAL_MOB_BASE, n)
    cfd.assert_lane_seed_pairs(seeds, "S1 formal evaluation", lane=cfd.S1_LANE)
    return seeds


def eval_at(episodes: int) -> tuple[int, ...]:
    """One terminal read.  No intermediate peeking at the formal evaluation set."""
    return (int(episodes),)


# ---------------------------------------------------------------- config
def s1_config(record, arm: int, episodes: int):
    """The trainer config for one arm.

    ``cf`` arms: the frozen E0/E1 kernel -- shared-continuation bootstrap, gamma 1.
    ``modqn``: the frozen eq-(16) recipe -- per-head max bootstrap, the prereg's own
    discount.  BOTH get the same budget-scaled epsilon schedule
    ``round(2000 N / 9000)``, so the same-budget comparison is not confounded by a
    different exploration schedule (the frozen 9000-episode run's own 2000-episode
    decay would leave a 1000-episode baseline still exploring at the end).
    """
    pilot_arm = "A0" if ARMS[int(arm)].kind == "modqn" else "A1"
    cfg = C.pilot_config(record, pilot_arm, int(episodes))
    return dataclasses.replace(
        cfg, epsilon_decay_episodes=D.epsilon_decay_episodes(episodes)
    )


def s1_cf_settings(calib: dict) -> CFRatioSettings:
    """CF-ratio settings: eta fixed at eta_0, lambda 0, no source pools, no
    calibration reading (the calibration episodes stay untouched at S1 too)."""
    return CFRatioSettings(
        source_kind="none", rho=1.0 / 9.0, alpha=1.0, h_cap_inter=0.6016,
        quarter_episodes=10**9, eta_first_update_episode=10**9,
        catfish_buffer_capacity=50_000,
        eta0=float(calib["eta0_bit_per_J"]),
        bits_scale=float(calib["bits_scale"]),
        joules_scale=float(calib["joules_scale"]),
        lambda0=0.0, dual_ascent=False,
        calibration_env_seed_base=0, calibration_mobility_seed_base=0,
        calibration_episodes=0, credit_mode=CREDIT_MODE,
    )


def s1_dev_settings(arm: int, k: int, *, eval_episodes: int = N_EVAL):
    """The S1-lane teacher settings for one arm (``cf`` arms only)."""
    spec = ARMS[int(arm)]
    if spec.kind != "cf":
        raise SystemExit(f"arm {arm} ({spec.name}) has no teacher settings")
    mech = spec.mechanism
    xep = mech == "D3-XEP"
    return cfd.DevSettings(
        lane=cfd.S1_LANE,
        mechanism=mech,
        teacher={"D0": "none", "D3-null": "random",
                 "D3-XEP": "T0-XEP"}.get(mech, "T0"),
        alpha=ALPHA0, tau=(D.TAU0 if spec.tau is None else float(spec.tau)),
        tau_s=TAU_S0, margin=MARGIN0, lambda_e=LAMBDA_E0,
        null_key=((S1_NULL_BASE, int(k)) if mech == "D3-null" else None),
        devval_env_base=EVAL_ENV_BASE, devval_mobility_base=EVAL_MOB_BASE,
        devval_episodes=int(eval_episodes),
        xep_reference_sha256=(D.XEP_REFERENCE_SHA256 if xep else None),
        xep_reference_key=((D.XEP_REF_ENV_SEED, D.XEP_REF_MOB_SEED) if xep else None),
        xep_reference_policy=(D.XEP_REF_POLICY if xep else None),
    )


def arm_config_payload(record, calib: dict, arm: int, k: int, *, episodes: int,
                       eval_episodes: int, calibration_sha256: str) -> dict:
    """Everything that defines one S1 run, for its configuration hash."""
    spec = ARMS[int(arm)]
    train_seed, env_seed, mob_seed = s1_triple(k)
    payload = {
        "lane": cfd.S1_LANE,
        "arm": int(arm), "arm_name": arm_name(arm), "arm_label": spec.name,
        "kind": spec.kind, "role": spec.role, "mechanism": spec.mechanism,
        "credit_mode": (CREDIT_MODE if spec.kind == "cf" else None),
        "seed_index": int(k),
        "seeds": {"train": train_seed, "env": env_seed, "mobility": mob_seed},
        "eval_seeds": [list(x) for x in eval_seeds(eval_episodes)],
        "trainer_config": dataclasses.asdict(s1_config(record, arm, episodes)),
        "episodes": int(episodes),
        "eval_at": list(eval_at(episodes)),
        "calibration_sha256": calibration_sha256,
        "prereg_digest": record.digest,
        "tle_file_set_sha256": TLE_FILE_SET_SHA256,
    }
    if spec.kind == "cf":
        payload["cf_settings"] = dataclasses.asdict(s1_cf_settings(calib))
        payload["dev_settings"] = dataclasses.asdict(
            s1_dev_settings(arm, k, eval_episodes=eval_episodes)
        )
    return payload


def config_hash(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()


# ---------------------------------------------------------------- manifest
MANIFEST_FILES = D.MANIFEST_FILES + (
    "scripts/s1_common.py",
    "scripts/run_s1.py",
    "scripts/s1_launch.py",
    "scripts/s1_reference.py",
    "scripts/s1_manifest.py",
    "docs/dev-e0/V025-CONTROLLER-AMENDMENT-12-S1-SECOND-NULL-2026-09-12.md",
    "docs/dev-e0/V025-CONTROLLER-AMENDMENT-13-S1-FROZEN-CONFIGURATION-2026-09-12.md",
)


def code_manifest() -> dict:
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


def declared_manifest(record, calib: dict, calibration_sha256: str, *,
                      episodes: int = EPISODES,
                      eval_episodes: int = N_EVAL) -> dict:
    """The whole frozen S1 declaration, in one hashable object.

    Amendment 13 section 7 item 7: the six-arm list, the S1-TRAIN / S1-NULL
    namespaces, the 1000-episode depth, the frozen hyperparameters and the formal
    evaluation namespace, committed and hashed BEFORE any formal outcome exists.
    """
    code = code_manifest()
    arm_payloads = {
        f"{arm}:{k}": arm_config_payload(
            record, calib, arm, k, episodes=episodes,
            eval_episodes=eval_episodes, calibration_sha256=calibration_sha256)
        for arm in sorted(ARMS) for k in SEED_INDICES
    }
    return {
        "declaration": "S1 frozen configuration",
        "authority": [
            "V025-CONTROLLER-AMENDMENT-13-S1-FROZEN-CONFIGURATION-2026-09-12.md",
            "V025-CONTROLLER-AMENDMENT-12-S1-SECOND-NULL-2026-09-12.md",
            "V025-CONTROLLER-AMENDMENT-8-CONVERGENCE-FUNNEL-2026-09-12.md section 3b",
        ],
        "lane": cfd.S1_LANE,
        "arms": {str(a): dataclasses.asdict(s) for a, s in sorted(ARMS.items())},
        "rolled_reference": {
            "label": "BASELINE_MODQN_eq16_frozen_9000ep",
            "checkpoint_sha256": FROZEN_MODQN_SHA256,
            "training": "none -- rolled once under the same formal evaluation protocol",
            "role": ("published / frozen reference; NOT a conjunctive S1 veto "
                     "(Amendment 13 section 2)"),
        },
        "episodes": int(episodes),
        "seed_indices": list(SEED_INDICES),
        "specs": list(SPECS),
        "n_trained_runs": len(SPECS),
        "eval_at": list(eval_at(episodes)),
        "eval_episodes": int(eval_episodes),
        "namespaces": {
            "S1_TRAIN": {"train": S1_TRAIN_BASE, "env": S1_ENV_BASE,
                         "mobility": S1_MOB_BASE},
            "S1_NULL": [S1_NULL_BASE, "k"],
            "FORMAL_EVALUATION": {"env": EVAL_ENV_BASE, "mobility": EVAL_MOB_BASE},
            "T0_XEP_REFERENCE": {
                "env": D.XEP_REF_ENV_SEED, "mobility": D.XEP_REF_MOB_SEED,
                "note": ("DEV-NULL, sealed, never regenerated "
                         "(Amendment 13 section 5 exception)"),
            },
            "NEVER_TOUCHED_BY_S1": {
                "calibration": [9_121_000, 9_122_000],
                "CONFIRM": [9_301_000, 9_302_000, 9_303_000, 9_311_000, 9_312_000],
                "DEV/DEVVAL/DEV-NULL": [9_201_000, 9_202_000, 9_203_000, 9_211_000,
                                        9_212_000, 9_221_000, 9_231_000, 9_241_000],
            },
            "allowed": [list(r) for r in cfd.S1_ALLOWED_SEED_RANGES],
            "forbidden": [list(r) for r in cfd.S1_FORBIDDEN_SEED_RANGES],
        },
        "frozen_hyperparameters": {
            "learner": ("ratio learner, three heads, DQNNetwork (100, 50, 50) tanh, "
                        "113-dim observation, 28-action contract"),
            "deployed_score": "S = Q~_B - eta~ Q~_E, lambda = 0",
            "eta": "fixed at eta_0", "eta0_bit_per_J": ETA0_EXPECTED,
            "credit_mode": CREDIT_MODE,
            "teacher": "T0 = LP-prev(c = 1, m = 0), raw user state at collection time",
            "D3": {"margin": MARGIN0, "lambda_e": LAMBDA_E0},
            "D2": {"alpha": ALPHA0, "tau": D2_TAU, "tau_s": TAU_S0},
            "epsilon_decay_episodes": D.epsilon_decay_episodes(episodes),
            "t0_xep_reference_sha256": D.XEP_REFERENCE_SHA256,
        },
        "calibration_sha256": calibration_sha256,
        "prereg_digest": record.digest,
        "tle_file_set_sha256": TLE_FILE_SET_SHA256,
        "code": code, "code_digest": manifest_digest(code),
        "arm_configs": {key: config_hash(p) for key, p in arm_payloads.items()},
        "arm_payloads": arm_payloads,
        "reading_rules": {
            "Amendment 4": ("conjunctive gate against D3-null: rho >= 0.5 x R_repr, "
                            "2/3 seed direction, service / rate floor, matched null, "
                            "beyond seed noise -- continue-eligibility, not a claim"),
            "Amendment 12 section 3": ("rho_info decides the WORDING; only rho_info "
                                       "<= 0 triggers review"),
            "Amendment 12 section 4": ("D3-XEP must earn 'plausible': served >= 0.99 "
                                       "and EE >= 0.98 x EE(D0)"),
            "Amendment 13 section 2": ("MODQN @1000 is the same-budget win gate; the "
                                       "frozen 9000-episode checkpoint is a reference, "
                                       "not a veto"),
        },
    }


def assert_environment() -> str:
    return D.assert_environment()
