#!/usr/bin/env python3
"""Two-arm FULL2+C3-S confirmatory ladder; never launches implicitly."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import errno
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
from typing import Any, Callable, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SCREEN_DIR = REPO / ".scratch/multi-catfish-v023-c3s-screen"
STAGEC_DIR = REPO / ".scratch/multi-catfish-v023-c1c2-successor-stagec-launch"
STAGEC_PHYSICAL_DIR = REPO / ".scratch/multi-catfish-v023-c1c2-successor-physical-evaluation"
for _path in (HERE, SCREEN_DIR, STAGEC_DIR, STAGEC_PHYSICAL_DIR, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import build_c3s_confirm_world_plan as world_plan  # noqa: E402
from c3s_full2_policy_adapter import (  # noqa: E402
    ARMS, C3SFull2PolicyAdapter, FixedPolicyEpisodeAdapter, load_full2_export,
)


SCHEMA = "multi-catfish-mcrl-v023-c3s-confirmatory-v1"
CLAIM_CEILING = "TRAIN_DEVELOPMENT_FULL2_C3S_CONFIRMATION_NO_LEARNER_NO_TEST_NO_EFFICACY"
CHECKPOINT_EVERY = 100
RUNG_BOUNDARIES = (100, 500, 1500, 3000)
TERMINAL_BOUNDARY = 3000
SERVICE_MARGIN = Fraction(1, 1000)
HELD = "C3S_CONTRIBUTION_HELD"
FALSIFIED = "C3S_CONTRIBUTION_FALSIFIED"
THREAD_ENV = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")
CANONICAL_INTERPRETER = Path("/home/sat/mcrl-leo-handover/.venv/bin/python")
PLAN_CONTRACT_PLACEHOLDER = HERE / "SEALED-C3S-FULL2-CONFIRMATORY-PLAN.md"
DEFAULT_WORLD_PLAN = HERE / "C3S-CONFIRM-WORLD-PLAN-9000.json"
DEFAULT_PREFLIGHT = HERE / "C3S-CONFIRM-PREFLIGHT.json"
BOUNDARY_DONOR = STAGEC_PHYSICAL_DIR / "v023_c1c2_successor_physical_runner.py"
ACCEPTANCE_DONOR = STAGEC_DIR / "accept_stage_c_chunk_equivalence.py"
COMMON_DONOR = STAGEC_DIR / "stagec_common.py"


class ConfirmatoryError(RuntimeError):
    """Provenance, matching, publication, or analysis integrity failed."""


class ConfirmatoryIncomplete(ConfirmatoryError):
    """Required coverage is absent without evidence of scientific invalidity."""


def _load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ConfirmatoryError(f"cannot import donor module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, module)
    spec.loader.exec_module(module)
    return module


def canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as error:
        raise ConfirmatoryError("artifact is not finite canonical ASCII JSON") from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: str | Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise ConfirmatoryError(f"required regular file is absent or symlinked: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: str | Path, *, field: str = "JSON artifact") -> dict[str, Any]:
    source = Path(path)
    try:
        value = json.loads(source.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ConfirmatoryError(f"cannot read {field}: {source}") from error
    if not isinstance(value, dict):
        raise ConfirmatoryError(f"{field} root is not an object")
    return value


def write_once(path: str | Path, payload: Mapping[str, object]) -> str:
    """Atomically publish immutable JSON plus a sibling digest sidecar."""

    target = Path(path)
    sidecar = Path(f"{target}.sha256")
    if target.exists() or target.is_symlink() or sidecar.exists() or sidecar.is_symlink():
        raise ConfirmatoryError(f"refusing to overwrite write-once artifact: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = canonical_bytes(payload) + b"\n"
    descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, target)
    except FileExistsError as error:
        raise ConfirmatoryError(f"artifact was published concurrently: {target}") from error
    finally:
        Path(temporary).unlink(missing_ok=True)
    digest = file_sha256(target)
    sidecar.write_text(f"{digest}  {target.name}\n", encoding="ascii")
    target.chmod(0o444)
    sidecar.chmod(0o444)
    if file_sha256(target) != digest:
        raise ConfirmatoryError("write-once artifact changed after publication")
    return digest


def validate_sealed_file(path: str | Path, expected_sha256: str | None = None) -> dict[str, str]:
    target = Path(path)
    sidecar = Path(f"{target}.sha256")
    try:
        mode_ok = target.stat().st_mode & 0o777 == 0o444 and sidecar.stat().st_mode & 0o777 == 0o444
        digest = file_sha256(target)
        words = sidecar.read_text(encoding="ascii").split()
    except (OSError, UnicodeError, ConfirmatoryError):
        raise ConfirmatoryError(f"sealed file or sidecar is invalid: {target}") from None
    if not mode_ok or words != [digest, target.name] or (expected_sha256 is not None and digest != expected_sha256):
        raise ConfirmatoryError(f"sealed file or sidecar is invalid: {target}")
    return {"path": str(target.resolve()), "sha256": digest}


def pin_runtime() -> dict[str, object]:
    if Path(sys.executable).resolve() != CANONICAL_INTERPRETER.resolve():
        raise ConfirmatoryError(f"formal execution requires interpreter {CANONICAL_INTERPRETER}")
    if any(os.environ.get(name) != "1" for name in THREAD_ENV):
        raise ConfirmatoryError("all OMP/BLAS thread variables must equal 1")
    import torch

    try:
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
    except RuntimeError:
        if torch.get_num_threads() != 1 or torch.get_num_interop_threads() != 1:
            raise ConfirmatoryError("Torch could not be pinned to one thread") from None
    if torch.get_num_threads() != 1 or torch.get_num_interop_threads() != 1:
        raise ConfirmatoryError("Torch one-thread pins did not take effect")
    return {
        "interpreter": str(Path(sys.executable).resolve()),
        "threads": {name: 1 for name in THREAD_ENV},
        "torch_num_threads": 1,
        "torch_num_interop_threads": 1,
        "torch_version": torch.__version__,
        "numpy_version": np.__version__,
    }


def _float(value: object, *, field: str, positive: bool = False) -> float:
    if isinstance(value, str) and value.startswith(("0x", "-0x")):
        parsed = float.fromhex(value)
    else:
        try:
            parsed = float(value)
        except (TypeError, ValueError, OverflowError) as error:
            raise ConfirmatoryError(f"{field} is not a float") from error
    if not math.isfinite(parsed) or (positive and parsed <= 0) or (not positive and parsed < 0):
        raise ConfirmatoryError(f"{field} is outside its domain")
    return parsed


def validate_episode(receipt: Mapping[str, object], *, arm: str | None = None) -> dict[str, Any]:
    expected_arm = receipt.get("arm") if arm is None else arm
    required = {
        "schema", "status", "arm", "episode_index", "world_id", "world_seed",
        "world_domain",
        "field_root_digest", "initial_state_sha256", "policy_binding_sha256",
        "total_bits", "total_energy_j", "served_user_steps",
        "service_opportunities", "action_trace_sha256", "plan_sha256",
    }
    if set(receipt) != required or receipt.get("schema") != f"{SCHEMA}-episode-receipt" or receipt.get("status") != "COMPLETE":
        raise ConfirmatoryError("episode receipt schema/status drifted")
    if expected_arm not in ARMS or receipt.get("arm") != expected_arm:
        raise ConfirmatoryError("episode arm drifted")
    index = receipt.get("episode_index")
    domain = receipt.get("world_domain")
    opportunities = receipt.get("service_opportunities")
    served = receipt.get("served_user_steps")
    if (
        type(index) is not int or index < 1
        or not isinstance(domain, str)
        or type(receipt.get("world_seed")) is not int
        or type(opportunities) is not int or opportunities != 1000
        or type(served) is not int or not 0 <= served <= opportunities
    ):
        raise ConfirmatoryError("episode identity or service coverage drifted")
    if domain == f"C3S_CONFIRM/world/{index}":
        expected_world_id = f"c3s-confirm-world-{index:06d}"
    elif domain == f"C3S_CONFIRM_ACCEPT/world/{index}":
        expected_world_id = f"c3s-confirm-accept-world-{index:06d}"
    else:
        raise ConfirmatoryError("episode world domain is outside the sealed panels")
    if receipt.get("world_id") != expected_world_id or receipt.get("world_seed") != world_plan.derive_seed(domain):
        raise ConfirmatoryError("episode identity or world seed differs from its domain rule")
    for name in ("field_root_digest", "initial_state_sha256", "policy_binding_sha256", "action_trace_sha256", "plan_sha256"):
        value = receipt.get(name)
        if not isinstance(value, str) or len(value) != 64:
            raise ConfirmatoryError(f"episode {name} is not a SHA-256")
    _float(receipt.get("total_bits"), field="total_bits")
    _float(receipt.get("total_energy_j"), field="total_energy_j", positive=True)
    return dict(receipt)


def pool_episodes(receipts: Sequence[Mapping[str, object]], *, arm: str) -> dict[str, object]:
    ordered = sorted((validate_episode(row, arm=arm) for row in receipts), key=lambda row: row["episode_index"])
    if [row["episode_index"] for row in ordered] != list(range(1, len(ordered) + 1)):
        raise ConfirmatoryError("episode coverage is not one contiguous prefix")
    bits = math.fsum(_float(row["total_bits"], field="total_bits") for row in ordered)
    energy = math.fsum(_float(row["total_energy_j"], field="total_energy_j", positive=True) for row in ordered)
    served = sum(int(row["served_user_steps"]) for row in ordered)
    opportunities = sum(int(row["service_opportunities"]) for row in ordered)
    if energy <= 0 or opportunities <= 0:
        raise ConfirmatoryError("pooled denominator is non-positive")
    return {
        "episodes": len(ordered),
        "total_bits": bits,
        "total_bits_hex": bits.hex(),
        "total_energy_j": energy,
        "total_energy_j_hex": energy.hex(),
        "ee_bits_per_j": bits / energy,
        "ee_bits_per_j_hex": (bits / energy).hex(),
        "served_user_steps": served,
        "service_opportunities": opportunities,
        "service_fraction": served / opportunities,
        "service_fraction_hex": (served / opportunities).hex(),
    }


def adjudicate(pooled_by_arm: Mapping[str, object], *, completed_episodes: int) -> dict[str, object]:
    if completed_episodes != TERMINAL_BOUNDARY:
        return {"scientific_disposition_emitted": False, "overall_token": None, "reasons": []}
    if set(pooled_by_arm) != set(ARMS):
        raise ConfirmatoryError("terminal adjudication lacks both arms")
    base = pooled_by_arm["FULL2"]
    c3s = pooled_by_arm["FULL2+C3-S"]
    if not isinstance(base, Mapping) or not isinstance(c3s, Mapping):
        raise ConfirmatoryError("terminal pooled endpoints are malformed")
    if base.get("episodes") != 3000 or c3s.get("episodes") != 3000:
        raise ConfirmatoryIncomplete("terminal matched coverage is incomplete")
    reasons: list[str] = []
    if _float(c3s.get("ee_bits_per_j"), field="C3S EE") <= _float(base.get("ee_bits_per_j"), field="FULL2 EE"):
        reasons.append("EE_NOT_STRICTLY_ABOVE_FULL2")
    c3s_service = Fraction(int(c3s["served_user_steps"]), int(c3s["service_opportunities"]))
    base_service = Fraction(int(base["served_user_steps"]), int(base["service_opportunities"]))
    if c3s_service < base_service - SERVICE_MARGIN:
        reasons.append("SERVICE_MARGIN_FAILED")
    return {
        "scientific_disposition_emitted": True,
        "overall_token": HELD if not reasons else FALSIFIED,
        "reasons": reasons,
    }


def boundary_table(
    *, plan: Mapping[str, object], arm: str, policy_binding: Mapping[str, object],
    boundaries: Sequence[int], rng_factory: Callable[[int], Sequence[np.random.Generator]],
) -> dict[int, dict[str, object]]:
    """Import the stage-C boundary body and reuse its real age-draw replay."""

    if arm not in ARMS:
        raise ConfirmatoryError("boundary arm is invalid")
    requested = tuple(boundaries)
    if not requested or requested[0] != 0 or tuple(sorted(set(requested))) != requested or any(
        type(value) is not int or value < 0 or value % 100 for value in requested
    ):
        raise ConfirmatoryError("boundaries must be sorted unique 100-aligned values from zero")
    worlds = plan.get("worlds")
    if not isinstance(worlds, list) or requested[-1] > min(len(worlds), 3000):
        raise ConfirmatoryError("boundary exceeds the admitted 3000 prefix")
    donor = _load_module(BOUNDARY_DONOR, "c3s_confirm_boundary_donor")
    proxy_worlds = [SimpleNamespace(**row) for row in worlds]
    proxy_plan = SimpleNamespace(worlds=proxy_worlds, plan_sha256=plan["plan_sha256"])
    try:
        rngs = tuple(rng_factory(int(worlds[0]["world_seed"])))
        age_rng = rngs[0].spawn(1)[0]
    except (IndexError, TypeError, ValueError, AttributeError) as error:
        raise ConfirmatoryError("cannot construct the stage-C age stream") from error
    result: dict[int, dict[str, object]] = {}
    requested_set = set(requested)
    states = {0: {"format_version": 1, "age_rng_state": None}}
    for episode in range(1, requested[-1] + 1):
        age_rng.integers(0, 10, size=100)
        if episode in requested_set:
            states[episode] = {
                "format_version": 1,
                "age_rng_state": json.loads(json.dumps(age_rng.bit_generator.state)),
            }
    for boundary in requested:
        donor_payload = donor._boundary_body(
            arm=arm, boundary=boundary, plan=proxy_plan,
            schedule_sha256=canonical_sha256({"rungs": list(RUNG_BOUNDARIES), "chunk": 100}),
            policy_binding=policy_binding,
            environment_training_state=states[boundary],
            rng_algorithm=type(age_rng.bit_generator).__name__,
        )
        result[boundary] = {
            "schema": f"{SCHEMA}-boundary-state",
            "arm": arm,
            "episode_index": boundary,
            "source_stage_c_boundary": donor_payload,
            "source_builder": {"path": str(BOUNDARY_DONOR.resolve()), "sha256": file_sha256(BOUNDARY_DONOR)},
        }
        result[boundary]["boundary_state_sha256"] = canonical_sha256(result[boundary])
    return result


def publish_chunk(
    *, arm: str, start: int, rows: Sequence[Mapping[str, object]], output: Path,
    start_boundary: Mapping[str, object], end_boundary: Mapping[str, object],
    authority_sha256: str,
    runtime: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Publish one completed 100-episode chunk from an episode executor."""

    if arm not in ARMS or type(start) is not int or start < 0 or start % 100 or len(rows) != 100:
        raise ConfirmatoryError("formal chunks are exactly 100 episodes and 100-aligned")
    if output.exists() or output.is_symlink():
        raise ConfirmatoryError("chunk output must be absent")
    ordered = [validate_episode(row, arm=arm) for row in rows]
    if [row["episode_index"] for row in ordered] != list(range(start + 1, start + 101)):
        raise ConfirmatoryError("chunk rows do not match the declared range")
    if start_boundary.get("episode_index") != start or end_boundary.get("episode_index") != start + 100:
        raise ConfirmatoryError("chunk boundary states do not bind its range")
    if start_boundary.get("arm") != arm or end_boundary.get("arm") != arm:
        raise ConfirmatoryError("chunk boundary arm drifted")
    output.mkdir(parents=True, exist_ok=False)
    write_once(output / "boundary-start.json", start_boundary)
    write_once(output / "boundary-end.json", end_boundary)
    for row in ordered:
        write_once(output / "episodes" / f"episode-{row['episode_index']:06d}.json", row)
    payload = {
        "schema": f"{SCHEMA}-chunk-receipt", "status": "COMPLETE", "arm": arm,
        "chunk_id": f"{arm}-{start:06d}-{start + 100:06d}",
        "start_boundary": start, "end_boundary": start + 100,
        "start_boundary_state_sha256": start_boundary.get("boundary_state_sha256"),
        "end_boundary_state_sha256": end_boundary.get("boundary_state_sha256"),
        "ordered_episode_digest": canonical_sha256(ordered),
        "authority_sha256": authority_sha256,
        "runtime": None if runtime is None else dict(runtime),
    }
    write_once(output / "chunk-receipt.json", payload)
    return payload


