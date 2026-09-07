#!/usr/bin/env python3
"""Independent completeness verifier for one 100EP pilot arm."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import torch


ARMS = ("B000", "F111", "A011", "A101", "A110")
LANES = {
    "F111": {"C1": True, "C2": True, "C3": True},
    "A011": {"C1": False, "C2": True, "C3": True},
    "A101": {"C1": True, "C2": False, "C3": True},
    "A110": {"C1": True, "C2": True, "C3": False},
}
GATES = {
    arm: {
        source: "route" if informed else "shadow"
        for source, informed in lanes.items()
    }
    for arm, lanes in LANES.items()
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json(path: Path, *, label: str, failures: list[str]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        failures.append(f"{label}: unreadable ({type(error).__name__})")
        return None


def _bound_file(
    raw_path: Any,
    raw_sha: Any,
    *,
    expected: Path,
    label: str,
    failures: list[str],
) -> Path | None:
    try:
        observed = Path(str(raw_path)).expanduser().resolve()
    except (OSError, RuntimeError):
        observed = None
    target = Path(expected).expanduser().resolve()
    if observed != target:
        failures.append(f"{label}: path mismatch")
        return None
    if not target.is_file() or target.stat().st_size <= 0:
        failures.append(f"{label}: missing or empty")
        return None
    if raw_sha != sha256_file(target):
        failures.append(f"{label}: hash mismatch")
        return None
    return target


def _load_torch(path: Path, *, label: str, failures: list[str]) -> Mapping[str, Any] | None:
    try:
        value = torch.load(path, map_location="cpu", weights_only=False)
    except Exception as error:
        failures.append(f"{label}: reload failed ({type(error).__name__})")
        return None
    if not isinstance(value, Mapping):
        failures.append(f"{label}: mapping payload required")
        return None
    return value


def _grid(
    rows: Any,
    *,
    episodes: int,
    sources: Sequence[str] | None,
    label: str,
    failures: list[str],
) -> None:
    expected = (
        {(episode, step) for episode in range(episodes) for step in range(10)}
        if sources is None
        else {
            (episode, step, source)
            for episode in range(episodes)
            for step in range(10)
            for source in sources
        }
    )
    if not isinstance(rows, list) or len(rows) != len(expected):
        failures.append(f"{label}: exactly {len(expected)} rows required")
        return
    observed = set()
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            failures.append(f"{label}[{index}]: object required")
            continue
        episode = row.get("episode")
        step = row.get("step")
        source = row.get("source")
        if type(episode) is not int or type(step) is not int:
            failures.append(f"{label}[{index}]: integer episode/step required")
            continue
        if sources is not None and (not isinstance(source, str) or source not in sources):
            failures.append(f"{label}[{index}]: exact source required")
            continue
        key = (episode, step) if sources is None else (episode, step, source)
        if key in observed:
            failures.append(f"{label}[{index}]: duplicate grid cell")
        observed.add(key)
    if observed != expected:
        failures.append(f"{label}: episode-step-source grid mismatch")


def verify_pilot100_arm(
    *,
    status_path: Path,
    arm: str,
    episodes: int,
) -> dict[str, Any]:
    """Verify training receipts, lane identity, and resumable carrier state."""

    root = Path(status_path).expanduser().resolve().parent
    failures: list[str] = []
    artifacts: dict[str, dict[str, Any]] = {}
    status = _json(Path(status_path), label="arm status", failures=failures)
    if arm not in ARMS:
        failures.append("arm: outside pilot")
    if not isinstance(status, Mapping):
        failures.append("arm status: object required")
        result = None
    else:
        result = status.get("result")
        if not isinstance(result, Mapping):
            failures.append("arm status.result: object required")
            result = None

    episode_log_path = root / "episode-logs.json"
    episode_logs = _json(episode_log_path, label="episode logs", failures=failures)
    if not isinstance(episode_logs, list) or len(episode_logs) != episodes:
        failures.append(f"episode logs: exactly {episodes} rows required")
    elif [row.get("episode") for row in episode_logs if isinstance(row, Mapping)] != list(range(episodes)):
        failures.append("episode logs: exact episode sequence required")
    if episode_log_path.is_file():
        artifacts["episode_logs"] = {
            "path": str(episode_log_path),
            "sha256": sha256_file(episode_log_path),
            "rows": len(episode_logs) if isinstance(episode_logs, list) else None,
        }

    if result is not None and arm == "B000":
        if result.get("dispatch") != "unchanged_MODQNTrainer.train":
            failures.append("baseline dispatch identity mismatch")
        training_state = _bound_file(
            result.get("training_state"),
            result.get("training_state_sha256"),
            expected=root / "training-state.pt",
            label="baseline training state",
            failures=failures,
        )
        if training_state is not None:
            payload = _load_torch(
                training_state, label="baseline training state", failures=failures
            )
            if payload is not None and not {
                "q_networks",
                "target_networks",
                "optimizers",
            }.issubset(payload):
                failures.append("baseline training state: core keys missing")
            artifacts["training_state"] = {
                "path": str(training_state),
                "sha256": sha256_file(training_state),
                "load_round_trip": "PASS" if payload is not None else "FAIL",
            }

    if result is not None and arm != "B000":
        expected_lanes = LANES[arm]
        expected_gates = GATES[arm]
        if result.get("lanes_informed") != expected_lanes:
            failures.append("treatment informed-lane mapping mismatch")
        if result.get("gates") != expected_gates:
            failures.append("treatment gate mapping mismatch")
        if result.get("counterfactual_used_for_runtime_admission") is not False:
            failures.append("runtime counterfactual admission must remain false")
        if result.get("role_support_version") != "V0.2_OBSERVABLE_ELIGIBILITY":
            failures.append("treatment role support version mismatch")
        if result.get("specialist_bundle_replay_capacity") != 2000:
            failures.append("specialist bundle replay capacity mismatch")
        if type(result.get("consumed_specialist_bundle_count")) is not int or result.get(
            "consumed_specialist_bundle_count"
        ) < 0:
            failures.append("consumed specialist bundle count invalid")

        receipt_specs = (
            ("main_update", "main-update-receipts.json", None),
            ("role_eligibility", "role-eligibility-receipts.json", ("C2", "C3")),
            ("specialist_replay", "specialist-replay-receipts.json", ("C1", "C2", "C3")),
        )
        for key, filename, sources in receipt_specs:
            path = root / filename
            rows = _json(path, label=key, failures=failures)
            _grid(
                rows,
                episodes=episodes,
                sources=sources,
                label=key,
                failures=failures,
            )
            if isinstance(rows, list) and key == "role_eligibility":
                for index, row in enumerate(rows):
                    if not isinstance(row, Mapping):
                        continue
                    if row.get("support_version") != "V0.2_OBSERVABLE_ELIGIBILITY":
                        failures.append(
                            f"role_eligibility[{index}]: support version mismatch"
                        )
                    if row.get("future_outcome_used_for_admission") is not False:
                        failures.append(
                            f"role_eligibility[{index}]: future outcome admission forbidden"
                        )
            if isinstance(rows, list) and key == "main_update":
                for index, row in enumerate(rows):
                    losses = row.get("losses") if isinstance(row, Mapping) else None
                    if (
                        not isinstance(losses, list)
                        or len(losses) != 3
                        or any(
                            isinstance(value, bool)
                            or not isinstance(value, (int, float))
                            or not math.isfinite(float(value))
                            or float(value) < 0.0
                            for value in losses
                        )
                    ):
                        failures.append(f"main_update[{index}]: three finite losses required")
                    quota = row.get("quota_receipt") if isinstance(row, Mapping) else None
                    if not isinstance(quota, Mapping):
                        failures.append(f"main_update[{index}]: quota receipt missing")
                        continue
                    if quota.get("role_to_objective") != {"C1": 0, "C2": 1, "C3": 2}:
                        failures.append(f"main_update[{index}]: role/objective map mismatch")
                    if quota.get("dose_borrowing") is not False:
                        failures.append(f"main_update[{index}]: dose borrowing forbidden")
                    expected_sources = [
                        source for source, enabled in expected_lanes.items() if enabled
                    ]
                    if quota.get("requested_source_ids") != expected_sources:
                        failures.append(f"main_update[{index}]: requested sources mismatch")
                    if quota.get("runner_resubmits_deferred_bundles") is not False:
                        failures.append(f"main_update[{index}]: deferred resubmission forbidden")
            if path.is_file():
                artifacts[key] = {
                    "path": str(path),
                    "sha256": sha256_file(path),
                    "rows": len(rows) if isinstance(rows, list) else None,
                }

        carrier = _bound_file(
            result.get("carrier_state"),
            result.get("carrier_state_sha256"),
            expected=root / "carrier-state.pt",
            label="carrier state",
            failures=failures,
        )
        if carrier is not None:
            payload = _load_torch(carrier, label="carrier state", failures=failures)
            if payload is not None:
                if payload.get("schema") != "smc-er-carrier-state-v1":
                    failures.append("carrier state schema mismatch")
                if payload.get("episodes_completed") != episodes:
                    failures.append("carrier state episode mismatch")
                if payload.get("gates") != expected_gates:
                    failures.append("carrier state gate mapping mismatch")
                required = {
                    "main_training_state",
                    "specialists",
                    "bundle_replays",
                    "main_consumed_specialist_bundles",
                    "source_rng_states",
                }
                if not required.issubset(payload):
                    failures.append("carrier state resumability keys missing")
            artifacts["carrier_state"] = {
                "path": str(carrier),
                "sha256": sha256_file(carrier),
                "load_round_trip": "PASS" if payload is not None else "FAIL",
            }

        resume = result.get("rolling_resume_state")
        if not isinstance(resume, Mapping) or resume.get("episodes_completed") != episodes:
            failures.append("rolling carrier state episode mismatch")
        else:
            rolling = _bound_file(
                resume.get("path"),
                resume.get("sha256"),
                expected=root / "resume" / "latest-carrier-state.pt",
                label="rolling carrier state",
                failures=failures,
            )
            if rolling is not None:
                payload = _load_torch(
                    rolling, label="rolling carrier state", failures=failures
                )
                if payload is not None and payload.get("episodes_completed") != episodes:
                    failures.append("rolling carrier state payload episode mismatch")
                artifacts["rolling_carrier_state"] = {
                    "path": str(rolling),
                    "sha256": sha256_file(rolling),
                    "load_round_trip": "PASS" if payload is not None else "FAIL",
                }

    return {
        "schema": "multi-catfish-mcrl-pilot100-arm-verification-v1",
        "status": "PASS" if not failures else "FAIL",
        "arm": arm,
        "episodes": episodes,
        "receipt_artifacts": artifacts,
        "failures": failures,
    }


__all__ = ["verify_pilot100_arm"]
