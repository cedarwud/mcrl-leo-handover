"""W-25 — probe P3: does ``r3`` discriminate, and at what scale?

P3 carries two obligations that were separate until 2026-08-23: SDD §4's
B17 Q3 (discriminability) and Q-D (the calibration scale).  They share one
measurement — the ``U_{b_u}`` distribution — which is why one probe can
hold both, but the discriminability half had no owner until the W-24 audit.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pytest

from mcrl.env.action_contract import NUM_ACTIONS, SlotTable
from mcrl.env.constants import TLE_ROOT_DEFAULT
from mcrl.env.mobility import MobilityConfig
from mcrl.env.reference_policy import STAY_IF_POSSIBLE, build_reference_policy
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.service import R3_CALIBRATION_SCALE, R3_SCALE_IS_FROZEN
from mcrl.env.step import PhysicsConfig, StepEnvironment
from mcrl.env.tle import TleArchive
from mcrl.errors import MCRLContractError
from mcrl.runtime.probe_p3 import (
    P3Accumulator,
    _correlation,
    _counterfactual_loads,
    _qd_scale,
    apply_qd_scale,
    run_probe_p3,
)

_ARCHIVE = Path(TLE_ROOT_DEFAULT).expanduser()
requires_archive = pytest.mark.skipif(
    not _ARCHIVE.is_dir(), reason="TLE archive not present"
)
USERS = 12
EPOCHS = [
    dt.datetime(2026, 8, 8, 0, 0, tzinfo=dt.timezone.utc) + dt.timedelta(hours=17 * k)
    for k in range(2)
]


def _environment():
    driver = ScenarioDriver(
        TleArchive(_ARCHIVE), ScenarioConfig(mobility=MobilityConfig(num_users=USERS))
    )
    return StepEnvironment(driver, physics=PhysicsConfig())


def _run(record):
    return run_probe_p3(
        prereg=record,
        policy=build_reference_policy(STAY_IF_POSSIBLE, seed=7),
        environment=_environment(),
        epochs=EPOCHS,
        env_rng=np.random.default_rng(0),
        mobility_rng=np.random.default_rng(1000),
        action_rng=np.random.default_rng(2000),
    )


@pytest.fixture(scope="module")
def record():
    from mcrl.runtime.prereg_draft import freeze

    return freeze()


# -- the counterfactual, which is the trap --------------------------------


class _Outcome:
    """Minimal stand-in carrying only what ``_counterfactual_loads`` reads."""

    class _Resolution:
        def __init__(self, loads, served, sat, cell):
            self.eligible_load_by_beam = loads
            self.served = served
            self.serving_satellite = sat
            self.serving_cell = cell

    def __init__(self, loads, served, sat, cell):
        self.resolution = self._Resolution(loads, served, sat, cell)


def _table(pairs):
    norads = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    cells = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    mask = np.zeros(NUM_ACTIONS, dtype=bool)
    for index, (norad, cell) in enumerate(pairs):
        norads[index], cells[index], mask[index] = norad, cell, True
    return SlotTable(norad_ids=norads, cell_ids=cells, mask=mask)


def test_a_user_counts_themselves_onto_the_beam_they_would_join():
    """The load a user WOULD experience, not the load already there."""
    table = _table([(1, 10), (2, 20)])
    outcome = _Outcome(
        {(1, 10): 3, (2, 20): 5},
        np.array([False]),
        np.array([-1]),
        np.array([-1]),
    )
    loads = _counterfactual_loads(0, table, np.array([0, 1]), outcome)
    assert loads.tolist() == [4.0, 6.0], "joining adds one"


def test_a_user_already_on_a_beam_is_not_credited_a_lower_load():
    """The trap: reading the realised load would favour staying put.

    A user sitting on a beam of 3 is one of that 3.  If their own candidate
    reported 3 while every other candidate reported "occupants + 1", the
    argmax would prefer the incumbent for an arithmetic reason rather than a
    congestion one — and the whole probe is about whether ``r3`` steers on
    congestion.
    """
    table = _table([(1, 10), (2, 20)])
    outcome = _Outcome(
        {(1, 10): 3, (2, 20): 3},
        np.array([True]),
        np.array([1]),
        np.array([10]),
    )
    loads = _counterfactual_loads(0, table, np.array([0, 1]), outcome)
    assert loads.tolist() == [3.0, 4.0], (
        "the incumbent beam holds 3 INCLUDING this user, so staying is 3; "
        "the other holds 3 strangers, so joining is 4"
    )


# -- the Q-D mapping is applied, not chosen -------------------------------


def test_the_qd_mapping_is_p95_rounded():
    values = np.array([1, 1, 2, 2, 3, 3, 4, 5, 6, 20], dtype=np.float64)
    assert _qd_scale(values) == int(round(float(np.percentile(values, 95))))
    # p95, not max: the max is one congested beam.
    assert _qd_scale(values) < values.max()


def test_an_empty_r3_series_refuses_to_produce_a_scale():
    with pytest.raises(MCRLContractError, match="must not be invented"):
        _qd_scale(np.array([]))


def test_the_frozen_scale_is_what_the_mapping_returned():
    """``R3_CALIBRATION_SCALE`` must be P3's output, not a chosen number."""
    from mcrl.runtime.prereg_draft import SELECTION_MAPPINGS

    mapping = SELECTION_MAPPINGS["Q-D r3 calibration scale"]
    assert R3_SCALE_IS_FROZEN is True
    assert mapping["resolved"] == R3_CALIBRATION_SCALE == 6
    measured = mapping["measured_abs_r3_over_served_steps"]
    assert int(round(measured["p95"])) == R3_CALIBRATION_SCALE


