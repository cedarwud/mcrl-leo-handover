#!/usr/bin/env python3
"""Run the V0.24 finite-demand regime-map probe.

Reference-carrier definitions (all mask-legal, no learner/checkpoint input):

* ``nearest-eligible``: first valid action in satellite-major/beam-minor order.
* ``stay-if-possible``: retain the prior physical ``(NORAD, cell)`` when it
  remains legal, otherwise use ``nearest-eligible``.
* ``random-masked``: uniform draw from the valid mask in increasing user
  order, using a carrier-specific RNG derived from the declared world.

The physical environment always runs once in G0.  Its complete capacity,
service, beam, and energy profiles are immutable raw tape.  Grid tapes contain
only deterministic demand-capped metrics and bind the one raw-tape digest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import sys
import tempfile
from typing import Any, Callable, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
E1_DIR = REPO / ".scratch" / "multi-catfish-v023-c3-existence-e1"
for _path in (HERE, E1_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import e1_estimands  # noqa: E402
import run_v023_c3_existence_e1 as e1_runner  # noqa: E402

from mcrl.env.constants import DECISION_STEP_S  # noqa: E402
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.env.reference_policy import (  # noqa: E402
    NEAREST_ELIGIBLE,
    RANDOM_MASKED,
    STAY_IF_POSSIBLE,
    build_reference_policy,
)


SCHEMA = "multi-catfish-mcrl-v024-regime-b-probe-v1"
CLAIM_CEILING = "TRAIN_DEVELOPMENT_V024_REGIME_PROBE_NO_LEARNER_NO_EFFICACY_NO_TEST"
RAW_TAPE_SCHEMA = f"{SCHEMA}-raw-physical-tape"
GRID_TAPE_SCHEMA = f"{SCHEMA}-grid-tape"
UNIT_RECEIPT_SCHEMA = f"{SCHEMA}-unit-receipt"
TERMINAL_RECEIPT_SCHEMA = f"{SCHEMA}-terminal-receipt"
PREFLIGHT_SCHEMA = f"{SCHEMA}-preflight"
AUTHORITY_SCHEMA = f"{SCHEMA}-launch-authority"

GRIDS: dict[str, float] = {
    "G0": math.inf,
    "G1": 200e6,
    "G2": 50e6,
    "G3": 10e6,
}
SELECTION_ORDER = ("G1", "G2", "G3")
CARRIERS = (NEAREST_ELIGIBLE, STAY_IF_POSSIBLE, RANDOM_MASKED)
WORLDS = (
    5683200792433982503,
    7374843801585642838,
    3226893802015760720,
    1341435503386059806,
)
WORLD_DOMAIN_PREFIX = "V024_REGIME_B/world/"
USERS = 100
STEPS = 10
INTERVAL_S = DECISION_STEP_S
FIELD_COMPONENT = "V024_REGIME_B_PROBE_PHYSICAL_V1"
TLE_ROOT = Path("/home/sat/mcrl-runtime/tle-frozen-20260820")
DESIGN_MEMO = REPO / ".scratch/multi-catfish-v024-regime-b-design/V024-REGIME-B-DESIGN-CODEX-GPT6-ASTRA-ULTRA-2026-09-08.md"
PROTOCOL = REPO / ".scratch/multi-catfish-v024-regime-b-design/TRACK-B-PROTOCOL-2026-09-08.md"
WORLD_DERIVATION = REPO / ".scratch/multi-catfish-v024-regime-b-design/V024-WORLD-DERIVATION-2026-09-08.json"
DEFAULT_PREFLIGHT = HERE / "V024-PROBE-PREFLIGHT.json"
DEFAULT_OUTPUT = REPO / "artifacts/v024-regime-b/probe"

THRESHOLD_J_GAIN = 0.05
THRESHOLD_J_MINUS_U = 0.01
THRESHOLD_INTERACTION = 0.005
REQUIRED_POSITIVE_WORLDS = 3
DEMAND_GUARD_FRACTION = 0.95
SERVICE_MARGIN = e1_estimands.SERVICE_MARGIN


class ProbeError(RuntimeError):
    """A probe binding, physical tape, or receipt failed closed."""


class ProbeIncomplete(ProbeError):
    """The declared panel is not complete enough for a scientific result."""


def canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as error:
        raise ProbeError("value is not finite canonical ASCII JSON") from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise ProbeError(f"required regular file is missing or symlinked: {target}")
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path, *, label: str) -> dict[str, Any]:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise ProbeError(f"{label} is missing or symlinked: {target}")
    try:
        payload = json.loads(target.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ProbeError(f"{label} is not ASCII JSON: {target}") from error
    if not isinstance(payload, dict):
        raise ProbeError(f"{label} must be a JSON object")
    return payload


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str) or len(value) != 64 or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ProbeError(f"{field} must be a lowercase SHA-256")
    return value


def derive_world_seed(index: int) -> int:
    domain = f"{WORLD_DOMAIN_PREFIX}{index}"
    return int.from_bytes(hashlib.sha256(domain.encode("ascii")).digest()[:8], "big") & ((1 << 63) - 1)


def carrier_seed(world: int, carrier: str) -> int:
    """A fixed, world-rooted seed; only random-masked consumes its RNG."""

    if world not in WORLDS or carrier not in CARRIERS:
        raise ProbeError("carrier seed requested outside the fixed panel")
    domain = f"V024_REGIME_B/reference/{world}/{carrier}"
    return int.from_bytes(hashlib.sha256(domain.encode("ascii")).digest()[:8], "big") & ((1 << 63) - 1)


class UnitKey:
    def __init__(self, world: int, carrier: str) -> None:
        self.world = int(world)
        self.carrier = str(carrier)
        self.verify()

    @classmethod
    def parse(cls, value: str) -> "UnitKey":
        try:
            world, carrier = value.split(":", 1)
            return cls(int(world), carrier)
        except (TypeError, ValueError) as error:
            raise ProbeError("unit must be W:C") from error

    def verify(self) -> None:
        if self.world not in WORLDS:
            raise ProbeError("unit world is outside the fixed four-world probe panel")
        if self.carrier not in CARRIERS:
            raise ProbeError("unit carrier is outside the three fixed reference rules")

    @property
    def slug(self) -> str:
        return f"world-{self.world}-{self.carrier}"

    def as_dict(self) -> dict[str, object]:
        return {
            "world": self.world,
            "world_domain": f"{WORLD_DOMAIN_PREFIX}{WORLDS.index(self.world) + 1}",
            "carrier": self.carrier,
            "carrier_seed": carrier_seed(self.world, self.carrier),
        }


ALL_UNITS = tuple(UnitKey(world, carrier) for world in WORLDS for carrier in CARRIERS)


def panel_bindings() -> dict[str, object]:
    return {
        "grids": {name: ("infinity" if math.isinf(value) else value) for name, value in GRIDS.items()},
        "selection_rule": "FIRST_QUALIFYING_G1_THEN_G2_THEN_G3_G0_NEVER_SELECTED",
        "world_domain_prefix": WORLD_DOMAIN_PREFIX,
        "worlds": list(WORLDS),
        "carriers": list(CARRIERS),
        "carrier_definitions": {
            NEAREST_ELIGIBLE: "FIRST_MASK_TRUE_SATELLITE_MAJOR_BEAM_MINOR",
            STAY_IF_POSSIBLE: "HOLD_PHYSICAL_NORAD_CELL_IF_MASK_LEGAL_ELSE_NEAREST_ELIGIBLE",
            RANDOM_MASKED: "UNIFORM_VALID_ACTION_USER_ORDER_CARRIER_SEED_RNG",
        },
        "users": USERS,
        "steps_per_unit": STEPS,
        "unit_count": len(ALL_UNITS),
        "interval_s_hex": INTERVAL_S.hex(),
        "field_component": FIELD_COMPONENT,
        "service_margin": SERVICE_MARGIN,
        "raw_tape_sharing": "ONE_G0_PHYSICAL_TAPE_PER_WORLD_CARRIER_SHARED_BY_ALL_GRIDS",
        "qualification_thresholds": {
            "j_gain": THRESHOLD_J_GAIN,
            "j_minus_u": THRESHOLD_J_MINUS_U,
            "interaction": THRESHOLD_INTERACTION,
            "positive_worlds": REQUIRED_POSITIVE_WORLDS,
            "demand_guard": DEMAND_GUARD_FRACTION,
        },
    }


def _sealed_binding(path: Path, *, label: str) -> dict[str, str]:
    target = Path(path)
    sidecar = Path(f"{target}.sha256")
    message = f"{label} is not controller-sealed read-only with a matching .sha256 sidecar"
    if (
        target.is_symlink() or not target.is_file() or target.stat().st_mode & 0o222
        or sidecar.is_symlink() or not sidecar.is_file() or sidecar.stat().st_mode & 0o222
    ):
        raise ProbeError(message)
    digest = file_sha256(target)
    if sidecar.read_text(encoding="ascii").split() != [digest, target.name]:
        raise ProbeError(message)
    return {"path": str(target.resolve()), "sha256": digest}


def authority_documents() -> dict[str, object]:
    world_payload = _load_json(WORLD_DERIVATION, label="world derivation")
    observed = world_payload.get("probe_worlds")
    expected = {
        f"{WORLD_DOMAIN_PREFIX}{index}": seed
        for index, seed in enumerate(WORLDS, start=1)
    }
    if observed != expected or tuple(derive_world_seed(index) for index in range(1, 5)) != WORLDS:
        raise ProbeError("world derivation disagrees with the fixed probe panel")
    return {
        "design_memo": _sealed_binding(DESIGN_MEMO, label="Track-B design memo"),
        "protocol": _sealed_binding(PROTOCOL, label="Track-B protocol"),
        "world_derivation": {"path": str(WORLD_DERIVATION.resolve()), "sha256": file_sha256(WORLD_DERIVATION)},
    }


def expected_code_bindings() -> list[dict[str, str]]:
    paths = (
        HERE / "run_v024_regime_probe.py",
        HERE / "build_v024_probe_preflight.py",
        REPO / "src/mcrl/env/demand.py",
        REPO / "src/mcrl/env/step.py",
        REPO / "src/mcrl/env/reference_policy.py",
        E1_DIR / "e1_estimands.py",
        E1_DIR / "run_v023_c3_existence_e1.py",
    )
    return [{"path": str(path.resolve()), "sha256": file_sha256(path)} for path in paths]


def build_preflight_payload() -> dict[str, object]:
    return {
        "schema": PREFLIGHT_SCHEMA,
        "status": "FROZEN_PREFLIGHT",
        "claim_ceiling": CLAIM_CEILING,
        "authority_documents": authority_documents(),
        "panel_bindings": panel_bindings(),
        "e1_solver_method": e1_estimands.CERTIFICATE_METHOD,
        "e1_joint_catalog_import": str((E1_DIR / "run_v023_c3_existence_e1.py").resolve()),
        "code_files": expected_code_bindings(),
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }


def validate_preflight(path: Path) -> tuple[dict[str, Any], str]:
    target = Path(path)
    payload = _load_json(target, label="probe preflight")
    if payload != build_preflight_payload():
        raise ProbeError("probe preflight disagrees with current authority/code bindings")
    digest = file_sha256(target)
    _sealed_binding(target, label="probe preflight")
    return payload, digest


def validate_launch_authority(
    path: Path, *, preflight: Path, preflight_sha256: str, grid: str,
    output: Path, mode: str,
) -> dict[str, Any]:
    payload = _load_json(path, label="probe launch authority")
    _sealed_binding(Path(path), label="probe launch authority")
    expected = {
        "schema": AUTHORITY_SCHEMA,
        "status": "FROZEN_LAUNCH_AUTHORITY",
        "claim_ceiling": CLAIM_CEILING,
        "preflight": {"path": str(Path(preflight).resolve()), "sha256": preflight_sha256},
        "authority_documents": authority_documents(),
        "panel_bindings": panel_bindings(),
        "grid": grid,
        "mode": mode,
        "checkout_root": str(REPO.resolve()),
        "output_root": str(Path(output).resolve()),
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }
    if payload != expected:
        raise ProbeError("launch authority does not bind the exact grid/mode/preflight/output")
    return payload


def _write_once(path: Path, payload: Mapping[str, object]) -> str:
    target = Path(path)
    if target.exists() or target.is_symlink():
        raise ProbeError(f"refusing to overwrite write-once artifact: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = canonical_bytes(payload) + b"\n"
    with target.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    target.chmod(0o444)
    if target.read_bytes() != encoded or stat.S_IMODE(target.stat().st_mode) != 0o444:
        raise ProbeError(f"write-once artifact failed immutable readback: {target}")
    return hashlib.sha256(encoded).hexdigest()


def _hex_vector(value: object, *, field: str) -> list[str]:
    array = np.asarray(value, dtype=np.float64)
    if array.ndim != 1 or not np.all(np.isfinite(array)) or np.any(array < 0.0):
        raise ProbeError(f"{field} must be a finite nonnegative vector")
    return [float(item).hex() for item in array.tolist()]


def _physical_profile(evaluation: Any, *, interval_s: float) -> tuple[dict[str, object], Any, np.ndarray]:
    profile, link_power = e1_runner.f1.profile_from_evaluation(evaluation, interval_s=interval_s)
    payload = e1_runner.f1.profile_to_payload(profile, link_power_w=link_power)
    capacity_bits = np.asarray(
        getattr(evaluation, "capacity_bits", np.asarray(evaluation.link_rate_bps) * interval_s),
        dtype=np.float64,
    )
    if capacity_bits.shape != (profile.users,):
        raise ProbeError("physical profile capacity_bits has the wrong user shape")
    payload["capacity_bits"] = _hex_vector(capacity_bits, field="capacity_bits")
    payload["rate_semantics"] = "UNBOUNDED_SHANNON_CAPACITY_BITS_PER_S"
    return payload, profile, link_power


def _evaluate(step_env: Any, actions: np.ndarray, rng: np.random.Generator) -> Any:
    return e1_runner._evaluate_actions_neutral(step_env, actions, rng)


def _serialize_candidate(
    row: Mapping[str, object], *, interval_s: float
) -> dict[str, object]:
    result = dict(row)
    profile = result.pop("profile")
    link_power = np.asarray(result.pop("link_power_w"), dtype=np.float64)
    payload = e1_runner.f1.profile_to_payload(profile, link_power_w=link_power)
    capacity = np.asarray(profile.link_rate_bps, dtype=np.float64) * interval_s
    payload["capacity_bits"] = _hex_vector(capacity, field="capacity_bits")
    payload["rate_semantics"] = "UNBOUNDED_SHANNON_CAPACITY_BITS_PER_S"
    result.pop("metrics", None)
    result.pop("f0_conservation", None)
    result["profile"] = payload
    return result


def _build_joint_rows(
    *, observation: Any, reference: np.ndarray, reference_profile: Any,
    reference_link_power: np.ndarray, step_env: Any, rng: np.random.Generator,
    interval_s: float,
) -> tuple[dict[str, object], ...]:
    anchor = e1_runner.JointWitnessAnchor(
        observation=observation,
        reference_actions=reference,
        reference_profile=reference_profile,
        reference_link_power_w=reference_link_power,
        step_env=step_env,
        rng=rng,
        interval_s=interval_s,
    )
    return tuple(
        _serialize_candidate(row, interval_s=interval_s)
        for row in e1_runner.build_joint_witness_catalog(anchor)
    )


def _production_environment(key: UnitKey, tle_root: Path) -> tuple[Any, tuple[np.random.Generator, ...]]:
    """Reuse E1's TRAIN epoch/TLE/RNG conventions without any checkpoint."""

    from mcrl.env.ephemeris import TRAIN, BlockAlternatingSplit, EpisodeStartSampler
    from mcrl.env.mobility import MobilityConfig
    from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
    from mcrl.env.step import StepEnvironment
    from mcrl.env.tle import TleArchive
    from mcrl.runtime.trainer_env import TrainerEnvironment
    from mcrl.runtime.training_pipeline import _evaluation_rngs

    archive = TleArchive(Path(tle_root))
    driver = ScenarioDriver(
        archive, ScenarioConfig(mobility=MobilityConfig(num_users=USERS))
    )
    split = BlockAlternatingSplit.for_archive(archive)
    environment = TrainerEnvironment(
        StepEnvironment(driver), EpisodeStartSampler.for_archive(archive, split, TRAIN)
    )
    rngs = tuple(_evaluation_rngs(key.world))
    step_env = environment.environment
    if getattr(step_env, "_started", False):
        raise ProbeError("environment started before keyed-field binding")
    step_env._fading_field = KeyedFadingField.from_components(FIELD_COMPONENT, key.world)
    return environment, rngs


