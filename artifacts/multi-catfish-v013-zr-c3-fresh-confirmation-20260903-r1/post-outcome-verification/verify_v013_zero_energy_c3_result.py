#!/usr/bin/env python3
"""Independent, fail-closed verifier for the V0.13 ZR oracle result.

This module is intentionally a receipt verifier, not a second runner.  It
does not import the V0.13 runner (or any of its gate helpers), open a simulator
environment, load a learner, or inspect a training log.  It authenticates the
24 immutable shard receipts and recomputes the result-level arithmetic and
acceptance decision from their rows.

The verifier is useful on a copied result bundle as well as in a CI test.  A
normal invocation is::

    python verify_v013_zero_energy_c3_result.py \
      --shards /path/to/run-v013/shards/*/shard.json \
      --merged /path/to/run-v013/merged/result.json \
      --authority /path/to/FROZEN-AUTHORITY.json

The authority checks are enabled by default.  ``verify_bundle(...,
enforce_authority=False)`` exists only for synthetic receipt tests; production
verification should leave it enabled.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np


REPO = Path(__file__).resolve().parents[2]

RESULT_SCHEMA = "multi-catfish-mcrl-v013-zero-energy-c3-oracle-result-v1"
EPISODE_SCHEMA = "multi-catfish-mcrl-v013-zero-energy-c3-oracle-episode-v1"
SHARD_SCHEMA = "multi-catfish-mcrl-v013-zero-energy-c3-oracle-shard-v1"
CONTRACT_SCHEMA = "multi-catfish-mcrl-v013-zero-energy-c3-oracle-contract-v1"
AUTHORITY_SCHEMA = "multi-catfish-mcrl-v013-executable-authority-v1"

WORLD_SEEDS = (2026104901, 2026104902, 2026104903, 2026104904)
LINEAGES = (2026092101, 2026092102, 2026092103)
ARMS = ("DROP_C3", "FULL_ZR")
USERS = 100
STEPS_PER_EPISODE = 10
FIELD_COMPONENT = "MCRL_V013_ZR_ACCEPTANCE_CONFIRMATION_V1"
FIELD_EXCLUDES = (
    "arm",
    "initialization_seed",
    "policy_label",
    "action",
    "target",
    "outcome",
)
FROZEN_STATUS = "Status: **FROZEN BEFORE OUTCOME ACCESS**"
NUM_ACTIONS = 28
EXPECTED_EXECUTION_ENVIRONMENT = {
    "python": "3.13.3",
    "implementation": "cpython",
    "cache_tag": "cpython-313",
    "soabi": "cpython-313-x86_64-linux-gnu",
    "machine": "x86_64",
    "numpy": "2.5.2",
    "numpy_config_sha256": "67dfb7e234e361796a37141fe8465bb2f95d16bdd66033b3ca95d0ad266ff4c3",
    "torch": "2.13.0+cu130",
    "torch_distribution": "2.13.0",
    "torch_git": "cf30153c4c131c8164ee7798e5022d810682e2cb",
    "torch_cuda": "13.0",
    "torch_config_sha256": "e100a7e4066820bfb7d99d6d8d7718604f04364f175d137350aa6bff20563fd0",
    "sgp4": "2.27",
    "pyyaml": "6.0.3",
    "distribution_count": 40,
    "distribution_set_sha256": "9727663cc5c343e0a30b4f49a4e0de9062874582b8ada20104175c9a76360e20",
}

DEFAULT_CONTRACT_PATH = (
    REPO
    / "docs"
    / "MULTI-CATFISH-MCRL-V013-ZR-C3-FRESH-CONFIRMATION-PREREG-2026-09-03.md"
)
DEFAULT_RUNNER_PATH = (
    REPO
    / ".scratch"
    / "zero-energy-c3-v013"
    / "run_v013_zero_energy_c3_oracle.py"
)
DEFAULT_AUTHORITY_PATH = (
    REPO / "artifacts" / "multi-catfish-v013-zr-c3-fresh-confirmation-20260903-r1"
    / "FROZEN-AUTHORITY.json"
)
DEFAULT_PREREG_PATH = REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json"
DEFAULT_RUNTIME_PATHS = (
    REPO / "src" / "mcrl" / "runtime" / "ee_axis_ops3.py",
    REPO / "src" / "mcrl" / "runtime" / "ee_axis_ops3_live.py",
    REPO / "src" / "mcrl" / "runtime" / "ee_axis_zero_marginal_c3.py",
    REPO / "src" / "mcrl" / "runtime" / "ee_axis_zero_marginal_c3_live.py",
)
DEFAULT_SOURCE_ROOTS = (
    REPO / "src",
    REPO / ".scratch" / "c3-v04",
    REPO / "scripts",
    REPO / ".scratch" / "zero-energy-c3-v013",
)

# The V0.13 runner carries only the frozen Q1 head receipt, not a second copy
# of the checkpoint bytes.  These values are the sealed V0.3 source authority
# that the receipt must name.  Keeping them here makes this verifier
# independent of the V0.13 producer and lets it reject a receipt that merely
# agrees with 17 other stale receipts.
V03_AUTHORITY_FILE_SHA256 = (
    "71f339d840bf999642f9392baa0e0325459672419d5e5e21e2de0731ad2b1755"
)
V03_CHECKPOINT_SHA256 = {
    2026092101: (
        "f26aab2fab6d31d6f3e4acd97782beeb0bba055ec94611dc9f3ed47038a231f0"
    ),
    2026092102: (
        "6930534d90840807c4dda1eda9c0ecf58793175053a37a43b75e38a7b6d310ba"
    ),
    2026092103: (
        "507b871f2536097b400b099b9dcb666e8445e9aee921001d61e70ff6042646b2"
    ),
}
V03_HEAD_INDEX = 0
V03_FROZEN_RUNG = 10
V03_TRAINER_ALGORITHM = (
    "multi-catfish-mcrl-ee-axis-v03-action-shared-masked-meanmax"
)
V03_CONFIG_SHA256 = (
    "456267625a1a9481f0f24e5ce1e90c9f914e770f64aa2dbc729aea41c4c0a356"
)


class V013ResultVerificationError(RuntimeError):
    """A receipt, authority, arithmetic, or gate check failed closed."""


# Kept only so the copied legacy helper bodies below remain inertly importable;
# all active V0.13 paths use the explicitly named class above.
V012ResultVerificationError = V013ResultVerificationError


def _canonical_bytes(value: object) -> bytes:
    """Return the exact JSON byte convention used by V0.13 receipts."""

    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V013ResultVerificationError(
            "payload is not finite canonical JSON"
        ) from error


def canonical_sha256(value: object) -> str:
    """Hash a JSON value without importing the producer."""

    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V012ResultVerificationError(
            f"expected a regular non-symlink file: {source}"
        )
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_canonical_json(path: Path) -> dict[str, Any]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V012ResultVerificationError(f"receipt is missing: {source}")
    raw = source.read_bytes()
    try:
        payload = json.loads(
            raw.decode("ascii"),
            parse_constant=lambda value: (
                (_ for _ in ()).throw(ValueError(f"non-finite JSON constant {value}"))
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise V012ResultVerificationError(f"invalid JSON receipt: {source}") from error
    if not isinstance(payload, dict):
        raise V012ResultVerificationError(f"receipt root is not an object: {source}")
    if raw != _canonical_bytes(payload):
        raise V012ResultVerificationError(f"receipt is not canonical JSON: {source}")
    return payload


def _read_sealed_json(path: Path) -> dict[str, Any]:
    """Read a sealed predecessor receipt allowing its canonical final newline."""

    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V012ResultVerificationError(f"sealed source receipt is missing: {source}")
    raw = source.read_bytes()
    try:
        payload = json.loads(
            raw.decode("ascii"),
            parse_constant=lambda value: (
                (_ for _ in ()).throw(ValueError(f"non-finite JSON constant {value}"))
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise V012ResultVerificationError(
            f"invalid sealed source receipt: {source}"
        ) from error
    if not isinstance(payload, dict):
        raise V012ResultVerificationError(
            f"sealed source receipt root is not an object: {source}"
        )
    canonical = _canonical_bytes(payload)
    if raw not in {canonical, canonical + b"\n"}:
        raise V012ResultVerificationError(
            f"sealed source receipt is not canonical JSON: {source}"
        )
    return payload


def _read_json_document(path: Path) -> dict[str, Any]:
    """Read a frozen source document (the PREREG is pretty-printed UTF-8)."""

    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V012ResultVerificationError(f"source JSON is missing: {source}")
    try:
        payload = json.loads(
            source.read_text(encoding="utf-8"),
            parse_constant=lambda value: (
                (_ for _ in ()).throw(ValueError(f"non-finite JSON constant {value}"))
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise V012ResultVerificationError(f"invalid source JSON: {source}") from error
    if not isinstance(payload, dict):
        raise V012ResultVerificationError(f"source JSON root is not an object: {source}")
    return payload


def _sha256_text(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V012ResultVerificationError(f"{field} must be a lowercase SHA-256")
    return value


def _finite_number(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise V012ResultVerificationError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise V012ResultVerificationError(f"{field} must be finite")
    return result


def _nonnegative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise V012ResultVerificationError(f"{field} must be a non-negative integer")
    return int(value)


def _bool(value: object, *, field: str) -> bool:
    if type(value) is not bool:
        raise V012ResultVerificationError(f"{field} must be Boolean")
    return bool(value)


def _require_exact(actual: object, expected: object, *, field: str) -> None:
    if actual != expected:
        raise V012ResultVerificationError(f"{field} does not match frozen value")


def _legacy_contract_placeholder() -> dict[str, Any]:
    """Retained only to keep the copied preamble import-safe.

    The active ``expected_contract`` definition appears in the independent
    V0.13 section below; this placeholder deliberately has no legacy arms.
    """

    return {}


def _prereg_record_digest(payload: Mapping[str, Any]) -> str:
    """Recompute ``PreregRecord.with_digest`` without importing prereg.py."""

    required = ("schema", "sections", "holdout")
    if any(key not in payload for key in required):
        raise V012ResultVerificationError("frozen PREREG omits a required field")
    hashable = json.dumps(
        {
            "schema": payload["schema"],
            "sections": payload["sections"],
            "holdout": payload["holdout"],
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(hashable.encode("utf-8")).hexdigest()


def _tle_file_set_hash(rows: Sequence[Mapping[str, Any]]) -> str:
    try:
        joined = "\n".join(
            f"{row['file']}:{row['sha256']}"
            for row in sorted(rows, key=lambda item: str(item["file"]))
        )
    except (KeyError, TypeError) as error:
        raise V012ResultVerificationError("malformed frozen TLE file rows") from error
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _verify_tle_root(
    prereg: Mapping[str, Any], tle_root: Path
) -> str:
    ephemeris = prereg.get("sections", {}).get("ephemeris", {})
    if not isinstance(ephemeris, Mapping):
        raise V012ResultVerificationError("PREREG ephemeris section is malformed")
    frozen = ephemeris.get("frozen_files")
    if not isinstance(frozen, list) or not frozen:
        raise V012ResultVerificationError("PREREG has no frozen TLE file set")
    root = Path(tle_root)
    if root.is_symlink() or not root.is_dir():
        raise V012ResultVerificationError(f"TLE root is not a directory: {root}")
    actual_rows: list[dict[str, str]] = []
    for frozen_row in frozen:
        if not isinstance(frozen_row, Mapping):
            raise V012ResultVerificationError("malformed frozen TLE file row")
        name = frozen_row.get("file")
        declared = frozen_row.get("sha256")
        if not isinstance(name, str) or not name or Path(name).name != name:
            raise V012ResultVerificationError("TLE file name is not a simple file")
        _sha256_text(declared, field=f"TLE {name} sha256")
        source = root / name
        actual = file_sha256(source)
        if actual != declared:
            raise V012ResultVerificationError(f"TLE file hash mismatch: {name}")
        actual_rows.append({"file": name, "sha256": actual})
    return _tle_file_set_hash(actual_rows)


def python_source_authority(
    *,
    repo: Path = REPO,
    source_roots: Sequence[Path] | None = None,
) -> dict[str, Any]:
    """Recompute the producer's source-set digest without importing it."""

    root = Path(repo)
    roots = tuple(source_roots) if source_roots is not None else tuple(
        root / path.relative_to(REPO) for path in DEFAULT_SOURCE_ROOTS
    )
    files: list[Path] = []
    for source_root in roots:
        if source_root.is_symlink() or not source_root.is_dir():
            raise V012ResultVerificationError(
                f"source authority root is missing or non-regular: {source_root}"
            )
        files.extend(
            path
            for path in source_root.rglob("*.py")
            if path.is_file() and not path.is_symlink()
        )
    if not files:
        raise V012ResultVerificationError("Python source authority set is empty")
    relative_hashes = {
        str(path.relative_to(root)): file_sha256(path)
        for path in sorted(files, key=lambda item: str(item.relative_to(root)))
    }
    return {
        "python_source_file_count": len(relative_hashes),
        "python_source_file_set_sha256": canonical_sha256(relative_hashes),
    }


