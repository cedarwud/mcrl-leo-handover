#!/usr/bin/env python3
"""C3 existence screen E1: immutable world-lineage units and exact merge.

Imports and ``--dry-run`` are simulator-inert.  Unit execution reuses the F1
BASE/unilateral machinery and the F2 world-by-lineage/runtime conventions.
It adds only physically evaluated complete joint witness profiles.  Merge
authenticates all twelve units and solves U1 and J1 without running physics.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
from fractions import Fraction
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import shutil
import signal
import sys
import tempfile
import time
import traceback
from typing import Any, Callable, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
F0_DIR = REPO / ".scratch" / "multi-catfish-v023-c3-contingency"
F1_DIR = REPO / ".scratch" / "multi-catfish-v023-c3-contingency-f1"
F2_DIR = REPO / ".scratch" / "multi-catfish-v023-c3-contingency-f2"
STAGEC_PLAN_DIR = REPO / ".scratch" / "multi-catfish-v023-c1c2-successor-physical-evaluation"
STAGEC_LAUNCH_DIR = REPO / ".scratch" / "multi-catfish-v023-c1c2-successor-stagec-launch"
for _path in (HERE, F0_DIR, F1_DIR, F2_DIR, STAGEC_PLAN_DIR, STAGEC_LAUNCH_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import e1_estimands as estimands  # noqa: E402
import run_v023_c3_contingency_f1 as f1  # noqa: E402
import run_v023_c3_contingency_f2 as f2  # noqa: E402
import build_v023_c1c2_successor_world_plan as stagec_plan  # noqa: E402
import stagec_common  # noqa: E402
from c3_contingency_f0 import compute_cost_shares  # noqa: E402
from mcrl.env.constants import DECISION_STEP_S  # noqa: E402
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_v04_c3_opening_source import (  # noqa: E402
    _assert_evaluation_neutral,
    _evaluation_snapshot,
)


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
INTERVAL_S = DECISION_STEP_S
DISALLOWED_HISTORICAL_WORLDS = frozenset(f2.WORLDS)

CONTRACT_FILENAME = "V023-C3-EXISTENCE-TEST-CONTRACT-E1-2026-09-08.md"
DEFAULT_PREFLIGHT = HERE / "E1-PREFLIGHT-MANIFEST.json"
DEFAULT_TAPE_NAME = "e1-physical-tape.json"
DEFAULT_TAPE_MANIFEST_NAME = "e1-physical-tape.manifest.json"
DEFAULT_UNIT_RECEIPT_NAME = "receipt.json"
DEFAULT_TERMINAL_RECEIPT_NAME = "terminal-receipt.json"
DEFAULT_GLOBAL_INVALIDATION_NAME = "GLOBAL-INVALIDATION.json"
DEFAULT_BUDGET_LEDGER_NAME = "budget-ledger.json"
DEFAULT_BUDGET_WORKER_SECONDS = 57_600.0
DEFAULT_BUDGET_RESERVATION_WORKER_SECONDS = DEFAULT_BUDGET_WORKER_SECONDS / 12.0
CANONICAL_TLE_ROOT = Path("/home/sat/mcrl-runtime/tle-frozen-20260820")
CANONICAL_INTERPRETER = Path("/home/sat/mcrl-leo-handover/.venv/bin/python")

UNILATERAL_PROFILE_PREFIX = "U"
JOINT_PROFILE_PREFIX = "J"
BASE_PROFILE_ID = estimands.BASE_PROFILE_ID
UNILATERAL_OUTCOMES = ("E1_UNILATERAL_HEADROOM", "E1_UNILATERAL_CLOSED")
JOINT_OUTCOMES = ("E1_JOINT_HEADROOM", "E1_JOINT_CLOSED")


class E1Error(RuntimeError):
    """An E1 binding, tape, physical catalog, or receipt failed closed."""


class E1Incomplete(E1Error):
    """E1 stopped for interruption or a declared resource limit."""


class E1MergeWaiting(E1Incomplete):
    """Merge cannot begin until every immutable unit is present."""

    def __init__(self, missing: int) -> None:
        self.missing = missing
        super().__init__(f"{missing} units missing")


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
        "lambda_bits_per_j_hex": f1.LAMBDA_BITS_PER_J.hex(),
        "kappa_bits_hex": f1.KAPPA_BITS.hex(),
        "q1_q2_plus_z_over_kappa_used": False,
        "stage_c_world_plan_exclusion_sha256": stagec_common.PLAN_SHA256,
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
    paths: list[tuple[str, Path]] = [
        ("e1_runner", HERE / "run_v023_c3_existence_e1.py"),
        ("e1_estimands", HERE / "e1_estimands.py"),
        ("e1_preflight_builder", HERE / "build_e1_preflight_manifest.py"),
        ("e1_launch_authority_builder", HERE / "build_e1_launch_authority.py"),
        ("e1_estimand_tests", HERE / "test_e1_estimands.py"),
        ("e1_runner_tests", HERE / "test_run_v023_c3_existence_e1.py"),
        ("e1_readme", HERE / "README.md"),
        ("e1_changelog", HERE / "CHANGELOG.md"),
        ("f1_tape_machinery_import", F1_DIR / "run_v023_c3_contingency_f1.py"),
        ("f2_unit_merge_conventions_import", F2_DIR / "run_v023_c3_contingency_f2.py"),
        ("f0_conservation_import", F0_DIR / "c3_contingency_f0.py"),
        ("joint_profile_evaluator", REPO / "src/mcrl/env/step.py"),
        ("joint_profile_physics", REPO / "src/mcrl/env/link_budget.py"),
        ("evaluation_neutrality", REPO / "src/mcrl/runtime/ee_axis_v04_c3_opening_source.py"),
        ("canonical_interval", REPO / "src/mcrl/env/constants.py"),
        ("stage_c_world_plan_builder", STAGEC_PLAN_DIR / "build_v023_c1c2_successor_world_plan.py"),
        ("stage_c_plan_authority", STAGEC_LAUNCH_DIR / "stagec_common.py"),
        ("rng_construction", REPO / "src/mcrl/runtime/training_pipeline.py"),
        ("keyed_field_construction", REPO / "src/mcrl/env/keyed_fading.py"),
        ("rng_state_authentication", REPO / "src/mcrl/env/observation_provenance.py"),
    ]
    seen = {path.resolve() for _role, path in paths}
    for row in f2.expected_code_bindings():
        path = REPO / row["path"]
        if path.resolve() not in seen:
            paths.append((f"f2_import_{row['role']}", path))
            seen.add(path.resolve())
    return [
        {"role": role, "path": _repo_relative(path), "sha256": file_sha256(path)}
        for role, path in paths
    ]


def sealed_contract_binding() -> dict[str, str]:
    """Authenticate the controller-owned contract without modifying it."""

    contract = HERE / CONTRACT_FILENAME
    sidecar = Path(f"{contract}.sha256")
    message = "E1 contract is not sealed read-only with matching .sha256 sidecar"
    if (
        contract.is_symlink()
        or not contract.is_file()
        or contract.stat().st_mode & 0o222
        or sidecar.is_symlink()
        or not sidecar.is_file()
        or sidecar.stat().st_mode & 0o222
    ):
        raise E1Error(message)
    digest = file_sha256(contract)
    if sidecar.read_text(encoding="ascii").split() != [digest, contract.name]:
        raise E1Error(message)
    return {"path": str(contract.resolve()), "sha256": digest}


def prereg_tle_bindings() -> dict[str, object]:
    """Rebuild the imported PREREG/TLE manifest at the one permitted root."""

    from mcrl.env.tle import TleArchive
    from mcrl.runtime.prereg import read_prereg
    from mcrl.runtime.training_pipeline import assert_ephemeris_matches_record

    if file_sha256(f1.PREREG_PATH) != f1.PREREG_SHA256:
        raise E1Error("TRAIN PREREG bytes changed")
    record = read_prereg(f1.PREREG_PATH)
    if record.digest != f1.PREREG_RECORD_DIGEST:
        raise E1Error("TRAIN PREREG semantic digest changed")
    if CANONICAL_TLE_ROOT.is_symlink() or not CANONICAL_TLE_ROOT.is_dir():
        raise E1Error("canonical TLE root is missing or symlinked")
    try:
        manifest = assert_ephemeris_matches_record(
            record, archive=TleArchive(CANONICAL_TLE_ROOT)
        )
    except Exception as error:
        raise E1Error("canonical TLE archive disagrees with imported PREREG machinery") from error
    return {
        "preregistration": {
            "path": _repo_relative(f1.PREREG_PATH),
            "sha256": f1.PREREG_SHA256,
            "record_digest": f1.PREREG_RECORD_DIGEST,
        },
        "tle_archive": {
            "root": str(CANONICAL_TLE_ROOT),
            "manifest_sha256": canonical_sha256(manifest),
            "file_set_sha256": manifest["file_set_sha256"],
            "file_count": len(manifest["frozen_files"]),
        },
    }


def _assert_server_interpreter() -> None:
    if Path(sys.executable).resolve() != CANONICAL_INTERPRETER.resolve():
        raise E1Error(f"E1 requires interpreter {CANONICAL_INTERPRETER}")


def _cpu_model() -> str:
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        for line in cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines():
            name, separator, value = line.partition(":")
            if separator and name.strip() in {"model name", "Hardware"} and value.strip():
                return value.strip()
    return platform.processor() or platform.machine()


def process_bindings() -> dict[str, object]:
    _assert_server_interpreter()
    import torch

    venv_root = Path(sys.prefix).resolve()
    pyvenv = venv_root / "pyvenv.cfg"
    if not pyvenv.is_file() or pyvenv.is_symlink():
        raise E1Error("selected virtual environment lacks a regular pyvenv.cfg")
    thread_names = (
        "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    )
    sgp4_version = importlib.metadata.version("sgp4")
    core_count = os.cpu_count()
    if core_count is None or core_count <= 0 or not _cpu_model():
        raise E1Error("hardware CPU identity is unavailable")
    thread_environment = {name: os.environ.get(name) for name in thread_names}
    torch_threads = {
        "intraop": torch.get_num_threads(),
        "interop": torch.get_num_interop_threads(),
    }
    return {
        "checkout_root": str(REPO.resolve()),
        "interpreter": str(Path(sys.executable).resolve()),
        "python_version": sys.version,
        "numpy_version": np.__version__,
        "torch_version": torch.__version__,
        "sgp4_version": sgp4_version,
        "third_party_versions": {
            "numpy": np.__version__, "torch": torch.__version__, "sgp4": sgp4_version,
        },
        "hardware": {
            "cpu_model": _cpu_model(),
            "core_count": core_count,
            "logical_core_count": core_count,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "kernel": platform.release(),
        },
        "effective_threads": {
            "environment": thread_environment,
            "torch_num_threads": torch_threads["intraop"],
            "torch_num_interop_threads": torch_threads["interop"],
        },
        "thread_environment": thread_environment,
        "torch_threads": torch_threads,
        "virtual_environment": {
            "root": str(venv_root),
            "pyvenv_cfg_path": str(pyvenv.resolve()),
            "pyvenv_cfg_sha256": file_sha256(pyvenv),
            "sys_prefix": sys.prefix,
        },
    }


def validate_static_bindings() -> dict[str, object]:
    contract_binding = sealed_contract_binding()
    if LINEAGES != tuple(range(2026092101, 2026092104)):
        raise E1Error("lineage panel drifted")
    if CANONICAL_STEP_INDICES != tuple(range(STEP_COUNT)) or STEP_COUNT != 10:
        raise E1Error("E1 requires exactly canonical steps 0..9")
    if USERS != 100 or SPLIT != "TRAIN" or SERVICE_MARGIN != f1.SERVICE_MARGIN:
        raise E1Error("imported user/split/service binding drifted")
    if world_seeds() != WORLDS:
        raise E1Error("derived E1 world panel drifted")
    stage_c_payload = stagec_plan.build_world_plan()
    if stage_c_payload.get("plan_sha256") != stagec_common.PLAN_SHA256:
        raise E1Error("stage-C 9000-world plan authority drifted")
    stage_c_seeds = {
        int(row["world_seed"])
        for row in stage_c_payload["worlds"]
        if isinstance(row, Mapping)
    }
    if len(stage_c_seeds) != stagec_plan.EPISODES or stage_c_seeds.intersection(WORLDS):
        raise E1Error("E1 worlds collide with or cannot authenticate the stage-C plan")
    try:
        f2_static = f2.validate_static_bindings()
    except f2.F2Error as error:
        raise E1Error(f"F1/F2 reusable machinery failed authentication: {error}") from error
    return {
        "bindings": panel_bindings(),
        "contract": contract_binding,
        **prereg_tle_bindings(),
        "process_environment": process_bindings(),
        "lineage_authorities": f2.lineage_authority_bindings(),
        "reused_f2_code_files": f2.expected_code_bindings(),
        "formula_digests": formula_digests(),
        "reused_f2_preflight": f2_static["f1_preflight"],
        "world_exclusion_check": {
            "stage_c_plan_sha256": stagec_common.PLAN_SHA256,
            "stage_c_world_count": len(stage_c_seeds),
            "overlap": [],
        },
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
    _validate_digest_sidecar(target, digest=digest, label="E1 preflight")
    return payload, digest


def _validate_digest_sidecar(path: Path, *, digest: str, label: str) -> Path:
    target = Path(path)
    sidecar = target.with_suffix(".sha256")
    if (
        target.is_symlink() or not target.is_file() or target.stat().st_mode & 0o222
        or sidecar.is_symlink() or not sidecar.is_file() or sidecar.stat().st_mode & 0o222
    ):
        raise E1Error(f"{label} digest sidecar is missing or symlinked")
    if sidecar.read_text(encoding="ascii").split() != [digest, target.name]:
        raise E1Error(f"{label} digest sidecar disagrees")
    return sidecar


def _preflight_path_record(path: Path) -> str:
    resolved = Path(path).resolve()
    return _repo_relative(resolved) if resolved.is_relative_to(REPO.resolve()) else str(resolved)


def validate_launch_authority(
    path: Path, *, preflight_path: Path, preflight_sha256: str,
    output_root: Path | None = None, tle_root: Path | None = None,
    launch_arguments: Sequence[str] | None = None,
) -> dict[str, Any]:
    authority_path = Path(path)
    payload = _load_json(authority_path, field="E1 launch authority")
    _validate_digest_sidecar(
        authority_path, digest=file_sha256(authority_path), label="E1 launch authority"
    )
    expected_keys = {
        "schema", "status", "claim_ceiling", "preflight_manifest", "contract",
        "bindings", "checkout_root", "output_root", "tle_root", "preregistration",
        "tle_archive", "launch_arguments", "test_split_opened", "episode_training",
        "learner_update", "efficacy_claim",
    }
    if set(payload) != expected_keys:
        raise E1Error("launch authority keys differ from the exact E1 contract")
    contract = payload.get("contract")
    if not isinstance(contract, Mapping) or set(contract) != {"path", "sha256"}:
        raise E1Error("launch authority contract binding needs exact path/sha256 keys")
    if dict(contract) != sealed_contract_binding():
        raise E1Error("launch authority does not bind the controller-placed E1 contract")
    bound_output = payload.get("output_root")
    if not isinstance(bound_output, str) or not Path(bound_output).is_absolute():
        raise E1Error("launch authority output root must be absolute")
    if output_root is not None and (
        not Path(output_root).is_absolute()
        or str(Path(output_root)) != str(Path(bound_output))
        or Path(output_root).is_symlink()
    ):
        raise E1Error("runtime output root differs from launch authority")
    if tle_root is not None and (
        Path(tle_root) != CANONICAL_TLE_ROOT or Path(tle_root).is_symlink()
    ):
        raise E1Error("runtime TLE root differs from the canonical frozen root")
    frozen_inputs = prereg_tle_bindings()
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
        "checkout_root": str(REPO.resolve()),
        "output_root": str(Path(bound_output).resolve()),
        "tle_root": str(CANONICAL_TLE_ROOT),
        "preregistration": frozen_inputs["preregistration"],
        "tle_archive": frozen_inputs["tle_archive"],
        "launch_arguments": list(payload.get("launch_arguments", [])),
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }
    if payload != expected:
        raise E1Error("launch authority does not pin the exact E1 bindings")
    arguments = payload.get("launch_arguments")
    if (
        not isinstance(arguments, list)
        or any(not isinstance(value, str) for value in arguments)
        or launch_arguments is not None
        and list(launch_arguments) != arguments
    ):
        raise E1Error("runtime launch arguments differ from launch authority")
    return payload


def _profile_metrics(profile: f1.PhysicalProfile) -> dict[str, object]:
    if profile.users != USERS or profile.interval_s != INTERVAL_S:
        raise E1Error("every physical profile must match BASE users and canonical interval")
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
    reference_link_power_w: np.ndarray
    step_env: Any
    rng: np.random.Generator
    interval_s: float


def _evaluate_actions_neutral(step_env: Any, actions: np.ndarray, rng: np.random.Generator) -> Any:
    before = _evaluation_snapshot(step_env, rng)
    evaluation = step_env.evaluate_actions(actions, rng)
    _assert_evaluation_neutral(step_env, rng, before)
    return evaluation


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
    if base.users != USERS or base.interval_s != INTERVAL_S or anchor.interval_s != INTERVAL_S:
        raise E1Error("joint catalog BASE must have 100 users and canonical interval")
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
    base_payload = f1.profile_to_payload(
        base, link_power_w=anchor.reference_link_power_w
    )
    first_profile_by_sha = {canonical_sha256(base_payload): BASE_PROFILE_ID}
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
            evaluation = _evaluate_actions_neutral(anchor.step_env, actions, anchor.rng)
            profile, link_power = f1.profile_from_evaluation(
                evaluation, interval_s=anchor.interval_s
            )
            if profile.users != base.users or profile.interval_s != INTERVAL_S:
                raise E1Error("joint witness profile must match BASE users and interval")
            conservation = _conservation(profile)
            profile_id = (
                f"{JOINT_PROFILE_PREFIX}:{origin[0]}:{origin[1]}"
                f"->{destination[0]}:{destination[1]}"
            )
            physical_payload = f1.profile_to_payload(profile, link_power_w=link_power)
            profile_sha = canonical_sha256(physical_payload)
            alias_of = first_profile_by_sha.get(profile_sha)
            first_profile_by_sha.setdefault(profile_sha, profile_id)
            rows.append(
                {
                    "profile_id": profile_id,
                    "origin_physical_key": list(origin),
                    "destination_physical_key": list(destination),
                    "origin_users": list(users),
                    "candidate_joint_actions": [int(value) for value in actions.tolist()],
                    "profile": profile,
                    "link_power_w": link_power,
                    "physical_profile_sha256": profile_sha,
                    "alias_of_profile_id": alias_of,
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


def _encode_q12_surface(value: object) -> dict[str, object]:
    array = np.asarray(value)
    if array.dtype != np.dtype(np.float32) or array.shape != (USERS, f1.NUM_ACTIONS):
        raise E1Error("Q1+Q2 surface must have exact float32 dtype and shape (100,28)")
    if not np.all(np.isfinite(array)):
        raise E1Error("Q1+Q2 surface contains non-finite values")
    little = np.ascontiguousarray(array, dtype=np.dtype("<f4"))
    return {
        "encoding": "base16-little-endian-c-order",
        "dtype": "<f4",
        "shape": [USERS, f1.NUM_ACTIONS],
        "data_hex": little.tobytes(order="C").hex(),
    }


def _decode_q12_surface(value: object) -> np.ndarray:
    if not isinstance(value, Mapping) or set(value) != {
        "encoding", "dtype", "shape", "data_hex"
    }:
        raise E1Error("serialized Q1+Q2 surface is missing or malformed")
    if (
        value.get("encoding") != "base16-little-endian-c-order"
        or value.get("dtype") != "<f4"
        or value.get("shape") != [USERS, f1.NUM_ACTIONS]
        or not isinstance(value.get("data_hex"), str)
    ):
        raise E1Error("serialized Q1+Q2 surface dtype/shape is malformed")
    text = value["data_hex"]
    try:
        raw = bytes.fromhex(text)
    except ValueError as error:
        raise E1Error("serialized Q1+Q2 surface base16 is malformed") from error
    expected_bytes = USERS * f1.NUM_ACTIONS * np.dtype("<f4").itemsize
    if len(raw) != expected_bytes or text != raw.hex():
        raise E1Error("serialized Q1+Q2 surface byte length/canonical base16 is malformed")
    result = np.frombuffer(raw, dtype=np.dtype("<f4")).reshape(USERS, f1.NUM_ACTIONS).copy()
    if result.dtype != np.dtype(np.float32) or not np.all(np.isfinite(result)):
        raise E1Error("serialized Q1+Q2 surface values are malformed")
    return result


def _masked_first_argmax(values: object, masks: object) -> np.ndarray:
    """Direct BASE selector with NumPy ties and no residual composition."""

    surface = np.asarray(values)
    legal = np.asarray(masks)
    if surface.shape != (USERS, f1.NUM_ACTIONS) or not np.issubdtype(surface.dtype, np.floating):
        raise E1Error("BASE Q surface is malformed")
    if legal.dtype != np.bool_ or legal.shape != surface.shape:
        raise E1Error("BASE legality mask is malformed")
    if not np.all(np.isfinite(surface)):
        raise E1Error("BASE Q surface is non-finite")
    selected = np.full(USERS, f1.NO_OP_ACTION, dtype=np.int64)
    eligible = np.any(legal, axis=1)
    selected[eligible] = np.argmax(
        np.where(legal[eligible], surface[eligible], -np.inf), axis=1
    )
    return selected


def _base_argmax(q12: np.ndarray, masks: np.ndarray) -> np.ndarray:
    """Stored-Q12 BASE selector with exact float32 input authentication."""

    if q12.dtype != np.dtype(np.float32):
        raise E1Error("BASE Q1+Q2 surface is not float32")
    return _masked_first_argmax(q12, masks)


def _q12_surface_base_only(
    physical: Any, frozen: Any, step_env: Any, observation: Any
) -> tuple[Any, np.ndarray, np.ndarray]:
    """Thin BASE-only counterpart to F1's combined surface/deployment helper."""

    from mcrl.runtime.ee_axis_ops3_live import (
        build_ops3_live_surfaces,
        project_ops3_anchor,
        snapshot_ops3_anchor,
    )
    from mcrl.runtime.ee_axis_state import encode_ee_axis_state
    from mcrl.runtime.ee_axis_v014_q2_state import encode_ee_axis_v014_q2_states

    native = encode_ee_axis_state(step_env, observation)
    native.verify()
    masks = np.asarray(native.action_masks, dtype=np.bool_)
    eligible = np.any(masks, axis=1)
    q1 = f1._network_surface_allow_empty(
        physical, frozen.q1, native.state_matrix, masks, field="Q1"
    )
    q1_reference = _masked_first_argmax(q1, masks)
    anchor = snapshot_ops3_anchor(step_env, observation)
    projection = project_ops3_anchor(anchor)
    surfaces = build_ops3_live_surfaces(anchor, projection, q1_reference)
    q2 = np.zeros(masks.shape, dtype=np.float64)
    if np.any(eligible):
        q2_state = encode_ee_axis_v014_q2_states(
            tuple(surface for index, surface in enumerate(surfaces) if bool(eligible[index]))
        )
        q2_state.verify()
        if not np.array_equal(q2_state.action_masks, masks[eligible]):
            raise E1Error("Q2 carrier mask differs from native mask")
        q2[eligible] = physical._surface(
            frozen.q2, q2_state.state_matrix, q2_state.action_masks, field="Q2"
        )
    q12 = np.asarray(
        np.asarray(q1, dtype=np.float32) + np.asarray(q2, dtype=np.float32),
        dtype=np.float32,
    )
    return native, q12, _base_argmax(q12, masks)


