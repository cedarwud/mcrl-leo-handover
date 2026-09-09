"""V0.23 heterogeneous three-route inference and checkpoint seam.

Q1 consumes its native 228-D action-shared state; Q2 consumes the authenticated
448-D feature-major OPS-3 state and its native legal-action mask.  Q3 alone
reads the structured LC-SRS C3View.  The two Q12 inputs are captured exactly
once into an immutable snapshot before the final scalar sum and masked argmax.
This module owns no teacher, simulator, coalition selector, or retry.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
import hashlib
import json
import struct
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from ..env.action_contract import NO_OP_ACTION
from ..errors import MCRLContractError
from ..runtime.ee_axis_lcsrs_c3_state import C3View, LCSRS_C3_SCHEMA_SHA256
from ..runtime.finiteness import assert_finite_parameters
from .ee_axis_action_shared import (
    ACTION_SHARED_ALGORITHM,
    ACTION_SHARED_CHECKPOINT_VERSION,
    ActionSharedQNetwork,
    EEAxisActionSharedConfig,
)
from .ee_axis_lcsrs_c3_head import LCSRSC3HeadConfig, LCSRSC3QNetwork
from .ee_axis_v014_head import EEAxisV014HeadConfig, V014ActionSetQNetwork


LCSRS_THREE_ROUTE_ALGORITHM = "multi-catfish-mcrl-v023-lcsrs-three-route"
LCSRS_THREE_ROUTE_CHECKPOINT_VERSION = 2
LCSRS_ROUTE_NAMES = ("C1", "C2", "C3")


def _readonly_float32(value: object, *, name: str) -> np.ndarray:
    try:
        result = np.array(value, dtype=np.float32, copy=True, order="C")
    except (TypeError, ValueError, OverflowError) as error:
        raise MCRLContractError(f"{name} cannot be materialised") from error
    if result.ndim != 2 or not np.all(np.isfinite(result)):
        raise MCRLContractError(f"{name} must be a finite matrix")
    result.setflags(write=False)
    return result


def _array_digest(value: np.ndarray, *, domain: str) -> str:
    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(domain.encode("ascii"))
    digest.update(struct.pack(">I", array.ndim))
    for extent in array.shape:
        digest.update(struct.pack(">Q", int(extent)))
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _q12_model_digest(
    q1: ActionSharedQNetwork,
    q2: V014ActionSetQNetwork,
    q1_config: EEAxisActionSharedConfig,
    q2_config: EEAxisV014HeadConfig,
) -> str:
    digest = hashlib.sha256()
    digest.update(b"v023-heterogeneous-q12-model-v2")
    for name, config in (("q1", q1_config), ("q2", q2_config)):
        digest.update(name.encode("ascii"))
        digest.update(
            json.dumps(asdict(config), sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        )
    for route, network in (("q1", q1), ("q2", q2)):
        digest.update(route.encode("ascii"))
        for name, tensor in sorted(network.state_dict().items()):
            array = tensor.detach().cpu().numpy()
            digest.update(name.encode("utf-8"))
            digest.update(_array_digest(array, domain="parameter").encode("ascii"))
    return digest.hexdigest()


def _snapshot_digest(
    q1: np.ndarray,
    q2: np.ndarray,
    q12: np.ndarray,
    *,
    source_state_digest: str,
    q2_state_digest: str,
    q2_action_mask_digest: str,
    native_observation_event_digest: str,
    model_digest: str,
) -> str:
    digest = hashlib.sha256()
    digest.update(LCSRS_THREE_ROUTE_ALGORITHM.encode("ascii"))
    digest.update(source_state_digest.encode("ascii"))
    digest.update(q2_state_digest.encode("ascii"))
    digest.update(q2_action_mask_digest.encode("ascii"))
    digest.update(native_observation_event_digest.encode("ascii"))
    digest.update(model_digest.encode("ascii"))
    for name, value in (("q1", q1), ("q2", q2), ("q12", q12)):
        array = np.ascontiguousarray(value)
        digest.update(name.encode("ascii"))
        digest.update(struct.pack(">II", *array.shape))
        digest.update(array.dtype.str.encode("ascii"))
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


@dataclass(frozen=True)
class DetachedQ12Snapshot:
    """One immutable Q1/Q2 evaluation at a captured native decision state."""

    q1: np.ndarray
    q2: np.ndarray
    source_state_digest: str
    native_observation_event_digest: str
    model_digest: str
    q2_state_digest: str
    q2_action_mask_digest: str
    q12: np.ndarray | None = None
    content_digest: str = ""

    def __post_init__(self) -> None:
        q1 = _readonly_float32(self.q1, name="q1")
        q2 = _readonly_float32(self.q2, name="q2")
        if q1.shape != q2.shape or q1.shape[1] < 1:
            raise MCRLContractError("Q1 and Q2 snapshot shapes disagree")
        expected_q12 = np.asarray(q1 + q2, dtype=np.float32)
        supplied = expected_q12 if self.q12 is None else self.q12
        q12 = _readonly_float32(supplied, name="q12")
        if q12.shape != q1.shape or not np.array_equal(q12, expected_q12):
            raise MCRLContractError("q12 must be the exact float32 Q1+Q2 sum")
        for name, digest in (
            ("source_state_digest", self.source_state_digest),
            ("q2_state_digest", self.q2_state_digest),
            ("q2_action_mask_digest", self.q2_action_mask_digest),
            (
                "native_observation_event_digest",
                self.native_observation_event_digest,
            ),
            ("model_digest", self.model_digest),
        ):
            if (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
            ):
                raise MCRLContractError(f"{name} must be a lowercase SHA-256")
        object.__setattr__(self, "q1", q1)
        object.__setattr__(self, "q2", q2)
        object.__setattr__(self, "q12", q12)
        expected_digest = _snapshot_digest(
            q1,
            q2,
            q12,
            source_state_digest=self.source_state_digest,
            q2_state_digest=self.q2_state_digest,
            q2_action_mask_digest=self.q2_action_mask_digest,
            native_observation_event_digest=self.native_observation_event_digest,
            model_digest=self.model_digest,
        )
        if self.content_digest not in {"", expected_digest}:
            raise MCRLContractError("detached Q12 snapshot digest mismatch")
        object.__setattr__(self, "content_digest", expected_digest)

    @property
    def users(self) -> int:
        return int(self.q1.shape[0])

    @property
    def actions(self) -> int:
        return int(self.q1.shape[1])


@dataclass(frozen=True)
class LCSRSThreeRouteConfig:
    """Frozen network and optimizer configuration for exactly three routes."""

    q1: EEAxisActionSharedConfig | None = None
    q2: EEAxisV014HeadConfig | None = None
    # Compatibility-only constructor alias.  It is canonicalised into q1 and
    # remains in the serialized config so an old q12-only config cannot load a
    # new checkpoint under the version-2 format.
    q12: EEAxisActionSharedConfig | None = None
    q3: LCSRSC3HeadConfig = field(default_factory=LCSRSC3HeadConfig)
    q3_learning_rate: float = 1.0e-3
    q3_betas: tuple[float, float] = (0.9, 0.999)
    q3_epsilon: float = 1.0e-8
    q3_weight_decay: float = 0.0

    def __post_init__(self) -> None:
        q1 = self.q1 if self.q1 is not None else self.q12
        if not isinstance(q1, EEAxisActionSharedConfig):
            raise TypeError("V0.23 requires an EEAxisActionSharedConfig for Q1")
        if self.q1 is not None and self.q12 is not None and self.q1 != self.q12:
            raise ValueError("q1 and legacy q12 aliases disagree")
        q2 = self.q2
        if q2 is None:
            q2 = EEAxisV014HeadConfig(
                action_dim=q1.action_dim,
                local_feature_dim=16,
                global_feature_dim=0,
                hidden_layers=(100, 50, 50),
                activation="tanh",
                learning_rate=1.0e-3,
                kappa_bits=q1.kappa_bits,
                beta=0.1,
            )
        if not isinstance(q2, EEAxisV014HeadConfig):
            raise TypeError("V0.23 requires an EEAxisV014HeadConfig for Q2")
        if q1.action_dim != q2.action_dim or q1.action_dim != self.q3.action_dim:
            raise ValueError("Q1/Q2 and Q3 action dimensions must agree")
        if (
            q2.local_feature_dim != 16
            or q2.global_feature_dim != 0
            or q2.hidden_layers != (100, 50, 50)
            or q2.activation != "tanh"
            or q2.learning_rate != 1.0e-3
            or q2.kappa_bits != q1.kappa_bits
            or q2.beta != 0.1
        ):
            raise ValueError("V0.23 Q2 must use the frozen V0.14 OPS-3 head config")
        object.__setattr__(self, "q1", q1)
        object.__setattr__(self, "q2", q2)
        object.__setattr__(self, "q12", q1)
        if self.q3_learning_rate != 1.0e-3:
            raise ValueError("V0.23 Q3 learning rate is frozen at 1e-3")
        if self.q3_betas != (0.9, 0.999):
            raise ValueError("V0.23 Q3 Adam betas are frozen")
        if self.q3_epsilon != 1.0e-8 or self.q3_weight_decay != 0.0:
            raise ValueError("V0.23 Q3 Adam epsilon/weight decay are frozen")


class EEAxisLCSRSThreeRoute(nn.Module):
    """Exactly Q1, Q2, Q3 with heterogeneous inputs and one final argmax."""

    def __init__(
        self,
        config: LCSRSThreeRouteConfig,
        *,
        train_seed: int,
        device: str = "cpu",
    ) -> None:
        super().__init__()
        if isinstance(train_seed, bool) or not isinstance(train_seed, int):
            raise TypeError("train_seed must be an integer")
        self.config = config
        self.train_seed = train_seed
        self.device = torch.device(device)
        torch.manual_seed(train_seed)
        self.q_networks = nn.ModuleList(
            [
                ActionSharedQNetwork(config.q12).to(self.device),
                V014ActionSetQNetwork(config.q2).to(self.device),
                LCSRSC3QNetwork(config.q3).to(self.device),
            ]
        )
        self.optimizers = [
            optim.Adam(self.q_networks[0].parameters(), lr=config.q12.learning_rate),
            optim.Adam(self.q_networks[1].parameters(), lr=config.q2.learning_rate),
            optim.Adam(
                self.q_networks[2].parameters(),
                lr=config.q3_learning_rate,
                betas=config.q3_betas,
                eps=config.q3_epsilon,
                weight_decay=config.q3_weight_decay,
            ),
        ]
        parameter_ids = [
            {id(parameter) for parameter in network.parameters()}
            for network in self.q_networks
        ]
        if any(
            parameter_ids[left] & parameter_ids[right]
            for left in range(3)
            for right in range(left)
        ):
            raise RuntimeError("V0.23 Q functions may not share trainable parameters")

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
    def q3(self) -> LCSRSC3QNetwork:
        network = self.q_networks[2]
        assert isinstance(network, LCSRSC3QNetwork)
        return network

    def capture_q12(
        self,
        q1_states: object,
        *,
        q2_states: object,
        q2_action_masks: object,
        native_observation_event_digest: str,
    ) -> DetachedQ12Snapshot:
        """Capture native Q1 and OPS-3 Q2 inputs in one immutable snapshot."""

        from ..runtime.ee_axis_state import EEAxisStateObservation

        if isinstance(q1_states, EEAxisStateObservation):
            q1_states.verify()
            q1_values = np.asarray(q1_states.state_matrix, dtype=np.float32)
            source_state_digest = q1_states.state_sha256
        else:
            q1_values = np.asarray(q1_states, dtype=np.float32)
            source_state_digest = _array_digest(
                q1_values,
                domain="native-q1-state",
            )
        if q1_values.ndim != 2 or q1_values.shape[1] != self.config.q1.state_dim:
            raise ValueError(
                f"Q1 states must have shape (U,{self.config.q1.state_dim})"
            )
        q2_values = np.asarray(q2_states, dtype=np.float32)
        q2_masks = np.asarray(q2_action_masks)
        if q2_values.ndim != 2 or q2_values.shape != (
            q1_values.shape[0], self.config.q2.state_dim
        ):
            raise ValueError(
                f"Q2 OPS-3 states must have shape (U,{self.config.q2.state_dim})"
            )
        if q2_masks.dtype != np.bool_ or q2_masks.shape != (
            q1_values.shape[0], self.config.q2.action_dim
        ):
            raise ValueError("Q2 OPS-3 masks must be Boolean and action-aligned")
        if not np.all(np.isfinite(q1_values)) or not np.all(np.isfinite(q2_values)):
            raise ValueError("Q1 and Q2 states must be finite")
        if not np.all(np.any(q2_masks, axis=1)):
            raise ValueError("every Q2 OPS-3 row requires a legal action")
        q1_tensor = torch.tensor(q1_values, dtype=torch.float32, device=self.device)
        q2_tensor = torch.tensor(q2_values, dtype=torch.float32, device=self.device)
        mask_tensor = torch.tensor(q2_masks, dtype=torch.bool, device=self.device)
        with torch.no_grad():
            q1 = self.q1(q1_tensor).cpu().numpy()
            q2 = self.q2(q2_tensor, mask_tensor).cpu().numpy()
        return DetachedQ12Snapshot(
            q1=q1,
            q2=q2,
            source_state_digest=source_state_digest,
            native_observation_event_digest=native_observation_event_digest,
            model_digest=_q12_model_digest(
                self.q1, self.q2, self.config.q1, self.config.q2
            ),
            q2_state_digest=_array_digest(q2_values, domain="ops3-q2-state"),
            q2_action_mask_digest=_array_digest(
                q2_masks, domain="ops3-q2-action-mask"
            ),
        )

    capture_q1_q2 = capture_q12

    @staticmethod
    def _validate_view(
        snapshot: DetachedQ12Snapshot,
        view: C3View,
    ) -> None:
        view.verify()
        if snapshot.users != view.action_context.shape[0]:
            raise MCRLContractError("Q12 snapshot and C3View user counts disagree")
        if snapshot.actions != view.action_mask.shape[1]:
            raise MCRLContractError("Q12 snapshot and C3View action counts disagree")
        expected = np.argmax(
            np.where(view.action_mask, snapshot.q12, -np.inf),
            axis=1,
        ).astype(np.int64)
        if not np.array_equal(expected, view.reference_actions):
            raise MCRLContractError(
                "C3View references are not the native masked Q1+Q2 argmax"
            )

    def q_values(
        self,
        snapshot: DetachedQ12Snapshot,
        view: C3View,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return the three scalar surfaces without recomputing Q1 or Q2."""

        self._validate_view(snapshot, view)
        with torch.no_grad():
            q3 = self.q3.forward_view(view, device=self.device).cpu().numpy()
        return snapshot.q1, snapshot.q2, q3

    def deployment_scores(
        self,
        snapshot: DetachedQ12Snapshot,
        view: C3View,
    ) -> np.ndarray:
        q1, q2, q3 = self.q_values(snapshot, view)
        return np.asarray(q1 + q2 + q3, dtype=np.float32)

    def select_greedy_actions(
        self,
        snapshot: DetachedQ12Snapshot,
        view: C3View,
    ) -> np.ndarray:
        """Apply exactly one native mask and one row-wise argmax to the sum."""

        scores = self.deployment_scores(snapshot, view)
        masks = np.asarray(view.action_mask)
        actions = np.full(scores.shape[0], NO_OP_ACTION, dtype=np.int64)
        eligible = np.any(masks, axis=1)
        actions[eligible] = np.argmax(
            np.where(masks[eligible], scores[eligible], -np.inf),
            axis=1,
        )
        return actions

    def load_q12_background(self, state: Mapping[str, Any]) -> None:
        """Load only Q1/Q2 from one authenticated legacy action-shared state."""

        if state.get("algorithm") != ACTION_SHARED_ALGORITHM:
            raise MCRLContractError("Q1/Q2 background has the wrong algorithm")
        if state.get("format_version") != ACTION_SHARED_CHECKPOINT_VERSION:
            raise MCRLContractError("Q1/Q2 background version is unsupported")
        if state.get("config") != asdict(self.config.q1):
            raise MCRLContractError("Q1/Q2 background config mismatch")
        networks = state.get("q_networks")
        if not isinstance(networks, list) or len(networks) != 3:
            raise MCRLContractError("Q1/Q2 background must contain three source nets")
        self.q1.load_state_dict(networks[0])
        self.q2.load_state_dict(networks[1])
        assert_finite_parameters((self.q1, self.q2))

    def checkpoint_state(self, *, update_count: int) -> dict[str, Any]:
        if isinstance(update_count, bool) or not isinstance(update_count, int):
            raise ValueError("update_count must be a nonnegative integer")
        if update_count < 0:
            raise ValueError("update_count must be a nonnegative integer")
        return {
            "format_version": LCSRS_THREE_ROUTE_CHECKPOINT_VERSION,
            "algorithm": LCSRS_THREE_ROUTE_ALGORITHM,
            "update_count": update_count,
            "train_seed": self.train_seed,
            "config": asdict(self.config),
            "c3_schema_sha256": LCSRS_C3_SCHEMA_SHA256,
            "route_names": list(LCSRS_ROUTE_NAMES),
            "q_networks": [network.state_dict() for network in self.q_networks],
            "optimizers": [optimizer.state_dict() for optimizer in self.optimizers],
        }

    def load_checkpoint_state(self, state: Mapping[str, Any]) -> int:
        if state.get("algorithm") != LCSRS_THREE_ROUTE_ALGORITHM:
            raise MCRLContractError("checkpoint is not V0.23 LC-SRS three-route")
        if state.get("format_version") != LCSRS_THREE_ROUTE_CHECKPOINT_VERSION:
            raise MCRLContractError("unsupported V0.23 checkpoint version")
        if state.get("train_seed") != self.train_seed:
            raise MCRLContractError("V0.23 checkpoint train_seed mismatch")
        if state.get("config") != asdict(self.config):
            raise MCRLContractError("V0.23 checkpoint config mismatch")
        if state.get("c3_schema_sha256") != LCSRS_C3_SCHEMA_SHA256:
            raise MCRLContractError("V0.23 checkpoint C3 schema mismatch")
        if state.get("route_names") != list(LCSRS_ROUTE_NAMES):
            raise MCRLContractError("V0.23 checkpoint route order mismatch")
        networks = state.get("q_networks")
        optimizers = state.get("optimizers")
        if not isinstance(networks, list) or len(networks) != 3:
            raise MCRLContractError("V0.23 checkpoint needs exactly three Q nets")
        if not isinstance(optimizers, list) or len(optimizers) != 3:
            raise MCRLContractError("V0.23 checkpoint needs exactly three optimizers")
        update_count = state.get("update_count")
        if isinstance(update_count, bool) or not isinstance(update_count, int):
            raise MCRLContractError("invalid V0.23 checkpoint update_count")
        if update_count < 0:
            raise MCRLContractError("invalid V0.23 checkpoint update_count")
        for network, payload in zip(self.q_networks, networks, strict=True):
            network.load_state_dict(payload)
        for optimizer, payload in zip(self.optimizers, optimizers, strict=True):
            optimizer.load_state_dict(payload)
        assert_finite_parameters(self.q_networks)
        return update_count


__all__ = [
    "LCSRS_THREE_ROUTE_ALGORITHM",
    "LCSRS_THREE_ROUTE_CHECKPOINT_VERSION",
    "LCSRS_ROUTE_NAMES",
    "DetachedQ12Snapshot",
    "LCSRSThreeRouteConfig",
    "EEAxisLCSRSThreeRoute",
]
