"""Replay-buffer implementation for the runtime seam."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
from numpy.random import Generator


class ReplayBuffer:
    """Fixed-capacity FIFO experience replay (ASSUME-MODQN-REP-006)."""

    _STATE_FORMAT_VERSION = 1

    def __init__(self, capacity: int) -> None:
        if isinstance(capacity, bool) or not isinstance(capacity, int):
            raise TypeError(f"capacity must be an integer, got {capacity!r}")
        if capacity < 1:
            raise ValueError(f"capacity must be positive, got {capacity}")
        self._capacity = capacity
        self._buf: deque[tuple[Any, ...]] = deque(maxlen=capacity)

    @property
    def capacity(self) -> int:
        return self._capacity

    def push(
        self,
        state: np.ndarray,
        action: int,
        reward_3: np.ndarray,
        next_state: np.ndarray,
        mask: np.ndarray,
        next_mask: np.ndarray,
        done: bool,
    ) -> None:
        self._buf.append((state, action, reward_3, next_state, mask, next_mask, done))

    def sample(
        self, batch_size: int, rng: Generator
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        indices = rng.choice(len(self._buf), size=batch_size, replace=False)
        batch = [self._buf[i] for i in indices]

        states = np.array([b[0] for b in batch], dtype=np.float32)
        actions = np.array([b[1] for b in batch], dtype=np.int64)
        rewards = np.array([b[2] for b in batch], dtype=np.float32)
        next_states = np.array([b[3] for b in batch], dtype=np.float32)
        masks = np.array([b[4] for b in batch])
        next_masks = np.array([b[5] for b in batch])
        dones = np.array([b[6] for b in batch], dtype=np.float32)

        return states, actions, rewards, next_states, masks, next_masks, dones

    def __len__(self) -> int:
        return len(self._buf)

    def state_dict(self) -> dict[str, Any]:
        """Return an independent, FIFO-preserving snapshot of the buffer.

        The trainer's episode-boundary resume state must include replay, not
        just network weights.  Copies are deliberate: a caller may continue
        training or mutate the original arrays after taking a snapshot
        without changing the snapshot that will be restored in another
        process.
        """

        return {
            "format_version": self._STATE_FORMAT_VERSION,
            "capacity": self._capacity,
            "buffer": [self._copy_transition(item) for item in self._buf],
        }

    def load_state_dict(self, state: Mapping[str, Any]) -> None:
        """Restore a validated FIFO snapshot into this buffer.

        A capacity mismatch is rejected instead of silently truncating a
        resumed run.  The transition schema is checked before replacing the
        current deque, so malformed input cannot leave a half-restored
        buffer.
        """

        if not isinstance(state, Mapping):
            raise TypeError("replay state must be a mapping")
        version = state.get("format_version")
        if version != self._STATE_FORMAT_VERSION:
            raise ValueError(
                "unsupported replay state format_version "
                f"{version!r}; expected {self._STATE_FORMAT_VERSION}"
            )
        capacity = state.get("capacity")
        if capacity != self._capacity:
            raise ValueError(
                "replay state capacity "
                f"{capacity!r} does not match buffer capacity {self._capacity}"
            )
        raw_buffer = state.get("buffer")
        if isinstance(raw_buffer, (str, bytes)) or not isinstance(
            raw_buffer, Sequence
        ):
            raise TypeError("replay state buffer must be a sequence")
        if len(raw_buffer) > self._capacity:
            raise ValueError(
                "replay state buffer length "
                f"{len(raw_buffer)} exceeds capacity {self._capacity}"
            )

        restored = [self._copy_transition(item) for item in raw_buffer]
        self._buf = deque(restored, maxlen=self._capacity)

    @staticmethod
    def _copy_transition(item: Any) -> tuple[Any, ...]:
        """Validate and deep-copy one seven-field replay transition."""

        if isinstance(item, (str, bytes)) or not isinstance(item, Sequence):
            raise TypeError("each replay transition must be a seven-field sequence")
        if len(item) != 7:
            raise ValueError(
                "each replay transition must contain state, action, reward_3, "
                "next_state, mask, next_mask, and done"
            )

        state, action, reward_3, next_state, mask, next_mask, done = item
        for name, value in (
            ("state", state),
            ("reward_3", reward_3),
            ("next_state", next_state),
            ("mask", mask),
            ("next_mask", next_mask),
        ):
            if not isinstance(value, np.ndarray):
                raise TypeError(
                    f"replay transition {name} must be a numpy array, "
                    f"got {type(value).__name__}"
                )
        if isinstance(action, bool) or not isinstance(action, (int, np.integer)):
            raise TypeError(
                f"replay transition action must be an integer, got {action!r}"
            )
        if not isinstance(done, (bool, np.bool_)):
            raise TypeError(
                f"replay transition done must be boolean, got {done!r}"
            )

        return (
            np.array(state, copy=True),
            int(action),
            np.array(reward_3, copy=True),
            np.array(next_state, copy=True),
            np.array(mask, copy=True),
            np.array(next_mask, copy=True),
            bool(done),
        )
