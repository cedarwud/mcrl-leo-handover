#!/usr/bin/env python3
"""Exact semantic comparator for two C2 V0.3 runtime snapshots."""

from __future__ import annotations

import argparse
from dataclasses import fields, is_dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SMC = HERE.parent / "smc-er-short-ep"
for _path in (HERE, SMC, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))


SCHEMA = "c2-v03-resume-parity-receipt-v2"
CLAIM_CEILING = (
    "bounded training-result resume parity with real monotonic-clock provenance "
    "retained; no EE efficacy, training trend, or Chapter-5 result"
)
CHRONOLOGY_TIME_FIELDS = (
    "forecast_started_ns",
    "forecast_completed_ns",
    "live_step_started_ns",
    "live_step_completed_ns",
)
_ALLOWED_STATE_DIFFERENCE = re.compile(
    r"^\$\['(?:"
    r"c2_option_ledger'\]\['records'\]\[\d+\]\['sequence_sha256"
    r"|joint_transaction_ledger'\]\['records'\]\[\d+\]\['(?:"
    r"transition_sha256|primitive_sequence_sha256|record_sha256)"
    r")'\]$"
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load(path: Path) -> Mapping[str, Any]:
    try:
        value = torch.load(path, map_location="cpu", weights_only=False)
    except TypeError:
        value = torch.load(path, map_location="cpu")
    if not isinstance(value, Mapping):
        raise TypeError("runtime state must be a mapping")
    return value


def _load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _json_digest(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _type_name(value: Any) -> str:
    cls = type(value)
    return f"{cls.__module__}.{cls.__qualname__}"


def exact_differences(
    left: Any,
    right: Any,
    *,
    path: str = "$",
    limit: int = 64,
) -> list[str]:
    """Return exact semantic differences, including every tensor/array byte."""

    differences: list[str] = []
    seen: set[tuple[int, int]] = set()

    def add(message: str) -> None:
        if len(differences) < limit:
            differences.append(message)

    def compare(a: Any, b: Any, current: str) -> None:
        if len(differences) >= limit:
            return
        if type(a) is not type(b):
            add(f"{current}: type {_type_name(a)} != {_type_name(b)}")
            return
        if isinstance(a, torch.Tensor):
            if a.dtype != b.dtype or tuple(a.shape) != tuple(b.shape):
                add(
                    f"{current}: tensor metadata {(a.dtype, tuple(a.shape))} != "
                    f"{(b.dtype, tuple(b.shape))}"
                )
            elif not torch.equal(a.detach().cpu(), b.detach().cpu()):
                add(f"{current}: tensor bytes differ")
            return
        if isinstance(a, np.ndarray):
            if a.dtype != b.dtype or a.shape != b.shape:
                add(
                    f"{current}: array metadata {(a.dtype, a.shape)} != "
                    f"{(b.dtype, b.shape)}"
                )
            elif not np.array_equal(a, b, equal_nan=True):
                add(f"{current}: array values differ")
            return
        if isinstance(a, np.generic):
            if a.dtype != b.dtype or a.item() != b.item():
                add(f"{current}: numpy scalar differs")
            return
        if isinstance(a, Mapping):
            pair = (id(a), id(b))
            if pair in seen:
                return
            seen.add(pair)
            if set(a) != set(b):
                add(
                    f"{current}: mapping keys differ; "
                    f"left_only={sorted(map(str, set(a) - set(b)))} "
                    f"right_only={sorted(map(str, set(b) - set(a)))}"
                )
                return
            for key in sorted(a, key=lambda item: str(item)):
                compare(a[key], b[key], f"{current}[{key!r}]")
            return
        if is_dataclass(a) and not isinstance(a, type):
            if _type_name(a) != _type_name(b):
                add(f"{current}: dataclass types differ")
                return
            for item in fields(a):
                compare(
                    getattr(a, item.name),
                    getattr(b, item.name),
                    f"{current}.{item.name}",
                )
            return
        if isinstance(a, (list, tuple)):
            if len(a) != len(b):
                add(f"{current}: sequence length {len(a)} != {len(b)}")
                return
            for index, (left_item, right_item) in enumerate(zip(a, b, strict=True)):
                compare(left_item, right_item, f"{current}[{index}]")
            return
        if isinstance(a, (set, frozenset)):
            if a != b:
                add(f"{current}: set values differ")
            return
        if isinstance(a, float):
            if math.isnan(a) and math.isnan(b):
                return
            if a != b:
                add(f"{current}: float {a!r} != {b!r}")
            return
        raw_a = getattr(a, "__dict__", None)
        raw_b = getattr(b, "__dict__", None)
        if isinstance(raw_a, Mapping) and isinstance(raw_b, Mapping):
            compare(raw_a, raw_b, f"{current}.__dict__")
            return
        try:
            equal = a == b
        except Exception as error:
            add(f"{current}: equality raised {type(error).__name__}: {error}")
            return
        if isinstance(equal, (np.ndarray, torch.Tensor)):
            add(f"{current}: equality returned a non-scalar result")
        elif not bool(equal):
            add(f"{current}: value {a!r} != {b!r}")

    compare(left, right, path)
    return differences


def _difference_path(message: str) -> str:
    return message.split(": ", 1)[0]


def _state_difference_classes(
    differences: Sequence[str],
) -> tuple[list[str], list[str]]:
    allowed: list[str] = []
    unexpected: list[str] = []
    for item in differences:
        target = allowed if _ALLOWED_STATE_DIFFERENCE.fullmatch(
            _difference_path(item)
        ) else unexpected
        target.append(item)
    return allowed, unexpected


def _chronology_digest(receipt: Mapping[str, Any]) -> str:
    fields = (
        "schema",
        "option_id",
        "anchor_sha256",
        "live_rng_before_sha256",
        "live_rng_after_forecast_sha256",
        "forecast_rng_sha256",
        "forecast_request_sha256",
        "forecast_payload_sha256",
        *CHRONOLOGY_TIME_FIELDS,
        "forecast_sequence",
        "live_rng_unchanged_during_forecast",
        "claim_ceiling",
    )
    if set(receipt) != set(fields):
        raise ValueError("chronology receipt fields drifted")
    times = tuple(receipt[name] for name in CHRONOLOGY_TIME_FIELDS)
    if any(type(value) is not int or value < 0 for value in times):
        raise ValueError("chronology timestamps must be nonnegative exact integers")
    if tuple(sorted(times)) != times:
        raise ValueError("chronology timestamps are out of order")
    return _json_digest({name: receipt[name] for name in fields})


def _clock_excluded_digest(receipt: Mapping[str, Any]) -> str:
    return _json_digest(
        {
            name: value
            for name, value in receipt.items()
            if name not in CHRONOLOGY_TIME_FIELDS
        }
    )


def _load_status(run_dir: Path) -> Mapping[str, Any]:
    value = _load_json(run_dir / "status.json")
    if not isinstance(value, Mapping) or value.get("status") != "complete":
        raise ValueError("resume parity requires a completed status.json")
    return value


def _validate_audits(
    full_dir: Path,
    resumed_dir: Path,
) -> tuple[dict[str, Any], list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    status = _load_status(resumed_dir)
    result = status.get("result")
    if not isinstance(result, Mapping):
        raise ValueError("resumed status lacks its result mapping")
    start_episode = result.get("start_episode")
    if type(start_episode) is not int or start_episode < 0:
        raise ValueError("resumed status lacks an absolute start_episode")

    full_raw = _load_json(full_dir / "c2-option-chronology-audits.json")
    resumed_raw = _load_json(resumed_dir / "c2-option-chronology-audits.json")
    if not isinstance(full_raw, list) or not isinstance(resumed_raw, list):
        raise ValueError("option chronology audits must be JSON lists")
    full = [
        item
        for item in full_raw
        if isinstance(item, Mapping) and item.get("episode", -1) >= start_episode
    ]
    resumed = [item for item in resumed_raw if isinstance(item, Mapping)]
    if len(full) != len(resumed):
        raise ValueError("continuation chronology audit counts differ")

    errors: list[str] = []
    normalized_full: list[dict[str, Any]] = []
    normalized_resumed: list[dict[str, Any]] = []
    clock_values_differ = False
    for index, (left, right) in enumerate(zip(full, resumed, strict=True)):
        for side, item in (("full", left), ("resumed", right)):
            if item.get("audit_available") is not True:
                errors.append(f"{side}[{index}] chronology audit unavailable")
                continue
            receipt = item.get("chronology_receipt")
            if not isinstance(receipt, Mapping):
                errors.append(f"{side}[{index}] chronology receipt missing")
                continue
            try:
                actual = _chronology_digest(receipt)
            except (TypeError, ValueError) as error:
                errors.append(f"{side}[{index}] invalid chronology: {error}")
                continue
            if actual != item.get("chronology_receipt_sha256"):
                errors.append(f"{side}[{index}] chronology digest mismatch")
            if _clock_excluded_digest(receipt) != item.get(
                "clock_excluded_identity_sha256"
            ):
                errors.append(f"{side}[{index}] clock-excluded digest mismatch")

        left_copy = json.loads(json.dumps(left))
        right_copy = json.loads(json.dumps(right))
        left_receipt = left_copy.get("chronology_receipt", {})
        right_receipt = right_copy.get("chronology_receipt", {})
        if isinstance(left_receipt, dict) and isinstance(right_receipt, dict):
            if any(
                left_receipt.get(name) != right_receipt.get(name)
                for name in CHRONOLOGY_TIME_FIELDS
            ):
                clock_values_differ = True
            for name in CHRONOLOGY_TIME_FIELDS:
                left_receipt[name] = "<real-monotonic-clock>"
                right_receipt[name] = "<real-monotonic-clock>"
        for name in (
            "chronology_receipt_sha256",
            "admission_plan_sha256",
            "admission_proof_sha256",
            "transition_sha256",
            "primitive_sequence_sha256",
            "joint_record_sha256",
        ):
            left_copy[name] = "<chronology-bound-integrity-hash>"
            right_copy[name] = "<chronology-bound-integrity-hash>"
        normalized_full.append(left_copy)
        normalized_resumed.append(right_copy)

    normalized_differences = exact_differences(
        normalized_full, normalized_resumed, path="$audits"
    )
    errors.extend(normalized_differences)
    return (
        {
            "status": "PASS" if not errors else "FAIL",
            "resume_start_episode": start_episode,
            "paired_option_count": len(full),
            "real_clock_values_differ": clock_values_differ,
            "clock_excluded_identity_exact": not normalized_differences,
            "errors": errors,
        },
        full,
        resumed,
    )


def _validate_ledger_bindings(
    state: Mapping[str, Any],
    audits: Sequence[Mapping[str, Any]],
) -> list[str]:
    errors: list[str] = []
    c2_records = state.get("c2_option_ledger", {}).get("records", [])
    joint_records = state.get("joint_transaction_ledger", {}).get("records", [])
    c2_by_option = {item.get("option_id"): item for item in c2_records}
    joint_by_option = {item.get("option_id"): item for item in joint_records}
    for index, audit in enumerate(audits):
        option_id = audit.get("option_id")
        c2_record = c2_by_option.get(option_id)
        if c2_record is None:
            errors.append(f"audit[{index}] option missing from C2 ledger")
            continue
        if c2_record.get("sequence_sha256") != audit.get(
            "primitive_sequence_sha256"
        ):
            errors.append(f"audit[{index}] primitive sequence is not ledger-bound")
        joint_record = joint_by_option.get(option_id)
        if audit.get("joint_record_sha256") is not None:
            if joint_record is None:
                errors.append(f"audit[{index}] option missing from joint ledger")
                continue
            for ledger_name, audit_name in (
                ("primitive_sequence_sha256", "primitive_sequence_sha256"),
                ("transition_sha256", "transition_sha256"),
                ("record_sha256", "joint_record_sha256"),
            ):
                if joint_record.get(ledger_name) != audit.get(audit_name):
                    errors.append(
                        f"audit[{index}] {audit_name} is not joint-ledger-bound"
                    )
    return errors


def verify(full: Path, resumed: Path) -> dict[str, Any]:
    full = Path(full).expanduser().resolve()
    resumed = Path(resumed).expanduser().resolve()
    left = _load(full)
    right = _load(resumed)
    differences = exact_differences(left, right)
    allowed, unexpected = _state_difference_classes(differences)
    full_dir = full.parent
    resumed_dir = resumed.parent
    full_checkpoint = full_dir / "final-checkpoint.pt"
    resumed_checkpoint = resumed_dir / "final-checkpoint.pt"
    checkpoint_exact = (
        full_checkpoint.is_file()
        and resumed_checkpoint.is_file()
        and _sha256_file(full_checkpoint) == _sha256_file(resumed_checkpoint)
    )
    try:
        audit_report, full_audits, resumed_audits = _validate_audits(
            full_dir, resumed_dir
        )
        binding_errors = [
            *(
                f"full: {item}"
                for item in _validate_ledger_bindings(left, full_audits)
            ),
            *(
                f"resumed: {item}"
                for item in _validate_ledger_bindings(right, resumed_audits)
            ),
        ]
    except (OSError, TypeError, ValueError) as error:
        audit_report = {
            "status": "FAIL",
            "errors": [f"{type(error).__name__}: {error}"],
        }
        binding_errors = []
    episodes_exact = left.get("episodes_completed") == right.get(
        "episodes_completed"
    )
    training_result_equivalent = bool(
        not unexpected
        and checkpoint_exact
        and episodes_exact
        and audit_report.get("status") == "PASS"
        and not binding_errors
    )
    return {
        "schema": SCHEMA,
        "status": "PASS" if training_result_equivalent else "FAIL",
        "claim_ceiling": CLAIM_CEILING,
        "full_state": {"path": str(full), "sha256": _sha256_file(full)},
        "resumed_state": {
            "path": str(resumed),
            "sha256": _sha256_file(resumed),
        },
        "byte_identical": _sha256_file(full) == _sha256_file(resumed),
        "runtime_state_semantic_exact": not differences,
        "training_result_equivalent": training_result_equivalent,
        "final_checkpoint": {
            "full_path": str(full_checkpoint),
            "resumed_path": str(resumed_checkpoint),
            "byte_identical": checkpoint_exact,
            "sha256": (
                _sha256_file(full_checkpoint)
                if full_checkpoint.is_file()
                else None
            ),
        },
        "difference_count_capped": len(differences),
        "differences": differences,
        "allowed_clock_provenance_differences": allowed,
        "unexpected_state_differences": unexpected,
        "chronology_audit": audit_report,
        "ledger_binding_errors": binding_errors,
        "episodes_completed": {
            "full": left.get("episodes_completed"),
            "resumed": right.get("episodes_completed"),
        },
    }


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", type=Path, required=True)
    parser.add_argument("--resumed", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    payload = verify(args.full, args.resumed)
    if args.output is not None:
        output = Path(args.output).expanduser().resolve()
        if output.exists():
            raise FileExistsError(f"refusing to overwrite parity receipt: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(output.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(output)
        print(output)
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
