from __future__ import annotations

from fractions import Fraction
import hashlib
import json
from types import SimpleNamespace

import numpy as np
import pytest

import run_v023_c3s_shadow_replay as shadow


# Synthetic fixture only: two users make purity/replay tests small and deterministic.
FIXTURE_USERS = 2
# Synthetic fixture only: two actions exercise a real BASE/counterfactual difference.
FIXTURE_ACTIONS = 2
# Synthetic fixture only: three steps exercise state advancement without heavy compute.
FIXTURE_HORIZON = 3


class FakeStepEnvironment:
    def __init__(self, horizon: int = FIXTURE_HORIZON) -> None:
        self.horizon = horizon
        self.step_index = 0
        # Synthetic fixture interval; one second makes bits/power arithmetic transparent.
        interval_s = 1.0
        self.driver = SimpleNamespace(
            config=SimpleNamespace(ephemeris=SimpleNamespace(time_step_s=interval_s)),
        )

    def observation(self) -> SimpleNamespace:
        return SimpleNamespace(
            step_index=self.step_index,
            masks=np.ones((FIXTURE_USERS, FIXTURE_ACTIONS), dtype=np.bool_),
        )

    def step(self, actions: np.ndarray, _rng: np.random.Generator) -> SimpleNamespace:
        selected = np.asarray(actions, dtype=np.int64)
        # Synthetic fixture physics: action one trades one bit for one watt.
        rates = np.asarray([10.0 - float(value) for value in selected], dtype=np.float64)
        power = 2.0 + float(np.sum(selected))
        self.step_index += 1
        return SimpleNamespace(
            link_rate_bps=rates,
            system_power_w=power,
            resolution=SimpleNamespace(served_count=FIXTURE_USERS),
            done=self.step_index == self.horizon,
            observation=self.observation(),
        )


class FakeTrainerEnvironment:
    def __init__(self, horizon: int = FIXTURE_HORIZON) -> None:
        self.environment = FakeStepEnvironment(horizon)
        self.last_outcome: SimpleNamespace | None = None

    def reset(
        self, _env_rng: np.random.Generator, _mobility_rng: np.random.Generator,
    ) -> tuple[None, None, SimpleNamespace]:
        self.environment.step_index = 0
        return None, None, self.environment.observation()

    def step(self, actions: np.ndarray, rng: np.random.Generator) -> SimpleNamespace:
        self.last_outcome = self.environment.step(actions, rng)
        return self.last_outcome


