#!/usr/bin/env python3
"""Launch the sealed LR=0.001, 100EP five-arm diagnostic pilot.

The launcher is a thin adapter over the already tested matrix process manager
and receipt verifiers.  It accepts only the canonical pilot authority, an
absent output root, the runtime TLE root, and bounded parallelism.  All
training/evaluation knobs are derived from the authority.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import run_intermediate_trend_matrix as matrix  # noqa: E402
from pilot100_authority import (  # noqa: E402
    CANONICAL_AUTHORITY_RELATIVE,
    CLAIM_CEILING,
    EVIDENCE_CEILING,
    PILOT_EPISODES,
    PILOT_OUTPUT_RELATIVE,
    validate_pilot100_authority,
)
from pilot100_sweep_verifier import verify_pilot100_sweep  # noqa: E402
from pilot100_arm_verifier import verify_pilot100_arm  # noqa: E402


SCHEMA = "multi-catfish-mcrl-pilot100-matrix-v1"
ARM_RUNNER = HERE / "run_pilot100_arm.py"


class Pilot100MatrixError(RuntimeError):
    """Raised when the 100EP pilot cannot be authorised or completed."""


def _read_object(path: Path, *, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise Pilot100MatrixError(f"{label} is unreadable: {path}") from error
    if not isinstance(value, Mapping):
        raise Pilot100MatrixError(f"{label} must be a JSON object: {path}")
    return value


def load_and_validate_authority(path: Path, *, tle_root: Path) -> dict[str, Any]:
    authority_path = Path(path).expanduser().resolve()
    canonical = (REPO / CANONICAL_AUTHORITY_RELATIVE).resolve()
    if authority_path != canonical:
        raise Pilot100MatrixError(
            f"canonical pilot authority path required: {canonical}"
        )
    request = _read_object(authority_path, label="pilot100 authority")
    try:
        validated = validate_pilot100_authority(
            request,
            tle_root=Path(tle_root).expanduser().resolve(),
            repo=REPO,
        )
    except Exception as error:
        raise Pilot100MatrixError(f"pilot100 authority rejected: {error}") from error
    if validated.get("status") != "PASS":
        raise Pilot100MatrixError("pilot100 authority validator did not return PASS")
    return dict(validated)


def arm_command(
    *,
    authority_path: Path,
    arm: str,
    output_dir: Path,
    tle_root: Path,
) -> list[str]:
    """Build the knob-free command for one authority-derived pilot arm."""

    if arm not in matrix.ALLOWED_ARMS:
        raise Pilot100MatrixError(f"arm is outside the five-arm pilot: {arm}")
    return [
        sys.executable,
        str(ARM_RUNNER),
        "--authority",
        str(Path(authority_path).expanduser().resolve()),
        "--arm",
        arm,
        "--output-dir",
        str(Path(output_dir).expanduser().resolve()),
        "--tle-root",
        str(Path(tle_root).expanduser().resolve()),
    ]


def _preflight(
    *,
    authority_path: Path,
    output_root: Path,
    tle_root: Path,
    max_parallel: int,
) -> dict[str, Any]:
    if max_parallel not in (1, 2):
        raise Pilot100MatrixError("max_parallel must be 1 or 2")
    root = Path(output_root).expanduser().resolve()
    canonical_output = (REPO / PILOT_OUTPUT_RELATIVE).resolve()
    if root != canonical_output:
        raise Pilot100MatrixError(
            f"canonical pilot output root required: {canonical_output}"
        )
    if root.exists():
        raise Pilot100MatrixError(
            f"output root must be absent before launch: {root}"
        )
    authority_file = Path(authority_path).expanduser().resolve()
    validated = load_and_validate_authority(authority_file, tle_root=tle_root)
    config = matrix._config(validated)
    prereg, c1_corpus = matrix._authority_paths(validated)
    expected_tle_hash = str(
        validated.get("authority", {}).get("tle_file_set_sha256", "")
    )
    if expected_tle_hash != matrix.CANONICAL_TLE_FILE_SET_SHA256:
        raise Pilot100MatrixError("authority TLE file-set hash is not canonical")
    actual_tle_hash, tle_file_count = matrix.canonical_tle_file_set_hash(tle_root)
    if actual_tle_hash != expected_tle_hash:
        raise Pilot100MatrixError(
            "supplied TLE root does not match the authority file-set hash"
        )
    runtime_tle = Path(tle_root).expanduser().resolve()
    logs = root / "logs"
    plans = [
        matrix.ArmPlan(
            arm=arm,
            output_dir=root / arm,
            command=tuple(
                arm_command(
                    authority_path=authority_file,
                    arm=arm,
                    output_dir=root / arm,
                    tle_root=runtime_tle,
                )
            ),
            log_path=logs / f"{index:02d}-{arm}.log",
            usage_path=logs / f"{index:02d}-{arm}.time-v.log",
        )
        for index, arm in enumerate(matrix.ALLOWED_ARMS, start=1)
    ]
    return {
        "authority_file": authority_file,
        "authority_sha256": matrix.sha256_file(authority_file),
        "validated": validated,
        "config": config,
        "prereg": prereg,
        "prereg_sha256": matrix.sha256_file(prereg),
        "c1_corpus": c1_corpus,
        "c1_corpus_sha256": matrix.sha256_file(c1_corpus),
        "expected_tle_hash": expected_tle_hash,
        "actual_tle_hash": actual_tle_hash,
        "tle_file_count": tle_file_count,
        "tle_root": runtime_tle,
        "output_root": root,
        "logs": logs,
        "plans": plans,
        "max_parallel": max_parallel,
    }


def preflight_receipt(
    *,
    authority_path: Path,
    output_root: Path,
    tle_root: Path,
    max_parallel: int,
) -> dict[str, Any]:
    """Return a no-write, no-launch receipt for the exact five commands."""

    state = _preflight(
        authority_path=authority_path,
        output_root=output_root,
        tle_root=tle_root,
        max_parallel=max_parallel,
    )
    authority_file = state["authority_file"]
    return {
        "schema": "multi-catfish-mcrl-pilot100-preflight-v1",
        "status": "PASS",
        "claim_ceiling": CLAIM_CEILING,
        "authority_manifest": str(authority_file),
        "authority_manifest_sha256": state["authority_sha256"],
        "episodes": PILOT_EPISODES,
        "learning_rate": state["validated"]["learning_rate"],
        "arms": list(matrix.ALLOWED_ARMS),
        "max_parallel": max_parallel,
        "output_root_absent": True,
        "tle_file_set_sha256": state["actual_tle_hash"],
        "tle_file_count": state["tle_file_count"],
        "commands": [list(plan.command) for plan in state["plans"]],
        "no_process_launched": True,
        "formal_training_authorized": False,
        "automatic_longer_run_authorized": False,
        "9000_authorized": False,
    }


def _verify_pilot_binding(
    *,
    row: Mapping[str, Any],
    validated: Mapping[str, Any],
    authority_sha256: str,
) -> dict[str, Any]:
    failures: list[str] = []
    verification = row.get("verification")
    status_path = (
        Path(str(verification.get("status_path")))
        if isinstance(verification, Mapping)
        else None
    )
    status = None
    if status_path is None or not status_path.is_file():
        failures.append("pilot status path missing")
    else:
        try:
            status = _read_object(status_path, label="pilot arm status")
        except Pilot100MatrixError as error:
            failures.append(str(error))
    if status is not None:
        exact = {
            "schema": "multi-catfish-mcrl-pilot100-one-arm-v1",
            "claim_ceiling": CLAIM_CEILING,
            "formal_training_authorized": False,
            "automatic_longer_run_authorized": False,
            "9000_authorized": False,
        }
        for field, expected in exact.items():
            if status.get(field) != expected:
                failures.append(f"pilot status.{field} mismatch")
        gate = status.get("gate_manifest")
        if not isinstance(gate, Mapping):
            failures.append("pilot gate manifest missing")
        else:
            if gate.get("status") != "AUTHORIZED_FOR_BOUNDED_100EP_PILOT":
                failures.append("pilot gate status mismatch")
            if gate.get("authority_manifest_sha256") != authority_sha256:
                failures.append("pilot gate authority hash mismatch")
            if gate.get("validated") != validated:
                failures.append("pilot gate validated authority mismatch")
        expected_sources = {
            **validated["authority"]["protected_source_sha256"],
            **validated["authority"]["pilot_route_source_sha256"],
        }
        if status.get("source_files_sha256") != expected_sources:
            failures.append("pilot status source binding mismatch")
    arm_verification = None
    if status_path is not None and status_path.is_file():
        arm_verification = verify_pilot100_arm(
            status_path=status_path,
            arm=str(row.get("arm")),
            episodes=PILOT_EPISODES,
        )
        failures.extend(str(item) for item in arm_verification["failures"])
    return {
        "status": "PASS" if not failures else "FAIL",
        "arm_receipt_verification": arm_verification,
        "failures": failures,
    }


def _drift_check(state: Mapping[str, Any], *, phase: str) -> dict[str, Any]:
    """Revalidate all authority/source/TLE bindings after long-running work."""

    failures: list[str] = []
    try:
        current = load_and_validate_authority(
            state["authority_file"], tle_root=state["tle_root"]
        )
    except Exception as error:
        current = None
        failures.append(f"authority revalidation rejected ({type(error).__name__}: {error})")
    if current is not None and current != state["validated"]:
        failures.append("validated authority changed during pilot")
    try:
        tle_hash, tle_count = matrix.canonical_tle_file_set_hash(state["tle_root"])
    except Exception as error:
        tle_hash = None
        tle_count = None
        failures.append(f"runtime TLE revalidation rejected ({type(error).__name__}: {error})")
    if tle_hash != state["expected_tle_hash"] or tle_count != state["tle_file_count"]:
        failures.append("runtime TLE file set changed during pilot")
    try:
        current_authority_sha = matrix.sha256_file(state["authority_file"])
    except (OSError, RuntimeError):
        current_authority_sha = None
        failures.append("authority manifest disappeared during pilot")
    if current_authority_sha != state["authority_sha256"]:
        failures.append("authority manifest bytes changed during pilot")
    return {
        "phase": phase,
        "status": "PASS" if not failures else "FAIL",
        "authority_manifest_sha256_initial": state["authority_sha256"],
        "authority_manifest_sha256_current": current_authority_sha,
        "tle_file_set_sha256": tle_hash,
        "tle_file_count": tle_count,
        "failures": failures,
    }


def run_matrix(
    *,
    authority_path: Path,
    output_root: Path,
    tle_root: Path,
    max_parallel: int,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Run exactly five 100EP arms, verify them, then run the EE sweep."""

    state = _preflight(
        authority_path=authority_path,
        output_root=output_root,
        tle_root=tle_root,
        max_parallel=max_parallel,
    )
    root = state["output_root"]
    logs = state["logs"]
    root.mkdir(parents=True, exist_ok=False)
    logs.mkdir()

    arm_receipts, arm_failed = matrix._collect_arm_runs(
        plans=state["plans"],
        max_parallel=max_parallel,
        validated=state["validated"],
        config=state["config"],
        expected_tle_hash=state["expected_tle_hash"],
        expected_episodes=PILOT_EPISODES,
        require_periodic=True,
        sleep_fn=sleep_fn,
    )
    authority_sha = state["authority_sha256"]
    for row in arm_receipts:
        if row.get("status") != "PASS":
            continue
        pilot_verification = _verify_pilot_binding(
            row=row,
            validated=state["validated"],
            authority_sha256=authority_sha,
        )
        row["pilot_verification"] = pilot_verification
        if pilot_verification["status"] != "PASS":
            row["status"] = "failed"
            arm_failed = True

    checkpoints: dict[str, Path] = {}
    for row in arm_receipts:
        verification = row.get("verification")
        if (
            row.get("status") == "PASS"
            and isinstance(verification, Mapping)
            and verification.get("status") == "PASS"
        ):
            checkpoints[str(row["arm"])] = Path(str(verification["checkpoint_path"]))

    drift_checks = [_drift_check(state, phase="before_sweep")]
    if drift_checks[-1]["status"] != "PASS":
        arm_failed = True

    sweep_receipt: dict[str, Any] | None = None
    sweep_success = False
    if not arm_failed and tuple(checkpoints) == tuple(matrix.ALLOWED_ARMS):
        sweep_output = root / "ee-sweep"
        sweep_plan = matrix.ArmPlan(
            arm="EE_SWEEP",
            output_dir=sweep_output,
            command=tuple(
                matrix.sweep_command(
                    validated=state["validated"],
                    checkpoints=checkpoints,
                    output_dir=sweep_output,
                    tle_root=state["tle_root"],
                    prereg=state["prereg"],
                )
            ),
            log_path=logs / "20-ee-sweep.log",
            usage_path=logs / "20-ee-sweep.time-v.log",
        )
        sweep_receipt, sweep_success = matrix._execute_sweep(
            plan=sweep_plan,
            validated=state["validated"],
            config=state["config"],
            expected_tle_hash=state["expected_tle_hash"],
        )
        if sweep_success:
            strong_verification = verify_pilot100_sweep(
                output_dir=sweep_output,
                training_seed=state["config"]["training_seed"],
                evaluation_users=state["config"]["evaluation_users"],
                evaluation_seeds=state["config"]["evaluation_seeds"],
                checkpoints=checkpoints,
                expected_tle_hash=state["expected_tle_hash"],
                expected_tle_count=state["tle_file_count"],
                expected_prereg_sha256=state["validated"]["authority"][
                    "canonical_prereg_sha256"
                ],
                expected_episode_index=PILOT_EPISODES - 1,
            )
            sweep_receipt["pilot100_verification"] = strong_verification
            if strong_verification["status"] != "PASS":
                sweep_receipt["status"] = "failed"
                sweep_success = False

    drift_checks.append(_drift_check(state, phase="before_final_complete"))
    complete = (
        not arm_failed
        and sweep_success
        and all(row["status"] == "PASS" for row in drift_checks)
    )
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "complete" if complete else "failed",
        "execution_complete": bool(complete),
        "claim_ceiling": CLAIM_CEILING,
        "evidence_ceiling": EVIDENCE_CEILING,
        "authority_manifest": str(state["authority_file"]),
        "authority_manifest_sha256": authority_sha,
        "episodes": PILOT_EPISODES,
        "learning_rate": state["validated"]["learning_rate"],
        "arms": list(matrix.ALLOWED_ARMS),
        "max_parallel": max_parallel,
        "training": {
            "users": state["config"]["users"],
            "training_seed": state["config"]["training_seed"],
            "environment_seed": state["config"]["environment_seed"],
            "mobility_seed": state["config"]["mobility_seed"],
            "epsilon_decay_episodes": state["config"]["epsilon_decay_episodes"],
            "target_update_every": state["config"]["target_update_every"],
            "checkpoint_every_episodes": state["config"]["checkpoint_every_episodes"],
            "specialist_bundle_replay_capacity": state["config"][
                "specialist_bundle_replay_capacity"
            ],
            "acrm_eta": state["config"]["acrm_eta"],
            "donor_beta": state["config"]["donor_beta"],
        },
        "evaluation": {
            "users": list(state["config"]["evaluation_users"]),
            "seeds": list(state["config"]["evaluation_seeds"]),
            "policy": "Main-only masked-greedy MODQN",
            "partition": "TEST",
            "ee_aggregation": "ratio-of-sums per training seed, then equal-weight mean",
        },
        "canonical_inputs": {
            "prereg": str(state["prereg"]),
            "prereg_sha256": state["prereg_sha256"],
            "c1_exp_corpus_manifest": str(state["c1_corpus"]),
            "c1_exp_corpus_manifest_sha256": state["c1_corpus_sha256"],
            "tle_root": str(state["tle_root"]),
            "tle_file_set_sha256": state["actual_tle_hash"],
            "tle_file_count": state["tle_file_count"],
        },
        "continuation_rule": state["validated"]["continuation_rule"],
        "automatic_continuation_ready": False,
        "drift_checks": drift_checks,
        "arm_runs": arm_receipts,
        "sweep": sweep_receipt,
        "no_retry": True,
        "formal_training_authorized": False,
        "automatic_longer_run_authorized": False,
        "9000_authorized": False,
    }
    matrix._write_json(root / "matrix-receipt.json", receipt)
    if not complete:
        raise Pilot100MatrixError(
            f"pilot100 matrix failed; receipt: {root / 'matrix-receipt.json'}"
        )
    return receipt


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    parser.add_argument("--max-parallel", type=int, choices=(1, 2), default=1)
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="validate and print the exact five commands without writing or launching",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    try:
        if args.preflight_only:
            receipt = preflight_receipt(
                authority_path=args.authority,
                output_root=args.output_root,
                tle_root=args.tle_root,
                max_parallel=args.max_parallel,
            )
            print(json.dumps(receipt, indent=2, sort_keys=True))
            return 0
        run_matrix(
            authority_path=args.authority,
            output_root=args.output_root,
            tle_root=args.tle_root,
            max_parallel=args.max_parallel,
        )
    except Pilot100MatrixError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(Path(args.output_root).expanduser().resolve() / "matrix-receipt.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
