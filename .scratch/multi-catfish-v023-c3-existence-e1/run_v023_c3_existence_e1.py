#!/usr/bin/env python3
"""C3 existence screen E1: immutable world-lineage units and exact merge.

Imports and ``--dry-run`` are simulator-inert.  Unit execution reuses the F1
BASE/unilateral machinery and the F2 world-by-lineage/runtime conventions.
It adds only physically evaluated complete joint witness profiles.  Merge
authenticates all twelve units and solves U1 and J1 without running physics.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import traceback
from typing import Any, Callable, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
F0_DIR = REPO / ".scratch" / "multi-catfish-v023-c3-contingency"
F1_DIR = REPO / ".scratch" / "multi-catfish-v023-c3-contingency-f1"
F2_DIR = REPO / ".scratch" / "multi-catfish-v023-c3-contingency-f2"
for _path in (HERE, F0_DIR, F1_DIR, F2_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import e1_estimands as estimands  # noqa: E402
import run_v023_c3_contingency_f1 as f1  # noqa: E402
import run_v023_c3_contingency_f2 as f2  # noqa: E402
from c3_contingency_f0 import compute_cost_shares  # noqa: E402
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402


SCHEMA = "multi-catfish-mcrl-v023-c3-existence-e1-v1"
PREFLIGHT_SCHEMA = f"{SCHEMA}-preflight-manifest"
LAUNCH_AUTHORITY_SCHEMA = f"{SCHEMA}-launch-authority"
UNIT_TAPE_SCHEMA = f"{SCHEMA}-unit-physical-tape"
UNIT_TAPE_MANIFEST_SCHEMA = f"{SCHEMA}-unit-physical-tape-manifest"
UNIT_RECEIPT_SCHEMA = f"{SCHEMA}-unit-receipt"
TERMINAL_RECEIPT_SCHEMA = f"{SCHEMA}-terminal-receipt"
CLAIM_CEILING = (
    "TRAIN_DEVELOPMENT_C3_EXISTENCE_SCREEN_E1_NO_LEARNER_NO_EFFICACY_NO_TEST"
)

WORLD_DOMAIN_PREFIX = "C3_EXISTENCE_E1/world/"
WORLD_COUNT = 4
WORLD_DOMAINS = tuple(f"{WORLD_DOMAIN_PREFIX}{index}" for index in range(1, WORLD_COUNT + 1))
WORLD_SEED_MASK = (1 << 63) - 1
WORLD_SEED_DIGEST_BYTES = 8
LINEAGES = f2.LINEAGES
CANONICAL_STEP_INDICES = f2.CANONICAL_STEP_INDICES
STEP_COUNT = f2.STEP_COUNT
USERS = f1.USERS
SPLIT = f1.SPLIT
FIELD_COMPONENT = f1.FIELD_COMPONENT
SERVICE_MARGIN = estimands.SERVICE_MARGIN
DISALLOWED_HISTORICAL_WORLDS = frozenset(f2.WORLDS)

CONTRACT_FILENAME = "V023-C3-EXISTENCE-TEST-CONTRACT-E1-2026-09-08.md"
DEFAULT_PREFLIGHT = HERE / "E1-PREFLIGHT-MANIFEST.json"
DEFAULT_TAPE_NAME = "e1-physical-tape.json"
DEFAULT_TAPE_MANIFEST_NAME = "e1-physical-tape.manifest.json"
DEFAULT_UNIT_RECEIPT_NAME = "receipt.json"
DEFAULT_TERMINAL_RECEIPT_NAME = "terminal-receipt.json"

UNILATERAL_PROFILE_PREFIX = "U"
JOINT_PROFILE_PREFIX = "J"
BASE_PROFILE_ID = estimands.BASE_PROFILE_ID
UNILATERAL_OUTCOMES = ("E1_UNILATERAL_HEADROOM", "E1_UNILATERAL_CLOSED")
JOINT_OUTCOMES = ("E1_JOINT_HEADROOM", "E1_JOINT_CLOSED")


class E1Error(RuntimeError):
    """An E1 binding, tape, physical catalog, or receipt failed closed."""


def canonical_bytes(value: object) -> bytes:
    try:
        return f1.canonical_bytes(value)
    except f1.F1Error as error:
        raise E1Error(str(error)) from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    try:
        return f1.file_sha256(path)
    except f1.F1Error as error:
        raise E1Error(str(error)) from error


def _digest(value: object, *, field: str) -> str:
    try:
        return f1._digest(value, field=field)
    except f1.F1Error as error:
        raise E1Error(str(error)) from error


def _load_json(path: Path, *, field: str) -> dict[str, Any]:
    try:
        return f1._load_json(path, field=field)
    except f1.F1Error as error:
        raise E1Error(str(error)) from error


def _repo_relative(path: Path) -> str:
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(REPO.resolve()):
        raise E1Error(f"binding escapes repository: {path}")
    return resolved.relative_to(REPO.resolve()).as_posix()


def derive_world_seed(domain: str) -> int:
    """Apply the project's SHA-256/first-eight-bytes/positive-int63 rule."""

    if domain not in WORLD_DOMAINS:
        raise E1Error("world seed domain is outside the E1 four-domain set")
    digest = hashlib.sha256(domain.encode("ascii")).digest()
    return int.from_bytes(digest[:WORLD_SEED_DIGEST_BYTES], "big") & WORLD_SEED_MASK


def world_seeds() -> tuple[int, ...]:
    seeds = tuple(derive_world_seed(domain) for domain in WORLD_DOMAINS)
    if len(set(seeds)) != WORLD_COUNT or any(seed in DISALLOWED_HISTORICAL_WORLDS for seed in seeds):
        raise E1Error("E1 world seeds collide with each other or the F1/F2 panel")
    return seeds


