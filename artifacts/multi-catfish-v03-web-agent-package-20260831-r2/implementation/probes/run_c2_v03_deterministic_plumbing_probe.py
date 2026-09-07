#!/usr/bin/env python3
"""Deterministic, no-training C2 V0.3 fixed-lambda plumbing probe.

This is intentionally a receipt probe, not an option runner or a C2 efficacy
census.  The live world always advances with masked-greedy Main.  At sealed
handover anchors, an incumbent-hold ``PreparedC2Fork`` produces detached
reference/candidate traces.  Every complete four-offset trace is retained and
scored with one Main-reference calibration multiplier, irrespective of the
legacy C2 certificate's pass/fail result.  A forecast support rejection is a
right-censored observation; it is never substituted, dropped, or imputed.

The current fork disables fading, so its output is diagnostic-only: it checks
the pre-outcome API, offset accounting, raw receipts, and Main non-mutation.
It does not establish stochastic physical viability or EE efficacy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile
import time
from typing import Any, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
C2_V03 = REPO / ".scratch" / "c2-v03"
STAGE0 = REPO / ".scratch" / "catfish-stage0"
SMC = REPO / ".scratch" / "smc-er-short-ep"
LEGACY = REPO / ".scratch" / "catfish-oracle-gate"
for path in (HERE, C2_V03, STAGE0, SMC, LEGACY, REPO, REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import c2_temporal_fork_trainer_backend as backend  # noqa: E402
import run_c2_v03_real_backend_smoke as smoke  # noqa: E402
import scripts.run_head_pivotality_probe as loader  # noqa: E402
from mcrl.env.action_contract import Association  # noqa: E402
from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.env.keyed_fading import KEYED_FADING_VERSION  # noqa: E402
from mcrl.runtime.probe_p6 import P6_EVALUATION_SEEDS  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    _code_sha256,
    _default_code_paths,
)
from run_c3_unilateral_oracle_pilot import (  # noqa: E402
    DEFAULT_INPUT,
    DEFAULT_PREREG,
    _freeze_lambda,
    _frozen_archive,
)


EXPECTED_OFFSETS = (0, 1, 2, 3)
DEFAULT_OUTPUT = HERE / "c2-v03-deterministic-plumbing-probe.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _departure_users(wrapped: Any, main_physical: Sequence[Any]) -> list[int]:
    """Return the sealed ascending incumbent-departure schedule."""

    users: list[int] = []
    for uid, (incumbent, physical) in enumerate(
        zip(wrapped.environment._previous_association, main_physical, strict=True)
    ):
        if (
            isinstance(incumbent, Association)
            and physical is not None
            and physical != (int(incumbent.norad_id), int(incumbent.cell_id))
        ):
            users.append(uid)
    return users


def _trace_receipts(
    reference_trace: Sequence[Any],
    candidate_trace: Sequence[Any],
    *,
    interval_s: float,
    multiplier: float,
    focal_user: int,
) -> tuple[list[dict[str, Any]], float, dict[str, Any]]:
    """Read exactly offsets 0..3 and compute their fixed-lambda surpluses."""

    if len(reference_trace) != len(EXPECTED_OFFSETS) or len(candidate_trace) != len(
        EXPECTED_OFFSETS
    ):
        raise RuntimeError("complete C2 trace must contain exactly offsets 0..3")

    receipts: list[dict[str, Any]] = []
    for expected, reference, candidate in zip(
        EXPECTED_OFFSETS, reference_trace, candidate_trace, strict=True
    ):
        if int(reference.offset) != expected or int(candidate.offset) != expected:
            raise RuntimeError("C2 trace offsets must be exactly ordered 0..3")
        reference_rates = [float(value) for value in reference.link_rate_bps]
        candidate_rates = [float(value) for value in candidate.link_rate_bps]
        if len(reference_rates) != len(candidate_rates):
            raise RuntimeError("matched C2 traces have different user counts")
        delta_rates = [
            candidate_rate - reference_rate
            for reference_rate, candidate_rate in zip(
                reference_rates, candidate_rates, strict=True
            )
        ]
        delta_rate_sum = math.fsum(delta_rates)
        reference_power = float(reference.system_power_w)
        candidate_power = float(candidate.system_power_w)
        delta_power = candidate_power - reference_power
        g_k = interval_s * delta_rate_sum - multiplier * interval_s * delta_power
        reference_served = [bool(value) for value in reference.served]
        candidate_served = [bool(value) for value in candidate.served]
        if len(reference_served) != len(candidate_served):
            raise RuntimeError("matched C2 traces have different served-vector sizes")
        new_outage_users = [
            uid
            for uid, (served_m, served_c) in enumerate(
                zip(reference_served, candidate_served, strict=True)
            )
            if served_m and not served_c
        ]
        receipts.append(
            {
                "offset": expected,
                "reference_per_user_rate_bps": reference_rates,
                "candidate_per_user_rate_bps": candidate_rates,
                "delta_per_user_rate_bps": delta_rates,
                "reference_system_rate_bps": math.fsum(reference_rates),
                "candidate_system_rate_bps": math.fsum(candidate_rates),
                "delta_system_rate_bps": delta_rate_sum,
                "reference_system_power_w": reference_power,
                "candidate_system_power_w": candidate_power,
                "delta_system_power_w": delta_power,
                "g_k_fixed_lambda_bits": g_k,
                "reference_served": reference_served,
                "candidate_served": candidate_served,
                "reference_served_count": sum(reference_served),
                "candidate_served_count": sum(candidate_served),
                "new_outage_users": new_outage_users,
            }
        )
    z2 = math.fsum(row["g_k_fixed_lambda_bits"] for row in receipts[1:])
    downstream = receipts[1:]
    service_guard = {
        "offsets": [int(row["offset"]) for row in downstream],
        "no_new_outage_for_any_reference_served_user": all(
            not row["new_outage_users"] for row in downstream
        ),
        "served_count_not_lower": all(
            int(row["candidate_served_count"])
            >= int(row["reference_served_count"])
            for row in downstream
        ),
        "focal_reference_service_preserved": all(
            not row["reference_served"][focal_user]
            or row["candidate_served"][focal_user]
            for row in downstream
        ),
    }
    service_guard["passed"] = all(service_guard[key] for key in (
        "no_new_outage_for_any_reference_served_user",
        "served_count_not_lower",
        "focal_reference_service_preserved",
    ))
    return receipts, float(z2), service_guard


def _certificate_diagnostic(build: Any) -> dict[str, Any]:
    """Keep old C2 admission evidence as diagnostic data only."""

    certificate = build.certificate
    return {
        "passed": bool(certificate.passed),
        "failures": [failure.value for failure in certificate.failures],
        "ee_surplus_bits": float(certificate.ee_surplus_bits),
        "ee_surplus_floor_bits": float(certificate.ee_surplus_floor_bits),
        "hold_r2_margin": float(certificate.hold_r2_margin),
        "full_r2_margin": float(certificate.full_r2_margin),
        "support_actions": [int(action) for action in certificate.support_actions],
    }


def _support_censor(error: backend.C2ForecastSupportRejection) -> dict[str, Any]:
    return {
        "outcome": "RIGHT_CENSORED_SUPPORT_REJECTION",
        "censor_reason": error.reason,
        "forecast_offset": int(error.forecast_offset),
        "branch_side": "candidate",
        "user": int(error.user),
        "physical_key": (
            None if error.physical_key is None else list(error.physical_key)
        ),
        "detail": str(error),
    }


def main(
    argv: Sequence[str] | None = None,
    *,
    default_fading_mode: str = "disabled",
    default_output: Path = DEFAULT_OUTPUT,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=default_output)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument(
        "--tle-root", type=Path, default=Path(TLE_ROOT_DEFAULT).expanduser()
    )
    parser.add_argument("--users", type=int, default=smoke.USERS)
    parser.add_argument("--max-candidates", type=int, default=3)
    parser.add_argument("--max-anchors", type=int, default=1)
    parser.add_argument("--seed", type=int, default=smoke.DEVELOPMENT_SEED)
    parser.add_argument(
        "--calibration-seed",
        type=int,
        default=P6_EVALUATION_SEEDS[0],
        help="one frozen TRAIN-only Main seed shared across every C2 evaluation seed",
    )
    parser.add_argument(
        "--fading-mode",
        choices=("disabled", KEYED_FADING_VERSION),
        default=default_fading_mode,
    )
    args = parser.parse_args(argv)
    if (
        args.max_candidates <= 0
        or args.max_anchors <= 0
        or args.users <= 0
        or args.seed < 0
        or args.calibration_seed < 0
    ):
        raise ValueError("candidate/anchor caps must be positive and seed nonnegative")

    record = read_prereg(args.prereg)
    frozen_temp = tempfile.TemporaryDirectory(prefix="mcrl-ee-axis-c2-v03-")
    archive = _frozen_archive(
        record, args.tle_root, Path(frozen_temp.name) / "frozen-tle"
    )
    trainer, checkpoint = loader._verify_and_load_trainer(
        record,
        archive,
        run_dir=args.input_dir / "main",
        users=args.users,
    )
    networks_before = smoke._network_snapshot(trainer)
    replay_before = len(trainer.replay)
    environment_source_sha256 = _code_sha256(_default_code_paths())
    reward_source_sha256 = _sha256(REPO / "src/mcrl/env/step.py")

    # This is the same Q1-reference ratio-of-sums helper used by the C3 pilot.
    # Its environment is separate from the Main-only live path below.
    calibration_wrapped = loader._make_environment(archive, users=args.users)
    calibration = _freeze_lambda(
        trainer,
        calibration_wrapped,
        seed=args.calibration_seed,
    )
    multiplier = float(calibration["lambda_bits_per_j"])
    interval_s = float(calibration["interval_s"])

    wrapped = loader._make_environment(archive, users=args.users)
    env_rng, mobility_rng, _action_rng, _control_rng = loader._evaluation_rngs(
        args.seed
    )
    states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    anchors: list[dict[str, Any]] = []
    started = time.perf_counter()

    while int(observation.step_index) <= smoke.MAX_ANCHOR_STEP:
        main_actions, main_physical = smoke._main_decision(
            trainer, wrapped, states, masks, observation, env_rng
        )
        departures = _departure_users(wrapped, main_physical)
        if departures and 10 - int(observation.step_index) >= 4:
            scheduled = departures[: args.max_candidates]
            rows: list[dict[str, Any]] = []
            for focal_user in scheduled:
                row_started = time.perf_counter()
                try:
                    service = backend.C2TemporalForkTrainerBackend(
                        wrapped=wrapped,
                        states=states,
                        masks=masks,
                        observation=observation,
                        env_rng=env_rng,
                        trainer=trainer,
                        checkpoint_sha256=checkpoint["checkpoint_sha256"],
                        environment_source_sha256=environment_source_sha256,
                        reward_source_sha256=reward_source_sha256,
                        evaluation_seed=args.seed,
                        focal_user=focal_user,
                        forecast_fading_mode=args.fading_mode,
                    )
                    prepared = service.prepare_hold_or_max_lagged_gain_rival(
                        focal_user=focal_user
                    )
                    build = prepared.run_forecast()
                    offset_receipts, z2, service_guard = _trace_receipts(
                        prepared.reference_trace,
                        prepared.candidate_trace,
                        interval_s=interval_s,
                        multiplier=multiplier,
                        focal_user=focal_user,
                    )
                    rows.append(
                        {
                            "outcome": "COMPLETE_TRACE_SCORED",
                            "focal_user": focal_user,
                            "candidate_key": list(prepared.candidate_key),
                            "source_rule": prepared.source_rule,
                            "reference_trace_sha256": build.reference_trace_sha256,
                            "candidate_trace_sha256": build.candidate_trace_sha256,
                            "forecast_payload_sha256": build.forecast_payload_sha256,
                            "fading_authority_mode": build.authority.fading_mode,
                            "fading_field_receipt": prepared.forecast_rng_state.get(
                                "fading_field_receipt"
                            ),
                            "old_certificate_diagnostic": _certificate_diagnostic(build),
                            "offset_receipts": offset_receipts,
                            "z2_temporal_surplus_bits": z2,
                            "service_guard": service_guard,
                            "elapsed_s": time.perf_counter() - row_started,
                        }
                    )
                except backend.C2ForecastSupportRejection as error:
                    rows.append(
                        {
                            "focal_user": focal_user,
                            **_support_censor(error),
                            "elapsed_s": time.perf_counter() - row_started,
                        }
                    )
                except Exception as error:
                    rows.append(
                        {
                            "outcome": "FORECAST_ERROR_NOT_SCORED",
                            "focal_user": focal_user,
                            "error": f"{type(error).__name__}: {error}",
                            "elapsed_s": time.perf_counter() - row_started,
                        }
                    )
            anchors.append(
                {
                    "step_index": int(observation.step_index),
                    "departure_user_count": len(departures),
                    "scheduled_focal_users": scheduled,
                    "candidates": rows,
                }
            )
            if len(anchors) >= args.max_anchors:
                # Do not take another realised Main step after the final sealed
                # anchor: forecasts remain pre-outcome and no option executes.
                break

        # The only live advance in this probe is the unmodified Main action.
        result = wrapped.step(main_actions, env_rng)
        if result.done:
            break
        states = result.user_states
        masks = result.action_masks
        observation = wrapped.last_outcome.observation

    all_rows = [row for anchor in anchors for row in anchor["candidates"]]
    complete_rows = [row for row in all_rows if row["outcome"] == "COMPLETE_TRACE_SCORED"]
    censored_rows = [
        row
        for row in all_rows
        if row["outcome"] == "RIGHT_CENSORED_SUPPORT_REJECTION"
    ]
    networks_unchanged = smoke._networks_equal(trainer, networks_before)
    replay_after = len(trainer.replay)
    replay_unchanged = replay_after == replay_before
    keyed = args.fading_mode == KEYED_FADING_VERSION
    payload = {
        "schema": (
            "c2-v03-fixed-lambda-keyed-fading-viability-probe-v1"
            if keyed
            else "c2-v03-fixed-lambda-deterministic-plumbing-probe-v1"
        ),
        "status": "PASS" if networks_unchanged and replay_unchanged else "FAIL",
        "claim_ceiling": (
            "DIAGNOSTIC_ONLY_NO_TRAINING_NO_OPTION_EXECUTION_NO_EE_EFFICACY"
        ),
        "fading_mode": args.fading_mode,
        "fading_claim": (
            "CANONICAL_FADING_MATCHED_TRACE_VIABILITY_ONLY; not training or C2 EE efficacy"
            if keyed
            else "DIAGNOSTIC_ONLY; fading-disabled twins do not establish stochastic physical viability or C2 EE efficacy"
        ),
        "live_policy": "Main-only masked-greedy advance; no C2 selection or execution",
        "training_or_replay_write": False,
        "lambda_calibration": {
            **calibration,
            "lambda_hex": multiplier.hex(),
            "calibration_helper": "run_c3_unilateral_oracle_pilot._freeze_lambda",
        },
        "candidate_schedule": {
            "rule": "ascending_departure_user_incumbent_hold_only_no_early_stop",
            "max_candidates_per_anchor": args.max_candidates,
            "max_anchors": args.max_anchors,
            "forecast_offsets": list(EXPECTED_OFFSETS),
        },
        "seed": args.seed,
        "checkpoint_sha256": checkpoint["checkpoint_sha256"],
        "environment_source_sha256": environment_source_sha256,
        "reward_source_sha256": reward_source_sha256,
        "anchors": anchors,
        "summary": {
            "anchors": len(anchors),
            "attempted_candidates": len(all_rows),
            "complete_forecasts_scored": len(complete_rows),
            "support_rejections_right_censored": len(censored_rows),
            "other_forecast_errors": len(all_rows) - len(complete_rows) - len(censored_rows),
            "positive_z2_complete_forecasts": sum(
                float(row["z2_temporal_surplus_bits"]) > 0.0
                for row in complete_rows
            ),
            "service_safe_complete_forecasts": sum(
                bool(row["service_guard"]["passed"])
                for row in complete_rows
            ),
            "positive_z2_service_safe_forecasts": sum(
                bool(row["service_guard"]["passed"])
                and float(row["z2_temporal_surplus_bits"]) > 0.0
                for row in complete_rows
            ),
        },
        "main_networks_bitwise_unchanged": networks_unchanged,
        "main_replay_length_before": replay_before,
        "main_replay_length_after": replay_after,
        "main_replay_unchanged": replay_unchanged,
        "elapsed_s": time.perf_counter() - started,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    frozen_temp.cleanup()
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
