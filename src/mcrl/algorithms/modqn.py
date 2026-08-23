"""MODQN trainer for PAP-2024-MORL-MULTIBEAM reproduction.

Three parallel DQNs (one per objective: throughput, handover, load balance).
Scalarized action selection with weight row at decision time.
Epsilon-greedy with action masking (ASSUME-MODQN-REP-012).
Experience replay with periodic hard target-network sync.

All trainer hyperparameters must come from the resolved-run config.
No hidden defaults — every knob is surfaced in TrainerConfig.

Paper-backed (SDD §3.5):
    hidden_layers, activation, learning_rate, discount_factor,
    batch_size, episodes, objective_weights.

Reproduction-assumption:
    epsilon schedule (ASSUME-MODQN-REP-004),
    target update cadence (ASSUME-MODQN-REP-005),
    replay capacity (ASSUME-MODQN-REP-006),
    policy sharing mode (ASSUME-MODQN-REP-007),
    state encoding/normalization (ASSUME-MODQN-REP-013).
"""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path
from typing import Any, TYPE_CHECKING

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from ..artifacts import (
    CheckpointPayloadV1,
    CheckpointRuleV1,
    read_checkpoint,
    write_checkpoint,
)
from ..env.step_types import (
    ActionMask,
    RewardComponents,
    UserState,
)

if TYPE_CHECKING:  # PATCH P-09 (W-10)
    # The environment class itself is built on top of this contract; importing
    # it at runtime would make the algorithm depend on the environment rather
    # than on the typed seam between them.
    from ..env.step import StepEnvironment
from ..env.action_contract import NO_OP_ACTION, is_no_op, no_op_actions
from ..errors import MCRLContractError
from ..runtime.finiteness import (
    assert_finite_gradients,
    assert_finite_loss,
    assert_finite_parameters,
)
from ..runtime.objective_math import (
    apply_reward_calibration,
    scalarize_objectives,
)
from ..runtime.collapse_metrics import compute_collapse_metrics
from ..runtime.q_network import DQNNetwork
from ..runtime.replay_buffer import ReplayBuffer
from ..runtime.state_encoding import encode_state, state_dim_for
from ..runtime.trainer_spec import (
    EpisodeLog,
    EvalSummary,
    TrainerConfig,
)

_RUNTIME_REAL_EMISSION_HOOK_ENABLED_KEYS = (
    "hook_enabled",
    "enabled",
    "runtime_real_emission_enabled",
    "emission_enabled",
)


