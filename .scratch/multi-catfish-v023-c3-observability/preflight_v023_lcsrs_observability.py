#!/usr/bin/env python3
"""External, non-circular preflight for the V0.23 LC-SRS gate.

This module intentionally performs no simulator work, opens no TLE archive,
and never imports a learner or a runner.  The companion manifest digest seals
the manifest bytes; the manifest seals this module and the future runner.
Keeping this process independent prevents a runner from authenticating its own
mutable inputs.

The preflight is a source/provenance gate, not a scientific result.  A PASS
only means that the frozen inputs are present and byte-authenticated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MANIFEST_NAME = "PREFLIGHT-MANIFEST.json"
MANIFEST_DIGEST_NAME = "PREFLIGHT-MANIFEST.sha256"
MANIFEST_SCHEMA = "multi-catfish-mcrl-v023-lcsrs-observability-preflight-v1"
MANIFEST_VERSION = 1

EXPECTED_WORLDS = [
    2026121705,
    2026121706,
    2026121707,
    2026121708,
    2026121709,
    2026121710,
    2026121711,
    2026121712,
]
EXPECTED_STUDENT_SEEDS = [2026135101, 2026135102, 2026135103]
EXPECTED_STEPS = 10
EXPECTED_USERS = 100
EXPECTED_ACTIONS = 28
EXPECTED_DRAW_COUNT = 32
EXPECTED_FOLD_COUNT = 8
EXPECTED_FIT_UPDATES = 2000
EXPECTED_LINEAGE = 2026092101
EXPECTED_FIELD_COMPONENT = "MCRL_V023_LCSRS_C3_OBSERVABILITY_V1"
EXPECTED_SPLIT = "TRAIN_DEVELOPMENT"
EXPECTED_LAMBDA_HEX = "0x1.c3c0a7b6b86d3p+26"
EXPECTED_KAPPA_HEX = "0x1.2cea89d260f2ap+33"
EXPECTED_LEARNER = {
    "architecture": "shared-67-64-64-1-reference-centred-q3",
    "arms": ["INFORMED", "MATCHED_PLACEBO"],
    "models": 48,
    "optimizer": "Adam",
    "batch_size": 256,
    "updates": 2000,
    "learning_rate": 0.001,
    "adam_betas": [0.9, 0.999],
    "adam_epsilon": 1.0e-8,
    "weight_decay": 0.0,
    "loss_multiplier": 3.0,
    "sampler": "anchor-uniform-class-uniform-row-uniform-with-replacement",
    "rng": "numpy-pcg64",
    "config_sha256": "6b1c31bb4ccddf19a9e07e13713d2ebb1a4d4555620299257a7a641f0f29111a",
    "initial_network_sha256_by_seed": {
        "2026135101": "278b580b917a0e981f571c5edb2de96f47cc2d0fbd3d5f40218773156ef7a95a",
        "2026135102": "ae0969b16f67691d6a78bc8c6fc06ec29ac839becfdcc731b032e1491531e2e4",
        "2026135103": "d85768fc279d67f8d1982513a858a1be0e5b52403e6de93e9c93e2ae6bc63d68",
    },
}


class V023PreflightError(RuntimeError):
    """An authenticated V0.23 input failed closed."""


def file_sha256(path: Path) -> str:
    """Hash one regular file without following a symlink as the input."""

    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V023PreflightError(f"expected a regular file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
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
        raise V023PreflightError(f"{field} is not a lowercase SHA-256")
    return value


def _canonical_json(path: Path) -> dict[str, Any]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V023PreflightError(f"manifest is missing or non-regular: {source}")
    raw = source.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V023PreflightError("manifest is not canonical ASCII JSON") from error
    if not isinstance(payload, dict):
        raise V023PreflightError("manifest root is not an object")
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    if raw not in (canonical, canonical + b"\n"):
        raise V023PreflightError("manifest is not canonical JSON")
    return payload


def _mapping(value: object, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise V023PreflightError(f"{field} is not an object")
    return value


def _relative_file(value: object, *, field: str, repo: Path) -> tuple[str, Path]:
    if not isinstance(value, str) or not value.strip():
        raise V023PreflightError(f"{field}.path is empty")
    relative = Path(value)
    if relative.is_absolute() or any(part == ".." for part in relative.parts):
        raise V023PreflightError(f"{field}.path must stay repository-relative")
    root = Path(repo).resolve()
    resolved = (root / relative).resolve()
    if not resolved.is_relative_to(root):
        raise V023PreflightError(f"{field}.path escapes the repository")
    return relative.as_posix(), resolved


def _validate_digest_file(path: Path, manifest_digest: str) -> None:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V023PreflightError(f"manifest digest file is missing: {source}")
    lines = source.read_text(encoding="ascii").splitlines()
    if len(lines) != 1:
        raise V023PreflightError("manifest digest file must contain exactly one line")
    parts = lines[0].split()
    if len(parts) != 2 or parts[1] != MANIFEST_NAME:
        raise V023PreflightError("manifest digest file has a noncanonical filename binding")
    if _digest(parts[0], field="manifest_sha256") != manifest_digest:
        raise V023PreflightError("manifest digest file disagrees with manifest bytes")


def _validate_configuration(configuration: Mapping[str, Any]) -> None:
    if configuration.get("split") != EXPECTED_SPLIT:
        raise V023PreflightError("manifest split is not TRAIN_DEVELOPMENT")
    if configuration.get("worlds") != EXPECTED_WORLDS:
        raise V023PreflightError("manifest world panel drifted")
    if configuration.get("student_seeds") != EXPECTED_STUDENT_SEEDS:
        raise V023PreflightError("manifest student seed panel drifted")
    expected = {
        "lineage": EXPECTED_LINEAGE,
        "steps_per_episode": EXPECTED_STEPS,
        "users": EXPECTED_USERS,
        "action_count": EXPECTED_ACTIONS,
        "draw_count": EXPECTED_DRAW_COUNT,
        "fold_count": EXPECTED_FOLD_COUNT,
        "fit_updates": EXPECTED_FIT_UPDATES,
        "field_component": EXPECTED_FIELD_COMPONENT,
        "lambda_hex": EXPECTED_LAMBDA_HEX,
        "kappa_hex": EXPECTED_KAPPA_HEX,
        "test_split_opened": False,
        "episode_training": False,
    }
    for field, expected_value in expected.items():
        if configuration.get(field) != expected_value:
            raise V023PreflightError(
                f"manifest configuration.{field} drifted: "
                f"expected {expected_value!r}, got {configuration.get(field)!r}"
            )
    learner = _mapping(configuration.get("learner"), field="configuration.learner")
    if dict(learner) != EXPECTED_LEARNER:
        raise V023PreflightError(
            "serialized learner configuration or initial parameter digests drifted"
        )
    tle = _mapping(configuration.get("tle"), field="configuration.tle")
    if tle.get("root_argument") != "--tle-root":
        raise V023PreflightError("TLE root argument drifted")
    _digest(tle.get("file_set_sha256"), field="configuration.tle.file_set_sha256")
    if not isinstance(tle.get("root_default"), str) or not tle["root_default"].strip():
        raise V023PreflightError("configuration.tle.root_default is empty")


def validate_manifest(
    manifest_path: Path,
    *,
    manifest_digest_path: Path | None = None,
    repo: Path = REPO,
    prereg_path: Path | None = None,
) -> dict[str, Any]:
    """Validate the frozen manifest and return a serializable receipt.

    This check intentionally does not inspect the external TLE root.  The
    runtime ephemeris validator must authenticate that root after a server
    launch is explicitly authorized.  ``prereg_path`` is optional for unit
    tests but, when supplied, must be the manifest's declared path and digest.
    """

    repo_root = Path(repo).resolve()
    source = Path(manifest_path)
    manifest = _canonical_json(source)
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise V023PreflightError("manifest schema is stale")
    if manifest.get("manifest_version") != MANIFEST_VERSION:
        raise V023PreflightError("manifest version is unsupported")
    manifest_digest = file_sha256(source)
    digest_path = (
        Path(manifest_digest_path)
        if manifest_digest_path is not None
        else source.with_name(MANIFEST_DIGEST_NAME)
    )
    _validate_digest_file(digest_path, manifest_digest)
    configuration = _mapping(manifest.get("configuration"), field="configuration")
    _validate_configuration(configuration)

    bindings_raw = manifest.get("bindings")
    if not isinstance(bindings_raw, list) or not bindings_raw:
        raise V023PreflightError("manifest has no file bindings")
    bindings: list[dict[str, str]] = []
    seen: set[str] = set()
    seen_roles: set[str] = set()
    for index, raw in enumerate(bindings_raw):
        entry = _mapping(raw, field=f"bindings[{index}]")
        role = entry.get("role")
        if not isinstance(role, str) or not role.strip():
            raise V023PreflightError(f"bindings[{index}].role is empty")
        if role in seen_roles:
            raise V023PreflightError(f"manifest repeats file-binding role: {role}")
        seen_roles.add(role)
        relative, resolved = _relative_file(
            entry.get("path"), field=f"bindings[{index}]", repo=repo_root
        )
        if relative in seen:
            raise V023PreflightError(f"manifest repeats file binding: {relative}")
        seen.add(relative)
        expected = _digest(entry.get("sha256"), field=f"bindings[{index}].sha256")
        actual = file_sha256(resolved)
        if actual != expected:
            raise V023PreflightError(
                f"manifest binding drifted for {relative}: expected {expected}, got {actual}"
            )
        bindings.append({"role": role, "path": relative, "sha256": actual})

    by_role = {entry["role"]: entry for entry in bindings}
    required_roles = {
        "runner",
        "preflight",
        "verifier",
        "contract",
        "formula",
        "preregistration",
        "fit_merged",
        "selected_q1_q2_checkpoint",
        "runtime_tle",
        "runtime_ephemeris",
        "runtime_step",
        "runtime_keyed_fading",
        "runtime_observation_provenance",
        "runtime_action_contract",
        "runtime_antenna",
        "runtime_candidates",
        "runtime_cells",
        "runtime_constants",
        "runtime_d2",
        "runtime_dwell",
        "runtime_geometry",
        "runtime_interference",
        "runtime_link_budget",
        "runtime_mobility",
        "runtime_pointing",
        "runtime_scenario",
        "runtime_service",
        "runtime_step_types",
        "runtime_state",
        "runtime_encoder",
        "runtime_topology",
        "runtime_teacher",
        "runtime_dataset",
        "runtime_learner",
        "runtime_placebo",
        "runtime_pipeline",
        "runtime_c3_head",
        "runtime_three_route",
        "source_server",
        "fit_server",
        "composition_server",
        "composition_runtime",
        "full_gate_server",
        "server_sync_launcher",
        "server_finalize",
        "runtime_source_adapter",
        "runtime_fit_adapter",
        "runtime_composition_adapter",
        "runtime_source_artifact",
        "source_artifact_schema",
        "scientific_verifier",
        "source_stage_verifier",
        "fit_independent_verifier",
        "final_verifier",
        "result_sealer",
        "execution_parameter_addendum",
        "launch_decision",
        "relaunch_decision_r4",
        "q12_repricing_contract",
        "q12_execution_contract",
        "q12_authority",
        "q12_fit_runner",
        "runtime_ops3_formula",
        "runtime_ops3_live",
        "runtime_q2_state",
    }
    missing = sorted(required_roles - set(by_role))
    if missing:
        raise V023PreflightError("manifest is missing required roles: " + ", ".join(missing))

    expected_paths = {
        "runner": ".scratch/multi-catfish-v023-c3-observability/run_v023_lcsrs_observability_gate.py",
        "preflight": ".scratch/multi-catfish-v023-c3-observability/preflight_v023_lcsrs_observability.py",
        "verifier": ".scratch/multi-catfish-v023-c3-observability/verify_v023_lcsrs_observability_gate.py",
        "contract": "docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md",
        "formula": "src/mcrl/runtime/ee_axis_coalition_residual_c3.py",
        "preregistration": "artifacts/PREREG-FROZEN-2026-08-25-R2.json",
        "fit_merged": ".scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/merged/result.json",
        "selected_q1_q2_checkpoint": ".scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/lineage-2026092101/checkpoints/lineage-2026092101-q2init-2026108101-rung-003000.pt",
        "runtime_tle": "src/mcrl/env/tle.py",
        "runtime_ephemeris": "src/mcrl/env/ephemeris.py",
        "runtime_step": "src/mcrl/env/step.py",
        "runtime_keyed_fading": "src/mcrl/env/keyed_fading.py",
        "runtime_observation_provenance": "src/mcrl/env/observation_provenance.py",
        "runtime_action_contract": "src/mcrl/env/action_contract.py",
        "runtime_antenna": "src/mcrl/env/antenna.py",
        "runtime_candidates": "src/mcrl/env/candidates.py",
        "runtime_cells": "src/mcrl/env/cells.py",
        "runtime_constants": "src/mcrl/env/constants.py",
        "runtime_d2": "src/mcrl/env/d2.py",
        "runtime_dwell": "src/mcrl/env/dwell.py",
        "runtime_geometry": "src/mcrl/env/geometry.py",
        "runtime_interference": "src/mcrl/env/interference.py",
        "runtime_link_budget": "src/mcrl/env/link_budget.py",
        "runtime_mobility": "src/mcrl/env/mobility.py",
        "runtime_pointing": "src/mcrl/env/pointing.py",
        "runtime_scenario": "src/mcrl/env/scenario.py",
        "runtime_service": "src/mcrl/env/service.py",
        "runtime_step_types": "src/mcrl/env/step_types.py",
        "runtime_state": "src/mcrl/runtime/ee_axis_lcsrs_c3_state.py",
        "runtime_encoder": "src/mcrl/runtime/ee_axis_lcsrs_c3_encoder.py",
        "runtime_topology": "src/mcrl/runtime/ee_axis_lcsrs_c3_topology.py",
        "runtime_teacher": "src/mcrl/runtime/ee_axis_lcsrs_c3_teacher.py",
        "runtime_dataset": "src/mcrl/runtime/ee_axis_lcsrs_c3_dataset.py",
        "runtime_learner": "src/mcrl/runtime/ee_axis_lcsrs_c3_learner.py",
        "runtime_placebo": "src/mcrl/runtime/ee_axis_lcsrs_c3_placebo.py",
        "runtime_pipeline": "src/mcrl/runtime/ee_axis_lcsrs_c3_pipeline.py",
        "runtime_c3_head": "src/mcrl/algorithms/ee_axis_lcsrs_c3_head.py",
        "runtime_three_route": "src/mcrl/algorithms/ee_axis_lcsrs_three_route.py",
        "source_server": ".scratch/multi-catfish-v023-c3-observability/run_v023_lcsrs_source_server.py",
        "fit_server": ".scratch/multi-catfish-v023-c3-observability/run_v023_lcsrs_fit_server.py",
        "composition_server": ".scratch/multi-catfish-v023-c3-observability/run_v023_lcsrs_composition_server.py",
        "composition_runtime": ".scratch/multi-catfish-v023-c3-observability/v023_lcsrs_composition_runtime.py",
        "full_gate_server": ".scratch/multi-catfish-v023-c3-observability/run_v023_lcsrs_full_gate_server.sh",
        "server_sync_launcher": ".scratch/multi-catfish-v023-c3-observability/sync_launch_v023_lcsrs_gate_server.sh",
        "server_finalize": ".scratch/multi-catfish-v023-c3-observability/finalize_v023_lcsrs_gate_server.sh",
        "runtime_source_adapter": ".scratch/multi-catfish-v023-c3-observability/v023_lcsrs_source_adapter.py",
        "runtime_fit_adapter": ".scratch/multi-catfish-v023-c3-observability/v023_lcsrs_fit_adapter.py",
        "runtime_composition_adapter": ".scratch/multi-catfish-v023-c3-observability/v023_lcsrs_composition_adapter.py",
        "runtime_source_artifact": "src/mcrl/runtime/ee_axis_lcsrs_c3_source_artifact.py",
        "source_artifact_schema": ".scratch/multi-catfish-v023-c3-observability/SOURCE-ARTIFACT-SCHEMA.md",
        "scientific_verifier": ".scratch/multi-catfish-v023-c3-observability/verify_v023_lcsrs_scientific.py",
        "source_stage_verifier": ".scratch/multi-catfish-v023-c3-observability/verify_v023_lcsrs_source_stage.py",
        "fit_independent_verifier": ".scratch/multi-catfish-v023-c3-observability/verify_v023_lcsrs_fit_independent.py",
        "final_verifier": ".scratch/multi-catfish-v023-c3-observability/verify_v023_lcsrs_final.py",
        "result_sealer": ".scratch/multi-catfish-v023-c3-observability/seal_v023_lcsrs_result_directory.py",
        "execution_parameter_addendum": "docs/MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md",
        "launch_decision": "docs/MULTI-CATFISH-MCRL-V023-LC-SRS-GATE-LAUNCH-DECISION-2026-09-05.md",
        "relaunch_decision_r4": "docs/MULTI-CATFISH-MCRL-V023-LC-SRS-GATE-RELAUNCH-DECISION-R4-2026-09-06.md",
        "q12_repricing_contract": ".scratch/multi-catfish-v020-c3-source-audit/Q1-Q2-LAMBDA-REPRICING-PREOUTCOME-CONTRACT-2026-09-04.md",
        "q12_execution_contract": ".scratch/multi-catfish-v020-c3-source-audit/Q1-Q2-REPRICED-SUPERVISED-EXECUTION-CONTRACT-2026-09-04.md",
        "q12_authority": ".scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/lineage-2026092101/authority.json",
        "q12_fit_runner": ".scratch/multi-catfish-v020-c3-source-audit/run_v020_repriced_q1_q2.py",
        "runtime_ops3_formula": "src/mcrl/runtime/ee_axis_ops3.py",
        "runtime_ops3_live": "src/mcrl/runtime/ee_axis_ops3_live.py",
        "runtime_q2_state": "src/mcrl/runtime/ee_axis_v014_q2_state.py",
    }
    for role, expected_path in expected_paths.items():
        if by_role[role]["path"] != expected_path:
            raise V023PreflightError(
                f"manifest path for {role} is not frozen: {by_role[role]['path']}"
            )

    fit = _mapping(configuration.get("fit_merged"), field="configuration.fit_merged")
    checkpoint = _mapping(
        configuration.get("selected_checkpoint"),
        field="configuration.selected_checkpoint",
    )
    for declared, role, label in (
        (fit, "fit_merged", "fit_merged"),
        (checkpoint, "selected_q1_q2_checkpoint", "selected_checkpoint"),
    ):
        if declared.get("path") != by_role[role]["path"]:
            raise V023PreflightError(f"configuration.{label}.path disagrees with binding")
        if declared.get("sha256") != by_role[role]["sha256"]:
            raise V023PreflightError(f"configuration.{label}.sha256 disagrees with binding")
    if prereg_path is not None:
        supplied = Path(prereg_path)
        relative, resolved = _relative_file(
            str(supplied), field="preregistration_argument", repo=repo_root
        ) if not supplied.is_absolute() else _relative_file(
            str(supplied.resolve().relative_to(repo_root)),
            field="preregistration_argument",
            repo=repo_root,
        )
        declared = by_role["preregistration"]
        if relative != declared["path"] or file_sha256(resolved) != declared["sha256"]:
            raise V023PreflightError("preregistration argument disagrees with manifest")

    return {
        "schema": "multi-catfish-mcrl-v023-lcsrs-observability-preflight-receipt-v1",
        "status": "PASS",
        "manifest_schema": MANIFEST_SCHEMA,
        "manifest_file_sha256": manifest_digest,
        "manifest_digest_path": str(digest_path.resolve()),
        "configuration": dict(configuration),
        "bindings": bindings,
        "test_split_opened": False,
        "episode_training": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=HERE / MANIFEST_NAME)
    parser.add_argument(
        "--manifest-digest", type=Path, default=HERE / MANIFEST_DIGEST_NAME
    )
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--prereg", type=Path, default=None)
    args = parser.parse_args(argv)
    receipt = validate_manifest(
        args.manifest,
        manifest_digest_path=args.manifest_digest,
        repo=args.repo,
        prereg_path=args.prereg,
    )
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