def _make_environment(archive: Any) -> Any:
    from mcrl.env.ephemeris import TRAIN, BlockAlternatingSplit, EpisodeStartSampler
    from mcrl.env.mobility import MobilityConfig
    from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
    from mcrl.env.step import StepEnvironment
    from mcrl.runtime.trainer_env import TrainerEnvironment

    driver = ScenarioDriver(
        archive,
        ScenarioConfig(mobility=MobilityConfig(num_users=100), steps_per_episode=10),
    )
    split = BlockAlternatingSplit.for_archive(archive)
    sampler = EpisodeStartSampler.for_archive(archive, split, TRAIN)
    return TrainerEnvironment(StepEnvironment(driver), sampler)


def execute_formal_chunk(
    *, arm: str, start: int, end: int, output: Path,
    authority: Mapping[str, object],
) -> dict[str, object]:
    """Execute one authority-bound 100-episode arm chunk."""

    if arm not in ARMS or end != start + 100 or start < 0 or start % 100:
        raise ConfirmatoryError("formal execution requires one 100-aligned 100-episode chunk")
    formal_root = Path(str(authority.get("output_root", ""))).resolve()
    if not output.resolve().is_relative_to(formal_root):
        raise ConfirmatoryError("chunk output escapes the authority-bound output root")
    runtime = pin_runtime()
    plan_record = authority.get("world_plan")
    coordinator = authority.get("coordinator")
    stage_a = authority.get("stage_a_full2_export")
    physical = authority.get("physical_inputs")
    if not all(isinstance(record, Mapping) for record in (plan_record, coordinator, stage_a, physical)):
        raise ConfirmatoryError("launch authority lacks execution inputs")
    plan = world_plan.read_world_plan(Path(str(plan_record["path"])))
    if end > 3000:
        raise ConfirmatoryError("this authority never permits execution above episode 3000")
    frozen = load_full2_export(stage_a["path"], str(stage_a["sha256"]))
    catalog = str(coordinator.get("catalog"))
    policy = C3SFull2PolicyAdapter(
        frozen_full2=frozen, coordinator_enabled=arm == "FULL2+C3-S", catalog=catalog,
    )
    binding = policy.binding()
    binding_sha = canonical_sha256(binding)
    from mcrl.env.keyed_fading import KeyedFadingField
    from mcrl.env.tle import TleArchive
    from mcrl.runtime.training_pipeline import _evaluation_rngs

    archive = TleArchive(Path(str(physical["tle_root"])))
    boundaries = boundary_table(
        plan=plan, arm=arm, policy_binding=binding,
        boundaries=(0, start, end) if start else (0, end),
        rng_factory=_evaluation_rngs,
    )
    start_state = boundaries[start]["source_stage_c_boundary"]["environment_training_state"]
    state: Mapping[str, object] | None = None if start == 0 else start_state
    episode_adapter = FixedPolicyEpisodeAdapter(policy)
    rows: list[dict[str, object]] = []
    for index in range(start + 1, end + 1):
        world = plan["worlds"][index - 1]
        environment = _make_environment(archive)
        environment.environment._fading_field = KeyedFadingField.from_components(
            world_plan.FIELD_COMPONENT, int(world["world_seed"])
        )
        if state is not None:
            environment.load_training_state_dict(state)
        rngs = tuple(_evaluation_rngs(int(world["world_seed"])))
        execution = episode_adapter.run_episode(
            environment, environment_rng=rngs[0], mobility_rng=rngs[1],
        )
        state = environment.training_state_dict()
        rows.append({
            "schema": f"{SCHEMA}-episode-receipt", "status": "COMPLETE",
            "arm": arm, "episode_index": index, "world_id": world["world_id"],
            "world_domain": world["domain"],
            "world_seed": world["world_seed"], "field_root_digest": world["field_root_digest"],
            "initial_state_sha256": execution.initial_state_sha256,
            "policy_binding_sha256": binding_sha,
            "total_bits": execution.total_bits, "total_energy_j": execution.total_energy_j,
            "served_user_steps": execution.served_user_steps,
            "service_opportunities": execution.service_opportunities,
            "action_trace_sha256": execution.action_trace_sha256,
            "plan_sha256": plan["plan_sha256"],
        })
    payload = publish_chunk(
        arm=arm, start=start, rows=rows, output=output,
        start_boundary=boundaries[start], end_boundary=boundaries[end],
        authority_sha256=str(authority["authority_sha256"]),
        runtime=runtime,
    )
    return payload


