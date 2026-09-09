from __future__ import annotations

import copy
import json
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import os
import re
import shlex
import shutil
import stat
import struct
import subprocess
import sys
from types import SimpleNamespace

import pytest

from preflight_v023_c1c2_targets import (
    RUNTIME_IMPORT_BINDINGS,
    PreflightError,
    sha256_file,
    validate_manifest,
    validate_nested_r6_runtime_closure,
)
from audit_v023_c1c2_checkpoint_closure import (
    CheckpointClosureError,
    LEGACY_MAIN_RELATIVE,
    LEGACY_MAIN_SHA256,
    R6_CHECKPOINT_RELATIVE,
    R6_CHECKPOINT_SHA256,
    TARGET_ADAPTER,
    audit as audit_checkpoint_closure,
)
from run_v023_c1c2_targets_server import (
    ControllerError,
    SCHEDULE_SCHEMA,
    _canonical,
    _merge,
    _ops3_row,
    _read_receipt,
    _schedule_sha256,
    _validate_ops3_dataset,
)
import run_v023_c1c2_targets_server as controller_module
import seal_v023_c1c2_target_output as sealer_module


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
MANIFEST = HERE / "CODE-MANIFEST.json"
MANIFEST_DIGEST = HERE / "CODE-MANIFEST.sha256"
LAUNCHER = HERE / "sync_launch_v023_c1c2_targets_server.sh"
REAL_OPS3_EXCERPT = (
    REPO
    / ".scratch"
    / "multi-catfish-v023-c1c2-target-generation-launch"
    / "fixtures-real-shard"
    / "c2-neutral-world-2026121708.excerpt.json"
)


def _real_ops3_rows() -> list[dict[str, object]]:
    payload = json.loads(REAL_OPS3_EXCERPT.read_text(encoding="ascii"))
    return payload["rows"]


def _real_ops3_binding(row: dict[str, object]) -> dict[str, object]:
    binding_fields = (
        "source_anchor_sha256",
        "world",
        "step_index",
        "focal_user",
        "reference_action",
        "candidate_action",
        "candidate_physical_key",
        "source_rule",
        "schedule_sha256",
        "target_delta",
        "target_unit",
    )
    provenance = row["provenance"]
    assert isinstance(provenance, dict)
    return {
        **{field: row[field] for field in binding_fields},
        "ops3_anchor_sha256": provenance["ops3_anchor_sha256"],
        "ops3_projection_sha256": provenance["ops3_projection_sha256"],
    }


def _validate_real_ops3_row(row: dict[str, object]) -> None:
    _ops3_row(
        row,
        binding=_real_ops3_binding(row),
        mode=str(row["mode"]),
        world=int(row["world"]),
    )


def _write_current_ops3_manifest(tmp_path: Path) -> tuple[Path, Path]:
    """Make a disposable, fully rehashed V0.23 OPS-3 manifest for preflight tests.

    The checked-in manifest is deliberately left untouched until all semantic
    tests are accepted.  This fixture proves the new closure can authenticate
    without accidentally blessing its old Temporal-Fork bindings.
    """

    payload = json.loads(MANIFEST.read_text(encoding="ascii"))
    bindings = []
    for row in payload["bindings"]:
        relative = str(row["path"])
        role = str(row["role"])
        if (
            role.startswith("runtime_")
            or "c2-v03" in relative
            or "ee_axis_temporal" in relative
            or "temporal_fork" in relative
        ):
            continue
        source = REPO / relative
        if source.is_file():
            row = {**row, "sha256": sha256_file(source)}
        bindings.append(row)
    bound_roles = {row["role"] for row in bindings}
    for role, relative in RUNTIME_IMPORT_BINDINGS:
        source = REPO / relative
        if role in bound_roles:
            continue
        bindings.append({"role": role, "path": relative, "sha256": sha256_file(source)})
        bound_roles.add(role)
    for role, relative in (
        ("short_benchmark", ".scratch/multi-catfish-v023-c1c2-target-generation/benchmark_v023_c1c2_targets.py"),
        ("short_benchmark_runner", ".scratch/multi-catfish-v023-c1c2-target-generation-launch/run_v023_c1c2_short_benchmarks.py"),
        ("short_benchmark_tests", ".scratch/multi-catfish-v023-c1c2-target-generation-launch/test_v023_c1c2_short_benchmarks.py"),
        ("checkpoint_closure_audit", ".scratch/multi-catfish-v023-c1c2-target-generation-launch/audit_v023_c1c2_checkpoint_closure.py"),
    ):
        if role not in bound_roles:
            bindings.append({"role": role, "path": relative, "sha256": sha256_file(REPO / relative)})
            bound_roles.add(role)
    payload["bindings"] = bindings
    payload["schema"] = "multi-catfish-mcrl-v023-c1c2-target-generation-preflight-v2"
    payload["manifest_version"] = 2
    payload["r6_manifest_sha256"] = sha256_file(REPO / ".scratch/multi-catfish-v023-r6-fit-binding-fix/PREFLIGHT-MANIFEST.json")
    path = tmp_path / "CODE-MANIFEST.json"
    path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n", encoding="ascii")
    digest = tmp_path / "CODE-MANIFEST.sha256"
    digest.write_text(f"{sha256_file(path)}  CODE-MANIFEST.json\n", encoding="ascii")
    return path, digest


