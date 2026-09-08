#!/usr/bin/env python3
"""Run the TRAIN-only V0.24 Track-B parallel physics-lever matrix probe.

The CLI is one lever and one ``WORLD:CARRIER`` unit, or one lever merge.
``--estimate`` covers all levers and is simulator/authority inert.  Heavy
acquisition is reachable only after an immutable preflight and exact launch
authority.  L1/L12 never reinterpret the r2 scalar rows: their registered
hooks must replay the same exogenous anchors and keep keyed fading event
``physics``.  L2/L4 bind and read the r2 tapes without modifying them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import sys
from typing import Any, Callable, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent  # Provenance: installed Track-B probe package layout.
REPO = HERE.parents[2]  # Provenance: installed Track-B probe package layout.
E1_DIR = REPO / ".scratch/multi-catfish-v023-c3-existence-e1"  # Provenance: task-required exact E1 estimands import.
for _import_root in (HERE, E1_DIR):
    if str(_import_root) not in sys.path:
        sys.path.insert(0, str(_import_root))

import e1_estimands  # noqa: E402
import run_v024_regime_probe as finite_probe  # noqa: E402
from levers.common import RegenerationRequired, TODO_CONTROLLER_DECLARE  # noqa: E402
from levers.registry import LEVER_PRIORITY, LEVERS, apply_profile, get_lever  # noqa: E402


SCHEMA = "multi-catfish-mcrl-v024-trackb-lever-matrix-v1"  # Provenance: task Track-B iteration-2 deliverable identity.
CLAIM_CEILING = "TRAIN_OUTCOME_INFORMED_DEVELOPMENT_LEVER_MATRIX_NO_LEARNER_NO_EFFICACY_NO_TEST"  # Provenance: Astra multiplicity/exposure declaration.
PREFLIGHT_SCHEMA = f"{SCHEMA}-preflight"  # Provenance: inherited C3-S preflight pattern.
AUTHORITY_SCHEMA = f"{SCHEMA}-launch-authority"  # Provenance: inherited C3-S exact-invocation authority pattern.
UNIT_RECEIPT_SCHEMA = f"{SCHEMA}-unit-receipt"  # Provenance: inherited immutable unit-receipt pattern.
TERMINAL_RECEIPT_SCHEMA = f"{SCHEMA}-terminal-receipt"  # Provenance: inherited immutable merge-receipt pattern.

WORLDS = finite_probe.WORLDS  # Provenance: Astra common panel uses the B-r2 four-world panel.
CARRIERS = finite_probe.CARRIERS  # Provenance: Astra common panel uses three fixed B reference carriers.
STEPS = finite_probe.STEPS  # Provenance: Astra common panel freezes ten anchors per world/carrier.
USERS = finite_probe.USERS  # Provenance: Astra common panel freezes 100 users.
INTERVAL_S = finite_probe.INTERVAL_S  # Provenance: Astra common H preserves native 47(0.64) seconds.
SERVICE_MARGIN = 0.001  # Provenance: Astra common qualification Q.
MAP_J_GAIN = 0.05  # Provenance: Astra common qualification Q.
MAP_J_MINUS_U = 0.01  # Provenance: Astra common qualification Q.
MAP_INTERACTION = 0.005  # Provenance: Astra common qualification Q.
MAP_POSITIVE_WORLDS = 3  # Provenance: Astra common qualification Q.
RATE_TARGET_GUARD = 0.95  # Provenance: Astra L1/L12 arms and gates.
MAX_WORKERS = 2  # Provenance: Astra ordering b overlap budget.
TOP_PROPOSALS = 2  # Provenance: Astra set-decoder catalog declaration.
OPS3_HORIZON = 3  # Provenance: Astra common targets preserve OPS-3 H<=3.

ALL_NEUTRAL_CONTROL = "ALL_NEUTRAL_CONTROL"  # Provenance: task convention; this label is never rewritten as BASELINE.
ARMS = (
    ALL_NEUTRAL_CONTROL,
    "REFERENCE",
    "O1",
    "O2",
    "O12",
    "O123",
    "SET_PRIVILEGED",
    "SET_NOMINAL",
    "DROP_C1_O23",
    "DROP_C2_O13",
    "DROP_C3_O12",
)  # Provenance: Astra common arms A, including O2 diagnostic and both set decoders.
MARGINALS = {
    "C1": ("O123", "DROP_C1_O23"),
    "C2": ("O123", "DROP_C2_O13"),
    "C3": ("O123", "DROP_C3_O12"),
}  # Provenance: Astra common marginal definitions Q.
MECHANISM_FIELDS = {
    "L1": ("occupancy", "allocated_bandwidth_hz", "target_sinr", "requested_power_w", "allocated_power_w", "cap_hits", "interference_w", "attainment", "solver_residual_w"),
    "L12": ("occupancy", "allocated_bandwidth_hz", "target_sinr", "requested_power_w", "allocated_power_w", "cap_hits", "interference_w", "attainment", "solver_residual_w", "pa_floor_beams", "pa_knee_beams", "matched_l12_minus_l1_energy_j"),
    "L2": ("rf_power_invariant", "unchanged_max_occupancy_moves", "dc_repricing_j", "activation_changes", "lambda_bits_per_j", "kappa_bits"),
    "L4": ("physical_transitions", "distinct_setups", "failed_attempts", "initial_state_authenticated", "event_energy_j", "event_energy_share", "shared_setup_interaction_j", "additive_user_event_j"),
}  # Provenance: Astra per-lever failure-analysis obligation.
COMPOSITION_FIELDS = ("intended_surplus", "realized_surplus", "changed_users", "action_disagreement", "service_losses", "set_vs_additive_conversion")  # Provenance: Astra common failure-analysis obligation.
ENERGY_COMPONENT_FIELDS = ("pa_j", "fixed_circuit_j", "event_j", "other_j")  # Provenance: Astra mandatory PA-versus-rest failure decomposition.
INTERACTION_DECOMPOSITION_FIELDS = ("bits", "pa_energy_j", "fixed_circuit_energy_j", "event_energy_j", "other_energy_j")  # Provenance: Astra mandatory interaction energy decomposition.
PRIORITY_SELECTION_RULE = "FIRST_QUALIFYING_L1_THEN_L12_THEN_L2_THEN_L4_AFTER_COMPLETE_MATRIX"  # Provenance: Astra multiplicity declaration.

R2_INPUT = Path("/home/sat/mcrl-v024-regime-probe-20260908-r2/raw-units")  # Provenance: task-specified authenticated r2 tape source.
DEFAULT_OUTPUT = REPO / "artifacts/v024-regime-b/iteration-2-lever-matrix"  # Provenance: Track-B artifact isolation convention.
DEFAULT_PREFLIGHT = HERE / "V024-LEVER-MATRIX-PREFLIGHT.json"  # Provenance: C3-S preflight naming pattern.
DESIGN_MEMO = REPO / ".scratch/multi-catfish-v024-regime-b-design/V024-REGIME-B-DESIGN-CODEX-GPT6-ASTRA-ULTRA-2026-09-08.md"  # Provenance: task binding list.
PROTOCOL = REPO / ".scratch/multi-catfish-v024-regime-b-design/TRACK-B-PROTOCOL-2026-09-08.md"  # Provenance: task binding list.
ROUND2_ADJUDICATION = REPO / ".scratch/multi-catfish-v024-regime-b-design/ADJUDICATION-OUTSIDE-ROUND2-TRACK-B-CODEX-GPT6-ASTRA-2026-09-08.md"  # Provenance: task binding list.
ASTRA_MULTI = REPO / ".tmp-prompts-trackb/astra-trackb-multi-final.md"  # Provenance: task Step 0 matrix authority.
ASTRA_NEXT = REPO / ".tmp-prompts-trackb/astra-trackb-next-final.md"  # Provenance: task Step 0 priority authority.
DECLARATION = REPO / ".scratch/multi-catfish-v024-regime-b/ITERATION-2-LEVER-MATRIX-DECLARATION-DRAFT-2026-09-08.md"  # Provenance: task deliverable 4.


class MatrixProbeError(RuntimeError):
    """A declaration, input, execution, or immutable binding failed closed."""


class MatrixProbeWaiting(MatrixProbeError):
    """A merge is waiting for declared unit receipts or acquisition."""


class UnitKey:
    def __init__(self, world: int, carrier: str) -> None:
        self.world = int(world)
        self.carrier = str(carrier)
        if self.world not in WORLDS or self.carrier not in CARRIERS:
            raise MatrixProbeError("unit is outside the B-r2 4-world x 3-carrier panel")

    @classmethod
    def parse(cls, value: str) -> "UnitKey":
        try:
            world, carrier = value.split(":", 1)
            return cls(int(world), carrier)
        except (TypeError, ValueError) as error:
            raise MatrixProbeError("--unit must be WORLD:CARRIER") from error

    @property
    def slug(self) -> str:
        return f"world-{self.world}-{self.carrier}"

    def as_dict(self) -> Mapping[str, object]:
        return finite_probe.UnitKey(self.world, self.carrier).as_dict()


ALL_UNITS = tuple(UnitKey(world, carrier) for world in WORLDS for carrier in CARRIERS)  # Provenance: Astra common full panel cross-product.

# Server-side acquisition is installed explicitly by the launcher.  Keeping
# these as injection seams prevents local tests or imports from opening a
# simulator, and avoids sys.modules aliasing.
REGENERATION_ADAPTER: Callable[..., object] | None = None
SUPPLEMENT_ACQUISITION_ADAPTER: Callable[..., object] | None = None


def canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as error:
        raise MatrixProbeError("value is not finite canonical ASCII JSON") from error


def file_sha256(path: Path) -> str:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise MatrixProbeError(f"required regular file is absent or symlinked: {target}")
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for block in iter(lambda: handle.read(1_048_576), b""):
            digest.update(block)
    return digest.hexdigest()


def file_binding(path: Path) -> Mapping[str, object]:
    target = Path(path)
    return {"path": str(target.resolve()), "sha256": file_sha256(target), "bytes": target.stat().st_size}


def sealed_document_binding(path: Path) -> Mapping[str, object]:
    target = Path(path)
    binding = dict(file_binding(target))
    sidecar = Path(f"{target}.sha256")
    if sidecar.is_symlink() or not sidecar.is_file() or sidecar.read_text(encoding="ascii").split() != [binding["sha256"], target.name]:
        raise MatrixProbeError(f"sealed design document sidecar disagrees: {target}")
    binding["seal_sidecar"] = file_binding(sidecar)
    return binding


def _load_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise MatrixProbeError(f"{label} is not readable ASCII JSON") from error
    if not isinstance(payload, dict):
        raise MatrixProbeError(f"{label} must be a JSON object")
    return payload


def r2_path(key: UnitKey) -> Path:
    return R2_INPUT / key.slug / "physical-tape.json"


def r2_bindings() -> list[Mapping[str, object]]:
    paths = [r2_path(key) for key in ALL_UNITS]
    if any(not path.is_file() for path in paths):
        raise MatrixProbeError("authenticated r2 inventory is not the declared 12 tapes")
    return [file_binding(path) for path in paths]


def constants_table() -> Mapping[str, object]:
    return {
        "common": [
            {"name": "service_margin", "value": SERVICE_MARGIN.hex(), "provenance": "Astra common qualification Q"},
            {"name": "map_j_gain", "value": MAP_J_GAIN.hex(), "provenance": "Astra common qualification Q"},
            {"name": "map_j_minus_u", "value": MAP_J_MINUS_U.hex(), "provenance": "Astra common qualification Q"},
            {"name": "map_interaction", "value": MAP_INTERACTION.hex(), "provenance": "Astra common qualification Q"},
            {"name": "positive_worlds", "value": MAP_POSITIVE_WORLDS, "provenance": "Astra common qualification Q"},
            {"name": "ops3_horizon", "value": OPS3_HORIZON, "provenance": "Astra common targets"},
            {"name": "top_proposals", "value": TOP_PROPOSALS, "provenance": "Astra common set decoder"},
            {"name": "interval_s", "value": INTERVAL_S.hex(), "provenance": "Astra common H; native 47(0.64) storage"},
        ],
        "levers": {lever_id: list(LEVERS[lever_id].constants) for lever_id in LEVER_PRIORITY},
    }


def panel_bindings() -> Mapping[str, object]:
    return {
        "worlds": list(WORLDS),
        "carriers": list(CARRIERS),
        "carrier_definitions": finite_probe.panel_bindings()["carrier_definitions"],
        "steps_per_unit": STEPS,
        "users": USERS,
        "units": len(ALL_UNITS),
        "anchors": len(ALL_UNITS) * STEPS,
        "split": "TRAIN",
        "continuation": "ORIGINAL_PHYSICS_REFERENCE_ONLY",
        "counterfactuals": "DETACHED_OVERRIDE",
        "keyed_fading_event": "physics",
        "priority": list(LEVER_PRIORITY),
        "selection_rule": PRIORITY_SELECTION_RULE,
        "arms": list(ARMS),
        "marginals": {name: list(pair) for name, pair in MARGINALS.items()},
        "all_neutral_control_label": ALL_NEUTRAL_CONTROL,
    }


def authority_documents() -> Mapping[str, object]:
    return {
        "sealed_design_memo": sealed_document_binding(DESIGN_MEMO),
        "sealed_protocol": sealed_document_binding(PROTOCOL),
        "round2_adjudication": file_binding(ROUND2_ADJUDICATION),
        "astra_parallel_matrix": file_binding(ASTRA_MULTI),
        "astra_single_lever_priority": file_binding(ASTRA_NEXT),
        "declaration_draft": file_binding(DECLARATION),
    }


def expected_code_bindings() -> list[Mapping[str, object]]:
    paths = [
        HERE / "run_v024_lever_matrix_probe.py",
        HERE / "build_lever_matrix_preflight.py",
        HERE / "build_lever_matrix_launch_authority.py",
        HERE / "test_lever_matrix_probe.py",
        HERE / "rate_target_sum_power.py",
        HERE / "levers/common.py",
        HERE / "levers/registry.py",
        HERE / "levers/lever_l1_sum_power.py",
        HERE / "levers/lever_l12.py",
        HERE / "levers/lever_l2_pa_curve.py",
        HERE / "levers/lever_l4_handover_energy.py",
        HERE / "run_v024_regime_probe.py",
        E1_DIR / "e1_estimands.py",
        REPO / "src/mcrl/env/link_budget.py",
        REPO / "src/mcrl/env/keyed_fading.py",
    ]
    return [file_binding(path) for path in paths]


def estimate() -> Mapping[str, object]:
    inventory = r2_bindings()
    digest_by_slug = {path["path"].split("/")[-2]: path["sha256"] for path in inventory}
    return {
        "schema": f"{SCHEMA}-estimate",
        "panel": {"worlds": len(WORLDS), "carriers": len(CARRIERS), "units_per_lever": len(ALL_UNITS), "anchors_per_lever": len(ALL_UNITS) * STEPS},
        "priority": list(LEVER_PRIORITY),
        "maximum_parallel_single_thread_workers": MAX_WORKERS,
        "r2_tape_digests": digest_by_slug,
        "levers": {
            lever_id: {
                "identity": definition.identity,
                "unit_status": definition.estimate_status(),
                "r2_raw_tapes_reused": not definition.regeneration_required,
                "r2_tape_policy": definition.r2_tape_policy,
                "regeneration_hook": definition.module_name + ".regeneration_hook",
                "controller_todos": list(definition.controller_todos),
                "execution_ready": definition.execution_ready and not definition.regeneration_required,
                "supplementary_acquisition_required": True,
            }
            for lever_id, definition in LEVERS.items()
        },
    }


def build_preflight_payload(*, exposure_timestamp_utc: str, reviewer: str) -> Mapping[str, object]:
    if not exposure_timestamp_utc.endswith("Z") or not reviewer.strip():
        raise MatrixProbeError("controller must provide a UTC Z timestamp and reviewer")
    return {
        "schema": PREFLIGHT_SCHEMA,
        "status": "FROZEN_PREFLIGHT",
        "claim_ceiling": CLAIM_CEILING,
        "exposure_timestamp_utc": exposure_timestamp_utc,
        "reviewer": reviewer,
        "authority_documents": authority_documents(),
        "constants_table": constants_table(),
        "constants_table_sha256": hashlib.sha256(canonical_bytes(constants_table())).hexdigest(),
        "panel": panel_bindings(),
        "r2_read_only_tapes": r2_bindings(),
        "lever_todos": {lever_id: list(get_lever(lever_id).controller_todos) for lever_id in LEVER_PRIORITY},
        "code_files": expected_code_bindings(),
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }


def _sidecar(path: Path) -> Path:
    return Path(str(path) + ".sha256")


def _validate_sidecar(path: Path) -> str:
    target = Path(path)
    digest = file_sha256(target)
    sidecar = _sidecar(target)
    if sidecar.is_symlink() or not sidecar.is_file() or sidecar.read_text(encoding="ascii").split() != [digest, target.name]:
        raise MatrixProbeError(f"immutable digest sidecar disagrees: {target}")
    if stat.S_IMODE(target.stat().st_mode) != 0o444 or stat.S_IMODE(sidecar.stat().st_mode) != 0o444:
        raise MatrixProbeError(f"immutable authority is not mode 0444: {target}")
    return digest


def write_once_with_sidecar(path: Path, payload: Mapping[str, object]) -> tuple[Path, Path, str]:
    target = Path(path)
    sidecar = _sidecar(target)
    if target.exists() or target.is_symlink() or sidecar.exists() or sidecar.is_symlink():
        raise MatrixProbeError(f"refusing to overwrite immutable artifact: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = canonical_bytes(payload) + b"\n"
    with target.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    digest = hashlib.sha256(encoded).hexdigest()
    with sidecar.open("xb") as handle:
        handle.write(f"{digest}  {target.name}\n".encode("ascii"))
        handle.flush()
        os.fsync(handle.fileno())
    target.chmod(0o444)
    sidecar.chmod(0o444)
    _validate_sidecar(target)
    return target, sidecar, digest


def validate_preflight(path: Path) -> tuple[dict[str, Any], str]:
    payload = _load_json(path, label="lever-matrix preflight")
    digest = _validate_sidecar(path)
    if payload.get("schema") != PREFLIGHT_SCHEMA or payload.get("status") != "FROZEN_PREFLIGHT":
        raise MatrixProbeError("preflight schema/status drifted")
    expected = build_preflight_payload(
        exposure_timestamp_utc=str(payload.get("exposure_timestamp_utc", "")),
        reviewer=str(payload.get("reviewer", "")),
    )
    if payload != expected:
        raise MatrixProbeError("preflight differs from current code/documents/constants/tapes")
    return payload, digest


def require_lever_startable(lever_id: str) -> None:
    missing = get_lever(lever_id).controller_todos
    if missing:
        raise MatrixProbeError(f"{TODO_CONTROLLER_DECLARE} blocks {lever_id}: " + ", ".join(missing))


def launch_authority_payload(
    *, preflight: Path, output: Path, lever_id: str, mode: str,
    unit: str | None, launch_arguments: Sequence[str], exposure_timestamp_utc: str,
) -> Mapping[str, object]:
    require_lever_startable(lever_id)
    _manifest, digest = validate_preflight(preflight)
    if mode not in {"unit", "merge"} or (mode == "unit") != (unit is not None):
        raise MatrixProbeError("authority must bind exactly one unit or merge")
    definition = get_lever(lever_id)
    return {
        "schema": AUTHORITY_SCHEMA,
        "status": "FROZEN_LAUNCH_AUTHORITY",
        "claim_ceiling": CLAIM_CEILING,
        "preflight": {"path": str(Path(preflight).resolve()), "sha256": digest},
        "lever": lever_id,
        "lever_identity": definition.identity,
        "mode": mode,
        "unit": unit,
        "output_root": str(Path(output).resolve()),
        "checkout_root": str(REPO.resolve()),
        "launch_arguments": list(launch_arguments),
        "exposure_timestamp_utc": exposure_timestamp_utc,
        "constants": list(definition.constants),
        "r2_tape_policy": definition.r2_tape_policy,
        "maximum_workers": MAX_WORKERS,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }


def validate_launch_authority(
    path: Path, *, preflight: Path, output: Path, lever_id: str, mode: str,
    unit: str | None, launch_arguments: Sequence[str],
) -> Mapping[str, object]:
    payload = _load_json(path, label="lever launch authority")
    _validate_sidecar(path)
    expected = launch_authority_payload(
        preflight=preflight,
        output=output,
        lever_id=lever_id,
        mode=mode,
        unit=unit,
        launch_arguments=launch_arguments,
        exposure_timestamp_utc=str(payload.get("exposure_timestamp_utc", "")),
    )
    if payload != expected:
        raise MatrixProbeError("launch authority differs from the exact lever invocation")
    return payload


def transform_r2_tape(
    raw: Mapping[str, object], *, lever_id: str,
    context_for_profile: Callable[[Mapping[str, object], str, Mapping[str, object]], Mapping[str, object]] | None = None,
) -> Mapping[str, object]:
    """Deterministically apply an accounting-only lever to every r2 profile."""

    definition = get_lever(lever_id)
    if definition.regeneration_required:
        raise RegenerationRequired(f"{lever_id} cannot transform r2 physical rows")
    result = json.loads(json.dumps(raw))
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            raise MatrixProbeError("r2 step is malformed")
        rows: list[tuple[str, dict[str, object]]] = [("reference", step)]
        rows.extend(("unilateral", row) for row in step.get("unilateral_profiles", []))
        rows.extend(("joint", row) for row in step.get("joint_profiles", []))
        for kind, row in rows:
            field = "reference_profile" if kind == "reference" else "profile"
            profile = row.get(field)
            if not isinstance(profile, Mapping):
                raise MatrixProbeError("r2 profile is malformed")
            context = {} if context_for_profile is None else dict(context_for_profile(step, kind, row))
            row[field] = dict(apply_profile(lever_id, profile, **context))
    result["lever_transform"] = {
        "lever": lever_id,
        "identity": definition.identity,
        "source_tape_sha256": hashlib.sha256(canonical_bytes(raw) + b"\n").hexdigest(),
        "rf_rate_rows_reused": True,
    }
    return result


def masked_argmax(surface: object, masks: object) -> np.ndarray:
    """Simultaneous unweighted masked argmax with lowest-index ties/NOOP."""

    values = np.asarray(surface, dtype=np.float64)
    legal = np.asarray(masks)
    if values.ndim != 2 or legal.dtype != np.bool_ or legal.shape != values.shape or not np.all(np.isfinite(values)):
        raise MatrixProbeError("surface and masks must be aligned finite/Boolean matrices")
    actions = np.full(values.shape[0], -1, dtype=np.int64)
    eligible = np.any(legal, axis=1)
    actions[eligible] = np.argmax(np.where(legal[eligible], values[eligible], -np.inf), axis=1)
    return actions


def _profile_values(profile: Mapping[str, object]) -> tuple[np.ndarray, float, int]:
    try:
        bits = np.asarray([float.fromhex(str(value)) for value in profile["bits"]], dtype=np.float64)
        energy = float.fromhex(str(profile["energy_j"]))
        served = np.asarray(profile["served"], dtype=np.bool_)
    except (KeyError, TypeError, ValueError) as error:
        raise MatrixProbeError("target profile is malformed") from error
    if bits.ndim != 1 or served.shape != bits.shape or not np.all(np.isfinite(bits)) or np.any(bits < 0.0) or not math.isfinite(energy) or energy <= 0.0:
        raise MatrixProbeError("target profile violates bits/energy/service domains")
    return bits, energy, int(np.count_nonzero(served))


def target_surfaces(
    *, reference_actions: object, masks: object, reference_profile: Mapping[str, object],
    unilateral_profiles: Sequence[Mapping[str, object]], c2_surface: object,
    lcsrs_pairs: Sequence[Mapping[str, object]], lambda_bits_per_j: float,
    kappa_bits: float,
) -> Mapping[str, np.ndarray]:
    """Build exact C1, imported-normalized C2, and LC-SRS C3 surfaces."""

    if not math.isfinite(lambda_bits_per_j) or lambda_bits_per_j <= 0.0 or not math.isfinite(kappa_bits) or kappa_bits <= 0.0:
        raise MatrixProbeError("lambda/kappa must be positive finite pre-score constants")
    legal = np.asarray(masks, dtype=np.bool_)
    reference = np.asarray(reference_actions, dtype=np.int64)
    base_bits, base_energy, _base_served = _profile_values(reference_profile)
    if legal.ndim != 2 or reference.shape != (legal.shape[0],):
        raise MatrixProbeError("reference actions/masks disagree")
    c1 = np.zeros(legal.shape, dtype=np.float64)
    for row in unilateral_profiles:
        user = int(row["focal_user"])
        action = int(row["candidate_action"])
        bits, energy, _served = _profile_values(row["profile"])
        c1[user, action] = (float(bits[user] - base_bits[user]) - lambda_bits_per_j * (energy - base_energy)) / kappa_bits
    # C2 arrives already normalized under the inherited OPS-3 rule; there is
    # deliberately no second kappa division here.
    c2 = np.asarray(c2_surface, dtype=np.float64)
    if c2.shape != legal.shape or not np.all(np.isfinite(c2)):
        raise MatrixProbeError("OPS-3 C2 surface is malformed")
    c3 = np.zeros(legal.shape, dtype=np.float64)
    for pair in lcsrs_pairs:
        members = tuple(int(value) for value in pair["member_users"])
        actions = tuple(int(value) for value in pair["proposed_actions"])
        profiles = pair["profiles"]
        if len(members) != 2 or len(actions) != 2 or not isinstance(profiles, Sequence) or len(profiles) != 4:
            raise MatrixProbeError("LC-SRS pair needs two members/actions and 00/10/01/11 profiles")
        values = [_profile_values(profile) for profile in profiles]
        b0, e0, _ = values[0]
        unilateral_values = [
            math.fsum((values[index][0] - b0).tolist()) - lambda_bits_per_j * (values[index][1] - e0)
            for index in (1, 2)
        ]
        joint_value = math.fsum((values[3][0] - b0).tolist()) - lambda_bits_per_j * (values[3][1] - e0)
        psi = joint_value - math.fsum(unilateral_values)
        for offset, (user, action) in enumerate(zip(members, actions, strict=True), start=1):
            unilateral_bits = values[offset][0] - b0
            nonfocal = math.fsum(float(value) for index, value in enumerate(unilateral_bits) if index != user)
            c3[user, action] = (nonfocal + psi / 2.0) / kappa_bits
    rows = np.arange(reference.size)
    for surface in (c1, c2, c3):
        surface[~legal] = 0.0
        surface[rows, reference] = 0.0
    return {"C1": c1, "C2": c2, "C3": c3}


def compose_arms(surfaces: Mapping[str, object], masks: object) -> Mapping[str, np.ndarray]:
    """Compose exact named heads and literal DROP arms only."""

    c1, c2, c3 = (np.asarray(surfaces[name], dtype=np.float64) for name in ("C1", "C2", "C3"))
    return {
        "O1": masked_argmax(c1, masks),
        "O2": masked_argmax(c2, masks),
        "O12": masked_argmax(c1 + c2, masks),
        "O123": masked_argmax(c1 + c2 + c3, masks),
        "DROP_C1_O23": masked_argmax(c2 + c3, masks),
        "DROP_C2_O13": masked_argmax(c1 + c3, masks),
        "DROP_C3_O12": masked_argmax(c1 + c2, masks),
    }


def set_decode(
    catalog: Sequence[Mapping[str, object]], *, lambda_bits_per_j: float,
    kappa_bits: float, privileged: bool,
) -> Mapping[str, object]:
    """Apply identical catalogs/guards/ties for privileged S* and nominal S0."""

    if not catalog or str(catalog[0].get("configuration_kind")) != "reference":
        raise MatrixProbeError("set catalog must retain reference first")
    service_field = "served" if privileged else "nominal_served"
    reference_service = int(catalog[0][service_field])
    opportunities = int(catalog[0]["opportunities"])
    minimum_service = math.ceil(reference_service - SERVICE_MARGIN * opportunities)
    attainment_field = "attainment_fraction" if privileged else "nominal_attainment_fraction"
    reference_attainment = catalog[0].get(attainment_field)
    scored: list[tuple[float, str, Mapping[str, object]]] = []
    for row in catalog:
        if int(row["opportunities"]) != opportunities or int(row[service_field]) < minimum_service:
            continue
        attainment_value = row.get(attainment_field)
        if reference_attainment is not None and (
            attainment_value is None
            or float(attainment_value) < RATE_TARGET_GUARD
            or float(attainment_value) < float(reference_attainment) - SERVICE_MARGIN
        ):
            continue
        if row.get("configuration_kind") not in {"reference", "top2_unilateral", "complete_evacuation"}:
            raise MatrixProbeError("set catalog contains an undeclared configuration kind")
        if row.get("configuration_kind") != "reference" and row.get("proposal_membership_verified") is not True:
            raise MatrixProbeError("set catalog violates proposal membership")
        if privileged:
            bits, energy, _served = _profile_values(row["profile"])
            score = math.fsum(bits.tolist()) - lambda_bits_per_j * energy + kappa_bits * float(row.get("q2_delta", 0.0))
        else:
            score = float(row["nominal_score"])
            if not math.isfinite(score) or row.get("nominal_uses_realized_profile") is not False:
                raise MatrixProbeError("nominal set decoder must use a finite causal score without realized profiles")
        scored.append((score, str(row["configuration_id"]), row))
    if not scored:
        raise MatrixProbeError("set service guard removed the mandatory reference")
    return min(scored, key=lambda item: (-item[0], item[1]))[2]


def _validate_failure_energy_decomposition(
    arm_rows: Sequence[Mapping[str, object]], mechanism_rows: Sequence[Mapping[str, object]],
) -> None:
    """Refuse incomplete/non-finite PA-versus-rest failure-analysis inputs."""

    for index, row in enumerate(arm_rows):
        components = row.get("energy_components")
        if not isinstance(components, Mapping) or any(name not in components for name in ENERGY_COMPONENT_FIELDS):
            raise MatrixProbeError(f"arm row {index} lacks the mandatory PA-versus-rest energy decomposition")
        values = [float(components[name]) for name in ENERGY_COMPONENT_FIELDS]
        if not all(math.isfinite(value) and value >= 0.0 for value in values):
            raise MatrixProbeError(f"arm row {index} has a non-finite or negative energy component")
        energy_j = float(row["energy_j"])
        if not math.isfinite(energy_j) or not math.isclose(math.fsum(values), energy_j, rel_tol=1e-12, abs_tol=1e-9):
            raise MatrixProbeError(f"arm row {index} energy components do not sum to energy_j")
    for index, row in enumerate(mechanism_rows):
        decomposition = row.get("interaction_decomposition")
        if not isinstance(decomposition, Mapping) or any(name not in decomposition for name in INTERACTION_DECOMPOSITION_FIELDS):
            raise MatrixProbeError(f"mechanism row {index} lacks the mandatory interaction decomposition")
        if not all(math.isfinite(float(decomposition[name])) for name in INTERACTION_DECOMPOSITION_FIELDS):
            raise MatrixProbeError(f"mechanism row {index} has a non-finite interaction decomposition")


def _row_metrics(rows: Sequence[Mapping[str, object]]) -> Mapping[str, object]:
    bits = math.fsum(float(row["bits"]) for row in rows)
    energy = math.fsum(float(row["energy_j"]) for row in rows)
    served = sum(int(row["served"]) for row in rows)
    opportunities = sum(int(row["opportunities"]) for row in rows)
    if energy <= 0.0 or opportunities <= 0:
        raise MatrixProbeError("arm totals require positive energy/opportunities")
    components = {
        name: math.fsum(float(row["energy_components"][name]) for row in rows)  # type: ignore[index]
        for name in ENERGY_COMPONENT_FIELDS
    }
    result: dict[str, object] = {
        "bits": bits,
        "energy_j": energy,
        "pooled_ee_bits_per_j": bits / energy,
        "served": served,
        "opportunities": opportunities,
        "service_fraction": served / opportunities,
        "energy_decomposition_j": components,
    }
    applicable = [row for row in rows if row.get("attainment_applicable") is True]
    if applicable:
        attained = sum(int(row["target_attained"]) for row in applicable)
        count = sum(int(row["opportunities"]) for row in applicable)
        result["attainment_fraction"] = attained / count
    else:
        result["attainment_fraction"] = None
    return result


def _summarize_group(rows: Sequence[Mapping[str, object]]) -> Mapping[str, object]:
    arms: dict[str, Mapping[str, object]] = {}
    for arm in ARMS:
        selected = [row for row in rows if row.get("arm") == arm]
        if not selected:
            raise MatrixProbeError(f"completed group lacks arm {arm}")
        arms[arm] = dict(_row_metrics(selected))
    reference = arms["REFERENCE"]
    for metrics in arms.values():
        metrics["percent_vs_reference"] = 100.0 * (float(metrics["pooled_ee_bits_per_j"]) / float(reference["pooled_ee_bits_per_j"]) - 1.0)
        metrics["service_guard_pass"] = float(metrics["service_fraction"]) >= float(reference["service_fraction"]) - SERVICE_MARGIN
        attainment = metrics["attainment_fraction"]
        ref_attainment = reference["attainment_fraction"]
        metrics["attainment_guard_pass"] = True if attainment is None else float(attainment) >= RATE_TARGET_GUARD and float(attainment) >= float(ref_attainment) - SERVICE_MARGIN
    marginals: dict[str, Mapping[str, object]] = {}
    for name, (full_name, drop_name) in MARGINALS.items():
        full = arms[full_name]
        drop = arms[drop_name]
        delta_bits = float(full["bits"]) - float(drop["bits"])
        delta_energy = float(full["energy_j"]) - float(drop["energy_j"])
        eta_drop = float(drop["pooled_ee_bits_per_j"])
        delta_ee = float(full["pooled_ee_bits_per_j"]) - eta_drop
        marginals[name] = {
            "full_arm": full_name,
            "drop_arm": drop_name,
            "ee_delta_bits_per_j": delta_ee,
            "drop_relative_percent": 100.0 * delta_ee / eta_drop,
            "distance_from_zero_bits_per_j": delta_ee,
            "delta_bits": delta_bits,
            "delta_energy_j": delta_energy,
            "surplus_at_drop_ee_bits": delta_bits - eta_drop * delta_energy,
            "bits_moved": delta_bits != 0.0,
            "energy_moved": delta_energy != 0.0,
            "strictly_positive": delta_ee > 0.0,
            "guards_pass": bool(full["service_guard_pass"] and full["attainment_guard_pass"] and drop["service_guard_pass"] and drop["attainment_guard_pass"]),
        }
    return {"arms": arms, "marginals": marginals}


def summarize_arm_rows(rows: Sequence[Mapping[str, object]]) -> Mapping[str, object]:
    global_summary = _summarize_group(rows)
    worlds = {str(world): _summarize_group([row for row in rows if int(row["world"]) == world]) for world in WORLDS}
    carriers = {carrier: _summarize_group([row for row in rows if str(row["carrier"]) == carrier]) for carrier in CARRIERS}
    marginals = global_summary["marginals"]
    assert isinstance(marginals, Mapping)
    return {
        "global": global_summary,
        "worlds": worlds,
        "carrier_strata_diagnostic_only": carriers,
        "all_three_positive_and_guarded": all(bool(row["strictly_positive"] and row["guards_pass"]) for row in marginals.values()),
    }


def map_qualification(
    *, eta_ref: float, u1: float, j1: float, interaction_fraction: float,
    world_contrasts: Mapping[str, float], service_guards_pass: bool,
    additional_guards_pass: bool,
) -> Mapping[str, object]:
    statistics = {
        "j_gain_fraction": j1 / eta_ref - 1.0,
        "j_minus_u_over_reference": (j1 - u1) / eta_ref,
        "interaction_over_reference_bits": interaction_fraction,
        "positive_world_count": sum(float(value) > 0.0 for value in world_contrasts.values()),
    }
    distances = {
        "j_gain_minus_5pct": statistics["j_gain_fraction"] - MAP_J_GAIN,
        "j_minus_u_minus_1pct": statistics["j_minus_u_over_reference"] - MAP_J_MINUS_U,
        "interaction_minus_0_5pct": interaction_fraction - MAP_INTERACTION,
        "positive_worlds_minus_3": statistics["positive_world_count"] - MAP_POSITIVE_WORLDS,
    }
    tests = {
        "j_gain_at_least_5pct": distances["j_gain_minus_5pct"] >= 0.0,
        "j_minus_u_at_least_1pct_reference": distances["j_minus_u_minus_1pct"] >= 0.0,
        "interaction_at_least_0_5pct_reference_bits": distances["interaction_minus_0_5pct"] >= 0.0,
        "global_witness_j_minus_u_positive_in_3_worlds": distances["positive_worlds_minus_3"] >= 0,
        "service_guards": bool(service_guards_pass),
        "additional_demand_or_target_guards": bool(additional_guards_pass),
    }
    return {"statistics": statistics, "signed_distance_from_threshold": distances, "tests": tests, "qualifies": all(tests.values())}


def build_failure_analysis(
    *, lever_id: str, arm_rows: Sequence[Mapping[str, object]], regime_map: Mapping[str, object],
    mechanism_rows: Sequence[Mapping[str, object]], composition_rows: Sequence[Mapping[str, object]],
) -> Mapping[str, object]:
    """Build Astra's mandatory global/world/mechanism failure-analysis block."""

    summary = summarize_arm_rows(arm_rows)
    global_marginals = summary["global"]["marginals"]
    interaction_components = {
        name: math.fsum(float(row["interaction_decomposition"][name]) for row in mechanism_rows)  # type: ignore[index]
        for name in INTERACTION_DECOMPOSITION_FIELDS
    }
    mechanism_keys = MECHANISM_FIELDS[lever_id]
    missing_mechanism_fields = sorted({name for name in mechanism_keys if any(name not in row for row in mechanism_rows)}) if mechanism_rows else list(mechanism_keys)
    return {
        "lever": lever_id,
        "global_arm_and_marginal_table": summary["global"],
        "four_world_tables": summary["worlds"],
        "carrier_strata_diagnostic_only": summary["carrier_strata_diagnostic_only"],
        "failed_marginals": {name: row for name, row in global_marginals.items() if not bool(row["strictly_positive"] and row["guards_pass"])},
        "map_statistics_and_signed_threshold_distance": regime_map.get("qualification"),
        "energy_decomposition_pa_vs_rest": interaction_components,
        "mechanism_ledger": list(mechanism_rows),
        "missing_mechanism_fields": missing_mechanism_fields,
        "composition_diagnostics": list(composition_rows),
        "diagnostic_taxonomy": ["MISSING_PHYSICAL_HEADROOM", "C2_MISALIGNMENT", "C3_TARGET_FAILURE", "COMPOSITION_CANCELLATION", "GUARD_FAILURE"],
    }


