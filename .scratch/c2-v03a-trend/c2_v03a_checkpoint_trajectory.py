#!/usr/bin/env python3
"""Evaluate every 100EP checkpoint from one completed V0.3A matrix.

The final EE-vs-users sweep is the frozen learning-rate endpoint.  This
separate, optional trajectory is diagnostic: it evaluates the Main-only policy
at U=100 with the five frozen TEST seeds and never selects an intermediate
checkpoint.  Run it on the Ubuntu training server after matrix completion.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
LEGACY_DIR = REPO / ".scratch" / "smc-er-short-ep"
for path in (HERE, LEGACY_DIR, REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import c2_v03a_postrun_bundle as postrun  # noqa: E402
import c2_v03a_trend_arm as arm_runner  # noqa: E402
from c2_v03a_trend_authority import (  # noqa: E402
    ALLOWED_ARMS,
    EVALUATION_SEEDS,
    TRAINING_SEEDS,
)
from c2_v03a_trend_matrix import ARM_LABELS  # noqa: E402
from mcrl.artifacts import read_checkpoint  # noqa: E402
from sweep_evaluation import (  # noqa: E402
    canonical_ephemeris_authority,
    evaluate_checkpoint_point,
    ratio_of_sums,
    sha256_file,
)


SCHEMA = "multi-catfish-mcrl-c2-v03a-checkpoint-ee-trajectory-v1"
CHECKPOINT_EVERY_EPISODES = 100
USERS = 100
CLAIM_CEILING = (
    "ONE_TRAINING_SEED_EVERY_100EP_MAIN_ONLY_TEST_TRAJECTORY_"
    "NOT_CHECKPOINT_SELECTION_NOT_CHAPTER5_NOT_FORMAL_EFFICACY"
)
PLOT_STYLE = {
    "B000": ("#6E7278", "--", "o"),
    "F111": ("#1F6FB4", "-", "D"),
    "A011": ("#C6533D", "-.", "s"),
    "A101": ("#8A5FB5", ":", "^"),
    "A110": ("#2E8B4A", (0, (5, 2)), "v"),
}


class V03ATrajectoryError(RuntimeError):
    """Raised when checkpoint inventory or trajectory evidence drifts."""


def _read_object(path: Path, *, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise V03ATrajectoryError(f"{label} is unreadable: {path}") from error
    if not isinstance(value, Mapping):
        raise V03ATrajectoryError(f"{label} must be a JSON object")
    return value


def checkpoint_schedule(episodes: int) -> tuple[int, ...]:
    if type(episodes) is not int or episodes < CHECKPOINT_EVERY_EPISODES:
        raise V03ATrajectoryError("episodes cannot satisfy the 100EP cadence")
    if episodes % CHECKPOINT_EVERY_EPISODES != 0:
        raise V03ATrajectoryError("episodes must end on a 100EP checkpoint")
    return tuple(range(CHECKPOINT_EVERY_EPISODES, episodes + 1, CHECKPOINT_EVERY_EPISODES))


def _recorded_path(value: Any) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return Path(value).expanduser().resolve()
    except (OSError, RuntimeError):
        return None


def _validate_sealed_postrun_receipt(
    receipt_path: Path,
    *,
    matrix_root: Path,
    tle_root: Path,
) -> tuple[dict[str, Any], Mapping[str, Any], Mapping[str, Any]]:
    """Require the two-LR decision to be sealed before exposing TEST curves."""

    path = Path(receipt_path).expanduser().resolve()
    receipt = _read_object(path, label="sealed post-run receipt")
    if (
        receipt.get("schema") != postrun.SCHEMA
        or receipt.get("status") != "PASS"
        or receipt.get("formal_training_authorized") is not False
        or receipt.get("fresh_3000_launch_performed") is not False
        or receipt.get("decision")
        not in {"SELECT_AND_RUN_FRESH_3000", "STOP_BEFORE_3000"}
    ):
        raise V03ATrajectoryError("post-run LR decision is not sealed")
    matrices = receipt.get("matrices")
    if not isinstance(matrices, Mapping) or set(matrices) != {"0.001", "0.01"}:
        raise V03ATrajectoryError("post-run receipt lacks the exact two LR matrices")
    expected_rates = {"0.001": 0.001, "0.01": 0.01}
    live_validations: dict[str, Mapping[str, Any]] = {}
    for learning_rate, expected_rate in expected_rates.items():
        row = matrices.get(learning_rate)
        if not isinstance(row, Mapping):
            raise V03ATrajectoryError(f"sealed matrix {learning_rate} receipt is malformed")
        sealed_root = _recorded_path(row.get("matrix_root"))
        sealed_status = _recorded_path(row.get("matrix_status"))
        if (
            sealed_root is None
            or sealed_status != sealed_root / "matrix-status.json"
            or not sealed_status.is_file()
            or row.get("matrix_status_sha256") != sha256_file(sealed_status)
        ):
            raise V03ATrajectoryError(
                f"sealed matrix {learning_rate} status identity mismatch"
            )
        sealed_payload = _read_object(
            sealed_status, label=f"sealed matrix {learning_rate} status"
        )
        if sealed_payload.get("status") != "complete":
            raise V03ATrajectoryError(f"sealed matrix {learning_rate} is not complete")
        try:
            live_validation = postrun.validate_matrix(
                sealed_root,
                tle_root=Path(tle_root).expanduser().resolve(),
                expected_learning_rate=expected_rate,
            )
        except Exception as error:
            raise V03ATrajectoryError(
                f"sealed matrix {learning_rate} failed fresh post-run validation"
            ) from error
        if live_validation != row:
            raise V03ATrajectoryError(
                f"sealed matrix {learning_rate} receipt disagrees with fresh validation"
            )
        live_validations[learning_rate] = live_validation
    root = Path(matrix_root).expanduser().resolve()
    matches = [
        row
        for row in matrices.values()
        if isinstance(row, Mapping) and _recorded_path(row.get("matrix_root")) == root
    ]
    if len(matches) != 1:
        raise V03ATrajectoryError("matrix is not bound by the sealed LR decision")
    matrix_receipt = matches[0]
    status_path = root / "matrix-status.json"
    if (
        _recorded_path(matrix_receipt.get("matrix_status")) != status_path
        or not status_path.is_file()
        or matrix_receipt.get("matrix_status_sha256") != sha256_file(status_path)
    ):
        raise V03ATrajectoryError("sealed matrix-status identity mismatch")
    selection = receipt.get("lr_selection")
    if not isinstance(selection, Mapping):
        raise V03ATrajectoryError("sealed LR-selection receipt is missing")
    selection_path = _recorded_path(selection.get("path"))
    if (
        selection_path is None
        or not selection_path.is_file()
        or selection.get("sha256") != sha256_file(selection_path)
    ):
        raise V03ATrajectoryError("sealed LR-selection file identity mismatch")
    selection_payload = _read_object(selection_path, label="LR-selection receipt")
    try:
        recomputed_selection = postrun.lr_selector.select_learning_rate(
            Path(str(live_validations["0.001"]["sweep_summary"])),
            Path(str(live_validations["0.01"]["sweep_summary"])),
        )
    except Exception as error:
        raise V03ATrajectoryError(
            "LR selection cannot be recomputed from the two validated sweeps"
        ) from error
    if selection_payload != recomputed_selection:
        raise V03ATrajectoryError(
            "LR-selection receipt inputs or decision disagree with fresh validation"
        )
    if (
        selection_payload.get("status") != "PASS"
        or selection_payload.get("decision") != receipt.get("decision")
        or selection_payload.get("selected_learning_rate")
        != receipt.get("selected_learning_rate")
    ):
        raise V03ATrajectoryError("LR-selection decision disagrees with post-run receipt")
    mechanism_hashes = {
        row.get("mechanism_environment_source_sha256")
        for row in live_validations.values()
    }
    authority_hashes = {
        row.get("normalized_authority_excluding_learning_rate_sha256")
        for row in live_validations.values()
    }
    expected_consistency = {
        "status": "PASS",
        "environment_source_sha256": next(iter(mechanism_hashes)),
        "normalized_authority_excluding_learning_rate_sha256": next(
            iter(authority_hashes)
        ),
    }
    if (
        len(mechanism_hashes) != 1
        or None in mechanism_hashes
        or len(authority_hashes) != 1
        or None in authority_hashes
        or receipt.get("cross_lr_mechanism_consistency") != expected_consistency
    ):
        raise V03ATrajectoryError(
            "sealed cross-LR mechanism or authority consistency disagrees with validation"
        )
    return (
        {
            "path": str(path),
            "sha256": sha256_file(path),
            "decision": receipt["decision"],
            "selected_learning_rate": receipt.get("selected_learning_rate"),
        },
        matrix_receipt,
        live_validations[
            next(
                learning_rate
                for learning_rate, row in matrices.items()
                if isinstance(row, Mapping)
                and _recorded_path(row.get("matrix_root")) == root
            )
        ],
    )


def load_checkpoint_inventory(
    matrix_root: Path,
    *,
    tle_root: Path,
    postrun_receipt: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Validate the matrix, then materialize its exact 5x15 checkpoint grid."""

    root = Path(matrix_root).expanduser().resolve()
    sealed_postrun, sealed_matrix, matrix_verification = _validate_sealed_postrun_receipt(
        postrun_receipt,
        matrix_root=root,
        tle_root=tle_root,
    )
    matrix_path = root / "matrix-status.json"
    matrix = _read_object(matrix_path, label="matrix status")
    learning_rate = matrix.get("learning_rate")
    if (
        isinstance(learning_rate, bool)
        or not isinstance(learning_rate, (int, float))
        or not math.isfinite(float(learning_rate))
    ):
        raise V03ATrajectoryError("matrix learning rate is malformed")
    if matrix_verification.get("matrix_root") != str(root) or not math.isclose(
        float(matrix_verification.get("learning_rate", float("nan"))),
        float(learning_rate),
        rel_tol=0.0,
        abs_tol=1e-15,
    ):
        raise V03ATrajectoryError("selected matrix disagrees with sealed validation")

    authority_path = _recorded_path(matrix.get("authority"))
    if authority_path is None:
        raise V03ATrajectoryError("matrix authority path is malformed")
    try:
        validated = arm_runner.load_and_validate_authority(
            authority_path, tle_root=Path(tle_root).expanduser().resolve()
        )
    except Exception as error:
        raise V03ATrajectoryError("matrix authority no longer validates") from error
    episodes = validated.get("episodes")
    if episodes != postrun.MATRIX_EPISODES:
        raise V03ATrajectoryError("trajectory adapter requires the 1,500EP screen")
    if validated.get("checkpoint_every_episodes") != CHECKPOINT_EVERY_EPISODES:
        raise V03ATrajectoryError("authority checkpoint cadence drifted")
    if validated.get("seeds") != TRAINING_SEEDS:
        raise V03ATrajectoryError("authority training seeds drifted")
    if validated.get("evaluation_seeds") != EVALUATION_SEEDS:
        raise V03ATrajectoryError("authority evaluation seeds drifted")
    expected_schedule = checkpoint_schedule(episodes)

    sealed_arms_raw = sealed_matrix.get("arms")
    if not isinstance(sealed_arms_raw, list):
        raise V03ATrajectoryError("sealed matrix arm receipts are missing")
    sealed_arms = {
        str(row.get("arm")): row
        for row in sealed_arms_raw
        if isinstance(row, Mapping)
    }
    if set(sealed_arms) != set(ALLOWED_ARMS):
        raise V03ATrajectoryError("sealed matrix arm receipt grid is incomplete")

    inventory: list[dict[str, Any]] = []
    for arm in ALLOWED_ARMS:
        status_path = root / "arms" / arm / "status.json"
        status = _read_object(status_path, label=f"{arm} status")
        if (
            status.get("status") != "complete"
            or status.get("arm") != arm
            or status.get("formal_training_authorized") is not False
        ):
            raise V03ATrajectoryError(f"{arm} status is not a completed trend arm")
        result = status.get("result")
        if not isinstance(result, Mapping):
            raise V03ATrajectoryError(f"{arm} result is missing")
        if (
            status.get("run_mode") != "fresh_intermediate_trend"
            or result.get("start_episode", 0) != 0
            or (arm != "B000" and result.get("artifact_scope") != "complete_run")
        ):
            raise V03ATrajectoryError(
                f"{arm} trajectory requires a fresh complete 100..1500EP history"
            )
        trainer_config = status.get("trainer_config")
        if not isinstance(trainer_config, Mapping):
            raise V03ATrajectoryError(f"{arm} trainer config is missing")
        rows = result.get("periodic_checkpoints")
        if not isinstance(rows, list) or len(rows) != len(expected_schedule):
            raise V03ATrajectoryError(f"{arm} periodic checkpoint count mismatch")
        observed_schedule: list[int] = []
        for row in rows:
            if not isinstance(row, Mapping):
                raise V03ATrajectoryError(f"{arm} checkpoint row is malformed")
            completed = row.get("episodes_completed")
            if type(completed) is not int:
                raise V03ATrajectoryError(f"{arm} checkpoint episode is malformed")
            observed_schedule.append(completed)
            expected_path = (
                root
                / "arms"
                / arm
                / "checkpoints"
                / f"ep-{completed:06d}-main.pt"
            ).resolve()
            if _recorded_path(row.get("path")) != expected_path or not expected_path.is_file():
                raise V03ATrajectoryError(
                    f"{arm} checkpoint {completed} path/file mismatch"
                )
            digest = sha256_file(expected_path)
            if row.get("sha256") != digest:
                raise V03ATrajectoryError(f"{arm} checkpoint {completed} hash mismatch")
            if (
                row.get("episode_index") != completed - 1
                or row.get("checkpoint_kind") != "periodic-main-policy-trend"
                or row.get("load_round_trip") != "PASS"
            ):
                raise V03ATrajectoryError(
                    f"{arm} checkpoint {completed} receipt drifted"
                )
            payload = read_checkpoint(expected_path, map_location="cpu")
            try:
                identity = postrun._validate_checkpoint_payload(
                    payload,
                    validated=validated,
                    trainer_config=trainer_config,
                    episode_index=completed - 1,
                    checkpoint_kind="periodic-main-policy-trend",
                    label=f"{arm} checkpoint {completed}",
                )
            except postrun.V03APostrunError as error:
                raise V03ATrajectoryError(str(error)) from error
            inventory.append(
                {
                    "arm": arm,
                    "arm_label": ARM_LABELS[arm],
                    "episodes_completed": completed,
                    "path": expected_path,
                    "sha256": digest,
                    "payload": payload,
                    "identity": identity,
                }
            )
        if tuple(observed_schedule) != expected_schedule:
            raise V03ATrajectoryError(f"{arm} checkpoint sequence is incomplete")

    expected_count = len(ALLOWED_ARMS) * len(expected_schedule)
    if len(inventory) != expected_count:
        raise V03ATrajectoryError("checkpoint inventory grid is incomplete")
    for arm in ALLOWED_ARMS:
        sealed_rows = sealed_arms[arm].get("periodic_checkpoints")
        observed_rows = [item for item in inventory if item["arm"] == arm]
        if not isinstance(sealed_rows, list) or len(sealed_rows) != len(observed_rows):
            raise V03ATrajectoryError(f"{arm} sealed checkpoint inventory is incomplete")
        for sealed, observed in zip(sealed_rows, observed_rows, strict=True):
            if not isinstance(sealed, Mapping) or (
                sealed.get("episodes_completed") != observed["episodes_completed"]
                or sealed.get("sha256") != observed["sha256"]
                or sealed.get("online_policy_sha256")
                != observed["identity"]["online_policy_sha256"]
            ):
                raise V03ATrajectoryError(
                    f"{arm} checkpoint inventory disagrees with sealed post-run receipt"
                )
    authority_receipt = {
        "episodes": episodes,
        "learning_rate": float(validated["learning_rate"]),
        "training_seed": TRAINING_SEEDS["training"],
        "evaluation_seeds": list(EVALUATION_SEEDS),
        "users": USERS,
        "canonical_prereg": str(validated["canonical_prereg"]),
        "matrix_verification": matrix_verification,
        "matrix_status": str(matrix_path),
        "matrix_status_sha256": sha256_file(matrix_path),
        "sealed_postrun": sealed_postrun,
    }
    return authority_receipt, inventory


