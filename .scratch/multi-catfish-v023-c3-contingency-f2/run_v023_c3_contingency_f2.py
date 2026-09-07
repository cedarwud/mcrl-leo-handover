#!/usr/bin/env python3
"""V0.23 C3 contingency F2 shared four-world oracle screen.

Imports and ``--dry-run`` are simulator-inert. Real work is one authenticated
world x lineage unit at a time; ``--merge`` authenticates exactly twelve
immutable unit receipts and emits one immutable terminal receipt.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import math
import os
from pathlib import Path
import sys
import tempfile
import traceback
from types import SimpleNamespace
from typing import Any, Callable, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
F1_DIR = REPO / ".scratch" / "multi-catfish-v023-c3-contingency-f1"
V020_DIR = REPO / ".scratch" / "multi-catfish-v020-c3-source-audit"
for _path in (F1_DIR, V020_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

# These are normal imports of the sealed predecessors. In particular, F2 does
# not copy, rewrite, or alias the F1/F0 implementation.
import run_v023_c3_contingency_f1 as f1  # noqa: E402
import run_v020_repriced_c3_gate as v020_loader  # noqa: E402
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402


SCHEMA = "multi-catfish-mcrl-v023-c3-contingency-f2-v1"
PREFLIGHT_SCHEMA = f"{SCHEMA}-preflight-manifest"
LAUNCH_AUTHORITY_SCHEMA = f"{SCHEMA}-launch-authority"
UNIT_TAPE_SCHEMA = f"{SCHEMA}-unit-physical-tape"
UNIT_TAPE_MANIFEST_SCHEMA = f"{SCHEMA}-unit-physical-tape-manifest"
UNIT_RECEIPT_SCHEMA = f"{SCHEMA}-unit-receipt"
TERMINAL_RECEIPT_SCHEMA = f"{SCHEMA}-terminal-receipt"
CLAIM_CEILING = "TRAIN_DEVELOPMENT_C3_CONTINGENCY_F2_ORACLE_SCREEN_NO_EFFICACY_NO_TEST"

WORLDS = (2026121721, 2026121722, 2026121723, 2026121724)
LINEAGES = (2026092101, 2026092102, 2026092103)
CANONICAL_STEP_INDICES = tuple(range(10))
STEP_COUNT = 10
USERS = 100
SPLIT = "TRAIN"
FIELD_COMPONENT = "MCRL_V023_LCSRS_C3_OBSERVABILITY_V1"
SERVICE_MARGIN = 0.001
CANDIDATE_ORDER = ("D", "F")
WORLD_DIRECTION_MIN = 3
LINEAGE_DIRECTION_MIN = 2

Q2_INITIALIZATION_BY_LINEAGE = {
    2026092101: 2026108101,
    2026092102: 2026108102,
    2026092103: 2026108103,
}
CHECKPOINT_SHA256_BY_LINEAGE = {
    2026092101: "d40a0f3095f9bb9010d0146a88a77b3c8a824fb9bd3e5aee2205f3ae8be592dc",
    2026092102: "bb45bed30465f8be0ea9a1463c3b6e958d8f8b90cf11b4cd8e5d56a71f4b7057",
    2026092103: "32b5accfa1595ff19ddc11779402b5c86e115b883d04c6c5cbf90434ee32d44c",
}
AUTHORITY_BODY_SHA256_BY_LINEAGE = {
    2026092101: "50d32dae11b2906bb23a25893f4ba5c11d0f88197ee94fe7cd216677e8703d48",
    2026092102: "3b50f66bf3cf3f26adce15935adefd5751954cfffe79c72e7a02150c851bfc1f",
    2026092103: "503122a09c0c02ccd52aec55b50448950de00b8a194cd83ed4dda37f3f82a30f",
}
AUTHORITY_FILE_SHA256_BY_LINEAGE = {
    2026092101: "a05ee801c8f9d640b55f8ec984d874f149c30b868d1706d998f7e2053520078e",
    2026092102: "5a5bed3617437bbc981afc4de0b5880a3a5c91d3e3d857ac825527ae728ce64f",
    2026092103: "20f7ed79b1797e4ff8e6d2dc6de086b44341a0d0c6e7725a110027b062ff50c0",
}

DEFAULT_PREFLIGHT = HERE / "F2-PREFLIGHT-MANIFEST.json"
DEFAULT_TAPE_NAME = "physical-unilateral-tape.json"
DEFAULT_TAPE_MANIFEST_NAME = "physical-unilateral-tape.manifest.json"
DEFAULT_UNIT_RECEIPT_NAME = "receipt.json"
DEFAULT_TERMINAL_RECEIPT_NAME = "terminal-receipt.json"


class F2Error(RuntimeError):
    """An F2 binding, unit, receipt, or merge failed closed."""


class F2NotAdmitted(F2Error):
    """The sealed F1 result contains no surviving candidate."""


@dataclass(frozen=True, order=True)
class UnitKey:
    world: int
    lineage: int

    @classmethod
    def parse(cls, value: str) -> "UnitKey":
        try:
            world_text, lineage_text = value.split(":", 1)
            key = cls(int(world_text), int(lineage_text))
        except (AttributeError, TypeError, ValueError) as error:
            raise F2Error("unit must be WORLD:LINEAGE") from error
        key.verify()
        return key

    def verify(self) -> None:
        if type(self.world) is not int or self.world not in WORLDS:
            raise F2Error("unit world is outside the frozen four-world panel")
        if type(self.lineage) is not int or self.lineage not in LINEAGES:
            raise F2Error("unit lineage is outside the frozen three-lineage panel")

    @property
    def slug(self) -> str:
        self.verify()
        return f"{self.world}-{self.lineage}"

    def as_dict(self) -> dict[str, object]:
        self.verify()
        field = KeyedFadingField.from_components(FIELD_COMPONENT, self.world)
        return {
            "world": self.world,
            "lineage": self.lineage,
            "canonical_step_indices": list(CANONICAL_STEP_INDICES),
            "step_count": STEP_COUNT,
            "split": SPLIT,
            "field_component": FIELD_COMPONENT,
            "field_root_digest": field.root_digest,
            "users": USERS,
        }


ALL_UNITS = tuple(UnitKey(world, lineage) for world in WORLDS for lineage in LINEAGES)


def _checkpoint_path(lineage: int) -> Path:
    if lineage not in LINEAGES:
        raise F2Error("lineage is outside the frozen panel")
    q2_init = Q2_INITIALIZATION_BY_LINEAGE[lineage]
    return (
        V020_DIR
        / "repriced-q1-q2-fit"
        / f"lineage-{lineage}"
        / "checkpoints"
        / f"lineage-{lineage}-q2init-{q2_init}-rung-003000.pt"
    )


def _authority_path(lineage: int) -> Path:
    return _checkpoint_path(lineage).parents[1] / "authority.json"


def _repo_relative(path: Path) -> str:
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(REPO.resolve()):
        raise F2Error(f"binding escapes repository: {path}")
    return resolved.relative_to(REPO.resolve()).as_posix()


def _digest(value: object, *, field: str) -> str:
    try:
        return f1._digest(value, field=field)
    except f1.F1Error as error:
        raise F2Error(str(error)) from error


def _load_json(path: Path, *, field: str) -> dict[str, Any]:
    try:
        return f1._load_json(path, field=field)
    except f1.F1Error as error:
        raise F2Error(str(error)) from error


def canonical_bytes(value: object) -> bytes:
    try:
        return f1.canonical_bytes(value)
    except f1.F1Error as error:
        raise F2Error(str(error)) from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    try:
        return f1.file_sha256(path)
    except f1.F1Error as error:
        raise F2Error(str(error)) from error


def lineage_authority_bindings() -> list[dict[str, object]]:
    rows = []
    for lineage in LINEAGES:
        checkpoint = _checkpoint_path(lineage)
        authority = _authority_path(lineage)
        rows.append(
            {
                "lineage": lineage,
                "q2_initialization": Q2_INITIALIZATION_BY_LINEAGE[lineage],
                "checkpoint": {
                    "path": _repo_relative(checkpoint),
                    "sha256": CHECKPOINT_SHA256_BY_LINEAGE[lineage],
                    "role": f"V020_REPRICED_LINEAGE_{lineage}_RUNG_003000",
                },
                "q12_authority": {
                    "path": _repo_relative(authority),
                    "file_sha256": AUTHORITY_FILE_SHA256_BY_LINEAGE[lineage],
                    "body_sha256": AUTHORITY_BODY_SHA256_BY_LINEAGE[lineage],
                },
            }
        )
    return rows


def panel_bindings() -> dict[str, object]:
    return {
        "worlds": list(WORLDS),
        "lineages": list(LINEAGES),
        "canonical_step_indices": list(CANONICAL_STEP_INDICES),
        "step_count_per_unit": STEP_COUNT,
        "unit_count": len(ALL_UNITS),
        "split": SPLIT,
        "field_component": FIELD_COMPONENT,
        "field_root_digests": {
            str(world): KeyedFadingField.from_components(FIELD_COMPONENT, world).root_digest
            for world in WORLDS
        },
        "users": USERS,
        "reference_deployment_rule": f1.REFERENCE_DEPLOYMENT_RULE,
        "candidate_deployment_rule": f1.F1_DEPLOYMENT_RULE,
        "kappa_bits_hex": f1.KAPPA_BITS.hex(),
        "candidate_enumeration_rule": f1.CANDIDATE_ENUMERATION_RULE,
        "service_margin": SERVICE_MARGIN,
        "ee_rule": "POOLED_RATIO_OF_SUMS_STRICTLY_ABOVE_BASE",
        "world_direction_rule": "STRICTLY_POSITIVE_IN_AT_LEAST_3_OF_4_WORLDS",
        "lineage_direction_rule": "STRICTLY_POSITIVE_IN_AT_LEAST_2_OF_3_LINEAGES",
        "candidate_priority": list(CANDIDATE_ORDER),
        "empty_mask_rule": "NOOP",
    }


def formula_digests() -> dict[str, object]:
    """Carry F1's exact formula digests and add only the declared F2 panel rule."""

    f1_digests = f1.formula_digests()
    panel_rule = canonical_bytes(
        {
            "pooled_ee": "candidate-ratio-of-sums>base-ratio-of-sums",
            "world_directions": ">=3/4",
            "lineage_directions": ">=2/3",
            "service": "candidate>=base-0.001",
            "integrity": "all-unit-mechanics-and-provenance",
            "priority": ["D", "F"],
        }
    )
    return {
        "reused_f1_formula_digests": f1_digests,
        "f2_panel_pass_rule_sha256": hashlib.sha256(panel_rule).hexdigest(),
    }


