from __future__ import annotations

from dataclasses import replace
import hashlib
import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace
import subprocess
import sys

import numpy as np
import pytest


REPO = Path(__file__).resolve().parents[1]
RUNTIME_PATH = (
    REPO
    / ".scratch"
    / "multi-catfish-v023-c3-observability"
    / "v023_lcsrs_composition_runtime.py"
)
ADAPTER_PATH = (
    REPO
    / ".scratch"
    / "multi-catfish-v023-c3-observability"
    / "v023_lcsrs_composition_adapter.py"
)


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def runtime_module() -> ModuleType:
    return _load_module("test_w200_runtime", RUNTIME_PATH)


@pytest.fixture(scope="module")
def adapter_module() -> ModuleType:
    return _load_module("test_w200_adapter", ADAPTER_PATH)


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def _readonly(value: object, dtype: np.dtype[object] | type[object]) -> np.ndarray:
    result = np.array(value, dtype=dtype, copy=True)
    result.setflags(write=False)
    return result


class _FakeView:
    def __init__(
        self,
        *,
        digest: str,
        mask: np.ndarray,
        references: np.ndarray,
        forbidden: bool = False,
    ) -> None:
        users = references.size
        self.content_digest = digest
        self.action_context = _readonly(np.zeros((users, 28, 1)), np.float32)
        self.tokens = _readonly(np.zeros((users, 28, 1, 1)), np.float32)
        self.token_mask = _readonly(np.zeros((users, 28, 1)), np.bool_)
        self.action_mask = _readonly(mask, np.bool_)
        self.reference_actions = _readonly(references, np.int64)
        if forbidden:
            self.targets = _readonly(np.ones((users, 28)), np.float32)

    def verify(self) -> str:
        return self.content_digest


class _FakeTopology:
    def __init__(self, *, digest: str, capture: object) -> None:
        self.content_digest = digest
        self.capture = capture

    def verify(self) -> str:
        return self.content_digest


class _FakeCapture:
    def __init__(
        self,
        *,
        request: object,
        q1: np.ndarray,
        q2: np.ndarray,
        mask: np.ndarray,
        references: np.ndarray,
        forbidden_view: bool = False,
    ) -> None:
        snapshot = SimpleNamespace(
            q1=_readonly(q1, np.float32),
            q2=_readonly(q2, np.float32),
            content_digest=request.q12_snapshot_sha256,
            model_digest=request.q12_model_sha256,
            source_state_digest=request.q12_source_state_sha256,
            native_observation_event_digest=request.q12_event_sha256,
        )
        topology_capture = SimpleNamespace(
            world_id=request.world,
            phase=request.phase,
            anchor_id=request.anchor_id,
            q12_snapshot=snapshot,
            action_mask=_readonly(mask, np.bool_),
            reference_actions=_readonly(references, np.int64),
        )
        self.topology = _FakeTopology(
            digest=request.topology_sha256,
            capture=topology_capture,
        )
        self.view = _FakeView(
            digest=request.view_sha256,
            mask=mask,
            references=references,
            forbidden=forbidden_view,
        )
        self.native_observation_provenance = SimpleNamespace(
            field_root_digest=request.field_root_sha256,
            content_digest=request.q12_event_sha256,
        )
        self.state_schema_sha256 = request.state_schema_sha256
        self.state_sha256 = request.state_sha256
        self.content_digest = request.predecision_sha256

    def verify(self) -> str:
        return self.content_digest


def _spec(tmp_path: Path, *, arm: str = "INFORMED") -> SimpleNamespace:
    source = tmp_path / "source-root"
    source.mkdir(exist_ok=True)
    return SimpleNamespace(
        held_out_world=2026121705,
        student_seed=2026135101,
        arm=arm,
        source_directory=source,
        source_manifest=Path("source-manifest.json"),
        preflight_manifest_sha256=_digest("preflight"),
        source_manifest_sha256=_digest("source-manifest"),
        fit_receipt=tmp_path / "fit.json",
        fit_receipt_sha256=_digest("fit-receipt"),
        model_bytes_sha256=_digest("model-bytes"),
        model_sha256=_digest("model-logical"),
        output=tmp_path / "composition.json",
        device="cpu",
        contract_sha256=(
            "1e69a2e7242198adce97e6357e4205a29fe6d1fb06a48dc7e1839a675529811a"
        ),
    )


