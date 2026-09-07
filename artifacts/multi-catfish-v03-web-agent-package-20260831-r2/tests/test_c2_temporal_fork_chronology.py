from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import c2_temporal_fork_chronology as CHRONOLOGY  # noqa: E402
import c2_temporal_fork_core as C2  # noqa: E402
import c2_temporal_fork_forecast_adapter as FORECAST  # noqa: E402


USERS = 2
FOCAL = 1


def digest(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def physical(user: int, action: int) -> tuple[int, int]:
    return 80000 + user, action


def mask() -> np.ndarray:
    value = np.zeros((USERS, C2.ACTION_DIM), dtype=bool)
    value[:, [2, 3]] = True
    return value


def bindings():
    return tuple(
        (
            C2.ActionBinding(2, physical(user, 2)),
            C2.ActionBinding(3, physical(user, 3)),
        )
        for user in range(USERS)
    )


def state(branch: str, offset: int) -> np.ndarray:
    shift = 0.0 if offset == 0 or branch == "reference" else 10.0
    return np.asarray(
        [[shift + offset, user, 0.5] for user in range(USERS)],
        dtype=np.float32,
    )


def step(branch: str, offset: int):
    main_actions = (2, 2)
    main_physical = tuple(physical(user, 2) for user in range(USERS))
    actions = list(main_actions)
    physical_actions = list(main_physical)
    if branch == "candidate" and offset < C2.HOLD_STEPS:
        actions[FOCAL] = 3
        physical_actions[FOCAL] = physical(FOCAL, 3)
    rewards = [[1.0, 0.0, -1.0] for _ in range(USERS)]
    if branch == "reference" or offset == C2.HOLD_STEPS:
        rewards[FOCAL][1] = -0.5
    return FORECAST.ForecastStepPayload(
        offset=offset,
        state_matrix=state(branch, offset),
        mask_matrix=mask(),
        action_bindings_by_user=bindings(),
        detached_main_actions=main_actions,
        detached_main_physical_actions=main_physical,
        executed_actions=tuple(actions),
        executed_physical_actions=tuple(physical_actions),
        reward_matrix=tuple(tuple(row) for row in rewards),
        served=(True, True),
        link_rate_bps=(10.0, 10.0),
        system_power_w=100.0 if branch == "reference" else 90.0,
        active_physical_ids=(physical(0, 2), physical(1, 2)),
        next_state_matrix=state(branch, offset + 1),
        next_mask_matrix=mask(),
        done=False,
    )


def build(anchor, live_rng):
    source = FORECAST.ForecastSourcePayload(
        anchor_payload=anchor,
        reference_checkpoint_sha256=digest("checkpoint"),
        environment_source_sha256=digest("environment"),
        reward_source_sha256=digest("reward"),
        live_rng_state=live_rng,
        forecast_rng_state={"state": 999, "inc": 31},
        forecast_namespace="c2-v03/chronology-test",
        adapter_version="chronology-fixture-v1",
    )
    return FORECAST.build_authoritative_forecast(
        source,
        focal_user=FOCAL,
        user_count=USERS,
        pre_active_physical_ids=(physical(0, 2), physical(1, 2)),
        reference_trace=tuple(step("reference", offset) for offset in range(4)),
        candidate_trace=tuple(step("candidate", offset) for offset in range(4)),
    )


class Clock:
    def __init__(self):
        self.value = 0

    def __call__(self):
        self.value += 1
        return self.value


def test_forecast_precedes_live_step_and_live_rng_may_advance_only_in_executor():
    anchor = {"episode": 3, "step": 4}
    live = {"state": 111, "inc": 7}
    gate = CHRONOLOGY.PreoutcomeForecastGate(
        anchor_payload=anchor,
        live_rng_state=lambda: live,
        clock_ns=Clock(),
    )

    result = gate.run_forecast(build)
    assert gate.phase == "forecast_complete"

    def execute():
        live["state"] = 112
        return "outcome"

    outcome, receipt = gate.run_live_step(execute)
    assert outcome == "outcome"
    assert gate.phase == "closed"
    assert receipt.option_id == result.certificate.option_id
    assert receipt.live_rng_before_sha256 == receipt.live_rng_after_forecast_sha256
    assert receipt.forecast_completed_ns < receipt.live_step_started_ns
    assert receipt.forecast_sequence[-1] == "live_step_completed"


def test_forecast_that_advances_live_rng_fails_closed():
    anchor = {"episode": 3, "step": 4}
    live = {"state": 111, "inc": 7}
    gate = CHRONOLOGY.PreoutcomeForecastGate(
        anchor_payload=anchor, live_rng_state=lambda: live
    )

    def leaking(anchor_payload, live_state):
        result = build(anchor_payload, live_state)
        live["state"] += 1
        return result

    with pytest.raises(CHRONOLOGY.C2ChronologyError, match="advanced"):
        gate.run_forecast(leaking)
    assert gate.phase == "failed"
    with pytest.raises(CHRONOLOGY.C2ChronologyError):
        gate.run_live_step(lambda: None)


def test_live_step_before_forecast_and_all_reuse_are_rejected():
    anchor = {"episode": 3, "step": 4}
    live = {"state": 111, "inc": 7}
    gate = CHRONOLOGY.PreoutcomeForecastGate(
        anchor_payload=anchor, live_rng_state=lambda: live
    )
    with pytest.raises(CHRONOLOGY.C2ChronologyError, match="requires"):
        gate.run_live_step(lambda: None)
    gate.run_forecast(build)
    with pytest.raises(CHRONOLOGY.C2ChronologyError, match="exactly once"):
        gate.run_forecast(build)
    gate.run_live_step(lambda: None)
    with pytest.raises(CHRONOLOGY.C2ChronologyError, match="requires"):
        gate.run_live_step(lambda: None)


def test_forecast_authority_must_bind_captured_anchor_and_live_rng():
    anchor = {"episode": 3, "step": 4}
    live = {"state": 111, "inc": 7}
    gate = CHRONOLOGY.PreoutcomeForecastGate(
        anchor_payload=anchor, live_rng_state=lambda: live
    )
    with pytest.raises(CHRONOLOGY.C2ChronologyError, match="captured live RNG"):
        gate.run_forecast(
            lambda anchor_payload, _live: build(
                anchor_payload, {"state": 333, "inc": 7}
            )
        )
    assert gate.phase == "failed"


def test_callback_exceptions_leave_the_gate_failed_and_unreusable():
    anchor = {"episode": 3, "step": 4}
    live = {"state": 111, "inc": 7}
    forecast_gate = CHRONOLOGY.PreoutcomeForecastGate(
        anchor_payload=anchor, live_rng_state=lambda: live
    )

    def bad_forecast(_anchor, _rng):
        raise RuntimeError("forecast failed")

    with pytest.raises(RuntimeError, match="forecast failed"):
        forecast_gate.run_forecast(bad_forecast)
    assert forecast_gate.phase == "failed"

    live_gate = CHRONOLOGY.PreoutcomeForecastGate(
        anchor_payload=anchor, live_rng_state=lambda: live
    )
    live_gate.run_forecast(build)

    def bad_live():
        raise RuntimeError("live failed")

    with pytest.raises(RuntimeError, match="live failed"):
        live_gate.run_live_step(bad_live)
    assert live_gate.phase == "failed"
