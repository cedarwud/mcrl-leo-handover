#!/usr/bin/env python3
"""Independent structural verifier for V0.23 staged receipts.

The verifier does not import the runner, simulator, TLE loader, learner, or
formula implementation.  It checks canonical JSON, receipt seals, frozen
identity panels, shard coverage, and the closed TEST/episode-training
boundary.  Physical formula identities, common-field reuse, C3View leakage,
and held-out learner predicates remain explicit TODO inputs for the future
server adapter; this scaffold never labels those checks as scientific PASS.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CONTRACT_SHA256 = "1e69a2e7242198adce97e6357e4205a29fe6d1fb06a48dc7e1839a675529811a"
WORLDS = tuple(range(2026121705, 2026121713))
STUDENT_SEEDS = (2026135101, 2026135102, 2026135103)
ARMS = ("INFORMED", "MATCHED_PLACEBO")
SCHEMA = "multi-catfish-mcrl-v023-lcsrs-observability-gate-v1"
PLAN_SCHEMA = f"{SCHEMA}-plan"
SOURCE_SCHEMA = f"{SCHEMA}-source-shard"
SOURCE_MANIFEST_SCHEMA = f"{SCHEMA}-source-manifest"
FIT_SCHEMA = f"{SCHEMA}-fit-shard"
MERGE_SCHEMA = f"{SCHEMA}-merge-receipt"
RESULT_SCHEMA = f"{SCHEMA}-result"
CLAIM_CEILING = (
    "TRAIN_DEVELOPMENT_SOURCE_AND_LEARNER_GATE_NO_TEST_NO_EPISODE_TRAINING_NO_EFFICACY"
)


class V023VerificationError(RuntimeError):
    """A persisted V0.23 receipt failed independent structural verification."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V023VerificationError(f"expected regular receipt file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load(path: Path) -> dict[str, Any]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V023VerificationError(f"receipt is missing or non-regular: {source}")
    raw = source.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V023VerificationError(f"receipt is not ASCII JSON: {source}") from error
    if not isinstance(payload, dict):
        raise V023VerificationError("receipt root is not an object")
    canonical = _canonical_bytes(payload)
    if raw not in (canonical, canonical + b"\n"):
        raise V023VerificationError(f"receipt is not canonical JSON: {source}")
    return payload


