"""Fast actual-class tests for the scratch-only D40/current loader."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import sys

import pytest
import torch

from mcrl.algorithms.ee_axis_action_shared import EEAxisActionSharedConfig
from mcrl.algorithms.ee_axis_lcsrs_three_route import (
    EEAxisLCSRSThreeRoute,
    LCSRSThreeRouteConfig,
)


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("d40_current_loader_under_test", HERE / "d40_current_loader.py")
assert SPEC is not None and SPEC.loader is not None
API = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = API
SPEC.loader.exec_module(API)


def _config() -> LCSRSThreeRouteConfig:
    return LCSRSThreeRouteConfig(
        q12=EEAxisActionSharedConfig(
            state_dim=228,
            action_dim=28,
            hidden_layers=(8,),
            activation="relu",
            learning_rate=1.0e-2,
            kappa_bits=10.0,
            beta=0.2,
            loss_weights=(1.0, 2.0, 3.0),
        )
    )


def _model(
    seed: int = 17, config: LCSRSThreeRouteConfig | None = None
) -> EEAxisLCSRSThreeRoute:
    return EEAxisLCSRSThreeRoute(
        _config() if config is None else config,
        train_seed=seed,
    )


def _config_matching_d40_q1() -> LCSRSThreeRouteConfig:
    """Copy only the authenticated D40 Q1 config for the rejection test."""

    raw = dict(API.inspect_d40_checkpoint()["q1"]["config"])
    return LCSRSThreeRouteConfig(q12=EEAxisActionSharedConfig(**raw))


def _state_snapshot(model: EEAxisLCSRSThreeRoute) -> tuple[dict[str, torch.Tensor], ...]:
    return tuple(
        {
            name: tensor.detach().clone()
            for name, tensor in network.state_dict().items()
        }
        for network in model.q_networks
    )


def _assert_state_equal(
    actual: tuple[dict[str, torch.Tensor], ...],
    expected: tuple[dict[str, torch.Tensor], ...],
) -> None:
    assert len(actual) == len(expected)
    for actual_network, expected_network in zip(actual, expected, strict=True):
        assert set(actual_network) == set(expected_network)
        for name in actual_network:
            assert torch.equal(actual_network[name], expected_network[name]), name


def _assert_optimizer_state_equal(actual: object, expected: object) -> None:
    if isinstance(actual, torch.Tensor) and isinstance(expected, torch.Tensor):
        assert torch.equal(actual, expected)
        return
    if isinstance(actual, dict) and isinstance(expected, dict):
        assert set(actual) == set(expected)
        for key in actual:
            _assert_optimizer_state_equal(actual[key], expected[key])
        return
    if isinstance(actual, (list, tuple)) and isinstance(expected, (list, tuple)):
        assert len(actual) == len(expected)
        for left, right in zip(actual, expected, strict=True):
            _assert_optimizer_state_equal(left, right)
        return
    assert actual == expected


def test_actual_d40_checkpoint_is_authenticated_and_actual_v020_split_is_inspected() -> None:
    inspection = API.inspect_d40_checkpoint()

    assert inspection["checkpoint_sha256"] == API.D40_CHECKPOINT_SHA256
    assert inspection["checkpoint_schema"] == API.D40_CHECKPOINT_SCHEMA
    assert inspection["source_split"] == "V0.20"
    assert inspection["legacy_q3_present"] is False
    assert inspection["q1"]["source_field"] == "q1.q_networks[0]"
    assert inspection["q1"]["algorithm"] == API.D40_Q1_ALGORITHM
    assert inspection["q1"]["network_count"] == 3
    assert inspection["q2"]["source_field"] == "q2.q"
    assert inspection["q2"]["algorithm"] == API.D40_Q2_ALGORITHM

    q1_shapes = {
        item["key"]: tuple(item["shape"])
        for item in inspection["q1"]["state_dict"]
    }
    q2_shapes = {
        item["key"]: tuple(item["shape"])
        for item in inspection["q2"]["state_dict"]
    }
    assert q1_shapes["scorer.0.weight"] == (100, 28)
    assert q2_shapes["scorer.0.weight"] == (100, 48)


def test_real_d40_stops_with_precise_incompatibility_report_before_mutation() -> None:
    model = _model(config=_config_matching_d40_q1())
    before = _state_snapshot(model)

    with pytest.raises(API.D40CompatibilityError) as raised:
        API.load_authenticated_d40_into_current_model(model)

    error = raised.value
    fields = {item.field for item in error.report.mismatches}
    assert "q1.algorithm" in fields
    assert "q1.architecture.scorer_input_width" in fields
    assert "q1.q_networks[0].scorer.0.weight" in fields
    assert "q2.algorithm" in fields
    assert "q2.architecture.scorer_input_width" in fields
    assert "q2.q.scorer.0.weight" in fields
    assert "shape=(100, 12)" in str(error)
    assert "shape=(100, 28)" in str(error)
    assert "shape=(100, 48)" in str(error)
    _assert_state_equal(_state_snapshot(model), before)


def test_actual_class_q1_q2_tensors_are_copied_exactly_and_q3_is_untouched() -> None:
    donor = _model(seed=101)
    target = _model(seed=202)
    q3_before = {
        name: tensor.detach().clone()
        for name, tensor in target.q3.state_dict().items()
    }

    loaded = API.load_exact_compatible_q12_parameters(
        target,
        q1_state=donor.q1.state_dict(),
        q2_state=donor.q2.state_dict(),
    )

    assert loaded == tuple(
        [f"q1.{name}" for name in sorted(donor.q1.state_dict())]
        + [f"q2.{name}" for name in sorted(donor.q2.state_dict())]
    )
    for name, tensor in donor.q1.state_dict().items():
        assert torch.equal(target.q1.state_dict()[name], tensor)
    for name, tensor in donor.q2.state_dict().items():
        assert torch.equal(target.q2.state_dict()[name], tensor)
    for name, tensor in q3_before.items():
        assert torch.equal(target.q3.state_dict()[name], tensor)


def test_q3_is_deterministic_and_isolated_from_different_q1_q2_sources() -> None:
    donor_a = _model(seed=301)
    donor_b = _model(seed=302)
    target_a = _model(seed=777)
    target_b = _model(seed=777)

    API.load_exact_compatible_q12_parameters(
        target_a,
        q1_state=donor_a.q1.state_dict(),
        q2_state=donor_a.q2.state_dict(),
    )
    API.load_exact_compatible_q12_parameters(
        target_b,
        q1_state=donor_b.q1.state_dict(),
        q2_state=donor_b.q2.state_dict(),
    )

    for left, right in zip(target_a.q3.state_dict().values(), target_b.q3.state_dict().values(), strict=True):
        assert torch.equal(left, right)
    assert any(
        not torch.equal(left, right)
        for left, right in zip(target_a.q1.state_dict().values(), target_b.q1.state_dict().values(), strict=True)
    )

    different_seed = _model(seed=778)
    assert any(
        not torch.equal(left, right)
        for left, right in zip(target_a.q3.state_dict().values(), different_seed.q3.state_dict().values(), strict=True)
    )


def test_wrong_digest_is_rejected_before_payload_read(tmp_path: Path) -> None:
    copied = tmp_path / "tampered.pt"
    copied.write_bytes(API.D40_CHECKPOINT_PATH.read_bytes() + b"tamper")
    with pytest.raises(API.D40DigestMismatchError, match="hash mismatch"):
        API.inspect_d40_checkpoint(copied)


def test_legacy_q3_and_malformed_split_are_rejected() -> None:
    import torch as torch_local

    payload = torch_local.load(
        API.D40_CHECKPOINT_PATH, map_location="cpu", weights_only=True
    )
    legacy = deepcopy(payload)
    legacy["q3"] = {"legacy": True}
    with pytest.raises(API.D40LegacyQ3Error, match="legacy Q3"):
        API.inspect_authenticated_d40_payload(legacy)

    missing_split = deepcopy(payload)
    del missing_split["q2"]
    with pytest.raises(API.D40MalformedCheckpointError, match="root.q2"):
        API.inspect_authenticated_d40_payload(missing_split)

    partial = deepcopy(payload)
    del partial["q2"]["q"]["scorer.0.bias"]
    with pytest.raises(API.D40CompatibilityError) as raised:
        API.load_exact_compatible_q12_parameters(
            _model(),
            q1_state=partial["q1"]["q_networks"][0],
            q2_state=partial["q2"]["q"],
        )
    assert any(
        item.reason == "missing parameter key"
        and item.field.endswith("scorer.0.bias")
        for item in raised.value.report.mismatches
    )


def test_wrong_shape_is_rejected_without_partial_load() -> None:
    donor = _model(seed=401)
    target = _model(seed=402)
    before = _state_snapshot(target)
    q1_bad = {name: tensor.detach().clone() for name, tensor in donor.q1.state_dict().items()}
    q1_bad["scorer.0.weight"] = q1_bad["scorer.0.weight"][:, :-1]

    with pytest.raises(API.D40CompatibilityError, match="no tensors were loaded"):
        API.load_exact_compatible_q12_parameters(
            target, q1_state=q1_bad, q2_state=donor.q2.state_dict()
        )
    _assert_state_equal(_state_snapshot(target), before)


def test_forbidden_mode_and_five_arm_label_are_rejected() -> None:
    with pytest.raises(API.D40ModeError, match="PLUMBING_ONLY"):
        API.load_authenticated_d40_into_current_model(_model(), use_mode="EVALUATE")
    with pytest.raises(API.D40PolicyLabelError, match="five-arm"):
        API.load_authenticated_d40_into_current_model(
            _model(), output_label="trained five-arm policy"
        )


def test_round_trip_current_checkpoint_parity_after_exact_structural_load() -> None:
    donor = _model(seed=501)
    original = _model(seed=502)
    API.load_exact_compatible_q12_parameters(
        original,
        q1_state=donor.q1.state_dict(),
        q2_state=donor.q2.state_dict(),
    )
    checkpoint = deepcopy(original.checkpoint_state(update_count=19))

    resumed = _model(seed=502)
    assert resumed.load_checkpoint_state(checkpoint) == 19
    _assert_state_equal(_state_snapshot(resumed), _state_snapshot(original))
    for resumed_optimizer, original_optimizer in zip(
        resumed.optimizers, original.optimizers, strict=True
    ):
        _assert_optimizer_state_equal(
            resumed_optimizer.state_dict(), original_optimizer.state_dict()
        )


def test_explicit_q3_seed_is_required_by_the_build_entry_point() -> None:
    with pytest.raises(TypeError, match="q3_seed"):
        API.build_plumbing_only_model(_config())  # type: ignore[call-arg]
