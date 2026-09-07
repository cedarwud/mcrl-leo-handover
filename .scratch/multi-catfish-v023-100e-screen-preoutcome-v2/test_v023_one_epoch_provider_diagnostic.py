"""Focused tests for the non-formal one-epoch provider plumbing diagnostic.

These tests use a synthetic deterministic provider so no sealed root, server,
simulator, TEST split, or scientific claim is involved.  The real-provider run
is a separate server command whose receipt is authenticated on its own.
"""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.algorithms.ee_axis_action_shared import EEAxisActionSharedConfig
from mcrl.algorithms.ee_axis_lcsrs_three_route import LCSRSThreeRouteConfig
from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch
from mcrl.algorithms.ee_axis_v014_head import (
    EEAxisV014HeadConfig,
    EEAxisV014NormalizedPairBatch,
)
from mcrl.runtime.ee_axis_lcsrs_c3_dataset import (
    LCSRS_DRAW_COUNT,
    LCSRS_ROW_REFERENCE,
    LCSRSPairTargets,
    assemble_lcsrs_anchor_surface,
)
from mcrl.runtime.ee_axis_lcsrs_c3_learner import LCSRSC3SampledBatch
from mcrl.runtime.ee_axis_lcsrs_c3_state import assemble_c3_view


HERE = Path(__file__).resolve().parent
SPEC = spec_from_file_location(
    "v023_one_epoch_provider_diagnostic_under_test",
    HERE / "run_v023_one_epoch_provider_diagnostic.py",
)
assert SPEC is not None and SPEC.loader is not None
DIAG = module_from_spec(SPEC)
sys.modules[SPEC.name] = DIAG
SPEC.loader.exec_module(DIAG)

KAPPA = 10.0
OPS3_UNIT = "normalized-repriced-ops3-delta-over-kappa"


def _model_config() -> LCSRSThreeRouteConfig:
    q1 = EEAxisActionSharedConfig(
        state_dim=228, action_dim=28, hidden_layers=(100, 50, 50), activation="tanh",
        learning_rate=0.001, kappa_bits=KAPPA, beta=0.1, loss_weights=(1.0, 1.0, 1.0),
    )
    q2 = EEAxisV014HeadConfig(
        action_dim=28, local_feature_dim=16, global_feature_dim=0, hidden_layers=(100, 50, 50),
        activation="tanh", learning_rate=0.001, kappa_bits=KAPPA, beta=0.1,
    )
    return LCSRSThreeRouteConfig(q1=q1, q2=q2)


def _c3_surface():
    context = np.zeros((2, 28, 29), dtype=np.float32)
    tokens = np.zeros((2, 28, 3, 38), dtype=np.float32)
    token_mask = np.zeros((2, 28, 3), dtype=np.bool_)
    token_mask[:, :, 2] = True
    tokens[:, :, 2, 1] = 1.0
    tokens[:, 1, 2, 2:5] = 1.0
    view = assemble_c3_view(
        action_context=context, tokens=tokens, token_mask=token_mask,
        action_mask=np.ones((2, 28), dtype=np.bool_),
        reference_actions=np.asarray([0, 0], dtype=np.int64),
    )
    return assemble_lcsrs_anchor_surface(
        view,
        [LCSRSPairTargets(
            pair_id="diag", user_ids=np.asarray([0, 1], dtype=np.int64),
            action_ids=np.asarray([1, 1], dtype=np.int64),
            normalized_targets_by_draw=np.ones((LCSRS_DRAW_COUNT, 2), dtype=np.float64),
        )],
    )


def _batches(*, c2_state_dim: int = 448):
    rng = np.random.default_rng(3)
    deltas = {"informed": [1.0, -0.5, 0.25], "neutral": [0.125, 0.75, -0.375]}
    out = {}
    surface = _c3_surface()
    for source in ("neutral", "informed"):
        c1 = EEAxisPairBatch(
            states=rng.normal(size=(3, 228)).astype(np.float32),
            reference_actions=np.asarray([0, 2, 1], dtype=np.int64),
            candidate_actions=np.asarray([1, 3, 0], dtype=np.int64),
            target_surplus_bits=np.asarray([5.0, -2.0, 1.0], dtype=np.float64),
            action_masks=np.ones((3, 28), dtype=np.bool_),
        )
        c2 = EEAxisV014NormalizedPairBatch(
            states=rng.normal(size=(3, c2_state_dim)).astype(np.float32),
            reference_actions=np.asarray([0, 1, 2], dtype=np.int64),
            candidate_actions=np.asarray([1, 2, 3], dtype=np.int64),
            normalized_target_deltas=np.asarray(deltas[source], dtype=np.float64),
            action_masks=np.ones((3, 28), dtype=np.bool_),
        )
        c3 = LCSRSC3SampledBatch(
            anchor_indices=np.asarray([0], dtype=np.int64),
            row_classes=np.asarray([LCSRS_ROW_REFERENCE], dtype=np.uint8),
            user_indices=np.asarray([0], dtype=np.int64),
            action_indices=np.asarray([0], dtype=np.int64),
            normalized_targets=np.asarray([0.0], dtype=np.float32),
        )
        out[source] = {"C1": c1, "C2": c2, "C3": c3, "surface": surface}
    return out


