"""W-189 -- exact two-user four-profile LC-SRS teacher boundary."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from mcrl.runtime.ee_axis_lcsrs_c3_teacher import (
    LCSRSC3TeacherError,
    LCSRSFourProfileDraw,
    build_lcsrs_two_user_teacher,
    lcsrs_action_sha256,
)


def _draw(index: int, *, field: str = "a" * 64) -> LCSRSFourProfileDraw:
    actions = np.asarray([[0, 0], [1, 0], [0, 2], [1, 2]], dtype=np.int64)
    bits = np.asarray(
        [[100.0, 100.0], [90.0, 100.0], [100.0, 90.0], [100.0, 100.0]],
        dtype=np.float64,
    )
    energy = np.asarray([10.0, 10.0, 10.0, 5.0], dtype=np.float64)
    return LCSRSFourProfileDraw(
        draw_index=index,
        profile_actions=actions,
        profile_bits=bits,
        profile_energy_j=energy,
        common_field_sha256_by_profile=(field,) * 4,
        action_sha256_by_profile=tuple(lcsrs_action_sha256(row) for row in actions),
    )


def _kwargs() -> dict[str, object]:
    legal = np.zeros((2, 28), dtype=np.bool_)
    legal[:, 0] = True
    legal[0, 1] = True
    legal[1, 2] = True
    return {
        "pair_id": "p0",
        "member_users": np.asarray([0, 1], dtype=np.int64),
        "proposed_actions": np.asarray([1, 2], dtype=np.int64),
        "reference_actions": np.asarray([0, 0], dtype=np.int64),
        "legal_mask": legal,
        "draws": [_draw(index) for index in range(32)],
        "lambda_bits_per_j": 1.0,
        "kappa_bits": 2.0,
    }


def test_teacher_applies_formula_per_draw_then_averages_without_sign_filter() -> None:
    teacher = build_lcsrs_two_user_teacher(**_kwargs())
    assert len(teacher.draws) == len(teacher.formula_results) == 32
    np.testing.assert_allclose(teacher.pair_targets.normalized_targets_by_draw, 6.25)
    np.testing.assert_allclose(teacher.pair_targets.mean_targets, [6.25, 6.25])
    assert all(result.verify() == pytest.approx(0.0) for result in teacher.formula_results)
    assert len(teacher.content_digest) == 64
    for draw in teacher.draws:
        assert not draw.profile_actions.flags.writeable
        assert not draw.profile_bits.flags.writeable
        assert not draw.profile_energy_j.flags.writeable


def test_common_field_and_literal_profile_mismatches_fail_closed() -> None:
    values = _kwargs()
    with pytest.raises(LCSRSC3TeacherError, match="common random field"):
        replace(
            values["draws"][0],  # type: ignore[index]
            common_field_sha256_by_profile=("a" * 64, "a" * 64, "f" * 64, "a" * 64),
        )
    bad = list(values["draws"])  # type: ignore[arg-type]
    actions = np.array(bad[0].profile_actions, copy=True)
    actions[1, 1] = 2
    bad[0] = replace(
        bad[0],
        profile_actions=actions,
        action_sha256_by_profile=tuple(lcsrs_action_sha256(row) for row in actions),
    )
    values["draws"] = bad
    with pytest.raises(LCSRSC3TeacherError, match="00/10/01/11"):
        build_lcsrs_two_user_teacher(**values)


def test_exactly_two_members_and_exactly_32_draws_are_not_generalized() -> None:
    values = _kwargs()
    values["member_users"] = np.asarray([0, 1, 2], dtype=np.int64)
    with pytest.raises(LCSRSC3TeacherError, match="exactly two"):
        build_lcsrs_two_user_teacher(**values)
    values = _kwargs()
    values["draws"] = values["draws"][:-1]  # type: ignore[index]
    with pytest.raises(LCSRSC3TeacherError, match="exactly 32"):
        build_lcsrs_two_user_teacher(**values)


def test_negative_member_target_is_retained_as_valid_avoidance_evidence() -> None:
    values = _kwargs()
    draws = list(values["draws"])  # type: ignore[arg-type]
    for index, draw in enumerate(draws):
        bits = np.array(draw.profile_bits, copy=True)
        energy = np.array(draw.profile_energy_j, copy=True)
        bits[1] = [70.0, 100.0]
        bits[2] = [100.0, 100.0]
        bits[3] = [70.0, 70.0]
        energy[3] = 10.0
        draws[index] = replace(draw, profile_bits=bits, profile_energy_j=energy)
    values["draws"] = draws
    teacher = build_lcsrs_two_user_teacher(**values)
    assert np.any(teacher.pair_targets.normalized_targets_by_draw < 0.0)