ENVIRONMENT_FACTORY: Callable[[UnitKey, Path], tuple[Any, tuple[np.random.Generator, ...]]] = _production_environment
JOINT_BUILDER = _build_joint_rows


def generate_raw_tape(*, key: UnitKey, tle_root: Path, preflight_sha256: str) -> dict[str, object]:
    key.verify()
    environment, rngs = ENVIRONMENT_FACTORY(key, tle_root)
    if len(rngs) < 2:
        raise ProbeError("environment factory must provide environment and mobility RNGs")
    _states, _masks, observation = environment.reset(rngs[0], rngs[1])
    step_env = environment.environment
    interval_s = float(step_env.driver.config.ephemeris.time_step_s)
    if interval_s != INTERVAL_S or step_env.num_users != USERS:
        raise ProbeError("unit environment violates canonical interval/users")
    policy = build_reference_policy(key.carrier, carrier_seed(key.world, key.carrier))
    policy_rng = np.random.default_rng(carrier_seed(key.world, key.carrier))
    policy.reset()
    steps: list[dict[str, object]] = []
    for step_index in range(STEPS):
        if int(observation.step_index) != step_index:
            raise ProbeError("unit episode reached a noncanonical step")
        reference = np.asarray(policy.act(observation.candidates, policy_rng), dtype=np.int64)
        base_eval = _evaluate(step_env, reference, rngs[0])
        base_payload, base_profile, base_link_power = _physical_profile(base_eval, interval_s=interval_s)
        unilateral: list[dict[str, object]] = []
        for skeleton in e1_runner.f1.enumerate_unilateral_candidates(observation, reference):
            actions = np.asarray(skeleton["candidate_joint_actions"], dtype=np.int64)
            evaluation = _evaluate(step_env, actions, rngs[0])
            profile_payload, _profile, _link = _physical_profile(evaluation, interval_s=interval_s)
            unilateral.append({
                **skeleton,
                "profile_id": f"U:{skeleton['focal_user']}:{skeleton['candidate_action']}",
                "profile": profile_payload,
            })
        joint = list(JOINT_BUILDER(
            observation=observation, reference=reference,
            reference_profile=base_profile, reference_link_power=base_link_power,
            step_env=step_env, rng=rngs[0], interval_s=interval_s,
        ))
        steps.append({
            "step_index": step_index,
            "state_sha256": observation.observation_provenance.content_digest,
            "action_masks": [[bool(value) for value in row] for row in np.asarray(observation.masks).tolist()],
            "action_physical_keys": e1_runner.f1.action_physical_keys(observation),
            "reference_actions": [int(value) for value in reference.tolist()],
            "reference_profile": base_payload,
            "unilateral_profiles": unilateral,
            "joint_profiles": joint,
        })
        committed = environment.step(reference, rngs[0])
        committed_payload, _committed_profile, _committed_power = _physical_profile(
            environment.last_outcome, interval_s=interval_s
        )
        if committed_payload != base_payload:
            raise ProbeError("committed reference profile disagrees with its neutral evaluation")
        if step_index < STEPS - 1:
            if bool(committed.done):
                raise ProbeError("unit episode ended before step 9")
            observation = committed.observation
    return {
        "schema": RAW_TAPE_SCHEMA,
        "status": "COMPLETE_IMMUTABLE_TAPE",
        "claim_ceiling": CLAIM_CEILING,
        "unit": key.as_dict(),
        "panel_bindings": panel_bindings(),
        "preflight_sha256": preflight_sha256,
        "steps": steps,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }


def _profile_metrics(profile: Mapping[str, object], *, grid: str) -> dict[str, object]:
    try:
        capacity = np.asarray([float.fromhex(value) for value in profile["capacity_bits"]], dtype=np.float64)
        served = np.asarray(profile["served"], dtype=np.bool_)
        interval = float.fromhex(str(profile["interval_s"]))
        power = float.fromhex(str(profile["system_power_w"]))
    except (KeyError, TypeError, ValueError) as error:
        raise ProbeError("raw physical profile cannot be demand-capped") from error
    if capacity.shape != served.shape or capacity.ndim != 1 or interval != INTERVAL_S or power <= 0.0:
        raise ProbeError("raw physical profile has malformed capacity/service/energy")
    demand = GRIDS[grid]
    if math.isinf(demand):
        delivered = capacity.copy()
        demand_satisfied = int(np.count_nonzero(served))
        guard_applicable = False
    else:
        offered = demand * interval
        delivered = np.minimum(capacity, offered)
        demand_satisfied = int(np.count_nonzero(served & (delivered >= DEMAND_GUARD_FRACTION * offered)))
        guard_applicable = True
    return {
        "total_bits": float(math.fsum(delivered.tolist())),
        "total_energy_j": float(power * interval),
        "served": int(np.count_nonzero(served)),
        "opportunities": int(served.size),
        "demand_satisfied": demand_satisfied,
        "demand_guard_applicable": guard_applicable,
        "delivered_bits": _hex_vector(delivered, field="delivered_bits"),
    }