class CyclicProvider:
    """Deterministic provider that repeats one authenticated panel per epoch."""

    provider_identity = "synthetic-provider:diag"
    planned_epoch_budget = 100

    def __init__(self, batches):
        self._batches = batches
        self.cursor = 0
        self.source_index = 0
        self.provider_identity_payload = {"schema": "synthetic", "epoch_budget": 100}

    def next_batch(self, *, route, source, update_cursor):
        assert update_cursor == self.cursor
        assert route == ("C1", "C2", "C3")[self.cursor % 3]
        assert source == ("neutral", "informed")[self.source_index]
        if self.source_index == 1:
            self.source_index = 0
            self.cursor += 1
        else:
            self.source_index = 1
        orchestrator = DIAG.load_runner_module().ORCHESTRATOR
        batch = self._batches[source][route]
        return orchestrator.ProvidedRouteBatch(
            route=route, source=source, file_id=f"{route}-{source}-panel", batch=batch,
            c3_surfaces=(self._batches[source]["surface"],) if route == "C3" else (),
        )

    def sampler_state(self):
        return {"cursor": self.cursor, "source_index": self.source_index}

    def load_sampler_state(self, state):
        self.cursor = state["cursor"]
        self.source_index = state["source_index"]


def _artifact(batches, *, scale: float = 1.0):
    def for_mode(source):
        rows = [
            {"target_unit": OPS3_UNIT, "target_delta": float(value) * scale}
            for value in batches[source]["C2"].normalized_target_deltas
        ]
        entry = SimpleNamespace(path=Path(f"c2-{source}-world-1.json"), dataset=SimpleNamespace(rows=rows))
        return SimpleNamespace(c2_datasets=(entry,))
    return SimpleNamespace(for_mode=for_mode)


def test_diagnostic_passes_on_synthetic_provider_and_writes_receipt(tmp_path: Path) -> None:
    batches = _batches()
    root = tmp_path / "diag"
    receipt = DIAG.run_diagnostic(
        make_provider=lambda: CyclicProvider(batches),
        load_target_artifact=lambda: _artifact(batches),
        model_config=_model_config(),
        train_seed=7,
        output_root=root,
        scoring_users=1,
        metadata={"origin": "unit-test"},
    )
    assert receipt["status"] == DIAG.STATUS_PASS, receipt.get("failed_checks")
    assert receipt["failed_checks"] == []
    assert receipt["formal_100e_contract"] is False
    assert receipt["test_split_opened"] is False and receipt["episode_training"] is False
    written = json.loads((root / DIAG.RECEIPT_NAME).read_text(encoding="ascii"))
    assert written["status"] == DIAG.STATUS_PASS
    assert all(item["pass"] for item in written["checks"].values())
    assert written["checks"]["c2_labels_delivered_equal_producer_target_delta_no_second_division"]["informed"]["byte_equal_target_delta"]
    assert written["checks"]["q1_q2_q3_masked_deployment_scoring"]["users"] == 1
    assert set(written["checks"]["q1_q2_q3_masked_deployment_scoring"]["arms"]) == {
        "ALL_NEUTRAL_CONTROL", "FULL", "DROP_C1", "DROP_C2", "DROP_C3"
    }
    assert (root / DIAG.CHECKPOINT_NAME).is_file()
    assert (root / (DIAG.CHECKPOINT_NAME + ".sha256")).is_file()
    assert not (root / "COMPLETE").exists()
    assert len(written["epoch_updates"]) == 15


def test_diagnostic_fails_when_delivered_c2_labels_look_divided_twice(tmp_path: Path) -> None:
    batches = _batches()
    receipt = DIAG.run_diagnostic(
        make_provider=lambda: CyclicProvider(batches),
        load_target_artifact=lambda: _artifact(batches, scale=KAPPA),
        model_config=_model_config(),
        train_seed=7,
        output_root=tmp_path / "diag-twice",
    )
    assert receipt["status"] == DIAG.STATUS_FAIL
    assert receipt["failed_checks"] == [
        "c2_labels_delivered_equal_producer_target_delta_no_second_division"
    ]


