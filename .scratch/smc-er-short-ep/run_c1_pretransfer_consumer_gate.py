#!/usr/bin/env python3
"""Run deterministic C1 representation and atomic-consumer fixtures."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "src"))

from c1_exp_corpus import load_verified_c1_corpus, sha256_file  # noqa: E402
from check_zero_dose_parity import (  # noqa: E402
    _first_difference,
    validate_receipt as validate_zero_dose_receipt,
)
from smc_er_core import (  # noqa: E402
    AtomicBundle,
    ConsumedBundleLedger,
    update_main_with_source_quota,
)
from mcrl.artifacts import read_checkpoint  # noqa: E402
from mcrl.runtime.q_network import DQNNetwork  # noqa: E402
from mcrl.runtime.trainer_spec import TrainerConfig  # noqa: E402


SPEC = HERE / "C1-PRETRANSFER-CONSUMER-GATE-V1-SPEC-2026-08-28.md"
METHOD = REPO / "docs" / "MULTI-CATFISH-PAPER-ALGORITHM-V0.4-2026-08-27.md"
PRODUCTION_CORE = HERE / "smc_er_core.py"
CORPUS_LOADER = HERE / "c1_exp_corpus.py"
PARITY_CHECKER = HERE / "check_zero_dose_parity.py"
TEST_FILE = HERE / "test_c1_pretransfer_consumer_gate.py"
VALIDATOR = HERE / "c1_pretransfer_gate_validator.py"
VALIDATOR_TEST = HERE / "test_c1_pretransfer_gate_validator.py"
RUN_SHORT_EP = HERE / "run_short_ep.py"
RESULT_SCHEMA = "smc-er-pretransfer-consumer-gate-result-v1"
RAW_SCHEMA = "smc-er-c1-pretransfer-consumer-gate-raw-v1"
CLAIM_CEILING = "C1_ATOMIC_TRANSFER_FOR_EXACT_BOUND_DEVELOPMENTAL_RUNNER_ONLY"
RTOL = 1e-6
ATOL = 1e-7


def _write_new(path: Path, value: Any) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    temporary = path.with_suffix(path.suffix + ".tmp")
    if temporary.exists():
        raise FileExistsError(f"refusing to overwrite staged file {temporary}")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _clone_bundle(bundle: AtomicBundle, **changes: Any) -> AtomicBundle:
    fields = {
        "bundle_id": bundle.bundle_id,
        "source_id": bundle.source_id,
        "source_policy_version": bundle.source_policy_version,
        "block_id": bundle.block_id,
        "step_index": bundle.step_index,
        "states": bundle.states,
        "actions": bundle.actions,
        "rewards": bundle.rewards,
        "next_states": bundle.next_states,
        "masks": bundle.masks,
        "next_masks": bundle.next_masks,
        "done": bundle.done,
        "focal_user": bundle.focal_user,
        "specialist_rewards": bundle.specialist_rewards,
        "behavior_probabilities": bundle.behavior_probabilities,
        "provenance": bundle.provenance,
    }
    fields.update(changes)
    return AtomicBundle(**fields)


class _FixtureReplay:
    """Only the production updater's canonical RNG-consumption seam."""

    def __init__(self, size: int) -> None:
        self.size = int(size)

    def __len__(self) -> int:
        return self.size

    def sample(self, count: int, rng: np.random.Generator) -> tuple[Any, ...]:
        rng.choice(self.size, size=int(count), replace=False)
        return ()