def derive_grid_tape(raw: Mapping[str, object], *, grid: str, raw_sha256: str) -> dict[str, object]:
    if grid not in GRIDS:
        raise ProbeError("grid is outside G0..G3")
    if raw.get("schema") != RAW_TAPE_SCHEMA or raw.get("status") != "COMPLETE_IMMUTABLE_TAPE":
        raise ProbeError("raw tape schema/status drifted")
    steps = raw.get("steps")
    if not isinstance(steps, list) or len(steps) != STEPS:
        raise ProbeError("raw tape is incomplete")
    derived = []
    for step in steps:
        if not isinstance(step, Mapping):
            raise ProbeError("raw tape step is malformed")
        rows: dict[str, list[dict[str, object]]] = {}
        for field in ("unilateral_profiles", "joint_profiles"):
            candidates = step.get(field)
            if not isinstance(candidates, list):
                raise ProbeError(f"raw {field} is malformed")
            rows[field] = [
                {
                    "profile_id": str(row["profile_id"]),
                    "focal_user": row.get("focal_user"),
                    "candidate_action": row.get("candidate_action"),
                    "origin_users": row.get("origin_users"),
                    "candidate_joint_actions": row.get("candidate_joint_actions"),
                    **_profile_metrics(row["profile"], grid=grid),
                }
                for row in candidates
            ]
        derived.append({
            "step_index": step["step_index"],
            "base": {"profile_id": "BASE", **_profile_metrics(step["reference_profile"], grid=grid)},
            **rows,
        })
    return {
        "schema": GRID_TAPE_SCHEMA,
        "status": "COMPLETE_DERIVED_TAPE",
        "claim_ceiling": CLAIM_CEILING,
        "grid": grid,
        "demand_bits_per_s": "infinity" if math.isinf(GRIDS[grid]) else GRIDS[grid],
        "unit": raw["unit"],
        "raw_tape_sha256": _digest(raw_sha256, field="raw_tape_sha256"),
        "preflight_sha256": raw["preflight_sha256"],
        "steps": derived,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }


