"""V0.15 C3 pivotal residual-ranking source seam.

This module keeps the V0.14 action-set network and a zero-bootstrap residual
objective.  The learner-side change is the source frontier: one pair is
retained per source row instead of expanding every legal action against one
reference action.  The selected pair supplies the exact ZR residual; a
decision-aligned hinge additionally prevents an otherwise stable row from
being flipped by an unconstrained Q3 surface.

For a frozen learned background

``B(a) = Q1(a) + Q2_hat(a)``

the source teacher is ``argmax_a [B(a) + z3(a) / kappa]`` and the base is
``argmax_a B(a)``.  A pivotal row uses ``(base, teacher)``.  A stable row
uses ``(base, runner_up)`` where ``runner_up`` is the best non-base action
under the teacher surface.  In both cases the target is the unchanged,
signed ZR residual ``z3(candidate) - z3(base)``.  Thus this seam introduces
no new reward, rescaling, route weight, threshold, coordinator, or simulator
call.

The module is deliberately source-only.  It does not construct an
environment, open TEST data, or claim trajectory EE efficacy.  The learner
reuses :class:`V014ActionSetQNetwork`, but its loss is intentionally not the
V0.14 expanded-surface MSE: only the retained frontier residual is regressed;
the remaining legal actions appear only in the stability constraint.
"""

from __future__ import annotations

from collections.abc import Mapping
import copy
from dataclasses import asdict, dataclass
import math
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
import torch.optim as optim

from ..algorithms.ee_axis_pairwise import EEAxisPairBatch
from ..algorithms.ee_axis_v014_head import (
    EEAxisV014HeadConfig,
    V014ActionSetQNetwork,
)
from ..errors import MCRLContractError
from .finiteness import assert_finite_gradients, assert_finite_loss, assert_finite_parameters


V015_C3_PIVOTAL_SCHEMA = "multi-catfish-mcrl-v015-c3-pivotal-residual-ranking-v1"
V015_C3_PIVOTAL_CHECKPOINT_VERSION = 1
V015_C3_PIVOTAL_SOURCE_RULE = "learned-background-decision-frontier-one-pair-v1"
# These are method constants, not outcome-tuned hyperparameters.  The exact
# ZR residual is the only target.  Decision/stability terms merely constrain
# the deployment action surface against the same frozen background.
V015_C3_PIVOTAL_DECISION_WEIGHT = 1.0
V015_C3_PIVOTAL_STABILITY_WEIGHT = 1.0


class C3PivotalContractError(MCRLContractError):
    """A V0.15 pivotal C3 source or learner boundary was violated."""


def _finite_array(value: object, *, field: str, shape: tuple[int, ...]) -> np.ndarray:
    try:
        array = np.asarray(value)
    except (TypeError, ValueError) as error:
        raise C3PivotalContractError(f"{field} is not an array") from error
    if array.shape != shape or not np.all(np.isfinite(array)):
        raise C3PivotalContractError(
            f"{field} must be finite with shape {shape}, got {array.shape}"
        )
    return np.asarray(array, dtype=np.float64)


def _frozen(value: object, *, dtype: np.dtype[Any]) -> np.ndarray:
    result = np.array(value, dtype=dtype, copy=True, order="C")
    result.setflags(write=False)
    return result