def _execute_series(
    *, arm: str, worlds: Sequence[Mapping[str, object]], plan_sha256: str,
    authority: Mapping[str, object], initial_state: Mapping[str, object] | None,
) -> tuple[list[dict[str, object]], Mapping[str, object] | None]:
    coordinator = authority["coordinator"]
    stage_a = authority["stage_a_full2_export"]
    physical = authority["physical_inputs"]
    if not isinstance(coordinator, Mapping) or not isinstance(stage_a, Mapping) or not isinstance(physical, Mapping):
        raise ConfirmatoryError("authority execution bindings are malformed")
    frozen = load_full2_export(stage_a["path"], str(stage_a["sha256"]))
    policy = C3SFull2PolicyAdapter(
        frozen_full2=frozen, coordinator_enabled=arm == "FULL2+C3-S",
        catalog=str(coordinator["catalog"]),
    )
    binding_sha = canonical_sha256(policy.binding())
    episode_adapter = FixedPolicyEpisodeAdapter(policy)
    from mcrl.env.keyed_fading import KeyedFadingField
    from mcrl.env.tle import TleArchive
    from mcrl.runtime.training_pipeline import _evaluation_rngs

    archive = TleArchive(Path(str(physical["tle_root"])))
    state = initial_state
    rows: list[dict[str, object]] = []
    for world in worlds:
        index = int(world["episode_index"])
        environment = _make_environment(archive)
        environment.environment._fading_field = KeyedFadingField.from_components(
            world_plan.FIELD_COMPONENT, int(world["world_seed"])
        )
        if state is not None:
            environment.load_training_state_dict(state)
        rngs = tuple(_evaluation_rngs(int(world["world_seed"])))
        execution = episode_adapter.run_episode(
            environment, environment_rng=rngs[0], mobility_rng=rngs[1],
        )
        state = environment.training_state_dict()
        rows.append({
            "schema": f"{SCHEMA}-episode-receipt", "status": "COMPLETE",
            "arm": arm, "episode_index": index, "world_id": world["world_id"],
            "world_domain": world["domain"], "world_seed": world["world_seed"],
            "field_root_digest": world["field_root_digest"],
            "initial_state_sha256": execution.initial_state_sha256,
            "policy_binding_sha256": binding_sha,
            "total_bits": execution.total_bits, "total_energy_j": execution.total_energy_j,
            "served_user_steps": execution.served_user_steps,
            "service_opportunities": execution.service_opportunities,
            "action_trace_sha256": execution.action_trace_sha256,
            "plan_sha256": plan_sha256,
        })
    return rows, state


