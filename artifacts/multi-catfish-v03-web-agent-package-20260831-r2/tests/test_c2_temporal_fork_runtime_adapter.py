from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import c2_stage0_receipt_adapter as STAGE0  # noqa: E402
import c2_temporal_fork_core as C2  # noqa: E402
import c2_temporal_fork_runtime_adapter as ADAPTER  # noqa: E402


def digest(label):
    return hashlib.sha256(label.encode()).hexdigest()


def authority():
    return C2.ForecastAuthority(
        schema=C2.FORECAST_AUTHORITY_SCHEMA,
        anchor_sha256=digest("anchor"),
        reference_checkpoint_sha256=digest("checkpoint"),
        environment_source_sha256=digest("environment"),
        reward_source_sha256=digest("reward"),
        live_rng_state_sha256=digest("live"),
        forecast_rng_state_sha256=digest("forecast"),
        forecast_request_sha256=digest("forecast-request"),
        forecast_payload_sha256=digest("forecast-payload"),
        forecast_namespace="c2-v03/runtime-adapter-fixture",
        fading_mode="disabled",
        generated_preoutcome=True,
        adapter_version="runtime-adapter-v1",
    )


class Table:
    def __init__(self):
        self.mask = np.zeros(C2.ACTION_DIM, dtype=bool)
        self.norad_ids = np.full(C2.ACTION_DIM, -1, dtype=int)
        self.cell_ids = np.full(C2.ACTION_DIM, -1, dtype=int)
        self.mask[[3, 5]] = True
        self.norad_ids[[3, 5]] = 56355
        self.cell_ids[[3, 5]] = [30, 31]


def candidate(*, certified=True, focal=1, cell=30):
    return SimpleNamespace(
        focal_user=focal,
        incumbent_id=(56355, 29),
        reference_departure_id=(56355, 31),
        candidate_id=(56355, cell),
        certified=certified,
        first_failed_layer=None if certified else "activation_or_energy",
        reasons=() if certified else ("activation_or_energy_failed",),
        hold_system_r2_delta=0.5 if certified else 0.0,
        full_system_r2_delta=0.5 if certified else 0.0,
        reference_energy_j=100.0,
        candidate_energy_j=90.0 if certified else 110.0,
        reference_useful_bits=1000.0,
        candidate_useful_bits=1000.0,
        beam_pulses=((56355, 31),) if certified else (),
        satellite_pulses=(),
    )


def replay_lineages(*, focal=1, cell=30):
    return {
        (focal, (56355, cell)): STAGE0.LegacyReplayLineage(
            opening_state_sha256=digest(f"opening-state-{focal}-{cell}"),
            opening_mask_sha256=digest(f"opening-mask-{focal}-{cell}"),
            reference_branch_trace_sha256=digest(f"reference-trace-{focal}-{cell}"),
            candidate_branch_trace_sha256=digest(f"candidate-trace-{focal}-{cell}"),
        )
    }


def test_single_old_certified_alternative_is_segregated_from_v03a_runtime():
    # The old support maps are intentionally empty: its >=2-alternative rule
    # discarded this focal despite one full certificate.
    support = SimpleNamespace(
        receipts=(candidate(),),
        support_actions_by_user={},
        support_ids_by_user={},
    )
    with pytest.raises(C2.C2ContractError, match="policy-alignment proof"):
        ADAPTER.build_runtime_frontier(
            support,
            authority=authority(),
            slot_tables=(Table(), Table()),
            user_count=2,
            replay_lineage_by_candidate=replay_lineages(),
        )


def test_failed_historical_rows_are_ignored_not_rescued():
    support = SimpleNamespace(receipts=(candidate(certified=False),))
    frontier = ADAPTER.build_runtime_frontier(
        support,
        authority=authority(),
        slot_tables=(Table(), Table()),
        user_count=2,
        replay_lineage_by_candidate={},
    )
    assert frontier.certified_candidates == 0
    assert frontier.certificates_by_user == {}


def test_historical_reference_self_row_is_skipped_not_fatal():
    support = SimpleNamespace(receipts=(candidate(cell=31),))
    frontier = ADAPTER.build_runtime_frontier(
        support,
        authority=authority(),
        slot_tables=(Table(), Table()),
        user_count=2,
        replay_lineage_by_candidate={},
    )
    assert frontier.certified_candidates == 0
    assert frontier.certificates_by_user == {}


def test_duplicate_certified_physical_candidate_fails_closed():
    support = SimpleNamespace(receipts=(candidate(), candidate()))
    with pytest.raises(C2.C2ContractError, match="repeats"):
        ADAPTER.build_runtime_frontier(
            support,
            authority=authority(),
            slot_tables=(Table(), Table()),
            user_count=2,
            replay_lineage_by_candidate=replay_lineages(),
        )


def test_certified_candidate_must_map_uniquely_in_current_table():
    unsupported = candidate(cell=99)
    support = SimpleNamespace(receipts=(unsupported,))
    with pytest.raises(C2.C2ContractError, match="candidate physical key"):
        ADAPTER.build_runtime_frontier(
            support,
            authority=authority(),
            slot_tables=(Table(), Table()),
            user_count=2,
            replay_lineage_by_candidate=replay_lineages(cell=99),
        )


def test_slot_table_requires_boolean_mask_and_unique_physical_ids():
    malformed = Table()
    malformed.mask = malformed.mask.astype(int)
    with pytest.raises(C2.C2ContractError, match="Boolean"):
        ADAPTER.action_bindings_from_slot_table(malformed)

    duplicate = Table()
    duplicate.norad_ids[5] = duplicate.norad_ids[3]
    duplicate.cell_ids[5] = duplicate.cell_ids[3]
    with pytest.raises(C2.C2ContractError, match="repeat a physical key"):
        ADAPTER.action_bindings_from_slot_table(duplicate)


def test_certified_historical_row_requires_lossless_replay_lineage():
    support = SimpleNamespace(receipts=(candidate(),))
    with pytest.raises(C2.C2ContractError, match="lossless replay lineage"):
        ADAPTER.build_runtime_frontier(
            support,
            authority=authority(),
            slot_tables=(Table(), Table()),
            user_count=2,
            replay_lineage_by_candidate={},
        )


def test_slot_table_requires_frozen_28_action_width():
    malformed = Table()
    malformed.mask = malformed.mask[:-1]
    malformed.norad_ids = malformed.norad_ids[:-1]
    malformed.cell_ids = malformed.cell_ids[:-1]
    with pytest.raises(C2.C2ContractError, match="exactly 28"):
        ADAPTER.action_bindings_from_slot_table(malformed)
