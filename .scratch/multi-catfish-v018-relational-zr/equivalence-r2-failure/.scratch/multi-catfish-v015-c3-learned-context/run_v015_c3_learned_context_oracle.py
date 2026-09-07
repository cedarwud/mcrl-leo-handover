#!/usr/bin/env python3
"""V0.15 learned-context C3 development oracle.

This runner answers one bounded question:

    Does the exact current-slot ZR C3 teacher improve canonical trajectory
    ratio-of-sums EE when the *background policy* is Q1 plus a frozen learned
    V0.14 Q2 head?

The V0.14 Q2 checkpoint is used only through its deployable 448-dimensional
state.  The exact OPS3 surface is a state-input adapter; its ``q2_values``
are never an action surface.  The two arms use one common keyed-fading field
per world and one fresh environment per arm.  There is no learner update,
episode training, TEST split, coordinator, or post-action override.

The module intentionally has no import-time execution.  ``shard`` evaluates
one (world, arm, lineage) tuple.  ``merge`` checks the rectangular paired
closure and reports the pooled/per-world/per-lineage EE contrast.  Small
world/lineage lists are accepted so a server controller can start with a
single-world smoke and expand to the four-world development panel without
changing the mechanics.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time
from typing import Any

import numpy as np
import torch


REPO = Path(__file__).resolve().parents[2]
V013_RUNNER_PATH = (
    REPO / ".scratch" / "zero-energy-c3-v013" / "run_v013_zero_energy_c3_oracle.py"
)
_V013_SPEC = importlib.util.spec_from_file_location(
    "mcrl_v013_helpers_for_v015_learned_context", V013_RUNNER_PATH
)
if _V013_SPEC is None or _V013_SPEC.loader is None:
    raise RuntimeError(f"cannot import V0.13 helper runner: {V013_RUNNER_PATH}")
_V013 = importlib.util.module_from_spec(_V013_SPEC)
sys.modules[_V013_SPEC.name] = _V013
_V013_SPEC.loader.exec_module(_V013)

for _path in (REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.algorithms.ee_axis_v014_head import (  # noqa: E402
    EEAxisV014HeadConfig,
    V014ActionSetQNetwork,
    V014_HEAD_ALGORITHM,
    V014_HEAD_CHECKPOINT_VERSION,
)
from mcrl.env.action_contract import NUM_ACTIONS  # noqa: E402
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_ops3 import OPS3_KAPPA_BITS  # noqa: E402
from mcrl.runtime.ee_axis_v014_q2_state import (  # noqa: E402
    V014_Q2_STATE_DIM,
    V014_Q2_STATE_SCHEMA,
    encode_ee_axis_v014_q2_states,
)
from mcrl.runtime.ee_axis_state import encode_ee_axis_state  # noqa: E402
from mcrl.runtime.ee_axis_ops3_live import (  # noqa: E402
    build_ops3_live_surfaces,
    project_ops3_anchor,
    snapshot_ops3_anchor,
)
from mcrl.runtime.ee_axis_zero_marginal_c3_live import (  # noqa: E402
    measure_zero_marginal_c3,
    physics_signature,
)


RESULT_SCHEMA = "multi-catfish-mcrl-v015-c3-learned-context-oracle-result-v1"
SHARD_SCHEMA = "multi-catfish-mcrl-v015-c3-learned-context-oracle-shard-v1"
EPISODE_SCHEMA = "multi-catfish-mcrl-v015-c3-learned-context-episode-v1"
CONTRACT_SCHEMA = "multi-catfish-mcrl-v015-c3-learned-context-contract-v1"
RESULT_SEAL_SCHEMA = "multi-catfish-mcrl-v015-c3-learned-context-result-seal-v1"

WORLD_SEEDS = (2026105001, 2026105002, 2026105003, 2026105004)
LINEAGES = (2026092101, 2026092102, 2026092103)
ARMS = ("DROP_C3", "FULL_ZR")
USERS = 100
STEPS_PER_EPISODE = 10
FIELD_COMPONENT = "MCRL_V015_ZR_C3_LEARNED_CONTEXT_ORACLE_V1"

V03_ROOT = (
    REPO / "artifacts" / "multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1"
)
V014_GATE_ROOT = (
    REPO
    / "artifacts"
    / "multi-catfish-v014-learnability-20260903-r1"
    / "server-run"
    / "learner-gate"
)
V015_CONTRACT_PATH = (
    REPO
    / "artifacts"
    / "multi-catfish-v015-c3-learned-context-oracle-20260903-r1"
    / "contracts"
    / "MULTI-CATFISH-MCRL-V015-C3-LEARNED-CONTEXT-ORACLE-PREREG-2026-09-03.md"
)
# The frozen V0.15 document is the protocol contract.  The simulator's TLE
# rows still come from the already-frozen base JSON preregistration; the two
# boundaries must not be conflated.
V015_CONTRACT_SHA256 = (
    "006387d39376d93f6a9ad7515bb428320ac189843f0cb360c2609b3dd177355d"
)
DEFAULT_PREREG = REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json"
DEFAULT_TLE_ROOT = Path("~/demo/tle_data/starlink/tle").expanduser()
DEFAULT_OUTPUT_ROOT = REPO / ".scratch" / "multi-catfish-v015-c3-learned-context"

Q2_INIT_BY_LINEAGE = {
    2026092101: 2026108101,
    2026092102: 2026108102,
    2026092103: 2026108103,
}
Q2_CHECKPOINT_SHA256 = {
    2026108101: (
        "d981232a9e56e6ce71c8e8b1fda789efc69852d4a6a22e918a2992ddc58a533d"
    ),
    2026108102: (
        "9a45f5bc125d6ba453d7d74dbc640ec3d2e927fffb161518e383e6b3aabbe8ef"
    ),
    2026108103: (
        "8f9d2e5d1749515a0896137082b1430419ae1b8a794d28ea772a23c86648be81"
    ),
}
V014_RESULT_SHA256 = (
    "289949275e9241cc5b885b1fc588a69e97446f755d9cf4f3ccfe9542f03f6c7c"
)
V014_AUTHORITY_SHA256 = (
    "9de934468e79abe2ad6854b4f617fcb9521109e4d2bff6c7225962daef0877f4"
)
V014_RESULT_SEAL_SHA256 = (
    "b9f9bb231c8df2b1d8a61d02d7e274fb484fac1f5d39626908941e8f958868dd"
)

V03_AUTHORITY_SHA256 = _V013.old_gate.EXPECTED_V03_AUTHORITY_SHA256
V03_RESULT_SHA256 = _V013.old_gate.EXPECTED_V03_RESULT_FILE_SHA256
V03_RESULT_SEAL_SHA256 = _V013.old_gate.EXPECTED_V03_RESULT_SEAL_FILE_SHA256
V03_CHECKPOINT_SHA256 = dict(_V013.old_gate.EXPECTED_V03_CHECKPOINT_SHA256)


class V015OracleError(RuntimeError):
    """A V0.15 checkpoint, source, physics, pairing, or receipt boundary failed."""


def _canonical_default(value: object) -> bool | int | float:
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("non-finite NumPy scalar")
        return result
    raise TypeError(f"unsupported canonical JSON value: {type(value).__name__}")


def _canonical_bytes(payload: object) -> bytes:
    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
            default=_canonical_default,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V015OracleError("payload is not finite canonical JSON") from error


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def file_sha256(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V015OracleError(f"expected a regular file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def array_sha256(*values: object) -> str:
    digest = hashlib.sha256()
    for value in values:
        array = np.ascontiguousarray(np.asarray(value))
        digest.update(array.dtype.str.encode("ascii"))
        digest.update(repr(tuple(array.shape)).encode("ascii"))
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V015OracleError(f"missing JSON receipt: {source}")
    try:
        payload = json.loads(source.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise V015OracleError(f"invalid JSON receipt: {source}") from error
    if not isinstance(payload, dict):
        raise V015OracleError(f"JSON receipt is not an object: {source}")
    return payload


def validate_v015_contract(path: Path = V015_CONTRACT_PATH) -> None:
    """Require the immutable V0.15 contract before any simulator access."""

    source = Path(path)
    if file_sha256(source) != V015_CONTRACT_SHA256:
        raise V015OracleError("V0.15 contract bytes do not match the frozen prereg")
    text = source.read_text(encoding="utf-8")
    if "Status: `FROZEN_BEFORE_OUTCOME`" not in text:
        raise V015OracleError("V0.15 contract is not frozen before outcome access")
    for phrase in (
        "Q1 + Q2",
        "DROP_C3",
        "FULL_ZR",
        "exact OPS3 projection may be constructed only to",
        "TEST` split remains unopened",
    ):
        if phrase not in text:
            raise V015OracleError(f"V0.15 contract is missing required binding: {phrase}")


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V015OracleError(f"{field} is not a lowercase SHA-256 digest")
    return value


def _q_parameter_sha256(network: Any) -> str:
    digest = hashlib.sha256()
    for name, value in network.state_dict().items():
        tensor = value.detach().cpu()
        digest.update(str(name).encode("utf-8"))
        digest.update(str(tensor.dtype).encode("ascii"))
        digest.update(repr(tuple(tensor.shape)).encode("ascii"))
        digest.update(tensor.numpy().tobytes(order="C"))
    return digest.hexdigest()


def _q2_config_from_checkpoint(value: Mapping[str, Any]) -> EEAxisV014HeadConfig:
    config = value.get("config")
    if not isinstance(config, Mapping):
        raise V015OracleError("Q2 checkpoint config is missing")
    try:
        result = EEAxisV014HeadConfig(
            action_dim=int(config["action_dim"]),
            local_feature_dim=int(config["local_feature_dim"]),
            global_feature_dim=int(config["global_feature_dim"]),
            hidden_layers=tuple(int(item) for item in config["hidden_layers"]),
            activation=str(config["activation"]),
            learning_rate=float(config["learning_rate"]),
            kappa_bits=float(config["kappa_bits"]),
            beta=float(config["beta"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise V015OracleError("Q2 checkpoint config is malformed") from error
    if config != {
        "action_dim": result.action_dim,
        "local_feature_dim": result.local_feature_dim,
        "global_feature_dim": result.global_feature_dim,
        "hidden_layers": result.hidden_layers,
        "activation": result.activation,
        "learning_rate": result.learning_rate,
        "kappa_bits": result.kappa_bits,
        "beta": result.beta,
    }:
        raise V015OracleError("Q2 checkpoint config contains a noncanonical value")
    expected = EEAxisV014HeadConfig(
        action_dim=NUM_ACTIONS,
        local_feature_dim=16,
        global_feature_dim=0,
        hidden_layers=(100, 50, 50),
        activation="tanh",
        learning_rate=0.001,
        kappa_bits=float(OPS3_KAPPA_BITS),
        beta=0.1,
    )
    if result != expected:
        raise V015OracleError("Q2 checkpoint config is not the frozen V0.14 config")
    if result.state_dim != V014_Q2_STATE_DIM:
        raise V015OracleError("Q2 config state dimension disagrees with V0.14")
    return result


def validate_v014_gate_receipts(q2_root: Path = V014_GATE_ROOT) -> dict[str, Any]:
    """Authenticate the immutable V0.14 gate receipt before loading Q2."""

    root = Path(q2_root)
    result_path = root / "result.json"
    authority_path = root / "authority.json"
    seal_path = root / "result-seal.json"
    for path, expected in (
        (result_path, V014_RESULT_SHA256),
        (authority_path, V014_AUTHORITY_SHA256),
        (seal_path, V014_RESULT_SEAL_SHA256),
    ):
        if file_sha256(path) != expected:
            raise V015OracleError(f"V0.14 gate receipt hash drifted: {path.name}")
    result = _read_json(result_path)
    authority = _read_json(authority_path)
    seal = _read_json(seal_path)
    if result.get("schema") != "multi-catfish-mcrl-v014-supervised-learnability-result-v1":
        raise V015OracleError("V0.14 result schema is stale")
    if result.get("status") != "STOP_LEARNABILITY_GATE":
        raise V015OracleError("unexpected V0.14 gate status")
    if result.get("test_split_opened") is not False or result.get("held_out_ee_evaluated") is not False:
        raise V015OracleError("V0.14 gate crossed a forbidden boundary")
    if authority.get("authority_sha256") != result.get("authority_sha256"):
        raise V015OracleError("V0.14 authority/result digest mismatch")
    if seal.get("result_file_sha256") != V014_RESULT_SHA256:
        raise V015OracleError("V0.14 result seal does not bind result bytes")
    checkpoint_receipts = result.get("checkpoint_file_sha256s")
    if not isinstance(checkpoint_receipts, Mapping):
        raise V015OracleError("V0.14 result lacks checkpoint digest map")
    for lineage, init_seed in Q2_INIT_BY_LINEAGE.items():
        digest = checkpoint_receipts.get(str(init_seed), {})
        if not isinstance(digest, Mapping) or digest.get("3000") != Q2_CHECKPOINT_SHA256[init_seed]:
            raise V015OracleError(f"V0.14 result checkpoint map disagrees for {init_seed}")
    return {
        "result_file_sha256": V014_RESULT_SHA256,
        "authority_file_sha256": V014_AUTHORITY_SHA256,
        "result_seal_file_sha256": V014_RESULT_SEAL_SHA256,
        "result_authority_sha256": result.get("authority_sha256"),
        "result_run_spec_sha256": result.get("run_spec_sha256"),
        "result_schema": result.get("schema"),
        "claim_ceiling": result.get("claim_ceiling"),
    }


def load_frozen_q2(
    q2_root: Path = V014_GATE_ROOT,
    *,
    lineage: int,
    gate_receipt: Mapping[str, Any] | None = None,
) -> tuple[V014ActionSetQNetwork, dict[str, Any]]:
    """Load the exact V0.14 rung-3000 Q2 checkpoint for one Q1 lineage."""

    lineage = int(lineage)
    if lineage not in Q2_INIT_BY_LINEAGE:
        raise V015OracleError(f"lineage is outside the three frozen Q2 lineages: {lineage}")
    init_seed = Q2_INIT_BY_LINEAGE[lineage]
    root = Path(q2_root)
    if gate_receipt is None:
        gate_receipt = validate_v014_gate_receipts(root)
    path = root / "checkpoints" / f"init-{init_seed}-rung-003000.pt"
    actual = file_sha256(path)
    expected = Q2_CHECKPOINT_SHA256[init_seed]
    if actual != expected:
        raise V015OracleError(f"frozen Q2 checkpoint hash mismatch for {init_seed}")
    try:
        payload = torch.load(path, map_location="cpu", weights_only=False)
    except Exception as error:
        raise V015OracleError(f"cannot load frozen Q2 checkpoint: {path}") from error
    if not isinstance(payload, Mapping):
        raise V015OracleError("Q2 checkpoint root is not a mapping")
    for field, expected_value in (
        ("schema", "multi-catfish-mcrl-v014-supervised-learnability-checkpoint-v1"),
        ("runner_schema", "multi-catfish-mcrl-v014-supervised-learnability-gate-v1"),
        ("initialization_seed", init_seed),
        ("update_rung", 3000),
        ("test_split_opened", False),
        ("held_out_ee_evaluated", False),
        ("episode_training", False),
    ):
        if payload.get(field) != expected_value:
            raise V015OracleError(f"Q2 checkpoint metadata mismatch: {field}")
    q2_payload = payload.get("q2")
    q3_payload = payload.get("q3")
    if not isinstance(q2_payload, Mapping) or not isinstance(q3_payload, Mapping):
        raise V015OracleError("V0.14 checkpoint must contain both independent heads")
    if set(q2_payload) != {"algorithm", "format_version", "config", "train_seed", "update_count", "q", "optimizer"}:
        raise V015OracleError("Q2 nested checkpoint fields are noncanonical")
    config = _q2_config_from_checkpoint(q2_payload)
    if q2_payload.get("algorithm") != V014_HEAD_ALGORITHM:
        raise V015OracleError("Q2 nested algorithm is stale")
    if q2_payload.get("format_version") != V014_HEAD_CHECKPOINT_VERSION:
        raise V015OracleError("Q2 nested checkpoint format is stale")
    if q2_payload.get("train_seed") != init_seed or q2_payload.get("update_count") != 3000:
        raise V015OracleError("Q2 nested lineage/rung mismatch")
    if not isinstance(q2_payload.get("q"), Mapping) or not isinstance(q2_payload.get("optimizer"), Mapping):
        raise V015OracleError("Q2 nested model/optimizer payload is malformed")
    network = V014ActionSetQNetwork(config).to(torch.device("cpu"))
    try:
        network.load_state_dict(q2_payload["q"], strict=True)
    except (RuntimeError, TypeError, ValueError) as error:
        raise V015OracleError("Q2 nested model does not match its config") from error
    network.eval()
    network.requires_grad_(False)
    if any(parameter.requires_grad for parameter in network.parameters()):
        raise V015OracleError("frozen Q2 still has trainable parameters")
    parameter_sha = _q_parameter_sha256(network)
    receipt = {
        "checkpoint_path": str(path.resolve()),
        "checkpoint_sha256": actual,
        "parameter_sha256": parameter_sha,
        "gate_result_file_sha256": gate_receipt["result_file_sha256"],
        "gate_authority_file_sha256": gate_receipt["authority_file_sha256"],
        "gate_result_authority_sha256": gate_receipt["result_authority_sha256"],
        "initialization_seed": init_seed,
        "source_lineage": lineage,
        "rung": 3000,
        "state_schema": V014_Q2_STATE_SCHEMA,
        "state_dim": V014_Q2_STATE_DIM,
        "config": {
            "action_dim": config.action_dim,
            "local_feature_dim": config.local_feature_dim,
            "global_feature_dim": config.global_feature_dim,
            "hidden_layers": list(config.hidden_layers),
            "activation": config.activation,
            "learning_rate": config.learning_rate,
            "kappa_bits": config.kappa_bits,
            "beta": config.beta,
        },
    }
    return network, receipt


def load_frozen_q1(v03_root: Path, lineage: int) -> tuple[Any, dict[str, Any]]:
    """Load V0.3 head-0 and authenticate its known rung-10 bytes."""

    lineage = int(lineage)
    if lineage not in LINEAGES:
        raise V015OracleError(f"lineage is outside the three frozen Q1 lineages: {lineage}")
    path = Path(v03_root) / "checkpoints" / f"init-{lineage}-rung-000010.pt"
    actual = file_sha256(path)
    if actual != V03_CHECKPOINT_SHA256[lineage]:
        raise V015OracleError(f"frozen Q1 checkpoint hash mismatch for {lineage}")
    for name, expected in (
        ("authority.json", V03_AUTHORITY_SHA256),
        ("result.json", V03_RESULT_SHA256),
        ("result-seal.json", V03_RESULT_SEAL_SHA256),
    ):
        if file_sha256(Path(v03_root) / name) != expected:
            raise V015OracleError(f"frozen V0.3 receipt hash mismatch: {name}")
    try:
        network, receipt = _V013.load_frozen_q1(Path(v03_root), lineage)
    except Exception as error:
        raise V015OracleError(f"cannot load frozen Q1 for {lineage}") from error
    payload = dict(receipt)
    if payload.get("checkpoint_sha256") != actual:
        raise V015OracleError("loaded Q1 receipt disagrees with checkpoint bytes")
    payload["v03_authority_file_sha256"] = V03_AUTHORITY_SHA256
    payload["v03_result_file_sha256"] = V03_RESULT_SHA256
    payload["v03_result_seal_file_sha256"] = V03_RESULT_SEAL_SHA256
    return network, payload


def field_for_world(world_seed: int) -> KeyedFadingField:
    if isinstance(world_seed, bool) or not isinstance(world_seed, (int, np.integer)):
        raise V015OracleError("world seed must be an integer")
    return KeyedFadingField.from_components(FIELD_COMPONENT, int(world_seed))


def contract_receipt(
    *,
    worlds: Sequence[int] = WORLD_SEEDS,
    lineages: Sequence[int] = LINEAGES,
) -> dict[str, Any]:
    worlds_tuple = tuple(int(value) for value in worlds)
    lineages_tuple = tuple(int(value) for value in lineages)
    if not worlds_tuple or not lineages_tuple:
        raise V015OracleError("contract world/lineage lists must be nonempty")
    if any(value not in LINEAGES for value in lineages_tuple):
        raise V015OracleError("contract lineage list contains an unfrozen Q1/Q2 lineage")
    return {
        "schema": CONTRACT_SCHEMA,
        "world_seeds": list(worlds_tuple),
        "lineages": list(lineages_tuple),
        "arms": list(ARMS),
        "users": USERS,
        "steps_per_episode": STEPS_PER_EPISODE,
        "episodes": len(worlds_tuple) * len(lineages_tuple) * len(ARMS),
        "split": "TRAIN",
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "q1_policy": "frozen_v03_head_0_rung_10",
        "q2_policy": "frozen_v014_head_q2_rung_3000",
        "background_policy": "Q1_PLUS_LEARNED_Q2",
        "full_policy": "Q1_PLUS_LEARNED_Q2_PLUS_EXACT_ZR_C3",
        "exact_ops3_role": "Q2_STATE_INPUT_ONLY",
        "c3_formula": "UNCHANGED_ZR",
        "selection": "one_common_mask_one_masked_argmax_one_action",
        "field_component": FIELD_COMPONENT,
        "v015_contract_file_sha256": V015_CONTRACT_SHA256,
        "field_excludes": ["arm", "lineage", "policy", "action", "target", "outcome"],
        "checkpoint_rung": {"q1": 10, "q2": 3000},
        "q2_init_by_lineage": {str(key): value for key, value in Q2_INIT_BY_LINEAGE.items()},
        "q2_checkpoint_sha256": {str(key): value for key, value in Q2_CHECKPOINT_SHA256.items()},
        "gate": {
            "pooled_ee_strictly_above_drop_c3": True,
            "positive_worlds_minimum": min(3, len(worlds_tuple)),
            "positive_lineages_minimum": min(2, len(lineages_tuple)),
            "service_noninferior_pooled": True,
            "current_slot_joint_support": True,
        },
        "claim_ceiling": "TRAIN_DEVELOPMENT_ORACLE_NO_LEARNER_NO_TEST_NO_EFFICACY_CLAIM",
    }


def _q1_values(network: Any, states: np.ndarray, masks: np.ndarray) -> np.ndarray:
    values = network(
        torch.tensor(np.asarray(states, dtype=np.float32)),
        torch.tensor(np.asarray(masks, dtype=np.bool_), dtype=torch.bool),
    ).detach().cpu().numpy()
    result = np.asarray(values, dtype=np.float64)
    if result.shape != masks.shape or not np.all(np.isfinite(result)):
        raise V015OracleError("Q1 surface is malformed")
    return result


def _q2_values(network: V014ActionSetQNetwork, states: np.ndarray, masks: np.ndarray) -> np.ndarray:
    values = network(
        torch.tensor(np.asarray(states, dtype=np.float32)),
        torch.tensor(np.asarray(masks, dtype=np.bool_), dtype=torch.bool),
    ).detach().cpu().numpy()
    result = np.asarray(values, dtype=np.float64)
    if result.shape != masks.shape or not np.all(np.isfinite(result)):
        raise V015OracleError("learned Q2 surface is malformed")
    return result


def select_actions(
    q1: np.ndarray,
    learned_q2: np.ndarray,
    c3: np.ndarray,
    mask: np.ndarray,
    *,
    include_c3: bool,
) -> np.ndarray:
    legal = np.asarray(mask)
    if legal.dtype != np.bool_ or legal.ndim != 2 or legal.shape[1] != NUM_ACTIONS:
        raise V015OracleError("safe mask is not a Boolean native-action matrix")
    arrays = tuple(np.asarray(value, dtype=np.float64) for value in (q1, learned_q2, c3))
    if any(value.shape != legal.shape or not np.all(np.isfinite(value)) for value in arrays):
        raise V015OracleError("Q1/Q2/C3 surfaces are malformed")
    if not np.all(np.any(legal, axis=1)):
        raise V015OracleError("every user must have a legal native action")
    scores = arrays[0] + arrays[1]
    if include_c3:
        scores = scores + arrays[2]
    return np.argmax(np.where(legal, scores, -np.inf), axis=1).astype(np.int64)


def _live_digest(environment: Any, rng: np.random.Generator) -> str:
    return _V013._live_digest(environment, rng)


def _initial_world_sha(environment: Any, observation: Any) -> str:
    return _V013._initial_world_sha(environment, observation)


def _joint_support_receipt(
    step_env: Any,
    rng: np.random.Generator,
    reference: np.ndarray,
    selected: np.ndarray,
    interval_s: float,
) -> dict[str, Any]:
    """Use V0.13's exact current-slot support check for the new policy."""

    return _V013._joint_support_receipt(
        step_env, rng, reference, selected, interval_s
    )