def execute_acceptance(
    *, arm: str, output: Path, authority: Mapping[str, object], preflight_sha256: str,
) -> dict[str, object]:
    """Run the mandatory independent-domain sequential-200/2x100 check."""

    if arm not in ARMS:
        raise ConfirmatoryError("acceptance arm is invalid")
    pin_runtime()
    worlds = []
    from mcrl.env.keyed_fading import KeyedFadingField
    for index in range(1, 201):
        domain = f"C3S_CONFIRM_ACCEPT/world/{index}"
        seed = world_plan.derive_seed(domain)
        worlds.append({
            "episode_index": index, "world_id": f"c3s-confirm-accept-world-{index:06d}",
            "domain": domain, "world_seed": seed,
            "field_root_digest": KeyedFadingField.from_components(world_plan.FIELD_COMPONENT, seed).root_digest,
        })
    plan_sha = canonical_sha256({
        "domain": "C3S_CONFIRM_ACCEPT/world/{i}", "worlds": worlds,
        "arms": list(ARMS), "steps": 10,
    })
    direct, _direct_end = _execute_series(
        arm=arm, worlds=worlds, plan_sha256=plan_sha,
        authority=authority, initial_state=None,
    )
    first, first_state = _execute_series(
        arm=arm, worlds=worlds[:100], plan_sha256=plan_sha,
        authority=authority, initial_state=None,
    )
    second, _second_state = _execute_series(
        arm=arm, worlds=worlds[100:], plan_sha256=plan_sha,
        authority=authority, initial_state=first_state,
    )
    # Boundary tables are produced independently for the two paths and then
    # compared through the imported stage-C semantics.
    from mcrl.runtime.training_pipeline import _evaluation_rngs
    binding = {"arm": arm, "acceptance_plan_sha256": plan_sha}
    accept_plan = {"worlds": worlds, "plan_sha256": plan_sha}
    direct_boundaries = boundary_table(
        plan=accept_plan, arm=arm, policy_binding=binding,
        boundaries=(0, 100, 200), rng_factory=_evaluation_rngs,
    )
    chunk_boundaries = boundary_table(
        plan=accept_plan, arm=arm, policy_binding=binding,
        boundaries=(0, 100, 200), rng_factory=_evaluation_rngs,
    )
    return build_acceptance_receipt(
        arm=arm, direct_rows=direct, first_chunk_rows=first,
        second_chunk_rows=second, direct_boundary_states=direct_boundaries,
        chunk_boundary_states=chunk_boundaries, preflight_sha256=preflight_sha256,
        output=output,
    )