def current_authority(
    *,
    repo: Path = REPO,
    contract_path: Path | None = None,
    runner_path: Path | None = None,
    prereg_path: Path | None = None,
    runtime_paths: Sequence[Path] | None = None,
    tle_root: Path | None = None,
) -> dict[str, Any]:
    """Build the current-file authority tuple used by each shard.

    Q1 checkpoint bytes are deliberately not guessed here.  The verifier
    authenticates their exact cross-shard receipt consistency; a caller that
    needs checkpoint provenance should run the separate Q1 source gate.
    """

    root = Path(repo)
    contract = Path(contract_path or (root / DEFAULT_CONTRACT_PATH.relative_to(REPO)))
    runner = Path(runner_path or (root / DEFAULT_RUNNER_PATH.relative_to(REPO)))
    prereg_file = Path(prereg_path or (root / DEFAULT_PREREG_PATH.relative_to(REPO)))
    runtimes = tuple(runtime_paths) if runtime_paths is not None else tuple(
        root / path.relative_to(REPO) for path in DEFAULT_RUNTIME_PATHS
    )
    if FROZEN_STATUS not in contract.read_text(encoding="utf-8"):
        raise V012ResultVerificationError(
            "current V0.12 contract is not frozen before outcome access"
        )
    prereg = _read_json_document(prereg_file)
    if prereg.get("schema") != "mcrl-prereg-v1":
        raise V012ResultVerificationError("current PREREG schema drifted")
    declared_record_digest = prereg.get("digest")
    _sha256_text(declared_record_digest, field="PREREG digest")
    recomputed_record_digest = _prereg_record_digest(prereg)
    if declared_record_digest != recomputed_record_digest:
        raise V012ResultVerificationError("current PREREG digest failed")
    sections = prereg.get("sections")
    if not isinstance(sections, Mapping):
        raise V012ResultVerificationError("current PREREG sections are malformed")
    ephemeris = sections.get("ephemeris")
    if not isinstance(ephemeris, Mapping):
        raise V012ResultVerificationError("current PREREG ephemeris is malformed")
    declared_tle_hash = ephemeris.get("file_set_sha256")
    _sha256_text(declared_tle_hash, field="PREREG TLE file-set digest")
    if tle_root is not None:
        actual_tle_hash = _verify_tle_root(prereg, Path(tle_root))
        if actual_tle_hash != declared_tle_hash:
            raise V012ResultVerificationError("current TLE file-set digest failed")
    runtime_hashes = {
        str(path.relative_to(root)): file_sha256(path) for path in runtimes
    }
    source = python_source_authority(repo=root)
    return {
        "contract_file_sha256": file_sha256(contract),
        "runner_file_sha256": file_sha256(runner),
        "runtime_file_sha256": runtime_hashes,
        "source_authority": {
            "prereg_file_sha256": file_sha256(prereg_file),
            "prereg_record_digest": str(declared_record_digest),
            "tle_file_set_sha256": str(declared_tle_hash),
            **source,
        },
        "tle_source_checked": tle_root is not None,
    }


def _check_q1_sources(
    rows: Sequence[Mapping[str, Any]], *, v03_root: Path
) -> dict[str, Any]:
    """Authenticate the carried Q1 head against the sealed V0.3 source.

    This is intentionally receipt-and-byte based.  The verifier does not
    load Torch checkpoints or reconstruct a network; it checks the sealed
    authority metadata, the expected rung/head/seed/algorithm/config, and the
    exact checkpoint file hashes for every lineage.
    """

    root = Path(v03_root)
    if root.is_symlink() or not root.is_dir():
        raise V012ResultVerificationError(f"V0.3 root is not a directory: {root}")
    authority_path = root / "authority.json"
    authority = _read_sealed_json(authority_path)
    authority_file_sha = file_sha256(authority_path)
    if authority_file_sha != V03_AUTHORITY_FILE_SHA256:
        raise V012ResultVerificationError("sealed V0.3 authority.json drifted")
    metadata_checks = (
        (
            "schema",
            "multi-catfish-mcrl-v03-e1-masked-meanmax-fallback-v1-authority",
        ),
        ("status", "SEALED_BEFORE_VALIDATION_DATASET_AND_METRICS"),
        ("fallback_variant", "legal-mask-featurewise-mean-and-maximum-context"),
        ("initialization_seeds", list(LINEAGES)),
        ("one_shot", True),
        ("test_split_opened", False),
        ("validation_dataset_bytes_opened", False),
        ("validation_metrics_computed", False),
        ("held_out_ee_evaluated", False),
    )
    for field, expected in metadata_checks:
        if authority.get(field) != expected:
            raise V012ResultVerificationError(
                f"sealed V0.3 authority.{field} drifted"
            )
    seal_path = root / "authority-seal.json"
    seal = _read_sealed_json(seal_path)
    if (
        seal.get("schema")
        != "multi-catfish-mcrl-v03-e1-masked-meanmax-fallback-v1-authority-seal"
        or seal.get("authority_file_sha256") != authority_file_sha
        or seal.get("authority_sha256") != V03_AUTHORITY_FILE_SHA256
    ):
        raise V012ResultVerificationError("sealed V0.3 authority seal is invalid")
    checkpoint_paths: dict[str, str] = {}
    for lineage, expected_sha in V03_CHECKPOINT_SHA256.items():
        checkpoint = root / "checkpoints" / f"init-{lineage}-rung-000010.pt"
        actual_sha = file_sha256(checkpoint)
        if actual_sha != expected_sha:
            raise V012ResultVerificationError(
                f"sealed V0.3 checkpoint drifted for lineage {lineage}"
            )
        checkpoint_paths[str(lineage)] = str(checkpoint.resolve())
    for lineage in LINEAGES:
        lineage_rows = [
            row
            for row in rows
            if int(row["initialization_seed"]) == lineage
        ]
        if len(lineage_rows) != len(WORLD_SEEDS) * len(ARMS):
            raise V012ResultVerificationError(
                f"Q1 receipt coverage is incomplete for lineage {lineage}"
            )
        expected_path_name = f"init-{lineage}-rung-000010.pt"
        for row in lineage_rows:
            receipt = row["q1_checkpoint"]
            assert isinstance(receipt, Mapping)
            if Path(str(receipt["checkpoint_path"])).name != expected_path_name:
                raise V012ResultVerificationError(
                    f"Q1 receipt path drifted for lineage {lineage}"
                )
            if receipt["checkpoint_sha256"] != V03_CHECKPOINT_SHA256[lineage]:
                raise V012ResultVerificationError(
                    f"Q1 receipt checkpoint SHA drifted for lineage {lineage}"
                )
    return {
        "checked": True,
        "authority_file_sha256": authority_file_sha,
        "checkpoint_file_sha256s": {
            str(lineage): V03_CHECKPOINT_SHA256[lineage] for lineage in LINEAGES
        },
        "rung": V03_FROZEN_RUNG,
        "head_index": V03_HEAD_INDEX,
        "trainer_algorithm": V03_TRAINER_ALGORITHM,
        "config_sha256": V03_CONFIG_SHA256,
        "checkpoint_paths": checkpoint_paths,
    }


def _validate_contract(contract: object) -> None:
    _require_exact(contract, expected_contract(), field="contract")


def _validate_step(
    step: object, *, row_index: int, step_index: int, arm: str
) -> None:
    if not isinstance(step, Mapping):
        raise V012ResultVerificationError(
            f"row {row_index} step {step_index} is not an object"
        )
    _require_exact(step.get("step_index"), step_index, field="step_index")
    for name in (
        "total_bits",
        "total_energy_j",
    ):
        _finite_number(step.get(name), field=f"step[{step_index}].{name}")
    for name in (
        "served_user_steps",
        "active_beam_count",
        "active_satellite_count",
        "action_exposure",
    ):
        _nonnegative_int(step.get(name), field=f"step[{step_index}].{name}")
    actions = step.get("selected_actions")
    if (
        not isinstance(actions, list)
        or len(actions) != USERS
        or any(isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < 28 for value in actions)
    ):
        raise V012ResultVerificationError(
            f"step[{step_index}].selected_actions is not a 100-action vector"
        )
    hashes = step.get("surface_sha256")
    if not isinstance(hashes, Mapping):
        raise V012ResultVerificationError(f"step[{step_index}] omits surface hashes")
    for name in (
        "q1",
        "o2",
        "o3",
        "mask",
        "q1_reference",
        "background",
    ):
        _sha256_text(hashes.get(name), field=f"step[{step_index}].surface.{name}")
    mechanics = step.get("mechanics")
    if not isinstance(mechanics, Mapping):
        raise V012ResultVerificationError(f"step[{step_index}] omits mechanics")
    expected_mechanics = (
        "live_state_and_rng_unchanged",
        "common_mask",
        "reference_rows_exact_zero",
        "illegal_rows_exact_zero",
        "opening_service_gate_equal",
        "o2_immutable",
        "changed_actions_compatible",
        "changed_actions_strictly_positive_c3",
        "joint_support_passed",
        "passed",
    )
    for name in expected_mechanics:
        _bool(mechanics.get(name), field=f"step[{step_index}].mechanics.{name}")
    # The producer intentionally excludes the joint-support outcome from
    # mechanics.passed: an adverse physical outcome must still be serialized
    # as a valid receipt and fail the binding gate later.  Every other
    # mechanics constituent, however, is recomputed here rather than trusting
    # the summary Boolean.
    mechanics_components = all(
        bool(mechanics[name])
        for name in expected_mechanics
        if name not in {"joint_support_passed", "passed"}
    )
    if bool(mechanics["passed"]) != mechanics_components:
        raise V012ResultVerificationError(
            f"step[{step_index}].mechanics.passed is inconsistent"
        )
    method = step.get("method")
    if not isinstance(method, Mapping):
        raise V012ResultVerificationError(f"step[{step_index}] omits method receipt")
    _bool(method.get("identity_passed"), field=f"step[{step_index}].method.identity_passed")
    for name in (
        "positive_target_count",
        "supported_positive_target_count",
    ):
        _nonnegative_int(method.get(name), field=f"step[{step_index}].method.{name}")
    components = method.get("compatibility_component_counts")
    if not isinstance(components, Mapping):
        raise V012ResultVerificationError(
            f"step[{step_index}] omits compatibility component counts"
        )
    for name in (
        "served",
        "active_beams",
        "active_satellites",
        "rf_power",
        "network_power",
        "all",
    ):
        _nonnegative_int(components.get(name), field=f"step[{step_index}].method.{name}")
    joint = step.get("joint_support")
    if not isinstance(joint, Mapping):
        raise V012ResultVerificationError(
            f"step[{step_index}] omits joint support receipt"
        )
    for name in (
        "no_new_active_beam",
        "no_new_active_satellite",
        "network_power_nonincrease",
        "passed",
    ):
        _bool(joint.get(name), field=f"step[{step_index}].joint_support.{name}")
    joint_components = all(
        bool(joint[name])
        for name in (
            "no_new_active_beam",
            "no_new_active_satellite",
            "network_power_nonincrease",
        )
    )
    if bool(joint["passed"]) != joint_components:
        raise V012ResultVerificationError(
            f"step[{step_index}].joint_support.passed is inconsistent"
        )
    if bool(mechanics["joint_support_passed"]) != bool(joint["passed"]):
        raise V012ResultVerificationError(
            f"step[{step_index}] mechanics/joint-support status disagrees"
        )
    expected_kind = "DROP_C3" if arm == "DROP_C3" else arm.removeprefix("FULL_")
    if arm == "DROP_C3":
        _require_exact(
            method.get("kind"), expected_kind, field=f"step[{step_index}].method.kind"
        )
    else:
        _require_exact(
            method.get("formula"),
            expected_kind,
            field=f"step[{step_index}].method.formula",
        )
    status = joint.get("status")
    if status not in {"NO_EXPOSURE", "OBSERVED"}:
        raise V012ResultVerificationError(
            f"step[{step_index}].joint_support.status is invalid"
        )
    changed_users = _nonnegative_int(
        joint.get("changed_users"), field=f"step[{step_index}].joint_support.changed_users"
    )
    if (status == "NO_EXPOSURE") != (changed_users == 0):
        raise V012ResultVerificationError(
            f"step[{step_index}] joint-support exposure status is inconsistent"
        )