def _raw_path(output: Path, key: UnitKey) -> Path:
    return Path(output) / "raw-units" / key.slug / "physical-tape.json"


def _grid_path(output: Path, grid: str, key: UnitKey) -> Path:
    return Path(output) / "grids" / grid / "units" / key.slug / "grid-tape.json"


def _execute_unit_impl(
    *, key: UnitKey, grid: str, output: Path, tle_root: Path,
    preflight_sha256: str,
) -> tuple[Path, bool]:
    raw_path = _raw_path(output, key)
    raw_created = False
    if raw_path.exists():
        if raw_path.stat().st_mode & 0o222:
            raise ProbeError("existing raw tape is writable")
        raw = _load_json(raw_path, label="raw physical tape")
        raw_sha = file_sha256(raw_path)
        if raw.get("unit") != key.as_dict() or raw.get("preflight_sha256") != preflight_sha256:
            raise ProbeError("existing raw tape binding drifted")
    else:
        raw = generate_raw_tape(key=key, tle_root=tle_root, preflight_sha256=preflight_sha256)
        raw_sha = _write_once(raw_path, raw)
        raw_created = True
    grid_path = _grid_path(output, grid, key)
    derived = derive_grid_tape(raw, grid=grid, raw_sha256=raw_sha)
    if grid_path.exists():
        if _load_json(grid_path, label="grid tape") != derived or grid_path.stat().st_mode & 0o222:
            raise ProbeError("existing grid tape disagrees with raw physical tape")
        receipt_path = grid_path.with_name("receipt.json")
        receipt = _load_json(receipt_path, label="unit receipt")
        if receipt.get("status") != "COMPLETE" or receipt_path.stat().st_mode & 0o222:
            raise ProbeError("existing unit receipt is not immutable COMPLETE")
        return receipt_path, False
    _write_once(grid_path, derived)
    receipt = {
        "schema": UNIT_RECEIPT_SCHEMA,
        "status": "COMPLETE",
        "outcome": "V024_PROBE_UNIT_COMPLETE",
        "claim_ceiling": CLAIM_CEILING,
        "grid": grid,
        "unit": key.as_dict(),
        "raw_tape": {"path": str(raw_path.resolve()), "sha256": raw_sha, "created_by_this_launch": raw_created},
        "grid_tape": {"path": str(grid_path.resolve()), "sha256": file_sha256(grid_path)},
        "preflight_sha256": preflight_sha256,
        "integrity": True,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }
    receipt_path = grid_path.with_name("receipt.json")
    _write_once(receipt_path, receipt)
    return receipt_path, True


