"""Family-B reward-scale recalibration machinery for SDD 08 W-11.

This module implements the SDD 08 §3.11 five-axis procedure as reusable
pure functions plus one orchestration entry point. The calibration target is
share equality under the named reference mix
``{planner, greedy, sticky, round_robin, random}``, equal weighted. The
max-eta-biased arm is deliberately excluded because it would make the eta
objective self-referential, and the paper Table-II throughput-order mapping is
declared inapplicable to the Family-B eta-mode reward surface.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from ..runtime.angle_aware_ee import per_ue_energy_efficiency
from ..env.family_b_policies import (
    PolicyDecision,
    StickyPolicy,
    greedy_policy,
    planner_policy,
    random_policy,
    round_robin_policy,
    sticky_policy,
)
from ..env.family_b_sampling import eval_phase_grid, spawn_rng_domains
from ..env.family_b_step import FamilyBStepEnvironment

ObjectiveExtractor = Callable[[Any, FamilyBStepEnvironment], np.ndarray]
EnvFactory = Callable[[], FamilyBStepEnvironment]
RngDomainFactory = Callable[[int], Any]
PolicyCallable = Callable[[FamilyBStepEnvironment, Any, np.random.Generator], PolicyDecision]

REFERENCE_MIX: tuple[str, ...] = (
    "planner",
    "greedy",
    "sticky",
    "round_robin",
    "random",
)
EXCLUDED_FROM_CALIBRATION: tuple[str, ...] = ("max_eta_biased",)
OBJECTIVE_KEYS: tuple[str, str, str] = ("r1", "r2", "r3")
OBJECTIVE_WEIGHTS: tuple[float, float, float] = (1.0, 1.0, 1.0)
SCALE_FLOOR = 1.0e-12


@dataclass(frozen=True)
class FamilyBRecalibrationParams:
    """Prereg-named knobs for the SDD 08 §3.11 recalibration pipeline."""

    l4_4_reference_mix: tuple[str, ...] = REFERENCE_MIX
    l4_4_policy_weights: tuple[float, ...] = (0.2, 0.2, 0.2, 0.2, 0.2)
    l4_4_phase_bins: int = 8
    l4_4_min_episodes_per_stratum: int = 8
    l4_4_seed_set_a: tuple[int, ...] = (1000, 1001, 1002, 1003, 1004)
    l4_4_seed_set_b: tuple[int, ...] = (2000, 2001, 2002, 2003, 2004)
    l4_4_derivation_split: str = "even-grid-indices+seed_set_a derive / odd+seed_set_b verdict"
    l4_4_share_band: tuple[float, float] = (0.02, 0.90)
    eval_phase_grid_size: int = 288
    phase_support_s: float = 86_400.0
    objective_weights: tuple[float, float, float] = OBJECTIVE_WEIGHTS
    planner_restarts: int = 8
    steps_per_episode: int | None = None
    scale_floor: float = SCALE_FLOOR


def default_family_b_reference_policies(
    *,
    planner_restarts: int = 8,
) -> dict[str, PolicyCallable]:
    """Return the named SDD 08 calibration policy mix.

    The mapping intentionally omits ``max_eta_biased``. Sticky state is scoped
    to each rollout episode by :func:`rollout_policy_episode`.
    """

    def planner(env: FamilyBStepEnvironment, masks: Any, rng: np.random.Generator) -> PolicyDecision:
        return planner_policy(env, masks, planner_restarts=planner_restarts, rng=rng)

    def greedy(env: FamilyBStepEnvironment, masks: Any, rng: np.random.Generator) -> PolicyDecision:
        del rng
        return greedy_policy(env, masks)

    def sticky(env: FamilyBStepEnvironment, masks: Any, rng: np.random.Generator) -> PolicyDecision:
        del rng
        state = getattr(sticky, "_state", None)
        if state is None:
            state = StickyPolicy()
            setattr(sticky, "_state", state)
        return sticky_policy(env, masks, state)

    def round_robin(env: FamilyBStepEnvironment, masks: Any, rng: np.random.Generator) -> PolicyDecision:
        del rng
        return round_robin_policy(env, masks)

    def random(env: FamilyBStepEnvironment, masks: Any, rng: np.random.Generator) -> PolicyDecision:
        return random_policy(env, masks, rng)

    return {
        "planner": planner,
        "greedy": greedy,
        "sticky": sticky,
        "round_robin": round_robin,
        "random": random,
    }


def reset_policy_episode_state(policy: PolicyCallable) -> None:
    """Clear optional per-episode state carried by default policy closures."""

    if hasattr(policy, "_state"):
        delattr(policy, "_state")


def family_b_eta_r1(result: Any, env: FamilyBStepEnvironment, uid: int) -> float:
    """Return Family-B slot-space STANDARD angle-aware EE r1 for one user.

    ``eta = R_u / p_alloc`` (thesis §3.2 eq 3.22): transmit power is
    angle-INDEPENDENT; the angle enters ONLY through the numerator
    (``G^T(theta) -> SINR -> rate``). After the 2026-07-03 fix this equals the
    env's ``result.rewards[u].r1_energy_efficiency_credit`` (verified line-by-line
    and numerically to ~1e-11).

    ⚠ CORRECTION (2026-07-03): the erroneous ``/ g_t_linear`` was removed here.
    It divided power by the antenna gain => angle-DEPENDENT effective power and a
    ~1e4 EE inflation (= the mean served-user ``G_T``), matching neither thesis
    §3.2 nor peer LEO-EE papers (gain belongs inside the SINR only). This
    function is the LIVE eval axis AND the route-B / Family-B TRAIN reward (both
    reach it via the trainer override at ``family_b_retrain/trainer.py:144``), so
    train==eval EE consistency is preserved. The base
    ``MODQNTrainer.reward_vector_from_step_result`` (``modqn.py:838``,
    G1-protected) STILL holds the old ``/ g_t_linear`` as a DEAD sealed reference
    — it is not on any live path and its cleanup is deferred to the next
    G1-unlock / retrain window.

    Zero-power cap-bumped slots are not special-cased: allocated power is ``0``,
    ``p_tot_effective`` is ``0``, and ``per_ue_energy_efficiency`` applies its
    own epsilon guard => eta is ``0``.
    """

    uid_i = int(uid)
    rw = result.rewards[uid_i]
    user_state = result.user_states[uid_i]
    assigned_slot = int(np.argmax(user_state.access_vector))
    beam_power_w = float(result.slot_power_w[uid_i, assigned_slot])
    beam_load = float(user_state.beam_loads[assigned_slot])
    allocated_power_w = beam_power_w / max(beam_load, 1.0)

    # STANDARD angle-aware EE: p_tot = p_alloc, power angle-INDEPENDENT (thesis §3.2).
    # The erroneous "/ g_t_linear" (antenna-gain division => ~1e4 EE inflation) was
    # removed 2026-07-03; see the docstring. eta == env r1_energy_efficiency_credit.
    p_tot_effective = allocated_power_w

    ee_result = per_ue_energy_efficiency(
        rates_nmk=np.array([rw.r1_throughput], dtype=np.float64),
        admitted_link_nmk=np.array([True]),
        p_req_nmk=np.array([p_tot_effective], dtype=np.float64),
        p_max_nm=np.array([beam_power_w], dtype=np.float64),
        p_tot_nm=np.array([p_tot_effective], dtype=np.float64),
    )
    return float(ee_result.eta_nmk[0])


def family_b_eta_objective_extractor(
    result: Any,
    env: FamilyBStepEnvironment,
) -> np.ndarray:
    """Return aggregate raw ``(eta-r1, r2, r3)`` for SDD 08 calibration."""

    vals = [
        (
            family_b_eta_r1(result, env, uid),
            float(r.r2_handover),
            float(r.r3_load_balance),
        )
        for uid, r in enumerate(result.rewards)
    ]
    if not vals:
        return np.zeros(3, dtype=np.float64)
    return np.sum(np.asarray(vals, dtype=np.float64), axis=0)


def throughput_r1_objective_extractor(
    result: Any,
    env: FamilyBStepEnvironment,
) -> np.ndarray:
    """Return aggregate raw ``(throughput-r1, r2, r3)``.

    This legacy-compatible extractor is an explicit non-default alternative.
    It is not SDD 08-conformant for Family-B eta-mode r1 recalibration.
    """

    del env

    vals = [
        (float(r.r1_throughput), float(r.r2_handover), float(r.r3_load_balance))
        for r in result.rewards
    ]
    if not vals:
        return np.zeros(3, dtype=np.float64)
    return np.sum(np.asarray(vals, dtype=np.float64), axis=0)


default_objective_extractor = family_b_eta_objective_extractor


def grid_indices_for_split(
    *,
    grid_size: int,
    phase_bins: int,
    min_episodes_per_stratum: int,
    split: str,
) -> dict[int, list[int]]:
    """Select stratified eval-grid indices for the derivation or verdict split."""

    if split not in {"even", "odd"}:
        raise ValueError("split must be 'even' or 'odd'")
    if grid_size <= 0 or phase_bins <= 0 or min_episodes_per_stratum <= 0:
        raise ValueError("grid_size, phase_bins, and min episodes must be positive")
    if grid_size % phase_bins != 0:
        raise ValueError("grid_size must be divisible by phase_bins")
    parity = 0 if split == "even" else 1
    per_bin = grid_size // phase_bins
    selected: dict[int, list[int]] = {}
    for bin_id in range(phase_bins):
        start = bin_id * per_bin
        stop = start + per_bin
        candidates = [idx for idx in range(start, stop) if idx % 2 == parity]
        if len(candidates) < min_episodes_per_stratum:
            raise ValueError(
                f"bin {bin_id} has only {len(candidates)} {split} indices; "
                f"need {min_episodes_per_stratum}"
            )
        selected[bin_id] = candidates[:min_episodes_per_stratum]
    return selected


def rollout_policy_episode(
    *,
    env: FamilyBStepEnvironment,
    policy_name: str,
    policy: PolicyCallable,
    env_rng: np.random.Generator,
    mobility_rng: np.random.Generator,
    policy_rng: np.random.Generator,
    initial_time_s: float,
    objective_extractor: ObjectiveExtractor = default_objective_extractor,
    steps_per_episode: int | None = None,
) -> dict[str, Any]:
    """Run one non-learned Family-B reference-policy episode."""

    reset_policy_episode_state(policy)
    _states, masks, diag = env.reset(
        env_rng,
        mobility_rng,
        initial_time_s=float(initial_time_s),
    )
    n_steps = env.config.steps_per_episode if steps_per_episode is None else int(steps_per_episode)
    objective_sum = np.zeros(3, dtype=np.float64)
    cap_bumps = 0
    modal_fracs: list[float] = []
    active_counts: list[float] = []
    for _step in range(n_steps):
        decision = policy(env, masks, policy_rng)
        result = env.step(decision.actions, env_rng)
        objective_sum += np.asarray(objective_extractor(result, env), dtype=np.float64)
        cap_bumps += int(result.cap_bump_count)
        counts = np.bincount(np.asarray(decision.actions, dtype=np.int64), minlength=28)
        active = counts[counts > 0]
        modal_fracs.append(float(active.max()) / float(env.config.num_users) if active.size else 0.0)
        active_counts.append(float(active.size))
        masks = result.action_masks
        if result.done:
            break
    return {
        "policy": policy_name,
        "initial_time_s": float(diag["initial_time_s"]),
        "objective_sum": objective_sum,
        "cap_bump_count": cap_bumps,
        "modal_frac_mean": float(np.mean(modal_fracs)) if modal_fracs else 0.0,
        "active_action_count_mean": float(np.mean(active_counts)) if active_counts else 0.0,
        "steps": len(modal_fracs),
    }


def collect_reference_rollouts(
    *,
    env_factory: EnvFactory,
    policies: Mapping[str, PolicyCallable],
    rng_domain_factory: RngDomainFactory,
    params: FamilyBRecalibrationParams,
    split: str,
    objective_extractor: ObjectiveExtractor = default_objective_extractor,
) -> dict[str, list[dict[str, Any]]]:
    """Collect stratified even/odd-grid rollouts for the named reference mix."""

    grid = eval_phase_grid(
        support_s=params.phase_support_s,
        grid_size=params.eval_phase_grid_size,
    )
    split_indices = grid_indices_for_split(
        grid_size=params.eval_phase_grid_size,
        phase_bins=params.l4_4_phase_bins,
        min_episodes_per_stratum=params.l4_4_min_episodes_per_stratum,
        split=split,
    )
    seed_set = params.l4_4_seed_set_a if split == "even" else params.l4_4_seed_set_b
    out: dict[str, list[dict[str, Any]]] = {}
    for policy_name in params.l4_4_reference_mix:
        if policy_name in EXCLUDED_FROM_CALIBRATION:
            raise ValueError(f"{policy_name!r} is excluded from L4-4 calibration")
        if policy_name not in policies:
            raise KeyError(f"missing policy {policy_name!r}")
        policy = policies[policy_name]
        rows: list[dict[str, Any]] = []
        for seed in seed_set:
            domains = rng_domain_factory(int(seed))
            for bin_id, indices in split_indices.items():
                for grid_index in indices:
                    env = env_factory()
                    row = rollout_policy_episode(
                        env=env,
                        policy_name=policy_name,
                        policy=policy,
                        env_rng=domains.env,
                        mobility_rng=domains.mobility,
                        policy_rng=domains.train,
                        initial_time_s=float(grid[int(grid_index)]),
                        objective_extractor=objective_extractor,
                        steps_per_episode=params.steps_per_episode,
                    )
                    row["seed"] = int(seed)
                    row["phase_bin"] = int(bin_id)
                    row["grid_index"] = int(grid_index)
                    rows.append(row)
        out[policy_name] = rows
    return out


def aggregate_reference_magnitudes(
    rollouts_by_policy: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    """Compute equal-policy-weighted aggregate objective magnitudes."""

    per_policy: dict[str, dict[str, float]] = {}
    for policy_name, rows in rollouts_by_policy.items():
        if not rows:
            raise ValueError(f"policy {policy_name!r} has no rows")
        arr = np.stack([np.asarray(row["objective_sum"], dtype=np.float64) for row in rows], axis=0)
        mean_abs = np.mean(np.abs(arr), axis=0)
        per_policy[policy_name] = {
            key: float(mean_abs[idx]) for idx, key in enumerate(OBJECTIVE_KEYS)
        }
    aggregate = {
        key: float(np.mean([per_policy[p][key] for p in per_policy]))
        for key in OBJECTIVE_KEYS
    }
    return {"aggregate_mean_abs": aggregate, "per_policy_mean_abs": per_policy}


def derive_equal_share_scales(
    aggregate_mean_abs: Mapping[str, float],
    *,
    objective_weights: Sequence[float] = OBJECTIVE_WEIGHTS,
    scale_floor: float = SCALE_FLOOR,
) -> dict[str, float]:
    """Derive per-objective scales for equal weighted-share magnitudes."""

    if len(objective_weights) != 3:
        raise ValueError("objective_weights must have length 3")
    scales: dict[str, float] = {}
    for idx, key in enumerate(OBJECTIVE_KEYS):
        raw = float(aggregate_mean_abs[key])
        weighted = abs(float(objective_weights[idx])) * raw
        scales[key] = max(weighted, float(scale_floor))
    return scales


def share_report(
    rollouts_by_policy: Mapping[str, Sequence[Mapping[str, Any]]],
    scales: Mapping[str, float],
    *,
    objective_weights: Sequence[float] = OBJECTIVE_WEIGHTS,
    share_band: tuple[float, float] = (0.02, 0.90),
    zero_floor: float = SCALE_FLOOR,
) -> dict[str, Any]:
    """Compute aggregate-mix L4-4 verdict shares and per-policy diagnostics."""

    if len(objective_weights) != 3:
        raise ValueError("objective_weights must have length 3")
    div = np.array([float(scales[key]) for key in OBJECTIVE_KEYS], dtype=np.float64)
    weights = np.array(objective_weights, dtype=np.float64)
    per_policy: dict[str, Any] = {}
    contributions: list[np.ndarray] = []
    for policy_name, rows in rollouts_by_policy.items():
        arr = np.stack([np.asarray(row["objective_sum"], dtype=np.float64) for row in rows], axis=0)
        contrib = np.mean(np.abs(arr * weights / div), axis=0)
        total = float(np.sum(contrib))
        shares = np.zeros(3, dtype=np.float64) if total <= 0.0 else contrib / total
        contributions.append(contrib)
        per_policy[policy_name] = {
            "shares": {key: float(shares[idx]) for idx, key in enumerate(OBJECTIVE_KEYS)},
            "mean_abs_raw": {
                key: float(np.mean(np.abs(arr[:, idx]))) for idx, key in enumerate(OBJECTIVE_KEYS)
            },
            "zero_objective_flags": {
                key: bool(np.mean(np.abs(arr[:, idx])) <= zero_floor)
                for idx, key in enumerate(OBJECTIVE_KEYS)
            },
            "verdicted": False,
            "note": "per-policy zero-objective corners are reported, not verdicted",
        }
    agg_contrib = np.mean(np.stack(contributions, axis=0), axis=0)
    agg_total = float(np.sum(agg_contrib))
    agg_shares = np.zeros(3, dtype=np.float64) if agg_total <= 0.0 else agg_contrib / agg_total
    lo, hi = (float(share_band[0]), float(share_band[1]))
    passed = bool(np.all((agg_shares >= lo) & (agg_shares <= hi)))
    return {
        "aggregate_shares": {
            key: float(agg_shares[idx]) for idx, key in enumerate(OBJECTIVE_KEYS)
        },
        "aggregate_contributions": {
            key: float(agg_contrib[idx]) for idx, key in enumerate(OBJECTIVE_KEYS)
        },
        "share_band": [lo, hi],
        "passed": passed,
        "per_policy": per_policy,
    }


def build_scales_document(
    *,
    params: FamilyBRecalibrationParams,
    derivation_rollouts: Mapping[str, Sequence[Mapping[str, Any]]],
    scales: Mapping[str, float],
    verdict_rollouts: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Build the data-blind scale-pinning JSON document."""

    derivation_magnitudes = aggregate_reference_magnitudes(derivation_rollouts)
    verdict = None
    if verdict_rollouts is not None:
        verdict = share_report(
            verdict_rollouts,
            scales,
            objective_weights=params.objective_weights,
            share_band=params.l4_4_share_band,
            zero_floor=params.scale_floor,
        )
    derivation_indices = sorted(
        {
            int(row["grid_index"])
            for rows in derivation_rollouts.values()
            for row in rows
        }
    )
    provenance = {
        "procedure": "SDD 08 §3.11 five-axis Family-B reward recalibration",
        "calibration_target": "share equality under equal-weighted named reference mix",
        "table_ii_mapping": "inapplicable to Family-B eta-mode calibration",
        "excluded_policies": list(EXCLUDED_FROM_CALIBRATION),
        "grid_indices_used": derivation_indices,
        "seeds": list(params.l4_4_seed_set_a),
        "episode_counts": {
            policy: len(rows) for policy, rows in derivation_rollouts.items()
        },
        "phase_bins": int(params.l4_4_phase_bins),
        "min_episodes_per_stratum": int(params.l4_4_min_episodes_per_stratum),
        "derivation_split": params.l4_4_derivation_split,
    }
    return {
        "schema": "family-b-reward-recalibration-scales-v1",
        "claim": "READINESS-ONLY scale derivation machinery; not an effectiveness claim",
        "scales": {key: float(scales[key]) for key in OBJECTIVE_KEYS},
        "objective_weights": [float(w) for w in params.objective_weights],
        "derivation": derivation_magnitudes,
        "verdict": verdict,
        "provenance": provenance,
    }