def _unit_path(output: Path, lever_id: str, key: UnitKey) -> Path:
    return Path(output) / "levers" / lever_id / "units" / key.slug / "receipt.json"


def validate_acquired_unit(payload: object, *, lever_id: str, key: UnitKey, r2_binding: Mapping[str, object]) -> Mapping[str, object]:
    if not isinstance(payload, Mapping):
        raise MatrixProbeError("acquisition hook returned no unit mapping")
    required = {"arm_rows", "map_anchors", "mechanism_rows", "composition_rows", "reference_bits", "reference_energy_j", "reference_served", "all_neutral_control_byte_identical"}
    if not required.issubset(payload):
        raise MatrixProbeError("acquired unit lacks complete arms/map/failure-analysis inputs")
    if payload.get("lever") != lever_id or payload.get("unit") != key.as_dict():
        raise MatrixProbeError("acquired unit identity drifted")
    if payload.get("r2_tape_sha256") != r2_binding["sha256"]:
        raise MatrixProbeError("acquired unit does not bind the authenticated r2 anchor tape")
    arm_rows = payload["arm_rows"]
    map_anchors = payload["map_anchors"]
    mechanism_rows = payload["mechanism_rows"]
    composition_rows = payload["composition_rows"]
    if not all(isinstance(value, list) for value in (arm_rows, map_anchors, mechanism_rows, composition_rows)):
        raise MatrixProbeError("acquired unit collections must be lists")
    if len(map_anchors) != STEPS or len(mechanism_rows) < STEPS or len(composition_rows) < STEPS:
        raise MatrixProbeError("acquired unit does not cover all ten anchors/failure ledgers")
    missing_mechanism = sorted({field for field in MECHANISM_FIELDS[lever_id] if any(not isinstance(row, Mapping) or field not in row for row in mechanism_rows)})
    missing_composition = sorted({field for field in COMPOSITION_FIELDS if any(not isinstance(row, Mapping) or field not in row for row in composition_rows)})
    if missing_mechanism or missing_composition:
        raise MatrixProbeError(
            "acquired unit cannot support a complete failure analysis: "
            f"mechanism={missing_mechanism}, composition={missing_composition}"
        )
    _validate_failure_energy_decomposition(arm_rows, mechanism_rows)
    for arm in ARMS:
        selected = [row for row in arm_rows if isinstance(row, Mapping) and row.get("arm") == arm]
        if len(selected) != STEPS:
            raise MatrixProbeError(f"acquired unit does not have ten rows for arm {arm}")
        if any(int(row.get("world", -1)) != key.world or str(row.get("carrier", "")) != key.carrier for row in selected):
            raise MatrixProbeError("arm row unit identity drifted")
    anchor_ids = set()
    for anchor in map_anchors:
        if not isinstance(anchor, Mapping) or int(anchor.get("world", -1)) != key.world or str(anchor.get("carrier", "")) != key.carrier:
            raise MatrixProbeError("map anchor unit identity drifted")
        anchor_ids.add(str(anchor.get("anchor_id", "")))
    if "" in anchor_ids or len(anchor_ids) != STEPS:
        raise MatrixProbeError("map anchor IDs are absent or repeated")
    if float(payload["reference_bits"]) < 0.0 or float(payload["reference_energy_j"]) <= 0.0 or int(payload["reference_served"]) <= 0:
        raise MatrixProbeError("unit reference totals are outside their domain")
    definition = get_lever(lever_id)
    target_guard_expected = lever_id in {"L1", "L12"}
    if any(bool(row.get("attainment_applicable", False)) is not target_guard_expected for row in arm_rows):
        raise MatrixProbeError("arm target-attainment applicability disagrees with the lever")
    if any(bool(anchor["base"].get("additional_guard_applicable", False)) is not target_guard_expected for anchor in map_anchors):
        raise MatrixProbeError("map target-attainment applicability disagrees with the lever")
    if payload.get("all_neutral_control_byte_identical") is not True:
        raise MatrixProbeError("unit lacks byte-identical ALL_NEUTRAL_CONTROL proof")
    if definition.regeneration_required:
        if payload.get("physics_regenerated") is not True or payload.get("keyed_fading_event") != "physics" or payload.get("continuation") != "ORIGINAL_PHYSICS_REFERENCE_ONLY":
            raise MatrixProbeError("regenerated unit lacks matched-field/reference-continuation proof")
    elif payload.get("r2_rf_rate_rows_reused") is not True:
        raise MatrixProbeError("repricing unit lacks explicit r2 RF/rate reuse proof")
    return payload