WORLDS = world_seeds()


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
            raise E1Error("unit must be WORLD:LINEAGE") from error
        key.verify()
        return key

    def verify(self) -> None:
        if type(self.world) is not int or self.world not in WORLDS:
            raise E1Error("unit world is outside the derived E1 four-world panel")
        if type(self.lineage) is not int or self.lineage not in LINEAGES:
            raise E1Error("unit lineage is outside the three authenticated lineages")

    @property
    def slug(self) -> str:
        self.verify()
        return f"{self.world}-{self.lineage}"

    def as_dict(self) -> dict[str, object]:
        self.verify()
        field = KeyedFadingField.from_components(FIELD_COMPONENT, self.world)
        return {
            "world": self.world,
            "world_domain": WORLD_DOMAINS[WORLDS.index(self.world)],
            "lineage": self.lineage,
            "canonical_step_indices": list(CANONICAL_STEP_INDICES),
            "step_count": STEP_COUNT,
            "split": SPLIT,
            "field_component": FIELD_COMPONENT,
            "field_root_digest": field.root_digest,
            "users": USERS,
        }


ALL_UNITS = tuple(UnitKey(world, lineage) for world in WORLDS for lineage in LINEAGES)


def panel_bindings() -> dict[str, object]:
    return {
        "world_seed_derivation": {
            "algorithm": "SHA256_ASCII_FIRST_8_BYTES_BIG_ENDIAN_MASK_INT63",
            "domains": list(WORLD_DOMAINS),
            "seeds": list(WORLDS),
        },
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
        "base_rule": f1.REFERENCE_DEPLOYMENT_RULE,
        "unilateral_rule": f1.CANDIDATE_ENUMERATION_RULE,
        "joint_witness_rule": "EVACUATE_ALL_BASE_SERVED_USERS_OF_ONE_ORIGIN_BEAM_TO_EACH_COMMONLY_LEGAL_NONORIGIN_DESTINATION",
        "service_margin": SERVICE_MARGIN,
        "ee_rule": "POOLED_RATIO_OF_SUMS_STRICTLY_ABOVE_BASE",
        "base_advancement": "COMMIT_BASE_BETWEEN_CANONICAL_ANCHORS",
    }


def formula_digests() -> dict[str, object]:
    solver_rule = canonical_bytes(
        {
            "method": estimands.CERTIFICATE_METHOD,
            "service_margin_numerator": estimands.SERVICE_MARGIN_NUMERATOR,
            "service_margin_denominator": estimands.SERVICE_MARGIN_DENOMINATOR,
            "comparison": "STRICTLY_ABOVE_ETA_BASE",
        }
    )
    joint_rule = canonical_bytes(panel_bindings()["joint_witness_rule"])
    return {
        "reused_f1_formula_digests": f1.formula_digests(),
        "solver_rule_sha256": hashlib.sha256(solver_rule).hexdigest(),
        "joint_catalog_rule_sha256": hashlib.sha256(joint_rule).hexdigest(),
    }


def expected_code_bindings() -> list[dict[str, str]]:
    paths = (
        ("e1_runner", HERE / "run_v023_c3_existence_e1.py"),
        ("e1_estimands", HERE / "e1_estimands.py"),
        ("e1_preflight_builder", HERE / "build_e1_preflight_manifest.py"),
        ("f1_tape_machinery_import", F1_DIR / "run_v023_c3_contingency_f1.py"),
        ("f2_unit_merge_conventions_import", F2_DIR / "run_v023_c3_contingency_f2.py"),
        ("f0_conservation_import", F0_DIR / "c3_contingency_f0.py"),
        ("joint_profile_evaluator", REPO / "src/mcrl/env/step.py"),
        ("joint_profile_physics", REPO / "src/mcrl/env/link_budget.py"),
    )
    return [
        {"role": role, "path": _repo_relative(path), "sha256": file_sha256(path)}
        for role, path in paths
    ]


def validate_static_bindings() -> dict[str, object]:
    if LINEAGES != tuple(range(2026092101, 2026092104)):
        raise E1Error("lineage panel drifted")
    if CANONICAL_STEP_INDICES != tuple(range(STEP_COUNT)) or STEP_COUNT != 10:
        raise E1Error("E1 requires exactly canonical steps 0..9")
    if USERS != 100 or SPLIT != "TRAIN" or SERVICE_MARGIN != f1.SERVICE_MARGIN:
        raise E1Error("imported user/split/service binding drifted")
    if world_seeds() != WORLDS:
        raise E1Error("derived E1 world panel drifted")
    try:
        f2_static = f2.validate_static_bindings()
    except f2.F2Error as error:
        raise E1Error(f"F1/F2 reusable machinery failed authentication: {error}") from error
    return {
        "bindings": panel_bindings(),
        "lineage_authorities": f2.lineage_authority_bindings(),
        "formula_digests": formula_digests(),
        "reused_f2_preflight": f2_static["f1_preflight"],
    }


def validate_preflight_manifest(path: Path) -> tuple[dict[str, Any], str]:
    target = Path(path)
    payload = _load_json(target, field="E1 preflight manifest")
    expected = {
        "schema": PREFLIGHT_SCHEMA,
        "status": "FROZEN_PREFLIGHT",
        "claim_ceiling": CLAIM_CEILING,
        **validate_static_bindings(),
        "code_files": expected_code_bindings(),
    }
    if payload != expected:
        raise E1Error("E1 preflight manifest disagrees with exact bindings/code")
    digest = file_sha256(target)
    sidecar = target.with_suffix(".sha256")
    if sidecar.is_symlink() or not sidecar.is_file():
        raise E1Error("E1 preflight digest sidecar is missing or symlinked")
    if sidecar.read_text(encoding="ascii").split() != [digest, target.name]:
        raise E1Error("E1 preflight digest sidecar disagrees")
    return payload, digest


def _preflight_path_record(path: Path) -> str:
    resolved = Path(path).resolve()
    return _repo_relative(resolved) if resolved.is_relative_to(REPO.resolve()) else str(resolved)