def test_actual_dry_run_does_not_call_remote_writer(tmp_path: Path) -> None:
    marker = tmp_path / "remote-called"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    for name in ("ssh", "rsync", "tmux"):
        path = fake_bin / name
        path.write_text(f"#!/bin/sh\nprintf called > {marker}\nexit 99\n", encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
    env = dict(os.environ)
    env["PATH"] = f"{fake_bin}:/usr/bin:/bin"
    result = subprocess.run(
        [str(LAUNCHER), "--dry-run"],
        cwd=REPO,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "V023_C1C2_TARGET_SYNC_DRY_RUN_PASS" in result.stdout
    assert not marker.exists()


def test_dry_run_derives_controller_and_log_after_root_override() -> None:
    server_root = "/home/sat/mcrl-v023-c1c2-target-generation-derived-path-test"
    result = subprocess.run(
        [
            str(LAUNCHER),
            "--dry-run",
            "--server-root",
            server_root,
            "--output-root",
            "/home/sat/mcrl-v023-c1c2-target-output-derived-path-test",
            "--tmux-session",
            "mcrl-v023-c1c2-derived-path-test",
        ],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert f"controller={server_root}/.scratch/" in result.stdout
    assert f"log={server_root}/controller.log" in result.stdout


def test_remote_short_benchmark_uses_the_synced_server_path() -> None:
    """The SSH command must never retain the launcher's local checkout path."""

    launcher = LAUNCHER.read_text(encoding="utf-8")
    assert 'server_short_benchmark="${server_root}/.scratch/' in launcher
    assert launcher.count("'$server_python' '$server_short_benchmark'") == 2
    assert "'$server_python' '$short_benchmark'" not in launcher


def test_launcher_restores_frozen_r6_source_before_strict_remote_preflight() -> None:
    """Live learner edits must not silently rewrite the sealed source lineage."""

    launcher = LAUNCHER.read_text(encoding="utf-8")
    assert 'source_authority_root="${V023_SOURCE_AUTHORITY_ROOT:-' in launcher
    assert 'frozen_three_route="${source_authority_root}/src/mcrl/algorithms/' in launcher
    assert "cp -- '$frozen_three_route' '$restored_three_route'" in launcher
    restore = launcher.index("cp -- '$frozen_three_route' '$restored_three_route'")
    strict_preflight = launcher.index("--require-r6-runtime-closure")
    first_benchmark = launcher.index("'$server_python' '$server_short_benchmark'")
    assert restore < strict_preflight < first_benchmark


def test_nested_r6_runtime_closure_has_positive_and_mutation_controls(
    tmp_path: Path,
) -> None:
    frozen = tmp_path / "src" / "frozen.py"
    frozen.parent.mkdir(parents=True)
    frozen.write_bytes(b"frozen-source\n")
    payload = {
        "bindings": [
            {
                "role": "frozen_source",
                "path": "src/frozen.py",
                "sha256": sha256_file(frozen),
            }
        ]
    }
    assert validate_nested_r6_runtime_closure(payload, repo=tmp_path) == {
        "src/frozen.py": sha256_file(frozen)
    }
    frozen.write_bytes(b"mutated-source\n")
    with pytest.raises(PreflightError, match="nested R6 binding drifted"):
        validate_nested_r6_runtime_closure(payload, repo=tmp_path)


def test_preflight_binds_current_r6_manifest_and_rejects_stale_hash(tmp_path: Path) -> None:
    current_manifest, current_digest = _write_current_ops3_manifest(tmp_path)
    receipt = validate_manifest(current_manifest, manifest_digest_path=current_digest, repo=REPO)
    payload = json.loads(current_manifest.read_text(encoding="ascii"))
    r6 = next(row for row in payload["bindings"] if row["role"] == "r6_preflight_manifest")
    current = REPO / r6["path"]
    assert r6["sha256"] == sha256_file(current)
    assert payload["r6_manifest_sha256"] == sha256_file(current)
    assert receipt["r6_manifest_sha256"] == payload["r6_manifest_sha256"]
    broken = json.loads(current_manifest.read_text(encoding="ascii"))
    broken["r6_manifest_sha256"] = "0" * 64
    # The validator must not accept a target manifest pointing away from R6.
    broken_path = tmp_path / "broken-CODE-MANIFEST.json"
    broken_digest = tmp_path / "broken-CODE-MANIFEST.sha256"
    broken_path.write_text(json.dumps(broken, sort_keys=True, separators=(",", ":")) + "\n", encoding="ascii")
    broken_digest.write_text(f"{sha256_file(broken_path)}  CODE-MANIFEST.json\n", encoding="ascii")
    with pytest.raises(PreflightError, match="does not bind current R6 digest"):
        validate_manifest(broken_path, manifest_digest_path=broken_digest, repo=REPO)


def test_preflight_fails_closed_when_runtime_binding_is_missing(tmp_path: Path) -> None:
    current_manifest, _ = _write_current_ops3_manifest(tmp_path)
    broken = json.loads(current_manifest.read_text(encoding="ascii"))
    broken["bindings"] = [
        row for row in broken["bindings"] if row["role"] != "runtime_ops3_producer"
    ]
    broken_path = tmp_path / "CODE-MANIFEST.json"
    broken_digest = tmp_path / "CODE-MANIFEST.sha256"
    broken_path.write_text(
        json.dumps(broken, sort_keys=True, separators=(",", ":")) + "\n", encoding="ascii"
    )
    broken_digest.write_text(
        f"{sha256_file(broken_path)}  CODE-MANIFEST.json\n", encoding="ascii"
    )
    with pytest.raises(PreflightError, match="runtime_ops3_producer"):
        validate_manifest(broken_path, manifest_digest_path=broken_digest, repo=REPO)


def test_checkpoint_closure_binds_d40_and_current_ops3_before_ssh() -> None:
    """The launch lane authenticates D40 and the current OPS-3 consumer."""

    receipt = audit_checkpoint_closure(REPO)
    assert receipt["status"] == "PASS_D40_CHECKPOINT_RUNTIME_ADAPTER"
    assert receipt["ready_to_relaunch"] is True
    assert receipt["ssh_or_launch_performed"] is False
    assert receipt["target_generation_checkpoint"]["path"] == R6_CHECKPOINT_RELATIVE
    assert sha256_file(REPO / R6_CHECKPOINT_RELATIVE) == R6_CHECKPOINT_SHA256
    assert LEGACY_MAIN_RELATIVE not in {
        row["path"] for row in json.loads(MANIFEST.read_text(encoding="ascii"))["bindings"]
    }
    assert LEGACY_MAIN_SHA256 not in {
        row["sha256"] for row in json.loads(MANIFEST.read_text(encoding="ascii"))["bindings"]
    }


def test_checkpoint_closure_cli_require_ready_passes_before_remote_work() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(HERE / "audit_v023_c1c2_checkpoint_closure.py"),
            "--repo",
            str(REPO),
            "--require-ready",
        ],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "PASS_D40_CHECKPOINT_RUNTIME_ADAPTER"
    assert payload["ready_to_relaunch"] is True


def test_checkpoint_closure_guard_precedes_every_remote_effect() -> None:
    """A mismatched local bundle must stop before SSH, rsync, or tmux."""

    launcher = LAUNCHER.read_text(encoding="utf-8")
    guard = launcher.index('"$local_python" "$checkpoint_audit" --repo "$repo_root" --require-ready')
    remote_effects = [
        launcher.index("if ssh --"),
        launcher.index("rsync -aR"),
        launcher.index("tmux new-session"),
    ]
    assert guard < min(remote_effects)


def test_runtime_import_closure_is_bound_synced_and_importable(tmp_path: Path) -> None:
    current_manifest, _ = _write_current_ops3_manifest(tmp_path)
    payload = json.loads(current_manifest.read_text(encoding="ascii"))
    bound = {entry["role"]: entry["path"] for entry in payload["bindings"]}
    launcher = LAUNCHER.read_text(encoding="utf-8")
    for role, relative in RUNTIME_IMPORT_BINDINGS:
        assert bound[role] == relative
        assert (REPO / relative).is_file(), relative
        relative_path = Path(relative)
        assert relative in launcher or any(
            parent.as_posix() in launcher for parent in relative_path.parents if parent.as_posix() != "."
        )

    code = "\n".join(
        (
            "import importlib.util",
            "from pathlib import Path",
            "import sys",
            "path = Path('.scratch/multi-catfish-v023-c1c2-target-generation/generate_v023_c1c2_targets.py').resolve()",
            "spec = importlib.util.spec_from_file_location('target_generator_import_probe', path)",
            "module = importlib.util.module_from_spec(spec)",
            "sys.modules[spec.name] = module",
            "spec.loader.exec_module(module)",
            "runtime = module._runtime_modules()",
            "assert runtime.source is not None",
            "assert runtime.ops3_source is not None",
            "assert runtime.d40_adapter is not None",
            "assert hasattr(runtime.ops3_source, '_native_q12_anchor')",
            "assert 'mcrl_v023_target_ops3_producer' in sys.modules",
            "assert not any('temporal_fork' in name or 'temporal_pair_smoke' in name for name in sys.modules)",
            "print('V023_RUNTIME_IMPORT_CLOSURE_PASS')",
        )
    )
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "V023_RUNTIME_IMPORT_CLOSURE_PASS" in result.stdout


def test_launcher_sync_covers_every_r6_preflight_binding() -> None:
    """The server preflight must not discover a missing bound file after sync."""

    launcher = LAUNCHER.read_text(encoding="utf-8")
    match = re.search(r"sync_paths=\(\n(?P<body>.*?)\n\)", launcher, flags=re.DOTALL)
    assert match is not None
    sync_paths = tuple(shlex.split(match.group("body"), comments=True, posix=True))
    assert sync_paths
    r6 = json.loads(
        (REPO / ".scratch/multi-catfish-v023-r6-fit-binding-fix/PREFLIGHT-MANIFEST.json").read_text(
            encoding="ascii"
        )
    )
    uncovered: list[str] = []
    for row in r6["bindings"]:
        relative = Path(row["path"])
        if not any(relative == Path(root) or Path(root) in relative.parents for root in sync_paths):
            uncovered.append(relative.as_posix())
    assert uncovered == []


def test_launcher_sync_covers_q12_authority_file_maps() -> None:
    """Q1/Q2 authority paths are a second-order runtime closure."""

    launcher = LAUNCHER.read_text(encoding="utf-8")
    match = re.search(r"sync_paths=\(\n(?P<body>.*?)\n\)", launcher, flags=re.DOTALL)
    assert match is not None
    sync_paths = tuple(Path(value) for value in shlex.split(match.group("body"), comments=True, posix=True))
    authority = json.loads(
        (
            REPO
            / ".scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/lineage-2026092101/authority.json"
        ).read_text(encoding="ascii")
    )
    required = set(authority["code_file_sha256s"]) | set(
        authority["q2_repriced_target_file_sha256s"]
    )
    uncovered = [
        relative
        for relative in sorted(required)
        if not any(Path(relative) == root or root in Path(relative).parents for root in sync_paths)
    ]
    assert uncovered == []


def test_stale_or_missing_source_receipt_blocks_child_merge(tmp_path: Path) -> None:
    shard = tmp_path / "mode"
    shard.mkdir()
    (shard / "receipt.json").write_text("{}\n", encoding="ascii")
    with pytest.raises(ControllerError, match="receipt/manifest"):
        _read_receipt(shard)


def test_controller_claim_ceiling_matches_frozen_generator() -> None:
    generator = controller_module._load_generator()

    assert controller_module.CLAIM_CEILING == generator.CLAIM_CEILING


def test_sealer_claim_ceiling_matches_frozen_generator() -> None:
    generator = controller_module._load_generator()

    assert sealer_module.CLAIM_CEILING == generator.CLAIM_CEILING


def test_sealer_rejects_old_claim_ceiling(tmp_path: Path) -> None:
    root = tmp_path / "output"
    root.mkdir()
    receipt = {
        "schema": sealer_module.SCHEMA,
        "status": "TARGETS_MATERIALIZED_TRAIN",
        "claim_ceiling": (
            "TRAIN_PHYSICAL_TARGET_GENERATION_ONLY_NO_LEARNER_"
            "NO_EPISODE_TRAINING_NO_TEST"
        ),
        "training_or_replay_write": False,
        "learner_update": False,
        "test_split_opened": False,
    }
    receipt_path = root / "receipt.json"
    receipt_path.write_bytes(_canonical(receipt))
    (root / "MANIFEST.sha256").write_text(
        f"{__import__('hashlib').sha256(receipt_path.read_bytes()).hexdigest()}  receipt.json\n",
        encoding="ascii",
    )

    with pytest.raises(sealer_module.SealError, match="claim ceiling drifted"):
        sealer_module.seal(root)


def _synthetic_schedule() -> dict[str, dict[str, object]]:
    schedule: dict[str, dict[str, object]] = {}
    for mode in ("informed", "neutral"):
        for world in (10, 20):
            key = f"{mode}:{world}"
            common = {
                "source_anchor_sha256": f"{world:02x}" * 32,
                "source_seed": world,
                "world": world,
                "step_index": world + 1,
                "focal_user": world % 7,
                "reference_action": 0,
                "candidate_action": 2,
                "candidate_physical_key": [world, 1],
                "source_rule": mode,
            }
            schedule[key] = {
                "mode": mode,
                "world": world,
                "C1": [
                    {
                        **common,
                        "source_record_sha256": f"{world + 1:02x}" * 32,
                    }
                ],
                "C2": [
                    {
                        key: value
                        for key, value in common.items()
                        if key != "source_seed"
                    }
                ],
            }
    return schedule


def _write_synthetic_shard(
    root: Path,
    key: str,
    schedule_entry: dict[str, object],
) -> None:
    root.mkdir(parents=True)
    mode = str(schedule_entry["mode"])
    world = int(schedule_entry["world"])
    datasets: dict[str, dict[str, object]] = {"C1": {}, "C2": {}}
    row_bindings: dict[str, list[dict[str, object]]] = {"C1": [], "C2": []}
    files: dict[str, bytes] = {}
    for family in ("C1", "C2"):
        name = f"{family.lower()}-{mode}-world-{world}.json"
        rows = list(schedule_entry[family])
        if family == "C2":
            selected_rows = []
            for row in rows:
                target_reference = 0.25
                target_candidate = 1.5
                selected_rows.append(
                    {
                        "schema": "multi-catfish-mcrl-v023-repriced-ops3-selected-pair-dataset-v1",
                        "world": world,
                        "mode": mode,
                        "source_anchor_sha256": row["source_anchor_sha256"],
                        "step_index": row["step_index"],
                        "focal_user": row["focal_user"],
                        "reference_action": row["reference_action"],
                        "candidate_action": row["candidate_action"],
                        "candidate_physical_key": row["candidate_physical_key"],
                        "source_rule": row["source_rule"],
                        "schedule_sha256": "c" * 64,
                        "target_unit": "normalized-repriced-ops3-delta-over-kappa",
                        "target_reference_value": target_reference,
                        "target_candidate_value": target_candidate,
                        "target_delta": target_candidate - target_reference,
                        "q1_reference_action": 0,
                        "action_mask": [True, True, True],
                        "q2_state": [0.0] * 48,
                        "q2_features": [[0.0] * 16] * 3,
                        "persistence": [[0.0] * 3] * 3,
                        "rate_bps": [[0.0] * 3] * 3,
                        "marginal_power_w": [[0.0] * 3] * 3,
                        "required_power_w": [[0.0] * 3] * 3,
                        "horizon": 0,
                        "provenance": {
                            "ops3_anchor_sha256": "b" * 64,
                            "ops3_tracker_seed_sha256": "f" * 64,
                            "ops3_projection_sha256": "e" * 64,
                            "ops3_future_d2_indices": [],
                            "ops3_sample_times_utc": [],
                            "ops3_offset_times_utc": [],
                        },
                    }
                )
            payload = {
                "schema": "multi-catfish-mcrl-v023-repriced-ops3-selected-pair-dataset-v1",
                "source_manifest_sha256": "s" * 64,
                "checkpoint_sha256": "a" * 64,
                "lambda_bits_per_j": float(1.0).hex(),
                "kappa_bits": float(2.0).hex(),
                "target_unit": "normalized-repriced-ops3-delta-over-kappa",
                "rows": selected_rows,
            }
            content = _canonical(payload)
        else:
            content = _canonical({"family": family, "mode": mode, "world": world})
        files[name] = content
        datasets[family][key] = {
            "path": name,
            "rows": len(rows),
            "source_manifest_sha256": "s" * 64,
            "dataset_sha256": __import__("hashlib").sha256(
                content[:-1] if family == "C2" else content
            ).hexdigest(),
        }
        if family == "C2":
            datasets[family][key]["schema"] = "multi-catfish-mcrl-v023-repriced-ops3-selected-pair-dataset-v1"
        for row in rows:
            row_bindings[family].append(
                {
                    **row,
                    "mode": mode,
                    "common_random_field_sha256": "f" * 64,
                    "comparison_sha256": "e" * 64,
                    "backend_anchor_sha256": "b" * 64,
                    "schedule_sha256": "c" * 64,
                    **(
                        {
                            "ops3_anchor_sha256": "b" * 64,
                            "ops3_projection_sha256": "e" * 64,
                            "target_delta": 1.25,
                            "target_unit": "normalized-repriced-ops3-delta-over-kappa",
                        }
                        if family == "C2"
                        else {}
                    ),
                }
            )
    for name, content in files.items():
        (root / name).write_bytes(content)
    receipt = {
        "schema": "multi-catfish-mcrl-v023-c1c2-target-generation-v1",
        "status": "TARGETS_MATERIALIZED_TRAIN",
        "claim_ceiling": controller_module._load_generator().CLAIM_CEILING,
        "training_or_replay_write": False,
        "learner_update": False,
        "test_split_opened": False,
        "source": {
            "capture_path": "/capture.json",
            "capture_sha256": "a" * 64,
            "materialization_dir": "/materialized",
            "materialization_manifest_sha256": "m" * 64,
            "pool_sha256": "p" * 64,
            "source_family": "family",
            "source_manifest_sha256": "s" * 64,
            "checkpoint_sha256": "a" * 64,
        },
        "formula_constants": {"lambda": "lambda", "kappa": "kappa"},
        "code_closure": controller_module._load_generator()._output_code_closure(),
        "code_closure_sha256": __import__("hashlib").sha256(
            json.dumps(
                controller_module._load_generator()._output_code_closure(),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("ascii")
        ).hexdigest(),
        "datasets": datasets,
        "row_bindings": row_bindings,
        "shard": {"mode": mode, "world": world},
        "schedule": {
            "schema": SCHEDULE_SCHEMA,
            "shards": {key: schedule_entry},
            "sha256": _schedule_sha256({key: schedule_entry}),
        },
    }
    receipt_path = root / "receipt.json"
    receipt_path.write_bytes(_canonical(receipt))
    manifest_lines = [
        f"{__import__('hashlib').sha256(files[name]).hexdigest()}  {name}\n"
        for name in sorted(files)
    ]
    manifest_lines.append(
        f"{__import__('hashlib').sha256(receipt_path.read_bytes()).hexdigest()}  receipt.json\n"
    )
    (root / "MANIFEST.sha256").write_text("".join(manifest_lines), encoding="ascii")


def test_mode_receipt_rejects_old_claim_ceiling_with_exact_message(
    tmp_path: Path,
) -> None:
    schedule = _synthetic_schedule()
    key = "informed:10"
    shard = tmp_path / "shard"
    _write_synthetic_shard(shard, key, schedule[key])
    receipt_path = shard / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="ascii"))
    receipt["claim_ceiling"] = (
        "TRAIN_PHYSICAL_TARGET_GENERATION_ONLY_NO_LEARNER_"
        "NO_EPISODE_TRAINING_NO_TEST"
    )
    receipt_path.write_bytes(_canonical(receipt))
    manifest_path = shard / "MANIFEST.sha256"
    lines = manifest_path.read_text(encoding="ascii").splitlines()
    lines[-1] = (
        f"{__import__('hashlib').sha256(receipt_path.read_bytes()).hexdigest()}"
        "  receipt.json"
    )
    manifest_path.write_text("\n".join(lines) + "\n", encoding="ascii")

    with pytest.raises(ControllerError) as caught:
        _read_receipt(shard)
    assert str(caught.value) == "mode receipt claim ceiling drifted"


def test_mode_world_merge_is_order_content_and_sha_deterministic(tmp_path: Path) -> None:
    expected = _synthetic_schedule()
    first_staging = tmp_path / "first-staging"
    second_staging = tmp_path / "second-staging"
    first_shards: dict[str, Path] = {}
    second_shards: dict[str, Path] = {}
    for key, entry in expected.items():
        first = first_staging / key.replace(":", "-")
        second = second_staging / key.replace(":", "-")
        _write_synthetic_shard(first, key, entry)
        _write_synthetic_shard(second, key, entry)
        first_shards[key] = first
        second_shards[key] = second

    first_output = tmp_path / "merged-first"
    second_output = tmp_path / "merged-second"
    _merge(
        dict(reversed(tuple(first_shards.items()))),
        first_output,
        expected_schedule=expected,
    )
    _merge(second_shards, second_output, expected_schedule=expected)

    first_files = {
        path.relative_to(first_output).as_posix(): path.read_bytes()
        for path in first_output.rglob("*")
        if path.is_file()
    }
    second_files = {
        path.relative_to(second_output).as_posix(): path.read_bytes()
        for path in second_output.rglob("*")
        if path.is_file()
    }
    assert first_files == second_files
    merged_receipt = _read_receipt(first_output)
    assert merged_receipt["parallel_shards"] == sorted(expected)
    assert "shard" not in merged_receipt


def test_ops3_downstream_accepts_terminal_h0_without_a_legacy_release(tmp_path: Path) -> None:
    """A selected pair at episode end is valid when its declared surface is zero."""

    schedule = _synthetic_schedule()
    key = "informed:10"
    root = tmp_path / "shard"
    _write_synthetic_shard(root, key, schedule[key])
    receipt = _read_receipt(root)
    _validate_ops3_dataset(
        root,
        receipt["datasets"]["C2"][key],
        receipt["row_bindings"]["C2"],
        mode="informed",
        world=10,
        source_manifest_sha256=receipt["source"]["source_manifest_sha256"],
    )


def test_ops3_real_excerpt_rows_match_feature_major_state_and_native_d2_window() -> None:
    from src.mcrl.runtime.ee_axis_ops3_live import D2_SUBSTEPS_PER_DECISION

    rows = _real_ops3_rows()
    assert len(rows) == 3
    assert controller_module.OPS3_SAMPLES_PER_STEP == D2_SUBSTEPS_PER_DECISION == 47
    for row in rows:
        horizon = row["horizon"]
        provenance = row["provenance"]
        assert isinstance(horizon, int)
        assert isinstance(provenance, dict)
        assert len(provenance["ops3_future_d2_indices"]) == (
            horizon * controller_module.OPS3_SAMPLES_PER_STEP
        )
        _validate_real_ops3_row(row)


def test_ops3_real_excerpt_rejects_action_major_q2_state() -> None:
    row = copy.deepcopy(_real_ops3_rows()[0])
    row["q2_state"] = [
        struct.unpack("!f", struct.pack("!f", float(value)))[0]
        for feature_row in row["q2_features"]
        for value in feature_row
    ]

    with pytest.raises(
        ControllerError,
        match="OPS-3 q2_state is not the target-free feature projection",
    ):
        _validate_real_ops3_row(row)


def test_ops3_real_excerpt_rejects_permuted_q2_features() -> None:
    row = copy.deepcopy(_real_ops3_rows()[0])
    row["q2_features"][0], row["q2_features"][1] = (
        row["q2_features"][1],
        row["q2_features"][0],
    )

    with pytest.raises(
        ControllerError,
        match="OPS-3 q2_state is not the target-free feature projection",
    ):
        _validate_real_ops3_row(row)


def test_ops3_real_excerpt_rejects_truncated_offset_times() -> None:
    row = copy.deepcopy(_real_ops3_rows()[0])
    row["provenance"]["ops3_offset_times_utc"].pop()

    with pytest.raises(ControllerError, match="does not align with H_t"):
        _validate_real_ops3_row(row)


def test_ops3_real_excerpt_rejects_incomplete_native_d2_sample_step() -> None:
    row = copy.deepcopy(_real_ops3_rows()[0])
    row["provenance"]["ops3_future_d2_indices"].pop()
    row["provenance"]["ops3_sample_times_utc"].pop()

    with pytest.raises(ControllerError, match="does not align with H_t"):
        _validate_real_ops3_row(row)


def test_ops3_h0_rejects_nonempty_native_d2_provenance() -> None:
    row = copy.deepcopy(_real_ops3_rows()[0])
    row["horizon"] = 0
    action_count = len(row["action_mask"])
    for field in ("persistence", "rate_bps", "marginal_power_w", "required_power_w"):
        row[field] = [[0.0] * action_count for _ in range(controller_module.OPS3_HORIZON)]

    with pytest.raises(ControllerError, match="does not align with H_t"):
        _validate_real_ops3_row(row)


def test_ops3_downstream_rejects_double_normalization_and_state_aliasing(tmp_path: Path) -> None:
    schedule = _synthetic_schedule()
    key = "neutral:20"
    root = tmp_path / "shard"
    _write_synthetic_shard(root, key, schedule[key])
    receipt = _read_receipt(root)
    metadata = receipt["datasets"]["C2"][key]
    path = root / metadata["path"]
    payload = json.loads(path.read_text(encoding="ascii"))
    payload["target_unit"] = "raw-delta-bits"
    path.write_bytes(_canonical(payload))
    metadata["dataset_sha256"] = __import__("hashlib").sha256(
        _canonical(payload)[:-1]
    ).hexdigest()
    with pytest.raises(ControllerError, match="target unit"):
        _validate_ops3_dataset(
            root,
            metadata,
            receipt["row_bindings"]["C2"],
            mode="neutral",
            world=20,
            source_manifest_sha256=receipt["source"]["source_manifest_sha256"],
        )

    payload["target_unit"] = "normalized-repriced-ops3-delta-over-kappa"
    payload["rows"][0]["q2_state"][0] = 1.0
    path.write_bytes(_canonical(payload))
    metadata["dataset_sha256"] = __import__("hashlib").sha256(
        _canonical(payload)[:-1]
    ).hexdigest()
    with pytest.raises(ControllerError, match="target-free feature projection"):
        _validate_ops3_dataset(
            root,
            metadata,
            receipt["row_bindings"]["C2"],
            mode="neutral",
            world=20,
            source_manifest_sha256=receipt["source"]["source_manifest_sha256"],
        )


def test_merge_rejects_filename_only_dataset_substitution(tmp_path: Path) -> None:
    expected = _synthetic_schedule()
    key = "informed:10"
    shard = tmp_path / "shard"
    _write_synthetic_shard(shard, key, expected[key])
    receipt_path = shard / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="ascii"))
    receipt["datasets"]["C1"][key]["path"] = "c1-neutral-world-20.json"
    receipt_path.write_bytes(_canonical(receipt))
    manifest_path = shard / "MANIFEST.sha256"
    lines = manifest_path.read_text(encoding="ascii").splitlines()
    lines[-1] = f"{__import__('hashlib').sha256(receipt_path.read_bytes()).hexdigest()}  receipt.json"
    manifest_path.write_text("\n".join(lines) + "\n", encoding="ascii")

    with pytest.raises(ControllerError, match="dataset metadata"):
        _merge({key: shard}, tmp_path / "merged", expected_schedule={key: expected[key]})


