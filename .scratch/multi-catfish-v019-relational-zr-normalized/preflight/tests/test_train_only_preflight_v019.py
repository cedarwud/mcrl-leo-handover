"""Synthetic-only tests for the V0.19 TRAIN preflight.

These tests intentionally do not call the server runner, inspect a real source
root, open VALIDATION/TEST, or perform a learner update.
"""

from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace
import hashlib

import numpy as np
import pytest
import torch


HERE = Path(__file__).resolve()
PREFLIGHT = HERE.parents[1]
V019 = PREFLIGHT.parent
REPO = V019.parents[1]
sys.path.insert(0, str(PREFLIGHT))
sys.path.insert(0, str(V019 / "learner"))
sys.path.insert(0, str(REPO / "src"))

import train_only_preflight_v019 as preflight  # noqa: E402
from relational_source_schema import (  # noqa: E402
    ACTION_CONTEXT_DIM,
    ACTION_DIM,
    RelationalZRC3Source,
    VICTIM_TOKEN_DIM,
)


def test_fixed_profile_is_closed_and_matches_v018_profile() -> None:
    profile = {
        "action_dim": 28,
        "action_context_dim": 7,
        "victim_token_dim": 6,
        "hidden_layers": [100, 50, 50],
        "activation": "tanh",
        "optimizer": "Adam",
        "learning_rate": 0.001,
        "batch_size": 512,
        "update_count": 100,
        "beta": 0.0,
        "kappa_bits_hex": "0x1.2cea89d260f2ap+33",
        "output_unit_mode": "normalized_bits_per_kappa",
    }
    preflight.validate_fixed_profile(profile)

    drift = dict(profile)
    drift["learning_rate"] = 0.01
    with pytest.raises(preflight.PreflightError, match="learning_rate"):
        preflight.validate_fixed_profile(drift)

    missing = dict(profile)
    del missing["output_unit_mode"]
    with pytest.raises(preflight.PreflightError, match="unknown or missing"):
        preflight.validate_fixed_profile(missing)


def test_source_root_accepts_only_declared_train_directory(tmp_path: Path) -> None:
    wrong = tmp_path / "VALIDATION"
    wrong.mkdir()
    with pytest.raises(preflight.PreflightError, match="declared V0.18 TRAIN"):
        preflight.validate_source_root(wrong)

    test_dir = tmp_path / "TEST"
    test_dir.mkdir()
    with pytest.raises(preflight.PreflightError):
        preflight.validate_source_root(test_dir)


def test_schedule_is_exactly_100_updates_and_deterministic() -> None:
    first = preflight.build_schedule()
    second = preflight.build_schedule()
    assert first == second
    assert len(first) == 100
    assert [item.update for item in first] == list(range(1, 101))
    assert all(item.row_indices for item in first)
    assert all(len(item.row_indices) == 512 for item in first)
    assert all(len(set(item.row_indices)) == 512 for item in first)
    assert all(0 <= index < 1000 for item in first for index in item.row_indices)
    assert {item.source_index for item in first} == set(range(4))

    with pytest.raises(preflight.PreflightError, match="selected source lineage"):
        preflight.build_schedule(selected_lineage=2026092102)

    with pytest.raises(preflight.PreflightError, match="schedule seed"):
        preflight.build_schedule(schedule_seed=2026120493)


def test_lineage_selection_keeps_one_complete_background_binding() -> None:
    sources = tuple(
        preflight.TrainSource(
            path=Path(f"{world}-{lineage}"),
            source=SimpleNamespace(world_seed=world, lineage=lineage),
            bridge={},
        )
        for lineage in preflight.EXPECTED_LINEAGES
        for world in preflight.EXPECTED_TRAIN_WORLDS
    )
    selected = preflight.select_preflight_lineage(sources)
    assert len(selected) == 4
    assert {item.source.lineage for item in selected} == {2026092101}
    assert {item.source.world_seed for item in selected} == set(
        preflight.EXPECTED_TRAIN_WORLDS
    )


