"""W-133 -- PNFE shares the exact OPS-3 live projection and stays read-only."""

from __future__ import annotations

import copy
import datetime as dt
from pathlib import Path

import numpy as np
import pytest

from mcrl.env.constants import TLE_ROOT_DEFAULT
from mcrl.env.mobility import MobilityConfig
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.step import PhysicsConfig, StepEnvironment
from mcrl.env.tle import TleArchive
from mcrl.runtime.ee_axis_ops3_live import (
    build_ops3_live_surfaces,
    project_ops3_anchor,
    snapshot_ops3_anchor,
)
from mcrl.runtime import ee_axis_pnfe_live as pnfe_live
from mcrl.runtime.ee_axis_pnfe_live import (
    build_pnfe_live_surfaces,
    snapshot_pnfe_anchor,
)


_ARCHIVE = Path(TLE_ROOT_DEFAULT).expanduser()
requires_archive = pytest.mark.skipif(
    not _ARCHIVE.is_dir(), reason="TLE archive not present"
)
_START = dt.datetime(2026, 8, 20, 6, 0, tzinfo=dt.timezone.utc)


def _first_low_angle_actions(observation: object) -> np.ndarray:
    masks = np.asarray(observation.masks, dtype=np.bool_)  # type: ignore[attr-defined]
    theta = np.asarray(  # type: ignore[attr-defined]
        observation.candidates.off_axis_deg, dtype=np.float64
    ).reshape(masks.shape)
    result = np.full(masks.shape[0], -1, dtype=np.int64)
    for uid, mask in enumerate(masks):
        legal = np.flatnonzero(mask & np.isfinite(theta[uid]))
        if legal.size:
            result[uid] = int(legal[np.argmin(theta[uid, legal])])
    return result


def _state(environment: StepEnvironment, rng: np.random.Generator) -> tuple[object, ...]:
    radiating = environment._previous_radiating
    return (
        environment._step_index,
        id(environment._candidates),
        tuple(environment._segments),
        tuple(environment._previous_association),
        environment._previous_link_power_w.tobytes(),
        radiating.norad_ids.tobytes(),
        radiating.cell_ids.tobytes(),
        radiating.power_w.tobytes(),
        environment.driver.step_index,
        environment.driver.user_ecef_km().tobytes(),
        copy.deepcopy(rng.bit_generator.state),
    )


@requires_archive
def test_real_tle_pnfe_is_shared_projected_centered_and_read_only() -> None:
    environment = StepEnvironment(
        ScenarioDriver(
            TleArchive(_ARCHIVE),
            ScenarioConfig(
                steps_per_episode=5,
                mobility=MobilityConfig(num_users=4),
            ),
        ),
        physics=PhysicsConfig(fading_enabled=False, segment_warm_start="none"),
    )
    rng = np.random.default_rng(2026090207)
    opening = environment.reset(_START, rng)
    first_actions = _first_low_angle_actions(opening)
    first_outcome = environment.step(first_actions, rng)
    observation = first_outcome.observation
    references = _first_low_angle_actions(observation)

    before = _state(environment, rng)
    ops3_anchor = snapshot_ops3_anchor(environment, observation)
    projection = project_ops3_anchor(ops3_anchor)
    c2 = build_ops3_live_surfaces(ops3_anchor, projection, references)
    pnfe_anchor = snapshot_pnfe_anchor(environment, observation, ops3_anchor)
    receipt = build_pnfe_live_surfaces(
        pnfe_anchor, ops3_anchor, projection, c2, references
    )
    after = _state(environment, rng)

    assert before == after
    assert len(receipt.surfaces) == 4
    assert receipt.ops3_anchor_sha256 == ops3_anchor.anchor_sha256
    assert receipt.ops3_projection_sha256 == projection.projection_sha256
    assert len(receipt.receipt_sha256) == 64
    assert bool(np.any(pnfe_anchor.committed))

    # The v1.1 opening predicate must agree with the simulator's own
    # non-committing service resolution for every live candidate row.
    for action in np.flatnonzero(observation.masks[0]).tolist():
        joint = np.array(references, copy=True)
        joint[0] = action
        evaluated = environment.evaluate_actions(joint, rng)
        assert bool(evaluated.resolution.served[0]) == bool(
            c2[0].opening_service_feasible[action]
        )
    assert _state(environment, rng) == after
    for uid, surface in enumerate(receipt.surfaces):
        assert surface.reference_action == int(references[uid])
        assert surface.q3_values[references[uid]] == 0.0
        assert surface.horizon == projection.horizon
        np.testing.assert_array_equal(
            surface.focal_active[0], c2[uid].opening_service_feasible
        )
        # Adding a focal beam/user to one identical frozen background cannot
        # manufacture non-focal delivered bits in this physical model.
        assert float(np.max(surface.externality_bits)) <= 1e-5

    repeated = build_pnfe_live_surfaces(
        pnfe_anchor, ops3_anchor, projection, c2, references
    )
    assert repeated.receipt_sha256 == receipt.receipt_sha256
    for first, second in zip(receipt.surfaces, repeated.surfaces, strict=True):
        np.testing.assert_array_equal(first.q3_values, second.q3_values)

    # Independently rebuild a few opening candidates through the deliberately
    # slow whole-network branch evaluator.  This pins the vectorised
    # load/interference delta to the canonical physical implementation.
    uid = 0
    positions = pnfe_live._position_maps(ops3_anchor, projection)[0]
    served, power = pnfe_live._committed_service_states(
        pnfe_anchor, ops3_anchor, projection
    )[0]
    active, focal_power = pnfe_live._opening_focal_state(
        ops3_anchor, uid, c2[uid]
    )
    victims = np.arange(pnfe_anchor.num_users) != uid
    baseline = pnfe_live._rates_for_branch(
        anchor=ops3_anchor,
        pnfe=pnfe_anchor,
        positions=positions,
        served=served,
        link_power_w=power,
        focal_user=uid,
        focal_action=None,
        focal_power_w=0.0,
    )[victims]
    for action in np.flatnonzero(active)[:3].tolist():
        inserted = pnfe_live._rates_for_branch(
            anchor=ops3_anchor,
            pnfe=pnfe_anchor,
            positions=positions,
            served=served,
            link_power_w=power,
            focal_user=uid,
            focal_action=action,
            focal_power_w=float(focal_power[action]),
        )[victims]
        expected = ops3_anchor.decision_step_s * float(np.sum(inserted - baseline))
        assert receipt.surfaces[uid].externality_bits[0, action] == pytest.approx(
            expected, abs=1e-5
        )
