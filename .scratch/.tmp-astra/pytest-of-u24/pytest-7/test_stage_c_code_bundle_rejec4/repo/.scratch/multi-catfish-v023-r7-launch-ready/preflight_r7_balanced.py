#!/usr/bin/env python3
"""Fail-closed preflight for the frozen V0.23 LC-SRS R7 launch.

This module authenticates the launch decision, code manifest, repository
bindings, and immutable configuration.  It performs no simulator/TLE access,
learner fit, TEST access, episode training, SSH, or output-root creation.
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
CODE_MANIFEST = HERE / "R7-LAUNCH-CODE-MANIFEST.json"
CODE_MANIFEST_SHA = HERE / "R7-LAUNCH-CODE-MANIFEST.sha256"
MANIFEST_SCHEMA = "multi-catfish-mcrl-v023-r7-balanced-launch-preflight-v1"
CODE_MANIFEST_SCHEMA = "multi-catfish-mcrl-v023-r7-balanced-launch-code-manifest-v1"
LAUNCH_DECISION = "docs/MULTI-CATFISH-MCRL-V023-LC-SRS-R7-LAUNCH-DECISION-2026-09-06.md"
CONTRACT = "docs/MULTI-CATFISH-MCRL-V023-LC-SRS-SUCCESSOR-GATE-CONTRACT-R7-BALANCED-2026-09-06.md"
BASE_CONTRACT = "docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md"
EXECUTION_ADDENDUM = "docs/MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md"
PREREGISTRATION = "artifacts/PREREG-FROZEN-2026-08-25-R2.json"
CONTRACT_SHA256 = "027e09a75a2e775b81b570cd49f6637dd10d55220d3ace2cf26a5b37ab002be5"
TLE_ROOT = "/home/sat/mcrl-runtime/tle-frozen-20260820"
TLE_FILE_SET_SHA256 = "427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9"
OUTPUT_ROOT = "/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1"
TMUX_SESSION = "mcrl-v023-lcsrs-gate-20260906-r7-i1"
CLAIM_CEILING = "TRAIN_DEVELOPMENT_SOURCE_AND_LEARNER_GATE_NO_TEST_NO_EPISODE_TRAINING_NO_EFFICACY"
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

# ``v023_lcsrs_source_adapter._authenticate`` loads these predecessor runners
# through ``importlib.util`` and follows their literal Path-valued provenance
# bindings before any source worker is allowed to open a simulator. An AST
# walk over ``mcrl.*`` imports cannot see this closure, so keep the exact
# repository-relative paths in the launch authority and require every one in
# the transferred code manifest. This list is intentionally narrow: it is
# the files read by the authentication seam, not a copy of the historical
# scratch tree.
REQUIRED_DYNAMIC_SOURCE_PATHS = (
    ".scratch/multi-catfish-v020-c3-source-audit/run_v020_repriced_c3_gate.py",
    ".scratch/multi-catfish-v018-relational-zr/run_v018_analytic_diagnostic.py",
    ".scratch/multi-catfish-v015-c3-learned-context/run_v015_c3_learned_context_oracle.py",
    ".scratch/multi-catfish-v014-learner/run_v014_learner_gate.py",
    ".scratch/zero-energy-c3-v013/run_v013_zero_energy_c3_oracle.py",
    ".scratch/c3-v04/run_v04_c3_500_update_screen.py",
    ".scratch/c3-v04/run_v04_c3_learnability_gate.py",
    ".scratch/c3-v04/run_v04_c3_source.py",
    "scripts/run_head_pivotality_probe.py",
    ".scratch/multi-catfish-v020-c3-source-audit/q1-repricing/reprice_c1.py",
    ".scratch/multi-catfish-v020-c3-source-audit/REPRICED-C3-LAMBDA-CONFOUND-GATE-CONTRACT-2026-09-04.md",
    ".scratch/multi-catfish-v018-relational-zr/contracts/MULTI-CATFISH-MCRL-V018-ANALYTIC-DIAGNOSTIC-PREREG-2026-09-04.md",
    "artifacts/multi-catfish-v015-c3-learned-context-oracle-20260903-r1/contracts/MULTI-CATFISH-MCRL-V015-C3-LEARNED-CONTEXT-ORACLE-PREREG-2026-09-03.md",
    "docs/MULTI-CATFISH-MCRL-V013-ZR-C3-FRESH-CONFIRMATION-PREREG-2026-09-03.md",
    "artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/learner-gate/result.json",
    "artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/learner-gate/authority.json",
    "artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/learner-gate/result-seal.json",
    ".scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/merged/result.json",
    ".scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/lineage-2026092101/checkpoints/lineage-2026092101-q2init-2026108101-rung-003000.pt",
    ".scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/lineage-2026092102/checkpoints/lineage-2026092102-q2init-2026108102-rung-003000.pt",
    ".scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/lineage-2026092103/checkpoints/lineage-2026092103-q2init-2026108103-rung-003000.pt",
    ".scratch/multi-catfish-v020-c3-source-audit/q2-batch-repricing/shards/2026108001-2026092101/q2_target_bits_repriced.npy",
    ".scratch/multi-catfish-v020-c3-source-audit/q2-batch-repricing/shards/2026108002-2026092101/q2_target_bits_repriced.npy",
    ".scratch/multi-catfish-v020-c3-source-audit/q2-batch-repricing/shards/2026108003-2026092101/q2_target_bits_repriced.npy",
    ".scratch/multi-catfish-v020-c3-source-audit/q2-batch-repricing/shards/2026108004-2026092101/q2_target_bits_repriced.npy",
    ".scratch/multi-catfish-v020-c3-source-audit/q2-batch-repricing/shards/2026108005-2026092101/q2_target_bits_repriced.npy",
    ".scratch/multi-catfish-v020-c3-source-audit/q2-batch-repricing/shards/2026108006-2026092101/q2_target_bits_repriced.npy",
    ".scratch/multi-catfish-v020-c3-source-audit/q2-batch-repricing/shards/2026108007-2026092101/q2_target_bits_repriced.npy",
)


class R7PreflightError(RuntimeError):
    """The frozen launch authority or one of its bindings drifted."""


def _sha256(path: Path) -> str:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise R7PreflightError(f"binding is missing, symlinked, or not a file: {target}")
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_sha256(path: Path) -> str:
    return _sha256(path)


def _canonical_json(path: Path) -> tuple[dict[str, Any], bytes]:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise R7PreflightError(f"JSON binding is missing or symlinked: {target}")
    raw = target.read_bytes()
    try:
        value = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise R7PreflightError(f"JSON binding is not canonical ASCII JSON: {target}") from error
    if not isinstance(value, dict):
        raise R7PreflightError(f"JSON binding is not an object: {target}")
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
    if raw not in (canonical, canonical + b"\n"):
        raise R7PreflightError(f"JSON binding is not canonical: {target}")
    return value, raw


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise R7PreflightError(f"{field} is not an object")
    return value


def _repo_path(value: object, *, field: str, repo: Path) -> tuple[str, Path]:
    if not isinstance(value, str) or not value:
        raise R7PreflightError(f"{field} path is empty")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise R7PreflightError(f"{field} path is not repository-relative")
    target = (repo.resolve() / relative).resolve()
    if not target.is_relative_to(repo.resolve()):
        raise R7PreflightError(f"{field} path escapes repository")
    return relative.as_posix(), target


def _digest_sidecar(path: Path, digest: str, expected_name: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise R7PreflightError(f"digest sidecar is missing or symlinked: {path}")
    if path.read_text(encoding="ascii").split() != [digest, expected_name]:
        raise R7PreflightError(f"digest sidecar disagrees: {path}")


def _scan_forbidden_runtime_tokens(value: object) -> None:
    """Reject old R6 schedule identities from executable launch configuration."""

    forbidden = (
        "2026121705", "2026121706", "2026121707", "2026121708",
        "2026121709", "2026121710", "2026121711", "2026121712",
        "2026135101", "2026135102", "2026135103",
        "multi-catfish-v023-r6", "lcsrs-gate-20260906-r6",
        "sync_launch_v023_lcsrs_gate_server_r6",
    )
    if isinstance(value, str):
        if any(token in value for token in forbidden):
            raise R7PreflightError("old R6 world/seed/path entered launch configuration")
    elif isinstance(value, Mapping):
        for item in value.values():
            _scan_forbidden_runtime_tokens(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _scan_forbidden_runtime_tokens(item)


def _validate_code_manifest(path: Path, digest_path: Path, repo: Path) -> tuple[dict[str, Any], str]:
    payload, raw = _canonical_json(path)
    if set(payload) != {"bindings", "manifest_version", "schema", "status", "launch"}:
        raise R7PreflightError("code manifest field set drifted")
    if payload.get("schema") != CODE_MANIFEST_SCHEMA or payload.get("manifest_version") != 1:
        raise R7PreflightError("code manifest schema/version drifted")
    if payload.get("status") != "FROZEN_PRE_OUTCOME" or payload.get("launch") != "AUTHORIZED_ONE_SHOT":
        raise R7PreflightError("code manifest is not frozen for the authorized one-shot")
    bindings = payload.get("bindings")
    if not isinstance(bindings, list) or not bindings:
        raise R7PreflightError("code manifest has no bindings")
    seen_roles: set[str] = set()
    seen_paths: set[str] = set()
    for index, raw_binding in enumerate(bindings):
        item = _mapping(raw_binding, f"code bindings[{index}]")
        role = item.get("role")
        if not isinstance(role, str) or not role or role in seen_roles:
            raise R7PreflightError("code manifest roles are missing or repeated")
        relative, target = _repo_path(item.get("path"), field=f"code bindings[{index}]", repo=repo)
        if relative in seen_paths:
            raise R7PreflightError("code manifest repeats a path")
        declared = item.get("sha256")
        if not isinstance(declared, str) or _sha256(target) != declared:
            raise R7PreflightError(f"code binding hash drifted: {relative}")
        seen_roles.add(role)
        seen_paths.add(relative)
    missing_dynamic = sorted(set(REQUIRED_DYNAMIC_SOURCE_PATHS) - seen_paths)
    if missing_dynamic:
        raise R7PreflightError(
            "code manifest omits dynamic source provenance: "
            + ", ".join(missing_dynamic)
        )
    digest = hashlib.sha256(raw).hexdigest()
    _digest_sidecar(digest_path, digest, path.name)
    return payload, digest


def validate_manifest(
    manifest: Path = MANIFEST,
    digest: Path | None = None,
    *,
    manifest_digest_path: Path | None = None,
    repo: Path = REPO,
    prereg_path: Path | None = None,
) -> dict[str, Any]:
    """Authenticate the complete launch seal without touching runtime data."""

    if digest is not None and manifest_digest_path is not None:
        raise R7PreflightError("specify only one manifest digest path")
    manifest_path = Path(manifest)
    digest_path = Path(manifest_digest_path or digest or MANIFEST_SHA)
    repo_root = Path(repo).resolve()
    payload, raw = _canonical_json(manifest_path)
    expected_fields = {
        "bindings", "code_manifest", "configuration", "contract",
        "initial_network_sha256_by_seed", "launch", "manifest_version",
        "process_environment", "schema", "status", "student_seeds", "worlds",
    }
    if set(payload) != expected_fields:
        raise R7PreflightError("R7 launch manifest field set drifted")
    if payload.get("schema") != MANIFEST_SCHEMA or payload.get("manifest_version") != 1:
        raise R7PreflightError("R7 launch manifest schema/version drifted")
    if payload.get("status") != "FROZEN_PRE_OUTCOME" or payload.get("launch") != "AUTHORIZED_ONE_SHOT":
        raise R7PreflightError("R7 launch manifest is not FROZEN_PRE_OUTCOME/AUTHORIZED_ONE_SHOT")
    if payload.get("worlds") != list(WORLDS) or payload.get("student_seeds") != list(STUDENT_SEEDS):
        raise R7PreflightError("fresh R7 world or learner seed panel drifted")
    if payload.get("process_environment") != PROCESS_ENVIRONMENT:
        raise R7PreflightError("deterministic process environment drifted")
    if payload.get("contract") != {"path": CONTRACT, "sha256": CONTRACT_SHA256}:
        raise R7PreflightError("R7 contract binding drifted")
    if _sha256(repo_root / CONTRACT) != CONTRACT_SHA256:
        raise R7PreflightError("R7 contract bytes drifted")
    if payload.get("initial_network_sha256_by_seed") != INITIAL_DIGESTS:
        raise R7PreflightError("initial network digests drifted")
    manifest_sha256 = hashlib.sha256(raw).hexdigest()
    _digest_sidecar(digest_path, manifest_sha256, manifest_path.name)

    configuration = _mapping(payload.get("configuration"), "configuration")
    expected_config = {
        "split": "TRAIN_DEVELOPMENT",
        "test_split_opened": False,
        "episode_training": False,
        "scientific_efficacy": False,
        "claim_ceiling": CLAIM_CEILING,
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
        "source_jobs": 8,
        "fit_jobs": 8,
        "composition_jobs": 8,
        "output_root": OUTPUT_ROOT,
        "tmux_session": TMUX_SESSION,
        "tle": {"root_argument": "--tle-root", "root_default": TLE_ROOT, "file_set_sha256": TLE_FILE_SET_SHA256},
        "selected_checkpoint_role": "FROZEN_GATE_BACKGROUND_PROVENANCE_ONLY_NOT_CURRENT_LEARNER_INITIALIZATION",
    }
    for field, expected in expected_config.items():
        if configuration.get(field) != expected:
            raise R7PreflightError(f"configuration.{field} drifted")
    learner = _mapping(configuration.get("learner"), "configuration.learner")
    if dict(learner) != EXPECTED_LEARNER:
        raise R7PreflightError("learner configuration or initial digests drifted")
    for required in ("contract", "base_contract", "execution_addendum", "preregistration", "launch_decision", "code_manifest", "selected_checkpoint", "invalid_run_repair"):
        _mapping(configuration.get(required), f"configuration.{required}")

    code_link = _mapping(payload.get("code_manifest"), "code_manifest")
    code_relative, code_path = _repo_path(code_link.get("path"), field="code_manifest", repo=repo_root)
    if code_relative != ".scratch/multi-catfish-v023-r7-launch-ready/R7-LAUNCH-CODE-MANIFEST.json":
        raise R7PreflightError("code manifest path drifted")
    code_sha = code_link.get("sha256")
    if not isinstance(code_sha, str):
        raise R7PreflightError("code manifest digest is malformed")
    _, code_manifest_sha256 = _validate_code_manifest(code_path, repo_root / ".scratch/multi-catfish-v023-r7-launch-ready/R7-LAUNCH-CODE-MANIFEST.sha256", repo_root)
    if code_sha != code_manifest_sha256:
        raise R7PreflightError("code manifest digest disagrees")

    bindings = payload.get("bindings")
    if not isinstance(bindings, list) or not bindings:
        raise R7PreflightError("launch manifest has no bindings")
    by_role: dict[str, dict[str, str]] = {}
    by_path: set[str] = set()
    for index, raw_binding in enumerate(bindings):
        item = _mapping(raw_binding, f"bindings[{index}]")
        role, relative_value = item.get("role"), item.get("path")
        if not isinstance(role, str) or role in by_role:
            raise R7PreflightError("launch binding roles are missing or repeated")
        relative, target = _repo_path(relative_value, field=role, repo=repo_root)
        if relative in by_path:
            raise R7PreflightError("launch manifest repeats a path")
        declared = item.get("sha256")
        if not isinstance(declared, str) or _sha256(target) != declared:
            raise R7PreflightError(f"launch binding hash drifted: {relative}")
        by_role[role] = {"role": role, "path": relative, "sha256": declared}
        by_path.add(relative)

    required_roles = {
        "contract", "base_contract", "execution_parameter_addendum", "preregistration",
        "launch_decision", "code_manifest", "code_manifest_digest", "runner", "preflight",
        "preflight_resealer", "source_server", "fit_server", "composition_server",
        "composition_runtime", "full_gate_server", "sync_launcher", "finalizer",
        "source_adapter", "fit_adapter", "composition_adapter", "scientific_verifier",
        "source_stage_verifier", "fit_independent_verifier", "final_verifier",
        "result_sealer", "r7_decision", "source_artifact_schema", "launch_tests",
        "invalid_run_i0",
        "runtime_package_init", "runtime_algorithms_init", "runtime_env_init",
        "runtime_runtime_init",
    }
    missing = required_roles - set(by_role)
    if missing:
        raise R7PreflightError("launch manifest missing roles: " + ", ".join(sorted(missing)))
    if by_role["launch_decision"]["path"] != LAUNCH_DECISION:
        raise R7PreflightError("launch decision path drifted")
    decision_path = repo_root / LAUNCH_DECISION
    if _sha256(decision_path) != by_role["launch_decision"]["sha256"]:
        raise R7PreflightError("launch decision bytes drifted")
    decision_text = decision_path.read_text(encoding="utf-8")
    required_decision_tokens = (
        "AUTHORIZED_ONE_SHOT", "R6_FAILURE_RETAINED", "NO_TEST", "NO_EPISODE_TRAINING",
        "NO_EFFICACY", OUTPUT_ROOT, TMUX_SESSION, code_manifest_sha256,
        TLE_ROOT, TLE_FILE_SET_SHA256, CONTRACT_SHA256,
        "balanced accuracy", "raw sign accuracy", "one-shot",
    )
    if any(token not in decision_text for token in required_decision_tokens):
        raise R7PreflightError("launch decision is missing a frozen boundary or digest")
    for role, expected_path in (
        ("contract", CONTRACT), ("base_contract", BASE_CONTRACT),
        ("execution_parameter_addendum", EXECUTION_ADDENDUM),
        ("preregistration", PREREGISTRATION),
    ):
        if by_role[role]["path"] != expected_path:
            raise R7PreflightError(f"{role} path drifted")
    if by_role["code_manifest"]["path"] != code_relative:
        raise R7PreflightError("code manifest binding disagrees")
    _scan_forbidden_runtime_tokens(configuration)
    # The preflight module itself contains the forbidden-identity scanner;
    # exclude that validator source from the runtime-entrypoint text scan.
    for role in ("runner", "source_server", "fit_server", "composition_server", "full_gate_server", "sync_launcher", "finalizer"):
        text = (repo_root / by_role[role]["path"]).read_text(encoding="utf-8")
        if "R7_NO_LAUNCH" in text or "r7_launch_blocker" in text or "NO_LAUNCH" in text:
            raise R7PreflightError(f"draft launch blocker remains in {role}")
        if any(token in text for token in ("2026121705", "2026135101", "multi-catfish-v023-r6", "gate-20260906-r6")):
            raise R7PreflightError(f"R6 executable identity remains in {role}")

    # Keep the authenticated configuration and binding table in the receipt.
    # Runtime source consumers need those exact, already-validated values for
    # their TLE and byte-provenance checks.  Omitting them caused the first R7
    # infrastructure attempt to fail before any source outcome was produced.
    return {
        "schema": "multi-catfish-mcrl-v023-r7-balanced-launch-preflight-receipt-v1",
        "status": "PASS_FROZEN_PRE_OUTCOME_PREFLIGHT",
        "manifest_status": "FROZEN_PRE_OUTCOME",
        "launch": "AUTHORIZED_ONE_SHOT",
        "manifest_file_sha256": manifest_sha256,
        "code_manifest_sha256": code_manifest_sha256,
        "launch_decision_path": LAUNCH_DECISION,
        "launch_decision_sha256": by_role["launch_decision"]["sha256"],
        "output_root": OUTPUT_ROOT,
        "tmux_session": TMUX_SESSION,
        "worlds": list(WORLDS),
        "student_seeds": list(STUDENT_SEEDS),
        "initial_network_sha256_by_seed": dict(INITIAL_DIGESTS),
        "configuration": dict(configuration),
        "bindings": list(bindings),
        "claim_ceiling": CLAIM_CEILING,
        "test_split_opened": False,
        "episode_training": False,
        "scientific_efficacy": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--manifest-digest", type=Path, default=MANIFEST_SHA)
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--prereg", type=Path, default=None)
    args = parser.parse_args(argv)
    receipt = validate_manifest(args.manifest, manifest_digest_path=args.manifest_digest, repo=args.repo, prereg_path=args.prereg)
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