def expected_code_bindings() -> list[dict[str, str]]:
    paths: list[tuple[str, Path]] = [
        ("f2_runner", HERE / "run_v023_c3_contingency_f2.py"),
        ("f2_preflight_builder", HERE / "build_f2_preflight_manifest.py"),
        ("f1_runner_import", F1_DIR / "run_v023_c3_contingency_f1.py"),
        ("f1_preflight_builder_import", F1_DIR / "build_f1_preflight_manifest.py"),
        ("v020_multi_lineage_head_loader", V020_DIR / "run_v020_repriced_c3_gate.py"),
    ]
    seen = {path.resolve() for _, path in paths}
    for row in f1.expected_code_bindings():
        path = REPO / row["path"]
        if path.resolve() not in seen:
            paths.append((f"f1_import_{row['role']}", path))
            seen.add(path.resolve())
    return [
        {"role": role, "path": _repo_relative(path), "sha256": file_sha256(path)}
        for role, path in paths
    ]


def _validate_lineage_authority(lineage: int) -> None:
    checkpoint = _checkpoint_path(lineage)
    authority_path = _authority_path(lineage)
    matches = tuple(
        sorted(checkpoint.parent.glob(f"lineage-{lineage}-*-rung-003000.pt"))
    )
    if matches != (checkpoint,):
        raise F2Error(f"lineage {lineage} rung-003000 checkpoint is ambiguous")
    if file_sha256(checkpoint) != CHECKPOINT_SHA256_BY_LINEAGE[lineage]:
        raise F2Error(f"lineage {lineage} checkpoint bytes changed")
    if file_sha256(authority_path) != AUTHORITY_FILE_SHA256_BY_LINEAGE[lineage]:
        raise F2Error(f"lineage {lineage} authority bytes changed")
    authority = _load_json(authority_path, field=f"lineage {lineage} Q1/Q2 authority")
    unsigned = dict(authority)
    seal = unsigned.pop("authority_sha256", None)
    if (
        seal != AUTHORITY_BODY_SHA256_BY_LINEAGE[lineage]
        or canonical_sha256(unsigned) != seal
    ):
        raise F2Error(f"lineage {lineage} authority body seal disagrees")
    if (
        authority.get("lineage") != lineage
        or authority.get("q1_updates") != 10
        or authority.get("q2_initialization") != Q2_INITIALIZATION_BY_LINEAGE[lineage]
        or authority.get("q2_rungs") != [3, 10, 30, 100, 300, 1000, 3000]
        or authority.get("lambda_bits_per_j_hex") != f1.LAMBDA_BITS_PER_J.hex()
        or authority.get("contract_sha256") != f1.SOURCE_CONTRACT_SHA256
        or authority.get("repricing_contract_sha256") != f1.REPRICING_CONTRACT_SHA256
        or authority.get("test_split_opened") is not False
        or authority.get("simulator_run") is not False
        or authority.get("episode_training") is not False
    ):
        raise F2Error(f"lineage {lineage} Q1/Q2 authority semantics drifted")


