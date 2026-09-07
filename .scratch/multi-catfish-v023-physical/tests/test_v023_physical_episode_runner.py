"""Fast contract tests for the V0.23 fixed-policy physical seam.

The episode test replaces only the expensive TLE construction and physical
encoders with typed deterministic fixtures.  The production module still
requires a real ``TrainerEnvironment`` and uses the native encoders by
default; this keeps the one-episode receipt/checkpoint boundary checkable in
CI without opening a server launch.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest


REPO = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO / ".scratch" / "multi-catfish-v023-physical" / "v023_physical_episode_runner.py"
SPEC = importlib.util.spec_from_file_location("mcrl_v023_physical_episode_runner", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


@pytest.fixture(scope="module")
def frozen() -> module.FrozenV020Q12:
    return module.load_v020_q12()


def test_authenticated_v020_merge_is_current_and_frozen(frozen: module.FrozenV020Q12) -> None:
    assert frozen.binding.lineage == module.LINEAGE == 2026092101
    assert frozen.binding.checkpoint_sha256 == module.V020_CHECKPOINT_SHA256
    assert frozen.binding.q1_update_count == 10
    assert frozen.binding.q2_update_count == 3000
    assert frozen.binding.q2_initialization == 2026108101
    assert all(not parameter.requires_grad for parameter in frozen.q1.parameters())
    assert all(not parameter.requires_grad for parameter in frozen.q2.parameters())


@dataclass
class _Native:
    state_matrix: np.ndarray
    action_masks: np.ndarray


class _Outcome:
    def __init__(self, observation: object, *, done: bool) -> None:
        self.observation = observation
        self.done = done
        self.link_rate_bps = np.full(module.USERS, 2.5e6, dtype=np.float64)
        self.system_power_w = 25.0
        self.resolution = SimpleNamespace(served_count=module.USERS)


class _TypedTrainerEnvironment(module.TrainerEnvironment):
    """Small typed facade exercising the adapter's TrainerEnvironment seam."""

    def __init__(self, *_args: object) -> None:
        self.environment = SimpleNamespace(
            _fading_field=None,
            driver=SimpleNamespace(
                config=SimpleNamespace(
                    ephemeris=SimpleNamespace(time_step_s=1.0),
                ),
            ),
        )
        self.config = SimpleNamespace(num_users=module.USERS, steps_per_episode=module.STEPS)
        self._last_outcome: _Outcome | None = None
        self._steps = 0
        self.restored_state: object | None = None

    def reset(self, *_args: object) -> tuple[list[object], list[object], object]:
        self._steps = 0
        self._last_outcome = None
        observation = SimpleNamespace(num_users=module.USERS)
        return [object()] * module.USERS, [object()] * module.USERS, observation

    def step(self, _actions: np.ndarray, _env_rng: np.random.Generator) -> object:
        self._steps += 1
        observation = SimpleNamespace(num_users=module.USERS)
        self._last_outcome = _Outcome(observation, done=self._steps == module.STEPS)
        return SimpleNamespace(done=self._steps == module.STEPS)

    @property
    def last_outcome(self) -> _Outcome:
        assert self._last_outcome is not None
        return self._last_outcome

    def training_state_dict(self) -> dict[str, object]:
        return {"format_version": 1, "age_rng_state": None}

    def load_training_state_dict(self, state: object) -> None:
        self.restored_state = state


@pytest.fixture
def physical_fixtures(monkeypatch: pytest.MonkeyPatch) -> None:
    state = np.zeros((module.USERS, 228), dtype=np.float32)
    masks = np.ones((module.USERS, 28), dtype=np.bool_)
    q2_state = SimpleNamespace(
        state_matrix=np.zeros((module.USERS, 16 * 28), dtype=np.float32),
        action_masks=masks.copy(),
        verify=lambda: None,
    )
    monkeypatch.setattr(module, "encode_ee_axis_state", lambda _env, _obs: _Native(state, masks))
    monkeypatch.setattr(module, "snapshot_ops3_anchor", lambda _env, _obs: object())
    monkeypatch.setattr(module, "project_ops3_anchor", lambda _anchor: object())
    monkeypatch.setattr(module, "build_ops3_live_surfaces", lambda *_args: [object()])
    monkeypatch.setattr(module, "encode_ee_axis_v014_q2_states", lambda _surfaces: q2_state)