def _request(
    adapter: ModuleType,
    spec: object,
    *,
    phase: int = 1,
) -> object:
    references = np.asarray([0, 1, 2], dtype=np.int64)
    return adapter.ReplayAnchorRequest(
        world=spec.held_out_world,
        phase=phase,
        anchor_id=f"w{spec.held_out_world}:t{phase}",
        source_directory=spec.source_directory,
        preflight_manifest_sha256=spec.preflight_manifest_sha256,
        source_manifest_sha256=spec.source_manifest_sha256,
        source_index_sha256=_digest("source-index"),
        field_root_sha256=_digest("world-field"),
        predecision_sha256=_digest(f"predecision-{phase}"),
        state_schema_sha256=_digest("state-schema"),
        state_sha256=_digest(f"state-{phase}"),
        q12_snapshot_sha256=_digest(f"snapshot-{phase}"),
        q12_model_sha256=_digest("q12-model"),
        q12_source_state_sha256=_digest(f"state-{phase}"),
        q12_event_sha256=_digest(f"event-{phase}"),
        view_sha256=_digest(f"view-{phase}"),
        topology_sha256=_digest(f"topology-{phase}"),
        reference_actions_sha256=adapter.array_sha256(
            references,
            domain="v023-reference-actions",
        ),
    )


class _FakeBackend:
    def __init__(
        self,
        *,
        runtime: ModuleType,
        adapter: ModuleType,
        spec: object,
        expected_request: object | None = None,
        mutate_name: str | None = None,
        mutate_actions: bool = False,
        field_drift_after_role: bool = False,
        forbidden_view: bool = False,
        target_free: bool = True,
    ) -> None:
        self.runtime = runtime
        self.adapter = adapter
        self.spec = spec
        self.expected_request = expected_request
        self.mutate_name = mutate_name
        self.mutate_actions = mutate_actions
        self.field_drift_after_role = field_drift_after_role
        self.forbidden_view = forbidden_view
        self.target_free = target_free
        self.replay_calls: list[object] = []
        self.draw_calls: list[tuple[int, np.ndarray]] = []

    def replay_anchor(self, request: object) -> object:
        self.replay_calls.append(request)
        authority = request if self.expected_request is None else self.expected_request
        users = 3
        q1 = np.zeros((users, 28), dtype=np.float32)
        q2 = np.zeros_like(q1)
        references = np.asarray([0, 1, 2], dtype=np.int64)
        q1[np.arange(users), references] = np.float32(1.0)
        mask = np.ones_like(q1, dtype=np.bool_)
        capture = _FakeCapture(
            request=authority,
            q1=q1,
            q2=q2,
            mask=mask,
            references=references,
            forbidden_view=self.forbidden_view,
        )
        return self.runtime.ReplayMaterial(
            capture=capture,
            q1=q1,
            q2=q2,
            action_mask=mask,
            reference_actions=references,
            backend_anchor=(authority.world, authority.phase, authority.anchor_id),
            preflight_manifest_sha256=authority.preflight_manifest_sha256,
            source_manifest_sha256=authority.source_manifest_sha256,
            source_index_sha256=authority.source_index_sha256,
            field_root_sha256=authority.field_root_sha256,
            target_free_inference=self.target_free,
        )

    def evaluate_draw(
        self,
        material: object,
        actions: np.ndarray,
        draw_index: int,
    ) -> object:
        if self.mutate_actions and draw_index == 0:
            actions.setflags(write=True)
            actions[0] = (int(actions[0]) + 1) % 28
        self.draw_calls.append((draw_index, np.array(actions, copy=True)))
        call_role = (len(self.draw_calls) - 1) // 32
        field_suffix = "-drift" if self.field_drift_after_role and call_role > 0 else ""
        field = _digest(
            f"field:{self.spec.held_out_world}:{material.backend_anchor[2]}:"
            f"{draw_index}{field_suffix}"
        )
        before = {
            name: (
                self.spec.model_sha256
                if name == "q3"
                else _digest(f"before:{material.backend_anchor[2]}:{draw_index}:{name}")
            )
            for name in self.runtime.NONMUTATION_NAMES
        }
        after = dict(before)
        if self.mutate_name is not None and draw_index == 0:
            after[self.mutate_name] = _digest(f"mutated:{self.mutate_name}")
        beam_count = draw_index % 3
        beam_keys = np.asarray(
            [[1000 + draw_index + offset, 10 + offset] for offset in range(beam_count)],
            dtype=np.int64,
        ).reshape(-1, 2)
        satellites = np.unique(beam_keys[:, 0]) if beam_count else np.zeros((0,), dtype=np.int64)
        return self.runtime.DrawMeasurement(
            draw_index=draw_index,
            action_sha256=self.adapter.action_vector_sha256(actions),
            common_field_sha256=field,
            per_user_bits=np.asarray(
                [draw_index + 0.25, draw_index + 1.25, draw_index + 2.25],
                dtype=np.float64,
            ),
            energy_j=10.0 + draw_index,
            served=np.asarray([True, draw_index % 2 == 0, True], dtype=np.bool_),
            active_beam_keys=beam_keys,
            active_satellites=satellites,
            beam_power_w=np.arange(1, beam_count + 1, dtype=np.float64),
            nonmutation_before=before,
            nonmutation_after=after,
        )


