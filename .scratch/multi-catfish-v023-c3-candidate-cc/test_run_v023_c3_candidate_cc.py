from __future__ import annotations

from fractions import Fraction
import hashlib
import json
from pathlib import Path
import stat

import numpy as np
import pytest

import build_cc_launch_authority as authority_builder
import c3_contingency_f0 as f0
import run_v023_c3_candidate_cc as cc


@pytest.fixture(scope="session", autouse=True)
def _single_thread_runtime() -> None:
    cc.pin_single_thread_runtime()


def _encoded_q(values: list[list[float]]) -> dict[str, object]:
    array = np.ascontiguousarray(values, dtype=np.dtype("<f4"))
    return {
        "dtype": "<f4",
        "encoding": "base16-little-endian-c-order",
        "shape": list(array.shape),
        "data_hex": array.tobytes(order="C").hex(),
    }


def _metrics(bits: float, energy: float, served: int, users: int = 2) -> dict[str, object]:
    return {
        "total_bits": bits.hex(),
        "total_energy_j": energy.hex(),
        "served": served,
        "opportunities": users,
    }


def _f0() -> dict[str, object]:
    return {
        "f0_schema": cc.e1.f1.F0_SCHEMA,
        "verified": True,
        "power_residual_w": 0.0.hex(),
        "energy_residual_j": 0.0.hex(),
    }


def _candidate_row(
    action: int, *, energy: float, served: int, bits: float = 100.0
) -> dict[str, object]:
    return {
        "focal_user": 0,
        "reference_action": 0,
        "candidate_action": action,
        "reference_physical_key": [1, 10],
        "candidate_physical_key": [1, 10 + action],
        "candidate_joint_actions": [action, -1],
        "metrics": _metrics(bits, energy, served),
        "f0_conservation": _f0(),
    }


def _step(
    *, tied: bool, candidate_energy: float = 9.0, candidate_served: int = 2
) -> dict[str, object]:
    second = 0.5 if tied else 0.25
    return {
        "step_index": 0,
        "state_sha256": "a" * 64,
        "q1_q2_float32": _encoded_q([[0.5, second], [0.0, 0.0]]),
        "action_masks": [[True, True], [False, False]],
        "action_physical_keys": [[[1, 10], [1, 11]], [None, None]],
        "reference_actions": [0, -1],
        "reference_metrics": _metrics(100.0, 10.0, 2),
        "reference_f0_conservation": _f0(),
        "unilateral_candidates": [
            _candidate_row(1, energy=candidate_energy, served=candidate_served)
        ],
    }


def _pooled(anchor: dict[str, object]) -> dict[str, object]:
    return cc.pool_unit_receipts([{"anchors": [anchor]}])


def _authority() -> dict[str, object]:
    return {
        "contract": {"path": "/sealed/contract.md", "sha256": "1" * 64},
        "preflight_manifest": {
            "path": "/sealed/preflight.json", "sha256": "2" * 64,
        },
        "code_files": [
            {"role": "cc_runner", "path": "/sealed/runner.py", "sha256": "3" * 64},
            {"role": "cc_tests", "path": "/sealed/tests.py", "sha256": "4" * 64},
        ],
    }


def test_no_ties_records_no_exposure_and_no_support() -> None:
    anchor = cc.select_anchor(_step(tied=False))
    pooled = _pooled(anchor)
    assert anchor["focal_user"] is None
    assert pooled["outcome"] == "C_C_FAST_SCREEN_NO_SUPPORT"
    assert pooled["reasons"] == [
        "NO_EXACT_TIE_EXPOSURE",
        "NO_LEGAL_CHANGE",
        "EE_NOT_ABOVE_BASE",
    ]


def test_lower_energy_exact_tie_wins_and_supports() -> None:
    anchor = cc.select_anchor(_step(tied=True, candidate_energy=9.0))
    pooled = _pooled(anchor)
    assert anchor["focal_user"] == 0
    assert anchor["selected_action"] == 1
    assert anchor["legal_physical_change"] is True
    assert pooled["outcome"] == "C_C_FAST_SCREEN_SUPPORT"
    assert pooled["reasons"] == []


