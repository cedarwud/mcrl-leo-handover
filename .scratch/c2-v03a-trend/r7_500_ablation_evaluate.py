#!/usr/bin/env python3
"""Evaluate routed R7 ablations and emit frozen load-wise Catfish contrasts."""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
LEGACY_DIR = REPO / ".scratch" / "smc-er-short-ep"
for path in (HERE, LEGACY_DIR, REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import r7_500_authority as authority  # noqa: E402
import r7_500_evaluate as prefix_evaluator  # noqa: E402
import r7_500_lr_router as router  # noqa: E402
import r7_500_output as output_tools  # noqa: E402
import r7_500_prefix_bridge as bridge  # noqa: E402
import r7_500_server_preflight as preflight  # noqa: E402
import sweep_evaluation as sweep  # noqa: E402


SCHEMA = "multi-catfish-mcrl-c2-v03a-r7-500-ablation-evaluation-v3"
RAW_SCHEMA = "multi-catfish-mcrl-c2-v03a-r7-500-ablation-evaluation-raw-v1"
CONTRAST_SCHEMA = "multi-catfish-mcrl-c2-v03a-r7-500-catfish-contrasts-v1"
RECEIPT_SCHEMA = "multi-catfish-mcrl-c2-v03a-r7-500-ablation-evaluation-receipt-v3"
LABELS = {
    "B000": "Baseline MODQN",
    "F111": "Full Multi-Catfish MCRL",
    "A101": "Full minus C2 (A101)",
    "A011": "Full minus C1 (A011)",
    "A110": "Full minus C3 (A110)",
}
ROLE_WITHOUT = {"C1": "A011", "C2": "A101", "C3": "A110"}


class R7500AblationEvaluationError(RuntimeError):
    """Raised when routed ablation evidence is incomplete or unbound."""


def _read_object(path: Path, *, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise R7500AblationEvaluationError(f"{label} is unreadable: {path}") from error
    if not isinstance(value, Mapping):
        raise R7500AblationEvaluationError(f"{label} must be a JSON object")
    return value


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def _contrast_receipt(
    summary: Sequence[Mapping[str, Any]], *, available_arms: Sequence[str], failure_only: bool
) -> dict[str, Any]:
    indexed = {(str(row["arm"]), int(row["users"])): row for row in summary}
    roles: dict[str, Any] = {}
    for role, without_arm in ROLE_WITHOUT.items():
        if without_arm not in available_arms:
            continue
        rows = []
        for users in authority.EVALUATION_USERS:
            full = indexed[(LABELS["F111"], users)]
            without = indexed[(LABELS[without_arm], users)]
            full_ee = float(full["mean_ee_bits_per_j"])
            without_ee = float(without["mean_ee_bits_per_j"])
            contrast = 100.0 * (full_ee / without_ee - 1.0)
            rows.append(
                {
                    "users": users,
                    "full_ee_bits_per_j": full_ee,
                    "without_role_ee_bits_per_j": without_ee,
                    "d_role_percent": contrast,
                    "positive": contrast > 0.0,
                }
            )
        mean_contrast = sum(row["d_role_percent"] for row in rows) / len(rows)
        positive_loads = sum(bool(row["positive"]) for row in rows)
        supported = mean_contrast > 0.0 and positive_loads >= 4
        classification = (
            "FAILURE_ANALYSIS_ONLY_C2_DIAGNOSTIC"
            if failure_only and role == "C2"
            else "PRELIMINARILY_EE_POSITIVE"
            if supported
            else "NOT_PRELIMINARILY_EE_POSITIVE"
        )
        roles[role] = {
            "without_arm": without_arm,
            "formula": "100*(EE_F111-EE_Full-minus-Cj)/EE_Full-minus-Cj",
            "loadwise": rows,
            "equal_weight_mean_percent": mean_contrast,
            "positive_load_count": positive_loads,
            "guard_status": "PASS",
            "classification": classification,
            "preliminarily_ee_positive": supported and not failure_only,
        }
    return {
        "classification_rule": (
            "MEAN_STRICTLY_POSITIVE_AND_AT_LEAST_FOUR_OF_FIVE_LOADS_POSITIVE_"
            "AND_ALL_GUARDS_PASS"
        ),
        "failure_analysis_only": failure_only,
        "roles": roles,
    }


def evaluate_ablations(
    *,
    authority_path: Path,
    bridge_receipt_path: Path,
    reconciliation_receipt_path: Path,
    selection_receipt_path: Path,
    output_dir: Path,
    tle_root: Path,
    repo: Path = REPO,
) -> dict[str, Any]:
    repo = Path(repo).expanduser().resolve()
    tle_root = Path(tle_root).expanduser().resolve()
    validated, authority_sha = bridge.load_and_validate_authority(
        authority_path, repo=repo, tle_root=tle_root
    )
    selection_path = Path(selection_receipt_path).expanduser().resolve()
    selection = router.validate_selection_receipt(
        selection_path,
        authority_path=authority_path,
        tle_root=tle_root,
        repo=repo,
    )
    decision = selection["decision"]
    selected_lr = float(decision["selected_learning_rate"])
    lr_key = prefix_evaluator._lr_key(selected_lr)
    allowed = list(decision["allowed_ablation_arms"])
    selected_arms = [*authority.PREFIX_ARMS, *allowed]
    (
        _,
        _,
        _bridge_receipt,
        _reconciliation_receipt,
        checkpoints,
    ) = prefix_evaluator._load_inputs(
        authority_path=authority_path,
        bridge_receipt_path=bridge_receipt_path,
        reconciliation_receipt_path=reconciliation_receipt_path,
        learning_rate=selected_lr,
        tle_root=tle_root,
        repo=repo,
        selected_arms=selected_arms,
    )
    bridge_receipt_path = Path(bridge_receipt_path).expanduser().resolve()
    reconciliation_receipt_path = Path(reconciliation_receipt_path).expanduser().resolve()
    bridge_receipt_sha = authority.sha256_file(bridge_receipt_path)
    reconciliation_receipt_sha = authority.sha256_file(reconciliation_receipt_path)
    root = (repo / validated["ablation_output_root"]).resolve()
    selection_sha = authority.sha256_file(selection_path)
    base = validated["validated_base_authorities"][lr_key]
    expected_arms = selected_arms
    if [row["arm"] for row in checkpoints] != expected_arms:
        raise R7500AblationEvaluationError("ablation checkpoint order drifted")
    evaluation_gate = preflight.assert_evaluation_ready(
        authority_path=authority_path,
        tle_root=tle_root,
        repo=repo,
    )
    output = Path(output_dir).expanduser().resolve()
    expected_output = root / "evaluation" / "selected-lr-ablation"
    if output != expected_output:
        raise R7500AblationEvaluationError("ablation evaluation output path drifted")
    try:
        output, staging = output_tools.reserve_output_directory(
            output,
            marker={
                "schema": "r7-output-reservation-v1",
                "artifact": "ablation-evaluation",
                "required_labels": authority.REQUIRED_LABELS,
            },
        )
    except FileExistsError as error:
        raise FileExistsError(
            f"refusing to overwrite R7 ablation evaluation: {output}"
        ) from error
    lock_path = (repo / validated["resource_policy"]["global_evaluation_lock"]).resolve()
    lock_marker = {
        "artifact": "selected-lr-ablation-evaluation",
        "authority_sha256": authority_sha,
        "claim_ceiling": authority.CLAIM_CEILING,
        "required_labels": authority.REQUIRED_LABELS,
    }
    lock_acquired = False
    try:
        output_tools.acquire_evaluation_lock(
            lock_path,
            marker=lock_marker,
        )
        lock_acquired = True
        prereg = (repo / str(base["canonical_prereg"])).resolve()
        archive, ephemeris = sweep.canonical_ephemeris_authority(prereg, tle_root)
        raw = [
            sweep.evaluate_checkpoint_point(
                archive=archive,
                checkpoint_path=item["path"],
                checkpoint_payload=item["payload"],
                arm=item["label"],
                checkpoint_sha256=item["sha256"],
                users=users,
                evaluation_seed=seed,
            )
            for item in checkpoints
            for users in authority.EVALUATION_USERS
            for seed in authority.EVALUATION_SEEDS
        ]
        raw_rows = [asdict(row) for row in raw]
        try:
            prefix_evaluator.validate_evaluation_rows(
                raw_rows, expected_count=len(expected_arms) * 25
            )
        except Exception as error:
            raise R7500AblationEvaluationError(
                "ablation evaluation safeguards failed"
            ) from error
        summary = sweep.aggregate_rows(raw)
        if len(raw_rows) != len(expected_arms) * 25 or len(summary) != len(expected_arms) * 5:
            raise R7500AblationEvaluationError("ablation evaluation grid is incomplete")
        failure_only = (
            decision["decision"]
            == "REVEAL_A101_SOURCE_EP500_FAILURE_ANALYSIS_ONLY"
        )
        failure_label = "FAILURE-ANALYSIS-ONLY C2 DIAGNOSTIC"
        presentation_labels = [
            *authority.REQUIRED_LABELS,
            *([failure_label] if failure_only else []),
        ]
        contrast_core = _contrast_receipt(
            summary, available_arms=allowed, failure_only=failure_only
        )
        contrasts = {
            "schema": CONTRAST_SCHEMA,
            "status": "complete",
            "claim_ceiling": authority.CLAIM_CEILING,
            "required_labels": authority.REQUIRED_LABELS,
            "presentation_labels": presentation_labels,
            "authority_sha256": authority_sha,
            "selection_receipt_sha256": selection_sha,
            "learning_rate": selected_lr,
            **contrast_core,
        }
        payload = {
            "schema": SCHEMA,
            "status": "complete",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "claim_ceiling": authority.CLAIM_CEILING,
            "required_labels": authority.REQUIRED_LABELS,
            "presentation_labels": presentation_labels,
            "authority_sha256": authority_sha,
            "selection_receipt": {
                "path": str(selection_path),
                "sha256": selection_sha,
            },
            "bridge_receipt": {
                "path": str(bridge_receipt_path),
                "sha256": bridge_receipt_sha,
            },
            "reconciliation_receipt": {
                "path": str(reconciliation_receipt_path),
                "sha256": reconciliation_receipt_sha,
            },
            "source_checkpoint_reuse_only": True,
            "new_r7_training_authorized": False,
            "learning_rate": selected_lr,
            "endpoint_episodes": 500,
            "evaluation_policy": "MAIN_ONLY_MASKED_GREEDY",
            "evaluation_partition": "TEST",
            "ee_aggregation": "RATIO_OF_POOLED_USEFUL_BITS_TO_POOLED_SYSTEM_ENERGY",
            "users": authority.EVALUATION_USERS,
            "evaluation_seeds": authority.EVALUATION_SEEDS,
            "ephemeris_authority": ephemeris,
            "evaluation_gate": evaluation_gate,
            "checkpoints": [
                {
                    "arm": row["arm"],
                    "label": row["label"],
                    "path": str(row["path"]),
                    "sha256": row["sha256"],
                    "online_policy_sha256": row["online_policy_sha256"],
                }
                for row in checkpoints
            ],
            "summary": summary,
            "contrasts": contrasts,
        }
        raw_payload = {
            "schema": RAW_SCHEMA,
            "status": "complete",
            "created_utc": payload["created_utc"],
            "claim_ceiling": authority.CLAIM_CEILING,
            "required_labels": authority.REQUIRED_LABELS,
            "presentation_labels": presentation_labels,
            "authority_sha256": authority_sha,
            "selection_receipt": payload["selection_receipt"],
            "bridge_receipt": payload["bridge_receipt"],
            "reconciliation_receipt": payload["reconciliation_receipt"],
            "source_checkpoint_reuse_only": True,
            "new_r7_training_authorized": False,
            "learning_rate": selected_lr,
            "endpoint_episodes": 500,
            "evaluation_policy": payload["evaluation_policy"],
            "evaluation_partition": payload["evaluation_partition"],
            "ee_aggregation": payload["ee_aggregation"],
            "users": authority.EVALUATION_USERS,
            "evaluation_seeds": authority.EVALUATION_SEEDS,
            "ephemeris_authority": ephemeris,
            "evaluation_gate": evaluation_gate,
            "checkpoints": payload["checkpoints"],
            "rows": raw_rows,
        }
        raw_path = staging / "sweep-raw.json"
        summary_path = staging / "sweep-summary.json"
        contrast_path = staging / "catfish-contrasts.json"
        plot_path = staging / "ee-vs-users-r7-500-ablation.svg"
        _write_json(raw_path, raw_payload)
        _write_json(summary_path, payload)
        _write_json(contrast_path, contrasts)
        serialized_raw = _read_object(raw_path, label="serialized ablation raw")
        serialized_summary = _read_object(
            summary_path, label="serialized ablation summary"
        )
        serialized_contrasts = _read_object(
            contrast_path, label="serialized ablation contrasts"
        )
        try:
            recomputed_summary = prefix_evaluator.recompute_serialized_evaluation_rows(
                serialized_raw.get("rows"),
                ordered_labels=[LABELS[arm] for arm in expected_arms],
                checkpoint_bindings=payload["checkpoints"],
            )
        except Exception as error:
            raise R7500AblationEvaluationError(
                "serialized ablation raw grid failed independent reconstruction"
            ) from error
        recomputed_contrasts = {
            "schema": CONTRAST_SCHEMA,
            "status": "complete",
            "claim_ceiling": authority.CLAIM_CEILING,
            "required_labels": authority.REQUIRED_LABELS,
            "presentation_labels": presentation_labels,
            "authority_sha256": authority_sha,
            "selection_receipt_sha256": selection_sha,
            "learning_rate": selected_lr,
            **_contrast_receipt(
                recomputed_summary,
                available_arms=allowed,
                failure_only=failure_only,
            ),
        }
        if (
            serialized_raw != raw_payload
            or serialized_summary != payload
            or serialized_summary.get("summary") != recomputed_summary
            or serialized_contrasts != recomputed_contrasts
        ):
            raise R7500AblationEvaluationError(
                "ablation summary or contrasts do not reproduce from serialized raw"
            )
        prefix_evaluator.write_svg_plot(
            plot_path,
            summary,
            learning_rate=selected_lr,
            title=(
                "500-EP Failure-Analysis-Only C2 Diagnostic"
                if failure_only
                else "500-EP Preliminary Multi-Catfish Ablation"
            ),
            labels=[LABELS[arm] for arm in expected_arms],
            footer_labels=presentation_labels,
        )
        receipt = {
            "schema": RECEIPT_SCHEMA,
            "status": "PASS",
            "claim_ceiling": authority.CLAIM_CEILING,
            "required_labels": authority.REQUIRED_LABELS,
            "presentation_labels": presentation_labels,
            "authority_sha256": authority_sha,
            "selection_receipt_sha256": selection_sha,
            "learning_rate": selected_lr,
            "failure_analysis_only": failure_only,
            "independent_raw_recomputation": "PASS",
            "artifacts": {
                "raw": {"path": str(output / raw_path.name), "sha256": authority.sha256_file(raw_path)},
                "summary": {"path": str(output / summary_path.name), "sha256": authority.sha256_file(summary_path)},
                "contrasts": {"path": str(output / contrast_path.name), "sha256": authority.sha256_file(contrast_path)},
                "plot": {"path": str(output / plot_path.name), "sha256": authority.sha256_file(plot_path)},
            },
        }
        _write_json(staging / "evaluation-receipt.json", receipt)
        revalidated_selection = router.validate_selection_receipt(
            selection_path,
            authority_path=authority_path,
            tle_root=tle_root,
            repo=repo,
        )
        if (
            authority.sha256_file(selection_path) != selection_sha
            or revalidated_selection != selection
            or revalidated_selection.get("decision") != decision
            or
            authority.sha256_file(Path(authority_path).expanduser().resolve())
            != authority_sha
            or authority.sha256_file(bridge_receipt_path) != bridge_receipt_sha
            or authority.sha256_file(reconciliation_receipt_path)
            != reconciliation_receipt_sha
            or any(
                not row["path"].is_file()
                or authority.sha256_file(row["path"]) != row["sha256"]
                for row in checkpoints
            )
        ):
            raise R7500AblationEvaluationError(
                "R7 ablation lineage changed before publication"
            )
        output_tools.publish_receipt_last(
            staging=staging,
            output=output,
            receipt_name="evaluation-receipt.json",
        )
        output_tools.release_evaluation_lock(
            lock_path,
            expected_marker=lock_marker,
        )
        lock_acquired = False
        output_tools.finalize_publication(
            output=output,
            receipt_name="evaluation-receipt.json",
        )
        return receipt
    except BaseException as error:
        output_tools.abort_reserved_output(staging=staging, output=output)
        if lock_acquired:
            try:
                output_tools.release_evaluation_lock(
                    lock_path,
                    expected_marker=lock_marker,
                )
            except Exception as lock_error:
                error.add_note(
                    "R7 owned ablation lock cleanup failed; lock was preserved: "
                    f"{lock_error}"
                )
        raise


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--bridge-receipt", type=Path, required=True)
    parser.add_argument("--reconciliation-receipt", type=Path, required=True)
    parser.add_argument("--selection-receipt", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    evaluate_ablations(
        authority_path=args.authority,
        bridge_receipt_path=args.bridge_receipt,
        reconciliation_receipt_path=args.reconciliation_receipt,
        selection_receipt_path=args.selection_receipt,
        output_dir=args.output_dir,
        tle_root=args.tle_root,
    )
    print(Path(args.output_dir).expanduser().resolve() / "evaluation-receipt.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
