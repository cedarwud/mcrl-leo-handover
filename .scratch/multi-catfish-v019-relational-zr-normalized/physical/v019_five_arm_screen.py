#!/usr/bin/env python3
"""V0.19 post-gate five-arm screen seam.

This file is deliberately isolated from the frozen V0.19 learner gate.  It
contains the route decoder, receipt/aggregation contract, and an injected
episode loop for the later short TRAIN screen.  Importing it never opens a
simulator, reads an outcome, loads a checkpoint, or updates a learner.

The route arms are literal score-head ablations:

``FULL``      = Q1 + Q2 + Q3
``DROP_C1``   =       Q2 + Q3
``DROP_C2``   = Q1      + Q3
``DROP_C3``   = Q1 + Q2

``MAIN`` is an independent frozen legacy baseline.  It is not a fifth Q head
and is supplied by a separate callback.  All route arms use one common native
safe mask and one masked argmax.  Q3 is trained with the detached
``r12 = argmax(Q1 + Q2)`` reference.  Consequently the active Q3 arms all
reuse that same reference and the same structured state digest; dropping Q1
or Q2 changes only the final score sum.  ``DROP_C3`` does not evaluate Q3.

The physical callback is intentionally injected.  This keeps the present
module pure/mock-testable while leaving the exact post-PASS simulator and
checkpoint paths to a later, separately sealed binding step.
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


ACTION_DIM = 28
HEAD_NAMES = ("Q1", "Q2", "Q3")
ROUTE_ARMS = ("FULL", "DROP_C1", "DROP_C2", "DROP_C3")
ARMS = (*ROUTE_ARMS, "MAIN")
MAIN_ARM = "MAIN"
ACTIVE_HEADS: dict[str, tuple[str, ...]] = {
    "FULL": HEAD_NAMES,
    "DROP_C1": ("Q2", "Q3"),
    "DROP_C2": ("Q1", "Q3"),
    "DROP_C3": ("Q1", "Q2"),
}
Q3_ACTIVE_ARMS = ("FULL", "DROP_C1", "DROP_C2")
Q3_REFERENCE_MODE = "Q1_PLUS_Q2_FIXED_REFERENCE"
# V0.19 changes only the scorer's output parameterisation.  The structured
# relational input/state schema is therefore still the V0.18 schema.  Giving
# it a new name here would falsely claim that the physical feature contract
# changed and would make a route screen incomparable with the learner gate.
Q3_STATE_SCHEMA = "multi-catfish-mcrl-v018-relational-zr-c3-v1"
Q3_OUTPUT_UNIT_MODE = "normalized_bits_per_kappa"
EVALUATION_SPLIT = "TRAIN"
CHECKPOINT_EVERY_EPISODES = 100
DEFAULT_USERS = 100
DEFAULT_STEPS = 10
CLAIM_CEILING = "TRAIN_DEVELOPMENT_EE_RECEIPTS_ONLY_NO_TEST_EFFICACY_CLAIM"
SCREEN_SCHEMA = "multi-catfish-mcrl-v019-relational-zr-five-arm-screen-v1"
CHECKPOINT_SCHEMA = "multi-catfish-mcrl-v019-relational-zr-five-arm-checkpoint-v1"


class V019FiveArmScreenError(ValueError):
    """A V0.19 screen input, route, receipt, or pairing violated the seam."""


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
        raise V019FiveArmScreenError("payload is not finite canonical JSON") from error


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def file_sha256(path: str | Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V019FiveArmScreenError(f"expected a regular file: {source}")
    digest = hashlib.sha256()
    try:
        with source.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as error:
        raise V019FiveArmScreenError(f"cannot read file: {source}") from error
    return digest.hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V019FiveArmScreenError(f"{field} must be a lowercase SHA-256")
    return value


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise V019FiveArmScreenError(f"{field} must be a positive integer")
    result = int(value)
    if result <= 0:
        raise V019FiveArmScreenError(f"{field} must be a positive integer")
    return result


def _nonnegative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise V019FiveArmScreenError(f"{field} must be a nonnegative integer")
    result = int(value)
    if result < 0:
        raise V019FiveArmScreenError(f"{field} must be a nonnegative integer")
    return result


def _array_sha256(value: object) -> str:
    array = np.ascontiguousarray(np.asarray(value))
    digest = hashlib.sha256()
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _surface(value: object, *, field: str, rows: int | None = None) -> np.ndarray:
    try:
        raw = np.asarray(value)
        result = np.asarray(raw, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise V019FiveArmScreenError(f"{field} is not a numeric surface") from error
    if result.ndim != 2 or result.shape[1] != ACTION_DIM:
        raise V019FiveArmScreenError(f"{field} must have shape (users,{ACTION_DIM})")
    if rows is not None and result.shape[0] != rows:
        raise V019FiveArmScreenError(f"{field} row count disagrees")
    if not np.all(np.isfinite(result)):
        raise V019FiveArmScreenError(f"{field} contains non-finite values")
    return np.array(result, dtype=np.float64, copy=True, order="C")


def _mask(value: object, *, rows: int | None = None) -> np.ndarray:
    raw = np.asarray(value)
    if raw.dtype != np.bool_ or raw.ndim != 2 or raw.shape[1] != ACTION_DIM:
        raise V019FiveArmScreenError(
            f"native safe mask must have Boolean shape (users,{ACTION_DIM})"
        )
    if rows is not None and raw.shape[0] != rows:
        raise V019FiveArmScreenError("native safe mask row count disagrees")
    if raw.shape[0] < 1 or not np.all(np.any(raw, axis=1)):
        raise V019FiveArmScreenError("every user must have at least one legal action")
    return np.array(raw, dtype=np.bool_, copy=True, order="C")


def masked_argmax(scores: object, masks: object) -> np.ndarray:
    """Select one action per user from one common native safe mask.

    NumPy's first-maximum rule intentionally gives exact ties to the lowest
    action identifier, matching the existing V0.19 route decoder convention.
    """

    values = _surface(scores, field="scores")
    legal = _mask(masks, rows=int(values.shape[0]))
    return np.argmax(np.where(legal, values, -np.inf), axis=1).astype(
        np.int64, copy=False
    )


def q3_reference_actions(
    q1_values: object, q2_values: object, masks: object
) -> np.ndarray:
    """Return the fixed detached Q1+Q2 reference used by the learned Q3 head."""

    q1 = _surface(q1_values, field="Q1")
    q2 = _surface(q2_values, field="Q2", rows=int(q1.shape[0]))
    legal = _mask(masks, rows=int(q1.shape[0]))
    return masked_argmax(q1 + q2, legal)


@dataclass(frozen=True)
class Q3InputBinding:
    """Receipt for one Q3 structured input built at one physical anchor.

    ``reference_actions_sha256`` authenticates the actual detached reference
    vector supplied to the encoder.  ``state_sha256`` covers the complete
    ten-step/anchor state payload chosen by the physical callback.  The route
    runner requires these digests to be equal across FULL, DROP_C1, and
    DROP_C2 for a paired episode.  Thus dropping Q1 or Q2 cannot silently
    change the learned Q3 input or reference definition.
    """

    reference_actions_sha256: str
    state_sha256: str
    state_schema: str = Q3_STATE_SCHEMA
    reference_mode: str = Q3_REFERENCE_MODE
    output_unit_mode: str = Q3_OUTPUT_UNIT_MODE

    def verify(self) -> None:
        _digest(self.reference_actions_sha256, field="Q3 reference actions sha256")
        _digest(self.state_sha256, field="Q3 state sha256")
        if self.state_schema != Q3_STATE_SCHEMA:
            raise V019FiveArmScreenError("Q3 state schema is not the frozen relational-ZR schema")
        if self.reference_mode != Q3_REFERENCE_MODE:
            raise V019FiveArmScreenError("Q3 reference mode is not fixed Q1+Q2")
        if self.output_unit_mode != Q3_OUTPUT_UNIT_MODE:
            raise V019FiveArmScreenError(
                "Q3 output unit mode is not normalized_bits_per_kappa"
            )

    @classmethod
    def from_reference_and_state(
        cls, reference_actions: object, state_payload: object
    ) -> "Q3InputBinding":
        result = cls(
            reference_actions_sha256=_array_sha256(reference_actions),
            state_sha256=_array_sha256(state_payload),
        )
        result.verify()
        return result

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _validate_q3_reference(
    q1: np.ndarray,
    q2: np.ndarray,
    masks: np.ndarray,
    reference_actions: object,
    binding: Q3InputBinding,
) -> np.ndarray:
    expected = q3_reference_actions(q1, q2, masks)
    raw = np.asarray(reference_actions)
    if raw.shape != expected.shape or raw.dtype.kind not in "iu" or raw.dtype.kind == "b":
        raise V019FiveArmScreenError("Q3 reference actions have the wrong shape/type")
    actual = np.asarray(raw, dtype=np.int64)
    if not np.array_equal(actual, expected):
        raise V019FiveArmScreenError(
            "Q3 reference actions changed from the frozen Q1+Q2 definition"
        )
    binding.verify()
    if _array_sha256(actual) != binding.reference_actions_sha256:
        raise V019FiveArmScreenError(
            "Q3 reference-action digest does not authenticate the supplied vector"
        )
    return np.array(actual, dtype=np.int64, copy=True, order="C")


@dataclass(frozen=True)
class DecodedRoute:
    """Pure result of one route decode at one predecision anchor."""

    arm: str
    scores: np.ndarray
    selected_actions: np.ndarray
    q3_evaluated: bool
    q3_reference_actions: np.ndarray | None
    q3_input: Q3InputBinding | None

    def verify(self, masks: object) -> None:
        legal = _mask(masks, rows=int(self.scores.shape[0]))
        values = _surface(self.scores, field="decoded scores")
        selected = np.asarray(self.selected_actions)
        if self.arm not in ROUTE_ARMS:
            raise V019FiveArmScreenError("decoded route has an unknown arm")
        if selected.shape != (values.shape[0],) or selected.dtype.kind not in "iu":
            raise V019FiveArmScreenError("decoded action vector is malformed")
        if np.any(selected < 0) or np.any(selected >= ACTION_DIM):
            raise V019FiveArmScreenError("decoded action is outside native range")
        if np.any(~legal[np.arange(values.shape[0]), selected.astype(np.int64)]):
            raise V019FiveArmScreenError("decoded action is outside the common safe mask")
        if self.arm == "DROP_C3":
            if self.q3_evaluated or self.q3_reference_actions is not None or self.q3_input is not None:
                raise V019FiveArmScreenError("DROP_C3 must not evaluate or carry Q3 input")
        else:
            if not self.q3_evaluated or self.q3_reference_actions is None or self.q3_input is None:
                raise V019FiveArmScreenError("active Q3 route lacks its fixed input binding")
        if not np.array_equal(
            selected.astype(np.int64), masked_argmax(values, legal)
        ):
            raise V019FiveArmScreenError("route did not use one native masked argmax")


def compose_route_scores(
    q1_values: object,
    q2_values: object,
    q3_values: object | None,
    masks: object,
    arm: str,
    *,
    reference_actions: object | None = None,
    q3_input: Q3InputBinding | None = None,
) -> DecodedRoute:
    """Compose and decode one route arm without touching physical state.

    For active Q3 arms, ``reference_actions`` must be exactly the detached
    ``argmax(Q1+Q2)`` vector used during Q3 training.  It is intentionally
    *not* recomputed under DROP_C1 or DROP_C2.  Those arms are score-head
    ablations; changing the Q3 input would confound a head ablation with a
    state-definition ablation.
    """

    if arm not in ROUTE_ARMS:
        raise V019FiveArmScreenError("compose_route_scores accepts route arms only")
    q1 = _surface(q1_values, field="Q1")
    q2 = _surface(q2_values, field="Q2", rows=int(q1.shape[0]))
    legal = _mask(masks, rows=int(q1.shape[0]))
    base = q1 + q2
    if arm == "DROP_C3":
        if q3_values is not None or reference_actions is not None or q3_input is not None:
            raise V019FiveArmScreenError("DROP_C3 must not evaluate Q3")
        score = base
        route = DecodedRoute(
            arm=arm,
            scores=score,
            selected_actions=masked_argmax(score, legal),
            q3_evaluated=False,
            q3_reference_actions=None,
            q3_input=None,
        )
        route.verify(legal)
        return route
    if q3_values is None or reference_actions is None or q3_input is None:
        raise V019FiveArmScreenError(f"{arm} requires the fixed learned-Q3 input")
    q3 = _surface(q3_values, field="Q3", rows=int(q1.shape[0]))
    refs = _validate_q3_reference(q1, q2, legal, reference_actions, q3_input)
    if arm == "FULL":
        score = q1 + q2 + q3
    elif arm == "DROP_C1":
        score = q2 + q3
    else:  # DROP_C2
        score = q1 + q3
    route = DecodedRoute(
        arm=arm,
        scores=score,
        selected_actions=masked_argmax(score, legal),
        q3_evaluated=True,
        q3_reference_actions=refs,
        q3_input=q3_input,
    )
    route.verify(legal)
    return route


def main_actions(main_values: object, masks: object) -> np.ndarray:
    """Decode the independent frozen legacy MAIN surface."""

    values = _surface(main_values, field="MAIN")
    return masked_argmax(values, _mask(masks, rows=int(values.shape[0])))


@dataclass(frozen=True)
class LineageBinding:
    """One frozen Q1/Q2/learned-Q3 checkpoint lineage for the screen."""

    initialization_seed: int
    source_lineage: int
    q1_checkpoint_sha256: str
    q2_checkpoint_sha256: str
    q3_checkpoint_sha256: str
    q3_output_unit_mode: str = Q3_OUTPUT_UNIT_MODE

    def verify(self) -> None:
        _positive_int(self.initialization_seed, field="initialization_seed")
        _positive_int(self.source_lineage, field="source_lineage")
        for field in (
            "q1_checkpoint_sha256",
            "q2_checkpoint_sha256",
            "q3_checkpoint_sha256",
        ):
            _digest(getattr(self, field), field=field)
        if self.q3_output_unit_mode != Q3_OUTPUT_UNIT_MODE:
            raise V019FiveArmScreenError(
                "lineage Q3 checkpoint is not normalized_bits_per_kappa"
            )

    def as_dict(self) -> dict[str, object]:
        self.verify()
        return asdict(self)


@dataclass(frozen=True)
class V019FiveArmScreenSpec:
    """Post-gate short-screen identity; no world identity has a default."""

    evaluation_seeds: tuple[int, ...]
    field_component: str
    field_root_digests: tuple[tuple[int, str], ...]
    lineage_bindings: tuple[LineageBinding, ...]
    main_policy_sha256: str
    episodes: int = 100
    checkpoint_every_episodes: int = CHECKPOINT_EVERY_EPISODES
    users: int = DEFAULT_USERS
    steps: int = DEFAULT_STEPS
    evaluation_split: str = EVALUATION_SPLIT
    claim_ceiling: str = CLAIM_CEILING
    output_unit_mode: str = Q3_OUTPUT_UNIT_MODE

    def verify(self) -> None:
        if isinstance(self.episodes, bool) or not isinstance(self.episodes, int) or self.episodes <= 0:
            raise V019FiveArmScreenError("episodes must be a positive integer")
        if len(self.evaluation_seeds) != self.episodes:
            raise V019FiveArmScreenError("evaluation_seeds must cover every configured episode")
        if len(set(self.evaluation_seeds)) != len(self.evaluation_seeds):
            raise V019FiveArmScreenError("evaluation_seeds must be unique")
        for index, seed in enumerate(self.evaluation_seeds):
            _positive_int(seed, field=f"evaluation_seeds[{index}]")
        if not isinstance(self.field_component, str) or not self.field_component.strip():
            raise V019FiveArmScreenError("field_component must be nonempty")
        if any(
            not isinstance(pair, (tuple, list)) or len(pair) != 2
            for pair in self.field_root_digests
        ):
            raise V019FiveArmScreenError("field_root_digests must contain seed/digest pairs")
        digest_map = dict(self.field_root_digests)
        if set(digest_map) != set(self.evaluation_seeds):
            raise V019FiveArmScreenError("field_root_digests must cover exactly the evaluation seeds")
        if len(self.field_root_digests) != len(digest_map):
            raise V019FiveArmScreenError("field_root_digests contains duplicate seeds")
        for seed, digest in self.field_root_digests:
            _positive_int(seed, field="field_root_digests.seed")
            _digest(digest, field="field_root_digests.sha256")
        if len(set(digest_map.values())) != len(digest_map):
            raise V019FiveArmScreenError(
                "each evaluation world must bind a distinct keyed-field root"
            )
        if len(self.lineage_bindings) != 3:
            raise V019FiveArmScreenError("the screen requires exactly three frozen lineages")
        if any(not isinstance(binding, LineageBinding) for binding in self.lineage_bindings):
            raise V019FiveArmScreenError("lineage_bindings contains a malformed record")
        init_seeds = {binding.initialization_seed for binding in self.lineage_bindings}
        source_lineages = {binding.source_lineage for binding in self.lineage_bindings}
        if len(init_seeds) != 3 or len(source_lineages) != 3:
            raise V019FiveArmScreenError("lineage bindings must be distinct")
        for binding in self.lineage_bindings:
            binding.verify()
        _digest(self.main_policy_sha256, field="main_policy_sha256")
        if self.checkpoint_every_episodes != CHECKPOINT_EVERY_EPISODES:
            raise V019FiveArmScreenError("checkpoint cadence must be exactly every 100 episodes")
        if self.episodes % self.checkpoint_every_episodes != 0:
            raise V019FiveArmScreenError("episodes must end on a 100-episode checkpoint")
        if self.users != DEFAULT_USERS or self.steps != DEFAULT_STEPS:
            raise V019FiveArmScreenError("V0.19 short screen uses 100 users and ten steps")
        if self.evaluation_split != EVALUATION_SPLIT:
            raise V019FiveArmScreenError("physical screen is TRAIN-only")
        if self.claim_ceiling != CLAIM_CEILING:
            raise V019FiveArmScreenError("claim ceiling cannot be widened")
        if self.output_unit_mode != Q3_OUTPUT_UNIT_MODE:
            raise V019FiveArmScreenError(
                "physical screen must use normalized_bits_per_kappa"
            )

    @property
    def checkpoint_schedule(self) -> tuple[int, ...]:
        self.verify()
        return tuple(range(self.checkpoint_every_episodes, self.episodes + 1, self.checkpoint_every_episodes))

    def field_digest_for(self, evaluation_seed: int) -> str:
        self.verify()
        try:
            return dict(self.field_root_digests)[int(evaluation_seed)]
        except KeyError as error:
            raise V019FiveArmScreenError("evaluation seed has no frozen field digest") from error

    def as_dict(self) -> dict[str, object]:
        self.verify()
        return {
            "schema": SCREEN_SCHEMA,
            "evaluation_seeds": [int(seed) for seed in self.evaluation_seeds],
            "field_component": self.field_component,
            "field_root_digests": [
                [int(seed), digest] for seed, digest in self.field_root_digests
            ],
            "lineage_bindings": [binding.as_dict() for binding in self.lineage_bindings],
            "main_policy_sha256": self.main_policy_sha256,
            "episodes": int(self.episodes),
            "checkpoint_every_episodes": int(self.checkpoint_every_episodes),
            "users": int(self.users),
            "steps": int(self.steps),
            "evaluation_split": self.evaluation_split,
            "claim_ceiling": self.claim_ceiling,
            "output_unit_mode": self.output_unit_mode,
        }


@dataclass(frozen=True)
class V019EpisodeReceipt:
    """One additive physical TRAIN receipt from one arm/lineage/world."""

    arm: str
    episode_index: int
    evaluation_seed: int
    total_bits: float
    total_energy_j: float
    decision_count: int
    served_user_steps: int
    field_root_digest: str
    initialization_seed: int | None = None
    source_lineage: int | None = None
    q1_checkpoint_sha256: str | None = None
    q2_checkpoint_sha256: str | None = None
    q3_checkpoint_sha256: str | None = None
    main_policy_sha256: str | None = None
    q3_evaluated: bool = False
    q3_reference_mode: str = "NOT_APPLICABLE"
    q3_reference_actions_sha256: str | None = None
    q3_state_sha256: str | None = None
    q3_state_schema: str | None = None
    q3_output_unit_mode: str = "NOT_APPLICABLE"
    action_trace_sha256: str | None = None
    evaluation_split: str = EVALUATION_SPLIT
    test_split_opened: bool = False
    episode_training: bool = False
    learner_update: bool = False

    def __post_init__(self) -> None:
        if self.arm not in ARMS:
            raise V019FiveArmScreenError(f"unknown arm: {self.arm}")
        for field in (
            "q3_evaluated",
            "test_split_opened",
            "episode_training",
            "learner_update",
        ):
            if not isinstance(getattr(self, field), bool):
                raise V019FiveArmScreenError(f"{field} must be Boolean")
        for field in ("episode_index", "evaluation_seed", "decision_count"):
            _positive_int(getattr(self, field), field=field)
        _digest(self.field_root_digest, field="field_root_digest")
        bits = float(self.total_bits)
        energy = float(self.total_energy_j)
        if not math.isfinite(bits) or bits < 0.0:
            raise V019FiveArmScreenError("total_bits must be finite and nonnegative")
        if not math.isfinite(energy) or energy <= 0.0:
            raise V019FiveArmScreenError("total_energy_j must be finite and positive")
        served = _nonnegative_int(self.served_user_steps, field="served_user_steps")
        decisions = int(self.decision_count)
        if served > decisions:
            raise V019FiveArmScreenError("served_user_steps exceeds decision_count")
        if self.evaluation_split != EVALUATION_SPLIT:
            raise V019FiveArmScreenError("episode receipt is not TRAIN-only")
        if self.test_split_opened or self.episode_training or self.learner_update:
            raise V019FiveArmScreenError("episode receipt crossed a forbidden boundary")
        if self.action_trace_sha256 is not None:
            _digest(self.action_trace_sha256, field="action_trace_sha256")
        if self.arm in ROUTE_ARMS:
            _positive_int(self.initialization_seed, field="initialization_seed")
            _positive_int(self.source_lineage, field="source_lineage")
            for field in (
                "q1_checkpoint_sha256",
                "q2_checkpoint_sha256",
                "q3_checkpoint_sha256",
            ):
                _digest(getattr(self, field), field=field)
            if self.main_policy_sha256 is not None:
                raise V019FiveArmScreenError("route receipt must not carry MAIN policy digest")
            expected_q3 = self.arm in Q3_ACTIVE_ARMS
            if bool(self.q3_evaluated) != expected_q3:
                raise V019FiveArmScreenError("route q3_evaluated flag disagrees with arm")
            if self.q3_output_unit_mode != Q3_OUTPUT_UNIT_MODE:
                raise V019FiveArmScreenError(
                    "route Q3 output unit mode is not normalized_bits_per_kappa"
                )
            if expected_q3:
                if self.q3_reference_mode != Q3_REFERENCE_MODE:
                    raise V019FiveArmScreenError("active route lacks fixed Q1+Q2 Q3 reference mode")
                _digest(self.q3_reference_actions_sha256, field="q3_reference_actions_sha256")
                _digest(self.q3_state_sha256, field="q3_state_sha256")
                if self.q3_state_schema != Q3_STATE_SCHEMA:
                    raise V019FiveArmScreenError("active route Q3 state schema is stale")
            else:
                if self.q3_reference_mode != "NOT_APPLICABLE":
                    raise V019FiveArmScreenError("DROP_C3 must not carry a Q3 reference mode")
                if any(
                    value is not None
                    for value in (
                        self.q3_reference_actions_sha256,
                        self.q3_state_sha256,
                        self.q3_state_schema,
                    )
                ):
                    raise V019FiveArmScreenError("DROP_C3 must not carry Q3 input receipts")
        else:
            if any(value is not None for value in (self.initialization_seed, self.source_lineage)):
                raise V019FiveArmScreenError("MAIN receipt must not carry a route lineage")
            if any(
                value is not None
                for value in (
                    self.q1_checkpoint_sha256,
                    self.q2_checkpoint_sha256,
                    self.q3_checkpoint_sha256,
                )
            ):
                raise V019FiveArmScreenError("MAIN receipt must not carry route checkpoint digests")
            _digest(self.main_policy_sha256, field="main_policy_sha256")
            if self.q3_evaluated or self.q3_reference_mode != "NOT_APPLICABLE":
                raise V019FiveArmScreenError("MAIN must not evaluate Q3")
            if any(
                value is not None
                for value in (
                    self.q3_reference_actions_sha256,
                    self.q3_state_sha256,
                    self.q3_state_schema,
                )
            ):
                raise V019FiveArmScreenError("MAIN must not carry Q3 input receipts")
            if self.q3_output_unit_mode != "NOT_APPLICABLE":
                raise V019FiveArmScreenError(
                    "MAIN must not carry a Q3 output unit mode"
                )

    @property
    def ratio_of_sums_ee_bits_per_j(self) -> float:
        return float(self.total_bits) / float(self.total_energy_j)

    @property
    def served_fraction(self) -> float:
        return int(self.served_user_steps) / int(self.decision_count)

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload.update(
            {
                "ratio_of_sums_ee_bits_per_j": self.ratio_of_sums_ee_bits_per_j,
                "served_fraction": self.served_fraction,
                "outage_fraction": 1.0 - self.served_fraction,
            }
        )
        return payload

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> "V019EpisodeReceipt":
        if not isinstance(row, Mapping):
            raise V019FiveArmScreenError("episode receipt must be an object")
        required = {
            "arm",
            "episode_index",
            "evaluation_seed",
            "total_bits",
            "total_energy_j",
            "decision_count",
            "served_user_steps",
            "field_root_digest",
        }
        missing = sorted(required - set(row))
        if missing:
            raise V019FiveArmScreenError(
                f"episode receipt is missing {', '.join(missing)}"
            )
        fields = {
            field
            for field in cls.__dataclass_fields__
            if field in row
        }
        result = cls(**{field: row[field] for field in fields})
        if "ratio_of_sums_ee_bits_per_j" in row and not math.isclose(
            float(row["ratio_of_sums_ee_bits_per_j"]),
            result.ratio_of_sums_ee_bits_per_j,
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise V019FiveArmScreenError("receipt EE ratio disagrees with totals")
        for field, expected in (
            ("served_fraction", result.served_fraction),
            ("outage_fraction", 1.0 - result.served_fraction),
        ):
            if field in row and not math.isclose(
                float(row[field]), expected, rel_tol=1e-12, abs_tol=1e-12
            ):
                raise V019FiveArmScreenError(f"receipt {field} disagrees with counts")
        return result


def _normalise_receipts(
    rows: Sequence[V019EpisodeReceipt | Mapping[str, Any]],
) -> tuple[V019EpisodeReceipt, ...]:
    materialised: list[V019EpisodeReceipt] = []
    for row in rows:
        materialised.append(
            row if isinstance(row, V019EpisodeReceipt) else V019EpisodeReceipt.from_mapping(row)
        )
    if not materialised:
        raise V019FiveArmScreenError("cannot aggregate an empty arm")
    return tuple(materialised)


def ratio_of_sums(total_bits: float, total_energy_j: float) -> float:
    bits = float(total_bits)
    energy = float(total_energy_j)
    if not math.isfinite(bits) or bits < 0.0:
        raise V019FiveArmScreenError("total_bits must be finite and nonnegative")
    if not math.isfinite(energy) or energy <= 0.0:
        raise V019FiveArmScreenError("total_energy_j must be finite and positive")
    return bits / energy


def aggregate_arm(
    rows: Sequence[V019EpisodeReceipt | Mapping[str, Any]],
    *,
    arm: str | None = None,
) -> dict[str, object]:
    """Pool additive bits/energy first; the mean episode ratio is diagnostic."""

    materialised = _normalise_receipts(rows)
    labels = {row.arm for row in materialised}
    if len(labels) != 1:
        raise V019FiveArmScreenError("arm aggregate contains mixed arms")
    label = next(iter(labels))
    if arm is not None and arm != label:
        raise V019FiveArmScreenError("arm aggregate label disagrees with rows")
    keys = [
        (row.arm, row.episode_index, row.evaluation_seed, row.initialization_seed)
        for row in materialised
    ]
    if len(set(keys)) != len(keys):
        raise V019FiveArmScreenError(f"{label} contains duplicate receipt keys")
    bits = math.fsum(float(row.total_bits) for row in materialised)
    energy = math.fsum(float(row.total_energy_j) for row in materialised)
    decisions = sum(int(row.decision_count) for row in materialised)
    served = sum(int(row.served_user_steps) for row in materialised)
    if decisions <= 0 or served < 0 or served > decisions:
        raise V019FiveArmScreenError("aggregate service counts are invalid")
    return {
        "arm": label,
        "rows": len(materialised),
        "decision_count": decisions,
        "served_user_steps": served,
        "served_fraction": served / decisions,
        "outage_fraction": 1.0 - served / decisions,
        "total_bits": float(bits),
        "total_energy_j": float(energy),
        "pooled_ratio_of_sums_ee_bits_per_j": ratio_of_sums(bits, energy),
        "mean_episode_ee_bits_per_j": math.fsum(
            row.ratio_of_sums_ee_bits_per_j for row in materialised
        )
        / len(materialised),
    }


def _relative_contrast(
    full: Mapping[str, object], comparator: Mapping[str, object]
) -> dict[str, object]:
    full_ee = float(full["pooled_ratio_of_sums_ee_bits_per_j"])
    comparator_ee = float(comparator["pooled_ratio_of_sums_ee_bits_per_j"])
    if comparator_ee <= 0.0 or not math.isfinite(full_ee) or not math.isfinite(comparator_ee):
        raise V019FiveArmScreenError("contrast EE denominator is invalid")
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


def _validate_pairing(
    materialised: Mapping[str, tuple[V019EpisodeReceipt, ...]],
) -> None:
    route_keys = {
        arm: {
            (row.episode_index, row.evaluation_seed, row.initialization_seed)
            for row in materialised[arm]
        }
        for arm in ROUTE_ARMS
    }
    if len({frozenset(keys) for keys in route_keys.values()}) != 1:
        raise V019FiveArmScreenError("route arms do not share one world/lineage grid")
    main_keys = {
        (row.episode_index, row.evaluation_seed)
        for row in materialised[MAIN_ARM]
    }
    projected_route_keys = {
        (episode, world)
        for episode, world, _lineage in route_keys["FULL"]
    }
    if main_keys != projected_route_keys:
        raise V019FiveArmScreenError("MAIN does not cover the paired evaluation grid")
    fields: dict[int, str] = {}
    for rows in materialised.values():
        for row in rows:
            previous = fields.setdefault(row.evaluation_seed, row.field_root_digest)
            if previous != row.field_root_digest:
                raise V019FiveArmScreenError(
                    "one evaluation world uses multiple keyed fading fields"
                )
    # Active Q3 routes must share both the detached reference and full state
    # digest for each world/lineage.  This is the explicit ablation audit.
    by_key: dict[tuple[int, int, int], dict[str, V019EpisodeReceipt]] = {}
    for arm in Q3_ACTIVE_ARMS:
        for row in materialised[arm]:
            key = (row.episode_index, row.evaluation_seed, int(row.initialization_seed))
            by_key.setdefault(key, {})[arm] = row
    for key, rows in by_key.items():
        if set(rows) != set(Q3_ACTIVE_ARMS):
            raise V019FiveArmScreenError(f"Q3 active-arm panel is incomplete at {key}")
        reference_digests = {row.q3_reference_actions_sha256 for row in rows.values()}
        state_digests = {row.q3_state_sha256 for row in rows.values()}
        if len(reference_digests) != 1 or len(state_digests) != 1:
            raise V019FiveArmScreenError(
                "DROP_C1/DROP_C2 changed the learned Q3 input/reference definition"
            )


def per_initialization_aggregates(
    rows_by_arm: Mapping[str, Sequence[V019EpisodeReceipt | Mapping[str, Any]]],
    *,
    initialization_seeds: Sequence[int],
) -> dict[str, object]:
    """Keep each of the three lineages visible in marginal EE diagnostics."""

    materialised = {
        arm: _normalise_receipts(rows_by_arm[arm]) for arm in ARMS
    }
    result: dict[str, object] = {}
    for seed in initialization_seeds:
        route = {
            arm: [
                row
                for row in materialised[arm]
                if row.initialization_seed == int(seed)
            ]
            for arm in ROUTE_ARMS
        }
        if any(not rows for rows in route.values()):
            raise V019FiveArmScreenError(f"lineage {seed} is absent from a route arm")
        summaries = {
            arm: aggregate_arm(route[arm], arm=arm) for arm in ROUTE_ARMS
        }
        # MAIN is a shared frozen policy, so compare each route lineage to the
        # same paired MAIN world grid.  It is not duplicated as three receipts.
        main = aggregate_arm(materialised[MAIN_ARM], arm=MAIN_ARM)
        contrasts = {
            f"{arm}_minus_MAIN": _relative_contrast(summaries[arm], main)
            for arm in ROUTE_ARMS
        }
        contrasts.update(
            {
                f"FULL_minus_{arm}": _relative_contrast(
                    summaries["FULL"], summaries[arm]
                )
                for arm in ("DROP_C1", "DROP_C2", "DROP_C3")
            }
        )
        result[str(int(seed))] = {
            "summaries": summaries,
            "main_summary": main,
            "contrasts": contrasts,
        }
    return result


def evaluate_ordering(
    aggregate: Mapping[str, object],
    per_initialization: Mapping[str, object],
) -> dict[str, object]:
    """Apply the pre-outcome FULL/drop/MAIN ordering contract."""

    summaries = aggregate.get("summaries")
    if not isinstance(summaries, Mapping):
        raise V019FiveArmScreenError("aggregate lacks arm summaries")
    full_ee = float(summaries["FULL"]["pooled_ratio_of_sums_ee_bits_per_j"])
    main_ee = float(summaries[MAIN_ARM]["pooled_ratio_of_sums_ee_bits_per_j"])
    drops = ("DROP_C1", "DROP_C2", "DROP_C3")
    full_gt_drop = {
        arm: full_ee > float(summaries[arm]["pooled_ratio_of_sums_ee_bits_per_j"])
        for arm in drops
    }
    drop_gt_main = {
        arm: float(summaries[arm]["pooled_ratio_of_sums_ee_bits_per_j"]) > main_ee
        for arm in drops
    }
    service_noninferior = {
        arm: int(summaries["FULL"]["served_user_steps"])
        >= int(summaries[arm]["served_user_steps"])
        for arm in (*drops, MAIN_ARM)
    }
    lineage_positive_counts: dict[str, int] = {}
    lineage_count = len(per_initialization)
    for arm in drops:
        count = 0
        for payload in per_initialization.values():
            if not isinstance(payload, Mapping):
                raise V019FiveArmScreenError("per-initialization payload is malformed")
            contrasts = payload.get("contrasts")
            if not isinstance(contrasts, Mapping):
                raise V019FiveArmScreenError("per-initialization contrasts are missing")
            contrast = contrasts.get(f"FULL_minus_{arm}")
            if not isinstance(contrast, Mapping):
                raise V019FiveArmScreenError("per-initialization marginal is missing")
            if float(contrast["relative_delta"]) > 0.0:
                count += 1
        lineage_positive_counts[arm] = count
    lineage_support = {
        arm: count >= 2 and lineage_count == 3
        for arm, count in lineage_positive_counts.items()
    }
    pooled_marginals = {
        arm: bool(full_gt_drop[arm]) for arm in drops
    }
    passed = bool(
        all(full_gt_drop.values())
        and all(drop_gt_main.values())
        and all(service_noninferior.values())
        and all(pooled_marginals.values())
        and all(lineage_support.values())
    )
    return {
        "status": "PASS_SHORT_SCREEN_ORDERING" if passed else "FAIL_SHORT_SCREEN_ORDERING",
        "required_ordering": {
            "FULL_greater_than_each_drop": full_gt_drop,
            "each_drop_greater_than_MAIN": drop_gt_main,
            "no_total_order_required_among_drops": True,
            "MAIN_is_lowest": bool(main_ee < full_ee and all(drop_gt_main.values())),
        },
        "pooled_marginal_pass": pooled_marginals,
        "lineage_positive_counts": lineage_positive_counts,
        "lineage_support_pass": lineage_support,
        "service_noninferior": service_noninferior,
        "passed": passed,
        "claim_ceiling": CLAIM_CEILING,
    }


def aggregate_five_arm(
    rows_by_arm: Mapping[str, Sequence[V019EpisodeReceipt | Mapping[str, Any]]],
    *,
    initialization_seeds: Sequence[int] | None = None,
) -> dict[str, object]:
    """Aggregate exactly FULL/DROP_C1/DROP_C2/DROP_C3/MAIN."""

    if not isinstance(rows_by_arm, Mapping) or set(rows_by_arm) != set(ARMS):
        raise V019FiveArmScreenError(
            "five-arm screen requires exactly FULL, DROP_C1, DROP_C2, DROP_C3, MAIN"
        )
    materialised = {
        arm: _normalise_receipts(rows_by_arm[arm]) for arm in ARMS
    }
    _validate_pairing(materialised)
    summaries = {
        arm: aggregate_arm(materialised[arm], arm=arm) for arm in ARMS
    }
    contrasts = {
        f"FULL_minus_{arm}": _relative_contrast(summaries["FULL"], summaries[arm])
        for arm in ("DROP_C1", "DROP_C2", "DROP_C3", MAIN_ARM)
    }
    result: dict[str, object] = {
        "schema": SCREEN_SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "arms": list(ARMS),
        "route_arms": list(ROUTE_ARMS),
        "summaries": summaries,
        "contrasts": contrasts,
        "paired_route_keys": len(
            {
                (row.episode_index, row.evaluation_seed, row.initialization_seed)
                for row in materialised["FULL"]
            }
        ),
        "paired_main_keys": len(
            {
                (row.episode_index, row.evaluation_seed)
                for row in materialised[MAIN_ARM]
            }
        ),
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "output_unit_mode": Q3_OUTPUT_UNIT_MODE,
    }
    if initialization_seeds is not None:
        result["per_initialization"] = per_initialization_aggregates(
            materialised, initialization_seeds=initialization_seeds
        )
        result["ordering"] = evaluate_ordering(
            result,
            result["per_initialization"],  # type: ignore[arg-type]
        )
    return result


@dataclass(frozen=True)
class CheckpointEvent:
    """Read-only event at one 100-episode boundary."""

    arm: str
    episode_index: int
    configured_episodes: int
    receipts: tuple[V019EpisodeReceipt, ...]

    def summary(self) -> dict[str, object]:
        return aggregate_arm(self.receipts, arm=self.arm)


class RouteEpisodeRunner(Protocol):
    def __call__(
        self,
        *,
        arm: str,
        episode_index: int,
        evaluation_seed: int,
        lineage: LineageBinding,
        field_root_digest: str,
    ) -> V019EpisodeReceipt | Mapping[str, Any]:
        """Run one route episode using a pre-bound field and lineage."""


class MainEpisodeRunner(Protocol):
    def __call__(
        self,
        *,
        arm: str,
        episode_index: int,
        evaluation_seed: int,
        field_root_digest: str,
        main_policy_sha256: str,
    ) -> V019EpisodeReceipt | Mapping[str, Any]:
        """Run one independent frozen MAIN episode."""


CheckpointCallback: TypeAlias = Callable[[CheckpointEvent], Mapping[str, Any] | None]


def _write_json(path: Path, payload: Mapping[str, Any], *, overwrite: bool = False) -> str:
    if path.exists() or path.is_symlink():
        if not overwrite:
            raise V019FiveArmScreenError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")
    if overwrite:
        path.write_bytes(encoded)
    else:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary = Path(temporary_name)
        try:
            temporary.write_bytes(encoded)
            os.link(temporary, path)
        except FileExistsError as error:
            raise V019FiveArmScreenError(f"refusing to overwrite {path}") from error
        finally:
            temporary.unlink(missing_ok=True)
    return hashlib.sha256(encoded).hexdigest()


def _normalise_route_receipt(
    raw: V019EpisodeReceipt | Mapping[str, Any],
    *,
    arm: str,
    episode_index: int,
    evaluation_seed: int,
    lineage: LineageBinding,
    field_root_digest: str,
) -> V019EpisodeReceipt:
    receipt = raw if isinstance(raw, V019EpisodeReceipt) else V019EpisodeReceipt.from_mapping(raw)
    if (
        receipt.arm != arm
        or receipt.episode_index != episode_index
        or receipt.evaluation_seed != evaluation_seed
        or receipt.initialization_seed != lineage.initialization_seed
        or receipt.source_lineage != lineage.source_lineage
        or receipt.field_root_digest != field_root_digest
    ):
        raise V019FiveArmScreenError("route callback returned an unpaired receipt")
    for field in (
        "q1_checkpoint_sha256",
        "q2_checkpoint_sha256",
        "q3_checkpoint_sha256",
    ):
        if getattr(receipt, field) != getattr(lineage, field):
            raise V019FiveArmScreenError(f"route receipt {field} is not the frozen lineage binding")
    if receipt.q3_output_unit_mode != lineage.q3_output_unit_mode:
        raise V019FiveArmScreenError(
            "route receipt Q3 output unit mode is not the frozen lineage binding"
        )
    return receipt


def _normalise_main_receipt(
    raw: V019EpisodeReceipt | Mapping[str, Any],
    *,
    episode_index: int,
    evaluation_seed: int,
    field_root_digest: str,
    main_policy_sha256: str,
) -> V019EpisodeReceipt:
    receipt = raw if isinstance(raw, V019EpisodeReceipt) else V019EpisodeReceipt.from_mapping(raw)
    if (
        receipt.arm != MAIN_ARM
        or receipt.episode_index != episode_index
        or receipt.evaluation_seed != evaluation_seed
        or receipt.field_root_digest != field_root_digest
        or receipt.main_policy_sha256 != main_policy_sha256
    ):
        raise V019FiveArmScreenError("MAIN callback returned an unpaired receipt")
    return receipt


def run_five_arm_screen(
    *,
    spec: V019FiveArmScreenSpec,
    route_episode_runner: RouteEpisodeRunner,
    main_episode_runner: MainEpisodeRunner,
    output_dir: str | Path | None = None,
    checkpoint_callback: CheckpointCallback | None = None,
) -> dict[str, object]:
    """Run the post-gate paired short screen through injected callbacks.

    This loop is runnable once the parent fills the explicit post-gate
    bindings.  It itself performs no simulator call: a callback owns one
    physical episode and must return a complete, authenticated receipt.
    """

    spec.verify()
    if not callable(route_episode_runner) or not callable(main_episode_runner):
        raise V019FiveArmScreenError("episode callbacks must be callable")
    destination: Path | None = None
    if output_dir is not None:
        destination = Path(output_dir)
        if destination.exists() or destination.is_symlink():
            raise V019FiveArmScreenError(f"refusing to overwrite screen output: {destination}")
        destination.mkdir(parents=True, exist_ok=False)
        (destination / "checkpoints").mkdir()
        _write_json(
            destination / "status.json",
            {
                "schema": SCREEN_SCHEMA,
                "status": "RUNNING",
                "claim_ceiling": CLAIM_CEILING,
                "spec": spec.as_dict(),
                "completed_episode_indices": 0,
                "test_split_opened": False,
                "episode_training": False,
                "learner_update": False,
            },
        )

    rows_by_arm: dict[str, list[V019EpisodeReceipt]] = {arm: [] for arm in ARMS}
    checkpoint_hashes: dict[str, list[str]] = {arm: [] for arm in ARMS}
    q3_binding_by_key: dict[tuple[int, int, int], tuple[str, str]] = {}
    checkpoints = set(spec.checkpoint_schedule)
    for episode_index, evaluation_seed in enumerate(spec.evaluation_seeds, start=1):
        field_digest = spec.field_digest_for(evaluation_seed)
        for lineage in spec.lineage_bindings:
            for arm in ROUTE_ARMS:
                receipt = _normalise_route_receipt(
                    route_episode_runner(
                        arm=arm,
                        episode_index=episode_index,
                        evaluation_seed=int(evaluation_seed),
                        lineage=lineage,
                        field_root_digest=field_digest,
                    ),
                    arm=arm,
                    episode_index=episode_index,
                    evaluation_seed=int(evaluation_seed),
                    lineage=lineage,
                    field_root_digest=field_digest,
                )
                rows_by_arm[arm].append(receipt)
                if arm in Q3_ACTIVE_ARMS:
                    key = (
                        episode_index,
                        int(evaluation_seed),
                        int(lineage.initialization_seed),
                    )
                    binding = (
                        str(receipt.q3_reference_actions_sha256),
                        str(receipt.q3_state_sha256),
                    )
                    previous = q3_binding_by_key.setdefault(key, binding)
                    if previous != binding:
                        raise V019FiveArmScreenError(
                            "DROP_C1/DROP_C2 changed the learned Q3 input/reference definition"
                        )
        main = _normalise_main_receipt(
            main_episode_runner(
                arm=MAIN_ARM,
                episode_index=episode_index,
                evaluation_seed=int(evaluation_seed),
                field_root_digest=field_digest,
                main_policy_sha256=spec.main_policy_sha256,
            ),
            episode_index=episode_index,
            evaluation_seed=int(evaluation_seed),
            field_root_digest=field_digest,
            main_policy_sha256=spec.main_policy_sha256,
        )
        rows_by_arm[MAIN_ARM].append(main)
        if episode_index in checkpoints:
            for arm in ARMS:
                event = CheckpointEvent(
                    arm=arm,
                    episode_index=episode_index,
                    configured_episodes=spec.episodes,
                    receipts=tuple(
                        row
                        for row in rows_by_arm[arm]
                        if row.episode_index <= episode_index
                    ),
                )
                callback_payload = checkpoint_callback(event) if checkpoint_callback else None
                checkpoint_body: dict[str, Any] = {
                    "schema": CHECKPOINT_SCHEMA,
                    "claim_ceiling": CLAIM_CEILING,
                    "arm": arm,
                    "episode_index": episode_index,
                    "configured_episodes": spec.episodes,
                    "receipt_count": len(event.receipts),
                    "summary": event.summary(),
                    "output_unit_mode": spec.output_unit_mode,
                    "evaluation_split": EVALUATION_SPLIT,
                    "test_split_opened": False,
                    "episode_training": False,
                    "learner_update": False,
                }
                if callback_payload is not None:
                    if not isinstance(callback_payload, Mapping):
                        raise V019FiveArmScreenError("checkpoint callback must return a mapping")
                    checkpoint_body["callback_payload"] = dict(callback_payload)
                if destination is not None:
                    path = destination / "checkpoints" / f"{arm.lower()}-episode-{episode_index:06d}.json"
                    checkpoint_hashes[arm].append(_write_json(path, checkpoint_body))
        if destination is not None:
            _write_json(
                destination / "status.json",
                {
                    "schema": SCREEN_SCHEMA,
                    "status": "RUNNING",
                    "claim_ceiling": CLAIM_CEILING,
                    "spec": spec.as_dict(),
                    "completed_episode_indices": episode_index,
                    "test_split_opened": False,
                    "episode_training": False,
                    "learner_update": False,
                },
                overwrite=True,
            )

    aggregate = aggregate_five_arm(
        rows_by_arm,
        initialization_seeds=tuple(
            binding.initialization_seed for binding in spec.lineage_bindings
        ),
    )
    aggregate["spec"] = spec.as_dict()
    aggregate["checkpoint_file_sha256s"] = checkpoint_hashes
    aggregate["status"] = "COMPLETE_PLUMBING_ONLY"
    aggregate["efficacy_claim"] = False
    if destination is not None:
        receipts_payload = {
            "schema": SCREEN_SCHEMA,
            "claim_ceiling": CLAIM_CEILING,
            "output_unit_mode": spec.output_unit_mode,
            "rows_by_arm": {
                arm: [row.as_dict() for row in rows_by_arm[arm]] for arm in ARMS
            },
            "test_split_opened": False,
            "episode_training": False,
            "learner_update": False,
        }
        receipts_digest = _write_json(destination / "episode-receipts.json", receipts_payload)
        aggregate["episode_receipts_file_sha256"] = receipts_digest
        result_digest = _write_json(destination / "result.json", aggregate)
        _write_json(
            destination / "status.json",
            {
                **aggregate,
                "status": "COMPLETE_PLUMBING_ONLY",
                "result_file_sha256": result_digest,
            },
            overwrite=True,
        )
        aggregate["result_file_sha256"] = result_digest
    return aggregate


def read_rows_json(path: str | Path) -> Mapping[str, Sequence[Mapping[str, Any]]]:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise V019FiveArmScreenError(f"cannot read rows JSON: {source}") from error
    rows = payload.get("rows_by_arm") if isinstance(payload, Mapping) else payload
    if not isinstance(rows, Mapping):
        raise V019FiveArmScreenError("rows JSON must contain rows_by_arm")
    return rows


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows-json", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = aggregate_five_arm(read_rows_json(args.rows_json))
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


__all__ = [
    "ACTIVE_HEADS",
    "ACTION_DIM",
    "ARMS",
    "CHECKPOINT_EVERY_EPISODES",
    "CHECKPOINT_SCHEMA",
    "CLAIM_CEILING",
    "DecodedRoute",
    "EVALUATION_SPLIT",
    "LineageBinding",
    "MAIN_ARM",
    "MainEpisodeRunner",
    "Q3InputBinding",
    "Q3_ACTIVE_ARMS",
    "Q3_OUTPUT_UNIT_MODE",
    "Q3_REFERENCE_MODE",
    "Q3_STATE_SCHEMA",
    "ROUTE_ARMS",
    "RouteEpisodeRunner",
    "SCREEN_SCHEMA",
    "V019EpisodeReceipt",
    "V019FiveArmScreenError",
    "V019FiveArmScreenSpec",
    "aggregate_arm",
    "aggregate_five_arm",
    "canonical_sha256",
    "compose_route_scores",
    "evaluate_ordering",
    "file_sha256",
    "main_actions",
    "masked_argmax",
    "per_initialization_aggregates",
    "q3_reference_actions",
    "ratio_of_sums",
    "read_rows_json",
    "run_five_arm_screen",
]


if __name__ == "__main__":  # pragma: no cover - explicit receipt-only CLI
    raise SystemExit(main())
