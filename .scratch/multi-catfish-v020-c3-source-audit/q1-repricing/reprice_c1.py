#!/usr/bin/env python3
"""Offline C1 target reconstruction and lambda repricing.

This tool is intentionally source-only.  It reads the seven explicitly named
opening source files from the V0.3 E1 action-shared supplement, keeps rows whose
top-level ``admitted_route`` is exactly ``C1``, reconstructs the persisted C1
target, and computes the same target at one pre-frozen development multiplier.

It never imports the simulator, opens a TEST source, launches a learner, or
changes any shared source, document, or authority file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any, Iterable, Mapping


REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_DIR = (
    REPO_ROOT
    / "artifacts"
    / "multi-catfish-v03-e1-action-shared-supplement-20260901"
    / "source-data"
)
SOURCE_RECEIPT = SOURCE_DIR / "receipt.json"
OUTPUT_DIR = Path(__file__).resolve().parent

SOURCE_SEEDS = (2026092001, 2026092002, 2026092003, 2026092004, 2026092005, 2026092006, 2026092007)
SOURCE_SEED_SPLIT = {
    2026092001: "train",
    2026092002: "train",
    2026092003: "train",
    2026092004: "train",
    2026092005: "validation",
    2026092006: "validation",
    2026092007: "validation",
}
OLD_LAMBDA_HEX = "0x1.443a8f481639ap+26"
NEW_LAMBDA_HEX = "0x1.c3c0a7b6b86d3p+26"
OLD_LAMBDA_BITS_PER_J = float.fromhex(OLD_LAMBDA_HEX)
NEW_LAMBDA_BITS_PER_J = float.fromhex(NEW_LAMBDA_HEX)
OLD_TARGET_KEY = "zeta1_focal_surplus_bits"
SOURCE_SCHEMA = "multi-catfish-mcrl-v03-opening-dataset-v3"
RAW_SCHEMA = "multi-catfish-mcrl-v03-opening-source-v2"
C1_SOURCE_RULE = "c1-exp-dull-rollout-lower-frontier-v1"
OLD_ERROR_TOLERANCE_BITS = 1e-3


def sha256_file(path: Path) -> str:
    """Return the SHA-256 of one file without changing it."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _hex_float(value: object, *, field: str) -> float:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a hexadecimal float string")
    try:
        decoded = float.fromhex(value)
    except ValueError as error:
        raise ValueError(f"{field} is not a hexadecimal float: {value!r}") from error
    if not math.isfinite(decoded):
        raise ValueError(f"{field} must be finite")
    return decoded


def _hex(value: float) -> str:
    return float(value).hex()


def _sign(value: float) -> int:
    if value > 0.0:
        return 1
    if value < 0.0:
        return -1
    return 0


def c1_zeta1(
    *,
    candidate_rate_bps: float,
    reference_rate_bps: float,
    candidate_system_power_w: float,
    reference_system_power_w: float,
    interval_s: float,
    lambda_bits_per_j: float,
) -> float:
    """Reconstruct the canonical scalar C1 focal opening surplus in bits."""

    return float(
        interval_s
        * (
            (candidate_rate_bps - reference_rate_bps)
            - lambda_bits_per_j
            * (candidate_system_power_w - reference_system_power_w)
        )
    )


def _nearest_rank(values: list[float], quantile: float) -> float:
    if not values:
        raise ValueError("cannot compute a quantile of an empty sequence")
    ordered = sorted(values)
    index = max(0, math.ceil(quantile * len(ordered)) - 1)
    return float(ordered[index])


