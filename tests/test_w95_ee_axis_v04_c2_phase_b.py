"""W-95 -- Phase-B C2 shard/merge contract helpers.

These tests intentionally stay on the artifact and gate boundary.  They do
not import torch, load a checkpoint, open a TLE archive, run a simulator, or
start a Phase-B shard.
"""

from __future__ import annotations

import importlib.util
import hashlib
import inspect
import json
import math
from pathlib import Path
from types import SimpleNamespace
import sys

import numpy as np
import pytest


REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "v04_c2_phase_b_runner",
    REPO / ".scratch/c3-v04/run_v04_c2_phase_b.py",
)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _anchor() -> SimpleNamespace:
    keys = tuple((1000 + action, action) for action in range(27))
    return SimpleNamespace(
        intervention_key=(1, _sha("world"), _sha("anchor"), 0),
        source_seed=1,
        focal_user=0,
        reference_action=0,
        anchor_sha256=_sha("anchor"),
        anchor_schedule_sha256=_sha("schedule"),
        incumbent_physical_key=keys[0],
        candidate_physical_keys=keys,
    )


def _row(anchor: SimpleNamespace, action: int) -> dict[str, object]:
    key = anchor.candidate_physical_keys[action]
    sibling_key = [
        anchor.intervention_key[0],
        anchor.intervention_key[1],
        anchor.intervention_key[2],
        anchor.intervention_key[3],
        list(key),
    ]
    rates_r = [[10.0], [10.0], [10.0], [10.0]]
    rates_c = [[10.0], [11.0 + action], [11.0 + action], [11.0 + action]]
    return {
        "row_status": "ready",
        "sibling_key": sibling_key,
        "candidate_physical_key": list(key),
        "candidate_action": action + 1,
        "pair": {
            "zeta2_temporal_surplus_bits": float(action + 1),
            "candidate_rates_bps": rates_c,
            "reference_rates_bps": rates_r,
            "interval_s": 1.0,
            "release_offset": 2,
            "held_physical_key": list(key),
        },
    }


def test_physical_gate_excludes_schedule_incumbent_and_uses_json_cluster_keys() -> None:
    anchor = _anchor()
    rows = [_row(anchor, action) for action in range(27)]
    gate = runner._physical_gate(rows, (anchor,))

    # The incumbent is one of the 27 non-Main siblings and must be excluded
    # only from the G-S non-incumbent statistics, not from G-V top-three.
    assert gate["non_incumbent_count"] == 26
    assert gate["missing_outcome_count"] == 0
    key_text = runner._cluster_key_text(anchor.intervention_key)
    assert key_text in gate["cluster_target_iqr"]
    assert json.loads(key_text) == list(anchor.intervention_key)


def test_row_metrics_does_not_mislabel_candidate_as_non_incumbent() -> None:
    anchor = _anchor()
    metrics = runner._row_metrics(_row(anchor, 0))
    assert len(metrics) == 3
    target, delivered, release = metrics
    assert target == pytest.approx(1.0 / runner.support.KAPPA_BITS)
    assert delivered == pytest.approx(3.0)
    assert release == 2


def test_anchor_state_record_is_exact_228_28_and_tamper_evident() -> None:
    state = np.arange(228, dtype=np.float32)
    mask = np.ones(28, dtype=np.bool_)
    record = runner._anchor_state_record(
        state=state,
        mask=mask,
        state_schema=runner.EE_AXIS_STATE_SCHEMA,
        state_schema_sha256=runner.EE_AXIS_STATE_SCHEMA_SHA256,
        state_observation_sha256=_sha("encoded-observation"),
    )
    restored = runner._validate_anchor_state_record(record, field="anchor_state")
    assert restored["state"] == state.tolist()
    assert restored["action_mask"] == mask.tolist()

    damaged = dict(record)
    damaged["state"] = list(record["state"])
    damaged["state"][0] = 99.0  # type: ignore[index]
    with pytest.raises(runner.PhaseBError, match="state_row_sha256 drifted|anchor_state_sha256 drifted"):
        runner._validate_anchor_state_record(damaged, field="anchor_state")


