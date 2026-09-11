"""CF-ratio learner: three physical-quantity heads + three catfish (CF3PILOT).

Frozen design: ``.scratch/multi-catfish-v025-physics-successor/
V025-CONTROLLER-DECLARATION-THREE-CATFISH-PILOT-2026-09-11.md``; every
choice the declaration leaves open is written in
``.scratch/cf3-pilot/DECLARATION-ADDENDUM.md`` (before launch).

This is a NEW trainer composed on :class:`~mcrl.algorithms.modqn.MODQNTrainer`
(same environment contract, state encoder, masks, ``DQNNetwork`` class,
Adam optimisers, replay buffer, epsilon function, target sync, checkpoint
helpers).  ``modqn.py`` is not edited.

Heads, fixed order ``(B, E, H)``, reward vector per user-step:

* ``B_u = R_u * dt``  — user u's decoded bits (0 when unserved);
* ``E_u = P_sys * dt / U`` — system joules shared equally, so ``sum_u E_u``
  is the evaluator's denominator exactly (every user carries a share,
  served or not: that is the declared D-2 adaptation);
* ``H_u = 1`` iff u's step is an inter-satellite handover
  (``HandoverClass.INTER_SATELLITE``, the C-H quantity), else 0.

Replay stores the RAW ``(B, E, H)``.  At sample time rewards are divided by
fixed declared units ``(s_B, s_E, 1)`` (computed once, before training, on
the calibration seeds) and every head's target is

    y_k = r_k / s_k + gamma * Qtgt_k(s', a*) * (1 - done),
    a*  = argmax_{a legal} [Qtgt_B - eta~ Qtgt_E - lambda Qtgt_H](s', a)

with the CURRENT ``eta``, ``lambda`` (shared continuation, D-1 ON).  The
action rule is the same combination on the online heads.  ``eta~ = eta *
s_E / s_B`` is ``eta`` (bit/J) expressed in the heads' units; ``lambda``
multiplies ``Q_H`` in the same normalised score (one unit = ``s_B`` bits per
inter-satellite handover).

Catfish: each source runs its scripted rule in its OWN environment copy
(same seed values as the main), pushes unshaped raw ``(B, E, H)``
transitions into its OWN buffer, and head k's minibatch is
``batch - n_cf`` rows of main replay (one draw, shared by the three heads)
plus ``n_cf = round(rho * batch)`` rows from the buffer of the source routed
to head k.  Sources never touch the trainer's generators, so with
``rho = 0`` the trainer is bit-identical to OFF.
"""

from __future__ import annotations

import copy
import dataclasses
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch

from ..env.action_contract import HandoverClass, is_no_op
from ..env.constants import DECISION_STEP_S
from ..errors import MCRLContractError
from ..runtime.finiteness import (
    assert_finite_gradients,
    assert_finite_loss,
    assert_finite_parameters,
)
from ..runtime.replay_buffer import ReplayBuffer
from ..runtime.trainer_config_validation import TD_BOOTSTRAP_SHARED
from ..runtime.trainer_spec import TrainerConfig
from .cf_sources import (
    CF3_SPECS,
    HEAD_B,
    HEAD_E,
    HEAD_H,
    SourcePolicy,
    cf3_policies,
    random_legal,
)
from .modqn import MODQNTrainer

DT_S: float = float(DECISION_STEP_S)
H_CAP_INTER: float = 0.6016
"""C-H: inter-satellite handovers per user-step (declared, not tuned)."""

SOURCE_KINDS = ("none", "cf3", "null3")
NULL_RNG_OFFSET = 80_000
CATFISH_SAMPLING_RNG_OFFSET = 70_001


# ------------------------------------------------------------------ rewards
def cf_reward_matrix(result, outcome, *, dt: float = DT_S) -> np.ndarray:
    """``(U, 3)`` raw ``(B_u, E_u, H_u)`` for one step (float64).

    ``result`` is the trainer's ``StepResult``; ``outcome`` is
    ``env.last_outcome`` for the same step (energy + handover classes).
    """
    users = len(result.rewards)
    energy = outcome.energy
    served = result.served
    if served is None:
        raise MCRLContractError("cf_reward_matrix needs StepResult.served (D-2)")
    out = np.zeros((users, 3), dtype=np.float64)
    e_share = float(energy.system_consumed_power_w) * dt / users
    for uid in range(users):
        rate = float(result.rewards[uid].r1_throughput)
        # D-2 adaptation: an unserved user decodes nothing.
        out[uid, HEAD_B] = rate * dt if bool(served[uid]) else 0.0
        out[uid, HEAD_E] = e_share
        out[uid, HEAD_H] = (
            1.0 if outcome.handovers[uid] is HandoverClass.INTER_SATELLITE else 0.0
        )
    return out