class FixtureMain:
    """Minimal immutable-checkpoint Main clone accepted by the production core."""

    def __init__(self, checkpoint: Any, *, rng_seed: int) -> None:
        self.config = TrainerConfig(**checkpoint.trainer_config)
        self.device = torch.device("cpu")
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(0)
            self.q_nets = torch.nn.ModuleList(
                [
                    DQNNetwork(
                        checkpoint.state_dim,
                        checkpoint.action_dim,
                        self.config.hidden_layers,
                        self.config.activation,
                    )
                    for _ in range(3)
                ]
            )
        self.target_nets = copy.deepcopy(self.q_nets)
        for network, state in zip(self.q_nets, checkpoint.q_networks, strict=True):
            network.load_state_dict(state)
        for network, state in zip(
            self.target_nets, checkpoint.target_networks, strict=True
        ):
            network.load_state_dict(state)
            network.eval()
        self.optimizers = [
            torch.optim.Adam(network.parameters(), lr=self.config.learning_rate)
            for network in self.q_nets
        ]
        if checkpoint.optimizers is not None:
            for optimizer, state in zip(
                self.optimizers, checkpoint.optimizers, strict=True
            ):
                optimizer.load_state_dict(copy.deepcopy(state))
        self.replay = _FixtureReplay(self.config.batch_size)
        self._train_rng = np.random.default_rng(int(rng_seed))


def _snapshot(main: FixtureMain) -> dict[str, Any]:
    return {
        "q": [copy.deepcopy(network.state_dict()) for network in main.q_nets],
        "target": [
            copy.deepcopy(network.state_dict()) for network in main.target_nets
        ],
        "optimizer": [copy.deepcopy(item.state_dict()) for item in main.optimizers],
        "rng": copy.deepcopy(main._train_rng.bit_generator.state),
        "gradients": [
            [
                None if parameter.grad is None else parameter.grad.detach().clone()
                for parameter in network.parameters()
            ]
            for network in main.q_nets
        ],
    }


def _loss_for_rows(
    main: FixtureMain,
    bundle: AtomicBundle,
    rows: np.ndarray,
    objective: int,
) -> torch.Tensor:
    states = torch.tensor(bundle.states[rows], dtype=torch.float32)
    actions = torch.tensor(bundle.actions[rows], dtype=torch.long).unsqueeze(1)
    next_states = torch.tensor(bundle.next_states[rows], dtype=torch.float32)
    next_masks = torch.tensor(bundle.next_masks[rows], dtype=torch.bool)
    rewards = bundle.rewards[rows, objective]
    if main.config.reward_calibration_enabled:
        rewards = rewards / float(main.config.reward_calibration_scales[objective])
    reward = torch.tensor(rewards, dtype=torch.float32)
    done = torch.full((rows.size,), float(bundle.done), dtype=torch.float32)
    current = main.q_nets[objective](states).gather(1, actions).squeeze(1)
    with torch.no_grad():
        successor = main.target_nets[objective](next_states)
        successor[~next_masks] = -1e9
        target = reward + main.config.discount_factor * successor.max(dim=1).values * (
            1.0 - done
        )
    return torch.mean((current - target) ** 2)


def reference_atomic_update(
    main: FixtureMain, bundles: Sequence[AtomicBundle]
) -> tuple[float, float, float]:
    """Independent bundle-unit reference for the production quota updater."""

    if len({bundle.bundle_id for bundle in bundles}) != len(bundles):
        raise ValueError("reference updater rejects duplicate bundle IDs")
    main.replay.sample(main.config.batch_size, main._train_rng)
    losses: list[float] = []
    for objective in range(3):
        bundle_losses = [
            _loss_for_rows(main, bundle, bundle.admissible_rows(), objective)
            for bundle in bundles
            if bundle.admissible_rows().size
        ]
        if not bundle_losses:
            losses.append(0.0)
            continue
        loss = torch.stack(bundle_losses).mean()
        main.optimizers[objective].zero_grad()
        loss.backward()
        main.optimizers[objective].step()
        losses.append(float(loss.item()))
    return tuple(losses)  # type: ignore[return-value]


def _gradient_vector(
    main: FixtureMain,
    bundle: AtomicBundle,
    rows: np.ndarray,
    objective: int,
) -> np.ndarray:
    main.optimizers[objective].zero_grad(set_to_none=True)
    _loss_for_rows(main, bundle, rows, objective).backward()
    pieces = [
        parameter.grad.detach().cpu().reshape(-1)
        for parameter in main.q_nets[objective].parameters()
        if parameter.grad is not None
    ]
    return torch.cat(pieces).numpy().astype(np.float64, copy=True)


