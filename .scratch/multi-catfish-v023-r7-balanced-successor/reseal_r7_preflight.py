#!/usr/bin/env python3
"""Mechanically reseal the complete draft/no-launch R7 pipeline manifest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from preflight_r7_balanced import (
    CONTRACT,
    CONTRACT_SHA256,
    HERE,
    INITIAL_DIGESTS,
    MANIFEST_SCHEMA,
    PROCESS_ENVIRONMENT,
    REPO,
    STUDENT_SEEDS,
    WORLDS,
)


MANIFEST = HERE / "R7-PREFLIGHT-MANIFEST.json"
DIGEST = HERE / "R7-PREFLIGHT-MANIFEST.sha256"
COMPAT_MANIFEST = HERE / "PREFLIGHT-MANIFEST.json"
COMPAT_DIGEST = HERE / "PREFLIGHT-MANIFEST.sha256"
LOCAL_PREFIX = ".scratch/multi-catfish-v023-r7-balanced-successor"
LOCAL_BINDINGS = {
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
DROP_ROLES = {
    "contract",
    "launch_decision",
    "defect_decision_r6",
    "server_sync_launcher",
    "server_finalize",
    "full_gate_server",
    "runner",
    "preflight",
    "verifier",
    "source_server",
    "fit_server",
    "composition_server",
    "composition_runtime",
    "runtime_source_adapter",
    "runtime_fit_adapter",
    "runtime_composition_adapter",
    "scientific_verifier",
    "source_stage_verifier",
    "fit_independent_verifier",
    "final_verifier",
    "result_sealer",
    "source_artifact_schema",
    "test_v023_scaffold",
    "test_v023_source_adapter",
    "test_v023_r5_scaffold",
    "test_v023_r5_semantics",
}


def _sha(path: Path) -> str:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise RuntimeError(f"binding is missing or symlinked: {target}")
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _binding(role: str, relative: str) -> dict[str, str]:
    return {"role": role, "path": relative, "sha256": _sha(REPO / relative)}


def _template() -> dict[str, Any]:
    if MANIFEST.is_symlink() or not MANIFEST.is_file():
        raise RuntimeError("R7 immutable-configuration template is unavailable")
    payload = json.loads(MANIFEST.read_text(encoding="ascii"))
    if not isinstance(payload, dict) or not isinstance(payload.get("configuration"), dict):
        raise RuntimeError("R7 immutable-configuration template is malformed")
    return payload


def build() -> str:
    template = _template()
    by_role: dict[str, dict[str, str]] = {}
    for entry in template.get("bindings", []):
        if not isinstance(entry, dict):
            continue
        role = entry.get("role")
        path = entry.get("path")
        if (
            not isinstance(role, str)
            or not isinstance(path, str)
            or role in DROP_ROLES
            or path.startswith(".scratch/multi-catfish-v023-r6-fit-binding-fix/")
        ):
            continue
        by_role[role] = _binding(role, path)

    for role, name in LOCAL_BINDINGS.items():
        by_role[role] = _binding(role, f"{LOCAL_PREFIX}/{name}")
    by_role["contract"] = _binding("contract", CONTRACT)
    by_role["base_contract"] = _binding(
        "base_contract",
        "docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md",
    )

    configuration = dict(template["configuration"])
    learner = dict(configuration["learner"])
    learner["initial_network_sha256_by_seed"] = dict(INITIAL_DIGESTS)
    configuration.update(
        {
            "worlds": list(WORLDS),
            "student_seeds": list(STUDENT_SEEDS),
            "learner": learner,
            "process_environment": dict(PROCESS_ENVIRONMENT),
            "contract": {"path": CONTRACT, "sha256": CONTRACT_SHA256},
            "base_contract": {
                "path": by_role["base_contract"]["path"],
                "sha256": by_role["base_contract"]["sha256"],
            },
            "source_adapter": {
                "path": by_role["runtime_source_adapter"]["path"],
                "sha256": by_role["runtime_source_adapter"]["sha256"],
            },
        }
    )
    payload = {
        "bindings": [by_role[role] for role in sorted(by_role)],
        "configuration": configuration,
        "contract": {"path": CONTRACT, "sha256": CONTRACT_SHA256},
        "initial_network_sha256_by_seed": dict(INITIAL_DIGESTS),
        "launch": "NO_LAUNCH",
        "manifest_version": 1,
        "process_environment": dict(PROCESS_ENVIRONMENT),
        "schema": MANIFEST_SCHEMA,
        "status": "DRAFT_PRE_OUTCOME",
        "student_seeds": list(STUDENT_SEEDS),
        "worlds": list(WORLDS),
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii") + b"\n"
    MANIFEST.write_bytes(encoded)
    digest = hashlib.sha256(encoded).hexdigest()
    DIGEST.write_text(f"{digest}  {MANIFEST.name}\n", encoding="ascii", newline="")
    # Retain the copied filenames only as byte-identical R7 compatibility
    # aliases.  A stale explicit caller therefore sees the fresh R7 schedule,
    # never the excluded R6 panel.
    COMPAT_MANIFEST.write_bytes(encoded)
    COMPAT_DIGEST.write_text(
        f"{digest}  {COMPAT_MANIFEST.name}\n", encoding="ascii", newline=""
    )
    return digest


if __name__ == "__main__":
    print(build())
