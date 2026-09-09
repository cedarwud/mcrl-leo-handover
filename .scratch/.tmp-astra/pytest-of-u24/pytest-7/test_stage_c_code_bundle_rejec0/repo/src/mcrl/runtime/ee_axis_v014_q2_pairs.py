"""Complete legal-action pair rows for the V0.14 OPS3-Q2 learner."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..algorithms.ee_axis_pairwise import EEAxisPairBatch
from ..env.action_contract import NUM_ACTIONS
from ..errors import MCRLContractError
from .ee_axis_ops3 import OPS3Surface
from .ee_axis_v014_q2_state import (
    V014_Q2_STATE_DIM,
    encode_ee_axis_v014_q2_states,
)


class EEAxisV014Q2PairError(MCRLContractError):
    """A labeled OPS3 source cannot form a complete safe pair dataset."""


def _anchor(value: object) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise EEAxisV014Q2PairError("anchor_sha256 must be lowercase SHA-256")
    return value


@dataclass(frozen=True)
class V014Q2LabeledSurface:
    """One OPS3 teacher surface with TRAIN/validation grouping metadata."""

    surface: OPS3Surface
    source_seed: int
    anchor_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.surface, OPS3Surface):
            raise EEAxisV014Q2PairError("surface must be OPS3Surface")
        if (
            isinstance(self.source_seed, bool)
            or not isinstance(self.source_seed, int)
            or self.source_seed < 0
        ):
            raise EEAxisV014Q2PairError("source_seed must be nonnegative integer")
        _anchor(self.anchor_sha256)


@dataclass(frozen=True)
class EEAxisV014Q2PairDataset:
    """Pair batch plus metadata for anchor-then-seed validation."""

    batch: EEAxisPairBatch
    source_seeds: np.ndarray
    anchor_sha256s: np.ndarray

    def verify(self) -> None:
        try:
            self.batch.validate(
                state_dim=V014_Q2_STATE_DIM, action_dim=NUM_ACTIONS
            )
        except (TypeError, ValueError, MCRLContractError) as error:
            raise EEAxisV014Q2PairError("Q2 pair batch is invalid") from error
        rows = int(np.asarray(self.batch.states).shape[0])
        seeds = np.asarray(self.source_seeds)
        anchors = np.asarray(self.anchor_sha256s, dtype=object)
        if (
            rows < 1
            or seeds.shape != (rows,)
            or anchors.shape != (rows,)
            or not np.issubdtype(seeds.dtype, np.integer)
            or np.any(seeds < 0)
        ):
            raise EEAxisV014Q2PairError("Q2 pair metadata does not align")
        for value in anchors.tolist():
            _anchor(value)


def _readonly(value: np.ndarray) -> np.ndarray:
    result = np.array(value, copy=True, order="C")
    result.setflags(write=False)
    return result


def build_ee_axis_v014_q2_pair_dataset(
    sources: tuple[V014Q2LabeledSurface, ...] | list[V014Q2LabeledSurface],
) -> EEAxisV014Q2PairDataset:
    """Emit every legal non-reference action without sign filtering."""

    try:
        rows = tuple(sources)
    except TypeError as error:
        raise EEAxisV014Q2PairError("sources must be a sequence") from error
    if not rows:
        raise EEAxisV014Q2PairError("sources must be nonempty")
    if any(not isinstance(row, V014Q2LabeledSurface) for row in rows):
        raise EEAxisV014Q2PairError("sources contain an invalid labeled surface")

    encoded = encode_ee_axis_v014_q2_states(
        tuple(row.surface for row in rows)
    )
    states: list[np.ndarray] = []
    references: list[int] = []
    candidates: list[int] = []
    targets: list[float] = []
    masks: list[np.ndarray] = []
    seeds: list[int] = []
    anchors: list[str] = []
    for index, row in enumerate(rows):
        surface = row.surface
        reference = surface.reference_action
        legal = np.asarray(surface.legal_mask, dtype=np.bool_)
        if reference < 0 or reference >= NUM_ACTIONS or not bool(legal[reference]):
            raise EEAxisV014Q2PairError("OPS3 reference action must be legal")
        for candidate in np.flatnonzero(legal).tolist():
            if candidate == reference:
                continue
            target = float(
                surface.z2_bits[candidate] - surface.z2_bits[reference]
            )
            if not np.isfinite(target):
                raise EEAxisV014Q2PairError("Q2 pair target is non-finite")
            states.append(encoded.state_matrix[index])
            references.append(reference)
            candidates.append(candidate)
            targets.append(target)
            masks.append(legal)
            seeds.append(row.source_seed)
            anchors.append(row.anchor_sha256)
    if not states:
        raise EEAxisV014Q2PairError("sources contain no legal comparison")

    batch = EEAxisPairBatch(
        states=_readonly(np.stack(states).astype(np.float32, copy=False)),
        reference_actions=_readonly(np.asarray(references, dtype=np.int64)),
        candidate_actions=_readonly(np.asarray(candidates, dtype=np.int64)),
        target_surplus_bits=_readonly(np.asarray(targets, dtype=np.float64)),
        action_masks=_readonly(np.stack(masks).astype(np.bool_, copy=False)),
    )
    dataset = EEAxisV014Q2PairDataset(
        batch=batch,
        source_seeds=_readonly(np.asarray(seeds, dtype=np.int64)),
        anchor_sha256s=_readonly(np.asarray(anchors, dtype=object)),
    )
    dataset.verify()
    return dataset


__all__ = [
    "EEAxisV014Q2PairDataset",
    "EEAxisV014Q2PairError",
    "V014Q2LabeledSurface",
    "build_ee_axis_v014_q2_pair_dataset",
]
