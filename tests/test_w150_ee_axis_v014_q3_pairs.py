"""W-150 -- complete legal-action ZR-Q3 pair dataset."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.env.action_contract import NUM_ACTIONS, SlotTable
from mcrl.env.interference import RadiatingBeams
from mcrl.env.step import StepEnvironment, StepObservation
from mcrl.runtime.ee_axis_state import EE_AXIS_BASE_STATE_DIM
from mcrl.runtime.ee_axis_v014_q3_pairs import (
    EEAxisV014Q3PairError,
    build_ee_axis_v014_q3_pair_dataset,
)
from mcrl.runtime.ee_axis_v014_q3_state import encode_ee_axis_v014_q3_state
from mcrl.runtime.ee_axis_zero_marginal_c3 import build_zr_surface


def _state():
    norads = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    cells = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    mask = np.zeros(NUM_ACTIONS, dtype=np.bool_)
    for action in (0, 1, 2):
        norads[action] = 100 + action
        cells[action] = action
        mask[action] = True
    table = SlotTable(norads, cells, mask)
    candidates = SimpleNamespace(slot_tables=(table,))
    observation = StepObservation(
        step_index=0,
        candidates=candidates,
        user_states=(object(),),
        state_matrix=np.zeros((1, EE_AXIS_BASE_STATE_DIM), dtype=np.float32),
        masks=mask[None, :],
        candidate_sinr=np.zeros((1, NUM_ACTIONS), dtype=np.float64),
    )
    environment = object.__new__(StepEnvironment)
    environment.num_users = 1
    environment._candidates = candidates
    environment._previous_association = [None]
    environment._previous_served_rate_bps = np.zeros(1, dtype=np.float64)
    environment._previous_link_power_w = np.zeros(1, dtype=np.float64)
    environment._segments = [None]
    environment._previous_radiating = RadiatingBeams(
        norad_ids=np.empty(0, dtype=np.int64),
        cell_ids=np.empty(0, dtype=np.int64),
        satellite_ecef_km=np.empty((0, 3), dtype=np.float64),
        cell_centre_ecef_km=np.empty((0, 3), dtype=np.float64),
        colors=np.empty(0, dtype=np.int64),
        power_w=np.empty(0, dtype=np.float64),
    )
    environment.physics = SimpleNamespace(beam_power_max_w=2.2)
    environment.driver = SimpleNamespace(config=SimpleNamespace(steps_per_episode=10))
    return encode_ee_axis_v014_q3_state(
        environment, observation, interval_s=1.0, kappa_bits=10.0
    )


def _surface():
    legal = np.zeros(NUM_ACTIONS, dtype=np.bool_)
    legal[:3] = True
    compatibility = np.zeros(NUM_ACTIONS, dtype=np.bool_)
    compatibility[[0, 1]] = True
    candidate = np.tile(np.asarray([10.0]), (NUM_ACTIONS, 1))
    candidate[0, 0] = 10.0
    candidate[1, 0] = 12.0
    candidate[2, 0] = 9.0
    return build_zr_surface(
        baseline_rate_bps=np.asarray([10.0]),
        candidate_rate_bps=candidate,
        compatibility=compatibility,
        legal_mask=legal,
        reference_action=0,
        interval_s=1.0,
        kappa_bits=10.0,
    )


def test_builder_emits_complete_signed_zr_pairs_in_native_bits() -> None:
    dataset = build_ee_axis_v014_q3_pair_dataset(
        state=_state(),
        surfaces=(_surface(),),
        source_seed=33,
        anchor_sha256s=("a" * 64,),
    )
    assert dataset.batch.reference_actions.tolist() == [0, 0]
    assert dataset.batch.candidate_actions.tolist() == [1, 2]
    assert dataset.batch.target_surplus_bits.tolist() == [2.0, -1.0]
    assert dataset.source_seeds.tolist() == [33, 33]
    assert dataset.anchor_sha256s.tolist() == ["a" * 64, "a" * 64]
    dataset.verify()


def test_builder_rejects_mask_or_metadata_mismatch() -> None:
    state = _state()
    surface = _surface()
    different = np.array(surface.legal_mask, copy=True)
    different[2] = False
    # Rebuild a valid teacher with a deliberately different legal set.
    candidate = np.asarray(surface.candidate_rate_bps)
    mismatched = build_zr_surface(
        baseline_rate_bps=surface.baseline_rate_bps,
        candidate_rate_bps=candidate,
        compatibility=np.asarray(surface.compatibility) & different,
        legal_mask=different,
        reference_action=0,
        interval_s=surface.interval_s,
        kappa_bits=surface.kappa_bits,
    )
    with pytest.raises(EEAxisV014Q3PairError, match="mask"):
        build_ee_axis_v014_q3_pair_dataset(
            state=state,
            surfaces=(mismatched,),
            source_seed=33,
            anchor_sha256s=("b" * 64,),
        )
    with pytest.raises(EEAxisV014Q3PairError, match="anchor"):
        build_ee_axis_v014_q3_pair_dataset(
            state=state,
            surfaces=(surface,),
            source_seed=33,
            anchor_sha256s=(),
        )
