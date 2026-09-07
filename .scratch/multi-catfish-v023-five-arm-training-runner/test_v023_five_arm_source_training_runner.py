"""Fast real-class tests for the isolated V0.23 source-training runner."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pytest
import torch

from mcrl.algorithms.ee_axis_action_shared import EEAxisActionSharedConfig
from mcrl.algorithms.ee_axis_lcsrs_c3_head import LCSRSC3HeadConfig
from mcrl.algorithms.ee_axis_lcsrs_three_route import (
    EEAxisLCSRSThreeRoute,
    LCSRSThreeRouteConfig,
)
from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch
from mcrl.algorithms.ee_axis_v014_head import (
    EEAxisV014HeadConfig,
    EEAxisV014NormalizedPairBatch,
)
from mcrl.runtime.ee_axis_lcsrs_c3_dataset import (
    LCSRS_DRAW_COUNT,
    LCSRS_ROW_REFERENCE,
    LCSRSAnchorSurface,
    LCSRSPairTargets,
    assemble_lcsrs_anchor_surface,
)
from mcrl.runtime.ee_axis_lcsrs_c3_learner import LCSRSC3SampledBatch
from mcrl.runtime.ee_axis_lcsrs_c3_state import assemble_c3_view


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "v023_five_arm_source_training_runner_under_test",
    HERE / "v023_five_arm_source_training_runner.py",
)
assert SPEC is not None and SPEC.loader is not None
API = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = API
SPEC.loader.exec_module(API)

REAL_ONE_WORLD_SPEC = importlib.util.spec_from_file_location(
    "v023_real_one_world_plumbing_for_source_runner_test",
    HERE.parent
    / "multi-catfish-v023-real-one-world-plumbing"
    / "v023_real_one_world_plumbing.py",
)
assert REAL_ONE_WORLD_SPEC is not None and REAL_ONE_WORLD_SPEC.loader is not None
REAL_ONE_WORLD = importlib.util.module_from_spec(REAL_ONE_WORLD_SPEC)
sys.modules[REAL_ONE_WORLD_SPEC.name] = REAL_ONE_WORLD
REAL_ONE_WORLD_SPEC.loader.exec_module(REAL_ONE_WORLD)

PHYSICAL_EVAL_SPEC = importlib.util.spec_from_file_location(
    "v023_five_arm_eval_binding_for_source_runner_test",
    HERE.parent
    / "multi-catfish-v023-five-arm-evaluation"
    / "v023_five_arm_eval_binding.py",
)
assert PHYSICAL_EVAL_SPEC is not None and PHYSICAL_EVAL_SPEC.loader is not None
PHYSICAL_EVAL = importlib.util.module_from_spec(PHYSICAL_EVAL_SPEC)
sys.modules[PHYSICAL_EVAL_SPEC.name] = PHYSICAL_EVAL
PHYSICAL_EVAL_SPEC.loader.exec_module(PHYSICAL_EVAL)

DIGEST = "a" * 64
LATER_DIGEST = "b" * 64


@pytest.fixture(scope="module", autouse=True)
def _single_torch_thread():
    previous = torch.get_num_threads()
    torch.set_num_threads(1)
    yield
    torch.set_num_threads(previous)


class ProviderExhausted(RuntimeError):
    pass


def _model_config() -> LCSRSThreeRouteConfig:
    q1 = EEAxisActionSharedConfig(
        state_dim=228,
        action_dim=28,
        hidden_layers=(2,),
        activation="relu",
        learning_rate=1.0e-2,
        kappa_bits=10.0,
        beta=0.2,
        loss_weights=(1.0, 2.0, 3.0),
    )
    q2 = EEAxisV014HeadConfig(
        action_dim=28,
        local_feature_dim=16,
        global_feature_dim=0,
        hidden_layers=(100, 50, 50),
        activation="tanh",
        learning_rate=1.0e-3,
        kappa_bits=q1.kappa_bits,
        beta=0.1,
    )
    return LCSRSThreeRouteConfig(q1=q1, q2=q2)


def _current_one_world_config_from_checkpoint_state(
    state: Mapping[str, Any],
) -> LCSRSThreeRouteConfig:
    """Decode the current heterogeneous config for the legacy plumbing fixture."""

    raw = state["config"]
    q1_values = dict(raw["q1"])
    q12_values = dict(raw["q12"])
    q2_values = dict(raw["q2"])
    q3_values = dict(raw["q3"])
    for values, fields in (
        (q1_values, ("hidden_layers", "loss_weights")),
        (q12_values, ("hidden_layers", "loss_weights")),
        (q2_values, ("hidden_layers",)),
        (q3_values, ("hidden_layers",)),
    ):
        for field in fields:
            if isinstance(values.get(field), list):
                values[field] = tuple(values[field])
    return LCSRSThreeRouteConfig(
        q1=EEAxisActionSharedConfig(**q1_values),
        q12=EEAxisActionSharedConfig(**q12_values),
        q2=EEAxisV014HeadConfig(**q2_values),
        q3=LCSRSC3HeadConfig(**q3_values),
        q3_learning_rate=raw["q3_learning_rate"],
        q3_betas=tuple(raw["q3_betas"]),
        q3_epsilon=raw["q3_epsilon"],
        q3_weight_decay=raw["q3_weight_decay"],
    )


def _pair_batch(target: float) -> EEAxisPairBatch:
    rows = 2
    states = np.zeros((rows, 228), dtype=np.float32)
    states[:, 0] = (0.25, -0.5)
    states[:, 1] = (-0.75, 0.5)
    return EEAxisPairBatch(
        states=states,
        reference_actions=np.asarray((0, 1), dtype=np.int64),
        candidate_actions=np.asarray((1, 2), dtype=np.int64),
        target_surplus_bits=np.asarray((target, target + 0.25), dtype=np.float64),
        action_masks=np.ones((rows, 28), dtype=np.bool_),
    )


def _normalized_pair_batch(target: float) -> EEAxisV014NormalizedPairBatch:
    rows = 2
    features = np.zeros((rows, 16, 28), dtype=np.float32)
    features[:, 0, 0] = (0.25, -0.5)
    features[:, 0, 1] = (-0.75, 0.5)
    return EEAxisV014NormalizedPairBatch(
        states=features.reshape(rows, 448),
        reference_actions=np.asarray((0, 1), dtype=np.int64),
        candidate_actions=np.asarray((1, 2), dtype=np.int64),
        normalized_target_deltas=np.asarray(
            (target, target + 0.25), dtype=np.float64
        ),
        action_masks=np.ones((rows, 28), dtype=np.bool_),
    )


def _surface(target: float) -> LCSRSAnchorSurface:
    users, actions = 3, 28
    context = np.zeros((users, actions, 29), dtype=np.float32)
    tokens = np.zeros((users, actions, users + 1, 38), dtype=np.float32)
    action_mask = np.zeros((users, actions), dtype=np.bool_)
    action_mask[:, :3] = True
    token_mask = np.zeros((users, actions, users + 1), dtype=np.bool_)
    token_mask[:, :, users] = action_mask
    tokens[:, :, users, 1][action_mask] = 1.0
    tokens[0, 1, users, 2:5] = 1.0
    tokens[1, 1, users, 2:5] = 1.0
    context[0, 1, 0] = 0.2
    context[1, 1, 0] = -0.2
    view = assemble_c3_view(
        action_context=context,
        tokens=tokens,
        token_mask=token_mask,
        action_mask=action_mask,
        reference_actions=np.zeros(users, dtype=np.int64),
    )
    pair = LCSRSPairTargets(
        pair_id=f"fixture-{target}",
        user_ids=np.asarray((0, 1), dtype=np.int64),
        action_ids=np.asarray((1, 1), dtype=np.int64),
        normalized_targets_by_draw=np.tile(
            np.asarray(((target, -target),), dtype=np.float64),
            (LCSRS_DRAW_COUNT, 1),
        ),
    )
    return assemble_lcsrs_anchor_surface(view, (pair,))


def _c3_batch(target: float) -> LCSRSC3SampledBatch:
    return LCSRSC3SampledBatch(
        anchor_indices=np.zeros(3, dtype=np.int64),
        row_classes=np.asarray((3, 3, LCSRS_ROW_REFERENCE), dtype=np.uint8),
        user_indices=np.asarray((0, 1, 2), dtype=np.int64),
        action_indices=np.asarray((1, 1, 0), dtype=np.int64),
        normalized_targets=np.asarray((target, -target, 0.0), dtype=np.float32),
    )


class SyntheticProvider:
    """A deterministic source-only provider with exact resumable cursors."""

    def __init__(
        self,
        *,
        identity: str = "synthetic-source-provider-v1",
        limit: int | None = None,
        planned_epoch_budget: int = 500,
    ) -> None:
        self._identity = identity
        self._limit = limit
        self._planned_epoch_budget = planned_epoch_budget
        self._positions = {(route, source): 0 for route in API.ORCHESTRATOR.ROUTE_ORDER for source in API.ORCHESTRATOR.SOURCE_ORDER}
        self.calls: list[tuple[str, str, int]] = []
        self._pair = {
            source: _pair_batch(2.0 if source == "informed" else -1.0)
            for source in API.ORCHESTRATOR.SOURCE_ORDER
        }
        self._c2 = {
            source: _normalized_pair_batch(
                2.0 if source == "informed" else -1.0
            )
            for source in API.ORCHESTRATOR.SOURCE_ORDER
        }
        self._c3 = {
            source: (
                _c3_batch(2.0 if source == "informed" else -1.0),
                (_surface(2.0 if source == "informed" else -1.0),),
            )
            for source in API.ORCHESTRATOR.SOURCE_ORDER
        }

    def provider_identity(self) -> str:
        return self._identity

    @property
    def planned_epoch_budget(self) -> int:
        return self._planned_epoch_budget

    def next_batch(self, *, route: str, source: str, update_cursor: int):
        key = (route, source)
        position = self._positions[key]
        if self._limit is not None and position >= self._limit:
            raise ProviderExhausted(f"fixture exhausted at {route}/{source}/{position}")
        self._positions[key] = position + 1
        self.calls.append((route, source, update_cursor))
        if route == "C3":
            batch, surfaces = self._c3[source]
            return API.ORCHESTRATOR.ProvidedRouteBatch(
                route=route,
                source=source,
                file_id=f"c3-{source}-{position:04d}",
                batch=batch,
                c3_surfaces=surfaces,
            )
        batch = self._pair[source] if route == "C1" else self._c2[source]
        return API.ORCHESTRATOR.ProvidedRouteBatch(
            route=route,
            source=source,
            file_id=f"{route.lower()}-{source}-{position:04d}",
            batch=batch,
        )

    def sampler_state(self) -> dict[str, Any]:
        return {"positions": deepcopy(self._positions)}

    def load_sampler_state(self, state: dict[str, Any]) -> None:
        self._positions = deepcopy(state["positions"])


def _config(*, budget: int = 500) -> Any:
    return API.FrozenSourceTrainingConfig(
        epoch_budget=budget,
        orchestrator_config=API.ORCHESTRATOR.V023FiveArmOrchestratorConfig.formal(
            model_config=_model_config(), train_seed=17
        ),
        provider_factory_spec="fixtures:make_provider",
        authority_digests=API.RunAuthorityDigests(
            authority_sha256=DIGEST,
            code_sha256="c" * 64,
            input_sha256="d" * 64,
        ),
        later_budget_authority_sha256=LATER_DIGEST if budget > 100 else None,
    )


def _assert_tree_identical(left: Any, right: Any) -> None:
    assert type(left) is type(right)
    if isinstance(left, torch.Tensor):
        assert torch.equal(left, right)
    elif isinstance(left, Mapping):
        assert tuple(left) == tuple(right)
        for key in left:
            _assert_tree_identical(left[key], right[key])
    elif isinstance(left, (list, tuple)):
        assert len(left) == len(right)
        for first, second in zip(left, right, strict=True):
            _assert_tree_identical(first, second)
    else:
        assert left == right


def test_orchestrator_loader_reuses_factory_first_module_by_resolved_path():
    alias_name = "v023_five_arm_orchestrator_for_factory_first_test"
    wanted = API.ORCHESTRATOR_PATH.resolve()
    original_matches = {}
    for name, module in tuple(sys.modules.items()):
        module_file = getattr(module, "__file__", None)
        if isinstance(module_file, str) and Path(module_file).resolve() == wanted:
            original_matches[name] = module
            sys.modules.pop(name, None)
    alias_spec = importlib.util.spec_from_file_location(alias_name, API.ORCHESTRATOR_PATH)
    assert alias_spec is not None and alias_spec.loader is not None
    alias = importlib.util.module_from_spec(alias_spec)
    sys.modules[alias_name] = alias
    alias_spec.loader.exec_module(alias)
    try:
        loaded = API._load_orchestrator_module()
        assert loaded is alias
    finally:
        for name, module in tuple(sys.modules.items()):
            module_file = getattr(module, "__file__", None)
            if isinstance(module_file, str) and Path(module_file).resolve() == wanted:
                sys.modules.pop(name, None)
        sys.modules.update(original_matches)


def test_100_epochs_are_300_updates_with_one_complete_current_five_arm_checkpoint_and_exact_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        REAL_ONE_WORLD,
        "_config_from_checkpoint_state",
        _current_one_world_config_from_checkpoint_state,
    )
    provider = SyntheticProvider()
    runner = API.V023FiveArmSourceTrainingRunner(_config(), provider)
    for arm in API.ARMS:
        assert isinstance(runner.orchestrator.models[arm], EEAxisLCSRSThreeRoute)
    addresses = [
        parameter.detach().untyped_storage().data_ptr()
        for model in runner.orchestrator.models.values()
        for network in model.q_networks
        for parameter in network.parameters()
    ]
    assert len(addresses) == len(set(addresses))

    root = tmp_path / "source-run"
    runner.begin_new(root)
    receipt = runner.run_to_epoch(100)

    assert runner.completed_epochs == 100
    assert runner.orchestrator.update_cursor == 300
    assert receipt is not None and receipt["epoch"] == 100 and receipt["update_count"] == 300
    assert len(provider.calls) == 600
    assert [call[:2] for call in provider.calls[:6]] == [
        ("C1", "neutral"), ("C1", "informed"),
        ("C2", "neutral"), ("C2", "informed"),
        ("C3", "neutral"), ("C3", "informed"),
    ]

    checkpoints = sorted((root / "checkpoints").glob("*.runner.pt"))
    assert [path.name for path in checkpoints] == ["epoch-0100.runner.pt"]
    checkpoint = API._read_torch(checkpoints[0])
    assert checkpoint["arm_order"] == list(API.ARMS)
    assert checkpoint["source_ablation_map"] == API._source_map_payload()
    assert checkpoint["update_count"] == 3 * checkpoint["epoch"]
    assert tuple(checkpoint["models_and_optimizers"]) == API.ARMS
    assert len(checkpoint["consumed_file_order"]) == 300

    exports = sorted((root / "exports" / "epoch-0100").glob("*.pt"))
    assert [path.name.split("-", 1)[1].split(".current", 1)[0] for path in exports] == list(API.ARMS)
    assert len(exports) == 5
    for path in exports:
        state = API._read_torch(path)
        assert state["algorithm"] == API._current_model_algorithm()
    manifest = API.V023FiveArmSourceTrainingRunner._read_json(
        root / "exports" / "epoch-0100.json", label="export manifest"
    )
    assert [entry["arm"] for entry in manifest["exports"]] == list(API.ARMS)
    assert [entry["source_mapping"] for entry in manifest["exports"]] == [
        API.SOURCE_MAP[arm] for arm in API.ARMS
    ]
    # Source-training and one-world diagnostic exports share the same arm
    # namespace, so this cross-layer binding is intentionally one-to-one.
    diagnostic_paths = {
        arm: root / entry["path"]
        for arm, entry in zip(API.ARMS, manifest["exports"], strict=True)
    }
    real_one_world_models = REAL_ONE_WORLD.load_current_five_arm_models(diagnostic_paths)
    assert tuple(real_one_world_models) == REAL_ONE_WORLD.ARMS
    assert all(update_count == 300 for _, _, update_count in real_one_world_models.values())
    assert all(
        isinstance(model, EEAxisLCSRSThreeRoute)
        for model, _, _ in real_one_world_models.values()
    )

    runner.run_to_epoch(101)
    uninterrupted = runner.orchestrator.checkpoint_state()

    resumed_provider = SyntheticProvider()
    resumed = API.V023FiveArmSourceTrainingRunner(_config(), resumed_provider)
    resumed.resume_from_checkpoint(checkpoints[0])
    assert resumed.completed_epochs == 100
    resumed.run_to_epoch(101)
    _assert_tree_identical(uninterrupted, resumed.orchestrator.checkpoint_state())


def test_source_training_control_is_not_the_primary_physical_baseline():
    assert API.ARMS == (
        "ALL_NEUTRAL_CONTROL",
        "FULL",
        "DROP_C1",
        "DROP_C2",
        "DROP_C3",
    )
    assert set(API.SOURCE_MAP["ALL_NEUTRAL_CONTROL"].values()) == {"neutral"}
    assert "BASELINE" not in API.ARMS
    assert REAL_ONE_WORLD.ARMS == API.ARMS

    assert PHYSICAL_EVAL.ARMS == (
        "FULL",
        "BASELINE",
        "DROP_C1",
        "DROP_C2",
        "DROP_C3",
    )
    assert "ALL_NEUTRAL_CONTROL" not in PHYSICAL_EVAL.ARMS
    assert PHYSICAL_EVAL.BASELINE_SOURCE_KIND == (
        "EXPLICIT_AUTHENTICATED_PRE_CATFISH_POLICY"
    )
    assert set(API.ARMS[1:]) == PHYSICAL_EVAL.ROUTE_ARMS


def test_fail_closed_contract_rejects_test_partial_mismatched_provider_source_map_and_noncurrent_checkpoint(tmp_path: Path):
    with pytest.raises(API.V023SourceTrainingRunnerError, match="TEST"):
        API.FrozenSourceTrainingConfig(
            epoch_budget=100,
            orchestrator_config=API.ORCHESTRATOR.V023FiveArmOrchestratorConfig.formal(
                model_config=_model_config(), train_seed=17
            ),
            provider_factory_spec="fixtures:make_provider",
            authority_digests=API.RunAuthorityDigests(DIGEST, "c" * 64, "d" * 64),
            source_split="TEST",
        )

    provider = SyntheticProvider()
    runner = API.V023FiveArmSourceTrainingRunner(_config(), provider)
    root = tmp_path / "validation-run"
    runner.begin_new(root)
    runner.run_to_epoch(100)
    path = root / "checkpoints" / "epoch-0100.runner.pt"
    checkpoint = API._read_torch(path)

    partial = deepcopy(checkpoint)
    partial["update_count"] = 299
    with pytest.raises(API.V023SourceTrainingRunnerError, match="partial|cadence|binding"):
        runner._validate_checkpoint(partial)

    wrong_map = deepcopy(checkpoint)
    wrong_map["source_ablation_map"]["DROP_C3"]["C3"] = "informed"
    with pytest.raises(API.V023SourceTrainingRunnerError, match="source map"):
        runner._validate_checkpoint(wrong_map)

    old = deepcopy(checkpoint)
    old["models_and_optimizers"][API.ARMS[0]]["algorithm"] = "d40-legacy"
    with pytest.raises(API.V023SourceTrainingRunnerError, match="D40|non-current"):
        runner._validate_checkpoint(old)

    mismatched = API.V023FiveArmSourceTrainingRunner(
        _config(), SyntheticProvider(identity="different-provider")
    )
    with pytest.raises(API.V023SourceTrainingRunnerError, match="provider identity"):
        mismatched.resume_from_checkpoint(path)

    with path.open("r+b") as stream:
        stream.seek(32)
        original = stream.read(1)
        stream.seek(32)
        stream.write(bytes([original[0] ^ 0xFF]))
    authenticated = API.V023FiveArmSourceTrainingRunner(_config(), SyntheticProvider())
    with pytest.raises(API.V023SourceTrainingRunnerError, match="digest verification"):
        authenticated.resume_from_checkpoint(path)

    with pytest.raises(API.V023SourceTrainingRunnerError, match="epoch budget"):
        API.V023FiveArmSourceTrainingRunner(
            _config(budget=500),
            SyntheticProvider(planned_epoch_budget=100),
        )


def test_resume_rejects_checkpoint_receipt_update_and_arm_order_drift(tmp_path: Path):
    root = tmp_path / "receipt-validation"
    runner = API.V023FiveArmSourceTrainingRunner(_config(), SyntheticProvider())
    runner.begin_new(root)
    runner.run_to_epoch(100)
    checkpoint_path = root / "checkpoints" / "epoch-0100.runner.pt"
    receipt_path = root / "checkpoint-receipts" / "epoch-0100.json"

    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["update_count"] -= 1
    receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(API.V023SourceTrainingRunnerError, match="checkpoint receipt update count"):
        API.V023FiveArmSourceTrainingRunner(_config(), SyntheticProvider()).resume_from_checkpoint(
            checkpoint_path
        )

    receipt["update_count"] += 1
    receipt["arm_order"] = list(reversed(API.ARMS))
    receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(API.V023SourceTrainingRunnerError, match="checkpoint receipt arm order"):
        API.V023FiveArmSourceTrainingRunner(_config(), SyntheticProvider()).resume_from_checkpoint(
            checkpoint_path
        )


def test_resume_rejects_export_manifest_claim_ceiling_drift(tmp_path: Path):
    root = tmp_path / "manifest-validation"
    runner = API.V023FiveArmSourceTrainingRunner(_config(), SyntheticProvider())
    runner.begin_new(root)
    runner.run_to_epoch(100)
    checkpoint_path = root / "checkpoints" / "epoch-0100.runner.pt"
    receipt_path = root / "checkpoint-receipts" / "epoch-0100.json"
    manifest_path = root / "exports" / "epoch-0100.json"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["claim_ceiling"] = "tampered-source-training-claim"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["export_manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(API.V023SourceTrainingRunnerError, match="export manifest"):
        API.V023FiveArmSourceTrainingRunner(_config(), SyntheticProvider()).resume_from_checkpoint(
            checkpoint_path
        )


def test_exhaustion_propagates_and_cli_requires_explicit_execute_and_inputs(tmp_path: Path):
    exhausted = API.V023FiveArmSourceTrainingRunner(
        _config(), SyntheticProvider(limit=0)
    )
    exhausted.begin_new(tmp_path / "exhausted")
    with pytest.raises(ProviderExhausted, match="fixture exhausted"):
        exhausted.run_to_epoch(1)

    with pytest.raises(SystemExit) as failure:
        API.main(["--output-root", str(tmp_path / "never")])
    assert failure.value.code == 2

    required_but_not_executing = [
        "--output-root", str(tmp_path / "never"),
        "--epochs", "100",
        "--provider-factory", "fixture:factory",
        "--model-config-json", str(tmp_path / "model.json"),
        "--train-seed", "17",
        "--authority-sha256", "a" * 64,
        "--code-sha256", "b" * 64,
        "--input-sha256", "c" * 64,
    ]
    with pytest.raises(SystemExit) as no_execute:
        API.build_parser().parse_args(required_but_not_executing)
    assert no_execute.value.code == 2
    with pytest.raises(SystemExit) as no_input_digest:
        API.build_parser().parse_args(
            [item for item in required_but_not_executing if item not in {"--input-sha256", "c" * 64}]
            + ["--execute"]
        )
    assert no_input_digest.value.code == 2

    imports = []
    syntax = ast.parse((HERE / "v023_five_arm_source_training_runner.py").read_text(encoding="utf-8"))
    for node in ast.walk(syntax):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
        elif isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
    assert all("evaluation" not in item and "trainer_env" not in item for item in imports)
    assert all(not item.startswith("mcrl.env") for item in imports)