# ------------------------------------------------------------------ settings
@dataclass(frozen=True)
class CFRatioSettings:
    """Everything the CF-ratio learner adds to ``TrainerConfig``."""

    source_kind: str = "none"          # none | cf3 | null3
    rho: float = 1.0 / 9.0
    alpha: float = 1.0
    h_cap_inter: float = H_CAP_INTER
    quarter_episodes: int = 250
    eta_first_update_episode: int = 500   # Amendment 1 item 3
    catfish_buffer_capacity: int = 50_000
    eta0: float = 1.0                  # bit/J, MAX_NOMINAL_GAIN on calibration
    bits_scale: float = 1.0            # s_B, bits per user-step
    joules_scale: float = 1.0          # s_E, joules per user-step
    lambda0: float = 0.0
    calibration_env_seed_base: int = 9_121_000
    calibration_mobility_seed_base: int = 9_122_000
    calibration_episodes: int = 24

    def __post_init__(self) -> None:
        if self.source_kind not in SOURCE_KINDS:
            raise MCRLContractError(f"source_kind must be one of {SOURCE_KINDS}")
        if not 0.0 <= self.rho < 1.0:
            raise MCRLContractError("rho must be in [0, 1)")
        for name in ("eta0", "bits_scale", "joules_scale"):
            if not (np.isfinite(getattr(self, name)) and getattr(self, name) > 0):
                raise MCRLContractError(f"{name} must be finite and positive")


# ------------------------------------------------------------------ sources
class ExperienceSource:
    """One scripted source in its own environment copy with its own buffer."""

    def __init__(
        self,
        name: str,
        head: int,
        policy: SourcePolicy,
        env,
        *,
        env_seed: int,
        mobility_seed: int,
        capacity: int,
        encode: Callable,
        policy_rng: np.random.Generator | None = None,
    ) -> None:
        self.name = name
        self.head = int(head)
        self.policy = policy
        self.env = env
        self.env_rng = np.random.default_rng(env_seed)
        self.mobility_rng = np.random.default_rng(mobility_seed)
        self.policy_rng = policy_rng
        self.buffer = ReplayBuffer(int(capacity))
        self._encode = encode           # encode(states, t)
        self._t = 0
        self._states = self._masks = self._enc = None
        self.episode_totals = np.zeros(3, dtype=np.float64)
        self.episode_user_steps = 0

    def reset(self) -> None:
        states, masks, _ = self.env.reset(self.env_rng, self.mobility_rng)
        self._states, self._masks = states, masks
        self._t = 0
        self._enc = self._encode(states, 0)
        self.episode_totals = np.zeros(3, dtype=np.float64)
        self.episode_user_steps = 0

    def step(self) -> bool:
        actions = self.policy(self._states, self._masks)
        result = self.env.step(actions, self.env_rng)
        raw = cf_reward_matrix(result, self.env.last_outcome)
        self._t += 1
        next_enc = self._encode(result.user_states, self._t)
        self.episode_totals += raw.sum(axis=0)
        self.episode_user_steps += len(raw)
        for uid in range(len(raw)):
            if is_no_op(int(actions[uid])):
                continue
            next_mask = result.action_masks[uid].mask
            if not bool(result.done) and not bool(next_mask.any()):
                continue
            self.buffer.push(
                self._enc[uid],
                int(actions[uid]),
                raw[uid].copy(),
                next_enc[uid],
                self._masks[uid].mask.copy(),
                next_mask.copy(),
                bool(result.done),
            )
        self._states = result.user_states
        self._masks = result.action_masks
        self._enc = next_enc
        return bool(result.done)

    def state_dict(self) -> dict[str, Any]:
        env_state = getattr(self.env, "training_state_dict", None)
        return {
            "name": self.name,
            "head": self.head,
            "env_rng": copy.deepcopy(self.env_rng.bit_generator.state),
            "mobility_rng": copy.deepcopy(self.mobility_rng.bit_generator.state),
            "policy_rng": (
                None if self.policy_rng is None
                else copy.deepcopy(self.policy_rng.bit_generator.state)
            ),
            "env_state": copy.deepcopy(env_state()) if callable(env_state) else None,
            "buffer": self.buffer.state_dict(),
        }

    def load_state_dict(self, state: dict[str, Any]) -> None:
        if state["name"] != self.name or int(state["head"]) != self.head:
            raise MCRLContractError("source state does not match this source")
        self.env_rng.bit_generator.state = copy.deepcopy(state["env_rng"])
        self.mobility_rng.bit_generator.state = copy.deepcopy(state["mobility_rng"])
        if self.policy_rng is not None:
            self.policy_rng.bit_generator.state = copy.deepcopy(state["policy_rng"])
        if state["env_state"] is not None:
            self.env.load_training_state_dict(copy.deepcopy(state["env_state"]))
        self.buffer.load_state_dict(state["buffer"])