def _build_c3_surfaces(measurements: Any, interval_s: float) -> tuple[np.ndarray, dict[str, Any]]:
    """Build the unchanged ZR surface; exact OPS3 is not consulted here."""

    return _V013._build_c3_surfaces(
        formula="ZR", measurements=measurements, interval_s=interval_s
    )


def evaluate_episode(
    *,
    q1: Any,
    q1_receipt: Mapping[str, Any],
    q2: V014ActionSetQNetwork,
    q2_receipt: Mapping[str, Any],
    archive: Any,
    world_seed: int,
    field: KeyedFadingField,
    lineage: int,
    arm: str,
) -> dict[str, Any]:
    """Evaluate one ten-step paired arm using learned Q2 as the background."""

    if arm not in ARMS:
        raise V015OracleError(f"unknown arm: {arm}")
    if int(lineage) not in LINEAGES:
        raise V015OracleError("lineage is outside the frozen Q1/Q2 set")
    environment = _V013.screen._make_environment(archive, users=USERS)
    environment.environment._fading_field = field
    env_rng, mobility_rng, _action_rng, _control_rng = _V013.screen._evaluation_rngs(
        int(world_seed)
    )
    _states, _masks, observation = environment.reset(env_rng, mobility_rng)
    step_env = environment.environment
    interval_s = float(step_env.driver.config.ephemeris.time_step_s)
    initial_world = _initial_world_sha(environment, observation)
    q1_before = _q_parameter_sha256(q1)
    q2_before = _q_parameter_sha256(q2)
    started = time.perf_counter()

    total_bits = 0.0
    total_energy = 0.0
    served_steps = 0
    active_beam_steps = 0
    active_satellite_steps = 0
    c3_spread = 0
    positive_targets = 0
    supported_positive_targets = 0
    compatible_action_count = 0
    action_exposure = 0
    changed_actions_compatible = True
    joint_support_passed = True
    method_passed = True
    per_step: list[dict[str, Any]] = []

    with torch.no_grad():
        for step_index in range(STEPS_PER_EPISODE):
            native = encode_ee_axis_state(step_env, observation)
            mask = np.asarray(native.action_masks, dtype=np.bool_)
            q1_values = _q1_values(q1, native.state_matrix, mask)
            zero = np.zeros_like(q1_values)
            q1_reference = select_actions(q1_values, zero, zero, mask, include_c3=False)

            # The exact OPS3 surface is intentionally used only as a feature
            # carrier for the learned Q2 state.  Its teacher q2_values are
            # never read or added to the action score.
            before = _live_digest(environment, env_rng)
            anchor = snapshot_ops3_anchor(step_env, observation)
            projection = project_ops3_anchor(anchor)
            ops3_state_input = build_ops3_live_surfaces(anchor, projection, q1_reference)
            q2_state = encode_ee_axis_v014_q2_states(ops3_state_input)
            q2_state.verify()
            if not np.array_equal(q2_state.action_masks, mask):
                raise V015OracleError("Q2 state mask differs from the common deployment mask")
            learned_q2 = _q2_values(q2, q2_state.state_matrix, q2_state.action_masks)
            background = select_actions(q1_values, learned_q2, zero, mask, include_c3=False)
            selected = np.array(background, dtype=np.int64, copy=True)
            o3 = np.zeros_like(q1_values)
            method: dict[str, Any] = {
                "kind": "DROP_C3",
                "formula": None,
                "identity_passed": True,
                "positive_target_count": 0,
                "supported_positive_target_count": 0,
                "compatibility_component_counts": {
                    name: 0
                    for name in ("served", "active_beams", "active_satellites", "rf_power", "network_power", "all")
                },
            }
            measurements = None
            if arm == "FULL_ZR":
                measurements = measure_zero_marginal_c3(
                    step_env,
                    observation=observation,
                    reference_actions=background,
                    rng=env_rng,
                    include_insertion=False,
                    interval_s=interval_s,
                )
                o3, method = _build_c3_surfaces(measurements, interval_s)
                selected = select_actions(q1_values, learned_q2, o3, mask, include_c3=True)

            reference_zero = all(
                float(o3[uid, int(background[uid])]) == 0.0
                for uid in range(USERS)
            )
            illegal_zero = bool(np.all(o3[~mask] == 0.0))

            # The probe above must be read-only.  Counterfactual C3 creation is
            # allowed to consume the local evaluation RNG only through its
            # own keyed physical evaluations; the environment itself is still
            # unchanged before the selected action is committed.
            after = _live_digest(environment, env_rng)
            changed = np.flatnonzero(selected != background)
            step_changed_compatible = True
            changed_positive = True
            if measurements is not None:
                for uid_raw in changed.tolist():
                    uid = int(uid_raw)
                    action = int(selected[uid])
                    step_changed_compatible = step_changed_compatible and bool(measurements.compatible[uid, action])
                    changed_positive = changed_positive and bool(o3[uid, action] > 0.0)
            elif changed.size:
                raise V015OracleError("DROP_C3 changed from its own learned Q1+Q2 background")
            if not step_changed_compatible or not changed_positive:
                raise V015OracleError("a changed action lacks positive compatible ZR credit")

            base_evaluation = step_env.evaluate_actions(background, env_rng)
            opening_equal = all(
                bool(ops3_state_input[uid].opening_service_feasible[int(background[uid])])
                == bool(base_evaluation.resolution.served[uid])
                for uid in range(USERS)
            )
            joint_support = _joint_support_receipt(step_env, env_rng, background, selected, interval_s)
            mechanics = {
                "live_state_and_rng_unchanged": before == after,
                "common_mask": np.array_equal(q2_state.action_masks, mask),
                "reference_rows_exact_zero": reference_zero,
                "illegal_rows_exact_zero": illegal_zero,
                "opening_service_gate_equal": opening_equal,
                "learned_q2_surface_finite": bool(np.all(np.isfinite(learned_q2))),
                "q2_state_schema": q2_state.schema == V014_Q2_STATE_SCHEMA,
                "changed_actions_compatible": step_changed_compatible,
                "changed_actions_strictly_positive_c3": changed_positive,
                "joint_support_passed": bool(joint_support["passed"]),
                "background_sha256": array_sha256(background),
            }
            mechanics["passed"] = bool(
                all(
                    value
                    for key, value in mechanics.items()
                    if key not in {"background_sha256", "joint_support_passed", "passed"}
                )
            )
            if not mechanics["passed"]:
                raise V015OracleError("binding per-step mechanics failed")

            flips = int(changed.size)
            step_spread = int(sum(np.ptp(o3[uid, np.flatnonzero(mask[uid])]) > 0.0 for uid in range(mask.shape[0])))
            action_exposure += flips
            c3_spread += step_spread
            positive_targets += int(method["positive_target_count"])
            supported_positive_targets += int(method["supported_positive_target_count"])
            compatible_action_count += int(method["compatibility_component_counts"]["all"])
            changed_actions_compatible = changed_actions_compatible and step_changed_compatible
            joint_support_passed = joint_support_passed and bool(joint_support["passed"])
            method_passed = method_passed and bool(method["identity_passed"])

            result = environment.step(selected, env_rng)
            outcome = environment.last_outcome
            rates = np.asarray(outcome.link_rate_bps, dtype=np.float64)
            power = float(outcome.system_power_w)
            if (
                rates.shape != (USERS,)
                or not np.all(np.isfinite(rates))
                or np.any(rates < 0.0)
                or not math.isfinite(power)
                or power <= 0.0
            ):
                raise V015OracleError("canonical EE inputs are malformed")
            bits = interval_s * math.fsum(float(value) for value in rates)
            energy = interval_s * power
            total_bits += bits
            total_energy += energy
            served_steps += int(outcome.resolution.served_count)
            active_beam_steps += int(outcome.radiating.count)
            active_satellite_steps += len({int(value) for value in outcome.radiating.norad_ids.tolist()})
            per_step.append(
                {
                    "step_index": step_index,
                    "total_bits": float(bits),
                    "total_energy_j": float(energy),
                    "served_user_steps": int(outcome.resolution.served_count),
                    "active_beam_count": int(outcome.radiating.count),
                    "active_satellite_count": len({int(value) for value in outcome.radiating.norad_ids.tolist()}),
                    "action_exposure": flips,
                    "c3_legal_spread_count": step_spread,
                    "selected_actions": [int(value) for value in selected.tolist()],
                    "surface_sha256": {
                        "q1": array_sha256(q1_values),
                        "q2_learned": array_sha256(learned_q2),
                        "q2_state": q2_state.state_sha256,
                        "q2_state_mask": array_sha256(q2_state.action_masks),
                        "q3_zr": array_sha256(o3),
                        "mask": array_sha256(mask),
                        "q1_reference": array_sha256(q1_reference),
                        "background": array_sha256(background),
                    },
                    "mechanics": mechanics,
                    "method": method,
                    "joint_support": joint_support,
                }
            )
            if result.done:
                if step_index != STEPS_PER_EPISODE - 1:
                    raise V015OracleError("episode terminated before ten steps")
                break
            observation = outcome.observation

    q1_after = _q_parameter_sha256(q1)
    q2_after = _q_parameter_sha256(q2)
    if q1_before != q1_after:
        raise V015OracleError("frozen Q1 changed during oracle episode")
    if q2_before != q2_after:
        raise V015OracleError("frozen learned Q2 changed during oracle episode")
    return {
        "schema": EPISODE_SCHEMA,
        "arm": arm,
        "initialization_seed": int(lineage),
        "world_seed": int(world_seed),
        "split": "TRAIN",
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "users": USERS,
        "steps": STEPS_PER_EPISODE,
        "initial_world_sha256": initial_world,
        "field_root_digest": field.root_digest,
        "q1_checkpoint": dict(q1_receipt),
        "q2_checkpoint": dict(q2_receipt),
        "q1_parameter_sha256_before": q1_before,
        "q1_parameter_sha256_after": q1_after,
        "q2_parameter_sha256_before": q2_before,
        "q2_parameter_sha256_after": q2_after,
        "total_bits": float(total_bits),
        "total_energy_j": float(total_energy),
        "ratio_of_sums_ee_bits_per_j": float(total_bits / total_energy),
        "served_user_steps": served_steps,
        "served_fraction": served_steps / (USERS * STEPS_PER_EPISODE),
        "active_beam_steps": active_beam_steps,
        "active_satellite_steps": active_satellite_steps,
        "c3_legal_spread_count": c3_spread,
        "positive_target_count": positive_targets,
        "supported_positive_target_count": supported_positive_targets,
        "compatible_action_count": compatible_action_count,
        "action_exposure": action_exposure,
        "changed_actions_compatible": changed_actions_compatible,
        "joint_support_passed": joint_support_passed,
        "method_passed": method_passed,
        "candidate_specific_identity_passed": method_passed,
        "mechanics_passed": all(step["mechanics"]["passed"] for step in per_step),
        "per_step": per_step,
        "elapsed_s": time.perf_counter() - started,
    }


