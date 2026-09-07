#!/usr/bin/env python3
"""Seal the all-four-arm non-formal chunk-equivalence acceptance evidence."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import stagec_common as common


def build(bindings_path: Path, receipts: list[Path]) -> dict[str, object]:
    bindings = common.verify_bindings(bindings_path)
    if len(receipts) != len(common.ARMS):
        raise common.StageCError("acceptance bundle requires exactly four arm receipts")
    records = []
    procedure_sha = bindings["acceptance_procedure"]["sha256"]
    code_sha = bindings["code"]["external_manifest_sha256"]
    for arm, path in zip(common.ARMS, receipts, strict=True):
        expected = common.verify_named_sidecar(path)
        receipt = common.read_json(path, field=f"{arm} acceptance receipt")
        if (
            receipt.get("status") != "PASS_BITWISE_CHUNK_EQUIVALENCE"
            or receipt.get("formal") is not False
            or receipt.get("arm") != arm
            or receipt.get("bindings_sha256") != common.file_sha256(bindings_path)
            or receipt.get("code_manifest_sha256") != code_sha
            or receipt.get("acceptance_procedure_sha256") != procedure_sha
            or receipt.get("merged_artifacts_compared")
            != ["episodes", "checkpoints", "rungs", "resume_states"]
        ):
            raise common.StageCError(f"{arm} acceptance receipt is not admissible")
        records.append({
            "arm": arm,
            "path": str(path.resolve()),
            "sha256": expected,
            "status": "PASS_BITWISE_CHUNK_EQUIVALENCE",
        })
    return {
        "schema": common.SCHEMA_ACCEPTANCE_BUNDLE,
        "status": "PASS_ALL_FOUR_ARM_CHUNK_EQUIVALENCE",
        "formal": False,
        "arms": list(common.ARMS),
        "bindings_sha256": common.file_sha256(bindings_path),
        "code_manifest_sha256": code_sha,
        "acceptance_procedure_sha256": procedure_sha,
        "receipts": records,
        "scientific_output_emitted": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bindings", type=Path, required=True)
    parser.add_argument("--receipts", type=Path, nargs=4, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        payload = build(args.bindings, args.receipts)
        common.write_once(args.output, payload)
        common.write_digest_sidecar(args.output)
    except Exception as error:
        print(f"STAGEC_ACCEPTANCE_BUNDLE_ERROR: {error}", file=sys.stderr)
        return 2
    print(f"PASS_ALL_FOUR_ARM_CHUNK_EQUIVALENCE bundle={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