def test_active_launch_closure_has_no_legacy_checkpoint_path_and_targets_ubuntu() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="ascii"))
    paths = [entry["path"].lower() for entry in payload["bindings"]]
    assert all("r5" not in path for path in paths)
    launcher = LAUNCHER.read_text(encoding="utf-8")
    controller = (HERE / "run_v023_c1c2_targets_server.py").read_text(encoding="utf-8")
    preflight = (HERE / "preflight_v023_c1c2_targets.py").read_text(encoding="utf-8")
    assert "server_host=\"${V023_SERVER_HOST:-sat}\"" in launcher
    assert "/home/sat/mcrl-leo-handover/.venv/bin/python" in launcher
    assert "/home/sat/mcrl-v023-c1c2-target-generation-20260906-d40" in launcher
    assert "/home/sat/mcrl-v023-c1c2-targets-20260906-d40" in launcher
    assert "mcrl-v023-c1c2-target-generation-20260906-d40" in launcher
    assert "-m pytest -q" in launcher
    assert "audit_v023_c1c2_checkpoint_closure.py" in launcher
    assert "--require-ready" in launcher
    assert "--input-dir" not in launcher
    assert "artifacts/training-2026-08-25-rerun01" not in launcher
    assert "run_v023_c1c2_short_benchmarks.py" in launcher
    assert "short-benchmark-receipts" in launcher
    assert "--timeout-s 540" in launcher
    assert "--validate" in launcher
    assert "test_v023_c1c2_short_benchmarks.py" in launcher
    assert ".scratch/multi-catfish-v023-r7-launch-ready" in launcher
    assert ".scratch/c2-v03" not in launcher
    assert all(
        "c2-v03" not in relative and "ee_axis_temporal" not in relative and "temporal_fork" not in relative
        for _, relative in RUNTIME_IMPORT_BINDINGS
    )
    assert "runtime_ops3_producer" in preflight
    assert '"short_benchmark"' in preflight
    assert '"short_benchmark_runner"' in preflight
    assert '"--mode",' in controller
    assert '"--world",' in controller
    assert "mode/world" in controller
    assert "SHARD_STATUS_SCHEMA" in controller
    assert "shard-status" in controller
    assert 'event="terminal"' in controller


