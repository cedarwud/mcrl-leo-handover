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

    mcrl.env.step                       -> W-02 / W-03 (new environment)
    mcrl.runtime.angle_aware_ee         -> W-06 / W-15
    mcrl.runtime.popart_online          -> W-09 (χ / PopArt stays off, §8)
    mcrl.artifacts                      -> W-12 (checkpoint I/O)
    mcrl.runtime.trainer_config_validation -> W-09 / W-10

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

    from mcrl.env import step_types

    # -- W-02 / W-03: the environment ------------------------------------
    env_step = _module("mcrl.env.step")
    env_step.UserState = step_types.UserState
    env_step.ActionMask = step_types.ActionMask
    env_step.RewardComponents = step_types.RewardComponents
    env_step.StepResult = step_types.StepResult
    env_step.StepConfig = step_types.StepConfig

    class StepEnvironment:  # noqa: D401 - placeholder
        """Placeholder for the W-02/W-03 environment.

        Only a name for the trainer's type annotation.  Tests pass their own
        duck-typed doubles; instantiating this raises.
        """

        def __init__(self, *_args, **_kwargs) -> None:
            raise NotImplementedError(
                "StepEnvironment is owned by W-02/W-03 and does not exist yet."
            )

    env_step.StepEnvironment = StepEnvironment
    sys.modules["mcrl.env.step"] = env_step

    # -- W-06 / W-15: angle-aware EE (Bessel Miller routing lives here) ---
    aae = _module("mcrl.runtime.angle_aware_ee")
    aae.per_ue_energy_efficiency = _unavailable(
        "per_ue_energy_efficiency", "W-06/W-15"
    )
    sys.modules["mcrl.runtime.angle_aware_ee"] = aae

    # -- W-09: PopArt (SDD §8 keeps it off) ------------------------------
    popart = _module("mcrl.runtime.popart_online")

    class PopArtConfig:
        def __init__(self, *_args, **_kwargs) -> None:
            raise NotImplementedError(
                "PopArt is disabled by SDD §8 and was not ported."
            )

    class OnlinePopArt:
        def __init__(self, *_args, **_kwargs) -> None:
            raise NotImplementedError(
                "PopArt is disabled by SDD §8 and was not ported."
            )

    popart.PopArtConfig = PopArtConfig
    popart.OnlinePopArt = OnlinePopArt
    sys.modules["mcrl.runtime.popart_online"] = popart

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

    # -- W-09 / W-10: TrainerConfig validation ---------------------------
    # The 1,124-line source validator is mostly catfish / anti-collapse
    # rules that SDD §8 forbids, so it was deliberately not ported.  The
    # stand-in accepts any config; W-09/W-10 write the real one.
    validation = _module("mcrl.runtime.trainer_config_validation")

    def validate_trainer_config(_config) -> None:
        return None

    validation.validate_trainer_config = validate_trainer_config
    sys.modules["mcrl.runtime.trainer_config_validation"] = validation

    _INSTALLED = True