def _stats(values: Iterable[float]) -> dict[str, Any]:
    values = [float(value) for value in values]
    if not values or not all(math.isfinite(value) for value in values):
        raise ValueError("statistics require non-empty finite values")
    positive = sum(value > 0.0 for value in values)
    negative = sum(value < 0.0 for value in values)
    zero = len(values) - positive - negative
    return {
        "count": len(values),
        "positive": positive,
        "negative": negative,
        "zero": zero,
        "positive_fraction": positive / len(values),
        "negative_fraction": negative / len(values),
        "min_hex": _hex(min(values)),
        "max_hex": _hex(max(values)),
        "mean_hex": _hex(statistics.fmean(values)),
        "median_hex": _hex(statistics.median(values)),
        "std_population_hex": _hex(statistics.pstdev(values)),
        "p05_nearest_rank_hex": _hex(_nearest_rank(values, 0.05)),
        "p95_nearest_rank_hex": _hex(_nearest_rank(values, 0.95)),
        "sum_hex": _hex(math.fsum(values)),
    }


def _source_path(seed: int) -> Path:
    return SOURCE_DIR / f"opening-{seed}.json"


def _load_source_receipt() -> Mapping[str, Any]:
    with SOURCE_RECEIPT.open("r", encoding="utf-8") as stream:
        receipt = json.load(stream)
    if receipt.get("source_manifest_sha256") != "9ec832c71b29ad84e37856db1f5d237f07d177c62cc93fbb66de06d808184a0a":
        raise ValueError("source receipt is not bound to the frozen source manifest")
    if receipt.get("held_out_ee_evaluated") is not False:
        raise ValueError("source receipt does not state held-out EE was unopened")
    return receipt


def _load_source(seed: int, receipt: Mapping[str, Any]) -> Mapping[str, Any]:
    path = _source_path(seed)
    if not path.is_file():
        raise FileNotFoundError(path)
    expected_file_hash = receipt["opening_dataset_file_sha256s"][str(seed)]
    actual_file_hash = sha256_file(path)
    if actual_file_hash != expected_file_hash:
        raise ValueError(f"{path.name} byte hash mismatch")
    with path.open("r", encoding="utf-8") as stream:
        payload = json.load(stream)
    if payload.get("schema") != SOURCE_SCHEMA:
        raise ValueError(f"{path.name} has stale dataset schema")
    if payload.get("source_manifest_sha256") != receipt["source_manifest_sha256"]:
        raise ValueError(f"{path.name} source manifest mismatch")
    if payload.get("dataset_sha256") != receipt["opening_dataset_sha256s"][str(seed)]:
        raise ValueError(f"{path.name} canonical dataset hash mismatch")
    if not isinstance(payload.get("rows"), list):
        raise ValueError(f"{path.name} rows are not a list")
    return payload


