from __future__ import annotations

from probe.run_v025_synthetic_map import (
    LABEL,
    _bind_provider,
    _load_stage2,
    _provider,
    _signed,
    grid_cells,
    read_once,
    write_once,
)
from mcrl.physics_v025.tapes import PROBE_WORLD_DOMAINS, build_world_tape


def test_synthetic_map_uses_complete_stage2_cartesian_catalogue() -> None:
    runner = _load_stage2()
    cell = next(row for row in grid_cells() if row["id"] == "LOW-DENSE-WEAK")
    tape = build_world_tape(
        domain=PROBE_WORLD_DOMAINS[0],
        provider=_provider(cell, 1),
        steps=1,
        start_time_s=435.0,
    )
    base = runner._base_configuration(tape, 0, "nearest-eligible")
    rows = runner._catalogue(tape, 0, base)
    assert sum(row.changed_users == 0 for row in rows) == 1
    assert sum(row.changed_users == 1 for row in rows) == 3 * (4 - 1)
    assert len(rows) == 4**3


def test_exchangeability_cache_matches_uncached_full_physics() -> None:
    runner = _load_stage2()
    cell = next(row for row in grid_cells() if row["id"] == "MID-DENSE-STRONG")
    _bind_provider(runner, cell, 1)
    tape = build_world_tape(
        domain=PROBE_WORLD_DOMAINS[0],
        provider=_provider(cell, 1),
        steps=1,
        start_time_s=435.0,
    )
    left = runner.Configuration(
        "left",
        ((0, (90001, 0)), (1, (90001, 0)), (2, (90002, 0)), (3, (90002, 0))),
        2,
        "test",
    )
    right = runner.Configuration(
        "right",
        ((0, (90001, 0)), (1, (90002, 0)), (2, (90001, 0)), (3, (90002, 0))),
        2,
        "test",
    )
    cached = runner.StepEvaluator(tape, runner._setting("a-r0"), 0)
    cached.evaluate(left)
    cached_right = cached.evaluate(right)
    assert cached.physical_evaluations == 48

    equivalence_key = runner.EVALUATION_EQUIVALENCE_KEY
    runner.EVALUATION_EQUIVALENCE_KEY = None
    try:
        uncached_right = runner.StepEvaluator(tape, runner._setting("a-r0"), 0).evaluate(right)
    finally:
        runner.EVALUATION_EQUIVALENCE_KEY = equivalence_key
    assert cached_right.score == uncached_right.score
    assert cached_right.energy_components == uncached_right.energy_components


def test_synthetic_receipts_are_labelled_write_once_and_self_verifying(tmp_path) -> None:
    payload = _signed(
        {
            "schema": "test",
            "status": "PASS",
            "experiment_label": LABEL,
        }
    )
    path = tmp_path / "receipt.json"
    write_once(path, payload)
    assert read_once(path) == payload
    assert path.stat().st_mode & 0o777 == 0o444