def aggregate_trajectory(raw_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int], list[Mapping[str, Any]]] = defaultdict(list)
    for row in raw_rows:
        grouped[(str(row["arm"]), int(row["episodes_completed"]))].append(row)

    summary: list[dict[str, Any]] = []
    for arm in ALLOWED_ARMS:
        for completed in checkpoint_schedule(postrun.MATRIX_EPISODES):
            group = grouped.get((arm, completed), [])
            seeds = [int(row["evaluation_seed"]) for row in group]
            if seeds != EVALUATION_SEEDS:
                raise V03ATrajectoryError(
                    f"{arm} checkpoint {completed} evaluation seed grid drifted"
                )
            bits = math.fsum(float(row["useful_bits"]) for row in group)
            energy = math.fsum(float(row["system_energy_j"]) for row in group)
            served = sum(int(row["served_user_intervals"]) for row in group)
            total = sum(int(row["total_user_intervals"]) for row in group)
            summary.append(
                {
                    "arm": arm,
                    "arm_label": ARM_LABELS[arm],
                    "episodes_completed": completed,
                    "users": USERS,
                    "evaluation_seeds": seeds,
                    "useful_bits": bits,
                    "system_energy_j": energy,
                    "system_ee_bits_per_j": ratio_of_sums(bits, energy),
                    "served_fraction": served / total if total else 0.0,
                    "zero_power_intervals": sum(
                        int(row["zero_power_intervals"]) for row in group
                    ),
                    "zero_service_intervals": sum(
                        int(row["zero_service_intervals"]) for row in group
                    ),
                }
            )
    return summary


