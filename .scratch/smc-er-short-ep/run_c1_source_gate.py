#!/usr/bin/env python3
"""Run frozen C1 Source Gate A without training or Main replay transfer."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import pickle
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "src"))

from smc_er_roles import (  # noqa: E402
    local_snr_greedy_actions,
    main_greedy_actions,
    masked_uniform_actions,
)
from sweep_evaluation import (  # noqa: E402
    _trainer_config,
    evaluation_rngs,
    make_environment,
    ratio_of_sums,
)
from mcrl.algorithms.modqn import MODQNTrainer  # noqa: E402
from mcrl.artifacts import read_checkpoint  # noqa: E402
from mcrl.env.action_contract import Association, UNSERVED  # noqa: E402
from mcrl.env.constants import DECISION_STEP_S, TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.env.tle import TleArchive  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    CANONICAL_PREREG,
    CANONICAL_PREREG_BYTE_SHA256,
    assert_ephemeris_matches_record,
)


SPEC = HERE / "C1-SOURCE-GATE-A-SPEC-2026-08-27.md"
METHOD = REPO / "docs" / "MULTI-CATFISH-PAPER-ALGORITHM-V0.4-2026-08-27.md"
SEED_SCHEMA = "smc-er-c1-source-gate-a-seeds-v1"
RESULT_SCHEMA = "smc-er-c1-source-gate-a-result-v1"
CONTROL_NAMESPACE = "SMC-ER-C1-SOURCE-GATE-A-CONTROL-v1"
EXPECTED_SEEDS = 5
EXPECTED_STEPS = 10
EXPECTED_USERS = 100
MIN_POSITIVE_SEEDS = 4
MAX_SERVICE_DECLINE = 0.005


@dataclass(frozen=True)
class SourceMetrics:
    useful_bits: float
    system_energy_j: float
    served_user_intervals: int
    user_intervals: int
    zero_power_intervals: int
    reward_sum: tuple[float, float, float]

    @property
    def ee_bits_per_j(self) -> float:
        return ratio_of_sums(self.useful_bits, self.system_energy_j)

    @property
    def served_fraction(self) -> float:
        return (
            self.served_user_intervals / self.user_intervals
            if self.user_intervals
            else 0.0
        )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_json(value: Any) -> bytes:
    def default(item: Any) -> Any:
        if isinstance(item, np.ndarray):
            return item.tolist()
        if isinstance(item, np.generic):
            return item.item()
        raise TypeError(f"cannot serialize {type(item).__name__}")

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=default,
    ).encode("utf-8")


def _state_sha(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _object_sha(value: Any) -> str:
    return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()


def _array_sha(value: Any) -> str | None:
    return None if value is None else _object_sha(np.asarray(value))


def _rng_sha(rng: np.random.Generator | None) -> str | None:
    return None if rng is None else _state_sha(rng.bit_generator.state)


def _association_receipt(value: Any) -> dict[str, Any]:
    if isinstance(value, Association):
        return {
            "kind": "association",
            "norad_id": int(value.norad_id),
            "cell_id": int(value.cell_id),
        }
    if value is None:
        return {"kind": "episode_start"}
    if isinstance(value, type(UNSERVED)):
        return {"kind": "unserved"}
    raise TypeError(f"unexpected association state: {value!r}")


def anchor_fingerprint(wrapped: Any, env_rng: np.random.Generator) -> str:
    """Hash every mutable surface evaluate_actions is allowed to preserve."""

    environment = wrapped.environment
    driver = environment.driver
    tracker = driver._tracker
    satellites = driver._satellites
    receipt = {
        "wrapper": {
            "epoch": None if wrapped._epoch is None else wrapped._epoch.isoformat(),
            "last_outcome": (
                None
                if wrapped._last_outcome is None
                else _object_sha(wrapped._last_outcome)
            ),
        },
        "environment": {
            "step_index": int(environment._step_index),
            "started": bool(environment._started),
            "ledgers": [
                {
                    "previous": _association_receipt(ledger.previous),
                    "started": bool(ledger._started),
                }
                for ledger in environment._ledgers
            ],
            "segments": _object_sha(environment._segments),
            "previous_radiating": _object_sha(environment._previous_radiating),
            "previous_demand": [
                [int(key[0]), int(key[1]), int(value)]
                for key, value in sorted(environment._previous_demand.items())
            ],
            "previous_association": [
                _association_receipt(value)
                for value in environment._previous_association
            ],
            "candidates": (
                None
                if environment._candidates is None
                else _object_sha(environment._candidates)
            ),
            "pending_segment_age": _array_sha(environment._pending_segment_age),
            "mobility_rng": _rng_sha(environment._mobility_rng),
            "age_rng": _rng_sha(environment._age_rng),
        },
        "scenario": {
            "step_index": int(driver._step_index),
            "start_utc": (
                None if driver._start_utc is None else driver._start_utc.isoformat()
            ),
            "frozen_window": _array_sha(driver._frozen_window_norad_ids),
            "user_xy": _array_sha(driver._users._xy_km),
            "user_heading": _array_sha(driver._users._heading_rad),
            "dwell_anchors": _array_sha(driver._dwell._anchors),
            "satellite_ids": (
                None if satellites is None else _array_sha(satellites.norad_ids)
            ),
            "tracker": (
                None
                if tracker is None
                else {
                    "latched": _array_sha(tracker._latched),
                    "condition_active": _array_sha(tracker._condition_active),
                    "condition_started": _array_sha(tracker._condition_started),
                    "ttt_elapsed": _array_sha(tracker._ttt_elapsed),
                    "steps_seen": int(tracker._steps_seen),
                    "primed": bool(tracker._primed),
                }
            ),
        },
        "environment_rng": _rng_sha(env_rng),
    }
    return _state_sha(receipt)


def control_rng(seed: int) -> np.random.Generator:
    encoded = _canonical_json([CONTROL_NAMESPACE, int(seed)])
    integer = int.from_bytes(hashlib.sha256(encoded).digest()[:16], "big")
    return np.random.Generator(np.random.PCG64(np.random.SeedSequence(integer)))


def _metrics(rows: Sequence[Mapping[str, Any]]) -> SourceMetrics:
    useful_bits = math.fsum(float(row["throughput_bps"]) * DECISION_STEP_S for row in rows)
    energy = math.fsum(float(row["power_w"]) * DECISION_STEP_S for row in rows)
    reward = tuple(
        math.fsum(float(row["reward_sum"][index]) for row in rows)
        for index in range(3)
    )
    return SourceMetrics(
        useful_bits=useful_bits,
        system_energy_j=energy,
        served_user_intervals=sum(int(row["served"]) for row in rows),
        user_intervals=sum(int(row["users"]) for row in rows),
        zero_power_intervals=sum(int(float(row["power_w"]) == 0.0) for row in rows),
        reward_sum=(float(reward[0]), float(reward[1]), float(reward[2])),
    )


def decide_gate(
    seed_rows: Sequence[Mapping[str, Any]], *, guard_failures: Sequence[str]
) -> dict[str, Any]:
    if len(seed_rows) != EXPECTED_SEEDS:
        raise ValueError("Source Gate A requires exactly five seed rows")
    deltas = [float(row["delta_ee_bits_per_j"]) for row in seed_rows]
    mean_delta = float(np.mean(np.asarray(deltas, dtype=np.float64)))
    positive = sum(delta > 0.0 for delta in deltas)
    local_served = math.fsum(float(row["local_served_fraction"]) for row in seed_rows) / EXPECTED_SEEDS
    control_served = math.fsum(float(row["control_served_fraction"]) for row in seed_rows) / EXPECTED_SEEDS
    service_delta = local_served - control_served
    checks = {
        "mean_delta_ee_positive": mean_delta > 0.0,
        "positive_seeds_at_least_4_of_5": positive >= MIN_POSITIVE_SEEDS,
        "served_fraction_noninferior": service_delta >= -MAX_SERVICE_DECLINE,
        "all_guards_pass": not guard_failures,
    }
    passed = all(checks.values())
    return {
        "status": "PASS" if passed else "FAIL",
        "decision": "PASS_TO_C1_CONSUMER_GATE" if passed else "DROP_C1_SOURCE_VERSION",
        "checks": checks,
        "mean_seed_delta_ee_bits_per_j": mean_delta,
        "positive_seed_count": positive,
        "mean_local_served_fraction": local_served,
        "mean_control_served_fraction": control_served,
        "served_fraction_delta": service_delta,
        "guard_failures": list(dict.fromkeys(str(item) for item in guard_failures)),
    }


def _validate_evaluation(evaluation: Any, *, users: int, label: str) -> dict[str, Any]:
    throughput = float(evaluation.energy.system_throughput_bps)
    power = float(evaluation.energy.system_consumed_power_w)
    rewards = np.asarray(evaluation.reward_matrix, dtype=np.float64)
    if not math.isfinite(throughput) or throughput < 0.0:
        raise RuntimeError(f"{label} throughput is invalid")
    if not math.isfinite(power) or power < 0.0:
        raise RuntimeError(f"{label} power is invalid")
    if rewards.shape != (users, 3) or not np.all(np.isfinite(rewards)):
        raise RuntimeError(f"{label} reward matrix is invalid")
    if power == 0.0 and throughput != 0.0:
        raise RuntimeError(f"{label} has positive throughput at zero power")
    return {
        "throughput_bps": throughput,
        "power_w": power,
        "ee_bits_per_j": ratio_of_sums(
            throughput * DECISION_STEP_S, power * DECISION_STEP_S
        ),
        "served": int(evaluation.resolution.served_count),
        "users": int(users),
        "reward_sum": rewards.sum(axis=0).tolist(),
    }


def run_seed(
    *,
    archive: TleArchive,
    checkpoint_path: Path,
    checkpoint_payload: Any,
    checkpoint_sha256: str,
    seed: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    environment = make_environment(archive, users=EXPECTED_USERS)
    environment.assert_ready_to_train()
    trainer = MODQNTrainer(
        environment,
        _trainer_config(checkpoint_payload.trainer_config),
        train_seed=int(checkpoint_payload.train_seed),
        env_seed=int(checkpoint_payload.env_seed),
        mobility_seed=int(checkpoint_payload.mobility_seed),
        device="cpu",
    )
    trainer.load_checkpoint(checkpoint_path, load_optimizers=False)
    env_rng, mobility_rng = evaluation_rngs(seed)
    uniform_rng = control_rng(seed)
    states, masks, observation = environment.reset(env_rng, mobility_rng)
    local_rows: list[dict[str, Any]] = []
    control_rows: list[dict[str, Any]] = []
    paired_rows: list[dict[str, Any]] = []
    for _ in range(EXPECTED_STEPS):
        step = int(observation.step_index)
        before = anchor_fingerprint(environment, env_rng)
        local_actions, local_probabilities = local_snr_greedy_actions(states, masks)
        control_actions, control_probabilities = masked_uniform_actions(masks, uniform_rng)
        local = environment.environment.evaluate_actions(local_actions, env_rng)
        control = environment.environment.evaluate_actions(control_actions, env_rng)
        after = anchor_fingerprint(environment, env_rng)
        if before != after:
            raise RuntimeError("evaluate_actions mutated the common source-gate anchor")
        local_row = _validate_evaluation(local, users=EXPECTED_USERS, label="C1 source")
        control_row = _validate_evaluation(control, users=EXPECTED_USERS, label="C1 control")
        local_rows.append(local_row)
        control_rows.append(control_row)
        paired_rows.append(
            {
                "seed": int(seed),
                "step": step,
                "anchor_fingerprint_sha256": before,
                "checkpoint_sha256": checkpoint_sha256,
                "local": local_row,
                "control": control_row,
                "delta_ee_bits_per_j": (
                    float(local_row["ee_bits_per_j"])
                    - float(control_row["ee_bits_per_j"])
                ),
                "local_actions": np.asarray(local_actions, dtype=np.int32).tolist(),
                "control_actions": np.asarray(control_actions, dtype=np.int32).tolist(),
                "local_behavior_probabilities": local_probabilities.tolist(),
                "control_behavior_probabilities": control_probabilities.tolist(),
            }
        )
        encoded = trainer.encode_states(states)
        reference_actions = main_greedy_actions(trainer, encoded, masks)
        result = environment.step(reference_actions, env_rng)
        states, masks = result.user_states, result.action_masks
        observation = environment.last_outcome.observation
        if result.done:
            break
    if len(paired_rows) != EXPECTED_STEPS:
        raise RuntimeError("source gate episode ended before ten common anchors")
    local_metrics = _metrics(local_rows)
    control_metrics = _metrics(control_rows)
    seed_row = {
        "seed": int(seed),
        "local": asdict(local_metrics) | {
            "ee_bits_per_j": local_metrics.ee_bits_per_j,
            "served_fraction": local_metrics.served_fraction,
        },
        "control": asdict(control_metrics) | {
            "ee_bits_per_j": control_metrics.ee_bits_per_j,
            "served_fraction": control_metrics.served_fraction,
        },
        "delta_ee_bits_per_j": local_metrics.ee_bits_per_j - control_metrics.ee_bits_per_j,
        "local_served_fraction": local_metrics.served_fraction,
        "control_served_fraction": control_metrics.served_fraction,
    }
    return seed_row, paired_rows


def _read_seed_manifest(path: Path, *, checkpoint_sha256: str) -> tuple[int, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping) or payload.get("schema") != SEED_SCHEMA:
        raise RuntimeError("C1 seed manifest schema mismatch")
    if payload.get("spec_sha256") != sha256_file(SPEC):
        raise RuntimeError("C1 Source Gate A spec hash drift")
    if payload.get("checkpoint_sha256") != checkpoint_sha256:
        raise RuntimeError("C1 Source Gate A checkpoint hash drift")
    seeds = payload.get("seeds")
    if (
        not isinstance(seeds, list)
        or len(seeds) != EXPECTED_SEEDS
        or any(type(seed) is not int or seed < 0 for seed in seeds)
        or len(set(seeds)) != EXPECTED_SEEDS
    ):
        raise RuntimeError("C1 Source Gate A requires five unique integer seeds")
    return tuple(int(seed) for seed in seeds)


def _write_json(path: Path, payload: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--seed-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, default=Path(TLE_ROOT_DEFAULT))
    parser.add_argument("--prereg", type=Path, default=CANONICAL_PREREG)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    checkpoint = args.checkpoint.expanduser().resolve()
    seed_manifest = args.seed_manifest.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    prereg = args.prereg.expanduser().resolve()
    if not checkpoint.is_file() or not seed_manifest.is_file() or not prereg.is_file():
        raise FileNotFoundError("checkpoint, seed manifest, and prereg must exist")
    if (
        prereg != Path(CANONICAL_PREREG).resolve()
        or sha256_file(prereg) != CANONICAL_PREREG_BYTE_SHA256
    ):
        raise RuntimeError("C1 Source Gate A requires the canonical sealed preregistration")
    output_dir.mkdir(parents=True, exist_ok=False)
    checkpoint_sha = sha256_file(checkpoint)
    seeds = _read_seed_manifest(seed_manifest, checkpoint_sha256=checkpoint_sha)
    checkpoint_payload = read_checkpoint(checkpoint, map_location="cpu")
    archive = TleArchive(args.tle_root.expanduser().resolve())
    ephemeris = assert_ephemeris_matches_record(
        read_prereg(prereg), archive=archive
    )
    seed_rows: list[dict[str, Any]] = []
    paired_rows: list[dict[str, Any]] = []
    guard_failures: list[str] = []
    for seed in seeds:
        try:
            seed_row, rows = run_seed(
                archive=archive,
                checkpoint_path=checkpoint,
                checkpoint_payload=checkpoint_payload,
                checkpoint_sha256=checkpoint_sha,
                seed=seed,
            )
            seed_rows.append(seed_row)
            paired_rows.extend(rows)
        except Exception as exc:
            guard_failures.append(f"seed_{seed}:{type(exc).__name__}:{exc}")
    if len(seed_rows) != EXPECTED_SEEDS:
        # Preserve the formal denominator without fabricating zero-valued rows.
        decision = {
            "status": "FAIL",
            "decision": "DROP_C1_SOURCE_VERSION",
            "checks": {"all_five_seed_rows_present": False},
            "guard_failures": guard_failures,
        }
    else:
        decision = decide_gate(seed_rows, guard_failures=guard_failures)
    payload = {
        "schema": RESULT_SCHEMA,
        "status": decision["status"],
        "decision": decision["decision"],
        "source": "C1",
        "gate": "Source Gate A",
        "thresholds": {
            "expected_seeds": EXPECTED_SEEDS,
            "expected_steps_per_seed": EXPECTED_STEPS,
            "minimum_positive_seeds": MIN_POSITIVE_SEEDS,
            "maximum_served_fraction_decline": MAX_SERVICE_DECLINE,
        },
        "authority": {
            "checkpoint_path": str(checkpoint),
            "checkpoint_sha256": checkpoint_sha,
            "method_sha256": sha256_file(METHOD),
            "spec_sha256": sha256_file(SPEC),
            "runner_sha256": sha256_file(Path(__file__).resolve()),
            "seed_manifest_path": str(seed_manifest),
            "seed_manifest_sha256": sha256_file(seed_manifest),
            "prereg_path": str(prereg),
            "prereg_sha256": sha256_file(prereg),
            "tle_root_path": str(archive.root.resolve()),
            "tle_file_set_sha256": ephemeris["file_set_sha256"],
            "tle_file_count": int(ephemeris["archive"]["file_count"]),
        },
        "seed_rows": seed_rows,
        "paired_rows": paired_rows,
        "result": decision,
        "claim_ceiling": "SOURCE_QUALITY_ONLY_NOT_LEARNING_NOT_MAIN_ROUTING_NOT_EE_EFFICACY",
    }
    result_path = output_dir / "c1-source-gate-a-result.json"
    _write_json(result_path, payload)
    _write_json(
        output_dir / "receipt.json",
        {
            "schema": "smc-er-c1-source-gate-a-receipt-v1",
            "status": payload["status"],
            "decision": payload["decision"],
            "result_path": str(result_path),
            "result_sha256": sha256_file(result_path),
        },
    )
    print(result_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