def state_digest(step_env: FakeStepEnvironment, observation: SimpleNamespace) -> str:
    encoded = json.dumps(
        {"environment_step": step_env.step_index, "observation_step": observation.step_index},
        sort_keys=True,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def decision(
    _step_env: FakeStepEnvironment, observation: SimpleNamespace,
    _rng: np.random.Generator,
) -> shadow.ShadowDecision:
    base = np.zeros(FIXTURE_USERS, dtype=np.int64)
    committed = base.copy()
    committed[observation.step_index % FIXTURE_USERS] = 1
    # These nominal fixture values are deliberately distinct from realised physics.
    nominal_base = {
        "total_bits": 20.0, "total_energy_j": 2.0,
        "served": FIXTURE_USERS, "opportunities": FIXTURE_USERS,
    }
    nominal_committed = {
        "total_bits": 19.5, "total_energy_j": 2.5,
        "served": FIXTURE_USERS, "opportunities": FIXTURE_USERS,
    }
    return shadow.ShadowDecision(
        committed_actions=committed, base_actions=base,
        selected_profile_id=f"U:{observation.step_index}:1",
        nominal_committed=nominal_committed, nominal_base=nominal_base,
    )


def test_shadow_evaluation_does_not_change_live_environment_or_rng() -> None:
    step_env = FakeStepEnvironment()
    # Synthetic RNG seed is arbitrary and outcome-independent.
    rng = np.random.default_rng(71)
    before = shadow.v1policy._structural_sha256((step_env, rng))
    metric, recorded = shadow.shadow_evaluate_without_commit(
        step_env, np.zeros(FIXTURE_USERS, dtype=np.int64), rng,
        interval_s=1.0, expected_users=FIXTURE_USERS,
    )
    after = shadow.v1policy._structural_sha256((step_env, rng))
    assert recorded == before == after
    assert step_env.step_index == 0
    assert metric == {
        "bits_hex": (20.0).hex(), "energy_j_hex": (2.0).hex(),
        "served": FIXTURE_USERS, "opportunities": FIXTURE_USERS,
    }


def test_decomposition_identity_is_exact_in_fractions() -> None:
    def metric(bits: float, energy: float) -> dict[str, object]:
        return {
            "bits_hex": bits.hex(), "energy_j_hex": energy.hex(),
            "served": FIXTURE_USERS, "opportunities": FIXTURE_USERS,
        }

    # Synthetic accounting fixture: chosen, same-state BASE, trajectory BASE.
    result = shadow.decomposition(
        committed=[metric(15.0, 2.0), metric(12.0, 2.0)],
        same_state_base=[metric(13.0, 2.0), metric(11.0, 2.0)],
        trajectory_base=[metric(10.0, 2.0), metric(9.0, 2.0)],
        eta=Fraction(2),
    )
    immediate = shadow._fraction_payload(result["a_immediate_same_state"], field="a")
    remainder = shadow._fraction_payload(result["b_visited_state_remainder"], field="b")
    total = shadow._fraction_payload(result["total_arm_minus_base_trajectory"], field="total")
    assert immediate == 3
    assert remainder == 5
    assert immediate + remainder == total == 8
    assert result["identity_exact"] is True


def test_tiny_shadow_replay_is_bit_identical_to_archived_trajectory() -> None:
    # Synthetic RNG seeds are fixed test provenance, not scientific panel seeds.
    replay = shadow.run_shadow_trajectory(
        environment=FakeTrainerEnvironment(),
        env_rng=np.random.default_rng(101), mobility_rng=np.random.default_rng(102),
        horizon=FIXTURE_HORIZON, decide=decision,
        expected_users=FIXTURE_USERS, digest_state=state_digest,
    )
    second = shadow.run_shadow_trajectory(
        environment=FakeTrainerEnvironment(),
        env_rng=np.random.default_rng(101), mobility_rng=np.random.default_rng(102),
        horizon=FIXTURE_HORIZON, decide=decision,
        expected_users=FIXTURE_USERS, digest_state=state_digest,
    )
    archived = {
        "arms": {
            "LITE": {
                "initial_state_sha256": replay["initial_state_sha256"],
                "action_trace_sha256": replay["action_trace_sha256"],
                "steps": replay["steps"],
            },
        },
    }
    shadow.assert_bit_identical_replay(second, archived, arm="LITE")
    assert second == replay
    assert all(not row["configuration_equals_base"] for row in replay["shadow_decisions"])


def test_initial_state_mismatch_is_refused() -> None:
    archived = {"arms": {"LITE": {"initial_state_sha256": "0" * 64}}}
    with pytest.raises(shadow.ShadowReplayError, match="initial_state_sha256 mismatches"):
        shadow.assert_initial_state_matches("1" * 64, archived, arm="LITE")


def test_screen_unit_must_match_terminal_path_and_digest(tmp_path) -> None:
    key = SimpleNamespace(as_dict=lambda: {"world": 1, "lineage": 2})
    unit_path = tmp_path / "unit.json"
    digest = "a" * 64
    terminal = {
        "unit_receipts": [{
            "unit": key.as_dict(), "path": str(unit_path), "sha256": digest,
        }],
    }
    shadow.assert_screen_unit_is_terminal_bound(
        terminal, key, {"path": str(unit_path), "sha256": digest},
    )
    with pytest.raises(shadow.ShadowReplayError, match="path/digest"):
        shadow.assert_screen_unit_is_terminal_bound(
            terminal, key, {"path": str(unit_path), "sha256": "b" * 64},
        )


def test_formal_cli_requires_preflight_and_launch_authority_flags() -> None:
    parser = shadow._parser()
    args = parser.parse_args(["--unit", f"{shadow.matrix.WORLDS[0]}:{shadow.matrix.LINEAGES[0]}"])
    assert args.preflight_manifest == shadow.DEFAULT_PREFLIGHT
    assert args.launch_authority is None
    assert args.screen_run is None
    assert args.arm == "LITE"
    assert "V-E" in shadow.COORDINATOR_ARMS
    assert parser.parse_args(["--dry-run", "--arm", "V-E"]).arm == "V-E"
