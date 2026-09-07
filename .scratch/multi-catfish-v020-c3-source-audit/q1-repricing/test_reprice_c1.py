from __future__ import annotations

import importlib.util
import math
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("reprice_c1.py")
SPEC = importlib.util.spec_from_file_location("q1_repricing_module", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_frozen_lambda_constants_have_declared_hex_values() -> None:
    assert MODULE.OLD_LAMBDA_BITS_PER_J.hex() == MODULE.OLD_LAMBDA_HEX
    assert MODULE.NEW_LAMBDA_BITS_PER_J.hex() == MODULE.NEW_LAMBDA_HEX
    assert MODULE.NEW_LAMBDA_BITS_PER_J > MODULE.OLD_LAMBDA_BITS_PER_J


def test_known_first_admitted_c1_row_reconstructs_persisted_target() -> None:
    receipt = MODULE._load_source_receipt()
    payload = MODULE._load_source(MODULE.SOURCE_SEEDS[0], receipt)
    row_index = next(index for index, row in enumerate(payload["rows"]) if row["admitted_route"] == "C1")
    record = MODULE._validate_admitted_c1_row(payload["rows"][row_index], seed=MODULE.SOURCE_SEEDS[0], row_index=row_index)
    error = float.fromhex(record["old_reconstruction_error_bits_hex"])
    assert abs(error) <= MODULE.OLD_ERROR_TOLERANCE_BITS
    assert record["split"] == "train"
    assert record["new_sign"] in {-1, 0, 1}


def test_build_receipt_uses_only_admitted_c1_rows_and_expected_splits() -> None:
    receipt = MODULE.build_receipt()
    assert receipt["status"] == "PASS"
    assert receipt["counts"]["admitted_c1_rows"] == 1680
    assert receipt["counts"]["train_rows"] == 968
    assert receipt["counts"]["validation_rows"] == 712
    assert receipt["counts"]["excluded_c3_rows"] == 1862
    assert receipt["checks"]["c3_rows_used"] == 0
    assert receipt["checks"]["test_split_opened"] is False
    assert receipt["checks"]["simulator_or_training_invoked"] is False
    assert all(record["split"] in {"train", "validation"} for record in receipt["records"])


def test_old_reconstruction_error_passes_frozen_gate() -> None:
    receipt = MODULE.build_receipt()
    max_error = float.fromhex(receipt["checks"]["old_target_max_abs_error_bits"])
    assert max_error <= MODULE.OLD_ERROR_TOLERANCE_BITS
    assert receipt["checks"]["old_target_reconstruction_within_tolerance"] is True


def test_new_target_is_recomputed_from_raw_values() -> None:
    receipt = MODULE._load_source_receipt()
    payload = MODULE._load_source(2026092001, receipt)
    row_index = next(index for index, row in enumerate(payload["rows"]) if row["admitted_route"] == "C1")
    record = MODULE._validate_admitted_c1_row(payload["rows"][row_index], seed=2026092001, row_index=row_index)
    raw = payload["rows"][row_index]["raw"]
    focal = raw["focal_user"]
    direct = MODULE.c1_zeta1(
        candidate_rate_bps=float.fromhex(raw["candidate_rates_bps"][focal]),
        reference_rate_bps=float.fromhex(raw["reference_rates_bps"][focal]),
        candidate_system_power_w=float.fromhex(raw["candidate_system_power_w"]),
        reference_system_power_w=float.fromhex(raw["reference_system_power_w"]),
        interval_s=float.fromhex(raw["interval_s"]),
        lambda_bits_per_j=MODULE.NEW_LAMBDA_BITS_PER_J,
    )
    assert math.isclose(direct, float.fromhex(record["repriced_new_target_hex"]), rel_tol=0.0, abs_tol=1e-12)


def test_sign_change_counts_are_recorded_without_sign_tuning() -> None:
    receipt = MODULE.build_receipt()
    directions = receipt["summary"]["directions"]
    assert directions["sign_flips"] == 76
    assert directions["old_positive_new_negative"] == 37
    assert directions["old_negative_new_positive"] == 39
    assert directions["old_zero_new_nonzero"] == 0
    assert directions["old_nonzero_new_zero"] == 0
