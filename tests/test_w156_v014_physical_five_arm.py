"""W-156 -- authenticated V0.14 physical five-arm adapter plumbing.

These tests use synthetic receipts and synthetic gate checkpoints only.  They
do not open the simulator, harvest source, train an episode, or open TEST.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest

torch = pytest.importorskip("torch")

from mcrl.algorithms.ee_axis_v014_head import (
    EEAxisV014HeadConfig,
    EEAxisV014PairwiseLearner,
)
from mcrl.env.keyed_fading import KeyedFadingField


REPO = Path(__file__).resolve().parents[1]
RUNNER_PATH = (
    REPO
    / ".scratch"
    / "multi-catfish-v014-learner"
    / "run_v014_physical_five_arm.py"
)
SPEC = importlib.util.spec_from_file_location("mcrl_v014_physical_w156", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


INIT_SEEDS = (101, 102, 103)
RUNG = 3


def _head_configs() -> tuple[EEAxisV014HeadConfig, EEAxisV014HeadConfig]:
    common = dict(
        action_dim=28,
        hidden_layers=(2,),
        activation="tanh",
        learning_rate=0.001,
        kappa_bits=100.0,
        beta=0.1,
    )
    return (
        EEAxisV014HeadConfig(local_feature_dim=16, global_feature_dim=0, **common),
        EEAxisV014HeadConfig(local_feature_dim=10, global_feature_dim=7, **common),
    )


def _write_gate_panel(tmp_path: Path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    q2_config, q3_config = _head_configs()
    checkpoint_paths: dict[int, Path] = {}
    checkpoint_hashes: dict[str, dict[str, str]] = {}
    for seed in INIT_SEEDS:
        q2 = EEAxisV014PairwiseLearner(q2_config, train_seed=seed)
        q3 = EEAxisV014PairwiseLearner(q3_config, train_seed=seed)
        payload = {
            "schema": RUNNER.GATE_CHECKPOINT_SCHEMA,
            "claim_ceiling": "NO_DEPLOYED_EFFICACY_OR_EE_CLAIM",
            "initialization_seed": seed,
            "update_rung": RUNG,
            "test_split_opened": False,
            "held_out_ee_evaluated": False,
            "episode_training": False,
            "q2": q2.checkpoint_state(update_count=RUNG),
            "q3": q3.checkpoint_state(update_count=RUNG),
        }
        path = tmp_path / f"init-{seed}-rung-{RUNG:06d}.pt"
        torch.save(payload, path)
        checkpoint_paths[seed] = path
        checkpoint_hashes[str(seed)] = {
            str(RUNG): RUNNER.file_sha256(path),
        }
    result = {
        "schema": RUNNER.GATE_RESULT_SCHEMA,
        "status": "PASS_LEARNABILITY_GATE",
        "claim_ceiling": "NO_DEPLOYED_EFFICACY_OR_EE_CLAIM",
        "authority_sha256": "a" * 64,
        "run_spec_sha256": "b" * 64,
        "selection": {
            "deployment_rung": RUNG,
            "common_joint_rung": RUNG,
            "q2_diagnostic_best_rung": RUNG,
            "q3_diagnostic_best_rung": RUNG,
        },
        "spec": {"initialization_seeds": list(INIT_SEEDS)},
        "checkpoint_file_sha256s": checkpoint_hashes,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "episode_training": False,
    }
    result_path = tmp_path / "result.json"
    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    result_sha = RUNNER.file_sha256(result_path)
    seal = {
        "schema": RUNNER.GATE_RESULT_SEAL_SCHEMA,
        "result_file_sha256": result_sha,
        "authority_sha256": result["authority_sha256"],
        "run_spec_sha256": result["run_spec_sha256"],
    }
    seal_path = tmp_path / "result-seal.json"
    seal_path.write_text(
        json.dumps(seal, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    seal_sha = RUNNER.file_sha256(seal_path)
    selection = RUNNER.authenticate_gate_selection(
        result_path=result_path,
        seal_path=seal_path,
        expected_result_sha256=result_sha,
        expected_seal_sha256=seal_sha,
        checkpoint_paths_by_initialization=checkpoint_paths,
        initialization_seeds=INIT_SEEDS,
    )
    return selection, result_sha, seal_sha


def test_gate_seal_reconstructs_independent_q2_q3_at_common_rung(tmp_path: Path) -> None:
    selection, result_sha, seal_sha = _write_gate_panel(tmp_path)
    assert selection.deployment_rung == RUNG
    assert selection.result_sha256 == result_sha
    assert selection.seal_sha256 == seal_sha
    assert tuple(selection.heads_by_initialization) == INIT_SEEDS
    for pair in selection.heads_by_initialization.values():
        assert pair.q2 is not pair.q3
        assert pair.update_rung == RUNG
        assert pair.q2.config.state_dim == 16 * 28
        assert pair.q3.config.state_dim == 10 * 28 + 7
        assert all(not parameter.requires_grad for parameter in pair.q2.q.parameters())
        assert all(not parameter.requires_grad for parameter in pair.q3.q.parameters())

    adapter = RUNNER.V014PhysicalAdapter(
        selection=selection,
        archive=object(),
        q1_loader=lambda _seed: (None, {}),
        make_environment=lambda _archive, _users: None,
        rng_factory=lambda _seed: (),
        kappa_bits=100.0,
    )
    field = adapter.field_for(
        field_component="W156_TEST_FIELD",
        evaluation_seed=2026109001,
    )
    assert field.root_digest == KeyedFadingField.from_components(
        "W156_TEST_FIELD", 2026109001
    ).root_digest


def test_physical_spec_requires_later_sealed_100_seed_panel() -> None:
    with pytest.raises(RUNNER.V014PhysicalRunnerError, match="2026109001"):
        RUNNER.V014PhysicalEvaluationSpec(
            evaluation_seeds=tuple(range(2026109001, 2026109100)),
            field_component="W156_TEST_FIELD",
            initialization_seeds=INIT_SEEDS,
        ).verify()
    spec = RUNNER.V014PhysicalEvaluationSpec(
        evaluation_seeds=RUNNER.REQUIRED_EVALUATION_SEEDS,
        field_component="W156_TEST_FIELD",
        initialization_seeds=INIT_SEEDS,
    )
    spec.verify()
    assert spec.episodes == 100


class _SyntheticAdapter:
    """Inference-only adapter stand-in for receipt/aggregation tests."""

    def __init__(self, selection):
        self.selection = selection
        self.fields: dict[int, object] = {}

    def field_for(self, *, field_component: str, evaluation_seed: int):
        field = KeyedFadingField.from_components(field_component, evaluation_seed)
        self.fields[evaluation_seed] = field
        return field

    def evaluate_route_episode(
        self,
        *,
        arm: str,
        episode_index: int,
        evaluation_seed: int,
        initialization_seed: int,
        field: object,
    ):
        # The synthetic values exercise pooled ratio-of-sums and retain all
        # three initialisations; they are not scientific outcome evidence.
        arm_offset = {"FULL": 4.0, "DROP_C1": 1.0, "DROP_C2": 2.0, "DROP_C3": 3.0}[arm]
        bits = 100.0 + arm_offset + initialization_seed / 1000.0
        receipt = RUNNER.V014EpisodeReceipt(
            arm=arm,
            episode_index=episode_index,
            evaluation_seed=evaluation_seed,
            total_bits=bits,
            total_energy_j=10.0,
            decision_count=1000,
            served_user_steps=1000,
            initialization_seed=initialization_seed,
            world_seed=evaluation_seed,
        )
        return RUNNER.V014PhysicalEpisode(
            receipt=receipt,
            provenance={
                "runner_schema": RUNNER.PHYSICAL_RUNNER_SCHEMA,
                "arm": arm,
                "initialization_seed": initialization_seed,
                "evaluation_seed": evaluation_seed,
                "field_root_digest": field.root_digest,
                "gate_result_sha256": self.selection.result_sha256,
                "gate_seal_sha256": self.selection.seal_sha256,
                "deployment_rung": self.selection.deployment_rung,
                "q2_checkpoint_sha256": self.selection.heads_by_initialization[
                    initialization_seed
                ].checkpoint_sha256,
                "q3_checkpoint_sha256": self.selection.heads_by_initialization[
                    initialization_seed
                ].checkpoint_sha256,
                "evaluation_split": "TRAIN",
                "test_split_opened": False,
                "held_out_ee_evaluated": False,
                "episode_training": False,
            },
        )


def test_prepare_run_verify_keeps_all_initialisations_and_writes_once(
    tmp_path: Path,
) -> None:
    selection, _result_sha, _seal_sha = _write_gate_panel(tmp_path / "gate")
    physical_dir = tmp_path / "physical"
    spec = RUNNER.V014PhysicalEvaluationSpec(
        evaluation_seeds=RUNNER.REQUIRED_EVALUATION_SEEDS,
        field_component="W156_TEST_FIELD",
        initialization_seeds=INIT_SEEDS,
    )
    prepared = RUNNER.prepare_physical_evaluation(
        output_dir=physical_dir,
        spec=spec,
        selection=selection,
    )
    assert prepared["schema"] == RUNNER.PREPARE_SCHEMA
    adapter = _SyntheticAdapter(selection)

    def main_episode_runner(*, episode_index: int, evaluation_seed: int, field: object):
        return RUNNER.V014EpisodeReceipt(
            arm="MAIN",
            episode_index=episode_index,
            evaluation_seed=evaluation_seed,
            total_bits=90.0,
            total_energy_j=10.0,
            decision_count=1000,
            served_user_steps=1000,
        )

    result = RUNNER.run_physical_evaluation(
        prepared_path=physical_dir / "prepare.json",
        adapter=adapter,
        main_episode_runner=main_episode_runner,
    )
    assert result["status"] == "COMPLETE_PLUMBING_ONLY"
    assert result["aggregate"]["arms"] == list(RUNNER.ARMS)
    assert result["aggregate"]["per_initialization"].keys() == {str(seed) for seed in INIT_SEEDS}
    assert result["checkpoint_file_sha256s"].keys() == set(RUNNER.ARMS)
    # Four route arms retain 100 episodes for each of three initialisations;
    # MAIN remains one independent paired row per evaluation seed.
    assert all(
        result["aggregate"]["summaries"][arm]["rows"] == 300
        for arm in RUNNER.ROUTE_ARMS
    )
    assert result["aggregate"]["summaries"]["MAIN"]["rows"] == 100
    verified = RUNNER.verify_physical_evaluation(physical_dir)
    assert verified["status"] == "PASS_PHYSICAL_PLUMBING_INTEGRITY"
    assert verified["ratio_of_sums_recomputed"] is True
    assert verified["efficacy_claim"] is False
    with pytest.raises(RUNNER.V014PhysicalRunnerError, match="overwrite"):
        RUNNER.verify_physical_evaluation(physical_dir)
