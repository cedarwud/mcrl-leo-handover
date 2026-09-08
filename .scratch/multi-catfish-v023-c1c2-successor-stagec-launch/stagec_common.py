#!/usr/bin/env python3
"""Shared fail-closed primitives for the formal successor Stage-B/C bundle."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import stat
import subprocess
import tempfile
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PHYSICAL = REPO / ".scratch/multi-catfish-v023-c1c2-successor-physical-evaluation"
BASELINE = REPO / ".scratch/multi-catfish-v023-baseline-adapter"
SOURCE_RUNNER = REPO / ".scratch/multi-catfish-v023-two-route-source-training-runner"
CONTRACT = REPO / ".scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-DEVELOPMENT-CONTRACT-2026-09-07.md"
DECLARATION = REPO / ".scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-SCIENTIFIC-DECLARATION-2026-09-07.md"
SCHEDULING_ADDENDUM = REPO / ".scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-STAGEC-SCHEDULING-ADDENDUM-2026-09-07.md"
PREREG = REPO / "artifacts/PREREG-FROZEN-2026-08-25-R2.json"
TLE_ROOT = Path("/home/sat/mcrl-runtime/tle-frozen-20260820")
BASELINE_CHECKPOINT = REPO / "artifacts/training-2026-08-25-rerun01/main/final-checkpoint.pt"
BASELINE_STATUS = BASELINE_CHECKPOINT.with_name("status.json")
BASELINE_CHECKPOINT_SHA256 = "e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b"
PLAN_SHA256 = "866d28e05b04a361041f829e424a2417f49987239b7771ee94f43022d35e01bb"
FIELD_COMPONENT = "MCRL_V020_REPRICED_C3_GATE_V1"
ARMS = ("FULL2", "DROP_C1", "DROP_C2", "BASELINE")
LEARNED_ARMS = ARMS[:3]
PAUSES = (100, 500, 1500, 3000)
CHUNK_BARRIERS = (*PAUSES, 6000, 9000)
BINDINGS_NAME = "V023-C1C2-SUCCESSOR-STAGEC-EXECUTION-BINDINGS.json"
CODE_MANIFEST_NAME = "V023-C1C2-SUCCESSOR-STAGEC-CODE-MANIFEST.sha256"
CODE_PIN_NAME = "V023-C1C2-SUCCESSOR-STAGEC-CODE-MANIFEST-FROZEN.sha256"
SCHEMA_BINDINGS = "multi-catfish-mcrl-v023-c1c2-successor-stagec-execution-bindings-v1"
FORMAL_CLAIM = "TRAIN_DEVELOPMENT_C1C2_SUCCESSOR_PHYSICAL_EVALUATION_NO_C3_NO_TEST_NO_EFFICACY"
FORMAL_ADMISSION_NAME = "FORMAL-ADMISSION.json"
STAGE_AB_SUPPLEMENT_NAME = "STAGE-AB-ADMISSION-SUPPLEMENT.json"
ACCEPTANCE_BUNDLE_NAME = "STAGEC-CHUNK-ACCEPTANCE-BUNDLE.json"
ACCEPTANCE_PROCEDURE = HERE / "ACCEPTANCE-SERVER-EQUIVALENCE.md"
SCHEMA_STAGE_AB_SUPPLEMENT = "multi-catfish-mcrl-v023-c1c2-successor-stage-ab-admission-supplement-v1"
SCHEMA_ACCEPTANCE_BUNDLE = "multi-catfish-mcrl-v023-c1c2-successor-stagec-chunk-acceptance-bundle-v1"
TREE_MANIFEST_NAME = "MANIFEST.sha256"
COMPLETE_NAME = "COMPLETE"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
NUMERICAL_THREAD_ENV = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
)
CHUNK_EQUIVALENCE_PROVENANCE_ONLY_FIELDS = (
    "schema",
    "status",
    "chunk_id",
    "range",
    "start_boundary",
    "end_boundary",
    "start_boundary_state_sha256",
    "end_boundary_state_sha256",
    "threads",
    "runtime",
    "parent_checkpoint",
    "ordered_episode_records",
    "ordered_episode_record_digest",
    "started_utc",
    "ended_utc",
    "execution_mode",
)
CHUNK_EQUIVALENCE_ARTIFACTS = (
    "receipts",
    "checkpoints",
    "rungs",
    "resume_states",
)


class StageCError(RuntimeError):
    """A formal Stage-B/C authentication boundary failed."""


def digest(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        raise StageCError(f"{field} must be a lowercase SHA-256")
    return value


def regular_file(path: str | Path, *, field: str) -> Path:
    candidate = Path(path)
    try:
        info = candidate.lstat()
    except OSError as error:
        raise StageCError(f"{field} is missing: {candidate}") from error
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise StageCError(f"{field} is not a regular non-symlink file: {candidate}")
    return candidate


def file_sha256(path: str | Path, *, field: str = "file") -> str:
    source = regular_file(path, field=field)
    result = hashlib.sha256()
    with source.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def _jsonable(value: object) -> object:
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise StageCError("canonical mappings require string keys")
        return {key: _jsonable(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(child) for child in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise StageCError(f"value is not canonical JSON: {type(value).__name__}")


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        _jsonable(value), sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False,
    ).encode("ascii")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StageCError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path: str | Path, *, field: str) -> dict[str, Any]:
    source = regular_file(path, field=field)
    try:
        value = json.loads(
            source.read_text(encoding="ascii"), object_pairs_hook=_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(StageCError(f"nonfinite JSON: {token}")),
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise StageCError(f"{field} is not strict ASCII JSON") from error
    if not isinstance(value, dict):
        raise StageCError(f"{field} must be a JSON object")
    return value


def write_once(path: str | Path, payload: object, *, newline: bool = True) -> None:
    target = Path(path)
    if target.exists() or target.is_symlink():
        raise StageCError(f"refusing to overwrite: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_bytes(payload) + (b"\n" if newline else b"")
    descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, target)
        except FileExistsError as error:
            raise StageCError(f"concurrent publication: {target}") from error
    finally:
        Path(temporary).unlink(missing_ok=True)


def write_digest_sidecar(path: str | Path) -> Path:
    source = regular_file(path, field="sidecar source")
    sidecar = source.with_name(source.name + ".sha256")
    if sidecar.exists() or sidecar.is_symlink():
        raise StageCError(f"refusing to overwrite sidecar: {sidecar}")
    raw = f"{file_sha256(source)}  {source.name}\n".encode("ascii")
    descriptor = -1
    try:
        descriptor = os.open(sidecar, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as error:
        raise StageCError(f"refusing to overwrite sidecar: {sidecar}") from error
    finally:
        if descriptor != -1:
            os.close(descriptor)
    return sidecar


def verify_named_sidecar(path: str | Path) -> str:
    source = regular_file(path, field="sidecar source")
    sidecar = regular_file(source.with_name(source.name + ".sha256"), field="digest sidecar")
    fields = sidecar.read_text(encoding="ascii").strip().split()
    if len(fields) != 2 or fields[1] != source.name:
        raise StageCError(f"malformed digest sidecar: {sidecar}")
    expected = digest(fields[0], field=f"{source.name} sidecar digest")
    if file_sha256(source) != expected:
        raise StageCError(f"digest sidecar mismatch: {source}")
    return expected


def parse_sha256_manifest(path: str | Path, *, root: Path) -> dict[str, str]:
    manifest = regular_file(path, field="SHA-256 manifest")
    entries: dict[str, str] = {}
    for line in manifest.read_text(encoding="ascii").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\x00]+)", line)
        if match is None:
            raise StageCError(f"malformed manifest line: {line!r}")
        declared, relative_raw = match.groups()
        relative = Path(relative_raw)
        if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != relative_raw:
            raise StageCError(f"unsafe manifest path: {relative_raw}")
        if relative_raw in entries:
            raise StageCError(f"duplicate manifest entry: {relative_raw}")
        target = root / relative
        if file_sha256(target, field=f"manifest member {relative_raw}") != declared:
            raise StageCError(f"manifest member drifted: {relative_raw}")
        entries[relative_raw] = declared
    if not entries:
        raise StageCError("SHA-256 manifest is empty")
    return entries


def verify_code_manifest(repo: Path = REPO) -> tuple[str, dict[str, str]]:
    manifest = HERE / CODE_MANIFEST_NAME
    pin = HERE / CODE_PIN_NAME
    manifest_sha = file_sha256(manifest, field="Stage-C code manifest")
    fields = regular_file(pin, field="Stage-C code-manifest pin").read_text(encoding="ascii").strip().split()
    if fields != [manifest_sha, CODE_MANIFEST_NAME]:
        raise StageCError("Stage-C code manifest disagrees with its external pin")
    return manifest_sha, parse_sha256_manifest(manifest, root=repo)


def assert_no_placeholders(value: object) -> None:
    text = canonical_bytes(value).decode("ascii")
    if "<<" in text or ">>" in text or "BIND_AT_FREEZE" in text or "PLACEHOLDER" in text:
        raise StageCError("unresolved placeholder in execution bindings")


def tree_manifest(root: Path) -> tuple[list[dict[str, object]], str]:
    if root.is_symlink() or not root.is_dir():
        raise StageCError(f"TLE root is missing or symlinked: {root}")
    rows = []
    for path in sorted(root.iterdir()):
        if path.is_symlink() or not path.is_file():
            raise StageCError(f"frozen TLE root contains a non-regular member: {path.name}")
        rows.append({"path": path.name, "sha256": file_sha256(path, field="frozen TLE member")})
    if not rows:
        raise StageCError("frozen TLE root contains no regular files")
    return rows, canonical_sha256(rows)


def process_environment(*, expected_threads: int = 2) -> dict[str, object]:
    expected = {
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(REPO / "src"),
        "TMPDIR": str(REPO / ".tmp"),
        **{name: str(expected_threads) for name in NUMERICAL_THREAD_ENV},
    }
    for key, value in expected.items():
        if os.environ.get(key) != value:
            raise StageCError(f"deterministic process environment drifted: {key}")
    try:
        oom_score_adj = int(Path("/proc/self/oom_score_adj").read_text(encoding="ascii").strip())
    except (OSError, UnicodeError, ValueError) as error:
        raise StageCError("cannot authenticate oom_score_adj") from error
    if oom_score_adj != 1000:
        raise StageCError("oom_score_adj must equal 1000")
    limits = {}
    for name in ("RLIMIT_AS", "RLIMIT_CPU", "RLIMIT_NOFILE", "RLIMIT_NPROC"):
        identifier = getattr(resource, name)
        soft, hard = resource.getrlimit(identifier)
        limits[name] = ["infinity" if value == resource.RLIM_INFINITY else value for value in (soft, hard)]
    return {
        **expected,
        "oom_score_adj": oom_score_adj,
        "resource_limits": limits,
        "rng_policy": "numpy.SeedSequence(world_seed).spawn(2); fresh environment per arm; fixed-policy inference",
    }


def git_identity(repo: Path = REPO) -> dict[str, str]:
    def command(revision: str) -> str:
        try:
            result = subprocess.run(
                ["git", "-C", str(repo), "rev-parse", revision],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except (OSError, subprocess.CalledProcessError) as error:
            raise StageCError("cannot authenticate runtime git commit/tree") from error
        return result.stdout.strip()

    return {"commit": command("HEAD"), "tree": command("HEAD^{tree}")}


def verify_runtime_identity(
    bindings: Mapping[str, object], *, chunk_mode: bool = False
) -> None:
    if bindings.get("git") != git_identity(REPO):
        raise StageCError("runtime checkout commit/tree differs from frozen binding")
    execution = bindings.get("execution")
    observed = process_environment(expected_threads=1) if chunk_mode else process_environment()
    expected = dict(execution) if isinstance(execution, Mapping) else {}
    if chunk_mode:
        expected.update({name: "1" for name in NUMERICAL_THREAD_ENV})
    if not isinstance(execution, Mapping) or expected != observed:
        raise StageCError("runtime process/resource configuration differs from frozen binding")


def learned_training_provenance(bindings: Mapping[str, object]) -> dict[str, dict[str, object]]:
    stage_a = bindings.get("stage_a")
    if not isinstance(stage_a, Mapping):
        raise StageCError("Stage-A binding is missing")
    exports = stage_a.get("exports")
    manifest_sha = digest(stage_a.get("manifest_sha256"), field="Stage-A manifest digest")
    if not isinstance(exports, list) or len(exports) != len(LEARNED_ARMS):
        raise StageCError("Stage-A export coverage drifted")
    sources = {
        "FULL2": ["informed", "informed"],
        "DROP_C1": ["neutral", "informed"],
        "DROP_C2": ["informed", "neutral"],
    }
    result: dict[str, dict[str, object]] = {}
    for arm, entry in zip(LEARNED_ARMS, exports, strict=True):
        if not isinstance(entry, Mapping) or entry.get("arm") != arm:
            raise StageCError(f"Stage-A export order drifted: {arm}")
        result[arm] = {
            "arm": arm,
            "checkpoint_sha256": digest(entry.get("sha256"), field=f"{arm} export digest"),
            "source_mapping": sources[arm],
            "stage_a_status": "PASS_SOURCE_TRAINING_INTEGRITY",
            "manifest_sha256": manifest_sha,
        }
    return result


def stage_c_admission_mapping(
    bindings: Mapping[str, object], policy_bindings: Mapping[str, object]
) -> dict[str, dict[str, object]]:
    stage_a = bindings.get("stage_a")
    baseline = bindings.get("baseline")
    if not isinstance(stage_a, Mapping) or not isinstance(baseline, Mapping):
        raise StageCError("policy admission inputs are malformed")
    exports = stage_a.get("exports")
    if not isinstance(exports, list) or len(exports) != len(LEARNED_ARMS):
        raise StageCError("policy admission export coverage drifted")
    mapping: dict[str, dict[str, object]] = {}
    for arm, export in zip(LEARNED_ARMS, exports, strict=True):
        if not isinstance(export, Mapping) or export.get("arm") != arm:
            raise StageCError(f"policy admission export order drifted: {arm}")
        mapping[arm] = {
            "stage_a_export": {
                "path": str((Path(str(stage_a["root"])) / str(export["path"])).resolve()),
                "sha256": digest(export.get("sha256"), field=f"{arm} export digest"),
            },
            "policy_binding": policy_bindings[arm],
        }
    mapping["BASELINE"] = {
        "adapter_binding": {
            "checkpoint_path": str(Path(str(baseline["checkpoint_path"])).resolve()),
            "checkpoint_sha256": digest(
                baseline.get("checkpoint_sha256"), field="BASELINE checkpoint digest"
            ),
            "authentication_path": str(Path(str(baseline["status_path"])).resolve()),
            "authentication_sha256": digest(
                baseline.get("status_sha256"), field="BASELINE authentication digest"
            ),
            "adapter_closure_sha256": digest(
                baseline.get("adapter_closure_sha256"), field="BASELINE adapter closure digest"
            ),
            "routes": [],
        },
        "policy_binding": policy_bindings["BASELINE"],
    }
    return mapping


def verify_stage_c_admission_mapping(mapping: object) -> dict[str, dict[str, object]]:
    if not isinstance(mapping, Mapping) or set(mapping) != set(ARMS):
        raise StageCError("Stage-C admission mapping arm order/coverage drifted")
    result = {arm: dict(mapping[arm]) for arm in ARMS if isinstance(mapping[arm], Mapping)}
    if tuple(result) != ARMS:
        raise StageCError("Stage-C admission mapping record is malformed")
    for arm in LEARNED_ARMS:
        export = result[arm].get("stage_a_export")
        if not isinstance(export, Mapping):
            raise StageCError(f"{arm} Stage-A export admission is missing")
        path = regular_file(str(export.get("path")), field=f"{arm} admitted export")
        expected = digest(export.get("sha256"), field=f"{arm} admitted export digest")
        if file_sha256(path) != expected:
            raise StageCError(f"{arm} admitted export bytes drifted")
        binding = result[arm].get("policy_binding")
        if not isinstance(binding, Mapping) or binding.get("checkpoint_sha256") != expected:
            raise StageCError(f"{arm} policy binding differs from admitted export")
    baseline = result["BASELINE"].get("adapter_binding")
    policy = result["BASELINE"].get("policy_binding")
    if not isinstance(baseline, Mapping) or not isinstance(policy, Mapping):
        raise StageCError("BASELINE adapter admission is missing")
    for path_field, sha_field in (
        ("checkpoint_path", "checkpoint_sha256"),
        ("authentication_path", "authentication_sha256"),
    ):
        expected = digest(baseline.get(sha_field), field=f"BASELINE {sha_field}")
        if file_sha256(str(baseline.get(path_field)), field=f"BASELINE {path_field}") != expected:
            raise StageCError(f"BASELINE admitted {path_field} bytes drifted")
    if baseline.get("routes") != [] or policy.get("routes") != []:
        raise StageCError("BASELINE admission acquired successor routes")
    if (
        policy.get("checkpoint_sha256") != baseline.get("checkpoint_sha256")
        or policy.get("authentication_sha256") != baseline.get("authentication_sha256")
    ):
        raise StageCError("BASELINE policy differs from adapter admission")
    return result


def verified_stage_c_admission_mapping(
    bindings: Mapping[str, object], policy_bindings: Mapping[str, object]
) -> dict[str, dict[str, object]]:
    """Build and authenticate the exact four-arm Stage-C policy mapping."""
    return verify_stage_c_admission_mapping(
        stage_c_admission_mapping(bindings, policy_bindings)
    )


def publish_sealed_json(path: Path, payload: Mapping[str, object], *, field: str) -> str:
    if path.exists() or path.is_symlink():
        if read_json(path, field=field) != dict(payload):
            raise StageCError(f"{field} drifted on resume")
        return verify_named_sidecar(path)
    write_once(path, payload)
    write_digest_sidecar(path)
    return file_sha256(path, field=field)


def _verify_stage_a_record(stage_a: object) -> dict[str, object]:
    if not isinstance(stage_a, Mapping):
        raise StageCError("Stage-A supplement binding is missing")
    root = Path(str(stage_a.get("root", "")))
    manifest_sha = digest(stage_a.get("manifest_sha256"), field="Stage-A manifest digest")
    if file_sha256(root / "MANIFEST.sha256", field="Stage-A manifest") != manifest_sha:
        raise StageCError("Stage-A supplement manifest drifted")
    pass_receipt = stage_a.get("pass_receipt")
    if not isinstance(pass_receipt, Mapping):
        raise StageCError("Stage-A supplement PASS receipt is missing")
    pass_path = root / str(pass_receipt.get("path", ""))
    if file_sha256(pass_path, field="Stage-A PASS receipt") != pass_receipt.get("sha256"):
        raise StageCError("Stage-A supplement PASS receipt drifted")
    receipt = read_json(pass_path, field="Stage-A PASS receipt")
    decision = receipt.get("epoch_100_integrity")
    if not isinstance(decision, Mapping) or decision.get("decision") != "PASS_SOURCE_TRAINING_INTEGRITY":
        raise StageCError("Stage-A supplement does not authenticate PASS")
    exports = stage_a.get("exports")
    if not isinstance(exports, list) or [entry.get("arm") for entry in exports if isinstance(entry, Mapping)] != list(LEARNED_ARMS):
        raise StageCError("Stage-A supplement export coverage drifted")
    for arm, entry in zip(LEARNED_ARMS, exports, strict=True):
        if not isinstance(entry, Mapping):
            raise StageCError(f"{arm} Stage-A export binding is malformed")
        path = root / str(entry.get("path", ""))
        if file_sha256(path, field=f"{arm} Stage-A export") != entry.get("sha256"):
            raise StageCError(f"{arm} Stage-A supplement export drifted")
    return dict(stage_a)


def verify_acceptance_bundle(path: str | Path, bindings: Mapping[str, object]) -> dict[str, Any]:
    payload = read_json(path, field="Stage-C chunk acceptance bundle")
    bundle_sha = verify_named_sidecar(path)
    procedure_sha = file_sha256(ACCEPTANCE_PROCEDURE, field="acceptance procedure")
    receipts = payload.get("receipts")
    if (
        payload.get("schema") != SCHEMA_ACCEPTANCE_BUNDLE
        or payload.get("status") != "PASS_ALL_FOUR_ARM_CHUNK_EQUIVALENCE"
        or payload.get("formal") is not True
        or payload.get("arms") != list(ARMS)
        or payload.get("bindings_sha256") != bindings.get("bindings_sha256")
        or payload.get("code_manifest_sha256") != bindings.get("code", {}).get("external_manifest_sha256")
        or payload.get("acceptance_procedure_sha256") != procedure_sha
        or not isinstance(receipts, list)
        or len(receipts) != len(ARMS)
    ):
        raise StageCError("Stage-C acceptance bundle identity drifted")
    for arm, record in zip(ARMS, receipts, strict=True):
        if not isinstance(record, Mapping) or record.get("arm") != arm:
            raise StageCError("Stage-C acceptance arm order drifted")
        receipt_path = regular_file(str(record.get("path")), field=f"{arm} acceptance receipt")
        expected = digest(record.get("sha256"), field=f"{arm} acceptance receipt digest")
        if file_sha256(receipt_path) != expected or verify_named_sidecar(receipt_path) != expected:
            raise StageCError(f"{arm} acceptance receipt bytes drifted")
        receipt = read_json(receipt_path, field=f"{arm} acceptance receipt")
        if (
            receipt.get("status") != "PASS_BITWISE_CHUNK_EQUIVALENCE"
            or receipt.get("formal") is not True
            or receipt.get("arm") != arm
            or receipt.get("episodes") != 200
            or receipt.get("chunks") != [[1, 100], [101, 200]]
            or receipt.get("rehearsal_chunk") is not None
            or receipt.get("bindings_sha256") != payload.get("bindings_sha256")
            or receipt.get("code_manifest_sha256") != payload.get("code_manifest_sha256")
            or receipt.get("acceptance_procedure_sha256") != procedure_sha
            or receipt.get("receipt_comparison_excluded_provenance_fields")
            != list(CHUNK_EQUIVALENCE_PROVENANCE_ONLY_FIELDS)
            or receipt.get("merged_artifacts_compared")
            != list(CHUNK_EQUIVALENCE_ARTIFACTS)
        ):
            raise StageCError(f"{arm} acceptance receipt did not authenticate equivalence")
    return {**payload, "acceptance_bundle_path": str(Path(path).resolve()), "acceptance_bundle_sha256": bundle_sha}


def verify_stage_ab_supplement(
    path: str | Path, bindings_path: str | Path, bindings: Mapping[str, object] | None = None
) -> dict[str, Any]:
    base = verify_bindings(bindings_path) if bindings is None else dict(bindings)
    base_sha = file_sha256(bindings_path, field="prospective execution bindings")
    payload = read_json(path, field="Stage-A/B admission supplement")
    supplement_sha = verify_named_sidecar(path)
    stage_a = _verify_stage_a_record(payload.get("stage_a"))
    stage_b = payload.get("stage_b_pass_receipt")
    if (
        payload.get("schema") != SCHEMA_STAGE_AB_SUPPLEMENT
        or payload.get("status") != "PASS_STAGE_AB_IMPORTED_FOR_STAGE_C"
        or payload.get("formal") is not True
        or payload.get("bindings_sha256") != base_sha
        or not isinstance(stage_b, Mapping)
    ):
        raise StageCError("Stage-A/B supplement identity drifted")
    stage_b_path = regular_file(str(stage_b.get("path")), field="Stage-B PASS gate")
    if file_sha256(stage_b_path) != stage_b.get("sha256") or verify_named_sidecar(stage_b_path) != stage_b.get("sha256"):
        raise StageCError("Stage-B PASS gate bytes drifted")
    stage_b_payload = read_json(stage_b_path, field="Stage-B PASS gate")
    if stage_b_payload.get("status") != "PASS_PLUMBING_INTEGRITY" or stage_b_payload.get("formal") is not True:
        raise StageCError("Stage-B supplement does not authenticate PASS")
    return {
        **payload,
        "stage_a": stage_a,
        "supplement_path": str(Path(path).resolve()),
        "supplement_sha256": supplement_sha,
    }


def materialize_stage_ab(bindings: Mapping[str, object], supplement: Mapping[str, object]) -> dict[str, Any]:
    result = dict(bindings)
    result["stage_a"] = dict(supplement["stage_a"])
    result["stage_ab_supplement"] = {
        "path": supplement["supplement_path"],
        "sha256": supplement["supplement_sha256"],
    }
    return result


def ensure_runtime_admission(
    *,
    bindings: Mapping[str, object],
    path: Path,
    runner_schema: str,
    admitted_evaluation_sha256: str,
    predecessor_pass_receipts: Sequence[Mapping[str, object]],
    sampler_sha256: str,
) -> dict[str, object]:
    physical = bindings.get("physical_inputs")
    execution = bindings.get("execution")
    if not isinstance(physical, Mapping) or not isinstance(execution, Mapping):
        raise StageCError("runtime admission inputs are malformed")
    prereg_path = regular_file(str(physical.get("prereg_path")), field="PREREG")
    prereg_sha = digest(physical.get("prereg_sha256"), field="PREREG digest")
    if file_sha256(prereg_path) != prereg_sha:
        raise StageCError("PREREG bytes drifted before runtime admission")
    prereg = read_json(prereg_path, field="PREREG")
    sections = prereg.get("sections")
    ephemeris = sections.get("ephemeris") if isinstance(sections, Mapping) else None
    if not isinstance(ephemeris, Mapping):
        raise StageCError("PREREG lacks frozen ephemeris declaration")
    admission_dir = path.parent
    admission_dir.mkdir(parents=True, exist_ok=True)
    if admission_dir.is_symlink():
        raise StageCError("runtime admission directory is symlinked")
    stem = path.stem
    tle_snapshot = admission_dir / f"{stem}-tle-manifest.json"
    execution_snapshot = admission_dir / f"{stem}-execution-configuration.json"
    tle_snapshot_sha = publish_sealed_json(
        tle_snapshot, dict(ephemeris), field="frozen TLE manifest snapshot"
    )
    execution_snapshot_sha = publish_sealed_json(
        execution_snapshot, dict(execution), field="execution configuration snapshot"
    )
    predecessors: list[dict[str, object]] = []
    for index, record in enumerate(predecessor_pass_receipts):
        if not isinstance(record, Mapping):
            raise StageCError(f"predecessor PASS binding {index} is malformed")
        receipt_path = regular_file(str(record.get("path")), field=f"predecessor PASS {index}")
        receipt_sha = digest(record.get("sha256"), field=f"predecessor PASS {index} digest")
        if file_sha256(receipt_path) != receipt_sha:
            raise StageCError(f"predecessor PASS {index} bytes drifted")
        predecessors.append(
            {"path": str(receipt_path.resolve()), "sha256": receipt_sha, "status": record.get("status")}
        )
    payload: dict[str, object] = {
        "schema": f"{runner_schema}-runtime-admission-v1",
        "status": "FORMAL_RUNTIME_ADMITTED",
        "split": "TRAIN",
        "admitted_evaluation_sha256": digest(
            admitted_evaluation_sha256, field="admitted evaluation digest"
        ),
        "tle_root": str(Path(str(physical.get("tle_root"))).resolve()),
        "physical_configuration": {
            "users": 100,
            "steps": 10,
            "split": "TRAIN",
            "field_component": FIELD_COMPONENT,
            "tle_root": str(Path(str(physical.get("tle_root"))).resolve()),
        },
        "prereg": {"path": str(prereg_path.resolve()), "sha256": prereg_sha},
        "tle_manifest": {
            "path": str(tle_snapshot.resolve()),
            "sha256": tle_snapshot_sha,
            "file_set_sha256": digest(
                ephemeris.get("file_set_sha256"), field="frozen TLE file-set digest"
            ),
        },
        "execution_configuration": {
            "path": str(execution_snapshot.resolve()),
            "sha256": execution_snapshot_sha,
        },
        "predecessor_pass_receipts": predecessors,
        "sampler": {
            "part": "train",
            "as_dict_sha256": digest(sampler_sha256, field="TRAIN sampler digest"),
        },
        "learned_training_provenance": learned_training_provenance(bindings),
    }
    admission_sha = publish_sealed_json(path, payload, field="runtime admission")
    return {
        **payload,
        "admission_path": str(path.resolve()),
        "admission_sha256": admission_sha,
        "authenticated_predecessor_statuses": [str(record["status"]) for record in predecessors],
    }


def write_tree_seal(root: Path) -> str:
    if root.is_symlink() or not root.is_dir():
        raise StageCError("cannot seal a missing or symlinked result root")
    if (root / TREE_MANIFEST_NAME).exists() or (root / COMPLETE_NAME).exists():
        raise StageCError("result root is already sealed")
    files: dict[str, str] = {}
    for path in root.rglob("*"):
        if path.is_symlink():
            raise StageCError(f"result root contains a symlink: {path}")
        if path.is_file():
            files[path.relative_to(root).as_posix()] = file_sha256(path)
    manifest = "".join(f"{sha}  {name}\n" for name, sha in sorted(files.items()))
    manifest_path = root / TREE_MANIFEST_NAME
    descriptor = -1
    try:
        descriptor = os.open(manifest_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(manifest.encode("ascii"))
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if descriptor != -1:
            os.close(descriptor)
    manifest_sha = file_sha256(manifest_path)
    complete_path = root / COMPLETE_NAME
    descriptor = -1
    try:
        descriptor = os.open(complete_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(f"{manifest_sha}  {TREE_MANIFEST_NAME}\n".encode("ascii"))
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if descriptor != -1:
            os.close(descriptor)
    return manifest_sha


def verify_tree_seal(root: Path) -> str:
    manifest = regular_file(root / TREE_MANIFEST_NAME, field="result tree manifest")
    complete = regular_file(root / COMPLETE_NAME, field="result tree COMPLETE")
    manifest_sha = file_sha256(manifest)
    if complete.read_text(encoding="ascii") != f"{manifest_sha}  {TREE_MANIFEST_NAME}\n":
        raise StageCError("result COMPLETE does not authenticate tree manifest")
    entries = parse_sha256_manifest(manifest, root=root)
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and not path.is_symlink()
        and path.relative_to(root).as_posix() not in {TREE_MANIFEST_NAME, COMPLETE_NAME}
    }
    if set(entries) != actual:
        raise StageCError("result tree manifest closure drifted")
    return manifest_sha


def require_formal(value: Mapping[str, object], *, field: str) -> None:
    if value.get("formal") is False:
        raise StageCError(f"{field} is explicitly non-formal")


def verify_bindings(path: str | Path) -> dict[str, Any]:
    value = read_json(path, field="execution bindings")
    verify_named_sidecar(path)
    if value.get("schema") != SCHEMA_BINDINGS or value.get("formal") is not True:
        raise StageCError("execution bindings are not formal Stage C bindings")
    assert_no_placeholders(value)
    if value.get("arms") != list(ARMS):
        raise StageCError("execution bindings arm order drifted")
    if value.get("world_plan", {}).get("plan_sha256") != PLAN_SHA256:
        raise StageCError("execution bindings plan digest drifted")
    schedule = value.get("scheduling_addendum")
    if (
        not isinstance(schedule, Mapping)
        or schedule.get("path") != str(SCHEDULING_ADDENDUM.resolve())
        or file_sha256(SCHEDULING_ADDENDUM, field="scheduling addendum") != schedule.get("sha256")
        or verify_named_sidecar(SCHEDULING_ADDENDUM) != schedule.get("sha256")
    ):
        raise StageCError("execution bindings scheduling addendum drifted")
    procedure = value.get("acceptance_procedure")
    if (
        not isinstance(procedure, Mapping)
        or procedure.get("path") != str(ACCEPTANCE_PROCEDURE.resolve())
        or file_sha256(ACCEPTANCE_PROCEDURE, field="acceptance procedure") != procedure.get("sha256")
    ):
        raise StageCError("execution bindings acceptance procedure drifted")
    code_sha, _entries = verify_code_manifest()
    if value.get("code", {}).get("external_manifest_sha256") != code_sha:
        raise StageCError("execution bindings code closure drifted")
    physical = value.get("physical_inputs")
    if not isinstance(physical, Mapping):
        raise StageCError("execution bindings physical inputs are missing")
    if file_sha256(str(physical.get("prereg_path")), field="PREREG") != physical.get("prereg_sha256"):
        raise StageCError("execution bindings PREREG bytes drifted")
    tle_rows, tle_sha = tree_manifest(Path(str(physical.get("tle_root"))))
    if tle_rows != physical.get("tle_manifest") or tle_sha != physical.get("tle_manifest_sha256"):
        raise StageCError("execution bindings TLE closure drifted")
    plan = value.get("world_plan")
    if (
        not isinstance(plan, Mapping)
        or file_sha256(str(plan.get("path")), field="world plan") != plan.get("file_sha256")
    ):
        raise StageCError("execution bindings world-plan bytes drifted")
    return value


def forbid_policy_tokens(value: object, *, field: str) -> None:
    """Reject prohibited topology/split tokens with two declared exceptions.

    The frozen keyed-field namespace contains the historical substring C3 and
    the producer receipts carry boolean q3_evaluated=false audit fields.  They
    are authenticated exceptions, not routes, arms, models, or split openings.
    """
    def walk(child: object, key: str = "") -> None:
        if isinstance(child, Mapping):
            for nested_key, nested in child.items():
                if str(nested_key).lower() == "q3_evaluated" and nested is False:
                    continue
                walk(nested, str(nested_key))
            return
        if isinstance(child, (list, tuple)):
            for nested in child:
                walk(nested, key)
            return
        if not isinstance(child, str) or child == FIELD_COMPONENT:
            return
        tokens = [token.upper() for token in re.split(r"[^A-Za-z0-9]+", child) if token]
        normalized = child.upper()
        if (
            any(token in {"R7", "C3", "Q3", "TEST"} for token in tokens)
            or "ALL_NEUTRAL_CONTROL" in normalized
            or "DROP_C3" in normalized
        ):
            if "NO_C3" in normalized and "NO_TEST" in normalized:
                return
            raise StageCError(f"forbidden token in {field}: {child}")
        if normalized == "FULL":
            raise StageCError(f"FULL is forbidden as a trained arm in {field}")
    walk(value)
