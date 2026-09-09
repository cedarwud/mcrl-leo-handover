"""Result-blind writer for the V0.6 C2-k1 T1 formal verdict.

The T1 runner owns source adjudication.  This module owns only the narrow
post-source seam: it authenticates the frozen PREPARE_LIVE chain, loads the
frozen runner dynamically, asks that runner to verify ``source.json``, and
serialises the disposition returned by that verification.  There is no
``disposition`` argument anywhere in the public API.  In particular, a
caller cannot turn a falsified source into an authorization by supplying a
literal.

The exact verdict artifact and seal bind both the T1-preregistration digest
and the verifier code-authority digest.  The existing ``prepare_sha256`` also
transitively binds the same T1 preregistration because the frozen runner
authenticates it in PREPARE_LIVE.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Mapping

from . import ee_axis_v06_c2_k1_learner_contract_v2 as contract


REPO = Path(__file__).resolve().parents[3]
RUNNER_PATH = REPO / ".scratch" / "c3-v04" / "run_v06_c2_k1_t1.py"

WRITER_RECEIPT_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-t1-formal-verdict-writer-receipt-v1"

# These fields must be supported by the imported exact contract schema.
_PROVENANCE_FIELDS = {
    "t1_prereg_file_sha256": "T1 preregistration file digest",
    "verifier_code_authority_sha256": "verifier code-authority digest",
}


class FormalVerdictWriterError(RuntimeError):
    """A formal-verdict request is malformed or fails closed."""


def _safe_file(value: object, *, field: str) -> Path:
    """Resolve one absolute regular non-symlink file."""

    if not isinstance(value, (str, os.PathLike)):
        raise FormalVerdictWriterError(f"{field} must be a filesystem path")
    try:
        candidate = Path(value)
        resolved = candidate.resolve(strict=False)
    except (TypeError, ValueError, OSError) as error:
        raise FormalVerdictWriterError(f"{field} is not a valid path") from error
    if not candidate.is_absolute():
        raise FormalVerdictWriterError(f"{field} must be an absolute path")
    if candidate.is_symlink() or resolved.is_symlink():
        raise FormalVerdictWriterError(f"{field} must not be a symlink")
    if not resolved.is_file():
        raise FormalVerdictWriterError(f"{field} must name a regular file")
    return resolved


def _safe_output_path(value: object, *, field: str, expected_name: str) -> Path:
    """Resolve an output path without following an existing symlink."""

    if not isinstance(value, (str, os.PathLike)):
        raise FormalVerdictWriterError(f"{field} must be a filesystem path")
    try:
        candidate = Path(value)
    except (TypeError, ValueError, OSError) as error:
        raise FormalVerdictWriterError(f"{field} is not a valid path") from error
    if not candidate.is_absolute():
        raise FormalVerdictWriterError(f"{field} must be an absolute path")
    if candidate.name != expected_name:
        raise FormalVerdictWriterError(
            f"{field} must use the canonical filename {expected_name}"
        )
    if candidate.is_symlink():
        raise FormalVerdictWriterError(f"{field} must not be a symlink")
    try:
        return candidate.resolve(strict=False)
    except OSError as error:
        raise FormalVerdictWriterError(f"{field} cannot be resolved") from error


def _safe_directory(value: object, *, field: str) -> Path:
    if not isinstance(value, (str, os.PathLike)):
        raise FormalVerdictWriterError(f"{field} must be a directory path")
    try:
        candidate = Path(value)
        resolved = candidate.resolve(strict=False)
    except (TypeError, ValueError, OSError) as error:
        raise FormalVerdictWriterError(f"{field} is not a valid path") from error
    if not candidate.is_absolute():
        raise FormalVerdictWriterError(f"{field} must be an absolute path")
    if candidate.is_symlink() or resolved.is_symlink():
        raise FormalVerdictWriterError(f"{field} must not be a symlink")
    if not resolved.is_dir():
        raise FormalVerdictWriterError(f"{field} must name an existing directory")
    return resolved


def _sha256_file(path: Path, *, field: str) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise FormalVerdictWriterError(f"cannot read {field}") from error


def _valid_digest(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _digest(value: object, *, field: str) -> str:
    if not _valid_digest(value):
        raise FormalVerdictWriterError(f"{field} is not a lowercase SHA-256 digest")
    return str(value)


def _load_frozen_runner(path: object | None = None) -> tuple[ModuleType, Path, str]:
    """Dynamically load exactly one content-addressed frozen T1 runner."""

    if path is None:
        path = RUNNER_PATH
    runner_path = _safe_file(path, field="frozen T1 runner path")
    runner_file_sha256 = _sha256_file(runner_path, field="frozen T1 runner")
    module_name = (
        "mcrl_v06_c2_k1_t1_formal_verdict_runner_"
        + runner_file_sha256[:20]
    )
    spec = importlib.util.spec_from_file_location(module_name, runner_path)
    if spec is None or spec.loader is None:
        raise FormalVerdictWriterError("cannot load the frozen T1 runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(module_name, None)
        raise
    return module, runner_path, runner_file_sha256


def _canonical_runner_read(runner: ModuleType, path: Path, *, field: str) -> dict[str, Any]:
    reader = getattr(runner, "_canonical_read", None)
    if not callable(reader):
        raise FormalVerdictWriterError("frozen T1 runner has no canonical JSON reader")
    try:
        payload = reader(path)
    except Exception as error:
        raise FormalVerdictWriterError(f"{field} failed frozen-runner validation") from error
    if not isinstance(payload, dict):
        raise FormalVerdictWriterError(f"{field} is not a JSON object")
    return payload


def _canonical_sha256(runner: ModuleType, payload: object, *, field: str) -> str:
    hasher = getattr(runner, "canonical_sha256", None)
    if not callable(hasher):
        raise FormalVerdictWriterError("frozen T1 runner has no canonical hash function")
    try:
        value = hasher(payload)
    except Exception as error:
        raise FormalVerdictWriterError(f"cannot hash {field}") from error
    return _digest(value, field=f"{field} digest")


def _source_payload_sha256(runner: ModuleType, source: Mapping[str, Any]) -> str:
    hasher = getattr(runner, "_source_payload_sha256", None)
    if not callable(hasher):
        raise FormalVerdictWriterError("frozen T1 runner has no source payload hash function")
    try:
        value = hasher(source)
    except Exception as error:
        raise FormalVerdictWriterError("cannot recompute source payload hash") from error
    return _digest(value, field="source payload")


def _prepare_payload_sha256(runner: ModuleType, prepare: Mapping[str, Any]) -> str:
    supplied = prepare.get("prepare_sha256")
    unsigned = dict(prepare)
    unsigned.pop("prepare_sha256", None)
    expected = _canonical_sha256(runner, unsigned, field="PREPARE_LIVE payload")
    if supplied != expected:
        raise FormalVerdictWriterError("PREPARE_LIVE payload digest is stale")
    return _digest(supplied, field="PREPARE_LIVE prepare_sha256")


def _validate_prepare_seal(
    runner: ModuleType,
    prepare_path: Path,
    prepare: Mapping[str, Any],
    t1_prereg_path: Path,
) -> dict[str, Any]:
    """Recompute prepare/seal/T1 hashes after the runner's authentication."""

    prepare_sha = _prepare_payload_sha256(runner, prepare)
    prepare_seal_path = prepare_path.with_name("prepare-live-seal.json")
    prepare_seal_path = _safe_file(
        prepare_seal_path, field="PREPARE_LIVE seal path"
    )
    seal = _canonical_runner_read(
        runner, prepare_seal_path, field="PREPARE_LIVE seal"
    )
    expected_schema = "multi-catfish-mcrl-v06-c2-k1-t1-prepare-live-seal-v2"
    expected_fields = {
        "schema",
        "prepare_sha256",
        "prepare_file_sha256",
        "training",
        "test_split_opened",
        "outcome_selection",
    }
    if set(seal) != expected_fields or seal.get("schema") != expected_schema:
        raise FormalVerdictWriterError("PREPARE_LIVE seal schema is not exact")
    prepare_file_sha256 = _sha256_file(prepare_path, field="PREPARE_LIVE file")
    if seal.get("prepare_sha256") != prepare_sha:
        raise FormalVerdictWriterError("PREPARE_LIVE seal payload digest drifted")
    if seal.get("prepare_file_sha256") != prepare_file_sha256:
        raise FormalVerdictWriterError("PREPARE_LIVE seal file digest drifted")
    if any(seal.get(name) is not False for name in (
        "training", "test_split_opened", "outcome_selection"
    )):
        raise FormalVerdictWriterError("PREPARE_LIVE seal opens a forbidden boundary")
    t1_file_sha256 = _sha256_file(t1_prereg_path, field="T1 preregistration")
    if prepare.get("t1_prereg_file_sha256") != t1_file_sha256:
        raise FormalVerdictWriterError("current T1 preregistration differs from PREPARE_LIVE")
    return {
        "prepare_path": str(prepare_path),
        "prepare_file_sha256": prepare_file_sha256,
        "prepare_payload_sha256": prepare_sha,
        "prepare_seal_path": str(prepare_seal_path),
        "prepare_seal_file_sha256": _sha256_file(
            prepare_seal_path, field="PREPARE_LIVE seal"
        ),
        "t1_prereg_path": str(t1_prereg_path),
        "t1_prereg_file_sha256": t1_file_sha256,
    }