def test_state_authority_collapses_identical_cluster_copies() -> None:
    anchor = _anchor()
    state = np.arange(228, dtype=np.float32)
    mask = np.ones(28, dtype=np.bool_)
    state_record = runner._anchor_state_record(
        state=state,
        mask=mask,
        state_schema=runner.EE_AXIS_STATE_SCHEMA,
        state_schema_sha256=runner.EE_AXIS_STATE_SCHEMA_SHA256,
        state_observation_sha256=_sha("encoded-observation"),
    )
    rows = []
    for action in range(27):
        row = _row(anchor, action)
        row["anchor_state"] = state_record
        rows.append(row)
    authority = runner._collect_anchor_state_authority(
        rows,
        (anchor,),
        require_complete=True,
    )
    entry = authority[runner._cluster_key_text(anchor.intervention_key)]
    assert entry["status"] == "COMPLETE"
    assert entry["anchor_state"]["anchor_state_sha256"] == state_record["anchor_state_sha256"]


def test_gc_gate_adds_shared_zero_reference_to_27_q13_targets() -> None:
    anchor = _anchor()
    phase_rows = []
    q13_rows = []
    for action in range(27):
        row = _row(anchor, action)
        phase_rows.append(
            {
                "sibling_key": row["sibling_key"],
                "candidate_action": row["candidate_action"],
                "zeta2_temporal_surplus_bits": float(action + 1),
            }
        )
        q13_rows.append(row)

    result = runner._gc_gate(
        {"rows": phase_rows},
        {seed: q13_rows for seed in runner.Q13_INIT_SEEDS},
        (anchor,),
    )
    key_text = str(anchor.intervention_key)
    for seed in runner.Q13_INIT_SEEDS:
        cluster = result["initialization"][str(seed)]["cluster_spearman"]
        assert cluster[key_text] is not None


def test_q13_pair_state_check_runs_after_pair_materialization() -> None:
    source = inspect.getsource(runner._materialize_q13_pair)
    assert source.index("pair = _build_temporal_pair(") < source.index(
        "np.asarray(pair.state"
    )


def test_q13_gate_uses_receipt_only_seam_and_binds_frozen_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    manifest_body = {"schema": "frozen-source-v1", "files": []}
    manifest = manifest_body | {
        "source_manifest_sha256": runner._canonical_sha256(manifest_body)
    }
    (source_dir / "source-manifest.json").write_bytes(
        runner._canonical_bytes(manifest)
    )

    selected_paths: dict[str, str] = {}
    selected_receipts: dict[str, dict[str, str]] = {}
    for seed in runner.Q13_INIT_SEEDS:
        path = tmp_path / f"hybrid-{seed}.pt"
        path.write_bytes(f"hybrid-{seed}".encode("ascii"))
        selected_paths[str(seed)] = str(path)
        selected_receipts[str(seed)] = {
            "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest()
        }

    observed: dict[str, object] = {}

    class FakeScreen:
        @staticmethod
        def authenticate_gate(gate_dir: Path, *, source_dir: Path | None, prereg_path: Path) -> dict[str, object]:
            observed["source_dir"] = source_dir
            return {
                "selected_q3_rung": 100,
                "selected_hybrid_paths": selected_paths,
                "result": {"selected_hybrids": selected_receipts},
                "source_manifest_sha256": manifest["source_manifest_sha256"],
                "authority_sha256": _sha("authority"),
                "result_file_sha256": _sha("result"),
                "schedule_sha256": _sha("schedule"),
            }

    monkeypatch.setattr(runner, "_screen_module", lambda: FakeScreen)
    receipt = runner._authenticate_q13_gate(
        tmp_path / "gate",
        source_dir=source_dir,
        prereg_path=tmp_path / "prereg.json",
        v03_root=tmp_path / "v03",
    )

    assert observed["source_dir"] is None
    assert receipt["source_manifest_sha256"] == manifest["source_manifest_sha256"]
    assert len(receipt["selected_hybrid_file_sha256"]) == 3