def _validate_admitted_c1_row(row: Mapping[str, Any], *, seed: int, row_index: int) -> dict[str, Any]:
    if row.get("admitted_route") != "C1":
        raise ValueError("internal error: a non-C1 row reached the C1 validator")
    if row.get("routes", {}).get("C1", {}).get("source_rule") != C1_SOURCE_RULE:
        raise ValueError(f"seed {seed} row {row_index} has an unexpected C1 source rule")
    raw = row.get("raw")
    targets = row.get("targets")
    if not isinstance(raw, Mapping) or not isinstance(targets, Mapping):
        raise ValueError(f"seed {seed} row {row_index} lacks raw/targets objects")
    if raw.get("schema") != RAW_SCHEMA:
        raise ValueError(f"seed {seed} row {row_index} has a stale raw schema")
    if raw.get("source_manifest_sha256") != "9ec832c71b29ad84e37856db1f5d237f07d177c62cc93fbb66de06d808184a0a":
        raise ValueError(f"seed {seed} row {row_index} source manifest mismatch")
    if raw.get("lambda_bits_per_j") != OLD_LAMBDA_HEX:
        raise ValueError(f"seed {seed} row {row_index} does not carry the frozen old lambda")

    focal_user = raw.get("focal_user")
    if type(focal_user) is not int or focal_user < 0:
        raise ValueError(f"seed {seed} row {row_index} has an invalid focal user")
    candidate_rates = raw.get("candidate_rates_bps")
    reference_rates = raw.get("reference_rates_bps")
    candidate_joint = raw.get("candidate_joint_actions")
    reference_joint = raw.get("reference_joint_actions")
    if not all(isinstance(vector, list) for vector in (candidate_rates, reference_rates, candidate_joint, reference_joint)):
        raise ValueError(f"seed {seed} row {row_index} has invalid source vectors")
    if not (len(candidate_rates) == len(reference_rates) == len(candidate_joint) == len(reference_joint)):
        raise ValueError(f"seed {seed} row {row_index} vectors disagree about user count")
    if focal_user >= len(candidate_rates):
        raise ValueError(f"seed {seed} row {row_index} focal user is out of range")
    changed = [index for index, (candidate, reference) in enumerate(zip(candidate_joint, reference_joint)) if candidate != reference]
    if changed != [focal_user]:
        raise ValueError(f"seed {seed} row {row_index} is not a unilateral C1 comparison")
    if raw.get("candidate_action") != candidate_joint[focal_user] or raw.get("reference_action") != reference_joint[focal_user]:
        raise ValueError(f"seed {seed} row {row_index} scalar actions disagree with joint actions")

    candidate_rate = _hex_float(candidate_rates[focal_user], field="candidate focal rate")
    reference_rate = _hex_float(reference_rates[focal_user], field="reference focal rate")
    candidate_power = _hex_float(raw["candidate_system_power_w"], field="candidate system power")
    reference_power = _hex_float(raw["reference_system_power_w"], field="reference system power")
    interval = _hex_float(raw["interval_s"], field="interval")
    persisted_old = _hex_float(targets[OLD_TARGET_KEY], field="persisted old C1 target")
    reconstructed_old = c1_zeta1(
        candidate_rate_bps=candidate_rate,
        reference_rate_bps=reference_rate,
        candidate_system_power_w=candidate_power,
        reference_system_power_w=reference_power,
        interval_s=interval,
        lambda_bits_per_j=OLD_LAMBDA_BITS_PER_J,
    )
    repriced_new = c1_zeta1(
        candidate_rate_bps=candidate_rate,
        reference_rate_bps=reference_rate,
        candidate_system_power_w=candidate_power,
        reference_system_power_w=reference_power,
        interval_s=interval,
        lambda_bits_per_j=NEW_LAMBDA_BITS_PER_J,
    )
    old_error = reconstructed_old - persisted_old
    if not all(math.isfinite(value) for value in (reconstructed_old, repriced_new, old_error)):
        raise ValueError(f"seed {seed} row {row_index} produced a non-finite target")
    old_sign = _sign(persisted_old)
    new_sign = _sign(repriced_new)
    return {
        "source_seed": seed,
        "split": SOURCE_SEED_SPLIT[seed],
        "row_index": row_index,
        "anchor_sha256": raw["anchor_sha256"],
        "focal_user": focal_user,
        "reference_action": raw["reference_action"],
        "candidate_action": raw["candidate_action"],
        "candidate_rate_bps_hex": candidate_rates[focal_user],
        "reference_rate_bps_hex": reference_rates[focal_user],
        "candidate_system_power_w_hex": raw["candidate_system_power_w"],
        "reference_system_power_w_hex": raw["reference_system_power_w"],
        "interval_s_hex": raw["interval_s"],
        "persisted_old_target_hex": _hex(persisted_old),
        "reconstructed_old_target_hex": _hex(reconstructed_old),
        "old_reconstruction_error_bits_hex": _hex(old_error),
        "repriced_new_target_hex": _hex(repriced_new),
        "new_minus_old_bits_hex": _hex(repriced_new - persisted_old),
        "old_sign": old_sign,
        "new_sign": new_sign,
        "sign_flip": old_sign != new_sign,
    }


