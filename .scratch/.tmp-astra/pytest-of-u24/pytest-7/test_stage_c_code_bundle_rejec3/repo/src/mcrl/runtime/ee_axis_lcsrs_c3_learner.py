"""Fixed class-balanced source learner for the V0.23 LC-SRS C3 gate."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import struct
from typing import Sequence

import numpy as np
import torch
import torch.optim as optim

from ..algorithms.ee_axis_lcsrs_c3_head import LCSRSC3QNetwork
from ..errors import MCRLContractError
from .ee_axis_lcsrs_c3_dataset import (
    LCSRS_ROW_CONTROL,
    LCSRS_ROW_REFERENCE,
    LCSRS_ROW_SUPPORTED,
    LCSRSAnchorSurface,
)
from .finiteness import (
    assert_finite_gradients,
    assert_finite_loss,
    assert_finite_parameters,
)


LCSRS_C3_LEARNER_ALGORITHM = "multi-catfish-mcrl-v023-lcsrs-c3-source-learner"
LCSRS_C3_BATCH_SIZE = 256
LCSRS_C3_UPDATE_COUNT = 2000
LCSRS_C3_LEARNING_RATE = 1.0e-3
LCSRS_C3_ADAM_BETAS = (0.9, 0.999)
LCSRS_C3_ADAM_EPSILON = 1.0e-8
LCSRS_C3_WEIGHT_DECAY = 0.0
LCSRS_C3_CLASS_ORDER = (
    LCSRS_ROW_SUPPORTED,
    LCSRS_ROW_REFERENCE,
    LCSRS_ROW_CONTROL,
)


class LCSRSC3LearnerError(MCRLContractError):
    """A frozen LC-SRS learner, sampler, or source boundary was violated."""


@dataclass(frozen=True)
class LCSRSC3LearnerConfig:
    """Non-tunable source learner declaration."""

    batch_size: int = LCSRS_C3_BATCH_SIZE
    updates: int = LCSRS_C3_UPDATE_COUNT
    learning_rate: float = LCSRS_C3_LEARNING_RATE
    adam_betas: tuple[float, float] = LCSRS_C3_ADAM_BETAS
    adam_epsilon: float = LCSRS_C3_ADAM_EPSILON
    weight_decay: float = LCSRS_C3_WEIGHT_DECAY
    loss_multiplier: float = 3.0
    sampler: str = "anchor-uniform-class-uniform-row-uniform-with-replacement"
    rng: str = "numpy-pcg64"

    def __post_init__(self) -> None:
        if (
            self.batch_size != LCSRS_C3_BATCH_SIZE
            or self.updates != LCSRS_C3_UPDATE_COUNT
            or self.learning_rate != LCSRS_C3_LEARNING_RATE
            or self.adam_betas != LCSRS_C3_ADAM_BETAS
            or self.adam_epsilon != LCSRS_C3_ADAM_EPSILON
            or self.weight_decay != LCSRS_C3_WEIGHT_DECAY
            or self.loss_multiplier != 3.0
            or self.sampler
            != "anchor-uniform-class-uniform-row-uniform-with-replacement"
            or self.rng != "numpy-pcg64"
        ):
            raise ValueError("V0.23 LC-SRS learner configuration is frozen")


LCSRS_C3_LEARNER_CONFIG = LCSRSC3LearnerConfig()
LCSRS_C3_LEARNER_CONFIG_SHA256 = hashlib.sha256(
    json.dumps(
        asdict(LCSRS_C3_LEARNER_CONFIG),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("ascii")
).hexdigest()


def _readonly(value: object, *, dtype: np.dtype) -> np.ndarray:
    try:
        result = np.array(value, dtype=dtype, copy=True, order="C")
    except (TypeError, ValueError, OverflowError) as error:
        raise LCSRSC3LearnerError("sampled batch array is malformed") from error
    result.setflags(write=False)
    return result


@dataclass(frozen=True)
class LCSRSC3SampledBatch:
    """One exact anchor/class/row-uniform mini-batch."""

    anchor_indices: np.ndarray
    row_classes: np.ndarray
    user_indices: np.ndarray
    action_indices: np.ndarray
    normalized_targets: np.ndarray

    def __post_init__(self) -> None:
        anchors = _readonly(self.anchor_indices, dtype=np.dtype(np.int64))
        classes = _readonly(self.row_classes, dtype=np.dtype(np.uint8))
        users = _readonly(self.user_indices, dtype=np.dtype(np.int64))
        actions = _readonly(self.action_indices, dtype=np.dtype(np.int64))
        targets = _readonly(self.normalized_targets, dtype=np.dtype(np.float32))
        size = int(anchors.size)
        if size < 1 or any(
            array.shape != (size,) for array in (classes, users, actions, targets)
        ):
            raise LCSRSC3LearnerError("sampled batch columns must be aligned vectors")
        if np.any(anchors < 0) or np.any(users < 0) or np.any(actions < 0):
            raise LCSRSC3LearnerError("sampled indices must be nonnegative")
        if not np.all(np.isin(classes, np.asarray(LCSRS_C3_CLASS_ORDER))):
            raise LCSRSC3LearnerError("sampled row class is outside S/R/C")
        if not np.all(np.isfinite(targets)):
            raise LCSRSC3LearnerError("sampled targets must be finite")
        object.__setattr__(self, "anchor_indices", anchors)
        object.__setattr__(self, "row_classes", classes)
        object.__setattr__(self, "user_indices", users)
        object.__setattr__(self, "action_indices", actions)
        object.__setattr__(self, "normalized_targets", targets)

    @property
    def rows(self) -> int:
        return int(self.anchor_indices.size)


class LCSRSC3ClassBalancedSampler:
    """Frozen PCG64 sampler implementing the displayed three-class loss."""

    def __init__(
        self,
        surfaces: Sequence[LCSRSAnchorSurface],
        *,
        student_seed: int,
        normalized_targets_by_anchor: Sequence[np.ndarray] | None = None,
    ) -> None:
        if isinstance(student_seed, bool) or not isinstance(student_seed, int):
            raise TypeError("student_seed must be an integer")
        if student_seed < 0:
            raise ValueError("student_seed must be nonnegative")
        self.surfaces = tuple(surfaces)
        if not self.surfaces:
            raise LCSRSC3LearnerError("source learner needs a retained anchor")
        raw_targets = (
            tuple(surface.normalized_targets for surface in self.surfaces)
            if normalized_targets_by_anchor is None
            else tuple(normalized_targets_by_anchor)
        )
        if len(raw_targets) != len(self.surfaces):
            raise LCSRSC3LearnerError("target override count must equal anchor count")
        targets: list[np.ndarray] = []
        for surface, value in zip(self.surfaces, raw_targets, strict=True):
            target = _readonly(value, dtype=np.dtype(np.float32))
            if target.shape != surface.normalized_targets.shape or not np.all(
                np.isfinite(target)
            ):
                raise LCSRSC3LearnerError("target override has the wrong shape or values")
            if np.any(target[surface.row_class != LCSRS_ROW_SUPPORTED] != 0.0):
                raise LCSRSC3LearnerError("only SUPPORTED target overrides may be nonzero")
            targets.append(target)
        self.normalized_targets_by_anchor = tuple(targets)
        self._cells: tuple[tuple[np.ndarray, ...], ...] = tuple(
            tuple(surface.cells_for_class(row_class) for row_class in LCSRS_C3_CLASS_ORDER)
            for surface in self.surfaces
        )
        for surface, classes in zip(self.surfaces, self._cells, strict=True):
            surface.view.verify()
            if any(cells.shape[0] < 1 for cells in classes):
                raise LCSRSC3LearnerError("each retained anchor needs nonempty S/R/C")
        self.rng = np.random.Generator(np.random.PCG64(student_seed))

    def draw(self, batch_size: int = LCSRS_C3_BATCH_SIZE) -> LCSRSC3SampledBatch:
        if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size < 1:
            raise ValueError("batch_size must be a positive integer")
        anchors = self.rng.integers(0, len(self.surfaces), size=batch_size, dtype=np.int64)
        class_offsets = self.rng.integers(0, 3, size=batch_size, dtype=np.int64)
        users = np.empty(batch_size, dtype=np.int64)
        actions = np.empty(batch_size, dtype=np.int64)
        targets = np.empty(batch_size, dtype=np.float32)
        for row, (anchor, class_offset) in enumerate(
            zip(anchors.tolist(), class_offsets.tolist(), strict=True)
        ):
            cells = self._cells[anchor][class_offset]
            chosen = int(self.rng.integers(0, cells.shape[0]))
            users[row], actions[row] = cells[chosen]
            targets[row] = self.normalized_targets_by_anchor[anchor][users[row], actions[row]]
        classes = np.asarray(
            [LCSRS_C3_CLASS_ORDER[offset] for offset in class_offsets],
            dtype=np.uint8,
        )
        return LCSRSC3SampledBatch(
            anchor_indices=anchors,
            row_classes=classes,
            user_indices=users,
            action_indices=actions,
            normalized_targets=targets,
        )


def score_sampled_cells(
    network: LCSRSC3QNetwork,
    surfaces: Sequence[LCSRSAnchorSurface],
    batch: LCSRSC3SampledBatch,
    *,
    device: torch.device | str = "cpu",
) -> torch.Tensor:
    """Score a heterogeneous mini-batch with one shared token-scorer call."""

    if not isinstance(network, LCSRSC3QNetwork):
        raise TypeError("network must be the frozen LC-SRS C3 head")
    source = tuple(surfaces)
    if not source:
        raise LCSRSC3LearnerError("source learner needs a retained anchor")
    if np.any(batch.anchor_indices >= len(source)):
        raise LCSRSC3LearnerError("sampled anchor is outside the source")
    target_device = torch.device(device)
    feature_blocks: list[np.ndarray] = []
    segment_rows: list[int] = []
    for row, (anchor_index, user, action) in enumerate(
        zip(
            batch.anchor_indices.tolist(),
            batch.user_indices.tolist(),
            batch.action_indices.tolist(),
            strict=True,
        )
    ):
        surface = source[int(anchor_index)]
        view = surface.view
        if surface.row_class[int(user), int(action)] != batch.row_classes[row]:
            raise LCSRSC3LearnerError("sampled class disagrees with source surface")
        if not view.action_mask[int(user), int(action)]:
            raise LCSRSC3LearnerError("sampled cell is not legal")
        reference = int(view.reference_actions[int(user)])
        if int(action) == reference:
            continue
        for segment, cell_action in ((2 * row, int(action)), (2 * row + 1, reference)):
            active = np.flatnonzero(view.token_mask[int(user), cell_action])
            if active.size < 1:
                raise LCSRSC3LearnerError("legal sampled cell lacks an active token")
            context = np.repeat(
                view.action_context[int(user), cell_action][None, :],
                active.size,
                axis=0,
            )
            feature_blocks.append(
                np.concatenate((context, view.tokens[int(user), cell_action, active]), axis=1)
            )
            segment_rows.extend([segment] * int(active.size))
    if not feature_blocks:
        parameter = next(network.parameters())
        return parameter.sum().mul(0.0).expand(batch.rows)
    features = torch.tensor(
        np.concatenate(feature_blocks, axis=0),
        dtype=torch.float32,
        device=target_device,
    )
    segments = torch.tensor(segment_rows, dtype=torch.int64, device=target_device)
    contributions = network.token_scorer(features).squeeze(1)
    totals = contributions.new_zeros(batch.rows * 2).index_add(0, segments, contributions)
    return totals[0::2] - totals[1::2]


def lcsrs_c3_training_step(
    network: LCSRSC3QNetwork,
    optimizer: optim.Optimizer,
    surfaces: Sequence[LCSRSAnchorSurface],
    batch: LCSRSC3SampledBatch,
    *,
    device: torch.device | str = "cpu",
) -> float:
    """Apply one fixed unbiased stochastic estimate of the three-class loss."""

    optimizer.zero_grad(set_to_none=True)
    predictions = score_sampled_cells(network, surfaces, batch, device=device)
    targets = torch.tensor(
        np.asarray(batch.normalized_targets), dtype=torch.float32, device=predictions.device
    )
    loss = 3.0 * torch.mean(torch.square(predictions - targets))
    assert_finite_loss(loss, objective=2)
    loss.backward()
    assert_finite_gradients(network.parameters(), objective=2)
    optimizer.step()
    assert_finite_parameters((network,))
    return float(loss.detach().cpu().item())


def make_lcsrs_c3_student(
    *, student_seed: int, device: torch.device | str = "cpu"
) -> tuple[LCSRSC3QNetwork, optim.Adam]:
    """Create one exactly initialized student and its frozen Adam optimizer."""

    if isinstance(student_seed, bool) or not isinstance(student_seed, int):
        raise TypeError("student_seed must be an integer")
    torch.manual_seed(student_seed)
    network = LCSRSC3QNetwork().to(torch.device(device))
    optimizer = optim.Adam(
        network.parameters(),
        lr=LCSRS_C3_LEARNING_RATE,
        betas=LCSRS_C3_ADAM_BETAS,
        eps=LCSRS_C3_ADAM_EPSILON,
        weight_decay=LCSRS_C3_WEIGHT_DECAY,
    )
    return network, optimizer


def lcsrs_c3_network_sha256(network: LCSRSC3QNetwork) -> str:
    """Hash one C3 parameter state without pickle or device-dependent bytes."""

    if not isinstance(network, LCSRSC3QNetwork):
        raise TypeError("network must be the frozen LC-SRS C3 head")
    digest = hashlib.sha256()
    digest.update(LCSRS_C3_LEARNER_ALGORITHM.encode("ascii"))
    for name, tensor in sorted(network.state_dict().items()):
        encoded = name.encode("utf-8")
        array = np.ascontiguousarray(tensor.detach().cpu().numpy())
        digest.update(struct.pack(">I", len(encoded)))
        digest.update(encoded)
        digest.update(array.dtype.str.encode("ascii"))
        digest.update(repr(tuple(array.shape)).encode("ascii"))
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _target_source_sha256(
    surfaces: tuple[LCSRSAnchorSurface, ...], targets: tuple[np.ndarray, ...]
) -> str:
    digest = hashlib.sha256()
    digest.update(b"multi-catfish-mcrl-v023-lcsrs-fitting-source-v1")
    for surface, target in zip(surfaces, targets, strict=True):
        digest.update(surface.content_digest.encode("ascii"))
        array = np.ascontiguousarray(target, dtype=np.float32)
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


@dataclass(frozen=True)
class LCSRSC3FitReceipt:
    """One fixed 2000-update INFORMED or MATCHED-PLACEBO fit receipt."""

    arm: str
    student_seed: int
    source_anchor_sha256s: tuple[str, ...]
    target_source_sha256: str
    initial_network_sha256: str
    final_network_sha256: str
    losses: np.ndarray
    config_sha256: str = LCSRS_C3_LEARNER_CONFIG_SHA256
    updates: int = LCSRS_C3_UPDATE_COUNT
    batch_size: int = LCSRS_C3_BATCH_SIZE

    def __post_init__(self) -> None:
        if self.arm not in {"INFORMED", "MATCHED_PLACEBO"}:
            raise LCSRSC3LearnerError("fit arm must be INFORMED or MATCHED_PLACEBO")
        if (
            isinstance(self.student_seed, bool)
            or not isinstance(self.student_seed, int)
            or self.student_seed < 0
        ):
            raise LCSRSC3LearnerError("fit student_seed must be nonnegative")
        if not self.source_anchor_sha256s:
            raise LCSRSC3LearnerError("fit receipt needs source anchors")
        for field in (
            self.target_source_sha256,
            self.initial_network_sha256,
            self.final_network_sha256,
            self.config_sha256,
            *self.source_anchor_sha256s,
        ):
            if (
                not isinstance(field, str)
                or len(field) != 64
                or any(character not in "0123456789abcdef" for character in field)
            ):
                raise LCSRSC3LearnerError("fit receipt contains a malformed SHA-256")
        losses = _readonly(self.losses, dtype=np.dtype(np.float64))
        if losses.shape != (LCSRS_C3_UPDATE_COUNT,) or not np.all(np.isfinite(losses)):
            raise LCSRSC3LearnerError("fit receipt needs exactly 2000 finite losses")
        if self.config_sha256 != LCSRS_C3_LEARNER_CONFIG_SHA256:
            raise LCSRSC3LearnerError("fit learner configuration hash drifted")
        if self.updates != LCSRS_C3_UPDATE_COUNT or self.batch_size != LCSRS_C3_BATCH_SIZE:
            raise LCSRSC3LearnerError("fit update or batch budget drifted")
        object.__setattr__(self, "losses", losses)


def fit_lcsrs_c3_source(
    surfaces: Sequence[LCSRSAnchorSurface],
    *,
    arm: str,
    student_seed: int,
    normalized_targets_by_anchor: Sequence[np.ndarray] | None = None,
    device: torch.device | str = "cpu",
) -> tuple[LCSRSC3QNetwork, LCSRSC3FitReceipt]:
    """Run exactly one frozen 2000-update source fit; no early selection."""

    if arm == "INFORMED" and normalized_targets_by_anchor is not None:
        raise LCSRSC3LearnerError("INFORMED must use the authenticated source targets")
    if arm == "MATCHED_PLACEBO" and normalized_targets_by_anchor is None:
        raise LCSRSC3LearnerError("MATCHED_PLACEBO requires its frozen target permutation")
    if arm not in {"INFORMED", "MATCHED_PLACEBO"}:
        raise LCSRSC3LearnerError("fit arm must be INFORMED or MATCHED_PLACEBO")
    source = tuple(surfaces)
    network, optimizer = make_lcsrs_c3_student(student_seed=student_seed, device=device)
    initial = lcsrs_c3_network_sha256(network)
    sampler = LCSRSC3ClassBalancedSampler(
        source,
        student_seed=student_seed,
        normalized_targets_by_anchor=normalized_targets_by_anchor,
    )
    losses = np.empty(LCSRS_C3_UPDATE_COUNT, dtype=np.float64)
    for update in range(LCSRS_C3_UPDATE_COUNT):
        batch = sampler.draw(LCSRS_C3_BATCH_SIZE)
        losses[update] = lcsrs_c3_training_step(
            network, optimizer, source, batch, device=device
        )
    targets = sampler.normalized_targets_by_anchor
    receipt = LCSRSC3FitReceipt(
        arm=arm,
        student_seed=student_seed,
        source_anchor_sha256s=tuple(surface.content_digest for surface in source),
        target_source_sha256=_target_source_sha256(source, targets),
        initial_network_sha256=initial,
        final_network_sha256=lcsrs_c3_network_sha256(network),
        losses=losses,
    )
    return network, receipt


__all__ = [
    "LCSRS_C3_LEARNER_ALGORITHM",
    "LCSRS_C3_BATCH_SIZE",
    "LCSRS_C3_UPDATE_COUNT",
    "LCSRS_C3_LEARNER_CONFIG",
    "LCSRS_C3_LEARNER_CONFIG_SHA256",
    "LCSRSC3LearnerError",
    "LCSRSC3LearnerConfig",
    "LCSRSC3SampledBatch",
    "LCSRSC3ClassBalancedSampler",
    "score_sampled_cells",
    "lcsrs_c3_training_step",
    "make_lcsrs_c3_student",
    "lcsrs_c3_network_sha256",
    "LCSRSC3FitReceipt",
    "fit_lcsrs_c3_source",
]
