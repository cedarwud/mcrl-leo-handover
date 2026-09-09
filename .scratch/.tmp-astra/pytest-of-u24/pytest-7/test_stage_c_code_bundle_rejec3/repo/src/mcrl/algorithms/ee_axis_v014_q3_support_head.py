"""Deployable V0.14 Q3 precision-calibrated support-bonus learner.

The Q3 head predicts a nonnegative support bonus from the decision-time
ZR-Q3 state.  It has two independent action-set scorers:

* a support logit, trained with class-balanced binary cross entropy; and
* a positive surplus amplitude, trained only on supported comparisons.

The support posterior is corrected from the balanced training posterior to
the frozen natural TRAIN prior at inference.  A frozen support threshold
turns that posterior into a precision-calibrated bonus gate.  The
label-only compatibility array, route references, and surplus surfaces are
consumed only by :meth:`update`; they are not part of the 287-dimensional
deployment state.

This module is a learner boundary.  It does not construct a simulator, read
an evaluator, or run an episode.  The scorer form is shared with the ordinary
V0.14 independent action-set head so that the state/action contract remains
the same as the deployable Q3 route.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import asdict
import math
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
import torch.optim as optim

from ..env.action_contract import NO_OP_ACTION
from ..errors import MCRLContractError
from ..runtime.ee_axis_ops3 import OPS3_KAPPA_BITS
from ..runtime.ee_axis_v014_q3_state import (
    V014_Q3_GLOBAL_FEATURES,
    V014_Q3_LOCAL_FEATURES,
    V014_Q3_STATE_DIM,
)
from ..runtime.finiteness import (
    assert_finite_gradients,
    assert_finite_loss,
    assert_finite_parameters,
)
from .ee_axis_v014_head import (
    EEAxisV014HeadConfig,
    V014ActionSetQNetwork,
)


V014_Q3_SUPPORT_ALGORITHM = "multi-catfish-mcrl-v014-q3-support-bonus"
V014_Q3_SUPPORT_CHECKPOINT_VERSION = 1
V014_Q3_SUPPORT_ACTION_DIM = 28
V014_Q3_SUPPORT_LOCAL_FEATURE_DIM = V014_Q3_LOCAL_FEATURES
V014_Q3_SUPPORT_GLOBAL_FEATURE_DIM = V014_Q3_GLOBAL_FEATURES
V014_Q3_SUPPORT_STATE_DIM = V014_Q3_STATE_DIM
V014_Q3_SUPPORT_DEFAULT_HIDDEN_LAYERS = (100, 50, 50)
V014_Q3_SUPPORT_DEFAULT_LEARNING_RATE = 0.001
V014_Q3_SUPPORT_KAPPA_BITS = float(OPS3_KAPPA_BITS)
V014_Q3_SUPPORT_DEFAULT_THRESHOLD = 0.5


class V014Q3SupportHeadError(MCRLContractError):
    """A V0.14 Q3 support-head contract was violated."""


def q3_support_config(
    *,
    hidden_layers: tuple[int, ...] = V014_Q3_SUPPORT_DEFAULT_HIDDEN_LAYERS,
    learning_rate: float = V014_Q3_SUPPORT_DEFAULT_LEARNING_RATE,
    kappa_bits: float = V014_Q3_SUPPORT_KAPPA_BITS,
) -> EEAxisV014HeadConfig:
    """Return the fixed-width deployable Q3 support-head configuration."""

    return EEAxisV014HeadConfig(
        action_dim=V014_Q3_SUPPORT_ACTION_DIM,
        local_feature_dim=V014_Q3_SUPPORT_LOCAL_FEATURE_DIM,
        global_feature_dim=V014_Q3_SUPPORT_GLOBAL_FEATURE_DIM,
        hidden_layers=tuple(hidden_layers),
        activation="tanh",
        learning_rate=float(learning_rate),
        kappa_bits=float(kappa_bits),
        beta=0.0,
    )


# Descriptive aliases keep the module easy to discover while retaining one
# configuration type and one implementation.
deployable_q3_support_config = q3_support_config
default_q3_support_config = q3_support_config
Q3SupportHeadConfig = EEAxisV014HeadConfig


def natural_probability_from_balanced_logit(
    balanced_logit: torch.Tensor, *, positive_prior: float
) -> torch.Tensor:
    """Undo the equal-class BCE prior shift.

    With ``pos_weight=(1-p)/p``, the optimum logit is the natural logit plus
    the negative natural-prior offset.  Adding the log prior odds recovers
    the natural support probability before the frozen bonus threshold is
    applied.
    """

    prior = _finite_probability(positive_prior, field="positive_prior")
    offset = math.log(prior) - math.log1p(-prior)
    return torch.sigmoid(balanced_logit + offset)


def _finite_probability(value: object, *, field: str) -> float:
    if isinstance(value, bool):
        raise V014Q3SupportHeadError(f"{field} must lie strictly in (0,1)")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise V014Q3SupportHeadError(
            f"{field} must lie strictly in (0,1)"
        ) from error
    if not math.isfinite(result) or not 0.0 < result < 1.0:
        raise V014Q3SupportHeadError(f"{field} must lie strictly in (0,1)")
    return result


def _finite_threshold(value: object, *, field: str) -> float:
    if isinstance(value, bool):
        raise V014Q3SupportHeadError(f"{field} must be finite in [0,1]")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise V014Q3SupportHeadError(f"{field} must be finite in [0,1]") from error
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise V014Q3SupportHeadError(f"{field} must be finite in [0,1]")
    return result


def _train_seed(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("train_seed must be an integer")
    return value


def _as_int_tuple(value: object, *, field: str) -> tuple[int, ...]:
    try:
        values = tuple(value)  # type: ignore[arg-type]
    except TypeError as error:
        raise V014Q3SupportHeadError(f"{field} must be a sequence") from error
    if not values or any(
        isinstance(width, bool) or not isinstance(width, int) or width < 1
        for width in values
    ):
        raise V014Q3SupportHeadError(
            f"{field} must contain positive integer widths"
        )
    return values


def _spec_value(spec: object | None, name: str, default: object) -> object:
    if spec is None:
        return default
    return getattr(spec, name, default)


def _validate_deployable_config(config: EEAxisV014HeadConfig) -> None:
    if not isinstance(config, EEAxisV014HeadConfig):
        raise TypeError("config must be an EEAxisV014HeadConfig")
    expected = {
        "action_dim": V014_Q3_SUPPORT_ACTION_DIM,
        "local_feature_dim": V014_Q3_SUPPORT_LOCAL_FEATURE_DIM,
        "global_feature_dim": V014_Q3_SUPPORT_GLOBAL_FEATURE_DIM,
    }
    for name, value in expected.items():
        if getattr(config, name) != value:
            raise V014Q3SupportHeadError(
                f"deployable Q3 support config {name} must be {value}"
            )


def _validate_update_count(value: object, *, error_type: type[Exception]) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise error_type("update_count must be a nonnegative integer")
    return value


class Q3SupportBonusLearner:
    """One deployable Arm-A Q3 precision-calibrated bonus learner.

    ``positive_prior`` and ``support_threshold`` are supplied by the caller
    from the frozen TRAIN calibration.  They remain immutable for the life of
    the learner and are serialized with every checkpoint.  A compatibility
    ``spec``/``seed`` form is accepted so the bounded probe can be promoted
    without changing its update call, but the state width is always 287.
    """

    algorithm = V014_Q3_SUPPORT_ALGORITHM
    checkpoint_version = V014_Q3_SUPPORT_CHECKPOINT_VERSION

    def __init__(
        self,
        config: EEAxisV014HeadConfig | None = None,
        *,
        positive_prior: float,
        support_threshold: float,
        train_seed: int | None = None,
        device: str = "cpu",
        # Compatibility with the source-only probe's constructor.
        global_feature_dim: int = V014_Q3_SUPPORT_GLOBAL_FEATURE_DIM,
        spec: object | None = None,
        seed: int | None = None,
    ) -> None:
        if train_seed is not None and seed is not None and train_seed != seed:
            raise V014Q3SupportHeadError("train_seed and seed disagree")
        resolved_seed = train_seed if train_seed is not None else seed
        if resolved_seed is None:
            resolved_seed = 0
        resolved_seed = _train_seed(resolved_seed)
        if device != "cpu":
            raise V014Q3SupportHeadError(
                "V0.14 Q3 support head permits only the deterministic CPU path"
            )
        if isinstance(global_feature_dim, bool) or not isinstance(
            global_feature_dim, int
        ):
            raise V014Q3SupportHeadError("global_feature_dim must be an integer")
        if global_feature_dim != V014_Q3_SUPPORT_GLOBAL_FEATURE_DIM:
            raise V014Q3SupportHeadError(
                "deployable Q3 support head requires seven global features"
            )
        if config is None:
            hidden_layers = _as_int_tuple(
                _spec_value(
                    spec,
                    "hidden_layers",
                    V014_Q3_SUPPORT_DEFAULT_HIDDEN_LAYERS,
                ),
                field="hidden_layers",
            )
            learning_rate = float(
                _spec_value(
                    spec,
                    "learning_rate",
                    V014_Q3_SUPPORT_DEFAULT_LEARNING_RATE,
                )
            )
            kappa_bits = float(
                _spec_value(spec, "kappa_bits", V014_Q3_SUPPORT_KAPPA_BITS)
            )
            config = q3_support_config(
                hidden_layers=hidden_layers,
                learning_rate=learning_rate,
                kappa_bits=kappa_bits,
            )
        _validate_deployable_config(config)
        self.config = config
        self.train_seed = resolved_seed
        self.device = torch.device("cpu")
        self.positive_prior = _finite_probability(
            positive_prior, field="positive_prior"
        )
        self.support_threshold = _finite_threshold(
            support_threshold, field="support_threshold"
        )

        # The two networks must be independently parameterized.  Seeding once
        # before construction gives a deterministic but distinct initialization
        # to the classifier and amplitude paths.
        torch.manual_seed(self.train_seed)
        self.classifier = V014ActionSetQNetwork(config).to(self.device)
        self.positive_amplitude = V014ActionSetQNetwork(config).to(self.device)
        self.optimizer = optim.Adam(
            tuple(self.classifier.parameters())
            + tuple(self.positive_amplitude.parameters()),
            lr=float(config.learning_rate),
        )
        self.update_count = 0

    @property
    def state_dim(self) -> int:
        """The deployable state width (always 287)."""

        return int(self.config.state_dim)

    @staticmethod
    def _surface_arrays(
        states: np.ndarray,
        masks: np.ndarray,
        references: np.ndarray,
        targets_bits: np.ndarray,
        compatibility: np.ndarray,
        *,
        kappa_bits: float,
    ) -> tuple[
        np.ndarray,
        np.ndarray,
        np.ndarray,
        np.ndarray,
        np.ndarray,
        np.ndarray,
    ]:
        try:
            values = np.asarray(states, dtype=np.float32)
            legal = np.asarray(masks)
            refs = np.asarray(references)
            targets = np.asarray(targets_bits, dtype=np.float64)
            compatible = np.asarray(compatibility)
        except (TypeError, ValueError, OverflowError) as error:
            raise V014Q3SupportHeadError("support-head arrays are malformed") from error

        if values.ndim != 2 or values.shape[1] != V014_Q3_SUPPORT_STATE_DIM:
            raise V014Q3SupportHeadError(
                f"states must have shape (rows,{V014_Q3_SUPPORT_STATE_DIM})"
            )
        rows = int(values.shape[0])
        if rows < 1 or not np.all(np.isfinite(values)):
            raise V014Q3SupportHeadError("states must be nonempty and finite")
        if legal.dtype != np.bool_ or legal.shape != (
            rows,
            V014_Q3_SUPPORT_ACTION_DIM,
        ):
            raise V014Q3SupportHeadError(
                "masks must be Boolean shape (rows,28)"
            )
        if not np.all(np.any(legal, axis=1)):
            raise V014Q3SupportHeadError(
                "every support-head row needs a legal action"
            )
        if (
            refs.shape != (rows,)
            or refs.dtype == np.bool_
            or not np.issubdtype(refs.dtype, np.integer)
            or np.any(refs < 0)
            or np.any(refs >= V014_Q3_SUPPORT_ACTION_DIM)
            or not np.all(legal[np.arange(rows), refs])
        ):
            raise V014Q3SupportHeadError(
                "reference actions must be legal integer action indices"
            )
        if targets.shape != (rows, V014_Q3_SUPPORT_ACTION_DIM) or not np.all(
            np.isfinite(targets)
        ):
            raise V014Q3SupportHeadError(
                "target_surfaces_bits must be finite shape (rows,28)"
            )
        if compatible.dtype != np.bool_ or compatible.shape != targets.shape:
            raise V014Q3SupportHeadError(
                "compatibility must be Boolean shape (rows,28)"
            )
        if not math.isfinite(float(kappa_bits)) or float(kappa_bits) <= 0.0:
            raise V014Q3SupportHeadError("kappa_bits must be finite and positive")

        comparisons = np.array(legal, dtype=np.bool_, copy=True)
        comparisons[np.arange(rows), refs] = False
        if not np.any(comparisons):
            raise V014Q3SupportHeadError(
                "support-head batch contains no non-reference comparison"
            )
        target_delta = targets - targets[np.arange(rows), refs][:, None]
        support = comparisons & compatible & (target_delta > 0.0)
        return (
            np.ascontiguousarray(values),
            np.ascontiguousarray(legal),
            np.ascontiguousarray(refs, dtype=np.int64),
            np.ascontiguousarray(targets),
            np.ascontiguousarray(compatible),
            np.ascontiguousarray(support),
        )

    def _arrays_for_update(
        self,
        states: np.ndarray,
        masks: np.ndarray,
        references: np.ndarray,
        targets_bits: np.ndarray,
        compatibility: np.ndarray,
    ) -> tuple[torch.Tensor, ...]:
        values, legal, refs, targets, _compatible, support = self._surface_arrays(
            states,
            masks,
            references,
            targets_bits,
            compatibility,
            kappa_bits=float(self.config.kappa_bits),
        )
        target_delta = targets / float(self.config.kappa_bits)
        target_delta = target_delta - target_delta[
            np.arange(target_delta.shape[0]), refs
        ][:, None]
        comparisons = np.array(legal, dtype=np.bool_, copy=True)
        comparisons[np.arange(comparisons.shape[0]), refs] = False
        return (
            torch.as_tensor(values, dtype=torch.float32, device=self.device),
            torch.as_tensor(legal, dtype=torch.bool, device=self.device),
            torch.as_tensor(refs, dtype=torch.int64, device=self.device),
            torch.as_tensor(target_delta, dtype=torch.float32, device=self.device),
            torch.as_tensor(comparisons, dtype=torch.bool, device=self.device),
            torch.as_tensor(support, dtype=torch.bool, device=self.device),
        )

    def update(
        self,
        states: np.ndarray,
        masks: np.ndarray,
        references: np.ndarray,
        targets_bits: np.ndarray,
        compatibility: np.ndarray,
    ) -> dict[str, float | int]:
        """Perform one deterministic Adam update on complete action surfaces."""

        (
            values,
            legal,
            refs,
            target_delta,
            comparisons,
            support,
        ) = self._arrays_for_update(
            states, masks, references, targets_bits, compatibility
        )
        self.classifier.train()
        self.positive_amplitude.train()
        logits = self.classifier(values, legal)
        raw_amplitude = self.positive_amplitude(values, legal)
        labels = support.to(dtype=torch.float32)
        positive_weight = (1.0 - self.positive_prior) / self.positive_prior
        bce = F.binary_cross_entropy_with_logits(
            logits[comparisons],
            labels[comparisons],
            pos_weight=torch.tensor(
                positive_weight, dtype=torch.float32, device=self.device
            ),
        )
        if bool(torch.any(support)):
            amplitude = F.softplus(raw_amplitude[support])
            amplitude_mse = torch.mean(
                (amplitude - target_delta[support]).square()
            )
        else:
            # Keep a zero-gradient term attached to the amplitude path so the
            # optimizer state remains well-defined on support-free minibatches.
            amplitude_mse = raw_amplitude.sum() * 0.0
        loss = bce + amplitude_mse
        self.optimizer.zero_grad(set_to_none=True)
        loss.backward()
        assert_finite_loss(loss, objective=3)
        assert_finite_gradients(
            tuple(self.classifier.parameters())
            + tuple(self.positive_amplitude.parameters()),
            objective=3,
        )
        self.optimizer.step()
        assert_finite_parameters((self.classifier, self.positive_amplitude))
        self.update_count += 1
        return {
            "batch_size": int(values.shape[0]),
            "comparison_count": int(torch.count_nonzero(comparisons)),
            "support_count": int(torch.count_nonzero(support)),
            "loss": float(loss.detach().cpu()),
            "balanced_bce": float(bce.detach().cpu()),
            "positive_amplitude_mse": float(amplitude_mse.detach().cpu()),
            "update_count": self.update_count,
        }

    def _inference_arrays(
        self,
        states: np.ndarray,
        masks: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        try:
            values = np.asarray(states, dtype=np.float32)
            legal = np.asarray(masks)
        except (TypeError, ValueError, OverflowError) as error:
            raise V014Q3SupportHeadError(
                "support-head inference arrays are malformed"
            ) from error
        if values.ndim != 2 or values.shape[1] != V014_Q3_SUPPORT_STATE_DIM:
            raise V014Q3SupportHeadError(
                f"states must have shape (rows,{V014_Q3_SUPPORT_STATE_DIM})"
            )
        rows = int(values.shape[0])
        if rows < 1 or not np.all(np.isfinite(values)):
            raise V014Q3SupportHeadError("states must be nonempty and finite")
        if legal.dtype != np.bool_ or legal.shape != (
            rows,
            V014_Q3_SUPPORT_ACTION_DIM,
        ):
            raise V014Q3SupportHeadError("masks must be Boolean shape (rows,28)")
        if not np.all(np.any(legal, axis=1)):
            raise V014Q3SupportHeadError(
                "every support-head row needs a legal action"
            )
        return (
            np.ascontiguousarray(values),
            np.ascontiguousarray(legal),
        )

    def predict(
        self,
        states: np.ndarray,
        masks: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return natural support probability, amplitude, and nonnegative bonus.

        The bonus is
        ``I[p >= support_threshold] * p * softplus(amplitude)`` in kappa
        normalized units.  References are deliberately absent from this
        inference interface: they are a label-construction input only.
        Illegal slots are scored for shape/equivariance consistency but must
        be excluded by the caller's deployment mask.
        """

        values, legal = self._inference_arrays(states, masks)
        self.classifier.eval()
        self.positive_amplitude.eval()
        with torch.no_grad():
            state_tensor = torch.as_tensor(
                values, dtype=torch.float32, device=self.device
            )
            mask_tensor = torch.as_tensor(
                legal, dtype=torch.bool, device=self.device
            )
            logits = self.classifier(state_tensor, mask_tensor)
            probability = natural_probability_from_balanced_logit(
                logits, positive_prior=self.positive_prior
            )
            positive = F.softplus(
                self.positive_amplitude(state_tensor, mask_tensor)
            )
            bonus = probability * positive
            bonus = torch.where(
                probability >= float(self.support_threshold),
                bonus,
                torch.zeros_like(bonus),
            )
        probability_np = np.asarray(probability.cpu().numpy(), dtype=np.float32)
        positive_np = np.asarray(positive.cpu().numpy(), dtype=np.float32)
        bonus_np = np.asarray(bonus.cpu().numpy(), dtype=np.float32)
        return probability_np, positive_np, bonus_np

    def q_values(
        self,
        states: np.ndarray,
        masks: np.ndarray,
    ) -> np.ndarray:
        """Return thresholded nonnegative Q3 support bonuses."""

        return self.predict(states, masks)[2]

    def support_probabilities(
        self,
        states: np.ndarray,
        masks: np.ndarray,
    ) -> np.ndarray:
        """Return the natural-prior-corrected support probabilities."""

        return self.predict(states, masks)[0]

    def positive_amplitudes(
        self,
        states: np.ndarray,
        masks: np.ndarray,
    ) -> np.ndarray:
        """Return the positive supported-amplitude prediction in kappa units."""

        return self.predict(states, masks)[1]

    def select_greedy_actions(
        self,
        states: np.ndarray,
        masks: np.ndarray,
    ) -> np.ndarray:
        """Select the legal action with maximum support bonus."""

        legal = np.asarray(masks)
        scores = self.q_values(states, legal)
        if legal.dtype != np.bool_ or legal.shape != scores.shape:
            raise V014Q3SupportHeadError(
                "masks must be Boolean and match the Q3 surface shape"
            )
        actions = np.full(scores.shape[0], NO_OP_ACTION, dtype=np.int64)
        eligible = np.any(legal, axis=1)
        actions[eligible] = np.argmax(
            np.where(legal[eligible], scores[eligible], -np.inf), axis=1
        )
        return actions

    def checkpoint_state(self, *, update_count: int | None = None) -> dict[str, Any]:
        """Serialize deterministic learner state and frozen calibration.

        Every tensor payload is deep-copied so a later optimizer step cannot
        mutate an already-created checkpoint in place.
        """

        if update_count is None:
            count = self.update_count
        else:
            count = _validate_update_count(
                update_count, error_type=V014Q3SupportHeadError
            )
        return {
            "algorithm": self.algorithm,
            "format_version": self.checkpoint_version,
            "config": asdict(self.config),
            "train_seed": self.train_seed,
            "positive_prior": self.positive_prior,
            "support_threshold": self.support_threshold,
            "update_count": count,
            "classifier": deepcopy(self.classifier.state_dict()),
            "positive_amplitude": deepcopy(self.positive_amplitude.state_dict()),
            "optimizer": deepcopy(self.optimizer.state_dict()),
        }

    def load_checkpoint_state(self, payload: Mapping[str, Any]) -> int:
        """Load a checkpoint only when architecture and calibration match."""

        if not isinstance(payload, Mapping):
            raise V014Q3SupportHeadError("support-head checkpoint must be a mapping")
        if payload.get("algorithm") != self.algorithm:
            raise MCRLContractError(
                "checkpoint is not a V0.14 Q3 support-head checkpoint"
            )
        if payload.get("format_version") != self.checkpoint_version:
            raise MCRLContractError(
                "unsupported V0.14 Q3 support-head checkpoint version"
            )
        if payload.get("config") != asdict(self.config):
            raise MCRLContractError(
                "V0.14 Q3 support-head checkpoint config mismatch"
            )
        if payload.get("train_seed") != self.train_seed:
            raise MCRLContractError(
                "V0.14 Q3 support-head checkpoint train_seed mismatch"
            )
        try:
            prior = _finite_probability(
                payload["positive_prior"], field="positive_prior"
            )
            threshold = _finite_threshold(
                payload["support_threshold"], field="support_threshold"
            )
        except (KeyError, V014Q3SupportHeadError) as error:
            raise MCRLContractError(
                "malformed V0.14 Q3 support-head calibration"
            ) from error
        if prior.hex() != self.positive_prior.hex():
            raise MCRLContractError(
                "V0.14 Q3 support-head positive_prior mismatch"
            )
        if threshold.hex() != self.support_threshold.hex():
            raise MCRLContractError(
                "V0.14 Q3 support-head support_threshold mismatch"
            )
        try:
            count = _validate_update_count(
                payload["update_count"], error_type=MCRLContractError
            )
        except KeyError as error:
            raise MCRLContractError(
                "malformed V0.14 Q3 support-head update_count"
            ) from error
        classifier = payload.get("classifier")
        amplitude = payload.get("positive_amplitude")
        optimizer = payload.get("optimizer")
        if not isinstance(classifier, Mapping) or not isinstance(
            amplitude, Mapping
        ) or not isinstance(optimizer, Mapping):
            raise MCRLContractError(
                "malformed V0.14 Q3 support-head checkpoint payload"
            )
        try:
            # Loading from a private copy also prevents an optimizer
            # implementation from retaining or mutating the caller's receipt.
            self.classifier.load_state_dict(deepcopy(classifier), strict=True)
            self.positive_amplitude.load_state_dict(
                deepcopy(amplitude), strict=True
            )
            self.optimizer.load_state_dict(deepcopy(optimizer))
        except (KeyError, TypeError, ValueError, RuntimeError) as error:
            raise MCRLContractError(
                "malformed V0.14 Q3 support-head checkpoint"
            ) from error
        assert_finite_parameters((self.classifier, self.positive_amplitude))
        self.update_count = count
        return count


