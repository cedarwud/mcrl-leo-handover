"""Unique anchor-level LC-SRS teacher surfaces for the V0.23 source gate."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct

import numpy as np

from ..errors import MCRLContractError
from .ee_axis_lcsrs_c3_state import C3View, LCSRS_ACTION_DIM


LCSRS_DRAW_COUNT = 32
LCSRS_ROW_MASKED = np.uint8(0)
LCSRS_ROW_REFERENCE = np.uint8(1)
LCSRS_ROW_CONTROL = np.uint8(2)
LCSRS_ROW_SUPPORTED = np.uint8(3)


class LCSRSC3DatasetError(MCRLContractError):
    """An LC-SRS pair or unique anchor surface violates the frozen contract."""


def _readonly(value: object, *, dtype: np.dtype) -> np.ndarray:
    try:
        result = np.array(value, dtype=dtype, copy=True, order="C")
    except (TypeError, ValueError, OverflowError) as error:
        raise LCSRSC3DatasetError("LC-SRS dataset array cannot be materialised") from error
    result.setflags(write=False)
    return result


def _digest_array(digest: "hashlib._Hash", name: str, value: np.ndarray) -> None:
    array = np.ascontiguousarray(value)
    digest.update(name.encode("ascii"))
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes(order="C"))


@dataclass(frozen=True)
class LCSRSPairTargets:
    """The two normalized member labels across exactly 32 matched draws."""

    pair_id: str
    user_ids: np.ndarray
    action_ids: np.ndarray
    normalized_targets_by_draw: np.ndarray

    def __post_init__(self) -> None:
        if not isinstance(self.pair_id, str) or not self.pair_id:
            raise LCSRSC3DatasetError("pair_id must be a nonempty receipt identifier")
        users = _readonly(self.user_ids, dtype=np.dtype(np.int64))
        actions = _readonly(self.action_ids, dtype=np.dtype(np.int64))
        targets = _readonly(
            self.normalized_targets_by_draw,
            dtype=np.dtype(np.float64),
        )
        if users.shape != (2,) or np.unique(users).size != 2:
            raise LCSRSC3DatasetError("LC-SRS pair must contain two unique users")
        if actions.shape != (2,):
            raise LCSRSC3DatasetError("LC-SRS pair must contain two actions")
        if targets.shape != (LCSRS_DRAW_COUNT, 2):
            raise LCSRSC3DatasetError("LC-SRS pair requires exactly 32 two-user draws")
        if not np.all(np.isfinite(targets)):
            raise LCSRSC3DatasetError("LC-SRS normalized targets must be finite")
        object.__setattr__(self, "user_ids", users)
        object.__setattr__(self, "action_ids", actions)
        object.__setattr__(self, "normalized_targets_by_draw", targets)

    @property
    def mean_targets(self) -> np.ndarray:
        result = np.mean(self.normalized_targets_by_draw, axis=0, dtype=np.float64)
        result.setflags(write=False)
        return result


def _surface_digest(
    view_digest: str,
    targets: np.ndarray,
    row_class: np.ndarray,
    pairs: tuple[LCSRSPairTargets, ...],
) -> str:
    digest = hashlib.sha256()
    digest.update(b"multi-catfish-mcrl-v023-lcsrs-anchor-surface-v1")
    digest.update(view_digest.encode("ascii"))
    _digest_array(digest, "targets", targets)
    _digest_array(digest, "row_class", row_class)
    for pair in pairs:
        encoded = pair.pair_id.encode("utf-8")
        digest.update(struct.pack(">I", len(encoded)))
        digest.update(encoded)
        _digest_array(digest, "pair_users", pair.user_ids)
        _digest_array(digest, "pair_actions", pair.action_ids)
        _digest_array(digest, "pair_draw_targets", pair.normalized_targets_by_draw)
    return digest.hexdigest()


def _anchor_record_digest(
    *,
    world_id: int,
    phase: int,
    anchor_id: str,
    surface_digest: str,
    q12_values: np.ndarray,
) -> str:
    digest = hashlib.sha256()
    digest.update(b"multi-catfish-mcrl-v023-lcsrs-anchor-record-v1")
    digest.update(struct.pack(">QI", world_id, phase))
    encoded = anchor_id.encode("utf-8")
    digest.update(struct.pack(">I", len(encoded)))
    digest.update(encoded)
    digest.update(surface_digest.encode("ascii"))
    _digest_array(digest, "q12", q12_values)
    return digest.hexdigest()


@dataclass(frozen=True)
class LCSRSAnchorSurface:
    """One non-overwriting S/R/C/MASKED surface for one immutable C3View."""

    view: C3View
    normalized_targets: np.ndarray
    row_class: np.ndarray
    pairs: tuple[LCSRSPairTargets, ...]
    content_digest: str = ""

    def __post_init__(self) -> None:
        self.view.verify()
        targets = _readonly(self.normalized_targets, dtype=np.dtype(np.float32))
        row_class = _readonly(self.row_class, dtype=np.dtype(np.uint8))
        users = int(self.view.action_context.shape[0])
        expected_shape = (users, LCSRS_ACTION_DIM)
        if targets.shape != expected_shape or row_class.shape != expected_shape:
            raise LCSRSC3DatasetError("anchor target/class surfaces have wrong shape")
        if not np.all(np.isfinite(targets)):
            raise LCSRSC3DatasetError("anchor targets must be finite")
        if np.any(~np.isin(row_class, np.arange(4, dtype=np.uint8))):
            raise LCSRSC3DatasetError("anchor row class is unknown")
        if np.any(row_class[~self.view.action_mask] != LCSRS_ROW_MASKED):
            raise LCSRSC3DatasetError("illegal cells must be MASKED")
        if np.any(row_class[self.view.action_mask] == LCSRS_ROW_MASKED):
            raise LCSRSC3DatasetError("legal cells cannot be MASKED")
        rows = np.arange(users)
        if np.any(row_class[rows, self.view.reference_actions] != LCSRS_ROW_REFERENCE):
            raise LCSRSC3DatasetError("every reference cell must be REFERENCE")
        zero = row_class != LCSRS_ROW_SUPPORTED
        if np.any(targets[zero] != 0.0):
            raise LCSRSC3DatasetError("only SUPPORTED cells may have nonzero targets")
        for required in (
            LCSRS_ROW_SUPPORTED,
            LCSRS_ROW_REFERENCE,
            LCSRS_ROW_CONTROL,
        ):
            if not np.any(row_class == required):
                raise LCSRSC3DatasetError("fitting anchor requires nonempty S/R/C classes")
        pairs = tuple(self.pairs)
        pair_ids: set[str] = set()
        pair_users: set[int] = set()
        supported_cells: set[tuple[int, int]] = set()
        for pair in pairs:
            if not isinstance(pair, LCSRSPairTargets):
                raise LCSRSC3DatasetError("pair record has the wrong type")
            if pair.pair_id in pair_ids:
                raise LCSRSC3DatasetError("pair identifiers must be unique at an anchor")
            pair_ids.add(pair.pair_id)
            for offset, (user_raw, action_raw) in enumerate(
                zip(pair.user_ids.tolist(), pair.action_ids.tolist(), strict=True)
            ):
                user = int(user_raw)
                action = int(action_raw)
                cell = (user, action)
                if user < 0 or user >= users or action < 0 or action >= LCSRS_ACTION_DIM:
                    raise LCSRSC3DatasetError("pair user/action is out of range")
                if user in pair_users or cell in supported_cells:
                    raise LCSRSC3DatasetError("anchor pairs must be user/cell-disjoint")
                if row_class[cell] != LCSRS_ROW_SUPPORTED:
                    raise LCSRSC3DatasetError("pair cell must be the unique SUPPORTED row")
                if targets[cell] != np.float32(pair.mean_targets[offset]):
                    raise LCSRSC3DatasetError("supported target disagrees with 32-draw mean")
                if not np.array_equal(
                    self.view.tokens[user, action, users, 2:5],
                    np.asarray([1.0, 1.0, 1.0], dtype=np.float32),
                ):
                    raise LCSRSC3DatasetError("pair cell is not designated and supported")
                pair_users.add(user)
                supported_cells.add(cell)
        declared_supported = {
            (int(user), int(action))
            for user, action in np.argwhere(row_class == LCSRS_ROW_SUPPORTED)
        }
        if declared_supported != supported_cells:
            raise LCSRSC3DatasetError("SUPPORTED rows and pair records disagree")
        expected = _surface_digest(self.view.content_digest, targets, row_class, pairs)
        if self.content_digest not in {"", expected}:
            raise LCSRSC3DatasetError("anchor surface digest mismatch")
        object.__setattr__(self, "normalized_targets", targets)
        object.__setattr__(self, "row_class", row_class)
        object.__setattr__(self, "pairs", pairs)
        object.__setattr__(self, "content_digest", expected)

    def cells_for_class(self, row_class: np.uint8) -> np.ndarray:
        cells = np.argwhere(self.row_class == row_class).astype(np.int64, copy=False)
        cells.setflags(write=False)
        return cells


@dataclass(frozen=True)
class LCSRSAnchorRecord:
    """One fitting anchor plus authenticated raw detached-Q12 provenance."""

    world_id: int
    phase: int
    anchor_id: str
    surface: LCSRSAnchorSurface
    q12_values: np.ndarray
    content_digest: str = ""

    def __post_init__(self) -> None:
        if (
            isinstance(self.world_id, bool)
            or not isinstance(self.world_id, int)
            or self.world_id < 0
        ):
            raise LCSRSC3DatasetError("world_id must be a nonnegative integer")
        if (
            isinstance(self.phase, bool)
            or not isinstance(self.phase, int)
            or not 1 <= self.phase <= 9
        ):
            raise LCSRSC3DatasetError("phase must be an integer in [1,9]")
        if not isinstance(self.anchor_id, str) or not self.anchor_id:
            raise LCSRSC3DatasetError("anchor_id must be a nonempty receipt identifier")
        if not isinstance(self.surface, LCSRSAnchorSurface):
            raise LCSRSC3DatasetError("surface must be an LC-SRS anchor surface")
        self.surface.view.verify()
        q12 = _readonly(self.q12_values, dtype=np.dtype(np.float64))
        view = self.surface.view
        if q12.shape != view.action_mask.shape or not np.all(np.isfinite(q12)):
            raise LCSRSC3DatasetError("q12_values must be a finite native action surface")
        expected_reference = np.argmax(
            np.where(view.action_mask, q12, -np.inf), axis=1
        ).astype(np.int64)
        if not np.array_equal(expected_reference, view.reference_actions):
            raise LCSRSC3DatasetError("q12_values disagree with detached reference actions")
        rows = np.arange(q12.shape[0])
        margins = q12 - q12[rows, view.reference_actions, None]
        encoded_margins = np.asarray(np.tanh(margins), dtype=np.float32)
        observed_margins = view.action_context[:, :, 23]
        if not np.allclose(
            encoded_margins[view.action_mask],
            observed_margins[view.action_mask],
            rtol=0.0,
            atol=2.0 * np.finfo(np.float32).eps,
        ):
            raise LCSRSC3DatasetError("q12_values disagree with encoded Q12 margins")
        expected_digest = _anchor_record_digest(
            world_id=self.world_id,
            phase=self.phase,
            anchor_id=self.anchor_id,
            surface_digest=self.surface.content_digest,
            q12_values=q12,
        )
        if self.content_digest not in {"", expected_digest}:
            raise LCSRSC3DatasetError("anchor record digest mismatch")
        object.__setattr__(self, "q12_values", q12)
        object.__setattr__(self, "content_digest", expected_digest)

    def base_gap(self, user: int, action: int) -> float:
        reference = int(self.surface.view.reference_actions[user])
        return float(self.q12_values[user, reference] - self.q12_values[user, action])


def assemble_lcsrs_anchor_surface(
    view: C3View,
    pairs: tuple[LCSRSPairTargets, ...] | list[LCSRSPairTargets],
) -> LCSRSAnchorSurface:
    """Merge disjoint two-user labels once; never overwrite a supported cell."""

    view.verify()
    pair_tuple = tuple(pairs)
    if not pair_tuple:
        raise LCSRSC3DatasetError("fitting anchor needs at least one LC-SRS pair")
    users = int(view.action_context.shape[0])
    row_class = np.full((users, LCSRS_ACTION_DIM), LCSRS_ROW_MASKED, dtype=np.uint8)
    row_class[view.action_mask] = LCSRS_ROW_CONTROL
    row_class[np.arange(users), view.reference_actions] = LCSRS_ROW_REFERENCE
    targets = np.zeros((users, LCSRS_ACTION_DIM), dtype=np.float32)
    used_users: set[int] = set()
    used_cells: set[tuple[int, int]] = set()
    pair_ids: set[str] = set()
    pair_slot = users
    for pair in pair_tuple:
        if not isinstance(pair, LCSRSPairTargets):
            raise LCSRSC3DatasetError("pair record has the wrong type")
        if pair.pair_id in pair_ids:
            raise LCSRSC3DatasetError("pair identifiers must be unique at an anchor")
        pair_ids.add(pair.pair_id)
        means = pair.mean_targets
        for offset, (user_raw, action_raw) in enumerate(
            zip(pair.user_ids.tolist(), pair.action_ids.tolist(), strict=True)
        ):
            user = int(user_raw)
            action = int(action_raw)
            if user < 0 or user >= users or action < 0 or action >= LCSRS_ACTION_DIM:
                raise LCSRSC3DatasetError("pair user/action is out of range")
            if user in used_users:
                raise LCSRSC3DatasetError("closure-eligible pairs must be user-disjoint")
            cell = (user, action)
            if cell in used_cells or row_class[cell] != LCSRS_ROW_CONTROL:
                raise LCSRSC3DatasetError("supported cell would overwrite another class")
            pair_status = view.tokens[user, action, pair_slot, 2:5]
            if not np.array_equal(pair_status, np.asarray([1.0, 1.0, 1.0])):
                raise LCSRSC3DatasetError("pair cell is not designated and supported")
            targets[cell] = np.float32(means[offset])
            row_class[cell] = LCSRS_ROW_SUPPORTED
            used_users.add(user)
            used_cells.add(cell)
    return LCSRSAnchorSurface(
        view=view,
        normalized_targets=targets,
        row_class=row_class,
        pairs=pair_tuple,
    )


__all__ = [
    "LCSRS_DRAW_COUNT",
    "LCSRS_ROW_MASKED",
    "LCSRS_ROW_REFERENCE",
    "LCSRS_ROW_CONTROL",
    "LCSRS_ROW_SUPPORTED",
    "LCSRSC3DatasetError",
    "LCSRSPairTargets",
    "LCSRSAnchorSurface",
    "LCSRSAnchorRecord",
    "assemble_lcsrs_anchor_surface",
]