def validate_static_bindings() -> dict[str, object]:
    if tuple(key for key in ALL_UNITS) != tuple(
        UnitKey(world, lineage) for world in WORLDS for lineage in LINEAGES
    ):
        raise F2Error("unit matrix drifted")
    if WORLDS != tuple(range(2026121721, 2026121725)):
        raise F2Error("F2 worlds drifted")
    if LINEAGES != tuple(range(2026092101, 2026092104)):
        raise F2Error("F2 lineages drifted")
    if CANONICAL_STEP_INDICES != tuple(range(10)) or USERS != f1.USERS:
        raise F2Error("F2 step/user binding drifted")
    if (
        FIELD_COMPONENT != f1.FIELD_COMPONENT
        or f1.F1_DEPLOYMENT_RULE != "MASKED_ARGMAX_Q1_PLUS_Q2_PLUS_Z_OVER_KAPPA"
        or f1.KAPPA_BITS.hex() != "0x1.2cea89d260f2ap+33"
        or f1.SERVICE_MARGIN != SERVICE_MARGIN
    ):
        raise F2Error("F1-imported field/composition/service binding drifted")
    # This authenticates the corrected F1 code, its preflight builder, all
    # F1-bound formula sources, and the sealed STOP_PHYSICS branch.
    _f1_manifest, f1_preflight_sha = f1.validate_preflight_manifest(f1.DEFAULT_PREFLIGHT)
    for lineage in LINEAGES:
        _validate_lineage_authority(lineage)
    return {
        "bindings": panel_bindings(),
        "lineage_authorities": lineage_authority_bindings(),
        "f1_preflight": {
            "path": _repo_relative(f1.DEFAULT_PREFLIGHT),
            "sha256": f1_preflight_sha,
        },
        "formula_digests": formula_digests(),
    }


def validate_preflight_manifest(path: Path) -> tuple[dict[str, Any], str]:
    target = Path(path)
    payload = _load_json(target, field="F2 preflight manifest")
    expected = {
        "schema": PREFLIGHT_SCHEMA,
        "status": "FROZEN_PREFLIGHT",
        "claim_ceiling": CLAIM_CEILING,
        **validate_static_bindings(),
        "code_files": expected_code_bindings(),
    }
    if payload != expected:
        raise F2Error("F2 preflight manifest disagrees with exact bindings/code")
    digest = file_sha256(target)
    sidecar = target.with_suffix(".sha256")
    if sidecar.is_symlink() or not sidecar.is_file():
        raise F2Error("F2 preflight digest sidecar is missing or symlinked")
    if sidecar.read_text(encoding="ascii").split() != [digest, target.name]:
        raise F2Error("F2 preflight digest sidecar disagrees")
    return payload, digest


