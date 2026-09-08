#!/usr/bin/env python3
"""TRAIN-only deployable set-decoder diagnostic over the immutable E1 tapes.

The probe replays each E1 world/lineage trajectory.  At every authenticated
predecision anchor it evaluates the *recorded* BASE, unilateral, and joint
action vectors with the OPS-3 median/no-fading convention (unit Rician gain,
zero dB shadowing).  Selection uses those nominal metrics; reporting and
pooling use only the realised E1 tape metrics.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import replace
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time
from typing import Any, Iterable, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
E1_CODE = REPO / ".scratch" / "multi-catfish-v023-c3-existence-e1"
F1_CODE = REPO / ".scratch" / "multi-catfish-v023-c3-contingency-f1"
F0_CODE = REPO / ".scratch" / "multi-catfish-v023-c3-contingency"
F2_CODE = REPO / ".scratch" / "multi-catfish-v023-c3-contingency-f2"
STAGEC_PLAN = REPO / ".scratch" / "multi-catfish-v023-c1c2-successor-physical-evaluation"
STAGEC_LAUNCH = REPO / ".scratch" / "multi-catfish-v023-c1c2-successor-stagec-launch"
for _path in (HERE, E1_CODE, F1_CODE, F0_CODE, F2_CODE, STAGEC_PLAN, STAGEC_LAUNCH):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))


SCHEMA = "multi-catfish-mcrl-v023-c3-probe-s0-v1"
UNIT_SCHEMA = f"{SCHEMA}-unit"
RESULT_SCHEMA = f"{SCHEMA}-result"
CLAIM_CEILING = "TRAIN_DEVELOPMENT_DIAGNOSTIC_PROBE_S0_NO_LEARNER_NO_ADMISSION_NO_TEST"
EXPECTED_TERMINAL_SHA256 = "0bc54fad23c8cdac2ce789c49ee37880f4df6e32110576c7a800443df0e7c4a6"
DEFAULT_INPUT = Path("/home/sat/mcrl-v023-c3-existence-e1-20260908-r1")
DEFAULT_OUTPUT = Path("/home/sat/mcrl-v023-c3-probe-s0-20260908-r1")
CANONICAL_TLE_ROOT = Path("/home/sat/mcrl-runtime/tle-frozen-20260820")
RESULT_NAME = "probe-s0-result.json"
TABLE_NAME = "probe-s0-table.md"
UNIT_NAME = "unit-result.json"
THREAD_ENV = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")
ARMS = ("BASE", "ORACLE_U1", "ORACLE_J1", "S0", "S0_U", "S0_J")


class ProbeError(RuntimeError):
    """The diagnostic contract, source authentication, or replay failed."""


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def sha256_file(path: Path, *, chunk_size: int = 8 << 20) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while block := handle.read(chunk_size):
            digest.update(block)
    return digest.hexdigest()


def require_file_digest(path: Path, expected: str, *, label: str) -> None:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ProbeError(f"{label} is absent, non-regular, or a symlink: {path}")
    observed = sha256_file(path)
    if observed != expected:
        raise ProbeError(
            f"{label} digest mismatch: expected {expected}, observed {observed}"
        )


def load_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProbeError(f"cannot read {label}: {path}") from error
    if not isinstance(value, dict):
        raise ProbeError(f"{label} must be a JSON object")
    return value


def parse_exact(value: object, *, label: str) -> Fraction:
    if not isinstance(value, Mapping):
        raise ProbeError(f"{label} exact rational is malformed")
    try:
        result = Fraction(int(value["numerator"]), int(value["denominator"]))
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
        raise ProbeError(f"{label} exact rational is malformed") from error
    if set(value) != {"numerator", "denominator", "float_hex"}:
        raise ProbeError(f"{label} exact rational has unexpected fields")
    try:
        encoded_float = float.fromhex(str(value["float_hex"]))
    except (ValueError, OverflowError) as error:
        raise ProbeError(f"{label} float hex is malformed") from error
    if encoded_float.hex() != float(result).hex():
        raise ProbeError(f"{label} float hex disagrees with exact rational")
    return result


def fraction_payload(value: Fraction) -> dict[str, str]:
    return {
        "numerator": str(value.numerator),
        "denominator": str(value.denominator),
        "float_hex": float(value).hex(),
    }


def metric_from_tape(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ProbeError(f"{label} metrics are malformed")
    try:
        bits = float.fromhex(str(value["total_bits"]))
        energy = float.fromhex(str(value["total_energy_j"]))
        served = value["served"]
        opportunities = value["opportunities"]
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        raise ProbeError(f"{label} metrics are malformed") from error
    if (
        not math.isfinite(bits) or bits < 0.0
        or not math.isfinite(energy) or energy <= 0.0
        or type(served) is not int or type(opportunities) is not int
        or not 0 <= served <= opportunities or opportunities <= 0
    ):
        raise ProbeError(f"{label} metrics are outside their domain")
    return {
        "total_bits": bits,
        "total_energy_j": energy,
        "served": served,
        "opportunities": opportunities,
    }


def metric_payload(metric: Mapping[str, object]) -> dict[str, object]:
    return {
        "total_bits_hex": float(metric["total_bits"]).hex(),
        "total_energy_j_hex": float(metric["total_energy_j"]).hex(),
        "served": int(metric["served"]),
        "opportunities": int(metric["opportunities"]),
    }


def score_exact(metric: Mapping[str, object], eta_ref: Fraction) -> Fraction:
    return Fraction.from_float(float(metric["total_bits"])) - eta_ref * Fraction.from_float(
        float(metric["total_energy_j"])
    )


def choose_profile(
    profiles: Sequence[Mapping[str, object]], *, eta_ref: Fraction,
    allowed_kinds: frozenset[str],
) -> Mapping[str, object]:
    """Choose by nominal score/service only, with a canonical ID tie break."""

    base_rows = [row for row in profiles if row.get("kind") == "base"]
    if len(base_rows) != 1:
        raise ProbeError("an anchor requires exactly one BASE profile")
    base_nominal = base_rows[0].get("nominal")
    if not isinstance(base_nominal, Mapping):
        raise ProbeError("BASE nominal metrics are absent")
    threshold = int(base_nominal["served"])
    eligible: list[tuple[Fraction, str, Mapping[str, object]]] = []
    for row in profiles:
        kind = row.get("kind")
        nominal = row.get("nominal")
        profile_id = row.get("profile_id")
        if kind not in allowed_kinds or not isinstance(nominal, Mapping) or not isinstance(profile_id, str):
            continue
        if int(nominal["served"]) >= threshold:
            eligible.append((score_exact(nominal, eta_ref), profile_id, row))
    if not eligible:
        raise ProbeError("nominal service constraint has no feasible profile")
    # Maximization followed by lexicographically first profile ID.
    best_score = max(value[0] for value in eligible)
    return min((value for value in eligible if value[0] == best_score), key=lambda value: value[1])[2]


def _average_ranks(values: Sequence[Fraction]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: (values[index], index))
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(order):
        end = cursor + 1
        while end < len(order) and values[order[end]] == values[order[cursor]]:
            end += 1
        rank = (cursor + 1 + end) / 2.0
        for index in order[cursor:end]:
            ranks[index] = rank
        cursor = end
    return ranks


def spearman_exact_scores(nominal: Sequence[Fraction], realised: Sequence[Fraction]) -> float | None:
    if len(nominal) != len(realised) or not nominal:
        raise ProbeError("rank correlation inputs must be nonempty and equal length")
    left = _average_ranks(nominal)
    right = _average_ranks(realised)
    left_mean = math.fsum(left) / len(left)
    right_mean = math.fsum(right) / len(right)
    covariance = math.fsum((a - left_mean) * (b - right_mean) for a, b in zip(left, right, strict=True))
    left_ss = math.fsum((a - left_mean) ** 2 for a in left)
    right_ss = math.fsum((b - right_mean) ** 2 for b in right)
    if left_ss == 0.0 or right_ss == 0.0:
        return None
    return covariance / math.sqrt(left_ss * right_ss)


def exact_pool(metrics: Iterable[Mapping[str, object]]) -> dict[str, object]:
    bits = Fraction(0)
    energy = Fraction(0)
    served = 0
    opportunities = 0
    count = 0
    for metric in metrics:
        bits += Fraction.from_float(float(metric["total_bits"]))
        energy += Fraction.from_float(float(metric["total_energy_j"]))
        served += int(metric["served"])
        opportunities += int(metric["opportunities"])
        count += 1
    if count == 0 or energy <= 0 or opportunities <= 0:
        raise ProbeError("cannot pool an empty or non-positive metric set")
    eta = bits / energy
    service = Fraction(served, opportunities)
    return {
        "anchors": count,
        "total_bits_exact": fraction_payload(bits),
        "total_energy_j_exact": fraction_payload(energy),
        "eta_exact": fraction_payload(eta),
        "eta_bits_per_j": float(eta),
        "eta_hex": float(eta).hex(),
        "served": served,
        "opportunities": opportunities,
        "service_fraction_exact": fraction_payload(service),
        "service_fraction": float(service),
        "service_fraction_hex": float(service).hex(),
    }


def process_synthetic_tape(tape: Mapping[str, object], eta_ref: Fraction) -> list[dict[str, object]]:
    """Pure tiny-tape path used to test ranking, realised scoring, and pooling."""

    raw = tape.get("anchors")
    if not isinstance(raw, list):
        raise ProbeError("synthetic tape anchors are malformed")
    results = []
    for anchor in raw:
        if not isinstance(anchor, Mapping) or not isinstance(anchor.get("profiles"), list):
            raise ProbeError("synthetic anchor is malformed")
        profiles = anchor["profiles"]
        chosen = choose_profile(
            profiles, eta_ref=eta_ref, allowed_kinds=frozenset({"base", "unilateral", "joint"})
        )
        realised = chosen.get("realised")
        if not isinstance(realised, Mapping):
            raise ProbeError("chosen synthetic profile lacks realised metrics")
        results.append({"profile_id": chosen["profile_id"], "realised": dict(realised)})
    return results


def _pin_runtime() -> tuple[Any, Any, Any]:
    for name in THREAD_ENV:
        if os.environ.get(name) != "1":
            raise ProbeError(f"{name}=1 is required before importing the runtime")
    import run_v023_c3_existence_e1 as e1
    import run_v023_c3_contingency_f1 as f1
    from mcrl.runtime.ee_axis_ops3_live import snapshot_ops3_anchor

    e1.pin_single_thread_runtime()
    return e1, f1, snapshot_ops3_anchor


def load_terminal(input_root: Path) -> dict[str, Any]:
    path = Path(input_root) / "terminal-receipt.json"
    require_file_digest(path, EXPECTED_TERMINAL_SHA256, label="E1 terminal receipt")
    terminal = load_json(path, label="E1 terminal receipt")
    if (
        terminal.get("status") != "COMPLETE" or terminal.get("integrity") is not True
        or terminal.get("test_split_opened") is not False
        or terminal.get("episode_training") is not False
        or terminal.get("learner_update") is not False
    ):
        raise ProbeError("E1 terminal receipt is not the sealed TRAIN result")
    if terminal.get("U1", {}).get("eta_BASE_hex") != terminal.get("J1", {}).get("eta_BASE_hex"):
        raise ProbeError("E1 U1/J1 BASE constants disagree")
    return terminal


def terminal_units(terminal: Mapping[str, object]) -> dict[tuple[int, int], Mapping[str, object]]:
    rows = terminal.get("unit_receipts")
    if not isinstance(rows, list) or len(rows) != 12:
        raise ProbeError("terminal receipt does not bind twelve units")
    result: dict[tuple[int, int], Mapping[str, object]] = {}
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("unit"), Mapping):
            raise ProbeError("terminal unit binding is malformed")
        unit = row["unit"]
        key = (int(unit["world"]), int(unit["lineage"]))
        if key in result:
            raise ProbeError("terminal unit binding is duplicated")
        result[key] = row
    return result


def authenticate_unit_input(
    input_root: Path, terminal: Mapping[str, object], key: tuple[int, int],
) -> tuple[dict[str, Any], dict[str, str]]:
    binding = terminal_units(terminal).get(key)
    if binding is None:
        raise ProbeError(f"unit {key[0]}:{key[1]} is outside the terminal panel")
    relative_receipt = binding.get("path")
    expected_receipt_sha = binding.get("sha256")
    if not isinstance(relative_receipt, str) or not isinstance(expected_receipt_sha, str):
        raise ProbeError("terminal unit path/digest is malformed")
    receipt_path = Path(input_root) / relative_receipt
    require_file_digest(receipt_path, expected_receipt_sha, label="E1 unit receipt")
    receipt = load_json(receipt_path, label="E1 unit receipt")
    tape_sha = receipt.get("tape_sha256")
    if not isinstance(tape_sha, str):
        raise ProbeError("E1 unit receipt lacks tape_sha256")
    unit_dir = receipt_path.parent
    tape_path = unit_dir / "e1-physical-tape.json"
    manifest_path = unit_dir / "e1-physical-tape.manifest.json"
    require_file_digest(tape_path, tape_sha, label="E1 unit tape")
    manifest = load_json(manifest_path, label="E1 tape manifest")
    if not isinstance(manifest.get("tape"), Mapping) or manifest["tape"].get("sha256") != tape_sha:
        raise ProbeError("E1 tape manifest disagrees with authenticated tape")
    tape = load_json(tape_path, label="E1 unit tape")
    raw_unit = tape.get("unit")
    if (
        tape.get("status") != "COMPLETE_IMMUTABLE_TAPE"
        or not isinstance(raw_unit, Mapping)
        or (raw_unit.get("world"), raw_unit.get("lineage")) != key
        or raw_unit.get("split") != "TRAIN"
        or tape.get("test_split_opened") is not False
    ):
        raise ProbeError("E1 tape identity/status/split is malformed")
    return tape, {
        "tape_sha256": tape_sha,
        "tape_manifest_sha256": sha256_file(manifest_path),
        "unit_receipt_sha256": expected_receipt_sha,
    }


def code_digests() -> list[dict[str, str]]:
    paths = (
        HERE / "run_probe_s0.py",
        E1_CODE / "run_v023_c3_existence_e1.py",
        F1_CODE / "run_v023_c3_contingency_f1.py",
        REPO / "src/mcrl/runtime/ee_axis_ops3_live.py",
        REPO / "src/mcrl/env/step.py",
        REPO / "src/mcrl/env/keyed_fading.py",
        REPO / ".scratch/multi-catfish-v023-physical/v023_physical_episode_runner.py",
        REPO / ".scratch/multi-catfish-v023-physical/run_v023_dropc3_evaluation_server.py",
    )
    return [
        {"path": path.relative_to(REPO).as_posix(), "sha256": sha256_file(path)}
        for path in paths
    ]


@contextmanager
def nominal_no_fading(step_env: Any):
    """Temporarily apply the exact no-fading convention used by OPS-3."""

    original_physics = step_env.physics
    original_field = step_env._fading_field
    step_env.physics = replace(original_physics, fading_enabled=False)
    step_env._fading_field = None
    try:
        yield
    finally:
        step_env._fading_field = original_field
        step_env.physics = original_physics


def _nominal_metric(e1: Any, f1: Any, step_env: Any, actions: Any, rng: Any, interval_s: float) -> dict[str, object]:
    with nominal_no_fading(step_env):
        evaluation = e1._evaluate_actions_neutral(step_env, actions, rng)
    profile, _link_power = f1.profile_from_evaluation(evaluation, interval_s=interval_s)
    encoded = e1._profile_metrics(profile)
    return metric_from_tape(encoded, label="nominal evaluation")


def _candidate_rows(step: Mapping[str, object]) -> list[dict[str, object]]:
    result = [{
        "profile_id": "BASE", "kind": "base",
        "actions": step.get("reference_actions"),
        "realised": metric_from_tape(step.get("reference_metrics"), label="BASE realised"),
    }]
    for field, kind in (("unilateral_candidates", "unilateral"), ("joint_witness_catalog", "joint")):
        rows = step.get(field)
        if not isinstance(rows, list):
            raise ProbeError(f"{field} is not a list")
        for raw in rows:
            if not isinstance(raw, Mapping) or not isinstance(raw.get("profile_id"), str):
                raise ProbeError(f"{field} contains a malformed row")
            result.append({
                "profile_id": raw["profile_id"], "kind": kind,
                "actions": raw.get("candidate_joint_actions"),
                "realised": metric_from_tape(raw.get("metrics"), label=f"{raw['profile_id']} realised"),
            })
    ids = [str(row["profile_id"]) for row in result]
    if len(ids) != len(set(ids)):
        raise ProbeError("profile IDs collide within an anchor")
    return result


def _rank_diagnostic(profiles: Sequence[Mapping[str, object]], eta_ref: Fraction) -> dict[str, object]:
    nominal = [score_exact(row["nominal"], eta_ref) for row in profiles]  # type: ignore[arg-type]
    realised = [score_exact(row["realised"], eta_ref) for row in profiles]  # type: ignore[arg-type]
    correlation = spearman_exact_scores(nominal, realised)
    return {
        "profile_count": len(profiles),
        "quantity": "TOTAL_BITS_MINUS_ETA_REF_TIMES_TOTAL_ENERGY_J",
        "method": "SPEARMAN_AVERAGE_RANKS_EXACT_SCORE_TIES",
        "correlation": correlation,
        "correlation_hex": None if correlation is None else correlation.hex(),
    }


def _selected_payload(row: Mapping[str, object], eta_ref: Fraction) -> dict[str, object]:
    nominal = row["nominal"]
    realised = row["realised"]
    assert isinstance(nominal, Mapping) and isinstance(realised, Mapping)
    return {
        "profile_id": row["profile_id"],
        "kind": row["kind"],
        "nominal": metric_payload(nominal),
        "nominal_score_exact": fraction_payload(score_exact(nominal, eta_ref)),
        # This is the only metric block consumed by merge/pooling.
        "realised_tape_metrics": metric_payload(realised),
    }


def _metric_from_selected(value: Mapping[str, object]) -> dict[str, object]:
    raw = value.get("realised_tape_metrics")
    if not isinstance(raw, Mapping):
        raise ProbeError("selected row lacks realised_tape_metrics")
    try:
        return {
            "total_bits": float.fromhex(str(raw["total_bits_hex"])),
            "total_energy_j": float.fromhex(str(raw["total_energy_j_hex"])),
            "served": int(raw["served"]),
            "opportunities": int(raw["opportunities"]),
        }
    except (KeyError, ValueError, OverflowError, TypeError) as error:
        raise ProbeError("selected realised metrics are malformed") from error


def evaluate_unit(
    *, input_root: Path, terminal: Mapping[str, object], key: tuple[int, int],
    e1: Any, f1: Any, snapshot_ops3_anchor: Any,
) -> dict[str, object]:
    import numpy as np
    from mcrl.env.keyed_fading import KeyedFadingField
    from mcrl.runtime.ee_axis_state import encode_ee_axis_state
    from mcrl.runtime.prereg import read_prereg
    from mcrl.runtime.training_pipeline import _evaluation_rngs

    tape, input_digests = authenticate_unit_input(input_root, terminal, key)
    eta_ref = parse_exact(terminal["U1"]["eta_BASE_exact"], label="eta_BASE")
    u_choices = terminal["U1"].get("chosen_profiles")
    j_choices = terminal["J1"].get("chosen_profiles")
    if not isinstance(u_choices, Mapping) or not isinstance(j_choices, Mapping):
        raise ProbeError("terminal oracle choice maps are malformed")

    record = read_prereg(f1.PREREG_PATH)
    if record.digest != f1.PREREG_RECORD_DIGEST:
        raise ProbeError("TRAIN preregistration digest changed")
    physical, server = f1._runtime_modules()
    world, lineage = key
    field = KeyedFadingField.from_components(e1.FIELD_COMPONENT, world)
    started_ns = time.time_ns()
    started = time.monotonic()
    anchors: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix=f"probe-s0-{world}-{lineage}-tle-") as temporary:
        archive = server._freeze_archive(
            record, CANONICAL_TLE_ROOT, Path(temporary) / "frozen", physical
        )
        environment = server._make_environment(archive)
        step_env = environment.environment
        if getattr(step_env, "_started", False):
            raise ProbeError("environment started before the keyed field was bound")
        step_env._fading_field = field
        rngs = tuple(_evaluation_rngs(world))
        _states, _masks, observation = environment.reset(rngs[0], rngs[1])
        interval_s = float(step_env.driver.config.ephemeris.time_step_s)
        steps = tape.get("steps")
        if not isinstance(steps, list) or len(steps) != 10:
            raise ProbeError("unit tape must contain ten anchors")
        for step in steps:
            if not isinstance(step, Mapping):
                raise ProbeError("unit step is malformed")
            step_index = int(step["step_index"])
            anchor_id = f"{world}:{lineage}:{step_index}"
            if int(observation.step_index) != step_index:
                raise ProbeError(f"{anchor_id}: replay reached the wrong step")
            native = encode_ee_axis_state(step_env, observation)
            native.verify()
            if native.state_sha256 != step.get("state_sha256"):
                raise ProbeError(f"{anchor_id}: live causal state digest disagrees with tape")
            masks = np.asarray(step.get("action_masks"), dtype=np.bool_)
            if not np.array_equal(masks, np.asarray(native.action_masks, dtype=np.bool_)):
                raise ProbeError(f"{anchor_id}: live action masks disagree with tape")
            if f1.action_physical_keys(observation) != step.get("action_physical_keys"):
                raise ProbeError(f"{anchor_id}: live physical action keys disagree with tape")
            reference = np.asarray(step.get("reference_actions"), dtype=np.int64)
            # The OPS-3 helper authenticates and detaches current geometry,
            # committed associations/occupancy, and segment state.  We do not
            # invoke project_ops3_anchor: future information is forbidden.
            snapshot = snapshot_ops3_anchor(step_env, observation)
            profiles = _candidate_rows(step)
            nominal_cache: dict[tuple[int, ...], dict[str, object]] = {}
            for row in profiles:
                actions = np.asarray(row["actions"], dtype=np.int64)
                if actions.shape != reference.shape:
                    raise ProbeError(f"{anchor_id}: profile action vector is malformed")
                action_key = tuple(int(value) for value in actions.tolist())
                if action_key not in nominal_cache:
                    nominal_cache[action_key] = _nominal_metric(
                        e1, f1, step_env, actions, rngs[0], interval_s
                    )
                row["nominal"] = nominal_cache[action_key]
            by_id = {str(row["profile_id"]): row for row in profiles}
            oracle_u_id = u_choices.get(anchor_id)
            oracle_j_id = j_choices.get(anchor_id)
            if oracle_u_id not in by_id or oracle_j_id not in by_id:
                raise ProbeError(f"{anchor_id}: terminal oracle profile is absent from tape")
            selected_rows = {
                "BASE": by_id["BASE"],
                "ORACLE_U1": by_id[str(oracle_u_id)],
                "ORACLE_J1": by_id[str(oracle_j_id)],
                "S0": choose_profile(
                    profiles, eta_ref=eta_ref,
                    allowed_kinds=frozenset({"base", "unilateral", "joint"}),
                ),
                "S0_U": choose_profile(
                    profiles, eta_ref=eta_ref,
                    allowed_kinds=frozenset({"base", "unilateral"}),
                ),
                "S0_J": choose_profile(
                    profiles, eta_ref=eta_ref,
                    allowed_kinds=frozenset({"base", "joint"}),
                ),
            }
            anchors.append({
                "anchor_id": anchor_id,
                "world": world,
                "lineage": lineage,
                "step_index": step_index,
                "ops3_current_anchor_sha256": snapshot.anchor_sha256,
                "nominal_convention": "OPS3_UNIT_RICIAN_GAIN_ZERO_DB_SHADOW_CURRENT_ANCHOR_ONLY",
                "profile_counts": {
                    "base": 1,
                    "unilateral": sum(row["kind"] == "unilateral" for row in profiles),
                    "joint": sum(row["kind"] == "joint" for row in profiles),
                    "unique_action_vectors_evaluated": len(nominal_cache),
                },
                "rank_correlation": _rank_diagnostic(profiles, eta_ref),
                "selected": {
                    arm: _selected_payload(selected_rows[arm], eta_ref) for arm in ARMS
                },
            })
            environment.step(reference, rngs[0])
            committed = environment.last_outcome
            committed_profile, committed_link_power = f1.profile_from_evaluation(
                committed, interval_s=interval_s
            )
            if f1.profile_to_payload(
                committed_profile, link_power_w=committed_link_power
            ) != step.get("reference_profile"):
                raise ProbeError(f"{anchor_id}: keyed BASE replay disagrees with realised tape")
            if step_index < 9:
                if bool(committed.done):
                    raise ProbeError(f"{anchor_id}: replay terminated early")
                observation = committed.observation
    elapsed = time.monotonic() - started
    finished_ns = time.time_ns()
    return {
        "schema": UNIT_SCHEMA,
        "status": "COMPLETE",
        "claim_ceiling": CLAIM_CEILING,
        "unit": {"world": world, "lineage": lineage, "split": "TRAIN"},
        "eta_ref_exact": fraction_payload(eta_ref),
        "input_digests": {
            "terminal_receipt_sha256": EXPECTED_TERMINAL_SHA256,
            **input_digests,
        },
        "code_digests": code_digests(),
        "anchors": anchors,
        "timing": {
            "started_epoch_ns": started_ns,
            "finished_epoch_ns": finished_ns,
            "elapsed_seconds_hex": elapsed.hex(),
        },
        "selection_uses_nominal_only": True,
        "scoring_uses_realised_tape_metrics_only": True,
        "test_split_opened": False,
        "learner_used": False,
        "admission_authority": False,
    }


def write_once(path: Path, payload: object) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise ProbeError(f"refusing to overwrite write-once artifact: {path}")
    encoded = canonical_bytes(payload) + b"\n"
    with path.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    path.chmod(0o444)
    observed = path.read_bytes()
    if observed != encoded or path.stat().st_mode & 0o777 != 0o444:
        raise ProbeError(f"write-once artifact failed readback: {path}")
    return hashlib.sha256(observed).hexdigest()


def write_once_text(path: Path, text: str) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise ProbeError(f"refusing to overwrite write-once artifact: {path}")
    encoded = text.encode("utf-8")
    with path.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    path.chmod(0o444)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _unit_path(output_root: Path, key: tuple[int, int]) -> Path:
    return Path(output_root) / "units" / f"{key[0]}-{key[1]}" / UNIT_NAME


def execute_unit(
    *, input_root: Path, output_root: Path, terminal: Mapping[str, object],
    key: tuple[int, int], e1: Any, f1: Any, snapshot_ops3_anchor: Any,
) -> tuple[Path, bool]:
    path = _unit_path(output_root, key)
    if path.exists() and not path.is_symlink():
        payload = load_json(path, label="existing probe unit")
        if payload.get("schema") != UNIT_SCHEMA or payload.get("status") != "COMPLETE":
            raise ProbeError(f"existing probe unit is invalid: {path}")
        return path, True
    payload = evaluate_unit(
        input_root=input_root, terminal=terminal, key=key,
        e1=e1, f1=f1, snapshot_ops3_anchor=snapshot_ops3_anchor,
    )
    write_once(path, payload)
    return path, False


def _verify_unit_result(
    path: Path, *, key: tuple[int, int], expected_code: list[dict[str, str]],
    expected_tape_sha: str,
) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o777 != 0o444:
        raise ProbeError(f"unit result is absent, mutable, or a symlink: {path}")
    value = load_json(path, label="probe unit result")
    if (
        value.get("schema") != UNIT_SCHEMA or value.get("status") != "COMPLETE"
        or value.get("unit", {}).get("world") != key[0]
        or value.get("unit", {}).get("lineage") != key[1]
        or value.get("claim_ceiling") != CLAIM_CEILING
        or value.get("code_digests") != expected_code
        or value.get("input_digests", {}).get("terminal_receipt_sha256") != EXPECTED_TERMINAL_SHA256
        or value.get("input_digests", {}).get("tape_sha256") != expected_tape_sha
        or value.get("selection_uses_nominal_only") is not True
        or value.get("scoring_uses_realised_tape_metrics_only") is not True
        or value.get("test_split_opened") is not False
        or len(value.get("anchors", [])) != 10
    ):
        raise ProbeError(f"unit result binding drifted: {path}")
    return value


def _arm_breakdown(anchors: Sequence[Mapping[str, object]], arm: str) -> dict[str, object]:
    return exact_pool(
        _metric_from_selected(anchor["selected"][arm])  # type: ignore[index]
        for anchor in anchors
    )


def _pct_delta(value: Fraction, base: Fraction) -> Fraction:
    return Fraction(100) * (value / base - 1)


def build_result(
    *, input_root: Path, output_root: Path, terminal: Mapping[str, object],
    units: Sequence[Mapping[str, object]], unit_files: Sequence[Path],
) -> dict[str, object]:
    anchors = [anchor for unit in units for anchor in unit["anchors"]]  # type: ignore[index]
    anchors.sort(key=lambda row: str(row["anchor_id"]))
    if len(anchors) != 120 or len({row["anchor_id"] for row in anchors}) != 120:
        raise ProbeError("merge requires exactly 120 unique anchors")
    pooled = {arm: _arm_breakdown(anchors, arm) for arm in ARMS}
    base_eta = parse_exact(pooled["BASE"]["eta_exact"], label="merged BASE eta")
    eta_ref = parse_exact(terminal["U1"]["eta_BASE_exact"], label="terminal eta_BASE")
    if base_eta != eta_ref:
        raise ProbeError("merged BASE eta disagrees exactly with E1 terminal receipt")
    for arm, terminal_name in (("ORACLE_U1", "U1"), ("ORACLE_J1", "J1")):
        observed = parse_exact(pooled[arm]["eta_exact"], label=f"merged {arm} eta")
        expected = parse_exact(
            terminal[terminal_name]["certificate"]["optimal_ratio_exact"],
            label=f"terminal {terminal_name} eta",
        )
        if observed != expected:
            raise ProbeError(f"merged {arm} does not reproduce E1 exactly")
    for arm in ARMS:
        eta = parse_exact(pooled[arm]["eta_exact"], label=f"{arm} eta")
        delta = _pct_delta(eta, base_eta)
        pooled[arm]["percent_vs_base_exact"] = fraction_payload(delta)
        pooled[arm]["percent_vs_base"] = float(delta)

    worlds = sorted({int(anchor["world"]) for anchor in anchors})
    lineages = sorted({int(anchor["lineage"]) for anchor in anchors})
    per_world = {
        str(world): {
            arm: _arm_breakdown([row for row in anchors if int(row["world"]) == world], arm)
            for arm in ARMS
        }
        for world in worlds
    }
    per_lineage = {
        str(lineage): {
            arm: _arm_breakdown([row for row in anchors if int(row["lineage"]) == lineage], arm)
            for arm in ARMS
        }
        for lineage in lineages
    }
    def agree(left: str, right: str) -> dict[str, object]:
        count = sum(
            anchor["selected"][left]["profile_id"] == anchor["selected"][right]["profile_id"]  # type: ignore[index]
            for anchor in anchors
        )
        fraction = Fraction(count, len(anchors))
        return {"matches": count, "anchors": len(anchors), "fraction_exact": fraction_payload(fraction), "fraction": float(fraction)}

    correlations = [
        row["rank_correlation"]["correlation"] for row in anchors  # type: ignore[index]
        if row["rank_correlation"]["correlation"] is not None  # type: ignore[index]
    ]
    timing_rows = [unit["timing"] for unit in units]
    started_ns = min(int(row["started_epoch_ns"]) for row in timing_rows)
    finished_ns = max(int(row["finished_epoch_ns"]) for row in timing_rows)
    worker_seconds = math.fsum(float.fromhex(str(row["elapsed_seconds_hex"])) for row in timing_rows)
    rank_summary = {
        "anchors": len(anchors),
        "defined_anchors": len(correlations),
        "undefined_constant_rank_anchors": len(anchors) - len(correlations),
        "mean": None if not correlations else math.fsum(float(v) for v in correlations) / len(correlations),
        "median": None if not correlations else statistics.median(float(v) for v in correlations),
        "minimum": None if not correlations else min(float(v) for v in correlations),
        "maximum": None if not correlations else max(float(v) for v in correlations),
    }
    return {
        "schema": RESULT_SCHEMA,
        "status": "COMPLETE",
        "claim_ceiling": CLAIM_CEILING,
        "question": "Can an S0 deployable nominal set decoder capture E1's realised oracle headroom in the original regime?",
        "interpretation_boundary": "TRAIN development diagnostic only; no learner, admission authority, efficacy claim, or TEST access",
        "eta_ref_exact": fraction_payload(eta_ref),
        "eta_ref_bits_per_j": float(eta_ref),
        "selection_rule": {
            "objective": "MAX_NOMINAL_TOTAL_BITS_MINUS_ETA_REF_TIMES_NOMINAL_TOTAL_ENERGY_J",
            "constraint": "NOMINAL_SERVED_AT_LEAST_BASE_NOMINAL_SERVED",
            "tie_break": "LEXICOGRAPHIC_PROFILE_ID",
            "nominal_channel": "OPS3_UNIT_RICIAN_GAIN_ZERO_DB_SHADOW_CURRENT_ANCHOR_ONLY",
            "trajectory": "ORIGINAL_KEYED_FIELD_BASE_COMMITTED_BETWEEN_ANCHORS",
            "scoring": "REALISED_E1_TAPE_METRICS_ONLY",
        },
        "pooled": pooled,
        "per_world": per_world,
        "per_lineage": per_lineage,
        "agreement": {
            "S0_vs_ORACLE_U1": agree("S0", "ORACLE_U1"),
            "S0_vs_ORACLE_J1": agree("S0", "ORACLE_J1"),
            "S0_U_vs_ORACLE_U1": agree("S0_U", "ORACLE_U1"),
            "S0_J_vs_ORACLE_J1": agree("S0_J", "ORACLE_J1"),
        },
        "nominal_vs_realised_rank_correlation": rank_summary,
        "anchors": anchors,
        "input_digests": {
            "terminal_receipt": {
                "path": str(Path(input_root) / "terminal-receipt.json"),
                "sha256": EXPECTED_TERMINAL_SHA256,
            },
            "unit_tapes": [
                {
                    "world": unit["unit"]["world"],  # type: ignore[index]
                    "lineage": unit["unit"]["lineage"],  # type: ignore[index]
                    **unit["input_digests"],  # type: ignore[misc]
                }
                for unit in units
            ],
        },
        "code_digests": code_digests(),
        "unit_results": [
            {"path": str(path), "sha256": sha256_file(path)} for path in unit_files
        ],
        "timing": {
            "unit_worker_seconds": worker_seconds,
            "unit_worker_seconds_hex": worker_seconds.hex(),
            "parallel_wall_span_seconds": (finished_ns - started_ns) / 1e9,
            "parallel_wall_span_seconds_hex": ((finished_ns - started_ns) / 1e9).hex(),
            "first_unit_started_epoch_ns": started_ns,
            "last_unit_finished_epoch_ns": finished_ns,
        },
        "test_split_opened": False,
        "learner_used": False,
        "admission_authority": False,
        "efficacy_claim": False,
    }


def markdown_table(result: Mapping[str, object]) -> str:
    pooled = result["pooled"]
    assert isinstance(pooled, Mapping)
    labels = {
        "BASE": "BASE", "ORACLE_U1": "B(U1 oracle)", "ORACLE_J1": "B(J1 oracle)",
        "S0": "S0 deployable", "S0_U": "S0-U deployable", "S0_J": "S0-J deployable",
    }
    lines = [
        f"# S0 deployable set-decoder diagnostic\n",
        f"Claim ceiling: `{CLAIM_CEILING}`\n",
        "| Arm | Pooled EE (bits/J) | % vs BASE | Service | Served / opportunities |",
        "|---|---:|---:|---:|---:|",
    ]
    for arm in ARMS:
        row = pooled[arm]
        assert isinstance(row, Mapping)
        lines.append(
            f"| {labels[arm]} | {float(row['eta_bits_per_j']):,.6f} | "
            f"{float(row['percent_vs_base']):+.6f}% | {100.0 * float(row['service_fraction']):.6f}% | "
            f"{row['served']} / {row['opportunities']} |"
        )
    agreement = result["agreement"]
    assert isinstance(agreement, Mapping)
    lines.extend(["", "## Choice agreement", "", "| Comparison | Matches | Fraction |", "|---|---:|---:|"])
    for name, value in agreement.items():
        assert isinstance(value, Mapping)
        lines.append(f"| {name.replace('_', ' ')} | {value['matches']} / {value['anchors']} | {100.0 * float(value['fraction']):.3f}% |")
    rank = result["nominal_vs_realised_rank_correlation"]
    assert isinstance(rank, Mapping)
    lines.extend([
        "", "## Information-gap diagnostic", "",
        f"Per-anchor nominal-vs-realised Spearman rank correlation: mean "
        f"{float(rank['mean']):.6f}, median {float(rank['median']):.6f}, range "
        f"[{float(rank['minimum']):.6f}, {float(rank['maximum']):.6f}] "
        f"over {rank['defined_anchors']} defined anchors.", "",
        "All arm scores above use realised E1 tape rows; nominal values are selection-only.",
    ])
    return "\n".join(lines) + "\n"


def merge(*, input_root: Path, output_root: Path, terminal: Mapping[str, object]) -> tuple[Path, Path]:
    expected_code = code_digests()
    bindings = terminal_units(terminal)
    units = []
    paths = []
    for key in sorted(bindings):
        receipt = load_json(Path(input_root) / str(bindings[key]["path"]), label="E1 unit receipt")
        tape_sha = str(receipt["tape_sha256"])
        path = _unit_path(output_root, key)
        units.append(_verify_unit_result(path, key=key, expected_code=expected_code, expected_tape_sha=tape_sha))
        paths.append(path)
    result = build_result(
        input_root=input_root, output_root=output_root, terminal=terminal,
        units=units, unit_files=paths,
    )
    result_path = Path(output_root) / RESULT_NAME
    table_path = Path(output_root) / TABLE_NAME
    write_once(result_path, result)
    write_once_text(table_path, markdown_table(result))
    return result_path, table_path


def estimate(*, input_root: Path, terminal: Mapping[str, object], workers: int) -> dict[str, object]:
    if not 1 <= workers <= 12:
        raise ProbeError("--workers must be between 1 and 12")
    bindings = terminal_units(terminal)
    rows = []
    total_profiles = 0
    for key in sorted(bindings):
        receipt_path = Path(input_root) / str(bindings[key]["path"])
        require_file_digest(receipt_path, str(bindings[key]["sha256"]), label="E1 unit receipt")
        receipt = load_json(receipt_path, label="E1 unit receipt")
        counts = receipt.get("counts")
        if not isinstance(counts, Mapping):
            raise ProbeError("E1 unit counts are absent")
        profiles = int(counts["anchors"]) + int(counts["unilateral_profiles"]) + int(counts["joint_profiles"])
        total_profiles += profiles
        rows.append({
            "world": key[0], "lineage": key[1],
            "anchors": int(counts["anchors"]),
            "unilateral_profiles": int(counts["unilateral_profiles"]),
            "joint_profiles": int(counts["joint_profiles"]),
            "nominal_profile_rows": profiles,
        })
    ledger = load_json(Path(input_root) / "budget-ledger.json", label="E1 timing ledger")
    e1_worker_seconds = float.fromhex(str(ledger["unit_charged_worker_seconds_hex"]))
    if int(ledger.get("unit_charge_count", -1)) != 12 or e1_worker_seconds <= 0.0:
        raise ProbeError("E1 timing ledger does not contain twelve positive unit timings")
    seconds_per_profile = e1_worker_seconds / total_profiles
    estimates = [row["nominal_profile_rows"] * seconds_per_profile for row in rows]
    # Deterministic longest-processing-time scheduling gives a more honest N-worker wall estimate.
    loads = [0.0] * workers
    for duration in sorted(estimates, reverse=True):
        index = min(range(workers), key=lambda item: (loads[item], item))
        loads[index] += duration
    projected_worker_seconds = math.fsum(estimates)
    return {
        "schema": f"{SCHEMA}-estimate",
        "workers": workers,
        "units": rows,
        "totals": {
            "anchors": sum(int(row["anchors"]) for row in rows),
            "unilateral_profiles": sum(int(row["unilateral_profiles"]) for row in rows),
            "joint_profiles": sum(int(row["joint_profiles"]) for row in rows),
            "nominal_profile_rows": total_profiles,
        },
        "basis": {
            "e1_unit_charged_worker_seconds": e1_worker_seconds,
            "e1_unit_charged_worker_seconds_hex": e1_worker_seconds.hex(),
            "seconds_per_e1_profile_row": seconds_per_profile,
            "method": "E1_AGGREGATE_UNIT_CHARGE_PROPORTIONAL_TO_RECORDED_PROFILE_ROWS_PLUS_LPT_SCHEDULING",
            "note": "Conservative directional estimate; probe skips Q inference and full tape serialization but adds nominal replay.",
        },
        "projected_worker_seconds": projected_worker_seconds,
        "projected_wall_seconds": max(loads),
        "projected_wall_minutes": max(loads) / 60.0,
        "worker_load_seconds": loads,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--estimate", action="store_true")
    mode.add_argument("--unit", metavar="WORLD:LINEAGE")
    mode.add_argument("--merge", action="store_true")
    parser.add_argument("--workers", type=int, default=12, help="estimate worker count (1..12)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        terminal = load_terminal(args.input_root)
        if args.estimate:
            print(json.dumps(estimate(input_root=args.input_root, terminal=terminal, workers=args.workers), sort_keys=True, indent=2))
            return 0
        e1, f1, snapshot_ops3_anchor = _pin_runtime()
        if args.unit:
            try:
                world_text, lineage_text = args.unit.split(":", 1)
                key = (int(world_text), int(lineage_text))
            except (AttributeError, ValueError) as error:
                raise ProbeError("--unit must be WORLD:LINEAGE") from error
            if key not in terminal_units(terminal):
                raise ProbeError("--unit is outside the authenticated E1 panel")
            path, reused = execute_unit(
                input_root=args.input_root, output_root=args.output_root,
                terminal=terminal, key=key, e1=e1, f1=f1,
                snapshot_ops3_anchor=snapshot_ops3_anchor,
            )
            print(json.dumps({"status": "COMPLETE", "path": str(path), "sha256": sha256_file(path), "reused": reused}, sort_keys=True))
            return 0
        result_path, table_path = merge(
            input_root=args.input_root, output_root=args.output_root, terminal=terminal
        )
        print(json.dumps({
            "status": "COMPLETE", "result": str(result_path),
            "result_sha256": sha256_file(result_path), "table": str(table_path),
            "table_sha256": sha256_file(table_path),
        }, sort_keys=True))
        return 0
    except ProbeError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
