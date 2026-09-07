from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import run_oracle_gate as gate  # noqa: E402
from mcrl.env.action_contract import (  # noqa: E402
    NUM_ACTIONS,
    Association,
    SlotTable,
    UNSERVED,
)


def _table(rows: dict[int, tuple[int, int]]) -> SlotTable:
    norads = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    cells = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    mask = np.zeros(NUM_ACTIONS, dtype=bool)
    for action, (norad, cell) in rows.items():
        norads[action] = norad
        cells[action] = cell
        mask[action] = True
    return SlotTable(norad_ids=norads, cell_ids=cells, mask=mask)


def _choices(
    rows: dict[int, tuple[int, int]],
    *,
    loads: dict[int, float] | None = None,
    sinr: dict[int, float] | None = None,
) -> list[gate.CandidateChoice]:
    table = _table(rows)
    prior = np.zeros(NUM_ACTIONS, dtype=np.float64)
    candidate_sinr = np.ones(NUM_ACTIONS, dtype=np.float64)
    q1 = np.arange(NUM_ACTIONS, dtype=np.float64)
    for action, value in (loads or {}).items():
        prior[action] = value
    for action, value in (sinr or {}).items():
        candidate_sinr[action] = value
    return gate._physical_candidates(
        table,
        prior_demand=prior,
        candidate_sinr=candidate_sinr,
        q1=q1,
    )


def test_q1_projection_respects_masks_ties_and_noop() -> None:
    q1 = np.zeros((2, NUM_ACTIONS), dtype=np.float64)
    q1[0, 0] = 999.0
    q1[0, 1] = 5.0
    q1[0, 2] = 5.0
    masks = np.zeros_like(q1, dtype=bool)
    masks[0, [1, 2]] = True

    actions = gate.masked_greedy_actions(q1, masks)

    assert actions.tolist() == [1, -1]


def test_r2_exact_stay_and_same_satellite_are_separate() -> None:
    candidates = _choices(
        {
            0: (10, 1),
            1: (10, 2),
            2: (10, 3),
            3: (20, 1),
        },
        sinr={0: 2.0, 1: 4.0, 2: 8.0, 3: 16.0},
    )
    previous = Association(10, 1)
    kwargs = {
        "previous": previous,
        "baseline_key": (20, 1),
        "candidates": candidates,
        "baseline_intent": {(20, 1)},
        "other_user_intent": set(),
    }

    exact = gate.canonical_proposal("r2_exact_stay", **kwargs)
    same_satellite = gate.canonical_proposal("r2_same_satellite", **kwargs)

    assert exact.choice is not None and exact.choice.key == (10, 1)
    assert same_satellite.choice is not None
    assert same_satellite.choice.key == (10, 3)
    assert gate.canonical_proposal(
        "r2_exact_stay", **(kwargs | {"previous": None})
    ).reason == "episode_start"
    assert gate.canonical_proposal(
        "r2_exact_stay", **(kwargs | {"previous": UNSERVED})
    ).reason == "previously_unserved"


def test_r3_uses_reference_intent_sets_and_deterministic_tie_break() -> None:
    candidates = _choices(
        {
            0: (20, 1),
            1: (30, 1),
            2: (40, 1),
            3: (50, 1),
        },
        loads={1: 2.0, 2: 1.0, 3: 1.0},
        sinr={1: 4.0, 2: 3.0, 3: 9.0},
    )
    kwargs = {
        "previous": Association(20, 1),
        "baseline_key": (20, 1),
        "candidates": candidates,
        "baseline_intent": {(20, 1), (30, 1)},
        "other_user_intent": {(30, 1)},
    }

    reuse = gate.canonical_proposal("r3_reuse_intended", **kwargs)
    opened = gate.canonical_proposal("r3_open_new_intent", **kwargs)

    assert reuse.choice is not None and reuse.choice.key == (30, 1)
    assert opened.choice is not None and opened.choice.key == (50, 1)


def test_physical_candidates_deduplicate_relative_actions() -> None:
    candidates = _choices({0: (10, 1), 7: (10, 1), 8: (20, 1)})

    assert [(row.action, row.key) for row in candidates] == [
        (0, (10, 1)),
        (8, (20, 1)),
    ]


def test_fractional_ee_certificate_identity_and_sign() -> None:
    positive = gate.ee_certificate(
        baseline_throughput_bps=1000.0,
        baseline_power_w=10.0,
        alternative_throughput_bps=1150.0,
        alternative_power_w=11.0,
    )
    negative = gate.ee_certificate(
        baseline_throughput_bps=1000.0,
        baseline_power_w=10.0,
        alternative_throughput_bps=1000.0,
        alternative_power_w=11.0,
    )

    assert positive["identity_pass"] is True
    assert positive["sign_pass"] is True
    assert positive["sign"] == 1
    assert negative["identity_pass"] is True
    assert negative["sign_pass"] is True
    assert negative["sign"] == -1