def _runtime_and_backend(
    runtime_module: ModuleType,
    adapter_module: ModuleType,
    spec: object,
    **backend_options: object,
) -> tuple[object, _FakeBackend]:
    backend = _FakeBackend(
        runtime=runtime_module,
        adapter=adapter_module,
        spec=spec,
        **backend_options,
    )
    runtime = runtime_module.build_runtime(
        spec=spec,
        adapter=adapter_module,
        backend_factory=lambda _spec: backend,
    )
    return runtime, backend


def _replay(
    runtime_module: ModuleType,
    adapter_module: ModuleType,
    tmp_path: Path,
    **backend_options: object,
) -> tuple[object, _FakeBackend, object, object, object]:
    spec = _spec(tmp_path)
    request = _request(adapter_module, spec)
    runtime, backend = _runtime_and_backend(
        runtime_module,
        adapter_module,
        spec,
        **backend_options,
    )
    replayed = runtime.replay_anchor(request)
    return runtime, backend, spec, request, replayed


def _physical_request(
    adapter: ModuleType,
    replayed: object,
    *,
    role: str,
    actions: np.ndarray | None = None,
) -> object:
    selected = replayed.reference_actions if actions is None else actions
    return adapter.PhysicalEvaluationRequest(
        handle=replayed.handle,
        world=replayed.world,
        phase=replayed.phase,
        anchor_id=replayed.anchor_id,
        role=role,
        actions=selected,
        draw_index=np.arange(32, dtype=np.int64),
    )


