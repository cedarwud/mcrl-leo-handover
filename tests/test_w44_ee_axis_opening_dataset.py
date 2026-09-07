"""W-44 — persistent D^o storage for V0.3 opening comparisons."""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from mcrl.env.action_contract import Association, NO_OP_ACTION
from mcrl.env.constants import TLE_ROOT_DEFAULT
from mcrl.env.keyed_fading import KeyedFadingField
from mcrl.env.mobility import MobilityConfig
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.step import StepEnvironment
from mcrl.env.tle import TleArchive
from mcrl.runtime.ee_axis_opening_dataset import (
    OPENING_DATASET_SCHEMA,
    EEAxisOpeningDataset,
    OpeningDatasetContractError,
    read_opening_dataset,
    write_opening_dataset,
)
from mcrl.runtime.ee_axis_opening_source import (
    OpeningSourceProvenance,
    produce_opening_comparison,
)
from mcrl.runtime.ee_axis_state import (
    EE_AXIS_STATE_SCHEMA,
    EE_AXIS_STATE_SCHEMA_SHA256,
    encode_ee_axis_state,
)


_ARCHIVE = Path(TLE_ROOT_DEFAULT).expanduser()
requires_archive = pytest.mark.skipif(
    not _ARCHIVE.is_dir(), reason="TLE archive not present"
)
START = dt.datetime(2026, 8, 20, 6, 0, tzinfo=dt.timezone.utc)


def _environment(*, tag: str = "w44", users: int = 4):
    field = KeyedFadingField.from_components(tag, 1, users)
    environment = StepEnvironment(
        ScenarioDriver(
            TleArchive(_ARCHIVE),
            ScenarioConfig(mobility=MobilityConfig(num_users=users)),
        ),
        fading_field=field,
    )
    rng = np.random.default_rng(2026083101)
    observation = environment.reset(START, rng)
    return environment, observation, rng, field


def _physical_key(table, action: int) -> tuple[int, int] | None:
    if int(action) == NO_OP_ACTION:
        return None
    association = table.association(int(action))
    if not isinstance(association, Association):
        return None
    return int(association.norad_id), int(association.cell_id)


def _reference(observation) -> np.ndarray:
    actions = np.full(observation.num_users, NO_OP_ACTION, dtype=np.int64)
    for uid, mask in enumerate(observation.masks):
        valid = np.flatnonzero(mask)
        if valid.size:
            actions[uid] = int(valid[0])
    return actions


def _action_pairs(observation, *, limit: int = 3):
    reference = _reference(observation)
    pairs = []
    for focal, table in enumerate(observation.candidates.slot_tables):
        reference_key = _physical_key(table, int(reference[focal]))
        for action in np.flatnonzero(observation.masks[focal]).tolist():
            if _physical_key(table, int(action)) == reference_key:
                continue
            candidate = reference.copy()
            candidate[focal] = int(action)
            pairs.append((focal, reference.copy(), candidate))
            if len(pairs) == limit:
                return pairs
    pytest.skip("fixture has too few distinct legal physical alternatives")


def _provenance(
    field: KeyedFadingField,
    *,
    manifest: str = "b" * 64,
    checkpoint: str = "c" * 64,
    c1_rule: str = "sealed-c1-w44-rule",
    c3_rule: str = "sealed-c3-w44-rule",
    admitted_route: str = "C1",
) -> OpeningSourceProvenance:
    return OpeningSourceProvenance(
        source_policy_version=7,
        anchor_sha256="a" * 64,
        source_manifest_sha256=manifest,
        checkpoint_sha256=checkpoint,
        common_random_field_sha256=field.root_digest,
        c1_source_rule=c1_rule,
        c3_source_rule=c3_rule,
        admitted_route=admitted_route,
    )


def _produce(
    environment,
    observation,
    rng,
    field,
    pair,
    *,
    provenance: OpeningSourceProvenance | None = None,
    admitted_route: str = "C1",
):
    return produce_opening_comparison(
        environment,
        observation=observation,
        state_observation=encode_ee_axis_state(environment, observation),
        reference_actions=pair[1],
        candidate_actions=pair[2],
        focal_user=pair[0],
        common_random_field=field,
        provenance=provenance or _provenance(field, admitted_route=admitted_route),
        rng=rng,
        lambda_bits_per_j=10.0,
        interval_s=float(environment.driver.config.ephemeris.time_step_s),
    )


