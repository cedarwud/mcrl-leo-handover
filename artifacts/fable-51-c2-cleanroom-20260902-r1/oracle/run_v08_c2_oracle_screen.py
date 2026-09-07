#!/usr/bin/env python3
"""V0.8 Stage-1b C2 formula/oracle interaction screen.

The deployed Multi-Catfish policy sums three value surfaces under one legal
mask and one argmax.  This runner keeps the frozen learned Q1 and Q3 heads and
*replaces* the learned Q2 head by a deterministic orbital-physics oracle

    Q2*(s, a) = ZETA2*(s, a) / kappa_bits

evaluated at decision time from SGP4 satellite positions, the earth-fixed cell
lattice, the frozen antenna/link-budget model, and the previous committed
step's non-focal context.  The OLD learned Q2 surface is never used.

Seven route arms (P1, P3, P2, P12, P13, P23, P123) are evaluated for each of
the three initialization lineages on matched worlds with common randomness,
plus the frozen Main baseline once per world.

Nothing here trains, writes replay, or opens the TEST split: the sampler is
TRAIN-only exactly as ``run_v04_c3_500_update_screen._make_environment`` builds
it, and the hybrid is snapshotted before and asserted unchanged after every
episode.

Read-only with respect to the repository.  Every output goes to --output-dir.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from collections.abc import Mapping, Sequence
import datetime as dt
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys
import tempfile
import time
from typing import Any

import numpy as np
import torch


# --------------------------------------------------------------------------
# Repository seams.  This file lives OUTSIDE the repository and never writes
# into it; it only imports the frozen consumers and the physics modules.
# --------------------------------------------------------------------------

REPO = Path("/home/u24/papers/mcrl-leo-handover")
C3_V04 = REPO / ".scratch" / "c3-v04"
for _path in (C3_V04, REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_v04_c3_500_update_screen as screen  # noqa: E402
import run_v04_c3_learnability_gate as gate  # noqa: E402
import run_v04_c3_source as source  # noqa: E402
import run_v04_five_arm_ablation as five_arm  # noqa: E402
from mcrl.env.action_contract import (  # noqa: E402
    NO_OP_ACTION,
    NUM_ACTIONS,
    NUM_BEAM_SLOTS,
)
from mcrl.env.antenna import RX_GAIN_MAX_DBI, transmit_gain_linear  # noqa: E402
from mcrl.env.geometry import angle_between_deg  # noqa: E402
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.env.link_budget import (  # noqa: E402
    BEAM_BANDWIDTH_HZ,
    BEAM_POWER_MAX_W,
    BASEBAND_POWER_PER_SATELLITE_W,
    CIRCUIT_POWER_PER_BEAM_W,
    SEGMENT_START_POWER_W,
    link_power_factor,
    noise_power_w,
    pa_efficiency,
    supply_power_w,
)
from mcrl.runtime.ee_axis_state import encode_ee_axis_state  # noqa: E402
from mcrl.runtime.ee_axis_v04_c3_state import (  # noqa: E402
    encode_ee_axis_v04_c3_state,
)
from mcrl.runtime.ee_axis_v07_c2_d2 import D2_LAMBDA_BITS_PER_J  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402


HERE = Path(__file__).resolve().parent

RESULT_SCHEMA = "multi-catfish-mcrl-v08-c2-oracle-screen-result-v1"
EPISODE_SCHEMA = "multi-catfish-mcrl-v08-c2-oracle-screen-episode-v1"

# The keyed fading root is (component, evaluation_seed) ONLY: the
# initialization seed and the policy label are deliberately excluded so every
# arm of one world shares one field.
FIELD_COMPONENT = "V08_C2_ORACLE_SCREEN_V1"
FIELD_EXCLUDED_COMPONENTS = ("initialization_seed", "policy_label")

USERS = 100
STEPS_PER_EPISODE = 10
EVALUATION_SPLIT = "TRAIN"
TEST_SPLIT_OPENED = False
EPISODE_TRAINING = False
SELECTED_Q3_RUNG = five_arm.SELECTED_Q3_RUNG
INITIALIZATION_SEEDS = tuple(gate.INITIALIZATION_SEEDS)

SMOKE_SEED = 2026090299
PREREG_BLOCK_SEEDS = tuple(range(2026090221, 2026090227))

# Two oracle surfaces live side by side: "Q2S" is the parent contract's H-A
# surface, "Q2S_OPS3" is Addendum A's variant.  Arms name which they sum.
ROUTE_NAMES = ("Q1", "Q2S", "Q2S_OPS3", "Q3")
HA_ROUTE_ARMS = ("P1", "P3", "P2", "P12", "P13", "P23", "P123")
OPS3_ROUTE_ARMS = ("O2", "O12", "O23", "O123")
ROUTE_ARMS = (*HA_ROUTE_ARMS, *OPS3_ROUTE_ARMS)
ARMS = (*ROUTE_ARMS, "MAIN")
ARM_ORDER = (
    "P1",
    "P2",
    "P3",
    "P12",
    "P13",
    "P23",
    "P123",
    "O2",
    "O12",
    "O23",
    "O123",
    "MAIN",
)
ACTIVE_ROUTES: dict[str, tuple[str, ...]] = {
    "P1": ("Q1",),
    "P3": ("Q3",),
    "P2": ("Q2S",),
    "P12": ("Q1", "Q2S"),
    "P13": ("Q1", "Q3"),
    "P23": ("Q2S", "Q3"),
    "P123": ("Q1", "Q2S", "Q3"),
    "O2": ("Q2S_OPS3",),
    "O12": ("Q1", "Q2S_OPS3"),
    "O23": ("Q2S_OPS3", "Q3"),
    "O123": ("Q1", "Q2S_OPS3", "Q3"),
}
HA_SURFACE_ARMS = frozenset(
    arm for arm, routes in ACTIVE_ROUTES.items() if "Q2S" in routes
)
OPS3_SURFACE_ARMS = frozenset(
    arm for arm, routes in ACTIVE_ROUTES.items() if "Q2S_OPS3" in routes
)

HA_PRIMARY_CONTRASTS = (
    ("P123", "P13"),   # D-C2
    ("P123", "P12"),   # D-C3
    ("P123", "P23"),   # D-C1
)
OPS3_PRIMARY_CONTRASTS = (
    ("O123", "P13"),   # D-C2  (P13 is shared between the two routes)
    ("O123", "O12"),   # D-C3
    ("O123", "O23"),   # D-C1
)
PRIMARY_CONTRASTS = (*HA_PRIMARY_CONTRASTS, *OPS3_PRIMARY_CONTRASTS)
NAMED_CONTRASTS = (
    *PRIMARY_CONTRASTS,
    ("P123", "MAIN"),
    ("O123", "MAIN"),
    ("P13", "P1"),
    ("P12", "P1"),
    ("O12", "P1"),
    ("P1", "MAIN"),
    ("P13", "MAIN"),
    ("P123", "O123"),
)
CONTRAST_ROLE = {
    ("P123", "P13"): "primary_c2_direction",
    ("P123", "P12"): "primary_c3_direction",
    ("P123", "P23"): "primary_c1_direction",
    ("O123", "P13"): "ops3_primary_c2_direction",
    ("O123", "O12"): "ops3_primary_c3_direction",
    ("O123", "O23"): "ops3_primary_c1_direction",
    ("P123", "MAIN"): "named_vs_main",
    ("O123", "MAIN"): "named_ops3_vs_main",
    ("P13", "P1"): "named_q3_marginal",
    ("P12", "P1"): "named_q2star_marginal",
    ("O12", "P1"): "named_q2star_ops3_marginal",
    ("P1", "MAIN"): "named_q1_vs_main",
    ("P13", "MAIN"): "named_dropc2_vs_main",
    ("P123", "O123"): "named_route_head_to_head",
}

BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_SEED = 2026090299

# Oracle constants ---------------------------------------------------------

HORIZON_OFFSETS = (1, 2, 3)
P0_W = float(SEGMENT_START_POWER_W)
P_MAX_W = float(BEAM_POWER_MAX_W)
RX_GAIN_MAX_LINEAR = 10.0 ** (RX_GAIN_MAX_DBI / 10.0)
NOISE_W = float(noise_power_w(BEAM_BANDWIDTH_HZ))

# Sealed TRAIN-only multipliers.  NEVER recomputed from new outcomes.
LAMBDA0_BITS_PER_J = float(source.LAMBDA_BITS_PER_J)
LAMBDA0_HEX = LAMBDA0_BITS_PER_J.hex()
LAMBDA0_SOURCES = (
    ".scratch/c3-v04/run_v04_c3_source.py:LAMBDA_BITS_PER_J",
    "src/mcrl/runtime/ee_axis_v07_c2_d2.py:D2_LAMBDA_BITS_PER_J",
)
KAPPA_BITS_SOURCE = float(source.KAPPA_BITS)

DEFAULT_TLE_ROOT = Path("~/demo/tle_data/starlink/tle").expanduser()

# The exact live modules whose physics this oracle mirrors.  Their digests are
# recorded in every result so the formula can be bound to the code that
# produced the episodes, independently of the (stale) V0.4 source-construction
# closure manifest.
PHYSICS_CODE_PATHS = (
    "src/mcrl/env/step.py",
    "src/mcrl/env/link_budget.py",
    "src/mcrl/env/antenna.py",
    "src/mcrl/env/pointing.py",
    "src/mcrl/env/geometry.py",
    "src/mcrl/env/cells.py",
    "src/mcrl/env/candidates.py",
    "src/mcrl/env/action_contract.py",
    "src/mcrl/env/service.py",
    "src/mcrl/env/scenario.py",
    "src/mcrl/env/keyed_fading.py",
    "src/mcrl/runtime/trainer_env.py",
    "src/mcrl/runtime/ee_axis_state.py",
    "src/mcrl/runtime/ee_axis_v04_c3_state.py",
    "src/mcrl/algorithms/ee_axis_v04_hybrid.py",
    ".scratch/c3-v04/run_v04_c3_500_update_screen.py",
    ".scratch/c3-v04/run_v04_c3_learnability_gate.py",
    ".scratch/c3-v04/run_v04_c3_source.py",
    ".scratch/c3-v04/run_v04_five_arm_ablation.py",
)


class OracleScreenError(RuntimeError):
    """One error type for every refusal in this runner."""


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
            "utf-8"
        )
    ).hexdigest()


def _array_sha256(*arrays: np.ndarray) -> str:
    digest = hashlib.sha256()
    for value in arrays:
        array = np.ascontiguousarray(np.asarray(value))
        digest.update(str(array.dtype).encode("ascii"))
        digest.update(repr(tuple(array.shape)).encode("ascii"))
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _field_for_seed(evaluation_seed: int) -> KeyedFadingField:
    seed = int(evaluation_seed)
    if seed < 1:
        raise OracleScreenError("evaluation_seed must be a positive integer")
    return KeyedFadingField.from_components(FIELD_COMPONENT, seed)


def common_field_receipt(evaluation_seed: int) -> dict[str, Any]:
    field = _field_for_seed(evaluation_seed)
    return {
        "components": [FIELD_COMPONENT, int(evaluation_seed)],
        "excluded_components": list(FIELD_EXCLUDED_COMPONENTS),
        "root_digest": field.root_digest,
    }


def _supply_power_w(power: np.ndarray) -> np.ndarray:
    """``P^p(p) = p / xi(p)`` from the live link-budget seam; ``P^p(0) = 0``."""

    values = np.asarray(power, dtype=np.float64)
    clean = np.where(np.isfinite(values) & (values > 0.0), values, 0.0)
    return supply_power_w(clean, pa_efficiency(clean))


# --------------------------------------------------------------------------
# Action selection.  Identical shape to five_arm.route_actions: one common
# legal mask, one argmax over the left-to-right route sum.
# --------------------------------------------------------------------------


def select_actions(
    surfaces: Mapping[str, np.ndarray], masks: np.ndarray, policy_label: str
) -> np.ndarray:
    if policy_label not in ROUTE_ARMS:
        raise OracleScreenError(f"unsupported route arm: {policy_label}")
    arrays = tuple(np.asarray(surfaces[name], dtype=np.float64) for name in ROUTE_NAMES)
    if any(array.ndim != 2 for array in arrays):
        raise OracleScreenError("route Q surfaces must be two-dimensional")
    if any(array.shape != arrays[0].shape for array in arrays[1:]):
        raise OracleScreenError("route Q surfaces must share one shape")
    if any(not np.all(np.isfinite(array)) for array in arrays):
        raise OracleScreenError("route Q surfaces must be finite")
    legal = np.asarray(masks)
    if legal.dtype != np.bool_ or legal.shape != arrays[0].shape:
        raise OracleScreenError("common legal mask must be Boolean and match Q surfaces")
    if not np.all(np.any(legal, axis=1)):
        raise OracleScreenError("common legal mask must admit one action per user")

    active = ACTIVE_ROUTES[policy_label]
    indices = tuple(ROUTE_NAMES.index(route) for route in active)
    scores = np.array(arrays[indices[0]], copy=True)
    for index in indices[1:]:
        scores = scores + arrays[index]
    if not np.all(np.isfinite(scores)):
        raise OracleScreenError("summed route scores are non-finite")
    actions = np.full(scores.shape[0], NO_OP_ACTION, dtype=np.int64)
    eligible = np.any(legal, axis=1)
    actions[eligible] = np.argmax(
        np.where(legal[eligible], scores[eligible], -np.inf), axis=1
    )
    return actions


# --------------------------------------------------------------------------
# The oracle target ZETA2*(s, a)
# --------------------------------------------------------------------------


def _slot_tables_arrays(observation: Any) -> tuple[np.ndarray, np.ndarray]:
    norad = np.stack([table.norad_ids for table in observation.candidates.slot_tables])
    cell = np.stack([table.cell_ids for table in observation.candidates.slot_tables])
    return norad.astype(np.int64), cell.astype(np.int64)


def _theta0_deg(observation: Any) -> np.ndarray:
    """``(U, 28)`` current off-axis angle, laid out exactly as ``_observe``."""

    off_axis = observation.candidates.off_axis_deg
    users = off_axis.shape[0]
    theta = np.zeros((users, NUM_ACTIONS), dtype=np.float64)
    for slot in range(off_axis.shape[1]):
        block = slice(slot * NUM_BEAM_SLOTS, (slot + 1) * NUM_BEAM_SLOTS)
        angles = off_axis[:, slot, :]
        theta[:, block] = np.where(np.isnan(angles), 0.0, angles)
    return theta


def _repeat_per_slot(values: np.ndarray) -> np.ndarray:
    """``(U, L)`` -> ``(U, 28)`` in the action layout used by ``_candidate_sinr``."""

    return np.repeat(np.asarray(values, dtype=np.float64), NUM_BEAM_SLOTS, axis=1)


def _positions_for_offset(driver: Any, offset: int) -> tuple[np.ndarray, np.ndarray]:
    """Sorted NORAD ids and their ``(S, 3)`` ECEF km ``offset`` steps ahead."""

    mapping = driver.satellite_ecef_at(int(offset))
    norads = np.array(sorted(int(key) for key in mapping), dtype=np.int64)
    if norads.size == 0:
        raise OracleScreenError("the driver returned no tracked satellite positions")
    positions = np.stack(
        [np.asarray(mapping[int(norad)], dtype=np.float64) for norad in norads]
    )
    return norads, positions


def _gather_positions(
    norad_ids: np.ndarray, table_norads: np.ndarray, table_positions: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """``(U, 28, 3)`` positions plus a Boolean "this NORAD is tracked" mask."""

    flat = norad_ids.reshape(-1)
    index = np.searchsorted(table_norads, flat)
    safe = np.clip(index, 0, table_norads.size - 1)
    present = (flat >= 0) & (table_norads[safe] == flat)
    positions = table_positions[safe].reshape(norad_ids.shape + (3,))
    finite = np.all(np.isfinite(positions), axis=-1)
    return positions, present.reshape(norad_ids.shape) & finite


def _geometry(
    satellite_ecef: np.ndarray, user_ecef: np.ndarray, cell_ecef: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Off-axis angle (deg), slant range (km), and elevation (deg).

    Mirrors ``pointing.candidate_geometry``: the slant range is
    ``|r_sat - r_user|`` and the elevation comes from the user's local up
    vector; the off-axis angle is eq. (3.6) at the satellite.
    """

    delta = satellite_ecef - user_ecef
    slant = np.linalg.norm(delta, axis=-1)
    up = user_ecef / np.maximum(
        np.linalg.norm(user_ecef, axis=-1, keepdims=True), 1e-12
    )
    sin_elevation = np.sum(delta * up, axis=-1) / np.maximum(slant, 1e-12)
    elevation = np.degrees(np.arcsin(np.clip(sin_elevation, -1.0, 1.0)))
    theta = angle_between_deg(satellite_ecef, cell_ecef, user_ecef)
    return theta, slant, elevation