def test_a_correlation_that_does_not_exist_is_not_reported_as_zero():
    """``None`` and 0.0 are different findings and must not be conflated."""
    constant = np.ones(10)
    assert _correlation(constant, np.arange(10.0)) is None
    assert _correlation(np.arange(10.0), np.arange(10.0)) == pytest.approx(1.0)


# -- the gate -------------------------------------------------------------


@requires_archive
def test_p3_refuses_a_record_without_its_own_grid_entry(record):
    from mcrl.runtime.prereg import PreregRecord

    stripped = PreregRecord(
        sections=dict(record.sections) | {"probe_grid": {"P1": {"x": 1}}},
        holdout=record.holdout,
    ).with_digest()
    with pytest.raises(MCRLContractError, match="no P3 entry"):
        _run(stripped)


@requires_archive
def test_p3_refuses_when_its_selection_mapping_is_absent(record):
    from mcrl.runtime.prereg import PreregRecord

    stripped = PreregRecord(
        sections=dict(record.sections) | {"selection_mappings": {"other": {}}},
        holdout=record.holdout,
    ).with_digest()
    with pytest.raises(MCRLContractError, match="before P3 runs"):
        _run(stripped)


# -- end to end -----------------------------------------------------------


@requires_archive
def test_p3_answers_both_of_its_questions(record):
    result = _run(record)

    # B17 Q3: r3 must actually discriminate between a user's candidates.
    assert result["candidate_load_width"]["p50"] > 0.0
    assert result["degenerate_step_fraction"] < 0.5
    assert 0.0 <= result["r1_r3_argmax_agreement_rate"] <= 1.0
    assert result["argmax_comparisons"] > 0

    # Q-D: the scale, and it must be the mapping's output.
    assert result["qd_scale_p95_rounded"] == apply_qd_scale(result)
    assert result["qd_scale_p95_rounded"] >= 1

    # Provenance travels with the numbers.
    assert result["prereg_digest"] == record.digest
    assert result["selection_mapping"]["rule"]
    assert len(result["epochs"]) == len(EPOCHS)


@requires_archive
def test_p3_is_reproducible_from_its_three_streams(record):
    first, second = _run(record), _run(record)
    assert first["qd_scale_p95_rounded"] == second["qd_scale_p95_rounded"]
    assert (
        first["r1_r3_argmax_agreement_rate"]
        == second["r1_r3_argmax_agreement_rate"]
    )


def test_the_accumulator_refuses_to_summarise_nothing():
    with pytest.raises(MCRLContractError):
        P3Accumulator().summarise()
