from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def _load(name: str, path: Path):
    spec = spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


benchmark = _load(
    "mcrl_v023_c1_target_benchmark_test_module",
    HERE / "benchmark_v023_c1_targets.py",
)
materializer_test = _load(
    "mcrl_v023_c1_target_benchmark_fixture_module",
    REPO
    / ".scratch"
    / "multi-catfish-v023-c1c2-neutral-materialization"
    / "test_materialize_v023_c1c2.py",
)


def _sealed(tmp_path: Path):
    materializer = materializer_test.module
    payload = materializer_test._payload()
    capture = tmp_path / "capture.json"
    capture.write_bytes(materializer.canonical_bytes(payload) + b"\n")
    bundle = materializer.materialize_capture(payload)
    materialization = tmp_path / "materialized"
    materializer.write_materialization(bundle, materialization)
    return benchmark.GENERATOR.load_sealed_inputs(capture, materialization)


def test_smallest_c1_unit_remains_a_valid_complete_selection(tmp_path: Path) -> None:
    sealed = _sealed(tmp_path)
    for mode in ("informed", "neutral"):
        selection = sealed.c1_routes[mode]
        world, step, rows = benchmark.choose_smallest_complete_unit(sealed, selection)
        subset = benchmark.subset_complete_unit(selection, rows)

        assert world in benchmark.GENERATOR._group_c1_by_world(sealed, selection)
        assert step == rows[0].step_index
        assert subset.budget == len(rows) > 0
        assert {row.anchor_sha256 for row in rows} == set(subset.selected_anchor_sha256s)
        assert {
            (row.anchor_sha256, row.focal_user) for row in rows
        } == set(subset.selected_focal_users)


def test_c1_benchmark_cli_has_no_output_or_test_option() -> None:
    destinations = {action.dest for action in benchmark._parser()._actions}
    assert "output" not in destinations
    assert "test" not in destinations
