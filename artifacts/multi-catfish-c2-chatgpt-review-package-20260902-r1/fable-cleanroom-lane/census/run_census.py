#!/usr/bin/env python3
"""H-A deterministic hold-horizon focal segment-timing surplus census.

Read-only diagnostic.  Writes nothing into the repository; all outputs go
under the session scratchpad.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

REPO = Path("/home/u24/papers/mcrl-leo-handover")
HERE = REPO / ".scratch" / "c3-v04"
SCRATCH = Path(
    "/tmp/claude-1000/-home-u24-papers-mcrl-leo-handover/"
    "d47a2ac0-70e1-49ca-b412-995b22bcb231/scratchpad/census"
)
for _p in (HERE, REPO, REPO / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import run_v04_five_arm_ablation as five  # noqa: E402
import run_v04_c3_500_update_screen as screen  # noqa: E402
import run_v04_c3_source as c3source  # noqa: E402

from mcrl.env.antenna import transmit_gain_linear  # noqa: E402
from mcrl.env.geometry import angle_between_deg  # noqa: E402
from mcrl.env.link_budget import (  # noqa: E402
    BASEBAND_POWER_PER_SATELLITE_W,
    CIRCUIT_POWER_PER_BEAM_W,
    link_power_factor,
    pa_efficiency,
)
from mcrl.env.step import _RX_GAIN_MAX_LINEAR  # noqa: E402
from mcrl.env.tle import TleArchive  # noqa: E402
from mcrl.runtime.ee_axis_state import encode_ee_axis_state  # noqa: E402
from mcrl.runtime.ee_axis_v04_c3_state import encode_ee_axis_v04_c3_state  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402

NUM_ACTIONS = 28
HORIZON = 3
LAMBDA0 = c3source.LAMBDA_BITS_PER_J
LAMBDA0_SOURCE = f"{HERE / 'run_v04_c3_source.py'}:102 LAMBDA_BITS_PER_J"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def psup(power):
    p = np.asarray(power, dtype=np.float64)
    xi = pa_efficiency(np.maximum(p, 0.0))
    return np.where(p > 0.0, p / np.where(xi > 0.0, xi, 1.0), 0.0)


def satellite_table(driver, offset, norad_ids):
    positions = driver.satellite_ecef_at(int(offset))
    unique = np.unique(norad_ids[norad_ids >= 0])
    table = np.full((unique.size + 1, 3), np.nan, dtype=np.float64)
    flat = np.full(norad_ids.shape, unique.size, dtype=np.int64)
    for slot, norad in enumerate(unique.tolist()):
        pos = positions.get(int(norad))
        if pos is not None:
            table[slot] = np.asarray(pos, dtype=np.float64)
        flat[norad_ids == norad] = slot
    return table[flat]


def geometry_at(driver, offset, norad_ids, cell_ids, user_ecef, centres):
    sat = satellite_table(driver, offset, norad_ids)
    present = (norad_ids >= 0) & (cell_ids >= 0) & np.isfinite(sat).all(axis=-1)
    safe_cells = np.where(cell_ids >= 0, cell_ids, 0)
    beam = centres[safe_cells]
    theta = angle_between_deg(np.where(present[..., None], sat, 0.0), beam,
                              np.broadcast_to(user_ecef[:, None, :], sat.shape))
    gain = np.where(present, transmit_gain_linear(np.where(present, theta, 0.0)), 0.0)
    delta = np.where(present[..., None], sat, np.nan) - user_ecef[:, None, :]
    slant = np.linalg.norm(delta, axis=-1)
    up = user_ecef / np.maximum(np.linalg.norm(user_ecef, axis=1, keepdims=True), 1e-12)
    sin_el = np.sum(delta * up[:, None, :], axis=-1) / np.maximum(slant, 1e-12)
    elev = np.degrees(np.arcsin(np.clip(sin_el, -1.0, 1.0)))
    path = np.where(
        present,
        link_power_factor(
            np.where(present, slant, 1.0),
            np.where(present, elev, 0.0),
            np.full(slant.shape, _RX_GAIN_MAX_LINEAR),
            shadow_fading_db=0.0,
        ),
        0.0,
    )
    return {
        "theta": np.where(present, theta, np.nan),
        "gain": gain,
        "path": path,
        "present": present,
        "sat": sat,
    }


def frozen_context(outcome, norad_ids, cell_ids, users):
    n_a = np.zeros(norad_ids.shape, dtype=np.float64)
    m_a = np.zeros(norad_ids.shape, dtype=np.float64)
    sat_active = np.zeros(norad_ids.shape, dtype=bool)
    if outcome is None:
        return n_a, m_a, sat_active
    served = np.asarray(outcome.resolution.served, dtype=bool)
    sat = np.asarray(outcome.resolution.serving_satellite, dtype=np.int64)
    cell = np.asarray(outcome.resolution.serving_cell, dtype=np.int64)
    power = np.asarray(outcome.link_power_w, dtype=np.float64)
    beam_users: dict[tuple[int, int], list[tuple[float, int]]] = {}
    sat_users: dict[int, int] = {}
    for uid in range(users):
        if not served[uid]:
            continue
        key = (int(sat[uid]), int(cell[uid]))
        beam_users.setdefault(key, []).append((float(power[uid]), uid))
        sat_users[int(sat[uid])] = sat_users.get(int(sat[uid]), 0) + 1
    for uid in range(users):
        own_key = (int(sat[uid]), int(cell[uid])) if served[uid] else None
        own_sat = int(sat[uid]) if served[uid] else None
        for action in range(NUM_ACTIONS):
            norad = int(norad_ids[uid, action])
            cid = int(cell_ids[uid, action])
            if norad < 0 or cid < 0:
                continue
            key = (norad, cid)
            entries = beam_users.get(key, ())
            if own_key is not None and key == own_key:
                rest = [value for value, other in entries if other != uid]
            else:
                rest = [value for value, _ in entries]
            n_a[uid, action] = len(rest)
            m_a[uid, action] = max(rest) if rest else 0.0
            scount = sat_users.get(norad, 0)
            if own_sat is not None and norad == own_sat:
                scount -= 1
            sat_active[uid, action] = scount > 0
    return n_a, m_a, sat_active


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worlds", type=int, default=6)
    parser.add_argument("--lineages", type=int, default=3)
    parser.add_argument("--out", type=str, default="census-raw.npz")
    args = parser.parse_args()

    started = time.perf_counter()
    seeds = [2026090211 + offset for offset in range(6)][: args.worlds]
    lineages = list(five.INITIALIZATION_SEEDS)[: args.lineages]
    print(f"[census] worlds={seeds} lineages={lineages}", flush=True)

    receipt = screen.authenticate_gate(
        five.DEFAULT_GATE_DIR, source_dir=None, prereg_path=five.DEFAULT_PREREG
    )
    checkpoint_sha: dict[str, str] = {}
    for seed in lineages:
        path = Path(receipt["selected_hybrid_paths"][str(seed)])
        checkpoint_sha[str(path)] = file_sha256(path)
        v03 = Path(five.DEFAULT_V03_ROOT) / "checkpoints" / f"init-{seed}-rung-000010.pt"
        checkpoint_sha[str(v03)] = file_sha256(v03)
    print(f"[census] recorded SHA-256 for {len(checkpoint_sha)} checkpoint files", flush=True)

    record = read_prereg(five.DEFAULT_PREREG)
    view = SCRATCH / "frozen-tle"
    t0 = time.perf_counter()
    if view.exists():
        archive, reused = TleArchive(view), True
    else:
        archive, reused = screen._frozen_archive(record, five.DEFAULT_TLE_ROOT, view), False
    print(f"[census] archive ready {time.perf_counter()-t0:.1f}s reused={reused}", flush=True)

    trainers = {}
    for seed in lineages:
        trainer = screen.load_gate_selected_hybrid(
            receipt, v03_root=five.DEFAULT_V03_ROOT, initialization_seed=seed
        )
        five._prepare_hybrid(trainer)
        trainers[seed] = trainer
    kappa_bits = float(trainers[lineages[0]].v04_config.kappa_bits)
    print(f"[census] kappa_bits={kappa_bits!r} lambda0={LAMBDA0!r}", flush=True)

    keys_scalar = (
        "world", "lineage", "step", "user", "n_legal", "a_taken", "a_incumbent",
        "empty_mask", "prev_served", "served_now", "taken_pred_power",
        "taken_norad", "taken_cell", "served_norad", "served_cell",
        "realized_link_power", "taken_start", "taken_continues",
    )
    keys_action = (
        "legal", "zeta2", "rate_part", "energy_part", "zeta2_full", "hold_h",
        "q1", "q3", "start_gain", "n_a", "m_a", "sat_active", "gamma0",
        "sinr_zero", "geom_ok", "continuing",
    )
    keys_k = ("gain_ratio", "feasible")
    store: dict[str, list] = {key: [] for key in keys_scalar + keys_action + keys_k}
    diagnostics = {
        "sat_ecef_k0_max_dev_km": 0.0,
        "gain_k0_max_rel_dev": 0.0,
        "step_index_mismatch": 0,
        "nonfinite_zeta2": 0,
    }

    total = len(lineages) * len(seeds)
    done = 0
    for lineage in lineages:
        trainer = trainers[lineage]
        for world in seeds:
            done += 1
            t_ep = time.perf_counter()
            environment = screen._make_environment(archive, users=100)
            environment.environment._fading_field = five._field_for_seed(world)
            env_rng, mobility_rng, _a, _c = screen._evaluation_rngs(world)
            _s, _m, observation = environment.reset(env_rng, mobility_rng)
            step_env = environment.environment
            driver = step_env.driver
            interval_s = float(driver.config.ephemeris.time_step_s)
            centres = np.asarray(driver.grid.centers_ecef_km, dtype=np.float64)
            physics = step_env.physics
            p0 = float(physics.segment_start_power_w)
            pmax = float(physics.beam_power_max_w)
            bandwidth = float(physics.beam_bandwidth_hz)
            users = int(step_env.num_users)
            prev_outcome = None

            with torch.no_grad():
                for step in range(int(driver.config.steps_per_episode)):
                    if int(observation.step_index) != step:
                        diagnostics["step_index_mismatch"] += 1
                    legacy = encode_ee_axis_state(step_env, observation)
                    v04 = encode_ee_axis_v04_c3_state(
                        step_env, observation, interval_s=interval_s,
                        kappa_bits=kappa_bits,
                    )
                    masks = np.asarray(v04.action_masks, dtype=bool)
                    q1, _q2, q3 = trainer.q_values_by_route(
                        np.asarray(legacy.state_matrix),
                        np.asarray(v04.state_matrix), masks,
                    )
                    candidates = observation.candidates
                    norad_ids = np.stack(
                        [t.norad_ids for t in candidates.slot_tables]
                    ).astype(np.int64)
                    cell_ids = np.stack(
                        [t.cell_ids for t in candidates.slot_tables]
                    ).astype(np.int64)
                    user_ecef = np.asarray(driver.user_ecef_km(), dtype=np.float64)
                    geoms = [
                        geometry_at(driver, k, norad_ids, cell_ids, user_ecef, centres)
                        for k in range(HORIZON + 1)
                    ]
                    g0 = geoms[0]["gain"]
                    path0 = geoms[0]["path"]
                    present0 = geoms[0]["present"]

                    window = np.asarray(candidates.window_satellite_ecef_km)
                    slot_of = np.repeat(np.arange(4), 7)[None, :]
                    ref = window[np.arange(users)[:, None], slot_of, :]
                    finite = np.isfinite(ref).all(axis=-1) & geoms[0]["present"]
                    if finite.any():
                        dev = np.linalg.norm(
                            geoms[0]["sat"][finite] - ref[finite], axis=-1
                        ).max()
                        diagnostics["sat_ecef_k0_max_dev_km"] = max(
                            diagnostics["sat_ecef_k0_max_dev_km"], float(dev))
                    off_flat = np.asarray(candidates.off_axis_deg).reshape(users, -1)
                    gain_ref = np.where(
                        np.isfinite(off_flat),
                        transmit_gain_linear(np.where(np.isfinite(off_flat), off_flat, 0.0)),
                        0.0,
                    )
                    both = masks & (gain_ref > 0)
                    if both.any():
                        rel = np.abs(g0[both] - gain_ref[both]) / gain_ref[both]
                        diagnostics["gain_k0_max_rel_dev"] = max(
                            diagnostics["gain_k0_max_rel_dev"], float(rel.max()))

                    segments = step_env._segments
                    prev_assoc = step_env._previous_association
                    seg_norad = np.full(users, -1, dtype=np.int64)
                    seg_cell = np.full(users, -1, dtype=np.int64)
                    seg_gain = np.zeros(users, dtype=np.float64)
                    for uid in range(users):
                        seg = segments[uid]
                        if seg is not None and prev_assoc[uid] is not None:
                            seg_norad[uid] = seg.norad_id
                            seg_cell[uid] = seg.cell_id
                            seg_gain[uid] = float(seg.start_transmit_gain)
                    continuing = (
                        (norad_ids == seg_norad[:, None])
                        & (cell_ids == seg_cell[:, None])
                        & (seg_norad[:, None] >= 0)
                    )
                    start = np.where(continuing, seg_gain[:, None], g0)

                    incumbent = np.full(users, -1, dtype=np.int64)
                    for uid in range(users):
                        prev = prev_assoc[uid]
                        if prev is None:
                            continue
                        hit = np.flatnonzero(
                            (norad_ids[uid] == prev.norad_id)
                            & (cell_ids[uid] == prev.cell_id) & masks[uid])
                        if hit.size:
                            incumbent[uid] = int(hit[0])

                    gk = np.stack([geoms[k]["gain"] for k in range(1, HORIZON + 1)])
                    pathk = np.stack([geoms[k]["path"] for k in range(1, HORIZON + 1)])
                    presentk = np.stack(
                        [geoms[k]["present"] for k in range(1, HORIZON + 1)])
                    geom_ok = presentk.all(axis=0) & present0 & (g0 > 0)
                    safe_gk = np.where(gk > 0, gk, np.nan)
                    p_hold = p0 * start[None] / safe_gk
                    feasible = np.isfinite(p_hold) & (p_hold <= pmax)
                    alive = np.cumprod(feasible.astype(np.int64), axis=0).astype(bool)
                    hold_h = alive.sum(axis=0)

                    gamma0 = np.asarray(observation.candidate_sinr, dtype=np.float64)
                    sinr_zero = masks & ~(gamma0 > 0)
                    safe_path0 = np.where(path0 > 0, path0, np.nan)
                    safe_gamma = np.where(gamma0 > 0, gamma0, np.nan)
                    in_plus_n = p0 * g0 * safe_path0 / safe_gamma
                    sinr_k = (p0 * start[None] * pathk) / in_plus_n[None]
                    n_a, m_a, sat_active = frozen_context(
                        prev_outcome, norad_ids, cell_ids, users)
                    rate_k = (bandwidth / (n_a[None] + 1.0)) * np.log2(
                        1.0 + np.maximum(np.nan_to_num(sinr_k, nan=0.0), 0.0))

                    base = psup(m_a)
                    p_for_power = np.where(np.isfinite(p_hold), p_hold, 0.0)
                    marginal = psup(np.maximum(m_a[None], p_for_power)) - base[None]
                    activation = (n_a == 0).astype(np.float64) * (
                        CIRCUIT_POWER_PER_BEAM_W
                        + (~sat_active).astype(np.float64)
                        * BASEBAND_POWER_PER_SATELLITE_W)
                    power_k = marginal + activation[None]

                    rate_term = interval_s * np.where(alive, rate_k, 0.0)
                    energy_term = LAMBDA0 * interval_s * np.where(alive, power_k, 0.0)
                    rate_full = interval_s * rate_k
                    energy_full = LAMBDA0 * interval_s * power_k
                    legal = masks & geom_ok
                    zeta2 = np.where(legal, (rate_term - energy_term).sum(axis=0), 0.0)
                    zeta2_full = np.where(
                        legal, (rate_full - energy_full).sum(axis=0), 0.0)
                    diagnostics["nonfinite_zeta2"] += int(
                        (~np.isfinite(zeta2[legal])).sum())

                    scores = q1 + q3
                    eligible = masks.any(axis=1)
                    a_taken = np.full(users, -1, dtype=np.int64)
                    a_taken[eligible] = np.argmax(
                        np.where(masks[eligible], scores[eligible], -np.inf), axis=1)
                    actions = np.where(a_taken >= 0, a_taken, five.NO_OP_ACTION)

                    idx = np.arange(users)
                    safe_a = np.clip(a_taken, 0, None)
                    ok = a_taken >= 0
                    taken_start = np.where(ok, start[idx, safe_a], np.nan)
                    taken_g1 = np.where(ok, gk[0][idx, safe_a], np.nan)
                    taken_pred = p0 * taken_start / np.where(taken_g1 > 0, taken_g1, np.nan)
                    taken_norad = np.where(ok, norad_ids[idx, safe_a], -1)
                    taken_cell = np.where(ok, cell_ids[idx, safe_a], -1)
                    taken_cont = np.where(ok, continuing[idx, safe_a], False)

                    prev_served = (
                        np.asarray(prev_outcome.resolution.served, dtype=bool)
                        if prev_outcome is not None else np.zeros(users, dtype=bool))

                    result = environment.step(actions, env_rng)
                    outcome = environment.last_outcome
                    served_now = np.asarray(outcome.resolution.served, dtype=bool)

                    store["world"].append(np.full(users, world, dtype=np.int64))
                    store["lineage"].append(np.full(users, lineage, dtype=np.int64))
                    store["step"].append(np.full(users, step, dtype=np.int64))
                    store["user"].append(idx.copy())
                    store["n_legal"].append(legal.sum(axis=1).astype(np.int64))
                    store["a_taken"].append(a_taken)
                    store["a_incumbent"].append(incumbent)
                    store["empty_mask"].append(~eligible)
                    store["prev_served"].append(prev_served)
                    store["served_now"].append(served_now)
                    store["taken_pred_power"].append(taken_pred)
                    store["taken_norad"].append(taken_norad.astype(np.int64))
                    store["taken_cell"].append(taken_cell.astype(np.int64))
                    store["taken_start"].append(taken_start)
                    store["taken_continues"].append(taken_cont.astype(bool))
                    store["served_norad"].append(
                        np.asarray(outcome.resolution.serving_satellite, dtype=np.int64))
                    store["served_cell"].append(
                        np.asarray(outcome.resolution.serving_cell, dtype=np.int64))
                    store["realized_link_power"].append(
                        np.asarray(outcome.link_power_w, dtype=np.float64))
                    store["legal"].append(legal)
                    store["zeta2"].append(zeta2)
                    store["rate_part"].append(
                        np.where(legal, rate_term.sum(axis=0), 0.0))
                    store["energy_part"].append(
                        np.where(legal, energy_term.sum(axis=0), 0.0))
                    store["zeta2_full"].append(zeta2_full)
                    store["hold_h"].append(np.where(legal, hold_h, -1).astype(np.int64))
                    store["q1"].append(np.asarray(q1, dtype=np.float64))
                    store["q3"].append(np.asarray(q3, dtype=np.float64))
                    store["start_gain"].append(start)
                    store["n_a"].append(n_a)
                    store["m_a"].append(m_a)
                    store["sat_active"].append(sat_active)
                    store["gamma0"].append(gamma0)
                    store["sinr_zero"].append(sinr_zero)
                    store["geom_ok"].append(geom_ok)
                    store["continuing"].append(continuing)
                    store["gain_ratio"].append(
                        np.moveaxis(np.where(
                            (g0[None] > 0) & presentk,
                            gk / np.where(g0[None] > 0, g0[None], np.nan), np.nan), 0, -1))
                    store["feasible"].append(np.moveaxis(feasible, 0, -1))

                    prev_outcome = outcome
                    if result.done:
                        break
                    observation = outcome.observation

            print(f"[census] episode {done}/{total} lineage={lineage} "
                  f"world={world} {time.perf_counter()-t_ep:.1f}s", flush=True)

    packed = {key: np.concatenate(value, axis=0) for key, value in store.items()}
    packed["_lambda0"] = np.array([LAMBDA0])
    packed["_kappa_bits"] = np.array([kappa_bits])
    packed["_interval_s"] = np.array([interval_s])
    np.savez_compressed(SCRATCH / args.out, **packed)
    meta = {
        "worlds": seeds,
        "lineages": lineages,
        "lambda0": LAMBDA0,
        "lambda0_hex": LAMBDA0.hex(),
        "lambda0_source": LAMBDA0_SOURCE,
        "kappa_bits": kappa_bits,
        "kappa_bits_hex": float(kappa_bits).hex(),
        "interval_s": interval_s,
        "checkpoint_sha256": checkpoint_sha,
        "diagnostics": diagnostics,
        "elapsed_s": time.perf_counter() - started,
        "anchors": int(packed["user"].shape[0]),
    }
    (SCRATCH / "census-meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2)[:2000], flush=True)
    print(f"[census] total {time.perf_counter()-started:.1f}s", flush=True)


if __name__ == "__main__":
    main()