def test_global_gradient_rms_is_over_all_finite_elements() -> None:
    left = torch.tensor([3.0, 4.0], requires_grad=True)
    right = torch.tensor([0.0, 0.0, 12.0], requires_grad=True)
    (left.square().sum() + right.square().sum()).backward()
    # Gradients are [6, 8] and [0, 0, 24], hence sqrt(676 / 5).
    assert preflight.global_gradient_rms((left, right)) == pytest.approx(
        (676.0 / 5.0) ** 0.5
    )


def _synthetic_source() -> RelationalZRC3Source:
    rows = 3
    victims = 1
    rng = np.random.default_rng(91)
    context = rng.normal(size=(rows, ACTION_DIM, ACTION_CONTEXT_DIM))
    tokens = rng.normal(size=(rows, ACTION_DIM, victims, VICTIM_TOKEN_DIM))
    action_mask = np.ones((rows, ACTION_DIM), dtype=np.bool_)
    victim_mask = np.ones((rows, ACTION_DIM, victims), dtype=np.bool_)
    compatible = np.ones((rows, ACTION_DIM), dtype=np.bool_)
    references = np.zeros(rows, dtype=np.int64)
    target = np.zeros((rows, ACTION_DIM), dtype=np.float64)
    target[:, 1] = np.asarray([2.0, 4.0, 6.0])
    return RelationalZRC3Source(
        action_context=context,
        victim_tokens=tokens,
        action_mask=action_mask,
        victim_mask=victim_mask,
        positive_credit_compatible=compatible,
        reference_actions=references,
        target_surface_bits=target,
        world_seed=101,
        lineage=1,
        split="TRAIN",
        field_root_digest="a" * 64,
        kappa_bits=preflight.EXPECTED_KAPPA_BITS,
    )


def test_zero_null_mse_uses_same_legal_nonreference_normalized_surface() -> None:
    source = _synthetic_source()
    value = preflight.zero_null_pair_mse(source, (0, 1, 2))
    expected = np.mean(
        np.square(
            np.asarray([2.0, 4.0, 6.0], dtype=np.float64)
            / preflight.EXPECTED_KAPPA_BITS
        )
    )
    assert value == pytest.approx(float(expected))


def test_preflight_constants_keep_single_dev_seed_pair_and_no_validation() -> None:
    assert preflight.DEV_INITIALIZATION_SEED == 2026120491
    assert preflight.DEV_SCHEDULE_SEED == 2026120492
    assert preflight.DEV_INITIALIZATION_SEED != preflight.DEV_SCHEDULE_SEED
    assert preflight.FIRST_GRADIENT_RMS_THRESHOLD == pytest.approx(1e-5)
    assert preflight.EXPECTED_OUTPUT_UNIT_MODE == "normalized_bits_per_kappa"
    assert "VALIDATION" not in str(preflight.EXPECTED_SOURCE_ROOT)
    assert "TEST" not in str(preflight.EXPECTED_SOURCE_ROOT)


def test_receipt_body_and_file_hashes_are_distinct_and_verifiable(tmp_path: Path) -> None:
    body = {"schema": preflight.PREFLIGHT_SCHEMA, "decision": "ABORT"}
    payload = preflight._write_receipt(tmp_path / "receipt", body)
    receipt_path = tmp_path / "receipt" / "receipt.json"
    receipt_bytes = receipt_path.read_bytes()
    assert payload["receipt_body_sha256"] == preflight.canonical_sha256(body)
    line = (tmp_path / "receipt" / "receipt.sha256").read_text(encoding="ascii")
    file_digest, filename = line.strip().split("  ")
    assert filename == "receipt.json"
    assert file_digest == hashlib.sha256(receipt_bytes).hexdigest()
    assert file_digest != payload["receipt_body_sha256"]