def _validate_unilateral_catalog_only(step: Mapping[str, object], base: f1.PhysicalProfile) -> None:
    """Thin E1 validation-only wrapper around donor profile/physical identities."""

    masks = np.asarray(step.get("action_masks"))
    reference = np.asarray(step.get("reference_actions"))
    physical_keys = step.get("action_physical_keys")
    candidates = step.get("unilateral_candidates")
    if masks.dtype != np.bool_ or masks.shape != (USERS, f1.NUM_ACTIONS):
        raise E1Error("step action masks are malformed")
    if reference.dtype.kind not in "iu" or reference.shape != (USERS,):
        raise E1Error("step reference actions are malformed")
    if (
        not isinstance(physical_keys, list)
        or len(physical_keys) != USERS
        or any(not isinstance(row, list) or len(row) != f1.NUM_ACTIONS for row in physical_keys)
        or not isinstance(candidates, list)
    ):
        raise E1Error("unilateral tape physical-key/candidate surface is malformed")
    eligible = np.any(masks, axis=1)
    covered = {(user, int(reference[user])) for user in range(USERS)}
    for user, action in enumerate(reference.tolist()):
        if bool(eligible[user]):
            if not 0 <= action < f1.NUM_ACTIONS or not bool(masks[user, action]):
                raise E1Error("BASE selected an illegal action")
        elif action != f1.NO_OP_ACTION:
            raise E1Error("empty-mask user requires the NOOP BASE action")
    for row in candidates:
        if not isinstance(row, Mapping):
            raise E1Error("unilateral candidate row is malformed")
        focal = row.get("focal_user")
        action = row.get("candidate_action")
        if type(focal) is not int or type(action) is not int:
            raise E1Error("unilateral candidate indices are malformed")
        key = (focal, action)
        if (
            key in covered or not 0 <= focal < USERS or not 0 <= action < f1.NUM_ACTIONS
            or not bool(masks[focal, action])
        ):
            raise E1Error("unilateral candidate is duplicate, out of range, or illegal")
        candidate_joint = np.asarray(row.get("candidate_joint_actions"))
        if (
            candidate_joint.dtype.kind not in "iu"
            or candidate_joint.shape != reference.shape
            or np.flatnonzero(candidate_joint != reference).tolist() != [focal]
            or int(candidate_joint[focal]) != action
            or row.get("candidate_physical_key") != physical_keys[focal][action]
            or row.get("reference_physical_key") != physical_keys[focal][int(reference[focal])]
        ):
            raise E1Error("unilateral candidate physical mutation is malformed")
        profile = f1.profile_from_payload(row.get("profile"))
        if profile.users != base.users or profile.interval_s != INTERVAL_S:
            raise E1Error("unilateral profile must match BASE users and interval")
        covered.add(key)
    expected = {(user, int(reference[user])) for user in range(USERS)}
    for user in range(USERS):
        reference_key = physical_keys[user][int(reference[user])] if bool(eligible[user]) else None
        seen: set[tuple[int, int]] = set()
        for raw_action in np.flatnonzero(masks[user]).tolist():
            action = int(raw_action)
            raw_key = physical_keys[user][action]
            if raw_key is None or raw_key == reference_key:
                continue
            if not isinstance(raw_key, list) or len(raw_key) != 2 or any(type(item) is not int for item in raw_key):
                raise E1Error("unilateral physical key is malformed")
            key_tuple = (raw_key[0], raw_key[1])
            if key_tuple in seen:
                raise E1Error("two legal slots alias one unilateral physical candidate")
            seen.add(key_tuple)
            expected.add((user, action))
    if covered != expected:
        raise E1Error("unilateral tape does not cover every legal physical action exactly once")