def validate_launch_authority(
    path: Path, *, preflight_path: Path, preflight_sha256: str
) -> dict[str, Any]:
    payload = _load_json(path, field="E1 launch authority")
    expected_keys = {
        "schema", "status", "claim_ceiling", "preflight_manifest", "contract",
        "bindings", "test_split_opened", "episode_training", "learner_update",
        "efficacy_claim",
    }
    if set(payload) != expected_keys:
        raise E1Error("launch authority keys differ from the exact E1 contract")
    contract = payload.get("contract")
    if not isinstance(contract, Mapping) or set(contract) != {"path", "sha256"}:
        raise E1Error("launch authority contract binding needs exact path/sha256 keys")
    contract_path_text = contract.get("path")
    if not isinstance(contract_path_text, str):
        raise E1Error("launch authority contract path is malformed")
    contract_path = Path(contract_path_text)
    if (
        not contract_path.is_absolute()
        or contract_path.resolve().parent != HERE.resolve()
        or contract_path.name != CONTRACT_FILENAME
        or file_sha256(contract_path) != _digest(contract.get("sha256"), field="contract sha256")
    ):
        raise E1Error("launch authority does not bind the controller-placed E1 contract")
    expected = {
        "schema": LAUNCH_AUTHORITY_SCHEMA,
        "status": "FROZEN_LAUNCH_AUTHORITY",
        "claim_ceiling": CLAIM_CEILING,
        "preflight_manifest": {
            "path": _preflight_path_record(preflight_path),
            "sha256": _digest(preflight_sha256, field="preflight sha256"),
        },
        "contract": dict(contract),
        "bindings": panel_bindings(),
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }
    if payload != expected:
        raise E1Error("launch authority does not pin the exact E1 bindings")
    return payload


def _profile_metrics(profile: f1.PhysicalProfile) -> dict[str, object]:
    total_bits = profile.interval_s * math.fsum(float(value) for value in profile.link_rate_bps)
    total_energy = profile.network_energy_j
    served = int(np.count_nonzero(profile.served))
    if not math.isfinite(total_bits) or total_bits < 0.0 or total_energy <= 0.0:
        raise E1Error("physical profile metrics are invalid")
    return {
        "total_bits": total_bits.hex(),
        "total_energy_j": total_energy.hex(),
        "served": served,
        "opportunities": profile.users,
    }


def _solver_metrics(profile_id: str, profile: f1.PhysicalProfile) -> dict[str, object]:
    metrics = _profile_metrics(profile)
    return {
        "profile_id": profile_id,
        "total_bits": float.fromhex(str(metrics["total_bits"])),
        "total_energy_j": float.fromhex(str(metrics["total_energy_j"])),
        "served": metrics["served"],
        "opportunities": metrics["opportunities"],
    }


def _conservation(profile: f1.PhysicalProfile) -> dict[str, object]:
    result = compute_cost_shares(profile)
    residual = result.verify()
    return {
        "f0_schema": f1.F0_SCHEMA,
        "verified": True,
        "power_residual_w": result.conservation_residual_power_w.hex(),
        "energy_residual_j": residual.hex(),
    }


@dataclass(frozen=True)
class JointWitnessAnchor:
    """Runtime inputs for catalog construction at one matched anchor."""

    observation: Any
    reference_actions: np.ndarray
    reference_profile: f1.PhysicalProfile
    step_env: Any
    rng: np.random.Generator
    interval_s: float


def _legal_key_actions(observation: Any, user: int) -> dict[tuple[int, int], int]:
    table = tuple(observation.candidates.slot_tables)[user]
    mask = np.asarray(table.mask)
    if mask.dtype != np.bool_ or mask.shape != (f1.NUM_ACTIONS,):
        raise E1Error("joint catalog found a malformed legality mask")
    result: dict[tuple[int, int], int] = {}
    for raw_action in np.flatnonzero(mask).tolist():
        action = int(raw_action)
        key = f1._physical_key(table, action)
        if key is None:
            continue
        if key in result:
            raise E1Error("two legal slots alias one physical destination")
        result[key] = action
    return result


def build_joint_witness_catalog(anchor: JointWitnessAnchor) -> tuple[dict[str, object], ...]:
    """Evaluate every declared all-users-on-origin evacuation profile.

    A destination is retained only when the exact physical ``(satellite,
    cell)`` key is legal for every BASE-served user on the origin beam.
    Every row is evaluated once through ``StepEnvironment.evaluate_actions``;
    no unilateral quantities are added or composed.
    """

    reference = np.asarray(anchor.reference_actions)
    base = anchor.reference_profile
    if reference.dtype.kind not in "iu" or reference.shape != (base.users,):
        raise E1Error("joint catalog reference action vector is malformed")
    if base.users != len(tuple(anchor.observation.candidates.slot_tables)):
        raise E1Error("joint catalog profile/observation user counts disagree")
    origins: dict[tuple[int, int], list[int]] = {}
    for user in range(base.users):
        if bool(base.served[user]):
            key = (int(base.serving_satellite[user]), int(base.serving_cell[user]))
            origins.setdefault(key, []).append(user)
    rows: list[dict[str, object]] = []
    for origin in sorted(origins):
        users = tuple(origins[origin])
        legal_maps = tuple(_legal_key_actions(anchor.observation, user) for user in users)
        common = set(legal_maps[0])
        for mapping in legal_maps[1:]:
            common.intersection_update(mapping)
        common.discard(origin)
        for destination in sorted(common):
            actions = np.array(reference, dtype=np.int64, copy=True)
            for user, mapping in zip(users, legal_maps, strict=True):
                actions[user] = mapping[destination]
            evaluation = anchor.step_env.evaluate_actions(actions, anchor.rng)
            profile, link_power = f1.profile_from_evaluation(
                evaluation, interval_s=anchor.interval_s
            )
            conservation = _conservation(profile)
            profile_id = (
                f"{JOINT_PROFILE_PREFIX}:{origin[0]}:{origin[1]}"
                f"->{destination[0]}:{destination[1]}"
            )
            rows.append(
                {
                    "profile_id": profile_id,
                    "origin_physical_key": list(origin),
                    "destination_physical_key": list(destination),
                    "origin_users": list(users),
                    "candidate_joint_actions": [int(value) for value in actions.tolist()],
                    "profile": profile,
                    "link_power_w": link_power,
                    "metrics": _profile_metrics(profile),
                    "f0_conservation": conservation,
                }
            )
    return tuple(rows)


