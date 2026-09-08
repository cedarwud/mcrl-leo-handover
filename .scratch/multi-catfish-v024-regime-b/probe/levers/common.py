"""Shared types and fail-closed helpers for declared physics levers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping


TODO_CONTROLLER_DECLARE = "TODO_CONTROLLER_DECLARE"  # Provenance: task instruction for unspecified or VERIFY_SOURCE declarations.


class LeverError(RuntimeError):
    """A lever input, declared domain, or detached operation is invalid."""


class RegenerationRequired(LeverError):
    """The selected lever cannot consume old physical outcomes."""


@dataclass(frozen=True)
class LeverDefinition:
    """Registry metadata plus explicit detached call seams."""

    lever_id: str
    identity: str
    module_name: str
    priority: int
    r2_tape_policy: str
    regeneration_required: bool
    controller_todos: tuple[str, ...]
    constants: tuple[Mapping[str, object], ...]
    apply_profile: Callable[..., Mapping[str, object]]
    regeneration_hook: Callable[..., object]

    @property
    def execution_ready(self) -> bool:
        return not self.controller_todos

    def estimate_status(self) -> str:
        if self.regeneration_required:
            return "REGEN_REQUIRED"
        if self.controller_todos:
            return TODO_CONTROLLER_DECLARE
        return "READY"


def constant(name: str, value: object, provenance: str) -> Mapping[str, object]:
    """Create one JSON-safe constant-table row with mandatory provenance."""

    if not name or not provenance:
        raise LeverError("every constant requires a name and provenance")
    return {"name": name, "value": value, "provenance": provenance}


def invoke_regeneration_adapter(
    adapter: Callable[..., object] | None, *, lever_id: str, identity: str,
    evaluate_actions: Callable[..., object], context: Mapping[str, object],
    extra_bindings: Mapping[str, object] | None = None,
) -> object:
    """Invoke one heavy replay adapter with the immutable matched-field rules."""

    if adapter is None:
        raise RegenerationRequired(f"{lever_id} regeneration adapter is required; no tape was synthesized")
    return adapter(
        lever_id=lever_id,
        identity=identity,
        evaluate_actions=evaluate_actions,
        keyed_fading_event="physics",
        continuation="ORIGINAL_PHYSICS_REFERENCE_ONLY",
        **dict(extra_bindings or {}),
        **dict(context),
    )