def test_diagnostic_fails_closed_when_provider_c2_is_228d(tmp_path: Path) -> None:
    batches = _batches(c2_state_dim=228)
    receipt = DIAG.run_diagnostic(
        make_provider=lambda: CyclicProvider(batches),
        load_target_artifact=lambda: _artifact(batches),
        model_config=_model_config(),
        train_seed=7,
        output_root=tmp_path / "diag-228",
    )
    assert receipt["status"] == DIAG.STATUS_FAIL
    assert receipt["error"] is not None
    assert (tmp_path / "diag-228" / DIAG.RECEIPT_NAME).is_file()


def test_diagnostic_refuses_existing_output_root(tmp_path: Path) -> None:
    root = tmp_path / "exists"
    root.mkdir()
    with pytest.raises(DIAG.V023OneEpochDiagnosticError, match="absent"):
        DIAG.run_diagnostic(
            make_provider=lambda: CyclicProvider(_batches()),
            model_config=_model_config(),
            train_seed=7,
            output_root=root,
        )


def test_diagnostic_requires_the_target_artifact_loader(tmp_path: Path) -> None:
    receipt = DIAG.run_diagnostic(
        make_provider=lambda: CyclicProvider(_batches()),
        model_config=_model_config(),
        train_seed=7,
        output_root=tmp_path / "diag-no-loader",
    )
    assert receipt["status"] == DIAG.STATUS_FAIL
    assert receipt["failed_checks"] == [
        "c2_labels_delivered_equal_producer_target_delta_no_second_division"
    ]


def test_diagnostic_detects_a_trainer_that_rescales_c2_deltas(monkeypatch, tmp_path: Path) -> None:
    """Mutation: a trainer dividing the delivered deltas by kappa again must fail the behavioural check."""

    batches = _batches()
    orchestrator = DIAG.load_runner_module().ORCHESTRATOR
    trainer_type = orchestrator._load_existing_trainer_type()
    original = trainer_type.update_c2

    def rescaling_update_c2(self, batch):
        rescaled = EEAxisV014NormalizedPairBatch(
            states=batch.states,
            reference_actions=batch.reference_actions,
            candidate_actions=batch.candidate_actions,
            normalized_target_deltas=np.asarray(batch.normalized_target_deltas, dtype=np.float64) / KAPPA,
            action_masks=batch.action_masks,
        )
        return original(self, rescaled)

    monkeypatch.setattr(trainer_type, "update_c2", rescaling_update_c2)
    receipt = DIAG.run_diagnostic(
        make_provider=lambda: CyclicProvider(batches),
        load_target_artifact=lambda: _artifact(batches),
        model_config=_model_config(),
        train_seed=7,
        output_root=tmp_path / "diag-rescaled-trainer",
    )
    assert receipt["status"] == DIAG.STATUS_FAIL
    assert "c2_update_loss_reproduced_from_delivered_deltas_without_rescaling" in receipt["failed_checks"]
    # the producer-vs-delivered equality still holds: the defect is isolated to the trainer path
    assert "c2_labels_delivered_equal_producer_target_delta_no_second_division" not in receipt["failed_checks"]


def test_diagnostic_rejects_untrimmed_or_oversized_identity(tmp_path: Path) -> None:
    class Padded(CyclicProvider):
        provider_identity = " padded "

    receipt = DIAG.run_diagnostic(
        make_provider=lambda: Padded(_batches()),
        load_target_artifact=lambda: _artifact(_batches()),
        model_config=_model_config(),
        train_seed=7,
        output_root=tmp_path / "diag-identity",
    )
    assert receipt["status"] == DIAG.STATUS_FAIL
    assert "provider_identity" in (receipt.get("error") or "")


def test_receipt_survives_unserialisable_metadata(tmp_path: Path) -> None:
    class Opaque:
        pass

    batches = _batches()
    receipt = DIAG.run_diagnostic(
        make_provider=lambda: CyclicProvider(batches),
        load_target_artifact=lambda: _artifact(batches),
        model_config=_model_config(),
        train_seed=7,
        output_root=tmp_path / "diag-opaque",
        metadata={"opaque": Opaque(), "raw": b"\x00\x01", "tags": {"b", "a"}},
    )
    assert receipt["status"] == DIAG.STATUS_PASS, receipt.get("failed_checks")
    written = json.loads((tmp_path / "diag-opaque" / DIAG.RECEIPT_NAME).read_text(encoding="ascii"))
    assert written["metadata"]["tags"] == ["a", "b"]
    assert written["metadata"]["raw"]["length"] == 2

