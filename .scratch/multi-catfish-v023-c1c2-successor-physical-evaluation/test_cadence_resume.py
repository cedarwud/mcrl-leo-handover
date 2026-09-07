from __future__ import annotations

from pathlib import Path
import sys

import pytest


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import build_v023_c1c2_successor_world_plan as builder
import v023_c1c2_successor_physical_runner as runner


def _plan() -> runner.EvaluationPlan:
    payload = builder.build_world_plan()
    return runner.EvaluationPlan(
        worlds=tuple(runner.WorldBinding(**row) for row in payload["worlds"]),
        plan_sha256=payload["plan_sha256"],
    )


class _StubEvaluationAdapter:
    """The predecessor runner's deterministic persistence helper, generalized."""

    def __init__(self) -> None:
        self._bindings = {
            arm: {
                "arm": arm,
                "routes": [] if arm == "BASELINE" else ["C1", "C2"],
                "checkpoint_sha256": runner.canonical_sha256({"arm": arm}),
                "fixed_policy": True,
            }
            for arm in runner.ARMS
        }
        self._states: dict[str, dict[str, object] | None] = {
            arm: None for arm in runner.ARMS
        }

    @property
    def policy_bindings(self):
        return self._bindings

    def resume_state_for(self, arm: str):
        return self._states[arm]

    def restore_resume_states(self, states):
        assert set(states) == set(runner.ARMS)
        self._states = {arm: dict(states[arm]) for arm in runner.ARMS}

    def run_episode(self, *, arm, world, plan_sha256, resume_state=None):
        previous = world.episode_index - 1
        if previous == 0:
            assert resume_state is None
        else:
            assert resume_state["episode_index"] == previous
            assert resume_state["plan_sha256"] == plan_sha256
        arm_offset = runner.ARMS.index(arm)
        total_bits = float(10_000 + 100 * (3 - arm_offset) + world.episode_index)
        total_energy = 10.0
        receipt = runner.EpisodeReceipt(
            schema=runner.RECEIPT_SCHEMA,
            status=runner.STATUS,
            split=runner.SPLIT,
            arm=arm,
            routes=() if arm == "BASELINE" else runner.ROUTES,
            episode_index=world.episode_index,
            world_id=world.world_id,
            world_seed=world.world_seed,
            users=runner.USERS,
            steps=runner.STEPS,
            decision_interval_s=1.0,
            total_bits=total_bits,
            total_energy_j=total_energy,
            ratio_of_sums_ee_bits_per_j=total_bits / total_energy,
            served_user_steps=runner.USERS * runner.STEPS,
            service_opportunities=runner.USERS * runner.STEPS,
            service_fraction=1.0,
            initial_world_sha256=runner.canonical_sha256(
                {"world_id": world.world_id, "world_seed": world.world_seed}
            ),
            field_component=runner.FIELD_COMPONENT,
            field_root_digest=world.field_root_digest,
            action_trace_sha256=runner.canonical_sha256(
                {"arm": arm, "episode": world.episode_index}
            ),
            plan_sha256=plan_sha256,
            policy_binding=self._bindings[arm],
        )
        receipt.verify()
        self._states[arm] = {
            "arm": arm,
            "episode_index": world.episode_index,
            "plan_sha256": plan_sha256,
        }
        return receipt


def test_checkpoint_and_rung_cadence_resume_100_to_500(tmp_path: Path) -> None:
    plan = _plan()
    output = tmp_path / "run"
    first = runner.FixedPolicyEvaluationRunner(
        adapter=_StubEvaluationAdapter(), plan=plan
    ).run(output_dir=output, pause_at=100)
    assert first["completed_episode"] == 100
    assert first["terminal_result_emitted"] is False
    assert not (output / "result.json").exists()
    checkpoint = output / "checkpoints" / "checkpoint-000100.json"
    assert checkpoint.is_file()
    assert (output / "rungs" / "rung-000100.json").is_file()

    resumed = runner.FixedPolicyEvaluationRunner(
        adapter=_StubEvaluationAdapter(), plan=plan
    ).run(output_dir=output, pause_at=500, resume_checkpoint=checkpoint)
    assert resumed["completed_episode"] == 500
    assert resumed["receipt_count"] == 500 * len(runner.ARMS)
    assert resumed["terminal_result_emitted"] is False
    assert not (output / "result.json").exists()
    assert [path.name for path in sorted((output / "checkpoints").glob("*.json"))] == [
        f"checkpoint-{index:06d}.json" for index in range(100, 501, 100)
    ]
    assert [path.name for path in sorted((output / "rungs").glob("*.json"))] == [
        f"rung-{index:06d}.json" for index in range(100, 501, 100)
    ]


def test_resume_rejects_non_cadence_checkpoint_payload() -> None:
    plan = _plan()
    evaluation = runner.FixedPolicyEvaluationRunner(
        adapter=_StubEvaluationAdapter(), plan=plan
    )
    payload = evaluation._checkpoint_payload(100, [])
    payload["completed_episode"] = 101
    with pytest.raises(runner.C1C2PhysicalError, match="100-episode cadence"):
        evaluation._validate_resume(payload)


def test_resume_rejects_root_with_terminal_result(tmp_path: Path) -> None:
    plan = _plan()
    output = tmp_path / "terminal"
    output.mkdir()
    (output / "result.json").write_text("{}", encoding="ascii")
    with pytest.raises(runner.C1C2PhysicalError, match="terminal result"):
        runner.FixedPolicyEvaluationRunner(
            adapter=_StubEvaluationAdapter(), plan=plan
        ).run(
            output_dir=output,
            pause_at=500,
            resume_checkpoint=output / "checkpoints" / "checkpoint-000100.json",
        )
    assert not (output / "integrity-stop.json").exists()


def test_9000_terminal_requires_later_authority() -> None:
    plan = _plan()
    with pytest.raises(runner.C1C2PhysicalError, match="continuation_authority"):
        runner.FixedPolicyEvaluationRunner(
            adapter=_StubEvaluationAdapter(),
            plan=plan,
            terminal_boundary=9000,
        )
