from __future__ import annotations

from fractions import Fraction
import json
from pathlib import Path

import numpy as np
import pytest

import run_v023_c3_candidate_ca as ca


def test_contract_toy_three_member_exact_shapley_and_overlap() -> None:
    members = (4, 7, 9)
    values = {
        frozenset(): 0.0,
        frozenset({4}): -3.0,
        frozenset({7}): -3.0,
        frozenset({9}): -3.0,
        frozenset({4, 7}): -3.0,
        frozenset({4, 9}): -3.0,
        frozenset({7, 9}): -3.0,
        frozenset({4, 7, 9}): 12.0,
    }

    shapley = ca.exact_shapley(values, members)
    assert shapley == {4: Fraction(4), 7: Fraction(4), 9: Fraction(4)}
    z = ca.subtract_overlap(shapley, {4: 1.0, 7: 2.0, 9: 3.0})
    assert z == {4: Fraction(3), 7: Fraction(2), 9: Fraction(1)}
    assert sum(z.values()) + sum(map(Fraction, (1.0, 2.0, 3.0))) == 12


def test_catalogue_mismatch_blocks_support() -> None:
    outcome = ca.screen_decision(
        base_rows=[ca.PooledRow(10.0, 2.0, 10, 10)],
        candidate_rows=[ca.PooledRow(12.0, 2.0, 10, 10)],
        catalogue_agreement=False,
        higher_order_exposure=True,
        legal_physical_change=True,
    )
    assert outcome["decision"] == "C_A_FAST_SCREEN_NO_SUPPORT"
    assert outcome["reasons"] == ["INTERFACE_CATALOG_MISMATCH"]


def test_higher_order_exposure_is_required() -> None:
    outcome = ca.screen_decision(
        base_rows=[ca.PooledRow(10.0, 2.0, 10, 10)],
        candidate_rows=[ca.PooledRow(12.0, 2.0, 10, 10)],
        catalogue_agreement=True,
        higher_order_exposure=False,
        legal_physical_change=True,
    )
    assert outcome["decision"] == "C_A_FAST_SCREEN_NO_SUPPORT"
    assert outcome["reasons"] == ["NO_HIGHER_ORDER_EXPOSURE"]


def test_float32_composition_lowest_tie_and_noop() -> None:
    q12 = np.asarray([[1.0, 1.0, 0.0], [4.0, 9.0, 2.0]], dtype=np.float32)
    masks = np.asarray([[True, True, False], [False, False, False]])
    z = np.zeros((2, 3), dtype=np.float64)
    # This is below one float32 ulp at 1.0, but composition happens after the
    # already-frozen float32 surface is promoted to float64.
    z[0, 1] = ca.KAPPA_BITS * 2.0**-30
    actions, composed = ca.select_deployed_actions(q12, masks, z)
    assert composed.dtype == np.float64
    assert actions.tolist() == [1, ca.NO_OP_ACTION]

    z[0, 1] = 0.0
    actions, _ = ca.select_deployed_actions(q12, masks, z)
    assert actions.tolist() == [0, ca.NO_OP_ACTION]


def test_exact_rational_pooling_is_ratio_of_sums() -> None:
    pooled = ca.pool_exact(
        [ca.PooledRow(1.5, 0.5, 1, 2), ca.PooledRow(2.25, 1.0, 2, 3)]
    )
    assert pooled["total_bits_exact"] == Fraction(15, 4)
    assert pooled["total_energy_j_exact"] == Fraction(3, 2)
    assert pooled["eta_exact"] == Fraction(5, 2)
    assert pooled["service_fraction_exact"] == Fraction(3, 5)


def test_unsealed_contract_refused(tmp_path: Path) -> None:
    contract = tmp_path / "contract.md"
    contract.write_text("draft\n", encoding="utf-8")
    with pytest.raises(ca.CAError, match="not sealed"):
        ca.sealed_contract_binding(contract)


