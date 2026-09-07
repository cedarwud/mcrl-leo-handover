#!/usr/bin/env python3
"""Isolated real-environment C2-k1 adapter used by the V0.6 shard path.

Only this file knows how to turn the frozen V0.4 loader into a live
environment.  It intentionally has no import of the V0.4 C2 hold/tape
modules.  The public ``run_one_anchor_lineage`` function is also usable with
the small runtime protocol in tests, so contract tests do not need TLE files.
"""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Callable

import numpy as np

from mcrl.env.keyed_fading import KeyedFadingField
from mcrl.runtime.ee_axis_state import encode_ee_axis_state
from mcrl.runtime.ee_axis_v04_c3_state import encode_ee_axis_v04_c3_state
from mcrl.runtime.ee_axis_v06_c2_k1 import (
    ACTION_COUNT,
    branch_local_actions,
    c2_k1_surplus_bits,
    canonical_sha256,
    four_offset_metrics,
    masked_argmax,
    oracle_and_drop_scores,
    policy_hash,
    select_anchor,
    select_train_worlds,
)


class LiveAdapterError(RuntimeError):
    """The physical shard cannot be produced and must stop."""


class DefaultLiveRuntime:
    """Authenticated V0.4 loader with a deliberately tiny V0.6 seam."""

    users = 100

    def __init__(self, loader: Any, production_runtime: Any, record: Any, archive: Any, trainer: Any,
                 checkpoint_sha256: str, prereg_file_sha256: str,
                 hybrids: Mapping[str, Any], hybrid_hashes: Mapping[str, str],
                 gate_receipt: Mapping[str, Any], q13_gate_source_manifest_sha256: str) -> None:
        self.loader = loader
        self.production_runtime = production_runtime
        self.record = record
        self.archive = archive
        self.trainer = trainer
        self.checkpoint_sha256 = checkpoint_sha256
        self.prereg_file_sha256 = prereg_file_sha256
        self.hybrids = dict(hybrids)
        self.hybrid_hashes = dict(hybrid_hashes)
        self.gate_receipt = dict(gate_receipt)
        # This digest authenticates the frozen Q1+Q3 gate/source closure.  It
        # is deliberately distinct from the current simulator source manifest
        # used to root the physical CRN in the V0.6 prepare/shard runner.
        self.q13_gate_source_manifest_sha256 = q13_gate_source_manifest_sha256

    def make_environment(self, archive: Any, *, users: int) -> Any:
        return self.production_runtime.make_environment(archive, users=users)

    def bind_field(self, wrapped: Any, field: KeyedFadingField) -> Any:
        environment = getattr(wrapped, "environment", wrapped)
        if bool(getattr(environment, "_started", False)):
            raise LiveAdapterError("keyed field must bind before reset")
        environment._fading_field = field
        return environment

    def evaluation_rngs(self, source_seed: int) -> tuple[np.random.Generator, ...]:
        return self.production_runtime.evaluation_rngs(int(source_seed))

    def main_actions(self, trainer: Any, wrapped: Any, states: Any, masks: Any,
                     observation: Any, rng: Any) -> np.ndarray:
        return np.asarray(self.production_runtime.main_actions(trainer, wrapped, states, masks, observation, rng), dtype=np.int64)


def frozen_network_digest(network: Any) -> str:
    """Digest one frozen Q-network's parameters, independent of state data."""
    digest = hashlib.sha256()
    for name, value in sorted(network.state_dict().items(), key=lambda item: str(item[0])):
        array = np.asarray(value.detach().cpu().numpy())
        digest.update(str(name).encode("ascii")); digest.update(b"\0")
        digest.update(str(array.dtype).encode("ascii")); digest.update(b"\0")
        digest.update(json.dumps(list(array.shape), separators=(",", ":")).encode("ascii")); digest.update(b"\0")
        digest.update(np.ascontiguousarray(array).tobytes())
    return digest.hexdigest()


