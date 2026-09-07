"""W-58 -- fresh-seed E1 split and sibling-group contracts."""

from __future__ import annotations

from dataclasses import replace

import pytest

from mcrl.runtime.ee_axis_e1_split import (
    E1PairIndexRow,
    E1SplitContractError,
    verify_e1_partition,
    verify_e1_seed_split,
    verify_full_sibling_groups,
)


SEED_SPLIT = {
    101: "train",
    102: "train",
    103: "train",
    104: "validation",
    105: "test",
    106: "test",
}


def _digest(index: int) -> str:
    return f"{index:064x}"


def _rows() -> list[E1PairIndexRow]:
    rows: list[E1PairIndexRow] = []
    for route in ("C1", "C2", "C3"):
        for index, seed in enumerate(SEED_SPLIT, start=1):
            if route == "C2":
                rows.append(
                    E1PairIndexRow(
                        route=route,
                        source_seed=seed,
                        anchor_sha256=_digest(index),
                        inference_anchor_sha256=_digest(index),
                        focal_user=0,
                        reference_action=0,
                        candidate_action=1,
                        action_mask=(True, True, True),
                    )
                )
            else:
                for candidate in (1, 2):
                    rows.append(
                        E1PairIndexRow(
                            route=route,
                            source_seed=seed,
                            anchor_sha256=_digest(index),
                            inference_anchor_sha256=_digest(index),
                            focal_user=0,
                            reference_action=0,
                            candidate_action=candidate,
                            action_mask=(True, True, True),
                        )
                    )
    return rows


def test_seed_split_requires_fresh_six_seed_three_one_two_partition() -> None:
    assert verify_e1_seed_split(SEED_SPLIT, burned_seeds=[1, 2]) == SEED_SPLIT
    with pytest.raises(E1SplitContractError, match="overlap burned"):
        verify_e1_seed_split(SEED_SPLIT, burned_seeds=[105])
    with pytest.raises(E1SplitContractError, match="3/1/2"):
        verify_e1_seed_split({**SEED_SPLIT, 106: "validation"}, burned_seeds=[])


def test_full_sibling_group_requires_every_legal_nonreference_action_once() -> None:
    rows = [row for row in _rows() if row.route == "C1"]
    verify_full_sibling_groups(rows, route="C1")
    with pytest.raises(E1SplitContractError, match="full legal-alternative"):
        verify_full_sibling_groups(rows[:-1], route="C1")
    with pytest.raises(E1SplitContractError, match="only to C1/C3"):
        verify_full_sibling_groups(rows, route="C2")


def test_partition_counts_clusters_by_route_and_seed_level_split() -> None:
    receipt = verify_e1_partition(
        _rows(),
        seed_split=SEED_SPLIT,
        burned_seeds=[],
        minimum_clusters={"train": 3, "validation": 1, "test": 2},
        minimum_inference_anchors={
            route: {"train": 3, "validation": 1, "test": 2}
            for route in ("C1", "C2", "C3")
        },
    )
    assert [item.route for item in receipt.coverage] == ["C1", "C2", "C3"]
    assert receipt.coverage[0].train_clusters == 3
    assert receipt.coverage[0].train_inference_anchors == 3
    assert receipt.coverage[0].train_rows == 6
    assert receipt.coverage[1].test_rows == 2


def test_partition_distinguishes_intervention_clusters_from_inference_anchors() -> None:
    with pytest.raises(E1SplitContractError, match="inference-anchor"):
        verify_e1_partition(
            _rows(),
            seed_split=SEED_SPLIT,
            burned_seeds=[],
            minimum_clusters={"train": 3, "validation": 1, "test": 2},
            minimum_inference_anchors={
                "C1": {"train": 3, "validation": 2, "test": 2},
                "C2": {"train": 3, "validation": 1, "test": 2},
                "C3": {"train": 3, "validation": 1, "test": 2},
            },
        )


def test_partition_fails_closed_when_one_route_lacks_independent_clusters() -> None:
    rows = [
        row
        for row in _rows()
        if not (row.route == "C2" and row.source_seed == 106)
    ]
    with pytest.raises(E1SplitContractError, match="C2 has insufficient"):
        verify_e1_partition(
            rows,
            seed_split=SEED_SPLIT,
            burned_seeds=[],
            minimum_clusters={"train": 3, "validation": 1, "test": 2},
        )


def test_partition_rejects_same_anchor_digest_across_seed_splits() -> None:
    rows = _rows()
    validation_index = next(
        index
        for index, row in enumerate(rows)
        if row.route == "C2" and row.source_seed == 104
    )
    rows[validation_index] = replace(
        rows[validation_index],
        anchor_sha256=_digest(1),
        inference_anchor_sha256=_digest(1),
    )
    with pytest.raises(E1SplitContractError, match="appears across"):
        verify_e1_partition(
            rows,
            seed_split=SEED_SPLIT,
            burned_seeds=[],
            minimum_clusters={"train": 3, "validation": 1, "test": 2},
        )


def test_partition_rejects_physical_anchor_overlap_even_if_inference_id_differs() -> None:
    rows = _rows()
    validation_index = next(
        index
        for index, row in enumerate(rows)
        if row.route == "C2" and row.source_seed == 104
    )
    rows[validation_index] = replace(
        rows[validation_index],
        anchor_sha256=_digest(1),
    )
    with pytest.raises(E1SplitContractError, match="appears across"):
        verify_e1_partition(
            rows,
            seed_split=SEED_SPLIT,
            burned_seeds=[],
            minimum_clusters={"train": 3, "validation": 1, "test": 2},
        )


def test_opening_route_cannot_forge_inference_anchor_identity() -> None:
    row = next(row for row in _rows() if row.route == "C1")
    forged = replace(row, inference_anchor_sha256=_digest(999))
    with pytest.raises(E1SplitContractError, match="opening anchor"):
        forged.verify()
