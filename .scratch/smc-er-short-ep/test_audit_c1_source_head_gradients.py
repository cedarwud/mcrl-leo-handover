from __future__ import annotations

import copy

import numpy as np
import pytest
import torch
import torch.nn as nn

import audit_c1_source_head_gradients as audit
from smc_er_core import AtomicBundle


class TinyQ(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.linear = nn.Linear(3, 2)

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return self.linear(value)


def bundle(
    *,
    source: str,
    bundle_id: str,
    block: int = 0,
    step: int = 0,
    reward: float = 8.0,
) -> AtomicBundle:
    states = np.array([[1.0, 0.5, -0.25], [0.25, -0.5, 1.0]], dtype=np.float32)
    masks = np.ones((2, 2), dtype=bool)
    rewards = np.array(
        [[reward, -1.0, -2.0], [reward / 2.0, 0.0, -1.0]],
        dtype=np.float64,
    )
    return AtomicBundle(
        bundle_id=bundle_id,
        source_id=source,
        source_policy_version=0,
        block_id=block,
        step_index=step,
        states=states,
        actions=np.array([0, 1], dtype=np.int64),
        rewards=rewards,
        next_states=states + 0.1,
        masks=masks,
        next_masks=masks,
        done=False,
    )


def gradient_config() -> audit.GradientConfig:
    return audit.GradientConfig(
        discount_factor=0.9,
        reward_calibration_enabled=True,
        reward_calibration_scales=(2.0, 1.0, 2.0),
    )


def test_pairing_fails_closed_on_missing_and_duplicate_keys() -> None:
    mains = [bundle(source="Main", bundle_id="m0")]
    c1s = [bundle(source="C1", bundle_id="c0")]
    pairs, prefill = audit.pair_online_bundles(
        mains, c1s, expected_count=1, expected_prefill=0
    )
    assert len(pairs) == 1
    assert prefill == 0

    with pytest.raises(audit.AuditError, match="count mismatch"):
        audit.pair_online_bundles(mains, [], expected_count=1)

    duplicate = bundle(source="Main", bundle_id="m1", block=0, step=0)
    with pytest.raises(audit.AuditError, match="duplicate Main bundle"):
        audit.pair_online_bundles(
            [mains[0], duplicate],
            [c1s[0], bundle(source="C1", bundle_id="c1", block=0, step=1)],
            expected_count=2,
        )


def test_cosine_reports_zero_norm_as_undefined() -> None:
    result = audit.cosine_metric(torch.zeros(4), torch.ones(4))
    assert result["status"] == "UNDEFINED_ZERO_NORM"
    assert result["value"] is None


def test_hash_mismatch_fails_closed(tmp_path) -> None:
    path = tmp_path / "input.bin"
    path.write_bytes(b"sealed")
    with pytest.raises(audit.AuditError, match="SHA-256 mismatch"):
        audit.verify_sha256(path, "0" * 64, label="synthetic input")


def test_autograd_diagnostic_does_not_mutate_parameters() -> None:
    torch.manual_seed(7)
    online = TinyQ()
    target = copy.deepcopy(online)
    initial = audit.InitialMain(
        online=nn.ModuleList([online]), targets=nn.ModuleList([target])
    )
    before = audit.parameter_snapshot(initial)
    ledger = audit.CalibrationLedger()
    loss, gradient, rows = audit.td_loss_and_gradient(
        online,
        target,
        bundle(source="Main", bundle_id="main"),
        objective=0,
        config=gradient_config(),
        calibration_ledger=ledger,
        calibration_key=("test", "Main", "main", "0"),
    )
    after = audit.parameter_snapshot(initial)
    assert loss > 0.0
    assert rows == 2
    assert gradient.numel() == sum(parameter.numel() for parameter in online.parameters())
    assert before == after
    assert all(parameter.grad is None for parameter in online.parameters())


def test_calibration_is_applied_once_and_duplicate_application_rejected() -> None:
    ledger = audit.CalibrationLedger()
    key = ("arm", "Main", "bundle", "0")
    calibrated = ledger.apply(
        key,
        np.array([8.0], dtype=np.float64),
        enabled=True,
        scale=2.0,
    )
    np.testing.assert_array_equal(calibrated, np.array([4.0]))
    with pytest.raises(audit.AuditError, match="more than once"):
        ledger.apply(
            key,
            np.array([8.0], dtype=np.float64),
            enabled=True,
            scale=2.0,
        )


def test_output_refuses_overwrite(tmp_path) -> None:
    output = tmp_path / "audit.json"
    audit.write_json_exclusive(output, {"first": True})
    with pytest.raises(audit.AuditError, match="refusing to overwrite"):
        audit.write_json_exclusive(output, {"second": True})
    assert output.read_text(encoding="utf-8") == '{\n  "first": true\n}\n'
