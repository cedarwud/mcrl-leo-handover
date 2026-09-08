"""Independent receipt merge, cluster inference, and terminal decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from math import sqrt
from pathlib import Path
from statistics import NormalDist
from typing import Mapping, Sequence

import numpy as np

from .canonical import (
    StageCContractError,
    file_sha256,
    float_hex,
    parse_float_hex,
    write_once_json,
)
from .evaluation import (
    AllocationManifest,
    AttemptRegistry,
    POLICY_ORDER,
    read_unit_receipt,
    reaggregate_steps,
)
from .learner import ARM_ORDER
from .state import Q1_SCHEMA_SHA256, Q2_SCHEMA_SHA256


REPORT_SCHEMA = "mcrl-v025-stagec-terminal-report-v1-draft"
DROP_ARMS = ("DROP_C1", "DROP_C2", "DROP_C3")
EE_MARGIN_RELATIVE = 0.005
AVAILABILITY_MARGIN = -0.005
HANDOVER_RELATIVE_MARGIN = 0.05
PHI_COST_RELATIVE_MARGIN = 0.05
ZERO_BIT_DISPOSITION = (
    "bits_zero_with_positive_energy_is_defined_ee_zero;"
    "relative_gain_is_undefined_only_when_the_comparator_ee_is_zero;"
    "undefined_draws_are_counted_and_fail_the_affected_gate"
)


@dataclass(slots=True)
class AdditiveTotals:
    bits: float = 0.0
    joules: float = 0.0
    complete_num: int = 0
    complete_den: int = 0
    handover_num: int = 0
    handover_den: int = 0
    phi_num: int = 0
    phi_den: int = 0

    def add(self, other: "AdditiveTotals") -> None:
        self.bits += other.bits
        self.joules += other.joules
        self.complete_num += other.complete_num
        self.complete_den += other.complete_den
        self.handover_num += other.handover_num
        self.handover_den += other.handover_den
        self.phi_num += other.phi_num
        self.phi_den += other.phi_den

    def multiplied(self, count: int) -> "AdditiveTotals":
        return AdditiveTotals(
            self.bits * count,
            self.joules * count,
            self.complete_num * count,
            self.complete_den * count,
            self.handover_num * count,
            self.handover_den * count,
            self.phi_num * count,
            self.phi_den * count,
        )


def _totals(summary: Mapping[str, object]) -> AdditiveTotals:
    result = AdditiveTotals(
        bits=parse_float_hex(summary["bits_hex"], field="summary.bits"),
        joules=parse_float_hex(summary["joules_hex"], field="summary.joules"),
        complete_num=int(summary["complete_service_numerator"]),
        complete_den=int(summary["complete_service_denominator"]),
        handover_num=int(summary["handover_numerator"]),
        handover_den=int(summary["handover_denominator"]),
        phi_num=int(summary["phi_cost_numerator_half_units"]),
        phi_den=int(summary["phi_cost_denominator_half_user_steps"]),
    )
    if (
        result.bits < 0
        or result.joules <= 0
        or result.complete_den <= 0
        or result.handover_den <= 0
        or result.phi_den <= 0
    ):
        raise StageCContractError("invalid independently aggregated totals")
    return result


def _assert_step_is_canonical(row: Mapping[str, object]) -> None:
    components = row.get("energy_components_j_hex")
    events = row.get("events")
    if not isinstance(components, dict) or not components:
        raise StageCContractError("step energy component ledger is missing")
    component_sum = sum(
        parse_float_hex(value, field=f"energy.{name}")
        for name, value in sorted(components.items())
    )
    joules = parse_float_hex(row.get("joules_hex"), field="step.joules")
    if component_sum.hex() != joules.hex():
        raise StageCContractError("step energy component sum disagrees with joules")
    if not isinstance(events, list):
        raise StageCContractError("step physical event ledger is missing")
    allowed = {
        "unchanged", "beam_change", "satellite_change", "cell_rekey",
        "initial_entry", "reentry", "exit",
    }
    for event in events:
        if (
            not isinstance(event, dict)
            or event.get("event_type") not in allowed
            or "prior_physical_identity" not in event
            or "current_physical_identity" not in event
        ):
            raise StageCContractError("step physical event identity is incomplete")
    user_ids = [event["user_id"] for event in events]
    if (
        len(set(user_ids)) != len(user_ids)
        or len(events) != int(row.get("complete_service_denominator", -1))
        or len(events) != int(row.get("handover_denominator", -1))
    ):
        raise StageCContractError("step user roster or QoS denominator drifted")


def _totals_payload(value: AdditiveTotals) -> dict[str, object]:
    return {
        "bits_hex": float_hex(value.bits),
        "joules_hex": float_hex(value.joules),
        "complete_service_numerator": value.complete_num,
        "complete_service_denominator": value.complete_den,
        "handover_numerator": value.handover_num,
        "handover_denominator": value.handover_den,
        "phi_cost_numerator_half_units": value.phi_num,
        "phi_cost_denominator_half_user_steps": value.phi_den,
    }


def _ratio(numerator: float | int, denominator: float | int) -> float | None:
    return None if denominator == 0 else float(numerator) / float(denominator)


def _metrics(full: AdditiveTotals, drop: AdditiveTotals) -> dict[str, float | None]:
    full_ee = _ratio(full.bits, full.joules)
    drop_ee = _ratio(drop.bits, drop.joules)
    ee_relative = (
        None if full_ee is None or drop_ee in (None, 0.0) else full_ee / drop_ee - 1.0
    )
    full_availability = _ratio(full.complete_num, full.complete_den)
    drop_availability = _ratio(drop.complete_num, drop.complete_den)
    availability_difference = (
        None
        if full_availability is None or drop_availability is None
        else full_availability - drop_availability
    )
    full_handover = _ratio(full.handover_num, full.handover_den)
    drop_handover = _ratio(drop.handover_num, drop.handover_den)
    handover_relative = (
        None
        if full_handover is None or drop_handover in (None, 0.0)
        else full_handover / drop_handover - 1.0
    )
    full_phi = _ratio(full.phi_num, full.phi_den)
    drop_phi = _ratio(drop.phi_num, drop.phi_den)
    phi_relative = (
        None
        if full_phi is None or drop_phi in (None, 0.0)
        else full_phi / drop_phi - 1.0
    )
    return {
        "ee_relative": ee_relative,
        "availability_difference": availability_difference,
        "handover_relative": handover_relative,
        "phi_cost_relative": phi_relative,
    }


def _interval(values: Sequence[float]) -> tuple[float, float] | None:
    if not values:
        return None
    lower, upper = np.quantile(
        np.asarray(values, dtype=np.float64), [0.025, 0.975], method="linear"
    )
    return float(lower), float(upper)


def _sum_selected(
    clusters: Mapping[tuple[str, int], Mapping[str, AdditiveTotals]],
    selected: Sequence[tuple[str, int]],
    arm: str,
) -> AdditiveTotals:
    result = AdditiveTotals()
    for key in selected:
        result.add(clusters[key][arm])
    return result


def _bootstrap(
    clusters: Mapping[tuple[str, int], Mapping[str, AdditiveTotals]],
    *,
    drop_arm: str,
    draws: int,
    seed: int,
) -> dict[str, object]:
    keys = sorted(clusters)
    rng = np.random.default_rng(seed)
    samples: dict[str, list[float]] = {
        "ee_relative": [],
        "availability_difference": [],
        "handover_relative": [],
        "phi_cost_relative": [],
    }
    undefined = {key: 0 for key in samples}
    for _ in range(draws):
        selected = [keys[int(index)] for index in rng.integers(0, len(keys), len(keys))]
        values = _metrics(
            _sum_selected(clusters, selected, "FULL"),
            _sum_selected(clusters, selected, drop_arm),
        )
        for metric, value in values.items():
            if value is None or not np.isfinite(value):
                undefined[metric] += 1
            else:
                samples[metric].append(float(value))
    return {
        "draws": draws,
        "central_95_percentile_intervals": {
            metric: _interval(values) for metric, values in samples.items()
        },
        "undefined_draws": undefined,
        "quantile_method": "numpy.quantile linear",
    }


def _two_way_bootstrap(
    clusters: Mapping[tuple[str, int], Mapping[str, AdditiveTotals]],
    *,
    drop_arm: str,
    draws: int,
    seed: int,
) -> dict[str, object]:
    dates = sorted({key[0] for key in clusters})
    seeds = sorted({key[1] for key in clusters})
    expected = {(date, learner_seed) for date in dates for learner_seed in seeds}
    if set(clusters) != expected:
        return {"status": "UNDEFINED_INCOMPLETE_DATE_X_SEED_RECTANGLE"}
    rng = np.random.default_rng(seed)
    values: list[float] = []
    undefined = 0
    for _ in range(draws):
        sampled_dates = [dates[int(i)] for i in rng.integers(0, len(dates), len(dates))]
        sampled_seeds = [seeds[int(i)] for i in rng.integers(0, len(seeds), len(seeds))]
        selected = [
            (date, learner_seed)
            for date in sampled_dates
            for learner_seed in sampled_seeds
        ]
        metric = _metrics(
            _sum_selected(clusters, selected, "FULL"),
            _sum_selected(clusters, selected, drop_arm),
        )["ee_relative"]
        if metric is None or not np.isfinite(metric):
            undefined += 1
        else:
            values.append(float(metric))
    return {
        "status": "OK",
        "central_95_percentile_interval": _interval(values),
        "undefined_draws": undefined,
        "draws": draws,
    }


def _delta_method_ee(
    clusters: Mapping[tuple[str, int], Mapping[str, AdditiveTotals]],
    drop_arm: str,
) -> dict[str, float] | dict[str, str]:
    rows = np.asarray(
        [
            [
                arms["FULL"].bits,
                arms["FULL"].joules,
                arms[drop_arm].bits,
                arms[drop_arm].joules,
            ]
            for _, arms in sorted(clusters.items())
        ],
        dtype=np.float64,
    )
    if rows.shape[0] < 2 or np.any(rows.sum(axis=0) == 0):
        return {"status": "UNDEFINED"}
    means = rows.mean(axis=0)
    bf, ef, bd, ed = means
    estimate = (bf * ed) / (ef * bd) - 1.0
    gradient = np.asarray(
        [
            ed / (ef * bd),
            -(bf * ed) / (ef * ef * bd),
            -(bf * ed) / (ef * bd * bd),
            bf / (ef * bd),
        ]
    )
    covariance_of_mean = np.cov(rows, rowvar=False, ddof=1) / rows.shape[0]
    variance = float(gradient @ covariance_of_mean @ gradient)
    standard_error = sqrt(max(0.0, variance))
    z = NormalDist().inv_cdf(0.975)
    return {
        "status": "OK",
        "estimate": float(estimate),
        "standard_error": standard_error,
        "lower": float(estimate - z * standard_error),
        "upper": float(estimate + z * standard_error),
    }


def admission_decision(
    *,
    acceptance_suite_pass: bool,
    oracle_positive_by_route: Mapping[str, bool],
    qos_pass: bool,
    genuine_joint_headroom: bool,
    s0_relative_gain: float,
    zero_bit_disposition_sealed: bool,
) -> dict[str, object]:
    required_routes = {"C1", "C2", "C3"}
    route_pass = set(oracle_positive_by_route) == required_routes and all(
        oracle_positive_by_route.values()
    )
    admitted = all(
        (
            acceptance_suite_pass,
            route_pass,
            qos_pass,
            genuine_joint_headroom,
            s0_relative_gain >= 0.01,
            zero_bit_disposition_sealed,
        )
    )
    return {
        "decision": "PHYSICS-GO" if admitted else "HOLD",
        "acceptance_suite_pass": acceptance_suite_pass,
        "oracle_positive_by_route": dict(oracle_positive_by_route),
        "qos_pass": qos_pass,
        "genuine_joint_headroom": genuine_joint_headroom,
        "s0_relative_gain": s0_relative_gain,
        "zero_bit_disposition_sealed": zero_bit_disposition_sealed,
    }


def claim_decision(contrasts: Mapping[str, Mapping[str, object]]) -> dict[str, object]:
    per_contrast: dict[str, bool] = {}
    for arm in DROP_ARMS:
        result = contrasts.get(arm)
        if result is None:
            per_contrast[arm] = False
            continue
        intervals = result["bootstrap"]["central_95_percentile_intervals"]
        undefined = result["bootstrap"]["undefined_draws"]
        ee = intervals["ee_relative"]
        availability = intervals["availability_difference"]
        handover = intervals["handover_relative"]
        phi = intervals["phi_cost_relative"]
        per_contrast[arm] = bool(
            ee is not None
            and availability is not None
            and handover is not None
            and phi is not None
            and not any(undefined.values())
            and ee[0] > EE_MARGIN_RELATIVE
            and availability[0] > AVAILABILITY_MARGIN
            and handover[1] < HANDOVER_RELATIVE_MARGIN
            and phi[1] < PHI_COST_RELATIVE_MARGIN
        )
    passed = all(per_contrast.values()) and set(per_contrast) == set(DROP_ARMS)
    return {
        "decision": "CLAIM_PASS" if passed else "CLAIM_FAIL",
        "per_contrast": per_contrast,
        "wording": (
            "TRAIN-panel conditional intersection-union claim: with the other two "
            "components enabled, each FULL-minus-DROP relative pooled-EE lower "
            "bound exceeds +0.5%, and FULL is QoS non-inferior."
        ),
        "multiplicity": "single prespecified conjunction; no per-contrast inflation",
    }


def merge_receipts(
    receipt_paths: Sequence[str | Path],
    *,
    manifest: AllocationManifest,
    registry: AttemptRegistry,
    bootstrap_draws: int | None = None,
    bootstrap_seed: int | None = None,
    physics_admission: Mapping[str, object] | None = None,
    artifact_digests: Mapping[str, object] | None = None,
    interface_assumptions: Sequence[str] = (),
    controller_decide: Sequence[str] = (),
) -> dict[str, object]:
    draws = manifest.bootstrap_draws if bootstrap_draws is None else bootstrap_draws
    seed = manifest.bootstrap_seed if bootstrap_seed is None else bootstrap_seed
    if draws != manifest.bootstrap_draws or seed != manifest.bootstrap_seed:
        raise StageCContractError("merge bootstrap parameters differ from allocation")
    records = registry.records()
    status_by_key: dict[str, list[Mapping[str, object]]] = {}
    for record in records:
        status_by_key.setdefault(str(record["attempt_key"]), []).append(record)
    expected = {unit.unit_id: unit for unit in manifest.units}
    expected_attempt_keys = {unit.attempt_key for unit in manifest.units}
    if set(status_by_key) - expected_attempt_keys:
        raise StageCContractError("attempt registry contains an unallocated unit")
    if any(record.get("status") == "ABANDONED" for record in records):
        raise StageCContractError("attempt registry contains an unadjudicated abandonment")
    if len(receipt_paths) != len(expected):
        raise StageCContractError("receipt set is incomplete or duplicated")
    clusters: dict[tuple[str, int], dict[str, AdditiveTotals]] = {}
    seen: set[str] = set()
    for receipt_path in receipt_paths:
        receipt = read_unit_receipt(receipt_path)
        unit_payload = receipt.get("unit")
        if not isinstance(unit_payload, dict):
            raise StageCContractError("receipt unit identity is missing")
        unit_id = str(unit_payload.get("unit_id"))
        unit = expected.get(unit_id)
        if unit is None or unit_id in seen or unit_payload != asdict(unit):
            raise StageCContractError("receipt unit is unexpected, duplicate, or drifted")
        seen.add(unit_id)
        if receipt.get("allocation_manifest_digest") != manifest.digest:
            raise StageCContractError("receipt allocation authority drifted")
        if (
            receipt.get("arm_order") != list(ARM_ORDER)
            or receipt.get("supportive_comparators") != ["S_UNI"]
        ):
            raise StageCContractError("receipt policy inventory drifted")
        conformance = receipt.get("conformance")
        if (
            not isinstance(conformance, dict)
            or conformance.get("schema")
            != "mcrl-v025-stagec-harness-conformance-v1-draft"
            or conformance.get("null_equals_base") is not True
            or conformance.get("joint_profile_validation") is not True
            or not isinstance(conformance.get("receipt_sha256"), str)
            or len(conformance["receipt_sha256"]) != 64
            or any(
                char not in "0123456789abcdef"
                for char in conformance["receipt_sha256"]
            )
        ):
            raise StageCContractError("receipt conformance evidence drifted")
        if conformance.get("authority") != {
            "code_digest": unit.code_digest,
            "provider_digest": unit.provider_digest,
            "launch_digest": unit.launch_digest,
            "physics_digest": unit.physics_digest,
            "catalogue_digest": unit.catalogue_digest,
            "deployment_capability_digest": unit.deployment_capability_digest,
            "setting_digest": unit.setting_digest,
            "calibration_digest": unit.calibration_digest,
        }:
            raise StageCContractError("receipt conformance authority drifted")
        statuses = status_by_key.get(unit.attempt_key, [])
        if [row["status"] for row in statuses] != ["STARTED", "DONE"]:
            raise StageCContractError(
                "unit lacks one STARTED followed by one DONE attempt"
            )
        if statuses[-1].get("receipt_sha256") != file_sha256(receipt_path):
            raise StageCContractError("DONE registry digest disagrees with receipt")
        steps = receipt.get("steps")
        summary = receipt.get("summary")
        initial_states = receipt.get("initial_temporal_state")
        if (
            not isinstance(steps, list)
            or not isinstance(summary, dict)
            or not isinstance(initial_states, dict)
        ):
            raise StageCContractError("receipt rows or summaries are missing")
        if set(summary) != set(POLICY_ORDER) or set(initial_states) != set(POLICY_ORDER):
            raise StageCContractError("receipt summary policy inventory drifted")
        authority_fields = (
            "provider_digest",
            "launch_digest",
            "code_digest",
            "physics_digest",
            "catalogue_digest",
            "deployment_capability_digest",
            "setting_digest",
            "calibration_digest",
        )
        indices_by_arm: dict[str, list[int]] = {arm: [] for arm in POLICY_ORDER}
        try:
            unit_start = datetime.fromisoformat(
                unit.resolved_start_utc.replace("Z", "+00:00")
            )
        except ValueError as error:
            raise StageCContractError("allocated unit start time is invalid") from error
        for row in steps:
            if not isinstance(row, dict):
                raise StageCContractError("receipt step row is not an object")
            _assert_step_is_canonical(row)
            arm = row.get("arm")
            step_index = row.get("step_index")
            if (
                arm not in POLICY_ORDER
                or isinstance(step_index, bool)
                or not isinstance(step_index, int)
                or step_index < 0
            ):
                raise StageCContractError("step arm or index drifted")
            expected_time = (
                unit_start + timedelta(seconds=30.08 * step_index)
            ).isoformat().replace("+00:00", "Z")
            if (
                row.get("unit_id") != unit.unit_id
                or row.get("world_id") != unit.world_id
                or row.get("world_seed") != unit.world_seed
                or row.get("learner_seed") != unit.learner_seed
                or row.get("tle_date") != unit.tle_date
                or row.get("decision_time_utc") != expected_time
                or row.get("decision_time_offset_s_hex")
                != float_hex(30.08 * step_index)
                or any(row.get(field) != getattr(unit, field) for field in authority_fields)
            ):
                raise StageCContractError("step identity or authority drifted")
            indices_by_arm[str(arm)].append(step_index)
        lengths = {len(indices) for indices in indices_by_arm.values()}
        if len(lengths) != 1 or not lengths or next(iter(lengths)) < 1:
            raise StageCContractError("step policy coverage drifted")
        for indices in indices_by_arm.values():
            if sorted(indices) != list(range(len(indices))):
                raise StageCContractError("step indices are duplicated or noncontiguous")
        cluster = clusters.setdefault((unit.tle_date, unit.learner_seed), {})
        for arm in POLICY_ORDER:
            arm_rows = sorted(
                (row for row in steps if row.get("arm") == arm),
                key=lambda row: int(row["step_index"]),
            )
            initial = initial_states[arm]
            if (
                not isinstance(initial, dict)
                or set(initial) != {"profile", "ever_served_user_ids", "user_ids"}
                or not isinstance(initial["profile"], list)
                or not isinstance(initial["user_ids"], list)
                or not isinstance(initial["ever_served_user_ids"], list)
            ):
                raise StageCContractError("initial temporal state schema drifted")
            prior_identities = initial["profile"]
            roster = initial["user_ids"]
            if len(prior_identities) != len(roster) or len(set(roster)) != len(roster):
                raise StageCContractError("initial temporal roster drifted")
            for row in arm_rows:
                events = row["events"]
                if [event["user_id"] for event in events] != roster:
                    raise StageCContractError("arm roster changed across temporal rows")
                if [event["prior_physical_identity"] for event in events] != prior_identities:
                    raise StageCContractError("arm temporal before-state drifted")
                prior_identities = [
                    event["current_physical_identity"] for event in events
                ]
            rebuilt = reaggregate_steps(arm_rows)
            if summary.get(arm) != rebuilt:
                raise StageCContractError(
                    f"trusted summary disagrees with rows for {arm}"
                )
            destination = cluster.setdefault(arm, AdditiveTotals())
            destination.add(_totals(rebuilt))
    if seen != set(expected):
        raise StageCContractError("not every allocated unit produced a receipt")
    for arms in clusters.values():
        if set(arms) != set(POLICY_ORDER):
            raise StageCContractError("cluster is missing a comparative arm")
    contrasts: dict[str, dict[str, object]] = {}
    all_keys = sorted(clusters)
    for index, drop_arm in enumerate(DROP_ARMS):
        point = _metrics(
            _sum_selected(clusters, all_keys, "FULL"),
            _sum_selected(clusters, all_keys, drop_arm),
        )
        contrasts[drop_arm] = {
            "point_estimates": point,
            "bootstrap": _bootstrap(
                clusters,
                drop_arm=drop_arm,
                draws=draws,
                seed=seed + index,
            ),
            "delta_method_ee": _delta_method_ee(clusters, drop_arm),
            "two_way_cluster_bootstrap_ee": _two_way_bootstrap(
                clusters,
                drop_arm=drop_arm,
                draws=draws,
                seed=seed + 100 + index,
            ),
        }
    claim = claim_decision(contrasts)
    for arm in DROP_ARMS:
        contrasts[arm]["gate_passed"] = claim["per_contrast"][arm]
    pooled_totals = {
        arm: _totals_payload(_sum_selected(clusters, all_keys, arm))
        for arm in POLICY_ORDER
    }
    cluster_totals = {
        f"{date}|{seed}": {
            arm: _totals_payload(clusters[(date, seed)][arm])
            for arm in POLICY_ORDER
        }
        for date, seed in all_keys
    }
    authority_fields = (
        "archive_digest",
        "provider_digest",
        "launch_digest",
        "code_digest",
        "physics_digest",
        "catalogue_digest",
        "deployment_capability_digest",
        "setting_digest",
        "calibration_digest",
    )
    artifact_inventory: dict[str, object] = {
        "state_schema": {
            "q1_schema_sha256": Q1_SCHEMA_SHA256,
            "q2_schema_sha256": Q2_SCHEMA_SHA256,
        },
        "source_shards": [],
        "batches": {},
        "checkpoints": {},
        "deployment_capability": [],
    }
    if artifact_digests is not None:
        artifact_inventory.update(dict(artifact_digests))
    conformance_evidence = sorted(
        {
            str(receipt["conformance"]["receipt_sha256"])
            for receipt_path in receipt_paths
            for receipt in (read_unit_receipt(receipt_path),)
            if isinstance(receipt.get("conformance"), dict)
        }
    )
    abandoned = [
        dict(record) for record in records if record.get("status") == "ABANDONED"
    ]
    report: dict[str, object] = {
        "schema": REPORT_SCHEMA,
        "terminal_adjudication_count": 1,
        "authorities": {
            "allocation_manifest_digest": manifest.digest,
            "allocation_acceptance_evidence_mode": manifest.acceptance_evidence_mode,
            "legacy_panel_overlap": list(manifest.legacy_panel_overlap),
            "unit_authorities": {
                field: sorted({getattr(unit, field) for unit in manifest.units})
                for field in authority_fields
            },
            "registry_head_sha256": (
                records[-1]["record_sha256"] if records else "0" * 64
            ),
        },
        "allocation_manifest_digest": manifest.digest,
        "inventory": {
            "experiments": sorted({unit.experiment_id for unit in manifest.units}),
            "panels": sorted({unit.panel_id for unit in manifest.units}),
            "cells": sorted({unit.cell_id for unit in manifest.units}),
            "worlds": sorted({unit.world_id for unit in manifest.units}),
            "dates": sorted({unit.tle_date for unit in manifest.units}),
            "learner_seeds": sorted({unit.learner_seed for unit in manifest.units}),
            "arms": list(ARM_ORDER),
            "supportive_comparators": ["S_UNI"],
        },
        "cluster_identity": ["tle_date", "learner_seed"],
        "cluster_count": len(clusters),
        "world_count": len(receipt_paths),
        "arm_order": list(ARM_ORDER),
        "supportive_comparators": {
            "S_UNI": {
                "pooled_bits": _sum_selected(clusters, all_keys, "S_UNI").bits,
                "pooled_joules": _sum_selected(clusters, all_keys, "S_UNI").joules,
            }
        },
        "artifact_digests": artifact_inventory,
        "pooled_additive_totals": pooled_totals,
        "cluster_additive_totals": cluster_totals,
        "estimator": "pooled sum(bits) / sum(joules)",
        "bootstrap": "cluster resample; ratio recomputed per draw; central 95% percentile",
        "bootstrap_parameters": {"draws": draws, "seed": seed},
        "zero_bit_disposition": ZERO_BIT_DISPOSITION,
        "margins": {
            "ee_relative": EE_MARGIN_RELATIVE,
            "availability_difference": AVAILABILITY_MARGIN,
            "handover_relative": HANDOVER_RELATIVE_MARGIN,
            "phi_cost_relative": PHI_COST_RELATIVE_MARGIN,
        },
        "contrasts": contrasts,
        "claim": claim,
        "admission": (
            dict(physics_admission)
            if physics_admission is not None
            else {"decision": "HOLD", "reason": "admission evidence not supplied"}
        ),
        "conformance_evidence_sha256": conformance_evidence,
        "attempt_registry": {
            "record_count": len(records),
            "abandoned_count": len(abandoned),
            "head_sha256": records[-1]["record_sha256"] if records else "0" * 64,
        },
        "anomalies_and_abandonments": abandoned,
        "interface_assumptions": list(interface_assumptions),
        "controller_decide": list(controller_decide),
        "evidence_ceiling": "TRAIN_ONLY_NO_TEST_NO_GENERALIZATION",
    }
    if physics_admission is not None:
        report["physics_admission"] = dict(physics_admission)
    return report


def write_terminal_report(path: str | Path, report: Mapping[str, object]) -> str:
    if (
        report.get("schema") != REPORT_SCHEMA
        or report.get("terminal_adjudication_count") != 1
    ):
        raise StageCContractError("terminal report adjudication schema drifted")
    return write_once_json(path, dict(report))


__all__ = [
    "REPORT_SCHEMA",
    "ZERO_BIT_DISPOSITION",
    "admission_decision",
    "claim_decision",
    "merge_receipts",
    "write_terminal_report",
]