def acquire_unit(*, lever_id: str, key: UnitKey, preflight_sha256: str) -> Mapping[str, object]:
    require_lever_startable(lever_id)
    definition = get_lever(lever_id)
    source = file_binding(r2_path(key))
    context = {"key": key, "r2_tape": source, "preflight_sha256": preflight_sha256}
    if definition.regeneration_required:
        payload = definition.regeneration_hook(REGENERATION_ADAPTER, **context)
    else:
        if SUPPLEMENT_ACQUISITION_ADAPTER is None:
            raise MatrixProbeWaiting(f"{lever_id} needs authenticated OPS-3/LC-SRS/composed/event supplements; r2 tape remains read-only")
        raw = _load_json(r2_path(key), label="r2 raw tape")
        payload = SUPPLEMENT_ACQUISITION_ADAPTER(
            lever_id=lever_id,
            identity=definition.identity,
            key=key,
            raw_tape=raw,
            raw_tape_binding=source,
            apply_profile=lambda profile, **kwargs: apply_profile(lever_id, profile, **kwargs),
            preflight_sha256=preflight_sha256,
        )
    return validate_acquired_unit(payload, lever_id=lever_id, key=key, r2_binding=source)


def execute_unit(
    *, lever_id: str, key: UnitKey, output: Path, preflight_sha256: str,
    launch_authority_sha256: str,
) -> Path:
    target = _unit_path(output, lever_id, key)
    try:
        tape = acquire_unit(lever_id=lever_id, key=key, preflight_sha256=preflight_sha256)
        status = "COMPLETE"
        failure = None
    except KeyboardInterrupt as error:
        tape = None
        status = "INCOMPLETE"
        failure = {"error_type": type(error).__name__, "error_text": str(error)}
    except RegenerationRequired as error:
        tape = None
        status = "REGEN_REQUIRED"
        failure = {"error_type": type(error).__name__, "error_text": str(error)}
    except MatrixProbeWaiting as error:
        tape = None
        status = "INCOMPLETE"
        failure = {"error_type": type(error).__name__, "error_text": str(error)}
    except Exception as error:
        tape = None
        status = "INVALID_RUN"
        failure = {"error_type": type(error).__name__, "error_text": str(error)}
    receipt = {
        "schema": UNIT_RECEIPT_SCHEMA,
        "status": status,
        "claim_ceiling": CLAIM_CEILING,
        "lever": lever_id,
        "lever_identity": get_lever(lever_id).identity,
        "unit": key.as_dict(),
        "preflight_sha256": preflight_sha256,
        "launch_authority_sha256": launch_authority_sha256,
        "r2_tape": file_binding(r2_path(key)),
        "tape": tape,
        "failure": failure,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }
    return write_once_with_sidecar(target, receipt)[0]


