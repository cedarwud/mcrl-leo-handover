#!/usr/bin/env python3
"""V0.14 five-arm evaluation plumbing.

This module is an integration seam, not an experiment launcher.  It keeps the
V0.14 deployment decoder and the physical EE accounting in one small,
simulator-independent unit so that a later runner can supply a frozen episode
callback without reimplementing the ablation rules.

The route arms are literal head omissions from the direct unweighted sum:

``FULL``      = Q1 + Q2 + Q3
``DROP_C1``   =       Q2 + Q3
``DROP_C2``   = Q1      + Q3
``DROP_C3``   = Q1 + Q2

``MAIN`` is deliberately separate.  It is the frozen legacy Main baseline,
not an empty route set and not a fourth Catfish.  The caller must provide its
surface explicitly.  Every route uses the same safe mask and one native
masked argmax.  Episode EE is always computed as pooled delivered bits divided
by pooled positive energy; an average of episode ratios is never the endpoint.

No simulator, source harvest, learner update, TEST split, or policy training is
performed here.  ``run_five_arm_evaluation`` accepts an episode callback and
therefore remains useful to a later physical runner while being safe to test
with synthetic receipts.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any, Protocol, TypeAlias

import numpy as np

from mcrl.errors import MCRLContractError


ACTION_DIM = 28
HEAD_NAMES = ("Q1", "Q2", "Q3")
ROUTE_ARMS = ("FULL", "DROP_C1", "DROP_C2", "DROP_C3")
ARMS = (*ROUTE_ARMS, "MAIN")
MAIN_ARM = "MAIN"
BASELINE_ARM = MAIN_ARM
ACTIVE_HEADS: dict[str, tuple[str, ...]] = {
    "FULL": HEAD_NAMES,
    "DROP_C1": ("Q2", "Q3"),
    "DROP_C2": ("Q1", "Q3"),
    "DROP_C3": ("Q1", "Q2"),
}

EVALUATION_EPISODES = 100
CHECKPOINT_EVERY_EPISODES = 100
EVALUATION_SCHEMA = "multi-catfish-mcrl-v014-five-arm-evaluation-v1"
CHECKPOINT_SCHEMA = "multi-catfish-mcrl-v014-five-arm-checkpoint-v1"
CLAIM_CEILING = "TRAIN_DEVELOPMENT_EE_RECEIPTS_ONLY_NO_TEST_EFFICACY_CLAIM"


class V014FiveArmEvaluationError(MCRLContractError):
    """A V0.14 five-arm policy or EE receipt violates its contract."""


def _canonical_arm(arm: object) -> str:
    if arm not in ARMS:
        raise V014FiveArmEvaluationError(
            f"arm must be one of {', '.join(ARMS)}"
        )
    return str(arm)


def _finite_surface(
    value: object,
    *,
    field: str,
    rows: int | None = None,
    action_dim: int = ACTION_DIM,
) -> np.ndarray:
    try:
        array = np.asarray(value)
    except (TypeError, ValueError) as error:
        raise V014FiveArmEvaluationError(f"{field} is not an array") from error
    if array.ndim != 2 or array.shape[1] != action_dim:
        raise V014FiveArmEvaluationError(
            f"{field} must have shape (users,{action_dim})"
        )
    if rows is not None and array.shape[0] != rows:
        raise V014FiveArmEvaluationError(f"{field} row count disagrees")
    try:
        result = np.asarray(array, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise V014FiveArmEvaluationError(f"{field} is not numeric") from error
    if not np.all(np.isfinite(result)):
        raise V014FiveArmEvaluationError(f"{field} contains non-finite values")
    return result


def _common_mask(
    value: object,
    *,
    rows: int | None = None,
    action_dim: int = ACTION_DIM,
) -> np.ndarray:
    try:
        array = np.asarray(value)
    except (TypeError, ValueError) as error:
        raise V014FiveArmEvaluationError("safe mask is not an array") from error
    if array.dtype != np.bool_ or array.ndim != 2 or array.shape[1] != action_dim:
        raise V014FiveArmEvaluationError(
            f"common safe mask must be Boolean shape (users,{action_dim})"
        )
    if rows is not None and array.shape[0] != rows:
        raise V014FiveArmEvaluationError("common safe mask row count disagrees")
    if array.shape[0] < 1 or not np.all(np.any(array, axis=1)):
        raise V014FiveArmEvaluationError(
            "common safe mask must admit one legal action per user"
        )
    return np.array(array, dtype=np.bool_, copy=True, order="C")


def _validated_surfaces(
    q1_values: object,
    q2_values: object,
    q3_values: object,
    masks: object,
) -> tuple[dict[str, np.ndarray], np.ndarray]:
    q1 = _finite_surface(q1_values, field="Q1")
    rows = int(q1.shape[0])
    action_dim = int(q1.shape[1])
    if action_dim != ACTION_DIM:
        raise V014FiveArmEvaluationError(
            f"V0.14 deployment requires {ACTION_DIM} actions"
        )
    surfaces = {
        "Q1": q1,
        "Q2": _finite_surface(q2_values, field="Q2", rows=rows),
        "Q3": _finite_surface(q3_values, field="Q3", rows=rows),
    }
    if any(surface.shape != q1.shape for surface in surfaces.values()):
        raise V014FiveArmEvaluationError(
            "Q1, Q2, and Q3 surfaces must share one action-aligned shape"
        )
    mask = _common_mask(masks, rows=rows, action_dim=action_dim)
    return surfaces, mask


def _masked_argmax(scores: np.ndarray, masks: np.ndarray) -> np.ndarray:
    """Select once over the common safe set; NumPy ties go to low action ID."""

    legal = _common_mask(masks, rows=int(scores.shape[0]), action_dim=int(scores.shape[1]))
    if scores.ndim != 2 or scores.shape != legal.shape:
        raise V014FiveArmEvaluationError("scores and common mask are misaligned")
    if not np.all(np.isfinite(scores)):
        raise V014FiveArmEvaluationError("summed scores contain non-finite values")
    return np.argmax(np.where(legal, scores, -np.inf), axis=1).astype(
        np.int64, copy=False
    )


def ratio_of_sums(total_bits: float, total_energy_j: float) -> float:
    """Compute canonical EE from additive totals, never from row ratios."""

    bits = float(total_bits)
    energy = float(total_energy_j)
    if not math.isfinite(bits) or bits < 0.0:
        raise V014FiveArmEvaluationError(
            "total_bits must be finite and nonnegative"
        )
    if not math.isfinite(energy) or energy <= 0.0:
        raise V014FiveArmEvaluationError(
            "total_energy_j must be finite and positive"
        )
    return bits / energy


def summed_route_scores(
    q1_values: object,
    q2_values: object,
    q3_values: object,
    masks: object,
    arm: str,
) -> np.ndarray:
    """Return the direct, unweighted score surface for one route arm."""

    label = _canonical_arm(arm)
    if label == MAIN_ARM:
        raise V014FiveArmEvaluationError(
            "MAIN is an independent frozen baseline; pass its surface to main_actions"
        )
    surfaces, _mask = _validated_surfaces(q1_values, q2_values, q3_values, masks)
    active = ACTIVE_HEADS[label]
    scores = np.zeros_like(surfaces[active[0]], dtype=np.float64)
    for head in active:
        # This is intentionally an unweighted literal sum.  A dropped head is
        # omitted; no route-count normalization or replacement value is used.
        scores = scores + surfaces[head]
    if not np.all(np.isfinite(scores)):
        raise V014FiveArmEvaluationError("summed route scores contain non-finite values")
    return scores


def route_actions(
    q1_values: object,
    q2_values: object,
    q3_values: object,
    masks: object,
    arm: str,
) -> np.ndarray:
    """Decode a route arm with one common-mask argmax."""

    label = _canonical_arm(arm)
    if label == MAIN_ARM:
        raise V014FiveArmEvaluationError("route_actions does not decode MAIN")
    scores = summed_route_scores(q1_values, q2_values, q3_values, masks, label)
    return _masked_argmax(scores, _common_mask(masks, rows=scores.shape[0]))


def main_actions(main_values: object, masks: object) -> np.ndarray:
    """Decode the independent frozen legacy Main baseline."""

    main = _finite_surface(main_values, field="MAIN")
    legal = _common_mask(masks, rows=int(main.shape[0]), action_dim=int(main.shape[1]))
    return _masked_argmax(main, legal)


def select_arm_actions(
    q1_values: object,
    q2_values: object,
    q3_values: object,
    masks: object,
    arm: str,
    *,
    main_values: object | None = None,
) -> np.ndarray:
    """Decode any of the five arms without adding a second action stage.

    The three route values represent the frozen Q1 surface and the learned
    Q2/Q3 surfaces at the same decision state.  ``MAIN`` intentionally does
    not query or combine these surfaces: it requires the caller's separate
    frozen legacy Main surface.
    """

    label = _canonical_arm(arm)
    if label == MAIN_ARM:
        if main_values is None:
            raise V014FiveArmEvaluationError(
                "MAIN requires an explicit frozen baseline surface"
            )
        return main_actions(main_values, masks)
    return route_actions(q1_values, q2_values, q3_values, masks, label)


@dataclass(frozen=True)
class V014EpisodeReceipt:
    """Additive physical totals for one frozen TRAIN episode."""

    arm: str
    episode_index: int
    evaluation_seed: int
    total_bits: float
    total_energy_j: float
    decision_count: int
    served_user_steps: int
    initialization_seed: int | None = None
    world_seed: int | None = None
    action_trace_sha256: str | None = None
    evaluation_split: str = "TRAIN"
    test_split_opened: bool = False
    episode_training: bool = False

    def __post_init__(self) -> None:
        label = _canonical_arm(self.arm)
        if label != self.arm:
            raise V014FiveArmEvaluationError("episode arm is not canonical")
        for field in ("episode_index", "evaluation_seed", "decision_count"):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
                raise V014FiveArmEvaluationError(f"{field} must be an integer")
            if int(value) <= 0:
                raise V014FiveArmEvaluationError(f"{field} must be positive")
        for field in ("initialization_seed", "world_seed"):
            value = getattr(self, field)
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, (int, np.integer))
                or int(value) <= 0
            ):
                raise V014FiveArmEvaluationError(f"{field} must be positive or None")
        for field in ("total_bits", "total_energy_j"):
            value = float(getattr(self, field))
            if not math.isfinite(value) or value < 0.0:
                raise V014FiveArmEvaluationError(
                    f"{field} must be finite and nonnegative"
                )
        if float(self.total_energy_j) <= 0.0:
            raise V014FiveArmEvaluationError("total_energy_j must be positive")
        served = self.served_user_steps
        if isinstance(served, bool) or not isinstance(served, (int, np.integer)):
            raise V014FiveArmEvaluationError("served_user_steps must be an integer")
        if not 0 <= int(served) <= int(self.decision_count):
            raise V014FiveArmEvaluationError("served_user_steps is out of bounds")
        if self.evaluation_split != "TRAIN":
            raise V014FiveArmEvaluationError("V0.14 evaluation is TRAIN-only")
        if self.test_split_opened is not False or self.episode_training is not False:
            raise V014FiveArmEvaluationError(
                "five-arm evaluation must not open TEST or train an episode"
            )
        if self.action_trace_sha256 is not None:
            _validate_digest(self.action_trace_sha256, field="action_trace_sha256")

    @property
    def ratio_of_sums_ee_bits_per_j(self) -> float:
        return float(self.total_bits) / float(self.total_energy_j)

    @property
    def served_fraction(self) -> float:
        return int(self.served_user_steps) / int(self.decision_count)

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["ratio_of_sums_ee_bits_per_j"] = self.ratio_of_sums_ee_bits_per_j
        payload["served_fraction"] = self.served_fraction
        payload["outage_fraction"] = 1.0 - self.served_fraction
        return payload

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> "V014EpisodeReceipt":
        if not isinstance(row, Mapping):
            raise V014FiveArmEvaluationError("episode receipt must be an object")
        required = (
            "arm",
            "episode_index",
            "evaluation_seed",
            "total_bits",
            "total_energy_j",
            "decision_count",
            "served_user_steps",
        )
        missing = [field for field in required if field not in row]
        if missing:
            raise V014FiveArmEvaluationError(
                f"episode receipt is missing {', '.join(missing)}"
            )
        values = {
            field: row[field]
            for field in (
                "arm",
                "episode_index",
                "evaluation_seed",
                "total_bits",
                "total_energy_j",
                "decision_count",
                "served_user_steps",
                "initialization_seed",
                "world_seed",
                "action_trace_sha256",
                "evaluation_split",
                "test_split_opened",
                "episode_training",
            )
            if field in row
        }
        result = cls(**values)
        if "ratio_of_sums_ee_bits_per_j" in row:
            supplied = float(row["ratio_of_sums_ee_bits_per_j"])
            if not math.isfinite(supplied) or not math.isclose(
                supplied,
                result.ratio_of_sums_ee_bits_per_j,
                rel_tol=1e-12,
                abs_tol=1e-12,
            ):
                raise V014FiveArmEvaluationError(
                    "episode ratio_of_sums_ee_bits_per_j is inconsistent"
                )
        for field, expected in (
            ("served_fraction", result.served_fraction),
            ("outage_fraction", 1.0 - result.served_fraction),
        ):
            if field in row:
                supplied = float(row[field])
                if not math.isfinite(supplied) or not math.isclose(
                    supplied, expected, rel_tol=1e-12, abs_tol=1e-12
                ):
                    raise V014FiveArmEvaluationError(
                        f"episode {field} is inconsistent"
                    )
        return result


def _validate_digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V014FiveArmEvaluationError(f"{field} must be a lowercase SHA-256")
    return value


def _normalise_receipts(
    rows: Sequence[V014EpisodeReceipt | Mapping[str, Any]],
) -> tuple[V014EpisodeReceipt, ...]:
    materialized: list[V014EpisodeReceipt] = []
    for row in rows:
        if isinstance(row, V014EpisodeReceipt):
            materialized.append(row)
        else:
            materialized.append(V014EpisodeReceipt.from_mapping(row))
    if not materialized:
        raise V014FiveArmEvaluationError("cannot aggregate an empty arm")
    return tuple(materialized)


def aggregate_arm(
    rows: Sequence[V014EpisodeReceipt | Mapping[str, Any]],
    *,
    arm: str | None = None,
) -> dict[str, object]:
    """Pool one arm's additive totals before computing EE."""

    materialized = _normalise_receipts(rows)
    labels = {row.arm for row in materialized}
    if len(labels) != 1:
        raise V014FiveArmEvaluationError("an arm aggregate contains mixed arms")
    label = next(iter(labels))
    if arm is not None and _canonical_arm(arm) != label:
        raise V014FiveArmEvaluationError("arm aggregate label disagrees with rows")
    keys = [
        (row.episode_index, row.evaluation_seed, row.initialization_seed)
        for row in materialized
    ]
    if len(set(keys)) != len(keys):
        raise V014FiveArmEvaluationError(f"{label} contains duplicate episode keys")
    bits = float(math.fsum(float(row.total_bits) for row in materialized))
    energy = float(math.fsum(float(row.total_energy_j) for row in materialized))
    decisions = int(sum(int(row.decision_count) for row in materialized))
    served = int(sum(int(row.served_user_steps) for row in materialized))
    if decisions <= 0 or served < 0 or served > decisions:
        raise V014FiveArmEvaluationError("arm aggregate service totals are invalid")
    pooled_ee = ratio_of_sums(bits, energy)
    return {
        "arm": label,
        "rows": len(materialized),
        "decision_count": decisions,
        "served_user_steps": served,
        "served_fraction": served / decisions,
        "outage_fraction": 1.0 - served / decisions,
        "total_bits": bits,
        "total_energy_j": energy,
        "pooled_ratio_of_sums_ee_bits_per_j": pooled_ee,
        # This is descriptive only; it is never used as the EE endpoint.
        "mean_episode_ee_bits_per_j": float(
            math.fsum(row.ratio_of_sums_ee_bits_per_j for row in materialized)
            / len(materialized)
        ),
    }