def _frozen_context(
    outcome: Any, norad_ids: np.ndarray, cell_ids: np.ndarray, legal: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """``n_a``, ``m_a`` and ``sat_active_a`` from the last committed step.

    All three are *non-focal*: user ``u``'s own contribution to the previous
    step is removed from its own row, so the oracle scores the marginal
    addition of ``u`` to a beam that already carries the others.
    """

    users, actions = norad_ids.shape
    counts: dict[tuple[int, int], int] = defaultdict(int)
    best: dict[tuple[int, int], tuple[float, int]] = {}
    second: dict[tuple[int, int], float] = defaultdict(float)
    sat_counts: dict[int, int] = defaultdict(int)
    own_beam: list[tuple[int, int] | None] = [None] * users

    if outcome is not None:
        resolution = outcome.resolution
        served = np.asarray(resolution.served, dtype=bool)
        serving_satellite = np.asarray(resolution.serving_satellite, dtype=np.int64)
        serving_cell = np.asarray(resolution.serving_cell, dtype=np.int64)
        link_power = np.asarray(outcome.link_power_w, dtype=np.float64)
        for uid in range(min(users, served.size)):
            if not bool(served[uid]):
                continue
            key = (int(serving_satellite[uid]), int(serving_cell[uid]))
            own_beam[uid] = key
            counts[key] += 1
            sat_counts[key[0]] += 1
            power = float(link_power[uid])
            current = best.get(key)
            if current is None or power > current[0]:
                if current is not None:
                    second[key] = max(second[key], current[0])
                best[key] = (power, uid)
            else:
                second[key] = max(second[key], power)

    n_a = np.zeros((users, actions), dtype=np.float64)
    m_a = np.zeros((users, actions), dtype=np.float64)
    sat_active = np.zeros((users, actions), dtype=bool)
    if outcome is None:
        return n_a, m_a, sat_active

    for uid in range(users):
        mine = own_beam[uid]
        for action in range(actions):
            if not bool(legal[uid, action]):
                continue
            key = (int(norad_ids[uid, action]), int(cell_ids[uid, action]))
            count = counts.get(key, 0)
            top = best.get(key)
            peak = 0.0 if top is None else top[0]
            if mine is not None and mine == key:
                count -= 1
                if top is not None and top[1] == uid:
                    peak = float(second.get(key, 0.0))
            n_a[uid, action] = float(count)
            m_a[uid, action] = 0.0 if count <= 0 else peak
            satellite = key[0]
            sat_count = sat_counts.get(satellite, 0)
            if mine is not None and mine[0] == satellite:
                sat_count -= 1
            sat_active[uid, action] = sat_count > 0
    return n_a, m_a, sat_active


def oracle_q2_star(
    environment: Any,
    observation: Any,
    *,
    kappa_bits: float,
    interval_s: float,
    step_index: int,
    steps_per_episode: int = STEPS_PER_EPISODE,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Return the two ``(U, 28)`` oracle surfaces plus a diagnostic block.

    **H-A** (parent contract section 1) -- bounded-horizon hold surplus,
    censored at the first infeasible offset:

        ZETA2*_a = sum_{k=1..3} [ dt * R_a(k) - lambda0 * dt * P_a(k) ]
        Q2*_HA   = ZETA2*_a / kappa

    **OPS-3** (Addendum A) -- the same p_a(h), R_a(h), P_a(h), frozen
    background and constants, but averaged over a truncated horizon with an
    explicit outage charge instead of censoring:

        H_t      = min(3, 9 - t)                       (Z = 0 when H_t = 0)
        chi_a(h) = 1[G_a(h) > 0] 1[p_a(h) <= 1.65] 1[elev_a(h) > 0 deg]
        Z_a      = (1/H_t) sum_{h=1..H_t}
                     [ chi_a(h) dt (R_a(h) - lambda0 P_a(h))
                       - (1 - chi_a(h)) kappa ]
        Q2*_OPS3 = Z_a / kappa

    The per-offset raw ``R`` and ``P`` are shared: only the aggregation
    differs, which is what makes the ``H_t = 3``, all-chi self-check exact.
    """

    step_env = environment.environment
    driver = step_env.driver
    legal = np.asarray(observation.masks, dtype=bool)
    norad_ids, cell_ids = _slot_tables_arrays(observation)
    users = legal.shape[0]

    theta0 = _theta0_deg(observation)
    gain0 = np.asarray(transmit_gain_linear(theta0), dtype=np.float64)
    gain0 = np.where(legal, gain0, 0.0)

    slant0 = _repeat_per_slot(observation.candidates.slant_range_km)
    elevation0 = _repeat_per_slot(observation.candidates.elevation_deg)
    usable0 = legal & np.isfinite(slant0)
    path0 = np.where(
        usable0,
        link_power_factor(
            np.where(usable0, slant0, 1.0),
            np.where(usable0, elevation0, 0.0),
            np.full(slant0.shape, RX_GAIN_MAX_LINEAR),
            shadow_fading_db=0.0,
        ),
        0.0,
    )

    # I_a + N frozen at its decision-time value, obtained by inverting the
    # observation's gamma block under the expected-value convention fade = 1
    # and shadow = 0 dB.  Both random terms therefore cancel between the
    # numerator and the denominator of R_a(k); what survives is the
    # deterministic geometry ratio path(t+k)/path(t).
    sinr0 = np.asarray(observation.candidate_sinr, dtype=np.float64)
    positive = legal & (sinr0 > 0.0)
    denominator = np.where(
        positive,
        P0_W * gain0 * path0 / np.where(positive, sinr0, 1.0),
        NOISE_W,
    )
    nonpositive_sinr = int(np.count_nonzero(legal & ~positive))
    denominator = np.where(
        np.isfinite(denominator) & (denominator > 0.0), denominator, NOISE_W
    )

    # Segment start gain: p(t) = p0 * G(theta(tau)) / G(theta(t)).
    start_gain = np.array(gain0, copy=True)
    continuing_mask = np.zeros((users, NUM_ACTIONS), dtype=bool)
    for uid in range(users):
        segment = step_env._segments[uid]
        if segment is None or step_env._previous_association[uid] is None:
            continue
        same = (norad_ids[uid] == segment.norad_id) & (
            cell_ids[uid] == segment.cell_id
        )
        same &= legal[uid]
        if not np.any(same):
            continue
        continuing_mask[uid] = same
        start_gain[uid] = np.where(same, float(segment.start_transmit_gain), gain0[uid])

    n_a, m_a, sat_active = _frozen_context(
        environment._last_outcome, norad_ids, cell_ids, legal
    )
    base_supply = _supply_power_w(m_a)
    empty_beam = (n_a <= 0.0) & legal
    fixed_term = np.where(
        empty_beam,
        CIRCUIT_POWER_PER_BEAM_W
        + np.where(sat_active, 0.0, BASEBAND_POWER_PER_SATELLITE_W),
        0.0,
    )

    user_ecef = np.asarray(driver.user_ecef_km(), dtype=np.float64)[:, None, :]
    grid_centres = np.asarray(driver.grid.centers_ecef_km, dtype=np.float64)
    safe_cells = np.where(cell_ids >= 0, cell_ids, 0)
    cell_ecef = grid_centres[safe_cells]

    # Addendum A: H_t = min(3, 9 - t) with a 10-step episode.  H_t = 0 at the
    # last decision, where the OPS-3 surface is identically zero.
    horizon_t = int(max(0, min(len(HORIZON_OFFSETS), (steps_per_episode - 1) - int(step_index))))

    alive = legal.copy()
    zeta = np.zeros((users, NUM_ACTIONS), dtype=np.float64)
    ops3_sum = np.zeros((users, NUM_ACTIONS), dtype=np.float64)
    chi_all = legal.copy()
    censored_at: dict[str, int] = {}
    chi_zero_at: dict[str, int] = {}
    below_horizon_at: dict[str, int] = {}
    predicted_power = {}
    for offset in HORIZON_OFFSETS:
        table_norads, table_positions = _positions_for_offset(driver, offset)
        satellite_ecef, tracked = _gather_positions(
            norad_ids, table_norads, table_positions
        )
        theta_k, slant_k, elevation_k = _geometry(satellite_ecef, user_ecef, cell_ecef)
        usable_k = legal & tracked & np.isfinite(theta_k) & np.isfinite(slant_k)
        gain_k = np.where(
            usable_k,
            np.asarray(
                transmit_gain_linear(np.where(usable_k, theta_k, 0.0)), dtype=np.float64
            ),
            0.0,
        )
        power_k = np.where(
            gain_k > 0.0, P0_W * start_gain / np.where(gain_k > 0.0, gain_k, 1.0), np.inf
        )
        feasible_k = usable_k & (gain_k > 0.0) & (power_k <= P_MAX_W)
        above_horizon_k = usable_k & (elevation_k > 0.0)
        # Addendum A chi: per offset, no running censoring.
        chi_k = feasible_k & above_horizon_k
        alive = alive & feasible_k
        censored_at[f"k{offset}"] = int(np.count_nonzero(legal & ~alive))
        chi_zero_at[f"h{offset}"] = int(np.count_nonzero(legal & ~chi_k))
        below_horizon_at[f"h{offset}"] = int(
            np.count_nonzero(legal & feasible_k & ~above_horizon_k)
        )
        if offset == 1:
            predicted_power = {
                "power_w": np.where(feasible_k, power_k, np.nan),
                "feasible": feasible_k,
            }

        # Raw per-offset rate and marginal power, evaluated wherever the
        # geometry exists.  Both aggregations below consume exactly these.
        path_k = np.where(
            usable_k,
            link_power_factor(
                np.where(usable_k, slant_k, 1.0),
                np.where(usable_k, elevation_k, 0.0),
                np.full(slant_k.shape, RX_GAIN_MAX_LINEAR),
                shadow_fading_db=0.0,
            ),
            0.0,
        )
        gamma_k = np.where(usable_k, P0_W * start_gain * path_k / denominator, 0.0)
        rate_k = np.where(
            usable_k, (BEAM_BANDWIDTH_HZ / (n_a + 1.0)) * np.log2(1.0 + gamma_k), 0.0
        )
        finite_power_k = np.where(np.isfinite(power_k), power_k, 0.0)
        marginal_k = np.where(
            usable_k,
            _supply_power_w(np.maximum(m_a, finite_power_k))
            - base_supply
            + fixed_term,
            0.0,
        )
        surplus_k = interval_s * rate_k - LAMBDA0_BITS_PER_J * interval_s * marginal_k

        # H-A: censored from the first infeasible offset onward.
        zeta = zeta + np.where(alive, surplus_k, 0.0)

        # OPS-3: truncated at the episode end, -kappa per projected outage.
        if offset <= horizon_t:
            ops3_sum = ops3_sum + np.where(chi_k, surplus_k, -float(kappa_bits))
            chi_all = chi_all & chi_k

    zeta = np.where(legal, zeta, 0.0)
    if not np.all(np.isfinite(zeta)):
        raise OracleScreenError("the oracle target produced a non-finite value")
    q2_star = zeta / float(kappa_bits)

    if horizon_t > 0:
        z_ops3 = np.where(legal, ops3_sum / float(horizon_t), 0.0)
    else:
        z_ops3 = np.zeros((users, NUM_ACTIONS), dtype=np.float64)
        chi_all = np.zeros((users, NUM_ACTIONS), dtype=bool)
    if not np.all(np.isfinite(z_ops3)):
        raise OracleScreenError("the OPS-3 oracle target produced a non-finite value")
    q2_star_ops3 = z_ops3 / float(kappa_bits)

    # Self-check: where H_t = 3 and every chi is 1, OPS-3 must be H-A / 3.
    ratio_check = {"samples": 0, "max_rel_error": 0.0}
    if horizon_t == len(HORIZON_OFFSETS):
        exact = legal & chi_all & alive
        if np.any(exact):
            expected = q2_star[exact] / float(len(HORIZON_OFFSETS))
            observed = q2_star_ops3[exact]
            scale = np.maximum(np.abs(expected), 1e-300)
            ratio_check = {
                "samples": int(np.count_nonzero(exact)),
                "max_rel_error": float(np.max(np.abs(observed - expected) / scale)),
            }

    diagnostics = {
        "nonpositive_candidate_sinr": nonpositive_sinr,
        "censored_legal_actions": censored_at,
        "ops3_chi_zero_legal_actions": chi_zero_at,
        "ops3_below_horizon_legal_actions": below_horizon_at,
        "ops3_horizon_t": horizon_t,
        "ops3_ratio_check": ratio_check,
        "legal_actions": int(np.count_nonzero(legal)),
        "continuing_legal_actions": int(np.count_nonzero(continuing_mask)),
        "step_zero_context": environment._last_outcome is None,
        "gain0": gain0,
        "theta0_deg": theta0,
        "start_gain": start_gain,
        "predicted_power_k1": predicted_power,
        "zeta_bits": zeta,
        "z_ops3_bits": z_ops3,
        "norad_ids": norad_ids,
        "cell_ids": cell_ids,
    }
    return q2_star, q2_star_ops3, diagnostics


# --------------------------------------------------------------------------
# Episode evaluation
# --------------------------------------------------------------------------


def _encode_world(
    environment: Any, observation: Any, *, interval_s: float, kappa_bits: float
) -> dict[str, Any]:
    legacy = encode_ee_axis_state(environment.environment, observation)
    v04 = encode_ee_axis_v04_c3_state(
        environment.environment,
        observation,
        interval_s=interval_s,
        kappa_bits=kappa_bits,
    )
    if not np.array_equal(legacy.action_masks, v04.action_masks):
        raise OracleScreenError("V0.3/V0.4 deployment masks differ")
    masks = np.asarray(v04.action_masks)
    if masks.dtype != np.bool_ or masks.shape != (USERS, NUM_ACTIONS):
        raise OracleScreenError("deployment masks have an unexpected shape")
    state_sha = _array_sha256(
        np.asarray(legacy.state_matrix), np.asarray(v04.state_matrix)
    )
    mask_sha = _array_sha256(masks)
    start_epoch = str(environment.epoch.isoformat())
    world_sha = canonical_sha256(
        {
            "start_epoch": start_epoch,
            "initial_state_sha256": state_sha,
            "initial_mask_sha256": mask_sha,
        }
    )
    return {
        "legacy": legacy,
        "v04": v04,
        "masks": masks,
        "start_epoch": start_epoch,
        "initial_world_sha256": world_sha,
        "initial_state_sha256": state_sha,
        "initial_mask_sha256": mask_sha,
    }


def _validate_physics(outcome: Any) -> tuple[np.ndarray, float]:
    rates = np.asarray(outcome.link_rate_bps, dtype=np.float64)
    power = float(outcome.system_power_w)
    system_rate = float(math.fsum(float(value) for value in rates))
    if (
        rates.shape != (USERS,)
        or not np.all(np.isfinite(rates))
        or np.any(rates < 0.0)
        or not math.isfinite(power)
        or power < 0.0
        or (power == 0.0 and system_rate > 0.0)
    ):
        raise OracleScreenError("episode produced malformed physical EE inputs")
    return rates, power


def _action_trace_sha256(
    *,
    policy_label: str,
    initialization_seed: int | None,
    evaluation_seed: int,
    actions: Sequence[Sequence[int]],
) -> str:
    return canonical_sha256(
        {
            "schema": "multi-catfish-mcrl-v08-c2-oracle-action-trace-v1",
            "policy_label": policy_label,
            "initialization_seed": initialization_seed,
            "evaluation_seed": evaluation_seed,
            "actions": actions,
        }
    )


def _row(
    *,
    policy_label: str,
    initialization_seed: int | None,
    evaluation_seed: int,
    encoded: Mapping[str, Any],
    field: KeyedFadingField,
    total_bits: float,
    total_energy: float,
    served_user_steps: int,
    steps: int,
    actions: Sequence[Sequence[int]],
    hold_decisions: int,
    infeasible_hold_count: int,
    infeasible_incumbent_count: int,
    per_step_power_w: Sequence[float],
    per_step_bits: Sequence[float],
    per_step_served: Sequence[int],
    oracle_diagnostics: Mapping[str, Any] | None,
    elapsed_s: float,
) -> dict[str, Any]:
    if total_energy <= 0.0:
        raise OracleScreenError("episode must consume positive total energy")
    decision_count = steps * USERS
    if decision_count <= 0 or not 0 <= served_user_steps <= decision_count:
        raise OracleScreenError("episode service counts are non-physical")
    return {
        "schema": EPISODE_SCHEMA,
        "policy_label": policy_label,
        "evaluation_split": EVALUATION_SPLIT,
        "initialization_seed": initialization_seed,
        "evaluation_seed": int(evaluation_seed),
        "selected_q3_rung": SELECTED_Q3_RUNG if policy_label != "MAIN" else None,
        "steps": int(steps),
        "users": USERS,
        "decision_count": int(decision_count),
        "start_epoch": encoded["start_epoch"],
        "initial_world_sha256": encoded["initial_world_sha256"],
        "initial_state_sha256": encoded["initial_state_sha256"],
        "initial_mask_sha256": encoded["initial_mask_sha256"],
        "fading_field_sha256": field.root_digest,
        "fading_field_components": [FIELD_COMPONENT, int(evaluation_seed)],
        "total_bits": float(total_bits),
        "total_energy_j": float(total_energy),
        "ratio_of_sums_ee_bits_per_j": float(total_bits / total_energy),
        "served_user_steps": int(served_user_steps),
        "served_fraction": float(served_user_steps / decision_count),
        "outage_fraction": float(1.0 - served_user_steps / decision_count),
        "action_trace_sha256": _action_trace_sha256(
            policy_label=policy_label,
            initialization_seed=initialization_seed,
            evaluation_seed=evaluation_seed,
            actions=actions,
        ),
        "hold_decisions": int(hold_decisions),
        "hold_fraction": float(hold_decisions / decision_count),
        "infeasible_hold_count": int(infeasible_hold_count),
        "infeasible_on_incumbent_count": int(infeasible_incumbent_count),
        "per_step_total_power_w": [float(value) for value in per_step_power_w],
        "per_step_bits": [float(value) for value in per_step_bits],
        "per_step_served_users": [int(value) for value in per_step_served],
        "oracle_diagnostics": dict(oracle_diagnostics) if oracle_diagnostics else None,
        "elapsed_s": float(elapsed_s),
        "test_split_opened": TEST_SPLIT_OPENED,
        "episode_training": EPISODE_TRAINING,
    }


def _ops3_reference_delta(
    main_reference: tuple[Any, Any],
    environment: Any,
    observation: Any,
    z_ops3_bits: np.ndarray,
    masks: np.ndarray,
    env_rng: Any,
) -> list[float]:
    """Diagnostic only: ``Z_a - Z_{a^M}`` at the frozen-Main reference row.

    Addendum A drops this subtraction from the deployed surface because it is
    a per-state constant that cannot move an argmax.  It is recovered here
    purely to report its spread.  The frozen Main policy is queried through
    the authoritative read-only seam and its action is never committed.
    """

    runtime, main_trainer = main_reference
    if main_trainer is None:
        return []
    reference = np.asarray(
        runtime.main_actions(
            main_trainer,
            environment,
            list(observation.user_states),
            masks,
            observation,
            env_rng,
        ),
        dtype=np.int64,
    )
    legal = np.asarray(masks, dtype=bool)
    out: list[float] = []
    for uid in range(reference.shape[0]):
        action = int(reference[uid])
        if action == NO_OP_ACTION or not bool(legal[uid, action]):
            continue
        base = float(z_ops3_bits[uid, action])
        row = z_ops3_bits[uid][legal[uid]]
        out.extend((row - base).tolist())
    return out


def _finalize_oracle_notes(
    notes: Mapping[str, Any], reference_deltas: Sequence[float]
) -> dict[str, Any]:
    payload = dict(notes)
    if reference_deltas:
        values = np.asarray(reference_deltas, dtype=np.float64)
        payload["ops3_reference_row_delta_bits"] = {
            "samples": int(values.size),
            "min": float(np.min(values)),
            "median": float(np.median(values)),
            "max": float(np.max(values)),
            "mean_abs": float(np.mean(np.abs(values))),
        }
    else:
        payload["ops3_reference_row_delta_bits"] = None
    return payload


def _incumbent_pairs(step_env: Any) -> list[tuple[int, int] | None]:
    return [
        None if association is None else (int(association.norad_id), int(association.cell_id))
        for association in step_env._previous_association
    ]


def evaluate_route_episode(
    trainer: Any,
    archive: Any,
    *,
    evaluation_seed: int,
    initialization_seed: int,
    policy_label: str,
    field: KeyedFadingField,
    instrument: dict[str, Any] | None = None,
    main_reference: tuple[Any, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate one frozen route arm.  Never mutates the hybrid.

    ``main_reference`` is ``(runtime, main_trainer)``.  When supplied it is
    used ONLY to recover the frozen-Main reference action ``a^M`` at each
    anchor so that ``Z_a - Z_{a^M}`` can be reported as an OPS-3 diagnostic.
    It never enters a score, an argmax or a committed action.
    """

    if policy_label not in ROUTE_ARMS:
        raise OracleScreenError(f"unsupported route policy: {policy_label}")
    five_arm._prepare_hybrid(trainer)
    expected = _field_for_seed(evaluation_seed)
    if field.root_digest != expected.root_digest:
        raise OracleScreenError("route episode field is not the common keyed field")
    before = five_arm._snapshot_hybrid(trainer)
    started = time.perf_counter()

    environment = screen._make_environment(archive, users=USERS)
    environment.environment._fading_field = field
    env_rng, mobility_rng, _action_rng, _control_rng = screen._evaluation_rngs(
        evaluation_seed
    )
    _states, _masks, observation = environment.reset(env_rng, mobility_rng)
    interval_s = float(environment.environment.driver.config.ephemeris.time_step_s)
    if not math.isfinite(interval_s) or interval_s <= 0.0:
        raise OracleScreenError("TRAIN interval is not finite and positive")
    kappa_bits = float(trainer.v04_config.kappa_bits)
    encoded = _encode_world(
        environment, observation, interval_s=interval_s, kappa_bits=kappa_bits
    )

    needs_ha = policy_label in HA_SURFACE_ARMS
    needs_ops3 = policy_label in OPS3_SURFACE_ARMS
    needs_oracle = needs_ha or needs_ops3
    total_bits = 0.0
    total_energy = 0.0
    served_user_steps = 0
    hold_decisions = 0
    infeasible_hold_count = 0
    infeasible_incumbent_count = 0
    steps = 0
    action_trace: list[list[int]] = []
    per_step_power: list[float] = []
    per_step_bits: list[float] = []
    per_step_served: list[int] = []
    oracle_notes: dict[str, Any] = {
        "nonpositive_candidate_sinr": 0,
        "censored_legal_actions": {f"k{k}": 0 for k in HORIZON_OFFSETS},
        "ops3_chi_zero_legal_actions": {f"h{k}": 0 for k in HORIZON_OFFSETS},
        "ops3_below_horizon_legal_actions": {f"h{k}": 0 for k in HORIZON_OFFSETS},
        "ops3_horizon_t_by_step": [],
        "ops3_ratio_check_samples": 0,
        "ops3_ratio_check_max_rel_error": 0.0,
        "legal_actions": 0,
        "continuing_legal_actions": 0,
        "step_zero_context_steps": 0,
    }
    reference_deltas: list[float] = []
    # uid -> (pair, predicted p_a(1) in W, origin decision step)
    pending_prediction: dict[int, tuple[tuple[int, int], float, int]] = {}
    previous_served_pair: dict[int, tuple[int, int]] = {}

    with torch.no_grad():
        while True:
            step_env = environment.environment
            legacy = encode_ee_axis_state(step_env, observation)
            v04 = encode_ee_axis_v04_c3_state(
                step_env,
                observation,
                interval_s=interval_s,
                kappa_bits=kappa_bits,
            )
            if not np.array_equal(legacy.action_masks, v04.action_masks):
                raise OracleScreenError("V0.3/V0.4 masks differ during the episode")
            masks = np.asarray(v04.action_masks)
            q1, _q2_old, q3 = trainer.q_values_by_route(
                np.asarray(legacy.state_matrix), np.asarray(v04.state_matrix), masks
            )
            zeros = np.zeros_like(np.asarray(q1, dtype=np.float64))
            surfaces: dict[str, np.ndarray] = {
                "Q1": np.asarray(q1, dtype=np.float64),
                "Q3": np.asarray(q3, dtype=np.float64),
                "Q2S": zeros,
                "Q2S_OPS3": np.array(zeros, copy=True),
            }
            diagnostics: dict[str, Any] | None = None
            if needs_oracle or instrument is not None:
                q2_star, q2_star_ops3, diagnostics = oracle_q2_star(
                    environment,
                    observation,
                    kappa_bits=kappa_bits,
                    interval_s=interval_s,
                    step_index=steps,
                )
                surfaces["Q2S"] = q2_star
                surfaces["Q2S_OPS3"] = q2_star_ops3
                for key, value in diagnostics["ops3_chi_zero_legal_actions"].items():
                    oracle_notes["ops3_chi_zero_legal_actions"][key] += int(value)
                for key, value in diagnostics[
                    "ops3_below_horizon_legal_actions"
                ].items():
                    oracle_notes["ops3_below_horizon_legal_actions"][key] += int(value)
                oracle_notes["ops3_horizon_t_by_step"].append(
                    int(diagnostics["ops3_horizon_t"])
                )
                ratio = diagnostics["ops3_ratio_check"]
                oracle_notes["ops3_ratio_check_samples"] += int(ratio["samples"])
                oracle_notes["ops3_ratio_check_max_rel_error"] = max(
                    float(oracle_notes["ops3_ratio_check_max_rel_error"]),
                    float(ratio["max_rel_error"]),
                )
                if main_reference is not None:
                    reference_deltas.extend(
                        _ops3_reference_delta(
                            main_reference,
                            environment,
                            observation,
                            np.asarray(diagnostics["z_ops3_bits"], dtype=np.float64),
                            masks,
                            env_rng,
                        )
                    )
                oracle_notes["nonpositive_candidate_sinr"] += int(
                    diagnostics["nonpositive_candidate_sinr"]
                )
                for key, value in diagnostics["censored_legal_actions"].items():
                    oracle_notes["censored_legal_actions"][key] += int(value)
                oracle_notes["legal_actions"] += int(diagnostics["legal_actions"])
                oracle_notes["continuing_legal_actions"] += int(
                    diagnostics["continuing_legal_actions"]
                )
                oracle_notes["step_zero_context_steps"] += int(
                    bool(diagnostics["step_zero_context"])
                )

            incumbents = _incumbent_pairs(step_env)
            actions = select_actions(surfaces, masks, policy_label)
            next_prediction: dict[int, tuple[tuple[int, int], float, int]] = {}
            if instrument is not None:
                _instrument_step(
                    instrument,
                    environment=environment,
                    surfaces=surfaces,
                    masks=masks,
                    diagnostics=diagnostics,
                    step_index=steps,
                )
                next_prediction = _collect_predictions(
                    diagnostics, actions, step_index=steps
                )

            chosen_pairs: list[tuple[int, int] | None] = []
            for uid in range(USERS):
                action = int(actions[uid])
                if action == NO_OP_ACTION:
                    chosen_pairs.append(None)
                    continue
                chosen_pairs.append(
                    (
                        int(step_env._candidates.slot_tables[uid].norad_ids[action]),
                        int(step_env._candidates.slot_tables[uid].cell_ids[action]),
                    )
                )
            held = [
                bool(
                    chosen_pairs[uid] is not None
                    and incumbents[uid] is not None
                    and chosen_pairs[uid] == incumbents[uid]
                )
                for uid in range(USERS)
            ]
            hold_decisions += int(sum(held))

            action_trace.append([int(value) for value in actions.tolist()])
            result = environment.step(actions, env_rng)
            outcome = environment.last_outcome
            rates, power = _validate_physics(outcome)
            step_bits = float(math.fsum(float(value) for value in rates)) * interval_s
            total_bits += step_bits
            total_energy += power * interval_s
            served_user_steps += int(outcome.resolution.served_count)
            per_step_power.append(power)
            per_step_bits.append(step_bits)
            per_step_served.append(int(outcome.resolution.served_count))
            outage = np.asarray(outcome.resolution.outage_infeasible, dtype=bool)
            infeasible_hold_count += int(np.count_nonzero(outage))
            infeasible_incumbent_count += int(
                np.count_nonzero(outage & np.array(held, dtype=bool))
            )
            if instrument is not None:
                served_now = _check_predictions(
                    instrument,
                    pending_prediction,
                    previous_served_pair,
                    outcome,
                )
                pending_prediction = next_prediction
                previous_served_pair = served_now
            steps += 1
            if result.done:
                break
            observation = outcome.observation

    five_arm._assert_hybrid_unchanged(trainer, before)
    if steps != STEPS_PER_EPISODE:
        raise OracleScreenError(
            f"TRAIN episode length drifted: expected {STEPS_PER_EPISODE}, got {steps}"
        )
    return _row(
        policy_label=policy_label,
        initialization_seed=int(initialization_seed),
        evaluation_seed=int(evaluation_seed),
        encoded=encoded,
        field=field,
        total_bits=total_bits,
        total_energy=total_energy,
        served_user_steps=served_user_steps,
        steps=steps,
        actions=action_trace,
        hold_decisions=hold_decisions,
        infeasible_hold_count=infeasible_hold_count,
        infeasible_incumbent_count=infeasible_incumbent_count,
        per_step_power_w=per_step_power,
        per_step_bits=per_step_bits,
        per_step_served=per_step_served,
        oracle_diagnostics=(
            _finalize_oracle_notes(oracle_notes, reference_deltas)
            if (needs_oracle or instrument)
            else None
        ),
        elapsed_s=time.perf_counter() - started,
    )


def evaluate_main_episode(
    trainer: Any,
    archive: Any,
    *,
    runtime: Any,
    evaluation_seed: int,
    field: KeyedFadingField,
    kappa_bits: float,
) -> dict[str, Any]:
    """Evaluate the independent frozen Main policy once per world."""

    expected = _field_for_seed(evaluation_seed)
    if field.root_digest != expected.root_digest:
        raise OracleScreenError("Main episode field is not the common keyed field")
    before = runtime.network_snapshot(trainer)
    replay_before = int(runtime.replay_size(trainer))
    started = time.perf_counter()

    environment = screen._make_environment(archive, users=USERS)
    environment.environment._fading_field = field
    env_rng, mobility_rng, _action_rng, _control_rng = screen._evaluation_rngs(
        evaluation_seed
    )
    states, masks, observation = environment.reset(env_rng, mobility_rng)
    interval_s = float(environment.environment.driver.config.ephemeris.time_step_s)
    if not math.isfinite(interval_s) or interval_s <= 0.0:
        raise OracleScreenError("TRAIN interval is not finite and positive")
    encoded = _encode_world(
        environment, observation, interval_s=interval_s, kappa_bits=kappa_bits
    )

    total_bits = 0.0
    total_energy = 0.0
    served_user_steps = 0
    hold_decisions = 0
    infeasible_hold_count = 0
    infeasible_incumbent_count = 0
    steps = 0
    action_trace: list[list[int]] = []
    per_step_power: list[float] = []
    per_step_bits: list[float] = []
    per_step_served: list[int] = []
    with torch.no_grad():
        while True:
            step_env = environment.environment
            actions = np.asarray(
                runtime.main_actions(
                    trainer, environment, states, masks, observation, env_rng
                ),
                dtype=np.int64,
            )
            if actions.shape != (USERS,):
                raise OracleScreenError("Main action vector has the wrong shape")
            incumbents = _incumbent_pairs(step_env)
            held = []
            for uid in range(USERS):
                action = int(actions[uid])
                if action == NO_OP_ACTION or incumbents[uid] is None:
                    held.append(False)
                    continue
                pair = (
                    int(step_env._candidates.slot_tables[uid].norad_ids[action]),
                    int(step_env._candidates.slot_tables[uid].cell_ids[action]),
                )
                held.append(pair == incumbents[uid])
            hold_decisions += int(sum(held))

            action_trace.append([int(value) for value in actions.tolist()])
            result = environment.step(actions, env_rng)
            outcome = environment.last_outcome
            rates, power = _validate_physics(outcome)
            step_bits = float(math.fsum(float(value) for value in rates)) * interval_s
            total_bits += step_bits
            total_energy += power * interval_s
            served_user_steps += int(outcome.resolution.served_count)
            per_step_power.append(power)
            per_step_bits.append(step_bits)
            per_step_served.append(int(outcome.resolution.served_count))
            outage = np.asarray(outcome.resolution.outage_infeasible, dtype=bool)
            infeasible_hold_count += int(np.count_nonzero(outage))
            infeasible_incumbent_count += int(
                np.count_nonzero(outage & np.array(held, dtype=bool))
            )
            steps += 1
            if result.done:
                break
            states = result.user_states
            masks = result.action_masks
            observation = outcome.observation

    if not runtime.networks_equal(trainer, before):
        raise OracleScreenError("Main network parameters changed during evaluation")
    if int(runtime.replay_size(trainer)) != replay_before:
        raise OracleScreenError("Main replay changed during evaluation")
    if steps != STEPS_PER_EPISODE:
        raise OracleScreenError(
            f"TRAIN episode length drifted: expected {STEPS_PER_EPISODE}, got {steps}"
        )
    return _row(
        policy_label="MAIN",
        initialization_seed=None,
        evaluation_seed=int(evaluation_seed),
        encoded=encoded,
        field=field,
        total_bits=total_bits,
        total_energy=total_energy,
        served_user_steps=served_user_steps,
        steps=steps,
        actions=action_trace,
        hold_decisions=hold_decisions,
        infeasible_hold_count=infeasible_hold_count,
        infeasible_incumbent_count=infeasible_incumbent_count,
        per_step_power_w=per_step_power,
        per_step_bits=per_step_bits,
        per_step_served=per_step_served,
        oracle_diagnostics=None,
        elapsed_s=time.perf_counter() - started,
    )


# --------------------------------------------------------------------------
# Smoke instrumentation and self-checks
# --------------------------------------------------------------------------


def _instrument_step(
    instrument: dict[str, Any],
    *,
    environment: Any,
    surfaces: Mapping[str, np.ndarray],
    masks: np.ndarray,
    diagnostics: Mapping[str, Any] | None,
    step_index: int,
) -> None:
    """Self-check (i), the one-step surface statistics, and self-check (iii)."""

    if diagnostics is None:
        return
    step_env = environment.environment
    driver = step_env.driver
    legal = np.asarray(masks, dtype=bool)

    # (i) G_a(0) from an independent geometry pass vs the candidate table.
    table_norads, table_positions = _positions_for_offset(driver, 0)
    norad_ids = np.asarray(diagnostics["norad_ids"])
    cell_ids = np.asarray(diagnostics["cell_ids"])
    satellite_ecef, tracked = _gather_positions(
        norad_ids, table_norads, table_positions
    )
    user_ecef = np.asarray(driver.user_ecef_km(), dtype=np.float64)[:, None, :]
    grid_centres = np.asarray(driver.grid.centers_ecef_km, dtype=np.float64)
    cell_ecef = grid_centres[np.where(cell_ids >= 0, cell_ids, 0)]
    theta_own, _slant, _elevation = _geometry(satellite_ecef, user_ecef, cell_ecef)
    gain_own = np.asarray(transmit_gain_linear(np.where(legal, theta_own, 0.0)))
    gain_table = np.asarray(diagnostics["gain0"])
    where = legal & tracked
    if np.any(where):
        reference = np.abs(gain_table[where])
        error = np.abs(gain_own[where] - gain_table[where]) / np.maximum(
            reference, 1e-300
        )
        instrument["gain_check_max_rel_error"] = max(
            instrument.get("gain_check_max_rel_error", 0.0), float(np.max(error))
        )
        theta_error = np.abs(
            theta_own[where] - np.asarray(diagnostics["theta0_deg"])[where]
        )
        instrument["theta_check_max_abs_error_deg"] = max(
            instrument.get("theta_check_max_abs_error_deg", 0.0),
            float(np.max(theta_error)),
        )
        instrument["gain_check_samples"] = instrument.get(
            "gain_check_samples", 0
        ) + int(np.count_nonzero(where))

    # One-step surface statistics: Q2* against Q1+Q3, and the argmax flip rate.
    if step_index == instrument.get("surface_step", 1):
        q2 = np.asarray(surfaces["Q2S"], dtype=np.float64)
        base = np.asarray(surfaces["Q1"], dtype=np.float64) + np.asarray(
            surfaces["Q3"], dtype=np.float64
        )
        legal_q2 = q2[legal]
        legal_base = base[legal]
        without = np.argmax(np.where(legal, base, -np.inf), axis=1)
        with_oracle = np.argmax(np.where(legal, base + q2, -np.inf), axis=1)
        instrument["surface_stats"] = {
            "step_index": int(step_index),
            "q2_star_min": float(np.min(legal_q2)),
            "q2_star_median": float(np.median(legal_q2)),
            "q2_star_max": float(np.max(legal_q2)),
            "q1_plus_q3_min": float(np.min(legal_base)),
            "q1_plus_q3_median": float(np.median(legal_base)),
            "q1_plus_q3_max": float(np.max(legal_base)),
            "zeta_bits_median": float(
                np.median(np.asarray(diagnostics["zeta_bits"])[legal])
            ),
            "argmax_flip_fraction": float(np.mean(without != with_oracle)),
            "legal_actions": int(np.count_nonzero(legal)),
        }
        instrument["route_actions_parity"] = _route_actions_parity(
            surfaces, legal, np.asarray(diagnostics["gain0"])
        )


def _collect_predictions(
    diagnostics: Mapping[str, Any] | None,
    actions: np.ndarray,
    *,
    step_index: int,
) -> dict[int, tuple[tuple[int, int], float, int]]:
    """Record ``p_a(1)`` for the action chosen now, to check at the next step."""

    if diagnostics is None:
        return {}
    block = diagnostics.get("predicted_power_k1") or {}
    predicted = block.get("power_w")
    if predicted is None:
        return {}
    norad_ids = np.asarray(diagnostics["norad_ids"])
    cell_ids = np.asarray(diagnostics["cell_ids"])
    out: dict[int, tuple[tuple[int, int], float, int]] = {}
    for uid in range(len(actions)):
        action = int(actions[uid])
        if action == NO_OP_ACTION:
            continue
        value = float(predicted[uid, action])
        if not math.isfinite(value) or value <= 0.0:
            continue
        out[uid] = (
            (int(norad_ids[uid, action]), int(cell_ids[uid, action])),
            value,
            int(step_index),
        )
    return out


def _check_predictions(
    instrument: dict[str, Any],
    pending: Mapping[int, tuple[tuple[int, int], float, int]],
    previous_served_pair: Mapping[int, tuple[int, int]],
    outcome: Any,
) -> dict[int, tuple[int, int]]:
    """(ii) realized ``p(t+1)`` vs the ``p_a(1)`` predicted one step earlier.

    Only users whose segment genuinely continued are compared: they must have
    been *served* on the pair at the origin step and served on the same pair
    here.  Predictions whose origin is step 0 are bucketed separately because
    the environment warm-starts step-0 segments at a historical
    ``G^T(theta(tau))`` the decision-time oracle cannot see.
    """

    served = np.asarray(outcome.resolution.served, dtype=bool)
    satellites = np.asarray(outcome.resolution.serving_satellite, dtype=np.int64)
    cells = np.asarray(outcome.resolution.serving_cell, dtype=np.int64)
    realised = np.asarray(outcome.link_power_w, dtype=np.float64)
    for uid, (pair, predicted, origin) in pending.items():
        if not bool(served[uid]):
            continue
        if (int(satellites[uid]), int(cells[uid])) != pair:
            continue
        if previous_served_pair.get(uid) != pair:
            continue
        bucket = "power_rel_errors" if origin >= 1 else "power_rel_errors_step0_origin"
        instrument.setdefault(bucket, []).append(
            abs(float(realised[uid]) - predicted) / predicted
        )
    return {
        uid: (int(satellites[uid]), int(cells[uid]))
        for uid in range(served.size)
        if bool(served[uid])
    }


class _StubTrainer:
    """Minimal object exposing only ``q_values_by_route`` for the parity test."""

    def __init__(self, q1: np.ndarray, q2: np.ndarray, q3: np.ndarray) -> None:
        self._surfaces = (q1, q2, q3)

    def q_values_by_route(self, states_v03, states_v04, masks):  # noqa: ANN001
        del states_v03, states_v04, masks
        return self._surfaces


def _route_actions_parity(
    surfaces: Mapping[str, np.ndarray], legal: np.ndarray, filler: np.ndarray
) -> dict[str, Any]:
    """(iii) P13 selection must equal ``five_arm.route_actions(..., DROP_C2)``."""

    q1 = np.asarray(surfaces["Q1"], dtype=np.float64)
    q2 = np.asarray(surfaces["Q2S"], dtype=np.float64)
    q3 = np.asarray(surfaces["Q3"], dtype=np.float64)
    stub = _StubTrainer(q1, q2, q3)
    reference = five_arm.route_actions(
        stub,
        np.zeros((q1.shape[0], 1), dtype=np.float64),
        np.zeros((q1.shape[0], 1), dtype=np.float64),
        legal,
        "DROP_C2",
    )
    mine = select_actions(surfaces, legal, "P13")
    matches = bool(np.array_equal(np.asarray(reference, dtype=np.int64), mine))
    # And with a deliberately different middle surface, to prove the parity is
    # not an accident of Q2* being small.
    scrambled = {**surfaces, "Q2S": np.asarray(filler, dtype=np.float64)}
    stub2 = _StubTrainer(q1, np.asarray(filler, dtype=np.float64), q3)
    reference2 = five_arm.route_actions(
        stub2,
        np.zeros((q1.shape[0], 1), dtype=np.float64),
        np.zeros((q1.shape[0], 1), dtype=np.float64),
        legal,
        "DROP_C2",
    )
    matches2 = bool(
        np.array_equal(
            np.asarray(reference2, dtype=np.int64), select_actions(scrambled, legal, "P13")
        )
    )
    return {
        "p13_matches_drop_c2": matches,
        "p13_matches_drop_c2_with_scrambled_middle": matches2,
        "users": int(q1.shape[0]),
    }


# --------------------------------------------------------------------------
# Aggregation
# --------------------------------------------------------------------------


def _ops3_ratio_rollup(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Addendum A self-check: OPS-3 == H-A / 3 at unpenalised full horizons.

    At an anchor with ``H_t = 3`` where every ``chi_a(h) = 1`` (so H-A is also
    uncensored), the two aggregations differ only by the ``1/H_t`` factor.
    """

    samples = 0
    worst = 0.0
    arms: list[str] = []
    for row in rows:
        notes = row.get("oracle_diagnostics") or {}
        count = int(notes.get("ops3_ratio_check_samples", 0) or 0)
        if count <= 0:
            continue
        samples += count
        worst = max(worst, float(notes.get("ops3_ratio_check_max_rel_error", 0.0)))
        arms.append(str(row.get("policy_label")))
    return {
        "statement": "Q2*_OPS3 == Q2*_HA / 3 where H_t = 3 and every chi = 1",
        "samples": samples,
        "max_rel_error": worst,
        "tolerance": 1e-12,
        "passed": bool(samples > 0 and worst <= 1e-12),
        "arms_contributing": sorted(set(arms)),
    }


def _pool(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "episodes": 0,
            "total_bits": 0.0,
            "total_energy_j": 0.0,
            "ratio_of_sums_ee_bits_per_j": None,
            "served_fraction": None,
            "hold_fraction": None,
            "infeasible_hold_count": 0,
        }
    bits = math.fsum(float(row["total_bits"]) for row in rows)
    energy = math.fsum(float(row["total_energy_j"]) for row in rows)
    served = sum(int(row["served_user_steps"]) for row in rows)
    decisions = sum(int(row["decision_count"]) for row in rows)
    holds = sum(int(row["hold_decisions"]) for row in rows)
    infeasible = sum(int(row["infeasible_hold_count"]) for row in rows)
    incumbent_infeasible = sum(
        int(row["infeasible_on_incumbent_count"]) for row in rows
    )
    return {
        "episodes": len(rows),
        "total_bits": bits,
        "total_energy_j": energy,
        "ratio_of_sums_ee_bits_per_j": bits / energy if energy > 0.0 else None,
        "served_user_steps": served,
        "decision_count": decisions,
        "served_fraction": served / decisions if decisions else None,
        "hold_decisions": holds,
        "hold_fraction": holds / decisions if decisions else None,
        "infeasible_hold_count": infeasible,
        "infeasible_on_incumbent_count": incumbent_infeasible,
        "mean_elapsed_s": float(np.mean([float(row["elapsed_s"]) for row in rows])),
    }


def _contrast(
    left: Mapping[str, Any], right: Mapping[str, Any], *, left_arm: str, right_arm: str
) -> dict[str, Any]:
    lhs = left.get("ratio_of_sums_ee_bits_per_j")
    rhs = right.get("ratio_of_sums_ee_bits_per_j")
    delta = None if lhs is None or rhs is None else float(lhs - rhs)
    relative = (
        None if delta is None or not rhs else float(delta / rhs)
    )
    lserved = left.get("served_fraction")
    rserved = right.get("served_fraction")
    return {
        "left_arm": left_arm,
        "right_arm": right_arm,
        "role": CONTRAST_ROLE.get((left_arm, right_arm), "diagnostic_lattice_pair"),
        "left_ee_bits_per_j": lhs,
        "right_ee_bits_per_j": rhs,
        "delta_ee_bits_per_j": delta,
        "relative_delta_ee": relative,
        "left_served_fraction": lserved,
        "right_served_fraction": rserved,
        "delta_served_fraction": (
            None if lserved is None or rserved is None else float(lserved - rserved)
        ),
        "left_hold_fraction": left.get("hold_fraction"),
        "right_hold_fraction": right.get("hold_fraction"),
        "delta_hold_fraction": (
            None
            if left.get("hold_fraction") is None or right.get("hold_fraction") is None
            else float(left["hold_fraction"] - right["hold_fraction"])
        ),
        "left_episodes": left.get("episodes"),
        "right_episodes": right.get("episodes"),
    }


def _all_pairs(arms: Sequence[str]) -> tuple[tuple[str, str], ...]:
    named = tuple(pair for pair in NAMED_CONTRASTS if pair[0] in arms and pair[1] in arms)
    seen = {frozenset(pair) for pair in named}
    extra: list[tuple[str, str]] = []
    order = [arm for arm in ARM_ORDER if arm in arms]
    for left, right in itertools.combinations(order, 2):
        if frozenset((left, right)) in seen:
            continue
        extra.append((left, right))
    return (*named, *tuple(extra))


def _paired_world_bootstrap(
    rows_by_arm: Mapping[str, Sequence[Mapping[str, Any]]],
    worlds: Sequence[int],
    pairs: Sequence[tuple[str, str]],
) -> dict[str, Any]:
    """Resample WORLDS with replacement; recompute each arm's ratio of sums.

    Reported only.  The screen's decision inputs are the pooled contrasts.
    """

    if len(worlds) < 2:
        return {
            "replicates": 0,
            "note": "fewer than two worlds; a paired-world bootstrap is undefined",
            "contrasts": {},
        }
    index: dict[str, dict[int, tuple[float, float]]] = {}
    for arm, rows in rows_by_arm.items():
        per_world: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
        for row in rows:
            per_world[int(row["evaluation_seed"])].append(row)
        index[arm] = {
            world: (
                math.fsum(float(r["total_bits"]) for r in items),
                math.fsum(float(r["total_energy_j"]) for r in items),
            )
            for world, items in per_world.items()
        }
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    order = list(worlds)
    draws = rng.integers(0, len(order), size=(BOOTSTRAP_REPLICATES, len(order)))
    out: dict[str, Any] = {}
    for left, right in pairs:
        if left not in index or right not in index:
            continue
        samples = np.empty(BOOTSTRAP_REPLICATES, dtype=np.float64)
        for replicate in range(BOOTSTRAP_REPLICATES):
            picked = [order[i] for i in draws[replicate]]
            lb = math.fsum(index[left][world][0] for world in picked)
            le = math.fsum(index[left][world][1] for world in picked)
            rb = math.fsum(index[right][world][0] for world in picked)
            re = math.fsum(index[right][world][1] for world in picked)
            samples[replicate] = (lb / le) - (rb / re)
        out[f"{left}_vs_{right}"] = {
            "mean": float(np.mean(samples)),
            "median": float(np.median(samples)),
            "ci_2p5": float(np.percentile(samples, 2.5)),
            "ci_97p5": float(np.percentile(samples, 97.5)),
            "fraction_positive": float(np.mean(samples > 0.0)),
        }
    return {
        "replicates": BOOTSTRAP_REPLICATES,
        "rng": "numpy.default_rng",
        "seed": BOOTSTRAP_SEED,
        "resampling_unit": "evaluation_seed (world), paired across arms",
        "statistic": "difference of pooled ratio-of-sums EE (bit/J)",
        "decision_input": False,
        "contrasts": out,
    }


def build_summaries(
    rows_by_arm: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    worlds: Sequence[int],
    lineages: Sequence[int],
) -> dict[str, Any]:
    arms = [arm for arm in ARM_ORDER if arm in rows_by_arm]
    pooled = {arm: _pool(list(rows_by_arm[arm])) for arm in arms}
    per_lineage: dict[str, dict[str, Any]] = {}
    for arm in arms:
        per_lineage[arm] = {}
        for lineage in lineages:
            if arm == "MAIN":
                subset = list(rows_by_arm[arm])
            else:
                subset = [
                    row
                    for row in rows_by_arm[arm]
                    if int(row["initialization_seed"]) == int(lineage)
                ]
            per_lineage[arm][str(lineage)] = _pool(subset)
    per_world: dict[str, dict[str, Any]] = {}
    for arm in arms:
        per_world[arm] = {
            str(world): _pool(
                [row for row in rows_by_arm[arm] if int(row["evaluation_seed"]) == world]
            )
            for world in worlds
        }

    pairs = _all_pairs(arms)
    contrasts_pooled = [
        _contrast(pooled[left], pooled[right], left_arm=left, right_arm=right)
        for left, right in pairs
    ]
    contrasts_lineage = {
        str(lineage): [
            _contrast(
                per_lineage[left][str(lineage)],
                per_lineage[right][str(lineage)],
                left_arm=left,
                right_arm=right,
            )
            for left, right in pairs
        ]
        for lineage in lineages
    }
    contrasts_world = {
        str(world): [
            _contrast(
                per_world[left][str(world)],
                per_world[right][str(world)],
                left_arm=left,
                right_arm=right,
            )
            for left, right in pairs
        ]
        for world in worlds
    }
    bootstrap = _paired_world_bootstrap(
        rows_by_arm,
        worlds,
        [pair for pair in PRIMARY_CONTRASTS if pair[0] in arms and pair[1] in arms],
    )
    return {
        "arms": arms,
        "contrast_pairs": [list(pair) for pair in pairs],
        "pooled_by_arm": pooled,
        "pooled_by_arm_and_initialization": per_lineage,
        "pooled_by_arm_and_world": per_world,
        "contrasts_pooled": contrasts_pooled,
        "contrasts_by_initialization": contrasts_lineage,
        "contrasts_by_world": contrasts_world,
        "paired_world_bootstrap": bootstrap,
    }


# --------------------------------------------------------------------------
# Execution
# --------------------------------------------------------------------------


def _load_world(
    *,
    tle_root: Path,
    prereg_path: Path,
    gate_dir: Path,
    source_dir: Path,
    v03_root: Path,
    main_dir: Path,
    temporary: Path,
    lineages: Sequence[int],
    need_main: bool,
    need_route: bool,
    need_main_reference: bool,
    source_closure: str,
) -> dict[str, Any]:
    runtime = source._default_runtime()
    record = read_prereg(prereg_path)
    archive = screen._frozen_archive(record, Path(tle_root), temporary / "frozen-tle")

    # ``source_dir`` re-runs the V0.4 *source-construction* closure check.  In a
    # tree that has grown V0.5-V0.7 modules that check cannot pass, and it is
    # not this screen's authority: no C3 dataset is constructed here.  Both
    # modes still SHA-verify the gate authority/result seals, the three
    # selected hybrid checkpoint files, the Main checkpoint, and the frozen
    # TLE/PREREG binding.  The mode is recorded in the result either way.
    closure_note: str | None = None
    if source_closure == "require":
        gate_receipt = screen.authenticate_gate(
            Path(gate_dir), source_dir=Path(source_dir), prereg_path=Path(prereg_path)
        )
    elif source_closure == "receipt-only":
        try:
            screen.authenticate_gate(
                Path(gate_dir),
                source_dir=Path(source_dir),
                prereg_path=Path(prereg_path),
            )
            closure_note = "source closure re-check PASSED even though it was not required"
        except Exception as error:  # noqa: BLE001 - recorded, not swallowed
            closure_note = f"source closure re-check FAILED and was not required: {error}"
        gate_receipt = screen.authenticate_gate(
            Path(gate_dir), source_dir=None, prereg_path=Path(prereg_path)
        )
    else:
        raise OracleScreenError(f"unknown source-closure mode: {source_closure}")
    if closure_note:
        print(f"[source-closure] {closure_note}")
    if gate_receipt.get("selected_q3_rung") != SELECTED_Q3_RUNG:
        raise OracleScreenError("gate receipt is not the selected rung 100")

    checkpoints: dict[str, str] = {}
    main_trainer = None
    main_meta: Mapping[str, Any] = {}
    if need_main or need_main_reference:
        main_trainer, main_meta = runtime.load_trainer(
            record, archive, run_dir=Path(main_dir), users=USERS
        )
        if not isinstance(main_meta, Mapping):
            raise OracleScreenError("Main loader returned no metadata")
        checkpoints["main"] = str(main_meta.get("checkpoint_sha256"))
        if checkpoints["main"] != five_arm.EXPECTED_MAIN_CHECKPOINT_SHA256:
            raise OracleScreenError(
                "loaded Main checkpoint is not the exact frozen checkpoint"
            )

    hybrids: dict[int, Any] = {}
    if need_route:
        selected = gate_receipt.get("selected_hybrid_paths") or {}
        for lineage in lineages:
            trainer = screen.load_gate_selected_hybrid(
                gate_receipt, v03_root=Path(v03_root), initialization_seed=int(lineage)
            )
            five_arm._prepare_hybrid(trainer)
            hybrids[int(lineage)] = trainer
            path = selected.get(str(int(lineage)))
            if path is not None:
                checkpoints[f"hybrid_{lineage}"] = _file_sha256(Path(path))
                checkpoints[f"hybrid_{lineage}_path"] = str(Path(path))
            for index, lineage_entry in enumerate(trainer.frozen_lineage):
                entry = lineage_entry.as_dict()
                checkpoints[
                    f"v03_frozen_{lineage}_head{entry.get('head_index', index)}"
                ] = str(entry.get("checkpoint_sha256"))
    return {
        "runtime": runtime,
        "record": record,
        "archive": archive,
        "gate_receipt": gate_receipt,
        "main_trainer": main_trainer,
        "main_meta": dict(main_meta) if main_meta else {},
        "hybrids": hybrids,
        "checkpoint_sha256": checkpoints,
        "source_closure_mode": source_closure,
        "source_closure_note": closure_note,
    }


def execute(
    *,
    mode: str,
    seeds: Sequence[int],
    lineages: Sequence[int],
    arms: Sequence[str],
    output_dir: Path,
    contract_sha256: str,
    tle_root: Path,
    prereg_path: Path,
    gate_dir: Path,
    source_dir: Path,
    v03_root: Path,
    main_dir: Path,
    instrument: bool,
    source_closure: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    started_utc = dt.datetime.now(dt.timezone.utc).isoformat()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    unknown = [arm for arm in arms if arm not in ARMS]
    if unknown:
        raise OracleScreenError(f"unknown arms requested: {unknown}")
    route_arms = [arm for arm in ARM_ORDER if arm in arms and arm != "MAIN"]
    need_main = "MAIN" in arms
    need_route = bool(route_arms)
    # The frozen Main policy is additionally loaded, read-only, whenever an
    # OPS-3 arm runs: Addendum A asks for Z_a - Z_{a^M} as a diagnostic.
    need_main_reference = any(arm in OPS3_SURFACE_ARMS for arm in route_arms)

    if mode == "run" and any(int(seed) in PREREG_BLOCK_SEEDS for seed in seeds):
        print(
            "[note] the requested seeds intersect the preregistered block "
            f"{PREREG_BLOCK_SEEDS[0]}..{PREREG_BLOCK_SEEDS[-1]}; the controller "
            "must freeze the contract before this is a preregistered run."
        )

    rows_by_arm: dict[str, list[dict[str, Any]]] = {arm: [] for arm in arms}
    instrument_state: dict[str, Any] = {"surface_step": 1} if instrument else {}
    timings: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="mcrl-v08-c2-oracle-tle-") as temporary:
        loaded = _load_world(
            tle_root=Path(tle_root),
            prereg_path=Path(prereg_path),
            gate_dir=Path(gate_dir),
            source_dir=Path(source_dir),
            v03_root=Path(v03_root),
            main_dir=Path(main_dir),
            temporary=Path(temporary),
            lineages=lineages,
            need_main=need_main,
            need_route=need_route,
            need_main_reference=need_main_reference,
            source_closure=source_closure,
        )
        runtime = loaded["runtime"]
        archive = loaded["archive"]
        hybrids = loaded["hybrids"]
        main_trainer = loaded["main_trainer"]
        kappa_bits = float(gate._config_pair()[1].kappa_bits)
        if kappa_bits != KAPPA_BITS_SOURCE:
            raise OracleScreenError(
                "gate kappa_bits does not equal the sealed source-runner constant"
            )
        for lineage, trainer in hybrids.items():
            if float(trainer.v04_config.kappa_bits) != KAPPA_BITS_SOURCE:
                raise OracleScreenError(
                    f"hybrid {lineage} kappa_bits is not the sealed constant"
                )
        if LAMBDA0_BITS_PER_J != float.fromhex("0x1.443a8f481639ap+26"):
            raise OracleScreenError("lambda0 is not the sealed TRAIN-only constant")
        if LAMBDA0_BITS_PER_J != float(D2_LAMBDA_BITS_PER_J):
            raise OracleScreenError("lambda0 disagrees between its two sealed sources")

        main_before = (
            runtime.network_snapshot(main_trainer) if main_trainer is not None else None
        )
        main_replay_before = (
            int(runtime.replay_size(main_trainer)) if main_trainer is not None else 0
        )
        hybrid_before = {
            lineage: five_arm._snapshot_hybrid(trainer)
            for lineage, trainer in hybrids.items()
        }

        for evaluation_seed in seeds:
            field = _field_for_seed(int(evaluation_seed))
            if need_main:
                row = evaluate_main_episode(
                    main_trainer,
                    archive,
                    runtime=runtime,
                    evaluation_seed=int(evaluation_seed),
                    field=field,
                    kappa_bits=kappa_bits,
                )
                rows_by_arm["MAIN"].append(row)
                timings.append(
                    {
                        "policy_label": "MAIN",
                        "evaluation_seed": int(evaluation_seed),
                        "initialization_seed": None,
                        "elapsed_s": row["elapsed_s"],
                    }
                )
                print(
                    f"  [{evaluation_seed}] MAIN            "
                    f"EE={row['ratio_of_sums_ee_bits_per_j']:.6g} "
                    f"served={row['served_fraction']:.4f} "
                    f"hold={row['hold_fraction']:.4f} "
                    f"{row['elapsed_s']:.2f}s"
                )
            for lineage in lineages:
                trainer = hybrids[int(lineage)]
                for arm in route_arms:
                    row = evaluate_route_episode(
                        trainer,
                        archive,
                        evaluation_seed=int(evaluation_seed),
                        initialization_seed=int(lineage),
                        policy_label=arm,
                        field=field,
                        instrument=(
                            instrument_state
                            if instrument and arm == "P123" else None
                        ),
                        main_reference=(
                            (runtime, main_trainer)
                            if (arm in OPS3_SURFACE_ARMS and main_trainer is not None)
                            else None
                        ),
                    )
                    rows_by_arm[arm].append(row)
                    timings.append(
                        {
                            "policy_label": arm,
                            "evaluation_seed": int(evaluation_seed),
                            "initialization_seed": int(lineage),
                            "elapsed_s": row["elapsed_s"],
                        }
                    )
                    print(
                        f"  [{evaluation_seed}/{lineage}] {arm:<6}     "
                        f"EE={row['ratio_of_sums_ee_bits_per_j']:.6g} "
                        f"served={row['served_fraction']:.4f} "
                        f"hold={row['hold_fraction']:.4f} "
                        f"{row['elapsed_s']:.2f}s"
                    )

        if main_trainer is not None:
            if not runtime.networks_equal(main_trainer, main_before):
                raise OracleScreenError("Main parameters changed during the screen")
            if int(runtime.replay_size(main_trainer)) != main_replay_before:
                raise OracleScreenError("Main replay changed during the screen")
        for lineage, trainer in hybrids.items():
            five_arm._assert_hybrid_unchanged(trainer, hybrid_before[lineage])

    elapsed = time.perf_counter() - started
    summaries = build_summaries(
        rows_by_arm, worlds=[int(seed) for seed in seeds], lineages=[int(x) for x in lineages]
    )
    all_rows = [row for arm in ARM_ORDER if arm in rows_by_arm for row in rows_by_arm[arm]]

    result: dict[str, Any] = {
        "schema": RESULT_SCHEMA,
        "mode": mode,
        "status": "ORACLE_SCREEN_COMPLETE",
        "claim_ceiling": (
            "V08_C2_ORACLE_FORMULA_INTERACTION_SCREEN_ONLY_"
            "NOT_A_PREREGISTERED_EE_EFFICACY_CLAIM"
        ),
        "contract_sha256": str(contract_sha256),
        "code_file_sha256": _file_sha256(Path(__file__).resolve()),
        "code_file": str(Path(__file__).resolve()),
        "started_utc": started_utc,
        "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "elapsed_s": float(elapsed),
        "evaluation_split": EVALUATION_SPLIT,
        "test_split_opened": TEST_SPLIT_OPENED,
        "episode_training": EPISODE_TRAINING,
        "users": USERS,
        "steps_per_episode": STEPS_PER_EPISODE,
        "selected_q3_rung": SELECTED_Q3_RUNG,
        "arms": list(arms),
        "route_arms": route_arms,
        "active_routes": {arm: list(ACTIVE_ROUTES[arm]) for arm in route_arms},
        "evaluation_seeds": [int(seed) for seed in seeds],
        "initialization_seeds": [int(value) for value in lineages],
        "episode_count": len(all_rows),
        "learned_q2_used": False,
        "main_loaded_for_ops3_reference_diagnostic": bool(need_main_reference),
        "ops3_surface_arms": sorted(a for a in route_arms if a in OPS3_SURFACE_ARMS),
        "ha_surface_arms": sorted(a for a in route_arms if a in HA_SURFACE_ARMS),
        "oracle": {
            "field_component": FIELD_COMPONENT,
            "field_excluded_components": list(FIELD_EXCLUDED_COMPONENTS),
            "horizon_offsets": list(HORIZON_OFFSETS),
            "ops3_horizon_rule": "H_t = min(3, 9 - t); Z = 0 when H_t = 0",
            "ops3_chi": (
                "1[G_a(h) > 0] * 1[p_a(h) <= 1.65 W] * "
                "1[projected elevation of s_a toward u at t+h > 0 deg]"
            ),
            "ops3_aggregation": (
                "Z_a = (1/H_t) sum_h [ chi dt (R - lambda0 P) - (1-chi) kappa ]; "
                "Q2*_OPS3 = Z_a / kappa; reference row Z_{a^M} NOT subtracted "
                "in the deployed surface (per-state constant), reported only "
                "as a diagnostic"
            ),
            "p0_w": P0_W,
            "beam_power_max_w": P_MAX_W,
            "beam_bandwidth_hz": float(BEAM_BANDWIDTH_HZ),
            "noise_power_w": NOISE_W,
            "circuit_power_per_beam_w": float(CIRCUIT_POWER_PER_BEAM_W),
            "baseband_power_per_satellite_w": float(BASEBAND_POWER_PER_SATELLITE_W),
            "rx_gain_max_linear": RX_GAIN_MAX_LINEAR,
            "lambda0_bits_per_j": LAMBDA0_BITS_PER_J,
            "lambda0_hex": LAMBDA0_HEX,
            "lambda0_sources": list(LAMBDA0_SOURCES),
            "kappa_bits": KAPPA_BITS_SOURCE,
            "kappa_bits_hex": KAPPA_BITS_SOURCE.hex(),
            "kappa_bits_source": ".scratch/c3-v04/run_v04_c3_source.py:KAPPA_BITS",
            "user_position_approximation": (
                "future off-axis angles and slant ranges use the CURRENT user ECEF; "
                "users move ~250 m per 30.08 s step"
            ),
            "interference_convention": (
                "I+N frozen at decision time by inverting the observation gamma block "
                "with fade=1 and shadow=0 dB"
            ),
        },
        "checkpoint_sha256": loaded["checkpoint_sha256"],
        "source_closure_mode": loaded["source_closure_mode"],
        "source_closure_note": loaded["source_closure_note"],
        "physics_code_sha256": {
            name: _file_sha256(REPO / name) for name in PHYSICS_CODE_PATHS
        },
        "main_checkpoint_meta": {
            key: value
            for key, value in loaded["main_meta"].items()
            if isinstance(value, (str, int, float, bool)) or value is None
        },
        "gate_authority_sha256": loaded["gate_receipt"].get("authority_sha256"),
        "keyed_fields": {
            str(int(seed)): common_field_receipt(int(seed)) for seed in seeds
        },
        "timings": timings,
        "summaries": summaries,
        "ops3_ratio_self_check": _ops3_ratio_rollup(all_rows),
        "rows": all_rows,
    }
    if instrument:
        errors = instrument_state.get("power_rel_errors") or []
        step0 = instrument_state.get("power_rel_errors_step0_origin") or []
        result["self_checks"] = {
            "gain_check_max_rel_error": instrument_state.get(
                "gain_check_max_rel_error"
            ),
            "theta_check_max_abs_error_deg": instrument_state.get(
                "theta_check_max_abs_error_deg"
            ),
            "gain_check_samples": instrument_state.get("gain_check_samples"),
            "power_prediction_samples": len(errors),
            "power_prediction_median_rel_error": (
                float(np.median(errors)) if errors else None
            ),
            "power_prediction_p95_rel_error": (
                float(np.percentile(errors, 95.0)) if errors else None
            ),
            "power_prediction_max_rel_error": (float(np.max(errors)) if errors else None),
            "power_prediction_step0_origin_samples": len(step0),
            "power_prediction_step0_origin_median_rel_error": (
                float(np.median(step0)) if step0 else None
            ),
            "power_prediction_step0_origin_p95_rel_error": (
                float(np.percentile(step0, 95.0)) if step0 else None
            ),
            "surface_stats": instrument_state.get("surface_stats"),
            "route_actions_parity": instrument_state.get("route_actions_parity"),
        }

    result_path = output / "result.json"
    with open(result_path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True, default=float)
        handle.write("\n")
    rows_path = output / "rows.jsonl"
    with open(rows_path, "w", encoding="utf-8") as handle:
        for row in all_rows:
            handle.write(
                json.dumps(row, sort_keys=True, separators=(",", ":"), default=float)
            )
            handle.write("\n")
    result["result_file_sha256"] = _file_sha256(result_path)
    result["rows_file_sha256"] = _file_sha256(rows_path)
    print(f"\nwrote {result_path}")
    print(f"wrote {rows_path}")
    return result


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _report(result: Mapping[str, Any]) -> None:
    summaries = result["summaries"]
    print("\n=== per-arm pooled (ratio of sums) ===")
    print(f"{'arm':<6} {'episodes':>8} {'EE bit/J':>14} {'served':>8} {'hold':>8} {'infeas':>8}")
    for arm in summaries["arms"]:
        pooled = summaries["pooled_by_arm"][arm]
        print(
            f"{arm:<6} {pooled['episodes']:>8} "
            f"{pooled['ratio_of_sums_ee_bits_per_j']:>14.6g} "
            f"{pooled['served_fraction']:>8.4f} {pooled['hold_fraction']:>8.4f} "
            f"{pooled['infeasible_hold_count']:>8}"
        )
    print("\n=== named contrasts (pooled) ===")
    for entry in summaries["contrasts_pooled"]:
        if entry["role"] == "diagnostic_lattice_pair":
            continue
        delta = entry["delta_ee_bits_per_j"]
        relative = entry["relative_delta_ee"]
        print(
            f"{entry['left_arm']:>5} - {entry['right_arm']:<5} "
            f"dEE={delta:+.6g} ({relative:+.4%})  "
            f"dserved={entry['delta_served_fraction']:+.4f}  [{entry['role']}]"
        )
    check = result.get("ops3_ratio_self_check") or {}
    if check.get("samples"):
        print(
            f"\nOPS-3 vs H-A ratio self-check: {check['statement']} -> "
            f"max rel error {check['max_rel_error']:.3e} over "
            f"{check['samples']} legal actions, passed={check['passed']}"
        )
    bootstrap = summaries["paired_world_bootstrap"]
    if bootstrap.get("contrasts"):
        print("\n=== paired-world bootstrap (report only, not a decision input) ===")
        for key, block in bootstrap["contrasts"].items():
            print(
                f"{key:<14} mean={block['mean']:+.6g} "
                f"CI95=[{block['ci_2p5']:+.6g}, {block['ci_97p5']:+.6g}] "
                f"P(>0)={block['fraction_positive']:.3f}"
            )


def _report_self_checks(result: Mapping[str, Any]) -> None:
    checks = result.get("self_checks") or {}
    print("\n=== self-checks ===")
    print(
        "(i)   G_a(0) geometry parity: max |rel err| = "
        f"{checks.get('gain_check_max_rel_error')!r} over "
        f"{checks.get('gain_check_samples')!r} legal slots; "
        f"max |theta err| = {checks.get('theta_check_max_abs_error_deg')!r} deg"
    )
    print(
        "(ii)  realized p(t+1) vs predicted p_a(1) on continued segments (origin t>=1): "
        f"n={checks.get('power_prediction_samples')!r} "
        f"median rel err={checks.get('power_prediction_median_rel_error')!r} "
        f"p95={checks.get('power_prediction_p95_rel_error')!r} "
        f"max={checks.get('power_prediction_max_rel_error')!r}"
    )
    print(
        "      step-0-origin predictions (environment warm-starts those segments): "
        f"n={checks.get('power_prediction_step0_origin_samples')!r} "
        f"median rel err={checks.get('power_prediction_step0_origin_median_rel_error')!r} "
        f"p95={checks.get('power_prediction_step0_origin_p95_rel_error')!r}"
    )
    parity = checks.get("route_actions_parity") or {}
    print(
        "(iii) P13 selection == five_arm.route_actions(DROP_C2): "
        f"{parity.get('p13_matches_drop_c2')!r} "
        f"(scrambled middle surface: {parity.get('p13_matches_drop_c2_with_scrambled_middle')!r})"
    )
    stats = checks.get("surface_stats") or {}
    if stats:
        print("\n=== one-step surface statistics (step "
              f"{stats.get('step_index')}) ===")
        print(
            "Q2*      min/median/max = "
            f"{stats['q2_star_min']:.6g} / {stats['q2_star_median']:.6g} / "
            f"{stats['q2_star_max']:.6g}"
        )
        print(
            "Q1+Q3    min/median/max = "
            f"{stats['q1_plus_q3_min']:.6g} / {stats['q1_plus_q3_median']:.6g} / "
            f"{stats['q1_plus_q3_max']:.6g}"
        )
        print(f"ZETA2* median (bits)   = {stats['zeta_bits_median']:.6g}")
        print(
            "argmax flip fraction when Q2* is added to Q1+Q3 = "
            f"{stats['argmax_flip_fraction']:.4f}"
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("smoke", "run"):
        command = sub.add_parser(name)
        command.add_argument("--seeds", type=int, nargs="+", default=None)
        command.add_argument("--lineages", type=int, nargs="+", default=None)
        command.add_argument("--arms", type=str, nargs="+", default=list(ARMS))
        command.add_argument(
            "--output-dir",
            type=Path,
            default=HERE / (f"{name}-latest"),
        )
        command.add_argument("--contract-sha256", type=str, default="UNSEALED_ENGINEERING")
        command.add_argument("--tle-root", type=Path, default=DEFAULT_TLE_ROOT)
        command.add_argument("--prereg", type=Path, default=screen.DEFAULT_PREREG)
        command.add_argument("--gate-dir", type=Path, default=screen.DEFAULT_GATE_DIR)
        command.add_argument("--source-dir", type=Path, default=screen.DEFAULT_SOURCE_DIR)
        command.add_argument("--v03-root", type=Path, default=screen.DEFAULT_V03_ROOT)
        command.add_argument("--main-dir", type=Path, default=five_arm.DEFAULT_MAIN_DIR)
        command.add_argument(
            "--source-closure",
            choices=("require", "receipt-only"),
            default="receipt-only",
            help=(
                "require: also re-verify the sealed V0.4 source-CONSTRUCTION "
                "closure manifest against the current tree.  receipt-only "
                "(default): authenticate the gate seals, the three selected "
                "hybrid checkpoint files, the Main checkpoint and the frozen "
                "TLE/PREREG binding, and record whether the closure re-check "
                "would have passed."
            ),
        )
    args = parser.parse_args(argv)

    if args.command == "smoke":
        seeds = list(args.seeds) if args.seeds is not None else [SMOKE_SEED]
        if seeds != [SMOKE_SEED]:
            raise OracleScreenError(
                f"smoke is reserved for evaluation seed {SMOKE_SEED} only"
            )
        lineages = (
            list(args.lineages)
            if args.lineages is not None
            else [INITIALIZATION_SEEDS[0]]
        )
        instrument = True
    else:
        if args.seeds is None:
            raise OracleScreenError("run requires an explicit --seeds list")
        seeds = list(args.seeds)
        lineages = (
            list(args.lineages)
            if args.lineages is not None
            else list(INITIALIZATION_SEEDS)
        )
        instrument = False

    print(
        f"mode={args.command} seeds={list(seeds)} lineages={list(lineages)} "
        f"arms={list(args.arms)}"
    )
    print(f"output-dir={args.output_dir}")
    print(f"lambda0={LAMBDA0_BITS_PER_J!r} hex={LAMBDA0_HEX}")
    print(f"kappa_bits={KAPPA_BITS_SOURCE!r} hex={KAPPA_BITS_SOURCE.hex()}")
    result = execute(
        mode=args.command,
        seeds=[int(value) for value in seeds],
        lineages=[int(value) for value in lineages],
        arms=[str(value) for value in args.arms],
        output_dir=Path(args.output_dir),
        contract_sha256=str(args.contract_sha256),
        tle_root=Path(args.tle_root),
        prereg_path=Path(args.prereg),
        gate_dir=Path(args.gate_dir),
        source_dir=Path(args.source_dir),
        v03_root=Path(args.v03_root),
        main_dir=Path(args.main_dir),
        instrument=instrument,
        source_closure=str(args.source_closure),
    )
    _report(result)
    if instrument:
        _report_self_checks(result)
    episodes = int(result["episode_count"])
    if episodes:
        mean_s = float(
            np.mean([float(entry["elapsed_s"]) for entry in result["timings"]])
        )
        print(
            f"\n{episodes} episodes in {result['elapsed_s']:.1f}s "
            f"(mean {mean_s:.2f}s/episode)"
        )
        print(
            "projected wall time for 6 seeds x 3 lineages x 7 arms + 6 MAIN = 132 "
            f"episodes: {132.0 * mean_s / 60.0:.1f} min at this rate"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
