"""W-94 -- regression seam for the post-outcome single-route diagnostic."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[1]
RUNNER = REPO / ".scratch" / "c3-v04" / "run_v04_route_interaction_diagnostic.py"


def _module():
    spec = importlib.util.spec_from_file_location("v04_route_interaction_w94", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _single_row(diagnostic, policy: str, *, bits: float = 120.0) -> dict:
    five = diagnostic.five
    seed = five.EVALUATION_SEEDS[0]
    initialization_seed = five.INITIALIZATION_SEEDS[0]
    field = five.common_field_receipt(seed)
    world = hashlib.sha256(f"world:{seed}".encode("ascii")).hexdigest()
    mask = hashlib.sha256(f"mask:{seed}".encode("ascii")).hexdigest()
    energy = 10.0
    return {
        "schema": five.EPISODE_SCHEMA,
        "policy_label": policy,
        "evaluation_split": "TRAIN",
        "initialization_seed": initialization_seed,
        "evaluation_seed": seed,
        "selected_q3_rung": 100,
        "total_q3_update_count": 100,
        "steps": 10,
        "users": 100,
        "decision_count": 1000,
        "start_epoch": "2026-09-01T00:00:00+00:00",
        "initial_world_sha256": world,
        "initial_state_sha256": world,
        "initial_mask_sha256": mask,
        "fading_field_sha256": field["root_digest"],
        "fading_field_components": field["components"],
        "total_bits": bits,
        "total_energy_j": energy,
        "ratio_of_sums_ee_bits_per_j": bits / energy,
        "served_user_steps": 900,
        "served_fraction": 0.9,
        "outage_fraction": 0.1,
        "action_trace_sha256": hashlib.sha256(
            f"{policy}:{seed}:{initialization_seed}".encode("ascii")
        ).hexdigest(),
        "test_split_opened": False,
        "held_out_ee_evaluated": True,
        "episode_training": False,
    }


def test_single_route_summary_adapts_only_the_validator_copy():
    diagnostic = _module()
    row = _single_row(diagnostic, "C1_ONLY")

    summary = diagnostic._summary([row], single_route_policy="C1_ONLY")

    assert summary["rows"] == 1
    assert summary["pooled_ratio_of_sums_ee_bits_per_j"] == pytest.approx(12.0)
    assert row["policy_label"] == "C1_ONLY"


def test_single_route_summary_fails_closed_on_label_mismatch():
    diagnostic = _module()
    row = _single_row(diagnostic, "C2_ONLY")

    with pytest.raises(
        diagnostic.RouteInteractionDiagnosticError,
        match="single-route row policy label drifted",
    ):
        diagnostic._summary([row], single_route_policy="C1_ONLY")