def _relative_contrast(
    full: Mapping[str, object], comparator: Mapping[str, object]
) -> dict[str, object]:
    full_ee = float(full["pooled_ratio_of_sums_ee_bits_per_j"])
    comparator_ee = float(comparator["pooled_ratio_of_sums_ee_bits_per_j"])
    if not math.isfinite(full_ee) or not math.isfinite(comparator_ee) or comparator_ee <= 0.0:
        raise V014FiveArmEvaluationError("contrast denominator EE is invalid")
    return {
        "full_ee_bits_per_j": full_ee,
        "comparator_ee_bits_per_j": comparator_ee,
        "relative_delta": full_ee / comparator_ee - 1.0,
        "relative_delta_percent": 100.0 * (full_ee / comparator_ee - 1.0),
        "full_served_user_steps": int(full["served_user_steps"]),
        "comparator_served_user_steps": int(comparator["served_user_steps"]),
        "service_noninferior": int(full["served_user_steps"])
        >= int(comparator["served_user_steps"]),
    }


def aggregate_five_arm(
    rows_by_arm: Mapping[str, Sequence[V014EpisodeReceipt | Mapping[str, Any]]],
) -> dict[str, object]:
    """Validate and aggregate exactly the five V0.14 ablation arms."""

    if not isinstance(rows_by_arm, Mapping) or set(rows_by_arm) != set(ARMS):
        raise V014FiveArmEvaluationError(
            "five-arm evaluation requires exactly FULL, DROP_C1, DROP_C2, DROP_C3, MAIN"
        )
    materialized_by_arm = {
        arm: _normalise_receipts(rows_by_arm[arm]) for arm in ARMS
    }
    summaries = {
        arm: aggregate_arm(materialized_by_arm[arm], arm=arm)
        for arm in ARMS
    }
    # Episode index is the paired evaluation unit.  Initialization lineages
    # may create multiple route rows per index, while MAIN remains independent.
    episode_sets = {
        arm: {int(row.episode_index) for row in materialized_by_arm[arm]}
        for arm in ARMS
    }
    if len({frozenset(values) for values in episode_sets.values()}) != 1:
        raise V014FiveArmEvaluationError(
            "five arms do not cover the same evaluation episode indices"
        )
    pairing_sets = {
        arm: {
            (int(row.episode_index), int(row.evaluation_seed))
            for row in materialized_by_arm[arm]
        }
        for arm in ARMS
    }
    if len({frozenset(values) for values in pairing_sets.values()}) != 1:
        raise V014FiveArmEvaluationError(
            "five arms do not share one paired evaluation-seed grid"
        )
    contrasts = {
        f"FULL_minus_{arm}": _relative_contrast(summaries["FULL"], summaries[arm])
        for arm in ROUTE_ARMS[1:]
    }
    contrasts["FULL_minus_MAIN"] = _relative_contrast(
        summaries["FULL"], summaries[MAIN_ARM]
    )
    return {
        "schema": EVALUATION_SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "arms": list(ARMS),
        "route_arms": list(ROUTE_ARMS),
        "summaries": summaries,
        "contrasts": contrasts,
        "episode_indices": sorted(next(iter(episode_sets.values()))),
    }