def build_acceptance_receipt(
    *, arm: str, direct_rows: Sequence[Mapping[str, object]],
    first_chunk_rows: Sequence[Mapping[str, object]],
    second_chunk_rows: Sequence[Mapping[str, object]],
    direct_boundary_states: Mapping[int, object],
    chunk_boundary_states: Mapping[int, object],
    preflight_sha256: str, output: Path,
) -> dict[str, object]:
    """Require direct 200 versus 2x100 bitwise equivalence for one arm."""

    if arm not in ARMS or len(direct_rows) != 200 or len(first_chunk_rows) != 100 or len(second_chunk_rows) != 100:
        raise ConfirmatoryError("acceptance requires sequential 200 versus exactly 2x100")
    chunked = [*first_chunk_rows, *second_chunk_rows]
    for index, row in enumerate(direct_rows, 1):
        parsed = validate_episode(row, arm=arm)
        if parsed["world_domain"] != f"C3S_CONFIRM_ACCEPT/world/{index}":
            raise ConfirmatoryError("acceptance receipt uses a non-acceptance world")
    for index, row in enumerate(chunked, 1):
        parsed = validate_episode(row, arm=arm)
        if parsed["world_domain"] != f"C3S_CONFIRM_ACCEPT/world/{index}":
            raise ConfirmatoryError("chunked acceptance uses a non-acceptance world")
    acceptance_comparison(list(direct_rows), chunked, artifact="receipts")
    for boundary in (0, 100, 200):
        if boundary not in direct_boundary_states or boundary not in chunk_boundary_states:
            raise ConfirmatoryError("acceptance lacks a required boundary state")
        acceptance_comparison(
            direct_boundary_states[boundary], chunk_boundary_states[boundary],
            artifact=f"resume_states[{boundary}]",
        )
    for boundary in (100, 200):
        acceptance_comparison(
            pool_episodes(direct_rows[:boundary], arm=arm),
            pool_episodes(chunked[:boundary], arm=arm),
            artifact=f"rungs[{boundary}]",
        )
    direct_pools = {
        str(boundary): pool_episodes(direct_rows[:boundary], arm=arm)
        for boundary in (100, 200)
    }
    chunk_pools = {
        str(boundary): pool_episodes(chunked[:boundary], arm=arm)
        for boundary in (100, 200)
    }
    evidence = {
        "sequential": {
            "episodes": list(direct_rows),
            "resume_states": {str(key): value for key, value in direct_boundary_states.items()},
            "checkpoints": direct_pools, "rungs": direct_pools,
        },
        "two_by_100": {
            "episodes": chunked,
            "resume_states": {str(key): value for key, value in chunk_boundary_states.items()},
            "checkpoints": chunk_pools, "rungs": chunk_pools,
        },
    }
    payload = {
        "schema": f"{SCHEMA}-chunk-equivalence",
        "status": "PASS_BITWISE_CHUNK_EQUIVALENCE",
        "arm": arm, "episodes": 200, "chunks": [[1, 100], [101, 200]],
        "preflight_sha256": preflight_sha256,
        "episode_digest": canonical_sha256(chunked),
        "excluded_fields": list(_equivalence_exclusions()),
        "comparison_source": {"path": str(ACCEPTANCE_DONOR.resolve()), "sha256": file_sha256(ACCEPTANCE_DONOR)},
        "merged_artifacts_compared": ["receipts", "checkpoints", "rungs", "resume_states"],
        "evidence": evidence,
    }
    write_once(output, payload)
    return payload


def authenticate_launch_authority(
    path: Path, *, mode: str, launch_arguments: Sequence[str],
) -> dict[str, Any]:
    binding = validate_sealed_file(path)
    payload = read_json(path, field="launch authority")
    if (
        payload.get("schema") != f"{SCHEMA}-launch-authority"
        or payload.get("status") != "FROZEN_LAUNCH_AUTHORITY"
        or payload.get("mode") != mode
        or payload.get("authority_path") != str(path.resolve())
        or payload.get("launch_arguments") != list(launch_arguments)
    ):
        raise ConfirmatoryError("launch authority does not bind this exact invocation")
    preflight = payload.get("preflight")
    if not isinstance(preflight, Mapping):
        raise ConfirmatoryError("launch authority lacks preflight binding")
    validate_sealed_file(str(preflight.get("path", "")), str(preflight.get("sha256", "")))
    manifest = read_json(str(preflight["path"]), field="bound preflight")
    for record in manifest.get("code_files", []):
        if not isinstance(record, Mapping) or file_sha256(str(record.get("path", ""))) != record.get("sha256"):
            raise ConfirmatoryError("preflight code bytes drifted")
    for record in (
        payload.get("plan_contract"), payload.get("stage_a_full2_export"),
        payload.get("coordinator", {}).get("code"), payload.get("coordinator", {}).get("config"),
        payload.get("world_plan"), payload.get("physical_inputs", {}).get("prereg"),
        payload.get("physical_inputs", {}).get("tle_manifest"),
    ):
        if not isinstance(record, Mapping) or file_sha256(str(record.get("path", ""))) != record.get("sha256"):
            raise ConfirmatoryError("launch input bytes drifted")
    if mode == "formal":
        verify_acceptance_receipts(
            [Path(str(row["path"])) for row in payload.get("acceptance_receipts", [])],
            preflight_sha256=str(preflight["sha256"]),
        )
    return {**payload, "authority_sha256": binding["sha256"]}


