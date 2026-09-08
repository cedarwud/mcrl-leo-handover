#!/usr/bin/env python3
"""Offline same-state shadow replay for a completed C3-S variant matrix.

This diagnostic never participates in the matrix kill rule or progression.  It
replays one already-screened coordinator policy and evaluates BASE once on a
deep copy of each visited pre-decision state.  The copied branch is discarded.
"""

from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Callable, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
V1_DIR = REPO / ".scratch" / "multi-catfish-v023-c3s-screen"
for _import_dir in (HERE, V1_DIR):
    if str(_import_dir) not in sys.path:
        sys.path.insert(0, str(_import_dir))

# Reuse the actual screen modules through ordinary imports so replay follows
# the same policy implementation and import identity.
import c3s_policy as v1policy  # noqa: E402
import run_v023_c3s_screen as v1runner  # noqa: E402
import run_v023_c3s_variants as matrix  # noqa: E402
import variant_policy  # noqa: E402


SCHEMA = "multi-catfish-mcrl-v023-c3s-shadow-replay-v1"
PREFLIGHT_SCHEMA = f"{SCHEMA}-preflight-reference"
AUTHORITY_SCHEMA = f"{SCHEMA}-launch-authority"
UNIT_SCHEMA = f"{SCHEMA}-unit-receipt"
TERMINAL_SCHEMA = f"{SCHEMA}-decomposition"
CLAIM_CEILING = "TRAIN_DEVELOPMENT_C3S_SHADOW_ACCOUNTING_NO_CAUSAL_PROOF_NO_PROGRESSION_NO_TEST"
JSON_NAME = "SHADOW-REPLAY-DECOMPOSITION.json"
MARKDOWN_NAME = "SHADOW-REPLAY-DECOMPOSITION.md"
DEFAULT_OUTPUT = HERE / "shadow-replay-output"
DEFAULT_PREFLIGHT = matrix.DEFAULT_PREFLIGHT

# Contract §Panel fixes the replay to the same 30 decision epochs as the screen.
HORIZON = matrix.HORIZON
# The variant declaration is the sole authority for coordinator-arm names.
# Disabled optional arms are accepted for replay without activating them in the
# default matrix; the archived receipt must still prove the selected arm ran.
DECLARED_OPTIONAL_ARMS = tuple(
    json.loads(matrix.CONFIG_PATH.read_text(encoding="ascii")).get("optional_arms", {})
)
COORDINATOR_ARMS = (*matrix.COORDINATOR_ARMS, *DECLARED_OPTIONAL_ARMS)
# Outside-review §5 budgets exactly one additional physical evaluation/decision.
EXTRA_PHYSICAL_EVALUATIONS_PER_DECISION = 1
ALL_UNITS = matrix.ALL_UNITS


class ShadowReplayError(RuntimeError):
    """A replay input, purity invariant, or exact accounting check failed."""


class MergeWaiting(ShadowReplayError):
    def __init__(self, missing: int) -> None:
        self.missing = missing
        super().__init__(f"{missing} shadow replay units missing")


@dataclass(frozen=True)
class ShadowDecision:
    """One policy decision plus the two nominal same-state evaluations."""

    committed_actions: np.ndarray
    base_actions: np.ndarray
    selected_profile_id: str
    nominal_committed: Mapping[str, object]
    nominal_base: Mapping[str, object]


def canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as error:
        raise ShadowReplayError("artifact is not finite canonical ASCII JSON") from error


