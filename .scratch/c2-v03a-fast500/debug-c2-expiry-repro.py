"""Seconds-long red repro for the real C2 live-option expiry seam.

This stays outside the shared implementation.  Forecast uses a detached clone
whose incumbent remains available; the live opening step then removes that
physical key from the focal user's slot table.  The runner records the expiry
but still sends the nonterminal payload prefix to ``close_temporal_option``.
"""

from __future__ import annotations

import copy
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".scratch" / "c2-v03"))
sys.path.insert(0, str(ROOT / ".scratch" / "smc-er-short-ep"))
sys.path.insert(0, str(ROOT / "src"))

import c2_temporal_fork_option_runner as option_runner  # noqa: E402
import c2_temporal_fork_trainer_backend as backend  # noqa: E402
import test_c2_temporal_fork_trainer_backend as fixture  # noqa: E402


class LiveExpiryWrapped(fixture._Wrapped):
    """Keep forecast support but expire the incumbent after live offset 0."""

    def __init__(self) -> None:
        super().__init__()
        self._live_mode = True

    def __deepcopy__(self, memo):
        clone = type(self).__new__(type(self))
        memo[id(self)] = clone
        clone.__dict__ = copy.deepcopy(self.__dict__, memo)
        clone._live_mode = False
        return clone

    def step(self, actions: np.ndarray, env_rng: np.random.Generator):
        result = super().step(actions, env_rng)
        if self._live_mode and self._offset == 1:
            # The incumbent (1,3) disappears from the live successor table;
            # the detached forecast clone deliberately does not take this path.
            expired = (fixture._Table({11: (1, 11)}), self._tables[1])
            self._tables = expired
            successor = fixture._Observation(
                self._offset,
                self._observation.state_matrix,
                expired,
            )
            self._observation = successor
            self._last_outcome.observation = successor
            result.user_states = [
                np.array(row, copy=True) for row in successor.state_matrix
            ]
            result.action_masks = [
                fixture.SimpleNamespace(mask=np.array(table.mask, copy=True))
                for table in successor.candidates.slot_tables
            ]
        return result


def main() -> None:
    wrapped = LiveExpiryWrapped()
    trainer = fixture._Trainer()
    service = fixture._construct_backend(wrapped, trainer)
    prepared = service.prepare_incumbent_hold(focal_user=0)
    build = prepared.run_forecast()
    assert build.certificate.passed, build.certificate.failures

    compose_calls: list[tuple[int, str]] = []
    original_compose = backend._compose_candidate_actions

    def trace_compose(*args, **kwargs):
        try:
            return original_compose(*args, **kwargs)
        except backend.C2ForecastSupportRejection as error:
            compose_calls.append((int(kwargs["offset"]), error.reason))
            raise

    close_calls: list[int] = []
    original_close = option_runner.forecast.close_committed_option

    def trace_close(*args, **kwargs):
        close_calls.append(len(kwargs["committed_steps"]))
        return original_close(*args, **kwargs)

    backend._compose_candidate_actions = trace_compose
    option_runner.forecast.close_committed_option = trace_close
    try:
        option_runner.commit_prepared_option(
            prepared,
            opening_behavior_probability=1.0,
            discount_factor=0.9,
            block_id=0,
            selection_receipt_sha256="d" * 64,
        )
    except Exception as error:  # red-capable assertion below
        print(f"exception={type(error).__name__}: {error}")
        print(f"expiry_calls={compose_calls}")
        print(f"closure_prefix_lengths={close_calls}")
        assert type(error).__name__ == "C2ContractError"
        assert str(error) == (
            "a nonterminal C2 prefix is a runner-integrity error, not zero dose"
        )
        assert compose_calls == [(1, "focal_hold_expired")]
        assert close_calls == [1]
    else:  # pragma: no cover - the bug must remain red until fixed
        raise AssertionError("expiry seam unexpectedly committed without error")


if __name__ == "__main__":
    main()