@dataclass(frozen=True)
class V014FiveArmEvaluationSpec:
    """Fixed loop and checkpoint cadence for one evaluation block."""

    episodes: int = EVALUATION_EPISODES
    checkpoint_every_episodes: int = CHECKPOINT_EVERY_EPISODES
    arms: tuple[str, ...] = ARMS
    evaluation_split: str = "TRAIN"
    claim_ceiling: str = CLAIM_CEILING

    def verify(self) -> None:
        if isinstance(self.episodes, bool) or not isinstance(self.episodes, int):
            raise V014FiveArmEvaluationError("episodes must be an integer")
        if self.episodes < 1:
            raise V014FiveArmEvaluationError("episodes must be positive")
        if (
            isinstance(self.checkpoint_every_episodes, bool)
            or not isinstance(self.checkpoint_every_episodes, int)
            or self.checkpoint_every_episodes <= 0
        ):
            raise V014FiveArmEvaluationError(
                "checkpoint_every_episodes must be positive"
            )
        if self.episodes % self.checkpoint_every_episodes != 0:
            raise V014FiveArmEvaluationError(
                "episodes must end on a 100-EP checkpoint"
            )
        if tuple(self.arms) != ARMS:
            raise V014FiveArmEvaluationError("arm order must be the frozen five-arm order")
        if self.evaluation_split != "TRAIN":
            raise V014FiveArmEvaluationError("V0.14 evaluation is TRAIN-only")
        if self.claim_ceiling != CLAIM_CEILING:
            raise V014FiveArmEvaluationError("claim ceiling cannot be widened")

    def checkpoint_schedule(self) -> tuple[int, ...]:
        self.verify()
        return tuple(
            range(
                self.checkpoint_every_episodes,
                self.episodes + 1,
                self.checkpoint_every_episodes,
            )
        )