def _validate_source_seal(
    runner: ModuleType,
    source_path: Path,
    source: Mapping[str, Any],
    source_seal_path: Path,
) -> dict[str, Any]:
    """Recompute both source hashes and authenticate source-seal.json."""

    source_payload_sha256 = _source_payload_sha256(runner, source)
    if source.get("source_sha256") != source_payload_sha256:
        raise FormalVerdictWriterError("source payload digest is stale")
    source_file_sha256 = _sha256_file(source_path, field="T1 source")
    source_seal = _canonical_runner_read(
        runner, source_seal_path, field="T1 source seal"
    )
    expected_fields = {
        "schema",
        "source_sha256",
        "source_file_sha256",
        "prepare_sha256",
        "training",
        "test_split_opened",
        "outcome_selection",
    }
    source_seal_schema = getattr(
        runner, "SOURCE_SEAL_SCHEMA", contract.T1_SOURCE_SEAL_SCHEMA
    )
    if (
        source_seal_schema != contract.T1_SOURCE_SEAL_SCHEMA
        or set(source_seal) != expected_fields
        or source_seal.get("schema") != source_seal_schema
    ):
        raise FormalVerdictWriterError("T1 source-seal schema is not exact")
    # ``source.json.source_sha256`` excludes its own field.  The runner's
    # source seal, matching ``seal_source``, records the canonical digest of
    # the complete source object (including that field).  Keep the two
    # distinct; conflating them would reject a genuine runner seal.
    source_seal_payload_sha256 = _canonical_sha256(
        runner, source, field="T1 source payload for seal"
    )
    if source_seal.get("source_sha256") != source_seal_payload_sha256:
        raise FormalVerdictWriterError("T1 source-seal payload digest drifted")
    if source_seal.get("source_file_sha256") != source_file_sha256:
        raise FormalVerdictWriterError("T1 source-seal file digest drifted")
    if source_seal.get("prepare_sha256") != source.get("prepare_sha256"):
        raise FormalVerdictWriterError("T1 source-seal prepare authority drifted")
    if any(source_seal.get(name) is not False for name in (
        "training", "test_split_opened", "outcome_selection"
    )):
        raise FormalVerdictWriterError("T1 source seal opens a forbidden boundary")
    return {
        "source_path": str(source_path),
        "source_file_sha256": source_file_sha256,
        "source_payload_sha256": source_payload_sha256,
        "source_seal_path": str(source_seal_path),
        "source_seal_file_sha256": _sha256_file(
            source_seal_path, field="T1 source seal"
        ),
        "source_seal_payload_sha256": _canonical_sha256(
            runner, source_seal, field="T1 source seal payload"
        ),
        "source_seal_source_sha256": source_seal_payload_sha256,
    }