def build_step_payload(
    *,
    step_index: int,
    q12: object,
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
        "q1_q2_float32": _encode_q12_surface(q12),
        "action_masks": [[bool(value) for value in row] for row in masks.tolist()],
        "action_physical_keys": [list(row) for row in action_physical_key_table],
        "reference_actions": [int(value) for value in actions.tolist()],
        "reference_profile": f1.profile_to_payload(
            reference_profile, link_power_w=reference_link_power_w
        ),
        "reference_metrics": _profile_metrics(reference_profile),
        "reference_f0_conservation": _conservation(reference_profile),
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
    if base.interval_s != INTERVAL_S:
        raise E1Error("physical profile interval disagrees with canonical 30.08 s")
    _verify_metrics(base, step.get("reference_metrics"))
    if step.get("reference_f0_conservation") != _conservation(base):
        raise E1Error("serialized BASE F0 conservation receipt disagrees")
    q12 = _decode_q12_surface(step.get("q1_q2_float32"))
    masks = np.asarray(step.get("action_masks"))
    reference = np.asarray(step.get("reference_actions"))
    if not np.array_equal(_base_argmax(q12, masks), reference):
        raise E1Error("BASE is not the masked first-index Q1+Q2 argmax")
    _validate_unilateral_catalog_only(step, base)
    unilateral = step.get("unilateral_candidates")
    if not isinstance(unilateral, list):
        raise E1Error("unilateral candidate tape must be a list")
    for row in unilateral:
        if not isinstance(row, Mapping):
            raise E1Error("unilateral candidate row is malformed")
        expected_id = f"{UNILATERAL_PROFILE_PREFIX}:{row.get('focal_user')}:{row.get('candidate_action')}"
        if row.get("profile_id") != expected_id:
            raise E1Error("unilateral profile ID drifted")
        unilateral_profile = f1.profile_from_payload(row.get("profile"))
        if unilateral_profile.users != USERS or unilateral_profile.interval_s != INTERVAL_S:
            raise E1Error("unilateral profile must have 100 users and canonical interval")
        _verify_metrics(unilateral_profile, row.get("metrics"))
        if row.get("f0_conservation") != _conservation(unilateral_profile):
            raise E1Error("unilateral F0 conservation receipt disagrees")
    if reference.dtype.kind not in "iu" or reference.shape != (USERS,):
        raise E1Error("serialized BASE actions are malformed")
    joint = step.get("joint_witness_catalog")
    if not isinstance(joint, list):
        raise E1Error("joint witness catalog must be a list")
    expected = _expected_joint_keys(step, base)
    observed: list[tuple[tuple[int, int], tuple[int, int], tuple[int, ...]]] = []
    key_table = step["action_physical_keys"]
    base_payload_sha = canonical_sha256(step["reference_profile"])
    first_profile_by_sha = {base_payload_sha: BASE_PROFILE_ID}
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
        if profile.users != USERS or profile.interval_s != INTERVAL_S:
            raise E1Error("joint witness profile must have 100 users and canonical interval")
        _verify_metrics(profile, row.get("metrics"))
        if row.get("f0_conservation") != _conservation(profile):
            raise E1Error("joint witness F0 conservation receipt disagrees")
        profile_sha = canonical_sha256(row.get("profile"))
        if row.get("physical_profile_sha256") != profile_sha:
            raise E1Error("joint witness physical profile digest disagrees")
        if row.get("alias_of_profile_id") != first_profile_by_sha.get(profile_sha):
            raise E1Error("joint witness alias record disagrees with exact profile bytes")
        first_profile_by_sha.setdefault(profile_sha, expected_id)
    if observed != expected:
        raise E1Error("joint witness catalog is not exact and exhaustive")
    return {"base": base, "unilateral_count": len(unilateral), "joint_count": len(joint)}


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
    target = Path(path)
    if target.exists() or target.is_symlink():
        raise E1Error(f"refusing to overwrite write-once artifact: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = canonical_bytes(payload) + b"\n"
    with target.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    target.chmod(0o444)
    # Publication succeeds only after reopening the actual immutable bytes.
    observed = target.read_bytes()
    digest = hashlib.sha256(observed).hexdigest()
    if observed != encoded or target.stat().st_mode & 0o777 != 0o444:
        raise E1Error(f"published artifact failed readback: {target}")
    loaded = _load_json(target, field=f"published artifact {target.name}")
    if loaded != payload:
        raise E1Error(f"published artifact payload changed on readback: {target}")
    return digest


def _verify_published(path: Path, payload: Mapping[str, object], digest: str) -> None:
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_mode & 0o777 != 0o444
        or file_sha256(path) != digest
        or _load_json(path, field=f"published {path.name}") != payload
    ):
        raise E1Error(f"published artifact failed immutable hash readback: {path}")


@contextmanager
def _interruption_safe_publication() -> Any:
    """Defer catchable process interruptions across the final atomic rename."""

    mask = {signal.SIGINT, signal.SIGTERM}
    previous: set[signal.Signals] | None = None
    if hasattr(signal, "pthread_sigmask"):
        try:
            previous = signal.pthread_sigmask(signal.SIG_BLOCK, mask)
        except (OSError, ValueError):
            previous = None
    try:
        yield
    finally:
        if previous is not None:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous)


