#!/usr/bin/env python3
"""Digest-bound physics overrides used only by the C3-S diagnostic runner."""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
from pathlib import Path
from typing import Any

import numpy as np


OVERRIDE_NAMES = ("none", "ablate_anchor")


class PhysicsOverrideError(RuntimeError):
    """A diagnostic physics override was malformed or could not be applied."""


@dataclass(frozen=True)
class PhysicsOverride:
    """Explicit override object passed to every environment in one unit.

    Provenance: Gemini/Opus fresh-context physics reviews, 2026-09-08.
    Forward links operate at fixed EIRP with ACM; segment-anchored gain
    inversion can manufacture a renewal premium.  ``ablate_anchor`` tests
    whether the coordinator advantage and its phase escalation collapse.
    """

    name: str

    def __post_init__(self) -> None:
        if self.name not in OVERRIDE_NAMES:
            raise PhysicsOverrideError(f"unknown physics override: {self.name}")

    def resolve_physics(
        self, environment: Any, decision: Any, actions: np.ndarray, rng: Any,
    ) -> dict[str, object]:
        """Call the canonical evaluator after applying the declared ablation.

        The canonical wanted-signal path already multiplies link power by the
        current ``field_now.transmit_gain``.  Refreshing every carried segment
        start gain to the action's current transmit gain therefore makes the
        recurrence return exactly p0 while retaining current-gain wanted
        signal evaluation.  Segment ages remain association ages; they are
        not reset by this physics-only ablation.
        """

        from mcrl.env.action_contract import NO_OP_ACTION, decode_action
        from mcrl.env.antenna import transmit_gain_linear
        from mcrl.env.step import Segment, StepEnvironment

        if self.name == "none":
            return StepEnvironment._resolve_physics(environment, decision, actions, rng)

        selected = np.asarray(actions)
        refreshed = list(environment._segments)
        for uid, action_value in enumerate(selected.tolist()):
            if int(action_value) == NO_OP_ACTION:
                continue
            slot, beam = decode_action(int(action_value))
            association = decision.slot_tables[uid].association(int(action_value))
            segment = refreshed[uid]
            if segment is None or not segment.continues(association):
                continue
            theta = float(decision.off_axis_deg[uid, slot, beam])
            gain = float(transmit_gain_linear(np.asarray([theta], dtype=np.float64))[0])
            if not np.isfinite(gain) or gain <= 0.0:
                continue
            refreshed[uid] = replace(segment, start_transmit_gain=gain)

        # Step zero represents a warm segment in the canonical path.  Zeroing
        # the pending age only for the evaluator call refreshes that opening
        # anchor too; the caller may already have captured the age receipt.
        original_pending = environment._pending_segment_age
        environment._segments = refreshed
        if int(environment._step_index) == 0 and original_pending is not None:
            environment._pending_segment_age = np.zeros_like(original_pending)
        try:
            result = StepEnvironment._resolve_physics(
                environment, decision, selected, rng
            )
        finally:
            environment._pending_segment_age = original_pending

        # A continuing segment remains continuing for association-age
        # instrumentation, but carries the just-used current gain as the next
        # call's anchor.  The canonical call above constructs this state.
        for uid, segment in enumerate(environment._segments):
            if segment is not None and not isinstance(segment, Segment):
                raise PhysicsOverrideError(f"user {uid} produced a malformed segment")
        return result

    def binding(self) -> dict[str, object]:
        path = Path(__file__).resolve()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return {
            "name": self.name,
            "implementation_path": str(path),
            "implementation_sha256": digest,
            "segment_start_power_w_hex": float(0.825).hex(),
            "wanted_transmit_gain": "CURRENT_TRANSMIT_GAIN",
            "scope": "DIAGNOSTIC_ONLY_NOT_A_SEALED_PHYSICS_CHANGE",
        }


class DiagnosticStepEnvironment:
    """Factory namespace for an explicit diagnostic StepEnvironment subclass."""

    @staticmethod
    def construct(driver: Any, *, physics_override: PhysicsOverride) -> Any:
        from mcrl.env.step import StepEnvironment

        class _OverrideStepEnvironment(StepEnvironment):
            def __init__(self, source_driver: Any, *, override: PhysicsOverride) -> None:
                super().__init__(source_driver)
                self.diagnostic_physics_override = override

            def _resolve_physics(
                self, decision: Any, actions: np.ndarray, rng: Any,
            ) -> dict[str, object]:
                return self.diagnostic_physics_override.resolve_physics(
                    self, decision, actions, rng
                )

        return _OverrideStepEnvironment(driver, override=physics_override)


def get_physics_override(name: str) -> PhysicsOverride:
    return PhysicsOverride(str(name))


__all__ = [
    "DiagnosticStepEnvironment", "OVERRIDE_NAMES", "PhysicsOverride",
    "PhysicsOverrideError", "get_physics_override",
]
