from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import torch


MODULE_PATH = Path(__file__).resolve().parents[1] / "v019_physical_adapter.py"
SPEC = importlib.util.spec_from_file_location("v019_physical_adapter_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

LAUNCHER_PATH = MODULE_PATH.parent / "run_v019_five_arm_screen_server.py"
sys.path.insert(0, str(MODULE_PATH.parent))
LAUNCHER_SPEC = importlib.util.spec_from_file_location(
    "run_v019_five_arm_screen_server_under_test", LAUNCHER_PATH
)
assert LAUNCHER_SPEC is not None and LAUNCHER_SPEC.loader is not None
LAUNCHER = importlib.util.module_from_spec(LAUNCHER_SPEC)
sys.modules[LAUNCHER_SPEC.name] = LAUNCHER
LAUNCHER_SPEC.loader.exec_module(LAUNCHER)


def test_gate_binding_requires_exact_pass_result(tmp_path: Path) -> None:
    payload = {
        "schema": MODULE.GATE_RESULT_SCHEMA,
        "decision": MODULE.GATE_DECISION,
        "output_unit_mode": MODULE.Q3_OUTPUT_UNIT_MODE,
        "contract_sha256": "a" * 64,
        "source_panel_sha256": "b" * 64,
        "code_manifest_sha256": "c" * 64,
        "independent_verification_sha256": "d" * 64,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
    }
    path = tmp_path / "gate.json"
    path.write_bytes(MODULE._canonical_bytes(payload))
    binding = MODULE.authenticate_gate_result(
        path,
        expected_result_sha256=MODULE.file_sha256(path),
    )
    assert binding.result_sha256 == MODULE.file_sha256(path)
    assert binding.contract_sha256 == "a" * 64

    changed = {**payload, "decision": "STOP_LEARNER_GATE"}
    path.write_bytes(MODULE._canonical_bytes(changed))
    try:
        MODULE.authenticate_gate_result(
            path,
            expected_result_sha256=binding.result_sha256,
        )
    except MODULE.V019PhysicalAdapterError as error:
        assert "digest" in str(error)
    else:  # pragma: no cover - assertion branch
        raise AssertionError("changed gate bytes must not authenticate")


def test_q3_loader_freezes_normalized_100_update_checkpoint(tmp_path: Path) -> None:
    config = MODULE.RelationalZRC3LearnerConfig(
        action_dim=28,
        action_context_dim=7,
        victim_token_dim=6,
        hidden_layers=(100, 50, 50),
        activation="tanh",
        learning_rate=0.001,
        kappa_bits=float(MODULE.OPS3_KAPPA_BITS),
        beta=0.0,
        output_unit_mode=MODULE.Q3_OUTPUT_UNIT_MODE,
    )
    learner = MODULE.RelationalZRC3PairwiseLearner(config, train_seed=2026120711)
    # This is a synthetic checkpoint fixture only; no source or learner run
    # is opened by the adapter test.
    learner.update_count = MODULE.Q3_UPDATE_RUNG
    path = tmp_path / "checkpoint.pt"
    learner.save_checkpoint(
        path,
        contract_sha256="a" * 64,
        source_sha256="b" * 64,
        code_manifest_sha256="c" * 64,
    )
    head = MODULE.load_q3_head(
        path,
        expected_checkpoint_sha256=MODULE.file_sha256(path),
        initialization_seed=2026120711,
        source_lineage=2026092101,
        contract_sha256="a" * 64,
        source_sha256="b" * 64,
        code_manifest_sha256="c" * 64,
    )
    assert head.learner.update_count == 100
    assert head.learner.config.output_unit_mode == MODULE.Q3_OUTPUT_UNIT_MODE
    assert all(not parameter.requires_grad for parameter in head.learner.q3.parameters())


def test_tensor_policy_snapshots_compare_bitwise() -> None:
    left = ({"q": torch.tensor([1.0, 2.0])},)
    right = ({"q": torch.tensor([1.0, 2.0])},)
    changed = ({"q": torch.tensor([1.0, 3.0])},)
    assert MODULE._snapshots_equal(left, right)
    assert not MODULE._snapshots_equal(left, changed)


def test_launcher_only_exposes_explicit_post_pass_execution_boundary() -> None:
    checklist = LAUNCHER.required_runtime_inputs()
    assert checklist["schema"] == LAUNCHER.RUNTIME_INPUT_SCHEMA
    assert checklist["fixed"]["episodes"] == 100
    assert checklist["fixed"]["checkpoint_every_episodes"] == 100
    assert checklist["fixed"]["q3_output_unit_mode"] == "normalized_bits_per_kappa"
    assert "initialization_to_source_lineage_mapping" in checklist["required_after_pass"]
