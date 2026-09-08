"""L4: explicit handover/reconfiguration event-energy proxy."""

from __future__ import annotations

import copy
import math
from typing import Mapping, Sequence

import numpy as np

from mcrl.env.link_budget import (
    BEAM_POWER_MAX_W,
    CIRCUIT_POWER_PER_BEAM_W,
    PA_MAX_EFFICIENCY,
    PA_SATURATION_POWER_W,
)

from .common import LeverDefinition, LeverError, RegenerationRequired, TODO_CONTROLLER_DECLARE, constant


LEVER_ID = "L4"  # Provenance: Astra parallel lever-matrix declaration.
IDENTITY = "B2_L4_CONTROL_EVENT_ENERGY_PROXY"  # Provenance: Astra L4 identity item 1.
R2_TAPE_POLICY = "REUSE_PAYLOAD_ROWS_ADD_AUTHENTICATED_EVENT_LEDGER"  # Provenance: Astra L4 tape-validity item 8.
REGENERATION_REQUIRED = False  # Provenance: ASTRA_TRACKB_MULTI excludes L4 from REGEN_NEEDED.
BEAM_SETUP_TIME_S = 500.0e-6  # Provenance: Astra L4 item 4, HOBS Eq. (7)/Table I timing proxy.
FEEDBACK_TIME_S = 50.0e-6  # Provenance: Astra L4 item 4, HOBS Eq. (7)/Table I timing proxy.
ACK_TIME_S = 50.0e-6  # Provenance: Astra L4 item 4, HOBS Eq. (7)/Table I timing proxy.
CONTROL_RX_POWER_W = CIRCUIT_POWER_PER_BEAM_W  # Provenance: Astra L4 item 5 declared 0.338 W receiver proxy.
CONTROL_TX_POWER_W = math.sqrt(BEAM_POWER_MAX_W * PA_SATURATION_POWER_W) / PA_MAX_EFFICIENCY + CIRCUIT_POWER_PER_BEAM_W  # Provenance: Astra L4 item 5 formula using inherited original PA and circuit constants.
BEAM_SETUP_ENERGY_J = CONTROL_TX_POWER_W * BEAM_SETUP_TIME_S  # Provenance: Astra L4 item 3 power-times-source-duration formula.
USER_EVENT_ENERGY_J = CONTROL_RX_POWER_W * FEEDBACK_TIME_S + CONTROL_TX_POWER_W * ACK_TIME_S  # Provenance: Astra L4 item 3 power-times-source-duration formula.
VERIFY_SOURCE_MODEL = TODO_CONTROLLER_DECLARE  # Provenance: Astra L4 item 6 flags incremental-boundary and subsystem verification.
CONTROLLER_TODOS = (
    "L4_VERIFY_INCREMENTAL_RESOURCE_BOUNDARY_AND_EVENT_APPLICABILITY",
    "L4_VERIFY_SUBSYSTEM_EVENT_ENERGY_MEASUREMENTS",
)  # Provenance: Astra L4 VERIFY_SOURCE item 6; task requires fail-closed TODO declarations.

CONSTANTS = (
    constant("beam_setup_time_s", BEAM_SETUP_TIME_S.hex(), "Astra L4 item 4; HOBS timing adapted as a proxy"),
    constant("feedback_time_s", FEEDBACK_TIME_S.hex(), "Astra L4 item 4; HOBS timing adapted as a proxy"),
    constant("ack_time_s", ACK_TIME_S.hex(), "Astra L4 item 4; HOBS timing adapted as a proxy"),
    constant("control_rx_power_w", CONTROL_RX_POWER_W.hex(), "Astra L4 item 5; inherited circuit proxy"),
    constant("control_tx_power_w", CONTROL_TX_POWER_W.hex(), "Astra L4 item 5; original PA at 1.65 W plus circuit"),
    constant("beam_setup_energy_j", BEAM_SETUP_ENERGY_J.hex(), "Astra L4 item 3 formula, unrounded"),
    constant("user_event_energy_j", USER_EVENT_ENERGY_J.hex(), "Astra L4 item 3 formula, unrounded"),
    constant("verify_source_model", VERIFY_SOURCE_MODEL, "Astra L4 item 6; controller must resolve before launch"),
)