def _verifier_code_authority(
    runner: ModuleType, runner_path: Path, runner_file_sha256: str
) -> tuple[str, str | None]:
    """Return the runner's sealed code-authority digest and optional detail."""

    manifest_builder = getattr(runner, "_code_authority_manifest", None)
    if callable(manifest_builder):
        try:
            manifest = manifest_builder()
        except Exception as error:
            raise FormalVerdictWriterError(
                "frozen T1 runner code authority could not be recomputed"
            ) from error
        if not isinstance(manifest, Mapping) or not _valid_digest(manifest.get("sha256")):
            raise FormalVerdictWriterError(
                "frozen T1 runner code authority is malformed"
            )
        return str(manifest["sha256"]), runner_file_sha256
    # A test-only/future runner without the optional manifest still has a
    # content-addressed code file.  Record that fact in the writer receipt;
    # production PREPARE_LIVE authentication requires the full manifest.
    return runner_file_sha256, runner_file_sha256


def _contract_exact_fields(name: str) -> frozenset[str]:
    value = getattr(contract, name, None)
    if not isinstance(value, (set, frozenset)):
        raise FormalVerdictWriterError(f"learner contract does not expose {name}")
    return frozenset(str(item) for item in value)


def _add_supported_provenance(
    artifact: dict[str, Any],
    seal: dict[str, Any],
    *,
    t1_prereg_file_sha256: str,
    verifier_code_authority_sha256: str,
) -> list[str]:
    """Bind amendment fields only when the exact shared schema supports them."""

    artifact_fields = _contract_exact_fields("_ARTIFACT_FIELDS")
    seal_fields = _contract_exact_fields("_SEAL_FIELDS")
    values = {
        "t1_prereg_file_sha256": t1_prereg_file_sha256,
        "verifier_code_authority_sha256": verifier_code_authority_sha256,
    }
    gaps: list[str] = []
    for name, description in _PROVENANCE_FIELDS.items():
        locations = []
        if name in artifact_fields:
            artifact[name] = values[name]
            locations.append("artifact")
        if name in seal_fields:
            seal[name] = values[name]
            locations.append("seal")
        if not locations:
            gaps.append(f"{name}: {description} absent from current exact schema")
    return gaps