def execute_unit(
    *, key: UnitKey, grid: str, output: Path, tle_root: Path,
    preflight_sha256: str,
) -> tuple[Path, bool]:
    """Execute a unit and seal non-scientific terminal failures like E1."""

    try:
        return _execute_unit_impl(
            key=key, grid=grid, output=output, tle_root=tle_root,
            preflight_sha256=preflight_sha256,
        )
    except (KeyboardInterrupt, e1_estimands.E1ResourceIncomplete) as error:
        status = "INCOMPLETE"
        caught = error
    except Exception as error:
        status = "INVALID_RUN"
        caught = error
    receipt_path = _grid_path(output, grid, key).with_name("receipt.json")
    if receipt_path.exists() or receipt_path.is_symlink():
        raise ProbeError("unit failed after a receipt path was already published") from caught
    payload = {
        "schema": UNIT_RECEIPT_SCHEMA,
        "status": status,
        "outcome": status,
        "claim_ceiling": CLAIM_CEILING,
        "grid": grid,
        "unit": key.as_dict(),
        "raw_tape": None,
        "grid_tape": None,
        "preflight_sha256": preflight_sha256,
        "integrity": False,
        "error_type": type(caught).__name__,
        "error_sha256": hashlib.sha256(str(caught).encode("utf-8")).hexdigest(),
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }
    _write_once(receipt_path, payload)
    return receipt_path, True


def _anchor_panels(output: Path, grid: str) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, dict[str, object]]]:
    unilateral_panel: list[dict[str, object]] = []
    joint_panel: list[dict[str, object]] = []
    metadata: dict[str, dict[str, object]] = {}
    for key in ALL_UNITS:
        path = _grid_path(output, grid, key)
        if not path.is_file():
            raise ProbeIncomplete(f"missing grid unit {key.slug}")
        receipt_path = path.with_name("receipt.json")
        if not receipt_path.is_file():
            raise ProbeIncomplete(f"missing grid unit receipt {key.slug}")
        receipt = _load_json(receipt_path, label="unit receipt")
        if (
            receipt_path.stat().st_mode & 0o222
            or receipt.get("status") != "COMPLETE"
            or receipt.get("grid") != grid
            or receipt.get("unit") != key.as_dict()
            or receipt.get("grid_tape", {}).get("sha256") != file_sha256(path)
        ):
            raise ProbeError("unit receipt/grid tape binding drifted")
        tape = _load_json(path, label="grid tape")
        if tape.get("grid") != grid or tape.get("unit") != key.as_dict():
            raise ProbeError("grid unit binding drifted")
        raw_path = _raw_path(output, key)
        raw = _load_json(raw_path, label="raw physical tape")
        raw_sha = file_sha256(raw_path)
        if (
            raw_path.stat().st_mode & 0o222
            or tape.get("raw_tape_sha256") != raw_sha
            or receipt.get("raw_tape", {}).get("sha256") != raw_sha
            or raw.get("unit") != key.as_dict()
            or derive_grid_tape(raw, grid=grid, raw_sha256=raw_sha) != tape
        ):
            raise ProbeError("raw/grid shared-tape authentication failed")
        for step in tape["steps"]:
            anchor_id = f"{key.world}:{key.carrier}:{step['step_index']}"
            base = {name: step["base"][name] for name in ("profile_id", "total_bits", "total_energy_j", "served", "opportunities")}
            unilateral = [
                {name: row[name] for name in ("profile_id", "total_bits", "total_energy_j", "served", "opportunities")}
                for row in step["unilateral_profiles"]
            ]
            joint = [
                {name: row[name] for name in ("profile_id", "total_bits", "total_energy_j", "served", "opportunities")}
                for row in step["joint_profiles"]
            ]
            unilateral_panel.append({"anchor_id": anchor_id, "base": base, "unilateral_profiles": unilateral})
            joint_panel.append({"anchor_id": anchor_id, "base": base, "joint_profiles": joint})
            metadata[anchor_id] = {
                "world": key.world,
                "base": step["base"],
                "unilateral": {row["profile_id"]: row for row in step["unilateral_profiles"]},
                "joint": {row["profile_id"]: row for row in step["joint_profiles"]},
            }
    return unilateral_panel, joint_panel, metadata