def _canonical_survivors(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or any(type(item) is not str for item in value):
        raise F2Error("surviving_candidates must be a JSON list")
    survivors = tuple(name for name in CANDIDATE_ORDER if name in value)
    if list(survivors) != value or len(set(value)) != len(value):
        raise F2Error("surviving_candidates must be the ordered D/F subset")
    return survivors


def _validate_f1_result(
    path: Path, *, expected_sha256: str, declared_survivors: Sequence[str]
) -> dict[str, Any]:
    target = Path(path)
    digest = _digest(expected_sha256, field="F1 result sha256")
    if file_sha256(target) != digest:
        raise F2Error("sealed F1 result digest disagrees")
    if target.stat().st_mode & 0o222:
        raise F2Error("sealed F1 result remains writable")
    receipt = _load_json(target, field="sealed F1 result")
    if (
        receipt.get("schema") != f1.RECEIPT_SCHEMA
        or receipt.get("status") != "COMPLETE"
        or receipt.get("claim_ceiling") != f1.CLAIM_CEILING
        or receipt.get("bindings") != f1.F1Bindings().as_dict()
        or receipt.get("authority") != f1.authority_bindings()
        or receipt.get("formula_digests") != f1.formula_digests()
        or receipt.get("test_split_opened") is not False
        or receipt.get("episode_training") is not False
        or receipt.get("learner_update") is not False
        or receipt.get("efficacy_claim") is not False
    ):
        raise F2Error("sealed F1 result semantics drifted")
    rules = receipt.get("kill_rules")
    if not isinstance(rules, Mapping) or set(rules) != set(CANDIDATE_ORDER):
        raise F2Error("sealed F1 result lacks complete D/F rule bundles")
    if any(
        not isinstance(rules[name], Mapping) or rules[name].get("integrity") is not True
        for name in CANDIDATE_ORDER
    ):
        raise F2Error("sealed F1 result has an integrity failure")
    observed = tuple(name for name in CANDIDATE_ORDER if rules[name].get("survives") is True)
    if tuple(declared_survivors) != observed:
        raise F2Error("launch-authority F1 survivor set disagrees with sealed result")
    expected_outcome = f1.adjudicate_outcome(rules)
    if receipt.get("outcome") != expected_outcome:
        raise F2Error("sealed F1 outcome disagrees with its rule bundles")
    if not observed:
        raise F2NotAdmitted("F2_NOT_ADMITTED: sealed F1 killed both D and F")
    return receipt


def _preflight_path_record(path: Path) -> str:
    resolved = Path(path).resolve()
    if resolved.is_relative_to(REPO.resolve()):
        return resolved.relative_to(REPO.resolve()).as_posix()
    return str(resolved)


def validate_launch_authority(
    path: Path, *, preflight_path: Path, preflight_sha256: str
) -> dict[str, Any]:
    payload = _load_json(path, field="F2 launch authority")
    if (
        payload.get("schema") != LAUNCH_AUTHORITY_SCHEMA
        or payload.get("status") != "FROZEN_LAUNCH_AUTHORITY"
        or payload.get("claim_ceiling") != CLAIM_CEILING
        or payload.get("preflight_manifest")
        != {
            "path": _preflight_path_record(preflight_path),
            "sha256": _digest(preflight_sha256, field="preflight sha256"),
        }
        or payload.get("bindings") != panel_bindings()
        or payload.get("test_split_opened") is not False
        or payload.get("episode_training") is not False
        or payload.get("learner_update") is not False
    ):
        raise F2Error("launch authority does not pin the exact F2 preflight/bindings")
    f1_record = payload.get("f1_result")
    if not isinstance(f1_record, Mapping):
        raise F2Error("launch authority lacks sealed F1 result binding")
    survivors = _canonical_survivors(f1_record.get("surviving_candidates"))
    f1_path = f1_record.get("path")
    if not isinstance(f1_path, str) or not Path(f1_path).is_absolute():
        raise F2Error("launch-authority F1 result path must be absolute")
    f1_sha = _digest(f1_record.get("sha256"), field="F1 result sha256")
    _validate_f1_result(
        Path(f1_path), expected_sha256=f1_sha, declared_survivors=survivors
    )
    return payload


def f1_result_binding(authority: Mapping[str, object]) -> dict[str, object]:
    record = authority.get("f1_result")
    if not isinstance(record, Mapping):
        raise F2Error("authority lacks F1 result binding")
    survivors = _canonical_survivors(record.get("surviving_candidates"))
    if not survivors:
        raise F2NotAdmitted("F2_NOT_ADMITTED: no F1 survivor")
    return {
        "path": record["path"],
        "sha256": _digest(record.get("sha256"), field="F1 result sha256"),
        "surviving_candidates": list(survivors),
    }


def _pooled_metrics(profiles: Sequence[f1.PhysicalProfile]) -> dict[str, float | int]:
    if not profiles:
        raise F2Error("pooled metrics require at least one profile")
    total_bits = math.fsum(
        profile.interval_s * math.fsum(float(value) for value in profile.link_rate_bps)
        for profile in profiles
    )
    total_energy = math.fsum(profile.network_energy_j for profile in profiles)
    served = sum(int(np.count_nonzero(profile.served)) for profile in profiles)
    opportunities = sum(profile.users for profile in profiles)
    if (
        not math.isfinite(total_bits)
        or total_bits < 0.0
        or not math.isfinite(total_energy)
        or total_energy <= 0.0
        or opportunities <= 0
    ):
        raise F2Error("pooled bits/energy/service are invalid")
    return {
        "total_bits": total_bits,
        "total_energy_j": total_energy,
        "ratio_of_sums_ee_bits_per_j": total_bits / total_energy,
        "served_user_steps": served,
        "service_opportunities": opportunities,
        "service_fraction": served / opportunities,
    }


def build_f2_step_payload(
    *, step_index: int, admitted_candidates: Sequence[str], **kwargs: object
) -> dict[str, object]:
    """Use F1's tape-step writer, widening only its bound step index to 0..9."""

    if type(step_index) is not int or step_index not in CANONICAL_STEP_INDICES:
        raise F2Error("step payload index is outside the ten canonical steps")
    survivors = tuple(admitted_candidates)
    if not survivors or any(name not in CANDIDATE_ORDER for name in survivors):
        raise F2Error("step payload requires an admitted D/F subset")
    try:
        row = f1.build_step_payload(step_index=step_index % 2, **kwargs)
    except f1.F1Error as error:
        raise F2Error(str(error)) from error
    row["step_index"] = step_index
    deployments = row["deployments"]
    assert isinstance(deployments, dict)
    for name in CANDIDATE_ORDER:
        deployments[name]["evaluated"] = name in survivors
    return row


def build_unit_tape_payload(
    *,
    key: UnitKey,
    steps: Sequence[Mapping[str, object]],
    q1_parameter_sha256: str,
    q2_parameter_sha256: str,
    preflight_manifest_sha256: str,
    f1_binding: Mapping[str, object],
) -> dict[str, object]:
    key.verify()
    return {
        "schema": UNIT_TAPE_SCHEMA,
        "status": "COMPLETE_IMMUTABLE_TAPE",
        "claim_ceiling": CLAIM_CEILING,
        "unit": key.as_dict(),
        "panel_bindings": panel_bindings(),
        "lineage_authority": lineage_authority_bindings()[LINEAGES.index(key.lineage)],
        "formula_digests": formula_digests(),
        "preflight_manifest_sha256": _digest(
            preflight_manifest_sha256, field="preflight_manifest_sha256"
        ),
        "f1_result": dict(f1_binding),
        "q1_parameter_sha256": _digest(q1_parameter_sha256, field="q1_parameter_sha256"),
        "q2_parameter_sha256": _digest(q2_parameter_sha256, field="q2_parameter_sha256"),
        "steps": [dict(step) for step in steps],
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }


def verify_unit_tape(tape: Mapping[str, object], *, key: UnitKey) -> dict[str, object]:
    key.verify()
    if tape.get("schema") != UNIT_TAPE_SCHEMA or tape.get("status") != "COMPLETE_IMMUTABLE_TAPE":
        raise F2Error("unit tape schema/status drifted")
    if (
        tape.get("claim_ceiling") != CLAIM_CEILING
        or tape.get("unit") != key.as_dict()
        or tape.get("panel_bindings") != panel_bindings()
        or tape.get("lineage_authority")
        != lineage_authority_bindings()[LINEAGES.index(key.lineage)]
        or tape.get("formula_digests") != formula_digests()
    ):
        raise F2Error("unit tape binding/formula drifted")
    for field in ("preflight_manifest_sha256", "q1_parameter_sha256", "q2_parameter_sha256"):
        _digest(tape.get(field), field=field)
    f1_binding = tape.get("f1_result")
    if not isinstance(f1_binding, Mapping):
        raise F2Error("unit tape lacks F1 admission binding")
    survivors = _canonical_survivors(f1_binding.get("surviving_candidates"))
    if not survivors:
        raise F2NotAdmitted("F2_NOT_ADMITTED: unit tape has no F1 survivor")
    _digest(f1_binding.get("sha256"), field="F1 result sha256")
    if not isinstance(f1_binding.get("path"), str):
        raise F2Error("unit tape F1 result path is malformed")
    if any(
        tape.get(field) is not False
        for field in ("test_split_opened", "episode_training", "learner_update", "efficacy_claim")
    ):
        raise F2Error("unit tape crossed a forbidden boundary")
    steps = tape.get("steps")
    if (
        not isinstance(steps, list)
        or len(steps) != STEP_COUNT
        or [row.get("step_index") for row in steps if isinstance(row, Mapping)]
        != list(CANONICAL_STEP_INDICES)
    ):
        raise F2Error("unit tape must contain exactly canonical steps 0..9")
    selected: dict[str, list[np.ndarray]] = {"BASE": [], "D": [], "F": []}
    profiles: dict[str, list[f1.PhysicalProfile]] = {"BASE": [], "D": [], "F": []}
    for step in steps:
        if not isinstance(step, Mapping):
            raise F2Error("unit tape step is malformed")
        try:
            q12 = f1._matrix_from_hex(step.get("q12"), field="q12")
            masks = np.asarray(step.get("action_masks"))
            reference = np.asarray(step.get("reference_actions"))
            base_profile = f1.profile_from_payload(step.get("reference_profile"))
            d_target, f_target = f1.target_surfaces_from_step(step)
        except f1.F1Error as error:
            raise F2Error(str(error)) from error
        if base_profile.users != USERS:
            raise F2Error(f"BASE profile must contain exactly {USERS} users")
        if q12.shape != (USERS, f1.NUM_ACTIONS) or masks.dtype != np.bool_ or masks.shape != q12.shape:
            raise F2Error("unit step Q/mask/profile dimensions disagree")
        base = f1.masked_argmax_q12_plus_z(q12, np.zeros_like(q12), masks)
        if reference.dtype.kind not in "iu" or not np.array_equal(reference, base):
            raise F2Error("BASE is not the masked Q1+Q2 argmax")
        deployments = step.get("deployments")
        if not isinstance(deployments, Mapping):
            raise F2Error("unit step deployment map is malformed")
        selected["BASE"].append(base)
        profiles["BASE"].append(base_profile)
        for name, target in (("D", d_target), ("F", f_target)):
            row = deployments.get(name)
            if not isinstance(row, Mapping) or row.get("evaluated") is not (name in survivors):
                raise F2Error(f"{name} deployment admission marker drifted")
            expected = (
                f1.masked_argmax_q12_plus_z(q12, target, masks)
                if name in survivors
                else base
            )
            actions = np.asarray(row.get("actions"))
            if actions.dtype.kind not in "iu" or not np.array_equal(actions, expected):
                raise F2Error(f"{name} deployment violates F1 composition/admission")
            profile = f1.profile_from_payload(row.get("profile"))
            if profile.users != USERS or profile.interval_s != base_profile.interval_s:
                raise F2Error(f"{name} deployment profile must match BASE users and interval")
            if name not in survivors and row.get("profile") != step.get("reference_profile"):
                raise F2Error(f"unadmitted {name} must be a non-evaluated BASE placeholder")
            selected[name].append(expected)
            profiles[name].append(profile)
    return {"survivors": survivors, "selected": selected, "profiles": profiles}


def screen_unit_tape(
    tape: Mapping[str, object], *, key: UnitKey, tape_sha256: str
) -> dict[str, object]:
    verified = verify_unit_tape(tape, key=key)
    survivors = verified["survivors"]
    profiles = verified["profiles"]
    selected = verified["selected"]
    metrics = {"BASE": _pooled_metrics(profiles["BASE"])}
    rules: dict[str, object] = {}
    for name in survivors:
        metrics[name] = _pooled_metrics(profiles[name])
        changed = any(
            not np.array_equal(candidate, base)
            for candidate, base in zip(selected[name], selected["BASE"], strict=True)
        )
        try:
            rules[name] = f1.evaluate_kill_rules(
                base_metrics=metrics["BASE"],
                candidate_metrics=metrics[name],
                action_changed=changed,
                integrity_ok=True,
            )
        except f1.F1Error as error:
            raise F2Error(str(error)) from error
    return {
        "schema": UNIT_RECEIPT_SCHEMA,
        "status": "COMPLETE",
        "outcome": "F2_UNIT_COMPLETE",
        "claim_ceiling": CLAIM_CEILING,
        "unit": key.as_dict(),
        "panel_bindings": panel_bindings(),
        "lineage_authority": tape["lineage_authority"],
        "formula_digests": formula_digests(),
        "preflight_manifest_sha256": tape["preflight_manifest_sha256"],
        "f1_result": tape["f1_result"],
        "tape_sha256": _digest(tape_sha256, field="tape_sha256"),
        "metrics": metrics,
        "unit_rules": rules,
        "mechanics_integrity": True,
        "provenance_integrity": True,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }


def _write_once(path: Path, payload: Mapping[str, object]) -> str:
    try:
        return f1._write_once(path, payload)
    except f1.F1Error as error:
        raise F2Error(str(error)) from error


def _unit_dir(output: Path, key: UnitKey) -> Path:
    return Path(output) / "units" / key.slug


def write_unit_bundle(
    output: Path, *, key: UnitKey, tape: Mapping[str, object]
) -> tuple[Path, Path, Path]:
    verify_unit_tape(tape, key=key)
    units_root = Path(output) / "units"
    if Path(output).is_symlink() or units_root.is_symlink():
        raise F2Error("output/units directory must not be a symlink")
    units_root.mkdir(parents=True, exist_ok=True)
    final = _unit_dir(output, key)
    if final.exists() or final.is_symlink():
        raise F2Error(f"refusing to overwrite write-once unit {key.slug}")
    stage = Path(tempfile.mkdtemp(prefix=f".stage-{key.slug}-", dir=units_root))
    try:
        tape_path = stage / DEFAULT_TAPE_NAME
        manifest_path = stage / DEFAULT_TAPE_MANIFEST_NAME
        receipt_path = stage / DEFAULT_UNIT_RECEIPT_NAME
        tape_sha = _write_once(tape_path, tape)
        manifest = {
            "schema": UNIT_TAPE_MANIFEST_SCHEMA,
            "status": "COMPLETE_IMMUTABLE_TAPE",
            "claim_ceiling": CLAIM_CEILING,
            "unit": key.as_dict(),
            "tape": {
                "path": DEFAULT_TAPE_NAME,
                "sha256": tape_sha,
                "bytes": tape_path.stat().st_size,
                "mode": "0444",
            },
            "formula_digests": formula_digests(),
            "preflight_manifest_sha256": tape["preflight_manifest_sha256"],
            "f1_result": tape["f1_result"],
        }
        _write_once(manifest_path, manifest)
        receipt = screen_unit_tape(tape, key=key, tape_sha256=tape_sha)
        _write_once(receipt_path, receipt)
        os.rename(stage, final)
    except BaseException:
        # A killed process may leave only a uniquely named stage directory.
        # It is never treated as a complete unit and never overwrites one.
        raise
    return (
        final / DEFAULT_TAPE_NAME,
        final / DEFAULT_TAPE_MANIFEST_NAME,
        final / DEFAULT_UNIT_RECEIPT_NAME,
    )


def authenticate_unit_bundle(
    output: Path,
    *,
    key: UnitKey,
    preflight_sha256: str,
    f1_binding: Mapping[str, object],
) -> tuple[dict[str, Any], str]:
    root = _unit_dir(output, key)
    tape_path = root / DEFAULT_TAPE_NAME
    manifest_path = root / DEFAULT_TAPE_MANIFEST_NAME
    receipt_path = root / DEFAULT_UNIT_RECEIPT_NAME
    if root.is_symlink() or any(path.is_symlink() for path in (tape_path, manifest_path, receipt_path)):
        raise F2Error(f"unit {key.slug} contains a symlink")
    tape = _load_json(tape_path, field=f"unit {key.slug} tape")
    manifest = _load_json(manifest_path, field=f"unit {key.slug} tape manifest")
    receipt = _load_json(receipt_path, field=f"unit {key.slug} receipt")
    if any(path.stat().st_mode & 0o222 for path in (tape_path, manifest_path, receipt_path)):
        raise F2Error(f"unit {key.slug} artifact remains writable")
    tape_sha = file_sha256(tape_path)
    expected_manifest = {
        "schema": UNIT_TAPE_MANIFEST_SCHEMA,
        "status": "COMPLETE_IMMUTABLE_TAPE",
        "claim_ceiling": CLAIM_CEILING,
        "unit": key.as_dict(),
        "tape": {
            "path": DEFAULT_TAPE_NAME,
            "sha256": tape_sha,
            "bytes": tape_path.stat().st_size,
            "mode": "0444",
        },
        "formula_digests": formula_digests(),
        "preflight_manifest_sha256": preflight_sha256,
        "f1_result": dict(f1_binding),
    }
    if manifest != expected_manifest:
        raise F2Error(f"unit {key.slug} tape manifest disagrees")
    if tape.get("preflight_manifest_sha256") != preflight_sha256 or tape.get("f1_result") != dict(f1_binding):
        raise F2Error(f"unit {key.slug} launch provenance disagrees")
    expected_receipt = screen_unit_tape(tape, key=key, tape_sha256=tape_sha)
    if receipt != expected_receipt:
        raise F2Error(f"unit {key.slug} receipt disagrees with authenticated tape")
    return receipt, file_sha256(receipt_path)


def _load_frozen_heads(lineage: int) -> Any:
    _validate_lineage_authority(lineage)
    try:
        q1, q1_receipt, q2, q2_receipt = v020_loader.load_repriced_heads(lineage)
    except Exception as error:
        raise F2Error(f"cannot load authenticated Q1/Q2 lineage {lineage}") from error
    checkpoint_sha = CHECKPOINT_SHA256_BY_LINEAGE[lineage]
    if (
        q1_receipt.get("checkpoint_sha256") != checkpoint_sha
        or q2_receipt.get("checkpoint_sha256") != checkpoint_sha
    ):
        raise F2Error("loaded Q1/Q2 receipt disagrees with frozen checkpoint")
    return SimpleNamespace(q1=q1, q2=q2, q1_receipt=q1_receipt, q2_receipt=q2_receipt)


def _generate_unit_tape(
    *,
    key: UnitKey,
    tle_root: Path,
    preflight_sha256: str,
    f1_binding: Mapping[str, object],
) -> dict[str, object]:
    """Extend the imported F1 tape generator mechanics to one ten-step unit."""

    key.verify()
    survivors = _canonical_survivors(f1_binding.get("surviving_candidates"))
    if not survivors:
        raise F2NotAdmitted("F2_NOT_ADMITTED: no F1 survivor")
    physical, server = f1._runtime_modules()
    from mcrl.runtime.prereg import read_prereg
    from mcrl.runtime.training_pipeline import _evaluation_rngs

    record = read_prereg(f1.PREREG_PATH)
    if record.digest != f1.PREREG_RECORD_DIGEST:
        raise F2Error("TRAIN PREREG record digest changed")
    frozen = _load_frozen_heads(key.lineage)
    q1_before = physical._parameter_sha256(frozen.q1)
    q2_before = physical._parameter_sha256(frozen.q2)
    field = KeyedFadingField.from_components(FIELD_COMPONENT, key.world)
    with tempfile.TemporaryDirectory(prefix=f"mcrl-v023-c3-f2-{key.slug}-tle-") as temporary:
        archive = server._freeze_archive(
            record, Path(tle_root), Path(temporary) / "frozen", physical
        )
        environment = server._make_environment(archive)
        step_env = environment.environment
        if getattr(step_env, "_started", False):
            raise F2Error("environment started before matched keyed field binding")
        step_env._fading_field = field
        rngs = tuple(_evaluation_rngs(key.world))
        if len(rngs) < 2:
            raise F2Error("canonical RNG factory lacks environment/mobility streams")
        _states, _masks, observation = environment.reset(rngs[0], rngs[1])
        interval_s = float(step_env.driver.config.ephemeris.time_step_s)
        if not math.isfinite(interval_s) or interval_s <= 0.0:
            raise F2Error("canonical decision interval is invalid")
        steps: list[dict[str, object]] = []
        for step_index in CANONICAL_STEP_INDICES:
            if int(observation.step_index) != step_index:
                raise F2Error("canonical replay reached the wrong step")
            native, q12, reference = f1._q12_surface(
                physical, frozen, step_env, observation
            )
            masks = np.asarray(native.action_masks, dtype=np.bool_)
            reference_eval = step_env.evaluate_actions(reference, rngs[0])
            reference_profile, reference_link_power = f1.profile_from_evaluation(
                reference_eval, interval_s=interval_s
            )
            skeletons = f1.enumerate_unilateral_candidates(observation, reference)
            candidate_rows: list[dict[str, object]] = []
            d = np.zeros_like(np.asarray(q12, dtype=np.float64))
            ff = np.zeros_like(d)
            for skeleton in skeletons:
                actions = np.asarray(skeleton["candidate_joint_actions"], dtype=np.int64)
                evaluation = step_env.evaluate_actions(actions, rngs[0])
                profile, link_power = f1.profile_from_evaluation(
                    evaluation, interval_s=interval_s
                )
                focal = int(skeleton["focal_user"])
                action = int(skeleton["candidate_action"])
                target = f1.compute_c3_targets(
                    reference_profile,
                    profile,
                    focal_user=focal,
                    lambda_bits_per_j=f1.LAMBDA_BITS_PER_J,
                )
                d[focal, action] = target.d_bits
                ff[focal, action] = target.f_bits
                candidate_rows.append(
                    {**skeleton, "profile": profile, "link_power_w": link_power}
                )
            targets = {"D": d, "F": ff}
            selected: dict[str, np.ndarray] = {}
            deployment_profiles: dict[str, tuple[f1.PhysicalProfile, np.ndarray]] = {}
            cache = {
                tuple(int(value) for value in reference.tolist()): (
                    reference_profile,
                    reference_link_power,
                )
            }
            for name in CANDIDATE_ORDER:
                if name in survivors:
                    selected[name] = f1.masked_argmax_q12_plus_z(
                        q12, targets[name], masks
                    )
                    action_key = tuple(int(value) for value in selected[name].tolist())
                    if action_key not in cache:
                        evaluation = step_env.evaluate_actions(selected[name], rngs[0])
                        cache[action_key] = f1.profile_from_evaluation(
                            evaluation, interval_s=interval_s
                        )
                    deployment_profiles[name] = cache[action_key]
                else:
                    selected[name] = np.array(reference, dtype=np.int64, copy=True)
                    deployment_profiles[name] = (reference_profile, reference_link_power)
            step_payload = build_f2_step_payload(
                step_index=step_index,
                admitted_candidates=survivors,
                q12=q12,
                action_masks=masks,
                reference_actions=reference,
                reference_profile=reference_profile,
                reference_link_power_w=reference_link_power,
                candidates=candidate_rows,
                deployment_actions=selected,
                deployment_profiles=deployment_profiles,
                state_sha256=native.state_sha256,
                action_physical_key_table=f1.action_physical_keys(observation),
            )
            rd, rf = f1.target_surfaces_from_step(step_payload)
            if not np.array_equal(rd, d) or not np.array_equal(rf, ff):
                raise F2Error("serialized unilateral tape changed F0 D/F targets")
            environment.step(reference, rngs[0])
            committed = environment.last_outcome
            committed_profile, committed_link_power = f1.profile_from_evaluation(
                committed, interval_s=interval_s
            )
            if f1.profile_to_payload(
                committed_profile, link_power_w=committed_link_power
            ) != step_payload["reference_profile"]:
                raise F2Error("BASE counterfactual disagrees with committed reference step")
            if step_index < CANONICAL_STEP_INDICES[-1]:
                if bool(committed.done):
                    raise F2Error("canonical episode terminated before step 9")
                observation = committed.observation
            steps.append(step_payload)
    if (
        physical._parameter_sha256(frozen.q1) != q1_before
        or physical._parameter_sha256(frozen.q2) != q2_before
    ):
        raise F2Error("frozen Q1/Q2 parameters changed during F2 inference")
    tape = build_unit_tape_payload(
        key=key,
        steps=steps,
        q1_parameter_sha256=q1_before,
        q2_parameter_sha256=q2_before,
        preflight_manifest_sha256=preflight_sha256,
        f1_binding=f1_binding,
    )
    verify_unit_tape(tape, key=key)
    return tape


def _sum_metric_rows(rows: Sequence[Mapping[str, object]]) -> dict[str, float | int]:
    total_bits = math.fsum(float(row["total_bits"]) for row in rows)
    total_energy = math.fsum(float(row["total_energy_j"]) for row in rows)
    served = sum(int(row["served_user_steps"]) for row in rows)
    opportunities = sum(int(row["service_opportunities"]) for row in rows)
    if (
        not math.isfinite(total_bits)
        or total_bits < 0.0
        or not math.isfinite(total_energy)
        or total_energy <= 0.0
        or opportunities <= 0
    ):
        raise F2Error("merged metric totals are invalid")
    return {
        "total_bits": total_bits,
        "total_energy_j": total_energy,
        "ratio_of_sums_ee_bits_per_j": total_bits / total_energy,
        "served_user_steps": served,
        "service_opportunities": opportunities,
        "service_fraction": served / opportunities,
    }


def evaluate_panel_candidate(
    receipts: Sequence[Mapping[str, object]], *, candidate: str
) -> dict[str, object]:
    if candidate not in CANDIDATE_ORDER or len(receipts) != len(ALL_UNITS):
        raise F2Error("panel evaluation requires one candidate and exactly twelve receipts")
    base_rows: list[Mapping[str, object]] = []
    candidate_rows: list[Mapping[str, object]] = []
    by_world: dict[int, dict[str, list[Mapping[str, object]]]] = {
        world: {"BASE": [], candidate: []} for world in WORLDS
    }
    by_lineage: dict[int, dict[str, list[Mapping[str, object]]]] = {
        lineage: {"BASE": [], candidate: []} for lineage in LINEAGES
    }
    integrity_ok = True
    for receipt in receipts:
        metrics = receipt.get("metrics")
        unit = receipt.get("unit")
        rules = receipt.get("unit_rules")
        if not isinstance(metrics, Mapping) or not isinstance(unit, Mapping) or not isinstance(rules, Mapping):
            raise F2Error("unit receipt lacks panel inputs")
        if candidate not in metrics or candidate not in rules:
            raise F2Error(f"candidate {candidate} is not admitted in every unit")
        if (
            receipt.get("mechanics_integrity") is not True
            or receipt.get("provenance_integrity") is not True
            or not isinstance(rules[candidate], Mapping)
            or rules[candidate].get("integrity") is not True
        ):
            integrity_ok = False
        world = unit.get("world")
        lineage = unit.get("lineage")
        if world not in WORLDS or lineage not in LINEAGES:
            raise F2Error("unit receipt identity is outside the panel")
        base = metrics["BASE"]
        row = metrics[candidate]
        if not isinstance(base, Mapping) or not isinstance(row, Mapping):
            raise F2Error("unit metrics are malformed")
        base_rows.append(base)
        candidate_rows.append(row)
        by_world[world]["BASE"].append(base)
        by_world[world][candidate].append(row)
        by_lineage[lineage]["BASE"].append(base)
        by_lineage[lineage][candidate].append(row)
    pooled = {"BASE": _sum_metric_rows(base_rows), candidate: _sum_metric_rows(candidate_rows)}
    try:
        imported = f1.evaluate_kill_rules(
            base_metrics=pooled["BASE"],
            candidate_metrics=pooled[candidate],
            action_changed=True,
            integrity_ok=integrity_ok,
        )
    except f1.F1Error as error:
        raise F2Error(str(error)) from error
    world_directions: dict[str, bool] = {}
    for world in WORLDS:
        grouped = {
            "BASE": _sum_metric_rows(by_world[world]["BASE"]),
            candidate: _sum_metric_rows(by_world[world][candidate]),
        }
        world_directions[str(world)] = (
            grouped[candidate]["ratio_of_sums_ee_bits_per_j"]
            > grouped["BASE"]["ratio_of_sums_ee_bits_per_j"]
        )
    lineage_directions: dict[str, bool] = {}
    for lineage in LINEAGES:
        grouped = {
            "BASE": _sum_metric_rows(by_lineage[lineage]["BASE"]),
            candidate: _sum_metric_rows(by_lineage[lineage][candidate]),
        }
        lineage_directions[str(lineage)] = (
            grouped[candidate]["ratio_of_sums_ee_bits_per_j"]
            > grouped["BASE"]["ratio_of_sums_ee_bits_per_j"]
        )
    world_positive_count = sum(world_directions.values())
    lineage_positive_count = sum(lineage_directions.values())
    passes = (
        imported["integrity"]
        and imported["service_noninferior"]
        and imported["ee_strictly_above_base"]
        and world_positive_count >= WORLD_DIRECTION_MIN
        and lineage_positive_count >= LINEAGE_DIRECTION_MIN
    )
    return {
        "integrity": imported["integrity"],
        "pooled_ee_strictly_above_base": imported["ee_strictly_above_base"],
        "service_noninferior": imported["service_noninferior"],
        "world_positive_count": world_positive_count,
        "world_positive_required": WORLD_DIRECTION_MIN,
        "world_directions": world_directions,
        "lineage_positive_count": lineage_positive_count,
        "lineage_positive_required": LINEAGE_DIRECTION_MIN,
        "lineage_directions": lineage_directions,
        "pooled_metrics": pooled,
        "passes": bool(passes),
    }


def adjudicate_panel(candidate_rules: Mapping[str, Mapping[str, object]]) -> str:
    if not candidate_rules or any(name not in CANDIDATE_ORDER for name in candidate_rules):
        raise F2Error("panel adjudication requires an admitted D/F subset")
    if any(
        not isinstance(candidate_rules[name], Mapping)
        or candidate_rules[name].get("integrity") is not True
        for name in candidate_rules
    ):
        return "INVALID_RUN"
    if "D" in candidate_rules and candidate_rules["D"].get("passes") is True:
        return "F2_PASS_D"
    if "F" in candidate_rules and candidate_rules["F"].get("passes") is True:
        return "F2_PASS_F"
    return "F2_NO_SUPPORT"


def build_terminal_receipt(
    *,
    receipts: Sequence[Mapping[str, object]],
    receipt_digests: Sequence[tuple[UnitKey, str]],
    preflight_sha256: str,
    f1_binding: Mapping[str, object],
) -> dict[str, object]:
    if len(receipts) != len(ALL_UNITS) or len(receipt_digests) != len(ALL_UNITS):
        raise F2Error("terminal receipt requires exactly twelve complete units")
    if tuple(key for key, _digest_value in receipt_digests) != ALL_UNITS:
        raise F2Error("terminal receipt unit ordering/coverage drifted")
    if tuple(
        UnitKey(int(receipt["unit"]["world"]), int(receipt["unit"]["lineage"]))
        for receipt in receipts
    ) != ALL_UNITS:
        raise F2Error("terminal receipt inputs do not cover the exact unit matrix")
    survivors = _canonical_survivors(f1_binding.get("surviving_candidates"))
    candidate_rules = {
        name: evaluate_panel_candidate(receipts, candidate=name) for name in survivors
    }
    outcome = adjudicate_panel(candidate_rules)
    return {
        "schema": TERMINAL_RECEIPT_SCHEMA,
        "status": "INVALID_RUN" if outcome == "INVALID_RUN" else "COMPLETE",
        "outcome": outcome,
        "claim_ceiling": CLAIM_CEILING,
        "panel_bindings": panel_bindings(),
        "lineage_authorities": lineage_authority_bindings(),
        "formula_digests": formula_digests(),
        "preflight_manifest_sha256": _digest(preflight_sha256, field="preflight sha256"),
        "f1_result": dict(f1_binding),
        "unit_receipts": [
            {"unit": key.as_dict(), "path": f"units/{key.slug}/receipt.json", "sha256": digest}
            for key, digest in receipt_digests
        ],
        "candidate_rules": candidate_rules,
        "priority_applied": list(CANDIDATE_ORDER),
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }


def invalid_terminal_receipt(
    *, error: BaseException, preflight_sha256: str, f1_binding: Mapping[str, object]
) -> dict[str, object]:
    return {
        "schema": TERMINAL_RECEIPT_SCHEMA,
        "status": "INVALID_RUN",
        "outcome": "INVALID_RUN",
        "claim_ceiling": CLAIM_CEILING,
        "panel_bindings": panel_bindings(),
        "lineage_authorities": lineage_authority_bindings(),
        "formula_digests": formula_digests(),
        "preflight_manifest_sha256": _digest(preflight_sha256, field="preflight sha256"),
        "f1_result": dict(f1_binding),
        "unit_receipts": None,
        "candidate_rules": None,
        "priority_applied": list(CANDIDATE_ORDER),
        "error_type": type(error).__name__,
        "error_sha256": hashlib.sha256(str(error).encode("utf-8")).hexdigest(),
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }


def execute_unit(
    *,
    key: UnitKey,
    output: Path,
    tle_root: Path,
    preflight_sha256: str,
    authority: Mapping[str, object],
    generator: Callable[..., dict[str, object]] = _generate_unit_tape,
) -> tuple[Path, bool]:
    f1_binding = f1_result_binding(authority)
    final = _unit_dir(output, key)
    if final.exists() or final.is_symlink():
        authenticate_unit_bundle(
            output,
            key=key,
            preflight_sha256=preflight_sha256,
            f1_binding=f1_binding,
        )
        return final / DEFAULT_UNIT_RECEIPT_NAME, True
    tape = generator(
        key=key,
        tle_root=Path(tle_root),
        preflight_sha256=preflight_sha256,
        f1_binding=f1_binding,
    )
    _tape, _manifest, receipt = write_unit_bundle(output, key=key, tape=tape)
    return receipt, False


def _validate_existing_terminal(
    path: Path, *, preflight_sha256: str, f1_binding: Mapping[str, object]
) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o222:
        raise F2Error("terminal receipt is missing, symlinked, or writable")
    receipt = _load_json(path, field="terminal receipt")
    if (
        receipt.get("schema") != TERMINAL_RECEIPT_SCHEMA
        or receipt.get("outcome") not in {"F2_PASS_D", "F2_PASS_F", "F2_NO_SUPPORT", "INVALID_RUN"}
        or receipt.get("status")
        != ("INVALID_RUN" if receipt.get("outcome") == "INVALID_RUN" else "COMPLETE")
        or receipt.get("claim_ceiling") != CLAIM_CEILING
        or receipt.get("panel_bindings") != panel_bindings()
        or receipt.get("lineage_authorities") != lineage_authority_bindings()
        or receipt.get("formula_digests") != formula_digests()
        or receipt.get("preflight_manifest_sha256") != preflight_sha256
        or receipt.get("f1_result") != dict(f1_binding)
        or receipt.get("priority_applied") != list(CANDIDATE_ORDER)
        or any(
            receipt.get(field) is not False
            for field in ("test_split_opened", "episode_training", "learner_update", "efficacy_claim")
        )
    ):
        raise F2Error("terminal receipt binding drifted")
    return receipt


def execute_merge(
    *, output: Path, preflight_sha256: str, authority: Mapping[str, object]
) -> tuple[Path, bool]:
    root = Path(output)
    if root.is_symlink():
        raise F2Error("output directory must not be a symlink")
    root.mkdir(parents=True, exist_ok=True)
    f1_binding = f1_result_binding(authority)
    terminal = root / DEFAULT_TERMINAL_RECEIPT_NAME
    if terminal.exists() or terminal.is_symlink():
        observed = _validate_existing_terminal(
            terminal, preflight_sha256=preflight_sha256, f1_binding=f1_binding
        )
        if observed["outcome"] != "INVALID_RUN":
            receipts = []
            digests = []
            for key in ALL_UNITS:
                receipt, digest = authenticate_unit_bundle(
                    root,
                    key=key,
                    preflight_sha256=preflight_sha256,
                    f1_binding=f1_binding,
                )
                receipts.append(receipt)
                digests.append((key, digest))
            expected = build_terminal_receipt(
                receipts=receipts,
                receipt_digests=digests,
                preflight_sha256=preflight_sha256,
                f1_binding=f1_binding,
            )
            if observed != expected:
                raise F2Error("terminal receipt disagrees with its twelve unit receipts")
        return terminal, True
    try:
        receipts: list[dict[str, Any]] = []
        digests: list[tuple[UnitKey, str]] = []
        for key in ALL_UNITS:
            receipt, digest = authenticate_unit_bundle(
                root,
                key=key,
                preflight_sha256=preflight_sha256,
                f1_binding=f1_binding,
            )
            receipts.append(receipt)
            digests.append((key, digest))
        payload = build_terminal_receipt(
            receipts=receipts,
            receipt_digests=digests,
            preflight_sha256=preflight_sha256,
            f1_binding=f1_binding,
        )
    except Exception as error:
        payload = invalid_terminal_receipt(
            error=error,
            preflight_sha256=preflight_sha256,
            f1_binding=f1_binding,
        )
    _write_once(terminal, payload)
    return terminal, False


def run(args: argparse.Namespace) -> dict[str, object]:
    _manifest, preflight_sha = validate_preflight_manifest(Path(args.preflight_manifest))
    if args.dry_run:
        if args.launch_authority is not None:
            authority = validate_launch_authority(
                Path(args.launch_authority),
                preflight_path=Path(args.preflight_manifest),
                preflight_sha256=preflight_sha,
            )
            return {"preflight": Path(args.preflight_manifest), "authority": authority}
        return {"preflight": Path(args.preflight_manifest)}
    if args.launch_authority is None or args.output is None:
        raise F2Error("F2 execution requires --launch-authority and --output")
    authority = validate_launch_authority(
        Path(args.launch_authority),
        preflight_path=Path(args.preflight_manifest),
        preflight_sha256=preflight_sha,
    )
    if args.unit is not None:
        if args.tle_root is None:
            raise F2Error("--unit requires --tle-root")
        receipt, skipped = execute_unit(
            key=UnitKey.parse(args.unit),
            output=Path(args.output),
            tle_root=Path(args.tle_root),
            preflight_sha256=preflight_sha,
            authority=authority,
        )
        return {"receipt": receipt, "skipped": skipped, "mode": "unit"}
    terminal, skipped = execute_merge(
        output=Path(args.output),
        preflight_sha256=preflight_sha,
        authority=authority,
    )
    return {"receipt": terminal, "skipped": skipped, "mode": "merge"}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--unit", help="run one exact WORLD:LINEAGE shard")
    mode.add_argument("--merge", action="store_true", help="authenticate 12 shards and decide")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--preflight-manifest", type=Path, default=DEFAULT_PREFLIGHT)
    parser.add_argument("--launch-authority", type=Path)
    parser.add_argument("--tle-root", type=Path)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.dry_run and args.unit is None and not args.merge:
        print("F2_ERROR: real execution requires exactly one of --unit or --merge", file=sys.stderr)
        return 2
    try:
        result = run(args)
    except F2NotAdmitted as error:
        print(str(error), file=sys.stderr)
        return 3
    except Exception as error:
        print(f"F2_ERROR: {error}", file=sys.stderr)
        traceback.print_exception(error, file=sys.stderr)
        return 2
    if args.dry_run:
        print(f"F2_DRY_RUN_PASS preflight={result['preflight']}")
    else:
        state = "SKIPPED_COMPLETE" if result["skipped"] else "WRITTEN"
        print(f"F2_{str(result['mode']).upper()}_{state} receipt={result['receipt']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
