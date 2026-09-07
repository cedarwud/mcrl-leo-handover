#!/usr/bin/env python3
"""Independently replay and verify a C1 Source Gate A result receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import run_c1_source_gate as gate
import verify_c1_corrective_replay_addendum as correction


SCHEMA = "smc-er-c1-source-gate-a-verification-v2"
SEED_CORRECTION_SCHEMA = (
    "smc-er-c1-source-gate-a-seed-provenance-correction-v1"
)
SEED_CORRECTION_STATUS = "CORRECTED_BEFORE_DOWNSTREAM_EFFICACY_SEED_REVEAL"
SEED_CORRECTION_CLAIM = (
    "SOURCE_SEED_PROVENANCE_ONLY_NOT_SOURCE_QUALITY_NOT_LEARNING_NOT_EE_EFFICACY"
)


def _same(left: float, right: float) -> bool:
    return math.isclose(float(left), float(right), rel_tol=1e-12, abs_tol=1e-9)


def _sha_payload(value: Any) -> str:
    return hashlib.sha256(gate._canonical_json(value)).hexdigest()


def _bound_json(
    path: Path | None,
    *,
    expected_sha256: str | None,
    label: str,
    failures: list[str],
) -> Mapping[str, Any]:
    if path is None or not path.is_file():
        failures.append(f"{label}_missing")
        return {}
    if expected_sha256 is None or gate.sha256_file(path) != expected_sha256:
        failures.append(f"{label}_hash_mismatch")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        failures.append(f"{label}_unreadable")
        return {}
    if not isinstance(payload, Mapping):
        failures.append(f"{label}_malformed")
        return {}
    return payload


def _validate_seed_provenance_correction(
    path: Path | None,
    *,
    source_gate_path: Path | None,
    seed_manifest_path: Path,
    seed_manifest: Mapping[str, Any],
    manifest_seeds: list[int],
    checkpoint_sha256: str,
    ephemeris: Mapping[str, Any],
    failures: list[str],
) -> tuple[str | None, Mapping[str, Any]]:
    """Bind the transparent correction for the historical seed-derivation text."""

    if path is None:
        failures.append("source_seed_provenance_correction_missing")
        return None, {}
    correction_path = Path(path).expanduser().resolve()
    if not correction_path.is_file():
        failures.append("source_seed_provenance_correction_missing")
        return None, {}
    correction_sha256 = gate.sha256_file(correction_path)
    payload = _bound_json(
        correction_path,
        expected_sha256=correction_sha256,
        label="source_seed_provenance_correction",
        failures=failures,
    )
    if (
        payload.get("schema") != SEED_CORRECTION_SCHEMA
        or payload.get("status") != SEED_CORRECTION_STATUS
        or payload.get("claim_ceiling") != SEED_CORRECTION_CLAIM
    ):
        failures.append("source_seed_provenance_correction_schema_mismatch")

    authority = payload.get("authority")
    if not isinstance(authority, Mapping):
        failures.append("source_seed_provenance_correction_authority_missing")
        return correction_sha256, payload
    corrected_spec = Path(str(authority.get("source_gate_spec_path", ""))).expanduser()
    corrected_manifest = Path(
        str(authority.get("source_seed_manifest_path", ""))
    ).expanduser()
    corrected_result = Path(
        str(authority.get("canonical_source_gate_result_path", ""))
    ).expanduser()
    if (
        not corrected_spec.is_file()
        or corrected_spec.resolve() != gate.SPEC.resolve()
        or authority.get("source_gate_spec_sha256") != gate.sha256_file(gate.SPEC)
        or corrected_manifest.resolve() != seed_manifest_path.resolve()
        or not corrected_manifest.is_file()
        or authority.get("source_seed_manifest_sha256")
        != gate.sha256_file(seed_manifest_path)
        or authority.get("checkpoint_sha256") != checkpoint_sha256
        or source_gate_path is None
        or corrected_result.resolve()
        != Path(source_gate_path).expanduser().resolve()
        or not corrected_result.is_file()
        or authority.get("canonical_source_gate_result_sha256")
        != gate.sha256_file(corrected_result)
        or authority.get("canonical_tle_file_count")
        != ephemeris.get("archive", {}).get("file_count")
        or authority.get("canonical_tle_file_set_sha256")
        != ephemeris.get("file_set_sha256")
    ):
        failures.append("source_seed_provenance_correction_authority_mismatch")

    statement = payload.get("incorrect_historical_statement")
    spec_digest = gate.sha256_file(gate.SPEC)
    expected_literal = [
        int.from_bytes(bytes.fromhex(spec_digest)[offset : offset + 4], "big")
        for offset in range(0, 20, 4)
    ]
    if (
        not isinstance(statement, Mapping)
        or statement.get("declared_derivation") != seed_manifest.get("derivation")
        or statement.get("declared_derivation_is_true_for_all_five_seeds")
        is not False
        or statement.get("expected_if_declaration_were_literal") != expected_literal
        or statement.get("frozen_actual_seeds") != manifest_seeds
        or statement.get("matching_prefix_seed_count") != 3
        or manifest_seeds[:3] != expected_literal[:3]
        or manifest_seeds[3:] == expected_literal[3:]
    ):
        failures.append("source_seed_provenance_correction_statement_mismatch")

    reconstruction = payload.get("transparent_reconstruction")
    offsets = [0, 8, 16, 25, 33]
    windows = [spec_digest[offset : offset + 8] for offset in offsets]
    reconstructed = [int(value, 16) for value in windows]
    if (
        not isinstance(reconstruction, Mapping)
        or reconstruction.get("spec_sha256_hex_character_offsets") != offsets
        or reconstruction.get("eight_hex_character_windows") != windows
        or reconstruction.get("reconstructed_uint32_big_endian_values")
        != manifest_seeds
        or reconstructed != manifest_seeds
        or reconstruction.get("historical_generator_or_command_record_available")
        is not False
        or not isinstance(reconstruction.get("historical_origin_claim"), str)
        or not reconstruction.get("historical_origin_claim")
    ):
        failures.append("source_seed_provenance_correction_reconstruction_mismatch")

    attestations = payload.get("attestations")
    required_attestations = (
        "source_result_hash_binds_the_unchanged_seed_manifest",
        "no_seed_value_changed_by_this_correction",
        "no_new_seed_sample_was_drawn",
        "no_source_gate_outcome_was_changed",
        "no_outcome_conditioned_selection_was_performed_by_this_correction",
        "correction_precedes_downstream_efficacy_seed_reveal",
        "campaign_ledger_absent_when_correction_was_written",
        "execution_ledger_absent_when_correction_was_written",
        "do_not_repeat_the_incorrect_five_consecutive_words_claim",
    )
    if (
        not isinstance(attestations, Mapping)
        or any(attestations.get(field) is not True for field in required_attestations)
    ):
        failures.append("source_seed_provenance_correction_attestation_mismatch")
    return correction_sha256, payload


def verify_payload(
    payload: Mapping[str, Any],
    *,
    source_gate_path: Path | None = None,
    corrective_addendum: Path | None = None,
    corrective_replay_verification: Path | None = None,
    source_seed_provenance_correction: Path | None = None,
    replay_raw_rows: bool = True,
) -> dict[str, Any]:
    """Verify authority, ordered seeds/rows, metrics, and deterministic raw replay."""

    failures: list[str] = []
    if payload.get("schema") != gate.RESULT_SCHEMA:
        failures.append("result_schema_mismatch")
    if payload.get("status") != "PASS" or payload.get("decision") != "PASS_TO_C1_CONSUMER_GATE":
        failures.append("result_status_or_decision_mismatch")
    if (
        payload.get("claim_ceiling")
        != "SOURCE_QUALITY_ONLY_NOT_LEARNING_NOT_MAIN_ROUTING_NOT_EE_EFFICACY"
    ):
        failures.append("claim_ceiling_mismatch")

    authority = payload.get("authority")
    if not isinstance(authority, Mapping):
        failures.append("authority_missing")
        authority = {}
    bindings = {
        "method_sha256": gate.sha256_file(gate.METHOD),
        "spec_sha256": gate.sha256_file(gate.SPEC),
        "runner_sha256": gate.sha256_file(gate.HERE / "run_c1_source_gate.py"),
    }
    for field, expected in bindings.items():
        if authority.get(field) != expected:
            failures.append(f"{field}_mismatch")

    checkpoint_path = Path(str(authority.get("checkpoint_path", ""))).expanduser()
    seed_path = Path(str(authority.get("seed_manifest_path", ""))).expanduser()
    for label, path, digest_field in (
        ("checkpoint", checkpoint_path, "checkpoint_sha256"),
        ("seed_manifest", seed_path, "seed_manifest_sha256"),
    ):
        if not path.is_file():
            failures.append(f"{label}_missing")
        elif gate.sha256_file(path) != authority.get(digest_field):
            failures.append(f"{label}_hash_mismatch")

    manifest_seeds: list[int] = []
    seed_manifest: Mapping[str, Any] = {}
    if seed_path.is_file() and gate.sha256_file(seed_path) == authority.get("seed_manifest_sha256"):
        seed_manifest = _bound_json(
            seed_path,
            expected_sha256=str(authority.get("seed_manifest_sha256")),
            label="seed_manifest",
            failures=failures,
        )
        values = seed_manifest.get("seeds")
        if (
            seed_manifest.get("schema") != gate.SEED_SCHEMA
            or seed_manifest.get("status") != "frozen"
            or seed_manifest.get("spec_sha256") != bindings["spec_sha256"]
            or seed_manifest.get("checkpoint_sha256") != authority.get("checkpoint_sha256")
            or not isinstance(values, list)
            or len(values) != gate.EXPECTED_SEEDS
            or any(type(value) is not int or value < 0 for value in values)
            or len(set(values)) != gate.EXPECTED_SEEDS
        ):
            failures.append("seed_manifest_authority_mismatch")
        else:
            manifest_seeds = list(map(int, values))

    prereg_path = Path(str(authority.get("prereg_path", ""))).expanduser()
    if (
        not prereg_path.is_file()
        or prereg_path.resolve() != Path(gate.CANONICAL_PREREG).resolve()
        or gate.sha256_file(prereg_path) != gate.CANONICAL_PREREG_BYTE_SHA256
        or authority.get("prereg_sha256") != gate.CANONICAL_PREREG_BYTE_SHA256
    ):
        failures.append("prereg_authority_mismatch")
    tle_root = Path(str(authority.get("tle_root_path", ""))).expanduser()
    ephemeris: Mapping[str, Any] = {}
    if not tle_root.is_dir() or not prereg_path.is_file():
        failures.append("tle_authority_missing")
    else:
        try:
            ephemeris = gate.assert_ephemeris_matches_record(
                gate.read_prereg(prereg_path), archive=gate.TleArchive(tle_root)
            )
        except Exception:
            failures.append("tle_authority_replay_failed")
        else:
            if (
                authority.get("tle_file_set_sha256")
                != ephemeris.get("file_set_sha256")
                or authority.get("tle_file_count")
                != ephemeris.get("archive", {}).get("file_count")
            ):
                failures.append("tle_authority_mismatch")

    seed_correction_sha256, seed_correction_payload = (
        _validate_seed_provenance_correction(
            source_seed_provenance_correction,
            source_gate_path=source_gate_path,
            seed_manifest_path=seed_path,
            seed_manifest=seed_manifest,
            manifest_seeds=manifest_seeds,
            checkpoint_sha256=str(authority.get("checkpoint_sha256", "")),
            ephemeris=ephemeris,
            failures=failures,
        )
    )

    correction_receipt: Mapping[str, Any] = {}
    reproduced_correction: Mapping[str, Any] = {}
    correction_addendum_sha256: str | None = None
    correction_verification_sha256: str | None = None
    if corrective_addendum is None or corrective_replay_verification is None:
        failures.append("corrective_replay_authority_missing")
    else:
        corrective_addendum = Path(corrective_addendum).expanduser().resolve()
        corrective_replay_verification = (
            Path(corrective_replay_verification).expanduser().resolve()
        )
        if not corrective_addendum.is_file():
            failures.append("corrective_replay_addendum_missing")
        else:
            correction_addendum_sha256 = gate.sha256_file(corrective_addendum)
        if not corrective_replay_verification.is_file():
            failures.append("corrective_replay_verification_missing")
        else:
            correction_verification_sha256 = gate.sha256_file(
                corrective_replay_verification
            )
            correction_receipt = _bound_json(
                corrective_replay_verification,
                expected_sha256=correction_verification_sha256,
                label="corrective_replay_verification",
                failures=failures,
            )
        if corrective_addendum.is_file():
            reproduced_correction = correction.verify_addendum(corrective_addendum)
        if (
            correction_receipt.get("status") != "PASS"
            or dict(correction_receipt) != dict(reproduced_correction)
        ):
            failures.append("corrective_replay_verification_mismatch")
        if source_gate_path is None or not Path(source_gate_path).is_file():
            failures.append("source_gate_result_path_missing")
        elif (
            correction_receipt.get("canonical_source_gate_result_sha256")
            != gate.sha256_file(Path(source_gate_path).expanduser().resolve())
        ):
            failures.append("corrective_replay_source_result_mismatch")

    paired = payload.get("paired_rows")
    seed_rows = payload.get("seed_rows")
    if not isinstance(paired, list) or not isinstance(seed_rows, list):
        failures.append("rows_missing")
        paired = []
        seed_rows = []

    expected_identities = [
        (seed, step)
        for seed in manifest_seeds
        for step in range(gate.EXPECTED_STEPS)
    ]
    actual_identities: list[tuple[int, int]] = []
    by_seed: dict[int, list[Mapping[str, Any]]] = {}
    identities: set[tuple[int, int]] = set()
    for row in paired:
        if not isinstance(row, Mapping):
            failures.append("malformed_paired_row")
            continue
        seed = row.get("seed")
        step = row.get("step")
        if type(seed) is not int or type(step) is not int:
            failures.append("noninteger_seed_or_step")
            continue
        identity = (int(seed), int(step))
        actual_identities.append(identity)
        if identity in identities:
            failures.append("duplicate_seed_step")
        identities.add(identity)
        by_seed.setdefault(int(seed), []).append(row)
        local = row.get("local")
        control = row.get("control")
        if not isinstance(local, Mapping) or not isinstance(control, Mapping):
            failures.append("paired_endpoint_missing")
            continue
        expected_delta = float(local["ee_bits_per_j"]) - float(
            control["ee_bits_per_j"]
        )
        if not _same(expected_delta, float(row.get("delta_ee_bits_per_j", math.nan))):
            failures.append("paired_delta_mismatch")

    if expected_identities and actual_identities != expected_identities:
        failures.append("manifest_to_paired_rows_order_mismatch")
    if len(by_seed) != gate.EXPECTED_SEEDS or any(
        len(rows) != gate.EXPECTED_STEPS for rows in by_seed.values()
    ):
        failures.append("seed_step_denominator_mismatch")

    recorded_seed_order = [
        int(row["seed"])
        for row in seed_rows
        if isinstance(row, Mapping) and type(row.get("seed")) is int
    ]
    if manifest_seeds and recorded_seed_order != manifest_seeds:
        failures.append("manifest_to_seed_rows_order_mismatch")
    if len(recorded_seed_order) != len(seed_rows) or len(set(recorded_seed_order)) != len(recorded_seed_order):
        failures.append("seed_rows_duplicate_or_malformed")

    recomputed_seed_rows: list[dict[str, Any]] = []
    for seed in manifest_seeds:
        rows = by_seed.get(seed, [])
        ordered = sorted(rows, key=lambda row: int(row["step"]))
        if len(ordered) != gate.EXPECTED_STEPS:
            continue
        local_metrics = gate._metrics([row["local"] for row in ordered])
        control_metrics = gate._metrics([row["control"] for row in ordered])
        recomputed_seed_rows.append(
            {
                "seed": seed,
                "delta_ee_bits_per_j": (
                    local_metrics.ee_bits_per_j - control_metrics.ee_bits_per_j
                ),
                "local_served_fraction": local_metrics.served_fraction,
                "control_served_fraction": control_metrics.served_fraction,
            }
        )
    recorded_by_seed = {
        int(row["seed"]): row
        for row in seed_rows
        if isinstance(row, Mapping) and type(row.get("seed")) is int
    }
    for recomputed in recomputed_seed_rows:
        recorded = recorded_by_seed.get(int(recomputed["seed"]))
        if recorded is None:
            failures.append("recorded_seed_row_missing")
            continue
        for field in (
            "delta_ee_bits_per_j",
            "local_served_fraction",
            "control_served_fraction",
        ):
            if not _same(float(recomputed[field]), float(recorded.get(field, math.nan))):
                failures.append(f"seed_{field}_mismatch")

    if len(recomputed_seed_rows) == gate.EXPECTED_SEEDS:
        decision = gate.decide_gate(recomputed_seed_rows, guard_failures=())
        recorded_result = payload.get("result")
        if not isinstance(recorded_result, Mapping):
            failures.append("recorded_result_missing")
        else:
            for field in ("status", "decision", "positive_seed_count"):
                if decision.get(field) != recorded_result.get(field):
                    failures.append(f"decision_{field}_mismatch")
            for field in (
                "mean_seed_delta_ee_bits_per_j",
                "served_fraction_delta",
            ):
                if not _same(
                    float(decision[field]), float(recorded_result.get(field, math.nan))
                ):
                    failures.append(f"decision_{field}_mismatch")
            if recorded_result.get("guard_failures") != []:
                failures.append("recorded_guard_failures_not_empty")
    else:
        decision = {"status": "FAIL", "decision": "UNVERIFIABLE"}

    raw_replay_performed = False
    raw_replay_equal = False
    replayed_seed_rows: list[dict[str, Any]] = []
    replayed_paired_rows: list[dict[str, Any]] = []
    if replay_raw_rows and not failures and manifest_seeds:
        raw_replay_performed = True
        checkpoint_sha256 = str(authority.get("checkpoint_sha256"))
        checkpoint_payload = gate.read_checkpoint(checkpoint_path, map_location="cpu")
        archive = gate.TleArchive(tle_root.resolve())
        for seed in manifest_seeds:
            replayed_seed, replayed_rows = gate.run_seed(
                archive=archive,
                checkpoint_path=checkpoint_path,
                checkpoint_payload=checkpoint_payload,
                checkpoint_sha256=checkpoint_sha256,
                seed=seed,
            )
            replayed_seed_rows.append(replayed_seed)
            replayed_paired_rows.extend(replayed_rows)
        raw_replay_equal = (
            gate._canonical_json(replayed_seed_rows) == gate._canonical_json(seed_rows)
            and gate._canonical_json(replayed_paired_rows) == gate._canonical_json(paired)
        )
        if not raw_replay_equal:
            failures.append("deterministic_raw_replay_mismatch")
    elif replay_raw_rows:
        failures.append("deterministic_raw_replay_not_attempted")

    unique = list(dict.fromkeys(failures))
    return {
        "schema": SCHEMA,
        "status": "PASS" if not unique else "FAIL",
        "failures": unique,
        "recomputed_decision": decision,
        "paired_rows": len(paired),
        "seed_rows": len(recomputed_seed_rows),
        "manifest_seed_count": len(manifest_seeds),
        "manifest_to_paired_rows_order_equal": actual_identities == expected_identities,
        "manifest_to_seed_rows_order_equal": recorded_seed_order == manifest_seeds,
        "paired_rows_sha256": _sha_payload(paired),
        "seed_rows_sha256": _sha_payload(seed_rows),
        "deterministic_raw_replay_performed": raw_replay_performed,
        "deterministic_raw_replay_equal": raw_replay_equal,
        "replayed_paired_rows_sha256": (
            _sha_payload(replayed_paired_rows) if raw_replay_performed else None
        ),
        "replayed_seed_rows_sha256": (
            _sha_payload(replayed_seed_rows) if raw_replay_performed else None
        ),
        "corrective_replay_addendum_path": (
            str(Path(corrective_addendum).expanduser().resolve())
            if corrective_addendum is not None
            else None
        ),
        "corrective_replay_addendum_sha256": correction_addendum_sha256,
        "corrective_replay_verification_path": (
            str(Path(corrective_replay_verification).expanduser().resolve())
            if corrective_replay_verification is not None
            else None
        ),
        "corrective_replay_verification_sha256": correction_verification_sha256,
        "corrective_replay_verification_equal": (
            dict(correction_receipt) == dict(reproduced_correction)
            and correction_receipt.get("status") == "PASS"
        ),
        "source_seed_provenance_correction_path": (
            str(Path(source_seed_provenance_correction).expanduser().resolve())
            if source_seed_provenance_correction is not None
            else None
        ),
        "source_seed_provenance_correction_sha256": seed_correction_sha256,
        "source_seed_provenance_correction_equal": bool(
            seed_correction_payload
            and seed_correction_payload.get("status") == SEED_CORRECTION_STATUS
            and not any(
                failure.startswith("source_seed_provenance_correction")
                for failure in unique
            )
        ),
        "tle_file_set_sha256": ephemeris.get("file_set_sha256"),
        "tle_file_count": ephemeris.get("archive", {}).get("file_count"),
    }


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--corrective-replay-addendum", type=Path, required=True)
    parser.add_argument("--corrective-replay-verification", type=Path, required=True)
    parser.add_argument(
        "--source-seed-provenance-correction", type=Path, required=True
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    result_path = args.result.expanduser().resolve()
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    verification = verify_payload(
        payload,
        source_gate_path=result_path,
        corrective_addendum=args.corrective_replay_addendum,
        corrective_replay_verification=args.corrective_replay_verification,
        source_seed_provenance_correction=args.source_seed_provenance_correction,
    )
    args.output.write_text(
        json.dumps(verification, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(verification, sort_keys=True))
    return 0 if verification["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