def interaction_and_directions(
    *, j1: Mapping[str, object], metadata: Mapping[str, Mapping[str, object]],
    eta_ref: float, grid: str,
) -> dict[str, object]:
    surplus = 0.0
    reference_bits = 0.0
    world_values = {world: 0.0 for world in WORLDS}
    selected_demand = base_demand = opportunities = 0
    chosen = j1.get("chosen_profiles")
    if not isinstance(chosen, Mapping):
        raise ProbeError("J1 result lacks chosen profiles")
    for anchor_id, profile_id in chosen.items():
        info = metadata[str(anchor_id)]
        base = info["base"]
        reference_bits += float(base["total_bits"])
        row = base if profile_id == "BASE" else info["joint"].get(profile_id)
        if row is None:
            raise ProbeError("J witness profile is absent from grid metadata")
        selected_demand += int(row["demand_satisfied"])
        base_demand += int(base["demand_satisfied"])
        opportunities += int(base["opportunities"])
        joint_value = (
            float(row["total_bits"]) - float(base["total_bits"])
            - eta_ref * (float(row["total_energy_j"]) - float(base["total_energy_j"]))
        )
        world_values[int(info["world"])] += joint_value
        if profile_id == "BASE":
            continue
        unilateral_sum = 0.0
        actions = row.get("candidate_joint_actions")
        users = row.get("origin_users")
        if not isinstance(actions, list) or not isinstance(users, list):
            raise ProbeError("J witness lacks complete changed-user actions")
        for user in users:
            unilateral_id = f"U:{user}:{actions[user]}"
            single = info["unilateral"].get(unilateral_id)
            if single is None:
                raise ProbeError("J witness lacks its matching unilateral profile")
            unilateral_sum += (
                float(single["total_bits"]) - float(base["total_bits"])
                - eta_ref * (float(single["total_energy_j"]) - float(base["total_energy_j"]))
            )
        surplus += joint_value - unilateral_sum
    if math.isinf(GRIDS[grid]):
        demand_guard = True
        demand_note = "NOT_APPLICABLE_G0_FULL_BUFFER"
    else:
        selected_fraction = selected_demand / opportunities
        base_fraction = base_demand / opportunities
        demand_guard = (
            selected_fraction >= DEMAND_GUARD_FRACTION
            and selected_fraction >= base_fraction - SERVICE_MARGIN
        )
        demand_note = "APPLIED"
    return {
        "interaction_surplus_bits": surplus,
        "reference_bits": reference_bits,
        "interaction_fraction": surplus / reference_bits,
        "world_joint_value_bits": {str(world): value for world, value in world_values.items()},
        "positive_world_count": sum(value > 0.0 for value in world_values.values()),
        "demand_guard_pass": demand_guard,
        "demand_guard_note": demand_note,
        "selected_demand_satisfied": selected_demand,
        "base_demand_satisfied": base_demand,
        "opportunities": opportunities,
    }


def qualification(
    *, j1: float, u1: float, eta_ref: float, interaction_fraction: float,
    positive_world_count: int, demand_guard_pass: bool,
) -> dict[str, object]:
    tests = {
        "j1_over_reference_minus_one_at_least_5pct": j1 >= eta_ref * (1.0 + THRESHOLD_J_GAIN),
        "j1_minus_u1_over_reference_at_least_1pct": j1 - u1 >= eta_ref * THRESHOLD_J_MINUS_U,
        "interaction_over_reference_bits_at_least_0_5pct": interaction_fraction >= THRESHOLD_INTERACTION,
        "at_least_three_worlds_positive_with_demand_guard": positive_world_count >= REQUIRED_POSITIVE_WORLDS and demand_guard_pass,
    }
    qualifies = all(tests.values())
    return {
        "tests": tests,
        "outcome": "V024_PROBE_QUALIFIES" if qualifies else "V024_PROBE_NOT_QUALIFYING",
        "qualifies": qualifies,
    }


def execute_merge(*, output: Path, grid: str, preflight_sha256: str) -> Path:
    terminal = Path(output) / "grids" / grid / "terminal-receipt.json"
    if terminal.exists() or terminal.is_symlink():
        raise ProbeError("refusing to overwrite write-once terminal receipt")
    try:
        unilateral, joint, metadata = _anchor_panels(output, grid)
        u1 = e1_estimands.solve_u1(unilateral)
        j1 = e1_estimands.solve_j1(joint)
        if u1["eta_BASE_hex"] != j1["eta_BASE_hex"]:
            raise ProbeError("U1/J1 reference EE differs")
        eta_ref = float(j1["eta_BASE"])
        interaction = interaction_and_directions(j1=j1, metadata=metadata, eta_ref=eta_ref, grid=grid)
        verdict = qualification(
            j1=float(j1["J1"]), u1=float(u1["U1"]), eta_ref=eta_ref,
            interaction_fraction=float(interaction["interaction_fraction"]),
            positive_world_count=int(interaction["positive_world_count"]),
            demand_guard_pass=bool(interaction["demand_guard_pass"]),
        )
        payload = {
            "schema": TERMINAL_RECEIPT_SCHEMA,
            "status": "COMPLETE",
            "outcome": verdict["outcome"],
            "claim_ceiling": CLAIM_CEILING,
            "grid": grid,
            "preflight_sha256": preflight_sha256,
            "panel_bindings": panel_bindings(),
            "U1": u1,
            "J1": j1,
            "interaction": interaction,
            "qualification": verdict,
            "selection_rule": "FIRST_QUALIFYING_G1_THEN_G2_THEN_G3_G0_NEVER_SELECTED",
            "integrity": True,
            "test_split_opened": False,
            "episode_training": False,
            "learner_update": False,
            "efficacy_claim": False,
        }
    except ProbeIncomplete as error:
        payload = _terminal_failure(grid, preflight_sha256, "INCOMPLETE", error)
    except e1_estimands.E1ResourceIncomplete as error:
        payload = _terminal_failure(grid, preflight_sha256, "INCOMPLETE", error)
    except Exception as error:
        payload = _terminal_failure(grid, preflight_sha256, "INVALID_RUN", error)
    _write_once(terminal, payload)
    return terminal


