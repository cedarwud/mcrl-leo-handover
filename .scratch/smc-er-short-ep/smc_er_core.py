"""Isolated Multi-Catfish MCRL learner and atomic-bundle primitives.

Nothing in this developmental carrier is reachable from ``src/mcrl``.  The
canonical environment and unchanged Main MODQN are imported; specialist and
experience-routing mechanics remain here behind G-6.
"""

from __future__ import annotations

import copy
import hashlib
import math
import sys
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src"))

from mcrl.algorithms.modqn import MODQNTrainer  # noqa: E402
from mcrl.env.action_contract import NO_OP_ACTION  # noqa: E402
from mcrl.runtime.finiteness import (  # noqa: E402
    assert_finite_gradients,
    assert_finite_loss,
    assert_finite_parameters,
)
from mcrl.runtime.q_network import DQNNetwork  # noqa: E402
from mcrl.runtime.trainer_spec import TrainerConfig  # noqa: E402


SOURCE_IDS = ("Main", "C1", "C2", "C3")


def _immutable_array(value: Any, *, dtype: Any | None = None) -> np.ndarray:
    array = np.array(value, dtype=dtype, copy=True)
    array.setflags(write=False)
    return array


class FrozenDict(dict[Any, Any]):
    """JSON-compatible dictionary whose lineage cannot mutate after admission."""

    @staticmethod
    def _blocked(*_args: Any, **_kwargs: Any) -> None:
        raise TypeError("frozen provenance cannot be mutated")

    __setitem__ = _blocked
    __delitem__ = _blocked
    clear = _blocked
    pop = _blocked
    popitem = _blocked
    setdefault = _blocked
    update = _blocked

    def __deepcopy__(self, _memo: dict[int, Any]) -> "FrozenDict":
        return self

    def __reduce_ex__(self, _protocol: int) -> tuple[Any, tuple[dict[Any, Any]]]:
        """Rebuild through the constructor instead of mutating on unpickle."""
        return (type(self), (dict(self),))


