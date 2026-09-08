"""L1: detached rate-target SINR control with summed per-user RF power."""

from __future__ import annotations

from typing import Any, Callable, Mapping

import rate_target_sum_power as _engine

from .common import LeverDefinition, RegenerationRequired, constant, invoke_regeneration_adapter


LEVER_ID = "L1"  # Provenance: Astra parallel lever-matrix declaration.
IDENTITY = "B2_L1_RATE_TARGET_SUM_POWER"  # Provenance: Astra L1 identity item 1.
R2_TAPE_POLICY = "REGENERATE_PHYSICS_KEEP_TAPE_AS_PROVENANCE_CONTROL"  # Provenance: Astra L1 tape-validity item 7.
REGENERATION_REQUIRED = True  # Provenance: ASTRA_TRACKB_MULTI REGEN_NEEDED=L1,L12.
CONTROLLER_TODOS: tuple[str, ...] = ()  # Provenance: Astra L1 supplies every executable constant.

CONSTANTS = (
    constant("rate_target_bps", _engine.RATE_TARGET_BPS.hex(), "Astra L1 item 2; synthetic scenario, not calibrated traffic"),
    constant("power_residual_tolerance_w", _engine.POWER_RESIDUAL_TOLERANCE_W.hex(), "Astra L1 item 4"),
    constant("power_iteration_limit", _engine.POWER_ITERATION_LIMIT, "Astra L1 item 4"),
    constant("rate_attainment_fraction", _engine.RATE_ATTAINMENT_FRACTION.hex(), "Astra L1 item 8"),
)


def evaluate_actions(environment: Any, actions: object, rng: Any, *, enabled: bool = True) -> Any:
    """Evaluate L1 in a detached copy, or delegate byte-identically when off."""

    return _engine.evaluate_actions(environment, actions, rng, enabled=enabled)


def apply_profile(profile: Mapping[str, object], **_: object) -> Mapping[str, object]:
    """Reject scalar repricing: L1 changes RF, rates, feasibility, and energy."""

    raise RegenerationRequired("L1 requires authenticated anchor replay; r2 scalar physical rows are invalid")


def regeneration_hook(
    replay_and_acquire: Callable[..., object] | None = None, **context: object,
) -> object:
    """Bind the server acquisition adapter without changing keyed fading identity.

    The injected adapter owns heavy replay.  Keeping this as dependency
    injection makes synthetic verification simulator-inert and prevents a
    placeholder tape from being mistaken for acquired evidence.
    """

    return invoke_regeneration_adapter(
        replay_and_acquire,
        lever_id=LEVER_ID,
        identity=IDENTITY,
        evaluate_actions=evaluate_actions,
        context=context,
    )


DEFINITION = LeverDefinition(
    lever_id=LEVER_ID,
    identity=IDENTITY,
    module_name=__name__,
    priority=1,
    r2_tape_policy=R2_TAPE_POLICY,
    regeneration_required=REGENERATION_REQUIRED,
    controller_todos=CONTROLLER_TODOS,
    constants=CONSTANTS,
    apply_profile=apply_profile,
    regeneration_hook=regeneration_hook,
)