class MODQNTrainer:
    """Multi-Objective DQN trainer per PAP-2024-MORL-MULTIBEAM.

    Usage::

        env = StepEnvironment(...)
        trainer = MODQNTrainer(env, config, ...)
        logs = trainer.train()
    """

    def __init__(
        self,
        env: StepEnvironment,
        config: TrainerConfig,
        train_seed: int = 42,
        env_seed: int = 1337,
        mobility_seed: int = 7,
        device: str = "cpu",
        runtime_real_emission_collector: Any | None = None,
    ) -> None:
        self.env = env
        self.config = config
        self.device = torch.device(device)
        self.train_seed = train_seed
        self.env_seed = env_seed
        self.mobility_seed = mobility_seed

        self.num_beams = env.num_beams_total
        self.num_users = env.config.num_users
        self.state_dim = state_dim_for(self.num_beams)
        self.action_dim = self.num_beams

        # Deterministic seed path (ASSUME-MODQN-REP-018)
        torch.manual_seed(train_seed)
        self._train_rng = np.random.default_rng(train_seed)
        self._env_rng = np.random.default_rng(env_seed)
        self._mobility_rng = np.random.default_rng(mobility_seed)

        # 3 parallel DQNs: Q1 (throughput), Q2 (handover), Q3 (load balance)
        self.q_nets = nn.ModuleList([
            DQNNetwork(
                self.state_dim, self.action_dim,
                config.hidden_layers, config.activation,
            ).to(self.device)
            for _ in range(3)
        ])
        self.target_nets = nn.ModuleList([
            copy.deepcopy(q).to(self.device) for q in self.q_nets
        ])
        for t in self.target_nets:
            t.eval()

        # Per-objective optimizers
        self.optimizers = [
            optim.Adam(self.q_nets[i].parameters(), lr=config.learning_rate)
            for i in range(3)
        ]

        # Replay buffer (ASSUME-MODQN-REP-006)
        self.replay = ReplayBuffer(config.replay_capacity)

        self._loss_fn = nn.MSELoss()
        self._loaded_checkpoint_metadata: dict[str, Any] | None = None
        self._secondary_checkpoint_enabled: bool = False
        self._secondary_checkpoint_status: str = (
            "not-yet-implemented: no eval loop / best-eval checkpoint in this training run"
        )
        self._evaluation_every_episodes: int | None = None
        self._evaluation_seed_set: tuple[int, ...] = ()
        self._best_eval_summary: EvalSummary | None = None
        self._best_eval_payload: CheckpointPayloadV1 | None = None
        # PATCH P-03 (L-3, SDD §4A.5a(4)): the drop rates that decide whether
        # plain dropping is admissible or a semi-MDP transition is required.
        self._no_op_transitions_skipped: int = 0
        self._all_invalid_next_transitions_skipped: int = 0
        self._decision_steps_seen: int = 0
        self._runtime_real_emission_collector = runtime_real_emission_collector
        self._runtime_real_emission_hook_enabled()

    def get_masking_diagnostics(self) -> dict[str, int]:
        """Replay-exclusion counts owned by PATCH P-03 (SDD §4A.5a(4)).

        ``no_op_transitions_skipped``  — steps where the user had no valid
        action at all (``mask_t`` empty), executed a no-op, and contributed
        no transition.
        ``all_invalid_next_transitions_skipped`` — non-terminal steps whose
        successor mask was empty, so the bootstrap target was undefined.
        ``decision_steps_seen`` — the denominator: every (user, step) pair
        the training loop reached.

        Probe P1 reports all three.  See
        ``mcrl.runtime.outage_gate.evaluate_outage_gate`` for what the rate
        obliges: dropping is only admissible while outage is rare, because
        it does not merely lose data — it makes outage **free**.
        """
        return {
            "no_op_transitions_skipped": int(self._no_op_transitions_skipped),
            "all_invalid_next_transitions_skipped": int(
                self._all_invalid_next_transitions_skipped
            ),
            "decision_steps_seen": int(self._decision_steps_seen),
        }

    def reset_masking_diagnostics(self) -> None:
        self._no_op_transitions_skipped = 0
        self._all_invalid_next_transitions_skipped = 0
        self._decision_steps_seen = 0

    def _runtime_real_emission_hook_enabled(self) -> bool:
        collector = self._runtime_real_emission_collector
        if collector is None:
            return False

        markers: dict[str, Any] = {}
        if isinstance(collector, Mapping):
            markers = {
                key: collector[key]
                for key in _RUNTIME_REAL_EMISSION_HOOK_ENABLED_KEYS
                if key in collector
            }
        else:
            raw_attrs = getattr(collector, "__dict__", {})
            if isinstance(raw_attrs, Mapping):
                markers = {
                    key: raw_attrs[key]
                    for key in _RUNTIME_REAL_EMISSION_HOOK_ENABLED_KEYS
                    if key in raw_attrs
                }

        for value in markers.values():
            if self._runtime_real_emission_marker_enabled(value):
                raise RuntimeError(
                    "v2-FEWL-RE-I3-Impl-B runtime real-emission hook "
                    "enabled mode is not authorized; default-off plumbing "
                    "must not emit runtime rows."
                )
        return False

    @staticmethod
    def _runtime_real_emission_marker_enabled(value: Any) -> bool:
        if value is True:
            return True
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "enabled", "on", "yes"}
        return isinstance(value, int) and value == 1

    def _emit_runtime_real_emission_hook(self, _event_type: str) -> None:
        if not self._runtime_real_emission_hook_enabled():
            return
        raise RuntimeError(
            "v2-FEWL-RE-I3-Impl-B runtime real-emission enabled path is "
            "unsupported."
        )

    # -- epsilon schedule (ASSUME-MODQN-REP-004) ----------------------------

    def epsilon(self, episode: int) -> float:
        """Linear epsilon decay from start to end over decay_episodes."""
        cfg = self.config
        if episode >= cfg.epsilon_decay_episodes:
            return cfg.epsilon_end
        frac = episode / cfg.epsilon_decay_episodes
        return cfg.epsilon_start + (cfg.epsilon_end - cfg.epsilon_start) * frac

    # -- action selection ---------------------------------------------------

    def _predict_objective_q_values(
        self,
        states_encoded: np.ndarray,
    ) -> list[np.ndarray]:
        """Run the three objective networks on a batch of encoded states."""
        with torch.no_grad():
            st = torch.tensor(
                states_encoded, dtype=torch.float32, device=self.device
            )
            return [self.q_nets[i](st).cpu().numpy() for i in range(3)]

    def _scalarize_q_values(
        self,
        q_values: list[np.ndarray],
        objective_weights: tuple[float, float, float],
    ) -> np.ndarray:
        """Scalarize the three objective-Q tables with one weight row."""
        return (
            objective_weights[0] * q_values[0]
            + objective_weights[1] * q_values[1]
            + objective_weights[2] * q_values[2]
        )

    def _select_masked_greedy_action(
        self,
        scalarized_row: np.ndarray,
        mask: np.ndarray,
    ) -> int | None:
        """Return the greedy masked action or ``None`` when no action is valid."""
        valid = np.flatnonzero(mask)
        if valid.size == 0:
            return None
        q_row = scalarized_row.copy()
        q_row[~mask] = -np.inf
        return int(np.argmax(q_row))

    def _rank_masked_actions(
        self,
        scalarized_row: np.ndarray,
        mask: np.ndarray,
    ) -> list[int]:
        """Return valid actions sorted by scalarized-Q then beam index."""
        valid = np.flatnonzero(mask)
        return sorted(
            (int(action) for action in valid.tolist()),
            key=lambda action: (-float(scalarized_row[action]), int(action)),
        )

    def _select_unconstrained_actions(
        self,
        scalarized: np.ndarray,
        masks: list[ActionMask],
        eps: float,
    ) -> np.ndarray:
        """Return the normal MODQN epsilon-greedy actions.

        PATCH P-01 (L-1, SDD §4A.5a(1)): an empty decision mask yields
        ``NO_OP_ACTION``, never index 0.  Exploration stays masked (P-9).
        """
        U = len(masks)
        actions = no_op_actions(U)
        for uid in range(U):
            valid = np.where(masks[uid].mask)[0]
            if len(valid) == 0:
                # PATCH P-01: no valid action -> no-op, user unserved this
                # step.  Never fall back to any index.
                actions[uid] = NO_OP_ACTION
                continue

            if self._train_rng.random() < eps:
                actions[uid] = self._train_rng.choice(valid)
            else:
                selected_action = self._select_masked_greedy_action(
                    scalarized[uid],
                    masks[uid].mask,
                )
                if selected_action is None:
                    # Structurally unreachable: ``valid`` is non-empty here.
                    # Fail loudly rather than restore the index-0 fallback.
                    raise MCRLContractError(
                        "masked greedy selection returned None for user "
                        f"{uid} despite {valid.size} valid actions"
                    )
                actions[uid] = selected_action

        return actions

    def select_actions(
        self,
        states_encoded: np.ndarray,
        masks: list[ActionMask],
        eps: float,
        *,
        objective_weights: tuple[float, float, float] | None = None,
        raw_states: list[UserState] | None = None,
    ) -> np.ndarray:
        """Epsilon-greedy masked action selection with scalarized Q.

        At each decision step:
        1. Compute Q1, Q2, Q3 for each user
        2. Scalarize: Q_scalar = w1*Q1 + w2*Q2 + w3*Q3
        3. Mask invalid actions to -inf
        4. epsilon-greedy over the masked scalarized Q

        Returns actions array shape (num_users,).

        PATCH P-05 (W-09): there is exactly one selection path.  The
        capacity-aware and QoS-sticky branches, and the config switch that
        dispatched to them, are gone — SDD §2.2 deletes that family of
        ceilings, and the 2026-08-22 ruling forbids leaving a socket for a
        deleted mechanism.
        ``raw_states`` is retained only because callers pass it positionally;
        nothing reads it.
        """
        del raw_states
        w = objective_weights or self.config.objective_weights
        q_values = self._predict_objective_q_values(states_encoded)
        scalarized = self._scalarize_q_values(q_values, w)
        return self._select_unconstrained_actions(scalarized, masks, eps)

    def select_actions_with_diagnostics(
        self,
        states_encoded: np.ndarray,
        masks: list[ActionMask],
        *,
        objective_weights: tuple[float, float, float] | None = None,
        top_k: int = 3,
    ) -> tuple[np.ndarray, list[dict[str, Any] | None]]:
        """Greedy masked action selection plus exporter-owned diagnostics.

        This helper is intentionally separate from ``select_actions()`` so
        training/evaluation call sites keep their existing API and epsilon
        semantics. It is meant for exporter-time replay of an already selected
        checkpoint only.
        """
        if top_k < 1:
            raise ValueError(f"top_k must be >= 1, got {top_k}")

        U = len(masks)
        actions = no_op_actions(U)
        diagnostics: list[dict[str, Any] | None] = []
        w = objective_weights or self.config.objective_weights
        q_values = self._predict_objective_q_values(states_encoded)
        scalarized = self._scalarize_q_values(q_values, w)

        for uid in range(U):
            mask = masks[uid].mask
            selected_action = self._select_masked_greedy_action(
                scalarized[uid],
                mask,
            )
            if selected_action is None:
                # PATCH P-02 (L-1, SDD §4A.5a(1)): empty mask -> no-op, not
                # index 0.  Diagnostics stay ``None`` for an absent decision.
                actions[uid] = NO_OP_ACTION
                diagnostics.append(None)
                continue

            ordered_actions = self._rank_masked_actions(scalarized[uid], mask)
            if not ordered_actions or ordered_actions[0] != selected_action:
                raise ValueError(
                    "Policy diagnostics could not align the greedy selected action "
                    f"for user {uid}: selected={selected_action}, ordered={ordered_actions[:1]}."
                )

            valid_scalarized = scalarized[uid, mask]
            if not np.all(np.isfinite(valid_scalarized)):
                raise ValueError(
                    "Policy diagnostics require finite scalarized-Q values on the "
                    f"decision mask for user {uid}."
                )

            objective_q_values: list[np.ndarray] = []
            for obj_idx, q_table in enumerate(q_values):
                valid_objective_q = q_table[uid, mask]
                if not np.all(np.isfinite(valid_objective_q)):
                    raise ValueError(
                        "Policy diagnostics require finite objective-Q values on "
                        f"the decision mask for user {uid}, objective {obj_idx}."
                    )
                objective_q_values.append(q_table[uid])

            actions[uid] = selected_action
            runner_up_action = ordered_actions[1] if len(ordered_actions) > 1 else None
            selected_scalarized_q = float(scalarized[uid][selected_action])
            runner_up_scalarized_q = (
                float(scalarized[uid][runner_up_action])
                if runner_up_action is not None
                else None
            )
            scalarized_margin = (
                float(selected_scalarized_q - runner_up_scalarized_q)
                if runner_up_scalarized_q is not None
                else None
            )
            top_candidates = []
            for action in ordered_actions[:top_k]:
                top_candidates.append(
                    {
                        "action": int(action),
                        "validUnderDecisionMask": bool(mask[action]),
                        "objectiveQ": [
                            float(objective_q_values[0][action]),
                            float(objective_q_values[1][action]),
                            float(objective_q_values[2][action]),
                        ],
                        "scalarizedQ": float(scalarized[uid][action]),
                    }
                )

            diagnostics.append(
                {
                    "objectiveWeights": [float(value) for value in w],
                    "availableActionCount": int(np.sum(mask)),
                    "selectedAction": int(selected_action),
                    "selectedScalarizedQ": selected_scalarized_q,
                    "runnerUpAction": (
                        None if runner_up_action is None else int(runner_up_action)
                    ),
                    "runnerUpScalarizedQ": runner_up_scalarized_q,
                    "scalarizedMarginToRunnerUp": scalarized_margin,
                    "topCandidates": top_candidates,
                }
            )

        return actions, diagnostics

    # -- network update -----------------------------------------------------
    #
    # PATCH P-11 (W-08): ``_update_from_arrays`` is removed.  It was the
    # override seam the source project's subclasses used, and this project has
    # none — SDD §8 forbids every one of them.  It had zero callers here.
    #
    # Two reasons to delete rather than repair it.  First, it held a SECOND
    # implementation of the TD target, and B1's whole point is that the target
    # is unambiguously MODQN eq. (16) vanilla — two copies of an equation drift,
    # and the dormant one already differed in how it masked (``masked_fill``
    # out-of-place vs in-place assignment).  Second, its finiteness check
    # SILENTLY SKIPPED the offending objective and kept training, which is
    # exactly what §3.7 P-3 and §6 G-11 forbid; a dormant path that would
    # violate a gate the moment it were wired up is a trap, not a spare part.

    def update(self) -> tuple[float, float, float]:
        """Sample a batch from replay and update all 3 DQNs.

        Returns per-objective MSE losses (0.0 if replay too small).

        PATCH P-04 (L-2, SDD §3.7 P-3 / §6 G-11): the fail-loud finiteness
        battery.  Non-finite loss, gradient, or online-network parameter
        aborts training instead of continuing silently.
        """
        cfg = self.config
        if len(self.replay) < cfg.batch_size:
            return (0.0, 0.0, 0.0)

        (
            states, actions, rewards, next_states,
            _masks, next_masks, dones,
        ) = self.replay.sample(cfg.batch_size, self._train_rng)

        st = torch.tensor(states, dtype=torch.float32, device=self.device)
        act = torch.tensor(actions, dtype=torch.long, device=self.device).unsqueeze(1)
        ns = torch.tensor(next_states, dtype=torch.float32, device=self.device)
        nm = torch.tensor(next_masks, dtype=torch.bool, device=self.device)
        dn = torch.tensor(dones, dtype=torch.float32, device=self.device)

        losses: list[float] = []
        for obj_idx in range(3):
            r = torch.tensor(
                rewards[:, obj_idx], dtype=torch.float32, device=self.device
            )

            # Current Q(s, a)
            q_current = self.q_nets[obj_idx](st).gather(1, act).squeeze(1)

            # Target: r + gamma * max_a' Q_target(s', a') where a' valid
            with torch.no_grad():
                q_next_all = self.target_nets[obj_idx](ns)
                # Mask invalid next-actions to large negative value
                q_next_all[~nm] = -1e9
                q_next_max = q_next_all.max(dim=1).values
                target = r + cfg.discount_factor * q_next_max * (1.0 - dn)

            loss = self._loss_fn(q_current, target)

            # PATCH P-04 (P-3 / G-11): fail loud, never skip-and-continue.
            assert_finite_loss(loss, objective=obj_idx)

            self.optimizers[obj_idx].zero_grad()
            loss.backward()
            assert_finite_gradients(
                self.q_nets[obj_idx].parameters(),
                objective=obj_idx,
            )
            self.optimizers[obj_idx].step()

            losses.append(loss.item())

        # PATCH P-04 (P-3 / G-11): parameters must stay finite after the step.
        assert_finite_parameters(self.q_nets)

        return (losses[0], losses[1], losses[2])

    # -- target sync (ASSUME-MODQN-REP-005) --------------------------------

    def sync_targets(self) -> None:
        """Hard copy online networks to target networks."""
        for i in range(3):
            self.target_nets[i].load_state_dict(self.q_nets[i].state_dict())

    def _encode_states(self, states: list[UserState]) -> np.ndarray:
        """Encode a list of user states with the active trainer config."""
        return np.array(
            [encode_state(s, self.num_users, self.config) for s in states],
            dtype=np.float32,
        )

    def encode_states(self, states: list[UserState]) -> np.ndarray:
        """Public wrapper for the active state-encoding surface."""
        return self._encode_states(states)

    def reward_vector_from_step_result(
        self,
        result,
        uid: int,
        *,
        is_eval: bool = False,
    ) -> np.ndarray:
        """Return the three-objective reward vector for one user.

        PATCH P-14 (ruling C-7): the trainer no longer *computes* ``r1``.
        Eq. (3.25) divides by the common system power ``P^N``, a global
        quantity the trainer cannot see — it would have to know every other
        user's link to form the denominator.  The environment computes it.

        PATCH P-20: and it no longer *selects* ``r1`` either.  The call to
        ``select_r1_reward_value`` dispatched over five candidate fields;
        (3.25) names one quantity, so the field is read directly.  The old
        default pointed at ``r1_throughput``, which the environment had
        begun filling with bits/J — a field whose name disagreed with its
        contents, selected by a switch with one live position.
        """
        del is_eval  # both paths take the same reward; kept for the signature
        rw = result.rewards[uid]
        return np.array(
            [
                rw.r1_system_ee_contribution,
                rw.r2_handover,
                rw.r3_load_balance,
            ],
            dtype=np.float64,
        )

    def _evaluate_one_seed(
        self,
        eval_seed: int,
        *,
        objective_weights: tuple[float, float, float] | None = None,
    ) -> dict[str, float]:
        """Greedy rollout for one evaluation seed."""
        env_seed_seq, mobility_seed_seq = np.random.SeedSequence(eval_seed).spawn(2)
        env_rng = np.random.default_rng(env_seed_seq)
        mobility_rng = np.random.default_rng(mobility_seed_seq)
        weights = objective_weights or self.config.objective_weights

        states, masks, _diag = self.env.reset(env_rng, mobility_rng)
        encoded = self._encode_states(states)

        ep_reward = np.zeros(3, dtype=np.float64)
        ep_handovers = 0

        for _step_idx in range(self.env.config.steps_per_episode):
            actions = self.select_actions(
                encoded,
                masks,
                eps=0.0,
                objective_weights=weights,
                raw_states=states,
            )
            result = self.env.step(actions, env_rng)

            for uid, rw in enumerate(result.rewards):
                reward_vec = self.reward_vector_from_step_result(
                    result,
                    uid,
                    is_eval=True,
                )
                ep_reward += reward_vec
                if rw.r2_handover < 0:
                    ep_handovers += 1

            if result.done:
                break

            states = result.user_states
            encoded = self._encode_states(result.user_states)
            masks = result.action_masks

        avg_reward = ep_reward / max(self.num_users, 1)
        scalar = scalarize_objectives(avg_reward, weights)

        return {
            "scalar_reward": float(scalar),
            "r1_mean": float(avg_reward[0]),
            "r2_mean": float(avg_reward[1]),
            "r3_mean": float(avg_reward[2]),
            "total_handovers": float(ep_handovers),
        }

    def evaluate_policy(
        self,
        evaluation_seed_set: tuple[int, ...],
        *,
        episode: int,
        evaluation_every_episodes: int,
        objective_weights: tuple[float, float, float] | None = None,
    ) -> EvalSummary:
        """Evaluate the greedy policy over the configured evaluation seeds."""
        if not evaluation_seed_set:
            raise ValueError("evaluation_seed_set must be non-empty for evaluation")

        rows = [
            self._evaluate_one_seed(seed, objective_weights=objective_weights)
            for seed in evaluation_seed_set
        ]

        def mean_std(key: str) -> tuple[float, float]:
            values = np.array([row[key] for row in rows], dtype=np.float64)
            return float(np.mean(values)), float(np.std(values))

        scalar_mean, scalar_std = mean_std("scalar_reward")
        r1_mean, r1_std = mean_std("r1_mean")
        r2_mean, r2_std = mean_std("r2_mean")
        r3_mean, r3_std = mean_std("r3_mean")
        handover_mean, handover_std = mean_std("total_handovers")

        return EvalSummary(
            episode=episode,
            evaluation_every_episodes=evaluation_every_episodes,
            eval_seeds=tuple(int(seed) for seed in evaluation_seed_set),
            mean_scalar_reward=scalar_mean,
            std_scalar_reward=scalar_std,
            mean_r1=r1_mean,
            std_r1=r1_std,
            mean_r2=r2_mean,
            std_r2=r2_std,
            mean_r3=r3_mean,
            std_r3=r3_std,
            mean_total_handovers=handover_mean,
            std_total_handovers=handover_std,
        )

    # -- checkpointing (ASSUME-MODQN-REP-015) ------------------------------

    def checkpoint_rule(self) -> CheckpointRuleV1:
        """Return the active checkpoint-selection rule for metadata/logging."""
        return CheckpointRuleV1(
            assumption_id=self.config.checkpoint_assumption_id,
            primary_report=self.config.checkpoint_primary_report,
            secondary_report=self.config.checkpoint_secondary_report,
            secondary_implemented=self._secondary_checkpoint_enabled,
            secondary_status=self._secondary_checkpoint_status,
        )

    def build_checkpoint_payload(
        self,
        *,
        episode: int,
        checkpoint_kind: str,
        logs: list[EpisodeLog] | None = None,
        include_optimizers: bool = True,
        evaluation_summary: dict[str, Any] | None = None,
    ) -> CheckpointPayloadV1:
        """Build a serializable checkpoint payload."""
        summary = None
        if evaluation_summary is not None:
            summary = copy.deepcopy(evaluation_summary)
            if "eval_seeds" in summary:
                summary["eval_seeds"] = [int(seed) for seed in summary["eval_seeds"]]

        return CheckpointPayloadV1(
            format_version=1,
            checkpoint_kind=checkpoint_kind,
            episode=episode,
            train_seed=self.train_seed,
            env_seed=self.env_seed,
            mobility_seed=self.mobility_seed,
            state_dim=self.state_dim,
            action_dim=self.action_dim,
            trainer_config=asdict(self.config),
            checkpoint_rule=self.checkpoint_rule(),
            q_networks=[net.state_dict() for net in self.q_nets],
            target_networks=[net.state_dict() for net in self.target_nets],
            optimizers=(
                [optimizer.state_dict() for optimizer in self.optimizers]
                if include_optimizers
                else None
            ),
            last_episode_log=asdict(logs[-1]) if logs else None,
            evaluation_summary=summary,
        )

    def _write_checkpoint_payload(
        self,
        path: str | Path,
        payload: CheckpointPayloadV1,
    ) -> Path:
        """Write a pre-built checkpoint payload to disk."""
        return write_checkpoint(Path(path), payload)

    def _load_checkpoint_payload(
        self,
        payload: CheckpointPayloadV1,
        *,
        checkpoint_path: str | Path | None = None,
        load_optimizers: bool = True,
    ) -> CheckpointPayloadV1:
        """Load trainer weights/state from a checkpoint payload."""
        for net, state in zip(self.q_nets, payload.q_networks):
            net.load_state_dict(state)
        for net, state in zip(self.target_nets, payload.target_networks):
            net.load_state_dict(state)
            net.eval()

        optimizer_loaded = False
        if load_optimizers and payload.optimizers is not None:
            for optimizer, state in zip(self.optimizers, payload.optimizers):
                optimizer.load_state_dict(state)
            optimizer_loaded = True

        self._loaded_checkpoint_metadata = {
            "path": str(checkpoint_path) if checkpoint_path is not None else None,
            "checkpoint_kind": payload.checkpoint_kind,
            "episode": payload.episode,
            "checkpoint_rule": payload.checkpoint_rule.to_dict(),
            "optimizer_loaded": optimizer_loaded,
            "evaluation_summary": copy.deepcopy(payload.evaluation_summary),
        }
        return payload

    def save_checkpoint(
        self,
        path: str | Path,
        *,
        episode: int,
        checkpoint_kind: str,
        logs: list[EpisodeLog] | None = None,
        include_optimizers: bool = True,
        evaluation_summary: dict[str, Any] | None = None,
    ) -> Path:
        """Save the current trainer weights/state to disk."""
        payload = self.build_checkpoint_payload(
            episode=episode,
            checkpoint_kind=checkpoint_kind,
            logs=logs,
            include_optimizers=include_optimizers,
            evaluation_summary=evaluation_summary,
        )
        return self._write_checkpoint_payload(path, payload)

    def has_best_eval_checkpoint(self) -> bool:
        """Whether an eval-selected secondary checkpoint is available."""
        return self._best_eval_payload is not None

    def best_eval_summary(self) -> EvalSummary | None:
        """Return the current best eval summary, if one exists."""
        return self._best_eval_summary

    def save_best_eval_checkpoint(self, path: str | Path) -> Path:
        """Persist the best eval-selected checkpoint discovered during training."""
        if self._best_eval_payload is None:
            raise ValueError("No best-eval checkpoint payload is available")
        return self._write_checkpoint_payload(path, copy.deepcopy(self._best_eval_payload))

    def restore_best_eval_checkpoint(
        self,
        *,
        load_optimizers: bool = True,
    ) -> dict[str, Any]:
        """Restore the in-memory best-eval checkpoint into the live trainer."""
        if self._best_eval_payload is None:
            raise ValueError("No best-eval checkpoint payload is available")
        payload = self._load_checkpoint_payload(
            copy.deepcopy(self._best_eval_payload),
            checkpoint_path="<in-memory-best-eval>",
            load_optimizers=load_optimizers,
        )
        return payload.to_dict()

    def load_checkpoint(
        self,
        path: str | Path,
        *,
        load_optimizers: bool = True,
    ) -> dict[str, Any]:
        """Load trainer weights/state from a checkpoint file."""
        checkpoint_path = Path(path)
        payload = read_checkpoint(
            checkpoint_path,
            map_location=self.device,
        )
        loaded = self._load_checkpoint_payload(
            payload,
            checkpoint_path=checkpoint_path,
            load_optimizers=load_optimizers,
        )
        return loaded.to_dict()

    # -- training loop ------------------------------------------------------

    def train(
        self,
        progress_every: int = 100,
        *,
        evaluation_seed_set: tuple[int, ...] | None = None,
        evaluation_every_episodes: int | None = None,
    ) -> list[EpisodeLog]:
        """Full MODQN training loop.

        Returns a list of per-episode metrics.
        """
        cfg = self.config
        logs: list[EpisodeLog] = []
        eval_seeds = tuple(int(seed) for seed in (evaluation_seed_set or ()))
        eval_every = max(
            int(evaluation_every_episodes or cfg.target_update_every_episodes),
            1,
        )

        self._best_eval_summary = None
        self._best_eval_payload = None
        self._evaluation_every_episodes = eval_every if eval_seeds else None
        self._evaluation_seed_set = eval_seeds
        self._secondary_checkpoint_enabled = bool(eval_seeds)
        if eval_seeds:
            self._secondary_checkpoint_status = (
                "best-eval checkpoint captured from mean weighted reward over "
                f"{len(eval_seeds)} evaluation seeds; evaluated every "
                f"{eval_every} episodes and at the final episode"
            )
        else:
            self._secondary_checkpoint_status = (
                "not-yet-implemented: no eval loop / best-eval checkpoint in this training run"
            )

        for ep in range(cfg.episodes):
            eps = self.epsilon(ep)

            # Reset environment
            states, masks, _diag = self.env.reset(
                self._env_rng, self._mobility_rng
            )

            # Encode states
            encoded = self._encode_states(states)

            ep_reward = np.zeros(3, dtype=np.float64)
            ep_handovers = 0
            ep_losses = np.zeros(3, dtype=np.float64)
            update_count = 0
            collapse = None

            for _step_idx in range(self.env.config.steps_per_episode):
                # Select actions
                actions = self.select_actions(
                    encoded,
                    masks,
                    eps,
                    raw_states=states,
                )

                # PATCH P-23: G-3's four collapse indicators, sampled at the
                # FIRST decision step of every episode.
                #
                # They are here because B17's first question -- does
                # shared-Q + argmax still collapse in the new environment --
                # is the go/no-go for the whole contribution line, and G-3
                # fails on a MISSING indicator.  Discovering the gap after
                # 9,000 episodes costs the run.
                #
                # The cadence is a pre-registration item, not a convenience:
                # the first step is before epsilon-greedy exploration has
                # been averaged over the episode, so the number describes the
                # policy's own decision surface rather than a mixture of it
                # and the exploration schedule.
                if collapse is None:
                    collapse = compute_collapse_metrics(
                        self._scalarize_q_values(
                            self._predict_objective_q_values(encoded),
                            cfg.objective_weights,
                        ),
                        np.stack([mask.mask for mask in masks]),
                        actions,
                    )

                # Step environment
                result = self.env.step(actions, self._env_rng)

                # PATCH P-05 (W-09): the §6.2 row-capture block is removed.
                # It reached into ``env._beam``, ``env._orbit`` and
                # ``env._user_positions`` — private members of the OLD
                # environment, which this project replaces — and imported
                # ``analysis.phase02_section_6_2_row_producer``, a module that
                # was never ported.  It could not have run here.

                # Encode next states
                next_encoded = self._encode_states(result.user_states)

                # Store transitions per user (ASSUME-MODQN-REP-007: shared policy)
                for uid in range(self.num_users):
                    rw = result.rewards[uid]
                    reward_vec = self.reward_vector_from_step_result(result, uid)

                    # Episode reporting covers every user, served or not.
                    ep_reward += reward_vec
                    if rw.r2_handover < 0:
                        ep_handovers += 1

                    # PATCH P-03 (L-3, SDD §4A.5a(2)-(3)).  A transition may
                    # enter replay only if it is a real decision with a
                    # well-defined bootstrap target:
                    #   (a) mask_t non-empty  -> the action was actually chosen
                    #       by the policy (no-op transitions are dropped), and
                    #   (b) done_t or mask_{t+1} non-empty -> the target's
                    #       masked max is defined.  Without (b) the target row
                    #       is all ``-1e9`` and y = r + 0.9*(-1e9).
                    # Both drop reasons are counted against decision_steps_seen
                    # so probe P1 can apply the §4A.5a(4) gate: dropping makes
                    # outage look FREE (r1~0, r2=0, r3=0 all read as neutral),
                    # which is the very hole the re-entry phi2 exists to close.
                    self._decision_steps_seen += 1
                    if is_no_op(int(actions[uid])):
                        self._no_op_transitions_skipped += 1
                        continue
                    next_mask = result.action_masks[uid].mask
                    if not bool(result.done) and not bool(next_mask.any()):
                        self._all_invalid_next_transitions_skipped += 1
                        continue

                    reward_vec_train = apply_reward_calibration(reward_vec, cfg)
                    self.replay.push(
                        encoded[uid],
                        int(actions[uid]),
                        reward_vec_train.astype(np.float32),
                        next_encoded[uid],
                        masks[uid].mask.copy(),
                        next_mask.copy(),
                        result.done,
                    )
                    self._emit_runtime_real_emission_hook("transition_stored")

                # Update networks
                step_losses = self.update()
                if step_losses[0] > 0:
                    ep_losses += step_losses
                    update_count += 1

                # Advance
                states = result.user_states
                encoded = next_encoded
                masks = result.action_masks

                if result.done:
                    break

            # Target network sync (ASSUME-MODQN-REP-005)
            if (ep + 1) % cfg.target_update_every_episodes == 0:
                self.sync_targets()

            # Record metrics
            avg_reward = ep_reward / max(self.num_users, 1)
            scalar = scalarize_objectives(avg_reward, cfg.objective_weights)
            avg_losses = ep_losses / max(update_count, 1)
            # Both scalings: the effective trade-off is omega_j / c_j, so a
            # log carrying only one of them cannot answer B17's second
            # question without recomputing from numbers it no longer has.
            calibrated = apply_reward_calibration(avg_reward, cfg)
            assert collapse is not None, "an episode ran with no decision step"

            log = EpisodeLog(
                episode=ep,
                epsilon=eps,
                r1_mean=float(avg_reward[0]),
                r2_mean=float(avg_reward[1]),
                r3_mean=float(avg_reward[2]),
                scalar_reward=float(scalar),
                total_handovers=ep_handovers,
                replay_size=len(self.replay),
                losses=(float(avg_losses[0]), float(avg_losses[1]), float(avg_losses[2])),
                active_beam_count=collapse.active_beam_count,
                argmax_agreement=collapse.argmax_agreement,
                q_margin=collapse.q_margin,
                q_entropy=collapse.q_entropy,
                q_margin_raw=collapse.q_margin_raw,
                q_range=collapse.q_range,
                r1_mean_calibrated=float(calibrated[0]),
                r2_mean_calibrated=float(calibrated[1]),
                r3_mean_calibrated=float(calibrated[2]),
            )
            logs.append(log)

            if self._secondary_checkpoint_enabled:
                should_evaluate = ((ep + 1) % eval_every == 0) or (ep == cfg.episodes - 1)
                if should_evaluate:
                    eval_summary = self.evaluate_policy(
                        eval_seeds,
                        episode=ep,
                        evaluation_every_episodes=eval_every,
                    )
                    is_best = (
                        self._best_eval_summary is None
                        or eval_summary.mean_scalar_reward
                        > self._best_eval_summary.mean_scalar_reward
                    )
                    if is_best:
                        self._best_eval_summary = eval_summary
                        self._best_eval_payload = copy.deepcopy(
                            self.build_checkpoint_payload(
                                episode=ep,
                                checkpoint_kind=cfg.checkpoint_secondary_report,
                                logs=logs,
                                include_optimizers=True,
                                evaluation_summary=asdict(eval_summary),
                            )
                        )
                        if progress_every > 0:
                            print(
                                f"[eval {ep+1:5d}/{cfg.episodes}] "
                                f"best-mean-scalar={eval_summary.mean_scalar_reward:.4e} "
                                f"std={eval_summary.std_scalar_reward:.4e} "
                                f"seeds={len(eval_seeds)}"
                            )

            if progress_every > 0 and (ep + 1) % progress_every == 0:
                print(
                    f"[ep {ep+1:5d}/{cfg.episodes}] "
                    f"eps={eps:.3f} "
                    f"scalar={scalar:.4e} "
                    f"r1={avg_reward[0]:.4e} "
                    f"r2={avg_reward[1]:.4f} "
                    f"r3={avg_reward[2]:.4e} "
                    f"ho={ep_handovers} "
                    f"buf={len(self.replay)}"
                )

        return logs
