#!/usr/bin/env python3
"""HCELL shared helpers.  DESIGN_PHASE_MEASUREMENT_NOT_A_CLAIM.

Learner-free.  Reads no checkpoint.  Imports the sealed V0.25 source tree and
the verified clean-path / crowding runners read-only; writes only under
/home/sat/mcrl-v025-hcell-ws.

Treatment H on the dense path
-----------------------------
The sealed ``StepEvaluator.evaluate_many`` takes its dense path only for the
label ``a-r0``; for ``a-rH`` it falls back to scalar ``evaluate``, which the
mandatory evaluator rule forbids.  H is, by the sealed design, a *rescore* of
the same integrated tape (``shared_computation_plan``: rescore_from_integrated_tape
includes "H"): joules, decoding time and PHY service are unchanged and only
useful bits/time inside each event blackout are removed.  This module applies
that removal to dense ``a-r0`` profiles using the sealed helpers themselves:

* ledger   : ``runner._interruption_events(incumbent, config, t0)``
* blackouts: ``integration._blackouts`` (62 ms beam change / cell rekey,
             142 ms satellite change, entries logged without blackout,
             per-user union, clipped to the step)
* removal  : ``integration._linear_integral`` on the first D2 subinterval,
             with boundary-0 and boundary-1 per-user rates taken from two
             single-boundary dense evaluations of the same configurations.

The KAT script (hcell_kat.py) checks this dense rescore against the sealed
scalar ``a-rH`` path per user.
"""

from __future__ import annotations

from collections import Counter
from fractions import Fraction
import gc
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import sys
import time

WORKSPACE = Path("/home/sat/mcrl-v025-hcell-ws")
SCRATCH = WORKSPACE / ".scratch/hcell"
CLEANPATH_RUNNER = Path("/home/sat/mcrl-v025-rank2-ws/.scratch/cleanpath/run_cleanpath.py")
CLEANPATH_RECEIPT = Path("/home/sat/mcrl-v025-rank2-ws/.scratch/cleanpath/cleanpath-receipt.json")
CROWD_RUNNER = Path("/home/sat/mcrl-v025-crowd-ws/.scratch/crowding-cost/run_crowding_cost.py")
CROWD_RECEIPT = Path("/home/sat/mcrl-v025-crowd-ws/.scratch/crowding-cost/crowding-cost-receipt.json")
PUBLISHED_RECEIPT = Path("/home/sat/mcrl-v025-rank-ws/.scratch/statics/statics-receipt.json")
PYTHON = "/home/sat/mcrl-leo-handover/.venv/bin/python"
THREAD_VARS = (
    "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
)
MAX_RSS_BYTES = 5_000_000_000
H_KINDS = ("beam_change", "satellite_change", "cell_rekey")
ALL_KINDS = ("unchanged", "beam_change", "satellite_change", "cell_rekey",
             "initial_entry", "reentry", "exit")
E_HO_VALUES_J = (3.0, 30.0, 130.0)

