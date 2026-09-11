"""Fail-loud finiteness battery for the training step.

New file (W-16).  Ports the *semantics* of the source project's guards at
``family_b_r3/common_trainer.py:516-517, 520-525, 529-530`` (SDD §3.7 P-3)
into a reusable helper so every update path — the live ``update()`` and any
later batch path added by W-08 — shares one implementation.

SDD §6 G-11: a non-finite loss, gradient, or parameter aborts training.
Silently skipping the offending objective is *not* compliant — it keeps
training and leaves the §6 G-3 collapse metrics to be computed on a NaN
policy.  The source project's dormant batch-update twin did exactly that;
W-08 deleted it rather than repair it, so ``update()`` is now the only
update path and this battery is the only finiteness policy.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import torch

from ..errors import NonFiniteTrainingError


def assert_finite_loss(loss: torch.Tensor, *, objective: int) -> None:
    """Raise when the TD loss is not finite (common_trainer.py:516-517)."""
    if not bool(torch.isfinite(loss)):
        raise NonFiniteTrainingError(
            f"nonfinite TD loss for objective {objective}"
        )


def assert_finite_gradients(
    parameters: Iterable[torch.nn.Parameter],
    *,
    objective: int,
) -> None:
    """Raise when any populated gradient is not finite (…:520-525)."""
    for index, parameter in enumerate(parameters):
        grad = parameter.grad
        if grad is not None and not bool(torch.isfinite(grad).all()):
            raise NonFiniteTrainingError(
                f"nonfinite gradient for objective {objective}, "
                f"parameter index {index}"
            )


def all_parameters_finite(networks: Sequence[torch.nn.Module]) -> bool:
    """Mirror of ``common_trainer.py:173`` ``_all_finite_networks``."""
    return all(
        bool(torch.isfinite(parameter.detach()).all())
        for network in networks
        for parameter in network.parameters()
    )


def assert_finite_parameters(networks: Sequence[torch.nn.Module]) -> None:
    """Raise when any online-network parameter is not finite (…:529-530)."""
    if not all_parameters_finite(networks):
        raise NonFiniteTrainingError("nonfinite online-network parameter")
