"""W-103 -- live adapter uses branch-local execution only."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np

from mcrl.env.keyed_fading import KeyedFadingField
from mcrl.env.action_contract import NUM_ACTIONS
from mcrl.runtime.ee_axis_v06_c2_k1 import canonical_bytes


ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / ".scratch" / "c3-v04" / "v06_c2_k1_live_adapter.py"
spec = importlib.util.spec_from_file_location("v06_live_adapter", LIVE)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class _Observation:
    step_index = 0
    masks = np.ones((1, NUM_ACTIONS), dtype=bool)


class _Outcome:
    def __init__(self):
        self.observation = _Observation()
        self.link_rate_bps = np.asarray([10.0])
        self.system_power_w = 2.0
        self.resolution = type("Resolution", (), {"served": np.asarray([True], dtype=bool)})()


class _Wrapped:
    def __init__(self, calls):
        self.calls = calls
        self.last_outcome = _Outcome()

    def reset(self, _rng, _mobility):
        return [], [], self.last_outcome.observation

    def step(self, actions, _rng):
        self.calls.append(np.asarray(actions, dtype=np.int64).tolist())
        self.last_outcome = _Outcome()
        return type("Result", (), {"done": False})()


class _Runtime:
    users = 1

    def __init__(self):
        self.calls = []

    def make_environment(self, _archive, *, users):
        assert users == 1
        return _Wrapped(self.calls)

    def bind_field(self, _wrapped, _field):
        return None

    def evaluation_rngs(self, _seed):
        return (np.random.default_rng(1), np.random.default_rng(2))


def test_roll_branch_executes_own_q13_action_at_all_future_offsets(monkeypatch):
    runtime = _Runtime()
    # A real branch-local policy callback would inspect that branch's own
    # state/mask.  The test callback makes the expected executed action clear.
    monkeypatch.setattr(
        mod, "_q13_surfaces",
        lambda *_args, **_kwargs: (np.eye(NUM_ACTIONS)[5][None, :],
                                   np.eye(NUM_ACTIONS)[5][None, :],
                                   np.ones((1, NUM_ACTIONS), dtype=bool)),
    )
    field = KeyedFadingField.from_components("test-v06", "a" * 64, 7)
    rates, power, served, detail = mod._roll_branch(
        runtime, object(), object(), source_seed=7, target_step=0,
        history=[np.asarray([1], dtype=np.int64)], focal_user=0,
        opening_action=3, field=field, interval_s=1.0, kappa_bits=1.0,
    )
    assert runtime.calls == [[3], [5], [5], [5]]
    assert detail["actions"] == [[3], [5], [5], [5]]
    assert detail["q13_actions_k1"] == [5]
    assert rates.shape == (4, 1) and power.shape == (4,)
    assert served.shape == (4, 1) and np.all(served)


def test_roll_branch_uses_noop_for_empty_future_mask(monkeypatch):
    runtime = _Runtime()
    monkeypatch.setattr(
        mod, "_q13_surfaces",
        lambda *_args, **_kwargs: (np.zeros((1, NUM_ACTIONS)),
                                   np.zeros((1, NUM_ACTIONS)),
                                   np.zeros((1, NUM_ACTIONS), dtype=bool)),
    )
    field = KeyedFadingField.from_components("test-v06-noop", "a" * 64, 7)
    _, _, _, detail = mod._roll_branch(
        runtime, object(), object(), source_seed=7, target_step=0,
        history=[np.asarray([1], dtype=np.int64)], focal_user=0,
        opening_action=3, field=field, interval_s=1.0, kappa_bits=1.0,
        end_offset=1,
    )
    assert runtime.calls == [[3], [-1]]
    assert detail["q13_actions_k1"] == [-1]


def test_live_adapter_source_has_no_legacy_compositor_symbols():
    source = LIVE.read_text(encoding="utf-8")
    assert "hold(" not in source.lower()
    assert "tape(" not in source.lower()
    assert "release(" not in source.lower()
    assert "run_v04_c2_phase_b.py" in source


def test_live_lineage_result_is_canonical_finite_json(monkeypatch):
    runtime = _Runtime()
    monkeypatch.setattr(
        mod, "_q13_surfaces",
        lambda *_args, **_kwargs: (np.zeros((1, NUM_ACTIONS)),
                                   np.zeros((1, NUM_ACTIONS)),
                                   np.ones((1, NUM_ACTIONS), dtype=bool)),
    )

    class Network:
        def state_dict(self):
            return {}

    hybrid = type("Hybrid", (), {
        "q_nets": (Network(), Network(), Network()),
        "initialization_seed": 1,
    })()
    field = KeyedFadingField.from_components("test-v06-json", "a" * 64, 7)
    result = mod.run_one_anchor_lineage(
        runtime, object(), hybrid, source_seed=7, target_step=0,
        focal_user=0, history=[np.asarray([0], dtype=np.int64)],
        field=field, interval_s=1.0, kappa_bits=1.0,
        lambda_bits_per_j=1.0,
    )

    assert all(type(row["main_gauge"]["identity_passed"]) is bool
               for row in result["opening_rows"])
    assert canonical_bytes(result).endswith(b"\n")


def test_selected_full_continuation_cannot_mutate_frozen_networks(monkeypatch):
    import pytest
    runtime = _Runtime()
    monkeypatch.setattr(
        mod, "_q13_surfaces",
        lambda *_args, **_kwargs: (np.zeros((1, NUM_ACTIONS)),
                                   np.zeros((1, NUM_ACTIONS)),
                                   np.ones((1, NUM_ACTIONS), dtype=bool)),
    )
    class Value:
        def __init__(self):
            self.array = np.zeros((1, 1), dtype=np.float64)

        def detach(self):
            return self

        def cpu(self):
            return self

        def numpy(self):
            return self.array

    class Network:
        def __init__(self):
            self.weight = Value()

        def state_dict(self):
            return {"weight": self.weight}

    networks = (Network(), Network(), Network())
    hybrid = type("Hybrid", (), {
        "q_nets": networks, "initialization_seed": 1,
    })()
    original_roll = mod._roll_branch
    mutated = {"done": False}

    def mutating_roll(*args, **kwargs):
        result = original_roll(*args, **kwargs)
        if kwargs.get("end_offset") == 3 and not mutated["done"]:
            networks[1].weight.array += 1.0
            mutated["done"] = True
        return result

    monkeypatch.setattr(mod, "_roll_branch", mutating_roll)
    field = KeyedFadingField.from_components("test-v06-mutation", "a" * 64, 7)
    with pytest.raises(mod.LiveAdapterError, match="selected continuation mutated"):
        mod.run_one_anchor_lineage(
            runtime, object(), hybrid, source_seed=7, target_step=0,
            focal_user=0, history=[np.asarray([0], dtype=np.int64)],
            field=field, interval_s=1.0, kappa_bits=1.0,
            lambda_bits_per_j=1.0)


def test_real_v04_source_interface_uses_default_runtime_not_module_frozen_archive():
    import pytest
    pytest.importorskip("torch")
    source = mod._source_loader()
    runtime = source._default_runtime()
    assert not hasattr(source, "_frozen_archive")
    assert callable(runtime.frozen_archive)
    assert callable(runtime.load_trainer)
    assert callable(runtime.make_environment)


def test_authenticated_runtime_uses_frozen_loader_boundaries(monkeypatch, tmp_path):
    class Loader:
        def __init__(self):
            self.calls = []

        def _record_and_prereg(self, *, prereg_path, record):
            self.calls.append("prereg")
            return object(), "p" * 64

        def _authenticate_main_authority(self, path):
            self.calls.append("main-auth")
            return {"checkpoint_file_sha256": "c" * 64}

        def _frozen_archive(self, record, source, target):
            self.calls.append("archive")
            target.mkdir(parents=True)
            return object()

        def _verify_and_load_trainer(self, record, archive, *, run_dir, users):
            self.calls.append("trainer")
            return object(), {"checkpoint_sha256": "c" * 64}

        def _checkpoint_sha256(self, checkpoint):
            return checkpoint["checkpoint_sha256"]

    loader = Loader()
    class Runtime:
        frozen_archive = staticmethod(lambda record, source, target: loader._frozen_archive(record, source, target))
        load_trainer = staticmethod(lambda record, archive, *, run_dir, users: loader._verify_and_load_trainer(record, archive, run_dir=run_dir, users=users))
        make_environment = staticmethod(lambda archive, *, users: None)
        evaluation_rngs = staticmethod(lambda seed: (np.random.default_rng(seed), np.random.default_rng(seed + 1)))
        main_actions = staticmethod(lambda *args: np.zeros(1, dtype=np.int64))
    loader._default_runtime = lambda: Runtime()
    monkeypatch.setattr(mod, "_source_loader", lambda: loader)
    class PhaseB:
        Q13_INIT_SEEDS = (1, 2, 3)

        def _authenticate_q13_gate(self, *_args, **_kwargs):
            return {"source_manifest_sha256": "s" * 64,
                    "selected_hybrid_file_sha256": {"1": "a" * 64, "2": "b" * 64, "3": "c" * 64}}

        def _screen_module(self):
            return self

        def load_gate_selected_hybrid(self, *_args, **_kwargs):
            return type("Hybrid", (), {"q_nets": (type("N", (), {"eval": lambda self: None})(),) * 3,
                                        "selected_q3_rung": 100,
                                        "initialization_seed": _kwargs["initialization_seed"]})()

    monkeypatch.setattr(mod, "_phase_b_loader", lambda: PhaseB())
    with mod.authenticated_runtime(tle_root=tmp_path, prereg_path=tmp_path / "p",
                                   main_dir=tmp_path / "m", gate_dir=tmp_path / "g",
                                   source_dir=tmp_path / "s", v03_root=tmp_path / "v") as runtime:
        assert runtime.prereg_file_sha256 == "p" * 64
        assert runtime.checkpoint_sha256 == "c" * 64
        assert runtime.q13_gate_source_manifest_sha256 == "s" * 64
    assert loader.calls == ["prereg", "main-auth", "archive", "trainer"]