def _write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    materialized = list(rows)
    if not materialized:
        raise V03ATrajectoryError("refusing to write an empty trajectory CSV")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(materialized[0]))
        writer.writeheader()
        writer.writerows(materialized)


def _plot(path: Path, summary: Sequence[Mapping[str, Any]]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(12.0, 5.2))
    for arm in ALLOWED_ARMS:
        rows = [row for row in summary if row["arm"] == arm]
        xs = [int(row["episodes_completed"]) for row in rows]
        ys = [float(row["system_ee_bits_per_j"]) / 1e6 for row in rows]
        colour, linestyle, marker = PLOT_STYLE[arm]
        ax.plot(
            xs,
            ys,
            color=colour,
            linestyle=linestyle,
            marker=marker,
            markersize=5,
            linewidth=2.2,
            label=ARM_LABELS[arm],
        )
    ax.set_xlabel("Training episodes", fontsize=20)
    ax.set_ylabel("Held-out EE at 100 users (Mbits/J)", fontsize=20)
    ax.tick_params(axis="both", labelsize=16)
    ax.grid(True, linestyle=":", linewidth=0.9, alpha=0.45)
    ax.legend(loc="best", frameon=False, fontsize=13)
    fig.text(
        0.995,
        0.008,
        "one-seed 100EP trajectory - diagnostic, not checkpoint selection",
        ha="right",
        va="bottom",
        fontsize=12,
        style="italic",
    )
    fig.tight_layout(pad=0.7, rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=200, facecolor="white")
    plt.close(fig)