@dataclass(frozen=True)
class V014CheckpointEvent:
    """Read-only event passed to a checkpoint callback."""

    arm: str
    episode_index: int
    configured_episodes: int
    receipts: tuple[V014EpisodeReceipt, ...]

    def summary(self) -> dict[str, object]:
        return aggregate_arm(self.receipts, arm=self.arm)


class EpisodeRunner(Protocol):
    def __call__(self, *, arm: str, episode_index: int) -> Mapping[str, Any] | V014EpisodeReceipt:
        """Return one frozen episode receipt for the requested arm/index."""


CheckpointCallback: TypeAlias = Callable[
    [V014CheckpointEvent], Mapping[str, Any] | None
]
EpisodeCallback: TypeAlias = Callable[[V014EpisodeReceipt], None]


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> str:
    encoded = (
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        + "\n"
    ).encode("ascii")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
    return hashlib.sha256(encoded).hexdigest()


def _write_once_json(path: Path, payload: Mapping[str, Any]) -> str:
    if path.exists() or path.is_symlink():
        raise V014FiveArmEvaluationError(f"refusing to overwrite {path}")
    encoded = (
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        + "\n"
    ).encode("ascii")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary_name, path)
        except FileExistsError as error:
            raise V014FiveArmEvaluationError(f"refusing to overwrite {path}") from error
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
    return hashlib.sha256(encoded).hexdigest()


