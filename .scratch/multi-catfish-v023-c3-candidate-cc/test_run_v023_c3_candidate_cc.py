from __future__ import annotations

from fractions import Fraction
import hashlib
import json
from pathlib import Path
import stat

import numpy as np
import pytest

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
