#!/usr/bin/env python3
"""Authenticate the isolated R7 package without authorizing or starting work.

The validator reads only repository files. It never opens a TLE archive,
imports the simulator or learner, creates a run directory, or executes a
physical, fit, composition, SSH, or TEST path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from r7_balanced_successor_gate import PROCESS_ENVIRONMENT, STUDENT_SEEDS, WORLDS


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MANIFEST = HERE / "R7-PREFLIGHT-MANIFEST.json"
MANIFEST_SHA = HERE / "R7-PREFLIGHT-MANIFEST.sha256"
MANIFEST_SCHEMA = "multi-catfish-mcrl-v023-r7-balanced-preflight-v1"
CONTRACT = "docs/MULTI-CATFISH-MCRL-V023-LC-SRS-SUCCESSOR-GATE-CONTRACT-R7-BALANCED-2026-09-06.md"
CONTRACT_SHA256 = "027e09a75a2e775b81b570cd49f6637dd10d55220d3ace2cf26a5b37ab002be5"
INITIAL_DIGESTS = {
    "2026135201": "106d23119468eb472babffe78a49c439296a232d8c5481d2aa8cb2890ec08a6f",
    "2026135202": "c726537fd8a309249cbb9eb674ab6c22e663925400112fd01c7a4f790398f56b",
    "2026135203": "016cebc7d0b69a6938a1547c4e400ce3afb2b1cf6e16ce8b6ca72408db427080",
}
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
    "initial_network_sha256_by_seed": dict(INITIAL_DIGESTS),
}
EXPECTED_TLE = {
    "file_set_sha256": "427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9",
    "root_argument": "--tle-root",
    "root_default": "/home/sat/mcrl-runtime/tle-frozen-20260820",
}
EXPECTED_CONFIGURATION_FIELDS = {
    "action_count",
    "base_contract",
    "contract",
    "draw_count",
    "episode_training",
    "execution_addendum",
    "field_component",
    "fit_merged",
    "fit_updates",
    "fold_count",
    "kappa_hex",
    "lambda_hex",
    "learner",
    "lineage",
    "placebo_key",
    "placebo_key_sha256",
    "process_environment",
    "selected_checkpoint",
    "source_adapter",
    "source_artifact_loader",
    "source_artifact_schema",
    "split",
    "steps_per_episode",
    "student_seeds",
    "test_split_opened",
    "tle",
    "users",
    "worlds",
}
EXPECTED_MANIFEST_FIELDS = {
    "bindings",
    "configuration",
    "contract",
    "initial_network_sha256_by_seed",
    "launch",
    "manifest_version",
    "process_environment",
    "schema",
    "status",
    "student_seeds",
    "worlds",
}
LOCAL_PREFIX = ".scratch/multi-catfish-v023-r7-balanced-successor/"
EXPECTED_LOCAL_FILES = {
    "runner": "run_v023_lcsrs_observability_gate.py",
    "preflight": "preflight_r7_balanced.py",
    "preflight_resealer": "reseal_r7_preflight.py",
    "preflight_compat": "preflight_v023_lcsrs_r6.py",
    "preflight_reseal_compat": "reseal_v023_r6_preflight.py",
    "source_server": "run_v023_lcsrs_source_server.py",
    "fit_server": "run_v023_lcsrs_fit_server.py",
    "composition_server": "run_v023_lcsrs_composition_server.py",
    "composition_runtime": "v023_lcsrs_composition_runtime.py",
    "full_gate_server": "run_v023_lcsrs_full_gate_server.sh",
    "server_sync_blocker": "sync_launch_v023_lcsrs_gate_server_r6.sh",
    "server_finalize_blocker": "finalize_v023_lcsrs_gate_server.sh",
    "runtime_source_adapter": "v023_lcsrs_source_adapter.py",
    "runtime_fit_adapter": "v023_lcsrs_fit_adapter.py",
    "runtime_composition_adapter": "v023_lcsrs_composition_adapter.py",
    "scientific_verifier": "verify_v023_lcsrs_scientific.py",
    "source_stage_verifier": "verify_v023_lcsrs_source_stage.py",
    "fit_independent_verifier": "verify_v023_lcsrs_fit_independent.py",
    "final_verifier": "verify_v023_lcsrs_final.py",
    "result_sealer": "seal_v023_lcsrs_result_directory.py",
    "r7_decision": "r7_balanced_successor_gate.py",
    "r7_launch_blocker": "r7_launch_blocker.sh",
    "source_artifact_schema": "SOURCE-ARTIFACT-SCHEMA.md",
    "test_r7_balanced": "test_r7_balanced_successor.py",
    "test_r7_pipeline": "test_r7_pipeline_receipts.py",
    "test_r7_structural": "test_r7_structural_receipts.py",
    "test_source_adapter": "test_v023_lcsrs_source_adapter.py",
    "test_verifier_semantics": "test_v023_r5_verifier_semantics.py",
}
REQUIRED_LOCAL_ROLES = {
    "runner",
    "preflight",
    "preflight_resealer",
    "preflight_compat",
    "preflight_reseal_compat",
    "source_server",
    "fit_server",
    "composition_server",
    "composition_runtime",
    "full_gate_server",
    "server_sync_blocker",
    "server_finalize_blocker",
    "runtime_source_adapter",
    "runtime_fit_adapter",
    "runtime_composition_adapter",
    "scientific_verifier",
    "source_stage_verifier",
    "fit_independent_verifier",
    "final_verifier",
    "result_sealer",
    "r7_decision",
    "r7_launch_blocker",
    "source_artifact_schema",
    "test_r7_balanced",
    "test_r7_pipeline",
    "test_r7_structural",
    "test_source_adapter",
    "test_verifier_semantics",
    "contract",
    "base_contract",
    "execution_parameter_addendum",
    "preregistration",
}
REQUIRED_BOUND_ROLES = REQUIRED_LOCAL_ROLES | {
    "fit_merged",
    "formula",
    "q12_authority",
    "q12_execution_contract",
    "q12_fit_runner",
    "q12_repricing_contract",
    "selected_q1_q2_checkpoint",
    "runtime_action_contract",
    "runtime_antenna",
    "runtime_c3_head",
    "runtime_candidates",
    "runtime_cells",
    "runtime_constants",
    "runtime_d2",
    "runtime_dataset",
    "runtime_dwell",
    "runtime_encoder",
    "runtime_ephemeris",
    "runtime_gate_fit",
    "runtime_gate_metrics",
    "runtime_geometry",
    "runtime_interference",
    "runtime_keyed_fading",
    "runtime_learner",
    "runtime_link_budget",
    "runtime_mobility",
    "runtime_observation_provenance",
    "runtime_ops3_formula",
    "runtime_ops3_live",
    "runtime_pipeline",
    "runtime_placebo",
    "runtime_pointing",
    "runtime_q2_state",
    "runtime_scenario",
    "runtime_service",
    "runtime_source_artifact",
    "runtime_state",
    "runtime_step",
    "runtime_step_types",
    "runtime_teacher",
    "runtime_three_route",
    "runtime_tle",
    "runtime_topology",
    *(f"test_w{number}" for number in range(181, 206)),
}


class R7PreflightError(RuntimeError):
    """The no-launch R7 package or one of its immutable bindings drifted."""


def _sha256(path: Path) -> str:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise R7PreflightError(f"non-regular binding: {target}")
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_sha256(path: Path) -> str:
    """Public no-follow hash helper for focused structural tests."""

    return _sha256(path)


def _canonical_payload(path: Path) -> tuple[dict[str, Any], bytes]:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise R7PreflightError(f"manifest is missing or symlinked: {target}")
    raw = target.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise R7PreflightError("manifest is not canonical ASCII JSON") from error
    if not isinstance(payload, dict):
        raise R7PreflightError("manifest root is not an object")
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    if raw not in (canonical, canonical + b"\n"):
        raise R7PreflightError("manifest is not canonical JSON")
    return payload, raw


def _mapping(value: object, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise R7PreflightError(f"{field} is not an object")
    return value


def _bound_path(repo: Path, relative: object, *, field: str) -> tuple[str, Path]:
    if not isinstance(relative, str) or not relative:
        raise R7PreflightError(f"{field} path is empty")
    value = Path(relative)
    if value.is_absolute() or ".." in value.parts:
        raise R7PreflightError(f"{field} path is not repository-relative")
    root = repo.resolve()
    target = (root / value).resolve()
    if not target.is_relative_to(root):
        raise R7PreflightError(f"{field} path escapes the repository")
    return value.as_posix(), target


def validate_manifest(
    manifest: Path = MANIFEST,
    digest: Path | None = None,
    *,
    manifest_digest_path: Path | None = None,
    repo: Path = REPO,
    prereg_path: Path | None = None,
) -> dict[str, Any]:
    """Validate one complete R7 code/config seal and return a no-launch receipt."""

    if digest is not None and manifest_digest_path is not None:
        raise R7PreflightError("specify only one manifest digest path")
    manifest_path = Path(manifest)
    digest_path = Path(manifest_digest_path or digest or MANIFEST_SHA)
    repo_root = Path(repo).resolve()
    payload, raw = _canonical_payload(manifest_path)
    if set(payload) != EXPECTED_MANIFEST_FIELDS:
        raise R7PreflightError("R7 manifest field set drifted")
    if payload.get("schema") != MANIFEST_SCHEMA or payload.get("manifest_version") != 1:
        raise R7PreflightError("manifest schema/version is not the R7 no-launch seal")
    if payload.get("status") != "DRAFT_PRE_OUTCOME" or payload.get("launch") != "NO_LAUNCH":
        raise R7PreflightError("R7 must remain DRAFT_PRE_OUTCOME / NO_LAUNCH")
    if payload.get("worlds") != list(WORLDS) or payload.get("student_seeds") != list(STUDENT_SEEDS):
        raise R7PreflightError("fresh R7 world or learner seed panel drifted")
    if payload.get("process_environment") != PROCESS_ENVIRONMENT:
        raise R7PreflightError("deterministic process environment drifted")
    if payload.get("contract") != {"path": CONTRACT, "sha256": CONTRACT_SHA256}:
        raise R7PreflightError("R7 contract binding drifted")
    if _sha256(repo_root / CONTRACT) != CONTRACT_SHA256:
        raise R7PreflightError("R7 contract bytes drifted")
    if payload.get("initial_network_sha256_by_seed") != INITIAL_DIGESTS:
        raise R7PreflightError("R7 initial learner parameter digests drifted")

    manifest_sha256 = hashlib.sha256(raw).hexdigest()
    if digest_path.is_symlink() or not digest_path.is_file():
        raise R7PreflightError("manifest digest sidecar is missing or symlinked")
    if digest_path.read_text(encoding="ascii").split() != [
        manifest_sha256,
        manifest_path.name,
    ]:
        raise R7PreflightError("manifest digest sidecar drifted")

    configuration = _mapping(payload.get("configuration"), field="configuration")
    if set(configuration) != EXPECTED_CONFIGURATION_FIELDS:
        raise R7PreflightError("R7 configuration field set drifted")
    expected_configuration = {
        "split": "TRAIN_DEVELOPMENT",
        "test_split_opened": False,
        "episode_training": False,
        "worlds": list(WORLDS),
        "student_seeds": list(STUDENT_SEEDS),
        "steps_per_episode": 10,
        "users": 100,
        "action_count": 28,
        "draw_count": 32,
        "fold_count": 8,
        "fit_updates": 2000,
        "lineage": 2026092101,
        "field_component": "MCRL_V023_LCSRS_C3_OBSERVABILITY_V1",
        "placebo_key": "MCRL_V023_LCSRS_MATCHED_PLACEBO_V1",
        "placebo_key_sha256": "7dc54ab9323b60b30a1bfdbde60872b1f825e4b142dac2c0c0f2269d147a0825",
        "source_artifact_schema": "multi-catfish-mcrl-v023-lcsrs-source-artifact-v1",
        "lambda_hex": "0x1.c3c0a7b6b86d3p+26",
        "kappa_hex": "0x1.2cea89d260f2ap+33",
        "process_environment": PROCESS_ENVIRONMENT,
    }
    for field, expected in expected_configuration.items():
        if configuration.get(field) != expected:
            raise R7PreflightError(f"configuration.{field} drifted")
    learner = _mapping(configuration.get("learner"), field="configuration.learner")
    if dict(learner) != EXPECTED_LEARNER:
        raise R7PreflightError(
            "R7 learner configuration or initial parameter digests drifted"
        )
    tle = _mapping(configuration.get("tle"), field="configuration.tle")
    if dict(tle) != EXPECTED_TLE:
        raise R7PreflightError("configuration TLE binding drifted")

    raw_bindings = payload.get("bindings")
    if not isinstance(raw_bindings, list) or not raw_bindings:
        raise R7PreflightError("manifest has no file bindings")
    bindings: list[dict[str, str]] = []
    roles: set[str] = set()
    paths: set[str] = set()
    for index, raw_binding in enumerate(raw_bindings):
        binding = _mapping(raw_binding, field=f"bindings[{index}]")
        role = binding.get("role")
        if not isinstance(role, str) or not role or role in roles:
            raise R7PreflightError("manifest binding roles are missing or repeated")
        relative, target = _bound_path(repo_root, binding.get("path"), field=role)
        if relative in paths:
            raise R7PreflightError(f"manifest repeats path: {relative}")
        expected_sha = binding.get("sha256")
        if not isinstance(expected_sha, str) or _sha256(target) != expected_sha:
            raise R7PreflightError(f"binding drifted: {relative}")
        roles.add(role)
        paths.add(relative)
        bindings.append({"role": role, "path": relative, "sha256": expected_sha})
    missing = REQUIRED_BOUND_ROLES - roles
    if missing:
        raise R7PreflightError("manifest is missing R7 roles: " + ", ".join(sorted(missing)))
    forbidden_roles = {role for role in roles if "launch_decision" in role or "defect_decision" in role}
    if forbidden_roles:
        raise R7PreflightError("draft R7 manifest contains launch authority")
    for role, filename in EXPECTED_LOCAL_FILES.items():
        match = next(item for item in bindings if item["role"] == role)
        if match["path"] != LOCAL_PREFIX + filename:
            raise R7PreflightError(f"R7 local path drifted for role: {role}")
    expected_external_paths = {
        "contract": CONTRACT,
        "base_contract": "docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md",
        "execution_parameter_addendum": "docs/MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md",
        "preregistration": "artifacts/PREREG-FROZEN-2026-08-25-R2.json",
        "formula": "src/mcrl/runtime/ee_axis_coalition_residual_c3.py",
    }
    for role, expected_path in expected_external_paths.items():
        match = next(item for item in bindings if item["role"] == role)
        if match["path"] != expected_path:
            raise R7PreflightError(f"R7 external path drifted for role: {role}")
    for item in bindings:
        if item["role"].startswith("runtime_") and item["role"] not in EXPECTED_LOCAL_FILES:
            if not item["path"].startswith("src/mcrl/"):
                raise R7PreflightError(
                    f"runtime role escapes the frozen source tree: {item['role']}"
                )
    by_role = {item["role"]: item for item in bindings}
    configuration_links = {
        "contract": "contract",
        "base_contract": "base_contract",
        "execution_addendum": "execution_parameter_addendum",
        "fit_merged": "fit_merged",
        "selected_checkpoint": "selected_q1_q2_checkpoint",
        "source_adapter": "runtime_source_adapter",
        "source_artifact_loader": "runtime_source_artifact",
    }
    for field, role in configuration_links.items():
        declared = _mapping(
            configuration.get(field), field=f"configuration.{field}"
        )
        bound = by_role[role]
        if declared.get("path") != bound["path"] or declared.get("sha256") != bound["sha256"]:
            raise R7PreflightError(
                f"configuration.{field} disagrees with binding role {role}"
            )
    prereg = next(item for item in bindings if item["role"] == "preregistration")
    if prereg_path is not None and Path(prereg_path).resolve() != (repo_root / prereg["path"]).resolve():
        raise R7PreflightError("preregistration argument disagrees with the manifest")

    return {
        "schema": "multi-catfish-mcrl-v023-r7-balanced-no-launch-preflight-receipt-v1",
        "status": "PASS_NO_LAUNCH_PREFLIGHT",
        "manifest_status": "DRAFT_PRE_OUTCOME",
        "launch": "NO_LAUNCH",
        "manifest_file_sha256": manifest_sha256,
        "configuration": dict(configuration),
        "bindings": bindings,
        "worlds": list(WORLDS),
        "student_seeds": list(STUDENT_SEEDS),
        "initial_network_sha256_by_seed": dict(INITIAL_DIGESTS),
        "test_split_opened": False,
        "episode_training": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--manifest-digest", type=Path, default=MANIFEST_SHA)
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