def _validate_inputs(
    states: object,
    action_masks: object,
    q1_values: object,
    q2_values: object,
    z3_target_bits: object,
    *,
    kappa_bits: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    state_array = np.asarray(states)
    if state_array.ndim != 2 or state_array.shape[1] < 1:
        raise C3PivotalContractError("states must be a nonempty 2-D matrix")
    rows = int(state_array.shape[0])
    if rows < 1:
        raise C3PivotalContractError("source must contain at least one row")
    if not np.all(np.isfinite(state_array)):
        raise C3PivotalContractError("states must be finite")
    state_array = np.asarray(state_array, dtype=np.float32)

    masks = np.asarray(action_masks)
    if masks.dtype != np.bool_ or masks.shape != (rows, 28):
        raise C3PivotalContractError(
            f"action_masks must be Boolean shape ({rows},28), got {masks.shape}"
        )
    if not np.all(np.any(masks, axis=1)):
        raise C3PivotalContractError("every source row needs a legal action")
    masks = np.asarray(masks, dtype=np.bool_)

    q1 = _finite_array(q1_values, field="q1_values", shape=(rows, 28))
    q2 = _finite_array(q2_values, field="q2_values", shape=(rows, 28))
    z3 = _finite_array(z3_target_bits, field="z3_target_bits", shape=(rows, 28))
    if np.any(z3[~masks] != 0.0):
        raise C3PivotalContractError("z3_target_bits must be zero outside the legal mask")
    try:
        kappa = float(kappa_bits)
    except (TypeError, ValueError, OverflowError) as error:
        raise C3PivotalContractError("kappa_bits must be finite and positive") from error
    if not math.isfinite(kappa) or kappa <= 0.0:
        raise C3PivotalContractError("kappa_bits must be finite and positive")
    return state_array, masks, q1, q2, z3


def _masked_argmax(scores: np.ndarray, masks: np.ndarray) -> np.ndarray:
    masked = np.where(masks, scores, -np.inf)
    # np.argmax has the required deterministic lowest-action tie break.
    return np.argmax(masked, axis=1).astype(np.int64, copy=False)


@dataclass(frozen=True)
class V015C3PivotalLabels:
    """Decision-frontier labels derived from one frozen source surface."""

    background_values: np.ndarray
    teacher_values: np.ndarray
    base_actions: np.ndarray
    teacher_actions: np.ndarray
    runner_up_actions: np.ndarray
    pivotal: np.ndarray
    eligible: np.ndarray
    kappa_bits: float
    schema: str = V015_C3_PIVOTAL_SCHEMA

    def verify(self) -> None:
        background = np.asarray(self.background_values)
        teacher = np.asarray(self.teacher_values)
        if background.ndim != 2 or background.shape[1] != 28:
            raise C3PivotalContractError("background_values must have shape (N,28)")
        rows = int(background.shape[0])
        if teacher.shape != background.shape or not np.all(np.isfinite(background)):
            raise C3PivotalContractError("teacher/background surfaces are malformed")
        if not np.all(np.isfinite(teacher)):
            raise C3PivotalContractError("teacher values must be finite")
        for name in (
            "base_actions",
            "teacher_actions",
            "runner_up_actions",
        ):
            values = np.asarray(getattr(self, name))
            if values.shape != (rows,) or not np.issubdtype(values.dtype, np.integer):
                raise C3PivotalContractError(f"{name} must be an integer vector")
            if np.any(values < 0) or np.any(values >= 28):
                raise C3PivotalContractError(f"{name} contains an illegal action index")
        for name in ("pivotal", "eligible"):
            values = np.asarray(getattr(self, name))
            if values.dtype != np.bool_ or values.shape != (rows,):
                raise C3PivotalContractError(f"{name} must be Boolean shape ({rows},)")
        if not np.array_equal(
            np.asarray(self.pivotal),
            np.asarray(self.teacher_actions) != np.asarray(self.base_actions),
        ):
            raise C3PivotalContractError("pivotal labels disagree with teacher/base actions")
        if np.any(np.asarray(self.pivotal) & ~np.asarray(self.eligible)):
            raise C3PivotalContractError("every pivotal row must be eligible")
        if not math.isfinite(float(self.kappa_bits)) or float(self.kappa_bits) <= 0.0:
            raise C3PivotalContractError("kappa_bits must be finite and positive")
        if self.schema != V015_C3_PIVOTAL_SCHEMA:
            raise C3PivotalContractError("pivotal label schema is stale")


def derive_pivotal_labels(
    q1_values: object,
    q2_values: object,
    z3_target_bits: object,
    action_masks: object,
    *,
    kappa_bits: float,
) -> V015C3PivotalLabels:
    """Derive base/teacher/frontier labels without touching a simulator.

    ``q1_values`` and ``q2_values`` are already frozen surfaces.  The
    teacher uses the exact signed ZR target in dimensionless units; no
    learned Q3 or outcome-dependent quantity enters this construction.
    """

    _unused_states = np.zeros((np.asarray(q1_values).shape[0], 1), dtype=np.float32)
    _states, masks, q1, q2, z3 = _validate_inputs(
        _unused_states,
        action_masks,
        q1_values,
        q2_values,
        z3_target_bits,
        kappa_bits=kappa_bits,
    )
    del _states
    background = q1 + q2
    teacher_values = background + z3 / float(kappa_bits)
    base_actions = _masked_argmax(background, masks)
    teacher_actions = _masked_argmax(teacher_values, masks)
    pivotal = teacher_actions != base_actions

    runner_scores = np.where(masks, teacher_values, -np.inf)
    runner_scores[np.arange(runner_scores.shape[0]), base_actions] = -np.inf
    eligible = np.any(np.isfinite(runner_scores), axis=1)
    # A one-action row has no non-base comparison.  Its runner-up is a
    # harmless sentinel and the row is omitted from the learner pair set.
    runner_up = np.where(
        eligible,
        np.argmax(runner_scores, axis=1),
        base_actions,
    ).astype(np.int64, copy=False)
    labels = V015C3PivotalLabels(
        background_values=_frozen(background, dtype=np.dtype(np.float64)),
        teacher_values=_frozen(teacher_values, dtype=np.dtype(np.float64)),
        base_actions=_frozen(base_actions, dtype=np.dtype(np.int64)),
        teacher_actions=_frozen(teacher_actions, dtype=np.dtype(np.int64)),
        runner_up_actions=_frozen(runner_up, dtype=np.dtype(np.int64)),
        pivotal=_frozen(pivotal, dtype=np.dtype(np.bool_)),
        eligible=_frozen(eligible, dtype=np.dtype(np.bool_)),
        kappa_bits=float(kappa_bits),
    )
    labels.verify()
    return labels


@dataclass(frozen=True)
class V015C3PivotalPairs:
    """One retained pair per eligible source row.

    ``source_row_indices`` maps the compact pair rows back to the original
    source rows.  This makes the stable/pivotal counts auditable without
    retaining a second expanded dataset.
    """

    states: np.ndarray
    action_masks: np.ndarray
    background_values: np.ndarray
    reference_actions: np.ndarray
    candidate_actions: np.ndarray
    target_surplus_bits: np.ndarray
    source_row_indices: np.ndarray
    pivotal: np.ndarray
    base_actions: np.ndarray
    teacher_actions: np.ndarray
    runner_up_actions: np.ndarray
    kappa_bits: float
    schema: str = V015_C3_PIVOTAL_SCHEMA
    source_rule: str = V015_C3_PIVOTAL_SOURCE_RULE

    def verify(self) -> None:
        states = np.asarray(self.states)
        masks = np.asarray(self.action_masks)
        background = np.asarray(self.background_values)
        references = np.asarray(self.reference_actions)
        candidates = np.asarray(self.candidate_actions)
        targets = np.asarray(self.target_surplus_bits)
        source_rows = np.asarray(self.source_row_indices)
        pivotal = np.asarray(self.pivotal)
        rows = int(states.shape[0]) if states.ndim == 2 else -1
        if states.ndim != 2 or states.shape[1] < 1 or rows < 1:
            raise C3PivotalContractError("pivotal pairs need at least one state row")
        if (
            masks.dtype != np.bool_
            or masks.shape != (rows, 28)
            or background.shape != (rows, 28)
            or references.shape != (rows,)
            or candidates.shape != (rows,)
            or targets.shape != (rows,)
            or source_rows.shape != (rows,)
            or pivotal.dtype != np.bool_
            or pivotal.shape != (rows,)
        ):
            raise C3PivotalContractError("pivotal pair arrays are not row-aligned")
        if not np.all(np.isfinite(states)) or not np.all(np.isfinite(targets)):
            raise C3PivotalContractError("pivotal states/targets must be finite")
        if not np.all(np.isfinite(background)):
            raise C3PivotalContractError("pivotal background values must be finite")
        if not np.issubdtype(references.dtype, np.integer) or not np.issubdtype(
            candidates.dtype, np.integer
        ):
            raise C3PivotalContractError("pivotal actions must be integer arrays")
        if np.any(references < 0) or np.any(references >= 28) or np.any(
            candidates < 0
        ) or np.any(candidates >= 28):
            raise C3PivotalContractError("pivotal pair action is outside action space")
        if np.any(references == candidates):
            raise C3PivotalContractError("pivotal pair must compare distinct actions")
        indices = np.arange(rows)
        if not np.all(masks[indices, references]) or not np.all(masks[indices, candidates]):
            raise C3PivotalContractError("pivotal pair action is illegal under its mask")
        if not np.issubdtype(source_rows.dtype, np.integer) or np.any(source_rows < 0):
            raise C3PivotalContractError("source_row_indices must be nonnegative integers")
        if np.asarray(self.base_actions).shape != (rows,) or np.asarray(
            self.teacher_actions
        ).shape != (rows,) or np.asarray(self.runner_up_actions).shape != (rows,):
            raise C3PivotalContractError("pivotal audit actions are not row-aligned")
        expected_candidates = np.where(
            pivotal, np.asarray(self.teacher_actions), np.asarray(self.runner_up_actions)
        )
        if not np.array_equal(references, np.asarray(self.base_actions)):
            raise C3PivotalContractError("pair references must be the frozen base action")
        if not np.array_equal(candidates, expected_candidates):
            raise C3PivotalContractError("pair candidates disagree with pivotal labels")
        if not math.isfinite(float(self.kappa_bits)) or float(self.kappa_bits) <= 0.0:
            raise C3PivotalContractError("kappa_bits must be finite and positive")
        if self.schema != V015_C3_PIVOTAL_SCHEMA:
            raise C3PivotalContractError("pivotal pair schema is stale")
        if self.source_rule != V015_C3_PIVOTAL_SOURCE_RULE:
            raise C3PivotalContractError("pivotal source rule is stale")

    @property
    def rows(self) -> int:
        return int(np.asarray(self.states).shape[0])

    @property
    def pivotal_rows(self) -> int:
        return int(np.count_nonzero(np.asarray(self.pivotal)))

    @property
    def stable_rows(self) -> int:
        return self.rows - self.pivotal_rows

    def as_pairwise_batch(self) -> EEAxisPairBatch:
        """Expose the exact V0.14 pairwise learner input."""

        self.verify()
        batch = EEAxisPairBatch(
            states=np.asarray(self.states),
            reference_actions=np.asarray(self.reference_actions),
            candidate_actions=np.asarray(self.candidate_actions),
            target_surplus_bits=np.asarray(self.target_surplus_bits),
            action_masks=np.asarray(self.action_masks),
        )
        return batch

    def take(self, indices: object) -> "V015C3PivotalPairs":
        """Return an immutable cyclic mini-batch without changing source order."""

        selected = np.asarray(indices)
        if selected.ndim != 1 or not np.issubdtype(selected.dtype, np.integer):
            raise C3PivotalContractError("batch indices must be a one-dimensional integer array")
        selected = np.asarray(selected, dtype=np.int64)
        if selected.size < 1 or np.any(selected < 0) or np.any(selected >= self.rows):
            raise C3PivotalContractError("batch indices lie outside pivotal source rows")
        return V015C3PivotalPairs(
            states=_frozen(np.asarray(self.states)[selected], dtype=np.dtype(np.float32)),
            action_masks=_frozen(
                np.asarray(self.action_masks)[selected], dtype=np.dtype(np.bool_)
            ),
            background_values=_frozen(
                np.asarray(self.background_values)[selected], dtype=np.dtype(np.float64)
            ),
            reference_actions=_frozen(
                np.asarray(self.reference_actions)[selected], dtype=np.dtype(np.int64)
            ),
            candidate_actions=_frozen(
                np.asarray(self.candidate_actions)[selected], dtype=np.dtype(np.int64)
            ),
            target_surplus_bits=_frozen(
                np.asarray(self.target_surplus_bits)[selected], dtype=np.dtype(np.float64)
            ),
            source_row_indices=_frozen(
                np.asarray(self.source_row_indices)[selected], dtype=np.dtype(np.int64)
            ),
            pivotal=_frozen(np.asarray(self.pivotal)[selected], dtype=np.dtype(np.bool_)),
            base_actions=_frozen(
                np.asarray(self.base_actions)[selected], dtype=np.dtype(np.int64)
            ),
            teacher_actions=_frozen(
                np.asarray(self.teacher_actions)[selected], dtype=np.dtype(np.int64)
            ),
            runner_up_actions=_frozen(
                np.asarray(self.runner_up_actions)[selected], dtype=np.dtype(np.int64)
            ),
            kappa_bits=float(self.kappa_bits),
        )


def build_pivotal_pairs(
    states: object,
    action_masks: object,
    q1_values: object,
    q2_values: object,
    z3_target_bits: object,
    *,
    kappa_bits: float,
) -> V015C3PivotalPairs:
    """Build the one-frontier-pair source set for frozen learned ``Q2``.

    Stable one-action rows are intentionally excluded because no distinct
    comparison exists.  Pivotal rows can never be excluded: teacher and base
    differ only when at least two legal actions exist.
    """

    state_array = np.asarray(states)
    if state_array.ndim != 2:
        raise C3PivotalContractError("states must be a 2-D matrix")
    _states, masks, q1, q2, z3 = _validate_inputs(
        state_array,
        action_masks,
        q1_values,
        q2_values,
        z3_target_bits,
        kappa_bits=kappa_bits,
    )
    labels = derive_pivotal_labels(
        q1,
        q2,
        z3,
        masks,
        kappa_bits=kappa_bits,
    )
    selected = np.flatnonzero(np.asarray(labels.eligible)).astype(np.int64)
    if selected.size < 1:
        raise C3PivotalContractError("source has no row with two legal actions")
    base = np.asarray(labels.base_actions)
    teacher = np.asarray(labels.teacher_actions)
    runner = np.asarray(labels.runner_up_actions)
    pivotal = np.asarray(labels.pivotal)
    candidates_all = np.where(pivotal, teacher, runner)
    pair_rows = np.arange(state_array.shape[0])[selected]
    targets = z3[pair_rows, candidates_all[selected]] - z3[pair_rows, base[selected]]
    pairs = V015C3PivotalPairs(
        states=_frozen(state_array[selected], dtype=np.dtype(np.float32)),
        action_masks=_frozen(masks[selected], dtype=np.dtype(np.bool_)),
        background_values=_frozen(
            np.asarray(labels.background_values)[selected], dtype=np.dtype(np.float64)
        ),
        reference_actions=_frozen(base[selected], dtype=np.dtype(np.int64)),
        candidate_actions=_frozen(candidates_all[selected], dtype=np.dtype(np.int64)),
        target_surplus_bits=_frozen(targets, dtype=np.dtype(np.float64)),
        source_row_indices=_frozen(pair_rows, dtype=np.dtype(np.int64)),
        pivotal=_frozen(pivotal[selected], dtype=np.dtype(np.bool_)),
        base_actions=_frozen(base[selected], dtype=np.dtype(np.int64)),
        teacher_actions=_frozen(teacher[selected], dtype=np.dtype(np.int64)),
        runner_up_actions=_frozen(runner[selected], dtype=np.dtype(np.int64)),
        kappa_bits=float(kappa_bits),
    )
    pairs.verify()
    return pairs


def evaluate_pivotal_decisions(
    *,
    q1_values: object,
    q2_values: object,
    z3_target_bits: object,
    q3_values: object,
    action_masks: object,
    kappa_bits: float,
) -> dict[str, float | int]:
    """Return source-only decision diagnostics for one frozen Q3 surface.

    The diagnostics are learnability/decision-alignment evidence only.  They
    do not evaluate an environment trajectory or infer an EE improvement.
    """

    q3 = np.asarray(q3_values)
    rows = np.asarray(q1_values).shape[0]
    if q3.shape != (rows, 28) or not np.all(np.isfinite(q3)):
        raise C3PivotalContractError("q3_values must be finite shape (N,28)")
    labels = derive_pivotal_labels(
        q1_values,
        q2_values,
        z3_target_bits,
        action_masks,
        kappa_bits=kappa_bits,
    )
    masks = np.asarray(action_masks)
    student = _masked_argmax(np.asarray(labels.background_values) + q3, masks)
    base = np.asarray(labels.base_actions)
    teacher = np.asarray(labels.teacher_actions)
    pivotal = np.asarray(labels.pivotal)
    stable = ~pivotal
    pair_mask = np.asarray(labels.eligible)
    pair_rows = np.flatnonzero(pair_mask)
    pair_candidates = np.where(pivotal, teacher, np.asarray(labels.runner_up_actions))
    z3 = np.asarray(z3_target_bits, dtype=np.float64)
    q3_float = np.asarray(q3, dtype=np.float64)
    target_delta = z3[pair_rows, pair_candidates[pair_rows]] - z3[
        pair_rows, base[pair_rows]
    ]
    predicted_delta = q3_float[pair_rows, pair_candidates[pair_rows]] - q3_float[
        pair_rows, base[pair_rows]
    ]
    result: dict[str, float | int] = {
        "rows": int(rows),
        "eligible_rows": int(np.count_nonzero(pair_mask)),
        "single_legal_rows": int(np.count_nonzero(~pair_mask)),
        "pivotal_rows": int(np.count_nonzero(pivotal)),
        "stable_rows": int(np.count_nonzero(stable)),
        "pivotal_rate": float(np.mean(pivotal)),
        "pivotal_agreement": float(np.mean(student[pivotal] == teacher[pivotal]))
        if np.any(pivotal)
        else float("nan"),
        "stable_preservation": float(np.mean(student[stable] == base[stable]))
        if np.any(stable)
        else float("nan"),
        "all_teacher_agreement": float(np.mean(student == teacher)),
        "frontier_residual_mae_bits": float(np.mean(np.abs(predicted_delta - target_delta)))
        if pair_rows.size
        else float("nan"),
    }
    return result


class EEAxisV015C3PivotalLearner:
    """Train Q3 with frontier residuals plus decision/stability constraints.

    The network is the existing V0.14 ActionSet scorer.  Unlike the rejected
    exploratory one-pair MSE, this objective uses the retained pair only for
    the exact residual and checks the actual deployment score ``B + Q3``:

    ``L_piv = mean[(Q3(t)-Q3(b)) - (z3(t)-z3(b))/kappa]^2``

    ``L_flip = mean[relu((B(b)+Q3(b))-(B(t)+Q3(t)))^2]``

    over pivotal rows, and

    ``L_stable = mean[relu((B(a)+Q3(a))-(B(b)+Q3(b)))^2]``

    over every legal non-base action on rows with ``teacher == base``.
    ``beta * mean(Q3(b)^2)`` is the inherited pairwise gauge.  The latter
    terms are not new rewards; they keep a learned residual from changing a
    decision that the C3 teacher did not mark as pivotal.  Frozen ``B`` is
    passed in the source object and never receives a gradient.
    """

    def __init__(
        self,
        config: EEAxisV014HeadConfig,
        *,
        train_seed: int,
        device: str = "cpu",
    ) -> None:
        if not isinstance(train_seed, int) or isinstance(train_seed, bool):
            raise C3PivotalContractError("train_seed must be an integer")
        if config.action_dim != 28:
            raise C3PivotalContractError("V0.15 C3 learner requires the 28-action V0.14 surface")
        self.config = config
        self.train_seed = train_seed
        self.device = torch.device(device)
        torch.manual_seed(train_seed)
        self.q = V014ActionSetQNetwork(config).to(self.device)
        # Q3 is a residual surface over a frozen learned background.  Start
        # at the exact zero residual so an untrained checkpoint cannot alter
        # the base argmax before the first update.  The output layer still
        # receives gradients; hidden layers begin adapting after it moves.
        output_layer = self.q.scorer[-1]
        if not isinstance(output_layer, torch.nn.Linear):
            raise C3PivotalContractError("V0.14 ActionSet scorer lacks a linear output layer")
        torch.nn.init.zeros_(output_layer.weight)
        torch.nn.init.zeros_(output_layer.bias)
        self.optimizer = optim.Adam(self.q.parameters(), lr=float(config.learning_rate))

    def _arrays(self, pairs: V015C3PivotalPairs) -> tuple[torch.Tensor, ...]:
        if not isinstance(pairs, V015C3PivotalPairs):
            raise C3PivotalContractError("learner expects V015C3PivotalPairs")
        pairs.verify()
        return (
            torch.tensor(np.asarray(pairs.states), dtype=torch.float32, device=self.device),
            torch.tensor(np.asarray(pairs.action_masks), dtype=torch.bool, device=self.device),
            # The Q1+learned-Q2 background is a detached source label by
            # construction.  No tensor supplied here can backpropagate into
            # either frozen head.
            torch.tensor(
                np.asarray(pairs.background_values), dtype=torch.float32, device=self.device
            ).detach(),
            torch.tensor(
                np.asarray(pairs.reference_actions), dtype=torch.int64, device=self.device
            ),
            torch.tensor(
                np.asarray(pairs.candidate_actions), dtype=torch.int64, device=self.device
            ),
            torch.tensor(
                np.asarray(pairs.target_surplus_bits),
                dtype=torch.float32,
                device=self.device,
            )
            / float(self.config.kappa_bits),
            torch.tensor(np.asarray(pairs.pivotal), dtype=torch.bool, device=self.device),
        )

    @staticmethod
    def _mean_or_zero(value: torch.Tensor, *, like: torch.Tensor) -> torch.Tensor:
        return torch.mean(value) if value.numel() else like.sum() * 0.0

    def _loss(
        self, pairs: V015C3PivotalPairs
    ) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
        states, masks, background, references, candidates, target, pivotal = self._arrays(pairs)
        surface = self.q(states, masks)
        rows = torch.arange(states.shape[0], device=self.device)
        q_reference = surface[rows, references]
        q_candidate = surface[rows, candidates]
        residual = q_candidate - q_reference - target
        pivotal_residual_mse = self._mean_or_zero(residual[pivotal].square(), like=surface)

        scores = background + surface
        score_reference = scores[rows, references]
        score_candidate = scores[rows, candidates]
        pivotal_decision_violation = self._mean_or_zero(
            F.relu(score_reference[pivotal] - score_candidate[pivotal]).square(),
            like=surface,
        )

        # A stable row must keep the frozen base action on top of every legal
        # alternative.  There is no margin hyperparameter: equality is the
        # exact teacher boundary and numpy/torch argmax share the first-index
        # tie break.
        stable = ~pivotal
        legal_nonbase = masks.clone()
        legal_nonbase[rows, references] = False
        stable_constraints = F.relu(scores - score_reference[:, None]).square()
        stable_constraints = stable_constraints[stable[:, None] & legal_nonbase]
        stable_decision_violation = self._mean_or_zero(stable_constraints, like=surface)
        gauge_mse = torch.mean(q_reference.square())
        loss = (
            pivotal_residual_mse
            + V015_C3_PIVOTAL_DECISION_WEIGHT * pivotal_decision_violation
            + V015_C3_PIVOTAL_STABILITY_WEIGHT * stable_decision_violation
            + float(self.config.beta) * gauge_mse
        )
        return loss, {
            "pivotal_residual_mse": pivotal_residual_mse,
            "pivotal_decision_violation": pivotal_decision_violation,
            "stable_decision_violation": stable_decision_violation,
            "gauge_mse": gauge_mse,
        }

    def measure(self, pairs: V015C3PivotalPairs) -> dict[str, float | int | str]:
        self.q.eval()
        with torch.no_grad():
            loss, components = self._loss(pairs)
        return {
            "batch_size": pairs.rows,
            "pivotal_rows": pairs.pivotal_rows,
            "stable_rows": pairs.stable_rows,
            "loss": float(loss.detach().cpu()),
            **{
                name: float(value.detach().cpu())
                for name, value in components.items()
            },
            "source_rule": V015_C3_PIVOTAL_SOURCE_RULE,
        }

    def update(self, pairs: V015C3PivotalPairs) -> dict[str, float | int | str]:
        self.q.train()
        loss, components = self._loss(pairs)
        self.optimizer.zero_grad(set_to_none=True)
        loss.backward()
        assert_finite_loss(loss, objective=0)
        assert_finite_gradients(self.q.parameters(), objective=0)
        self.optimizer.step()
        assert_finite_parameters([self.q])
        return {
            "batch_size": pairs.rows,
            "pivotal_rows": pairs.pivotal_rows,
            "stable_rows": pairs.stable_rows,
            "loss": float(loss.detach().cpu()),
            **{
                name: float(value.detach().cpu())
                for name, value in components.items()
            },
            "source_rule": V015_C3_PIVOTAL_SOURCE_RULE,
        }

    def q_values(self, states: object, action_masks: object) -> np.ndarray:
        values = np.asarray(states, dtype=np.float32)
        masks = np.asarray(action_masks)
        if values.ndim != 2 or values.shape[1] != self.config.state_dim:
            raise C3PivotalContractError(
                f"states must have shape (N,{self.config.state_dim})"
            )
        if not np.all(np.isfinite(values)):
            raise C3PivotalContractError("states must be finite")
        if masks.dtype != np.bool_ or masks.shape != (values.shape[0], self.config.action_dim):
            raise C3PivotalContractError("action_masks must be Boolean and action-aligned")
        self.q.eval()
        with torch.no_grad():
            state_tensor = torch.tensor(values, dtype=torch.float32, device=self.device)
            mask_tensor = torch.tensor(masks, dtype=torch.bool, device=self.device)
            return self.q(state_tensor, mask_tensor).cpu().numpy()

    def checkpoint_state(self, *, update_count: int) -> dict[str, object]:
        if isinstance(update_count, bool) or not isinstance(update_count, int) or update_count < 0:
            raise C3PivotalContractError("update_count must be a nonnegative integer")
        return {
            "schema": V015_C3_PIVOTAL_SCHEMA,
            "checkpoint_version": V015_C3_PIVOTAL_CHECKPOINT_VERSION,
            "algorithm": V015_C3_PIVOTAL_SOURCE_RULE,
            "config": asdict(self.config),
            "train_seed": int(self.train_seed),
            "update_count": int(update_count),
            # Deep-copy because callers may retain a checkpoint dictionary
            # while this learner continues updating on another rung.
            "q": copy.deepcopy(self.q.state_dict()),
            "optimizer": copy.deepcopy(self.optimizer.state_dict()),
            "claim_ceiling": "NO_DEPLOYED_EFFICACY_OR_EE_CLAIM",
            "test_split_opened": False,
            "episode_training": False,
        }

    def load_checkpoint_state(self, state: Mapping[str, object]) -> int:
        if not isinstance(state, Mapping):
            raise C3PivotalContractError("checkpoint must be a mapping")
        if state.get("schema") != V015_C3_PIVOTAL_SCHEMA:
            raise C3PivotalContractError("checkpoint schema is stale")
        if state.get("checkpoint_version") != V015_C3_PIVOTAL_CHECKPOINT_VERSION:
            raise C3PivotalContractError("unsupported pivotal checkpoint version")
        if state.get("algorithm") != V015_C3_PIVOTAL_SOURCE_RULE:
            raise C3PivotalContractError("checkpoint algorithm is stale")
        if state.get("config") != asdict(self.config) or state.get("train_seed") != self.train_seed:
            raise C3PivotalContractError("pivotal checkpoint config/seed mismatch")
        if state.get("claim_ceiling") != "NO_DEPLOYED_EFFICACY_OR_EE_CLAIM":
            raise C3PivotalContractError("checkpoint claim ceiling drifted")
        if bool(state.get("test_split_opened", True)) or bool(state.get("episode_training", True)):
            raise C3PivotalContractError("pivotal checkpoint crossed a forbidden boundary")
        try:
            self.q.load_state_dict(state["q"])
            self.optimizer.load_state_dict(state["optimizer"])
        except (KeyError, TypeError, ValueError, RuntimeError) as error:
            raise C3PivotalContractError("malformed pivotal ActionSet state") from error
        update_count = state.get("update_count")
        if isinstance(update_count, bool) or not isinstance(update_count, int) or update_count < 0:
            raise C3PivotalContractError("checkpoint update_count is malformed")
        return update_count


__all__ = [
    "C3PivotalContractError",
    "EEAxisV015C3PivotalLearner",
    "V015C3PivotalLabels",
    "V015C3PivotalPairs",
    "V015_C3_PIVOTAL_CHECKPOINT_VERSION",
    "V015_C3_PIVOTAL_SCHEMA",
    "V015_C3_PIVOTAL_SOURCE_RULE",
    "build_pivotal_pairs",
    "derive_pivotal_labels",
    "evaluate_pivotal_decisions",
]
