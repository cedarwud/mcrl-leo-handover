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

TRAIN_SEEDS = ((42, 1337, 7), (43, 1338, 8), (44, 1339, 9), (45, 1340, 10), (46, 1341, 11))
GATE_SEEDS = (0, 1, 2)          # the learning check is declared over A1 seeds 0-2
A0_SEEDS = (0, 1, 2)
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


_SHARED_ARCHIVE = None


def shared_archive():
    """ONE read-only ``TleArchive`` per process.

    ``TleArchive`` caches every parsed daily file without bound, per
    instance; ``make_training_environment`` builds a new instance per env, so
    a process holding four envs (main + three sources) plus per-episode
    calibration envs held up to four copies of the parse cache (A2 reached
    3.9 GB RSS by episode 100 of the diagnostic stage).  Parsed files are
    immutable (records are tuples), so sharing one instance changes no
    number -- ``tests/test_cf_ratio.py`` checks rollouts are bit-identical.
    """
    global _SHARED_ARCHIVE
    if _SHARED_ARCHIVE is None:
        from mcrl.env.tle import TleArchive
        from mcrl.runtime.training_pipeline import resolve_tle_root
        _SHARED_ARCHIVE = TleArchive(resolve_tle_root())
    return _SHARED_ARCHIVE


def env_factory(users: int = 100):
    from mcrl.algorithms.cf_ratio import make_env_on
    return lambda: make_env_on(shared_archive(), users)


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


# ---------------------------------------------------------------- manifest
MANIFEST_FILES = (
    "src/mcrl/algorithms/cf_ratio.py",
    "src/mcrl/algorithms/cf_sources.py",
    "src/mcrl/algorithms/modqn.py",
    "scripts/run_cf3_pilot.py",
    "scripts/cf3_common.py",
    "scripts/cf3_launch.py",
    "docs/cf3-pilot/V025-CONTROLLER-DECLARATION-THREE-CATFISH-PILOT-2026-09-11.md",
    "docs/cf3-pilot/V025-CONTROLLER-AMENDMENT-1-THREE-CATFISH-PILOT-2026-09-11.md",
    "docs/cf3-pilot/V025-CONTROLLER-AMENDMENT-2-EE-ONLY-2026-09-11.md",
)


def code_manifest() -> dict:
    """Code identity for fingerprints: commit, key-file hashes, whole-src hash.

    Launch and resume fail closed when this differs from the root's
    ``RUN-MANIFEST.json`` (coordinator review item 3).
    """
    commit_file = REPO / "COMMIT"
    commit = commit_file.read_text().strip() if commit_file.is_file() else "uncommitted-worktree"
    files = {f: sha256_file(REPO / f) for f in MANIFEST_FILES}
    h = hashlib.sha256()
    for p in sorted((REPO / "src").rglob("*.py")):
        h.update(str(p.relative_to(REPO)).encode())
        h.update(sha256_file(p).encode())
    return {"commit": commit, "files": files, "src_tree_sha256": h.hexdigest()}


def manifest_digest(code: dict) -> str:
    return hashlib.sha256(json.dumps(code, sort_keys=True).encode()).hexdigest()