def _serialize_profile_row(row: Mapping[str, object]) -> dict[str, object]:
    result = dict(row)
    profile = result.pop("profile", None)
    link_power = result.pop("link_power_w", None)
    if not isinstance(profile, f1.PhysicalProfile):
        raise E1Error("physical candidate row lacks a PhysicalProfile")
    result["profile"] = f1.profile_to_payload(profile, link_power_w=link_power)
    return result


def build_step_payload(
    *,
    step_index: int,
    reference_actions: object,
    action_masks: object,
    reference_profile: f1.PhysicalProfile,
    reference_link_power_w: object,
    unilateral_candidates: Sequence[Mapping[str, object]],
    joint_catalog: Sequence[Mapping[str, object]],
    state_sha256: str,
    action_physical_key_table: Sequence[Sequence[Sequence[int] | None]],
) -> dict[str, object]:
    if type(step_index) is not int or step_index not in CANONICAL_STEP_INDICES:
        raise E1Error("step index is outside canonical steps 0..9")
    masks = np.asarray(action_masks)
    actions = np.asarray(reference_actions)
    if masks.dtype != np.bool_ or masks.shape != (USERS, f1.NUM_ACTIONS):
        raise E1Error("step action masks are malformed")
    if actions.dtype.kind not in "iu" or actions.shape != (USERS,):
        raise E1Error("step reference actions are malformed")
    _digest(state_sha256, field="state_sha256")
    return {
        "step_index": step_index,
        "state_sha256": state_sha256,
        "action_masks": [[bool(value) for value in row] for row in masks.tolist()],
        "action_physical_keys": [list(row) for row in action_physical_key_table],
        "reference_actions": [int(value) for value in actions.tolist()],
        "reference_profile": f1.profile_to_payload(
            reference_profile, link_power_w=reference_link_power_w
        ),
        "reference_metrics": _profile_metrics(reference_profile),
        "unilateral_candidates": [
            _serialize_profile_row(row) for row in unilateral_candidates
        ],
        "joint_witness_catalog": [_serialize_profile_row(row) for row in joint_catalog],
    }


def _expected_joint_keys(step: Mapping[str, object], base: f1.PhysicalProfile) -> list[tuple[tuple[int, int], tuple[int, int], tuple[int, ...]]]:
    masks = np.asarray(step.get("action_masks"))
    key_table = step.get("action_physical_keys")
    if masks.dtype != np.bool_ or masks.shape != (USERS, f1.NUM_ACTIONS):
        raise E1Error("serialized joint catalog masks are malformed")
    if not isinstance(key_table, list) or len(key_table) != USERS:
        raise E1Error("serialized physical key table is malformed")
    origins: dict[tuple[int, int], list[int]] = {}
    for user in range(USERS):
        if bool(base.served[user]):
            origins.setdefault(
                (int(base.serving_satellite[user]), int(base.serving_cell[user])), []
            ).append(user)
    expected = []
    for origin in sorted(origins):
        users = tuple(origins[origin])
        common: set[tuple[int, int]] | None = None
        for user in users:
            mapping: set[tuple[int, int]] = set()
            row = key_table[user]
            if not isinstance(row, list) or len(row) != f1.NUM_ACTIONS:
                raise E1Error("serialized physical key row is malformed")
            for action in np.flatnonzero(masks[user]).tolist():
                raw = row[int(action)]
                if raw is None:
                    continue
                if not isinstance(raw, list) or len(raw) != 2 or any(type(item) is not int for item in raw):
                    raise E1Error("serialized physical key is malformed")
                key = (raw[0], raw[1])
                if key in mapping:
                    raise E1Error("serialized physical key aliases within a user")
                mapping.add(key)
            common = mapping if common is None else common.intersection(mapping)
        assert common is not None
        common.discard(origin)
        expected.extend((origin, destination, users) for destination in sorted(common))
    return expected


def _verify_metrics(profile: f1.PhysicalProfile, value: object) -> None:
    if value != _profile_metrics(profile):
        raise E1Error("serialized bits/energy/service metrics disagree with profile")


def verify_step_payload(step: Mapping[str, object]) -> dict[str, object]:
    if type(step.get("step_index")) is not int or step["step_index"] not in CANONICAL_STEP_INDICES:
        raise E1Error("serialized step index is invalid")
    _digest(step.get("state_sha256"), field="state_sha256")
    base = f1.profile_from_payload(step.get("reference_profile"))
    if base.users != USERS:
        raise E1Error("BASE profile has the wrong user count")
    _verify_metrics(base, step.get("reference_metrics"))
    try:
        # The imported F1 reader recomputes F0 and proves exact unilateral
        # mask/tie/NOOP/physical-key coverage from this shared tape surface.
        f1.target_surfaces_from_step(step)
    except f1.F1Error as error:
        raise E1Error(f"unilateral tape verification failed: {error}") from error
    reference = np.asarray(step.get("reference_actions"))
    masks = np.asarray(step.get("action_masks"))
    if reference.dtype.kind not in "iu" or reference.shape != (USERS,):
        raise E1Error("serialized BASE actions are malformed")
    joint = step.get("joint_witness_catalog")
    if not isinstance(joint, list):
        raise E1Error("joint witness catalog must be a list")
    expected = _expected_joint_keys(step, base)
    observed: list[tuple[tuple[int, int], tuple[int, int], tuple[int, ...]]] = []
    key_table = step["action_physical_keys"]
    for row in joint:
        if not isinstance(row, Mapping):
            raise E1Error("joint witness row is malformed")
        raw_origin = row.get("origin_physical_key")
        raw_destination = row.get("destination_physical_key")
        raw_users = row.get("origin_users")
        if (
            not isinstance(raw_origin, list) or len(raw_origin) != 2
            or not isinstance(raw_destination, list) or len(raw_destination) != 2
            or not isinstance(raw_users, list)
            or any(type(value) is not int for value in (*raw_origin, *raw_destination, *raw_users))
        ):
            raise E1Error("joint witness identities are malformed")
        origin = (raw_origin[0], raw_origin[1])
        destination = (raw_destination[0], raw_destination[1])
        users = tuple(raw_users)
        observed.append((origin, destination, users))
        expected_id = (
            f"{JOINT_PROFILE_PREFIX}:{origin[0]}:{origin[1]}"
            f"->{destination[0]}:{destination[1]}"
        )
        if row.get("profile_id") != expected_id:
            raise E1Error("joint witness profile ID drifted")
        actions = np.asarray(row.get("candidate_joint_actions"))
        if actions.dtype.kind not in "iu" or actions.shape != reference.shape:
            raise E1Error("joint witness action vector is malformed")
        changed = tuple(np.flatnonzero(actions != reference).tolist())
        if changed != users:
            raise E1Error("joint witness must change exactly all origin users")
        for user in users:
            action = int(actions[user])
            if not 0 <= action < f1.NUM_ACTIONS or not bool(masks[user, action]):
                raise E1Error("joint witness selected an illegal destination")
            if key_table[user][action] != list(destination):
                raise E1Error("joint witness destination is not common by physical key")
            if not bool(base.served[user]) or (
                int(base.serving_satellite[user]), int(base.serving_cell[user])
            ) != origin:
                raise E1Error("joint witness origin group disagrees with BASE service")
        profile = f1.profile_from_payload(row.get("profile"))
        _verify_metrics(profile, row.get("metrics"))
        if row.get("f0_conservation") != _conservation(profile):
            raise E1Error("joint witness F0 conservation receipt disagrees")
    if observed != expected:
        raise E1Error("joint witness catalog is not exact and exhaustive")
    return {"base": base, "unilateral_count": len(step["unilateral_candidates"]), "joint_count": len(joint)}


