#!/usr/bin/env python3
"""Reconcile R7 EP500 snapshots against completed R2 arm receipts."""

from __future__ import annotations

import argparse
import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for path in (HERE, REPO / "src"):
    if str(path) not in __import__("sys").path:
        __import__("sys").path.insert(0, str(path))

import r7_500_authority as authority  # noqa: E402
import r7_500_checkpoint as checkpoint_tools  # noqa: E402
import r7_500_output as output_tools  # noqa: E402
import r7_500_prefix_bridge as bridge  # noqa: E402
from mcrl.artifacts import read_checkpoint  # noqa: E402


SCHEMA = "multi-catfish-mcrl-c2-v03a-r7-500-prefix-reconciliation-v4"
SOURCE_STATUS_SCHEMA = bridge.SOURCE_STATUS_SCHEMA


class R7500ReconciliationError(RuntimeError):
    """Raised when a prefix is not backed by a completed source-arm receipt."""


def _read_object(path: Path, *, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise R7500ReconciliationError(f"{label} is unreadable: {path}") from error
    if not isinstance(value, Mapping):
        raise R7500ReconciliationError(f"{label} must be a JSON object")
    return value


def _write_json_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n"
    )
    # Keep pre-publication bytes outside the already accepted bridge directory.
    # A SIGKILL may leave this private sibling behind, but it must not mutate the
    # contents of a directory whose receipt has already been published.
    temporary_parent = path.parent.parent
    temporary_parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{path.parent.name}-{path.name}.",
        suffix=".tmp",
        dir=temporary_parent,
    )
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _lr_key(value: Any) -> str:
    for expected in authority.ALLOWED_LEARNING_RATES:
        if (
            not isinstance(value, bool)
            and isinstance(value, (int, float))
            and math.isclose(float(value), expected, rel_tol=0.0, abs_tol=1e-15)
        ):
            return str(expected)
    raise R7500ReconciliationError("prefix learning rate is invalid")


def _periodic_row(status: Mapping[str, Any]) -> Mapping[str, Any]:
    result = status.get("result")
    rows = result.get("periodic_checkpoints") if isinstance(result, Mapping) else None
    matches = [
        row
        for row in rows
        if isinstance(row, Mapping) and row.get("episodes_completed") == 500
    ] if isinstance(rows, list) else []
    if len(matches) != 1:
        raise R7500ReconciliationError("source status lacks one exact EP500 receipt")
    return matches[0]