def _validate_row(row: object, *, row_index: int) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise V012ResultVerificationError(f"row {row_index} is not an object")
    _require_exact(row.get("schema"), EPISODE_SCHEMA, field="row.schema")
    world = row.get("world_seed")
    lineage = row.get("initialization_seed")
    arm = row.get("arm")
    if world not in WORLD_SEEDS or lineage not in LINEAGES or arm not in ARMS:
        raise V012ResultVerificationError("row has an unfrozen world/arm/lineage")
    _require_exact(row.get("split"), "TRAIN", field="row.split")
    for name in ("test_split_opened", "episode_training", "learner_update"):
        _require_exact(row.get(name), False, field=f"row.{name}")
    _require_exact(row.get("users"), USERS, field="row.users")
    _require_exact(row.get("steps"), STEPS_PER_EPISODE, field="row.steps")
    initial_world = row.get("initial_world_sha256")
    field_digest = row.get("field_root_digest")
    _sha256_text(initial_world, field="row.initial_world_sha256")
    _sha256_text(field_digest, field="row.field_root_digest")
    checkpoint = row.get("q1_checkpoint")
    if not isinstance(checkpoint, dict):
        raise V012ResultVerificationError("row.q1_checkpoint is not an object")
    checkpoint_fields = (
        "checkpoint_path",
        "checkpoint_sha256",
        "parameter_sha256",
        "authority_sha256",
        "initialization_seed",
        "rung",
        "head_index",
        "trainer_algorithm",
        "config_sha256",
    )
    if any(field not in checkpoint for field in checkpoint_fields):
        raise V012ResultVerificationError(
            "row.q1_checkpoint is not a structured frozen-head receipt"
        )
    checkpoint_path = checkpoint.get("checkpoint_path")
    if not isinstance(checkpoint_path, str) or not checkpoint_path:
        raise V012ResultVerificationError("row.q1_checkpoint path is malformed")
    expected_checkpoint_name = f"init-{lineage}-rung-000010.pt"
    if Path(checkpoint_path).name != expected_checkpoint_name:
        raise V012ResultVerificationError("row.q1_checkpoint path is not the frozen rung")
    _sha256_text(checkpoint.get("checkpoint_sha256"), field="q1 checkpoint sha256")
    _sha256_text(checkpoint.get("parameter_sha256"), field="q1 parameter sha256")
    _sha256_text(checkpoint.get("authority_sha256"), field="q1 authority sha256")
    _sha256_text(checkpoint.get("config_sha256"), field="q1 config sha256")
    _require_exact(
        checkpoint.get("checkpoint_sha256"),
        V03_CHECKPOINT_SHA256[int(lineage)],
        field="q1 checkpoint sha256",
    )
    _require_exact(
        checkpoint.get("authority_sha256"),
        V03_AUTHORITY_FILE_SHA256,
        field="q1 authority sha256",
    )
    _require_exact(
        checkpoint.get("initialization_seed"),
        int(lineage),
        field="q1 checkpoint initialization_seed",
    )
    _require_exact(
        checkpoint.get("rung"), V03_FROZEN_RUNG, field="q1 checkpoint rung"
    )
    _require_exact(
        checkpoint.get("head_index"), V03_HEAD_INDEX, field="q1 checkpoint head_index"
    )
    _require_exact(
        checkpoint.get("trainer_algorithm"),
        V03_TRAINER_ALGORITHM,
        field="q1 checkpoint trainer_algorithm",
    )
    _require_exact(
        checkpoint.get("config_sha256"),
        V03_CONFIG_SHA256,
        field="q1 checkpoint config_sha256",
    )
    for name in ("q1_parameter_sha256_before", "q1_parameter_sha256_after"):
        _sha256_text(row.get(name), field=f"row.{name}")
    if row["q1_parameter_sha256_before"] != row["q1_parameter_sha256_after"]:
        raise V012ResultVerificationError("frozen Q1 changed inside a row")
    if (
        checkpoint["parameter_sha256"] != row["q1_parameter_sha256_before"]
        or checkpoint["parameter_sha256"] != row["q1_parameter_sha256_after"]
    ):
        raise V012ResultVerificationError(
            "q1 checkpoint parameter SHA disagrees with row parameter hashes"
        )
    bits = _finite_number(row.get("total_bits"), field="row.total_bits")
    energy = _finite_number(row.get("total_energy_j"), field="row.total_energy_j")
    if bits < 0.0 or energy <= 0.0:
        raise V012ResultVerificationError("row canonical EE inputs are invalid")
    ratio = _finite_number(
        row.get("ratio_of_sums_ee_bits_per_j"), field="row.ratio_of_sums_ee_bits_per_j"
    )
    if ratio != bits / energy:
        raise V012ResultVerificationError("row ratio-of-sums EE does not recompute")
    for name in (
        "served_user_steps",
        "active_beam_steps",
        "active_satellite_steps",
        "c3_legal_spread_count",
        "positive_target_count",
        "supported_positive_target_count",
        "compatible_action_count",
        "action_exposure",
    ):
        _nonnegative_int(row.get(name), field=f"row.{name}")
    fraction = _finite_number(row.get("served_fraction"), field="row.served_fraction")
    if fraction != row["served_user_steps"] / (USERS * STEPS_PER_EPISODE):
        raise V012ResultVerificationError("row served fraction does not recompute")
    for name in (
        "changed_actions_compatible",
        "joint_support_passed",
        "method_passed",
        "candidate_specific_identity_passed",
        "mechanics_passed",
    ):
        _bool(row.get(name), field=f"row.{name}")
    per_step = row.get("per_step")
    if not isinstance(per_step, list) or len(per_step) != STEPS_PER_EPISODE:
        raise V012ResultVerificationError("row per_step coverage is not exactly ten")
    for step_index, step in enumerate(per_step):
        _validate_step(
            step, row_index=row_index, step_index=step_index, arm=str(arm)
        )
    # The row totals must be the direct sum of its ten canonical steps.  Use
    # ordinary left-to-right addition here because that is how the producer
    # accumulates the episode totals; pools below use math.fsum.
    summed_bits = 0.0
    summed_energy = 0.0
    summed_served = 0
    summed_beams = 0
    summed_sats = 0
    summed_exposure = 0
    summed_positive = 0
    summed_supported_positive = 0
    summed_compatible = 0
    mechanics_passed = True
    method_passed = True
    changed_compatible = True
    joint_support_passed = True
    for step in per_step:
        assert isinstance(step, Mapping)
        summed_bits += float(step["total_bits"])
        summed_energy += float(step["total_energy_j"])
        summed_served += int(step["served_user_steps"])
        summed_beams += int(step["active_beam_count"])
        summed_sats += int(step["active_satellite_count"])
        summed_exposure += int(step["action_exposure"])
        mechanics = step["mechanics"]
        method = step["method"]
        joint = step["joint_support"]
        assert isinstance(mechanics, Mapping) and isinstance(method, Mapping)
        assert isinstance(joint, Mapping)
        summed_positive += int(method["positive_target_count"])
        summed_supported_positive += int(method["supported_positive_target_count"])
        summed_compatible += int(method["compatibility_component_counts"]["all"])
        mechanics_passed = mechanics_passed and bool(mechanics["passed"])
        method_passed = method_passed and bool(method["identity_passed"])
        changed_compatible = changed_compatible and bool(
            mechanics["changed_actions_compatible"]
        )
        joint_support_passed = joint_support_passed and bool(joint["passed"])
    if summed_bits != bits or summed_energy != energy:
        raise V012ResultVerificationError("row EE totals do not match per-step totals")
    if (
        summed_served != row["served_user_steps"]
        or summed_beams != row["active_beam_steps"]
        or summed_sats != row["active_satellite_steps"]
        or summed_exposure != row["action_exposure"]
        or summed_positive != row["positive_target_count"]
        or summed_supported_positive != row["supported_positive_target_count"]
        or summed_compatible != row["compatible_action_count"]
    ):
        raise V012ResultVerificationError("row count totals do not match per-step totals")
    if mechanics_passed != row["mechanics_passed"]:
        raise V012ResultVerificationError("row mechanics flag does not recompute")
    if method_passed != row["method_passed"]:
        raise V012ResultVerificationError("row method flag does not recompute")
    if changed_compatible != row["changed_actions_compatible"]:
        raise V012ResultVerificationError(
            "row compatibility flag does not recompute"
        )
    if joint_support_passed != row["joint_support_passed"]:
        raise V012ResultVerificationError(
            "row joint support flag does not recompute"
        )
    if row["candidate_specific_identity_passed"] != row["method_passed"]:
        raise V012ResultVerificationError("row identity flag is inconsistent")
    if arm == "DROP_C3":
        if row["action_exposure"] != 0:
            raise V012ResultVerificationError("DROP_C3 has action exposure")
        if not row["changed_actions_compatible"] or not row["joint_support_passed"]:
            raise V012ResultVerificationError("DROP_C3 structural flags failed")
    return row