def _scalarized_preference(
    main: FixtureMain,
    bundle: AtomicBundle,
    *,
    row: int,
    executed_action: int,
    comparator_action: int,
) -> float:
    """Return the frozen Main weighted-Q preference for two valid actions."""

    weights = np.asarray(main.config.objective_weights, dtype=np.float64)
    with torch.no_grad():
        state = torch.tensor(bundle.states[[row]], dtype=torch.float32)
        heads = np.stack(
            [network(state).cpu().numpy()[0] for network in main.q_nets], axis=0
        )
    scalarized = np.sum(weights[:, None] * heads, axis=0)
    return float(scalarized[executed_action] - scalarized[comparator_action])


def _frozen_main_comparator(
    main: FixtureMain, bundle: AtomicBundle, row: int
) -> int:
    valid = np.flatnonzero(bundle.masks[row])
    if valid.size < 2:
        raise RuntimeError("preference fixture requires two valid actions")
    weights = np.asarray(main.config.objective_weights, dtype=np.float64)
    with torch.no_grad():
        state = torch.tensor(bundle.states[[row]], dtype=torch.float32)
        heads = np.stack(
            [network(state).cpu().numpy()[0] for network in main.q_nets], axis=0
        )
    scalarized = np.sum(weights[:, None] * heads, axis=0)
    return min(map(int, valid), key=lambda action: (-float(scalarized[action]), action))


def _preference_perturbation_check(
    checkpoint: Any,
    *,
    rng_seed: int,
    main_bundle: AtomicBundle,
    c1_bundle: AtomicBundle,
    mutated_bundle: AtomicBundle,
    focal_row: int,
) -> dict[str, Any]:
    """Compare one-row and complete-bundle preference response directions."""

    frozen = FixtureMain(checkpoint, rng_seed=rng_seed)
    row = int(focal_row)
    executed = int(c1_bundle.actions[row])
    comparator = _frozen_main_comparator(frozen, c1_bundle, row)
    if executed == comparator:
        return {
            "informative": False,
            "reason": "the selected row equals the frozen Main comparator",
            "non_reversal": False,
        }
    focal_actions = np.full(c1_bundle.users, -1, dtype=np.int64)
    focal_actions[row] = executed
    focal_base_bundle = _clone_bundle(
        c1_bundle,
        bundle_id="C1-GATE-V1-C1-FOCAL-BASE",
        actions=focal_actions,
    )
    focal_changed_bundle = _clone_bundle(
        mutated_bundle,
        bundle_id="C1-GATE-V1-C1-FOCAL-CHANGED",
        actions=focal_actions,
    )

    branches: dict[str, FixtureMain] = {
        name: FixtureMain(checkpoint, rng_seed=rng_seed)
        for name in ("focal_base", "focal_changed", "atomic_base", "atomic_changed")
    }
    reference_atomic_update(
        branches["focal_base"], [main_bundle, focal_base_bundle]
    )
    reference_atomic_update(
        branches["focal_changed"], [main_bundle, focal_changed_bundle]
    )
    reference_atomic_update(branches["atomic_base"], [main_bundle, c1_bundle])
    reference_atomic_update(
        branches["atomic_changed"], [main_bundle, mutated_bundle]
    )
    preferences = {
        name: _scalarized_preference(
            branch,
            c1_bundle,
            row=row,
            executed_action=executed,
            comparator_action=comparator,
        )
        for name, branch in branches.items()
    }
    focal_delta = preferences["focal_changed"] - preferences["focal_base"]
    atomic_delta = preferences["atomic_changed"] - preferences["atomic_base"]
    product = focal_delta * atomic_delta
    return {
        "informative": bool(abs(focal_delta) > ATOL and abs(atomic_delta) > ATOL),
        "row": row,
        "executed_action": executed,
        "frozen_main_comparator_action": comparator,
        "preferences": preferences,
        "focal_delta": focal_delta,
        "atomic_delta": atomic_delta,
        "direction_product": product,
        "non_reversal": bool(product >= -ATOL),
    }