def test_energy_selection_that_breaks_service_is_no_support() -> None:
    anchor = cc.select_anchor(
        _step(tied=True, candidate_energy=9.0, candidate_served=1)
    )
    pooled = _pooled(anchor)
    assert anchor["selected_action"] == 1
    assert pooled["outcome"] == "C_C_FAST_SCREEN_NO_SUPPORT"
    assert pooled["reasons"] == ["SERVICE_NONINFERIORITY_FAILED"]


def test_float32_exact_equality_signed_zero_and_near_tie() -> None:
    q = np.asarray(
        [
            [-0.0, +0.0, -1.0],
            [0.5, 0.5, 0.4999999701976776],
        ],
        dtype=np.float32,
    )
    masks = np.ones(q.shape, dtype=np.bool_)
    assert cc.exact_tie_sets(q, masks) == ((0, 1), (0, 1))
    assert q[1, 2] != q[1, 0]


def test_duplicate_nonbase_physical_alias_is_rejected() -> None:
    step = _step(tied=True)
    step["q1_q2_float32"] = _encoded_q([[0.5, 0.5, 0.5], [0.0, 0.0, 0.0]])
    step["action_masks"] = [[True, True, True], [False, False, False]]
    step["action_physical_keys"] = [
        [[1, 10], [1, 11], [1, 11]],
        [None, None, None],
    ]
    with pytest.raises(cc.CCError, match="alias"):
        cc.select_anchor(step)


def test_write_once_mode_readback_and_overwrite_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cc, "HERE", tmp_path)
    target, sidecar, digest = cc.write_once_with_sidecar(
        tmp_path / "receipt.json", {"answer": 42}
    )
    assert stat.S_IMODE(target.stat().st_mode) == 0o444
    assert stat.S_IMODE(sidecar.stat().st_mode) == 0o444
    assert cc.file_sha256(target) == digest
    assert json.loads(target.read_text(encoding="utf-8")) == {"answer": 42}
    with pytest.raises(cc.CCError, match="overwrite"):
        cc.write_once_with_sidecar(target, {"answer": 43})


def test_contract_requires_exact_0444_matching_appended_sidecar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contract = tmp_path / "contract.md"
    contract.write_text("prospective contract\n", encoding="utf-8")
    digest = hashlib.sha256(contract.read_bytes()).hexdigest()
    sidecar = Path(f"{contract}.sha256")
    sidecar.write_text(f"{digest}  {contract.name}\n", encoding="ascii")
    contract.chmod(0o444)
    sidecar.chmod(0o444)
    monkeypatch.setattr(cc, "CONTRACT_PATH", contract)
    assert cc.sealed_contract_binding() == {
        "path": str(contract.resolve()),
        "sha256": digest,
    }
    contract.chmod(0o644)
    with pytest.raises(cc.CCError, match="not sealed"):
        cc.sealed_contract_binding()


def test_launch_authority_rejects_nonexact_key_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cc, "HERE", tmp_path)
    payload = {name: None for name in cc.AUTHORITY_KEYS}
    payload["unexpected"] = None
    authority, _sidecar, _digest = cc.write_once_with_sidecar(
        tmp_path / "authority.json", payload
    )
    with pytest.raises(cc.CCError, match="keys differ"):
        cc.validate_launch_authority(
            authority,
            preflight_path=tmp_path / "preflight.json",
            preflight_sha256="0" * 64,
        )