def _pool(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise V012ResultVerificationError("cannot pool an empty receipt set")
    bits = math.fsum(float(row["total_bits"]) for row in rows)
    energy = math.fsum(float(row["total_energy_j"]) for row in rows)
    served = sum(int(row["served_user_steps"]) for row in rows)
    return {
        "row_count": len(rows),
        "total_bits": bits,
        "total_energy_j": energy,
        "ratio_of_sums_ee_bits_per_j": bits / energy,
        "served_user_steps": served,
        "served_fraction": served / (len(rows) * USERS * STEPS_PER_EPISODE),
        "active_beam_steps": sum(int(row["active_beam_steps"]) for row in rows),
        "active_satellite_steps": sum(
            int(row["active_satellite_steps"]) for row in rows
        ),
        "c3_legal_spread_count": sum(
            int(row["c3_legal_spread_count"]) for row in rows
        ),
        "supported_positive_target_count": sum(
            int(row["supported_positive_target_count"]) for row in rows
        ),
        "compatible_action_count": sum(
            int(row["compatible_action_count"]) for row in rows
        ),
        "action_exposure": sum(int(row["action_exposure"]) for row in rows),
    }


def _pair_gate(
    *,
    label: str,
    full_arm: str,
    rows: Sequence[Mapping[str, Any]],
    pooled_by_arm: Mapping[str, Mapping[str, Any]],
    pooled_by_world_and_arm: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> dict[str, Any]:
    """Recompute the frozen binding gate, independently of the producer."""

    indexed = {
        (
            int(row["world_seed"]),
            str(row["arm"]),
            int(row["initialization_seed"]),
        ): row
        for row in rows
    }
    full_pool = pooled_by_arm[full_arm]
    drop_pool = pooled_by_arm["DROP_C3"]
    full_ee = float(full_pool["ratio_of_sums_ee_bits_per_j"])
    drop_ee = float(drop_pool["ratio_of_sums_ee_bits_per_j"])
    pooled_delta = full_ee - drop_ee
    by_world: dict[str, Any] = {}
    every_world_positive = True
    every_world_service = True
    every_world_beams = True
    every_world_satellites = True
    every_world_lineages = True
    every_world_service_lineages = True
    for world in WORLD_SEEDS:
        full_world = pooled_by_world_and_arm[str(world)][full_arm]
        drop_world = pooled_by_world_and_arm[str(world)]["DROP_C3"]
        world_delta = float(full_world["ratio_of_sums_ee_bits_per_j"]) - float(
            drop_world["ratio_of_sums_ee_bits_per_j"]
        )
        positive_lineages = 0
        service_lineages = 0
        lineage_receipts: dict[str, Any] = {}
        for lineage in LINEAGES:
            full = indexed[(world, full_arm, lineage)]
            drop = indexed[(world, "DROP_C3", lineage)]
            delta = float(full["ratio_of_sums_ee_bits_per_j"]) - float(
                drop["ratio_of_sums_ee_bits_per_j"]
            )
            service_delta = int(full["served_user_steps"]) - int(
                drop["served_user_steps"]
            )
            positive_lineages += int(delta > 0.0)
            service_lineages += int(service_delta >= 0)
            lineage_receipts[str(lineage)] = {
                "delta_ee_bits_per_j": delta,
                "relative_delta_ee": delta
                / float(drop["ratio_of_sums_ee_bits_per_j"]),
                "delta_served_user_steps": service_delta,
                "delta_active_beam_steps": int(full["active_beam_steps"])
                - int(drop["active_beam_steps"]),
                "delta_active_satellite_steps": int(full["active_satellite_steps"])
                - int(drop["active_satellite_steps"]),
            }
        world_service = int(full_world["served_user_steps"]) >= int(
            drop_world["served_user_steps"]
        )
        world_beams = int(full_world["active_beam_steps"]) <= int(
            drop_world["active_beam_steps"]
        )
        world_satellites = int(full_world["active_satellite_steps"]) <= int(
            drop_world["active_satellite_steps"]
        )
        every_world_positive = every_world_positive and world_delta > 0.0
        every_world_service = every_world_service and world_service
        every_world_beams = every_world_beams and world_beams
        every_world_satellites = every_world_satellites and world_satellites
        every_world_lineages = every_world_lineages and positive_lineages >= 2
        every_world_service_lineages = (
            every_world_service_lineages and service_lineages >= 2
        )
        by_world[str(world)] = {
            "delta_ee_bits_per_j": world_delta,
            "relative_delta_ee": world_delta
            / float(drop_world["ratio_of_sums_ee_bits_per_j"]),
            "delta_served_user_steps": int(full_world["served_user_steps"])
            - int(drop_world["served_user_steps"]),
            "delta_active_beam_steps": int(full_world["active_beam_steps"])
            - int(drop_world["active_beam_steps"]),
            "delta_active_satellite_steps": int(full_world["active_satellite_steps"])
            - int(drop_world["active_satellite_steps"]),
            "positive_lineages": positive_lineages,
            "service_noninferior_lineages": service_lineages,
            "pooled_service_noninferior": world_service,
            "active_beam_steps_not_above": world_beams,
            "active_satellite_steps_not_above": world_satellites,
            "by_lineage": lineage_receipts,
        }
    full_rows = [row for row in rows if str(row["arm"]) == full_arm]
    drop_rows = [row for row in rows if str(row["arm"]) == "DROP_C3"]
    mechanics = all(bool(row["mechanics_passed"]) for row in (*full_rows, *drop_rows))
    method = all(bool(row["method_passed"]) for row in full_rows)
    identity = all(
        bool(row["candidate_specific_identity_passed"]) for row in full_rows
    )
    spread = int(full_pool["c3_legal_spread_count"])
    supported_positive = int(full_pool["supported_positive_target_count"])
    exposure = int(full_pool["action_exposure"])
    changed_compatible = all(
        bool(row["changed_actions_compatible"]) for row in full_rows
    )
    joint_support = all(bool(row["joint_support_passed"]) for row in full_rows)
    pooled_service = int(full_pool["served_user_steps"]) >= int(
        drop_pool["served_user_steps"]
    )
    pooled_beams = int(full_pool["active_beam_steps"]) <= int(
        drop_pool["active_beam_steps"]
    )
    pooled_satellites = int(full_pool["active_satellite_steps"]) <= int(
        drop_pool["active_satellite_steps"]
    )
    hard_stops: list[str] = []
    checks = (
        (mechanics, f"{label} mechanics failed"),
        (method, f"{label} formula method failed"),
        (identity, f"{label} formula identity failed"),
        (spread > 0, f"{label} has zero legal-action C3 spread"),
        (supported_positive > 0, f"{label} has zero supported-positive targets"),
        (exposure > 0, f"{label} has zero executed-action exposure"),
        (changed_compatible, f"{label} changed an action outside compatibility support"),
        (joint_support, f"{label} joint action expanded current energy support"),
        (pooled_delta > 0.0, f"{label} pooled EE is not strictly positive"),
        (every_world_positive, f"{label} is not EE-positive in every frozen world"),
        (every_world_lineages, f"{label} has fewer than two positive lineages in a world"),
        (pooled_service, f"{label} pooled service guard failed"),
        (every_world_service, f"{label} per-world service guard failed"),
        (every_world_service_lineages, f"{label} has fewer than two service-safe lineages in a world"),
        (pooled_beams, f"{label} pooled active-beam guard failed"),
        (every_world_beams, f"{label} per-world active-beam guard failed"),
        (pooled_satellites, f"{label} pooled active-satellite guard failed"),
        (every_world_satellites, f"{label} per-world active-satellite guard failed"),
    )
    hard_stops.extend(message for passed, message in checks if not passed)
    return {
        "label": label,
        "full_arm": full_arm,
        "drop_arm": "DROP_C3",
        "passed": not hard_stops,
        "pooled": {
            "delta_ee_bits_per_j": pooled_delta,
            "relative_delta_ee": pooled_delta / drop_ee,
            "delta_served_user_steps": int(full_pool["served_user_steps"])
            - int(drop_pool["served_user_steps"]),
            "delta_active_beam_steps": int(full_pool["active_beam_steps"])
            - int(drop_pool["active_beam_steps"]),
            "delta_active_satellite_steps": int(full_pool["active_satellite_steps"])
            - int(drop_pool["active_satellite_steps"]),
        },
        "by_world": by_world,
        "mechanics_passed": mechanics,
        "method_passed": method,
        "candidate_specific_identity_passed": identity,
        "c3_legal_spread_count": spread,
        "supported_positive_target_count": supported_positive,
        "action_exposure": exposure,
        "changed_actions_compatible": changed_compatible,
        "joint_support_passed": joint_support,
        "pooled_service_noninferior": pooled_service,
        "pooled_active_beam_steps_not_above": pooled_beams,
        "pooled_active_satellite_steps_not_above": pooled_satellites,
        "hard_stops": hard_stops,
    }


def ordered_decision(*, passed_zr: bool, passed_hr: bool) -> str:
    """Apply the preregistered ZR-before-HR mapping."""

    if passed_zr:
        return "GO_ZR_C3_LEARNABILITY_PREREG_ONLY"
    if passed_hr:
        return "GO_HR_C3_LEARNABILITY_PREREG_ONLY"
    return "STOP_C3_ORACLE_REDESIGN_REVIEW_SEAM"


def _authority_from_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "contract",
        "contract_sha256",
        "contract_file_sha256",
        "runner_file_sha256",
        "runtime_file_sha256",
        "source_authority",
    )
    return {key: payload.get(key) for key in keys}


def _check_authority(
    payloads: Sequence[Mapping[str, Any]],
    *,
    repo: Path,
    contract_path: Path | None,
    runner_path: Path | None,
    prereg_path: Path | None,
    runtime_paths: Sequence[Path] | None,
    tle_root: Path | None,
) -> dict[str, Any]:
    if not payloads:
        raise V012ResultVerificationError("no shard payloads")
    expected_contract_value = expected_contract()
    current = current_authority(
        repo=repo,
        contract_path=contract_path,
        runner_path=runner_path,
        prereg_path=prereg_path,
        runtime_paths=runtime_paths,
        tle_root=tle_root,
    )
    expected = {
        "contract": expected_contract_value,
        "contract_sha256": canonical_sha256(expected_contract_value),
        "contract_file_sha256": current["contract_file_sha256"],
        "runner_file_sha256": current["runner_file_sha256"],
        "runtime_file_sha256": current["runtime_file_sha256"],
        "source_authority": current["source_authority"],
    }
    for index, payload in enumerate(payloads):
        observed = _authority_from_payload(payload)
        if observed != expected:
            raise V012ResultVerificationError(
                f"shard {index} authority does not match current source state"
            )
    for index, payload in enumerate(payloads[1:], start=1):
        if _authority_from_payload(payload) != _authority_from_payload(payloads[0]):
            raise V012ResultVerificationError(
                f"shard {index} authority disagrees with shard 0"
            )
    return {
        "checked": True,
        "tle_source_checked": bool(current["tle_source_checked"]),
        "contract_sha256": expected["contract_sha256"],
        "contract_file_sha256": expected["contract_file_sha256"],
        "runner_file_sha256": expected["runner_file_sha256"],
        "runtime_file_sha256": expected["runtime_file_sha256"],
        "source_authority": expected["source_authority"],
    }


def _check_payload_shape(payload: Mapping[str, Any], *, index: int) -> dict[str, Any]:
    _require_exact(payload.get("schema"), SHARD_SCHEMA, field=f"shard[{index}].schema")
    shard_id = payload.get("shard_id")
    if not isinstance(shard_id, str) or not shard_id:
        raise V012ResultVerificationError(f"shard[{index}] has no shard_id")
    row = payload.get("row")
    if not isinstance(row, dict):
        raise V012ResultVerificationError(f"shard[{index}] has no row")
    row_hash = payload.get("row_sha256")
    _sha256_text(row_hash, field=f"shard[{index}].row_sha256")
    if canonical_sha256(row) != row_hash:
        raise V012ResultVerificationError(f"shard[{index}] row digest failed")
    _validate_row(row, row_index=index)
    expected_id = f"{row['world_seed']}-{row['arm']}-{row['initialization_seed']}"
    if shard_id != expected_id:
        raise V012ResultVerificationError(f"shard[{index}] shard_id is inconsistent")
    return row


def _coverage(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    expected = {
        (world, arm, lineage)
        for world in WORLD_SEEDS
        for arm in ARMS
        for lineage in LINEAGES
    }
    observed = {
        (int(row["world_seed"]), str(row["arm"]), int(row["initialization_seed"]))
        for row in rows
    }
    if observed != expected or len(rows) != len(expected):
        missing = sorted(expected - observed)
        extra = sorted(observed - expected)
        raise V012ResultVerificationError(
            f"world/arm/lineage coverage is not exact (missing={missing}, extra={extra})"
        )
    return {
        "expected_rows": len(expected),
        "observed_rows": len(rows),
        "worlds": list(WORLD_SEEDS),
        "arms": list(ARMS),
        "lineages": list(LINEAGES),
        "exact": True,
    }


def _recompute_result(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_arm = {
        arm: [row for row in rows if str(row["arm"]) == arm] for arm in ARMS
    }
    pooled_by_arm = {arm: _pool(by_arm[arm]) for arm in ARMS}
    pooled_by_world_and_arm = {
        str(world): {
            arm: _pool(
                [
                    row
                    for row in rows
                    if int(row["world_seed"]) == world and str(row["arm"]) == arm
                ]
            )
            for arm in ARMS
        }
        for world in WORLD_SEEDS
    }
    gates = {
        "ZR": _pair_gate(
            label="ZR",
            full_arm="FULL_ZR",
            rows=rows,
            pooled_by_arm=pooled_by_arm,
            pooled_by_world_and_arm=pooled_by_world_and_arm,
        ),
        "HR": _pair_gate(
            label="HR",
            full_arm="FULL_ZR",
            rows=rows,
            pooled_by_arm=pooled_by_arm,
            pooled_by_world_and_arm=pooled_by_world_and_arm,
        ),
    }
    pass_zr = bool(gates["ZR"]["passed"])
    pass_hr = bool(gates["HR"]["passed"])
    return {
        "pooled_by_arm": pooled_by_arm,
        "pooled_by_world_and_arm": pooled_by_world_and_arm,
        "candidate_gates": gates,
        "gate": {
            "decision": ordered_decision(passed_zr=pass_zr, passed_hr=pass_hr),
            "pass_zr": pass_zr,
            "pass_hr": pass_hr,
            "ordered_selection_zr_before_hr": True,
        },
    }


def verify_bundle(
    shard_paths: Sequence[Path],
    merged_path: Path,
    *,
    repo: Path = REPO,
    contract_path: Path | None = None,
    runner_path: Path | None = None,
    prereg_path: Path | None = None,
    runtime_paths: Sequence[Path] | None = None,
    tle_root: Path | None = None,
    v03_root: Path | None = None,
    enforce_authority: bool = True,
) -> dict[str, Any]:
    """Verify a complete V0.12 receipt bundle and return a JSON report.

    Any malformed, incomplete, stale, inconsistent, or gate-failing bundle
    returns ``passed=False``.  It never returns a partial success.  This
    function catches only expected verification errors so programming errors
    remain visible to tests and operators.
    """

    try:
        paths = [Path(path) for path in shard_paths]
        if len(paths) != len(WORLD_SEEDS) * len(ARMS) * len(LINEAGES):
            raise V012ResultVerificationError(
                f"expected exactly {len(WORLD_SEEDS) * len(ARMS) * len(LINEAGES)} shard paths"
            )
        payloads = [_read_canonical_json(path) for path in paths]
        rows = [
            _check_payload_shape(payload, index=index)
            for index, payload in enumerate(payloads)
        ]
        coverage = _coverage(rows)
        if enforce_authority and tle_root is None:
            raise V012ResultVerificationError(
                "production verification requires --tle-root"
            )
        # The same frozen Q1 lineage must be used by both worlds and all
        # three arms.  This is the receipt-level checkpoint authentication
        # available to this lightweight verifier; it does not pretend to
        # recompute neural-network parameter bytes.
        for lineage in LINEAGES:
            lineage_rows = [
                row
                for row in rows
                if int(row["initialization_seed"]) == lineage
            ]
            first_lineage = lineage_rows[0]
            if any(
                row["q1_checkpoint"] != first_lineage["q1_checkpoint"]
                or row["q1_parameter_sha256_before"]
                != first_lineage["q1_parameter_sha256_before"]
                or row["q1_parameter_sha256_after"]
                != first_lineage["q1_parameter_sha256_after"]
                for row in lineage_rows[1:]
            ):
                raise V012ResultVerificationError(
                    f"lineage {lineage} Q1 checkpoint receipts disagree"
                )
        authority = (
            _check_authority(
                payloads,
                repo=Path(repo),
                contract_path=contract_path,
                runner_path=runner_path,
                prereg_path=prereg_path,
                runtime_paths=runtime_paths,
                tle_root=tle_root,
            )
            if enforce_authority
            else {"checked": False, "reason": "synthetic/test mode"}
        )
        q1_authority = (
            _check_q1_sources(rows, v03_root=Path(v03_root))
            if enforce_authority and v03_root is not None
            else (
                {
                    "checked": False,
                    "reason": "synthetic/test mode",
                }
                if not enforce_authority
                else {
                    "checked": False,
                    "reason": "missing required v03_root",
                }
            )
        )
        if enforce_authority and v03_root is None:
            raise V012ResultVerificationError(
                "production verification requires --v03-root"
            )
        merged = _read_canonical_json(Path(merged_path))
        _require_exact(merged.get("schema"), RESULT_SCHEMA, field="result.schema")
        _require_exact(
            merged.get("claim_ceiling"),
            "TWO_TRAIN_WORLD_ORDERED_ORACLE_NO_LEARNER_NO_TEST",
            field="result.claim_ceiling",
        )
        expected_rows = sorted(
            rows,
            key=lambda row: (
                WORLD_SEEDS.index(int(row["world_seed"])),
                ARMS.index(str(row["arm"])),
                LINEAGES.index(int(row["initialization_seed"])),
            ),
        )
        if merged.get("rows") != expected_rows:
            raise V012ResultVerificationError(
                "merged result rows do not exactly match sorted shard rows"
            )
        _require_exact(merged.get("contract"), expected_contract(), field="result.contract")
        _require_exact(
            merged.get("contract_sha256"),
            canonical_sha256(expected_contract()),
            field="result.contract_sha256",
        )
        for field in (
            "contract_file_sha256",
            "runner_file_sha256",
            "runtime_file_sha256",
            "source_authority",
        ):
            if enforce_authority and merged.get(field) != payloads[0].get(field):
                raise V012ResultVerificationError(
                    f"result.{field} disagrees with shard authority"
                )
        initial_worlds = {
            str(world): next(
                str(row["initial_world_sha256"])
                for row in rows
                if int(row["world_seed"]) == world
            )
            for world in WORLD_SEEDS
        }
        for world in WORLD_SEEDS:
            world_rows = [row for row in rows if int(row["world_seed"]) == world]
            if len({str(row["initial_world_sha256"]) for row in world_rows}) != 1:
                raise V012ResultVerificationError(
                    f"world {world} does not share one initial world receipt"
                )
            if len({str(row["field_root_digest"]) for row in world_rows}) != 1:
                raise V012ResultVerificationError(
                    f"world {world} does not share one common field receipt"
                )
        field_by_world = {
            str(world): next(
                str(row["field_root_digest"])
                for row in rows
                if int(row["world_seed"]) == world
            )
            for world in WORLD_SEEDS
        }
        if field_by_world[str(WORLD_SEEDS[0])] == field_by_world[str(WORLD_SEEDS[1])]:
            raise V012ResultVerificationError("two frozen worlds share one field digest")
        _require_exact(merged.get("initial_world_sha256"), initial_worlds, field="result.initial_world_sha256")
        _require_exact(merged.get("field_root_digest_by_world"), field_by_world, field="result.field_root_digest_by_world")
        recomputed = _recompute_result(rows)
        _require_exact(merged.get("summaries"), {key: recomputed[key] for key in ("pooled_by_arm", "pooled_by_world_and_arm", "candidate_gates")}, field="result.summaries")
        _require_exact(merged.get("gate"), recomputed["gate"], field="result.gate")
        result_without_hash = dict(merged)
        result_hash = result_without_hash.pop("result_sha256", None)
        _sha256_text(result_hash, field="result.result_sha256")
        if canonical_sha256(result_without_hash) != result_hash:
            raise V012ResultVerificationError("merged result digest failed")
        return {
            "passed": True,
            "schema": RESULT_SCHEMA,
            "shard_count": len(payloads),
            "coverage": coverage,
            "authority": authority,
            "q1_authority": q1_authority,
            "decision": recomputed["gate"]["decision"],
            "pass_zr": recomputed["gate"]["pass_zr"],
            "pass_hr": recomputed["gate"]["pass_hr"],
            "result_sha256": result_hash,
            "recomputed": recomputed,
        }
    except V012ResultVerificationError as error:
        return {
            "passed": False,
            "schema": RESULT_SCHEMA,
            "errors": [str(error)],
        }


###############################################################################
# Independent V0.13 implementation
#
# The copied V0.12 helpers above are intentionally left untouched as a source
# comparison aid.  The definitions below are the only ones used by the V0.13
# verifier.  They do not import the producer, the simulator, or any outcome.
###############################################################################


def _v013_exact_keys(
    value: object, expected: set[str], *, field: str
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise V013ResultVerificationError(f"{field} is not an object")
    observed = set(value.keys())
    if observed != expected:
        missing = sorted(expected - observed)
        extra = sorted(observed - expected)
        raise V013ResultVerificationError(
            f"{field} keys are not exact (missing={missing}, extra={extra})"
        )
    return dict(value)


def _v013_no_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_canonical_json(path: Path) -> dict[str, Any]:
    """Read one ASCII canonical JSON object and reject duplicate keys."""

    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V013ResultVerificationError(f"receipt is missing: {source}")
    raw = source.read_bytes()
    try:
        payload = json.loads(
            raw.decode("ascii"),
            object_pairs_hook=_v013_no_duplicate_pairs,
            parse_constant=lambda value: (
                (_ for _ in ()).throw(ValueError(f"non-finite JSON constant {value}"))
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise V013ResultVerificationError(f"invalid JSON receipt: {source}: {error}") from error
    if not isinstance(payload, dict):
        raise V013ResultVerificationError(f"receipt root is not an object: {source}")
    if raw != _canonical_bytes(payload):
        raise V013ResultVerificationError(f"receipt is not canonical JSON: {source}")
    return payload


def _v013_sha256(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V013ResultVerificationError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _v013_finite(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise V013ResultVerificationError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise V013ResultVerificationError(f"{field} must be finite")
    return result


def _v013_nonnegative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or type(value) is not int or value < 0:
        raise V013ResultVerificationError(f"{field} must be a non-negative integer")
    return int(value)


def _v013_bool(value: object, *, field: str) -> bool:
    if type(value) is not bool:
        raise V013ResultVerificationError(f"{field} must be Boolean")
    return bool(value)


def _v013_exact(actual: object, expected: object, *, field: str) -> None:
    if actual != expected:
        raise V013ResultVerificationError(f"{field} does not match frozen value")


def expected_contract() -> dict[str, Any]:
    """Reconstruct the V0.13 contract without importing its producer."""

    return {
        "schema": CONTRACT_SCHEMA,
        "world_seeds": list(WORLD_SEEDS),
        "lineages": list(LINEAGES),
        "arms": list(ARMS),
        "arm_heads": {
            "DROP_C3": ["Q1", "O2_OPS3"],
            "FULL_ZR": ["Q1", "O2_OPS3", "O3_ZR"],
        },
        "candidate_order": ["ZR"],
        "users": USERS,
        "steps_per_episode": STEPS_PER_EPISODE,
        "episodes": len(WORLD_SEEDS) * len(LINEAGES) * len(ARMS),
        "split": "TRAIN",
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "background": "MASKED_ARGMAX_Q1_PLUS_O2",
        "summation": "left_to_right_unweighted",
        "selection": "one_common_mask_one_argmax_one_action",
        "compatibility": {
            "role": "teacher_target_support_not_action_mask",
            "tolerance": 0.0,
            "components": [
                "served_vector",
                "active_beam_set",
                "active_satellite_set",
                "per_beam_rf_power",
                "canonical_network_power",
            ],
        },
        "field_components": [FIELD_COMPONENT, "world_seed"],
        "field_excludes": list(FIELD_EXCLUDES),
        "zero_marginal_c3_schema": "multi-catfish-mcrl-v012-zero-marginal-c3-surface-v1",
        "zero_marginal_c3_live_schema": "multi-catfish-mcrl-v012-zero-energy-c3-live-measurement-v1",
        "ops3_live_schema": "multi-catfish-mcrl-v03-c2-ops3-live-anchor-v1.2",
        "lambda_bits_per_j_hex": "0x1.443a8f481639ap+26",
        "kappa_bits_hex": "0x1.2cea89d260f2ap+33",
        "gate": {
            "pooled_full_strictly_above_drop_c3": True,
            "every_world_strictly_above_drop_c3": True,
            "positive_lineages_per_world_minimum": 2,
            "service_noninferior_pooled_and_every_world": True,
            "service_noninferior_lineages_per_world_minimum": 2,
            "one_user_step_shortfall_fails": True,
            "exact_total_trajectory_energy_nonincrease_pooled_or_world": True,
            "active_beam_steps_not_above_pooled_or_world": "diagnostic_only",
            "active_satellite_steps_not_above_pooled_or_world": "diagnostic_only",
            "nonzero_supported_positive_spread": True,
            "nonzero_executed_action_exposure": True,
            "every_changed_action_compatible": True,
            "executed_joint_adds_no_beam_or_satellite": True,
            "executed_joint_network_power_nonincrease": True,
        },
        "selection_table": {
            "ZR": "GO_ZR_C3_LEARNABILITY_PREREG_ONLY",
            "none": "STOP_ZR_C3_ORACLE",
        },
    }


def array_sha256(*values: object) -> str:
    """Match the receipt's dtype/shape/bytes array digest convention."""

    digest = hashlib.sha256()
    for value in values:
        array = np.ascontiguousarray(np.asarray(value))
        digest.update(array.dtype.str.encode("ascii"))
        digest.update(repr(tuple(array.shape)).encode("ascii"))
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


_AUTHORITY_KEYS = {
    "base_prereg",
    "contract_file_sha256",
    "contract_receipt_sha256",
    "execution_environment",
    "pyproject_file_sha256",
    "python_source_authority",
    "runner_file_sha256",
    "runtime_file_sha256",
    "schema",
    "v03_frozen",
    "wrapper_file_sha256",
}


def _validate_authority_document(
    authority: object, *, authority_path: Path | None = None
) -> dict[str, Any]:
    value = _v013_exact_keys(authority, _AUTHORITY_KEYS, field="frozen_authority")
    _v013_exact(value["schema"], AUTHORITY_SCHEMA, field="frozen_authority.schema")
    env = _v013_exact_keys(
        value["execution_environment"],
        set(EXPECTED_EXECUTION_ENVIRONMENT),
        field="frozen_authority.execution_environment",
    )
    _v013_exact(env, EXPECTED_EXECUTION_ENVIRONMENT, field="execution_environment")
    for name in (
        "contract_file_sha256",
        "contract_receipt_sha256",
        "pyproject_file_sha256",
        "runner_file_sha256",
    ):
        _v013_sha256(value[name], field=f"frozen_authority.{name}")
    _v013_exact(
        value["contract_receipt_sha256"],
        canonical_sha256(expected_contract()),
        field="frozen_authority.contract_receipt_sha256",
    )
    runtime = value["runtime_file_sha256"]
    if not isinstance(runtime, Mapping) or not runtime:
        raise V013ResultVerificationError("frozen_authority.runtime_file_sha256 is empty")
    for name, digest in runtime.items():
        if not isinstance(name, str) or not name:
            raise V013ResultVerificationError("frozen_authority runtime path is malformed")
        _v013_sha256(digest, field=f"frozen_authority.runtime_file_sha256.{name}")
    wrappers = value["wrapper_file_sha256"]
    if not isinstance(wrappers, Mapping) or not wrappers:
        raise V013ResultVerificationError("frozen_authority.wrapper_file_sha256 is empty")
    for name, digest in wrappers.items():
        if not isinstance(name, str) or not name:
            raise V013ResultVerificationError("frozen_authority wrapper path is malformed")
        _v013_sha256(digest, field=f"frozen_authority.wrapper_file_sha256.{name}")
    base = _v013_exact_keys(
        value["base_prereg"],
        {"file_sha256", "record_digest", "tle_file_set_sha256"},
        field="frozen_authority.base_prereg",
    )
    for name, digest in base.items():
        _v013_sha256(digest, field=f"frozen_authority.base_prereg.{name}")
    source = _v013_exact_keys(
        value["python_source_authority"],
        {"python_source_file_count", "python_source_file_set_sha256"},
        field="frozen_authority.python_source_authority",
    )
    _v013_nonnegative_int(
        source["python_source_file_count"],
        field="frozen_authority.python_source_file_count",
    )
    _v013_sha256(
        source["python_source_file_set_sha256"],
        field="frozen_authority.python_source_file_set_sha256",
    )
    frozen = _v013_exact_keys(
        value["v03_frozen"],
        {"checkpoint_rung", "q1_checkpoint_file_sha256", "q1_head_index", "receipt_file_sha256"},
        field="frozen_authority.v03_frozen",
    )
    _v013_exact(frozen["checkpoint_rung"], V03_FROZEN_RUNG, field="Q1 checkpoint rung")
    _v013_exact(frozen["q1_head_index"], V03_HEAD_INDEX, field="Q1 head index")
    q1_hashes = _v013_exact_keys(
        frozen["q1_checkpoint_file_sha256"],
        {str(lineage) for lineage in LINEAGES},
        field="frozen_authority.q1_checkpoint_file_sha256",
    )
    for lineage in LINEAGES:
        _v013_exact(
            q1_hashes[str(lineage)],
            V03_CHECKPOINT_SHA256[lineage],
            field=f"Q1 checkpoint {lineage}",
        )
    receipt_hashes = _v013_exact_keys(
        frozen["receipt_file_sha256"],
        {"authority-seal.json", "authority.json", "result-seal.json", "result.json"},
        field="frozen_authority.v03_frozen.receipt_file_sha256",
    )
    for name, digest in receipt_hashes.items():
        _v013_sha256(digest, field=f"V0.3 receipt {name}")
    if authority_path is not None:
        _v013_sha256(file_sha256(Path(authority_path)), field="authority file")
    return value


def _authority_payload_view(payload: Mapping[str, Any]) -> dict[str, Any]:
    keys = {
        "contract",
        "contract_sha256",
        "contract_file_sha256",
        "runner_file_sha256",
        "runtime_file_sha256",
        "wrapper_file_sha256",
        "source_authority",
        "frozen_authority",
        "frozen_authority_file_sha256",
    }
    return {key: payload.get(key) for key in keys}


def _expected_authority_view(
    authority: Mapping[str, Any], *, authority_file_sha256: str
) -> dict[str, Any]:
    base = authority["base_prereg"]
    source = authority["python_source_authority"]
    return {
        "contract": expected_contract(),
        "contract_sha256": canonical_sha256(expected_contract()),
        "contract_file_sha256": authority["contract_file_sha256"],
        "runner_file_sha256": authority["runner_file_sha256"],
        "runtime_file_sha256": authority["runtime_file_sha256"],
        "wrapper_file_sha256": authority["wrapper_file_sha256"],
        "source_authority": {
            "prereg_file_sha256": base["file_sha256"],
            "prereg_record_digest": base["record_digest"],
            "tle_file_set_sha256": base["tle_file_set_sha256"],
            "python_source_file_count": source["python_source_file_count"],
            "python_source_file_set_sha256": source["python_source_file_set_sha256"],
        },
        "frozen_authority": dict(authority),
        "frozen_authority_file_sha256": authority_file_sha256,
    }


def _validate_q1_receipt(row: Mapping[str, Any], *, lineage: int) -> None:
    receipt = _v013_exact_keys(
        row["q1_checkpoint"],
        {
            "checkpoint_path",
            "checkpoint_sha256",
            "parameter_sha256",
            "authority_sha256",
            "initialization_seed",
            "rung",
            "head_index",
            "trainer_algorithm",
            "config_sha256",
        },
        field="row.q1_checkpoint",
    )
    path = receipt["checkpoint_path"]
    if not isinstance(path, str) or Path(path).name != f"init-{lineage}-rung-000010.pt":
        raise V013ResultVerificationError("row Q1 checkpoint path is not the frozen rung")
    for name in ("checkpoint_sha256", "parameter_sha256", "authority_sha256", "config_sha256"):
        _v013_sha256(receipt[name], field=f"row.q1_checkpoint.{name}")
    _v013_exact(receipt["checkpoint_sha256"], V03_CHECKPOINT_SHA256[lineage], field="Q1 checkpoint SHA")
    _v013_exact(receipt["authority_sha256"], V03_AUTHORITY_FILE_SHA256, field="Q1 authority SHA")
    _v013_exact(receipt["initialization_seed"], lineage, field="Q1 lineage")
    _v013_exact(receipt["rung"], V03_FROZEN_RUNG, field="Q1 rung")
    _v013_exact(receipt["head_index"], V03_HEAD_INDEX, field="Q1 head")
    if not isinstance(receipt["trainer_algorithm"], str) or not receipt["trainer_algorithm"]:
        raise V013ResultVerificationError("row Q1 trainer algorithm is malformed")
    _v013_exact(receipt["config_sha256"], V03_CONFIG_SHA256, field="Q1 config SHA")
    before = _v013_sha256(row["q1_parameter_sha256_before"], field="row.Q1.before")
    after = _v013_sha256(row["q1_parameter_sha256_after"], field="row.Q1.after")
    if before != after or before != receipt["parameter_sha256"]:
        raise V013ResultVerificationError("row frozen Q1 hashes disagree")


def _validate_step_v013(
    step: object, *, row_index: int, step_index: int, arm: str
) -> None:
    value = _v013_exact_keys(
        step,
        {
            "step_index",
            "total_bits",
            "total_energy_j",
            "served_user_steps",
            "active_beam_count",
            "active_satellite_count",
            "action_exposure",
            "c3_legal_spread_count",
            "selected_actions",
            "surface_sha256",
            "mechanics",
            "method",
            "joint_support",
        },
        field=f"row[{row_index}].step[{step_index}]",
    )
    _v013_exact(value["step_index"], step_index, field="step_index")
    bits = _v013_finite(value["total_bits"], field="step.total_bits")
    energy = _v013_finite(value["total_energy_j"], field="step.total_energy_j")
    if bits < 0.0 or energy <= 0.0:
        raise V013ResultVerificationError("step canonical EE inputs are invalid")
    served = _v013_nonnegative_int(value["served_user_steps"], field="step.served_user_steps")
    if served > USERS:
        raise V013ResultVerificationError("step served-user count exceeds the frozen population")
    for name in ("active_beam_count", "active_satellite_count", "action_exposure", "c3_legal_spread_count"):
        count = _v013_nonnegative_int(value[name], field=f"step.{name}")
        if name in {"action_exposure", "c3_legal_spread_count"} and count > USERS:
            raise V013ResultVerificationError(f"step.{name} exceeds the frozen population")
    actions = value["selected_actions"]
    if (
        not isinstance(actions, list)
        or len(actions) != USERS
        or any(type(action) is not int or not 0 <= action < NUM_ACTIONS for action in actions)
    ):
        raise V013ResultVerificationError("step selected_actions is not 100 native actions")
    surfaces = _v013_exact_keys(
        value["surface_sha256"],
        {"q1", "o2", "o3", "mask", "q1_reference", "background"},
        field="step.surface_sha256",
    )
    for name, digest in surfaces.items():
        _v013_sha256(digest, field=f"step.surface_sha256.{name}")

    mechanics = _v013_exact_keys(
        value["mechanics"],
        {
            "live_state_and_rng_unchanged",
            "common_mask",
            "reference_rows_exact_zero",
            "illegal_rows_exact_zero",
            "opening_service_gate_equal",
            "o2_immutable",
            "changed_actions_compatible",
            "changed_actions_strictly_positive_c3",
            "joint_support_passed",
            "background_sha256",
            "passed",
        },
        field="step.mechanics",
    )
    for name in (
        "live_state_and_rng_unchanged",
        "common_mask",
        "reference_rows_exact_zero",
        "illegal_rows_exact_zero",
        "opening_service_gate_equal",
        "o2_immutable",
        "changed_actions_compatible",
        "changed_actions_strictly_positive_c3",
        "joint_support_passed",
        "passed",
    ):
        _v013_bool(mechanics[name], field=f"step.mechanics.{name}")
    _v013_sha256(mechanics["background_sha256"], field="step.mechanics.background_sha256")
    recomputed_mechanics = all(
        mechanics[name]
        for name in (
            "live_state_and_rng_unchanged",
            "common_mask",
            "reference_rows_exact_zero",
            "illegal_rows_exact_zero",
            "opening_service_gate_equal",
            "o2_immutable",
            "changed_actions_compatible",
            "changed_actions_strictly_positive_c3",
            "changed_actions_strictly_positive_c3",
        )
    )
    if mechanics["passed"] is not recomputed_mechanics:
        raise V013ResultVerificationError("step mechanics.passed does not recompute")

    if arm == "DROP_C3":
        method_keys = {
            "kind",
            "identity_passed",
            "positive_target_count",
            "supported_positive_target_count",
            "compatibility_component_counts",
        }
    else:
        method_keys = {
            "formula",
            "identity_passed",
            "positive_target_count",
            "supported_positive_target_count",
            "compatibility_component_counts",
            "unsupported_positive_target_count",
            "counterfactual_evaluations",
            "reference_signature_sha256",
            "measurements_sha256",
        }
    method = _v013_exact_keys(value["method"], method_keys, field="step.method")
    _v013_bool(method["identity_passed"], field="step.method.identity_passed")
    positive = _v013_nonnegative_int(method["positive_target_count"], field="step.method.positive_target_count")
    supported = _v013_nonnegative_int(method["supported_positive_target_count"], field="step.method.supported_positive_target_count")
    if supported > positive:
        raise V013ResultVerificationError("supported-positive count exceeds positive count")
    components = _v013_exact_keys(
        method["compatibility_component_counts"],
        {"served", "active_beams", "active_satellites", "rf_power", "network_power", "all"},
        field="step.method.compatibility_component_counts",
    )
    for name, count_raw in components.items():
        count = _v013_nonnegative_int(count_raw, field=f"step.method.compatibility.{name}")
        if count > USERS * NUM_ACTIONS:
            raise V013ResultVerificationError("compatibility component count is out of bounds")
    if arm == "DROP_C3":
        _v013_exact(method["kind"], "DROP_C3", field="step.method.kind")
        if positive or supported or any(components.values()) or value["action_exposure"] or value["c3_legal_spread_count"]:
            raise V013ResultVerificationError("DROP_C3 contains C3 method activity")
        if surfaces["background"] != mechanics["background_sha256"]:
            raise V013ResultVerificationError("DROP_C3 background hashes disagree")
        if array_sha256(np.asarray(actions, dtype=np.int64)) != surfaces["background"]:
            raise V013ResultVerificationError("DROP_C3 selected actions differ from its background")
    else:
        _v013_exact(method["formula"], "ZR", field="step.method.formula")
        _v013_exact(method["unsupported_positive_target_count"], 0, field="step.method.unsupported_positive_target_count")
        _v013_nonnegative_int(method["counterfactual_evaluations"], field="step.method.counterfactual_evaluations")
        _v013_sha256(method["reference_signature_sha256"], field="step.method.reference_signature_sha256")
        _v013_sha256(method["measurements_sha256"], field="step.method.measurements_sha256")

    joint = value["joint_support"]
    if not isinstance(joint, Mapping):
        raise V013ResultVerificationError("step joint_support is not an object")
    status = joint.get("status")
    short_keys = {
        "status", "changed_users", "no_new_active_beam", "no_new_active_satellite",
        "network_power_nonincrease", "passed",
    }
    observed_keys = short_keys | {
        "delta_bits", "delta_energy_j", "baseline_active_beams", "selected_active_beams",
        "baseline_active_satellites", "selected_active_satellites", "baseline_network_power_w",
        "selected_network_power_w", "power_tolerance_w", "new_active_beams", "new_active_satellites",
    }
    joint_value = _v013_exact_keys(
        joint,
        short_keys if status == "NO_EXPOSURE" else observed_keys,
        field="step.joint_support",
    )
    if status not in {"NO_EXPOSURE", "OBSERVED"}:
        raise V013ResultVerificationError("step joint_support status is invalid")
    changed_users = _v013_nonnegative_int(joint_value["changed_users"], field="step.joint_support.changed_users")
    if changed_users != value["action_exposure"] or ((status == "NO_EXPOSURE") != (changed_users == 0)):
        raise V013ResultVerificationError("step joint-support exposure is inconsistent")
    for name in ("no_new_active_beam", "no_new_active_satellite", "network_power_nonincrease", "passed"):
        _v013_bool(joint_value[name], field=f"step.joint_support.{name}")
    if status == "OBSERVED":
        for name in ("delta_bits", "delta_energy_j", "baseline_network_power_w", "selected_network_power_w", "power_tolerance_w"):
            number = _v013_finite(joint_value[name], field=f"step.joint_support.{name}")
            if name in {"baseline_network_power_w", "selected_network_power_w"} and number <= 0.0:
                raise V013ResultVerificationError("joint-support network power is not positive")
            if name == "power_tolerance_w" and number < 0.0:
                raise V013ResultVerificationError("joint-support power tolerance is negative")
        for name in ("baseline_active_beams", "selected_active_beams", "baseline_active_satellites", "selected_active_satellites"):
            _v013_nonnegative_int(joint_value[name], field=f"step.joint_support.{name}")
        new_beams = joint_value["new_active_beams"]
        new_sats = joint_value["new_active_satellites"]
        if (
            not isinstance(new_beams, list)
            or any(type(pair) is not list or len(pair) != 2 or any(type(item) is not int for item in pair) for pair in new_beams)
            or not isinstance(new_sats, list)
            or any(type(item) is not int for item in new_sats)
        ):
            raise V013ResultVerificationError("joint-support new-resource lists are malformed")
        if joint_value["no_new_active_beam"] is not (len(new_beams) == 0) or joint_value["no_new_active_satellite"] is not (len(new_sats) == 0):
            raise V013ResultVerificationError("joint-support resource flags do not recompute")
        recomputed_power = joint_value["selected_network_power_w"] <= joint_value["baseline_network_power_w"] + joint_value["power_tolerance_w"]
        if joint_value["network_power_nonincrease"] is not recomputed_power:
            raise V013ResultVerificationError("joint-support power flag does not recompute")
    recomputed_joint = bool(
        joint_value["no_new_active_beam"]
        and joint_value["no_new_active_satellite"]
        and joint_value["network_power_nonincrease"]
    )
    if joint_value["passed"] is not recomputed_joint:
        raise V013ResultVerificationError("step joint-support passed flag does not recompute")
    if mechanics["joint_support_passed"] is not joint_value["passed"]:
        raise V013ResultVerificationError("step mechanics and joint-support flags disagree")


def _validate_row_receipt(row: object, *, row_index: int) -> dict[str, Any]:
    value = _v013_exact_keys(
        row,
        {
            "schema", "arm", "initialization_seed", "world_seed", "split", "test_split_opened",
            "episode_training", "learner_update", "users", "steps", "initial_world_sha256",
            "field_root_digest", "q1_checkpoint", "q1_parameter_sha256_before", "q1_parameter_sha256_after",
            "total_bits", "total_energy_j", "ratio_of_sums_ee_bits_per_j", "served_user_steps",
            "served_fraction", "active_beam_steps", "active_satellite_steps", "c3_legal_spread_count",
            "positive_target_count", "supported_positive_target_count", "compatible_action_count",
            "action_exposure", "changed_actions_compatible", "joint_support_passed", "method_passed",
            "candidate_specific_identity_passed", "mechanics_passed", "per_step", "elapsed_s",
        },
        field=f"row[{row_index}]",
    )
    _v013_exact(value["schema"], EPISODE_SCHEMA, field="row.schema")
    world = value["world_seed"]
    lineage = value["initialization_seed"]
    arm = value["arm"]
    if type(world) is not int or world not in WORLD_SEEDS or type(lineage) is not int or lineage not in LINEAGES or type(arm) is not str or arm not in ARMS:
        raise V013ResultVerificationError("row has an unfrozen world, arm, or lineage")
    _v013_exact(value["split"], "TRAIN", field="row.split")
    for name in ("test_split_opened", "episode_training", "learner_update"):
        _v013_exact(value[name], False, field=f"row.{name}")
    _v013_exact(value["users"], USERS, field="row.users")
    _v013_exact(value["steps"], STEPS_PER_EPISODE, field="row.steps")
    _v013_sha256(value["initial_world_sha256"], field="row.initial_world_sha256")
    _v013_sha256(value["field_root_digest"], field="row.field_root_digest")
    _validate_q1_receipt(value, lineage=lineage)
    bits = _v013_finite(value["total_bits"], field="row.total_bits")
    energy = _v013_finite(value["total_energy_j"], field="row.total_energy_j")
    if bits < 0.0 or energy <= 0.0:
        raise V013ResultVerificationError("row canonical EE inputs are invalid")
    ratio = _v013_finite(value["ratio_of_sums_ee_bits_per_j"], field="row.ratio_of_sums_ee_bits_per_j")
    if ratio != bits / energy:
        raise V013ResultVerificationError("row ratio-of-sums EE does not recompute")
    counts: dict[str, int] = {}
    for name in (
        "served_user_steps", "active_beam_steps", "active_satellite_steps", "c3_legal_spread_count",
        "positive_target_count", "supported_positive_target_count", "compatible_action_count", "action_exposure",
    ):
        counts[name] = _v013_nonnegative_int(value[name], field=f"row.{name}")
    if counts["served_user_steps"] > USERS * STEPS_PER_EPISODE:
        raise V013ResultVerificationError("row served-user count is out of bounds")
    fraction = _v013_finite(value["served_fraction"], field="row.served_fraction")
    if fraction != counts["served_user_steps"] / (USERS * STEPS_PER_EPISODE):
        raise V013ResultVerificationError("row served fraction does not recompute")
    flags: dict[str, bool] = {}
    for name in ("changed_actions_compatible", "joint_support_passed", "method_passed", "candidate_specific_identity_passed", "mechanics_passed"):
        flags[name] = _v013_bool(value[name], field=f"row.{name}")
    elapsed = _v013_finite(value["elapsed_s"], field="row.elapsed_s")
    if elapsed < 0.0:
        raise V013ResultVerificationError("row elapsed time is negative")
    per_step = value["per_step"]
    if not isinstance(per_step, list) or len(per_step) != STEPS_PER_EPISODE:
        raise V013ResultVerificationError("row per-step coverage is not exactly ten")
    for step_index, step in enumerate(per_step):
        _validate_step_v013(step, row_index=row_index, step_index=step_index, arm=arm)
    summed_bits = 0.0
    summed_energy = 0.0
    summed = {name: 0 for name in counts}
    recomputed_flags = {
        "changed_actions_compatible": True,
        "joint_support_passed": True,
        "method_passed": True,
        "mechanics_passed": True,
    }
    for step in per_step:
        assert isinstance(step, Mapping)
        summed_bits += float(step["total_bits"])
        summed_energy += float(step["total_energy_j"])
        summed["served_user_steps"] += int(step["served_user_steps"])
        summed["active_beam_steps"] += int(step["active_beam_count"])
        summed["active_satellite_steps"] += int(step["active_satellite_count"])
        summed["action_exposure"] += int(step["action_exposure"])
        summed["c3_legal_spread_count"] += int(step["c3_legal_spread_count"])
        method = step["method"]
        mechanics = step["mechanics"]
        joint = step["joint_support"]
        assert isinstance(method, Mapping) and isinstance(mechanics, Mapping) and isinstance(joint, Mapping)
        summed["positive_target_count"] += int(method["positive_target_count"])
        summed["supported_positive_target_count"] += int(method["supported_positive_target_count"])
        summed["compatible_action_count"] += int(method["compatibility_component_counts"]["all"])
        recomputed_flags["changed_actions_compatible"] &= mechanics["changed_actions_compatible"] is True
        recomputed_flags["joint_support_passed"] &= joint["passed"] is True
        recomputed_flags["method_passed"] &= method["identity_passed"] is True
        recomputed_flags["mechanics_passed"] &= mechanics["passed"] is True
    if summed_bits != bits or summed_energy != energy:
        raise V013ResultVerificationError("row EE totals do not match its ten step receipts")
    if any(summed[name] != counts[name] for name in counts):
        raise V013ResultVerificationError("row count totals do not match its ten step receipts")
    if any(recomputed_flags[name] is not flags[name] for name in recomputed_flags):
        raise V013ResultVerificationError("row Boolean summaries do not match its step receipts")
    if flags["candidate_specific_identity_passed"] is not flags["method_passed"]:
        raise V013ResultVerificationError("row method and identity summaries disagree")
    if arm == "DROP_C3" and any(counts[name] for name in ("action_exposure", "c3_legal_spread_count", "positive_target_count", "supported_positive_target_count", "compatible_action_count")):
        raise V013ResultVerificationError("DROP_C3 row contains C3 activity")
    return value


def _pool_v013(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise V013ResultVerificationError("cannot pool an empty row set")
    bits = math.fsum(float(row["total_bits"]) for row in rows)
    energy = math.fsum(float(row["total_energy_j"]) for row in rows)
    served = sum(int(row["served_user_steps"]) for row in rows)
    return {
        "row_count": len(rows),
        "total_bits": bits,
        "total_energy_j": energy,
        "ratio_of_sums_ee_bits_per_j": bits / energy,
        "served_user_steps": served,
        "served_fraction": served / (len(rows) * USERS * STEPS_PER_EPISODE),
        "active_beam_steps": sum(int(row["active_beam_steps"]) for row in rows),
        "active_satellite_steps": sum(int(row["active_satellite_steps"]) for row in rows),
        "c3_legal_spread_count": sum(int(row["c3_legal_spread_count"]) for row in rows),
        "supported_positive_target_count": sum(int(row["supported_positive_target_count"]) for row in rows),
        "compatible_action_count": sum(int(row["compatible_action_count"]) for row in rows),
        "action_exposure": sum(int(row["action_exposure"]) for row in rows),
    }


def _pair_gate_v013(
    *, label: str, rows: Sequence[Mapping[str, Any]], pooled_by_arm: Mapping[str, Mapping[str, Any]], pooled_by_world_and_arm: Mapping[str, Mapping[str, Mapping[str, Any]]]
) -> dict[str, Any]:
    indexed = {(int(row["world_seed"]), str(row["arm"]), int(row["initialization_seed"])): row for row in rows}
    full_pool = pooled_by_arm["FULL_ZR"]
    drop_pool = pooled_by_arm["DROP_C3"]
    pooled_delta = float(full_pool["ratio_of_sums_ee_bits_per_j"]) - float(drop_pool["ratio_of_sums_ee_bits_per_j"])
    by_world: dict[str, Any] = {}
    every_world_positive = True
    every_world_service = True
    every_world_energy = True
    every_world_lineages = True
    every_world_service_lineages = True
    for world in WORLD_SEEDS:
        full_world = pooled_by_world_and_arm[str(world)]["FULL_ZR"]
        drop_world = pooled_by_world_and_arm[str(world)]["DROP_C3"]
        world_delta = float(full_world["ratio_of_sums_ee_bits_per_j"]) - float(drop_world["ratio_of_sums_ee_bits_per_j"])
        positive_lineages = 0
        service_lineages = 0
        lineage_receipts: dict[str, Any] = {}
        for lineage in LINEAGES:
            full = indexed[(world, "FULL_ZR", lineage)]
            drop = indexed[(world, "DROP_C3", lineage)]
            delta = float(full["ratio_of_sums_ee_bits_per_j"]) - float(drop["ratio_of_sums_ee_bits_per_j"])
            service_delta = int(full["served_user_steps"]) - int(drop["served_user_steps"])
            positive_lineages += int(delta > 0.0)
            service_lineages += int(service_delta >= 0)
            lineage_receipts[str(lineage)] = {
                "delta_ee_bits_per_j": delta,
                "relative_delta_ee": delta / float(drop["ratio_of_sums_ee_bits_per_j"]),
                "delta_served_user_steps": service_delta,
                "delta_active_beam_steps": int(full["active_beam_steps"]) - int(drop["active_beam_steps"]),
                "delta_active_satellite_steps": int(full["active_satellite_steps"]) - int(drop["active_satellite_steps"]),
            }
        world_service = int(full_world["served_user_steps"]) >= int(drop_world["served_user_steps"])
        world_energy = float(full_world["total_energy_j"]) <= float(drop_world["total_energy_j"])
        every_world_positive &= world_delta > 0.0
        every_world_service &= world_service
        every_world_energy &= world_energy
        every_world_lineages &= positive_lineages >= 2
        every_world_service_lineages &= service_lineages >= 2
        by_world[str(world)] = {
            "delta_ee_bits_per_j": world_delta,
            "relative_delta_ee": world_delta / float(drop_world["ratio_of_sums_ee_bits_per_j"]),
            "delta_served_user_steps": int(full_world["served_user_steps"]) - int(drop_world["served_user_steps"]),
            "delta_active_beam_steps": int(full_world["active_beam_steps"]) - int(drop_world["active_beam_steps"]),
            "delta_active_satellite_steps": int(full_world["active_satellite_steps"]) - int(drop_world["active_satellite_steps"]),
            "delta_total_energy_j": float(full_world["total_energy_j"]) - float(drop_world["total_energy_j"]),
            "positive_lineages": positive_lineages,
            "service_noninferior_lineages": service_lineages,
            "pooled_service_noninferior": world_service,
            "total_trajectory_energy_nonincrease": world_energy,
            "active_beam_steps_not_above_diagnostic": int(full_world["active_beam_steps"]) <= int(drop_world["active_beam_steps"]),
            "active_satellite_steps_not_above_diagnostic": int(full_world["active_satellite_steps"]) <= int(drop_world["active_satellite_steps"]),
            "by_lineage": lineage_receipts,
        }
    full_rows = [row for row in rows if row["arm"] == "FULL_ZR"]
    drop_rows = [row for row in rows if row["arm"] == "DROP_C3"]
    mechanics = all(row["mechanics_passed"] is True for row in (*full_rows, *drop_rows))
    method = all(row["method_passed"] is True for row in full_rows)
    identity = all(row["candidate_specific_identity_passed"] is True for row in full_rows)
    spread = int(full_pool["c3_legal_spread_count"])
    supported = int(full_pool["supported_positive_target_count"])
    exposure = int(full_pool["action_exposure"])
    compatible = all(row["changed_actions_compatible"] is True for row in full_rows)
    joint_support = all(row["joint_support_passed"] is True for row in full_rows)
    pooled_service = int(full_pool["served_user_steps"]) >= int(drop_pool["served_user_steps"])
    pooled_energy = float(full_pool["total_energy_j"]) <= float(drop_pool["total_energy_j"])
    checks = (
        (mechanics, f"{label} mechanics failed"),
        (method, f"{label} formula method failed"),
        (identity, f"{label} formula identity failed"),
        (spread > 0, f"{label} has zero legal-action C3 spread"),
        (supported > 0, f"{label} has zero supported-positive targets"),
        (exposure > 0, f"{label} has zero executed-action exposure"),
        (compatible, f"{label} changed an action outside compatibility support"),
        (joint_support, f"{label} joint action expanded current energy support"),
        (pooled_delta > 0.0, f"{label} pooled EE is not strictly positive"),
        (every_world_positive, f"{label} is not EE-positive in every frozen world"),
        (every_world_lineages, f"{label} has fewer than two positive lineages in a world"),
        (pooled_service, f"{label} pooled service guard failed"),
        (every_world_service, f"{label} per-world service guard failed"),
        (every_world_service_lineages, f"{label} has fewer than two service-safe lineages in a world"),
        (pooled_energy, f"{label} pooled trajectory energy increased"),
        (every_world_energy, f"{label} per-world trajectory energy increased"),
    )
    hard_stops = [message for passed, message in checks if not passed]
    return {
        "label": label,
        "full_arm": "FULL_ZR",
        "drop_arm": "DROP_C3",
        "passed": not hard_stops,
        "pooled": {
            "delta_ee_bits_per_j": pooled_delta,
            "relative_delta_ee": pooled_delta / float(drop_pool["ratio_of_sums_ee_bits_per_j"]),
            "delta_served_user_steps": int(full_pool["served_user_steps"]) - int(drop_pool["served_user_steps"]),
            "delta_active_beam_steps": int(full_pool["active_beam_steps"]) - int(drop_pool["active_beam_steps"]),
            "delta_active_satellite_steps": int(full_pool["active_satellite_steps"]) - int(drop_pool["active_satellite_steps"]),
            "delta_total_energy_j": float(full_pool["total_energy_j"]) - float(drop_pool["total_energy_j"]),
        },
        "by_world": by_world,
        "mechanics_passed": mechanics,
        "method_passed": method,
        "candidate_specific_identity_passed": identity,
        "c3_legal_spread_count": spread,
        "supported_positive_target_count": supported,
        "action_exposure": exposure,
        "changed_actions_compatible": compatible,
        "joint_support_passed": joint_support,
        "pooled_service_noninferior": pooled_service,
        "pooled_total_trajectory_energy_nonincrease": pooled_energy,
        "pooled_active_beam_steps_not_above_diagnostic": int(full_pool["active_beam_steps"]) <= int(drop_pool["active_beam_steps"]),
        "pooled_active_satellite_steps_not_above_diagnostic": int(full_pool["active_satellite_steps"]) <= int(drop_pool["active_satellite_steps"]),
        "per_world_total_trajectory_energy_nonincrease": every_world_energy,
        "hard_stops": hard_stops,
    }


def ordered_decision(*, passed_zr: bool) -> str:
    return "GO_ZR_C3_LEARNABILITY_PREREG_ONLY" if passed_zr else "STOP_ZR_C3_ORACLE"


def _recompute_result_v013(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_arm = {arm: [row for row in rows if row["arm"] == arm] for arm in ARMS}
    pooled_by_arm = {arm: _pool_v013(by_arm[arm]) for arm in ARMS}
    pooled_by_world_and_arm = {
        str(world): {
            arm: _pool_v013([row for row in rows if row["world_seed"] == world and row["arm"] == arm])
            for arm in ARMS
        }
        for world in WORLD_SEEDS
    }
    gates = {"ZR": _pair_gate_v013(label="ZR", rows=rows, pooled_by_arm=pooled_by_arm, pooled_by_world_and_arm=pooled_by_world_and_arm)}
    return {
        "pooled_by_arm": pooled_by_arm,
        "pooled_by_world_and_arm": pooled_by_world_and_arm,
        "candidate_gates": gates,
        "gate": {
            "decision": ordered_decision(passed_zr=bool(gates["ZR"]["passed"])),
            "pass_zr": bool(gates["ZR"]["passed"]),
            "ordered_selection_zr_only": True,
        },
    }


def _cross_arm_step_zero(rows: Sequence[Mapping[str, Any]]) -> None:
    """Require the matched arms to share the same step-0 Q1/O2 context."""

    indexed = {(int(row["world_seed"]), str(row["arm"]), int(row["initialization_seed"])): row for row in rows}
    for world in WORLD_SEEDS:
        for lineage in LINEAGES:
            drop = indexed[(world, "DROP_C3", lineage)]["per_step"][0]
            full = indexed[(world, "FULL_ZR", lineage)]["per_step"][0]
            assert isinstance(drop, Mapping) and isinstance(full, Mapping)
            drop_surfaces = drop["surface_sha256"]
            full_surfaces = full["surface_sha256"]
            assert isinstance(drop_surfaces, Mapping) and isinstance(full_surfaces, Mapping)
            for name in ("q1", "o2", "mask", "q1_reference", "background"):
                if drop_surfaces[name] != full_surfaces[name]:
                    raise V013ResultVerificationError(
                        f"world {world} lineage {lineage} step-0 {name} differs across arms"
                    )


def verify_bundle(
    shard_paths: Sequence[Path],
    merged_path: Path,
    *,
    repo: Path = REPO,
    authority_path: Path | None = None,
    enforce_authority: bool = True,
    **_unused: Any,
) -> dict[str, Any]:
    """Verify V0.13 shards, matched context, exact pools, gates, and result hash."""

    try:
        expected_count = len(WORLD_SEEDS) * len(ARMS) * len(LINEAGES)
        paths = [Path(path) for path in shard_paths]
        if len(paths) != expected_count:
            raise V013ResultVerificationError(f"expected exactly {expected_count} shard paths")
        if len(set(paths)) != expected_count:
            raise V013ResultVerificationError("shard paths are not unique")
        payloads = [read_canonical_json(path) for path in paths]
        shard_keys = {
            "schema", "shard_id", "contract", "contract_sha256", "contract_file_sha256",
            "runner_file_sha256", "runtime_file_sha256", "wrapper_file_sha256", "source_authority",
            "frozen_authority", "frozen_authority_file_sha256", "row", "row_sha256",
        }
        rows: list[dict[str, Any]] = []
        first_authority_view: dict[str, Any] | None = None
        frozen_authority: dict[str, Any] | None = None
        authority_file_sha = ""
        if enforce_authority:
            path = Path(authority_path or DEFAULT_AUTHORITY_PATH)
            frozen_authority = _validate_authority_document(read_canonical_json(path), authority_path=path)
            authority_file_sha = file_sha256(path)
            first_authority_view = _expected_authority_view(frozen_authority, authority_file_sha256=authority_file_sha)
        for index, payload in enumerate(payloads):
            value = _v013_exact_keys(payload, shard_keys, field=f"shard[{index}]")
            _v013_exact(value["schema"], SHARD_SCHEMA, field="shard.schema")
            row = _validate_row_receipt(value["row"], row_index=index)
            row_hash = _v013_sha256(value["row_sha256"], field="shard.row_sha256")
            if canonical_sha256(row) != row_hash:
                raise V013ResultVerificationError("shard row digest failed")
            _v013_exact(value["contract"], expected_contract(), field="shard.contract")
            _v013_exact(
                value["contract_sha256"],
                canonical_sha256(expected_contract()),
                field="shard.contract_sha256",
            )
            _v013_sha256(
                value["frozen_authority_file_sha256"],
                field="shard.frozen_authority_file_sha256",
            )
            _validate_authority_document(value["frozen_authority"])
            expected_shard_id = f"{row['world_seed']}-{row['arm']}-{row['initialization_seed']}"
            _v013_exact(value["shard_id"], expected_shard_id, field="shard.shard_id")
            observed_view = _authority_payload_view(value)
            if first_authority_view is None:
                first_authority_view = observed_view
            if enforce_authority:
                assert first_authority_view is not None
                if observed_view != first_authority_view:
                    raise V013ResultVerificationError("shard authority differs from frozen authority")
            elif observed_view != first_authority_view:
                raise V013ResultVerificationError("shard authority fields disagree")
            rows.append(row)
        expected_pairs = {(world, arm, lineage) for world in WORLD_SEEDS for arm in ARMS for lineage in LINEAGES}
        observed_pairs = {(int(row["world_seed"]), str(row["arm"]), int(row["initialization_seed"])) for row in rows}
        if observed_pairs != expected_pairs or len(rows) != len(expected_pairs):
            raise V013ResultVerificationError("shard world/arm/lineage coverage is not exact")
        for lineage in LINEAGES:
            lineage_rows = [row for row in rows if row["initialization_seed"] == lineage]
            first = lineage_rows[0]
            for row in lineage_rows[1:]:
                if row["q1_checkpoint"] != first["q1_checkpoint"] or row["q1_parameter_sha256_before"] != first["q1_parameter_sha256_before"] or row["q1_parameter_sha256_after"] != first["q1_parameter_sha256_after"]:
                    raise V013ResultVerificationError(f"lineage {lineage} Q1 receipts disagree")
        for world in WORLD_SEEDS:
            world_rows = [row for row in rows if row["world_seed"] == world]
            if len({row["field_root_digest"] for row in world_rows}) != 1:
                raise V013ResultVerificationError(f"world {world} does not share one common field")
            if len({row["initial_world_sha256"] for row in world_rows}) != 1:
                raise V013ResultVerificationError(f"world {world} does not share one initial world")
        field_by_world = {str(world): next(row["field_root_digest"] for row in rows if row["world_seed"] == world) for world in WORLD_SEEDS}
        if len(set(field_by_world.values())) != len(WORLD_SEEDS):
            raise V013ResultVerificationError("frozen worlds unexpectedly share one field digest")
        _cross_arm_step_zero(rows)
        recomputed = _recompute_result_v013(rows)
        merged = read_canonical_json(Path(merged_path))
        result_keys = {
            "schema", "claim_ceiling", "contract", "contract_sha256", "contract_file_sha256", "runner_file_sha256",
            "runtime_file_sha256", "wrapper_file_sha256", "source_authority", "frozen_authority",
            "frozen_authority_file_sha256", "field_root_digest_by_world", "initial_world_sha256", "rows", "summaries", "gate", "result_sha256",
        }
        result = _v013_exact_keys(merged, result_keys, field="result")
        _v013_exact(result["schema"], RESULT_SCHEMA, field="result.schema")
        _v013_exact(result["claim_ceiling"], "FOUR_TRAIN_WORLD_ZR_ORACLE_NO_LEARNER_NO_TEST", field="result.claim_ceiling")
        expected_rows = sorted(rows, key=lambda row: (WORLD_SEEDS.index(row["world_seed"]), ARMS.index(row["arm"]), LINEAGES.index(row["initialization_seed"])))
        _v013_exact(result["rows"], expected_rows, field="result.rows")
        _v013_exact(result["contract"], expected_contract(), field="result.contract")
        _v013_exact(result["contract_sha256"], canonical_sha256(expected_contract()), field="result.contract_sha256")
        for name in ("contract_file_sha256", "runner_file_sha256", "runtime_file_sha256", "wrapper_file_sha256", "source_authority", "frozen_authority", "frozen_authority_file_sha256"):
            _v013_exact(result[name], first_authority_view[name], field=f"result.{name}")
        initial_worlds = {str(world): next(row["initial_world_sha256"] for row in rows if row["world_seed"] == world) for world in WORLD_SEEDS}
        _v013_exact(result["initial_world_sha256"], initial_worlds, field="result.initial_world_sha256")
        _v013_exact(result["field_root_digest_by_world"], field_by_world, field="result.field_root_digest_by_world")
        _v013_exact(result["summaries"], {key: recomputed[key] for key in ("pooled_by_arm", "pooled_by_world_and_arm", "candidate_gates")}, field="result.summaries")
        _v013_exact(result["gate"], recomputed["gate"], field="result.gate")
        result_hash = _v013_sha256(result["result_sha256"], field="result.result_sha256")
        without_hash = dict(result)
        without_hash.pop("result_sha256")
        if canonical_sha256(without_hash) != result_hash:
            raise V013ResultVerificationError("merged result digest failed")
        return {
            "passed": True,
            "schema": RESULT_SCHEMA,
            "shard_count": len(payloads),
            "coverage": {"expected_rows": expected_count, "observed_rows": len(rows), "worlds": list(WORLD_SEEDS), "arms": list(ARMS), "lineages": list(LINEAGES), "exact": True},
            "authority": {"checked": enforce_authority, "authority_file_sha256": authority_file_sha if enforce_authority else None},
            "decision": recomputed["gate"]["decision"],
            "pass_zr": recomputed["gate"]["pass_zr"],
            "result_sha256": result_hash,
            "recomputed": recomputed,
        }
    except V013ResultVerificationError as error:
        return {"passed": False, "schema": RESULT_SCHEMA, "errors": [str(error)]}


# Public test/diagnostic aliases mirror the producer's receipt vocabulary while
# keeping the implementation above independent of that producer.
V013OracleError = V013ResultVerificationError
_pool = _pool_v013


def _pair_gate(
    *,
    label: str,
    full_arm: str = "FULL_ZR",
    rows: Sequence[Mapping[str, Any]],
    pooled_by_arm: Mapping[str, Mapping[str, Any]],
    pooled_by_world_and_arm: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> dict[str, Any]:
    if full_arm != "FULL_ZR":
        raise V013ResultVerificationError("V0.13 has only the FULL_ZR candidate")
    return _pair_gate_v013(
        label=label,
        rows=rows,
        pooled_by_arm=pooled_by_arm,
        pooled_by_world_and_arm=pooled_by_world_and_arm,
    )


_recompute_result = _recompute_result_v013


def verify_or_raise(*args: Any, **kwargs: Any) -> dict[str, Any]:
    report = verify_bundle(*args, **kwargs)
    if not report.get("passed"):
        errors = report.get("errors") or ["V0.13 result verification failed"]
        raise V013ResultVerificationError("; ".join(str(error) for error in errors))
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shards", nargs="+", type=Path, required=True)
    parser.add_argument("--merged", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--authority", type=Path, default=DEFAULT_AUTHORITY_PATH)
    parser.add_argument(
        "--no-authority",
        action="store_true",
        help="test-only synthetic mode; do not use for production receipts",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    report = verify_bundle(
        args.shards,
        args.merged,
        repo=args.repo,
        authority_path=args.authority,
        enforce_authority=not args.no_authority,
    )
    print(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True))
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    sys.exit(main())
