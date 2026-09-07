"""Small helpers for engineering-lane scratch outputs only."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import hashlib
from io import BytesIO
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch


def export_torch_mapping(value: Mapping[str, Any], path: Path) -> Path:
    if not isinstance(value, Mapping):
        raise TypeError("scratch checkpoint value must be a mapping")
    destination = Path(path)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"refusing to overwrite scratch checkpoint: {destination}")
    if not destination.parent.is_dir() or destination.parent.is_symlink():
        raise FileNotFoundError(f"scratch checkpoint parent is unavailable: {destination.parent}")
    stream = BytesIO()
    torch.save(dict(value), stream)
    destination.write_bytes(stream.getvalue())
    return destination


def reload_torch_mapping(path: Path) -> Mapping[str, Any]:
    source = Path(path)
    try:
        value = torch.load(source, map_location="cpu", weights_only=False)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        raise ValueError("scratch checkpoint cannot be reloaded") from error
    if not isinstance(value, Mapping):
        raise TypeError("reloaded scratch checkpoint must be a mapping")
    return value


def _file_identity(path: Path) -> dict[str, object]:
    source = Path(path)
    return {
        "path": str(source.resolve()),
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "size": source.stat().st_size,
    }


def build_fresh_two_route_exports(
    model_config_path: Path,
    output_dir: Path,
    *,
    seed: int,
    model_config_sha256: str,
    arms: Sequence[str],
    model_class: Any,
    model_config_class: Any,
    q1_config_class: Any,
    q2_config_class: Any,
) -> dict[str, object]:
    """Write fresh, untrained producer-owned checkpoint states for three arms."""

    if tuple(arms) != ("FULL2", "DROP_C1", "DROP_C2"):
        raise ValueError("fresh export arms must be FULL2, DROP_C1, DROP_C2")
    config_path = Path(model_config_path)
    actual_config_sha256 = hashlib.sha256(config_path.read_bytes()).hexdigest()
    if actual_config_sha256 != model_config_sha256:
        raise ValueError("model configuration digest drifted")
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    q1_raw, q2_raw = dict(raw["q1"]), dict(raw["q2"])
    q1_raw["hidden_layers"] = tuple(q1_raw["hidden_layers"])
    q1_raw["loss_weights"] = tuple(q1_raw["loss_weights"])
    q2_raw["hidden_layers"] = tuple(q2_raw["hidden_layers"])
    config = model_config_class(
        q1=q1_config_class(**q1_raw),
        q2=q2_config_class(**q2_raw),
    )
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=False)
    exports: list[dict[str, object]] = []
    for offset, arm in enumerate(arms):
        model = model_class(config, train_seed=seed, device="cpu")
        payload = model.checkpoint_state(
            update_count=200,
            route_update_counts={"C1": 100, "C2": 100},
        )
        if payload["initialization"] != model.initialization_digests:
            raise ValueError(f"{arm} initialization digest binding drifted")
        path = root / f"{arm}.pt"
        with BytesIO() as stream:
            # All arms share the producer's formal initialization bytes.  The
            # export name and per-arm serialization digest carry arm identity.
            torch.save(payload, stream, pickle_protocol=2 + offset)
            path.write_bytes(stream.getvalue())
        exports.append(
            {
                "arm": arm,
                "seed": seed,
                "model_config_sha256": actual_config_sha256,
                "serialization_protocol": 2 + offset,
                **_file_identity(path),
                "initialization": dict(model.initialization_digests),
            }
        )
    return {
        "exports": exports,
        "model_config_sha256": actual_config_sha256,
        "identities": {str(item["arm"]): _file_identity(Path(str(item["path"]))) for item in exports},
    }


def load_exports_through_both_paths(
    export_bundle: Mapping[str, object],
    *,
    physical_loader: Any,
    diagnostic_loader: Any,
) -> dict[str, object]:
    """Require the physical runner seam and diagnostic-bound seam to accept all exports."""

    exports = export_bundle.get("exports")
    if not isinstance(exports, list) or len(exports) != 3:
        raise ValueError("fresh export bundle must contain exactly three exports")
    accepted: dict[str, object] = {}
    identities: dict[str, object] = {}
    for item in exports:
        if not isinstance(item, Mapping):
            raise TypeError("export identity must be a mapping")
        arm, path, digest = str(item["arm"]), Path(str(item["path"])), str(item["sha256"])
        if _file_identity(path)["sha256"] != digest:
            raise ValueError(f"{arm} export bytes changed before loading")
        first = physical_loader(path, arm=arm, expected_sha256=digest)
        second = diagnostic_loader(path, arm=arm, expected_sha256=digest)
        if first.binding() != second.binding():
            raise ValueError(f"{arm} loader bindings disagree")
        accepted[arm] = first.binding()
        identities[arm] = _file_identity(path)
    return {"accepted": accepted, "identities": identities}


def admit_baseline(
    checkpoint_path: Path,
    status_path: Path,
    *,
    expected_sha256: str,
    adapter_class: Any,
    user_state_class: Any,
) -> dict[str, object]:
    if _file_identity(Path(checkpoint_path))["sha256"] != expected_sha256:
        raise ValueError("baseline checkpoint digest differs from the declared identity")
    adapter = adapter_class.from_artifacts(
        checkpoint_path=checkpoint_path,
        status_path=status_path,
    )
    if adapter.checkpoint_sha256 != expected_sha256:
        raise ValueError("baseline adapter admitted a different checkpoint")
    action_dim = int(adapter.action_dim)
    access = np.zeros(action_dim, dtype=np.float32)
    access[0] = 1.0
    native_state = user_state_class(
        access_vector=access,
        channel_quality=np.linspace(0.0, 2.0, action_dim, dtype=np.float32),
        beam_offsets=np.linspace(-0.2, 0.2, action_dim, dtype=np.float32),
        beam_loads=np.full(action_dim, 1.0, dtype=np.float32),
        contract_fields=np.arange(13, dtype=np.float32),
    )
    encoded = adapter.encode_user_state(native_state, num_users=1)
    if np.asarray(encoded).shape != (int(adapter.state_dim),):
        raise ValueError("baseline adapter emitted an unexpected encoded shape")
    return {
        "checkpoint_sha256": adapter.checkpoint_sha256,
        "contract_fields_encoding_sha256": hashlib.sha256(
            np.asarray(encoded, dtype=np.float32).tobytes()
        ).hexdigest(),
        "identities": {
            "checkpoint": _file_identity(Path(checkpoint_path)),
            "status": _file_identity(Path(status_path)),
        },
    }


def build_and_check_world_plan(
    destination: Path,
    *,
    expected_digest: str,
    build: Any,
    write_once: Any,
    read: Any,
    check_main: Any,
) -> dict[str, object]:
    payload = build()
    write_once(Path(destination), payload)
    checked = read(Path(destination))
    if checked.get("plan_sha256") != expected_digest:
        raise ValueError("world plan digest differs from the declared identity")
    if check_main(["--check", str(destination)]) != 0:
        raise ValueError("world plan --check rejected the generated plan")
    return {
        "path": str(Path(destination).resolve()),
        "plan_sha256": expected_digest,
        "identities": {"world_plan": _file_identity(Path(destination))},
    }


def check_simulate_off_deployment(selector: Any, *, arms: Sequence[str]) -> dict[str, object]:
    if tuple(arms) != ("FULL2", "DROP_C1", "DROP_C2"):
        raise ValueError("deployment check requires exactly the three learned arms")
    q1 = np.zeros((2, 28), dtype=np.float32)
    q2 = np.zeros((2, 28), dtype=np.float32)
    legal = np.zeros((2, 28), dtype=np.bool_)
    legal[0, [3, 7]] = True
    legal[1, [1, 4]] = True
    q1[1, 1] = 1.0
    q2[1, 4] = 2.0
    selected = selector(q1, q2, legal).tolist()
    if selected != [3, 4]:
        raise ValueError("masked Q1+Q2 argmax or lowest-index tie rule drifted")
    return {
        "simulate_off": True,
        "actions_by_arm": {arm: selected for arm in arms},
        "identities": {"synthetic_mask_sha256": hashlib.sha256(legal.tobytes()).hexdigest()},
    }


class _SyntheticEvaluationAdapter:
    def __init__(self, runner_module: Any) -> None:
        self.runner = runner_module
        self._bindings = {
            arm: {
                "arm": arm,
                "routes": [] if arm == "BASELINE" else ["C1", "C2"],
                "checkpoint_sha256": runner_module.canonical_sha256({"arm": arm}),
                "fixed_policy": True,
            }
            for arm in runner_module.ARMS
        }
        self._states = {arm: None for arm in runner_module.ARMS}

    @property
    def policy_bindings(self) -> Mapping[str, object]:
        return self._bindings

    def resume_state_for(self, arm: str) -> object:
        return self._states[arm]

    def restore_resume_states(self, states: Mapping[str, object]) -> None:
        self._states = {arm: dict(states[arm]) for arm in self.runner.ARMS}  # type: ignore[arg-type]

    def run_episode(self, *, arm: str, world: Any, plan_sha256: str, resume_state: Any = None) -> Any:
        previous = world.episode_index - 1
        if previous == 0:
            if resume_state is not None:
                raise ValueError("first synthetic episode unexpectedly has resume state")
        elif resume_state.get("episode_index") != previous:
            raise ValueError("synthetic resume cadence drifted")
        offset = self.runner.ARMS.index(arm)
        total_bits = float(10_000 + 100 * (3 - offset) + world.episode_index)
        receipt = self.runner.EpisodeReceipt(
            schema=self.runner.RECEIPT_SCHEMA,
            status=self.runner.STATUS,
            split=self.runner.SPLIT,
            arm=arm,
            routes=() if arm == "BASELINE" else self.runner.ROUTES,
            episode_index=world.episode_index,
            world_id=world.world_id,
            world_seed=world.world_seed,
            users=self.runner.USERS,
            steps=self.runner.STEPS,
            decision_interval_s=1.0,
            total_bits=total_bits,
            total_energy_j=10.0,
            ratio_of_sums_ee_bits_per_j=total_bits / 10.0,
            served_user_steps=self.runner.USERS * self.runner.STEPS,
            service_opportunities=self.runner.USERS * self.runner.STEPS,
            service_fraction=1.0,
            initial_world_sha256=self.runner.canonical_sha256({"world": world.world_id}),
            field_component=self.runner.FIELD_COMPONENT,
            field_root_digest=world.field_root_digest,
            action_trace_sha256=self.runner.canonical_sha256({"arm": arm, "episode": world.episode_index}),
            plan_sha256=plan_sha256,
            policy_binding=self._bindings[arm],
        )
        receipt.verify()
        self._states[arm] = {"arm": arm, "episode_index": world.episode_index, "plan_sha256": plan_sha256}
        return receipt


def exercise_receipt_cadence_resume(
    world_plan_path: Path,
    output_dir: Path,
    *,
    runner_module: Any,
) -> dict[str, object]:
    plan = runner_module.EvaluationPlan.from_file(world_plan_path)
    adapter = _SyntheticEvaluationAdapter(runner_module)
    evaluation = runner_module.FixedPolicyEvaluationRunner(adapter=adapter, plan=plan)
    summary = evaluation.run(output_dir=output_dir, pause_at=100)
    checkpoint = Path(output_dir) / "checkpoints" / "checkpoint-000100.json"
    rung = Path(output_dir) / "rungs" / "rung-000100.json"
    resumed = runner_module.FixedPolicyEvaluationRunner(
        adapter=_SyntheticEvaluationAdapter(runner_module), plan=plan
    ).run(output_dir=output_dir, pause_at=500, resume_checkpoint=checkpoint)
    if (
        summary["completed_episode"] != 100
        or resumed["completed_episode"] != 500
        or resumed["receipt_count"] != 2000
        or summary["terminal_result_emitted"]
        or resumed["terminal_result_emitted"]
    ):
        raise ValueError("100-episode checkpoint/rung cadence drifted")
    if (Path(output_dir) / "result.json").exists():
        raise ValueError("non-terminal cadence path emitted result.json")
    return {
        "completed_episode": resumed["completed_episode"],
        "receipt_count": resumed["receipt_count"],
        "resumed": True,
        "terminal_result_emitted": False,
        "identities": {"checkpoint": _file_identity(checkpoint), "rung": _file_identity(rung)},
    }


def run_optional_real_diagnostic(
    export_bundle: Mapping[str, object],
    *,
    tle_root: Path,
    output: Path,
    baseline_checkpoint: Path,
    baseline_status: Path,
    diagnostic: Any,
) -> dict[str, object]:
    exports = export_bundle["exports"]
    args = argparse.Namespace(
        tle_root=Path(tle_root),
        output=Path(output),
        learned_checkpoint=[Path(str(item["path"])) for item in exports],
        learned_sha256=[str(item["sha256"]) for item in exports],
        baseline_checkpoint=Path(baseline_checkpoint),
        baseline_status=Path(baseline_status),
        baseline_status_sha256=_file_identity(Path(baseline_status))["sha256"],
    )
    result = diagnostic(args)
    return {
        "status": result["status"],
        "identities": {
            "tle_root": str(Path(tle_root).resolve()),
            "baseline_checkpoint": _file_identity(Path(baseline_checkpoint)),
            "baseline_status": _file_identity(Path(baseline_status)),
        },
    }
