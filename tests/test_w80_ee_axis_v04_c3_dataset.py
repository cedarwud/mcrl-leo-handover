"""V0.4 C3 deterministic opening-dataset persistence boundary."""

from __future__ import annotations

import json
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.env.action_contract import NUM_ACTIONS, SlotTable
from mcrl.env.interference import empty_radiating_beams
from mcrl.env.keyed_fading import KeyedFadingField
from mcrl.env.step import ActionEvaluation, StepEnvironment, StepObservation
from mcrl.runtime.ee_axis_opening_pairs import build_opening_pair
from mcrl.runtime.ee_axis_v04_c3_dataset import (
    V04_C3_DATASET_SCHEMA,
    V04C3DatasetContractError,
    V04C3OpeningDataset,
    V04C3OpeningDatasetRow,
    _canonical_sha256,
    read_v04_c3_dataset,
    write_v04_c3_dataset,
)
from mcrl.runtime.ee_axis_v04_c3_opening_source import (
    V04C3OpeningProvenance,
    produce_v04_c3_opening_comparison,
)
from mcrl.runtime.ee_axis_v04_c3_selector import C3_V04_INFORMED_SOURCE_RULE
from mcrl.runtime.ee_axis_v04_c3_state import encode_ee_axis_v04_c3_state


def _table(keys: dict[int, tuple[int, int]]) -> SlotTable:
    norads = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    cells = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    mask = np.zeros(NUM_ACTIONS, dtype=np.bool_)
    for action, (norad, cell) in keys.items():
        norads[action] = norad
        cells[action] = cell
        mask[action] = True
    return SlotTable(norads, cells, mask)


def _fixture(tag: str = "w78"):
    tables = (
        _table({0: (101, 1), 1: (202, 2), 2: (505, 5)}),
        _table({0: (101, 1), 1: (303, 3)}),
        _table({0: (101, 2), 1: (404, 4)}),
    )
    masks = np.stack([table.mask for table in tables])
    candidates = SimpleNamespace(slot_tables=tables, masks=masks)
    observation = StepObservation(
        step_index=0,
        candidates=candidates,
        user_states=(object(), object(), object()),
        state_matrix=np.zeros((3, 112), dtype=np.float32),
        masks=masks,
        candidate_sinr=np.zeros((3, NUM_ACTIONS), dtype=np.float64),
    )
    field = KeyedFadingField.from_components(tag, 1, 3)
    environment = object.__new__(StepEnvironment)
    environment.num_users = 3
    environment._candidates = candidates
    environment._previous_association = [None, None, None]
    environment._previous_served_rate_bps = np.zeros(3, dtype=np.float64)
    environment._previous_link_power_w = np.zeros(3, dtype=np.float64)
    environment._previous_demand = {}
    environment._previous_radiating = empty_radiating_beams()
    environment._segments = [None, None, None]
    environment._step_index = 0
    environment._fading_field = field
    environment.physics = SimpleNamespace(beam_power_max_w=2.2, fading_enabled=True)
    environment.driver = SimpleNamespace(
        grid=SimpleNamespace(),
        step_index=0,
        config=SimpleNamespace(steps_per_episode=10),
    )
    return environment, observation, field


def _provenance(
    field: KeyedFadingField,
    *,
    manifest: str = "b" * 64,
    checkpoint: str = "c" * 64,
    rule: str = C3_V04_INFORMED_SOURCE_RULE,
) -> V04C3OpeningProvenance:
    return V04C3OpeningProvenance(
        source_policy_version=7,
        anchor_sha256="a" * 64,
        source_manifest_sha256=manifest,
        checkpoint_sha256=checkpoint,
        common_random_field_sha256=field.root_digest,
        c3_source_rule=rule,
    )


def _evaluation(actions: np.ndarray) -> ActionEvaluation:
    action = int(actions[0])
    if action == 0:
        rates, power = [100.0, 200.0, 300.0], 10.0
    elif action == 1:
        rates, power = [110.0, 180.0, 330.0], 12.0
    else:
        rates, power = [90.0, 220.0, 280.0], 11.0
    return ActionEvaluation(
        rewards=(),
        resolution=SimpleNamespace(),
        energy=SimpleNamespace(),
        interference=SimpleNamespace(),
        radiating=empty_radiating_beams(),
        link_power_w=np.zeros(3, dtype=np.float64),
        link_sinr=np.zeros(3, dtype=np.float64),
        link_rate_bps=np.asarray(rates, dtype=np.float64),
        handovers=(),
        system_power_w=power,
        fixed_power_w=0.0,
    )


def _comparison(environment, observation, field, monkeypatch, *, action=1, provenance=None):
    state = encode_ee_axis_v04_c3_state(
        environment, observation, interval_s=2.0, kappa_bits=100.0
    )
    reference = np.asarray([0, 0, 0], dtype=np.int64)
    candidate = np.asarray([action, 0, 0], dtype=np.int64)

    def fake_evaluate(self, actions, rng):
        return _evaluation(actions)

    monkeypatch.setattr(StepEnvironment, "evaluate_actions", fake_evaluate)
    return produce_v04_c3_opening_comparison(
        environment,
        observation=observation,
        state_observation=state,
        reference_actions=reference,
        candidate_actions=candidate,
        focal_user=0,
        common_random_field=field,
        provenance=provenance or _provenance(field),
        rng=np.random.default_rng(78),
        lambda_bits_per_j=10.0,
        interval_s=2.0,
        kappa_bits=100.0,
    )


