"""Isolated V0.23 heterogeneous three-route learner seam.

The current production model owns the three heterogeneous heads and their
optimizers.  This scratch-only adapter adds the missing update boundary:

* C1 uses the existing raw-bit :class:`EEAxisPairBatch` action-shared
  objective; C2 uses the separately typed already-normalized 448-D OPS-3
  batch and the existing V0.14 action-set head.
* C3 uses the existing structured sampled batch and anchor surfaces, then
  delegates the update to the current ``lcsrs_c3_training_step``.

No source loader, simulator, schedule, target construction, or checkpoint
format is introduced here.  Checkpoint operations are direct calls to the
current ``EEAxisLCSRSThreeRoute`` methods.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import torch

from mcrl.algorithms.ee_axis_action_shared import (
    ActionSharedQNetwork,
    EEAxisActionSharedConfig,
)
from mcrl.algorithms.ee_axis_v014_head import (
    EEAxisV014HeadConfig,
    EEAxisV014NormalizedPairBatch,
    V014ActionSetQNetwork,
)
from mcrl.algorithms.ee_axis_lcsrs_c3_head import (
    LCSRSC3HeadConfig,
    LCSRSC3QNetwork,
)
from mcrl.algorithms.ee_axis_lcsrs_three_route import (
    EEAxisLCSRSThreeRoute,
    LCSRSThreeRouteConfig,
)
from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch
from mcrl.errors import MCRLContractError
from mcrl.runtime.ee_axis_lcsrs_c3_dataset import LCSRSAnchorSurface
from mcrl.runtime.ee_axis_lcsrs_c3_learner import (
    LCSRSC3SampledBatch,
    lcsrs_c3_training_step,
)
from mcrl.runtime.finiteness import (
    assert_finite_gradients,
    assert_finite_loss,
    assert_finite_parameters,
)


PAIRWISE_ROUTES = ("C1", "C2")
ALL_ROUTES = ("C1", "C2", "C3")


class V023HeterogeneousTrainerError(MCRLContractError):
    """The isolated V0.23 learner seam received an invalid contract."""


class V023HeterogeneousTrainer:
    """Update one current heterogeneous route at a time.

    ``model`` remains the owner of all trainable state.  In particular, this
    class does not create replacement heads or optimizers and does not add a
    second checkpoint representation.
    """

    def __init__(self, model: EEAxisLCSRSThreeRoute) -> None:
        self._validate_model(model)
        self.model = model
        self._validate_parameter_and_optimizer_isolation()

    @staticmethod
    def _validate_model(model: object) -> None:
        if not isinstance(model, EEAxisLCSRSThreeRoute):
            raise TypeError(
                "model must be the current EEAxisLCSRSThreeRoute"
            )
        if not isinstance(model.config, LCSRSThreeRouteConfig):
            raise V023HeterogeneousTrainerError(
                "current model must carry LCSRSThreeRouteConfig"
            )
        if not isinstance(model.config.q1, EEAxisActionSharedConfig):
            raise V023HeterogeneousTrainerError(
                "current model is missing its action-shared Q1 config"
            )
        if not isinstance(model.config.q2, EEAxisV014HeadConfig):
            raise V023HeterogeneousTrainerError(
                "current model is missing its frozen V0.14 OPS-3 Q2 config"
            )
        if not isinstance(model.config.q3, LCSRSC3HeadConfig):
            raise V023HeterogeneousTrainerError(
                "current model is missing its frozen structured Q3 config"
            )
        if len(model.q_networks) != 3 or len(model.optimizers) != 3:
            raise V023HeterogeneousTrainerError(
                "current model must contain exactly three heads and optimizers"
            )
        if (
            model.q_networks[0] is not model.q1
            or model.q_networks[1] is not model.q2
            or model.q_networks[2] is not model.q3
        ):
            raise V023HeterogeneousTrainerError(
                "current model route properties disagree with q_networks"
            )
        if not isinstance(model.q1, ActionSharedQNetwork):
            raise V023HeterogeneousTrainerError(
                "current Q1 head must be an action-shared network"
            )
        if not isinstance(model.q2, V014ActionSetQNetwork):
            raise V023HeterogeneousTrainerError(
                "current Q2 head must be the V0.14 action-set network"
            )
        if not isinstance(model.q3, LCSRSC3QNetwork):
            raise V023HeterogeneousTrainerError(
                "current Q3 head must be the structured LC-SRS network"
            )

    def _validate_parameter_and_optimizer_isolation(self) -> None:
        network_parameter_ids = [
            {id(parameter) for parameter in network.parameters()}
            for network in self.model.q_networks
        ]
        if any(
            network_parameter_ids[left] & network_parameter_ids[right]
            for left in range(3)
            for right in range(left)
        ):
            raise V023HeterogeneousTrainerError(
                "current route heads share trainable parameters"
            )

        for index, (network, optimizer) in enumerate(
            zip(self.model.q_networks, self.model.optimizers, strict=True)
        ):
            if not isinstance(optimizer, torch.optim.Optimizer):
                raise V023HeterogeneousTrainerError(
                    f"optimizer {index} is not a torch optimizer"
                )
            expected = network_parameter_ids[index]
            actual_parameters = [
                parameter
                for group in optimizer.param_groups
                for parameter in group["params"]
            ]
            if len(actual_parameters) != len(expected) or {
                id(parameter) for parameter in actual_parameters
            } != expected:
                raise V023HeterogeneousTrainerError(
                    f"optimizer {index} is not bound exactly to route {index}"
                )

        for index, expected_rate in (
            (0, float(self.model.config.q1.learning_rate)),
            (1, float(self.model.config.q2.learning_rate)),
        ):
            groups = self.model.optimizers[index].param_groups
            if len(groups) != 1 or float(groups[0]["lr"]) != expected_rate:
                raise V023HeterogeneousTrainerError(
                    f"optimizer {index} learning rate drifts from route config"
                )

        q3_groups = self.model.optimizers[2].param_groups
        if len(q3_groups) != 1:
            raise V023HeterogeneousTrainerError(
                "optimizer 2 must have one frozen C3 parameter group"
            )
        q3_group = q3_groups[0]
        q3_config = self.model.config
        if (
            float(q3_group["lr"]) != float(q3_config.q3_learning_rate)
            or tuple(q3_group["betas"]) != tuple(q3_config.q3_betas)
            or float(q3_group["eps"]) != float(q3_config.q3_epsilon)
            or float(q3_group["weight_decay"]) != float(q3_config.q3_weight_decay)
        ):
            raise V023HeterogeneousTrainerError(
                "optimizer 2 drifts from the frozen C3 model config"
            )

    def _clear_all_gradients(self) -> None:
        for network in self.model.q_networks:
            for parameter in network.parameters():
                parameter.grad = None

    def _parameter_snapshot(self) -> tuple[tuple[torch.Tensor, ...], ...]:
        return tuple(
            tuple(parameter.detach().clone() for parameter in network.parameters())
            for network in self.model.q_networks
        )

    def _assert_no_cross_route_gradients(self, route_index: int) -> None:
        for index, network in enumerate(self.model.q_networks):
            if index == route_index:
                continue
            if any(parameter.grad is not None for parameter in network.parameters()):
                raise V023HeterogeneousTrainerError(
                    f"route {route_index} produced a gradient on route {index}"
                )

    def _assert_only_route_changed(
        self,
        before: tuple[tuple[torch.Tensor, ...], ...],
        route_index: int,
    ) -> None:
        for index, (old_network, network) in enumerate(
            zip(before, self.model.q_networks, strict=True)
        ):
            if index == route_index:
                continue
            for parameter_index, (old, current) in enumerate(
                zip(old_network, network.parameters(), strict=True)
            ):
                if not torch.equal(old, current.detach()):
                    raise V023HeterogeneousTrainerError(
                        "route update changed a non-target parameter "
                        f"(route={index}, parameter={parameter_index})"
                    )

    @staticmethod
    def _validate_pair_batch(
        batch: object,
        *,
        config: EEAxisActionSharedConfig,
    ) -> EEAxisPairBatch:
        if not isinstance(batch, EEAxisPairBatch):
            raise TypeError("C1 update requires an EEAxisPairBatch")
        batch.validate(state_dim=config.state_dim, action_dim=config.action_dim)
        if np.asarray(batch.states).shape[0] < 1:
            raise V023HeterogeneousTrainerError(
                "C1 action-shared batch must contain at least one row"
            )
        return batch

    def _update_c1_pairwise(
        self, batch: EEAxisPairBatch
    ) -> dict[str, float | int | str]:
        config = self.model.config.q1
        self._validate_pair_batch(batch, config=config)
        route_index = 0
        network = self.model.q1
        optimizer = self.model.optimizers[0]
        before = self._parameter_snapshot()
        self._clear_all_gradients()

        states = torch.tensor(
            np.asarray(batch.states, dtype=np.float32),
            dtype=torch.float32,
            device=self.model.device,
        )
        reference = torch.tensor(
            np.asarray(batch.reference_actions, dtype=np.int64),
            dtype=torch.int64,
            device=self.model.device,
        )
        candidate = torch.tensor(
            np.asarray(batch.candidate_actions, dtype=np.int64),
            dtype=torch.int64,
            device=self.model.device,
        )
        normalized_target = torch.tensor(
            np.asarray(batch.target_surplus_bits, dtype=np.float32)
            / float(config.kappa_bits),
            dtype=torch.float32,
            device=self.model.device,
        )

        # This is the existing action-shared pairwise objective: there is no
        # next-state value and therefore no bootstrap term.
        q_surface = network(states)
        q_reference = q_surface.gather(1, reference[:, None]).squeeze(1)
        q_candidate = q_surface.gather(1, candidate[:, None]).squeeze(1)
        residual = q_candidate - q_reference - normalized_target
        pair_mse = torch.mean(residual.square())
        gauge_mse = torch.mean(q_reference.square())
        loss = float(config.loss_weights[route_index]) * (
            pair_mse + float(config.beta) * gauge_mse
        )

        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        assert_finite_loss(loss, objective=route_index + 1)
        self._assert_no_cross_route_gradients(route_index)
        assert_finite_gradients(network.parameters(), objective=route_index + 1)
        optimizer.step()
        assert_finite_parameters(self.model.q_networks)
        self._assert_no_cross_route_gradients(route_index)
        self._assert_only_route_changed(before, route_index)
        return {
            "route": "C1",
            "batch_size": int(states.shape[0]),
            "loss": float(loss.detach().cpu()),
            "pair_mse": float(pair_mse.detach().cpu()),
            "gauge_mse": float(gauge_mse.detach().cpu()),
        }

    def update_c1(self, batch: EEAxisPairBatch) -> dict[str, float | int | str]:
        """Apply one exact action-shared pairwise update to ``model.q1``."""

        return self._update_c1_pairwise(batch)

    def update_c2(
        self, batch: EEAxisV014NormalizedPairBatch
    ) -> dict[str, float | int | str]:
        """Update Q2 from a typed target already normalized by kappa.

        No raw-bit conversion is available on this path: OPS-3's
        ``target_delta`` is already in the V0.14 learner unit.
        """

        if not isinstance(batch, EEAxisV014NormalizedPairBatch):
            raise TypeError("C2 update requires an EEAxisV014NormalizedPairBatch")
        config = self.model.config.q2
        batch.validate(config=config)
        route_index = 1
        before = self._parameter_snapshot()
        self._clear_all_gradients()
        states = torch.tensor(batch.states, dtype=torch.float32, device=self.model.device)
        reference = torch.tensor(batch.reference_actions, dtype=torch.int64, device=self.model.device)
        candidate = torch.tensor(batch.candidate_actions, dtype=torch.int64, device=self.model.device)
        action_masks = torch.tensor(batch.action_masks, dtype=torch.bool, device=self.model.device)
        already_normalized_target = torch.tensor(
            batch.normalized_target_deltas, dtype=torch.float32, device=self.model.device
        )
        surface = self.model.q2(states, action_masks)
        rows = torch.arange(states.shape[0], device=self.model.device)
        q_reference = surface[rows, reference]
        q_candidate = surface[rows, candidate]
        residual = q_candidate - q_reference - already_normalized_target
        pair_mse = torch.mean(residual.square())
        gauge_mse = torch.mean(q_reference.square())
        loss = pair_mse + float(config.beta) * gauge_mse
        optimizer = self.model.optimizers[route_index]
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        assert_finite_loss(loss, objective=route_index + 1)
        self._assert_no_cross_route_gradients(route_index)
        assert_finite_gradients(self.model.q2.parameters(), objective=route_index + 1)
        optimizer.step()
        assert_finite_parameters(self.model.q_networks)
        self._assert_no_cross_route_gradients(route_index)
        self._assert_only_route_changed(before, route_index)
        return {
            "route": "C2",
            "batch_size": int(states.shape[0]),
            "loss": float(loss.detach().cpu()),
            "pair_mse": float(pair_mse.detach().cpu()),
            "gauge_mse": float(gauge_mse.detach().cpu()),
        }

    @staticmethod
    def _validate_c3_inputs(
        batch: object,
        surfaces: object,
    ) -> tuple[LCSRSC3SampledBatch, tuple[LCSRSAnchorSurface, ...]]:
        if not isinstance(batch, LCSRSC3SampledBatch):
            raise TypeError("C3 update requires an LCSRSC3SampledBatch")
        if isinstance(surfaces, (str, bytes, Mapping)):
            raise TypeError("C3 surfaces must be a sequence of LCSRSAnchorSurface")
        try:
            source = tuple(surfaces)  # type: ignore[arg-type]
        except TypeError as error:
            raise TypeError(
                "C3 surfaces must be a sequence of LCSRSAnchorSurface"
            ) from error
        if not source:
            raise V023HeterogeneousTrainerError(
                "C3 update requires at least one LCSRSAnchorSurface"
            )
        for index, surface in enumerate(source):
            if not isinstance(surface, LCSRSAnchorSurface):
                raise TypeError(
                    "C3 surface "
                    f"{index} is not an LCSRSAnchorSurface"
                )
            surface.view.verify()
        return batch, source

    def update_c3(
        self,
        batch: LCSRSC3SampledBatch,
        surfaces: Sequence[LCSRSAnchorSurface],
    ) -> dict[str, float | int | str]:
        """Delegate one structured C3 update to the current implementation."""

        checked_batch, source = self._validate_c3_inputs(batch, surfaces)
        before = self._parameter_snapshot()
        self._clear_all_gradients()
        loss = lcsrs_c3_training_step(
            self.model.q3,
            self.model.optimizers[2],
            source,
            checked_batch,
            device=self.model.device,
        )
        if not np.isfinite(float(loss)):
            raise V023HeterogeneousTrainerError("C3 update returned a non-finite loss")
        assert_finite_parameters(self.model.q_networks)
        self._assert_no_cross_route_gradients(2)
        self._assert_only_route_changed(before, 2)
        return {
            "route": "C3",
            "batch_size": checked_batch.rows,
            "loss": float(loss),
        }

    def update_route(
        self,
        route: str,
        batch: EEAxisPairBatch | EEAxisV014NormalizedPairBatch | LCSRSC3SampledBatch,
        *,
        surfaces: Sequence[LCSRSAnchorSurface] | None = None,
    ) -> dict[str, float | int | str]:
        """Dispatch one explicitly typed route update.

        C1/C2 do not accept structured surfaces.  C3 requires them explicitly;
        no source or sampler is inferred here.
        """

        if route == "C1":
            if surfaces is not None:
                raise V023HeterogeneousTrainerError(
                    "C1 does not accept C3 surfaces"
                )
            return self.update_c1(batch)  # type: ignore[arg-type]
        if route == "C2":
            if surfaces is not None:
                raise V023HeterogeneousTrainerError(
                    "C2 does not accept C3 surfaces"
                )
            return self.update_c2(batch)  # type: ignore[arg-type]
        if route == "C3":
            if surfaces is None:
                raise V023HeterogeneousTrainerError(
                    "C3 route update requires explicit LC-SRS surfaces"
                )
            return self.update_c3(batch, surfaces)  # type: ignore[arg-type]
        raise ValueError(f"route must be one of {ALL_ROUTES}, got {route!r}")

    def checkpoint_state(self, *, update_count: int) -> dict[str, Any]:
        """Use the current three-route checkpoint representation unchanged."""

        return self.model.checkpoint_state(update_count=update_count)

    def load_checkpoint_state(self, state: Mapping[str, Any]) -> int:
        """Resume through the current model's authenticated loader unchanged."""

        if not isinstance(state, Mapping):
            raise TypeError("checkpoint state must be a mapping")
        update_count = self.model.load_checkpoint_state(state)
        self._validate_parameter_and_optimizer_isolation()
        self._clear_all_gradients()
        return update_count


__all__ = [
    "ALL_ROUTES",
    "PAIRWISE_ROUTES",
    "V023HeterogeneousTrainer",
    "V023HeterogeneousTrainerError",
]