def _freeze_lineage(value: Any) -> Any:
    if isinstance(value, Mapping):
        return FrozenDict(
            {
                copy.deepcopy(key): _freeze_lineage(item)
                for key, item in value.items()
            }
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_lineage(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze_lineage(item) for item in value)
    if isinstance(value, np.ndarray):
        return _immutable_array(value)
    return copy.deepcopy(value)


@dataclass(frozen=True)
class AtomicBundle:
    """One complete joint environment transition with immutable lineage."""

    bundle_id: str
    source_id: str
    source_policy_version: int
    block_id: int
    step_index: int
    states: np.ndarray
    actions: np.ndarray
    rewards: np.ndarray
    next_states: np.ndarray
    masks: np.ndarray
    next_masks: np.ndarray
    done: bool
    focal_user: int | None = None
    specialist_rewards: np.ndarray | None = None
    behavior_probabilities: np.ndarray | None = None
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.bundle_id:
            raise ValueError("bundle_id cannot be empty")
        if self.source_id not in SOURCE_IDS:
            raise ValueError(f"unknown source_id {self.source_id!r}")
        states = _immutable_array(self.states, dtype=np.float32)
        actions = _immutable_array(self.actions, dtype=np.int64)
        rewards = _immutable_array(self.rewards, dtype=np.float64)
        next_states = _immutable_array(self.next_states, dtype=np.float32)
        masks = _immutable_array(self.masks, dtype=bool)
        next_masks = _immutable_array(self.next_masks, dtype=bool)
        users = states.shape[0]
        if states.ndim != 2 or next_states.shape != states.shape:
            raise ValueError("states and next_states must share shape (U,D)")
        if actions.shape != (users,):
            raise ValueError("actions must have shape (U,)")
        if rewards.shape != (users, 3):
            raise ValueError("rewards must have shape (U,3)")
        if masks.ndim != 2 or masks.shape[0] != users:
            raise ValueError("masks must have shape (U,A)")
        if next_masks.shape != masks.shape:
            raise ValueError("next_masks must match masks")
        valid_action = actions != NO_OP_ACTION
        if np.any(valid_action & ((actions < 0) | (actions >= masks.shape[1]))):
            raise ValueError("actions must be NO_OP_ACTION or a valid action index")
        if np.any(valid_action & ~masks[np.arange(users), np.maximum(actions, 0)]):
            raise ValueError("an executed action is false under its decision mask")
        if not np.all(np.isfinite(states)) or not np.all(np.isfinite(next_states)):
            raise ValueError("bundle states must be finite")
        if not np.all(np.isfinite(rewards)):
            raise ValueError("bundle rewards must be finite")
        if self.focal_user is not None and not 0 <= int(self.focal_user) < users:
            raise ValueError("focal_user is outside the bundle")
        specialist_rewards = None
        if self.specialist_rewards is not None:
            specialist_rewards = _immutable_array(
                self.specialist_rewards, dtype=np.float64
            )
            if specialist_rewards.shape != (users,):
                raise ValueError("specialist_rewards must have shape (U,)")
            if not np.all(np.isfinite(specialist_rewards)):
                raise ValueError("specialist_rewards must be finite")
        probabilities = None
        if self.behavior_probabilities is not None:
            probabilities = _immutable_array(
                self.behavior_probabilities, dtype=np.float64
            )
            if probabilities.shape != (users,):
                raise ValueError("behavior_probabilities must have shape (U,)")
            if np.any(~np.isfinite(probabilities)) or np.any(
                (probabilities < 0.0) | (probabilities > 1.0)
            ):
                raise ValueError("behavior probabilities must be finite in [0,1]")
        object.__setattr__(self, "states", states)
        object.__setattr__(self, "actions", actions)
        object.__setattr__(self, "rewards", rewards)
        object.__setattr__(self, "next_states", next_states)
        object.__setattr__(self, "masks", masks)
        object.__setattr__(self, "next_masks", next_masks)
        object.__setattr__(self, "specialist_rewards", specialist_rewards)
        object.__setattr__(self, "behavior_probabilities", probabilities)
        object.__setattr__(self, "provenance", _freeze_lineage(self.provenance))

    @property
    def users(self) -> int:
        return int(self.actions.size)

    def admissible_rows(self) -> np.ndarray:
        action_exists = self.actions != NO_OP_ACTION
        bootstrap_exists = bool(self.done) | self.next_masks.any(axis=1)
        return np.flatnonzero(action_exists & bootstrap_exists)


class BundleReplay:
    """FIFO replay whose atomic unit is one complete joint bundle."""

    FORMAT_VERSION = 1

    def __init__(self, capacity: int) -> None:
        if isinstance(capacity, bool) or not isinstance(capacity, int):
            raise TypeError("bundle capacity must be an integer")
        if capacity < 1:
            raise ValueError("bundle capacity must be positive")
        self.capacity = capacity
        self._items: deque[AtomicBundle] = deque(maxlen=capacity)
        self._seen: set[str] = set()

    def push(self, bundle: AtomicBundle) -> None:
        if bundle.bundle_id in self._seen:
            raise ValueError(f"duplicate bundle routing: {bundle.bundle_id}")
        self._items.append(bundle)
        self._seen.add(bundle.bundle_id)

    def sample(
        self, count: int, rng: np.random.Generator
    ) -> tuple[AtomicBundle, ...]:
        if count < 0:
            raise ValueError("sample count cannot be negative")
        if count > len(self._items):
            raise ValueError("bundle replay shortage")
        if count == 0:
            return ()
        indices = rng.choice(len(self._items), size=count, replace=False)
        return tuple(self._items[int(index)] for index in np.atleast_1d(indices))

    def __len__(self) -> int:
        return len(self._items)

    def state_dict(self) -> dict[str, Any]:
        return {
            "format_version": self.FORMAT_VERSION,
            "capacity": self.capacity,
            # AtomicBundle is frozen and all ndarray payloads are read-only.
            # Retaining the immutable objects avoids doubling multi-GB replay
            # memory during a rolling checkpoint.
            "items": list(self._items),
            "seen": sorted(self._seen),
        }

    def load_state_dict(self, state: Mapping[str, Any]) -> None:
        if state.get("format_version") != self.FORMAT_VERSION:
            raise ValueError("unsupported bundle replay format")
        if state.get("capacity") != self.capacity:
            raise ValueError("bundle replay capacity mismatch")
        items = state.get("items")
        seen = state.get("seen")
        if not isinstance(items, Sequence) or not isinstance(seen, Sequence):
            raise TypeError("bundle replay state is malformed")
        if len(items) > self.capacity or any(
            not isinstance(item, AtomicBundle) for item in items
        ):
            raise ValueError("bundle replay items are invalid")
        ids = [item.bundle_id for item in items]
        if len(set(ids)) != len(ids) or not set(ids).issubset(set(map(str, seen))):
            raise ValueError("bundle replay lineage is inconsistent")
        self._items = deque(list(items), maxlen=self.capacity)
        self._seen = set(map(str, seen))


class ConsumedBundleLedger:
    """Durable at-most-once admission ledger for specialist-to-Main routing."""

    FORMAT_VERSION = 1

    def __init__(self) -> None:
        self._seen: set[str] = set()

    def preflight(self, bundles: Sequence[AtomicBundle]) -> tuple[str, ...]:
        """Validate at-most-once admission without mutating durable state."""

        ids = tuple(bundle.bundle_id for bundle in bundles)
        if len(ids) != len(set(ids)):
            raise ValueError("the same bundle cannot enter one Main update twice")
        repeated = sorted(set(ids) & self._seen)
        if repeated:
            raise ValueError(
                "specialist bundle was already consumed by Main: "
                + ",".join(repeated)
            )
        return ids

    def commit(self, bundle_ids: Sequence[str]) -> tuple[str, ...]:
        """Commit IDs only after the corresponding Main update succeeds."""

        ids = tuple(bundle_ids)
        if any(type(value) is not str or not value for value in ids):
            raise ValueError("committed bundle IDs must be nonempty exact strings")
        if len(ids) != len(set(ids)):
            raise ValueError("the same bundle cannot enter one Main update twice")
        repeated = sorted(set(ids) & self._seen)
        if repeated:
            raise ValueError(
                "specialist bundle was already consumed by Main: "
                + ",".join(repeated)
            )
        self._seen.update(ids)
        return ids

    def admit(self, bundles: Sequence[AtomicBundle]) -> tuple[str, ...]:
        """Compatibility helper for an already-successful external operation."""

        return self.commit(self.preflight(bundles))

    def __len__(self) -> int:
        return len(self._seen)

    def state_dict(self) -> dict[str, Any]:
        return {
            "format_version": self.FORMAT_VERSION,
            "seen_bundle_ids": sorted(self._seen),
        }

    def load_state_dict(self, state: Mapping[str, Any]) -> None:
        if state.get("format_version") != self.FORMAT_VERSION:
            raise ValueError("unsupported consumed-bundle ledger format")
        raw = state.get("seen_bundle_ids")
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
            raise TypeError("consumed-bundle ledger state is malformed")
        ids = tuple(str(value) for value in raw)
        if any(not value for value in ids) or len(ids) != len(set(ids)):
            raise ValueError("consumed-bundle ledger IDs are invalid")
        self._seen = set(ids)


@dataclass(frozen=True)
class GateLedger:
    """Independent consumer verdicts; absent entries fail closed."""

    C1: str = "shadow"
    C2: str = "shadow"
    C3: str = "shadow"

    def __post_init__(self) -> None:
        for source in ("C1", "C2", "C3"):
            if getattr(self, source) not in {"route", "shadow"}:
                raise ValueError(f"{source} gate must be route or shadow")

    def routes(self, source_id: str) -> bool:
        if source_id == "Main":
            return True
        if source_id not in {"C1", "C2", "C3"}:
            raise ValueError(f"unknown source {source_id!r}")
        return getattr(self, source_id) == "route"


class ObjectiveSpecialist:
    """One online/target DQN belonging to exactly one canonical objective."""

    def __init__(
        self,
        *,
        objective_index: int,
        state_dim: int,
        action_dim: int,
        config: TrainerConfig,
        seed: int,
    ) -> None:
        if objective_index not in (0, 1, 2):
            raise ValueError("objective_index must be 0, 1, or 2")
        self.objective_index = objective_index
        self.config = config
        self.seed = int(seed)
        self.rng = np.random.default_rng(self.seed)
        self.replay_rng = np.random.default_rng(self.seed + 1_000_003)
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(self.seed)
            self.online = DQNNetwork(
                state_dim,
                action_dim,
                config.hidden_layers,
                config.activation,
            )
        self.target = copy.deepcopy(self.online)
        self.target.eval()
        self.optimizer = optim.Adam(
            self.online.parameters(), lr=config.learning_rate
        )
        self.loss_fn = nn.MSELoss()
        self.policy_version = 0
        self.updates = 0

    def q_values(self, states: np.ndarray) -> np.ndarray:
        with torch.no_grad():
            tensor = torch.tensor(states, dtype=torch.float32)
            return self.online(tensor).cpu().numpy()

    def select_row(
        self,
        state: np.ndarray,
        support: Sequence[int],
        *,
        epsilon: float,
        informed: bool,
    ) -> tuple[int, float]:
        ordered = tuple(dict.fromkeys(int(action) for action in support))
        if not ordered:
            return NO_OP_ACTION, 1.0
        if any(action < 0 for action in ordered):
            raise ValueError("specialist support cannot contain NO_OP_ACTION")
        if not math.isfinite(epsilon) or not 0.0 <= epsilon <= 1.0:
            raise ValueError("epsilon must be finite in [0,1]")
        if not informed:
            selected = int(ordered[int(self.rng.integers(0, len(ordered)))])
            return selected, 1.0 / len(ordered)
        q = self.q_values(np.asarray(state, dtype=np.float32)[None, :])[0]
        greedy = min(ordered, key=lambda action: (-float(q[action]), action))
        if self.rng.random() < epsilon:
            selected = int(ordered[int(self.rng.integers(0, len(ordered)))])
        else:
            selected = int(greedy)
        marginal_probability = epsilon / len(ordered)
        if selected == greedy:
            marginal_probability += 1.0 - epsilon
        return selected, float(marginal_probability)

    def update_bundle(self, bundle: AtomicBundle) -> float:
        rows = bundle.admissible_rows()
        if self.objective_index in (1, 2):
            if bundle.focal_user is None:
                raise ValueError("C2/C3 specialist bundle requires focal_user")
            rows = rows[rows == int(bundle.focal_user)]
        if rows.size == 0:
            return 0.0
        rewards = (
            bundle.specialist_rewards[rows]
            if bundle.specialist_rewards is not None
            else bundle.rewards[rows, self.objective_index]
        )
        if self.config.reward_calibration_enabled:
            rewards = rewards / float(
                self.config.reward_calibration_scales[self.objective_index]
            )
        states = torch.tensor(bundle.states[rows], dtype=torch.float32)
        actions = torch.tensor(bundle.actions[rows], dtype=torch.long).unsqueeze(1)
        next_states = torch.tensor(bundle.next_states[rows], dtype=torch.float32)
        next_masks = torch.tensor(bundle.next_masks[rows], dtype=torch.bool)
        reward_t = torch.tensor(rewards, dtype=torch.float32)
        done = torch.full(
            (rows.size,), float(bundle.done), dtype=torch.float32
        )
        q_current = self.online(states).gather(1, actions).squeeze(1)
        with torch.no_grad():
            q_next = self.target(next_states)
            q_next[~next_masks] = -1e9
            q_next_max = q_next.max(dim=1).values
            target = reward_t + self.config.discount_factor * q_next_max * (
                1.0 - done
            )
        loss = self.loss_fn(q_current, target)
        assert_finite_loss(loss, objective=self.objective_index)
        self.optimizer.zero_grad()
        loss.backward()
        assert_finite_gradients(
            self.online.parameters(), objective=self.objective_index
        )
        self.optimizer.step()
        assert_finite_parameters([self.online])
        self.updates += 1
        return float(loss.item())

    def update_from_replay(
        self, replay: BundleReplay, *, bundle_count: int = 1
    ) -> tuple[float, tuple[str, ...]]:
        """Sample complete bundles from this specialist's own replay.

        The replay RNG is independent from the behavior-policy RNG so replay
        sampling cannot perturb a later epsilon-greedy action sequence.
        """

        if bundle_count < 1:
            raise ValueError("bundle_count must be positive")
        if len(replay) < bundle_count:
            return 0.0, ()
        sampled = replay.sample(bundle_count, self.replay_rng)
        losses = tuple(self.update_bundle(item) for item in sampled)
        return float(np.mean(losses)), tuple(item.bundle_id for item in sampled)

    def sync_target(self) -> None:
        self.target.load_state_dict(self.online.state_dict())
        self.policy_version += 1

    def state_dict(self) -> dict[str, Any]:
        return {
            "objective_index": self.objective_index,
            "seed": self.seed,
            "online": copy.deepcopy(self.online.state_dict()),
            "target": copy.deepcopy(self.target.state_dict()),
            "optimizer": copy.deepcopy(self.optimizer.state_dict()),
            "rng_state": copy.deepcopy(self.rng.bit_generator.state),
            "replay_rng_state": copy.deepcopy(
                self.replay_rng.bit_generator.state
            ),
            "policy_version": self.policy_version,
            "updates": self.updates,
        }

    def load_state_dict(self, state: Mapping[str, Any]) -> None:
        if state.get("objective_index") != self.objective_index:
            raise ValueError("specialist objective mismatch")
        if state.get("seed") != self.seed:
            raise ValueError("specialist seed mismatch")
        self.online.load_state_dict(state["online"])
        self.target.load_state_dict(state["target"])
        self.optimizer.load_state_dict(state["optimizer"])
        self.rng.bit_generator.state = copy.deepcopy(state["rng_state"])
        self.replay_rng.bit_generator.state = copy.deepcopy(
            state["replay_rng_state"]
        )
        self.policy_version = int(state["policy_version"])
        self.updates = int(state["updates"])


def update_main_from_bundles(
    main: MODQNTrainer, bundles: Sequence[AtomicBundle]
) -> tuple[float, float, float]:
    """One Main update: each complete bundle has total sample weight one."""

    unique = {bundle.bundle_id for bundle in bundles}
    if len(unique) != len(bundles):
        raise ValueError("the same bundle cannot enter one Main update twice")
    usable = [bundle for bundle in bundles if bundle.admissible_rows().size]
    if not usable:
        return (0.0, 0.0, 0.0)
    losses: list[float] = []
    for objective in range(3):
        per_bundle: list[torch.Tensor] = []
        for bundle in usable:
            rows = bundle.admissible_rows()
            states = torch.tensor(
                bundle.states[rows], dtype=torch.float32, device=main.device
            )
            actions = torch.tensor(
                bundle.actions[rows], dtype=torch.long, device=main.device
            ).unsqueeze(1)
            next_states = torch.tensor(
                bundle.next_states[rows], dtype=torch.float32, device=main.device
            )
            next_masks = torch.tensor(
                bundle.next_masks[rows], dtype=torch.bool, device=main.device
            )
            rewards = bundle.rewards[rows, objective]
            if main.config.reward_calibration_enabled:
                rewards = rewards / float(
                    main.config.reward_calibration_scales[objective]
                )
            reward_t = torch.tensor(
                rewards, dtype=torch.float32, device=main.device
            )
            done = torch.full(
                (rows.size,),
                float(bundle.done),
                dtype=torch.float32,
                device=main.device,
            )
            q_current = main.q_nets[objective](states).gather(1, actions).squeeze(1)
            with torch.no_grad():
                q_next = main.target_nets[objective](next_states)
                q_next[~next_masks] = -1e9
                q_next_max = q_next.max(dim=1).values
                target = reward_t + main.config.discount_factor * q_next_max * (
                    1.0 - done
                )
            per_bundle.append(torch.mean((q_current - target) ** 2))
        loss = torch.stack(per_bundle).mean()
        assert_finite_loss(loss, objective=objective)
        main.optimizers[objective].zero_grad()
        loss.backward()
        assert_finite_gradients(
            main.q_nets[objective].parameters(), objective=objective
        )
        main.optimizers[objective].step()
        losses.append(float(loss.item()))
    assert_finite_parameters(main.q_nets)
    if not all(math.isfinite(value) for value in losses):
        raise RuntimeError("Main bundle update produced non-finite loss")
    return losses[0], losses[1], losses[2]


def update_main_with_source_quota(
    main: MODQNTrainer,
    specialist_bundles: Sequence[AtomicBundle],
    *,
    source_quota: Sequence[str] | None = None,
    main_bundle: AtomicBundle | None = None,
    consumed_ledger: ConsumedBundleLedger | None = None,
) -> tuple[tuple[float, float, float], dict[str, Any]]:
    """One Main optimizer update with one unit per admitted source.

    With no routed source this delegates exactly to canonical row-replay.
    Once any source is routed, Main and every routed specialist contribute
    one complete atomic bundle unit; rows are averaged within a bundle and
    units are averaged across the frozen quota.  A missing unit contributes
    zero gradient but remains in the denominator.
    """

    unique = {bundle.bundle_id for bundle in specialist_bundles}
    if len(unique) != len(specialist_bundles):
        raise ValueError("the same specialist bundle cannot enter Main twice")
    if any(bundle.source_id == "Main" for bundle in specialist_bundles):
        raise ValueError("Main-origin experience belongs to canonical replay")
    if source_quota is None:
        quota = tuple(bundle.source_id for bundle in specialist_bundles)
    else:
        quota = tuple(str(source) for source in source_quota)
    if len(set(quota)) != len(quota):
        raise ValueError("source_quota cannot repeat a specialist source")
    if any(source not in {"C1", "C2", "C3"} for source in quota):
        raise ValueError("source_quota must contain only C1, C2, or C3")
    if quota and not isinstance(consumed_ledger, ConsumedBundleLedger):
        raise ValueError("routed source quota requires a consumed-bundle ledger")
    bundle_by_source: dict[str, AtomicBundle] = {}
    for bundle in specialist_bundles:
        if bundle.source_id not in quota:
            raise ValueError("a specialist bundle is outside source_quota")
        if bundle.source_id in bundle_by_source:
            raise ValueError("source_quota accepts at most one bundle per source")
        bundle_by_source[bundle.source_id] = bundle
    if not quota:
        losses = main.update()
        return losses, {
            "mode": "exact_baseline_delegate",
            "source_units": ["Main"],
            "specialist_bundle_ids": [],
            "missing_source_ids": [],
        }
    if main_bundle is None or main_bundle.source_id != "Main":
        raise ValueError("routed source quota requires one Main-origin bundle")
    assert consumed_ledger is not None
    config = main.config
    replay_size_before_update = len(main.replay)
    if replay_size_before_update < config.batch_size:
        return (0.0, 0.0, 0.0), {
            "mode": "warmup_no_update",
            "source_units": [],
            "specialist_bundle_ids": [],
            "requested_source_units": ["Main", *quota],
            "main_bundle_id": main_bundle.bundle_id,
            "admitted_specialist_bundle_ids": [],
            "deferred_specialist_bundle_ids": [
                bundle.bundle_id for bundle in specialist_bundles
            ],
            "main_replay_size_before_update": replay_size_before_update,
            "main_batch_size": int(config.batch_size),
            "canonical_replay_rng_sample_consumed": False,
            "missing_source_ids": [
                source for source in quota if source not in bundle_by_source
            ],
            "unusable_specialist_bundle_ids": [],
        }

    pending_bundle_ids = consumed_ledger.preflight(specialist_bundles)

    # Keep the canonical Main RNG schedule aligned across carriers even
    # though routed mode learns from bundle-composed units rather than the
    # sampled row minibatch.
    main.replay.sample(config.batch_size, main._train_rng)
    quota_rows = [
        ("Main", main_bundle, main_bundle.admissible_rows()),
        *[
        (
            source,
            bundle_by_source.get(source),
            (
                bundle_by_source[source].admissible_rows()
                if source in bundle_by_source
                else np.empty(0, dtype=np.int64)
            ),
        )
        for source in quota
        ],
    ]

    losses: list[float] = []
    for objective in range(3):
        source_losses: list[torch.Tensor] = []
        zero_anchor = next(main.q_nets[objective].parameters()).sum() * 0.0
        for _source, bundle, rows in quota_rows:
            if bundle is None or not rows.size:
                # Fail-closed shortage rule: keep the preregistered source
                # unit in the denominator, but contribute no gradient.  In
                # particular, another lane cannot silently borrow this dose.
                source_losses.append(zero_anchor)
                continue
            bundle_states = torch.tensor(
                bundle.states[rows], dtype=torch.float32, device=main.device
            )
            bundle_actions = torch.tensor(
                bundle.actions[rows], dtype=torch.long, device=main.device
            ).unsqueeze(1)
            bundle_next_states = torch.tensor(
                bundle.next_states[rows], dtype=torch.float32, device=main.device
            )
            bundle_next_masks = torch.tensor(
                bundle.next_masks[rows], dtype=torch.bool, device=main.device
            )
            natural_reward = bundle.rewards[rows, objective]
            if config.reward_calibration_enabled:
                natural_reward = natural_reward / float(
                    config.reward_calibration_scales[objective]
                )
            bundle_reward = torch.tensor(
                natural_reward, dtype=torch.float32, device=main.device
            )
            bundle_done = torch.full(
                (rows.size,),
                float(bundle.done),
                dtype=torch.float32,
                device=main.device,
            )
            bundle_current = main.q_nets[objective](bundle_states).gather(
                1, bundle_actions
            ).squeeze(1)
            with torch.no_grad():
                bundle_next = main.target_nets[objective](bundle_next_states)
                bundle_next[~bundle_next_masks] = -1e9
                bundle_target = bundle_reward + config.discount_factor * (
                    bundle_next.max(dim=1).values
                ) * (1.0 - bundle_done)
            source_losses.append(
                torch.mean((bundle_current - bundle_target) ** 2)
            )

        loss = torch.stack(source_losses).mean()
        assert_finite_loss(loss, objective=objective)
        main.optimizers[objective].zero_grad()
        loss.backward()
        assert_finite_gradients(
            main.q_nets[objective].parameters(), objective=objective
        )
        main.optimizers[objective].step()
        losses.append(float(loss.item()))
    assert_finite_parameters(main.q_nets)
    if not all(math.isfinite(value) for value in losses):
        raise RuntimeError("Main source-quota update produced non-finite loss")
    admitted_bundle_ids = consumed_ledger.commit(pending_bundle_ids)
    return (losses[0], losses[1], losses[2]), {
        "mode": "source_unit_mean",
        "unit_definition": "one_complete_atomic_bundle_per_source",
        "shortage_rule": "zero_gradient_source_unit",
        "source_units": ["Main", *quota],
        "requested_source_units": ["Main", *quota],
        "main_bundle_id": main_bundle.bundle_id,
        "main_replay_size_before_update": replay_size_before_update,
        "main_batch_size": int(config.batch_size),
        "canonical_replay_rng_sample_consumed": True,
        "specialist_bundle_ids": [
            bundle.bundle_id for bundle in specialist_bundles
        ],
        "admitted_specialist_bundle_ids": list(admitted_bundle_ids),
        "deferred_specialist_bundle_ids": [],
        "missing_source_ids": [
            source for source in quota if source not in bundle_by_source
        ],
        "unusable_specialist_bundle_ids": [
            bundle.bundle_id
            for _source, bundle, rows in quota_rows
            if _source != "Main" and bundle is not None and not rows.size
        ],
    }


def update_main_with_role_targeted_donors(
    main: MODQNTrainer,
    specialist_bundles: Sequence[AtomicBundle],
    *,
    source_quota: Sequence[str] | None = None,
    beta: float = 0.25,
    consumed_ledger: ConsumedBundleLedger | None = None,
    consumer_block_id: int | None = None,
) -> tuple[tuple[float, float, float], dict[str, Any]]:
    """Update Main from canonical replay plus diagonal specialist donors.

    C1 augments objective 0, C2 objective 1, and C3 objective 2.  Every
    objective retains the loss from the exact batch sampled by canonical Main
    replay.  A usable scheduled donor changes only its matching objective via
    ``(1-beta) * L_Main + beta * L_Cj``; missing and unusable donors have
    effective beta zero and cannot lend their dose to another objective.

    The older ``update_main_with_source_quota`` carrier is intentionally kept
    separate because it reproduces the sealed all-head source-unit evidence.
    """

    if isinstance(beta, bool) or not isinstance(beta, (int, float, np.number)):
        raise TypeError("beta must be a finite number")
    beta_value = float(beta)
    if not math.isfinite(beta_value) or not 0.0 <= beta_value < 1.0:
        raise ValueError("beta must satisfy 0 <= beta < 1")

    bundle_ids = tuple(bundle.bundle_id for bundle in specialist_bundles)
    if len(bundle_ids) != len(set(bundle_ids)):
        raise ValueError("the same specialist bundle cannot enter Main twice")
    if any(bundle.source_id == "Main" for bundle in specialist_bundles):
        raise ValueError("Main-origin experience belongs to canonical replay")

    if source_quota is None:
        quota = tuple(bundle.source_id for bundle in specialist_bundles)
    else:
        quota = tuple(str(source) for source in source_quota)
    if len(quota) != len(set(quota)):
        raise ValueError("source_quota cannot repeat a specialist source")
    if any(source not in {"C1", "C2", "C3"} for source in quota):
        raise ValueError("source_quota must contain only C1, C2, or C3")
    if consumer_block_id is not None and (
        type(consumer_block_id) is not int or consumer_block_id < 0
    ):
        raise ValueError("consumer_block_id must be a nonnegative exact integer")

    bundle_by_source: dict[str, AtomicBundle] = {}
    for bundle in specialist_bundles:
        if bundle.source_id not in quota:
            raise ValueError("a specialist bundle is outside source_quota")
        if bundle.source_id in bundle_by_source:
            raise ValueError("source_quota accepts at most one bundle per source")
        if bundle.behavior_probabilities is None:
            raise ValueError(
                "routed specialist bundle lacks behavior-probability authority"
            )
        if bundle.source_id in {"C2", "C3"} and bundle.focal_user is None:
            raise ValueError(
                "routed C2/C3 bundle lacks focal-row authority"
            )
        if bundle.source_id == "C1" and bundle.focal_user is not None:
            raise ValueError("routed C1 bundle must remain a joint-row source")
        bundle_by_source[bundle.source_id] = bundle

    resolved_consumer_block = (
        int(consumer_block_id)
        if consumer_block_id is not None
        else max((int(bundle.block_id) for bundle in specialist_bundles), default=0)
    )
    if any(bundle.block_id > resolved_consumer_block for bundle in specialist_bundles):
        raise ValueError("specialist bundle comes from a future consumer block")

    # This direct delegation is the zero-dose parity boundary.  In particular,
    # do not independently reproduce canonical warmup, sampling, loss, or
    # optimizer behavior on this path.
    if not quota:
        losses = main.update()
        return losses, {
            "mode": "exact_baseline_delegate",
            "role_to_objective": {"C1": 0, "C2": 1, "C3": 2},
            "requested_source_ids": [],
            "specialist_bundle_ids": [],
            "scheduled_beta": {},
            "effective_beta": {},
            "missing_source_ids": [],
            "unusable_specialist_bundle_ids": [],
            "canonical_replay_sample_used": None,
            "canonical_sample_used_in_all_objective_losses": None,
            "donor_loss_audit": {},
        }

    if not isinstance(consumed_ledger, ConsumedBundleLedger):
        raise ValueError("routed source quota requires a consumed-bundle ledger")

    role_to_objective = {"C1": 0, "C2": 1, "C3": 2}
    missing_source_ids = [
        source for source in quota if source not in bundle_by_source
    ]
    admissible_by_source = {
        source: (
            bundle_by_source[source].admissible_rows()
            if source in bundle_by_source
            else np.empty(0, dtype=np.int64)
        )
        for source in quota
    }
    rows_by_source: dict[str, np.ndarray] = {}
    nonfocal_audit_rows_by_source: dict[str, np.ndarray] = {}
    for source in quota:
        bundle = bundle_by_source.get(source)
        admissible = admissible_by_source[source]
        if bundle is None or source == "C1":
            rows_by_source[source] = admissible
            nonfocal_audit_rows_by_source[source] = np.empty(
                0, dtype=np.int64
            )
            continue
        focal = int(bundle.focal_user)  # validated above
        rows_by_source[source] = (
            np.array([focal], dtype=np.int64)
            if np.any(admissible == focal)
            else np.empty(0, dtype=np.int64)
        )
        nonfocal_audit_rows_by_source[source] = admissible[admissible != focal]
    unusable_bundle_ids = [
        bundle_by_source[source].bundle_id
        for source in quota
        if source in bundle_by_source and not rows_by_source[source].size
    ]
    scheduled_beta = {
        source: (
            beta_value
            if source in bundle_by_source and rows_by_source[source].size
            else 0.0
        )
        for source in quota
    }

    config = main.config
    replay_size_before_update = len(main.replay)
    common_receipt: dict[str, Any] = {
        "role_to_objective": role_to_objective,
        "requested_source_ids": list(quota),
        "specialist_bundle_ids": list(bundle_ids),
        "scheduled_beta": scheduled_beta,
        "effective_beta": scheduled_beta,
        "missing_source_ids": missing_source_ids,
        "unusable_specialist_bundle_ids": unusable_bundle_ids,
        "main_replay_size_before_update": replay_size_before_update,
        "main_batch_size": int(config.batch_size),
        "dose_borrowing": False,
        "private_specialist_fields_ignored": [
            "specialist_rewards",
            "provenance",
        ],
        "canonical_replay_reward_space": "precalibrated_at_main_admission",
        "donor_reward_space": "canonical_raw_then_main_calibration_once",
    }
    if replay_size_before_update < config.batch_size:
        return (0.0, 0.0, 0.0), {
            "mode": "warmup_no_update",
            **common_receipt,
            "effective_beta": {source: 0.0 for source in quota},
            "admitted_specialist_bundle_ids": [],
            "deferred_specialist_bundle_ids": list(bundle_ids),
            "canonical_replay_sample_used": False,
            "canonical_sample_used_in_all_objective_losses": False,
            "donor_loss_audit": {},
        }

    # Admission is a durable consumed-on-update receipt.  Warm-up returns above
    # without sampling, optimizing, or burning a bundle that can be learned once
    # canonical Main replay reaches its batch threshold.
    pending_bundle_ids = consumed_ledger.preflight(specialist_bundles)

    (
        states,
        actions,
        rewards,
        next_states,
        _masks,
        next_masks,
        dones,
    ) = main.replay.sample(config.batch_size, main._train_rng)
    state_t = torch.tensor(states, dtype=torch.float32, device=main.device)
    action_t = torch.tensor(
        actions, dtype=torch.long, device=main.device
    ).unsqueeze(1)
    next_state_t = torch.tensor(
        next_states, dtype=torch.float32, device=main.device
    )
    next_mask_t = torch.tensor(
        next_masks, dtype=torch.bool, device=main.device
    )
    done_t = torch.tensor(dones, dtype=torch.float32, device=main.device)

    def donor_loss(
        bundle: AtomicBundle,
        rows: np.ndarray,
        objective: int,
    ) -> torch.Tensor:
        donor_states = torch.tensor(
            bundle.states[rows], dtype=torch.float32, device=main.device
        )
        donor_actions = torch.tensor(
            bundle.actions[rows], dtype=torch.long, device=main.device
        ).unsqueeze(1)
        donor_next_states = torch.tensor(
            bundle.next_states[rows], dtype=torch.float32, device=main.device
        )
        donor_next_masks = torch.tensor(
            bundle.next_masks[rows], dtype=torch.bool, device=main.device
        )
        canonical_rewards = bundle.rewards[rows, objective]
        if config.reward_calibration_enabled:
            canonical_rewards = canonical_rewards / float(
                config.reward_calibration_scales[objective]
            )
        donor_rewards = torch.tensor(
            canonical_rewards, dtype=torch.float32, device=main.device
        )
        donor_dones = torch.full(
            (rows.size,),
            float(bundle.done),
            dtype=torch.float32,
            device=main.device,
        )
        donor_current = main.q_nets[objective](donor_states).gather(
            1, donor_actions
        ).squeeze(1)
        with torch.no_grad():
            donor_next = main.target_nets[objective](donor_next_states)
            donor_next[~donor_next_masks] = -1e9
            donor_target = donor_rewards + config.discount_factor * (
                donor_next.max(dim=1).values
            ) * (1.0 - donor_dones)
        # Row mean gives this complete atomic bundle total sample weight one.
        return torch.mean((donor_current - donor_target) ** 2)

    targeted_losses: dict[int, torch.Tensor] = {}
    donor_loss_audit: dict[str, dict[str, Any]] = {}
    for source in quota:
        bundle = bundle_by_source.get(source)
        rows = rows_by_source[source]
        target_objective = role_to_objective[source]
        audit_entry: dict[str, Any] = {
            "bundle_id": bundle.bundle_id if bundle is not None else None,
            "target_objective": target_objective,
            "effective_beta": scheduled_beta[source],
            "source_policy_version": (
                int(bundle.source_policy_version) if bundle is not None else None
            ),
            "source_block_id": int(bundle.block_id) if bundle is not None else None,
            "consumer_block_id": resolved_consumer_block,
            "source_age_blocks": (
                resolved_consumer_block - int(bundle.block_id)
                if bundle is not None
                else None
            ),
            "behavior_probabilities": (
                bundle.behavior_probabilities[rows].tolist()
                if bundle is not None
                and bundle.behavior_probabilities is not None
                and rows.size
                else None
            ),
            "donor_row_policy": (
                "all_admissible_joint_rows"
                if source == "C1"
                else "focal_row_only"
            ),
            "target_rows": rows.tolist(),
            "nonfocal_audit_rows": (
                nonfocal_audit_rows_by_source[source].tolist()
            ),
            "canonical_reward_shape": (
                list(bundle.rewards.shape) if bundle is not None else None
            ),
            "canonical_rewards_sha256": (
                hashlib.sha256(
                    np.ascontiguousarray(bundle.rewards).tobytes()
                ).hexdigest()
                if bundle is not None
                else None
            ),
            "canonical_reward_sums": (
                bundle.rewards.sum(axis=0).tolist()
                if bundle is not None
                else None
            ),
            "target_loss": None,
            "nonfocal_target_loss_no_grad": None,
            "no_grad_audit_losses": {},
        }
        if bundle is not None and rows.size:
            target_loss = donor_loss(bundle, rows, target_objective)
            assert_finite_loss(target_loss, objective=target_objective)
            targeted_losses[target_objective] = target_loss
            audit_entry["target_loss"] = float(target_loss.detach().item())
            with torch.no_grad():
                nonfocal_rows = nonfocal_audit_rows_by_source[source]
                if nonfocal_rows.size:
                    audit_entry["nonfocal_target_loss_no_grad"] = float(
                        donor_loss(
                            bundle, nonfocal_rows, target_objective
                        ).item()
                    )
                audit_entry["no_grad_audit_losses"] = {
                    str(objective): float(
                        donor_loss(bundle, rows, objective).item()
                    )
                    for objective in range(3)
                    if objective != target_objective
                }
        donor_loss_audit[source] = audit_entry

    losses: list[float] = []
    canonical_main_losses: list[float] = []
    for objective in range(3):
        reward_t = torch.tensor(
            rewards[:, objective], dtype=torch.float32, device=main.device
        )
        q_current = main.q_nets[objective](state_t).gather(
            1, action_t
        ).squeeze(1)
        with torch.no_grad():
            q_next = main.target_nets[objective](next_state_t)
            q_next[~next_mask_t] = -1e9
            target = reward_t + config.discount_factor * q_next.max(
                dim=1
            ).values * (1.0 - done_t)
        main_loss = main._loss_fn(q_current, target)
        assert_finite_loss(main_loss, objective=objective)
        canonical_main_losses.append(float(main_loss.detach().item()))

        if objective in targeted_losses:
            loss = (
                (1.0 - beta_value) * main_loss
                + beta_value * targeted_losses[objective]
            )
        else:
            loss = main_loss
        assert_finite_loss(loss, objective=objective)
        main.optimizers[objective].zero_grad()
        loss.backward()
        assert_finite_gradients(
            main.q_nets[objective].parameters(), objective=objective
        )
        main.optimizers[objective].step()
        losses.append(float(loss.item()))

    assert_finite_parameters(main.q_nets)
    if not all(math.isfinite(value) for value in losses):
        raise RuntimeError("role-targeted Main update produced non-finite loss")
    admitted_bundle_ids = consumed_ledger.commit(pending_bundle_ids)
    common_receipt["admitted_specialist_bundle_ids"] = list(admitted_bundle_ids)
    common_receipt["deferred_specialist_bundle_ids"] = []
    return (losses[0], losses[1], losses[2]), {
        "mode": "canonical_main_plus_role_targeted_donor",
        **common_receipt,
        "canonical_replay_sample_used": True,
        "canonical_sample_used_in_all_objective_losses": True,
        "canonical_main_losses": canonical_main_losses,
        "donor_loss_audit": donor_loss_audit,
        "optimizer_steps_per_objective": [1, 1, 1],
        "atomic_donor_row_reduction": "mean_to_bundle_weight_one",
    }


def acrm_rewards(
    catfish_r1: np.ndarray, main_counterfactual_r1: np.ndarray, *, eta: float
) -> np.ndarray:
    """C1-private ACRM; the returned values never enter Main replay."""

    catfish = np.asarray(catfish_r1, dtype=np.float64)
    main = np.asarray(main_counterfactual_r1, dtype=np.float64)
    if catfish.shape != main.shape or catfish.ndim != 1:
        raise ValueError("ACRM operands must share shape (U,)")
    if not np.all(np.isfinite(catfish)) or not np.all(np.isfinite(main)):
        raise ValueError("ACRM operands must be finite")
    if not math.isfinite(eta) or eta < 0.0:
        raise ValueError("eta must be finite and non-negative")
    return catfish + float(eta) * (catfish - main)