@requires_archive
def test_dataset_deduplicates_raw_rows_and_exposes_deterministic_c1_c3_batches():
    environment, observation, rng, field = _environment()
    pairs = _action_pairs(observation)
    results = [
        _produce(
            environment,
            observation,
            rng,
            field,
            pair,
            admitted_route=("C1" if index != 1 else "C3"),
        )
        for index, pair in enumerate(pairs)
    ]

    dataset = EEAxisOpeningDataset.from_results(
        [results[2], results[0], results[1], results[0]]
    )

    assert dataset.schema == OPENING_DATASET_SCHEMA
    assert dataset.state_schema == EE_AXIS_STATE_SCHEMA
    assert dataset.state_schema_sha256 == EE_AXIS_STATE_SCHEMA_SHA256
    assert len(dataset.rows) == 3
    assert dataset.raw_comparison_sha256s == tuple(
        sorted(result.raw_pair.comparison_sha256 for result in results)
    )
    assert dataset.c1_batch().route == "C1"
    assert dataset.c3_batch().route == "C3"
    assert len(dataset.c1_pairs) == 2
    assert len(dataset.c3_pairs) == 1
    assert dataset.c1_batch().verify() == dataset.c1_batch().batch_sha256
    assert dataset.c3_batch().verify() == dataset.c3_batch().batch_sha256

    by_digest = {result.raw_pair.comparison_sha256: result for result in results}
    for row in dataset.rows:
        result = by_digest[row.raw_pair.comparison_sha256]
        assert row.zeta1_focal_surplus_bits == result.c1.pair.zeta1_focal_surplus_bits
        assert (
            row.zeta3_nonfocal_externality_bits
            == result.c3.pair.zeta3_nonfocal_externality_bits
        )
        assert row.c1_source_rule == result.c1.pair.source_rule
        assert row.c3_source_rule == result.c3.pair.source_rule


@requires_archive
def test_dataset_keeps_signed_zero_and_nonzero_targets_without_sign_filtering():
    environment, observation, rng, field = _environment()
    results = [
        _produce(
            environment,
            observation,
            rng,
            field,
            pair,
            admitted_route=("C1" if index % 2 == 0 else "C3"),
        )
        for index, pair in enumerate(_action_pairs(observation))
    ]
    dataset = EEAxisOpeningDataset.from_results(results)

    c1_targets = [pair.route_target_surplus_bits for pair in dataset.c1_pairs]
    c3_targets = [pair.route_target_surplus_bits for pair in dataset.c3_pairs]
    by_digest = {result.raw_pair.comparison_sha256: result for result in results}
    expected_c1 = [
        by_digest[row.raw_pair.comparison_sha256].c1.pair.route_target_surplus_bits
        for row in dataset.rows
        if row.admitted_route == "C1"
    ]
    expected_c3 = [
        by_digest[row.raw_pair.comparison_sha256].c3.pair.route_target_surplus_bits
        for row in dataset.rows
        if row.admitted_route == "C3"
    ]
    assert c1_targets == expected_c1
    assert c3_targets == expected_c3
    assert any(value < 0.0 for value in c1_targets)
    assert any(value > 0.0 for value in c3_targets)
    assert all(np.isfinite(value) for value in c1_targets + c3_targets)


@requires_archive
def test_same_raw_comparison_can_be_admitted_once_per_independent_route():
    environment, observation, rng, field = _environment()
    pair = _action_pairs(observation, limit=1)[0]
    c1 = _produce(
        environment, observation, rng, field, pair, admitted_route="C1"
    )
    c3 = _produce(
        environment, observation, rng, field, pair, admitted_route="C3"
    )
    assert c1.raw_pair.comparison_sha256 == c3.raw_pair.comparison_sha256

    dataset = EEAxisOpeningDataset.from_results([c3, c1, c1])
    assert len(dataset.rows) == 2
    assert len(dataset.c1_pairs) == 1
    assert len(dataset.c3_pairs) == 1
    assert [row.admitted_route for row in dataset.rows] == ["C1", "C3"]