@contextmanager
def authenticated_runtime(*, tle_root: Path, prereg_path: Path, main_dir: Path,
                          gate_dir: Path, source_dir: Path, v03_root: Path,
                          users: int = 100):
    """Load the exact frozen Main/checkpoint/TLE authority, read-only."""
    loader = _source_loader()
    try:
        production_runtime = loader._default_runtime()
    except AttributeError as exc:
        raise LiveAdapterError("V0.4 source runner has no authenticated default runtime") from exc
    try:
        record, prereg_sha = loader._record_and_prereg(prereg_path=Path(prereg_path), record=None)
        main_auth = loader._authenticate_main_authority(Path(main_dir))
    except Exception as exc:
        raise LiveAdapterError(f"frozen authority authentication failed: {exc}") from exc
    with tempfile.TemporaryDirectory(prefix="mcrl-v06-c2-k1-tle-") as temp:
        try:
            archive = production_runtime.frozen_archive(
                record, Path(tle_root), Path(temp) / "frozen-tle")
            trainer, checkpoint = production_runtime.load_trainer(
                record, archive, run_dir=Path(main_dir), users=users)
            checkpoint_sha = loader._checkpoint_sha256(checkpoint)
            if checkpoint_sha != main_auth["checkpoint_file_sha256"]:
                raise LiveAdapterError("loaded checkpoint differs from Main authority")
            phase_b = _phase_b_loader()
            q13_gate = phase_b._authenticate_q13_gate(
                Path(gate_dir), source_dir=Path(source_dir),
                prereg_path=Path(prereg_path), v03_root=Path(v03_root)
            )
            screen = phase_b._screen_module()
            seeds = tuple(phase_b.Q13_INIT_SEEDS)
            hybrids = {}
            selected_hashes = dict(q13_gate.get("selected_hybrid_file_sha256", {}))
            hashes: dict[str, str] = {}
            for index, seed in enumerate(seeds):
                lineage = ("q13-a", "q13-b", "q13-c")[index]
                hybrid = screen.load_gate_selected_hybrid(
                    q13_gate, v03_root=Path(v03_root), initialization_seed=int(seed)
                )
                if (getattr(hybrid, "initialization_seed", int(seed)) != int(seed)
                        or len(tuple(hybrid.q_nets)) != 3 or hybrid.selected_q3_rung != 100):
                    raise LiveAdapterError(f"gate-selected hybrid is not exact Q1+Q3 lineage {lineage}")
                if not isinstance(selected_hashes.get(str(seed)), str) or len(selected_hashes[str(seed)]) != 64:
                    raise LiveAdapterError(f"missing authenticated hybrid digest for {lineage}")
                for network in hybrid.q_nets:
                    network.eval()
                hybrids[lineage] = hybrid
                hashes[lineage] = str(selected_hashes.get(str(seed), ""))
        except Exception as exc:
            raise LiveAdapterError(f"frozen Main/TLE loading failed: {exc}") from exc
        q13_source_manifest_sha = q13_gate.get("source_manifest_sha256")
        if not isinstance(q13_source_manifest_sha, str) or len(q13_source_manifest_sha) != 64:
            raise LiveAdapterError("Q1+Q3 gate lacks authenticated source manifest digest")
        yield DefaultLiveRuntime(loader, production_runtime, record, archive, trainer, checkpoint_sha, prereg_sha,
                                 hybrids, hashes, q13_gate, q13_source_manifest_sha)


