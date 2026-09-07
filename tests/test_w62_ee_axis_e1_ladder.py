"""W-62 -- validation-only E1 update ladder and common-rung selection."""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.algorithms.ee_axis_pairwise import (
    EEAxisPairBatch,
    EEAxisPairwiseConfig,
)
import mcrl.runtime.ee_axis_e1_ladder as ladder
from mcrl.runtime.ee_axis_e1_ladder import (
    E1LadderBatches,
    E1LadderError,
    E1LadderSpec,
    learner_config_sha256,
    pair_batch_digest,
    run_e1_validation_ladder,
    select_common_validation_rung,
)


def _batch(*, validation: bool) -> EEAxisPairBatch:
    states = np.asarray(
        [
            [0.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0],
            [1.0, 1.0, 0.0, 0.0],
        ],
        dtype=np.float32,
    )
    reference = np.asarray([0, 0, 1, 2], dtype=np.int64)
    candidate = np.asarray([1, 2, 2, 0], dtype=np.int64)
    targets = np.asarray(
        [1.5, 1.0, 1.5, -1.0] if validation else [1.0, 2.0, 1.0, -2.0],
        dtype=np.float64,
    )
    return EEAxisPairBatch(
        states=states,
        reference_actions=reference,
        candidate_actions=candidate,
        target_surplus_bits=targets,
        action_masks=np.ones((4, 3), dtype=np.bool_),
    )


def _batches() -> E1LadderBatches:
    train = _batch(validation=False)
    validation = _batch(validation=True)
    return E1LadderBatches(
        train=(train, train, train),
        validation=(validation, validation, validation),
    )


def _config() -> EEAxisPairwiseConfig:
    return EEAxisPairwiseConfig(
        state_dim=4,
        action_dim=3,
        hidden_layers=(5,),
        activation="tanh",
        learning_rate=0.01,
        kappa_bits=1.0,
        beta=0.01,
        loss_weights=(1.0, 1.0, 1.0),
    )


def _spec(*, run_id: str = "unit-e1", update_rungs=(10, 100, 1_000, 10_000)) -> E1LadderSpec:
    batches = _batches()
    digests = batches.digests()
    return E1LadderSpec(
        run_id=run_id,
        initialization_seeds=(11, 22, 33),
        source_prereg_sha256="a" * 64,
        source_manifest_sha256="b" * 64,
        checkpoint_sha256="c" * 64,
        source_receipt_file_sha256="e" * 64,
        ladder_index_file_sha256="d" * 64,
        learner_config_sha256=learner_config_sha256(_config()),
        train_source_seeds=(101, 102, 103),
        validation_source_seeds=(104,),
        train_batch_sha256s=tuple(
            digests["train"][route] for route in ("C1", "C2", "C3")
        ),
        validation_batch_sha256s=tuple(
            digests["validation"][route] for route in ("C1", "C2", "C3")
        ),
        update_rungs=update_rungs,
    )


def _receipt(rung_values: dict[int, float]) -> dict[int, dict[int, dict[str, dict[str, float]]]]:
    return {
        seed: {
            rung: {
                route: {"model_to_action_only_mae_ratio": value}
                for route in ("C1", "C2", "C3")
            }
            for rung, value in rung_values.items()
        }
        for seed in (11, 22, 33)
    }


def test_common_rung_uses_validation_mean_and_breaks_exact_tie_smaller() -> None:
    receipts = _receipt({10: 0.8, 100: 0.4, 1_000: 0.4, 10_000: 0.7})
    selected, means = select_common_validation_rung(
        receipts,
        expected_initialization_seeds=(11, 22, 33),
    )
    assert selected == 100
    assert means[100] == pytest.approx(0.4)


def test_ladder_spec_rejects_any_unsealed_schedule() -> None:
    with pytest.raises(E1LadderError, match="sealed ladder"):
        _spec(run_id="bad", update_rungs=(1, 2, 3, 4)).verify()
    with pytest.raises(E1LadderError, match="distinct"):
        bad = _spec(run_id="bad")
        E1LadderSpec(
            **{**bad.__dict__, "initialization_seeds": (11, 11, 33)}
        ).verify()


def test_batch_digest_changes_when_one_target_changes() -> None:
    first = _batch(validation=False)
    second = _batch(validation=False)
    second.target_surplus_bits[0] += 1.0
    assert pair_batch_digest(first) != pair_batch_digest(second)


def test_ladder_rejects_identical_train_validation_and_config_drift(tmp_path) -> None:
    train = _batch(validation=False)
    identical = E1LadderBatches(
        train=(train, train, train),
        validation=(train, train, train),
    )
    with pytest.raises(E1LadderError, match="identical"):
        identical.verify(_config())

    config = _config()
    drifted = EEAxisPairwiseConfig(
        **{**config.__dict__, "learning_rate": 0.02}
    )
    with pytest.raises(E1LadderError, match="config disagrees"):
        run_e1_validation_ladder(
            config=drifted,
            batches=_batches(),
            spec=_spec(),
            output_dir=tmp_path / "drifted",
        )


def test_runner_never_receives_test_or_ee_and_writes_rung_checkpoints(
    tmp_path, monkeypatch
) -> None:
    # Exercise the complete write-once runner with a tiny sealed ladder.  The
    # production constant remains 10/100/1000/10000; only this unit-test module
    # changes the contract constant before constructing its spec.
    monkeypatch.setattr(ladder, "E1_UPDATE_RUNGS", (1, 2))
    spec = _spec(update_rungs=(1, 2))
    output = tmp_path / "e1"
    result = run_e1_validation_ladder(
        config=_config(),
        batches=_batches(),
        spec=spec,
        output_dir=output,
    )
    assert result["status"] == "complete"
    assert result["selected_common_rung"] in {1, 2}
    assert result["test_split_opened"] is False
    assert result["held_out_ee_evaluated"] is False
    assert len(list((output / "checkpoints").glob("*.pt"))) == 6
    with pytest.raises(E1LadderError, match="already exists"):
        run_e1_validation_ladder(
            config=_config(),
            batches=_batches(),
            spec=spec,
            output_dir=output,
        )
