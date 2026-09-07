"""W-173 -- V0.18 relational-ZR C3 predecision seam.

These tests deliberately stay at the encoder boundary.  They exercise the
physical-key predicates and immutable representation without opening an
action outcome, consuming a random field, or running an episode.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.env.action_contract import NUM_ACTIONS, SlotTable
from mcrl.env.step import StepEnvironment, StepObservation
from mcrl.runtime.ee_axis_relational_zr_c3 import (
    RELATIONAL_ZR_ACTION_CONTEXT_DIM,
    RELATIONAL_ZR_VICTIM_TOKEN_DIM,
    RelationalZRC3Error,
    compute_positive_credit_compatible,
    compute_victim_mask,
    encode_relational_zr_c3_state,
    nominal_relational_zr_surface,
)


def _table(keys: dict[int, tuple[int, int]]) -> SlotTable:
    norads = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    cells = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    mask = np.zeros(NUM_ACTIONS, dtype=np.bool_)
    for action, (norad, cell) in keys.items():
        norads[action] = norad
        cells[action] = cell
        mask[action] = True
    return SlotTable(norads, cells, mask)


def _identity_panel() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """A small panel whose rows intentionally use different slot identities."""

    users = 3
    legal = np.zeros((users, NUM_ACTIONS), dtype=np.bool_)
    norads = np.full((users, NUM_ACTIONS), -1, dtype=np.int64)
    cells = np.full((users, NUM_ACTIONS), -1, dtype=np.int64)

    def add(user: int, action: int, key: tuple[int, int]) -> None:
        legal[user, action] = True
        norads[user, action], cells[user, action] = key

    # The reference key of user 0 has a same-satellite co-channel peer, a
    # different-satellite co-channel peer, and a different-colour peer.
    add(0, 0, (101, 1))
    add(0, 1, (101, 1))  # same physical key, different flat slot
    add(0, 2, (202, 4))  # candidate-only changed key
    add(1, 0, (101, 2))  # same satellite, same colour, different cell
    add(1, 1, (303, 2))  # different satellite, same colour
    add(2, 0, (101, 3))  # different colour
    add(2, 1, (101, 1))  # exact same physical key as user 0

    references = np.asarray([0, 0, 0], dtype=np.int64)
    opening = np.zeros_like(legal)
    opening[0, 0] = True
    opening[0, 1] = True
    opening[0, 2] = True
    opening[1, 0] = True
    opening[2, 0] = True
    powers = np.zeros((users, NUM_ACTIONS), dtype=np.float64)
    powers[0, 0] = 0.5
    powers[0, 1] = 0.5
    powers[0, 2] = 0.6
    powers[1, 0] = 0.4
    powers[1, 1] = 0.7
    powers[2, 0] = 0.3
    powers[2, 1] = 0.5
    colours = np.asarray([0, 0, 0, 1, 0], dtype=np.int64)
    return references, legal, opening, powers, np.stack((norads, cells, np.zeros_like(norads)), axis=-1)[..., :2], colours


def _base_fixture() -> tuple[StepEnvironment, StepObservation, np.ndarray, np.ndarray, np.ndarray]:
    tables = (
        _table({0: (101, 0), 1: (101, 1), 2: (202, 4), 7: (202, 0)}),
        _table({0: (101, 1), 1: (303, 2), 7: (202, 2)}),
        _table({0: (202, 0), 1: (303, 3), 7: (404, 4)}),
    )
    users = len(tables)
    candidates = SimpleNamespace(
        slot_tables=tables,
        # Candidate geometry is supplied as current predecision geometry.
        off_axis_deg=np.zeros((users, 4, 7), dtype=np.float64),
        slant_range_km=np.full((users, 4), 550.0, dtype=np.float64),
        elevation_deg=np.full((users, 4), 60.0, dtype=np.float64),
        window_norad_ids=np.asarray(
            [[101, 202, 303, 404]] * users, dtype=np.int64
        ),
        window_satellite_ecef_km=np.asarray(
            [
                [[6800.0, 0.0, 0.0], [0.0, 6800.0, 0.0], [-6800.0, 0.0, 0.0], [0.0, -6800.0, 0.0]],
            ]
            * users,
            dtype=np.float64,
        ),
        cell_colors=np.asarray([0, 0, 0, 1, 0], dtype=np.int64),
        cell_centres_ecef_km=np.asarray(
            [
                [6371.0, 0.0, 0.0],
                [6368.0, 100.0, 0.0],
                [6368.0, -100.0, 0.0],
                [6368.0, 0.0, 100.0],
                [6368.0, 0.0, -100.0],
            ],
            dtype=np.float64,
        ),
    )
    masks = np.stack([table.mask for table in tables])
    observation = StepObservation(
        step_index=0,
        candidates=candidates,
        user_states=(object(),) * users,
        state_matrix=np.zeros((users, 112), dtype=np.float32),
        masks=masks,
        candidate_sinr=np.full((users, NUM_ACTIONS), 2.0, dtype=np.float64),
    )
    environment = object.__new__(StepEnvironment)
    environment.num_users = users
    environment._candidates = candidates
    environment.physics = SimpleNamespace(
        beam_power_max_w=2.0,
        beam_bandwidth_hz=1.0e6,
        noise_power_w=1.0e-9,
    )
    environment.driver = SimpleNamespace(
        grid=SimpleNamespace(
            colors=candidates.cell_colors,
            centers_ecef_km=candidates.cell_centres_ecef_km,
        ),
        user_ecef_km=lambda: np.asarray(
            [[6371.0, 0.0, 0.0], [6368.0, 100.0, 0.0], [6368.0, -100.0, 0.0]],
            dtype=np.float64,
        ),
        satellite_ecef_at=lambda _offset: {
            101: np.asarray([6800.0, 0.0, 0.0]),
            202: np.asarray([0.0, 6800.0, 0.0]),
            303: np.asarray([-6800.0, 0.0, 0.0]),
            404: np.asarray([0.0, -6800.0, 0.0]),
        },
    )
    references = np.asarray([0, 0, 0], dtype=np.int64)
    opening = np.zeros_like(masks)
    opening[masks] = True
    powers = np.zeros((users, NUM_ACTIONS), dtype=np.float64)
    for uid, row in enumerate(masks):
        powers[uid, row] = 0.25 + 0.01 * np.flatnonzero(row)
    return environment, observation, references, opening, powers


def test_positive_credit_has_same_key_add_remove_and_both_unserved_branches() -> None:
    references, legal, opening, powers, identity, _colours = _identity_panel()
    norads, cells = identity[..., 0], identity[..., 1]
    compatible = compute_positive_credit_compatible(
        reference_actions=references,
        action_mask=legal,
        opening_feasibility_surface=opening,
        required_power_surface=powers,
        candidate_norad_ids=norads,
        candidate_cell_ids=cells,
    )
    # User 0 action 1 has the exact same key and power as its reference;
    # action 2 adds a different active beam and is not compatible.
    assert bool(compatible[0, 1])
    assert not bool(compatible[0, 2])

    both_unserved_opening = opening.copy()
    both_unserved_opening[0, 0] = False
    both_unserved_opening[0, 2] = False
    assert bool(
        compute_positive_credit_compatible(
            reference_actions=references,
            action_mask=legal,
            opening_feasibility_surface=both_unserved_opening,
            required_power_surface=powers,
            candidate_norad_ids=norads,
            candidate_cell_ids=cells,
        )[0, 2]
    )


def test_all_empty_reference_is_guarded_and_byte_sensitive_max_power_is_exact() -> None:
    references, legal, opening, powers, identity, _colours = _identity_panel()
    norads, cells = identity[..., 0], identity[..., 1]
    empty_legal = legal.copy()
    empty_legal[0] = False
    empty_opening = opening.copy()
    empty_opening[0] = False
    empty_refs = references.copy()
    empty_refs[0] = -1
    empty_result = compute_positive_credit_compatible(
        reference_actions=empty_refs,
        action_mask=empty_legal,
        opening_feasibility_surface=empty_opening,
        required_power_surface=powers,
        candidate_norad_ids=norads,
        candidate_cell_ids=cells,
    )
    assert not np.any(empty_result[0])

    bad_reference = references.copy()
    bad_reference[0] = -1
    with pytest.raises(RelationalZRC3Error, match="all-empty"):
        compute_positive_credit_compatible(
            reference_actions=bad_reference,
            action_mask=legal,
            opening_feasibility_surface=opening,
            required_power_surface=powers,
            candidate_norad_ids=norads,
            candidate_cell_ids=cells,
        )

    # For focal user 0, action 1 keeps the same key but a one-ULP change in
    # the focal max power must fail the byte-sensitive comparison.
    exact = compute_positive_credit_compatible(
        reference_actions=references,
        action_mask=legal,
        opening_feasibility_surface=opening,
        required_power_surface=powers,
        candidate_norad_ids=norads,
        candidate_cell_ids=cells,
    )
    altered_power = powers.copy()
    altered_power[0, 1] = np.nextafter(altered_power[0, 1], np.inf)
    altered = compute_positive_credit_compatible(
        reference_actions=references,
        action_mask=legal,
        opening_feasibility_surface=opening,
        required_power_surface=altered_power,
        candidate_norad_ids=norads,
        candidate_cell_ids=cells,
    )
    assert bool(exact[0, 1])
    assert not bool(altered[0, 1])


def test_victim_mask_uses_exact_same_beam_and_cochannel_predicates() -> None:
    references, legal, opening, powers, identity, colours = _identity_panel()
    del powers
    norads, cells = identity[..., 0], identity[..., 1]
    victim = compute_victim_mask(
        reference_actions=references,
        action_mask=legal,
        opening_feasibility_surface=opening,
        candidate_norad_ids=norads,
        candidate_cell_ids=cells,
        cell_colors=colours,
    )
    # Focal 0 action 0 changes its opened origin beam.  User 1 is same
    # satellite/different cell with the same colour; user 2 is different
    # colour.  User 0 itself is never a victim.
    assert bool(victim[0, 0, 1])
    assert not bool(victim[0, 0, 2])
    assert not bool(victim[0, 0, 0])
    # Different-satellite same-colour co-channel case.
    opening_with_alt = opening.copy()
    opening_with_alt[0, 2] = True
    assert bool(
        compute_victim_mask(
            reference_actions=references,
            action_mask=legal,
            opening_feasibility_surface=opening_with_alt,
            candidate_norad_ids=norads,
            candidate_cell_ids=cells,
            cell_colors=colours,
        )[0, 2, 1]
    )
    # A reference-unserved user is excluded even when its physical key would
    # otherwise be co-channel.
    opening_unserved = opening.copy()
    opening_unserved[1, 0] = False
    assert not bool(
        compute_victim_mask(
            reference_actions=references,
            action_mask=legal,
            opening_feasibility_surface=opening_unserved,
            candidate_norad_ids=norads,
            candidate_cell_ids=cells,
            cell_colors=colours,
        )[0, 0, 1]
    )
    # No focal branch changes when both branches are unserved, hence no real
    # victim rows are opened.
    opening_both_unserved = opening.copy()
    opening_both_unserved[0, 0] = False
    opening_both_unserved[0, 1] = False
    opening_both_unserved[0, 2] = False
    assert not np.any(
        compute_victim_mask(
            reference_actions=references,
            action_mask=legal,
            opening_feasibility_surface=opening_both_unserved,
            candidate_norad_ids=norads,
            candidate_cell_ids=cells,
            cell_colors=colours,
        )[0]
    )


def test_encoder_preserves_shapes_zeroes_focal_and_padding_and_keeps_nonfocal_signal() -> None:
    environment, observation, references, opening, powers = _base_fixture()
    encoded = encode_relational_zr_c3_state(
        environment,
        observation,
        references,
        required_power_surface=powers,
        opening_feasibility_surface=opening,
    )
    users = len(references)
    assert encoded.action_context.shape == (users, NUM_ACTIONS, RELATIONAL_ZR_ACTION_CONTEXT_DIM)
    assert encoded.victim_tokens.shape == (users, NUM_ACTIONS, users, RELATIONAL_ZR_VICTIM_TOKEN_DIM)
    assert encoded.action_mask.shape == (users, NUM_ACTIONS)
    assert encoded.victim_mask.shape == (users, NUM_ACTIONS, users)
    assert not np.any(encoded.victim_mask[np.arange(users), :, np.arange(users)])
    assert np.all(encoded.victim_tokens[~encoded.victim_mask] == 0.0)
    assert np.all(encoded.action_context[~encoded.action_mask] == 0.0)

    # The focal delta was fixed to the diagonal only: at least one legal
    # non-focal token survives while every focal/padded row remains zero.
    assert np.any(encoded.victim_mask)
    assert np.any(encoded.victim_tokens[encoded.victim_mask] != 0.0)
    encoded.verify()
    assert not encoded.action_context.flags.writeable
    assert not encoded.victim_tokens.flags.writeable
    assert not encoded.action_mask.flags.writeable
    assert not encoded.victim_mask.flags.writeable
    assert not encoded.positive_credit_compatible.flags.writeable
    assert not encoded.reference_actions.flags.writeable


def test_nominal_zr_surface_is_predecision_diagnostic_and_centred_on_reference() -> None:
    environment, observation, references, opening, powers = _base_fixture()
    delta, q3 = nominal_relational_zr_surface(
        environment,
        observation,
        reference_actions=references,
        required_power_surface=powers,
        opening_feasibility_surface=opening,
        interval_s=1.0,
        kappa_bits=1.0,
    )
    users = len(references)
    assert delta.shape == (users, NUM_ACTIONS, users)
    assert q3.shape == (users, NUM_ACTIONS)
    assert not delta.flags.writeable
    assert not q3.flags.writeable
    assert np.all(delta[np.arange(users), :, np.arange(users)] == 0.0)
    assert np.all(q3[np.arange(users), references] == 0.0)
    # The relational panel is not allowed to disappear into an accidentally
    # all-focal implementation.
    assert np.any(delta != 0.0)


def test_encoder_is_detached_immutable_and_digest_verified() -> None:
    environment, observation, references, opening, powers = _base_fixture()
    encoded = encode_relational_zr_c3_state(
        environment,
        observation,
        references,
        required_power_surface=powers,
        opening_feasibility_surface=opening,
    )
    digest = encoded.content_digest
    powers[0, 0] += 1.0
    opening[0, 0] = False
    assert encoded.content_digest == digest
    with pytest.raises(ValueError):
        encoded.action_context[0, 0, 0] = 0.0
    with pytest.raises(RelationalZRC3Error, match="digest"):
        replace(encoded, content_digest="0" * 64).verify()


def test_user_relabel_is_equivariant_and_action_slots_follow_physical_keys() -> None:
    references, legal, opening, powers, identity, colours = _identity_panel()
    norads, cells = identity[..., 0], identity[..., 1]
    original = compute_victim_mask(
        reference_actions=references,
        action_mask=legal,
        opening_feasibility_surface=opening,
        candidate_norad_ids=norads,
        candidate_cell_ids=cells,
        cell_colors=colours,
    )
    permutation = np.asarray([2, 0, 1], dtype=np.int64)
    relabelled = compute_victim_mask(
        reference_actions=references[permutation],
        action_mask=legal[permutation],
        opening_feasibility_surface=opening[permutation],
        candidate_norad_ids=norads[permutation],
        candidate_cell_ids=cells[permutation],
        cell_colors=colours,
    )
    np.testing.assert_array_equal(relabelled, original[permutation][:, :, permutation])
    # Flat action 0 and action 1 denote the same physical key for focal 0;
    # replacing one slot does not alter its victim relation.
    assert np.array_equal(original[0, 0], original[0, 1])


def test_source_does_not_depend_on_realised_evaluation_or_randomness() -> None:
    source = Path(__file__).resolve().parents[1] / "src/mcrl/runtime/ee_axis_relational_zr_c3.py"
    text = source.read_text(encoding="utf-8")
    for forbidden in ("ActionEvaluation", "evaluate_actions", "KeyedFadingField", "np.random", "default_rng"):
        assert forbidden not in text