def _merge_regime_map(unit_tapes: Sequence[Mapping[str, object]]) -> Mapping[str, object]:
    anchors = [anchor for tape in unit_tapes for anchor in tape["map_anchors"]]
    unilateral = [{"anchor_id": row["anchor_id"], "base": row["base"], "unilateral_profiles": row["unilateral_profiles"]} for row in anchors]
    joint = [{"anchor_id": row["anchor_id"], "base": row["base"], "joint_profiles": row["joint_profiles"]} for row in anchors]
    u1 = e1_estimands.solve_u1(unilateral)
    j1 = e1_estimands.solve_j1(joint)
    if u1["eta_BASE_hex"] != j1["eta_BASE_hex"]:
        raise MatrixProbeError("U1/J1 reference pooled EE differs")
    # Reconstruct both exact global witnesses without any worldwise re-solve.
    # The exact solvers independently verify their own serialized certificates.
    by_id = {str(row["anchor_id"]): row for row in anchors}
    if len(by_id) != len(anchors):
        raise MatrixProbeError("map anchor IDs are not unique")
    world_totals = {world: {"U": [0.0, 0.0], "J": [0.0, 0.0]} for world in WORLDS}
    interaction = 0.0
    reference_bits = 0.0
    service = {"reference": 0, "U": 0, "J": 0, "opportunities": 0}
    attainment = {"reference": 0, "U": 0, "J": 0, "opportunities": 0, "applicable": False}
    eta_ref = float(j1["eta_BASE"])
    for anchor_id, raw in by_id.items():
        world = int(raw["world"])
        if world not in WORLDS:
            raise MatrixProbeError("map anchor world is outside the fixed panel")
        base = raw["base"]
        unilateral_rows = {str(row["profile_id"]): row for row in raw["unilateral_profiles"]}
        joint_rows = {str(row["profile_id"]): row for row in raw["joint_profiles"]}
        uid = str(u1["chosen_profiles"][anchor_id])
        jid = str(j1["chosen_profiles"][anchor_id])
        urow = base if uid == "BASE" else unilateral_rows[uid]
        jrow = base if jid == "BASE" else joint_rows[jid]
        for label, row in (("U", urow), ("J", jrow)):
            world_totals[world][label][0] += float(row["total_bits"])
            world_totals[world][label][1] += float(row["total_energy_j"])
            service[label] += int(row["served"])
        reference_bits += float(base["total_bits"])
        service["reference"] += int(base["served"])
        service["opportunities"] += int(base["opportunities"])
        applicable = bool(base.get("additional_guard_applicable", False))
        if applicable:
            attainment["applicable"] = True
            attainment["opportunities"] += int(base["opportunities"])
            attainment["reference"] += int(base["target_attained"])
            attainment["U"] += int(urow["target_attained"])
            attainment["J"] += int(jrow["target_attained"])
        if jid == "BASE":
            continue
        joint_value = float(jrow["total_bits"]) - float(base["total_bits"]) - eta_ref * (float(jrow["total_energy_j"]) - float(base["total_energy_j"]))
        member_ids = jrow.get("member_unilateral_profile_ids")
        if not isinstance(member_ids, list):
            raise MatrixProbeError("selected J profile lacks member unilateral identities")
        unilateral_value = math.fsum(
            float(unilateral_rows[str(profile_id)]["total_bits"]) - float(base["total_bits"])
            - eta_ref * (float(unilateral_rows[str(profile_id)]["total_energy_j"]) - float(base["total_energy_j"]))
            for profile_id in member_ids
        )
        interaction += joint_value - unilateral_value
    world_contrasts = {
        str(world): totals["J"][0] / totals["J"][1] - totals["U"][0] / totals["U"][1]
        for world, totals in world_totals.items()
    }
    opportunities = service["opportunities"]
    reference_service_fraction = service["reference"] / opportunities
    service_guards = all(service[label] / opportunities >= reference_service_fraction - SERVICE_MARGIN for label in ("U", "J"))
    if attainment["applicable"]:
        guard_opportunities = attainment["opportunities"]
        reference_attainment = attainment["reference"] / guard_opportunities
        additional_guards = all(
            attainment[label] / guard_opportunities >= RATE_TARGET_GUARD
            and attainment[label] / guard_opportunities >= reference_attainment - SERVICE_MARGIN
            for label in ("U", "J")
        )
    else:
        reference_attainment = None
        additional_guards = True
    qualification = map_qualification(
        eta_ref=eta_ref,
        u1=float(u1["U1"]),
        j1=float(j1["J1"]),
        interaction_fraction=interaction / reference_bits,
        world_contrasts=world_contrasts,
        service_guards_pass=service_guards,
        additional_guards_pass=additional_guards,
    )
    return {
        "U1": u1,
        "J1": j1,
        "interaction_surplus_bits": interaction,
        "interaction_fraction": interaction / reference_bits,
        "world_j_minus_u_ee_using_global_witnesses": world_contrasts,
        "global_witness_service": {**service, "reference_fraction": reference_service_fraction, "guards_pass": service_guards},
        "global_witness_additional_guard": {**attainment, "reference_fraction": reference_attainment, "guards_pass": additional_guards},
        "qualification": qualification,
    }