def _publish_write_once(path: Path, payload: Mapping[str, object]) -> str:
    """Stage, fsync, and atomically rename one immutable JSON artifact."""

    target = Path(path)
    if target.exists() or target.is_symlink():
        raise E1Error(f"refusing to overwrite write-once artifact: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, stage_text = tempfile.mkstemp(
        prefix=f".stage-{target.name}-", suffix=".tmp", dir=target.parent
    )
    os.close(descriptor)
    stage = Path(stage_text)
    stage.unlink()
    try:
        digest = _write_once(stage, payload)
        _verify_published(stage, payload, digest)
        with _interruption_safe_publication():
            if target.exists() or target.is_symlink():
                raise E1Error(f"refusing to overwrite write-once artifact: {target}")
            os.rename(stage, target)
        _verify_published(target, payload, digest)
        return digest
    finally:
        if stage.exists() or stage.is_symlink():
            stage.unlink()


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
    try:
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
        manifest_sha = _write_once(manifest_path, manifest)
        receipt_payload = _unit_receipt(tape, key=key, tape_sha256=tape_sha)
        receipt_sha = _write_once(receipt_path, receipt_payload)
        _verify_published(tape_path, tape, tape_sha)
        _verify_published(manifest_path, manifest, manifest_sha)
        _verify_published(receipt_path, receipt_payload, receipt_sha)
        stage.chmod(0o555)
        with _interruption_safe_publication():
            if final.exists() or final.is_symlink():
                raise E1Error(f"refusing to overwrite write-once unit {key.slug}")
            os.rename(stage, final)
        authenticate_unit_bundle(root, key=key, preflight_sha256=str(tape["preflight_manifest_sha256"]))
        return final / DEFAULT_TAPE_NAME, final / DEFAULT_TAPE_MANIFEST_NAME, final / DEFAULT_UNIT_RECEIPT_NAME
    finally:
        if stage.exists() or stage.is_symlink():
            if stage.is_dir() and not stage.is_symlink():
                stage.chmod(0o755)
            shutil.rmtree(stage)


