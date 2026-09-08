"""Read-only StepEnvironment extractor and clean-room differential harness."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
from types import MethodType
from typing import Any

import numpy as np

from mcrl.env.action_contract import NO_OP_ACTION, NUM_BEAM_SLOTS
from mcrl.env.ephemeris import BlockAlternatingSplit, EpisodeStartSampler, TRAIN
from mcrl.env.keyed_fading import KeyedFadingField
from mcrl.env.mobility import MobilityConfig
from mcrl.env.reference_policy import REFERENCE_POLICY_NAMES, build_reference_policy
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.step import PhysicsConfig, StepEnvironment
from mcrl.env.tle import TleArchive

import reference_physics as ref


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TLE_ROOT = Path("~/demo/tle_data/starlink/tle").expanduser()
WORLD_DOMAINS = tuple(f"DIFF_AUDIT/world/{index}" for index in range(1, 4))
WORLD_MASK = (1 << 63) - 1
WORLD_SEEDS = tuple(
    int.from_bytes(hashlib.sha256(domain.encode("ascii")).digest()[:8], "big")
    & WORLD_MASK
    for domain in WORLD_DOMAINS
)
POLICIES = ("stay-if-possible", "nearest-eligible", "random-masked")


def _angle(vertex: np.ndarray, first: np.ndarray, second: np.ndarray) -> np.ndarray:
    a = np.asarray(first, dtype=float) - np.asarray(vertex, dtype=float)
    b = np.asarray(second, dtype=float) - np.asarray(vertex, dtype=float)
    a /= np.maximum(np.linalg.norm(a, axis=-1, keepdims=True), 1e-12)
    b /= np.maximum(np.linalg.norm(b, axis=-1, keepdims=True), 1e-12)
    return np.degrees(np.arccos(np.clip(np.sum(a * b, axis=-1), -1.0, 1.0)))


def _look(sat: np.ndarray, users: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    delta = np.asarray(sat, dtype=float) - np.asarray(users, dtype=float)
    slant = np.linalg.norm(delta, axis=-1)
    up = np.asarray(users, dtype=float) / np.maximum(
        np.linalg.norm(users, axis=-1, keepdims=True), 1e-12
    )
    elevation = np.degrees(
        np.arcsin(
            np.clip(
                np.sum(delta * up, axis=-1) / np.maximum(slant, 1e-12),
                -1.0,
                1.0,
            )
        )
    )
    return slant, elevation


def _satellite_positions(decision: Any) -> dict[int, np.ndarray]:
    result: dict[int, np.ndarray] = {}
    for uid in range(decision.window_norad_ids.shape[0]):
        for slot in range(decision.window_norad_ids.shape[1]):
            norad = int(decision.window_norad_ids[uid, slot])
            if norad >= 0 and norad not in result:
                result[norad] = np.asarray(
                    decision.window_satellite_ecef_km[uid, slot], dtype=float
                )
    return result


class ReadOnlyExtractor:
    """Capture private intermediates without changing their values or control flow."""

    def __init__(self, environment: StepEnvironment) -> None:
        self.environment = environment
        self.physics: dict[str, Any] | None = None
        self.fading: dict[int, np.ndarray] = {}
        self.shadow: dict[int, np.ndarray] = {}
        original_resolve = environment._resolve_physics
        original_draw = environment._draw_fading

        def draw(_instance: StepEnvironment, *args: Any, **kwargs: Any):
            fading, shadow = original_draw(*args, **kwargs)
            if kwargs.get("event", "direct") == "physics":
                self.fading = {int(k): np.array(v, copy=True) for k, v in fading.items()}
                self.shadow = {int(k): np.array(v, copy=True) for k, v in shadow.items()}
            return fading, shadow

        def resolve(
            _instance: StepEnvironment, decision: Any, actions: np.ndarray, rng: np.random.Generator
        ):
            payload = original_resolve(decision, actions, rng)
            self.physics = {
                key: np.array(value, copy=True) if isinstance(value, np.ndarray) else value
                for key, value in payload.items()
            }
            return payload

        environment._draw_fading = MethodType(draw, environment)  # type: ignore[method-assign]
        environment._resolve_physics = MethodType(resolve, environment)  # type: ignore[method-assign]


def _metric_array_by_key(
    keys: list[tuple[int, int]], values: np.ndarray, union: list[tuple[int, int]]
) -> np.ndarray:
    lookup = {key: float(value) for key, value in zip(keys, values, strict=True)}
    return np.array([lookup.get(key, 0.0) for key in union], dtype=float)


def _reference_step(
    environment: StepEnvironment,
    decision: Any,
    actions: np.ndarray,
    fading: dict[int, np.ndarray],
    shadow: dict[int, np.ndarray],
    segments: list[tuple[int, int, float] | None],
    previous_associations: list[tuple[int, int] | None],
    step_index: int,
    user_ecef: np.ndarray,
    pending_age: np.ndarray | None,
    historical: dict[tuple[int, int], np.ndarray],
) -> dict[str, Any]:
    users = environment.num_users
    grid = environment.driver.grid
    user_ecef = np.asarray(user_ecef, dtype=float)
    satellite = _satellite_positions(decision)

    associations: list[tuple[int, int] | None] = []
    theta = np.zeros(users, dtype=float)
    for uid, action_raw in enumerate(actions):
        action = int(action_raw)
        if action == NO_OP_ACTION:
            associations.append(None)
            continue
        slot, beam = divmod(action, NUM_BEAM_SLOTS)
        association = decision.slot_tables[uid].association(action)
        associations.append((int(association.norad_id), int(association.cell_id)))
        theta[uid] = float(decision.off_axis_deg[uid, slot, beam])

    gain = np.where(
        np.array([association is not None for association in associations]),
        ref.transmit_pattern_gain(theta),
        0.0,
    )
    link_power = np.zeros(users, dtype=float)
    proposed_segments: list[tuple[int, int, float] | None] = [None] * users
    for uid, association in enumerate(associations):
        if association is None or gain[uid] <= 0.0:
            continue
        segment = segments[uid]
        continuing = (
            segment is not None
            and segment[:2] == association
            and previous_associations[uid] is not None
        )
        if continuing:
            start_gain = float(segment[2])
        else:
            start_gain = float(gain[uid])
            if step_index == 0 and pending_age is not None:
                age = int(pending_age[uid])
                position = historical.get((age, association[0]))
                if age > 0 and position is not None:
                    historical_angle = float(
                        _angle(
                            position,
                            grid.centers_ecef_km[association[1]],
                            user_ecef[uid],
                        )
                    )
                    historical_gain = float(ref.transmit_pattern_gain(historical_angle))
                    if historical_gain > 0.0:
                        start_gain = historical_gain
        link_power[uid] = float(ref.segment_link_power_w(start_gain, gain[uid]))
        proposed_segments[uid] = (association[0], association[1], start_gain)

    chosen = np.array([association is not None for association in associations])
    feasible = ref.feasible_power(link_power) & (gain > 0.0)
    served = chosen & feasible
    for uid in range(users):
        segments[uid] = proposed_segments[uid] if served[uid] else None
        previous_associations[uid] = associations[uid] if served[uid] else None

    beam_keys = sorted({associations[uid] for uid in range(users) if served[uid]})
    beam_keys = [key for key in beam_keys if key is not None]
    served_keys = [associations[uid] for uid in range(users) if served[uid]]
    beam_power_map = ref.per_beam_power_w(link_power[served], served_keys)  # type: ignore[arg-type]
    beam_power = np.array([beam_power_map[key] for key in beam_keys], dtype=float)

    if beam_keys:
        beam_sat = np.stack([satellite[key[0]] for key in beam_keys])
        beam_cell = np.stack([grid.centers_ecef_km[key[1]] for key in beam_keys])
        off_axis = _angle(
            beam_sat[None, :, :], beam_cell[None, :, :], user_ecef[:, None, :]
        )
        transmit = ref.transmit_pattern_gain(off_axis)
        slant, elevation = _look(beam_sat[None, :, :], user_ecef[:, None, :])
        fading_matrix = np.stack([fading[key[0]] for key in beam_keys], axis=1)
        shadow_matrix = np.stack([shadow[key[0]] for key in beam_keys], axis=1)
        path_without_receive = (
            10.0 ** (-ref.total_path_loss_db(slant, elevation, shadow_matrix) / 10.0)
            * fading_matrix
        )
        serving_sat = np.array(
            [association[0] if association is not None and served[uid] else -1 for uid, association in enumerate(associations)]
        )
        serving_cell = np.array(
            [association[1] if association is not None and served[uid] else -1 for uid, association in enumerate(associations)]
        )
        boresight = np.stack(
            [satellite[int(n)] if n >= 0 else user_ecef[uid] for uid, n in enumerate(serving_sat)]
        )
        separation = _angle(
            user_ecef[:, None, :], boresight[:, None, :], beam_sat[None, :, :]
        )
        receive = ref.receive_pattern_gain(separation)
        receive = np.where(
            beam_sat.shape[0] and (serving_sat[:, None] == np.array([k[0] for k in beam_keys])[None, :]),
            10.0 ** (ref.RX_GAIN_MAX_DBI / 10.0),
            receive,
        )
        terms = beam_power[None, :] * transmit * path_without_receive * receive
        colors = np.array([int(grid.colors[key[1]]) for key in beam_keys])
        wanted_colors = np.array(
            [int(grid.colors[cell]) if cell >= 0 else -1 for cell in serving_cell]
        )
        same_sat = serving_sat[:, None] == np.array([key[0] for key in beam_keys])[None, :]
        same_cell = serving_cell[:, None] == np.array([key[1] for key in beam_keys])[None, :]
        co_colour = wanted_colors[:, None] == colors[None, :]
        linked = served[:, None]
        intra = np.sum(terms * (linked & same_sat & ~same_cell & co_colour), axis=1)
        inter = np.sum(terms * (linked & ~same_sat & co_colour), axis=1)
        beam_index = {key: i for i, key in enumerate(beam_keys)}
        wanted = np.zeros(users, dtype=float)
        for uid, association in enumerate(associations):
            if served[uid] and association is not None:
                column = beam_index[association]
                wanted[uid] = (
                    link_power[uid]
                    * transmit[uid, column]
                    * path_without_receive[uid, column]
                    * 10.0 ** (ref.RX_GAIN_MAX_DBI / 10.0)
                )
    else:
        terms = np.zeros((users, 0), dtype=float)
        separation = np.zeros((users, 0), dtype=float)
        intra = inter = wanted = np.zeros(users, dtype=float)

    interference = intra + inter
    sinr = np.where(served, ref.sinr(wanted, interference), 0.0)
    loads_by_key = {key: served_keys.count(key) for key in beam_keys}
    loads = np.array(
        [loads_by_key.get(associations[uid], 1) if served[uid] else 1 for uid in range(users)],
        dtype=float,
    )
    rate = np.where(served, ref.shannon_rate_bps(sinr, loads), 0.0)
    supply = ref.pa_supply_power_w(beam_power)
    fixed = ref.fixed_power_w(beam_keys)
    system = fixed + float(np.sum(supply))
    return {
        "served": served,
        "link_power_w": link_power,
        "beam_keys": beam_keys,
        "beam_power_w": beam_power,
        "pa_supply_w": supply,
        "fixed_power_w": fixed,
        "system_power_w": system,
        "wanted_w": wanted,
        "intra_w": intra,
        "inter_w": inter,
        "interference_w": interference,
        "sinr": sinr,
        "rate_bps": rate,
        "bits": ref.delivered_bits(rate),
        "terms_w": terms,
        "separation_deg": separation,
    }


def _relative(actual: np.ndarray, expected: np.ndarray) -> np.ndarray:
    actual = np.asarray(actual, dtype=float)
    expected = np.asarray(expected, dtype=float)
    scale = np.maximum(np.abs(expected), np.finfo(float).tiny)
    return np.abs(actual - expected) / scale


class MetricBook:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, Any]] = {}

    def add(self, name: str, env_value: Any, ref_value: Any, where: dict[str, Any]) -> None:
        actual = np.asarray(env_value, dtype=float)
        expected = np.asarray(ref_value, dtype=float)
        if actual.shape != expected.shape:
            error = math.inf
            flat_index = -1
        elif actual.size == 0:
            error = 0.0
            flat_index = -1
        else:
            rel = _relative(actual, expected)
            flat_index = int(np.argmax(rel))
            error = float(rel.flat[flat_index])
        row = self.rows.setdefault(
            name,
            {"max_relative_error": -1.0, "first_divergence": None, "max_witness": None},
        )
        witness = {
            **where,
            "flat_index": flat_index,
            "env": None if flat_index < 0 or actual.size == 0 else float(actual.flat[flat_index]),
            "reference": None if flat_index < 0 or expected.size == 0 else float(expected.flat[flat_index]),
            "relative_error": error,
        }
        if error > row["max_relative_error"]:
            row["max_relative_error"] = error
            row["max_witness"] = witness
        if error > 1e-6 and row["first_divergence"] is None:
            row["first_divergence"] = witness


def _run_trace(world_seed: int, policy_name: str, steps: int, book: MetricBook) -> dict[str, Any]:
    children = np.random.SeedSequence(world_seed).spawn(3)
    env_rng, mobility_rng, action_rng = (np.random.default_rng(child) for child in children)
    archive = TleArchive(TLE_ROOT)
    split = BlockAlternatingSplit.for_archive(archive)
    sampler = EpisodeStartSampler.for_archive(archive, split, TRAIN)
    epoch = sampler.draw(env_rng)
    environment = StepEnvironment(
        ScenarioDriver(
            archive,
            ScenarioConfig(
                mobility=MobilityConfig(num_users=100), steps_per_episode=steps
            ),
        ),
        physics=PhysicsConfig(segment_warm_start="uniform-episode-length"),
        fading_field=KeyedFadingField.from_components("DIFF_AUDIT", world_seed),
    )
    extractor = ReadOnlyExtractor(environment)
    observation = environment.reset(epoch, env_rng, mobility_rng=mobility_rng)
    policy = build_reference_policy(policy_name, seed=world_seed)
    policy.reset()
    ref_segments: list[tuple[int, int, float] | None] = [None] * 100
    ref_previous: list[tuple[int, int] | None] = [None] * 100
    sinr_db: list[float] = []
    no_interference_sinr_db: list[float] = []
    interference_penalty_db: list[float] = []
    intra_fraction: list[float] = []
    same_cell_interferer_count = 0
    segment_checks = {"continued_at_dwell_boundary": 0, "association_change_reset": 0,
                      "outage_cleared_segment": 0, "post_outage_reset": 0}
    previous_served_key: list[tuple[int, int] | None] = [None] * 100
    previous_was_outage = np.zeros(100, dtype=bool)
    nominal_other_term_max_abs = 0.0
    for step_index in range(steps):
        decision = observation.candidates
        actions = policy.act(decision, action_rng)
        user_ecef = np.asarray(environment.driver.user_ecef_km(), dtype=float).copy()
        pending_age = (
            None
            if environment._pending_segment_age is None
            else np.asarray(environment._pending_segment_age, dtype=int).copy()
        )
        historical: dict[tuple[int, int], np.ndarray] = {}
        if step_index == 0 and pending_age is not None:
            for age in sorted({int(value) for value in pending_age if int(value) > 0}):
                for norad, position in environment.driver.satellite_ecef_at(-age).items():
                    historical[(age, int(norad))] = np.asarray(position, dtype=float).copy()
        outcome = environment.step(actions, env_rng)
        hidden = extractor.physics
        if hidden is None:
            raise RuntimeError("read-only extractor missed physics payload")
        segments_before = copy.deepcopy(ref_segments)
        previous_before = list(ref_previous)
        calculated = _reference_step(
            environment,
            decision,
            actions,
            extractor.fading,
            extractor.shadow,
            ref_segments,
            ref_previous,
            step_index,
            user_ecef,
            pending_age,
            historical,
        )
        nominal = _reference_step(
            environment, decision, actions,
            {key: np.ones_like(value) for key, value in extractor.fading.items()},
            {key: np.zeros_like(value) for key, value in extractor.shadow.items()},
            segments_before, previous_before, step_index, user_ecef, pending_age, historical,
        )
        for name in ("served", "link_power_w", "beam_power_w", "pa_supply_w", "fixed_power_w", "system_power_w"):
            nominal_other_term_max_abs = max(
                nominal_other_term_max_abs,
                float(np.max(np.abs(np.asarray(calculated[name], dtype=float) - np.asarray(nominal[name], dtype=float)), initial=0.0)),
            )
        where = {"world_seed": world_seed, "policy": policy_name, "step": step_index}
        env_keys = [tuple(map(int, key)) for key in hidden["beam_keys"]]
        ref_keys = list(calculated["beam_keys"])
        union = sorted(set(env_keys) | set(ref_keys))
        env_beam = _metric_array_by_key(env_keys, outcome.radiating.power_w, union)
        ref_beam = _metric_array_by_key(ref_keys, calculated["beam_power_w"], union)
        env_supply = _metric_array_by_key(env_keys, hidden["supply_power_w"], union)
        ref_supply = _metric_array_by_key(ref_keys, calculated["pa_supply_w"], union)
        env_interference = outcome.interference.total_w
        env_wanted = outcome.link_sinr * (
            env_interference + environment.physics.noise_power_w
        )
        pairs = (
            ("served", outcome.resolution.served, calculated["served"]),
            ("link_power_w", outcome.link_power_w, calculated["link_power_w"]),
            ("wanted_w", env_wanted, calculated["wanted_w"]),
            ("intra_interference_w", outcome.interference.intra_w, calculated["intra_w"]),
            ("inter_interference_w", outcome.interference.inter_w, calculated["inter_w"]),
            ("interference_w", env_interference, calculated["interference_w"]),
            ("sinr", outcome.link_sinr, calculated["sinr"]),
            ("rate_bps", outcome.link_rate_bps, calculated["rate_bps"]),
            ("bits", ref.delivered_bits(outcome.link_rate_bps), calculated["bits"]),
            ("beam_rf_power_w", env_beam, ref_beam),
            ("pa_supply_w", env_supply, ref_supply),
            ("fixed_power_w", outcome.fixed_power_w, calculated["fixed_power_w"]),
            ("system_power_w", outcome.system_power_w, calculated["system_power_w"]),
        )
        for name, actual, expected in pairs:
            book.add(name, actual, expected, where)
        served = outcome.resolution.served
        current_keys: list[tuple[int, int] | None] = []
        for uid, association in enumerate(hidden["associations"]):
            key = None if association is None else (int(association.norad_id), int(association.cell_id))
            current_keys.append(key)
            segment = environment._segments[uid]
            if not served[uid]:
                assert segment is None
                segment_checks["outage_cleared_segment"] += 1
            else:
                assert segment is not None
                if step_index > 0 and previous_served_key[uid] != key:
                    assert segment.age_steps == 1, (
                        step_index, uid, previous_served_key[uid], key,
                        segment.age_steps, previous_was_outage[uid]
                    )
                    segment_checks["association_change_reset"] += 1
                    if previous_was_outage[uid]:
                        segment_checks["post_outage_reset"] += 1
                if step_index > 0 and decision.dwell.is_boundary and previous_served_key[uid] == key:
                    assert segment.age_steps > 0
                    segment_checks["continued_at_dwell_boundary"] += 1
        previous_served_key = [current_keys[uid] if served[uid] else None for uid in range(100)]
        previous_was_outage = ~served
        realised_db = 10.0 * np.log10(outcome.link_sinr[served])
        no_i_sinr = env_wanted[served] / environment.physics.noise_power_w
        no_i_db = 10.0 * np.log10(no_i_sinr)
        sinr_db.extend(realised_db.tolist())
        no_interference_sinr_db.extend(no_i_db.tolist())
        interference_penalty_db.extend((no_i_db - realised_db).tolist())
        total_i = outcome.interference.total_w[served]
        intra_fraction.extend(
            np.divide(
                outcome.interference.intra_w[served],
                total_i,
                out=np.zeros_like(total_i),
                where=total_i > 0,
            ).tolist()
        )
        if outcome.radiating.count:
            serving_sat = outcome.resolution.serving_satellite
            serving_cell = outcome.resolution.serving_cell
            same_cell_interferer_count += int(
                np.count_nonzero(
                    served[:, None]
                    & (outcome.radiating.cell_ids[None, :] == serving_cell[:, None])
                    & (outcome.radiating.norad_ids[None, :] != serving_sat[:, None])
                    & (
                        outcome.radiating.colors[None, :]
                        == environment.driver.grid.colors[np.maximum(serving_cell, 0)][:, None]
                    )
                )
            )
        observation = outcome.observation
    return {
        "world_seed": world_seed,
        "policy": policy_name,
        "epoch": epoch.isoformat(),
        "steps": steps,
        "sinr_db_p50": float(np.median(sinr_db)),
        "sinr_db_p05": float(np.quantile(sinr_db, 0.05)),
        "sinr_db_p95": float(np.quantile(sinr_db, 0.95)),
        "no_interference_sinr_db_p50": float(np.median(no_interference_sinr_db)),
        "interference_penalty_db_p50": float(np.median(interference_penalty_db)),
        "intra_fraction_mean": float(np.mean(intra_fraction)),
        "same_cell_cross_satellite_memberships": same_cell_interferer_count,
        "segment_checks": segment_checks,
        "nominal_realised_other_term_max_abs": nominal_other_term_max_abs,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--output", type=Path, default=HERE / "part2-results.json")
    args = parser.parse_args()
    if not TLE_ROOT.is_dir():
        raise SystemExit(f"TLE archive absent: {TLE_ROOT}")
    worlds = WORLD_SEEDS[:1] if args.quick else WORLD_SEEDS
    policies = POLICIES[:1] if args.quick else POLICIES
    steps = 3 if args.quick else 30
    book = MetricBook()
    traces = [_run_trace(world, policy, steps, book) for world in worlds for policy in policies]
    payload = {
        "schema": "v023-differential-audit-part2-v1",
        "world_domains": list(WORLD_DOMAINS),
        "world_seeds": list(WORLD_SEEDS),
        "s465_minimum_angle_deg_reference": ref.s465_minimum_angle_deg(),
        "traces": traces,
        "metrics": book.rows,
    }
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"traces": traces, "metrics": book.rows}, indent=2, sort_keys=True))
    return 1 if any(row["first_divergence"] for row in book.rows.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
