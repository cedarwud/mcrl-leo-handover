#!/usr/bin/env python3
"""Matched C3 lambda-confound gate on the repriced Q1/Q2 background.

The physical episode mechanics are reused from the already-audited V0.18
analytic diagnostic.  This wrapper changes only the authenticated Q1/Q2
checkpoint loader, fresh development worlds, keyed-field namespace, and the
predeclared V0.20 adjudication.  It performs no learner update and opens no
TEST split.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Mapping, Sequence

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.algorithms.ee_axis_action_shared_meanmax import (  # noqa: E402
    EEAxisMaskedMeanMaxConfig,
    EEAxisMaskedMeanMaxTrainer,
)
from mcrl.algorithms.ee_axis_v014_head import (  # noqa: E402
    EEAxisV014HeadConfig,
    EEAxisV014PairwiseLearner,
)
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402


V018_PATH = REPO / ".scratch" / "multi-catfish-v018-relational-zr" / "run_v018_analytic_diagnostic.py"
CONTRACT = HERE / "REPRICED-C3-LAMBDA-CONFOUND-GATE-CONTRACT-2026-09-04.md"
CONTRACT_SHA256 = "8587537e0c4790b383b62680748b21ecffb89550849814e50043d035cd918759"
FIT_ROOT = HERE / "repriced-q1-q2-fit"
FIT_MERGED = FIT_ROOT / "merged" / "result.json"
FIT_MERGED_SHA256 = "4657a1f758fa83c92deb631231431abf6bae586c050abfffc9f7e06963d9029a"

WORLDS = (2026121501, 2026121502, 2026121503, 2026121504)
LINEAGES = (2026092101, 2026092102, 2026092103)
Q2_INITIALIZATIONS = (2026108101, 2026108102, 2026108103)
Q2_INIT_BY_LINEAGE = dict(zip(LINEAGES, Q2_INITIALIZATIONS, strict=True))
CHECKPOINT_SHA256_BY_LINEAGE = {
    2026092101: "d40a0f3095f9bb9010d0146a88a77b3c8a824fb9bd3e5aee2205f3ae8be592dc",
    2026092102: "bb45bed30465f8be0ea9a1463c3b6e958d8f8b90cf11b4cd8e5d56a71f4b7057",
    2026092103: "32b5accfa1595ff19ddc11779402b5c86e115b883d04c6c5cbf90434ee32d44c",
}
ARMS = ("BASE", "EXACT_ZR", "NOMINAL_ZR")
FIELD_COMPONENT = "MCRL_V020_REPRICED_C3_GATE_V1"
SERVICE_MARGIN = 0.001
SCHEMA = "multi-catfish-mcrl-v020-repriced-c3-lambda-confound-gate-v1"
SHARD_SCHEMA = f"{SCHEMA}-shard"
RESULT_SCHEMA = f"{SCHEMA}-result"
CLAIM_CEILING = "TRAIN_MATCHED_GATE_NO_Q3_LEARNER_NO_TEST_NO_EFFICACY"


class V020C3GateError(RuntimeError):
    """The frozen C3 gate boundary or matched panel was violated."""


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise V020C3GateError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise V020C3GateError(f"expected regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_default(value: object) -> bool | int | float:
    """Normalize NumPy scalars emitted by the audited V0.18 evaluator."""

    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("non-finite NumPy scalar")
        return result
    raise TypeError(f"unsupported canonical JSON value: {type(value).__name__}")


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
        default=_canonical_default,
    ).encode("ascii")


def _canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _checkpoint_path(lineage: int) -> Path:
    q2_init = Q2_INIT_BY_LINEAGE[lineage]
    return (
        FIT_ROOT
        / f"lineage-{lineage}"
        / "checkpoints"
        / f"lineage-{lineage}-q2init-{q2_init}-rung-003000.pt"
    )


def _tuple_fields(payload: Mapping[str, object], names: Sequence[str]) -> dict[str, object]:
    result = dict(payload)
    for name in names:
        value = result.get(name)
        if isinstance(value, list):
            result[name] = tuple(value)
    return result


def load_repriced_heads(lineage: int) -> tuple[Any, dict[str, object], Any, dict[str, object]]:
    if lineage not in LINEAGES:
        raise V020C3GateError("lineage is outside the frozen panel")
    path = _checkpoint_path(lineage)
    actual = _sha256(path)
    if actual != CHECKPOINT_SHA256_BY_LINEAGE[lineage]:
        raise V020C3GateError(f"repriced checkpoint hash mismatch for {lineage}")
    payload = torch.load(path, map_location="cpu", weights_only=False)
    if (
        payload.get("schema") != "multi-catfish-mcrl-v020-repriced-q1-q2-source-fit-v1-checkpoint"
        or payload.get("lineage") != lineage
        or payload.get("q2_initialization") != Q2_INIT_BY_LINEAGE[lineage]
        or payload.get("q1_update_count") != 10
        or payload.get("q2_update_count") != 3000
        or payload.get("q1_head_index") != 0
    ):
        raise V020C3GateError("repriced checkpoint identity drifted")
    q1_payload = payload.get("q1")
    q2_payload = payload.get("q2")
    if not isinstance(q1_payload, Mapping) or not isinstance(q2_payload, Mapping):
        raise V020C3GateError("repriced checkpoint lacks Q1/Q2 payloads")
    q1_config_raw = q1_payload.get("config")
    q2_config_raw = q2_payload.get("config")
    if not isinstance(q1_config_raw, Mapping) or not isinstance(q2_config_raw, Mapping):
        raise V020C3GateError("repriced checkpoint config is malformed")
    q1_config = EEAxisMaskedMeanMaxConfig(
        **_tuple_fields(q1_config_raw, ("hidden_layers", "loss_weights"))
    )
    q1_trainer = EEAxisMaskedMeanMaxTrainer(q1_config, train_seed=lineage, device="cpu")
    if q1_trainer.load_checkpoint_state(q1_payload) != 10:
        raise V020C3GateError("repriced Q1 update count drifted")
    q1 = q1_trainer.q_nets[0]
    q1.eval()
    q1.requires_grad_(False)

    q2_config = EEAxisV014HeadConfig(
        **_tuple_fields(q2_config_raw, ("hidden_layers",))
    )
    q2_learner = EEAxisV014PairwiseLearner(
        q2_config, train_seed=Q2_INIT_BY_LINEAGE[lineage], device="cpu"
    )
    if q2_learner.load_checkpoint_state(q2_payload) != 3000:
        raise V020C3GateError("repriced Q2 update count drifted")
    q2 = q2_learner.q
    q2.eval()
    q2.requires_grad_(False)
    q1_receipt = {
        "checkpoint_path": str(path.resolve()),
        "checkpoint_sha256": actual,
        "combined_checkpoint": True,
        "head_index": 0,
        "update_count": 10,
        "train_seed": lineage,
        "config": asdict(q1_config),
    }
    q2_receipt = {
        "checkpoint_path": str(path.resolve()),
        "checkpoint_sha256": actual,
        "combined_checkpoint": True,
        "update_count": 3000,
        "train_seed": Q2_INIT_BY_LINEAGE[lineage],
        "config": asdict(q2_config),
    }
    return q1, q1_receipt, q2, q2_receipt


def _validate_global_inputs() -> dict[str, object]:
    if _sha256(CONTRACT) != CONTRACT_SHA256:
        raise V020C3GateError("C3 contract bytes changed")
    if _sha256(FIT_MERGED) != FIT_MERGED_SHA256:
        raise V020C3GateError("repriced Q1/Q2 merge bytes changed")
    merged = json.loads(FIT_MERGED.read_text(encoding="ascii"))
    if merged.get("status") != "GO_MATCHED_C3_GATE":
        raise V020C3GateError("repriced Q1/Q2 merge does not authorize C3")
    for lineage in LINEAGES:
        if _sha256(_checkpoint_path(lineage)) != CHECKPOINT_SHA256_BY_LINEAGE[lineage]:
            raise V020C3GateError("a declared Q1/Q2 checkpoint changed")
    return merged


def run_shard(
    *,
    world: int,
    lineage: int,
    arm: str,
    output: Path,
    tle_root: Path,
    prereg: Path,
) -> dict[str, object]:
    if world not in WORLDS or lineage not in LINEAGES or arm not in ARMS:
        raise V020C3GateError("shard identity is outside the frozen panel")
    if output.exists() or output.is_symlink():
        raise V020C3GateError(f"refusing to overwrite {output}")
    _validate_global_inputs()
    v018 = _load_module("v020_v018_physics", V018_PATH)
    q1, q1_receipt, q2, q2_receipt = load_repriced_heads(lineage)
    record = v018._V015._V013.read_prereg(prereg)
    field = KeyedFadingField.from_components(FIELD_COMPONENT, world)
    with tempfile.TemporaryDirectory(prefix="mcrl-v020-repriced-c3-tle-") as temporary:
        archive = v018._V015._V013.screen._frozen_archive(
            record, tle_root, Path(temporary) / "frozen-tle"
        )
        row = v018.evaluate_episode(
            q1=q1,
            q1_receipt=q1_receipt,
            q2=q2,
            q2_receipt=q2_receipt,
            archive=archive,
            world_seed=world,
            field=field,
            lineage=lineage,
            arm=arm,
        )
    row["split"] = "TRAIN_DEVELOPMENT"
    row["q2_initialization_seed"] = Q2_INIT_BY_LINEAGE[lineage]
    payload: dict[str, object] = {
        "schema": SHARD_SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "contract_sha256": CONTRACT_SHA256,
        "runner_file_sha256": _sha256(Path(__file__)),
        "fit_merged_file_sha256": FIT_MERGED_SHA256,
        "world": world,
        "lineage": lineage,
        "arm": arm,
        "checkpoint_sha256": CHECKPOINT_SHA256_BY_LINEAGE[lineage],
        "row": row,
        "row_sha256": _canonical_sha256(row),
        "test_split_opened": False,
        "learner_update": False,
        "episode_training": False,
    }
    output.mkdir(parents=True, exist_ok=False)
    (output / "shard.json").write_bytes(_canonical_bytes(payload))
    print(
        f"{world}/{arm}/{lineage}: EE={float(row['ratio_of_sums_ee_bits_per_j']):.9g} "
        f"elapsed={float(row['elapsed_s']):.1f}s",
        flush=True,
    )
    return payload


def _pool(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    bits = math.fsum(float(row["total_bits"]) for row in rows)
    energy = math.fsum(float(row["total_energy_j"]) for row in rows)
    served = sum(int(row["served_user_steps"]) for row in rows)
    opportunities = sum(int(row["served_opportunities"]) for row in rows)
    exposure = sum(int(row["action_exposure"]) for row in rows)
    if not rows or bits <= 0.0 or energy <= 0.0 or opportunities <= 0:
        raise V020C3GateError("cannot pool malformed C3 rows")
    return {
        "row_count": len(rows),
        "total_bits": bits,
        "total_energy_j": energy,
        "ratio_of_sums_ee_bits_per_j": bits / energy,
        "served_user_steps": served,
        "served_opportunities": opportunities,
        "served_fraction": served / opportunities,
        "action_exposure": exposure,
    }


def _relative(treatment: Mapping[str, object], base: Mapping[str, object]) -> float:
    return (
        float(treatment["ratio_of_sums_ee_bits_per_j"])
        / float(base["ratio_of_sums_ee_bits_per_j"])
        - 1.0
    )


def _contrast(
    indexed: Mapping[tuple[int, str, int], Mapping[str, object]], arm: str
) -> dict[str, object]:
    base = _pool([indexed[(world, "BASE", lineage)] for world in WORLDS for lineage in LINEAGES])
    treatment = _pool([indexed[(world, arm, lineage)] for world in WORLDS for lineage in LINEAGES])
    by_world: dict[str, float] = {}
    for world in WORLDS:
        b = _pool([indexed[(world, "BASE", lineage)] for lineage in LINEAGES])
        t = _pool([indexed[(world, arm, lineage)] for lineage in LINEAGES])
        by_world[str(world)] = _relative(t, b)
    by_lineage: dict[str, float] = {}
    for lineage in LINEAGES:
        b = _pool([indexed[(world, "BASE", lineage)] for world in WORLDS])
        t = _pool([indexed[(world, arm, lineage)] for world in WORLDS])
        by_lineage[str(lineage)] = _relative(t, b)
    relative = _relative(treatment, base)
    positive_worlds = sum(value > 0.0 for value in by_world.values())
    positive_lineages = sum(value > 0.0 for value in by_lineage.values())
    service_noninferior = (
        float(treatment["served_fraction"]) >= float(base["served_fraction"]) - SERVICE_MARGIN
    )
    passed = bool(
        relative > 0.0
        and positive_lineages == 3
        and positive_worlds >= 3
        and service_noninferior
        and int(treatment["action_exposure"]) > 0
    )
    return {
        "arm": arm,
        "base": base,
        "treatment": treatment,
        "relative_delta_ee": relative,
        "by_world_relative_delta_ee": by_world,
        "by_lineage_relative_delta_ee": by_lineage,
        "positive_world_count": positive_worlds,
        "positive_lineage_count": positive_lineages,
        "service_noninferior": service_noninferior,
        "passed": passed,
    }


def merge(*, shards: Sequence[Path], output: Path) -> dict[str, object]:
    if output.exists() or output.is_symlink():
        raise V020C3GateError(f"refusing to overwrite {output}")
    _validate_global_inputs()
    indexed: dict[tuple[int, str, int], Mapping[str, object]] = {}
    shard_receipts: list[dict[str, str]] = []
    for path in shards:
        payload = json.loads(path.read_text(encoding="ascii"))
        if payload.get("schema") != SHARD_SCHEMA or payload.get("contract_sha256") != CONTRACT_SHA256:
            raise V020C3GateError(f"stale shard: {path}")
        row = payload.get("row")
        if not isinstance(row, Mapping) or payload.get("row_sha256") != _canonical_sha256(row):
            raise V020C3GateError(f"invalid row receipt: {path}")
        key = (int(row["world_seed"]), str(row["arm"]), int(row["lineage"]))
        if key in indexed:
            raise V020C3GateError("duplicate shard identity")
        indexed[key] = row
        shard_receipts.append({"path": str(path), "sha256": _sha256(path)})
    expected = {(world, arm, lineage) for world in WORLDS for arm in ARMS for lineage in LINEAGES}
    if set(indexed) != expected:
        raise V020C3GateError("shards do not form the frozen rectangular panel")
    for world in WORLDS:
        rows = [indexed[(world, arm, lineage)] for arm in ARMS for lineage in LINEAGES]
        if len({str(row["initial_world_sha256"]) for row in rows}) != 1:
            raise V020C3GateError("matched arms do not share an initial world")
        if len({str(row["field_root_digest"]) for row in rows}) != 1:
            raise V020C3GateError("matched arms do not share a keyed field")
    mechanics = all(
        bool(row.get("mechanics_passed")) and bool(row.get("compatibility_proof_passed"))
        for row in indexed.values()
    )
    exact = _contrast(indexed, "EXACT_ZR")
    nominal = _contrast(indexed, "NOMINAL_ZR")
    if not mechanics or not exact["passed"]:
        decision = "REDESIGN_R3_TARGET"
    elif nominal["passed"]:
        decision = "GO_Q3_SOURCE_AND_LEARNER"
    else:
        decision = "REVISE_NOMINAL_Q3"
    result: dict[str, object] = {
        "schema": RESULT_SCHEMA,
        "decision": decision,
        "claim_ceiling": CLAIM_CEILING,
        "contract_sha256": CONTRACT_SHA256,
        "fit_merged_file_sha256": FIT_MERGED_SHA256,
        "worlds": list(WORLDS),
        "lineages": list(LINEAGES),
        "arms": list(ARMS),
        "field_component": FIELD_COMPONENT,
        "mechanics_passed": mechanics,
        "pooled_by_arm": {
            arm: _pool([indexed[(world, arm, lineage)] for world in WORLDS for lineage in LINEAGES])
            for arm in ARMS
        },
        "contrasts": {"EXACT_ZR": exact, "NOMINAL_ZR": nominal},
        "shard_receipts": sorted(shard_receipts, key=lambda row: row["path"]),
        "test_split_opened": False,
        "learner_update": False,
        "episode_training": False,
    }
    result["result_sha256"] = _canonical_sha256(result)
    output.mkdir(parents=True, exist_ok=False)
    result_path = output / "result.json"
    result_path.write_bytes(_canonical_bytes(result))
    (output / "result-seal.json").write_bytes(
        _canonical_bytes(
            {
                "schema": f"{RESULT_SCHEMA}-seal",
                "result_file_sha256": _sha256(result_path),
                "result_sha256": result["result_sha256"],
            }
        )
    )
    print(
        f"decision={decision} exact={float(exact['relative_delta_ee']):+.6%} "
        f"nominal={float(nominal['relative_delta_ee']):+.6%}",
        flush=True,
    )
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    shard = commands.add_parser("shard")
    shard.add_argument("--world", type=int, choices=WORLDS, required=True)
    shard.add_argument("--lineage", type=int, choices=LINEAGES, required=True)
    shard.add_argument("--arm", choices=ARMS, required=True)
    shard.add_argument("--output", type=Path, required=True)
    shard.add_argument("--tle-root", type=Path, default=Path("~/demo/tle_data/starlink/tle").expanduser())
    shard.add_argument("--prereg", type=Path, default=REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json")
    merge_parser = commands.add_parser("merge")
    merge_parser.add_argument("--shard", type=Path, action="append", required=True)
    merge_parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    torch.set_num_threads(1)
    if args.command == "shard":
        result = run_shard(
            world=args.world,
            lineage=args.lineage,
            arm=args.arm,
            output=args.output,
            tle_root=args.tle_root,
            prereg=args.prereg,
        )
    else:
        result = merge(shards=args.shard, output=args.output)
    if args.command == "merge":
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