def _evaluate_request(
    prepare_path: object,
    t1_prereg_path: object,
    source_path: object,
    source_seal_path: object | None,
) -> dict[str, Any]:
    """Authenticate all input paths and build the exact current artifact."""

    prepare = _safe_file(prepare_path, field="PREPARE_LIVE path")
    if prepare.name != "prepare-live.json":
        raise FormalVerdictWriterError(
            "PREPARE_LIVE path must use the canonical filename prepare-live.json"
        )
    t1_prereg = _safe_file(t1_prereg_path, field="T1 preregistration path")
    source = _safe_file(source_path, field="T1 source path")
    if source.name != "source.json":
        raise FormalVerdictWriterError(
            "T1 source path must use the canonical filename source.json"
        )
    if source_seal_path is None:
        source_seal = _safe_file(
            source.with_name("source-seal.json"), field="T1 source seal path"
        )
    else:
        source_seal = _safe_file(source_seal_path, field="T1 source seal path")
    if source_seal.name != "source-seal.json":
        raise FormalVerdictWriterError(
            "T1 source seal path must use the canonical filename source-seal.json"
        )
    if source_seal.parent != source.parent:
        raise FormalVerdictWriterError(
            "T1 source and source-seal must be sibling files"
        )

    runner, runner_file, runner_file_sha256 = _load_frozen_runner()
    read_prepare = getattr(runner, "_read_formal_prepare", None)
    verify_source = getattr(runner, "verify_source", None)
    if not callable(read_prepare) or not callable(verify_source):
        raise FormalVerdictWriterError(
            "frozen T1 runner lacks _read_formal_prepare or verify_source"
        )
    try:
        prepared_payload = read_prepare(prepare, t1_prereg)
    except Exception as error:
        raise FormalVerdictWriterError(
            "formal PREPARE_LIVE plus T1 preregistration authentication failed"
        ) from error
    if not isinstance(prepared_payload, Mapping):
        raise FormalVerdictWriterError("frozen runner returned malformed PREPARE_LIVE")
    prepared = dict(prepared_payload)
    prepare_receipt = _validate_prepare_seal(
        runner, prepare, prepared, t1_prereg
    )

    source_payload = _canonical_runner_read(runner, source, field="T1 source")
    source_receipt = _validate_source_seal(
        runner, source, source_payload, source_seal
    )
    try:
        verification = verify_source(source_payload, prepared)
    except Exception as error:
        raise FormalVerdictWriterError(
            "frozen T1 verify_source rejected the source artifact"
        ) from error
    if not isinstance(verification, Mapping):
        raise FormalVerdictWriterError("frozen T1 verify_source returned malformed evidence")
    status = verification.get("status")
    if status != "VERIFIED":
        raise FormalVerdictWriterError("frozen T1 verify_source did not return VERIFIED")
    disposition = verification.get("disposition")
    allowed = {
        contract.FORMAL_LEARNER_VERDICT,
        contract.SOURCE_FALSIFIED_VERDICT,
    }
    if disposition not in allowed:
        raise FormalVerdictWriterError(
            "frozen T1 verify_source returned an inadmissible disposition"
        )
    gates = verification.get("gates")
    if not isinstance(gates, Mapping) or type(gates.get("launchable")) is not bool:
        raise FormalVerdictWriterError("frozen T1 verify_source returned malformed gates")
    expected_disposition = (
        contract.FORMAL_LEARNER_VERDICT
        if gates["launchable"]
        else contract.SOURCE_FALSIFIED_VERDICT
    )
    if disposition != expected_disposition:
        raise FormalVerdictWriterError(
            "frozen T1 disposition disagrees with its verified gates"
        )
    if verification.get("pairs") != 1008 or verification.get("controls") != 36:
        raise FormalVerdictWriterError(
            "frozen T1 verify_source returned unexpected cardinality"
        )

    artifact: dict[str, Any] = {
        "schema": contract.FORMAL_VERDICT_ARTIFACT_SCHEMA,
        "status": "VERIFIED",
        "disposition": str(disposition),
        "source_schema": contract.T1_SOURCE_SCHEMA,
        "source_seal_schema": contract.T1_SOURCE_SEAL_SCHEMA,
        "source_path": source_receipt["source_path"],
        "source_file_sha256": source_receipt["source_file_sha256"],
        "source_payload_sha256": source_receipt["source_payload_sha256"],
        "source_seal_path": source_receipt["source_seal_path"],
        "source_seal_file_sha256": source_receipt["source_seal_file_sha256"],
        "prepare_sha256": prepare_receipt["prepare_payload_sha256"],
        "counts": {"pairs": 1008, "controls": 36},
        "gates": copy.deepcopy(dict(gates)),
        "training": False,
        "test_split_opened": False,
        "outcome_selection": False,
        "q2_consulted": False,
        "write_once": True,
        "attempt": 1,
        "retry": False,
        "replacement": False,
    }
    verifier_code_authority_sha256, verifier_file_sha256 = _verifier_code_authority(
        runner, runner_file, runner_file_sha256
    )
    sealed_code_authority = prepared.get("code_authority")
    if isinstance(sealed_code_authority, Mapping):
        if sealed_code_authority.get("sha256") != verifier_code_authority_sha256:
            raise FormalVerdictWriterError(
                "PREPARE_LIVE code-authority digest differs from the verifier"
            )
    # Keep the exact shared contract shape authoritative.
    provisional_seal: dict[str, Any] = {}
    schema_gap = _add_supported_provenance(
        artifact,
        provisional_seal,
        t1_prereg_file_sha256=prepare_receipt["t1_prereg_file_sha256"],
        verifier_code_authority_sha256=verifier_code_authority_sha256,
    )
    artifact["verdict_sha256"] = _canonical_sha256(
        runner, artifact, field="formal verdict artifact"
    )
    artifact_fields = _contract_exact_fields("_ARTIFACT_FIELDS")
    if set(artifact) != artifact_fields:
        raise FormalVerdictWriterError(
            "writer cannot emit the current exact formal-verdict artifact schema"
        )

    return {
        "artifact": artifact,
        "prepare": prepare_receipt,
        "source": source_receipt,
        "runner_path": str(runner_file),
        "runner_file_sha256": runner_file_sha256,
        "verifier_file_sha256": verifier_file_sha256,
        "verifier_code_authority_sha256": verifier_code_authority_sha256,
        "schema_gap": schema_gap,
        "verification": dict(verification),
    }