def build_sources(
    kind: str,
    *,
    env_factory: Callable[[], Any],
    env_seed: int,
    mobility_seed: int,
    train_seed: int,
    capacity: int,
    encode: Callable,
) -> list[ExperienceSource]:
    """Declared routing ``C1 -> Q_B, C2 -> Q_H, C3 -> Q_E``; NULL3 identical
    except each policy is random-legal on its own generator."""
    if kind == "none":
        return []
    rules = cf3_policies()
    sources = []
    for k, (name, head) in enumerate(CF3_SPECS):
        if kind == "cf3":
            policy, prng, label = rules[name], None, name
        elif kind == "null3":
            prng = np.random.default_rng(train_seed + NULL_RNG_OFFSET + k)
            policy, label = random_legal(prng), f"NULL{k + 1}_for_{name}"
        else:
            raise MCRLContractError(f"unknown source kind {kind!r}")
        sources.append(
            ExperienceSource(
                label, head, policy, env_factory(),
                env_seed=env_seed, mobility_seed=mobility_seed,
                capacity=capacity, encode=encode, policy_rng=prng,
            )
        )
    return sources


# ------------------------------------------------------------------ rollouts
def episode_seeds(env_base: int, mobility_base: int, n: int) -> list[tuple[int, int]]:
    """Per-episode seeds ``(env_base + i, mobility_base + i)``, i = 0..n-1."""
    return [(int(env_base) + i, int(mobility_base) + i) for i in range(int(n))]


def pooled_rollout(
    policy_factory: Callable[[int], Callable[[np.ndarray, list, list], np.ndarray]],
    *,
    env_factory: Callable[[], Any],
    encode: Callable,
    seeds: Sequence[tuple[int, int]] | None = None,
    stream: tuple[int, int, int] | None = None,
) -> dict[str, Any]:
    """Pooled bits / pooled joules (divided once), plus the reported extras.

    Two modes, exactly one of which is given:

    * ``seeds`` (DECLARED, CF3PILOT addendum): every episode i runs on a FRESH
      environment with ``env_rng = default_rng(seeds[i][0])`` and
      ``mobility_rng = default_rng(seeds[i][1])``, so every arm starts every
      episode from the same epoch, population, warm-start ages and fading
      stream position -- pairing holds at every episode, not only episode 0.
    * ``stream = (env_seed, mobility_seed, n)``: the B0 harness's convention
      (one env, one generator pair carried across n episodes).  Kept only for
      the placebo that shows this function computes the harness's estimand
      bit-for-bit.

    ``policy_factory(i)`` returns the policy for episode i
    (``policy(encoded, masks, states) -> actions``).  Bits and joules come
    from ``env.last_outcome.energy``; no trainer generator is consumed.
    """
    if (seeds is None) == (stream is None):
        raise ValueError("give exactly one of seeds / stream")
    if stream is not None:
        env = env_factory()
        env_rng = np.random.default_rng(stream[0])
        mobility_rng = np.random.default_rng(stream[1])
        plan = [(env, env_rng, mobility_rng)] * int(stream[2])
    else:
        plan = None
    n = len(seeds) if seeds is not None else int(stream[2])
    rows = []
    for i in range(n):
        if plan is not None:
            env, env_rng, mobility_rng = plan[i]
        else:
            env = env_factory()
            env_rng = np.random.default_rng(seeds[i][0])
            mobility_rng = np.random.default_rng(seeds[i][1])
        users, steps = env.config.num_users, env.config.steps_per_episode
        policy = policy_factory(i)
        states, masks, _ = env.reset(env_rng, mobility_rng)
        enc = encode(states, 0)
        epoch = getattr(env, "epoch", None)
        import hashlib
        t0_hash = hashlib.sha256(np.ascontiguousarray(enc).tobytes()).hexdigest()
        row = {"bits": 0.0, "joules": 0.0, "served": 0, "user_steps": 0,
               "h_inter": 0, "h_intra": 0, "beams": 0.0, "steps": 0,
               "epoch": None if epoch is None else str(epoch),
               "t0_obs_sha256": t0_hash}
        for t in range(steps):
            actions = policy(enc, masks, states)
            res = env.step(actions, env_rng)
            out = env.last_outcome
            e = out.energy
            row["bits"] += float(e.system_throughput_bps) * DT_S
            row["joules"] += float(e.system_consumed_power_w) * DT_S
            row["served"] += int(e.served)
            row["beams"] += float(e.eff_beams)
            row["steps"] += 1
            row["user_steps"] += users
            for cls in out.handovers:
                row["h_inter"] += int(cls is HandoverClass.INTER_SATELLITE)
                row["h_intra"] += int(cls is HandoverClass.INTRA_SATELLITE)
            states, masks = res.user_states, res.action_masks
            enc = encode(states, t + 1)
            if res.done:
                break
        rows.append(row)
    # Plain left-to-right accumulation, exactly as the B0 harness does
    # (``bits += eb``).  NOT ``sum()``: since Python 3.12 ``sum`` of floats is
    # compensated (Neumaier) and differs from the harness in the last ulp.
    bits = 0.0
    joules = 0.0
    beams_total = 0.0
    for r in rows:
        bits += r["bits"]
        joules += r["joules"]
        beams_total += r["beams"]
    us = sum(r["user_steps"] for r in rows)
    return {
        "bits": bits,
        "joules": joules,
        "ee": bits / joules,
        "h_inter": sum(r["h_inter"] for r in rows) / us,
        "h_intra": sum(r["h_intra"] for r in rows) / us,
        "served": sum(r["served"] for r in rows) / us,
        "beams": beams_total / sum(r["steps"] for r in rows),
        "user_steps": us,
        "bits_per_user_step": bits / us,
        "joules_per_user_step": joules / us,
        "ee_ep": [r["bits"] / r["joules"] if r["joules"] > 0 else float("nan") for r in rows],
        "episodes": rows,
        "n_episodes": n,
    }