@requires_archive
def test_dataset_rejects_mixed_manifest_checkpoint_random_field_and_conflicting_duplicate():
    environment, observation, rng, field = _environment()
    pair = _action_pairs(observation, limit=1)[0]
    base = _produce(environment, observation, rng, field, pair)
    dataset = EEAxisOpeningDataset.from_results([base])

    # Exact replay of the same raw comparison is idempotent.
    assert dataset.add(base).rows == dataset.rows

    manifest_variant = _produce(
        environment,
        observation,
        rng,
        field,
        pair,
        provenance=_provenance(field, manifest="d" * 64),
    )
    with pytest.raises(OpeningDatasetContractError, match="source manifest"):
        dataset.add(manifest_variant)

    checkpoint_variant = _produce(
        environment,
        observation,
        rng,
        field,
        pair,
        provenance=_provenance(field, checkpoint="e" * 64),
    )
    with pytest.raises(OpeningDatasetContractError, match="checkpoint"):
        dataset.add(checkpoint_variant)

    rule_variant = _produce(
        environment,
        observation,
        rng,
        field,
        pair,
        provenance=_provenance(field, c1_rule="different-c1-rule"),
    )
    with pytest.raises(OpeningDatasetContractError, match="duplicate raw"):
        dataset.add(rule_variant)

    foreign_environment, foreign_observation, foreign_rng, foreign_field = _environment(
        tag="w44-foreign"
    )
    foreign = _produce(
        foreign_environment,
        foreign_observation,
        foreign_rng,
        foreign_field,
        _action_pairs(foreign_observation, limit=1)[0],
        provenance=OpeningSourceProvenance(
            source_policy_version=7,
            anchor_sha256="a" * 64,
            source_manifest_sha256="b" * 64,
            checkpoint_sha256="c" * 64,
            common_random_field_sha256=foreign_field.root_digest,
            c1_source_rule="sealed-c1-w44-rule",
            c3_source_rule="sealed-c3-w44-rule",
            admitted_route="C1",
        ),
    )
    with pytest.raises(OpeningDatasetContractError, match="random field"):
        dataset.add(foreign)


@requires_archive
def test_dataset_round_trip_is_deterministic_and_write_once_atomic(tmp_path: Path):
    environment, observation, rng, field = _environment()
    results = [
        _produce(
            environment,
            observation,
            rng,
            field,
            pair,
            admitted_route=("C1" if index == 0 else "C3"),
        )
        for index, pair in enumerate(_action_pairs(observation, limit=2))
    ]
    first = EEAxisOpeningDataset.from_results(results)
    second = EEAxisOpeningDataset.from_results(reversed(results))
    first_path = tmp_path / "opening-dataset.json"
    second_path = tmp_path / "opening-dataset-reversed.json"

    assert write_opening_dataset(first_path, first) == first_path
    assert write_opening_dataset(second_path, second) == second_path
    assert first_path.read_bytes() == second_path.read_bytes()

    restored = read_opening_dataset(first_path)
    assert restored.raw_comparison_sha256s == first.raw_comparison_sha256s
    assert [row.c1_comparison_sha256 for row in restored.rows] == [
        row.c1_comparison_sha256 for row in first.rows
    ]
    assert restored.c1_batch().pair_batch.target_surplus_bits.tolist() == [
        pair.route_target_surplus_bits for pair in first.c1_pairs
    ]

    original_bytes = first_path.read_bytes()
    with pytest.raises(OpeningDatasetContractError, match="write-once"):
        write_opening_dataset(first_path, first)
    assert first_path.read_bytes() == original_bytes


@requires_archive
def test_dataset_read_rejects_tampered_schema_or_lineage(tmp_path: Path):
    environment, observation, rng, field = _environment()
    result = _produce(environment, observation, rng, field, _action_pairs(observation, limit=1)[0])
    dataset = EEAxisOpeningDataset.from_results([result])
    path = tmp_path / "opening-dataset.json"
    write_opening_dataset(path, dataset)

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["source_schema"] = "legacy-opening-pair-v1"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(OpeningDatasetContractError, match="digest|schema"):
        read_opening_dataset(path)

    write_opening_dataset(tmp_path / "clean.json", dataset)
    clean_path = tmp_path / "clean.json"
    clean = json.loads(clean_path.read_text(encoding="utf-8"))
    clean["source_manifest_sha256"] = "f" * 64
    clean_path.write_text(json.dumps(clean), encoding="utf-8")
    with pytest.raises(OpeningDatasetContractError, match="digest|manifest"):
        read_opening_dataset(clean_path)