def test_q13_release_metadata_is_normalized_after_final_support_observation() -> None:
    source = inspect.getsource(runner._materialize_q13_pair)
    release_check = source.index('raise PhaseBError("Q1+Q3 continuation did not produce one release")')
    normalize = source.index("candidate_trace = [", release_check)
    build = source.index("build = forecast.build_authoritative_forecast(", normalize)
    assert release_check < normalize < build
    assert "release_offset=release_offset" in source[normalize:build]


def test_q13_gate_binds_selected_checkpoint_bytes_to_gate_receipts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    manifest_body = {"schema": "frozen-source-v1", "files": []}
    manifest = manifest_body | {
        "source_manifest_sha256": runner._canonical_sha256(manifest_body)
    }
    (source_dir / "source-manifest.json").write_bytes(
        runner._canonical_bytes(manifest)
    )
    selected_paths: dict[str, Path] = {}
    selected_receipts: dict[str, dict[str, str]] = {}
    for seed in runner.Q13_INIT_SEEDS:
        path = tmp_path / f"hybrid-{seed}.pt"
        path.write_bytes(f"checkpoint-{seed}".encode("ascii"))
        selected_paths[str(seed)] = path
        selected_receipts[str(seed)] = {
            "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest()
        }

    class FakeScreen:
        @staticmethod
        def authenticate_gate(*_args: object, **_kwargs: object) -> dict[str, object]:
            return {
                "selected_q3_rung": 100,
                "selected_hybrid_paths": selected_paths,
                "result": {"selected_hybrids": selected_receipts},
                "source_manifest_sha256": manifest["source_manifest_sha256"],
            }

    monkeypatch.setattr(runner, "_screen_module", lambda: FakeScreen)
    receipt = runner._authenticate_q13_gate(
        tmp_path / "gate",
        source_dir=source_dir,
        prereg_path=tmp_path / "prereg",
        v03_root=tmp_path / "v03",
    )
    assert receipt["selected_hybrid_file_sha256"] == {
        seed: selected_receipts[seed]["file_sha256"] for seed in selected_receipts
    }


@pytest.mark.parametrize(
    ("gc_passed", "q13_count", "expected"),
    (
        (True, 0, (runner.C2_P0_MAIN_VALUE,)),
        (True, 2, (runner.C2_P0_MAIN_VALUE, runner.C2_P1_Q13_VALUE, runner.C2_P2_Q13_HUBER)),
        (False, 2, (runner.C2_P1_Q13_VALUE, runner.C2_P2_Q13_HUBER)),
        (False, 1, ()),
    ),
)
def test_phase_b_authorization_is_arm_specific(
    gc_passed: bool, q13_count: int, expected: tuple[str, ...]
) -> None:
    assert runner._eligible_arms(
        gc_passed=gc_passed,
        q13_physical_pass_count=q13_count,
    ) == expected


def test_downstream_surplus_uses_contract_exact_fsum_order() -> None:
    reference_rates = np.zeros((4, 3), dtype=np.float64)
    candidate_rates = np.asarray(
        (
            (0.0, 0.0, 0.0),
            (1.0e16, 1.0, -1.0e16),
            (3.0, 4.0, 5.0),
            (7.0, 8.0, 9.0),
        ),
        dtype=np.float64,
    )
    reference_power = np.asarray((1.0, 1.0, 1.0, 1.0), dtype=np.float64)
    candidate_power = np.asarray((1.0, 2.0, 3.0, 4.0), dtype=np.float64)
    observed = runner._downstream_surplus_from_traces(
        candidate_rates=candidate_rates,
        reference_rates=reference_rates,
        candidate_power=candidate_power,
        reference_power=reference_power,
        interval_s=2.0,
        lambda_bits_per_j=10.0,
    )
    expected = np.asarray(
        (
            2.0 * math.fsum(candidate_rates[1]) - 20.0,
            2.0 * math.fsum(candidate_rates[2]) - 40.0,
            2.0 * math.fsum(candidate_rates[3]) - 60.0,
        ),
        dtype=np.float64,
    )
    np.testing.assert_array_equal(observed, expected)
