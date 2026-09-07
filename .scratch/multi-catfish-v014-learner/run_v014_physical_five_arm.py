#!/usr/bin/env python3
"""Authenticated physical adapter for the V0.14 five-arm TRAIN block.

This module is the execution seam between the source-only V0.14 learnability
gate and a later, sealed physical evaluation contract.  It deliberately does
not choose a world/evaluation seed, a fading component, a checkpoint rung, or
a legacy Main checkpoint.  Those values must be supplied by the caller after
the gate and evaluation contracts have been frozen.

The route decoder is the V0.14 direct sum of three independent surfaces:

``FULL``      = Q1 + Q2 + Q3
``DROP_C1``   =       Q2 + Q3
``DROP_C2``   = Q1      + Q3
``DROP_C3``   = Q1 + Q2

All route arms share the same native safe mask and one masked argmax.  MAIN is
not a route arm: it is supplied by an independent frozen legacy policy
callback.  Q1 is loaded through an explicit frozen-lineage callback; Q2 and
Q3 are reconstructed from the authenticated V0.14 gate checkpoints and are
only queried in ``eval``/no-gradient mode.  No optimizer, replay buffer,
learner update, TEST split, or episode training is reachable from the physical
evaluation methods.

The public workflow has three write-once boundaries:

``prepare_physical_evaluation``
    authenticates the gate and records the sealed input panel, without opening
    the simulator;
``run_physical_evaluation``
    consumes that preparation and writes TRAIN episode receipts plus the
    100-episode progress checkpoint;
``verify_physical_evaluation``
    re-hashes and re-aggregates the receipts and writes a verification receipt.

The resulting files carry a development-only claim ceiling.  A successful
plumbing verification is not an efficacy result.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import io
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any, Protocol, TypeAlias

import numpy as np
import torch

from mcrl.algorithms.ee_axis_v014_head import (
    EEAxisV014HeadConfig,
    EEAxisV014PairwiseLearner,
)
from mcrl.env.keyed_fading import KeyedFadingField
from mcrl.errors import MCRLContractError
from mcrl.runtime.ee_axis_ops3 import OPS3_KAPPA_BITS
from mcrl.runtime.ee_axis_ops3_live import (
    build_ops3_live_surfaces,
    project_ops3_anchor,
    snapshot_ops3_anchor,
)
from mcrl.runtime.ee_axis_state import encode_ee_axis_state
from mcrl.runtime.ee_axis_v014_q2_state import encode_ee_axis_v014_q2_states
from mcrl.runtime.ee_axis_v014_q3_state import encode_ee_axis_v014_q3_state


HERE = Path(__file__).resolve().parent

# The already-frozen callback/aggregation seam is intentionally imported as a
# data module.  This file does not edit or duplicate its route accounting.
import importlib.util as _importlib_util
import sys as _sys

_EVALUATION_PATH = HERE / "run_v014_five_arm_evaluation.py"
_EVALUATION_SPEC = _importlib_util.spec_from_file_location(
    "mcrl_v014_five_arm_evaluation_for_physical", _EVALUATION_PATH
)
if _EVALUATION_SPEC is None or _EVALUATION_SPEC.loader is None:
    raise RuntimeError(f"cannot load V0.14 evaluation seam: {_EVALUATION_PATH}")
_EVALUATION = _importlib_util.module_from_spec(_EVALUATION_SPEC)
_sys.modules[_EVALUATION_SPEC.name] = _EVALUATION
_EVALUATION_SPEC.loader.exec_module(_EVALUATION)

ACTION_DIM = int(_EVALUATION.ACTION_DIM)
ARMS = tuple(_EVALUATION.ARMS)
ROUTE_ARMS = tuple(_EVALUATION.ROUTE_ARMS)
MAIN_ARM = str(_EVALUATION.MAIN_ARM)
V014EpisodeReceipt = _EVALUATION.V014EpisodeReceipt
aggregate_arm = _EVALUATION.aggregate_arm
aggregate_five_arm = _EVALUATION.aggregate_five_arm


PHYSICAL_RUNNER_SCHEMA = "multi-catfish-mcrl-v014-physical-five-arm-v1"
PREPARE_SCHEMA = "multi-catfish-mcrl-v014-physical-five-arm-prepare-v1"
RUN_SCHEMA = "multi-catfish-mcrl-v014-physical-five-arm-run-v1"
VERIFY_SCHEMA = "multi-catfish-mcrl-v014-physical-five-arm-verify-v1"
PHYSICAL_CHECKPOINT_SCHEMA = (
    "multi-catfish-mcrl-v014-physical-five-arm-episode-checkpoint-v1"
)
GATE_RESULT_SCHEMA = "multi-catfish-mcrl-v014-supervised-learnability-result-v1"
GATE_RESULT_SEAL_SCHEMA = (
    "multi-catfish-mcrl-v014-supervised-learnability-result-seal-v1"
)
GATE_CHECKPOINT_SCHEMA = (
    "multi-catfish-mcrl-v014-supervised-learnability-checkpoint-v1"
)
CLAIM_CEILING = "TRAIN_DEVELOPMENT_EE_RECEIPTS_ONLY_NO_TEST_EFFICACY_CLAIM"

EVALUATION_EPISODES = 100
CHECKPOINT_EVERY_EPISODES = 100
# This panel is supplied by the parent V0.14 freeze.  It is intentionally not
# used as a CLI default: the later sealed contract must still provide all 100
# values explicitly, and the runner verifies that the supplied block matches
# this freeze.
REQUIRED_EVALUATION_SEEDS = tuple(range(2026109001, 2026109101))
DEFAULT_USERS = 100
DEFAULT_STEPS = 10
DEFAULT_KAPPA_BITS = float(OPS3_KAPPA_BITS)
Q2_LOCAL_FEATURES = 16
Q3_LOCAL_FEATURES = 10
Q3_GLOBAL_FEATURES = 7


class V014PhysicalRunnerError(MCRLContractError):
    """A physical V0.14 input, policy, receipt, or provenance check failed."""


def _canonical_bytes(payload: object) -> bytes:
    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V014PhysicalRunnerError("payload is not finite canonical JSON") from error


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def file_sha256(path: str | Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V014PhysicalRunnerError(f"expected a regular file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V014PhysicalRunnerError(f"{field} must be a lowercase SHA-256")
    return value


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise V014PhysicalRunnerError(f"{field} must be a positive integer")
    result = int(value)
    if result <= 0:
        raise V014PhysicalRunnerError(f"{field} must be a positive integer")
    return result


def _read_json(path: str | Path, *, field: str) -> dict[str, Any]:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise V014PhysicalRunnerError(f"cannot read {field}: {source}") from error
    if not isinstance(payload, dict):
        raise V014PhysicalRunnerError(f"{field} must be a JSON object")
    return payload


def _write_once_bytes(path: str | Path, payload: bytes) -> str:
    destination = Path(path)
    if destination.exists() or destination.is_symlink():
        raise V014PhysicalRunnerError(f"refusing to overwrite {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary_name, destination)
        except FileExistsError as error:
            raise V014PhysicalRunnerError(
                f"refusing to overwrite {destination}"
            ) from error
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
    return file_sha256(destination)


def _write_once_json_strict(path: str | Path, payload: Mapping[str, Any]) -> str:
    return _write_once_bytes(
        path,
        (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode("ascii"),
    )


def _torch_state_sha256(module: Any) -> str:
    """Digest parameters and buffers without touching optimizer state."""

    if not hasattr(module, "state_dict"):
        raise V014PhysicalRunnerError("frozen network has no state_dict")
    digest = hashlib.sha256()
    state = module.state_dict()
    for name, value in state.items():
        tensor = value.detach().cpu()
        digest.update(str(name).encode("utf-8"))
        digest.update(str(tensor.dtype).encode("ascii"))
        digest.update(repr(tuple(tensor.shape)).encode("ascii"))
        digest.update(tensor.numpy().tobytes(order="C"))
    return digest.hexdigest()


def _optimizer_state_sha256(learner: EEAxisV014PairwiseLearner) -> str:
    """Digest optimizer slots to make the no-update boundary auditable."""

    buffer = io.BytesIO()
    torch.save(learner.optimizer.state_dict(), buffer)
    return hashlib.sha256(buffer.getvalue()).hexdigest()


def _action_trace_update(digest: "hashlib._Hash", actions: np.ndarray) -> None:
    values = np.ascontiguousarray(np.asarray(actions, dtype=np.int64))
    digest.update(values.dtype.str.encode("ascii"))
    digest.update(repr(tuple(values.shape)).encode("ascii"))
    digest.update(values.tobytes(order="C"))


def _array_surface(network: Any, states: np.ndarray, masks: np.ndarray) -> np.ndarray:
    """Evaluate a frozen Q network with the canonical tensor boundary."""

    values = np.asarray(states, dtype=np.float32)
    legal = np.asarray(masks)
    if values.ndim != 2 or legal.dtype != np.bool_:
        raise V014PhysicalRunnerError("network input state/mask is malformed")
    if legal.shape != (values.shape[0], ACTION_DIM):
        raise V014PhysicalRunnerError("network input mask is not action-aligned")
    with torch.no_grad():
        result = network(
            torch.tensor(values, dtype=torch.float32),
            torch.tensor(legal, dtype=torch.bool),
        )
    array = np.asarray(result.detach().cpu().numpy(), dtype=np.float64)
    if array.shape != legal.shape or not np.all(np.isfinite(array)):
        raise V014PhysicalRunnerError("frozen Q1 surface is malformed")
    return array


def _q1_actions(values: np.ndarray, masks: np.ndarray) -> np.ndarray:
    """Internal Q1 reference needed to build the Q2 causal sidecar."""

    legal = np.asarray(masks)
    if legal.dtype != np.bool_ or values.shape != legal.shape:
        raise V014PhysicalRunnerError("Q1 reference surface/mask mismatch")
    if not np.all(np.any(legal, axis=1)):
        raise V014PhysicalRunnerError("every user needs a legal Q1 reference")
    return np.argmax(np.where(legal, values, -np.inf), axis=1).astype(
        np.int64, copy=False
    )


def _set_fading_field(environment: Any, field: Any) -> Any:
    """Attach one field to a fresh TrainerEnvironment/StepEnvironment."""

    step_environment = getattr(environment, "environment", environment)
    if not hasattr(step_environment, "_fading_field"):
        raise V014PhysicalRunnerError(
            "environment does not expose the canonical fading-field boundary"
        )
    step_environment._fading_field = field
    return step_environment


def _reset_environment(environment: Any, rngs: Sequence[Any]) -> Any:
    if len(rngs) < 2:
        raise V014PhysicalRunnerError("rng_factory must return env and mobility RNGs")
    reset = environment.reset(rngs[0], rngs[1])
    if isinstance(reset, tuple) and len(reset) == 3:
        return reset[2]
    return reset


def _last_outcome(environment: Any, result: Any) -> Any:
    # The live outcome is authoritative.  In particular, do not use
    # ``result.observation``: the canonical environment stores the next
    # predecision observation on ``last_outcome`` after a step.
    outcome = getattr(environment, "last_outcome", None)
    if outcome is None:
        raise V014PhysicalRunnerError("environment did not expose last_outcome")
    return outcome


def _observation_after_step(environment: Any, outcome: Any) -> Any:
    observation = getattr(outcome, "observation", None)
    if observation is None:
        raise V014PhysicalRunnerError("last_outcome has no next observation")
    return observation


@dataclass(frozen=True)
class V014GateHeadPair:
    """One authenticated, no-update Q2/Q3 pair at the common gate rung."""

    initialization_seed: int
    checkpoint_path: Path
    checkpoint_sha256: str
    update_rung: int
    q2: EEAxisV014PairwiseLearner
    q3: EEAxisV014PairwiseLearner
    q2_config: dict[str, Any]
    q3_config: dict[str, Any]

    def verify_frozen(self) -> None:
        if self.q2 is self.q3:
            raise V014PhysicalRunnerError("Q2 and Q3 must be independent learners")
        if self.q2.config == self.q3.config:
            # The state dimensions are part of the V0.14 role separation.  A
            # common MLP form is fine; identical Q2/Q3 state configs are not.
            raise V014PhysicalRunnerError("Q2 and Q3 configs must be role-specific")
        if self.q2.config.action_dim != ACTION_DIM or self.q3.config.action_dim != ACTION_DIM:
            raise V014PhysicalRunnerError("V0.14 heads must use the native action set")
        if self.q2.config.local_feature_dim != Q2_LOCAL_FEATURES or self.q2.config.global_feature_dim != 0:
            raise V014PhysicalRunnerError("Q2 checkpoint state dimensions are not V0.14")
        if self.q3.config.local_feature_dim != Q3_LOCAL_FEATURES or self.q3.config.global_feature_dim != Q3_GLOBAL_FEATURES:
            raise V014PhysicalRunnerError("Q3 checkpoint state dimensions are not V0.14")
        self.q2.q.eval()
        self.q3.q.eval()
        self.q2.q.requires_grad_(False)
        self.q3.q.requires_grad_(False)
        if any(parameter.requires_grad for parameter in self.q2.q.parameters()) or any(
            parameter.requires_grad for parameter in self.q3.q.parameters()
        ):
            raise V014PhysicalRunnerError("learned route heads remain trainable")


@dataclass(frozen=True)
class V014GateSelection:
    """Gate result/seal plus the selected common-rung checkpoint heads."""

    result_path: Path
    seal_path: Path
    result_sha256: str
    seal_sha256: str
    authority_sha256: str
    run_spec_sha256: str
    deployment_rung: int
    initialization_seeds: tuple[int, ...]
    heads_by_initialization: Mapping[int, V014GateHeadPair]

    def verify(self) -> None:
        if len(self.initialization_seeds) != 3 or len(set(self.initialization_seeds)) != 3:
            raise V014PhysicalRunnerError("physical V0.14 panel requires three initialisations")
        if set(self.heads_by_initialization) != set(self.initialization_seeds):
            raise V014PhysicalRunnerError("gate heads do not match initialisation panel")
        _digest(self.result_sha256, field="gate result sha256")
        _digest(self.seal_sha256, field="gate seal sha256")
        _digest(self.authority_sha256, field="gate authority sha256")
        _digest(self.run_spec_sha256, field="gate run-spec sha256")
        _positive_int(self.deployment_rung, field="deployment_rung")
        for seed in self.initialization_seeds:
            pair = self.heads_by_initialization[int(seed)]
            if pair.initialization_seed != int(seed) or pair.update_rung != self.deployment_rung:
                raise V014PhysicalRunnerError(
                    "gate head metadata disagrees with the common deployment selection"
                )
            pair.verify_frozen()


def _revalidate_gate_files(selection: V014GateSelection) -> None:
    """Ensure the files behind an in-memory selection are still sealed."""

    if file_sha256(selection.result_path) != selection.result_sha256:
        raise V014PhysicalRunnerError("gate result changed after authentication")
    if file_sha256(selection.seal_path) != selection.seal_sha256:
        raise V014PhysicalRunnerError("gate result seal changed after authentication")
    for seed in selection.initialization_seeds:
        pair = selection.heads_by_initialization[int(seed)]
        if file_sha256(pair.checkpoint_path) != pair.checkpoint_sha256:
            raise V014PhysicalRunnerError(
                f"gate checkpoint changed after authentication for {seed}"
            )


def _load_gate_head(
    checkpoint_path: Path,
    *,
    expected_sha256: str,
    expected_seed: int,
    expected_rung: int,
) -> V014GateHeadPair:
    actual_sha256 = file_sha256(checkpoint_path)
    if actual_sha256 != expected_sha256:
        raise V014PhysicalRunnerError(
            f"gate checkpoint hash mismatch for initialisation {expected_seed}"
        )
    try:
        payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    except (OSError, EOFError, RuntimeError, TypeError, ValueError) as error:
        raise V014PhysicalRunnerError(
            f"cannot load gate checkpoint: {checkpoint_path}"
        ) from error
    if not isinstance(payload, Mapping):
        raise V014PhysicalRunnerError("gate checkpoint must be a mapping")
    if payload.get("schema") != GATE_CHECKPOINT_SCHEMA:
        raise V014PhysicalRunnerError("checkpoint is not a V0.14 gate checkpoint")
    if payload.get("claim_ceiling") != "NO_DEPLOYED_EFFICACY_OR_EE_CLAIM":
        raise V014PhysicalRunnerError("gate checkpoint claim ceiling drifted")
    if payload.get("initialization_seed") != expected_seed:
        raise V014PhysicalRunnerError("checkpoint initialisation seed disagrees")
    if payload.get("update_rung") != expected_rung:
        raise V014PhysicalRunnerError("checkpoint is not at the common deployment rung")
    if any(bool(payload.get(name, True)) for name in (
        "test_split_opened", "held_out_ee_evaluated", "episode_training"
    )):
        raise V014PhysicalRunnerError("gate checkpoint crossed a forbidden boundary")
    q2_payload = payload.get("q2")
    q3_payload = payload.get("q3")
    if not isinstance(q2_payload, Mapping) or not isinstance(q3_payload, Mapping):
        raise V014PhysicalRunnerError("gate checkpoint lacks independent Q2/Q3 states")
    try:
        q2_config_payload = dict(q2_payload["config"])
        q3_config_payload = dict(q3_payload["config"])
        q2_config = EEAxisV014HeadConfig(**q2_config_payload)
        q3_config = EEAxisV014HeadConfig(**q3_config_payload)
        q2_seed = _positive_int(q2_payload["train_seed"], field="Q2 train_seed")
        q3_seed = _positive_int(q3_payload["train_seed"], field="Q3 train_seed")
        if q2_seed != expected_seed or q3_seed != expected_seed:
            raise V014PhysicalRunnerError("head train seeds disagree with initialisation")
        q2 = EEAxisV014PairwiseLearner(q2_config, train_seed=q2_seed, device="cpu")
        q3 = EEAxisV014PairwiseLearner(q3_config, train_seed=q3_seed, device="cpu")
        if q2.load_checkpoint_state(q2_payload) != expected_rung:
            raise V014PhysicalRunnerError("Q2 inner checkpoint rung disagrees")
        if q3.load_checkpoint_state(q3_payload) != expected_rung:
            raise V014PhysicalRunnerError("Q3 inner checkpoint rung disagrees")
    except (KeyError, TypeError, ValueError, MCRLContractError) as error:
        raise V014PhysicalRunnerError("malformed independent V0.14 head state") from error
    pair = V014GateHeadPair(
        initialization_seed=int(expected_seed),
        checkpoint_path=checkpoint_path,
        checkpoint_sha256=actual_sha256,
        update_rung=int(expected_rung),
        q2=q2,
        q3=q3,
        q2_config=q2_config_payload,
        q3_config=q3_config_payload,
    )
    pair.verify_frozen()
    return pair


def authenticate_gate_selection(
    *,
    result_path: str | Path,
    seal_path: str | Path,
    expected_result_sha256: str,
    expected_seal_sha256: str,
    checkpoint_paths_by_initialization: Mapping[int, str | Path],
    initialization_seeds: Sequence[int],
) -> V014GateSelection:
    """Authenticate a PASS gate and reconstruct Q2/Q3 at one common rung.

    The expected result/seal hashes are required by design.  A physical run
    cannot silently treat an unsealed local result as the selected gate.
    Likewise, checkpoint *paths* are explicit because the gate result records
    hashes, not an authority to search a mutable directory.
    """

    result_file = Path(result_path)
    seal_file = Path(seal_path)
    expected_result = _digest(expected_result_sha256, field="expected gate result sha256")
    expected_seal = _digest(expected_seal_sha256, field="expected gate seal sha256")
    actual_result = file_sha256(result_file)
    actual_seal = file_sha256(seal_file)
    if actual_result != expected_result:
        raise V014PhysicalRunnerError("gate result does not match supplied seal hash")
    if actual_seal != expected_seal:
        raise V014PhysicalRunnerError("gate result-seal file does not match supplied hash")
    result = _read_json(result_file, field="gate result")
    seal = _read_json(seal_file, field="gate result seal")
    if result.get("schema") != GATE_RESULT_SCHEMA:
        raise V014PhysicalRunnerError("gate result schema is not V0.14")
    if seal.get("schema") != GATE_RESULT_SEAL_SCHEMA:
        raise V014PhysicalRunnerError("gate seal schema is not V0.14")
    if seal.get("result_file_sha256") != actual_result:
        raise V014PhysicalRunnerError("gate seal does not authenticate result bytes")
    for name in ("authority_sha256", "run_spec_sha256"):
        _digest(result.get(name), field=f"gate result {name}")
        if seal.get(name) != result.get(name):
            raise V014PhysicalRunnerError(f"gate seal {name} disagrees with result")
    if result.get("status") != "PASS_LEARNABILITY_GATE":
        raise V014PhysicalRunnerError("physical evaluation requires PASS_LEARNABILITY_GATE")
    if result.get("claim_ceiling") != "NO_DEPLOYED_EFFICACY_OR_EE_CLAIM":
        raise V014PhysicalRunnerError("gate claim ceiling is not the frozen development ceiling")
    if any(bool(result.get(name, True)) for name in (
        "test_split_opened", "held_out_ee_evaluated", "episode_training"
    )):
        raise V014PhysicalRunnerError("gate result crossed a forbidden boundary")
    selection = result.get("selection")
    if not isinstance(selection, Mapping):
        raise V014PhysicalRunnerError("gate result lacks selection")
    common_rung = selection.get("common_joint_rung")
    deployment_rung = selection.get("deployment_rung")
    if common_rung != deployment_rung:
        raise V014PhysicalRunnerError("deployment must use the common joint rung")
    rung = _positive_int(common_rung, field="common joint deployment rung")
    seeds = tuple(_positive_int(seed, field="initialization seed") for seed in initialization_seeds)
    if len(seeds) != 3 or len(set(seeds)) != 3:
        raise V014PhysicalRunnerError("exactly three distinct initialisation seeds are required")
    spec_payload = result.get("spec")
    if not isinstance(spec_payload, Mapping):
        raise V014PhysicalRunnerError("gate result lacks a valid learner spec")
    try:
        stored_seeds = tuple(
            sorted(int(value) for value in (spec_payload.get("initialization_seeds", ()) or ()))
        )
    except (TypeError, ValueError) as error:
        raise V014PhysicalRunnerError("gate result initialisation panel is malformed") from error
    if stored_seeds != tuple(sorted(seeds)):
        raise V014PhysicalRunnerError("requested initialisation panel disagrees with gate result")
    stored_hashes = result.get("checkpoint_file_sha256s")
    if not isinstance(stored_hashes, Mapping):
        raise V014PhysicalRunnerError("gate result lacks checkpoint hashes")
    try:
        stored_hash_seed_set = {int(key) for key in stored_hashes}
    except (TypeError, ValueError) as error:
        raise V014PhysicalRunnerError("gate checkpoint hash panel is malformed") from error
    if stored_hash_seed_set != set(seeds):
        raise V014PhysicalRunnerError("gate checkpoint hash panel is incomplete")
    try:
        path_seed_set = {int(key) for key in checkpoint_paths_by_initialization}
    except (TypeError, ValueError) as error:
        raise V014PhysicalRunnerError("checkpoint path panel is malformed") from error
    if path_seed_set != set(seeds):
        raise V014PhysicalRunnerError("checkpoint path panel is incomplete")
    heads: dict[int, V014GateHeadPair] = {}
    for seed in seeds:
        per_seed = stored_hashes.get(str(seed), stored_hashes.get(seed))
        if not isinstance(per_seed, Mapping):
            raise V014PhysicalRunnerError("gate checkpoint hash row is malformed")
        expected_checkpoint = per_seed.get(str(rung), per_seed.get(rung))
        _digest(expected_checkpoint, field=f"checkpoint sha256 for {seed}")
        heads[int(seed)] = _load_gate_head(
            Path(checkpoint_paths_by_initialization[int(seed)]),
            expected_sha256=expected_checkpoint,
            expected_seed=int(seed),
            expected_rung=rung,
        )
    selection_obj = V014GateSelection(
        result_path=result_file,
        seal_path=seal_file,
        result_sha256=actual_result,
        seal_sha256=actual_seal,
        authority_sha256=str(result["authority_sha256"]),
        run_spec_sha256=str(result["run_spec_sha256"]),
        deployment_rung=rung,
        initialization_seeds=seeds,
        heads_by_initialization=heads,
    )
    selection_obj.verify()
    return selection_obj


@dataclass(frozen=True)
class V014PhysicalEvaluationSpec:
    """Later-sealed physical panel; no evaluation seed has a default."""

    evaluation_seeds: tuple[int, ...]
    field_component: str
    initialization_seeds: tuple[int, ...]
    users: int = DEFAULT_USERS
    steps: int = DEFAULT_STEPS
    checkpoint_every_episodes: int = CHECKPOINT_EVERY_EPISODES
    evaluation_split: str = "TRAIN"
    claim_ceiling: str = CLAIM_CEILING

    @property
    def episodes(self) -> int:
        return len(self.evaluation_seeds)

    def verify(self) -> None:
        if tuple(self.evaluation_seeds) != REQUIRED_EVALUATION_SEEDS:
            raise V014PhysicalRunnerError(
                "the sealed physical block must provide evaluation seeds "
                "2026109001..2026109100 in order"
            )
        if len(set(self.evaluation_seeds)) != len(self.evaluation_seeds):
            raise V014PhysicalRunnerError("evaluation seeds must be distinct")
        for index, seed in enumerate(self.evaluation_seeds):
            _positive_int(seed, field=f"evaluation_seeds[{index}]")
        if len(self.initialization_seeds) != 3 or len(set(self.initialization_seeds)) != 3:
            raise V014PhysicalRunnerError("physical block requires three initialisations")
        for index, seed in enumerate(self.initialization_seeds):
            _positive_int(seed, field=f"initialization_seeds[{index}]")
        if not isinstance(self.field_component, str) or not self.field_component.strip():
            raise V014PhysicalRunnerError("field_component is required and cannot be blank")
        if self.users != DEFAULT_USERS or self.steps != DEFAULT_STEPS:
            raise V014PhysicalRunnerError("V0.14 physical panel uses 100 users and ten steps")
        if self.checkpoint_every_episodes != CHECKPOINT_EVERY_EPISODES:
            raise V014PhysicalRunnerError("physical receipt cadence must be exactly 100 episodes")
        if self.evaluation_split != "TRAIN":
            raise V014PhysicalRunnerError("physical evaluation is TRAIN-only")
        if self.claim_ceiling != CLAIM_CEILING:
            raise V014PhysicalRunnerError("physical claim ceiling cannot be widened")

    def as_dict(self) -> dict[str, Any]:
        self.verify()
        return {
            "schema": PHYSICAL_RUNNER_SCHEMA,
            "evaluation_seeds": [int(seed) for seed in self.evaluation_seeds],
            "field_component": self.field_component,
            "initialization_seeds": [int(seed) for seed in self.initialization_seeds],
            "users": int(self.users),
            "steps": int(self.steps),
            "episodes": self.episodes,
            "checkpoint_every_episodes": int(self.checkpoint_every_episodes),
            "evaluation_split": self.evaluation_split,
            "claim_ceiling": self.claim_ceiling,
        }


Q1Loader: TypeAlias = Callable[[int], tuple[Any, Mapping[str, Any]]]
EnvironmentFactory: TypeAlias = Callable[[Any, int], Any]
RngFactory: TypeAlias = Callable[[int], Sequence[Any]]
FieldFactory: TypeAlias = Callable[[str, int], Any]


@dataclass(frozen=True)
class V014PhysicalEpisode:
    """Base receipt plus immutable provenance retained outside the old seam."""

    receipt: V014EpisodeReceipt
    provenance: Mapping[str, Any]

    def as_dict(self) -> dict[str, Any]:
        payload = self.receipt.as_dict()
        payload["provenance"] = dict(self.provenance)
        return payload


class MainEpisodeRunner(Protocol):
    def __call__(
        self,
        *,
        episode_index: int,
        evaluation_seed: int,
        field: Any,
    ) -> V014EpisodeReceipt | Mapping[str, Any]:
        """Run one independent frozen legacy MAIN episode."""


class V014PhysicalAdapter:
    """Run one route episode with frozen Q1/Q2/Q3 surfaces."""

    def __init__(
        self,
        *,
        selection: V014GateSelection,
        archive: Any,
        q1_loader: Q1Loader,
        make_environment: EnvironmentFactory,
        rng_factory: RngFactory,
        field_factory: FieldFactory | None = None,
        users: int = DEFAULT_USERS,
        steps: int = DEFAULT_STEPS,
        kappa_bits: float = DEFAULT_KAPPA_BITS,
    ) -> None:
        selection.verify()
        if not callable(q1_loader) or not callable(make_environment) or not callable(rng_factory):
            raise V014PhysicalRunnerError("Q1/environment/RNG factories must be callable")
        if field_factory is not None and not callable(field_factory):
            raise V014PhysicalRunnerError("field_factory must be callable")
        if users != DEFAULT_USERS or steps != DEFAULT_STEPS:
            raise V014PhysicalRunnerError("physical V0.14 uses the canonical 100x10 episode")
        if not math.isfinite(float(kappa_bits)) or float(kappa_bits) <= 0.0:
            raise V014PhysicalRunnerError("kappa_bits must be finite and positive")
        for seed in selection.initialization_seeds:
            pair = selection.heads_by_initialization[int(seed)]
            if float(pair.q2.config.kappa_bits).hex() != float(kappa_bits).hex() or float(
                pair.q3.config.kappa_bits
            ).hex() != float(kappa_bits).hex():
                raise V014PhysicalRunnerError(
                    "physical kappa_bits disagrees with gate-selected head configs"
                )
        self.selection = selection
        self.archive = archive
        self.q1_loader = q1_loader
        self.make_environment = make_environment
        self.rng_factory = rng_factory
        self.field_factory = field_factory or (
            lambda component, seed: KeyedFadingField.from_components(component, seed)
        )
        self.users = int(users)
        self.steps = int(steps)
        self.kappa_bits = float(kappa_bits)
        self._q1_by_initialization: dict[int, tuple[Any, Mapping[str, Any]]] = {}
        self._q1_digests: dict[int, str] = {}

    def field_for(self, *, field_component: str, evaluation_seed: int) -> Any:
        _positive_int(evaluation_seed, field="evaluation_seed")
        field = self.field_factory(field_component, int(evaluation_seed))
        if not isinstance(field, KeyedFadingField):
            raise V014PhysicalRunnerError(
                "field_factory must return the canonical KeyedFadingField"
            )
        expected = KeyedFadingField.from_components(
            field_component, int(evaluation_seed)
        )
        if field.root_digest != expected.root_digest:
            raise V014PhysicalRunnerError(
                "field_factory did not produce the canonical component/seed field"
            )
        return field

    def _q1(self, initialization_seed: int) -> tuple[Any, Mapping[str, Any]]:
        seed = int(initialization_seed)
        if seed not in self.selection.heads_by_initialization:
            raise V014PhysicalRunnerError("Q1 lineage is outside the authenticated panel")
        cached = self._q1_by_initialization.get(seed)
        if cached is None:
            loaded = self.q1_loader(seed)
            if not isinstance(loaded, tuple) or len(loaded) != 2:
                raise V014PhysicalRunnerError("q1_loader must return (network, receipt)")
            network, receipt = loaded
            if not isinstance(receipt, Mapping):
                raise V014PhysicalRunnerError("Q1 receipt must be a mapping")
            network.eval()
            network.requires_grad_(False)
            if any(parameter.requires_grad for parameter in network.parameters()):
                raise V014PhysicalRunnerError("frozen Q1 still has trainable parameters")
            q1_digest = _digest(
                receipt.get("parameter_sha256"),
                field="Q1 receipt parameter_sha256",
            )
            if q1_digest != _torch_state_sha256(network):
                raise V014PhysicalRunnerError("Q1 receipt does not authenticate its network")
            cached = (network, receipt)
            self._q1_by_initialization[seed] = cached
            self._q1_digests[seed] = _torch_state_sha256(network)
        return cached

    def evaluate_route_episode(
        self,
        *,
        arm: str,
        episode_index: int,
        evaluation_seed: int,
        initialization_seed: int,
        field: Any,
    ) -> V014PhysicalEpisode:
        if arm not in ROUTE_ARMS:
            raise V014PhysicalRunnerError("physical route episode requires a route arm")
        _positive_int(episode_index, field="episode_index")
        _positive_int(evaluation_seed, field="evaluation_seed")
        _positive_int(initialization_seed, field="initialization_seed")
        if field is None:
            raise V014PhysicalRunnerError("paired keyed fading field cannot be None")
        q1, q1_receipt = self._q1(initialization_seed)
        pair = self.selection.heads_by_initialization[int(initialization_seed)]
        q1_before = self._q1_digests[int(initialization_seed)]
        q2_before = _torch_state_sha256(pair.q2.q)
        q3_before = _torch_state_sha256(pair.q3.q)
        q2_optimizer_before = _optimizer_state_sha256(pair.q2)
        q3_optimizer_before = _optimizer_state_sha256(pair.q3)
        environment = self.make_environment(self.archive, self.users)
        step_environment = _set_fading_field(environment, field)
        rngs = tuple(self.rng_factory(int(evaluation_seed)))
        if len(rngs) < 2:
            raise V014PhysicalRunnerError("rng_factory must return env and mobility RNGs")
        env_rng = rngs[0]
        observation = _reset_environment(environment, rngs)
        try:
            interval_s = float(step_environment.driver.config.ephemeris.time_step_s)
        except (AttributeError, TypeError, ValueError) as error:
            raise V014PhysicalRunnerError("canonical decision interval is unavailable") from error
        if not math.isfinite(interval_s) or interval_s <= 0.0:
            raise V014PhysicalRunnerError("decision interval must be finite and positive")
        total_bits = 0.0
        total_energy = 0.0
        served_steps = 0
        action_digest = hashlib.sha256()
        with torch.no_grad():
            for step_index in range(self.steps):
                native = encode_ee_axis_state(step_environment, observation)
                mask = np.asarray(native.action_masks, dtype=np.bool_)
                q1_values = _array_surface(q1, native.state_matrix, mask)
                q1_reference = _q1_actions(q1_values, mask)

                # Q2 is derived from the detached OPS-3 physical forecast at
                # this live predecision anchor.  The forecast does not advance
                # the live environment or consume its RNG.
                anchor = snapshot_ops3_anchor(step_environment, observation)
                projection = project_ops3_anchor(anchor)
                ops3_surfaces = build_ops3_live_surfaces(
                    anchor, projection, q1_reference
                )
                q2_state = encode_ee_axis_v014_q2_states(ops3_surfaces)
                q2_mask = np.asarray(q2_state.action_masks, dtype=np.bool_)
                q2_values = pair.q2.q_values(q2_state.state_matrix, q2_mask)

                # Q3 sees only current causal state and committed previous-slot
                # context; it never receives Q1/Q2 surfaces or teacher targets.
                q3_state = encode_ee_axis_v014_q3_state(
                    step_environment,
                    observation,
                    interval_s=interval_s,
                    kappa_bits=self.kappa_bits,
                )
                q3_mask = np.asarray(q3_state.action_masks, dtype=np.bool_)
                if not np.array_equal(mask, q2_mask) or not np.array_equal(mask, q3_mask):
                    raise V014PhysicalRunnerError(
                        "Q1/Q2/Q3 do not share one safe action mask"
                    )
                q3_values = pair.q3.q_values(q3_state.state_matrix, q3_mask)
                selected = _EVALUATION.route_actions(
                    q1_values, q2_values, q3_values, mask, arm
                )
                if selected.shape != (self.users,):
                    raise V014PhysicalRunnerError("route decoder returned wrong action shape")
                _action_trace_update(action_digest, selected)
                result = environment.step(selected, env_rng)
                outcome = _last_outcome(environment, result)
                rates = np.asarray(getattr(outcome, "link_rate_bps", None), dtype=np.float64)
                power = float(getattr(outcome, "system_power_w", np.nan))
                if rates.shape != (self.users,) or not np.all(np.isfinite(rates)) or np.any(rates < 0.0):
                    raise V014PhysicalRunnerError("canonical link-rate outcome is malformed")
                if not math.isfinite(power) or power <= 0.0:
                    raise V014PhysicalRunnerError("canonical system power must be positive")
                total_bits += interval_s * math.fsum(float(value) for value in rates)
                total_energy += interval_s * power
                resolution = getattr(outcome, "resolution", None)
                served_steps += _positive_or_zero_int(
                    getattr(resolution, "served_count", None),
                    field="served_count",
                )
                if step_index != self.steps - 1:
                    if bool(getattr(result, "done", False)):
                        raise V014PhysicalRunnerError("episode terminated before ten steps")
                    observation = _observation_after_step(environment, outcome)
        if _torch_state_sha256(q1) != q1_before:
            raise V014PhysicalRunnerError("physical evaluation mutated frozen Q1")
        if _torch_state_sha256(pair.q2.q) != q2_before or _torch_state_sha256(pair.q3.q) != q3_before:
            raise V014PhysicalRunnerError("physical evaluation mutated frozen Q2/Q3")
        if (
            _optimizer_state_sha256(pair.q2) != q2_optimizer_before
            or _optimizer_state_sha256(pair.q3) != q3_optimizer_before
        ):
            raise V014PhysicalRunnerError("physical evaluation mutated Q2/Q3 optimizers")
        receipt = V014EpisodeReceipt(
            arm=arm,
            episode_index=int(episode_index),
            evaluation_seed=int(evaluation_seed),
            total_bits=float(total_bits),
            total_energy_j=float(total_energy),
            decision_count=self.users * self.steps,
            served_user_steps=int(served_steps),
            initialization_seed=int(initialization_seed),
            world_seed=int(evaluation_seed),
            action_trace_sha256=action_digest.hexdigest(),
        )
        q1_sha = q1_receipt.get("parameter_sha256")
        if q1_sha is not None:
            _digest(q1_sha, field="Q1 receipt parameter_sha256")
        provenance = {
            "runner_schema": PHYSICAL_RUNNER_SCHEMA,
            "arm": arm,
            "initialization_seed": int(initialization_seed),
            "evaluation_seed": int(evaluation_seed),
            "field_root_digest": _field_root_digest(field),
            "gate_result_sha256": self.selection.result_sha256,
            "gate_seal_sha256": self.selection.seal_sha256,
            "deployment_rung": self.selection.deployment_rung,
            "q1_parameter_sha256": q1_sha,
            "q2_checkpoint_sha256": pair.checkpoint_sha256,
            "q3_checkpoint_sha256": pair.checkpoint_sha256,
            "q2_state_schema": "multi-catfish-mcrl-v014-ops3-q2-state-v1",
            "q3_state_schema": "multi-catfish-mcrl-v014-zr-q3-state-v1",
            "evaluation_split": "TRAIN",
            "test_split_opened": False,
            "held_out_ee_evaluated": False,
            "episode_training": False,
        }
        return V014PhysicalEpisode(receipt=receipt, provenance=provenance)


def _positive_or_zero_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise V014PhysicalRunnerError(f"{field} must be an integer")
    result = int(value)
    if result < 0:
        raise V014PhysicalRunnerError(f"{field} must be nonnegative")
    return result


def _field_root_digest(field: Any) -> str | None:
    value = getattr(field, "root_digest", None)
    if value is None:
        return None
    return _digest(value, field="field root_digest")


def _validate_main_receipt(
    raw: V014EpisodeReceipt | Mapping[str, Any],
    *,
    episode_index: int,
    evaluation_seed: int,
) -> V014EpisodeReceipt:
    if not isinstance(raw, V014EpisodeReceipt) and hasattr(raw, "as_dict"):
        raw = raw.as_dict()
    receipt = raw if isinstance(raw, V014EpisodeReceipt) else V014EpisodeReceipt.from_mapping(raw)
    if (
        receipt.arm != MAIN_ARM
        or receipt.episode_index != episode_index
        or receipt.evaluation_seed != evaluation_seed
        or receipt.initialization_seed is not None
    ):
        raise V014PhysicalRunnerError("MAIN callback returned an unpaired/contaminated receipt")
    return receipt


def _per_initialization_aggregates(
    rows_by_arm: Mapping[str, Sequence[V014EpisodeReceipt]],
    *,
    initialization_seeds: Sequence[int],
) -> dict[str, Any]:
    """Report pooled and each-init FULL-vs-drop contrasts without collapsing seeds."""

    output: dict[str, Any] = {}
    for seed in initialization_seeds:
        per_seed: dict[str, list[V014EpisodeReceipt]] = {}
        for arm in ROUTE_ARMS:
            rows = [
                row for row in rows_by_arm[arm]
                if row.initialization_seed == int(seed)
            ]
            if not rows:
                raise V014PhysicalRunnerError(
                    f"route arm {arm} has no rows for initialisation {seed}"
                )
            per_seed[arm] = rows
        summaries = {
            arm: aggregate_arm(per_seed[arm], arm=arm) for arm in ROUTE_ARMS
        }
        full_ee = float(summaries["FULL"]["pooled_ratio_of_sums_ee_bits_per_j"])
        contrasts = {}
        for arm in ("DROP_C1", "DROP_C2", "DROP_C3"):
            comparator_ee = float(summaries[arm]["pooled_ratio_of_sums_ee_bits_per_j"])
            contrasts[f"FULL_minus_{arm}"] = {
                "full_ee_bits_per_j": full_ee,
                "comparator_ee_bits_per_j": comparator_ee,
                "relative_delta": full_ee / comparator_ee - 1.0,
                "relative_delta_percent": 100.0 * (full_ee / comparator_ee - 1.0),
                "full_served_user_steps": int(summaries["FULL"]["served_user_steps"]),
                "comparator_served_user_steps": int(summaries[arm]["served_user_steps"]),
                "service_noninferior": int(summaries["FULL"]["served_user_steps"])
                >= int(summaries[arm]["served_user_steps"]),
            }
        output[str(int(seed))] = {
            "summaries": summaries,
            "contrasts": contrasts,
        }
    return output


def prepare_physical_evaluation(
    *,
    output_dir: str | Path,
    spec: V014PhysicalEvaluationSpec,
    selection: V014GateSelection,
) -> dict[str, Any]:
    """Create the immutable input receipt; this function never opens a simulator."""

    spec.verify()
    selection.verify()
    _revalidate_gate_files(selection)
    if tuple(spec.initialization_seeds) != tuple(selection.initialization_seeds):
        raise V014PhysicalRunnerError("physical spec seeds disagree with authenticated gate")
    destination = Path(output_dir)
    if destination.exists() or destination.is_symlink():
        raise V014PhysicalRunnerError(f"refusing to overwrite physical output: {destination}")
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "checkpoints").mkdir()
    body = {
        "schema": PREPARE_SCHEMA,
        "runner_schema": PHYSICAL_RUNNER_SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "spec": spec.as_dict(),
        "gate": {
            "result_path": str(selection.result_path),
            "seal_path": str(selection.seal_path),
            "result_sha256": selection.result_sha256,
            "seal_sha256": selection.seal_sha256,
            "authority_sha256": selection.authority_sha256,
            "run_spec_sha256": selection.run_spec_sha256,
            "deployment_rung": selection.deployment_rung,
            "initialization_seeds": list(selection.initialization_seeds),
            "checkpoint_paths": {
                str(seed): str(selection.heads_by_initialization[seed].checkpoint_path)
                for seed in selection.initialization_seeds
            },
            "checkpoint_sha256s": {
                str(seed): selection.heads_by_initialization[seed].checkpoint_sha256
                for seed in selection.initialization_seeds
            },
        },
        "evaluation_split": "TRAIN",
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "episode_training": False,
        "outcomes_opened": False,
    }
    body["prepare_sha256"] = canonical_sha256(body)
    digest = _write_once_json_strict(destination / "prepare.json", body)
    return {**body, "prepare_file_sha256": digest}


def _load_preparation(path: str | Path) -> dict[str, Any]:
    payload = _read_json(path, field="physical preparation")
    if payload.get("schema") != PREPARE_SCHEMA:
        raise V014PhysicalRunnerError("unsupported physical preparation schema")
    if payload.get("runner_schema") != PHYSICAL_RUNNER_SCHEMA:
        raise V014PhysicalRunnerError("physical preparation runner schema drifted")
    if payload.get("claim_ceiling") != CLAIM_CEILING:
        raise V014PhysicalRunnerError("physical preparation claim ceiling drifted")
    if any(bool(payload.get(name, True)) for name in ("test_split_opened", "held_out_ee_evaluated", "episode_training", "outcomes_opened")):
        raise V014PhysicalRunnerError("physical preparation crossed a forbidden boundary")
    claimed = payload.get("prepare_sha256")
    _digest(claimed, field="prepare_sha256")
    body = dict(payload)
    body.pop("prepare_sha256", None)
    if canonical_sha256(body) != claimed:
        raise V014PhysicalRunnerError("physical preparation self-digest mismatch")
    return payload


def run_physical_evaluation(
    *,
    prepared_path: str | Path,
    adapter: V014PhysicalAdapter,
    main_episode_runner: MainEpisodeRunner,
) -> dict[str, Any]:
    """Run the exact five-arm TRAIN block after preparation.

    The evaluation seeds are already in ``prepare.json``.  The runner never
    manufactures a seed or searches a directory for one.  For each evaluation
    seed, one keyed fading object is shared by every route lineage/arm and the
    independent legacy MAIN callback, establishing paired world identity.
    """

    if not callable(main_episode_runner):
        raise V014PhysicalRunnerError("main_episode_runner must be callable")
    preparation_file = Path(prepared_path)
    preparation = _load_preparation(preparation_file)
    spec_payload = preparation.get("spec")
    gate_payload = preparation.get("gate")
    if not isinstance(spec_payload, Mapping) or not isinstance(gate_payload, Mapping):
        raise V014PhysicalRunnerError("preparation lacks spec/gate")
    spec = V014PhysicalEvaluationSpec(
        evaluation_seeds=tuple(int(seed) for seed in spec_payload.get("evaluation_seeds", ())),
        field_component=str(spec_payload.get("field_component", "")),
        initialization_seeds=tuple(int(seed) for seed in spec_payload.get("initialization_seeds", ())),
        users=int(spec_payload.get("users", -1)),
        steps=int(spec_payload.get("steps", -1)),
        checkpoint_every_episodes=int(spec_payload.get("checkpoint_every_episodes", -1)),
        evaluation_split=str(spec_payload.get("evaluation_split", "")),
        claim_ceiling=str(spec_payload.get("claim_ceiling", "")),
    )
    spec.verify()
    adapter.selection.verify()
    _revalidate_gate_files(adapter.selection)
    if tuple(adapter.selection.initialization_seeds) != tuple(spec.initialization_seeds):
        raise V014PhysicalRunnerError("adapter gate panel disagrees with preparation")
    expected_gate = {
        "result_sha256": adapter.selection.result_sha256,
        "seal_sha256": adapter.selection.seal_sha256,
        "authority_sha256": adapter.selection.authority_sha256,
        "run_spec_sha256": adapter.selection.run_spec_sha256,
        "deployment_rung": adapter.selection.deployment_rung,
        "initialization_seeds": list(adapter.selection.initialization_seeds),
    }
    for name, expected in expected_gate.items():
        if gate_payload.get(name) != expected:
            raise V014PhysicalRunnerError(
                f"preparation gate {name} disagrees with authenticated selection"
            )
    destination = preparation_file.parent
    run_path = destination / "run.json"
    if run_path.exists() or run_path.is_symlink():
        raise V014PhysicalRunnerError(f"refusing to overwrite physical run: {run_path}")
    rows_by_arm: dict[str, list[V014EpisodeReceipt]] = {arm: [] for arm in ARMS}
    provenance: list[dict[str, Any]] = []
    checkpoint_hashes: dict[str, str] = {}
    episode_receipt_rows: list[dict[str, Any]] = []
    for episode_index, evaluation_seed in enumerate(spec.evaluation_seeds, start=1):
        field = adapter.field_for(
            field_component=spec.field_component,
            evaluation_seed=int(evaluation_seed),
        )
        field_digest = _field_root_digest(field)
        for arm in ROUTE_ARMS:
            for initialization_seed in spec.initialization_seeds:
                physical = adapter.evaluate_route_episode(
                    arm=arm,
                    episode_index=episode_index,
                    evaluation_seed=int(evaluation_seed),
                    initialization_seed=int(initialization_seed),
                    field=field,
                )
                receipt = physical.receipt
                rows_by_arm[arm].append(receipt)
                row = physical.as_dict()
                episode_receipt_rows.append(row)
                provenance.append(dict(physical.provenance))
        main_receipt = _validate_main_receipt(
            main_episode_runner(
                episode_index=episode_index,
                evaluation_seed=int(evaluation_seed),
                field=field,
            ),
            episode_index=episode_index,
            evaluation_seed=int(evaluation_seed),
        )
        rows_by_arm[MAIN_ARM].append(main_receipt)
        episode_receipt_rows.append(main_receipt.as_dict())
        provenance.append({
            "runner_schema": PHYSICAL_RUNNER_SCHEMA,
            "arm": MAIN_ARM,
            "initialization_seed": None,
            "evaluation_seed": int(evaluation_seed),
            "field_root_digest": field_digest,
            "gate_result_sha256": adapter.selection.result_sha256,
            "gate_seal_sha256": adapter.selection.seal_sha256,
            "deployment_rung": adapter.selection.deployment_rung,
            "evaluation_split": "TRAIN",
            "test_split_opened": False,
            "held_out_ee_evaluated": False,
            "episode_training": False,
        })
    aggregate = aggregate_five_arm(rows_by_arm)
    aggregate["per_initialization"] = _per_initialization_aggregates(
        rows_by_arm,
        initialization_seeds=spec.initialization_seeds,
    )
    receipts_payload = {
        "schema": RUN_SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "evaluation_split": "TRAIN",
        "rows": episode_receipt_rows,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "episode_training": False,
    }
    receipts_digest = _write_once_json_strict(
        destination / "episode-receipts.json", receipts_payload
    )
    provenance_payload = {
        "schema": RUN_SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "rows": provenance,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "episode_training": False,
    }
    provenance_digest = _write_once_json_strict(
        destination / "episode-provenance.json", provenance_payload
    )
    # The physical adapter is inference-only: this is an evaluation progress
    # receipt at the required 100-episode boundary, not a learner checkpoint.
    for arm in ARMS:
        checkpoint_payload = {
            "schema": PHYSICAL_CHECKPOINT_SCHEMA,
            "claim_ceiling": CLAIM_CEILING,
            "arm": arm,
            "episode_index": EVALUATION_EPISODES,
            "configured_episodes": EVALUATION_EPISODES,
            "evaluation_split": "TRAIN",
            "gate_result_sha256": adapter.selection.result_sha256,
            "gate_seal_sha256": adapter.selection.seal_sha256,
            "deployment_rung": adapter.selection.deployment_rung,
            "receipt_count": len(rows_by_arm[arm]),
            "test_split_opened": False,
            "held_out_ee_evaluated": False,
            "episode_training": False,
        }
        checkpoint_path = destination / "checkpoints" / f"{arm.lower()}-episode-000100.json"
        checkpoint_hashes[arm] = _write_once_json_strict(checkpoint_path, checkpoint_payload)
    run_body = {
        "schema": RUN_SCHEMA,
        "runner_schema": PHYSICAL_RUNNER_SCHEMA,
        "status": "COMPLETE_PLUMBING_ONLY",
        "claim_ceiling": CLAIM_CEILING,
        "prepare_file_sha256": file_sha256(preparation_file),
        "gate": dict(gate_payload),
        "spec": spec.as_dict(),
        "aggregate": aggregate,
        "episode_receipts_file_sha256": receipts_digest,
        "episode_provenance_file_sha256": provenance_digest,
        "checkpoint_file_sha256s": checkpoint_hashes,
        "evaluation_split": "TRAIN",
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "episode_training": False,
        "efficacy_claim": False,
    }
    run_digest = _write_once_json_strict(run_path, run_body)
    return {**run_body, "run_file_sha256": run_digest}


def verify_physical_evaluation(run_dir: str | Path) -> dict[str, Any]:
    """Verify hashes, exact five-arm shape, pairing, and ratio-of-sums totals."""

    destination = Path(run_dir)
    run_path = destination / "run.json"
    verify_path = destination / "verify.json"
    if verify_path.exists() or verify_path.is_symlink():
        raise V014PhysicalRunnerError(f"refusing to overwrite verification: {verify_path}")
    run = _read_json(run_path, field="physical run")
    if run.get("schema") != RUN_SCHEMA or run.get("runner_schema") != PHYSICAL_RUNNER_SCHEMA:
        raise V014PhysicalRunnerError("unsupported physical run schema")
    if run.get("claim_ceiling") != CLAIM_CEILING or run.get("status") != "COMPLETE_PLUMBING_ONLY":
        raise V014PhysicalRunnerError("physical run status/claim ceiling is invalid")
    if any(bool(run.get(name, True)) for name in ("test_split_opened", "held_out_ee_evaluated", "episode_training", "efficacy_claim")):
        raise V014PhysicalRunnerError("physical run crossed a forbidden boundary")
    preparation = _load_preparation(destination / "prepare.json")
    if run.get("prepare_file_sha256") != file_sha256(destination / "prepare.json"):
        raise V014PhysicalRunnerError("physical run preparation hash mismatch")
    if run.get("spec") != preparation.get("spec") or run.get("gate") != preparation.get("gate"):
        raise V014PhysicalRunnerError("physical run panel disagrees with preparation")
    spec_payload = preparation.get("spec")
    if not isinstance(spec_payload, Mapping):
        raise V014PhysicalRunnerError("preparation lacks physical spec")
    try:
        checked_spec = V014PhysicalEvaluationSpec(
            evaluation_seeds=tuple(int(seed) for seed in spec_payload["evaluation_seeds"]),
            field_component=str(spec_payload["field_component"]),
            initialization_seeds=tuple(int(seed) for seed in spec_payload["initialization_seeds"]),
            users=int(spec_payload["users"]),
            steps=int(spec_payload["steps"]),
            checkpoint_every_episodes=int(spec_payload["checkpoint_every_episodes"]),
            evaluation_split=str(spec_payload["evaluation_split"]),
            claim_ceiling=str(spec_payload["claim_ceiling"]),
        )
        checked_spec.verify()
    except (KeyError, TypeError, ValueError) as error:
        raise V014PhysicalRunnerError("preparation physical spec is malformed") from error
    receipts_path = destination / "episode-receipts.json"
    provenance_path = destination / "episode-provenance.json"
    if run.get("episode_receipts_file_sha256") != file_sha256(receipts_path):
        raise V014PhysicalRunnerError("episode receipt hash mismatch")
    if run.get("episode_provenance_file_sha256") != file_sha256(provenance_path):
        raise V014PhysicalRunnerError("episode provenance hash mismatch")
    receipts = _read_json(receipts_path, field="episode receipts")
    provenance = _read_json(provenance_path, field="episode provenance")
    if receipts.get("schema") != RUN_SCHEMA or provenance.get("schema") != RUN_SCHEMA:
        raise V014PhysicalRunnerError("episode receipt schema drifted")
    if any(bool(receipts.get(name, True)) for name in ("test_split_opened", "held_out_ee_evaluated", "episode_training")):
        raise V014PhysicalRunnerError("episode receipts crossed a forbidden boundary")
    if any(bool(provenance.get(name, True)) for name in ("test_split_opened", "held_out_ee_evaluated", "episode_training")):
        raise V014PhysicalRunnerError("episode provenance crossed a forbidden boundary")
    rows = receipts.get("rows")
    provenance_rows = provenance.get("rows")
    if not isinstance(rows, list) or not isinstance(provenance_rows, list) or len(rows) != len(provenance_rows):
        raise V014PhysicalRunnerError("receipt/provenance row counts disagree")
    rows_by_arm: dict[str, list[V014EpisodeReceipt]] = {arm: [] for arm in ARMS}
    expected_indices = set(range(1, len(checked_spec.evaluation_seeds) + 1))
    seen_route: set[tuple[str, int, int, int]] = set()
    seen_main: set[tuple[int, int]] = set()
    field_digests_by_seed: dict[int, str] = {}
    gate_payload = run.get("gate")
    if not isinstance(gate_payload, Mapping):
        raise V014PhysicalRunnerError("physical run lacks authenticated gate panel")
    try:
        gate_result_path = Path(str(gate_payload["result_path"]))
        gate_seal_path = Path(str(gate_payload["seal_path"]))
        if file_sha256(gate_result_path) != gate_payload["result_sha256"]:
            raise V014PhysicalRunnerError("gate result changed after physical run")
        if file_sha256(gate_seal_path) != gate_payload["seal_sha256"]:
            raise V014PhysicalRunnerError("gate result seal changed after physical run")
        checkpoint_paths = gate_payload["checkpoint_paths"]
        checkpoint_hashes = gate_payload["checkpoint_sha256s"]
        if not isinstance(checkpoint_paths, Mapping) or not isinstance(checkpoint_hashes, Mapping):
            raise V014PhysicalRunnerError("physical run gate checkpoint panel is malformed")
        for seed in checked_spec.initialization_seeds:
            path = Path(str(checkpoint_paths[str(seed)]))
            if file_sha256(path) != checkpoint_hashes[str(seed)]:
                raise V014PhysicalRunnerError(
                    f"gate checkpoint changed after physical run for {seed}"
                )
    except KeyError as error:
        raise V014PhysicalRunnerError("physical run gate file panel is incomplete") from error
    for raw, provenance_row in zip(rows, provenance_rows, strict=True):
        receipt = V014EpisodeReceipt.from_mapping(raw)
        if not isinstance(provenance_row, Mapping):
            raise V014PhysicalRunnerError("provenance row is not an object")
        if provenance_row.get("arm") != receipt.arm or provenance_row.get("evaluation_seed") != receipt.evaluation_seed:
            raise V014PhysicalRunnerError("provenance row is not paired to receipt")
        if provenance_row.get("runner_schema") != PHYSICAL_RUNNER_SCHEMA:
            raise V014PhysicalRunnerError("provenance runner schema drifted")
        if provenance_row.get("gate_result_sha256") != gate_payload.get("result_sha256"):
            raise V014PhysicalRunnerError("provenance gate result is not authenticated")
        if provenance_row.get("gate_seal_sha256") != gate_payload.get("seal_sha256"):
            raise V014PhysicalRunnerError("provenance gate seal is not authenticated")
        if provenance_row.get("deployment_rung") != gate_payload.get("deployment_rung"):
            raise V014PhysicalRunnerError("provenance deployment rung disagrees")
        if provenance_row.get("evaluation_split") != "TRAIN" or any(
            bool(provenance_row.get(name, True))
            for name in ("test_split_opened", "held_out_ee_evaluated", "episode_training")
        ):
            raise V014PhysicalRunnerError("provenance crossed a forbidden boundary")
        field_digest = provenance_row.get("field_root_digest")
        if field_digest is None:
            raise V014PhysicalRunnerError("provenance lacks the paired field root")
        _digest(field_digest, field="field root digest")
        prior_field_digest = field_digests_by_seed.setdefault(
            receipt.evaluation_seed, field_digest
        )
        if prior_field_digest != field_digest:
            raise V014PhysicalRunnerError(
                "one evaluation seed was evaluated under multiple fading fields"
            )
        rows_by_arm[receipt.arm].append(receipt)
        if receipt.arm in ROUTE_ARMS:
            if receipt.initialization_seed is None:
                raise V014PhysicalRunnerError("route receipt lacks initialisation seed")
            if provenance_row.get("initialization_seed") != receipt.initialization_seed:
                raise V014PhysicalRunnerError("route provenance initialisation is not paired")
            checkpoint_hashes = gate_payload.get("checkpoint_sha256s")
            if not isinstance(checkpoint_hashes, Mapping):
                raise V014PhysicalRunnerError("gate panel lacks checkpoint hashes")
            expected_checkpoint = checkpoint_hashes.get(str(receipt.initialization_seed))
            if provenance_row.get("q2_checkpoint_sha256") != expected_checkpoint or provenance_row.get("q3_checkpoint_sha256") != expected_checkpoint:
                raise V014PhysicalRunnerError("route provenance checkpoint is not gate-selected")
            key = (receipt.arm, receipt.episode_index, receipt.evaluation_seed, receipt.initialization_seed)
            if key in seen_route:
                raise V014PhysicalRunnerError("duplicate route receipt key")
            seen_route.add(key)
        else:
            if receipt.initialization_seed is not None:
                raise V014PhysicalRunnerError("MAIN receipt carries route initialisation")
            if provenance_row.get("initialization_seed") is not None:
                raise V014PhysicalRunnerError("MAIN provenance carries route initialisation")
            key_main = (receipt.episode_index, receipt.evaluation_seed)
            if key_main in seen_main:
                raise V014PhysicalRunnerError("duplicate MAIN receipt key")
            seen_main.add(key_main)
    aggregate = aggregate_five_arm(rows_by_arm)
    expected_route_rows = len(checked_spec.evaluation_seeds) * len(checked_spec.initialization_seeds)
    for arm in ROUTE_ARMS:
        if len(rows_by_arm[arm]) != expected_route_rows:
            raise V014PhysicalRunnerError(
                f"{arm} does not contain one row per evaluation seed and initialisation"
            )
        if {
            int(row.initialization_seed) for row in rows_by_arm[arm]
            if row.initialization_seed is not None
        } != set(checked_spec.initialization_seeds):
            raise V014PhysicalRunnerError(f"{arm} initialisation panel is incomplete")
        for seed in checked_spec.initialization_seeds:
            seed_rows = [
                row for row in rows_by_arm[arm]
                if row.initialization_seed == int(seed)
            ]
            if len(seed_rows) != len(checked_spec.evaluation_seeds):
                raise V014PhysicalRunnerError(
                    f"{arm} initialisation {seed} does not cover all episodes"
                )
            if {int(row.episode_index) for row in seed_rows} != expected_indices:
                raise V014PhysicalRunnerError(
                    f"{arm} initialisation {seed} episode panel is incomplete"
                )
            if {
                int(row.evaluation_seed) for row in seed_rows
            } != set(checked_spec.evaluation_seeds):
                raise V014PhysicalRunnerError(
                    f"{arm} initialisation {seed} evaluation-seed panel is incomplete"
                )
    if len(rows_by_arm[MAIN_ARM]) != len(checked_spec.evaluation_seeds):
        raise V014PhysicalRunnerError("MAIN does not contain one row per evaluation seed")
    if {int(row.episode_index) for row in rows_by_arm[MAIN_ARM]} != expected_indices:
        raise V014PhysicalRunnerError("MAIN episode index panel is incomplete")
    if {
        int(row.evaluation_seed) for row in rows_by_arm[MAIN_ARM]
    } != set(checked_spec.evaluation_seeds):
        raise V014PhysicalRunnerError("MAIN evaluation-seed panel is incomplete")
    aggregate["per_initialization"] = _per_initialization_aggregates(
        rows_by_arm,
        initialization_seeds=checked_spec.initialization_seeds,
    )
    expected_aggregate = run.get("aggregate")
    if not isinstance(expected_aggregate, Mapping):
        raise V014PhysicalRunnerError("run lacks aggregate")
    # Compare the deterministic JSON representations rather than relying on
    # approximate floats: both sides were built from the same finite receipts.
    if canonical_sha256(aggregate) != canonical_sha256(expected_aggregate):
        raise V014PhysicalRunnerError("recomputed aggregate disagrees with run")
    checkpoint_hashes = run.get("checkpoint_file_sha256s")
    if not isinstance(checkpoint_hashes, Mapping) or set(checkpoint_hashes) != set(ARMS):
        raise V014PhysicalRunnerError("checkpoint hash panel is incomplete")
    for arm in ARMS:
        checkpoint_path = destination / "checkpoints" / f"{arm.lower()}-episode-000100.json"
        if file_sha256(checkpoint_path) != checkpoint_hashes[arm]:
            raise V014PhysicalRunnerError(f"checkpoint hash mismatch for {arm}")
        checkpoint = _read_json(checkpoint_path, field=f"{arm} checkpoint")
        if checkpoint.get("schema") != PHYSICAL_CHECKPOINT_SCHEMA or checkpoint.get("arm") != arm:
            raise V014PhysicalRunnerError(f"checkpoint content mismatch for {arm}")
        if checkpoint.get("episode_index") != EVALUATION_EPISODES:
            raise V014PhysicalRunnerError(f"checkpoint cadence mismatch for {arm}")
    result = {
        "schema": VERIFY_SCHEMA,
        "runner_schema": PHYSICAL_RUNNER_SCHEMA,
        "status": "PASS_PHYSICAL_PLUMBING_INTEGRITY",
        "claim_ceiling": CLAIM_CEILING,
        "run_file_sha256": file_sha256(run_path),
        "prepare_file_sha256": file_sha256(destination / "prepare.json"),
        "episode_receipts_file_sha256": file_sha256(receipts_path),
        "episode_provenance_file_sha256": file_sha256(provenance_path),
        "arms": list(ARMS),
        "route_initialization_rows": {
            arm: len(rows_by_arm[arm]) for arm in ROUTE_ARMS
        },
        "main_rows": len(rows_by_arm[MAIN_ARM]),
        "ratio_of_sums_recomputed": True,
        "common_mask_single_argmax_contract": True,
        "paired_keyed_fading_contract": True,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "episode_training": False,
        "efficacy_claim": False,
        "preparation_schema": preparation["schema"],
    }
    digest = _write_once_json_strict(verify_path, result)
    return {**result, "verify_file_sha256": digest}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare", help="authenticate and seal a physical input panel")
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--gate-result", type=Path, required=True)
    prepare.add_argument("--gate-seal", type=Path, required=True)
    prepare.add_argument("--expected-gate-result-sha256", required=True)
    prepare.add_argument("--expected-gate-seal-sha256", required=True)
    prepare.add_argument("--checkpoint", action="append", required=True, metavar="SEED=PATH")
    prepare.add_argument("--initialization-seed", action="append", type=int, required=True)
    prepare.add_argument("--evaluation-seed", action="append", type=int, required=True,
                         help="repeat exactly 100 times from the later sealed contract")
    prepare.add_argument("--field-component", required=True,
                         help="later-sealed canonical keyed-fading component")
    verify = subparsers.add_parser("verify", help="verify a completed physical receipt directory")
    verify.add_argument("--run-dir", type=Path, required=True)
    return parser


def _parse_checkpoint_args(values: Sequence[str]) -> dict[int, Path]:
    output: dict[int, Path] = {}
    for value in values:
        if "=" not in value:
            raise V014PhysicalRunnerError("--checkpoint must use SEED=PATH")
        raw_seed, raw_path = value.split("=", 1)
        seed = _positive_int(int(raw_seed), field="checkpoint seed")
        if seed in output:
            raise V014PhysicalRunnerError("duplicate --checkpoint seed")
        output[seed] = Path(raw_path)
    return output


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "verify":
        print(json.dumps(verify_physical_evaluation(args.run_dir), indent=2, sort_keys=True))
        return 0
    seeds = tuple(int(value) for value in args.initialization_seed)
    checkpoint_paths = _parse_checkpoint_args(args.checkpoint)
    selection = authenticate_gate_selection(
        result_path=args.gate_result,
        seal_path=args.gate_seal,
        expected_result_sha256=args.expected_gate_result_sha256,
        expected_seal_sha256=args.expected_gate_seal_sha256,
        checkpoint_paths_by_initialization=checkpoint_paths,
        initialization_seeds=seeds,
    )
    spec = V014PhysicalEvaluationSpec(
        evaluation_seeds=tuple(int(value) for value in args.evaluation_seed),
        field_component=args.field_component,
        initialization_seeds=seeds,
    )
    print(json.dumps(prepare_physical_evaluation(output_dir=args.output, spec=spec, selection=selection), indent=2, sort_keys=True))
    return 0


__all__ = [
    "ARMS",
    "CLAIM_CEILING",
    "EVALUATION_EPISODES",
    "GATE_CHECKPOINT_SCHEMA",
    "GATE_RESULT_SCHEMA",
    "GATE_RESULT_SEAL_SCHEMA",
    "MAIN_ARM",
    "PHYSICAL_CHECKPOINT_SCHEMA",
    "PHYSICAL_RUNNER_SCHEMA",
    "PREPARE_SCHEMA",
    "REQUIRED_EVALUATION_SEEDS",
    "ROUTE_ARMS",
    "RUN_SCHEMA",
    "VERIFY_SCHEMA",
    "V014GateHeadPair",
    "V014GateSelection",
    "V014PhysicalAdapter",
    "V014PhysicalEpisode",
    "V014PhysicalEvaluationSpec",
    "V014PhysicalRunnerError",
    "authenticate_gate_selection",
    "canonical_sha256",
    "file_sha256",
    "prepare_physical_evaluation",
    "run_physical_evaluation",
    "verify_physical_evaluation",
]


if __name__ == "__main__":
    raise SystemExit(main())
