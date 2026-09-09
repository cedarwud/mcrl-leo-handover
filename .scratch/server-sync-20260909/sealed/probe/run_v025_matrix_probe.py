#!/usr/bin/env python3
"""Run the TRAIN-only V0.25 v1.2 matrix probe.

``--dry-run`` and ``--rehearsal`` execute the real V0.25 radiation, ACM,
energy, target, set-decoder, and receipt path on a tiny deterministic provider.
The provider is converted to primitive snapshots; no environment or Satrec is
ever deep-copied.  A server launcher may replace only ``WORLD_PROVIDER_FACTORY``.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, TimeoutError as FutureTimeoutError
from concurrent.futures.process import BrokenProcessPool
import datetime as dt
from dataclasses import dataclass, replace
from functools import cmp_to_key
from fractions import Fraction
import hashlib
import itertools
import importlib
import json
import math
import multiprocessing as mp
import os
from pathlib import Path
import pickle
import stat
import sys
import time
import uuid
from typing import Callable, Iterable, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from mcrl.errors import MCRLContractError  # noqa: E402
from mcrl.physics_v025.acm import ACM_MODES, rate_model, select_mode  # noqa: E402
from mcrl.physics_v025.architectures import RadiationConfig  # noqa: E402
from mcrl.physics_v025.architectures import Geometry, Link  # noqa: E402
from mcrl.physics_v025.adapter import (  # noqa: E402
    CellScore,
    build_shared_tape,
    discontinuities_from_event_ledger,
    score_setting,
)
from mcrl.physics_v025.batch import evaluate_ar_tdm_catalogue  # noqa: E402
from mcrl.physics_v025.channel import (  # noqa: E402
    fading_product_quantile,
    noise_power_w,
    transmit_gain_linear,
)
from mcrl.physics_v025.calibration import (  # noqa: E402
    CalibrationObservation,
    CalibrationValues,
    NominalConfiguration,
    freeze_setting_calibration,
    nominal_greedy_reference,
    assert_calibration_world_separation,
)
from mcrl.physics_v025.constants_v025 import (  # noqa: E402
    BEAM_RF_CAP_W,
    DECISION_INTERVAL_S,
    SINR_MIN_DB,
    constant_manifest,
)
from mcrl.physics_v025.energy import (  # noqa: E402
    HardwareInventory,
    PRIMARY_IDLE_POWER_W,
    SENSITIVITY_IDLE_POWER_W,
    schedule_energy,
)
from mcrl.physics_v025.endpoint import StepEndpoint  # noqa: E402
from mcrl.physics_v025.integration import InterruptionEvent  # noqa: E402
from mcrl.physics_v025.matrix import (  # noqa: E402
    ALL_SEALED_RUN_SETTINGS,
    LAUNCH_RUN_ORDER,
    MATRIX_SETTINGS,
    PRIMARY_RUN_SETTING,
    REGIME_RUN_SETTINGS,
    PhysicsSetting,
    SealedRunSetting,
    run_setting_for,
    shared_computation_plan,
)
from mcrl.physics_v025.parity import (  # noqa: E402
    DecisionProfile,
    common_action_bootstrap,
    declared_c3_oracle,
    demand_cap_profiles,
    production_c3,
    reoptimize_joint_by_regime,
    reward_endpoint_identity,
    trace_declared_target_decoder_parity,
)
from mcrl.physics_v025.tapes import (  # noqa: E402
    CALIBRATION_WORLD_DOMAINS,
    DEVELOPMENT_WORLD_DOMAINS,
    KAT_WORLD_DOMAINS,
    PROBE_WORLD_DOMAINS,
    PROVIDER_KAT_WORLD_DOMAINS,
    REFERENCE_CARRIERS,
    SMOKE_WORLD_DOMAINS,
    SYNTHETIC_WORLD_DOMAINS,
    ExogenousWorldTape,
    PrimitiveWorldProvider,
    ProviderProtocolOutputs,
    TinySyntheticProvider,
    build_world_tape,
    canonical_bytes,
    corrected_boundary_rekey_rate,
    digest_payload,
    seed_from_domain,
)
from mcrl.physics_v025.targets import (  # noqa: E402
    NetworkOutcome,
    OffsetProjection,
    c1_difference_surplus,
    c2_persistence_forecast,
    c3_lcsrs_interaction,
    classify_physical_transition,
    network_objective,
    matched_anchor_decomposition,
    phi_qos,
    project_three_offsets,
    set_score_decomposition,
    assert_reward_core_identity,
)


SCHEMA = "multi-catfish-mcrl-v025-matrix-probe-v1.9-stage4h"
SWEEP_SCHEMA = "multi-catfish-mcrl-v025-ch5-sweep-v1-stage4i"
UNIT_SCHEMA = f"{SCHEMA}-unit-receipt"
MERGE_SCHEMA = f"{SCHEMA}-merge-receipt"
DEFAULT_OUTPUT = REPO / "artifacts/v025-physics-successor/matrix-probe"
ATTEMPT_REGISTRY = Path("/home/sat/mcrl-records/ATTEMPT-REGISTRY-2026-09.jsonl")
REFERENCE_SECONDS = 302.0
REFERENCE_WORKERS = 4
REFERENCE_EVALUATIONS = 3_840
ORCHESTRATION_RESERVE = 1.30
OVERNIGHT_CORE_HOURS = 160.0

ALL_NEUTRAL_CONTROL = "ALL_NEUTRAL_CONTROL"
REPORTING_ONLY_ARMS = ("ONLY_C1", "ONLY_C1C2")
ARMS = (
    "E1_U1",
    "E1_J1",
    "UNION_CATALOGUE_OPTIMUM",
    "S0_DEPLOYABLE",
    *REPORTING_ONLY_ARMS,
    "FULL",
    "DROP_C1",
    "DROP_C2",
    "DROP_C3",
    "UNI",
    "S_UNI",
    ALL_NEUTRAL_CONTROL,
    "NULL",
    "RANDOM_FEASIBLE",
    "NOMINAL_GREEDY",
)
MARGINALS = {
    "C1": ("FULL", "DROP_C1"),
    "C2": ("FULL", "DROP_C2"),
    "C3": ("FULL", "DROP_C3"),
}
TOP_PROPOSALS = 2
SHORTLIST_OPTIONS_PER_USER = 8
# The sealed fading quantile the catalogue's k=0 unilateral surplus ranking
# reads.  Stage 1 may reuse those profiles only when it reads the same view.
CATALOGUE_RANKING_ALPHA = 0.10
# Purely a performance switch, carried so the selection-identity KAT can run
# the same anchor with and without the k=0 reuse and the worker-side ranking
# pass and assert that the coordinator ranks the identical configuration.
# It selects no physics and enters no receipt field that a claim reads.
SELECTION_REUSE_ENABLED = True
FIVE_BOUNDARY_SELECTION_INDICES = (0, 12, 24, 36, 47)
ONE_BOUNDARY_PER_OFFSET_INDICES = (0,)
SELECTION_BOUNDARY_INDICES = ONE_BOUNDARY_PER_OFFSET_INDICES
SELECTION_STAGE2_M = 48
SELECTION_TIE_RELATIVE_TOLERANCE = Fraction(1, 1_000_000_000)
ARM_PRIMARY_COMPONENTS = {
    "ONLY_C1": ("C1",),
    "ONLY_C1C2": ("C1",),
    "FULL": ("C1", "C3"),
    "DROP_C1": ("C3",),
    "DROP_C2": ("C1", "C3"),
    "DROP_C3": ("C1",),
}
ARM_C2_TIEBREAK = {
    "ONLY_C1": False,
    "ONLY_C1C2": True,
    "FULL": True,
    "DROP_C1": True,
    "DROP_C2": False,
    "DROP_C3": True,
}
COMPLETE_CATALOGUE_LIMIT = 4_096
PAIRWISE_TOP_K_USERS = 10
CATALOGUE_CAP = 1_500
DECISION_DEADLINE_S = 10.0
S_UNI_COMPUTE_BUDGET_S = 10.0
S_UNI_BUDGET_GUARD_S = 0.5
DECLARED_WORKERS = 4
PARALLEL_MINIMUM_ROWS = 128
ENERGY_BOUNDARY_SENTENCE = (
    "Pooled successfully decoded forward-downlink information bits per joule of "
    "modelled partial-payload DC energy, comprising user-link PA supply, the "
    "declared per-beam chain circuitry and a declared common processing "
    "increment, with explicitly stated idle states; spacecraft bus, unmodelled "
    "payload functions, feeder and inter-satellite links, and ground/terminal "
    "energy are outside this metric."
)
SET_LEVEL_ARMS = (
    "S0_DEPLOYABLE",
    *REPORTING_ONLY_ARMS,
    "FULL",
    "DROP_C1",
    "DROP_C2",
    "DROP_C3",
    "UNI",
    "S_UNI",
)
SWEEP_PRIMARY_CURVES = ("BASELINE", "ONLY_C1", "ONLY_C1C2", "FULL", "S_UNI")
SWEEP_COMPANION_CURVES = ("DROP_C1", "DROP_C2", "DROP_C3")
SWEEP_CURVES = SWEEP_PRIMARY_CURVES + SWEEP_COMPANION_CURVES
SWEEP_ARM_SOURCE = {
    "BASELINE": "NULL",
    **{arm: arm for arm in SWEEP_CURVES if arm != "BASELINE"},
}
SWEEP_PANEL_POINTS: dict[str, tuple[tuple[object, str], ...]] = {
    "A": ((25, "R7"), (50, "a-r0"), (100, "R1")),
    "B": ((0.1, "R4"), (0.338, "a-r0"), (1.0, "R3")),
    "E": (("a-r0", "a-r0"), ("a′-r0", "a′-r0"), ("a-γ0", "a-γ0"), ("b0", "b0")),
    "F": tuple((angle, "a-r0") for angle in (0.0, 0.5, 1.0, 1.5, 2.0)),
}
SWEEP_PANEL_METADATA = {
    "A": {"x_axis": "rate_target_mbit_s", "worlds_per_x": 4, "anchors_per_world": 90},
    "B": {"x_axis": "circuit_power_per_active_chain_w", "worlds_per_x": 4, "anchors_per_world": 90},
    "E": {"x_axis": "architecture", "worlds_per_x": 4, "anchors_per_world": 90},
    "F": {"x_axis": "off_axis_angle_deg", "worlds_per_x": 1, "anchors_per_world": 1},
}
SUCCESSOR_DEVELOPMENT_ROLES = frozenset(
    {
        "PROBE",
        "CALIBRATION",
        "REHEARSAL",
        "KAT",
        "SYNTHETIC_REAL",
        "SMOKE",
    }
)
SELECTION_DEPENDENCY_ALLOWLIST = (
    "immutable_world_tape",
    "opening_incumbent_assignments",
    "nominal_boundary_fields",
    "frozen_calibration",
    "sealed_run_setting",
    "physical_event_ledger",
)


def apply_deadline_fallback(
    selections: Mapping[str, Configuration],
    *,
    base: Configuration,
    missed: bool,
) -> dict[str, Configuration]:
    """Commit BASE for every deployable set arm after one whole-path miss."""

    result = dict(selections)
    if missed:
        for arm in SET_LEVEL_ARMS:
            result[arm] = base
    return result


def catalogue_definition() -> dict[str, object]:
    definition = {
        "version": "mcrl-v025-bounded-catalogue-v5-stage4h",
        "complete_cartesian_limit": COMPLETE_CATALOGUE_LIMIT,
        "unilateral": "top-8 live legal options per user by nominal single-link margin",
        "selection_boundary_indices": list(SELECTION_BOUNDARY_INDICES),
        "stage2_top_m": SELECTION_STAGE2_M,
        "declared_selection_workers": DECLARED_WORKERS,
        "s0": "top-two nominal proposals plus frozen beam evacuations",
        "pairwise": {
            "top_k_users_by_nominal_unilateral_surplus": PAIRWISE_TOP_K_USERS,
            "top_legal_options_per_user": TOP_PROPOSALS,
        },
        "evacuation": "every user on each active beam to best live legal alternative",
        "zero_legal_user": "explicit null action; excluded from Cartesian factor",
        "cap": CATALOGUE_CAP,
    }
    return {**definition, "sha256": digest_payload(definition)}


def _sweep_point(panel: str, x_value: object) -> tuple[object, str]:
    panel = panel.upper()
    if panel not in SWEEP_PANEL_POINTS:
        raise ProbeError("sweep panel must be A, B, E, or F")
    for declared_x, run_id in SWEEP_PANEL_POINTS[panel]:
        if x_value == declared_x and type(x_value) is type(declared_x):
            return declared_x, run_id
    raise ProbeError(f"x-value {x_value!r} is not sealed for sweep panel {panel}")


def sweep_receipt_identity(
    *,
    panel: str,
    x_value: object,
    run_id: str,
    world_domain: str,
    world_sha256: str,
    catalogue_sha256: str,
) -> dict[str, object]:
    """Bind the panel and x-value alongside the reused physical authorities."""

    panel = panel.upper()
    declared_x, declared_run = _sweep_point(panel, x_value)
    if run_id != declared_run:
        raise ProbeError("sweep x-value does not bind the requested run setting")
    for name, value in (
        ("world_sha256", world_sha256),
        ("catalogue_sha256", catalogue_sha256),
    ):
        if len(value) != 64 or not set(value) <= set("0123456789abcdef"):
            raise ProbeError(f"sweep identity has invalid {name}")
    body = {
        "schema": f"{SWEEP_SCHEMA}-point-identity",
        "panel": panel,
        "x_axis": SWEEP_PANEL_METADATA[panel]["x_axis"],
        "x_value": declared_x,
        "run_id": run_id,
        "world_domain": world_domain,
        "world_sha256": world_sha256,
        "catalogue_sha256": catalogue_sha256,
    }
    return {**body, "sha256": digest_payload(body)}


def sweep_plan(panel: str) -> dict[str, object]:
    """Return the sealed, simulator-inert execution plan for one CH5 panel."""

    panel = panel.upper()
    if panel not in SWEEP_PANEL_POINTS:
        raise ProbeError("sweep panel must be A, B, E, or F")
    metadata = SWEEP_PANEL_METADATA[panel]
    points = [
        {"x_value": x_value, "run_id": run_id}
        for x_value, run_id in SWEEP_PANEL_POINTS[panel]
    ]
    return {
        "schema": f"{SWEEP_SCHEMA}-plan",
        "status": "PLANNED_NOT_RUN",
        "panel": panel,
        **metadata,
        "points": points,
        "primary_curves": list(SWEEP_PRIMARY_CURVES),
        "companion_curves": list(SWEEP_COMPANION_CURVES),
        "curves": list(SWEEP_CURVES),
        "curve_count": len(SWEEP_CURVES),
        "curve_arm_source": dict(SWEEP_ARM_SOURCE),
        "shared_world_tape_within_x": True,
        "shared_catalogue_across_arms": True,
        "reporting_only_arms": list(REPORTING_ONLY_ARMS),
        "enters_certificate": False,
        "enters_admission": False,
    }


def project_sweep_costs(
    *,
    measured_anchor_wall_s: float,
    measured_provider_wall_s: float,
    process_concurrency: int = 20,
) -> dict[str, object]:
    """Project all sealed panels from one quarantined panel-A anchor."""

    if measured_anchor_wall_s <= 0.0 or measured_provider_wall_s < 0.0:
        raise ProbeError("measured sweep costs must be nonnegative, with a positive anchor")
    if type(process_concurrency) is not int or process_concurrency < DECLARED_WORKERS:
        raise ProbeError("process concurrency cannot run one declared four-worker unit")
    concurrent_units = process_concurrency // DECLARED_WORKERS
    panels = {}
    for panel, points in SWEEP_PANEL_POINTS.items():
        metadata = SWEEP_PANEL_METADATA[panel]
        worlds_per_x = int(metadata["worlds_per_x"])
        anchors_per_world = int(metadata["anchors_per_world"])
        units = len(points) * worlds_per_x
        anchors = units * anchors_per_world
        anchor_core_hours = (
            anchors * measured_anchor_wall_s * DECLARED_WORKERS / 3600.0
        )
        provider_builds = 0 if panel == "F" else worlds_per_x
        provider_core_hours = provider_builds * measured_provider_wall_s / 3600.0
        core_hours = anchor_core_hours + provider_core_hours
        waves = math.ceil(units / concurrent_units)
        panels[panel] = {
            "x_values": len(points),
            "formal_units": units,
            "anchors": anchors,
            "provider_builds_reused_across_x": provider_builds,
            "projected_core_hours": core_hours,
            "ideal_wall_minutes_at_concurrency": core_hours * 60.0 / process_concurrency,
            "whole_unit_wave_upper_minutes": (
                waves
                * (
                    measured_provider_wall_s
                    + anchors_per_world * measured_anchor_wall_s
                )
                / 60.0
            ),
        }
    return {
        "schema": f"{SWEEP_SCHEMA}-cost-projection",
        "measured_anchor_wall_s": measured_anchor_wall_s,
        "measured_provider_wall_s": measured_provider_wall_s,
        "declared_workers_per_unit": DECLARED_WORKERS,
        "process_concurrency": process_concurrency,
        "concurrent_units": concurrent_units,
        "panels": panels,
    }


def _selection_dependencies(
    *,
    tape: ExogenousWorldTape,
    incumbent: Configuration,
    setting: PhysicsSetting,
    calibration: CalibrationValues,
    run_setting: SealedRunSetting,
    step_index: int,
    carrier: str,
    cell_rekeyed_users: Iterable[int],
    previously_served_users: Iterable[int],
) -> dict[str, object]:
    """Materialize the complete allowlisted input surface before selection."""

    return {
        "immutable_world_tape": tape.digest,
        "opening_incumbent_assignments": incumbent.assignments,
        "nominal_boundary_fields": {
            "step_index": step_index,
            "carrier": carrier,
            "field": "nominal",
        },
        "frozen_calibration": calibration.digest,
        "sealed_run_setting": run_setting.digest,
        "physical_event_ledger": digest_payload(
            [
                event.__dict__
                for event in _physical_events(
                    incumbent,
                    incumbent,
                    cell_rekeyed_users=cell_rekeyed_users,
                    previously_served_users=previously_served_users,
                )
            ]
        ),
    }


def _assert_selection_dependencies(dependencies: Mapping[str, object]) -> str:
    """Reject an undeclared selection input before any candidate is scored."""

    if tuple(dependencies) != SELECTION_DEPENDENCY_ALLOWLIST:
        raise ProbeError("selection attempted to consume a hidden dependency")
    return digest_payload(dependencies)


def _prewarm_selection_quantiles(
    tape: ExogenousWorldTape,
    *,
    anchor_step: int,
    boundary_indices: tuple[int, ...],
    alpha: float | None,
) -> int:
    """Populate sealed quantile bins once before the forked workers inherit them."""

    if alpha is None:
        return 0
    elevations: set[float] = set()
    for step_index in range(anchor_step, anchor_step + 4):
        step = tape.steps[step_index]
        if step.arrays is not None:
            for boundary in boundary_indices if step_index > anchor_step else (0,):
                elevations.update(
                    float(value)
                    for value in step.arrays.elevations_deg[boundary].tolist()
                )
        else:
            for boundary in boundary_indices if step_index > anchor_step else (0,):
                elevations.update(
                    row.elevation_deg
                    for row in step.boundaries[boundary].candidates
                )
    bins = {
        math.floor(value / 0.5 + 0.5) * 0.5
        for value in elevations
    }
    for elevation_bin in sorted(bins):
        fading_product_quantile(elevation_bin, alpha)
    return len(bins)

# Server injection seam. The object is read sequentially and detached by
# build_world_tape; it is never cloned or retained in a receipt.
WORLD_PROVIDER_FACTORY: Callable[[], PrimitiveWorldProvider] = TinySyntheticProvider


class ProbeError(RuntimeError):
    pass


def _source_digest_for_factory(factory: Callable[[], object]) -> str:
    module = sys.modules.get(factory.__module__)
    path = None if module is None else getattr(module, "__file__", None)
    if path is None or not Path(path).is_file():
        return digest_payload({"module": factory.__module__, "name": factory.__qualname__})
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _code_authority_digest() -> str:
    digest = hashlib.sha256()
    for path in (Path(__file__), *sorted((REPO / "src/mcrl/physics_v025").glob("*.py"))):
        digest.update(path.relative_to(REPO).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def append_attempt(
    *,
    status: str,
    attempt_id: str,
    experiment: str,
    panel: str,
    cell: str,
    unit: str,
    authority: Mapping[str, object],
) -> str:
    """Append one fsynced hash-chained attempt record."""

    if status not in {"STARTED", "DONE", "ABANDONED"}:
        raise ProbeError("attempt status is invalid")
    import fcntl

    ATTEMPT_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    with ATTEMPT_REGISTRY.open("a+b") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.seek(0)
        lines = [line for line in handle.read().splitlines() if line]
        previous = None
        if lines:
            previous = json.loads(lines[-1])["record_sha256"]
        record = {
            "schema": f"{SCHEMA}-attempt-v1",
            "status": status,
            "attempt_id": attempt_id,
            "experiment": experiment,
            "panel": panel,
            "cell": cell,
            "unit": unit,
            "authority": dict(authority),
            "utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "previous_record_sha256": previous,
        }
        record["record_sha256"] = digest_payload(record)
        handle.seek(0, os.SEEK_END)
        handle.write(canonical_bytes(record) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return str(record["record_sha256"])


def _attempt_records() -> list[dict[str, object]]:
    if not ATTEMPT_REGISTRY.is_file():
        return []
    records = [json.loads(line) for line in ATTEMPT_REGISTRY.read_text(encoding="ascii").splitlines() if line]
    previous = None
    for record in records:
        declared = record.get("record_sha256")
        unsigned = dict(record)
        unsigned.pop("record_sha256", None)
        if unsigned.get("previous_record_sha256") != previous or declared != digest_payload(unsigned):
            raise ProbeError("attempt registry hash chain is invalid")
        previous = declared
    return records


@dataclass(frozen=True)
class Configuration:
    configuration_id: str
    assignments: tuple[tuple[int, tuple[int, int] | None], ...]
    changed_users: int
    kind: str

    @property
    def mapping(self) -> dict[int, tuple[int, int] | None]:
        return dict(self.assignments)


@dataclass(frozen=True)
class EvaluatedProfile:
    config: Configuration
    score: CellScore
    energy_components: Mapping[str, float]
    lit_beam_seconds: float
    lit_satellite_seconds: float
    acm_mode_counts: Mapping[str, int]
    se_plateau_user_steps: int
    user_step_observations: int
    rf_cap_hits: int
    rf_transmission_observations: int
    treatment_t_same_instant_comparison: Mapping[str, object] | None
    certificate_status: str = "CONVERGED"
    certificate_iterations: int = 0
    required_power_w_max: float = 0.0
    min_decoding_margin_db: float = -100.0
    mean_acm_se_bit_s_hz: float = 0.0
    m_target_counts: Mapping[str, int] = None  # type: ignore[assignment]
    m_tx_counts: Mapping[str, int] = None  # type: ignore[assignment]
    realised_decode_successes: int = 0
    realised_decode_failures: int = 0

    @property
    def bits(self) -> float:
        return math.fsum(self.score.bits.values())

    @property
    def joules(self) -> float:
        return self.score.joules

    def outcome(self, *, phi: Fraction = Fraction()) -> NetworkOutcome:
        opportunities = max(1, len(self.score.bits)) * DECISION_INTERVAL_S
        decoding = math.fsum(self.score.decoding_time_s.values()) / opportunities
        useful = math.fsum(self.score.useful_time_s.values()) / opportunities
        return NetworkOutcome.build(
            bits=sum((Fraction(str(value)) for value in self.score.bits.values()), Fraction()),
            joules=self.joules,
            phi=phi,
            decoding_availability=min(1.0, max(0.0, decoding)),
            useful_availability=min(1.0, max(0.0, useful)),
            per_user_bits=self.score.bits,
        )


@dataclass(frozen=True)
class SelectionProfile:
    """Minimal stage-1 result transferred from a worker to the coordinator."""

    config: Configuration
    bits: float
    joules: float
    served_count: int


@dataclass
class EvaluationCounter:
    boundary_evaluations: int = 0


_SELECTION_WORKER_CONTEXT: dict[str, object] | None = None


def _deterministic_shards(
    configs: Sequence[Configuration], workers: int
) -> tuple[tuple[Configuration, ...], ...]:
    """Round-robin configuration shards with a stable worker assignment."""

    if type(workers) is not int or workers < 1:
        raise ProbeError("selection worker count must be a positive integer")
    return tuple(tuple(configs[index::workers]) for index in range(workers))


def _selection_worker_stage1(
    task: tuple[int, tuple[Configuration, ...]],
) -> tuple[int, tuple[SelectionProfile, ...], tuple[str, ...], int]:
    """Evaluate one deterministic k=0 shard in a forked worker process."""

    if _SELECTION_WORKER_CONTEXT is None:
        raise ProbeError("selection worker context was not installed before fork")
    shard_index, configs = task
    context = _SELECTION_WORKER_CONTEXT
    evaluator = StepEvaluator(
        context["tape"],  # type: ignore[arg-type]
        context["setting"],  # type: ignore[arg-type]
        int(context["step_index"]),
        transition_from=context["incumbent"],  # type: ignore[arg-type]
        cell_rekeyed_users=context["cell_rekeys"],  # type: ignore[arg-type]
        previously_served_users=context["previously_served_users"],  # type: ignore[arg-type]
        field=(
            "nominal" if context["selection_alpha"] is None else "margin"
        ),
        fading_quantile_alpha=(
            None
            if context["selection_alpha"] is None
            else float(context["selection_alpha"])
        ),
        run_setting=context["run_setting"],  # type: ignore[arg-type]
        boundary_indices=(0,),
    )
    evaluator.evaluate_many(configs)
    profiles = tuple(
        SelectionProfile(
            config,
            evaluator._evaluated[config.configuration_id].bits,
            evaluator._evaluated[config.configuration_id].joules,
            sum(
                evaluator._evaluated[
                    config.configuration_id
                ].score.served_phy.values()
            ),
        )
        for config in configs
        if config.configuration_id in evaluator._evaluated
    )
    invalid = tuple(
        config.configuration_id
        for config in configs
        if config.configuration_id in evaluator._invalid
    )
    return shard_index, profiles, invalid, evaluator.physical_evaluations


def _selection_worker_catalogue_ranking(
    task: tuple[int, tuple[Configuration, ...]],
) -> tuple[int, tuple[SelectionProfile, ...], tuple[str, ...], int]:
    """Evaluate one shard of the catalogue's k=0 unilateral ranking rows.

    The evaluator is constructed with exactly the arguments the serial
    ``_catalogue_with_census`` ranking evaluator uses: the sealed ranking view
    (``field="margin"``, ``alpha=0.10``), the decision boundary only, and
    ``transition_from=base``.  Sharding is the same deterministic round robin
    used by stage 1, so the reduction is catalogue-order exact.
    """

    if _SELECTION_WORKER_CONTEXT is None:
        raise ProbeError("selection worker context was not installed before fork")
    shard_index, configs = task
    context = _SELECTION_WORKER_CONTEXT
    base = _base_configuration(
        context["tape"],  # type: ignore[arg-type]
        int(context["step_index"]),
        str(context["carrier"]),
    )
    evaluator = StepEvaluator(
        context["tape"],  # type: ignore[arg-type]
        context["ranking_setting"],  # type: ignore[arg-type]
        int(context["step_index"]),
        transition_from=base,
        field="margin",
        fading_quantile_alpha=CATALOGUE_RANKING_ALPHA,
        run_setting=context["run_setting"],  # type: ignore[arg-type]
        boundary_indices=(0,),
    )
    evaluator.evaluate_many(configs)
    profiles = tuple(
        SelectionProfile(
            config,
            evaluator._evaluated[config.configuration_id].bits,
            evaluator._evaluated[config.configuration_id].joules,
            sum(evaluator._evaluated[config.configuration_id].score.served_phy.values()),
        )
        for config in configs
        if config.configuration_id in evaluator._evaluated
    )
    invalid = tuple(
        config.configuration_id
        for config in configs
        if config.configuration_id in evaluator._invalid
    )
    return shard_index, profiles, invalid, evaluator.physical_evaluations


def _selection_worker_stage2(
    task: tuple[int, tuple[Configuration, ...], tuple[int, ...]],
) -> tuple[
    int,
    dict[str, tuple[OffsetProjection, ...]],
    tuple[dict[str, object], ...],
    int,
]:
    """Evaluate every offset for one shortlist shard in a worker process."""

    if _SELECTION_WORKER_CONTEXT is None:
        raise ProbeError("selection worker context was not installed before fork")
    shard_index, configs, boundary_indices = task
    context = _SELECTION_WORKER_CONTEXT
    counter = EvaluationCounter()
    forecasts, receipts = _batched_stage2_forecasts(
        tape=context["tape"],  # type: ignore[arg-type]
        setting=context["setting"],  # type: ignore[arg-type]
        anchor_step=int(context["step_index"]),
        carrier=str(context["carrier"]),
        configs=configs,
        counter=counter,
        calibration=context["calibration"],  # type: ignore[arg-type]
        run_setting=context["run_setting"],  # type: ignore[arg-type]
        boundary_indices=boundary_indices,
        fading_quantile_alpha=(
            None
            if context["selection_alpha"] is None
            else float(context["selection_alpha"])
        ),
    )
    return shard_index, forecasts, receipts, counter.boundary_evaluations


def _selection_worker_s_uni(
    compute_budget_s: float,
) -> tuple[Configuration, int, float, bool, str, EvaluatedProfile, int]:
    """Run the separately budgeted S_UNI comparator without parent NumPy use."""

    if _SELECTION_WORKER_CONTEXT is None:
        raise ProbeError("selection worker context was not installed before fork")
    context = _SELECTION_WORKER_CONTEXT
    counter = EvaluationCounter()
    base = _base_configuration(
        context["tape"],  # type: ignore[arg-type]
        int(context["step_index"]),
        str(context["carrier"]),
    )
    evaluator = StepEvaluator(
        context["tape"],  # type: ignore[arg-type]
        context["setting"],  # type: ignore[arg-type]
        int(context["step_index"]),
        transition_from=context["incumbent"],  # type: ignore[arg-type]
        cell_rekeyed_users=context["cell_rekeys"],  # type: ignore[arg-type]
        previously_served_users=context["previously_served_users"],  # type: ignore[arg-type]
        field=(
            "nominal" if context["selection_alpha"] is None else "margin"
        ),
        fading_quantile_alpha=(
            None
            if context["selection_alpha"] is None
            else float(context["selection_alpha"])
        ),
        counter=counter,
        run_setting=context["run_setting"],  # type: ignore[arg-type]
        boundary_indices=(0,),
    )
    selected, iterations, wall_s, missed, termination = _s_uni_select(
        base=base,
        incumbent=context["incumbent"],  # type: ignore[arg-type]
        tape=context["tape"],  # type: ignore[arg-type]
        step_index=int(context["step_index"]),
        evaluator=evaluator,
        calibration=context["calibration"],  # type: ignore[arg-type]
        compute_budget_s=compute_budget_s,
        run_setting=context["run_setting"],  # type: ignore[arg-type]
        cell_rekeyed_users=context["cell_rekeys"],  # type: ignore[arg-type]
    )
    committed = selected if not missed else base
    full_evaluator = StepEvaluator(
        context["tape"],  # type: ignore[arg-type]
        context["setting"],  # type: ignore[arg-type]
        int(context["step_index"]),
        transition_from=context["incumbent"],  # type: ignore[arg-type]
        cell_rekeyed_users=context["cell_rekeys"],  # type: ignore[arg-type]
        previously_served_users=context["previously_served_users"],  # type: ignore[arg-type]
        counter=counter,
        run_setting=context["run_setting"],  # type: ignore[arg-type]
    )
    return (
        selected,
        iterations,
        wall_s,
        missed,
        termination,
        full_evaluator.evaluate(committed),
        counter.boundary_evaluations,
    )


def _selection_worker_validate(
    task: tuple[
        tuple[Configuration, ...],
        Configuration,
        Configuration,
        Configuration,
    ],
) -> tuple[
    tuple[EvaluatedProfile, ...],
    object,
    tuple[EvaluatedProfile, ...],
    object,
    int,
]:
    """Validate committed profiles and both selected/base decompositions."""

    if _SELECTION_WORKER_CONTEXT is None:
        raise ProbeError("selection worker context was not installed before fork")
    selected, full, j1, u1 = task
    context = _SELECTION_WORKER_CONTEXT
    counter = EvaluationCounter()
    base = _base_configuration(
        context["tape"],  # type: ignore[arg-type]
        int(context["step_index"]),
        str(context["carrier"]),
    )
    evaluator = StepEvaluator(
        context["tape"],  # type: ignore[arg-type]
        context["setting"],  # type: ignore[arg-type]
        int(context["step_index"]),
        transition_from=context["incumbent"],  # type: ignore[arg-type]
        cell_rekeyed_users=context["cell_rekeys"],  # type: ignore[arg-type]
        previously_served_users=context["previously_served_users"],  # type: ignore[arg-type]
        counter=counter,
        run_setting=context["run_setting"],  # type: ignore[arg-type]
    )
    unique = tuple(
        {row.configuration_id: row for row in (*selected, j1, u1)}.values()
    )
    evaluator.evaluate_many(unique)
    if base.configuration_id not in evaluator._evaluated:
        raise ProbeError("BASE has an invalid committed-profile power certificate")
    decomposition, singletons = _committed_set_decomposition(
        base=base,
        selected=full,
        incumbent=context["incumbent"],  # type: ignore[arg-type]
        evaluator=evaluator,
        calibration=context["calibration"],  # type: ignore[arg-type]
        cell_rekeyed_users=context["cell_rekeys"],  # type: ignore[arg-type]
    )
    base_decomposition, _base_singletons = _committed_set_decomposition(
        base=base,
        selected=base,
        incumbent=context["incumbent"],  # type: ignore[arg-type]
        evaluator=evaluator,
        calibration=context["calibration"],  # type: ignore[arg-type]
        cell_rekeyed_users=context["cell_rekeys"],  # type: ignore[arg-type]
    )
    return (
        tuple(evaluator._evaluated.values()),
        decomposition,
        singletons,
        base_decomposition,
        counter.boundary_evaluations,
    )


def _validate_committed_serially(
    *,
    tape: ExogenousWorldTape,
    setting: PhysicsSetting,
    step_index: int,
    incumbent: Configuration,
    cell_rekeys: tuple[int, ...],
    previously_served: tuple[int, ...],
    run_setting: SealedRunSetting,
    calibration: CalibrationValues,
    base: Configuration,
    unique_selected: tuple[Configuration, ...],
    full: Configuration,
    j1: Configuration,
    u1: Configuration,
) -> tuple[
    tuple[EvaluatedProfile, ...],
    object,
    tuple[EvaluatedProfile, ...],
    object,
    int,
    StepEvaluator,
]:
    """Recompute the committed validation in this process.

    Used only to rebuild the receipt after a worker is lost to the host; the
    committed selection has already been fixed by the deadline at that point.
    The arithmetic is the same ``_selection_worker_validate`` performs.
    """

    counter = EvaluationCounter()
    evaluator = StepEvaluator(
        tape,
        setting,
        step_index,
        transition_from=incumbent,
        cell_rekeyed_users=cell_rekeys,
        previously_served_users=previously_served,
        counter=counter,
        run_setting=run_setting,
    )
    evaluator.evaluate_many(
        tuple({row.configuration_id: row for row in (*unique_selected, j1, u1)}.values())
    )
    if base.configuration_id not in evaluator._evaluated:
        raise ProbeError("BASE has an invalid committed-profile power certificate")
    decomposition, singletons = _committed_set_decomposition(
        base=base,
        selected=full,
        incumbent=incumbent,
        evaluator=evaluator,
        calibration=calibration,
        cell_rekeyed_users=cell_rekeys,
    )
    base_decomposition, _base_singletons = _committed_set_decomposition(
        base=base,
        selected=base,
        incumbent=incumbent,
        evaluator=evaluator,
        calibration=calibration,
        cell_rekeyed_users=cell_rekeys,
    )
    return (
        tuple(evaluator._evaluated.values()),
        decomposition,
        singletons,
        base_decomposition,
        counter.boundary_evaluations,
        evaluator,
    )


def _open_selection_pool(
    *,
    workers: int,
    tape: ExogenousWorldTape,
    setting: PhysicsSetting,
    step_index: int,
    carrier: str,
    incumbent: Configuration,
    cell_rekeys: tuple[int, ...],
    previously_served_users: tuple[int, ...],
    calibration: CalibrationValues,
    run_setting: SealedRunSetting,
    selection_alpha: float | None = 0.10,
    ranking_setting: PhysicsSetting | None = None,
) -> ProcessPoolExecutor | None:
    """Open the cold per-anchor process pool required by the F2 clock rule."""

    global _SELECTION_WORKER_CONTEXT
    if workers == 1:
        return None
    if "fork" not in mp.get_all_start_methods():
        raise ProbeError("declared process parallelism requires the POSIX fork start method")
    _SELECTION_WORKER_CONTEXT = {
        "tape": tape,
        "setting": setting,
        "step_index": step_index,
        "carrier": carrier,
        "incumbent": incumbent,
        "cell_rekeys": cell_rekeys,
        "previously_served_users": previously_served_users,
        "calibration": calibration,
        "run_setting": run_setting,
        "selection_alpha": selection_alpha,
        "ranking_setting": setting if ranking_setting is None else ranking_setting,
    }
    return ProcessPoolExecutor(
        max_workers=workers,
        mp_context=mp.get_context("fork"),
    )


def _profiles_from_evaluator(
    evaluator: StepEvaluator, configs: Sequence[Configuration]
) -> dict[str, SelectionProfile]:
    return {
        config.configuration_id: SelectionProfile(
            config,
            evaluator._evaluated[config.configuration_id].bits,
            evaluator._evaluated[config.configuration_id].joules,
            sum(evaluator._evaluated[config.configuration_id].score.served_phy.values()),
        )
        for config in configs
        if config.configuration_id in evaluator._evaluated
    }


def _ranking_profiles(
    *,
    pool: ProcessPoolExecutor | None,
    configs: Sequence[Configuration],
    workers: int,
    serial_evaluator: StepEvaluator,
    counter: EvaluationCounter | None,
) -> dict[str, SelectionProfile]:
    """Evaluate the catalogue's k=0 ranking rows, in workers when worthwhile.

    Shards are the same deterministic round robin stage 1 uses and the
    reduction is in ``configs`` order, so the serial and parallel results are
    exactly equal.
    """

    if pool is None or workers < 2 or len(configs) < PARALLEL_MINIMUM_ROWS:
        serial_evaluator.evaluate_many(configs)
        return _profiles_from_evaluator(serial_evaluator, configs)
    shards = _deterministic_shards(configs, workers)
    results = list(
        pool.map(
            _selection_worker_catalogue_ranking,
            tuple(enumerate(shards)),
            chunksize=1,
        )
    )
    merged: dict[str, SelectionProfile] = {}
    for _index, rows, invalid_ids, evaluations in sorted(results):
        merged.update((row.config.configuration_id, row) for row in rows)
        serial_evaluator._invalid.update(invalid_ids)
        if counter is not None:
            counter.boundary_evaluations += evaluations
    return {
        row.configuration_id: merged[row.configuration_id]
        for row in configs
        if row.configuration_id in merged
    }


def _parallel_stage1_profiles(
    *,
    pool: ProcessPoolExecutor | None,
    configs: Sequence[Configuration],
    workers: int,
    serial_evaluator: StepEvaluator,
    counter: EvaluationCounter,
    seed_profiles: Mapping[str, SelectionProfile] | None = None,
) -> tuple[dict[str, SelectionProfile], set[str], tuple[dict[str, object], ...]]:
    """Evaluate and reduce k=0 shards in catalogue order.

    ``seed_profiles`` carries rows already scored on this anchor's identical
    k=0 view (the catalogue's unilateral ranking).  Because the a-r0 batch
    kernel is a pure function of the step arrays, the selected candidate rows,
    the field, the quantile alpha, the boundary indices and the run setting,
    reusing them is bit-for-bit equal to re-evaluating them.
    """

    seeded = dict(seed_profiles or {})
    residual = tuple(row for row in configs if row.configuration_id not in seeded)
    shards = _deterministic_shards(residual, workers)
    shard_receipt = tuple(
        {
            "worker_index": index,
            "configuration_ids": [row.configuration_id for row in shard],
        }
        for index, shard in enumerate(shards)
    )
    if pool is None:
        serial_evaluator.evaluate_many(residual)
        profiles = {**seeded, **_profiles_from_evaluator(serial_evaluator, residual)}
        invalid = set(serial_evaluator._invalid)
    else:
        results = list(
            pool.map(
                _selection_worker_stage1,
                tuple(enumerate(shards)),
                chunksize=1,
            )
        )
        profiles = dict(seeded)
        invalid = set()
        for _index, rows, invalid_ids, evaluations in sorted(results):
            profiles.update((row.config.configuration_id, row) for row in rows)
            invalid.update(invalid_ids)
            counter.boundary_evaluations += evaluations
    ordered = {
        row.configuration_id: profiles[row.configuration_id]
        for row in configs
        if row.configuration_id in profiles
    }
    return ordered, invalid, shard_receipt


def _parallel_stage2_forecasts(
    *,
    pool: ProcessPoolExecutor | None,
    tape: ExogenousWorldTape,
    setting: PhysicsSetting,
    anchor_step: int,
    carrier: str,
    configs: Sequence[Configuration],
    counter: EvaluationCounter,
    calibration: CalibrationValues,
    run_setting: SealedRunSetting,
    workers: int,
    boundary_indices: tuple[int, ...],
    fading_quantile_alpha: float | None = 0.10,
) -> tuple[
    dict[str, tuple[OffsetProjection, ...]],
    tuple[dict[str, object], ...],
    tuple[dict[str, object], ...],
]:
    """Evaluate stage 2 by stable shards and reduce by catalogue then offset."""

    shards = _deterministic_shards(configs, workers)
    shard_receipt = tuple(
        {
            "worker_index": index,
            "configuration_ids": [row.configuration_id for row in shard],
        }
        for index, shard in enumerate(shards)
    )
    if pool is None:
        forecasts, receipts = _batched_stage2_forecasts(
            tape=tape,
            setting=setting,
            anchor_step=anchor_step,
            carrier=carrier,
            configs=configs,
            counter=counter,
            calibration=calibration,
            run_setting=run_setting,
            boundary_indices=boundary_indices,
            fading_quantile_alpha=fading_quantile_alpha,
        )
        return forecasts, receipts, shard_receipt
    results = list(
        pool.map(
            _selection_worker_stage2,
            tuple(
                (index, shard, boundary_indices)
                for index, shard in enumerate(shards)
            ),
            chunksize=1,
        )
    )
    unordered_forecasts: dict[str, tuple[OffsetProjection, ...]] = {}
    unordered_receipts: dict[tuple[str, int], dict[str, object]] = {}
    for _index, forecasts, receipts, evaluations in sorted(results):
        unordered_forecasts.update(forecasts)
        unordered_receipts.update(
            ((str(row["configuration_id"]), int(row["offset"])), row)
            for row in receipts
        )
        counter.boundary_evaluations += evaluations
    ordered_forecasts = {
        row.configuration_id: unordered_forecasts[row.configuration_id]
        for row in configs
    }
    ordered_receipts = tuple(
        unordered_receipts[(row.configuration_id, offset)]
        for offset in (1, 2, 3)
        for row in configs
    )
    return ordered_forecasts, ordered_receipts, shard_receipt


def _setting(label: str) -> PhysicsSetting:
    matches = [setting for setting in MATRIX_SETTINGS if setting.label == label]
    if len(matches) != 1:
        raise ProbeError(f"cell must be one of the {len(MATRIX_SETTINGS)} declared labels: {label!r}")
    return matches[0]


def _provider_for_run(run_setting: SealedRunSetting) -> PrimitiveWorldProvider:
    if run_setting.user_count == 100:
        return WORLD_PROVIDER_FACTORY()
    try:
        return WORLD_PROVIDER_FACTORY(user_count=run_setting.user_count)  # type: ignore[call-arg]
    except TypeError as error:
        raise ProbeError("R2 requires a provider factory with a user_count parameter") from error


def _world_domain(index: int, *, calibration: bool = False) -> str:
    domains = CALIBRATION_WORLD_DOMAINS if calibration else PROBE_WORLD_DOMAINS
    if index < 1 or index > len(domains):
        raise ProbeError("world index is outside the declared domain inventory")
    return domains[index - 1]


def _base_configuration(tape: ExogenousWorldTape, step_index: int, carrier: str) -> Configuration:
    action = next(
        row for row in tape.carriers if row.step_index == step_index and row.carrier == carrier
    )
    mapping = dict(action.assignments)
    step = tape.steps[step_index]
    if step.arrays is not None:
        arrays = step.arrays
        live = arrays.visible[0] & arrays.d2_eligible[0] & arrays.cell_reachable[0]
        users_with_legal = {
            int(arrays.users[int(arrays.row_user_column[row])])
            for row in np.flatnonzero(live).tolist()
        }
    else:
        users_with_legal = {
            row.user_id for row in step.boundaries[0].candidates if row.legal
        }
    # The opening reference is part of the selection contract: a user with
    # no live legal action is NULL in BASE and in every derived catalogue row.
    for user in mapping:
        if user not in users_with_legal:
            mapping[user] = None
    return Configuration(
        f"BASE:{carrier}", tuple(sorted(mapping.items())), 0, "reference"
    )


def _previously_served_users(
    tape: ExogenousWorldTape, step_index: int, carrier: str
) -> tuple[int, ...]:
    """Users served at any earlier decision instant on this immutable tape."""

    return tuple(
        user.user_id
        for user in tape.user_layout
        if any(
            _base_configuration(tape, earlier, carrier).mapping[user.user_id]
            is not None
            for earlier in range(step_index)
        )
    )


def _candidate_shortlist(boundary) -> set[tuple[int, tuple[int, int]]]:
    """Coarse provider shortlist, before successor visibility/D2 masks."""

    return {
        (row.user_id, row.identity)
        for row in boundary.candidates
        if row.coarse_shortlisted
    }


def _rekeyed_users(tape: ExogenousWorldTape, step_index: int) -> tuple[int, ...]:
    step = tape.steps[step_index]
    return () if step.arrays is not None else step.boundaries[0].cell_rekeyed_users


def _legal_options(
    tape: ExogenousWorldTape, step_index: int
) -> tuple[dict[int, tuple[tuple[int, int], ...]], dict[str, int]]:
    """Return decision-instant legal options without materialising array rows."""

    step = tape.steps[step_index]
    users = tuple(sorted(user.user_id for user in tape.user_layout))
    if step.arrays is not None:
        arrays = step.arrays
        live = arrays.visible[0] & arrays.d2_eligible[0] & arrays.cell_reachable[0]
        options: dict[int, list[tuple[float, tuple[int, int]]]] = {user: [] for user in users}
        for row in np.flatnonzero(live).tolist():
            user = int(arrays.users[int(arrays.row_user_column[row])])
            identity = tuple(int(value) for value in arrays.identities[row])
            options[user].append((float(arrays.slants_km[0, row]), identity))
        resolved = {
            user: tuple(identity for _slant, identity in sorted(set(rows)))
            for user, rows in options.items()
        }
        legal_count = int(np.count_nonzero(live))
        return resolved, {
            "coarse_shortlist_count": int(len(arrays.identities)),
            "full_successor_legal_count": legal_count,
            "candidate_shortlist_miss_count": 0,
        }
    first = step.boundaries[0]
    full_legal = {(row.user_id, row.identity) for row in first.candidates if row.legal}
    resolved = {
        user: tuple(
            row.identity
            for row in sorted(
                (
                    row
                    for row in first.candidates
                    if row.user_id == user
                    and row.legal
                ),
                key=lambda row: (row.slant_km, row.identity),
            )
        )
        for user in users
    }
    return resolved, {
        "coarse_shortlist_count": len(_candidate_shortlist(first)),
        "full_successor_legal_count": len(full_legal),
        "candidate_shortlist_miss_count": len(
            full_legal - _candidate_shortlist(first)
        ),
    }


def _selection_shortlist(
    tape: ExogenousWorldTape,
    step_index: int,
    *,
    run_setting: SealedRunSetting,
) -> tuple[dict[int, tuple[tuple[int, int], ...]], dict[str, object]]:
    """Top eight live actions by decision-instant nominal link margin."""

    options, census = _legal_options(tape, step_index)
    step = tape.steps[step_index]
    ranked: dict[int, tuple[tuple[int, int], ...]] = {}
    excluded_margins: list[float] = []
    if step.arrays is not None:
        arrays = step.arrays
        row_of = arrays._row_index()
        noise = noise_power_w(500_000_000.0)
        for user, identities in options.items():
            rows = []
            for identity in identities:
                row = row_of[(user, identity)]
                sinr = BEAM_RF_CAP_W * float(arrays.nominal_gain[0, row]) / noise
                margin = 10.0 * math.log10(max(sinr, np.finfo(float).tiny)) - SINR_MIN_DB
                rows.append((margin, identity))
            ordered = sorted(rows, key=lambda item: (-item[0], item[1]))
            ranked[user] = tuple(identity for _margin, identity in ordered[:SHORTLIST_OPTIONS_PER_USER])
            excluded_margins.extend(margin for margin, _identity in ordered[SHORTLIST_OPTIONS_PER_USER:])
    else:
        first = step.boundaries[0]
        by_key = {(row.user_id, row.identity): row for row in first.candidates}
        noise = noise_power_w(500_000_000.0)
        for user, identities in options.items():
            rows = []
            for identity in identities:
                candidate = by_key[(user, identity)]
                sinr = BEAM_RF_CAP_W * candidate.nominal_gain / noise
                margin = 10.0 * math.log10(max(sinr, np.finfo(float).tiny)) - SINR_MIN_DB
                rows.append((margin, identity))
            ordered = sorted(rows, key=lambda item: (-item[0], item[1]))
            ranked[user] = tuple(identity for _margin, identity in ordered[:SHORTLIST_OPTIONS_PER_USER])
            excluded_margins.extend(margin for margin, _identity in ordered[SHORTLIST_OPTIONS_PER_USER:])
    kept = sum(len(rows) for rows in ranked.values())
    total = sum(len(rows) for rows in options.values())
    return ranked, {
        **census,
        "selection_shortlist_per_user": SHORTLIST_OPTIONS_PER_USER,
        "selection_shortlist_count": kept,
        "legal_options_outside_selection_shortlist": total - kept,
        "best_excluded_nominal_margin_db": (
            None if not excluded_margins else max(excluded_margins)
        ),
        "shortlist_superset_miss_count": census["candidate_shortlist_miss_count"],
    }


def _configuration(
    base: Configuration,
    mapping: Mapping[int, tuple[int, int] | None],
    *,
    kind: str,
) -> Configuration:
    assignments = tuple(sorted(mapping.items()))
    base_map = base.mapping
    changed = sum(base_map[user] != identity for user, identity in assignments)
    encoded = ";".join(
        f"{user}:NULL" if identity is None else f"{user}:{identity[0]}:{identity[1]}"
        for user, identity in assignments
    )
    return Configuration(f"CFG:{encoded}", assignments, changed, kind)


def _catalogue_with_census(
    tape: ExogenousWorldTape,
    step_index: int,
    base: Configuration,
    *,
    setting: PhysicsSetting | None = None,
    calibration: CalibrationValues | None = None,
    counter: EvaluationCounter | None = None,
    run_setting: SealedRunSetting | None = None,
    ranking_pool: ProcessPoolExecutor | None = None,
    ranking_workers: int = 1,
    ranking_sink: dict[str, SelectionProfile] | None = None,
    ranking_invalid_sink: set[str] | None = None,
) -> tuple[tuple[Configuration, ...], dict[str, object]]:
    users = tuple(sorted(user.user_id for user in tape.user_layout))
    active_run = run_setting_for("a-r0") if run_setting is None else run_setting
    all_options, raw_census = _legal_options(tape, step_index)
    product_size = math.prod(
        len(all_options[user]) if all_options[user] else 1 for user in users
    )
    if product_size <= COMPLETE_CATALOGUE_LIMIT:
        options, census = all_options, raw_census
    else:
        options, census = _selection_shortlist(
            tape, step_index, run_setting=active_run
        )
    factors = tuple(options[user] if options[user] else (None,) for user in users)
    rows: list[Configuration] = [base]
    base_map = base.mapping
    if product_size <= COMPLETE_CATALOGUE_LIMIT:
        for product in itertools.product(*factors):
            mapping = dict(zip(users, product, strict=True))
            if mapping == base_map:
                continue
            rows.append(_configuration(base, mapping, kind="complete-cartesian"))
        mode = "complete-cartesian"
    else:
        # (i) every legal unilateral move; an option-less user keeps the
        # explicit null action and never collapses the other users' catalogue.
        unilaterals: dict[int, list[Configuration]] = {user: [] for user in users}
        for user in users:
            for identity in options[user]:
                if identity == base_map[user]:
                    continue
                mapping = dict(base_map)
                mapping[user] = identity
                row = _configuration(base, mapping, kind="unilateral")
                rows.append(row)
                unilaterals[user].append(row)

        # Rank users by the best exact nonlinear nominal single-user surplus
        # at the decision instant.  The one-boundary result is held over the
        # step only for this causal selection-time ranking.
        rank_setting = _setting("a-r0") if setting is None else setting
        nominal = StepEvaluator(
            tape,
            rank_setting,
            step_index,
            transition_from=base,
            field="margin",
            fading_quantile_alpha=CATALOGUE_RANKING_ALPHA,
            counter=counter,
            run_setting=active_run,
            boundary_indices=(0,),
        )
        rank_rows = [base] + [row for values in unilaterals.values() for row in values]
        # The ranking rows are the k=0 view the coordinator already has to
        # score; evaluate them once, in the same four declared workers, and
        # publish them so stage 1 does not repeat the identical batch call.
        ranking_profiles = _ranking_profiles(
            pool=ranking_pool,
            configs=rank_rows,
            workers=ranking_workers,
            serial_evaluator=nominal,
            counter=counter,
        )
        rank_profile_of = {
            row.configuration_id: ranking_profiles[row.configuration_id]
            for row in rank_rows
            if row.configuration_id in ranking_profiles
        }
        if ranking_sink is not None:
            ranking_sink.update(rank_profile_of)
        if ranking_invalid_sink is not None:
            ranking_invalid_sink.update(nominal._invalid)

        def _rank_bits_joules(row: Configuration) -> tuple[float, float]:
            hit = rank_profile_of.get(row.configuration_id)
            if hit is not None:
                return hit.bits, hit.joules
            # Preserves the sealed behaviour for a row the batch path rejected:
            # the scalar evaluator raises on an invalid power certificate.
            profile = nominal.evaluate(row)
            return profile.bits, profile.joules

        base_bits, base_joules = _rank_bits_joules(base)
        eta = Fraction() if calibration is None else calibration.eta_ref
        kappa = Fraction(1) if calibration is None else calibration.kappa_bits_per_user_step
        best_surplus = {}
        for user in users:
            values = []
            for row in unilaterals[user]:
                bits, joules = _rank_bits_joules(row)
                core = Fraction(str(bits - base_bits)) - eta * Fraction(
                    str(joules - base_joules)
                )
                core += kappa * _phi_for(base, row)
                values.append(core)
            best_surplus[user] = max(values, default=Fraction(-10**30))
        ranked_users = sorted(
            users,
            key=lambda user: (-best_surplus[user], user),
        )[:PAIRWISE_TOP_K_USERS]

        # (ii) S0 top-two proposals assembled as complete deployable profiles.
        for proposal_rank in range(TOP_PROPOSALS):
            mapping = dict(base_map)
            for user in users:
                if len(unilaterals[user]) > proposal_rank:
                    mapping[user] = unilaterals[user][proposal_rank].mapping[user]
            if mapping != base_map:
                rows.append(_configuration(base, mapping, kind="s0-top-two"))

        # (iii) pairwise moves among top K, over each user's top two options.
        for first, second in itertools.combinations(ranked_users, 2):
            for first_row in unilaterals[first][:TOP_PROPOSALS]:
                for second_row in unilaterals[second][:TOP_PROPOSALS]:
                    mapping = dict(base_map)
                    mapping[first] = first_row.mapping[first]
                    mapping[second] = second_row.mapping[second]
                    rows.append(_configuration(base, mapping, kind="pairwise-top10-top2"))

        # (iv) one evacuation set per active beam, every incumbent user moved
        # to its best live legal alternative (or explicit null if none).
        for beam in sorted({identity for identity in base_map.values() if identity is not None}):
            mapping = dict(base_map)
            affected = [user for user in users if base_map[user] == beam]
            for user in affected:
                mapping[user] = next(
                    (identity for identity in options[user] if identity != beam),
                    None,
                )
            if mapping != base_map:
                rows.append(_configuration(base, mapping, kind="beam-evacuation"))
        mode = "bounded-union-v2"

    unique = {row.assignments: row for row in rows}
    ordered = (base,) + tuple(
        sorted(
            (row for assignments, row in unique.items() if assignments != base.assignments),
            key=lambda row: row.configuration_id,
        )
    )
    if mode != "complete-cartesian" and len(ordered) > CATALOGUE_CAP:
        raise ProbeError(f"bounded catalogue exceeded sealed cap {CATALOGUE_CAP}")
    return ordered, {
        **census,
        "complete_cartesian_size": product_size,
        "catalogue_mode": mode,
        "null_action_users": sum(not options[user] for user in users),
        "bounded_catalogue_count": len(ordered),
        "top10_users_by_exact_nominal_unilateral_surplus": ranked_users if mode != "complete-cartesian" else [],
    }


def _catalogue(tape: ExogenousWorldTape, step_index: int, base: Configuration) -> tuple[Configuration, ...]:
    return _catalogue_with_census(tape, step_index, base)[0]


def _energy_fields(
    shared,
    setting: PhysicsSetting,
    *,
    circuit_power_per_active_chain_w: float = 0.338,
) -> tuple[dict[str, float], float, float]:
    idle = SENSITIVITY_IDLE_POWER_W if setting.standby == "f" else PRIMARY_IDLE_POWER_W
    boundary = []
    for item in shared.integrated:
        receipt = schedule_energy(
            shared.inventory,
            ((slot.fraction, dict(slot.beam_rf_w)) for slot in item.radiation.slots),
            duration_s=1.0,
            idle_power_w=idle,
            circuit_power_per_active_chain_w=circuit_power_per_active_chain_w,
        )
        beams = {beam for slot in item.radiation.slots for beam, rf in slot.beam_rf_w if rf > 0.0}
        satellites = {beam[0] for beam in beams}
        boundary.append((receipt, float(len(beams)), float(len(satellites))))
    fields = ("pa_j", "circuit_j", "standby_j", "baseband_j", "bus_j")
    if setting.integration == "T":
        receipt, beams, satellites = boundary[0]
        return (
            {name: getattr(receipt, name) * DECISION_INTERVAL_S for name in fields},
            beams * DECISION_INTERVAL_S,
            satellites * DECISION_INTERVAL_S,
        )
    components = {name: 0.0 for name in fields}
    beam_seconds = satellite_seconds = 0.0
    for left, right in zip(boundary, boundary[1:]):
        for name in fields:
            components[name] += 0.5 * (getattr(left[0], name) + getattr(right[0], name)) * 0.640
        beam_seconds += 0.5 * (left[1] + right[1]) * 0.640
        satellite_seconds += 0.5 * (left[2] + right[2]) * 0.640
    return components, beam_seconds, satellite_seconds


def _physical_events(
    before: Configuration,
    after: Configuration,
    *,
    cell_rekeyed_users: Iterable[int] = (),
    previously_served_users: Iterable[int] = (),
):
    """Build the one authoritative ledger from physical assignment identities."""

    before_map = before.mapping
    rekeyed = frozenset(cell_rekeyed_users)
    previously_served = frozenset(previously_served_users)
    return tuple(
        classify_physical_transition(
            user_id=user,
            before=before_map[user],
            after=identity,
            cell_rekey=user in rekeyed,
            was_previously_served=(
                before_map[user] is not None or user in previously_served
            ),
        )
        for user, identity in after.assignments
    )


def _interruption_events(
    before: Configuration,
    after: Configuration,
    decision_time_s: float,
    *,
    cell_rekeyed_users: Iterable[int] = (),
    previously_served_users: Iterable[int] = (),
) -> tuple[InterruptionEvent, ...]:
    """Translate that ledger to H/SH useful-time removals at the decision instant."""

    mapping = {
        "beam_change": "same_satellite_beam_change",
        "satellite_change": "satellite_change",
        "cell_rekey": "same_satellite_beam_change",
        "initial_entry": "initial_entry",
        "reentry": "reentry",
    }
    return tuple(
        InterruptionEvent(event.user_id, decision_time_s, mapping[event.kind])
        for event in _physical_events(
            before,
            after,
            cell_rekeyed_users=cell_rekeyed_users,
            previously_served_users=previously_served_users,
        )
        if event.kind in mapping
    )


class StepEvaluator:
    """Architecture/configuration cache; treatment cells only rescore it."""

    def __init__(
        self,
        tape: ExogenousWorldTape,
        setting: PhysicsSetting,
        step_index: int,
        *,
        transition_from: Configuration,
        cell_rekeyed_users: Iterable[int] = (),
        previously_served_users: Iterable[int] = (),
        field: str = "realised",
        counter: EvaluationCounter | None = None,
        run_setting: SealedRunSetting | None = None,
        boundary_indices: tuple[int, ...] = tuple(range(48)),
        fading_quantile_alpha: float | None = 0.10,
    ) -> None:
        self.tape = tape
        self.setting = setting
        self.step_index = step_index
        self.transition_from = transition_from
        self.cell_rekeyed_users = tuple(cell_rekeyed_users)
        self.previously_served_users = tuple(previously_served_users)
        self.field = field
        self.counter = counter
        self.run_setting = run_setting_for(setting.label) if run_setting is None else run_setting
        self.boundary_indices = boundary_indices
        self.fading_quantile_alpha = fading_quantile_alpha
        self._shared: dict[str, object] = {}
        self._evaluated: dict[str, EvaluatedProfile] = {}
        self._invalid: set[str] = set()
        self.physical_evaluations = 0

    def evaluate_many(self, configs: Sequence[Configuration]) -> None:
        """Populate the cache through the dense real-world ``a-r0`` path."""

        missing = [row for row in configs if row.configuration_id not in self._evaluated]
        step = self.tape.steps[self.step_index]
        if not missing or step.arrays is None or self.setting.label != "a-r0":
            for config in missing:
                self.evaluate(config)
            return
        arrays = step.arrays
        row_of = arrays._row_index()
        users = tuple(int(value) for value in arrays.users)
        selected = np.full((len(missing), len(users)), -1, dtype=np.int64)
        absent = np.zeros(len(missing), dtype=np.bool_)
        for config_index, config in enumerate(missing):
            mapping = config.mapping
            for user_column, user in enumerate(users):
                identity = mapping[user]
                if identity is not None:
                    row = row_of.get((user, identity))
                    if row is None:
                        absent[config_index] = True
                    else:
                        selected[config_index, user_column] = row
        result = evaluate_ar_tdm_catalogue(
            arrays,
            selected,
            field=self.field,
            rate_target_bps=self.run_setting.rate_target_bps,
            circuit_power_per_active_chain_w=self.run_setting.circuit_power_per_active_chain_w,
            boundary_indices=self.boundary_indices,
            fading_quantile_alpha=self.fading_quantile_alpha,
        )
        mode_names = ("NO_MODE",) + tuple(row.name for row in ACM_MODES)
        for index, config in enumerate(missing):
            if absent[index] or not bool(result.valid[index]):
                self._invalid.add(config.configuration_id)
                continue
            per_user_bits = {
                user: float(result.bits[index, column])
                for column, user in enumerate(users)
            }
            decoding = {
                user: float(result.decoding_time_s[index, column])
                for column, user in enumerate(users)
            }
            served = {user: decoding[user] > 0.0 for user in users}
            feasible = {
                user: bool(result.feasible[index, column])
                for column, user in enumerate(users)
            }
            attained = {
                user: bool(result.attained[index, column])
                for column, user in enumerate(users)
            }
            score = CellScore(
                self.setting,
                per_user_bits,
                float(result.joules[index]),
                decoding,
                dict(decoding),
                served,
                attained,
                feasible,
                None,
                self.run_setting.rate_target_bps,
                True,
                float(result.residual_w[index]),
            )
            components = {
                "pa_j": float(result.pa_j[index]),
                "circuit_j": float(result.circuit_j[index]),
                "standby_j": 0.0,
                "baseband_j": float(result.baseband_j[index]),
                "bus_j": 0.0,
            }
            counts = {
                name: int(result.mode_counts[index, column])
                for column, name in enumerate(mode_names)
                if result.mode_counts[index, column]
            }
            target_counts = {
                name: int(result.target_mode_counts[index, column])
                for column, name in enumerate(mode_names)
                if result.target_mode_counts[index, column]
            }
            transmitted_counts = {
                name: int(result.transmitted_mode_counts[index, column])
                for column, name in enumerate(mode_names)
                if result.transmitted_mode_counts[index, column]
            }
            profile = EvaluatedProfile(
                config,
                score,
                components,
                (
                    0.0
                    if self.run_setting.circuit_power_per_active_chain_w == 0.0
                    else components["circuit_j"] / self.run_setting.circuit_power_per_active_chain_w
                ),
                components["baseband_j"] / 0.200,
                counts,
                int(result.plateau_users[index]),
                len(users),
                int(result.cap_hits[index]),
                int(result.transmissions[index]),
                None,
                {0: "INVALID", 1: "CONVERGED", 2: "CONVERGED_SLOW"}[
                    int(result.certificate_status[index])
                ],
                int(result.certificate_iterations[index]),
                float(result.max_rf_power_w[index]),
                float(result.min_decoding_margin_db[index]),
                float(result.mean_acm_se_bit_s_hz[index]),
                target_counts,
                transmitted_counts,
                int(result.realised_decode_successes[index]),
                int(result.realised_decode_failures[index]),
            )
            self._evaluated[config.configuration_id] = profile
        evaluations = len(missing) * len(self.boundary_indices)
        self.physical_evaluations += evaluations
        if self.counter is not None:
            self.counter.boundary_evaluations += evaluations

    def evaluate(self, config: Configuration) -> EvaluatedProfile:
        if config.configuration_id in self._evaluated:
            return self._evaluated[config.configuration_id]
        geometry = self.tape.geometry_for(step_index=self.step_index, assignments=config.mapping)
        shared = build_shared_tape(
            self.setting.architecture,
            geometry,
            self.tape.inventory,
            field=self.field,  # type: ignore[arg-type]
            roster=tuple(user.user_id for user in self.tape.user_layout),
            config=RadiationConfig(
                rate_target_bps=self.run_setting.rate_target_bps,
                fading_quantile_alpha=self.fading_quantile_alpha,
            ),
            circuit_power_per_active_chain_w=self.run_setting.circuit_power_per_active_chain_w,
        )
        event_ledger = _interruption_events(
            self.transition_from,
            config,
            shared.integrated[0].time_s,
            cell_rekeyed_users=self.cell_rekeyed_users,
            previously_served_users=self.previously_served_users,
        )
        score = score_setting(
            shared,
            self.setting,
            discontinuities=discontinuities_from_event_ledger(
                shared, event_ledger
            ),
            interruptions=event_ledger,
        )
        if not score.valid:
            raise ProbeError(f"invalid power certificate for {config.configuration_id}")
        components, beam_seconds, satellite_seconds = _energy_fields(
            shared,
            self.setting,
            circuit_power_per_active_chain_w=self.run_setting.circuit_power_per_active_chain_w,
        )
        if not math.isclose(math.fsum(components.values()), score.joules, rel_tol=1e-10, abs_tol=1e-8):
            raise ProbeError("energy-component reconstruction disagrees with cell score")
        mode_counts: dict[str, int] = {}
        target_counts: dict[str, int] = {}
        transmitted_counts: dict[str, int] = {}
        decode_successes = decode_failures = 0
        cap_hits = transmissions = 0
        top_mode = max(ACM_MODES, key=lambda row: row.efficiency_bit_per_symbol)
        user_on_plateau: dict[int, bool] = {}
        for boundary in shared.integrated:
            for slot in boundary.radiation.slots:
                for tx in slot.transmissions:
                    mode = tx.m_tx if tx.realised_outcome and tx.realised_outcome.decoded else None
                    name = "NO_MODE" if mode is None else mode.name
                    mode_counts[name] = mode_counts.get(name, 0) + 1
                    target_name = "NO_MODE" if tx.m_target is None else tx.m_target.name
                    target_counts[target_name] = target_counts.get(target_name, 0) + 1
                    tx_name = "NO_MODE" if tx.m_tx is None else tx.m_tx.name
                    transmitted_counts[tx_name] = transmitted_counts.get(tx_name, 0) + 1
                    decoded = bool(tx.realised_outcome and tx.realised_outcome.decoded)
                    decode_successes += int(decoded)
                    decode_failures += int(not decoded)
                    user_on_plateau[tx.user_id] = user_on_plateau.get(tx.user_id, True) and tx.m_tx == top_mode
                    transmissions += 1
                    cap_hits += int(math.isclose(tx.rf_power_w, BEAM_RF_CAP_W, rel_tol=0.0, abs_tol=1e-9))
        t_comparison = None
        if self.setting.integration == "T":
            integral_setting = next(
                row
                for row in MATRIX_SETTINGS
                if row.architecture == self.setting.architecture and row.treatment == "0"
            )
            integral_score = score_setting(
                shared,
                integral_setting,
                discontinuities=discontinuities_from_event_ledger(
                    shared, event_ledger
                ),
                interruptions=event_ledger,
            )
            t_comparison = {
                "snapshot_convention": "left-endpoint decision-time zero-order hold",
                "same_instant_integral": {
                    "bits": math.fsum(integral_score.bits.values()),
                    "joules": integral_score.joules,
                },
                "left_snapshot": {"bits": math.fsum(score.bits.values()), "joules": score.joules},
            }
        result = EvaluatedProfile(
            config,
            score,
            components,
            beam_seconds,
            satellite_seconds,
            mode_counts,
            sum(user_on_plateau.values()),
            len(user_on_plateau),
            cap_hits,
            transmissions,
            t_comparison,
            max(
                (
                    boundary.radiation.certificate.status
                    for boundary in shared.integrated
                ),
                key=lambda value: {"FIXED": 0, "CONVERGED": 1, "CONVERGED_SLOW": 2, "INVALID": 3}[value],
            ),
            sum(boundary.radiation.certificate.iterations for boundary in shared.integrated),
            max(
                (
                    tx.rf_power_w
                    for boundary in shared.integrated
                    for slot in boundary.radiation.slots
                    for tx in slot.transmissions
                ),
                default=0.0,
            ),
            min(
                (
                    (
                        -100.0
                        if tx.m_tx is None
                        else 10.0 * math.log10(tx.sinr)
                        - tx.m_tx.threshold_db
                    )
                    for boundary in shared.integrated
                    for slot in boundary.radiation.slots
                    for tx in slot.transmissions
                ),
                default=-100.0,
            ),
            math.fsum(
                (
                    tx.realised_outcome.credited_spectral_efficiency_bit_per_s_hz
                    if self.setting.rate == "ACM"
                    and tx.realised_outcome is not None
                    else rate_model(self.setting.rate).rate_bps(
                        tx.sinr, tx.bandwidth_hz
                    )
                    / tx.bandwidth_hz
                )
                for boundary in shared.integrated
                for slot in boundary.radiation.slots
                for tx in slot.transmissions
            ) / max(
                1,
                sum(
                    1
                    for boundary in shared.integrated
                    for slot in boundary.radiation.slots
                    for _tx in slot.transmissions
                ),
            ),
            target_counts,
            transmitted_counts,
            decode_successes,
            decode_failures,
        )
        self._shared[config.configuration_id] = shared
        self._evaluated[config.configuration_id] = result
        self.physical_evaluations += len(shared.integrated)
        if self.counter is not None:
            self.counter.boundary_evaluations += len(shared.integrated)
        return result

    def required_power(self, config: Configuration) -> tuple[float, float]:
        profile = self.evaluate(config)
        if config.configuration_id not in self._shared:
            return profile.required_power_w_max, BEAM_RF_CAP_W
        shared = self._shared[config.configuration_id]
        powers = [
            tx.rf_power_w
            for boundary in shared.integrated  # type: ignore[attr-defined]
            for slot in boundary.radiation.slots
            for tx in slot.transmissions
        ]
        return (max(powers, default=0.0), BEAM_RF_CAP_W)


def _nominal_configuration(
    config: Configuration, profile: EvaluatedProfile | SelectionProfile
) -> NominalConfiguration:
    return NominalConfiguration(
        config.configuration_id,
        config.assignments,
        profile.bits,
        profile.joules,
        (
            profile.served_count
            if isinstance(profile, SelectionProfile)
            else sum(profile.score.served_phy.values())
        ),
    )


def _calibrate(
    setting: PhysicsSetting,
    run_setting: SealedRunSetting | None = None,
    prepared_tapes: Mapping[str, ExogenousWorldTape] | None = None,
) -> CalibrationValues:
    run_setting = run_setting_for(setting.label) if run_setting is None else run_setting
    observations = []
    for index, domain in enumerate(CALIBRATION_WORLD_DOMAINS, start=1):
        if prepared_tapes is None:
            tape = build_world_tape(
                domain=domain,
                provider=_provider_for_run(run_setting),
                steps=30,
                start_time_s=0.0,
            )
        else:
            try:
                tape = prepared_tapes[domain]
            except KeyError:
                raise ProbeError(
                    f"prepared calibration tapes omit {domain}"
                ) from None
            if tape.domain != domain or len(tape.steps) != 30:
                raise ProbeError("prepared calibration tape identity/length drifted")
        bits = joules = 0.0
        selection_ids = []
        for step_index in range(30):
            base = _base_configuration(tape, step_index, "nearest-eligible")
            catalog, _census = _catalogue_with_census(
                tape,
                step_index,
                base,
                setting=setting,
                run_setting=run_setting,
            )
            nominal_evaluator = StepEvaluator(
                tape,
                setting,
                step_index,
                transition_from=base,
                cell_rekeyed_users=_rekeyed_users(tape, step_index),
                field="nominal",
                fading_quantile_alpha=None,
                run_setting=run_setting,
                # The reference selector is a decision-instant rule.  Only
                # the chosen configuration receives the complete 48-boundary
                # realised rollout below.
                boundary_indices=(0,),
            )
            nominal_evaluator.evaluate_many(catalog)
            nominal_profiles = {
                config.configuration_id: nominal_evaluator.evaluate(config)
                for config in catalog
                if config.configuration_id not in nominal_evaluator._invalid
            }
            chosen_nominal = nominal_greedy_reference(
                _nominal_configuration(config, nominal_profiles[config.configuration_id])
                for config in catalog
                if config.configuration_id in nominal_profiles
            )
            chosen = next(
                config
                for config in catalog
                if config.configuration_id == chosen_nominal.configuration_id
            )
            evaluated = StepEvaluator(
                tape,
                setting,
                step_index,
                transition_from=base,
                cell_rekeyed_users=_rekeyed_users(tape, step_index),
                run_setting=run_setting,
                fading_quantile_alpha=None,
            ).evaluate(chosen)
            bits += evaluated.bits
            joules += evaluated.joules
            selection_ids.append(chosen.configuration_id)
        observations.append(
            CalibrationObservation.build(
                world_domain=domain,
                bits=bits,
                joules=joules,
                users=len(tape.user_layout),
                time_s=30 * DECISION_INTERVAL_S,
                selected_configuration_id=digest_payload(selection_ids),
                decision_steps=30,
            )
        )
    frozen = freeze_setting_calibration(setting=setting, observations=observations)
    return replace(
        frozen,
        setting_label=run_setting.run_id,
        setting_digest=run_setting.digest,
    )


def _objective(
    profile: EvaluatedProfile | SelectionProfile,
    calibration: CalibrationValues,
) -> Fraction:
    if isinstance(profile, SelectionProfile):
        return Fraction(str(profile.bits)) - calibration.eta_ref * Fraction(
            str(profile.joules)
        )
    return network_objective(
        profile.outcome(),
        lambda_bits_per_j=calibration.lambda_bits_per_j,
        eta_ref=calibration.eta_ref,
        kappa_bits_per_user_step=calibration.kappa_bits_per_user_step,
    )


def _best(
    rows: Iterable[EvaluatedProfile], calibration: CalibrationValues
) -> EvaluatedProfile:
    return min(rows, key=lambda row: (-_objective(row, calibration), row.config.configuration_id))


def _phi_for(
    base: Configuration,
    candidate: Configuration,
    *,
    cell_rekeyed_users: Iterable[int] = (),
) -> Fraction:
    return phi_qos(
        _physical_events(
            base, candidate, cell_rekeyed_users=cell_rekeyed_users
        )
    )


def _forecast_rows(
    *,
    tape: ExogenousWorldTape,
    setting: PhysicsSetting,
    anchor_step: int,
    config: Configuration,
    carrier: str,
    counter: EvaluationCounter,
    focal_user: int,
    run_setting: SealedRunSetting | None = None,
) -> tuple[OffsetProjection, ...]:
    rows = []
    for offset in range(1, 4):
        projected_step = anchor_step + offset
        base = _base_configuration(tape, projected_step, carrier)
        # Persist physical identities; Geometry is rebuilt at the projected boundary.
        persisted = Configuration(config.configuration_id, config.assignments, config.changed_users, config.kind)
        evaluator = StepEvaluator(
            tape,
            setting,
            projected_step,
            transition_from=base,
            cell_rekeyed_users=_rekeyed_users(tape, projected_step),
            field="margin",
            fading_quantile_alpha=0.10,
            counter=counter,
            run_setting=run_setting,
        )
        try:
            result = evaluator.evaluate(persisted)
            valid = True
        except (MCRLContractError, ProbeError):
            result = None
            valid = False
        required, cap = 0.0, BEAM_RF_CAP_W
        margins = []
        ses = []
        if valid and result is not None:
            required, cap = evaluator.required_power(result.config)
            shared = evaluator._shared[result.config.configuration_id]
            model = rate_model(setting.rate)
            for boundary in shared.integrated:  # type: ignore[attr-defined]
                for slot in boundary.radiation.slots:
                    for tx in slot.transmissions:
                        margins.append(
                            -100.0
                            if tx.m_tx is None
                            else 10.0 * math.log10(tx.sinr) - tx.m_tx.threshold_db
                        )
                        ses.append(
                            tx.realised_outcome.credited_spectral_efficiency_bit_per_s_hz
                            if setting.rate == "ACM" and tx.realised_outcome is not None
                            else model.rate_bps(tx.sinr, tx.bandwidth_hz)
                            / tx.bandwidth_hz
                        )
            survives = bool(result.score.served_phy.get(focal_user, False))
            outcome = result.outcome()
        else:
            survives = False
            outcome = NetworkOutcome.build(
                bits=0,
                joules=0,
                phi=0,
                decoding_availability=0,
                useful_availability=0,
            )
        rows.append(
            OffsetProjection(
                offset,
                valid,
                survives,
                outcome,
                True,
                required if setting.architecture in {"a-r", "a′-r"} else None,
                cap if setting.architecture in {"a-r", "a′-r"} else None,
                min(margins, default=-math.inf) if margins else -100.0,
                math.fsum(ses) / len(ses) if ses else 0.0,
            )
        )
    return tuple(rows)


def _factor_scores(
    *,
    tape: ExogenousWorldTape,
    setting: PhysicsSetting,
    step_index: int,
    carrier: str,
    base: Configuration,
    incumbent: Configuration,
    catalog: Sequence[Configuration],
    evaluated: Mapping[str, EvaluatedProfile],
    calibration: CalibrationValues,
    counter: EvaluationCounter,
) -> tuple[
    dict[str, dict[tuple[int, tuple[int, int] | None], Fraction]],
    Fraction,
    int,
]:
    base_profile = evaluated[base.configuration_id]
    result = {name: {} for name in ("C1", "C2", "C3")}
    for config in catalog:
        if config.changed_users != 1:
            continue
        user = next(
            user for user, identity in config.assignments if dict(base.assignments)[user] != identity
        )
        identity = dict(config.assignments)[user]
        c1 = c1_difference_surplus(
            evaluated[config.configuration_id].outcome(
                phi=_phi_for(
                    incumbent,
                    config,
                    cell_rekeyed_users=_rekeyed_users(tape, step_index),
                )
            ),
            base_profile.outcome(
                phi=_phi_for(
                    incumbent,
                    base,
                    cell_rekeyed_users=_rekeyed_users(tape, step_index),
                )
            ),
            lambda_bits_per_j=calibration.lambda_bits_per_j,
            eta_ref=calibration.eta_ref,
            kappa_bits_per_user_step=calibration.kappa_bits_per_user_step,
        )
        result["C1"][(user, identity)] = c1.normalized_total
        candidate_forecast = _forecast_rows(
            tape=tape,
            setting=setting,
            anchor_step=step_index,
            config=config,
            carrier=carrier,
            counter=counter,
            focal_user=user,
        )
        default_forecast = _forecast_rows(
            tape=tape,
            setting=setting,
            anchor_step=step_index,
            config=base,
            carrier=carrier,
            counter=counter,
            focal_user=user,
        )
        c2 = c2_persistence_forecast(
            candidate_forecast,
            default_forecast,
            lambda_bits_per_j=calibration.lambda_bits_per_j,
            eta_ref=calibration.eta_ref,
            kappa_bits_per_user_step=calibration.kappa_bits_per_user_step,
        )
        result["C2"][(user, identity)] = c2.normalized_total
    users = tuple(user for user, _ in base.assignments)
    interaction_sum = Fraction()
    interaction_count = 0
    for user0, user1 in itertools.combinations(users, 2):
        uni0 = [row for row in catalog if row.changed_users == 1 and dict(row.assignments)[user0] != dict(base.assignments)[user0]]
        uni1 = [row for row in catalog if row.changed_users == 1 and dict(row.assignments)[user1] != dict(base.assignments)[user1]]
        for first in uni0:
            for second in uni1:
                merged_map = dict(base.assignments)
                merged_map[user0] = dict(first.assignments)[user0]
                merged_map[user1] = dict(second.assignments)[user1]
                joint = next((row for row in catalog if row.mapping == merged_map), None)
                if joint is None:
                    continue
                interaction = c3_lcsrs_interaction(
                    coalition_users=(user0, user1),
                    f00=base_profile.outcome(),
                    f10=evaluated[first.configuration_id].outcome(),
                    f01=evaluated[second.configuration_id].outcome(),
                    f11=evaluated[joint.configuration_id].outcome(),
                    lambda_bits_per_j=calibration.lambda_bits_per_j,
                    eta_ref=calibration.eta_ref,
                    kappa_bits_per_user_step=calibration.kappa_bits_per_user_step,
                )
                interaction_sum += interaction.psi
                interaction_count += 1
                for user, z3 in interaction.z3_by_user:
                    identity = merged_map[user]
                    old = result["C3"].get((user, identity))
                    normalized = z3 / calibration.kappa_bits_per_user_step
                    if old is None or normalized > old:
                        result["C3"][(user, identity)] = normalized
    return result, interaction_sum, interaction_count


def _configuration_factor_scores(
    *,
    tape: ExogenousWorldTape,
    setting: PhysicsSetting,
    step_index: int,
    carrier: str,
    base: Configuration,
    incumbent: Configuration,
    catalog: Sequence[Configuration],
    evaluator: StepEvaluator,
    calibration: CalibrationValues,
    counter: EvaluationCounter,
    c2_horizon_offsets: int = 3,
    run_setting: SealedRunSetting | None = None,
) -> tuple[dict[str, dict[str, object]], Fraction, int]:
    """Score every complete configuration by the sealed v1.5 decomposition."""

    base_profile = evaluator.evaluate(base)
    base_map = base.mapping
    singleton_c2: dict[tuple[int, tuple[int, int] | None], Fraction] = {}
    default_forecasts: dict[int, tuple[OffsetProjection, ...]] = {}
    result: dict[str, dict[str, object]] = {}
    interaction_sum = Fraction()
    interaction_count = 0
    for config in catalog:
        selected_map = config.mapping
        changed = tuple(
            user for user in sorted(base_map) if selected_map[user] != base_map[user]
        )
        required_subsets = {frozenset(), frozenset(changed)} | {
            frozenset((user,)) for user in changed
        }
        reporting_subsets = (
            {
                frozenset(subset)
                for size in range(len(changed) + 1)
                for subset in itertools.combinations(changed, size)
            }
            if 1 < len(changed) <= 4
            else required_subsets
        )
        outcomes: dict[frozenset[int], NetworkOutcome] = {}
        for subset in reporting_subsets:
            mapping = dict(base_map)
            for user in subset:
                mapping[user] = selected_map[user]
            subset_config = _configuration(base, mapping, kind="v15-sparse-set")
            outcomes[subset] = evaluator.evaluate(subset_config).outcome()
        candidate_phi = _phi_for(
            incumbent,
            config,
            cell_rekeyed_users=_rekeyed_users(tape, step_index),
        )
        base_phi = _phi_for(
            incumbent,
            base,
            cell_rekeyed_users=_rekeyed_users(tape, step_index),
        )
        decomposition = set_score_decomposition(
            coalition_users=changed,
            outcomes_by_subset=outcomes,
            lambda_bits_per_j=calibration.lambda_bits_per_j,
            eta_ref=calibration.eta_ref,
            kappa_bits_per_user_step=calibration.kappa_bits_per_user_step,
            phi_difference=candidate_phi - base_phi,
        )
        c2 = Fraction()
        for user in changed:
            key = (user, selected_map[user])
            if key not in singleton_c2:
                singleton_map = dict(base_map)
                singleton_map[user] = selected_map[user]
                singleton_config = _configuration(base, singleton_map, kind="v15-singleton")
                if user not in default_forecasts:
                    default_forecasts[user] = _forecast_rows(
                        tape=tape,
                        setting=setting,
                        anchor_step=step_index,
                        config=base,
                        carrier=carrier,
                        counter=counter,
                        focal_user=user,
                        run_setting=run_setting,
                    )
                projection = c2_persistence_forecast(
                    _forecast_rows(
                        tape=tape,
                        setting=setting,
                        anchor_step=step_index,
                        config=singleton_config,
                        carrier=carrier,
                        counter=counter,
                        focal_user=user,
                        run_setting=run_setting,
                    ),
                    default_forecasts[user],
                    lambda_bits_per_j=calibration.lambda_bits_per_j,
                    eta_ref=calibration.eta_ref,
                    kappa_bits_per_user_step=calibration.kappa_bits_per_user_step,
                    horizon_offsets=c2_horizon_offsets,
                )
                singleton_c2[key] = projection.normalized_total
            c2 += singleton_c2[key]
        result[config.configuration_id] = {
            "C1": decomposition.factor_c1,
            "C2": c2,
            "C3": decomposition.c3,
            "d_by_user": decomposition.d_by_user,
            "psi_A": decomposition.interaction_bits,
            "shapley_interaction_by_user": decomposition.shapley_interaction_by_user,
            "credit_split": decomposition.credit_split,
            "joint_change_bits": decomposition.joint_change_bits,
            "c1_physical_core": decomposition.c1,
            "phi_difference": decomposition.phi_difference,
        }
        if changed:
            interaction_sum += decomposition.interaction_bits
        if len(changed) > 1:
            interaction_count += 1
    return result, interaction_sum, interaction_count


def _set_score_select(
    *,
    catalog: Sequence[Configuration],
    factors: Mapping[str, Mapping[str, object]],
    include: Sequence[str],
) -> Configuration:
    """Select by the arm's immediate key, with C2 only as a tie-break."""

    include_set = frozenset(include)
    arm = {
        frozenset(("C1", "C2", "C3")): "FULL",
        frozenset(("C2", "C3")): "DROP_C1",
        frozenset(("C1", "C3")): "DROP_C2",
        frozenset(("C1", "C2")): "DROP_C3",
    }.get(include_set)
    if arm is None:
        # UNI and legacy KAT-only callers still use their declared components,
        # but continuation remains a secondary key whenever it is present.
        primary_names = tuple(name for name in include if name != "C2")
        use_c2 = "C2" in include
    else:
        primary_names = ARM_PRIMARY_COMPONENTS[arm]
        use_c2 = ARM_C2_TIEBREAK[arm]
    return _rank_for_arm(
        catalog=catalog,
        factors=factors,
        primary_names=primary_names,
        use_c2=use_c2,
    )[0]


def _relative_tie(left: Fraction, right: Fraction) -> bool:
    scale = max(Fraction(1), abs(left), abs(right))
    return abs(left - right) <= SELECTION_TIE_RELATIVE_TOLERANCE * scale


def _rank_for_arm(
    *,
    catalog: Sequence[Configuration],
    factors: Mapping[str, Mapping[str, object]],
    primary_names: Sequence[str],
    use_c2: bool,
) -> tuple[Configuration, ...]:
    values = {
        row.configuration_id: (
            sum(
                (
                    Fraction(factors[row.configuration_id][name])
                    for name in primary_names
                ),
                Fraction(),
            ),
            Fraction(factors[row.configuration_id]["C2"]),
        )
        for row in catalog
    }

    def compare(left: Configuration, right: Configuration) -> int:
        left_primary, left_c2 = values[left.configuration_id]
        right_primary, right_c2 = values[right.configuration_id]
        if not _relative_tie(left_primary, right_primary):
            return -1 if left_primary > right_primary else 1
        if use_c2 and not _relative_tie(left_c2, right_c2):
            return -1 if left_c2 > right_c2 else 1
        return (left.configuration_id > right.configuration_id) - (
            left.configuration_id < right.configuration_id
        )

    return tuple(sorted(catalog, key=cmp_to_key(compare)))


def _select_for_arm(
    arm: str,
    *,
    catalog: Sequence[Configuration],
    factors: Mapping[str, Mapping[str, object]],
) -> Configuration:
    """Select with exactly the primary and secondary keys owned by ``arm``."""

    if arm not in ARM_PRIMARY_COMPONENTS:
        raise ProbeError(f"unknown oracle arm: {arm}")
    return _rank_for_arm(
        catalog=catalog,
        factors=factors,
        primary_names=ARM_PRIMARY_COMPONENTS[arm],
        use_c2=ARM_C2_TIEBREAK[arm],
    )[0]


def _selection_factor_scores(
    *,
    base: Configuration,
    incumbent: Configuration,
    catalog: Sequence[Configuration],
    evaluated: Mapping[str, EvaluatedProfile | SelectionProfile],
    calibration: CalibrationValues,
    cell_rekeyed_users: Iterable[int] = (),
) -> dict[str, dict[str, object]]:
    """Configuration-local C1/C3 on the sealed coarse selection grid.

    C3 is never reduced to a per-(user, action) maximum.  Each row owns its
    own joint residual, so evacuation and proposal rows are scored as atomic
    coalitions.  Shapley credits are attached when the complete coalition
    game is evaluated for the committed row.
    """

    base_profile = evaluated[base.configuration_id]
    base_map = base.mapping
    base_core = Fraction(str(base_profile.bits)) - calibration.eta_ref * Fraction(
        str(base_profile.joules)
    )
    result: dict[str, dict[str, object]] = {}
    for config in catalog:
        changed = tuple(
            user
            for user in sorted(base_map)
            if config.mapping[user] != base_map[user]
        )
        d_rows = []
        for user in changed:
            mapping = dict(base_map)
            mapping[user] = config.mapping[user]
            singleton = _configuration(base, mapping, kind="selection-singleton")
            profile = evaluated[singleton.configuration_id]
            value = Fraction(str(profile.bits)) - calibration.eta_ref * Fraction(
                str(profile.joules)
            )
            d_rows.append((user, value - base_core))
        profile = evaluated[config.configuration_id]
        joint = (
            Fraction(str(profile.bits))
            - calibration.eta_ref * Fraction(str(profile.joules))
            - base_core
        )
        additive = sum((value for _user, value in d_rows), Fraction())
        psi = joint - additive
        phi = _phi_for(
            incumbent, config, cell_rekeyed_users=cell_rekeyed_users
        ) - _phi_for(
            incumbent, base, cell_rekeyed_users=cell_rekeyed_users
        )
        result[config.configuration_id] = {
            "C1": additive / calibration.kappa_bits_per_user_step + phi,
            "C2": Fraction(),
            "C3": psi / calibration.kappa_bits_per_user_step,
            "d_by_user": tuple(d_rows),
            "psi_A": psi,
            "shapley_interaction_by_user": (),
            "joint_change_bits": joint,
            "c1_physical_core": additive / calibration.kappa_bits_per_user_step,
            "phi_difference": phi,
        }
    return result


def _projection_from_profile(
    *,
    offset: int,
    profile: EvaluatedProfile | None,
    survives: bool,
) -> OffsetProjection:
    if profile is not None:
        opportunities = max(1, len(profile.score.bits)) * DECISION_INTERVAL_S
        compact_outcome = NetworkOutcome.build(
            bits=sum(
                (Fraction(str(value)) for value in profile.score.bits.values()),
                Fraction(),
            ),
            joules=profile.joules,
            phi=0,
            decoding_availability=min(
                1.0,
                max(
                    0.0,
                    math.fsum(profile.score.decoding_time_s.values())
                    / opportunities,
                ),
            ),
            useful_availability=min(
                1.0,
                max(
                    0.0,
                    math.fsum(profile.score.useful_time_s.values())
                    / opportunities,
                ),
            ),
        )
    else:
        compact_outcome = NetworkOutcome.build(
            bits=0,
            joules=0,
            phi=0,
            decoding_availability=0,
            useful_availability=0,
        )
    return OffsetProjection(
        offset,
        profile is not None,
        survives,
        compact_outcome,
        True,
        None if profile is None else profile.required_power_w_max,
        None if profile is None else BEAM_RF_CAP_W,
        -100.0 if profile is None else profile.min_decoding_margin_db,
        0.0 if profile is None else profile.mean_acm_se_bit_s_hz,
    )


def _batched_stage2_forecasts(
    *,
    tape: ExogenousWorldTape,
    setting: PhysicsSetting,
    anchor_step: int,
    carrier: str,
    configs: Sequence[Configuration],
    counter: EvaluationCounter,
    calibration: CalibrationValues,
    run_setting: SealedRunSetting,
    boundary_indices: tuple[int, ...] = SELECTION_BOUNDARY_INDICES,
    fading_quantile_alpha: float | None = 0.10,
) -> tuple[
    dict[str, tuple[OffsetProjection, ...]],
    tuple[dict[str, object], ...],
]:
    """Evaluate configuration × offset × coarse-boundary forecasts in batches."""

    by_config: dict[str, list[OffsetProjection]] = {
        row.configuration_id: [] for row in configs
    }
    receipts: list[dict[str, object]] = []
    for offset in (1, 2, 3):
        projected_step = anchor_step + offset
        transition = _base_configuration(tape, projected_step, carrier)
        evaluator = StepEvaluator(
            tape,
            setting,
            projected_step,
            transition_from=transition,
            field=(
                "nominal" if fading_quantile_alpha is None else "margin"
            ),
            counter=counter,
            run_setting=run_setting,
            boundary_indices=boundary_indices,
            fading_quantile_alpha=fading_quantile_alpha,
        )
        evaluator.evaluate_many(configs)
        for config in configs:
            profile = evaluator._evaluated.get(config.configuration_id)
            changed = tuple(
                user
                for user in config.mapping
                if config.mapping[user] != transition.mapping.get(user)
            )
            survives = profile is not None and all(
                profile.score.served_phy.get(user, False) for user in changed
            )
            projection = _projection_from_profile(
                offset=offset, profile=profile, survives=survives
            )
            by_config[config.configuration_id].append(projection)
            receipts.append(
                {
                    "schema": f"{SCHEMA}-forecast-margin-row-v1",
                    "configuration_id": config.configuration_id,
                    "offset": offset,
                    "valid": projection.valid,
                    "survives": projection.survives,
                    "required_power_w": projection.required_power_w,
                    "power_cap_w": projection.power_cap_w,
                    "required_power_cap_margin_w": projection.required_power_cap_margin_w,
                    "min_decoding_margin_db": projection.min_decoding_margin_db,
                    "mean_acm_se_bit_s_hz": projection.mean_acm_se_bit_s_hz,
                }
            )
    validated: dict[str, tuple[OffsetProjection, ...]] = {}
    for config in configs:
        rows = tuple(by_config[config.configuration_id])
        if all(row.valid for row in rows):
            def replay_projection(
                index: int,
                _time_s: float,
                assignments: Mapping[int, tuple[int, int] | None],
                recompute_background: bool,
                *,
                expected_assignments: Mapping[int, tuple[int, int] | None] = config.mapping,
                projections: tuple[OffsetProjection, ...] = rows,
            ) -> OffsetProjection:
                if assignments != expected_assignments or not recompute_background:
                    raise ProbeError("forecast projection replay contract drifted")
                return projections[index - 1]

            rows = project_three_offsets(
                assignments=config.mapping,
                evaluator=replay_projection,
                architecture=setting.architecture,
                lambda_bits_per_j=calibration.lambda_bits_per_j,
                eta_ref=calibration.eta_ref,
                kappa_bits_per_user_step=calibration.kappa_bits_per_user_step,
            )
        validated[config.configuration_id] = rows
    return validated, tuple(receipts)


def _attach_stage2_c2(
    *,
    factors: dict[str, dict[str, object]],
    forecasts: Mapping[str, tuple[OffsetProjection, ...]],
    base: Configuration,
    calibration: CalibrationValues,
    horizon_offsets: int,
) -> None:
    baseline = forecasts[base.configuration_id]
    for configuration_id, rows in forecasts.items():
        label = c2_persistence_forecast(
            rows,
            baseline,
            lambda_bits_per_j=calibration.lambda_bits_per_j,
            eta_ref=calibration.eta_ref,
            kappa_bits_per_user_step=calibration.kappa_bits_per_user_step,
            horizon_offsets=horizon_offsets,
        )
        factors[configuration_id]["C2"] = label.normalized_total
        factors[configuration_id]["c2_lost_offsets"] = label.lost_offsets


def _c2_tie_diagnostic(
    *,
    catalog: Sequence[Configuration],
    factors: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    rows: dict[str, object] = {}
    for arm, components in ARM_PRIMARY_COMPONENTS.items():
        primary = {
            row.configuration_id: sum(
                (
                    Fraction(factors[row.configuration_id][name])
                    for name in components
                ),
                Fraction(),
            )
            for row in catalog
        }
        maximum = max(primary.values())
        tied = sorted(
            configuration_id
            for configuration_id, value in primary.items()
            if _relative_tie(value, maximum)
        )
        rows[arm] = {
            "primary_components": list(components),
            "tie_count": len(tied),
            "tie_present": len(tied) > 1,
            "tied_configuration_ids": tied,
            "secondary": "C2" if ARM_C2_TIEBREAK[arm] else "configuration_id",
        }
    return rows


def _c2_forecast_validity_certificate(
    *,
    tape: ExogenousWorldTape,
    setting: PhysicsSetting,
    anchor_step: int,
    carrier: str,
    immediate: Configuration,
    continuation: Configuration,
    forecasts: Mapping[str, tuple[OffsetProjection, ...]],
    calibration: CalibrationValues,
    run_setting: SealedRunSetting,
) -> dict[str, object]:
    """Separate coarse integration and realised-fading forecast errors."""

    rows = []
    for offset in (1, 2, 3):
        projected_step = anchor_step + offset
        transition = _base_configuration(tape, projected_step, carrier)
        margin = StepEvaluator(
            tape,
            setting,
            projected_step,
            transition_from=transition,
            field="margin",
            run_setting=run_setting,
            boundary_indices=tuple(range(48)),
            fading_quantile_alpha=0.10,
        )
        realised = StepEvaluator(
            tape,
            setting,
            projected_step,
            transition_from=transition,
            field="realised",
            run_setting=run_setting,
            boundary_indices=tuple(range(48)),
            fading_quantile_alpha=0.10,
        )
        pair = (immediate, continuation)
        margin.evaluate_many(pair)
        realised.evaluate_many(pair)
        valid = all(
            config.configuration_id in margin._evaluated
            and config.configuration_id in realised._evaluated
            and config.configuration_id in forecasts
            for config in pair
        )
        if not valid:
            rows.append({"offset": offset, "valid": False})
            continue
        coarse_delta = float(
            network_objective(
                forecasts[continuation.configuration_id][offset - 1].outcome,
                lambda_bits_per_j=calibration.lambda_bits_per_j,
                eta_ref=calibration.eta_ref,
                kappa_bits_per_user_step=calibration.kappa_bits_per_user_step,
            )
            - network_objective(
                forecasts[immediate.configuration_id][offset - 1].outcome,
                lambda_bits_per_j=calibration.lambda_bits_per_j,
                eta_ref=calibration.eta_ref,
                kappa_bits_per_user_step=calibration.kappa_bits_per_user_step,
            )
        )
        margin_delta = float(
            _objective(margin.evaluate(continuation), calibration)
            - _objective(margin.evaluate(immediate), calibration)
        )
        realised_delta = float(
            _objective(realised.evaluate(continuation), calibration)
            - _objective(realised.evaluate(immediate), calibration)
        )
        rows.append(
            {
                "offset": offset,
                "valid": True,
                "predicted_margin_coarse_delta_bits": coarse_delta,
                "margin_48_boundary_delta_bits": margin_delta,
                "realised_48_boundary_delta_bits": realised_delta,
                "integration_error_bits": margin_delta - coarse_delta,
                "fading_error_bits": realised_delta - margin_delta,
                "total_forecast_error_bits": realised_delta - coarse_delta,
                "sign_agrees": (
                    coarse_delta == 0.0
                    or realised_delta == 0.0
                    or math.copysign(1.0, coarse_delta)
                    == math.copysign(1.0, realised_delta)
                ),
            }
        )
    return {
        "comparison": "DROP_C2 immediate deterministic choice vs FULL C2 tie-break choice",
        "rows": rows,
        "valid": all(row["valid"] and row.get("sign_agrees", True) for row in rows),
        "integration_and_fading_errors_separated": True,
    }


def _committed_set_decomposition(
    *,
    base: Configuration,
    selected: Configuration,
    incumbent: Configuration,
    evaluator: StepEvaluator,
    calibration: CalibrationValues,
    cell_rekeyed_users: Iterable[int] = (),
) -> tuple[object, tuple[EvaluatedProfile, ...]]:
    """Evaluate O(|A|) set terms and optional small-set Shapley reporting."""

    base_map = base.mapping
    changed = tuple(
        user for user in sorted(base_map) if selected.mapping[user] != base_map[user]
    )
    required_subsets = {frozenset(), frozenset(changed)} | {
        frozenset((user,)) for user in changed
    }
    subsets = (
        {
            frozenset(subset)
            for size in range(len(changed) + 1)
            for subset in itertools.combinations(changed, size)
        }
        if 1 < len(changed) <= 4
        else required_subsets
    )
    configs: list[tuple[frozenset[int], Configuration]] = []
    for subset in sorted(subsets, key=lambda row: (len(row), tuple(sorted(row)))):
        mapping = dict(base_map)
        for user in subset:
            mapping[user] = selected.mapping[user]
        configs.append((subset, _configuration(base, mapping, kind="committed-sparse-set")))
    evaluator.evaluate_many([config for _subset, config in configs])
    outcomes = {
        subset: evaluator.evaluate(config).outcome()
        for subset, config in configs
    }
    decomposition = set_score_decomposition(
        coalition_users=changed,
        outcomes_by_subset=outcomes,
        lambda_bits_per_j=calibration.lambda_bits_per_j,
        eta_ref=calibration.eta_ref,
        kappa_bits_per_user_step=calibration.kappa_bits_per_user_step,
        phi_difference=(
            _phi_for(incumbent, selected, cell_rekeyed_users=cell_rekeyed_users)
            - _phi_for(incumbent, base, cell_rekeyed_users=cell_rekeyed_users)
        ),
    )
    singletons = tuple(
        evaluator.evaluate(config)
        for subset, config in configs
        if len(subset) == 1
    )
    return decomposition, singletons


def _independent_proposal(
    *,
    base: Configuration,
    catalog: Sequence[Configuration],
    factors: Mapping[str, Mapping[tuple[int, tuple[int, int] | None], Fraction]],
    include: Sequence[str],
) -> Configuration:
    assignments = dict(base.assignments)
    for user in sorted(assignments):
        candidates = []
        for config in catalog:
            if config.changed_users != 1:
                continue
            identity = dict(config.assignments)[user]
            if identity == assignments[user]:
                continue
            score = sum((factors[name].get((user, identity), Fraction()) for name in include), Fraction())
            candidates.append((score, identity))
        if candidates:
            score, identity = min(candidates, key=lambda row: (-row[0], row[1]))
            if score > 0:
                assignments[user] = identity
    return next(
        (row for row in catalog if row.mapping == assignments),
        base,
    )


def _set_select(
    *,
    catalog: Sequence[Configuration],
    evaluated: Mapping[str, EvaluatedProfile],
    factors: Mapping[str, Mapping[tuple[int, tuple[int, int] | None], Fraction]],
    include: Sequence[str],
    base: Configuration,
    calibration: CalibrationValues,
) -> Configuration:
    del evaluated, calibration
    base_map = dict(base.assignments)
    scored = []
    for config in catalog:
        bonus = Fraction()
        for user, identity in config.assignments:
            if identity == base_map[user]:
                continue
            bonus += sum((factors[name].get((user, identity), Fraction()) for name in include), Fraction())
        # Factor arms compare only the declared target sum.  Exact F is
        # reserved for the U1/J1/union ceiling arms and S_UNI comparator.
        scored.append((bonus, config.configuration_id, config))
    return min(scored, key=lambda row: (-row[0], row[1]))[2]


def _unilateral_factor_select(
    *,
    base: Configuration,
    catalog: Sequence[Configuration],
    factors: Mapping[str, Mapping[tuple[int, tuple[int, int] | None], Fraction]],
) -> Configuration:
    candidates = [base] + [row for row in catalog if row.changed_users == 1]
    return _set_select(
        catalog=candidates,
        evaluated={},
        factors=factors,
        include=("C1", "C2", "C3"),
        base=base,
        calibration=None,  # type: ignore[arg-type]
    )


def _s_uni_select(
    *,
    base: Configuration,
    incumbent: Configuration,
    tape: ExogenousWorldTape,
    step_index: int,
    evaluator: StepEvaluator,
    calibration: CalibrationValues,
    compute_budget_s: float,
    run_setting: SealedRunSetting,
    cell_rekeyed_users: Iterable[int] = (),
) -> tuple[Configuration, int, float, bool, str]:
    """Information-matched exact single-user best response to convergence."""

    started = time.perf_counter()
    # Evaluation calls are non-preemptible.  Reserve enough wall time for the
    # final in-flight candidate and receipt bookkeeping so the arm stays
    # inside its declared comparator budget.
    deadline_at = started + max(0.0, compute_budget_s - S_UNI_BUDGET_GUARD_S)
    options, _census = _legal_options(tape, step_index)
    current = base
    iterations = 0
    previous_batch_wall_s = 0.0
    base_profile = evaluator.evaluate(base)
    base_served = sum(base_profile.score.served_phy.values())

    def coordinator_k0_objective(
        config: Configuration, profile: EvaluatedProfile
    ) -> Fraction:
        # C1+C3 at k=0 is (F(config)-F(base))/kappa plus the
        # incumbent-relative Phi difference.  The omitted base constants do
        # not affect ranking, so this is exactly the coordinator objective in
        # physical bit units.
        return _objective(profile, calibration) + (
            calibration.kappa_bits_per_user_step
            * _phi_for(
                incumbent,
                config,
                cell_rekeyed_users=cell_rekeyed_users,
            )
        )

    while True:
        if time.perf_counter() >= deadline_at:
            return (
                base,
                iterations,
                time.perf_counter() - started,
                True,
                "DEADLINE_FALLBACK_BASE",
            )
        current_profile = evaluator.evaluate(current)
        best = current
        best_value = coordinator_k0_objective(current, current_profile)
        candidates = []
        for user in sorted(options):
            for identity in options[user]:
                if identity == current.mapping[user]:
                    continue
                mapping = current.mapping
                mapping[user] = identity
                candidates.append(
                    _configuration(base, mapping, kind="s-uni-iterate")
                )
        for offset in range(0, len(candidates), SELECTION_STAGE2_M):
            remaining_s = deadline_at - time.perf_counter()
            if remaining_s <= max(0.25, previous_batch_wall_s):
                return (
                    base,
                    iterations,
                    time.perf_counter() - started,
                    True,
                    "DEADLINE_FALLBACK_BASE",
                )
            batch_started = time.perf_counter()
            evaluator.evaluate_many(
                candidates[offset : offset + SELECTION_STAGE2_M]
            )
            previous_batch_wall_s = max(
                previous_batch_wall_s,
                time.perf_counter() - batch_started,
            )
            if time.perf_counter() >= deadline_at:
                return (
                    base,
                    iterations,
                    time.perf_counter() - started,
                    True,
                    "DEADLINE_FALLBACK_BASE",
                )
        for candidate in candidates:
            if candidate.configuration_id in getattr(evaluator, "_invalid", ()):
                continue
            profile = evaluator.evaluate(candidate)
            if sum(profile.score.served_phy.values()) < base_served:
                continue
            value = coordinator_k0_objective(candidate, profile)
            if value > best_value or (
                value == best_value and candidate.configuration_id < best.configuration_id
            ):
                best, best_value = candidate, value
        if best.assignments == current.assignments:
            return (
                current,
                iterations,
                time.perf_counter() - started,
                False,
                "NO_IMPROVING_LEGAL_UNILATERAL",
            )
        current = best
        iterations += 1


def _stage2_shortlist(
    *,
    catalog: Sequence[Configuration],
    factors: Mapping[str, Mapping[str, object]],
    mandatory_ids: set[str],
    stage2_m: int = SELECTION_STAGE2_M,
) -> tuple[tuple[Configuration, ...], dict[str, object]]:
    """Build the production top-M surface from k=0 scores only."""

    if type(stage2_m) is not int or stage2_m < 1:
        raise ProbeError("stage-2 M must be a positive integer")
    rankings = {
        arm: _rank_for_arm(
            catalog=catalog,
            factors=factors,
            primary_names=components,
            use_c2=ARM_C2_TIEBREAK[arm],
        )
        for arm, components in ARM_PRIMARY_COMPONENTS.items()
    }
    stage2_ids = set(mandatory_ids)
    for ranking in rankings.values():
        stage2_ids.update(row.configuration_id for row in ranking[:stage2_m])
    rows = tuple(row for row in catalog if row.configuration_id in stage2_ids)
    return rows, {
        "stage1_top1_configuration": rankings["FULL"][0].configuration_id,
        "stage1_top1_by_arm": {
            arm: ranking[0].configuration_id
            for arm, ranking in rankings.items()
        },
        "stage2_candidate_count": len(rows),
        "stage2_top_m_per_arm": stage2_m,
    }


def _stage2_top1_diagnostic(
    *,
    stage1_top1_configuration: str,
    stage2_catalog: Sequence[Configuration],
    factors: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    """Compare k=0 top-1 with post-forecast top-1 on the evaluated surface."""

    stage2_top1 = _set_score_select(
        catalog=stage2_catalog,
        factors=factors,
        include=("C1", "C2", "C3"),
    )
    return {
        "stage1_top1_configuration": stage1_top1_configuration,
        "stage2_top1_configuration": stage2_top1.configuration_id,
        "stage1_stage2_top1_agree": (
            stage1_top1_configuration == stage2_top1.configuration_id
        ),
    }


def _s0_select(
    tape: ExogenousWorldTape,
    setting: PhysicsSetting,
    step_index: int,
    base: Configuration,
    catalog: Sequence[Configuration],
    counter: EvaluationCounter,
    run_setting: SealedRunSetting | None = None,
) -> tuple[Configuration, tuple[str, ...], Configuration]:
    nominal_evaluator = StepEvaluator(
        tape,
        setting,
        step_index,
        transition_from=base,
        cell_rekeyed_users=_rekeyed_users(tape, step_index),
        field="margin",
        fading_quantile_alpha=0.10,
        counter=counter,
        run_setting=run_setting,
    )
    nominal_profiles = {
        row.configuration_id: nominal_evaluator.evaluate(row) for row in catalog
    }
    unilateral = [row for row in catalog if row.changed_users == 1]
    top_ids = []
    for user, _ in base.assignments:
        proposals = [row for row in unilateral if dict(row.assignments)[user] != dict(base.assignments)[user]]
        ranked = sorted(
            proposals,
            key=lambda row: (
                -_nominal_configuration(row, nominal_profiles[row.configuration_id]).nominal_bits,
                row.configuration_id,
            ),
        )[:TOP_PROPOSALS]
        top_ids.extend(row.configuration_id for row in ranked)
    allowed = [base] + [row for row in unilateral if row.configuration_id in top_ids]
    # Frozen evacuations: include multi-user configurations assembled solely
    # from the top-two per-user proposal identities.
    allowed.extend(
        row
        for row in catalog
        if row.changed_users > 1
        and all(
            any(dict(proposal.assignments)[user] == identity for proposal in unilateral if proposal.configuration_id in top_ids)
            for user, identity in row.assignments
            if identity != dict(base.assignments)[user]
        )
    )
    nominal = nominal_greedy_reference(
        _nominal_configuration(row, nominal_profiles[row.configuration_id]) for row in allowed
    )
    nominal_all = nominal_greedy_reference(
        _nominal_configuration(row, nominal_profiles[row.configuration_id]) for row in catalog
    )
    return (
        next(row for row in allowed if row.configuration_id == nominal.configuration_id),
        tuple(sorted(set(top_ids))),
        next(row for row in catalog if row.configuration_id == nominal_all.configuration_id),
    )


def _rate_tail(bits: Mapping[int, float]) -> dict[str, float]:
    rates = np.asarray([value / DECISION_INTERVAL_S for value in bits.values()], dtype=np.float64)
    if rates.size == 0:
        return {"p05_bps": 0.0, "p50_bps": 0.0, "p95_bps": 0.0}
    return {
        "p05_bps": float(np.quantile(rates, 0.05)),
        "p50_bps": float(np.quantile(rates, 0.50)),
        "p95_bps": float(np.quantile(rates, 0.95)),
    }


def _arm_row(
    *,
    arm: str,
    profile: EvaluatedProfile,
    base: Configuration,
    cell_rekeyed_users: Iterable[int],
    previously_served_users: Iterable[int],
    elapsed_s: float,
) -> dict[str, object]:
    users = max(1, len(base.assignments))
    opportunity = users * DECISION_INTERVAL_S
    events = _physical_events(
        base,
        profile.config,
        cell_rekeyed_users=cell_rekeyed_users,
        previously_served_users=previously_served_users,
    )
    phi = phi_qos(events)
    handover_count = sum(
        event.kind in {"beam_change", "satellite_change", "cell_rekey"} for event in events
    )
    complete = sum(
        math.isclose(
            float(profile.score.decoding_time_s.get(user, 0.0)),
            DECISION_INTERVAL_S,
            rel_tol=0.0,
            abs_tol=1.0e-9,
        )
        for user, _identity in base.assignments
    )
    partial = sum(
        float(profile.score.decoding_time_s.get(user, 0.0)) > 0.0
        for user, _identity in base.assignments
    )
    useful_user_seconds = math.fsum(profile.score.useful_time_s.values())
    return {
        "arm": arm,
        "configuration_id": profile.config.configuration_id,
        "bits": profile.bits,
        "joules": profile.joules,
        "pooled_ee_bits_per_j": None if profile.joules == 0 else profile.bits / profile.joules,
        "energy": dict(profile.energy_components),
        "lit_beam_seconds": profile.lit_beam_seconds,
        "lit_satellite_seconds": profile.lit_satellite_seconds,
        "decoding_availability": math.fsum(profile.score.decoding_time_s.values()) / opportunity,
        "useful_availability": math.fsum(profile.score.useful_time_s.values()) / opportunity,
        "partial_service_availability": partial / users,
        "complete_service_availability": complete / users,
        "complete_service_user_steps": complete,
        "full_roster_user_steps": users,
        "qos_additive": {
            "availability_served": useful_user_seconds,
            "availability_opportunities": opportunity,
            "handover_events": handover_count,
            "handover_opportunities": users,
            "phi_cost_numerator": -float(phi),
            "phi_cost_denominator": users,
        },
        "phi_signalling_qos_preference": float(phi),
        "phi_priced_handover_cost_per_user_step": -float(phi) / users,
        "handover_rate_per_user_decision": handover_count / users,
        "rate_tail": _rate_tail(profile.score.bits),
        "served_PHY": profile.score.served_phy,
        "rate_target_attained": profile.score.rate_target_attained,
        "rate_target_feasible": profile.score.rate_target_feasible,
        "rate_target_attainment_by_boundary": profile.score.rate_target_attainment_by_boundary,
        "acm_mode_counts": dict(profile.acm_mode_counts),
        "acm_causal_objects": {
            "m_target_counts": dict(profile.m_target_counts or {}),
            "m_tx_counts": dict(profile.m_tx_counts or {}),
            "realised_outcome": {
                "decoded": profile.realised_decode_successes,
                "outage": profile.realised_decode_failures,
            },
            "emission_granularity": "per arm user-step transmission census",
        },
        "required_power_w_max": profile.required_power_w_max,
        "min_decoding_margin_db": profile.min_decoding_margin_db,
        "mean_acm_se_bit_s_hz": profile.mean_acm_se_bit_s_hz,
        "rf_cap_hits": profile.rf_cap_hits,
        "rf_transmission_observations": profile.rf_transmission_observations,
        "certificate_status": profile.certificate_status,
        "certificate_iterations": profile.certificate_iterations,
        "treatment_t_same_instant_comparison": profile.treatment_t_same_instant_comparison,
        "changed_users": profile.config.changed_users,
        "handovers": {
            kind: sum(event.kind == kind for event in events)
            for kind in ("beam_change", "satellite_change", "cell_rekey", "initial_entry", "reentry", "exit")
        },
        "prior_current_identities": [
            {
                "user_id": user,
                "prior": None if base.mapping[user] is None else list(base.mapping[user]),
                "current": (
                    None
                    if profile.config.mapping[user] is None
                    else list(profile.config.mapping[user])
                ),
                "event_type": next(event.kind for event in events if event.user_id == user),
            }
            for user, _identity in base.assignments
        ],
        "decision_time_s": elapsed_s,
    }


def _anchor_qos_metrics(
    profile: EvaluatedProfile,
    incumbent: Configuration,
    *,
    cell_rekeyed_users: Iterable[int],
    previously_served_users: Iterable[int] = (),
) -> dict[str, float]:
    users = max(1, len(incumbent.assignments))
    events = _physical_events(
        incumbent,
        profile.config,
        cell_rekeyed_users=cell_rekeyed_users,
        previously_served_users=previously_served_users,
    )
    return {
        "availability": math.fsum(profile.score.useful_time_s.values())
        / (users * DECISION_INTERVAL_S),
        "handover_rate": sum(
            event.kind in {"beam_change", "satellite_change", "cell_rekey"}
            for event in events
        )
        / users,
        "phi_cost": max(0.0, -float(phi_qos(events))) / users,
    }


def _anchor_qos_noninferior(
    candidate: EvaluatedProfile,
    comparators: Sequence[EvaluatedProfile],
    incumbent: Configuration,
    *,
    cell_rekeyed_users: Iterable[int],
    previously_served_users: Iterable[int] = (),
) -> tuple[bool, dict[str, object]]:
    candidate_qos = _anchor_qos_metrics(
        candidate,
        incumbent,
        cell_rekeyed_users=cell_rekeyed_users,
        previously_served_users=previously_served_users,
    )

    def relative(numerator: float, denominator: float) -> float | None:
        if denominator > 0.0:
            return numerator / denominator - 1.0
        return 0.0 if numerator == 0.0 else None

    rows = {}
    passed = True
    for comparator in comparators:
        comparator_qos = _anchor_qos_metrics(
            comparator,
            incumbent,
            cell_rekeyed_users=cell_rekeyed_users,
            previously_served_users=previously_served_users,
        )
        certificate = {
            "availability_delta": candidate_qos["availability"]
            - comparator_qos["availability"],
            "handover_rate_relative_change": relative(
                candidate_qos["handover_rate"], comparator_qos["handover_rate"]
            ),
            "phi_cost_relative_change": relative(
                candidate_qos["phi_cost"], comparator_qos["phi_cost"]
            ),
        }
        handover_relative = certificate["handover_rate_relative_change"]
        phi_relative = certificate["phi_cost_relative_change"]
        certificate["pass"] = (
            certificate["availability_delta"] > -0.005
            and handover_relative is not None
            and handover_relative < 0.05
            and phi_relative is not None
            and phi_relative < 0.05
        )
        passed &= bool(certificate["pass"])
        rows[comparator.config.configuration_id] = certificate
    return passed, {"candidate": candidate_qos, "comparators": rows}


def _canonical_step_rows(
    steps: Sequence[Mapping[str, object]],
    *,
    provider_sha256: str,
    code_sha256: str,
) -> list[dict[str, object]]:
    rows = []
    for step in steps:
        for arm in step["arms"]:  # type: ignore[index]
            rows.append(
                {
                    "schema": f"{SCHEMA}-canonical-step-row",
                    "anchor_index": int(step["anchor_index"]),
                    "step_index": int(step["step_index"]),
                    "carrier": str(step["carrier"]),
                    "rekey_eligible_user_boundaries": int(
                        step["rekey_eligible_user_boundaries"]
                    ),
                    "arm": str(arm["arm"]),
                    "bits_hex": float(arm["bits"]).hex(),
                    "joules_hex": float(arm["joules"]).hex(),
                    "energy_hex": {
                        name: float(value).hex()
                        for name, value in arm["energy"].items()  # type: ignore[union-attr]
                    },
                    "opportunity_user_seconds_hex": (
                        int(arm["full_roster_user_steps"]) * DECISION_INTERVAL_S
                    ).hex(),
                    "served_partial_user_steps": int(
                        round(
                            float(arm["partial_service_availability"])
                            * int(arm["full_roster_user_steps"])
                        )
                    ),
                    "served_complete_user_steps": int(arm["complete_service_user_steps"]),
                    "full_roster_user_steps": int(arm["full_roster_user_steps"]),
                    "prior_current_identities": arm["prior_current_identities"],
                    "phi_numerator_hex": float(arm["phi_signalling_qos_preference"]).hex(),
                    "phi_denominator": int(arm["full_roster_user_steps"]),
                    "handover_events": int(arm["qos_additive"]["handover_events"]),
                    "handover_opportunities": int(
                        arm["qos_additive"]["handover_opportunities"]
                    ),
                    "arm_payload": arm,
                    "arm_payload_sha256": digest_payload(arm),
                    "provider_sha256": provider_sha256,
                    "code_sha256": code_sha256,
                }
            )
    return rows


def _verify_reaggregation(
    rows: Sequence[Mapping[str, object]],
    summary: Mapping[str, object],
    *,
    provider_sha256: str | None = None,
    code_sha256: str | None = None,
) -> None:
    wrapper_rows = [
        {
            name: value
            for name, value in row.items()
            if name not in {"arm_payload", "arm_payload_sha256"}
        }
        for row in rows
    ]
    if digest_payload(wrapper_rows) != summary["canonical_wrapper_sha256"]:
        raise ProbeError("canonical row wrappers disagree with summary binding")
    expected_schema = f"{SCHEMA}-canonical-step-row"
    hexadecimal = set("0123456789abcdef")
    for row in rows:
        payload = row["arm_payload"]
        expected_wrapper = {
            "schema": expected_schema,
            "arm": payload["arm"],
            "bits_hex": float(payload["bits"]).hex(),
            "joules_hex": float(payload["joules"]).hex(),
            "energy_hex": {
                name: float(value).hex()
                for name, value in payload["energy"].items()
            },
            "opportunity_user_seconds_hex": (
                int(payload["full_roster_user_steps"]) * DECISION_INTERVAL_S
            ).hex(),
            "served_partial_user_steps": int(
                round(
                    float(payload["partial_service_availability"])
                    * int(payload["full_roster_user_steps"])
                )
            ),
            "served_complete_user_steps": int(
                payload["complete_service_user_steps"]
            ),
            "full_roster_user_steps": int(payload["full_roster_user_steps"]),
            "prior_current_identities": payload["prior_current_identities"],
            "phi_numerator_hex": float(
                payload["phi_signalling_qos_preference"]
            ).hex(),
            "phi_denominator": int(payload["full_roster_user_steps"]),
            "handover_events": int(payload["qos_additive"]["handover_events"]),
            "handover_opportunities": int(
                payload["qos_additive"]["handover_opportunities"]
            ),
        }
        if any(row[name] != value for name, value in expected_wrapper.items()):
            raise ProbeError("canonical row wrapper disagrees with arm payload")
        for field, expected_authority in (
            ("provider_sha256", provider_sha256),
            ("code_sha256", code_sha256),
        ):
            value = row[field]
            if (
                not isinstance(value, str)
                or len(value) != 64
                or not set(value) <= hexadecimal
                or (expected_authority is not None and value != expected_authority)
            ):
                raise ProbeError(f"canonical row has invalid {field}")
    groups: dict[tuple[object, object, object], set[str]] = {}
    for row in rows:
        key = (row["anchor_index"], row["step_index"], row["carrier"])
        groups.setdefault(key, set()).add(str(row["arm"]))
    if any(arms != set(ARMS) for arms in groups.values()):
        raise ProbeError("canonical anchor wrapper does not contain every arm")
    if sorted(int(key[0]) for key in groups) != list(range(len(groups))):
        raise ProbeError("canonical anchor indices are not contiguous")
    if any(str(key[2]) not in REFERENCE_CARRIERS for key in groups):
        raise ProbeError("canonical row carrier is outside the reference set")
    for arm_name in ARMS:
        selected = [row for row in rows if row["arm"] == arm_name]
        expected = summary["arms"][arm_name]  # type: ignore[index]
        if any(
            row["arm_payload_sha256"] != digest_payload(row["arm_payload"])
            for row in selected
        ):
            raise ProbeError("canonical row arm payload digest is invalid")
        arms = [row["arm_payload"] for row in selected]
        sums = {
            "bits": math.fsum(float(row["bits"]) for row in arms),
            "joules": math.fsum(float(row["joules"]) for row in arms),
            "pa_j": math.fsum(float(row["energy"]["pa_j"]) for row in arms),
            "standby_j": math.fsum(float(row["energy"]["standby_j"]) for row in arms),
            "circuit_j": math.fsum(float(row["energy"]["circuit_j"]) for row in arms),
            "baseband_j": math.fsum(float(row["energy"]["baseband_j"]) for row in arms),
            "phi_signalling_qos_preference": math.fsum(
                float(row["phi_signalling_qos_preference"]) for row in arms
            ),
            "changed_users": sum(int(row["changed_users"]) for row in arms),
        }
        for name, value in sums.items():
            if isinstance(value, int):
                matches = value == int(expected[name])
            else:
                matches = float(value).hex() == float(expected[name]).hex()
            if not matches:
                raise ProbeError(
                    f"canonical rows disagree with receipt summary field {arm_name}.{name}"
                )
        pooled_ee = None if sums["joules"] == 0 else sums["bits"] / sums["joules"]
        expected_ee = expected["pooled_ee_bits_per_j"]
        if (pooled_ee is None) != (expected_ee is None) or (
            pooled_ee is not None
            and expected_ee is not None
            and float(pooled_ee).hex() != float(expected_ee).hex()
        ):
            raise ProbeError(
                f"canonical rows disagree with pooled EE for {arm_name}"
            )
        for kind in (
            "beam_change",
            "satellite_change",
            "cell_rekey",
            "initial_entry",
            "reentry",
            "exit",
        ):
            value = sum(int(row["handovers"][kind]) for row in arms)
            if value != int(expected["handovers"][kind]):
                raise ProbeError(
                    f"canonical rows disagree with handover field {arm_name}.{kind}"
                )
        additive = {
            name: math.fsum(float(row["qos_additive"][name]) for row in arms)
            for name in (
                "availability_served",
                "availability_opportunities",
                "handover_events",
                "handover_opportunities",
                "phi_cost_numerator",
                "phi_cost_denominator",
            )
        }
        for name, value in additive.items():
            if float(value).hex() != float(expected["qos_additive"][name]).hex():
                raise ProbeError(
                    f"canonical rows disagree with additive QoS field {arm_name}.{name}"
                )
        derived = {
            "availability": additive["availability_served"] / additive["availability_opportunities"],
            "decoding_availability": math.fsum(float(row["decoding_availability"]) for row in arms) / len(arms),
            "partial_service_availability": math.fsum(float(row["partial_service_availability"]) for row in arms) / len(arms),
            "useful_availability": math.fsum(float(row["useful_availability"]) for row in arms) / len(arms),
            "phi_priced_handover_cost_per_user_step": additive["phi_cost_numerator"] / additive["phi_cost_denominator"],
            "handover_rate_per_user_decision": additive["handover_events"] / additive["handover_opportunities"],
        }
        for name, value in derived.items():
            if float(value).hex() != float(expected[name]).hex():
                raise ProbeError(
                    f"canonical rows disagree with derived QoS field {arm_name}.{name}"
                )
        rekeys = sum(int(row["handovers"]["cell_rekey"]) for row in arms)
        eligible = sum(
            int(row["rekey_eligible_user_boundaries"]) for row in selected
        )
        corrected_rekey = {
            "rekeys": rekeys,
            "eligible_user_boundaries": eligible,
            "rate": corrected_boundary_rekey_rate(
                rekeys=rekeys,
                eligible_boundaries=eligible,
            ),
            "numerator_source": "physical event ledger",
        }
        if corrected_rekey != expected["corrected_boundary_conditional_rekey"]:
            raise ProbeError(
                f"canonical rows disagree with corrected rekey rate for {arm_name}"
            )
        distribution_fields = {
            "decision_time_tail_s": {
                "p50": float(np.quantile([row["decision_time_s"] for row in arms], 0.5)),
                "p95": float(np.quantile([row["decision_time_s"] for row in arms], 0.95)),
                "max": max(float(row["decision_time_s"]) for row in arms),
            },
            "rate_tail": {
                key: float(
                    np.quantile([row["rate_tail"][key] for row in arms], 0.5)
                )
                for key in ("p05_bps", "p50_bps", "p95_bps")
            },
            "required_power_w_max_distribution": {
                "min": min(float(row["required_power_w_max"]) for row in arms),
                "p50": float(
                    np.quantile(
                        [row["required_power_w_max"] for row in arms], 0.5
                    )
                ),
                "max": max(float(row["required_power_w_max"]) for row in arms),
            },
        }
        for field, values in distribution_fields.items():
            if any(
                float(value).hex() != float(expected[field][name]).hex()
                for name, value in values.items()
            ):
                raise ProbeError(
                    f"canonical rows disagree with distribution field {arm_name}.{field}"
                )
        expected_modes = {
            mode: sum(int(row["acm_mode_counts"].get(mode, 0)) for row in arms)
            for mode in sorted({mode for row in arms for mode in row["acm_mode_counts"]})
        }
        if expected_modes != expected["acm_mode_counts"]:
            raise ProbeError(f"canonical rows disagree with ACM modes for {arm_name}")
        expected_certificates = {
            status: sum(row["certificate_status"] == status for row in arms)
            for status in ("FIXED", "CONVERGED", "CONVERGED_SLOW", "INVALID")
        }
        if expected_certificates != expected["certificate_distribution"]:
            raise ProbeError(f"canonical rows disagree with certificates for {arm_name}")
        rf_total = sum(int(row["rf_transmission_observations"]) for row in arms)
        rf_share = sum(int(row["rf_cap_hits"]) for row in arms) / max(1, rf_total)
        if float(rf_share).hex() != float(expected["rf_cap_share"]).hex():
            raise ProbeError(f"canonical rows disagree with RF-cap share for {arm_name}")
        for row in selected:
            payload = row["arm_payload"]
            if row["prior_current_identities"] != payload["prior_current_identities"]:
                raise ProbeError("canonical identity ledger disagrees with arm payload")
            if row["bits_hex"] != float(payload["bits"]).hex() or row["joules_hex"] != float(payload["joules"]).hex():
                raise ProbeError("canonical endpoint hex disagrees with arm payload")
        if digest_payload(arms) != expected["arm_payloads_sha256"]:
            raise ProbeError(
                f"canonical rows disagree with complete payload aggregate for {arm_name}"
            )


def _usable_energy_range_step(
    *,
    selected: EvaluatedProfile,
    base: Configuration,
    base_profile: EvaluatedProfile,
    evaluated: Mapping[str, EvaluatedProfile],
) -> dict[str, object]:
    """Reporting-only successor range diagnostic; it applies no gate."""

    base_map = dict(base.assignments)
    by_beam: dict[str, float] = {}
    for beam in sorted({identity for identity in base_map.values() if identity is not None}):
        alternatives = [
            row
            for row in evaluated.values()
            if all(row.score.served_phy.values())
            and any(
                base_map[user] == beam and identity != beam
                for user, identity in row.config.assignments
            )
        ]
        best_change = max(
            (base_profile.joules - row.joules for row in alternatives),
            default=0.0,
        )
        by_beam[f"{beam[0]}:{beam[1]}"] = float(best_change)
    return {
        "selected_acm_mode_counts": dict(sorted(selected.acm_mode_counts.items())),
        "se_plateau_user_steps": selected.se_plateau_user_steps,
        "user_step_observations": selected.user_step_observations,
        "rf_cap_hits": selected.rf_cap_hits,
        "rf_transmission_observations": selected.rf_transmission_observations,
        "se_plateau_user_step_share": (
            0.0
            if selected.user_step_observations == 0
            else selected.se_plateau_user_steps / selected.user_step_observations
        ),
        "rf_cap_transmission_share": (
            0.0
            if selected.rf_transmission_observations == 0
            else selected.rf_cap_hits / selected.rf_transmission_observations
        ),
        "best_feasible_reassignment_dc_energy_change_j_by_beam": by_beam,
        "thresholds_applied": False,
    }


def execute_step(
    *,
    tape: ExogenousWorldTape,
    setting: PhysicsSetting,
    step_index: int,
    carrier: str,
    calibration: CalibrationValues,
    counter: EvaluationCounter,
    incumbent: Configuration | None = None,
    c2_horizon_offsets: int = 3,
    run_setting: SealedRunSetting | None = None,
    selection_workers: int = DECLARED_WORKERS,
    selection_boundary_indices: tuple[int, ...] = SELECTION_BOUNDARY_INDICES,
    selection_stage2_m: int = SELECTION_STAGE2_M,
    selection_fading_quantile_alpha: float | None = 0.10,
    previously_served_users: Iterable[int] | None = None,
) -> dict[str, object]:
    if type(selection_workers) is not int or selection_workers < 1:
        raise ProbeError("selection_workers must be a positive integer")
    if not selection_boundary_indices or any(
        type(index) is not int or not 0 <= index < 48
        for index in selection_boundary_indices
    ):
        raise ProbeError("selection boundary indices must be nonempty indices in 0..47")
    anchor_started = time.perf_counter()
    decision_started = anchor_started
    deadline_at = decision_started + DECISION_DEADLINE_S
    phase: dict[str, float] = {}
    counter_start = counter.boundary_evaluations
    active_run = run_setting_for(setting.label) if run_setting is None else run_setting
    base = _base_configuration(tape, step_index, carrier)
    incumbent = base if incumbent is None else incumbent
    cell_rekeys = _rekeyed_users(tape, step_index)
    previously_served = (
        _previously_served_users(tape, step_index, carrier)
        if previously_served_users is None
        else tuple(sorted(set(int(user) for user in previously_served_users)))
    )
    selection_dependency_sha256 = _assert_selection_dependencies(
        _selection_dependencies(
            tape=tape,
            incumbent=incumbent,
            setting=setting,
            calibration=calibration,
            run_setting=active_run,
            step_index=step_index,
            carrier=carrier,
            cell_rekeyed_users=cell_rekeys,
            previously_served_users=previously_served,
        )
    )

    started = time.perf_counter()
    quantile_bins = _prewarm_selection_quantiles(
        tape,
        anchor_step=step_index,
        boundary_indices=selection_boundary_indices,
        alpha=selection_fading_quantile_alpha,
    )
    phase["fading_quantile_cache"] = time.perf_counter() - started
    phase["fading_quantile_cache_bins"] = quantile_bins

    # The pool is opened before the catalogue so that the catalogue's own k=0
    # unilateral ranking pass runs in the declared workers instead of serially
    # in the coordinator process.  Opening it here changes no result: the
    # workers are forked after the quantile prewarm exactly as before, and the
    # pool is closed again below whenever the catalogue turns out to be too
    # small for the sealed parallel-execution predicate.
    pool = _open_selection_pool(
        workers=selection_workers,
        tape=tape,
        setting=setting,
        step_index=step_index,
        carrier=carrier,
        incumbent=incumbent,
        cell_rekeys=cell_rekeys,
        previously_served_users=previously_served,
        calibration=calibration,
        run_setting=active_run,
        selection_alpha=selection_fading_quantile_alpha,
        ranking_setting=_setting("a-r0") if setting is None else setting,
    )
    started = time.perf_counter()
    ranking_sink: dict[str, SelectionProfile] = {}
    ranking_invalid: set[str] = set()
    catalog, catalogue_census = _catalogue_with_census(
        tape,
        step_index,
        base,
        setting=setting,
        calibration=calibration,
        counter=counter,
        run_setting=active_run,
        ranking_pool=pool if SELECTION_REUSE_ENABLED else None,
        ranking_workers=selection_workers,
        ranking_sink=ranking_sink,
        ranking_invalid_sink=ranking_invalid,
    )
    if catalogue_census["catalogue_mode"] != "complete-cartesian" and len(catalog) > CATALOGUE_CAP:
        raise ProbeError(
            f"selection shortlist row-count gate failed: {len(catalog)} > {CATALOGUE_CAP}"
        )
    phase["catalogue"] = time.perf_counter() - started
    phase["catalogue_row_count"] = len(catalog)

    parallel_used = (
        selection_workers > 1 and len(catalog) >= PARALLEL_MINIMUM_ROWS
    )
    evaluation_workers = selection_workers if parallel_used else 1
    if pool is not None and not parallel_used:
        pool.shutdown(wait=True)
        pool = None
    # Stage 1 reads the same k=0 view as the catalogue ranking only when the
    # selection quantile is the sealed ranking quantile and the field agrees.
    # Every other input of the a-r0 batch kernel (step arrays, selected rows,
    # boundary indices, run setting) is already identical by construction.
    stage1_reuse_allowed = (
        SELECTION_REUSE_ENABLED
        and selection_fading_quantile_alpha == CATALOGUE_RANKING_ALPHA
    )
    seed_profiles = ranking_sink if stage1_reuse_allowed else {}
    stage1_reused_ids = sum(
        1 for row in catalog if row.configuration_id in seed_profiles
    )
    stage1_evaluated_count = len(catalog) - stage1_reused_ids
    started = time.perf_counter()
    selection_evaluator = StepEvaluator(
        tape,
        setting,
        step_index,
        transition_from=incumbent,
        cell_rekeyed_users=cell_rekeys,
        previously_served_users=previously_served,
        field=(
            "nominal"
            if selection_fading_quantile_alpha is None
            else "margin"
        ),
        counter=counter,
        run_setting=active_run,
        boundary_indices=(0,),
        fading_quantile_alpha=selection_fading_quantile_alpha,
    )
    stage1_profiles, stage1_invalid, stage1_shards = _parallel_stage1_profiles(
        pool=pool,
        configs=catalog,
        workers=evaluation_workers,
        serial_evaluator=selection_evaluator,
        counter=counter,
        seed_profiles=seed_profiles,
    )
    if stage1_reuse_allowed:
        stage1_invalid |= ranking_invalid
    selection_evaluator._invalid.update(stage1_invalid)
    catalog = tuple(
        row
        for row in catalog
        if row.configuration_id not in selection_evaluator._invalid
    )
    if base.configuration_id not in stage1_profiles:
        raise ProbeError("BASE has an invalid selection-time power certificate")
    factors = _selection_factor_scores(
        base=base,
        incumbent=incumbent,
        catalog=catalog,
        evaluated=stage1_profiles,
        calibration=calibration,
        cell_rekeyed_users=cell_rekeys,
    )
    base_selection = stage1_profiles[base.configuration_id]
    base_served = base_selection.served_count
    service_guarded = tuple(
        row
        for row in catalog
        if stage1_profiles[row.configuration_id].served_count
        >= base_served
    )
    unilateral_configs = tuple(row for row in catalog if row.changed_users == 1)
    joint_configs = tuple(row for row in catalog if row.changed_users > 1)
    u1 = _best(
        (base_selection, *(stage1_profiles[row.configuration_id] for row in unilateral_configs)),
        calibration,
    )
    j1 = _best(
        (base_selection, *(stage1_profiles[row.configuration_id] for row in joint_configs)),
        calibration,
    )
    union = _best(stage1_profiles.values(), calibration)
    phase["stage1_scores"] = time.perf_counter() - started

    started = time.perf_counter()
    mandatory_ids = {
        base.configuration_id,
        *(
            row.configuration_id
            for row in catalog
            if row.kind in {"s0-top-two", "beam-evacuation"}
        ),
    }
    incumbent_match = next(
        (row for row in catalog if row.assignments == incumbent.assignments), None
    )
    if incumbent_match is not None:
        mandatory_ids.add(incumbent_match.configuration_id)
    stage2, stage2_shortlist_diagnostic = _stage2_shortlist(
        catalog=catalog,
        factors=factors,
        mandatory_ids=mandatory_ids,
        stage2_m=selection_stage2_m,
    )
    forecasts, forecast_receipts, stage2_shards = _parallel_stage2_forecasts(
        pool=pool,
        tape=tape,
        setting=setting,
        anchor_step=step_index,
        carrier=carrier,
        configs=stage2,
        counter=counter,
        calibration=calibration,
        run_setting=active_run,
        workers=evaluation_workers,
        boundary_indices=selection_boundary_indices,
        fading_quantile_alpha=selection_fading_quantile_alpha,
    )
    _attach_stage2_c2(
        factors=factors,
        forecasts=forecasts,
        base=base,
        calibration=calibration,
        horizon_offsets=c2_horizon_offsets,
    )
    c2_tie_diagnostic = _c2_tie_diagnostic(
        catalog=stage2,
        factors=factors,
    )
    stage2 = tuple(row for row in stage2 if row.configuration_id in forecasts)
    stage2_top1_diagnostic = _stage2_top1_diagnostic(
        stage1_top1_configuration=str(
            stage2_shortlist_diagnostic["stage1_top1_configuration"]
        ),
        stage2_catalog=stage2,
        factors=factors,
    )
    phase["stage2_forecasts"] = time.perf_counter() - started

    started = time.perf_counter()
    guarded_stage2 = tuple(row for row in stage2 if row in service_guarded)
    if base not in guarded_stage2:
        guarded_stage2 = (base, *guarded_stage2)
    s0_candidates = tuple(
        row
        for row in guarded_stage2
        if row.kind in {"reference", "s0-top-two", "beam-evacuation"}
    )
    if not s0_candidates:
        s0_candidates = (base,)
    s0 = nominal_greedy_reference(
        _nominal_configuration(row, stage1_profiles[row.configuration_id])
        for row in s0_candidates
    )
    s0_config = next(row for row in s0_candidates if row.configuration_id == s0.configuration_id)
    nominal_all = nominal_greedy_reference(
        _nominal_configuration(row, stage1_profiles[row.configuration_id])
        for row in catalog
    )
    nominal_control = next(
        row for row in catalog if row.configuration_id == nominal_all.configuration_id
    )
    selections = {
        "E1_U1": u1.config,
        "E1_J1": j1.config,
        "UNION_CATALOGUE_OPTIMUM": union.config,
        "S0_DEPLOYABLE": s0_config,
        **{
            arm: _select_for_arm(
                arm, catalog=guarded_stage2, factors=factors
            )
            for arm in ARM_PRIMARY_COMPONENTS
        },
        "UNI": _set_score_select(
            catalog=(base, *tuple(row for row in guarded_stage2 if row.changed_users == 1)),
            factors=factors,
            include=("C1", "C2", "C3"),
        ),
        "S_UNI": base,
        ALL_NEUTRAL_CONTROL: base,
        "NULL": base,
        "RANDOM_FEASIBLE": catalog[int(tape.seed + step_index) % len(catalog)],
        "NOMINAL_GREEDY": nominal_control,
    }
    phase["selection"] = time.perf_counter() - started

    # A miss detected before committed validation atomically selects BASE for
    # every deployable arm.  The committed 48-boundary validation is now waited
    # on preemptively against the same wall clock (see the bounded
    # ``future.result(timeout=...)`` below), so the coordinator never has to
    # forecast the validation cost: the only test that can fire before the
    # solve starts is the exact statement that the clock has already run out.
    #
    # The superseded stage-4h predicate extrapolated a k=0 *per-catalogue-row*
    # wall cost to ``validation_rows * 48`` boundary rows.  That estimator
    # over-predicted the measured validation phase by 1.6x-32x on the ten-anchor
    # a-r0 smoke (for example anchor 2: reserve 10.284 s against a measured
    # 0.911 s), because the k=0 stage-1 wall is dominated by per-call batch
    # setup that a 48-boundary batch pays once, not 48 times.  Every arm
    # therefore fell back to BASE even when the whole decision finished in
    # 5.7 s of the 10 s budget.  The rows below are retained for the receipt
    # only; they no longer gate anything.
    elapsed_before_validation = time.perf_counter() - decision_started
    changed_full = selections["FULL"].changed_users
    decomposition_rows = (
        2**changed_full
        if 1 < changed_full <= 4
        else changed_full + 2
        if changed_full
        else 1
    )
    validation_rows = len(
        {row.configuration_id for row in selections.values()}
    ) + decomposition_rows
    deadline_missed = elapsed_before_validation >= DECISION_DEADLINE_S
    validation_wait_budget_s = max(
        0.0, DECISION_DEADLINE_S - elapsed_before_validation
    )
    # Reporting only: what the superseded stage-4h predicate would have decided
    # on this very anchor, so a before/after fallback-rate comparison is paired
    # by construction instead of relying on two separately loaded runs.
    retired_reserve_s = (
        phase["stage1_scores"] / max(1, len(catalog))
    ) * validation_rows * 48
    retired_predicate_would_fall_back = (
        elapsed_before_validation >= DECISION_DEADLINE_S
        or elapsed_before_validation + retired_reserve_s >= DECISION_DEADLINE_S
    )
    validation_within_deadline: bool | None = None
    pre_fallback = {name: row.configuration_id for name, row in selections.items()}
    selections = apply_deadline_fallback(selections, base=base, missed=deadline_missed)

    unique_selected = tuple(
        {row.configuration_id: row for row in selections.values()}.values()
    )
    started = time.perf_counter()
    if pool is not None:
        validation_future = pool.submit(
            _selection_worker_validate,
            (unique_selected, selections["FULL"], j1.config, u1.config),
        )
        # Preemptive wait: the committed selection is fixed at the ten-second
        # wall whatever the solve is doing.  On a timeout the arms atomically
        # take BASE and the decomposition is read from the same future purely
        # so the receipt can carry it; nothing after the timeout can change
        # which configuration was committed.
        try:
            (
                validated_profiles,
                committed_decomposition,
                singleton_profiles,
                base_decomposition,
                validation_evaluations,
            ) = validation_future.result(timeout=validation_wait_budget_s)
            validation_within_deadline = True
        except FutureTimeoutError:
            validation_within_deadline = False
            deadline_missed = True
            try:
                (
                    validated_profiles,
                    committed_decomposition,
                    singleton_profiles,
                    base_decomposition,
                    validation_evaluations,
                ) = validation_future.result()
            except BrokenProcessPool:
                # The committed decision is already fixed at the deadline; the
                # receipt data is recovered in this process so that a worker
                # lost to the host (out of memory, external kill) degrades the
                # audit trail's latency and not its content.  The remaining
                # worker-side stages fall back to the serial path below.
                pool = None
                (
                    validated_profiles,
                    committed_decomposition,
                    singleton_profiles,
                    base_decomposition,
                    validation_evaluations,
                    recovered_evaluator,
                ) = _validate_committed_serially(
                    tape=tape,
                    setting=setting,
                    step_index=step_index,
                    incumbent=incumbent,
                    cell_rekeys=cell_rekeys,
                    previously_served=previously_served,
                    run_setting=active_run,
                    calibration=calibration,
                    base=base,
                    unique_selected=unique_selected,
                    full=selections["FULL"],
                    j1=j1.config,
                    u1=u1.config,
                )
        counter.boundary_evaluations += validation_evaluations
        evaluated = {
            profile.config.configuration_id: profile
            for profile in validated_profiles
        }
        evaluator = recovered_evaluator if pool is None else None
        s_uni_future = None
    else:
        s_uni_future = None
        evaluator = StepEvaluator(
            tape,
            setting,
            step_index,
            transition_from=incumbent,
            cell_rekeyed_users=cell_rekeys,
            previously_served_users=previously_served,
            counter=counter,
            run_setting=active_run,
        )
        evaluator.evaluate_many(unique_selected)
        if base.configuration_id not in evaluator._evaluated:
            raise ProbeError("BASE has an invalid committed-profile power certificate")
        committed_decomposition, singleton_profiles = _committed_set_decomposition(
            base=base,
            selected=selections["FULL"],
            incumbent=incumbent,
            evaluator=evaluator,
            calibration=calibration,
            cell_rekeyed_users=cell_rekeys,
        )
        base_decomposition, _ = _committed_set_decomposition(
            base=base,
            selected=base,
            incumbent=incumbent,
            evaluator=evaluator,
            calibration=calibration,
            cell_rekeyed_users=cell_rekeys,
        )
        evaluated = dict(evaluator._evaluated)
    phase["validation"] = time.perf_counter() - started
    selection_wall_s = time.perf_counter() - decision_started
    # The wall at which the committed selection was fixed.  On a preemptive
    # timeout that instant is exactly the deadline; the extra time spent
    # draining the future is receipt bookkeeping, not decision time.
    committed_decision_wall_s = (
        DECISION_DEADLINE_S
        if validation_within_deadline is False
        else selection_wall_s
    )
    if validation_within_deadline is False or (
        selection_wall_s > DECISION_DEADLINE_S and not deadline_missed
    ):
        deadline_missed = True
        selections = apply_deadline_fallback(selections, base=base, missed=True)
        committed_decomposition = base_decomposition
        singleton_profiles = ()

    if s_uni_future is not None:
        (
            s_uni,
            s_uni_iterations,
            s_uni_wall_s,
            s_uni_missed,
            s_uni_termination,
            s_uni_profile,
            s_uni_evaluations,
        ) = s_uni_future.result()
        counter.boundary_evaluations += s_uni_evaluations
        pool.shutdown(wait=True)
        evaluated[s_uni_profile.config.configuration_id] = s_uni_profile
    elif pool is not None:
        (
            s_uni,
            s_uni_iterations,
            s_uni_wall_s,
            s_uni_missed,
            s_uni_termination,
            s_uni_profile,
            s_uni_evaluations,
        ) = pool.submit(
            _selection_worker_s_uni, S_UNI_COMPUTE_BUDGET_S
        ).result()
        counter.boundary_evaluations += s_uni_evaluations
        pool.shutdown(wait=True)
        evaluated[s_uni_profile.config.configuration_id] = s_uni_profile
    else:
        assert evaluator is not None
        s_uni, s_uni_iterations, s_uni_wall_s, s_uni_missed, s_uni_termination = (
            _s_uni_select(
                base=base,
                incumbent=incumbent,
                tape=tape,
                step_index=step_index,
                evaluator=selection_evaluator,
                calibration=calibration,
                compute_budget_s=S_UNI_COMPUTE_BUDGET_S,
                run_setting=active_run,
                cell_rekeyed_users=cell_rekeys,
            )
        )
        evaluator.evaluate(s_uni if not s_uni_missed else base)
        evaluated.update(evaluator._evaluated)
    phase["s_uni_comparator"] = s_uni_wall_s
    pre_fallback["S_UNI"] = s_uni.configuration_id
    # S_UNI is an independently budgeted comparator.  A coordinator miss
    # cannot discard a successful comparator result.
    selections["S_UNI"] = s_uni if not s_uni_missed else base
    c2_diagnostic_started = time.perf_counter()
    configuration_by_id = {row.configuration_id: row for row in catalog}
    c2_forecast_certificate = _c2_forecast_validity_certificate(
        tape=tape,
        setting=setting,
        anchor_step=step_index,
        carrier=carrier,
        immediate=configuration_by_id[pre_fallback["DROP_C2"]],
        continuation=configuration_by_id[pre_fallback["FULL"]],
        forecasts=forecasts,
        calibration=calibration,
        run_setting=active_run,
    )
    c2_forecast_certificate["tie_diagnostic"] = c2_tie_diagnostic
    phase["c2_forecast_validity_diagnostic"] = (
        time.perf_counter() - c2_diagnostic_started
    )
    base_profile = evaluated[base.configuration_id]
    full_profile = evaluated[selections["FULL"].configuration_id]
    range_diagnostic = _usable_energy_range_step(
        selected=full_profile,
        base=base,
        base_profile=base_profile,
        evaluated=evaluated,
    )
    selected_full_factors = factors.get(
        selections["FULL"].configuration_id,
        factors[base.configuration_id],
    )
    selected_full_factors = {
        **selected_full_factors,
        "committed_d_by_user": committed_decomposition.d_by_user,
        "committed_psi_A": committed_decomposition.interaction_bits,
        "committed_shapley_interaction_by_user": committed_decomposition.shapley_interaction_by_user,
        "credit_split": committed_decomposition.credit_split,
        "committed_joint_change_bits": committed_decomposition.joint_change_bits,
    }
    solver_residual_w_max = max(
        row.score.certificate_residual_w for row in evaluated.values()
    )
    # An update residual is not, without a contraction proof, an upper bound
    # on fixed-point error or on threshold-sensitive F.  Only an exactly fixed
    # floating-point update certifies zero here; all other cases fail closed
    # until the solver exports independently proved F bounds.
    certified_numerical_error_bits = (
        0.0 if solver_residual_w_max == 0.0 else None
    )
    exact_j1 = evaluated[j1.config.configuration_id]
    exact_u1 = evaluated[u1.config.configuration_id]
    j1_objective_margin_bits = float(
        _objective(exact_j1, calibration) - _objective(exact_u1, calibration)
    )
    j1_matched_qos, j1_qos_certificate = _anchor_qos_noninferior(
        exact_j1,
        (base_profile, exact_u1),
        incumbent,
        cell_rekeyed_users=cell_rekeys,
        previously_served_users=previously_served,
    )
    genuine_multi_user_witness = (
        j1.config.changed_users > 1
        and j1_matched_qos
        and certified_numerical_error_bits is not None
        and j1_objective_margin_bits > certified_numerical_error_bits
    )
    additive_interaction = None
    if (
        not deadline_missed
        and singleton_profiles
        and base_profile.bits > 0.0
        and base_profile.joules > 0.0
        and full_profile.joules > 0.0
    ):
        matched = matched_anchor_decomposition(
            base=(base_profile.outcome(),),
            selected=(full_profile.outcome(),),
            singleton_selected=tuple((row.outcome(),) for row in singleton_profiles),
        )
        additive_interaction = {
            "reference": "a0 pooled EE at this matched anchor",
            "sign_convention": "positive improves F=B-eta0*E relative to a0",
            "A_bits": float(matched.additive),
            "I_bits": float(matched.interaction),
            "delta_joint_bits": float(matched.joint_change),
            "g_A": float(matched.g_additive),
            "g_I": float(matched.g_interaction),
        }
    else:
        additive_interaction = {
            "reference": "a0 pooled EE at this matched anchor",
            "sign_convention": "positive improves F=B-eta0*E relative to a0",
            "A_bits": 0.0,
            "I_bits": 0.0,
            "delta_joint_bits": 0.0,
            "g_A": 0.0,
            "g_I": 0.0,
        }

    ledger_started = time.perf_counter()
    arm_rows = []
    opening_state = {
        "world_domain": tape.domain,
        "world_sha256": tape.digest,
        "step_index": step_index,
        "carrier": carrier,
        "incumbent_assignments": incumbent.assignments,
        "previously_served_users": previously_served,
        "selection_dependency_sha256": selection_dependency_sha256,
        "dependency_allowlist": list(SELECTION_DEPENDENCY_ALLOWLIST),
    }
    opening_state_sha256 = digest_payload(opening_state)
    for arm in ARMS:
        started = time.perf_counter()
        profile = evaluated[selections[arm].configuration_id]
        arm_rows.append(
            _arm_row(
                arm=arm,
                profile=profile,
                base=incumbent,
                cell_rekeyed_users=cell_rekeys,
                previously_served_users=previously_served,
                elapsed_s=time.perf_counter() - started,
            )
        )
        arm_rows[-1]["computation_deadline_s"] = DECISION_DEADLINE_S
        arm_rows[-1]["declared_worker_count"] = selection_workers
        arm_rows[-1]["opening_state_sha256"] = opening_state_sha256
        arm_rows[-1]["deadline_missed"] = (
            s_uni_missed
            if arm == "S_UNI"
            else deadline_missed
            if arm in SET_LEVEL_ARMS
            else False
        )
        if arm == "S_UNI":
            arm_rows[-1]["iteration_count"] = s_uni_iterations
            arm_rows[-1]["decoder_wall_s"] = s_uni_wall_s
            arm_rows[-1]["compute_budget_s"] = S_UNI_COMPUTE_BUDGET_S
            arm_rows[-1]["termination_certificate"] = s_uni_termination
    phase["ledger_receipts"] = time.perf_counter() - ledger_started
    phase["total_anchor"] = time.perf_counter() - anchor_started
    interaction_sum = sum(
        (Fraction(row["psi_A"]) for row in factors.values()), Fraction()
    )
    interaction_count = sum(
        1 for row in catalog if row.changed_users > 1
    )
    certificate_distribution: dict[str, int] = {}
    for profile in evaluated.values():
        certificate_distribution[profile.certificate_status] = (
            certificate_distribution.get(profile.certificate_status, 0) + 1
        )
    return {
        "step_index": step_index,
        "carrier": carrier,
        "rekey_eligible_user_boundaries": (
            len(base.assignments)
            if step_index > 0 and tape.steps[step_index].refresh_phase == 0
            else 0
        ),
        "arms": arm_rows,
        "c2_forecast_certificate": c2_forecast_certificate,
        "e1_certificate": {
            "candidate_census_complete": True,
            **catalogue_census,
            "candidate_count": len(catalog),
            "unilateral_count": len(unilateral_configs),
            "joint_count": len(joint_configs),
            "u1_configuration": u1.config.configuration_id,
            "j1_configuration": j1.config.configuration_id,
            "union_configuration": union.config.configuration_id,
            "genuine_multi_user_witness": genuine_multi_user_witness,
            "j1_beyond_base_and_u_all": genuine_multi_user_witness,
            "j1_objective_margin_bits": j1_objective_margin_bits,
            "certified_numerical_error_bits": certified_numerical_error_bits,
            "certified_numerical_error_status": (
                "EXACT_FIXED_POINT"
                if certified_numerical_error_bits is not None
                else "UNAVAILABLE_FAIL_CLOSED"
            ),
            "matched_qos_noninferior": j1_matched_qos,
            "matched_qos_certificate": j1_qos_certificate,
            "u_all_configuration": u1.config.configuration_id,
            "solver_residual_w_max": solver_residual_w_max,
        },
        "s0_certificate": {
            "nominal_information_only": True,
            "top_two_proposal_ids": sorted(
                row.configuration_id for row in catalog if row.kind == "s0-top-two"
            ),
            "evacuation_decoder": "frozen-complete-top2-combinations-v1",
        },
        "non_additive_interaction_bits": float(
            committed_decomposition.interaction_bits
        ),
        "non_additive_interaction_count": int(
            selections["FULL"].changed_users > 1
        ),
        "catalogue_interaction_sum_bits": float(interaction_sum),
        "catalogue_interaction_configuration_count": interaction_count,
        "factor_arm_formulas": {
            "ONLY_C1": "primary C1_m; secondary configuration_id",
            "ONLY_C1C2": "primary C1_m; secondary C2",
            "FULL": "primary C1_m+C3_m; secondary C2",
            "DROP_C1": "primary C3_m; secondary C2",
            "DROP_C2": "primary C1_m+C3_m; secondary configuration_id",
            "DROP_C3": "primary C1_m; secondary C2",
            "same_keys_for_ranking_pruning_guards_and_ties": True,
            "reporting_only_arms": list(REPORTING_ONLY_ARMS),
            "reporting_arms_enter_certificates": False,
            "reporting_arms_enter_admission": False,
        },
        "selected_full_set_score": {
            name: (
                float(value)
                if isinstance(value, Fraction)
                else value
                if isinstance(value, (int, float, str, bool)) or value is None
                else [[user, float(credit)] for user, credit in value]
            )
            for name, value in selected_full_factors.items()
        },
        "matched_anchor_decomposition": additive_interaction,
        "decomposition_contract": {
            "selection_time": "F_m at decision/forecast grid; d_i^m, Psi_A^m and V_CA only",
            "outcome": "realised 48-boundary F; labels, credit split and endpoint certificates only",
            "mixed": False,
            "interaction_labels_uncapped": True,
            "shapley_split_max_coalition_size": 4,
        },
        "forecast_margin_schema": f"{SCHEMA}-forecast-margin-row-v1",
        "forecast_margin_rows": list(forecast_receipts),
        "certificate_distribution": dict(sorted(certificate_distribution.items())),
        "service_guard": {
            "rule": "served-user count must not decrease versus BASE",
            "applied_arms": list(SET_LEVEL_ARMS),
            "not_applied_arms": [arm for arm in ARMS if arm not in SET_LEVEL_ARMS],
        },
        "opening_state_certificate": {
            **opening_state,
            "sha256": opening_state_sha256,
            "identical_across_all_arms": len(
                {row["opening_state_sha256"] for row in arm_rows}
            ) == 1,
        },
        "selection_approximations": {
            "causal_margin_adjusted_nominal_information_only": True,
            "fading_quantile_alpha": selection_fading_quantile_alpha,
            "c2_tie_diagnostic": c2_tie_diagnostic,
            "stage1_boundary_indices": [0],
            "selection_boundary_indices": list(selection_boundary_indices),
            "stage2_M": selection_stage2_m,
            "stage2_count": len(stage2),
            # The stage-4h extrapolated reserve is retired; the committed
            # validation is now bounded by a measured preemptive wait.
            "validation_reserve_s": None,
            "validation_deadline_model": "preemptive-measured-wait",
            "retired_stage4h_reserve_s": retired_reserve_s,
            "retired_stage4h_predicate_would_fall_back": (
                retired_predicate_would_fall_back
            ),
            "validation_rows": validation_rows,
            "validation_wait_budget_s": validation_wait_budget_s,
            "validation_within_deadline": validation_within_deadline,
            "elapsed_before_validation_s": elapsed_before_validation,
            "stage1_reused_from_catalogue_ranking": stage1_reused_ids,
            "stage1_evaluated_configuration_count": stage1_evaluated_count,
            "parallel_execution": parallel_used,
            "deterministic_sharding": "catalogue-index-mod-worker-count",
            "stage1_shards": list(stage1_shards),
            "stage2_shards": list(stage2_shards),
            "pre_fallback_selections": pre_fallback,
            **stage2_top1_diagnostic,
            "committed_endpoint_boundaries": 48,
        },
        "coordinator": {
            "deadline_s": DECISION_DEADLINE_S,
            "declared_worker_count": selection_workers,
            "effective_worker_count": evaluation_workers,
            "whole_path_wall_s": selection_wall_s,
            "committed_decision_wall_s": committed_decision_wall_s,
            "deadline_missed": deadline_missed,
            "fallback": "BASE" if deadline_missed else None,
            "s_uni_iterations": s_uni_iterations,
            "s_uni_wall_s": s_uni_wall_s,
            "s_uni_compute_budget_s": S_UNI_COMPUTE_BUDGET_S,
            "s_uni_termination_certificate": s_uni_termination,
        },
        "phase_seconds": phase,
        "successor_usable_energy_range": range_diagnostic,
        "physical_boundary_evaluations": counter.boundary_evaluations - counter_start,
    }


def _summarize_energy_range(steps: Sequence[Mapping[str, object]]) -> dict[str, object]:
    rows = [step["successor_usable_energy_range"] for step in steps]
    mode_counts: dict[str, int] = {}
    by_beam: dict[str, float] = {}
    for row in rows:
        for name, count in row["selected_acm_mode_counts"].items():  # type: ignore[union-attr]
            mode_counts[str(name)] = mode_counts.get(str(name), 0) + int(count)
        for beam, value in row["best_feasible_reassignment_dc_energy_change_j_by_beam"].items():  # type: ignore[union-attr]
            by_beam[str(beam)] = max(by_beam.get(str(beam), -math.inf), float(value))
    plateau = sum(int(row["se_plateau_user_steps"]) for row in rows)
    users = sum(int(row["user_step_observations"]) for row in rows)
    cap_hits = sum(int(row["rf_cap_hits"]) for row in rows)
    rf = sum(int(row["rf_transmission_observations"]) for row in rows)
    return {
        "selected_acm_mode_counts": dict(sorted(mode_counts.items())),
        "se_plateau_user_step_share": 0.0 if users == 0 else plateau / users,
        "rf_cap_transmission_share": 0.0 if rf == 0 else cap_hits / rf,
        "best_feasible_reassignment_dc_energy_change_j_by_beam": dict(sorted(by_beam.items())),
        "thresholds_applied": False,
    }


def _summarize_steps(steps: Sequence[Mapping[str, object]], calibration: CalibrationValues) -> dict[str, object]:
    by_arm: dict[str, dict[str, object]] = {}
    for arm in ARMS:
        rows = [row for step in steps for row in step["arms"] if row["arm"] == arm]  # type: ignore[index]
        bits = math.fsum(float(row["bits"]) for row in rows)
        joules = math.fsum(float(row["joules"]) for row in rows)
        availability_served = math.fsum(
            float(row["qos_additive"]["availability_served"]) for row in rows  # type: ignore[index]
        )
        availability_opportunities = math.fsum(
            float(row["qos_additive"]["availability_opportunities"]) for row in rows  # type: ignore[index]
        )
        handover_events = math.fsum(
            float(row["qos_additive"]["handover_events"]) for row in rows  # type: ignore[index]
        )
        handover_opportunities = math.fsum(
            float(row["qos_additive"]["handover_opportunities"]) for row in rows  # type: ignore[index]
        )
        phi_cost_numerator = math.fsum(
            float(row["qos_additive"]["phi_cost_numerator"]) for row in rows  # type: ignore[index]
        )
        phi_cost_denominator = math.fsum(
            float(row["qos_additive"]["phi_cost_denominator"]) for row in rows  # type: ignore[index]
        )
        by_arm[arm] = {
            "arm_payloads_sha256": digest_payload(rows),
            "bits": bits,
            "joules": joules,
            "pooled_ee_bits_per_j": None if joules == 0 else bits / joules,
            "pa_j": math.fsum(float(row["energy"]["pa_j"]) for row in rows),  # type: ignore[index]
            "standby_j": math.fsum(float(row["energy"]["standby_j"]) for row in rows),  # type: ignore[index]
            "circuit_j": math.fsum(float(row["energy"]["circuit_j"]) for row in rows),  # type: ignore[index]
            "baseband_j": math.fsum(float(row["energy"]["baseband_j"]) for row in rows),  # type: ignore[index]
            "availability": availability_served / availability_opportunities,
            "decoding_availability": math.fsum(float(row["decoding_availability"]) for row in rows) / len(rows),
            "partial_service_availability": math.fsum(float(row["partial_service_availability"]) for row in rows) / len(rows),
            "useful_availability": math.fsum(float(row["useful_availability"]) for row in rows) / len(rows),
            "phi_signalling_qos_preference": math.fsum(
                float(row["phi_signalling_qos_preference"]) for row in rows
            ),
            "phi_priced_handover_cost_per_user_step": phi_cost_numerator / phi_cost_denominator,
            "qos_additive": {
                "availability_served": availability_served,
                "availability_opportunities": availability_opportunities,
                "handover_events": handover_events,
                "handover_opportunities": handover_opportunities,
                "phi_cost_numerator": phi_cost_numerator,
                "phi_cost_denominator": phi_cost_denominator,
            },
            "handovers": {
                kind: sum(int(row["handovers"][kind]) for row in rows)  # type: ignore[index]
                for kind in ("beam_change", "satellite_change", "cell_rekey", "initial_entry", "reentry", "exit")
            },
            "corrected_boundary_conditional_rekey": {
                "rekeys": sum(int(row["handovers"]["cell_rekey"]) for row in rows),  # type: ignore[index]
                "eligible_user_boundaries": sum(
                    int(step["rekey_eligible_user_boundaries"]) for step in steps
                ),
                "rate": corrected_boundary_rekey_rate(
                    rekeys=sum(int(row["handovers"]["cell_rekey"]) for row in rows),  # type: ignore[index]
                    eligible_boundaries=sum(
                        int(step["rekey_eligible_user_boundaries"]) for step in steps
                    ),
                ),
                "numerator_source": "physical event ledger",
            },
            "handover_rate_per_user_decision": handover_events / handover_opportunities,
            "changed_users": sum(int(row["changed_users"]) for row in rows),
            "decision_time_tail_s": {
                "p50": float(np.quantile([row["decision_time_s"] for row in rows], 0.5)),
                "p95": float(np.quantile([row["decision_time_s"] for row in rows], 0.95)),
                "max": max(float(row["decision_time_s"]) for row in rows),
            },
            "rate_tail": {
                key: float(np.quantile([row["rate_tail"][key] for row in rows], 0.5))  # type: ignore[index]
                for key in ("p05_bps", "p50_bps", "p95_bps")
            },
            "required_power_w_max_distribution": {
                "min": min(float(row["required_power_w_max"]) for row in rows),
                "p50": float(np.quantile([row["required_power_w_max"] for row in rows], 0.5)),
                "max": max(float(row["required_power_w_max"]) for row in rows),
            },
            "acm_mode_counts": {
                mode: sum(int(row["acm_mode_counts"].get(mode, 0)) for row in rows)
                for mode in sorted(
                    {
                        mode
                        for row in rows
                        for mode in row["acm_mode_counts"]
                    }
                )
            },
            "acm_causal_objects": {
                "m_target_counts": {
                    mode: sum(
                        int(row["acm_causal_objects"]["m_target_counts"].get(mode, 0))
                        for row in rows
                    )
                    for mode in sorted(
                        {
                            mode
                            for row in rows
                            for mode in row["acm_causal_objects"]["m_target_counts"]
                        }
                    )
                },
                "m_tx_counts": {
                    mode: sum(
                        int(row["acm_causal_objects"]["m_tx_counts"].get(mode, 0))
                        for row in rows
                    )
                    for mode in sorted(
                        {
                            mode
                            for row in rows
                            for mode in row["acm_causal_objects"]["m_tx_counts"]
                        }
                    )
                },
                "realised_outcome": {
                    outcome: sum(
                        int(row["acm_causal_objects"]["realised_outcome"][outcome])
                        for row in rows
                    )
                    for outcome in ("decoded", "outage")
                },
            },
            "certificate_distribution": {
                status: sum(row["certificate_status"] == status for row in rows)
                for status in ("FIXED", "CONVERGED", "CONVERGED_SLOW", "INVALID")
            },
            "rf_cap_share": (
                sum(int(row["rf_cap_hits"]) for row in rows)
                / max(1, sum(int(row["rf_transmission_observations"]) for row in rows))
            ),
        }
    marginals = {}
    failed = []
    for name, (full_name, drop_name) in MARGINALS.items():
        full, drop = by_arm[full_name], by_arm[drop_name]
        full_ee, drop_ee = full["pooled_ee_bits_per_j"], drop["pooled_ee_bits_per_j"]
        delta_bits = float(full["bits"]) - float(drop["bits"])
        delta_joules = float(full["joules"]) - float(drop["joules"])
        delta_ee = None if full_ee is None or drop_ee is None else float(full_ee) - float(drop_ee)
        if name == "C2":
            validity_rows = [
                step["c2_forecast_certificate"] for step in steps
            ]
            validity_pass = all(bool(certificate["valid"]) for certificate in validity_rows)
            tie_count = sum(
                bool(step["selection_approximations"]["c2_tie_diagnostic"]["FULL"]["tie_present"])
                for step in steps
            )
        else:
            validity_pass = True
            tie_count = 0
        row = {
            "full": full_name,
            "drop": drop_name,
            "delta_bits": delta_bits,
            "delta_joules": delta_joules,
            "delta_ee_bits_per_j": delta_ee,
            "surplus_at_calibration_price_bits": delta_bits - float(calibration.eta_ref) * delta_joules,
            "failed": (
                not validity_pass
                if name == "C2"
                else delta_ee is None or delta_ee <= 0.0
            ),
        }
        if name == "C2":
            row.update(
                {
                    "certificate_kind": "three-offset forecast validity",
                    "forecast_validity_pass": validity_pass,
                    "zero_set_level_marginal_accepted": delta_ee == 0.0,
                    "tie_count": tie_count,
                    "tie_frequency": tie_count / len(steps),
                }
            )
        if row["failed"]:
            failed.append(name)
        marginals[name] = row
    return {
        "arms": by_arm,
        "marginals": marginals,
        "which_marginal_failed": failed,
        "non_additive_interaction_bits": math.fsum(float(step["non_additive_interaction_bits"]) for step in steps),
        "matched_anchor_decomposition": {
            "anchor_count": len(steps),
            "A_bits": math.fsum(
                float(step["matched_anchor_decomposition"]["A_bits"]) for step in steps
            ),
            "I_bits": math.fsum(
                float(step["matched_anchor_decomposition"]["I_bits"]) for step in steps
            ),
            "delta_joint_bits": math.fsum(
                float(step["matched_anchor_decomposition"]["delta_joint_bits"])
                for step in steps
            ),
            "negative_interaction_anchor_share": sum(
                float(step["matched_anchor_decomposition"]["g_I"]) < 0.0
                for step in steps
            ) / len(steps),
            "by_anchor": [step["matched_anchor_decomposition"] for step in steps],
        },
        "outage_runs": _outage_runs(steps),
        "handover_totals": {
            kind: sum(
                int(row["handovers"][kind])  # type: ignore[index]
                for step in steps
                for row in step["arms"]  # type: ignore[index]
            )
            for kind in ("beam_change", "satellite_change", "cell_rekey", "initial_entry", "reentry", "exit")
        },
        "corrected_boundary_conditional_rekey_by_arm": {
            arm: by_arm[arm]["corrected_boundary_conditional_rekey"] for arm in ARMS
        },
    }


def pooled_ratio_cluster_bootstrap(
    clusters: Sequence[Mapping[str, float]],
    *,
    draws: int = 10_000,
    seed: int = 0x0252026,
) -> dict[str, object]:
    """One-way paired-date bootstrap of pooled EE and additive QoS counts."""

    if type(draws) is not int or draws < 1 or len(clusters) < 2:
        raise ProbeError("cluster bootstrap needs at least two clusters and one draw")
    fields = (
        "full_bits",
        "full_joules",
        "comparator_bits",
        "comparator_joules",
        "full_availability_served",
        "full_availability_opportunities",
        "comparator_availability_served",
        "comparator_availability_opportunities",
        "full_phi_numerator",
        "full_phi_denominator",
        "comparator_phi_numerator",
        "comparator_phi_denominator",
        "full_handover_events",
        "full_handover_opportunities",
        "comparator_handover_events",
        "comparator_handover_opportunities",
    )
    def value(row: Mapping[str, float], field: str) -> float:
        if field in row:
            return float(row[field])
        legacy = {
            "full_availability_served": float(row.get("full_qos", 0.0)),
            "full_availability_opportunities": 1.0,
            "comparator_availability_served": float(row.get("comparator_qos", 0.0)),
            "comparator_availability_opportunities": 1.0,
            "full_phi_numerator": float(row.get("full_phi_cost_per_user_step", max(0.0, -float(row.get("full_phi", 0.0))))),
            "full_phi_denominator": 1.0,
            "comparator_phi_numerator": float(row.get("comparator_phi_cost_per_user_step", max(0.0, -float(row.get("comparator_phi", 0.0))))),
            "comparator_phi_denominator": 1.0,
            "full_handover_events": float(row.get("full_handover_rate", 0.0)),
            "full_handover_opportunities": 1.0,
            "comparator_handover_events": float(row.get("comparator_handover_rate", 0.0)),
            "comparator_handover_opportunities": 1.0,
        }
        if field in legacy:
            return legacy[field]
        raise ProbeError(f"bootstrap row lacks {field}")

    values = np.asarray(
        [[value(row, field) for field in fields] for row in clusters],
        dtype=np.float64,
    )
    if not np.all(np.isfinite(values)) or np.any(values < 0.0):
        raise ProbeError("bootstrap inputs must be finite and physical")
    denominator_columns = (1, 3, 5, 7, 9, 11, 13, 15)
    if np.any(values[:, denominator_columns] <= 0.0):
        raise ProbeError("bootstrap additive denominators must be positive")

    rng = np.random.default_rng(seed)
    sampled_rows = []
    attempts = 0
    while len(sampled_rows) < draws and attempts < draws * 20:
        attempts += 1
        indices = rng.integers(0, len(values), size=len(values))
        totals = values[indices].sum(axis=0)
        # A zero-bit cluster is valid input.  Degenerate all-zero resamples
        # are discarded/redrawn so the primary ratio interval stays defined.
        if totals[0] <= 0.0 or totals[2] <= 0.0:
            continue
        sampled_rows.append(totals)
    if len(sampled_rows) != draws:
        raise ProbeError("bootstrap could not form enough positive pooled-bit draws")
    sampled = np.asarray(sampled_rows, dtype=np.float64)
    full_ee = sampled[:, 0] / sampled[:, 1]
    comparator_ee = sampled[:, 2] / sampled[:, 3]
    contrast = full_ee / comparator_ee - 1.0
    qos_delta = sampled[:, 4] / sampled[:, 5] - sampled[:, 6] / sampled[:, 7]
    def relative_change(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
        result = np.full(numerator.shape, np.inf, dtype=np.float64)
        positive = denominator > 0.0
        result[positive] = numerator[positive] / denominator[positive] - 1.0
        result[(denominator == 0.0) & (numerator == 0.0)] = 0.0
        return result

    full_phi_rate = sampled[:, 8] / sampled[:, 9]
    comparator_phi_rate = sampled[:, 10] / sampled[:, 11]
    phi_relative = relative_change(full_phi_rate, comparator_phi_rate)
    full_handover_rate = sampled[:, 12] / sampled[:, 13]
    comparator_handover_rate = sampled[:, 14] / sampled[:, 15]
    handover_relative = relative_change(full_handover_rate, comparator_handover_rate)

    totals = values.sum(axis=0)
    if totals[0] <= 0.0 or totals[2] <= 0.0:
        raise ProbeError("observed pooled bits must be positive for an EE contrast")
    observed = (totals[0] / totals[1]) / (totals[2] / totals[3]) - 1.0
    observed_qos = totals[4] / totals[5] - totals[6] / totals[7]
    observed_phi = float(relative_change(totals[8:9] / totals[9:10], totals[10:11] / totals[11:12])[0])
    observed_handovers = float(relative_change(totals[12:13] / totals[13:14], totals[14:15] / totals[15:16])[0])
    ee_lower = float(np.quantile(contrast, 0.025))
    ee_upper = float(np.quantile(contrast, 0.975))
    qos_lower = float(np.quantile(qos_delta, 0.025))
    phi_upper = float(np.quantile(phi_relative, 0.975))
    handover_upper = float(np.quantile(handover_relative, 0.975))
    return {
        "schema": f"{SCHEMA}-pooled-ratio-cluster-bootstrap",
        "clusters": len(values),
        "draws": draws,
        "seed": seed,
        "estimator": "paired resample; recompute pooled ratios from additive date-cluster totals within every draw",
        "interval_convention": "central 95% percentile interval [q0.025,q0.975]",
        "contrast_relative": observed,
        "contrast_lower_95_relative": ee_lower,
        "contrast_upper_95_relative": ee_upper,
        "contrast_percentage_points": 100.0 * observed,
        "contrast_lower_95_percentage_points": 100.0 * ee_lower,
        "contrast_upper_95_percentage_points": 100.0 * ee_upper,
        "prespecified_margin_relative": 0.005,
        "ee_margin_pass": ee_lower > 0.005,
        "qos_availability_delta": observed_qos,
        "qos_availability_lower_95": qos_lower,
        "phi_priced_handover_cost_relative_change": observed_phi,
        "phi_priced_handover_cost_relative_upper_95": phi_upper,
        "handover_rate_relative_change": observed_handovers,
        "handover_rate_relative_upper_95": handover_upper,
        "availability_margin_fraction": -0.005,
        "relative_cost_margin": 0.05,
        "qos_noninferior": qos_lower > -0.005 and phi_upper < 0.05 and handover_upper < 0.05,
        "additive_fields_pooled_inside_each_draw": list(fields[4:]),
        "zero_bit_cluster_disposition": "valid for primary; discard/redraw only an all-zero pooled-bit resample",
        "supplementary_paired_world_log_ee": (
            {
                "status": "UNDEFINED_ZERO_BIT_CLUSTER",
                "not_a_substitute_for_pooled_ratio_interval": True,
            }
            if np.any(values[:, 0] == 0.0) or np.any(values[:, 2] == 0.0)
            else {
                "status": "DEFINED",
                **(lambda paired, sampled_log: {
                    "mean_log_ratio": float(paired.mean()),
                    "lower_95_percentage_points": float(100.0 * np.expm1(np.quantile(sampled_log, 0.025))),
                    "upper_95_percentage_points": float(100.0 * np.expm1(np.quantile(sampled_log, 0.975))),
                })(
                    np.log((values[:, 0] / values[:, 1]) / (values[:, 2] / values[:, 3])),
                    np.log((values[:, 0] / values[:, 1]) / (values[:, 2] / values[:, 3]))[
                        np.random.default_rng(seed ^ 0x11AACC).integers(
                            0, len(values), size=(draws, len(values))
                        )
                    ].mean(axis=1),
                ),
                "not_a_substitute_for_pooled_ratio_interval": True,
            }
        ),
    }


def _positive_paired_ratio_values(blocks: Sequence[Mapping[str, object]]) -> np.ndarray:
    """Validate the four positive fields shared by log-based estimators."""

    values = np.asarray(
        [
            [
                float(row["full_bits"]),
                float(row["full_joules"]),
                float(row["comparator_bits"]),
                float(row["comparator_joules"]),
            ]
            for row in blocks
        ],
        dtype=np.float64,
    )
    if not np.all(np.isfinite(values)) or np.any(values <= 0.0):
        raise ProbeError("paired log-contrast bits and energy must be finite and positive")
    return values


def delta_method_log_contrast(
    blocks: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Reporting-only paired-block delta interval for the pooled log contrast."""

    if len(blocks) < 2:
        raise ProbeError("delta-method interval needs at least two paired blocks")
    raw = np.asarray(
        [
            [
                float(row["full_bits"]),
                float(row["full_joules"]),
                float(row["comparator_bits"]),
                float(row["comparator_joules"]),
            ]
            for row in blocks
        ],
        dtype=np.float64,
    )
    if np.any(raw[:, (0, 2)] == 0.0):
        return {
            "schema": f"{SCHEMA}-paired-block-delta-log-contrast",
            "status": "UNDEFINED_ZERO_BIT_CLUSTER",
            "reporting_only": True,
        }
    values = _positive_paired_ratio_values(blocks)
    means = values.mean(axis=0)
    log_contrast = math.log(means[0] / means[1]) - math.log(means[2] / means[3])
    psi = (
        values[:, 0] / means[0]
        - values[:, 1] / means[1]
        - values[:, 2] / means[2]
        + values[:, 3] / means[3]
    )
    standard_error = float(np.std(psi, ddof=1) / math.sqrt(len(values)))
    low_log = log_contrast - 1.959963984540054 * standard_error
    high_log = log_contrast + 1.959963984540054 * standard_error
    return {
        "schema": f"{SCHEMA}-paired-block-delta-log-contrast",
        "status": "DEFINED",
        "blocks": len(values),
        "formula": "psi=(BF/mu_BF-EF/mu_EF)-(BD/mu_BD-ED/mu_ED)",
        "mean_log_ratio": log_contrast,
        "standard_error_log_ratio": standard_error,
        "contrast_percentage_points": 100.0 * math.expm1(log_contrast),
        "lower_95_percentage_points": 100.0 * math.expm1(low_log),
        "upper_95_percentage_points": 100.0 * math.expm1(high_log),
        "reporting_only": True,
    }


def two_way_pigeonhole_bootstrap(
    blocks: Sequence[Mapping[str, object]],
    *,
    draws: int = 10_000,
    seed: int = 0x0252026,
) -> dict[str, object]:
    """Two-way date x learner-seed bootstrap with arm-paired weights.

    Every draw applies the same product weight to FULL and its comparator,
    pools all additive numerators/denominators, and recomputes every ratio.
    """

    if type(draws) is not int or draws < 1 or len(blocks) < 2:
        raise ProbeError("pigeonhole bootstrap needs at least two blocks and one draw")
    dates = sorted({str(row["tle_date"]) for row in blocks})
    seeds = sorted({int(row["learner_seed"]) for row in blocks})
    if not dates or not seeds:
        raise ProbeError("pigeonhole bootstrap needs both clustering dimensions")
    date_index = {value: index for index, value in enumerate(dates)}
    seed_index = {value: index for index, value in enumerate(seeds)}
    core = np.asarray(
        [
            [
                float(row["full_bits"]),
                float(row["full_joules"]),
                float(row["comparator_bits"]),
                float(row["comparator_joules"]),
            ]
            for row in blocks
        ],
        dtype=np.float64,
    )
    if not np.all(np.isfinite(core)) or np.any(core < 0.0) or np.any(core[:, (1, 3)] <= 0.0):
        raise ProbeError("pigeonhole core inputs must be finite with positive energy")

    def get(row: Mapping[str, object], name: str, fallback: str, default: float) -> float:
        return float(row[name]) if name in row else float(row.get(fallback, default))

    qos = np.asarray(
        [
            [
                get(row, "full_availability_served", "full_qos", 0.0),
                get(row, "full_availability_opportunities", "_missing", 1.0),
                get(row, "comparator_availability_served", "comparator_qos", 0.0),
                get(row, "comparator_availability_opportunities", "_missing", 1.0),
                get(row, "full_phi_numerator", "full_phi_cost_per_user_step", max(0.0, -float(row.get("full_phi", 0.0)))),
                get(row, "full_phi_denominator", "_missing", 1.0),
                get(row, "comparator_phi_numerator", "comparator_phi_cost_per_user_step", max(0.0, -float(row.get("comparator_phi", 0.0)))),
                get(row, "comparator_phi_denominator", "_missing", 1.0),
                get(row, "full_handover_events", "full_handover_rate", 0.0),
                get(row, "full_handover_opportunities", "_missing", 1.0),
                get(row, "comparator_handover_events", "comparator_handover_rate", 0.0),
                get(row, "comparator_handover_opportunities", "_missing", 1.0),
            ]
            for row in blocks
        ],
        dtype=np.float64,
    )
    values = np.concatenate((core, qos), axis=1)
    if not np.all(np.isfinite(qos)) or np.any(qos < 0.0) or np.any(qos[:, (1, 3, 5, 7, 9, 11)] <= 0.0):
        raise ProbeError("pigeonhole QoS counts must be finite additive quantities")
    row_dates = np.asarray([date_index[str(row["tle_date"])] for row in blocks])
    row_seeds = np.asarray([seed_index[int(row["learner_seed"])] for row in blocks])
    rng = np.random.default_rng(seed)
    sampled_rows = []
    attempts = 0
    while len(sampled_rows) < draws and attempts < draws * 20:
        attempts += 1
        date_weights = rng.multinomial(len(dates), np.full(len(dates), 1.0 / len(dates)))
        seed_weights = rng.multinomial(len(seeds), np.full(len(seeds), 1.0 / len(seeds)))
        weights = date_weights[row_dates] * seed_weights[row_seeds]
        totals = (values * weights[:, None]).sum(axis=0)
        if totals[0] <= 0.0 or totals[2] <= 0.0:
            continue
        sampled_rows.append(totals)
    if len(sampled_rows) != draws:
        raise ProbeError("pigeonhole bootstrap could not form enough nonempty resamples")
    sampled = np.asarray(sampled_rows, dtype=np.float64)
    interval = (sampled[:, 0] / sampled[:, 1]) / (sampled[:, 2] / sampled[:, 3]) - 1.0
    availability = sampled[:, 4] / sampled[:, 5] - sampled[:, 6] / sampled[:, 7]

    def relative(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
        result = np.full(numerator.shape, np.inf)
        positive = denominator > 0.0
        result[positive] = numerator[positive] / denominator[positive] - 1.0
        result[(numerator == 0.0) & (denominator == 0.0)] = 0.0
        return result

    phi = relative(sampled[:, 8] / sampled[:, 9], sampled[:, 10] / sampled[:, 11])
    handover = relative(sampled[:, 12] / sampled[:, 13], sampled[:, 14] / sampled[:, 15])
    totals = values.sum(axis=0)
    observed = (totals[0] / totals[1]) / (totals[2] / totals[3]) - 1.0
    availability_lower = float(np.quantile(availability, 0.025))
    phi_upper = float(np.quantile(phi, 0.975))
    handover_upper = float(np.quantile(handover, 0.975))
    lower = float(np.quantile(interval, 0.025))
    upper = float(np.quantile(interval, 0.975))
    return {
        "schema": f"{SCHEMA}-two-way-pigeonhole-bootstrap",
        "tle_dates": len(dates),
        "learner_seeds": len(seeds),
        "draws": draws,
        "seed": seed,
        "estimator": "two-way pigeonhole date x learner seed; arms paired; additive ratios recomputed per draw",
        "interval_convention": "central 95% percentile interval [q0.025,q0.975]",
        "contrast_relative": observed,
        "contrast_lower_95_relative": lower,
        "contrast_upper_95_relative": upper,
        "contrast_percentage_points": 100.0 * observed,
        "lower_95_percentage_points": 100.0 * lower,
        "upper_95_percentage_points": 100.0 * upper,
        "prespecified_margin_relative": 0.005,
        "ee_margin_pass": lower > 0.005,
        "qos_availability_lower_95": availability_lower,
        "phi_priced_handover_cost_relative_upper_95": phi_upper,
        "handover_rate_relative_upper_95": handover_upper,
        "qos_noninferior": availability_lower > -0.005 and phi_upper < 0.05 and handover_upper < 0.05,
        "zero_bit_cluster_disposition": "valid for primary; discard/redraw only an all-zero pooled-bit resample",
        "eligible_as_primary_for_learner_experiments": True,
    }


def uncertainty_estimate(
    blocks: Sequence[Mapping[str, object]],
    *,
    learner_experiment: bool,
    draws: int = 10_000,
    seed: int = 0x0252026,
) -> dict[str, object]:
    """Dispatch the v1.5 primary estimator by experiment type."""

    if learner_experiment:
        primary = two_way_pigeonhole_bootstrap(blocks, draws=draws, seed=seed)
    else:
        # A date is the resampling unit.  If callers supply multiple rows for
        # one date, pool every additive field before entering the bootstrap.
        # This also makes accidental learner-seed pseudoreplication impossible
        # in the learner-free physics path.
        grouped: dict[str, list[Mapping[str, object]]] = {}
        for index, row in enumerate(blocks):
            grouped.setdefault(str(row.get("tle_date", index)), []).append(row)
        date_clusters: list[dict[str, float]] = []
        identifiers = {"tle_date", "learner_seed"}
        for rows in grouped.values():
            fields = set().union(*(set(row) for row in rows)) - identifiers
            date_clusters.append(
                {
                    field: math.fsum(float(row[field]) for row in rows if field in row)
                    for field in fields
                }
            )
        primary = pooled_ratio_cluster_bootstrap(
            date_clusters, draws=draws, seed=seed
        )
    return {
        "primary": primary,
        "primary_estimator": "two-way-pigeonhole" if learner_experiment else "one-way-date-bootstrap",
        "supplementary_delta_method": delta_method_log_contrast(blocks),
    }


def _outage_runs(steps: Sequence[Mapping[str, object]]) -> dict[str, int]:
    result = {}
    for arm in ARMS:
        longest = current = 0
        for step in steps:
            row = next(row for row in step["arms"] if row["arm"] == arm)  # type: ignore[index]
            outage = not all(bool(value) for value in row["served_PHY"].values()) if row["served_PHY"] else True  # type: ignore[union-attr]
            current = current + 1 if outage else 0
            longest = max(longest, current)
        result[arm] = longest
    return result


def assert_matrix_conformance(receipt: Mapping[str, object]) -> None:
    """Shared fail-closed receipt suite used by every comparative harness."""

    if receipt.get("schema") != UNIT_SCHEMA:
        raise ProbeError("unit receipt schema is not the stage-4c conformance schema")
    if receipt.get("arms") != list(ARMS):
        raise ProbeError("unit receipt arm inventory is not exact")
    for field in (
        "provider_source_sha256",
        "code_authority_sha256",
        "world_manifest_sha256",
        "calibration_sha256",
    ):
        if not isinstance(receipt.get(field), str) or len(receipt[field]) != 64:
            raise ProbeError(f"unit receipt authority field {field} is incomplete")
    steps = receipt.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ProbeError("unit receipt has no anchor rows")
    for step in steps:
        if [row["arm"] for row in step["arms"]] != list(ARMS):
            raise ProbeError("anchor arm order is not exact")
        if step["selection_approximations"]["committed_endpoint_boundaries"] != 48:
            raise ProbeError("committed endpoint is not the exact 48-boundary endpoint")
        if step["coordinator"]["deadline_s"] != DECISION_DEADLINE_S:
            raise ProbeError("coordinator deadline drifted")
        if step["forecast_margin_schema"] != f"{SCHEMA}-forecast-margin-row-v1":
            raise ProbeError("forecast schema is unstamped")
        if not step["opening_state_certificate"]["identical_across_all_arms"]:
            raise ProbeError("arms did not share one certified opening state")
        if step["service_guard"]["applied_arms"] != list(SET_LEVEL_ARMS):
            raise ProbeError("service-guard capability declaration drifted")
        opening = dict(step["opening_state_certificate"])
        declared = opening.pop("sha256", None)
        identical = opening.pop("identical_across_all_arms", None)
        if identical is not True or tuple(opening["dependency_allowlist"]) != SELECTION_DEPENDENCY_ALLOWLIST:
            raise ProbeError("opening-state dependency allowlist drifted")
        if set(opening) != {
            "world_domain", "world_sha256", "step_index", "carrier",
            "incumbent_assignments", "previously_served_users",
            "selection_dependency_sha256", "dependency_allowlist",
        } or declared != digest_payload(opening):
            raise ProbeError("opening-state certificate has hidden or mutated dependencies")
        by_name = {row["arm"]: row for row in step["arms"]}
        null_row, base_row = by_name["NULL"], by_name[ALL_NEUTRAL_CONTROL]
        invariant_fields = (
            "configuration_id", "bits", "joules", "energy", "served_PHY",
            "rate_target_attained", "rate_target_feasible", "handovers",
            "prior_current_identities", "certificate_status",
        )
        if any(null_row[name] != base_row[name] for name in invariant_fields):
            raise ProbeError("NULL is not physically identical to BASE")


def run_unit(
    *,
    setting: PhysicsSetting,
    world_index: int,
    executed_steps: int = 30,
    anchor_stride: int = 1,
    smoke_not_matrix: bool = False,
    attempt_id: str | None = None,
    calibration: CalibrationValues | None = None,
    expected_world_digest: str | None = None,
    expected_world_manifest: Mapping[str, object] | None = None,
    run_setting: SealedRunSetting | None = None,
    prepared_tape: ExogenousWorldTape | None = None,
    selection_workers: int = DECLARED_WORKERS,
    selection_boundary_indices: tuple[int, ...] = SELECTION_BOUNDARY_INDICES,
    selection_stage2_m: int = SELECTION_STAGE2_M,
    anchor_limit: int | None = None,
    selection_fading_quantile_alpha: float | None = 0.10,
    sweep_panel: str | None = None,
    sweep_x_value: object | None = None,
) -> dict[str, object]:
    if (
        type(executed_steps) is not int
        or not 1 <= executed_steps <= 30
        or type(anchor_stride) is not int
        or anchor_stride < 1
        or (
            anchor_limit is not None
            and (type(anchor_limit) is not int or anchor_limit < 1)
        )
    ):
        raise ProbeError(
            "executed_steps must be 1..30, anchor stride positive, and anchor limit positive"
        )
    if smoke_not_matrix:
        if world_index != 1:
            raise ProbeError("development smoke has exactly one quarantined world")
        domain = SMOKE_WORLD_DOMAINS[0]
    elif expected_world_manifest is None and prepared_tape is not None:
        allowed_nonformal = (
            KAT_WORLD_DOMAINS
            + SYNTHETIC_WORLD_DOMAINS
            + PROVIDER_KAT_WORLD_DOMAINS
        )
        if prepared_tape.domain not in allowed_nonformal:
            raise ProbeError("prepared nonformal tape is outside a KAT namespace")
        domain = prepared_tape.domain
    elif expected_world_manifest is None:
        if world_index < 1 or world_index > len(DEVELOPMENT_WORLD_DOMAINS):
            raise ProbeError("world index is outside the development domain inventory")
        domain = DEVELOPMENT_WORLD_DOMAINS[world_index - 1]
    else:
        domain = _world_domain(world_index)
    run_setting = run_setting_for(setting.label) if run_setting is None else run_setting
    if run_setting.base_cell != setting.label:
        raise ProbeError("run setting does not bind the requested physical cell")
    if (sweep_panel is None) != (sweep_x_value is None):
        raise ProbeError("sweep panel and x-value must be supplied together")
    if sweep_panel is not None:
        _declared_x, expected_run_id = _sweep_point(sweep_panel, sweep_x_value)
        if expected_run_id != run_setting.run_id:
            raise ProbeError("sweep point does not match the unit run setting")
    if prepared_tape is None:
        tape = build_world_tape(
            domain=domain,
            provider=_provider_for_run(run_setting),
            steps=executed_steps + 3,
            start_time_s=0.0,
        )
    else:
        tape = prepared_tape
        if tape.domain != domain or len(tape.steps) != executed_steps + 3:
            raise ProbeError("prepared tape disagrees with the requested unit")
    if expected_world_digest is not None and tape.digest != expected_world_digest:
        raise ProbeError("rebuilt world tape disagrees with the pre-outcome sealed manifest")
    if expected_world_manifest is not None and tape.manifest() != dict(expected_world_manifest):
        raise ProbeError("rebuilt provider protocol outputs disagree with the sealed manifest")
    calibration = _calibrate(setting, run_setting) if calibration is None else calibration
    if calibration.setting_digest != run_setting.digest:
        raise ProbeError("frozen calibration does not belong to the requested cell")
    started = time.perf_counter()
    counter = EvaluationCounter()
    steps = []
    anchor_index = 0
    for step in range(0, executed_steps, anchor_stride):
        for carrier in REFERENCE_CARRIERS:
            incumbent = _base_configuration(
                tape,
                max(0, step - 1),
                carrier,
            )
            row = execute_step(
                tape=tape,
                setting=setting,
                step_index=step,
                carrier=carrier,
                calibration=calibration,
                counter=counter,
                incumbent=incumbent,
                c2_horizon_offsets=run_setting.c2_horizon_offsets,
                run_setting=run_setting,
                selection_workers=selection_workers,
                selection_boundary_indices=selection_boundary_indices,
                selection_stage2_m=selection_stage2_m,
                selection_fading_quantile_alpha=selection_fading_quantile_alpha,
            )
            row["anchor_index"] = anchor_index
            row["forecast_offsets"] = [1, 2, 3]
            steps.append(row)
            anchor_index += 1
            if anchor_limit is not None and anchor_index >= anchor_limit:
                break
        if anchor_limit is not None and anchor_index >= anchor_limit:
            break
    elapsed = time.perf_counter() - started
    provider_sha256 = tape.protocol.provider_source_digest
    code_sha256 = _code_authority_digest()
    reward_core_identities: dict[str, list[int]] = {}
    for arm in ARMS:
        endpoints = []
        for step in steps:
            arm_row = next(row for row in step["arms"] if row["arm"] == arm)
            opportunity = (
                int(arm_row["full_roster_user_steps"]) * DECISION_INTERVAL_S
            )
            endpoints.append(
                StepEndpoint.build(
                    bits=arm_row["bits"],
                    joules=arm_row["joules"],
                    decoding_user_seconds=(
                        float(arm_row["decoding_availability"]) * opportunity
                    ),
                    # Both time values cross the same receipt boundary before
                    # exact endpoint accounting.  Reconstructing only
                    # decoding time while passing the pre-serialization
                    # useful-time sum can invert an exact equality by one
                    # floating-point ulp (for example 31.040000000000013 vs
                    # 31.040000000000017 seconds).
                    useful_user_seconds=(
                        float(arm_row["useful_availability"]) * opportunity
                    ),
                    opportunity_user_seconds=opportunity,
                    complete_service_user_steps=arm_row[
                        "complete_service_user_steps"
                    ],
                    user_steps=arm_row["full_roster_user_steps"],
                )
            )
        identity = assert_reward_core_identity(
            endpoints,
            lambda_bits_per_j=calibration.lambda_bits_per_j,
            eta_ref=calibration.eta_ref,
            kappa_bits_per_user_step=calibration.kappa_bits_per_user_step,
        )
        reward_core_identities[arm] = [identity.numerator, identity.denominator]
    summary = _summarize_steps(steps, calibration)
    canonical_rows = _canonical_step_rows(
        steps,
        provider_sha256=provider_sha256,
        code_sha256=code_sha256,
    )
    summary["canonical_wrapper_sha256"] = digest_payload(
        [
            {
                name: value
                for name, value in row.items()
                if name not in {"arm_payload", "arm_payload_sha256"}
            }
            for row in canonical_rows
        ]
    )
    _verify_reaggregation(
        canonical_rows,
        summary,
        provider_sha256=provider_sha256,
        code_sha256=code_sha256,
    )
    sweep_identity = (
        None
        if sweep_panel is None
        else sweep_receipt_identity(
            panel=sweep_panel,
            x_value=sweep_x_value,
            run_id=run_setting.run_id,
            world_domain=domain,
            world_sha256=tape.digest,
            catalogue_sha256=str(catalogue_definition()["sha256"]),
        )
    )
    receipt = {
        "schema": UNIT_SCHEMA,
        "receipt_header": {
            "energy_boundary": ENERGY_BOUNDARY_SENTENCE,
            "traffic_model": (
                "saturated full-buffer decodable throughput; the per-user rate "
                "target is a power-control setpoint, not a demand model"
            ),
            "pa_efficiency_name": "saturation efficiency",
            "hardware_mapping_assumption": (
                "one beam maps to one switchable RF chain; the per-satellite "
                "common term is a processing increment, not total platform load"
            ),
            "atomic_application_limitation": (
                "ideal simultaneous all-user profile application; partial "
                "completion and execution-aware control remain unvalidated"
            ),
            "causality_rule": (
                "orbital elements are usable only when receipt/publication time "
                "precedes the decision instant; nearest epoch is retrospective"
            ),
        },
        "status": "SMOKE_NOT_MATRIX" if smoke_not_matrix else "COMPLETE",
        "SMOKE_NOT_MATRIX": smoke_not_matrix,
        "attempt_id": attempt_id,
        "split": tape.split,
        "test_split_opened": False,
        "training": False,
        "cell": run_setting.run_id,
        "base_cell": setting.label,
        "cell_sha256": run_setting.digest,
        "claim_classification": run_setting.claim_classification,
        "regime": run_setting.regime,
        "regime_wording": (
            "primary a-r0"
            if run_setting.claim_classification == "PRIMARY"
            else f"in regime {run_setting.regime}"
        ),
        "sealed_run_setting": run_setting.payload(),
        "sweep_identity": sweep_identity,
        "world_index": world_index,
        "world_domain": domain,
        "world_seed": tape.seed,
        "learner_seed": 0,
        "cluster": {
            "tle_date": tape.tle_date,
            "world_seed": tape.seed,
            "learner_seed": 0,
            "oracle_world": world_index,
        },
        "world_manifest": tape.manifest(),
        "world_manifest_sha256": tape.digest,
        "calibration": calibration.payload(),
        "calibration_sha256": calibration.digest,
        "provider_source_sha256": provider_sha256,
        "code_authority_sha256": code_sha256,
        "anchor_stride": anchor_stride,
        "canonical_steps_rolled": 30,
        "prepared_steps": len(tape.steps),
        "prepared_step_contract": "30 executed + 3 forecast offsets",
        "c2_horizon_offsets_used": list(range(1, run_setting.c2_horizon_offsets + 1)),
        "anchor_count": len(steps),
        "anchor_limit": anchor_limit,
        "selection_workers": selection_workers,
        "selection_boundary_indices": list(selection_boundary_indices),
        "selection_stage2_m": selection_stage2_m,
        "selection_fading_quantile_alpha": selection_fading_quantile_alpha,
        "reward_core_identity_checked_for_all_arms": True,
        "reward_core_identity_by_arm": reward_core_identities,
        "catalogue_definition": catalogue_definition(),
        "catalogue_definition_sha256": catalogue_definition()["sha256"],
        "arms": list(ARMS),
        "steps": steps,
        "canonical_step_rows": canonical_rows,
        "canonical_step_rows_sha256": digest_payload(canonical_rows),
        "candidate_shortlist_miss_count": sum(
            int(step["e1_certificate"]["candidate_shortlist_miss_count"]) for step in steps
        ),
        "successor_usable_energy_range": _summarize_energy_range(steps),
        "failure_analysis": summary,
        "elapsed_seconds": elapsed,
    }
    assert_matrix_conformance(receipt)
    receipt["receipt_sha256"] = digest_payload(receipt)
    return receipt


def synthetic_shortlist_miss_counts() -> dict[int, int]:
    """KAT helper: census all four synthetic probe worlds before outcomes."""

    counts: dict[int, int] = {}
    for world_index, domain in enumerate(PROBE_WORLD_DOMAINS, start=1):
        tape = build_world_tape(
            domain=domain,
            provider=TinySyntheticProvider(),
            steps=1,
            start_time_s=0.0,
        )
        base = _base_configuration(tape, 0, "nearest-eligible")
        _rows, census = _catalogue_with_census(tape, 0, base)
        counts[world_index] = census["candidate_shortlist_miss_count"]
    return counts


def closed_loop_quantile_sweep(
    *,
    tape: ExogenousWorldTape,
    calibration: CalibrationValues,
    executed_steps: int = 2,
    selection_workers: int = DECLARED_WORKERS,
    selection_boundary_indices: tuple[int, ...] = SELECTION_BOUNDARY_INDICES,
    selection_stage2_m: int = SELECTION_STAGE2_M,
) -> dict[str, object]:
    """Run the sealed paired alpha sweep with one trajectory per arm.

    Calls are deduplicated only when both the carried configuration and prior
    served-user state are identical.  The selected row for each arm is then
    carried to that arm's next anchor, so an arm can diverge from every other
    arm and from the same arm under another alpha.  Every selected endpoint is
    still the ordinary realised 48-boundary endpoint with deadline fallback.
    """

    if tape.domain != SMOKE_WORLD_DOMAINS[0]:
        raise ProbeError("quantile sweep must use the quarantined SMOKE world")
    if type(executed_steps) is not int or not 1 <= executed_steps <= 30:
        raise ProbeError("quantile sweep steps must lie in 1..30")
    if len(tape.steps) < executed_steps + 3:
        raise ProbeError("quantile sweep tape omits forecast offsets")
    setting = _setting("a-r0")
    run_setting = run_setting_for("a-r0")
    if calibration.setting_digest != run_setting.digest:
        raise ProbeError("quantile sweep calibration does not bind a-r0")

    variants: tuple[tuple[str, float | None], ...] = (
        ("nominal", None),
        ("alpha_0.05", 0.05),
        ("alpha_0.10_PRIMARY", 0.10),
        ("alpha_0.25", 0.25),
    )
    variant_rows: dict[str, object] = {}
    for label, alpha in variants:
        incumbents = {
            arm: _base_configuration(tape, 0, "nearest-eligible")
            for arm in ARMS
        }
        previously_served: dict[str, tuple[int, ...]] = {arm: () for arm in ARMS}
        totals = {
            arm: {
                "bits": 0.0,
                "joules": 0.0,
                "availability_served": 0.0,
                "availability_opportunities": 0.0,
                "handover_events": 0,
                "handover_opportunities": 0,
                "deadline_misses": 0,
                "configurations": [],
            }
            for arm in ARMS
        }
        calls = 0
        for step_index in range(executed_steps):
            groups: dict[
                tuple[tuple[tuple[int, tuple[int, int] | None], ...], tuple[int, ...]],
                list[str],
            ] = {}
            for arm in ARMS:
                key = (incumbents[arm].assignments, previously_served[arm])
                groups.setdefault(key, []).append(arm)
            next_incumbents: dict[str, Configuration] = {}
            next_previously_served: dict[str, tuple[int, ...]] = {}
            for (_assignments, _served), grouped_arms in groups.items():
                representative = grouped_arms[0]
                result = execute_step(
                    tape=tape,
                    setting=setting,
                    step_index=step_index,
                    carrier="nearest-eligible",
                    calibration=calibration,
                    counter=EvaluationCounter(),
                    incumbent=incumbents[representative],
                    previously_served_users=previously_served[representative],
                    c2_horizon_offsets=run_setting.c2_horizon_offsets,
                    run_setting=run_setting,
                    selection_workers=selection_workers,
                    selection_boundary_indices=selection_boundary_indices,
                    selection_stage2_m=selection_stage2_m,
                    selection_fading_quantile_alpha=alpha,
                )
                calls += 1
                rows = {str(row["arm"]): row for row in result["arms"]}
                for arm in grouped_arms:
                    row = rows[arm]
                    aggregate = totals[arm]
                    aggregate["bits"] += float(row["bits"])
                    aggregate["joules"] += float(row["joules"])
                    aggregate["availability_served"] += float(
                        row["qos_additive"]["availability_served"]
                    )
                    aggregate["availability_opportunities"] += float(
                        row["qos_additive"]["availability_opportunities"]
                    )
                    aggregate["handover_events"] += int(
                        row["qos_additive"]["handover_events"]
                    )
                    aggregate["handover_opportunities"] += int(
                        row["qos_additive"]["handover_opportunities"]
                    )
                    aggregate["deadline_misses"] += int(row["deadline_missed"])
                    aggregate["configurations"].append(row["configuration_id"])
                    carried = tuple(
                        (
                            int(item["user_id"]),
                            None
                            if item["current"] is None
                            else (int(item["current"][0]), int(item["current"][1])),
                        )
                        for item in row["prior_current_identities"]
                    )
                    next_incumbents[arm] = Configuration(
                        str(row["configuration_id"]), carried, 0, "sweep-carried"
                    )
                    next_previously_served[arm] = tuple(
                        sorted(
                            int(user)
                            for user, served in row["served_PHY"].items()
                            if served
                        )
                    )
            incumbents = next_incumbents
            previously_served = next_previously_served
        arm_rows = {}
        for arm, aggregate in totals.items():
            bits = float(aggregate["bits"])
            joules = float(aggregate["joules"])
            served = float(aggregate["availability_served"])
            opportunities = float(aggregate["availability_opportunities"])
            arm_rows[arm] = {
                **aggregate,
                "pooled_ee_bits_per_j": None if joules == 0.0 else bits / joules,
                "availability": served / opportunities,
                "trajectory_sha256": digest_payload(aggregate["configurations"]),
            }
        variant_rows[label] = {
            "alpha": alpha,
            "primary": alpha == 0.10,
            "arms": arm_rows,
            "deduplicated_execute_step_calls": calls,
        }
    primary = variant_rows["alpha_0.10_PRIMARY"]
    comparisons = {}
    for label, _alpha in variants:
        rows = variant_rows[label]
        comparisons[label] = {
            arm: {
                "same_trajectory_as_primary": (
                    rows["arms"][arm]["trajectory_sha256"]
                    == primary["arms"][arm]["trajectory_sha256"]
                ),
                "pooled_ee_delta_vs_primary": (
                    None
                    if rows["arms"][arm]["pooled_ee_bits_per_j"] is None
                    or primary["arms"][arm]["pooled_ee_bits_per_j"] is None
                    else rows["arms"][arm]["pooled_ee_bits_per_j"]
                    - primary["arms"][arm]["pooled_ee_bits_per_j"]
                ),
            }
            for arm in ARMS
        }
    payload = {
        "schema": f"{SCHEMA}-closed-loop-quantile-sweep-v1",
        "status": "SMOKE_NOT_MATRIX",
        "world_domain": tape.domain,
        "world_sha256": tape.digest,
        "paired_common_exogenous_world": True,
        "executed_steps": executed_steps,
        "endpoint_boundaries_per_anchor": 48,
        "each_arm_keeps_own_trajectory": True,
        "deadline_and_fallback_accounted": True,
        "selection_workers": selection_workers,
        "selection_boundary_indices": list(selection_boundary_indices),
        "selection_stage2_m": selection_stage2_m,
        "primary_alpha_remains_0.10": True,
        "variants": variant_rows,
        "comparisons_to_primary": comparisons,
    }
    payload["receipt_sha256"] = digest_payload(payload)
    return payload


def _dry_run_parity_receipt() -> dict[str, object]:
    profiles = tuple(
        DecisionProfile.build(label, bits=(5, 5), energy_j=energy, served=(True, True))
        for label, energy in zip(("00", "10", "01", "11"), (10, 10, 10, 8), strict=True)
    )
    trace = trace_declared_target_decoder_parity(
        *profiles,
        lambda_bits_per_j=1,
        eta_ref=1,
        kappa_bits_per_user_step=2,
    )
    declared_formula = declared_c3_oracle(
        *profiles,
        lambda_bits_per_j=1,
        eta_ref=1,
        kappa_bits_per_user_step=2,
    )
    production_formula = production_c3(
        *profiles,
        lambda_bits_per_j=1,
        eta_ref=1,
        kappa_bits_per_user_step=2,
    )
    base = Configuration("00", ((0, None), (1, None)), 0, "parity")
    catalog = (
        base,
        Configuration("10", ((0, (1, 0)), (1, None)), 1, "parity"),
        Configuration("01", ((0, None), (1, (2, 0))), 1, "parity"),
        Configuration("11", ((0, (1, 0)), (1, (2, 0))), 2, "parity"),
    )

    class _ParityObjective:
        def __init__(self, profile: DecisionProfile) -> None:
            self.profile = profile

        def outcome(self) -> NetworkOutcome:
            return NetworkOutcome.build(
                bits=self.profile.total_bits,
                joules=self.profile.energy_j,
                phi=0,
                decoding_availability=1,
                useful_availability=1,
                per_user_bits=dict(enumerate(self.profile.bits)),
            )

    calibration = CalibrationValues(
        "fixture",
        "fixture",
        Fraction(1),
        Fraction(1),
        Fraction(1, 2),
        Fraction(1),
        Fraction(1),
        1,
        2,
        Fraction(1, 2),
        CALIBRATION_WORLD_DOMAINS,
        ("fixture-1", "fixture-2"),
    )
    evaluated = {
        config.configuration_id: _ParityObjective(profile)
        for config, profile in zip(catalog, profiles, strict=True)
    }
    v15_decomposition = set_score_decomposition(
        coalition_users=(0, 1),
        outcomes_by_subset={
            frozenset(): evaluated["00"].outcome(),
            frozenset((0,)): evaluated["10"].outcome(),
            frozenset((1,)): evaluated["01"].outcome(),
            frozenset((0, 1)): evaluated["11"].outcome(),
        },
        lambda_bits_per_j=1,
        eta_ref=1,
        kappa_bits_per_user_step=2,
    )
    if v15_decomposition.c1 + v15_decomposition.c3 != (
        v15_decomposition.joint_change_bits / 2
    ):
        raise ProbeError("v1.5 C1+C3 set-score identity failed")
    decoder_cross: dict[str, dict[str, object]] = {}
    for formula_name, formula in (
        ("declared", declared_formula),
        ("production", production_formula),
    ):
        decoder_factors = {
            "C1": {},
            "C2": {},
            "C3": {
                (0, (1, 0)): formula.lcsrs_shares[0] / 2,
                (1, (2, 0)): formula.lcsrs_shares[1] / 2,
            },
        }
        additive = _independent_proposal(
            base=base, catalog=catalog, factors=decoder_factors, include=("C3",)
        )
        atomic = _set_select(
            catalog=catalog,
            evaluated=evaluated,  # type: ignore[arg-type]
            factors=decoder_factors,
            include=("C3",),
            base=base,
            calibration=calibration,
        )
        decoder_cross[formula_name] = {}
        for decoder_name, selected in (("additive", additive), ("atomic", atomic)):
            endpoint = profiles[("00", "10", "01", "11").index(selected.configuration_id)]
            decoder_cross[formula_name][decoder_name] = {
                "executed_action": selected.configuration_id,
                "bits": [float(value) for value in endpoint.bits],
                "joules": float(endpoint.energy_j),
                "served": list(endpoint.served),
            }
    additive = decoder_cross["production"]["additive"]
    atomic = decoder_cross["production"]["atomic"]
    if additive["executed_action"] != trace.additive_execution.action:
        raise ProbeError("production additive decoder disagrees with declared fixture")
    if atomic["executed_action"] != trace.atomic_execution.action:
        raise ProbeError("production atomic set decoder disagrees with declared fixture")
    core = reward_endpoint_identity(
        step_bits=(10, 20, 5),
        step_energy_j=(1, 3, 2),
        lambda_bits_per_j=2,
        eta_ref=2,
        kappa_bits_per_user_step=1,
    )
    capped = demand_cap_profiles(
        profiles,
        demand_cap_bits=100,
        lambda_bits_per_j=1,
        eta_ref=1,
        kappa_bits_per_user_step=2,
    )
    reoptimized = reoptimize_joint_by_regime(
        {"fixture": profiles},
        lambda_by_regime={"fixture": 1},
        eta_ref_by_regime={"fixture": 1},
        kappa_bits_per_user_step_by_regime={"fixture": 2},
    )
    bootstrap = common_action_bootstrap(
        ((10, 0), (0, 9)),
        lambda_bits_per_j=1,
        eta_ref=1,
        kappa_bits_per_user_step=1,
    )
    payload = {
        "declared_psi": 2,
        "v15_set_score_identity": {
            "d_by_user": [
                [user, float(value)] for user, value in v15_decomposition.d_by_user
            ],
            "psi_A": float(v15_decomposition.interaction_bits),
            "shapley_interaction_by_user": [
                [user, float(value)]
                for user, value in v15_decomposition.shapley_interaction_by_user
            ],
            "C1_plus_C3": float(v15_decomposition.c1 + v15_decomposition.c3),
            "F_joint_minus_F_base_over_kappa": float(
                v15_decomposition.joint_change_bits / 2
            ),
            "exact": True,
        },
        "production_formula_matches_declared": trace.production_formula_matches_declared,
        "additive_executed_action": additive["executed_action"],
        "atomic_executed_action": atomic["executed_action"],
        "executed_endpoint_energy_j": atomic["joules"],
        "formula_decoder_cross": decoder_cross,
        "production_decoder_paths": ["_independent_proposal", "_set_select"],
        "reward_endpoint_identity_core": float(core),
        "nonbinding_demand_cap_invariant": capped == profiles,
        "per_regime_joint_reoptimization": reoptimized,
        "common_action_bootstrap": {
            "action_index": bootstrap.action_index,
            "selected_heads": [float(value) for value in bootstrap.selected_heads],
            "scalarized_value": float(bootstrap.scalarized_value),
            "unattainable_headwise_mix_rejected": bootstrap.selected_heads != (10, 9),
        },
        "raw_states_traced": sorted(trace.raw_state_endpoints),
        "t3_energy_used": False,
    }
    payload["kat_receipt_sha256"] = digest_payload(payload)
    return payload


def estimate(*, q: float | None) -> dict[str, object]:
    plan = dict(shared_computation_plan(q=q))
    reference = float(plan["reference_core_hours"])
    projected = None if q is None else reference * q * ORCHESTRATION_RESERVE
    plan.update(
        {
            "schema": f"{SCHEMA}-estimate",
            "worlds": list(PROBE_WORLD_DOMAINS),
            # Retain the sealed v1.2 matrix accounting fields.  The additive
            # contingency settings are reported separately and do not rewrite
            # the 31-cell reference estimate.
            "cells": [setting.label for setting in MATRIX_SETTINGS],
            "units": len(PROBE_WORLD_DOMAINS) * len(MATRIX_SETTINGS),
            "all_sealed_run_settings": [
                setting.run_id for setting in ALL_SEALED_RUN_SETTINGS
            ],
            "all_sealed_run_units": (
                len(PROBE_WORLD_DOMAINS) * len(ALL_SEALED_RUN_SETTINGS)
            ),
            "matrix_cells": [setting.label for setting in MATRIX_SETTINGS],
            "matrix_cells_count": len(MATRIX_SETTINGS),
            "sealed_sensitivities_enumerated_after_matrix": [
                setting.run_id for setting in ALL_SEALED_RUN_SETTINGS[len(MATRIX_SETTINGS):]
            ],
            "launch_order": [setting.run_id for setting in LAUNCH_RUN_ORDER],
            "arms": list(ARMS),
            "architecture_tape_once_treatments_rescore": True,
            "orchestration_rescore_reserve": ORCHESTRATION_RESERVE,
            "projected_core_hours_with_reserve": projected,
            "overnight_ceiling_core_hours": OVERNIGHT_CORE_HOURS,
            "within_overnight_ceiling": None if projected is None else projected <= OVERNIGHT_CORE_HOURS,
            "no_catalogue_or_world_truncation": True,
        }
    )
    return plan


def rehearsal(
    *,
    calibration: CalibrationValues | None = None,
    prepared_tape: ExogenousWorldTape | None = None,
) -> dict[str, object]:
    setting = _setting("a-r0")
    calibration = _calibrate(setting) if calibration is None else calibration
    started = time.perf_counter()
    receipt = run_unit(
        setting=setting,
        world_index=1,
        executed_steps=1,
        calibration=calibration,
        prepared_tape=prepared_tape,
        anchor_limit=3,
    )
    elapsed = time.perf_counter() - started
    evaluations = sum(int(step["physical_boundary_evaluations"]) for step in receipt["steps"])
    reference_core_seconds_per_evaluation = REFERENCE_SECONDS * REFERENCE_WORKERS / REFERENCE_EVALUATIONS
    q = (elapsed / max(1, evaluations)) / reference_core_seconds_per_evaluation
    projection = estimate(q=q)
    rehearsal_core_minutes = elapsed * DECLARED_WORKERS / 60.0
    per_anchor_wall_s = elapsed / 3
    projected_four_world_core_hours = (
        per_anchor_wall_s * 4 * 90 * DECLARED_WORKERS / 3600.0
    )
    concurrent_units = 20 // DECLARED_WORKERS
    return {
        "schema": f"{SCHEMA}-rehearsal",
        "cell": "a-r0",
        "world": 1,
        "anchors": 3,
        "arms": list(ARMS),
        "elapsed_seconds": elapsed,
        "physical_boundary_evaluations": evaluations,
        "q": q,
        "reference": {
            "seconds": REFERENCE_SECONDS,
            "workers": REFERENCE_WORKERS,
            "evaluations": REFERENCE_EVALUATIONS,
        },
        "q": q,
        "declared_workers_per_unit": DECLARED_WORKERS,
        "rehearsal_core_minutes": rehearsal_core_minutes,
        "within_10_core_minutes": rehearsal_core_minutes <= 10.0,
        "projection_4_worlds_x_90_anchors": {
            "anchors": 4 * 90,
            "core_hours": projected_four_world_core_hours,
            "process_concurrency": 20,
            "workers_per_unit": DECLARED_WORKERS,
            "concurrent_units": concurrent_units,
            "ideal_wall_minutes": (
                projected_four_world_core_hours
                * 60.0
                / (concurrent_units * DECLARED_WORKERS)
            ),
        },
        "projected_matrix_core_hours": projection["projected_core_hours_with_reserve"],
        "within_160_core_hours": projection["within_overnight_ceiling"],
        "where_time_goes_if_over_ceiling": None
        if projection["within_overnight_ceiling"]
        else {
            "geometry_channel_power_catalogue": "architecture tape construction and complete candidate census",
            "forecast": "three projected offsets with background powers recomputed",
            "rescoring": "12 arms and exact-factor per-cell selection",
            "action": "optimize shared primitive computation; do not truncate cells/worlds/catalogue",
        },
        "development_rehearsal_not_claim_panel": True,
        "unit_receipt_sha256": receipt["receipt_sha256"],
    }


def build_calibration_manifest(
    run_settings: Sequence[SealedRunSetting] = ALL_SEALED_RUN_SETTINGS,
) -> dict[str, object]:
    """Compute every disjoint-world cell calibration before any probe unit."""

    world_manifests = []
    calibration_tapes = []
    tapes_by_profile: dict[str, dict[str, ExogenousWorldTape]] = {}
    selected_runs = tuple(run_settings)
    if not selected_runs:
        raise ProbeError("calibration manifest requires at least one setting")
    provider_profiles = tuple(
        profile
        for profile in (PRIMARY_RUN_SETTING, run_setting_for("R2"))
        if any(run.user_count == profile.user_count for run in selected_runs)
    )
    for profile in provider_profiles:
        profile_name = "R2" if profile.run_id == "R2" else "DEFAULT"
        tapes_by_profile[profile_name] = {}
        for world_index, domain in enumerate(CALIBRATION_WORLD_DOMAINS, start=1):
            tape = build_world_tape(
                domain=domain,
                provider=_provider_for_run(profile),
                steps=30,
                start_time_s=0.0,
            )
            calibration_tapes.append(tape)
            tapes_by_profile[profile_name][domain] = tape
            world_manifests.append(
                {
                    "world_index": world_index,
                    "world_profile": profile_name,
                    "domain": domain,
                    "manifest": tape.manifest(),
                    "world_manifest_sha256": tape.digest,
                }
            )
    values = [
        _calibrate(
            _setting(run.base_cell),
            run,
            prepared_tapes=tapes_by_profile[
                "R2" if run.run_id == "R2" else "DEFAULT"
            ],
        )
        for run in selected_runs
    ]
    probe_tapes = [
        build_world_tape(
            domain=domain,
            provider=_provider_for_run(profile),
            steps=1,
            start_time_s=0.0,
        )
        for profile in provider_profiles
        for domain in PROBE_WORLD_DOMAINS
    ]
    assert_calibration_world_separation(
        calibration_tapes=calibration_tapes, probe_tapes=probe_tapes
    )
    payload = {
        "schema": f"{SCHEMA}-calibration-manifest",
        "status": "FROZEN_CALIBRATION",
        "worlds": list(CALIBRATION_WORLD_DOMAINS),
        "world_manifests": world_manifests,
        "cells": [value.payload() for value in values],
        "cell_order": [setting.run_id for setting in selected_runs],
        "test_split_opened": False,
        "probe_outcomes_opened": False,
        "frozen_once": True,
    }
    payload["receipt_sha256"] = digest_payload(payload)
    return payload


def build_probe_world_manifest(
    *,
    executed_steps: int = 30,
    tape_cache: dict[str, bytes] | None = None,
) -> dict[str, object]:
    """Materialize/digest the four common tapes before opening any arm outcome."""

    worlds = []
    probe_tapes = []
    provider_profiles = (PRIMARY_RUN_SETTING, run_setting_for("R2"))
    for profile in provider_profiles:
        for index, domain in enumerate(PROBE_WORLD_DOMAINS, start=1):
            tape = build_world_tape(
                domain=domain,
                provider=_provider_for_run(profile),
                steps=executed_steps + 3,
                start_time_s=0.0,
            )
            profile_name = "R2" if profile.run_id == "R2" else "DEFAULT"
            cache_name = f"world-tapes/{profile_name.lower()}-world-{index}.pickle"
            encoded_tape = pickle.dumps(tape, protocol=pickle.HIGHEST_PROTOCOL)
            if tape_cache is not None:
                tape_cache[cache_name] = encoded_tape
            probe_tapes.append(tape)
            worlds.append(
                {
                    "world_index": index,
                    "world_profile": profile_name,
                    "domain": domain,
                    "world_seed": tape.seed,
                    "manifest": tape.manifest(),
                    "world_manifest_sha256": tape.digest,
                    "tape_cache_file": cache_name,
                    "tape_cache_sha256": hashlib.sha256(encoded_tape).hexdigest(),
                }
            )
    calibration_tapes = [
        build_world_tape(
            domain=domain,
            provider=WORLD_PROVIDER_FACTORY(),
            steps=1,
            start_time_s=0.0,
        )
        for domain in CALIBRATION_WORLD_DOMAINS
    ]
    assert_calibration_world_separation(
        calibration_tapes=calibration_tapes, probe_tapes=probe_tapes
    )
    payload = {
        "schema": f"{SCHEMA}-world-manifest",
        "status": "FROZEN_WORLD_MANIFEST",
        "executed_steps": executed_steps,
        "forecast_offsets": 3,
        "worlds": worlds,
        "test_split_opened": False,
        "probe_outcomes_opened": False,
    }
    payload["receipt_sha256"] = digest_payload(payload)
    return payload


def world_allocation_identity(
    tape: ExogenousWorldTape,
    *,
    role: str,
    learner_seed: int,
) -> dict[str, object]:
    """Return the full audit-A allocation identity for one world."""

    manifest = tape.manifest()
    return {
        "role": role,
        "world_domain": tape.domain,
        "split": tape.split,
        "start_utc": manifest["start_utc"],
        "tle_date": tape.tle_date,
        "tle_files": manifest["tle_files"],
        "split_rule_sha256": manifest["split_rule_sha256"],
        "provider_source_sha256": manifest["provider_source_sha256"],
        "layout_sha256": manifest["layout_sha256"],
        "mobility_stream_identity": manifest["stream_identities"]["mobility"],  # type: ignore[index]
        "fading_stream_identity": manifest["stream_identities"]["fading"],  # type: ignore[index]
        "world_seed": tape.seed,
        "learner_seed": learner_seed,
        "world_manifest_sha256": tape.digest,
    }


def assert_role_wise_date_disjointness(
    identities: Sequence[Mapping[str, object]],
) -> None:
    """Fail closed when a claim date was used by any development role."""

    roles_by_date: dict[str, set[str]] = {}
    for row in identities:
        role, date = str(row.get("role", "")), str(row.get("tle_date", ""))
        if not role or not date:
            raise ProbeError("allocation identity lacks role or TLE date")
        roles_by_date.setdefault(date, set()).add(role)
    collisions = {
        date: sorted(roles)
        for date, roles in roles_by_date.items()
        if "CLAIM_PANEL" in roles and roles != {"CLAIM_PANEL"}
    }
    if collisions:
        raise ProbeError(f"successor role-wise date collision: {collisions}")


def build_allocation_manifest(
    identities: Sequence[Mapping[str, object]],
    *,
    legacy_development_overlap_dates: Sequence[str] = (),
) -> dict[str, object]:
    """Seal role allocations and the non-causal TLE benchmark convention."""

    rows = [dict(row) for row in identities]
    assert_role_wise_date_disjointness(rows)
    required = {
        "role", "world_domain", "split", "start_utc", "tle_date", "tle_files",
        "split_rule_sha256", "provider_source_sha256", "layout_sha256",
        "mobility_stream_identity", "fading_stream_identity", "world_seed",
        "learner_seed", "world_manifest_sha256",
    }
    if any(set(row) != required for row in rows):
        raise ProbeError("allocation manifest world identity is incomplete or noncanonical")
    if any(row["split"] != "TRAIN" for row in rows):
        raise ProbeError("allocation manifest may contain TRAIN worlds only")
    roles = {str(row["role"]) for row in rows}
    required_roles = SUCCESSOR_DEVELOPMENT_ROLES | {"CLAIM_PANEL"}
    if not required_roles <= roles:
        raise ProbeError(
            "allocation manifest must enumerate CLAIM_PANEL and every successor-development role"
        )
    payload = {
        "schema": f"{SCHEMA}-allocation-manifest",
        "status": "FROZEN_ALLOCATION",
        "worlds": rows,
        "role_wise_date_disjoint": True,
        "claim_panel_date_fresh_from_successor_development": True,
        "legacy_development_overlap_dates": sorted(set(legacy_development_overlap_dates)),
        "tle_selection_convention": {
            "rule": "per NORAD choose nearest epoch from date-1/date/date+1 at episode start",
            "maximum_absolute_age_hours": 24,
            "future_epochs_allowed": True,
            "causality": "NON_CAUSAL_ACCURACY_FIRST_BENCHMARK",
            "verify_source": True,
        },
    }
    payload["receipt_sha256"] = digest_payload(payload)
    return payload


def load_calibration(
    path: Path,
    setting: PhysicsSetting,
    run_setting: SealedRunSetting | None = None,
) -> CalibrationValues:
    target = Path(path)
    sidecar = _sidecar(target)
    if not target.is_file() or not sidecar.is_file():
        raise ProbeError("frozen calibration manifest and sidecar are required")
    encoded = target.read_bytes()
    digest = hashlib.sha256(encoded).hexdigest()
    if sidecar.read_text(encoding="ascii").split() != [digest, target.name]:
        raise ProbeError("calibration sidecar disagrees")
    if stat.S_IMODE(target.stat().st_mode) != 0o444:
        raise ProbeError("calibration manifest is not immutable mode 0444")
    payload = json.loads(encoded)
    if payload.get("schema") != f"{SCHEMA}-calibration-manifest" or payload.get("status") != "FROZEN_CALIBRATION":
        raise ProbeError("calibration manifest schema/status disagrees")
    _verify_self_digest(payload, label="calibration manifest")
    run_setting = run_setting_for(setting.label) if run_setting is None else run_setting
    rows = [row for row in payload.get("cells", []) if row.get("setting_sha256") == run_setting.digest]
    if len(rows) != 1:
        raise ProbeError("calibration manifest lacks exactly one requested setting")
    return CalibrationValues.from_payload(rows[0])


def _verify_world_protocol_manifest(manifest: Mapping[str, object]) -> None:
    protocol = manifest.get("provider_protocol")
    if not isinstance(protocol, dict):
        raise ProbeError("world manifest lacks mandatory provider protocol outputs")
    for field in ("split", "start_utc", "tle_files", "split_rule_sha256", "provider_source_sha256"):
        if protocol.get(field) != manifest.get(field):
            raise ProbeError(f"world manifest provider protocol disagrees on {field}")
    if manifest.get("split") != "TRAIN":
        raise ProbeError("world manifest is not TRAIN")
    if not isinstance(manifest.get("tle_files"), list) or not manifest["tle_files"]:
        raise ProbeError("world manifest has no opened TLE bindings")
    for name, digest in manifest["tle_files"]:  # type: ignore[assignment]
        if not name or not isinstance(digest, str) or len(digest) != 64:
            raise ProbeError("world manifest has malformed TLE filename/hash output")
    for field in ("split_rule_sha256", "provider_source_sha256"):
        value = manifest.get(field)
        if not isinstance(value, str) or len(value) != 64:
            raise ProbeError(f"world manifest has malformed {field}")
    try:
        ProviderProtocolOutputs(
            split=str(protocol["split"]),
            start_utc=str(protocol["start_utc"]),
            tle_files=tuple((str(name), str(digest)) for name, digest in protocol["tle_files"]),
            split_rule_digest=str(protocol["split_rule_sha256"]),
            provider_source_digest=str(protocol["provider_source_sha256"]),
        )
    except (KeyError, TypeError, ValueError, MCRLContractError) as error:
        raise ProbeError("world manifest provider protocol is not executable/valid") from error


def load_world_binding(
    path: Path,
    world_index: int,
    run_setting: SealedRunSetting = PRIMARY_RUN_SETTING,
) -> tuple[str, dict[str, object]]:
    target = Path(path)
    sidecar = _sidecar(target)
    if not target.is_file() or not sidecar.is_file():
        raise ProbeError("frozen world manifest and sidecar are required")
    encoded = target.read_bytes()
    digest = hashlib.sha256(encoded).hexdigest()
    if sidecar.read_text(encoding="ascii").split() != [digest, target.name]:
        raise ProbeError("world-manifest sidecar disagrees")
    if stat.S_IMODE(target.stat().st_mode) != 0o444:
        raise ProbeError("world manifest is not immutable mode 0444")
    payload = json.loads(encoded)
    if payload.get("schema") != f"{SCHEMA}-world-manifest" or payload.get("status") != "FROZEN_WORLD_MANIFEST":
        raise ProbeError("world manifest schema/status disagrees")
    _verify_self_digest(payload, label="world manifest")
    profile = "R2" if run_setting.run_id == "R2" else "DEFAULT"
    rows = [
        row
        for row in payload.get("worlds", [])
        if row.get("world_index") == world_index
        and row.get("world_profile", "DEFAULT") == profile
    ]
    if len(rows) != 1 or rows[0].get("domain") != _world_domain(world_index):
        raise ProbeError("world manifest lacks exactly one requested domain")
    manifest = rows[0].get("manifest")
    if not isinstance(manifest, dict):
        raise ProbeError("world manifest row lacks embedded tape manifest")
    _verify_world_protocol_manifest(manifest)
    if rows[0].get("world_manifest_sha256") != digest_payload(manifest):
        raise ProbeError("world manifest row digest does not bind its protocol outputs")
    return str(rows[0]["world_manifest_sha256"]), manifest


def load_world_digest(path: Path, world_index: int) -> str:
    """Compatibility wrapper around the stronger pre-unit protocol verifier."""

    return load_world_binding(path, world_index)[0]


def load_prepared_world_tape(
    path: Path,
    world_index: int,
    run_setting: SealedRunSetting = PRIMARY_RUN_SETTING,
) -> ExogenousWorldTape:
    """Load the immutable once-per-world tape bound by the formal manifest."""

    world_digest, manifest = load_world_binding(path, world_index, run_setting)
    payload = json.loads(Path(path).read_bytes())
    profile = "R2" if run_setting.run_id == "R2" else "DEFAULT"
    row = next(
        row
        for row in payload["worlds"]
        if row.get("world_index") == world_index
        and row.get("world_profile", "DEFAULT") == profile
    )
    cache_name = row.get("tape_cache_file")
    cache_digest = row.get("tape_cache_sha256")
    if not isinstance(cache_name, str) or not isinstance(cache_digest, str):
        raise ProbeError("world manifest omits its prepared tape binding")
    root = Path(path).parent.resolve()
    target = (root / cache_name).resolve()
    if not target.is_relative_to(root):
        raise ProbeError("prepared tape path escapes the manifest directory")
    sidecar = _sidecar(target)
    if not target.is_file() or not sidecar.is_file():
        raise ProbeError("prepared world tape and sidecar are required")
    encoded = target.read_bytes()
    actual = hashlib.sha256(encoded).hexdigest()
    if actual != cache_digest:
        raise ProbeError("prepared world tape digest disagrees with manifest")
    if sidecar.read_text(encoding="ascii").split() != [actual, target.name]:
        raise ProbeError("prepared world tape sidecar disagrees")
    if stat.S_IMODE(target.stat().st_mode) != 0o444:
        raise ProbeError("prepared world tape is not immutable mode 0444")
    try:
        tape = pickle.loads(encoded)
    except Exception as error:
        raise ProbeError("prepared world tape cannot be decoded") from error
    if not isinstance(tape, ExogenousWorldTape):
        raise ProbeError("prepared world tape has the wrong type")
    if tape.digest != world_digest or tape.manifest() != manifest:
        raise ProbeError("prepared world tape disagrees with its manifest")
    return tape


def install_provider(
    specification: str, *, validate_instance: bool = True
) -> None:
    """Install ``module:factory`` for formal server world acquisition."""

    global WORLD_PROVIDER_FACTORY
    try:
        module_name, attribute = specification.split(":", 1)
        factory = getattr(importlib.import_module(module_name), attribute)
    except Exception as error:
        raise ProbeError("--provider must name an importable module:factory") from error
    if not callable(factory):
        raise ProbeError("--provider must name an importable module:factory")
    if validate_instance:
        try:
            provider = factory()
        except Exception as error:
            raise ProbeError("provider factory could not be constructed") from error
        for name in (
            "inventory", "cluster_identity", "protocol_outputs", "user_layout", "boundary"
        ):
            if not callable(getattr(provider, name, None)):
                raise ProbeError(f"provider lacks callable {name}")
    WORLD_PROVIDER_FACTORY = factory


def _sidecar(path: Path) -> Path:
    return Path(str(path) + ".sha256")


def _verify_self_digest(payload: Mapping[str, object], *, label: str) -> None:
    unsigned = dict(payload)
    declared = unsigned.pop("receipt_sha256", None)
    if not isinstance(declared, str) or declared != digest_payload(unsigned):
        raise ProbeError(f"{label} embedded receipt digest disagrees")


def write_immutable(path: Path, payload: Mapping[str, object]) -> str:
    target = Path(path)
    sidecar = _sidecar(target)
    if target.exists() or target.is_symlink() or sidecar.exists() or sidecar.is_symlink():
        raise ProbeError(f"refusing to overwrite immutable receipt: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = canonical_bytes(payload) + b"\n"
    digest = hashlib.sha256(encoded).hexdigest()
    with target.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    with sidecar.open("xb") as handle:
        handle.write(f"{digest}  {target.name}\n".encode("ascii"))
        handle.flush()
        os.fsync(handle.fileno())
    target.chmod(0o444)
    sidecar.chmod(0o444)
    return digest


def write_immutable_bytes(path: Path, encoded: bytes) -> str:
    """Write one content-addressed binary companion with receipt guardrails."""

    target = Path(path)
    sidecar = _sidecar(target)
    if target.exists() or target.is_symlink() or sidecar.exists() or sidecar.is_symlink():
        raise ProbeError(f"refusing to overwrite immutable companion: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(encoded).hexdigest()
    with target.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    with sidecar.open("xb") as handle:
        handle.write(f"{digest}  {target.name}\n".encode("ascii"))
        handle.flush()
        os.fsync(handle.fileno())
    target.chmod(0o444)
    sidecar.chmod(0o444)
    return digest


def write_domain_manifest_inventory(
    output: Path,
    payload: Mapping[str, object],
    *,
    kind: str,
) -> list[dict[str, object]]:
    """Write one immutable formal manifest for every declared world domain."""

    source_key = "worlds" if kind == "probe" else "world_manifests"
    rows = payload.get(source_key)
    if not isinstance(rows, list):
        raise ProbeError(f"{kind} aggregate manifest lacks world rows")
    by_domain: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("domain"), str):
            raise ProbeError(f"{kind} aggregate manifest has a malformed world row")
        by_domain.setdefault(str(row["domain"]), []).append(row)
    inventory = []
    for domain, domain_rows in sorted(by_domain.items()):
        domain_payload: dict[str, object] = {
            "schema": f"{SCHEMA}-{kind}-domain-manifest",
            "status": "FROZEN_FORMAL_WORLD",
            "domain": domain,
            "aggregate_receipt_sha256": payload["receipt_sha256"],
            "world_profiles": domain_rows,
            "outcomes_opened": False,
        }
        domain_payload["receipt_sha256"] = digest_payload(domain_payload)
        path = output / "formal-manifests" / domain / "manifest.json"
        file_sha256 = write_immutable(path, domain_payload)
        inventory.append(
            {
                "domain": domain,
                "path": str(path),
                "file_sha256": file_sha256,
                "receipt_sha256": domain_payload["receipt_sha256"],
            }
        )
    return inventory


def _unit_path(output: Path, setting: PhysicsSetting, world: int) -> Path:
    safe = setting.label.replace("′", "prime").replace("γ", "gamma")
    return output / "units" / safe / f"world-{world}.json"


def _run_unit_path(output: Path, run_setting: SealedRunSetting, world: int) -> Path:
    safe = run_setting.run_id.replace("′", "prime").replace("γ", "gamma")
    return output / "units" / safe / f"world-{world}.json"


def _nonadditivity_fraction(receipts: Sequence[Mapping[str, object]]) -> float | None:
    """Interaction share of the matched FULL-vs-BASE F change, without clipping."""

    interaction = joint = 0.0
    for receipt in receipts:
        summary = receipt["failure_analysis"]  # type: ignore[index]
        interaction += float(summary["non_additive_interaction_bits"])
        full = summary["arms"]["FULL"]  # type: ignore[index]
        base = summary["arms"][ALL_NEUTRAL_CONTROL]  # type: ignore[index]
        eta_ratio = receipt["calibration"]["eta_ref"]  # type: ignore[index]
        eta = float(eta_ratio[0]) / float(eta_ratio[1])
        joint += (float(full["bits"]) - float(base["bits"])) - eta * (
            float(full["joules"]) - float(base["joules"])
        )
    return None if joint == 0.0 else interaction / joint


def _merged_uncertainty(receipts: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Build v1.2 uncertainty and claim gates from complete unit receipts."""

    by_cell: dict[str, list[Mapping[str, object]]] = {}
    for receipt in receipts:
        by_cell.setdefault(str(receipt["cell"]), []).append(receipt)
    results: dict[str, object] = {}
    for run_setting in ALL_SEALED_RUN_SETTINGS:
        rows = sorted(by_cell[run_setting.run_id], key=lambda row: int(row["world_index"]))
        cluster_ids = [
            (
                str(row["world_manifest"]["cluster"]["tle_date"]),  # type: ignore[index]
                int(row.get("learner_seed", 0)),
            )
            for row in rows
        ]
        contrasts: dict[str, object] = {}
        for name, comparator in (
            *((name, drop) for name, (_full, drop) in MARGINALS.items()),
            ("LEVEL_A_S_UNI", "S_UNI"),
            ("ALL_NEUTRAL", ALL_NEUTRAL_CONTROL),
        ):
            grouped: dict[tuple[str, int], list[dict[str, float]]] = {}
            for row in rows:
                arms = row["failure_analysis"]["arms"]  # type: ignore[index]
                full = arms["FULL"]
                other = arms[comparator]
                grouped.setdefault(
                    (
                        str(row["world_manifest"]["cluster"]["tle_date"]),  # type: ignore[index]
                        int(row.get("learner_seed", 0)),
                    ),
                    [],
                ).append(
                    {
                        "tle_date": row["world_manifest"]["cluster"]["tle_date"],
                        "learner_seed": row["learner_seed"],
                        "full_bits": full["bits"],
                        "full_joules": full["joules"],
                        "comparator_bits": other["bits"],
                        "comparator_joules": other["joules"],
                        "full_availability_served": full["qos_additive"]["availability_served"],
                        "full_availability_opportunities": full["qos_additive"]["availability_opportunities"],
                        "comparator_availability_served": other["qos_additive"]["availability_served"],
                        "comparator_availability_opportunities": other["qos_additive"]["availability_opportunities"],
                        "full_phi_numerator": full["qos_additive"]["phi_cost_numerator"],
                        "full_phi_denominator": full["qos_additive"]["phi_cost_denominator"],
                        "comparator_phi_numerator": other["qos_additive"]["phi_cost_numerator"],
                        "comparator_phi_denominator": other["qos_additive"]["phi_cost_denominator"],
                        "full_handover_events": full["qos_additive"]["handover_events"],
                        "full_handover_opportunities": full["qos_additive"]["handover_opportunities"],
                        "comparator_handover_events": other["qos_additive"]["handover_events"],
                        "comparator_handover_opportunities": other["qos_additive"]["handover_opportunities"],
                    }
                )
            clusters = []
            for (tle_date, learner_seed), members in sorted(grouped.items()):
                clusters.append(
                    {
                        "tle_date": tle_date,
                        "learner_seed": learner_seed,
                        "full_bits": math.fsum(row["full_bits"] for row in members),
                        "full_joules": math.fsum(row["full_joules"] for row in members),
                        "comparator_bits": math.fsum(row["comparator_bits"] for row in members),
                        "comparator_joules": math.fsum(row["comparator_joules"] for row in members),
                        **{
                            field: math.fsum(row[field] for row in members)
                            for field in (
                                "full_availability_served",
                                "full_availability_opportunities",
                                "comparator_availability_served",
                                "comparator_availability_opportunities",
                                "full_phi_numerator",
                                "full_phi_denominator",
                                "comparator_phi_numerator",
                                "comparator_phi_denominator",
                                "full_handover_events",
                                "full_handover_opportunities",
                                "comparator_handover_events",
                                "comparator_handover_opportunities",
                            )
                        },
                    }
                )
            bootstrap_seed = seed_from_domain(f"V025_PROBE/bootstrap/{run_setting.run_id}/{name}")
            estimate_row = uncertainty_estimate(
                clusters,
                learner_experiment=False,
                seed=bootstrap_seed,
            )
            estimate_row["supplementary_two_way_pigeonhole"] = two_way_pigeonhole_bootstrap(
                clusters,
                seed=bootstrap_seed ^ 0x5A5A5A5A,
            )
            contrasts[name] = estimate_row["primary"] | {
                "supplementary_delta_method": estimate_row["supplementary_delta_method"],
                "supplementary_two_way_pigeonhole": estimate_row["supplementary_two_way_pigeonhole"],
            }
        marginal_rows = [contrasts[name] for name in MARGINALS]
        results[run_setting.run_id] = {
            "cluster_ids_tle_date_x_learner_seed": [[date, seed] for date, seed in sorted(set(cluster_ids))],
            "learner_seed_by_world": {
                str(row["world_index"]): row["learner_seed"]
                for row in rows
            },
            "contrasts": contrasts,
            "intersection_union_success": all(
                row["ee_margin_pass"] and row["qos_noninferior"] for row in marginal_rows  # type: ignore[index]
            ),
            "claim_scope": "FULL-minus-DROP with other two components enabled",
            "claim_classification": (
                run_setting.claim_classification
            ),
            "level_b": {
                "contrast": "FULL_vs_DROP_C3",
                "certificate": contrasts["C3"],
                "nonadditivity_fraction": _nonadditivity_fraction(rows),
            },
            "level_a": {
                "contrast": "FULL_vs_S_UNI",
                "certificate": contrasts["LEVEL_A_S_UNI"],
                "nonadditivity_fraction": _nonadditivity_fraction(rows),
            },
            "main_effects_claimed": False,
        }
    return {
        "primary_estimator": "one-way paired bootstrap over TLE dates for learner-free physics matrix",
        "learner_experiment_primary_estimator": "two-way pigeonhole bootstrap over TLE dates x learner seeds",
        "cluster_unit": "TLE date; worlds pool within a cell",
        "per_cell": results,
        "primary_a_r0_intersection_union_success": results["a-r0"]["intersection_union_success"],  # type: ignore[index]
        "all_neutral_support_only": True,
    }


def training_admission(
    *,
    primary_setting: str,
    certificates: Mapping[str, object],
    regime_certificates: Mapping[str, Mapping[str, object]] | None = None,
) -> dict[str, object]:
    """Execute the v1.9 monotone a-r0 admission trichotomy."""

    if primary_setting != "a-r0":
        raise ProbeError("training admission must read a-r0 only")
    specifications = (
        ("physics_integrity", "physics/integrity PASS", lambda value: value is True),
        ("u1_complete_certified", "complete U1 census with certified optimum", lambda value: value is True),
        ("s0_relative_gain", "deployable S0 relative pooled-EE gain >= 1%", lambda value: float(value) >= 0.01),
        ("s0_vs_s_uni_certified", "S0 exceeds certified S_UNI beyond numerical error", lambda value: value is True),
        ("c1_oracle_marginal", "C1 oracle marginal is positive beyond numerical error", lambda value: value is True),
        ("c2_forecast_validity", "C2 three-offset forecast validity is established", lambda value: value is True),
        ("qos_validity_deadline", "QoS, physics validity, and deadlines pass", lambda value: value is True),
    )
    c3_specifications = (
        ("c3_choice_nontrivial", "interaction-aware choice differs at a non-trivial anchor fraction", lambda value: value is True),
        ("c3_realised_contrast_positive", "realised interaction-aware contrast is positive", lambda value: value is True),
    )

    def evaluate(
        setting_id: str, values: Mapping[str, object]
    ) -> tuple[dict[str, object], str]:
        rows: dict[str, object] = {}
        for key, rule, predicate in (*specifications, *c3_specifications):
            if key not in values:
                raise ProbeError(f"{setting_id} admission certificate missing {key}")
            value = values[key]
            rows[key] = {"value": value, "rule": rule, "pass": bool(predicate(value))}
        common_pass = all(
            bool(rows[key]["pass"])  # type: ignore[index]
            for key, _rule, _predicate in specifications
        )
        c3_pass = all(
            bool(rows[key]["pass"])  # type: ignore[index]
            for key, _rule, _predicate in c3_specifications
        )
        decision = (
            "ADMIT_FULL"
            if common_pass and c3_pass
            else "ADMIT_C1C2"
            if common_pass
            else "NOT_ADMITTED"
        )
        return rows, decision

    rows, decision = evaluate("a-r0", certificates)
    sensitivities = {}
    for regime, regime_values in sorted((regime_certificates or {}).items()):
        regime_rows, regime_decision = evaluate(regime, regime_values)
        sensitivities[regime] = {
            "label": f"in regime {regime}",
            "decision": (
                f"{regime_decision}_IN_REGIME"
                if regime_decision != "NOT_ADMITTED"
                else "NOT_ADMITTED_IN_REGIME"
            ),
            "certificates": regime_rows,
            "reported_separately": True,
            "changes_primary_admission": False,
        }
    return {
        "decision": decision,
        "source_setting": "a-r0",
        "certificates": rows,
        "u1_need_not_exceed_base_for_c3": True,
        "training_setting_if_admitted": "a-r0",
        "regime_sensitivity_certificates": sensitivities,
        "truth_table": admission_truth_table(),
    }


def admission_truth_table() -> list[dict[str, object]]:
    """Complete monotone v1.9 truth table over common and C3 states."""

    rows = []
    for common_pass in (False, True):
        for c3_choice in (False, True):
            for c3_positive in (False, True):
                c3_pass = c3_choice and c3_positive
                rows.append(
                    {
                        "common_certificates_pass": common_pass,
                        "c3_choice_nontrivial": c3_choice,
                        "c3_realised_contrast_positive": c3_positive,
                        "decision": (
                            "ADMIT_FULL"
                            if common_pass and c3_pass
                            else "ADMIT_C1C2"
                            if common_pass
                            else "NOT_ADMITTED"
                        ),
                    }
                )
    return rows


def _pooled_relative_ee(
    receipts: Sequence[Mapping[str, object]], first: str, second: str
) -> float:
    def totals(arm: str) -> tuple[float, float]:
        return (
            math.fsum(float(row["failure_analysis"]["arms"][arm]["bits"]) for row in receipts),  # type: ignore[index]
            math.fsum(float(row["failure_analysis"]["arms"][arm]["joules"]) for row in receipts),  # type: ignore[index]
        )
    first_bits, first_joules = totals(first)
    second_bits, second_joules = totals(second)
    if min(first_joules, second_joules, second_bits) <= 0.0:
        return -math.inf
    return (first_bits / first_joules) / (second_bits / second_joules) - 1.0


def _setting_admission_certificates(
    receipts: Sequence[Mapping[str, object]],
    uncertainty: Mapping[str, object],
    run_id: str,
) -> dict[str, object]:
    setting_receipts = [row for row in receipts if row["cell"] == run_id]
    if not setting_receipts:
        raise ProbeError(f"{run_id} receipts are required for admission reporting")
    setting_uncertainty = uncertainty["per_cell"][run_id]  # type: ignore[index]
    contrasts = setting_uncertainty["contrasts"]  # type: ignore[index]
    numerical_error = 1.0e-9
    return {
        "physics_integrity": all(row.get("status") == "COMPLETE" for row in setting_receipts),
        "u1_complete_certified": all(
            step["e1_certificate"]["candidate_census_complete"]
            for row in setting_receipts
            for step in row["steps"]  # type: ignore[index]
        ),
        "s0_relative_gain": _pooled_relative_ee(
            setting_receipts, "S0_DEPLOYABLE", ALL_NEUTRAL_CONTROL
        ),
        "s0_vs_s_uni_certified": (
            _pooled_relative_ee(setting_receipts, "S0_DEPLOYABLE", "S_UNI")
            > numerical_error
            and all(
                arm["termination_certificate"]
                in {"NO_IMPROVING_LEGAL_UNILATERAL", "EXHAUSTED_LEGAL_OPTIONS"}
                for row in setting_receipts
                for step in row["steps"]  # type: ignore[index]
                for arm in step["arms"]  # type: ignore[index]
                if arm["arm"] == "S_UNI"
            )
        ),
        "c1_oracle_marginal": bool(
            contrasts["C1"]["ee_margin_pass"]
            and contrasts["C1"]["qos_noninferior"]
        ),
        "c2_forecast_validity": all(
            step["c2_forecast_certificate"]["valid"]
            for row in setting_receipts
            for step in row["steps"]  # type: ignore[index]
        ),
        "qos_validity_deadline": all(
            row.get("status") == "COMPLETE"
            and not any(
                bool(arm.get("deadline_missed"))
                for step in row["steps"]  # type: ignore[index]
                for arm in step["arms"]  # type: ignore[index]
                if arm["arm"] in SET_LEVEL_ARMS
            )
            for row in setting_receipts
        ),
        "c3_choice_nontrivial": (
            sum(
                step["selection_approximations"]["pre_fallback_selections"]["FULL"]
                != step["selection_approximations"]["pre_fallback_selections"]["DROP_C3"]
                for row in setting_receipts
                for step in row["steps"]  # type: ignore[index]
            )
            / max(
                1,
                sum(len(row["steps"]) for row in setting_receipts),  # type: ignore[arg-type]
            )
            > 0.0
        ),
        "c3_realised_contrast_positive": bool(
            contrasts["C3"]["contrast_relative"] > 0.0
        ),
    }


def report_schema() -> dict[str, object]:
    """Return the executable, TRAIN-only v1.5 claim classification."""

    return {
        "only_primary_setting": "a-r0",
        "primary_claim": "conditional conjunction",
        "all_other_settings": "EXPLORATORY_SENSITIVITY",
        "panel": "TRAIN_ONLY",
    }


def merge(output: Path) -> dict[str, object]:
    registry = _attempt_records()
    by_attempt: dict[str, list[dict[str, object]]] = {}
    for record in registry:
        by_attempt.setdefault(str(record["attempt_id"]), []).append(record)
    bindings = []
    receipts = []
    for run_setting in ALL_SEALED_RUN_SETTINGS:
        setting = _setting(run_setting.base_cell)
        for world in range(1, 5):
            path = _run_unit_path(output, run_setting, world)
            sidecar = _sidecar(path)
            if not path.is_file() or not sidecar.is_file():
                raise ProbeError(f"merge waiting for {run_setting.run_id}:{world}")
            encoded = path.read_bytes()
            digest = hashlib.sha256(encoded).hexdigest()
            if sidecar.read_text(encoding="ascii").split() != [digest, path.name]:
                raise ProbeError(f"unit digest sidecar mismatch: {path}")
            if stat.S_IMODE(path.stat().st_mode) != 0o444:
                raise ProbeError(f"unit is not immutable mode 0444: {path}")
            receipt = json.loads(encoded)
            if receipt.get("cell_sha256") != run_setting.digest or receipt.get("world_index") != world:
                raise ProbeError(f"unit identity mismatch: {path}")
            if receipt.get("claim_classification") != run_setting.claim_classification:
                raise ProbeError(f"unit claim classification mismatch: {path}")
            if receipt.get("schema") != UNIT_SCHEMA or receipt.get("status") != "COMPLETE":
                raise ProbeError(f"unit schema/status mismatch: {path}")
            attempt_id = receipt.get("attempt_id")
            attempt_rows = by_attempt.get(str(attempt_id), [])
            statuses = [row.get("status") for row in attempt_rows]
            if statuses != ["STARTED", "DONE"]:
                raise ProbeError(f"unit lacks one clean STARTED/DONE attempt: {path}")
            if any(row.get("status") == "ABANDONED" for row in attempt_rows):
                raise ProbeError(f"unit has an unadjudicated abandoned attempt: {path}")
            _verify_self_digest(receipt, label=f"unit {run_setting.run_id}:{world}")
            if receipt.get("world_manifest_sha256") != digest_payload(receipt["world_manifest"]):
                raise ProbeError(f"embedded world-manifest digest mismatch: {path}")
            if receipt.get("calibration_sha256") != digest_payload(receipt["calibration"]):
                raise ProbeError(f"embedded calibration digest mismatch: {path}")
            if receipt.get("canonical_step_rows_sha256") != digest_payload(
                receipt.get("canonical_step_rows")
            ):
                raise ProbeError(f"canonical step-row digest mismatch: {path}")
            _verify_reaggregation(
                receipt["canonical_step_rows"],  # type: ignore[arg-type]
                receipt["failure_analysis"],  # type: ignore[arg-type]
                provider_sha256=str(receipt["provider_source_sha256"]),
                code_sha256=str(receipt["code_authority_sha256"]),
            )
            receipts.append(receipt)
            bindings.append({"cell": run_setting.run_id, "world": world, "path": str(path), "sha256": digest})
    for world in range(1, 5):
        default_digests = {
            row["world_manifest_sha256"]
            for row in receipts
            if row["world_index"] == world and row["cell"] != "R2"
        }
        r2_digests = {
            row["world_manifest_sha256"]
            for row in receipts
            if row["world_index"] == world and row["cell"] == "R2"
        }
        if len(default_digests) != 1 or len(r2_digests) != 1:
            raise ProbeError(f"world {world} is not common within each provider regime")
    for run_setting in ALL_SEALED_RUN_SETTINGS:
        digests = {row["calibration_sha256"] for row in receipts if row["cell"] == run_setting.run_id}
        if len(digests) != 1:
            raise ProbeError(f"calibration drift across worlds for {run_setting.run_id}")
    strides = {int(row.get("anchor_stride", 0)) for row in receipts}
    if len(strides) != 1 or next(iter(strides)) < 1:
        raise ProbeError("merge refuses missing or mixed anchor strides")
    catalogue_digests = {row.get("catalogue_definition_sha256") for row in receipts}
    if catalogue_digests != {catalogue_definition()["sha256"]}:
        raise ProbeError("catalogue definition drift across units")
    uncertainty = _merged_uncertainty(receipts)
    admission = training_admission(
        primary_setting="a-r0",
        certificates=_setting_admission_certificates(receipts, uncertainty, "a-r0"),
        regime_certificates={
            run.regime: _setting_admission_certificates(
                receipts, uncertainty, run.run_id
            )
            for run in (
                *REGIME_RUN_SETTINGS,
                run_setting_for("a′-r0"),
                run_setting_for("a-γ0"),
            )
        },
    )
    payload = {
        "schema": MERGE_SCHEMA,
        "status": "COMPLETE",
        "units": bindings,
        "unit_count": len(bindings),
        "cell_order": [setting.run_id for setting in ALL_SEALED_RUN_SETTINGS],
        "worlds": list(PROBE_WORLD_DOMAINS),
        "all_cells_reported": True,
        "anchor_stride": next(iter(strides)),
        "catalogue_definition_sha256": catalogue_definition()["sha256"],
        "test_split_opened": False,
        "training": False,
        "uncertainty": uncertainty,
        "training_admission": admission,
        "report_schema": report_schema(),
        "summary_sha256": digest_payload([receipt["failure_analysis"] for receipt in receipts]),
    }
    payload["receipt_sha256"] = digest_payload(payload)
    return payload


def _sweep_safe(value: object) -> str:
    return str(value).replace("′", "prime").replace("γ", "gamma").replace(".", "p")


def _sweep_unit_path(output: Path, panel: str, x_value: object, world: int) -> Path:
    return output / "sweeps" / panel / _sweep_safe(x_value) / f"world-{world}.json"


def _sweep_point_from_units(
    *,
    panel: str,
    x_value: object,
    run_id: str,
    receipts: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    if not receipts:
        raise ProbeError("a sweep point requires at least one unit receipt")
    identities = []
    for receipt in receipts:
        identity = receipt.get("sweep_identity")
        if not isinstance(identity, Mapping):
            raise ProbeError("sweep unit omitted its identity")
        if identity.get("panel") != panel or identity.get("x_value") != x_value:
            raise ProbeError("sweep unit identity disagrees with its panel point")
        identities.append(identity)
    curves = {}
    for curve in SWEEP_CURVES:
        source = SWEEP_ARM_SOURCE[curve]
        bits = math.fsum(
            float(receipt["failure_analysis"]["arms"][source]["bits"])  # type: ignore[index]
            for receipt in receipts
        )
        joules = math.fsum(
            float(receipt["failure_analysis"]["arms"][source]["joules"])  # type: ignore[index]
            for receipt in receipts
        )
        curves[curve] = {
            "source_arm": source,
            "bits": bits,
            "joules": joules,
            "pooled_ee_bits_per_j": None if joules == 0.0 else bits / joules,
        }
    identity_body = {
        "schema": f"{SWEEP_SCHEMA}-pooled-point-identity",
        "panel": panel,
        "x_axis": SWEEP_PANEL_METADATA[panel]["x_axis"],
        "x_value": x_value,
        "run_id": run_id,
        "unit_identity_sha256s": [identity["sha256"] for identity in identities],
    }
    payload = {
        "schema": f"{SWEEP_SCHEMA}-pooled-point",
        "status": "COMPLETE",
        "identity": {**identity_body, "sha256": digest_payload(identity_body)},
        "panel": panel,
        "x_value": x_value,
        "run_id": run_id,
        "world_count": len(receipts),
        "curves": curves,
        "reporting_only": list(REPORTING_ONLY_ARMS),
        "enters_certificate": False,
        "enters_admission": False,
    }
    payload["receipt_sha256"] = digest_payload(payload)
    return payload


def _off_axis_sweep_point(angle_deg: float) -> dict[str, object]:
    """Evaluate the sealed 48-boundary fixed-occupancy panel-F fixture."""

    _sweep_point("F", angle_deg)
    beam = (99_999, 0)
    path_without_tx_gain = 5.0e-16
    gain = float(transmit_gain_linear(angle_deg)) * path_without_tx_gain
    geometry = Geometry(
        (Link(0, beam, 0, gain, gain),),
        np.zeros((1, 1), dtype=np.float64),
        np.zeros((1, 1), dtype=np.float64),
    )
    tape = build_shared_tape(
        "a-r",
        tuple((index * 0.640, geometry) for index in range(48)),
        HardwareInventory.fixed((beam,)),
        roster=(0,),
    )
    score = score_setting(tape, _setting("a-r0"))
    bits = math.fsum(score.bits.values())
    joules = float(score.joules)
    world_body = {
        "domain": "V025_OFF_AXIS_KAT/quarantined/fixed-occupancy-1",
        "off_axis_angle_deg": angle_deg,
        "occupancy": 1,
        "boundaries": 48,
        "path_factor_without_tx_gain": path_without_tx_gain,
    }
    world_sha256 = digest_payload(world_body)
    identity = sweep_receipt_identity(
        panel="F",
        x_value=angle_deg,
        run_id="a-r0",
        world_domain=str(world_body["domain"]),
        world_sha256=world_sha256,
        catalogue_sha256=str(catalogue_definition()["sha256"]),
    )
    curves = {
        curve: {
            "source_arm": SWEEP_ARM_SOURCE[curve],
            "bits": bits,
            "joules": joules,
            "pooled_ee_bits_per_j": None if joules == 0.0 else bits / joules,
        }
        for curve in SWEEP_CURVES
    }
    payload = {
        "schema": f"{SWEEP_SCHEMA}-pooled-point",
        "status": "COMPLETE",
        "identity": identity,
        "panel": "F",
        "x_value": angle_deg,
        "run_id": "a-r0",
        "world_count": 1,
        "world": world_body,
        "curves": curves,
        "single_member_catalogue_all_curves_coincide": True,
        "deadline_missed": False,
        "fallback": None,
        "reporting_only": list(REPORTING_ONLY_ARMS),
        "enters_certificate": False,
        "enters_admission": False,
    }
    payload["receipt_sha256"] = digest_payload(payload)
    return payload


def run_sweep_panel(
    *,
    panel: str,
    output: Path,
    calibration_manifest: Path | None = None,
    world_manifest: Path | None = None,
    executed_steps: int = 30,
    anchor_stride: int = 1,
    anchor_limit: int | None = None,
) -> dict[str, object]:
    """Execute one sealed CH5 panel and write identity-bound point receipts."""

    panel = panel.upper()
    plan = sweep_plan(panel)
    bindings = []
    if panel == "F":
        for x_value, run_id in SWEEP_PANEL_POINTS[panel]:
            receipt = _off_axis_sweep_point(float(x_value))
            path = _sweep_unit_path(output, panel, x_value, 1)
            file_sha256 = write_immutable(path, receipt)
            bindings.append(
                {"x_value": x_value, "run_id": run_id, "path": str(path), "file_sha256": file_sha256}
            )
    else:
        if calibration_manifest is None or world_manifest is None:
            raise ProbeError("panels A, B, and E require calibration and world manifests")
        tape_cache: dict[str, ExogenousWorldTape] = {}
        for x_value, run_id in SWEEP_PANEL_POINTS[panel]:
            run_setting = run_setting_for(run_id)
            setting = _setting(run_setting.base_cell)
            calibration = load_calibration(calibration_manifest, setting, run_setting)
            units = []
            for world in range(1, 5):
                world_sha256, expected_manifest = load_world_binding(
                    world_manifest, world, run_setting
                )
                if world_sha256 not in tape_cache:
                    tape_cache[world_sha256] = load_prepared_world_tape(
                        world_manifest, world, run_setting
                    )
                receipt = run_unit(
                    setting=setting,
                    world_index=world,
                    executed_steps=executed_steps,
                    anchor_stride=anchor_stride,
                    calibration=calibration,
                    expected_world_digest=world_sha256,
                    expected_world_manifest=expected_manifest,
                    run_setting=run_setting,
                    prepared_tape=tape_cache[world_sha256],
                    anchor_limit=anchor_limit,
                    sweep_panel=panel,
                    sweep_x_value=x_value,
                )
                unit_path = _sweep_unit_path(output, panel, x_value, world)
                unit_file_sha256 = write_immutable(unit_path, receipt)
                units.append(receipt)
                bindings.append(
                    {
                        "x_value": x_value,
                        "run_id": run_id,
                        "world": world,
                        "path": str(unit_path),
                        "file_sha256": unit_file_sha256,
                    }
                )
            point = _sweep_point_from_units(
                panel=panel,
                x_value=x_value,
                run_id=run_id,
                receipts=units,
            )
            point_path = output / "sweeps" / panel / _sweep_safe(x_value) / "pooled.json"
            point_sha256 = write_immutable(point_path, point)
            bindings.append(
                {"x_value": x_value, "run_id": run_id, "path": str(point_path), "file_sha256": point_sha256}
            )
    payload = {
        **plan,
        "status": "COMPLETE",
        "bindings": bindings,
        "test_split_opened": False,
        "training": False,
    }
    payload["receipt_sha256"] = digest_payload(payload)
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--unit", metavar="CELL:WORLD")
    modes.add_argument("--merge", action="store_true")
    modes.add_argument("--estimate", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--rehearsal", action="store_true")
    modes.add_argument("--calibrate", action="store_true")
    modes.add_argument("--manifest", action="store_true")
    modes.add_argument("--allocation", action="store_true")
    modes.add_argument("--sweep", choices=tuple(SWEEP_PANEL_POINTS))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--provider", help="formal server primitive provider as module:factory")
    parser.add_argument("--calibration", type=Path, help="immutable calibration manifest for --unit")
    parser.add_argument("--world-manifest", type=Path, help="immutable pre-outcome world manifest for --unit")
    parser.add_argument(
        "--allocation-input",
        type=Path,
        help="JSON allocation identities consumed by --allocation",
    )
    parser.add_argument("--q", type=float)
    parser.add_argument("--anchor-stride", type=int, default=1)
    parser.add_argument("--executed-steps", type=int, default=30)
    parser.add_argument("--anchors", type=int, help="exact anchor limit for rehearsal/smoke")
    parser.add_argument("--setting", help="single sealed setting for calibration")
    parser.add_argument("--smoke-not-matrix", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.provider:
        # Formal unit workers consume the immutable tape cache and therefore
        # import, but never instantiate, the provider factory.
        install_provider(
            args.provider,
            validate_instance=not (
                (args.unit and not args.smoke_not_matrix) or args.sweep
            ),
        )
    if args.sweep:
        if args.sweep != "F" and (
            not args.provider
            or args.calibration is None
            or args.world_manifest is None
        ):
            raise SystemExit(
                "--sweep A/B/E requires --provider, --calibration, and --world-manifest"
            )
        payload = run_sweep_panel(
            panel=args.sweep,
            output=args.output,
            calibration_manifest=args.calibration,
            world_manifest=args.world_manifest,
            executed_steps=args.executed_steps,
            anchor_stride=args.anchor_stride,
            anchor_limit=args.anchors,
        )
        path = args.output / "sweeps" / args.sweep / "panel-receipt.json"
        digest = write_immutable(path, payload)
        print(
            json.dumps(
                {
                    "status": "COMPLETE",
                    "panel": args.sweep,
                    "path": str(path),
                    "file_sha256": digest,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.estimate:
        print(json.dumps(estimate(q=args.q), indent=2, sort_keys=True))
        return 0
    if args.dry_run:
        receipt = run_unit(setting=_setting("a-r0"), world_index=1, executed_steps=1)
        parity = _dry_run_parity_receipt()
        result = {
            "schema": f"{SCHEMA}-dry-run",
            "status": "PASS",
            "one_real_step_every_arm": [row["arm"] for row in receipt["steps"][0]["arms"]],
            "arms_expected": list(ARMS),
            "no_environment_clone": True,
            "world_manifest_sha256": receipt["world_manifest_sha256"],
            "calibration_sha256": receipt["calibration_sha256"],
            "unit_receipt_sha256": receipt["receipt_sha256"],
            "declared_target_decoder_parity": parity,
            "kat_receipt_sha256": parity["kat_receipt_sha256"],
            "reward_endpoint_identity_checked": True,
            "candidate_shortlist_miss_counts": synthetic_shortlist_miss_counts(),
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.rehearsal:
        frozen = None
        if args.calibration is not None:
            frozen = load_calibration(
                args.calibration,
                _setting("a-r0"),
                run_setting_for("a-r0"),
            )
        payload = rehearsal(calibration=frozen)
        path = args.output / "rehearsal.json"
        digest = write_immutable(path, payload)
        print(json.dumps({"status": "COMPLETE", "path": str(path), "file_sha256": digest, **payload}, indent=2, sort_keys=True))
        return 0
    if args.calibrate:
        if not args.provider:
            raise SystemExit("--calibrate requires the formal server --provider module:factory")
        selected_runs = (
            ALL_SEALED_RUN_SETTINGS
            if args.setting is None
            else (run_setting_for(args.setting),)
        )
        payload = build_calibration_manifest(selected_runs)
        domain_inventory = write_domain_manifest_inventory(
            args.output, payload, kind="calibration"
        )
        path = args.output / "calibration-manifest.json"
        digest = write_immutable(path, payload)
        print(json.dumps({"status": "FROZEN_CALIBRATION", "path": str(path), "file_sha256": digest, "domain_manifests": domain_inventory}, indent=2, sort_keys=True))
        return 0
    if args.manifest:
        if not args.provider:
            raise SystemExit("--manifest requires the formal server --provider module:factory")
        tape_cache: dict[str, bytes] = {}
        payload = build_probe_world_manifest(tape_cache=tape_cache)
        for relative_path, encoded in sorted(tape_cache.items()):
            write_immutable_bytes(args.output / relative_path, encoded)
        domain_inventory = write_domain_manifest_inventory(
            args.output, payload, kind="probe"
        )
        path = args.output / "world-manifest.json"
        digest = write_immutable(path, payload)
        print(json.dumps({"status": "FROZEN_WORLD_MANIFEST", "path": str(path), "file_sha256": digest, "domain_manifests": domain_inventory}, indent=2, sort_keys=True))
        return 0
    if args.allocation:
        if args.allocation_input is None:
            raise SystemExit("--allocation requires --allocation-input")
        try:
            source = json.loads(args.allocation_input.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise SystemExit(f"invalid --allocation-input: {error}") from error
        if not isinstance(source, (list, dict)):
            raise SystemExit("--allocation-input must be a list or JSON object")
        identities = source if isinstance(source, list) else source.get("worlds")
        if not isinstance(identities, list):
            raise SystemExit("--allocation-input must be a list or contain a worlds list")
        overlap = [] if isinstance(source, list) else source.get(
            "legacy_development_overlap_dates", []
        )
        if not isinstance(overlap, list) or not all(
            isinstance(value, str) for value in overlap
        ):
            raise SystemExit("legacy_development_overlap_dates must be a list of strings")
        payload = build_allocation_manifest(
            identities,
            legacy_development_overlap_dates=overlap,
        )
        path = args.output / "allocation-manifest.json"
        digest = write_immutable(path, payload)
        print(json.dumps({"status": "FROZEN_ALLOCATION", "path": str(path), "file_sha256": digest}, indent=2, sort_keys=True))
        return 0
    if args.unit:
        if (
            not args.provider
            or args.calibration is None
            or (args.world_manifest is None and not args.smoke_not_matrix)
        ):
            raise SystemExit(
                "formal --unit requires --provider module:factory, --calibration manifest, "
                "and --world-manifest (the quarantined smoke supplies its own binding)"
            )
        try:
            cell, world_text = args.unit.rsplit(":", 1)
            run_setting = run_setting_for(cell)
            setting = _setting(run_setting.base_cell)
            world = int(world_text)
        except (ValueError, ProbeError) as error:
            raise SystemExit(f"invalid --unit CELL:WORLD: {error}") from error
        frozen_calibration = load_calibration(args.calibration, setting, run_setting)
        prepared_tape = None
        if args.smoke_not_matrix:
            if world != 1:
                raise SystemExit("development smoke has exactly one quarantined world")
            prepared_tape = build_world_tape(
                domain=SMOKE_WORLD_DOMAINS[0],
                provider=_provider_for_run(run_setting),
                steps=args.executed_steps + 3,
                start_time_s=0.0,
            )
            world_digest = prepared_tape.digest
            expected_world_manifest = prepared_tape.manifest()
        else:
            assert args.world_manifest is not None
            world_digest, expected_world_manifest = load_world_binding(
                args.world_manifest, world, run_setting
            )
            prepared_tape = load_prepared_world_tape(
                args.world_manifest, world, run_setting
            )
        attempt_id = str(uuid.uuid4())
        authority = {
            "code_sha256": _code_authority_digest(),
            "provider_sha256": expected_world_manifest["provider_source_sha256"],
            "world_sha256": world_digest,
            "calibration_sha256": frozen_calibration.digest,
        }
        append_attempt(
            status="STARTED",
            attempt_id=attempt_id,
            experiment="V025_PHYSICS_SUCCESSOR",
            panel="SMOKE" if args.smoke_not_matrix else "PROBE_R2",
            cell=run_setting.run_id,
            unit=str(world),
            authority=authority,
        )
        try:
            receipt = run_unit(
                setting=setting,
                world_index=world,
                executed_steps=args.executed_steps,
                anchor_stride=args.anchor_stride,
                smoke_not_matrix=args.smoke_not_matrix,
                attempt_id=attempt_id,
                calibration=frozen_calibration,
                expected_world_digest=world_digest,
                expected_world_manifest=expected_world_manifest,
                run_setting=run_setting,
                prepared_tape=prepared_tape,
                anchor_limit=args.anchors,
            )
            path = (
                args.output / "smoke" / "a-r0-world-1.json"
                if args.smoke_not_matrix
                else _run_unit_path(args.output, run_setting, world)
            )
            digest = write_immutable(path, receipt)
        except Exception:
            append_attempt(
                status="ABANDONED",
                attempt_id=attempt_id,
                experiment="V025_PHYSICS_SUCCESSOR",
                panel="SMOKE" if args.smoke_not_matrix else "PROBE_R2",
                cell=run_setting.run_id,
                unit=str(world),
                authority=authority,
            )
            raise
        append_attempt(
            status="DONE",
            attempt_id=attempt_id,
            experiment="V025_PHYSICS_SUCCESSOR",
            panel="SMOKE" if args.smoke_not_matrix else "PROBE_R2",
            cell=run_setting.run_id,
            unit=str(world),
            authority={**authority, "receipt_file_sha256": digest},
        )
        print(json.dumps({"status": "COMPLETE", "path": str(path), "file_sha256": digest}, indent=2, sort_keys=True))
        return 0
    payload = merge(args.output)
    path = args.output / "merged-receipt.json"
    digest = write_immutable(path, payload)
    print(json.dumps({"status": "COMPLETE", "path": str(path), "file_sha256": digest}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