def test_all_decision_imports_are_bound_and_f0_drift_refuses_dry_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    bindings = cc.expected_code_bindings()
    bound_paths = {Path(row["path"]) for row in bindings}
    assert {
        Path(cc.e1.__file__).resolve(),
        Path(cc.e1.f1.__file__).resolve(),
        Path(cc.f0.__file__).resolve(),
    } <= bound_paths

    f0_source = tmp_path / "c3_contingency_f0.py"
    f0_source.write_bytes(Path(cc.f0.__file__).read_bytes())
    monkeypatch.setattr(cc.f0, "__file__", str(f0_source))
    monkeypatch.setattr(
        cc, "_candidate_local", lambda path, *, field: Path(path).resolve()
    )
    monkeypatch.setattr(cc, "pin_single_thread_runtime", lambda: None)
    contract = {"path": "/sealed/contract.md", "sha256": "1" * 64}
    preflight = tmp_path / "preflight.json"
    preflight_sha = "2" * 64
    monkeypatch.setattr(cc, "sealed_contract_binding", lambda: contract)
    monkeypatch.setattr(
        cc, "validate_preflight_manifest", lambda _path: ({}, preflight_sha)
    )
    authority_payload = {
        "schema": cc.LAUNCH_AUTHORITY_SCHEMA,
        "status": "FROZEN_LAUNCH_AUTHORITY",
        "claim_ceiling": cc.CLAIM_CEILING,
        "preflight_manifest": {
            "path": str(preflight.resolve()),
            "sha256": preflight_sha,
        },
        "contract": contract,
        "e1_input": None,
        "code_files": cc.expected_code_bindings(),
        "output_root": str((tmp_path / "run-output").resolve()),
        "launch_arguments": [],
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }
    authority, _sidecar, _digest = cc.write_once_with_sidecar(
        tmp_path / "authority.json", authority_payload
    )

    f0_source.write_bytes(f0_source.read_bytes() + b"\n# digest drift\n")
    assert cc.main([
        "--preflight-manifest", str(preflight),
        "--launch-authority", str(authority),
        "--dry-run",
    ]) == 2
    assert "launch authority does not pin exact C-C bindings" in capsys.readouterr().err


def test_exact_rational_pooling_uses_binary64_values_losslessly() -> None:
    anchor = {
        "focal_user": 0,
        "legal_physical_change": True,
        "base_metrics": _metrics(0.1, 0.3, 2),
        "selected_metrics": _metrics(0.2, 0.3, 2),
    }
    pooled = _pooled(anchor)
    exact = pooled["exact"]
    base_bits = Fraction(
        int(exact["base_bits"]["numerator"]),
        int(exact["base_bits"]["denominator"]),
    )
    eta_selected = Fraction(
        int(exact["eta_selected"]["numerator"]),
        int(exact["eta_selected"]["denominator"]),
    )
    assert base_bits == Fraction.from_float(0.1)
    assert base_bits != Fraction(1, 10)
    assert eta_selected == Fraction.from_float(0.2) / Fraction.from_float(0.3)
    assert pooled["outcome"] == "C_C_FAST_SCREEN_SUPPORT"


def test_e1_accepted_roundoff_residual_is_accepted_by_cc() -> None:
    users = 100
    profile_fields = {
        "link_rate_bps": np.ones(users),
        "served": np.ones(users, dtype=np.bool_),
        "serving_satellite": np.zeros(users, dtype=np.int64),
        "serving_cell": np.zeros(users, dtype=np.int64),
        "active_beam_satellites": np.asarray([0], dtype=np.int64),
        "active_beam_cells": np.asarray([0], dtype=np.int64),
        "beam_power_w": np.asarray([1.0]),
        "fixed_power_w": 0.0,
        "system_power_w": 0.0,
        "interval_s": 30.08,
    }
    prototype = f0.PhysicalProfile(**profile_fields)
    canonical = f0._canonical_power_components(prototype)
    profile_fields.update({
        "fixed_power_w": canonical.fixed_power_w,
        "system_power_w": canonical.system_power_w,
    })
    receipt = cc.e1._conservation(f0.PhysicalProfile(**profile_fields))

    assert receipt["power_residual_w"] == (-2.0 ** -50).hex()
    energy = f0.PhysicalProfile(**profile_fields).network_energy_j.hex()
    assert cc._f0(
        receipt, field="synthetic E1 profile", network_energy_j=energy
    ) == cc.canonical_sha256(receipt)

    invalid = {**receipt, "power_residual_w": float(1.0e-6).hex()}
    with pytest.raises(cc.CCError, match="failed F0 verification"):
        cc._f0(invalid, field="material mismatch", network_energy_j=energy)


