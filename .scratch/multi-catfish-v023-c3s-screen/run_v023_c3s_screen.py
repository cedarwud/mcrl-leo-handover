#!/usr/bin/env python3
"""Three-arm closed-loop C3S kill-screen runner (no implicit formal run).

Each ``--unit WORLD:LINEAGE`` invocation always runs BASE, FULL, then LITE;
partial-arm execution is intentionally unsupported so one receipt is matched.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
from typing import Any, Callable, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
E1_DIR = REPO / ".scratch" / "multi-catfish-v023-c3-existence-e1"
F1_DIR = REPO / ".scratch" / "multi-catfish-v023-c3-contingency-f1"
F2_DIR = REPO / ".scratch" / "multi-catfish-v023-c3-contingency-f2"
S0_DIR = REPO / ".scratch" / "multi-catfish-v023-c3-probe-s0"
STAGEC_DIR = REPO / ".scratch" / "multi-catfish-v023-c1c2-successor-physical-evaluation"
for _path in (HERE, E1_DIR, F1_DIR, F2_DIR, S0_DIR, STAGEC_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import c3s_policy  # noqa: E402
import run_probe_s0 as s0  # noqa: E402
import run_v023_c3_contingency_f1 as f1  # noqa: E402
import run_v023_c3_contingency_f2 as f2  # noqa: E402
import run_v023_c3_existence_e1 as e1  # noqa: E402


SCHEMA = "multi-catfish-mcrl-v023-c3s-screen-v2"
PREFLIGHT_SCHEMA = f"{SCHEMA}-preflight-manifest"
LAUNCH_AUTHORITY_SCHEMA = f"{SCHEMA}-launch-authority"
UNIT_RECEIPT_SCHEMA = f"{SCHEMA}-unit-receipt"
TERMINAL_RECEIPT_SCHEMA = f"{SCHEMA}-terminal-receipt"
CLAIM_CEILING = "TRAIN_DEVELOPMENT_C3S_CLOSED_LOOP_KILL_SCREEN_NO_LEARNER_NO_EFFICACY_NO_TEST"

CONTRACT_PATH = HERE / "V023-C3S-SET-LEVEL-COORDINATOR-KILL-SCREEN-CONTRACT-2026-09-08.md"
CONFIG_PATH = HERE / "c3s_config.json"
DEFAULT_PREFLIGHT = HERE / "C3S-PREFLIGHT-MANIFEST.json"
DEFAULT_OUTPUT = HERE / "run-output"
DEFAULT_HORIZON = 30
CANONICAL_TLE_ROOT = Path("/home/sat/mcrl-runtime/tle-frozen-20260820")
CANONICAL_INTERPRETER = Path("/home/sat/mcrl-leo-handover/.venv/bin/python")
S0_RESULT = Path("/home/sat/mcrl-v023-c3-probe-s0-20260908-r1/probe-s0-result.json")
S0_RESULT_SHA256 = "ba496e936c5c884d8541c3312c142ac4b83cbaec0d173cba8be34fc4faa31c5b"
E1_LEDGER = Path("/home/sat/mcrl-v023-c3-existence-e1-20260908-r1/budget-ledger.json")
E1_LEDGER_SHA256 = "43d13115c7138fe7491b72a20ddf59ccfb3c2d385167166b9bcea67427b70030"
WORLD_DOMAIN_PREFIX = "C3S_SCREEN/world/"
WORLD_DOMAINS = tuple(f"{WORLD_DOMAIN_PREFIX}{index}" for index in range(1, 5))
WORLD_MASK = (1 << 63) - 1
LINEAGES = tuple(e1.LINEAGES)
FIELD_COMPONENT = e1.FIELD_COMPONENT
USERS = 100
ARMS = ("BASE", "FULL", "LITE")
COORDINATOR_ARMS = ("FULL", "LITE")
SERVICE_MARGIN = Fraction(1, 1000)
CHECKPOINT_EVERY = 100
THREAD_ENV = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")
OUTCOME_PREFIX = {"FULL": "C3S_FULL_SCREEN", "LITE": "C3S_LITE_SCREEN"}
REASON_ORDER = ("EE_NOT_STRICTLY_ABOVE_BASE", "SERVICE_MARGIN_FAILED")
PROGRESSION_RULE = (
    "both SUPPORT -> lite proceeds; exactly one SUPPORT -> that configuration proceeds; "
    "neither SUPPORT -> progression closed"
)
UNIT_RECEIPT_NAME = "receipt.json"
TERMINAL_RECEIPT_NAME = "terminal-receipt.json"
GLOBAL_INVALIDATION_NAME = "GLOBAL-INVALIDATION.json"


class C3SScreenError(RuntimeError):
    """A C3S authority, runtime, or immutable receipt failed closed."""


class C3SScreenIncomplete(C3SScreenError):
    """Execution stopped without a scientific disposition."""


class MergeWaiting(C3SScreenIncomplete):
    def __init__(self, missing: int) -> None:
        self.missing = missing
        self.receipt: Path | None = None
        super().__init__(f"{missing} units missing")


def canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as error:
        raise C3SScreenError("artifact is not finite canonical ASCII JSON") from error


def file_sha256(path: Path) -> str:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise C3SScreenError(f"required regular file is absent or symlinked: {target}")
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str) or len(value) != 64 or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise C3SScreenError(f"{field} must be a lowercase SHA-256")
    return value


def load_json(path: Path, *, field: str) -> dict[str, Any]:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise C3SScreenError(f"{field} is absent or symlinked")
    try:
        value = json.loads(target.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise C3SScreenError(f"{field} is not valid ASCII JSON") from error
    if not isinstance(value, dict):
        raise C3SScreenError(f"{field} must be a JSON object")
    return value


def derive_world_seed(domain: str) -> int:
    if domain not in WORLD_DOMAINS:
        raise C3SScreenError("world domain is outside C3S_SCREEN/world/{1..4}")
    return int.from_bytes(hashlib.sha256(domain.encode("ascii")).digest()[:8], "big") & WORLD_MASK


WORLDS = tuple(derive_world_seed(domain) for domain in WORLD_DOMAINS)
EXPECTED_WORLDS = (
    8464287092499831892, 7305539127129390835,
    7691130988233444596, 5887834234954284271,
)
if WORLDS != EXPECTED_WORLDS:  # pragma: no cover - module integrity assertion
    raise RuntimeError("C3S world derivation drifted")


@dataclass(frozen=True, order=True)
class UnitKey:
    world: int
    lineage: int

    @classmethod
    def parse(cls, value: str) -> "UnitKey":
        try:
            world, lineage = value.split(":", 1)
            result = cls(int(world), int(lineage))
        except (AttributeError, TypeError, ValueError) as error:
            raise C3SScreenError("--unit must be WORLD:LINEAGE") from error
        result.verify()
        return result

    def verify(self) -> None:
        if type(self.world) is not int or self.world not in WORLDS:
            raise C3SScreenError("unit world is outside the four derived C3S worlds")
        if type(self.lineage) is not int or self.lineage not in LINEAGES:
            raise C3SScreenError("unit lineage is outside the authenticated lineage panel")

    @property
    def slug(self) -> str:
        self.verify()
        return f"{self.world}-{self.lineage}"

    def as_dict(self) -> dict[str, int]:
        self.verify()
        return {"world": self.world, "lineage": self.lineage}


ALL_UNITS = tuple(UnitKey(world, lineage) for world in WORLDS for lineage in LINEAGES)


def fraction_payload(value: Fraction) -> dict[str, str]:
    return {
        "numerator": str(value.numerator),
        "denominator": str(value.denominator),
        "float_hex": float(value).hex(),
    }


def panel_bindings(horizon: int) -> dict[str, object]:
    if type(horizon) is not int or horizon < 1:
        raise C3SScreenError("horizon must be a positive exact integer")
    return {
        "world_seed_derivation": {
            "algorithm": "SHA256_ASCII_FIRST_8_BYTES_BIG_ENDIAN_MASK_INT63",
            "domains": list(WORLD_DOMAINS), "seeds": list(WORLDS),
        },
        "lineages": list(LINEAGES),
        "units": len(ALL_UNITS), "episodes": len(ALL_UNITS) * len(ARMS),
        "users": USERS, "horizon": horizon,
        "arms": list(ARMS), "split": "TRAIN", "field_component": FIELD_COMPONENT,
        "unit_execution": "ALL_THREE_ARMS_SEQUENTIALLY_FROM_MATCHED_INITIAL_STATE",
        "field_root_digests": {
            str(world): e1.KeyedFadingField.from_components(FIELD_COMPONENT, world).root_digest
            for world in WORLDS
        },
        "trajectory_rule": "OWN_TRAJECTORY_AFTER_IDENTICAL_INITIAL_WORLD",
        "selection_rule": "S0_NOMINAL_BITS_MINUS_ETA_REF_ENERGY_WITH_BASE_SERVICE_GUARD",
        "service_margin": fraction_payload(SERVICE_MARGIN),
        "checkpoint_every_episodes": CHECKPOINT_EVERY,
    }


def sealed_contract_binding() -> dict[str, str]:
    sidecar = Path(f"{CONTRACT_PATH}.sha256")
    message = "C3S contract is not sealed read-only with matching .sha256 sidecar"
    try:
        if (
            CONTRACT_PATH.is_symlink() or not CONTRACT_PATH.is_file()
            or CONTRACT_PATH.stat().st_mode & 0o777 != 0o444
            or sidecar.is_symlink() or not sidecar.is_file()
            or sidecar.stat().st_mode & 0o777 != 0o444
        ):
            raise C3SScreenError(message)
        digest = file_sha256(CONTRACT_PATH)
        if sidecar.read_text(encoding="ascii").split() != [digest, CONTRACT_PATH.name]:
            raise C3SScreenError(message)
    except (OSError, UnicodeError, C3SScreenError):
        raise C3SScreenError(message) from None
    return {"path": str(CONTRACT_PATH.resolve()), "sha256": digest}


def _local(path: Path, *, field: str) -> Path:
    target = (Path.cwd() / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    if not target.is_relative_to(HERE.resolve()):
        raise C3SScreenError(f"{field} must remain inside {HERE}")
    return target


def expected_code_bindings() -> list[dict[str, str]]:
    paths = (
        ("c3s_policy", HERE / "c3s_policy.py"),
        ("c3s_runner", HERE / "run_v023_c3s_screen.py"),
        ("c3s_preflight_builder", HERE / "build_c3s_preflight_manifest.py"),
        ("c3s_authority_builder", HERE / "build_c3s_launch_authority.py"),
        ("c3s_tests", HERE / "test_c3s_screen.py"),
        ("eta_ref_config", CONFIG_PATH),
        ("s0_nominal_evaluator", S0_DIR / "run_probe_s0.py"),
        ("e1_catalog_and_neutrality", E1_DIR / "run_v023_c3_existence_e1.py"),
        ("f1_unilateral_builder", F1_DIR / "run_v023_c3_contingency_f1.py"),
        ("f2_lineage_loader", F2_DIR / "run_v023_c3_contingency_f2.py"),
        ("step_physics", REPO / "src/mcrl/env/step.py"),
        ("keyed_field", REPO / "src/mcrl/env/keyed_fading.py"),
        ("rng_factory", REPO / "src/mcrl/runtime/training_pipeline.py"),
    )
    return [
        {"role": role, "path": str(path.resolve()), "sha256": file_sha256(path)}
        for role, path in paths
    ]


def pin_single_thread_runtime() -> None:
    if Path(sys.executable).resolve() != CANONICAL_INTERPRETER.resolve():
        raise C3SScreenError(f"C3S requires interpreter {CANONICAL_INTERPRETER}")
    if any(os.environ.get(name) != "1" for name in THREAD_ENV):
        raise C3SScreenError("all OMP/BLAS numerical thread variables must equal 1")
    try:
        e1.pin_single_thread_runtime()
    except e1.E1Error as error:
        raise C3SScreenError(str(error)) from error


def validate_static_bindings() -> dict[str, object]:
    contract = sealed_contract_binding()
    if USERS != e1.USERS or LINEAGES != tuple(f2.LINEAGES) or len(ALL_UNITS) != 12:
        raise C3SScreenError("imported E1 users/lineages drifted")
    if set(WORLDS).intersection(e1.WORLDS) or set(WORLDS).intersection(f2.WORLDS):
        raise C3SScreenError("C3S worlds collide with an E1/F2 world")
    for lineage in LINEAGES:
        try:
            f2._validate_lineage_authority(lineage)
        except f2.F2Error as error:
            raise C3SScreenError(f"lineage {lineage} authority failed: {error}") from error
    try:
        frozen_inputs = e1.prereg_tle_bindings()
        process = e1.process_bindings()
    except e1.E1Error as error:
        raise C3SScreenError(str(error)) from error
    return {
        "contract": contract,
        "static_panel": panel_bindings(DEFAULT_HORIZON),
        "lineage_authorities": f2.lineage_authority_bindings(),
        **frozen_inputs,
        "process_environment": process,
        "eta_ref": {
            "config": {"path": str(CONFIG_PATH.resolve()), "sha256": file_sha256(CONFIG_PATH)},
            "exact": fraction_payload(c3s_policy.load_eta_ref(CONFIG_PATH)),
        },
    }


def _validate_sealed(path: Path, *, digest: str, field: str) -> None:
    target = Path(path)
    sidecar = target.with_suffix(".sha256")
    if (
        target.is_symlink() or not target.is_file() or target.stat().st_mode & 0o777 != 0o444
        or sidecar.is_symlink() or not sidecar.is_file() or sidecar.stat().st_mode & 0o777 != 0o444
        or sidecar.read_text(encoding="ascii").split() != [digest, target.name]
        or file_sha256(target) != digest
    ):
        raise C3SScreenError(f"{field} is not sealed mode-0444 with matching sidecar")


def validate_preflight_manifest(path: Path) -> tuple[dict[str, Any], str]:
    target = Path(path)
    payload = load_json(target, field="C3S preflight manifest")
    expected = {
        "schema": PREFLIGHT_SCHEMA, "status": "FROZEN_PREFLIGHT",
        "claim_ceiling": CLAIM_CEILING, **validate_static_bindings(),
        "code_files": expected_code_bindings(),
    }
    if payload != expected:
        raise C3SScreenError("C3S preflight disagrees with exact bindings/code")
    digest = file_sha256(target)
    _validate_sealed(target, digest=digest, field="C3S preflight manifest")
    return payload, digest


AUTHORITY_KEYS = {
    "schema", "status", "claim_ceiling", "contract", "preflight_manifest",
    "lineage_authorities", "preregistration", "tle_archive", "code_files",
    "execution", "output_root", "launch_arguments", "test_split_opened",
    "episode_training", "learner_update", "efficacy_claim",
}


def validate_launch_authority(
    path: Path, *, preflight_path: Path, preflight_sha256: str,
    output_root: Path, horizon: int, launch_arguments: Sequence[str],
    target: UnitKey | None,
) -> dict[str, Any]:
    if horizon != DEFAULT_HORIZON:
        raise C3SScreenError("formal authority requires the contract-fixed 30-step horizon")
    authority_path = Path(path)
    payload = load_json(authority_path, field="C3S launch authority")
    digest = file_sha256(authority_path)
    _validate_sealed(authority_path, digest=digest, field="C3S launch authority")
    if set(payload) != AUTHORITY_KEYS:
        raise C3SScreenError("launch authority keys differ from the exact schema")
    static = validate_static_bindings()
    expected = {
        "schema": LAUNCH_AUTHORITY_SCHEMA, "status": "FROZEN_LAUNCH_AUTHORITY",
        "claim_ceiling": CLAIM_CEILING,
        "contract": static["contract"],
        "preflight_manifest": {
            "path": str(Path(preflight_path).resolve()), "sha256": preflight_sha256,
        },
        "lineage_authorities": static["lineage_authorities"],
        "preregistration": static["preregistration"],
        "tle_archive": static["tle_archive"],
        "code_files": expected_code_bindings(),
        "execution": {
            "mode": "unit" if target is not None else "merge",
            "unit": None if target is None else target.as_dict(),
            "panel": panel_bindings(horizon),
            "eta_ref_exact": fraction_payload(c3s_policy.load_eta_ref(CONFIG_PATH)),
        },
        "output_root": str(_local(output_root, field="output root")),
        "launch_arguments": list(launch_arguments),
        "test_split_opened": False, "episode_training": False,
        "learner_update": False, "efficacy_claim": False,
    }
    if payload != expected:
        raise C3SScreenError("launch authority does not bind this exact invocation")
    return payload


def authority_common_binding(authority: Mapping[str, object]) -> dict[str, object]:
    """Return the fields intentionally common to unit and merge authorities."""

    execution = authority.get("execution")
    if not isinstance(execution, Mapping):
        raise C3SScreenError("launch authority execution binding is absent")
    return {
        "contract": authority.get("contract"),
        "preflight_manifest": authority.get("preflight_manifest"),
        "lineage_authorities": authority.get("lineage_authorities"),
        "preregistration": authority.get("preregistration"),
        "tle_archive": authority.get("tle_archive"),
        "code_files": authority.get("code_files"),
        "panel": execution.get("panel"),
        "eta_ref_exact": execution.get("eta_ref_exact"),
        "output_root": authority.get("output_root"),
    }


def write_once_with_sidecar(
    path: Path, payload: Mapping[str, object],
) -> tuple[Path, Path, str]:
    target = _local(path, field="write-once artifact")
    sidecar = target.with_suffix(".sha256")
    if target.exists() or target.is_symlink() or sidecar.exists() or sidecar.is_symlink():
        raise C3SScreenError("refusing to overwrite write-once artifact or sidecar")
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = canonical_bytes(payload) + b"\n"
    try:
        with target.open("xb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        target.chmod(0o444)
        digest = file_sha256(target)
        with sidecar.open("xb") as handle:
            handle.write(f"{digest}  {target.name}\n".encode("ascii"))
            handle.flush()
            os.fsync(handle.fileno())
        sidecar.chmod(0o444)
        _validate_sealed(target, digest=digest, field="published artifact")
    except Exception:
        # Never remove the primary after publication: it is write-once evidence.
        raise
    return target, sidecar, digest


def _step_metric(outcome: Any, interval_s: float) -> dict[str, object]:
    try:
        rates = np.asarray(outcome.link_rate_bps, dtype=np.float64)
        power = float(outcome.system_power_w)
        served = int(outcome.resolution.served_count)
    except (AttributeError, TypeError, ValueError) as error:
        raise C3SScreenError("committed outcome lacks physical endpoint metrics") from error
    if (
        rates.shape != (USERS,) or not np.all(np.isfinite(rates)) or np.any(rates < 0)
        or not math.isfinite(power) or power <= 0 or not 0 <= served <= USERS
    ):
        raise C3SScreenError("committed physical endpoint metric is invalid")
    bits = interval_s * math.fsum(float(value) for value in rates)
    energy = interval_s * power
    return {
        "bits_hex": bits.hex(), "energy_j_hex": energy.hex(),
        "served": served, "opportunities": USERS,
    }


def run_arm_trajectory(
    *, environment: Any, env_rng: np.random.Generator,
    mobility_rng: np.random.Generator, horizon: int,
    selector: Callable[[Any, Any, np.random.Generator], np.ndarray],
) -> dict[str, object]:
    """Run one arm in its own environment; useful as the synthetic test seam."""

    _states, _masks, observation = environment.reset(env_rng, mobility_rng)
    step_env = environment.environment
    try:
        native = __import__(
            "mcrl.runtime.ee_axis_state", fromlist=["encode_ee_axis_state"]
        ).encode_ee_axis_state(step_env, observation)
        initial_sha = native.state_sha256
        interval_s = float(step_env.driver.config.ephemeris.time_step_s)
    except (AttributeError, TypeError, ValueError) as error:
        raise C3SScreenError("initial environment state cannot be authenticated") from error
    steps: list[dict[str, object]] = []
    decision_wall: list[str] = []
    action_trace = hashlib.sha256()
    for step_index in range(horizon):
        if int(observation.step_index) != step_index:
            raise C3SScreenError("arm trajectory reached the wrong decision index")
        decision_started = time.perf_counter()
        actions = np.asarray(selector(step_env, observation, env_rng))
        decision_wall.append((time.perf_counter() - decision_started).hex())
        masks = np.asarray(observation.masks)
        if actions.dtype.kind not in "iu" or actions.shape != (USERS,):
            raise C3SScreenError("selector did not return a complete 100-user action vector")
        if masks.dtype != np.bool_ or masks.shape != (USERS, f1.NUM_ACTIONS):
            raise C3SScreenError("current action mask is malformed")
        rows = np.arange(USERS)
        eligible = np.any(masks, axis=1)
        if (
            np.any(actions[eligible] < 0)
            or np.any(actions[eligible] >= f1.NUM_ACTIONS)
            or np.any(~masks[rows[eligible], actions[eligible]])
            or np.any(actions[~eligible] != f1.NO_OP_ACTION)
        ):
            raise C3SScreenError("selector returned an illegal action")
        selected = actions.astype(np.int64, copy=True)
        action_trace.update(selected.tobytes(order="C"))
        result = environment.step(selected, env_rng)
        outcome = environment.last_outcome
        metric = _step_metric(outcome, interval_s)
        steps.append({"step_index": step_index, **metric})
        done = bool(getattr(outcome, "done", getattr(result, "done", False)))
        if step_index < horizon - 1 and done:
            raise C3SScreenError("arm trajectory ended before the declared horizon")
        if step_index == horizon - 1 and not done:
            raise C3SScreenError("arm trajectory did not end at the declared horizon")
        observation = outcome.observation
    return {
        "initial_state_sha256": initial_sha,
        "action_trace_sha256": action_trace.hexdigest(),
        "decision_wall_seconds_hex": decision_wall,
        "steps": steps,
    }


def _make_environment(archive: Any, *, horizon: int) -> Any:
    from mcrl.env.ephemeris import TRAIN, BlockAlternatingSplit, EpisodeStartSampler
    from mcrl.env.mobility import MobilityConfig
    from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
    from mcrl.env.step import StepEnvironment
    from mcrl.runtime.trainer_env import TrainerEnvironment

    driver = ScenarioDriver(
        archive,
        ScenarioConfig(mobility=MobilityConfig(num_users=USERS), steps_per_episode=horizon),
    )
    split = BlockAlternatingSplit.for_archive(archive)
    sampler = EpisodeStartSampler.for_archive(archive, split, TRAIN)
    return TrainerEnvironment(StepEnvironment(driver), sampler)


def execute_physical_unit(key: UnitKey, *, horizon: int) -> dict[str, object]:
    """Execute BASE, full, and lite from fresh matched initial environments."""

    from mcrl.env.keyed_fading import KeyedFadingField
    from mcrl.runtime.prereg import read_prereg
    from mcrl.runtime.training_pipeline import _evaluation_rngs

    key.verify()
    record = read_prereg(f1.PREREG_PATH)
    if record.digest != f1.PREREG_RECORD_DIGEST:
        raise C3SScreenError("TRAIN PREREG semantic digest changed")
    physical, server = f1._runtime_modules()
    frozen = f2._load_frozen_heads(key.lineage)
    q_before = (physical._parameter_sha256(frozen.q1), physical._parameter_sha256(frozen.q2))
    with tempfile.TemporaryDirectory(prefix=f"c3s-{key.slug}-tle-", dir=os.environ.get("TMPDIR")) as temporary:
        archive = server._freeze_archive(
            record, CANONICAL_TLE_ROOT, Path(temporary) / "frozen", physical
        )
        trajectories: dict[str, dict[str, object]] = {}
        adapters: dict[str, c3s_policy.C3SPolicyAdapter] = {}
        for arm in ARMS:
            environment = _make_environment(archive, horizon=horizon)
            field = KeyedFadingField.from_components(FIELD_COMPONENT, key.world)
            environment.environment._fading_field = field
            rngs = tuple(_evaluation_rngs(key.world))
            if len(rngs) < 2:
                raise C3SScreenError("canonical RNG factory lacks two streams")
            if arm == "BASE":
                def selector(step_env: Any, observation: Any, _rng: np.random.Generator) -> np.ndarray:
                    return e1._q12_surface_base_only(
                        physical, frozen, step_env, observation
                    )[2]
            else:
                adapter = c3s_policy.C3SPolicyAdapter(
                    physical=physical, frozen=frozen, catalog=arm.lower()
                )
                adapters[arm] = adapter
                selector = adapter.select_actions
            trajectories[arm] = run_arm_trajectory(
                environment=environment, env_rng=rngs[0], mobility_rng=rngs[1],
                horizon=horizon, selector=selector,
            )
        if len({trajectories[arm]["initial_state_sha256"] for arm in ARMS}) != 1:
            raise C3SScreenError("matched arms do not share the same initial state")
        q_after = (physical._parameter_sha256(frozen.q1), physical._parameter_sha256(frozen.q2))
        if q_after != q_before:
            raise C3SScreenError("authenticated Q1/Q2 parameters changed during inference")
        decisions = {arm: adapters[arm].decision_records for arm in COORDINATOR_ARMS}
        changes = {
            arm: sum(bool(row["action_changed"]) for row in decisions[arm])
            for arm in COORDINATOR_ARMS
        }
        return {
            "schema": UNIT_RECEIPT_SCHEMA, "status": "COMPLETE",
            "outcome": "C3S_SCREEN_UNIT_COMPLETE", "claim_ceiling": CLAIM_CEILING,
            "unit": key.as_dict(), "horizon": horizon, "users": USERS,
            "field_component": FIELD_COMPONENT,
            "field_root_digest": KeyedFadingField.from_components(
                FIELD_COMPONENT, key.world
            ).root_digest,
            "lineage_authority": f2.lineage_authority_bindings()[LINEAGES.index(key.lineage)],
            "eta_ref_exact": fraction_payload(adapters["FULL"].eta_ref),
            "arms": trajectories,
            "decisions_by_arm": decisions,
            "action_changes_by_arm": changes,
            "integrity": True, "test_split_opened": False,
            "episode_training": False, "learner_update": False, "efficacy_claim": False,
        }


def _exact_hex(value: object, *, field: str, positive: bool = False) -> Fraction:
    try:
        parsed = float.fromhex(str(value))
    except (ValueError, OverflowError) as error:
        raise C3SScreenError(f"{field} is not a float hex") from error
    if not math.isfinite(parsed) or (positive and parsed <= 0) or (not positive and parsed < 0):
        raise C3SScreenError(f"{field} is outside its domain")
    return Fraction.from_float(parsed)


def pool_unit_receipts(receipts: Sequence[Mapping[str, object]]) -> dict[str, object]:
    totals = {
        arm: {"bits": Fraction(0), "energy": Fraction(0), "served": 0, "opportunities": 0}
        for arm in ARMS
    }
    changes = {arm: 0 for arm in COORDINATOR_ARMS}
    decisions = {arm: 0 for arm in COORDINATOR_ARMS}
    for receipt in receipts:
        arms = receipt.get("arms")
        if not isinstance(arms, Mapping) or set(arms) != set(ARMS):
            raise C3SScreenError("unit receipt arm coverage is malformed")
        receipt_changes = receipt.get("action_changes_by_arm")
        receipt_decisions = receipt.get("decisions_by_arm")
        if (
            not isinstance(receipt_changes, Mapping)
            or set(receipt_changes) != set(COORDINATOR_ARMS)
            or not isinstance(receipt_decisions, Mapping)
            or set(receipt_decisions) != set(COORDINATOR_ARMS)
        ):
            raise C3SScreenError("unit receipt lacks per-coordinator records")
        for arm in COORDINATOR_ARMS:
            arm_decisions = receipt_decisions[arm]
            arm_changes = receipt_changes[arm]
            if (
                not isinstance(arm_decisions, list) or type(arm_changes) is not int
                or not 0 <= arm_changes <= len(arm_decisions)
            ):
                raise C3SScreenError("unit per-coordinator counts are malformed")
            decisions[arm] += len(arm_decisions)
            changes[arm] += arm_changes
        for arm in ARMS:
            trajectory = arms[arm]
            if not isinstance(trajectory, Mapping) or not isinstance(trajectory.get("steps"), list):
                raise C3SScreenError("unit trajectory is malformed")
            for step in trajectory["steps"]:
                if not isinstance(step, Mapping):
                    raise C3SScreenError("unit step is malformed")
                totals[arm]["bits"] += _exact_hex(step.get("bits_hex"), field="bits")
                totals[arm]["energy"] += _exact_hex(
                    step.get("energy_j_hex"), field="energy", positive=True
                )
                served = step.get("served")
                opportunities = step.get("opportunities")
                if type(served) is not int or type(opportunities) is not int or not 0 <= served <= opportunities:
                    raise C3SScreenError("service counts are malformed")
                totals[arm]["served"] += served
                totals[arm]["opportunities"] += opportunities
    exact: dict[str, dict[str, object]] = {}
    for arm in ARMS:
        row = totals[arm]
        bits = row["bits"]
        energy = row["energy"]
        served = int(row["served"])
        opportunities = int(row["opportunities"])
        assert isinstance(bits, Fraction) and isinstance(energy, Fraction)
        if energy <= 0 or opportunities <= 0:
            raise C3SScreenError("pooled denominator is non-positive")
        exact[arm] = {
            "total_bits": fraction_payload(bits),
            "total_energy_j": fraction_payload(energy),
            "eta": fraction_payload(bits / energy),
            "served": served, "opportunities": opportunities,
            "service": fraction_payload(Fraction(served, opportunities)),
        }
    eta_base = _fraction_from_payload(exact["BASE"]["eta"])
    service_base = _fraction_from_payload(exact["BASE"]["service"])
    dispositions: dict[str, dict[str, object]] = {}
    for arm in COORDINATOR_ARMS:
        reasons: list[str] = []
        if _fraction_from_payload(exact[arm]["eta"]) <= eta_base:
            reasons.append("EE_NOT_STRICTLY_ABOVE_BASE")
        if _fraction_from_payload(exact[arm]["service"]) < service_base - SERVICE_MARGIN:
            reasons.append("SERVICE_MARGIN_FAILED")
        dispositions[arm] = {
            "outcome": f"{OUTCOME_PREFIX[arm]}_{'SUPPORT' if not reasons else 'NO_SUPPORT'}",
            "reasons": reasons,
        }
    return {
        "decisions": dispositions, "arms": exact,
        "counts": {
            "units": len(receipts), "decisions_by_arm": decisions,
            "action_changes_by_arm": changes,
        },
    }


def _fraction_from_payload(value: object) -> Fraction:
    if not isinstance(value, Mapping):
        raise C3SScreenError("exact rational payload is malformed")
    try:
        return Fraction(int(value["numerator"]), int(value["denominator"]))
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
        raise C3SScreenError("exact rational payload is malformed") from error


def invalid_receipt(
    *, scope: str, error: BaseException, key: UnitKey | None,
    preflight_sha256: str, authority_sha256: str,
    producer_common_binding: Mapping[str, object] | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "schema": UNIT_RECEIPT_SCHEMA if key is not None else TERMINAL_RECEIPT_SCHEMA,
        "status": "INVALID_RUN", "outcome": "INVALID_RUN", "scope": scope,
        "claim_ceiling": CLAIM_CEILING,
        "unit": None if key is None else key.as_dict(),
        "preflight_manifest_sha256": preflight_sha256,
        "launch_authority_sha256": authority_sha256,
        "error_type": type(error).__name__,
        "error_sha256": hashlib.sha256(str(error).encode("utf-8")).hexdigest(),
        "integrity": False, "test_split_opened": False,
        "episode_training": False, "learner_update": False, "efficacy_claim": False,
    }
    if producer_common_binding is not None:
        result["producer_common_binding"] = dict(producer_common_binding)
    return result


def incomplete_receipt(
    *, scope: str, error: BaseException, key: UnitKey | None,
    preflight_sha256: str, authority_sha256: str,
    producer_common_binding: Mapping[str, object] | None = None,
) -> dict[str, object]:
    result = invalid_receipt(
        scope=scope, error=error, key=key, preflight_sha256=preflight_sha256,
        authority_sha256=authority_sha256,
        producer_common_binding=producer_common_binding,
    )
    result.update({"status": "INCOMPLETE", "outcome": "INCOMPLETE", "integrity": None})
    return result


def _unit_path(root: Path, key: UnitKey) -> Path:
    return Path(root) / "units" / key.slug / UNIT_RECEIPT_NAME


def _publish_unit(root: Path, key: UnitKey, payload: Mapping[str, object]) -> Path:
    destination = _local(root, field="output root") / "units" / key.slug
    if destination.exists() or destination.is_symlink():
        raise C3SScreenError(f"refusing to overwrite write-once unit {key.slug}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".stage-{key.slug}-", dir=destination.parent))
    try:
        write_once_with_sidecar(stage / UNIT_RECEIPT_NAME, payload)
        stage.chmod(0o555)
        os.rename(stage, destination)
    finally:
        if stage.exists() and not stage.is_symlink():
            stage.chmod(0o755)
            shutil.rmtree(stage)
    return destination / UNIT_RECEIPT_NAME


def execute_unit(
    *, key: UnitKey, output: Path, horizon: int,
    preflight_sha256: str, authority_sha256: str,
    producer_common_binding: Mapping[str, object],
) -> tuple[Path, bool]:
    try:
        payload = execute_physical_unit(key, horizon=horizon)
        payload["preflight_manifest_sha256"] = preflight_sha256
        payload["launch_authority_sha256"] = authority_sha256
        payload["producer_common_binding"] = dict(producer_common_binding)
        return _publish_unit(output, key, payload), True
    except (KeyboardInterrupt, C3SScreenIncomplete) as error:
        payload = incomplete_receipt(
            scope="unit", error=error, key=key, preflight_sha256=preflight_sha256,
            authority_sha256=authority_sha256,
            producer_common_binding=producer_common_binding,
        )
        return _publish_unit(output, key, payload), False
    except Exception as error:
        payload = invalid_receipt(
            scope="unit", error=error, key=key, preflight_sha256=preflight_sha256,
            authority_sha256=authority_sha256,
            producer_common_binding=producer_common_binding,
        )
        return _publish_unit(output, key, payload), False


def _load_complete_units(
    root: Path, *, horizon: int, preflight_sha256: str,
    producer_common_binding: Mapping[str, object],
) -> tuple[list[dict[str, Any]], list[dict[str, object]]]:
    receipts: list[dict[str, Any]] = []
    bindings: list[dict[str, object]] = []
    missing = 0
    for key in ALL_UNITS:
        path = _unit_path(root, key)
        if not path.exists() and not path.is_symlink():
            missing += 1
            continue
        digest = file_sha256(path)
        _validate_sealed(path, digest=digest, field=f"unit {key.slug}")
        receipt = load_json(path, field=f"unit {key.slug}")
        arms = receipt.get("arms")
        decisions = receipt.get("decisions_by_arm")
        changes = receipt.get("action_changes_by_arm")
        expected_root = e1.KeyedFadingField.from_components(
            FIELD_COMPONENT, key.world
        ).root_digest
        trajectory_ok = isinstance(arms, Mapping) and set(arms) == set(ARMS)
        if trajectory_ok:
            for arm in ARMS:
                trajectory = arms[arm]
                trajectory_ok = (
                    isinstance(trajectory, Mapping)
                    and isinstance(trajectory.get("steps"), list)
                    and len(trajectory["steps"]) == horizon
                    and isinstance(trajectory.get("decision_wall_seconds_hex"), list)
                    and len(trajectory["decision_wall_seconds_hex"]) == horizon
                    and [
                        row.get("step_index") for row in trajectory["steps"]
                        if isinstance(row, Mapping)
                    ] == list(range(horizon))
                )
                if not trajectory_ok:
                    break
        if (
            receipt.get("schema") != UNIT_RECEIPT_SCHEMA
            or receipt.get("status") != "COMPLETE"
            or receipt.get("outcome") != "C3S_SCREEN_UNIT_COMPLETE"
            or receipt.get("unit") != key.as_dict()
            or receipt.get("horizon") != horizon
            or receipt.get("users") != USERS
            or receipt.get("field_component") != FIELD_COMPONENT
            or receipt.get("field_root_digest") != expected_root
            or receipt.get("lineage_authority")
            != f2.lineage_authority_bindings()[LINEAGES.index(key.lineage)]
            or not trajectory_ok
            or len({arms[arm].get("initial_state_sha256") for arm in ARMS}) != 1
            or not isinstance(decisions, Mapping)
            or set(decisions) != set(COORDINATOR_ARMS)
            or not isinstance(changes, Mapping)
            or set(changes) != set(COORDINATOR_ARMS)
            or any(not isinstance(decisions[arm], list) or len(decisions[arm]) != horizon
                   for arm in COORDINATOR_ARMS)
            or any(
                changes[arm] != sum(
                    bool(row.get("action_changed"))
                    for row in decisions[arm] if isinstance(row, Mapping)
                )
                for arm in COORDINATOR_ARMS
            )
            or any(
                changes[arm] == 0 and (
                    arms["BASE"].get("action_trace_sha256")
                    != arms[arm].get("action_trace_sha256")
                    or arms["BASE"].get("steps") != arms[arm].get("steps")
                )
                for arm in COORDINATOR_ARMS
            )
            or receipt.get("preflight_manifest_sha256") != preflight_sha256
            or receipt.get("producer_common_binding") != dict(producer_common_binding)
            or receipt.get("integrity") is not True
        ):
            raise C3SScreenError(f"unit {key.slug} is invalid or incomplete")
        receipts.append(receipt)
        bindings.append({"unit": key.as_dict(), "path": str(path.relative_to(root)), "sha256": digest})
    if missing:
        raise MergeWaiting(missing)
    return receipts, bindings


def coordinator_timing_summary(
    receipts: Sequence[Mapping[str, object]], *, arm: str,
) -> dict[str, object]:
    if arm not in COORDINATOR_ARMS:
        raise C3SScreenError("coordinator timing arm must be FULL or LITE")
    wall: list[float] = []
    catalogs: list[int] = []
    unique_evaluations: list[int] = []
    peak_rss = 0
    for receipt in receipts:
        decisions_by_arm = receipt.get("decisions_by_arm")
        if not isinstance(decisions_by_arm, Mapping):
            raise C3SScreenError("unit receipt lacks per-coordinator timing")
        for row in decisions_by_arm[arm]:
            if not isinstance(row, Mapping):
                raise C3SScreenError("C3S decision timing row is malformed")
            try:
                seconds = float.fromhex(str(row["wall_seconds_hex"]))
                catalog = int(row["catalog_size"])
                rss = int(row["peak_rss_kib"])
                unique = int(row["unique_nominal_evaluations"])
                phases = row["phase_wall_seconds_hex"]
                required_phases = {
                    "q_inference", "base_nominal_evaluation", "enumeration",
                    "remaining_nominal_evaluations", "catalog_total", "selection",
                }
                if not isinstance(phases, Mapping) or set(phases) != required_phases:
                    raise ValueError("phase keys drifted")
                phase_seconds = [float.fromhex(str(phases[name])) for name in required_phases]
                counts = row["profile_counts"]
                if (
                    row.get("catalog") != arm.lower()
                    or not isinstance(counts, Mapping)
                    or set(counts) != {"base", "unilateral", "joint"}
                    or sum(int(counts[name]) for name in counts) != catalog
                ):
                    raise ValueError("profile census drifted")
            except (KeyError, TypeError, ValueError, OverflowError) as error:
                raise C3SScreenError("C3S decision timing row is malformed") from error
            if (
                not math.isfinite(seconds) or seconds < 0
                or any(not math.isfinite(value) or value < 0 for value in phase_seconds)
                or catalog < 1 or not 1 <= unique <= catalog or rss < 0
            ):
                raise C3SScreenError("C3S decision timing value is invalid")
            wall.append(seconds)
            catalogs.append(catalog)
            unique_evaluations.append(unique)
            peak_rss = max(peak_rss, rss)
    if not wall:
        raise C3SScreenError("C3S decision timing summary is empty")
    ordered = sorted(wall)
    p95 = ordered[math.ceil(0.95 * len(ordered)) - 1]
    return {
        "decisions": len(wall),
        "wall_seconds": {
            "mean_hex": (math.fsum(wall) / len(wall)).hex(),
            "median_hex": ((ordered[(len(ordered) - 1) // 2] + ordered[len(ordered) // 2]) / 2).hex(),
            "p95_nearest_rank_hex": p95.hex(), "maximum_hex": max(wall).hex(),
        },
        "catalog_size": {
            "minimum": min(catalogs), "maximum": max(catalogs),
            "mean": math.fsum(catalogs) / len(catalogs),
        },
        "unique_nominal_evaluations": {
            "minimum": min(unique_evaluations), "maximum": max(unique_evaluations),
            "mean": math.fsum(unique_evaluations) / len(unique_evaluations),
        },
        "peak_rss_kib": peak_rss,
    }


def per_arm_wall_timing(
    receipts: Sequence[Mapping[str, object]],
) -> dict[str, dict[str, object]]:
    """Summarize like-for-like selector wall time for all three arms."""

    result: dict[str, dict[str, object]] = {}
    for arm in ARMS:
        wall: list[float] = []
        for receipt in receipts:
            arms = receipt.get("arms")
            if not isinstance(arms, Mapping) or not isinstance(arms.get(arm), Mapping):
                raise C3SScreenError("unit receipt lacks arm timing")
            raw = arms[arm].get("decision_wall_seconds_hex")
            if not isinstance(raw, list):
                raise C3SScreenError("unit arm timing is malformed")
            try:
                wall.extend(float.fromhex(str(value)) for value in raw)
            except (TypeError, ValueError, OverflowError) as error:
                raise C3SScreenError("unit arm timing is malformed") from error
        if not wall or any(not math.isfinite(value) or value < 0 for value in wall):
            raise C3SScreenError("unit arm timing is empty or invalid")
        ordered = sorted(wall)
        result[arm] = {
            "decisions": len(wall),
            "mean_hex": (math.fsum(wall) / len(wall)).hex(),
            "median_hex": (
                (ordered[(len(ordered) - 1) // 2] + ordered[len(ordered) // 2]) / 2
            ).hex(),
            "p95_nearest_rank_hex": ordered[math.ceil(0.95 * len(ordered)) - 1].hex(),
            "maximum_hex": max(wall).hex(),
        }
    return result


def descriptive_breakdowns(
    receipts: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for name, values in (("per_world", WORLDS), ("per_lineage", LINEAGES)):
        rows: dict[str, object] = {}
        field = "world" if name == "per_world" else "lineage"
        for value in values:
            subset = [receipt for receipt in receipts if receipt["unit"][field] == value]  # type: ignore[index]
            pooled = pool_unit_receipts(subset)
            rows[str(value)] = {
                "arms": pooled["arms"],
                "action_changes_by_arm": pooled["counts"]["action_changes_by_arm"],
                "units": len(subset),
            }
        result[name] = rows
    return result


def full_vs_lite_comparison(
    pooled: Mapping[str, object], timing: Mapping[str, object],
) -> list[dict[str, object]]:
    """Build the declared descriptive, non-decisional comparison table."""

    arms = pooled.get("arms")
    counts = pooled.get("counts")
    if not isinstance(arms, Mapping) or not isinstance(counts, Mapping):
        raise C3SScreenError("pooled full/lite comparison inputs are malformed")
    changes = counts.get("action_changes_by_arm")
    if not isinstance(changes, Mapping):
        raise C3SScreenError("pooled action-change comparison is malformed")
    rows: list[dict[str, object]] = []
    for metric in ("eta", "service"):
        full = _fraction_from_payload(arms["FULL"][metric])
        lite = _fraction_from_payload(arms["LITE"][metric])
        rows.append({
            "metric": metric, "FULL": fraction_payload(full),
            "LITE": fraction_payload(lite),
            "full_minus_lite": fraction_payload(full - lite),
        })
    rows.append({
        "metric": "action_changes", "FULL": int(changes["FULL"]),
        "LITE": int(changes["LITE"]),
        "full_minus_lite": int(changes["FULL"]) - int(changes["LITE"]),
    })
    rows.append({
        "metric": "selector_wall_seconds", "FULL": timing["FULL"],
        "LITE": timing["LITE"], "comparison_role": "DESCRIPTIVE_NON_DECISIONAL",
    })
    return rows


def execute_merge(
    *, output: Path, horizon: int, preflight_sha256: str, authority_sha256: str,
    producer_common_binding: Mapping[str, object],
) -> tuple[Path, bool]:
    root = _local(output, field="output root")
    terminal = root / TERMINAL_RECEIPT_NAME
    try:
        receipts, bindings = _load_complete_units(
            root, horizon=horizon, preflight_sha256=preflight_sha256,
            producer_common_binding=producer_common_binding,
        )
        pooled = pool_unit_receipts(receipts)
        arm_timing = per_arm_wall_timing(receipts)
        coordinator_timing = {
            arm: coordinator_timing_summary(receipts, arm=arm)
            for arm in COORDINATOR_ARMS
        }
        expected_opportunities = len(ALL_UNITS) * horizon * USERS
        if (
            pooled["counts"]["units"] != 12
            or any(
                pooled["counts"]["decisions_by_arm"][arm] != 12 * horizon
                for arm in COORDINATOR_ARMS
            )
            or any(
                pooled["arms"][arm]["opportunities"] != expected_opportunities
                for arm in ARMS
            )
        ):
            raise C3SScreenError("merge coverage is incomplete")
        payload = {
            "schema": TERMINAL_RECEIPT_SCHEMA, "status": "COMPLETE",
            "outcome": "C3S_THREE_ARM_SCREEN_COMPLETE",
            "decisions": pooled["decisions"],
            "progression_rule": PROGRESSION_RULE,
            "progression_rule_role": "PREDECLARED_REPORTING_ONLY_NO_OUTCOME_SELECTION_LOGIC",
            "claim_ceiling": CLAIM_CEILING, "panel": panel_bindings(horizon),
            "eta_ref_exact": fraction_payload(c3s_policy.load_eta_ref(CONFIG_PATH)),
            "pooled_exact": pooled["arms"], "counts": pooled["counts"],
            **descriptive_breakdowns(receipts),
            "per_arm_decision_wall_timing": arm_timing,
            "coordinator_timing": coordinator_timing,
            "full_vs_lite_comparison": full_vs_lite_comparison(pooled, arm_timing),
            "unit_receipts": bindings,
            "preflight_manifest_sha256": preflight_sha256,
            "launch_authority_sha256": authority_sha256,
            "producer_common_binding": dict(producer_common_binding),
            "integrity": True, "test_split_opened": False,
            "episode_training": False, "learner_update": False, "efficacy_claim": False,
        }
        write_once_with_sidecar(terminal, payload)
        return terminal, True
    except MergeWaiting as error:
        payload = incomplete_receipt(
            scope="merge", error=error, key=None,
            preflight_sha256=preflight_sha256,
            authority_sha256=authority_sha256,
            producer_common_binding=producer_common_binding,
        )
        incomplete_root = root / "incomplete"
        for sequence in range(1, 1_000_000):
            path = incomplete_root / f"merge-{sequence:06d}.json"
            try:
                write_once_with_sidecar(path, payload)
            except C3SScreenError as collision:
                if "refusing to overwrite" in str(collision):
                    continue
                raise
            error.receipt = path
            break
        raise
    except Exception as error:
        payload = invalid_receipt(
            scope="merge", error=error, key=None, preflight_sha256=preflight_sha256,
            authority_sha256=authority_sha256,
            producer_common_binding=producer_common_binding,
        )
        write_once_with_sidecar(root / GLOBAL_INVALIDATION_NAME, payload)
        return root / GLOBAL_INVALIDATION_NAME, False


def estimate(*, units: int) -> dict[str, object]:
    """Estimate all three arms at the two requested planning horizons."""

    if type(units) is not int or units < 1:
        raise C3SScreenError("estimate units must be a positive exact integer")
    if file_sha256(S0_RESULT) != S0_RESULT_SHA256 or file_sha256(E1_LEDGER) != E1_LEDGER_SHA256:
        raise C3SScreenError("E1/S0 timing basis digest changed")
    result = load_json(S0_RESULT, field="S0 timing result")
    ledger = load_json(E1_LEDGER, field="E1 timing ledger")
    anchors = result.get("anchors")
    if not isinstance(anchors, list) or len(anchors) != 120:
        raise C3SScreenError("S0 timing basis lacks 120 anchors")
    candidate_rows = sum(
        int(row["profile_counts"]["base"])
        + int(row["profile_counts"]["unilateral"])
        + int(row["profile_counts"]["joint"])
        for row in anchors
    )
    unique_rows = sum(
        int(row["profile_counts"]["unique_action_vectors_evaluated"])
        for row in anchors
    )
    s0_seconds = float(result["timing"]["unit_worker_seconds"])
    e1_seconds = float.fromhex(str(ledger["unit_charged_worker_seconds_hex"]))
    per_decision = Fraction(unique_rows, len(anchors))
    s0_rate = s0_seconds / unique_rows
    e1_rate = e1_seconds / candidate_rows
    full_seconds_per_decision = float(per_decision) * s0_rate + (
        candidate_rows / len(anchors)
    ) * e1_rate
    lite_ratio = Fraction(1, 10)
    horizons: dict[str, object] = {}
    for horizon in (30, 100):
        full_evaluations = per_decision * horizon * units
        lite_evaluations = full_evaluations * lite_ratio
        full_hours = full_seconds_per_decision * horizon * units / 3600.0
        horizons[str(horizon)] = {
            "horizon": horizon,
            "episodes": units * len(ARMS),
            "planning_cost_ratio_full_to_lite": 10.0,
            "arms": {
                "BASE": {
                    "projected_nominal_evaluations_exact": fraction_payload(Fraction(0)),
                    "worker_hours": 0.0,
                    "note": "Q inference and committed execution only; negligible in catalog estimate",
                },
                "FULL": {
                    "projected_nominal_evaluations_exact": fraction_payload(full_evaluations),
                    "worker_hours": full_hours,
                },
                "LITE": {
                    "projected_nominal_evaluations_exact": fraction_payload(lite_evaluations),
                    "worker_hours": full_hours * float(lite_ratio),
                    "planning_cost_relative_to_full": fraction_payload(lite_ratio),
                },
            },
        }
    return {
        "schema": f"{SCHEMA}-estimate", "units": units,
        "world_domains": list(WORLD_DOMAINS), "worlds": list(WORLDS),
        "horizons": horizons,
        "full_nominal_evaluations_per_decision_exact": fraction_payload(per_decision),
        "lite_planning_rule": "ONE_TENTH_OF_FULL_PER_ADDENDUM_A_APPROXIMATE_COST_TARGET",
        "basis": {
            "s0_result_sha256": S0_RESULT_SHA256,
            "e1_ledger_sha256": E1_LEDGER_SHA256,
            "observed_anchors": len(anchors), "observed_candidate_rows": candidate_rows,
            "observed_unique_action_vectors": unique_rows,
            "s0_worker_seconds": s0_seconds, "e1_worker_seconds": e1_seconds,
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-manifest", type=Path, default=DEFAULT_PREFLIGHT)
    parser.add_argument("--launch-authority", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--horizon", type=int, default=DEFAULT_HORIZON)
    parser.add_argument(
        "--unit", metavar="WORLD:LINEAGE",
        help="run BASE, FULL, then LITE sequentially for one matched unit",
    )
    parser.add_argument("--merge", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--estimate", action="store_true")
    parser.add_argument("--estimate-units", type=int, default=12)
    return parser


def run(args: argparse.Namespace) -> dict[str, object]:
    if args.estimate:
        return {"mode": "estimate", "estimate": estimate(units=args.estimate_units)}
    sealed_contract_binding()  # The prospective contract is always the first launch gate.
    _preflight, preflight_sha = validate_preflight_manifest(args.preflight_manifest)
    if args.dry_run:
        return {"mode": "dry-run", "worlds": list(WORLDS), "panel": panel_bindings(args.horizon)}
    key = UnitKey.parse(args.unit) if args.unit is not None else None
    if args.launch_authority is None:
        raise C3SScreenError("execution requires --launch-authority")
    authority_sha = file_sha256(args.launch_authority)
    authority = validate_launch_authority(
        args.launch_authority, preflight_path=args.preflight_manifest,
        preflight_sha256=preflight_sha, output_root=args.output, horizon=args.horizon,
        launch_arguments=args.raw_launch_arguments, target=key,
    )
    if key is not None:
        receipt, valid = execute_unit(
            key=key, output=args.output, horizon=args.horizon,
            preflight_sha256=preflight_sha, authority_sha256=authority_sha,
            producer_common_binding=authority_common_binding(authority),
        )
        return {"mode": "unit", "receipt": str(receipt), "valid": valid, "worlds": list(WORLDS)}
    receipt, valid = execute_merge(
        output=args.output, horizon=args.horizon, preflight_sha256=preflight_sha,
        authority_sha256=authority_sha,
        producer_common_binding=authority_common_binding(authority),
    )
    return {"mode": "merge", "receipt": str(receipt), "valid": valid, "worlds": list(WORLDS)}


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    args = _parser().parse_args(raw)
    args.raw_launch_arguments = raw
    if not args.estimate and not args.dry_run and (args.unit is None) == (not args.merge):
        print("C3S_SCREEN_ERROR: choose exactly one of --unit WORLD:LINEAGE or --merge", file=sys.stderr)
        return 2
    try:
        if not args.estimate:
            pin_single_thread_runtime()
        result = run(args)
    except MergeWaiting as error:
        receipt = "" if error.receipt is None else f" receipt={error.receipt}"
        print(f"C3S_SCREEN_INCOMPLETE missing_units={error.missing}{receipt}")
        return 3
    except Exception as error:
        print(f"C3S_SCREEN_REFUSED: {error}", file=sys.stderr)
        return 2
    if result["mode"] == "estimate":
        print(json.dumps(result["estimate"], sort_keys=True, indent=2))
        return 0
    if result["mode"] == "dry-run":
        print(
            f"C3S_SCREEN_DRY_RUN_PASS arms={','.join(ARMS)} "
            f"worlds={','.join(str(value) for value in WORLDS)}"
        )
        return 0
    print(
        f"C3S_SCREEN_{str(result['mode']).upper()} worlds="
        f"{','.join(str(value) for value in WORLDS)} receipt={result['receipt']}"
    )
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