def build_unit_tape_payload(
    *, key: UnitKey, steps: Sequence[Mapping[str, object]],
    q1_parameter_sha256: str, q2_parameter_sha256: str,
    preflight_manifest_sha256: str,
) -> dict[str, object]:
    key.verify()
    return {
        "schema": UNIT_TAPE_SCHEMA,
        "status": "COMPLETE_IMMUTABLE_TAPE",
        "claim_ceiling": CLAIM_CEILING,
        "unit": key.as_dict(),
        "panel_bindings": panel_bindings(),
        "lineage_authority": f2.lineage_authority_bindings()[LINEAGES.index(key.lineage)],
        "formula_digests": formula_digests(),
        "preflight_manifest_sha256": _digest(preflight_manifest_sha256, field="preflight sha256"),
        "q1_parameter_sha256": _digest(q1_parameter_sha256, field="q1 sha256"),
        "q2_parameter_sha256": _digest(q2_parameter_sha256, field="q2 sha256"),
        "steps": [dict(step) for step in steps],
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }


def verify_unit_tape(tape: Mapping[str, object], *, key: UnitKey) -> dict[str, int]:
    key.verify()
    if tape.get("schema") != UNIT_TAPE_SCHEMA or tape.get("status") != "COMPLETE_IMMUTABLE_TAPE":
        raise E1Error("unit tape schema/status drifted")
    if (
        tape.get("claim_ceiling") != CLAIM_CEILING
        or tape.get("unit") != key.as_dict()
        or tape.get("panel_bindings") != panel_bindings()
        or tape.get("lineage_authority") != f2.lineage_authority_bindings()[LINEAGES.index(key.lineage)]
        or tape.get("formula_digests") != formula_digests()
        or any(tape.get(field) is not False for field in (
            "test_split_opened", "episode_training", "learner_update", "efficacy_claim"
        ))
    ):
        raise E1Error("unit tape binding or claim boundary drifted")
    for field in ("preflight_manifest_sha256", "q1_parameter_sha256", "q2_parameter_sha256"):
        _digest(tape.get(field), field=field)
    steps = tape.get("steps")
    if (
        not isinstance(steps, list) or len(steps) != STEP_COUNT
        or [row.get("step_index") for row in steps if isinstance(row, Mapping)] != list(CANONICAL_STEP_INDICES)
    ):
        raise E1Error("unit tape must contain exactly canonical steps 0..9")
    unilateral = 0
    joint = 0
    for step in steps:
        if not isinstance(step, Mapping):
            raise E1Error("unit tape step is malformed")
        counts = verify_step_payload(step)
        unilateral += int(counts["unilateral_count"])
        joint += int(counts["joint_count"])
    return {"anchors": len(steps), "unilateral_profiles": unilateral, "joint_profiles": joint}


def _write_once(path: Path, payload: Mapping[str, object]) -> str:
    try:
        return f1._write_once(path, payload)
    except f1.F1Error as error:
        raise E1Error(str(error)) from error


def _unit_dir(output: Path, key: UnitKey) -> Path:
    return Path(output) / "units" / key.slug


def _unit_receipt(tape: Mapping[str, object], *, key: UnitKey, tape_sha256: str) -> dict[str, object]:
    counts = verify_unit_tape(tape, key=key)
    return {
        "schema": UNIT_RECEIPT_SCHEMA,
        "status": "COMPLETE",
        "outcome": "E1_UNIT_COMPLETE",
        "claim_ceiling": CLAIM_CEILING,
        "unit": key.as_dict(),
        "panel_bindings": panel_bindings(),
        "lineage_authority": tape["lineage_authority"],
        "formula_digests": formula_digests(),
        "preflight_manifest_sha256": tape["preflight_manifest_sha256"],
        "tape_sha256": _digest(tape_sha256, field="tape sha256"),
        "counts": counts,
        "integrity": True,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }


def invalid_unit_receipt(*, key: UnitKey, preflight_sha256: str, error: BaseException) -> dict[str, object]:
    return {
        "schema": UNIT_RECEIPT_SCHEMA,
        "status": "INVALID_RUN",
        "outcome": "INVALID_RUN",
        "claim_ceiling": CLAIM_CEILING,
        "unit": key.as_dict(),
        "panel_bindings": panel_bindings(),
        "lineage_authority": f2.lineage_authority_bindings()[LINEAGES.index(key.lineage)],
        "formula_digests": formula_digests(),
        "preflight_manifest_sha256": _digest(preflight_sha256, field="preflight sha256"),
        "tape_sha256": None,
        "counts": None,
        "integrity": False,
        "error_type": type(error).__name__,
        "error_sha256": hashlib.sha256(str(error).encode("utf-8")).hexdigest(),
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }


def write_unit_bundle(output: Path, *, key: UnitKey, tape: Mapping[str, object]) -> tuple[Path, Path, Path]:
    verify_unit_tape(tape, key=key)
    root = Path(output)
    units_root = root / "units"
    if root.is_symlink() or units_root.is_symlink():
        raise E1Error("output/units directory must not be a symlink")
    units_root.mkdir(parents=True, exist_ok=True)
    final = _unit_dir(root, key)
    if final.exists() or final.is_symlink():
        raise E1Error(f"refusing to overwrite write-once unit {key.slug}")
    stage = Path(tempfile.mkdtemp(prefix=f".stage-{key.slug}-", dir=units_root))
    tape_path = stage / DEFAULT_TAPE_NAME
    manifest_path = stage / DEFAULT_TAPE_MANIFEST_NAME
    receipt_path = stage / DEFAULT_UNIT_RECEIPT_NAME
    tape_sha = _write_once(tape_path, tape)
    manifest = {
        "schema": UNIT_TAPE_MANIFEST_SCHEMA,
        "status": "COMPLETE_IMMUTABLE_TAPE",
        "claim_ceiling": CLAIM_CEILING,
        "unit": key.as_dict(),
        "tape": {"path": DEFAULT_TAPE_NAME, "sha256": tape_sha, "bytes": tape_path.stat().st_size, "mode": "0444"},
        "formula_digests": formula_digests(),
        "preflight_manifest_sha256": tape["preflight_manifest_sha256"],
    }
    _write_once(manifest_path, manifest)
    _write_once(receipt_path, _unit_receipt(tape, key=key, tape_sha256=tape_sha))
    os.rename(stage, final)
    return final / DEFAULT_TAPE_NAME, final / DEFAULT_TAPE_MANIFEST_NAME, final / DEFAULT_UNIT_RECEIPT_NAME


def _write_invalid_unit(output: Path, *, key: UnitKey, preflight_sha256: str, error: BaseException) -> Path:
    units_root = Path(output) / "units"
    units_root.mkdir(parents=True, exist_ok=True)
    final = _unit_dir(output, key)
    if final.exists() or final.is_symlink():
        raise E1Error(f"refusing to overwrite write-once unit {key.slug}")
    final.mkdir()
    receipt = final / DEFAULT_UNIT_RECEIPT_NAME
    _write_once(receipt, invalid_unit_receipt(key=key, preflight_sha256=preflight_sha256, error=error))
    final.chmod(0o555)
    return receipt


def authenticate_unit_bundle(output: Path, *, key: UnitKey, preflight_sha256: str) -> tuple[dict[str, Any], str, dict[str, Any]]:
    root = _unit_dir(output, key)
    receipt_path = root / DEFAULT_UNIT_RECEIPT_NAME
    receipt = _load_json(receipt_path, field=f"unit {key.slug} receipt")
    if receipt_path.stat().st_mode & 0o222:
        raise E1Error(f"unit {key.slug} receipt remains writable")
    if receipt.get("status") == "INVALID_RUN":
        raise E1Error(f"unit {key.slug} is sealed INVALID_RUN")
    tape_path = root / DEFAULT_TAPE_NAME
    manifest_path = root / DEFAULT_TAPE_MANIFEST_NAME
    tape = _load_json(tape_path, field=f"unit {key.slug} tape")
    manifest = _load_json(manifest_path, field=f"unit {key.slug} manifest")
    if any(path.stat().st_mode & 0o222 for path in (tape_path, manifest_path)):
        raise E1Error(f"unit {key.slug} tape bundle remains writable")
    tape_sha = file_sha256(tape_path)
    expected_manifest = {
        "schema": UNIT_TAPE_MANIFEST_SCHEMA,
        "status": "COMPLETE_IMMUTABLE_TAPE",
        "claim_ceiling": CLAIM_CEILING,
        "unit": key.as_dict(),
        "tape": {"path": DEFAULT_TAPE_NAME, "sha256": tape_sha, "bytes": tape_path.stat().st_size, "mode": "0444"},
        "formula_digests": formula_digests(),
        "preflight_manifest_sha256": preflight_sha256,
    }
    if manifest != expected_manifest or tape.get("preflight_manifest_sha256") != preflight_sha256:
        raise E1Error(f"unit {key.slug} manifest/provenance disagrees")
    expected_receipt = _unit_receipt(tape, key=key, tape_sha256=tape_sha)
    if receipt != expected_receipt:
        raise E1Error(f"unit {key.slug} receipt disagrees with its tape")
    return receipt, file_sha256(receipt_path), tape