def test_one_episode_paired_evaluation_is_finite_and_pooled(
    frozen: module.FrozenV020Q12,
    physical_fixtures: None,
) -> None:
    adapter = module.V023PhysicalEpisodeAdapter(
        frozen=frozen,
        archive=object(),
        environment_factory=lambda _archive, _users: _TypedTrainerEnvironment(),
        rng_factory=lambda seed: (
            np.random.default_rng(seed),
            np.random.default_rng(seed + 1),
        ),
    )
    world = module.make_world_binding(episode_index=1, world_seed=2026121501)
    baseline = adapter.run_episode(arm="BASELINE", world=world)
    drop_c3 = adapter.run_episode(arm="DROP_C3", world=world)

    assert baseline.status == drop_c3.status == module.STATUS
    assert baseline.split == drop_c3.split == "EVALUATION_DEVELOPMENT"
    assert baseline.initial_world_sha256 == drop_c3.initial_world_sha256
    assert baseline.field_root_digest == drop_c3.field_root_digest == world.field_root_digest
    assert baseline.action_trace_sha256 == drop_c3.action_trace_sha256
    assert baseline.q3_evaluated is False
    assert baseline.total_energy_j > 0.0
    assert baseline.ratio_of_sums_ee_bits_per_j == pytest.approx(
        baseline.total_bits / baseline.total_energy_j,
        abs=1e-12,
    )
    pooled = module.pool_receipts((baseline,), arm="BASELINE")
    pooled_drop = module.pool_receipts((drop_c3,), arm="DROP_C3")
    assert pooled["ratio_of_sums_ee_bits_per_j"] == pytest.approx(
        baseline.total_bits / baseline.total_energy_j, abs=1e-12
    )
    assert pooled_drop["ratio_of_sums_ee_bits_per_j"] == pytest.approx(
        drop_c3.total_bits / drop_c3.total_energy_j, abs=1e-12
    )


def test_plan_requires_complete_checkpoint_blocks() -> None:
    world = module.make_world_binding(episode_index=1, world_seed=2026121501)
    with pytest.raises(module.V023PhysicalError, match="100-episode checkpoint blocks"):
        module.V023EpisodePlan(worlds=(world,)).verify(
            checkpoint=module.V020CheckpointBinding()
        )
    module.V023EpisodePlan(worlds=(world,), integration_only=True).verify(
        checkpoint=module.V020CheckpointBinding()
    )


def test_checkpoint_binding_fails_closed_on_hash_drift(tmp_path: Path) -> None:
    bad = module.V020CheckpointBinding(
        checkpoint_path=tmp_path / "not-the-checkpoint.pt",
        checkpoint_sha256="0" * 64,
    )
    with pytest.raises(module.V023PhysicalError, match="current V0.20 lineage"):
        bad.verify_files()