def run_five_arm_evaluation(
    episode_runner: EpisodeRunner,
    *,
    spec: V014FiveArmEvaluationSpec | None = None,
    output_dir: str | Path | None = None,
    checkpoint_callback: CheckpointCallback | None = None,
    episode_callback: EpisodeCallback | None = None,
) -> dict[str, object]:
    """Collect one paired five-arm block through an injected episode callback.

    This function intentionally does not know how an episode is simulated.
    The callback must return a complete physical receipt with the requested
    canonical arm and episode index.  A callback may use its checkpoint hook to
    save a model checkpoint, but this module itself never updates a learner or
    writes model bytes.
    """

    if not callable(episode_runner):
        raise V014FiveArmEvaluationError("episode_runner must be callable")
    run_spec = spec or V014FiveArmEvaluationSpec()
    run_spec.verify()
    destination: Path | None = None
    if output_dir is not None:
        destination = Path(output_dir)
        if destination.exists() or destination.is_symlink():
            raise V014FiveArmEvaluationError(
                f"refusing to overwrite evaluation output: {destination}"
            )
        destination.mkdir(parents=True, exist_ok=False)
        (destination / "checkpoints").mkdir()

    rows_by_arm: dict[str, list[V014EpisodeReceipt]] = {arm: [] for arm in ARMS}
    checkpoint_digests: dict[str, list[str]] = {arm: [] for arm in ARMS}
    if destination is not None:
        _write_json_atomic(
            destination / "status.json",
            {
                "schema": EVALUATION_SCHEMA,
                "status": "running",
                "claim_ceiling": CLAIM_CEILING,
                "spec": asdict(run_spec),
                "completed_arms": 0,
                "completed_episodes": 0,
                "test_split_opened": False,
                "episode_training": False,
            },
        )

    for arm in ARMS:
        for episode_index in range(1, run_spec.episodes + 1):
            raw = episode_runner(arm=arm, episode_index=episode_index)
            receipt = (
                raw
                if isinstance(raw, V014EpisodeReceipt)
                else V014EpisodeReceipt.from_mapping(raw)
            )
            if receipt.arm != arm or receipt.episode_index != episode_index:
                raise V014FiveArmEvaluationError(
                    "episode callback returned a receipt for the wrong arm/index"
                )
            rows_by_arm[arm].append(receipt)
            if episode_callback is not None:
                episode_callback(receipt)
            if episode_index in run_spec.checkpoint_schedule():
                event = V014CheckpointEvent(
                    arm=arm,
                    episode_index=episode_index,
                    configured_episodes=run_spec.episodes,
                    receipts=tuple(rows_by_arm[arm]),
                )
                supplied = checkpoint_callback(event) if checkpoint_callback else None
                checkpoint_payload: dict[str, Any] = {
                    "schema": CHECKPOINT_SCHEMA,
                    "claim_ceiling": CLAIM_CEILING,
                    "arm": arm,
                    "episode_index": episode_index,
                    "configured_episodes": run_spec.episodes,
                    "evaluation_split": "TRAIN",
                    "test_split_opened": False,
                    "episode_training": False,
                    "summary": event.summary(),
                }
                if supplied is not None:
                    if not isinstance(supplied, Mapping):
                        raise V014FiveArmEvaluationError(
                            "checkpoint callback must return a mapping or None"
                        )
                    checkpoint_payload["callback_payload"] = dict(supplied)
                if destination is not None:
                    checkpoint_path = (
                        destination
                        / "checkpoints"
                        / f"{arm.lower()}-episode-{episode_index:06d}.json"
                    )
                    checkpoint_digests[arm].append(
                        _write_once_json(checkpoint_path, checkpoint_payload)
                    )
        if destination is not None:
            _write_json_atomic(
                destination / "status.json",
                {
                    "schema": EVALUATION_SCHEMA,
                    "status": "running",
                    "claim_ceiling": CLAIM_CEILING,
                    "spec": asdict(run_spec),
                    "completed_arms": ARMS.index(arm) + 1,
                    "completed_episodes": (ARMS.index(arm) + 1) * run_spec.episodes,
                    "active_arm": arm,
                    "test_split_opened": False,
                    "episode_training": False,
                },
            )

    result = aggregate_five_arm(rows_by_arm)
    result.update(
        {
            "spec": asdict(run_spec),
            "checkpoint_file_sha256s": checkpoint_digests,
            "test_split_opened": False,
            "episode_training": False,
        }
    )
    if destination is not None:
        receipt_file_digest = _write_once_json(
            destination / "episode-receipts.json",
            {
                "schema": EVALUATION_SCHEMA,
                "claim_ceiling": CLAIM_CEILING,
                "rows_by_arm": {
                    arm: [row.as_dict() for row in rows_by_arm[arm]]
                    for arm in ARMS
                },
            },
        )
        result["episode_receipts_file_sha256"] = receipt_file_digest
        result_digest = _write_once_json(destination / "result.json", result)
        _write_json_atomic(
            destination / "status.json",
            {
                **result,
                "status": "complete",
                "result_file_sha256": result_digest,
            },
        )
        result["result_file_sha256"] = result_digest
    return result


