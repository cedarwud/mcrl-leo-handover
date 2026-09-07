"""Minimal three-route update schedule for Multi-Catfish MCRL V0.3.

The data adapters own route admission.  This module only verifies that one
cycle contains exactly C1/D^o, C2/D^t, and C3/D^o batches, then dispatches
each batch to its corresponding independent Q function.  It does not copy a
target across routes or infer a missing Catfish source.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from ..algorithms.ee_axis_pairwise import (
    EEAxisPairwiseTrainer,
    ROUTE_NAMES,
)
from ..errors import MCRLContractError
from .ee_axis_opening_pairs import (
    EEAxisOpeningRouteBatch,
    update_opening_route,
)
from .ee_axis_state import EE_AXIS_STATE_DIM
from .ee_axis_temporal_pairs import EEAxisTemporalRouteBatch


class EEAxisTrainingScheduleError(MCRLContractError):
    """A proposed three-route update cycle violates route isolation."""


@dataclass(frozen=True)
class EEAxisThreeRouteBatches:
    """Exactly one verified batch for every current Catfish route."""

    c1: EEAxisOpeningRouteBatch
    c2: EEAxisTemporalRouteBatch
    c3: EEAxisOpeningRouteBatch

    def verify(self, trainer: EEAxisPairwiseTrainer) -> None:
        if not isinstance(trainer, EEAxisPairwiseTrainer):
            raise EEAxisTrainingScheduleError(
                "trainer must be EEAxisPairwiseTrainer"
            )
        if not isinstance(self.c1, EEAxisOpeningRouteBatch) or self.c1.route != "C1":
            raise EEAxisTrainingScheduleError("c1 must be a C1 opening batch")
        if not isinstance(self.c2, EEAxisTemporalRouteBatch) or self.c2.route != "C2":
            raise EEAxisTrainingScheduleError("c2 must be a C2 temporal batch")
        if not isinstance(self.c3, EEAxisOpeningRouteBatch) or self.c3.route != "C3":
            raise EEAxisTrainingScheduleError("c3 must be a C3 opening batch")
        try:
            self.c1.verify()
            self.c2.verify()
            self.c3.verify()
        except MCRLContractError as error:
            raise EEAxisTrainingScheduleError(str(error)) from error
        if trainer.config.state_dim != EE_AXIS_STATE_DIM:
            raise EEAxisTrainingScheduleError(
                f"trainer must use the current {EE_AXIS_STATE_DIM}-D state"
            )
        for route, batch in (
            ("C1", self.c1.pair_batch),
            ("C2", self.c2.pair_batch),
            ("C3", self.c3.pair_batch),
        ):
            try:
                batch.validate(
                    state_dim=trainer.config.state_dim,
                    action_dim=trainer.config.action_dim,
                )
            except (MCRLContractError, TypeError, ValueError) as error:
                raise EEAxisTrainingScheduleError(
                    f"{route} batch is incompatible with the trainer: {error}"
                ) from error

    def batch_for(self, route: str) -> EEAxisOpeningRouteBatch | EEAxisTemporalRouteBatch:
        if route == "C1":
            return self.c1
        if route == "C2":
            return self.c2
        if route == "C3":
            return self.c3
        raise EEAxisTrainingScheduleError(f"unknown route {route!r}")


def update_three_route_cycle(
    trainer: EEAxisPairwiseTrainer,
    batches: EEAxisThreeRouteBatches,
    *,
    order: tuple[str, str, str] = ROUTE_NAMES,
) -> tuple[Mapping[str, float | int | str], ...]:
    """Run one explicit diagonal update for C1, C2, and C3.

    ``order`` may permute execution for a deterministic smoke, but it must be
    an exact permutation: no route can be duplicated or silently omitted.
    """

    if tuple(sorted(order)) != tuple(sorted(ROUTE_NAMES)) or len(order) != 3:
        raise EEAxisTrainingScheduleError(
            "update order must contain C1, C2, and C3 exactly once"
        )
    batches.verify(trainer)
    receipts: list[Mapping[str, float | int | str]] = []
    for route in order:
        batch = batches.batch_for(route)
        if route in ("C1", "C3"):
            if not isinstance(batch, EEAxisOpeningRouteBatch):
                raise EEAxisTrainingScheduleError(
                    f"{route} dispatch received a non-opening batch"
                )
            receipt = update_opening_route(trainer, batch)
        else:
            if not isinstance(batch, EEAxisTemporalRouteBatch):
                raise EEAxisTrainingScheduleError(
                    "C2 dispatch received a non-temporal batch"
                )
            batch.verify()
            receipt = trainer.update_route("C2", batch.pair_batch)
        if receipt.get("route") != route:
            raise EEAxisTrainingScheduleError("trainer receipt changed route")
        receipts.append(receipt)
    return tuple(receipts)


__all__ = [
    "EEAxisThreeRouteBatches",
    "EEAxisTrainingScheduleError",
    "update_three_route_cycle",
]
