"""Branch-independent common-random fading for matched counterfactuals.

The canonical environment historically consumes one sequential generator in
sorted-satellite order.  That is reproducible for one trajectory, but two
counterfactual branches can expose different satellite sets and consequently
shift every later draw.  :class:`KeyedFadingField` removes that branch-size
dependence by assigning each ``(event, step, NORAD)`` path its own deterministic
substream.

The field does not change either fading distribution.  It only changes how
their random numbers are addressed.  The user axis remains vector-indexed, so
the same physical user and satellite receive the same underlying draw in two
matched branches even when the branches contain other, different satellites.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from .link_budget import rician_fading_gain, shadow_fading_db


KEYED_FADING_VERSION = "keyed-branch-independent-v1"
"""Versioned random-field contract used by the V0.3 C2 matched forks."""


@dataclass(frozen=True)
class KeyedFadingField:
    """Immutable keyed fading field shared by matched environment branches."""

    root_key: str
    version: str = KEYED_FADING_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.root_key, str) or not self.root_key:
            raise ValueError("root_key must be a non-empty string")
        if self.version != KEYED_FADING_VERSION:
            raise ValueError(
                f"unsupported keyed fading version {self.version!r}; "
                f"expected {KEYED_FADING_VERSION!r}"
            )

    @classmethod
    def from_components(
        cls,
        *components: str | int,
        version: str = KEYED_FADING_VERSION,
    ) -> "KeyedFadingField":
        """Derive a stable root from sealed, scalar source identifiers."""

        if not components:
            raise ValueError("at least one root component is required")
        if any(not isinstance(value, (str, int)) for value in components):
            raise TypeError("root components must be strings or integers")
        payload = json.dumps(
            [version, *components],
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return cls(root_key=hashlib.sha256(payload).hexdigest(), version=version)

    @property
    def root_digest(self) -> str:
        """Non-secret receipt identifier for the sealed field root."""

        return hashlib.sha256(self.root_key.encode("utf-8")).hexdigest()

    def receipt(self) -> dict[str, object]:
        """Return the minimum provenance needed to reproduce a field."""

        return {
            "mode": self.version,
            "version": self.version,
            "generator": "sha256-to-numpy-pcg64-v1",
            "root_digest": self.root_digest,
            "key_axes": ["event", "step_index", "norad_id"],
            "user_axis": "stable-vector-index",
        }

    def draw(
        self,
        *,
        event: str,
        step_index: int,
        norad_ids: Iterable[int],
        num_users: int,
        elevation_by_norad: Mapping[int, Sequence[float] | np.ndarray] | None,
        k_factor_db: float,
    ) -> tuple[dict[int, np.ndarray], dict[int, np.ndarray]]:
        """Draw the canonical Rician gain and shadow loss for keyed paths.

        Satellite order and the presence of unrelated satellites cannot alter
        a common path's values.  Elevation may differ between branches; in that
        case the underlying standard-normal shadow variate remains common while
        the canonical elevation-dependent sigma is applied branch locally.
        """

        if not isinstance(event, str) or not event:
            raise ValueError("event must be a non-empty string")
        if isinstance(step_index, bool) or not isinstance(step_index, int):
            raise TypeError("step_index must be an integer")
        if step_index < 0:
            raise ValueError("step_index must be non-negative")
        if isinstance(num_users, bool) or not isinstance(num_users, int):
            raise TypeError("num_users must be an integer")
        if num_users <= 0:
            raise ValueError("num_users must be positive")

        order = sorted({int(norad) for norad in norad_ids})
        rician: dict[int, np.ndarray] = {}
        shadow: dict[int, np.ndarray] = {}
        elevations = elevation_by_norad or {}
        for norad in order:
            rng = self._generator(event=event, step_index=step_index, norad=norad)
            rician[norad] = rician_fading_gain(
                rng,
                (num_users,),
                k_factor_db=k_factor_db,
            )
            elevation = np.asarray(
                elevations.get(norad, np.full(num_users, 10.0)),
                dtype=np.float64,
            )
            if elevation.shape != (num_users,):
                raise ValueError(
                    f"elevation for NORAD {norad} must have shape "
                    f"({num_users},), got {elevation.shape}"
                )
            shadow[norad] = shadow_fading_db(rng, elevation)
        return rician, shadow

    def _generator(
        self,
        *,
        event: str,
        step_index: int,
        norad: int,
    ) -> np.random.Generator:
        payload = json.dumps(
            [self.version, self.root_key, event, step_index, norad],
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("utf-8")
        seed = int.from_bytes(hashlib.sha256(payload).digest()[:16], "big")
        return np.random.Generator(np.random.PCG64(seed))