def test_e1_terminal_must_match_reviewed_digest_before_metadata_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    terminal = tmp_path / cc.E1_TERMINAL
    terminal.write_text("{}\n", encoding="ascii")
    terminal.chmod(0o444)
    monkeypatch.setattr(
        cc, "_jq_json",
        lambda *_args, **_kwargs: pytest.fail("unreviewed terminal metadata was read"),
    )
    with pytest.raises(cc.CCError, match="reviewed digest"):
        cc._e1_terminal_metadata(tmp_path)


def test_unit_receipt_carries_exact_cc_producer_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authority = _authority()
    producer = cc.unit_producer_binding(authority, authority_sha256="5" * 64)
    key = cc.e1.ALL_UNITS[0]
    tape = {
        "schema": cc.e1.UNIT_TAPE_SCHEMA,
        "status": "COMPLETE_IMMUTABLE_TAPE",
        "claim_ceiling": cc.e1.CLAIM_CEILING,
        "unit": key.as_dict(),
        "panel_bindings": cc.e1.panel_bindings(),
        "preflight_manifest_sha256": "6" * 64,
        "steps": [{"step_index": 0}, {"step_index": 1}],
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }
    anchors = [
        {"focal_user": None, "legal_physical_change": False,
         "base_metrics": {"opportunities": 100}},
        {"focal_user": 0, "legal_physical_change": True,
         "base_metrics": {"opportunities": 100}},
    ]
    monkeypatch.setattr(cc, "select_anchor", lambda step: anchors[step["step_index"]])

    receipt = cc.evaluate_unit_tape(
        tape, key=key, tape_sha256="7" * 64, producer_authority=producer
    )
    assert receipt["producer_cc_authority"] == {
        "contract_sha256": "1" * 64,
        "preflight_manifest_sha256": "2" * 64,
        "code_files": [
            {"role": "cc_runner", "sha256": "3" * 64},
            {"role": "cc_tests", "sha256": "4" * 64},
        ],
        "unit_authority_sha256": "5" * 64,
    }


def test_merge_refuses_receipts_without_cc_provenance() -> None:
    receipts = [
        {"source_e1_tape_sha256": f"{index:064x}", "anchors": []}
        for index in range(len(cc.e1.ALL_UNITS))
    ]
    bindings = [{} for _key in cc.e1.ALL_UNITS]
    with pytest.raises(cc.CCError, match="producer authority provenance"):
        cc.build_terminal_receipt(receipts, bindings, authority=_authority())


def test_merge_requires_common_contract_preflight_and_code_binding() -> None:
    authority = _authority()
    producer = cc.unit_producer_binding(authority, authority_sha256="5" * 64)
    receipts = [
        {"producer_cc_authority": dict(producer), "anchors": []}
        for _key in cc.e1.ALL_UNITS
    ]
    receipts[-1]["producer_cc_authority"] = {
        **producer,
        "code_files": [
            {"role": "foreign_runner", "sha256": "a" * 64},
        ],
    }
    bindings = [{} for _key in cc.e1.ALL_UNITS]
    with pytest.raises(cc.CCError, match="differs from merge authority"):
        cc.build_terminal_receipt(receipts, bindings, authority=authority)


