#!/usr/bin/env python3
"""Run the frozen disjoint-seed C3 median-guard shadow campaign.

This is an evaluation-only runner.  It does not update a learner, replay
buffer, reward implementation, runtime policy, or any project document.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import importlib.metadata
import json
import math
import os
import pickle
import platform
import statistics
import sys
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any, Iterable

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ORACLE_DIR = REPO / ".scratch" / "catfish-oracle-gate"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ORACLE_DIR))
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

import run_c3_intra_bottleneck_shadow as base  # noqa: E402
import run_oracle_gate as oracle_module  # noqa: E402
import scripts.run_head_pivotality_probe as checkpoint_loader  # noqa: E402
from mcrl.env.action_contract import (  # noqa: E402
    NO_OP_ACTION,
    UNSERVED,
    Association,
    HandoverClass,
)
from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.env.ephemeris import SatelliteSet  # noqa: E402
from mcrl.env.link_budget import (  # noqa: E402
    BASEBAND_POWER_PER_SATELLITE_W,
    CIRCUIT_POWER_PER_BEAM_W,
)
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    _code_sha256,
    _default_code_paths,
    _evaluation_rngs,
)


SPEC = HERE / "C3-DISJOINT-MEDIAN-SHADOW-SPEC-2026-08-27.md"
SPEC_SHA256 = "edb7576b07e24214083a97461698c6a4bc52fd84ff9172ae5e70d3ac9eabec42"
SOURCE_DRIFT_MANIFEST = (
    HERE / "C3-ANALYSIS-SOURCE-DRIFT-MANIFEST-2026-08-27.md"
)
SOURCE_DRIFT_MANIFEST_SHA256 = (
    "d3f4c2f78dfaa8bb9a94d5a988c6420b3875f50dfcf6a5e9bb54735187edf76c"
)
HELPER_CLOSURE_MANIFEST = HERE / "C3-HELPER-CLOSURE-MANIFEST-2026-08-27.md"
HELPER_CLOSURE_MANIFEST_SHA256 = (
    "575e7745216bb171808224be000b5538ce047e88e703902731d13335ccf104f0"
)
C3_V1_HELPER = HERE / "run_c3_intra_bottleneck_shadow.py"
C3_V1_HELPER_SHA256 = (
    "c9558d4db702bc3a84efc00b92e809f9a190409a9b6f286cb225e5ce52a40706"
)
ORACLE_HELPER = ORACLE_DIR / "run_oracle_gate.py"
ORACLE_HELPER_SHA256 = (
    "b50c396ea344d444e5db704aea05db613f9d6e29930524185d0f33f3cee338cb"
)
CHECKPOINT_LOADER_HELPER = REPO / "scripts" / "run_head_pivotality_probe.py"
CHECKPOINT_LOADER_HELPER_SHA256 = (
    "563c5c5fa04068868d02cbce542dc3a15305fd840b766dc919f257ea49dddeb9"
)
FROZEN_SEEDS = tuple(range(2026082801, 2026082806))
USERS = 100
FORMAL_STEPS = 10
OBSERVATION_DIM = 112
MAX_PAIRED_HORIZON = 3
DECISION_INTERVAL_S = 30.08
PHI1_TIME_S = 0.062
PHI2_TIME_S = 0.142
SEED_T95_DF4 = 2.776445105
POWER_TOLERANCE_W = 1e-10
IMMEDIATE_EE_SIGN_UNAVAILABLE = np.int8(-2)
EXPECTED_CHECKPOINT_SHA256 = base.EXPECTED_CHECKPOINT_SHA256
EXPECTED_PREREG_DIGEST = (
    "3a920671dcce62075b1a21362d392b6c370c99979cba70d72a513da9ae9773f4"
)
EXPECTED_PREREG_FILE_SHA256 = (
    "8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543"
)
EXPECTED_LAUNCHED_CODE_SHA256 = (
    "544fcf078f7e0d74c38e79288081c60357bc64b59540120dbe4e30bffe014ec4"
)
EXPECTED_ANALYSIS_CODE_SHA256 = (
    "4cfc7e3043453994fc0686c3bbfa14d9a95156aeabc578b26decb2f210603a2e"
)

DEFAULT_OUTPUT = (
    HERE / "c3-disjoint-median-shadow-seeds-2026082801-2026082805-v1.json"
)
DEFAULT_OBSERVATIONS_OUTPUT = (
    HERE
    / "c3-disjoint-median-shadow-seeds-2026082801-2026082805-observations-v1.npz"
)
DEFAULT_RECEIPT_OUTPUT = (
    HERE
    / "c3-disjoint-median-shadow-seeds-2026082801-2026082805-receipt-v1.json"
)


PhysicalKey = tuple[int, int]


def _json_default(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"cannot serialize {type(value).__name__}")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _state_sha(state: Any) -> str:
    encoded = json.dumps(
        state,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    ).encode("utf-8")
    return _sha256_bytes(encoded)


def _pickle_sha(state: Any) -> str:
    """Hash a complete in-memory object graph for same-process clone checks."""

    return _sha256_bytes(pickle.dumps(state, protocol=5))


def _rng_sha(rng: np.random.Generator | None) -> str | None:
    return None if rng is None else _state_sha(rng.bit_generator.state)


def _slot_tables_sha(slot_tables: Iterable[Any]) -> str:
    digest = hashlib.sha256()
    for uid, table in enumerate(slot_tables):
        digest.update(int(uid).to_bytes(4, byteorder="little", signed=False))
        for values in (table.norad_ids, table.cell_ids, table.mask):
            array = np.ascontiguousarray(values)
            digest.update(str(array.dtype).encode("ascii"))
            digest.update(np.asarray(array.shape, dtype=np.int64).tobytes())
            digest.update(array.tobytes())
    return digest.hexdigest()


def _candidate_table_sha(observation: Any) -> str:
    return _slot_tables_sha(observation.candidates.slot_tables)


def _environment_candidate_sha(environment: Any) -> str | None:
    candidates = environment._candidates
    return None if candidates is None else _slot_tables_sha(candidates.slot_tables)


def _optional_array_sha(value: Any) -> str | None:
    return None if value is None else _pickle_sha(np.asarray(value))


def _association_state(value: object) -> dict[str, Any]:
    if isinstance(value, Association):
        return {
            "kind": "association",
            "norad_id": int(value.norad_id),
            "cell_id": int(value.cell_id),
        }
    # ``_Unserved`` is a semantic sentinel, but a generic ``deepcopy`` creates
    # another instance of the same private type.  Receipts therefore classify
    # it by type instead of relying on object identity.
    if isinstance(value, type(UNSERVED)):
        return {"kind": "unserved"}
    if value is None:
        return {"kind": "episode_start"}
    raise TypeError(f"unexpected association state: {value!r}")


def _wrapped_mutable_state_receipt(wrapped: Any) -> dict[str, Any]:
    """Hash rollout state; rebuilt branch-local SGP4 internals stay isolated."""

    environment = wrapped.environment
    driver = environment.driver
    tracker = driver._tracker
    satellites = driver._satellites
    return {
        "wrapper": {
            "epoch": None if wrapped._epoch is None else wrapped._epoch.isoformat(),
            "last_outcome_sha256": (
                None
                if wrapped._last_outcome is None
                else _pickle_sha(wrapped._last_outcome)
            ),
        },
        "environment": {
            "step_index": int(environment._step_index),
            "started": bool(environment._started),
            "ledgers": [
                {
                    "previous": _association_state(ledger.previous),
                    "started": bool(ledger._started),
                }
                for ledger in environment._ledgers
            ],
            "segments_sha256": _pickle_sha(environment._segments),
            "previous_radiating_sha256": _pickle_sha(
                environment._previous_radiating
            ),
            "previous_demand": [
                [int(key[0]), int(key[1]), int(value)]
                for key, value in sorted(environment._previous_demand.items())
            ],
            "previous_association": [
                _association_state(value)
                for value in environment._previous_association
            ],
            "candidates_sha256": (
                None
                if environment._candidates is None
                else _pickle_sha(environment._candidates)
            ),
            "pending_segment_age_sha256": _optional_array_sha(
                environment._pending_segment_age
            ),
            "mobility_rng_sha256": _rng_sha(environment._mobility_rng),
            "age_rng_sha256": _rng_sha(environment._age_rng),
        },
        "scenario_driver": {
            "step_index": int(driver._step_index),
            "start_utc": (
                None if driver._start_utc is None else driver._start_utc.isoformat()
            ),
            "frozen_window_norad_ids_sha256": _optional_array_sha(
                driver._frozen_window_norad_ids
            ),
            "user_xy_km_sha256": _optional_array_sha(driver._users._xy_km),
            "user_heading_rad_sha256": _optional_array_sha(
                driver._users._heading_rad
            ),
            "dwell_anchors_sha256": _optional_array_sha(driver._dwell._anchors),
            "satellite_norad_ids_sha256": (
                None
                if satellites is None
                else _optional_array_sha(satellites.norad_ids)
            ),
            "satellite_tle_records_sha256": (
                None
                if satellites is None
                else _pickle_sha(satellites.records)
            ),
            "d2_tracker": (
                None
                if tracker is None
                else {
                    "latched_sha256": _optional_array_sha(tracker._latched),
                    "condition_active_sha256": _optional_array_sha(
                        tracker._condition_active
                    ),
                    "condition_started_sha256": _optional_array_sha(
                        tracker._condition_started
                    ),
                    "ttt_elapsed_sha256": _optional_array_sha(
                        tracker._ttt_elapsed
                    ),
                    "steps_seen": int(tracker._steps_seen),
                    "primed": bool(tracker._primed),
                }
            ),
        },
    }


def _wrapped_mutable_state_sha(wrapped: Any) -> str:
    return _state_sha(_wrapped_mutable_state_receipt(wrapped))


def _clone_wrapped_for_pair(wrapped: Any) -> Any:
    """Clone continuation state and rebuild the mutable SGP4 propagator."""

    source_environment = wrapped.environment
    source_driver = source_environment.driver

    driver = copy.copy(source_driver)
    users = copy.copy(source_driver._users)
    users._xy_km = (
        None
        if source_driver._users._xy_km is None
        else source_driver._users._xy_km.copy()
    )
    users._heading_rad = (
        None
        if source_driver._users._heading_rad is None
        else source_driver._users._heading_rad.copy()
    )
    dwell = copy.copy(source_driver._dwell)
    dwell._anchors = (
        None
        if source_driver._dwell._anchors is None
        else source_driver._dwell._anchors.copy()
    )
    driver._users = users
    driver._dwell = dwell
    driver._tracker = copy.deepcopy(source_driver._tracker)
    # SatelliteSet contains unpickleable SGP4 Satrec objects, and SGP4 may
    # update internal propagation fields by reference.  Rebuild the complete
    # propagator from the frozen immutable TLE records so neither branch can
    # mutate the other branch or the outer rollout through a shared SatrecArray.
    if source_driver._satellites is None:
        raise RuntimeError("cannot clone an uninitialised satellite propagator")
    driver._satellites = SatelliteSet(source_driver._satellites.records)
    driver._frozen_window_norad_ids = (
        None
        if source_driver._frozen_window_norad_ids is None
        else source_driver._frozen_window_norad_ids.copy()
    )

    environment = copy.copy(source_environment)
    environment.driver = driver
    # Ledger payloads are immutable Association values, the UNSERVED sentinel,
    # or None.  Shallow-copy each ledger so the branch owns its mutable
    # ``_started``/``_previous`` slots while preserving sentinel identity.
    environment._ledgers = [
        copy.copy(ledger) for ledger in source_environment._ledgers
    ]
    environment._segments = copy.deepcopy(source_environment._segments)
    environment._previous_radiating = copy.deepcopy(
        source_environment._previous_radiating
    )
    environment._previous_demand = dict(source_environment._previous_demand)
    environment._previous_association = list(
        source_environment._previous_association
    )
    environment._candidates = copy.deepcopy(source_environment._candidates)
    environment._mobility_rng = copy.deepcopy(source_environment._mobility_rng)
    environment._pending_segment_age = (
        None
        if source_environment._pending_segment_age is None
        else source_environment._pending_segment_age.copy()
    )
    environment._age_rng = copy.deepcopy(source_environment._age_rng)

    branch = copy.copy(wrapped)
    branch.environment = environment
    branch._last_outcome = copy.deepcopy(wrapped._last_outcome)
    return branch


def _active_keys(evaluation: Any) -> set[PhysicalKey]:
    return {tuple(map(int, key)) for key in evaluation.resolution.active_beams}


def _active_satellites(evaluation: Any) -> set[int]:
    return {key[0] for key in _active_keys(evaluation)}


def _sign(value: float) -> int:
    return 1 if value > 0.0 else (-1 if value < 0.0 else 0)


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _marginal_power_reward_w(
    evaluation: Any,
    *,
    actions: np.ndarray,
    focal_user: int,
    physics: Any,
) -> float:
    """ADR removal-counterfactual reward, computed from the live PA identity."""

    if not bool(evaluation.resolution.served[focal_user]):
        if int(actions[focal_user]) == NO_OP_ACTION:
            return 0.0
        c_out = (
            base._supply(float(physics.beam_power_max_w), physics)
            + CIRCUIT_POWER_PER_BEAM_W
            + BASEBAND_POWER_PER_SATELLITE_W
        )
        return -float(c_out)

    key = base._served_key(evaluation, focal_user)
    if key is None:
        raise RuntimeError("served focal user has no physical beam key")
    users = base._users_on(evaluation, key)
    beam_power = max(float(evaluation.link_power_w[uid]) for uid in users)
    if len(users) > 1:
        power_minus = max(
            float(evaluation.link_power_w[uid])
            for uid in users
            if uid != focal_user
        )
        marginal = base._supply(beam_power, physics) - base._supply(
            power_minus, physics
        )
    else:
        active_on_satellite = sum(
            candidate[0] == key[0] for candidate in _active_keys(evaluation)
        )
        marginal = (
            base._supply(beam_power, physics)
            + CIRCUIT_POWER_PER_BEAM_W
            + (
                BASEBAND_POWER_PER_SATELLITE_W
                if active_on_satellite == 1
                else 0.0
            )
        )
    if marginal < -POWER_TOLERANCE_W:
        raise RuntimeError("removal counterfactual produced negative marginal power")
    return -float(max(marginal, 0.0))


def _source_qualification_exact(
    *,
    environment: Any,
    observation: Any,
    baseline_actions: np.ndarray,
    baseline_keys: list[PhysicalKey | None],
    baseline: Any,
    focal_user: int,
) -> tuple[dict[str, Any], list[tuple[int, PhysicalKey]]]:
    """Frozen v1 source logic with the preregistered exact inequality."""

    source = baseline_keys[focal_user]
    common = {
        "focal_user": int(focal_user),
        "reference_action": int(baseline_actions[focal_user]),
        "reference_key": base._json_key(source),
        "reference_handover": baseline.handovers[focal_user].value,
    }
    if source is None or not bool(baseline.resolution.served[focal_user]):
        return common | {
            "status": "source_ineligible",
            "reason": "reference_unserved",
        }, []

    previous = environment._previous_association[focal_user]
    segment = environment._segments[focal_user]
    continuing = bool(
        isinstance(previous, Association)
        and segment is not None
        and (previous.norad_id, previous.cell_id) == source
        and segment.continues(previous)
    )
    if not continuing or baseline.handovers[focal_user] is not HandoverClass.NONE:
        return common | {
            "status": "source_ineligible",
            "reason": "reference_not_continuing_incumbent",
        }, []

    source_users = base._users_on(baseline, source)
    if len(source_users) < 2:
        return common | {
            "status": "source_ineligible",
            "reason": "source_load_lt_2",
        }, []
    other_source_users = [uid for uid in source_users if uid != focal_user]
    focal_power = float(baseline.link_power_w[focal_user])
    next_power = max(float(baseline.link_power_w[uid]) for uid in other_source_users)
    if not focal_power > next_power:
        return common | {
            "status": "source_ineligible",
            "reason": "focal_not_strict_unique_source_max",
            "source_load": len(source_users),
            "focal_power_w": focal_power,
            "source_next_power_w": next_power,
        }, []

    active = _active_keys(baseline)
    table = observation.candidates.slot_tables[focal_user]
    candidates = [
        (action, key)
        for action, key in base._physical_actions(table)
        if key != source and key[0] == source[0] and key in active
    ]
    if not candidates:
        return common | {
            "status": "source_qualified_no_destination",
            "reason": "no_active_same_satellite_destination",
            "source_load": len(source_users),
            "focal_power_w": focal_power,
            "source_next_power_w": next_power,
        }, []
    return common | {
        "status": "source_qualified",
        "reason": "candidate_scan_required",
        "source_load": len(source_users),
        "focal_power_w": focal_power,
        "source_next_power_w": next_power,
        "candidate_count_pre_certificate": len(candidates),
    }, candidates


def _certify_candidate(
    *,
    environment: Any,
    baseline_actions: np.ndarray,
    baseline_keys: list[PhysicalKey | None],
    baseline: Any,
    focal_user: int,
    candidate_action: int,
    candidate_key: PhysicalKey,
    source_row: dict[str, Any],
    rng: np.random.Generator,
) -> dict[str, Any]:
    """Apply the frozen deterministic service and PA certificate."""

    source_key = baseline_keys[focal_user]
    if source_key is None:
        raise RuntimeError("candidate certificate received an unserved source")
    destination_users = base._users_on(baseline, candidate_key)
    if not destination_users:
        raise RuntimeError("candidate certificate received an inactive destination")
    destination_max = max(
        float(baseline.link_power_w[uid]) for uid in destination_users
    )

    alternative_actions = baseline_actions.copy()
    alternative_actions[focal_user] = int(candidate_action)
    alternative = environment.evaluate_actions(alternative_actions, rng)
    alternative_keys = base.v1.physical_action_keys(
        alternative_actions, environment._candidates.slot_tables
    )
    changed_physical_users = [
        uid
        for uid, (reference, candidate) in enumerate(
            zip(baseline_keys, alternative_keys, strict=True)
        )
        if reference != candidate
    ]

    invariant_failures: list[str] = []
    if changed_physical_users != [focal_user]:
        invariant_failures.append("not_exactly_one_focal_physical_action_change")
    if not np.array_equal(
        alternative_actions[np.arange(USERS) != focal_user],
        baseline_actions[np.arange(USERS) != focal_user],
    ):
        invariant_failures.append("nonfocal_action_changed")
    if not bool(alternative.resolution.served[focal_user]):
        invariant_failures.append("candidate_focal_unserved")
    if alternative.handovers[focal_user] is not HandoverClass.INTRA_SATELLITE:
        invariant_failures.append("candidate_not_phi1")
    if not np.array_equal(
        alternative.resolution.served, baseline.resolution.served
    ):
        invariant_failures.append("served_vector_changed")
    if _active_keys(alternative) != _active_keys(baseline):
        invariant_failures.append("active_beam_set_changed")
    if _active_satellites(alternative) != _active_satellites(baseline):
        invariant_failures.append("active_satellite_set_changed")
    if base._served_key(alternative, focal_user) != candidate_key:
        invariant_failures.append("focal_not_served_on_candidate")
    nonfocal = np.arange(USERS) != focal_user
    if not np.allclose(
        alternative.link_power_w[nonfocal],
        baseline.link_power_w[nonfocal],
        rtol=0.0,
        atol=0.0,
        equal_nan=True,
    ):
        invariant_failures.append("nonfocal_link_power_changed")

    candidate_power = float(alternative.link_power_w[focal_user])
    common = {
        "candidate_action": int(candidate_action),
        "candidate_key": base._json_key(candidate_key),
        "source_key": base._json_key(source_key),
        "candidate_power_w": candidate_power,
        "destination_max_power_w": destination_max,
        "candidate_handover": alternative.handovers[focal_user].value,
        "changed_physical_users": changed_physical_users,
        "eligibility_reads_realised_fading_rate_reward_ee_or_successor": False,
        "neutral_branch_rician_power_gain": 1.0,
        "neutral_branch_shadow_loss_db": 0.0,
    }
    if candidate_power > destination_max:
        return common | {
            "status": "candidate_ineligible",
            "reason": "candidate_exceeds_destination_max",
            "power_certified": False,
            "guard_retained": False,
            "selected": False,
        }
    if invariant_failures:
        return common | {
            "status": "certificate_failure",
            "reason": "preoutcome_invariant_failure",
            "invariant_failures": invariant_failures,
            "power_certified": False,
            "guard_retained": False,
            "selected": False,
        }

    source_next = float(source_row["source_next_power_w"])
    source_max = float(source_row["focal_power_w"])
    predicted_delta = base._supply(source_next, environment.physics) - base._supply(
        source_max, environment.physics
    )
    neutral_delta = float(alternative.system_power_w - baseline.system_power_w)
    residual = neutral_delta - predicted_delta
    certificate_pass = bool(
        predicted_delta < 0.0
        and neutral_delta < 0.0
        and abs(residual) <= POWER_TOLERANCE_W
    )
    common.update(
        {
            "source_load_reference": len(base._users_on(baseline, source_key)),
            "destination_load_reference": len(destination_users),
            "source_max_power_w": source_max,
            "source_next_power_w": source_next,
            "predicted_delta_system_power_w": predicted_delta,
            "neutral_delta_system_power_w": neutral_delta,
            "power_identity_residual_w": residual,
        }
    )
    if not certificate_pass:
        return common | {
            "status": "certificate_failure",
            "reason": "power_identity_failure",
            "power_certified": False,
            "guard_retained": False,
            "selected": False,
        }

    median_reference = float(baseline.energy.system_throughput_bps)
    median_candidate = float(alternative.energy.system_throughput_bps)
    median_delta = median_candidate - median_reference
    retained = bool(median_delta >= 0.0)
    return common | {
        "status": (
            "guard_retained" if retained else "power_certified_guard_rejected"
        ),
        "reason": (
            "median_rate_noninferior"
            if retained
            else "median_rate_decreased"
        ),
        "power_certified": True,
        "guard_retained": retained,
        "selected": False,
        "median_reference_throughput_bps": median_reference,
        "median_candidate_throughput_bps": median_candidate,
        "median_delta_throughput_bps": median_delta,
        "guard_reads_only_fading_off_rate": True,
    }


def _scan_preoutcome(
    *,
    environment: Any,
    observation: Any,
    baseline_actions: np.ndarray,
    seed: int,
    step_index: int,
    rng: np.random.Generator,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[int, dict[str, Any]],
]:
    """Freeze all proposals under neutral propagation before actual evaluation."""

    source_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    selected_by_focal: dict[int, dict[str, Any]] = {}
    original_physics = environment.physics
    environment.physics = replace(original_physics, fading_enabled=False)
    try:
        neutral_reference = environment.evaluate_actions(baseline_actions, rng)
        baseline_keys = base.v1.physical_action_keys(
            baseline_actions, observation.candidates.slot_tables
        )
        for focal_user in range(USERS):
            source_row, scan = _source_qualification_exact(
                environment=environment,
                observation=observation,
                baseline_actions=baseline_actions,
                baseline_keys=baseline_keys,
                baseline=neutral_reference,
                focal_user=focal_user,
            )
            source_row.update(
                {
                    "evaluation_seed": int(seed),
                    "step_index": int(step_index),
                    "proposal_frozen_before_realised_outcome": True,
                    "neutral_branch_rician_power_gain": 1.0,
                    "neutral_branch_shadow_loss_db": 0.0,
                }
            )
            source_rows.append(source_row)
            focal_candidates: list[dict[str, Any]] = []
            for action, key in scan:
                row = _certify_candidate(
                    environment=environment,
                    baseline_actions=baseline_actions,
                    baseline_keys=baseline_keys,
                    baseline=neutral_reference,
                    focal_user=focal_user,
                    candidate_action=action,
                    candidate_key=key,
                    source_row=source_row,
                    rng=rng,
                )
                row.update(
                    {
                        "evaluation_seed": int(seed),
                        "step_index": int(step_index),
                        "focal_user": int(focal_user),
                        "reference_action": int(baseline_actions[focal_user]),
                        "reference_key": source_row["reference_key"],
                    }
                )
                candidate_rows.append(row)
                focal_candidates.append(row)

            survivors = [row for row in focal_candidates if row["guard_retained"]]
            if survivors:
                # Most negative delta is the largest certified power reduction.
                selected = min(
                    survivors,
                    key=lambda row: (
                        float(row["predicted_delta_system_power_w"]),
                        int(row["candidate_key"][0]),
                        int(row["candidate_key"][1]),
                        int(row["candidate_action"]),
                    ),
                )
                selected["selected"] = True
                selected["selection_rule"] = (
                    "largest_certified_power_reduction_then_lexicographic_"
                    "norad_cell_action"
                )
                selected_by_focal[focal_user] = selected
    finally:
        environment.physics = original_physics
    return source_rows, candidate_rows, selected_by_focal


def _interval_ledger(outcome: Any) -> dict[str, Any]:
    rates = np.asarray(outcome.link_rate_bps, dtype=np.float64)
    phi1 = np.array(
        [handover is HandoverClass.INTRA_SATELLITE for handover in outcome.handovers],
        dtype=bool,
    )
    phi2 = np.array(
        [handover is HandoverClass.INTER_SATELLITE for handover in outcome.handovers],
        dtype=bool,
    )
    throughput = float(rates.sum())
    power = float(outcome.system_power_w)
    b_nominal = DECISION_INTERVAL_S * throughput
    e_payload = DECISION_INTERVAL_S * power
    eta_nominal = b_nominal / e_payload if e_payload > 0.0 else None
    canonical_eta = float(outcome.energy.system_ee_bits_per_j)
    return {
        "step_index": int(outcome.step_index),
        "system_throughput_bps": throughput,
        "system_power_w": power,
        "B_nominal_bits": b_nominal,
        "E_payload_j": e_payload,
        "L_phi1_bps": float(rates[phi1].sum()),
        "L_phi2_bps": float(rates[phi2].sum()),
        "N_phi1": int(np.count_nonzero(phi1)),
        "N_phi2": int(np.count_nonzero(phi2)),
        "served_count": int(outcome.resolution.served_count),
        "active_beams": [list(key) for key in sorted(_active_keys(outcome))],
        "eta_nominal_bits_per_j": eta_nominal,
        "canonical_eta_bits_per_j": canonical_eta,
        "nominal_eta_identity_residual_bits_per_j": (
            None if eta_nominal is None else float(eta_nominal - canonical_eta)
        ),
        "preview_commit_parity": True,
    }


def _branch_summary(intervals: list[dict[str, Any]]) -> dict[str, Any]:
    totals = {
        "B_nominal_bits": float(sum(row["B_nominal_bits"] for row in intervals)),
        "E_payload_j": float(sum(row["E_payload_j"] for row in intervals)),
        "L_phi1_bps": float(sum(row["L_phi1_bps"] for row in intervals)),
        "L_phi2_bps": float(sum(row["L_phi2_bps"] for row in intervals)),
        "N_phi1": int(sum(row["N_phi1"] for row in intervals)),
        "N_phi2": int(sum(row["N_phi2"] for row in intervals)),
    }
    if totals["E_payload_j"] <= 0.0:
        raise RuntimeError("selected paired branch has non-positive payload energy")
    b_time = (
        totals["B_nominal_bits"]
        - PHI1_TIME_S * totals["L_phi1_bps"]
        - PHI2_TIME_S * totals["L_phi2_bps"]
    )
    return totals | {
        "B_time_62_142ms_bits": float(b_time),
        "eta_nominal_bits_per_j": float(
            totals["B_nominal_bits"] / totals["E_payload_j"]
        ),
        "eta_time_62_142ms_E0_bits_per_j": float(
            b_time / totals["E_payload_j"]
        ),
        "E1_j": None,
        "E2_j": None,
        "handover_energy_instantiated": False,
    }


def _main_actions(
    trainer: Any, states: list[Any], wrapped_masks: list[Any]
) -> tuple[np.ndarray, np.ndarray]:
    encoded = trainer.encode_states(states)
    masks = np.stack([row.mask for row in wrapped_masks])
    q1 = trainer.scalarized_q_values(encoded, objective_weights=(1.0, 0.0, 0.0))
    return base.v1.masked_greedy_actions(q1, masks), encoded


def _preview_parity(preview: Any, outcome: Any) -> tuple[bool, str | None]:
    try:
        base.v1._assert_full_preview_parity(preview, outcome)
    except RuntimeError as exc:
        return False, str(exc)
    return True, None


def _paired_horizon(
    *,
    trainer: Any,
    wrapped: Any,
    env_rng: np.random.Generator,
    pre_observation: Any,
    reference_actions: np.ndarray,
    candidate_actions: np.ndarray,
    focal_user: int,
    horizon: int,
    predicted_delta_power_w: float,
) -> dict[str, Any]:
    """Execute two actual-fading branches from independent rollout forks."""

    if not 1 <= horizon <= MAX_PAIRED_HORIZON:
        raise ValueError("paired horizon must lie in [1, 3]")
    outer_step_before = int(wrapped.environment._step_index)
    outer_full_state_before = _wrapped_mutable_state_sha(wrapped)
    outer_candidate_before = _environment_candidate_sha(wrapped.environment)
    outer_env_rng_before = _rng_sha(env_rng)
    outer_mobility_rng_before = _rng_sha(wrapped.environment._mobility_rng)
    outer_age_rng_before = _rng_sha(wrapped.environment._age_rng)
    branch_a = _clone_wrapped_for_pair(wrapped)
    branch_b = _clone_wrapped_for_pair(wrapped)
    rng_a = copy.deepcopy(env_rng)
    rng_b = copy.deepcopy(env_rng)
    outer_satellites = wrapped.environment.driver._satellites
    satellites_a = branch_a.environment.driver._satellites
    satellites_b = branch_b.environment.driver._satellites
    if outer_satellites is None or satellites_a is None or satellites_b is None:
        raise RuntimeError("paired branch has no satellite propagator")
    mobility_a = branch_a.environment._mobility_rng
    mobility_b = branch_b.environment._mobility_rng
    age_a = branch_a.environment._age_rng
    age_b = branch_b.environment._age_rng
    branch_a_full_state = _wrapped_mutable_state_sha(branch_a)
    branch_b_full_state = _wrapped_mutable_state_sha(branch_b)
    branch_a_candidate = _environment_candidate_sha(branch_a.environment)
    branch_b_candidate = _environment_candidate_sha(branch_b.environment)
    outer_full_state_after_clone = _wrapped_mutable_state_sha(wrapped)
    outer_candidate_after_clone = _environment_candidate_sha(wrapped.environment)
    age_rng_objects_separate = bool(
        (
            wrapped.environment._age_rng is None
            and age_a is None
            and age_b is None
        )
        or (
            wrapped.environment._age_rng is not None
            and age_a is not None
            and age_b is not None
            and age_a is not age_b
            and age_a is not wrapped.environment._age_rng
            and age_b is not wrapped.environment._age_rng
        )
    )
    clone_boolean_checks = {
        "separate_wrapper_objects": branch_a is not branch_b,
        "separate_environment_objects": (
            branch_a.environment is not branch_b.environment
            and branch_a.environment is not wrapped.environment
            and branch_b.environment is not wrapped.environment
        ),
        "separate_scenario_driver_objects": (
            branch_a.environment.driver is not branch_b.environment.driver
            and branch_a.environment.driver is not wrapped.environment.driver
            and branch_b.environment.driver is not wrapped.environment.driver
        ),
        "separate_driver_mutable_component_objects": (
            branch_a.environment.driver._users
            is not branch_b.environment.driver._users
            and branch_a.environment.driver._dwell
            is not branch_b.environment.driver._dwell
            and branch_a.environment.driver._tracker
            is not branch_b.environment.driver._tracker
        ),
        "separate_satellite_set_objects": (
            satellites_a is not satellites_b
            and satellites_a is not outer_satellites
            and satellites_b is not outer_satellites
        ),
        "separate_satrec_array_objects": (
            satellites_a._array is not satellites_b._array
            and satellites_a._array is not outer_satellites._array
            and satellites_b._array is not outer_satellites._array
        ),
        "separate_satrec_objects": (
            len(satellites_a._satrecs)
            == len(satellites_b._satrecs)
            == len(outer_satellites._satrecs)
            and all(
                sat_a is not sat_b
                and sat_a is not sat_outer
                and sat_b is not sat_outer
                for sat_a, sat_b, sat_outer in zip(
                    satellites_a._satrecs,
                    satellites_b._satrecs,
                    outer_satellites._satrecs,
                    strict=True,
                )
            )
        ),
        "satellite_tle_records_equal": (
            satellites_a.records
            == satellites_b.records
            == outer_satellites.records
            and _pickle_sha(satellites_a.records)
            == _pickle_sha(satellites_b.records)
            == _pickle_sha(outer_satellites.records)
        ),
        "satellite_norad_order_equal": (
            np.array_equal(satellites_a.norad_ids, satellites_b.norad_ids)
            and np.array_equal(satellites_a.norad_ids, outer_satellites.norad_ids)
        ),
        "separate_candidate_objects": (
            branch_a.environment._candidates
            is not branch_b.environment._candidates
            and branch_a.environment._candidates
            is not wrapped.environment._candidates
            and branch_b.environment._candidates
            is not wrapped.environment._candidates
        ),
        "separate_environment_rng_objects": (
            rng_a is not rng_b and rng_a is not env_rng and rng_b is not env_rng
        ),
        "separate_mobility_rng_objects": (
            mobility_a is not None
            and mobility_b is not None
            and mobility_a is not mobility_b
            and mobility_a is not wrapped.environment._mobility_rng
            and mobility_b is not wrapped.environment._mobility_rng
        ),
        "separate_age_rng_objects_or_all_none": age_rng_objects_separate,
        "environment_rng_state_equal": (
            outer_env_rng_before == _rng_sha(rng_a) == _rng_sha(rng_b)
        ),
        "mobility_rng_state_equal": (
            outer_mobility_rng_before
            == _rng_sha(mobility_a)
            == _rng_sha(mobility_b)
        ),
        "age_rng_state_equal": (
            outer_age_rng_before == _rng_sha(age_a) == _rng_sha(age_b)
        ),
        "branch_full_state_matches_outer": (
            branch_a_full_state
            == branch_b_full_state
            == outer_full_state_before
        ),
        "candidate_table_state_equal": (
            branch_a_candidate
            == branch_b_candidate
            == outer_candidate_before
            == _candidate_table_sha(pre_observation)
        ),
        "outer_environment_untouched_before_pair": (
            outer_full_state_after_clone == outer_full_state_before
            and outer_candidate_after_clone == outer_candidate_before
            and _rng_sha(env_rng) == outer_env_rng_before
            and _rng_sha(wrapped.environment._mobility_rng)
            == outer_mobility_rng_before
            and _rng_sha(wrapped.environment._age_rng) == outer_age_rng_before
        ),
    }
    clone_checks: dict[str, Any] = {
        "hash_method": (
            "explicit mutable-state receipt with SHA-256 subgraphs; every branch "
            "rebuilds an independent SGP4 SatelliteSet/SatrecArray from equal "
            "frozen TLE records"
        ),
        "full_wrapped_state_sha256": {
            "outer_before": outer_full_state_before,
            "outer_after_clone": outer_full_state_after_clone,
            "branch_A_at_clone": branch_a_full_state,
            "branch_B_at_clone": branch_b_full_state,
        },
        "candidate_table_sha256": {
            "pre_observation": _candidate_table_sha(pre_observation),
            "outer_before": outer_candidate_before,
            "outer_after_clone": outer_candidate_after_clone,
            "branch_A_at_clone": branch_a_candidate,
            "branch_B_at_clone": branch_b_candidate,
        },
        "rng_sha256": {
            "outer_environment_before": outer_env_rng_before,
            "branch_A_environment_at_clone": _rng_sha(rng_a),
            "branch_B_environment_at_clone": _rng_sha(rng_b),
            "outer_mobility_before": outer_mobility_rng_before,
            "branch_A_mobility_at_clone": _rng_sha(mobility_a),
            "branch_B_mobility_at_clone": _rng_sha(mobility_b),
            "outer_age_before": outer_age_rng_before,
            "branch_A_age_at_clone": _rng_sha(age_a),
            "branch_B_age_at_clone": _rng_sha(age_b),
        },
        "checks": clone_boolean_checks,
    }

    result_a: Any = None
    result_b: Any = None
    observation_a = pre_observation
    observation_b = pre_observation
    intervals_a: list[dict[str, Any]] = []
    intervals_b: list[dict[str, Any]] = []
    crn_rows: list[dict[str, Any]] = []
    engineering_failures: list[str] = [
        f"clone_{name}"
        for name, passed in clone_boolean_checks.items()
        if not passed
    ]
    first_details: dict[str, Any] | None = None

    for offset in range(horizon):
        if offset == 0:
            actions_a = reference_actions.copy()
            actions_b = candidate_actions.copy()
        else:
            actions_a, _encoded_a = _main_actions(
                trainer, result_a.user_states, result_a.action_masks
            )
            actions_b, _encoded_b = _main_actions(
                trainer, result_b.user_states, result_b.action_masks
            )
            observation_a = branch_a.last_outcome.observation
            observation_b = branch_b.last_outcome.observation

        candidate_sha_a = _candidate_table_sha(observation_a)
        candidate_sha_b = _candidate_table_sha(observation_b)
        keys_a = base.v1.physical_action_keys(
            actions_a, observation_a.candidates.slot_tables
        )
        keys_b = base.v1.physical_action_keys(
            actions_b, observation_b.candidates.slot_tables
        )
        changed_actions = np.flatnonzero(actions_a != actions_b).astype(int).tolist()
        env_before_a = _rng_sha(rng_a)
        env_before_b = _rng_sha(rng_b)
        mob_before_a = _rng_sha(branch_a.environment._mobility_rng)
        mob_before_b = _rng_sha(branch_b.environment._mobility_rng)

        preview_a = branch_a.environment.evaluate_actions(actions_a, rng_a)
        preview_b = branch_b.environment.evaluate_actions(actions_b, rng_b)
        result_a = branch_a.step(actions_a, rng_a)
        result_b = branch_b.step(actions_b, rng_b)
        outcome_a = branch_a.last_outcome
        outcome_b = branch_b.last_outcome
        parity_a, parity_error_a = _preview_parity(preview_a, outcome_a)
        parity_b, parity_error_b = _preview_parity(preview_b, outcome_b)
        if not parity_a:
            engineering_failures.append(
                f"branch_A_preview_commit_parity_offset_{offset}: {parity_error_a}"
            )
        if not parity_b:
            engineering_failures.append(
                f"branch_B_preview_commit_parity_offset_{offset}: {parity_error_b}"
            )

        ledger_a = _interval_ledger(outcome_a)
        ledger_b = _interval_ledger(outcome_b)
        ledger_a["preview_commit_parity"] = parity_a
        ledger_b["preview_commit_parity"] = parity_b
        intervals_a.append(ledger_a)
        intervals_b.append(ledger_b)

        candidate_tables_equal = candidate_sha_a == candidate_sha_b
        actions_equal = bool(np.array_equal(actions_a, actions_b))
        env_after_equal = _rng_sha(rng_a) == _rng_sha(rng_b)
        mobility_after_equal = _rng_sha(
            branch_a.environment._mobility_rng
        ) == _rng_sha(branch_b.environment._mobility_rng)
        exact_interpretation = bool(
            env_before_a == env_before_b
            and mob_before_a == mob_before_b
            and env_after_equal
            and mobility_after_equal
            and candidate_tables_equal
            and (offset == 0 or actions_equal)
        )
        crn_rows.append(
            {
                "horizon_offset": int(offset),
                "candidate_table_sha256_A": candidate_sha_a,
                "candidate_table_sha256_B": candidate_sha_b,
                "candidate_tables_equal": candidate_tables_equal,
                "actions_equal": actions_equal,
                "changed_action_users": changed_actions,
                "physical_keys_equal": keys_a == keys_b,
                "environment_rng_equal_before": env_before_a == env_before_b,
                "environment_rng_equal_after": env_after_equal,
                "mobility_rng_equal_before": mob_before_a == mob_before_b,
                "mobility_rng_equal_after": mobility_after_equal,
                "exact_draw_by_draw_crn_interpretation": exact_interpretation,
                "interpretation_note": (
                    "cloned-stream focal intervention"
                    if offset == 0
                    else (
                        "candidate/action divergence limits CRN interpretation"
                        if not exact_interpretation
                        else "candidate/action and cloned streams remain aligned"
                    )
                ),
            }
        )

        if offset == 0:
            nonfocal = np.arange(USERS) != focal_user
            served_equal = bool(
                np.array_equal(
                    outcome_a.resolution.served, outcome_b.resolution.served
                )
            )
            active_beams_equal = _active_keys(outcome_a) == _active_keys(outcome_b)
            active_satellites_equal = _active_satellites(
                outcome_a
            ) == _active_satellites(outcome_b)
            nonfocal_actions_equal = bool(
                np.array_equal(actions_a[nonfocal], actions_b[nonfocal])
            )
            nonfocal_power_equal = bool(
                np.allclose(
                    outcome_a.link_power_w[nonfocal],
                    outcome_b.link_power_w[nonfocal],
                    rtol=0.0,
                    atol=0.0,
                    equal_nan=True,
                )
            )
            actual_delta_power = float(
                outcome_b.system_power_w - outcome_a.system_power_w
            )
            power_residual = actual_delta_power - predicted_delta_power_w
            r3_a = _marginal_power_reward_w(
                outcome_a,
                actions=actions_a,
                focal_user=focal_user,
                physics=branch_a.environment.physics,
            )
            r3_b = _marginal_power_reward_w(
                outcome_b,
                actions=actions_b,
                focal_user=focal_user,
                physics=branch_b.environment.physics,
            )
            incentive_residual = (r3_b - r3_a) - (
                outcome_a.system_power_w - outcome_b.system_power_w
            )
            first_checks = {
                "served_set_preserved": served_equal,
                "active_beam_set_preserved": active_beams_equal,
                "active_satellite_set_preserved": active_satellites_equal,
                "nonfocal_actions_unchanged": nonfocal_actions_equal,
                "nonfocal_link_powers_unchanged": nonfocal_power_equal,
                "reference_handover_none": (
                    outcome_a.handovers[focal_user] is HandoverClass.NONE
                ),
                "candidate_handover_phi1": (
                    outcome_b.handovers[focal_user]
                    is HandoverClass.INTRA_SATELLITE
                ),
                "strict_actual_power_reduction": actual_delta_power < 0.0,
                "actual_power_identity_within_1e_10_w": (
                    abs(power_residual) <= POWER_TOLERANCE_W
                ),
                "marginal_reward_incentive_identity_within_1e_10_w": (
                    abs(incentive_residual) <= POWER_TOLERANCE_W
                ),
                "branch_A_preview_commit_parity": parity_a,
                "branch_B_preview_commit_parity": parity_b,
            }
            for name, passed in first_checks.items():
                if not passed:
                    engineering_failures.append(f"first_step_{name}")
            first_details = {
                "checks": first_checks,
                "reference_system_power_w": float(outcome_a.system_power_w),
                "candidate_system_power_w": float(outcome_b.system_power_w),
                "actual_delta_system_power_w": actual_delta_power,
                "predicted_delta_system_power_w": float(predicted_delta_power_w),
                "actual_power_identity_residual_w": float(power_residual),
                "reference_system_throughput_bps": float(
                    outcome_a.energy.system_throughput_bps
                ),
                "candidate_system_throughput_bps": float(
                    outcome_b.energy.system_throughput_bps
                ),
                "delta_system_throughput_bps": float(
                    outcome_b.energy.system_throughput_bps
                    - outcome_a.energy.system_throughput_bps
                ),
                "reference_eta_bits_per_j": float(
                    outcome_a.energy.system_ee_bits_per_j
                ),
                "candidate_eta_bits_per_j": float(
                    outcome_b.energy.system_ee_bits_per_j
                ),
                "delta_eta_bits_per_j": float(
                    outcome_b.energy.system_ee_bits_per_j
                    - outcome_a.energy.system_ee_bits_per_j
                ),
                "realised_immediate_ee_sign": _sign(
                    float(
                        outcome_b.energy.system_ee_bits_per_j
                        - outcome_a.energy.system_ee_bits_per_j
                    )
                ),
                "reference_focal_marginal_power_reward_w": r3_a,
                "candidate_focal_marginal_power_reward_w": r3_b,
                "marginal_reward_delta_w": float(r3_b - r3_a),
                "marginal_reward_incentive_identity_residual_w": float(
                    incentive_residual
                ),
            }

        if result_a.done != result_b.done:
            engineering_failures.append("paired_done_flags_diverged")
            break
        if result_a.done:
            break

    if first_details is None:
        raise RuntimeError("paired branch did not execute its first interval")
    summary_a = _branch_summary(intervals_a)
    summary_b = _branch_summary(intervals_b)
    eta_ref = float(summary_a["eta_time_62_142ms_E0_bits_per_j"])
    if eta_ref <= 0.0:
        engineering_failures.append("reference_time_eta_nonpositive")
        e_extra_star: float | None = None
    else:
        e_extra_star = float(
            summary_b["B_time_62_142ms_bits"] / eta_ref
            - summary_b["E_payload_j"]
        )

    outer_full_state_after_pair = _wrapped_mutable_state_sha(wrapped)
    outer_candidate_after_pair = _environment_candidate_sha(wrapped.environment)
    post_pair_checks = {
        "outer_step_index_unchanged_after_pair": (
            int(wrapped.environment._step_index) == outer_step_before
        ),
        "outer_full_state_unchanged_after_pair": (
            outer_full_state_after_pair == outer_full_state_before
        ),
        "outer_candidate_table_unchanged_after_pair": (
            outer_candidate_after_pair == outer_candidate_before
        ),
        "outer_environment_rng_unchanged_after_pair": (
            _rng_sha(env_rng) == outer_env_rng_before
        ),
        "outer_mobility_rng_unchanged_after_pair": (
            _rng_sha(wrapped.environment._mobility_rng)
            == outer_mobility_rng_before
        ),
        "outer_age_rng_unchanged_after_pair": (
            _rng_sha(wrapped.environment._age_rng) == outer_age_rng_before
        ),
    }
    clone_checks["checks"].update(post_pair_checks)
    clone_checks["full_wrapped_state_sha256"]["outer_after_pair"] = (
        outer_full_state_after_pair
    )
    clone_checks["candidate_table_sha256"]["outer_after_pair"] = (
        outer_candidate_after_pair
    )
    clone_checks["rng_sha256"].update(
        {
            "outer_environment_after_pair": _rng_sha(env_rng),
            "outer_mobility_after_pair": _rng_sha(
                wrapped.environment._mobility_rng
            ),
            "outer_age_after_pair": _rng_sha(wrapped.environment._age_rng),
        }
    )
    engineering_failures.extend(
        f"clone_{name}" for name, passed in post_pair_checks.items() if not passed
    )

    comparison = {
        "delta_eta_nominal_bits_per_j": float(
            summary_b["eta_nominal_bits_per_j"]
            - summary_a["eta_nominal_bits_per_j"]
        ),
        "delta_eta_time_62_142ms_E0_bits_per_j": float(
            summary_b["eta_time_62_142ms_E0_bits_per_j"]
            - summary_a["eta_time_62_142ms_E0_bits_per_j"]
        ),
        "payload_energy_saving_j": float(
            summary_a["E_payload_j"] - summary_b["E_payload_j"]
        ),
        "delta_N_phi1_candidate_minus_reference": int(
            summary_b["N_phi1"] - summary_a["N_phi1"]
        ),
        "delta_N_phi2_candidate_minus_reference": int(
            summary_b["N_phi2"] - summary_a["N_phi2"]
        ),
        "E_extra_star_j": e_extra_star,
        "E_extra_star_is_break_even_ledger_not_E_HO": True,
    }
    return {
        "horizon_intervals": len(intervals_a),
        "first_step": first_details,
        "branch_A_reference": {
            "intervals": intervals_a,
            "summary": summary_a,
        },
        "branch_B_candidate_then_frozen_main": {
            "intervals": intervals_b,
            "summary": summary_b,
        },
        "comparison": comparison,
        "cloned_state_checks": clone_checks,
        "crn_diagnostics": crn_rows,
        "exact_crn_beyond_cloned_start": bool(
            all(row["exact_draw_by_draw_crn_interpretation"] for row in crn_rows)
        ),
        "engineering_failures": sorted(set(engineering_failures)),
    }


def _empty_observation_store() -> dict[str, list[Any]]:
    return {
        "observation": [],
        "seed": [],
        "step": [],
        "user": [],
        "reference_action": [],
        "source_qualified": [],
        "power_certified": [],
        "guard_retained": [],
        "selected": [],
        "realised_immediate_ee_sign": [],
        "focal_marginal_power_reward_w": [],
    }


def _append_observations(
    store: dict[str, list[Any]],
    *,
    encoded: np.ndarray,
    seed: int,
    step: int,
    baseline_actions: np.ndarray,
    source_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    selected_by_focal: dict[int, dict[str, Any]],
    marginal_rewards: np.ndarray,
) -> None:
    if encoded.shape != (USERS, OBSERVATION_DIM):
        raise RuntimeError(
            f"expected encoded Main state {(USERS, OBSERVATION_DIM)}, got {encoded.shape}"
        )
    by_focal: dict[int, list[dict[str, Any]]] = {uid: [] for uid in range(USERS)}
    for row in candidate_rows:
        by_focal[int(row["focal_user"])].append(row)
    if len(source_rows) != USERS:
        raise RuntimeError("source census did not return one row per user")
    for uid in range(USERS):
        source = source_rows[uid]
        focal_candidates = by_focal[uid]
        selected = selected_by_focal.get(uid)
        realised_sign = (
            IMMEDIATE_EE_SIGN_UNAVAILABLE
            if selected is None
            else np.int8(selected["paired"]["first_step"]["realised_immediate_ee_sign"])
        )
        store["observation"].append(
            np.asarray(encoded[uid], dtype=np.float32).copy()
        )
        store["seed"].append(int(seed))
        store["step"].append(int(step))
        store["user"].append(int(uid))
        store["reference_action"].append(int(baseline_actions[uid]))
        store["source_qualified"].append(
            str(source["status"]).startswith("source_qualified")
        )
        store["power_certified"].append(
            any(bool(row["power_certified"]) for row in focal_candidates)
        )
        store["guard_retained"].append(
            any(bool(row["guard_retained"]) for row in focal_candidates)
        )
        store["selected"].append(selected is not None)
        store["realised_immediate_ee_sign"].append(realised_sign)
        store["focal_marginal_power_reward_w"].append(
            float(marginal_rewards[uid])
        )


def run_seed(
    *,
    trainer: Any,
    wrapped: Any,
    seed: int,
    max_steps: int,
    observation_store: dict[str, list[Any]],
) -> dict[str, Any]:
    env_rng, mobility_rng, _action_rng, _control_rng = _evaluation_rngs(seed)
    states, wrapped_masks, observation = wrapped.reset(env_rng, mobility_rng)
    encoded = trainer.encode_states(states)
    source_rows_all: list[dict[str, Any]] = []
    candidate_rows_all: list[dict[str, Any]] = []
    paired_rows: list[dict[str, Any]] = []
    baseline_steps: list[dict[str, Any]] = []
    engineering_failures: list[str] = []

    for _ in range(max_steps):
        masks = np.stack([row.mask for row in wrapped_masks])
        q1 = trainer.scalarized_q_values(encoded, objective_weights=(1.0, 0.0, 0.0))
        baseline_actions = base.v1.masked_greedy_actions(q1, masks)
        step_index = int(observation.step_index)

        # This entire scan completes before any actual-fading current-slot
        # ActionEvaluation is requested.
        source_rows, candidate_rows, selected_by_focal = _scan_preoutcome(
            environment=wrapped.environment,
            observation=observation,
            baseline_actions=baseline_actions,
            seed=seed,
            step_index=step_index,
            rng=env_rng,
        )
        source_rows_all.extend(source_rows)
        candidate_rows_all.extend(candidate_rows)
        engineering_failures.extend(
            f"preoutcome_candidate_certificate_failure_step_{step_index}_user_"
            f"{row['focal_user']}_action_{row['candidate_action']}"
            for row in candidate_rows
            if row["status"] == "certificate_failure"
        )

        actual_reference = wrapped.environment.evaluate_actions(
            baseline_actions, env_rng
        )
        marginal_rewards = np.array(
            [
                _marginal_power_reward_w(
                    actual_reference,
                    actions=baseline_actions,
                    focal_user=uid,
                    physics=wrapped.environment.physics,
                )
                for uid in range(USERS)
            ],
            dtype=np.float64,
        )

        horizon = min(MAX_PAIRED_HORIZON, max_steps - step_index)
        if horizon < 1:
            raise RuntimeError("selected proposal has no remaining paired interval")
        for focal_user in sorted(selected_by_focal):
            selected = selected_by_focal[focal_user]
            candidate_actions = baseline_actions.copy()
            candidate_actions[focal_user] = int(selected["candidate_action"])
            paired = _paired_horizon(
                trainer=trainer,
                wrapped=wrapped,
                env_rng=env_rng,
                pre_observation=observation,
                reference_actions=baseline_actions,
                candidate_actions=candidate_actions,
                focal_user=focal_user,
                horizon=horizon,
                predicted_delta_power_w=float(
                    selected["predicted_delta_system_power_w"]
                ),
            )
            pair_index = len(paired_rows)
            selected["paired_row_index_within_seed"] = pair_index
            selected["paired"] = paired
            paired_rows.append(
                {
                    "evaluation_seed": int(seed),
                    "step_index": int(step_index),
                    "focal_user": int(focal_user),
                    "reference_action": int(baseline_actions[focal_user]),
                    "candidate_action": int(selected["candidate_action"]),
                    "reference_key": selected["reference_key"],
                    "candidate_key": selected["candidate_key"],
                    "paired": paired,
                }
            )
            engineering_failures.extend(
                f"paired_step_{step_index}_user_{focal_user}: {failure}"
                for failure in paired["engineering_failures"]
            )

        _append_observations(
            observation_store,
            encoded=encoded,
            seed=seed,
            step=step_index,
            baseline_actions=baseline_actions,
            source_rows=source_rows,
            candidate_rows=candidate_rows,
            selected_by_focal=selected_by_focal,
            marginal_rewards=marginal_rewards,
        )

        result = wrapped.step(baseline_actions, env_rng)
        parity, parity_error = _preview_parity(actual_reference, wrapped.last_outcome)
        if not parity:
            engineering_failures.append(
                f"baseline_preview_commit_parity_step_{step_index}: {parity_error}"
            )
        baseline_steps.append(
            {
                "step_index": step_index,
                "system_power_w": float(wrapped.last_outcome.system_power_w),
                "system_throughput_bps": float(
                    wrapped.last_outcome.energy.system_throughput_bps
                ),
                "system_ee_bits_per_j": float(
                    wrapped.last_outcome.energy.system_ee_bits_per_j
                ),
                "served_count": int(wrapped.last_outcome.resolution.served_count),
                "preview_commit_parity": parity,
                "proposals_frozen_before_actual_evaluation": True,
            }
        )
        if result.done or len(baseline_steps) >= max_steps:
            break
        states = result.user_states
        wrapped_masks = result.action_masks
        observation = wrapped.last_outcome.observation
        encoded = trainer.encode_states(states)

    return {
        "evaluation_seed": int(seed),
        "steps": len(baseline_steps),
        "census_user_steps": len(source_rows_all),
        "baseline_steps": baseline_steps,
        "source_rows": source_rows_all,
        "candidate_rows": candidate_rows_all,
        "paired_rows": paired_rows,
        "engineering_failures": sorted(set(engineering_failures)),
    }


def _observation_arrays(
    store: dict[str, list[Any]], *, runner_sha256: str
) -> dict[str, np.ndarray]:
    rows = len(store["seed"])
    observations = (
        np.stack(store["observation"]).astype(np.float32, copy=False)
        if rows
        else np.empty((0, OBSERVATION_DIM), dtype=np.float32)
    )
    arrays = {
        "observation": observations,
        "seed": np.asarray(store["seed"], dtype=np.int64),
        "step": np.asarray(store["step"], dtype=np.int16),
        "user": np.asarray(store["user"], dtype=np.int16),
        "reference_action": np.asarray(
            store["reference_action"], dtype=np.int16
        ),
        "source_qualified": np.asarray(store["source_qualified"], dtype=np.bool_),
        "power_certified": np.asarray(store["power_certified"], dtype=np.bool_),
        "guard_retained": np.asarray(store["guard_retained"], dtype=np.bool_),
        "selected": np.asarray(store["selected"], dtype=np.bool_),
        "realised_immediate_ee_sign": np.asarray(
            store["realised_immediate_ee_sign"], dtype=np.int8
        ),
        "focal_marginal_power_reward_w": np.asarray(
            store["focal_marginal_power_reward_w"], dtype=np.float64
        ),
        "schema": np.asarray("mcrl-c3-disjoint-median-shadow-observations-v1"),
        "spec_sha256": np.asarray(SPEC_SHA256),
        "runner_sha256": np.asarray(runner_sha256),
        "immediate_ee_sign_unavailable_sentinel": np.asarray(
            IMMEDIATE_EE_SIGN_UNAVAILABLE, dtype=np.int8
        ),
    }
    for name, array in arrays.items():
        if name in {
            "schema",
            "spec_sha256",
            "runner_sha256",
            "immediate_ee_sign_unavailable_sentinel",
        }:
            continue
        if array.shape[0] != rows:
            raise RuntimeError(f"observation field {name} has inconsistent row count")
    if observations.shape != (rows, OBSERVATION_DIM):
        raise RuntimeError("observation artifact is not N x 112")
    return arrays


def _stage_npz(
    arrays: dict[str, np.ndarray], destination: Path
) -> tuple[Path, str, int]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w+b",
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            np.savez_compressed(handle, **arrays)
            handle.flush()
            os.fsync(handle.fileno())
        digest = base.v1._sha256(temporary)
        size = temporary.stat().st_size
        if base.v1._sha256(temporary) != digest:
            raise RuntimeError("staged observation artifact hash was not stable")
        return temporary, digest, size
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _stage_json(payload: dict[str, Any], destination: Path) -> tuple[Path, str, int]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    encoded = (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            allow_nan=False,
            default=_json_default,
        )
        + "\n"
    ).encode("utf-8")
    handle = tempfile.NamedTemporaryFile(
        mode="w+b",
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        return temporary, _sha256_bytes(encoded), len(encoded)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _fsync_parents(paths: Iterable[Path]) -> None:
    for parent in sorted({path.parent.resolve() for path in paths}, key=str):
        descriptor = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def _publish_bundle_without_overwrite(
    *,
    staged_json: Path,
    json_output: Path,
    staged_npz: Path,
    npz_output: Path,
    staged_receipt: Path,
    receipt_output: Path,
    expected_json_sha256: str,
    expected_npz_sha256: str,
    expected_receipt_sha256: str,
) -> None:
    items = (
        (staged_npz, npz_output, expected_npz_sha256),
        (staged_json, json_output, expected_json_sha256),
        # The receipt is the commit marker and is therefore always linked last.
        (staged_receipt, receipt_output, expected_receipt_sha256),
    )
    published: list[Path] = []
    try:
        for staged, destination, _expected in items:
            os.link(staged, destination)
            published.append(destination)
        for _staged, destination, expected in items:
            if base.v1._sha256(destination) != expected:
                raise RuntimeError(
                    f"published artifact hash differs from staged hash: {destination}"
                )
        _fsync_parents(published)
    except BaseException:
        for destination in reversed(published):
            destination.unlink(missing_ok=True)
        if published:
            _fsync_parents(published)
        raise
    finally:
        for staged, _destination, _expected in items:
            staged.unlink(missing_ok=True)


def _campaign_summary(
    rollouts: list[dict[str, Any]], *, formal: bool, artifacts_pass: bool
) -> dict[str, Any]:
    paired = [row for rollout in rollouts for row in rollout["paired_rows"]]
    deltas = [
        float(row["paired"]["comparison"]["delta_eta_time_62_142ms_E0_bits_per_j"])
        for row in paired
    ]
    by_seed: list[dict[str, Any]] = []
    seed_means: list[float] = []
    for rollout in rollouts:
        values = [
            float(
                row["paired"]["comparison"][
                    "delta_eta_time_62_142ms_E0_bits_per_j"
                ]
            )
            for row in rollout["paired_rows"]
        ]
        mean = float(statistics.fmean(values)) if values else None
        if mean is not None:
            seed_means.append(mean)
        by_seed.append(
            {
                "seed": int(rollout["evaluation_seed"]),
                "selected_pairs": len(values),
                "mean_delta_eta_time_62_142ms_E0_bits_per_j": mean,
                "positive_mean": None if mean is None else bool(mean > 0.0),
            }
        )

    pooled_mean = float(statistics.fmean(deltas)) if deltas else None
    t95_estimable = bool(formal and len(seed_means) == 5)
    if t95_estimable:
        seed_mean = float(statistics.fmean(seed_means))
        seed_sd = float(statistics.stdev(seed_means))
        half_width = SEED_T95_DF4 * seed_sd / math.sqrt(5.0)
        seed_t95 = {
            "estimable": True,
            "n_seed_means": 5,
            "df": 4,
            "critical_value": SEED_T95_DF4,
            "mean": seed_mean,
            "sample_sd": seed_sd,
            "lower": float(seed_mean - half_width),
            "upper": float(seed_mean + half_width),
        }
    else:
        seed_t95 = {
            "estimable": False,
            "n_seed_means": len(seed_means),
            "df": None,
            "critical_value": SEED_T95_DF4,
            "mean": (
                float(statistics.fmean(seed_means)) if seed_means else None
            ),
            "sample_sd": (
                float(statistics.stdev(seed_means))
                if len(seed_means) >= 2
                else None
            ),
            "lower": None,
            "upper": None,
            "reason": (
                "frozen df=4 endpoint requires five defined seed-level "
                "conditional means; no value is imputed for a zero-support seed"
            ),
        }

    failures = sorted(
        {
            failure
            for rollout in rollouts
            for failure in rollout["engineering_failures"]
        }
    )
    supported_seeds = sum(row["selected_pairs"] >= 1 for row in by_seed)
    positive_seed_means = sum(row["positive_mean"] is True for row in by_seed)
    service_power_applicable = bool(paired)
    service_power_pass = bool(
        paired
        and all(not row["paired"]["engineering_failures"] for row in paired)
    )
    conditions = {
        "at_least_20_selected_pairs": len(paired) >= 20,
        "at_least_one_pair_in_four_of_five_seeds": supported_seeds >= 4,
        "pooled_mean_delta_eta_time_positive": (
            pooled_mean is not None and pooled_mean > 0.0
        ),
        "positive_seed_mean_in_at_least_four_of_five": positive_seed_means >= 4,
        "seed_t95_lower_above_zero": bool(
            seed_t95["lower"] is not None and seed_t95["lower"] > 0.0
        ),
        "all_selected_first_steps_service_preserving_and_strict_lower_power": (
            service_power_pass
        ),
        "all_engineering_identities_pass": not failures,
        "artifact_prepublication_checks_pass": bool(artifacts_pass),
    }
    if failures:
        decision = "CERTIFICATE_FAILURE"
    elif not formal:
        decision = "PILOT_NOT_ADJUDICATED"
    elif all(conditions.values()):
        decision = "PASS_TO_R2_AND_ALIASING_GATES_ONLY"
    else:
        decision = "FAIL_DROP_C3_EE_DIRECTION"
    return {
        "selected_pairs": len(paired),
        "supported_seeds": supported_seeds,
        "pooled_mean_delta_eta_time_62_142ms_E0_bits_per_j": pooled_mean,
        "positive_seed_means": positive_seed_means,
        "selected_pair_conditions_applicable": service_power_applicable,
        "selected_pair_conditions_not_applicable_reason": (
            None
            if service_power_applicable
            else "zero selected pairs; no vacuous all-pass is permitted"
        ),
        "by_seed": by_seed,
        "seed_t95": seed_t95,
        "frozen_advance_conditions": conditions,
        "engineering_failures": failures,
        "decision": decision,
    }


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=base.v1.DEFAULT_INPUT)
    parser.add_argument("--prereg", type=Path, default=base.v1.DEFAULT_PREREG)
    parser.add_argument(
        "--tle-root", type=Path, default=Path(TLE_ROOT_DEFAULT).expanduser()
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--observations-output", type=Path, default=DEFAULT_OBSERVATIONS_OUTPUT
    )
    parser.add_argument(
        "--receipt-output", type=Path, default=DEFAULT_RECEIPT_OUTPUT
    )
    parser.add_argument("--seeds", type=int, nargs="+", default=list(FROZEN_SEEDS))
    parser.add_argument("--max-steps", type=int, default=FORMAL_STEPS)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    if base.v1._sha256(SPEC) != SPEC_SHA256:
        raise RuntimeError("frozen C3 disjoint median-shadow specification changed")
    if (
        not SOURCE_DRIFT_MANIFEST.is_file()
        or base.v1._sha256(SOURCE_DRIFT_MANIFEST)
        != SOURCE_DRIFT_MANIFEST_SHA256
    ):
        raise RuntimeError("reviewed C3 analysis-source drift manifest changed")
    helper_closure_checks = {
        "helper_closure_manifest_sha256_matches_frozen": (
            HELPER_CLOSURE_MANIFEST.is_file()
            and base.v1._sha256(HELPER_CLOSURE_MANIFEST)
            == HELPER_CLOSURE_MANIFEST_SHA256
        ),
        "c3_v1_helper_sha256_matches_frozen": (
            C3_V1_HELPER.is_file()
            and base.v1._sha256(C3_V1_HELPER) == C3_V1_HELPER_SHA256
        ),
        "c3_v1_helper_import_path_matches_frozen": (
            Path(base.__file__).resolve() == C3_V1_HELPER.resolve()
        ),
        "oracle_helper_sha256_matches_frozen": (
            ORACLE_HELPER.is_file()
            and base.v1._sha256(ORACLE_HELPER) == ORACLE_HELPER_SHA256
        ),
        "oracle_helper_import_path_matches_frozen": (
            Path(oracle_module.__file__).resolve() == ORACLE_HELPER.resolve()
        ),
        "base_v1_module_identity_matches_oracle_import": (
            base.v1 is oracle_module
        ),
        "checkpoint_loader_helper_sha256_matches_frozen": (
            CHECKPOINT_LOADER_HELPER.is_file()
            and base.v1._sha256(CHECKPOINT_LOADER_HELPER)
            == CHECKPOINT_LOADER_HELPER_SHA256
        ),
        "checkpoint_loader_import_path_matches_frozen": (
            Path(checkpoint_loader.__file__).resolve()
            == CHECKPOINT_LOADER_HELPER.resolve()
        ),
        "checkpoint_loader_symbol_bindings_match_oracle": all(
            getattr(oracle_module, name) is getattr(checkpoint_loader, name)
            for name in (
                "DEFAULT_INPUT",
                "DEFAULT_PREREG",
                "_sha256",
                "_frozen_archive",
                "_make_environment",
                "_verify_and_load_trainer",
            )
        ),
    }
    failed_helpers = [
        name for name, passed in helper_closure_checks.items() if not passed
    ]
    if failed_helpers:
        raise RuntimeError(
            "frozen C3 helper closure failed: " + ", ".join(failed_helpers)
        )
    destinations = (args.output, args.observations_output, args.receipt_output)
    if len({destination.resolve() for destination in destinations}) != 3:
        raise ValueError("JSON, observation, and receipt outputs must be distinct")
    for destination in destinations:
        if destination.exists():
            raise FileExistsError(f"refusing to overwrite existing output: {destination}")
    if len(set(args.seeds)) != len(args.seeds):
        raise ValueError("--seeds must be unique")
    if any(seed not in FROZEN_SEEDS for seed in args.seeds):
        raise ValueError("every seed must belong to the frozen 2026082801..05 set")
    if not 1 <= args.max_steps <= FORMAL_STEPS:
        raise ValueError("--max-steps must lie in [1, 10]")

    formal = tuple(args.seeds) == FROZEN_SEEDS and args.max_steps == FORMAL_STEPS
    runner_path = Path(__file__).resolve()
    runner_sha = base.v1._sha256(runner_path)
    record = read_prereg(args.prereg)
    prereg_file_sha = base.v1._sha256(args.prereg)
    if record.digest != EXPECTED_PREREG_DIGEST:
        raise RuntimeError("preregistration digest differs from the frozen C3 input")
    if prereg_file_sha != EXPECTED_PREREG_FILE_SHA256:
        raise RuntimeError("preregistration byte SHA-256 differs from the frozen input")
    current_code_sha = _code_sha256(_default_code_paths())
    if current_code_sha != EXPECTED_ANALYSIS_CODE_SHA256:
        raise RuntimeError("analysis source differs from the reviewed C3 drift manifest")
    observation_store = _empty_observation_store()

    with tempfile.TemporaryDirectory(prefix="mcrl-c3-disjoint-median-shadow-") as temp:
        archive = base.v1._frozen_archive(
            record, args.tle_root, Path(temp) / "frozen-tle"
        )
        trainer, checkpoint = base.v1._verify_and_load_trainer(
            record,
            archive,
            run_dir=args.input_dir / "main",
            users=USERS,
        )
        if checkpoint["checkpoint_sha256"] != EXPECTED_CHECKPOINT_SHA256:
            raise RuntimeError("checkpoint digest differs from frozen shadow input")
        status = json.loads(
            Path(checkpoint["status_path"]).read_text(encoding="utf-8")
        )
        source_input_checks = {
            "prereg_digest_matches_frozen": record.digest
            == EXPECTED_PREREG_DIGEST,
            "prereg_file_sha256_matches_frozen": prereg_file_sha
            == EXPECTED_PREREG_FILE_SHA256,
            "status_prereg_digest_matches_frozen": status.get("prereg_digest")
            == EXPECTED_PREREG_DIGEST,
            "status_fingerprint_prereg_digest_matches_frozen": status.get(
                "run_fingerprint", {}
            ).get("prereg_digest")
            == EXPECTED_PREREG_DIGEST,
            "checkpoint_matches_frozen": checkpoint["checkpoint_sha256"]
            == EXPECTED_CHECKPOINT_SHA256,
            "launched_code_matches_frozen": checkpoint["launched_code_sha256"]
            == EXPECTED_LAUNCHED_CODE_SHA256,
            "analysis_code_matches_reviewed_manifest": current_code_sha
            == EXPECTED_ANALYSIS_CODE_SHA256,
            "source_drift_manifest_sha256_matches_frozen": base.v1._sha256(
                SOURCE_DRIFT_MANIFEST
            )
            == SOURCE_DRIFT_MANIFEST_SHA256,
            "helper_closure_matches_frozen": all(helper_closure_checks.values()),
        }
        failed_source_inputs = [
            name for name, passed in source_input_checks.items() if not passed
        ]
        if failed_source_inputs:
            raise RuntimeError(
                "frozen C3 source/input contract failed: "
                + ", ".join(failed_source_inputs)
            )
        rollouts = []
        for seed in args.seeds:
            wrapped = base.v1._make_environment(archive, users=USERS)
            rollouts.append(
                run_seed(
                    trainer=trainer,
                    wrapped=wrapped,
                    seed=seed,
                    max_steps=args.max_steps,
                    observation_store=observation_store,
                )
            )

    arrays = _observation_arrays(observation_store, runner_sha256=runner_sha)
    expected_rows = len(args.seeds) * args.max_steps * USERS
    if arrays["observation"].shape[0] != expected_rows:
        raise RuntimeError(
            f"expected {expected_rows} censused observations, got "
            f"{arrays['observation'].shape[0]}"
        )
    staged_npz, npz_sha, npz_size = _stage_npz(
        arrays, args.observations_output
    )
    staged_json: Path | None = None
    staged_receipt: Path | None = None
    try:
        artifact_checks = {
            "spec_sha256_verified": base.v1._sha256(SPEC) == SPEC_SHA256,
            "source_drift_manifest_sha256_verified": (
                base.v1._sha256(SOURCE_DRIFT_MANIFEST)
                == SOURCE_DRIFT_MANIFEST_SHA256
            ),
            "helper_closure_verified": all(helper_closure_checks.values()),
            "source_input_contract_verified": all(source_input_checks.values()),
            "checkpoint_sha256_verified": (
                checkpoint["checkpoint_sha256"] == EXPECTED_CHECKPOINT_SHA256
            ),
            "prereg_digest_verified": record.digest == EXPECTED_PREREG_DIGEST,
            "prereg_file_sha256_verified": (
                prereg_file_sha == EXPECTED_PREREG_FILE_SHA256
            ),
            "observation_npz_sha256_verified": (
                base.v1._sha256(staged_npz) == npz_sha
            ),
            "observation_row_count_verified": (
                arrays["observation"].shape == (expected_rows, OBSERVATION_DIM)
            ),
        }
        campaign = _campaign_summary(
            rollouts,
            formal=formal,
            artifacts_pass=all(artifact_checks.values()),
        )
        payload = {
            "schema": "mcrl-c3-disjoint-median-shadow-v1",
            "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "status": "complete",
            "stage": "frozen_formal_campaign" if formal else "engineering_pilot",
            "formal_decision_adjudicated": formal,
            "mode": (
                "evaluation-only legacy-narrow sensitivity; no optimizer, replay, "
                "reward, runtime, Main transfer, or training update"
            ),
            "claim_boundary": (
                "at most conditional 62/142-ms E_HO=0 paired-horizon EE evidence "
                "for the frozen C3 rule; never an accepted temporal-EE, Main-transfer, "
                "learnability, causal Multi-Catfish, implementation, or training claim"
            ),
            "multiplicity_disclosure": (
                "the unchanged median rule was the third guard examined on the "
                "one-seed development pool and selected exactly its five immediate-"
                "EE-positive rows; the original decision REJECT_MEDIAN_RATE_RULE "
                "remains permanent"
            ),
            "spec_path": str(SPEC),
            "spec_sha256": SPEC_SHA256,
            "runner_path": str(runner_path),
            "runner_sha256": runner_sha,
            "analysis_code_sha256": current_code_sha,
            "analysis_source_matches_training": (
                current_code_sha == checkpoint["launched_code_sha256"]
            ),
            "analysis_source_drift_review": {
                "passed": all(source_input_checks.values()),
                "manifest_path": str(SOURCE_DRIFT_MANIFEST),
                "manifest_sha256": SOURCE_DRIFT_MANIFEST_SHA256,
                "expected_analysis_code_sha256": EXPECTED_ANALYSIS_CODE_SHA256,
                "expected_launched_code_sha256": EXPECTED_LAUNCHED_CODE_SHA256,
                "checks": source_input_checks,
                "claim": (
                    "state encoding, Q1 inference, and committed physics are "
                    "compatible for this evaluation-only shadow; counterfactual "
                    "preview still requires per-step preview/commit parity"
                ),
            },
            "helper_closure": {
                "passed": all(helper_closure_checks.values()),
                "manifest_path": str(HELPER_CLOSURE_MANIFEST),
                "manifest_sha256": HELPER_CLOSURE_MANIFEST_SHA256,
                "checks": helper_closure_checks,
                "files": {
                    str(C3_V1_HELPER): C3_V1_HELPER_SHA256,
                    str(ORACLE_HELPER): ORACLE_HELPER_SHA256,
                    str(CHECKPOINT_LOADER_HELPER): (
                        CHECKPOINT_LOADER_HELPER_SHA256
                    ),
                },
            },
            "checkpoint": checkpoint,
            "prereg_path": str(args.prereg),
            "prereg_digest": record.digest,
            "prereg_file_sha256": prereg_file_sha,
            "input_dir": str(args.input_dir),
            "tle_root": str(args.tle_root),
            "frozen_tle_contract_verified": True,
            "configuration": {
                "evaluation_seeds": list(args.seeds),
                "frozen_formal_seeds": list(FROZEN_SEEDS),
                "users": USERS,
                "max_steps": args.max_steps,
                "formal_steps": FORMAL_STEPS,
                "paired_horizon_max": MAX_PAIRED_HORIZON,
                "decision_interval_s": DECISION_INTERVAL_S,
                "time_sensitivity_s": {"phi1": PHI1_TIME_S, "phi2": PHI2_TIME_S},
                "E1_j": None,
                "E2_j": None,
                "seed_t95_critical_df4": SEED_T95_DF4,
                "command_argv": list(sys.argv),
            },
            "proposal_visibility": {
                "eligibility_branch_fading_enabled": False,
                "rician_power_gain": 1.0,
                "shadow_loss_db": 0.0,
                "reads_realised_fading": False,
                "reads_realised_rate": False,
                "reads_reward": False,
                "reads_realised_EE": False,
                "reads_successor": False,
                "median_guard_reads_fading_off_system_rate_only": True,
                "selection_completed_before_actual_current_slot_evaluation": True,
                "maximum_selected_candidate_per_focal": 1,
            },
            "observation_artifact": {
                "path": str(args.observations_output),
                "sha256": npz_sha,
                "bytes": npz_size,
                "rows": int(arrays["observation"].shape[0]),
                "dimension": int(arrays["observation"].shape[1]),
                "dtype": str(arrays["observation"].dtype),
                "compressed_npz": True,
                "realised_immediate_ee_sign_encoding": {
                    "negative": -1,
                    "zero": 0,
                    "positive": 1,
                    "unavailable_unselected": int(IMMEDIATE_EE_SIGN_UNAVAILABLE),
                },
                "purpose": (
                    "subsequent collision and leave-one-seed-out 1-NN/permutation "
                    "audit only; does not decide Main transfer"
                ),
            },
            "artifact_checks": artifact_checks,
            "publication_contract": {
                "receipt_path": str(args.receipt_output),
                "receipt_schema": "mcrl-c3-shadow-bundle-receipt-v1",
                "valid_only_when_receipt_exists_and_hashes_match": True,
                "receipt_is_published_last": True,
                "no_overwrite": True,
                "rollback_all_new_bundle_paths_on_caught_failure": True,
            },
            "campaign_summary": campaign,
            "decision": campaign["decision"],
            "provenance": {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "numpy": np.__version__,
                "torch": _package_version("torch"),
                "sgp4": _package_version("sgp4"),
                "independent_unit": "evaluation seed; selected pairs cluster within seed",
                "baseline_policy": "frozen masked-greedy Q1-only Main",
                "paired_policy": (
                    "first interval frozen reference versus one focal change; then "
                    "each branch independently frozen masked-greedy Q1-only Main"
                ),
                "rng_contract": (
                    "four streams spawned from each frozen seed; paired branches "
                    "clone every explicit mutable continuation field and RNG and "
                    "rebuild independent SGP4 propagators from identical frozen "
                    "TLE records; divergence is logged without extending the CRN "
                    "claim"
                ),
                "bundle_hashes": (
                    "the JSON and NPZ hashes are committed by the separately hashed "
                    "receipt sidecar, which is published last"
                ),
            },
            "rollouts": rollouts,
        }
        staged_json, json_sha, json_size = _stage_json(payload, args.output)
        receipt_payload = {
            "schema": "mcrl-c3-shadow-bundle-receipt-v1",
            "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "status": "complete",
            "commit_marker_published_last": True,
            "formal_campaign": formal,
            "decision": campaign["decision"],
            "spec_sha256": SPEC_SHA256,
            "runner_sha256": runner_sha,
            "source_drift_manifest_sha256": SOURCE_DRIFT_MANIFEST_SHA256,
            "helper_closure_manifest_sha256": HELPER_CLOSURE_MANIFEST_SHA256,
            "helper_closure_checks": helper_closure_checks,
            "analysis_code_sha256": current_code_sha,
            "launched_code_sha256": checkpoint["launched_code_sha256"],
            "checkpoint_sha256": checkpoint["checkpoint_sha256"],
            "prereg_digest": record.digest,
            "prereg_file_sha256": prereg_file_sha,
            "artifacts": {
                "json": {
                    "path": str(args.output),
                    "sha256": json_sha,
                    "bytes": json_size,
                },
                "observations_npz": {
                    "path": str(args.observations_output),
                    "sha256": npz_sha,
                    "bytes": npz_size,
                },
            },
        }
        staged_receipt, receipt_sha, receipt_size = _stage_json(
            receipt_payload, args.receipt_output
        )
        _publish_bundle_without_overwrite(
            staged_json=staged_json,
            json_output=args.output,
            staged_npz=staged_npz,
            npz_output=args.observations_output,
            staged_receipt=staged_receipt,
            receipt_output=args.receipt_output,
            expected_json_sha256=json_sha,
            expected_npz_sha256=npz_sha,
            expected_receipt_sha256=receipt_sha,
        )
    except BaseException:
        for staged in (staged_npz, staged_json, staged_receipt):
            if staged is not None:
                staged.unlink(missing_ok=True)
        raise

    print(
        json.dumps(
            {
                "json_output": str(args.output),
                "json_sha256": json_sha,
                "json_bytes": json_size,
                "observations_output": str(args.observations_output),
                "observations_sha256": npz_sha,
                "receipt_output": str(args.receipt_output),
                "receipt_sha256": receipt_sha,
                "receipt_bytes": receipt_size,
                "decision": campaign["decision"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