# Names used by adjacent V0.14 code remain available without creating a
# second implementation.  The old class spelling is only an import alias;
# its inference contract is the nonnegative support bonus above.
Q3SupportMixtureLearner = Q3SupportBonusLearner
EEAxisV014Q3SupportLearner = Q3SupportBonusLearner
EEAxisV014Q3SupportHead = Q3SupportBonusLearner


__all__ = [
    "EEAxisV014HeadConfig",
    "EEAxisV014Q3SupportHead",
    "EEAxisV014Q3SupportLearner",
    "Q3SupportHeadConfig",
    "Q3SupportBonusLearner",
    "Q3SupportMixtureLearner",
    "V014ActionSetQNetwork",
    "V014Q3SupportHeadError",
    "V014_Q3_SUPPORT_ACTION_DIM",
    "V014_Q3_SUPPORT_ALGORITHM",
    "V014_Q3_SUPPORT_CHECKPOINT_VERSION",
    "V014_Q3_SUPPORT_DEFAULT_HIDDEN_LAYERS",
    "V014_Q3_SUPPORT_DEFAULT_LEARNING_RATE",
    "V014_Q3_SUPPORT_DEFAULT_THRESHOLD",
    "V014_Q3_SUPPORT_GLOBAL_FEATURE_DIM",
    "V014_Q3_SUPPORT_KAPPA_BITS",
    "V014_Q3_SUPPORT_LOCAL_FEATURE_DIM",
    "V014_Q3_SUPPORT_STATE_DIM",
    "default_q3_support_config",
    "deployable_q3_support_config",
    "natural_probability_from_balanced_logit",
    "q3_support_config",
]
