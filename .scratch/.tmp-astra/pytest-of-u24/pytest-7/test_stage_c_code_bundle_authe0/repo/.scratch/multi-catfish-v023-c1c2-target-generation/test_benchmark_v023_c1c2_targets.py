from __future__ import annotations

from dataclasses import dataclass
import ast
from pathlib import Path
from types import SimpleNamespace

import pytest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def _load_benchmark():
    import importlib.util
    import sys

    path = HERE / "benchmark_v023_c1c2_targets.py"
    spec = importlib.util.spec_from_file_location(
        "mcrl_v023_c1c2_target_benchmark_test_module", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


benchmark = _load_benchmark()


@dataclass(frozen=True)
class _Row:
    anchor_sha256: str
    step_index: int
    focal_user: int
    candidate_action: int
    candidate_physical_key: tuple[int, int]


def _sealed(rows: list[_Row]):
    anchors = {
        (row.anchor_sha256, row.focal_user): SimpleNamespace(
            world_id=2026121705,
            source_seed=2026121705,
            anchor=SimpleNamespace(step_index=row.step_index),
        )
        for row in rows
    }
    return SimpleNamespace(c2_anchor_by_key=anchors)


def test_choose_cohort_is_common_world_step_and_one_row_per_anchor() -> None:
    informed_rows = [
        _Row("a" * 64, 1, 0, 1, (10, 1)),
        _Row("b" * 64, 1, 1, 2, (11, 1)),
        _Row("c" * 64, 3, 0, 3, (12, 1)),
    ]
    neutral_rows = [
        _Row("a" * 64, 1, 0, 4, (20, 1)),
        _Row("b" * 64, 1, 1, 5, (21, 1)),
        _Row("d" * 64, 1, 2, 6, (22, 1)),
    ]
    cohort = benchmark.choose_cohort(
        _sealed(informed_rows + neutral_rows),
        {
            "informed": SimpleNamespace(opportunities=tuple(informed_rows)),
            "neutral": SimpleNamespace(opportunities=tuple(neutral_rows)),
        },
        modes=("informed", "neutral"),
        anchor_count=2,
        max_step=2,
    )

    assert (cohort.world, cohort.step) == (2026121705, 1)
    assert [row.anchor_sha256 for row in cohort.rows("informed")] == [
        "a" * 64,
        "b" * 64,
    ]
    assert [row.anchor_sha256 for row in cohort.rows("neutral")] == [
        "a" * 64,
        "b" * 64,
    ]


def test_choose_cohort_rejects_missing_bounded_common_cohort() -> None:
    rows = [_Row("a" * 64, 4, 0, 1, (10, 1))]
    with pytest.raises(benchmark.BenchmarkError, match="no common C2 cohort"):
        benchmark.choose_cohort(
            _sealed(rows),
            {
                "informed": SimpleNamespace(opportunities=tuple(rows)),
                "neutral": SimpleNamespace(opportunities=tuple(rows)),
            },
            modes=("informed", "neutral"),
            anchor_count=1,
            max_step=2,
        )


def test_full_step_cohort_keeps_the_complete_smallest_schedule() -> None:
    rows = [
        _Row("a" * 64, 1, 0, 1, (10, 1)),
        _Row("b" * 64, 1, 1, 2, (11, 1)),
        _Row("c" * 64, 2, 2, 3, (12, 1)),
    ]
    cohort = benchmark.choose_full_step_cohort(
        _sealed(rows),
        {"informed": SimpleNamespace(opportunities=tuple(rows))},
        modes=("informed",),
        max_step=2,
    )
    assert (cohort.world, cohort.step) == (2026121705, 2)
    assert cohort.rows("informed") == (rows[2],)


def test_choose_cohort_rejects_world_source_seed_mismatch() -> None:
    row = _Row("a" * 64, 1, 0, 1, (10, 1))
    sealed = _sealed([row])
    sealed.c2_anchor_by_key[(row.anchor_sha256, row.focal_user)].world_id = 99
    with pytest.raises(benchmark.BenchmarkError, match="world/source seed"):
        benchmark.choose_cohort(
            sealed,
            {"informed": SimpleNamespace(opportunities=(row,))},
            modes=("informed",),
            anchor_count=1,
            max_step=2,
        )


def test_parser_has_no_output_argument_and_fixed_100_user_default() -> None:
    parser = benchmark._parser()
    actions = {action.dest: action for action in parser._actions}
    assert "output" not in actions
    assert actions["users"].default == 100
    assert actions["anchor_count"].choices == (1, 2, 4)
    assert actions["full_step_cohort"].default is False


def test_benchmark_source_has_no_write_or_full_generation_calls() -> None:
    source = (HERE / "benchmark_v023_c1c2_targets.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "generate_targets" not in called_names
    assert "_write_outputs" not in called_names
    assert not any(
        marker in source
        for marker in ("write_text(", "write_bytes(", "open(\"wb\")", "os.open(")
    )


def test_timeout_contract_is_strictly_below_ten_minutes() -> None:
    with pytest.raises(benchmark.BenchmarkError, match="strictly below"):
        with benchmark._deadline("unit", 600.0):
            pass