def _terminal_failure(grid: str, preflight_sha256: str, status: str, error: BaseException) -> dict[str, object]:
    return {
        "schema": TERMINAL_RECEIPT_SCHEMA,
        "status": status,
        "outcome": status,
        "claim_ceiling": CLAIM_CEILING,
        "grid": grid,
        "preflight_sha256": preflight_sha256,
        "panel_bindings": panel_bindings(),
        "U1": None,
        "J1": None,
        "interaction": None,
        "qualification": None,
        "selection_rule": "FIRST_QUALIFYING_G1_THEN_G2_THEN_G3_G0_NEVER_SELECTED",
        "integrity": False,
        "error_type": type(error).__name__,
        "error_sha256": hashlib.sha256(str(error).encode("utf-8")).hexdigest(),
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }


def select_grid(receipts: Mapping[str, Mapping[str, object]]) -> str | None:
    """Encode the preregistered choice; this function does not run selection."""

    for grid in SELECTION_ORDER:
        receipt = receipts.get(grid)
        if receipt is not None and receipt.get("status") == "COMPLETE" and receipt.get("outcome") == "V024_PROBE_QUALIFIES":
            return grid
    return None


def estimate() -> dict[str, object]:
    anchors = len(ALL_UNITS) * STEPS
    max_unilateral = anchors * USERS * 27
    max_joint = anchors * USERS * 27
    return {
        "worlds": len(WORLDS),
        "carriers": len(CARRIERS),
        "units": len(ALL_UNITS),
        "anchors": anchors,
        "raw_reference_profiles": anchors,
        "raw_unilateral_profiles_upper_bound": max_unilateral,
        "raw_joint_profiles_upper_bound": max_joint,
        "raw_physical_profile_evaluations_upper_bound": anchors + max_unilateral + max_joint,
        "grid_derivations": len(GRIDS),
        "raw_tape_runs": len(ALL_UNITS),
        "worker_hours_low": 12,
        "worker_hours_high": 24,
        "cost_basis": "E1_FIRST_24_HOUR_PROBE_RESERVE_FROM_V024_DESIGN_MEMO_SECTION_5",
        "note": "raw physical evaluations are shared once across all four grids",
    }


def pin_single_thread_runtime() -> None:
    """Enforce the server launch contract, including Torch's two pools."""

    names = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")
    if any(os.environ.get(name) != "1" for name in names):
        raise ProbeError("probe requires every declared thread environment variable to equal 1")
    try:
        e1_runner.pin_single_thread_runtime()
    except e1_runner.E1Error as error:
        raise ProbeError(str(error)) from error


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid", choices=tuple(GRIDS))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--unit", help="one fixed WORLD:CARRIER unit")
    mode.add_argument("--merge", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--estimate", action="store_true")
    parser.add_argument("--preflight", type=Path, default=DEFAULT_PREFLIGHT)
    parser.add_argument("--launch-authority", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--tle-root", type=Path, default=TLE_ROOT)
    return parser


def run(args: argparse.Namespace) -> dict[str, object]:
    if args.estimate:
        return {"mode": "estimate", "estimate": estimate()}
    if args.grid is None:
        raise ProbeError("--grid is required outside --estimate")
    if args.dry_run:
        # Surface the controller seal gate before a downstream absent
        # preflight, matching E1's launch-authority lifecycle.
        authority_documents()
    _preflight, preflight_sha = validate_preflight(args.preflight)
    mode = "dry-run" if args.dry_run else "unit" if args.unit is not None else "merge" if args.merge else ""
    if not mode:
        raise ProbeError("choose --unit or --merge, or use --dry-run")
    if args.launch_authority is not None:
        validate_launch_authority(
            args.launch_authority, preflight=args.preflight,
            preflight_sha256=preflight_sha, grid=args.grid,
            output=args.output, mode=mode,
        )
    elif not args.dry_run:
        raise ProbeError("execution requires a controller-sealed --launch-authority")
    if args.dry_run:
        return {"mode": mode, "grid": args.grid, "worlds": WORLDS, "preflight_sha256": preflight_sha}
    if args.unit is not None:
        receipt, written = execute_unit(
            key=UnitKey.parse(args.unit), grid=args.grid, output=args.output,
            tle_root=args.tle_root, preflight_sha256=preflight_sha,
        )
        return {
            "mode": "unit", "receipt": str(receipt), "written": written,
            "status": _load_json(receipt, label="unit receipt")["status"],
        }
    receipt = execute_merge(output=args.output, grid=args.grid, preflight_sha256=preflight_sha)
    return {"mode": "merge", "receipt": str(receipt)}


def main(argv: Sequence[str] | None = None) -> int:
    try:
        pin_single_thread_runtime()
    except Exception as error:
        print(f"V024_PROBE_ERROR: {error}", file=sys.stderr)
        return 2
    args = _parser().parse_args(argv)
    try:
        result = run(args)
    except Exception as error:
        print(f"V024_PROBE_ERROR: {error}", file=sys.stderr)
        return 2
    if result["mode"] == "estimate":
        print(json.dumps(result["estimate"], sort_keys=True, indent=2))
    elif result["mode"] == "dry-run":
        print(f"V024_PROBE_DRY_RUN_PASS grid={result['grid']} preflight={result['preflight_sha256']}")
    else:
        print(f"V024_PROBE_{str(result['mode']).upper()} receipt={result['receipt']}")
    status = result.get("status")
    return 3 if status == "INCOMPLETE" else 2 if status == "INVALID_RUN" else 0


if __name__ == "__main__":
    raise SystemExit(main())