def _state_close(left: Mapping[str, Any], right: Mapping[str, Any]) -> tuple[bool, str | None]:
    difference = _first_difference(left, right)
    if difference is None:
        return True, None

    def compare(a: Any, b: Any, path: str = "root") -> str | None:
        if isinstance(a, Mapping) and isinstance(b, Mapping) and set(a) == set(b):
            for key in sorted(a, key=str):
                found = compare(a[key], b[key], f"{path}.{key}")
                if found:
                    return found
            return None
        if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)) and len(a) == len(b):
            for index, (x, y) in enumerate(zip(a, b, strict=True)):
                found = compare(x, y, f"{path}[{index}]")
                if found:
                    return found
            return None
        if isinstance(a, torch.Tensor) and isinstance(b, torch.Tensor):
            return None if torch.allclose(a, b, rtol=RTOL, atol=ATOL) else path
        if isinstance(a, np.ndarray) and isinstance(b, np.ndarray):
            return None if np.allclose(a, b, rtol=RTOL, atol=ATOL) else path
        return None if a == b else path

    tolerant = compare(left, right)
    return tolerant is None, tolerant


def evaluate_gate(
    *,
    checkpoint_path: Path,
    corpus_manifest_path: Path,
    zero_dose_parity_path: Path,
) -> dict[str, Any]:
    try:
        validate_zero_dose_receipt(zero_dose_parity_path)
    except Exception as exc:
        raise RuntimeError(
            "current zero-dose parity prerequisite is not an authenticated exact PASS"
        ) from exc
    checkpoint = read_checkpoint(checkpoint_path, map_location="cpu")
    checkpoint_sha = sha256_file(checkpoint_path)
    corpus = load_verified_c1_corpus(
        corpus_manifest_path,
        expected_checkpoint_sha256=checkpoint_sha,
        expected_state_dim=checkpoint.state_dim,
        expected_action_dim=checkpoint.action_dim,
    )
    c1 = corpus.prefill_bundles(informed=True)[0]
    main_source = _clone_bundle(
        corpus.prefill_bundles(informed=False)[0],
        bundle_id="C1-GATE-V1-MAIN-FIXTURE",
        source_id="Main",
        specialist_rewards=None,
        provenance={"fixture": "frozen_main_unit"},
    )
    c1 = _clone_bundle(c1, bundle_id="C1-GATE-V1-C1-FIXTURE")
    rng_seed = int.from_bytes(bytes.fromhex(checkpoint_sha)[:8], "big")

    production = FixtureMain(checkpoint, rng_seed=rng_seed)
    reference = FixtureMain(checkpoint, rng_seed=rng_seed)
    production_losses, production_receipt = update_main_with_source_quota(
        production,
        [c1],
        source_quota=("C1",),
        main_bundle=main_source,
        consumed_ledger=ConsumedBundleLedger(),
    )
    reference_losses = reference_atomic_update(reference, [main_source, c1])
    production_snapshot = _snapshot(production)
    reference_snapshot = _snapshot(reference)
    reference_state_equal, reference_difference = _state_close(
        production_snapshot, reference_snapshot
    )

    private_a = _clone_bundle(
        c1,
        specialist_rewards=np.full(c1.users, 1e12, dtype=np.float64),
        provenance={"hidden_trigger": "positive", "acrm": 1e12},
    )
    private_b = _clone_bundle(
        c1,
        specialist_rewards=np.full(c1.users, -1e12, dtype=np.float64),
        provenance={"hidden_trigger": "negative", "acrm": -1e12},
    )
    alias_left = FixtureMain(checkpoint, rng_seed=rng_seed)
    alias_right = FixtureMain(checkpoint, rng_seed=rng_seed)
    alias_left_losses, _ = update_main_with_source_quota(
        alias_left,
        [private_a],
        source_quota=("C1",),
        main_bundle=main_source,
        consumed_ledger=ConsumedBundleLedger(),
    )
    alias_right_losses, _ = update_main_with_source_quota(
        alias_right,
        [private_b],
        source_quota=("C1",),
        main_bundle=main_source,
        consumed_ledger=ConsumedBundleLedger(),
    )
    alias_equal = _first_difference(_snapshot(alias_left), _snapshot(alias_right)) is None

    rows = c1.admissible_rows()
    if rows.size == 0:
        raise RuntimeError("C1 consumer fixture has no admissible rows")
    frozen_for_fixture = FixtureMain(checkpoint, rng_seed=rng_seed)
    informative_rows = [
        int(raw_row)
        for raw_row in rows
        if int(c1.actions[int(raw_row)])
        != _frozen_main_comparator(frozen_for_fixture, c1, int(raw_row))
    ]
    focal = informative_rows[0] if informative_rows else int(rows[0])
    mutated_rewards = np.array(c1.rewards, copy=True)
    mutated_rewards[focal] += np.asarray(
        checkpoint.trainer_config["reward_calibration_scales"], dtype=np.float64
    )
    mutated = _clone_bundle(c1, rewards=mutated_rewards)
    gradient_rows: list[dict[str, Any]] = []
    for objective in range(3):
        base_main = FixtureMain(checkpoint, rng_seed=rng_seed)
        focal_base = _gradient_vector(
            base_main, c1, np.asarray([focal], dtype=np.int64), objective
        )
        focal_changed = _gradient_vector(
            base_main, mutated, np.asarray([focal], dtype=np.int64), objective
        )
        atomic_base = _gradient_vector(base_main, c1, rows, objective)
        atomic_changed = _gradient_vector(base_main, mutated, rows, objective)
        focal_delta = focal_changed - focal_base
        atomic_delta = atomic_changed - atomic_base
        dot = float(np.dot(focal_delta, atomic_delta))
        gradient_rows.append(
            {
                "objective": objective,
                "focal_user": focal,
                "focal_delta_norm": float(np.linalg.norm(focal_delta)),
                "atomic_delta_norm": float(np.linalg.norm(atomic_delta)),
                "dot_product": dot,
                "nonnegative": bool(dot >= -ATOL),
            }
        )

    preference = _preference_perturbation_check(
        checkpoint,
        rng_seed=rng_seed,
        main_bundle=main_source,
        c1_bundle=c1,
        mutated_bundle=mutated,
        focal_row=focal,
    )

    excluded_row = int(rows[-1])
    noop_actions = np.array(c1.actions, copy=True)
    noop_actions[excluded_row] = -1
    noop_base = _clone_bundle(
        c1,
        bundle_id="C1-GATE-V1-C1-NOOP",
        actions=noop_actions,
    )
    noop_rewards = np.array(noop_base.rewards, copy=True)
    noop_rewards[excluded_row] += np.asarray(
        checkpoint.trainer_config["reward_calibration_scales"], dtype=np.float64
    ) * 1e6
    noop_changed = _clone_bundle(noop_base, rewards=noop_rewards)
    noop_left = FixtureMain(checkpoint, rng_seed=rng_seed)
    noop_right = FixtureMain(checkpoint, rng_seed=rng_seed)
    noop_left_losses, _ = update_main_with_source_quota(
        noop_left,
        [noop_base],
        source_quota=("C1",),
        main_bundle=main_source,
        consumed_ledger=ConsumedBundleLedger(),
    )
    noop_right_losses, _ = update_main_with_source_quota(
        noop_right,
        [noop_changed],
        source_quota=("C1",),
        main_bundle=main_source,
        consumed_ledger=ConsumedBundleLedger(),
    )
    noop_equal = _first_difference(_snapshot(noop_left), _snapshot(noop_right)) is None

    permutation = np.arange(c1.users - 1, -1, -1, dtype=np.int64)
    permuted = _clone_bundle(
        c1,
        bundle_id="C1-GATE-V1-C1-PERMUTED",
        states=c1.states[permutation],
        actions=c1.actions[permutation],
        rewards=c1.rewards[permutation],
        next_states=c1.next_states[permutation],
        masks=c1.masks[permutation],
        next_masks=c1.next_masks[permutation],
        specialist_rewards=(
            None
            if c1.specialist_rewards is None
            else c1.specialist_rewards[permutation]
        ),
        behavior_probabilities=(
            None
            if c1.behavior_probabilities is None
            else c1.behavior_probabilities[permutation]
        ),
    )
    ordered_main = FixtureMain(checkpoint, rng_seed=rng_seed)
    permuted_main = FixtureMain(checkpoint, rng_seed=rng_seed)
    ordered_losses, _ = update_main_with_source_quota(
        ordered_main,
        [c1],
        source_quota=("C1",),
        main_bundle=main_source,
        consumed_ledger=ConsumedBundleLedger(),
    )
    permuted_losses, _ = update_main_with_source_quota(
        permuted_main,
        [permuted],
        source_quota=("C1",),
        main_bundle=main_source,
        consumed_ledger=ConsumedBundleLedger(),
    )
    permutation_equal, permutation_difference = _state_close(
        _snapshot(ordered_main), _snapshot(permuted_main)
    )

    ledger = ConsumedBundleLedger()
    ledger.admit([c1])
    restored = ConsumedBundleLedger()
    restored.load_state_dict(ledger.state_dict())
    duplicate_rejected = False
    try:
        restored.admit([c1])
    except ValueError:
        duplicate_rejected = True

    checks = {
        "zero_dose_exact_pass": True,
        "production_matches_independent_reference": bool(
            np.allclose(production_losses, reference_losses, rtol=RTOL, atol=ATOL)
            and reference_state_equal
        ),
        "private_signal_and_provenance_invariant": bool(
            alias_left_losses == alias_right_losses and alias_equal
        ),
        "isolated_row_gradient_has_no_atomic_credit_reversal": all(
            row["nonnegative"] for row in gradient_rows
        ),
        "executed_vs_frozen_main_preference_has_no_reversal": bool(
            preference.get("informative") is True
            and preference.get("non_reversal") is True
        ),
        "noop_row_has_zero_hidden_weight": bool(
            noop_left_losses == noop_right_losses and noop_equal
        ),
        "row_permutation_invariant": bool(
            np.allclose(ordered_losses, permuted_losses, rtol=RTOL, atol=ATOL)
            and permutation_equal
        ),
        "all_admissible_rows_counted_once": bool(
            len(set(map(int, rows))) == rows.size
            and np.all(np.diff(rows) > 0)
            and production_receipt.get("unit_definition")
            == "one_complete_atomic_bundle_per_source"
            and production_receipt.get("source_units") == ["Main", "C1"]
        ),
        "durable_duplicate_rejected_after_resume": duplicate_rejected,
    }
    return {
        "schema": RAW_SCHEMA,
        "status": "complete",
        "claim_ceiling": CLAIM_CEILING,
        "checks": checks,
        "fixtures": {
            "checkpoint_sha256": checkpoint_sha,
            "corpus_manifest_sha256": corpus.manifest_sha256,
            "corpus_sha256": corpus.corpus_sha256,
            "main_bundle_id": main_source.bundle_id,
            "c1_bundle_id": c1.bundle_id,
            "users": c1.users,
            "admissible_rows": rows.tolist(),
            "focal_fixture_user": focal,
        },
        "reference": {
            "production_losses": list(production_losses),
            "reference_losses": list(reference_losses),
            "state_equal": reference_state_equal,
            "first_difference": reference_difference,
        },
        "private_alias": {
            "left_losses": list(alias_left_losses),
            "right_losses": list(alias_right_losses),
            "state_equal": alias_equal,
            "canonical_bundle_equal": True,
            "private_rewards_differ": True,
            "hidden_trigger_labels_differ": True,
        },
        "gradient_rows": gradient_rows,
        "preference_perturbation": preference,
        "noop_row": {
            "excluded_row": excluded_row,
            "base_losses": list(noop_left_losses),
            "changed_losses": list(noop_right_losses),
            "state_equal": noop_equal,
        },
        "permutation": {
            "ordered_losses": list(ordered_losses),
            "permuted_losses": list(permuted_losses),
            "state_equal": permutation_equal,
            "first_difference": permutation_difference,
        },
        "duplicate_ledger": {
            "saved_state": ledger.state_dict(),
            "restored_state": restored.state_dict(),
            "duplicate_rejected": duplicate_rejected,
        },
    }


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--c1-exp-corpus-manifest", type=Path, required=True)
    parser.add_argument("--zero-dose-parity", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    output = args.output_dir.expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"refusing to reuse gate output directory: {output}")
    for path in (
        SPEC,
        METHOD,
        PRODUCTION_CORE,
        CORPUS_LOADER,
        PARITY_CHECKER,
        TEST_FILE,
        VALIDATOR,
        VALIDATOR_TEST,
        RUN_SHORT_EP,
        args.checkpoint,
        args.c1_exp_corpus_manifest,
        args.zero_dose_parity,
    ):
        if not Path(path).expanduser().resolve().is_file():
            raise FileNotFoundError(path)
    raw = evaluate_gate(
        checkpoint_path=args.checkpoint.expanduser().resolve(),
        corpus_manifest_path=args.c1_exp_corpus_manifest.expanduser().resolve(),
        zero_dose_parity_path=args.zero_dose_parity.expanduser().resolve(),
    )
    output.mkdir(parents=True, exist_ok=False)
    raw_path = output / "c1-pretransfer-consumer-gate-raw.json"
    _write_new(raw_path, raw)
    passed = all(raw["checks"].values())
    result = {
        "schema": RESULT_SCHEMA,
        "source": "C1",
        "gate_type": "pretransfer-representation-and-atomic-bundle",
        "status": "PASS" if passed else "FAIL",
        "decision": "ROUTE" if passed else "SHADOW",
        "prerequisites_closed": True,
        "claim_ceiling": CLAIM_CEILING,
        "checks": raw["checks"],
        "protocol": {
            "deterministic_seedless_fixtures": True,
            "persistent_main_updated": False,
            "outcome_or_ee_selection": False,
            "authorized_source": "C1",
            "authorized_follow_on": "post-gate-4EP-developmental-carrier-efficacy-micro-screen",
            "loss_family": "canonical-Main-MSE",
            "bundle_weight": 1.0,
        },
        "authority": {
            "spec_path": str(SPEC),
            "spec_sha256": sha256_file(SPEC),
            "runner_path": str(Path(__file__).resolve()),
            "runner_sha256": sha256_file(Path(__file__).resolve()),
            "test_path": str(TEST_FILE),
            "test_sha256": sha256_file(TEST_FILE),
            "validator_path": str(VALIDATOR),
            "validator_sha256": sha256_file(VALIDATOR),
            "validator_test_path": str(VALIDATOR_TEST),
            "validator_test_sha256": sha256_file(VALIDATOR_TEST),
            "method_path": str(METHOD),
            "method_sha256": sha256_file(METHOD),
            "routing_core_path": str(PRODUCTION_CORE),
            "routing_core_sha256": sha256_file(PRODUCTION_CORE),
            "corpus_loader_path": str(CORPUS_LOADER),
            "corpus_loader_sha256": sha256_file(CORPUS_LOADER),
            "parity_checker_path": str(PARITY_CHECKER),
            "parity_checker_sha256": sha256_file(PARITY_CHECKER),
            "run_short_ep_path": str(RUN_SHORT_EP),
            "run_short_ep_sha256": sha256_file(RUN_SHORT_EP),
            "checkpoint_path": str(args.checkpoint.expanduser().resolve()),
            "checkpoint_sha256": sha256_file(args.checkpoint.expanduser().resolve()),
            "corpus_manifest_path": str(args.c1_exp_corpus_manifest.expanduser().resolve()),
            "corpus_manifest_sha256": sha256_file(args.c1_exp_corpus_manifest.expanduser().resolve()),
            "zero_dose_parity_path": str(args.zero_dose_parity.expanduser().resolve()),
            "zero_dose_parity_sha256": sha256_file(args.zero_dose_parity.expanduser().resolve()),
            "raw_path": str(raw_path),
            "raw_sha256": sha256_file(raw_path),
        },
    }
    result_path = output / "c1-pretransfer-consumer-gate-result.json"
    _write_new(result_path, result)
    print(result_path)
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ATOL",
    "CLAIM_CEILING",
    "FixtureMain",
    "RAW_SCHEMA",
    "RESULT_SCHEMA",
    "RTOL",
    "evaluate_gate",
    "reference_atomic_update",
]
