"""B402 C3 learner with a masked teacher-distribution KL objective.

The B402 successor keeps the V0.16 402-dimensional, reference-conditioned
state carrier and the V0.14 permutation-equivariant ActionSet scorer.  Its
only learner change is the objective: every legal action in every source row
participates in a row-mean KL divergence between the frozen teacher surface
and the learned residual surface.  The context-specific background is
materialised by the caller before it crosses this module's interface.

For one source row, with legal set ``L``::

    T[a] = B[a] + z3[a] / kappa
    S[a] = B[a] + Q3(s, a)
    loss = mean_rows(KL(softmax(T[L]) || softmax(S[L])))
           + beta * mean_rows(Q3(s, reference)**2)

The mask is part of the interface, not a deployment convenience.  Illegal
actions are excluded from both normalisers and have no KL gradient.  This
module is source-only: it does not construct an environment, open TEST, or
evaluate trajectory EE.
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

from ..algorithms.ee_axis_v014_head import (
    EEAxisV014HeadConfig,
    V014ActionSetQNetwork,
)
from ..errors import MCRLContractError
from .finiteness import (
    assert_finite_gradients,
    assert_finite_loss,
    assert_finite_parameters,
)


B402_SOFTKL_SCHEMA = "multi-catfish-mcrl-b402-c3-softkl-row-kl-v1"
B402_SOFTKL_BATCH_SCHEMA = "multi-catfish-mcrl-b402-c3-softkl-batch-v1"
B402_SOFTKL_ALGORITHM = "multi-catfish-mcrl-b402-c3-softkl"
B402_SOFTKL_CHECKPOINT_VERSION = 1
B402_SOFTKL_CLAIM_CEILING = "NO_DEPLOYED_EFFICACY_OR_EE_CLAIM"

B402_ACTION_DIM = 28
B402_LOCAL_FEATURE_DIM = 14
B402_GLOBAL_FEATURE_DIM = 10
B402_STATE_DIM = B402_LOCAL_FEATURE_DIM * B402_ACTION_DIM + B402_GLOBAL_FEATURE_DIM
B402_HIDDEN_LAYERS = (100, 50, 50)
B402_ACTIVATION = "tanh"
B402_LEARNING_RATE = 0.001
B402_BETA = 0.1


class B402SoftKLContractError(MCRLContractError):
    """A B402 source, objective, or checkpoint boundary was violated."""


def _frozen(value: object, *, dtype: np.dtype[Any], field: str) -> np.ndarray:
    try:
        result = np.array(value, dtype=dtype, copy=True, order="C")
    except (TypeError, ValueError) as error:
        raise B402SoftKLContractError(f"{field} is malformed") from error
    result.setflags(write=False)
    return result


def _finite_float(value: object, *, field: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise B402SoftKLContractError(f"{field} must be finite") from error
    if not math.isfinite(parsed):
        raise B402SoftKLContractError(f"{field} must be finite")
    return parsed


@dataclass(frozen=True)
class B402SoftKLBatch:
    """Immutable full-surface rows consumed by the B402 learner.

    ``background_values`` is already the context-specific detached ``B``
    surface.  The context code itself is intentionally absent from this
    interface: the state and background are materialised by the gate before
    training.  Unlike the V0.15 frontier-pair representation, one-action rows
    and every legal action remain present.
    """

    states: np.ndarray
    action_masks: np.ndarray
    background_values: np.ndarray
    z3_target_bits: np.ndarray
    reference_actions: np.ndarray
    kappa_bits: float
    schema: str = B402_SOFTKL_BATCH_SCHEMA

    @property
    def rows(self) -> int:
        return int(np.asarray(self.states).shape[0])

    def verify(self) -> None:
        states = np.asarray(self.states)
        masks = np.asarray(self.action_masks)
        background = np.asarray(self.background_values)
        z3 = np.asarray(self.z3_target_bits)
        references = np.asarray(self.reference_actions)

        if self.schema != B402_SOFTKL_BATCH_SCHEMA:
            raise B402SoftKLContractError("B402 batch schema is stale")
        if (
            states.ndim != 2
            or states.shape[1] != B402_STATE_DIM
            or states.shape[0] < 1
            or states.dtype != np.dtype(np.float32)
            or not np.all(np.isfinite(states))
        ):
            raise B402SoftKLContractError(
                f"states must be finite float32 shape (N,{B402_STATE_DIM})"
            )
        rows = int(states.shape[0])
        if (
            masks.dtype != np.bool_
            or masks.shape != (rows, B402_ACTION_DIM)
            or not np.all(np.any(masks, axis=1))
        ):
            raise B402SoftKLContractError(
                f"action_masks must be nonempty Boolean shape (N,{B402_ACTION_DIM})"
            )
        for name, values in (
            ("background_values", background),
            ("z3_target_bits", z3),
        ):
            if (
                values.dtype != np.dtype(np.float64)
                or values.shape != (rows, B402_ACTION_DIM)
                or not np.all(np.isfinite(values))
            ):
                raise B402SoftKLContractError(
                    f"{name} must be finite float64 shape (N,{B402_ACTION_DIM})"
                )
        if (
            references.dtype != np.dtype(np.int64)
            or references.shape != (rows,)
            or np.any(references < 0)
            or np.any(references >= B402_ACTION_DIM)
        ):
            raise B402SoftKLContractError(
                f"reference_actions must be int64 shape ({rows},) in [0,{B402_ACTION_DIM})"
            )
        row_index = np.arange(rows, dtype=np.int64)
        if not np.all(masks[row_index, references]):
            raise B402SoftKLContractError(
                "reference_actions are illegal under the stored mask"
            )
        if np.any(z3[~masks] != 0.0):
            raise B402SoftKLContractError(
                "z3_target_bits must be zero outside the legal mask"
            )
        if np.any(z3[row_index, references] != 0.0):
            raise B402SoftKLContractError(
                "z3_target_bits must be exactly zero at every reference action"
            )
        kappa = _finite_float(self.kappa_bits, field="kappa_bits")
        if kappa <= 0.0:
            raise B402SoftKLContractError("kappa_bits must be positive")
        for name in (
            "states",
            "action_masks",
            "background_values",
            "z3_target_bits",
            "reference_actions",
        ):
            if np.asarray(getattr(self, name)).flags.writeable:
                raise B402SoftKLContractError(f"{name} must be immutable")

    def take(self, indices: object) -> "B402SoftKLBatch":
        """Return an owned immutable cyclic mini-batch."""

        self.verify()
        selected = np.asarray(indices)
        if (
            selected.ndim != 1
            or selected.dtype.kind not in "iu"
            or selected.size < 1
            or np.any(selected < 0)
            or np.any(selected >= self.rows)
        ):
            raise B402SoftKLContractError(
                "batch indices must be a nonempty one-dimensional integer vector"
            )
        selected = np.asarray(selected, dtype=np.int64)
        return B402SoftKLBatch(
            states=_frozen(
                np.asarray(self.states)[selected],
                dtype=np.dtype(np.float32),
                field="states",
            ),
            action_masks=_frozen(
                np.asarray(self.action_masks)[selected],
                dtype=np.dtype(np.bool_),
                field="action_masks",
            ),
            background_values=_frozen(
                np.asarray(self.background_values)[selected],
                dtype=np.dtype(np.float64),
                field="background_values",
            ),
            z3_target_bits=_frozen(
                np.asarray(self.z3_target_bits)[selected],
                dtype=np.dtype(np.float64),
                field="z3_target_bits",
            ),
            reference_actions=_frozen(
                np.asarray(self.reference_actions)[selected],
                dtype=np.dtype(np.int64),
                field="reference_actions",
            ),
            kappa_bits=float(self.kappa_bits),
        )


def build_b402_softkl_batch(
    *,
    states: object,
    action_masks: object,
    background_values: object,
    z3_target_bits: object,
    reference_actions: object,
    kappa_bits: float,
) -> B402SoftKLBatch:
    """Copy, freeze, and validate full B402 source surfaces."""

    try:
        raw_masks = np.asarray(action_masks)
    except (TypeError, ValueError) as error:
        raise B402SoftKLContractError("action_masks is malformed") from error
    if raw_masks.dtype != np.bool_:
        raise B402SoftKLContractError("action_masks must be Boolean")
    try:
        parsed_kappa = float(kappa_bits)
    except (TypeError, ValueError, OverflowError) as error:
        raise B402SoftKLContractError("kappa_bits must be finite") from error
    batch = B402SoftKLBatch(
        states=_frozen(states, dtype=np.dtype(np.float32), field="states"),
        action_masks=_frozen(
            action_masks, dtype=np.dtype(np.bool_), field="action_masks"
        ),
        background_values=_frozen(
            background_values,
            dtype=np.dtype(np.float64),
            field="background_values",
        ),
        z3_target_bits=_frozen(
            z3_target_bits,
            dtype=np.dtype(np.float64),
            field="z3_target_bits",
        ),
        reference_actions=_frozen(
            reference_actions,
            dtype=np.dtype(np.int64),
            field="reference_actions",
        ),
        kappa_bits=parsed_kappa,
    )
    batch.verify()
    return batch


def _validate_kl_tensors(
    teacher_logits: torch.Tensor,
    student_logits: torch.Tensor,
    legal_mask: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    if not (
        isinstance(teacher_logits, torch.Tensor)
        and isinstance(student_logits, torch.Tensor)
        and isinstance(legal_mask, torch.Tensor)
    ):
        raise B402SoftKLContractError("masked KL expects torch tensors")
    if (
        teacher_logits.ndim != 2
        or student_logits.shape != teacher_logits.shape
        or legal_mask.shape != teacher_logits.shape
        or teacher_logits.shape[0] < 1
        or teacher_logits.shape[1] != B402_ACTION_DIM
    ):
        raise B402SoftKLContractError(
            f"masked KL tensors must align as (N,{B402_ACTION_DIM})"
        )
    if legal_mask.dtype != torch.bool:
        raise B402SoftKLContractError("masked KL legal_mask must be Boolean")
    if not (
        teacher_logits.device == student_logits.device == legal_mask.device
    ):
        raise B402SoftKLContractError("masked KL tensors must share a device")
    if not bool(torch.isfinite(teacher_logits).all()) or not bool(
        torch.isfinite(student_logits).all()
    ):
        raise B402SoftKLContractError("masked KL logits must be finite")
    if not bool(torch.any(legal_mask, dim=1).all()):
        raise B402SoftKLContractError(
            "masked KL requires at least one legal action per row"
        )
    # Float64 is deliberate: source backgrounds and ZR surfaces are stored in
    # float64, and the log-normaliser should not be the first place that loses
    # their dynamic range.  Gradients still flow back to a float32 Q3 tensor.
    return (
        teacher_logits.to(dtype=torch.float64),
        student_logits.to(dtype=torch.float64),
        legal_mask,
    )


def masked_kl_rows(
    teacher_logits: torch.Tensor,
    student_logits: torch.Tensor,
    legal_mask: torch.Tensor,
) -> torch.Tensor:
    """Return one finite ``KL(teacher || student)`` value per row.

    Both softmax normalisers see only legal actions.  Illegal log-probability
    entries are replaced with zero *after* ``log_softmax`` and before the
    product, avoiding the ``0 * -inf`` NaN trap.  The returned tensor is not
    reduced across rows; callers perform the prescribed row mean.
    """

    teacher, student, mask = _validate_kl_tensors(
        teacher_logits, student_logits, legal_mask
    )
    negative_inf = torch.full_like(teacher, -torch.inf)
    teacher_raw = F.log_softmax(torch.where(mask, teacher, negative_inf), dim=-1)
    student_raw = F.log_softmax(torch.where(mask, student, negative_inf), dim=-1)

    # A very large but finite logit gap can underflow a teacher probability to
    # zero in floating point.  Such a term is mathematically zero; exclude it
    # before multiplying by a possibly infinite log-ratio.  A non-finite
    # contribution with positive teacher mass remains a hard error below.
    teacher_prob = torch.where(
        mask, torch.exp(teacher_raw), torch.zeros_like(teacher_raw)
    )
    support = mask & (teacher_prob > 0.0) & torch.isfinite(teacher_raw)
    teacher_logp = torch.where(support, teacher_raw, torch.zeros_like(teacher_raw))
    student_logp = torch.where(support, student_raw, torch.zeros_like(student_raw))
    terms = teacher_prob * (teacher_logp - student_logp)
    row_kl = torch.where(support, terms, torch.zeros_like(terms)).sum(dim=-1)
    if not bool(torch.isfinite(row_kl).all()):
        raise B402SoftKLContractError("masked KL produced a non-finite row")
    return row_kl


def masked_kl_loss(
    teacher_logits: torch.Tensor,
    student_logits: torch.Tensor,
    legal_mask: torch.Tensor,
) -> torch.Tensor:
    """Return the prescribed mean of per-row masked KL values."""

    return torch.mean(masked_kl_rows(teacher_logits, student_logits, legal_mask))


class EEAxisB402SoftKLLearner:
    """One independent action-shared Q3 head for the B402 objective."""

    def __init__(
        self,
        config: EEAxisV014HeadConfig,
        *,
        train_seed: int,
        device: str = "cpu",
    ) -> None:
        if isinstance(train_seed, bool) or not isinstance(train_seed, int):
            raise B402SoftKLContractError("train_seed must be an integer")
        if (
            config.action_dim != B402_ACTION_DIM
            or config.local_feature_dim != B402_LOCAL_FEATURE_DIM
            or config.global_feature_dim != B402_GLOBAL_FEATURE_DIM
            or config.hidden_layers != B402_HIDDEN_LAYERS
            or config.activation != B402_ACTIVATION
            or float(config.learning_rate).hex() != float(B402_LEARNING_RATE).hex()
            or float(config.beta).hex() != float(B402_BETA).hex()
        ):
            raise B402SoftKLContractError(
                "B402 learner requires the frozen 402-D ActionSet configuration"
            )
        self.config = config
        self.train_seed = train_seed
        self.device = torch.device(device)
        torch.manual_seed(train_seed)
        self.q = V014ActionSetQNetwork(config).to(self.device)
        output_layer = self.q.scorer[-1]
        if not isinstance(output_layer, torch.nn.Linear):
            raise B402SoftKLContractError(
                "ActionSet scorer lacks a linear output layer"
            )
        # The residual surface is exactly zero before the first update.  This
        # makes the initial deployment argmax equal the frozen background.
        torch.nn.init.zeros_(output_layer.weight)
        torch.nn.init.zeros_(output_layer.bias)
        self.optimizer = optim.Adam(
            self.q.parameters(), lr=float(config.learning_rate)
        )

    def _arrays(
        self, batch: B402SoftKLBatch
    ) -> tuple[torch.Tensor, ...]:
        if not isinstance(batch, B402SoftKLBatch):
            raise B402SoftKLContractError("learner expects B402SoftKLBatch")
        batch.verify()
        if float(batch.kappa_bits).hex() != float(self.config.kappa_bits).hex():
            raise B402SoftKLContractError("batch kappa differs from learner config")
        return (
            torch.tensor(
                np.asarray(batch.states),
                dtype=torch.float32,
                device=self.device,
            ),
            torch.tensor(
                np.asarray(batch.action_masks),
                dtype=torch.bool,
                device=self.device,
            ),
            torch.tensor(
                np.asarray(batch.background_values),
                dtype=torch.float64,
                device=self.device,
            ).detach(),
            torch.tensor(
                np.asarray(batch.z3_target_bits),
                dtype=torch.float64,
                device=self.device,
            ).detach(),
            torch.tensor(
                np.asarray(batch.reference_actions),
                dtype=torch.int64,
                device=self.device,
            ),
        )

    def _loss(
        self, batch: B402SoftKLBatch
    ) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
        states, masks, background, z3, references = self._arrays(batch)
        q3_float32 = self.q(states, masks)
        if not bool(torch.isfinite(q3_float32).all()):
            raise B402SoftKLContractError("Q3 surface is non-finite")
        q3 = q3_float32.to(dtype=torch.float64)
        teacher = background + z3 / float(self.config.kappa_bits)
        student = background + q3
        row_kl = masked_kl_rows(teacher, student, masks)
        rows = torch.arange(states.shape[0], device=self.device)
        q_reference = q3[rows, references]
        row_mean_kl = torch.mean(row_kl)
        gauge_mse = torch.mean(q_reference.square())
        loss = row_mean_kl + float(self.config.beta) * gauge_mse
        return loss, {
            "row_mean_kl": row_mean_kl,
            "gauge_mse": gauge_mse,
        }

    @staticmethod
    def _metrics(
        batch: B402SoftKLBatch,
        loss: torch.Tensor,
        components: Mapping[str, torch.Tensor],
    ) -> dict[str, float | int | str]:
        return {
            "algorithm": B402_SOFTKL_ALGORITHM,
            "batch_size": batch.rows,
            "loss": float(loss.detach().cpu()),
            **{
                name: float(value.detach().cpu())
                for name, value in components.items()
            },
        }

    def measure(self, batch: B402SoftKLBatch) -> dict[str, float | int | str]:
        """Measure the full-surface objective without changing parameters."""

        self.q.eval()
        with torch.no_grad():
            loss, components = self._loss(batch)
        return self._metrics(batch, loss, components)

    def update(self, batch: B402SoftKLBatch) -> dict[str, float | int | str]:
        """Apply one Adam update and fail loudly on non-finite values."""

        self.q.train()
        loss, components = self._loss(batch)
        assert_finite_loss(loss, objective=0)
        self.optimizer.zero_grad(set_to_none=True)
        loss.backward()
        assert_finite_gradients(self.q.parameters(), objective=0)
        self.optimizer.step()
        assert_finite_parameters([self.q])
        return self._metrics(batch, loss, components)

    def q_values(self, states: object, action_masks: object) -> np.ndarray:
        """Return the residual surface; callers own the final masked argmax."""

        values = np.asarray(states, dtype=np.float32)
        masks = np.asarray(action_masks)
        if (
            values.ndim != 2
            or values.shape[1] != self.config.state_dim
            or values.shape[0] < 1
            or not np.all(np.isfinite(values))
        ):
            raise B402SoftKLContractError(
                f"states must be finite shape (N,{self.config.state_dim})"
            )
        if (
            masks.dtype != np.bool_
            or masks.shape != (values.shape[0], self.config.action_dim)
            or not np.all(np.any(masks, axis=1))
        ):
            raise B402SoftKLContractError(
                "action_masks must be nonempty Boolean and action-aligned"
            )
        self.q.eval()
        with torch.no_grad():
            state_tensor = torch.tensor(
                values, dtype=torch.float32, device=self.device
            )
            mask_tensor = torch.tensor(
                masks, dtype=torch.bool, device=self.device
            )
            result = self.q(state_tensor, mask_tensor).cpu().numpy()
        result = np.array(result, dtype=np.float32, copy=True)
        if not np.all(np.isfinite(result)):
            raise B402SoftKLContractError("Q3 surface is non-finite")
        return result

    def checkpoint_state(self, *, update_count: int) -> dict[str, object]:
        """Return a deep-copied, source-only learner checkpoint payload."""

        if (
            isinstance(update_count, bool)
            or not isinstance(update_count, int)
            or update_count < 0
        ):
            raise B402SoftKLContractError(
                "update_count must be a nonnegative integer"
            )
        return {
            "schema": B402_SOFTKL_SCHEMA,
            "checkpoint_version": B402_SOFTKL_CHECKPOINT_VERSION,
            "algorithm": B402_SOFTKL_ALGORITHM,
            "config": asdict(self.config),
            "train_seed": int(self.train_seed),
            "update_count": int(update_count),
            "q": copy.deepcopy(self.q.state_dict()),
            "optimizer": copy.deepcopy(self.optimizer.state_dict()),
            "claim_ceiling": B402_SOFTKL_CLAIM_CEILING,
            "test_split_opened": False,
            "episode_training": False,
        }

    def load_checkpoint_state(self, state: Mapping[str, object]) -> int:
        """Load only a matching B402 source-only checkpoint."""

        if not isinstance(state, Mapping):
            raise B402SoftKLContractError("checkpoint must be a mapping")
        if state.get("schema") != B402_SOFTKL_SCHEMA:
            raise B402SoftKLContractError("checkpoint schema is stale")
        if state.get("checkpoint_version") != B402_SOFTKL_CHECKPOINT_VERSION:
            raise B402SoftKLContractError("unsupported B402 checkpoint version")
        if state.get("algorithm") != B402_SOFTKL_ALGORITHM:
            raise B402SoftKLContractError("checkpoint algorithm is stale")
        if state.get("config") != asdict(self.config):
            raise B402SoftKLContractError("B402 checkpoint config mismatch")
        if state.get("train_seed") != self.train_seed:
            raise B402SoftKLContractError("B402 checkpoint train_seed mismatch")
        if state.get("claim_ceiling") != B402_SOFTKL_CLAIM_CEILING:
            raise B402SoftKLContractError("checkpoint claim ceiling drifted")
        if state.get("test_split_opened") is not False or state.get(
            "episode_training"
        ) is not False:
            raise B402SoftKLContractError(
                "checkpoint crossed a forbidden split or episode boundary"
            )
        update_count = state.get("update_count")
        if (
            isinstance(update_count, bool)
            or not isinstance(update_count, int)
            or update_count < 0
        ):
            raise B402SoftKLContractError("checkpoint update_count is malformed")
        try:
            self.q.load_state_dict(state["q"])
            self.optimizer.load_state_dict(state["optimizer"])
        except (KeyError, TypeError, ValueError, RuntimeError) as error:
            raise B402SoftKLContractError("malformed B402 learner state") from error
        assert_finite_parameters([self.q])
        return int(update_count)


__all__ = [
    "B402_ACTION_DIM",
    "B402_ACTIVATION",
    "B402_BETA",
    "B402_GLOBAL_FEATURE_DIM",
    "B402_HIDDEN_LAYERS",
    "B402_LEARNING_RATE",
    "B402_LOCAL_FEATURE_DIM",
    "B402_SOFTKL_ALGORITHM",
    "B402_SOFTKL_BATCH_SCHEMA",
    "B402_SOFTKL_CHECKPOINT_VERSION",
    "B402_SOFTKL_CLAIM_CEILING",
    "B402_SOFTKL_SCHEMA",
    "B402_STATE_DIM",
    "B402SoftKLBatch",
    "B402SoftKLContractError",
    "EEAxisB402SoftKLLearner",
    "build_b402_softkl_batch",
    "masked_kl_loss",
    "masked_kl_rows",
]
