#!/usr/bin/env python3
"""Independent post-outcome verifier for the V0.22 mechanics probe.

This module consumes the persisted JSON receipt produced by
``run_v022_coalition_residual_probe.py``.  It deliberately does not import the
runner or the coalition formula and does not create an environment, open a TLE
archive, evaluate physics, train a learner, or open TEST.  All topology,
formula, sparse-surface, composition, and decision checks are recomputed from
the persisted receipt and the external preflight bindings.

The verifier is intentionally stricter than the runner's self-reported
``mechanics`` object: those booleans are treated as claims to cross-check, not
as inputs to the decision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MANIFEST = HERE / "PREFLIGHT-MANIFEST.json"
MANIFEST_DIGEST = HERE / "PREFLIGHT-MANIFEST.sha256"
RUNNER = HERE / "run_v022_coalition_residual_probe.py"
CONTRACT = HERE / "COALITION-RESIDUAL-MECHANICS-PROBE-CONTRACT-2026-09-05.md"
FORMULA = REPO / "src" / "mcrl" / "runtime" / "ee_axis_coalition_residual_c3.py"
PREREG = REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json"

SCHEMA = "multi-catfish-mcrl-v022-c3-coalition-residual-mechanics-probe-v1"
VERIFICATION_SCHEMA = (
    "multi-catfish-mcrl-v022-c3-coalition-residual-verification-v1"
)
PREFLIGHT_SCHEMA = "multi-catfish-mcrl-v022-c3-coalition-residual-preflight-v1"
WORLDS = (2026121701, 2026121702, 2026121703, 2026121704)
LINEAGE = 2026092101
USERS = 100
ACTIONS = 28
STEPS = 10
FIELD_COMPONENT = "MCRL_V022_C3_COALITION_RESIDUAL_V1"
LAMBDA_HEX = "0x1.c3c0a7b6b86d3p+26"
KAPPA_HEX = "0x1.2cea89d260f2ap+33"
LAMBDA = float.fromhex(LAMBDA_HEX)
KAPPA = float.fromhex(KAPPA_HEX)
CLAIM_CEILING = (
    "TRAIN_TOPOLOGY_SELECTED_CURRENT_SLOT_MECHANICS_NO_LEARNER_NO_EPISODE_TRAINING_NO_TEST"
)

REQUIRED_ROLES = {
    "runner",
    "preflight",
    "contract",
    "formula",
    "preregistration",
    "fit_merged",
    "selected_q1_q2_checkpoint",
    "v020_runner",
    "v018_runner",
    "v015_runner",
    "v013_runner",
    "screen_runner",
    "screen_gate",
    "screen_source",
    "runtime_training_pipeline",
    "runtime_tle",
}
EXPECTED_PATHS = {
    "runner": ".scratch/multi-catfish-v022-c3-coalition-residual/run_v022_coalition_residual_probe.py",
    "preflight": ".scratch/multi-catfish-v022-c3-coalition-residual/preflight_v022_coalition_residual.py",
    "contract": ".scratch/multi-catfish-v022-c3-coalition-residual/COALITION-RESIDUAL-MECHANICS-PROBE-CONTRACT-2026-09-05.md",
    "formula": "src/mcrl/runtime/ee_axis_coalition_residual_c3.py",
    "preregistration": "artifacts/PREREG-FROZEN-2026-08-25-R2.json",
    "fit_merged": ".scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/merged/result.json",
    "selected_q1_q2_checkpoint": ".scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/lineage-2026092101/checkpoints/lineage-2026092101-q2init-2026108101-rung-003000.pt",
    "v020_runner": ".scratch/multi-catfish-v020-c3-source-audit/run_v020_repriced_c3_gate.py",
    "v018_runner": ".scratch/multi-catfish-v018-relational-zr/run_v018_analytic_diagnostic.py",
    "v015_runner": ".scratch/multi-catfish-v015-c3-learned-context/run_v015_c3_learned_context_oracle.py",
    "v013_runner": ".scratch/zero-energy-c3-v013/run_v013_zero_energy_c3_oracle.py",
    "screen_runner": ".scratch/c3-v04/run_v04_c3_500_update_screen.py",
    "screen_gate": ".scratch/c3-v04/run_v04_c3_learnability_gate.py",
    "screen_source": ".scratch/c3-v04/run_v04_c3_source.py",
    "runtime_training_pipeline": "src/mcrl/runtime/training_pipeline.py",
    "runtime_tle": "src/mcrl/env/tle.py",
}


class VerificationError(RuntimeError):
    """A persisted receipt failed an independent verification check."""


def _sha256_file(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise VerificationError(f"expected regular file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _digest_string(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise VerificationError(f"{field} is not a lowercase SHA-256")
    return value


def _finite_float(value: object, *, field: str) -> float:
    if isinstance(value, bool):
        raise VerificationError(f"{field} is Boolean")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise VerificationError(f"{field} is not numeric") from error
    if not math.isfinite(result):
        raise VerificationError(f"{field} is not finite")
    return result


def _finite_array(
    value: object,
    *,
    field: str,
    shape: tuple[int, ...] | None = None,
    nonnegative: bool = False,
) -> np.ndarray:
    try:
        result = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as error:
        raise VerificationError(f"{field} is not a numeric array") from error
    if shape is not None and result.shape != shape:
        raise VerificationError(f"{field} has shape {result.shape}, expected {shape}")
    if not np.all(np.isfinite(result)):
        raise VerificationError(f"{field} contains a non-finite value")
    if nonnegative and np.any(result < 0.0):
        raise VerificationError(f"{field} contains a negative value")
    return np.asarray(result, dtype=np.float64)


def _int_array(
    value: object, *, field: str, shape: tuple[int, ...] | None = None
) -> np.ndarray:
    raw = np.asarray(value)
    if raw.dtype == np.bool_ or not np.issubdtype(raw.dtype, np.integer):
        raise VerificationError(f"{field} is not an integer array")
    if shape is not None and raw.shape != shape:
        raise VerificationError(f"{field} has shape {raw.shape}, expected {shape}")
    return np.asarray(raw, dtype=np.int64)


def _bool_array(
    value: object, *, field: str, shape: tuple[int, ...]
) -> np.ndarray:
    raw = np.asarray(value)
    if raw.dtype != np.bool_ or raw.shape != shape:
        raise VerificationError(f"{field} is not Boolean shape {shape}")
    return np.asarray(raw, dtype=np.bool_)


def _mapping(value: object, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise VerificationError(f"{field} is not an object")
    return value


def _relative_path(path: object, *, repo: Path, field: str) -> tuple[str, Path]:
    if not isinstance(path, str) or not path.strip():
        raise VerificationError(f"{field}.path is empty")
    relative = Path(path)
    if relative.is_absolute() or any(part == ".." for part in relative.parts):
        raise VerificationError(f"{field}.path must be repository-relative")
    resolved = (repo.resolve() / relative).resolve()
    if not resolved.is_relative_to(repo.resolve()):
        raise VerificationError(f"{field}.path escapes repository")
    return relative.as_posix(), resolved


def _close(left: float, right: float, *, scale: float = 1.0) -> bool:
    magnitude = max(1.0, abs(float(left)), abs(float(right)))
    tolerance = max(1.0e-12 * scale, 1024.0 * np.finfo(np.float64).eps * magnitude)
    return math.isfinite(float(left)) and math.isfinite(float(right)) and abs(left - right) <= tolerance


def _array_close(left: object, right: object, *, field: str) -> bool:
    lhs = np.asarray(left, dtype=np.float64)
    rhs = np.asarray(right, dtype=np.float64)
    if lhs.shape != rhs.shape:
        raise VerificationError(f"{field} shape differs")
    if not np.all(np.isfinite(lhs)) or not np.all(np.isfinite(rhs)):
        raise VerificationError(f"{field} contains non-finite values")
    if lhs.size == 0:
        return True
    scale = max(1.0, float(np.max(np.abs(lhs))), float(np.max(np.abs(rhs))))
    tolerance = max(1.0e-12, 1024.0 * np.finfo(np.float64).eps * scale)
    return bool(np.all(np.abs(lhs - rhs) <= tolerance))


def _safe_sum(value: object, *, field: str) -> float:
    try:
        result = math.fsum(float(item) for item in np.asarray(value).reshape(-1).tolist())
    except (TypeError, ValueError, OverflowError) as error:
        raise VerificationError(f"{field} cannot be summed") from error
    if not math.isfinite(result):
        raise VerificationError(f"{field} sum is not finite")
    return float(result)


def _record_error(errors: list[str], check: str, error: Exception) -> None:
    errors.append(f"{check}: {error}")


def _check(
    checks: dict[str, bool], errors: list[str], name: str, fn: Any
) -> Any | None:
    try:
        value = fn()
        checks[name] = True
        return value
    except Exception as error:  # pragma: no cover - exercised by tamper tests
        checks[name] = False
        _record_error(errors, name, error)
        return None


def _load_manifest(
    *, manifest_path: Path, digest_path: Path, repo: Path
) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, str]]]:
    raw = manifest_path.read_bytes()
    try:
        manifest = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VerificationError("preflight manifest is not ASCII JSON") from error
    manifest_obj = _mapping(manifest, field="preflight manifest")
    canonical = _canonical_bytes(manifest_obj)
    if raw not in (canonical, canonical + b"\n"):
        raise VerificationError("preflight manifest is not canonical JSON")
    manifest_sha = _sha256_file(manifest_path)
    digest_lines = digest_path.read_text(encoding="ascii").splitlines()
    if len(digest_lines) != 1:
        raise VerificationError("preflight digest file must contain one line")
    parts = digest_lines[0].split()
    if len(parts) != 2 or parts[1] != "PREFLIGHT-MANIFEST.json":
        raise VerificationError("preflight digest filename binding is malformed")
    if _digest_string(parts[0], field="preflight digest") != manifest_sha:
        raise VerificationError("preflight digest does not match manifest bytes")
    if manifest_obj.get("schema") != PREFLIGHT_SCHEMA:
        raise VerificationError("preflight manifest schema drifted")
    if manifest_obj.get("manifest_version") != 1:
        raise VerificationError("preflight manifest version drifted")

    configuration = _mapping(manifest_obj.get("configuration"), field="configuration")
    expected_configuration = {
        "split": "TRAIN_DEVELOPMENT",
        "lineage": LINEAGE,
        "worlds": list(WORLDS),
        "steps_per_episode": STEPS,
        "users": USERS,
        "action_count": ACTIONS,
        "field_component": FIELD_COMPONENT,
    }
    for key, expected in expected_configuration.items():
        if configuration.get(key) != expected:
            raise VerificationError(f"configuration.{key} drifted")
    tle = _mapping(configuration.get("tle"), field="configuration.tle")
    tle_digest = _digest_string(
        tle.get("file_set_sha256"), field="configuration.tle.file_set_sha256"
    )

    bindings_raw = manifest_obj.get("bindings")
    if not isinstance(bindings_raw, list) or not bindings_raw:
        raise VerificationError("preflight manifest has no bindings")
    bindings: list[dict[str, str]] = []
    by_role: dict[str, dict[str, str]] = {}
    seen_paths: set[str] = set()
    for index, raw_entry in enumerate(bindings_raw):
        entry = _mapping(raw_entry, field=f"bindings[{index}]")
        role = entry.get("role")
        if not isinstance(role, str) or not role:
            raise VerificationError(f"bindings[{index}].role is empty")
        relative, resolved = _relative_path(
            entry.get("path"), repo=repo, field=f"bindings[{index}]"
        )
        if relative in seen_paths:
            raise VerificationError(f"manifest repeats {relative}")
        seen_paths.add(relative)
        expected_sha = _digest_string(
            entry.get("sha256"), field=f"bindings[{index}].sha256"
        )
        actual_sha = _sha256_file(resolved)
        if actual_sha != expected_sha:
            raise VerificationError(f"binding drifted for {relative}")
        normalized = {"role": role, "path": relative, "sha256": actual_sha}
        bindings.append(normalized)
        if role in by_role:
            raise VerificationError(f"manifest repeats role {role}")
        by_role[role] = normalized

    missing = sorted(REQUIRED_ROLES - set(by_role))
    if missing:
        raise VerificationError("required roles missing: " + ", ".join(missing))
    for role, expected_path in EXPECTED_PATHS.items():
        if by_role[role]["path"] != expected_path:
            raise VerificationError(f"manifest path drifted for {role}")

    fit = _mapping(configuration.get("fit_merged"), field="configuration.fit_merged")
    checkpoint = _mapping(
        configuration.get("selected_checkpoint"),
        field="configuration.selected_checkpoint",
    )
    if fit.get("path") != by_role["fit_merged"]["path"] or fit.get("sha256") != by_role["fit_merged"]["sha256"]:
        raise VerificationError("configuration.fit_merged disagrees with binding")
    if checkpoint.get("path") != by_role["selected_q1_q2_checkpoint"]["path"] or checkpoint.get("sha256") != by_role["selected_q1_q2_checkpoint"]["sha256"]:
        raise VerificationError("configuration.selected_checkpoint disagrees with binding")

    receipt = {
        "schema": PREFLIGHT_SCHEMA,
        "status": "PASS",
        "manifest_path": str(manifest_path.resolve()),
        "manifest_file_sha256": manifest_sha,
        "manifest_digest_path": str(digest_path.resolve()),
        "manifest_binding_count": len(bindings),
        "bindings": bindings,
        "configuration": {
            **expected_configuration,
            "tle_file_set_sha256": tle_digest,
            "fit_merged": dict(fit),
            "selected_checkpoint": dict(checkpoint),
        },
    }
    return manifest_obj, receipt, by_role


def _validate_preflight_receipt(
    result_preflight: object, expected_receipt: Mapping[str, Any]
) -> None:
    supplied = _mapping(result_preflight, field="result.preflight")
    if dict(supplied) != dict(expected_receipt):
        raise VerificationError("result.preflight differs from independently rebuilt receipt")


def _topology_proposal_from_inputs(inputs: Mapping[str, Any]) -> dict[str, Any] | None:
    required = {
        "reference_actions",
        "legal_mask",
        "opening_feasible",
        "base_surface",
        "candidate_physical_keys",
        "base_surface_sha256",
    }
    if set(inputs) != required:
        raise VerificationError("topology_inputs contains missing or outcome-bearing fields")
    reference = _int_array(inputs["reference_actions"], field="reference_actions", shape=(USERS,))
    legal = _bool_array(inputs["legal_mask"], field="legal_mask", shape=(USERS, ACTIONS))
    opening = _bool_array(
        inputs["opening_feasible"], field="opening_feasible", shape=(USERS, ACTIONS)
    )
    base = _finite_array(
        inputs["base_surface"], field="base_surface", shape=(USERS, ACTIONS)
    )
    base_digest = hashlib.sha256(
        np.ascontiguousarray(base, dtype=np.float64).tobytes()
    ).hexdigest()
    if inputs.get("base_surface_sha256") != base_digest:
        raise VerificationError("base_surface_sha256 disagrees with persisted surface")
    raw_keys = inputs["candidate_physical_keys"]
    if not isinstance(raw_keys, list) or len(raw_keys) != USERS:
        raise VerificationError("candidate_physical_keys has wrong user count")
    keys: list[list[tuple[int, int]]] = []
    for user, row in enumerate(raw_keys):
        if not isinstance(row, list) or len(row) != ACTIONS:
            raise VerificationError(f"candidate_physical_keys row {user} has wrong width")
        parsed_row: list[tuple[int, int]] = []
        for action, pair in enumerate(row):
            if not isinstance(pair, list) or len(pair) != 2:
                raise VerificationError(f"candidate key ({user},{action}) malformed")
            if any(isinstance(value, bool) or not isinstance(value, int) for value in pair):
                raise VerificationError(f"candidate key ({user},{action}) is not integer")
            parsed_row.append((int(pair[0]), int(pair[1])))
        keys.append(parsed_row)

    reference_keys: list[tuple[int, int] | None] = [None] * USERS
    occupants: dict[tuple[int, int], list[int]] = {}
    for user, raw_action in enumerate(reference.tolist()):
        action = int(raw_action)
        if action < 0 or action >= ACTIONS:
            raise VerificationError("reference action is out of range")
        if not bool(legal[user, action]):
            raise VerificationError("reference action is illegal")
        if not bool(opening[user, action]):
            continue
        key = keys[user][action]
        reference_keys[user] = key
        occupants.setdefault(key, []).append(user)

    for source in sorted(key for key, members in occupants.items() if len(members) == 2):
        members = tuple(sorted(int(user) for user in occupants[source]))
        outside_keys = {
            key
            for key, users_on_key in occupants.items()
            if key != source and any(int(user) not in members for user in users_on_key)
        }
        if not outside_keys:
            continue
        proposed_actions: list[int] = []
        proposed_keys: list[tuple[int, int]] = []
        complete = True
        for user in members:
            choices: list[int] = []
            for action in np.flatnonzero(legal[user] & opening[user]).tolist():
                action = int(action)
                key = keys[user][action]
                if key != source and key in outside_keys:
                    choices.append(action)
            if not choices:
                complete = False
                break
            best = max(float(base[user, action]) for action in choices)
            selected = min(action for action in choices if float(base[user, action]) == best)
            proposed_actions.append(selected)
            proposed_keys.append(keys[user][selected])
        if complete:
            return {
                "source_key": [int(source[0]), int(source[1])],
                "coalition_user_ids": [int(user) for user in members],
                "proposed_actions": proposed_actions,
                "proposed_keys": [
                    [int(key[0]), int(key[1])] for key in proposed_keys
                ],
                "reference_occupancy": {
                    f"{key[0]}:{key[1]}": [int(user) for user in sorted(users_on_key)]
                    for key, users_on_key in sorted(occupants.items())
                },
            }
    return None


def _validate_scan(payload: Mapping[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    scan_raw = payload.get("scan")
    if not isinstance(scan_raw, list) or not scan_raw:
        raise VerificationError("scan is empty or malformed")
    selected_world = payload.get("selected_world")
    selected_step = payload.get("selected_step")
    rows: list[Mapping[str, Any]] = []
    qualified_rows: list[tuple[int, int, dict[str, Any]]] = []
    expected_index = 0
    for raw_row in scan_raw:
        row = _mapping(raw_row, field="scan row")
        world = row.get("world")
        step = row.get("step")
        if isinstance(world, bool) or not isinstance(world, int):
            raise VerificationError("scan world is not integer")
        if isinstance(step, bool) or not isinstance(step, int):
            raise VerificationError("scan step is not integer")
        if world not in WORLDS or step < 0 or step >= STEPS:
            raise VerificationError("scan world/step outside frozen panel")
        if expected_index >= len(WORLDS) * STEPS:
            raise VerificationError("scan has too many rows")
        expected_world = WORLDS[expected_index // STEPS]
        expected_step = expected_index % STEPS
        if (world, step) != (expected_world, expected_step):
            raise VerificationError("scan is not an ordered prefix of the frozen panel")
        expected_index += 1
        inputs = _mapping(row.get("topology_inputs"), field="scan.topology_inputs")
        # Section 2/3 excludes the initial anchor.  At step zero the runner
        # intentionally records an outcome-blind no-candidate row even when
        # the raw topology would otherwise contain a pair.
        proposal = None if step == 0 else _topology_proposal_from_inputs(inputs)
        qualified = row.get("qualified")
        if not isinstance(qualified, bool):
            raise VerificationError("scan.qualified is not Boolean")
        if qualified != (proposal is not None):
            raise VerificationError(f"scan qualification disagrees at {world}/{step}")
        reference = _int_array(
            inputs["reference_actions"], field="scan.reference_actions", shape=(USERS,)
        )
        expected_ref_hash = hashlib.sha256(
            np.ascontiguousarray(reference, dtype=np.int64).tobytes()
        ).hexdigest()
        if row.get("reference_sha256") != expected_ref_hash:
            raise VerificationError(f"reference hash disagrees at {world}/{step}")
        if qualified:
            supplied_proposal = _mapping(row.get("proposal"), field="scan.proposal")
            if dict(supplied_proposal) != proposal:
                raise VerificationError(f"topology proposal disagrees at {world}/{step}")
            qualified_rows.append((world, step, dict(proposal)))
        elif row.get("proposal") is not None:
            raise VerificationError(f"unqualified row has proposal at {world}/{step}")
        rows.append(row)

    if qualified_rows:
        world, step, proposal = qualified_rows[0]
        if (selected_world, selected_step) != (world, step):
            raise VerificationError("selected anchor is not the first qualified row")
        if len(rows) != expected_index or (world, step) != (rows[-1]["world"], rows[-1]["step"]):
            raise VerificationError("scan continues after selected first qualified anchor")
        selected = proposal
    else:
        if payload.get("decision") != "NO_QUALIFIED_PAIR_CASE":
            raise VerificationError("unqualified complete scan has a non-NO_CASE decision")
        if expected_index != len(WORLDS) * STEPS:
            raise VerificationError("NO_CASE scan is not complete")
        if selected_world is not None or selected_step is not None:
            raise VerificationError("NO_CASE contains selected anchor")
        selected = None
    return selected, {
        "rows": len(rows),
        "qualified_rows": len(qualified_rows),
        "first_qualified": (
            {"world": qualified_rows[0][0], "step": qualified_rows[0][1]}
            if qualified_rows
            else None
        ),
    }


def _profile_record(
    record: Mapping[str, Any], *, name: str, users: int
) -> dict[str, Any]:
    actions = _int_array(record.get("actions"), field=f"profiles.{name}.actions", shape=(users,))
    if np.any(actions < 0) or np.any(actions >= ACTIONS):
        raise VerificationError(f"profiles.{name}.actions out of range")
    bits = _finite_array(
        record.get("per_user_bits"), field=f"profiles.{name}.per_user_bits", shape=(users,), nonnegative=True
    )
    total = _finite_float(record.get("total_bits"), field=f"profiles.{name}.total_bits")
    energy = _finite_float(record.get("energy_j"), field=f"profiles.{name}.energy_j")
    ee = _finite_float(
        record.get("ratio_of_sums_ee_bits_per_j"),
        field=f"profiles.{name}.ratio_of_sums_ee_bits_per_j",
    )
    served_raw = record.get("served")
    served = np.asarray(served_raw)
    if served.dtype != np.bool_ or served.shape != (users,):
        raise VerificationError(f"profiles.{name}.served malformed")
    beam_raw = record.get("active_beam_keys")
    if not isinstance(beam_raw, list):
        raise VerificationError(f"profiles.{name}.active_beam_keys malformed")
    beams: list[tuple[int, int]] = []
    for pair in beam_raw:
        if not isinstance(pair, list) or len(pair) != 2:
            raise VerificationError(f"profiles.{name}.active_beam_keys pair malformed")
        if any(isinstance(value, bool) or not isinstance(value, int) for value in pair):
            raise VerificationError(f"profiles.{name}.active_beam_keys not integer")
        beams.append((int(pair[0]), int(pair[1])))
    if len(set(beams)) != len(beams):
        raise VerificationError(f"profiles.{name}.active_beam_keys contains duplicates")
    active_satellites_raw = record.get("active_satellites")
    if not isinstance(active_satellites_raw, list):
        raise VerificationError(f"profiles.{name}.active_satellites malformed")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in active_satellites_raw):
        raise VerificationError(f"profiles.{name}.active_satellites not integer")
    active_satellites = [int(value) for value in active_satellites_raw]
    if active_satellites != sorted(set(active_satellites)):
        raise VerificationError(f"profiles.{name}.active_satellites not sorted/unique")
    expected_satellites = sorted({beam[0] for beam in beams})
    if active_satellites != expected_satellites:
        raise VerificationError(f"profiles.{name}.active_satellites disagree with beams")
    power = _finite_array(
        record.get("beam_power_w"), field=f"profiles.{name}.beam_power_w", shape=(len(beams),)
    )
    action_hash = hashlib.sha256(
        np.ascontiguousarray(actions, dtype=np.int64).tobytes()
    ).hexdigest()
    if record.get("action_sha256") != action_hash:
        raise VerificationError(f"profiles.{name}.action_sha256 disagrees")
    expected_total = _safe_sum(bits, field=f"profiles.{name}.total_bits")
    if not _close(total, expected_total):
        raise VerificationError(f"profiles.{name}.total_bits disagrees")
    if energy <= 0.0:
        raise VerificationError(f"profiles.{name}.energy_j is not positive")
    expected_ee = expected_total / energy
    if not _close(ee, expected_ee):
        raise VerificationError(f"profiles.{name}.EE disagrees")
    expected_served = int(np.count_nonzero(served))
    if record.get("served_users") != expected_served:
        raise VerificationError(f"profiles.{name}.served_users disagrees")
    return {
        "actions": actions,
        "bits": bits,
        "total_bits": total,
        "energy_j": energy,
        "ee": ee,
        "served": served,
        "served_users": expected_served,
        "beams": set(beams),
        "beam_list": beams,
        "power": power,
    }


def _verify_profiles(
    payload: Mapping[str, Any], selected: Mapping[str, Any]
) -> tuple[dict[str, dict[str, Any]], dict[str, bool]]:
    profiles_raw = _mapping(payload.get("profiles"), field="profiles")
    if set(profiles_raw) != {"00", "10", "01", "11"}:
        raise VerificationError("profiles must contain exactly 00, 10, 01, 11")
    profiles = {
        name: _profile_record(profiles_raw[name], name=name, users=USERS)
        for name in ("00", "10", "01", "11")
    }
    inputs = _mapping(payload["topology_inputs"], field="topology_inputs")
    reference = _int_array(inputs["reference_actions"], field="reference_actions", shape=(USERS,))
    legal = _bool_array(inputs["legal_mask"], field="legal_mask", shape=(USERS, ACTIONS))
    members = _int_array(selected["coalition_user_ids"], field="coalition_user_ids", shape=(2,))
    proposed = _int_array(selected["proposed_actions"], field="proposed_actions", shape=(2,))
    if np.any(members < 0) or np.any(members >= USERS) or np.unique(members).size != 2:
        raise VerificationError("selected coalition members malformed")
    for name, actions in ((name, profile["actions"]) for name, profile in profiles.items()):
        if not np.all(legal[np.arange(USERS), actions]):
            raise VerificationError(f"profiles.{name} contains illegal action")
    expected_actions = {
        "00": reference,
        "10": np.array(reference, copy=True),
        "01": np.array(reference, copy=True),
        "11": np.array(reference, copy=True),
    }
    expected_actions["10"][members[0]] = proposed[0]
    expected_actions["01"][members[1]] = proposed[1]
    expected_actions["11"][members] = proposed
    for name in expected_actions:
        if not np.array_equal(profiles[name]["actions"], expected_actions[name]):
            raise VerificationError(f"profiles.{name}.actions do not match fixed profile")

    source = tuple(int(value) for value in selected["source_key"])
    beams = {name: profile["beams"] for name, profile in profiles.items()}
    public_good = {
        "source_beam_public_good_signature": bool(
            source in beams["00"]
            and source in beams["10"]
            and source in beams["01"]
            and source not in beams["11"]
        ),
        "joint_opens_no_new_beam": not bool(beams["11"] - beams["00"]),
        "joint_removes_exactly_source_beam": bool(
            beams["00"] - beams["11"] == {source}
            and len(beams["11"]) == len(beams["00"]) - 1
        ),
        "pair_served_all_profiles": all(
            bool(profiles[name]["served"][int(user)])
            for name in ("00", "10", "01", "11")
            for user in members.tolist()
        ),
        "joint_service_noninferior": profiles["11"]["served_users"] >= profiles["00"]["served_users"],
    }
    public_good["joint_ee_positive"] = profiles["11"]["ee"] > profiles["00"]["ee"]
    return profiles, public_good


def _formula_check(
    payload: Mapping[str, Any], profiles: Mapping[str, Mapping[str, Any]], selected: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    formula = _mapping(payload.get("formula"), field="formula")
    if formula.get("schema") != "multi-catfish-mcrl-v022-c3-coalition-residual-v1":
        raise VerificationError("formula schema drifted")
    lambda_value = _finite_float(payload.get("lambda_bits_per_j"), field="lambda")
    kappa_value = _finite_float(payload.get("kappa_bits"), field="kappa")
    if payload.get("lambda_bits_per_j_hex") != LAMBDA_HEX or not _close(lambda_value, LAMBDA):
        raise VerificationError("lambda disagrees with frozen contract")
    if payload.get("kappa_bits_hex") != KAPPA_HEX or not _close(kappa_value, KAPPA):
        raise VerificationError("kappa disagrees with frozen contract")
    members = _int_array(selected["coalition_user_ids"], field="members", shape=(2,))
    b0 = profiles["00"]["bits"]
    e0 = profiles["00"]["energy_j"]
    bu = np.stack([profiles["10"]["bits"], profiles["01"]["bits"]])
    eu = np.asarray([profiles["10"]["energy_j"], profiles["01"]["energy_j"]], dtype=np.float64)
    bc = profiles["11"]["bits"]
    ec = profiles["11"]["energy_j"]
    delta_u = bu - b0[None, :]
    delta_c = bc - b0
    delta_eu = eu - e0
    delta_ec = ec - e0
    own = np.asarray(
        [
            float(delta_u[index, int(user)] - lambda_value * delta_eu[index])
            for index, user in enumerate(members.tolist())
        ],
        dtype=np.float64,
    )
    nonfocal = np.asarray(
        [
            _safe_sum(np.delete(delta_u[index], int(user)), field="nonfocal_bits")
            for index, user in enumerate(members.tolist())
        ],
        dtype=np.float64,
    )
    d = own + nonfocal
    joint_delta_bits = _safe_sum(delta_c, field="joint_delta_bits")
    unilateral_totals = np.asarray(
        [_safe_sum(row, field="unilateral_delta_bits") for row in delta_u], dtype=np.float64
    )
    sum_unilateral_totals = _safe_sum(unilateral_totals, field="sum_unilateral_totals")
    sum_unilateral_energy = _safe_sum(delta_eu, field="sum_unilateral_energy")
    joint_surplus = joint_delta_bits - lambda_value * delta_ec
    interaction_bits = joint_delta_bits - sum_unilateral_totals
    interaction_energy = delta_ec - sum_unilateral_energy
    interaction_surplus = interaction_bits - lambda_value * interaction_energy
    equal_share = interaction_surplus / 2.0
    z3 = nonfocal + equal_share
    combined = own + z3
    identity_residual = _safe_sum(combined, field="identity") - joint_surplus
    expected = {
        "own_bits": own,
        "nonfocal_bits": nonfocal,
        "d_bits": d,
        "joint_delta_bits": joint_delta_bits,
        "joint_delta_energy_j": delta_ec,
        "joint_surplus_bits": joint_surplus,
        "interaction_bits": interaction_bits,
        "interaction_energy_j": interaction_energy,
        "interaction_surplus_bits": interaction_surplus,
        "equal_share_bits": equal_share,
        "z3_bits": z3,
        "combined_bits": combined,
        "identity_residual_bits": identity_residual,
    }
    for field, value in expected.items():
        supplied = formula.get(field)
        if isinstance(value, np.ndarray):
            if not _array_close(supplied, value, field=f"formula.{field}"):
                raise VerificationError(f"formula.{field} disagrees")
        elif not _close(_finite_float(supplied, field=f"formula.{field}"), float(value)):
            raise VerificationError(f"formula.{field} disagrees")
    scale = max(1.0, abs(joint_surplus), abs(_safe_sum(combined, field="identity")))
    identity_tolerance = max(1.0e-12, 1024.0 * np.finfo(np.float64).eps * scale)
    if abs(identity_residual) > identity_tolerance:
        raise VerificationError("formula identity residual is material")

    # Explicit two-player Shapley recomputation of the residual game.
    v_single = nonfocal
    v_full = joint_surplus - _safe_sum(own, field="own")
    shapley = np.asarray(
        [
            0.5 * (v_single[0] + v_full - v_single[1]),
            0.5 * (v_single[1] + v_full - v_single[0]),
        ],
        dtype=np.float64,
    )
    if not _array_close(shapley, z3, field="shapley"):
        raise VerificationError("z3 is not the independently recomputed Shapley value")
    if not _close(_safe_sum(own + shapley, field="shapley_identity"), joint_surplus):
        raise VerificationError("Shapley identity does not recover joint surplus")

    q3 = np.zeros((USERS, ACTIONS), dtype=np.float64)
    proposed = _int_array(selected["proposed_actions"], field="proposed", shape=(2,))
    legal = _bool_array(payload["topology_inputs"]["legal_mask"], field="legal", shape=(USERS, ACTIONS))
    reference = _int_array(payload["topology_inputs"]["reference_actions"], field="reference", shape=(USERS,))
    for index, (user, action) in enumerate(zip(members.tolist(), proposed.tolist(), strict=True)):
        if not legal[int(user), int(action)] or int(action) == int(reference[int(user)]):
            raise VerificationError("sparse Q3 support is illegal or references the incumbent")
        q3[int(user), int(action)] = z3[index] / kappa_value
    if not np.all(np.isfinite(q3)):
        raise VerificationError("sparse Q3 surface is non-finite")
    expected_q3_hash = hashlib.sha256(
        np.ascontiguousarray(q3, dtype=np.float64).tobytes()
    ).hexdigest()
    if formula.get("q3_sha256") != expected_q3_hash:
        raise VerificationError("formula.q3_sha256 disagrees")
    if np.count_nonzero(q3) > 2:
        raise VerificationError("sparse Q3 surface has more than two supports")
    if np.any(q3[~legal] != 0.0):
        raise VerificationError("sparse Q3 has an illegal nonzero cell")
    if np.any(q3[np.arange(USERS), reference] != 0.0):
        raise VerificationError("sparse Q3 has a nonzero reference cell")

    formula_summary = {
        "own_bits": own.tolist(),
        "nonfocal_bits": nonfocal.tolist(),
        "d_bits": d.tolist(),
        "Psi_B": float(interaction_bits),
        "Psi_E": float(interaction_energy),
        "Psi": float(interaction_surplus),
        "z3_bits": z3.tolist(),
        "combined_bits": combined.tolist(),
        "shapley_bits": shapley.tolist(),
        "joint_surplus_bits": float(joint_surplus),
        "identity_residual_bits": float(identity_residual),
    }
    return expected, {"summary": formula_summary, "q3": q3}


def _composition_check(
    payload: Mapping[str, Any],
    profiles: Mapping[str, Mapping[str, Any]],
    selected: Mapping[str, Any],
    q3: np.ndarray,
) -> tuple[str, dict[str, Any]]:
    inputs = _mapping(payload["topology_inputs"], field="topology_inputs")
    base = _finite_array(inputs["base_surface"], field="base_surface", shape=(USERS, ACTIONS))
    legal = _bool_array(inputs["legal_mask"], field="legal_mask", shape=(USERS, ACTIONS))
    scores = np.where(legal, base + q3, -np.inf)
    if not np.all(np.any(legal, axis=1)):
        raise VerificationError("native mask contains an empty row")
    recomputed = np.argmax(scores, axis=1).astype(np.int64)
    composition = _mapping(payload.get("composition"), field="composition")
    selected_actions = _int_array(composition.get("selected_actions"), field="composition.selected_actions", shape=(USERS,))
    if not np.array_equal(selected_actions, recomputed):
        raise VerificationError("composition selected_actions disagree with native masked argmax")
    members = _int_array(selected["coalition_user_ids"], field="members", shape=(2,))
    proposed = _int_array(selected["proposed_actions"], field="proposed", shape=(2,))
    reference = _int_array(inputs["reference_actions"], field="reference", shape=(USERS,))
    nonmembers = np.ones(USERS, dtype=np.bool_)
    nonmembers[members] = False
    if not np.array_equal(selected_actions[nonmembers], reference[nonmembers]):
        adoption = "OTHER_PROFILE"
    else:
        adopted = [int(selected_actions[user]) == int(action) for user, action in zip(members.tolist(), proposed.tolist(), strict=True)]
        if adopted == [True, True]:
            adoption = "11"
        elif adopted == [True, False]:
            adoption = "10"
        elif adopted == [False, True]:
            adoption = "01"
        elif np.array_equal(selected_actions, reference):
            adoption = "00"
        else:
            adoption = "OTHER_PROFILE"
    if composition.get("adoption_profile") != adoption:
        raise VerificationError("composition adoption_profile disagrees")
    selected_record = _profile_record(
        _mapping(composition.get("record"), field="composition.record"),
        name="composition",
        users=USERS,
    )
    # The composed record must be internally valid; this is a separate native
    # action evaluation receipt and must not be silently substituted by a
    # profile record.
    if not np.array_equal(selected_record["actions"], selected_actions):
        raise VerificationError("composition.record actions disagree")
    return adoption, {
        "selected_actions": selected_actions.tolist(),
        "adoption_profile": adoption,
        "score_surface_sha256": hashlib.sha256(
            np.ascontiguousarray(base + q3, dtype=np.float64).tobytes()
        ).hexdigest(),
        "q3_nonzero_cells": int(np.count_nonzero(q3)),
    }


def _receipt_digest_evidence(
    payload: Mapping[str, Any], *, by_role: Mapping[str, Mapping[str, str]], manifest_receipt: Mapping[str, Any]
) -> dict[str, bool]:
    """Check receipt-bound runtime evidence without rerunning runtime code."""

    ephemeris = _mapping(payload.get("ephemeris_validation"), field="ephemeris_validation")
    if ephemeris.get("status") != "PASS":
        raise VerificationError("ephemeris validation receipt is not PASS")
    if ephemeris.get("file_set_sha256") != manifest_receipt["configuration"]["tle_file_set_sha256"]:
        raise VerificationError("ephemeris file-set digest disagrees with preflight")
    _digest_string(ephemeris.get("receipt_sha256"), field="ephemeris.receipt_sha256")
    inherited = _mapping(payload.get("inherited_validators"), field="inherited_validators")
    validator_fields = [key for key in inherited if key.endswith("_validator")]
    if not validator_fields or any(inherited[key] != "PASS" for key in validator_fields):
        raise VerificationError("inherited validator receipt is not all PASS")
    nonmutation = _mapping(payload.get("nonmutation_receipt"), field="nonmutation_receipt")
    for prefix in ("q1_parameter_sha256", "q2_parameter_sha256"):
        before = _digest_string(nonmutation.get(prefix + "_before"), field=prefix + "_before")
        after = _digest_string(nonmutation.get(prefix + "_after"), field=prefix + "_after")
        if before != after:
            raise VerificationError(prefix + " changed")
    if payload.get("decision") != "NO_QUALIFIED_PAIR_CASE":
        for field in ("live_digest_before", "live_digest_after_profiles", "live_digest_after_composed", "rng_digest_before", "rng_digest_after_profiles", "rng_digest_after_composed"):
            _digest_string(nonmutation.get(field), field=field)
        if not (
            nonmutation["live_digest_before"]
            == nonmutation["live_digest_after_profiles"]
            == nonmutation["live_digest_after_composed"]
            and nonmutation["rng_digest_before"]
            == nonmutation["rng_digest_after_profiles"]
            == nonmutation["rng_digest_after_composed"]
        ):
            raise VerificationError("counterfactual live/RNG digests changed")
    return {
        "tle_runtime_receipt_consistent": True,
        "inherited_validator_receipt_consistent": True,
        "q1_q2_parameter_receipt_unchanged": True,
        "counterfactual_live_rng_receipt_unchanged": True,
    }


def verify_payload(
    payload: Mapping[str, Any],
    *,
    repo: Path = REPO,
    manifest_path: Path = MANIFEST,
    digest_path: Path = MANIFEST_DIGEST,
    result_path: Path | None = None,
) -> dict[str, Any]:
    """Independently verify a parsed V0.22 result and return a compact report."""

    if not isinstance(payload, Mapping):
        raise VerificationError("result root is not an object")
    errors: list[str] = []
    checks: dict[str, bool] = {}

    reported_digest = payload.get("result_sha256")
    _check(
        checks,
        errors,
        "canonical_result_payload_sha256",
        lambda: (
            _digest_string(reported_digest, field="result_sha256"),
            _canonical_sha256({key: value for key, value in payload.items() if key != "result_sha256"})
            == reported_digest
            or (_ for _ in ()).throw(VerificationError("result_sha256 does not cover canonical payload")),
        ),
    )

    _check(checks, errors, "result_schema_and_claim_ceiling", lambda: (
        payload.get("schema") == SCHEMA
        and payload.get("claim_ceiling") == CLAIM_CEILING
        and payload.get("split") == "TRAIN_DEVELOPMENT"
        and payload.get("worlds") == list(WORLDS)
        and payload.get("lineage") == LINEAGE
        and payload.get("test_split_opened") is False
        and payload.get("learner_update") is False
        and payload.get("episode_training") is False
        or (_ for _ in ()).throw(VerificationError("result schema/claim ceiling drifted")),
    ))

    manifest_data: tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, str]]] | None = None
    manifest_data = _check(
        checks,
        errors,
        "external_preflight_manifest_and_bindings",
        lambda: _load_manifest(manifest_path=Path(manifest_path), digest_path=Path(digest_path), repo=Path(repo)),
    )
    if manifest_data is None:
        # Remaining checks cannot be made authoritative without the external
        # binding.  Return a compact failure report rather than a traceback.
        report = {
            "schema": VERIFICATION_SCHEMA,
            "status": "FAIL",
            "checks": checks,
            "errors": errors,
        }
        raise VerificationError(json.dumps(report, sort_keys=True))
    _manifest_obj, manifest_receipt, by_role = manifest_data
    _check(
        checks,
        errors,
        "result_preflight_receipt_matches_external_rebuild",
        lambda: _validate_preflight_receipt(payload.get("preflight"), manifest_receipt),
    )

    def check_file_claim(field: str, role: str) -> None:
        expected = by_role[role]
        claimed = _digest_string(payload.get(field), field=field)
        if claimed != expected["sha256"]:
            raise VerificationError(f"{field} disagrees with {role} binding")

    for field, role in (
        ("runner_sha256", "runner"),
        ("contract_sha256", "contract"),
        ("formula_sha256", "formula"),
        ("prereg_sha256", "preregistration"),
    ):
        _check(checks, errors, f"{role}_hash", lambda field=field, role=role: check_file_claim(field, role))
    _check(checks, errors, "checkpoint_hashes", lambda: _check_checkpoint_receipts(payload, by_role))

    selected: dict[str, Any] | None = None
    scan_summary = _check(checks, errors, "ordered_scan_and_topology_recompute", lambda: _validate_scan(payload))
    if scan_summary is not None:
        selected, scan_info = scan_summary
    else:
        scan_info = {}

    profiles: dict[str, dict[str, Any]] | None = None
    public_good: dict[str, bool] = {}
    formula_payload: tuple[dict[str, Any], dict[str, Any]] | None = None
    composition_summary: dict[str, Any] = {}
    adoption: str | None = None
    if selected is not None:
        # The topology-input receipt is repeated at the result root for the
        # selected anchor.  It must equal the selected scan row's persisted
        # inputs; this blocks post-outcome substitution of the inputs used for
        # profile recomputation.
        _check(checks, errors, "selected_topology_inputs_match_scan", lambda: _selected_inputs_match_scan(payload))
        profile_result = _check(
            checks,
            errors,
            "profile_totals_ee_service_beam_sets",
            lambda: _verify_profiles(payload, selected),
        )
        if profile_result is not None:
            profiles, public_good = profile_result
        if profiles is not None:
            formula_payload = _check(
                checks,
                errors,
                "independent_l_e_d_psi_shapley_identity",
                lambda: _formula_check(payload, profiles, selected),
            )
        if formula_payload is not None and profiles is not None:
            adoption = _check(checks, errors, "native_masked_argmax_and_adoption", lambda: _composition_check(payload, profiles, selected, formula_payload[1]["q3"]))
            if adoption is not None:
                adoption, composition_summary = adoption
        _check(checks, errors, "runtime_receipt_digests", lambda: _receipt_digest_evidence(payload, by_role=by_role, manifest_receipt=manifest_receipt))

    if selected is None and payload.get("decision") == "NO_QUALIFIED_PAIR_CASE":
        _check(checks, errors, "no_case_runtime_receipt_digests", lambda: _receipt_digest_evidence(payload, by_role=by_role, manifest_receipt=manifest_receipt))

    if selected is not None and profiles is not None and formula_payload is not None and adoption is not None:
        _check(checks, errors, "ratio_of_sums_sign_identity", lambda: _ratio_sign_check(payload, profiles))
        mechanics = {
            "contract_authenticated": checks.get("contract_hash", False),
            "formula_authenticated": checks.get("formula_hash", False),
            "prereg_authenticated": checks.get("preregistration_hash", False),
            "checkpoint_authenticated": checks.get("checkpoint_hashes", False),
            "tle_runtime_validated": checks.get("runtime_receipt_digests", False),
            "inherited_validators_passed": checks.get("runtime_receipt_digests", False),
            "topology_selected_preoutcome": checks.get("ordered_scan_and_topology_recompute", False)
            and checks.get("selected_topology_inputs_match_scan", False),
            "source_beam_public_good_signature": public_good.get("source_beam_public_good_signature", False),
            "joint_opens_no_new_beam": public_good.get("joint_opens_no_new_beam", False),
            "joint_removes_exactly_source_beam": public_good.get("joint_removes_exactly_source_beam", False),
            "pair_served_all_profiles": public_good.get("pair_served_all_profiles", False),
            "joint_service_noninferior": public_good.get("joint_service_noninferior", False),
            "formula_identity_verified": checks.get("independent_l_e_d_psi_shapley_identity", False),
            "ratio_sign_identity_agrees": checks.get("ratio_of_sums_sign_identity", False),
            "live_state_and_rng_unchanged": checks.get("runtime_receipt_digests", False),
            "q1_q2_unchanged": checks.get("runtime_receipt_digests", False),
            "sparse_q3_exact_zero_fill": checks.get("independent_l_e_d_psi_shapley_identity", False),
        }
        mechanics_passed = all(mechanics.values())
        recomputed_decision = (
            "GO_LC_SRS_OBSERVABILITY_GATE"
            if mechanics_passed and public_good.get("joint_ee_positive", False) and adoption == "11"
            else "REDESIGN_COALITION_INTERFACE"
            if mechanics_passed and public_good.get("joint_ee_positive", False)
            else "STOP_THIS_COALITION_PROPOSAL"
        )
    elif selected is None:
        mechanics = {}
        mechanics_passed = False
        recomputed_decision = "NO_QUALIFIED_PAIR_CASE"
    else:
        mechanics = {}
        mechanics_passed = False
        recomputed_decision = "VERIFICATION_INCOMPLETE"

    _check(
        checks,
        errors,
        "decision_reproduced_without_reported_mechanics_booleans",
        lambda: payload.get("decision") == recomputed_decision
        or (_ for _ in ()).throw(VerificationError(f"decision differs: expected {recomputed_decision}")),
    )
    reported_mechanics = payload.get("mechanics")
    if isinstance(reported_mechanics, Mapping) and mechanics:
        _check(
            checks,
            errors,
            "reported_mechanics_booleans_cross_checked",
            lambda: _cross_check_reported_mechanics(reported_mechanics, mechanics),
        )

    report = {
        "schema": VERIFICATION_SCHEMA,
        "status": "PASS" if not errors else "FAIL",
        "result_path": str(Path(result_path).resolve()) if result_path is not None else None,
        "result_sha256": reported_digest,
        "checks": checks,
        "errors": errors,
        "selected_anchor": (
            {"world": payload.get("selected_world"), "step": payload.get("selected_step"), **dict(selected)}
            if selected is not None
            else None
        ),
        "scan": scan_info,
        "profiles": _profile_summary(profiles) if profiles is not None else {},
        "public_good": public_good,
        "formula": formula_payload[1]["summary"] if formula_payload is not None else {},
        "composition": composition_summary,
        "adoption_profile": adoption,
        "reported_decision": payload.get("decision"),
        "recomputed_decision": recomputed_decision,
        "recomputed_mechanics_passed": mechanics_passed,
        "mechanics": mechanics,
        "hashes": {
            "manifest_sha256": manifest_receipt["manifest_file_sha256"],
            "runner_sha256": by_role["runner"]["sha256"],
            "contract_sha256": by_role["contract"]["sha256"],
            "formula_sha256": by_role["formula"]["sha256"],
            "prereg_sha256": by_role["preregistration"]["sha256"],
            "checkpoint_sha256": by_role["selected_q1_q2_checkpoint"]["sha256"],
        },
    }
    if errors:
        raise VerificationError(json.dumps(report, sort_keys=True))
    return report


def _check_checkpoint_receipts(
    payload: Mapping[str, Any], by_role: Mapping[str, Mapping[str, str]]
) -> None:
    checkpoint = by_role["selected_q1_q2_checkpoint"]
    for field in ("q1_receipt", "q2_receipt"):
        receipt = _mapping(payload.get(field), field=field)
        path = receipt.get("checkpoint_path")
        if not isinstance(path, str) or Path(path).resolve() != (REPO / checkpoint["path"]).resolve():
            raise VerificationError(f"{field}.checkpoint_path disagrees")
        if receipt.get("checkpoint_sha256") != checkpoint["sha256"]:
            raise VerificationError(f"{field}.checkpoint_sha256 disagrees")
        if receipt.get("combined_checkpoint") is not True:
            raise VerificationError(f"{field} is not the combined checkpoint")


def _selected_inputs_match_scan(payload: Mapping[str, Any]) -> None:
    selected_world = payload.get("selected_world")
    selected_step = payload.get("selected_step")
    scan = payload.get("scan")
    if not isinstance(scan, list):
        raise VerificationError("scan malformed")
    matches = [
        row for row in scan
        if isinstance(row, Mapping)
        and row.get("world") == selected_world
        and row.get("step") == selected_step
    ]
    if len(matches) != 1:
        raise VerificationError("selected scan row is missing or duplicated")
    root_inputs = _mapping(payload.get("topology_inputs"), field="topology_inputs")
    row_inputs = _mapping(matches[0].get("topology_inputs"), field="scan.topology_inputs")
    if dict(root_inputs) != dict(row_inputs):
        raise VerificationError("root topology_inputs differ from selected scan inputs")


def _ratio_sign_check(payload: Mapping[str, Any], profiles: Mapping[str, Mapping[str, Any]]) -> None:
    delta_bits = profiles["11"]["total_bits"] - profiles["00"]["total_bits"]
    delta_energy = profiles["11"]["energy_j"] - profiles["00"]["energy_j"]
    value = delta_bits - profiles["00"]["ee"] * delta_energy
    expected_positive = value > 0.0
    actual_positive = profiles["11"]["ee"] > profiles["00"]["ee"]
    if expected_positive != actual_positive:
        raise VerificationError("ratio-of-sums sign identity disagrees")
    if not _close(_finite_float(payload.get("ratio_reference_identity_bits"), field="ratio_reference_identity_bits"), value):
        raise VerificationError("ratio_reference_identity_bits disagrees")


def _cross_check_reported_mechanics(
    reported: Mapping[str, Any], recomputed: Mapping[str, bool]
) -> None:
    for key, value in recomputed.items():
        if key in reported and reported[key] is not value:
            raise VerificationError(f"reported mechanics.{key} disagrees with recomputation")


def _profile_summary(profiles: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    return {
        name: {
            "total_bits": float(profile["total_bits"]),
            "energy_j": float(profile["energy_j"]),
            "ee_bits_per_j": float(profile["ee"]),
            "served_users": int(profile["served_users"]),
            "active_beam_count": len(profile["beams"]),
        }
        for name, profile in profiles.items()
    }


def verify_result_file(
    result_path: Path,
    *,
    output_path: Path | None = None,
    repo: Path = REPO,
    manifest_path: Path = MANIFEST,
    digest_path: Path = MANIFEST_DIGEST,
) -> dict[str, Any]:
    source = Path(result_path)
    if source.is_symlink() or not source.is_file():
        raise VerificationError(f"result is not a regular file: {source}")
    try:
        raw = source.read_bytes()
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VerificationError("result is not ASCII JSON") from error
    if raw not in (_canonical_bytes(payload), _canonical_bytes(payload) + b"\n"):
        raise VerificationError("result is not canonical JSON")
    report = verify_payload(
        payload,
        repo=Path(repo),
        manifest_path=Path(manifest_path),
        digest_path=Path(digest_path),
        result_path=source,
    )
    if output_path is not None:
        target = Path(output_path)
        if target.exists() or target.is_symlink():
            raise VerificationError(f"refusing to overwrite verification output: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_canonical_bytes(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--manifest-digest", type=Path, default=MANIFEST_DIGEST)
    args = parser.parse_args()
    try:
        report = verify_result_file(
            args.result,
            output_path=args.output,
            repo=REPO,
            manifest_path=args.manifest,
            digest_path=args.manifest_digest,
        )
    except VerificationError as error:
        text = str(error)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = {"schema": VERIFICATION_SCHEMA, "status": "FAIL", "errors": [text]}
        print(json.dumps(parsed, sort_keys=True, separators=(",", ":")))
        return 1
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
