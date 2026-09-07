#!/usr/bin/env python3
"""Non-formal V0.23 one-world plumbing rehearsal with fresh model bytes.

The formal source runner is not imported and no learner update is invented.
Fresh checkpoints therefore carry ``update_count=0``.  The existing plumbing
loader is called unchanged; if it refuses those bytes, this script records the
exact refusal and may run only a read-only, first-decision TRAIN diagnostic.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict
from hashlib import sha256
from io import BytesIO
import argparse
import importlib.util
import json
import os
from pathlib import Path
import secrets
import sys
import time
from typing import Any

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PLUMBING_PATH = HERE / "v023_real_one_world_plumbing.py"
MODEL_CONFIG_PATH = (
    REPO
    / ".scratch/multi-catfish-v023-100e-screen-preoutcome-v2"
    / "V023-100E-MODEL-CONFIG.json"
)

ARMS = (
    "ALL_NEUTRAL_CONTROL",
    "FULL",
    "DROP_C1",
    "DROP_C2",
    "DROP_C3",
)
TRAIN_SEED = 2927175120652069826
WORLD_INDEX = 1
WORLD_ID = "train-v023-100e-plumbing-001"
WORLD_SEED = 2818138104890398344
TLE_ROOT = Path("/home/sat/mcrl-runtime/tle-frozen-20260820")
UNTRAINED_MODELS = "UNTRAINED_FRESH_INITIALIZATION_NOT_A_TRAINED_POLICY"
EXPORT_MANIFEST_SCHEMA = (
    "multi-catfish-mcrl-v023-five-arm-source-training-runner-v2-"
    "five-current-model-exports"
)
REHEARSAL_SCHEMA = "multi-catfish-mcrl-v023-one-world-plumbing-rehearsal-v1"
REHEARSAL_MARKER = "REHEARSAL-UNTRAINED"


class RehearsalError(RuntimeError):
    """The non-formal rehearsal crossed or could not satisfy its boundary."""


def _load_module(name: str, path: Path) -> Any:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise RehearsalError(f"required source is absent: {source}")
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        raise RehearsalError(f"cannot import required source: {source}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


PLUMBING = _load_module("v023_one_world_fresh_rehearsal_plumbing", PLUMBING_PATH)


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise RehearsalError("receipt is not finite canonical JSON") from error


def file_sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise RehearsalError(f"artifact is not a regular file: {path}")
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _torch_bytes(value: object) -> bytes:
    stream = BytesIO()
    torch.save(value, stream)
    return stream.getvalue()


def _atomic_write_once(path: Path, payload: bytes) -> str:
    if path.exists() or path.is_symlink():
        raise RehearsalError(f"refusing to overwrite artifact: {path}")
    if path.parent.is_symlink() or not path.parent.is_dir():
        raise RehearsalError(f"artifact parent is unavailable: {path.parent}")
    temporary = path.parent / f".{path.name}.{secrets.token_hex(16)}.tmp"
    descriptor: int | None = None
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            descriptor = None
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            raise RehearsalError(f"refusing to overwrite artifact: {path}") from error
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return sha256(payload).hexdigest()


def _write_json_once(path: Path, value: Mapping[str, Any]) -> str:
    return _atomic_write_once(path, _canonical_bytes(value))


def _require_absent(path: Path, *, field: str) -> None:
    if path.exists() or path.is_symlink():
        raise RehearsalError(f"{field} already exists; overwrite is refused: {path}")
    if path.parent.is_symlink() or not path.parent.is_dir():
        raise RehearsalError(f"{field} parent is unavailable: {path.parent}")


def _require_cli_scratch_root(path: Path, *, field: str) -> Path:
    resolved = path.resolve(strict=False)
    scratch = (REPO / ".scratch").resolve()
    try:
        resolved.relative_to(scratch)
    except ValueError as error:
        raise RehearsalError(f"{field} must remain under checkout .scratch") from error
    if REHEARSAL_MARKER not in resolved.name.upper():
        raise RehearsalError(f"{field} name must contain {REHEARSAL_MARKER}")
    return resolved


def load_model_config(path: Path = MODEL_CONFIG_PATH) -> Any:
    """Materialise the exact q1/q2/q3 configuration from the V2 JSON."""

    from mcrl.algorithms.ee_axis_action_shared import EEAxisActionSharedConfig
    from mcrl.algorithms.ee_axis_lcsrs_c3_head import LCSRSC3HeadConfig
    from mcrl.algorithms.ee_axis_lcsrs_three_route import LCSRSThreeRouteConfig
    from mcrl.algorithms.ee_axis_v014_head import EEAxisV014HeadConfig

    if path.is_symlink() or not path.is_file():
        raise RehearsalError(f"model config is not a regular file: {path}")
    raw = json.loads(path.read_text(encoding="ascii"))
    if not isinstance(raw, dict) or set(raw) != {"q1", "q2", "q3"}:
        raise RehearsalError("model config must contain exactly q1, q2, q3")
    q1_values = dict(raw["q1"])
    q2_values = dict(raw["q2"])
    q3_values = dict(raw["q3"])
    q1_values["hidden_layers"] = tuple(q1_values["hidden_layers"])
    q1_values["loss_weights"] = tuple(q1_values["loss_weights"])
    q2_values["hidden_layers"] = tuple(q2_values["hidden_layers"])
    q3_values["hidden_layers"] = tuple(q3_values["hidden_layers"])
    config = LCSRSThreeRouteConfig(
        q1=EEAxisActionSharedConfig(**q1_values),
        q2=EEAxisV014HeadConfig(**q2_values),
        q3=LCSRSC3HeadConfig(**q3_values),
    )
    if config.q1.state_dim != 228 or config.q2.state_dim != 448:
        raise RehearsalError("V2 q1/q2 state dimensions are not 228/448")
    return config


def build_fresh_models(config: Any) -> dict[str, Any]:
    """Build five independent models from the same deterministic seed."""

    from mcrl.algorithms.ee_axis_lcsrs_three_route import EEAxisLCSRSThreeRoute

    models = {
        arm: EEAxisLCSRSThreeRoute(config, train_seed=TRAIN_SEED, device="cpu")
        for arm in ARMS
    }
    if len({id(model) for model in models.values()}) != len(ARMS):
        raise RehearsalError("fresh model instances alias")
    parameter_digests = {PLUMBING._parameter_sha256(model) for model in models.values()}
    if len(parameter_digests) != 1:
        raise RehearsalError("same-seed fresh model initialization bytes differ")
    return models


def write_fresh_untrained_exports(
    export_root: Path,
    *,
    config_path: Path = MODEL_CONFIG_PATH,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Path]]:
    """Write runner-shaped epoch-0000 exports into one absent root."""

    root = Path(export_root)
    _require_absent(root, field="scratch export root")
    config = load_model_config(config_path)
    models = build_fresh_models(config)
    root.mkdir(mode=0o700)
    exports_root = root / "exports"
    exports_root.mkdir(mode=0o700)
    epoch_directory = exports_root / "epoch-0000"
    epoch_directory.mkdir(mode=0o700)
    entries: list[dict[str, Any]] = []
    paths: dict[str, Path] = {}
    for index, arm in enumerate(ARMS):
        state = models[arm].checkpoint_state(update_count=0)
        filename = f"{index:02d}-{arm}.current-ee-axis-lcsrs-three-route.pt"
        destination = epoch_directory / filename
        digest = _atomic_write_once(destination, _torch_bytes(state))
        _atomic_write_once(destination.with_suffix(destination.suffix + ".sha256"), f"{digest}\n".encode("ascii"))
        paths[arm] = destination
        entries.append(
            {
                "arm": arm,
                "path": str(destination.relative_to(root)),
                "sha256": digest,
                "algorithm": state["algorithm"],
                "update_count": 0,
                "source_mapping": dict(PLUMBING.SOURCE_MAPPING[arm]),
            }
        )
    initialization_sha256 = PLUMBING._parameter_sha256(models[ARMS[0]])
    manifest: dict[str, Any] = {
        "schema": EXPORT_MANIFEST_SCHEMA,
        "claim_ceiling": "NON_FORMAL_DRESS_REHEARSAL_NO_TRAINING_NO_EFFICACY",
        "formal": False,
        "models": UNTRAINED_MODELS,
        "epoch": 0,
        "update_count": 0,
        "train_seed": TRAIN_SEED,
        "model_config_path": str(config_path.resolve()),
        "model_config_sha256": file_sha256(config_path),
        "initialization_sha256": initialization_sha256,
        "arm_order": list(ARMS),
        "source_ablation_map": {
            arm: dict(PLUMBING.SOURCE_MAPPING[arm]) for arm in ARMS
        },
        "exports": entries,
    }
    manifest_path = exports_root / "epoch-0000.json"
    manifest_digest = _write_json_once(manifest_path, manifest)
    manifest["manifest_path"] = str(manifest_path)
    manifest["manifest_sha256"] = manifest_digest
    return manifest, models, paths


def probe_existing_plumbing(checkpoint_paths: Mapping[str, Path]) -> dict[str, Any]:
    """Call the existing loader unchanged and preserve any refusal verbatim."""

    started = time.perf_counter()
    try:
        loaded = PLUMBING.load_current_five_arm_models(checkpoint_paths)
    except Exception as error:  # exact external boundary is recorded below
        return {
            "accepted": False,
            "exception_type": type(error).__name__,
            "message": str(error),
            "wall_time_s": time.perf_counter() - started,
            "check": (
                "v023_real_one_world_plumbing.load_current_model_checkpoint_state -> "
                "_positive_int(state['update_count'], zero_allowed=False)"
            ),
        }
    return {
        "accepted": True,
        "wall_time_s": time.perf_counter() - started,
        "loaded_arm_order": list(loaded),
    }


def _make_environment(tle_root: Path, users: int) -> Any:
    from mcrl.env.ephemeris import TRAIN, BlockAlternatingSplit, EpisodeStartSampler
    from mcrl.env.mobility import MobilityConfig
    from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
    from mcrl.env.step import StepEnvironment
    from mcrl.env.tle import TleArchive
    from mcrl.runtime.trainer_env import TrainerEnvironment

    archive = TleArchive(tle_root)
    driver = ScenarioDriver(archive, ScenarioConfig(mobility=MobilityConfig(num_users=users)))
    split = BlockAlternatingSplit.for_archive(archive)
    sampler = EpisodeStartSampler.for_archive(archive, split, TRAIN)
    return TrainerEnvironment(StepEnvironment(driver), sampler)


def _evaluation_rngs(seed: int) -> tuple[np.random.Generator, ...]:
    children = np.random.SeedSequence(int(seed)).spawn(4)
    return tuple(np.random.default_rng(child) for child in children)


def _masked_argmax(scores: np.ndarray, masks: np.ndarray) -> np.ndarray:
    if scores.shape != masks.shape or masks.dtype != np.bool_ or not np.all(np.any(masks, axis=1)):
        raise RehearsalError("masked argmax inputs are malformed")
    return np.argmax(np.where(masks, scores, -np.inf), axis=1).astype(np.int64)


def run_first_decision_diagnostic(
    *,
    models: Mapping[str, Any],
    world: Any,
    tle_root: Path,
) -> dict[str, Any]:
    """Capture one initial TRAIN decision per arm; never call environment.step."""

    if tle_root.resolve(strict=False) != TLE_ROOT.resolve(strict=False):
        raise RehearsalError(f"diagnostic TLE root must be exactly {TLE_ROOT}")
    shared_field = PLUMBING._physical.KeyedFadingField.from_components(
        PLUMBING.TRAIN_FIELD_COMPONENT, world.world_seed
    )
    try:
        c3_factory = PLUMBING.load_current_structured_c3_view_factory()
        c3_provider_blocker = None
    except Exception as error:
        c3_factory = None
        c3_provider_blocker = {
            "exception_type": type(error).__name__,
            "message": str(error),
            "check": "v023_real_one_world_plumbing.load_current_structured_c3_view_factory",
        }
    rows: list[dict[str, Any]] = []
    initial_digests: list[str] = []
    for arm in ARMS:
        arm_started = time.perf_counter()
        environment = _make_environment(tle_root, PLUMBING.USERS)
        environment.environment._fading_field = shared_field
        env_rng, mobility_rng, _action_rng, _control_rng = _evaluation_rngs(world.world_seed)
        _states, _masks, observation = environment.reset(env_rng, mobility_rng)
        step_started = time.perf_counter()
        native = PLUMBING._physical.encode_ee_axis_state(environment.environment, observation)
        native.verify()
        masks = np.asarray(native.action_masks, dtype=np.bool_)
        model = models[arm]
        with torch.no_grad():
            q1 = model.q1(torch.tensor(native.state_matrix, dtype=torch.float32)).cpu().numpy()
        q1_reference = _masked_argmax(q1, masks)
        anchor = PLUMBING._physical.snapshot_ops3_anchor(environment.environment, observation)
        projection = PLUMBING._physical.project_ops3_anchor(anchor)
        q2_surfaces = PLUMBING._physical.build_ops3_live_surfaces(anchor, projection, q1_reference)
        q2_state = PLUMBING._physical.encode_ee_axis_v014_q2_states(q2_surfaces)
        q2_state.verify()
        q2_masks = np.asarray(q2_state.action_masks, dtype=np.bool_)
        if not np.array_equal(masks, q2_masks):
            raise RehearsalError(f"{arm} Q1/Q2 masks differ")
        snapshot = model.capture_q12(
            native,
            q2_states=q2_state.state_matrix,
            q2_action_masks=q2_masks,
            native_observation_event_digest=PLUMBING._observation_digest(native),
        )
        actions = _masked_argmax(snapshot.q12, masks)
        decision_kind = "Q1_Q2_ONLY_C3_PROVIDER_BLOCKED"
        c3_shapes = None
        if c3_factory is not None:
            view = c3_factory(
                step_environment=environment.environment,
                observation=observation,
                native_state=native,
                q12_snapshot=snapshot,
                world=world,
            )
            actions = model.select_greedy_actions(snapshot, view)
            actions = PLUMBING._validate_actions(actions, masks)
            decision_kind = "Q1_Q2_Q3_MASKED_ARGMAX"
            c3_shapes = {
                "action_context": list(view.action_context.shape),
                "tokens": list(view.tokens.shape),
                "token_mask": list(view.token_mask.shape),
                "action_mask": list(view.action_mask.shape),
            }
        initial_digest = PLUMBING._observation_digest(native)
        initial_digests.append(initial_digest)
        step_wall = time.perf_counter() - step_started
        rows.append(
            {
                "arm": arm,
                "fresh_environment": True,
                "step_index": 0,
                "decision_kind": decision_kind,
                "q1_state_shape": list(np.asarray(native.state_matrix).shape),
                "q2_state_shape": list(np.asarray(q2_state.state_matrix).shape),
                "mask_shape": list(masks.shape),
                "c3_shapes": c3_shapes,
                "initial_world_sha256": initial_digest,
                "field_root_digest": shared_field.root_digest,
                "actions_sha256": sha256(np.asarray(actions, dtype=np.int64).tobytes()).hexdigest(),
                "all_actions_legal": bool(np.all(masks[np.arange(PLUMBING.USERS), actions])),
                "step_wall_time_s": step_wall,
                "arm_wall_time_s": time.perf_counter() - arm_started,
                "environment_step_called": False,
                "total_bits": None,
                "total_energy_j": None,
            }
        )
    if len(set(initial_digests)) != 1:
        raise RehearsalError("fresh environments did not share one common initial state")
    return {
        "status": "FIRST_DECISION_ONLY_NO_ENVIRONMENT_STEP",
        "c3_provider_blocker": c3_provider_blocker,
        "fresh_environment_count": len(rows),
        "common_initial_world_sha256": initial_digests[0],
        "common_field_root_digest": shared_field.root_digest,
        "arms": rows,
    }


def run_rehearsal(
    *,
    export_root: Path,
    output_root: Path,
    tle_root: Path,
    execute_first_decision_diagnostic: bool,
    config_path: Path = MODEL_CONFIG_PATH,
) -> dict[str, Any]:
    _require_absent(export_root, field="scratch export root")
    _require_absent(output_root, field="scratch output root")
    manifest, models, paths = write_fresh_untrained_exports(export_root, config_path=config_path)
    output_root.mkdir(mode=0o700)
    world = PLUMBING.make_train_world(
        world_index=WORLD_INDEX, world_id=WORLD_ID, world_seed=WORLD_SEED
    )
    probe = probe_existing_plumbing(paths)
    diagnostic = None
    status = "PLUMBING_ACCEPTED_UNTRAINED_EXPORTS"
    if not probe["accepted"]:
        status = "BLOCKED_BY_EXISTING_PLUMBING_UNTRAINED_EXPORT_CHECK"
        if execute_first_decision_diagnostic:
            diagnostic = run_first_decision_diagnostic(
                models=models, world=world, tle_root=tle_root
            )
    receipt: dict[str, Any] = {
        "schema": REHEARSAL_SCHEMA,
        "formal": False,
        "models": UNTRAINED_MODELS,
        "status": status,
        "claim_ceiling": "NON_FORMAL_DRESS_REHEARSAL_NO_EFFICACY_NO_POLICY_RESULT",
        "train_seed": TRAIN_SEED,
        "world": {
            "index": WORLD_INDEX,
            "id": WORLD_ID,
            "seed": WORLD_SEED,
            "split": "TRAIN",
            "tle_root": str(tle_root),
            "steps_requested": 10,
            "users": 100,
        },
        "export_manifest_path": manifest["manifest_path"],
        "export_manifest_sha256": manifest["manifest_sha256"],
        "initialization_sha256": manifest["initialization_sha256"],
        "existing_plumbing_probe": probe,
        "first_decision_diagnostic": diagnostic,
        "test_split_opened": False,
        "learner_update": False,
        "episode_training": False,
        "environment_steps_executed": 0 if diagnostic is not None else None,
        "energy_bits_receipts_available": False,
        "scientific_decision": None,
    }
    receipt_path = output_root / "rehearsal-receipt.json"
    receipt_digest = _write_json_once(receipt_path, receipt)
    _atomic_write_once(
        receipt_path.with_suffix(receipt_path.suffix + ".sha256"),
        f"{receipt_digest}\n".encode("ascii"),
    )
    return receipt


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, default=TLE_ROOT)
    parser.add_argument("--model-config", type=Path, default=MODEL_CONFIG_PATH)
    parser.add_argument("--execute-first-decision-diagnostic", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        export_root = _require_cli_scratch_root(args.export_root, field="export root")
        output_root = _require_cli_scratch_root(args.output_root, field="output root")
        receipt = run_rehearsal(
            export_root=export_root,
            output_root=output_root,
            tle_root=args.tle_root,
            execute_first_decision_diagnostic=bool(args.execute_first_decision_diagnostic),
            config_path=args.model_config,
        )
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False))
    return 0 if receipt["status"] == "PLUMBING_ACCEPTED_UNTRAINED_EXPORTS" else 3


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ARMS",
    "EXPORT_MANIFEST_SCHEMA",
    "MODEL_CONFIG_PATH",
    "REHEARSAL_SCHEMA",
    "TRAIN_SEED",
    "UNTRAINED_MODELS",
    "WORLD_ID",
    "WORLD_INDEX",
    "WORLD_SEED",
    "RehearsalError",
    "build_fresh_models",
    "file_sha256",
    "load_model_config",
    "main",
    "probe_existing_plumbing",
    "run_first_decision_diagnostic",
    "run_rehearsal",
    "write_fresh_untrained_exports",
]