def _read_rows(path: Path) -> Mapping[str, Sequence[Mapping[str, Any]]]:
    try:
        payload = json.loads(path.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise V014FiveArmEvaluationError(f"cannot read rows JSON: {path}") from error
    rows = payload.get("rows_by_arm") if isinstance(payload, Mapping) else payload
    if not isinstance(rows, Mapping):
        raise V014FiveArmEvaluationError("rows JSON must contain rows_by_arm")
    return rows


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rows-json",
        type=Path,
        required=True,
        help="precomputed TRAIN episode receipts; no simulator is launched",
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = aggregate_five_arm(_read_rows(args.rows_json))
    destination = Path(args.output)
    if destination.exists() or destination.is_symlink():
        raise V014FiveArmEvaluationError(f"refusing to overwrite output: {destination}")
    destination.mkdir(parents=True, exist_ok=False)
    digest = _write_once_json(destination / "result.json", result)
    print(json.dumps({**result, "result_file_sha256": digest}, indent=2, sort_keys=True))
    return 0


__all__ = [
    "ACTION_DIM",
    "ACTIVE_HEADS",
    "ARMS",
    "BASELINE_ARM",
    "CHECKPOINT_EVERY_EPISODES",
    "CHECKPOINT_SCHEMA",
    "CLAIM_CEILING",
    "EVALUATION_EPISODES",
    "EVALUATION_SCHEMA",
    "MAIN_ARM",
    "ROUTE_ARMS",
    "V014CheckpointEvent",
    "V014EpisodeReceipt",
    "V014FiveArmEvaluationError",
    "V014FiveArmEvaluationSpec",
    "aggregate_arm",
    "aggregate_five_arm",
    "main_actions",
    "ratio_of_sums",
    "route_actions",
    "run_five_arm_evaluation",
    "select_arm_actions",
    "summed_route_scores",
]


if __name__ == "__main__":
    raise SystemExit(main())