def evaluate_trajectory(
    *,
    matrix_root: Path,
    output_dir: Path,
    tle_root: Path,
    postrun_receipt: Path,
) -> dict[str, Any]:
    authority, inventory = load_checkpoint_inventory(
        matrix_root,
        tle_root=tle_root,
        postrun_receipt=postrun_receipt,
    )
    prereg_raw = Path(authority["canonical_prereg"]).expanduser()
    prereg = prereg_raw.resolve() if prereg_raw.is_absolute() else (REPO / prereg_raw).resolve()
    archive, ephemeris = canonical_ephemeris_authority(prereg, tle_root)

    raw_rows: list[dict[str, Any]] = []
    for item in inventory:
        for seed in EVALUATION_SEEDS:
            totals = evaluate_checkpoint_point(
                archive=archive,
                checkpoint_path=item["path"],
                checkpoint_payload=item["payload"],
                arm=item["arm"],
                checkpoint_sha256=item["sha256"],
                users=USERS,
                evaluation_seed=seed,
            )
            row = asdict(totals)
            row["arm_label"] = item["arm_label"]
            row["episodes_completed"] = item["episodes_completed"]
            raw_rows.append(row)

    summary = aggregate_trajectory(raw_rows)
    if len(raw_rows) != len(inventory) * len(EVALUATION_SEEDS):
        raise V03ATrajectoryError("trajectory raw row count mismatch")
    if len(summary) != len(inventory):
        raise V03ATrajectoryError("trajectory summary row count mismatch")
    if any(int(row["zero_power_intervals"]) != 0 for row in raw_rows):
        raise V03ATrajectoryError(
            "trajectory contains zero-power intervals and is not interpretable"
        )

    out = Path(output_dir).expanduser().resolve()
    if out.exists():
        raise FileExistsError(f"refusing to overwrite trajectory output: {out}")
    out.mkdir(parents=True, exist_ok=False)
    raw_path = out / "checkpoint-trajectory-raw.json"
    summary_path = out / "checkpoint-trajectory-summary.json"
    raw_path.write_text(
        json.dumps(raw_rows, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    payload = {
        "schema": SCHEMA,
        "status": "complete",
        "claim_ceiling": CLAIM_CEILING,
        "checkpoint_selection_performed": False,
        "episodes": authority["episodes"],
        "checkpoint_every_episodes": CHECKPOINT_EVERY_EPISODES,
        "learning_rate": authority["learning_rate"],
        "training_seed": authority["training_seed"],
        "users": USERS,
        "evaluation_seeds": list(EVALUATION_SEEDS),
        "evaluation_partition": "test",
        "evaluation_policy": "Main-only masked-greedy MODQN",
        "ee_aggregation": (
            "ratio of pooled useful bits to pooled system energy within each "
            "arm/checkpoint cell"
        ),
        "authority": ephemeris,
        "matrix_status": authority["matrix_status"],
        "matrix_status_sha256": authority["matrix_status_sha256"],
        "sealed_postrun": authority["sealed_postrun"],
        "checkpoint_inventory": [
            {
                "arm": item["arm"],
                "arm_label": item["arm_label"],
                "episodes_completed": item["episodes_completed"],
                "path": str(item["path"]),
                "sha256": item["sha256"],
                **item["identity"],
            }
            for item in inventory
        ],
        "summary": summary,
    }
    summary_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    raw_csv_path = out / "checkpoint-trajectory-raw.csv"
    summary_csv_path = out / "checkpoint-trajectory-summary.csv"
    _write_csv(raw_csv_path, raw_rows)
    _write_csv(
        summary_csv_path,
        [
            {key: value for key, value in row.items() if key != "evaluation_seeds"}
            for row in summary
        ],
    )
    plot_path = out / "ee-vs-training-episodes.png"
    _plot(plot_path, summary)
    plot_status = {
        "status": "complete",
        "path": str(plot_path),
        "sha256": sha256_file(plot_path),
    }
    (out / "plot-status.json").write_text(
        json.dumps(plot_status, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    receipt = {
        "schema": "multi-catfish-mcrl-c2-v03a-checkpoint-ee-trajectory-receipt-v1",
        "status": "PASS",
        "claim_ceiling": CLAIM_CEILING,
        "checkpoint_selection_performed": False,
        "sealed_postrun": authority["sealed_postrun"],
        "matrix_status": authority["matrix_status"],
        "matrix_status_sha256": authority["matrix_status_sha256"],
        "checkpoint_inventory_count": len(inventory),
        "artifacts": {
            "raw_json": {"path": str(raw_path), "sha256": sha256_file(raw_path)},
            "summary_json": {
                "path": str(summary_path),
                "sha256": sha256_file(summary_path),
            },
            "raw_csv": {
                "path": str(raw_csv_path),
                "sha256": sha256_file(raw_csv_path),
            },
            "summary_csv": {
                "path": str(summary_csv_path),
                "sha256": sha256_file(summary_csv_path),
            },
            "plot": plot_status,
        },
    }
    receipt_path = out / "trajectory-receipt.json"
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return receipt


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    parser.add_argument("--postrun-receipt", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    try:
        evaluate_trajectory(
            matrix_root=args.matrix_root,
            output_dir=args.output_dir,
            tle_root=args.tle_root,
            postrun_receipt=args.postrun_receipt,
        )
    except V03ATrajectoryError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(Path(args.output_dir).expanduser().resolve() / "trajectory-receipt.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