def _recompute_document_digest(payload: dict[str, object]) -> None:
    body = {key: value for key, value in payload.items() if key != "dataset_sha256"}
    payload["dataset_sha256"] = _canonical_sha256(body)


def test_dataset_sorts_deduplicates_and_rebuilds_c3_batch(monkeypatch):
    environment, observation, field = _fixture()
    first = _comparison(environment, observation, field, monkeypatch, action=1)
    second = _comparison(environment, observation, field, monkeypatch, action=2)
    dataset = V04C3OpeningDataset.from_comparisons(
        [second, first, first]
    )

    assert dataset.schema == V04_C3_DATASET_SCHEMA
    assert dataset.comparison_sha256s == tuple(sorted(dataset.comparison_sha256s))
    assert len(dataset.rows) == 2
    assert all(row.pair.source_route == "C3" for row in dataset.rows)
    batch = dataset.c3_batch()
    assert batch.route == "C3"
    assert batch.pair_batch.target_surplus_bits.tolist() == [
        row.pair.route_target_surplus_bits for row in dataset.rows
    ]
    assert batch.verify() == batch.batch_sha256


def test_dataset_rejects_mixed_or_conflicting_lineage(monkeypatch):
    environment, observation, field = _fixture()
    base = _comparison(environment, observation, field, monkeypatch)
    dataset = V04C3OpeningDataset.from_comparisons([base])

    variant = _comparison(
        environment,
        observation,
        field,
        monkeypatch,
        provenance=_provenance(field, manifest="d" * 64),
    )
    with pytest.raises(V04C3DatasetContractError, match="manifest"):
        dataset.add(variant)

    row = V04C3OpeningDatasetRow.from_comparison(base)
    with pytest.raises(V04C3DatasetContractError, match="producer comparison digest"):
        V04C3OpeningDataset(
            source_policy_version=7,
            source_manifest_sha256="b" * 64,
            checkpoint_sha256="c" * 64,
            common_random_field_sha256=field.root_digest,
            state_schema=row.state_schema,
            state_schema_sha256=row.state_schema_sha256,
            kappa_bits=100.0,
            rows=(replace(row, producer_comparison_sha256="f" * 64),),
        )


def test_round_trip_is_deterministic_and_publish_is_write_once(monkeypatch, tmp_path):
    environment, observation, field = _fixture()
    first = _comparison(environment, observation, field, monkeypatch, action=1)
    second = _comparison(environment, observation, field, monkeypatch, action=2)
    dataset = V04C3OpeningDataset.from_comparisons([first, second])
    reversed_dataset = V04C3OpeningDataset.from_comparisons([second, first])
    path = tmp_path / "v04-c3.json"
    reversed_path = tmp_path / "v04-c3-reversed.json"

    write_v04_c3_dataset(path, dataset)
    write_v04_c3_dataset(reversed_path, reversed_dataset)
    assert path.read_bytes() == reversed_path.read_bytes()
    restored = read_v04_c3_dataset(path)
    assert restored.comparison_sha256s == dataset.comparison_sha256s
    assert [row.reference_physical_key for row in restored.rows] == [
        row.reference_physical_key for row in dataset.rows
    ]
    assert [row.candidate_physical_key for row in restored.rows] == [
        row.candidate_physical_key for row in dataset.rows
    ]
    assert restored.c3_batch().pair_batch.target_surplus_bits.tolist() == [
        row.pair.route_target_surplus_bits for row in dataset.rows
    ]

    replacement = V04C3OpeningDataset.from_comparisons([first])
    with pytest.raises(V04C3DatasetContractError, match="write-once"):
        write_v04_c3_dataset(path, replacement)


def test_read_rejects_v03_provenance_and_tampered_pair(tmp_path, monkeypatch):
    environment, observation, field = _fixture()
    comparison = _comparison(environment, observation, field, monkeypatch)
    dataset = V04C3OpeningDataset.from_comparisons([comparison])
    path = tmp_path / "v04-c3.json"
    write_v04_c3_dataset(path, dataset)

    stale_source = json.loads(path.read_text(encoding="ascii"))
    stale_source["source_schema"] = "multi-catfish-mcrl-v03-opening-source-v2"
    _recompute_document_digest(stale_source)
    path.write_text(json.dumps(stale_source), encoding="ascii")
    with pytest.raises(V04C3DatasetContractError, match="V0.3 source"):
        read_v04_c3_dataset(path)

    path.unlink()
    write_v04_c3_dataset(path, dataset)
    tampered = json.loads(path.read_text(encoding="ascii"))
    row = tampered["rows"][0]
    row["pair"]["zeta3_nonfocal_externality_bits"] = "0x1.0p+20"
    _recompute_document_digest(tampered)
    path.write_text(json.dumps(tampered), encoding="ascii")
    with pytest.raises(V04C3DatasetContractError, match="rebuilt C3 target"):
        read_v04_c3_dataset(path)


def test_dataset_rejects_v03_comparison_object(monkeypatch):
    environment, observation, field = _fixture()
    # The V0.3 producer result is intentionally not accepted by the strict
    # V0.4 comparison type boundary.
    with pytest.raises(V04C3DatasetContractError, match="V04C3OpeningComparison"):
        V04C3OpeningDataset.from_comparisons([object()])
