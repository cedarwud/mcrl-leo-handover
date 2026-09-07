#!/usr/bin/env python3
"""Fail-closed preflight for the V0.23 R6 composition-only accelerator.

This module is intentionally independent of the production adapter.  It reads
the already-running R6 result tree, verifies the exact source/fit identities
needed by the existing composition server, and inspects live process and
memory evidence before a wrapper may start any worker.  It never imports
Torch, NumPy, a simulator, TLE data, or a learner.

The accelerator is a scheduling aid, not a new experiment.  It is restricted
to the four predeclared tail shards and emits no scientific decision.  Missing
live-controller evidence, a partial output, an active target collision, or an
unbound memory budget is a ``NO-GO``.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Mapping, Sequence
import zipfile


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
R6_DIR = REPO / ".scratch" / "multi-catfish-v023-r6-fit-binding-fix"
R6_DIR_NAME = ".scratch/multi-catfish-v023-r6-fit-binding-fix"

CONTRACT_SHA256 = "1e69a2e7242198adce97e6357e4205a29fe6d1fb06a48dc7e1839a675529811a"
ADDENDUM_SHA256 = "486568d017de84bfba5aa8bb65f634998446ac4b3ad471795b9055085e8f5070"
PREFLIGHT_MANIFEST_SHA256 = "761436f04fe322679068e2482b672bee53628115872ef0bcf21be537ad2fc446"
BASE_PREFLIGHT_SHA256 = "311c1410446ee0e2748e25ae08633a586eccff7be68700b994c433f3feb80c39"
COMPOSITION_SERVER_SHA256 = "bf19fde6b9a97644b642a18e7cc19103e25f4d5a8c2a3434871d2c87186b2852"
COMPOSITION_RUNTIME_SHA256 = "366bb654a1b6c6d1d4a7146533b0a6556f64cf1b86c9aee68e2b9764bc39b168"
FULL_RUNNER_SHA256 = "674db977dccfff21931ca67d3f4146c235cd957c9e0a453fe57bcae0777e503d"

CONTRACT_RELATIVE = "docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md"
ADDENDUM_RELATIVE = "docs/MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md"
BASE_PREFLIGHT_RELATIVE = f"{R6_DIR_NAME}/preflight_v023_lcsrs_r6.py"
COMPOSITION_SERVER_RELATIVE = f"{R6_DIR_NAME}/run_v023_lcsrs_composition_server.py"
COMPOSITION_RUNTIME_RELATIVE = f"{R6_DIR_NAME}/v023_lcsrs_composition_runtime.py"
FULL_RUNNER_RELATIVE = f"{R6_DIR_NAME}/run_v023_lcsrs_full_gate_server.sh"

WORLDS = (2026121705, 2026121706, 2026121707, 2026121708, 2026121709, 2026121710, 2026121711, 2026121712)
STUDENT_SEEDS = (2026135101, 2026135102, 2026135103)
ARMS = ("INFORMED", "MATCHED_PLACEBO")
TARGETS = (
    (2026121712, 2026135102, "INFORMED"),
    (2026121712, 2026135102, "MATCHED_PLACEBO"),
    (2026121712, 2026135103, "INFORMED"),
    (2026121712, 2026135103, "MATCHED_PLACEBO"),
)

MAIN_COMPOSITION_JOBS = 2
ACCELERATOR_COMPOSITION_JOBS = 4
MAX_TOTAL_COMPOSITION_WORKERS = 6
FIT_UPDATES = 2000
CLAIM_CEILING = "TRAIN_DEVELOPMENT_SOURCE_AND_LEARNER_GATE_NO_TEST_NO_EPISODE_TRAINING_NO_EFFICACY"
COMPOSITION_SCHEMA = "multi-catfish-mcrl-v023-lcsrs-composition-artifact-v1"
FIT_SCHEMA = "multi-catfish-mcrl-v023-lcsrs-observability-gate-v1-fit-shard"
LAUNCH_METADATA_SCHEMA = "multi-catfish-mcrl-v023-lcsrs-server-run-v1"
ACCELERATOR_SCHEMA = "multi-catfish-mcrl-v023-r6-composition-accelerator-preflight-v1"
MEMORY_PROOF_SCHEMA = "v023-r6-composition-worker-memory-proof-v1"
EXPECTED_TLE_ROOT = "/home/sat/mcrl-runtime/tle-frozen-20260820"

EXIT_ERROR = 2
EXIT_SKIP = 3
EXIT_NO_GO = 4


class AcceleratorPreflightError(RuntimeError):
    """A live, provenance, identity, or resource safety gate failed."""


def canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise AcceleratorPreflightError("value is not canonical finite ASCII JSON") from error


def file_sha256(path: Path, *, field: str = "file") -> str:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise AcceleratorPreflightError(f"{field} is missing or symlinked: {target}")
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise AcceleratorPreflightError(f"{field} is not a lowercase SHA-256")
    return value


def read_canonical_json(path: Path, *, field: str) -> dict[str, Any]:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise AcceleratorPreflightError(f"{field} is missing or symlinked: {target}")
    raw = target.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AcceleratorPreflightError(f"{field} is not ASCII JSON") from error
    if not isinstance(payload, dict) or raw not in (canonical_bytes(payload), canonical_bytes(payload) + b"\n"):
        raise AcceleratorPreflightError(f"{field} is not canonical JSON")
    return payload


def _regular_dir(path: Path, *, field: str) -> Path:
    target = Path(path)
    if target.is_symlink() or not target.is_dir():
        raise AcceleratorPreflightError(f"{field} is missing or symlinked: {target}")
    return target.resolve()


def _safe_relative(root: Path, value: object, *, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise AcceleratorPreflightError(f"{field} path is empty")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise AcceleratorPreflightError(f"{field} path escapes its root")
    root_resolved = Path(root).resolve()
    candidate = root_resolved / relative
    if candidate.is_symlink():
        raise AcceleratorPreflightError(f"{field} path is symlinked")
    resolved = candidate.resolve(strict=False)
    if not resolved.is_relative_to(root_resolved):
        raise AcceleratorPreflightError(f"{field} path escapes its root")
    return resolved


def _safe_child(root: Path, value: object, *, field: str) -> Path:
    target = _safe_relative(root, value, field=field)
    if target.is_symlink() or not target.is_file():
        raise AcceleratorPreflightError(f"{field} is missing or symlinked: {target}")
    return target


@dataclass(frozen=True)
class Target:
    world: int
    seed: int
    arm: str

    @property
    def arm_name(self) -> str:
        return self.arm.lower()

    def output_relative(self) -> str:
        return f"composition/world-{self.world}/seed-{self.seed}/{self.arm_name}.json"

    def fit_relative(self) -> str:
        return f"fit/world-{self.world}/seed-{self.seed}/{self.arm_name}.json"


def target_from_tuple(value: tuple[int, int, str]) -> Target:
    return Target(*value)


def target_paths(run_root: Path, target: Target) -> tuple[Path, Path, Path]:
    index = Path(run_root) / target.output_relative()
    arrays = index.with_name(index.stem + ".arrays.npz")
    sidecar = arrays.with_name(arrays.name + ".sha256")
    return index, arrays, sidecar


def _validate_digest_sidecar(path: Path, *, expected: str, target: Path, field: str) -> None:
    raw = path.read_bytes()
    expected_bytes = f"{expected}  {target.name}\n".encode("ascii")
    if raw != expected_bytes:
        raise AcceleratorPreflightError(f"{field} digest sidecar disagrees")


def _validate_npz_container(path: Path, *, field: str) -> None:
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if not names or len(names) != len(set(names)):
                raise AcceleratorPreflightError(f"{field} has no unique members")
            for name in names:
                member = Path(name)
                if member.is_absolute() or ".." in member.parts or not name.endswith(".npy"):
                    raise AcceleratorPreflightError(f"{field} has an unsafe member name")
            if archive.testzip() is not None:
                raise AcceleratorPreflightError(f"{field} has a corrupt member")
    except (OSError, zipfile.BadZipFile) as error:
        raise AcceleratorPreflightError(f"{field} is not a readable NPZ container") from error


def validate_existing_composition(
    run_root: Path,
    target: Target,
    *,
    preflight_sha256: str,
    source_manifest_sha256: str,
    fit_hashes: Mapping[str, str],
) -> dict[str, object]:
    """Validate all three immutable composition files before allowing a skip."""

    index, arrays, sidecar = target_paths(run_root, target)
    paths = (index, arrays, sidecar)
    if not all(path.exists() or path.is_symlink() for path in paths):
        raise AcceleratorPreflightError(
            f"partial composition output for {target.world}/{target.seed}/{target.arm}"
        )
    if any(path.is_symlink() or not path.is_file() for path in paths):
        raise AcceleratorPreflightError("existing composition output is not three regular files")
    payload = read_canonical_json(index, field="existing composition index")
    if payload.get("schema") != COMPOSITION_SCHEMA or payload.get("status") != "PASS_COMPOSITION_EVIDENCE":
        raise AcceleratorPreflightError("existing composition index is not a complete PASS artifact")
    expected_fields = {
        "claim_ceiling": CLAIM_CEILING,
        "contract_sha256": CONTRACT_SHA256,
        "preflight_manifest_sha256": preflight_sha256,
        "source_manifest_sha256": source_manifest_sha256,
        "split": "TRAIN_DEVELOPMENT",
        "held_out_world": target.world,
        "student_seed": target.seed,
        "arm": target.arm,
        "fit_receipt_sha256": fit_hashes["fit_receipt_sha256"],
        "fit_model_bytes_sha256": fit_hashes["model_bytes_sha256"],
        "fit_model_sha256": fit_hashes["model_sha256"],
        "fit_update_count": FIT_UPDATES,
        "fit_already_completed": True,
        "test_split_opened": False,
        "test_worlds": [],
        "episode_training": False,
        "learner_update": False,
        "scientific_decision_opened": False,
        "c3_decision": None,
    }
    for field, expected in expected_fields.items():
        if payload.get(field) != expected:
            raise AcceleratorPreflightError(f"existing composition {field} disagrees")
    receipt = payload.get("receipt_sha256")
    if digest(receipt, field="existing composition receipt_sha256") != hashlib.sha256(
        canonical_bytes({key: value for key, value in payload.items() if key != "receipt_sha256"})
    ).hexdigest():
        raise AcceleratorPreflightError("existing composition receipt seal disagrees")
    arrays_receipt = payload.get("arrays")
    if not isinstance(arrays_receipt, Mapping):
        raise AcceleratorPreflightError("existing composition arrays receipt is missing")
    if arrays_receipt.get("allow_pickle") is not False:
        raise AcceleratorPreflightError("existing composition arrays do not bind allow_pickle=false")
    if arrays_receipt.get("npz_relative_path") != arrays.name or arrays_receipt.get("npz_sha256_file") != sidecar.name:
        raise AcceleratorPreflightError("existing composition sidecar names drifted")
    arrays_sha256 = file_sha256(arrays, field="existing composition NPZ")
    if digest(arrays_receipt.get("npz_sha256"), field="existing composition NPZ sha256") != arrays_sha256:
        raise AcceleratorPreflightError("existing composition NPZ hash disagrees")
    _validate_digest_sidecar(sidecar, expected=arrays_sha256, target=arrays, field="existing composition NPZ")
    _validate_npz_container(arrays, field="existing composition NPZ")
    return {
        "status": "SKIP_EXISTING",
        "output": index.relative_to(run_root).as_posix(),
        "output_sha256": file_sha256(index, field="existing composition index"),
    }


def validate_fixed_inputs(repo: Path) -> dict[str, str]:
    """Bind the exact files used by the R6 full runner's composition command."""

    root = _regular_dir(repo, field="repository root")
    bindings = {
        CONTRACT_RELATIVE: CONTRACT_SHA256,
        ADDENDUM_RELATIVE: ADDENDUM_SHA256,
        BASE_PREFLIGHT_RELATIVE: BASE_PREFLIGHT_SHA256,
        COMPOSITION_SERVER_RELATIVE: COMPOSITION_SERVER_SHA256,
        COMPOSITION_RUNTIME_RELATIVE: COMPOSITION_RUNTIME_SHA256,
        FULL_RUNNER_RELATIVE: FULL_RUNNER_SHA256,
    }
    for relative, expected in bindings.items():
        actual = file_sha256(root / relative, field=relative)
        if actual != expected:
            raise AcceleratorPreflightError(
                f"R6 binding drifted for {relative}: expected {expected}, got {actual}"
            )
    manifest = root / R6_DIR_NAME / "PREFLIGHT-MANIFEST.json"
    manifest_digest = root / R6_DIR_NAME / "PREFLIGHT-MANIFEST.sha256"
    if file_sha256(manifest, field="R6 preflight manifest") != PREFLIGHT_MANIFEST_SHA256:
        raise AcceleratorPreflightError("R6 preflight manifest digest drifted")
    if manifest_digest.is_symlink() or not manifest_digest.is_file():
        raise AcceleratorPreflightError("R6 preflight digest sidecar is missing or symlinked")
    digest_line = manifest_digest.read_text(encoding="ascii").split()
    if digest_line != [PREFLIGHT_MANIFEST_SHA256, "PREFLIGHT-MANIFEST.json"]:
        raise AcceleratorPreflightError("R6 preflight digest sidecar drifted")
    manifest_payload = read_canonical_json(manifest, field="R6 preflight manifest")
    if manifest_payload.get("schema") != "multi-catfish-mcrl-v023-lcsrs-observability-preflight-r6-fit-binding-v1":
        raise AcceleratorPreflightError("R6 preflight schema drifted")
    configuration = manifest_payload.get("configuration")
    if not isinstance(configuration, Mapping):
        raise AcceleratorPreflightError("R6 preflight configuration is missing")
    if configuration.get("worlds") != list(WORLDS) or configuration.get("student_seeds") != list(STUDENT_SEEDS):
        raise AcceleratorPreflightError("R6 preflight world/seed panel drifted")
    if configuration.get("split") != "TRAIN_DEVELOPMENT" or configuration.get("test_split_opened") is not False or configuration.get("episode_training") is not False:
        raise AcceleratorPreflightError("R6 preflight crossed a closed boundary")
    tle = configuration.get("tle")
    if not isinstance(tle, Mapping) or tle.get("root_default") != EXPECTED_TLE_ROOT:
        raise AcceleratorPreflightError("R6 preflight TLE root drifted")
    return {
        "manifest_sha256": PREFLIGHT_MANIFEST_SHA256,
        "contract_sha256": CONTRACT_SHA256,
        "composition_server": str(root / COMPOSITION_SERVER_RELATIVE),
        "composition_runtime": str(root / COMPOSITION_RUNTIME_RELATIVE),
    }


