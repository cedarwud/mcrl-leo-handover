"""Focused tests for the offline V0.23 post-Gate C3 update ladder."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import numpy as np
import pytest
import torch

from mcrl.runtime.ee_axis_lcsrs_c3_dataset import (
    LCSRSPairTargets,
    assemble_lcsrs_anchor_surface,
)
from mcrl.runtime.ee_axis_lcsrs_c3_state import assemble_c3_view


HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "postgate_c3_update_ladder.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("postgate_c3_update_ladder_test", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ladder = _load_module()


def _surface():
    users = 2
    actions = 28
    action_context = np.zeros((users, actions, 29), dtype=np.float32)
    action_mask = np.ones((users, actions), dtype=np.bool_)
    token_mask = np.zeros((users, actions, users + 1), dtype=np.bool_)
    token_mask[:, :, users] = True
    tokens = np.zeros((users, actions, users + 1, 38), dtype=np.float32)
    tokens[:, :, users, 1] = 1.0
    # The pair token uses the supported [source occupancy, supported,
    # designated] sentinel only for the two designated cells.
    tokens[:, 1, users, 2:5] = 1.0
    reference_actions = np.zeros(users, dtype=np.int64)
    view = assemble_c3_view(
        action_context=action_context,
        tokens=tokens,
        token_mask=token_mask,
        action_mask=action_mask,
        reference_actions=reference_actions,
    )
    draws = np.tile(np.asarray([[0.5, -0.25]], dtype=np.float64), (32, 1))
    pair = LCSRSPairTargets(
        pair_id="unit-pair",
        user_ids=np.asarray([0, 1], dtype=np.int64),
        action_ids=np.asarray([1, 1], dtype=np.int64),
        normalized_targets_by_draw=draws,
    )
    return assemble_lcsrs_anchor_surface(view, [pair])


class _Provider:
    def __init__(self, source):
        self.source = source
        self.calls: list[tuple[str, int]] = []

    def provide(self, *, arm: str, student_seed: int):
        self.calls.append((arm, student_seed))
        return self.source


def _provider(*, arm: str = "INFORMED") -> _Provider:
    source = ladder.AuthenticatedV023Source(
        arm=arm,
        source_manifest_sha256="a" * 64,
        surfaces=(_surface(),),
    )
    return _Provider(source)


def test_fixed_axis_seeds_and_update_checkpoint_identity(tmp_path: Path) -> None:
    assert ladder.POSTGATE_C3_UPDATE_AXIS == tuple(range(0, 2001, 100))
    assert ladder.POSTGATE_C3_STUDENT_SEEDS == (2026135101, 2026135102, 2026135103)
    provider = _provider()
    result = ladder.run_postgate_c3_update_ladder(
        provider,
        arm="INFORMED",
        output_dir=tmp_path / "axis",
        stop_after=0,
    )
    assert result.student_seeds == ladder.POSTGATE_C3_STUDENT_SEEDS
    assert result.status == "PARTIAL"
    assert result.selected_checkpoint is None
    assert len(result.checkpoints) == 3
    assert provider.calls == [("INFORMED", seed) for seed in ladder.POSTGATE_C3_STUDENT_SEEDS]
    for checkpoint in result.checkpoints:
        receipt = checkpoint.receipt
        assert receipt["update_count"] == 0
        assert receipt["checkpoint_kind"] == "LEARNER_UPDATE"
        assert receipt["update_axis"] == "learner_updates"
        assert receipt["learner_update"] is True
        assert receipt["episode_checkpoint"] is False
        assert receipt["episode_training"] is False
        assert receipt["test_split_opened"] is False
        assert receipt["evaluation"] is False
        assert receipt["selection"]["outcome_dependent_selection"] is False


def test_resume_is_byte_and_model_digest_deterministic(monkeypatch, tmp_path: Path) -> None:
    def deterministic_step(network, optimizer, surfaces, batch, *, device="cpu"):
        del optimizer, surfaces, batch, device
        with torch.no_grad():
            network.token_scorer[0].bias.add_(0.0001)
        return 0.0

    monkeypatch.setattr(ladder, "lcsrs_c3_training_step", deterministic_step)
    uninterrupted = ladder.run_postgate_c3_update_ladder(
        _provider(), arm="INFORMED", output_dir=tmp_path / "full", stop_after=200
    )
    paused = ladder.run_postgate_c3_update_ladder(
        _provider(), arm="INFORMED", output_dir=tmp_path / "paused", stop_after=100
    )
    for seed in ladder.POSTGATE_C3_STUDENT_SEEDS:
        paused_checkpoint = next(
            row
            for row in paused.checkpoints
            if row.receipt["student_seed"] == seed and row.update_count == 100
        )
        resumed = ladder.resume_postgate_c3_update_ladder(
            paused_checkpoint.receipt_path,
            _provider(),
            stop_after=200,
        )
        actual = next(row for row in resumed.checkpoints if row.update_count == 200)
        expected = next(
            row
            for row in uninterrupted.checkpoints
            if row.receipt["student_seed"] == seed and row.update_count == 200
        )
        assert actual.receipt == expected.receipt
        assert actual.state_path.read_bytes() == expected.state_path.read_bytes()


def test_checkpoint_hashes_fail_closed_when_state_is_modified(tmp_path: Path) -> None:
    result = ladder.run_postgate_c3_update_ladder(
        _provider(), arm="INFORMED", output_dir=tmp_path / "run", stop_after=0
    )
    checkpoint = result.checkpoints[0]
    original = checkpoint.state_path.read_bytes()
    checkpoint.state_path.write_bytes(original + b"tampered")
    with pytest.raises(ladder.PostGateC3UpdateLadderError, match="state byte hash"):
        ladder.verify_postgate_c3_checkpoint(checkpoint.receipt_path)


def test_neutral_source_is_external_and_equal_budget_only() -> None:
    surface = _surface()
    neutral_targets = np.zeros_like(surface.normalized_targets)
    neutral_targets[0, 1] = 0.125
    source = ladder.AuthenticatedV023Source(
        arm="NEUTRAL_SOURCE",
        source_manifest_sha256="b" * 64,
        surfaces=(surface,),
        normalized_targets_by_anchor=(neutral_targets,),
    )
    assert source.arm == "NEUTRAL_SOURCE"
    assert source.target_source_sha256 != ladder.AuthenticatedV023Source(
        arm="INFORMED",
        source_manifest_sha256="b" * 64,
        surfaces=(surface,),
    ).target_source_sha256
    assert ladder.POSTGATE_C3_UPDATE_COUNT == 2000
    with pytest.raises(ladder.PostGateC3UpdateLadderError, match="requires an external"):
        ladder.AuthenticatedV023Source(
            arm="NEUTRAL_SOURCE",
            source_manifest_sha256="b" * 64,
            surfaces=(surface,),
        )


def test_existing_authenticated_source_panel_is_only_adapted_not_rebuilt() -> None:
    surface = _surface()
    panel = SimpleNamespace(
        source_manifest_sha256="c" * 64,
        artifacts=(SimpleNamespace(records=(SimpleNamespace(surface=surface),)),),
    )
    source = ladder.authenticated_source_from_v023_panel(
        panel,
        arm="INFORMED",
    )
    assert source.source_manifest_sha256 == "c" * 64
    assert source.surfaces == (surface,)