def test_isolated_copied_bundle_authenticates_d40_checkpoint(tmp_path: Path) -> None:
    """The launch adapter authenticates copied bytes without simulator access."""

    adapter_copy = tmp_path / "bundle" / "d40_checkpoint_runtime_adapter.py"
    checkpoint_copy = tmp_path / "bundle" / "d40.pt"
    adapter_copy.parent.mkdir()
    shutil.copyfile(TARGET_ADAPTER, adapter_copy)
    shutil.copyfile(REPO / R6_CHECKPOINT_RELATIVE, checkpoint_copy)
    spec = spec_from_file_location(
        "isolated_d40_checkpoint_runtime_adapter", adapter_copy
    )
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    receipt = module.authenticate_d40_checkpoint(checkpoint_copy)
    assert receipt["checkpoint_sha256"] == R6_CHECKPOINT_SHA256
    assert receipt["checkpoint_schema"] == module.D40_CHECKPOINT_SCHEMA
    assert receipt["episode_training"] is False


def test_controller_detects_nonfirst_failure_before_first_child_finishes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schedule = {
        "informed:10": {"mode": "informed", "world": 10, "C1": [], "C2": [{}]},
        "informed:20": {"mode": "informed", "world": 20, "C1": [], "C2": [{}]},
        "neutral:10": {"mode": "neutral", "world": 10, "C1": [], "C2": [{}]},
    }

    class FakeProcess:
        def __init__(self, command, **_kwargs):
            self.world = int(command[command.index("--world") + 1])
            self.returncode = 9 if self.world == 20 else None

        def poll(self):
            return self.returncode

        def wait(self):
            if self.returncode is None:
                raise AssertionError("controller waited on the unfinished first child")
            return self.returncode

        def terminate(self):
            self.returncode = -15

    merge_called = False

    def fail_if_merged(*_args, **_kwargs):
        nonlocal merge_called
        merge_called = True

    monkeypatch.setattr(controller_module, "_expected_schedule", lambda _args: schedule)
    monkeypatch.setattr(controller_module.subprocess, "Popen", FakeProcess)
    monkeypatch.setattr(controller_module, "_merge", fail_if_merged)
    staging = tmp_path / "staging"
    output = tmp_path / "output"
    args = SimpleNamespace(
        output=output,
        staging=staging,
        capture=tmp_path / "capture",
        materialization_dir=tmp_path / "materialized",
        tle_root=tmp_path / "tle",
        prereg=tmp_path / "prereg",
        manifest=tmp_path / "manifest",
        manifest_digest=tmp_path / "manifest.sha256",
        execution_addendum=tmp_path / "addendum",
        python=Path(sys.executable),
        users=100,
        max_workers=2,
    )

    assert controller_module.run(args) == 2
    assert not merge_called
    terminal = {
        path.name: json.loads(path.read_text(encoding="ascii"))
        for path in (staging / "shard-status").glob("*.terminal.json")
    }
    assert terminal["informed-world-20.terminal.json"]["returncode"] == 9
    assert terminal["informed-world-20.terminal.json"]["error"] == (
        "mode/world shard exited with status 9"
    )
    assert terminal["informed-world-10.terminal.json"]["error"] == (
        "controller aborted this shard after another failure"
    )
    assert terminal["neutral-world-10.terminal.json"]["state"] == "BLOCKED"
    assert (output / "FAILED").is_file()
