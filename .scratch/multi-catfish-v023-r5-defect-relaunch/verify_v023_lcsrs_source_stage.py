#!/usr/bin/env python3
"""Authenticate the V0.23 source panel before any learner fit is launched.

This is a read-only, source-evidence-only boundary.  It reopens all eight
source shards through the independent scientific verifier and emits exactly
``INSUFFICIENT_PAIRS`` when the frozen coverage predicate fails (fewer than 24
eligible pairs, a world with no pair, or a fold below 80% placebo coverage).
It does not run a simulator, open TLE, fit a learner, or evaluate TEST.

The full launcher should invoke this command immediately after sealing
``source-manifest.json`` and before starting the first fit worker.  A decision
of ``INSUFFICIENT_PAIRS`` is a complete, authenticated early stop; any other
decision merely clears this one pre-fit coverage gate and does not claim C3
efficacy or authorize episode training.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
SCIENTIFIC_PATH = HERE / "verify_v023_lcsrs_scientific.py"
SCHEMA = "multi-catfish-mcrl-v023-lcsrs-observability-gate-v1-source-stage-decision"
CONTRACT_SHA256 = "1e69a2e7242198adce97e6357e4205a29fe6d1fb06a48dc7e1839a675529811a"
CLAIM_CEILING = (
    "TRAIN_DEVELOPMENT_SOURCE_AND_LEARNER_GATE_NO_TEST_NO_EPISODE_TRAINING_NO_EFFICACY"
)
WORLDS = tuple(range(2026121705, 2026121713))


class V023SourceStageError(RuntimeError):
    """The authenticated source-stage pre-fit boundary failed."""


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V023SourceStageError("source-stage value is not canonical finite JSON") from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V023SourceStageError(f"{field} is not a lowercase SHA-256")
    return value


def _load_scientific() -> ModuleType:
    target = Path(SCIENTIFIC_PATH)
    if target.is_symlink() or not target.is_file():
        raise V023SourceStageError(f"scientific verifier is missing or symlinked: {target}")
    spec = importlib.util.spec_from_file_location("mcrl_v023_source_stage_scientific", target)
    if spec is None or spec.loader is None:
        raise V023SourceStageError(f"cannot load scientific verifier: {target}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        raise V023SourceStageError("scientific verifier import failed") from error
    return module


def classify_source_panel(panel: Mapping[str, Any]) -> str:
    """Map the authenticated source panel to the pre-fit decision token."""

    predicates = panel.get("predicates")
    if not isinstance(predicates, Mapping):
        raise V023SourceStageError("source panel predicates are missing")
    if predicates.get("pair_coverage") is not True:
        return "INSUFFICIENT_PAIRS"
    return "SOURCE_STAGE_READY_FOR_FIT"


def build_source_stage_receipt(
    panel: Mapping[str, Any], *, preflight_sha256: str
) -> dict[str, Any]:
    """Build a sealed receipt without changing the verifier's panel result."""

    preflight = _digest(preflight_sha256, field="preflight_manifest_sha256")
    if panel.get("status") != "VERIFIED_SOURCE_PANEL_NUMERICS":
        raise V023SourceStageError("source panel was not independently verified")
    if panel.get("contract_sha256") != CONTRACT_SHA256:
        raise V023SourceStageError("source panel contract digest drifted")
    if panel.get("preflight_manifest_sha256") != preflight:
        raise V023SourceStageError("source panel preflight digest disagrees")
    if panel.get("worlds") != list(WORLDS):
        raise V023SourceStageError("source panel world order drifted")
    decision = classify_source_panel(panel)
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "VERIFIED_SOURCE_STAGE",
        "decision": decision,
        "claim_ceiling": CLAIM_CEILING,
        "contract_sha256": CONTRACT_SHA256,
        "preflight_manifest_sha256": preflight,
        "split": "TRAIN_DEVELOPMENT",
        "worlds": list(WORLDS),
        "source_count": len(WORLDS),
        "fit_launched": False,
        "learner_update": False,
        "episode_training": False,
        "test_split_opened": False,
        "coverage_predicate": bool(panel["predicates"]["pair_coverage"]),
        "source_panel": dict(panel),
        "note": (
            "INSUFFICIENT_PAIRS is a source-stage exposure stop; "
            "SOURCE_STAGE_READY_FOR_FIT clears only this pre-fit coverage check."
        ),
    }
    receipt["receipt_sha256"] = canonical_sha256(receipt)
    return receipt


def _write_once_json(path: Path, payload: Mapping[str, Any]) -> Path:
    target = Path(path).resolve(strict=False)
    if target.exists() or target.is_symlink():
        raise V023SourceStageError(f"refusing to overwrite source-stage receipt: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = _canonical_bytes(dict(payload))
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
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
    return target


def _read_canonical_receipt(path: Path) -> dict[str, Any]:
    requested = Path(path)
    if requested.is_symlink():
        raise V023SourceStageError("existing source-stage receipt is missing or symlinked")
    source = requested.resolve(strict=False)
    if not source.is_file():
        raise V023SourceStageError("existing source-stage receipt is missing or symlinked")
    raw = source.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V023SourceStageError("existing source-stage receipt is malformed") from error
    if not isinstance(payload, dict) or raw not in (
        _canonical_bytes(payload),
        _canonical_bytes(payload) + b"\n",
    ):
        raise V023SourceStageError("existing source-stage receipt is not canonical")
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", nargs=len(WORLDS), type=Path, required=True)
    parser.add_argument("--preflight-sha256", required=True)
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--output", type=Path)
    destination.add_argument("--verify-existing", type=Path)
    return parser


def run_source_stage_check(
    source_paths: Sequence[Path], *, preflight_sha256: str, output: Path
) -> Path:
    if len(source_paths) != len(WORLDS):
        raise V023SourceStageError("source-stage check requires exactly eight source shards")
    scientific = _load_scientific()
    try:
        panel = scientific.verify_source_panel_science(
            [Path(path).resolve() for path in source_paths]
        )
    except Exception as error:
        raise V023SourceStageError("independent source panel verification failed") from error
    receipt = build_source_stage_receipt(panel, preflight_sha256=preflight_sha256)
    return _write_once_json(output, receipt)


def verify_existing_source_stage(
    source_paths: Sequence[Path], *, preflight_sha256: str, receipt_path: Path
) -> Path:
    """Recompute the complete source panel and compare one cached receipt exactly."""

    if len(source_paths) != len(WORLDS):
        raise V023SourceStageError("source-stage check requires exactly eight source shards")
    scientific = _load_scientific()
    try:
        panel = scientific.verify_source_panel_science(
            [Path(path).resolve() for path in source_paths]
        )
    except Exception as error:
        raise V023SourceStageError("independent source panel verification failed") from error
    expected = build_source_stage_receipt(panel, preflight_sha256=preflight_sha256)
    actual = _read_canonical_receipt(receipt_path)
    if actual != expected:
        raise V023SourceStageError(
            "existing source-stage receipt disagrees with recomputed source numerics"
        )
    return Path(receipt_path).resolve()


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.verify_existing is not None:
            result = verify_existing_source_stage(
                args.source,
                preflight_sha256=str(args.preflight_sha256),
                receipt_path=args.verify_existing,
            )
        else:
            result = run_source_stage_check(
                args.source,
                preflight_sha256=str(args.preflight_sha256),
                output=args.output,
            )
    except V023SourceStageError as error:
        print(f"SOURCE_STAGE_ERROR: {error}", file=sys.stderr)
        return 2
    print(f"SOURCE_STAGE_PASS: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
