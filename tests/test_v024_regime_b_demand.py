"""V0.24 B1 finite-demand accounting and G0 identity tests."""

from __future__ import annotations

import dataclasses
import datetime as dt
import enum
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from mcrl.env.constants import DECISION_STEP_S, TLE_ROOT_DEFAULT
from mcrl.env.demand import DemandModel
from mcrl.env.mobility import MobilityConfig
from mcrl.env.reference_policy import NEAREST_ELIGIBLE, build_reference_policy
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.step import PhysicsConfig, StepEnvironment
from mcrl.env.tle import TleArchive


ARCHIVE = Path(TLE_ROOT_DEFAULT).expanduser()
START = dt.datetime(2026, 8, 20, 6, 0, tzinfo=dt.timezone.utc)
requires_archive = pytest.mark.skipif(not ARCHIVE.is_dir(), reason="TLE archive absent")
LEGACY_OUTCOME_FIELDS = (
    "step_index", "done", "observation", "rewards", "resolution", "energy",
    "interference", "radiating", "interference_terms_w", "separation_deg",
    "link_power_w", "link_sinr", "link_rate_bps", "handovers",
    "system_power_w", "fixed_power_w", "diagnostics",
)
PRE_CHANGE_G0_SHA256 = "46b16f1725fde28adbd843d915be7771fc57b2683fde9b0d0f1fe9d088ba849e"


def _encode(value: object) -> object:
    if dataclasses.is_dataclass(value):
        return {
            "@": value.__class__.__qualname__,
            **{field.name: _encode(getattr(value, field.name)) for field in dataclasses.fields(value)},
        }
    if isinstance(value, np.ndarray):
        array = np.ascontiguousarray(value)
        return {"@": "ndarray", "dtype": array.dtype.str, "shape": list(array.shape), "data": array.tobytes().hex()}
    if isinstance(value, np.generic):
        return _encode(value.item())
    if isinstance(value, enum.Enum):
        return {"@": value.__class__.__qualname__, "value": _encode(value.value)}
    if isinstance(value, dict):
        return [[_encode(key), _encode(item)] for key, item in sorted(value.items(), key=lambda pair: repr(pair[0]))]
    if isinstance(value, (list, tuple)):
        return [_encode(item) for item in value]
    if isinstance(value, float):
        return {"@": "float", "hex": value.hex()}
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(type(value))


def _environment(demand: DemandModel | None = None) -> StepEnvironment:
    return StepEnvironment(
        ScenarioDriver(
            TleArchive(ARCHIVE),
            ScenarioConfig(mobility=MobilityConfig(num_users=4)),
        ),
        physics=PhysicsConfig(segment_warm_start="none", fading_enabled=False),
        demand=demand,
    )


def _episode(environment: StepEnvironment) -> list[object]:
    rng = np.random.default_rng(2401)
    observation = environment.reset(START, rng, mobility_rng=np.random.default_rng(2402))
    policy = build_reference_policy(NEAREST_ELIGIBLE, 5683200792433982503)
    policy.reset()
    outcomes = []
    for _ in range(2):
        actions = policy.act(observation.candidates, np.random.default_rng(2403))
        outcome = environment.step(actions, rng)
        outcomes.append(outcome)
        observation = outcome.observation
    return outcomes


def test_demand_cap_arithmetic() -> None:
    rates = np.array([0.0, 5.0, 12.0], dtype=np.float64)
    assert np.array_equal(
        DemandModel(10.0).delivered_bits(rates, interval_s=2.0),
        np.array([0.0, 10.0, 20.0]),
    )
    assert np.array_equal(
        DemandModel().delivered_bits(rates, interval_s=2.0), rates * 2.0
    )
    with pytest.raises(ValueError):
        DemandModel(0.0)


@requires_archive
def test_g0_preexisting_outcome_payload_is_byte_identical() -> None:
    outcomes = _episode(_environment())
    legacy = [
        {
            "@": "StepOutcome",
            **{name: _encode(getattr(outcome, name)) for name in LEGACY_OUTCOME_FIELDS},
        }
        for outcome in outcomes
    ]
    encoded = json.dumps(legacy, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    assert hashlib.sha256(encoded).hexdigest() == PRE_CHANGE_G0_SHA256
    for outcome in outcomes:
        assert np.array_equal(outcome.capacity_bits, outcome.delivered_bits)
        assert np.array_equal(
            outcome.capacity_bits, outcome.link_rate_bps * DECISION_STEP_S
        )


@requires_archive
def test_finite_demand_changes_only_goodput_accounting() -> None:
    g0 = _episode(_environment())
    finite = _episode(_environment(DemandModel(10e6)))
    for control, capped in zip(g0, finite, strict=True):
        assert np.array_equal(control.capacity_bits, capped.capacity_bits)
        assert np.all(capped.delivered_bits <= 30.08 * 10e6)
        assert np.array_equal(control.link_power_w, capped.link_power_w)
        assert control.system_power_w == capped.system_power_w
        assert np.array_equal(control.resolution.served, capped.resolution.served)
        assert np.array_equal(control.radiating.power_w, capped.radiating.power_w)


@requires_archive
def test_action_evaluation_and_last_outcome_expose_both_bit_columns() -> None:
    environment = _environment(DemandModel(50e6))
    rng = np.random.default_rng(91)
    observation = environment.reset(START, rng, mobility_rng=np.random.default_rng(92))
    actions = np.asarray([np.flatnonzero(row)[0] for row in observation.masks], dtype=np.int64)
    evaluation = environment.evaluate_actions(actions, rng)
    outcome = environment.step(actions, rng)
    for value in (evaluation, outcome):
        assert value.capacity_bits.shape == value.delivered_bits.shape == (4,)
        assert np.all(value.delivered_bits <= value.capacity_bits)
