"""Test-only stand-ins for modules W-01 did not port yet.

``src/mcrl/algorithms/modqn.py`` was ported byte-for-byte in W-01 and still
imports four siblings that this repo does not have, plus one lazy import
inside ``TrainerConfig.__post_init__``.  The tree is therefore not importable
(``docs/PROVENANCE.md``, "尚未處理").  W-16 must be testable *now*, so the
shim below installs the missing modules into ``sys.modules`` before
``mcrl.algorithms.modqn`` is first imported.

Every entry is temporary and names its owning work item.  **When that work
item lands, delete the entry.**  A shim entry that outlives its owner is a
bug: it means live code is running against a stand-in.

    mcrl.artifacts                      -> W-12 (checkpoint I/O)

RETIRED
    mcrl.runtime.popart_online          -> W-09 removed the import entirely
    mcrl.env.step                       -> W-10 repointed the container types
                                           to env.step_types; StepEnvironment
                                           is now a TYPE_CHECKING-only import
    mcrl.runtime.angle_aware_ee         -> W-06 ported the per-UE eta closure
                                           into runtime/energy_efficiency.py
    mcrl.runtime.trainer_config_validation -> a real validator now exists; the
                                           permissive stand-in was MASKING it

Design rule: a stand-in either re-exports the canonical type from
``mcrl.env.step_types`` or **raises**.  It never invents behaviour, so no
test can accidentally pass against fabricated physics.
"""

from __future__ import annotations

import sys
import types

_INSTALLED = False


def _module(name: str) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__dict__["__mcrl_test_shim__"] = True
    return module


def _unavailable(what: str, owner: str):
    def _raise(*_args, **_kwargs):
        raise NotImplementedError(
            f"{what} is not implemented in this repo yet (owner: {owner}). "
            "The W-16 test shim deliberately refuses to fake it."
        )

    return _raise


def install() -> None:
    """Install the stand-ins.  Idempotent."""
    global _INSTALLED
    if _INSTALLED:
        return

    # -- W-12: checkpoint artifacts --------------------------------------
    artifacts = _module("mcrl.artifacts")

    class _CheckpointPlaceholder:
        def __init__(self, *_args, **_kwargs) -> None:
            raise NotImplementedError(
                "Checkpoint payloads are owned by W-12 and do not exist yet."
            )

    artifacts.CheckpointPayloadV1 = _CheckpointPlaceholder
    artifacts.CheckpointRuleV1 = _CheckpointPlaceholder
    artifacts.read_checkpoint = _unavailable("read_checkpoint", "W-12")
    artifacts.write_checkpoint = _unavailable("write_checkpoint", "W-12")
    sys.modules["mcrl.artifacts"] = artifacts

    _INSTALLED = True
