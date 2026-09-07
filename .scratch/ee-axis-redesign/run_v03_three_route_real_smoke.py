#!/usr/bin/env python3
"""Real C1/C2/C3 source -> three-Q update/checkpoint smoke for V0.3.

This is the last engineering bridge before a 10--20 source-episode pilot.  It
uses real TLE physics and the frozen Main checkpoint to construct one current
row for every route, persists D^o and D^t, runs one diagonal update cycle at
both requested learning rates, and proves each resulting checkpoint reloads
bit-identically.  It does not evaluate held-out EE and makes no efficacy
claim.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
C2_V03 = REPO / ".scratch" / "c2-v03"
for path in (HERE, C2_V03, REPO, REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import run_c2_v03_real_temporal_pair_smoke as c2_smoke  # noqa: E402
import run_v03_opening_real_smoke as opening_smoke  # noqa: E402
from mcrl.algorithms.ee_axis_pairwise import EEAxisPairwiseTrainer  # noqa: E402
from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.runtime.ee_axis_calibration import calibrate_ee_axis_pilot  # noqa: E402
from mcrl.runtime.ee_axis_opening_dataset import write_opening_dataset  # noqa: E402
from mcrl.runtime.ee_axis_pilot_runner import (  # noqa: E402
    EEAxisPilotRunSpec,
    load_pairwise_pilot_checkpoint,
    run_pairwise_pilot,
)
from mcrl.runtime.ee_axis_temporal_dataset import (  # noqa: E402
    EEAxisTemporalDataset,
    write_temporal_dataset,
)
from mcrl.runtime.ee_axis_training_schedule import (  # noqa: E402
    EEAxisThreeRouteBatches,
)
from mcrl.runtime.training_pipeline import (  # noqa: E402
    _code_sha256,
    _default_code_paths,
)


SCHEMA = "multi-catfish-mcrl-v03-three-route-real-smoke-v1"
CLAIM_CEILING = "REAL_THREE_ROUTE_PLUMBING_AND_CHECKPOINT_ONLY_NOT_EE_EFFICACY"
LEARNING_RATES = (0.001, 0.01)
TRAIN_SEEDS = (2026083111, 2026083112)


def _source_manifest_sha256() -> str:
    paths = list(_default_code_paths())
    paths.extend(sorted(C2_V03.glob("*.py")))
    paths.extend(
        [
            Path(opening_smoke.__file__),
            Path(c2_smoke.__file__),
            Path(__file__),
        ]
    )
    unique = sorted({path.resolve() for path in paths}, key=lambda path: str(path))
    missing = [path for path in unique if not path.is_file()]
    if missing:
        raise RuntimeError(f"three-route source closure has missing files: {missing}")
    return _code_sha256(unique)


def _checkpoint_reload_proof(
    *,
    trainer: EEAxisPairwiseTrainer,
    batches: EEAxisThreeRouteBatches,
    calibration: Any,
    learning_rate: float,
    train_seed: int,
    spec: EEAxisPilotRunSpec,
    checkpoint: Path,
) -> bool:
    restored = EEAxisPairwiseTrainer(
        calibration.pairwise_config(learning_rate=learning_rate),
        train_seed=train_seed,
    )
    completed = load_pairwise_pilot_checkpoint(
        checkpoint,
        trainer=restored,
        expected_spec=spec,
        expected_batch_digests={
            "C1": batches.c1.verify(),
            "C2": batches.c2.verify(),
            "C3": batches.c3.verify(),
        },
    )
    if completed != spec.episodes:
        return False
    states = np.concatenate(
        (
            batches.c1.pair_batch.states,
            batches.c2.pair_batch.states,
            batches.c3.pair_batch.states,
        ),
        axis=0,
    )
    return bool(
        np.array_equal(
            trainer.deployment_scores(states),
            restored.deployment_scores(states),
        )
    )


def run_smoke(*, output_dir: Path, tle_root: Path) -> dict[str, Any]:
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError(f"refusing to overwrite three-route smoke: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    source_manifest_sha256 = _source_manifest_sha256()

    opening_box = []
    opening_receipt = opening_smoke.run_smoke(
        tle_root=tle_root,
        dataset_out=opening_box,
        source_manifest_override=source_manifest_sha256,
    )
    if len(opening_box) != 1:
        raise RuntimeError("opening smoke did not return exactly one D^o dataset")
    opening_dataset = opening_box[0]

    temporal_box = []
    c2_receipt = c2_smoke.run_real_temporal_pair_smoke(
        tle_root=tle_root,
        users=100,
        max_anchor_steps=6,
        max_candidates=1,
        materialization_out=temporal_box,
        source_manifest_override=source_manifest_sha256,
    )
    if len(temporal_box) != 1:
        raise RuntimeError("C2 smoke did not return exactly one temporal pair")
    temporal_materialization = temporal_box[0]
    temporal_dataset = EEAxisTemporalDataset.from_pairs(
        (temporal_materialization.pair,)
    )

    if opening_dataset.checkpoint_sha256 != temporal_dataset.checkpoint_sha256:
        raise RuntimeError("opening and temporal sources use different Main checkpoints")
    if opening_dataset.source_manifest_sha256 != temporal_dataset.source_manifest_sha256:
        raise RuntimeError("opening and temporal sources use different source manifests")
    opening_lambda = float(opening_dataset.rows[0].raw_pair.lambda_bits_per_j)
    temporal_lambda = float(temporal_dataset.lambda_bits_per_j)
    if not math.isclose(opening_lambda, temporal_lambda, rel_tol=0.0, abs_tol=1e-9):
        raise RuntimeError("C1/C2/C3 source rows do not share one lambda0")

    calibration_payload = c2_receipt["calibration"]
    calibration = calibrate_ee_axis_pilot(
        calibration_seed=int(calibration_payload["calibration_seed"]),
        useful_bits=float(calibration_payload["useful_bits"]),
        energy_j=float(calibration_payload["energy_j"]),
        steps=int(calibration_payload["steps"]),
        users=100,
    )
    if not math.isclose(
        calibration.lambda_bits_per_j,
        temporal_lambda,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise RuntimeError("calibration lambda disagrees with persisted source rows")

    batches = EEAxisThreeRouteBatches(
        c1=opening_dataset.c1_batch(),
        c2=temporal_dataset.route_batch(),
        c3=opening_dataset.c3_batch(),
    )
    with tempfile.TemporaryDirectory(
        prefix=f".{output_dir.name}.", dir=output_dir.parent
    ) as temporary:
        staging = Path(temporary) / "publish"
        staging.mkdir()
        source_dir = staging / "source"
        write_opening_dataset(source_dir / "opening-do.json", opening_dataset)
        write_temporal_dataset(source_dir / "temporal-dt.json", temporal_dataset)
        arms: dict[str, Any] = {}
        for learning_rate, train_seed in zip(LEARNING_RATES, TRAIN_SEEDS, strict=True):
            label = f"lr-{learning_rate:g}"
            trainer = EEAxisPairwiseTrainer(
                calibration.pairwise_config(learning_rate=learning_rate),
                train_seed=train_seed,
            )
            spec = EEAxisPilotRunSpec(
                run_id=f"three-route-real-smoke-{label}",
                episodes=1,
                checkpoint_every_episodes=100,
            )
            pilot_dir = staging / label
            status = run_pairwise_pilot(
                trainer,
                batches,
                spec=spec,
                output_dir=pilot_dir,
            )
            checkpoint = (
                pilot_dir / "checkpoints" / "checkpoint-episode-000001.pt"
            )
            reload_equal = _checkpoint_reload_proof(
                trainer=trainer,
                batches=batches,
                calibration=calibration,
                learning_rate=learning_rate,
                train_seed=train_seed,
                spec=spec,
                checkpoint=checkpoint,
            )
            if not reload_equal:
                raise RuntimeError(f"{label} checkpoint did not reload bit-identically")
            arms[label] = {
                "learning_rate": learning_rate,
                "train_seed": train_seed,
                "episodes": 1,
                "updates": 3,
                "status": status["status"],
                "initial_fit": status["initial_fit"],
                "final_fit": status["final_fit"],
                "checkpoint": checkpoint.relative_to(staging).as_posix(),
                "checkpoint_reload_bitwise_equal": reload_equal,
            }

        payload = {
            "schema": SCHEMA,
            "status": "PASS",
            "claim_ceiling": CLAIM_CEILING,
            "held_out_ee_evaluated": False,
            "source_manifest_sha256": source_manifest_sha256,
            "checkpoint_sha256": opening_dataset.checkpoint_sha256,
            "lambda_bits_per_j": calibration.lambda_bits_per_j,
            "kappa_bits": calibration.kappa_bits,
            "beta": calibration.beta,
            "loss_weights": list(calibration.loss_weights),
            "state_dim": int(batches.c1.pair_batch.states.shape[1]),
            "source_rows": {
                "C1": int(batches.c1.pair_batch.states.shape[0]),
                "C2": int(batches.c2.pair_batch.states.shape[0]),
                "C3": int(batches.c3.pair_batch.states.shape[0]),
            },
            "targets_bits": {
                "C1": [float(value) for value in batches.c1.pair_batch.target_surplus_bits],
                "C2": [float(value) for value in batches.c2.pair_batch.target_surplus_bits],
                "C3": [float(value) for value in batches.c3.pair_batch.target_surplus_bits],
            },
            "opening_source_receipt": opening_receipt,
            "temporal_source_receipt": c2_receipt,
            "arms": arms,
            "elapsed_s": time.perf_counter() - started,
        }
        (staging / "receipt.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        os.rename(staging, output_dir)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO
        / "artifacts"
        / "multi-catfish-v03-three-route-real-smoke-20260831",
    )
    parser.add_argument(
        "--tle-root",
        type=Path,
        default=Path(TLE_ROOT_DEFAULT).expanduser(),
    )
    args = parser.parse_args()
    payload = run_smoke(output_dir=args.output_dir, tle_root=args.tle_root)
    print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