def execute_merge(
    *, lever_id: str, output: Path, preflight_sha256: str,
    launch_authority_sha256: str,
) -> Path:
    receipts = []
    missing = []
    for key in ALL_UNITS:
        path = _unit_path(output, lever_id, key)
        if not path.is_file():
            missing.append(key.slug)
            continue
        _validate_sidecar(path)
        receipt = _load_json(path, label="unit receipt")
        if receipt.get("lever") != lever_id or receipt.get("unit") != key.as_dict():
            raise MatrixProbeError("unit receipt binding drifted")
        if receipt.get("preflight_sha256") != preflight_sha256:
            raise MatrixProbeError("unit receipt was produced under a different preflight")
        authority_digest = receipt.get("launch_authority_sha256")
        if not isinstance(authority_digest, str) or len(authority_digest) != 64:
            raise MatrixProbeError("unit receipt lacks its exact launch-authority digest")
        receipts.append(receipt)
    if missing:
        raise MatrixProbeWaiting("waiting for units: " + ", ".join(missing))
    failures = [row for row in receipts if row.get("status") != "COMPLETE"]
    terminal: dict[str, object] = {
        "schema": TERMINAL_RECEIPT_SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "lever": lever_id,
        "lever_identity": get_lever(lever_id).identity,
        "preflight_sha256": preflight_sha256,
        "launch_authority_sha256": launch_authority_sha256,
        "unit_receipts": [{"unit": row["unit"], "status": row["status"]} for row in receipts],
    }
    if failures:
        terminal.update({"status": "INCOMPLETE" if any(row["status"] in {"INCOMPLETE", "REGEN_REQUIRED"} for row in failures) else "INVALID_RUN", "failures": failures})
    else:
        tapes = [row["tape"] for row in receipts]
        arm_rows = [row for tape in tapes for row in tape["arm_rows"]]
        regime_map = _merge_regime_map(tapes)
        failure_analysis = build_failure_analysis(
            lever_id=lever_id,
            arm_rows=arm_rows,
            regime_map=regime_map,
            mechanism_rows=[row for tape in tapes for row in tape["mechanism_rows"]],
            composition_rows=[row for tape in tapes for row in tape["composition_rows"]],
        )
        arms = summarize_arm_rows(arm_rows)
        outcome = "SUPPORT" if regime_map["qualification"]["qualifies"] and arms["all_three_positive_and_guarded"] else "NO_SUPPORT"
        terminal.update({
            "status": "COMPLETE",
            "outcome": outcome,
            "lambda_bits_per_j": math.fsum(float(tape["reference_bits"]) for tape in tapes) / math.fsum(float(tape["reference_energy_j"]) for tape in tapes),
            "kappa_bits": math.fsum(float(tape["reference_bits"]) for tape in tapes) / sum(int(tape["reference_served"]) for tape in tapes),
            "arms": arms,
            "regime_map": regime_map,
            "failure_analysis": failure_analysis,
        })
    terminal.update({"test_split_opened": False, "episode_training": False, "learner_update": False, "efficacy_claim": False})
    path = Path(output) / "levers" / lever_id / "terminal-receipt.json"
    target = write_once_with_sidecar(path, terminal)[0]
    maybe_write_matrix_adjudication(output=output, preflight_sha256=preflight_sha256)
    return target


