#!/usr/bin/env python3
"""Seal all-four-arm chunk-equivalence acceptance evidence."""

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
    receipt_modes: list[bool] = []
    procedure_sha = bindings["acceptance_procedure"]["sha256"]
    code_sha = bindings["code"]["external_manifest_sha256"]
    for arm, path in zip(common.ARMS, receipts, strict=True):
        expected = common.verify_named_sidecar(path)
        receipt = common.read_json(path, field=f"{arm} acceptance receipt")
        if (
            receipt.get("status") != "PASS_BITWISE_CHUNK_EQUIVALENCE"
            or type(receipt.get("formal")) is not bool
            or receipt.get("arm") != arm
            or receipt.get("bindings_sha256") != common.file_sha256(bindings_path)
            or receipt.get("code_manifest_sha256") != code_sha
            or receipt.get("acceptance_procedure_sha256") != procedure_sha
            or receipt.get("receipt_comparison_excluded_provenance_fields")
            != list(common.CHUNK_EQUIVALENCE_PROVENANCE_ONLY_FIELDS)
            or receipt.get("merged_artifacts_compared")
            != list(common.CHUNK_EQUIVALENCE_ARTIFACTS)
        ):
            raise common.StageCError(f"{arm} acceptance receipt is not admissible")
        formal = receipt["formal"]
        if formal:
            shape_ok = (
                receipt.get("episodes") == 200
                and receipt.get("chunks") == [[1, 100], [101, 200]]
                and receipt.get("rehearsal_chunk") is None
            )
        else:
            shape_ok = (
                receipt.get("episodes") == 100
                and receipt.get("chunks") == [[1, 50], [51, 100]]
                and receipt.get("rehearsal_chunk") == 50
            )
        if not shape_ok:
            raise common.StageCError(f"{arm} acceptance receipt mode/shape drifted")
        receipt_modes.append(formal)
        records.append({
            "arm": arm,
            "path": str(path.resolve()),
            "sha256": expected,
            "status": "PASS_BITWISE_CHUNK_EQUIVALENCE",
        })
    if len(set(receipt_modes)) != 1:
        raise common.StageCError("acceptance bundle cannot mix formal and rehearsal receipts")
    formal = receipt_modes[0]
    return {
        "schema": common.SCHEMA_ACCEPTANCE_BUNDLE,
        "status": "PASS_ALL_FOUR_ARM_CHUNK_EQUIVALENCE",
        "formal": formal,
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
