from __future__ import annotations

from types import SimpleNamespace
import sys

import numpy as np
import pytest


HERE = __import__("pathlib").Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "src"))

import c2_temporal_fork_telemetry as telemetry  # noqa: E402
from mcrl.env.constants import DECISION_STEP_S  # noqa: E402


def _outcome(*, throughput: float, power: float, served=(True, False)):
    served_array = np.asarray(served, dtype=np.bool_)
    return SimpleNamespace(
        reward_matrix=np.asarray(
            [[throughput / 10.0, -0.5, 0.1], [0.0, 0.0, -0.1]],
            dtype=np.float64,
        ),
        energy=SimpleNamespace(
            system_throughput_bps=throughput,
            system_consumed_power_w=power,
        ),
        resolution=SimpleNamespace(
            served=served_array,
            served_count=int(served_array.sum()),
        ),
    )


def test_main_ee_is_ratio_of_sums_not_mean_of_ratios():
    accumulator = telemetry.MainOutcomeAccumulator()
    accumulator.observe(_outcome(throughput=10.0, power=1.0))
    accumulator.observe(_outcome(throughput=10.0, power=9.0))

    result = accumulator.snapshot()
    assert result["useful_bits"] == pytest.approx(20.0 * DECISION_STEP_S)
    assert result["energy_j"] == pytest.approx(10.0 * DECISION_STEP_S)
    assert result["ratio_of_sums_ee_bits_per_j"] == pytest.approx(2.0)
    assert result["ratio_of_sums_ee_bits_per_j"] != pytest.approx(
        (10.0 / 1.0 + 10.0 / 9.0) / 2.0
    )
    assert result["served_fraction"] == pytest.approx(0.5)


def test_schedule_and_execution_keep_opportunity_cost_and_dose_separate():
    run = telemetry.C2RunTelemetry()
    run.observe_main(_outcome(throughput=5.0, power=2.0))
    rows = [
        {"passed": True, "elapsed_s": 1.0},
        {"passed": True, "elapsed_s": 2.0},
        {"passed": False, "elapsed_s": 3.0},
        {"passed": False, "support_rejection": "expiry", "elapsed_s": 4.0},
        {"passed": False, "contract_error": "bad", "elapsed_s": 5.0},
    ]
    run.observe_schedule(rows, support_count=2)
    receipt = SimpleNamespace(admitted=True, updated=True, joint_committed=True)
    unit = SimpleNamespace(committed_payloads=(1, 2, 3, 4))
    run.observe_execution(receipt, unit)

    result = run.snapshot()
    assert result["main"]["ratio_of_sums_ee_bits_per_j"] == pytest.approx(2.5)
    assert result["c2"]["choice_counts"] == {"K0": 0, "K1": 0, "K>=2": 1}
    assert result["c2"]["candidate_outcomes"] == {
        "certificate_pass": 2,
        "certificate_fail": 1,
        "support_rejection": 1,
        "contract_error": 1,
    }
    assert result["c2"]["forecast_wall_time_s"] == pytest.approx(15.0)
    assert result["c2"]["option_primitive_steps"] == 4
    assert result["c2"]["joint_commits"] == 1


def test_schedule_support_count_mismatch_fails_closed():
    run = telemetry.C2RunTelemetry()
    with pytest.raises(
        telemetry.TelemetryContractError,
        match="support_count disagrees",
    ):
        run.observe_schedule([{"passed": True, "elapsed_s": 0.1}], support_count=0)
    assert run.snapshot()["c2"]["schedules"] == 0
    assert run.snapshot()["c2"]["scheduled_candidates"] == 0


def test_invalid_execution_dose_fails_before_mutating_counts():
    run = telemetry.C2RunTelemetry()
    receipt = SimpleNamespace(admitted=False, updated=True, joint_committed=True)
    unit = SimpleNamespace(committed_payloads=(1,))
    with pytest.raises(telemetry.TelemetryContractError, match="without admission"):
        run.observe_execution(receipt, unit)
    assert run.snapshot()["c2"]["options_executed"] == 0
    assert run.snapshot()["c2"]["joint_commits"] == 0


def test_observation_wrapper_returns_exact_result_and_delegates_state():
    result = object()
    outcome = _outcome(throughput=3.0, power=2.0)

    class Environment:
        marker = "canonical"
        last_outcome = outcome

        def step(self, actions, rng):
            assert actions == [7]
            assert rng == "rng"
            return result

    run = telemetry.C2RunTelemetry()
    wrapped = telemetry.OutcomeTelemetryEnvironment(Environment(), run)
    assert wrapped.marker == "canonical"
    assert wrapped.step([7], "rng") is result
    assert run.snapshot()["main"]["steps"] == 1


def test_malformed_outcome_fails_before_mutating_accumulator():
    accumulator = telemetry.MainOutcomeAccumulator()
    bad = _outcome(throughput=1.0, power=1.0)
    bad.resolution.served_count = 2
    with pytest.raises(telemetry.TelemetryContractError, match="served_count"):
        accumulator.observe(bad)
    assert accumulator.snapshot()["steps"] == 0
