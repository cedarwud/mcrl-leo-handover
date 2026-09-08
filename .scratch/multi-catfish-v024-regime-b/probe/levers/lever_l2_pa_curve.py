"""L2: device-anchored analytical PA back-off surrogate."""

from __future__ import annotations

import copy
import math
from typing import Mapping

import numpy as np

from mcrl.env.link_budget import PA_SATURATION_POWER_W

from .common import LeverDefinition, LeverError, RegenerationRequired, TODO_CONTROLLER_DECLARE, constant


LEVER_ID = "L2"  # Provenance: Astra parallel lever-matrix declaration.
IDENTITY = "B2_L2_PIACIBELLO_SURROGATE"  # Provenance: Astra L2 identity item 1.
R2_TAPE_POLICY = "REUSE_RF_RATE_ROWS_REPRICE_EACH_ACTIVE_BEAM"  # Provenance: Astra L2 tape-validity item 8.
REGENERATION_REQUIRED = False  # Provenance: ASTRA_TRACKB_MULTI excludes L2 from REGEN_NEEDED.
PAE_AT_6DB = 0.20  # Provenance: Astra L2 item 4 midpoint of the cited 19--21% range.
PAE_AT_SATURATION = 0.27  # Provenance: Astra L2 item 4 midpoint of the cited 23--31% range.
GAIN_LINEAR = 100.0  # Provenance: Astra L2 item 4, declared 20 dB midpoint approximation.
BACKOFF_KNEE_RATIO = 10.0 ** (-6.0 / 10.0)  # Provenance: Astra L2 item 2, exact 6 dB back-off formula.
BIAS_FLOOR_W = 1.32  # Provenance: Astra L2 item 5 derived as 11(0.050)[2(0.8+0.3)+0.2] W.
VERIFY_SOURCE_MODEL = TODO_CONTROLLER_DECLARE  # Provenance: Astra L2 item 6 flags source/model verification before launch.
CONTROLLER_TODOS = (
    "L2_VERIFY_GAIN_PAE_AND_BIAS_FLOOR_SOURCE",
    "L2_VERIFY_LOW_POWER_TEMPERATURE_20GHZ_BEAM_MAPPING_AND_MULTICARRIER_APPLICABILITY",
)  # Provenance: Astra L2 VERIFY_SOURCE item 6; task requires fail-closed TODO declarations.

CONSTANTS = (
    constant("pae_at_6db", PAE_AT_6DB.hex(), "Astra L2 item 4; constructed midpoint"),
    constant("pae_at_saturation", PAE_AT_SATURATION.hex(), "Astra L2 item 4; constructed midpoint"),
    constant("gain_linear", GAIN_LINEAR.hex(), "Astra L2 item 4; 20 dB midpoint approximation"),
    constant("backoff_knee_ratio", BACKOFF_KNEE_RATIO.hex(), "Astra L2 item 2; 10^(-6/10)"),
    constant("bias_floor_w", BIAS_FLOOR_W.hex(), "Astra L2 item 5; derived bias approximation"),
    constant("pa_saturation_power_w", PA_SATURATION_POWER_W.hex(), "Inherited link-budget saturation scale per Astra common H"),
    constant("verify_source_model", VERIFY_SOURCE_MODEL, "Astra L2 item 6; controller must resolve before launch"),
)


def pa_dc_power_w(rf_power_w: object) -> np.ndarray | float:
    """Return the declared DC input for legal nonnegative RF output power."""

    scalar = np.asarray(rf_power_w).ndim == 0
    power = np.asarray(rf_power_w, dtype=np.float64)
    if not np.all(np.isfinite(power)) or np.any(power < 0.0) or np.any(power > PA_SATURATION_POWER_W):
        raise LeverError("L2 RF power lies outside 0..P_sat")
    q = power / PA_SATURATION_POWER_W
    efficiency = np.zeros_like(power)
    low = (q > 0.0) & (q <= BACKOFF_KNEE_RATIO)
    high = q > BACKOFF_KNEE_RATIO
    efficiency[low] = PAE_AT_6DB * np.sqrt(q[low] / BACKOFF_KNEE_RATIO)
    efficiency[high] = PAE_AT_6DB + (PAE_AT_SATURATION - PAE_AT_6DB) * (
        q[high] - BACKOFF_KNEE_RATIO
    ) / (1.0 - BACKOFF_KNEE_RATIO)
    dc = np.zeros_like(power)
    positive = power > 0.0
    dc[positive] = np.maximum(BIAS_FLOOR_W, power[positive] * (1.0 - 1.0 / GAIN_LINEAR) / efficiency[positive])
    return float(dc) if scalar else dc