def _read_chunk(root: Path, *, arm: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    receipt = read_json(root / "chunk-receipt.json", field="chunk receipt")
    start, end = receipt.get("start_boundary"), receipt.get("end_boundary")
    if (
        receipt.get("schema") != f"{SCHEMA}-chunk-receipt"
        or receipt.get("status") != "COMPLETE"
        or receipt.get("arm") != arm
        or type(start) is not int or type(end) is not int
        or start < 0 or end != start + 100
        or receipt.get("chunk_id") != f"{arm}-{start:06d}-{end:06d}"
    ):
        raise ConfirmatoryError("chunk receipt identity drifted")
    boundaries: dict[str, dict[str, Any]] = {}
    for name, expected_episode, receipt_field in (
        ("boundary-start.json", start, "start_boundary_state_sha256"),
        ("boundary-end.json", end, "end_boundary_state_sha256"),
    ):
        value = read_json(root / name, field=name)
        body = dict(value)
        claimed = body.pop("boundary_state_sha256", None)
        if (
            value.get("schema") != f"{SCHEMA}-boundary-state"
            or value.get("arm") != arm
            or value.get("episode_index") != expected_episode
            or claimed != canonical_sha256(body)
            or receipt.get(receipt_field) != claimed
        ):
            raise ConfirmatoryError("chunk boundary-state provenance drifted")
        boundaries[name] = value
    authority_sha = receipt.get("authority_sha256")
    if not isinstance(authority_sha, str) or len(authority_sha) != 64:
        raise ConfirmatoryError("chunk authority digest is absent")
    paths = [root / "episodes" / f"episode-{index:06d}.json" for index in range(start + 1, end + 1)]
    if any(not path.is_file() for path in paths):
        raise ConfirmatoryIncomplete("chunk episode coverage is incomplete")
    rows = [validate_episode(read_json(path, field="chunk episode"), arm=arm) for path in paths]
    if canonical_sha256(rows) != receipt.get("ordered_episode_digest"):
        raise ConfirmatoryError("chunk ordered episode digest drifted")
    receipt["_boundary_start"] = boundaries["boundary-start.json"]
    receipt["_boundary_end"] = boundaries["boundary-end.json"]
    return receipt, rows


def merge_arm_chunks(arm: str, chunk_roots: Sequence[Path], output: Path) -> dict[str, object]:
    if arm not in ARMS:
        raise ConfirmatoryError("unknown arm")
    if output.exists() or output.is_symlink():
        raise ConfirmatoryError("arm merge output must be absent")
    chunks = [_read_chunk(Path(root), arm=arm) for root in chunk_roots]
    chunks.sort(key=lambda item: int(item[0]["start_boundary"]))
    cursor = 0
    rows: list[dict[str, Any]] = []
    plan_digests: set[str] = set()
    policy_digests: set[str] = set()
    authority_digests: set[str] = set()
    previous_end_digest: str | None = None
    for receipt, block in chunks:
        if receipt["start_boundary"] != cursor:
            raise ConfirmatoryIncomplete("chunks are not one contiguous prefix")
        cursor = int(receipt["end_boundary"])
        if previous_end_digest is not None and receipt["start_boundary_state_sha256"] != previous_end_digest:
            raise ConfirmatoryError("adjacent chunks disagree at their boundary state")
        previous_end_digest = str(receipt["end_boundary_state_sha256"])
        rows.extend(block)
        plan_digests.update(str(row["plan_sha256"]) for row in block)
        policy_digests.update(str(row["policy_binding_sha256"]) for row in block)
        authority_digests.add(str(receipt["authority_sha256"]))
    if cursor not in RUNG_BOUNDARIES or len(plan_digests) != 1 or len(policy_digests) != 1 or len(authority_digests) != 1:
        raise ConfirmatoryError("arm merge boundary or provenance drifted")
    output.mkdir(parents=True, exist_ok=False)
    for row in rows:
        write_once(output / "episodes" / f"episode-{row['episode_index']:06d}.json", row)
    for boundary in range(100, cursor + 1, 100):
        pooled = pool_episodes(rows[:boundary], arm=arm)
        checkpoint = {
            "schema": f"{SCHEMA}-arm-checkpoint", "status": "COMPLETE",
            "arm": arm, "completed_episode": boundary,
            "plan_sha256": next(iter(plan_digests)),
            "policy_binding_sha256": next(iter(policy_digests)),
            "pooled": pooled, "scientific_disposition_emitted": False,
        }
        write_once(output / "checkpoints" / f"checkpoint-{boundary:06d}.json", checkpoint)
        if boundary in RUNG_BOUNDARIES:
            write_once(output / "rungs" / f"rung-{boundary:06d}.json", {
                **checkpoint, "schema": f"{SCHEMA}-arm-rung",
            })
    payload = {
        "schema": f"{SCHEMA}-arm-merge", "status": "COMPLETE_ARM_MERGE",
        "arm": arm, "arm_order": list(ARMS), "completed_episode": cursor,
        "plan_sha256": next(iter(plan_digests)),
        "policy_binding_sha256": next(iter(policy_digests)),
        "authority_sha256": next(iter(authority_digests)),
        "ordered_episode_digest": canonical_sha256(rows),
        "pooled": pool_episodes(rows, arm=arm),
        "chunk_receipts": [
            {"path": str((Path(root) / "chunk-receipt.json").resolve()), "sha256": file_sha256(Path(root) / "chunk-receipt.json")}
            for root in chunk_roots
        ],
        "scientific_disposition_emitted": False,
    }
    write_once(output / "arm-merge.json", payload)
    return payload


def _read_arm_merge(root: Path, arm: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    merge = read_json(root / "arm-merge.json", field=f"{arm} arm merge")
    completed = merge.get("completed_episode")
    if merge.get("status") != "COMPLETE_ARM_MERGE" or merge.get("arm") != arm or completed not in RUNG_BOUNDARIES:
        raise ConfirmatoryError(f"{arm} merge identity drifted")
    rows = [
        validate_episode(read_json(root / "episodes" / f"episode-{index:06d}.json"), arm=arm)
        for index in range(1, int(completed) + 1)
    ]
    if canonical_sha256(rows) != merge.get("ordered_episode_digest") or pool_episodes(rows, arm=arm) != merge.get("pooled"):
        raise ConfirmatoryError(f"{arm} merge contents drifted")
    return merge, rows


def merge_two_arms(arm_roots: Mapping[str, Path], output: Path) -> dict[str, object]:
    if tuple(arm_roots) != ARMS:
        raise ConfirmatoryError("two-arm merge requires frozen arm order")
    if output.exists() or output.is_symlink():
        raise ConfirmatoryError("two-arm merge output must be absent")
    loaded = {arm: _read_arm_merge(Path(arm_roots[arm]), arm) for arm in ARMS}
    completed = {int(loaded[arm][0]["completed_episode"]) for arm in ARMS}
    plans = {str(loaded[arm][0]["plan_sha256"]) for arm in ARMS}
    if len(completed) != 1 or len(plans) != 1:
        raise ConfirmatoryError("two arms disagree on boundary or plan")
    boundary = next(iter(completed))
    for index in range(boundary):
        base = loaded["FULL2"][1][index]
        c3s = loaded["FULL2+C3-S"][1][index]
        for name in ("episode_index", "world_id", "world_domain", "world_seed", "field_root_digest", "initial_state_sha256", "plan_sha256"):
            if base[name] != c3s[name]:
                raise ConfirmatoryError(f"matched episode differs at {name} for episode {index + 1}")
    output.mkdir(parents=True, exist_ok=False)
    for checkpoint_boundary in range(100, boundary + 1, 100):
        pooled = {
            arm: pool_episodes(loaded[arm][1][:checkpoint_boundary], arm=arm)
            for arm in ARMS
        }
        checkpoint = {
            "schema": f"{SCHEMA}-checkpoint", "status": "COMPLETE",
            "completed_episode": checkpoint_boundary, "arms": list(ARMS),
            "plan_sha256": next(iter(plans)), "pooled_by_arm": pooled,
            "scientific_disposition_emitted": False,
        }
        write_once(output / "checkpoints" / f"checkpoint-{checkpoint_boundary:06d}.json", checkpoint)
        if checkpoint_boundary in RUNG_BOUNDARIES:
            write_once(output / "rungs" / f"rung-{checkpoint_boundary:06d}.json", {
                **checkpoint, "schema": f"{SCHEMA}-rung",
            })
    pooled_final = {arm: loaded[arm][0]["pooled"] for arm in ARMS}
    disposition = adjudicate(pooled_final, completed_episodes=boundary)
    result: dict[str, object] = {
        "schema": f"{SCHEMA}-two-arm-merge", "status": "COMPLETE",
        "completed_episode": boundary, "arms": list(ARMS),
        "plan_sha256": next(iter(plans)), "pooled_by_arm": pooled_final,
        "claim_ceiling": CLAIM_CEILING,
        "arm_merge_provenance": {
            arm: {"path": str((Path(arm_roots[arm]) / "arm-merge.json").resolve()), "sha256": file_sha256(Path(arm_roots[arm]) / "arm-merge.json")}
            for arm in ARMS
        },
        **disposition,
    }
    write_once(output / "merge-receipt.json", result)
    if boundary == TERMINAL_BOUNDARY:
        write_once(output / "result.json", {
            **result, "schema": f"{SCHEMA}-terminal-result", "terminal_boundary": 3000,
        })
    return result


def acceptance_comparison(
    direct: object, chunked: object, *, artifact: str,
) -> None:
    """Use the stage-C comparison implementation and exclusion list verbatim."""

    common = _load_module(COMMON_DONOR, "stagec_common")
    comparison = _load_module(ACCEPTANCE_DONOR, "c3s_confirm_acceptance_donor")
    if tuple(comparison.common.CHUNK_EQUIVALENCE_PROVENANCE_ONLY_FIELDS) != tuple(
        common.CHUNK_EQUIVALENCE_PROVENANCE_ONLY_FIELDS
    ):
        raise ConfirmatoryError("stage-C equivalence exclusion list import drifted")
    comparison._assert_equivalent(direct, chunked, artifact=artifact)


def verify_acceptance_receipts(paths: Sequence[Path], *, preflight_sha256: str) -> list[dict[str, object]]:
    if len(paths) != 2:
        raise ConfirmatoryError("formal launch requires two arm acceptance receipts")
    records = []
    for arm, path in zip(ARMS, paths, strict=True):
        sealed = validate_sealed_file(path)
        payload = read_json(path, field=f"{arm} acceptance")
        if (
            payload.get("schema") != f"{SCHEMA}-chunk-equivalence"
            or payload.get("status") != "PASS_BITWISE_CHUNK_EQUIVALENCE"
            or payload.get("arm") != arm
            or payload.get("episodes") != 200
            or payload.get("chunks") != [[1, 100], [101, 200]]
            or payload.get("preflight_sha256") != preflight_sha256
            or payload.get("excluded_fields") != list(_equivalence_exclusions())
        ):
            raise ConfirmatoryError(f"{arm} acceptance receipt drifted")
        evidence = payload.get("evidence")
        if not isinstance(evidence, Mapping):
            raise ConfirmatoryError(f"{arm} acceptance evidence is absent")
        direct = evidence.get("sequential")
        chunked = evidence.get("two_by_100")
        if not isinstance(direct, Mapping) or not isinstance(chunked, Mapping):
            raise ConfirmatoryError(f"{arm} acceptance paths are malformed")
        for artifact in ("episodes", "resume_states", "checkpoints", "rungs"):
            acceptance_comparison(
                direct.get(artifact), chunked.get(artifact),
                artifact=f"{arm}.{artifact}",
            )
        records.append(sealed)
    return records


def _equivalence_exclusions() -> tuple[str, ...]:
    common = _load_module(COMMON_DONOR, "stagec_common")
    return tuple(common.CHUNK_EQUIVALENCE_PROVENANCE_ONLY_FIELDS)


def estimate(catalog: str, *, episodes: int = 3000, screen_timing: Path | None = None) -> dict[str, object]:
    if catalog not in ("lite", "full") or type(episodes) is not int or episodes < 1:
        raise ConfirmatoryError("estimate requires catalog lite/full and positive episodes")
    tau: float | None = None
    basis: dict[str, object]
    if screen_timing is None:
        configured = os.environ.get("MCRL_C3S_SCREEN_TIMING_RECEIPT")
        candidates = [
            Path(configured) if configured else None,
            SCREEN_DIR / "run-output/terminal/terminal-receipt.json",
        ]
        screen_timing = next(
            (candidate for candidate in candidates if candidate is not None and candidate.is_file()),
            None,
        )
    if screen_timing is not None and screen_timing.is_file():
        payload = read_json(screen_timing, field="screen timing receipt")
        timing = payload.get("coordinator_timing")
        arm = catalog.upper()
        if isinstance(timing, Mapping) and isinstance(timing.get(arm), Mapping):
            row = timing[arm]
            for key in ("total_wall_seconds", "selector_wall_seconds"):
                metric = row.get(key)
                if isinstance(metric, Mapping) and metric.get("mean_hex") is not None:
                    tau = float.fromhex(str(metric["mean_hex"]))
                    break
            if tau is None and row.get("mean_hex") is not None:
                tau = float.fromhex(str(row["mean_hex"]))
        if tau is not None:
            basis = {"kind": "SCREEN_MEASURED_MEAN_SELECTOR_WALL", "path": str(screen_timing.resolve()), "sha256": file_sha256(screen_timing)}
    if tau is None:
        screen_runner = _load_module(SCREEN_DIR / "run_v023_c3s_screen.py", "c3s_confirm_screen_runner")
        fallback = screen_runner.estimate(units=1)
        full_hours = float(fallback["horizons"]["100"]["arms"]["FULL"]["worker_hours"])
        full_tau = full_hours * 3600.0 / 100.0
        tau = full_tau if catalog == "full" else full_tau / 10.0
        basis = {
            "kind": "S0_E1_MEASURED_COST_FALLBACK",
            "screen_estimate_basis": fallback["basis"],
            "lite_rule": "one tenth of full" if catalog == "lite" else None,
        }
    main_hours = episodes * (27.2 + 10.0 * tau) / 3600.0
    acceptance_hours = 400 * (27.2 + 10.0 * tau) / 3600.0
    return {
        "schema": f"{SCHEMA}-estimate", "catalog": catalog, "episodes_per_arm": episodes,
        "arm_episodes": episodes * 2, "decisions_per_episode": 10,
        "selector_mean_seconds_per_decision": tau,
        "main_panel_worker_hours": main_hours,
        "acceptance_worker_hours": acceptance_hours,
        "total_worker_hours": main_hours + acceptance_hours,
        "formula": "C(N)=N*(27.2+10*tau_c)/3600 worker-hours; acceptance=C(400)",
        "basis": basis,
    }


def dry_run(catalog: str) -> str:
    if catalog not in ("lite", "full"):
        raise ConfirmatoryError("dry-run catalog must be lite or full")
    return (
        f"C3S_CONFIRM_DRY_RUN catalog={catalog} arms=FULL2,FULL2+C3-S "
        "chunks=100 rungs=100,500,1500,3000 terminal=3000 execution=NOT_STARTED"
    )


def publish_failure(output: Path, error: BaseException, *, scope: str) -> dict[str, object]:
    incomplete = isinstance(error, (ConfirmatoryIncomplete, KeyboardInterrupt, MemoryError)) or (
        isinstance(error, OSError)
        and error.errno in (errno.ENOSPC, errno.EDQUOT, errno.EMFILE, errno.ENFILE)
    )
    status = "INCOMPLETE" if incomplete else "INVALID_RUN"
    payload = {
        "schema": f"{SCHEMA}-failure", "status": status, "scope": scope,
        "error_type": type(error).__name__, "message": str(error),
        "overall_token": None, "scientific_disposition_emitted": False,
    }
    write_once(output / ("INCOMPLETE.json" if incomplete else "INVALID_RUN.json"), payload)
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--estimate", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--accept", action="store_true")
    mode.add_argument("--run-chunk", action="store_true")
    mode.add_argument("--merge-arm", action="store_true")
    mode.add_argument("--merge-two", action="store_true")
    parser.add_argument("--catalog", choices=("lite", "full"), default="lite")
    parser.add_argument("--episodes", type=int, default=3000)
    parser.add_argument("--screen-timing", type=Path)
    parser.add_argument("--arm", choices=ARMS)
    parser.add_argument("--chunk-root", type=Path, action="append", default=[])
    parser.add_argument("--arm-root", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--launch-authority", type=Path)
    parser.add_argument("--start", type=int)
    parser.add_argument("--end", type=int)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    launch_arguments = list(sys.argv[1:] if argv is None else argv)
    args = _parser().parse_args(launch_arguments)
    try:
        if args.estimate:
            print(json.dumps(estimate(args.catalog, episodes=args.episodes, screen_timing=args.screen_timing), sort_keys=True, separators=(",", ":")))
        elif args.dry_run:
            print(dry_run(args.catalog))
        elif args.accept:
            if args.arm is None or args.output is None or args.launch_authority is None:
                raise ConfirmatoryError("--accept requires arm/output/launch-authority")
            authority = authenticate_launch_authority(
                args.launch_authority, mode="acceptance", launch_arguments=launch_arguments,
            )
            preflight = authority["preflight"]
            print(json.dumps(execute_acceptance(
                arm=args.arm, output=args.output, authority=authority,
                preflight_sha256=str(preflight["sha256"]),
            ), sort_keys=True, separators=(",", ":")))
        elif args.run_chunk:
            if args.arm is None or args.start is None or args.end is None or args.output is None or args.launch_authority is None:
                raise ConfirmatoryError("--run-chunk requires arm/start/end/output/launch-authority")
            authority = authenticate_launch_authority(
                args.launch_authority, mode="formal", launch_arguments=launch_arguments,
            )
            print(json.dumps(execute_formal_chunk(
                arm=args.arm, start=args.start, end=args.end,
                output=args.output, authority=authority,
            ), sort_keys=True, separators=(",", ":")))
        elif args.merge_arm:
            if args.arm is None or args.output is None:
                raise ConfirmatoryError("--merge-arm requires --arm and --output")
            if args.launch_authority is None:
                raise ConfirmatoryError("formal merge requires --launch-authority")
            authenticate_launch_authority(
                args.launch_authority, mode="formal", launch_arguments=launch_arguments,
            )
            print(json.dumps(merge_arm_chunks(args.arm, args.chunk_root, args.output), sort_keys=True, separators=(",", ":")))
        else:
            if len(args.arm_root) != 2 or args.output is None:
                raise ConfirmatoryError("--merge-two requires two ordered --arm-root values and --output")
            if args.launch_authority is None:
                raise ConfirmatoryError("formal merge requires --launch-authority")
            authenticate_launch_authority(
                args.launch_authority, mode="formal", launch_arguments=launch_arguments,
            )
            roots = {arm: root for arm, root in zip(ARMS, args.arm_root, strict=True)}
            print(json.dumps(merge_two_arms(roots, args.output), sort_keys=True, separators=(",", ":")))
    except (ConfirmatoryIncomplete, KeyboardInterrupt) as error:
        if args.output is not None:
            try:
                publish_failure(args.output, error, scope="runner")
            except Exception:
                pass
        print(f"INCOMPLETE: {error}", file=sys.stderr)
        return 3
    except Exception as error:
        if args.output is not None and not (args.estimate or args.dry_run):
            try:
                publish_failure(args.output, error, scope="runner")
            except Exception:
                pass
        print(f"INVALID_RUN: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ARMS", "FALSIFIED", "HELD", "RUNG_BOUNDARIES", "ConfirmatoryError",
    "ConfirmatoryIncomplete", "acceptance_comparison", "adjudicate", "boundary_table",
    "build_acceptance_receipt", "dry_run", "estimate", "merge_arm_chunks",
    "merge_two_arms", "pool_episodes", "publish_chunk",
    "validate_sealed_file", "write_once",
]
