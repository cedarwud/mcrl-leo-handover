#!/usr/bin/env python3
"""Build the immutable R7 launch-code and preflight manifests.

This is a release-time tool.  It has no server, simulator, TLE, TEST, fit, or
episode-training path.  The code manifest intentionally excludes the launch
decision and both manifests, avoiding a circular digest; the preflight
manifest binds those three files separately.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import preflight_r7_balanced as authority


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PREFIX = ".scratch/multi-catfish-v023-r7-launch-ready"
DRAFT_MANIFEST = REPO / ".scratch/multi-catfish-v023-r7-balanced-successor/R7-PREFLIGHT-MANIFEST.json"
CODE_MANIFEST = HERE / "R7-LAUNCH-CODE-MANIFEST.json"
CODE_DIGEST = HERE / "R7-LAUNCH-CODE-MANIFEST.sha256"
PREFLIGHT_MANIFEST = HERE / "R7-PREFLIGHT-MANIFEST.json"
PREFLIGHT_DIGEST = HERE / "R7-PREFLIGHT-MANIFEST.sha256"

LOCAL_BINDINGS = {
    "runner": "run_v023_lcsrs_observability_gate.py",
    "preflight": "preflight_r7_balanced.py",
    "preflight_resealer": "reseal_r7_preflight.py",
    "source_server": "run_v023_lcsrs_source_server.py",
    "fit_server": "run_v023_lcsrs_fit_server.py",
    "composition_server": "run_v023_lcsrs_composition_server.py",
    "composition_runtime": "v023_lcsrs_composition_runtime.py",
    "full_gate_server": "run_v023_lcsrs_full_gate_server.sh",
    "sync_launcher": "sync_launch_v023_lcsrs_gate_server_r7.sh",
    "finalizer": "finalize_v023_lcsrs_gate_server_r7.sh",
    "source_adapter": "v023_lcsrs_source_adapter.py",
    "fit_adapter": "v023_lcsrs_fit_adapter.py",
    "composition_adapter": "v023_lcsrs_composition_adapter.py",
    "scientific_verifier": "verify_v023_lcsrs_scientific.py",
    "source_stage_verifier": "verify_v023_lcsrs_source_stage.py",
    "fit_independent_verifier": "verify_v023_lcsrs_fit_independent.py",
    "final_verifier": "verify_v023_lcsrs_final.py",
    "result_sealer": "seal_v023_lcsrs_result_directory.py",
    "r7_decision": "r7_balanced_successor_gate.py",
    "source_artifact_schema": "SOURCE-ARTIFACT-SCHEMA.md",
    "launch_tests": "test_r7_launch_ready.py",
    "invalid_run_i0": "R7-INVALID-RUN-I0.json",
}

PACKAGE_BINDINGS = {
    "runtime_package_init": "src/mcrl/__init__.py",
    "runtime_algorithms_init": "src/mcrl/algorithms/__init__.py",
    "runtime_env_init": "src/mcrl/env/__init__.py",
    "runtime_runtime_init": "src/mcrl/runtime/__init__.py",
    "runtime_dependency_action_shared": "src/mcrl/algorithms/ee_axis_action_shared.py",
    "runtime_dependency_action_shared_meanmax": "src/mcrl/algorithms/ee_axis_action_shared_meanmax.py",
    "runtime_dependency_pairwise": "src/mcrl/algorithms/ee_axis_pairwise.py",
    "runtime_dependency_v014_head": "src/mcrl/algorithms/ee_axis_v014_head.py",
    "runtime_dependency_errors": "src/mcrl/errors.py",
    "runtime_dependency_bessel": "src/mcrl/runtime/bessel.py",
    "runtime_dependency_ee_axis_state": "src/mcrl/runtime/ee_axis_state.py",
    "runtime_dependency_v014_learnability": "src/mcrl/runtime/ee_axis_v014_learnability.py",
    "runtime_dependency_v04_c3_learnability": "src/mcrl/runtime/ee_axis_v04_c3_learnability.py",
    "runtime_dependency_v04_c3_dataset": "src/mcrl/runtime/ee_axis_v04_c3_dataset.py",
    "runtime_dependency_v04_c3_opening_source": "src/mcrl/runtime/ee_axis_v04_c3_opening_source.py",
    "runtime_dependency_v04_c3_schedule": "src/mcrl/runtime/ee_axis_v04_c3_schedule.py",
    "runtime_dependency_v04_c3_selector": "src/mcrl/runtime/ee_axis_v04_c3_selector.py",
    "runtime_dependency_v04_c3_state": "src/mcrl/runtime/ee_axis_v04_c3_state.py",
    "runtime_dependency_v04_hybrid": "src/mcrl/algorithms/ee_axis_v04_hybrid.py",
    "runtime_dependency_v014_gate": "src/mcrl/runtime/ee_axis_v014_gate.py",
    "runtime_dependency_v014_q3_state": "src/mcrl/runtime/ee_axis_v014_q3_state.py",
    "runtime_dependency_v018_gate": "src/mcrl/runtime/ee_axis_v018_gate.py",
    "runtime_dependency_artifacts_init": "src/mcrl/artifacts/__init__.py",
    "runtime_dependency_artifacts_io": "src/mcrl/artifacts/io.py",
    "runtime_dependency_artifacts_models": "src/mcrl/artifacts/models.py",
    "runtime_dependency_collapse_metrics": "src/mcrl/runtime/collapse_metrics.py",
    "runtime_dependency_ee_axis_opening_pairs": "src/mcrl/runtime/ee_axis_opening_pairs.py",
    "runtime_dependency_relational_zr": "src/mcrl/runtime/ee_axis_relational_zr_c3.py",
    "runtime_dependency_zero_marginal": "src/mcrl/runtime/ee_axis_zero_marginal_c3.py",
    "runtime_dependency_zero_marginal_live": "src/mcrl/runtime/ee_axis_zero_marginal_c3_live.py",
    "runtime_dependency_ee_surplus_targets": "src/mcrl/runtime/ee_surplus_targets.py",
    "runtime_dependency_head_pivotality": "src/mcrl/runtime/head_pivotality.py",
    "runtime_dependency_objective_math": "src/mcrl/runtime/objective_math.py",
    "runtime_dependency_prereg": "src/mcrl/runtime/prereg.py",
    "runtime_dependency_probe_p6": "src/mcrl/runtime/probe_p6.py",
    "runtime_dependency_replay_buffer": "src/mcrl/runtime/replay_buffer.py",
    "runtime_dependency_reward_calibration": "src/mcrl/runtime/reward_calibration.py",
    "runtime_dependency_trainer_env": "src/mcrl/runtime/trainer_env.py",
    "runtime_dependency_training_pipeline": "src/mcrl/runtime/training_pipeline.py",
    "runtime_dependency_modqn": "src/mcrl/algorithms/modqn.py",
    "runtime_dependency_energy_efficiency": "src/mcrl/runtime/energy_efficiency.py",
    "runtime_dependency_finiteness": "src/mcrl/runtime/finiteness.py",
    "runtime_dependency_q_network": "src/mcrl/runtime/q_network.py",
    "runtime_dependency_state_encoding": "src/mcrl/runtime/state_encoding.py",
    "runtime_dependency_trainer_config": "src/mcrl/runtime/trainer_config_validation.py",
    "runtime_dependency_trainer_spec": "src/mcrl/runtime/trainer_spec.py",
}

# These are the exact non-``mcrl.*`` files traversed by
# ``v023_lcsrs_source_adapter._authenticate``. They are deliberately kept
# as individual bindings instead of synchronising a predecessor scratch tree.
# The preflight module independently requires the same path set, so a future
# edit cannot silently remove a literal dynamic dependency from the transfer.
DYNAMIC_PROVENANCE_BINDINGS = {
    "dynamic_v020_c3_gate": ".scratch/multi-catfish-v020-c3-source-audit/run_v020_repriced_c3_gate.py",
    "dynamic_v018_analytic_runner": ".scratch/multi-catfish-v018-relational-zr/run_v018_analytic_diagnostic.py",
    "dynamic_v015_learned_context_runner": ".scratch/multi-catfish-v015-c3-learned-context/run_v015_c3_learned_context_oracle.py",
    "dynamic_v014_learner_gate_runner": ".scratch/multi-catfish-v014-learner/run_v014_learner_gate.py",
    "dynamic_v013_zero_energy_runner": ".scratch/zero-energy-c3-v013/run_v013_zero_energy_c3_oracle.py",
    "dynamic_v04_screen_runner": ".scratch/c3-v04/run_v04_c3_500_update_screen.py",
    "dynamic_v04_learnability_runner": ".scratch/c3-v04/run_v04_c3_learnability_gate.py",
    "dynamic_v04_source_runner": ".scratch/c3-v04/run_v04_c3_source.py",
    "dynamic_head_pivotality_probe": "scripts/run_head_pivotality_probe.py",
    "dynamic_v020_q1_repricing": ".scratch/multi-catfish-v020-c3-source-audit/q1-repricing/reprice_c1.py",
    "dynamic_v020_c3_contract": ".scratch/multi-catfish-v020-c3-source-audit/REPRICED-C3-LAMBDA-CONFOUND-GATE-CONTRACT-2026-09-04.md",
    "dynamic_v018_contract": ".scratch/multi-catfish-v018-relational-zr/contracts/MULTI-CATFISH-MCRL-V018-ANALYTIC-DIAGNOSTIC-PREREG-2026-09-04.md",
    "dynamic_v015_contract": "artifacts/multi-catfish-v015-c3-learned-context-oracle-20260903-r1/contracts/MULTI-CATFISH-MCRL-V015-C3-LEARNED-CONTEXT-ORACLE-PREREG-2026-09-03.md",
    "dynamic_v013_contract": "docs/MULTI-CATFISH-MCRL-V013-ZR-C3-FRESH-CONFIRMATION-PREREG-2026-09-03.md",
    "dynamic_v014_result": "artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/learner-gate/result.json",
    "dynamic_v014_authority": "artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/learner-gate/authority.json",
    "dynamic_v014_result_seal": "artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/learner-gate/result-seal.json",
    "dynamic_v020_fit_merged": ".scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/merged/result.json",
    "dynamic_v020_checkpoint_2026092101": ".scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/lineage-2026092101/checkpoints/lineage-2026092101-q2init-2026108101-rung-003000.pt",
    "dynamic_v020_checkpoint_2026092102": ".scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/lineage-2026092102/checkpoints/lineage-2026092102-q2init-2026108102-rung-003000.pt",
    "dynamic_v020_checkpoint_2026092103": ".scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/lineage-2026092103/checkpoints/lineage-2026092103-q2init-2026108103-rung-003000.pt",
    "dynamic_v020_target_2026108001": ".scratch/multi-catfish-v020-c3-source-audit/q2-batch-repricing/shards/2026108001-2026092101/q2_target_bits_repriced.npy",
    "dynamic_v020_target_2026108002": ".scratch/multi-catfish-v020-c3-source-audit/q2-batch-repricing/shards/2026108002-2026092101/q2_target_bits_repriced.npy",
    "dynamic_v020_target_2026108003": ".scratch/multi-catfish-v020-c3-source-audit/q2-batch-repricing/shards/2026108003-2026092101/q2_target_bits_repriced.npy",
    "dynamic_v020_target_2026108004": ".scratch/multi-catfish-v020-c3-source-audit/q2-batch-repricing/shards/2026108004-2026092101/q2_target_bits_repriced.npy",
    "dynamic_v020_target_2026108005": ".scratch/multi-catfish-v020-c3-source-audit/q2-batch-repricing/shards/2026108005-2026092101/q2_target_bits_repriced.npy",
    "dynamic_v020_target_2026108006": ".scratch/multi-catfish-v020-c3-source-audit/q2-batch-repricing/shards/2026108006-2026092101/q2_target_bits_repriced.npy",
    "dynamic_v020_target_2026108007": ".scratch/multi-catfish-v020-c3-source-audit/q2-batch-repricing/shards/2026108007-2026092101/q2_target_bits_repriced.npy",
}

if set(DYNAMIC_PROVENANCE_BINDINGS.values()) != set(authority.REQUIRED_DYNAMIC_SOURCE_PATHS):
    raise RuntimeError("dynamic provenance binding set disagrees with preflight authority")


def _sha(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"binding is missing or symlinked: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _binding(role: str, path: str) -> dict[str, str]:
    return {"role": role, "path": path, "sha256": _sha(REPO / path)}


def _add_unique_binding(
    entries: dict[str, dict[str, str]], role: str, path: str
) -> None:
    """Add one path unless an existing authority role already binds it."""

    if any(item.get("path") == path for item in entries.values()):
        return
    entries[role] = _binding(role, path)


def _external_bindings() -> dict[str, dict[str, str]]:
    if not DRAFT_MANIFEST.is_file() or DRAFT_MANIFEST.is_symlink():
        raise RuntimeError("the independently sealed R7 draft manifest is missing")
    payload = json.loads(DRAFT_MANIFEST.read_text(encoding="ascii"))
    result: dict[str, dict[str, str]] = {}
    for item in payload.get("bindings", []):
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        path = item.get("path")
        if not isinstance(role, str) or not isinstance(path, str):
            continue
        if path.startswith(".scratch/multi-catfish-v023-r7-balanced-successor/"):
            continue
        if role in {"launch_decision", "server_sync_launcher", "server_finalize"}:
            continue
        result[role] = _binding(role, path)
    return result


def build_code_manifest() -> str:
    entries = _external_bindings()
    for role, path in PACKAGE_BINDINGS.items():
        entries[role] = _binding(role, path)
    for role, path in DYNAMIC_PROVENANCE_BINDINGS.items():
        _add_unique_binding(entries, role, path)
    for role, filename in LOCAL_BINDINGS.items():
        entries[role] = _binding(role, f"{PREFIX}/{filename}")
    payload = {
        "bindings": [entries[role] for role in sorted(entries)],
        "launch": "AUTHORIZED_ONE_SHOT",
        "manifest_version": 1,
        "schema": authority.CODE_MANIFEST_SCHEMA,
        "status": "FROZEN_PRE_OUTCOME",
    }
    encoded = _canonical(payload) + b"\n"
    CODE_MANIFEST.write_bytes(encoded)
    digest = hashlib.sha256(encoded).hexdigest()
    CODE_DIGEST.write_text(f"{digest}  {CODE_MANIFEST.name}\n", encoding="ascii", newline="")
    return digest


def build() -> str:
    code_digest = build_code_manifest()
    launch_decision_path = REPO / authority.LAUNCH_DECISION
    if not launch_decision_path.is_file() or launch_decision_path.is_symlink():
        raise RuntimeError("R7 launch decision is missing")
    entries = _external_bindings()
    for role, path in PACKAGE_BINDINGS.items():
        entries[role] = _binding(role, path)
    for role, path in DYNAMIC_PROVENANCE_BINDINGS.items():
        _add_unique_binding(entries, role, path)
    for role, filename in LOCAL_BINDINGS.items():
        entries[role] = _binding(role, f"{PREFIX}/{filename}")
    entries["launch_decision"] = _binding("launch_decision", authority.LAUNCH_DECISION)
    entries["code_manifest"] = _binding("code_manifest", f"{PREFIX}/{CODE_MANIFEST.name}")
    entries["code_manifest_digest"] = _binding("code_manifest_digest", f"{PREFIX}/{CODE_DIGEST.name}")

    def link(role: str) -> dict[str, str]:
        return {"path": entries[role]["path"], "sha256": entries[role]["sha256"]}

    configuration: dict[str, Any] = {
        "split": "TRAIN_DEVELOPMENT",
        "test_split_opened": False,
        "episode_training": False,
        "scientific_efficacy": False,
        "claim_ceiling": authority.CLAIM_CEILING,
        "worlds": list(authority.WORLDS),
        "student_seeds": list(authority.STUDENT_SEEDS),
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
        "process_environment": dict(authority.PROCESS_ENVIRONMENT),
        "source_jobs": 8,
        "fit_jobs": 8,
        "composition_jobs": 8,
        "output_root": authority.OUTPUT_ROOT,
        "tmux_session": authority.TMUX_SESSION,
        "tle": {"root_argument": "--tle-root", "root_default": authority.TLE_ROOT, "file_set_sha256": authority.TLE_FILE_SET_SHA256},
        "selected_checkpoint_role": "FROZEN_GATE_BACKGROUND_PROVENANCE_ONLY_NOT_CURRENT_LEARNER_INITIALIZATION",
        "contract": link("contract"),
        "base_contract": link("base_contract"),
        "execution_addendum": link("execution_parameter_addendum"),
        "preregistration": link("preregistration"),
        "launch_decision": link("launch_decision"),
        "code_manifest": link("code_manifest"),
        "selected_checkpoint": link("selected_q1_q2_checkpoint"),
        "invalid_run_repair": link("invalid_run_i0"),
        "source_adapter": link("source_adapter"),
        "source_artifact_loader": link("runtime_source_artifact"),
        "learner": dict(authority.EXPECTED_LEARNER),
    }
    payload = {
        "bindings": [entries[role] for role in sorted(entries)],
        "code_manifest": link("code_manifest"),
        "configuration": configuration,
        "contract": {"path": authority.CONTRACT, "sha256": authority.CONTRACT_SHA256},
        "initial_network_sha256_by_seed": dict(authority.INITIAL_DIGESTS),
        "launch": "AUTHORIZED_ONE_SHOT",
        "manifest_version": 1,
        "process_environment": dict(authority.PROCESS_ENVIRONMENT),
        "schema": authority.MANIFEST_SCHEMA,
        "status": "FROZEN_PRE_OUTCOME",
        "student_seeds": list(authority.STUDENT_SEEDS),
        "worlds": list(authority.WORLDS),
    }
    encoded = _canonical(payload) + b"\n"
    PREFLIGHT_MANIFEST.write_bytes(encoded)
    digest = hashlib.sha256(encoded).hexdigest()
    PREFLIGHT_DIGEST.write_text(f"{digest}  {PREFLIGHT_MANIFEST.name}\n", encoding="ascii", newline="")
    return digest


if __name__ == "__main__":
    print(build())