def _float_hex(value: object, *, field: str) -> float:
    try:
        result = float.fromhex(str(value))
    except (TypeError, ValueError) as error:
        raise LeverError(f"L2 profile {field} is not a hexadecimal float") from error
    if not math.isfinite(result):
        raise LeverError(f"L2 profile {field} is nonfinite")
    return result


def beam_powers_from_profile(profile: Mapping[str, object]) -> tuple[np.ndarray, tuple[tuple[int, int], ...]]:
    """Recover original max-user active-beam powers from an r2 physical row."""

    try:
        powers = np.asarray([float.fromhex(str(value)) for value in profile["link_power_w"]], dtype=np.float64)
        served = np.asarray(profile["served"], dtype=np.bool_)
        satellites = np.asarray(profile["serving_satellite"], dtype=np.int64)
        cells = np.asarray(profile["serving_cell"], dtype=np.int64)
    except (KeyError, TypeError, ValueError) as error:
        raise LeverError("L2 profile lacks r2 per-user RF/service identities") from error
    if not (powers.ndim == 1 and served.shape == satellites.shape == cells.shape == powers.shape):
        raise LeverError("L2 profile user vectors disagree")
    by_beam: dict[tuple[int, int], float] = {}
    for index in np.flatnonzero(served).tolist():
        key = (int(satellites[index]), int(cells[index]))
        by_beam[key] = max(by_beam.get(key, 0.0), float(powers[index]))
    keys = tuple(sorted(by_beam))
    return np.asarray([by_beam[key] for key in keys], dtype=np.float64), keys


def apply_profile(profile: Mapping[str, object], **_: object) -> Mapping[str, object]:
    """Reprice one r2 row beam-by-beam while preserving RF, rates, and bits."""

    beam_power, beam_keys = beam_powers_from_profile(profile)
    fixed_power = _float_hex(profile.get("fixed_power_w"), field="fixed_power_w")
    old_system_power = _float_hex(profile.get("system_power_w"), field="system_power_w")
    new_pa = float(np.sum(pa_dc_power_w(beam_power), dtype=np.float64))
    new_system_power = new_pa + fixed_power
    result = copy.deepcopy(dict(profile))
    result["system_power_w"] = new_system_power.hex()
    result["energy_override"] = {
        "lever": LEVER_ID,
        "identity": IDENTITY,
        "rf_rate_rows_unchanged": True,
        "active_beam_keys": [[satellite, cell] for satellite, cell in beam_keys],
        "beam_power_w": [float(value).hex() for value in beam_power],
        "pa_dc_power_w": [float(value).hex() for value in np.asarray(pa_dc_power_w(beam_power))],
        "old_system_power_w": old_system_power.hex(),
        "new_pa_power_w": new_pa.hex(),
        "fixed_circuit_power_w": fixed_power.hex(),
        "new_system_power_w": new_system_power.hex(),
        "bias_floor_beams": int(np.count_nonzero(np.asarray(pa_dc_power_w(beam_power)) == BIAS_FLOOR_W)),
        "at_or_below_6db_knee_beams": int(np.count_nonzero(beam_power / PA_SATURATION_POWER_W <= BACKOFF_KNEE_RATIO)),
    }
    return result


def regeneration_hook(**_: object) -> object:
    """L2 has no full-PHY regeneration; supplementary profiles are repriced too."""

    raise RegenerationRequired("L2 reuses r2 rows but still requires declared OPS-3/LC-SRS/composed supplements")


DEFINITION = LeverDefinition(
    lever_id=LEVER_ID,
    identity=IDENTITY,
    module_name=__name__,
    priority=3,
    r2_tape_policy=R2_TAPE_POLICY,
    regeneration_required=REGENERATION_REQUIRED,
    controller_todos=CONTROLLER_TODOS,
    constants=CONSTANTS,
    apply_profile=apply_profile,
    regeneration_hook=regeneration_hook,
)
