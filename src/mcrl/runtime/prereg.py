"""PREREG freezing and the data-blindness guard (W-13).

SDD §7.1 lists what must be frozen **before the first probe runs**, and adds
the reason::

    在觀察 P1 之後才選門檻即為洩漏,除非該映射事先凍結。

A document alone cannot enforce that, because the failure mode is a person
writing down a threshold after seeing the number it was supposed to bound.
So the freezer does three mechanical things a document cannot:

1. **It refuses to emit while anything is still open.**  ``N`` (Q-E) and the
   ``r3`` scale (Q-D) both carry machine-checkable freeze flags, and a PREREG
   naming a placeholder is worse than no PREREG — it looks decided.

2. **It commits to the hold-out seed without revealing it.**  §7.1 wants "一個
   不可存取的、獨立的留出產生器與已承諾的種子".  The freeze stores
   ``sha256(seed ‖ salt)``; using the hold-out later requires producing a seed
   that matches.  A seed chosen after seeing P1 will not.

3. **It hashes itself.**  Any later edit to a frozen record is detectable
   rather than arguable.

And the data-blindness guard encodes §4's r2 correction: an **untrained
network is not data-blind**.  Its argmax is decided by initialisation and
feature scale, so what a probe measures through one is the initialisation,
not the environment.  A reference policy here is therefore a declared rule
with a seed — never a model, trained or otherwise.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..errors import MCRLContractError

PREREG_SCHEMA: str = "mcrl-prereg-v1"

_CHECKPOINT_SUFFIXES = frozenset({".pt", ".pth", ".ckpt", ".safetensors"})


class PreregFreezeError(MCRLContractError):
    """The PREREG cannot be frozen, or a frozen one was violated."""


class DataBlindnessError(MCRLContractError):
    """A probe would consume something it must not see."""


# ---------------------------------------------------------------------------
# Open questions block the freeze
# ---------------------------------------------------------------------------


def open_questions() -> dict[str, bool]:
    """Which decisions are still open, read from the code that owns them."""
    from ..env.dwell import DWELL_N_IS_FROZEN
    from ..env.service import R3_SCALE_IS_FROZEN

    return {
        "Q-E dwell N": bool(DWELL_N_IS_FROZEN),
        "Q-D r3 calibration scale": bool(R3_SCALE_IS_FROZEN),
    }


def assert_nothing_is_still_open() -> None:
    """Refuse to freeze while a placeholder would be written in as decided."""
    unresolved = [name for name, frozen in open_questions().items() if not frozen]
    if unresolved:
        raise PreregFreezeError(
            "cannot freeze a PREREG while these are open: "
            + ", ".join(unresolved)
            + ". A PREREG naming a placeholder is worse than none — it reads "
            "as decided."
        )


# ---------------------------------------------------------------------------
# Hold-out seed commitment
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HoldoutCommitment:
    """A binding commitment to a hold-out seed that does not reveal it.

    The digest goes into the frozen record; the seed stays with whoever will
    run the hold-out.  Producing a *different* seed later cannot satisfy the
    digest, so "we picked the seed after seeing P1" stops being an
    unfalsifiable worry.
    """

    digest: str
    salt: str

    @classmethod
    def commit(cls, seed: int, *, salt: str | None = None) -> HoldoutCommitment:
        chosen_salt = secrets.token_hex(16) if salt is None else salt
        return cls(digest=_seed_digest(seed, chosen_salt), salt=chosen_salt)

    def verify(self, seed: int) -> None:
        """Raise unless ``seed`` is the one that was committed to."""
        if _seed_digest(seed, self.salt) != self.digest:
            raise PreregFreezeError(
                "hold-out seed does not match the committed digest; a seed "
                "chosen after seeing the data cannot be substituted here"
            )

    def as_dict(self) -> dict[str, str]:
        return {"digest": self.digest, "salt": self.salt}

    @classmethod
    def from_dict(cls, payload: Mapping[str, str]) -> HoldoutCommitment:
        return cls(digest=str(payload["digest"]), salt=str(payload["salt"]))


def _seed_digest(seed: int, salt: str) -> str:
    return hashlib.sha256(f"{int(seed)}:{salt}".encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Data blindness
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReferencePolicy:
    """A fixed rule with a seed.  **Never a model.**

    SDD §4 r2: an untrained network is not data-blind either, because its
    argmax follows from initialisation and feature scale — a probe run
    through one measures the initialisation.
    """

    name: str
    seed: int
    description: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("a reference policy needs a name")
        if hasattr(self.name, "state_dict") or hasattr(self.name, "forward"):
            raise DataBlindnessError("a reference policy may not be a model")

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "seed": self.seed, "description": self.description}


def assert_data_blind(
    *,
    policy: Any,
    inputs: Sequence[str | Path] = (),
) -> ReferencePolicy:
    """Refuse a probe that would consume a trained artefact.

    Two checks, matching the two ways §4 says a probe stops being blind:
    running the policy through a network at all, and reading anything a
    training run produced.
    """
    if not isinstance(policy, ReferencePolicy):
        raise DataBlindnessError(
            "probes must use a declared ReferencePolicy, not "
            f"{type(policy).__name__}. SDD §4 r2: an untrained network is not "
            "data-blind — its argmax is set by initialisation and feature "
            "scale, so the probe would measure the initialisation."
        )
    for entry in inputs:
        path = Path(entry)
        if path.suffix.lower() in _CHECKPOINT_SUFFIXES:
            raise DataBlindnessError(
                f"probe input {path.name!r} is a training checkpoint; probes "
                "must not consume training output"
            )
    return policy


# ---------------------------------------------------------------------------
# The frozen record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PreregRecord:
    """One frozen pre-registration, self-hashing."""

    sections: dict[str, Any]
    holdout: HoldoutCommitment
    schema: str = PREREG_SCHEMA
    digest: str = field(default="")

    def with_digest(self) -> PreregRecord:
        payload = self._hashable()
        return PreregRecord(
            sections=self.sections,
            holdout=self.holdout,
            schema=self.schema,
            digest=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        )

    def _hashable(self) -> str:
        return json.dumps(
            {
                "schema": self.schema,
                "sections": self.sections,
                "holdout": self.holdout.as_dict(),
            },
            sort_keys=True,
            ensure_ascii=False,
        )

    def verify(self) -> None:
        """Raise if the record has been edited since it was frozen."""
        expected = hashlib.sha256(self._hashable().encode("utf-8")).hexdigest()
        if not self.digest:
            raise PreregFreezeError("record carries no digest; it was never frozen")
        if expected != self.digest:
            raise PreregFreezeError(
                "PREREG digest does not match its contents; the record was "
                "edited after freezing"
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "digest": self.digest,
            "holdout": self.holdout.as_dict(),
            "sections": self.sections,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PreregRecord:
        if payload.get("schema") != PREREG_SCHEMA:
            raise PreregFreezeError(
                f"unknown PREREG schema {payload.get('schema')!r}"
            )
        return cls(
            sections=dict(payload["sections"]),
            holdout=HoldoutCommitment.from_dict(payload["holdout"]),
            schema=str(payload["schema"]),
            digest=str(payload.get("digest", "")),
        )


REQUIRED_SECTIONS: tuple[str, ...] = (
    "ephemeris",
    "split",
    "sampling",
    "d2",
    "antenna_and_link_budget",
    "dwell",
    "reward",
    "action_and_state",
    "training",
    "probe_grid",
    "thresholds",
    "stopping_rules",
    "reference_policy",
)
"""§7.1's minimum set, plus the parameter blocks the probes depend on."""


