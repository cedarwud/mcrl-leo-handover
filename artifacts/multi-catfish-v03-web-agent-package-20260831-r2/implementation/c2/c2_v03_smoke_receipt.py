#!/usr/bin/env python3
"""Validate a completed C2 V0.3 smoke and emit a fail-closed receipt.

This is an evidence adapter, not a trainer.  It accepts one completed runner
directory, reuses the strict segment contract, and adds the checks that are
easy to miss when inspecting a directory by hand (checkpoint paths/hashes,
run-journal closure, and complete-run scope).  Its result is deliberately
limited to opportunity/dose mechanics.  Main EE is recorded only as a
ratio-of-sums descriptive quantity; this tool never makes an efficacy claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SMC_DIR = HERE.parent / "smc-er-short-ep"
for _path in (HERE, SMC_DIR, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import torch

import c2_temporal_fork_core as c2_core
import c2_temporal_fork_episode_runner as episode_runner
import c2_temporal_fork_trainer_backend as c2_backend
import c2_temporal_fork_segment_merge as merger


SCHEMA = "c2-v03a-opportunity-dose-smoke-receipt-v3"
JOURNAL_SCHEMA = "c2-v03-bounded-run-journal-v2"
CLAIM_CEILING = (
    "opportunity/dose mechanics only; Main ratio-of-sums EE is descriptive; "
    "no EE efficacy, training trend, Chapter-5 result, or deployment authorization"
)
REQUIRED_RUN_FILES = (
    "run-journal.json",
    "initial-main-checkpoint.pt",
    "final-checkpoint.pt",
    "carrier-state.pt",
    *merger.LIST_ARTIFACTS,
    "run-telemetry.json",
)


class SmokeReceiptError(RuntimeError):
    """The completed output is not safe to summarize as a smoke receipt."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON constant {value}")
            ),
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise SmokeReceiptError(f"invalid JSON artifact {path}: {error}") from error


