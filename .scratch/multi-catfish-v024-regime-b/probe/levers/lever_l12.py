"""L12: L1 summed-power RF physics followed by the L2 PA surrogate."""

from __future__ import annotations

from typing import Any, Callable, Mapping

import rate_target_sum_power as _engine

from .common import LeverDefinition, RegenerationRequired, constant, invoke_regeneration_adapter
from .lever_l2_pa_curve import CONTROLLER_TODOS as L2_CONTROLLER_TODOS
from .lever_l2_pa_curve import CONSTANTS as L2_CONSTANTS
from .lever_l2_pa_curve import pa_dc_power_w
from .lever_l1_sum_power import CONSTANTS as L1_CONSTANTS


LEVER_ID = "L12"  # Provenance: Astra parallel lever-matrix declaration.
IDENTITY = "B2_L12_RATE_TARGET_DEVICE_PA"  # Provenance: Astra L12 identity item 1.
R2_TAPE_POLICY = "REGENERATE_L1_RF_THEN_APPLY_L2_PA"  # Provenance: Astra L12 tape-validity item 5.
REGENERATION_REQUIRED = True  # Provenance: ASTRA_TRACKB_MULTI REGEN_NEEDED=L1,L12.
CONTROLLER_TODOS = L2_CONTROLLER_TODOS  # Provenance: Astra L12 inherits every L2 source limitation without refitting.
CONSTANTS = (*L1_CONSTANTS, *L2_CONSTANTS, constant("l1_l12_rf_identity", True, "Astra L12 isolation item 4"))


def evaluate_actions(environment: Any, actions: object, rng: Any, *, enabled: bool = True) -> Any:
    """Evaluate L1 RF/rates with L2 DC accounting and no PA feedback."""

    return _engine.evaluate_actions(
        environment,
        actions,
        rng,
        enabled=enabled,
        pa_dc_power=pa_dc_power_w,
        override_id=IDENTITY,
    )


def apply_profile(profile: Mapping[str, object], **_: object) -> Mapping[str, object]:
    raise RegenerationRequired("L12 needs L1-regenerated RF/rate profiles before L2 energy accounting")


def regeneration_hook(
    replay_and_acquire: Callable[..., object] | None = None, **context: object,
) -> object:
    return invoke_regeneration_adapter(
        replay_and_acquire,
        lever_id=LEVER_ID,
        identity=IDENTITY,
        evaluate_actions=evaluate_actions,
        context=context,
        extra_bindings={"matched_rf_identity_with": "L1"},
    )


DEFINITION = LeverDefinition(
    lever_id=LEVER_ID,
    identity=IDENTITY,
    module_name=__name__,
    priority=2,
    r2_tape_policy=R2_TAPE_POLICY,
    regeneration_required=REGENERATION_REQUIRED,
    controller_todos=CONTROLLER_TODOS,
    constants=CONSTANTS,
    apply_profile=apply_profile,
    regeneration_hook=regeneration_hook,
)
