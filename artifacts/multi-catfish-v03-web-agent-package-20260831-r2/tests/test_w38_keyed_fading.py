"""W-38 — branch-independent keyed common-random fading for C2 V0.3."""

from __future__ import annotations

import numpy as np

from mcrl.env.keyed_fading import KEYED_FADING_VERSION, KeyedFadingField
from mcrl.env.link_budget import (
    rician_fading_gain,
    shadow_fading_db,
    shadow_fading_sigma_db,
)
from mcrl.env.step import PhysicsConfig, StepEnvironment


def _draw(
    field: KeyedFadingField,
    norads: list[int],
    *,
    event: str = "physics",
    step: int = 4,
    elevations: dict[int, np.ndarray] | None = None,
):
    return field.draw(
        event=event,
        step_index=step,
        norad_ids=norads,
        num_users=3,
        elevation_by_norad=elevations,
        k_factor_db=20.0,
    )


def test_common_paths_are_invariant_to_satellite_set_and_order():
    field = KeyedFadingField.from_components("checkpoint-A", 17, "anchor-9")
    elevation = {
        101: np.array([30.0, 40.0, 50.0]),
        202: np.array([35.0, 45.0, 55.0]),
        303: np.array([25.0, 35.0, 45.0]),
    }

    left_r, left_s = _draw(field, [202, 101], elevations=elevation)
    right_r, right_s = _draw(field, [303, 101, 202], elevations=elevation)

    for norad in (101, 202):
        assert np.array_equal(left_r[norad], right_r[norad])
        assert np.array_equal(left_s[norad], right_s[norad])


def test_event_step_and_root_are_independent_key_axes():
    field = KeyedFadingField.from_components("checkpoint-A", 17)
    base_r, base_s = _draw(field, [101])
    variants = [
        _draw(field, [101], event="observation"),
        _draw(field, [101], step=5),
        _draw(KeyedFadingField.from_components("checkpoint-A", 18), [101]),
    ]

    for rician, shadow in variants:
        assert not np.array_equal(base_r[101], rician[101])
        assert not np.array_equal(base_s[101], shadow[101])


def test_elevation_changes_sigma_but_keeps_the_shadow_normal_common():
    field = KeyedFadingField.from_components("checkpoint-A", 17)
    low = {101: np.array([20.0, 30.0, 40.0])}
    high = {101: np.array([50.0, 60.0, 70.0])}

    low_r, low_s = _draw(field, [101], elevations=low)
    high_r, high_s = _draw(field, [101], elevations=high)

    assert np.array_equal(low_r[101], high_r[101])
    low_z = low_s[101] / shadow_fading_sigma_db(low[101])
    high_z = high_s[101] / shadow_fading_sigma_db(high[101])
    assert np.allclose(low_z, high_z, rtol=0.0, atol=1e-15)


def test_default_step_environment_path_keeps_legacy_sequential_draws():
    stand_in = StepEnvironment.__new__(StepEnvironment)
    stand_in.physics = PhysicsConfig()
    stand_in.num_users = 3
    stand_in._step_index = 2
    stand_in._fading_field = None
    satellite_ecef = {202: np.zeros(3), 101: np.ones(3)}
    elevation = {
        101: np.array([30.0, 40.0, 50.0]),
        202: np.array([35.0, 45.0, 55.0]),
    }

    actual_rng = np.random.default_rng(91)
    actual_r, actual_s = stand_in._draw_fading(
        satellite_ecef,
        actual_rng,
        elevation,
        event="physics",
    )

    expected_rng = np.random.default_rng(91)
    expected_r: dict[int, np.ndarray] = {}
    expected_s: dict[int, np.ndarray] = {}
    for norad in sorted(satellite_ecef):
        expected_r[norad] = rician_fading_gain(
            expected_rng,
            (3,),
            k_factor_db=stand_in.physics.rician_k_factor_db,
        )
        expected_s[norad] = shadow_fading_db(expected_rng, elevation[norad])

    for norad in sorted(satellite_ecef):
        assert np.array_equal(actual_r[norad], expected_r[norad])
        assert np.array_equal(actual_s[norad], expected_s[norad])


def test_step_environment_keyed_path_does_not_consume_branch_rng():
    stand_in = StepEnvironment.__new__(StepEnvironment)
    stand_in.physics = PhysicsConfig()
    stand_in.num_users = 3
    stand_in._step_index = 2
    stand_in._fading_field = KeyedFadingField.from_components("fork", 8)

    branch_rng = np.random.default_rng(91)
    stand_in._draw_fading(
        {101: np.ones(3)},
        branch_rng,
        {101: np.array([30.0, 40.0, 50.0])},
        event="physics",
    )
    untouched_rng = np.random.default_rng(91)
    assert branch_rng.random() == untouched_rng.random()


def test_receipt_names_the_version_and_key_axes_without_raw_root():
    field = KeyedFadingField.from_components("checkpoint-A", 17)
    receipt = field.receipt()

    assert receipt["mode"] == KEYED_FADING_VERSION
    assert receipt["version"] == KEYED_FADING_VERSION
    assert receipt["key_axes"] == ["event", "step_index", "norad_id"]
    assert receipt["root_digest"] == field.root_digest
    assert field.root_key not in receipt.values()