def run_shard(
    *,
    world_seed: int,
    arm: str,
    lineage: int,
    output_dir: Path,
    q2_root: Path = V014_GATE_ROOT,
    v03_root: Path = V03_ROOT,
    prereg_path: Path = DEFAULT_PREREG,
    tle_root: Path = DEFAULT_TLE_ROOT,
) -> dict[str, Any]:
    output = Path(output_dir)
    if output.exists() or output.is_symlink():
        raise V015OracleError(f"refusing to overwrite shard output: {output}")
    if int(world_seed) <= 0 or int(lineage) not in LINEAGES or arm not in ARMS:
        raise V015OracleError("world, lineage, or arm is outside the V0.15 declaration")
    validate_v015_contract()
    gate_receipt = validate_v014_gate_receipts(q2_root)
    q1, q1_receipt = load_frozen_q1(v03_root, lineage)
    q2, q2_receipt = load_frozen_q2(q2_root, lineage=lineage, gate_receipt=gate_receipt)
    record = _V013.read_prereg(prereg_path)
    field = field_for_world(int(world_seed))
    with tempfile.TemporaryDirectory(prefix="mcrl-v015-learned-context-tle-") as temporary:
        archive = _V013.screen._frozen_archive(record, Path(tle_root), Path(temporary) / "frozen-tle")
        row = evaluate_episode(
            q1=q1,
            q1_receipt=q1_receipt,
            q2=q2,
            q2_receipt=q2_receipt,
            archive=archive,
            world_seed=int(world_seed),
            field=field,
            lineage=int(lineage),
            arm=arm,
        )
    contract = contract_receipt(worlds=(int(world_seed),), lineages=(int(lineage),))
    payload = {
        "schema": SHARD_SCHEMA,
        "shard_id": f"{int(world_seed)}-{arm}-{int(lineage)}",
        "contract": contract,
        "contract_sha256": canonical_sha256(contract),
        "runner_file_sha256": file_sha256(Path(__file__).resolve()),
        "prereg_file_sha256": file_sha256(Path(prereg_path)),
        "q1_checkpoint_sha256": q1_receipt["checkpoint_sha256"],
        "q2_checkpoint_sha256": q2_receipt["checkpoint_sha256"],
        "q2_gate_receipt": dict(gate_receipt),
        "row": row,
    }
    payload["row_sha256"] = canonical_sha256(row)
    output.mkdir(parents=True, exist_ok=False)
    (output / "shard.json").write_bytes(_canonical_bytes(payload))
    print(
        f"{world_seed}/{arm}/{lineage}: "
        f"EE={row['ratio_of_sums_ee_bits_per_j']:.9g} elapsed={row['elapsed_s']:.1f}s"
    )
    return payload