def adjudicate_matrix(terminals: Mapping[str, Mapping[str, object]]) -> Mapping[str, object]:
    """Apply the predeclared priority only after all four terminals exist."""

    if set(terminals) != set(LEVER_PRIORITY):
        missing = [lever_id for lever_id in LEVER_PRIORITY if lever_id not in terminals]
        return {"status": "WAITING_FOR_ALL_LEVERS", "selected_lever": None, "missing": missing}
    incomplete = [lever_id for lever_id in LEVER_PRIORITY if terminals[lever_id].get("status") != "COMPLETE"]
    if incomplete:
        return {"status": "INCOMPLETE", "selected_lever": None, "unresolved_levers": incomplete}
    selected = next((lever_id for lever_id in LEVER_PRIORITY if terminals[lever_id].get("outcome") == "SUPPORT"), None)
    return {
        "status": "COMPLETE",
        "selected_lever": selected,
        "selection": "NONE" if selected is None else selected,
        "priority": list(LEVER_PRIORITY),
        "selection_rule": PRIORITY_SELECTION_RULE,
        "all_outcomes": {lever_id: terminals[lever_id].get("outcome") for lever_id in LEVER_PRIORITY},
    }


def maybe_write_matrix_adjudication(*, output: Path, preflight_sha256: str) -> Path | None:
    """The last per-lever merge publishes one immutable matrix decision."""

    matrix_path = Path(output) / "matrix-terminal-receipt.json"
    if matrix_path.exists():
        _validate_sidecar(matrix_path)
        existing = _load_json(matrix_path, label="matrix terminal receipt")
        if existing.get("preflight_sha256") != preflight_sha256:
            raise MatrixProbeError("matrix terminal preflight binding drifted")
        return matrix_path
    terminals: dict[str, Mapping[str, object]] = {}
    bindings: dict[str, Mapping[str, object]] = {}
    for lever_id in LEVER_PRIORITY:
        path = Path(output) / "levers" / lever_id / "terminal-receipt.json"
        if not path.is_file():
            return None
        _validate_sidecar(path)
        payload = _load_json(path, label=f"{lever_id} terminal receipt")
        if payload.get("lever") != lever_id or payload.get("preflight_sha256") != preflight_sha256:
            raise MatrixProbeError("per-lever terminal cannot enter matrix adjudication")
        terminals[lever_id] = payload
        bindings[lever_id] = file_binding(path)
    decision = adjudicate_matrix(terminals)
    payload = {
        "schema": f"{SCHEMA}-matrix-terminal-receipt",
        "claim_ceiling": CLAIM_CEILING,
        "preflight_sha256": preflight_sha256,
        "lever_terminal_bindings": bindings,
        "adjudication": decision,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }
    return write_once_with_sidecar(matrix_path, payload)[0]


