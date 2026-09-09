"""The bounded V0.4 three-network deployment container.

V0.4 changes the *C3 view* and its local learner.  It does not reopen the
sealed C1/C2 validation or instantiate another set of route heads.  This
module is the narrow seam between those two facts:

* ``q_1`` and ``q_2`` are the exact head-0/head-1 weights from one sealed
  V0.3 masked-mean/max rung-10 checkpoint.  They consume the V0.3 state and
  the one common Boolean legal-action mask.
* ``q_3`` is one fresh action-shared scalar scorer.  It consumes only the
  V0.4 C3 state and is the only network with an optimizer.
* Deployment adds the three route surfaces and performs one masked argmax.

The checkpoint loader is intentionally strict.  A path, digest, authority,
initialisation seed, rung, trainer format, and config are all part of the
frozen-head lineage.  Loading a different head, a different rung, or a
different fallback checkpoint is a contract error rather than a warning.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from ..env.action_contract import NO_OP_ACTION
from ..errors import MCRLContractError
from ..runtime.finiteness import (
    assert_finite_gradients,
    assert_finite_loss,
    assert_finite_parameters,
)
from .ee_axis_action_shared import (
    ActionSharedQNetwork,
    EEAxisActionSharedConfig,
)
from .ee_axis_action_shared_meanmax import (
    MASKED_MEANMAX_ALGORITHM,
    MASKED_MEANMAX_CHECKPOINT_VERSION,
    EEAxisMaskedMeanMaxConfig,
    MaskedMeanMaxQNetwork,
)
from .ee_axis_pairwise import EEAxisPairBatch


HYBRID_ALGORITHM = "multi-catfish-mcrl-ee-axis-v04-c3-hybrid"
HYBRID_CHECKPOINT_VERSION = 1
V03_FALLBACK_CHECKPOINT_SCHEMA = (
    "multi-catfish-mcrl-v03-e1-masked-meanmax-fallback-v1-checkpoint"
)
V03_FROZEN_RUNG = 10
HYBRID_ROUTE_ORDER = ("C1", "C2", "C3")


def _digest(value: object, *, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or value != value.lower():
        raise MCRLContractError(f"{field} must be a 64-character SHA-256 hex digest")
    try:
        int(value, 16)
    except ValueError as error:
        raise MCRLContractError(f"{field} must be a SHA-256 hex digest") from error
    return value


def _strict_int(value: object, *, field: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise MCRLContractError(f"{field} must be an integer >= {minimum}")
    return int(value)


def _sha256_file(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise MCRLContractError(
            f"sealed V0.3 checkpoint is missing, non-regular, or a symlink: {path}"
        )
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _config_digest(config: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        config,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
        default=list,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class FrozenMeanMaxCheckpointSpec:
    """Expected identity of one sealed V0.3 init-seed rung checkpoint."""

    path: Path | str
    sha256: str
    authority_sha256: str
    initialization_seed: int
    rung: int = V03_FROZEN_RUNG

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", Path(self.path))
        _digest(self.sha256, field="checkpoint sha256")
        _digest(self.authority_sha256, field="checkpoint authority_sha256")
        _strict_int(
            self.initialization_seed,
            field="checkpoint initialization_seed",
            minimum=0,
        )
        _strict_int(self.rung, field="checkpoint rung", minimum=1)
        if self.rung != V03_FROZEN_RUNG:
            raise MCRLContractError(
                f"V0.4 freezes V0.3 masked mean/max at rung {V03_FROZEN_RUNG}"
            )


@dataclass(frozen=True)
class FrozenMeanMaxHeadLineage:
    """Auditable identity for one extracted frozen route head."""

    checkpoint_path: str
    checkpoint_sha256: str
    authority_sha256: str
    initialization_seed: int
    rung: int
    head_index: int
    trainer_algorithm: str
    config_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FrozenMeanMaxHeadPair:
    """The two frozen route heads and their independently recorded lineage."""

    q1: MaskedMeanMaxQNetwork
    q2: MaskedMeanMaxQNetwork
    q1_lineage: FrozenMeanMaxHeadLineage
    q2_lineage: FrozenMeanMaxHeadLineage


def _validate_v03_trainer_payload(
    payload: Mapping[str, Any],
    *,
    spec: FrozenMeanMaxCheckpointSpec,
    config: EEAxisMaskedMeanMaxConfig,
) -> Mapping[str, Any]:
    """Validate outer and nested checkpoint identity before extracting a head."""

    if payload.get("schema") != V03_FALLBACK_CHECKPOINT_SCHEMA:
        raise MCRLContractError("sealed checkpoint is not the V0.3 fallback schema")
    if payload.get("authority_sha256") != spec.authority_sha256:
        raise MCRLContractError("sealed checkpoint authority_sha256 mismatch")
    if payload.get("initialization_seed") != spec.initialization_seed:
        raise MCRLContractError("sealed checkpoint initialization_seed mismatch")
    if payload.get("rung") != spec.rung:
        raise MCRLContractError("sealed checkpoint rung mismatch")
    if payload.get("validation_dataset_bytes_opened") is not True:
        raise MCRLContractError("sealed checkpoint lacks validation-dataset receipt")
    if payload.get("validation_metrics_computed") is not True:
        raise MCRLContractError("sealed checkpoint lacks validation-metric receipt")
    if payload.get("test_split_opened") is not False:
        raise MCRLContractError("sealed checkpoint crossed the TEST boundary")
    if payload.get("held_out_ee_evaluated") is not False:
        raise MCRLContractError("sealed checkpoint crossed the held-out EE boundary")

    trainer = payload.get("trainer")
    if not isinstance(trainer, Mapping):
        raise MCRLContractError("sealed checkpoint trainer payload is missing")
    if trainer.get("format_version") != MASKED_MEANMAX_CHECKPOINT_VERSION:
        raise MCRLContractError("sealed checkpoint trainer format mismatch")
    if trainer.get("algorithm") != MASKED_MEANMAX_ALGORITHM:
        raise MCRLContractError("sealed checkpoint trainer algorithm mismatch")
    if trainer.get("train_seed") != spec.initialization_seed:
        raise MCRLContractError("sealed checkpoint trainer train_seed mismatch")
    if trainer.get("update_count") != spec.rung * 3:
        raise MCRLContractError("sealed checkpoint trainer update_count mismatch")
    if trainer.get("config") != asdict(config):
        raise MCRLContractError("sealed checkpoint masked mean/max config mismatch")
    networks = trainer.get("q_networks")
    if not isinstance(networks, list) or len(networks) != 3:
        raise MCRLContractError(
            "sealed V0.3 trainer must contain exactly three route heads"
        )
    optimizers = trainer.get("optimizers")
    if not isinstance(optimizers, list) or len(optimizers) != 3:
        raise MCRLContractError(
            "sealed V0.3 trainer must contain exactly three optimizer receipts"
        )
    return trainer


def _load_sealed_payload(
    spec: FrozenMeanMaxCheckpointSpec,
    config: EEAxisMaskedMeanMaxConfig,
) -> tuple[Mapping[str, Any], str]:
    path = Path(spec.path)
    actual_sha256 = _sha256_file(path)
    if actual_sha256 != spec.sha256:
        raise MCRLContractError("sealed V0.3 checkpoint bytes do not match expected sha256")
    try:
        payload = torch.load(path, map_location="cpu", weights_only=False)
    except Exception as error:
        raise MCRLContractError("sealed V0.3 checkpoint cannot be loaded") from error
    if not isinstance(payload, Mapping):
        raise MCRLContractError("sealed V0.3 checkpoint must contain a mapping")
    trainer = _validate_v03_trainer_payload(payload, spec=spec, config=config)
    return trainer, actual_sha256


def extract_frozen_meanmax_head(
    spec: FrozenMeanMaxCheckpointSpec,
    config: EEAxisMaskedMeanMaxConfig,
    *,
    head_index: int,
    device: str = "cpu",
) -> tuple[MaskedMeanMaxQNetwork, FrozenMeanMaxHeadLineage]:
    """Extract exactly head 0 or 1 from a sealed rung-10 checkpoint.

    C1 and C2 are intentionally tied to the two head indices produced by the
    sealed V0.3 route order.  Head 2 is not accepted here: it is replaced by
    the fresh V0.4 local Q3 below.
    """

    if isinstance(head_index, bool) or head_index not in (0, 1):
        raise MCRLContractError("frozen V0.3 extraction accepts only head indices 0 and 1")
    trainer, actual_sha256 = _load_sealed_payload(spec, config)
    networks = trainer["q_networks"]
    payload = networks[head_index]
    if not isinstance(payload, Mapping):
        raise MCRLContractError("sealed route head state is not a mapping")
    network = MaskedMeanMaxQNetwork(config).to(torch.device(device))
    try:
        network.load_state_dict(payload, strict=True)
    except (RuntimeError, TypeError) as error:
        raise MCRLContractError("sealed route head state does not match config") from error
    network.requires_grad_(False)
    network.eval()
    lineage = FrozenMeanMaxHeadLineage(
        checkpoint_path=str(Path(spec.path).resolve()),
        checkpoint_sha256=actual_sha256,
        authority_sha256=spec.authority_sha256,
        initialization_seed=spec.initialization_seed,
        rung=spec.rung,
        head_index=head_index,
        trainer_algorithm=str(trainer["algorithm"]),
        config_sha256=_config_digest(asdict(config)),
    )
    return network, lineage


def load_frozen_meanmax_head_pair(
    spec: FrozenMeanMaxCheckpointSpec,
    config: EEAxisMaskedMeanMaxConfig,
    *,
    device: str = "cpu",
) -> FrozenMeanMaxHeadPair:
    """Load the paired C1/C2 heads from one sealed init-seed checkpoint."""

    # Validate and hash the file once before extracting both heads.  The
    # public single-head helper remains available for audit probes; this pair
    # loader is the normal production path and ensures both heads share one
    # exact physical checkpoint lineage.
    trainer, actual_sha256 = _load_sealed_payload(spec, config)
    networks = trainer["q_networks"]
    extracted: list[MaskedMeanMaxQNetwork] = []
    lineages: list[FrozenMeanMaxHeadLineage] = []
    for head_index in (0, 1):
        payload = networks[head_index]
        if not isinstance(payload, Mapping):
            raise MCRLContractError("sealed route head state is not a mapping")
        network = MaskedMeanMaxQNetwork(config).to(torch.device(device))
        try:
            network.load_state_dict(payload, strict=True)
        except (RuntimeError, TypeError) as error:
            raise MCRLContractError(
                "sealed route head state does not match config"
            ) from error
        network.requires_grad_(False)
        network.eval()
        extracted.append(network)
        lineages.append(
            FrozenMeanMaxHeadLineage(
                checkpoint_path=str(Path(spec.path).resolve()),
                checkpoint_sha256=actual_sha256,
                authority_sha256=spec.authority_sha256,
                initialization_seed=spec.initialization_seed,
                rung=spec.rung,
                head_index=head_index,
                trainer_algorithm=str(trainer["algorithm"]),
                config_sha256=_config_digest(asdict(config)),
            )
        )
    return FrozenMeanMaxHeadPair(
        q1=extracted[0],
        q2=extracted[1],
        q1_lineage=lineages[0],
        q2_lineage=lineages[1],
    )


def _validate_hybrid_configs(
    v03_config: EEAxisMaskedMeanMaxConfig,
    v04_config: EEAxisActionSharedConfig,
) -> None:
    if v03_config.action_dim != v04_config.action_dim:
        raise MCRLContractError("V0.3 and V0.4 action dimensions must match")
    if v03_config.state_dim != v04_config.state_dim:
        raise MCRLContractError("V0.3 and V0.4 state dimensions must match")
    for field in (
        "hidden_layers",
        "activation",
        "learning_rate",
        "kappa_bits",
        "beta",
        "loss_weights",
    ):
        if getattr(v03_config, field) != getattr(v04_config, field):
            raise MCRLContractError(
                f"V0.3/V0.4 learner config mismatch in frozen field {field}"
            )


class EEAxisV04HybridTrainer:
    """Three Q networks: frozen C1/C2 heads plus trainable local C3.

    The class deliberately has only ``q_nets`` (length three) and one
    ``q3_optimizer``.  Q1/Q2 are not represented by trainers or optimizers;
    their parameters are frozen and never participate in the C3 gradient.
    """

    def __init__(
        self,
        *,
        q1: MaskedMeanMaxQNetwork,
        q2: MaskedMeanMaxQNetwork,
        v03_config: EEAxisMaskedMeanMaxConfig,
        v04_config: EEAxisActionSharedConfig,
        initialization_seed: int,
        selected_q3_rung: int,
        frozen_lineage: tuple[FrozenMeanMaxHeadLineage, FrozenMeanMaxHeadLineage],
        device: str = "cpu",
    ) -> None:
        _validate_hybrid_configs(v03_config, v04_config)
        if not isinstance(q1, MaskedMeanMaxQNetwork) or not isinstance(
            q2, MaskedMeanMaxQNetwork
        ):
            raise TypeError("q1 and q2 must be masked mean/max networks")
        if len(frozen_lineage) != 2 or tuple(
            lineage.head_index for lineage in frozen_lineage
        ) != (0, 1):
            raise MCRLContractError("hybrid frozen lineage must be head indices (0, 1)")
        if isinstance(initialization_seed, bool) or not isinstance(initialization_seed, int):
            raise TypeError("initialization_seed must be an integer")
        if isinstance(selected_q3_rung, bool) or not isinstance(selected_q3_rung, int):
            raise TypeError("selected_q3_rung must be an integer")
        if selected_q3_rung < 1:
            raise ValueError("selected_q3_rung must be positive")
        for lineage in frozen_lineage:
            if lineage.initialization_seed != initialization_seed:
                raise MCRLContractError("frozen head seed does not match hybrid seed")
            if lineage.rung != V03_FROZEN_RUNG:
                raise MCRLContractError("hybrid requires frozen V0.3 rung 10 heads")

        self.v03_config = v03_config
        self.v04_config = v04_config
        self.initialization_seed = initialization_seed
        self.selected_q3_rung = selected_q3_rung
        self.frozen_lineage = frozen_lineage
        self.device = torch.device(device)

        # Seed only the one fresh local Q3 construction.  q1/q2 are already
        # loaded from sealed bytes and are not re-initialised here.
        torch.manual_seed(initialization_seed)
        q3 = ActionSharedQNetwork(v04_config).to(self.device)
        self.q_nets = nn.ModuleList([q1.to(self.device), q2.to(self.device), q3])
        self.q_nets[0].requires_grad_(False)
        self.q_nets[1].requires_grad_(False)
        self.q_nets[0].eval()
        self.q_nets[1].eval()
        self.q_nets[2].train()
        self.q3_optimizer = optim.Adam(
            tuple(parameter for parameter in self.q_nets[2].parameters()),
            lr=v04_config.learning_rate,
        )
        self.q3_update_count = 0
        self._assert_exact_three_networks()

    @classmethod
    def from_sealed_checkpoint(
        cls,
        spec: FrozenMeanMaxCheckpointSpec,
        *,
        v03_config: EEAxisMaskedMeanMaxConfig,
        v04_config: EEAxisActionSharedConfig,
        selected_q3_rung: int,
        device: str = "cpu",
    ) -> "EEAxisV04HybridTrainer":
        """Construct a hybrid from exact V0.3 head-0/head-1 checkpoint bytes."""

        pair = load_frozen_meanmax_head_pair(spec, v03_config, device=device)
        return cls(
            q1=pair.q1,
            q2=pair.q2,
            v03_config=v03_config,
            v04_config=v04_config,
            initialization_seed=spec.initialization_seed,
            selected_q3_rung=selected_q3_rung,
            frozen_lineage=(pair.q1_lineage, pair.q2_lineage),
            device=device,
        )

    @property
    def q1(self) -> MaskedMeanMaxQNetwork:
        return self.q_nets[0]  # type: ignore[return-value]

    @property
    def q2(self) -> MaskedMeanMaxQNetwork:
        return self.q_nets[1]  # type: ignore[return-value]

    @property
    def q3(self) -> ActionSharedQNetwork:
        return self.q_nets[2]  # type: ignore[return-value]

    def _assert_exact_three_networks(self) -> None:
        if len(self.q_nets) != 3:
            raise RuntimeError("V0.4 hybrid must instantiate exactly three Q networks")
        parameter_ids = [
            {id(parameter) for parameter in network.parameters()}
            for network in self.q_nets
        ]
        if any(parameter_ids[i] & parameter_ids[j] for i in range(3) for j in range(i)):
            raise RuntimeError("hybrid Q networks may not share parameters")
        if any(parameter.requires_grad for network in self.q_nets[:2] for parameter in network.parameters()):
            raise RuntimeError("hybrid C1/C2 parameters must be frozen")

    def _states(
        self,
        values: np.ndarray,
        *,
        label: str,
        batch_size: int | None = None,
    ) -> np.ndarray:
        result = np.asarray(values, dtype=np.float32)
        if result.ndim != 2 or result.shape[1] != self.v03_config.state_dim:
            raise ValueError(
                f"{label} must have shape (batch, {self.v03_config.state_dim})"
            )
        if batch_size is not None and result.shape[0] != batch_size:
            raise ValueError("V0.3 and V0.4 state views must share one batch dimension")
        if not np.all(np.isfinite(result)):
            raise ValueError(f"{label} must be finite")
        return result

    def _masks(self, masks: np.ndarray, *, batch_size: int) -> np.ndarray:
        result = np.asarray(masks)
        if result.dtype != np.bool_ or result.shape != (
            batch_size,
            self.v03_config.action_dim,
        ):
            raise ValueError(
                "legal masks must be Boolean with shape "
                f"({batch_size}, {self.v03_config.action_dim})"
            )
        if not np.all(np.any(result, axis=1)):
            raise ValueError("legal masks must admit at least one action per row")
        return result

    def q_values_by_route(
        self,
        states_v03: np.ndarray,
        states_v04: np.ndarray,
        masks: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Evaluate Q1/Q2 on V0.3 and Q3 on V0.4 causal views."""

        v03 = self._states(states_v03, label="V0.3 states")
        v04 = self._states(states_v04, label="V0.4 C3 states", batch_size=v03.shape[0])
        legal = self._masks(masks, batch_size=v03.shape[0])
        with torch.no_grad():
            state_v03 = torch.tensor(v03, dtype=torch.float32, device=self.device)
            state_v04 = torch.tensor(v04, dtype=torch.float32, device=self.device)
            mask = torch.tensor(legal, dtype=torch.bool, device=self.device)
            q1 = self.q1(state_v03, mask).cpu().numpy()
            q2 = self.q2(state_v03, mask).cpu().numpy()
            q3 = self.q3(state_v04).cpu().numpy()
        return q1, q2, q3

    def deployment_scores(
        self,
        states_v03: np.ndarray,
        states_v04: np.ndarray,
        masks: np.ndarray,
        *,
        drop_c3: bool = False,
    ) -> np.ndarray:
        """Return the direct route sum; ``drop_c3`` is the matched ablation."""

        q1, q2, q3 = self.q_values_by_route(states_v03, states_v04, masks)
        scores = q1 + q2
        if not drop_c3:
            scores = scores + q3
        return scores

    def select_greedy_actions(
        self,
        states_v03: np.ndarray,
        states_v04: np.ndarray,
        masks: np.ndarray,
        *,
        drop_c3: bool = False,
    ) -> np.ndarray:
        """Select one action with one common legal mask and one masked argmax."""

        masks_array = np.asarray(masks)
        scores = self.deployment_scores(
            states_v03,
            states_v04,
            masks_array,
            drop_c3=drop_c3,
        )
        if masks_array.dtype != np.bool_ or masks_array.shape != scores.shape:
            raise ValueError("legal masks must match the summed Q surface")
        actions = np.full(scores.shape[0], NO_OP_ACTION, dtype=np.int64)
        eligible = np.any(masks_array, axis=1)
        actions[eligible] = np.argmax(
            np.where(masks_array[eligible], scores[eligible], -np.inf),
            axis=1,
        )
        return actions

    def update_c3(self, batch: EEAxisPairBatch) -> dict[str, float | int | str]:
        """Update only Q3 from a V0.4 C3 pair batch.

        Q1 and Q2 have no optimizer and no gradient path.  This method does
        not even evaluate them, preventing a future refactor from silently
        coupling the frozen routes to the C3 loss.
        """

        batch.validate(
            state_dim=self.v04_config.state_dim,
            action_dim=self.v04_config.action_dim,
        )
        states = torch.tensor(
            np.asarray(batch.states, dtype=np.float32),
            dtype=torch.float32,
            device=self.device,
        )
        reference = torch.tensor(
            np.asarray(batch.reference_actions, dtype=np.int64),
            dtype=torch.int64,
            device=self.device,
        )
        candidate = torch.tensor(
            np.asarray(batch.candidate_actions, dtype=np.int64),
            dtype=torch.int64,
            device=self.device,
        )
        target = torch.tensor(
            np.asarray(batch.target_surplus_bits, dtype=np.float32)
            / float(self.v04_config.kappa_bits),
            dtype=torch.float32,
            device=self.device,
        )
        for network in self.q_nets[:2]:
            for parameter in network.parameters():
                parameter.grad = None
        self.q3.train()
        q_surface = self.q3(states)
        q_reference = q_surface.gather(1, reference[:, None]).squeeze(1)
        q_candidate = q_surface.gather(1, candidate[:, None]).squeeze(1)
        residual = q_candidate - q_reference - target
        pair_mse = torch.mean(residual.square())
        gauge_mse = torch.mean(q_reference.square())
        loss = float(self.v04_config.loss_weights[2]) * (
            pair_mse + float(self.v04_config.beta) * gauge_mse
        )
        self.q3_optimizer.zero_grad(set_to_none=True)
        loss.backward()
        assert_finite_loss(loss, objective=3)
        assert_finite_gradients(self.q3.parameters(), objective=3)
        self.q3_optimizer.step()
        self.q3_update_count += 1
        assert_finite_parameters(self.q_nets)
        self._assert_exact_three_networks()
        return {
            "route": "C3",
            "batch_size": int(states.shape[0]),
            "loss": float(loss.detach().cpu()),
            "pair_mse": float(pair_mse.detach().cpu()),
            "gauge_mse": float(gauge_mse.detach().cpu()),
            "update_count": self.q3_update_count,
        }

    def update_route(
        self,
        route: str,
        batch: EEAxisPairBatch,
    ) -> dict[str, float | int | str]:
        """Compatibility spelling that rejects any frozen-route update."""

        if route != "C3":
            raise MCRLContractError("V0.4 hybrid exposes a training update only for C3")
        return self.update_c3(batch)

    def checkpoint_state(self) -> dict[str, Any]:
        """Serialize the hybrid with route order and frozen lineage attached."""

        return {
            "format_version": HYBRID_CHECKPOINT_VERSION,
            "algorithm": HYBRID_ALGORITHM,
            "initialization_seed": self.initialization_seed,
            "selected_q3_rung": self.selected_q3_rung,
            "q3_update_count": self.q3_update_count,
            "v03_config": asdict(self.v03_config),
            "v04_config": asdict(self.v04_config),
            "route_order": list(HYBRID_ROUTE_ORDER),
            "frozen_lineage": [lineage.as_dict() for lineage in self.frozen_lineage],
            "q_networks": [
                {
                    key: value.detach().cpu().clone()
                    for key, value in network.state_dict().items()
                }
                for network in self.q_nets
            ],
            "q3_optimizer": self.q3_optimizer.state_dict(),
        }

    def load_checkpoint_state(self, state: Mapping[str, Any]) -> int:
        """Reload one selected hybrid without ever replacing frozen Q1/Q2.

        The serialized Q1/Q2 tensors are receipts: they must be bit-identical
        to the heads already reconstructed from the sealed V0.3 checkpoint.
        Only the selected Q3 tensors and its sole optimizer are loaded.
        """

        if not isinstance(state, Mapping):
            raise MCRLContractError("hybrid checkpoint must be a mapping")
        if state.get("format_version") != HYBRID_CHECKPOINT_VERSION:
            raise MCRLContractError("hybrid checkpoint format mismatch")
        if state.get("algorithm") != HYBRID_ALGORITHM:
            raise MCRLContractError("hybrid checkpoint algorithm mismatch")
        if state.get("initialization_seed") != self.initialization_seed:
            raise MCRLContractError("hybrid checkpoint initialization seed mismatch")
        if state.get("selected_q3_rung") != self.selected_q3_rung:
            raise MCRLContractError("hybrid checkpoint selected_q3_rung mismatch")
        if state.get("v03_config") != asdict(self.v03_config) or state.get(
            "v04_config"
        ) != asdict(self.v04_config):
            raise MCRLContractError("hybrid checkpoint learner config mismatch")
        if state.get("route_order") != list(HYBRID_ROUTE_ORDER):
            raise MCRLContractError("hybrid checkpoint route order mismatch")
        expected_lineage = [lineage.as_dict() for lineage in self.frozen_lineage]
        if state.get("frozen_lineage") != expected_lineage:
            raise MCRLContractError("hybrid checkpoint frozen-head lineage mismatch")
        update_count = _strict_int(
            state.get("q3_update_count"),
            field="hybrid checkpoint q3_update_count",
            minimum=1,
        )
        if update_count != self.selected_q3_rung:
            raise MCRLContractError(
                "hybrid checkpoint update count must equal selected_q3_rung"
            )
        networks = state.get("q_networks")
        if not isinstance(networks, list) or len(networks) != 3:
            raise MCRLContractError("hybrid checkpoint must contain exactly three heads")
        for route_index in (0, 1):
            supplied = networks[route_index]
            expected = self.q_nets[route_index].state_dict()
            if not isinstance(supplied, Mapping) or set(supplied) != set(expected):
                raise MCRLContractError("hybrid checkpoint frozen-head receipt mismatch")
            for name, expected_tensor in expected.items():
                observed = supplied[name]
                if not isinstance(observed, torch.Tensor) or not torch.equal(
                    observed.detach().cpu(), expected_tensor.detach().cpu()
                ):
                    raise MCRLContractError(
                        "hybrid checkpoint frozen-head tensor drifted"
                    )
        q3_state = networks[2]
        optimizer_state = state.get("q3_optimizer")
        if not isinstance(q3_state, Mapping) or not isinstance(
            optimizer_state, Mapping
        ):
            raise MCRLContractError("hybrid checkpoint Q3 payload is malformed")
        try:
            self.q3.load_state_dict(q3_state, strict=True)
            self.q3_optimizer.load_state_dict(optimizer_state)
        except (RuntimeError, TypeError, ValueError) as error:
            raise MCRLContractError("hybrid checkpoint Q3 state is incompatible") from error
        self.q3_update_count = update_count
        assert_finite_parameters(self.q_nets)
        self._assert_exact_three_networks()
        return update_count


__all__ = [
    "HYBRID_ALGORITHM",
    "HYBRID_CHECKPOINT_VERSION",
    "V03_FALLBACK_CHECKPOINT_SCHEMA",
    "V03_FROZEN_RUNG",
    "FrozenMeanMaxCheckpointSpec",
    "FrozenMeanMaxHeadLineage",
    "FrozenMeanMaxHeadPair",
    "extract_frozen_meanmax_head",
    "load_frozen_meanmax_head_pair",
    "EEAxisV04HybridTrainer",
]
