"""Prospective allocation, attempt registry, conformance, and unit receipts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import fcntl
import json
import os
from pathlib import Path
from typing import Mapping, Protocol, Sequence

from .canonical import (
    StageCContractError,
    canonical_json_bytes,
    canonical_sha256,
    file_sha256,
    float_hex,
    parse_float_hex,
    read_verified_json,
    write_once_json,
)
from .learner import ARM_ORDER, LEARNER_SEEDS, ThreeRouteModel
from .state import PhysicalAction


ALLOCATION_SCHEMA = "mcrl-v025-stagec-allocation-manifest-v1"
ATTEMPT_SCHEMA = "mcrl-v025-stagec-attempt-record-v1"
UNIT_RECEIPT_SCHEMA = "mcrl-v025-stagec-unit-receipt-v1"
SUPPORTIVE_COMPARATORS = ("S0", "S_UNI")
POLICY_ORDER = (*ARM_ORDER, *SUPPORTIVE_COMPARATORS)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class AllocationUnit:
    experiment_id: str
    panel_id: str
    cell_id: str
    unit_id: str
    world_id: str
    resolved_start_utc: str
    tle_date: str
    split: str
    role: str
    archive_digest: str
    provider_digest: str
    launch_digest: str
    code_digest: str
    physics_digest: str
    catalogue_digest: str
    deployment_capability_digest: str
    setting_digest: str
    calibration_digest: str
    learner_seed: int
    world_seed: int

    @property
    def attempt_key(self) -> str:
        return "|".join((self.experiment_id, self.panel_id, self.cell_id, self.unit_id))


@dataclass(frozen=True, slots=True)
class AllocationManifest:
    units: tuple[AllocationUnit, ...]
    legacy_panel_overlap: tuple[str, ...]
    acceptance_evidence_mode: str
    bootstrap_draws: int
    bootstrap_seed: int
    digest: str

    @classmethod
    def create(
        cls,
        units: Sequence[AllocationUnit],
        *,
        legacy_panel_overlap: Sequence[str] = (),
        acceptance_evidence_mode: str = "synthetic_only",
        bootstrap_draws: int = 1000,
        bootstrap_seed: int = 20260908,
    ) -> "AllocationManifest":
        material = tuple(units)
        overlap = tuple(str(value) for value in legacy_panel_overlap)
        if not material:
            raise StageCContractError("allocation manifest must not be empty")
        if (
            isinstance(bootstrap_draws, bool)
            or bootstrap_draws < 1
            or isinstance(bootstrap_seed, bool)
        ):
            raise StageCContractError("allocation bootstrap parameters are invalid")
        if acceptance_evidence_mode not in {
            "disjoint_rehearsal_worlds",
            "blinded_hashes",
            "synthetic_only",
        }:
            raise StageCContractError("unknown acceptance evidence mode")
        if acceptance_evidence_mode == "synthetic_only" and any(
            unit.role == "claim" for unit in material
        ):
            raise StageCContractError("claim allocation cannot use synthetic-only acceptance")
        keys = [unit.attempt_key for unit in material]
        if len(set(keys)) != len(keys):
            raise StageCContractError("allocation manifest has duplicate units")
        if len({unit.unit_id for unit in material}) != len(material):
            raise StageCContractError("allocation unit_id values must be globally unique")
        for unit in material:
            if unit.split != "TRAIN":
                raise StageCContractError("V0.25 evaluation is TRAIN-only")
            if unit.role not in {
                "probe", "calibration", "rehearsal", "KAT", "claim", "synthetic"
            }:
                raise StageCContractError("unknown allocation role")
            for field in (
                "archive_digest",
                "provider_digest",
                "launch_digest",
                "code_digest",
                "physics_digest",
                "catalogue_digest",
                "deployment_capability_digest",
                "setting_digest",
                "calibration_digest",
            ):
                digest = getattr(unit, field)
                if (
                    len(digest) != 64
                    or any(char not in "0123456789abcdef" for char in digest)
                ):
                    raise StageCContractError(
                        f"allocation {field} must be a lowercase SHA-256"
                    )
            try:
                start = datetime.fromisoformat(
                    unit.resolved_start_utc.replace("Z", "+00:00")
                )
            except ValueError as error:
                raise StageCContractError("allocation start UTC is invalid") from error
            if start.tzinfo is None:
                raise StageCContractError("allocation start UTC lacks a timezone")
        claim_dates = {unit.tle_date for unit in material if unit.role == "claim"}
        development_dates = {
            unit.tle_date
            for unit in material
            if unit.role in {"probe", "calibration", "rehearsal", "KAT"}
        }
        if claim_dates & development_dates:
            raise StageCContractError("claim dates overlap successor development dates")
        claim_units = tuple(unit for unit in material if unit.role == "claim")
        if claim_units:
            if {unit.cell_id for unit in claim_units} != {"a-r0"}:
                raise StageCContractError("D4 permits only a-r0 as the primary claim cell")
            claim_seeds = {unit.learner_seed for unit in claim_units}
            if claim_seeds != set(LEARNER_SEEDS):
                raise StageCContractError("D1 claim panel requires the 12 sealed learner seeds")
            if not 150 <= len(claim_dates) <= 170:
                raise StageCContractError("D1 claim panel requires approximately 160 dates")
            counts: dict[tuple[str, int], int] = {}
            for unit in claim_units:
                counts[(unit.tle_date, unit.learner_seed)] = counts.get(
                    (unit.tle_date, unit.learner_seed), 0
                ) + 1
            expected = {(date, seed) for date in claim_dates for seed in claim_seeds}
            if set(counts) != expected or any(count != 2 for count in counts.values()):
                raise StageCContractError("D1 requires two worlds per TRAIN date and learner seed")
        payload = {
            "schema": ALLOCATION_SCHEMA,
            "sealed_pre_outcome": True,
            "legacy_panel_overlap": list(overlap),
            "acceptance_evidence_mode": acceptance_evidence_mode,
            "bootstrap_draws": bootstrap_draws,
            "bootstrap_seed": bootstrap_seed,
            "units": [asdict(unit) for unit in material],
        }
        return cls(
            material,
            overlap,
            acceptance_evidence_mode,
            bootstrap_draws,
            bootstrap_seed,
            canonical_sha256(payload),
        )

    def payload(self) -> dict[str, object]:
        return {
            "schema": ALLOCATION_SCHEMA,
            "sealed_pre_outcome": True,
            "legacy_panel_overlap": list(self.legacy_panel_overlap),
            "acceptance_evidence_mode": self.acceptance_evidence_mode,
            "bootstrap_draws": self.bootstrap_draws,
            "bootstrap_seed": self.bootstrap_seed,
            "units": [asdict(unit) for unit in self.units],
            "allocation_manifest_sha256": self.digest,
        }


class AttemptRegistry:
    """Append-only hash chain. STARTED is durable before evaluator entry."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _decode(data: bytes) -> tuple[dict[str, object], ...]:
        records: list[dict[str, object]] = []
        prior = "0" * 64
        for line_number, line in enumerate(data.splitlines(), 1):
            try:
                record = json.loads(line.decode("ascii"))
            except (UnicodeError, json.JSONDecodeError) as error:
                raise StageCContractError(f"invalid registry line {line_number}") from error
            if not isinstance(record, dict) or record.get("schema") != ATTEMPT_SCHEMA:
                raise StageCContractError("attempt registry schema drifted")
            digest = record.get("record_sha256")
            body = dict(record)
            body.pop("record_sha256", None)
            if body.get("previous_record_sha256") != prior or digest != canonical_sha256(body):
                raise StageCContractError("attempt registry hash chain is broken")
            prior = str(digest)
            records.append(record)
        return tuple(records)

    def records(self) -> tuple[dict[str, object], ...]:
        if not self.path.exists():
            return ()
        if self.path.is_symlink() or not self.path.is_file():
            raise StageCContractError("attempt registry is not a regular file")
        return self._decode(self.path.read_bytes())

    def append(
        self,
        *,
        status: str,
        unit: AllocationUnit,
        allocation_manifest_digest: str,
        receipt_sha256: str | None = None,
        reason: str | None = None,
    ) -> dict[str, object]:
        if status not in {"STARTED", "DONE", "ABANDONED"}:
            raise StageCContractError("invalid attempt status")
        descriptor = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o644)
        with os.fdopen(descriptor, "r+b", closefd=True) as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            stream.seek(0)
            existing = self._decode(stream.read())
            states = [
                row["status"] for row in existing if row["attempt_key"] == unit.attempt_key
            ]
            if status == "STARTED" and states:
                raise StageCContractError("duplicate evaluation attempt refused")
            if status != "STARTED" and states != ["STARTED"]:
                raise StageCContractError(
                    "terminal attempt record lacks exactly one STARTED"
                )
            previous = (
                str(existing[-1]["record_sha256"]) if existing else "0" * 64
            )
            body: dict[str, object] = {
                "schema": ATTEMPT_SCHEMA,
                "sequence": len(existing) + 1,
                "previous_record_sha256": previous,
                "status": status,
                "attempt_key": unit.attempt_key,
                "experiment_id": unit.experiment_id,
                "panel_id": unit.panel_id,
                "cell_id": unit.cell_id,
                "unit_id": unit.unit_id,
                "world_id": unit.world_id,
                "world_seed": unit.world_seed,
                "learner_seed": unit.learner_seed,
                "code_digest": unit.code_digest,
                "provider_digest": unit.provider_digest,
                "launch_digest": unit.launch_digest,
                "physics_digest": unit.physics_digest,
                "catalogue_digest": unit.catalogue_digest,
                "deployment_capability_digest": unit.deployment_capability_digest,
                "setting_digest": unit.setting_digest,
                "calibration_digest": unit.calibration_digest,
                "allocation_manifest_digest": allocation_manifest_digest,
                "utc": _utc_now(),
                "receipt_sha256": receipt_sha256,
                "reason": reason,
            }
            body["record_sha256"] = canonical_sha256(body)
            stream.seek(0, os.SEEK_END)
            stream.write(canonical_json_bytes(body) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
            return body


@dataclass(frozen=True, slots=True)
class StepOutcome:
    bits: float
    energy_components_j: Mapping[str, float]
    user_ids: tuple[int, ...]
    profile: tuple[PhysicalAction, ...]
    complete_service: tuple[bool, ...]
    decoding_user_seconds: float
    useful_user_seconds: float
    opportunity_user_seconds: float
    jointly_legal: bool
    cell_rekey_users: frozenset[int] = frozenset()
    coordinator_deadline_miss: bool = False

    @property
    def joules(self) -> float:
        return float(
            sum(value for _, value in sorted(self.energy_components_j.items()))
        )


@dataclass(frozen=True, slots=True)
class InitialTemporalState:
    profile: tuple[PhysicalAction, ...]
    ever_served_user_ids: frozenset[int]
    last_served_profile: tuple[PhysicalAction | None, ...] | None = None


class InitialTemporalStateProvider(Protocol):
    def __call__(
        self, *, unit: AllocationUnit, arm: str
    ) -> InitialTemporalState: ...


class UnitEvaluator(Protocol):
    def __call__(
        self,
        *,
        unit: AllocationUnit,
        arm: str,
        model: ThreeRouteModel | None,
        step_index: int,
        previous_profile: tuple[PhysicalAction, ...] | None,
    ) -> StepOutcome: ...


def _identity_payload(
    action: PhysicalAction | None,
) -> dict[str, int | None] | None:
    return None if action is None else action.payload()


def _event_kind(
    before: PhysicalAction | None,
    after: PhysicalAction,
    *,
    cell_rekey: bool,
    ever_served: bool,
) -> str:
    if before is None:
        if after.is_null:
            return "unchanged"
        return "reentry" if ever_served else "initial_entry"
    if before.is_null and after.is_null:
        return "unchanged"
    if before.is_null:
        return "reentry" if ever_served else "initial_entry"
    if after.is_null:
        return "exit"
    if before.norad_id != after.norad_id:
        return "satellite_change"
    if before.beam_chain_id != after.beam_chain_id:
        return "beam_change"
    if cell_rekey:
        return "cell_rekey"
    return "unchanged"


def _step_payload(
    *,
    unit: AllocationUnit,
    arm: str,
    step_index: int,
    outcome: StepOutcome,
    previous: tuple[PhysicalAction, ...] | None,
    ever_served: set[int],
    last_served: dict[int, PhysicalAction] | None = None,
) -> dict[str, object]:
    if not outcome.jointly_legal:
        raise StageCContractError("evaluator returned a jointly illegal committed profile")
    if (
        len(outcome.profile) != len(outcome.complete_service)
        or len(outcome.user_ids) != len(outcome.profile)
        or len(set(outcome.user_ids)) != len(outcome.user_ids)
    ):
        raise StageCContractError(
            "outcome roster and complete-service vector disagree"
        )
    if (
        outcome.bits < 0
        or outcome.joules < 0
        or (outcome.bits > 0 and outcome.joules == 0)
        or outcome.opportunity_user_seconds <= 0
    ):
        raise StageCContractError("invalid additive endpoint totals")
    if previous is not None and len(previous) != len(outcome.profile):
        raise StageCContractError("arm roster changed between steps")
    events: list[dict[str, object]] = []
    last = {} if last_served is None else last_served
    handovers = 0
    phi_half_units = 0
    for user_index, (user_id, after) in enumerate(
        zip(outcome.user_ids, outcome.profile, strict=True)
    ):
        before = None if previous is None else previous[user_index]
        kind = _event_kind(
            before,
            after,
            cell_rekey=user_id in outcome.cell_rekey_users,
            ever_served=user_id in ever_served,
        )
        reentry_reference = last.get(user_id)
        if kind == "reentry":
            handovers += 1
            phi_half_units += (
                2
                if reentry_reference is None
                or reentry_reference.norad_id != after.norad_id
                else 1
            )
        elif kind in {"beam_change", "satellite_change"}:
            handovers += 1
            phi_half_units += 1 if kind == "beam_change" else 2
        if not after.is_null:
            ever_served.add(user_id)
            last[user_id] = after
        events.append(
            {
                "user_id": user_id,
                "prior_physical_identity": _identity_payload(before),
                "current_physical_identity": _identity_payload(after),
                "event_type": kind,
                "reentry_reference_physical_identity": _identity_payload(reentry_reference),
                "cell_rekey": user_id in outcome.cell_rekey_users,
                "complete_service": bool(outcome.complete_service[user_index]),
            }
        )
    energy = {
        name: float_hex(value)
        for name, value in sorted(outcome.energy_components_j.items())
    }
    if not energy:
        raise StageCContractError("energy component ledger must not be empty")
    try:
        start_utc = datetime.fromisoformat(
            unit.resolved_start_utc.replace("Z", "+00:00")
        )
    except ValueError as error:
        raise StageCContractError("unit start UTC is invalid") from error
    decision_utc = (start_utc + timedelta(seconds=30.08 * step_index)).isoformat().replace(
        "+00:00", "Z"
    )
    return {
        "schema": "mcrl-v025-stagec-step-row-v1",
        "unit_id": unit.unit_id,
        "world_id": unit.world_id,
        "world_seed": unit.world_seed,
        "learner_seed": unit.learner_seed,
        "tle_date": unit.tle_date,
        "arm": arm,
        "step_index": step_index,
        "decision_time_utc": decision_utc,
        "decision_time_offset_s_hex": float_hex(30.08 * step_index),
        "bits_hex": float_hex(outcome.bits),
        "joules_hex": float_hex(outcome.joules),
        "energy_components_j_hex": energy,
        "complete_service_numerator": sum(outcome.complete_service),
        "complete_service_denominator": len(outcome.complete_service),
        "decoding_user_seconds_hex": float_hex(outcome.decoding_user_seconds),
        "useful_user_seconds_hex": float_hex(outcome.useful_user_seconds),
        "opportunity_user_seconds_hex": float_hex(outcome.opportunity_user_seconds),
        "handover_numerator": handovers,
        "handover_denominator": len(outcome.profile),
        "phi_cost_numerator_half_units": phi_half_units,
        "phi_cost_denominator_half_user_steps": 2 * len(outcome.profile),
        "coordinator_deadline_miss_numerator": int(outcome.coordinator_deadline_miss),
        "coordinator_deadline_miss_denominator": 1,
        "events": events,
        "provider_digest": unit.provider_digest,
        "launch_digest": unit.launch_digest,
        "code_digest": unit.code_digest,
        "physics_digest": unit.physics_digest,
        "catalogue_digest": unit.catalogue_digest,
        "deployment_capability_digest": unit.deployment_capability_digest,
        "setting_digest": unit.setting_digest,
        "calibration_digest": unit.calibration_digest,
    }


def reaggregate_steps(
    steps: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    if not steps:
        raise StageCContractError("cannot aggregate empty step rows")
    bits = sum(
        parse_float_hex(row["bits_hex"], field="bits_hex") for row in steps
    )
    joules = sum(
        parse_float_hex(row["joules_hex"], field="joules_hex") for row in steps
    )
    complete_num = sum(int(row["complete_service_numerator"]) for row in steps)
    complete_den = sum(int(row["complete_service_denominator"]) for row in steps)
    handover_num = sum(int(row["handover_numerator"]) for row in steps)
    handover_den = sum(int(row["handover_denominator"]) for row in steps)
    phi_num = sum(int(row["phi_cost_numerator_half_units"]) for row in steps)
    phi_den = sum(
        int(row["phi_cost_denominator_half_user_steps"]) for row in steps
    )
    miss_num = sum(int(row["coordinator_deadline_miss_numerator"]) for row in steps)
    miss_den = sum(int(row["coordinator_deadline_miss_denominator"]) for row in steps)
    return {
        "bits_hex": float_hex(bits),
        "joules_hex": float_hex(joules),
        "complete_service_numerator": complete_num,
        "complete_service_denominator": complete_den,
        "handover_numerator": handover_num,
        "handover_denominator": handover_den,
        "phi_cost_numerator_half_units": phi_num,
        "phi_cost_denominator_half_user_steps": phi_den,
        "coordinator_deadline_miss_numerator": miss_num,
        "coordinator_deadline_miss_denominator": miss_den,
    }


class EvaluationRunner:
    def __init__(
        self,
        *,
        manifest: AllocationManifest,
        registry: AttemptRegistry,
        evaluator: UnitEvaluator,
        initial_temporal_state: InitialTemporalStateProvider,
        output_directory: str | Path,
        steps: int,
    ) -> None:
        if steps < 1:
            raise StageCContractError("evaluation requires at least one step")
        self.manifest = manifest
        self.registry = registry
        self.evaluator = evaluator
        self.initial_temporal_state = initial_temporal_state
        self.output_directory = Path(output_directory)
        self.steps = steps

    def conformance_suite(
        self,
        *,
        unit: AllocationUnit,
        models: Mapping[str, ThreeRouteModel],
    ) -> dict[str, object]:
        if unit.role == "claim":
            raise StageCContractError("conformance must not consume a claim unit")
        missing = set(ARM_ORDER[:-1]) - set(models)
        if missing:
            raise StageCContractError(
                f"conformance missing learned arms: {sorted(missing)}"
            )
        self.registry.append(
            status="STARTED",
            unit=unit,
            allocation_manifest_digest=self.manifest.digest,
        )
        try:
            outcomes: dict[str, StepOutcome] = {}
            for arm in POLICY_ORDER:
                outcomes[arm] = self.evaluator(
                    unit=unit,
                    arm=arm,
                    model=(
                        None
                        if arm in {"BASELINE", "S_UNI"}
                        else models["FULL"] if arm == "S0" else models[arm]
                    ),
                    step_index=0,
                    previous_profile=None,
                )
            null = self.evaluator(
                unit=unit,
                arm="NULL",
                model=None,
                step_index=0,
                previous_profile=None,
            )
            if null != outcomes["BASELINE"]:
                raise StageCContractError("NULL is not exactly BASE per step")
            if not null.jointly_legal or not all(
                outcome.jointly_legal for outcome in outcomes.values()
            ):
                raise StageCContractError("conformance produced a jointly illegal profile")
            for arm, outcome in outcomes.items():
                temporal_state = self.initial_temporal_state(unit=unit, arm=arm)
                initial_last = (
                    temporal_state.last_served_profile
                    if temporal_state.last_served_profile is not None
                    else tuple(None if action.is_null else action for action in temporal_state.profile)
                )
                if len(initial_last) != len(temporal_state.profile):
                    raise StageCContractError("initial last-served profile is roster-incomplete")
                last_served = {
                    user_id: action
                    for user_id, action in zip(outcome.user_ids, initial_last, strict=True)
                    if action is not None
                }
                _step_payload(
                    unit=unit,
                    arm=arm,
                    step_index=0,
                    outcome=outcome,
                    previous=temporal_state.profile,
                    ever_served=set(temporal_state.ever_served_user_ids),
                    last_served=last_served,
                )
            authority = (
                unit.code_digest,
                unit.provider_digest,
                unit.launch_digest,
                unit.physics_digest,
                unit.catalogue_digest,
                unit.deployment_capability_digest,
                unit.setting_digest,
                unit.calibration_digest,
                self.manifest.digest,
            )
            if any(
                len(digest) != 64
                or any(char not in "0123456789abcdef" for char in digest)
                for digest in authority
            ):
                raise StageCContractError(
                    "conformance authority manifest is incomplete"
                )
            result: dict[str, object] = {
                "schema": "mcrl-v025-stagec-harness-conformance-v1",
                "allocation_manifest_digest": self.manifest.digest,
                "unit_id": unit.unit_id,
                "attempt_key": unit.attempt_key,
                "authority": {
                    "code_digest": unit.code_digest,
                    "provider_digest": unit.provider_digest,
                    "launch_digest": unit.launch_digest,
                    "physics_digest": unit.physics_digest,
                    "catalogue_digest": unit.catalogue_digest,
                    "deployment_capability_digest": unit.deployment_capability_digest,
                    "setting_digest": unit.setting_digest,
                    "calibration_digest": unit.calibration_digest,
                },
                "null_equals_base": True,
                "real_step_arms": list(ARM_ORDER),
                "supportive_comparators": list(SUPPORTIVE_COMPARATORS),
                "authority_complete": True,
                "joint_profile_validation": True,
                "reward_endpoint_identity": "bits_and_energy_component_ledger",
                "write_once_sha256_receipts": True,
                "outcome_digests": {
                    arm: canonical_sha256(
                        {
                            "bits_hex": float_hex(outcome.bits),
                            "joules_hex": float_hex(outcome.joules),
                            "profile": [action.payload() for action in outcome.profile],
                            "complete_service": list(outcome.complete_service),
                        }
                    )
                    for arm, outcome in outcomes.items()
                },
            }
            destination = self.output_directory / f"{unit.unit_id}.conformance.json"
            receipt_digest = write_once_json(destination, result)
            self.registry.append(
                status="DONE",
                unit=unit,
                allocation_manifest_digest=self.manifest.digest,
                receipt_sha256=receipt_digest,
            )
            return {
                **result,
                "receipt_path": str(destination.resolve()),
                "receipt_sha256": receipt_digest,
                "attempt_registry_path": str(self.registry.path.resolve()),
            }
        except Exception as error:
            self.registry.append(
                status="ABANDONED",
                unit=unit,
                allocation_manifest_digest=self.manifest.digest,
                reason=type(error).__name__,
            )
            raise

    def run_unit(
        self,
        *,
        unit: AllocationUnit,
        models: Mapping[str, ThreeRouteModel],
        conformance: Mapping[str, object],
    ) -> Path:
        if unit not in self.manifest.units:
            raise StageCContractError(
                "unit is absent from sealed allocation manifest"
            )
        if unit.role == "claim" and self.steps != 30:
            raise StageCContractError("D1 claim units require exactly 30 decision steps")
        if not all(
            conformance.get(field) is True
            for field in (
                "null_equals_base",
                "authority_complete",
                "joint_profile_validation",
                "write_once_sha256_receipts",
            )
        ):
            raise StageCContractError("harness conformance did not pass")
        receipt_sha256 = conformance.get("receipt_sha256")
        conformance_authority = conformance.get("authority")
        expected_conformance_authority = {
            "code_digest": unit.code_digest,
            "provider_digest": unit.provider_digest,
            "launch_digest": unit.launch_digest,
            "physics_digest": unit.physics_digest,
            "catalogue_digest": unit.catalogue_digest,
            "deployment_capability_digest": unit.deployment_capability_digest,
            "setting_digest": unit.setting_digest,
            "calibration_digest": unit.calibration_digest,
        }
        if (
            conformance.get("schema")
            != "mcrl-v025-stagec-harness-conformance-v1"
            or conformance_authority != expected_conformance_authority
            or conformance.get("real_step_arms") != list(ARM_ORDER)
            or conformance.get("supportive_comparators")
            != list(SUPPORTIVE_COMPARATORS)
            or conformance.get("reward_endpoint_identity")
            != "bits_and_energy_component_ledger"
            or not isinstance(receipt_sha256, str)
            or len(receipt_sha256) != 64
            or any(char not in "0123456789abcdef" for char in receipt_sha256)
        ):
            raise StageCContractError("harness conformance authority drifted")
        receipt_path = conformance.get("receipt_path")
        registry_path = conformance.get("attempt_registry_path")
        if not isinstance(receipt_path, str) or not isinstance(registry_path, str):
            raise StageCContractError("harness conformance evidence path is missing")
        persisted = read_verified_json(receipt_path)
        expected_persisted = dict(conformance)
        expected_persisted.pop("receipt_path")
        expected_persisted.pop("receipt_sha256")
        expected_persisted.pop("attempt_registry_path")
        if persisted != expected_persisted or file_sha256(receipt_path) != receipt_sha256:
            raise StageCContractError("harness conformance receipt drifted")
        conformance_records = [
            record
            for record in AttemptRegistry(registry_path).records()
            if record.get("attempt_key") == conformance.get("attempt_key")
        ]
        if (
            [record.get("status") for record in conformance_records]
            != ["STARTED", "DONE"]
            or conformance_records[-1].get("receipt_sha256") != receipt_sha256
        ):
            raise StageCContractError("harness conformance attempt chain drifted")
        self.registry.append(
            status="STARTED",
            unit=unit,
            allocation_manifest_digest=self.manifest.digest,
        )
        try:
            all_steps: list[dict[str, object]] = []
            initial_states: dict[str, dict[str, object]] = {}
            for arm in POLICY_ORDER:
                temporal_state = self.initial_temporal_state(unit=unit, arm=arm)
                if not temporal_state.profile:
                    raise StageCContractError("initial temporal profile must be complete")
                previous = temporal_state.profile
                ever_served = set(temporal_state.ever_served_user_ids)
                initial_last = (
                    temporal_state.last_served_profile
                    if temporal_state.last_served_profile is not None
                    else tuple(None if action.is_null else action for action in temporal_state.profile)
                )
                if len(initial_last) != len(temporal_state.profile):
                    raise StageCContractError("initial last-served profile is roster-incomplete")
                last_served: dict[int, PhysicalAction] = {}
                initial_states[arm] = {
                    "profile": [action.payload() for action in previous],
                    "ever_served_user_ids": sorted(ever_served),
                }
                for step_index in range(self.steps):
                    outcome = self.evaluator(
                        unit=unit,
                        arm=arm,
                        model=(
                            None
                            if arm in {"BASELINE", "S_UNI"}
                            else models["FULL"] if arm == "S0" else models[arm]
                        ),
                        step_index=step_index,
                        previous_profile=previous,
                    )
                    if step_index == 0:
                        initial_states[arm]["user_ids"] = list(outcome.user_ids)
                        last_served.update(
                            {
                                user_id: action
                                for user_id, action in zip(
                                    outcome.user_ids, initial_last, strict=True
                                )
                                if action is not None
                            }
                        )
                    all_steps.append(
                        _step_payload(
                            unit=unit,
                            arm=arm,
                            step_index=step_index,
                            outcome=outcome,
                            previous=previous,
                            ever_served=ever_served,
                            last_served=last_served,
                        )
                    )
                    previous = outcome.profile
            summaries = {
                arm: reaggregate_steps(
                    [row for row in all_steps if row["arm"] == arm]
                )
                for arm in POLICY_ORDER
            }
            receipt = {
                "schema": UNIT_RECEIPT_SCHEMA,
                "allocation_manifest_digest": self.manifest.digest,
                "unit": asdict(unit),
                "arm_order": list(ARM_ORDER),
                "supportive_comparators": list(SUPPORTIVE_COMPARATORS),
                "conformance": dict(conformance),
                "initial_temporal_state": initial_states,
                "steps": all_steps,
                "summary": summaries,
            }
            destination = self.output_directory / f"{unit.unit_id}.receipt.json"
            digest = write_once_json(destination, receipt)
            self.registry.append(
                status="DONE",
                unit=unit,
                allocation_manifest_digest=self.manifest.digest,
                receipt_sha256=digest,
            )
            return destination
        except Exception as error:
            self.registry.append(
                status="ABANDONED",
                unit=unit,
                allocation_manifest_digest=self.manifest.digest,
                reason=type(error).__name__,
            )
            raise


def read_unit_receipt(path: str | Path) -> dict[str, object]:
    payload = read_verified_json(path)
    if (
        not isinstance(payload, dict)
        or payload.get("schema") != UNIT_RECEIPT_SCHEMA
    ):
        raise StageCContractError("unsupported unit receipt")
    return payload


__all__ = [
    "ALLOCATION_SCHEMA",
    "AllocationManifest",
    "AllocationUnit",
    "AttemptRegistry",
    "EvaluationRunner",
    "InitialTemporalState",
    "InitialTemporalStateProvider",
    "POLICY_ORDER",
    "SUPPORTIVE_COMPARATORS",
    "StepOutcome",
    "read_unit_receipt",
    "reaggregate_steps",
]
