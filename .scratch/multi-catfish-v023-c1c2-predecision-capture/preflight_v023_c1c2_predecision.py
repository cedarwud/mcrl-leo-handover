#!/usr/bin/env python3
"""Read-only preflight for the V0.23 C1/C2 pre-outcome capture contract.

This module is deliberately standard-library only.  It authenticates the
explicit code manifest, verifies the frozen panel and seed domains, and
reruns the original V0.23 preflight.  It never imports NumPy, PyTorch, a
simulator, a TLE reader, a learner, or a capture runner.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Mapping


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CODE_MANIFEST = HERE / "CODE-MANIFEST.json"
V023_MANIFEST = REPO / ".scratch" / "multi-catfish-v023-r6-fit-binding-fix" / "PREFLIGHT-MANIFEST.json"
V023_MANIFEST_DIGEST = V023_MANIFEST.with_name("PREFLIGHT-MANIFEST.sha256")
V023_PREFLIGHT = V023_MANIFEST.with_name("preflight_v023_lcsrs_r6.py")
PREREGISTRATION = REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json"

SCHEMA = "multi-catfish-mcrl-v023-c1-c2-predecision-capture-preflight-v1"
RECEIPT_SCHEMA = "multi-catfish-mcrl-v023-c1-c2-predecision-capture-preflight-receipt-v1"
MANIFEST_SCHEMA = "multi-catfish-mcrl-v023-c1-c2-predecision-code-manifest-v1"
MANIFEST_VERSION = 1
FROZEN_WORLDS = tuple(range(2026121705, 2026121713))
SOURCE_CONCURRENCY = 4
C1_NEUTRAL_SEED = 3733296141
C2_NEUTRAL_SEED = 3936591716
C1_SEED_DOMAIN = (
    "mcrl-v023-c1c2-neutral-seed-v1|route=C1|"
    "panel=v023-train-panel-2026121705-2026121712-predecision"
)
C2_SEED_DOMAIN = (
    "mcrl-v023-c1c2-neutral-seed-v1|route=C2|"
    "panel=v023-train-panel-2026121705-2026121712-predecision"
)
C1_CLUSTER_NEUTRAL_SOURCE_RULE = "c1-cluster-profile-matched-randomized-predecision-v2"
CLAIM_CEILING = "TRAIN_SIMULATOR_SOURCE_TRAVERSAL_C1_DULL_EE_C2_PREDECISION_SINR_NO_LEARNER_NO_TEST_NO_EFFICACY"
TLE_FILE_SET_SHA256 = "427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9"
TLE_ROOT_ARGUMENT = "--tle-root"
TLE_ROOT_DEFAULT = "/home/sat/mcrl-runtime/tle-frozen-20260820"
C2_RELEASE_GRAMMAR = "C2_V0.3B_HOLD_WHILE_LEGAL_MONOTONE_RELEASE"


# This list is intentionally duplicated in code rather than inferred from the
# manifest.  A manifest that omits a required source seam or test therefore
# fails closed instead of defining its own weaker closure.
EXPECTED_BINDINGS: dict[str, str] = {
    "pre_outcome_contract": ".scratch/multi-catfish-v023-c1c2-predecision-capture/PRE-OUTCOME-CONTRACT.md",
    "code_manifest_preflight": ".scratch/multi-catfish-v023-c1c2-predecision-capture/preflight_v023_c1c2_predecision.py",
    "controller": ".scratch/multi-catfish-v023-c1c2-predecision-capture/run_v023_c1c2_predecision_capture_controller.py",
    "server_sync_launcher": ".scratch/multi-catfish-v023-c1c2-predecision-capture/sync_launch_v023_c1c2_predecision_capture_server.sh",
    "bridge": ".scratch/multi-catfish-v023-c1c2-predecision-capture/v023_c1c2_predecision_capture.py",
    "per_world_runner": ".scratch/multi-catfish-v023-c1c2-predecision-capture/run_v023_c1c2_predecision_capture_server.py",
    "panel_merger": ".scratch/multi-catfish-v023-c1c2-predecision-capture/merge_v023_c1c2_predecision_captures.py",
    "v2_materializer": ".scratch/multi-catfish-v023-c1c2-neutral-materialization/materialize_v023_c1c2.py",
    "neutral_adapter": ".scratch/multi-catfish-v023-c1c2-neutral-adapters/v023_c1c2_neutral_adapters.py",
    "source_adapter": ".scratch/multi-catfish-v023-r6-fit-binding-fix/v023_lcsrs_source_adapter.py",
    "c1_selector": "src/mcrl/runtime/ee_axis_c1_selector.py",
    "c1_dull_source": "src/mcrl/runtime/ee_axis_c1_dull_source.py",
    "c2_neutral_source": "src/mcrl/runtime/ee_axis_c2_neutral_source.py",
    "c2_temporal_contract": "src/mcrl/runtime/ee_axis_temporal_pairs.py",
    "c1_selector_test": "tests/test_w47_ee_axis_c1_selector.py",
    "capture_test": ".scratch/multi-catfish-v023-c1c2-predecision-capture/test_v023_c1c2_predecision_capture.py",
    "infrastructure_test": ".scratch/multi-catfish-v023-c1c2-predecision-capture/test_v023_c1c2_predecision_infrastructure.py",
    "neutral_adapter_test": ".scratch/multi-catfish-v023-c1c2-neutral-adapters/test_v023_c1c2_neutral_adapters.py",
    "materializer_test": ".scratch/multi-catfish-v023-c1c2-neutral-materialization/test_materialize_v023_c1c2.py",
    "original_v023_preflight": ".scratch/multi-catfish-v023-r6-fit-binding-fix/preflight_v023_lcsrs_r6.py",
    "original_v023_manifest": ".scratch/multi-catfish-v023-r6-fit-binding-fix/PREFLIGHT-MANIFEST.json",
    "original_v023_manifest_digest": ".scratch/multi-catfish-v023-r6-fit-binding-fix/PREFLIGHT-MANIFEST.sha256",
    "original_v023_scaffold_test": ".scratch/multi-catfish-v023-r6-fit-binding-fix/test_v023_lcsrs_r5_scaffold.py",
    "original_v023_source_adapter_test": ".scratch/multi-catfish-v023-r6-fit-binding-fix/test_v023_lcsrs_source_adapter.py",
    "original_v023_preregistration": "artifacts/PREREG-FROZEN-2026-08-25-R2.json",
}

EXPECTED_CONFIGURATION: dict[str, Any] = {
    "claim_ceiling": CLAIM_CEILING,
    "source_split": "TRAIN",
    "worlds": list(FROZEN_WORLDS),
    "world_count": 8,
    "source_concurrency": SOURCE_CONCURRENCY,
    "panel_neutral_seeds": {
        "C1": {"seed": C1_NEUTRAL_SEED, "derivation_domain": C1_SEED_DOMAIN},
        "C2": {"seed": C2_NEUTRAL_SEED, "derivation_domain": C2_SEED_DOMAIN},
    },
    "q1_q2_reference": {
        "source_adapter_seam": "_native_q12_anchor",
        "surface": "native float32 Q1+Q2",
        "selection": "native masked argmax with lowest action-index tie",
        "candidate_evaluation": False,
    },
    "c1": {
        "anchors_per_world": 10,
        "evaluation_seam": "capture_c1_dull_rollout_sample",
        "live_state_rng_guard": "equal_before_after_digest",
        "retained": [
            "frontier_score",
            "user_frontier_scores",
            "reference_actions",
            "slot_tables",
            "state_sha256",
            "source_seed",
            "step_index",
        ],
        "neutral_source_rule": C1_CLUSTER_NEUTRAL_SOURCE_RULE,
        "target_or_outcome_retained": False,
    },
    "c2": {
        "departure_steps": list(range(1, 10)),
        "departure_identity": "(norad_id, cell_id)",
        "reference": "native Q1+Q2 masked argmax",
        "hold_if_legal": "incumbent-hold",
        "fallback": "max-lagged-candidate-sinr-rival",
        "tie_break": ["candidate_sinr_desc", "norad_id_asc", "cell_id_asc", "action_asc"],
        "horizon_steps": 4,
        "release_grammar": C2_RELEASE_GRAMMAR,
        "candidate_execution": False,
        "target_or_outcome_retained": False,
    },
    "v2": {
        "capture_schema": "multi-catfish-mcrl-v023-c1-c2-predecision-capture-v2",
        "materialization_schema": "multi-catfish-mcrl-v023-c1-c2-materialization-v2",
        "canonical_json": "ASCII compact sorted keys with one final newline",
        "shared_c2_digest": "materialize_v023_c1c2.py:c2_anchor_sha256",
        "sha256_fields": "lowercase 64-hex",
    },
    "stage_order": [
        "inherited_v023_preflight",
        "eight_per_world_write_once_captures",
        "one_panel_merge",
        "one_v2_materialization",
        "hash_seal",
        "complete_marker",
    ],
    "write_once": {
        "world_captures": True,
        "panel_capture": True,
        "materialization_directory": True,
        "seal_files": True,
        "fresh_server_root": True,
        "fresh_tmux_session": True,
    },
    "controls": {
        "learner_update": False,
        "episode_policy_training": False,
        "test_split_opened": False,
        "evaluation": False,
        "efficacy_claim": False,
        "target_outcomes_persisted": False,
    },
    "v023_preflight": {
        "validator": EXPECTED_BINDINGS["original_v023_preflight"],
        "manifest": EXPECTED_BINDINGS["original_v023_manifest"],
        "manifest_digest": EXPECTED_BINDINGS["original_v023_manifest_digest"],
        "preregistration": EXPECTED_BINDINGS["original_v023_preregistration"],
    },
    "tle_identity": {
        "manifest": EXPECTED_BINDINGS["original_v023_manifest"],
        "file_set_sha256": TLE_FILE_SET_SHA256,
        "root_argument": TLE_ROOT_ARGUMENT,
        "root_default": TLE_ROOT_DEFAULT,
    },
    "outputs": {
        "world_pattern": "world-captures/world-{world}.json",
        "panel_capture": "panel-capture.json",
        "materialized_directory": "materialized-source",
        "seal_manifest": "MANIFEST.sha256",
        "complete_marker": "COMPLETE",
    },
}


class PredecisionPreflightError(RuntimeError):
    """A frozen source input or contract binding failed closed."""


def file_sha256(path: Path) -> str:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise PredecisionPreflightError(f"expected a regular file: {target}")
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise PredecisionPreflightError(f"{field} is not a lowercase SHA-256")
    return value


def _canonical_json(path: Path, *, field: str) -> dict[str, Any]:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise PredecisionPreflightError(f"{field} is missing or symlinked: {target}")
    pairs: list[tuple[str, object]] = []

    def reject_duplicates(raw_pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in raw_pairs:
            if key in result:
                raise PredecisionPreflightError(f"{field} repeats JSON key {key}")
            result[key] = value
        pairs.extend(raw_pairs)
        return result

    try:
        raw = target.read_bytes()
        payload = json.loads(raw.decode("ascii"), object_pairs_hook=reject_duplicates)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PredecisionPreflightError(f"{field} is not ASCII JSON") from error
    if not isinstance(payload, dict):
        raise PredecisionPreflightError(f"{field} root is not an object")
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    if raw != canonical + b"\n":
        raise PredecisionPreflightError(f"{field} is not canonical compact JSON")
    return payload


def _relative_file(value: object, *, field: str, repo: Path) -> tuple[str, Path]:
    if not isinstance(value, str) or not value.strip():
        raise PredecisionPreflightError(f"{field}.path is empty")
    relative = Path(value)
    if relative.is_absolute() or any(part in ("", ".", "..") for part in relative.parts):
        raise PredecisionPreflightError(f"{field}.path must be a clean repository-relative path")
    root = Path(repo).resolve()
    candidate = root / relative
    if candidate.is_symlink() or not candidate.is_file():
        raise PredecisionPreflightError(f"{field}.path must name a regular non-symlink file")
    resolved = candidate.resolve(strict=False)
    if not resolved.is_relative_to(root):
        raise PredecisionPreflightError(f"{field}.path escapes the repository")
    return relative.as_posix(), resolved


def _module(name: str, path: Path) -> ModuleType:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise PredecisionPreflightError(f"required preflight module is missing: {target}")
    spec = importlib.util.spec_from_file_location(name, target)
    if spec is None or spec.loader is None:
        raise PredecisionPreflightError(f"cannot load preflight module: {target}")
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    try:
        spec.loader.exec_module(loaded)
    except Exception as error:
        raise PredecisionPreflightError(f"original V0.23 preflight import failed: {target}") from error
    return loaded


def _clean_path(value: Path, *, field: str) -> Path:
    target = Path(value)
    if not target.is_absolute():
        target = (Path.cwd() / target).resolve(strict=False)
    if target.is_symlink() or not target.is_file():
        raise PredecisionPreflightError(f"{field} must be a regular file: {target}")
    return target.resolve()


def _validate_configuration(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping) or dict(value) != EXPECTED_CONFIGURATION:
        raise PredecisionPreflightError("pre-outcome configuration drifted from the frozen contract")
    return dict(value)


def validate_code_manifest(
    manifest_path: Path = CODE_MANIFEST,
    *,
    repo: Path = REPO,
    v023_manifest: Path = V023_MANIFEST,
    v023_manifest_digest: Path = V023_MANIFEST_DIGEST,
    v023_preflight: Path = V023_PREFLIGHT,
    preregistration: Path = PREREGISTRATION,
    expected_manifest_sha256: str | None = None,
) -> dict[str, Any]:
    """Authenticate the local code manifest and rerun original V0.23 preflight."""

    repo_root = Path(repo).resolve()
    if not repo_root.is_dir() or repo_root.is_symlink():
        raise PredecisionPreflightError(f"repository root is missing or symlinked: {repo_root}")
    source = _clean_path(Path(manifest_path), field="code manifest")
    manifest_sha256 = file_sha256(source)
    if expected_manifest_sha256 is not None and manifest_sha256 != _digest(
        expected_manifest_sha256, field="expected code manifest SHA-256"
    ):
        raise PredecisionPreflightError("code manifest bytes disagree with expected SHA-256")
    manifest = _canonical_json(source, field="code manifest")
    if set(manifest) != {"schema", "manifest_version", "bindings", "configuration"}:
        raise PredecisionPreflightError("code manifest top-level keys drifted")
    if manifest.get("schema") != MANIFEST_SCHEMA or manifest.get("manifest_version") != MANIFEST_VERSION:
        raise PredecisionPreflightError("code manifest schema/version is stale")
    configuration = _validate_configuration(manifest.get("configuration"))

    raw_bindings = manifest.get("bindings")
    if not isinstance(raw_bindings, list):
        raise PredecisionPreflightError("code manifest bindings must be an array")
    by_role: dict[str, dict[str, str]] = {}
    by_path: set[str] = set()
    for index, raw in enumerate(raw_bindings):
        if not isinstance(raw, Mapping) or set(raw) != {"path", "role", "sha256"}:
            raise PredecisionPreflightError(f"bindings[{index}] has unsupported keys")
        role = raw.get("role")
        if not isinstance(role, str) or not role.strip() or role in by_role:
            raise PredecisionPreflightError(f"bindings[{index}] role is empty or repeated")
        relative, resolved = _relative_file(raw.get("path"), field=f"bindings[{index}]", repo=repo_root)
        if relative in by_path:
            raise PredecisionPreflightError(f"code manifest repeats path {relative}")
        by_path.add(relative)
        expected = _digest(raw.get("sha256"), field=f"bindings[{index}].sha256")
        actual = file_sha256(resolved)
        if actual != expected:
            raise PredecisionPreflightError(
                f"code binding drifted for {relative}: expected {expected}, got {actual}"
            )
        by_role[role] = {"role": role, "path": relative, "sha256": actual}
    if set(by_role) != set(EXPECTED_BINDINGS):
        missing = sorted(set(EXPECTED_BINDINGS) - set(by_role))
        extra = sorted(set(by_role) - set(EXPECTED_BINDINGS))
        raise PredecisionPreflightError(f"code manifest binding roles drifted: missing={missing}, extra={extra}")
    for role, expected_path in EXPECTED_BINDINGS.items():
        if by_role[role]["path"] != expected_path:
            raise PredecisionPreflightError(
                f"code manifest path for {role} is not frozen: {by_role[role]['path']}"
            )

    manifest_path_for_call = _clean_path(Path(v023_manifest), field="original V0.23 manifest")
    digest_path_for_call = _clean_path(
        Path(v023_manifest_digest), field="original V0.23 manifest digest"
    )
    preflight_path_for_call = _clean_path(Path(v023_preflight), field="original V0.23 preflight")
    prereg_path_for_call = _clean_path(Path(preregistration), field="frozen preregistration")
    expected_paths = {
        "original_v023_manifest": manifest_path_for_call,
        "original_v023_manifest_digest": digest_path_for_call,
        "original_v023_preflight": preflight_path_for_call,
        "original_v023_preregistration": prereg_path_for_call,
    }
    for role, path in expected_paths.items():
        relative = path.relative_to(repo_root).as_posix()
        if relative != by_role[role]["path"]:
            raise PredecisionPreflightError(f"{role} argument disagrees with code manifest")
    declared_v023 = configuration["v023_preflight"]
    if declared_v023["manifest"] != by_role["original_v023_manifest"]["path"]:
        raise PredecisionPreflightError("configuration.v023_preflight.manifest disagrees")
    if declared_v023["manifest_digest"] != by_role["original_v023_manifest_digest"]["path"]:
        raise PredecisionPreflightError("configuration.v023_preflight.manifest_digest disagrees")
    if declared_v023["validator"] != by_role["original_v023_preflight"]["path"]:
        raise PredecisionPreflightError("configuration.v023_preflight.validator disagrees")
    if declared_v023["preregistration"] != by_role["original_v023_preregistration"]["path"]:
        raise PredecisionPreflightError("configuration.v023_preflight.preregistration disagrees")

    original = _module("mcrl_v023_original_preflight_for_c1c2", preflight_path_for_call)
    validate = getattr(original, "validate_manifest", None)
    if not callable(validate):
        raise PredecisionPreflightError("original V0.23 preflight exposes no validate_manifest")
    try:
        inherited = validate(
            manifest_path_for_call,
            manifest_digest_path=digest_path_for_call,
            repo=repo_root,
            prereg_path=prereg_path_for_call,
        )
    except Exception as error:
        raise PredecisionPreflightError("original V0.23 preflight failed") from error
    if not isinstance(inherited, Mapping) or inherited.get("status") != "PASS":
        raise PredecisionPreflightError("original V0.23 preflight did not return PASS")
    inherited_configuration = inherited.get("configuration")
    if not isinstance(inherited_configuration, Mapping):
        raise PredecisionPreflightError("original V0.23 preflight omitted configuration")
    tle = inherited_configuration.get("tle")
    if not isinstance(tle, Mapping) or {
        "file_set_sha256": tle.get("file_set_sha256"),
        "root_argument": tle.get("root_argument"),
        "root_default": tle.get("root_default"),
    } != {
        "file_set_sha256": TLE_FILE_SET_SHA256,
        "root_argument": TLE_ROOT_ARGUMENT,
        "root_default": TLE_ROOT_DEFAULT,
    }:
        raise PredecisionPreflightError("original V0.23 TLE identity drifted")
    if inherited.get("manifest_file_sha256") != by_role["original_v023_manifest"]["sha256"]:
        raise PredecisionPreflightError("original V0.23 manifest receipt digest disagrees")

    return {
        "schema": RECEIPT_SCHEMA,
        "status": "PASS",
        "code_manifest_sha256": manifest_sha256,
        "configuration": configuration,
        "bindings": [by_role[role] for role in sorted(by_role)],
        "inherited_v023_preflight": {
            "status": "PASS",
            "manifest_sha256": inherited["manifest_file_sha256"],
            "manifest_digest_path": str(digest_path_for_call),
            "tle_file_set_sha256": TLE_FILE_SET_SHA256,
            "tle_root_argument": TLE_ROOT_ARGUMENT,
            "tle_root_default": TLE_ROOT_DEFAULT,
        },
        "controls": configuration["controls"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=CODE_MANIFEST)
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--v023-manifest", type=Path, default=V023_MANIFEST)
    parser.add_argument("--v023-manifest-digest", type=Path, default=V023_MANIFEST_DIGEST)
    parser.add_argument("--v023-preflight", type=Path, default=V023_PREFLIGHT)
    parser.add_argument("--prereg", type=Path, default=PREREGISTRATION)
    parser.add_argument("--code-manifest-sha256", "--manifest-sha256", dest="expected_manifest_sha256")
    args = parser.parse_args(argv)
    try:
        receipt = validate_code_manifest(
            args.manifest,
            repo=args.repo,
            v023_manifest=args.v023_manifest,
            v023_manifest_digest=args.v023_manifest_digest,
            v023_preflight=args.v023_preflight,
            preregistration=args.prereg,
            expected_manifest_sha256=args.expected_manifest_sha256,
        )
    except (PredecisionPreflightError, OSError) as error:
        print(f"PREDECISION_PREFLIGHT_BLOCKED: {error}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


__all__ = [
    "C1_NEUTRAL_SEED",
    "C1_CLUSTER_NEUTRAL_SOURCE_RULE",
    "C1_SEED_DOMAIN",
    "C2_NEUTRAL_SEED",
    "C2_SEED_DOMAIN",
    "CLAIM_CEILING",
    "CODE_MANIFEST",
    "EXPECTED_BINDINGS",
    "EXPECTED_CONFIGURATION",
    "FROZEN_WORLDS",
    "PredecisionPreflightError",
    "SOURCE_CONCURRENCY",
    "file_sha256",
    "main",
    "validate_code_manifest",
]


if __name__ == "__main__":
    raise SystemExit(main())
