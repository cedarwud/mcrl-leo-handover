#!/usr/bin/env python3
"""Independent, fail-closed verifier for the V0.12 oracle result.

This module is intentionally a receipt verifier, not a second runner.  It
does not import the V0.12 runner (or any of its gate helpers), open a simulator
environment, load a learner, or inspect a training log.  It authenticates the
18 immutable shard receipts and recomputes the result-level arithmetic and
acceptance decision from their rows.

The verifier is useful on a copied result bundle as well as in a CI test.  A
normal invocation is::

    python verify_v012_zero_energy_c3_result.py \
      --shards /path/to/run-v012/shards/*/shard.json \
      --merged /path/to/run-v012/merged/result.json

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


REPO = Path(__file__).resolve().parents[2]

RESULT_SCHEMA = "multi-catfish-mcrl-v012-zero-energy-c3-oracle-result-v1"
EPISODE_SCHEMA = "multi-catfish-mcrl-v012-zero-energy-c3-oracle-episode-v1"
SHARD_SCHEMA = "multi-catfish-mcrl-v012-zero-energy-c3-oracle-shard-v1"
CONTRACT_SCHEMA = "multi-catfish-mcrl-v012-zero-energy-c3-oracle-contract-v1"

WORLD_SEEDS = (2026104801, 2026104802)
LINEAGES = (2026092101, 2026092102, 2026092103)
ARMS = ("DROP_C3", "FULL_ZR", "FULL_HR")
USERS = 100
STEPS_PER_EPISODE = 10
FIELD_COMPONENT = "MCRL_V012_ZERO_ENERGY_C3_ORACLE_V1"
FIELD_EXCLUDES = (
    "arm",
    "initialization_seed",
    "policy_label",
    "action",
    "target",
    "outcome",
)
FROZEN_STATUS = "Status: **FROZEN BEFORE OUTCOME ACCESS**"

DEFAULT_CONTRACT_PATH = (
    REPO
    / "docs"
    / "MULTI-CATFISH-MCRL-V012-ZERO-ENERGY-C3-ORACLE-PREREG-2026-09-03.md"
)
DEFAULT_RUNNER_PATH = (
    REPO
    / ".scratch"
    / "zero-energy-c3-v012"
    / "run_v012_zero_energy_c3_oracle.py"
)
DEFAULT_PREREG_PATH = REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json"
DEFAULT_RUNTIME_PATHS = (
    REPO / "src" / "mcrl" / "runtime" / "ee_axis_ops3.py",
    REPO / "src" / "mcrl" / "runtime" / "ee_axis_ops3_live.py",
    REPO / "src" / "mcrl" / "runtime" / "ee_axis_zero_marginal_c3.py",
    REPO / "src" / "mcrl" / "runtime" / "ee_axis_zero_marginal_c3_live.py",
)
DEFAULT_SOURCE_ROOTS = (
    REPO / "src" / "mcrl",
    REPO / ".scratch" / "c3-v04",
    REPO / "scripts",
)

# The V0.12 runner carries only the frozen Q1 head receipt, not a second copy
# of the checkpoint bytes.  These values are the sealed V0.3 source authority
# that the receipt must name.  Keeping them here makes this verifier
# independent of the V0.12 producer and lets it reject a receipt that merely
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


class V012ResultVerificationError(RuntimeError):
    """A receipt, authority, arithmetic, or gate check failed closed."""


def _canonical_bytes(value: object) -> bytes:
    """Return the exact JSON byte convention used by the V0.12 receipts."""

    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V012ResultVerificationError(
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


def expected_contract() -> dict[str, Any]:
    """Reconstruct the frozen contract independently of the V0.12 runner."""

    return {
        "schema": CONTRACT_SCHEMA,
        "world_seeds": list(WORLD_SEEDS),
        "lineages": list(LINEAGES),
        "arms": list(ARMS),
        "arm_heads": {
            "DROP_C3": ["Q1", "O2_OPS3"],
            "FULL_ZR": ["Q1", "O2_OPS3", "O3_ZR"],
            "FULL_HR": ["Q1", "O2_OPS3", "O3_HR"],
        },
        "candidate_order": ["ZR", "HR"],
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
        "zero_marginal_c3_schema": (
            "multi-catfish-mcrl-v012-zero-marginal-c3-surface-v1"
        ),
        "zero_marginal_c3_live_schema": (
            "multi-catfish-mcrl-v012-zero-energy-c3-live-measurement-v1"
        ),
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
            "active_beam_steps_not_above_pooled_or_world": True,
            "active_satellite_steps_not_above_pooled_or_world": True,
            "nonzero_supported_positive_spread": True,
            "nonzero_executed_action_exposure": True,
            "every_changed_action_compatible": True,
            "executed_joint_adds_no_beam_or_satellite": True,
            "executed_joint_network_power_nonincrease": True,
        },
        "selection_table": {
            "ZR": "GO_ZR_C3_LEARNABILITY_PREREG_ONLY",
            "not_ZR_and_HR": "GO_HR_C3_LEARNABILITY_PREREG_ONLY",
            "none": "STOP_C3_ORACLE_REDESIGN_REVIEW_SEAM",
        },
    }


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
            full_arm="FULL_HR",
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


def verify_or_raise(*args: Any, **kwargs: Any) -> dict[str, Any]:
    report = verify_bundle(*args, **kwargs)
    if not report.get("passed"):
        errors = report.get("errors") or ["V0.12 result verification failed"]
        raise V012ResultVerificationError("; ".join(str(error) for error in errors))
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shards", nargs="+", type=Path, required=True)
    parser.add_argument("--merged", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--contract", type=Path, default=None)
    parser.add_argument("--runner", type=Path, default=None)
    parser.add_argument("--prereg", type=Path, default=None)
    parser.add_argument("--tle-root", type=Path, required=True)
    parser.add_argument("--v03-root", type=Path, required=True)
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
        contract_path=args.contract,
        runner_path=args.runner,
        prereg_path=args.prereg,
        tle_root=args.tle_root,
        v03_root=args.v03_root,
        enforce_authority=not args.no_authority,
    )
    print(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True))
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    sys.exit(main())