def _mapping(value: Any, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SmokeReceiptError(f"{field} must be a mapping")
    return value


def _canonical_config(value: Any, *, field: str) -> dict[str, Any]:
    """Canonicalize tuples/lists so JSON and torch carrier views compare."""

    def convert(item: Any, item_field: str) -> Any:
        if isinstance(item, Mapping):
            if any(not isinstance(key, str) for key in item):
                raise SmokeReceiptError(f"{item_field} mapping keys must be strings")
            return {key: convert(item[key], f"{item_field}.{key}") for key in sorted(item)}
        if isinstance(item, (tuple, list)):
            return [convert(part, f"{item_field}[{index}]") for index, part in enumerate(item)]
        if isinstance(item, bool) or item is None or isinstance(item, (int, str)):
            return item
        if isinstance(item, float):
            if not math.isfinite(item):
                raise SmokeReceiptError(f"{item_field} contains a non-finite float")
            return item
        raise SmokeReceiptError(f"{item_field} contains unsupported value")

    result = convert(value, field)
    if not isinstance(result, dict) or "learning_rate" not in result:
        raise SmokeReceiptError(f"{field} must be a complete mapping with learning_rate")
    return result


def _digest(value: Any, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise SmokeReceiptError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _child_file(root: Path, raw: Any, *, field: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise SmokeReceiptError(f"{field} must be a nonempty path string")
    candidate = Path(raw).expanduser().resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise SmokeReceiptError(f"{field} escapes the runner output directory") from error
    if not candidate.is_file():
        raise SmokeReceiptError(f"{field} does not point to a file: {candidate}")
    return candidate


def _claim_is_bounded(claim: Any, *, field: str) -> str:
    if not isinstance(claim, str) or not claim.strip():
        raise SmokeReceiptError(f"{field} must be a nonempty claim ceiling")
    normalized = " ".join(claim.casefold().split())
    for required in ("no ee efficacy", "chapter-5", "deployment authorization"):
        if required not in normalized:
            raise SmokeReceiptError(
                f"{field} does not carry the required bounded-claim language: {required}"
            )
    return claim


def _validate_periodic_checkpoints(
    root: Path,
    result: Mapping[str, Any],
    *,
    episodes: int,
    checkpoint_every: int,
) -> list[dict[str, Any]]:
    raw = result.get("periodic_checkpoints")
    if not isinstance(raw, list):
        raise SmokeReceiptError("result.periodic_checkpoints must be a list")
    if result.get("periodic_checkpoint_count") != len(raw):
        raise SmokeReceiptError("periodic checkpoint count does not close")
    expected_episode_counts = list(range(checkpoint_every, episodes + 1, checkpoint_every))
    if [item.get("episodes_completed") for item in raw if isinstance(item, Mapping)] != expected_episode_counts:
        raise SmokeReceiptError("periodic checkpoint episode coverage is not exact")
    inventory: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for index, item in enumerate(raw):
        record = _mapping(item, field=f"result.periodic_checkpoints[{index}]")
        if record.get("checkpoint_kind") != "periodic-main-policy-trend":
            raise SmokeReceiptError(f"periodic checkpoint {index} kind drifted")
        if record.get("load_round_trip") != "PASS":
            raise SmokeReceiptError(f"periodic checkpoint {index} failed round-trip")
        try:
            path = _child_file(
                root,
                record.get("path"),
                field=f"result.periodic_checkpoints[{index}].path",
            )
        except SmokeReceiptError as error:
            raise SmokeReceiptError(f"periodic checkpoint {index} invalid: {error}") from error
        if path in seen:
            raise SmokeReceiptError("periodic checkpoint paths are duplicated")
        seen.add(path)
        claimed = _digest(
            record.get("sha256"),
            field=f"result.periodic_checkpoints[{index}].sha256",
        )
        actual = _sha256(path)
        if actual != claimed:
            raise SmokeReceiptError(f"periodic checkpoint {index} hash mismatch")
        inventory.append(
            {
                "path": str(path),
                "episodes_completed": record["episodes_completed"],
                "episode_index": record.get("episode_index"),
                "sha256": actual,
                "load_round_trip": "PASS",
            }
        )
    return inventory


def validate_completed_run(output_dir: Path) -> dict[str, Any]:
    """Return validated evidence for one complete C2 V0.3 runner output."""

    root = Path(output_dir).expanduser().resolve()
    if not root.is_dir():
        raise SmokeReceiptError(f"runner output directory does not exist: {root}")
    try:
        loaded = merger._load_segment(root)
    except (merger.SegmentMergeError, OSError, ValueError) as error:
        raise SmokeReceiptError(f"runner artifact contract rejected: {error}") from error

    status_path = root / "status.json"
    status = _mapping(_read_json(status_path), field="status")
    claim = _claim_is_bounded(status.get("claim_ceiling"), field="status.claim_ceiling")
    result = _mapping(status.get("result"), field="status.result")
    config = _mapping(status.get("config"), field="status.config")
    trainer_config = _canonical_config(
        status.get("trainer_config"), field="status.trainer_config"
    )
    if result.get("artifact_scope") != "complete_run":
        raise SmokeReceiptError("receipt requires a complete_run, not a segment")
    if result.get("start_episode") != 0:
        raise SmokeReceiptError("complete run must start at absolute episode zero")
    episodes = result.get("episodes")
    if type(episodes) is not int or episodes < 1:
        raise SmokeReceiptError("result.episodes must be a positive exact integer")
    if result.get("episodes_completed") != episodes or result.get("episodes_executed") != episodes:
        raise SmokeReceiptError("completed episode counts do not close")
    if config.get("episodes") != episodes:
        raise SmokeReceiptError("status config and result episode counts disagree")
    if config.get("arm") != status.get("arm"):
        raise SmokeReceiptError("status arm and config arm disagree")
    if "C2" not in loaded["active_sources"]:
        raise SmokeReceiptError("C2 is not active in this opportunity/dose run")
    max_candidates = config.get("max_c2_candidates")
    if type(max_candidates) is not int or max_candidates < 2:
        raise SmokeReceiptError("opportunity smoke requires max_c2_candidates >= 2")
    checkpoint_every = config.get("checkpoint_every")
    if type(checkpoint_every) is not int or checkpoint_every < 1:
        raise SmokeReceiptError("checkpoint_every must be a positive exact integer")
    if result.get("checkpoint_every_episodes") != checkpoint_every:
        raise SmokeReceiptError("checkpoint cadence disagrees with config")
    if result.get("claim_ceiling") != claim:
        raise SmokeReceiptError("status and result claim ceilings disagree")
    result_trainer_config = _canonical_config(
        result.get("trainer_config"), field="result.trainer_config"
    )
    if result_trainer_config != trainer_config:
        raise SmokeReceiptError("status and result trainer_config disagree")
    if "acrm_eta" not in config:
        raise SmokeReceiptError("status config lacks bound acrm_eta")
    acrm_eta = config["acrm_eta"]
    if isinstance(acrm_eta, bool) or not isinstance(acrm_eta, (int, float)):
        raise SmokeReceiptError("config.acrm_eta must be finite and nonnegative")
    if not math.isfinite(float(acrm_eta)) or float(acrm_eta) < 0.0:
        raise SmokeReceiptError("config.acrm_eta must be finite and nonnegative")

    journal_path = root / "run-journal.json"
    journal = _mapping(_read_json(journal_path), field="run-journal")
    if journal.get("schema") != JOURNAL_SCHEMA or journal.get("status") != "complete":
        raise SmokeReceiptError("run journal is not a completed bounded-run journal")
    if journal.get("config") != dict(config):
        raise SmokeReceiptError("run journal config disagrees with status config")
    journal_trainer_config = _canonical_config(
        journal.get("trainer_config"), field="run-journal.trainer_config"
    )
    if journal_trainer_config != trainer_config:
        raise SmokeReceiptError("run journal trainer_config disagrees with status")
    _claim_is_bounded(journal.get("claim_ceiling"), field="run-journal.claim_ceiling")
    journal_summary = _mapping(journal.get("result_summary"), field="run-journal.result_summary")
    if journal_summary.get("episodes") != episodes:
        raise SmokeReceiptError("run journal episode summary disagrees")
    if journal_summary.get("dispatch") != result.get("dispatch"):
        raise SmokeReceiptError("run journal dispatch disagrees")
    if journal_summary.get("checkpoint_sha256") != result.get("checkpoint_sha256"):
        raise SmokeReceiptError("run journal checkpoint digest disagrees")

    carrier_path_for_provenance = _child_file(
        root, result.get("carrier_state"), field="result.carrier_state"
    )
    try:
        carrier = torch.load(carrier_path_for_provenance, map_location="cpu", weights_only=False)
    except TypeError:
        carrier = torch.load(carrier_path_for_provenance, map_location="cpu")
    except Exception as error:
        raise SmokeReceiptError(f"carrier state is not loadable: {error}") from error
    carrier_mapping = _mapping(carrier, field="carrier-state")
    carrier_trainer_config = _canonical_config(
        carrier_mapping.get("trainer_config"), field="carrier-state.trainer_config"
    )
    main_state = _mapping(
        carrier_mapping.get("main_training_state"),
        field="carrier-state.main_training_state",
    )
    carrier_main_trainer_config = _canonical_config(
        main_state.get("trainer_config"),
        field="carrier-state.main_training_state.trainer_config",
    )
    if carrier_trainer_config != trainer_config or carrier_main_trainer_config != trainer_config:
        raise SmokeReceiptError("carrier trainer_config disagrees with status")
    carrier_authority = _mapping(
        carrier_mapping.get("authority"), field="carrier-state.authority"
    )
    mechanism_authority = _mapping(
        result.get("mechanism_authority"), field="result.mechanism_authority"
    )
    current_paths = episode_runner._c2_code_authority_paths()
    current_relative_paths = [
        path.relative_to(REPO).as_posix() for path in current_paths
    ]
    expected_mechanism_fields = {
        "candidate_version": c2_core.CANDIDATE_VERSION,
        "forecast_authority_schema": c2_core.FORECAST_AUTHORITY_SCHEMA,
        "main_policy_version": c2_backend.MAIN_POLICY_VERSION,
        "policy_compositor_version": c2_backend.POLICY_COMPOSITOR_VERSION,
        "environment_source_sha256": episode_runner._code_sha256(current_paths),
    }
    for field, expected in expected_mechanism_fields.items():
        if mechanism_authority.get(field) != expected:
            raise SmokeReceiptError(
                f"result.mechanism_authority.{field} disagrees with current code authority"
            )
    if mechanism_authority.get("code_authority_paths") != current_relative_paths:
        raise SmokeReceiptError(
            "result.mechanism_authority.code_authority_paths is not the exact current manifest"
        )
    reward_source_sha256 = _digest(
        mechanism_authority.get("reward_source_sha256"),
        field="result.mechanism_authority.reward_source_sha256",
    )
    for field in (
        "environment_source_sha256",
        "reward_source_sha256",
    ):
        if carrier_authority.get(field) != mechanism_authority.get(field):
            raise SmokeReceiptError(
                f"carrier-state authority {field} disagrees with result mechanism authority"
            )

    inventory: dict[str, dict[str, str]] = {}
    for name in REQUIRED_RUN_FILES:
        path = root / name
        if not path.is_file():
            raise SmokeReceiptError(f"required runner artifact is missing: {path}")
        inventory[name] = {"path": str(path), "sha256": _sha256(path)}

    final_path = _child_file(root, result.get("checkpoint"), field="result.checkpoint")
    final_claimed = _digest(result.get("checkpoint_sha256"), field="result.checkpoint_sha256")
    if _sha256(final_path) != final_claimed:
        raise SmokeReceiptError("final checkpoint hash mismatch")
    carrier_path = _child_file(root, result.get("carrier_state"), field="result.carrier_state")
    carrier_claimed = _digest(result.get("carrier_state_sha256"), field="result.carrier_state_sha256")
    if _sha256(carrier_path) != carrier_claimed:
        raise SmokeReceiptError("carrier-state hash mismatch")
    telemetry_path = _child_file(root, result.get("telemetry_path"), field="result.telemetry_path")
    telemetry_claimed = _digest(result.get("telemetry_sha256"), field="result.telemetry_sha256")
    if _sha256(telemetry_path) != telemetry_claimed:
        raise SmokeReceiptError("telemetry hash mismatch")
    audit_path = _child_file(
        root,
        result.get("c2_option_chronology_audit_path"),
        field="result.c2_option_chronology_audit_path",
    )
    audit_claimed = _digest(
        result.get("c2_option_chronology_audit_sha256"),
        field="result.c2_option_chronology_audit_sha256",
    )
    if _sha256(audit_path) != audit_claimed:
        raise SmokeReceiptError("C2 chronology audit hash mismatch")

    periodic = _validate_periodic_checkpoints(
        root, result, episodes=episodes, checkpoint_every=checkpoint_every
    )
    telemetry = loaded["telemetry"]
    main = telemetry["main"]
    c2 = telemetry["c2"]
    for index, row in enumerate(_read_json(root / "c2-training-receipts.json")):
        if len(row.get("candidate_rows", [])) > max_candidates:
            raise SmokeReceiptError(f"C2 candidate schedule {index} exceeds configured cap")

    inventory["final-checkpoint.pt"] = {"path": str(final_path), "sha256": final_claimed}
    inventory["carrier-state.pt"] = {"path": str(carrier_path), "sha256": carrier_claimed}
    inventory["run-telemetry.json"] = {"path": str(telemetry_path), "sha256": telemetry_claimed}
    inventory["c2-option-chronology-audits.json"] = {
        "path": str(audit_path),
        "sha256": audit_claimed,
    }
    return {
        "root": root,
        "status_sha256": _sha256(status_path),
        "claim_ceiling": claim,
        "config": dict(config),
        "provenance": {
            "acrm_eta": acrm_eta,
            "trainer_config": trainer_config,
            "carrier_trainer_config": carrier_trainer_config,
        },
        "mechanism_authority": {
            **dict(mechanism_authority),
            "reward_source_sha256": reward_source_sha256,
        },
        "authority_identity": loaded["authority"],
        "arm": loaded["arm"],
        "dispatch": loaded["dispatch"],
        "active_sources": loaded["active_sources"],
        "episodes": {
            "configured": episodes,
            "completed": result["episodes_completed"],
            "executed": result["episodes_executed"],
            "start_episode": result["start_episode"],
        },
        "c2": {
            "schedules": c2["schedules"],
            "candidate_outcomes": dict(c2["candidate_outcomes"]),
            "choice_counts": dict(c2["choice_counts"]),
            "empty_anchor_attempts": c2["empty_anchor_attempts"],
            "scheduled_candidates": c2["scheduled_candidates"],
            "options_executed": c2["options_executed"],
            "option_primitive_steps": c2["option_primitive_steps"],
            "admitted_options": c2["admitted_options"],
            "q2f_updates": c2["q2f_updates"],
            "joint_commits": c2["joint_commits"],
            "joint_commit_per_main_step": c2["joint_commit_per_main_step"],
            "forecast_wall_time_s": c2["forecast_wall_time_s"],
        },
        "main_descriptive": {
            "useful_bits": main["useful_bits"],
            "energy_j": main["energy_j"],
            "ratio_of_sums_ee_bits_per_j": main["ratio_of_sums_ee_bits_per_j"],
            "served_user_intervals": main["served_user_intervals"],
            "user_intervals": main["user_intervals"],
            "served_fraction": main["served_fraction"],
            "rule": "useful_bits / energy_j; descriptive only, never an efficacy result",
        },
        "checkpoint_inventory": {
            "initial": inventory["initial-main-checkpoint.pt"],
            "final": inventory["final-checkpoint.pt"],
            "carrier_state": inventory["carrier-state.pt"],
            "periodic": periodic,
        },
        "artifact_sha256": inventory,
        "verification": {
            "status_config_authority": "PASS",
            "episode_step_closure": "PASS",
            "c2_schedule_and_choice_closure": "PASS",
            "c2_execution_dose_closure": "PASS",
            "checkpoint_existence_and_hashes": "PASS",
            "policy_code_authority": "PASS",
        },
    }


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def write_smoke_receipt(output_dir: Path, receipt_path: Path) -> dict[str, Any]:
    """Validate ``output_dir`` and atomically create a new receipt."""

    destination = Path(receipt_path).expanduser().resolve()
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite receipt: {destination}")
    evidence = validate_completed_run(output_dir)
    source_claim = evidence.pop("claim_ceiling")
    receipt = {
        "schema": SCHEMA,
        "status": "PASS",
        "claim_ceiling": CLAIM_CEILING,
        "source_claim_ceiling": source_claim,
        "source_output_dir": str(evidence.pop("root")),
        **evidence,
        "receipt_digest_policy": "receipt_path and receipt_sha256 are returned out of band",
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.staging-", dir=destination.parent))
    try:
        staged = staging / destination.name
        _write_json(staged, receipt)
        if destination.exists():
            raise FileExistsError(f"refusing to overwrite receipt: {destination}")
        os.rename(staged, destination)
    except BaseException:
        if staging.exists():
            for child in staging.iterdir():
                child.unlink()
            staging.rmdir()
        raise
    receipt["receipt_path"] = str(destination)
    receipt["receipt_sha256"] = _sha256(destination)
    return receipt


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    receipt = write_smoke_receipt(args.input_dir, args.receipt)
    print(receipt["receipt_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
