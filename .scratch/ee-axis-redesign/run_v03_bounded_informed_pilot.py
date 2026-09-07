#!/usr/bin/env python3
"""Run the first multi-row 10--20 episode informed V0.3 pilot.

The source corpus is immutable.  Each pilot episode is one C1/C2/C3 update
cycle.  Two learning rates share the same initialization, and the trained
policies plus the common untrained initialization are evaluated on paired,
fresh keyed-fading seeds.  This remains a bounded directional pilot rather
than a Chapter-5 efficacy result.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile
import time
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
C2_V03 = REPO / ".scratch" / "c2-v03"
for path in (HERE, C2_V03, REPO, REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import run_c2_v03_deterministic_plumbing_probe as c2_probe  # noqa: E402
import scripts.run_head_pivotality_probe as loader  # noqa: E402
from mcrl.algorithms.ee_axis_pairwise import EEAxisPairwiseTrainer  # noqa: E402
from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_calibration import calibrate_ee_axis_pilot  # noqa: E402
from mcrl.runtime.ee_axis_evaluation import evaluate_ee_axis_episode  # noqa: E402
from mcrl.runtime.ee_axis_opening_dataset import read_opening_dataset  # noqa: E402
from mcrl.runtime.ee_axis_pilot_runner import (  # noqa: E402
    EEAxisPilotRunSpec,
    run_pairwise_pilot,
)
from mcrl.runtime.ee_axis_temporal_dataset import read_temporal_dataset  # noqa: E402
from mcrl.runtime.ee_axis_training_schedule import EEAxisThreeRouteBatches  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402


SCHEMA = "multi-catfish-mcrl-v03-bounded-informed-pilot-v1"
CLAIM_CEILING = "TEN_EP_MULTIROW_DIRECTIONAL_PILOT_NOT_CHAPTER5_EFFICACY"
LEARNING_RATES = (0.001, 0.01)
TRAIN_SEED = 2026083111
EVALUATION_SEEDS = (2026090101, 2026090102)
CALIBRATION_RECEIPT = (
    REPO
    / "artifacts"
    / "multi-catfish-v03-three-route-real-smoke-20260831"
    / "receipt.json"
)


class BoundedPilotError(RuntimeError):
    """The bounded multi-row informed pilot could not close."""


def _calibration(*, checkpoint_sha256: str, lambda_bits_per_j: float):
    try:
        payload = json.loads(CALIBRATION_RECEIPT.read_text(encoding="utf-8"))
        if payload["checkpoint_sha256"] != checkpoint_sha256:
            raise BoundedPilotError("calibration and corpus checkpoints disagree")
        raw = payload["temporal_source_receipt"]["calibration"]
        result = calibrate_ee_axis_pilot(
            calibration_seed=int(raw["calibration_seed"]),
            useful_bits=float(raw["useful_bits"]),
            energy_j=float(raw["energy_j"]),
            steps=int(raw["steps"]),
            users=100,
            beta=float(payload["beta"]),
            loss_weights=tuple(float(value) for value in payload["loss_weights"]),
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise BoundedPilotError("cannot load the frozen TRAIN-only calibration") from error
    if not math.isclose(
        result.lambda_bits_per_j,
        lambda_bits_per_j,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise BoundedPilotError("calibration lambda and corpus lambda disagree")
    return result


def _evaluate_policies(
    policies: dict[str, EEAxisPairwiseTrainer],
    *,
    checkpoint_sha256: str,
    tle_root: Path,
) -> dict[str, list[dict[str, Any]]]:
    record = read_prereg(REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json")
    receipts: dict[str, list[dict[str, Any]]] = {label: [] for label in policies}
    with tempfile.TemporaryDirectory(prefix="mcrl-v03-informed-pilot-eval-") as temporary:
        archive = c2_probe._frozen_archive(
            record, tle_root, Path(temporary) / "frozen-tle"
        )
        for seed in EVALUATION_SEEDS:
            for label, trainer in policies.items():
                wrapped = loader._make_environment(archive, users=100)
                wrapped.environment._fading_field = KeyedFadingField.from_components(
                    "multi-catfish-mcrl-v03-bounded-paired-evaluation-v1",
                    checkpoint_sha256,
                    seed,
                )
                env_rng, mobility_rng, _action_rng, _control_rng = loader._evaluation_rngs(
                    seed
                )
                receipt = evaluate_ee_axis_episode(
                    trainer,
                    wrapped,
                    env_rng=env_rng,
                    mobility_rng=mobility_rng,
                    evaluation_seed=seed,
                    policy_label=label,
                )
                receipts[label].append(
                    {
                        **receipt.payload(),
                        "receipt_sha256": receipt.verify(),
                        "ratio_of_sums_ee_bits_per_j": receipt.ratio_of_sums_ee_bits_per_j,
                        "served_fraction": receipt.served_fraction,
                        "outage_fraction": receipt.outage_fraction,
                    }
                )
    return receipts


def run_pilot(
    *,
    corpus_dir: Path,
    output_dir: Path,
    tle_root: Path,
    episodes: int,
) -> dict[str, Any]:
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError(f"refusing to overwrite bounded pilot: {output_dir}")
    if type(episodes) is not int or not 1 <= episodes <= 20:
        raise ValueError("episodes must be in [1,20]")
    started = time.perf_counter()
    opening = read_opening_dataset(corpus_dir / "opening-do.json")
    temporal = read_temporal_dataset(corpus_dir / "temporal-dt.json")
    if opening.checkpoint_sha256 != temporal.checkpoint_sha256:
        raise BoundedPilotError("opening and temporal corpus checkpoints disagree")
    if opening.source_manifest_sha256 != temporal.source_manifest_sha256:
        raise BoundedPilotError("opening and temporal corpus manifests disagree")
    if min(len(opening.c1_pairs), len(temporal.rows), len(opening.c3_pairs)) < 2:
        raise BoundedPilotError("bounded informed pilot requires at least two rows per route")
    opening_lambda = float(opening.rows[0].raw_pair.lambda_bits_per_j)
    if not math.isclose(opening_lambda, temporal.lambda_bits_per_j, rel_tol=0.0, abs_tol=1e-9):
        raise BoundedPilotError("opening and temporal corpus lambda values disagree")
    calibration = _calibration(
        checkpoint_sha256=opening.checkpoint_sha256,
        lambda_bits_per_j=opening_lambda,
    )
    batches = EEAxisThreeRouteBatches(
        c1=opening.c1_batch(),
        c2=temporal.route_batch(),
        c3=opening.c3_batch(),
    )

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{output_dir.name}.", dir=output_dir.parent) as temporary:
        staging = Path(temporary) / "publish"
        staging.mkdir()
        initial = EEAxisPairwiseTrainer(
            calibration.pairwise_config(learning_rate=LEARNING_RATES[0]),
            train_seed=TRAIN_SEED,
        )
        policies: dict[str, EEAxisPairwiseTrainer] = {"untrained-common-init": initial}
        arms: dict[str, Any] = {}
        for learning_rate in LEARNING_RATES:
            label = f"informed-lr-{learning_rate:g}"
            trainer = EEAxisPairwiseTrainer(
                calibration.pairwise_config(learning_rate=learning_rate),
                train_seed=TRAIN_SEED,
            )
            status = run_pairwise_pilot(
                trainer,
                batches,
                spec=EEAxisPilotRunSpec(
                    run_id=label,
                    episodes=episodes,
                    checkpoint_every_episodes=100,
                ),
                output_dir=staging / label,
            )
            policies[label] = trainer
            arms[label] = {
                "learning_rate": learning_rate,
                "episodes": episodes,
                "updates": episodes * 3,
                "initial_fit": status["initial_fit"],
                "final_fit": status["final_fit"],
                "elapsed_s": status["elapsed_s"],
            }
        evaluations = _evaluate_policies(
            policies,
            checkpoint_sha256=opening.checkpoint_sha256,
            tle_root=tle_root,
        )
        ee_means = {
            label: sum(row["ratio_of_sums_ee_bits_per_j"] for row in rows) / len(rows)
            for label, rows in evaluations.items()
        }
        initial_mean = ee_means["untrained-common-init"]
        payload = {
            "schema": SCHEMA,
            "status": "PASS",
            "claim_ceiling": CLAIM_CEILING,
            "source_manifest_sha256": opening.source_manifest_sha256,
            "checkpoint_sha256": opening.checkpoint_sha256,
            "corpus_rows": {
                "C1": len(opening.c1_pairs),
                "C2": len(temporal.rows),
                "C3": len(opening.c3_pairs),
            },
            "episodes": episodes,
            "train_seed": TRAIN_SEED,
            "evaluation_seeds": list(EVALUATION_SEEDS),
            "arms": arms,
            "heldout_evaluations": evaluations,
            "heldout_ee_mean_bits_per_j": ee_means,
            "heldout_delta_vs_untrained_bits_per_j": {
                label: mean - initial_mean
                for label, mean in ee_means.items()
                if label != "untrained-common-init"
            },
            "external_m0_baseline_evaluated": False,
            "elapsed_s": time.perf_counter() - started,
        }
        (staging / "receipt.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        shutil.move(str(staging), str(output_dir))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=REPO / "artifacts" / "multi-catfish-v03-phase1-informed-corpus-20260831",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO / "artifacts" / "multi-catfish-v03-bounded-informed-pilot-20260831",
    )
    parser.add_argument(
        "--tle-root",
        type=Path,
        default=Path(TLE_ROOT_DEFAULT).expanduser(),
    )
    parser.add_argument("--episodes", type=int, default=10)
    args = parser.parse_args()
    payload = run_pilot(
        corpus_dir=args.corpus_dir,
        output_dir=args.output_dir,
        tle_root=args.tle_root,
        episodes=args.episodes,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
