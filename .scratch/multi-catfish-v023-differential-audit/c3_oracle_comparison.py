"""Compare the diagnostic unilateral C3 with the declared LC-SRS pair oracle."""

from __future__ import annotations

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

from differential_audit import TLE_ROOT, WORLD_DOMAINS, WORLD_SEEDS
import reference_physics as ref


HERE = Path(__file__).resolve().parent
LAMBDA = float.fromhex("0x1.c3c0a7b6b86d3p+26")
KAPPA = float.fromhex("0x1.2cea89d260f2ap+33")


def profile(environment: StepEnvironment, actions: np.ndarray, rng: np.random.Generator) -> tuple[np.ndarray, float]:
    result = environment.evaluate_actions(actions, rng)
    return np.asarray(result.link_rate_bps) * ref.DECISION_STEP_S, result.system_power_w * ref.DECISION_STEP_S


def surplus(bits: np.ndarray, energy: float) -> float:
    return math.fsum(float(value) for value in bits) - LAMBDA * energy


def find_pair(decision, references: np.ndarray) -> tuple[int, int, int, int, tuple[int, int]]:
    by_destination: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for uid, table in enumerate(decision.slot_tables):
        reference_key = table.association(int(references[uid]))
        ref_pair = (int(reference_key.norad_id), int(reference_key.cell_id))
        for raw_action in np.flatnonzero(table.mask).tolist():
            action = int(raw_action)
            association = table.association(action)
            key = (int(association.norad_id), int(association.cell_id))
            if key != ref_pair:
                by_destination.setdefault(key, []).append((uid, action))
    for key in sorted(by_destination):
        candidates = by_destination[key]
        for first in candidates:
            for second in candidates:
                if first[0] != second[0]:
                    return first[0], first[1], second[0], second[1], key
    raise RuntimeError("synthetic world contains no shared alternate physical beam")


def main() -> None:
    seed = WORLD_SEEDS[0]
    streams = np.random.SeedSequence(seed).spawn(3)
    env_rng, mobility_rng, action_rng = (np.random.default_rng(item) for item in streams)
    archive = TleArchive(TLE_ROOT)
    sampler = EpisodeStartSampler.for_archive(archive, BlockAlternatingSplit.for_archive(archive), TRAIN)
    epoch = sampler.draw(env_rng)
    environment = StepEnvironment(
        ScenarioDriver(archive, ScenarioConfig(mobility=MobilityConfig(num_users=100), steps_per_episode=1)),
        physics=PhysicsConfig(segment_warm_start="uniform-episode-length"),
        fading_field=KeyedFadingField.from_components("DIFF_AUDIT", seed),
    )
    observation = environment.reset(epoch, env_rng, mobility_rng=mobility_rng)
    policy = build_reference_policy("nearest-eligible", seed=seed)
    policy.reset()
    reference_actions = policy.act(observation.candidates, action_rng)
    first_user, first_action, second_user, second_action, destination = find_pair(
        observation.candidates, reference_actions
    )

    a00 = np.array(reference_actions, copy=True)
    a10 = np.array(reference_actions, copy=True); a10[first_user] = first_action
    a01 = np.array(reference_actions, copy=True); a01[second_user] = second_action
    a11 = np.array(a10, copy=True); a11[second_user] = second_action
    b00, e00 = profile(environment, a00, env_rng)
    b10, e10 = profile(environment, a10, env_rng)
    b01, e01 = profile(environment, a01, env_rng)
    b11, e11 = profile(environment, a11, env_rng)

    unilateral_bits = np.stack((b10, b01))
    unilateral_energy = np.array((e10, e01))
    users = np.array((first_user, second_user))
    unilateral_c3 = np.array([
        math.fsum(float(value) for index, value in enumerate(unilateral_bits[row] - b00) if index != uid)
        for row, uid in enumerate(users)
    ])
    own = np.array([
        unilateral_bits[row, uid] - b00[uid] - LAMBDA * (unilateral_energy[row] - e00)
        for row, uid in enumerate(users)
    ])
    interaction = (surplus(b11, e11) - surplus(b00, e00)) - (
        surplus(b10, e10) - surplus(b00, e00)
    ) - (surplus(b01, e01) - surplus(b00, e00))
    lcsrs_c3 = unilateral_c3 + interaction / 2.0
    joint_surplus = surplus(b11, e11) - surplus(b00, e00)
    identity_residual = math.fsum(float(v) for v in own + lcsrs_c3) - joint_surplus

    rows = []
    for index, uid in enumerate(users.tolist()):
        rows.append({
            "user": uid,
            "proposed_action": [first_action, second_action][index],
            "unilateral_others_bits_c3": float(unilateral_c3[index]),
            "declared_lcsrs_c3_bits": float(lcsrs_c3[index]),
            "difference_bits": float(lcsrs_c3[index] - unilateral_c3[index]),
            "unilateral_q3_over_kappa": float(unilateral_c3[index] / KAPPA),
            "lcsrs_q3_over_kappa": float(lcsrs_c3[index] / KAPPA),
        })
    result = {
        "schema": "v023-c3-oracle-comparison-v1",
        "world_domain": WORLD_DOMAINS[0],
        "world_seed": seed,
        "epoch": epoch.isoformat(),
        "shared_proposed_physical_beam": list(destination),
        "computed_oracle_quantity": "others' delivered-bit change under each user's unilateral action",
        "computed_oracle_is_set_decoder": False,
        "declared_quantity": "LC-SRS: unilateral nonfocal bits plus one-half of the two-player joint EE-surplus interaction",
        "interaction_surplus_bits": float(interaction),
        "joint_identity_residual_bits": float(identity_residual),
        "rows": rows,
    }
    (HERE / "part4-c3-comparison.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
