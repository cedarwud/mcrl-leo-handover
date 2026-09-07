#!/usr/bin/env python3
"""Build the immutable, disjoint-seed C1 EXP and neutral corpora."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "src"))

from run_c1_source_gate import _canonical_json, sha256_file  # noqa: E402
from smc_er_roles import (  # noqa: E402
    local_snr_greedy_actions,
    masked_uniform_actions,
    physical_key_for_action,
)
from sweep_evaluation import (  # noqa: E402
    _trainer_config,
    evaluation_rngs,
    make_environment,
    ratio_of_sums,
)
from mcrl.algorithms.modqn import MODQNTrainer  # noqa: E402
from mcrl.artifacts import read_checkpoint  # noqa: E402
from mcrl.env.action_contract import NO_OP_ACTION  # noqa: E402
from mcrl.env.constants import DECISION_STEP_S, TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.env.tle import TleArchive  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    CANONICAL_PREREG,
    CANONICAL_PREREG_BYTE_SHA256,
    assert_ephemeris_matches_record,
)


SPEC = HERE / "C1-EXP-CORPUS-BUILD-SPEC-2026-08-27.md"
SOURCE_GATE_SPEC = HERE / "C1-SOURCE-GATE-A-SPEC-2026-08-27.md"
SEED_SCHEMA = "smc-er-c1-exp-build-seeds-v1"
MANIFEST_SCHEMA = "smc-er-c1-exp-corpus-manifest-v2"
PATH_BINDING = "repository_relative_posix_v1"
TLE_ROOT_BINDING = "runtime_argument"
CONTROL_NAMESPACE = "SMC-ER-C1-EXP-BUILD-CONTROL-v1"
EXPECTED_SEEDS = 5
EXPECTED_STEPS = 10
EXPECTED_USERS = 100
EXPECTED_BUNDLES_PER_BRANCH = EXPECTED_SEEDS * EXPECTED_STEPS
HIGH_COUNT = 17
MID_COUNT = 17
LOW_COUNT = 16


def _repository_relative_posix(
    path: Path, *, label: str, repo: Path = REPO
) -> str:
    """Serialize a path only when its resolved target is inside ``repo``.

    The manifest is copied between checkouts, so it must never persist a
    source-host absolute path.  Resolving before checking containment also
    rejects a symlink that escapes the repository.
    """

    root = Path(repo).expanduser().resolve()
    target = Path(path).expanduser().resolve()
    try:
        relative = target.relative_to(root)
    except ValueError as exc:
        raise RuntimeError(
            f"{label} must be serialized as a repository-relative POSIX path"
        ) from exc
    if not relative.parts:
        raise RuntimeError(f"{label} cannot name the repository root")
    rendered = relative.as_posix()
    if rendered.startswith("/") or "\\" in rendered:
        raise RuntimeError(
            f"{label} must be serialized as a repository-relative POSIX path"
        )
    return rendered


def _manifest_authority(
    *,
    checkpoint: Path,
    checkpoint_sha256: str,
    source_gate: Path,
    source_gate_sha256: str,
    seed_manifest: Path,
    seed_manifest_sha256: str,
    prereg: Path,
    prereg_sha256: str,
    ephemeris: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the portable authority block without changing scientific data."""

    return {
        "checkpoint_path": _repository_relative_posix(
            checkpoint, label="checkpoint"
        ),
        "checkpoint_sha256": checkpoint_sha256,
        "source_gate_result_path": _repository_relative_posix(
            source_gate, label="source gate result"
        ),
        "source_gate_result_sha256": source_gate_sha256,
        "source_gate_spec_sha256": sha256_file(SOURCE_GATE_SPEC),
        "build_spec_sha256": sha256_file(SPEC),
        "builder_sha256": sha256_file(Path(__file__).resolve()),
        "seed_manifest_path": _repository_relative_posix(
            seed_manifest, label="seed manifest"
        ),
        "seed_manifest_sha256": seed_manifest_sha256,
        "prereg_path": _repository_relative_posix(prereg, label="prereg"),
        "prereg_sha256": prereg_sha256,
        "tle_file_set_sha256": ephemeris["file_set_sha256"],
        "tle_file_count": int(ephemeris["archive"]["file_count"]),
    }