def _generate_unit_tape(*, key: UnitKey, tle_root: Path, preflight_sha256: str) -> dict[str, object]:
    """Generate one unit by the same in-process environment path as F1/F2."""

    key.verify()
    physical, server = f1._runtime_modules()
    from mcrl.runtime.prereg import read_prereg
    from mcrl.runtime.training_pipeline import _evaluation_rngs

    record = read_prereg(f1.PREREG_PATH)
    if record.digest != f1.PREREG_RECORD_DIGEST:
        raise E1Error("TRAIN PREREG record digest changed")
    frozen = f2._load_frozen_heads(key.lineage)
    q1_before = physical._parameter_sha256(frozen.q1)
    q2_before = physical._parameter_sha256(frozen.q2)
    field = KeyedFadingField.from_components(FIELD_COMPONENT, key.world)
    with tempfile.TemporaryDirectory(prefix=f"mcrl-v023-c3-e1-{key.slug}-tle-") as temporary:
        archive = server._freeze_archive(record, Path(tle_root), Path(temporary) / "frozen", physical)
        environment = server._make_environment(archive)
        step_env = environment.environment
        if getattr(step_env, "_started", False):
            raise E1Error("environment started before keyed field binding")
        step_env._fading_field = field
        rngs = tuple(_evaluation_rngs(key.world))
        if len(rngs) < 2:
            raise E1Error("canonical RNG factory lacks environment/mobility streams")
        _states, _masks, observation = environment.reset(rngs[0], rngs[1])
        interval_s = float(step_env.driver.config.ephemeris.time_step_s)
        if not math.isfinite(interval_s) or interval_s <= 0.0:
            raise E1Error("canonical decision interval is invalid")
        steps = []
        for step_index in CANONICAL_STEP_INDICES:
            if int(observation.step_index) != step_index:
                raise E1Error("canonical replay reached the wrong step")
            native, _q12, reference = f1._q12_surface(physical, frozen, step_env, observation)
            masks = np.asarray(native.action_masks, dtype=np.bool_)
            reference_evaluation = step_env.evaluate_actions(reference, rngs[0])
            reference_profile, reference_link_power = f1.profile_from_evaluation(
                reference_evaluation, interval_s=interval_s
            )
            unilateral_rows = []
            for skeleton in f1.enumerate_unilateral_candidates(observation, reference):
                actions = np.asarray(skeleton["candidate_joint_actions"], dtype=np.int64)
                evaluation = step_env.evaluate_actions(actions, rngs[0])
                profile, link_power = f1.profile_from_evaluation(evaluation, interval_s=interval_s)
                unilateral_rows.append({
                    **skeleton,
                    "profile_id": f"{UNILATERAL_PROFILE_PREFIX}:{skeleton['focal_user']}:{skeleton['candidate_action']}",
                    "profile": profile,
                    "link_power_w": link_power,
                    "metrics": _profile_metrics(profile),
                })
            joint_rows = build_joint_witness_catalog(JointWitnessAnchor(
                observation=observation,
                reference_actions=np.asarray(reference, dtype=np.int64),
                reference_profile=reference_profile,
                step_env=step_env,
                rng=rngs[0],
                interval_s=interval_s,
            ))
            step_payload = build_step_payload(
                step_index=step_index,
                reference_actions=reference,
                action_masks=masks,
                reference_profile=reference_profile,
                reference_link_power_w=reference_link_power,
                unilateral_candidates=unilateral_rows,
                joint_catalog=joint_rows,
                state_sha256=native.state_sha256,
                action_physical_key_table=f1.action_physical_keys(observation),
            )
            verify_step_payload(step_payload)
            environment.step(reference, rngs[0])
            committed = environment.last_outcome
            committed_profile, committed_link_power = f1.profile_from_evaluation(committed, interval_s=interval_s)
            if f1.profile_to_payload(committed_profile, link_power_w=committed_link_power) != step_payload["reference_profile"]:
                raise E1Error("BASE counterfactual disagrees with committed reference step")
            if step_index < CANONICAL_STEP_INDICES[-1]:
                if bool(committed.done):
                    raise E1Error("canonical episode terminated before step 9")
                observation = committed.observation
            steps.append(step_payload)
    if physical._parameter_sha256(frozen.q1) != q1_before or physical._parameter_sha256(frozen.q2) != q2_before:
        raise E1Error("frozen Q1/Q2 parameters changed during E1 inference")
    tape = build_unit_tape_payload(
        key=key, steps=steps, q1_parameter_sha256=q1_before,
        q2_parameter_sha256=q2_before, preflight_manifest_sha256=preflight_sha256,
    )
    verify_unit_tape(tape, key=key)
    return tape


def execute_unit(
    *, key: UnitKey, output: Path, tle_root: Path, preflight_sha256: str,
    generator: Callable[..., dict[str, object]] = _generate_unit_tape,
) -> tuple[Path, bool, bool]:
    final = _unit_dir(output, key)
    if final.exists() or final.is_symlink():
        receipt = _load_json(final / DEFAULT_UNIT_RECEIPT_NAME, field="existing unit receipt")
        if receipt.get("status") == "INVALID_RUN":
            return final / DEFAULT_UNIT_RECEIPT_NAME, True, False
        authenticate_unit_bundle(output, key=key, preflight_sha256=preflight_sha256)
        return final / DEFAULT_UNIT_RECEIPT_NAME, True, True
    try:
        tape = generator(key=key, tle_root=Path(tle_root), preflight_sha256=preflight_sha256)
        _tape, _manifest, receipt = write_unit_bundle(output, key=key, tape=tape)
        return receipt, False, True
    except Exception as error:
        receipt = _write_invalid_unit(
            output, key=key, preflight_sha256=preflight_sha256, error=error
        )
        return receipt, False, False