def file_sha256(path: Path) -> str:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise ShadowReplayError(f"required regular file is absent or symlinked: {target}")
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _local(path: Path, *, field: str) -> Path:
    target = (Path.cwd() / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    if not target.is_relative_to(HERE.resolve()):
        raise ShadowReplayError(f"{field} must remain inside {HERE}")
    return target


def _validate_sealed(path: Path, *, digest: str, field: str) -> None:
    target = Path(path)
    appended_sidecar = Path(f"{target}.sha256")
    sidecar = appended_sidecar if appended_sidecar.exists() else target.with_suffix(".sha256")
    try:
        valid = (
            not target.is_symlink() and target.is_file()
            and target.stat().st_mode & 0o777 == 0o444
            and not sidecar.is_symlink() and sidecar.is_file()
            and sidecar.stat().st_mode & 0o777 == 0o444
            and sidecar.read_text(encoding="ascii").split() == [digest, target.name]
            and file_sha256(target) == digest
        )
    except (OSError, UnicodeError):
        valid = False
    if not valid:
        raise ShadowReplayError(f"{field} is not sealed mode-0444 with matching sidecar")


def _load_sealed_json(path: Path, *, field: str) -> tuple[dict[str, Any], str]:
    digest = file_sha256(path)
    _validate_sealed(path, digest=digest, field=field)
    try:
        value = json.loads(Path(path).read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ShadowReplayError(f"{field} is not valid ASCII JSON") from error
    if not isinstance(value, dict):
        raise ShadowReplayError(f"{field} must be a JSON object")
    return value, digest


def _write_once(path: Path, content: bytes) -> tuple[Path, str]:
    target = _local(path, field="write-once output")
    # Appending avoids the JSON/Markdown pair colliding on one stem sidecar.
    sidecar = Path(f"{target}.sha256")
    if target.exists() or target.is_symlink() or sidecar.exists() or sidecar.is_symlink():
        raise ShadowReplayError("refusing to overwrite write-once output or sidecar")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    target.chmod(0o444)
    digest = file_sha256(target)
    with sidecar.open("xb") as handle:
        handle.write(f"{digest}  {target.name}\n".encode("ascii"))
        handle.flush()
        os.fsync(handle.fileno())
    sidecar.chmod(0o444)
    _validate_sealed(target, digest=digest, field="published shadow output")
    return target, digest


def fraction_payload(value: Fraction) -> dict[str, str]:
    return v1runner.fraction_payload(value)


def _fraction_payload(value: object, *, field: str) -> Fraction:
    if not isinstance(value, Mapping):
        raise ShadowReplayError(f"{field} exact rational is malformed")
    try:
        result = Fraction(int(value["numerator"]), int(value["denominator"]))
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
        raise ShadowReplayError(f"{field} exact rational is malformed") from error
    return result


def _exact_hex(value: object, *, field: str, positive: bool = False) -> Fraction:
    try:
        parsed = float.fromhex(str(value))
    except (TypeError, ValueError, OverflowError) as error:
        raise ShadowReplayError(f"{field} is not a binary64 hex value") from error
    if not math.isfinite(parsed) or (positive and parsed <= 0.0) or (not positive and parsed < 0.0):
        raise ShadowReplayError(f"{field} is outside its domain")
    return Fraction.from_float(parsed)


def _metric_payload(metric: Mapping[str, object], *, nominal: bool) -> dict[str, object]:
    bits_key = "total_bits" if nominal else "bits_hex"
    energy_key = "total_energy_j" if nominal else "energy_j_hex"
    try:
        bits = float(metric[bits_key]) if nominal else float.fromhex(str(metric[bits_key]))
        energy = float(metric[energy_key]) if nominal else float.fromhex(str(metric[energy_key]))
        served = int(metric["served"])
        opportunities = int(metric["opportunities"])
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        raise ShadowReplayError("physical metric is malformed") from error
    if (
        not math.isfinite(bits) or bits < 0.0 or not math.isfinite(energy) or energy <= 0.0
        or not 0 <= served <= opportunities or opportunities <= 0
    ):
        raise ShadowReplayError("physical metric is outside its domain")
    return {
        "bits_hex": bits.hex(), "energy_j_hex": energy.hex(),
        "served": served, "opportunities": opportunities,
    }


def _score(metric: Mapping[str, object], eta: Fraction) -> Fraction:
    return (
        _exact_hex(metric["bits_hex"], field="bits")
        - eta * _exact_hex(metric["energy_j_hex"], field="energy", positive=True)
    )


def _state_digest(step_env: Any, observation: Any) -> str:
    try:
        native = __import__(
            "mcrl.runtime.ee_axis_state", fromlist=["encode_ee_axis_state"]
        ).encode_ee_axis_state(step_env, observation)
        return str(native.state_sha256)
    except (AttributeError, TypeError, ValueError) as error:
        raise ShadowReplayError("pre-decision state cannot be authenticated") from error


def shadow_evaluate_without_commit(
    step_env: Any, actions: np.ndarray, rng: np.random.Generator, *,
    interval_s: float, expected_users: int,
) -> tuple[dict[str, object], str]:
    """Evaluate on a detached clone and prove the live environment/RNG unchanged."""

    if not isinstance(rng, np.random.Generator):
        raise ShadowReplayError("shadow evaluation RNG must be numpy.random.Generator")
    before = v1policy._structural_sha256((step_env, rng))
    detached_environment = copy.deepcopy(step_env)
    detached_rng = copy.deepcopy(rng)
    outcome = detached_environment.step(np.asarray(actions, dtype=np.int64), detached_rng)
    metric = _outcome_metric(outcome, interval_s=interval_s, expected_users=expected_users)
    after = v1policy._structural_sha256((step_env, rng))
    if after != before:
        raise ShadowReplayError("shadow BASE evaluation mutated live environment or RNG")
    return metric, before


def _outcome_metric(outcome: Any, *, interval_s: float, expected_users: int) -> dict[str, object]:
    try:
        rates = np.asarray(outcome.link_rate_bps, dtype=np.float64)
        power = float(outcome.system_power_w)
        served = int(outcome.resolution.served_count)
    except (AttributeError, TypeError, ValueError) as error:
        raise ShadowReplayError("outcome lacks physical endpoint metrics") from error
    if (
        rates.shape != (expected_users,) or not np.all(np.isfinite(rates)) or np.any(rates < 0.0)
        or not math.isfinite(power) or power <= 0.0 or not 0 <= served <= expected_users
        or not math.isfinite(interval_s) or interval_s <= 0.0
    ):
        raise ShadowReplayError("outcome physical endpoint metric is invalid")
    bits = interval_s * math.fsum(float(value) for value in rates)
    energy = interval_s * power
    return {
        "bits_hex": bits.hex(), "energy_j_hex": energy.hex(),
        "served": served, "opportunities": expected_users,
    }


def run_shadow_trajectory(
    *, environment: Any, env_rng: np.random.Generator,
    mobility_rng: np.random.Generator, horizon: int,
    decide: Callable[[Any, Any, np.random.Generator], ShadowDecision],
    expected_users: int = matrix.USERS,
    digest_state: Callable[[Any, Any], str] = _state_digest,
) -> dict[str, object]:
    """Synthetic-test seam and production replay loop."""

    _states, _masks, observation = environment.reset(env_rng, mobility_rng)
    step_env = environment.environment
    initial_state_sha256 = digest_state(step_env, observation)
    interval_s = float(step_env.driver.config.ephemeris.time_step_s)
    records: list[dict[str, object]] = []
    committed_steps: list[dict[str, object]] = []
    action_trace = hashlib.sha256()
    for step_index in range(horizon):
        if int(observation.step_index) != step_index:
            raise ShadowReplayError("replay reached the wrong decision index")
        predecision_sha256 = digest_state(step_env, observation)
        decision = decide(step_env, observation, env_rng)
        committed = np.asarray(decision.committed_actions)
        base = np.asarray(decision.base_actions)
        if (
            committed.dtype.kind not in "iu" or base.dtype.kind not in "iu"
            or committed.shape != (expected_users,) or base.shape != (expected_users,)
        ):
            raise ShadowReplayError("replay decision action vectors are malformed")
        masks = np.asarray(observation.masks)
        if masks.dtype != np.bool_ or masks.ndim != 2 or masks.shape[0] != expected_users:
            raise ShadowReplayError("replay action mask is malformed")
        rows = np.arange(expected_users)
        for label, actions in (("committed", committed), ("BASE", base)):
            eligible = np.any(masks, axis=1)
            valid = (
                not np.any(actions[eligible] < 0)
                and not np.any(actions[eligible] >= masks.shape[1])
                and not np.any(~masks[rows[eligible], actions[eligible]])
                and not np.any(actions[~eligible] != v1runner.f1.NO_OP_ACTION)
            )
            if not valid:
                raise ShadowReplayError(f"{label} action vector is illegal")
        shadow_metric, live_digest = shadow_evaluate_without_commit(
            step_env, base, env_rng, interval_s=interval_s, expected_users=expected_users,
        )
        selected = committed.astype(np.int64, copy=True)
        action_trace.update(selected.tobytes(order="C"))
        result = environment.step(selected, env_rng)
        outcome = environment.last_outcome
        committed_metric = _outcome_metric(
            outcome, interval_s=interval_s, expected_users=expected_users,
        )
        committed_steps.append({"step_index": step_index, **committed_metric})
        records.append({
            "step_index": step_index,
            "predecision_state_sha256": predecision_sha256,
            "live_environment_rng_sha256_before_shadow": live_digest,
            "live_environment_rng_sha256_after_shadow": live_digest,
            "shadow_state_unchanged": True,
            "selected_profile_id": decision.selected_profile_id,
            "base_actions": [int(value) for value in base.tolist()],
            "committed_actions": [int(value) for value in committed.tolist()],
            "configuration_equals_base": bool(np.array_equal(committed, base)),
            "nominal": {
                "committed": _metric_payload(decision.nominal_committed, nominal=True),
                "base_same_state": _metric_payload(decision.nominal_base, nominal=True),
            },
            "realised": {
                "committed": committed_metric,
                "base_same_state_shadow": shadow_metric,
            },
        })
        done = bool(getattr(outcome, "done", getattr(result, "done", False)))
        if step_index < horizon - 1 and done:
            raise ShadowReplayError("replay ended before its declared horizon")
        if step_index == horizon - 1 and not done:
            raise ShadowReplayError("replay did not end at its declared horizon")
        observation = outcome.observation
    return {
        "initial_state_sha256": initial_state_sha256,
        "action_trace_sha256": action_trace.hexdigest(),
        "steps": committed_steps,
        "shadow_decisions": records,
    }


def assert_initial_state_matches(
    replay_initial_sha256: str, screen_receipt: Mapping[str, object], *, arm: str,
) -> None:
    try:
        archived = str(screen_receipt["arms"][arm]["initial_state_sha256"])  # type: ignore[index]
    except (KeyError, TypeError) as error:
        raise ShadowReplayError("screen unit lacks the chosen arm initial-state digest") from error
    if replay_initial_sha256 != archived:
        raise ShadowReplayError("replay initial_state_sha256 mismatches archived screen unit")


def assert_bit_identical_replay(
    replay: Mapping[str, object], screen_receipt: Mapping[str, object], *, arm: str,
) -> None:
    """Ignore timings, but require identical initial state, actions, and endpoints."""

    assert_initial_state_matches(str(replay.get("initial_state_sha256")), screen_receipt, arm=arm)
    try:
        archived = screen_receipt["arms"][arm]  # type: ignore[index]
        archived_trace = str(archived["action_trace_sha256"])
        archived_steps = archived["steps"]
    except (KeyError, TypeError) as error:
        raise ShadowReplayError("screen unit lacks the chosen arm trajectory") from error
    if replay.get("action_trace_sha256") != archived_trace:
        raise ShadowReplayError("replay action trace is not bit-identical to the screen")
    if replay.get("steps") != archived_steps:
        raise ShadowReplayError("replay physical endpoints are not bit-identical to the screen")


def decomposition(
    *, committed: Sequence[Mapping[str, object]],
    same_state_base: Sequence[Mapping[str, object]],
    trajectory_base: Sequence[Mapping[str, object]], eta: Fraction,
) -> dict[str, object]:
    """Return the exact telescoping (a)+(b)=total accounting identity."""

    if not committed or not (
        len(committed) == len(same_state_base) == len(trajectory_base)
    ):
        raise ShadowReplayError("decomposition trajectories have unequal or empty coverage")
    committed_score = sum((_score(row, eta) for row in committed), Fraction(0))
    same_state_score = sum((_score(row, eta) for row in same_state_base), Fraction(0))
    trajectory_score = sum((_score(row, eta) for row in trajectory_base), Fraction(0))
    immediate = committed_score - same_state_score
    remainder = same_state_score - trajectory_score
    total = committed_score - trajectory_score
    if immediate + remainder != total:
        raise ShadowReplayError("exact shadow decomposition identity failed")
    return {
        "eta": fraction_payload(eta),
        "a_immediate_same_state": fraction_payload(immediate),
        "b_visited_state_remainder": fraction_payload(remainder),
        "total_arm_minus_base_trajectory": fraction_payload(total),
        "identity_exact": True,
    }


def _terminal_path(screen_root: Path) -> Path:
    direct = Path(screen_root) / "terminal-receipt.json"
    nested = Path(screen_root) / "terminal" / "terminal-receipt.json"
    if direct.is_file() and not direct.is_symlink():
        return direct
    if nested.is_file() and not nested.is_symlink():
        return nested
    raise ShadowReplayError("screen run lacks a terminal receipt")


def load_completed_no_support_screen(screen_root: Path) -> tuple[dict[str, Any], dict[str, str]]:
    path = _terminal_path(screen_root).resolve()
    receipt, digest = _load_sealed_json(path, field="completed screen terminal receipt")
    if (
        receipt.get("schema") != matrix.TERMINAL_SCHEMA
        or receipt.get("status") != "COMPLETE"
        or receipt.get("outcome") != "C3S_VARIANT_MATRIX_COMPLETE"
        or receipt.get("integrity") is not True
    ):
        raise ShadowReplayError("screen terminal receipt is not a valid completed matrix")
    panel_arms = receipt.get("panel", {}).get("arms")  # type: ignore[union-attr]
    allowed_panels = {
        tuple(matrix.active_arms()),
        tuple(matrix.active_arms(enable_ve=True)),
    }
    if not isinstance(panel_arms, list) or tuple(panel_arms) not in allowed_panels:
        raise ShadowReplayError("completed screen panel arm declaration is malformed")
    recorded_coordinators = tuple(panel_arms[1:])
    decisions = receipt.get("pooled", {}).get("decisions")  # type: ignore[union-attr]
    if (
        not isinstance(decisions, Mapping)
        or set(decisions) != set(recorded_coordinators)
    ):
        raise ShadowReplayError("completed screen lacks coordinator dispositions")
    if any(row.get("outcome") != "NO_SUPPORT" for row in decisions.values() if isinstance(row, Mapping)):
        raise ShadowReplayError("shadow replay is permitted only after every coordinator is NO_SUPPORT")
    if any(not isinstance(row, Mapping) for row in decisions.values()):
        raise ShadowReplayError("completed screen coordinator disposition is malformed")
    return receipt, {"path": str(path), "sha256": digest}


def _screen_unit_path(screen_root: Path, key: Any) -> Path:
    return Path(screen_root) / "units" / key.slug / "receipt.json"


def load_screen_unit(screen_root: Path, key: Any) -> tuple[dict[str, Any], dict[str, str]]:
    path = _screen_unit_path(screen_root, key).resolve()
    receipt, digest = _load_sealed_json(path, field=f"screen unit {key.slug}")
    if (
        receipt.get("schema") != matrix.UNIT_SCHEMA
        or receipt.get("status") != "COMPLETE"
        or receipt.get("outcome") != "C3S_VARIANT_MATRIX_UNIT_COMPLETE"
        or receipt.get("unit") != key.as_dict()
        or receipt.get("integrity") is not True
    ):
        raise ShadowReplayError(f"screen unit {key.slug} is invalid")
    return receipt, {"path": str(path), "sha256": digest}


def assert_screen_unit_is_terminal_bound(
    terminal: Mapping[str, object], key: Any, unit_binding: Mapping[str, str],
) -> None:
    """Require the replay input unit to be the one authenticated by the merge."""

    bindings = terminal.get("unit_receipts")
    if not isinstance(bindings, list):
        raise ShadowReplayError("screen terminal lacks unit receipt bindings")
    matches = [
        row for row in bindings
        if isinstance(row, Mapping) and row.get("unit") == key.as_dict()
    ]
    if len(matches) != 1:
        raise ShadowReplayError("screen terminal does not bind exactly one matching unit")
    bound = matches[0]
    try:
        same_path = Path(str(bound["path"])).resolve() == Path(unit_binding["path"]).resolve()
        same_digest = str(bound["sha256"]) == unit_binding["sha256"]
    except (KeyError, TypeError, OSError) as error:
        raise ShadowReplayError("screen terminal unit binding is malformed") from error
    if not same_path or not same_digest:
        raise ShadowReplayError("screen unit path/digest disagrees with the terminal receipt")


def _production_decider(adapter: Any) -> Callable[[Any, Any, np.random.Generator], ShadowDecision]:
    def decide(step_env: Any, observation: Any, rng: np.random.Generator) -> ShadowDecision:
        # The adapter call is the exact matrix policy path.  The additional pure
        # snapshot only records BASE and nominal endpoints for this diagnostic.
        snapshot, evaluator = v1policy._snapshot_inputs(adapter, step_env, observation)
        actions = np.asarray(adapter.select_actions(step_env, observation, rng), dtype=np.int64)
        base = np.asarray(snapshot.base_actions, dtype=np.int64)
        committed_eval = evaluator.evaluate(actions)
        base_eval = evaluator.evaluate(base)
        committed_metric = matrix._metric_from_outcome(committed_eval, snapshot.interval_s)
        base_metric = matrix._metric_from_outcome(base_eval, snapshot.interval_s)
        return ShadowDecision(
            committed_actions=actions, base_actions=base,
            selected_profile_id=str(adapter.decision_records[-1]["selected_profile_id"]),
            nominal_committed=committed_metric, nominal_base=base_metric,
        )
    return decide


def execute_physical_unit(
    key: Any, *, arm: str, horizon: int, screen_run: Path,
) -> dict[str, object]:
    """Re-run one screened trajectory, with one discarded BASE branch per step."""

    from mcrl.env.keyed_fading import KeyedFadingField
    from mcrl.runtime.prereg import read_prereg
    from mcrl.runtime.training_pipeline import _evaluation_rngs

    key.verify()
    if arm not in COORDINATOR_ARMS:
        raise ShadowReplayError("--arm is not a declared coordinator arm")
    if horizon != HORIZON:
        raise ShadowReplayError("shadow replay horizon differs from the screened horizon")
    terminal, terminal_binding = load_completed_no_support_screen(screen_run)
    screen_unit, unit_binding = load_screen_unit(screen_run, key)
    assert_screen_unit_is_terminal_bound(terminal, key, unit_binding)
    record = read_prereg(v1runner.f1.PREREG_PATH)
    if record.digest != v1runner.f1.PREREG_RECORD_DIGEST:
        raise ShadowReplayError("TRAIN PREREG semantic digest changed")
    physical, server = v1runner.f1._runtime_modules()
    frozen = v1runner.f2._load_frozen_heads(key.lineage)
    q_before = (physical._parameter_sha256(frozen.q1), physical._parameter_sha256(frozen.q2))
    with tempfile.TemporaryDirectory(prefix=f"c3s-shadow-{key.slug}-", dir=os.environ.get("TMPDIR")) as temporary:
        archive = server._freeze_archive(
            record, v1runner.CANONICAL_TLE_ROOT, Path(temporary) / "frozen", physical,
        )
        environment = v1runner._make_environment(archive, horizon=horizon)
        environment.environment._fading_field = KeyedFadingField.from_components(
            v1runner.FIELD_COMPONENT, key.world,
        )
        rngs = tuple(_evaluation_rngs(key.world))
        if len(rngs) < 2:
            raise ShadowReplayError("canonical RNG factory lacks two streams")
        adapter = variant_policy.VariantPolicyAdapter(
            physical=physical, frozen=frozen, arm=arm,
        )
        trajectory = run_shadow_trajectory(
            environment=environment, env_rng=rngs[0], mobility_rng=rngs[1],
            horizon=horizon, decide=_production_decider(adapter),
        )
    if q_before != (physical._parameter_sha256(frozen.q1), physical._parameter_sha256(frozen.q2)):
        raise ShadowReplayError("authenticated Q1/Q2 parameters changed during replay")
    assert_bit_identical_replay(trajectory, screen_unit, arm=arm)
    archived_base = screen_unit.get("arms", {}).get("BASE")  # type: ignore[union-attr]
    if not isinstance(archived_base, Mapping) or not isinstance(archived_base.get("steps"), list):
        raise ShadowReplayError("screen unit lacks its archived BASE trajectory")
    return {
        "schema": UNIT_SCHEMA, "status": "COMPLETE",
        "outcome": "C3S_SHADOW_REPLAY_UNIT_COMPLETE",
        "claim_ceiling": CLAIM_CEILING, "unit": key.as_dict(),
        "arm": arm, "horizon": horizon, "users": matrix.USERS,
        "screen_terminal": terminal_binding, "screen_unit": unit_binding,
        "trajectory": trajectory,
        "archived_base_steps": archived_base["steps"],
        "diagnostic_only": True, "progression_eligible": False,
        "counterfactual_branch_committed": False, "test_split_opened": False,
        "episode_training": False, "learner_update": False, "efficacy_claim": False,
    }


def _steps_for(receipts: Sequence[Mapping[str, object]], field: str) -> list[Mapping[str, object]]:
    rows: list[Mapping[str, object]] = []
    for receipt in receipts:
        if field == "committed":
            values = receipt["trajectory"]["steps"]  # type: ignore[index]
        elif field == "same_state_base":
            values = [row["realised"]["base_same_state_shadow"] for row in receipt["trajectory"]["shadow_decisions"]]  # type: ignore[index]
        elif field == "nominal_committed":
            values = [row["nominal"]["committed"] for row in receipt["trajectory"]["shadow_decisions"]]  # type: ignore[index]
        elif field == "nominal_base":
            values = [row["nominal"]["base_same_state"] for row in receipt["trajectory"]["shadow_decisions"]]  # type: ignore[index]
        else:
            values = receipt["archived_base_steps"]  # type: ignore[index]
        if not isinstance(values, list) or any(not isinstance(value, Mapping) for value in values):
            raise ShadowReplayError(f"unit {field} trajectory is malformed")
        rows.extend(values)
    return rows


def _paired_gain(
    committed: Sequence[Mapping[str, object]], base: Sequence[Mapping[str, object]], eta: Fraction,
) -> Fraction:
    if len(committed) != len(base):
        raise ShadowReplayError("paired gain coverage differs")
    return sum((_score(left, eta) - _score(right, eta) for left, right in zip(committed, base, strict=True)), Fraction(0))


def _physical_summary(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    if not rows:
        raise ShadowReplayError("physical summary has no rows")
    bits = sum((_exact_hex(row["bits_hex"], field="bits") for row in rows), Fraction(0))
    energy = sum(
        (_exact_hex(row["energy_j_hex"], field="energy", positive=True) for row in rows),
        Fraction(0),
    )
    try:
        served = sum(int(row["served"]) for row in rows)
        opportunities = sum(int(row["opportunities"]) for row in rows)
    except (KeyError, TypeError, ValueError) as error:
        raise ShadowReplayError("physical service summary is malformed") from error
    if energy <= 0 or opportunities <= 0 or not 0 <= served <= opportunities:
        raise ShadowReplayError("physical summary denominator is invalid")
    return {
        "total_bits": fraction_payload(bits),
        "total_energy_j": fraction_payload(energy),
        "eta": fraction_payload(bits / energy),
        "served": served, "opportunities": opportunities,
        "service": fraction_payload(Fraction(served, opportunities)),
    }


def _group_summary(receipts: Sequence[Mapping[str, object]], *, eta_base: Fraction, eta_ref: Fraction) -> dict[str, object]:
    committed = _steps_for(receipts, "committed")
    same_state = _steps_for(receipts, "same_state_base")
    trajectory_base = _steps_for(receipts, "trajectory_base")
    nominal_committed = _steps_for(receipts, "nominal_committed")
    nominal_base = _steps_for(receipts, "nominal_base")
    realised_gain_ref = _paired_gain(committed, same_state, eta_ref)
    nominal_gain_ref = _paired_gain(nominal_committed, nominal_base, eta_ref)
    at_screen_eta = decomposition(
        committed=committed, same_state_base=same_state,
        trajectory_base=trajectory_base, eta=eta_base,
    )
    at_eta_ref = decomposition(
        committed=committed, same_state_base=same_state,
        trajectory_base=trajectory_base, eta=eta_ref,
    )
    immediate_screen_eta = _fraction_payload(
        at_screen_eta["a_immediate_same_state"], field="screen-eta immediate benefit",
    )
    immediate_eta_ref = _fraction_payload(
        at_eta_ref["a_immediate_same_state"], field="eta_ref immediate benefit",
    )
    equal = sum(
        bool(row["configuration_equals_base"])
        for receipt in receipts for row in receipt["trajectory"]["shadow_decisions"]  # type: ignore[index]
    )
    return {
        "units": len(receipts), "decisions": len(committed),
        "configuration_equals_base_count": equal,
        "physical_totals": {
            "committed_arm": _physical_summary(committed),
            "base_same_visited_states": _physical_summary(same_state),
            "base_own_trajectory": _physical_summary(trajectory_base),
        },
        "at_screen_eta_base": at_screen_eta,
        "at_eta_ref": at_eta_ref,
        "nominal_vs_realised_at_eta_ref": {
            "nominal_paired_gain": fraction_payload(nominal_gain_ref),
            "realised_paired_gain": fraction_payload(realised_gain_ref),
            "nominal_minus_realised": fraction_payload(nominal_gain_ref - realised_gain_ref),
        },
        "price_mismatch_separated_from_model_gap": {
            "realised_immediate_screen_eta_minus_eta_ref": fraction_payload(
                immediate_screen_eta - immediate_eta_ref
            ),
            "nominal_minus_realised_at_eta_ref": fraction_payload(
                nominal_gain_ref - realised_gain_ref
            ),
        },
    }


def _cumulative_curves(
    receipts: Sequence[Mapping[str, object]], *, eta_base: Fraction, eta_ref: Fraction,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for stop in range(1, HORIZON + 1):
        committed: list[Mapping[str, object]] = []
        same_state: list[Mapping[str, object]] = []
        trajectory_base: list[Mapping[str, object]] = []
        nominal_committed: list[Mapping[str, object]] = []
        nominal_base: list[Mapping[str, object]] = []
        for receipt in receipts:
            decisions = receipt["trajectory"]["shadow_decisions"][:stop]  # type: ignore[index]
            committed.extend(receipt["trajectory"]["steps"][:stop])  # type: ignore[index]
            trajectory_base.extend(receipt["archived_base_steps"][:stop])  # type: ignore[index]
            same_state.extend(row["realised"]["base_same_state_shadow"] for row in decisions)
            nominal_committed.extend(row["nominal"]["committed"] for row in decisions)
            nominal_base.extend(row["nominal"]["base_same_state"] for row in decisions)
        rows.append({
            "through_step_index": stop - 1,
            "physical_totals": {
                "committed_arm": _physical_summary(committed),
                "base_same_visited_states": _physical_summary(same_state),
                "base_own_trajectory": _physical_summary(trajectory_base),
            },
            "at_screen_eta_base": decomposition(
                committed=committed, same_state_base=same_state,
                trajectory_base=trajectory_base, eta=eta_base,
            ),
            "nominal_paired_gain_at_eta_ref": fraction_payload(
                _paired_gain(nominal_committed, nominal_base, eta_ref)
            ),
            "realised_paired_gain_at_eta_ref": fraction_payload(
                _paired_gain(committed, same_state, eta_ref)
            ),
        })
    return rows


def pool_replays(
    receipts: Sequence[Mapping[str, object]], *, screen_terminal: Mapping[str, object],
    screen_terminal_binding: Mapping[str, str], arm: str,
) -> dict[str, object]:
    if len(receipts) != len(ALL_UNITS):
        raise ShadowReplayError("decomposition requires all 12 declared units")
    if any(receipt.get("arm") != arm for receipt in receipts):
        raise ShadowReplayError("shadow unit arm coverage is inconsistent")
    try:
        eta_base = _fraction_payload(
            screen_terminal["pooled"]["arms"]["BASE"]["eta"], field="screen eta_BASE",  # type: ignore[index]
        )
    except (KeyError, TypeError) as error:
        raise ShadowReplayError("screen terminal lacks pooled eta_BASE") from error
    eta_ref = v1policy.load_eta_ref()
    all_base = _steps_for(receipts, "trajectory_base")
    base_summary = _physical_summary(all_base)
    try:
        terminal_base = screen_terminal["pooled"]["arms"]["BASE"]  # type: ignore[index]
        totals_match = (
            _fraction_payload(base_summary["total_bits"], field="unit BASE bits")
            == _fraction_payload(terminal_base["total_bits"], field="terminal BASE bits")
            and _fraction_payload(base_summary["total_energy_j"], field="unit BASE energy")
            == _fraction_payload(terminal_base["total_energy_j"], field="terminal BASE energy")
            and int(base_summary["served"]) == int(terminal_base["served"])
            and int(base_summary["opportunities"]) == int(terminal_base["opportunities"])
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ShadowReplayError("screen terminal BASE totals are malformed") from error
    if not totals_match or _fraction_payload(base_summary["eta"], field="unit BASE eta") != eta_base:
        raise ShadowReplayError("archived unit BASE totals disagree with terminal BASE totals")
    worlds = {
        str(world): _group_summary(
            [row for row in receipts if row["unit"]["world"] == world],  # type: ignore[index]
            eta_base=eta_base, eta_ref=eta_ref,
        )
        for world in matrix.WORLDS
    }
    lineages = {
        str(lineage): _group_summary(
            [row for row in receipts if row["unit"]["lineage"] == lineage],  # type: ignore[index]
            eta_base=eta_base, eta_ref=eta_ref,
        )
        for lineage in matrix.LINEAGES
    }
    return {
        "schema": TERMINAL_SCHEMA, "status": "COMPLETE",
        "outcome": "C3S_SHADOW_ACCOUNTING_COMPLETE",
        "claim_ceiling": CLAIM_CEILING, "arm": arm,
        "screen_terminal": dict(screen_terminal_binding),
        "eta_base_source": "COMPLETED_SCREEN_POOLED_BASE_READ_ONLY_OFFLINE",
        "eta_ref": fraction_payload(eta_ref),
        "pooled": _group_summary(receipts, eta_base=eta_base, eta_ref=eta_ref),
        "per_world": worlds, "per_lineage": lineages,
        "cumulative_curves": _cumulative_curves(
            receipts, eta_base=eta_base, eta_ref=eta_ref,
        ),
        "interpretation": (
            "Accounting decomposition only; not a causal proof, rescue rerun, "
            "scientific gate, or input to progression."
        ),
        "diagnostic_only": True, "progression_eligible": False,
        "counterfactual_branch_committed": False, "test_split_opened": False,
        "episode_training": False, "learner_update": False, "efficacy_claim": False,
    }


def _markdown(payload: Mapping[str, object]) -> str:
    pooled = payload["pooled"]
    at_base = pooled["at_screen_eta_base"]  # type: ignore[index]
    at_ref = pooled["nominal_vs_realised_at_eta_ref"]  # type: ignore[index]
    separated = pooled["price_mismatch_separated_from_model_gap"]  # type: ignore[index]
    def value(row: Mapping[str, object]) -> str:
        return f"{row['numerator']}/{row['denominator']}"

    lines = [
        "# C3-S same-state shadow replay decomposition",
        "",
        f"Arm: `{payload['arm']}`. Units: {pooled['units']}. Decisions: {pooled['decisions']}.",  # type: ignore[index]
        f"Screen terminal SHA-256: `{payload['screen_terminal']['sha256']}`.",  # type: ignore[index]
        "",
        "This is an accounting decomposition only. It is not a causal proof, a rescue rerun, "
        "a scientific gate, or an input to progression. Every counterfactual BASE branch was discarded.",
        "",
        "## Exact pooled decomposition at completed-screen eta_BASE",
        "",
        f"- (a) immediate same-state benefit: `{value(at_base['a_immediate_same_state'])}`",
        f"- (b) visited-state remainder: `{value(at_base['b_visited_state_remainder'])}`",
        f"- total arm-minus-BASE trajectory: `{value(at_base['total_arm_minus_base_trajectory'])}`",
        f"- exact identity: `{at_base['identity_exact']}`",
        "",
        "## Nominal versus realised paired gain at frozen eta_ref",
        "",
        f"- nominal: `{value(at_ref['nominal_paired_gain'])}`",
        f"- realised: `{value(at_ref['realised_paired_gain'])}`",
        f"- nominal minus realised: `{value(at_ref['nominal_minus_realised'])}`",
        f"- realised price mismatch, eta_BASE minus eta_ref: "
        f"`{value(separated['realised_immediate_screen_eta_minus_eta_ref'])}`",
        f"- model gap at eta_ref, nominal minus realised: "
        f"`{value(separated['nominal_minus_realised_at_eta_ref'])}`",
        "",
        "The realised price-mismatch term is kept separate from the nominal-minus-realised model gap.",
        "",
        f"Committed configuration equalled BASE at {pooled['configuration_equals_base_count']} decisions.",  # type: ignore[index]
        "",
        "## Pooled physical totals",
        "",
    ]
    lines.extend([
        "| trajectory | bits | joules | EE | service |",
        "|---|---:|---:|---:|---:|",
    ])
    for label, row in pooled["physical_totals"].items():  # type: ignore[index,union-attr]
        lines.append(
            f"| {label} | {value(row['total_bits'])} | {value(row['total_energy_j'])} "
            f"| {value(row['eta'])} | {value(row['service'])} |"
        )
    for heading, key in (("Per-world", "per_world"), ("Per-lineage", "per_lineage")):
        lines.extend([
            "", f"## {heading} exact accounting", "",
            "| group | (a) immediate | (b) remainder | total | nominal gain @ eta_ref | realised gain @ eta_ref | equals BASE |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ])
        for group, summary in payload[key].items():  # type: ignore[index,union-attr]
            decomp = summary["at_screen_eta_base"]
            gains = summary["nominal_vs_realised_at_eta_ref"]
            lines.append(
                f"| {group} | {value(decomp['a_immediate_same_state'])} "
                f"| {value(decomp['b_visited_state_remainder'])} "
                f"| {value(decomp['total_arm_minus_base_trajectory'])} "
                f"| {value(gains['nominal_paired_gain'])} "
                f"| {value(gains['realised_paired_gain'])} "
                f"| {summary['configuration_equals_base_count']} |"
            )
    lines.extend([
        "", "## Cumulative exact curves", "",
        "| through step | (a) immediate | (b) remainder | total | nominal gain @ eta_ref | realised gain @ eta_ref |",
        "|---:|---:|---:|---:|---:|---:|",
    ])
    for row in payload["cumulative_curves"]:  # type: ignore[index]
        decomp = row["at_screen_eta_base"]
        lines.append(
            f"| {row['through_step_index']} | {value(decomp['a_immediate_same_state'])} "
            f"| {value(decomp['b_visited_state_remainder'])} "
            f"| {value(decomp['total_arm_minus_base_trajectory'])} "
            f"| {value(row['nominal_paired_gain_at_eta_ref'])} "
            f"| {value(row['realised_paired_gain_at_eta_ref'])} |"
        )
    lines.extend([
        "",
        "All values above are exact fractions. The companion JSON also contains exact binary64 projections and physical totals at every cumulative point.",
        "",
    ])
    return "\n".join(lines)


def validate_preflight(path: Path) -> dict[str, str]:
    payload, digest = _load_sealed_json(Path(path).resolve(), field="preflight manifest")
    if (
        payload.get("schema") != matrix.PREFLIGHT_SCHEMA
        or payload.get("status") != "FROZEN_PREFLIGHT"
    ):
        raise ShadowReplayError("preflight is not the sealed matrix preflight")
    return {"path": str(Path(path).resolve()), "sha256": digest}


def _code_bindings() -> list[dict[str, str]]:
    paths = (
        Path(__file__).resolve(), HERE / "build_shadow_launch_authority.py",
        HERE / "variant_policy.py", HERE / "variants_config.json",
        HERE / "run_v023_c3s_variants.py", V1_DIR / "c3s_policy.py",
        V1_DIR / "run_v023_c3s_screen.py",
    )
    return [{"path": str(path), "sha256": file_sha256(path)} for path in paths]


def authority_common_binding(authority: Mapping[str, object]) -> dict[str, object]:
    return {
        key: authority.get(key)
        for key in (
            "claim_ceiling", "preflight_manifest", "screen_terminal", "code_files",
            "arm", "horizon", "output_root", "diagnostic_only", "progression_eligible",
        )
    }


def build_launch_authority(
    *, preflight_manifest: Path, screen_run: Path, output: Path, arm: str,
    horizon: int, execution: Mapping[str, object], launch_arguments: Sequence[str],
) -> dict[str, object]:
    if arm not in COORDINATOR_ARMS or horizon != HORIZON:
        raise ShadowReplayError("launch authority arm/horizon is outside the declaration")
    preflight = validate_preflight(preflight_manifest)
    _terminal, screen_binding = load_completed_no_support_screen(screen_run)
    return {
        "schema": AUTHORITY_SCHEMA, "status": "FROZEN_LAUNCH_AUTHORITY",
        "claim_ceiling": CLAIM_CEILING, "preflight_manifest": preflight,
        "screen_terminal": screen_binding, "code_files": _code_bindings(),
        "arm": arm, "horizon": horizon,
        "output_root": str(_local(output, field="output root")),
        "execution": dict(execution), "launch_arguments": list(launch_arguments),
        "diagnostic_only": True, "progression_eligible": False,
        "counterfactual_branch_committed": False,
    }


def validate_launch_authority(
    path: Path, *, preflight_manifest: Path, screen_run: Path, output: Path,
    arm: str, horizon: int, execution: Mapping[str, object],
    launch_arguments: Sequence[str],
) -> tuple[dict[str, Any], str]:
    authority, digest = _load_sealed_json(Path(path).resolve(), field="shadow launch authority")
    expected = build_launch_authority(
        preflight_manifest=preflight_manifest, screen_run=screen_run, output=output,
        arm=arm, horizon=horizon, execution=execution,
        launch_arguments=launch_arguments,
    )
    if authority != expected:
        raise ShadowReplayError("shadow launch authority does not bind this exact invocation")
    return authority, digest


def _unit_path(output: Path, key: Any) -> Path:
    return Path(output) / "units" / key.slug / "shadow-replay-receipt.json"


def execute_unit(
    *, key: Any, output: Path, screen_run: Path, arm: str,
    authority: Mapping[str, object], authority_sha256: str, authority_path: Path,
) -> Path:
    target = _unit_path(_local(output, field="output root"), key)
    if target.exists() or target.is_symlink():
        raise ShadowReplayError("refusing to overwrite a shadow replay unit")
    payload = execute_physical_unit(key, arm=arm, horizon=HORIZON, screen_run=screen_run)
    payload.update({
        "launch_authority_sha256": authority_sha256,
        "launch_authority": {
            "path": str(Path(authority_path).resolve()), "sha256": authority_sha256,
        },
        "producer_common_binding": authority_common_binding(authority),
    })
    return _write_once(target, canonical_bytes(payload) + b"\n")[0]


def execute_merge(
    *, output: Path, screen_run: Path, arm: str,
    authority: Mapping[str, object], authority_sha256: str,
) -> Path:
    root = _local(output, field="output root")
    terminal, terminal_binding = load_completed_no_support_screen(screen_run)
    receipts: list[dict[str, Any]] = []
    unit_bindings: list[dict[str, object]] = []
    for key in ALL_UNITS:
        path = _unit_path(root, key)
        if not path.exists():
            continue
        receipt, digest = _load_sealed_json(path, field=f"shadow unit {key.slug}")
        producer = receipt.get("launch_authority")
        if not isinstance(producer, Mapping) or set(producer) != {"path", "sha256"}:
            raise ShadowReplayError(f"shadow unit {key.slug} lacks producer authority")
        producer_path = Path(str(producer["path"])).resolve()
        producer_authority, producer_sha = _load_sealed_json(
            producer_path, field=f"shadow unit {key.slug} producer authority",
        )
        if (
            receipt.get("schema") != UNIT_SCHEMA or receipt.get("status") != "COMPLETE"
            or receipt.get("unit") != key.as_dict() or receipt.get("arm") != arm
            or str(producer["sha256"]) != producer_sha
            or receipt.get("launch_authority_sha256") != producer_sha
            or producer_authority.get("schema") != AUTHORITY_SCHEMA
            or producer_authority.get("status") != "FROZEN_LAUNCH_AUTHORITY"
            or producer_authority.get("execution") != {"mode": "unit", "unit": key.as_dict()}
            or authority_common_binding(producer_authority) != authority_common_binding(authority)
            or receipt.get("producer_common_binding") != authority_common_binding(authority)
        ):
            raise ShadowReplayError(f"shadow unit {key.slug} is invalid")
        receipts.append(receipt)
        unit_bindings.append({"unit": key.as_dict(), "path": str(path.resolve()), "sha256": digest})
    if len(receipts) != len(ALL_UNITS):
        raise MergeWaiting(len(ALL_UNITS) - len(receipts))
    payload = pool_replays(
        receipts, screen_terminal=terminal,
        screen_terminal_binding=terminal_binding, arm=arm,
    )
    payload.update({
        "unit_receipts": unit_bindings,
        "launch_authority_sha256": authority_sha256,
        "producer_common_binding": authority_common_binding(authority),
    })
    json_path, _json_digest = _write_once(
        root / JSON_NAME, canonical_bytes(payload) + b"\n",
    )
    _write_once(root / MARKDOWN_NAME, _markdown(payload).encode("utf-8"))
    return json_path


def estimate(*, units: int, arm: str = "LITE") -> dict[str, object]:
    if type(units) is not int or units < 1:
        raise ShadowReplayError("estimate units must be a positive exact integer")
    if arm not in COORDINATOR_ARMS:
        raise ShadowReplayError("estimate arm is not a declared coordinator arm")
    source = matrix.estimate(units=units, enable_ve=arm == variant_policy.VE_ARM)
    lite = source["arms"]["LITE"]
    lite_evaluations = _fraction_payload(
        lite["projected_nominal_evaluations_exact"], field="matrix LITE evaluations",
    )
    if lite_evaluations <= 0:
        raise ShadowReplayError("matrix estimate has no positive LITE evaluation basis")
    hours_per_evaluation = float(lite["worker_hours"]) / float(lite_evaluations)
    extra_evaluations = units * HORIZON * EXTRA_PHYSICAL_EVALUATIONS_PER_DECISION
    extra_worker_hours = hours_per_evaluation * extra_evaluations
    replay_worker_hours = float(source["arms"][arm]["worker_hours"])
    return {
        "schema": f"{SCHEMA}-estimate", "units": units, "arm": arm,
        "episodes_replayed": units, "horizon": HORIZON,
        "extra_physical_evaluations_per_decision": EXTRA_PHYSICAL_EVALUATIONS_PER_DECISION,
        "projected_extra_physical_evaluations": extra_evaluations,
        "projected_policy_replay_worker_hours": replay_worker_hours,
        "projected_extra_shadow_worker_hours": extra_worker_hours,
        "projected_worker_hours": replay_worker_hours + extra_worker_hours,
        "planning_worker_hours_per_evaluation": hours_per_evaluation,
        "worker_hours_basis": (
            "Chosen-arm replay uses its matrix estimate; shadow overhead uses matrix "
            "LITE worker-hours per projected nominal evaluation multiplied by exactly "
            "one extra physical evaluation per replay decision."
        ),
        "source_matrix_arm_estimate": source["arms"][arm],
        "source_matrix_lite_rate_estimate": lite,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-manifest", type=Path, default=DEFAULT_PREFLIGHT)
    parser.add_argument("--launch-authority", type=Path)
    parser.add_argument("--screen-run", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--horizon", type=int, default=HORIZON)
    parser.add_argument("--arm", choices=COORDINATOR_ARMS, default="LITE")
    parser.add_argument("--unit", metavar="WORLD:LINEAGE")
    parser.add_argument("--merge", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--estimate", action="store_true")
    # Matrix contract fixes twelve world-lineage units; this only scales estimates.
    parser.add_argument("--estimate-units", type=int, default=len(ALL_UNITS))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    args = _parser().parse_args(raw)
    try:
        if args.estimate:
            print(json.dumps(
                estimate(units=args.estimate_units, arm=args.arm),
                sort_keys=True, indent=2,
            ))
            return 0
        if args.dry_run:
            print(
                f"C3S_SHADOW_DRY_RUN_PASS arm={args.arm} units={len(ALL_UNITS)} "
                f"horizon={HORIZON} diagnostic_only=true"
            )
            return 0
        if (args.unit is None) == (not args.merge):
            raise ShadowReplayError("formal invocation needs exactly one of --unit/--merge")
        if args.screen_run is None:
            raise ShadowReplayError("formal invocation requires --screen-run")
        if args.launch_authority is None:
            raise ShadowReplayError("formal invocation requires --launch-authority")
        if args.horizon != HORIZON:
            raise ShadowReplayError("formal horizon must equal the screened horizon")
        # Heavy work is gated before archive loading or environment construction.
        v1runner.pin_single_thread_runtime()
        key = v1runner.UnitKey.parse(args.unit) if args.unit else None
        execution = {"mode": "unit" if key else "merge", "unit": None if key is None else key.as_dict()}
        authority, authority_sha = validate_launch_authority(
            args.launch_authority, preflight_manifest=args.preflight_manifest,
            screen_run=args.screen_run, output=args.output, arm=args.arm,
            horizon=args.horizon, execution=execution, launch_arguments=raw,
        )
        receipt = execute_unit(
            key=key, output=args.output, screen_run=args.screen_run, arm=args.arm,
            authority=authority, authority_sha256=authority_sha,
            authority_path=args.launch_authority,
        ) if key is not None else execute_merge(
            output=args.output, screen_run=args.screen_run, arm=args.arm,
            authority=authority, authority_sha256=authority_sha,
        )
        print(f"C3S_SHADOW_{'UNIT' if key else 'MERGE'}_PASS receipt={receipt}")
        return 0
    except MergeWaiting as error:
        print(f"C3S_SHADOW_MERGE_INCOMPLETE missing_units={error.missing}")
        return 3
    except Exception as error:
        print(f"C3S_SHADOW_REFUSED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
