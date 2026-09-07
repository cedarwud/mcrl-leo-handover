#!/usr/bin/env python3
"""Mechanically reseal the mutable V0.23 preflight manifest.

This helper never changes a frozen contract or scientific source.  It extracts
the exact role-to-path authority table from the preflight validator, hashes
those files plus the focused verification tests, refreshes mirrored
configuration digests, and writes canonical ASCII JSON and its sidecar digest.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PREFLIGHT = HERE / "preflight_v023_lcsrs_r6.py"
MANIFEST = HERE / "PREFLIGHT-MANIFEST.json"
DIGEST = HERE / "PREFLIGHT-MANIFEST.sha256"
SERVER_TLE_ROOT = "/home/sat/mcrl-runtime/tle-frozen-20260820"
FROZEN_LEARNER = {
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

TEST_BINDINGS = {
    f"test_w{number}": f"tests/test_w{number}_ee_axis_lcsrs_{suffix}.py"
    for number, suffix in (
        (190, "c3_topology"),
        (191, "native_observation_provenance"),
        (192, "c3_pipeline"),
        (193, "c3_gate_metrics"),
        (194, "c3_gate_fit"),
        (195, "c3_source_artifact"),
        (196, "fit_adapter"),
        (197, "composition_adapter"),
        (198, "scientific_verifier"),
        (199, "fit_independent"),
        (200, "composition_runtime"),
        (201, "final_verifier"),
        (202, "server_launch_glue"),
        (203, "source_stage"),
        (204, "result_seal"),
    )
}
TEST_BINDINGS.update(
    {
        "test_w181": "tests/test_w181_ee_axis_coalition_residual_c3.py",
        "test_w182": "tests/test_w182_ee_axis_lcsrs_c3_state.py",
        "test_w183": "tests/test_w183_ee_axis_lcsrs_c3_head.py",
        "test_w184": "tests/test_w184_ee_axis_lcsrs_c3_encoder.py",
        "test_w185": "tests/test_w185_ee_axis_lcsrs_three_route.py",
        "test_w186": "tests/test_w186_ee_axis_lcsrs_c3_dataset.py",
        "test_w187": "tests/test_w187_ee_axis_lcsrs_c3_learner.py",
        "test_w188": "tests/test_w188_ee_axis_lcsrs_c3_placebo.py",
        "test_w189": "tests/test_w189_ee_axis_lcsrs_c3_teacher.py",
    }
)

# Superseded launch decisions remain available as repository history, but they
# must not survive into the current run's authenticated dependency closure.
SUPERSEDED_BINDING_ROLES = {
    "relaunch_decision_r2",
    "relaunch_decision_r3",
    "relaunch_decision_r4",
    "relaunch_decision_r5",
    "defect_decision_r5",
}
TEST_BINDINGS["test_w191"] = "tests/test_w191_native_observation_provenance.py"
TEST_BINDINGS["test_w205"] = "tests/test_w205_v023_step_result_contract.py"
TEST_BINDINGS.update(
    {
        "test_v023_scaffold": (
            ".scratch/multi-catfish-v023-r6-fit-binding-fix/"
            "test_v023_lcsrs_observability_scaffold.py"
        ),
        "test_v023_source_adapter": (
            ".scratch/multi-catfish-v023-r6-fit-binding-fix/"
            "test_v023_lcsrs_source_adapter.py"
        ),
        "test_v023_r5_scaffold": (
            ".scratch/multi-catfish-v023-r6-fit-binding-fix/"
            "test_v023_lcsrs_r5_scaffold.py"
        ),
        "test_v023_r5_semantics": (
            ".scratch/multi-catfish-v023-r6-fit-binding-fix/"
            "test_v023_r5_verifier_semantics.py"
        ),
    }
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _expected_paths() -> dict[str, str]:
    tree = ast.parse(PREFLIGHT.read_text(encoding="utf-8"), filename=str(PREFLIGHT))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        if node.targets[0].id == "expected_paths":
            value = ast.literal_eval(node.value)
            if not isinstance(value, dict):
                break
            return {str(role): str(path) for role, path in value.items()}
    raise RuntimeError("preflight expected_paths authority table was not found")


def main() -> int:
    payload = json.loads(MANIFEST.read_text(encoding="ascii"))
    payload["schema"] = "multi-catfish-mcrl-v023-lcsrs-observability-preflight-r6-fit-binding-v1"
    payload["manifest_version"] = 1
    old = {
        str(entry["role"]): str(entry["path"])
        for entry in payload.get("bindings", [])
        if str(entry["role"]) not in SUPERSEDED_BINDING_ROLES
    }
    paths = {**old, **_expected_paths(), **TEST_BINDINGS}
    bindings: list[dict[str, str]] = []
    seen_paths: set[str] = set()
    for role, relative in sorted(paths.items()):
        if relative in seen_paths:
            continue
        seen_paths.add(relative)
        target = REPO / relative
        if target.is_symlink() or not target.is_file():
            raise RuntimeError(f"binding is missing or symlinked: {role} -> {relative}")
        bindings.append({"path": relative, "role": role, "sha256": _sha256(target)})
    payload["bindings"] = bindings

    by_role = {entry["role"]: entry for entry in bindings}
    configuration = payload["configuration"]
    configuration["tle"]["root_default"] = SERVER_TLE_ROOT
    configuration["learner"] = FROZEN_LEARNER
    for key, role in (
        ("fit_merged", "fit_merged"),
        ("selected_checkpoint", "selected_q1_q2_checkpoint"),
        ("execution_addendum", "execution_parameter_addendum"),
        ("source_adapter", "runtime_source_adapter"),
        ("source_artifact_loader", "runtime_source_artifact"),
    ):
        configuration[key] = {
            "path": by_role[role]["path"],
            "sha256": by_role[role]["sha256"],
        }

    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    MANIFEST.write_bytes(encoded + b"\n")
    manifest_sha256 = hashlib.sha256(encoded + b"\n").hexdigest()
    DIGEST.write_text(
        f"{manifest_sha256}  {MANIFEST.name}\n", encoding="ascii", newline=""
    )
    print(manifest_sha256)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
