"""Pure mocked tests for the V0.18 simulator source adapter.

These tests do not import the real simulator runner, open TLE data, load a
checkpoint, or execute a physical step.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import sys

import numpy as np
import pytest


R2_ROOT = Path(__file__).resolve().parents[1]
REPO = R2_ROOT.parents[2]
sys.path.insert(0, str(R2_ROOT))
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / ".scratch/multi-catfish-v018-relational-zr/next-learner-draft"))

from mcrl.runtime.ee_axis_ops3 import OPS3_KAPPA_BITS  # noqa: E402
import relational_simulator_source_adapter as adapter  # noqa: E402


def _config(tmp_path: Path) -> adapter.SimulatorShardConfig:
    digest = "a" * 64
    code_manifest = tmp_path / "code-manifest.sha256"
    code_manifest.write_text("synthetic code closure\n", encoding="utf-8")
    return adapter.SimulatorShardConfig(
        config_sha256=digest,
        contract_path=tmp_path / "contract.md",
        contract_sha256="b" * 64,
        code_manifest_path=code_manifest,
        code_manifest_sha256=hashlib.sha256(code_manifest.read_bytes()).hexdigest(),
        split="TRAIN",
        world_seed=2026120501,
        lineage=2026092101,
        declared_worlds=(2026120501,),
        declared_lineages=(2026092101,),
        field_root_digest="c" * 64,
        q1_checkpoint_root=tmp_path / "q1",
        q2_checkpoint_root=tmp_path / "q2",
        prereg_path=tmp_path / "prereg.json",
        tle_root=tmp_path / "tle",
        output_dir=tmp_path / "out",
        q1_checkpoint_sha256="d" * 64,
        q2_checkpoint_sha256="e" * 64,
        q1_parameter_sha256="f" * 64,
        q2_parameter_sha256="1" * 64,
        kappa_bits=float(OPS3_KAPPA_BITS),
    )


def _canonical(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def test_config_requires_external_digest_and_closed_frozen_identity(tmp_path: Path) -> None:
    code_manifest = tmp_path / "code-manifest.sha256"
    code_manifest.write_text("synthetic code closure\n", encoding="utf-8")
    payload = {
        "schema": adapter.ADAPTER_SCHEMA,
        "schema_version": adapter.ADAPTER_SCHEMA_VERSION,
        "contract_path": "contract.md",
        "contract_sha256": "b" * 64,
        "code_manifest_path": code_manifest.name,
        "code_manifest_sha256": hashlib.sha256(code_manifest.read_bytes()).hexdigest(),
        "split": "TRAIN",
        "world_seed": 2026120501,
        "lineage": 2026092101,
        "declared_worlds": [2026120501],
        "declared_lineages": [2026092101],
        "field_root_digest": "c" * 64,
        "q1_checkpoint_root": "q1",
        "q2_checkpoint_root": "q2",
        "prereg_path": "prereg.json",
        "tle_root": "tle",
        "output_dir": "out",
        "q1_checkpoint_sha256": "d" * 64,
        "q2_checkpoint_sha256": "e" * 64,
        "q1_parameter_sha256": "f" * 64,
        "q2_parameter_sha256": "1" * 64,
        "kappa_bits_hex": float(OPS3_KAPPA_BITS).hex(),
        "users": 100,
        "steps": 10,
        "action_dim": 28,
        "contract_status": "FROZEN_BEFORE_OUTCOME",
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
    }
    path = tmp_path / "config.json"
    path.write_bytes(_canonical(payload))
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    config = adapter.load_shard_config(path, expected_sha256=expected)
    assert config.config_sha256 == expected
    assert config.q1_checkpoint_root == (tmp_path / "q1").absolute()
    assert config.code_manifest_path == (tmp_path / "code-manifest.sha256").absolute()
    with pytest.raises(adapter.SimulatorSourceAdapterError, match="digest"):
        adapter.load_shard_config(path, expected_sha256="0" * 64)


def test_exact_label_persists_builder_z3_bits_not_normalized_q3() -> None:
    rows = 2
    legal = np.ones((rows, 28), dtype=np.bool_)
    compatibility = np.zeros((rows, 28), dtype=np.bool_)
    compatibility[:, 1] = True
    references = np.zeros(rows, dtype=np.int64)
    baseline = np.ones((rows, rows), dtype=np.float64)
    candidate = np.ones((rows, 28, rows), dtype=np.float64)
    calls: list[dict[str, object]] = []

    def builder(**kwargs: object) -> object:
        calls.append(kwargs)
        bits = np.zeros(28, dtype=np.float64)
        bits[1] = 128.0
        return SimpleNamespace(z3_bits=bits, q3_values=np.full(28, 2.0))

    measurement = SimpleNamespace(
        reference_actions=references,
        legal_mask=legal,
        compatible=compatibility,
        reference_rate_bps=baseline,
        candidate_rate_bps=candidate,
    )
    label = adapter.build_exact_zr_label(
        measurement,
        1.0,
        kappa_bits=64.0,
        zr_builder=builder,
    )
    assert len(calls) == rows
    assert np.all(label.z3_bits[:, 1] == 128.0)
    assert np.all(label.z3_bits[:, 1] != 2.0)
    np.testing.assert_array_equal(label.positive_credit_compatible, compatibility)


def test_exact_label_rejects_positive_bits_outside_compatibility() -> None:
    legal = np.ones((1, 28), dtype=np.bool_)
    measurement = SimpleNamespace(
        reference_actions=np.zeros(1, dtype=np.int64),
        legal_mask=legal,
        compatible=np.zeros((1, 28), dtype=np.bool_),
        reference_rate_bps=np.ones((1, 1), dtype=np.float64),
        candidate_rate_bps=np.ones((1, 28, 1), dtype=np.float64),
    )

    def builder(**_kwargs: object) -> object:
        bits = np.zeros(28, dtype=np.float64)
        bits[1] = 1.0
        return SimpleNamespace(z3_bits=bits)

    with pytest.raises(adapter.SimulatorSourceAdapterError, match="compatibility"):
        adapter.build_exact_zr_label(
            measurement,
            1.0,
            kappa_bits=64.0,
            zr_builder=builder,
        )


def test_learner_contract_and_prior_analytic_contract_are_validated_separately(
    tmp_path: Path,
) -> None:
    contract = tmp_path / "contract.md"
    contract.write_text("Status: `FROZEN_BEFORE_OUTCOME`\n", encoding="utf-8")
    config = replace(
        _config(tmp_path),
        contract_sha256=hashlib.sha256(contract.read_bytes()).hexdigest(),
    )
    calls: list[tuple[object, ...]] = []
    q1 = object()
    q2 = object()

    def validate_analytic(*args: object) -> None:
        calls.append(args)
        assert args == ()

    v018 = SimpleNamespace(validate_v018_contract=validate_analytic)
    v015 = SimpleNamespace(
        validate_v015_contract=lambda: None,
        validate_v014_gate_receipts=lambda _root: {"gate": "ok"},
        load_frozen_q1=lambda _root, _lineage: (
            q1,
            {"checkpoint_sha256": config.q1_checkpoint_sha256},
        ),
        load_frozen_q2=lambda _root, lineage, gate_receipt: (
            q2,
            {"checkpoint_sha256": config.q2_checkpoint_sha256},
        ),
        _q_parameter_sha256=lambda network: (
            config.q1_parameter_sha256
            if network is q1
            else config.q2_parameter_sha256
        ),
    )
    runtime = adapter.RuntimeBindings(v018=v018, v015=v015, zr_builder=lambda **_: None)  # type: ignore[arg-type]
    loaded = adapter._validate_frozen_bindings(config, runtime)
    assert loaded[0] is q1
    assert loaded[2] is q2
    assert calls == [()]


def test_code_manifest_digest_is_checked_before_frozen_q_loading(
    tmp_path: Path,
) -> None:
    config = replace(_config(tmp_path), code_manifest_sha256="0" * 64)
    calls: list[str] = []
    runtime = adapter.RuntimeBindings(
        v018=SimpleNamespace(
            validate_v018_contract=lambda: calls.append("v018"),
        ),
        v015=SimpleNamespace(
            validate_v015_contract=lambda: calls.append("v015"),
            load_frozen_q1=lambda *_args: calls.append("q1"),
            load_frozen_q2=lambda *_args, **_kwargs: calls.append("q2"),
        ),
        zr_builder=lambda **_: None,
    )  # type: ignore[arg-type]

    with pytest.raises(adapter.SimulatorSourceAdapterError, match="code manifest"):
        adapter._validate_frozen_bindings(config, runtime)
    assert calls == []


def test_mocked_v018_v015_wiring_produces_exactly_ten_anchor_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config(tmp_path)
    users = config.users
    masks = np.ones((users, 28), dtype=np.bool_)
    state = np.zeros((users, 4), dtype=np.float32)
    gains = np.ones((users, 28), dtype=np.float64)
    ops3_anchor = SimpleNamespace(
        current_gain_linear=gains,
        segment_start_gain_linear=gains,
    )
    q2_state = SimpleNamespace(
        action_masks=masks, state_matrix=state, verify=lambda: None
    )
    calls: list[int] = []

    def fake_make(**kwargs: object) -> object:
        calls.append(int(kwargs["step_index"]))
        assert np.asarray(kwargs["q1"]).shape == (users, 28)
        assert np.asarray(kwargs["learned_q2"]).shape == (users, 28)
        return SimpleNamespace(step_index=int(kwargs["step_index"]))

    monkeypatch.setattr(adapter, "make_v018_anchor_input", fake_make)
    v018 = SimpleNamespace(
        BEAM_POWER_MAX_W=1.0,
        encode_ee_axis_state=lambda _env, _observation: SimpleNamespace(
            action_masks=masks, state_matrix=state
        ),
        _q1_values=lambda _network, _states, _masks: np.zeros((users, 28)),
        snapshot_ops3_anchor=lambda _env, _observation: ops3_anchor,
        project_ops3_anchor=lambda _anchor: object(),
        build_ops3_live_surfaces=lambda _anchor, _projection, _references: object(),
        _q2_values=lambda _network, _states, _masks: np.zeros((users, 28)),
        _current_required_power_and_opening=lambda **_kwargs: (gains, masks),
    )
    v015 = SimpleNamespace(
        select_actions=lambda _q1, _q2, _q3, _masks, include_c3: np.zeros(
            users, dtype=np.int64
        ),
        encode_ee_axis_v014_q2_states=lambda _surfaces: q2_state,
    )
    runtime = adapter.RuntimeBindings(v018=v018, v015=v015, zr_builder=lambda **_: None)  # type: ignore[arg-type]
    provider = adapter._anchor_provider(
        config,
        runtime,
        environment=object(),
        step_env=object(),
        env_rng=np.random.default_rng(1),
        observation=object(),
        q1=object(),
        q1_receipt={"checkpoint_path": str(tmp_path / "q1.pt")},
        q2=object(),
        q2_receipt={"checkpoint_path": str(tmp_path / "q2.pt")},
        interval_s=1.0,
    )
    anchors = [provider(step) for step in range(config.steps)]
    assert [anchor.step_index for anchor in anchors] == list(range(10))
    assert calls == list(range(10))
