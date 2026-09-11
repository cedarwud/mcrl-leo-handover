"""CF3PILOT shared constants and policy builders (declaration + Amendment 1).

Seeds (declared in ``.scratch/cf3-pilot/DECLARATION-ADDENDUM.md`` before
launch).  Training triples: the frozen main-run triple plus two neighbours.
Calibration and evaluation use per-episode reseeding: episode i runs on a
FRESH environment with ``env_rng = default_rng(base_env + i)`` and
``mobility_rng = default_rng(base_mob + i)`` (CFSCREEN pairing fact), so every
arm meets every episode at the same start epoch and t=0 observation.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import numpy as np  # noqa: E402

from mcrl.algorithms import cf_sources as cfs  # noqa: E402
from mcrl.algorithms.cf_ratio import episode_seeds  # noqa: E402

TRAIN_SEEDS = ((42, 1337, 7), (43, 1338, 8), (44, 1339, 9))
CAL_ENV_BASE, CAL_MOB_BASE = 9_121_000, 9_122_000
EVAL_ENV_BASE, EVAL_MOB_BASE = 9_111_000, 9_112_000
RANDOM_ACTION_BASE = 9_131_000
N_CAL = 24
N_EVAL = 24
EPISODES = 1000
EPSILON_DECAY_COMPRESSED = round(2000 * EPISODES / 9000)   # 222
TRAINED_CKPT = REPO / "artifacts" / "training-2026-08-25-rerun01" / "main" / "final-checkpoint.pt"


def cal_seeds(n: int = N_CAL):
    return episode_seeds(CAL_ENV_BASE, CAL_MOB_BASE, n)


def eval_seeds(n: int = N_EVAL):
    return episode_seeds(EVAL_ENV_BASE, EVAL_MOB_BASE, n)


def env_factory(users: int = 100):
    from mcrl.runtime.training_pipeline import make_training_environment
    return lambda: make_training_environment(users=users)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload) -> None:
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str))
    tmp.replace(path)


# ---------------------------------------------------------------- policies
def masked_argmax(score: np.ndarray, masks) -> np.ndarray:
    """Row-wise masked argmax (first index on ties), NO generator."""
    from mcrl.env.action_contract import NO_OP_ACTION, no_op_actions
    out = no_op_actions(len(masks))
    for u in range(len(masks)):
        v = np.flatnonzero(masks[u].mask)
        if v.size:
            row = np.asarray(score[u], dtype=np.float64)
            out[u] = int(v[int(np.argmax(row[v]))])
        else:
            out[u] = NO_OP_ACTION
    return out


def modqn_greedy(trainer):
    """Deployed MODQN rule (scalarised Q, masked argmax) without the train RNG."""
    def pol(enc, masks, states):
        return masked_argmax(trainer.scalarized_q_values(enc), masks)
    return pol


def rule_policy(name: str):
    rules = dict(cfs.cf3_policies())
    rules["MAX_NOMINAL_GAIN"] = cfs.max_nominal_gain
    fn = rules[name]
    return lambda enc, masks, states: fn(states, masks)


def random_policy_factory(base: int = RANDOM_ACTION_BASE):
    """RANDOM_MASKED: uniform over legal actions, episode i on its own seed."""
    def factory(i):
        fn = cfs.random_legal(np.random.default_rng(base + i))
        return lambda enc, masks, states: fn(states, masks)
    return factory