def test_documented_authority_invocation_executes_without_separator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "e1"
    source.mkdir()
    contract = tmp_path / "contract.md"
    preflight = tmp_path / "preflight.json"
    output_root = tmp_path / "run-output"
    authority = tmp_path / "authority.json"
    unit = f"{cc.e1.ALL_UNITS[0].world}:{cc.e1.ALL_UNITS[0].lineage}"

    monkeypatch.setattr(cc, "HERE", tmp_path)
    monkeypatch.setattr(cc, "pin_single_thread_runtime", lambda: None)
    monkeypatch.setattr(cc, "validate_preflight_manifest", lambda _path: ({}, "8" * 64))
    monkeypatch.setattr(
        cc, "sealed_contract_binding",
        lambda: {"path": str(contract.resolve()), "sha256": "9" * 64},
    )
    monkeypatch.setattr(cc, "expected_code_bindings", lambda: [])
    monkeypatch.setattr(
        cc, "discover_e1_input",
        lambda _source, hash_tapes: {
            "root": str(source.resolve()),
            "terminal_receipt": {"sha256": cc.E1_TERMINAL_SHA256},
            "units": [],
        },
    )
    launch_arguments = [
        "--preflight-manifest", str(preflight),
        "--launch-authority", str(authority),
        "--from-e1-root", str(source),
        "--output", str(output_root),
        "--unit", unit,
    ]
    result = authority_builder.main([
        "--preflight-manifest", str(preflight),
        "--contract", str(contract),
        "--from-e1-root", str(source),
        "--output-root", str(output_root),
        "--output", str(authority),
        "--launch-arguments", *launch_arguments,
    ])

    assert result == 0
    payload = json.loads(authority.read_text(encoding="utf-8"))
    assert payload["launch_arguments"] == launch_arguments
    assert payload["e1_input"]["terminal_receipt"]["sha256"] == cc.E1_TERMINAL_SHA256


def test_missing_units_wait_without_publishing_terminal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cc, "HERE", tmp_path)
    output = tmp_path / "run-output"
    with pytest.raises(cc.CCMergeWaiting) as caught:
        cc.execute_merge(output=output, authority=_authority())
    assert caught.value.missing == len(cc.e1.ALL_UNITS)
    assert not (output / cc.DEFAULT_TERMINAL).exists()


def test_present_corrupt_unit_publishes_invalid_terminal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cc, "HERE", tmp_path)
    output = tmp_path / "run-output"
    (output / "units" / cc.e1.ALL_UNITS[0].slug).mkdir(parents=True)

    terminal, valid = cc.execute_merge(output=output, authority=_authority())
    assert valid is False
    assert json.loads(terminal.read_text(encoding="utf-8"))["status"] == "INVALID_RUN"


def test_main_prints_exact_merge_waiting_line(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cc, "pin_single_thread_runtime", lambda: None)
    monkeypatch.setattr(
        cc, "run", lambda _args: (_ for _ in ()).throw(cc.CCMergeWaiting(4))
    )
    assert cc.main(["--merge"]) == 3
    assert capsys.readouterr().out == "C_C_MERGE_WAITING 4 units missing\n"


def test_exact_pooling_sums_unequal_energy_anchors_before_ratio() -> None:
    anchors = [
        {
            "focal_user": 0,
            "legal_physical_change": True,
            "base_metrics": _metrics(10.0, 1.0, 2),
            "selected_metrics": _metrics(9.0, 0.5, 2),
        },
        {
            "focal_user": 0,
            "legal_physical_change": True,
            "base_metrics": _metrics(90.0, 9.0, 2),
            "selected_metrics": _metrics(92.0, 10.0, 2),
        },
    ]
    pooled = cc.pool_unit_receipts([{"anchors": anchors}])
    exact = pooled["exact"]
    eta_selected = Fraction(
        int(exact["eta_selected"]["numerator"]),
        int(exact["eta_selected"]["denominator"]),
    )
    assert eta_selected == Fraction(101, 1) / Fraction.from_float(10.5)
    assert pooled["outcome"] == "C_C_FAST_SCREEN_NO_SUPPORT"
    assert pooled["reasons"] == ["EE_NOT_ABOVE_BASE"]


@pytest.mark.parametrize(
    ("lost", "outcome", "reasons"),
    [
        (2, "C_C_FAST_SCREEN_SUPPORT", []),
        (3, "C_C_FAST_SCREEN_NO_SUPPORT", ["SERVICE_NONINFERIORITY_FAILED"]),
    ],
)
def test_exact_lost_service_boundary_over_2400_opportunities(
    lost: int, outcome: str, reasons: list[str]
) -> None:
    anchor = {
        "focal_user": 0,
        "legal_physical_change": True,
        "base_metrics": _metrics(100.0, 10.0, 2400, users=2400),
        "selected_metrics": _metrics(100.0, 9.0, 2400 - lost, users=2400),
    }
    pooled = _pooled(anchor)
    assert pooled["outcome"] == outcome
    assert pooled["reasons"] == reasons
