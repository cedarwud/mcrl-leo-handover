"""Focused non-outcome tests for the bounded C2 development support seam."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys

import numpy as np
import pytest


MODULE = Path(__file__).with_name("c2_activation_churn_dev_support.py")
spec = importlib.util.spec_from_file_location("c2_activation_churn_dev_support", MODULE)
support = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = support
spec.loader.exec_module(support)


def _table(*, duplicate: bool = False):
    from mcrl.env.action_contract import SlotTable

    norads = np.full(28, -1, dtype=np.int64)
    cells = np.full(28, -1, dtype=np.int64)
    mask = np.zeros(28, dtype=bool)
    norads[:3] = [100, 100, 100]
    cells[:3] = [1, 1 if duplicate else 2, 3]
    mask[:3] = True
    return SlotTable(norads, cells, mask)


def test_physical_id_mapping_is_unique_and_round_trips():
    table = _table()
    assert support._unique_valid_ids(table) == ((100, 1), (100, 2), (100, 3))
    assert support._physical_id_for_action(table, 1) == (100, 2)
    assert support._action_for_physical_id(table, (100, 2)) == 1


def test_duplicate_physical_id_fails_closed():
    with pytest.raises(RuntimeError, match="duplicate physical ID"):
        support._unique_valid_ids(_table(duplicate=True))


def test_short_remaining_horizon_returns_explicit_empty_development_support():
    result = support.scan_c2_development_support(
        object(),
        wrapped=object(),
        env_rng=np.random.default_rng(1),
        states=(),
        masks=(),
        observation=object(),
        steps_remaining=3,
    )
    assert result.support_actions_by_user == {}
    assert result.support_ids_by_user == {}
    assert result.receipts == ()
    assert result.claim_ceiling == "DEVELOPMENT_ONLY_CAPPED_PREOUTCOME_SUPPORT"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("steps_remaining", -1, "nonnegative"),
        ("max_focal_users", 0, "positive"),
        ("max_candidates_per_focal", 0, "positive"),
    ],
)
def test_scan_caps_and_horizon_require_exact_nonnegative_integers(field, value, message):
    kwargs = {
        "steps_remaining": 4,
        "max_focal_users": 1,
        "max_candidates_per_focal": 1,
    }
    kwargs[field] = value
    with pytest.raises(ValueError, match=message):
        support.scan_c2_development_support(
            object(),
            wrapped=object(),
            env_rng=np.random.default_rng(1),
            states=(),
            masks=(),
            observation=object(),
            **kwargs,
        )


@pytest.mark.parametrize(
    ("focal_user_ids", "message"),
    [
        ((), "must not be empty"),
        ((-1,), "nonnegative exact integers"),
        ((1.0,), "nonnegative exact integers"),
        ((1, 1), "must not contain duplicates"),
    ],
)
def test_targeted_focal_user_filter_fails_closed_before_environment_use(
    focal_user_ids, message
):
    with pytest.raises(ValueError, match=message):
        support.scan_c2_development_support(
            object(),
            wrapped=object(),
            env_rng=np.random.default_rng(1),
            states=(),
            masks=(),
            observation=object(),
            steps_remaining=4,
            focal_user_ids=focal_user_ids,
        )


def test_reentry_flag_distinguishes_episode_start_incumbent_and_unserved():
    from mcrl.env.action_contract import Association, UNSERVED

    branch = SimpleNamespace(
        wrapped=SimpleNamespace(
            environment=SimpleNamespace(
                _ledgers=[
                    SimpleNamespace(previous=None),
                    SimpleNamespace(previous=Association(100, 1)),
                    SimpleNamespace(previous=UNSERVED),
                ]
            )
        )
    )
    assert not support._reentry_before_step(branch, 0)
    assert not support._reentry_before_step(branch, 1)
    assert support._reentry_before_step(branch, 2)
