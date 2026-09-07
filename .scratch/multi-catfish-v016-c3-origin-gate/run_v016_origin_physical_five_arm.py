#!/usr/bin/env python3
"""Conditional V0.16-O physical five-arm adapter.

This module is intentionally a *future* execution seam.  Importing it does
not open a simulator, read TRAIN/TEST trajectories, or perform a learner
update.  A physical caller must first supply an authenticated
``PASS_ORIGIN_GATE`` result and its explicit rung-3000 checkpoint paths.

The V0.16 route decoder is origin-aware and context-conditioned at the C3
state boundary::

    FULL     = Q1 + Q2 + Q3(s12),   reference action = argmax(Q1 + Q2)
    DROP_C1  =      Q2 + Q3(s2),    reference action = argmax(Q2)
    DROP_C2  = Q1      + Q3(s1),    reference action = argmax(Q1)
    DROP_C3  = Q1 + Q2,             Q3 is not evaluated

Every route uses the same native Boolean mask and one final masked argmax.
``MAIN`` remains an independently supplied frozen legacy baseline and is not
decoded by this module.  The physical loop is exposed as an adapter method so
the later sealed five-arm runner can compose it with the existing V0.14
receipt/aggregation infrastructure; this file itself has no default launcher
or experiment side effect.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Protocol, TypeAlias

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
# ``HERE`` is the gate directory (not the Python file), so its repository is
# two directory levels above the file but one above the directory's parent.
REPO = HERE.parents[1]
for _path in (REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.algorithms.ee_axis_v014_head import (  # noqa: E402
    EEAxisV014HeadConfig,
    V014ActionSetQNetwork,
)
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.errors import MCRLContractError  # noqa: E402
from mcrl.runtime.ee_axis_ops3 import OPS3_KAPPA_BITS  # noqa: E402
from mcrl.runtime.ee_axis_ops3_live import (  # noqa: E402
    build_ops3_live_surfaces,
    project_ops3_anchor,
    snapshot_ops3_anchor,
)
from mcrl.runtime.ee_axis_state import encode_ee_axis_state  # noqa: E402
from mcrl.runtime.ee_axis_v015_c3_pivotal import (  # noqa: E402
    EEAxisV015C3PivotalLearner,
)
from mcrl.runtime.ee_axis_v016_c3_origin_state import (  # noqa: E402
    V016_C3_ORIGIN_GLOBAL_FEATURES,
    V016_C3_ORIGIN_LOCAL_FEATURES,
    V016_C3_ORIGIN_STATE_DIM,
    V016_C3_ORIGIN_STATE_SCHEMA,
    encode_ee_axis_v016_c3_origin_state,
)


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise V016PhysicalRunnerError(f"cannot import helper module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# The old evaluation seam contains only receipt dataclasses and ratio-of-sums
# aggregation.  It has no import-time simulator or training side effect.  We
# use it as a data dependency instead of copying/altering the V0.14 runner.
_V014_EVALUATION = _load_module(
    REPO / ".scratch" / "multi-catfish-v014-learner" / "run_v014_five_arm_evaluation.py",
    "mcrl_v016_v014_evaluation_receipts",
)
_V014_PHYSICAL = _load_module(
    REPO / ".scratch" / "multi-catfish-v014-learner" / "run_v014_physical_five_arm.py",
    "mcrl_v016_v014_physical_helpers",
)
_V016_SOURCE = _load_module(
    HERE / "run_v016_origin_source_shard.py",
    "mcrl_v016_origin_physical_source_helpers",
)


ACTION_DIM = 28
ROUTE_ARMS = ("FULL", "DROP_C1", "DROP_C2", "DROP_C3")
ARMS = (*ROUTE_ARMS, "MAIN")
MAIN_ARM = "MAIN"
ARM_CONTEXT: dict[str, int] = {
    "FULL": 12,
    "DROP_C1": 2,
    "DROP_C2": 1,
}
CONTEXT_CODES = (12, 1, 2)
INITIALIZATION_SEEDS = (2026111101, 2026111102, 2026111103)
SOURCE_LINEAGES = (2026092101, 2026092102, 2026092103)
LINEAGE_BY_INITIALIZATION = dict(zip(INITIALIZATION_SEEDS, SOURCE_LINEAGES, strict=True))
ORIGIN_GATE_RUNG = 3000
Q3_LOCAL_FEATURES = V016_C3_ORIGIN_LOCAL_FEATURES
Q3_GLOBAL_FEATURES = V016_C3_ORIGIN_GLOBAL_FEATURES
Q3_STATE_DIM = V016_C3_ORIGIN_STATE_DIM
Q3_STATE_SCHEMA = V016_C3_ORIGIN_STATE_SCHEMA

GATE_RESULT_SCHEMA = "multi-catfish-mcrl-v016-c3-origin-learnability-result-v1"
GATE_RECEIPT_SCHEMA = "multi-catfish-mcrl-v016-c3-origin-gate-receipt-v1"
GATE_CHECKPOINT_SCHEMA = "multi-catfish-mcrl-v016-c3-origin-learnability-checkpoint-v1"
GATE_RUNNER_SCHEMA = "multi-catfish-mcrl-v016-c3-origin-learnability-gate-v1"
GATE_DECISION = "PASS_ORIGIN_GATE"
GATE_CLAIM_CEILING = "TRAIN_VALIDATION_SOURCE_ONLY_NO_TRAJECTORY_EE_OR_EFFICACY_CLAIM"
PHYSICAL_RUNNER_SCHEMA = "multi-catfish-mcrl-v016-origin-physical-five-arm-v1"
PHYSICAL_CLAIM_CEILING = "TRAIN_DEVELOPMENT_EE_RECEIPTS_ONLY_NO_TEST_EFFICACY_CLAIM"


class V016PhysicalRunnerError(MCRLContractError):
    """A V0.16 physical adapter input crossed a frozen boundary."""


def file_sha256(path: str | Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V016PhysicalRunnerError(f"expected a regular file: {source}")
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
        raise V016PhysicalRunnerError(f"{field} must be a lowercase SHA-256")
    return value


def _read_json(path: str | Path, *, field: str) -> dict[str, Any]:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise V016PhysicalRunnerError(f"cannot read {field}: {source}") from error
    if not isinstance(payload, dict):
        raise V016PhysicalRunnerError(f"{field} must be a JSON object")
    return payload


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise V016PhysicalRunnerError(f"{field} must be a positive integer")
    result = int(value)
    if result <= 0:
        raise V016PhysicalRunnerError(f"{field} must be a positive integer")
    return result


def _torch_parameter_sha256(module: Any) -> str:
    if not hasattr(module, "state_dict"):
        raise V016PhysicalRunnerError("frozen network has no state_dict")
    digest = hashlib.sha256()
    for name, value in module.state_dict().items():
        tensor = value.detach().cpu()
        digest.update(str(name).encode("utf-8"))
        digest.update(str(tensor.dtype).encode("ascii"))
        digest.update(repr(tuple(tensor.shape)).encode("ascii"))
        digest.update(tensor.numpy().tobytes(order="C"))
    return digest.hexdigest()


def _optimizer_sha256(learner: Any) -> str:
    buffer = io.BytesIO()
    torch.save(learner.optimizer.state_dict(), buffer)
    return hashlib.sha256(buffer.getvalue()).hexdigest()


def _expected_q3_config() -> EEAxisV014HeadConfig:
    return EEAxisV014HeadConfig(
        action_dim=ACTION_DIM,
        local_feature_dim=Q3_LOCAL_FEATURES,
        global_feature_dim=Q3_GLOBAL_FEATURES,
        hidden_layers=(100, 50, 50),
        activation="tanh",
        learning_rate=0.001,
        kappa_bits=float(OPS3_KAPPA_BITS),
        beta=0.1,
    )


def _config_from_payload(value: object) -> EEAxisV014HeadConfig:
    if not isinstance(value, Mapping):
        raise V016PhysicalRunnerError("Q3 checkpoint config is missing")
    expected_keys = {
        "action_dim",
        "local_feature_dim",
        "global_feature_dim",
        "hidden_layers",
        "activation",
        "learning_rate",
        "kappa_bits",
        "beta",
    }
    if set(value) != expected_keys:
        raise V016PhysicalRunnerError("Q3 checkpoint config fields are noncanonical")
    try:
        config = EEAxisV014HeadConfig(
            action_dim=int(value["action_dim"]),
            local_feature_dim=int(value["local_feature_dim"]),
            global_feature_dim=int(value["global_feature_dim"]),
            hidden_layers=tuple(int(item) for item in value["hidden_layers"]),
            activation=str(value["activation"]),
            learning_rate=float(value["learning_rate"]),
            kappa_bits=float(value["kappa_bits"]),
            beta=float(value["beta"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise V016PhysicalRunnerError("Q3 checkpoint config is malformed") from error
    if config != _expected_q3_config() or config.state_dim != Q3_STATE_DIM:
        raise V016PhysicalRunnerError("Q3 checkpoint config is not the frozen B402 config")
    return config


@dataclass(frozen=True)
class V016OriginGateHead:
    """One frozen Q3 learner reconstructed from an authenticated rung-3000 file."""

    initialization_seed: int
    source_lineage: int
    checkpoint_path: Path
    checkpoint_sha256: str
    update_rung: int
    q3: EEAxisV015C3PivotalLearner
    q3_config: EEAxisV014HeadConfig

    def verify_frozen(self) -> None:
        if self.update_rung != ORIGIN_GATE_RUNG:
            raise V016PhysicalRunnerError("V0.16 physical Q3 must use rung 3000")
        if self.q3.config != _expected_q3_config():
            raise V016PhysicalRunnerError("selected Q3 config is not the frozen B402 config")
        if self.q3.config.state_dim != Q3_STATE_DIM:
            raise V016PhysicalRunnerError("selected Q3 state dimension is not 402")
        if self.q3.train_seed != self.initialization_seed:
            raise V016PhysicalRunnerError("selected Q3 train seed disagrees with panel")
        self.q3.q.eval()
        self.q3.q.requires_grad_(False)
        if any(parameter.requires_grad for parameter in self.q3.q.parameters()):
            raise V016PhysicalRunnerError("selected Q3 remains trainable")


@dataclass(frozen=True)
class V016OriginGateSelection:
    """Authenticated PASS panel for future physical evaluation."""

    result_path: Path
    receipt_path: Path
    result_sha256: str
    receipt_sha256: str
    contract_sha256: str
    deployment_rung: int
    initialization_seeds: tuple[int, ...]
    source_lineages: tuple[int, ...]
    heads_by_initialization: Mapping[int, V016OriginGateHead]

    def verify(self) -> None:
        if self.deployment_rung != ORIGIN_GATE_RUNG:
            raise V016PhysicalRunnerError("V0.16 physical panel is fixed to rung 3000")
        if self.initialization_seeds != INITIALIZATION_SEEDS:
            raise V016PhysicalRunnerError("V0.16 physical panel requires the three frozen inits")
        if self.source_lineages != SOURCE_LINEAGES:
            raise V016PhysicalRunnerError("V0.16 physical panel requires the three frozen lineages")
        if set(self.heads_by_initialization) != set(self.initialization_seeds):
            raise V016PhysicalRunnerError("gate Q3 panel does not match three inits")
        _digest(self.result_sha256, field="gate result sha256")
        _digest(self.receipt_sha256, field="gate receipt sha256")
        _digest(self.contract_sha256, field="gate contract sha256")
        for index, seed in enumerate(self.initialization_seeds):
            head = self.heads_by_initialization[int(seed)]
            if head.initialization_seed != int(seed):
                raise V016PhysicalRunnerError("gate head initialization metadata disagrees")
            if head.source_lineage != self.source_lineages[index]:
                raise V016PhysicalRunnerError("gate head lineage metadata disagrees")
            head.verify_frozen()


def _load_q3_checkpoint(
    checkpoint_path: Path,
    *,
    expected_sha256: str,
    expected_seed: int,
    expected_lineage: int,
    expected_contract_sha256: str,
) -> V016OriginGateHead:
    actual = file_sha256(checkpoint_path)
    if actual != expected_sha256:
        raise V016PhysicalRunnerError(
            f"V0.16 Q3 checkpoint hash mismatch for initialization {expected_seed}"
        )
    try:
        payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    except (OSError, EOFError, RuntimeError, TypeError, ValueError) as error:
        raise V016PhysicalRunnerError(f"cannot load V0.16 Q3 checkpoint: {checkpoint_path}") from error
    if not isinstance(payload, Mapping):
        raise V016PhysicalRunnerError("V0.16 Q3 checkpoint must be a mapping")
    for name, expected in (
        ("schema", GATE_CHECKPOINT_SCHEMA),
        ("runner_schema", GATE_RUNNER_SCHEMA),
        ("claim_ceiling", "TRAIN_VALIDATION_SOURCE_ONLY_NO_TRAJECTORY_EE_OR_EFFICACY_CLAIM"),
        ("contract_sha256", expected_contract_sha256),
        ("initialization_seed", expected_seed),
        ("source_lineage", expected_lineage),
        ("update_rung", ORIGIN_GATE_RUNG),
        ("test_split_opened", False),
        ("held_out_ee_evaluated", False),
        ("episode_training", False),
    ):
        if payload.get(name) != expected:
            raise V016PhysicalRunnerError(
                f"V0.16 Q3 checkpoint metadata mismatch: {name}"
            )
    q3_payload = payload.get("q3")
    if not isinstance(q3_payload, Mapping):
        raise V016PhysicalRunnerError("V0.16 checkpoint lacks Q3 learner state")
    config = _config_from_payload(q3_payload.get("config"))
    try:
        train_seed = _positive_int(q3_payload.get("train_seed"), field="Q3 train_seed")
        learner = EEAxisV015C3PivotalLearner(config, train_seed=train_seed, device="cpu")
        loaded_rung = learner.load_checkpoint_state(q3_payload)
    except (KeyError, TypeError, ValueError, MCRLContractError) as error:
        raise V016PhysicalRunnerError("malformed V0.16 Q3 learner state") from error
    if train_seed != expected_seed or loaded_rung != ORIGIN_GATE_RUNG:
        raise V016PhysicalRunnerError("V0.16 Q3 learner seed/rung disagrees with panel")
    head = V016OriginGateHead(
        initialization_seed=int(expected_seed),
        source_lineage=int(expected_lineage),
        checkpoint_path=checkpoint_path,
        checkpoint_sha256=actual,
        update_rung=loaded_rung,
        q3=learner,
        q3_config=config,
    )
    head.verify_frozen()
    return head


def authenticate_origin_gate_selection(
    *,
    result_path: str | Path,
    receipt_path: str | Path,
    expected_result_sha256: str,
    expected_receipt_sha256: str,
    checkpoint_paths_by_initialization: Mapping[int, str | Path],
) -> V016OriginGateSelection:
    """Authenticate the only result allowed to unlock a future physical run.

    The checkpoint paths are explicit inputs.  The loader never searches a
    mutable directory and never accepts a result merely because it contains a
    truthy status field: the result, receipt, all three lineages/inits, every
    rung-3000 hash, and each nested learner configuration must agree.
    """

    result_file = Path(result_path)
    receipt_file = Path(receipt_path)
    expected_result = _digest(expected_result_sha256, field="expected result sha256")
    expected_receipt = _digest(expected_receipt_sha256, field="expected receipt sha256")
    actual_result = file_sha256(result_file)
    actual_receipt = file_sha256(receipt_file)
    if actual_result != expected_result:
        raise V016PhysicalRunnerError("gate result does not match supplied digest")
    if actual_receipt != expected_receipt:
        raise V016PhysicalRunnerError("gate receipt does not match supplied digest")
    result = _read_json(result_file, field="V0.16 origin gate result")
    receipt = _read_json(receipt_file, field="V0.16 origin gate receipt")
    if result.get("schema") != GATE_RESULT_SCHEMA:
        raise V016PhysicalRunnerError("gate result schema is not V0.16 origin gate")
    if receipt.get("schema") != GATE_RECEIPT_SCHEMA:
        raise V016PhysicalRunnerError("gate receipt schema is not V0.16 origin gate")
    if result.get("decision") != GATE_DECISION or result.get("passed") is not True:
        raise V016PhysicalRunnerError("physical evaluation requires PASS_ORIGIN_GATE")
    if receipt.get("decision") != GATE_DECISION:
        raise V016PhysicalRunnerError("gate receipt does not record PASS_ORIGIN_GATE")
    if receipt.get("result_sha256") != actual_result:
        raise V016PhysicalRunnerError("gate receipt does not authenticate result bytes")
    if receipt.get("claim_ceiling") != GATE_CLAIM_CEILING:
        raise V016PhysicalRunnerError("gate receipt claim ceiling drifted")
    if result.get("contract_sha256") != receipt.get("contract_sha256", result.get("contract_sha256")):
        # Current gate receipts do not repeat contract_sha256; if a future
        # receipt adds it, it must agree.  This conditional keeps the current
        # receipt format strict without inventing a second authority field.
        if "contract_sha256" in receipt:
            raise V016PhysicalRunnerError("gate receipt contract digest disagrees")
    contract_sha256 = _digest(result.get("contract_sha256"), field="gate contract sha256")
    if result.get("q3_state_schema") != Q3_STATE_SCHEMA or result.get("q3_state_dim") != Q3_STATE_DIM:
        raise V016PhysicalRunnerError("gate result does not select the 402-D V0.16 state")
    if tuple(result.get("source_lineages", ())) != SOURCE_LINEAGES:
        raise V016PhysicalRunnerError("gate result lineages are not the frozen three")
    if tuple(result.get("initialization_seeds", ())) != INITIALIZATION_SEEDS:
        raise V016PhysicalRunnerError("gate result initializations are not the frozen three")
    if ORIGIN_GATE_RUNG not in tuple(result.get("update_rungs", ())):
        raise V016PhysicalRunnerError("gate result lacks rung 3000")
    if result.get("next_authority") != "AUTHORIZE_100EP_FIVE_ARM_PREREG_ONLY":
        raise V016PhysicalRunnerError("gate result does not authorize the physical preregistration")
    for name in ("test_split_opened", "held_out_ee_evaluated", "episode_training"):
        if bool(result.get(name, True)):
            raise V016PhysicalRunnerError("gate result crossed a forbidden boundary")
    per_pass = result.get("per_initialization_pass")
    if not isinstance(per_pass, Mapping) or set(per_pass) != {str(seed) for seed in INITIALIZATION_SEEDS}:
        raise V016PhysicalRunnerError("gate result pass panel is not the three-init closure")
    if any(value is not True for value in per_pass.values()):
        raise V016PhysicalRunnerError("all three initialization gates must pass")
    reports = result.get("reports")
    if not isinstance(reports, Mapping):
        raise V016PhysicalRunnerError("gate result lacks per-initialization reports")
    checkpoint_paths = {int(seed): Path(path) for seed, path in checkpoint_paths_by_initialization.items()}
    if set(checkpoint_paths) != set(INITIALIZATION_SEEDS):
        raise V016PhysicalRunnerError("explicit checkpoint panel must contain exactly three inits")
    heads: dict[int, V016OriginGateHead] = {}
    for index, seed in enumerate(INITIALIZATION_SEEDS):
        report = reports.get(str(seed))
        if not isinstance(report, Mapping):
            raise V016PhysicalRunnerError(f"gate report is missing initialization {seed}")
        if int(report.get("source_lineage", -1)) != SOURCE_LINEAGES[index]:
            raise V016PhysicalRunnerError("gate report lineage disagrees with frozen panel")
        rungs = report.get("rungs")
        if not isinstance(rungs, Mapping):
            raise V016PhysicalRunnerError("gate report lacks rung map")
        rung_report = rungs.get(str(ORIGIN_GATE_RUNG))
        if not isinstance(rung_report, Mapping) or rung_report.get("decision", {}).get("passed") is not True:
            raise V016PhysicalRunnerError(f"initialization {seed} lacks a passing rung-3000 report")
        expected_checkpoint = _digest(
            rung_report.get("checkpoint_sha256"),
            field=f"rung-3000 checkpoint sha256 for {seed}",
        )
        heads[int(seed)] = _load_q3_checkpoint(
            checkpoint_paths[int(seed)],
            expected_sha256=expected_checkpoint,
            expected_seed=int(seed),
            expected_lineage=SOURCE_LINEAGES[index],
            expected_contract_sha256=contract_sha256,
        )
    selection = V016OriginGateSelection(
        result_path=result_file,
        receipt_path=receipt_file,
        result_sha256=actual_result,
        receipt_sha256=actual_receipt,
        contract_sha256=contract_sha256,
        deployment_rung=ORIGIN_GATE_RUNG,
        initialization_seeds=INITIALIZATION_SEEDS,
        source_lineages=SOURCE_LINEAGES,
        heads_by_initialization=heads,
    )
    selection.verify()
    return selection


# Short aliases make the future CLI seam easy to discover without weakening
# the canonical function name above.
authenticate_gate_selection = authenticate_origin_gate_selection
load_origin_gate_selection = authenticate_origin_gate_selection


def _surface(network: Any, states: object, masks: object, *, field: str) -> np.ndarray:
    values = np.asarray(states, dtype=np.float32)
    legal = np.asarray(masks)
    if values.ndim != 2 or legal.dtype != np.bool_ or legal.shape != (values.shape[0], ACTION_DIM):
        raise V016PhysicalRunnerError(f"{field} state/mask input is malformed")
    if not np.all(np.isfinite(values)) or not np.all(np.any(legal, axis=1)):
        raise V016PhysicalRunnerError(f"{field} state/mask input is invalid")
    with torch.no_grad():
        output = network(
            torch.tensor(values, dtype=torch.float32),
            torch.tensor(legal, dtype=torch.bool),
        )
    result = np.asarray(output.detach().cpu().numpy(), dtype=np.float64)
    if result.shape != legal.shape or not np.all(np.isfinite(result)):
        raise V016PhysicalRunnerError(f"{field} surface is malformed")
    return result


def _validate_surfaces(
    q1_values: object,
    q2_values: object,
    masks: object,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    legal = np.asarray(masks)
    if legal.dtype != np.bool_ or legal.ndim != 2 or legal.shape[1] != ACTION_DIM:
        raise V016PhysicalRunnerError("native safe mask must be Boolean shape (U,28)")
    if not np.all(np.any(legal, axis=1)):
        raise V016PhysicalRunnerError("every user must have a legal native action")
    q1 = np.asarray(q1_values, dtype=np.float64)
    q2 = np.asarray(q2_values, dtype=np.float64)
    if q1.shape != legal.shape or q2.shape != legal.shape:
        raise V016PhysicalRunnerError("Q1/Q2 surfaces are not action aligned")
    if not np.all(np.isfinite(q1)) or not np.all(np.isfinite(q2)):
        raise V016PhysicalRunnerError("Q1/Q2 surfaces contain non-finite values")
    return q1, q2, np.array(legal, dtype=np.bool_, copy=True, order="C")


def _masked_argmax(scores: np.ndarray, masks: np.ndarray) -> np.ndarray:
    if scores.shape != masks.shape or not np.all(np.isfinite(scores)):
        raise V016PhysicalRunnerError("decoder score surface is malformed")
    return np.argmax(np.where(masks, scores, -np.inf), axis=1).astype(np.int64)


@dataclass(frozen=True)
class V016DecodedAnchor:
    """Auditable result of one V0.16 per-anchor route decode."""

    arm: str
    context_code: int | None
    reference_actions: np.ndarray
    scores: np.ndarray
    selected_actions: np.ndarray
    q3_evaluated: bool
    q3_values: np.ndarray | None = None

    def verify(self, masks: object) -> None:
        legal = np.asarray(masks)
        if legal.dtype != np.bool_ or legal.shape != self.scores.shape:
            raise V016PhysicalRunnerError("decoded anchor mask is malformed")
        if self.arm not in ROUTE_ARMS:
            raise V016PhysicalRunnerError("decoded anchor contains an unknown route arm")
        if self.arm == "DROP_C3":
            if self.q3_evaluated or self.q3_values is not None or self.context_code is not None:
                raise V016PhysicalRunnerError("DROP_C3 must not evaluate or carry Q3/context state")
        else:
            if not self.q3_evaluated or self.context_code != ARM_CONTEXT[self.arm]:
                raise V016PhysicalRunnerError("route Q3 context is missing or wrong")
            if self.q3_values is None or self.q3_values.shape != self.scores.shape:
                raise V016PhysicalRunnerError("route Q3 surface is missing")
        if self.reference_actions.shape != (self.scores.shape[0],):
            raise V016PhysicalRunnerError("decoded reference action vector is malformed")
        if self.selected_actions.shape != self.reference_actions.shape:
            raise V016PhysicalRunnerError("decoded selected action vector is malformed")
        rows = np.arange(self.scores.shape[0])
        if np.any(self.reference_actions < 0) or np.any(~legal[rows, self.reference_actions]):
            raise V016PhysicalRunnerError("decoded reference action is illegal")
        if np.any(self.selected_actions < 0) or np.any(~legal[rows, self.selected_actions]):
            raise V016PhysicalRunnerError("decoded selected action is illegal")
        if not np.all(np.isfinite(self.scores)):
            raise V016PhysicalRunnerError("decoded score surface is non-finite")


class Q3Provider(Protocol):
    def __call__(self, *, context_code: int, reference_actions: np.ndarray) -> object:
        """Return Q3 values for the exact V0.16 origin-aware state."""


class V016OriginAnchorDecoder:
    """Pure V0.16 route decoder; it has no simulator or learner side effect."""

    @staticmethod
    def context_reference_actions(
        q1_values: object, q2_values: object, masks: object, context_code: int
    ) -> np.ndarray:
        q1, q2, legal = _validate_surfaces(q1_values, q2_values, masks)
        code = int(context_code)
        if code == 12:
            base = q1 + q2
        elif code == 1:
            base = q1
        elif code == 2:
            base = q2
        else:
            raise V016PhysicalRunnerError(f"unknown V0.16 origin context: {context_code}")
        return _masked_argmax(base, legal)

    def decode(
        self,
        *,
        arm: str,
        q1_values: object,
        q2_values: object,
        masks: object,
        q3_provider: Q3Provider | None = None,
    ) -> V016DecodedAnchor:
        if arm not in ROUTE_ARMS:
            raise V016PhysicalRunnerError("decoder accepts only route arms; MAIN is external")
        q1, q2, legal = _validate_surfaces(q1_values, q2_values, masks)
        if arm == "DROP_C3":
            # Deliberately do not invoke q3_provider and do not manufacture a
            # zero Q3 surface: the no-Q3 call is part of the route contract.
            scores = q1 + q2
            selected = _masked_argmax(scores, legal)
            result = V016DecodedAnchor(
                arm=arm,
                context_code=None,
                reference_actions=_masked_argmax(scores, legal),
                scores=scores,
                selected_actions=selected,
                q3_evaluated=False,
                q3_values=None,
            )
            result.verify(legal)
            return result
        if q3_provider is None or not callable(q3_provider):
            raise V016PhysicalRunnerError(f"{arm} requires a V0.16 Q3 provider")
        context = ARM_CONTEXT[arm]
        reference = self.context_reference_actions(q1, q2, legal, context)
        raw_q3 = q3_provider(context_code=context, reference_actions=reference)
        q3 = np.asarray(raw_q3, dtype=np.float64)
        if q3.shape != legal.shape or not np.all(np.isfinite(q3)):
            raise V016PhysicalRunnerError("Q3 provider returned a malformed surface")
        scores = (q1 + q2) + q3
        if arm == "DROP_C1":
            scores = q2 + q3
        elif arm == "DROP_C2":
            scores = q1 + q3
        selected = _masked_argmax(scores, legal)
        result = V016DecodedAnchor(
            arm=arm,
            context_code=context,
            reference_actions=reference,
            scores=scores,
            selected_actions=selected,
            q3_evaluated=True,
            q3_values=q3,
        )
        result.verify(legal)
        return result

    decode_anchor = decode


Q1Loader: TypeAlias = Callable[[int], tuple[Any, Mapping[str, Any]]]
Q2Loader: TypeAlias = Callable[[int], tuple[Any, Mapping[str, Any]]]
EnvironmentFactory: TypeAlias = Callable[[Any, int], Any]
RngFactory: TypeAlias = Callable[[int], Sequence[Any]]
FieldFactory: TypeAlias = Callable[[str, int], Any]


@dataclass(frozen=True)
class V016OriginPhysicalEpisode:
    """V0.14-compatible receipt plus V0.16 route provenance."""

    receipt: Any
    provenance: Mapping[str, Any]

    def as_dict(self) -> dict[str, Any]:
        payload = self.receipt.as_dict()
        payload["provenance"] = dict(self.provenance)
        return payload


class V016OriginPhysicalAdapter:
    """Compose V0.14 physical helpers with the V0.16 origin decoder.

    Construction is side-effect free.  ``evaluate_route_episode`` is the
    deepest physical seam: the later sealed runner supplies its archive,
    Q1/Q2 loaders, RNG factory, and keyed fading field.  No method here can
    update Q1/Q2/Q3; all loaded networks are switched to eval/no-grad mode.
    """

    def __init__(
        self,
        *,
        selection: V016OriginGateSelection,
        archive: Any,
        q1_loader: Q1Loader,
        q2_loader: Q2Loader,
        make_environment: EnvironmentFactory,
        rng_factory: RngFactory,
        field_factory: FieldFactory | None = None,
        users: int = 100,
        steps: int = 10,
        kappa_bits: float = float(OPS3_KAPPA_BITS),
    ) -> None:
        selection.verify()
        if not callable(q1_loader) or not callable(q2_loader):
            raise V016PhysicalRunnerError("Q1/Q2 loaders must be callable")
        if not callable(make_environment) or not callable(rng_factory):
            raise V016PhysicalRunnerError("environment/RNG factories must be callable")
        if field_factory is not None and not callable(field_factory):
            raise V016PhysicalRunnerError("field_factory must be callable")
        if users != 100 or steps != 10:
            raise V016PhysicalRunnerError("V0.16 physical episodes use 100 users and ten steps")
        if not math.isfinite(float(kappa_bits)) or float(kappa_bits) <= 0.0:
            raise V016PhysicalRunnerError("kappa_bits must be finite and positive")
        self.selection = selection
        self.archive = archive
        self.q1_loader = q1_loader
        self.q2_loader = q2_loader
        self.make_environment = make_environment
        self.rng_factory = rng_factory
        self.field_factory = field_factory or (
            lambda component, seed: KeyedFadingField.from_components(component, seed)
        )
        self.users = int(users)
        self.steps = int(steps)
        self.kappa_bits = float(kappa_bits)
        self.decoder = V016OriginAnchorDecoder()
        self._q1: dict[int, tuple[Any, Mapping[str, Any]]] = {}
        self._q2: dict[int, tuple[Any, Mapping[str, Any]]] = {}

    def field_for(self, *, field_component: str, evaluation_seed: int) -> Any:
        _positive_int(evaluation_seed, field="evaluation_seed")
        field = self.field_factory(field_component, int(evaluation_seed))
        if not isinstance(field, KeyedFadingField):
            raise V016PhysicalRunnerError("field_factory must return KeyedFadingField")
        expected = KeyedFadingField.from_components(field_component, int(evaluation_seed))
        if field.root_digest != expected.root_digest:
            raise V016PhysicalRunnerError("field_factory did not produce canonical field")
        return field

    def _load_q1(self, initialization_seed: int) -> tuple[Any, Mapping[str, Any]]:
        seed = int(initialization_seed)
        if seed not in self.selection.heads_by_initialization:
            raise V016PhysicalRunnerError("Q1 initialization is outside the authenticated panel")
        if seed not in self._q1:
            loaded = self.q1_loader(LINEAGE_BY_INITIALIZATION[seed])
            if not isinstance(loaded, tuple) or len(loaded) != 2 or not isinstance(loaded[1], Mapping):
                raise V016PhysicalRunnerError("q1_loader must return (network, receipt)")
            network, receipt = loaded
            if not callable(getattr(network, "parameters", None)):
                raise V016PhysicalRunnerError("Q1 loader returned a non-network")
            network.eval()
            network.requires_grad_(False)
            if any(parameter.requires_grad for parameter in network.parameters()):
                raise V016PhysicalRunnerError("frozen Q1 remains trainable")
            claimed = receipt.get("parameter_sha256")
            if claimed is not None and _digest(claimed, field="Q1 parameter sha256") != _torch_parameter_sha256(network):
                raise V016PhysicalRunnerError("Q1 receipt does not authenticate network")
            self._q1[seed] = (network, receipt)
        return self._q1[seed]

    def _load_q2(self, initialization_seed: int) -> tuple[Any, Mapping[str, Any]]:
        seed = int(initialization_seed)
        if seed not in self.selection.heads_by_initialization:
            raise V016PhysicalRunnerError("Q2 initialization is outside the authenticated panel")
        if seed not in self._q2:
            loaded = self.q2_loader(LINEAGE_BY_INITIALIZATION[seed])
            if not isinstance(loaded, tuple) or len(loaded) != 2 or not isinstance(loaded[1], Mapping):
                raise V016PhysicalRunnerError("q2_loader must return (network, receipt)")
            network, receipt = loaded
            if not isinstance(network, V014ActionSetQNetwork):
                raise V016PhysicalRunnerError("Q2 loader must return V014ActionSetQNetwork")
            expected = EEAxisV014HeadConfig(
                action_dim=ACTION_DIM,
                local_feature_dim=16,
                global_feature_dim=0,
                hidden_layers=(100, 50, 50),
                activation="tanh",
                learning_rate=0.001,
                kappa_bits=self.kappa_bits,
                beta=0.1,
            )
            if network.config != expected:
                raise V016PhysicalRunnerError("Q2 loader returned a noncanonical V0.14 config")
            network.eval()
            network.requires_grad_(False)
            if any(parameter.requires_grad for parameter in network.parameters()):
                raise V016PhysicalRunnerError("frozen Q2 remains trainable")
            claimed = receipt.get("parameter_sha256")
            if claimed is not None and _digest(claimed, field="Q2 parameter sha256") != _torch_parameter_sha256(network):
                raise V016PhysicalRunnerError("Q2 receipt does not authenticate network")
            self._q2[seed] = (network, receipt)
        return self._q2[seed]

    def evaluate_route_episode(
        self,
        *,
        arm: str,
        episode_index: int,
        evaluation_seed: int,
        initialization_seed: int,
        field: Any,
    ) -> V016OriginPhysicalEpisode:
        """Run one route episode with V0.16 origin-aware C3 decoding.

        This method is deliberately not called by the synthetic test suite;
        it is only the future composition seam after a separate physical
        contract is sealed.  The exact five-arm persistence/checkpoint writer
        remains the V0.14 runner's integration responsibility.
        """

        if arm not in ROUTE_ARMS:
            raise V016PhysicalRunnerError("physical route episode requires a route arm")
        _positive_int(episode_index, field="episode_index")
        _positive_int(evaluation_seed, field="evaluation_seed")
        _positive_int(initialization_seed, field="initialization_seed")
        if field is None:
            raise V016PhysicalRunnerError("paired keyed fading field cannot be None")
        q1, q1_receipt = self._load_q1(initialization_seed)
        q2, q2_receipt = self._load_q2(initialization_seed)
        head = self.selection.heads_by_initialization[int(initialization_seed)]
        q1_before = _torch_parameter_sha256(q1)
        q2_before = _torch_parameter_sha256(q2)
        q3_before = _torch_parameter_sha256(head.q3.q)
        q3_optimizer_before = _optimizer_sha256(head.q3)
        environment = self.make_environment(self.archive, self.users)
        step_environment = _V014_PHYSICAL._set_fading_field(environment, field)
        rngs = tuple(self.rng_factory(int(evaluation_seed)))
        if len(rngs) < 2:
            raise V016PhysicalRunnerError("rng_factory must return environment and mobility RNGs")
        env_rng = rngs[0]
        observation = _V014_PHYSICAL._reset_environment(environment, rngs)
        interval_s = float(step_environment.driver.config.ephemeris.time_step_s)
        if not math.isfinite(interval_s) or interval_s <= 0.0:
            raise V016PhysicalRunnerError("decision interval is not finite and positive")
        total_bits = 0.0
        total_energy = 0.0
        served_steps = 0
        action_digest = hashlib.sha256()
        with torch.no_grad():
            for step_index in range(self.steps):
                native = encode_ee_axis_state(step_environment, observation)
                masks = np.asarray(native.action_masks, dtype=np.bool_)
                q1_values = _surface(q1, native.state_matrix, masks, field="Q1")
                q1_reference = np.argmax(np.where(masks, q1_values, -np.inf), axis=1).astype(np.int64)
                anchor = snapshot_ops3_anchor(step_environment, observation)
                projection = project_ops3_anchor(anchor)
                q2_carrier = build_ops3_live_surfaces(anchor, projection, q1_reference)
                q2_state = _V014_PHYSICAL._EVALUATION.encode_ee_axis_v014_q2_states(q2_carrier)
                if not np.array_equal(q2_state.action_masks, masks):
                    raise V016PhysicalRunnerError("Q2 carrier mask differs from native mask")
                q2_values = _surface(q2, q2_state.state_matrix, q2_state.action_masks, field="Q2")
                required_power, opening = _V016_SOURCE.current_required_power_and_opening(
                    current_gain_linear=anchor.current_gain_linear,
                    segment_start_gain_linear=anchor.segment_start_gain_linear,
                    action_masks=masks,
                    pmax_w=_V016_SOURCE.BEAM_POWER_MAX_W,
                    p0_w=_V016_SOURCE.SEGMENT_START_POWER_W,
                )

                def q3_provider(*, context_code: int, reference_actions: np.ndarray) -> np.ndarray:
                    state = encode_ee_axis_v016_c3_origin_state(
                        step_environment,
                        observation,
                        reference_actions=reference_actions,
                        current_required_power_w=required_power,
                        opening_service_feasible=opening,
                        interval_s=interval_s,
                        kappa_bits=self.kappa_bits,
                        pmax_w=_V016_SOURCE.BEAM_POWER_MAX_W,
                    )
                    if state.state_matrix.shape != (self.users, Q3_STATE_DIM):
                        raise V016PhysicalRunnerError("V0.16 Q3 state is not 402-D")
                    return head.q3.q_values(state.state_matrix, state.action_masks)

                decoded = self.decoder.decode(
                    arm=arm,
                    q1_values=q1_values,
                    q2_values=q2_values,
                    masks=masks,
                    q3_provider=None if arm == "DROP_C3" else q3_provider,
                )
                _V014_PHYSICAL._action_trace_update(action_digest, decoded.selected_actions)
                result = environment.step(decoded.selected_actions, env_rng)
                outcome = _V014_PHYSICAL._last_outcome(environment, result)
                rates = np.asarray(getattr(outcome, "link_rate_bps", None), dtype=np.float64)
                power = float(getattr(outcome, "system_power_w", np.nan))
                if rates.shape != (self.users,) or not np.all(np.isfinite(rates)) or np.any(rates < 0.0):
                    raise V016PhysicalRunnerError("canonical link-rate outcome is malformed")
                if not math.isfinite(power) or power <= 0.0:
                    raise V016PhysicalRunnerError("canonical system power must be positive")
                total_bits += interval_s * math.fsum(float(value) for value in rates)
                total_energy += interval_s * power
                served_steps += int(getattr(getattr(outcome, "resolution", None), "served_count", 0))
                if step_index != self.steps - 1:
                    if bool(getattr(result, "done", False)):
                        raise V016PhysicalRunnerError("episode terminated before ten steps")
                    observation = _V014_PHYSICAL._observation_after_step(environment, outcome)
                elif not bool(getattr(result, "done", False)):
                    raise V016PhysicalRunnerError("canonical episode did not terminate at ten steps")
        if _torch_parameter_sha256(q1) != q1_before or _torch_parameter_sha256(q2) != q2_before:
            raise V016PhysicalRunnerError("physical evaluation mutated frozen Q1/Q2")
        if (
            _torch_parameter_sha256(head.q3.q) != q3_before
            or _optimizer_sha256(head.q3) != q3_optimizer_before
        ):
            raise V016PhysicalRunnerError("physical evaluation mutated frozen Q3/optimizer")
        receipt = _V014_EVALUATION.V014EpisodeReceipt(
            arm=arm,
            episode_index=int(episode_index),
            evaluation_seed=int(evaluation_seed),
            total_bits=float(total_bits),
            total_energy_j=float(total_energy),
            decision_count=self.users * self.steps,
            served_user_steps=int(served_steps),
            initialization_seed=int(initialization_seed),
            world_seed=int(evaluation_seed),
        )
        provenance = {
            "runner_schema": PHYSICAL_RUNNER_SCHEMA,
            "arm": arm,
            "context_code": None if arm == "DROP_C3" else ARM_CONTEXT[arm],
            "initialization_seed": int(initialization_seed),
            "source_lineage": LINEAGE_BY_INITIALIZATION[int(initialization_seed)],
            "evaluation_seed": int(evaluation_seed),
            "field_root_digest": getattr(field, "root_digest", None),
            "gate_result_sha256": self.selection.result_sha256,
            "gate_receipt_sha256": self.selection.receipt_sha256,
            "deployment_rung": self.selection.deployment_rung,
            "q1_parameter_sha256": q1_receipt.get("parameter_sha256"),
            "q2_parameter_sha256": q2_receipt.get("parameter_sha256"),
            "q3_checkpoint_sha256": head.checkpoint_sha256,
            "q3_state_schema": Q3_STATE_SCHEMA,
            "q3_state_dim": Q3_STATE_DIM,
            "evaluation_split": "TRAIN",
            "test_split_opened": False,
            "held_out_ee_evaluated": False,
            "episode_training": False,
        }
        return V016OriginPhysicalEpisode(receipt=receipt, provenance=provenance)


__all__ = [
    "ACTION_DIM",
    "ARMS",
    "ARM_CONTEXT",
    "CONTEXT_CODES",
    "GATE_CHECKPOINT_SCHEMA",
    "GATE_DECISION",
    "GATE_RECEIPT_SCHEMA",
    "GATE_RESULT_SCHEMA",
    "GATE_RUNNER_SCHEMA",
    "INITIALIZATION_SEEDS",
    "LINEAGE_BY_INITIALIZATION",
    "MAIN_ARM",
    "PHYSICAL_CLAIM_CEILING",
    "PHYSICAL_RUNNER_SCHEMA",
    "Q3_STATE_DIM",
    "Q3_STATE_SCHEMA",
    "ORIGIN_GATE_RUNG",
    "ROUTE_ARMS",
    "SOURCE_LINEAGES",
    "V016DecodedAnchor",
    "V016OriginAnchorDecoder",
    "V016OriginGateHead",
    "V016OriginGateSelection",
    "V016OriginPhysicalAdapter",
    "V016OriginPhysicalEpisode",
    "V016PhysicalRunnerError",
    "authenticate_gate_selection",
    "authenticate_origin_gate_selection",
    "file_sha256",
    "load_origin_gate_selection",
]