def incomplete_receipt(
    *, scope: str, preflight_sha256: str, error: BaseException,
    key: UnitKey | None = None, worker_seconds: float | None = None,
) -> dict[str, object]:
    return {
        "schema": TERMINAL_RECEIPT_SCHEMA if key is None else UNIT_RECEIPT_SCHEMA,
        "status": "INCOMPLETE",
        "outcome": "INCOMPLETE",
        "scope": scope,
        "claim_ceiling": CLAIM_CEILING,
        "unit": None if key is None else key.as_dict(),
        "preflight_manifest_sha256": _digest(preflight_sha256, field="preflight sha256"),
        "worker_seconds_hex": None if worker_seconds is None else float(worker_seconds).hex(),
        "error_type": type(error).__name__,
        "error_sha256": hashlib.sha256(str(error).encode("utf-8")).hexdigest(),
        "integrity": None,
        "U1": None,
        "J1": None,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }


def _write_incomplete(
    output: Path, *, scope: str, preflight_sha256: str, error: BaseException,
    key: UnitKey | None = None, worker_seconds: float | None = None,
) -> Path:
    root = Path(output) / "incomplete"
    root.mkdir(parents=True, exist_ok=True)
    stem = key.slug if key is not None else scope
    payload = incomplete_receipt(
        scope=scope, preflight_sha256=preflight_sha256, error=error,
        key=key, worker_seconds=worker_seconds,
    )
    for sequence in range(1, 1_000_000):
        path = root / f"{stem}-{sequence:06d}.json"
        try:
            digest = _publish_write_once(path, payload)
        except E1Error as collision:
            if "refusing to overwrite" in str(collision):
                continue
            raise
        _verify_published(path, payload, digest)
        return path
    raise E1Error("INCOMPLETE receipt sequence exhausted")


def _budget_path(output: Path) -> Path:
    return Path(output) / DEFAULT_BUDGET_LEDGER_NAME


def _empty_budget(cap: float) -> dict[str, object]:
    return {
        "schema": f"{SCHEMA}-worker-budget-ledger",
        "cap_worker_seconds_hex": cap.hex(),
        "charged_worker_seconds_hex": 0.0.hex(),
        "unit_charge_count": 0,
        "unit_charged_worker_seconds_hex": 0.0.hex(),
        "reservations": [],
    }


def _parse_budget(payload: Mapping[str, object], cap: float) -> tuple[float, int, float, list[dict[str, object]]]:
    if set(payload) != set(_empty_budget(cap)) or (
        payload.get("schema") != f"{SCHEMA}-worker-budget-ledger"
        or payload.get("cap_worker_seconds_hex") != cap.hex()
    ):
        raise E1Error("worker budget ledger binding drifted")
    try:
        charged = float.fromhex(str(payload["charged_worker_seconds_hex"]))
        unit_charged = float.fromhex(str(payload["unit_charged_worker_seconds_hex"]))
        count = payload["unit_charge_count"]
        reservations = payload["reservations"]
    except (KeyError, TypeError, ValueError) as error:
        raise E1Error("worker budget ledger is malformed") from error
    if (
        not math.isfinite(charged) or charged < 0.0 or charged > cap
        or not math.isfinite(unit_charged) or unit_charged < 0.0
        or type(count) is not int or count < 0
        or not isinstance(reservations, list)
    ):
        raise E1Error("worker budget ledger usage is malformed")
    seen: set[str] = set()
    normalized: list[dict[str, object]] = []
    for row in reservations:
        if not isinstance(row, Mapping) or set(row) != {
            "token", "scope", "unit", "reserved_worker_seconds_hex"
        }:
            raise E1Error("worker budget reservation is malformed")
        token = row.get("token")
        scope = row.get("scope")
        unit = row.get("unit")
        try:
            reserved = float.fromhex(str(row.get("reserved_worker_seconds_hex")))
        except (TypeError, ValueError) as error:
            raise E1Error("worker budget reservation amount is malformed") from error
        if (
            not isinstance(token, str) or not token or token in seen
            or scope not in {"unit", "merge"}
            or unit is not None and not isinstance(unit, str)
            or not math.isfinite(reserved) or reserved <= 0.0
        ):
            raise E1Error("worker budget reservation is malformed")
        seen.add(token)
        normalized.append(dict(row))
    if charged + math.fsum(
        float.fromhex(str(row["reserved_worker_seconds_hex"])) for row in normalized
    ) > cap:
        raise E1Error("worker budget reservations exceed the total pool")
    return charged, count, unit_charged, normalized


def _locked_budget_update(
    output: Path, cap: float,
    update: Callable[[dict[str, object]], tuple[dict[str, object], Any]],
) -> Any:
    root = Path(output)
    root.mkdir(parents=True, exist_ok=True)
    path = _budget_path(root)
    with path.open("a+b") as ledger:
        fcntl.flock(ledger.fileno(), fcntl.LOCK_EX)
        try:
            ledger.seek(0)
            raw = ledger.read()
            payload = _empty_budget(cap) if not raw else json.loads(raw)
            if not isinstance(payload, dict):
                raise E1Error("worker budget ledger is malformed")
            _parse_budget(payload, cap)
            replacement, result = update(payload)
            _parse_budget(replacement, cap)
            encoded = canonical_bytes(replacement) + b"\n"
            ledger.seek(0)
            ledger.truncate()
            ledger.write(encoded)
            ledger.flush()
            os.fsync(ledger.fileno())
            ledger.seek(0)
            if ledger.read() != encoded:
                raise E1Error("worker budget ledger failed readback")
            return result
        finally:
            fcntl.flock(ledger.fileno(), fcntl.LOCK_UN)


def _budget_snapshot(output: Path, cap: float) -> dict[str, object]:
    path = _budget_path(output)
    if not path.exists():
        return _empty_budget(cap)
    with path.open("rb") as ledger:
        fcntl.flock(ledger.fileno(), fcntl.LOCK_SH)
        try:
            payload = json.load(ledger)
            if not isinstance(payload, dict):
                raise E1Error("worker budget ledger is malformed")
            _parse_budget(payload, cap)
            return payload
        finally:
            fcntl.flock(ledger.fileno(), fcntl.LOCK_UN)


def _read_budget(output: Path, cap: float) -> float:
    payload = _budget_snapshot(output, cap)
    charged, _count, _unit_charged, _reservations = _parse_budget(payload, cap)
    return charged


