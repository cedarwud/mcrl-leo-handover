from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


RUNNER = (
    Path(__file__).resolve().parents[1]
    / ".scratch/ee-axis-redesign/run_v03_e1_masked_meanmax_fallback.py"
)
SPEC = importlib.util.spec_from_file_location("masked_meanmax_fallback", RUNNER)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def _write_v3_trigger_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    digest = "d" * 64
    preoutcome = "e" * 64
    preoutcome_seal = "f" * 64
    monkeypatch.setattr(runner.v3, "_code_manifest", lambda: {"synthetic": digest})
    authority_body = {
        "schema": runner.v3.EXECUTION_AUTHORITY_SCHEMA,
        "status": "SEALED_BEFORE_ANY_VALIDATION_METRIC",
        "claim_ceiling": runner.v3.CLAIM_CEILING,
        "preoutcome_authority_sha256": preoutcome,
        "preoutcome_authority_seal_sha256": preoutcome_seal,
        "code_manifest": {"synthetic": digest},
    }
    authority_sha = runner.stable.sources._canonical_sha256(authority_body)
    authority = {**authority_body, "authority_sha256": authority_sha}
    authority_file = runner.stable.sources._write_once_json(
        tmp_path / "authority.json", authority
    )
    authority_seal_file = runner.stable.sources._write_once_json(
        tmp_path / "authority-seal.json",
        {
            "schema": f"{runner.v3.EXECUTION_AUTHORITY_SCHEMA}-seal",
            "authority_sha256": authority_sha,
            "authority_file_sha256": authority_file,
        },
    )
    result = {
        "schema": runner.v3.RESULT_SCHEMA,
        "status": runner.TRIGGER_STATUS,
        "claim_ceiling": runner.v3.CLAIM_CEILING,
        "authority_sha256": authority_sha,
        "preoutcome_authority_sha256": preoutcome,
        "source_partition_expanded": "TRAIN",
        "expanded_route": "C2",
        "base_validation_batches_unchanged": True,
        "test_dataset_paths_opened": [],
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "gate": {
            "status": runner.TRIGGER_STATUS,
            "route_gate": {
                "C1": {"pass": True},
                "C2": {"pass": True},
                "C3": {"pass": False},
            },
            "collision_pass": True,
            "action_main_effect_pass": True,
            "c2_anchor_sensitivity_pass": True,
        },
    }
    result_file = runner.stable.sources._write_once_json(
        tmp_path / "result.json", result
    )
    result_seal_file = runner.stable.sources._write_once_json(
        tmp_path / "result-seal.json",
        {
            "schema": runner.v3.RESULT_SEAL_SCHEMA,
            "authority_sha256": authority_sha,
            "preoutcome_authority_sha256": preoutcome,
            "result_file_sha256": result_file,
        },
    )
    return {
        "authority_file": authority_file,
        "authority_seal_file": authority_seal_file,
        "result_file": result_file,
        "result_seal_file": result_seal_file,
        "preoutcome": preoutcome,
        "preoutcome_seal": preoutcome_seal,
        "authority_internal": authority_sha,
    }


def test_v3_trigger_uses_canonical_authority_id_not_authority_file_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hashes = _write_v3_trigger_fixture(tmp_path, monkeypatch)
    assert hashes["authority_internal"] != hashes["authority_file"]
    loaded = runner._authenticate_v3_trigger(
        tmp_path,
        expected_authority_file_sha256=hashes["authority_file"],
        expected_authority_seal_file_sha256=hashes["authority_seal_file"],
        expected_result_file_sha256=hashes["result_file"],
        expected_result_seal_file_sha256=hashes["result_seal_file"],
        expected_preoutcome_authority_sha256=hashes["preoutcome"],
        expected_preoutcome_authority_seal_sha256=hashes["preoutcome_seal"],
    )
    assert loaded["authority"]["authority_sha256"] == hashes["authority_internal"]


