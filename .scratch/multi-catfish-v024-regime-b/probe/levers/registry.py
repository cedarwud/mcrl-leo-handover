"""Priority-ordered registry and no-lever regression seam."""

from __future__ import annotations

from typing import Mapping

from .common import LeverDefinition, LeverError
from .lever_l1_sum_power import DEFINITION as L1
from .lever_l12 import DEFINITION as L12
from .lever_l2_pa_curve import DEFINITION as L2
from .lever_l4_handover_energy import DEFINITION as L4


LEVER_PRIORITY = ("L1", "L12", "L2", "L4")  # Provenance: Astra matrix priority declaration.
LEVERS: Mapping[str, LeverDefinition] = {row.lever_id: row for row in (L1, L12, L2, L4)}  # Provenance: ASTRA_TRACKB_MULTI shared-runner intersection.

if tuple(LEVERS) != LEVER_PRIORITY or len({row.identity for row in LEVERS.values()}) != len(LEVERS):
    raise RuntimeError("lever registry priority or identities drifted")


def get_lever(lever_id: str) -> LeverDefinition:
    try:
        return LEVERS[str(lever_id)]
    except KeyError as error:
        raise LeverError(f"unknown lever {lever_id!r}; expected {','.join(LEVER_PRIORITY)}") from error


def apply_profile(
    lever_id: str | None, profile: Mapping[str, object], **context: object,
) -> Mapping[str, object]:
    """Apply one explicit lever; ``None`` returns the original object unchanged."""

    if lever_id is None:
        return profile
    return get_lever(lever_id).apply_profile(profile, **context)


__all__ = ["LEVER_PRIORITY", "LEVERS", "apply_profile", "get_lever"]