def build_formal_verdict(
    prepare_path: object,
    t1_prereg_path: object,
    source_path: object,
    *,
    source_seal_path: object | None = None,
) -> dict[str, Any]:
    """Return an authenticated exact-schema verdict without writing files."""

    return dict(
        _evaluate_request(
            prepare_path, t1_prereg_path, source_path, source_seal_path
        )["artifact"]
    )


def _write_once_json(path: Path, payload: Mapping[str, Any]) -> str:
    """Write canonical JSON with O_EXCL and return its file SHA-256."""

    try:
        data = contract.canonical_bytes(payload)
    except Exception as error:
        raise FormalVerdictWriterError("formal verdict is not canonical finite JSON") from error
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o644)
    except FileExistsError as error:
        raise FormalVerdictWriterError(f"write-once target already exists: {path}") from error
    except OSError as error:
        raise FormalVerdictWriterError(f"cannot create write-once target: {path}") from error
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as error:
        raise FormalVerdictWriterError(f"cannot write write-once target: {path}") from error
    return hashlib.sha256(data).hexdigest()


def write_formal_verdict(
    prepare_path: object,
    t1_prereg_path: object,
    source_path: object,
    output_dir: object,
    *,
    source_seal_path: object | None = None,
    formal_verdict_path: object | None = None,
    formal_verdict_seal_path: object | None = None,
) -> dict[str, Any]:
    """Write one result-blind formal-verdict artifact and its file seal.

    The return value is a writer receipt.  Its ``artifact`` and ``seal``
    members contain the exact JSON objects written to disk; the top-level
    receipt also exposes the recomputed provenance digests for audit callers.
    """

    output = _safe_directory(output_dir, field="formal verdict output directory")
    artifact_path = _safe_output_path(
        formal_verdict_path or output / "formal-verdict.json",
        field="formal verdict artifact path",
        expected_name="formal-verdict.json",
    )
    seal_path = _safe_output_path(
        formal_verdict_seal_path or output / "formal-verdict-seal.json",
        field="formal verdict seal path",
        expected_name="formal-verdict-seal.json",
    )
    if artifact_path.parent != output or seal_path.parent != output:
        raise FormalVerdictWriterError(
            "formal verdict artifact and seal must be in output_dir"
        )
    # Fail before reading T1 so a second invocation cannot accidentally
    # re-adjudicate or attempt replacement after the write-once boundary.
    if os.path.lexists(artifact_path) or os.path.lexists(seal_path):
        raise FormalVerdictWriterError(
            "formal verdict artifact and seal are write-once and already exist"
        )

    context = _evaluate_request(
        prepare_path, t1_prereg_path, source_path, source_seal_path
    )
    artifact = dict(context["artifact"])
    artifact_file_sha256 = _write_once_json(artifact_path, artifact)

    seal: dict[str, Any] = {
        "schema": contract.FORMAL_VERDICT_SEAL_SCHEMA,
        "verdict_sha256": artifact["verdict_sha256"],
        "verdict_file_sha256": artifact_file_sha256,
        "verdict_path": str(artifact_path),
        "source_path": artifact["source_path"],
        "source_file_sha256": artifact["source_file_sha256"],
        "source_seal_path": artifact["source_seal_path"],
        "source_seal_file_sha256": artifact["source_seal_file_sha256"],
        "prepare_sha256": artifact["prepare_sha256"],
        "write_once": True,
        "attempt": 1,
        "retry": False,
        "replacement": False,
        "training": False,
        "test_split_opened": False,
        "outcome_selection": False,
        "q2_consulted": False,
    }
    # The artifact was already hashed in _evaluate_request.  Populate only
    # the seal here so a future contract amendment cannot accidentally make
    # the just-written artifact digest stale after it has been sealed.
    _add_supported_provenance(
        {},
        seal,
        t1_prereg_file_sha256=context["prepare"]["t1_prereg_file_sha256"],
        verifier_code_authority_sha256=context["verifier_code_authority_sha256"],
    )
    seal_fields = _contract_exact_fields("_SEAL_FIELDS")
    if set(seal) != seal_fields:
        raise FormalVerdictWriterError(
            "writer cannot emit the current exact formal-verdict seal schema"
        )
    seal_file_sha256 = _write_once_json(seal_path, seal)

    # Read-back through the current shared contract.  This catches any drift
    # between the writer and the exact artifact/seal shape before returning a
    # receipt.  It does not accept or inspect a caller disposition.
    try:
        authenticated = contract.verify_authenticated_formal_verdict(
            artifact_path,
            seal_path,
            expected_source_path=artifact["source_path"],
            expected_source_seal_path=artifact["source_seal_path"],
        )
    except Exception as error:
        raise FormalVerdictWriterError(
            "written formal verdict failed current learner-contract authentication"
        ) from error
    if authenticated.get("disposition") != artifact["disposition"]:
        raise FormalVerdictWriterError(
            "contract read-back disposition differs from frozen verify_source"
        )

    verification = context["verification"]
    receipt: dict[str, Any] = {
        "schema": WRITER_RECEIPT_SCHEMA,
        "status": "WRITTEN",
        "disposition": artifact["disposition"],
        "artifact": artifact,
        "seal": seal,
        "formal_verdict_path": str(artifact_path),
        "formal_verdict_file_sha256": artifact_file_sha256,
        "formal_verdict_seal_path": str(seal_path),
        "formal_verdict_seal_file_sha256": seal_file_sha256,
        "source_path": context["source"]["source_path"],
        "source_file_sha256": context["source"]["source_file_sha256"],
        "source_payload_sha256": context["source"]["source_payload_sha256"],
        "source_seal_path": context["source"]["source_seal_path"],
        "source_seal_file_sha256": context["source"]["source_seal_file_sha256"],
        "source_seal_payload_sha256": context["source"]["source_seal_payload_sha256"],
        "prepare_path": context["prepare"]["prepare_path"],
        "prepare_file_sha256": context["prepare"]["prepare_file_sha256"],
        "prepare_payload_sha256": context["prepare"]["prepare_payload_sha256"],
        "prepare_seal_path": context["prepare"]["prepare_seal_path"],
        "prepare_seal_file_sha256": context["prepare"]["prepare_seal_file_sha256"],
        "t1_prereg_path": context["prepare"]["t1_prereg_path"],
        "t1_prereg_file_sha256": context["prepare"]["t1_prereg_file_sha256"],
        "verifier_runner_path": context["runner_path"],
        "verifier_runner_file_sha256": context["runner_file_sha256"],
        "verifier_code_authority_sha256": context["verifier_code_authority_sha256"],
        "schema_gap": list(context["schema_gap"]),
        "counts": artifact["counts"],
        "gates": artifact["gates"],
        "write_once": True,
        "attempt": 1,
        "retry": False,
        "replacement": False,
        "contract_receipt": authenticated,
    }
    # This is deliberately a returned receipt, not an additional authority
    # artifact.  The only files written by this function are the exact
    # formal-verdict JSON and its exact file seal.
    if verification.get("disposition") != receipt["disposition"]:
        raise FormalVerdictWriterError(
            "writer receipt disposition is not the frozen verify_source result"
        )
    return receipt


# Discoverable aliases for launchers and focused tests.
write_v06_c2_k1_t1_formal_verdict = write_formal_verdict
build_v06_c2_k1_t1_formal_verdict = build_formal_verdict


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", type=Path, required=True)
    parser.add_argument("--t1-prereg", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-seal", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        receipt = write_formal_verdict(
            args.prepare,
            args.t1_prereg,
            args.source,
            args.output_dir,
            source_seal_path=args.source_seal,
        )
    except (FormalVerdictWriterError, OSError, ValueError, TypeError, ImportError) as error:
        print(f"FAIL_CLOSED: {error}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "disposition": receipt["disposition"],
                "formal_verdict_path": receipt["formal_verdict_path"],
                "formal_verdict_seal_path": receipt["formal_verdict_seal_path"],
                "schema_gap": receipt["schema_gap"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI smoke is covered by callers
    raise SystemExit(_main())


__all__ = [
    "FormalVerdictWriterError",
    "RUNNER_PATH",
    "WRITER_RECEIPT_SCHEMA",
    "build_formal_verdict",
    "build_v06_c2_k1_t1_formal_verdict",
    "write_formal_verdict",
    "write_v06_c2_k1_t1_formal_verdict",
]
