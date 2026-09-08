#!/usr/bin/env python3
"""Run the C3-S placebo controls and hostile baselines (TRAIN, no learning)."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Callable, Mapping, Sequence

import numpy as np

import c3s_diagnostic_policy as diagnostic
import c3s_physics_override as physics_ablation
import c3s_policy
import run_v023_c3s_screen as donor


HERE = Path(__file__).resolve().parent  # Diagnostic implementation location.
SCHEMA = "multi-catfish-mcrl-v023-c3s-diagnostic-arms-v2"  # Instrumented schema.
PREFLIGHT_SCHEMA = f"{SCHEMA}-preflight-manifest"  # Derived from diagnostic schema.
LAUNCH_AUTHORITY_SCHEMA = f"{SCHEMA}-launch-authority"  # Derived from diagnostic schema.
UNIT_RECEIPT_SCHEMA = f"{SCHEMA}-unit-receipt"  # Derived from diagnostic schema.
TERMINAL_RECEIPT_SCHEMA = f"{SCHEMA}-terminal-receipt"  # Derived from diagnostic schema.
CLAIM_CEILING = "TRAIN_DEVELOPMENT_DIAGNOSTIC_CONTROLS_NO_EFFICACY_NO_TEST"  # Task scope.
DEFAULT_HORIZON = 30  # Task-fixed 30-step panel.
USERS = 100  # Inherited E1/C3-S panel size.
WORLDS = donor.WORLDS  # Identical v1 world seeds and initial-state rule.
WORLD_DOMAINS = donor.WORLD_DOMAINS  # Identical v1 world domains.
LINEAGES = donor.LINEAGES  # Frozen E1 Q1/Q2 lineages.
FIELD_COMPONENT = donor.FIELD_COMPONENT  # Identical keyed-fading component.
BASE_ARM = "BASE"  # Mandatory comparison arm in every diagnostic unit.
DIAGNOSTIC_ARMS = (  # User-specified diagnostic arm order, 2026-09-08.
    "FULL", "LITE", "NULL", "RANDOM_RENEW", "RANDOM_RENEW_K",
    "BASE_FORCED_RENEW_4", "RANDOM_FEASIBLE", "SHUFFLED_SCORE", "HEUR", "HEUR_C3S_LITE",
    "NOMINAL_MPC", "LITE_UNILATERAL_ONLY", "LITE_EVACUATION_ONLY",
)
LEARNED_ARMS = frozenset({  # Arms whose proposal or pruning uses frozen Q1/Q2.
    "NULL", "RANDOM_FEASIBLE", "SHUFFLED_SCORE",
    "LITE_UNILATERAL_ONLY", "LITE_EVACUATION_ONLY",
})
Q_FREE_ARMS = frozenset({"HEUR", "HEUR_C3S_LITE", "NOMINAL_MPC"})  # Task definitions.
CHURN_ARMS = frozenset({"RANDOM_RENEW", "RANDOM_RENEW_K", "BASE_FORCED_RENEW_4"})
HANDOVER_ENERGY_GRID_J = (
    Fraction(0), Fraction(1, 2), Fraction(1),
    Fraction(2), Fraction(5), Fraction(10),
)
INSTRUMENTED_STEP_FIELDS = frozenset({
    "association_changed_users", "handover_count", "explicit_renewal_count",
    "handover_or_renewal_count", "users_changed_vs_base", "active_beam_count",
    "association_segment_age", "association_segment_age_before_decision",
    "per_user_transmit_power_sum_w_hex", "nominal", "realised",
    "executed_configuration_type", "dwell_phase_index",
})
DEFAULT_PREFLIGHT = HERE / "C3S-DIAGNOSTIC-PREFLIGHT-MANIFEST.json"  # Own authority namespace.
DEFAULT_OUTPUT = HERE / "diagnostic-run-output"  # Own receipt namespace.
UNIT_RECEIPT_NAME = "receipt.json"  # Matches established unit layout.
TERMINAL_RECEIPT_NAME = "terminal-receipt.json"  # Matches established merge layout.


class DiagnosticRunnerError(RuntimeError):
    """A diagnostic authority, trajectory, or receipt failed closed."""


class MergeWaiting(DiagnosticRunnerError):
    """The merge cannot proceed until all twelve selected-arm units exist."""

    def __init__(self, missing: int) -> None:
        self.missing = missing
        super().__init__(f"{missing} units missing")


@dataclass(frozen=True, order=True)
class UnitKey:
    world: int
    lineage: int

    @classmethod
    def parse(cls, value: str) -> "UnitKey":
        try:
            world, lineage = value.split(":", 1)
            result = cls(int(world), int(lineage))
        except (AttributeError, TypeError, ValueError) as error:
            raise DiagnosticRunnerError("--unit must be WORLD:LINEAGE") from error
        result.verify()
        return result

    def verify(self) -> None:
        if self.world not in WORLDS or self.lineage not in LINEAGES:
            raise DiagnosticRunnerError("unit is outside the fixed 4-world x 3-lineage panel")

    @property
    def slug(self) -> str:
        self.verify()
        return f"{self.world}-{self.lineage}"

    def as_dict(self) -> dict[str, int]:
        self.verify()
        return {"world": self.world, "lineage": self.lineage}


ALL_UNITS = tuple(UnitKey(world, lineage) for world in WORLDS for lineage in LINEAGES)  # 4x3 panel.


def parse_arms(values: Sequence[str] | str | None) -> tuple[str, ...]:
    """Parse comma- or space-separated arms into canonical declared order."""

    raw = list(DIAGNOSTIC_ARMS) if values is None else (
        [values] if isinstance(values, str) else list(values)
    )
    names = [part.strip().upper() for value in raw for part in value.split(",") if part.strip()]
    declared = frozenset((BASE_ARM, *DIAGNOSTIC_ARMS))
    if not names or len(names) != len(set(names)) or any(name not in declared for name in names):
        raise DiagnosticRunnerError("--arms must be a nonempty unique subset of declared diagnostic arms")
    selected = set(names) - {BASE_ARM}
    return tuple(arm for arm in DIAGNOSTIC_ARMS if arm in selected)


def panel_bindings(
    *, horizon: int, arms: Sequence[str], assert_null_equals_base: bool,
    physics_override: str = "none",
) -> dict[str, object]:
    selected = parse_arms(arms)
    if horizon != DEFAULT_HORIZON:
        raise DiagnosticRunnerError("formal diagnostic authority requires 30 steps")
    if assert_null_equals_base and "NULL" not in selected:
        raise DiagnosticRunnerError("--assert-null-equals-base requires NULL in --arms")
    override = physics_ablation.get_physics_override(physics_override)
    return {
        "world_domains": list(WORLD_DOMAINS), "worlds": list(WORLDS),
        "lineages": list(LINEAGES), "units": len(ALL_UNITS),
        "users": USERS, "horizon": horizon, "split": "TRAIN",
        "arms": [BASE_ARM, *selected], "selected_diagnostic_arms": list(selected),
        "episodes": len(ALL_UNITS) * (1 + len(selected)),
        "field_component": FIELD_COMPONENT,
        "trajectory_rule": "OWN_TRAJECTORY_FROM_IDENTICAL_INITIAL_STATE",
        "fading_rule": "IDENTICAL_KEYED_FIELD_ROOT_WITHOUT_ARM_OR_LINEAGE_IN_KEY",
        "assert_null_equals_base": bool(assert_null_equals_base),
        "physics_override": override.binding(),
    }


def expected_code_bindings() -> list[dict[str, str]]:
    """Bind this diagnostic layer plus the exact donor inference closure."""

    own = (
        HERE / "run_v023_c3s_diagnostic_arms.py",
        HERE / "c3s_diagnostic_policy.py",
        HERE / "c3s_physics_override.py",
        HERE / "build_c3s_diagnostic_preflight_manifest.py",
        HERE / "build_c3s_diagnostic_launch_authority.py",
        HERE / "c3s_policy.py",
        HERE / "c3s_config.json",
    )
    paths = {Path(row["path"]).resolve() for row in donor.expected_code_bindings()}
    paths.update(path.resolve() for path in own)
    return [
        {"path": str(path), "sha256": donor.file_sha256(path)}
        for path in sorted(paths, key=str)
    ]


def static_bindings() -> dict[str, object]:
    source_contract = donor.CONTRACT_PATH
    if source_contract.is_symlink() or not source_contract.is_file():
        raise DiagnosticRunnerError("v1 source contract is absent or symlinked")
    try:
        frozen_inputs = donor.e1.prereg_tle_bindings()
        for lineage in LINEAGES:
            donor.f2._validate_lineage_authority(lineage)
    except (donor.e1.E1Error, donor.f2.F2Error) as error:
        raise DiagnosticRunnerError("inherited frozen input binding failed") from error
    return {
        "source_contract": {
            "path": str(source_contract.resolve()),
            "sha256": donor.file_sha256(source_contract),
            "status": "DEVELOPMENT_SOURCE_BOUND_BY_PREFLIGHT_DIGEST",
        },
        "source_panel": donor.panel_bindings(DEFAULT_HORIZON),
        "lineage_authorities": donor.f2.lineage_authority_bindings(),
        "preregistration": frozen_inputs["preregistration"],
        "tle_archive": frozen_inputs["tle_archive"],
        "eta_ref_exact": donor.fraction_payload(c3s_policy.load_eta_ref()),
        "code_files": expected_code_bindings(),
    }


def validate_preflight_manifest(path: Path) -> tuple[dict[str, Any], str]:
    payload = donor.load_json(path, field="diagnostic preflight manifest")
    expected = {
        "schema": PREFLIGHT_SCHEMA, "status": "FROZEN_PREFLIGHT",
        "claim_ceiling": CLAIM_CEILING, **static_bindings(),
        "purpose": "C3S_PLACEBO_AND_HOSTILE_BASELINE_DIAGNOSTICS",
        "test_split_opened": False, "episode_training": False,
        "learner_update": False, "efficacy_claim": False,
    }
    if payload != expected:
        raise DiagnosticRunnerError("diagnostic preflight bindings drifted")
    digest = donor.file_sha256(path)
    donor._validate_sealed(path, digest=digest, field="diagnostic preflight manifest")
    return payload, digest


def authority_common_binding(authority: Mapping[str, object]) -> dict[str, object]:
    execution = authority.get("execution")
    if not isinstance(execution, Mapping):
        raise DiagnosticRunnerError("launch authority execution binding is absent")
    return {
        key: authority.get(key) for key in (
            "claim_ceiling", "preflight_manifest", "source_contract", "code_files",
            "lineage_authorities", "preregistration", "tle_archive", "output_root",
        )
    } | {"panel": execution.get("panel")}


def validate_launch_authority(
    path: Path, *, preflight_path: Path, output_root: Path,
    launch_arguments: Sequence[str], target: UnitKey | None, horizon: int,
    arms: Sequence[str], assert_null_equals_base: bool,
    physics_override: str,
    handover_energy_sensitivity: bool = False,
) -> tuple[dict[str, Any], str]:
    payload = donor.load_json(path, field="diagnostic launch authority")
    digest = donor.file_sha256(path)
    donor._validate_sealed(path, digest=digest, field="diagnostic launch authority")
    manifest, preflight_sha = validate_preflight_manifest(preflight_path)
    static = static_bindings()
    parsed = _parser().parse_args(list(launch_arguments))
    parsed_target = UnitKey.parse(parsed.unit) if parsed.unit else None
    if (
        parsed.dry_run or parsed.estimate or parsed_target != target
        or (parsed.unit is None) == (not parsed.merge)
        or parsed.horizon != horizon or parse_arms(parsed.arms) != parse_arms(arms)
        or bool(parsed.assert_null_equals_base) != bool(assert_null_equals_base)
        or parsed.physics_override != physics_override
        or bool(parsed.handover_energy_sensitivity) != bool(handover_energy_sensitivity)
        or parsed.launch_authority is None
        or Path(parsed.launch_authority).resolve() != Path(path).resolve()
        or Path(parsed.preflight_manifest).resolve() != Path(preflight_path).resolve()
        or donor._local(parsed.output, field="diagnostic output root")
        != donor._local(output_root, field="diagnostic output root")
    ):
        raise DiagnosticRunnerError("launch arguments do not bind the validated invocation")
    expected = {
        "schema": LAUNCH_AUTHORITY_SCHEMA, "status": "FROZEN_LAUNCH_AUTHORITY",
        "claim_ceiling": CLAIM_CEILING,
        "preflight_manifest": {"path": str(Path(preflight_path).resolve()), "sha256": preflight_sha},
        "source_contract": static["source_contract"], "code_files": static["code_files"],
        "lineage_authorities": static["lineage_authorities"],
        "preregistration": static["preregistration"], "tle_archive": static["tle_archive"],
        "execution": {
            "mode": "unit" if target is not None else "merge",
            "unit": None if target is None else target.as_dict(),
            "panel": panel_bindings(
                horizon=horizon, arms=arms,
                assert_null_equals_base=assert_null_equals_base,
                physics_override=physics_override,
            ),
        },
        "output_root": str(donor._local(output_root, field="diagnostic output root")),
        "launch_arguments": list(launch_arguments),
        "merge_analysis": {
            "handover_energy_sensitivity": bool(handover_energy_sensitivity),
        },
        "preflight_status": manifest["status"],
        "test_split_opened": False, "episode_training": False,
        "learner_update": False, "efficacy_claim": False,
    }
    if payload != expected:
        raise DiagnosticRunnerError("diagnostic launch authority does not bind this invocation")
    return payload, digest


def _step_metric(outcome: Any, interval_s: float) -> dict[str, object]:
    rates = np.asarray(outcome.link_rate_bps, dtype=np.float64)
    power = float(outcome.system_power_w)
    served = int(outcome.resolution.served_count)
    if (
        rates.shape != (USERS,) or not np.all(np.isfinite(rates)) or np.any(rates < 0)
        or not math.isfinite(power) or power <= 0 or not 0 <= served <= USERS
    ):
        raise DiagnosticRunnerError("committed physical endpoint is malformed")
    return {
        "bits_hex": (interval_s * math.fsum(float(value) for value in rates)).hex(),
        "energy_j_hex": (interval_s * power).hex(),
        "served": served, "opportunities": USERS,
    }


def _nominal_step_metric(
    step_env: Any, observation: Any, actions: np.ndarray, interval_s: float,
) -> dict[str, object]:
    """Evaluate the executed vector once under the detached nominal convention."""

    snapshot, evaluator = diagnostic._detached_snapshot(
        step_env, observation, reference=np.asarray(actions, dtype=np.int64)
    )
    outcome = evaluator.evaluate(np.asarray(actions, dtype=np.int64))
    rates = np.asarray(outcome.link_rate_bps, dtype=np.float64)
    return {
        "bits_hex": (interval_s * math.fsum(float(value) for value in rates)).hex(),
        "energy_j_hex": (interval_s * float(outcome.system_power_w)).hex(),
        "served": int(outcome.resolution.served_count),
        "opportunities": int(rates.size),
    }


def _realised_associations(outcome: Any) -> tuple[tuple[int, int] | None, ...]:
    resolution = outcome.resolution
    served = np.asarray(resolution.served, dtype=np.bool_)
    return tuple(
        (int(resolution.serving_satellite[uid]), int(resolution.serving_cell[uid]))
        if served[uid] else None
        for uid in range(served.size)
    )


def _segment_age_metric(step_env: Any) -> dict[str, object]:
    segments = tuple(getattr(step_env, "_segments", ()))
    ages = [int(segment.age_steps) for segment in segments if segment is not None]
    if any(age < 0 for age in ages):
        raise DiagnosticRunnerError("negative association segment age")
    histogram = {
        str(age): ages.count(age) for age in sorted(set(ages))
    }
    return {
        "mean_hex": None if not ages else (math.fsum(ages) / len(ages)).hex(),
        "histogram": histogram,
        "associated_users": len(ages),
        "unassociated_users": len(segments) - len(ages),
    }


def _age_vector_metric(ages: np.ndarray) -> dict[str, object]:
    values = [int(value) for value in np.asarray(ages, dtype=np.int64).tolist()]
    return {
        "mean_hex": (math.fsum(values) / len(values)).hex() if values else None,
        "histogram": {str(age): values.count(age) for age in sorted(set(values))},
        "users": len(values),
    }


def _prepare_explicit_renewals(step_env: Any, users: Sequence[int]) -> None:
    """Open new segments for declared renewal events without editing source physics."""

    segments = getattr(step_env, "_segments", None)
    if not isinstance(segments, list):
        raise DiagnosticRunnerError("environment does not expose diagnostic segment state")
    for uid in users:
        if not 0 <= int(uid) < len(segments):
            raise DiagnosticRunnerError("explicit renewal user is out of range")
        segments[int(uid)] = None
    pending = getattr(step_env, "_pending_segment_age", None)
    if int(getattr(step_env, "_step_index", -1)) == 0 and pending is not None:
        for uid in users:
            pending[int(uid)] = 0


def _physical_changes_vs_base(
    observation: Any, actions: np.ndarray, base: np.ndarray,
) -> int:
    tables = tuple(observation.candidates.slot_tables)
    if len(tables) != actions.size or actions.shape != base.shape:
        raise DiagnosticRunnerError("BASE comparison shape differs")
    changed = 0
    for uid, (action, base_action) in enumerate(zip(actions, base, strict=True)):
        def key(value: int) -> tuple[int, int] | None:
            if value == donor.f1.NO_OP_ACTION:
                return None
            return (
                int(tables[uid].norad_ids[value]), int(tables[uid].cell_ids[value])
            )
        changed += key(int(action)) != key(int(base_action))
    return int(changed)


def run_arm_trajectory(
    *, environment: Any, env_rng: np.random.Generator,
    mobility_rng: np.random.Generator, horizon: int,
    selector: Callable[[Any, Any, np.random.Generator], np.ndarray],
    decision_records: list[dict[str, object]] | None = None,
    nominal_metric_provider: (
        Callable[[Any, Any, np.ndarray, float], Mapping[str, object]] | None
    ) = None,
) -> dict[str, object]:
    """Run one arm with action authentication and per-step mechanism receipts."""

    _states, _masks, observation = environment.reset(env_rng, mobility_rng)
    step_env = environment.environment
    native = __import__("mcrl.runtime.ee_axis_state", fromlist=["encode_ee_axis_state"]).encode_ee_axis_state(
        step_env, observation
    )
    interval_s = float(step_env.driver.config.ephemeris.time_step_s)
    steps: list[dict[str, object]] = []
    wall: list[str] = []
    trace = hashlib.sha256()
    previous_realised: tuple[tuple[int, int] | None, ...] | None = None
    for step in range(horizon):
        if int(observation.step_index) != step:
            raise DiagnosticRunnerError("trajectory decision index drifted")
        age_before = _age_vector_metric(
            diagnostic.segment_ages_before_decision(step_env, USERS)
        )
        started = time.perf_counter()
        actions = np.asarray(selector(step_env, observation, env_rng))
        wall.append((time.perf_counter() - started).hex())
        masks = np.asarray(observation.masks)
        eligible = np.any(masks, axis=1)
        rows = np.arange(USERS)
        if (
            actions.dtype.kind not in "iu" or actions.shape != (USERS,)
            or masks.shape != (USERS, donor.f1.NUM_ACTIONS) or masks.dtype != np.bool_
            or np.any(actions[eligible] < 0) or np.any(actions[eligible] >= donor.f1.NUM_ACTIONS)
            or np.any(~masks[rows[eligible], actions[eligible]])
            or np.any(actions[~eligible] != donor.f1.NO_OP_ACTION)
        ):
            raise DiagnosticRunnerError("selector returned an illegal complete action")
        selected = actions.astype(np.int64, copy=True)
        record = None
        if decision_records is not None:
            if len(decision_records) != step + 1:
                raise DiagnosticRunnerError("selector decision receipt coverage drifted")
            record = decision_records[-1]
        explicit = tuple(int(value) for value in (record or {}).get("explicit_renewal_users", ()))
        _prepare_explicit_renewals(step_env, explicit)
        nominal = (
            dict(nominal_metric_provider(step_env, observation, selected, interval_s))
            if nominal_metric_provider is not None
            else None
        )
        action_bytes = selected.tobytes(order="C")
        trace.update(action_bytes)
        result = environment.step(selected, env_rng)
        outcome = environment.last_outcome
        done = bool(getattr(outcome, "done", getattr(result, "done", False)))
        if done != (step == horizon - 1):
            raise DiagnosticRunnerError("trajectory termination differs from fixed horizon")
        realised = _realised_associations(outcome)
        association_changed = (
            0 if previous_realised is None else
            sum(left != right for left, right in zip(previous_realised, realised, strict=True))
        )
        native_handover_users = {
            uid for uid, value in enumerate(getattr(outcome, "handovers", ()))
            if getattr(value, "value", "none") != "none"
        }
        handover_events = native_handover_users | set(explicit)
        age_metric = _segment_age_metric(step_env)
        dwell = getattr(getattr(observation, "candidates", None), "dwell", None)
        dwell_phase = int(round(float(getattr(dwell, "phase", (step % 4) / 4.0)) * 4)) % 4
        realised_metric = _step_metric(outcome, interval_s)
        link_power = np.asarray(getattr(outcome, "link_power_w", np.zeros(USERS)), dtype=np.float64)
        if link_power.shape != (USERS,) or np.any(~np.isfinite(link_power)) or np.any(link_power < 0):
            raise DiagnosticRunnerError("per-user transmit powers are malformed")
        served_power = np.where(
            np.asarray(outcome.resolution.served, dtype=np.bool_), link_power, 0.0
        )
        configuration = str((record or {}).get("executed_configuration_type", "UNSPECIFIED"))
        steps.append({
            "step_index": step,
            "actions_sha256": hashlib.sha256(action_bytes).hexdigest(),
            **realised_metric,
            "association_changed_users": int(association_changed),
            "handover_count": len(native_handover_users),
            "explicit_renewal_count": len(set(explicit)),
            "handover_or_renewal_count": len(handover_events),
            "users_changed_vs_base": int((record or {}).get("users_changed_vs_base", 0)),
            "active_beam_count": int(getattr(getattr(outcome, "radiating", None), "count", 0)),
            "association_segment_age": age_metric,
            "association_segment_age_before_decision": age_before,
            "dwell_phase_index": dwell_phase,
            "per_user_transmit_power_sum_w_hex": math.fsum(float(value) for value in served_power).hex(),
            "nominal": nominal,
            "realised": dict(realised_metric),
            "executed_configuration_type": configuration,
        })
        previous_realised = realised
        observation = outcome.observation
    return {
        "initial_state_sha256": native.state_sha256,
        "action_trace_sha256": trace.hexdigest(),
        "decision_wall_seconds_hex": wall, "steps": steps,
    }


def assert_null_equals_base(arms: Mapping[str, Mapping[str, object]]) -> None:
    """Fail on the first action/bits/joules/served step mismatch."""

    if "NULL" not in arms or BASE_ARM not in arms:
        raise DiagnosticRunnerError("NULL equality assertion lacks both trajectories")
    base_steps = arms[BASE_ARM].get("steps")
    null_steps = arms["NULL"].get("steps")
    if not isinstance(base_steps, list) or not isinstance(null_steps, list) or len(base_steps) != len(null_steps):
        raise DiagnosticRunnerError("NULL and BASE step coverage differs")
    fields = ("step_index", "actions_sha256", "bits_hex", "energy_j_hex", "served", "opportunities")
    for index, (base, null) in enumerate(zip(base_steps, null_steps, strict=True)):
        if not isinstance(base, Mapping) or not isinstance(null, Mapping) or any(base.get(k) != null.get(k) for k in fields):
            raise DiagnosticRunnerError(f"NULL differs from BASE at step {index}")


def _make_environment(
    archive: Any, *, horizon: int,
    physics_override: physics_ablation.PhysicsOverride,
) -> Any:
    """Construct the TRAIN wrapper around the explicit diagnostic physics path."""

    from mcrl.env.ephemeris import TRAIN, BlockAlternatingSplit, EpisodeStartSampler
    from mcrl.env.mobility import MobilityConfig
    from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
    from mcrl.runtime.trainer_env import TrainerEnvironment

    driver = ScenarioDriver(
        archive,
        ScenarioConfig(mobility=MobilityConfig(num_users=USERS), steps_per_episode=horizon),
    )
    split = BlockAlternatingSplit.for_archive(archive)
    sampler = EpisodeStartSampler.for_archive(archive, split, TRAIN)
    environment = physics_ablation.DiagnosticStepEnvironment.construct(
        driver, physics_override=physics_override,
    )
    return TrainerEnvironment(environment, sampler)


def execute_physical_unit(
    key: UnitKey, *, horizon: int, selected_arms: Sequence[str],
    assert_null: bool, physics_override: str = "none",
) -> dict[str, object]:
    """Execute BASE and selected diagnostics from independently reset worlds."""

    from mcrl.env.keyed_fading import KeyedFadingField
    from mcrl.runtime.prereg import read_prereg
    from mcrl.runtime.training_pipeline import _evaluation_rngs

    key.verify()
    chosen = parse_arms(selected_arms)
    record = read_prereg(donor.f1.PREREG_PATH)
    if record.digest != donor.f1.PREREG_RECORD_DIGEST:
        raise DiagnosticRunnerError("TRAIN PREREG semantic digest changed")
    physical, server = donor.f1._runtime_modules()
    frozen = donor.f2._load_frozen_heads(key.lineage)
    override = physics_ablation.get_physics_override(physics_override)
    q_before = (physical._parameter_sha256(frozen.q1), physical._parameter_sha256(frozen.q2))
    with tempfile.TemporaryDirectory(prefix=f"c3s-diag-{key.slug}-", dir=os.environ.get("TMPDIR")) as temporary:
        archive = server._freeze_archive(
            record, donor.CANONICAL_TLE_ROOT, Path(temporary) / "frozen", physical
        )
        trajectories: dict[str, dict[str, object]] = {}
        decisions: dict[str, list[dict[str, object]]] = {}
        arms = (BASE_ARM, *chosen)
        for arm in arms:
            environment = _make_environment(
                archive, horizon=horizon, physics_override=override,
            )
            environment.environment._fading_field = KeyedFadingField.from_components(
                FIELD_COMPONENT, key.world
            )
            rngs = tuple(_evaluation_rngs(key.world))
            if len(rngs) < 2:
                raise DiagnosticRunnerError("canonical RNG factory lacks two streams")

            def base_proposal(step_env: Any, observation: Any) -> np.ndarray:
                return donor.e1._q12_surface_base_only(
                    physical, frozen, step_env, observation
                )[2]

            if arm == BASE_ARM:
                base_records: list[dict[str, object]] = []

                def selector(step_env: Any, observation: Any, _rng: np.random.Generator) -> np.ndarray:
                    started = time.perf_counter()
                    actions = base_proposal(step_env, observation)
                    base_records.append({
                        "decision_index": len(base_records), "q_head_accesses": 2,
                        "wall_seconds_hex": (time.perf_counter() - started).hex(),
                        "selected_profile_id": "BASE",
                        "executed_configuration_type": "BASE",
                        "users_changed_vs_base": 0,
                        "explicit_renewal_users": [],
                    })
                    return actions
                decisions[arm] = base_records
            elif arm in {"FULL", "LITE"}:
                adapter = c3s_policy.C3SPolicyAdapter(
                    physical=physical, frozen=frozen,
                    catalog="full" if arm == "FULL" else "lite",
                )
                selector = adapter.select_actions
                decisions[arm] = adapter.decision_records
            elif arm in LEARNED_ARMS:
                catalog = "full" if arm == "NULL" else "lite"
                adapter: c3s_policy.C3SPolicyAdapter

                def decide(snapshot: Any, evaluator: Any, *, _arm: str = arm) -> Any:
                    return diagnostic.learned_decision(
                        snapshot, evaluator, arm=_arm, world=key.world,
                        lineage=key.lineage, step=len(adapter.decision_records),
                    )

                adapter = c3s_policy.C3SPolicyAdapter(
                    physical=physical, frozen=frozen, catalog=catalog,
                    decision_function=decide,
                )
                selector = adapter.select_actions
                decisions[arm] = adapter.decision_records
            elif arm in CHURN_ARMS:
                churn = diagnostic.ChurnSelector(
                    arm=arm, world=key.world, lineage=key.lineage,
                    base_proposer=base_proposal,
                )
                selector = churn.select_actions
                decisions[arm] = churn.decision_records
            else:
                qfree = diagnostic.QFreeSelector(arm=arm)

                def selector(
                    step_env: Any, observation: Any, rng: np.random.Generator,
                    *, _qfree: diagnostic.QFreeSelector = qfree,
                ) -> np.ndarray:
                    base = np.asarray(base_proposal(step_env, observation), dtype=np.int64)
                    actions = _qfree.select_actions(step_env, observation, rng)
                    row = _qfree.decision_records[-1]
                    row.update({
                        "users_changed_vs_base": _physical_changes_vs_base(
                            observation, np.asarray(actions), base,
                        ),
                        "explicit_renewal_users": [],
                        "executed_configuration_type": (
                            "HEUR_LOCAL_SNR" if _qfree.arm == "HEUR"
                            else "BASE" if row["selected_profile_id"] == "BASE"
                            else "UNILATERAL" if str(row["selected_profile_id"]).startswith("U:")
                            else "EVACUATION"
                        ),
                        "instrumentation_q_head_accesses": 2,
                    })
                    return actions

                decisions[arm] = qfree.decision_records
            trajectories[arm] = run_arm_trajectory(
                environment=environment, env_rng=rngs[0], mobility_rng=rngs[1],
                horizon=horizon, selector=selector,
                decision_records=decisions[arm],
                nominal_metric_provider=_nominal_step_metric,
            )
        if len({row["initial_state_sha256"] for row in trajectories.values()}) != 1:
            raise DiagnosticRunnerError("selected arms did not share identical initial states")
        if assert_null:
            assert_null_equals_base(trajectories)
        q_after = (physical._parameter_sha256(frozen.q1), physical._parameter_sha256(frozen.q2))
        if q_after != q_before:
            raise DiagnosticRunnerError("frozen Q parameters changed")
    return {
        "schema": UNIT_RECEIPT_SCHEMA, "status": "COMPLETE",
        "outcome": "C3S_DIAGNOSTIC_UNIT_COMPLETE", "claim_ceiling": CLAIM_CEILING,
        "unit": key.as_dict(), "horizon": horizon, "users": USERS,
        "split": "TRAIN", "selected_diagnostic_arms": list(chosen),
        "assert_null_equals_base": assert_null,
        "physics_override": override.binding(),
        "null_equals_base": None if "NULL" not in chosen else (
            trajectories["NULL"]["action_trace_sha256"] == trajectories[BASE_ARM]["action_trace_sha256"]
            and trajectories["NULL"]["steps"] == trajectories[BASE_ARM]["steps"]
        ),
        "field_component": FIELD_COMPONENT,
        "field_root_digest": KeyedFadingField.from_components(FIELD_COMPONENT, key.world).root_digest,
        "arms": trajectories, "decisions_by_arm": decisions,
        "q_free_arms": [arm for arm in chosen if arm in Q_FREE_ARMS],
        "integrity": True, "test_split_opened": False, "episode_training": False,
        "learner_update": False, "efficacy_claim": False,
    }


def _fraction_hex(value: object, *, positive: bool = False) -> Fraction:
    parsed = float.fromhex(str(value))
    if not math.isfinite(parsed) or parsed < 0 or positive and parsed <= 0:
        raise DiagnosticRunnerError("endpoint hex is outside its domain")
    return Fraction.from_float(parsed)


def _validate_instrumented_step(step: Mapping[str, object]) -> None:
    if not INSTRUMENTED_STEP_FIELDS <= set(step):
        raise DiagnosticRunnerError("unit step lacks required instrumentation")
    if not isinstance(step.get("nominal"), Mapping) or not isinstance(step.get("realised"), Mapping):
        raise DiagnosticRunnerError("unit step nominal/realised instrumentation is malformed")
    if not isinstance(step.get("association_segment_age"), Mapping):
        raise DiagnosticRunnerError("unit step segment-age instrumentation is malformed")
    for field in (
        "association_changed_users", "handover_count", "explicit_renewal_count",
        "handover_or_renewal_count", "users_changed_vs_base", "active_beam_count",
        "dwell_phase_index",
    ):
        if type(step.get(field)) is not int or int(step[field]) < 0:
            raise DiagnosticRunnerError(f"unit step {field} is malformed")
    if int(step["dwell_phase_index"]) > 3 or any(
        int(step[field]) > USERS for field in (
            "association_changed_users", "handover_count", "explicit_renewal_count",
            "handover_or_renewal_count", "users_changed_vs_base",
        )
    ):
        raise DiagnosticRunnerError("unit step instrumentation count is out of range")
    if not isinstance(step.get("executed_configuration_type"), str) or not step["executed_configuration_type"]:
        raise DiagnosticRunnerError("unit step configuration type is malformed")
    _fraction_hex(step["per_user_transmit_power_sum_w_hex"])


def _paired_stratified_tables(
    receipts: Sequence[Mapping[str, object]], *, arms: Sequence[str], field: str,
) -> dict[str, list[dict[str, object]]]:
    """Pool arm and paired BASE endpoints in each declared step stratum."""

    buckets: dict[str, dict[int, dict[str, Fraction | int]]] = {
        arm: {} for arm in arms
    }
    for receipt in receipts:
        trajectories = receipt["arms"]  # type: ignore[index]
        base_steps = trajectories[BASE_ARM]["steps"]  # type: ignore[index]
        for arm in arms:
            arm_steps = trajectories[arm]["steps"]  # type: ignore[index]
            if len(arm_steps) != len(base_steps):
                raise DiagnosticRunnerError("paired stratum step coverage differs")
            for arm_step, base_step in zip(arm_steps, base_steps, strict=True):
                stratum = int(arm_step[field])
                row = buckets[arm].setdefault(stratum, {
                    "arm_bits": Fraction(0), "arm_energy": Fraction(0),
                    "base_bits": Fraction(0), "base_energy": Fraction(0), "steps": 0,
                })
                row["arm_bits"] += _fraction_hex(arm_step["bits_hex"])  # type: ignore[operator]
                row["arm_energy"] += _fraction_hex(arm_step["energy_j_hex"], positive=True)  # type: ignore[operator]
                row["base_bits"] += _fraction_hex(base_step["bits_hex"])  # type: ignore[operator]
                row["base_energy"] += _fraction_hex(base_step["energy_j_hex"], positive=True)  # type: ignore[operator]
                row["steps"] = int(row["steps"]) + 1
    result: dict[str, list[dict[str, object]]] = {}
    for arm, by_value in buckets.items():
        result[arm] = []
        for value, row in sorted(by_value.items()):
            arm_eta = row["arm_bits"] / row["arm_energy"]  # type: ignore[operator]
            base_eta = row["base_bits"] / row["base_energy"]  # type: ignore[operator]
            result[arm].append({
                "stratum": value, "paired_steps": int(row["steps"]),
                "arm_eta": donor.fraction_payload(arm_eta),
                "paired_base_eta": donor.fraction_payload(base_eta),
                "eta_advantage_vs_paired_base": donor.fraction_payload(arm_eta / base_eta - 1),
            })
    return result


def _handover_energy_sensitivity(
    totals: Mapping[str, Mapping[str, Any]], *, arms: Sequence[str],
) -> dict[str, object]:
    """Offline-only EE repricing on the task-fixed handover-energy grid."""

    base = totals[BASE_ARM]
    grid: dict[str, dict[str, object]] = {}
    break_even: dict[str, object] = {}
    for arm in arms:
        row = totals[arm]
        grid[arm] = {}
        for energy_per_handover in HANDOVER_ENERGY_GRID_J:
            arm_energy = row["energy"] + energy_per_handover * int(row["handover_events"])
            base_energy = base["energy"] + energy_per_handover * int(base["handover_events"])
            advantage = (row["bits"] / arm_energy) / (base["bits"] / base_energy) - 1
            grid[arm][str(float(energy_per_handover))] = donor.fraction_payload(advantage)
        numerator = base["bits"] * row["energy"] - row["bits"] * base["energy"]
        denominator = (
            row["bits"] * int(base["handover_events"])
            - base["bits"] * int(row["handover_events"])
        )
        crossing = None if denominator == 0 else numerator / denominator
        break_even[arm] = {
            "energy_j_per_handover": (
                None if crossing is None or crossing < 0
                else donor.fraction_payload(crossing)
            ),
            "status": (
                "NO_NONNEGATIVE_ZERO_CROSSING"
                if crossing is None or crossing < 0 else "FINITE_ZERO_CROSSING"
            ),
        }
    return {
        "grid_j_per_handover": [donor.fraction_payload(value) for value in HANDOVER_ENERGY_GRID_J],
        "eta_advantage_vs_base": grid,
        "zero_crossing_vs_base": break_even,
        "handover_count_field": "handover_or_renewal_count",
        "provenance": "DECLARED_2026-09-08;30s_x_0.338W_APPROX_10J_ORDER_OF_MAGNITUDE_BRACKET",
        "report_only_no_threshold": True,
    }


def pool_unit_receipts(
    receipts: Sequence[Mapping[str, object]], *, selected_arms: Sequence[str],
    handover_energy_sensitivity: bool = False,
) -> dict[str, object]:
    chosen = parse_arms(selected_arms)
    arms = (BASE_ARM, *chosen)
    totals = {
        arm: {
            "bits": Fraction(0), "energy": Fraction(0), "served": 0,
            "n": 0, "handover_events": 0,
        }
        for arm in arms
    }
    costs = {arm: {"seconds": [], "catalog_rows": 0, "nominal_evaluations": 0} for arm in arms}
    for receipt in receipts:
        if tuple(receipt.get("selected_diagnostic_arms", ())) != chosen:
            raise DiagnosticRunnerError("unit arm selection differs at merge")
        trajectories = receipt.get("arms")
        decisions = receipt.get("decisions_by_arm")
        if not isinstance(trajectories, Mapping) or set(trajectories) != set(arms) or not isinstance(decisions, Mapping):
            raise DiagnosticRunnerError("unit arm coverage is malformed")
        for arm in arms:
            trajectory = trajectories[arm]
            for step in trajectory["steps"]:  # type: ignore[index]
                _validate_instrumented_step(step)
                totals[arm]["bits"] += _fraction_hex(step["bits_hex"])  # type: ignore[index]
                totals[arm]["energy"] += _fraction_hex(step["energy_j_hex"], positive=True)  # type: ignore[index]
                totals[arm]["served"] += int(step["served"])  # type: ignore[index]
                totals[arm]["n"] += int(step["opportunities"])  # type: ignore[index]
                totals[arm]["handover_events"] += int(step["handover_or_renewal_count"])  # type: ignore[index]
            for row in decisions.get(arm, []):
                costs[arm]["seconds"].append(float.fromhex(str(row["wall_seconds_hex"])))
                costs[arm]["catalog_rows"] += int(row.get("catalog_size", 0))
                costs[arm]["nominal_evaluations"] += int(row.get("unique_nominal_evaluations", 0))
    pooled: dict[str, object] = {}
    for arm in arms:
        row = totals[arm]
        eta = row["bits"] / row["energy"]
        service = Fraction(int(row["served"]), int(row["n"]))
        pooled[arm] = {
            "total_bits": donor.fraction_payload(row["bits"]),
            "total_energy_j": donor.fraction_payload(row["energy"]),
            "eta": donor.fraction_payload(eta), "served": row["served"],
            "opportunities": row["n"], "service": donor.fraction_payload(service),
            "handover_or_renewal_count": int(row["handover_events"]),
        }
    eta_base = donor._fraction_from_payload(pooled[BASE_ARM]["eta"])  # type: ignore[index]
    comparisons = {
        arm: {
            "eta_relative_to_base": donor.fraction_payload(
                donor._fraction_from_payload(pooled[arm]["eta"]) / eta_base - 1  # type: ignore[index]
            ),
            "expected_outcome": {
                "NULL": "EQUAL_TO_BASE",
                "RANDOM_FEASIBLE": "POOLED_EE_LE_BASE_REPORT_ONLY",
                "SHUFFLED_SCORE": "APPROX_RANDOM_FEASIBLE_REPORT_ONLY",
            }.get(arm, "DESCRIPTIVE_MECHANISM_SEPARATION"),
        }
        for arm in chosen
    }
    cost_summary = {}
    for arm, row in costs.items():
        seconds = row.pop("seconds")
        cost_summary[arm] = {
            **row, "decisions": len(seconds),
            "mean_selector_seconds_hex": (math.fsum(seconds) / len(seconds)).hex() if seconds else None,
            "total_selector_seconds_hex": math.fsum(seconds).hex(),
        }
    output = {
        "pooled_exact": pooled, "comparisons_vs_base": comparisons, "cost": cost_summary,
        "ee_advantage_vs_base_by_segment_age_phase": {
            "phase_definition": "FROZEN_DWELL_PHASE_INDEX_STEP_MOD_4;RED_TEAM_2026-09-08_DECOMPOSITION",
            "tables": _paired_stratified_tables(
                receipts, arms=chosen, field="dwell_phase_index",
            ),
        },
        "ee_advantage_vs_base_by_handover_count": {
            "handover_count_field": "handover_or_renewal_count",
            "tables": _paired_stratified_tables(
                receipts, arms=chosen, field="handover_or_renewal_count",
            ),
        },
    }
    if handover_energy_sensitivity:
        output["handover_energy_sensitivity"] = _handover_energy_sensitivity(
            totals, arms=chosen,
        )
    return output


def estimate(
    *, units: int, selected_arms: Sequence[str], physics_override: str = "none",
) -> dict[str, object]:
    """Report per-arm planning cost without executing simulator episodes."""

    chosen = parse_arms(selected_arms)
    if units < 1:
        raise DiagnosticRunnerError("--estimate-units must be positive")
    basis = donor.estimate(units=units)
    full_hours = float(basis["horizons"]["30"]["arms"]["FULL"]["worker_hours"])
    ratios = {
        "FULL": 1.0, "LITE": 0.1,
        "NULL": 1.0, "RANDOM_FEASIBLE": 0.1, "SHUFFLED_SCORE": 0.1,
        "RANDOM_RENEW": 0.0, "RANDOM_RENEW_K": 0.0,
        "BASE_FORCED_RENEW_4": 0.0,
        "HEUR": 0.0, "HEUR_C3S_LITE": 1.0, "NOMINAL_MPC": 1.0,
        "LITE_UNILATERAL_ONLY": 0.1, "LITE_EVACUATION_ONLY": 0.1,
    }  # Full/lite ratio inherited from sealed v1 planning; HEUR ranking is explicitly full-pass.
    notes = {
        "RANDOM_RENEW": "BASE-cost churn null; one unscored legal unilateral edit",
        "RANDOM_RENEW_K": "BASE-cost churn null; three unscored legal unilateral edits",
        "BASE_FORCED_RENEW_4": "BASE-cost age-triggered renewal; no energy scoring",
        "HEUR": "Q-free nominal candidate-SINR pass; catalog evaluations are zero",
        "HEUR_C3S_LITE": "full unilateral F pass needed to rank each user's alternative",
        "NOMINAL_MPC": "full unilateral-plus-evacuation nominal catalog",
    }  # Mechanism definitions from the diagnostic task.
    return {
        "schema": f"{SCHEMA}-estimate", "units": units, "horizon": DEFAULT_HORIZON,
        "physics_override": physics_ablation.get_physics_override(physics_override).binding(),
        "episodes": units * (1 + len(chosen)), "arms": {
            BASE_ARM: {"worker_hours": 0.0, "note": "committed execution and Q inference excluded"},
            **{
                arm: {
                    "worker_hours": full_hours * ratios[arm],
                    "relative_to_v1_full_catalog": ratios[arm],
                    "note": notes.get(arm, "v1 full/lite nominal-evaluation planning ratio"),
                }
                for arm in chosen
            },
        },
        "basis": basis["basis"],
        "caveat": (
            "planning estimate only; 0.0 means no catalog worker-hours and still "
            "incurs BASE inference, instrumentation, and committed episode execution"
        ),
    }


def _unit_path(root: Path, key: UnitKey) -> Path:
    return root / "units" / key.slug / UNIT_RECEIPT_NAME


def _publish_unit(root: Path, key: UnitKey, payload: Mapping[str, object]) -> Path:
    destination = donor._local(root, field="diagnostic output root") / "units" / key.slug
    if destination.exists() or destination.is_symlink():
        raise DiagnosticRunnerError("refusing to overwrite diagnostic unit")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".stage-{key.slug}-", dir=destination.parent))
    donor.write_once_with_sidecar(stage / UNIT_RECEIPT_NAME, payload)
    stage.chmod(0o555)
    os.rename(stage, destination)
    return destination / UNIT_RECEIPT_NAME


def execute_unit(
    *, key: UnitKey, output: Path, horizon: int, selected_arms: Sequence[str],
    assert_null: bool, preflight_sha256: str, authority: Mapping[str, object],
    authority_sha256: str, authority_path: Path,
    physics_override: str = "none",
) -> tuple[Path, bool]:
    root = donor._local(output, field="diagnostic output root")
    existing = _unit_path(root, key)
    if existing.exists():
        receipt = donor.load_json(existing, field="existing diagnostic unit")
        if receipt.get("status") != "COMPLETE" or receipt.get("producer_common_binding") != authority_common_binding(authority):
            raise DiagnosticRunnerError("existing diagnostic unit is not reusable")
        return existing, True
    try:
        payload = execute_physical_unit(
            key, horizon=horizon, selected_arms=selected_arms, assert_null=assert_null,
            physics_override=physics_override,
        )
        valid = True
    except Exception as error:
        payload = {
            "schema": UNIT_RECEIPT_SCHEMA, "status": "INVALID_RUN",
            "outcome": "INVALID_RUN", "scope": "unit", "claim_ceiling": CLAIM_CEILING,
            "unit": key.as_dict(), "horizon": horizon,
            "selected_diagnostic_arms": list(parse_arms(selected_arms)),
            "assert_null_equals_base": assert_null,
            "physics_override": physics_ablation.get_physics_override(physics_override).binding(),
            "error_type": type(error).__name__,
            "error_sha256": hashlib.sha256(str(error).encode("utf-8")).hexdigest(),
            "integrity": False, "test_split_opened": False,
            "episode_training": False, "learner_update": False, "efficacy_claim": False,
        }
        valid = False
    payload.update({
        "preflight_manifest_sha256": preflight_sha256,
        "launch_authority_sha256": authority_sha256,
        "launch_authority": {"path": str(Path(authority_path).resolve()), "sha256": authority_sha256},
        "producer_common_binding": authority_common_binding(authority),
    })
    return _publish_unit(root, key, payload), valid


def execute_merge(
    *, output: Path, horizon: int, selected_arms: Sequence[str], assert_null: bool,
    preflight_sha256: str, authority: Mapping[str, object], authority_sha256: str,
    authority_path: Path,
    physics_override: str = "none", handover_energy_sensitivity: bool = False,
) -> Path:
    root = donor._local(output, field="diagnostic output root")
    receipts: list[dict[str, Any]] = []
    bindings: list[dict[str, object]] = []
    missing = 0
    common = authority_common_binding(authority)
    for key in ALL_UNITS:
        path = _unit_path(root, key)
        if not path.exists():
            missing += 1
            continue
        digest = donor.file_sha256(path)
        donor._validate_sealed(path, digest=digest, field="diagnostic unit")
        receipt = donor.load_json(path, field="diagnostic unit")
        producer = receipt.get("launch_authority")
        if not isinstance(producer, Mapping) or set(producer) != {"path", "sha256"}:
            raise DiagnosticRunnerError(f"unit {key.slug} lacks producer authority")
        producer_path = Path(str(producer["path"]))
        producer_payload = donor.load_json(producer_path, field="unit producer authority")
        producer_arguments = producer_payload.get("launch_arguments")
        if not isinstance(producer_arguments, list):
            raise DiagnosticRunnerError(f"unit {key.slug} producer authority is malformed")
        validated_producer, producer_sha = validate_launch_authority(
            producer_path,
            preflight_path=Path(str(common["preflight_manifest"]["path"])),  # type: ignore[index]
            output_root=root, launch_arguments=producer_arguments, target=key,
            horizon=horizon, arms=selected_arms,
            assert_null_equals_base=assert_null,
            physics_override=physics_override,
            handover_energy_sensitivity=False,
        )
        if (
            receipt.get("schema") != UNIT_RECEIPT_SCHEMA or receipt.get("status") != "COMPLETE"
            or receipt.get("unit") != key.as_dict() or receipt.get("horizon") != horizon
            or tuple(receipt.get("selected_diagnostic_arms", ())) != parse_arms(selected_arms)
            or receipt.get("assert_null_equals_base") != assert_null
            or receipt.get("physics_override")
            != physics_ablation.get_physics_override(physics_override).binding()
            or receipt.get("producer_common_binding") != common
            or receipt.get("launch_authority_sha256") != producer_sha
            or producer.get("sha256") != producer_sha
            or authority_common_binding(validated_producer) != common
        ):
            raise DiagnosticRunnerError(f"unit {key.slug} is not merge-compatible")
        if assert_null and receipt.get("null_equals_base") is not True:
            raise DiagnosticRunnerError(f"unit {key.slug} failed NULL equality")
        receipts.append(receipt)
        bindings.append({"unit": key.as_dict(), "path": str(path.relative_to(root)), "sha256": digest})
    if missing:
        raise MergeWaiting(missing)
    payload = {
        "schema": TERMINAL_RECEIPT_SCHEMA, "status": "COMPLETE",
        "outcome": "C3S_DIAGNOSTIC_PANEL_COMPLETE", "claim_ceiling": CLAIM_CEILING,
        "panel": panel_bindings(
            horizon=horizon, arms=selected_arms,
            assert_null_equals_base=assert_null, physics_override=physics_override,
        ),
        **pool_unit_receipts(
            receipts, selected_arms=selected_arms,
            handover_energy_sensitivity=handover_energy_sensitivity,
        ),
        "handover_energy_sensitivity_requested": handover_energy_sensitivity,
        "unit_receipts": bindings, "preflight_manifest_sha256": preflight_sha256,
        "launch_authority_sha256": authority_sha256,
        "launch_authority": {"path": str(Path(authority_path).resolve()), "sha256": authority_sha256},
        "producer_common_binding": common, "integrity": True,
        "test_split_opened": False, "episode_training": False,
        "learner_update": False, "efficacy_claim": False,
    }
    return donor._publish_directory_artifact(
        root, directory_name="terminal", filename=TERMINAL_RECEIPT_NAME, payload=payload,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-manifest", type=Path, default=DEFAULT_PREFLIGHT)
    parser.add_argument("--launch-authority", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--horizon", type=int, default=DEFAULT_HORIZON)
    parser.add_argument("--arms", nargs="+", default=list(DIAGNOSTIC_ARMS))
    parser.add_argument("--assert-null-equals-base", action="store_true")
    parser.add_argument(
        "--physics-override", choices=physics_ablation.OVERRIDE_NAMES, default="none",
    )
    parser.add_argument("--handover-energy-sensitivity", action="store_true")
    parser.add_argument("--unit", metavar="WORLD:LINEAGE")
    parser.add_argument("--merge", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--estimate", action="store_true")
    parser.add_argument("--estimate-units", type=int, default=12)
    return parser


def run(args: argparse.Namespace) -> dict[str, object]:
    selected = parse_arms(args.arms)
    if args.estimate:
        return {"mode": "estimate", "estimate": estimate(
            units=args.estimate_units, selected_arms=selected,
            physics_override=args.physics_override,
        )}
    if args.dry_run:
        return {"mode": "dry-run", "panel": panel_bindings(
            horizon=args.horizon, arms=selected,
            assert_null_equals_base=args.assert_null_equals_base,
            physics_override=args.physics_override,
        )}
    preflight, preflight_sha = validate_preflight_manifest(args.preflight_manifest)
    del preflight
    key = UnitKey.parse(args.unit) if args.unit else None
    if args.launch_authority is None:
        raise DiagnosticRunnerError("execution requires --launch-authority")
    authority, authority_sha = validate_launch_authority(
        args.launch_authority, preflight_path=args.preflight_manifest,
        output_root=args.output, launch_arguments=args.raw_launch_arguments,
        target=key, horizon=args.horizon, arms=selected,
        assert_null_equals_base=args.assert_null_equals_base,
        physics_override=args.physics_override,
        handover_energy_sensitivity=args.handover_energy_sensitivity,
    )
    if key is not None:
        receipt, valid = execute_unit(
            key=key, output=args.output, horizon=args.horizon, selected_arms=selected,
            assert_null=args.assert_null_equals_base, preflight_sha256=preflight_sha,
            authority=authority, authority_sha256=authority_sha,
            authority_path=args.launch_authority,
            physics_override=args.physics_override,
        )
        return {"mode": "unit", "receipt": str(receipt), "valid": valid}
    receipt = execute_merge(
        output=args.output, horizon=args.horizon, selected_arms=selected,
        assert_null=args.assert_null_equals_base, preflight_sha256=preflight_sha,
        authority=authority, authority_sha256=authority_sha,
        authority_path=args.launch_authority,
        physics_override=args.physics_override,
        handover_energy_sensitivity=args.handover_energy_sensitivity,
    )
    return {"mode": "merge", "receipt": str(receipt), "valid": True}


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(__import__("sys").argv[1:] if argv is None else argv)
    args = _parser().parse_args(raw)
    args.raw_launch_arguments = raw
    if not args.estimate and not args.dry_run and (args.unit is None) == (not args.merge):
        print("C3S_DIAGNOSTIC_ERROR: choose exactly one of --unit or --merge", file=__import__("sys").stderr)
        return 2
    if args.handover_energy_sensitivity and not args.merge:
        print("C3S_DIAGNOSTIC_ERROR: --handover-energy-sensitivity is merge-only", file=__import__("sys").stderr)
        return 2
    try:
        if not args.estimate and not args.dry_run:
            donor.pin_single_thread_runtime()
        result = run(args)
    except MergeWaiting as error:
        print(f"C3S_DIAGNOSTIC_INCOMPLETE missing_units={error.missing}")
        return 3
    except Exception as error:
        print(f"C3S_DIAGNOSTIC_REFUSED: {error}", file=__import__("sys").stderr)
        return 2
    if result["mode"] == "estimate":
        print(json.dumps(result["estimate"], sort_keys=True, indent=2))
    elif result["mode"] == "dry-run":
        print(json.dumps(result["panel"], sort_keys=True, indent=2))
    else:
        print(f"C3S_DIAGNOSTIC_{str(result['mode']).upper()} receipt={result['receipt']}")
    return 0 if result.get("valid", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
