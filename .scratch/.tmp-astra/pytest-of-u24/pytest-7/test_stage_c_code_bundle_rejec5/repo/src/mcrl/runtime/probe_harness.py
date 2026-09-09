"""Shared machinery for the probes: the gate, the streams, the drive loop.

Four probes (P2, P4, P6, P7) are ablation-shaped and every one of them
would carry the same defect if it drew its sampling randomness from the
stream it sweeps.  So the separation lives **here, once**, rather than
being re-established in each module — the controller's warning about
converging the scripts was precisely that "从脚本搬进 probe" is where three
generators quietly become one.

The gate is here for the same reason: every probe must verify the frozen
record and find its own entry in the grid, and a probe that could run
before the freeze would make "the rule was committed in advance" an
honour system rather than a check.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Iterator, Sequence

import numpy as np

from ..env.reference_policy import ReferencePolicyRunner
from ..env.step import StepEnvironment, StepObservation, StepOutcome
from ..errors import MCRLContractError
from .prereg import PreregRecord, assert_data_blind


@dataclass(frozen=True)
class ProbeStreams:
    """The three independent generators every probe runs on.

    ``env`` drives the fading and (through a spawned child) the warm-start
    ages; ``mobility`` places and moves the users; ``action`` is the
    policy's own draw.  Keeping them apart is what makes an ablation an
    ablation: with one generator, changing the swept quantity advances the
    stream and silently re-draws the other two, so the measurement is of
    "the swept thing **and** a different sample" — numbers that look
    reasonable and are attributed wrongly.

    :meth:`spawn` derives all three from one integer so a probe run is
    reproducible from a single seed without ever sharing a stream.
    """

    env: np.random.Generator
    mobility: np.random.Generator
    action: np.random.Generator

    @classmethod
    def spawn(cls, seed: int) -> ProbeStreams:
        children = np.random.SeedSequence(seed).spawn(3)
        return cls(*(np.random.default_rng(child) for child in children))


def assert_probe_is_frozen(
    prereg: PreregRecord,
    probe_id: str,
    policy: ReferencePolicyRunner,
    *,
    requires_mapping: str | None = None,
) -> dict:
    """Verify the record, the grid entry, and the policy's data-blindness.

    ``requires_mapping`` names a selection mapping the probe *closes*; if
    given, it must already be in the frozen record.  A probe that closes a
    question without its rule frozen first is the §7.1 leak with extra
    steps.
    """
    prereg.verify()
    assert_data_blind(policy=policy.declaration)
    grid = prereg.sections.get("probe_grid", {})
    if not grid.get(probe_id):
        raise MCRLContractError(
            f"the frozen PREREG has no {probe_id} entry in its probe grid; "
            "§7.1 requires the complete grid to be frozen before the first "
            "probe"
        )
    if requires_mapping is not None:
        mapping = prereg.sections.get("selection_mappings", {}).get(
            requires_mapping
        )
        if not mapping:
            raise MCRLContractError(
                f"{probe_id} closes {requires_mapping!r}, so its selection "
                "mapping must be in the frozen record before it runs"
            )
    return dict(grid[probe_id])


def drive(
    environment: StepEnvironment,
    policy: ReferencePolicyRunner,
    epochs: Sequence[dt.datetime],
    streams: ProbeStreams,
) -> Iterator[tuple[StepObservation, np.ndarray, StepOutcome]]:
    """Yield ``(observation, actions, outcome)`` for every decision step.

    The observation is the one the actions were **chosen against**, not the
    one that follows — a probe correlating a choice with the state after it
    would be reading the future.
    """
    if not epochs:
        raise MCRLContractError("a probe needs at least one epoch")
    for epoch in epochs:
        observation = environment.reset(
            epoch, streams.env, mobility_rng=streams.mobility
        )
        policy.reset()
        while True:
            actions = policy.act(observation.candidates, streams.action)
            outcome = environment.step(actions, streams.env)
            yield observation, actions, outcome
            observation = outcome.observation
            if outcome.done:
                break


def quantiles(values: np.ndarray) -> dict[str, float]:
    """The five-number summary every probe reports its distributions with."""
    values = np.asarray(values, dtype=np.float64)
    if values.size == 0:
        return {"count": 0.0}
    return {
        "count": float(values.size),
        "min": float(values.min()),
        "p05": float(np.percentile(values, 5)),
        "p50": float(np.percentile(values, 50)),
        "p95": float(np.percentile(values, 95)),
        "max": float(values.max()),
        "mean": float(values.mean()),
    }
