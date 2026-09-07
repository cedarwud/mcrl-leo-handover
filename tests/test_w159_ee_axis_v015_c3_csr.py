"""Pure V0.15 C3 coalition-surplus-residual target seam."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.env.step import ActionEvaluation
from mcrl.errors import MCRLContractError
from mcrl.runtime.ee_axis_v015_c3_csr import (
    C3CSRContractError,
    C3CSRProvenance,
    build_c3_csr_target,
)


def _evaluation(
    rates: list[float],
    power: float,
    *,
    served: list[bool] | None = None,
) -> ActionEvaluation:
    served_vector = (
        np.ones(len(rates), dtype=np.bool_)
        if served is None
        else np.asarray(served, dtype=np.bool_)
    )
    return ActionEvaluation(
        rewards=(),
        resolution=SimpleNamespace(served=served_vector),
        energy=SimpleNamespace(),
        interference=SimpleNamespace(),
        radiating=SimpleNamespace(),
        link_power_w=np.zeros(len(rates), dtype=np.float64),
        link_sinr=np.zeros(len(rates), dtype=np.float64),
        link_rate_bps=np.asarray(rates, dtype=np.float64),
        handovers=(),
        system_power_w=power,
        fixed_power_w=0.0,
    )


def _provenance() -> C3CSRProvenance:
    return C3CSRProvenance(
        source_policy_version=15,
        anchor_sha256="a" * 64,
        source_manifest_sha256="b" * 64,
        checkpoint_sha256="c" * 64,
        common_random_field_sha256="d" * 64,
    )


def _target(*, swapped: bool = False):
    main = _evaluation([10.0, 20.0, 30.0], 10.0)
    candidate_u = _evaluation([14.0, 18.0, 32.0], 9.0)
    candidate_v = _evaluation([9.0, 25.0, 31.0], 11.0)
    candidate_uv = _evaluation([15.0, 24.0, 35.0], 7.0)
    if swapped:
        candidate_u, candidate_v = candidate_v, candidate_u
        focal_u, focal_v = 1, 0
    else:
        focal_u, focal_v = 0, 1
    return build_c3_csr_target(
        main,
        candidate_u,
        candidate_v,
        candidate_uv,
        focal_user_u=focal_u,
        focal_user_v=focal_v,
        interval_s=2.0,
        lambda_bits_per_j=3.0,
        provenance=_provenance(),
    )


def test_csr_identity_and_energy_interaction_are_exactly_exposed() -> None:
    target = _target()

    assert target.reference_surplus_bits == pytest.approx(60.0)
    assert target.candidate_u_surplus_bits == pytest.approx(74.0)
    assert target.candidate_v_surplus_bits == pytest.approx(64.0)
    assert target.candidate_uv_surplus_bits == pytest.approx(106.0)
    assert target.c1_u_bits == pytest.approx(14.0)
    assert target.c1_v_bits == pytest.approx(4.0)
    assert target.h_u_bits == pytest.approx(0.0)
    assert target.h_v_bits == pytest.approx(0.0)
    assert target.h_uv_bits == pytest.approx(28.0)
    assert target.z3_u_bits == pytest.approx(14.0)
    assert target.z3_v_bits == pytest.approx(14.0)
    assert target.energy_interaction_delta_w == pytest.approx(-3.0)
    assert target.energy_interaction_surplus_bits == pytest.approx(18.0)
    assert target.c1_u_bits + target.c1_v_bits + target.z3_u_bits + target.z3_v_bits == pytest.approx(
        target.candidate_uv_surplus_bits - target.reference_surplus_bits,
        abs=1e-12,
    )
    assert target.identity_residual_bits == pytest.approx(0.0, abs=1e-12)
    assert target.provenance is not None
    target.provenance.verify()


def test_csr_shapley_labels_swap_with_the_two_focal_users() -> None:
    forward = _target()
    reverse = _target(swapped=True)

    assert reverse.c1_u_bits == pytest.approx(forward.c1_v_bits)
    assert reverse.c1_v_bits == pytest.approx(forward.c1_u_bits)
    assert reverse.h_u_bits == pytest.approx(forward.h_v_bits)
    assert reverse.h_v_bits == pytest.approx(forward.h_u_bits)
    assert reverse.z3_u_bits == pytest.approx(forward.z3_v_bits)
    assert reverse.z3_v_bits == pytest.approx(forward.z3_u_bits)
    assert reverse.h_uv_bits == pytest.approx(forward.h_uv_bits)
    assert reverse.energy_interaction_delta_w == pytest.approx(
        forward.energy_interaction_delta_w
    )


def test_additive_branches_have_zero_spatial_interaction() -> None:
    main = _evaluation([100.0, 100.0, 100.0], 10.0)
    candidate_u = _evaluation([110.0, 102.0, 100.0], 11.0)
    candidate_v = _evaluation([103.0, 120.0, 100.0], 12.0)
    # The pair is the component-wise sum of the two singleton deltas.
    candidate_uv = _evaluation([113.0, 122.0, 100.0], 13.0)

    target = build_c3_csr_target(
        main,
        candidate_u,
        candidate_v,
        candidate_uv,
        focal_user_u=0,
        focal_user_v=1,
        interval_s=1.0,
        lambda_bits_per_j=2.0,
    )

    assert target.energy_interaction_delta_w == pytest.approx(0.0)
    assert target.energy_interaction_surplus_bits == pytest.approx(0.0)
    assert target.h_u_bits == pytest.approx(2.0)
    assert target.h_v_bits == pytest.approx(3.0)
    assert target.h_uv_bits == pytest.approx(5.0)
    assert target.z3_u_bits == pytest.approx(2.0)
    assert target.z3_v_bits == pytest.approx(3.0)
    assert target.spatial_interaction_surplus_bits == pytest.approx(0.0)


def test_positive_consolidation_energy_synergy_enters_c3_residual() -> None:
    main = _evaluation([100.0, 100.0], 10.0)
    candidate_u = _evaluation([100.0, 100.0], 12.0)
    candidate_v = _evaluation([100.0, 100.0], 13.0)
    # Pair consolidation needs 14 W, one watt less than additive singleton
    # activation (12 + 13 - 10 W).
    candidate_uv = _evaluation([100.0, 100.0], 14.0)

    target = build_c3_csr_target(
        main,
        candidate_u,
        candidate_v,
        candidate_uv,
        focal_user_u=0,
        focal_user_v=1,
        interval_s=2.0,
        lambda_bits_per_j=1.0,
    )

    assert target.energy_interaction_delta_w == pytest.approx(-1.0)
    assert target.energy_interaction_surplus_bits == pytest.approx(2.0)
    assert target.h_uv_bits == pytest.approx(2.0)
    assert target.z3_u_bits == pytest.approx(1.0)
    assert target.z3_v_bits == pytest.approx(1.0)


def test_csr_uses_served_rates_without_mutating_inputs() -> None:
    main_rates = np.asarray([10.0, 20.0, 999.0], dtype=np.float64)
    main = _evaluation(main_rates.tolist(), 10.0, served=[True, True, False])
    candidate_u = _evaluation([12.0, 20.0, 999.0], 10.0, served=[True, True, False])
    candidate_v = _evaluation([10.0, 22.0, 999.0], 10.0, served=[True, True, False])
    candidate_uv = _evaluation([12.0, 22.0, 999.0], 10.0, served=[True, True, False])
    before = main_rates.copy()

    target = build_c3_csr_target(
        main,
        candidate_u,
        candidate_v,
        candidate_uv,
        focal_user_u=0,
        focal_user_v=1,
        interval_s=1.0,
        lambda_bits_per_j=1.0,
    )

    assert target.reference_surplus_bits == pytest.approx(20.0)
    assert np.array_equal(main_rates, before)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"focal_user_u": 0, "focal_user_v": 0}, "distinct"),
        ({"focal_user_u": -1, "focal_user_v": 1}, "focal_user_u"),
        ({"focal_user_u": 0, "focal_user_v": 3}, "focal_user_v"),
        ({"interval_s": 0.0}, "interval_s"),
        ({"lambda_bits_per_j": -1.0}, "lambda_bits_per_j"),
    ],
)
def test_csr_rejects_invalid_scalar_inputs(kwargs: dict[str, object], message: str) -> None:
    values: dict[str, object] = {
        "focal_user_u": 0,
        "focal_user_v": 1,
        "interval_s": 1.0,
        "lambda_bits_per_j": 1.0,
    }
    values.update(kwargs)
    with pytest.raises(C3CSRContractError, match=message):
        build_c3_csr_target(
            _evaluation([1.0, 2.0, 3.0], 1.0),
            _evaluation([1.0, 2.0, 3.0], 1.0),
            _evaluation([1.0, 2.0, 3.0], 1.0),
            _evaluation([1.0, 2.0, 3.0], 1.0),
            **values,
        )


def test_csr_rejects_malformed_branches_and_provenance() -> None:
    good = _evaluation([1.0, 2.0, 3.0], 1.0)

    with pytest.raises(C3CSRContractError, match="ActionEvaluation"):
        build_c3_csr_target(
            object(),  # type: ignore[arg-type]
            good,
            good,
            good,
            focal_user_u=0,
            focal_user_v=1,
            interval_s=1.0,
            lambda_bits_per_j=1.0,
        )

    malformed = _evaluation([1.0, np.nan, 3.0], 1.0)
    with pytest.raises(C3CSRContractError, match="candidate_u.*rate"):
        build_c3_csr_target(
            good,
            malformed,
            good,
            good,
            focal_user_u=0,
            focal_user_v=1,
            interval_s=1.0,
            lambda_bits_per_j=1.0,
        )

    with pytest.raises(C3CSRContractError, match="provenance"):
        build_c3_csr_target(
            good,
            good,
            good,
            good,
            focal_user_u=0,
            focal_user_v=1,
            interval_s=1.0,
            lambda_bits_per_j=1.0,
            provenance=C3CSRProvenance(
                source_policy_version=1,
                anchor_sha256="not-a-digest",
                source_manifest_sha256="b" * 64,
                checkpoint_sha256="c" * 64,
                common_random_field_sha256="d" * 64,
            ),
        )

    with pytest.raises(C3CSRContractError, match="identical"):
        build_c3_csr_target(
            good,
            _evaluation([1.0, 2.0], 1.0),
            good,
            good,
            focal_user_u=0,
            focal_user_v=1,
            interval_s=1.0,
            lambda_bits_per_j=1.0,
        )


def test_csr_target_and_provenance_are_immutable() -> None:
    target = _target()

    with pytest.raises(FrozenInstanceError):
        target.z3_u_bits = 0.0  # type: ignore[misc]
    assert target.verify() == target.identity_residual_bits

