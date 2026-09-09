"""Complete signed ZR pair rows for the deployable V0.14 Q3 state."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

import numpy as np

from ..algorithms.ee_axis_pairwise import EEAxisPairBatch
from ..env.action_contract import NUM_ACTIONS
from ..errors import MCRLContractError
from .ee_axis_v014_q3_state import (
    EEAxisV014Q3StateObservation,
    V014_Q3_STATE_DIM,
)
from .ee_axis_zero_marginal_c3 import ZeroMarginalC3Surface


class EEAxisV014Q3PairError(MCRLContractError):
    """A V0.14 state and ZR teacher panel cannot form safe pair rows."""


def _anchor(value: object) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise EEAxisV014Q3PairError("anchor must be lowercase SHA-256")
    return value


def _readonly(value: np.ndarray) -> np.ndarray:
    result = np.array(value, copy=True, order="C")
    result.setflags(write=False)
    return result


@dataclass(frozen=True)
class EEAxisV014Q3PairDataset:
    """Q3 pair batch plus whole-anchor validation metadata."""

    batch: EEAxisPairBatch
    source_seeds: np.ndarray
    anchor_sha256s: np.ndarray

    def verify(self) -> None:
        try:
            self.batch.validate(
                state_dim=V014_Q3_STATE_DIM, action_dim=NUM_ACTIONS
            )
        except (TypeError, ValueError, MCRLContractError) as error:
            raise EEAxisV014Q3PairError("Q3 pair batch is invalid") from error
        count = int(np.asarray(self.batch.states).shape[0])
        seeds = np.asarray(self.source_seeds)
        anchors = np.asarray(self.anchor_sha256s, dtype=object)
        if (
            count < 1
            or seeds.shape != (count,)
            or anchors.shape != (count,)
            or not np.issubdtype(seeds.dtype, np.integer)
            or np.any(seeds < 0)
        ):
            raise EEAxisV014Q3PairError("Q3 pair metadata does not align")
        for value in anchors.tolist():
            _anchor(value)


def build_ee_axis_v014_q3_pair_dataset(
    *,
    state: EEAxisV014Q3StateObservation,
    surfaces: Sequence[ZeroMarginalC3Surface],
    source_seed: int,
    anchor_sha256s: Sequence[str],
) -> EEAxisV014Q3PairDataset:
    """Emit all legal non-reference ZR comparisons without sign filtering."""

    if not isinstance(state, EEAxisV014Q3StateObservation):
        raise EEAxisV014Q3PairError("state must be a V0.14 Q3 observation")
    try:
        state.verify()
    except (TypeError, ValueError, MCRLContractError) as error:
        raise EEAxisV014Q3PairError("V0.14 Q3 state is invalid") from error
    if (
        isinstance(source_seed, bool)
        or not isinstance(source_seed, int)
        or source_seed < 0
    ):
        raise EEAxisV014Q3PairError("source_seed must be nonnegative integer")
    try:
        teachers = tuple(surfaces)
        anchors = tuple(anchor_sha256s)
    except TypeError as error:
        raise EEAxisV014Q3PairError("surfaces and anchors must be sequences") from error
    users = int(state.state_matrix.shape[0])
    if len(teachers) != users:
        raise EEAxisV014Q3PairError("one ZR surface is required per state row")
    if len(anchors) != users:
        raise EEAxisV014Q3PairError("one anchor is required per state row")
    anchors = tuple(_anchor(value) for value in anchors)

    states: list[np.ndarray] = []
    references: list[int] = []
    candidates: list[int] = []
    targets: list[float] = []
    masks: list[np.ndarray] = []
    row_seeds: list[int] = []
    row_anchors: list[str] = []
    for uid, surface in enumerate(teachers):
        if not isinstance(surface, ZeroMarginalC3Surface) or surface.formula != "ZR":
            raise EEAxisV014Q3PairError("Q3 teacher must be a ZR surface")
        legal = np.asarray(surface.legal_mask, dtype=np.bool_)
        if not np.array_equal(legal, state.action_masks[uid]):
            raise EEAxisV014Q3PairError("Q3 teacher and deployable-state mask differ")
        reference = surface.reference_action
        if reference < 0 or reference >= NUM_ACTIONS or not bool(legal[reference]):
            raise EEAxisV014Q3PairError("Q3 reference action must be legal")
        for candidate in np.flatnonzero(legal).tolist():
            if candidate == reference:
                continue
            target = float(
                surface.z3_bits[candidate] - surface.z3_bits[reference]
            )
            if not np.isfinite(target):
                raise EEAxisV014Q3PairError("Q3 pair target is non-finite")
            states.append(state.state_matrix[uid])
            references.append(reference)
            candidates.append(candidate)
            targets.append(target)
            masks.append(legal)
            row_seeds.append(source_seed)
            row_anchors.append(anchors[uid])
    if not states:
        raise EEAxisV014Q3PairError("Q3 source contains no legal comparison")

    batch = EEAxisPairBatch(
        states=_readonly(np.stack(states).astype(np.float32, copy=False)),
        reference_actions=_readonly(np.asarray(references, dtype=np.int64)),
        candidate_actions=_readonly(np.asarray(candidates, dtype=np.int64)),
        target_surplus_bits=_readonly(np.asarray(targets, dtype=np.float64)),
        action_masks=_readonly(np.stack(masks).astype(np.bool_, copy=False)),
    )
    result = EEAxisV014Q3PairDataset(
        batch=batch,
        source_seeds=_readonly(np.asarray(row_seeds, dtype=np.int64)),
        anchor_sha256s=_readonly(np.asarray(row_anchors, dtype=object)),
    )
    result.verify()
    return result


__all__ = [
    "EEAxisV014Q3PairDataset",
    "EEAxisV014Q3PairError",
    "build_ee_axis_v014_q3_pair_dataset",
]