def _mapping(value: object, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise V023VerificationError(f"{field} is not an object")
    return value


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V023VerificationError(f"{field} is not a lowercase SHA-256")
    return value


def _exact_int(value: object, *, field: str) -> int:
    if type(value) is not int:
        raise V023VerificationError(f"{field} must be an exact integer")
    return value


def _verify_seal(payload: Mapping[str, Any], *, field: str = "receipt_sha256") -> None:
    declared = _digest(payload.get(field), field=field)
    unsigned = {key: value for key, value in payload.items() if key != field}
    if canonical_sha256(unsigned) != declared:
        raise V023VerificationError(f"{field} disagrees with canonical receipt bytes")


def _expected_source_shards() -> list[dict[str, Any]]:
    return [
        {"world": world, "relative_name": f"source/world-{world}.json"}
        for world in WORLDS
    ]


def _expected_fit_shards() -> list[dict[str, Any]]:
    return [
        {
            "held_out_world": world,
            "student_seed": seed,
            "arm": arm,
            "relative_name": (
                f"fit/world-{world}/seed-{seed}/{arm.lower()}.json"
            ),
        }
        for world in WORLDS
        for seed in STUDENT_SEEDS
        for arm in ARMS
    ]


def _common(payload: Mapping[str, Any], *, schema: str) -> None:
    if payload.get("schema") != schema:
        raise V023VerificationError(f"schema is not {schema}")
    if payload.get("claim_ceiling") != CLAIM_CEILING:
        raise V023VerificationError("receipt claim ceiling disagrees with frozen boundary")
    if payload.get("contract_sha256") != CONTRACT_SHA256:
        raise V023VerificationError("contract hash disagrees with the frozen V0.23 contract")
    if payload.get("split") != "TRAIN_DEVELOPMENT":
        raise V023VerificationError("receipt is not TRAIN_DEVELOPMENT")
    if payload.get("test_split_opened") is not False:
        raise V023VerificationError("receipt opened TEST")
    if payload.get("episode_training") is not False:
        raise V023VerificationError("receipt performed episode training")


def verify_plan_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("schema") != PLAN_SCHEMA:
        raise V023VerificationError("plan schema drifted")
    if payload.get("contract_sha256") != CONTRACT_SHA256:
        raise V023VerificationError("plan contract hash drifted")
    if payload.get("claim_ceiling") != CLAIM_CEILING:
        raise V023VerificationError("plan claim ceiling drifted")
    if payload.get("worlds") != list(WORLDS):
        raise V023VerificationError("plan world panel drifted")
    if payload.get("student_seeds") != list(STUDENT_SEEDS):
        raise V023VerificationError("plan student seed panel drifted")
    if payload.get("arms") != list(ARMS):
        raise V023VerificationError("plan arm panel drifted")
    if payload.get("draw_count") != 32 or payload.get("steps_per_episode") != 10:
        raise V023VerificationError("plan draw count or step count drifted")
    if payload.get("fold_count") != 8 or payload.get("fit_updates") != 2000:
        raise V023VerificationError("plan fold/update configuration drifted")
    if payload.get("source_count") != 8 or payload.get("fit_count") != 48:
        raise V023VerificationError("plan shard counts drifted")
    if payload.get("source_manifest") != "source-manifest.json":
        raise V023VerificationError("plan source-manifest stage drifted")
    if payload.get("source_shards") != _expected_source_shards():
        raise V023VerificationError("plan source-shard schedule drifted")
    if payload.get("fit_shards") != _expected_fit_shards():
        raise V023VerificationError("plan fit-shard schedule drifted")
    if payload.get("test_split_opened") is not False or payload.get("episode_training") is not False:
        raise V023VerificationError("plan opens a forbidden execution surface")
    _verify_seal(payload, field="plan_sha256")
    return {
        "status": "PASS_STRUCTURAL_PLAN",
        "scientific_claim": False,
        "source_count": payload["source_count"],
        "fit_count": payload["fit_count"],
    }


def verify_source_payload(
    payload: Mapping[str, Any], *, world: int, preflight_sha256: str
) -> dict[str, Any]:
    _common(payload, schema=SOURCE_SCHEMA)
    if _exact_int(payload.get("world"), field="world") != world or world not in WORLDS:
        raise V023VerificationError("source shard world is outside frozen panel")
    if payload.get("preflight_manifest_sha256") != preflight_sha256:
        raise V023VerificationError("source shard preflight hash drifted")
    if payload.get("status") != "PASS":
        raise V023VerificationError("source shard is not complete PASS")
    if payload.get("learner_update") is not False:
        raise V023VerificationError("source shard performed a learner update")
    for field in (
        "enumeration_sha256",
        "topology_sha256",
        "teacher_sha256",
        "surface_sha256",
    ):
        _digest(payload.get(field), field=field)
    for field in ("record_count", "pair_count", "supported_count", "placebo_eligible_count"):
        if _exact_int(payload.get(field), field=field) < 0:
            raise V023VerificationError(f"{field} is negative")
    _verify_seal(payload)
    return {
        "status": "PASS_STRUCTURAL_SOURCE",
        "scientific_claim": False,
        "world": world,
        "pair_count": payload["pair_count"],
    }


def verify_source_manifest_payload(
    payload: Mapping[str, Any], *, preflight_sha256: str
) -> dict[str, Any]:
    """Verify the fit-input manifest emitted after all source shards."""

    _common(payload, schema=SOURCE_MANIFEST_SCHEMA)
    if payload.get("status") != "PASS":
        raise V023VerificationError("source manifest is not complete PASS")
    if payload.get("learner_update") is not False:
        raise V023VerificationError("source manifest performed a learner update")
    if payload.get("claim_ceiling") != CLAIM_CEILING:
        raise V023VerificationError("source manifest claim ceiling drifted")
    if payload.get("preflight_manifest_sha256") != preflight_sha256:
        raise V023VerificationError("source manifest preflight hash drifted")
    if payload.get("worlds") != list(WORLDS):
        raise V023VerificationError("source manifest world panel drifted")
    if payload.get("source_count") != len(WORLDS):
        raise V023VerificationError("source manifest count drifted")
    if payload.get("shards") != _expected_source_shards():
        raise V023VerificationError("source manifest schedule drifted")
    entries = payload.get("entries")
    if not isinstance(entries, list) or len(entries) != len(WORLDS):
        raise V023VerificationError("source manifest entries are incomplete")
    for item, expected in zip(entries, _expected_source_shards(), strict=True):
        if not isinstance(item, Mapping):
            raise V023VerificationError("source manifest entry is not an object")
        if item.get("world") != expected["world"]:
            raise V023VerificationError("source manifest entry world drifted")
        if item.get("relative_name") != expected["relative_name"]:
            raise V023VerificationError("source manifest entry path drifted")
        _digest(item.get("sha256"), field="source manifest entry sha256")
    source_hash = _digest(
        payload.get("source_manifest_sha256"), field="source_manifest_sha256"
    )
    unsigned = dict(payload)
    unsigned.pop("source_manifest_sha256", None)
    unsigned.pop("manifest_sha256", None)
    if canonical_sha256(unsigned) != source_hash:
        raise V023VerificationError("source manifest hash disagrees with body")
    _verify_seal(payload, field="manifest_sha256")
    return {
        "status": "PASS_STRUCTURAL_SOURCE_MANIFEST",
        "scientific_claim": False,
        "source_count": len(WORLDS),
        "source_manifest_sha256": source_hash,
    }


def verify_fit_payload(
    payload: Mapping[str, Any],
    *,
    held_out_world: int,
    student_seed: int,
    arm: str,
    preflight_sha256: str,
    source_manifest_sha256: str,
) -> dict[str, Any]:
    _common(payload, schema=FIT_SCHEMA)
    if _exact_int(payload.get("held_out_world"), field="held_out_world") != held_out_world or held_out_world not in WORLDS:
        raise V023VerificationError("fit held-out world drifted")
    if _exact_int(payload.get("student_seed"), field="student_seed") != student_seed or student_seed not in STUDENT_SEEDS:
        raise V023VerificationError("fit student seed drifted")
    if payload.get("arm") != arm or arm not in ARMS:
        raise V023VerificationError("fit arm drifted")
    if payload.get("preflight_manifest_sha256") != preflight_sha256:
        raise V023VerificationError("fit preflight hash drifted")
    if payload.get("source_manifest_sha256") != source_manifest_sha256:
        raise V023VerificationError("fit source manifest hash drifted")
    if payload.get("status") != "PASS":
        raise V023VerificationError("fit shard is not complete PASS")
    if payload.get("learner_update") is not True:
        raise V023VerificationError("fit shard did not attest its learner update")
    if payload.get("update_count") != 2000:
        raise V023VerificationError("fit update count drifted")
    for field in ("model_sha256", "metrics_sha256"):
        _digest(payload.get(field), field=field)
    _verify_seal(payload)
    return {
        "status": "PASS_STRUCTURAL_FIT",
        "scientific_claim": False,
        "held_out_world": held_out_world,
        "student_seed": student_seed,
        "arm": arm,
    }


def _safe_child(root: Path, relative: str, *, field: str) -> Path:
    candidate = (Path(root).resolve() / relative).resolve()
    if not candidate.is_relative_to(Path(root).resolve()):
        raise V023VerificationError(f"{field} escapes shard root")
    return candidate


def verify_merge_payload(
    payload: Mapping[str, Any],
    *,
    source_root: Path | None = None,
    fit_root: Path | None = None,
) -> dict[str, Any]:
    _common(payload, schema=MERGE_SCHEMA)
    if payload.get("status") != "READY_FOR_INDEPENDENT_DECISION":
        raise V023VerificationError("merge receipt is not the scaffold-ready status")
    if payload.get("decision") is not None:
        raise V023VerificationError("scaffold merge may not open a scientific decision")
    if payload.get("worlds") != list(WORLDS) or payload.get("student_seeds") != list(STUDENT_SEEDS):
        raise V023VerificationError("merge identity panel drifted")
    if payload.get("arms") != list(ARMS):
        raise V023VerificationError("merge arm panel drifted")
    if payload.get("source_count") != 8 or payload.get("fit_count") != 48:
        raise V023VerificationError("merge shard counts are incomplete")
    source_entries = payload.get("source_shards")
    if not isinstance(source_entries, list) or len(source_entries) != len(WORLDS):
        raise V023VerificationError("merge source shard list is incomplete")
    for actual, expected in zip(source_entries, _expected_source_shards(), strict=True):
        if not isinstance(actual, Mapping):
            raise V023VerificationError("merge source shard entry is not an object")
        if actual.get("world") != expected["world"]:
            raise V023VerificationError("merge source shard identity drifted")
        if actual.get("path") != expected["relative_name"]:
            raise V023VerificationError("merge source shard path drifted")
        _digest(actual.get("sha256"), field="merge source shard sha256")
    fit_entries = payload.get("fit_shards")
    if not isinstance(fit_entries, list) or len(fit_entries) != len(_expected_fit_shards()):
        raise V023VerificationError("merge fit shard list is incomplete")
    for actual, expected in zip(fit_entries, _expected_fit_shards(), strict=True):
        if not isinstance(actual, Mapping):
            raise V023VerificationError("merge fit shard entry is not an object")
        for field in ("held_out_world", "student_seed", "arm"):
            if actual.get(field) != expected[field]:
                raise V023VerificationError("merge fit shard identity drifted")
        if actual.get("path") != expected["relative_name"]:
            raise V023VerificationError("merge fit shard path drifted")
        _digest(actual.get("sha256"), field="merge fit shard sha256")
    if payload.get("scientific_decision_opened") is not False:
        raise V023VerificationError("merge opened a scientific decision")
    preflight_sha256 = _digest(
        payload.get("preflight_manifest_sha256"), field="preflight_manifest_sha256"
    )
    merge_source_hash = _digest(
        payload.get("source_manifest_sha256"), field="source_manifest_sha256"
    )
    source_manifest = _mapping(payload.get("source_manifest"), field="source_manifest")
    verify_source_manifest_payload(
        source_manifest,
        preflight_sha256=preflight_sha256,
    )
    if merge_source_hash != source_manifest.get("source_manifest_sha256"):
        raise V023VerificationError("merge source manifest hash drifted")
    if source_manifest.get("shards") != _expected_source_shards():
        raise V023VerificationError("merge source manifest schedule drifted")
    if not isinstance(source_manifest.get("entries"), list):
        raise V023VerificationError("merge source manifest has no entries")
    manifest_entries = source_manifest["entries"]
    if len(manifest_entries) != len(WORLDS):
        raise V023VerificationError("merge source manifest entries are incomplete")
    for actual, expected in zip(manifest_entries, _expected_source_shards(), strict=True):
        if not isinstance(actual, Mapping):
            raise V023VerificationError("merge source manifest entry is not an object")
        if actual.get("world") != expected["world"]:
            raise V023VerificationError("merge source manifest world drifted")
        if actual.get("relative_name") != expected["relative_name"]:
            raise V023VerificationError("merge source manifest path drifted")
        _digest(actual.get("sha256"), field="merge source manifest sha256")
    source_hash = _digest(
        source_manifest.get("source_manifest_sha256"),
        field="source_manifest.source_manifest_sha256",
    )
    unsigned_source = dict(source_manifest)
    unsigned_source.pop("source_manifest_sha256", None)
    unsigned_source.pop("manifest_sha256", None)
    if canonical_sha256(unsigned_source) != source_hash:
        raise V023VerificationError("merge source manifest hash disagrees")
    _verify_seal(source_manifest, field="manifest_sha256")
    _verify_seal(payload)
    # Optional root-aware verification reopens every child receipt instead of
    # trusting the merge's copied booleans or lists.  The roots are explicit
    # because source and fit workers may be stored in different directories.
    if (source_root is None) != (fit_root is None):
        raise V023VerificationError("source_root and fit_root must be supplied together")
    if source_root is not None and fit_root is not None:
        for world, item in zip(WORLDS, source_manifest["entries"], strict=True):
            path = _safe_child(source_root, item["relative_name"], field="source child")
            if file_sha256(path) != item["sha256"]:
                raise V023VerificationError(f"source child hash drifted: {path}")
            verify_source_payload(
                _load(path), world=world, preflight_sha256=preflight_sha256
            )
        for expected, actual in zip(_expected_fit_shards(), payload["fit_shards"], strict=True):
            path = _safe_child(fit_root, actual["path"], field="fit child")
            if file_sha256(path) != actual["sha256"]:
                raise V023VerificationError(f"fit child hash drifted: {path}")
            verify_fit_payload(
                _load(path),
                held_out_world=expected["held_out_world"],
                student_seed=expected["student_seed"],
                arm=expected["arm"],
                preflight_sha256=preflight_sha256,
                source_manifest_sha256=payload["source_manifest_sha256"],
            )
    return {
        "status": "PASS_STRUCTURAL_MERGE",
        "scientific_claim": False,
        "decision": None,
        "source_count": 8,
        "fit_count": 48,
    }


def verify_result_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Verify a future final result's immutable outer boundary only.

    A complete physical/learner verifier must be added by the server adapter;
    this function intentionally returns a non-scientific status.
    """

    _common(payload, schema=RESULT_SCHEMA)
    if payload.get("claim_ceiling") != CLAIM_CEILING:
        raise V023VerificationError("result claim ceiling drifted")
    if payload.get("worlds") != list(WORLDS) or payload.get("student_seeds") != list(STUDENT_SEEDS):
        raise V023VerificationError("result identity panel drifted")
    if payload.get("arms") != list(ARMS):
        raise V023VerificationError("result arm panel drifted")
    _digest(payload.get("preflight_manifest_sha256"), field="preflight_manifest_sha256")
    decision = payload.get("decision")
    allowed = {
        "INSUFFICIENT_PAIRS",
        "STOP_PHYSICS",
        "STOP_OBSERVABILITY",
        "REDESIGN_INTERFACE",
        "GO_FIXED_LEARNER_SCREEN_CONTRACT",
        "INVALID_RUN",
    }
    if decision not in allowed:
        raise V023VerificationError("result decision token is not frozen")
    _verify_seal(payload)
    return {
        "status": "PASS_OUTER_BOUNDARY_ONLY",
        "scientific_claim": False,
        "decision": decision,
        "verification_scope": "schema_provenance_only",
    }


def verify_file(path: Path, *, kind: str = "auto", **kwargs: Any) -> dict[str, Any]:
    payload = _load(path)
    selected = kind
    if selected == "auto":
        selected = {
            PLAN_SCHEMA: "plan",
            SOURCE_SCHEMA: "source",
            SOURCE_MANIFEST_SCHEMA: "source-manifest",
            FIT_SCHEMA: "fit",
            MERGE_SCHEMA: "merge",
            RESULT_SCHEMA: "result",
        }.get(str(payload.get("schema")), "unknown")
    if selected == "plan":
        return verify_plan_payload(payload)
    if selected == "source":
        return verify_source_payload(payload, **kwargs)
    if selected == "source-manifest":
        return verify_source_manifest_payload(payload, **kwargs)
    if selected == "fit":
        return verify_fit_payload(payload, **kwargs)
    if selected == "merge":
        return verify_merge_payload(payload, **kwargs)
    if selected == "result":
        return verify_result_payload(payload)
    raise V023VerificationError(f"unknown receipt kind: {payload.get('schema')!r}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument(
        "--kind",
        choices=("auto", "plan", "source", "source-manifest", "fit", "merge", "result"),
        default="auto",
    )
    parser.add_argument("--source-root", type=Path, default=None)
    parser.add_argument("--fit-root", type=Path, default=None)
    parser.add_argument("--preflight-sha256", default=None)
    args = parser.parse_args(argv)
    kwargs: dict[str, Any] = {}
    if args.kind == "source-manifest":
        if args.preflight_sha256 is None:
            parser.error("--preflight-sha256 is required for source-manifest")
        kwargs["preflight_sha256"] = args.preflight_sha256
    elif args.kind == "merge":
        if (args.source_root is None) != (args.fit_root is None):
            parser.error("--source-root and --fit-root must be supplied together")
        if args.source_root is not None:
            kwargs["source_root"] = args.source_root
            kwargs["fit_root"] = args.fit_root
    report = verify_file(args.receipt, kind=args.kind, **kwargs)
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