@dataclass(frozen=True)
class BudgetReservation:
    token: str
    reserved_worker_seconds: float


def _reserve_budget(
    output: Path, cap: float, *, scope: str, key: UnitKey | None = None,
    declared_default: float = DEFAULT_BUDGET_RESERVATION_WORKER_SECONDS,
) -> BudgetReservation:
    if scope not in {"unit", "merge"} or not math.isfinite(declared_default) or declared_default <= 0.0:
        raise E1Error("worker budget reservation request is malformed")
    token = f"{scope}:{'none' if key is None else key.slug}:{os.getpid()}:{time.time_ns()}"

    def update(payload: dict[str, object]) -> tuple[dict[str, object], BudgetReservation]:
        charged, count, unit_charged, reservations = _parse_budget(payload, cap)
        # The declared default is a conservative floor; a measured unit mean
        # may raise it, but short fixture/verification calls cannot collapse
        # later reservations to an unsafe near-zero timer.
        estimate = max(declared_default, unit_charged / count) if count else declared_default
        reserved_total = math.fsum(
            float.fromhex(str(row["reserved_worker_seconds_hex"])) for row in reservations
        )
        available = cap - charged - reserved_total
        if estimate > available:
            raise E1Incomplete("declared worker-second budget cannot reserve another operation")
        row = {
            "token": token,
            "scope": scope,
            "unit": None if key is None else key.slug,
            "reserved_worker_seconds_hex": estimate.hex(),
        }
        replacement = dict(payload)
        replacement["reservations"] = [*reservations, row]
        return replacement, BudgetReservation(token, estimate)

    return _locked_budget_update(output, cap, update)


def _finish_budget(
    output: Path, cap: float, *, reservation: BudgetReservation, elapsed: float,
) -> float:
    charge = min(max(0.0, elapsed), reservation.reserved_worker_seconds)

    def update(payload: dict[str, object]) -> tuple[dict[str, object], float]:
        charged, count, unit_charged, reservations = _parse_budget(payload, cap)
        matches = [row for row in reservations if row["token"] == reservation.token]
        if len(matches) != 1:
            raise E1Error("worker budget reservation was already charged or is missing")
        row = matches[0]
        charged_after = charged + charge
        replacement = dict(payload)
        replacement["charged_worker_seconds_hex"] = charged_after.hex()
        replacement["reservations"] = [
            candidate for candidate in reservations if candidate["token"] != reservation.token
        ]
        if row["scope"] == "unit":
            replacement["unit_charge_count"] = count + 1
            replacement["unit_charged_worker_seconds_hex"] = (unit_charged + charge).hex()
        return replacement, charged_after

    return _locked_budget_update(output, cap, update)


def _record_budget(output: Path, cap: float, elapsed: float) -> float:
    """Compatibility helper for direct, locked setup charges in tests."""

    charge = max(0.0, elapsed)

    def update(payload: dict[str, object]) -> tuple[dict[str, object], float]:
        charged, _count, _unit_charged, reservations = _parse_budget(payload, cap)
        available = cap - math.fsum(
            float.fromhex(str(row["reserved_worker_seconds_hex"])) for row in reservations
        )
        charged_after = min(available, charged + charge)
        replacement = dict(payload)
        replacement["charged_worker_seconds_hex"] = charged_after.hex()
        return replacement, charged_after

    return _locked_budget_update(output, cap, update)


def _write_invalid_unit(output: Path, *, key: UnitKey, preflight_sha256: str, error: BaseException) -> Path:
    units_root = Path(output) / "units"
    units_root.mkdir(parents=True, exist_ok=True)
    final = _unit_dir(output, key)
    if final.exists() or final.is_symlink():
        raise E1Error(f"refusing to overwrite write-once unit {key.slug}")
    stage = Path(tempfile.mkdtemp(prefix=f".stage-invalid-{key.slug}-", dir=units_root))
    try:
        receipt = stage / DEFAULT_UNIT_RECEIPT_NAME
        payload = invalid_unit_receipt(
            key=key, preflight_sha256=preflight_sha256, error=error
        )
        digest = _write_once(receipt, payload)
        _verify_published(receipt, payload, digest)
        stage.chmod(0o555)
        with _interruption_safe_publication():
            if final.exists() or final.is_symlink():
                raise E1Error(f"refusing to overwrite write-once unit {key.slug}")
            os.rename(stage, final)
        _verify_published(final / DEFAULT_UNIT_RECEIPT_NAME, payload, digest)
        return final / DEFAULT_UNIT_RECEIPT_NAME
    finally:
        if stage.exists() or stage.is_symlink():
            if stage.is_dir() and not stage.is_symlink():
                stage.chmod(0o755)
            shutil.rmtree(stage)


def _validate_invalid_unit_receipt(
    receipt: Mapping[str, object], *, key: UnitKey, preflight_sha256: str
) -> None:
    expected_keys = {
        "schema", "status", "outcome", "claim_ceiling", "unit",
        "panel_bindings", "lineage_authority", "formula_digests",
        "preflight_manifest_sha256", "tape_sha256", "counts", "integrity",
        "error_type", "error_sha256", "test_split_opened", "episode_training",
        "learner_update", "efficacy_claim",
    }
    if (
        set(receipt) != expected_keys
        or receipt.get("schema") != UNIT_RECEIPT_SCHEMA
        or receipt.get("status") != "INVALID_RUN"
        or receipt.get("outcome") != "INVALID_RUN"
        or receipt.get("claim_ceiling") != CLAIM_CEILING
        or receipt.get("unit") != key.as_dict()
        or receipt.get("panel_bindings") != panel_bindings()
        or receipt.get("lineage_authority") != f2.lineage_authority_bindings()[LINEAGES.index(key.lineage)]
        or receipt.get("formula_digests") != formula_digests()
        or receipt.get("preflight_manifest_sha256") != preflight_sha256
        or receipt.get("tape_sha256") is not None
        or receipt.get("counts") is not None
        or receipt.get("integrity") is not False
        or not isinstance(receipt.get("error_type"), str)
        or any(receipt.get(field) is not False for field in (
            "test_split_opened", "episode_training", "learner_update", "efficacy_claim"
        ))
    ):
        raise E1Error(f"unit {key.slug} INVALID_RUN receipt drifted")
    _digest(receipt.get("error_sha256"), field="error_sha256")