def freeze_prereg(
    sections: Mapping[str, Any],
    *,
    holdout_seed: int,
    salt: str | None = None,
    allow_open_questions: bool = False,
) -> PreregRecord:
    """Assemble and seal a PREREG record.

    ``allow_open_questions`` exists for tests only.  A real freeze with an
    open Q-D or Q-E writes a placeholder into a document that reads as
    decided, which is the thing the freeze flags exist to prevent.
    """
    if not allow_open_questions:
        assert_nothing_is_still_open()

    missing = [name for name in REQUIRED_SECTIONS if name not in sections]
    if missing:
        raise PreregFreezeError(
            f"PREREG is missing required sections: {missing}. §7.1 requires the "
            "complete probe grid, the thresholds or a deterministic selection "
            "mapping, and the stopping rules to be frozen in advance."
        )
    empty = [name for name in REQUIRED_SECTIONS if not sections[name]]
    if empty:
        raise PreregFreezeError(f"PREREG sections are present but empty: {empty}")

    return PreregRecord(
        sections=json.loads(json.dumps(dict(sections), sort_keys=True)),
        holdout=HoldoutCommitment.commit(holdout_seed, salt=salt),
    ).with_digest()


def write_prereg(path: str | Path, record: PreregRecord) -> Path:
    record.verify()
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(record.as_dict(), indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    return target


def read_prereg(path: str | Path) -> PreregRecord:
    record = PreregRecord.from_dict(
        json.loads(Path(path).read_text(encoding="utf-8"))
    )
    record.verify()
    return record


# ---------------------------------------------------------------------------
# Assembling the sections from the code that implements them
# ---------------------------------------------------------------------------


def build_prereg_sections(
    *,
    reference_policy: ReferencePolicy,
    probe_grid: Mapping[str, Any],
    thresholds: Mapping[str, Any],
    stopping_rules: Mapping[str, Any],
    ephemeris_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Read the frozen values back out of the modules that own them.

    Transcribing them by hand is how a PREREG ends up describing a system
    that no longer exists: the document and the code drift, and the document
    is the one people trust.  Everything derivable is derived; only the
    genuinely pre-registration-only pieces — the probe grid, the thresholds,
    the stopping rules, the reference policy — are supplied by the caller.
    """
    from ..env import antenna, cells, constants, link_budget
    from ..env.action_contract import (
        CONTRACT_STATE_DIM,
        NUM_ACTIONS,
        NUM_BEAM_SLOTS,
        NUM_SATELLITE_SLOTS,
        PHI1,
        PHI2,
        STATE_DIM,
    )
    from ..env.d2 import THRESH2_SWEEP_KM, D2Config
    from ..env.dwell import DWELL_N_CANDIDATES, DwellConfig
    from ..env.tle import MAX_MALFORMED_RECORD_FRACTION
    from ..runtime.bessel import BESSEL_SERIES_MAX_ABS_X
    from ..runtime.trainer_spec import TrainerConfig

    d2 = D2Config()
    dwell = DwellConfig()
    training = TrainerConfig()

    return {
        "ephemeris": dict(ephemeris_manifest),
        "split": dict(ephemeris_manifest.get("split", {})),
        "sampling": dict(ephemeris_manifest.get("sampling", {})),
        "d2": d2.as_dict() | {
            "thresh2_sweep_km": list(THRESH2_SWEEP_KM),
            "warmup_steps": d2.warmup_steps,
        },
        "antenna_and_link_budget": {
            "theta_3db_deg_full_hpbw": antenna.THETA_3DB_DEG,
            "half_angle_convention": "pattern receives theta_3dB / 2",
            "g0_linear": antenna.G0_LINEAR,
            "rx_gain_max_dbi": antenna.RX_GAIN_MAX_DBI,
            "rx_envelope": "32 - 25*log10(theta_deg), clipped to [-10, 35]",
            "carrier_hz": link_budget.CARRIER_FREQ_HZ,
            "bandwidth_hz": link_budget.BANDWIDTH_HZ,
            "beam_bandwidth_hz": link_budget.BEAM_BANDWIDTH_HZ,
            "system_temperature_k": link_budget.SYSTEM_TEMPERATURE_K,
            "atmosphere_model": "slab: chi * H_atm / sin(elevation)",
            "atmosphere_height_km": link_budget.ATMOSPHERE_HEIGHT_KM,
            "beam_power_max_w": link_budget.BEAM_POWER_MAX_W,
            "satellite_power_ceiling": None,
            "beam_count_ceiling": None,
            "bessel_series_max_abs_x": BESSEL_SERIES_MAX_ABS_X,
        },
        "dwell": {
            "steps": dwell.steps,
            "candidates": list(DWELL_N_CANDIDATES),
            "phase": "normalised to [0, 1), zero on a boundary",
            "service_window_basis": "pass duration at >= 10 deg elevation",
        },
        "reward": {
            "r1": "angle-aware per-link EE",
            "r2": f"identity-based handover, phi1={PHI1}, phi2={PHI2}",
            "r3": "count-based -U_{b_u}",
            "load_semantics": "eligible (post-m^e) drives r3, power and gamma_req",
            "calibration_enabled": training.reward_calibration_enabled,
        },
        "action_and_state": {
            "satellite_slots": NUM_SATELLITE_SLOTS,
            "beam_slots": NUM_BEAM_SLOTS,
            "actions": NUM_ACTIONS,
            "contract_state_dim": CONTRACT_STATE_DIM,
            "state_dim": STATE_DIM,
            "hidden_layers": list(training.hidden_layers),
            "activation": training.activation,
            "beam_activation": "z = 1{U > 0}, derived",
        },
        "training": {
            "discount_factor": training.discount_factor,
            "batch_size": training.batch_size,
            "episodes": training.episodes,
            "steps_per_episode": constants.STEPS_PER_EPISODE,
            "objective_weights": list(training.objective_weights),
            "epsilon_start": training.epsilon_start,
            "epsilon_end": training.epsilon_end,
            "epsilon_decay_episodes": training.epsilon_decay_episodes,
            "target_update_every_episodes": training.target_update_every_episodes,
            "replay_capacity": training.replay_capacity,
            "learning_rate": "CONTROLLED VARIABLE — not a default",
            "td_target": "MODQN eq. (16) vanilla, per-objective target max, done term",
        },
        "probe_grid": dict(probe_grid),
        "thresholds": dict(thresholds),
        "stopping_rules": dict(stopping_rules),
        "reference_policy": reference_policy.as_dict(),
        "data_integrity": {
            "max_malformed_tle_record_fraction": MAX_MALFORMED_RECORD_FRACTION,
            "cell_grid_radius_basis": "h * tan(theta_3dB / 2)",
            "cell_theta_3db_deg": cells.THETA_3DB_DEG,
        },
    }
