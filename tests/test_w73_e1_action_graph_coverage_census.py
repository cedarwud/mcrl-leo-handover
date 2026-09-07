from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


RUNNER = (
    Path(__file__).resolve().parents[1]
    / ".scratch/ee-axis-redesign/census_v03_e1_action_graph_coverage.py"
)
SPEC = importlib.util.spec_from_file_location("e1_action_graph_census", RUNNER)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def _row(reference: int, candidate: int, *, seed: int = 1):
    return SimpleNamespace(
        reference_action=reference,
        candidate_action=candidate,
        source_seed=seed,
        cluster_key=("C1", seed, f"a{seed}", 0),
        inference_cluster_key=("C1", seed, f"a{seed}"),
    )


def test_graph_census_reports_cross_component_validation_contrast() -> None:
    report = runner._route_graph_report(
        [_row(0, 1), _row(2, 3)],
        [_row(0, 1, seed=2), _row(0, 2, seed=2)],
        action_dim=5,
    )
    assert report["connected_components_with_edges"] == [[0, 1], [2, 3]]
    assert report["isolated_actions"] == [4]
    assert report["unsupported_validation_rows"] == 1
    assert report["unsupported_validation_action_pairs"] == [
        {"reference_action": 0, "candidate_action": 2}
    ]
    assert report["all_validation_contrasts_identified"] is False


def test_graph_census_passes_when_train_graph_connects_validation_pairs() -> None:
    report = runner._route_graph_report(
        [_row(0, 1), _row(1, 2)],
        [_row(0, 2, seed=2)],
        action_dim=3,
    )
    assert report["unsupported_validation_rows"] == 0
    assert report["all_validation_contrasts_identified"] is True