def validate_launch_metadata(run_root: Path, *, preflight_sha256: str) -> None:
    payload = read_canonical_json(Path(run_root) / "LAUNCH-METADATA.json", field="R6 launch metadata")
    expected = {
        "schema": LAUNCH_METADATA_SCHEMA,
        "contract_sha256": CONTRACT_SHA256,
        "preflight_manifest_sha256": preflight_sha256,
        "device": "cpu",
        "split": "TRAIN_DEVELOPMENT",
        "test_split_opened": False,
        "episode_training": False,
        "source_count": 8,
        "fit_count": 48,
        "composition_count": 48,
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            raise AcceleratorPreflightError(f"R6 launch metadata {field} disagrees")


def validate_source_manifest(run_root: Path, *, preflight_sha256: str) -> str:
    path = Path(run_root) / "source-manifest.json"
    payload = read_canonical_json(path, field="R6 source manifest")
    expected = {
        "schema": "multi-catfish-mcrl-v023-lcsrs-observability-gate-v1-source-manifest",
        "status": "PASS",
        "contract_sha256": CONTRACT_SHA256,
        "preflight_manifest_sha256": preflight_sha256,
        "split": "TRAIN_DEVELOPMENT",
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "source_count": 8,
        "worlds": list(WORLDS),
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            raise AcceleratorPreflightError(f"R6 source manifest {field} disagrees")
    shards = payload.get("shards")
    entries = payload.get("entries")
    if not isinstance(shards, list) or shards != [
        {"world": world, "relative_name": f"source/world-{world}.json"} for world in WORLDS
    ]:
        raise AcceleratorPreflightError("R6 source manifest shard schedule drifted")
    if not isinstance(entries, list) or len(entries) != len(WORLDS):
        raise AcceleratorPreflightError("R6 source manifest entries are incomplete")
    for entry, world in zip(entries, WORLDS, strict=True):
        if not isinstance(entry, Mapping) or entry.get("world") != world or entry.get("relative_name") != f"source/world-{world}.json":
            raise AcceleratorPreflightError("R6 source manifest entry identity drifted")
        source = _safe_child(run_root, entry.get("relative_name"), field=f"source world {world}")
        if file_sha256(source, field=f"source world {world}") != digest(entry.get("sha256"), field=f"source world {world} sha256"):
            raise AcceleratorPreflightError(f"source world {world} hash disagrees with manifest")
    source_hash = digest(payload.get("source_manifest_sha256"), field="source_manifest_sha256")
    unsigned = dict(payload)
    unsigned.pop("source_manifest_sha256", None)
    unsigned.pop("manifest_sha256", None)
    if hashlib.sha256(canonical_bytes(unsigned)).hexdigest() != source_hash:
        raise AcceleratorPreflightError("R6 source manifest body seal disagrees")
    manifest_hash = digest(payload.get("manifest_sha256"), field="manifest_sha256")
    unsigned_manifest = dict(payload)
    unsigned_manifest.pop("manifest_sha256", None)
    if hashlib.sha256(canonical_bytes(unsigned_manifest)).hexdigest() != manifest_hash:
        raise AcceleratorPreflightError("R6 source manifest byte seal disagrees")
    return source_hash


def _fit_sidecar(root: Path, raw: object, *, field: str) -> tuple[Path, str]:
    if not isinstance(raw, Mapping):
        raise AcceleratorPreflightError(f"fit {field} receipt is missing")
    path = _safe_child(root, raw.get("path"), field=f"fit {field}")
    expected = digest(raw.get("sha256"), field=f"fit {field} sha256")
    actual = file_sha256(path, field=f"fit {field}")
    if actual != expected:
        raise AcceleratorPreflightError(f"fit {field} hash disagrees")
    return path, actual


def validate_fit_shard(
    run_root: Path,
    target: Target,
    *,
    preflight_sha256: str,
    source_manifest_sha256: str,
) -> dict[str, str]:
    path = Path(run_root) / target.fit_relative()
    payload = read_canonical_json(path, field=f"fit {target.world}/{target.seed}/{target.arm}")
    expected = {
        "schema": FIT_SCHEMA,
        "status": "PASS",
        "claim_ceiling": CLAIM_CEILING,
        "contract_sha256": CONTRACT_SHA256,
        "preflight_manifest_sha256": preflight_sha256,
        "source_manifest_sha256": source_manifest_sha256,
        "split": "TRAIN_DEVELOPMENT",
        "held_out_world": target.world,
        "student_seed": target.seed,
        "arm": target.arm,
        "update_count": FIT_UPDATES,
        "learner_update": True,
        "episode_training": False,
        "test_split_opened": False,
        "test_worlds": [],
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            raise AcceleratorPreflightError(f"fit {target.world}/{target.seed}/{target.arm} {field} disagrees")
    model_state = payload.get("model_state")
    metrics = payload.get("metrics")
    if not isinstance(model_state, Mapping) or not isinstance(metrics, Mapping):
        raise AcceleratorPreflightError("fit model/metrics sidecars are missing")
    fit_root = path.parent
    model_path, model_bytes_sha = _fit_sidecar(
        fit_root, {"path": model_state.get("path"), "sha256": model_state.get("npz_sha256")}, field="model NPZ"
    )
    model_digest_path = _safe_child(fit_root, model_state.get("npz_sha256_file"), field="fit model digest")
    _validate_digest_sidecar(model_digest_path, expected=model_bytes_sha, target=model_path, field="fit model")
    metrics_path, metrics_sha = _fit_sidecar(fit_root, {"path": metrics.get("path"), "sha256": metrics.get("sha256")}, field="metrics JSON")
    metrics_npz_path, metrics_npz_sha = _fit_sidecar(
        fit_root,
        {"path": metrics.get("npz_path"), "sha256": metrics.get("npz_sha256")},
        field="metrics NPZ",
    )
    metrics_digest_path = _safe_child(fit_root, metrics.get("npz_sha256_file"), field="fit metrics digest")
    _validate_digest_sidecar(metrics_digest_path, expected=metrics_npz_sha, target=metrics_npz_path, field="fit metrics")
    _validate_npz_container(model_path, field="fit model NPZ")
    _validate_npz_container(metrics_npz_path, field="fit metrics NPZ")
    placebo_path, placebo_sha = _fit_sidecar(fit_root, payload.get("placebo"), field="placebo")
    fit_receipt_path, fit_receipt_sha = _fit_sidecar(fit_root, payload.get("fit_receipt"), field="fit receipt")
    read_canonical_json(fit_receipt_path, field="fit receipt sidecar")
    if digest(payload.get("model_sha256"), field="fit model_sha256") != model_bytes_sha:
        raise AcceleratorPreflightError("fit top-level model_sha256 disagrees")
    model_logical_sha = digest(payload.get("network_sha256"), field="fit network_sha256")
    if digest(payload.get("metrics_sha256"), field="fit metrics_sha256") != metrics_sha:
        raise AcceleratorPreflightError("fit top-level metrics_sha256 disagrees")
    return {
        "fit_receipt_sha256": fit_receipt_sha,
        "model_bytes_sha256": model_bytes_sha,
        "model_sha256": model_logical_sha,
        "metrics_sha256": metrics_sha,
        "metrics_npz_sha256": metrics_npz_sha,
        "placebo_sha256": placebo_sha,
    }


@dataclass(frozen=True)
class ProcessSnapshot:
    pid: int
    argv: tuple[str, ...]

    @property
    def command(self) -> str:
        return " ".join(self.argv)


def list_processes(proc_root: Path = Path("/proc")) -> tuple[ProcessSnapshot, ...]:
    root = Path(proc_root)
    if root.is_symlink() or not root.is_dir():
        raise AcceleratorPreflightError(f"process root is missing or symlinked: {root}")
    result: list[ProcessSnapshot] = []
    for entry in sorted(root.iterdir(), key=lambda value: value.name):
        if not entry.name.isdigit() or entry.is_symlink():
            continue
        try:
            raw = (entry / "cmdline").read_bytes()
        except OSError:
            continue
        if not raw:
            continue
        argv = tuple(part.decode("utf-8", errors="replace") for part in raw.split(b"\0") if part)
        if argv:
            result.append(ProcessSnapshot(pid=int(entry.name), argv=argv))
    return tuple(result)


def _has_pair(argv: Sequence[str], name: str, value: str) -> bool:
    return any(argv[index] == name and index + 1 < len(argv) and argv[index + 1] == value for index in range(len(argv) - 1))


def _arg_value(argv: Sequence[str], name: str) -> str | None:
    for index, value in enumerate(argv[:-1]):
        if value == name:
            return argv[index + 1]
    return None


def validate_live_controller(
    *,
    server_root: Path,
    run_root: Path,
    controller_pid: int,
    proc_root: Path,
    ignored_pids: Iterable[int] = (),
) -> dict[str, object]:
    processes = list_processes(proc_root)
    ignored = {int(pid) for pid in ignored_pids}
    controller_path = (Path(server_root).resolve() / "v023_lcsrs_gate_controller.sh").as_posix()
    controller = next((item for item in processes if item.pid == controller_pid), None)
    if controller is None or controller_pid in ignored or controller_path not in controller.command:
        raise AcceleratorPreflightError("live R6 controller pid/path evidence is missing")
    full_runner_name = "run_v023_lcsrs_full_gate_server.sh"
    full_runners = [
        item
        for item in processes
        if item.pid not in ignored
        and full_runner_name in item.command
        and str(Path(run_root).resolve()) in item.command
        and _has_pair(item.argv, "--composition-jobs", str(MAIN_COMPOSITION_JOBS))
    ]
    if len(full_runners) != 1:
        raise AcceleratorPreflightError(
            f"expected one live full runner with --composition-jobs 2, found {len(full_runners)}"
        )
    composition_workers: list[ProcessSnapshot] = []
    for item in processes:
        if item.pid in ignored or "run_v023_lcsrs_composition_server.py" not in item.command:
            continue
        output = _arg_value(item.argv, "--output")
        if output is None:
            raise AcceleratorPreflightError("live composition worker has no explicit output")
        if not Path(output).is_absolute():
            raise AcceleratorPreflightError("live composition worker output is not absolute")
        output_path = Path(output).resolve(strict=False)
        if output_path.is_relative_to(Path(run_root).resolve()):
            composition_workers.append(item)
    if len(composition_workers) > MAIN_COMPOSITION_JOBS:
        raise AcceleratorPreflightError("live composition worker count exceeds main --composition-jobs 2")
    return {
        "controller_pid": controller_pid,
        "full_runner_pids": [item.pid for item in full_runners],
        "main_active_composition_workers": len(composition_workers),
        "worker_pids": [item.pid for item in composition_workers],
        "max_total_composition_workers": MAX_TOTAL_COMPOSITION_WORKERS,
    }


def validate_no_target_worker(
    *,
    run_root: Path,
    target: Target,
    proc_root: Path,
    ignored_pids: Iterable[int] = (),
) -> None:
    target_output = (Path(run_root) / target.output_relative()).resolve(strict=False)
    ignored = {int(pid) for pid in ignored_pids}
    for item in list_processes(proc_root):
        if item.pid in ignored or "run_v023_lcsrs_composition_server.py" not in item.command:
            continue
        output = _arg_value(item.argv, "--output")
        if output is not None and Path(output).is_absolute() and Path(output).resolve(strict=False) == target_output:
            raise AcceleratorPreflightError(
                f"target composition worker is already active: {target.world}/{target.seed}/{target.arm}"
            )


def _read_mem_available(meminfo: Path) -> int:
    target = Path(meminfo)
    if target.is_symlink() or not target.is_file():
        raise AcceleratorPreflightError(f"memory info is missing or symlinked: {target}")
    for line in target.read_text(encoding="ascii").splitlines():
        match = re.fullmatch(r"MemAvailable:\s+(\d+)\s+kB", line)
        if match:
            return int(match.group(1)) * 1024
    raise AcceleratorPreflightError("MemAvailable is absent from memory info")


def validate_memory_proof(
    proof_path: Path,
    *,
    meminfo: Path,
    run_root: Path,
    preflight_sha256: str,
) -> dict[str, object]:
    payload = read_canonical_json(proof_path, field="composition memory proof")
    expected = {
        "schema": MEMORY_PROOF_SCHEMA,
        "contract_sha256": CONTRACT_SHA256,
        "preflight_manifest_sha256": preflight_sha256,
        "run_root": str(Path(run_root).resolve()),
        "main_composition_jobs": MAIN_COMPOSITION_JOBS,
        "accelerator_composition_jobs": ACCELERATOR_COMPOSITION_JOBS,
        "max_total_composition_workers": MAX_TOTAL_COMPOSITION_WORKERS,
        "worker_count": MAX_TOTAL_COMPOSITION_WORKERS,
        "device": "cpu",
        "bound_kind": "upper_bound",
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            raise AcceleratorPreflightError(f"memory proof {field} disagrees")
    peak = payload.get("per_worker_peak_rss_bytes")
    reserve = payload.get("reserve_bytes")
    if type(peak) is not int or peak <= 0 or type(reserve) is not int or reserve < 0:
        raise AcceleratorPreflightError("memory proof peak/reserve bytes are malformed")
    available = _read_mem_available(meminfo)
    required = peak * MAX_TOTAL_COMPOSITION_WORKERS + reserve
    if available < required:
        raise AcceleratorPreflightError(
            f"memory headroom is insufficient: available={available} required={required}"
        )
    return {
        "status": "MEMORY_PROOF_PASS",
        "available_bytes": available,
        "required_bytes": required,
        "per_worker_peak_rss_bytes": peak,
        "reserve_bytes": reserve,
    }


def _base_receipt(*, status: str, run_root: Path, reason: str | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema": ACCELERATOR_SCHEMA,
        "status": status,
        "scientific_claim": False,
        "decision": None,
        "claim_ceiling": CLAIM_CEILING,
        "run_root": str(Path(run_root).resolve()),
        "contract_sha256": CONTRACT_SHA256,
        "preflight_manifest_sha256": PREFLIGHT_MANIFEST_SHA256,
        "worlds": list(WORLDS),
        "student_seeds": list(STUDENT_SEEDS),
        "arms": list(ARMS),
        "selected_targets": [
            {"world": world, "student_seed": seed, "arm": arm} for world, seed, arm in TARGETS
        ],
        "main_composition_jobs": MAIN_COMPOSITION_JOBS,
        "accelerator_composition_jobs": ACCELERATOR_COMPOSITION_JOBS,
        "max_total_composition_workers": MAX_TOTAL_COMPOSITION_WORKERS,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "no_formula_change": True,
        "no_seed_change": True,
        "no_world_change": True,
        "no_data_change": True,
        "no_scientific_decision": True,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if reason is not None:
        payload["reason"] = reason
    return payload


def _write_once(path: Path, payload: Mapping[str, object]) -> None:
    target = Path(path)
    if target.exists() or target.is_symlink():
        raise AcceleratorPreflightError(f"refusing to overwrite receipt: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = canonical_bytes(dict(payload)) + b"\n"
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640)
    except FileExistsError as error:
        raise AcceleratorPreflightError(f"refusing to overwrite receipt: {target}") from error
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            target.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def build_plan(
    *,
    repo: Path,
    run_root: Path,
    server_root: Path,
    controller_pid: int | None,
    memory_proof: Path | None,
    proc_root: Path,
    meminfo: Path,
    ignored_pids: Iterable[int] = (),
    only_target: Target | None = None,
    mode: str = "launch",
) -> dict[str, object]:
    if mode not in {"launch", "completion"}:
        raise AcceleratorPreflightError(f"unsupported mode: {mode}")
    fixed = validate_fixed_inputs(Path(repo))
    server = _regular_dir(server_root, field="server root")
    root = _regular_dir(run_root, field="R6 run root")
    if not root.is_relative_to(server):
        raise AcceleratorPreflightError("R6 run root is outside the declared server root")
    validate_launch_metadata(root, preflight_sha256=fixed["manifest_sha256"])
    source_manifest_sha256 = validate_source_manifest(root, preflight_sha256=fixed["manifest_sha256"])
    selected = (only_target,) if only_target is not None else tuple(target_from_tuple(item) for item in TARGETS)
    if any((item.world, item.seed, item.arm) not in TARGETS for item in selected):
        raise AcceleratorPreflightError("requested target is outside the four fixed tail shards")
    targets: list[dict[str, object]] = []
    ready_count = 0
    for target in selected:
        fit_hashes = validate_fit_shard(
            root,
            target,
            preflight_sha256=fixed["manifest_sha256"],
            source_manifest_sha256=source_manifest_sha256,
        )
        index, arrays, sidecar = target_paths(root, target)
        present = [path.exists() or path.is_symlink() for path in (index, arrays, sidecar)]
        if any(present):
            if not all(present):
                raise AcceleratorPreflightError(
                    f"partial output is present for {target.world}/{target.seed}/{target.arm}"
                )
            state = validate_existing_composition(
                root,
                target,
                preflight_sha256=fixed["manifest_sha256"],
                source_manifest_sha256=source_manifest_sha256,
                fit_hashes=fit_hashes,
            )
            target_status = dict(state)
        else:
            validate_no_target_worker(
                run_root=root,
                target=target,
                proc_root=proc_root,
                ignored_pids=ignored_pids,
            )
            target_status = {"status": "READY", "output": target.output_relative()}
            ready_count += 1
        targets.append(
            {
                "world": target.world,
                "student_seed": target.seed,
                "arm": target.arm,
                "fit": fit_hashes,
                **target_status,
            }
        )
    if mode == "completion":
        if any(item.get("status") != "SKIP_EXISTING" for item in targets):
            raise AcceleratorPreflightError("completion receipt requires all four composition outputs")
        receipt = _base_receipt(status="PASS_COMPOSITION_ACCELERATOR", run_root=root)
        receipt.update(
            {
                "source_manifest_sha256": source_manifest_sha256,
                "targets": targets,
                "resource": {"status": "NOT_REQUIRED_AFTER_COMPLETION"},
                "live_controller": {"status": "NOT_REQUIRED_AFTER_COMPLETION"},
                "runtime_module": fixed["composition_runtime"],
                "composition_server": fixed["composition_server"],
            }
        )
        return receipt
    if controller_pid is None:
        raise AcceleratorPreflightError("controller pid is required for a concurrent launch")
    live = validate_live_controller(
        server_root=server,
        run_root=root,
        controller_pid=controller_pid,
        proc_root=proc_root,
        ignored_pids=ignored_pids,
    )
    if ready_count == 0:
        receipt = _base_receipt(status="SKIP_EXISTING", run_root=root)
        receipt.update(
            {
                "source_manifest_sha256": source_manifest_sha256,
                "targets": targets,
                "resource": {"status": "NOT_REQUIRED_FOR_SAFE_SKIP"},
                "live_controller": live,
                "runtime_module": fixed["composition_runtime"],
                "composition_server": fixed["composition_server"],
            }
        )
        return receipt
    if memory_proof is None:
        raise AcceleratorPreflightError(
            "memory proof is required before adding four composition workers"
        )
    resource = validate_memory_proof(
        memory_proof,
        meminfo=meminfo,
        run_root=root,
        preflight_sha256=fixed["manifest_sha256"],
    )
    receipt = _base_receipt(status="READY_TO_LAUNCH", run_root=root)
    receipt.update(
        {
            "source_manifest_sha256": source_manifest_sha256,
            "targets": targets,
            "resource": resource,
            "live_controller": live,
            "runtime_module": fixed["composition_runtime"],
            "composition_server": fixed["composition_server"],
            "command_contract": {
                "device": "cpu",
                "runtime_factory": "build_runtime",
                "contract_sha256": CONTRACT_SHA256,
                "preflight_manifest_sha256": fixed["manifest_sha256"],
                "composition_jobs": ACCELERATOR_COMPOSITION_JOBS,
            },
        }
    )
    return receipt


def _parse_target(raw: Sequence[str] | None) -> Target | None:
    if raw is None:
        return None
    if len(raw) != 3:
        raise AcceleratorPreflightError("--only-target requires WORLD SEED ARM")
    try:
        target = Target(int(raw[0]), int(raw[1]), raw[2])
    except ValueError as error:
        raise AcceleratorPreflightError("--only-target identity is malformed") from error
    if (target.world, target.seed, target.arm) not in TARGETS:
        raise AcceleratorPreflightError("--only-target is outside the fixed tail panel")
    return target


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--repo-root", type=Path, default=REPO)
    value.add_argument("--run-root", type=Path, required=True)
    value.add_argument("--server-root", type=Path, required=True)
    value.add_argument("--controller-pid", type=int)
    value.add_argument("--memory-proof", type=Path)
    value.add_argument("--proc-root", type=Path, default=Path("/proc"))
    value.add_argument("--meminfo", type=Path, default=Path("/proc/meminfo"))
    value.add_argument("--ignore-pid", type=int, action="append", default=[])
    value.add_argument("--only-target", nargs=3, metavar=("WORLD", "SEED", "ARM"))
    value.add_argument("--mode", choices=("launch", "completion"), default="launch")
    value.add_argument("--receipt", type=Path)
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        target = _parse_target(args.only_target)
        receipt = build_plan(
            repo=args.repo_root,
            run_root=args.run_root,
            server_root=args.server_root,
            controller_pid=args.controller_pid,
            memory_proof=args.memory_proof,
            proc_root=args.proc_root,
            meminfo=args.meminfo,
            ignored_pids=args.ignore_pid,
            only_target=target,
            mode=args.mode,
        )
    except AcceleratorPreflightError as error:
        payload = _base_receipt(status="NO-GO", run_root=args.run_root, reason=str(error))
        if args.receipt is not None:
            try:
                _write_once(args.receipt, payload)
            except AcceleratorPreflightError:
                pass
        print(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
        return EXIT_NO_GO
    if args.receipt is not None:
        try:
            _write_once(args.receipt, receipt)
        except AcceleratorPreflightError as error:
            print(f"ACCELERATOR_PREFLIGHT_ERROR: {error}", file=sys.stderr)
            return EXIT_ERROR
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    if receipt["status"] == "SKIP_EXISTING":
        return EXIT_SKIP
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