def _pool(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise V015OracleError("cannot pool empty rows")
    bits = math.fsum(float(row["total_bits"]) for row in rows)
    energy = math.fsum(float(row["total_energy_j"]) for row in rows)
    served = sum(int(row["served_user_steps"]) for row in rows)
    return {
        "row_count": len(rows),
        "total_bits": bits,
        "total_energy_j": energy,
        "ratio_of_sums_ee_bits_per_j": bits / energy,
        "served_user_steps": served,
        "served_fraction": served / (len(rows) * USERS * STEPS_PER_EPISODE),
        "active_beam_steps": sum(int(row["active_beam_steps"]) for row in rows),
        "active_satellite_steps": sum(int(row["active_satellite_steps"]) for row in rows),
        "c3_legal_spread_count": sum(int(row["c3_legal_spread_count"]) for row in rows),
        "supported_positive_target_count": sum(int(row["supported_positive_target_count"]) for row in rows),
        "compatible_action_count": sum(int(row["compatible_action_count"]) for row in rows),
        "action_exposure": sum(int(row["action_exposure"]) for row in rows),
    }


def _pair_gate(
    rows: Sequence[Mapping[str, Any]],
    *,
    worlds: Sequence[int],
    lineages: Sequence[int],
) -> dict[str, Any]:
    indexed = {
        (int(row["world_seed"]), str(row["arm"]), int(row["initialization_seed"])): row
        for row in rows
    }
    expected = {(int(world), arm, int(lineage)) for world in worlds for arm in ARMS for lineage in lineages}
    if set(indexed) != expected:
        raise V015OracleError("shard closure is not a complete rectangular paired panel")
    pooled = {arm: _pool([row for row in rows if row["arm"] == arm]) for arm in ARMS}
    by_world = {
        str(world): {
            arm: _pool([row for row in rows if int(row["world_seed"]) == int(world) and row["arm"] == arm])
            for arm in ARMS
        }
        for world in worlds
    }
    full = pooled["FULL_ZR"]
    drop = pooled["DROP_C3"]
    pooled_delta = float(full["ratio_of_sums_ee_bits_per_j"]) - float(drop["ratio_of_sums_ee_bits_per_j"])
    world_receipts: dict[str, Any] = {}
    positive_world_count = 0
    for world in worlds:
        world_full = by_world[str(world)]["FULL_ZR"]
        world_drop = by_world[str(world)]["DROP_C3"]
        world_delta = float(world_full["ratio_of_sums_ee_bits_per_j"]) - float(world_drop["ratio_of_sums_ee_bits_per_j"])
        positive_lineages = 0
        service_lineages = 0
        lineage_receipts: dict[str, Any] = {}
        for lineage in lineages:
            full_row = indexed[(int(world), "FULL_ZR", int(lineage))]
            drop_row = indexed[(int(world), "DROP_C3", int(lineage))]
            delta = float(full_row["ratio_of_sums_ee_bits_per_j"]) - float(drop_row["ratio_of_sums_ee_bits_per_j"])
            service_delta = int(full_row["served_user_steps"]) - int(drop_row["served_user_steps"])
            positive_lineages += int(delta > 0.0)
            service_lineages += int(service_delta >= 0)
            lineage_receipts[str(lineage)] = {
                "delta_ee_bits_per_j": delta,
                "relative_delta_ee": delta / float(drop_row["ratio_of_sums_ee_bits_per_j"]),
                "delta_served_user_steps": service_delta,
            }
        world_service = int(world_full["served_user_steps"]) >= int(world_drop["served_user_steps"])
        positive_world_count += int(world_delta > 0.0)
        world_receipts[str(world)] = {
            "delta_ee_bits_per_j": world_delta,
            "relative_delta_ee": world_delta / float(world_drop["ratio_of_sums_ee_bits_per_j"]),
            "delta_served_user_steps": int(world_full["served_user_steps"]) - int(world_drop["served_user_steps"]),
            "delta_total_energy_j": float(world_full["total_energy_j"]) - float(world_drop["total_energy_j"]),
            "positive_lineages": positive_lineages,
            "service_noninferior_lineages": service_lineages,
            "pooled_service_noninferior": world_service,
            "by_lineage": lineage_receipts,
        }
    lineage_receipts: dict[str, Any] = {}
    positive_lineage_count = 0
    for lineage in lineages:
        full_rows = [
            row
            for row in rows
            if str(row["arm"]) == "FULL_ZR"
            and int(row["initialization_seed"]) == int(lineage)
        ]
        drop_rows = [
            row
            for row in rows
            if str(row["arm"]) == "DROP_C3"
            and int(row["initialization_seed"]) == int(lineage)
        ]
        full_lineage = _pool(full_rows)
        drop_lineage = _pool(drop_rows)
        delta = float(full_lineage["ratio_of_sums_ee_bits_per_j"]) - float(
            drop_lineage["ratio_of_sums_ee_bits_per_j"]
        )
        positive_lineage_count += int(delta > 0.0)
        lineage_receipts[str(lineage)] = {
            "delta_ee_bits_per_j": delta,
            "relative_delta_ee": delta
            / float(drop_lineage["ratio_of_sums_ee_bits_per_j"]),
            "delta_served_user_steps": int(full_lineage["served_user_steps"])
            - int(drop_lineage["served_user_steps"]),
        }
    integrity = all(
        bool(row["mechanics_passed"])
        and bool(row["method_passed"])
        and bool(row["candidate_specific_identity_passed"])
        and bool(row["changed_actions_compatible"])
        and bool(row["joint_support_passed"])
        for row in rows
    )
    exposure = int(full["action_exposure"]) > 0
    spread = int(full["c3_legal_spread_count"]) > 0
    service = int(full["served_user_steps"]) >= int(drop["served_user_steps"])
    hard_stops = []
    for passed, message in (
        (integrity, "mechanics/method integrity failed"),
        (spread, "FULL_ZR has zero legal C3 spread"),
        (exposure, "FULL_ZR has zero action exposure"),
        (pooled_delta > 0.0, "pooled EE is not strictly above DROP_C3"),
        (positive_world_count >= min(3, len(tuple(worlds))), "fewer than three world-pooled directions are positive"),
        (positive_lineage_count >= min(2, len(tuple(lineages))), "fewer than two lineage-pooled directions are positive"),
        (service, "pooled service guard failed"),
    ):
        if not passed:
            hard_stops.append(message)
    return {
        "passed": not hard_stops,
        "pooled": {
            "delta_ee_bits_per_j": pooled_delta,
            "relative_delta_ee": pooled_delta / float(drop["ratio_of_sums_ee_bits_per_j"]),
            "Delta": float(full["ratio_of_sums_ee_bits_per_j"])
            / float(drop["ratio_of_sums_ee_bits_per_j"])
            - 1.0,
            "delta_served_user_steps": int(full["served_user_steps"]) - int(drop["served_user_steps"]),
            "delta_total_energy_j": float(full["total_energy_j"]) - float(drop["total_energy_j"]),
        },
        "pooled_by_arm": pooled,
        "by_world": world_receipts,
        "by_lineage": lineage_receipts,
        "positive_world_count": positive_world_count,
        "positive_lineage_count": positive_lineage_count,
        "integrity_passed": integrity,
        "hard_stops": hard_stops,
    }


def _write_once_json(path: Path, payload: Mapping[str, Any]) -> str:
    destination = Path(path)
    if destination.exists() or destination.is_symlink():
        raise V015OracleError(f"refusing to overwrite {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    encoded = _canonical_bytes(payload)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_bytes(encoded)
    try:
        os.link(temporary, destination)
    except FileExistsError as error:
        raise V015OracleError(f"refusing to overwrite {destination}") from error
    finally:
        temporary.unlink(missing_ok=True)
    return file_sha256(destination)


def merge_shards(
    shard_files: Sequence[Path],
    output_dir: Path,
    *,
    worlds: Sequence[int],
    lineages: Sequence[int],
    q2_root: Path = V014_GATE_ROOT,
    v03_root: Path = V03_ROOT,
    prereg_path: Path = DEFAULT_PREREG,
) -> dict[str, Any]:
    output = Path(output_dir)
    if output.exists() or output.is_symlink():
        raise V015OracleError(f"refusing to overwrite merge output: {output}")
    validate_v015_contract()
    validate_v014_gate_receipts(q2_root)
    record = _V013.read_prereg(prereg_path)
    del record
    payloads = [_read_json(Path(path)) for path in shard_files]
    rows: list[dict[str, Any]] = []
    for payload in payloads:
        if payload.get("schema") != SHARD_SCHEMA:
            raise V015OracleError("a shard schema is stale")
        row = payload.get("row")
        if not isinstance(row, Mapping):
            raise V015OracleError("shard row is missing")
        if payload.get("row_sha256") != canonical_sha256(row):
            raise V015OracleError("shard row digest failed")
        if payload.get("q1_checkpoint_sha256") != row["q1_checkpoint"]["checkpoint_sha256"]:
            raise V015OracleError("shard Q1 receipt mismatch")
        if payload.get("q2_checkpoint_sha256") != row["q2_checkpoint"]["checkpoint_sha256"]:
            raise V015OracleError("shard Q2 receipt mismatch")
        rows.append(dict(row))
    expected_count = len(tuple(worlds)) * len(tuple(lineages)) * len(ARMS)
    if len(rows) != expected_count:
        raise V015OracleError(f"merge needs exactly {expected_count} shard rows")
    if len({(int(row["world_seed"]), str(row["arm"]), int(row["initialization_seed"])) for row in rows}) != len(rows):
        raise V015OracleError("merge contains duplicate shard identity")
    for world in worlds:
        world_rows = [row for row in rows if int(row["world_seed"]) == int(world)]
        if len({row["initial_world_sha256"] for row in world_rows}) != 1:
            raise V015OracleError("paired arms do not share one initial world")
        if len({row["field_root_digest"] for row in world_rows}) != 1:
            raise V015OracleError("paired arms do not share one common field")
    for lineage in lineages:
        lineage_rows = [row for row in rows if int(row["initialization_seed"]) == int(lineage)]
        if len({row["q1_checkpoint"]["checkpoint_sha256"] for row in lineage_rows}) != 1:
            raise V015OracleError("paired arms do not share one Q1 checkpoint")
        if len({row["q2_checkpoint"]["checkpoint_sha256"] for row in lineage_rows}) != 1:
            raise V015OracleError("paired arms do not share one Q2 checkpoint")
    gate = _pair_gate(rows, worlds=tuple(worlds), lineages=tuple(lineages))
    contract = contract_receipt(worlds=worlds, lineages=lineages)
    result = {
        "schema": RESULT_SCHEMA,
        "claim_ceiling": "TRAIN_DEVELOPMENT_ORACLE_NO_LEARNER_NO_TEST_NO_EFFICACY_CLAIM",
        "contract": contract,
        "contract_sha256": canonical_sha256(contract),
        "runner_file_sha256": file_sha256(Path(__file__).resolve()),
        "world_seeds": [int(value) for value in worlds],
        "lineages": [int(value) for value in lineages],
        "field_component": FIELD_COMPONENT,
        "rows": sorted(rows, key=lambda row: (int(row["world_seed"]), ARMS.index(str(row["arm"])), int(row["initialization_seed"]))),
        "summaries": {"pooled_by_arm": gate["pooled_by_arm"], "candidate_gate": gate},
        "gate": {"decision": "PASS_LEARNED_CONTEXT_ZR_ORACLE" if gate["passed"] else "STOP_LEARNED_CONTEXT_ZR_ORACLE", "passed": gate["passed"]},
    }
    result["result_sha256"] = canonical_sha256(result)
    result_file_sha = _write_once_json(output / "result.json", result)
    seal = {
        "schema": RESULT_SEAL_SCHEMA,
        "result_file_sha256": result_file_sha,
        "result_sha256": result["result_sha256"],
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
    }
    seal_file_sha = _write_once_json(output / "result-seal.json", seal)
    print(
        f"decision={result['gate']['decision']} "
        f"delta={gate['pooled']['delta_ee_bits_per_j']:+.6g}"
    )
    return {**result, "result_file_sha256": result_file_sha, "result_seal_file_sha256": seal_file_sha}


def _ints(values: Sequence[int] | None, default: Sequence[int]) -> tuple[int, ...]:
    result = tuple(int(value) for value in (values or default))
    if not result or len(set(result)) != len(result):
        raise V015OracleError("world/lineage CLI values must be distinct and nonempty")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("--json", action="store_true")
    shard = sub.add_parser("shard")
    shard.add_argument("--world", type=int, required=True)
    shard.add_argument("--lineage", type=int, choices=LINEAGES, required=True)
    shard.add_argument("--arm", choices=ARMS, required=True)
    shard.add_argument("--output", type=Path, required=True)
    shard.add_argument("--q2-root", type=Path, default=V014_GATE_ROOT)
    shard.add_argument("--v03-root", type=Path, default=V03_ROOT)
    shard.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    shard.add_argument("--tle-root", type=Path, default=DEFAULT_TLE_ROOT)
    merge = sub.add_parser("merge")
    merge.add_argument("--shards", type=Path, nargs="+", required=True)
    merge.add_argument("--output", type=Path, required=True)
    merge.add_argument("--world", type=int, action="append", default=None)
    merge.add_argument("--lineage", type=int, action="append", choices=LINEAGES, default=None)
    merge.add_argument("--q2-root", type=Path, default=V014_GATE_ROOT)
    merge.add_argument("--v03-root", type=Path, default=V03_ROOT)
    merge.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    args = parser.parse_args(argv)
    if args.command == "plan":
        payload = contract_receipt()
        print(json.dumps(payload, indent=2, sort_keys=True) if args.json else canonical_sha256(payload))
        return 0
    if args.command == "shard":
        run_shard(
            world_seed=args.world,
            arm=args.arm,
            lineage=args.lineage,
            output_dir=args.output,
            q2_root=args.q2_root,
            v03_root=args.v03_root,
            prereg_path=args.prereg,
            tle_root=args.tle_root,
        )
        return 0
    worlds = _ints(args.world, WORLD_SEEDS)
    lineages = _ints(args.lineage, LINEAGES)
    merge_shards(
        args.shards,
        args.output,
        worlds=worlds,
        lineages=lineages,
        q2_root=args.q2_root,
        v03_root=args.v03_root,
        prereg_path=args.prereg,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
