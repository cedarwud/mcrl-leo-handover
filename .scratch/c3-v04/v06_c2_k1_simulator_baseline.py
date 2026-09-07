#!/usr/bin/env python3
"""Freeze and verify the pre-learner simulator source closure for C2-k1.

PREPARE_LIVE bound the production simulator manifest before the bounded
learner implementation existed.  The learner files live below ``src/mcrl``
and therefore appear in the legacy broad production manifest even though they
do not implement simulator physics.  This helper preserves fail-closed
provenance without pretending that the broad manifest stayed byte-identical:

* ``capture`` must run on the untouched T1 checkout and persists every frozen
  path and digest whose aggregate equals PREPARE_LIVE;
* later verification requires every baseline byte to remain identical and
  permits exactly the declared learner-only extension paths, with their bytes
  supplied and checked by the caller's pre-reveal code authority.

No command reads a T1 shard, target, counterfactual outcome, or verdict.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

BASELINE_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-simulator-baseline-v1"
BASELINE_SEAL_SCHEMA = (
    "multi-catfish-mcrl-v06-c2-k1-simulator-baseline-seal-v1"
)
BASELINE_STATUS = "PRE_LEARNER_SIMULATOR_BASELINE_FROZEN"

# These files are learner/provenance machinery only.  None is imported by the
# T1 source producer.  Their exact bytes are independently bound by the
# bounded-screen pre-reveal code authority before any source result is opened.
LEARNER_EXTENSION_PATHS = (
    "src/mcrl/algorithms/ee_axis_v06_c2_k1.py",
    "src/mcrl/runtime/ee_axis_v06_c2_k1_formal_verdict_writer.py",
    "src/mcrl/runtime/ee_axis_v06_c2_k1_learner.py",
    "src/mcrl/runtime/ee_axis_v06_c2_k1_learner_contract_v2.py",
    "src/mcrl/runtime/ee_axis_v06_c2_k1_learner_prep.py",
    "src/mcrl/runtime/ee_axis_v06_c2_k1_q13.py",
    "src/mcrl/runtime/ee_axis_v06_c2_k1_state_authority.py",
)

_BASELINE_FIELDS = frozenset(
    {
        "schema",
        "status",
        "prepare_sha256",
        "prepare_file_sha256",
        "simulator_manifest_schema",
        "simulator_source_manifest_sha256",
        "files",
        "declared_learner_extension_paths",
        "extension_paths_present_at_capture",
        "captured_before_learner_extension",
        "source_outcome_opened",
        "training",
        "test_split_opened",
        "attempt",
        "retry",
        "replacement",
        "baseline_sha256",
    }
)
_SEAL_FIELDS = frozenset(
    {
        "schema",
        "baseline_sha256",
        "baseline_file_sha256",
        "prepare_sha256",
        "simulator_source_manifest_sha256",
        "files",
        "write_once",
        "source_outcome_opened",
        "training",
        "test_split_opened",
        "attempt",
        "retry",
        "replacement",
    }
)


class SimulatorBaselineError(RuntimeError):
    """The baseline or its learner-only extension is stale or malformed."""


def _canonical_bytes(payload: object) -> bytes:
    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise SimulatorBaselineError("payload is not canonical finite JSON") from error


def _canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _file_sha256(path: Path) -> str:
    candidate = Path(path)
    if candidate.is_symlink() or not candidate.is_file():
        raise SimulatorBaselineError(f"authority is not a regular file: {candidate}")
    return hashlib.sha256(candidate.read_bytes()).hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise SimulatorBaselineError(f"{field} must be a lowercase SHA-256")
    return value


def _json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SimulatorBaselineError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_json(path: Path) -> dict[str, Any]:
    candidate = Path(path)
    if candidate.is_symlink() or not candidate.is_file():
        raise SimulatorBaselineError(f"JSON authority is not a regular file: {candidate}")
    try:
        payload = json.loads(
            candidate.read_bytes().decode("ascii"),
            object_pairs_hook=_json_object,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise SimulatorBaselineError(f"invalid JSON authority: {candidate}") from error
    if not isinstance(payload, dict):
        raise SimulatorBaselineError(f"JSON authority root is not an object: {candidate}")
    return payload


def _write_once_json(path: Path, payload: Mapping[str, Any]) -> str:
    destination = Path(path)
    if destination.exists() or destination.is_symlink():
        raise SimulatorBaselineError(f"refusing to overwrite: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as stream:
        stream.write(_canonical_bytes(payload))
    return _file_sha256(destination)


def _exact_keys(
    value: object, expected: frozenset[str], *, field: str
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise SimulatorBaselineError(f"{field} fields drifted")
    return value


def _manifest_files(
    manifest: Mapping[str, Any], *, field: str
) -> tuple[dict[str, str], list[dict[str, str]]]:
    schema = manifest.get("schema")
    files = manifest.get("files")
    supplied = _digest(
        manifest.get("source_manifest_sha256"),
        field=f"{field}.source_manifest_sha256",
    )
    if not isinstance(schema, str) or not schema or not isinstance(files, list):
        raise SimulatorBaselineError(f"{field} manifest shape drifted")
    normalized: list[dict[str, str]] = []
    mapping: dict[str, str] = {}
    previous = ""
    for index, raw in enumerate(files):
        if not isinstance(raw, Mapping) or set(raw) != {"path", "sha256"}:
            raise SimulatorBaselineError(f"{field} file[{index}] fields drifted")
        path = raw.get("path")
        sha256 = _digest(raw.get("sha256"), field=f"{field}.file[{index}].sha256")
        if (
            not isinstance(path, str)
            or not path
            or path.startswith("/")
            or ".." in Path(path).parts
            or path <= previous
            or path in mapping
        ):
            raise SimulatorBaselineError(f"{field} file order/path drifted")
        previous = path
        mapping[path] = sha256
        normalized.append({"path": path, "sha256": sha256})
    body = {"schema": schema, "files": normalized}
    if _canonical_sha256(body) != supplied:
        raise SimulatorBaselineError(f"{field} aggregate digest drifted")
    return mapping, normalized


def _prepare_binding(prepare_path: Path) -> dict[str, str]:
    prepare = _read_json(prepare_path)
    prepare_sha = _digest(prepare.get("prepare_sha256"), field="prepare_sha256")
    simulator_sha = _digest(
        prepare.get("simulator_source_manifest_sha256"),
        field="simulator_source_manifest_sha256",
    )
    if (
        prepare.get("training") is not False
        or prepare.get("test_split_opened") is not False
        or prepare.get("outcome_selection") is not False
        or prepare.get("prepared_before_generation") is not True
    ):
        raise SimulatorBaselineError("PREPARE is not target-free pre-generation authority")
    return {
        "prepare_sha256": prepare_sha,
        "prepare_file_sha256": _file_sha256(prepare_path),
        "simulator_source_manifest_sha256": simulator_sha,
    }


def _production_manifest(support: Any) -> dict[str, Any]:
    manifest = support._production_source_manifest(support._production_modules())
    if not isinstance(manifest, dict):
        raise SimulatorBaselineError("production manifest is not an object")
    _manifest_files(manifest, field="production")
    return manifest


def capture_baseline(
    *, support: Any, prepare_path: Path, output_dir: Path
) -> dict[str, Any]:
    """Persist the exact untouched simulator manifest before learner sync."""

    root = Path(output_dir)
    if root.exists() or root.is_symlink():
        raise SimulatorBaselineError(f"refusing to overwrite baseline directory: {root}")
    prepare = _prepare_binding(prepare_path)
    manifest = _production_manifest(support)
    mapping, files = _manifest_files(manifest, field="production")
    if (
        manifest["source_manifest_sha256"]
        != prepare["simulator_source_manifest_sha256"]
    ):
        raise SimulatorBaselineError("production manifest does not equal PREPARE")
    present = sorted(set(mapping).intersection(LEARNER_EXTENSION_PATHS))
    if present:
        raise SimulatorBaselineError(
            "learner extension already exists before baseline capture: "
            + ", ".join(present)
        )
    body: dict[str, Any] = {
        "schema": BASELINE_SCHEMA,
        "status": BASELINE_STATUS,
        "prepare_sha256": prepare["prepare_sha256"],
        "prepare_file_sha256": prepare["prepare_file_sha256"],
        "simulator_manifest_schema": manifest["schema"],
        "simulator_source_manifest_sha256": manifest[
            "source_manifest_sha256"
        ],
        "files": files,
        "declared_learner_extension_paths": list(LEARNER_EXTENSION_PATHS),
        "extension_paths_present_at_capture": [],
        "captured_before_learner_extension": True,
        "source_outcome_opened": False,
        "training": False,
        "test_split_opened": False,
        "attempt": 1,
        "retry": False,
        "replacement": False,
    }
    payload = body | {"baseline_sha256": _canonical_sha256(body)}
    baseline_path = root / "simulator-baseline.json"
    baseline_file_sha = _write_once_json(baseline_path, payload)
    seal = {
        "schema": BASELINE_SEAL_SCHEMA,
        "baseline_sha256": payload["baseline_sha256"],
        "baseline_file_sha256": baseline_file_sha,
        "prepare_sha256": payload["prepare_sha256"],
        "simulator_source_manifest_sha256": payload[
            "simulator_source_manifest_sha256"
        ],
        "files": len(files),
        "write_once": True,
        "source_outcome_opened": False,
        "training": False,
        "test_split_opened": False,
        "attempt": 1,
        "retry": False,
        "replacement": False,
    }
    _write_once_json(root / "simulator-baseline-seal.json", seal)
    return payload


def verify_baseline_extension(
    *,
    support: Any,
    prepare_path: Path,
    baseline_path: Path,
    baseline_seal_path: Path,
    expected_extension_sha256: Mapping[str, str],
) -> dict[str, Any]:
    """Require frozen simulator bytes plus exactly the sealed learner files."""

    prepare = _prepare_binding(prepare_path)
    baseline = dict(
        _exact_keys(_read_json(baseline_path), _BASELINE_FIELDS, field="baseline")
    )
    seal = dict(
        _exact_keys(_read_json(baseline_seal_path), _SEAL_FIELDS, field="baseline seal")
    )
    unsigned = dict(baseline)
    supplied = _digest(unsigned.pop("baseline_sha256"), field="baseline_sha256")
    if _canonical_sha256(unsigned) != supplied:
        raise SimulatorBaselineError("baseline payload digest drifted")
    baseline_manifest = {
        "schema": baseline.get("simulator_manifest_schema"),
        "files": baseline.get("files"),
        "source_manifest_sha256": baseline.get(
            "simulator_source_manifest_sha256"
        ),
    }
    baseline_map, baseline_files = _manifest_files(
        baseline_manifest, field="baseline simulator"
    )
    expected_scalars = {
        "schema": BASELINE_SCHEMA,
        "status": BASELINE_STATUS,
        "prepare_sha256": prepare["prepare_sha256"],
        "prepare_file_sha256": prepare["prepare_file_sha256"],
        "simulator_source_manifest_sha256": prepare[
            "simulator_source_manifest_sha256"
        ],
        "declared_learner_extension_paths": list(LEARNER_EXTENSION_PATHS),
        "extension_paths_present_at_capture": [],
        "captured_before_learner_extension": True,
        "source_outcome_opened": False,
        "training": False,
        "test_split_opened": False,
        "attempt": 1,
        "retry": False,
        "replacement": False,
    }
    for field, expected in expected_scalars.items():
        if baseline.get(field) != expected:
            raise SimulatorBaselineError(f"baseline {field} drifted")
    expected_seal = {
        "schema": BASELINE_SEAL_SCHEMA,
        "baseline_sha256": supplied,
        "baseline_file_sha256": _file_sha256(baseline_path),
        "prepare_sha256": prepare["prepare_sha256"],
        "simulator_source_manifest_sha256": prepare[
            "simulator_source_manifest_sha256"
        ],
        "files": len(baseline_files),
        "write_once": True,
        "source_outcome_opened": False,
        "training": False,
        "test_split_opened": False,
        "attempt": 1,
        "retry": False,
        "replacement": False,
    }
    if seal != expected_seal:
        raise SimulatorBaselineError("baseline seal is invalid")

    current = _production_manifest(support)
    current_map, _ = _manifest_files(current, field="current production")
    missing = sorted(set(baseline_map) - set(current_map))
    changed = sorted(
        path
        for path, digest in baseline_map.items()
        if current_map.get(path) != digest
    )
    extras = sorted(set(current_map) - set(baseline_map))
    if missing or changed:
        raise SimulatorBaselineError(
            "frozen simulator closure drifted: missing="
            + repr(missing)
            + " changed="
            + repr(changed)
        )
    if extras != list(LEARNER_EXTENSION_PATHS):
        raise SimulatorBaselineError(
            "current manifest has an undeclared or missing learner extension: "
            + repr(extras)
        )
    if set(expected_extension_sha256) != set(LEARNER_EXTENSION_PATHS):
        raise SimulatorBaselineError("caller did not bind every learner extension path")
    extension_hashes = {
        path: _digest(
            expected_extension_sha256[path], field=f"extension digest {path}"
        )
        for path in LEARNER_EXTENSION_PATHS
    }
    observed_extension_hashes = {
        path: current_map[path] for path in LEARNER_EXTENSION_PATHS
    }
    if observed_extension_hashes != extension_hashes:
        raise SimulatorBaselineError("learner extension bytes drifted")
    return {
        "schema": "multi-catfish-mcrl-v06-c2-k1-simulator-extension-receipt-v1",
        "status": "SIMULATOR_BASELINE_AND_LEARNER_EXTENSION_VERIFIED",
        "baseline_sha256": supplied,
        "baseline_file_sha256": _file_sha256(baseline_path),
        "baseline_seal_file_sha256": _file_sha256(baseline_seal_path),
        "prepare_sha256": prepare["prepare_sha256"],
        "simulator_source_manifest_sha256": prepare[
            "simulator_source_manifest_sha256"
        ],
        "current_extended_manifest_sha256": current[
            "source_manifest_sha256"
        ],
        "baseline_files": len(baseline_files),
        "learner_extension_sha256": extension_hashes,
        "old_files_byte_identical": True,
        "only_declared_extensions_present": True,
        "source_outcome_opened": False,
        "training": False,
        "test_split_opened": False,
    }


def _load_support() -> Any:
    path = HERE / "run_v06_c2_k1_t1.py"
    name = "v06_c2_k1_t1_for_baseline_" + hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SimulatorBaselineError("cannot load frozen T1 runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module._support_census_loader()


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    capture = sub.add_parser("capture")
    capture.add_argument("--prepare", type=Path, required=True)
    capture.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command != "capture":  # pragma: no cover - argparse owns choices
            raise SimulatorBaselineError("unknown command")
        payload = capture_baseline(
            support=_load_support(),
            prepare_path=args.prepare,
            output_dir=args.output_dir,
        )
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "baseline_sha256": payload["baseline_sha256"],
                    "simulator_source_manifest_sha256": payload[
                        "simulator_source_manifest_sha256"
                    ],
                    "files": len(payload["files"]),
                    "source_outcome_opened": False,
                },
                sort_keys=True,
            )
        )
        return 0
    except (OSError, ValueError, TypeError, SimulatorBaselineError) as error:
        print(
            json.dumps(
                {"status": "SIMULATOR_BASELINE_INVALID", "error": str(error)},
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(_main())

