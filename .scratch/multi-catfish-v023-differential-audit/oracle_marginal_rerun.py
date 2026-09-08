"""One-world/three-carrier, 30-step C3 definition diagnostic under V0.23 physics."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np

from mcrl.env.ephemeris import BlockAlternatingSplit, EpisodeStartSampler, TRAIN
from mcrl.env.keyed_fading import KeyedFadingField
from mcrl.env.mobility import MobilityConfig
from mcrl.env.reference_policy import build_reference_policy
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.step import PhysicsConfig, StepEnvironment
from mcrl.env.tle import TleArchive

from differential_audit import POLICIES, TLE_ROOT, WORLD_DOMAINS, WORLD_SEEDS
from target_parity_suite.declared_c3_oracle import DecisionProfile, declared_c3_oracle


HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "declared-c3-oracle-marginals.json"
LAMBDA = float.fromhex("0x1.c3c0a7b6b86d3p+26")
INTERVAL = float.fromhex("0x1.e147ae147ae15p+4")
DEMANDS = (("G0", None), ("G1", 200e6), ("G2", 50e6), ("G3", 10e6))
LABELS = ("00", "10", "01", "11")


def _profile(environment: StepEnvironment, actions: np.ndarray, rng: np.random.Generator) -> DecisionProfile:
    value = environment.evaluate_actions(actions, rng)
    return DecisionProfile(
        np.asarray(value.link_rate_bps, dtype=np.float64) * INTERVAL,
        float(value.system_power_w) * INTERVAL,
    )


def _cap(profile: DecisionProfile, demand: float | None) -> DecisionProfile:
    if demand is None:
        return profile
    return DecisionProfile(np.minimum(profile.bits, float(demand) * INTERVAL), profile.energy_j)


def _pair(decision: object, references: np.ndarray) -> tuple[int, int, int, int]:
    destinations: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for uid, table in enumerate(decision.slot_tables):
        reference = table.association(int(references[uid]))
        reference_key = (int(reference.norad_id), int(reference.cell_id))
        for raw in np.flatnonzero(table.mask).tolist():
            association = table.association(int(raw))
            key = (int(association.norad_id), int(association.cell_id))
            if key != reference_key:
                destinations.setdefault(key, []).append((uid, int(raw)))
    for key in sorted(destinations):
        rows = destinations[key]
        for first in rows:
            for second in rows:
                if first[0] != second[0]:
                    return first[0], first[1], second[0], second[1]
    raise RuntimeError("no two users share an alternate physical beam")


def _label_actions(label: str, rows: tuple[np.ndarray, ...]) -> np.ndarray:
    return np.array(rows[LABELS.index(label)], copy=True)


def _drop_label(p00: DecisionProfile, p10: DecisionProfile, p01: DecisionProfile, users: tuple[int, int]) -> str:
    own0 = p10.bits[users[0]] - p00.bits[users[0]] - LAMBDA * (p10.energy_j - p00.energy_j)
    own1 = p01.bits[users[1]] - p00.bits[users[1]] - LAMBDA * (p01.energy_j - p00.energy_j)
    return ("1" if own0 > 0.0 else "0") + ("1" if own1 > 0.0 else "0")


def _executed_label(profiles: tuple[DecisionProfile, ...], users: tuple[int, int]) -> str:
    p00, p10, p01, _p11 = profiles
    scores = []
    for offset, candidate in enumerate((p10, p01)):
        scores.append(
            math.fsum(float(value) for value in candidate.bits - p00.bits)
            - LAMBDA * (candidate.energy_j - p00.energy_j)
        )
    return ("1" if scores[0] > 0.0 else "0") + ("1" if scores[1] > 0.0 else "0")


def _row(profile: DecisionProfile) -> dict[str, float]:
    return {"bits": math.fsum(float(v) for v in profile.bits), "energy_j": profile.energy_j}


def _carrier(policy_name: str) -> list[dict[str, object]]:
    seed = WORLD_SEEDS[0]
    seeds = np.random.SeedSequence(seed).spawn(3)
    env_rng, mobility_rng, action_rng = (np.random.default_rng(item) for item in seeds)
    archive = TleArchive(TLE_ROOT)
    epoch = EpisodeStartSampler.for_archive(
        archive, BlockAlternatingSplit.for_archive(archive), TRAIN
    ).draw(env_rng)
    environment = StepEnvironment(
        ScenarioDriver(
            archive,
            ScenarioConfig(steps_per_episode=30, mobility=MobilityConfig(num_users=100)),
        ),
        physics=PhysicsConfig(segment_warm_start="uniform-episode-length"),
        fading_field=KeyedFadingField.from_components("DECLARED_C3_ORACLE", seed, policy_name),
    )
    observation = environment.reset(epoch, env_rng, mobility_rng=mobility_rng)
    policy = build_reference_policy(policy_name, seed=seed)
    policy.reset()
    output: list[dict[str, object]] = []
    for step in range(30):
        reference = np.asarray(policy.act(observation.candidates, action_rng), dtype=np.int64)
        u0, a0, u1, a1 = _pair(observation.candidates, reference)
        rows = [np.array(reference, copy=True) for _ in range(4)]
        rows[1][u0] = a0
        rows[2][u1] = a1
        rows[3][u0], rows[3][u1] = a0, a1
        raw = tuple(_profile(environment, actions, env_rng) for actions in rows)
        g0_declared = declared_c3_oracle(*raw, lambda_bits_per_j=LAMBDA, users=(u0, u1))
        g0_label = g0_declared.atomic_selection.profile
        for grid, demand in DEMANDS:
            capped = tuple(_cap(value, demand) for value in raw)
            declared = declared_c3_oracle(*capped, lambda_bits_per_j=LAMBDA, users=(u0, u1))
            labels = {
                "drop_c3": _drop_label(capped[0], capped[1], capped[2], (u0, u1)),
                "executed": _executed_label(capped, (u0, u1)),
                "declared_reused_g0": g0_label,
                "declared_per_regime_j": declared.atomic_selection.profile,
            }
            output.append({
                "carrier": policy_name,
                "step": step,
                "grid": grid,
                "users": [u0, u1],
                "psi": declared.psi,
                "labels": labels,
                "profiles": {label: _row(profile) for label, profile in zip(LABELS, capped, strict=True)},
            })
        committed = environment.step(reference, env_rng)
        observation = committed.observation
    return output


def _metrics(rows: list[dict[str, object]], mode: str) -> dict[str, float | int]:
    def totals(label_key: str) -> tuple[float, float]:
        bits = energy = 0.0
        for row in rows:
            label = str(row["labels"][label_key])
            profile = row["profiles"][label]
            bits += float(profile["bits"])
            energy += float(profile["energy_j"])
        return bits, energy
    full_bits, full_energy = totals(mode)
    drop_bits, drop_energy = totals("drop_c3")
    return {
        "steps": len(rows),
        "full_ee_bits_per_j": full_bits / full_energy,
        "drop_c3_ee_bits_per_j": drop_bits / drop_energy,
        "c3_marginal_bits_per_j": full_bits / full_energy - drop_bits / drop_energy,
        "profiles_different_from_drop": sum(
            row["labels"][mode] != row["labels"]["drop_c3"] for row in rows
        ),
    }


def main() -> None:
    anchors = [row for policy in POLICIES for row in _carrier(policy)]
    results: dict[str, object] = {}
    for grid, _demand in DEMANDS:
        grid_rows = [row for row in anchors if row["grid"] == grid]
        results[grid] = {
            mode: _metrics(grid_rows, mode)
            for mode in ("executed", "declared_reused_g0", "declared_per_regime_j")
        }
    payload = {
        "schema": "v023-old-physics-declared-c3-oracle-marginals-v1",
        "claim": "diagnostic history only; not a successor claim",
        "world_domain": WORLD_DOMAINS[0],
        "world_seed": WORLD_SEEDS[0],
        "carriers": list(POLICIES),
        "steps_per_carrier": 30,
        "lambda_bits_per_j_hex": LAMBDA.hex(),
        "selection_note": "DROP uses unilateral own surplus; executed uses independent unilateral total-surplus signs; declared is atomic four-profile max; final mode re-optimizes that max after each demand cap.",
        "results": results,
        "anchors_sha256": hashlib.sha256(json.dumps(anchors, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