def _validate_repository_paths(
    *,
    checkpoint: Path,
    source_gate: Path,
    seed_manifest: Path,
    prereg: Path,
    output_dir: Path,
) -> dict[str, Path]:
    """Reject host-local inputs before any corpus work starts."""

    bound_files = {
        "checkpoint": checkpoint,
        "source_gate": source_gate,
        "seed_manifest": seed_manifest,
        "prereg": prereg,
    }
    resolved: dict[str, Path] = {}
    for name, raw_path in bound_files.items():
        path = Path(raw_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        _repository_relative_posix(path, label=name.replace("_", " "))
        resolved[name] = path

    output = Path(output_dir).expanduser().resolve()
    _repository_relative_posix(output, label="output directory")
    resolved["output_dir"] = output
    return resolved


def control_rng(seed: int) -> np.random.Generator:
    encoded = _canonical_json([CONTROL_NAMESPACE, int(seed)])
    integer = int.from_bytes(hashlib.sha256(encoded).digest()[:16], "big")
    return np.random.Generator(np.random.PCG64(np.random.SeedSequence(integer)))


def assign_strata(rows: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    """Freeze 17 high, 17 mid, 16 low by deterministic executed EE rank."""

    if len(rows) != EXPECTED_BUNDLES_PER_BRANCH:
        raise ValueError("each C1 EXP branch must contain exactly 50 bundles")
    ids = [str(row["bundle_id"]) for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("C1 EXP bundle IDs must be unique")
    ordered = sorted(
        rows,
        key=lambda row: (
            -float(row["system_ee_bits_per_j"]),
            int(row["seed"]),
            int(row["step"]),
            str(row["bundle_id"]),
        ),
    )
    result: dict[str, str] = {}
    for rank, row in enumerate(ordered):
        result[str(row["bundle_id"])] = (
            "high" if rank < HIGH_COUNT else "mid" if rank < HIGH_COUNT + MID_COUNT else "low"
        )
    return result


def _mask_block(masks: Sequence[Any]) -> np.ndarray:
    return np.stack([np.asarray(row.mask, dtype=bool) for row in masks])


def _physical_rows(actions: np.ndarray, observation: Any) -> tuple[np.ndarray, np.ndarray]:
    norad = np.full(actions.size, -1, dtype=np.int64)
    cell = np.full(actions.size, -1, dtype=np.int64)
    for uid, action in enumerate(np.asarray(actions, dtype=np.int64)):
        key = physical_key_for_action(
            observation.candidates.slot_tables[uid], int(action)
        )
        if key is not None:
            norad[uid], cell[uid] = int(key[0]), int(key[1])
    return norad, cell


def run_branch(
    *,
    branch: str,
    archive: TleArchive,
    checkpoint_path: Path,
    checkpoint_payload: Any,
    seed: int,
) -> list[dict[str, Any]]:
    if branch not in {"local", "control"}:
        raise ValueError("unknown C1 EXP branch")
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
    source_rng = control_rng(seed)
    states, masks, observation = environment.reset(env_rng, mobility_rng)
    rows: list[dict[str, Any]] = []
    for _ in range(EXPECTED_STEPS):
        step = int(observation.step_index)
        encoded = trainer.encode_states(states)
        current_masks = _mask_block(masks)
        if branch == "local":
            actions, probabilities = local_snr_greedy_actions(states, masks)
            behavior = "local_snr_greedy"
        else:
            actions, probabilities = masked_uniform_actions(masks, source_rng)
            behavior = "masked_uniform"
        norad, cell = _physical_rows(actions, observation)
        result = environment.step(actions, env_rng)
        outcome = environment.last_outcome
        next_encoded = trainer.encode_states(result.user_states)
        throughput = float(outcome.energy.system_throughput_bps)
        power = float(outcome.energy.system_consumed_power_w)
        rewards = np.asarray(outcome.reward_matrix, dtype=np.float64)
        if (
            not math.isfinite(throughput)
            or throughput < 0.0
            or not math.isfinite(power)
            or power < 0.0
            or rewards.shape != (EXPECTED_USERS, 3)
            or not np.all(np.isfinite(rewards))
        ):
            raise RuntimeError("invalid C1 EXP executed outcome")
        if power == 0.0 and throughput != 0.0:
            raise RuntimeError("positive C1 EXP throughput at zero power")
        bundle_id = f"C1-EXP-{branch}-seed{int(seed)}-step{step:02d}"
        rows.append(
            {
                "bundle_id": bundle_id,
                "branch": branch,
                "behavior": behavior,
                "seed": int(seed),
                "step": step,
                "states": np.asarray(encoded, dtype=np.float32),
                "actions": np.asarray(actions, dtype=np.int64),
                "rewards": rewards,
                "next_states": np.asarray(next_encoded, dtype=np.float32),
                "masks": current_masks,
                "next_masks": _mask_block(result.action_masks),
                "done": bool(result.done),
                "probabilities": np.asarray(probabilities, dtype=np.float64),
                "physical_norad_ids": norad,
                "physical_cell_ids": cell,
                "system_throughput_bps": throughput,
                "system_power_w": power,
                "system_ee_bits_per_j": ratio_of_sums(
                    throughput * DECISION_STEP_S, power * DECISION_STEP_S
                ),
                "served": int(outcome.resolution.served_count),
            }
        )
        states, masks, observation = (
            result.user_states,
            result.action_masks,
            outcome.observation,
        )
        if result.done:
            break
    if len(rows) != EXPECTED_STEPS:
        raise RuntimeError("C1 EXP branch ended before ten executed transitions")
    return rows


def _pack_branch(rows: Sequence[Mapping[str, Any]]) -> tuple[dict[str, np.ndarray], list[dict[str, Any]]]:
    strata = assign_strata(rows)
    ordered = sorted(rows, key=lambda row: (int(row["seed"]), int(row["step"])))
    arrays = {
        "bundle_ids": np.asarray([str(row["bundle_id"]) for row in ordered], dtype="U80"),
        "seeds": np.asarray([int(row["seed"]) for row in ordered], dtype=np.int64),
        "steps": np.asarray([int(row["step"]) for row in ordered], dtype=np.int64),
        "strata": np.asarray([strata[str(row["bundle_id"])] for row in ordered], dtype="U8"),
        "states": np.stack([row["states"] for row in ordered]),
        "actions": np.stack([row["actions"] for row in ordered]),
        "rewards": np.stack([row["rewards"] for row in ordered]),
        "next_states": np.stack([row["next_states"] for row in ordered]),
        "masks": np.stack([row["masks"] for row in ordered]),
        "next_masks": np.stack([row["next_masks"] for row in ordered]),
        "dones": np.asarray([bool(row["done"]) for row in ordered], dtype=bool),
        "probabilities": np.stack([row["probabilities"] for row in ordered]),
        "physical_norad_ids": np.stack([row["physical_norad_ids"] for row in ordered]),
        "physical_cell_ids": np.stack([row["physical_cell_ids"] for row in ordered]),
        "system_throughput_bps": np.asarray(
            [float(row["system_throughput_bps"]) for row in ordered], dtype=np.float64
        ),
        "system_power_w": np.asarray(
            [float(row["system_power_w"]) for row in ordered], dtype=np.float64
        ),
        "system_ee_bits_per_j": np.asarray(
            [float(row["system_ee_bits_per_j"]) for row in ordered], dtype=np.float64
        ),
        "served": np.asarray([int(row["served"]) for row in ordered], dtype=np.int64),
    }
    index = [
        {
            "bundle_id": str(row["bundle_id"]),
            "seed": int(row["seed"]),
            "step": int(row["step"]),
            "stratum": strata[str(row["bundle_id"])],
            "system_ee_bits_per_j": float(row["system_ee_bits_per_j"]),
        }
        for row in ordered
    ]
    return arrays, index


def _read_seeds(
    path: Path,
    *,
    checkpoint_sha256: str,
    source_gate_result_sha256: str,
) -> tuple[int, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping) or payload.get("schema") != SEED_SCHEMA:
        raise RuntimeError("C1 EXP seed manifest schema mismatch")
    bindings = {
        "spec_sha256": sha256_file(SPEC),
        "checkpoint_sha256": checkpoint_sha256,
        "source_gate_result_sha256": source_gate_result_sha256,
    }
    for field, expected in bindings.items():
        if payload.get(field) != expected:
            raise RuntimeError(f"C1 EXP seed manifest {field} drift")
    seeds = payload.get("seeds")
    if (
        not isinstance(seeds, list)
        or len(seeds) != EXPECTED_SEEDS
        or any(type(seed) is not int or seed < 0 for seed in seeds)
        or len(set(seeds)) != EXPECTED_SEEDS
    ):
        raise RuntimeError("C1 EXP build requires five unique integer seeds")
    return tuple(int(seed) for seed in seeds)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--source-gate-result", type=Path, required=True)
    parser.add_argument("--seed-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, default=Path(TLE_ROOT_DEFAULT))
    parser.add_argument("--prereg", type=Path, default=CANONICAL_PREREG)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    repository_paths = _validate_repository_paths(
        checkpoint=args.checkpoint,
        source_gate=args.source_gate_result,
        seed_manifest=args.seed_manifest,
        prereg=args.prereg,
        output_dir=args.output_dir,
    )
    checkpoint = repository_paths["checkpoint"]
    source_gate = repository_paths["source_gate"]
    seed_manifest = repository_paths["seed_manifest"]
    output_dir = repository_paths["output_dir"]
    # ``prereg`` is already validated and canonicalized by the helper above;
    # keep the named variable for the sealed-preregistration check below.
    prereg = repository_paths["prereg"]
    if (
        prereg != Path(CANONICAL_PREREG).resolve()
        or sha256_file(prereg) != CANONICAL_PREREG_BYTE_SHA256
    ):
        raise RuntimeError("C1 EXP corpus requires the canonical sealed preregistration")
    gate_payload = json.loads(source_gate.read_text(encoding="utf-8"))
    if gate_payload.get("status") != "PASS" or gate_payload.get("decision") != "PASS_TO_C1_CONSUMER_GATE":
        raise RuntimeError("C1 EXP corpus requires a frozen Source Gate A PASS")
    checkpoint_sha = sha256_file(checkpoint)
    gate_sha = sha256_file(source_gate)
    seeds = _read_seeds(
        seed_manifest,
        checkpoint_sha256=checkpoint_sha,
        source_gate_result_sha256=gate_sha,
    )
    output_dir.mkdir(parents=True, exist_ok=False)
    archive = TleArchive(args.tle_root.expanduser().resolve())
    ephemeris = assert_ephemeris_matches_record(
        read_prereg(prereg), archive=archive
    )
    source_authority = gate_payload.get("authority")
    if not isinstance(source_authority, Mapping) or (
        source_authority.get("prereg_sha256") != sha256_file(prereg)
        or source_authority.get("tle_file_set_sha256")
        != ephemeris["file_set_sha256"]
        or source_authority.get("tle_file_count")
        != int(ephemeris["archive"]["file_count"])
    ):
        raise RuntimeError("C1 EXP corpus TLE authority differs from Source Gate A")
    checkpoint_payload = read_checkpoint(checkpoint, map_location="cpu")
    by_branch: dict[str, list[dict[str, Any]]] = {"local": [], "control": []}
    for seed in seeds:
        for branch in ("local", "control"):
            by_branch[branch].extend(
                run_branch(
                    branch=branch,
                    archive=archive,
                    checkpoint_path=checkpoint,
                    checkpoint_payload=checkpoint_payload,
                    seed=seed,
                )
            )
    packed: dict[str, np.ndarray] = {}
    indices: dict[str, list[dict[str, Any]]] = {}
    for branch, rows in by_branch.items():
        arrays, index = _pack_branch(rows)
        indices[branch] = index
        packed.update({f"{branch}_{key}": value for key, value in arrays.items()})
    npz_path = output_dir / "c1-exp-corpus.npz"
    np.savez_compressed(npz_path, **packed)
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "status": "complete",
        "claim_ceiling": "C1_SPECIALIST_PREFILL_ONLY_NEVER_MAIN",
        "path_binding": PATH_BINDING,
        "tle_root_binding": TLE_ROOT_BINDING,
        "authority": _manifest_authority(
            checkpoint=checkpoint,
            checkpoint_sha256=checkpoint_sha,
            source_gate=source_gate,
            source_gate_sha256=gate_sha,
            seed_manifest=seed_manifest,
            seed_manifest_sha256=sha256_file(seed_manifest),
            prereg=prereg,
            prereg_sha256=sha256_file(prereg),
            ephemeris=ephemeris,
        ),
        "corpus_path": _repository_relative_posix(
            npz_path, label="corpus"
        ),
        "corpus_sha256": sha256_file(npz_path),
        "shape": {
            "users": EXPECTED_USERS,
            "state_dim": int(packed["local_states"].shape[-1]),
            "action_dim": int(packed["local_masks"].shape[-1]),
            "bundles_per_branch": EXPECTED_BUNDLES_PER_BRANCH,
            "high": HIGH_COUNT,
            "mid": MID_COUNT,
            "low": LOW_COUNT,
        },
        "branches": indices,
    }
    manifest_path = output_dir / "c1-exp-corpus-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
