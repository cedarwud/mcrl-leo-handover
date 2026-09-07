"""Fixed reference policies for the data-blind probes (SDD §4, W-11).

§4: "全部 probe 只用固定參考策略,不得消費任何訓練輸出", plus the r2
correction that an **untrained network is not data-blind either** — its
argmax follows from initialisation and feature scale, so a probe run
through one measures the initialisation rather than the environment.

Every policy here is a rule over the candidate table plus a seed.  None
looks at a Q value, a reward, or a checkpoint.  All three respect the mask
and emit ``NO_OP_ACTION`` on an empty one, so a probe measures the same
starvation a trained policy would meet rather than a fallback the
environment never offers (§4A.5a).

State lives on the runner, never in a module global: ``stay-if-possible``
has to remember an association across a step, and a policy that cached it
invisibly would be hard to tell from one that compares indices — which is
the very thing §4A.4 forbids.
"""

from __future__ import annotations

import numpy as np

from ..errors import MCRLContractError
from ..runtime.prereg import ReferencePolicy
from .action_contract import NO_OP_ACTION, NUM_BEAM_SLOTS, NUM_SATELLITE_SLOTS
from .candidates import StepCandidates

NEAREST_ELIGIBLE = "nearest-eligible"
"""Slot 0 (highest D2 margin), own cell.  The 'do the obvious thing' arm."""

RANDOM_MASKED = "random-masked"
"""Uniform over the valid actions.  The maximally uninformed arm."""

STAY_IF_POSSIBLE = "stay-if-possible"
"""Hold the current association while it stays valid; else nearest-eligible.

The arm that makes a measured handover rate a property of the **geometry**
rather than of a policy that churns for its own reasons — which is what
probe P1 is trying to measure.
"""

REFERENCE_POLICY_NAMES: tuple[str, ...] = (
    NEAREST_ELIGIBLE,
    RANDOM_MASKED,
    STAY_IF_POSSIBLE,
)

_DESCRIPTIONS = {
    NEAREST_ELIGIBLE: "best D2 margin, own cell, first valid in slot order",
    RANDOM_MASKED: "uniform over the valid actions",
    STAY_IF_POSSIBLE: "hold the previous association while it stays valid",
}

_SLOT_ORDER: tuple[int, ...] = tuple(
    NUM_BEAM_SLOTS * slot + beam
    for slot in range(NUM_SATELLITE_SLOTS)
    for beam in range(NUM_BEAM_SLOTS)
)
"""Satellite-major, beam-minor — the declared preference order (§4A.1)."""


class ReferencePolicyRunner:
    """A declared, data-blind policy with its own state."""

    def __init__(self, name: str, seed: int) -> None:
        if name not in REFERENCE_POLICY_NAMES:
            raise MCRLContractError(
                f"unknown reference policy {name!r}; "
                f"choose from {list(REFERENCE_POLICY_NAMES)}"
            )
        self.declaration = ReferencePolicy(
            name=name, seed=int(seed), description=_DESCRIPTIONS[name]
        )
        self._held: dict[int, tuple[int, int]] = {}

    @property
    def name(self) -> str:
        return self.declaration.name

    @property
    def seed(self) -> int:
        return self.declaration.seed

    def reset(self) -> None:
        """Clear the held associations.  Called at every episode boundary."""
        self._held.clear()

    def act(
        self, candidates: StepCandidates, rng: np.random.Generator
    ) -> np.ndarray:
        """Choose one action per user, or ``NO_OP_ACTION`` on an empty mask."""
        if self.name == NEAREST_ELIGIBLE:
            actions = self._nearest_eligible(candidates)
        elif self.name == RANDOM_MASKED:
            actions = self._random_masked(candidates, rng)
        else:
            actions = self._stay_if_possible(candidates)
        self._remember(candidates, actions)
        return actions

    # -- the three rules --------------------------------------------------

    def _nearest_eligible(self, candidates: StepCandidates) -> np.ndarray:
        actions = np.full(
            len(candidates.slot_tables), NO_OP_ACTION, dtype=np.int32
        )
        for uid, table in enumerate(candidates.slot_tables):
            for action in _SLOT_ORDER:
                if table.mask[action]:
                    actions[uid] = action
                    break
        return actions

    def _random_masked(
        self, candidates: StepCandidates, rng: np.random.Generator
    ) -> np.ndarray:
        actions = np.full(
            len(candidates.slot_tables), NO_OP_ACTION, dtype=np.int32
        )
        for uid, table in enumerate(candidates.slot_tables):
            valid = np.flatnonzero(table.mask)
            if valid.size:
                actions[uid] = int(rng.choice(valid))
        return actions

    def _stay_if_possible(self, candidates: StepCandidates) -> np.ndarray:
        """Reproduce the held ``(norad_id, cell_id)``, not the held index.

        Comparing indices would make this policy churn whenever the slot
        ordering shifted — the false-positive handover of §4A.4 — and that
        would corrupt exactly the event rate P1 measures.
        """
        actions = self._nearest_eligible(candidates)
        for uid, table in enumerate(candidates.slot_tables):
            held = self._held.get(uid)
            if held is None or not table.num_valid:
                continue
            norad, cell = held
            same = np.flatnonzero(
                table.mask & (table.norad_ids == norad) & (table.cell_ids == cell)
            )
            if same.size:
                actions[uid] = int(same[0])
        return actions

    # -- state -------------------------------------------------------------

    def _remember(self, candidates: StepCandidates, actions: np.ndarray) -> None:
        for uid, table in enumerate(candidates.slot_tables):
            action = int(actions[uid])
            if action == NO_OP_ACTION or not table.mask[action]:
                # An unserved step drops the hold, so the next served step is
                # a genuine re-entry rather than a silent continuation.
                self._held.pop(uid, None)
                continue
            self._held[uid] = (
                int(table.norad_ids[action]),
                int(table.cell_ids[action]),
            )


def build_reference_policy(name: str, seed: int) -> ReferencePolicyRunner:
    """Construct a runner; its ``declaration`` is what the PREREG freezes."""
    return ReferencePolicyRunner(name, seed)
