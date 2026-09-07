"""W-182 -- V0.23 immutable LC-SRS C3View contract."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from mcrl.runtime.ee_axis_lcsrs_c3_state import (
    C3View,
    LCSRS_ACTION_CONTEXT_DIM,
    LCSRS_ACTION_CONTEXT_FIELDS,
    LCSRS_ACTION_DIM,
    LCSRSC3StateError,
    LCSRS_ORDINARY_TOKEN_FIELDS,
    LCSRS_PAIR_TOKEN_FIELDS,
    LCSRS_TOKEN_DIM,
    assemble_c3_view,
)


def _arrays(users: int = 2) -> dict[str, np.ndarray]:
    context = np.zeros((users, LCSRS_ACTION_DIM, LCSRS_ACTION_CONTEXT_DIM), dtype=np.float32)
    tokens = np.zeros((users, LCSRS_ACTION_DIM, users + 1, LCSRS_TOKEN_DIM), dtype=np.float32)
    action_mask = np.zeros((users, LCSRS_ACTION_DIM), dtype=np.bool_)
    action_mask[:, :2] = True
    token_mask = np.zeros((users, LCSRS_ACTION_DIM, users + 1), dtype=np.bool_)
    token_mask[:, :, users] = action_mask
    tokens[:, :, users, 1][action_mask] = 1.0  # pair type [0, 1]
    # One ordinary relation token demonstrates its independently typed slot.
    token_mask[0, 1, 1] = True
    tokens[0, 1, 1, 0] = 1.0
    return {
        "action_context": context,
        "tokens": tokens,
        "token_mask": token_mask,
        "action_mask": action_mask,
        "reference_actions": np.zeros(users, dtype=np.int64),
    }


def test_shape_hash_digest_and_immutability_are_copy_stable() -> None:
    values = _arrays()
    first = assemble_c3_view(**values)
    second = assemble_c3_view(**values)
    assert first.action_context.shape == (2, 28, 29)
    assert first.tokens.shape == (2, 28, 3, 38)
    assert first.token_mask.shape == (2, 28, 3)
    assert first.action_mask.shape == (2, 28)
    assert first.reference_actions.shape == (2,)
    assert len(LCSRS_ACTION_CONTEXT_FIELDS) == 29
    assert len(LCSRS_ORDINARY_TOKEN_FIELDS) == 38
    assert len(LCSRS_PAIR_TOKEN_FIELDS) == 38
    assert len(set(LCSRS_ACTION_CONTEXT_FIELDS)) == 29
    assert len(set(LCSRS_ORDINARY_TOKEN_FIELDS)) == 38
    assert len(set(LCSRS_PAIR_TOKEN_FIELDS)) == 38
    assert first.content_digest == second.content_digest
    assert len(first.schema_sha256) == len(first.config_sha256) == 64
    values["tokens"][0, 1, 1, 9] = 99.0
    assert first.tokens[0, 1, 1, 9] == 0.0
    for field in ("action_context", "tokens", "token_mask", "action_mask", "reference_actions"):
        assert not getattr(first, field).flags.writeable
    with pytest.raises(ValueError):
        first.tokens[0, 1, 1, 9] = 1.0
    first.verify()


def test_illegal_zero_masked_zero_and_pair_sentinels_fail_closed() -> None:
    values = _arrays()
    values["action_context"][0, 4, 0] = 1.0
    with pytest.raises(LCSRSC3StateError, match="illegal"):
        assemble_c3_view(**values)

    values = _arrays()
    values["tokens"][0, 1, 0, 4] = 1.0
    with pytest.raises(LCSRSC3StateError, match="masked"):
        assemble_c3_view(**values)

    values = _arrays()
    # No-partner means type + status (0,0,0) and no other pair fields.
    values["tokens"][0, 1, 2, 8] = 1.0
    with pytest.raises(LCSRSC3StateError, match="sentinel"):
        assemble_c3_view(**values)

    values = _arrays()
    # An occupancy-two unsupported sentinel is (1,0,0), with its tail zero.
    values["tokens"][0, 1, 2, 2] = 1.0
    view = assemble_c3_view(**values)
    assert view.tokens[0, 1, 2, 2:5].tolist() == [1.0, 0.0, 0.0]


def test_reference_and_pair_slot_are_exact_contract_requirements() -> None:
    values = _arrays()
    values["reference_actions"][0] = 4
    with pytest.raises(LCSRSC3StateError, match="reference"):
        assemble_c3_view(**values)

    values = _arrays()
    values["token_mask"][0, 1, 2] = False
    values["tokens"][0, 1, 2, :] = 0.0
    with pytest.raises(LCSRSC3StateError, match="exactly one pair"):
        assemble_c3_view(**values)


def test_tampered_hash_or_digest_is_rejected_and_no_outcome_argument_exists() -> None:
    view = C3View(**_arrays())
    with pytest.raises(LCSRSC3StateError, match="schema hash"):
        replace(view, schema_sha256="0" * 64).verify()
    with pytest.raises(LCSRSC3StateError, match="config hash"):
        replace(view, config_sha256="0" * 64).verify()
    with pytest.raises(LCSRSC3StateError, match="content digest"):
        replace(view, content_digest="0" * 64).verify()
    with pytest.raises(TypeError, match="outcome"):
        assemble_c3_view(**_arrays(), outcome_bits=np.zeros(2))  # type: ignore[call-arg]
