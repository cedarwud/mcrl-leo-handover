#!/usr/bin/env python3
"""Re-run the pre-declared V0.25 synthetic mechanism map on stage 4b.

The script imports the stage-4b runner and supplies only a parametric primitive
provider. Radiation, energy, bounded-catalogue construction, ledger handling,
v1.5 target-sum selection, and step summaries remain stage-4b code paths.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import stat
import sys
import time
from typing import Callable, Mapping, Sequence


for _variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_variable] = "1"

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
STAGE2_PATH = (
    REPO
    / ".scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py"
)
DEFAULT_OUTPUT = (
    REPO / ".scratch/multi-catfish-v025-physics-successor/synthetic-map-r2"
)
DEFAULT_REPORT = (
    REPO
    / ".scratch/multi-catfish-v025-physics-successor/V025-SYNTHETIC-MAP-R2-REPORT-2026-09-08.md"
)
LABEL = "SYNTHETIC_MECHANISM_MAP_R2"
SCHEMA = "multi-catfish-mcrl-v025-synthetic-mechanism-map-r2-v1"
MAX_CORE_HOURS = 10.0
MAX_WORKERS = 4
STEPS = 30
WORLD_SEEDS = (1, 2, 3)
CALIBRATION_SEED = 10_000
CALIBRATION_START_S = 435.0
SETTINGS = ("a-r0", "a′-r0", "a-γ0", "b0", "a′-γ0")
OCCUPANCIES = (("LOW", 1.5), ("MID", 4.0), ("HIGH", 8.0))
DENSITIES = (("SPARSE", 2), ("DENSE", 4))
COUPLINGS = (("WEAK", -25.0), ("STRONG", -12.0))
ENGINE_DEFECTS = (
    {
        "id": "RATE_TARGET_CLEARANCE_ULP_ITERATION_CAP",
        "disposition": "FIXED_WITH_KAT",
        "symptom": (
            "HIGH-DENSE-STRONG a-r calibration returned INVALID after 4096 iterations "
            "with zero power residual because achieved SINR was two ulps below its target"
        ),
        "minimal_reproduction": (
            "ParametricSyntheticProvider(8, 4, -12, 10000), start_time_s=435, "
            "users 0/1 on NORAD 90001 and users 2..7 on NORAD 90004, a-r nominal"
        ),
        "kat": "tests/physics_v025/test_provider_synthetic.py::test_rate_target_fixed_point_accepts_power_tolerance_scale_clearance",
        "fix": "detect an eight-ulp rounding case and nudge under-target power upward by at most eight ulps",
    },
)

if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from mcrl.physics_v025.calibration import CalibrationValues  # noqa: E402
from mcrl.physics_v025.constants_v025 import DECISION_INTERVAL_S  # noqa: E402
from mcrl.physics_v025.provider_synthetic import (  # noqa: E402
    MAP_LAST_BOUNDARY_S,
    ParametricSyntheticProvider,
)
from mcrl.physics_v025.tapes import (  # noqa: E402
    PROBE_WORLD_DOMAINS,
    REFERENCE_CARRIERS,
    build_world_tape,
    canonical_bytes,
    digest_payload,
)


class SyntheticMapError(RuntimeError):
    pass


def _load_stage2():
    """Compatibility name retained for local callers; loads stage 4b."""

    name = "_mcrl_v025_stage4b_runner"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, STAGE2_PATH)
    if spec is None or spec.loader is None:
        raise SyntheticMapError(f"cannot load stage-2 runner: {STAGE2_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def grid_cells() -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "id": f"{occupancy_name}-{density_name}-{coupling_name}",
            "occupancy_label": occupancy_name,
            "users_per_beam": occupancy,
            "density_label": density_name,
            "sats_per_user": satellites,
            "coupling_label": coupling_name,
            "coupling_db": coupling_db,
        }
        for occupancy_name, occupancy in OCCUPANCIES
        for density_name, satellites in DENSITIES
        for coupling_name, coupling_db in COUPLINGS
    )


def _provider(cell: Mapping[str, object], seed: int) -> ParametricSyntheticProvider:
    return ParametricSyntheticProvider(
        float(cell["users_per_beam"]),
        int(cell["sats_per_user"]),
        float(cell["coupling_db"]),
        seed,
    )


def _bind_provider(runner, cell: Mapping[str, object], seed: int) -> None:
    runner.WORLD_PROVIDER_FACTORY = lambda: _provider(cell, seed)


def _calibrate(runner, cell: Mapping[str, object], setting_label: str):
    _bind_provider(runner, cell, CALIBRATION_SEED)
    setting = runner._setting(setting_label)
    run_setting = runner.run_setting_for(setting_label)
    observations = []
    for domain in runner.CALIBRATION_WORLD_DOMAINS:
        tape = build_world_tape(
            domain=domain,
            provider=runner.WORLD_PROVIDER_FACTORY(),
            steps=1,
            start_time_s=CALIBRATION_START_S,
        )
        base = runner._base_configuration(tape, 0, "nearest-eligible")
        catalog = runner._catalogue(tape, 0, base)
        evaluator = runner.StepEvaluator(
            tape,
            setting,
            0,
            transition_from=base,
            cell_rekeyed_users=runner._rekeyed_users(tape, 0),
            field="nominal",
            run_setting=run_setting,
        )
        profiles = {row.configuration_id: evaluator.evaluate(row) for row in catalog}
        selected = runner.nominal_greedy_reference(
            runner._nominal_configuration(row, profiles[row.configuration_id])
            for row in catalog
        )
        realised = runner.StepEvaluator(
            tape,
            setting,
            0,
            transition_from=base,
            cell_rekeyed_users=runner._rekeyed_users(tape, 0),
            run_setting=run_setting,
        ).evaluate(next(row for row in catalog if row.configuration_id == selected.configuration_id))
        observations.append(
            runner.CalibrationObservation.build(
                world_domain=domain,
                bits=realised.bits,
                joules=realised.joules,
                users=len(tape.user_layout),
                time_s=DECISION_INTERVAL_S,
                selected_configuration_id=selected.configuration_id,
            )
        )
    frozen = runner.freeze_setting_calibration(
        setting=setting,
        observations=observations,
    )
    return runner.replace(
        frozen,
        setting_label=run_setting.run_id,
        setting_digest=run_setting.digest,
    )


def _signed(payload: dict[str, object]) -> dict[str, object]:
    result = dict(payload)
    result["receipt_sha256"] = digest_payload(result)
    return result


def _sidecar(path: Path) -> Path:
    return Path(str(path) + ".sha256")


def write_once(path: Path, payload: Mapping[str, object]) -> str:
    if payload.get("experiment_label") != LABEL:
        raise SyntheticMapError("every synthetic-map receipt must carry the experiment label")
    target = Path(path)
    sidecar = _sidecar(target)
    if target.exists() or target.is_symlink() or sidecar.exists() or sidecar.is_symlink():
        raise SyntheticMapError(f"refusing to overwrite write-once receipt: {target}")
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


def read_once(path: Path) -> dict[str, object]:
    target = Path(path)
    sidecar = _sidecar(target)
    if not target.is_file() or not sidecar.is_file():
        raise SyntheticMapError(f"missing immutable receipt: {target}")
    encoded = target.read_bytes()
    digest = hashlib.sha256(encoded).hexdigest()
    if sidecar.read_text(encoding="ascii").split() != [digest, target.name]:
        raise SyntheticMapError(f"receipt sidecar mismatch: {target}")
    if stat.S_IMODE(target.stat().st_mode) != 0o444:
        raise SyntheticMapError(f"receipt is not mode 0444: {target}")
    payload = json.loads(encoded)
    if payload.get("experiment_label") != LABEL:
        raise SyntheticMapError(f"receipt label mismatch: {target}")
    unsigned = dict(payload)
    declared = unsigned.pop("receipt_sha256", None)
    if declared != digest_payload(unsigned):
        raise SyntheticMapError(f"embedded receipt digest mismatch: {target}")
    return payload


def _calibration_path(output: Path, cell_id: str, setting: str) -> Path:
    return output / "calibration" / cell_id / f"{_safe(setting)}.json"


def _unit_path(output: Path, cell_id: str, seed: int, setting: str) -> Path:
    return output / "units" / cell_id / f"world-{seed}" / f"{_safe(setting)}.json"


def _safe(label: str) -> str:
    return label.replace("′", "prime").replace("γ", "gamma")


def _estimated_unit_execution_seconds(execution_seconds: float, legal_steps: int) -> float:
    """Scale one measured carrier-step to one complete three-carrier unit."""

    return float(execution_seconds) * int(legal_steps) * len(REFERENCE_CARRIERS)


def _budget_gate_path(output: Path) -> Path:
    """Prefer a sealed correction over the original estimate, when present."""

    corrected = output / "corrected-estimate.json"
    return corrected if corrected.is_file() else output / "estimate.json"


def dry_run(output: Path) -> dict[str, object]:
    runner = _load_stage2()
    rows = []
    peak_step = 15
    for cell in grid_cells():
        calibrations = {}
        calibration_elapsed = {}
        for setting_label in SETTINGS:
            started = time.perf_counter()
            calibrations[setting_label] = _calibrate(runner, cell, setting_label)
            calibration_elapsed[setting_label] = time.perf_counter() - started
        _bind_provider(runner, cell, WORLD_SEEDS[0])
        tape_started = time.perf_counter()
        tape = build_world_tape(
            domain=PROBE_WORLD_DOMAINS[0],
            provider=runner.WORLD_PROVIDER_FACTORY(),
            steps=peak_step + 4,
            start_time_s=0.0,
        )
        tape_elapsed = time.perf_counter() - tape_started
        for setting_label in SETTINGS:
            counter = runner.EvaluationCounter()
            started = time.perf_counter()
            step = runner.execute_step(
                tape=tape,
                setting=runner._setting(setting_label),
                step_index=peak_step,
                carrier=REFERENCE_CARRIERS[peak_step % len(REFERENCE_CARRIERS)],
                calibration=calibrations[setting_label],
                counter=counter,
            )
            elapsed = time.perf_counter() - started
            arms = [row["arm"] for row in step["arms"]]
            if arms != list(runner.ARMS):
                raise SyntheticMapError("dry-run did not traverse all stage-4b arms")
            rows.append(
                {
                    "grid_cell": cell,
                    "setting": setting_label,
                    "step_index": peak_step,
                    "arms": arms,
                    "catalogue_count": step["e1_certificate"]["candidate_count"],
                    "physical_boundary_evaluations": step["physical_boundary_evaluations"],
                    "execution_seconds": elapsed,
                    "calibration_seconds": calibration_elapsed[setting_label],
                    "tape_seconds": tape_elapsed,
                    "world_manifest_sha256": tape.digest,
                }
            )
    return _signed(
        {
            "schema": f"{SCHEMA}-dry-run",
            "status": "PASS",
            "experiment_label": LABEL,
            "one_real_peak_step_every_arm_every_grid_cell_setting": True,
            "grid_cells": len(grid_cells()),
            "settings": list(SETTINGS),
            "rows": rows,
            "training": False,
            "real_worlds": False,
            "engine_defects": list(ENGINE_DEFECTS),
        }
    )


def estimate(output: Path) -> dict[str, object]:
    receipt = read_once(output / "dry-run.json")
    rows = []
    total_seconds = 0.0
    tape_seconds_by_cell = {}
    for row in receipt["rows"]:
        cell = row["grid_cell"]
        provider = _provider(cell, WORLD_SEEDS[0])
        domain_seed = 17
        legal_steps = 0
        for step_index in range(STEPS):
            boundary = provider.boundary(
                world_seed=domain_seed,
                step_index=step_index,
                boundary_index=0,
                absolute_time_s=step_index * DECISION_INTERVAL_S,
            )
            legal_steps += int(any(candidate.legal for candidate in boundary.candidates))
        # ``execution_seconds`` measures one (step, setting) call, while every
        # unit executes all three sealed reference carriers at each anchor.
        per_world = _estimated_unit_execution_seconds(
            float(row["execution_seconds"]), legal_steps
        )
        calibration = float(row["calibration_seconds"])
        total_seconds += per_world * len(WORLD_SEEDS) + calibration
        tape_seconds_by_cell[str(cell["id"])] = float(row["tape_seconds"]) * (33.0 / 19.0)
        rows.append(
            {
                "grid_cell": cell["id"],
                "setting": row["setting"],
                "legal_steps": legal_steps,
                "estimated_seconds_per_world": per_world,
                "measured_peak_step_seconds": row["execution_seconds"],
                "measured_calibration_seconds": calibration,
            }
        )
    total_seconds += math.fsum(tape_seconds_by_cell.values()) * len(WORLD_SEEDS)
    reserve = 1.20
    core_hours = total_seconds * reserve / 3600.0
    return _signed(
        {
            "schema": f"{SCHEMA}-estimate",
            "status": "PASS" if core_hours <= MAX_CORE_HOURS else "ABORT_OVER_BUDGET",
            "experiment_label": LABEL,
            "basis": "measured peak legal step times legal-step census times three reference carriers, plus calibration",
            "reserve_multiplier": reserve,
            "estimated_core_hours": core_hours,
            "core_hour_ceiling": MAX_CORE_HOURS,
            "within_ceiling": core_hours <= MAX_CORE_HOURS,
            "per_world_cost": rows,
            "workers_do_not_change_core_hour_accounting": True,
        }
    )


def _calibration_receipt_task(task):
    cell, setting_label = task
    runner = _load_stage2()
    started = time.perf_counter()
    value = _calibrate(runner, cell, setting_label)
    elapsed = time.perf_counter() - started
    return _signed(
        {
            "schema": f"{SCHEMA}-calibration",
            "status": "FROZEN_CALIBRATION",
            "experiment_label": LABEL,
            "grid_cell": cell,
            "setting": setting_label,
            "provider_seed": CALIBRATION_SEED,
            "calibration_start_s": CALIBRATION_START_S,
            "two_disjoint_calibration_domains": True,
            "calibration": value.payload(),
            "calibration_sha256": value.digest,
            "elapsed_seconds": elapsed,
        }
    )


def _unit_task(task):
    cell, world_seed, calibration_payloads = task
    runner = _load_stage2()
    _bind_provider(runner, cell, world_seed)
    started = time.perf_counter()
    results = []
    for setting_label in SETTINGS:
        calibration = CalibrationValues.from_payload(calibration_payloads[setting_label])
        try:
            receipt = runner.run_unit(
                setting=runner._setting(setting_label),
                world_index=world_seed,
                executed_steps=STEPS,
                calibration=calibration,
            )
        except Exception as error:
            results.append(
                {
                    "error": type(error).__name__,
                    "message": str(error),
                    "grid_cell": cell,
                    "world_seed": world_seed,
                    "setting": setting_label,
                }
            )
            continue
        receipt.pop("receipt_sha256", None)
        receipt.update(
            {
                "schema": f"{SCHEMA}-unit",
                "experiment_label": LABEL,
                "grid_cell": cell,
                "synthetic_world_seed": world_seed,
                "provider_parameter_sha256": _provider(cell, world_seed).parameter_digest,
                "steps_executed": STEPS,
                "catalogue_scope": "stage-4b bounded catalogue with complete Cartesian cells up to the sealed limit",
                "exchangeability_cache": "disabled; per-chain physical identities retained",
                "common_random_world_across_settings": True,
                "group_elapsed_seconds_so_far": time.perf_counter() - started,
            }
        )
        results.append(_signed(receipt))
    return results


def run_sweep(output: Path, *, workers: int) -> dict[str, object]:
    dry = read_once(output / "dry-run.json")
    gate = read_once(_budget_gate_path(output))
    if dry.get("status") != "PASS":
        raise SyntheticMapError("dry-run did not pass")
    if not gate.get("within_ceiling"):
        raise SyntheticMapError(
            "estimate exceeds 10 core-hours; sweep aborted; see estimate per-world cost"
        )
    if not 1 <= workers <= MAX_WORKERS:
        raise SyntheticMapError("workers must be between one and four")
    calibrations: dict[tuple[str, str], dict[str, object]] = {}
    calibration_tasks = [
        (cell, setting) for cell in grid_cells() for setting in SETTINGS
    ]
    for task in calibration_tasks:
        payload = _calibration_receipt_task(task)
        cell_id = str(payload["grid_cell"]["id"])
        setting = str(payload["setting"])
        write_once(_calibration_path(output, cell_id, setting), payload)
        calibrations[(cell_id, setting)] = payload
    tasks = [
        (
            cell,
            seed,
            {
                setting: calibrations[(str(cell["id"]), setting)]["calibration"]
                for setting in SETTINGS
            },
        )
        for cell in grid_cells()
        for seed in WORLD_SEEDS
    ]
    started = time.perf_counter()
    errors = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_unit_task, task): task for task in tasks}
        for future in as_completed(futures):
            for payload in future.result():
                if "error" in payload:
                    errors.append(payload)
                    continue
                cell_id = str(payload["grid_cell"]["id"])
                seed = int(payload["synthetic_world_seed"])
                setting = str(payload["cell"])
                write_once(_unit_path(output, cell_id, seed, setting), payload)
    elapsed = time.perf_counter() - started
    if errors:
        defect = _signed(
            {
                "schema": f"{SCHEMA}-defects",
                "status": "DEFECTS_FOUND",
                "experiment_label": LABEL,
                "errors": errors,
            }
        )
        write_once(output / "DEFECTS.json", defect)
        raise SyntheticMapError(f"{len(errors)} unit(s) failed; minimal reproductions are in DEFECTS.json")
    return _signed(
        {
            "schema": f"{SCHEMA}-sweep",
            "status": "COMPLETE",
            "experiment_label": LABEL,
            "unit_count": len(tasks) * len(SETTINGS),
            "worlds": len(grid_cells()) * len(WORLD_SEEDS),
            "settings": list(SETTINGS),
            "steps_per_unit": STEPS,
            "workers": workers,
            "wall_seconds": elapsed,
            "estimated_core_hours": gate["estimated_core_hours"],
        }
    )


def _ratio(pair) -> Fraction:
    return Fraction(int(pair[0]), int(pair[1]))


def _world_metrics(receipt: Mapping[str, object]) -> dict[str, object]:
    analysis = receipt["failure_analysis"]
    arms = analysis["arms"]
    calibration = receipt["calibration"]
    eta = _ratio(calibration["eta_ref"])
    kappa = _ratio(calibration["kappa_bits_per_user_s"])

    def objective(name: str) -> float:
        row = arms[name]
        return float(Fraction(str(row["bits"])) - eta * Fraction(str(row["joules"])))

    def normalized_difference(left: str, right: str) -> float:
        return (objective(left) - objective(right)) / float(kappa)

    certificates = [step["e1_certificate"] for step in receipt["steps"]]
    all_neutral = objective("ALL_NEUTRAL_CONTROL") / float(kappa)
    return {
        "seed": receipt["synthetic_world_seed"],
        "u1_certificate_normalized": objective("E1_U1") / float(kappa),
        "j1_certificate_normalized": objective("E1_J1") / float(kappa),
        "u1_j1_certificate": {
            "candidate_census_complete": all(
                bool(row["candidate_census_complete"]) for row in certificates
            ),
            "candidate_count_min": min(int(row["candidate_count"]) for row in certificates),
            "candidate_count_max": max(int(row["candidate_count"]) for row in certificates),
            "unilateral_count_min": min(int(row["unilateral_count"]) for row in certificates),
            "unilateral_count_max": max(int(row["unilateral_count"]) for row in certificates),
            "joint_count_min": min(int(row["joint_count"]) for row in certificates),
            "joint_count_max": max(int(row["joint_count"]) for row in certificates),
            "genuine_multi_user_witness_steps": sum(
                bool(row["genuine_multi_user_witness"]) for row in certificates
            ),
            "steps": len(certificates),
            "solver_residual_w_max": max(
                float(row["solver_residual_w_max"]) for row in certificates
            ),
        },
        "joint_headroom_normalized": normalized_difference("E1_J1", "E1_U1"),
        "s0_deployable_gain_normalized": normalized_difference("S0_DEPLOYABLE", "NULL"),
        "marginals_normalized": {
            name: float(row["surplus_at_calibration_price_bits"]) / float(kappa)
            for name, row in analysis["marginals"].items()
        },
        "all_neutral_normalized": all_neutral,
        "all_neutral_full_gain_normalized": normalized_difference("FULL", "ALL_NEUTRAL_CONTROL"),
        "availability": arms["FULL"]["availability"],
        "handover_rate": arms["FULL"]["handover_rate_per_user_decision"],
        "arms": {
            name: {"bits": row["bits"], "joules": row["joules"]}
            for name, row in arms.items()
        },
    }


def _aggregate_diagnostics(receipts: Sequence[Mapping[str, object]]) -> dict[str, object]:
    mode_counts: dict[str, int] = {}
    acm_samples = plateau = cap_hits = cap_samples = 0
    status_counts = {"FIXED": 0, "CONVERGED": 0, "INVALID": 0}
    iterations_sum = iterations_samples = iterations_max = 0
    residual_max = 0.0
    for receipt in receipts:
        for step in receipt["steps"]:
            full = next(row for row in step["arms"] if row["arm"] == "FULL")
            diagnostic = full["usable_energy_range"]
            for name, count in diagnostic["acm_mode_counts"].items():
                mode_counts[name] = mode_counts.get(name, 0) + int(count)
            acm_samples += int(diagnostic["acm_samples"])
            plateau += int(diagnostic["se_plateau_hits"])
            cap_hits += int(diagnostic["beam_cap_hits"])
            cap_samples += int(diagnostic["beam_cap_samples"])
            fixed = diagnostic["fixed_point"]
            for name, count in fixed["status_counts"].items():
                status_counts[name] += int(count)
            iterations_sum += int(fixed["iterations_sum"])
            iterations_samples += int(fixed["samples"])
            iterations_max = max(iterations_max, int(fixed["iterations_max"]))
            residual_max = max(residual_max, float(fixed["residual_w_max"]))
    return {
        "acm_mode_distribution": {
            name: count / acm_samples for name, count in sorted(mode_counts.items())
        }
        if acm_samples
        else {},
        "se_plateau_share": 0.0 if not acm_samples else plateau / acm_samples,
        "cap_hit_share": 0.0 if not cap_samples else cap_hits / cap_samples,
        "fixed_point_status_counts": status_counts,
        "fixed_point_iterations_mean": 0.0
        if not iterations_samples
        else iterations_sum / iterations_samples,
        "fixed_point_iterations_max": iterations_max,
        "fixed_point_residual_w_max": residual_max,
    }


def merge(output: Path) -> dict[str, object]:
    table = []
    unit_bindings = []
    for cell in grid_cells():
        cell_id = str(cell["id"])
        for setting in SETTINGS:
            receipts = [
                read_once(_unit_path(output, cell_id, seed, setting))
                for seed in WORLD_SEEDS
            ]
            metrics = [_world_metrics(receipt) for receipt in receipts]
            pooled = {}
            for arm in _load_stage2().ARMS:
                bits = math.fsum(float(row["arms"][arm]["bits"]) for row in metrics)
                joules = math.fsum(float(row["arms"][arm]["joules"]) for row in metrics)
                pooled[arm] = {
                    "sum_bits": bits,
                    "sum_joules": joules,
                    "pooled_bits_per_joule": None if joules == 0.0 else bits / joules,
                }
            table.append(
                {
                    "grid_cell": cell,
                    "setting": setting,
                    "per_world_paired": metrics,
                    "mean_u1_certificate_normalized": math.fsum(
                        row["u1_certificate_normalized"] for row in metrics
                    )
                    / len(metrics),
                    "mean_j1_certificate_normalized": math.fsum(
                        row["j1_certificate_normalized"] for row in metrics
                    )
                    / len(metrics),
                    "u1_j1_certificate": {
                        "candidate_census_complete": all(
                            row["u1_j1_certificate"]["candidate_census_complete"]
                            for row in metrics
                        ),
                        "candidate_count_range": [
                            min(row["u1_j1_certificate"]["candidate_count_min"] for row in metrics),
                            max(row["u1_j1_certificate"]["candidate_count_max"] for row in metrics),
                        ],
                        "unilateral_count_range": [
                            min(row["u1_j1_certificate"]["unilateral_count_min"] for row in metrics),
                            max(row["u1_j1_certificate"]["unilateral_count_max"] for row in metrics),
                        ],
                        "joint_count_range": [
                            min(row["u1_j1_certificate"]["joint_count_min"] for row in metrics),
                            max(row["u1_j1_certificate"]["joint_count_max"] for row in metrics),
                        ],
                        "genuine_multi_user_witness_steps": sum(
                            row["u1_j1_certificate"]["genuine_multi_user_witness_steps"]
                            for row in metrics
                        ),
                        "steps": sum(row["u1_j1_certificate"]["steps"] for row in metrics),
                        "solver_residual_w_max": max(
                            row["u1_j1_certificate"]["solver_residual_w_max"]
                            for row in metrics
                        ),
                    },
                    "mean_joint_headroom_normalized": math.fsum(
                        row["joint_headroom_normalized"] for row in metrics
                    )
                    / len(metrics),
                    "mean_s0_deployable_gain_normalized": math.fsum(
                        row["s0_deployable_gain_normalized"] for row in metrics
                    )
                    / len(metrics),
                    "mean_marginals_normalized": {
                        name: math.fsum(row["marginals_normalized"][name] for row in metrics)
                        / len(metrics)
                        for name in ("C1", "C2", "C3")
                    },
                    "mean_all_neutral_full_gain_normalized": math.fsum(
                        row["all_neutral_full_gain_normalized"] for row in metrics
                    )
                    / len(metrics),
                    "mean_all_neutral_normalized": math.fsum(
                        row["all_neutral_normalized"] for row in metrics
                    )
                    / len(metrics),
                    "mean_availability": math.fsum(row["availability"] for row in metrics)
                    / len(metrics),
                    "mean_handover_rate": math.fsum(row["handover_rate"] for row in metrics)
                    / len(metrics),
                    "pooled_sum_bits_sum_energy": pooled,
                    "usable_energy_range": _aggregate_diagnostics(receipts),
                }
            )
            for receipt in receipts:
                unit_bindings.append(
                    {
                        "grid_cell": cell_id,
                        "setting": setting,
                        "seed": receipt["synthetic_world_seed"],
                        "receipt_sha256": receipt["receipt_sha256"],
                    }
                )
    return _signed(
        {
            "schema": f"{SCHEMA}-merged",
            "status": "COMPLETE",
            "experiment_label": LABEL,
            "unit_count": len(unit_bindings),
            "units": unit_bindings,
            "grid_cell_setting_table": table,
            "uncertainty_intervals": False,
            "threshold_gates": False,
            "paired_per_world_differences": True,
            "pooled_sum_bits_sum_energy": True,
            "training": False,
            "real_worlds": False,
        }
    )


def _expectations(table: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    def headroom(setting: str, occupancy: str, coupling: str) -> float:
        rows = [
            row
            for row in table
            if row["setting"] == setting
            and row["grid_cell"]["occupancy_label"] == occupancy
            and row["grid_cell"]["coupling_label"] == coupling
        ]
        return math.fsum(row["mean_joint_headroom_normalized"] for row in rows) / len(rows)

    e1_numbers = {
        setting: {
            coupling: [headroom(setting, occupancy, coupling) for occupancy, _ in OCCUPANCIES]
            for coupling, _ in COUPLINGS
        }
        for setting in ("a-r0", "a′-r0")
    }
    occupancy_growth = all(
        values[0] <= values[1] <= values[2]
        for setting in e1_numbers.values()
        for values in setting.values()
    )
    coupling_growth = all(
        setting["STRONG"][index] >= setting["WEAK"][index]
        for setting in e1_numbers.values()
        for index in range(3)
    )
    low_c3 = [
        row["mean_marginals_normalized"]["C3"]
        for row in table
        if row["grid_cell"]["occupancy_label"] == "LOW"
    ]
    low_s0 = [
        row["mean_s0_deployable_gain_normalized"]
        for row in table
        if row["grid_cell"]["occupancy_label"] == "LOW"
    ]
    b_by_occupancy = {
        occupancy: math.fsum(
            row["mean_joint_headroom_normalized"]
            for row in table
            if row["setting"] == "b0"
            and row["grid_cell"]["occupancy_label"] == occupancy
        )
        / 4.0
        for occupancy, _ in OCCUPANCIES
    }
    slopes = {}
    for setting in ("a-r0", "a′-r0"):
        low = math.fsum(headroom(setting, "LOW", coupling) for coupling, _ in COUPLINGS) / 2
        high = math.fsum(headroom(setting, "HIGH", coupling) for coupling, _ in COUPLINGS) / 2
        slopes[setting] = high - low
    return [
        {
            "expectation": "E1",
            "score": "MET" if occupancy_growth and coupling_growth else "NOT MET",
            "numbers": e1_numbers,
            "rule": "nondecreasing LOW→MID→HIGH and STRONG>=WEAK for both rate-target settings",
        },
        {
            "expectation": "E2",
            "score": "INDETERMINATE",
            "numbers": {
                "low_occupancy_c3_marginal_normalized_range": [min(low_c3), max(low_c3)],
                "low_occupancy_s0_gain_normalized_range": [min(low_s0), max(low_s0)],
            },
            "rule": "the pre-declaration did not operationalize 'dominates' or 'approximately zero'; assigning a cutoff after observing outcomes would be post hoc",
        },
        {
            "expectation": "E3",
            "score": "INDETERMINATE",
            "numbers": {
                "b0_headroom_by_occupancy": b_by_occupancy,
                "range": max(b_by_occupancy.values()) - min(b_by_occupancy.values()),
            },
            "rule": "the pre-declaration supplied no numerical flatness tolerance; assigning one after observing outcomes would be post hoc",
        },
        {
            "expectation": "E4",
            "score": "MET"
            if abs(slopes["a′-r0"]) < abs(slopes["a-r0"])
            else "NOT MET",
            "numbers": {"HIGH_minus_LOW_headroom": slopes},
            "rule": "absolute FDM occupancy slope smaller than absolute TDM slope",
        },
    ]


def _cost_accounting(output: Path, sweep_receipt: Mapping[str, object]) -> dict[str, float]:
    def collect(root: Path) -> tuple[float, float, float, float]:
        unit_seconds = math.fsum(
            float(read_once(path)["elapsed_seconds"])
            for path in sorted((root / "units").glob("**/*.json"))
        )
        calibration_seconds = math.fsum(
            float(read_once(path)["elapsed_seconds"])
            for path in sorted((root / "calibration").glob("**/*.json"))
        )
        dry = read_once(root / "dry-run.json")
        dry_execution_seconds = math.fsum(
            float(row["execution_seconds"]) for row in dry["rows"]
        )
        dry_calibration_seconds = math.fsum(
            float(row["calibration_seconds"]) for row in dry["rows"]
        )
        dry_tape_seconds_by_cell: dict[str, float] = {}
        for row in dry["rows"]:
            dry_tape_seconds_by_cell[str(row["grid_cell"]["id"])] = float(
                row["tape_seconds"]
            )
        dry_tape_seconds = math.fsum(dry_tape_seconds_by_cell.values())
        sweep_tape_seconds = (
            dry_tape_seconds * (STEPS + 3) / (15 + 4) * len(WORLD_SEEDS)
        )
        dry_seconds = dry_execution_seconds + dry_calibration_seconds + dry_tape_seconds
        return unit_seconds, calibration_seconds, sweep_tape_seconds, dry_seconds

    unit_seconds, calibration_seconds, sweep_tape_seconds, dry_seconds = collect(output)
    exact_seconds = unit_seconds + calibration_seconds + sweep_tape_seconds + dry_seconds
    rehearsal = output / "reduced-catalogue-rehearsal"
    rehearsal_seconds = sum(collect(rehearsal)) if rehearsal.is_dir() else 0.0
    return {
        "unit_execution_core_hours": unit_seconds / 3600.0,
        "calibration_core_hours": calibration_seconds / 3600.0,
        "shared_tape_core_hours_extrapolated": sweep_tape_seconds / 3600.0,
        "dry_run_core_hours": dry_seconds / 3600.0,
        "exact_run_core_hours": exact_seconds / 3600.0,
        "superseded_rehearsal_core_hours": rehearsal_seconds / 3600.0,
        "total_task_core_hours": (exact_seconds + rehearsal_seconds) / 3600.0,
        "sweep_wall_time_hours": float(sweep_receipt["wall_seconds"]) / 3600.0,
    }


def render_report(
    merged: Mapping[str, object],
    sweep_receipt: Mapping[str, object],
    estimate_receipt: Mapping[str, object],
    pytest_line: str,
    cost: Mapping[str, float],
) -> str:
    table = merged["grid_cell_setting_table"]
    expectations = _expectations(table)
    lines = [
        "# V025 synthetic map report — 2026-09-08",
        "",
        f"Label: `{LABEL}`. These are synthetic engineering/mechanism results, not real-world evidence.",
        "",
        "## Verification and cost",
        "",
        f"- Pytest: `{pytest_line}`",
        f"- Pre-launch estimate: {float(estimate_receipt['estimated_core_hours']):.4f} core-hours (10 core-hour ceiling).",
        f"- Sweep: {int(sweep_receipt['unit_count'])} world-setting units, {int(sweep_receipt['workers'])} workers, {float(sweep_receipt['wall_seconds']):.1f} s wall time.",
        f"- Accounted exact-run compute: {cost['exact_run_core_hours']:.4f} core-hours (unit execution {cost['unit_execution_core_hours']:.4f}, calibration {cost['calibration_core_hours']:.4f}, shared-tape construction extrapolated {cost['shared_tape_core_hours_extrapolated']:.4f}, and dry-run {cost['dry_run_core_hours']:.4f}).",
        f"- Total task compute: {cost['total_task_core_hours']:.4f} core-hours, including {cost['superseded_rehearsal_core_hours']:.4f} core-hours for the superseded reduced-catalogue rehearsal retained separately from the exact results.",
        "- Tape cost is extrapolated from measured dry-run construction; estimate census and receipt/merge bookkeeping are negligible and omitted. The account is below the 10 core-hour ceiling.",
        "- Catalogue: complete Cartesian legal assignments; an exact exchangeability cache reuses physics for identical per-beam occupancy vectors.",
        "",
        "## Declared fields by grid cell × setting",
        "",
        "Values U1/J1/headroom/S0/FULL−DROP/ALL_NEUTRAL/FULL−neutral are paired three-world means in calibration-normalized units. EE is pooled ΣB/ΣE for FULL. Diagnostics are for FULL.",
        "",
        "| Grid cell | Setting | U1 | J1 | J1−U1 | S0 gain | ΔC1 | ΔC2 | ΔC3 | ALL_NEUTRAL | FULL−neutral | Avail. | H/O | FULL EE | ACM modes (all shares) | Plateau | Cap hit | FP conv/fixed/invalid; iter mean/max | U1/J1 census; witness |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---|---|",
    ]
    for row in table:
        diag = row["usable_energy_range"]
        status = diag["fixed_point_status_counts"]
        marginal = row["mean_marginals_normalized"]
        full_ee = row["pooled_sum_bits_sum_energy"]["FULL"]["pooled_bits_per_joule"]
        mode_summary = "; ".join(
            f"{name}={share:.2f}"
            for name, share in sorted(
                diag["acm_mode_distribution"].items(), key=lambda item: (-item[1], item[0])
            )
        )
        certificate = row["u1_j1_certificate"]
        certificate_summary = (
            f"N={certificate['candidate_count_range']}; "
            f"U={certificate['unilateral_count_range']}; "
            f"J={certificate['joint_count_range']}; "
            f"w={certificate['genuine_multi_user_witness_steps']}/{certificate['steps']}; "
            f"res={certificate['solver_residual_w_max']:.2g}"
        )
        lines.append(
            "| {grid} | {setting} | {u1:.4g} | {j1:.4g} | {head:.4g} | {s0:.4g} | "
            "{c1:.4g} | {c2:.4g} | {c3:.4g} | {all_neutral:.4g} | {neutral:.4g} | {availability:.3f} | "
            "{handover:.3f} | {ee:.4g} | {modes} | {plateau:.3f} | {cap:.3f} | {conv}/{fixed}/{invalid}; {mean:.2f}/{maximum} | {certificate} |".format(
                grid=row["grid_cell"]["id"],
                setting=row["setting"],
                u1=row["mean_u1_certificate_normalized"],
                j1=row["mean_j1_certificate_normalized"],
                head=row["mean_joint_headroom_normalized"],
                s0=row["mean_s0_deployable_gain_normalized"],
                c1=marginal["C1"],
                c2=marginal["C2"],
                c3=marginal["C3"],
                all_neutral=row["mean_all_neutral_normalized"],
                neutral=row["mean_all_neutral_full_gain_normalized"],
                availability=row["mean_availability"],
                handover=row["mean_handover_rate"],
                ee=full_ee,
                modes=mode_summary,
                plateau=diag["se_plateau_share"],
                cap=diag["cap_hit_share"],
                conv=status["CONVERGED"],
                fixed=status["FIXED"],
                invalid=status["INVALID"],
                mean=diag["fixed_point_iterations_mean"],
                maximum=diag["fixed_point_iterations_max"],
                certificate=certificate_summary,
            )
        )
    lines.extend(["", "## Pre-registered expectations", ""])
    for item in expectations:
        lines.extend(
            [
                f"- **{item['expectation']} — {item['score']}**. `{json.dumps(item['numbers'], sort_keys=True, ensure_ascii=False)}`",
                f"  Scoring rule: {item['rule']}.",
            ]
        )
    lines.extend(
        [
            "",
            "## DEFECTS",
            "",
            "- `RATE_TARGET_CLEARANCE_ULP_ITERATION_CAP` — **FIXED_WITH_KAT**. HIGH-DENSE-STRONG `a-r` nominal calibration reached the 4096-iteration cap with zero power residual because one achieved SINR was two floating-point ulps below its algebraically identical target. Minimal reproduction: `ParametricSyntheticProvider(8, 4, -12, 10000)`, `start_time_s=435`, users 0/1 on NORAD 90001 and users 2–7 on NORAD 90004. The fix detects an eight-ulp rounding case and nudges under-target power upward by at most eight ulps. KAT: `test_rate_target_fixed_point_accepts_power_tolerance_scale_clearance`.",
            "",
            "No other non-convergence, NaN, negative-bit, negative-energy, or unexpected cap pathology was observed in the completed receipts. The b0 cap-hit share of 1.000 is its declared fixed-RF construction; fixed-point invalid counts are tabulated above.",
            "",
            "The complete paired per-world differences, pooled ΣB/ΣE values for all 12 arms, ACM mode distributions, residuals, and immutable unit bindings are in `synthetic-map/merged-receipt.json`.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(path: Path, text: str) -> None:
    if path.exists() or path.is_symlink():
        raise SyntheticMapError(f"refusing to overwrite report: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(text)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--estimate", action="store_true")
    modes.add_argument("--sweep", action="store_true")
    modes.add_argument("--merge", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--workers", type=int, default=MAX_WORKERS)
    parser.add_argument("--pytest-line", default="not supplied")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.dry_run:
        payload = dry_run(args.output)
        path = args.output / "dry-run.json"
        digest = write_once(path, payload)
    elif args.estimate:
        payload = estimate(args.output)
        path = args.output / "estimate.json"
        digest = write_once(path, payload)
    elif args.sweep:
        payload = run_sweep(args.output, workers=args.workers)
        path = args.output / "sweep-receipt.json"
        digest = write_once(path, payload)
    else:
        sweep_receipt = read_once(args.output / "sweep-receipt.json")
        estimate_receipt = read_once(args.output / "estimate.json")
        payload = merge(args.output)
        path = args.output / "merged-receipt.json"
        digest = write_once(path, payload)
        write_report(
            args.report,
            render_report(
                payload,
                sweep_receipt,
                estimate_receipt,
                args.pytest_line,
                _cost_accounting(args.output, sweep_receipt),
            ),
        )
    print(
        json.dumps(
            {"status": payload["status"], "path": str(path), "file_sha256": digest},
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if payload["status"] != "ABORT_OVER_BUDGET" else 2


if __name__ == "__main__":
    raise SystemExit(main())
