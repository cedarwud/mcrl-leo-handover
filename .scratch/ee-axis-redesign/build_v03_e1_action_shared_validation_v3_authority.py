#!/usr/bin/env python3
"""Build the V3 validation pre-metric authority after a passing C2 expansion.

This builder is intentionally unusable with a prepare-only or
``INSUFFICIENT_COVERAGE`` expansion.  It authenticates dependency metadata and
code bytes, opens no validation dataset, computes no validation metric, and
authorizes no test or EE access.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Sequence


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "e1_action_shared_validation_v3_authority_contract",
    HERE / "run_v03_e1_action_shared_validation_v3.py",
)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load V3 validation authority contract")
consumer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(consumer)


def build(
    *,
    source_root: Path,
    independent_root: Path,
    census_root: Path,
    expansion_root: Path,
    output_dir: Path,
    expected_independent_result_sha256: str,
    expected_independent_result_seal_sha256: str,
    expected_census_result_sha256: str,
    expected_census_result_seal_sha256: str,
    expected_expansion_authority_sha256: str,
    expected_expansion_authority_seal_sha256: str,
    expected_expansion_result_sha256: str,
    expected_expansion_result_seal_sha256: str,
) -> dict[str, object]:
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError("refusing to overwrite V3 preoutcome authority")
    dependencies = consumer.collect_preoutcome_dependencies(
        source_root=source_root,
        independent_root=independent_root,
        census_root=census_root,
        expansion_root=expansion_root,
        expected_independent_result_sha256=expected_independent_result_sha256,
        expected_independent_result_seal_sha256=(
            expected_independent_result_seal_sha256
        ),
        expected_census_result_sha256=expected_census_result_sha256,
        expected_census_result_seal_sha256=expected_census_result_seal_sha256,
        expected_expansion_authority_sha256=expected_expansion_authority_sha256,
        expected_expansion_authority_seal_sha256=(
            expected_expansion_authority_seal_sha256
        ),
        expected_expansion_result_sha256=expected_expansion_result_sha256,
        expected_expansion_result_seal_sha256=(
            expected_expansion_result_seal_sha256
        ),
    )
    payload = consumer.preoutcome_authority_payload(dependencies)
    if (
        payload.get("validation_dataset_bytes_opened") is not False
        or payload.get("validation_metrics_computed") is not False
        or payload.get("test_split_opened") is not False
        or payload.get("held_out_ee_evaluated") is not False
    ):
        raise consumer.ActionSharedValidationV3Error(
            "preoutcome authority crossed a prohibited evidence boundary"
        )
    output_dir.mkdir(parents=True)
    authority_sha256 = consumer.stable.sources._write_once_json(
        output_dir / "authority.json", payload
    )
    seal_sha256 = consumer.stable.sources._write_once_json(
        output_dir / "authority-seal.json",
        {
            "schema": consumer.PREOUTCOME_SEAL_SCHEMA,
            "authority_file_sha256": authority_sha256,
        },
    )
    return {
        **payload,
        "authority_file_sha256": authority_sha256,
        "authority_seal_file_sha256": seal_sha256,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--independent-root", type=Path, required=True)
    parser.add_argument("--census-root", type=Path, required=True)
    parser.add_argument("--expansion-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-independent-result-sha256", required=True)
    parser.add_argument("--expected-independent-result-seal-sha256", required=True)
    parser.add_argument("--expected-census-result-sha256", required=True)
    parser.add_argument("--expected-census-result-seal-sha256", required=True)
    parser.add_argument("--expected-expansion-authority-sha256", required=True)
    parser.add_argument("--expected-expansion-authority-seal-sha256", required=True)
    parser.add_argument("--expected-expansion-result-sha256", required=True)
    parser.add_argument("--expected-expansion-result-seal-sha256", required=True)
    args = parser.parse_args(argv)
    result = build(
        source_root=args.source_root,
        independent_root=args.independent_root,
        census_root=args.census_root,
        expansion_root=args.expansion_root,
        output_dir=args.output_dir,
        expected_independent_result_sha256=args.expected_independent_result_sha256,
        expected_independent_result_seal_sha256=(
            args.expected_independent_result_seal_sha256
        ),
        expected_census_result_sha256=args.expected_census_result_sha256,
        expected_census_result_seal_sha256=args.expected_census_result_seal_sha256,
        expected_expansion_authority_sha256=args.expected_expansion_authority_sha256,
        expected_expansion_authority_seal_sha256=(
            args.expected_expansion_authority_seal_sha256
        ),
        expected_expansion_result_sha256=args.expected_expansion_result_sha256,
        expected_expansion_result_seal_sha256=(
            args.expected_expansion_result_seal_sha256
        ),
    )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