def _anchor_panels(tapes: Sequence[Mapping[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    unilateral_panel = []
    joint_panel = []
    for tape in tapes:
        unit = tape["unit"]
        assert isinstance(unit, Mapping)
        for step in tape["steps"]:
            assert isinstance(step, Mapping)
            anchor_id = f"{unit['world']}:{unit['lineage']}:{step['step_index']}"
            base_profile = f1.profile_from_payload(step["reference_profile"])
            base = _solver_metrics(BASE_PROFILE_ID, base_profile)
            unilateral = []
            for row in step["unilateral_candidates"]:
                profile = f1.profile_from_payload(row["profile"])
                unilateral.append(_solver_metrics(str(row["profile_id"]), profile))
            joint = []
            for row in step["joint_witness_catalog"]:
                profile = f1.profile_from_payload(row["profile"])
                joint.append(_solver_metrics(str(row["profile_id"]), profile))
            unilateral_panel.append({"anchor_id": anchor_id, "base": base, "unilateral_profiles": unilateral})
            joint_panel.append({"anchor_id": anchor_id, "base": base, "joint_profiles": joint})
    return unilateral_panel, joint_panel


def build_terminal_receipt(
    *, receipts: Sequence[Mapping[str, object]], receipt_digests: Sequence[tuple[UnitKey, str]],
    tapes: Sequence[Mapping[str, object]], preflight_sha256: str,
) -> dict[str, object]:
    if len(receipts) != len(ALL_UNITS) or len(tapes) != len(ALL_UNITS):
        raise E1Error("terminal receipt requires exactly twelve complete units")
    if tuple(key for key, _digest_value in receipt_digests) != ALL_UNITS:
        raise E1Error("terminal unit order/coverage drifted")
    unilateral_panel, joint_panel = _anchor_panels(tapes)
    u1 = estimands.solve_u1(unilateral_panel)
    j1 = estimands.solve_j1(joint_panel)
    unilateral_outcome = UNILATERAL_OUTCOMES[0] if u1["U1"] > u1["eta_BASE"] else UNILATERAL_OUTCOMES[1]
    joint_outcome = JOINT_OUTCOMES[0] if j1["J1"] > j1["eta_BASE"] else JOINT_OUTCOMES[1]
    if u1["eta_BASE_hex"] != j1["eta_BASE_hex"]:
        raise E1Error("U1 and J1 BASE denominators disagree")
    return {
        "schema": TERMINAL_RECEIPT_SCHEMA,
        "status": "COMPLETE",
        "outcome": {"unilateral": unilateral_outcome, "joint": joint_outcome},
        "claim_ceiling": CLAIM_CEILING,
        "panel_bindings": panel_bindings(),
        "lineage_authorities": f2.lineage_authority_bindings(),
        "formula_digests": formula_digests(),
        "preflight_manifest_sha256": _digest(preflight_sha256, field="preflight sha256"),
        "unit_receipts": [
            {"unit": key.as_dict(), "path": f"units/{key.slug}/{DEFAULT_UNIT_RECEIPT_NAME}", "sha256": digest}
            for key, digest in receipt_digests
        ],
        "U1": u1,
        "J1": j1,
        "integrity": True,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }


def invalid_terminal_receipt(*, preflight_sha256: str, error: BaseException) -> dict[str, object]:
    return {
        "schema": TERMINAL_RECEIPT_SCHEMA,
        "status": "INVALID_RUN",
        "outcome": "INVALID_RUN",
        "claim_ceiling": CLAIM_CEILING,
        "panel_bindings": panel_bindings(),
        "lineage_authorities": f2.lineage_authority_bindings(),
        "formula_digests": formula_digests(),
        "preflight_manifest_sha256": _digest(preflight_sha256, field="preflight sha256"),
        "unit_receipts": None,
        "U1": None,
        "J1": None,
        "integrity": False,
        "error_type": type(error).__name__,
        "error_sha256": hashlib.sha256(str(error).encode("utf-8")).hexdigest(),
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }


def execute_merge(*, output: Path, preflight_sha256: str) -> tuple[Path, bool, bool]:
    root = Path(output)
    if root.is_symlink():
        raise E1Error("output directory must not be a symlink")
    root.mkdir(parents=True, exist_ok=True)
    terminal = root / DEFAULT_TERMINAL_RECEIPT_NAME
    if terminal.exists() or terminal.is_symlink():
        receipt = _load_json(terminal, field="existing terminal receipt")
        if terminal.stat().st_mode & 0o222:
            raise E1Error("terminal receipt remains writable")
        return terminal, True, receipt.get("status") == "COMPLETE"
    try:
        receipts = []
        digests = []
        tapes = []
        for key in ALL_UNITS:
            receipt, digest, tape = authenticate_unit_bundle(
                root, key=key, preflight_sha256=preflight_sha256
            )
            receipts.append(receipt)
            digests.append((key, digest))
            tapes.append(tape)
        payload = build_terminal_receipt(
            receipts=receipts, receipt_digests=digests, tapes=tapes,
            preflight_sha256=preflight_sha256,
        )
        valid = True
    except Exception as error:
        payload = invalid_terminal_receipt(preflight_sha256=preflight_sha256, error=error)
        valid = False
    _write_once(terminal, payload)
    return terminal, False, valid


def run(args: argparse.Namespace) -> dict[str, object]:
    _manifest, preflight_sha = validate_preflight_manifest(Path(args.preflight_manifest))
    if args.dry_run:
        result: dict[str, object] = {
            "preflight": Path(args.preflight_manifest),
            "worlds": WORLDS,
        }
        if args.launch_authority is not None:
            result["authority"] = validate_launch_authority(
                Path(args.launch_authority), preflight_path=Path(args.preflight_manifest),
                preflight_sha256=preflight_sha,
            )
        return result
    if args.launch_authority is None or args.output is None:
        raise E1Error("E1 execution requires --launch-authority and --output")
    validate_launch_authority(
        Path(args.launch_authority), preflight_path=Path(args.preflight_manifest),
        preflight_sha256=preflight_sha,
    )
    if args.unit is not None:
        if args.tle_root is None:
            raise E1Error("--unit requires --tle-root")
        receipt, skipped, valid = execute_unit(
            key=UnitKey.parse(args.unit), output=Path(args.output),
            tle_root=Path(args.tle_root), preflight_sha256=preflight_sha,
        )
        return {"receipt": receipt, "skipped": skipped, "valid": valid, "mode": "unit"}
    terminal, skipped, valid = execute_merge(
        output=Path(args.output), preflight_sha256=preflight_sha
    )
    return {"receipt": terminal, "skipped": skipped, "valid": valid, "mode": "merge"}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--unit", help="run one exact WORLD:LINEAGE shard")
    mode.add_argument("--merge", action="store_true", help="authenticate 12 shards and solve U1/J1")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--preflight-manifest", type=Path, default=DEFAULT_PREFLIGHT)
    parser.add_argument("--launch-authority", type=Path)
    parser.add_argument("--tle-root", type=Path)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.dry_run and args.unit is None and not args.merge:
        print("E1_ERROR: execution requires exactly one of --unit or --merge", file=sys.stderr)
        return 2
    try:
        result = run(args)
    except Exception as error:
        print(f"E1_ERROR: {error}", file=sys.stderr)
        traceback.print_exception(error, file=sys.stderr)
        return 2
    if args.dry_run:
        print("E1_WORLD_SEEDS " + " ".join(str(seed) for seed in result["worlds"]))
        print(f"E1_DRY_RUN_PASS preflight={result['preflight']}")
        return 0
    state = "SKIPPED_COMPLETE" if result["skipped"] else "WRITTEN"
    print(f"E1_{str(result['mode']).upper()}_{state} receipt={result['receipt']}")
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
