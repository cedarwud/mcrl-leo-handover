#!/usr/bin/env python3
"""Posthoc per-source/per-head C1 gradient diagnostic.

This program is deliberately not a training entry point.  It authenticates the
sealed four-episode C1 carrier states, reconstructs the common initial Main
networks, and uses ``torch.autograd.grad`` on copies of those networks.  It
never constructs an optimizer, calls ``optimizer.step()``, or writes back to a
carrier artifact.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np
import torch
import torch.nn as nn


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "src"))

from mcrl.runtime.q_network import DQNNetwork  # noqa: E402
from smc_er_core import AtomicBundle  # noqa: E402


CLAIM_CEILING = (
    "POSTHOC_NO_STEP_GRADIENT_DIAGNOSTIC_ONLY_"
    "NOT_ROUTING_AUTHORITY_NOT_EFFICACY"
)
AUTHORITY_DIR = REPO / "artifacts" / "smc-er-c1-authority-20260828"
FREEZE_REL = Path(
    "smc-er-c1-postgate-efficacy-freeze-20260828-v1"
)
SCREEN_REL = Path(
    "smc-er-c1-postgate-efficacy-screen-20260828-v1"
)
README_REQUIRED = (
    FREEZE_REL / "c1-efficacy-microscreen-closure-v1.json",
    FREEZE_REL / "c1-efficacy-microscreen-seeds-v1.json",
    SCREEN_REL / "c1-postgate-efficacy-microscreen-raw.json",
    SCREEN_REL / "c1-postgate-efficacy-microscreen-result.json",
    SCREEN_REL / "independent-verification.json",
)
DESCRIPTIVE_CONFIG_KEYS = {
    "training_experiment_kind",
    "training_experiment_id",
    "method_family",
    "phase",
    "comparison_role",
}
EXPECTED_ARM_IDS = {"informed": "F111", "neutral": "A011"}
EXPECTED_PAIRS = 40
EXPECTED_PREFILL = 31
EXPECTED_BLOCKS = 4
EXPECTED_STEPS_PER_BLOCK = 10


class AuditError(RuntimeError):
    """Fail-closed diagnostic contract error."""


@dataclass(frozen=True)
class GradientConfig:
    discount_factor: float
    reward_calibration_enabled: bool
    reward_calibration_scales: tuple[float, float, float]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "GradientConfig":
        gamma = float(value["discount_factor"])
        enabled = bool(value["reward_calibration_enabled"])
        scales = tuple(float(item) for item in value["reward_calibration_scales"])
        if len(scales) != 3:
            raise AuditError("reward calibration must contain exactly three scales")
        if not math.isfinite(gamma) or not 0.0 <= gamma <= 1.0:
            raise AuditError("discount factor is invalid")
        if any(not math.isfinite(item) or item <= 0.0 for item in scales):
            raise AuditError("reward calibration scales must be finite and positive")
        return cls(gamma, enabled, scales)  # type: ignore[arg-type]


@dataclass
class InitialMain:
    online: nn.ModuleList
    targets: nn.ModuleList


class CalibrationLedger:
    """Prove that every audited bundle/head is calibrated exactly once."""

    def __init__(self) -> None:
        self._keys: set[tuple[str, ...]] = set()

    def apply(
        self,
        key: tuple[str, ...],
        raw_rewards: np.ndarray,
        *,
        enabled: bool,
        scale: float,
    ) -> np.ndarray:
        if key in self._keys:
            raise AuditError("reward calibration attempted more than once for " + repr(key))
        self._keys.add(key)
        rewards = np.asarray(raw_rewards, dtype=np.float64).copy()
        if not np.all(np.isfinite(rewards)):
            raise AuditError("raw rewards are non-finite")
        if enabled:
            rewards /= float(scale)
        return rewards

    def __len__(self) -> int:
        return len(self._keys)


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_sha256(path: Path, expected: str, *, label: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", str(expected)):
        raise AuditError(f"{label} has an invalid expected SHA-256")
    if not Path(path).is_file():
        raise AuditError(f"{label} is missing: {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise AuditError(
            f"{label} SHA-256 mismatch: expected {expected}, found {actual}"
        )
    return actual


def load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditError(f"cannot load {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise AuditError(f"{label} must be a JSON object")
    return value


def parse_readme_hashes(path: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    pattern = re.compile(r"^([0-9a-f]{64})\s+(.+)$")
    for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
        match = pattern.fullmatch(raw_line.strip())
        if match is None:
            continue
        relative = match.group(2)
        if relative in hashes and hashes[relative] != match.group(1):
            raise AuditError(f"README binds {relative} to conflicting hashes")
        hashes[relative] = match.group(1)
    return hashes


def main_source_tree_hash(repo: Path) -> tuple[str, int]:
    root = Path(repo) / "src" / "mcrl"
    rows = [
        {
            "path": path.relative_to(root).as_posix(),
            "sha256": sha256_file(path),
        }
        for path in sorted(root.rglob("*.py"))
        if "__pycache__" not in path.parts
    ]
    if not rows:
        raise AuditError("Main source tree is empty")
    return hashlib.sha256(canonical_json(rows)).hexdigest(), len(rows)


def normalise_config(config: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(config))
    for key in DESCRIPTIVE_CONFIG_KEYS:
        result.pop(key, None)
    return result


def tensor_modules_sha256(modules: Sequence[nn.Module]) -> str:
    digest = hashlib.sha256()
    for module_index, module in enumerate(modules):
        digest.update(str(module_index).encode("ascii"))
        for key, tensor in module.state_dict().items():
            value = tensor.detach().cpu().contiguous()
            digest.update(key.encode("utf-8"))
            digest.update(str(value.dtype).encode("ascii"))
            digest.update(canonical_json(list(value.shape)))
            digest.update(value.numpy().tobytes(order="C"))
    return digest.hexdigest()


def parameter_snapshot(main: InitialMain) -> dict[str, str]:
    return {
        "online_sha256": tensor_modules_sha256(main.online),
        "target_sha256": tensor_modules_sha256(main.targets),
    }


def reconstruct_initial_main(
    config: Mapping[str, Any],
    *,
    state_dim: int,
    action_dim: int,
    train_seed: int,
) -> InitialMain:
    hidden = tuple(int(item) for item in config["hidden_layers"])
    activation = str(config["activation"])
    if state_dim < 1 or action_dim < 1 or not hidden:
        raise AuditError("initial Main dimensions are invalid")
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(int(train_seed))
        online = nn.ModuleList(
            [
                DQNNetwork(state_dim, action_dim, hidden, activation)
                for _ in range(3)
            ]
        )
    targets = copy.deepcopy(online)
    for target in targets:
        target.eval()
    return InitialMain(online=online, targets=targets)


def _bundle_key(bundle: AtomicBundle) -> tuple[int, int]:
    return int(bundle.block_id), int(bundle.step_index)


def _unique_bundle_map(
    bundles: Sequence[AtomicBundle], *, expected_source: str
) -> dict[tuple[int, int], AtomicBundle]:
    result: dict[tuple[int, int], AtomicBundle] = {}
    ids: set[str] = set()
    for bundle in bundles:
        if not isinstance(bundle, AtomicBundle):
            raise AuditError("replay contains a non-AtomicBundle item")
        if bundle.source_id != expected_source:
            raise AuditError(
                f"{expected_source} replay contains source {bundle.source_id}"
            )
        if bundle.bundle_id in ids:
            raise AuditError(f"duplicate bundle ID {bundle.bundle_id}")
        ids.add(bundle.bundle_id)
        key = _bundle_key(bundle)
        if key in result:
            raise AuditError(
                f"duplicate {expected_source} bundle for block/step {key}"
            )
        result[key] = bundle
    return result


def pair_online_bundles(
    main_items: Sequence[AtomicBundle],
    c1_items: Sequence[AtomicBundle],
    *,
    expected_count: int,
    expected_prefill: int | None = None,
    expected_keys: set[tuple[int, int]] | None = None,
) -> tuple[list[tuple[AtomicBundle, AtomicBundle]], int]:
    main_online = list(main_items)
    prefill = [item for item in c1_items if item.bundle_id.startswith("C1-EXP-")]
    c1_online = [item for item in c1_items if not item.bundle_id.startswith("C1-EXP-")]
    if expected_prefill is not None and len(prefill) != expected_prefill:
        raise AuditError(
            f"C1 prefill count mismatch: expected {expected_prefill}, found {len(prefill)}"
        )
    if len(main_online) != expected_count or len(c1_online) != expected_count:
        raise AuditError(
            "online bundle count mismatch: "
            f"Main={len(main_online)}, C1={len(c1_online)}, expected={expected_count}"
        )
    main_map = _unique_bundle_map(main_online, expected_source="Main")
    c1_map = _unique_bundle_map(c1_online, expected_source="C1")
    if set(main_map) != set(c1_map):
        missing_main = sorted(set(c1_map) - set(main_map))
        missing_c1 = sorted(set(main_map) - set(c1_map))
        raise AuditError(
            f"Main/C1 pair keys differ; missing_main={missing_main}, missing_c1={missing_c1}"
        )
    if expected_keys is not None and set(main_map) != expected_keys:
        raise AuditError("online bundle keys do not match the sealed block/step grid")
    keys = sorted(main_map)
    return [(main_map[key], c1_map[key]) for key in keys], len(prefill)


def _flat_gradient(
    loss: torch.Tensor, parameters: Sequence[torch.nn.Parameter]
) -> torch.Tensor:
    gradients = torch.autograd.grad(
        loss,
        tuple(parameters),
        retain_graph=False,
        create_graph=False,
        allow_unused=False,
    )
    return torch.cat(
        [gradient.detach().reshape(-1).to(dtype=torch.float64) for gradient in gradients]
    )


def td_loss_and_gradient(
    online: nn.Module,
    target: nn.Module,
    bundle: AtomicBundle,
    *,
    objective: int,
    config: GradientConfig,
    calibration_ledger: CalibrationLedger,
    calibration_key: tuple[str, ...],
) -> tuple[float, torch.Tensor, int]:
    if objective not in (0, 1, 2):
        raise AuditError("objective must be 0, 1, or 2")
    parameters = tuple(online.parameters())
    rows = bundle.admissible_rows()
    raw_rewards = bundle.rewards[rows, objective]
    calibrated = calibration_ledger.apply(
        calibration_key,
        raw_rewards,
        enabled=config.reward_calibration_enabled,
        scale=config.reward_calibration_scales[objective],
    )
    if rows.size == 0:
        loss = sum(parameter.sum() * 0.0 for parameter in parameters)
        return 0.0, _flat_gradient(loss, parameters), 0

    states = torch.tensor(bundle.states[rows], dtype=torch.float32)
    actions = torch.tensor(bundle.actions[rows], dtype=torch.long).unsqueeze(1)
    next_states = torch.tensor(bundle.next_states[rows], dtype=torch.float32)
    next_masks = torch.tensor(bundle.next_masks[rows], dtype=torch.bool)
    rewards = torch.tensor(calibrated, dtype=torch.float32)
    done = torch.full((rows.size,), float(bundle.done), dtype=torch.float32)

    current = online(states).gather(1, actions).squeeze(1)
    with torch.no_grad():
        next_values = target(next_states).masked_fill(~next_masks, -1e9)
        td_target = rewards + config.discount_factor * next_values.max(dim=1).values * (
            1.0 - done
        )
    loss = torch.mean((current - td_target) ** 2)
    if not bool(torch.isfinite(loss)):
        raise AuditError("TD loss is non-finite")
    flat = _flat_gradient(loss, parameters)
    if not bool(torch.isfinite(flat).all()):
        raise AuditError("TD gradient is non-finite")
    return float(loss.detach().item()), flat, int(rows.size)


def vector_norms(vector: torch.Tensor) -> dict[str, float | int]:
    count = int(vector.numel())
    l2 = float(torch.linalg.vector_norm(vector).item())
    rms = l2 / math.sqrt(count) if count else 0.0
    return {"numel": count, "l2": l2, "rms": rms}


def cosine_metric(
    left: torch.Tensor, right: torch.Tensor
) -> dict[str, float | str | None]:
    left_norm = float(torch.linalg.vector_norm(left).item())
    right_norm = float(torch.linalg.vector_norm(right).item())
    if left_norm == 0.0 or right_norm == 0.0:
        return {
            "status": "UNDEFINED_ZERO_NORM",
            "value": None,
            "dot_product": float(torch.dot(left, right).item()),
        }
    value = float(torch.dot(left, right).item()) / (left_norm * right_norm)
    return {
        "status": "DEFINED",
        "value": max(-1.0, min(1.0, value)),
        "dot_product": float(torch.dot(left, right).item()),
    }


def gradient_comparison(main: torch.Tensor, c1: torch.Tensor) -> dict[str, Any]:
    if main.shape != c1.shape:
        raise AuditError("Main and C1 gradients have different shapes")
    return {
        "main": vector_norms(main),
        "c1": vector_norms(c1),
        "main_vs_c1_cosine": cosine_metric(main, c1),
        "combined_50_50": vector_norms(0.50 * main + 0.50 * c1),
        "combined_75_25": vector_norms(0.75 * main + 0.25 * c1),
    }


def numeric_summary(values: Sequence[float]) -> dict[str, float | int | None]:
    finite = [float(value) for value in values if math.isfinite(float(value))]
    if not finite:
        return {"count": 0, "mean": None, "median": None, "min": None, "max": None}
    return {
        "count": len(finite),
        "mean": math.fsum(finite) / len(finite),
        "median": float(median(finite)),
        "min": min(finite),
        "max": max(finite),
    }


def aggregate_heads(pair_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    aggregates: list[dict[str, Any]] = []
    for objective in range(3):
        heads = [row["heads"][objective] for row in pair_rows]
        cosine_values = [
            head["gradients"]["main_vs_c1_cosine"]["value"]
            for head in heads
            if head["gradients"]["main_vs_c1_cosine"]["value"] is not None
        ]
        weighted_main = [0.75 * head["gradients"]["main"]["l2"] for head in heads]
        weighted_c1 = [0.25 * head["gradients"]["c1"]["l2"] for head in heads]
        weighted_main_rms = math.sqrt(
            math.fsum(value * value for value in weighted_main) / len(weighted_main)
        )
        weighted_c1_rms = math.sqrt(
            math.fsum(value * value for value in weighted_c1) / len(weighted_c1)
        )
        aggregates.append(
            {
                "objective": objective,
                "pairs": len(heads),
                "main_loss": numeric_summary([head["main_loss"] for head in heads]),
                "c1_loss": numeric_summary([head["c1_loss"] for head in heads]),
                "main_gradient_l2": numeric_summary(
                    [head["gradients"]["main"]["l2"] for head in heads]
                ),
                "c1_gradient_l2": numeric_summary(
                    [head["gradients"]["c1"]["l2"] for head in heads]
                ),
                "main_gradient_rms": numeric_summary(
                    [head["gradients"]["main"]["rms"] for head in heads]
                ),
                "c1_gradient_rms": numeric_summary(
                    [head["gradients"]["c1"]["rms"] for head in heads]
                ),
                "cosine": {
                    **numeric_summary(cosine_values),
                    "undefined_zero_norm_count": len(heads) - len(cosine_values),
                },
                "combined_50_50_l2": numeric_summary(
                    [head["gradients"]["combined_50_50"]["l2"] for head in heads]
                ),
                "combined_75_25_l2": numeric_summary(
                    [head["gradients"]["combined_75_25"]["l2"] for head in heads]
                ),
                "fixed_75_25_weighted_norm_diagnostic": {
                    "weighted_main_l2_rms_across_pairs": weighted_main_rms,
                    "weighted_c1_l2_rms_across_pairs": weighted_c1_rms,
                    "c1_not_larger_than_main": weighted_c1_rms <= weighted_main_rms,
                    "decision_use": "DESCRIPTIVE_ONLY_NO_DOSE_SELECTION",
                },
            }
        )
    return aggregates


def _validate_authority(authority_dir: Path) -> dict[str, Any]:
    authority_dir = Path(authority_dir).resolve()
    readme = authority_dir / "README.md"
    if not readme.is_file():
        raise AuditError(f"authority README is missing: {readme}")
    readme_hashes = parse_readme_hashes(readme)
    verified: dict[str, str] = {"README.md": sha256_file(readme)}
    for relative in README_REQUIRED:
        key = relative.as_posix()
        if key not in readme_hashes:
            raise AuditError(f"authority README does not bind {key}")
        path = authority_dir / relative
        verified[key] = verify_sha256(path, readme_hashes[key], label=key)

    closure_path = authority_dir / README_REQUIRED[0]
    seeds_path = authority_dir / README_REQUIRED[1]
    raw_path = authority_dir / README_REQUIRED[2]
    result_path = authority_dir / README_REQUIRED[3]
    independent_path = authority_dir / README_REQUIRED[4]
    closure = load_json_object(closure_path, label="closure receipt")
    seeds = load_json_object(seeds_path, label="seed manifest")
    raw = load_json_object(raw_path, label="raw screen receipt")
    result = load_json_object(result_path, label="screen result")
    independent = load_json_object(independent_path, label="independent verification")

    if any(
        payload.get("claim_ceiling") != "ONE_SEED_4EP_DIRECTIONAL_SCREEN_NOT_ROUTING_AUTHORITY_NOT_CHAPTER5"
        for payload in (closure, raw, result)
    ):
        raise AuditError("sealed screen claim ceiling drift")
    if result.get("decision") != "STOP_AND_REDESIGN_C1" or result.get("status") != "FAIL":
        raise AuditError("sealed screen decision drift")
    if independent.get("receipt_valid") is not True:
        raise AuditError("independent verification is not valid")
    if result.get("authority", {}).get("raw_rows_sha256") != verified[
        README_REQUIRED[2].as_posix()
    ]:
        raise AuditError("screen result does not bind the archived raw rows")
    if result.get("authority", {}).get("seed_manifest_sha256") != verified[
        README_REQUIRED[1].as_posix()
    ]:
        raise AuditError("screen result does not bind the archived seed manifest")

    tree_hash, tree_count = main_source_tree_hash(REPO)
    if (
        tree_hash != seeds.get("main_source_tree_sha256")
        or tree_hash != closure.get("bindings", {}).get("main_source_tree_sha256")
        or tree_count != int(seeds.get("main_source_file_count", -1))
    ):
        raise AuditError("current Main source tree does not match sealed authority")
    routing_core = HERE / "smc_er_core.py"
    verify_sha256(
        routing_core,
        str(seeds.get("routing_core_sha256")),
        label="sealed routing core",
    )
    verified["code/smc_er_core.py"] = sha256_file(routing_core)
    verified["code/main_source_tree"] = tree_hash

    carrier_paths: dict[str, Path] = {}
    for arm in ("informed", "neutral"):
        path = authority_dir / SCREEN_REL / arm / "carrier-state.pt"
        branch = raw.get("branch_results", {}).get(arm, {})
        expected = branch.get("carrier_state_sha256")
        verified[f"carrier/{arm}"] = verify_sha256(
            path, str(expected), label=f"{arm} carrier state"
        )
        carrier_paths[arm] = path
    return {
        "authority_dir": authority_dir,
        "closure": closure,
        "seeds": seeds,
        "raw": raw,
        "result": result,
        "independent": independent,
        "carrier_paths": carrier_paths,
        "verified_hashes": verified,
        "main_source_file_count": tree_count,
    }


def _load_carrier(path: Path, *, arm: str, seeds: Mapping[str, Any]) -> dict[str, Any]:
    try:
        payload = torch.load(path, map_location="cpu", weights_only=False)
    except Exception as exc:  # pragma: no cover - exact torch pickle errors vary
        raise AuditError(f"cannot load authenticated {arm} carrier state: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema") != "smc-er-carrier-state-v1":
        raise AuditError(f"{arm} carrier state has the wrong schema")
    if payload.get("episodes_completed") != EXPECTED_BLOCKS:
        raise AuditError(f"{arm} carrier episode count drift")
    main_state = payload.get("main_training_state")
    replays = payload.get("bundle_replays")
    if not isinstance(main_state, Mapping) or not isinstance(replays, Mapping):
        raise AuditError(f"{arm} carrier lacks Main state or bundle replays")
    if main_state.get("train_seed") != seeds.get("training_seed"):
        raise AuditError(f"{arm} carrier training seed drift")
    if main_state.get("env_seed") != seeds.get("environment_seed"):
        raise AuditError(f"{arm} carrier environment seed drift")
    if main_state.get("mobility_seed") != seeds.get("mobility_seed"):
        raise AuditError(f"{arm} carrier mobility seed drift")
    config = main_state.get("trainer_config")
    if not isinstance(config, Mapping):
        raise AuditError(f"{arm} carrier trainer config is missing")
    if config.get("training_experiment_id") != EXPECTED_ARM_IDS[arm]:
        raise AuditError(f"{arm} carrier experiment ID drift")
    return payload


def _audit_arm(
    arm: str,
    carrier: Mapping[str, Any],
    initial: InitialMain,
    config: GradientConfig,
    calibration_ledger: CalibrationLedger,
) -> dict[str, Any]:
    replays = carrier["bundle_replays"]
    main_items = replays["Main"]["items"]
    c1_items = replays["C1"]["items"]
    expected_keys = {
        (block, step)
        for block in range(EXPECTED_BLOCKS)
        for step in range(EXPECTED_STEPS_PER_BLOCK)
    }
    pairs, prefill_count = pair_online_bundles(
        main_items,
        c1_items,
        expected_count=EXPECTED_PAIRS,
        expected_prefill=EXPECTED_PREFILL,
        expected_keys=expected_keys,
    )
    before = parameter_snapshot(initial)
    pair_rows: list[dict[str, Any]] = []
    for main_bundle, c1_bundle in pairs:
        heads: list[dict[str, Any]] = []
        for objective in range(3):
            main_loss, main_gradient, main_rows = td_loss_and_gradient(
                initial.online[objective],
                initial.targets[objective],
                main_bundle,
                objective=objective,
                config=config,
                calibration_ledger=calibration_ledger,
                calibration_key=(arm, "Main", main_bundle.bundle_id, str(objective)),
            )
            c1_loss, c1_gradient, c1_rows = td_loss_and_gradient(
                initial.online[objective],
                initial.targets[objective],
                c1_bundle,
                objective=objective,
                config=config,
                calibration_ledger=calibration_ledger,
                calibration_key=(arm, "C1", c1_bundle.bundle_id, str(objective)),
            )
            heads.append(
                {
                    "objective": objective,
                    "main_rows": main_rows,
                    "c1_rows": c1_rows,
                    "main_loss": main_loss,
                    "c1_loss": c1_loss,
                    "gradients": gradient_comparison(main_gradient, c1_gradient),
                }
            )
        pair_rows.append(
            {
                "block_id": int(main_bundle.block_id),
                "step_index": int(main_bundle.step_index),
                "main_bundle_id": main_bundle.bundle_id,
                "c1_bundle_id": c1_bundle.bundle_id,
                "heads": heads,
            }
        )
    after = parameter_snapshot(initial)
    grad_slots_none = all(
        parameter.grad is None
        for module in initial.online
        for parameter in module.parameters()
    )
    if before != after or not grad_slots_none:
        raise AuditError(f"{arm} initial Main parameters or grad slots were mutated")
    return {
        "online_main_bundles": len(pairs),
        "online_c1_bundles": len(pairs),
        "excluded_c1_exp_prefill_bundles": prefill_count,
        "exact_pairs": len(pairs),
        "parameter_bytes_before": before,
        "parameter_bytes_after": after,
        "parameter_bytes_unchanged": before == after,
        "parameter_grad_slots_all_none": grad_slots_none,
        "head_aggregates": aggregate_heads(pair_rows),
        "pair_rows": pair_rows,
    }


def run_audit(authority_dir: Path = AUTHORITY_DIR) -> dict[str, Any]:
    authority = _validate_authority(authority_dir)
    seeds = authority["seeds"]
    carriers = {
        arm: _load_carrier(path, arm=arm, seeds=seeds)
        for arm, path in authority["carrier_paths"].items()
    }
    main_states = {
        arm: carrier["main_training_state"] for arm, carrier in carriers.items()
    }
    normalised_configs = {
        arm: normalise_config(state["trainer_config"])
        for arm, state in main_states.items()
    }
    if normalised_configs["informed"] != normalised_configs["neutral"]:
        raise AuditError("informed and neutral configs differ beyond descriptive metadata")
    dimensions = {
        (int(state["state_dim"]), int(state["action_dim"]))
        for state in main_states.values()
    }
    if len(dimensions) != 1:
        raise AuditError("informed and neutral Main dimensions differ")
    state_dim, action_dim = next(iter(dimensions))
    train_seed = int(seeds["training_seed"])
    initial_models = {
        arm: reconstruct_initial_main(
            normalised_configs[arm],
            state_dim=state_dim,
            action_dim=action_dim,
            train_seed=train_seed,
        )
        for arm in ("informed", "neutral")
    }
    initial_snapshots = {
        arm: parameter_snapshot(model) for arm, model in initial_models.items()
    }
    initial_exact = initial_snapshots["informed"] == initial_snapshots["neutral"]
    online_target_exact = all(
        snapshot["online_sha256"] == snapshot["target_sha256"]
        for snapshot in initial_snapshots.values()
    )
    if not initial_exact or not online_target_exact:
        raise AuditError("reconstructed initial Main online/target parity failed")

    gradient_config = GradientConfig.from_mapping(normalised_configs["informed"])
    calibration_ledger = CalibrationLedger()
    arms = {
        arm: _audit_arm(
            arm,
            carriers[arm],
            initial_models[arm],
            gradient_config,
            calibration_ledger,
        )
        for arm in ("informed", "neutral")
    }
    expected_calibrations = 2 * EXPECTED_PAIRS * 2 * 3
    if len(calibration_ledger) != expected_calibrations:
        raise AuditError(
            "calibration application count mismatch: "
            f"expected {expected_calibrations}, found {len(calibration_ledger)}"
        )

    script = Path(__file__).resolve()
    test_file = HERE / "test_audit_c1_source_head_gradients.py"
    code_hashes = {
        "audit_script": sha256_file(script),
        "smc_er_core": sha256_file(HERE / "smc_er_core.py"),
        "q_network": sha256_file(REPO / "src" / "mcrl" / "runtime" / "q_network.py"),
        "modqn": sha256_file(REPO / "src" / "mcrl" / "algorithms" / "modqn.py"),
    }
    if test_file.is_file():
        code_hashes["audit_tests"] = sha256_file(test_file)
    return {
        "schema": "smc-er-c1-posthoc-source-head-gradient-audit-v1",
        "status": "PASS",
        "claim_ceiling": CLAIM_CEILING,
        "no_optimizer_step": True,
        "optimizer_constructed": False,
        "carrier_files_opened_read_only": True,
        "authority": {
            "root": str(authority["authority_dir"]),
            "verified_input_hashes": authority["verified_hashes"],
            "main_source_file_count": authority["main_source_file_count"],
            "code_hashes": code_hashes,
            "normalised_config_sha256": hashlib.sha256(
                canonical_json(normalised_configs["informed"])
            ).hexdigest(),
        },
        "initial_main_parity": {
            "train_seed": train_seed,
            "state_dim": state_dim,
            "action_dim": action_dim,
            "informed": initial_snapshots["informed"],
            "neutral": initial_snapshots["neutral"],
            "online_and_target_bytes_exact_across_arms": initial_exact,
            "each_initial_target_exact_copy_of_online": online_target_exact,
        },
        "calibration": {
            "enabled": gradient_config.reward_calibration_enabled,
            "scales": list(gradient_config.reward_calibration_scales),
            "application_count": len(calibration_ledger),
            "expected_application_count": expected_calibrations,
            "exactly_once_per_arm_source_bundle_head": True,
        },
        "gradient_weights": {
            "current_50_50": {"main": 0.50, "c1": 0.50},
            "fixed_diagnostic_75_25": {"main": 0.75, "c1": 0.25},
            "selection_or_tuning_authority": False,
        },
        "first_order_hypothetical_action_rank": {
            "status": "UNSUPPORTED",
            "reason": (
                "The sealed campaign defines no parameter-space perturbation operator "
                "or step size. Raw gradients do not uniquely define the Adam update, "
                "and selecting a scale posthoc would be an unsealed tuning choice."
            ),
        },
        "arms": arms,
    }


def write_json_exclusive(path: Path, payload: Mapping[str, Any]) -> None:
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
            stream.write("\n")
    except FileExistsError as exc:
        raise AuditError(f"refusing to overwrite existing output: {target}") from exc


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--authority-dir", type=Path, default=AUTHORITY_DIR)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    output = args.output.expanduser().resolve()
    if output.exists():
        raise AuditError(f"refusing to overwrite existing output: {output}")
    payload = run_audit(args.authority_dir)
    write_json_exclusive(output, payload)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "claim_ceiling": payload["claim_ceiling"],
                "output": str(output),
                "output_sha256": sha256_file(output),
                "pairs_per_arm": {
                    arm: payload["arms"][arm]["exact_pairs"]
                    for arm in ("informed", "neutral")
                },
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