def _direction_counts(records: list[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "sign_flips": sum(bool(record["sign_flip"]) for record in records),
        "old_positive_new_negative": sum(record["old_sign"] == 1 and record["new_sign"] == -1 for record in records),
        "old_negative_new_positive": sum(record["old_sign"] == -1 and record["new_sign"] == 1 for record in records),
        "old_zero_new_nonzero": sum(record["old_sign"] == 0 and record["new_sign"] != 0 for record in records),
        "old_nonzero_new_zero": sum(record["old_sign"] != 0 and record["new_sign"] == 0 for record in records),
    }


def _group_summary(records: list[Mapping[str, Any]]) -> dict[str, Any]:
    old = [_hex_float(record["persisted_old_target_hex"], field="old target") for record in records]
    new = [_hex_float(record["repriced_new_target_hex"], field="new target") for record in records]
    errors = [abs(_hex_float(record["old_reconstruction_error_bits_hex"], field="old error")) for record in records]
    delta = [_hex_float(record["new_minus_old_bits_hex"], field="new-minus-old") for record in records]
    return {
        "old_target": _stats(old),
        "new_target": _stats(new),
        "new_minus_old": _stats(delta),
        "absolute_old_reconstruction_error_bits": _stats(errors),
        "directions": _direction_counts(records),
    }


def build_receipt() -> dict[str, Any]:
    """Read the frozen source corpus and return a JSON-serializable receipt."""

    receipt = _load_source_receipt()
    records: list[Mapping[str, Any]] = []
    coverage_by_seed = {
        int(item["source_seed"]): item for item in receipt["coverage_by_seed"]
    }
    files: list[dict[str, Any]] = []
    for seed in SOURCE_SEEDS:
        if SOURCE_SEED_SPLIT[seed] not in {"train", "validation"}:
            raise ValueError(f"unexpected split for seed {seed}")
        payload = _load_source(seed, receipt)
        route_counts: dict[str, int] = {}
        for row_index, row in enumerate(payload["rows"]):
            route = row.get("admitted_route")
            route_counts[route] = route_counts.get(route, 0) + 1
            if route == "C1":
                records.append(_validate_admitted_c1_row(row, seed=seed, row_index=row_index))
        expected_c1_count = coverage_by_seed[seed]["c1_rows"]
        if route_counts.get("C1", 0) != expected_c1_count:
            raise ValueError(f"seed {seed} C1 row count disagrees with source receipt")
        files.append(
            {
                "seed": seed,
                "split": SOURCE_SEED_SPLIT[seed],
                "path": str(_source_path(seed).relative_to(REPO_ROOT)),
                "byte_sha256": sha256_file(_source_path(seed)),
                "dataset_sha256": payload["dataset_sha256"],
                "total_rows": len(payload["rows"]),
                "admitted_route_counts": route_counts,
                "admitted_c1_rows_used": route_counts.get("C1", 0),
                "non_c1_rows_excluded": len(payload["rows"]) - route_counts.get("C1", 0),
            }
        )

    # Sort by source seed and original row position, which is already the
    # deterministic traversal order above.  This assertion makes accidental
    # inclusion of a C3 row impossible to overlook in the receipt.
    if len(records) != sum(file["admitted_c1_rows_used"] for file in files):
        raise ValueError("record count does not equal admitted C1 count")
    if any(record["split"] not in {"train", "validation"} for record in records):
        raise ValueError("a record escaped the declared source split")

    by_split = {
        split: _group_summary([record for record in records if record["split"] == split])
        for split in ("train", "validation")
    }
    by_seed = {
        str(seed): _group_summary([record for record in records if record["source_seed"] == seed])
        for seed in SOURCE_SEEDS
    }
    old_errors = [abs(_hex_float(record["old_reconstruction_error_bits_hex"], field="old error")) for record in records]
    checks = {
        "source_manifest_sha256_matches_frozen": True,
        "all_seven_explicit_source_files_authenticated": True,
        "old_lambda_payload_is_uniform": True,
        "old_lambda_hex": OLD_LAMBDA_HEX,
        "new_lambda_is_fixed_before_repricing": NEW_LAMBDA_HEX,
        "only_admitted_route_C1_rows_used": True,
        "c3_rows_used": 0,
        "all_reconstructed_values_finite": True,
        "all_new_values_finite": True,
        "old_target_max_abs_error_bits": _hex(max(old_errors)),
        "old_target_error_tolerance_bits": OLD_ERROR_TOLERANCE_BITS,
        "old_target_reconstruction_within_tolerance": max(old_errors) <= OLD_ERROR_TOLERANCE_BITS,
        "test_split_opened": False,
        "simulator_or_training_invoked": False,
    }
    if not checks["old_target_reconstruction_within_tolerance"]:
        raise ValueError("old C1 target reconstruction exceeds frozen tolerance")

    return {
        "schema": "multi-catfish-mcrl-v03-q1-c1-lambda-repricing-receipt-v1",
        "status": "PASS",
        "claim_ceiling": "DEVELOPMENT_SOURCE_REPRICING_ONLY_NO_LEARNER_OR_EE_EFFICACY",
        "scope": {
            "route": "C1",
            "target": OLD_TARGET_KEY,
            "formula": "interval_s * ((candidate_focal_rate - reference_focal_rate) - lambda_bits_per_j * (candidate_system_power - reference_system_power))",
            "source_root": str(SOURCE_DIR.relative_to(REPO_ROOT)),
            "source_manifest_sha256": receipt["source_manifest_sha256"],
            "source_seeds": list(SOURCE_SEEDS),
            "source_seed_split": {str(seed): SOURCE_SEED_SPLIT[seed] for seed in SOURCE_SEEDS},
            "test_source_opened": False,
            "simulator_or_training_run": False,
        },
        "constants": {
            "old_lambda_bits_per_j": OLD_LAMBDA_BITS_PER_J,
            "old_lambda_hex": OLD_LAMBDA_HEX,
            "new_lambda_bits_per_j": NEW_LAMBDA_BITS_PER_J,
            "new_lambda_hex": NEW_LAMBDA_HEX,
            "old_lambda_delta_bits_per_j": NEW_LAMBDA_BITS_PER_J - OLD_LAMBDA_BITS_PER_J,
        },
        "counts": {
            "source_files": len(files),
            "source_rows_total": sum(file["total_rows"] for file in files),
            "admitted_c1_rows": len(records),
            "excluded_non_c1_rows": sum(file["non_c1_rows_excluded"] for file in files),
            "excluded_c3_rows": sum(file["admitted_route_counts"].get("C3", 0) for file in files),
            "train_rows": sum(record["split"] == "train" for record in records),
            "validation_rows": sum(record["split"] == "validation" for record in records),
        },
        "files": files,
        "summary": _group_summary(records),
        "by_split": by_split,
        "by_seed": by_seed,
        "checks": checks,
        "records": records,
    }


def _decimal_from_hex(value: str) -> str:
    return f"{_hex_float(value, field='display value'):.12g}"


def _fmt_stats(stats: Mapping[str, Any]) -> str:
    return (
        f"n={stats['count']}; +={stats['positive']} ({stats['positive_fraction']:.3%}); "
        f"-={stats['negative']} ({stats['negative_fraction']:.3%}); 0={stats['zero']}; "
        f"mean={_decimal_from_hex(stats['mean_hex'])}; median={_decimal_from_hex(stats['median_hex'])}; "
        f"min={_decimal_from_hex(stats['min_hex'])}; max={_decimal_from_hex(stats['max_hex'])}"
    )


def render_audit(receipt: Mapping[str, Any], *, script_hash: str) -> str:
    summary = receipt["summary"]
    directions = summary["directions"]
    lines = [
        "# Q1/C1 lambda repricing source audit",
        "",
        "Status: **PASS (offline source reconstruction only)**  ",
        "Claim ceiling: **no learner result, no episode result, and no EE efficacy claim**",
        "",
        "## Scope",
        "",
        "This audit reads only the seven explicitly named opening source files in the V0.3 E1 action-shared supplement. It uses rows whose top-level `admitted_route` is exactly `C1`; the C3 rows in the same files and all audit-only C1 route metadata on C3 rows are excluded. No simulator, TEST source, learner, or training process was invoked.",
        "",
        "The source split is 2026092001--2026092004 = TRAIN and 2026092005--2026092007 = internal validation. The latter is an internal source split, not a TEST outcome.",
        "",
        "## Formula and frozen constants",
        "",
        r"For every admitted C1 row, the reconstructed target is \(\zeta_1=\Delta t[(R_u^C-R_u^M)-\lambda(P_C^N-P_M^N)]\). The raw focal rates, full network powers, interval, action vectors, mask, and state are not changed.",
        "",
        f"- Old payload multiplier: `{receipt['constants']['old_lambda_hex']}` = {receipt['constants']['old_lambda_bits_per_j']:.16g} bit/J.",
        f"- Fixed repricing multiplier: `{receipt['constants']['new_lambda_hex']}` = {receipt['constants']['new_lambda_bits_per_j']:.16g} bit/J.",
        f"- Multiplier increase: {receipt['constants']['old_lambda_delta_bits_per_j']:.16g} bit/J.",
        "- The new multiplier was fixed before this offline output was inspected; no sign, threshold, or source row was tuned after repricing.",
        "",
        "## Source authentication and row counts",
        "",
        f"- Frozen source-manifest SHA-256: `{receipt['scope']['source_manifest_sha256']}`.",
        f"- Authenticated source files: {receipt['counts']['source_files']}.",
        f"- Total rows read: {receipt['counts']['source_rows_total']}.",
        f"- Admitted C1 rows used: **{receipt['counts']['admitted_c1_rows']}** ({receipt['counts']['train_rows']} TRAIN + {receipt['counts']['validation_rows']} internal validation).",
        f"- Non-C1 rows excluded: {receipt['counts']['excluded_non_c1_rows']} (including {receipt['counts']['excluded_c3_rows']} admitted C3 rows).",
        "",
        "| Seed | Split | Total rows | Admitted C1 | Excluded C3 | File SHA-256 |",
        "|---:|:---|---:|---:|---:|:---|",
    ]
    for file in receipt["files"]:
        lines.append(
            f"| {file['seed']} | {file['split']} | {file['total_rows']} | {file['admitted_c1_rows_used']} | {file['admitted_route_counts'].get('C3', 0)} | `{file['byte_sha256']}` |"
        )
    lines.extend(
        [
            "",
            "## Old-target reconstruction",
            "",
            f"All {receipt['counts']['admitted_c1_rows']} persisted payload targets were recomputed from raw focal rates, raw candidate/reference system power, the raw interval, and the payload old multiplier. The maximum absolute error is `{receipt['checks']['old_target_max_abs_error_bits']}` bit; the frozen acceptance tolerance is `{receipt['checks']['old_target_error_tolerance_bits']}` bit. **The reconstruction passes.**",
            "",
            f"Absolute-error summary: {_fmt_stats(summary['absolute_old_reconstruction_error_bits'])}.",
            "",
            "## Repriced target statistics",
            "",
            f"Old persisted C1 target: {_fmt_stats(summary['old_target'])}.",
            "",
            f"New C1 target at the fixed multiplier: {_fmt_stats(summary['new_target'])}.",
            "",
            f"New minus old target: {_fmt_stats(summary['new_minus_old'])}.",
            "",
            "Values above are target-label diagnostics in bits. They are not policy rollouts and do not establish that C1 improves canonical EE.",
            "",
            "## Sign changes",
            "",
            f"Across all admitted C1 rows, {directions['sign_flips']} / {receipt['counts']['admitted_c1_rows']} ({directions['sign_flips'] / receipt['counts']['admitted_c1_rows']:.3%}) changed sign when moving from the persisted old target to the fixed repriced target:",
            "",
            f"- old positive → new negative: {directions['old_positive_new_negative']}",
            f"- old negative → new positive: {directions['old_negative_new_positive']}",
            f"- old zero → new nonzero: {directions['old_zero_new_nonzero']}",
            f"- old nonzero → new zero: {directions['old_nonzero_new_zero']}",
            "",
            "## Split and seed summaries",
            "",
            "The standard deviation is population standard deviation; p05/p95 use nearest-rank quantiles. `+` and `-` count strict target signs.",
            "",
            "| Group | n | Old + / - | New + / - | Sign flips | Old mean (bit) | New mean (bit) |",
            "|:---|---:|---:|---:|---:|---:|---:|",
        ]
    )

    def row_for_group(name: str, group: Mapping[str, Any]) -> str:
        old = group["old_target"]
        new = group["new_target"]
        direction = group["directions"]
        return (
            f"| {name} | {old['count']} | {old['positive']} / {old['negative']} | "
            f"{new['positive']} / {new['negative']} | {direction['sign_flips']} | "
            f"{_decimal_from_hex(old['mean_hex'])} | {_decimal_from_hex(new['mean_hex'])} |"
        )

    for split in ("train", "validation"):
        lines.append(row_for_group(split, receipt["by_split"][split]))
    for seed in SOURCE_SEEDS:
        lines.append(row_for_group(str(seed), receipt["by_seed"][str(seed)]))
    lines.extend(
        [
            "",
            "## Interpretation and next gate",
            "",
            "Verified fact: the existing C1 source rows can be deterministically re-labeled at the fixed new multiplier, and the persisted old labels reconstruct within tolerance.",
            "",
            "Inference: changing the multiplier changes Q1's labels and therefore requires a matched Q1 retraining before using Q1 to rebuild Q1+Q2 references. This audit does not decide whether that retrained head improves EE.",
            "",
            "Proposal: pair this C1 repricing with the separately specified Q2 offline repricing, then retrain Q1 and Q2 together under one frozen execution receipt. Do not reprice only Q1 and do not use these source-label signs as an efficacy endpoint.",
            "",
            f"Tool script SHA-256: `{script_hash}`.",
            f"The complete per-row evidence is in `receipt.json`; the runnable implementation is `reprice_c1.py` and its tests are in `test_reprice_c1.py`.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(output_dir: Path = OUTPUT_DIR) -> dict[str, Any]:
    """Build and write the receipt, audit, and a non-circular file manifest."""

    output_dir.mkdir(parents=True, exist_ok=True)
    receipt = build_receipt()
    receipt["tool"] = {
        "script_path": str(Path(__file__).resolve().relative_to(REPO_ROOT)),
        "script_sha256": sha256_file(Path(__file__).resolve()),
        "test_path": str((output_dir / "test_reprice_c1.py").relative_to(REPO_ROOT)),
    }
    receipt_path = output_dir / "receipt.json"
    audit_path = output_dir / "Q1-REPRICING-AUDIT.md"
    manifest_path = output_dir / "MANIFEST.sha256"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    audit_path.write_text(render_audit(receipt, script_hash=receipt["tool"]["script_sha256"]) + "\n", encoding="utf-8")
    manifest_entries = []
    for path in (Path(__file__).resolve(), output_dir / "test_reprice_c1.py", receipt_path, audit_path):
        if not path.is_file():
            raise FileNotFoundError(path)
        manifest_entries.append(f"{sha256_file(path)}  {path.name}")
    manifest_path.write_text("\n".join(sorted(manifest_entries)) + "\n", encoding="utf-8")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    receipt = write_outputs(args.output_dir.resolve())
    print(json.dumps({"status": receipt["status"], "admitted_c1_rows": receipt["counts"]["admitted_c1_rows"], "sign_flips": receipt["summary"]["directions"]["sign_flips"]}, sort_keys=True))


if __name__ == "__main__":
    main()