def write_scales_json(document: Mapping[str, Any], path: str | Path) -> Path:
    """Write a recalibration scales document with stable JSON formatting."""

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    return out


def run_family_b_recalibration(
    *,
    env_factory: EnvFactory | None = None,
    policies: Mapping[str, PolicyCallable] | None = None,
    rng_domain_factory: RngDomainFactory = spawn_rng_domains,
    params: FamilyBRecalibrationParams | None = None,
    objective_extractor: ObjectiveExtractor = default_objective_extractor,
) -> dict[str, Any]:
    """Orchestrate derive-even / verdict-odd L4-4 recalibration machinery."""

    cfg = params or FamilyBRecalibrationParams()
    factory = env_factory or FamilyBStepEnvironment
    policy_map = policies or default_family_b_reference_policies(
        planner_restarts=cfg.planner_restarts,
    )
    derivation = collect_reference_rollouts(
        env_factory=factory,
        policies=policy_map,
        rng_domain_factory=rng_domain_factory,
        params=cfg,
        split="even",
        objective_extractor=objective_extractor,
    )
    mags = aggregate_reference_magnitudes(derivation)
    scales = derive_equal_share_scales(
        mags["aggregate_mean_abs"],
        objective_weights=cfg.objective_weights,
        scale_floor=cfg.scale_floor,
    )
    verdict = collect_reference_rollouts(
        env_factory=factory,
        policies=policy_map,
        rng_domain_factory=rng_domain_factory,
        params=cfg,
        split="odd",
        objective_extractor=objective_extractor,
    )
    return build_scales_document(
        params=cfg,
        derivation_rollouts=derivation,
        scales=scales,
        verdict_rollouts=verdict,
    )


__all__ = [
    "EXCLUDED_FROM_CALIBRATION",
    "FamilyBRecalibrationParams",
    "REFERENCE_MIX",
    "aggregate_reference_magnitudes",
    "build_scales_document",
    "collect_reference_rollouts",
    "default_family_b_reference_policies",
    "default_objective_extractor",
    "derive_equal_share_scales",
    "family_b_eta_objective_extractor",
    "family_b_eta_r1",
    "grid_indices_for_split",
    "rollout_policy_episode",
    "run_family_b_recalibration",
    "share_report",
    "throughput_r1_objective_extractor",
    "write_scales_json",
]
