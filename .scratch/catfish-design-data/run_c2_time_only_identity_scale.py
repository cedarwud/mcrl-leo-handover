#!/usr/bin/env python3
"""Run the frozen C2 payload-boundary time-only identity and scale gate.

This runner is evaluation-only.  It neither updates a learner nor changes the
runtime reward, environment, preregistration, checkpoint, or project sources.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import statistics
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ORACLE_DIR = REPO / ".scratch" / "catfish-oracle-gate"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ORACLE_DIR))
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

import run_state_observable_gate as v2  # noqa: E402
import scripts.run_head_pivotality_probe as checkpoint_loader  # noqa: E402
from mcrl.env.action_contract import (  # noqa: E402
    UNSERVED,
    Association,
    HandoverClass,
    classify_handover,
)
from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.probe_p6 import P6_EVALUATION_SEEDS  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    _code_sha256,
    _default_code_paths,
    _evaluation_rngs,
)


SPEC = HERE / "C2-TIME-ONLY-IDENTITY-SCALE-SPEC-2026-08-27.md"
SPEC_SHA256 = "209ebb929ca822900ef917d0179b578ad7084432fdd126619b4fceb33b050c91"
ADR = REPO / "docs" / "decisions" / "ADR-004-payload-boundary-time-only-c2.md"
ADR_SHA256 = "f3c12ad3bad94c2a1199e743abb020a1696fdb5008ebafcd4c29f7357e84b46b"
SOURCE_DRIFT_MANIFEST = (
    HERE / "C2-ANALYSIS-SOURCE-DRIFT-MANIFEST-2026-08-27.md"
)
SOURCE_DRIFT_MANIFEST_SHA256 = (
    "aeae4ad94b4f0b719cc6d92bdb1ed3d0eefe39b10ae34909e0352f0e01f0a3a6"
)
V2_RUNNER = ORACLE_DIR / "run_state_observable_gate.py"
V2_RUNNER_SHA256 = (
    "7f26af5e56460ff297f16cd2de4bf208cbe0a51e7b94091529bd547e623b7b63"
)
V2_SPEC = ORACLE_DIR / "SPEC-v2-STATE-ONLY.md"
V2_SPEC_SHA256 = "9a0a70dac4f8f892a29a5162692b0464406899d7deb6b8ea6327a17ac369a760"
V2_RECEIPT = ORACLE_DIR / "state-only-confirmation-seeds-10-k10-v2.json"
V2_RECEIPT_SHA256 = (
    "cd88d8c5b17d163a957d8c2e56c2995080c4bb1636cbcc93fae13b234ba50658"
)
ORACLE_HELPER = ORACLE_DIR / "run_oracle_gate.py"
ORACLE_HELPER_SHA256 = (
    "b50c396ea344d444e5db704aea05db613f9d6e29930524185d0f33f3cee338cb"
)
CHECKPOINT_LOADER_HELPER = REPO / "scripts" / "run_head_pivotality_probe.py"
CHECKPOINT_LOADER_HELPER_SHA256 = (
    "563c5c5fa04068868d02cbce542dc3a15305fd840b766dc919f257ea49dddeb9"
)

EXPECTED_CHECKPOINT_SHA256 = v2.EXPECTED_CHECKPOINT_SHA256
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
EXPECTED_V2_RECEIPT_ANALYSIS_CODE_SHA256 = (
    "baa87f938ed0fdbf3b3d1e0cd7b29bb6859e3b12dea77dcc66fcea430fc1ad6b"
)
EXPECTED_V2_FOCAL_SCHEDULE_SHA256 = (
    "24c1419c6ca2e64c301f5b89c3d94e4f91993996ad1ee135ac3c0e6693bedefd"
)
EXPECTED_V2_R2_CENSUS_SHA256 = (
    "ba408399fda6f43767a14fc878a0df1b27f836f23111ae415392ef36e54747fd"
)
EXPECTED_V2_ELIGIBLE_KEY_SHA256 = (
    "e5a93676779d7a9d0ba79afed194fa66425a9641b71acbc13baf14d6a64f981b"
)
EXPECTED_ELIGIBLE_BY_SEED = {
    2026082401: 79,
    2026082402: 77,
    2026082403: 69,
    2026082404: 72,
    2026082405: 81,
    2026082406: 70,
    2026082407: 82,
    2026082408: 75,
    2026082409: 80,
    2026082410: 73,
}
EXPECTED_UNSAFE_KEY = (2026082408, 1, 42)

FROZEN_SEEDS = tuple(P6_EVALUATION_SEEDS)
USERS = 100
FORMAL_STEPS = 10
FOCAL_USERS_PER_STEP = 10
EXPECTED_FOCAL_ROWS = 1_000
EXPECTED_ELIGIBLE = 758
EXPECTED_SERVICE_UNSAFE = 1

PRIMARY_DELTA_S = 30.08
D2_CLOCK_DELTA_S = 0.640
PHI1_TIME_S = 0.062
PHI2_TIME_S = 0.142
IDENTITY_RELATIVE_TOLERANCE = 1e-9
SEED_T95_DF9 = 2.2621571627409915

PRIMARY_CLOCK = "primary_Delta_30_08_s"
D2_CLOCK = "D2_CLOCK_SCALE_SENSITIVITY"
CLOCKS = ((PRIMARY_CLOCK, PRIMARY_DELTA_S), (D2_CLOCK, D2_CLOCK_DELTA_S))

DEFAULT_OUTPUT = (
    HERE / "c2-time-only-identity-scale-seeds-2026082401-2026082410-v1.json"
)


PhysicalKey = v2.PhysicalKey


def _json_default(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"cannot serialize {type(value).__name__}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_sha(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _array_sha(array: np.ndarray) -> str:
    values = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(str(values.dtype).encode("ascii"))
    digest.update(np.asarray(values.shape, dtype=np.int64).tobytes())
    digest.update(values.tobytes())
    return digest.hexdigest()


def _rng_sha(rng: np.random.Generator | None) -> str | None:
    return None if rng is None else _json_sha(rng.bit_generator.state)


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _association_json(value: object) -> dict[str, Any]:
    if isinstance(value, Association):
        return {
            "kind": "association",
            "key": [int(value.norad_id), int(value.cell_id)],
        }
    if value is UNSERVED:
        return {"kind": "unserved", "key": None}
    if value is None:
        return {"kind": "episode_start", "key": None}
    raise TypeError(f"unexpected association ledger value: {value!r}")


def _candidate_table_sha(environment: Any) -> str:
    candidates = environment._candidates
    if candidates is None:
        raise RuntimeError("environment has no current candidate table")
    digest = hashlib.sha256()
    for uid, table in enumerate(candidates.slot_tables):
        digest.update(int(uid).to_bytes(4, byteorder="little", signed=False))
        for values in (table.norad_ids, table.cell_ids, table.mask):
            array = np.ascontiguousarray(values)
            digest.update(str(array.dtype).encode("ascii"))
            digest.update(np.asarray(array.shape, dtype=np.int64).tobytes())
            digest.update(array.tobytes())
    return digest.hexdigest()


def _prestate_sha(environment: Any) -> str:
    """Hash the mutable state that a preview must not advance."""

    previous_demand = [
        [int(key[0]), int(key[1]), int(value)]
        for key, value in sorted(environment._previous_demand.items())
    ]
    state = {
        "step_index": int(environment._step_index),
        "started": bool(environment._started),
        "ledgers": [
            {
                "previous": _association_json(row.previous),
                "started": bool(row._started),
            }
            for row in environment._ledgers
        ],
        "previous_association": [
            _association_json(row) for row in environment._previous_association
        ],
        "previous_demand": previous_demand,
        "candidate_table_sha256": _candidate_table_sha(environment),
        "segments_repr": [repr(row) for row in environment._segments],
        "pending_segment_age_sha256": (
            None
            if environment._pending_segment_age is None
            else hashlib.sha256(
                np.ascontiguousarray(environment._pending_segment_age).tobytes()
            ).hexdigest()
        ),
        "previous_radiating_repr": repr(environment._previous_radiating),
        "mobility_rng_sha256": _rng_sha(environment._mobility_rng),
        "age_rng_sha256": _rng_sha(environment._age_rng),
    }
    return _json_sha(state)


def _realised_association(evaluation: Any, uid: int) -> object:
    if not bool(evaluation.resolution.served[uid]):
        return UNSERVED
    return Association(
        norad_id=int(evaluation.resolution.serving_satellite[uid]),
        cell_id=int(evaluation.resolution.serving_cell[uid]),
    )


def _event_surface(
    evaluation: Any, previous: Sequence[object]
) -> dict[str, Any]:
    """Derive successful-handover times from the pre-step physical ledger."""

    if len(previous) != USERS:
        raise RuntimeError(f"expected {USERS} pre-step ledger entries")
    if len(evaluation.handovers) != USERS:
        raise RuntimeError(f"expected {USERS} realised handover classes")

    times = np.zeros(USERS, dtype=np.float64)
    events: list[dict[str, Any]] = []
    failures: list[str] = []
    counts = {
        "N_phi1": 0,
        "N_phi2": 0,
        "reentry_count": 0,
        "episode_start_count": 0,
        "unserved_count": 0,
        "canonical_N_phi1": 0,
        "canonical_N_phi2": 0,
    }

    for uid, old in enumerate(previous):
        current = _realised_association(evaluation, uid)
        canonical = evaluation.handovers[uid]
        expected_canonical = classify_handover(old, current)
        if canonical is not expected_canonical:
            failures.append(f"user_{uid}_canonical_handover_disagrees_with_ledger")

        if canonical is HandoverClass.INTRA_SATELLITE:
            counts["canonical_N_phi1"] += 1
        elif canonical is HandoverClass.INTER_SATELLITE:
            counts["canonical_N_phi2"] += 1

        if old is None:
            event = "episode_start"
            counts["episode_start_count"] += 1
        elif current is UNSERVED:
            event = "current_unserved"
        elif old is UNSERVED:
            event = "reentry_after_unserved"
            counts["reentry_count"] += 1
        elif not isinstance(old, Association) or not isinstance(current, Association):
            failures.append(f"user_{uid}_unexpected_event_ledger_types")
            event = "invalid"
        elif old.norad_id == current.norad_id and old.cell_id == current.cell_id:
            event = "same_physical_association"
        elif old.norad_id == current.norad_id:
            event = "successful_phi1"
            times[uid] = PHI1_TIME_S
            counts["N_phi1"] += 1
        else:
            event = "successful_phi2"
            times[uid] = PHI2_TIME_S
            counts["N_phi2"] += 1

        if current is UNSERVED:
            counts["unserved_count"] += 1

        expected_for_event = {
            "episode_start": HandoverClass.NONE,
            "current_unserved": HandoverClass.NONE,
            "reentry_after_unserved": HandoverClass.INTER_SATELLITE,
            "same_physical_association": HandoverClass.NONE,
            "successful_phi1": HandoverClass.INTRA_SATELLITE,
            "successful_phi2": HandoverClass.INTER_SATELLITE,
        }.get(event)
        if expected_for_event is not None and canonical is not expected_for_event:
            failures.append(f"user_{uid}_{event}_canonical_class_mismatch")

        events.append(
            {
                "user": int(uid),
                "previous": _association_json(old),
                "current": _association_json(current),
                "temporal_event": event,
                "T_s": float(times[uid]),
                "canonical_handover_class": canonical.value,
                "current_served": current is not UNSERVED,
            }
        )

    if counts["canonical_N_phi1"] != counts["N_phi1"]:
        failures.append("canonical_phi1_count_differs_from_successful_phi1_count")
    if counts["canonical_N_phi2"] != counts["N_phi2"] + counts["reentry_count"]:
        failures.append("canonical_phi2_count_does_not_equal_successful_plus_reentry")

    counts["canonical_phi2_reentry_excess"] = (
        counts["canonical_N_phi2"] - counts["N_phi2"]
    )
    return {
        "times_s": times,
        "events": events,
        "counts": counts,
        "event_table_sha256": _json_sha(events),
        "engineering_failures": sorted(set(failures)),
    }


def _branch_surface(
    evaluation: Any, previous: Sequence[object]
) -> dict[str, Any]:
    rates = np.asarray(evaluation.link_rate_bps, dtype=np.float64).copy()
    power = float(evaluation.system_power_w)
    throughput = float(rates.sum(dtype=np.float64))
    event = _event_surface(evaluation, previous)
    failures = list(event["engineering_failures"])

    if rates.shape != (USERS,):
        failures.append(f"rate_array_shape_{rates.shape}_not_{(USERS,)}")
    if not np.all(np.isfinite(rates)):
        failures.append("rate_array_nonfinite")
    if np.any(rates < 0.0):
        failures.append("rate_array_negative")
    if not math.isfinite(power) or power < 0.0:
        failures.append("payload_system_power_nonfinite_or_negative")
    if power != float(evaluation.energy.system_consumed_power_w):
        failures.append("system_power_disagrees_with_canonical_payload_energy")

    canonical_throughput = float(evaluation.energy.system_throughput_bps)
    throughput_residual = throughput - canonical_throughput
    throughput_tolerance = (
        np.finfo(np.float64).eps * max(1.0, abs(canonical_throughput)) * 8.0
    )
    if abs(throughput_residual) > throughput_tolerance:
        failures.append("rate_sum_disagrees_with_canonical_system_throughput")

    return {
        "rates_bps": rates,
        "power_w": power,
        "throughput_bps": throughput,
        "canonical_throughput_bps": canonical_throughput,
        "throughput_identity_residual_bps": float(throughput_residual),
        "rate_array_sha256": _array_sha(rates),
        "event": event,
        "served": np.asarray(evaluation.resolution.served, dtype=np.bool_).copy(),
        "served_count": int(evaluation.resolution.served_count),
        "engineering_failures": sorted(set(failures)),
    }


def _clock_ledger(surface: dict[str, Any], *, delta_s: float) -> dict[str, Any]:
    rates = surface["rates_bps"]
    times = surface["event"]["times_s"]
    power = float(surface["power_w"])
    throughput = float(surface["throughput_bps"])
    failures = list(surface["engineering_failures"])

    if not math.isfinite(delta_s) or delta_s <= 0.0:
        failures.append("decision_interval_nonfinite_or_nonpositive")
    if not np.all(np.isfinite(times)) or np.any(times < 0.0):
        failures.append("event_time_nonfinite_or_negative")
    if np.any(times > delta_s):
        failures.append("event_time_exceeds_decision_interval")

    b0 = float(delta_s * throughput)
    e0 = float(delta_s * power)
    loss = float(np.dot(rates, times))
    domain_pass = bool(
        math.isfinite(b0)
        and math.isfinite(e0)
        and math.isfinite(loss)
        and e0 > 0.0
        and loss >= 0.0
        and loss <= b0
        and not failures
    )
    if e0 <= 0.0 or not math.isfinite(e0):
        failures.append("E0_must_be_finite_and_positive")
        eta0 = None
        eta_time = None
        r2_sum = None
        residual = None
        tolerance = None
        identity_pass = False
        event_free_exact = False
        relative_damage = None
    else:
        eta0 = float(b0 / e0)
        eta_time = float((b0 - loss) / e0)
        r2 = -rates * times / e0
        r2_sum = float(math.fsum(float(value) for value in r2))
        residual = float(r2_sum - (eta_time - eta0))
        tolerance = float(
            IDENTITY_RELATIVE_TOLERANCE * max(1.0, abs(eta0))
        )
        identity_pass = bool(
            math.isfinite(eta0)
            and math.isfinite(eta_time)
            and math.isfinite(r2_sum)
            and abs(residual) <= tolerance
        )
        event_free_exact = bool(np.any(times) or eta_time == eta0)
        relative_damage = (
            None if eta0 == 0.0 else float(abs((eta0 - eta_time) / eta0))
        )
        if not identity_pass:
            failures.append("time_only_algebraic_identity_failure")
        if not event_free_exact:
            failures.append("event_free_eta_time_not_exactly_eta0")
        if eta_time > eta0:
            failures.append("time_only_eta_exceeds_eta0")

    if loss < 0.0 or loss > b0:
        failures.append("time_loss_outside_zero_to_B0")

    domain_pass = bool(domain_pass and not failures)
    return {
        "Delta_s": float(delta_s),
        "B0_bits": b0,
        "E0_payload_j": e0,
        "L_time_bits": loss,
        "eta0_bits_per_j": eta0,
        "eta_time_bits_per_j": eta_time,
        "sum_r2_time_bits_per_j": r2_sum,
        "identity_residual_bits_per_j": residual,
        "identity_tolerance_bits_per_j": tolerance,
        "identity_pass": identity_pass,
        "event_free_eta_exact_pass": event_free_exact,
        "domain_and_unit_checks_pass": domain_pass,
        "absolute_relative_damage": relative_damage,
        "rate_array_sha256_used_for_B0_and_L": surface["rate_array_sha256"],
        "event_time_array_sha256": _array_sha(times),
        "identical_non_interruption_discounted_rate_array_in_B0_and_L": True,
        "denominator_boundary": "satellite_payload_only",
        "procedure_energy_in_denominator_j": None,
        "procedure_energy_excluded_not_assumed_zero": True,
        "engineering_failures": sorted(set(failures)),
    }


def _clock_pair(
    reference: dict[str, Any], stay: dict[str, Any], *, delta_s: float
) -> dict[str, Any]:
    ref = _clock_ledger(reference, delta_s=delta_s)
    alt = _clock_ledger(stay, delta_s=delta_s)
    ref_eta = ref["eta_time_bits_per_j"]
    alt_eta = alt["eta_time_bits_per_j"]
    delta_eta = (
        None if ref_eta is None or alt_eta is None else float(alt_eta - ref_eta)
    )
    return {
        "reference": ref,
        "stay": alt,
        "comparison": {
            "delta_eta_time_stay_minus_reference_bits_per_j": delta_eta,
            "positive_delta_eta_time": None if delta_eta is None else delta_eta > 0.0,
        },
    }


def _surface_receipt(surface: dict[str, Any], *, focal_user: int) -> dict[str, Any]:
    return {
        "system_throughput_bps": float(surface["throughput_bps"]),
        "system_power_w": float(surface["power_w"]),
        "served_count": int(surface["served_count"]),
        "rate_array_sha256": surface["rate_array_sha256"],
        "event_table_sha256": surface["event"]["event_table_sha256"],
        "event_counts": surface["event"]["counts"],
        "focal_event": surface["event"]["events"][focal_user],
    }


def _ineligible_row(
    *,
    seed: int,
    step: int,
    focal_user: int,
    previous: object,
    baseline_action: int,
    baseline_key: PhysicalKey | None,
    proposal: Any,
) -> dict[str, Any]:
    return {
        "evaluation_seed": int(seed),
        "step_index": int(step),
        "focal_user": int(focal_user),
        "family": v2.R2_FAMILY,
        "status": "ineligible",
        "reason": proposal.reason,
        "previous": _association_json(previous),
        "reference_action": int(baseline_action),
        "reference_key": v2.v1._json_key(baseline_key),
        "stay_action": None,
        "stay_key": None,
        "proposal_frozen_before_current_outcome": True,
    }


def run_rollout(
    trainer: Any,
    wrapped: Any,
    *,
    evaluation_seed: int,
    env_rng: np.random.Generator,
    mobility_rng: np.random.Generator,
    action_rng: np.random.Generator,
    max_steps: int,
) -> dict[str, Any]:
    states, wrapped_masks, observation = wrapped.reset(env_rng, mobility_rng)
    encoded = trainer.encode_states(states)
    proposal_rows: list[dict[str, Any]] = []
    baseline_steps: list[dict[str, Any]] = []
    engineering_failures: list[str] = []

    for _ in range(max_steps):
        masks = np.stack([row.mask for row in wrapped_masks])
        q1 = trainer.scalarized_q_values(encoded, objective_weights=(1.0, 0.0, 0.0))
        baseline_actions = v2.v1.masked_greedy_actions(q1, masks)
        focal_users = [
            int(uid)
            for uid in action_rng.choice(
                USERS, size=FOCAL_USERS_PER_STEP, replace=False
            ).tolist()
        ]
        step_index = int(observation.step_index)
        step_environment = wrapped.environment
        previous = tuple(row.previous for row in step_environment._ledgers)

        # The complete exact-stay census is frozen before any current-slot
        # ActionEvaluation is requested.
        prebuilt: list[tuple[int, PhysicalKey | None, Any]] = []
        for focal_user in focal_users:
            table = observation.candidates.slot_tables[focal_user]
            baseline_action = int(baseline_actions[focal_user])
            baseline_key = v2._key_for_action(table, baseline_action)
            candidates = v2.v1._physical_candidates(
                table,
                prior_demand=observation.user_states[focal_user].beam_loads,
                candidate_sinr=observation.candidate_sinr[focal_user],
                q1=q1[focal_user],
            )
            proposal = v2.state_only_proposal(
                v2.R2_FAMILY,
                baseline_action=baseline_action,
                baseline_key=baseline_key,
                candidates=candidates,
                access_vector=observation.user_states[focal_user].access_vector,
            )
            prebuilt.append((focal_user, baseline_key, proposal))

        baseline_keys = v2.v1.physical_action_keys(
            baseline_actions, observation.candidates.slot_tables
        )
        prestate_sha = _prestate_sha(step_environment)
        env_rng_before = _rng_sha(env_rng)
        baseline = step_environment.evaluate_actions(baseline_actions, env_rng)
        env_rng_after_baseline = _rng_sha(env_rng)
        prestate_after_baseline = _prestate_sha(step_environment)
        if env_rng_after_baseline != env_rng_before:
            engineering_failures.append(
                f"seed_{evaluation_seed}_step_{step_index}_baseline_preview_advanced_rng"
            )
        if prestate_after_baseline != prestate_sha:
            engineering_failures.append(
                f"seed_{evaluation_seed}_step_{step_index}_baseline_preview_mutated_prestate"
            )

        reference_surface = _branch_surface(baseline, previous)
        for failure in reference_surface["engineering_failures"]:
            engineering_failures.append(
                f"seed_{evaluation_seed}_step_{step_index}_reference_{failure}"
            )
        baseline_clocks = {
            name: _clock_ledger(reference_surface, delta_s=delta_s)
            for name, delta_s in CLOCKS
        }
        for name, ledger in baseline_clocks.items():
            for failure in ledger["engineering_failures"]:
                engineering_failures.append(
                    f"seed_{evaluation_seed}_step_{step_index}_reference_{name}_{failure}"
                )

        step_eligible_rows: list[dict[str, Any]] = []
        for focal_user, baseline_key, proposal in prebuilt:
            baseline_action = int(baseline_actions[focal_user])
            old = previous[focal_user]
            if proposal.choice is None:
                proposal_rows.append(
                    _ineligible_row(
                        seed=evaluation_seed,
                        step=step_index,
                        focal_user=focal_user,
                        previous=old,
                        baseline_action=baseline_action,
                        baseline_key=baseline_key,
                        proposal=proposal,
                    )
                )
                continue

            stay_key = proposal.choice.key
            expected_stay_key = (
                (int(old.norad_id), int(old.cell_id))
                if isinstance(old, Association)
                else None
            )
            exact_stay_identity = stay_key == expected_stay_key
            if not exact_stay_identity:
                engineering_failures.append(
                    f"seed_{evaluation_seed}_step_{step_index}_user_{focal_user}_"
                    "proposal_is_not_exact_physical_stay"
                )

            stay_actions = baseline_actions.copy()
            stay_actions[focal_user] = int(proposal.choice.action)
            stay_keys = v2.v1.physical_action_keys(
                stay_actions, observation.candidates.slot_tables
            )
            changed_action_users = (
                np.flatnonzero(stay_actions != baseline_actions).astype(int).tolist()
            )
            changed_physical_users = [
                uid
                for uid, (reference_key, candidate_key) in enumerate(
                    zip(baseline_keys, stay_keys, strict=True)
                )
                if reference_key != candidate_key
            ]
            one_focal_action = changed_action_users == [focal_user]
            one_focal_physical = changed_physical_users == [focal_user]
            if not one_focal_action or not one_focal_physical:
                engineering_failures.append(
                    f"seed_{evaluation_seed}_step_{step_index}_user_{focal_user}_"
                    "not_exactly_one_focal_action_change"
                )

            rng_before_stay = _rng_sha(env_rng)
            stay = step_environment.evaluate_actions(stay_actions, env_rng)
            rng_after_stay = _rng_sha(env_rng)
            prestate_after_stay = _prestate_sha(step_environment)
            common_rng = bool(
                rng_before_stay
                == rng_after_stay
                == env_rng_before
                == env_rng_after_baseline
            )
            preview_state_unchanged = prestate_after_stay == prestate_sha
            if not common_rng:
                engineering_failures.append(
                    f"seed_{evaluation_seed}_step_{step_index}_user_{focal_user}_"
                    "counterfactual_preview_rng_mismatch"
                )
            if not preview_state_unchanged:
                engineering_failures.append(
                    f"seed_{evaluation_seed}_step_{step_index}_user_{focal_user}_"
                    "counterfactual_preview_mutated_prestate"
                )

            stay_surface = _branch_surface(stay, previous)
            for failure in stay_surface["engineering_failures"]:
                engineering_failures.append(
                    f"seed_{evaluation_seed}_step_{step_index}_user_{focal_user}_"
                    f"stay_{failure}"
                )

            clocks = {
                name: _clock_pair(
                    reference_surface,
                    stay_surface,
                    delta_s=delta_s,
                )
                for name, delta_s in CLOCKS
            }
            for name, pair in clocks.items():
                for branch_name in ("reference", "stay"):
                    for failure in pair[branch_name]["engineering_failures"]:
                        engineering_failures.append(
                            f"seed_{evaluation_seed}_step_{step_index}_user_"
                            f"{focal_user}_{branch_name}_{name}_{failure}"
                        )

            reference_served = reference_surface["served"]
            stay_served = stay_surface["served"]
            became_unserved = np.flatnonzero(reference_served & ~stay_served).tolist()
            became_served = np.flatnonzero(~reference_served & stay_served).tolist()
            service_safe = bool(
                stay_surface["served_count"] >= reference_surface["served_count"]
                and stay_served[focal_user]
            )
            row = {
                "evaluation_seed": int(evaluation_seed),
                "step_index": int(step_index),
                "focal_user": int(focal_user),
                "family": v2.R2_FAMILY,
                "status": "evaluated",
                "reason": proposal.reason,
                "previous": _association_json(old),
                "reference_action": baseline_action,
                "stay_action": int(proposal.choice.action),
                "reference_key": v2.v1._json_key(baseline_key),
                "stay_key": v2.v1._json_key(stay_key),
                "proposal_frozen_before_current_outcome": True,
                "exact_visible_incumbent_stay_identity": exact_stay_identity,
                "changed_action_users": changed_action_users,
                "changed_physical_users": changed_physical_users,
                "exactly_one_focal_action_changed": bool(
                    one_focal_action and one_focal_physical
                ),
                "preview_common_rng": common_rng,
                "preview_prestate_unchanged": preview_state_unchanged,
                "baseline_preview_commit_parity": None,
                "reference_branch": _surface_receipt(
                    reference_surface, focal_user=focal_user
                ),
                "stay_branch": _surface_receipt(stay_surface, focal_user=focal_user),
                "service": {
                    "reference_focal_served": bool(reference_served[focal_user]),
                    "stay_focal_served": bool(stay_served[focal_user]),
                    "reference_served_count": int(reference_surface["served_count"]),
                    "stay_served_count": int(stay_surface["served_count"]),
                    "delta_served_count": int(
                        stay_surface["served_count"]
                        - reference_surface["served_count"]
                    ),
                    "became_unserved_user_ids": became_unserved,
                    "became_served_user_ids": became_served,
                    "service_safe_v2": service_safe,
                },
                "delta_system_throughput_bps": float(
                    stay_surface["throughput_bps"]
                    - reference_surface["throughput_bps"]
                ),
                "delta_payload_system_power_w": float(
                    stay_surface["power_w"] - reference_surface["power_w"]
                ),
                "clocks": clocks,
            }
            proposal_rows.append(row)
            step_eligible_rows.append(row)

        result = wrapped.step(baseline_actions, env_rng)
        try:
            v2.v1._assert_full_preview_parity(baseline, wrapped.last_outcome)
            preview_commit_parity = True
            preview_commit_error = None
        except RuntimeError as exc:
            preview_commit_parity = False
            preview_commit_error = str(exc)
            engineering_failures.append(
                f"seed_{evaluation_seed}_step_{step_index}_baseline_preview_commit_"
                f"parity_failure: {exc}"
            )
        for row in step_eligible_rows:
            row["baseline_preview_commit_parity"] = preview_commit_parity

        baseline_steps.append(
            {
                "step_index": int(step_index),
                "focal_users": focal_users,
                "proposal_census_frozen_before_current_outcome": True,
                "preview_common_rng": env_rng_before == env_rng_after_baseline,
                "preview_prestate_unchanged": prestate_sha == prestate_after_baseline,
                "preview_commit_parity": preview_commit_parity,
                "preview_commit_error": preview_commit_error,
                "reference_branch": _surface_receipt(
                    reference_surface, focal_user=focal_users[0]
                ),
                "clocks": baseline_clocks,
            }
        )

        if result.done or len(baseline_steps) >= max_steps:
            break
        states = result.user_states
        wrapped_masks = result.action_masks
        observation = wrapped.last_outcome.observation
        encoded = trainer.encode_states(states)

    return {
        "evaluation_seed": int(evaluation_seed),
        "steps": len(baseline_steps),
        "baseline_steps": baseline_steps,
        "proposal_rows": proposal_rows,
        "engineering_failures": sorted(set(engineering_failures)),
    }


def _t95(seed_means: list[float], *, formal: bool) -> dict[str, Any]:
    if formal and len(seed_means) == 10:
        mean = float(statistics.fmean(seed_means))
        sample_sd = float(statistics.stdev(seed_means))
        half_width = SEED_T95_DF9 * sample_sd / math.sqrt(10.0)
        return {
            "estimable": True,
            "n_seed_means": 10,
            "df": 9,
            "critical_value": SEED_T95_DF9,
            "mean": mean,
            "sample_sd": sample_sd,
            "lower": float(mean - half_width),
            "upper": float(mean + half_width),
        }
    return {
        "estimable": False,
        "n_seed_means": len(seed_means),
        "df": None,
        "critical_value": SEED_T95_DF9,
        "mean": float(statistics.fmean(seed_means)) if seed_means else None,
        "sample_sd": (
            float(statistics.stdev(seed_means)) if len(seed_means) >= 2 else None
        ),
        "lower": None,
        "upper": None,
        "reason": "ten-seed t95 is reported only for the frozen formal campaign",
    }


def _effect_summary(
    rollouts: Sequence[dict[str, Any]], *, clock: str, formal: bool
) -> dict[str, Any]:
    by_seed: list[dict[str, Any]] = []
    all_values: list[float] = []
    seed_means: list[float] = []
    for rollout in rollouts:
        rows = [
            row
            for row in rollout["proposal_rows"]
            if row["status"] == "evaluated"
        ]
        values = [
            float(
                row["clocks"][clock]["comparison"][
                    "delta_eta_time_stay_minus_reference_bits_per_j"
                ]
            )
            for row in rows
        ]
        mean = float(statistics.fmean(values)) if values else None
        if mean is not None:
            seed_means.append(mean)
        all_values.extend(values)
        positive = sum(value > 0.0 for value in values)
        by_seed.append(
            {
                "seed": int(rollout["evaluation_seed"]),
                "eligible": len(values),
                "positive_delta_eta_time": positive,
                "positive_fraction": float(positive / len(values)) if values else None,
                "mean_delta_eta_time_bits_per_j": mean,
                "positive_mean": None if mean is None else mean > 0.0,
            }
        )

    positive_total = sum(value > 0.0 for value in all_values)
    return {
        "eligible_pairs": len(all_values),
        "positive_delta_eta_time_pairs": positive_total,
        "positive_pair_fraction": (
            float(positive_total / len(all_values)) if all_values else None
        ),
        "seeds_with_any_positive_pair": sum(
            row["positive_delta_eta_time"] > 0 for row in by_seed
        ),
        "seeds_with_positive_mean": sum(row["positive_mean"] is True for row in by_seed),
        "mean_paired_effect_bits_per_j": (
            float(statistics.fmean(all_values)) if all_values else None
        ),
        "by_seed": by_seed,
        "ten_seed_t95_of_seed_mean_effect": _t95(seed_means, formal=formal),
        "threshold_tuning_performed": False,
    }


def _damage_summary(
    rollouts: Sequence[dict[str, Any]], *, clock: str, formal: bool
) -> dict[str, Any]:
    all_values: list[float] = []
    seed_means: list[float] = []
    by_seed: list[dict[str, Any]] = []
    for rollout in rollouts:
        values = [
            float(step["clocks"][clock]["absolute_relative_damage"])
            for step in rollout["baseline_steps"]
        ]
        mean = float(statistics.fmean(values)) if values else None
        if mean is not None:
            seed_means.append(mean)
        all_values.extend(values)
        by_seed.append(
            {
                "seed": int(rollout["evaluation_seed"]),
                "steps": len(values),
                "mean_absolute_relative_damage": mean,
            }
        )
    return {
        "reference_steps": len(all_values),
        "mean_absolute_relative_damage": (
            float(statistics.fmean(all_values)) if all_values else None
        ),
        "median_absolute_relative_damage": (
            float(statistics.median(all_values)) if all_values else None
        ),
        "minimum_absolute_relative_damage": min(all_values) if all_values else None,
        "maximum_absolute_relative_damage": max(all_values) if all_values else None,
        "by_seed": by_seed,
        "ten_seed_t95_of_seed_mean_damage": _t95(seed_means, formal=formal),
        "scientific_negligibility_threshold": None,
        "interpretation": "reported scale only; no threshold was selected or tuned",
    }


def _input_parity(
    rollouts: Sequence[dict[str, Any]], *, formal: bool
) -> dict[str, Any]:
    rows = [row for rollout in rollouts for row in rollout["proposal_rows"]]
    eligible = [row for row in rows if row["status"] == "evaluated"]
    unsafe = [row for row in eligible if not row["service"]["service_safe_v2"]]
    eligible_by_seed = {
        int(seed): sum(
            row["status"] == "evaluated" and row["evaluation_seed"] == seed
            for row in rows
        )
        for seed in FROZEN_SEEDS
    }
    schedule = [
        {
            "seed": int(rollout["evaluation_seed"]),
            "steps": [
                {
                    "step": int(step["step_index"]),
                    "focal_users": step["focal_users"],
                }
                for step in rollout["baseline_steps"]
            ],
        }
        for rollout in rollouts
    ]
    census = [
        (
            int(row["evaluation_seed"]),
            int(row["step_index"]),
            int(row["focal_user"]),
            row["status"],
            row["reason"],
            int(row["reference_action"]),
            None if row["stay_action"] is None else int(row["stay_action"]),
        )
        for row in rows
    ]
    eligible_keys = [
        (int(row["evaluation_seed"]), int(row["step_index"]), int(row["focal_user"]))
        for row in eligible
    ]
    unsafe_keys = [
        (int(row["evaluation_seed"]), int(row["step_index"]), int(row["focal_user"]))
        for row in unsafe
    ]

    observed = {
        "focal_rows": len(rows),
        "eligible": len(eligible),
        "ineligible": len(rows) - len(eligible),
        "service_unsafe": len(unsafe),
        "service_unsafe_keys": [list(key) for key in unsafe_keys],
        "eligible_by_seed": eligible_by_seed,
        "focal_schedule_sha256": _json_sha(schedule),
        "r2_census_sha256": _json_sha(census),
        "eligible_key_sha256": _json_sha(eligible_keys),
    }
    expected = {
        "focal_rows": EXPECTED_FOCAL_ROWS,
        "eligible": EXPECTED_ELIGIBLE,
        "ineligible": EXPECTED_FOCAL_ROWS - EXPECTED_ELIGIBLE,
        "service_unsafe": EXPECTED_SERVICE_UNSAFE,
        "service_unsafe_keys": [list(EXPECTED_UNSAFE_KEY)],
        "eligible_by_seed": EXPECTED_ELIGIBLE_BY_SEED,
        "focal_schedule_sha256": EXPECTED_V2_FOCAL_SCHEDULE_SHA256,
        "r2_census_sha256": EXPECTED_V2_R2_CENSUS_SHA256,
        "eligible_key_sha256": EXPECTED_V2_ELIGIBLE_KEY_SHA256,
    }
    checks = {
        name: observed[name] == expected[name]
        for name in (
            "focal_rows",
            "eligible",
            "ineligible",
            "service_unsafe",
            "service_unsafe_keys",
            "eligible_by_seed",
            "focal_schedule_sha256",
            "r2_census_sha256",
            "eligible_key_sha256",
        )
    }
    return {
        "applicable": formal,
        "expected_v2": expected,
        "observed": observed,
        "checks": checks if formal else None,
        "pass": bool(formal and all(checks.values())),
        "pilot_note": (
            None
            if formal
            else "partial seed/step smoke cannot adjudicate the frozen 758/1 parity"
        ),
    }


def _campaign_summary(
    rollouts: list[dict[str, Any]], *, formal: bool
) -> dict[str, Any]:
    parity = _input_parity(rollouts, formal=formal)
    engineering_failures = sorted(
        {
            failure
            for rollout in rollouts
            for failure in rollout["engineering_failures"]
        }
    )
    effects = {
        name: _effect_summary(rollouts, clock=name, formal=formal)
        for name, _delta_s in CLOCKS
    }
    reference_damage = {
        name: _damage_summary(rollouts, clock=name, formal=formal)
        for name, _delta_s in CLOCKS
    }
    if formal and not parity["pass"]:
        decision = "INPUT_PARITY_FAILURE"
    elif engineering_failures:
        decision = "IDENTITY_FAILURE"
    elif formal:
        decision = "IDENTITY_SCALE_PASS"
    else:
        decision = "PILOT_NOT_ADJUDICATED"
    return {
        "input_parity": parity,
        "engineering_failures": engineering_failures,
        "paired_effects": effects,
        "main_reference_absolute_relative_damage": reference_damage,
        "decision": decision,
    }


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _verify_static_authority(args: argparse.Namespace) -> dict[str, bool]:
    v2_receipt = _read_json(V2_RECEIPT)
    checks = {
        "c2_spec_sha256_verified": _sha256(SPEC) == SPEC_SHA256,
        "adr004_sha256_verified": _sha256(ADR) == ADR_SHA256,
        "source_drift_manifest_sha256_verified": (
            _sha256(SOURCE_DRIFT_MANIFEST) == SOURCE_DRIFT_MANIFEST_SHA256
        ),
        "v2_runner_sha256_verified": _sha256(V2_RUNNER) == V2_RUNNER_SHA256,
        "v2_import_path_verified": (
            Path(v2.__file__).resolve() == V2_RUNNER.resolve()
        ),
        "oracle_helper_sha256_verified": (
            _sha256(ORACLE_HELPER) == ORACLE_HELPER_SHA256
        ),
        "oracle_helper_import_path_verified": (
            Path(v2.v1.__file__).resolve() == ORACLE_HELPER.resolve()
        ),
        "checkpoint_loader_helper_sha256_verified": (
            _sha256(CHECKPOINT_LOADER_HELPER)
            == CHECKPOINT_LOADER_HELPER_SHA256
        ),
        "checkpoint_loader_import_path_verified": (
            Path(checkpoint_loader.__file__).resolve()
            == CHECKPOINT_LOADER_HELPER.resolve()
        ),
        "checkpoint_loader_symbol_binding_verified": all(
            getattr(v2.v1, name) is getattr(checkpoint_loader, name)
            for name in (
                "_frozen_archive",
                "_make_environment",
                "_sha256",
                "_verify_and_load_trainer",
            )
        ),
        "v2_spec_sha256_verified": _sha256(V2_SPEC) == V2_SPEC_SHA256,
        "v2_confirmation_receipt_sha256_verified": (
            _sha256(V2_RECEIPT) == V2_RECEIPT_SHA256
        ),
        "prereg_file_sha256_verified": (
            _sha256(args.prereg) == EXPECTED_PREREG_FILE_SHA256
        ),
        "v2_receipt_embedded_runner_sha256_verified": (
            v2_receipt.get("analysis_sha256") == V2_RUNNER_SHA256
        ),
        "v2_receipt_historical_analysis_code_sha256_verified": (
            v2_receipt.get("analysis_code_sha256")
            == EXPECTED_V2_RECEIPT_ANALYSIS_CODE_SHA256
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(
            "INPUT_PARITY_FAILURE: frozen authority verification failed: "
            + ", ".join(failed)
        )
    return checks


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=v2.v1.DEFAULT_INPUT)
    parser.add_argument("--prereg", type=Path, default=v2.v1.DEFAULT_PREREG)
    parser.add_argument(
        "--tle-root", type=Path, default=Path(TLE_ROOT_DEFAULT).expanduser()
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seeds", type=int, nargs="+", default=list(FROZEN_SEEDS))
    parser.add_argument("--max-steps", type=int, default=FORMAL_STEPS)
    return parser.parse_args()


def _publish_json(payload: dict[str, Any], destination: Path) -> tuple[str, int]:
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
    published = False
    digest = hashlib.sha256(encoded).hexdigest()
    try:
        with handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        if _sha256(temporary) != digest:
            raise RuntimeError("staged C2 JSON hash differs from encoded bytes")
        os.link(temporary, destination)
        published = True
        if _sha256(destination) != digest:
            raise RuntimeError("published C2 JSON hash differs from staged artifact")
        return digest, len(encoded)
    except BaseException:
        if published:
            destination.unlink(missing_ok=True)
        raise
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    args = _arguments()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {args.output}")
    if len(set(args.seeds)) != len(args.seeds):
        raise ValueError("--seeds must be unique")
    if any(seed not in FROZEN_SEEDS for seed in args.seeds):
        raise ValueError("every seed must belong to frozen 2026082401..2026082410")
    if not 1 <= args.max_steps <= FORMAL_STEPS:
        raise ValueError("--max-steps must lie in [1, 10]")

    formal = tuple(args.seeds) == FROZEN_SEEDS and args.max_steps == FORMAL_STEPS
    authority_checks = _verify_static_authority(args)
    record = read_prereg(args.prereg)
    if record.digest != EXPECTED_PREREG_DIGEST:
        raise RuntimeError("INPUT_PARITY_FAILURE: prereg self-digest changed")

    status_path = args.input_dir / "main" / "status.json"
    status = _read_json(status_path)
    if status.get("prereg_digest") != EXPECTED_PREREG_DIGEST:
        raise RuntimeError("INPUT_PARITY_FAILURE: Main status prereg digest changed")
    run_fingerprint = status.get("run_fingerprint")
    if not isinstance(run_fingerprint, dict):
        raise RuntimeError("INPUT_PARITY_FAILURE: Main status has no run fingerprint")
    if run_fingerprint.get("prereg_digest") != EXPECTED_PREREG_DIGEST:
        raise RuntimeError(
            "INPUT_PARITY_FAILURE: Main run fingerprint prereg digest changed"
        )
    frozen_seed_sets = run_fingerprint.get("frozen_seed_sets")
    if not isinstance(frozen_seed_sets, dict) or tuple(
        frozen_seed_sets.get("p6_evaluation", ())
    ) != FROZEN_SEEDS:
        raise RuntimeError(
            "INPUT_PARITY_FAILURE: Main run fingerprint evaluation seeds changed"
        )
    if run_fingerprint.get("code_sha256") != EXPECTED_LAUNCHED_CODE_SHA256:
        raise RuntimeError(
            "INPUT_PARITY_FAILURE: launched training code fingerprint changed"
        )

    current_code_sha = _code_sha256(_default_code_paths())
    if current_code_sha != EXPECTED_ANALYSIS_CODE_SHA256:
        raise RuntimeError(
            "INPUT_PARITY_FAILURE: analysis source differs from reviewed manifest"
        )
    runner_path = Path(__file__).resolve()
    runner_sha = _sha256(runner_path)
    with tempfile.TemporaryDirectory(prefix="mcrl-c2-time-only-") as temporary:
        archive = v2.v1._frozen_archive(
            record, args.tle_root, Path(temporary) / "frozen-tle"
        )
        trainer, checkpoint = v2.v1._verify_and_load_trainer(
            record,
            archive,
            run_dir=args.input_dir / "main",
            users=USERS,
        )
        if checkpoint["checkpoint_sha256"] != EXPECTED_CHECKPOINT_SHA256:
            raise RuntimeError("INPUT_PARITY_FAILURE: checkpoint digest changed")
        if checkpoint["launched_code_sha256"] != EXPECTED_LAUNCHED_CODE_SHA256:
            raise RuntimeError(
                "INPUT_PARITY_FAILURE: checkpoint launched-code fingerprint changed"
            )
        rollouts = []
        for seed in args.seeds:
            wrapped = v2.v1._make_environment(archive, users=USERS)
            env_rng, mobility_rng, action_rng, _control_rng = _evaluation_rngs(seed)
            rollouts.append(
                run_rollout(
                    trainer,
                    wrapped,
                    evaluation_seed=seed,
                    env_rng=env_rng,
                    mobility_rng=mobility_rng,
                    action_rng=action_rng,
                    max_steps=args.max_steps,
                )
            )

    campaign = _campaign_summary(rollouts, formal=formal)
    payload = {
        "schema": "mcrl-c2-time-only-identity-scale-v1",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "complete",
        "stage": "frozen_formal_campaign" if formal else "engineering_pilot",
        "formal_decision_adjudicated": formal,
        "mode": (
            "evaluation-only legacy sensitivity; exact-stay counterfactual census; "
            "no optimizer, replay, reward, runtime, preregistration, or training update"
        ),
        "claim_boundary": (
            "at most exact payload-boundary time-only algebra and conditional "
            "62/142-ms scale evidence; not accepted timing parameters, learning, "
            "Main transfer, implementation, or training authority"
        ),
        "decision": campaign["decision"],
        "campaign_summary": campaign,
        "configuration": {
            "evaluation_seeds": list(args.seeds),
            "frozen_formal_seeds": list(FROZEN_SEEDS),
            "users": USERS,
            "focal_users_per_step": FOCAL_USERS_PER_STEP,
            "max_steps": args.max_steps,
            "formal_steps": FORMAL_STEPS,
            "primary_decision_interval_s": PRIMARY_DELTA_S,
            "D2_clock_scale_sensitivity_interval_s": D2_CLOCK_DELTA_S,
            "conditional_time_sensitivity_s": {
                "phi1": PHI1_TIME_S,
                "phi2": PHI2_TIME_S,
            },
            "identity_relative_tolerance": IDENTITY_RELATIVE_TOLERANCE,
            "seed_t95_critical_df9": SEED_T95_DF9,
            "command_argv": list(sys.argv),
        },
        "event_semantics": {
            "episode_start": "T=0",
            "previous_or_current_unserved": "T=0",
            "reentry_after_unserved": (
                "T=0 here although canonical diagnostic R2 remains phi2"
            ),
            "same_physical_satellite_and_cell": "T=0",
            "same_satellite_different_cell": "conditional T=0.062 s",
            "different_satellite": "conditional T=0.142 s",
            "successful_handover_only": True,
        },
        "ledger_contract": {
            "B0": "Delta * sum_u R_u",
            "E0": "Delta * P_system_payload",
            "L": "sum_u R_u * T_u",
            "eta0": "B0 / E0",
            "eta_time": "(B0 - L) / E0",
            "r2_time_u": "-R_u * T_u / E0",
            "procedure_energy_term": None,
            "procedure_energy_excluded_not_assumed_zero": True,
            "same_rate_array_required_for_B0_and_L": True,
        },
        "frozen_inputs": {
            "authority_checks": authority_checks,
            "c2_spec_path": str(SPEC),
            "c2_spec_sha256": SPEC_SHA256,
            "adr004_path": str(ADR),
            "adr004_sha256": ADR_SHA256,
            "source_drift_manifest_path": str(SOURCE_DRIFT_MANIFEST),
            "source_drift_manifest_sha256": SOURCE_DRIFT_MANIFEST_SHA256,
            "v2_runner_path": str(V2_RUNNER),
            "v2_runner_sha256": V2_RUNNER_SHA256,
            "oracle_helper_path": str(ORACLE_HELPER),
            "oracle_helper_sha256": ORACLE_HELPER_SHA256,
            "checkpoint_loader_helper_path": str(CHECKPOINT_LOADER_HELPER),
            "checkpoint_loader_helper_sha256": CHECKPOINT_LOADER_HELPER_SHA256,
            "v2_spec_path": str(V2_SPEC),
            "v2_spec_sha256": V2_SPEC_SHA256,
            "v2_confirmation_receipt_path": str(V2_RECEIPT),
            "v2_confirmation_receipt_sha256": V2_RECEIPT_SHA256,
            "prereg_path": str(args.prereg),
            "prereg_digest": record.digest,
            "prereg_file_sha256": _sha256(args.prereg),
            "checkpoint": checkpoint,
            "frozen_tle_contract_verified": True,
        },
        "analysis": {
            "runner_path": str(runner_path),
            "runner_sha256": runner_sha,
            "analysis_code_sha256": current_code_sha,
            "launched_training_code_sha256": checkpoint["launched_code_sha256"],
            "analysis_source_matches_training": (
                current_code_sha == checkpoint["launched_code_sha256"]
            ),
            "analysis_source_drift_review": {
                "passed": bool(
                    current_code_sha == EXPECTED_ANALYSIS_CODE_SHA256
                    and checkpoint["launched_code_sha256"]
                    == EXPECTED_LAUNCHED_CODE_SHA256
                    and _sha256(SOURCE_DRIFT_MANIFEST)
                    == SOURCE_DRIFT_MANIFEST_SHA256
                ),
                "manifest_path": str(SOURCE_DRIFT_MANIFEST),
                "manifest_sha256": SOURCE_DRIFT_MANIFEST_SHA256,
                "expected_analysis_code_sha256": EXPECTED_ANALYSIS_CODE_SHA256,
                "expected_launched_code_sha256": EXPECTED_LAUNCHED_CODE_SHA256,
                "claim": (
                    "compatibility exception for this evaluation-only C2 gate; "
                    "formal validity still requires exact v2 census reproduction "
                    "and every preview, event, unit, and algebra identity check"
                ),
            },
            "output_json_sha256": (
                "printed only after fail-closed publication because a file cannot "
                "contain its own byte hash"
            ),
        },
        "provenance": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "torch": _package_version("torch"),
            "sgp4": _package_version("sgp4"),
            "independent_unit": "evaluation seed; focal rows cluster within seed",
            "baseline_policy": "frozen masked-greedy Q1-only Main",
            "challenger": "one focal exact visible incumbent stay",
            "proposal_timing": "all ten focal proposals fixed before current outcome",
            "trajectory": "baseline Q1-only Main commits; counterfactual stays are discarded",
        },
        "rollouts": rollouts,
    }
    output_sha, output_bytes = _publish_json(payload, args.output)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "output_sha256": output_sha,
                "output_bytes": output_bytes,
                "decision": campaign["decision"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
