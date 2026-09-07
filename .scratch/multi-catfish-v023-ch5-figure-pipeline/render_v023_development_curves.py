#!/usr/bin/env python3
"""Render authenticated TRAIN-development curves from physical-runner receipts.

This consumer is deliberately read-only with respect to evaluation roots.  The
current producer module supplies the receipt field contract; future variants
may add arms while retaining that contract and their own schema prefix.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, fields
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib  # noqa: E402

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PRODUCER_PATH = (
    REPO
    / ".scratch"
    / "multi-catfish-v023-c1c2-successor-physical-evaluation"
    / "v023_c1c2_successor_physical_runner.py"
)
WATERMARK = "REHEARSAL — NOT A RESULT"
FORBIDDEN_LABEL_WORDS = ("significant", "proves", "efficacy", "TEST")
BOOTSTRAP_REPLICATES = 500
FORMAL_ADMISSION_NAME = "FORMAL-ADMISSION.json"
TREE_MANIFEST_NAME = "MANIFEST.sha256"
COMPLETE_NAME = "COMPLETE"


class FigurePipelineError(RuntimeError):
    """An input authentication or rendering boundary failed."""


def _load_producer() -> Any:
    if not PRODUCER_PATH.is_file():
        raise FigurePipelineError(f"physical receipt producer is missing: {PRODUCER_PATH}")
    producer_dir = str(PRODUCER_PATH.parent)
    if producer_dir not in sys.path:
        sys.path.insert(0, producer_dir)
    try:
        return importlib.import_module(PRODUCER_PATH.stem)
    except ImportError as error:
        raise FigurePipelineError("cannot naturally import the physical receipt producer") from error


PRODUCER = _load_producer()
ARM_ORDER = tuple(PRODUCER.ARMS)
FORMAL_ADMISSION_SCHEMA = f"{PRODUCER.SCHEMA}-formal-admission-v1"
PLAN_BUILDER = importlib.import_module("build_v023_c1c2_successor_world_plan")
FROZEN_PLAN_SHA256 = PLAN_BUILDER.build_world_plan()["plan_sha256"]
RECEIPT_FIELDS = frozenset(field.name for field in fields(PRODUCER.EpisodeReceipt))


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as error:
        raise FigurePipelineError("input is not finite canonical JSON") from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise FigurePipelineError(f"expected a regular input file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise FigurePipelineError(f"JSON input is missing or symlinked: {path}")
    try:
        payload = json.loads(path.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise FigurePipelineError(f"invalid ASCII JSON: {path}") from error
    if not isinstance(payload, dict):
        raise FigurePipelineError(f"JSON root must be an object: {path}")
    return payload


def _sidecar_candidates(path: Path) -> tuple[Path, ...]:
    return (path.with_name(path.name + ".sha256"), path.with_suffix(".sha256"))


def _authenticate_sidecars(path: Path, actual: str) -> list[tuple[str, str]]:
    authenticated: list[tuple[str, str]] = []
    seen: set[Path] = set()
    for sidecar in _sidecar_candidates(path):
        if sidecar in seen or not sidecar.exists():
            continue
        seen.add(sidecar)
        if sidecar.is_symlink() or not sidecar.is_file():
            raise FigurePipelineError(f"digest sidecar is not a regular file: {sidecar}")
        words = sidecar.read_text(encoding="ascii").strip().split()
        if not words or len(words[0]) != 64 or words[0] != actual:
            raise FigurePipelineError(f"digest sidecar disagrees with input: {sidecar}")
        authenticated.append((sidecar.name, file_sha256(sidecar)))
    return authenticated


def _verify_external_manifest(root: Path) -> tuple[tuple[str, str], ...]:
    manifest = root / TREE_MANIFEST_NAME
    complete = root / COMPLETE_NAME
    if manifest.is_symlink() or not manifest.is_file() or complete.is_symlink() or not complete.is_file():
        raise FigurePipelineError("formal root lacks external manifest/COMPLETE seal")
    manifest_sha = file_sha256(manifest)
    if any(path.is_symlink() for path in root.rglob("*")):
        raise FigurePipelineError("formal root contains a symlink")
    if complete.read_bytes() != f"{manifest_sha}  {TREE_MANIFEST_NAME}\n".encode("ascii"):
        raise FigurePipelineError("formal root COMPLETE does not authenticate manifest")
    expected: dict[str, str] = {}
    try:
        lines = manifest.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeError) as error:
        raise FigurePipelineError("formal root manifest is unreadable") from error
    for line in lines:
        parts = line.split("  ", 1)
        if (
            len(parts) != 2
            or parts[1] in expected
            or _sha256_token(parts[0], "manifest entry") != parts[0]
            or Path(parts[1]).is_absolute()
            or ".." in Path(parts[1]).parts
        ):
            raise FigurePipelineError("formal root manifest is malformed")
        expected[parts[1]] = parts[0]
    actual = {
        path.relative_to(root).as_posix(): file_sha256(path)
        for path in root.rglob("*")
        if path.is_file()
        and not path.is_symlink()
        and path.relative_to(root).as_posix() not in {TREE_MANIFEST_NAME, COMPLETE_NAME}
    }
    if expected != dict(sorted(actual.items())):
        raise FigurePipelineError("formal root whole-tree manifest closure drifted")
    return tuple(sorted((path, digest) for path, digest in actual.items()))


def _read_formal_admission(root: Path) -> dict[str, Any] | None:
    path = root / FORMAL_ADMISSION_NAME
    if not path.exists():
        return None
    payload = _read_json(path)
    digest = file_sha256(path)
    if not _authenticate_sidecars(path, digest):
        raise FigurePipelineError("formal admission lacks its digest sidecar")
    required_digests = (
        "prereg_sha256",
        "tle_manifest_sha256",
        "execution_configuration_sha256",
        "stage_a_pass_receipt_sha256",
        "stage_b_pass_receipt_sha256",
        "policy_bindings_sha256",
    )
    if (
        payload.get("schema") != FORMAL_ADMISSION_SCHEMA
        or payload.get("status") != "FORMAL_STAGE_C_ADMITTED"
        or payload.get("formal") is not True
        or payload.get("integrity_status") != "VERIFIED"
        or payload.get("split") != PRODUCER.SPLIT
        or payload.get("arms") != list(PRODUCER.ARMS)
        or payload.get("plan_sha256") != FROZEN_PLAN_SHA256
        or any(_sha256_token(payload.get(field), field) != payload.get(field) for field in required_digests)
    ):
        raise FigurePipelineError("formal admission identity/bindings drifted")
    return payload


def _finite_number(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise FigurePipelineError(f"{label} is not numeric")
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise FigurePipelineError(f"{label} is not numeric") from error
    if not math.isfinite(result):
        raise FigurePipelineError(f"{label} is not finite")
    return result


def _sha256_token(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise FigurePipelineError(f"{label} is not a lowercase SHA-256")
    return value


def _validate_receipts(
    rows: object,
    *,
    completed: int,
    arms: tuple[str, ...],
    receipt_schema: str,
    expected_plan_sha256: str,
    expected_policy_bindings: Mapping[str, object],
) -> list[dict[str, Any]]:
    if not isinstance(rows, list) or len(rows) != completed * len(arms):
        raise FigurePipelineError("checkpoint receipt coverage is incomplete")
    result: list[dict[str, Any]] = []
    plan_sha: str | None = None
    claim: str | None = None
    for offset, raw in enumerate(rows):
        if not isinstance(raw, dict) or not RECEIPT_FIELDS.issubset(raw):
            raise FigurePipelineError("episode receipt does not satisfy producer field contract")
        row = dict(raw)
        episode = offset // len(arms) + 1
        arm = arms[offset % len(arms)]
        if row["episode_index"] != episode or row["arm"] != arm:
            raise FigurePipelineError("episode receipts are not complete ordered matched worlds")
        if (
            row["schema"] != receipt_schema
            or row["split"] != PRODUCER.SPLIT
            or row["status"] != PRODUCER.STATUS
        ):
            raise FigurePipelineError("episode receipt identity drifted")
        if row["users"] != PRODUCER.USERS or row["steps"] != PRODUCER.STEPS:
            raise FigurePipelineError("episode receipt dimensions drifted")
        expected_world = PRODUCER.WorldBinding(
            episode_index=episode,
            world_id=row["world_id"],
            world_seed=row["world_seed"],
            field_root_digest=row["field_root_digest"],
        )
        try:
            expected_world.verify()
        except PRODUCER.C1C2PhysicalError as error:
            raise FigurePipelineError("episode receipt differs from frozen world plan") from error
        bits = _finite_number(row["total_bits"], "total_bits")
        energy = _finite_number(row["total_energy_j"], "total_energy_j")
        ee = _finite_number(row["ratio_of_sums_ee_bits_per_j"], "ratio_of_sums_ee_bits_per_j")
        served = row["served_user_steps"]
        opportunities = row["service_opportunities"]
        if bits < 0 or energy <= 0 or type(served) is not int or type(opportunities) is not int:
            raise FigurePipelineError("episode additive endpoint is malformed")
        if opportunities != PRODUCER.USERS * PRODUCER.STEPS or served < 0 or served > opportunities:
            raise FigurePipelineError("episode service counts are malformed")
        if not math.isclose(ee, bits / energy, rel_tol=0.0, abs_tol=1e-12):
            raise FigurePipelineError("episode EE disagrees with additive sums")
        if not math.isclose(
            _finite_number(row["service_fraction"], "service_fraction"),
            served / opportunities,
            rel_tol=0.0,
            abs_tol=1e-15,
        ):
            raise FigurePipelineError("episode service fraction disagrees with counts")
        for boundary in ("q3_evaluated", "test_split_opened", "episode_training", "learner_update"):
            if row[boundary] is not False:
                raise FigurePipelineError("episode receipt crossed a prohibited boundary")
        binding = row["policy_binding"]
        if (
            not isinstance(binding, dict)
            or binding.get("arm") != arm
            or binding.get("routes") != row["routes"]
            or binding != expected_policy_bindings.get(arm)
        ):
            raise FigurePipelineError("episode policy binding disagrees with receipt")
        expected_routes = [] if arm == "BASELINE" else list(PRODUCER.ROUTES)
        if row["routes"] != expected_routes:
            raise FigurePipelineError("episode routes disagree with schema-specific arm")
        for digest_field in (
            "initial_world_sha256",
            "field_root_digest",
            "action_trace_sha256",
            "plan_sha256",
        ):
            _sha256_token(row[digest_field], digest_field)
        if row["plan_sha256"] != expected_plan_sha256:
            raise FigurePipelineError("episode receipt plan disagrees with checkpoint")
        if row["claim_ceiling"] != PRODUCER.CLAIM_CEILING:
            raise FigurePipelineError("episode claim ceiling differs from producer schema")
        if plan_sha is None:
            plan_sha = str(row["plan_sha256"])
            claim = str(row["claim_ceiling"])
        elif row["plan_sha256"] != plan_sha or row["claim_ceiling"] != claim:
            raise FigurePipelineError("episode receipt plan or claim ceiling drifted")
        result.append(row)
    for episode in range(completed):
        matched = result[episode * len(arms) : (episode + 1) * len(arms)]
        for key in ("world_id", "world_seed", "initial_world_sha256", "field_root_digest"):
            if len({row[key] for row in matched}) != 1:
                raise FigurePipelineError(f"matched-world receipt mismatch: {key}")
    return result


def _pool(rows: Sequence[Mapping[str, Any]], arm: str) -> dict[str, object]:
    selected = [row for row in rows if row["arm"] == arm]
    bits = math.fsum(float(row["total_bits"]) for row in selected)
    energy = math.fsum(float(row["total_energy_j"]) for row in selected)
    served = sum(int(row["served_user_steps"]) for row in selected)
    opportunities = sum(int(row["service_opportunities"]) for row in selected)
    return {
        "arm": arm,
        "routes": list(selected[0]["routes"]),
        "episodes": len(selected),
        "total_bits": bits,
        "total_energy_j": energy,
        "ratio_of_sums_ee_bits_per_j": bits / energy,
        "served_user_steps": served,
        "service_opportunities": opportunities,
        "service_fraction": served / opportunities,
        "episode_training": False,
        "learner_update": False,
    }


def _compare_pooled(expected: Mapping[str, Any], actual: Mapping[str, Any]) -> None:
    if set(expected) != set(actual):
        raise FigurePipelineError("rung pooled arm coverage disagrees with checkpoint")
    for arm in expected:
        if canonical_sha256(expected[arm]) != canonical_sha256(actual[arm]):
            raise FigurePipelineError(f"rung receipt disagrees with checkpoint receipts for {arm}")


def _validate_terminal_result(
    result: Mapping[str, Any], *, rung: "Rung", plan_sha256: str, continuation: bool
) -> None:
    boundary = 9000 if continuation else 3000
    pooled = result.get("pooled_by_arm")
    if not isinstance(pooled, dict):
        raise FigurePipelineError("terminal result lacks pooled endpoints")
    _compare_pooled(rung.pooled, pooled)
    if (
        result.get("schema")
        != (PRODUCER.CONTINUATION_RESULT_SCHEMA if continuation else PRODUCER.RESULT_SCHEMA)
        or result.get("status") != PRODUCER.STATUS
        or result.get("split") != PRODUCER.SPLIT
        or result.get("completed_episode") != boundary
        or result.get("terminal_boundary") != boundary
        or result.get("plan_sha256") != plan_sha256
        or result.get("arms") != list(PRODUCER.ARMS)
        or result.get("claim_ceiling") != PRODUCER.CLAIM_CEILING
        or any(result.get(field) is not False for field in (
            "q3_evaluated", "test_split_opened", "episode_training", "learner_update"
        ))
    ):
        raise FigurePipelineError("terminal result identity/disposition semantics drifted")
    authority = result.get("continuation_authority_sha256")
    if continuation:
        _sha256_token(authority, "continuation_authority_sha256")
        if (
            result.get("authorized_from_3000_token") != PRODUCER.HELD
            or result.get("scientific_disposition_emitted") is not False
            or "overall_token" in result
            or "reasons" in result
        ):
            raise FigurePipelineError("continuation result emitted a second scientific disposition")
    elif authority is not None:
        raise FigurePipelineError("3000 result unexpectedly carries continuation authority")
    else:
        disposition = PRODUCER.adjudicate_physical_disposition(
            rung.pooled,
            completed_episodes=3000,
            expected_episodes=3000,
        )
        if (
            result.get("overall_token") != disposition["overall_token"]
            or result.get("reasons") != disposition["reasons"]
            or result.get("scientific_disposition_emitted") is not True
        ):
            raise FigurePipelineError("3000 result disposition semantics drifted")


@dataclass(frozen=True)
class Rung:
    completed: int
    pooled: Mapping[str, Mapping[str, Any]]
    receipts: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True)
class RootData:
    root: Path
    root_sha256: str
    arms: tuple[str, ...]
    claim_ceiling: str
    formal: bool
    rungs: tuple[Rung, ...]
    authenticated_files: tuple[tuple[str, str], ...]

    @property
    def receipt_count(self) -> int:
        return len(self.rungs[-1].receipts)


def _root_formality(
    root: Path,
    tracked: list[tuple[str, str]],
    admission: Mapping[str, object] | None,
) -> bool:
    flags: list[bool] = []
    for path in sorted(root.glob("*.json")):
        payload = _read_json(path)
        digest = file_sha256(path)
        tracked.append((path.name, digest))
        tracked.extend((f"{path.name}/{name}", value) for name, value in _authenticate_sidecars(path, digest))
        if "formal" in payload:
            if type(payload["formal"]) is not bool:
                raise FigurePipelineError(f"formal flag is not Boolean: {path}")
            flags.append(payload["formal"])
    if len(set(flags)) > 1:
        raise FigurePipelineError("root contains inconsistent formal flags")
    named_nonformal = any(token in root.name.upper() for token in ("REHEARSAL", "NONFORMAL"))
    if flags and flags[0] is True and admission is None:
        raise FigurePipelineError("formal flag cannot replace authenticated formal admission")
    return admission is not None and (flags[0] if flags else True) and not named_nonformal


def load_root(root: str | Path, *, allow_nonformal: bool = False) -> RootData:
    source = Path(root).resolve()
    if source.is_symlink() or not source.is_dir():
        raise FigurePipelineError(f"input root is not a regular directory: {source}")
    tracked: list[tuple[str, str]] = []
    if any(source.glob("*integrity-stop.json")):
        raise FigurePipelineError("integrity STOP root cannot be rendered")
    admission = _read_formal_admission(source)
    formal = _root_formality(source, tracked, admission)
    if not formal and not allow_nonformal:
        raise FigurePipelineError("nonformal/rehearsal root requires --allow-nonformal")
    if formal:
        tracked.extend(_verify_external_manifest(source))
        tracked.extend(
            (
                (TREE_MANIFEST_NAME, file_sha256(source / TREE_MANIFEST_NAME)),
                (COMPLETE_NAME, file_sha256(source / COMPLETE_NAME)),
            )
        )
    checkpoint_paths = sorted((source / "checkpoints").glob("checkpoint-*.json"))
    rung_paths = sorted((source / "rungs").glob("rung-*.json"))
    if not checkpoint_paths or len(checkpoint_paths) != len(rung_paths):
        raise FigurePipelineError("root must contain matching checkpoint and rung histories")
    all_rungs: list[Rung] = []
    arms: tuple[str, ...] | None = None
    claim_ceiling: str | None = None
    schema_prefix: str | None = None
    plan_sha256: str | None = None
    previous_rows: list[dict[str, Any]] = []
    for ordinal, (checkpoint_path, rung_path) in enumerate(zip(checkpoint_paths, rung_paths), start=1):
        completed = ordinal * int(PRODUCER.CHECKPOINT_EVERY)
        expected_checkpoint_name = f"checkpoint-{completed:06d}.json"
        expected_rung_name = f"rung-{completed:06d}.json"
        if checkpoint_path.name != expected_checkpoint_name or rung_path.name != expected_rung_name:
            raise FigurePipelineError("receipt cadence is not contiguous from 100 episodes")
        checkpoint = _read_json(checkpoint_path)
        checkpoint_digest = file_sha256(checkpoint_path)
        tracked.append((str(checkpoint_path.relative_to(source)), checkpoint_digest))
        tracked.extend(
            (f"{checkpoint_path.relative_to(source)}/{name}", value)
            for name, value in _authenticate_sidecars(checkpoint_path, checkpoint_digest)
        )
        claimed = checkpoint.pop("checkpoint_sha256", None)
        if not isinstance(claimed, str) or claimed != canonical_sha256(checkpoint):
            raise FigurePipelineError(f"checkpoint digest disagrees with contents: {checkpoint_path}")
        checkpoint_schema = checkpoint.get("schema")
        if not isinstance(checkpoint_schema, str) or not checkpoint_schema.endswith("-checkpoint"):
            raise FigurePipelineError("checkpoint schema is malformed")
        current_schema_prefix = checkpoint_schema[: -len("-checkpoint")]
        if schema_prefix is None:
            schema_prefix = current_schema_prefix
        elif current_schema_prefix != schema_prefix:
            raise FigurePipelineError("checkpoint schema changes across rungs")
        if checkpoint.get("status") != PRODUCER.STATUS or checkpoint.get("split") != PRODUCER.SPLIT:
            raise FigurePipelineError("checkpoint identity drifted")
        for boundary in ("q3_evaluated", "test_split_opened", "episode_training", "learner_update"):
            if checkpoint.get(boundary) is not False:
                raise FigurePipelineError("checkpoint crossed a prohibited boundary")
        current_plan_sha256 = _sha256_token(checkpoint.get("plan_sha256"), "plan_sha256")
        if current_plan_sha256 != FROZEN_PLAN_SHA256:
            raise FigurePipelineError("checkpoint does not use the frozen world plan")
        if plan_sha256 is None:
            plan_sha256 = current_plan_sha256
        elif current_plan_sha256 != plan_sha256:
            raise FigurePipelineError("plan identity changes across checkpoints")
        raw_arms = checkpoint.get("arms")
        if not isinstance(raw_arms, list) or any(not isinstance(arm, str) for arm in raw_arms):
            raise FigurePipelineError("checkpoint arm list is malformed")
        current_arms = tuple(raw_arms)
        if current_schema_prefix != PRODUCER.SCHEMA or current_arms != ARM_ORDER:
            raise FigurePipelineError("checkpoint schema-specific arm coverage/order drifted")
        if arms is None:
            arms = current_arms
        elif current_arms != arms:
            raise FigurePipelineError("arm list changes across checkpoints")
        if checkpoint.get("completed_episode") != completed or checkpoint.get("checkpoint_every") != PRODUCER.CHECKPOINT_EVERY:
            raise FigurePipelineError("checkpoint cadence fields drifted")
        policy_bindings = checkpoint.get("policy_bindings")
        if not isinstance(policy_bindings, dict) or set(policy_bindings) != set(arms):
            raise FigurePipelineError("checkpoint policy binding coverage drifted")
        if admission is not None and canonical_sha256(policy_bindings) != admission["policy_bindings_sha256"]:
            raise FigurePipelineError("checkpoint policy bindings disagree with formal admission")
        rows = _validate_receipts(
            checkpoint.get("receipts"),
            completed=completed,
            arms=arms,
            receipt_schema=f"{schema_prefix}-episode-receipt",
            expected_plan_sha256=plan_sha256,
            expected_policy_bindings=policy_bindings,
        )
        if previous_rows and rows[: len(previous_rows)] != previous_rows:
            raise FigurePipelineError("checkpoint receipt history was rewritten")
        previous_rows = rows
        current_claim = str(rows[0]["claim_ceiling"])
        if checkpoint.get("claim_ceiling") != current_claim:
            raise FigurePipelineError("checkpoint claim ceiling disagrees with episode receipts")
        if claim_ceiling is None:
            claim_ceiling = current_claim
        elif current_claim != claim_ceiling:
            raise FigurePipelineError("claim ceiling changes across checkpoints")
        rung = _read_json(rung_path)
        rung_digest = file_sha256(rung_path)
        tracked.append((str(rung_path.relative_to(source)), rung_digest))
        tracked.extend(
            (f"{rung_path.relative_to(source)}/{name}", value)
            for name, value in _authenticate_sidecars(rung_path, rung_digest)
        )
        if (
            rung.get("schema") != f"{schema_prefix}-rung-receipt"
            or rung.get("status") != PRODUCER.STATUS
            or rung.get("split") != PRODUCER.SPLIT
            or rung.get("plan_sha256") != plan_sha256
            or rung.get("completed_episode") != completed
            or tuple(rung.get("arms", ())) != arms
        ):
            raise FigurePipelineError("rung identity or arm order disagrees with checkpoint")
        if rung.get("claim_ceiling") != claim_ceiling or rung.get("scientific_disposition_emitted") is not False:
            raise FigurePipelineError("rung crossed its development-reporting boundary")
        for boundary in ("q3_evaluated", "test_split_opened", "episode_training", "learner_update"):
            if rung.get(boundary) is not False:
                raise FigurePipelineError("rung crossed a prohibited boundary")
        expected_pooled = {arm: _pool(rows, arm) for arm in arms}
        pooled = rung.get("pooled_by_arm")
        if not isinstance(pooled, dict):
            raise FigurePipelineError("rung pooled endpoints are missing")
        _compare_pooled(expected_pooled, pooled)
        all_rungs.append(Rung(completed, expected_pooled, tuple(rows)))
    for result_name, boundary, continuation in (
        ("result.json", 3000, False),
        ("continuation-result.json", 9000, True),
    ):
        result_path = source / result_name
        if not result_path.exists():
            continue
        result = _read_json(result_path)
        result_digest = file_sha256(result_path)
        if (result_path.name, result_digest) not in tracked:
            tracked.append((result_path.name, result_digest))
            tracked.extend(
                (f"{result_path.name}/{name}", value)
                for name, value in _authenticate_sidecars(result_path, result_digest)
            )
        terminal_rung = next((rung for rung in all_rungs if rung.completed == boundary), None)
        if terminal_rung is None:
            raise FigurePipelineError("terminal result lacks its authenticated rung")
        _validate_terminal_result(
            result,
            rung=terminal_rung,
            plan_sha256=str(plan_sha256),
            continuation=continuation,
        )
    if all_rungs[-1].completed > 3000 and not (source / "result.json").is_file():
        raise FigurePipelineError("post-3000 history lacks the preserved 3000 result")
    tracked_sorted = tuple(sorted(set(tracked)))
    root_digest = canonical_sha256(
        {"files": [{"path": path, "sha256": digest} for path, digest in tracked_sorted]}
    )
    assert arms is not None and claim_ceiling is not None
    return RootData(source, root_digest, arms, claim_ceiling, formal, tuple(all_rungs), tracked_sorted)


COLORS = {
    "FULL2": "#16697A",
    "DROP_C1": "#D1495B",
    "DROP_C2": "#EDAE49",
    "BASELINE": "#4D4D4D",
    "FULL": "#00798C",
    "DROP_C3": "#7A5195",
}


def _style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "legend.fontsize": 8,
            "figure.dpi": 120,
            "savefig.dpi": 160,
            "axes.grid": True,
            "grid.alpha": 0.22,
            "path.simplify": False,
        }
    )


def _decorate(fig: Any, data: RootData, *, title: str) -> None:
    fig.suptitle(f"TRAIN development — {title}", y=0.985)
    footer = (
        "Development-only disclosure; no held-out use or scientific claim"
        f"   |   authenticated root: {data.root_sha256}"
    )
    fig.text(0.5, 0.012, footer, ha="center", va="bottom", fontsize=5.6, color="#555555")
    if not data.formal:
        fig.text(
            0.5,
            0.5,
            WATERMARK,
            ha="center",
            va="center",
            rotation=24,
            fontsize=28,
            color="#A23B3B",
            alpha=0.23,
            weight="bold",
        )


def _axis_labels(fig: Any) -> list[str]:
    labels: list[str] = []
    if fig._suptitle is not None:
        labels.append(fig._suptitle.get_text())
    for axis in fig.axes:
        labels.extend((axis.get_xlabel(), axis.get_ylabel(), axis.get_title()))
        labels.extend(text.get_text() for text in axis.get_legend().get_texts()) if axis.get_legend() else None
    labels.extend(text.get_text() for text in fig.texts)
    return labels


def _assert_safe_labels(fig: Any) -> None:
    for label in _axis_labels(fig):
        if any(word.lower() in label.lower() for word in FORBIDDEN_LABEL_WORDS):
            raise FigurePipelineError(f"forbidden word in semantic figure label: {label!r}")


def _plot_lines(axis: Any, data: RootData, metric: str) -> None:
    x = [rung.completed for rung in data.rungs]
    for arm in data.arms:
        y = [float(rung.pooled[arm][metric]) for rung in data.rungs]
        axis.plot(x, y, marker="o", markersize=3, linewidth=1.6, color=COLORS[arm], label=arm)


def build_ee_figure(data: RootData) -> Any:
    _style()
    fig, axis = plt.subplots(figsize=(8.2, 4.8))
    _plot_lines(axis, data, "ratio_of_sums_ee_bits_per_j")
    axis.set_xlabel("Cumulative episodes")
    axis.set_ylabel("Pooled energy efficiency (bit/J)")
    axis.legend(ncol=min(3, len(data.arms)), frameon=False)
    _decorate(fig, data, title="pooled ratio-of-sums energy efficiency")
    fig.subplots_adjust(left=0.12, right=0.98, top=0.88, bottom=0.17)
    _assert_safe_labels(fig)
    return fig


def build_service_figure(data: RootData) -> Any:
    _style()
    fig, axis = plt.subplots(figsize=(8.2, 4.8))
    x = np.asarray([rung.completed for rung in data.rungs])
    baseline = np.asarray([float(rung.pooled["BASELINE"]["service_fraction"]) for rung in data.rungs])
    axis.fill_between(x, baseline - 0.001, baseline + 0.001, color=COLORS["BASELINE"], alpha=0.13, label="BASELINE ± 0.001")
    _plot_lines(axis, data, "service_fraction")
    axis.set_xlabel("Cumulative episodes")
    axis.set_ylabel("Served fraction")
    all_values = np.asarray(
        [
            float(rung.pooled[arm]["service_fraction"])
            for rung in data.rungs
            for arm in data.arms
        ],
        dtype=np.float64,
    )
    lower = min(float(np.min(all_values)), float(np.min(baseline - PRODUCER.SERVICE_MARGIN)))
    upper = max(float(np.max(all_values)), float(np.max(baseline + PRODUCER.SERVICE_MARGIN)))
    padding = max(0.01, (upper - lower) * 0.05)
    axis.set_ylim(max(0.0, lower - padding), min(1.0, upper + padding))
    axis.legend(ncol=min(3, len(data.arms) + 1), frameon=False)
    _decorate(fig, data, title="served fraction and BASELINE margin band")
    fig.subplots_adjust(left=0.12, right=0.98, top=0.88, bottom=0.17)
    _assert_safe_labels(fig)
    return fig


def _paired_bootstrap(data: RootData, rung: Rung, arm: str) -> tuple[float, float, float]:
    by_arm = {
        name: [row for row in rung.receipts if row["arm"] == name]
        for name in (arm, "BASELINE")
    }
    n = rung.completed
    arrays = {
        name: (
            np.asarray([float(row["total_bits"]) for row in rows], dtype=np.float64),
            np.asarray([float(row["total_energy_j"]) for row in rows], dtype=np.float64),
        )
        for name, rows in by_arm.items()
    }
    center = float(rung.pooled[arm]["ratio_of_sums_ee_bits_per_j"]) - float(
        rung.pooled["BASELINE"]["ratio_of_sums_ee_bits_per_j"]
    )
    seed_material = f"{data.root_sha256}:{rung.completed}:{arm}:paired-bootstrap-v1".encode("ascii")
    seed = int.from_bytes(hashlib.sha256(seed_material).digest()[:8], "big")
    rng = np.random.default_rng(seed)
    estimates = np.empty(BOOTSTRAP_REPLICATES, dtype=np.float64)
    for start in range(0, BOOTSTRAP_REPLICATES, 50):
        stop = min(start + 50, BOOTSTRAP_REPLICATES)
        sample = rng.integers(0, n, size=(stop - start, n))
        arm_ee = arrays[arm][0][sample].sum(axis=1) / arrays[arm][1][sample].sum(axis=1)
        base_ee = arrays["BASELINE"][0][sample].sum(axis=1) / arrays["BASELINE"][1][sample].sum(axis=1)
        estimates[start:stop] = arm_ee - base_ee
    low, high = np.quantile(estimates, (0.025, 0.975), method="linear")
    return center, float(low), float(high)


def build_paired_figure(data: RootData) -> Any:
    _style()
    fig, axis = plt.subplots(figsize=(8.2, 4.8))
    learned = [arm for arm in data.arms if arm != "BASELINE"]
    x = np.asarray([rung.completed for rung in data.rungs])
    for arm in learned:
        triples = [_paired_bootstrap(data, rung, arm) for rung in data.rungs]
        center = np.asarray([value[0] for value in triples])
        low = np.asarray([value[1] for value in triples])
        high = np.asarray([value[2] for value in triples])
        axis.fill_between(x, low, high, color=COLORS[arm], alpha=0.13)
        axis.plot(x, center, marker="o", markersize=3, linewidth=1.6, color=COLORS[arm], label=arm)
    axis.axhline(0.0, color="#222222", linewidth=0.8)
    axis.set_xlabel("Cumulative episodes")
    axis.set_ylabel("Paired pooled EE difference vs BASELINE (bit/J)")
    axis.legend(ncol=min(3, len(learned)), frameon=False)
    _decorate(fig, data, title="matched-world paired differences (descriptive 95% bootstrap band)")
    fig.subplots_adjust(left=0.13, right=0.98, top=0.88, bottom=0.17)
    _assert_safe_labels(fig)
    return fig


def build_additive_figure(data: RootData) -> Any:
    _style()
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.6))
    for axis, metric, ylabel in (
        (axes[0], "total_bits", "Cumulative delivered bits (bit)"),
        (axes[1], "total_energy_j", "Cumulative energy (J)"),
    ):
        _plot_lines(axis, data, metric)
        axis.set_xlabel("Cumulative episodes")
        axis.set_ylabel(ylabel)
    axes[1].legend(ncol=min(2, len(data.arms)), frameon=False)
    _decorate(fig, data, title="additive physical endpoints")
    fig.subplots_adjust(left=0.09, right=0.98, top=0.86, bottom=0.18, wspace=0.28)
    _assert_safe_labels(fig)
    return fig


def _write_bytes_once(path: Path, content: bytes) -> None:
    try:
        with path.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as error:
        raise FigurePipelineError(f"refusing to overwrite output: {path}") from error


def _save_figure(fig: Any, output: Path, stem: str) -> list[dict[str, str]]:
    from io import BytesIO

    records: list[dict[str, str]] = []
    for extension in ("png", "pdf"):
        buffer = BytesIO()
        metadata = (
            {"Software": "v023-development-curves"}
            if extension == "png"
            else {"Creator": "v023-development-curves", "Producer": "matplotlib", "CreationDate": None, "ModDate": None}
        )
        fig.savefig(buffer, format=extension, metadata=metadata)
        content = buffer.getvalue()
        path = output / f"{stem}.{extension}"
        _write_bytes_once(path, content)
        records.append({"path": path.name, "sha256": hashlib.sha256(content).hexdigest()})
    plt.close(fig)
    return records


def render(
    roots: Sequence[str | Path],
    output_dir: str | Path,
    *,
    allow_nonformal: bool = False,
    additive_panels: bool = False,
) -> dict[str, Any]:
    if not roots:
        raise FigurePipelineError("at least one physical-evaluation root is required")
    output = Path(output_dir)
    if output.exists() or output.is_symlink():
        raise FigurePipelineError("output directory must be absent (write-once boundary)")
    datasets = [load_root(root, allow_nonformal=allow_nonformal) for root in roots]
    output.mkdir(parents=True, exist_ok=False)
    figure_records: list[dict[str, str]] = []
    builders = (("ee", build_ee_figure), ("service", build_service_figure), ("paired", build_paired_figure))
    if additive_panels:
        builders += (("additive", build_additive_figure),)
    for index, data in enumerate(datasets, start=1):
        for suffix, builder in builders:
            figure_records.extend(_save_figure(builder(data), output, f"root-{index:02d}-{suffix}"))
    code_digest = file_sha256(Path(__file__).resolve())
    manifest: dict[str, Any] = {
        "schema": "multi-catfish-mcrl-v023-ch5-development-figure-manifest-v1",
        "split_label": "TRAIN development",
        "nonformal_watermark": WATERMARK if any(not data.formal for data in datasets) else None,
        "code_sha256": code_digest,
        "input_roots": [
            {
                "index": index,
                "root_sha256": data.root_sha256,
                "formal": data.formal,
                "arms": list(data.arms),
                "claim_ceiling": data.claim_ceiling,
                "receipt_count": data.receipt_count,
                "rung_count": len(data.rungs),
                "rung_range": [data.rungs[0].completed, data.rungs[-1].completed],
                "authenticated_files": [
                    {"path": path, "sha256": digest} for path, digest in data.authenticated_files
                ],
            }
            for index, data in enumerate(datasets, start=1)
        ],
        "receipt_count": sum(data.receipt_count for data in datasets),
        "figures": figure_records,
    }
    _write_bytes_once(output / "FIGURE-MANIFEST.json", _canonical_bytes(manifest) + b"\n")
    return manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", required=True, help="primary physical-evaluation output root")
    parser.add_argument("--additional-root", action="append", default=[], help="additional physical-evaluation root; repeatable")
    parser.add_argument("--output-dir", required=True, help="absent write-once output directory")
    parser.add_argument("--allow-nonformal", action="store_true", help="admit rehearsal roots and watermark every figure")
    parser.add_argument("--additive-panels", action="store_true", help="also render cumulative bits and energy panels")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        manifest = render(
            [arguments.input_root, *arguments.additional_root],
            arguments.output_dir,
            allow_nonformal=arguments.allow_nonformal,
            additive_panels=arguments.additive_panels,
        )
    except FigurePipelineError as error:
        print(f"FIGURE_PIPELINE_REFUSED: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"output_dir": str(Path(arguments.output_dir).resolve()), "figures": len(manifest["figures"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