def _physical_key(value: object) -> tuple[int, int] | None:
    if value is None:
        return None
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 2:
        raise LeverError("physical association keys must be [NORAD, cell] or null")
    return int(value[0]), int(value[1])


def event_ledger(
    *, predecision_physical_keys: Sequence[object], selected_actions: Sequence[int],
    action_physical_keys: Sequence[Sequence[object]], served: Sequence[bool],
    initial_state_authenticated: bool,
) -> Mapping[str, object]:
    """Count attempted physical transitions and shared destination setups."""

    if not initial_state_authenticated:
        raise LeverError("L4 initial/predecision association state must be authenticated by replay")
    users = len(predecision_physical_keys)
    if not (len(selected_actions) == len(action_physical_keys) == len(served) == users):
        raise LeverError("L4 event-ledger user vectors disagree")
    destinations: list[tuple[int, int]] = []
    failed = 0
    transitions: list[Mapping[str, object]] = []
    for user, (old_value, action, choices, is_served) in enumerate(
        zip(predecision_physical_keys, selected_actions, action_physical_keys, served, strict=True)
    ):
        old = _physical_key(old_value)
        if int(action) < 0:
            continue
        if int(action) >= len(choices):
            raise LeverError("L4 selected action is outside its physical-key table")
        destination = _physical_key(choices[int(action)])
        if destination is None or destination == old:
            continue
        destinations.append(destination)
        if not bool(is_served):
            failed += 1
        transitions.append({"user": user, "from": old_value, "to": list(destination), "served": bool(is_served)})
    setup_count = len(set(destinations))
    handover_count = len(destinations)
    setup_energy = setup_count * BEAM_SETUP_ENERGY_J
    user_energy = handover_count * USER_EVENT_ENERGY_J
    return {
        "handover_count": handover_count,
        "distinct_setup_count": setup_count,
        "failed_attempt_count": failed,
        "setup_energy_j": setup_energy,
        "user_event_energy_j": user_energy,
        "event_energy_j": setup_energy + user_energy,
        "transitions": transitions,
        "initial_state_authenticated": True,
    }


def apply_profile(
    profile: Mapping[str, object], *, predecision_physical_keys: Sequence[object],
    selected_actions: Sequence[int], action_physical_keys: Sequence[Sequence[object]],
    initial_state_authenticated: bool, **_: object,
) -> Mapping[str, object]:
    """Add one current-anchor event charge without changing payload physics."""

    try:
        interval = float.fromhex(str(profile["interval_s"]))
        payload_power = float.fromhex(str(profile["system_power_w"]))
        served = profile["served"]
    except (KeyError, TypeError, ValueError) as error:
        raise LeverError("L4 profile lacks interval, system power, or service") from error
    ledger = event_ledger(
        predecision_physical_keys=predecision_physical_keys,
        selected_actions=selected_actions,
        action_physical_keys=action_physical_keys,
        served=served,
        initial_state_authenticated=initial_state_authenticated,
    )
    if not math.isfinite(interval) or interval <= 0.0 or not math.isfinite(payload_power) or payload_power <= 0.0:
        raise LeverError("L4 profile interval/payload power is invalid")
    event_energy = float(ledger["event_energy_j"])
    result = copy.deepcopy(dict(profile))
    result["system_power_w"] = (payload_power + event_energy / interval).hex()
    result["energy_override"] = {
        "lever": LEVER_ID,
        "identity": IDENTITY,
        "payload_physics_unchanged": True,
        "payload_power_w": payload_power.hex(),
        **ledger,
        "event_energy_share": event_energy / (payload_power * interval + event_energy),
    }
    return result


def regeneration_hook(**_: object) -> object:
    raise RegenerationRequired("L4 reuses payload rows but requires authenticated predecision/event and OPS-3/composed supplements")


DEFINITION = LeverDefinition(
    lever_id=LEVER_ID,
    identity=IDENTITY,
    module_name=__name__,
    priority=4,
    r2_tape_policy=R2_TAPE_POLICY,
    regeneration_required=REGENERATION_REQUIRED,
    controller_todos=CONTROLLER_TODOS,
    constants=CONSTANTS,
    apply_profile=apply_profile,
    regeneration_hook=regeneration_hook,
)