def reconcile_prefixes(
    *, authority_path: Path, bridge_receipt_path: Path, tle_root: Path, repo: Path = REPO
) -> dict[str, Any]:
    repo = Path(repo).expanduser().resolve()
    tle_root = Path(tle_root).expanduser().resolve()
    validated, authority_sha = bridge.load_and_validate_authority(
        authority_path, repo=repo, tle_root=tle_root
    )
    bridge_path = Path(bridge_receipt_path).expanduser().resolve()
    expected_bridge = (repo / validated["bridge_output"] / "prefix-bridge-receipt.json").resolve()
    if bridge_path != expected_bridge:
        raise R7500ReconciliationError("prefix bridge receipt path drifted")
    if (bridge_path.parent / output_tools.INCOMPLETE_MARKER).exists():
        raise R7500ReconciliationError("prefix bridge publication is incomplete")
    receipt = _read_object(bridge_path, label="prefix bridge receipt")
    bridge_authority = receipt.get("authority")
    if (
        receipt.get("schema") != bridge.SCHEMA
        or receipt.get("status") != "PASS"
        or receipt.get("claim_ceiling") != authority.CLAIM_CEILING
        or receipt.get("required_labels") != authority.REQUIRED_LABELS
        or receipt.get("endpoint_episodes") != 500
        or receipt.get("prefix_arms") != list(authority.PREFIX_ARMS)
        or receipt.get("bridged_arms") != list(authority.BRIDGED_ARMS)
        or receipt.get("learning_rates") != list(authority.ALLOWED_LEARNING_RATES)
        or receipt.get("outcome_bearing_source_status_parsed_by_whitelist_extractor")
        is not True
        or receipt.get("outcome_metric_fields_copied") is not False
        or receipt.get("outcome_metric_fields_emitted") is not False
        or receipt.get("outcome_metric_fields_used_for_admission") is not False
        or receipt.get("outcome_metric_fields_admitted") is not False
        or receipt.get("checkpoint_selection_performed") is not False
        or receipt.get("evaluation_authorized") is not False
        or receipt.get("routing_authorized") is not False
        or receipt.get("reconciliation_required") is not True
        or not isinstance(bridge_authority, Mapping)
        or bridge_authority.get("sha256") != authority_sha
        or bridge_authority.get("pin_map_sha256") != validated["pin_map_sha256"]
    ):
        raise R7500ReconciliationError("prefix bridge receipt is not reconcilable")
    bridge_root = bridge_path.parent
    authority_snapshot = (bridge_root / str(bridge_authority.get("snapshot"))).resolve()
    if (
        not authority_snapshot.is_relative_to(bridge_root)
        or not authority_snapshot.is_file()
        or authority.sha256_file(authority_snapshot) != authority_sha
    ):
        raise R7500ReconciliationError("prefix bridge authority snapshot drifted")
    rows = receipt.get("prefixes")
    if not isinstance(rows, list) or len(rows) != 10:
        raise R7500ReconciliationError("prefix bridge must contain exactly ten prefixes")
    reconciled: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise R7500ReconciliationError("prefix row is malformed")
        arm = row.get("arm")
        if arm not in authority.BRIDGED_ARMS:
            raise R7500ReconciliationError("prefix arm identity drifted")
        lr_key = _lr_key(row.get("learning_rate"))
        base = validated["validated_base_authorities"][lr_key]
        matrix_root = (repo / validated["source_matrix_paths"][lr_key]).resolve()
        arm_root = matrix_root / "arms" / str(arm)
        source_authority = row.get("source_authority")
        matrix_snapshot_row = row.get("matrix_status")
        run_snapshot_row = row.get("run")
        status_snapshot_row = row.get("completion_status")
        if (
            Path(str(row.get("source_matrix_root"))).expanduser().resolve()
            != matrix_root
            or Path(str(row.get("source_arm_root"))).expanduser().resolve()
            != arm_root
            or not isinstance(source_authority, Mapping)
            or Path(str(source_authority.get("path"))).expanduser().resolve()
            != Path(str(base["authority_path"])).resolve()
            or source_authority.get("sha256") != base["authority_sha256"]
            or source_authority.get("pin_map_sha256")
            != authority.canonical_json_sha256(base["pinned_files"])
        ):
            raise R7500ReconciliationError(f"{arm} source path authority drifted")
        for label, snapshot_row, path_field, sha_field in (
            ("matrix", matrix_snapshot_row, "snapshot", "sha256"),
            ("journal", run_snapshot_row, "journal_snapshot", "journal_sha256"),
        ):
            if not isinstance(snapshot_row, Mapping):
                raise R7500ReconciliationError(f"{arm} bridge {label} row is missing")
            snapshot_path = (bridge_root / str(snapshot_row.get(path_field))).resolve()
            if (
                not snapshot_path.is_relative_to(bridge_root)
                or not snapshot_path.is_file()
                or snapshot_row.get(sha_field) != authority.sha256_file(snapshot_path)
            ):
                raise R7500ReconciliationError(f"{arm} bridge {label} snapshot drifted")
        if not isinstance(status_snapshot_row, Mapping):
            raise R7500ReconciliationError(f"{arm} bridge status row is missing")
        status_snapshot = (bridge_root / str(status_snapshot_row.get("snapshot"))).resolve()
        if (
            not status_snapshot.is_relative_to(bridge_root)
            or not status_snapshot.is_file()
            or status_snapshot_row.get("sidecar_schema") != bridge.STATUS_SIDECAR_SCHEMA
            or status_snapshot_row.get("sidecar_sha256")
            != authority.sha256_file(status_snapshot)
        ):
            raise R7500ReconciliationError(f"{arm} bridge status sidecar drifted")
        live_matrix_path = matrix_root / "matrix-status.json"
        matrix = _read_object(live_matrix_path, label="source matrix status")
        if matrix_snapshot_row.get("sha256") != authority.sha256_file(live_matrix_path):
            raise R7500ReconciliationError(f"{arm} matrix changed after bridge snapshot")
        runs = matrix.get("runs")
        verifications = matrix.get("verifications")
        expected_arms = list(base["arms"])
        if (
            matrix.get("schema") != bridge.MATRIX_SCHEMA
            or matrix.get("status") != "complete"
            or matrix.get("authority_sha256") != base["authority_sha256"]
            or matrix.get("episodes") != 1500
            or matrix.get("learning_rate") != float(lr_key)
            or not isinstance(runs, Mapping)
            or set(runs) != set(expected_arms)
            or not isinstance(verifications, Mapping)
            or set(verifications) != set(expected_arms)
        ):
            raise R7500ReconciliationError(f"{arm} source matrix is not complete")
        for source_arm in expected_arms:
            source_run = runs[source_arm]
            source_verification = verifications[source_arm]
            if (
                not isinstance(source_run, Mapping)
                or source_run.get("status") != "process_complete"
                or source_run.get("exit_code") != 0
                or not isinstance(source_verification, Mapping)
                or source_verification.get("status") != "PASS"
                or source_verification.get("episodes_completed") != 1500
            ):
                raise R7500ReconciliationError(
                    f"{arm} source matrix arm {source_arm} is not verified complete"
                )
        if Path(str(matrix.get("authority"))).expanduser().resolve() != Path(
            str(base["authority_path"])
        ).resolve():
            raise R7500ReconciliationError(f"{arm} source authority path drifted")
        run = runs.get(arm) if isinstance(runs, Mapping) else None
        if (
            not isinstance(run, Mapping)
            or run.get("status") != "process_complete"
            or run.get("exit_code") != 0
        ):
            raise R7500ReconciliationError(f"{arm} source arm has not completed cleanly")
        bridge._validate_canonical_command(
            run.get("command"),
            arm=str(arm),
            authority_path=Path(str(base["authority_path"])),
            arm_root=arm_root,
            tle_root=tle_root,
            repo=repo,
        )
        journal_path = arm_root / "run-journal.json"
        journal = _read_object(journal_path, label=f"{arm} completed run journal")
        if run_snapshot_row.get("journal_sha256") != authority.sha256_file(journal_path):
            raise R7500ReconciliationError(f"{arm} journal changed after bridge snapshot")
        if journal.get("schema") != bridge.JOURNAL_SCHEMA or journal.get("status") != "complete":
            raise R7500ReconciliationError(f"{arm} run journal is not complete")
        status_path = arm_root / "status.json"
        if not status_path.is_file():
            raise R7500ReconciliationError(f"{arm} completed process lacks status.json")
        # The full source status is outcome-bearing.  Reconciliation only hashes
        # its live bytes; all parsing below is against the bridge's redacted
        # structural sidecar.  This also binds the matrix receipt to the exact
        # status bytes that were observed at reconciliation time.
        live_status_sha = authority.sha256_file(status_path)
        live_status_sha_after = authority.sha256_file(status_path)
        if live_status_sha != live_status_sha_after:
            raise R7500ReconciliationError(
                f"{arm} source status changed while it was being hashed"
            )
        if (
            status_snapshot_row.get("source_status_sha256") != live_status_sha
        ):
            raise R7500ReconciliationError(f"{arm} source status SHA changed after bridge snapshot")
        try:
            status_sidecar = bridge.validate_structural_status_sidecar(
                _read_object(status_snapshot, label=f"{arm} structural status sidecar"),
                expected_source_sha256=live_status_sha,
                expected_arm=str(arm),
            )
        except bridge.R7500PrefixBridgeError as error:
            raise R7500ReconciliationError(
                f"{arm} structural status sidecar is not admissible"
            ) from error
        result = status_sidecar.get("result")
        if (
            status_sidecar.get("source_status_schema") != SOURCE_STATUS_SCHEMA
            or status_sidecar.get("status") != "complete"
            or status_sidecar.get("arm") != arm
            or status_sidecar.get("episodes_planned") != 1500
            or status_sidecar.get("episodes_executed") != 1500
            or status_sidecar.get("users") != 100
            or status_sidecar.get("seeds") != authority.TRAINING_SEEDS
            or Path(str(status_sidecar.get("authority_path"))).expanduser().resolve()
            != Path(str(base["authority_path"])).resolve()
            or status_sidecar.get("run_mode") != "fresh_intermediate_trend"
            or status_sidecar.get("claim_ceiling") != base["claim_ceiling"]
            or status_sidecar.get("formal_training_authorized") is not False
            or not isinstance(result, Mapping)
            or result.get("episodes") != 1500
            or result.get("checkpoint_every_episodes") != 100
            or result.get("periodic_checkpoint_count") != 15
        ):
            raise R7500ReconciliationError(f"{arm} completed status identity drifted")
        if arm != "B000" and (
            result.get("start_episode") != 0
            or result.get("episodes_executed") != 1500
            or result.get("episodes_completed") != 1500
            or result.get("artifact_scope") != "complete_run"
        ):
            raise R7500ReconciliationError("non-baseline source completion scope drifted")
        runtime = status_sidecar.get("runtime")
        runtime_authority = status_sidecar.get("runtime_authority")
        canonical_prereg = (repo / str(base["canonical_prereg"])).resolve()
        recorded_torch = (
            runtime.get("torch") if isinstance(runtime, Mapping) else None
        )
        if (
            not isinstance(runtime, Mapping)
            or runtime.get("python") != authority.RUNTIME_PYTHON_VERSION
            or runtime.get("numpy") != authority.RUNTIME_PACKAGES["numpy"]
            or not isinstance(recorded_torch, str)
            or recorded_torch.split("+", 1)[0]
            != authority.RUNTIME_PACKAGES["torch"]
            or not isinstance(runtime_authority, Mapping)
            or Path(str(runtime_authority.get("prereg_path"))).expanduser().resolve()
            != canonical_prereg
            or runtime_authority.get("prereg_sha256")
            != authority.sha256_file(canonical_prereg)
            or Path(
                str(runtime_authority.get("tle_root_path"))
            ).expanduser().resolve()
            != tle_root
            or runtime_authority.get("tle_file_count") != base["tle_file_count"]
            or runtime_authority.get("tle_file_set_sha256")
            != base["tle_file_set_sha256"]
        ):
            raise R7500ReconciliationError(
                f"{arm} source runtime or ephemeris identity drifted"
            )
        verification = verifications[arm]
        if (
            verification.get("status_sha256") != live_status_sha
            or verification.get("checkpoint_sha256") != result.get("checkpoint_sha256")
        ):
            raise R7500ReconciliationError(f"{arm} matrix verification receipt drifted")
        trainer_config = status_sidecar.get("trainer_config")
        if not isinstance(trainer_config, Mapping) or trainer_config != journal.get("trainer_config"):
            raise R7500ReconciliationError(f"{arm} trainer config receipt drifted")
        checkpoint_row = row.get("checkpoint")
        if not isinstance(checkpoint_row, Mapping):
            raise R7500ReconciliationError("bridge checkpoint row is malformed")
        snapshot = (bridge_root / str(checkpoint_row.get("snapshot"))).resolve()
        source = arm_root / "checkpoints" / bridge.CHECKPOINT_NAME
        source_sha = authority.sha256_file(source)
        snapshot_sha = authority.sha256_file(snapshot)
        periodic = _periodic_row(status_sidecar)
        if (
            Path(str(periodic.get("path"))).expanduser().resolve() != source.resolve()
            or periodic.get("sha256") != source_sha
            or source_sha != snapshot_sha
            or source_sha != checkpoint_row.get("artifact_sha256")
            or periodic.get("episode_index") != 499
            or periodic.get("checkpoint_kind") != "periodic-main-policy-trend"
            or periodic.get("load_round_trip") != "PASS"
        ):
            raise R7500ReconciliationError(f"{arm} EP500 artifact receipt drifted")
        source_payload = read_checkpoint(source, map_location="cpu")
        snapshot_payload = read_checkpoint(snapshot, map_location="cpu")
        source_identity = checkpoint_tools.validate_checkpoint_payload(
            source_payload,
            validated=base,
            trainer_config=trainer_config,
            episode_index=499,
            checkpoint_kind="periodic-main-policy-trend",
            label=f"lr={lr_key} {arm} source EP500",
        )
        snapshot_identity = checkpoint_tools.validate_checkpoint_payload(
            snapshot_payload,
            validated=base,
            trainer_config=trainer_config,
            episode_index=499,
            checkpoint_kind="periodic-main-policy-trend",
            label=f"lr={lr_key} {arm} snapshot EP500",
        )
        if source_identity != snapshot_identity or source_identity["online_policy_sha256"] != checkpoint_row.get(
            "online_policy_sha256"
        ):
            raise R7500ReconciliationError(f"{arm} EP500 policy digest drifted")
        reconciled.append(
            {
                "learning_rate": float(lr_key),
                "arm": arm,
                "source_status_sha256": live_status_sha,
                "source_journal_sha256": authority.sha256_file(journal_path),
                "artifact_sha256": source_sha,
                "online_policy_sha256": source_identity["online_policy_sha256"],
                "episode_index": 499,
                "episodes_completed": 500,
                "checkpoint_kind": "periodic-main-policy-trend",
                "load_round_trip": "PASS",
                "finite_state": "PASS",
            }
        )
    expected_grid = [
        (float(lr), arm)
        for lr in ("0.001", "0.01")
        for arm in authority.BRIDGED_ARMS
    ]
    if [(row["learning_rate"], row["arm"]) for row in reconciled] != expected_grid:
        raise R7500ReconciliationError("reconciliation grid order drifted")
    result = {
        "schema": SCHEMA,
        "status": "PASS",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "claim_ceiling": authority.CLAIM_CEILING,
        "required_labels": authority.REQUIRED_LABELS,
        "authority_sha256": authority_sha,
        "bridge_receipt": {"path": str(bridge_path), "sha256": authority.sha256_file(bridge_path)},
        "outcome_bearing_source_status_parsed_by_whitelist_extractor": True,
        "outcome_metric_fields_copied": False,
        "outcome_metric_fields_emitted": False,
        "outcome_metric_fields_used_for_admission": False,
        "outcome_metric_fields_admitted": False,
        "evaluation_authorized": True,
        "routing_authorized": True,
        "routing_arms": list(authority.PREFIX_ARMS),
        "bridged_arms": list(authority.BRIDGED_ARMS),
        # Reconciliation admits all five source prefixes, but it does not reveal
        # an ablation.  That authorization exists only after a valid LR-selection
        # receipt has been produced and revalidated by the ablation evaluator.
        "selected_lr_ablation_reveal_authorized": False,
        "selected_lr_ablation_reveal_eligible_after_valid_selection": True,
        "new_r7_training_authorized": False,
        "prefixes": reconciled,
    }
    output = (repo / validated["reconciliation_receipt"]).resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite R7 reconciliation receipt: {output}")
    _write_json_exclusive(output, result)
    return result


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--bridge-receipt", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    reconcile_prefixes(
        authority_path=args.authority,
        bridge_receipt_path=args.bridge_receipt,
        tle_root=args.tle_root,
    )
    print((REPO / authority.RECONCILIATION_RECEIPT).resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