# ------------------------------------------------------------------ trainer
class LearningCheckStop(RuntimeError):
    """Raised at the first eta update when the declared learning check fails."""


class CFRatioTrainer(MODQNTrainer):
    """A1 OFF (``source_kind='none'``), A2 CF3, A3 NULL3.

    Amendment 1: ``gamma = 1`` with a true terminal at the 10th step, and the
    observation gains ONE feature -- the normalised remaining steps
    ``(T - t) / T`` -- because the 112-dim encoding carries no step index
    and finite-horizon values depend on the time left.  Replay is a common
    vector replay: every source transition trains all three heads.
    """

    def __init__(
        self,
        env,
        config: TrainerConfig,
        settings: CFRatioSettings,
        *,
        env_factory: Callable[[], Any] | None = None,
        train_seed: int = 42,
        env_seed: int = 1337,
        mobility_seed: int = 7,
        device: str = "cpu",
    ) -> None:
        if config.td_bootstrap_mode != TD_BOOTSTRAP_SHARED:
            raise MCRLContractError(
                "the CF-ratio learner is declared with the shared continuation "
                "bootstrap (D-1 flag ON)"
            )
        super().__init__(
            env, config, train_seed=train_seed, env_seed=env_seed,
            mobility_seed=mobility_seed, device=device,
        )
        # Rebuild the three networks one input wider (remaining-steps
        # feature), from the same seed, with the same class and optimiser.
        import torch.nn as nn
        import torch.optim as optim
        from ..runtime.q_network import DQNNetwork

        self.base_state_dim = self.state_dim
        self.state_dim = self.base_state_dim + 1
        torch.manual_seed(train_seed)
        self.q_nets = nn.ModuleList([
            DQNNetwork(self.state_dim, self.action_dim,
                       config.hidden_layers, config.activation).to(self.device)
            for _ in range(3)
        ])
        self.target_nets = nn.ModuleList([copy.deepcopy(q) for q in self.q_nets])
        for t in self.target_nets:
            t.eval()
        self.optimizers = [
            optim.Adam(self.q_nets[i].parameters(), lr=config.learning_rate)
            for i in range(3)
        ]

        self.settings = settings
        self.eta = float(settings.eta0)
        self.lam = float(settings.lambda0)
        self._env_factory = env_factory
        self._catfish_rng = np.random.default_rng(
            train_seed + CATFISH_SAMPLING_RNG_OFFSET
        )
        if settings.source_kind != "none" and env_factory is None:
            raise MCRLContractError("catfish arms need an env_factory")
        self.sources = build_sources(
            settings.source_kind,
            env_factory=env_factory,
            env_seed=env_seed,
            mobility_seed=mobility_seed,
            train_seed=train_seed,
            capacity=settings.catfish_buffer_capacity,
            encode=self.encode_at,
        ) if settings.source_kind != "none" else []
        # Amendment 1 item 2: 1/27 of the batch from EACH source, rounded to
        # nearest (128/27 = 4.74 -> 5), the main replay takes the rest (113).
        self.n_per_source = (
            int(round(settings.rho / 3.0 * config.batch_size)) if self.sources else 0
        )
        self.n_main = config.batch_size - self.n_per_source * len(self.sources)
        self._units = np.array(
            [settings.bits_scale, settings.joules_scale, 1.0], dtype=np.float64
        )
        self.dual_trajectory: list[dict[str, Any]] = [
            {"episode": 0, "eta": self.eta, "lambda": self.lam, "kind": "initial"}
        ]
        self._last_batch: dict[str, np.ndarray] | None = None
        self.learning_gate: Callable[[int, dict], None] | None = None

    # -- observation -------------------------------------------------------
    def encode_at(self, states, t: int) -> np.ndarray:
        """112-dim MODQN encoding + ``(T - t) / T`` (t = decision index)."""
        base = self._encode_states(states)
        steps = self.env.config.steps_per_episode
        rem = np.full((len(base), 1), (steps - int(t)) / steps, dtype=np.float32)
        return np.concatenate([base, rem], axis=1)

    # -- objective -------------------------------------------------------
    @property
    def eta_tilde(self) -> float:
        return self.eta * self.settings.joules_scale / self.settings.bits_scale

    def _combine(self, qb, qe, qh, *, lam=None):
        lam = self.lam if lam is None else lam
        return qb - self.eta_tilde * qe - lam * qh

    def combined_q_values(self, states_encoded: np.ndarray, *, lam=None) -> np.ndarray:
        q = self._predict_objective_q_values(states_encoded)
        return self._combine(q[HEAD_B], q[HEAD_E], q[HEAD_H], lam=lam)

    def select_actions(self, states_encoded, masks, eps, *,
                       objective_weights=None, raw_states=None):
        """epsilon-greedy masked ``argmax [Q_B - eta Q_E - lambda Q_H]``."""
        del objective_weights, raw_states
        return self._select_unconstrained_actions(
            self.combined_q_values(states_encoded), masks, eps
        )

    def greedy_actions(self, states_encoded, masks, *, lam=None) -> np.ndarray:
        """The deployed rule, consuming NO generator."""
        from ..env.action_contract import NO_OP_ACTION, no_op_actions
        combined = self.combined_q_values(states_encoded, lam=lam)
        out = no_op_actions(len(masks))
        for uid in range(len(masks)):
            sel = self._select_masked_greedy_action(combined[uid], masks[uid].mask)
            out[uid] = NO_OP_ACTION if sel is None else sel
        return out

    def _shared_continuation_action(self, ns, nm):
        """``argmax_a [Qtgt_B - eta~ Qtgt_E - lambda Qtgt_H](s', a)``, legal."""
        with torch.no_grad():
            score = self._combine(
                self.target_nets[HEAD_B](ns),
                self.target_nets[HEAD_E](ns),
                self.target_nets[HEAD_H](ns),
            )
            score = score.masked_fill(~nm, -1e9)
            return score.argmax(dim=1, keepdim=True)

    # -- replay ------------------------------------------------------------
    def _normalise(self, raw: np.ndarray) -> np.ndarray:
        return (np.asarray(raw, dtype=np.float64) / self._units).astype(np.float32)

    def _assemble_batch(self) -> dict[str, np.ndarray] | None:
        """One common minibatch for all three heads, or None if too small.

        ``source`` tags each row: -1 main replay, i = ``self.sources[i]``.
        """
        cfg = self.config
        if len(self.replay) < cfg.batch_size:
            return None
        if self.n_per_source and any(
            len(s.buffer) < self.n_per_source for s in self.sources
        ):
            return None
        parts = [self.replay.sample(self.n_main, self._train_rng)]
        tags = [np.full(self.n_main, -1, dtype=np.int64)]
        if self.n_per_source:
            for i, src in enumerate(self.sources):
                parts.append(src.buffer.sample(self.n_per_source, self._catfish_rng))
                tags.append(np.full(self.n_per_source, i, dtype=np.int64))
        fields = [
            np.concatenate([np.asarray(p[k]) for p in parts]) for k in range(7)
        ]
        st, act, rew, ns, _m, nm, dn = fields
        return {
            "states": st.astype(np.float32), "actions": act.astype(np.int64),
            "rewards_raw": rew, "next_states": ns.astype(np.float32),
            "next_masks": nm.astype(bool), "dones": dn.astype(np.float32),
            "source": np.concatenate(tags),
        }

    def continuation_actions(self, batch) -> torch.Tensor:
        ns = torch.tensor(batch["next_states"], dtype=torch.float32, device=self.device)
        nm = torch.tensor(batch["next_masks"], dtype=torch.bool, device=self.device)
        return self._shared_continuation_action(ns, nm)

    def head_targets(self, batch: dict[str, np.ndarray], head: int) -> torch.Tensor:
        """``y_k`` at the CURRENT ``eta``, ``lambda`` (recomputed per sample)."""
        ns = torch.tensor(batch["next_states"], dtype=torch.float32, device=self.device)
        dn = torch.tensor(batch["dones"], dtype=torch.float32, device=self.device)
        r = torch.tensor(
            self._normalise(batch["rewards_raw"])[:, head],
            dtype=torch.float32, device=self.device,
        )
        with torch.no_grad():
            a_star = self.continuation_actions(batch)
            q_next = self.target_nets[head](ns).gather(1, a_star).squeeze(1)
            return r + self.config.discount_factor * q_next * (1.0 - dn)

    def update(self) -> tuple[float, float, float]:
        batch = self._assemble_batch()
        self._last_batch = batch
        if batch is None:
            return (0.0, 0.0, 0.0)
        st = torch.tensor(batch["states"], dtype=torch.float32, device=self.device)
        act = torch.tensor(batch["actions"], dtype=torch.long, device=self.device).unsqueeze(1)
        losses = []
        for head in range(3):
            target = self.head_targets(batch, head)
            q_current = self.q_nets[head](st).gather(1, act).squeeze(1)
            loss = self._loss_fn(q_current, target)
            assert_finite_loss(loss, objective=head)
            self.optimizers[head].zero_grad()
            loss.backward()
            assert_finite_gradients(self.q_nets[head].parameters(), objective=head)
            self.optimizers[head].step()
            losses.append(loss.item())
        assert_finite_parameters(self.q_nets)
        return (losses[0], losses[1], losses[2])

    # -- dual / Dinkelbach -------------------------------------------------
    def measure_on_calibration(self) -> dict[str, Any]:
        """Greedy deployed rule on the calibration seeds (per-episode reseed)."""
        s = self.settings
        if self._env_factory is None:
            raise MCRLContractError("calibration needs an env_factory")
        greedy = lambda enc, masks, states: self.greedy_actions(enc, masks)  # noqa: E731
        return pooled_rollout(
            lambda i: greedy,
            env_factory=self._env_factory,
            encode=self.encode_at,
            seeds=episode_seeds(
                s.calibration_env_seed_base,
                s.calibration_mobility_seed_base,
                s.calibration_episodes,
            ),
        )

    def quarter_update(self, episode_done: int, *, final: bool = False) -> dict[str, Any]:
        """Measure; ``lambda`` ascent every quarter; ``eta`` from
        ``eta_first_update_episode`` on (Amendment 1).  At the first eta
        update ``learning_gate`` is consulted first; it may raise
        :class:`LearningCheckStop`.  ``final=True`` records without applying.
        """
        st = self.settings
        m = self.measure_on_calibration()
        row = {
            "episode": int(episode_done),
            "eta_before": self.eta, "lambda_before": self.lam,
            "measured_ee": float(m["ee"]), "measured_h_inter": float(m["h_inter"]),
            "measured_h_intra": float(m["h_intra"]),
            "measured_served": float(m["served"]), "measured_beams": float(m["beams"]),
            "measured_bits": float(m["bits"]), "measured_joules": float(m["joules"]),
            "measured_ee_ep": list(m["ee_ep"]),
            "kind": "final-diagnostic" if final else "quarter",
        }
        new_lam = max(0.0, self.lam + st.alpha * (m["h_inter"] - st.h_cap_inter))
        eta_due = episode_done >= st.eta_first_update_episode
        row["lambda_candidate"] = new_lam
        row["eta_candidate"] = float(m["ee"]) if eta_due else None
        if not final:
            if episode_done == st.eta_first_update_episode and self.learning_gate:
                self.learning_gate(episode_done, row)      # may raise
            self.lam = new_lam
            if eta_due:
                self.eta = float(m["ee"])
        row["eta"], row["lambda"] = self.eta, self.lam
        row["applied"] = not final
        self.dual_trajectory.append(row)
        return row

    # -- training loop -----------------------------------------------------
    def train_cf(
        self,
        *,
        start_episode: int = 0,
        initial_logs: list[dict] | None = None,
        episode_callback: Callable[[dict], None] | None = None,
        progress_every: int = 50,
    ) -> list[dict]:
        cfg, s = self.config, self.settings
        logs = list(initial_logs or [])
        if len(logs) != start_episode or any(
            row["episode"] != i for i, row in enumerate(logs)
        ):
            raise MCRLContractError("initial_logs must be episodes 0..start-1")
        users = self.num_users
        for ep in range(start_episode, cfg.episodes):
            eps = self.epsilon(ep)
            eta_ep, lam_ep = self.eta, self.lam
            states, masks, _ = self.env.reset(self._env_rng, self._mobility_rng)
            t = 0
            encoded = self.encode_at(states, t)
            for src in self.sources:
                src.reset()
            tot = np.zeros(3)
            served = h_intra = outages = 0
            beams = 0.0
            ep_losses = np.zeros(3)
            n_upd = 0
            n_steps = 0
            src_rows = np.zeros(len(self.sources) + 1, dtype=np.int64)
            for _t in range(self.env.config.steps_per_episode):
                actions = self.select_actions(encoded, masks, eps)
                result = self.env.step(actions, self._env_rng)
                outcome = self.env.last_outcome
                raw = cf_reward_matrix(result, outcome)
                tot += raw.sum(axis=0)
                served += int(outcome.energy.served)
                beams += float(outcome.energy.eff_beams)
                h_intra += sum(
                    int(c is HandoverClass.INTRA_SATELLITE) for c in outcome.handovers
                )
                outages += int(sum(1 for x in result.served if not x))
                n_steps += 1
                t += 1
                next_encoded = self.encode_at(result.user_states, t)
                for uid in range(users):
                    self._decision_steps_seen += 1
                    if is_no_op(int(actions[uid])):
                        self._no_op_transitions_skipped += 1
                        continue
                    next_mask = result.action_masks[uid].mask
                    if not bool(result.done) and not bool(next_mask.any()):
                        self._all_invalid_next_transitions_skipped += 1
                        continue
                    self.replay.push(
                        encoded[uid], int(actions[uid]), raw[uid].copy(),
                        next_encoded[uid], masks[uid].mask.copy(),
                        next_mask.copy(), bool(result.done),
                    )
                for src in self.sources:
                    src.step()
                step_losses = self.update()
                if self._last_batch is not None:
                    ep_losses += step_losses
                    n_upd += 1
                    src_rows += np.bincount(
                        self._last_batch["source"] + 1, minlength=len(src_rows)
                    )
                states, masks, encoded = (
                    result.user_states, result.action_masks, next_encoded
                )
                if result.done:
                    break
            if (ep + 1) % cfg.target_update_every_episodes == 0:
                self.sync_targets()
            us = n_steps * users
            norm = tot / self._units / us
            log = {
                "episode": ep,
                "epsilon": eps,
                "eta": eta_ep,
                "lambda": lam_ep,
                "eta_tilde": eta_ep * s.joules_scale / s.bits_scale,
                "bits": float(tot[HEAD_B]),
                "joules": float(tot[HEAD_E]),
                "ee_behaviour": float(tot[HEAD_B] / tot[HEAD_E]),
                "h_inter": float(tot[HEAD_H] / us),
                "h_intra": h_intra / us,
                "served": served / us,
                "beams": beams / n_steps,
                "outage_user_steps": outages,
                "head_reward_means_normalised": [float(x) for x in norm],
                "objective_per_user_step": float(
                    norm[HEAD_B] - (eta_ep * s.joules_scale / s.bits_scale) * norm[HEAD_E]
                    - lam_ep * norm[HEAD_H]
                ),
                "losses": [float(x) for x in (ep_losses / max(n_upd, 1))],
                "updates": n_upd,
                "batch_rows_by_source": [int(x) for x in src_rows],
                "replay_size": len(self.replay),
                "catfish_buffer_sizes": [len(x.buffer) for x in self.sources],
                "catfish_episode": [
                    {
                        "name": x.name,
                        "ee": float(x.episode_totals[HEAD_B] / x.episode_totals[HEAD_E]),
                        "h_inter": float(x.episode_totals[HEAD_H] / max(x.episode_user_steps, 1)),
                    }
                    for x in self.sources
                ],
                "quarter": None,
            }
            episode_done = ep + 1
            if episode_done % s.quarter_episodes == 0:
                log["quarter"] = self.quarter_update(
                    episode_done, final=episode_done >= cfg.episodes
                )
            for k, v in log.items():
                if isinstance(v, float) and not np.isfinite(v):
                    raise FloatingPointError(f"non-finite {k} in episode {ep}")
            logs.append(log)
            if episode_callback is not None:
                episode_callback(log)
            if progress_every and episode_done % progress_every == 0:
                print(
                    f"[ep {episode_done:5d}/{cfg.episodes}] eps={eps:.3f} "
                    f"ee_beh={log['ee_behaviour']:.4e} h_inter={log['h_inter']:.4f} "
                    f"served={log['served']:.4f} eta={self.eta:.4e} lam={self.lam:.4f} "
                    f"loss={log['losses'][0]:.3e},{log['losses'][1]:.3e},{log['losses'][2]:.3e} "
                    f"buf={len(self.replay)}",
                    flush=True,
                )
        return logs

    # -- persistence -------------------------------------------------------
    def training_state_dict(self) -> dict[str, Any]:
        state = super().training_state_dict()
        state["cf"] = {
            "settings": dataclasses.asdict(self.settings),
            "eta": self.eta,
            "lambda": self.lam,
            "dual_trajectory": copy.deepcopy(self.dual_trajectory),
            "catfish_rng": copy.deepcopy(self._catfish_rng.bit_generator.state),
            "sources": [src.state_dict() for src in self.sources],
        }
        return state

    def load_training_state_dict(self, state) -> None:
        cf = state["cf"]
        if cf["settings"] != dataclasses.asdict(self.settings):
            raise MCRLContractError("resume state CF settings do not match")
        super().load_training_state_dict(state)
        self.eta = float(cf["eta"])
        self.lam = float(cf["lambda"])
        self.dual_trajectory = copy.deepcopy(cf["dual_trajectory"])
        self._catfish_rng.bit_generator.state = copy.deepcopy(cf["catfish_rng"])
        if len(cf["sources"]) != len(self.sources):
            raise MCRLContractError("resume state source count does not match")
        for src, st in zip(self.sources, cf["sources"]):
            src.load_state_dict(st)

    def policy_payload(self, episode: int) -> dict[str, Any]:
        return {
            "schema": "cf-ratio-policy-v1",
            "episode": int(episode),
            "train_seed": self.train_seed,
            "env_seed": self.env_seed,
            "mobility_seed": self.mobility_seed,
            "state_dim": self.state_dim,
            "trainer_config": dataclasses.asdict(self.config),
            "settings": dataclasses.asdict(self.settings),
            "eta": self.eta,
            "lambda": self.lam,
            "eta_tilde": self.eta_tilde,
            "dual_trajectory": copy.deepcopy(self.dual_trajectory),
            "q_networks": [copy.deepcopy(n.state_dict()) for n in self.q_nets],
            "target_networks": [copy.deepcopy(n.state_dict()) for n in self.target_nets],
        }

    def save_policy(self, path: str | Path, episode: int) -> Path:
        path = Path(path)
        tmp = path.with_suffix(path.suffix + ".tmp")
        torch.save(self.policy_payload(episode), tmp)
        tmp.replace(path)
        return path

    def load_policy(self, path: str | Path) -> dict[str, Any]:
        payload = torch.load(Path(path), map_location="cpu", weights_only=False)
        if payload.get("schema") != "cf-ratio-policy-v1":
            raise MCRLContractError("not a cf-ratio policy checkpoint")
        for net, sd in zip(self.q_nets, payload["q_networks"]):
            net.load_state_dict(sd)
        for net, sd in zip(self.target_nets, payload["target_networks"]):
            net.load_state_dict(sd)
        self.eta = float(payload["eta"])
        self.lam = float(payload["lambda"])
        return payload


def trainer_config_from_payload(payload: dict[str, Any]) -> TrainerConfig:
    cfg = dict(payload["trainer_config"])
    for k in ("hidden_layers", "objective_weights", "reward_calibration_scales"):
        cfg[k] = tuple(cfg[k])
    return TrainerConfig(**cfg)


def cf_settings_from_payload(payload: dict[str, Any]) -> CFRatioSettings:
    return CFRatioSettings(**payload["settings"])