def _source_loader() -> Any:
    path = Path(__file__).with_name("run_v04_c3_source.py")
    name = "v04_loader_for_v06_" + hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise LiveAdapterError("cannot load authenticated V0.4 source loader")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def _phase_b_loader() -> Any:
    path = Path(__file__).with_name("run_v04_c2_phase_b.py")
    name = "v04_phase_b_for_v06_" + hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise LiveAdapterError("cannot load authenticated V0.4 Phase-B loader")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def _q13_surfaces(trainer: Any, wrapped: Any, observation: Any, *, interval_s: float,
                  kappa_bits: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return frozen Q1/Q3 surfaces and this branch's native mask."""
    if (not isinstance(getattr(trainer, "initialization_seed", None), (int, np.integer))
            or getattr(trainer, "selected_q3_rung", None) != 100
            or len(tuple(getattr(trainer, "q_nets", ()))) != 3):
        raise LiveAdapterError("Q13 surface request must use a gate-selected rung-100 hybrid")
    env = getattr(wrapped, "environment", wrapped)
    legacy = encode_ee_axis_state(env, observation)
    c3 = encode_ee_axis_v04_c3_state(env, observation, interval_s=interval_s, kappa_bits=kappa_bits)
    masks = np.asarray(observation.masks)
    surfaces = trainer.q_values_by_route(legacy.state_matrix, c3.state_matrix, masks)
    if not isinstance(surfaces, tuple) or len(surfaces) != 3:
        raise LiveAdapterError("frozen trainer did not return exactly Q1/Q2/Q3")
    q1, q2, q3 = (np.asarray(value, dtype=np.float64) for value in surfaces)
    if q1.shape != masks.shape or q3.shape != masks.shape or not np.all(np.isfinite(q1 + q3)):
        raise LiveAdapterError("Q1/Q3 surface shape or finiteness drifted")
    if q2.shape != q1.shape:
        raise LiveAdapterError("resident Q2 surface shape drifted")
    # Deliberately do not read q2.  The local name exists only to assert the
    # three-network API shape and is deleted before action construction.
    del q2
    return q1, q3, masks


def _q13_actions(trainer: Any, wrapped: Any, observation: Any, *, interval_s: float,
                 kappa_bits: float) -> np.ndarray:
    """Infer Q1+Q3 actions independently from this branch observation."""
    q1, q3, masks = _q13_surfaces(trainer, wrapped, observation,
                                  interval_s=interval_s, kappa_bits=kappa_bits)
    return np.asarray([
        masked_argmax(q1[user], q3[user], masks[user], field=f"branch.user{user}")
        for user in range(masks.shape[0])
    ], dtype=np.int64)


def _served(outcome: Any) -> np.ndarray:
    rates = np.asarray(outcome.link_rate_bps, dtype=np.float64)
    if rates.ndim != 1 or not np.all(np.isfinite(rates)):
        raise LiveAdapterError("physics outcome rates are malformed")
    resolution = getattr(outcome, "resolution", None)
    served = getattr(resolution, "served", None)
    if served is None:
        raise LiveAdapterError("physics outcome lacks authoritative resolution.served")
    result = np.asarray(served)
    if result.shape != rates.shape or result.dtype != np.bool_:
        raise LiveAdapterError("resolution.served has wrong shape or dtype")
    return np.array(result, dtype=bool, copy=True)


def _snapshot_networks(trainer: Any) -> tuple[dict[str, np.ndarray], ...]:
    result = []
    for network in tuple(getattr(trainer, "q_nets", ())):
        result.append({str(name): np.asarray(value.detach().cpu().numpy()).copy()
                       for name, value in network.state_dict().items()})
    return tuple(result)


def _same_networks(trainer: Any, before: tuple[dict[str, np.ndarray], ...]) -> bool:
    after = _snapshot_networks(trainer)
    return len(after) == len(before) and all(
        set(left) == set(right) and all(np.array_equal(left[name], right[name]) for name in left)
        for left, right in zip(before, after, strict=True)
    )


def _advance(wrapped: Any, actions: np.ndarray, rng: np.random.Generator, *,
             allow_terminal: bool = False) -> Any:
    result = wrapped.step(actions, rng)
    if bool(result.done) and not allow_terminal:
        raise LiveAdapterError("anchor/continuation reached terminal episode")
    return wrapped.last_outcome


def discover_anchor(runtime: Any, archive: Any, trainer: Any, *, source_seed: int,
                    field: KeyedFadingField, eligible_steps: tuple[int, ...]) -> tuple[int, list[np.ndarray], Any]:
    """Scan only predecision state/masks and return the first eligible anchor.

    Eligibility is structural (the focal row has complete native support),
    never a function of a counterfactual outcome.  The returned history's
    final action is the frozen Main reference at the anchor.
    """
    wrapped = runtime.make_environment(archive, users=runtime.users)
    runtime.bind_field(wrapped, field)
    env_rng, mobility_rng, *_ = runtime.evaluation_rngs(source_seed)
    states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    history: list[np.ndarray] = []
    for _ in range(max(eligible_steps) + 1):
        step = int(observation.step_index)
        reference = np.asarray(runtime.main_actions(trainer, wrapped, states, masks,
                                                     observation, env_rng), dtype=np.int64)
        if step in eligible_steps:
            mask = np.asarray(observation.masks)
            users = [user for user in range(mask.shape[0])
                     if mask[user].shape == (ACTION_COUNT,) and mask[user].dtype == np.bool_
                     and bool(np.all(mask[user]))]
            if users:
                history.append(np.array(reference, copy=True))
                return users[0], history, observation
        history.append(np.array(reference, copy=True))
        _advance(wrapped, reference, env_rng)
        states, masks, observation = (list(wrapped.last_outcome.observation.user_states),
                                      list(wrapped.last_outcome.observation.masks),
                                      wrapped.last_outcome.observation)
    raise LiveAdapterError("no predecision anchor with complete 28-action support")


def replay_main_to_anchor(runtime: Any, archive: Any, trainer: Any, *, source_seed: int,
                          target_step: int, field: KeyedFadingField) -> tuple[Any, list[np.ndarray], Any]:
    """Replay frozen Main to an already selected predecision anchor.

    This is the production prepare producer's state-only seam.  It returns
    the live wrapper, the Main action history including the anchor action, and
    the anchor observation so each authenticated Q13 hybrid can derive its
    own sealed Q1+Q3 score vector without a hand-entered binding file.
    """
    if type(target_step) is not int or target_step < 1:
        raise LiveAdapterError("target_step must be a positive integer")
    wrapped = runtime.make_environment(archive, users=runtime.users)
    runtime.bind_field(wrapped, field)
    env_rng, mobility_rng, *_ = runtime.evaluation_rngs(source_seed)
    states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    history: list[np.ndarray] = []
    while int(observation.step_index) < target_step:
        actions = runtime.main_actions(trainer, wrapped, states, masks, observation, env_rng)
        history.append(np.asarray(actions, dtype=np.int64).copy())
        _advance(wrapped, history[-1], env_rng)
        observation = wrapped.last_outcome.observation
        states = list(observation.user_states)
        masks = list(observation.masks)
    if int(observation.step_index) != target_step:
        raise LiveAdapterError("Main replay did not reach the selected anchor")
    reference = runtime.main_actions(trainer, wrapped, states, masks, observation, env_rng)
    history.append(np.asarray(reference, dtype=np.int64).copy())
    return wrapped, history, observation


def _roll_branch(runtime: Any, archive: Any, hybrid: Any, *, source_seed: int,
                 target_step: int, history: list[np.ndarray], focal_user: int,
                 opening_action: int, field: KeyedFadingField, interval_s: float,
                 kappa_bits: float, end_offset: int = 3) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    """Replay one branch and execute only own-branch Q1+Q3 at k1..k3."""
    if type(end_offset) is not int or end_offset not in (1, 3):
        raise LiveAdapterError("continuation end offset must be 1 or 3")
    wrapped = runtime.make_environment(archive, users=runtime.users)
    runtime.bind_field(wrapped, field)
    env_rng, mobility_rng, *_ = runtime.evaluation_rngs(source_seed)
    states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    # ``history[:-1]`` advances to the sealed anchor; the final entry is the
    # frozen Main reference action at k0 and is replaced only at focal user.
    for actions in history[:-1]:
        _advance(wrapped, np.asarray(actions, dtype=np.int64), env_rng)
        states, masks, observation = (list(wrapped.last_outcome.observation.user_states),
                                      list(wrapped.last_outcome.observation.masks),
                                      wrapped.last_outcome.observation)
    opening = np.array(history[-1], dtype=np.int64, copy=True)
    opening[focal_user] = opening_action
    outcomes = [_advance(wrapped, opening, env_rng)]
    actions = [opening]
    q13_k1: dict[str, Any] | None = None
    for offset in range(1, end_offset + 1):
        observation = outcomes[-1].observation
        q1_surface, q3_surface, branch_masks = _q13_surfaces(
            hybrid, wrapped, observation, interval_s=interval_s, kappa_bits=kappa_bits)
        own = np.asarray([
            masked_argmax(q1_surface[user], q3_surface[user], branch_masks[user],
                          field=f"branch.user{user}")
            for user in range(branch_masks.shape[0])
        ], dtype=np.int64)
        if q13_k1 is None:
            q13_k1 = {"q1": q1_surface, "q3": q3_surface, "mask": branch_masks}
        if own.shape != opening.shape:
            raise LiveAdapterError("branch-local Q1+Q3 vector shape drifted")
        actions.append(own)
        # A terminal outcome at k3 is a valid four-offset trace endpoint.
        # Any earlier terminal outcome is a premature, fail-closed source.
        outcomes.append(_advance(wrapped, own, env_rng,
                                 allow_terminal=(offset == 3)))
    rates = np.asarray([outcome.link_rate_bps for outcome in outcomes], dtype=np.float64)
    power = np.asarray([outcome.system_power_w for outcome in outcomes], dtype=np.float64)
    served = np.asarray([_served(outcome) for outcome in outcomes], dtype=bool)
    if q13_k1 is None:
        raise LiveAdapterError("continuation did not produce a k1 Q1+Q3 surface")
    expected_k1 = np.asarray([
        masked_argmax(q13_k1["q1"][user], q13_k1["q3"][user],
                      q13_k1["mask"][user], field=f"persisted-k1.user{user}")
        for user in range(q13_k1["mask"].shape[0])
    ], dtype=np.int64)
    if not np.array_equal(expected_k1, np.asarray(actions[1], dtype=np.int64)):
        raise LiveAdapterError("executed k1 actions disagree with persisted Q1+Q3 decision")
    return rates, power, served, {
        "actions": [row.tolist() for row in actions],
        "q13_actions_k1": expected_k1.tolist(),
        "q1_k1": q13_k1["q1"].tolist(), "q3_k1": q13_k1["q3"].tolist(),
        "mask_k1": q13_k1["mask"].tolist(),
    }


def run_one_anchor_lineage(runtime: Any, archive: Any, hybrid: Any, *, source_seed: int,
                           target_step: int, focal_user: int, history: list[np.ndarray],
                           field: KeyedFadingField, interval_s: float, kappa_bits: float,
                           lambda_bits_per_j: float, hybrid_sha256: str = "") -> dict[str, Any]:
    """Produce one real physical lineage using the exact future shard path.

    This smoke path deliberately requires all 28 focal actions to be legal at
    the sealed anchor.  If the native action mask does not provide that
    support, it fails closed instead of silently shrinking the promised 28.
    """
    if len(history) != target_step + 1:
        raise LiveAdapterError("history does not reach the sealed anchor")
    if type(focal_user) is not int or focal_user < 0:
        raise LiveAdapterError("focal user is malformed")
    wrapped = runtime.make_environment(archive, users=runtime.users)
    runtime.bind_field(wrapped, field)
    env_rng, mobility_rng, *_ = runtime.evaluation_rngs(source_seed)
    states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    for actions in history:
        if int(observation.step_index) == target_step:
            break
        _advance(wrapped, np.asarray(actions, dtype=np.int64), env_rng)
        observation = wrapped.last_outcome.observation
    mask = np.asarray(observation.masks[focal_user])
    if mask.shape != (ACTION_COUNT,) or mask.dtype != np.bool_ or not np.all(mask):
        raise LiveAdapterError("one-anchor smoke lacks complete 28-action native support")
    reference = np.asarray(history[-1], dtype=np.int64)
    if reference.shape != (runtime.users,):
        raise LiveAdapterError("reference action vector is malformed")
    q1, q3, anchor_mask = _q13_surfaces(hybrid, wrapped, observation,
                                         interval_s=interval_s, kappa_bits=kappa_bits)
    before = _snapshot_networks(hybrid)
    q1_digest = frozen_network_digest(hybrid.q_nets[0])
    q3_digest = frozen_network_digest(hybrid.q_nets[2])
    policy_digest = canonical_sha256({
        "q1_sha256": q1_digest, "q3_sha256": q3_digest,
        "hybrid_sha256": hybrid_sha256, "initialization_seed": int(hybrid.initialization_seed),
    })
    branch_rows = []
    reference_action = int(reference[focal_user])
    # The Main gauge is identical for every candidate row.  One deterministic
    # replay is sufficient; re-running it 28 times only inflates the batch
    # without changing the matched estimand.
    ref_rates, ref_power, ref_served, ref_actions = _roll_branch(
        runtime, archive, hybrid, source_seed=source_seed, target_step=target_step,
        history=history, focal_user=focal_user, opening_action=reference_action,
        field=field, interval_s=interval_s, kappa_bits=kappa_bits, end_offset=1)
    for action in range(ACTION_COUNT):
        if action == reference_action:
            cand_rates, cand_power, cand_served, cand_actions = (
                ref_rates.copy(), ref_power.copy(), ref_served.copy(),
                {key: (value.copy() if isinstance(value, list) else value)
                 for key, value in ref_actions.items()})
        else:
            cand_rates, cand_power, cand_served, cand_actions = _roll_branch(
                runtime, archive, hybrid, source_seed=source_seed, target_step=target_step,
                history=history, focal_user=focal_user, opening_action=action,
                field=field, interval_s=interval_s, kappa_bits=kappa_bits, end_offset=1)
        z = c2_k1_surplus_bits(cand_rates[1], ref_rates[1], cand_power[1], ref_power[1],
                               interval_s=interval_s, lambda_bits_per_j=lambda_bits_per_j)
        if action == reference_action:
            # The Main gauge row is not a new counterfactual.  It must reuse
            # the exact reference branch bytes and remain an all-zero pair.
            if not (np.array_equal(cand_rates, ref_rates)
                    and np.array_equal(cand_power, ref_power)
                    and np.array_equal(cand_served, ref_served)
                    and cand_actions["actions"] == ref_actions["actions"]):
                raise LiveAdapterError("a=a_M row is not bitwise reference=reference")
            if z != 0.0:
                raise LiveAdapterError("a=a_M row has nonzero k1 surplus")
        delta0 = cand_rates[0] - ref_rates[0]
        z1 = interval_s * float(delta0[focal_user]) - lambda_bits_per_j * interval_s * (cand_power[0] - ref_power[0])
        z3 = interval_s * float(np.sum(np.delete(delta0, focal_user)))
        g0 = interval_s * float(np.sum(delta0)) - lambda_bits_per_j * interval_s * (cand_power[0] - ref_power[0])
        branch_rows.append({"opening_action": action, "reference_action": int(reference[focal_user]),
                            "z2_k1_bits": z, "z2_k1_normalized": z / kappa_bits,
                            # The opening surface is frozen and identical for
                            # all 28 action rows.  Persist the focal slice so
                            # downstream generation can compare it bitwise to
                            # the prepare-live seal rather than recomputing it.
                            "q1_k0": q1[focal_user].tolist(),
                            "q3_k0": q3[focal_user].tolist(),
                            "mask_k0": anchor_mask[focal_user].tolist(),
                            "crn_sha256": field.root_digest,
                            "policy_sha256": policy_digest,
                            "candidate_rates_k0": cand_rates[0].tolist(), "reference_rates_k0": ref_rates[0].tolist(),
                            "candidate_power_k0": float(cand_power[0]), "reference_power_k0": float(ref_power[0]),
                            "candidate_rates_k1": cand_rates[1].tolist(), "reference_rates_k1": ref_rates[1].tolist(),
                            "candidate_power_k1": float(cand_power[1]), "reference_power_k1": float(ref_power[1]),
                            "main_gauge": {"z1_bits": z1, "z3_bits": z3, "z2_k1_bits": z,
                                           "g0_bits": g0, "g1_bits": z,
                                           "identity_residual_bits": z1 + z3 + z - g0 - z,
                                           "identity_passed": bool(abs(z1 + z3 + z - g0 - z) <= 1e-9 * max(abs(g0 + z), 1.0)),
                                           "identity_rel_tolerance": 1e-9},
                            "candidate_rates": cand_rates.tolist(), "reference_rates": ref_rates.tolist(),
                            "candidate_power": cand_power.tolist(), "reference_power": ref_power.tolist(),
                            "candidate_served": cand_served.tolist(), "reference_served": ref_served.tolist(),
                            "candidate_actions": cand_actions["actions"], "reference_actions": ref_actions["actions"],
                            "candidate_k0_executed_actions": cand_actions["actions"][0],
                            "reference_k0_executed_actions": ref_actions["actions"][0],
                            "k0_action_mask": anchor_mask.tolist(),
                            "candidate_k1_executed_actions": cand_actions["actions"][1],
                            "reference_k1_executed_actions": ref_actions["actions"][1],
                            "candidate_k1_q13_actions": cand_actions["q13_actions_k1"],
                            "reference_k1_q13_actions": ref_actions["q13_actions_k1"],
                            # Persist the complete all-user Q1+Q3 evidence so
                            # the formal adjudicator can derive every k1
                            # action independently, including legal NO_OP=-1
                            # when a user's native mask is empty.
                            "candidate_k1_q13_sum": (
                                np.asarray(cand_actions["q1_k1"], dtype=np.float64)
                                + np.asarray(cand_actions["q3_k1"], dtype=np.float64)
                            ).tolist(),
                            "candidate_k1_q13_mask": cand_actions["mask_k1"],
                            "reference_k1_q13_sum": (
                                np.asarray(ref_actions["q1_k1"], dtype=np.float64)
                                + np.asarray(ref_actions["q3_k1"], dtype=np.float64)
                            ).tolist(),
                            "reference_k1_q13_mask": ref_actions["mask_k1"],
                            "candidate_q1_k1": cand_actions["q1_k1"][focal_user],
                            "candidate_q3_k1": cand_actions["q3_k1"][focal_user],
                            "candidate_mask_k1": cand_actions["mask_k1"][focal_user],
                            "reference_q1_k1": ref_actions["q1_k1"][focal_user],
                            "reference_q3_k1": ref_actions["q3_k1"][focal_user],
                            "reference_mask_k1": ref_actions["mask_k1"][focal_user]})
    if not _same_networks(hybrid, before):
        raise LiveAdapterError("live source mutated frozen Q1/Q2/Q3 bytes")
    z = np.asarray([row["z2_k1_normalized"] for row in branch_rows], dtype=np.float64)
    oracle, drop = oracle_and_drop_scores(q1[focal_user], q3[focal_user], z,
                                          anchor_mask[focal_user])
    oracle_row = branch_rows[oracle]
    drop_row = branch_rows[drop]
    # Only the two selected openings are allowed to continue to k2/k3.  The
    # 28 rows above contain k0/k1 physics solely for the action-target census;
    # selected rows are replaced by their four-offset replays here.
    selected_full: dict[str, dict[str, Any]] = {}
    reference_full = _roll_branch(
        runtime, archive, hybrid, source_seed=source_seed, target_step=target_step,
        history=history, focal_user=focal_user, opening_action=reference_action,
        field=field, interval_s=interval_s, kappa_bits=kappa_bits, end_offset=3)
    for name, selected_action in (("oracle", oracle), ("drop", drop)):
        if name == "drop" and drop == oracle:
            selected_full[name] = dict(selected_full["oracle"])
            continue
        cand_rates, cand_power, cand_served, cand_actions = _roll_branch(
            runtime, archive, hybrid, source_seed=source_seed, target_step=target_step,
            history=history, focal_user=focal_user, opening_action=selected_action,
            field=field, interval_s=interval_s, kappa_bits=kappa_bits, end_offset=3)
        ref_rates_full, ref_power_full, ref_served_full, ref_actions_full = reference_full
        selected_full[name] = {"candidate_rates": cand_rates.tolist(), "candidate_power": cand_power.tolist(),
                              "candidate_served": cand_served.tolist(), "reference_rates": ref_rates_full.tolist(),
                              "reference_power": ref_power_full.tolist(), "reference_served": ref_served_full.tolist(),
                              "candidate_actions": cand_actions["actions"], "reference_actions": ref_actions_full["actions"]}
    if not _same_networks(hybrid, before):
        raise LiveAdapterError(
            "selected continuation mutated frozen Q1/Q2/Q3 bytes")
    controls = {
        "oracle_action": oracle, "drop_c2_action": drop,
        "oracle_drop_tie": oracle == drop, "tie_trace_reused": oracle == drop,
        "oracle_metrics": four_offset_metrics(selected_full["oracle"]["candidate_rates"], selected_full["oracle"]["candidate_power"],
                                                selected_full["oracle"]["candidate_served"], interval_s=interval_s),
        "drop_metrics": four_offset_metrics(selected_full["drop"]["candidate_rates"], selected_full["drop"]["candidate_power"],
                                             selected_full["drop"]["candidate_served"], interval_s=interval_s),
        "reference_oracle_metrics": four_offset_metrics(selected_full["oracle"]["reference_rates"], selected_full["oracle"]["reference_power"],
                                                          selected_full["oracle"]["reference_served"], interval_s=interval_s),
        "reference_drop_metrics": four_offset_metrics(selected_full["drop"]["reference_rates"], selected_full["drop"]["reference_power"],
                                                       selected_full["drop"]["reference_served"], interval_s=interval_s),
        "selected_four_offset_replays": selected_full,
    }
    # Bind each selected trace only to the opening row that actually produced
    # it.  Persist the action vectors as well as the physical arrays so the
    # final verifier can prove that the sealed trace belongs to a_D/a_O.
    for name, selected_action in (("oracle", oracle), ("drop", drop)):
        row = branch_rows[selected_action]
        trace = selected_full[name]
        row[f"{name}_rates_bps"] = trace["candidate_rates"]
        row[f"{name}_power_w"] = trace["candidate_power"]
        row[f"{name}_served"] = trace["candidate_served"]
        row[f"{name}_actions"] = trace["candidate_actions"]
        row[f"{name}_reference_rates_bps"] = trace["reference_rates"]
        row[f"{name}_reference_power_w"] = trace["reference_power"]
        row[f"{name}_reference_served"] = trace["reference_served"]
        row[f"{name}_reference_actions"] = trace["reference_actions"]
    return {"schema": "multi-catfish-mcrl-v06-c2-k1-live-lineage-v1",
            "source_seed": source_seed, "target_step": target_step,
            "focal_user": focal_user, "opening_rows": branch_rows,
            "control": controls, "q2_consulted": False,
            "lineage_initialization_seed": int(getattr(hybrid, "initialization_seed")),
            "crn_sha256": field.root_digest,
            "hold_tape_release_compositor": False,
            "frozen_networks_unchanged": True}


__all__ = ["LiveAdapterError", "frozen_network_digest", "replay_main_to_anchor", "run_one_anchor_lineage"]
