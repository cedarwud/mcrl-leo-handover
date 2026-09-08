#!/usr/bin/env python3
"""Nine-arm C3-S variant-matrix runner; no implicit formal execution."""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Callable, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
V1_DIR = REPO / ".scratch" / "multi-catfish-v023-c3s-screen"
for _path in (HERE, V1_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_v023_c3s_screen as v1runner  # noqa: E402
import variant_policy  # noqa: E402


SCHEMA = "multi-catfish-mcrl-v023-c3s-variant-matrix-v1"
PREFLIGHT_SCHEMA = f"{SCHEMA}-preflight-manifest"
AUTHORITY_SCHEMA = f"{SCHEMA}-launch-authority"
UNIT_SCHEMA = f"{SCHEMA}-unit-receipt"
TERMINAL_SCHEMA = f"{SCHEMA}-terminal-receipt"
CLAIM_CEILING = "TRAIN_DEVELOPMENT_C3S_VARIANT_MATRIX_NO_LEARNER_NO_EFFICACY_NO_TEST"
CONTRACT_PATH = HERE / "V023-C3S-VARIANT-MATRIX-KILL-SCREEN-CONTRACT-2026-09-08.md"
CONFIG_PATH = HERE / "variants_config.json"
DEFAULT_PREFLIGHT = HERE / "C3S-VARIANTS-PREFLIGHT-MANIFEST.json"
DEFAULT_OUTPUT = HERE / "run-output"
CANONICAL_INTERPRETER = Path("/home/sat/mcrl-leo-handover/.venv/bin/python")
THREAD_ENV = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")
CONSTANTS = variant_policy.load_constants(CONFIG_PATH)
ARMS = tuple(CONSTANTS["arms"])
COORDINATOR_ARMS = ARMS[1:]
VE_ARM = variant_policy.VE_ARM
WORLDS = tuple(int(value) for value in CONSTANTS["worlds"])
LINEAGES = tuple(int(value) for value in CONSTANTS["lineages"])
HORIZON = int(CONSTANTS["horizon_steps"])
USERS = int(CONSTANTS["users"])
SERVICE_MARGIN = variant_policy._fraction(CONSTANTS["service_margin"], field_name="service margin")
LATENCY_THRESHOLD = variant_policy._fraction(CONSTANTS["latency_threshold_seconds"], field_name="latency threshold")
REVERSAL_WINDOW = int(CONSTANTS["association_reversal_window_steps"])
ALL_UNITS = tuple(v1runner.UnitKey(world, lineage) for world in WORLDS for lineage in LINEAGES)


class VariantRunnerError(RuntimeError):
    pass


class MergeWaiting(VariantRunnerError):
    def __init__(self, missing: int) -> None:
        self.missing = missing
        super().__init__(f"{missing} units missing")


def canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as error:
        raise VariantRunnerError("artifact is not finite canonical ASCII JSON") from error


def file_sha256(path: Path) -> str:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise VariantRunnerError(f"required regular file is absent or symlinked: {target}")
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _local(path: Path, *, field_name: str) -> Path:
    target = (Path.cwd() / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    if not target.is_relative_to(HERE.resolve()):
        raise VariantRunnerError(f"{field_name} must remain inside {HERE}")
    return target


def _validate_sealed(path: Path, *, digest: str, field_name: str) -> None:
    target = Path(path)
    sidecar = target.with_suffix(".sha256")
    try:
        valid = (
            not target.is_symlink() and target.is_file() and target.stat().st_mode & 0o777 == 0o444
            and not sidecar.is_symlink() and sidecar.is_file() and sidecar.stat().st_mode & 0o777 == 0o444
            and sidecar.read_text(encoding="ascii").split() == [digest, target.name]
            and file_sha256(target) == digest
        )
    except (OSError, UnicodeError):
        valid = False
    if not valid:
        raise VariantRunnerError(f"{field_name} is not sealed mode-0444 with matching sidecar")


def sealed_contract_binding() -> dict[str, str]:
    try:
        digest = file_sha256(CONTRACT_PATH)
        _validate_sealed(CONTRACT_PATH, digest=digest, field_name="variant contract")
    except VariantRunnerError:
        raise VariantRunnerError(
            f"controller must place and seal the contract placeholder at {CONTRACT_PATH}"
        ) from None
    return {"path": str(CONTRACT_PATH.resolve()), "sha256": digest}


def write_once_with_sidecar(path: Path, payload: Mapping[str, object]) -> tuple[Path, Path, str]:
    target = _local(path, field_name="write-once artifact")
    sidecar = target.with_suffix(".sha256")
    if target.exists() or target.is_symlink() or sidecar.exists() or sidecar.is_symlink():
        raise VariantRunnerError("refusing to overwrite write-once artifact or sidecar")
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = canonical_bytes(payload) + b"\n"
    with target.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    target.chmod(0o444)
    digest = file_sha256(target)
    with sidecar.open("xb") as handle:
        handle.write(f"{digest}  {target.name}\n".encode("ascii"))
        handle.flush()
        os.fsync(handle.fileno())
    sidecar.chmod(0o444)
    _validate_sealed(target, digest=digest, field_name="published artifact")
    return target, sidecar, digest


def load_json(path: Path, *, field_name: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise VariantRunnerError(f"{field_name} is not valid ASCII JSON") from error
    if not isinstance(value, dict):
        raise VariantRunnerError(f"{field_name} must be a JSON object")
    return value


def fraction_payload(value: Fraction) -> dict[str, str]:
    return v1runner.fraction_payload(value)


def _from_payload(value: object) -> Fraction:
    if not isinstance(value, Mapping):
        raise VariantRunnerError("exact rational payload is malformed")
    try:
        return Fraction(int(value["numerator"]), int(value["denominator"]))
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
        raise VariantRunnerError("exact rational payload is malformed") from error


def expected_code_bindings() -> list[dict[str, str]]:
    own = [CONFIG_PATH, *sorted(HERE.glob("*.py"))]
    rows = [{"role": f"variant:{path.name}", "path": str(path.resolve()), "sha256": file_sha256(path)} for path in own]
    rows.extend(v1runner.expected_code_bindings())
    return sorted(rows, key=lambda row: (row["path"], row["role"]))


def active_arms(*, enable_ve: bool = False) -> tuple[str, ...]:
    """Return the sealed nine arms unless the tenth arm is explicitly enabled."""

    return (*ARMS, VE_ARM) if enable_ve else ARMS


def panel_bindings(horizon: int = HORIZON, *, enable_ve: bool = False) -> dict[str, object]:
    if horizon != HORIZON:
        raise VariantRunnerError("variant matrix horizon differs from configured horizon")
    arms = active_arms(enable_ve=enable_ve)
    result = {
        "worlds": list(WORLDS), "lineages": list(LINEAGES), "units": len(ALL_UNITS),
        "episodes": len(ALL_UNITS) * len(arms), "users": USERS, "horizon": horizon,
        "arms": list(arms), "split": "TRAIN", "trajectory_rule": (
            "TEN_INDEPENDENT_MATCHED_INITIAL_STATES" if enable_ve
            else "NINE_INDEPENDENT_MATCHED_INITIAL_STATES"
        ),
        "kill_rule": {"ee": "STRICTLY_ABOVE_BASE", "service_floor": "BASE_MINUS_SERVICE_MARGIN",
                      "service_margin": fraction_payload(SERVICE_MARGIN)},
    }
    if enable_ve:
        ve = variant_policy.load_ve_config(CONFIG_PATH)
        result["ve_opt_in"] = {
            "enabled_by_cli": True,
            "arm_config": ve,
            "scenario_seeds": list(variant_policy.ve_scenario_seeds(CONFIG_PATH)),
        }
    return result


def pin_single_thread_runtime() -> None:
    if Path(sys.executable).resolve() != CANONICAL_INTERPRETER.resolve():
        raise VariantRunnerError(f"runner requires interpreter {CANONICAL_INTERPRETER}")
    if any(os.environ.get(name) != "1" for name in THREAD_ENV):
        raise VariantRunnerError("all OMP/BLAS numerical thread variables must equal 1")
    v1runner.pin_single_thread_runtime()


def validate_static_bindings() -> dict[str, object]:
    if WORLDS != v1runner.WORLDS or LINEAGES != v1runner.LINEAGES or USERS != v1runner.USERS:
        raise VariantRunnerError("variant panel disagrees with the v1 authenticated panel")
    return {
        "contract": sealed_contract_binding(), "panel": panel_bindings(),
        "variant_config": {"path": str(CONFIG_PATH.resolve()), "sha256": file_sha256(CONFIG_PATH)},
        "code_files": expected_code_bindings(),
        "v1_static_bindings": v1runner.validate_static_bindings(),
    }


def _external_sealed_binding(path: Path, *, field_name: str) -> dict[str, str]:
    target = Path(path).resolve()
    digest = file_sha256(target)
    v1runner._validate_sealed(target, digest=digest, field=field_name)
    return {"path": str(target), "sha256": digest}


def validate_freeze(timestamp: str, reviewer: str) -> dict[str, str]:
    return v1runner.validate_freeze_metadata({"timestamp_utc": timestamp, "reviewer": reviewer})


def build_preflight(
    *, evidence_manifest: Path, world_census: Path, freeze_timestamp_utc: str, reviewer: str,
) -> dict[str, object]:
    evidence = _external_sealed_binding(evidence_manifest, field_name="variant evidence manifest")
    census = _external_sealed_binding(world_census, field_name="variant world census")
    v1runner.validate_evidence_manifest(evidence)
    v1runner.validate_world_census(census)
    return {
        "schema": PREFLIGHT_SCHEMA, "status": "FROZEN_PREFLIGHT", "claim_ceiling": CLAIM_CEILING,
        **validate_static_bindings(), "evidence_manifest": evidence, "world_census": census,
        "freeze": validate_freeze(freeze_timestamp_utc, reviewer),
    }


def validate_preflight(path: Path) -> tuple[dict[str, Any], str]:
    target = _local(path, field_name="preflight manifest")
    digest = file_sha256(target)
    _validate_sealed(target, digest=digest, field_name="preflight manifest")
    payload = load_json(target, field_name="preflight manifest")
    if payload.get("schema") != PREFLIGHT_SCHEMA or payload.get("status") != "FROZEN_PREFLIGHT":
        raise VariantRunnerError("preflight schema/status drifted")
    expected_static = validate_static_bindings()
    for key, value in expected_static.items():
        if payload.get(key) != value:
            raise VariantRunnerError(f"preflight static binding drifted: {key}")
    v1runner.validate_evidence_manifest(payload.get("evidence_manifest"))
    v1runner.validate_world_census(payload.get("world_census"))
    v1runner.validate_freeze_metadata(payload.get("freeze"))
    return payload, digest


def build_authority(
    *, preflight: Path, contract: Path, output_root: Path,
    launch_arguments: Sequence[str], authority_path: Path,
) -> dict[str, object]:
    manifest, preflight_sha = validate_preflight(preflight)
    contract_binding = sealed_contract_binding()
    if str(Path(contract).resolve()) != contract_binding["path"]:
        raise VariantRunnerError("authority must bind the exact controller-sealed contract placeholder")
    destination = _local(output_root, field_name="output root")
    authority = _local(authority_path, field_name="launch authority")
    parsed = _parser().parse_args(list(launch_arguments))
    target = v1runner.UnitKey.parse(parsed.unit) if parsed.unit else None
    if (
        parsed.dry_run or parsed.estimate or (target is None) == (not parsed.merge)
        or parsed.launch_authority is None or Path(parsed.launch_authority).resolve() != authority
        or Path(parsed.preflight_manifest).resolve() != Path(preflight).resolve()
        or _local(parsed.output, field_name="output root") != destination or parsed.horizon != HORIZON
    ):
        raise VariantRunnerError("launch arguments do not bind one exact unit/merge invocation")
    return {
        "schema": AUTHORITY_SCHEMA, "status": "FROZEN_LAUNCH_AUTHORITY", "claim_ceiling": CLAIM_CEILING,
        "contract": contract_binding,
        "preflight_manifest": {"path": str(Path(preflight).resolve()), "sha256": preflight_sha},
        "code_files": expected_code_bindings(), "panel": panel_bindings(enable_ve=parsed.enable_ve),
        "freeze_provenance": {key: manifest[key] for key in ("evidence_manifest", "world_census", "freeze")},
        "execution": {"mode": "unit" if target else "merge", "unit": None if target is None else target.as_dict()},
        "output_root": str(destination), "launch_arguments": list(launch_arguments),
        "test_split_opened": False, "episode_training": False, "learner_update": False, "efficacy_claim": False,
    }


def validate_authority(
    path: Path, *, preflight: Path, preflight_sha: str, output: Path,
    launch_arguments: Sequence[str], target: Any | None,
) -> tuple[dict[str, Any], str]:
    authority_path = _local(path, field_name="launch authority")
    digest = file_sha256(authority_path)
    _validate_sealed(authority_path, digest=digest, field_name="launch authority")
    payload = load_json(authority_path, field_name="launch authority")
    expected = build_authority(
        preflight=preflight, contract=CONTRACT_PATH, output_root=output,
        launch_arguments=launch_arguments, authority_path=authority_path,
    )
    if payload != expected or payload["preflight_manifest"]["sha256"] != preflight_sha:
        raise VariantRunnerError("launch authority does not bind this exact invocation")
    expected_unit = None if target is None else target.as_dict()
    if payload["execution"]["unit"] != expected_unit:
        raise VariantRunnerError("launch authority unit drifted")
    return payload, digest


def authority_common_binding(authority: Mapping[str, object]) -> dict[str, object]:
    return {
        key: authority.get(key)
        for key in (
            "contract", "preflight_manifest", "code_files", "panel",
            "freeze_provenance", "output_root",
        )
    }


def _cumulative(steps: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    bits = energy = Fraction(0)
    served = opportunities = 0
    rows = []
    for step in steps:
        bits += v1runner._exact_hex(step["bits_hex"], field="bits")
        energy += v1runner._exact_hex(step["energy_j_hex"], field="energy", positive=True)
        served += int(step["served"])
        opportunities += int(step["opportunities"])
        rows.append({"step_index": int(step["step_index"]), "eta": fraction_payload(bits / energy),
                     "service": fraction_payload(Fraction(served, opportunities))})
    return rows


def _trace_selector(
    selector: Callable[[Any, Any, np.random.Generator], np.ndarray],
    trace: list[tuple[tuple[int, int] | None, ...]],
) -> Callable[[Any, Any, np.random.Generator], np.ndarray]:
    def wrapped(step_env: Any, observation: Any, rng: np.random.Generator) -> np.ndarray:
        actions = np.asarray(selector(step_env, observation, rng), dtype=np.int64)
        physical: list[tuple[int, int] | None] = []
        for action, table in zip(actions.tolist(), observation.candidates.slot_tables, strict=True):
            physical.append(None if action < 0 else (int(table.norad_ids[action]), int(table.cell_ids[action])))
        trace.append(tuple(physical))
        return actions
    return wrapped


def execute_physical_unit(
    key: Any, *, horizon: int, arms: Sequence[str] = ARMS,
) -> dict[str, object]:
    from mcrl.env.keyed_fading import KeyedFadingField
    from mcrl.runtime.prereg import read_prereg
    from mcrl.runtime.training_pipeline import _evaluation_rngs

    key.verify()
    record = read_prereg(v1runner.f1.PREREG_PATH)
    if record.digest != v1runner.f1.PREREG_RECORD_DIGEST:
        raise VariantRunnerError("TRAIN PREREG semantic digest changed")
    physical, server = v1runner.f1._runtime_modules()
    frozen = v1runner.f2._load_frozen_heads(key.lineage)
    q_before = (physical._parameter_sha256(frozen.q1), physical._parameter_sha256(frozen.q2))
    trajectories: dict[str, dict[str, object]] = {}
    adapters: dict[str, variant_policy.VariantPolicyAdapter] = {}
    with tempfile.TemporaryDirectory(prefix=f"c3s-variants-{key.slug}-", dir=os.environ.get("TMPDIR")) as temporary:
        archive = server._freeze_archive(
            record, v1runner.CANONICAL_TLE_ROOT, Path(temporary) / "frozen", physical
        )
        for arm in arms:
            environment = v1runner._make_environment(archive, horizon=horizon)
            environment.environment._fading_field = KeyedFadingField.from_components(v1runner.FIELD_COMPONENT, key.world)
            rngs = tuple(_evaluation_rngs(key.world))
            if arm == "BASE":
                def selector(step_env: Any, observation: Any, _rng: np.random.Generator) -> np.ndarray:
                    return v1runner.e1._q12_surface_base_only(physical, frozen, step_env, observation)[2]
            else:
                adapter = variant_policy.VariantPolicyAdapter(physical=physical, frozen=frozen, arm=arm)
                adapters[arm] = adapter
                selector = adapter.select_actions
            trace: list[tuple[tuple[int, int] | None, ...]] = []
            trajectory = v1runner.run_arm_trajectory(
                environment=environment, env_rng=rngs[0], mobility_rng=rngs[1], horizon=horizon,
                selector=_trace_selector(selector, trace),
            )
            trajectory["cumulative_curve"] = _cumulative(trajectory["steps"])
            trajectory["association_reversals_within_3_steps"] = variant_policy.association_reversals(
                trace, window=REVERSAL_WINDOW
            )
            trajectory["catalog_sizes"] = (
                [1] * horizon
                if arm == "BASE"
                else [int(row["catalog_size"]) for row in adapters[arm].decision_records]
            )
            trajectories[arm] = trajectory
    coordinator_arms = tuple(arms[1:])
    if len({trajectory["initial_state_sha256"] for trajectory in trajectories.values()}) != 1:
        raise VariantRunnerError("matched arms do not share the same authenticated initial state")
    if len({id(adapter) for adapter in adapters.values()}) != len(coordinator_arms):
        raise VariantRunnerError("coordinator arms are not independent adapter instances")
    q_after = (physical._parameter_sha256(frozen.q1), physical._parameter_sha256(frozen.q2))
    if q_before != q_after:
        raise VariantRunnerError("authenticated Q heads changed during inference")
    decisions = {arm: adapters[arm].decision_records for arm in coordinator_arms}
    return {
        "schema": UNIT_SCHEMA, "status": "COMPLETE", "outcome": "C3S_VARIANT_MATRIX_UNIT_COMPLETE",
        "claim_ceiling": CLAIM_CEILING, "unit": key.as_dict(), "horizon": horizon, "users": USERS,
        "arms": trajectories, "decisions_by_arm": decisions,
        "action_changes_by_arm": {arm: sum(bool(row["action_changed"]) for row in decisions[arm]) for arm in coordinator_arms},
        "integrity": True, "test_split_opened": False, "episode_training": False,
        "learner_update": False, "efficacy_claim": False,
    }


def _latency(values: Sequence[float]) -> dict[str, object]:
    if not values or any(not math.isfinite(value) or value < 0 for value in values):
        raise VariantRunnerError("latency sample is empty or invalid")
    ordered = sorted(values)
    threshold = float(LATENCY_THRESHOLD)
    return {
        "count": len(values), "mean_hex": (math.fsum(values) / len(values)).hex(),
        "median_hex": ((ordered[(len(ordered) - 1) // 2] + ordered[len(ordered) // 2]) / 2).hex(),
        "p95_nearest_rank_hex": ordered[math.ceil(0.95 * len(ordered)) - 1].hex(),
        "maximum_hex": ordered[-1].hex(), "threshold_seconds": str(CONSTANTS["latency_threshold_seconds"]),
        "latency_over_threshold_count": sum(value > threshold for value in values),
    }


def pool_unit_receipts(
    receipts: Sequence[Mapping[str, object]], *, arms: Sequence[str] = ARMS,
) -> dict[str, object]:
    coordinator_arms = tuple(arms[1:])
    totals = {arm: {"bits": Fraction(0), "energy": Fraction(0), "served": 0, "opportunities": 0} for arm in arms}
    changes = {arm: 0 for arm in coordinator_arms}
    reversals = {arm: 0 for arm in arms}
    wall = {arm: [] for arm in arms}
    catalog = {arm: [] for arm in arms}
    curve_steps: dict[str, list[list[Mapping[str, object]]]] = {arm: [] for arm in arms}
    for receipt in receipts:
        receipt_arms = receipt.get("arms")
        decisions = receipt.get("decisions_by_arm")
        if not isinstance(receipt_arms, Mapping) or set(receipt_arms) != set(totals):
            raise VariantRunnerError("unit arm coverage is malformed")
        if not isinstance(decisions, Mapping) or set(decisions) != set(coordinator_arms):
            raise VariantRunnerError("unit decision coverage is malformed")
        for arm in totals:
            trajectory = receipt_arms[arm]
            curve_steps[arm].append(trajectory["steps"])
            reversals[arm] += int(trajectory["association_reversals_within_3_steps"])
            wall[arm].extend(float.fromhex(str(value)) for value in trajectory["decision_wall_seconds_hex"])
            sizes = trajectory.get("catalog_sizes")
            if not isinstance(sizes, list) or len(sizes) != len(trajectory["steps"]):
                raise VariantRunnerError("unit catalog-size trace is malformed")
            catalog[arm].extend(int(value) for value in sizes)
            for step in trajectory["steps"]:
                totals[arm]["bits"] += v1runner._exact_hex(step["bits_hex"], field="bits")
                totals[arm]["energy"] += v1runner._exact_hex(step["energy_j_hex"], field="energy", positive=True)
                totals[arm]["served"] += int(step["served"])
                totals[arm]["opportunities"] += int(step["opportunities"])
        for arm in coordinator_arms:
            changes[arm] += sum(bool(row["action_changed"]) for row in decisions[arm])
    exact: dict[str, dict[str, object]] = {}
    for arm, row in totals.items():
        bits, energy = row["bits"], row["energy"]
        served, opportunities = int(row["served"]), int(row["opportunities"])
        exact[arm] = {"total_bits": fraction_payload(bits), "total_energy_j": fraction_payload(energy),
                      "eta": fraction_payload(bits / energy), "served": served, "opportunities": opportunities,
                      "service": fraction_payload(Fraction(served, opportunities))}
    base_eta = _from_payload(exact["BASE"]["eta"])
    base_service = _from_payload(exact["BASE"]["service"])
    dispositions = {}
    for arm in coordinator_arms:
        reasons = []
        if _from_payload(exact[arm]["eta"]) <= base_eta:
            reasons.append("EE_NOT_STRICTLY_ABOVE_BASE")
        if _from_payload(exact[arm]["service"]) < base_service - SERVICE_MARGIN:
            reasons.append("SERVICE_MARGIN_FAILED")
        dispositions[arm] = {"outcome": "SUPPORT" if not reasons else "NO_SUPPORT", "reasons": reasons}
    cumulative = {}
    for arm, unit_steps in curve_steps.items():
        rows = []
        bits = energy = Fraction(0)
        served = opportunities = 0
        for index in range(HORIZON):
            for steps in unit_steps:
                step = steps[index]
                bits += v1runner._exact_hex(step["bits_hex"], field="bits")
                energy += v1runner._exact_hex(step["energy_j_hex"], field="energy", positive=True)
                served += int(step["served"]); opportunities += int(step["opportunities"])
            rows.append({"step_index": index, "eta": fraction_payload(bits / energy),
                         "service": fraction_payload(Fraction(served, opportunities))})
        cumulative[arm] = rows
    return {
        "arms": exact, "decisions": dispositions, "cumulative_curves": cumulative,
        "action_changes_by_arm": {"BASE": 0, **changes}, "association_reversals_by_arm": reversals,
        "latency_by_arm": {arm: _latency(values) for arm, values in wall.items()},
        "catalog_sizes_by_arm": {
            arm: {"minimum": min(values), "maximum": max(values), "mean": math.fsum(values) / len(values)}
            for arm, values in catalog.items()
        },
        "units": len(receipts),
    }


def descriptive_breakdowns(
    receipts: Sequence[Mapping[str, object]], *, arms: Sequence[str] = ARMS,
) -> dict[str, object]:
    result = {}
    for label, field_name, values in (("per_world", "world", WORLDS), ("per_lineage", "lineage", LINEAGES)):
        result[label] = {
            str(value): pool_unit_receipts(
                [row for row in receipts if row["unit"][field_name] == value], arms=arms,
            )
            for value in values
        }
    return result


def _unit_path(root: Path, key: Any) -> Path:
    return root / "units" / key.slug / "receipt.json"


def execute_unit(
    *, key: Any, output: Path, authority: Mapping[str, object], authority_sha: str,
    preflight_sha: str, enable_ve: bool = False,
) -> Path:
    root = _local(output, field_name="output root")
    path = _unit_path(root, key)
    if path.exists() or path.is_symlink():
        digest = file_sha256(path); _validate_sealed(path, digest=digest, field_name="unit receipt")
        existing = load_json(path, field_name="unit receipt")
        if (
            existing.get("schema") != UNIT_SCHEMA
            or existing.get("status") != "COMPLETE"
            or existing.get("unit") != key.as_dict()
            or existing.get("preflight_manifest_sha256") != preflight_sha
            or existing.get("launch_authority_sha256") != authority_sha
            or existing.get("producer_common_binding") != authority_common_binding(authority)
        ):
            raise VariantRunnerError("existing unit receipt is not reusable")
        return path
    payload = execute_physical_unit(
        key, horizon=HORIZON, arms=active_arms(enable_ve=enable_ve),
    )
    payload.update({"preflight_manifest_sha256": preflight_sha, "launch_authority_sha256": authority_sha,
                    "launch_authority": {"path": str(Path(authority["__path__"])), "sha256": authority_sha},
                    "producer_common_binding": authority_common_binding(authority)})
    return write_once_with_sidecar(path, payload)[0]


def execute_merge(
    *, output: Path, authority: Mapping[str, object], authority_sha: str,
    preflight_sha: str, enable_ve: bool = False,
) -> Path:
    root = _local(output, field_name="output root")
    terminal = root / "terminal-receipt.json"
    if terminal.exists() or terminal.is_symlink():
        digest = file_sha256(terminal); _validate_sealed(terminal, digest=digest, field_name="terminal receipt")
        existing = load_json(terminal, field_name="terminal receipt")
        if (
            existing.get("schema") != TERMINAL_SCHEMA
            or existing.get("status") != "COMPLETE"
            or existing.get("preflight_manifest_sha256") != preflight_sha
            or existing.get("launch_authority_sha256") != authority_sha
        ):
            raise VariantRunnerError("existing terminal receipt is not reusable")
        return terminal
    receipts, bindings = [], []
    for key in ALL_UNITS:
        path = _unit_path(root, key)
        if not path.exists():
            continue
        digest = file_sha256(path); _validate_sealed(path, digest=digest, field_name=f"unit {key.slug}")
        receipt = load_json(path, field_name=f"unit {key.slug}")
        producer = receipt.get("launch_authority")
        if not isinstance(producer, Mapping) or set(producer) != {"path", "sha256"}:
            raise VariantRunnerError(f"unit {key.slug} lacks producer authority")
        producer_path = _local(Path(str(producer["path"])), field_name="producer authority")
        producer_sha = str(producer["sha256"])
        _validate_sealed(producer_path, digest=producer_sha, field_name="producer authority")
        producer_payload = load_json(producer_path, field_name="producer authority")
        if (
            (receipt.get("schema"), receipt.get("status"), receipt.get("unit"))
            != (UNIT_SCHEMA, "COMPLETE", key.as_dict())
            or receipt.get("preflight_manifest_sha256") != preflight_sha
            or receipt.get("launch_authority_sha256") != producer_sha
            or producer_payload.get("schema") != AUTHORITY_SCHEMA
            or producer_payload.get("status") != "FROZEN_LAUNCH_AUTHORITY"
            or producer_payload.get("execution") != {"mode": "unit", "unit": key.as_dict()}
            or authority_common_binding(producer_payload) != authority_common_binding(authority)
            or receipt.get("producer_common_binding") != authority_common_binding(authority)
        ):
            raise VariantRunnerError(f"unit {key.slug} is invalid")
        receipts.append(receipt); bindings.append({"unit": key.as_dict(), "path": str(path), "sha256": digest})
    if len(receipts) != len(ALL_UNITS):
        raise MergeWaiting(len(ALL_UNITS) - len(receipts))
    arms = active_arms(enable_ve=enable_ve)
    pooled = pool_unit_receipts(receipts, arms=arms)
    payload = {
        "schema": TERMINAL_SCHEMA, "status": "COMPLETE", "outcome": "C3S_VARIANT_MATRIX_COMPLETE",
        "claim_ceiling": CLAIM_CEILING, "panel": panel_bindings(enable_ve=enable_ve), "pooled": pooled,
        **descriptive_breakdowns(receipts, arms=arms), "unit_receipts": bindings,
        "preflight_manifest_sha256": preflight_sha, "launch_authority_sha256": authority_sha,
        "integrity": True, "test_split_opened": False, "episode_training": False,
        "learner_update": False, "efficacy_claim": False,
    }
    return write_once_with_sidecar(terminal, payload)[0]


def estimate(*, units: int, enable_ve: bool = False) -> dict[str, object]:
    if type(units) is not int or units < 1:
        raise VariantRunnerError("estimate units must be a positive integer")
    source = v1runner.estimate(units=units)
    base_horizon = source["horizons"][str(HORIZON)]["arms"]
    full_evaluations = _from_payload(base_horizon["FULL"]["projected_nominal_evaluations_exact"])
    full_hours = float(base_horizon["FULL"]["worker_hours"])
    ratios = {"BASE": Fraction(0), "LITE": Fraction(1, 10), "V-J": Fraction(1, 10),
              "V-U": Fraction(1, 10), "V-M": Fraction(1, 10), "V-C": Fraction(1, 30),
              "V-H": Fraction(1, 10), "V-P": Fraction(1, 10), "V-L2": Fraction(1, 5)}
    arms = {}
    for arm in ARMS:
        ratio = ratios[arm]
        arms[arm] = {"projected_nominal_evaluations_exact": fraction_payload(full_evaluations * ratio),
                     "worker_hours": full_hours * float(ratio), "relative_to_v1_full": fraction_payload(ratio)}
    arms["V-P"]["additional_cost"] = "OPS3_TLE_D2_PROJECTION_NOT_INCLUDED_IN_NOMINAL_EVALUATION_BASIS"
    arms["V-L2"]["basis_note"] = "LITE_CURRENT_PLUS_ONE_PROJECTED_BASE_EVALUATION"
    ve_config = variant_policy.load_ve_config(CONFIG_PATH)
    ve_ratio = ratios["LITE"] * int(ve_config["scenario_count"])
    base_nominal_evaluations = Fraction(units * HORIZON)
    total_ve_evaluations = full_evaluations * ve_ratio + base_nominal_evaluations
    total_ve_ratio = total_ve_evaluations / full_evaluations
    ve_estimate = {
        "enabled": enable_ve,
        "projected_scenario_evaluations_exact": fraction_payload(full_evaluations * ve_ratio),
        "projected_base_nominal_evaluations_exact": fraction_payload(base_nominal_evaluations),
        "projected_total_physics_evaluations_exact": fraction_payload(total_ve_evaluations),
        "worker_hours": full_hours * float(total_ve_ratio),
        "relative_to_v1_full": fraction_payload(total_ve_ratio),
        "basis_note": (
            "K_RESET_COMMON_RANDOM_SCENARIOS_PER_DISTINCT_LITE_CANDIDATE_PLUS_"
            "ONE_BASE_NOMINAL_EVALUATION_PER_DECISION_FOR_ORIGIN_MEMBERSHIP"
        ),
    }
    if enable_ve:
        arms[VE_ARM] = ve_estimate
    return {"schema": f"{SCHEMA}-estimate", "units": units,
            "episodes": units * len(active_arms(enable_ve=enable_ve)),
            "horizon": HORIZON, "arms": arms, "optional_arms": {VE_ARM: ve_estimate},
            "source_v1_estimate": source["basis"]}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-manifest", type=Path, default=DEFAULT_PREFLIGHT)
    parser.add_argument("--launch-authority", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--horizon", type=int, default=HORIZON)
    parser.add_argument("--unit", metavar="WORLD:LINEAGE")
    parser.add_argument("--merge", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--estimate", action="store_true")
    parser.add_argument("--estimate-units", type=int, default=12)
    parser.add_argument(
        "--enable-ve", action="store_true",
        help="explicitly add the disabled-by-default V-E tenth arm",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    args = _parser().parse_args(raw)
    try:
        pin_single_thread_runtime()
        if args.estimate:
            print(json.dumps(estimate(units=args.estimate_units, enable_ve=args.enable_ve), sort_keys=True, indent=2)); return 0
        if args.dry_run:
            contract_state = "SEALED" if CONTRACT_PATH.is_file() else "AWAITING_CONTROLLER_PLACEHOLDER"
            print(f"C3S_VARIANTS_DRY_RUN_PASS arms={','.join(active_arms(enable_ve=args.enable_ve))} units={len(ALL_UNITS)} contract={contract_state}")
            return 0
        if (args.unit is None) == (not args.merge) or args.launch_authority is None:
            raise VariantRunnerError("formal invocation needs exactly one of --unit/--merge and --launch-authority")
        _manifest, preflight_sha = validate_preflight(args.preflight_manifest)
        key = v1runner.UnitKey.parse(args.unit) if args.unit else None
        authority, authority_sha = validate_authority(
            args.launch_authority, preflight=args.preflight_manifest, preflight_sha=preflight_sha,
            output=args.output, launch_arguments=raw, target=key,
        )
        authority["__path__"] = str(Path(args.launch_authority).resolve())
        receipt = execute_unit(key=key, output=args.output, authority=authority,
                               authority_sha=authority_sha, preflight_sha=preflight_sha,
                               enable_ve=args.enable_ve) if key else execute_merge(
                                   output=args.output, authority=authority,
                                   authority_sha=authority_sha, preflight_sha=preflight_sha,
                                   enable_ve=args.enable_ve)
        print(f"C3S_VARIANTS_{'UNIT' if key else 'MERGE'}_PASS receipt={receipt}"); return 0
    except MergeWaiting as error:
        print(f"C3S_VARIANTS_MERGE_INCOMPLETE missing_units={error.missing}"); return 3
    except Exception as error:
        print(f"C3S_VARIANTS_REFUSED: {error}", file=sys.stderr); return 2


if __name__ == "__main__":
    raise SystemExit(main())