def test_runtime_import_is_inert_and_default_factory_is_lazy(
    runtime_module: ModuleType,
    adapter_module: ModuleType,
    tmp_path: Path,
) -> None:
    script = f"""
import importlib.abc, importlib.util, pathlib, sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'mcrl' or fullname.startswith('mcrl.'):
            raise RuntimeError('simulator import attempted')
        return None
sys.meta_path.insert(0, Block())
path = pathlib.Path({str(RUNTIME_PATH)!r})
spec = importlib.util.spec_from_file_location('isolated_v023_runtime', path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
assert not any(name == 'mcrl' or name.startswith('mcrl.') for name in sys.modules)
assert 'v023_lcsrs_source_adapter' not in {{str(value) for value in sys.modules}}
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr

    runtime = runtime_module.build_runtime(spec=_spec(tmp_path), adapter=adapter_module)
    assert callable(runtime.replay_anchor)
    assert callable(runtime.evaluate_physical)
    assert runtime._backend._source is None
    assert runtime._backend._environment is None


def test_replay_binds_request_and_returns_target_free_immutable_view(
    runtime_module: ModuleType,
    adapter_module: ModuleType,
    tmp_path: Path,
) -> None:
    runtime, backend, _spec_value, request, replayed = _replay(
        runtime_module,
        adapter_module,
        tmp_path,
    )
    assert len(backend.replay_calls) == 1
    assert replayed.world == request.world
    assert replayed.phase == request.phase
    assert replayed.anchor_id == request.anchor_id
    assert replayed.handle.content_digest == request.predecision_sha256
    assert replayed.handle.token.endswith(f":{request.phase}:{request.anchor_id}")
    assert np.array_equal(replayed.reference_actions, [0, 1, 2])
    assert not replayed.q1.flags.writeable
    assert not replayed.q2.flags.writeable
    assert all(
        not hasattr(replayed.view, name)
        for name in runtime_module.FORBIDDEN_VIEW_FIELDS
    )
    target_free_source = __import__("inspect").getsource(
        runtime_module._ProductionBackend._target_free_q12
    )
    assert "_repriced_ops3_context" not in target_free_source
    assert "target_values" not in target_free_source
    assert "teacher" not in target_free_source
    assert runtime._current_material.target_free_inference is True


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("world", 2026121706),
        ("phase", 2),
        ("anchor_id", "w2026121705:t9"),
        ("preflight_manifest_sha256", _digest("bad-preflight")),
        ("source_manifest_sha256", _digest("bad-source-manifest")),
        ("source_index_sha256", _digest("bad-source-index")),
        ("field_root_sha256", _digest("bad-field-root")),
        ("predecision_sha256", _digest("bad-predecision")),
        ("state_schema_sha256", _digest("bad-state-schema")),
        ("state_sha256", _digest("bad-state")),
        ("q12_snapshot_sha256", _digest("bad-snapshot")),
        ("q12_model_sha256", _digest("bad-q12-model")),
        ("q12_source_state_sha256", _digest("bad-source-state")),
        ("q12_event_sha256", _digest("bad-event")),
        ("view_sha256", _digest("bad-view")),
        ("topology_sha256", _digest("bad-topology")),
        ("reference_actions_sha256", _digest("bad-reference")),
    ],
)
def test_replay_rejects_every_tampered_identity_or_digest(
    runtime_module: ModuleType,
    adapter_module: ModuleType,
    tmp_path: Path,
    field: str,
    replacement: object,
) -> None:
    spec = _spec(tmp_path)
    authority = _request(adapter_module, spec)
    request = replace(authority, **{field: replacement})
    runtime, _backend = _runtime_and_backend(
        runtime_module,
        adapter_module,
        spec,
        expected_request=authority,
    )
    with pytest.raises(runtime_module.V023CompositionRuntimeError):
        runtime.replay_anchor(request)
    with pytest.raises(runtime_module.V023CompositionRuntimeError, match="poisoned"):
        runtime.replay_anchor(authority)


def test_replay_rejects_tampered_source_directory(
    runtime_module: ModuleType,
    adapter_module: ModuleType,
    tmp_path: Path,
) -> None:
    spec = _spec(tmp_path)
    authority = _request(adapter_module, spec)
    other = tmp_path / "other-source"
    other.mkdir()
    request = replace(authority, source_directory=other)
    runtime, _backend = _runtime_and_backend(
        runtime_module,
        adapter_module,
        spec,
        expected_request=authority,
    )
    with pytest.raises(runtime_module.V023CompositionRuntimeError, match="source directory"):
        runtime.replay_anchor(request)


def test_full_roster_physical_arrays_field_and_action_identity(
    runtime_module: ModuleType,
    adapter_module: ModuleType,
    tmp_path: Path,
) -> None:
    runtime, backend, spec, _request_value, replayed = _replay(
        runtime_module,
        adapter_module,
        tmp_path,
    )
    request = _physical_request(adapter_module, replayed, role="ZERO_SURFACE_B")
    result = runtime.evaluate_physical(request)
    assert len(backend.draw_calls) == 32
    assert [draw for draw, _actions in backend.draw_calls] == list(range(32))
    assert all(np.array_equal(actions, request.actions) for _draw, actions in backend.draw_calls)
    assert result.per_user_bits.shape == (32, 3)
    assert result.served.shape == (32, 3)
    assert result.total_bits.shape == (32,)
    assert np.array_equal(result.total_bits, np.sum(result.per_user_bits, axis=1))
    assert result.energy_j.shape == (32,)
    assert result.active_beam_keys.shape == (32, 2, 2)
    assert result.beam_power_w.shape == (32, 2)
    assert result.active_satellites.shape == (32, 2)
    assert np.array_equal(result.active_beam_counts, np.arange(32) % 3)
    assert np.all(result.active_beam_keys[result.active_beam_counts == 0] == -1)
    assert result.action_sha256 == adapter_module.action_vector_sha256(request.actions)
    expected_fields = np.asarray(
        [
            _digest(f"field:{spec.held_out_world}:{replayed.anchor_id}:{draw}").encode("ascii")
            for draw in range(32)
        ],
        dtype="S64",
    )
    assert np.array_equal(result.common_field_digest, expected_fields)
    assert result.nonmutation_names == runtime_module.NONMUTATION_NAMES
    assert result.nonmutation_flags.shape == (32, 6)
    assert np.all(result.nonmutation_flags)


def test_production_draw_uses_exact_world_anchor_draw_key_and_one_full_vector(
    runtime_module: ModuleType,
    tmp_path: Path,
) -> None:
    spec = _spec(tmp_path)
    backend = runtime_module._ProductionBackend(spec, SimpleNamespace())
    calls: list[tuple[int, str, int]] = []
    evaluated: list[np.ndarray] = []

    class FieldFactory:
        def _make_draw_field(self, world: int, anchor_id: str, draw_index: int) -> object:
            calls.append((world, anchor_id, draw_index))
            return SimpleNamespace(
                root_digest=_digest(
                    f"{runtime_module.FIELD_COMPONENT}:{world}:{anchor_id}:{draw_index}"
                )
            )

    class StepEnvironment:
        def __init__(self) -> None:
            self._fading_field = SimpleNamespace(root_digest=_digest("world-field"))
            self.driver = SimpleNamespace(
                config=SimpleNamespace(ephemeris=SimpleNamespace(time_step_s=2.0))
            )

        def evaluate_actions(self, actions: np.ndarray, _rng: object) -> object:
            assert not actions.flags.writeable
            evaluated.append(np.array(actions, copy=True))
            return SimpleNamespace()

    def evaluation_record(_evaluation: object, *, actions: np.ndarray, interval_s: float) -> dict[str, object]:
        assert interval_s == 2.0
        assert np.array_equal(actions, [0, 1, 2])
        return {
            "per_user_bits": [1.0, 2.0, 3.0],
            "energy_j": 4.0,
            "served": [True, True, False],
            "active_beam_keys": [[100, 10], [101, 11]],
            "active_satellites": [100, 101],
            "beam_power_w": [5.0, 6.0],
        }

    source = SimpleNamespace(
        _live_digest=lambda _v018, _environment, _rng: _digest("live-state"),
        _rng_digest=lambda _state: _digest("rng-state"),
        _evaluation_record=evaluation_record,
    )
    v018 = SimpleNamespace(
        _V015=SimpleNamespace(
            _q_parameter_sha256=lambda network: _digest(f"network:{network}")
        )
    )
    step_env = StepEnvironment()
    backend._source = source
    backend._source_runtime = FieldFactory()
    backend._v018 = v018
    backend._q1 = "q1"
    backend._q2 = "q2"
    backend._q3_sha256 = spec.model_sha256
    backend._environment = SimpleNamespace()
    backend._step_env = step_env
    backend._env_rng = np.random.default_rng(123)
    backend._last_phase = 1
    material = SimpleNamespace(
        backend_anchor=(spec.held_out_world, 1, f"w{spec.held_out_world}:t1")
    )
    result = backend.evaluate_draw(
        material,
        _readonly([0, 1, 2], np.int64),
        7,
    )
    assert calls == [(spec.held_out_world, f"w{spec.held_out_world}:t1", 7)]
    assert len(evaluated) == 1
    assert np.array_equal(evaluated[0], [0, 1, 2])
    assert result.action_sha256 == runtime_module._action_sha256([0, 1, 2])
    assert result.common_field_sha256 == _digest(
        f"{runtime_module.FIELD_COMPONENT}:{spec.held_out_world}:"
        f"w{spec.held_out_world}:t1:7"
    )
    assert result.nonmutation_before == result.nonmutation_after


def test_one_pass_role_and_phase_state_machine(
    runtime_module: ModuleType,
    adapter_module: ModuleType,
    tmp_path: Path,
) -> None:
    spec = _spec(tmp_path)
    first = _request(adapter_module, spec, phase=1)
    runtime, backend = _runtime_and_backend(runtime_module, adapter_module, spec)
    replayed = runtime.replay_anchor(first)
    with pytest.raises(runtime_module.V023CompositionRuntimeError, match="before all physical roles"):
        runtime.replay_anchor(_request(adapter_module, spec, phase=2))
    assert len(backend.replay_calls) == 1

    runtime, backend = _runtime_and_backend(runtime_module, adapter_module, spec)
    replayed = runtime.replay_anchor(first)
    for role in ("ZERO_SURFACE_B", "INFORMED", "TEACHER_ORACLE"):
        runtime.evaluate_physical(
            _physical_request(adapter_module, replayed, role=role)
        )
    assert len(backend.draw_calls) == 96
    second = runtime.replay_anchor(_request(adapter_module, spec, phase=2))
    assert second.phase == 2
    assert len(backend.replay_calls) == 2

    runtime, _backend = _runtime_and_backend(runtime_module, adapter_module, spec)
    replayed = runtime.replay_anchor(first)
    with pytest.raises(runtime_module.V023CompositionRuntimeError, match="role order"):
        runtime.evaluate_physical(
            _physical_request(adapter_module, replayed, role="INFORMED")
        )


@pytest.mark.parametrize("name", ("environment", "rng", "q1", "q2", "q3", "matched_field"))
def test_every_named_mutation_guard_fails_closed(
    runtime_module: ModuleType,
    adapter_module: ModuleType,
    tmp_path: Path,
    name: str,
) -> None:
    runtime, backend, _spec_value, _request_value, replayed = _replay(
        runtime_module,
        adapter_module,
        tmp_path,
        mutate_name=name,
    )
    with pytest.raises(runtime_module.V023CompositionRuntimeError, match="mutated"):
        runtime.evaluate_physical(
            _physical_request(adapter_module, replayed, role="ZERO_SURFACE_B")
        )
    assert len(backend.draw_calls) == 1


def test_action_edit_and_cross_role_field_drift_are_rejected(
    runtime_module: ModuleType,
    adapter_module: ModuleType,
    tmp_path: Path,
) -> None:
    runtime, backend, _spec_value, _request_value, replayed = _replay(
        runtime_module,
        adapter_module,
        tmp_path,
        mutate_actions=True,
    )
    with pytest.raises(runtime_module.V023CompositionRuntimeError, match="edited"):
        runtime.evaluate_physical(
            _physical_request(adapter_module, replayed, role="ZERO_SURFACE_B")
        )
    assert len(backend.draw_calls) == 1

    other_root = tmp_path / "field-drift"
    other_root.mkdir()
    runtime, backend, _spec_value, _request_value, replayed = _replay(
        runtime_module,
        adapter_module,
        other_root,
        field_drift_after_role=True,
    )
    runtime.evaluate_physical(
        _physical_request(adapter_module, replayed, role="ZERO_SURFACE_B")
    )
    with pytest.raises(runtime_module.V023CompositionRuntimeError, match="common draw field"):
        runtime.evaluate_physical(
            _physical_request(adapter_module, replayed, role="INFORMED")
        )
    assert len(backend.draw_calls) == 64


def test_target_or_non_target_free_replay_is_rejected(
    runtime_module: ModuleType,
    adapter_module: ModuleType,
    tmp_path: Path,
) -> None:
    spec = _spec(tmp_path)
    request = _request(adapter_module, spec)
    runtime, _backend = _runtime_and_backend(
        runtime_module,
        adapter_module,
        spec,
        forbidden_view=True,
    )
    with pytest.raises(runtime_module.V023CompositionRuntimeError, match="teacher/target/outcome"):
        runtime.replay_anchor(request)

    other_root = tmp_path / "not-target-free"
    other_root.mkdir()
    spec = _spec(other_root)
    request = _request(adapter_module, spec)
    runtime, _backend = _runtime_and_backend(
        runtime_module,
        adapter_module,
        spec,
        target_free=False,
    )
    with pytest.raises(runtime_module.V023CompositionRuntimeError, match="target-free"):
        runtime.replay_anchor(request)


def test_factory_derives_optional_hashes_but_rejects_tampered_values(
    runtime_module: ModuleType,
    adapter_module: ModuleType,
    tmp_path: Path,
) -> None:
    spec = _spec(tmp_path)
    for name in ("model_sha256", "model_bytes_sha256", "contract_sha256"):
        derived = SimpleNamespace(**vars(spec))
        setattr(derived, name, None)
        runtime = runtime_module.build_runtime(
            spec=derived,
            adapter=adapter_module,
            backend_factory=lambda _spec: SimpleNamespace(
                replay_anchor=lambda _request: None,
                evaluate_draw=lambda _material, _actions, _draw: None,
            ),
        )
        assert callable(runtime.replay_anchor)

    for name, value in (
        ("model_sha256", "not-a-digest"),
        ("model_bytes_sha256", "not-a-digest"),
        ("contract_sha256", _digest("wrong-contract")),
    ):
        broken = SimpleNamespace(**vars(spec))
        setattr(broken, name, value)
        with pytest.raises(runtime_module.V023CompositionRuntimeError):
            runtime_module.build_runtime(
                spec=broken,
                adapter=adapter_module,
                backend_factory=lambda _spec: SimpleNamespace(
                    replay_anchor=lambda _request: None,
                    evaluate_draw=lambda _material, _actions, _draw: None,
                ),
            )


def test_production_backend_derives_missing_model_hashes_from_fit_authenticator(
    runtime_module: ModuleType,
    tmp_path: Path,
) -> None:
    spec = _spec(tmp_path)
    spec.model_bytes_sha256 = None
    spec.model_sha256 = None
    request = SimpleNamespace(source_index_sha256=_digest("source-index"))
    fitted = SimpleNamespace(
        held_out_world=spec.held_out_world,
        student_seed=spec.student_seed,
        arm=spec.arm,
        preflight_manifest_sha256=spec.preflight_manifest_sha256,
        source_manifest_sha256=spec.source_manifest_sha256,
        fit_receipt_sha256=spec.fit_receipt_sha256,
        source_index_sha256=request.source_index_sha256,
        update_count=2000,
        model_bytes_sha256=_digest("derived-model-bytes"),
        model_sha256=_digest("derived-model-logical"),
    )
    calls: list[tuple[object, str]] = []

    def authenticate(adapter_spec: object, *, device: str) -> object:
        calls.append((adapter_spec, device))
        return fitted

    fake_adapter = SimpleNamespace(
        CompositionShardSpec=lambda **values: SimpleNamespace(**values),
        authenticate_fit_artifact=authenticate,
    )
    backend = runtime_module._ProductionBackend(spec, fake_adapter)
    backend._authenticate_fit_identity(request)
    assert len(calls) == 1
    assert calls[0][1] == "cpu"
    assert backend._model_bytes_sha256 == fitted.model_bytes_sha256
    assert backend._q3_sha256 == fitted.model_sha256