def pin_single_thread_runtime() -> None:
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        if os.environ.get(name) != "1":
            raise MatrixProbeError(f"{name}=1 is required")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lever", choices=LEVER_PRIORITY)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--unit")
    mode.add_argument("--merge", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--estimate", action="store_true")
    parser.add_argument("--preflight", type=Path, default=DEFAULT_PREFLIGHT)
    parser.add_argument("--launch-authority", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def run(args: argparse.Namespace, *, argv: Sequence[str]) -> Mapping[str, object]:
    if args.estimate:
        if args.lever is not None or args.unit is not None or args.merge or args.dry_run:
            raise MatrixProbeError("--estimate covers all levers and accepts no lever/mode")
        return {"mode": "estimate", "estimate": estimate()}
    if args.lever is None or (args.unit is None and not args.merge):
        raise MatrixProbeError("choose --lever ID and exactly one of --unit WORLD:CARRIER or --merge")
    require_lever_startable(args.lever)
    _preflight, preflight_sha = validate_preflight(args.preflight)
    mode = "unit" if args.unit is not None else "merge"
    key = None if args.unit is None else UnitKey.parse(args.unit)
    if args.launch_authority is not None:
        validate_launch_authority(
            args.launch_authority,
            preflight=args.preflight,
            output=args.output,
            lever_id=args.lever,
            mode=mode,
            unit=args.unit,
            launch_arguments=argv,
        )
        launch_authority_sha = file_sha256(args.launch_authority)
    elif not args.dry_run:
        raise MatrixProbeError("execution requires a controller-sealed --launch-authority")
    else:
        launch_authority_sha = ""
    if args.dry_run:
        return {"mode": "dry-run", "lever": args.lever, "preflight_sha256": preflight_sha}
    if key is not None:
        return {"mode": "unit", "receipt": str(execute_unit(lever_id=args.lever, key=key, output=args.output, preflight_sha256=preflight_sha, launch_authority_sha256=launch_authority_sha))}
    return {"mode": "merge", "receipt": str(execute_merge(lever_id=args.lever, output=args.output, preflight_sha256=preflight_sha, launch_authority_sha256=launch_authority_sha))}


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        args = _parser().parse_args(arguments)
        if not args.estimate:
            pin_single_thread_runtime()
        result = run(args, argv=arguments)
    except MatrixProbeWaiting as error:
        print(f"V024_LEVER_MATRIX_WAITING: {error}", file=sys.stderr)
        return 3
    except Exception as error:
        print(f"V024_LEVER_MATRIX_ERROR: {error}", file=sys.stderr)
        return 2
    if result["mode"] == "estimate":
        print(json.dumps(result["estimate"], indent=2, sort_keys=True))
    elif result["mode"] == "dry-run":
        print(f"V024_LEVER_MATRIX_DRY_RUN_PASS lever={result['lever']} preflight={result['preflight_sha256']}")
    else:
        print(f"V024_LEVER_MATRIX_{str(result['mode']).upper()} receipt={result['receipt']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
