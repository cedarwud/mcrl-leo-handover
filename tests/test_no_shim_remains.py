"""The tree imports for real — no test-only stand-ins anywhere.

W-01's port left five module-level imports unsatisfied, so until W-12 every
test ran against ``sys.modules`` stand-ins.  That is a genuinely dangerous
state: one of them, the permissive ``trainer_config_validation`` no-op, was
silently **masking** the real validator once it was written, and the whole
suite still passed.

This is the gate that keeps the shim from coming back.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
SRC = TESTS.parent / "src" / "mcrl"

PREVIOUSLY_SHIMMED = (
    "mcrl.env.step_types",
    "mcrl.runtime.trainer_config_validation",
    "mcrl.artifacts",
    "mcrl.runtime.energy_efficiency",
)


def test_the_shim_module_is_gone():
    assert not (TESTS / "_port_shim.py").exists()
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("_port_shim")


def test_no_loaded_mcrl_module_is_a_stand_in():
    """The stand-ins marked themselves; nothing may still carry the mark."""
    for name, module in list(sys.modules.items()):
        if name.startswith("mcrl"):
            assert not getattr(module, "__mcrl_test_shim__", False), name


def test_every_previously_shimmed_module_is_a_real_file():
    for name in PREVIOUSLY_SHIMMED:
        module = importlib.import_module(name)
        assert module.__file__ is not None, name
        assert Path(module.__file__).is_file(), name
        assert str(SRC) in module.__file__, name


def test_the_trainer_imports_without_any_help():
    """The import that W-01 could not satisfy at all."""
    module = importlib.import_module("mcrl.algorithms.modqn")
    assert Path(module.__file__).is_file()
    assert module.MODQNTrainer is not None


def test_env_step_is_the_new_environment_not_a_resurrected_port():
    """``env.step`` exists again — as W-17's own file, not the old one.

    It was absent for a reason: W-01 ported a trainer that imported an
    environment nobody had written, and the shim that filled the hole made
    every test run against a stand-in.  The invariant was "no stub called
    ``env.step``", and while nothing had been written it was simplest to
    check that the path did not exist at all.

    W-17 wrote the real thing, so the check moves to what it always meant:
    the module is a real file, it is not a shim, it exports the environment,
    and it carries none of the ported surface the rulings deleted.
    """
    module = importlib.import_module("mcrl.env.step")
    assert Path(module.__file__).is_file()
    assert str(SRC) in module.__file__
    assert not getattr(module, "__mcrl_test_shim__", False)
    assert module.StepEnvironment is not None
    assert module.PhysicsConfig is not None

    source = (SRC / "env" / "step.py").read_text()
    for deleted in (
        "PowerSurfaceConfig",
        "hobs_power_surface_mode",
        "power_codebook",
        "total_power_budget_w",
    ):
        assert deleted not in source, (
            f"env/step.py mentions {deleted!r}: ruling C-2 deleted that "
            "surface and P-16 removed its config"
        )


def test_the_deleted_power_surface_has_no_home_left():
    """PATCH P-16: ``PowerSurfaceConfig`` is gone from the whole package."""
    step_types = importlib.import_module("mcrl.env.step_types")
    for name in (
        "PowerSurfaceConfig",
        "HOBS_POWER_SURFACE_STATIC_CONFIG",
        "HOBS_POWER_SURFACE_ACTIVE_LOAD_CONCAVE",
        "HOBS_POWER_SURFACE_ANGLE_AWARE_THESIS",
        "POWER_CODEBOOK_PROFILES",
    ):
        assert not hasattr(step_types, name), name


def test_conftest_carries_no_installer():
    """Checked on the parsed tree: the file is a docstring and nothing else.

    A text search would trip on the docstring, which names the modules that
    used to be installed.
    """
    import ast

    tree = ast.parse((TESTS / "conftest.py").read_text())
    executable = [
        node
        for node in tree.body
        if not (
            isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
        )
    ]
    assert executable == [], "conftest must contain no statements at all"