class _StubEvaluationAdapter:
    """Deterministic adapter used only to exercise runner persistence."""

    def __init__(self, frozen: module.FrozenV020Q12) -> None:
        self.frozen = frozen
        self._states: dict[str, dict[str, object] | None] = {
            arm: None for arm in module.ARMS
        }

    def resume_state_for(self, arm: str) -> dict[str, object] | None:
        return self._states[arm]

    def restore_resume_states(self, states: object) -> None:
        assert isinstance(states, dict)
        self._states = {
            arm: dict(states[arm]) if isinstance(states[arm], dict) else None
            for arm in module.ARMS
        }

    def run_episode(
        self,
        *,
        arm: str,
        world: module.V023WorldBinding,
        resume_state: object = None,
    ) -> module.V023EpisodeReceipt:
        expected_previous = world.episode_index - 1
        if expected_previous == 0:
            assert resume_state is None
        else:
            assert isinstance(resume_state, dict)
            assert resume_state["episode_index"] == expected_previous
        trace = module.canonical_sha256(
            {"world_seed": world.world_seed, "action": [7] * module.USERS}
        )
        initial = module.canonical_sha256(
            {"world_id": world.world_id, "world_seed": world.world_seed}
        )
        total_bits = float(1000 + world.episode_index)
        total_energy = float(10 + world.episode_index)
        row = module.V023EpisodeReceipt(
            schema=module.RECEIPT_SCHEMA,
            status=module.STATUS,
            split=module.EVALUATION_SPLIT,
            arm=arm,
            episode_index=world.episode_index,
            world_id=world.world_id,
            world_seed=world.world_seed,
            users=module.USERS,
            steps=module.STEPS,
            decision_interval_s=1.0,
            total_bits=total_bits,
            total_energy_j=total_energy,
            ratio_of_sums_ee_bits_per_j=total_bits / total_energy,
            served_user_steps=module.USERS * module.STEPS,
            service_opportunities=module.USERS * module.STEPS,
            service_fraction=1.0,
            initial_world_sha256=initial,
            field_component=module.FIELD_COMPONENT,
            field_root_digest=world.field_root_digest,
            action_trace_sha256=trace,
            checkpoint_binding=self.frozen.binding.as_dict(),
            q1_parameter_sha256=self.frozen.q1_parameter_sha256,
            q2_parameter_sha256=self.frozen.q2_parameter_sha256,
            q3_evaluated=False,
            test_split_opened=False,
            episode_training=False,
            learner_update=False,
        )
        row.verify()
        self._states[arm] = {
            "schema": f"{module.SCHEMA}-resume-state",
            "arm": arm,
            "episode_index": world.episode_index,
            "world_id": world.world_id,
            "world_seed": world.world_seed,
            "field_root_digest": world.field_root_digest,
            "environment_training_state": {"format_version": 1},
            "rng_states": [{"world_seed": world.world_seed}],
            "q1_parameter_sha256": self.frozen.q1_parameter_sha256,
            "q2_parameter_sha256": self.frozen.q2_parameter_sha256,
            "torch_rng_state": None,
        }
        return row


def test_checkpoint_resume_is_deterministic_and_complete(
    frozen: module.FrozenV020Q12, tmp_path: Path
) -> None:
    worlds = tuple(
        module.make_world_binding(
            episode_index=index, world_seed=2026121500 + index
        )
        for index in range(1, 201)
    )
    plan = module.V023EpisodePlan(worlds=worlds)

    interrupted_dir = tmp_path / "interrupted"
    first = module.V023PhysicalEpisodeRunner(
        adapter=_StubEvaluationAdapter(frozen), plan=plan
    ).run(output_dir=interrupted_dir, stop_after=100)
    checkpoint = interrupted_dir / "checkpoints" / "checkpoint-000100.json"
    assert first["completed_episode"] == 100
    assert checkpoint.is_file()

    resumed = module.V023PhysicalEpisodeRunner(
        adapter=_StubEvaluationAdapter(frozen), plan=plan
    ).run(output_dir=interrupted_dir, resume_checkpoint=checkpoint)
    uninterrupted = module.V023PhysicalEpisodeRunner(
        adapter=_StubEvaluationAdapter(frozen), plan=plan
    ).run(output_dir=tmp_path / "uninterrupted")
    assert resumed == uninterrupted
    assert resumed["completed_episode"] == 200
    assert resumed["receipt_count"] == 400
    assert resumed["checkpoints"] == [
        "checkpoints/checkpoint-000100.json",
        "checkpoints/checkpoint-000200.json",
    ]


def test_drop_c3_only_runner_emits_no_baseline_artifact(
    frozen: module.FrozenV020Q12, tmp_path: Path
) -> None:
    worlds = tuple(
        module.make_world_binding(
            episode_index=index, world_seed=2026090600 + index
        )
        for index in range(1, 101)
    )
    plan = module.V023EpisodePlan(
        worlds=worlds,
        arms=module.DROP_C3_ONLY_ARMS,
    )
    result = module.V023PhysicalEpisodeRunner(
        adapter=_StubEvaluationAdapter(frozen), plan=plan
    ).run(output_dir=tmp_path / "drop-c3")
    assert result["arms"] == ["DROP_C3"]
    assert result["receipt_count"] == 100
    assert result["baseline_artifact_emitted"] is False
    assert result["between_arm_comparison_performed"] is False
    assert (tmp_path / "drop-c3" / "result.json").is_file()
    assert (tmp_path / "drop-c3" / "checkpoints" / "checkpoint-000100.json").is_file()
