"""CAPPENALTY: per-satellite active-beam cap as an OFF-BY-DEFAULT env flag.

**THIS IS A PHYSICS CHANGE.  Turning it on defines a different MDP.**
It changes who is served, U_{s,v}, the radiating set, interference, system
power and every reward.  Numbers from a capped environment are about a
different system from the one this project's rulings define.

Why this file is NOT under ``src/``: ruling 2026-08-22 §7.1-7.2 removed the
cap *and forbids any socket for it* in the live tree, and
``tests/test_ruling_no_beam_count_cap.py`` scans ``src/mcrl`` for one.  The
experiment needs the cap, the live tree must stay ruling-compliant, so the
flag lives here, in the experiment's own workspace, as a subclass.

Mechanism, copied from the sibling rather than chosen
(``modqn-paper-reproduction/src/modqn_paper_reproduction/env/
family_b_step.py``):

* ``:834-844`` -- per satellite, rank beams by ELIGIBLE (post-feasibility)
  load, descending, ties by lower cell id, keep the top ``k``;
* ``:1039`` -- only users on a kept beam are served;
* ``:851-853`` -- a darkened beam still reveals its true pre-admission
  demand, so ``demand_by_beam`` (observation block 4) is left untouched.

Post-execution darkening, NOT a decision mask: a mask would depend on the
joint action and break the per-user independent argmax (ruling reason 5).
Unit of the cap: the physical satellite (``norad_id``); the sibling's window
slot ``l`` was a shared satellite, here each user's slots may differ.

``beam_cap=None`` (the default) calls the unmodified parent method; nothing
is wrapped, nothing is copied.  ``test_beam_cap.py`` proves bit-identity.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

import mcrl.env.step as _step_module
from mcrl.env.service import ServiceResolution
from mcrl.env.step import StepEnvironment


@dataclass(frozen=True)
class CappedServiceResolution(ServiceResolution):
    """A resolution after cap darkening.  ``cap_darkened`` is kept separate
    from ``outage_infeasible`` so the physical outage rate stays readable."""

    cap_darkened: np.ndarray = field(default=None)  # (U,) bool
    cap_k: int = 0


def apply_cap(resolution: ServiceResolution, k: int) -> CappedServiceResolution:
    """Darken every beam beyond the top ``k`` per satellite (sibling rule)."""
    if int(k) < 1:
        raise ValueError("cap k must be >= 1")
    by_satellite: dict[int, list[tuple[int, int]]] = {}
    for (norad, cell), load in resolution.eligible_load_by_beam.items():
        by_satellite.setdefault(int(norad), []).append((int(cell), int(load)))
    kept: set[tuple[int, int]] = set()
    for norad, beams in by_satellite.items():
        order = sorted(beams, key=lambda b: (-b[1], b[0]))
        kept.update((norad, cell) for cell, _ in order[: int(k)])

    served = np.array(resolution.served, dtype=bool, copy=True)
    darkened = np.zeros(served.size, dtype=bool)
    for uid in np.flatnonzero(served):
        key = (int(resolution.serving_satellite[uid]),
               int(resolution.serving_cell[uid]))
        if key not in kept:
            darkened[uid] = True
    served &= ~darkened
    serving_cell = np.array(resolution.serving_cell, copy=True)
    serving_satellite = np.array(resolution.serving_satellite, copy=True)
    serving_cell[darkened] = -1
    serving_satellite[darkened] = -1
    eligible = {
        key: load
        for key, load in resolution.eligible_load_by_beam.items()
        if (int(key[0]), int(key[1])) in kept
    }
    return CappedServiceResolution(
        served=served,
        serving_cell=serving_cell,
        serving_satellite=serving_satellite,
        demand_by_beam=resolution.demand_by_beam,  # pre-admission, untouched
        eligible_load_by_beam=eligible,
        no_op_users=resolution.no_op_users,
        outage_infeasible=resolution.outage_infeasible,
        cap_darkened=darkened,
        cap_k=int(k),
    )


class CappedStepEnvironment(StepEnvironment):
    """``StepEnvironment`` with an optional per-satellite active-beam cap.

    ``beam_cap=None``: every method is the parent's, untouched.
    """

    def __init__(self, driver, *, beam_cap: int | None = None, **kwargs) -> None:
        super().__init__(driver, **kwargs)
        if beam_cap is not None and int(beam_cap) < 1:
            raise ValueError("beam_cap must be None or >= 1")
        self.beam_cap: int | None = None if beam_cap is None else int(beam_cap)

    def _resolve_physics(self, decision, actions, rng):
        if self.beam_cap is None:
            return super()._resolve_physics(decision, actions, rng)
        original = _step_module.resolve_service
        k = self.beam_cap

        def capped(actions_, tables_, infeasible_):
            return apply_cap(original(actions_, tables_, infeasible_), k)

        # step.py looks resolve_service up in its module globals at call time
        # (src/mcrl/env/step.py:117 import, :822 call).  Swap for this call
        # only, restore unconditionally.
        _step_module.resolve_service = capped
        try:
            return super()._resolve_physics(decision, actions, rng)
        finally:
            _step_module.resolve_service = original


def make_capped_training_environment(*, users: int = 100,
                                     beam_cap: int | None = None):
    """``make_training_environment`` with the step environment replaced by
    :class:`CappedStepEnvironment`.  Construction mirrors
    ``src/mcrl/runtime/training_pipeline.py:736-745`` line for line, using
    that module's own imported names."""
    import mcrl.runtime.training_pipeline as tp

    archive = tp.TleArchive(Path(tp.TLE_ROOT_DEFAULT).expanduser())
    driver = tp.ScenarioDriver(
        archive,
        tp.ScenarioConfig(mobility=tp.MobilityConfig(num_users=users)),
    )
    split = tp.BlockAlternatingSplit.for_archive(archive)
    sampler = tp.EpisodeStartSampler.for_archive(archive, split, tp.TRAIN)
    return tp.TrainerEnvironment(
        CappedStepEnvironment(driver, beam_cap=beam_cap), sampler
    )


def active_beams_per_satellite(resolution: ServiceResolution) -> dict[int, int]:
    counts: dict[int, int] = {}
    for norad, _cell in resolution.active_beams:
        counts[int(norad)] = counts.get(int(norad), 0) + 1
    return counts
