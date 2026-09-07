#!/usr/bin/env python3
"""Integrity-only array-domain adapter for the frozen R7 final verifier."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from types import ModuleType
from typing import Any, Mapping, Sequence


SCHEMA = "multi-catfish-mcrl-v023-r7-final-verifier-domain-repair-v2"
STATUS = "PASS_R7_FINAL_VERIFIER_DOMAIN_REPAIR_R2"
CLAIM_CEILING = (
    "TRAIN_DEVELOPMENT_INTEGRITY_ONLY_DOMAIN_AND_IMPORT_CLOSURE_REPAIR_"
    "NO_TEST_NO_EPISODE_TRAINING_NO_EFFICACY"
)
ORIGINAL_VERIFIER_SHA256 = (
    "3cc573717f010d8b67ede027d05ef79f4c69497e9654d6766df50e88e9aa4717"
)
INVALID_VERIFICATION_SHA256 = (
    "2b14fb95b9599b1c6abd50a63ab7adaaf61e31a8bbf448ada625b4242fd6a64f"
)
SOURCE_ARRAY_SCHEMA = (
    "multi-catfish-mcrl-v023-lcsrs-source-artifact-v1-arrays-v1"
)
SOURCE_ARRAY_DOMAIN = "source-array-v1"
COMPOSITION_ARRAY_DOMAIN = "v023-composition-array-v1"
EXPECTED_INVALID_ERROR = "source 2026121801 array anchor_phase digest disagrees"
EXPECTED_SOURCE_LOADS = 8
EXPECTED_COMPOSITION_LOADS = 48
EXPECTED_PREFLIGHT_MANIFEST_SHA256 = (
    "9b08e3acc1d1d9b0cf506c3137f8e4013345ed8fb6f54c385a312ddb8570772a"
)
_DIGEST = re.compile(r"^[0-9a-f]{64}$")

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ORIGINAL_VERIFIER = (
    REPO
    / ".scratch/multi-catfish-v023-r7-launch-ready"
    / "verify_v023_lcsrs_final.py"
)


class V023R7DomainRepairError(RuntimeError):
    """The single authorized final-verifier repair failed closed."""


def _sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise V023R7DomainRepairError(f"expected regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii") + b"\n"
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V023R7DomainRepairError("repair receipt is not canonical finite JSON") from error


def _read_canonical(path: Path) -> dict[str, Any]:
    raw = path.read_bytes() if path.is_file() and not path.is_symlink() else b""
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise V023R7DomainRepairError(f"invalid canonical JSON: {path}") from error
    if not isinstance(payload, dict) or raw not in (
        _canonical_bytes(payload),
        _canonical_bytes(payload).rstrip(b"\n"),
    ):
        raise V023R7DomainRepairError(f"noncanonical JSON: {path}")
    return payload


def _write_once(path: Path, data: bytes) -> str:
    if path.exists() or path.is_symlink():
        raise V023R7DomainRepairError(f"refusing to overwrite: {path}")
    if path.parent.is_symlink() or not path.parent.is_dir():
        raise V023R7DomainRepairError(f"output parent is unavailable: {path.parent}")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return hashlib.sha256(data).hexdigest()


def _load_original() -> ModuleType:
    if _sha256(ORIGINAL_VERIFIER) != ORIGINAL_VERIFIER_SHA256:
        raise V023R7DomainRepairError("frozen original final verifier digest drifted")
    name = "v023_lcsrs_frozen_final_verifier_for_domain_repair"
    specification = importlib.util.spec_from_file_location(name, ORIGINAL_VERIFIER)
    if specification is None or specification.loader is None:
        raise V023R7DomainRepairError("cannot load frozen original final verifier")
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


@contextmanager
def _temporary_import_path(path: Path):
    """Expose frozen verifier siblings only for the verifier call.

    The additive repair has a different entry-point directory from the frozen
    verifier.  Its preflight module performs one ordinary sibling import, so a
    spec-loaded verifier otherwise returns INVALID before any array-domain
    dispatch is reached.
    """

    value = str(Path(path).resolve())
    original = list(sys.path)
    sys.path.insert(0, value)
    try:
        yield
    finally:
        sys.path[:] = original


def _install_domain_dispatch(module: ModuleType) -> tuple[Any, dict[str, int]]:
    original_loader = getattr(module, "_load_npz", None)
    if not callable(original_loader):
        raise V023R7DomainRepairError("frozen verifier has no NPZ loader")
    counts = {"source": 0, "composition": 0}

    def dispatch(root: Path, binding: Mapping[str, Any], *, label: str):
        if not isinstance(binding, Mapping):
            raise V023R7DomainRepairError("NPZ binding is not a mapping")
        schema = binding.get("schema")
        declared = binding.get("array_domain")
        if schema == SOURCE_ARRAY_SCHEMA and (
            "array_domain" not in binding or declared == SOURCE_ARRAY_DOMAIN
        ):
            domain = SOURCE_ARRAY_DOMAIN
            counts["source"] += 1
        elif schema is None and declared == COMPOSITION_ARRAY_DOMAIN:
            domain = COMPOSITION_ARRAY_DOMAIN
            counts["composition"] += 1
        else:
            raise V023R7DomainRepairError(
                f"unsupported NPZ schema/domain at {label}: {schema!r}/{declared!r}"
            )
        previous = module.V023_ARRAY_DOMAIN
        module.V023_ARRAY_DOMAIN = domain
        try:
            return original_loader(root, binding, label=label)
        finally:
            module.V023_ARRAY_DOMAIN = previous

    module._load_npz = dispatch
    return original_loader, counts


def _verify_invalid_attempt(path: Path) -> str:
    digest = _sha256(path)
    if digest != INVALID_VERIFICATION_SHA256:
        raise V023R7DomainRepairError("invalid verification receipt digest drifted")
    payload = _read_canonical(path)
    expected = {
        "status": "INVALID_RUN",
        "integrity_status": "INVALID",
        "scientific_claim": False,
        "test_split_opened": False,
        "episode_training": False,
        "no_scientific_token_before_integrity": True,
        "c3_decision": "INVALID_RUN",
        "errors": [EXPECTED_INVALID_ERROR],
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            raise V023R7DomainRepairError(
                f"invalid verification receipt drifted at {field}"
            )
    return digest


def run(
    *,
    source_paths: Sequence[Path],
    fit_paths: Sequence[Path],
    composition_paths: Sequence[Path],
    source_manifest: Path,
    launch_manifest: Path,
    launch_manifest_digest: Path,
    invalid_verification: Path,
    contract: Path,
    output: Path,
    receipt: Path,
) -> dict[str, Any]:
    if len(source_paths) != 8 or len(fit_paths) != 48 or len(composition_paths) != 48:
        raise V023R7DomainRepairError("repair requires the exact 8/48/48 panel")
    contract_sha = _sha256(contract)
    invalid_sha = _verify_invalid_attempt(invalid_verification)
    original = _load_original()
    original_loader, counts = _install_domain_dispatch(original)
    try:
        with _temporary_import_path(ORIGINAL_VERIFIER.parent):
            result = original.verify_v023_final_gate(
                source_paths=tuple(source_paths),
                fit_paths=tuple(fit_paths),
                composition_paths=tuple(composition_paths),
                source_manifest_path=source_manifest,
                expected_preflight_manifest_sha256=EXPECTED_PREFLIGHT_MANIFEST_SHA256,
                launch_manifest_path=launch_manifest,
                launch_manifest_digest_path=launch_manifest_digest,
            )
    finally:
        original._load_npz = original_loader
    if counts != {
        "source": EXPECTED_SOURCE_LOADS,
        "composition": EXPECTED_COMPOSITION_LOADS,
    }:
        raise V023R7DomainRepairError(f"NPZ domain dispatch count drifted: {counts}")
    output_sha = _write_once(output, _canonical_bytes(result))
    passed = (
        result.get("status") == "PASS_FINAL_INTEGRITY"
        and result.get("integrity_status") == "VERIFIED"
        and result.get("source_count") == 8
        and result.get("fit_count") == 48
        and result.get("composition_count") == 48
        and result.get("scientific_claim") is False
        and result.get("test_split_opened") is False
        and result.get("episode_training") is False
    )
    receipt_payload = {
        "schema": SCHEMA,
        "status": STATUS if passed else "FAILED_R7_FINAL_VERIFIER_DOMAIN_REPAIR",
        "claim_ceiling": CLAIM_CEILING,
        "contract_sha256": contract_sha,
        "repair_adapter_sha256": _sha256(Path(__file__).resolve()),
        "original_verifier_sha256": ORIGINAL_VERIFIER_SHA256,
        "preflight_manifest_sha256": EXPECTED_PREFLIGHT_MANIFEST_SHA256,
        "invalid_verification_sha256": invalid_sha,
        "corrected_verification_sha256": output_sha,
        "domain_dispatch": {
            "source": SOURCE_ARRAY_DOMAIN,
            "composition": COMPOSITION_ARRAY_DOMAIN,
            "source_loads": counts["source"],
            "composition_loads": counts["composition"],
        },
        "sibling_import_path_scoped": True,
        "corrected_integrity_status": result.get("integrity_status"),
        "corrected_status": result.get("status"),
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "scientific_claim": False,
    }
    _write_once(receipt, _canonical_bytes(receipt_payload))
    if not passed:
        raise V023R7DomainRepairError("corrected final verification remains invalid")
    return receipt_payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", nargs=8, type=Path, required=True)
    parser.add_argument("--fit", nargs=48, type=Path, required=True)
    parser.add_argument("--composition", nargs=48, type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--launch-manifest", type=Path, required=True)
    parser.add_argument("--launch-manifest-digest", type=Path, required=True)
    parser.add_argument("--invalid-verification", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        receipt = run(
            source_paths=args.source,
            fit_paths=args.fit,
            composition_paths=args.composition,
            source_manifest=args.source_manifest,
            launch_manifest=args.launch_manifest,
            launch_manifest_digest=args.launch_manifest_digest,
            invalid_verification=args.invalid_verification,
            contract=args.contract,
            output=args.output,
            receipt=args.receipt,
        )
    except Exception as error:
        print(f"V023_R7_DOMAIN_REPAIR_FAILED: {error}", file=sys.stderr)
        return 2
    print(
        "V023_R7_DOMAIN_REPAIR_PASS "
        f"source_loads={receipt['domain_dispatch']['source_loads']} "
        f"composition_loads={receipt['domain_dispatch']['composition_loads']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "COMPOSITION_ARRAY_DOMAIN",
    "SOURCE_ARRAY_DOMAIN",
    "SOURCE_ARRAY_SCHEMA",
    "V023R7DomainRepairError",
    "_install_domain_dispatch",
    "build_parser",
    "main",
    "run",
]
