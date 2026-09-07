"""W-52 -- real C2 backend to current Q2 temporal-pair smoke seam."""

from __future__ import annotations

from pathlib import Path
import os
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.env.constants import TLE_ROOT_DEFAULT


ROOT = Path(__file__).resolve().parents[1]
C2_ROOT = ROOT / ".scratch" / "c2-v03"
if str(C2_ROOT) not in sys.path:
    sys.path.insert(0, str(C2_ROOT))

import run_c2_v03_real_temporal_pair_smoke as smoke  # noqa: E402


def test_public_adapter_helper_keeps_required_call_order(monkeypatch):
    """The parent runner cannot accidentally forecast before capturing state."""

    events: list[str] = []
    captured = object()
    pair = SimpleNamespace(
        source_route="C2",
        state=np.zeros(228, dtype=np.float32),
    )
    route_batch = SimpleNamespace(
        route="C2",
        pair_batch=SimpleNamespace(states=np.zeros((1, 228), dtype=np.float32)),
    )
    route_batch.verify = lambda: events.append("batch_verify")

    def fake_capture(prepared, **kwargs):
        assert prepared is prepared_fork
        assert kwargs["anchor_schedule_sha256"] == "a" * 64
        events.append("capture")
        return captured

    def fake_forecast():
        events.append("forecast")
        return object()

    def fake_materialize(capture, prepared, **kwargs):
        assert capture is captured
        assert prepared is prepared_fork
        events.append("materialize")
        return pair

    def fake_route_batch(rows):
        assert tuple(rows) == (pair,)
        events.append("route_batch")
        return route_batch

    prepared_fork = SimpleNamespace(run_forecast=fake_forecast)
    monkeypatch.setattr(smoke, "capture_temporal_anchor", fake_capture)
    monkeypatch.setattr(smoke, "materialize_temporal_pair", fake_materialize)
    monkeypatch.setattr(smoke, "build_temporal_route_batch", fake_route_batch)

    result = smoke.capture_and_materialize_q2_pair(
        prepared_fork,
        anchor_schedule_sha256="a" * 64,
        source_manifest_sha256="b" * 64,
        lambda_bits_per_j=1.0,
        interval_s=1.0,
    )

    assert events == ["capture", "forecast", "materialize", "route_batch", "batch_verify"]
    assert result.capture is captured
    assert result.pair is pair
    assert result.route_batch is route_batch


def test_real_smoke_payload_contract_is_explicit():
    """Keep the CLI's claim and route contract visible to reviewers."""

    assert smoke.SCHEMA == "mcrl-multi-catfish-v03-real-temporal-pair-smoke-v1"
    assert "no training" in smoke.CLAIM_CEILING
    assert smoke.KEYED_FADING == "keyed-branch-independent-v1"


_RUN_REAL = os.environ.get("MCRL_RUN_REAL_C2_TEMPORAL_SMOKE") == "1"
_REAL_TLE_ROOT = Path(TLE_ROOT_DEFAULT).expanduser()
_REAL_CHECKPOINT = ROOT / "artifacts" / "training-2026-08-25-rerun01" / "main" / "final-checkpoint.pt"
requires_real_loader = pytest.mark.skipif(
    not _RUN_REAL or not _REAL_TLE_ROOT.is_dir() or not _REAL_CHECKPOINT.is_file(),
    reason="set MCRL_RUN_REAL_C2_TEMPORAL_SMOKE=1 with the frozen TLE/checkpoint to run the bounded real loader",
)


@requires_real_loader
def test_real_c2_backend_materializes_a_228d_q2_pair():
    payload = smoke.run_real_temporal_pair_smoke(
        users=10,
        max_anchor_steps=6,
        max_candidates=1,
    )

    assert payload["status"] == "PASS"
    assert payload["training_or_replay_write"] is False
    assert payload["pair"]["source_route"] == "C2"
    assert payload["pair"]["state_shape"] == [228]
    assert payload["q2_route_batch"]["route"] == "C2"
    assert payload["q2_route_batch"]["states_shape"] == [1, 228]
    assert payload["main_networks_bitwise_unchanged"] is True
    assert payload["main_replay_unchanged"] is True