SCALAR_CALLS = {"count": 0}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_digest(payload: dict) -> str:
    unsigned = dict(payload)
    unsigned.pop("receipt_sha256", None)
    return hashlib.sha256(json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


def atomic_write(path: Path, payload: dict) -> None:
    payload["receipt_sha256"] = canonical_digest(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, sort_keys=True, indent=1, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def peak_rss_bytes() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def check_runtime() -> None:
    if sys.executable != PYTHON:
        raise RuntimeError(f"wrong interpreter: {sys.executable}")
    if os.getpriority(os.PRIO_PROCESS, 0) < 15:
        raise RuntimeError("niceness is below 15")
    bad = {n: os.environ.get(n) for n in THREAD_VARS if os.environ.get(n) != "1"}
    if bad:
        raise RuntimeError(f"thread pins are not all one: {bad}")
    if peak_rss_bytes() >= MAX_RSS_BYTES:
        raise MemoryError(f"peak RSS {peak_rss_bytes()} is not below 5 GB")


def runtime_record() -> dict:
    return {
        "python": sys.executable,
        "niceness": os.getpriority(os.PRIO_PROCESS, 0),
        "thread_pins": {n: os.environ.get(n) for n in THREAD_VARS},
        "peak_rss_bytes": peak_rss_bytes(),
    }


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class Context:
    pass


def setup(*, with_crowd: bool = True) -> Context:
    """Load the verified clean-path runner, its PANELCEIL helpers and pilot."""
    ctx = Context()
    ctx.cleanpath = load_module("hcell_cleanpath_reference", CLEANPATH_RUNNER)
    ctx.panel = ctx.cleanpath.load_panel()
    ctx.pilot = ctx.panel.load_pilot()          # sha-checked by PANELCEIL
    ctx.runner = ctx.pilot.ENGINE
    ctx.calibration = ctx.panel.load_calibration(ctx.pilot)
    ctx.run_setting = ctx.runner.run_setting_for("a-r0")
    ctx.crowd = load_module("hcell_crowd_reference", CROWD_RUNNER) if with_crowd else None
    from mcrl.physics_v025 import integration as integ
    from mcrl.physics_v025 import constants_v025 as constants
    ctx.integ = integ
    ctx.constants = constants
    ctx.D2 = float(constants.D2_MEASUREMENT_STEP_S)
    ctx.INTERVAL = float(constants.DECISION_INTERVAL_S)
    ctx.rate_target_bps = float(ctx.run_setting.rate_target_bps)
    ctx.sources = {
        "cleanpath_runner_sha256": sha256(CLEANPATH_RUNNER),
        "crowd_runner_sha256": sha256(CROWD_RUNNER),
        "pilot_sha256": sha256(ctx.panel.PILOT_PATH),
        "engine_sha256": sha256(
            ctx.panel.SOURCE_ROOT
            / ".scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py"
        ),
        "integration_sha256": sha256(ctx.panel.SOURCE_ROOT / "src/mcrl/physics_v025/integration.py"),
        "adapter_sha256": sha256(ctx.panel.SOURCE_ROOT / "src/mcrl/physics_v025/adapter.py"),
        "batch_sha256": sha256(ctx.panel.SOURCE_ROOT / "src/mcrl/physics_v025/batch.py"),
        "targets_sha256": sha256(ctx.panel.SOURCE_ROOT / "src/mcrl/physics_v025/targets.py"),
        "constants_sha256": sha256(ctx.panel.SOURCE_ROOT / "src/mcrl/physics_v025/constants_v025.py"),
        "hcell_common_sha256": sha256(Path(__file__)),
    }
    ctx.interruption_constants = {
        "SAME_SATELLITE_INTERRUPTION_S": float(constants.SAME_SATELLITE_INTERRUPTION_S),
        "SATELLITE_CHANGE_INTERRUPTION_S": float(constants.SATELLITE_CHANGE_INTERRUPTION_S),
        "D2_MEASUREMENT_STEP_S": ctx.D2,
        "DECISION_INTERVAL_S": ctx.INTERVAL,
    }
    return ctx


def frozen_panel(ctx) -> list[dict]:
    published = json.loads(PUBLISHED_RECEIPT.read_text(encoding="utf-8"))
    if published.get("status") != "COMPLETE":
        raise RuntimeError("published static receipt is not complete")
    if published.get("receipt_sha256") != ctx.cleanpath.canonical_digest(published):
        raise RuntimeError("published static receipt digest failed")
    frozen = published["panel"]
    if len(frozen) != 12 or [int(r["global_anchor_index"]) for r in frozen] != list(range(12)):
        raise RuntimeError("frozen panel is not the 12 declared development anchors")
    for row in frozen:
        if row["world_id"] != "V025_PROBE/world/1" or int(row["world_index"]) != 1:
            raise RuntimeError("panel row outside development world 1")
    return frozen


def build_tape(ctx):
    from mcrl.physics_v025.provider_legacy import LegacyWorldProvider
    from mcrl.physics_v025.tapes import build_world_tape
    started = time.perf_counter()
    tape = build_world_tape(
        domain=ctx.pilot.TRAIN_WORLDS[0],
        provider=LegacyWorldProvider(role="pilot-source"),
        steps=33, start_time_s=0.0,
    )
    seconds = time.perf_counter() - started
    if tape.domain != "V025_PROBE/world/1":
        raise RuntimeError(f"unexpected tape domain {tape.domain}")
    return tape, {"domain": tape.domain, "seed": tape.seed, "digest": tape.digest,
                  "construction_seconds": seconds}


def install_scalar_stub(runner) -> None:
    """Replace StepEvaluator.evaluate class-wide with a counting, raising stub."""
    original = runner.StepEvaluator.evaluate

    def forbidden(*args, **kwargs):
        del args, kwargs
        SCALAR_CALLS["count"] += 1
        raise AssertionError("scalar StepEvaluator.evaluate is forbidden on the HCELL measured surface")

    forbidden.__name__ = "hcell_scalar_evaluate_forbidden"
    forbidden.__wrapped__ = original
    runner.StepEvaluator.evaluate = forbidden
    assert runner.StepEvaluator.evaluate is forbidden


def fresh_evaluator(ctx, tape, step_index, incumbent, *, field, boundaries):
    runner = ctx.runner
    return runner.StepEvaluator(
        tape, runner._setting("a-r0"), step_index,
        transition_from=incumbent,
        cell_rekeyed_users=runner._rekeyed_users(tape, step_index),
        field=field, counter=runner.EvaluationCounter(),
        run_setting=ctx.run_setting, boundary_indices=boundaries,
    )


def event_census(ctx, tape, step_index, incumbent, config) -> dict:
    events = ctx.runner._physical_events(
        incumbent, config, cell_rekeyed_users=ctx.runner._rekeyed_users(tape, step_index)
    )
    counts = Counter(event.kind for event in events)
    out = {kind: int(counts.get(kind, 0)) for kind in ALL_KINDS}
    out["h_events"] = sum(out[k] for k in H_KINDS)
    return out


def h_ledger(ctx, tape, step_index, incumbent, config):
    return ctx.runner._interruption_events(
        incumbent, config, 0.0,
        cell_rekeyed_users=ctx.runner._rekeyed_users(tape, step_index),
    )


def h_removal_endpoint(ctx, ledger, rate0, rate1, dec0, dec1):
    """Per-user removed bits and useful seconds on the full-48 tape.

    rate0/rate1: per-user rates (bit/s) at boundaries 0 and 1 (t0, t0+0.640 s).
    dec0/dec1  : per-user decoding indicator at those boundaries.
    Events sit at the decision instant t0 = 0 (relative clock).
    """
    blackouts, log = ctx.integ._blackouts(ledger, start_s=0.0, end_s=ctx.INTERVAL)
    kind_of = {}
    for event in log:
        if event.kind in ("initial_entry", "reentry"):
            continue
        if event.user_id in kind_of:
            raise RuntimeError("more than one interrupting event for one user in one step")
        kind_of[event.user_id] = event.kind
    removed_bits, removed_useful = {}, {}
    for user, intervals in blackouts.items():
        bits_parts, time_parts = [], []
        for low, high in intervals:
            if high > ctx.D2 + 1e-12:
                raise RuntimeError("blackout extends beyond the first D2 subinterval")
            cut_low, cut_high = max(0.0, low), min(ctx.D2, high)
            if cut_high > cut_low:
                bits_parts.append(ctx.integ._linear_integral(
                    rate0[user], rate1[user], 0.0, ctx.D2, cut_low, cut_high))
                time_parts.append(ctx.integ._linear_integral(
                    float(dec0[user]), float(dec1[user]), 0.0, ctx.D2, cut_low, cut_high))
        removed_bits[user] = math.fsum(bits_parts)
        removed_useful[user] = math.fsum(time_parts)
    by_kind = Counter()
    for user, value in removed_bits.items():
        by_kind[kind_of[user]] += value
    return removed_bits, removed_useful, {
        "blackout_users": len(blackouts),
        "logged_events": len(log),
        "removed_bits_by_kind": {k: float(by_kind.get(k, 0.0)) for k in
                                 ("same_satellite_beam_change", "satellite_change")},
    }


def h_removal_snapshot(ctx, ledger, per_user_bits_snapshot) -> float:
    """Zero-order-hold analogue for a one-boundary snapshot evaluator.

    A single-boundary dense profile holds the boundary-0 rate for 30.08 s, so
    rate = bits / 30.08 and the removed bits are rate x blackout length.
    """
    blackouts, _log = ctx.integ._blackouts(ledger, start_s=0.0, end_s=ctx.INTERVAL)
    parts = []
    for user, intervals in blackouts.items():
        rate = float(per_user_bits_snapshot[user]) / ctx.INTERVAL
        for low, high in intervals:
            parts.append(rate * (high - low))
    return math.fsum(parts)


def per_user_rates(ctx, profile):
    bits = profile.score.bits
    dec = profile.score.decoding_time_s
    return ({u: float(v) / ctx.INTERVAL for u, v in bits.items()},
            {u: float(v) > 0.0 for u, v in dec.items()})


def attained_count(ctx, per_user_bits) -> int:
    threshold = ctx.rate_target_bps * (47 * ctx.D2)
    return sum(1 for v in per_user_bits.values() if v >= threshold)


def cell_metrics(ctx, profile, removed_bits=None) -> dict:
    """a0 metrics, or aH metrics when removed_bits is supplied."""
    per_user = {u: float(v) for u, v in profile.score.bits.items()}
    if removed_bits is not None:
        per_user = {u: v - float(removed_bits.get(u, 0.0)) for u, v in per_user.items()}
    served = sum(1 for v in profile.score.served_phy.values() if v)
    return {
        "bits": math.fsum(per_user.values()),
        "joules": float(profile.joules),
        "served_count": served,
        "rate_target_attained_count": attained_count(ctx, per_user),
        "user_count": len(per_user),
    }


def pool_rows(rows) -> dict:
    bits = math.fsum(float(r["bits"]) for r in rows)
    joules = math.fsum(float(r["joules"]) for r in rows)
    return {
        "bits": bits,
        "joules": joules,
        "ee_mbit_per_j": bits / joules / 1e6,
        "served_count": sum(int(r["served_count"]) for r in rows),
        "rate_target_attained_count": sum(int(r["rate_target_attained_count"]) for r in rows),
        "user_count": sum(int(r["user_count"]) for r in rows),
    }


def eho_ee(bits: float, joules: float, events: int, e_ho: float) -> float:
    return bits / (joules + events * e_ho) / 1e6