def authenticate_unit_bundle(output: Path, *, key: UnitKey, preflight_sha256: str) -> tuple[dict[str, Any], str, dict[str, Any]]:
    root = _unit_dir(output, key)
    receipt_path = root / DEFAULT_UNIT_RECEIPT_NAME
    receipt = _load_json(receipt_path, field=f"unit {key.slug} receipt")
    if receipt_path.stat().st_mode & 0o222:
        raise E1Error(f"unit {key.slug} receipt remains writable")
    if receipt.get("status") == "INVALID_RUN":
        _validate_invalid_unit_receipt(
            receipt, key=key, preflight_sha256=preflight_sha256
        )
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
        if not math.isfinite(interval_s) or interval_s != INTERVAL_S:
            raise E1Error("runtime decision interval disagrees with canonical 30.08 s")
        steps = []
        for step_index in CANONICAL_STEP_INDICES:
            if int(observation.step_index) != step_index:
                raise E1Error("canonical replay reached the wrong step")
            native, q12, reference = _q12_surface_base_only(
                physical, frozen, step_env, observation
            )
            masks = np.asarray(native.action_masks, dtype=np.bool_)
            reference_evaluation = _evaluate_actions_neutral(step_env, reference, rngs[0])
            reference_profile, reference_link_power = f1.profile_from_evaluation(
                reference_evaluation, interval_s=interval_s
            )
            unilateral_rows = []
            for skeleton in f1.enumerate_unilateral_candidates(observation, reference):
                actions = np.asarray(skeleton["candidate_joint_actions"], dtype=np.int64)
                evaluation = _evaluate_actions_neutral(step_env, actions, rngs[0])
                profile, link_power = f1.profile_from_evaluation(evaluation, interval_s=interval_s)
                unilateral_rows.append({
                    **skeleton,
                    "profile_id": f"{UNILATERAL_PROFILE_PREFIX}:{skeleton['focal_user']}:{skeleton['candidate_action']}",
                    "profile": profile,
                    "link_power_w": link_power,
                    "metrics": _profile_metrics(profile),
                    "f0_conservation": _conservation(profile),
                })
            joint_rows = build_joint_witness_catalog(JointWitnessAnchor(
                observation=observation,
                reference_actions=np.asarray(reference, dtype=np.int64),
                reference_profile=reference_profile,
                reference_link_power_w=reference_link_power,
                step_env=step_env,
                rng=rngs[0],
                interval_s=interval_s,
            ))
            step_payload = build_step_payload(
                step_index=step_index,
                q12=q12,
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
    budget_worker_seconds: float = DEFAULT_BUDGET_WORKER_SECONDS,
    clock: Callable[[], float] = time.monotonic,
) -> tuple[Path, bool, bool]:
    marker = _existing_global_invalidation(output, preflight_sha256=preflight_sha256)
    if marker is not None:
        path, digest = marker
        raise E1Error(f"global invalidation marker refuses unit: {path} sha256={digest}")
    if Path(tle_root) != CANONICAL_TLE_ROOT or Path(tle_root).is_symlink():
        raise E1Error("unit execution requires the canonical frozen TLE root")
    if not math.isfinite(budget_worker_seconds) or budget_worker_seconds <= 0.0:
        raise E1Error("worker-second budget must be finite and positive")
    final = _unit_dir(output, key)
    existed_at_start = final.exists() or final.is_symlink()
    try:
        reservation = _reserve_budget(
            output, budget_worker_seconds, scope="unit", key=key
        )
    except E1Incomplete as error:
        used = _read_budget(output, budget_worker_seconds)
        return _write_incomplete(
            output, scope="unit", preflight_sha256=preflight_sha256,
            error=error, key=key, worker_seconds=used,
        ), False, False
    started = clock()
    old_handler: Any = None
    old_timer: tuple[float, float] | None = None
    timer_installed = False
    if hasattr(signal, "setitimer"):
        try:
            def _budget_alarm(_signum: int, _frame: object) -> None:
                raise E1Incomplete("declared worker-second reservation exhausted during unit")

            old_handler = signal.getsignal(signal.SIGALRM)
            signal.signal(signal.SIGALRM, _budget_alarm)
            old_timer = signal.setitimer(
                signal.ITIMER_REAL, reservation.reserved_worker_seconds
            )
            timer_installed = True
        except (ValueError, OSError):
            timer_installed = False
    result: tuple[Path, bool, bool] | None = None
    caught: BaseException | None = None
    try:
        if existed_at_start:
            receipt = _load_json(final / DEFAULT_UNIT_RECEIPT_NAME, field="existing unit receipt")
            if receipt.get("status") == "INVALID_RUN":
                if (final / DEFAULT_UNIT_RECEIPT_NAME).stat().st_mode & 0o222:
                    raise E1Error("existing INVALID_RUN unit receipt remains writable")
                _validate_invalid_unit_receipt(
                    receipt, key=key, preflight_sha256=preflight_sha256
                )
                result = (final / DEFAULT_UNIT_RECEIPT_NAME, True, False)
            else:
                authenticate_unit_bundle(output, key=key, preflight_sha256=preflight_sha256)
                result = (final / DEFAULT_UNIT_RECEIPT_NAME, True, True)
        else:
            tape = generator(
                key=key, tle_root=Path(tle_root), preflight_sha256=preflight_sha256
            )
            _tape, _manifest, receipt = write_unit_bundle(output, key=key, tape=tape)
            result = (receipt, False, True)
    except (Exception, KeyboardInterrupt) as error:
        caught = error
    finally:
        if timer_installed:
            signal.setitimer(signal.ITIMER_REAL, 0.0)
            signal.signal(signal.SIGALRM, old_handler)
            if old_timer is not None and old_timer[0] > 0.0:
                signal.setitimer(signal.ITIMER_REAL, *old_timer)
    with _interruption_safe_publication():
        used_after = _finish_budget(
            output, budget_worker_seconds, reservation=reservation,
            elapsed=clock() - started,
        )
    if caught is None:
        assert result is not None
        return result
    if not existed_at_start and (final.exists() or final.is_symlink()):
        invalidation = _publish_global_invalidation(
            output, preflight_sha256=preflight_sha256, error=caught
        )
        return invalidation, False, False
    if isinstance(caught, (E1Incomplete, KeyboardInterrupt, estimands.E1ResourceIncomplete)):
        return _write_incomplete(
            output, scope="unit", preflight_sha256=preflight_sha256,
            error=caught, key=key, worker_seconds=used_after,
        ), False, False
    if existed_at_start:
        invalidation = _publish_global_invalidation(
            output, preflight_sha256=preflight_sha256, error=caught
        )
        return invalidation, False, False
    receipt = _write_invalid_unit(
        output, key=key, preflight_sha256=preflight_sha256, error=caught
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
    def exact_value(payload: Mapping[str, object], field: str) -> Fraction:
        raw = payload[field]
        if not isinstance(raw, Mapping):
            raise E1Error(f"{field} exact value is malformed")
        return Fraction(int(raw["numerator"]), int(raw["denominator"]))

    u1_exact = exact_value(u1["certificate"], "optimal_ratio_exact")
    u1_base_exact = exact_value(u1, "eta_BASE_exact")
    j1_exact = exact_value(j1["certificate"], "optimal_ratio_exact")
    j1_base_exact = exact_value(j1, "eta_BASE_exact")
    unilateral_outcome = UNILATERAL_OUTCOMES[0] if u1_exact > u1_base_exact else UNILATERAL_OUTCOMES[1]
    joint_outcome = JOINT_OUTCOMES[0] if j1_exact > j1_base_exact else JOINT_OUTCOMES[1]
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


def _publish_global_invalidation(
    output: Path, *, preflight_sha256: str, error: BaseException
) -> Path:
    root = Path(output)
    root.mkdir(parents=True, exist_ok=True)
    path = root / DEFAULT_GLOBAL_INVALIDATION_NAME
    if path.exists() or path.is_symlink():
        _existing_global_invalidation(root, preflight_sha256=preflight_sha256)
        return path
    payload = invalid_terminal_receipt(preflight_sha256=preflight_sha256, error=error)
    digest = _publish_write_once(path, payload)
    _verify_published(path, payload, digest)
    return path


def _existing_global_invalidation(
    output: Path, *, preflight_sha256: str,
) -> tuple[Path, str] | None:
    path = Path(output) / DEFAULT_GLOBAL_INVALIDATION_NAME
    if not path.exists() and not path.is_symlink():
        return None
    if path.is_symlink() or not path.is_file():
        raise E1Error("existing global invalidation record is corrupted")
    receipt = _load_json(path, field="existing global invalidation")
    expected_keys = {
        "schema", "status", "outcome", "claim_ceiling", "panel_bindings",
        "lineage_authorities", "formula_digests", "preflight_manifest_sha256",
        "unit_receipts", "U1", "J1", "integrity", "error_type",
        "error_sha256", "test_split_opened", "episode_training",
        "learner_update", "efficacy_claim",
    }
    if (
        path.stat().st_mode & 0o777 != 0o444
        or set(receipt) != expected_keys
        or receipt.get("schema") != TERMINAL_RECEIPT_SCHEMA
        or receipt.get("status") != "INVALID_RUN"
        or receipt.get("outcome") != "INVALID_RUN"
        or receipt.get("claim_ceiling") != CLAIM_CEILING
        or receipt.get("integrity") is not False
        or receipt.get("preflight_manifest_sha256") != preflight_sha256
        or any(receipt.get(field) is not False for field in (
            "test_split_opened", "episode_training", "learner_update", "efficacy_claim"
        ))
    ):
        raise E1Error("existing global invalidation record is corrupted")
    _digest(receipt.get("error_sha256"), field="global invalidation error_sha256")
    return path, file_sha256(path)


def execute_merge(
    *, output: Path, preflight_sha256: str,
    budget_worker_seconds: float = DEFAULT_BUDGET_WORKER_SECONDS,
    clock: Callable[[], float] = time.monotonic,
) -> tuple[Path, bool, bool]:
    root = Path(output)
    marker = _existing_global_invalidation(root, preflight_sha256=preflight_sha256)
    if marker is not None:
        path, digest = marker
        raise E1Error(f"global invalidation marker refuses merge: {path} sha256={digest}")
    if root.is_symlink():
        raise E1Error("output directory must not be a symlink")
    if not math.isfinite(budget_worker_seconds) or budget_worker_seconds <= 0.0:
        raise E1Error("worker-second budget must be finite and positive")
    root.mkdir(parents=True, exist_ok=True)
    try:
        reservation = _reserve_budget(root, budget_worker_seconds, scope="merge")
    except E1Incomplete as error:
        return _write_incomplete(
            root, scope="merge", preflight_sha256=preflight_sha256,
            error=error, worker_seconds=_read_budget(root, budget_worker_seconds),
        ), False, False
    started = clock()
    old_handler: Any = None
    old_timer: tuple[float, float] | None = None
    timer_installed = False
    if hasattr(signal, "setitimer"):
        try:
            def _budget_alarm(_signum: int, _frame: object) -> None:
                raise E1Incomplete("declared worker-second reservation exhausted during merge")

            old_handler = signal.getsignal(signal.SIGALRM)
            signal.signal(signal.SIGALRM, _budget_alarm)
            old_timer = signal.setitimer(
                signal.ITIMER_REAL, reservation.reserved_worker_seconds
            )
            timer_installed = True
        except (ValueError, OSError):
            timer_installed = False
    terminal = root / DEFAULT_TERMINAL_RECEIPT_NAME
    existed_at_start = terminal.exists() or terminal.is_symlink()
    result: tuple[Path, bool, bool] | None = None
    payload: dict[str, object] | None = None
    caught: BaseException | None = None
    try:
        if existed_at_start:
            receipt = _load_json(terminal, field="existing terminal receipt")
            if terminal.stat().st_mode & 0o777 != 0o444:
                raise E1Error("terminal receipt remains writable")
            if receipt.get("status") == "COMPLETE":
                receipts = []
                digests = []
                tapes = []
                for key in ALL_UNITS:
                    unit_receipt, digest, tape = authenticate_unit_bundle(
                        root, key=key, preflight_sha256=preflight_sha256
                    )
                    receipts.append(unit_receipt)
                    digests.append((key, digest))
                    tapes.append(tape)
                expected = build_terminal_receipt(
                    receipts=receipts, receipt_digests=digests, tapes=tapes,
                    preflight_sha256=preflight_sha256,
                )
                if receipt != expected:
                    raise E1Error("existing terminal receipt disagrees with its units")
                result = (terminal, True, True)
            else:
                expected_keys = set(invalid_terminal_receipt(
                    preflight_sha256=preflight_sha256, error=E1Error("placeholder")
                ))
                if (
                    set(receipt) != expected_keys
                    or receipt.get("schema") != TERMINAL_RECEIPT_SCHEMA
                    or receipt.get("status") != "INVALID_RUN"
                    or receipt.get("outcome") != "INVALID_RUN"
                    or receipt.get("claim_ceiling") != CLAIM_CEILING
                    or receipt.get("panel_bindings") != panel_bindings()
                    or receipt.get("lineage_authorities") != f2.lineage_authority_bindings()
                    or receipt.get("formula_digests") != formula_digests()
                    or receipt.get("preflight_manifest_sha256") != preflight_sha256
                    or receipt.get("integrity") is not False
                ):
                    raise E1Error("existing INVALID_RUN terminal receipt drifted")
                _digest(receipt.get("error_sha256"), field="terminal error_sha256")
                result = (terminal, True, False)
        else:
            missing = sum(not _unit_dir(root, key).is_dir() for key in ALL_UNITS)
            if missing:
                raise E1MergeWaiting(missing)
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
    except (Exception, KeyboardInterrupt) as error:
        caught = error
    finally:
        if timer_installed:
            signal.setitimer(signal.ITIMER_REAL, 0.0)
            signal.signal(signal.SIGALRM, old_handler)
            if old_timer is not None and old_timer[0] > 0.0:
                signal.setitimer(signal.ITIMER_REAL, *old_timer)
    with _interruption_safe_publication():
        used_after = _finish_budget(
            root, budget_worker_seconds, reservation=reservation,
            elapsed=clock() - started,
        )
    if caught is None and result is not None:
        return result
    if isinstance(caught, E1MergeWaiting):
        raise caught
    if isinstance(caught, (estimands.E1ResourceIncomplete, E1Incomplete, KeyboardInterrupt)):
        path = _write_incomplete(
            root, scope="merge", preflight_sha256=preflight_sha256,
            error=caught, worker_seconds=used_after,
        )
        return path, False, False
    if caught is not None and existed_at_start:
        path = _publish_global_invalidation(
            root, preflight_sha256=preflight_sha256, error=caught
        )
        return path, False, False
    if caught is not None:
        payload = invalid_terminal_receipt(
            preflight_sha256=preflight_sha256, error=caught
        )
        valid = False
    else:
        assert payload is not None
        valid = True
    try:
        digest = _publish_write_once(terminal, payload)
        _verify_published(terminal, payload, digest)
    except (E1Incomplete, KeyboardInterrupt) as error:
        path = _write_incomplete(
            root, scope="merge", preflight_sha256=preflight_sha256,
            error=error, worker_seconds=used_after,
        )
        return path, False, False
    return terminal, False, valid


def run(args: argparse.Namespace) -> dict[str, object]:
    # Dry-run must report the unsealed contract, not a downstream missing
    # preflight, so the controller receives the true launch gate first.
    sealed_contract_binding()
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
                launch_arguments=None,
            )
        return result
    if args.launch_authority is None or args.output is None:
        raise E1Error("E1 execution requires --launch-authority and --output")
    if not Path(args.output).is_absolute():
        raise E1Error("E1 execution requires an absolute --output root")
    validate_launch_authority(
        Path(args.launch_authority), preflight_path=Path(args.preflight_manifest),
        preflight_sha256=preflight_sha,
        output_root=Path(args.output), tle_root=Path(args.tle_root) if args.tle_root is not None else None,
        launch_arguments=getattr(args, "raw_launch_arguments", None),
    )
    if args.unit is not None:
        if args.tle_root is None:
            raise E1Error("--unit requires --tle-root")
        receipt, skipped, valid = execute_unit(
            key=UnitKey.parse(args.unit), output=Path(args.output),
            tle_root=Path(args.tle_root), preflight_sha256=preflight_sha,
            budget_worker_seconds=float(args.budget_worker_seconds),
        )
        return {"receipt": receipt, "skipped": skipped, "valid": valid, "mode": "unit"}
    terminal, skipped, valid = execute_merge(
        output=Path(args.output), preflight_sha256=preflight_sha,
        budget_worker_seconds=float(args.budget_worker_seconds),
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
    parser.add_argument(
        "--budget-worker-seconds", type=float,
        default=DEFAULT_BUDGET_WORKER_SECONDS,
        help="one shared unit/verification/merge worker-second pool (default: 57600)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    args = _parser().parse_args(raw)
    args.raw_launch_arguments = raw
    if not args.dry_run and args.unit is None and not args.merge:
        print("E1_ERROR: execution requires exactly one of --unit or --merge", file=sys.stderr)
        return 2
    old_sigterm = signal.getsignal(signal.SIGTERM)
    def _interrupt(_signum: int, _frame: object) -> None:
        raise E1Incomplete("execution interrupted by SIGTERM")
    signal.signal(signal.SIGTERM, _interrupt)
    try:
        result = run(args)
    except E1MergeWaiting as error:
        print(f"E1_MERGE_WAITING {error.missing} units missing")
        return 3
    except Exception as error:
        print(f"E1_ERROR: {error}", file=sys.stderr)
        return 2
    finally:
        signal.signal(signal.SIGTERM, old_sigterm)
    if args.dry_run:
        print("E1_WORLD_SEEDS " + " ".join(str(seed) for seed in result["worlds"]))
        print(f"E1_DRY_RUN_PASS preflight={result['preflight']}")
        return 0
    receipt_payload = _load_json(Path(result["receipt"]), field="published receipt")
    if receipt_payload.get("status") == "INCOMPLETE":
        print(f"E1_{str(result['mode']).upper()}_INCOMPLETE receipt={result['receipt']}")
        return 3
    state = "SKIPPED_COMPLETE" if result["skipped"] else "WRITTEN"
    print(f"E1_{str(result['mode']).upper()}_{state} receipt={result['receipt']}")
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