def test_v3_trigger_rejects_authority_file_digest_as_canonical_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hashes = _write_v3_trigger_fixture(tmp_path, monkeypatch)
    with pytest.raises(runner.MaskedMeanMaxFallbackError, match="authority file bytes"):
        runner._authenticate_v3_trigger(
            tmp_path,
            expected_authority_file_sha256=hashes["authority_internal"],
            expected_authority_seal_file_sha256=hashes["authority_seal_file"],
            expected_result_file_sha256=hashes["result_file"],
            expected_result_seal_file_sha256=hashes["result_seal_file"],
            expected_preoutcome_authority_sha256=hashes["preoutcome"],
            expected_preoutcome_authority_seal_sha256=hashes["preoutcome_seal"],
        )


def test_fallback_status_has_no_second_fallback_state() -> None:
    assert runner.FALSE_BOUNDARY["validation_metrics_computed"] is False
    assert runner.POST_METRIC_BOUNDARY["validation_metrics_computed"] is True
    assert runner.CONTEXT_SELECTION_PROVENANCE["fresh_validation_look_index"] == 2
    assert runner.CONTEXT_SELECTION_PROVENANCE["alpha_control_gate_used"] is False
    assert runner.CONTEXT_SELECTION_PROVENANCE["sign_only_exploratory_gate_used"] is False
    assert runner._final_status(runner.GO_STATUS) == runner.GO_STATUS
    assert runner._final_status(runner.TRIGGER_STATUS) == runner.STOP_STATUS
    assert runner._final_status("STOP_ACTION_SHARED_VALIDATION") == runner.STOP_STATUS
    with pytest.raises(runner.MaskedMeanMaxFallbackError, match="unknown"):
        runner._final_status("TRY_ANOTHER_FALLBACK")


def test_state_mask_census_reports_actual_train_validation_surface() -> None:
    def batch(seed: int) -> SimpleNamespace:
        return SimpleNamespace(
            states=np.asarray(
                [[seed, 0.0], [seed + 1, 0.0]], dtype=np.float32
            ),
            action_masks=np.asarray(
                [[True, True], [True, False]], dtype=np.bool_
            ),
        )

    batches = SimpleNamespace(
        batch=lambda split, route: batch(
            {("train", "C1"): 0, ("validation", "C1"): 0}[split, route]
        )
    )
    # Use the real route names while keeping the fixture intentionally tiny.
    batches.batch = lambda split, route: batch(
        (0 if split == "train" else 10) + runner.ROUTE_NAMES.index(route) * 100
    )
    census = runner._state_mask_census(batches)
    assert census["rows"] == 12
    assert census["distinct_states"] == 12
    assert census["all_legal_mask_fraction"] == pytest.approx(0.5)
    assert set(census["by_route"]) == set(runner.ROUTE_NAMES)


def test_checkpoint_digest_is_verified_before_reload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = runner.meanmax.EEAxisMaskedMeanMaxConfig(
        state_dim=28,
        action_dim=3,
        hidden_layers=(4,),
        activation="tanh",
        learning_rate=0.001,
        kappa_bits=2.0,
        beta=0.1,
        loss_weights=(1.0, 1.0, 1.0),
    )
    trainer = runner.meanmax.EEAxisMaskedMeanMaxTrainer(config, train_seed=1)
    monkeypatch.setattr(
        runner.stable,
        "_save_checkpoint",
        lambda path, payload: (path.write_bytes(b"tampered"), "a" * 64)[1],
    )
    with pytest.raises(runner.MaskedMeanMaxFallbackError, match="digest"):
        runner._save_and_reload(
            path=tmp_path / "checkpoint.pt",
            authority_sha256="b" * 64,
            trainer=trainer,
            seed=1,
            rung=1,
            metrics={route: {} for route in runner.ROUTE_NAMES},
            batches=SimpleNamespace(),
        )