@pytest.mark.parametrize(
    "value",
    [
        "1:2026092101",
        f"{ca.WORLDS[0]}:1",
    ],
)
def test_other_worlds_or_lineages_refused(value: str) -> None:
    with pytest.raises(ca.CAError):
        ca.UnitKey.parse(value)


def test_other_steps_refused() -> None:
    with pytest.raises(ca.CAError, match="steps 0 and 1"):
        ca.validate_step_indices([0, 2])


def test_write_once_refuses_overwrite_and_publishes_0444(tmp_path: Path) -> None:
    target = tmp_path / "receipt.json"
    digest = ca.write_once(target, {"value": 1})
    assert target.stat().st_mode & 0o777 == 0o444
    assert ca.file_sha256(target) == digest
    assert json.loads(target.read_text(encoding="ascii")) == {"value": 1}
    with pytest.raises(ca.CAError, match="overwrite"):
        ca.write_once(target, {"value": 2})


def test_profile_count_cap_refuses_without_truncating() -> None:
    with pytest.raises(ca.CAIncomplete, match="PROFILE_COUNT_EXCEEDED") as caught:
        ca.require_profile_count_within_cap(member_count=3, profile_count_cap=7)
    assert caught.value.reason == "PROFILE_COUNT_EXCEEDED"
    assert ca.require_profile_count_within_cap(member_count=3, profile_count_cap=8) == 8


def test_output_root_is_confined_to_owned_candidate_directory() -> None:
    owned = ca.HERE / "formal-output"
    assert ca.validate_output_root(owned) == owned.resolve()
    for forbidden in (ca.E1_OUTPUT_ROOT, Path("/tmp/candidate-ca-escape"), ca.REPO / ".scratch"):
        with pytest.raises(ca.CAError, match="owned C-A directory"):
            ca.validate_output_root(forbidden)


def test_budget_ledger_rejects_duplicate_or_nonfinite_reservations() -> None:
    payload = ca._empty_budget()
    payload["reservations"] = [
        {"token": "same", "scope": "merge", "worker_seconds_hex": 1.0.hex()},
        {"token": "same", "scope": "merge", "worker_seconds_hex": float("inf").hex()},
    ]
    with pytest.raises(ca.CAError, match="reservation"):
        ca._validate_budget(payload)


def test_status_receipt_reuse_is_exactly_authenticated(tmp_path: Path) -> None:
    kwargs = {
        "status": "INCOMPLETE",
        "scope": "unit:test",
        "profile_count_cap": 8,
        "error": ca.CAIncomplete("INTERRUPTED"),
        "preflight_path": tmp_path / "preflight.json",
        "preflight_sha256": "1" * 64,
        "launch_authority_path": tmp_path / "authority.json",
        "launch_authority_sha256": "2" * 64,
    }
    path = ca._publish_status_once(tmp_path, **kwargs)
    assert ca._publish_status_once(tmp_path, **kwargs) == path
    with pytest.raises(ca.CAError, match="binding/content drifted"):
        ca._publish_status_once(
            tmp_path, **{**kwargs, "launch_authority_sha256": "3" * 64}
        )


def test_physical_metrics_must_derive_from_serialized_profile() -> None:
    key = ca.ALL_UNITS[0]
    tape_path, _manifest_path, _receipt_path = ca._e1_unit_paths(ca.E1_OUTPUT_ROOT, key)
    tape = json.loads(tape_path.read_text(encoding="ascii"))
    payload = tape["steps"][0]["reference_profile"]
    profile = ca.f1.profile_from_payload(payload)
    receipt = {
        "physical_profile_sha256": ca.canonical_sha256(payload),
        "physical_profile": payload,
        "metrics": ca.e1._profile_metrics(profile),
        "f0_conservation": ca.e1._conservation(profile),
    }
    assert ca._profile_row_from_receipt(receipt).opportunities == ca.USERS
    tampered = {**receipt, "metrics": {**receipt["metrics"], "served": 0}}
    with pytest.raises(ca.CAError, match="not derived"):
        ca._profile_row_from_receipt(tampered)
