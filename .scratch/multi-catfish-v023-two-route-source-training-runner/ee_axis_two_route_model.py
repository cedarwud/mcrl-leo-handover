"""V0.23 C1/C2-only model built from the existing Q1 and Q2 constructors."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import asdict, dataclass
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.algorithms.ee_axis_action_shared import (
    ActionSharedQNetwork,
    EEAxisActionSharedConfig,
)
from mcrl.algorithms.ee_axis_lcsrs_three_route import (
    DetachedQ12Snapshot,
    LCSRS_THREE_ROUTE_ALGORITHM,
    _array_digest,
    _q12_model_digest,
)
from mcrl.algorithms.ee_axis_v014_head import (
    EEAxisV014HeadConfig,
    V014ActionSetQNetwork,
)
from mcrl.errors import MCRLContractError
from mcrl.runtime.finiteness import assert_finite_parameters


TWO_ROUTE_CHECKPOINT_SCHEMA = (
    "multi-catfish-mcrl-v023-c1c2-successor-two-route-checkpoint-v1"
)
TWO_ROUTE_ALGORITHM = "multi-catfish-mcrl-v023-c1c2-successor-two-route"
ROUTES = ("C1", "C2")
FORMAL_TRAIN_SEED = 2927175120652069826
FROZEN_MODEL_CONFIG_SHA256 = (
    "9eafcd184bd0ec015498832be61b5c95a71373e98f63ab804c9654775a8b1d5d"
)
FROZEN_MODEL_CONFIG_PATH = (
    REPO
    / ".scratch/multi-catfish-v023-c1c2-successor/"
    "V023-C1C2-SUCCESSOR-MODEL-CONFIG.json"
)


def _authenticated_frozen_records() -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        payload_bytes = FROZEN_MODEL_CONFIG_PATH.read_bytes()
        if sha256(payload_bytes).hexdigest() != FROZEN_MODEL_CONFIG_SHA256:
            raise RuntimeError("frozen successor model-config digest drifted")
        payload = json.loads(payload_bytes.decode("ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError("frozen successor model-config is unavailable") from error
    if not isinstance(payload, Mapping) or set(payload) != {"q1", "q2"}:
        raise RuntimeError("frozen successor model-config must contain only Q1/Q2")
    records: list[dict[str, Any]] = []
    for route, tuple_fields in (("q1", ("hidden_layers", "loss_weights")),
                                ("q2", ("hidden_layers",))):
        record = dict(payload[route])
        for field in tuple_fields:
            if isinstance(record.get(field), list):
                record[field] = tuple(record[field])
        records.append(record)
    return records[0], records[1]


FROZEN_Q1_CONFIG, FROZEN_Q2_CONFIG = _authenticated_frozen_records()


class EEAxisTwoRouteError(MCRLContractError):
    """The C1/C2-only model or checkpoint contract was violated."""


def _torch_bytes(value: object) -> bytes:
    stream = BytesIO()
    torch.save(value, stream)
    return stream.getvalue()


def _state_digest(value: object) -> str:
    return sha256(_torch_bytes(value)).hexdigest()


def _contains_q3(value: object) -> bool:
    if isinstance(value, Mapping):
        return any(str(key).upper() == "Q3" or _contains_q3(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return any(_contains_q3(item) for item in value)
    return isinstance(value, str) and value.upper() == "C3"


@dataclass(frozen=True, slots=True)
class EEAxisTwoRouteConfig:
    """Frozen Q1 228-D and Q2 448-D V0.14 OPS-3 configuration."""

    q1: EEAxisActionSharedConfig
    q2: EEAxisV014HeadConfig

    def __post_init__(self) -> None:
        if not isinstance(self.q1, EEAxisActionSharedConfig):
            raise TypeError("q1 must be EEAxisActionSharedConfig")
        if not isinstance(self.q2, EEAxisV014HeadConfig):
            raise TypeError("q2 must be EEAxisV014HeadConfig")
        if asdict(self.q1) != FROZEN_Q1_CONFIG:
            raise ValueError("Q1 must equal the frozen authenticated Q1 record")
        if asdict(self.q2) != FROZEN_Q2_CONFIG or self.q2.state_dim != 448:
            raise ValueError("Q2 must equal the frozen authenticated Q2 record")


def _finite_optimizer_tree(value: object) -> bool:
    if isinstance(value, torch.Tensor):
        return bool(torch.all(torch.isfinite(value)).item())
    if isinstance(value, Mapping):
        return all(_finite_optimizer_tree(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(_finite_optimizer_tree(item) for item in value)
    if isinstance(value, (float, np.floating)):
        return bool(np.isfinite(value))
    return True


def deploy_q12_action(
    q1_values: object,
    q2_values: object,
    action_masks: object,
) -> np.ndarray:
    """Apply the current carrier's float64 Q1+Q2 masked argmax exactly.

    NumPy ``argmax`` supplies the fixed lowest-action-index tie handling.
    Empty legal rows are rejected, matching the physical carrier.
    """

    q1 = np.asarray(q1_values, dtype=np.float64)
    q2 = np.asarray(q2_values, dtype=np.float64)
    masks = np.asarray(action_masks)
    if q1.ndim != 2 or q1.shape[1] != 28 or q2.shape != q1.shape:
        raise EEAxisTwoRouteError("Q1 and Q2 score surfaces must have shape (U,28)")
    if masks.dtype != np.bool_ or masks.shape != q1.shape:
        raise EEAxisTwoRouteError("score mask is not a native Boolean surface")
    scores = q1 + q2
    if not np.all(np.isfinite(scores)) or not np.all(np.any(masks, axis=1)):
        raise EEAxisTwoRouteError("score surface is non-finite or has an empty row")
    return np.argmax(np.where(masks, scores, -np.inf), axis=1).astype(np.int64)


class EEAxisTwoRouteModel(nn.Module):
    """Exactly two independent heads and optimizers; no Q3 and no C3View."""

    def __init__(
        self,
        config: EEAxisTwoRouteConfig,
        *,
        train_seed: int,
        formal: bool = True,
        device: str = "cpu",
    ) -> None:
        super().__init__()
        if not isinstance(config, EEAxisTwoRouteConfig):
            raise TypeError("config must be EEAxisTwoRouteConfig")
        if type(formal) is not bool:
            raise TypeError("formal must be a Boolean")
        if type(train_seed) is not int:
            raise TypeError("train_seed must be an integer")
        if formal and train_seed != FORMAL_TRAIN_SEED:
            raise ValueError(f"train_seed must be exactly {FORMAL_TRAIN_SEED}")
        self.config = config
        self.train_seed = train_seed
        self.formal = formal
        self.device = torch.device(device)
        torch.manual_seed(train_seed)
        self.q_networks = nn.ModuleList(
            [
                ActionSharedQNetwork(config.q1).to(self.device),
                V014ActionSetQNetwork(config.q2).to(self.device),
            ]
        )
        self.optimizers = [
            optim.Adam(self.q_networks[0].parameters(), lr=config.q1.learning_rate),
            optim.Adam(self.q_networks[1].parameters(), lr=config.q2.learning_rate),
        ]
        self._assert_isolation()
        initial_heads = {
            route: deepcopy(network.state_dict())
            for route, network in zip(ROUTES, self.q_networks, strict=True)
        }
        initial_optimizers = {
            route: deepcopy(optimizer.state_dict())
            for route, optimizer in zip(ROUTES, self.optimizers, strict=True)
        }
        self._initialization = {
            "bytes_sha256": _state_digest(
                {"routes": list(ROUTES), "heads": initial_heads, "optimizers": initial_optimizers}
            ),
            "head_state_sha256": {
                route: _state_digest(initial_heads[route]) for route in ROUTES
            },
            "optimizer_state_sha256": {
                route: _state_digest(initial_optimizers[route]) for route in ROUTES
            },
        }

    @property
    def q1(self) -> ActionSharedQNetwork:
        network = self.q_networks[0]
        assert isinstance(network, ActionSharedQNetwork)
        return network

    @property
    def q2(self) -> V014ActionSetQNetwork:
        network = self.q_networks[1]
        assert isinstance(network, V014ActionSetQNetwork)
        return network

    @property
    def initialization_digests(self) -> Mapping[str, Any]:
        return deepcopy(self._initialization)

    def _assert_isolation(self) -> None:
        parameter_sets = [
            {id(parameter) for parameter in network.parameters()}
            for network in self.q_networks
        ]
        if parameter_sets[0] & parameter_sets[1]:
            raise EEAxisTwoRouteError("Q1 and Q2 share trainable parameters")
        for index, (network, optimizer) in enumerate(
            zip(self.q_networks, self.optimizers, strict=True)
        ):
            expected = {id(parameter) for parameter in network.parameters()}
            actual = {
                id(parameter)
                for group in optimizer.param_groups
                for parameter in group["params"]
            }
            if actual != expected:
                raise EEAxisTwoRouteError(f"optimizer {index} is not head-local")
            if type(optimizer) is not optim.Adam:
                raise EEAxisTwoRouteError(f"optimizer {index} must be exact Adam")

    def _validate_optimizer_state(self, route: str, value: object, index: int) -> None:
        if not isinstance(value, Mapping) or set(value) != {"state", "param_groups"}:
            raise EEAxisTwoRouteError(f"{route} Adam state is malformed")
        groups = value["param_groups"]
        state_values = value["state"]
        expected = self.optimizers[index].state_dict()
        if not isinstance(groups, list) or len(groups) != 1 or not isinstance(state_values, Mapping):
            raise EEAxisTwoRouteError(f"{route} Adam state is malformed")
        observed_group = groups[0]
        expected_group = expected["param_groups"][0]
        if not isinstance(observed_group, Mapping) or set(observed_group) != set(expected_group):
            raise EEAxisTwoRouteError(f"{route} Adam defaults drifted")
        if observed_group.get("params") != expected_group["params"]:
            raise EEAxisTwoRouteError(f"{route} Adam parameter topology drifted")
        for key, expected_value in expected_group.items():
            if key != "params" and observed_group.get(key) != expected_value:
                raise EEAxisTwoRouteError(f"{route} Adam defaults drifted")
        if set(state_values) - set(observed_group["params"]):
            raise EEAxisTwoRouteError(f"{route} Adam state names unknown parameters")
        if not _finite_optimizer_tree(value):
            raise EEAxisTwoRouteError(f"{route} Adam state is non-finite")

    def capture_q12(
        self,
        q1_states: object,
        *,
        q2_states: object,
        q2_action_masks: object,
        native_observation_event_digest: str,
    ) -> DetachedQ12Snapshot:
        """Capture one immutable Q1/Q2 evaluation using the existing snapshot."""

        from mcrl.runtime.ee_axis_state import EEAxisStateObservation

        if isinstance(q1_states, EEAxisStateObservation):
            q1_states.verify()
            q1_array = np.asarray(q1_states.state_matrix, dtype=np.float32)
            source_digest = q1_states.state_sha256
        else:
            q1_array = np.asarray(q1_states, dtype=np.float32)
            source_digest = _array_digest(q1_array, domain="native-q1-state")
        q2_array = np.asarray(q2_states, dtype=np.float32)
        masks = np.asarray(q2_action_masks)
        if q1_array.ndim != 2 or q1_array.shape[1] != 228:
            raise ValueError("Q1 states must have shape (U,228)")
        if q2_array.shape != (q1_array.shape[0], 448):
            raise ValueError("Q2 OPS-3 states must have shape (U,448)")
        if masks.dtype != np.bool_ or masks.shape != (q1_array.shape[0], 28):
            raise ValueError("Q2 OPS-3 masks must be Boolean and action-aligned")
        if not np.all(np.isfinite(q1_array)) or not np.all(np.isfinite(q2_array)):
            raise ValueError("Q1 and Q2 states must be finite")
        if not np.all(np.any(masks, axis=1)):
            raise ValueError("every Q2 OPS-3 row requires a legal action")
        with torch.no_grad():
            q1 = self.q1(torch.tensor(q1_array, dtype=torch.float32, device=self.device)).cpu().numpy()
            q2 = self.q2(
                torch.tensor(q2_array, dtype=torch.float32, device=self.device),
                torch.tensor(masks, dtype=torch.bool, device=self.device),
            ).cpu().numpy()
        return DetachedQ12Snapshot(
            q1=q1,
            q2=q2,
            source_state_digest=source_digest,
            native_observation_event_digest=native_observation_event_digest,
            model_digest=_q12_model_digest(self.q1, self.q2, self.config.q1, self.config.q2),
            q2_state_digest=_array_digest(q2_array, domain="ops3-q2-state"),
            q2_action_mask_digest=_array_digest(masks, domain="ops3-q2-action-mask"),
        )

    capture_q1_q2 = capture_q12

    def select_greedy_actions(
        self, snapshot: DetachedQ12Snapshot, action_masks: object
    ) -> np.ndarray:
        if not isinstance(snapshot, DetachedQ12Snapshot):
            raise TypeError("snapshot must be DetachedQ12Snapshot")
        return deploy_q12_action(snapshot.q1, snapshot.q2, action_masks)

    def checkpoint_state(
        self,
        *,
        update_count: int,
        route_update_counts: Mapping[str, int] | None = None,
    ) -> dict[str, Any]:
        if isinstance(update_count, bool) or not isinstance(update_count, int) or update_count < 0:
            raise ValueError("update_count must be a nonnegative integer")
        counts = dict(route_update_counts or {route: update_count for route in ROUTES})
        if set(counts) != set(ROUTES) or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in counts.values()
        ):
            raise ValueError("route_update_counts must contain nonnegative C1/C2 integers")
        heads = {
            route: deepcopy(network.state_dict())
            for route, network in zip(ROUTES, self.q_networks, strict=True)
        }
        optimizer_states = {
            route: deepcopy(optimizer.state_dict())
            for route, optimizer in zip(ROUTES, self.optimizers, strict=True)
        }
        return {
            "schema": TWO_ROUTE_CHECKPOINT_SCHEMA,
            "algorithm": TWO_ROUTE_ALGORITHM,
            "format_version": 1,
            "routes": list(ROUTES),
            "update_count": update_count,
            "route_update_counts": counts,
            "formal": self.formal,
            "train_seed": self.train_seed,
            "config": asdict(self.config),
            "initialization": deepcopy(self._initialization),
            "heads": {
                route: {"state": heads[route], "sha256": _state_digest(heads[route])}
                for route in ROUTES
            },
            "optimizers": {
                route: {
                    "state": optimizer_states[route],
                    "sha256": _state_digest(optimizer_states[route]),
                }
                for route in ROUTES
            },
        }

    def load_checkpoint_state(self, state: Mapping[str, Any]) -> int:
        if not isinstance(state, Mapping):
            raise TypeError("checkpoint state must be a mapping")
        if _contains_q3(state):
            raise EEAxisTwoRouteError("Q3/C3 state is forbidden in a two-route checkpoint")
        expected = {
            "schema", "algorithm", "format_version", "routes", "update_count",
            "route_update_counts", "formal", "train_seed", "config", "initialization",
            "heads", "optimizers",
        }
        if set(state) != expected:
            raise EEAxisTwoRouteError("unsupported two-route checkpoint schema")
        if (
            state["schema"] != TWO_ROUTE_CHECKPOINT_SCHEMA
            or state["algorithm"] != TWO_ROUTE_ALGORITHM
            or state["format_version"] != 1
        ):
            if state.get("algorithm") == LCSRS_THREE_ROUTE_ALGORITHM:
                raise EEAxisTwoRouteError("three-route checkpoints are rejected")
            raise EEAxisTwoRouteError("unsupported two-route checkpoint identity")
        if state["routes"] != list(ROUTES):
            raise EEAxisTwoRouteError("checkpoint routes must be exactly C1 and C2")
        if (
            state["formal"] is not self.formal
            or state["train_seed"] != self.train_seed
            or state["config"] != asdict(self.config)
        ):
            raise EEAxisTwoRouteError("checkpoint configuration or seed mismatch")
        if state["initialization"] != self._initialization:
            raise EEAxisTwoRouteError("checkpoint initial-byte digests mismatch")
        update_count = state["update_count"]
        counts = state["route_update_counts"]
        if (
            isinstance(update_count, bool)
            or not isinstance(update_count, int)
            or update_count < 0
            or not isinstance(counts, Mapping)
            or set(counts) != set(ROUTES)
            or any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in counts.values())
        ):
            raise EEAxisTwoRouteError("checkpoint update counts are invalid")
        heads = state["heads"]
        optimizer_states = state["optimizers"]
        if not isinstance(heads, Mapping) or tuple(heads) != ROUTES:
            raise EEAxisTwoRouteError("checkpoint head states are not ordered C1/C2")
        if not isinstance(optimizer_states, Mapping) or tuple(optimizer_states) != ROUTES:
            raise EEAxisTwoRouteError("checkpoint optimizer states are not ordered C1/C2")
        for route in ROUTES:
            head = heads[route]
            optimizer = optimizer_states[route]
            if not isinstance(head, Mapping) or set(head) != {"state", "sha256"}:
                raise EEAxisTwoRouteError("checkpoint head payload is malformed")
            if not isinstance(optimizer, Mapping) or set(optimizer) != {"state", "sha256"}:
                raise EEAxisTwoRouteError("checkpoint optimizer payload is malformed")
            if _state_digest(head["state"]) != head["sha256"]:
                raise EEAxisTwoRouteError(f"{route} head-state digest mismatch")
            if _state_digest(optimizer["state"]) != optimizer["sha256"]:
                raise EEAxisTwoRouteError(f"{route} optimizer-state digest mismatch")
            self._validate_optimizer_state(
                route, optimizer["state"], ROUTES.index(route)
            )
        try:
            for route, network in zip(ROUTES, self.q_networks, strict=True):
                network.load_state_dict(heads[route]["state"])
            for route, optimizer in zip(ROUTES, self.optimizers, strict=True):
                optimizer.load_state_dict(optimizer_states[route]["state"])
        except (KeyError, TypeError, ValueError, RuntimeError) as error:
            raise EEAxisTwoRouteError("malformed two-route checkpoint state") from error
        assert_finite_parameters(self.q_networks)
        self._assert_isolation()
        return update_count


__all__ = [
    "DetachedQ12Snapshot",
    "EEAxisTwoRouteConfig",
    "EEAxisTwoRouteError",
    "EEAxisTwoRouteModel",
    "FORMAL_TRAIN_SEED",
    "FROZEN_MODEL_CONFIG_SHA256",
    "FROZEN_MODEL_CONFIG_PATH",
    "FROZEN_Q1_CONFIG",
    "FROZEN_Q2_CONFIG",
    "ROUTES",
    "TWO_ROUTE_ALGORITHM",
    "TWO_ROUTE_CHECKPOINT_SCHEMA",
    "deploy_q12_action",
]
