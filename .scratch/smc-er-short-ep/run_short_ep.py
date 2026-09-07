#!/usr/bin/env python3
"""Train one isolated Multi-Catfish MCRL developmental short-episode arm.

Baseline ``B000`` delegates to the unchanged canonical MODQN training loop.
Treatment arms collect four independent trajectories per logical step and
route only complete, gate-authorised bundles into Main.  All specialist
behaviour disappears from the saved Main-only evaluation checkpoint.

V0.2 uses only cheap, pre-outcome physical eligibility online.  C2 opens at a
Main handover boundary; C3 offers explicit defer-to-Main plus already-active,
same-satellite lower-load relocations.  Four-offset counterfactuals are
sampled Stage-0 diagnostics, never per-transition replay admission.  Formal
routing still requires separate sealed consumer-gate evidence;
``--development-route-all`` remains a bounded non-formal trend override.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import platform
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
STAGE0 = HERE.parent / "catfish-stage0"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(STAGE0))
sys.path.insert(0, str(REPO / "src"))

from smc_er_core import (  # noqa: E402
    AtomicBundle,
    BundleReplay,
    ConsumedBundleLedger,
    GateLedger,
    ObjectiveSpecialist,
    acrm_rewards,
    update_main_with_role_targeted_donors,
)
from c1_exp_corpus import (  # noqa: E402
    EXPECTED_USERS as EXPECTED_C1_CORPUS_USERS,
    VerifiedC1Corpus,
    load_verified_c1_corpus,
)
from gate_receipt_validator import (  # noqa: E402
    GateReceiptValidationError,
    validate_main_consumer_result,
)
from c1_pretransfer_gate_validator import (  # noqa: E402
    C1PretransferGateValidationError,
    validate_c1_pretransfer_result,
)
from intermediate_trend_authority import (  # noqa: E402
    CLAIM_CEILING as INTERMEDIATE_TREND_CLAIM_CEILING,
    TREND_CHECKPOINT_EVERY_EPISODES,
    TREND_SPECIALIST_BUNDLE_REPLAY_CAPACITY,
    validate_intermediate_trend_authority,
)
from smc_er_roles import (  # noqa: E402
    OptionCommitment,
    advance_option_after_execution,
    c2_observable_decision,
    c3_relocation_decision,
    epsilon_greedy_probabilities,
    local_snr_greedy_actions,
    main_greedy_actions,
    masked_uniform_actions,
    observable_c2_supports,
    observable_c3_supports,
    physical_key_for_action,
    specialist_joint_actions,
)
from mcrl.algorithms.modqn import MODQNTrainer  # noqa: E402
from mcrl.artifacts import read_checkpoint  # noqa: E402
from mcrl.env.action_contract import Association, is_no_op  # noqa: E402
from mcrl.env.constants import DECISION_STEP_S, TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.env.ephemeris import (  # noqa: E402
    TRAIN,
    BlockAlternatingSplit,
    EpisodeStartSampler,
)
from mcrl.env.mobility import MobilityConfig  # noqa: E402
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver  # noqa: E402
from mcrl.env.step import StepEnvironment  # noqa: E402
from mcrl.env.tle import TleArchive  # noqa: E402
from mcrl.runtime.objective_math import apply_reward_calibration  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.trainer_env import TrainerEnvironment  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    CANONICAL_PREREG,
    CANONICAL_PREREG_BYTE_SHA256,
    _frozen_reward_scales,
    assert_ephemeris_matches_record,
)
from mcrl.runtime.trainer_spec import TrainerConfig  # noqa: E402


SCHEMA = "multi-catfish-mcrl-one-arm-short-ep-v2"
GATE_SCHEMA = "multi-catfish-mcrl-consumer-gates-v2"
GATE_RESULT_SCHEMA = "multi-catfish-mcrl-main-consumer-gate-result-v2"
C1_PRETRANSFER_GATE_RESULT_SCHEMA = "smc-er-pretransfer-consumer-gate-result-v1"
ARM_LANES: dict[str, tuple[bool, bool, bool] | None] = {
    "B000": None,
    "F111": (True, True, True),
    "A011": (False, True, True),
    "A101": (True, False, True),
    "A110": (True, True, False),
    "S100": (True, False, False),
    "S010": (False, True, False),
    "S001": (False, False, True),
}
ARM_ACTIVE_SOURCES: dict[str, frozenset[str]] = {
    "F111": frozenset({"C1", "C2", "C3"}),
    "A011": frozenset({"C2", "C3"}),
    "A101": frozenset({"C1", "C3"}),
    "A110": frozenset({"C1", "C2"}),
    "S100": frozenset({"C1"}),
    "S010": frozenset({"C2"}),
    "S001": frozenset({"C3"}),
}
ARM_LABELS = {
    "B000": "Baseline MODQN",
    "F111": "Full Multi-Catfish MCRL",
    "A011": "Full - C1",
    "A101": "Full - C2",
    "A110": "Full - C3",
    "S100": "C1 only",
    "S010": "C2 only",
    "S001": "C3 only",
}

DEFAULT_CHECKPOINT_EVERY_EPISODES = 100
SPECIALIST_BUNDLE_REPLAY_CAPACITY = TREND_SPECIALIST_BUNDLE_REPLAY_CAPACITY
SOURCE_ORDER = ("Main", "C1", "C2", "C3")
DEFAULT_LEARNING_RATE = 0.001
DEFAULT_ACRM_ETA = 1.0
DEVELOPMENT_MAX_EPISODES = 24
ROLE_SUPPORT_VERSION = "V0.2_OBSERVABLE_ELIGIBILITY"


@dataclass
class Trajectory:
    environment: TrainerEnvironment
    env_rng: np.random.Generator
    mobility_rng: np.random.Generator
    states: list[Any] | None = None
    masks: list[Any] | None = None
    observation: Any | None = None

    def reset(self) -> None:
        states, masks, observation = self.environment.reset(
            self.env_rng, self.mobility_rng
        )
        self.states = states
        self.masks = masks
        self.observation = observation

    def advance(self, result: Any) -> None:
        self.states = list(result.user_states)
        self.masks = list(result.action_masks)
        self.observation = self.environment.last_outcome.observation


@dataclass(frozen=True)
class FrozenMainComparator:
    """Detached scalarized Main surface fixed for one collection block."""

    q_nets: tuple[Any, Any, Any]
    objective_weights: tuple[float, float, float]
    version_sha256: str
    state_encoder: Callable[[Sequence[Any]], np.ndarray]

    @classmethod
    def from_main(cls, main: MODQNTrainer) -> "FrozenMainComparator":
        networks = tuple(copy.deepcopy(net).cpu().eval() for net in main.q_nets)
        digest = hashlib.sha256()
        for objective, network in enumerate(networks):
            for name, tensor in sorted(network.state_dict().items()):
                digest.update(f"{objective}:{name}".encode("utf-8"))
                digest.update(np.asarray(tensor.detach().cpu()).tobytes(order="C"))
        return cls(
            q_nets=networks,  # type: ignore[arg-type]
            objective_weights=tuple(float(value) for value in main.config.objective_weights),
            version_sha256=digest.hexdigest(),
            state_encoder=getattr(
                main,
                "encode_states",
                lambda states: np.asarray(states, dtype=np.float32),
            ),
        )

    @property
    def config(self) -> Any:
        return SimpleNamespace(objective_weights=self.objective_weights)

    def encode_states(self, states: Sequence[Any]) -> np.ndarray:
        return self.state_encoder(states)

    def scalarized_q_values(
        self,
        states_encoded: np.ndarray,
        *,
        objective_weights: Sequence[float] | None = None,
    ) -> np.ndarray:
        if objective_weights is not None and tuple(float(value) for value in objective_weights) != self.objective_weights:
            raise ValueError("frozen Main comparator objective weights drifted")
        with torch.no_grad():
            states = torch.tensor(states_encoded, dtype=torch.float32)
            values = [network(states).cpu().numpy() for network in self.q_nets]
        return (
            self.objective_weights[0] * values[0]
            + self.objective_weights[1] * values[1]
            + self.objective_weights[2] * values[2]
        )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_ephemeris_authority(
    prereg_path: Path, tle_root: Path
) -> tuple[Path, TleArchive, dict[str, Any]]:
    """Fail closed unless this arm uses the sealed prereg and exact TLE set."""

    prereg = Path(prereg_path).expanduser().resolve()
    canonical = Path(CANONICAL_PREREG).resolve()
    if (
        not prereg.is_file()
        or prereg != canonical
        or sha256_file(prereg) != CANONICAL_PREREG_BYTE_SHA256
    ):
        raise RuntimeError("short-EP arms require the canonical sealed preregistration")
    record = read_prereg(prereg)
    record.verify()
    archive = TleArchive(Path(tle_root).expanduser().resolve())
    ephemeris = assert_ephemeris_matches_record(record, archive=archive)
    return prereg, archive, {
        "prereg_path": str(prereg),
        "prereg_sha256": sha256_file(prereg),
        "tle_root_path": str(archive.root.resolve()),
        "tle_file_set_sha256": str(ephemeris["file_set_sha256"]),
        "tle_file_count": int(ephemeris["archive"]["file_count"]),
    }


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            default=lambda item: (
                item.tolist()
                if isinstance(item, np.ndarray)
                else item.item()
                if isinstance(item, np.generic)
                else str(item)
            ),
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _make_environment(archive: TleArchive, *, users: int) -> TrainerEnvironment:
    driver = ScenarioDriver(
        archive,
        ScenarioConfig(mobility=MobilityConfig(num_users=int(users))),
    )
    split = BlockAlternatingSplit.for_archive(archive)
    sampler = EpisodeStartSampler.for_archive(archive, split, TRAIN)
    environment = TrainerEnvironment(StepEnvironment(driver), sampler)
    environment.assert_ready_to_train()
    return environment


def _short_config(
    prereg_path: Path,
    *,
    arm: str,
    episodes: int,
    epsilon_decay_episodes: int,
    target_update_every: int,
    learning_rate: float,
) -> TrainerConfig:
    record = read_prereg(prereg_path)
    record.verify()
    training = record.sections["training"]
    network = record.sections["action_and_state"]
    baseline = arm == "B000"
    return TrainerConfig(
        hidden_layers=tuple(int(value) for value in network["hidden_layers"]),
        activation=str(network["activation"]),
        learning_rate=float(learning_rate),
        discount_factor=float(training["discount_factor"]),
        batch_size=int(training["batch_size"]),
        episodes=int(episodes),
        objective_weights=tuple(
            float(value) for value in training["objective_weights"]
        ),
        epsilon_start=1.0,
        epsilon_end=0.01,
        epsilon_decay_episodes=int(epsilon_decay_episodes),
        target_update_every_episodes=int(target_update_every),
        replay_capacity=int(training["replay_capacity"]),
        training_experiment_kind=(
            "baseline-short-ep" if baseline else "multi-catfish-mcrl-short-ep"
        ),
        training_experiment_id=arm,
        method_family=(
            "MODQN-baseline" if baseline else "Multi-Catfish-MCRL-developmental"
        ),
        phase="developmental-short-ep",
        comparison_role=ARM_LABELS[arm],
        reward_calibration_enabled=True,
        reward_calibration_scales=_frozen_reward_scales(record),
        device="cpu",
    )


def _valid_digest(value: Any) -> bool:
    return bool(
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def load_gate_ledger(path: Path | None) -> tuple[GateLedger, dict[str, Any]]:
    """Load three independent verdicts; missing authority fails closed."""

    if path is None:
        return GateLedger(), {
            "schema": GATE_SCHEMA,
            "status": "absent-fail-closed",
            "verdicts": {source: "shadow" for source in ("C1", "C2", "C3")},
        }
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != GATE_SCHEMA:
        raise RuntimeError("consumer gate manifest has the wrong schema")
    verdicts = payload.get("verdicts")
    evidence = payload.get("evidence")
    if not isinstance(verdicts, Mapping) or not isinstance(evidence, Mapping):
        raise RuntimeError("consumer gate manifest is incomplete")
    values: dict[str, str] = {}
    for source in ("C1", "C2", "C3"):
        verdict = verdicts.get(source)
        if verdict not in {"route", "shadow"}:
            raise RuntimeError(f"invalid {source} gate verdict")
        values[source] = str(verdict)
        if verdict == "route":
            receipt = evidence.get(source)
            if (
                not isinstance(receipt, Mapping)
                or receipt.get("status") != "PASS"
                or not _valid_digest(receipt.get("receipt_sha256"))
            ):
                raise RuntimeError(f"{source} route verdict lacks sealed PASS evidence")
            raw_receipt_path = receipt.get("receipt_path")
            if not isinstance(raw_receipt_path, str) or not raw_receipt_path:
                raise RuntimeError(f"{source} route verdict lacks a receipt path")
            receipt_path = Path(raw_receipt_path).expanduser()
            if not receipt_path.is_absolute():
                receipt_path = Path(path).resolve().parent / receipt_path
            receipt_path = receipt_path.resolve()
            if (
                not receipt_path.is_file()
                or sha256_file(receipt_path) != receipt.get("receipt_sha256")
            ):
                raise RuntimeError(f"{source} gate receipt is missing or hash-drifted")
            receipt_payload = json.loads(receipt_path.read_text(encoding="utf-8"))
            expected_schema = (
                C1_PRETRANSFER_GATE_RESULT_SCHEMA
                if source == "C1"
                else GATE_RESULT_SCHEMA
            )
            if (
                not isinstance(receipt_payload, Mapping)
                or receipt_payload.get("schema") != expected_schema
                or receipt_payload.get("source") != source
                or receipt_payload.get("status") != "PASS"
                or receipt_payload.get("decision") != "ROUTE"
                or receipt_payload.get("prerequisites_closed") is not True
            ):
                raise RuntimeError(f"{source} gate receipt does not authorize routing")
            try:
                if source == "C1":
                    validate_c1_pretransfer_result(receipt_path)
                else:
                    validate_main_consumer_result(
                        receipt_path,
                        expected_source=source,
                    )
            except (
                C1PretransferGateValidationError,
                GateReceiptValidationError,
            ) as exc:
                raise RuntimeError(
                    f"{source} gate receipt failed independent validation: {exc}"
                ) from exc
    ledger = GateLedger(**values)
    return ledger, payload


def load_intermediate_trend_authority(
    path: Path,
    *,
    arm: str,
    episodes: int,
    users: int,
    train_seed: int,
    env_seed: int,
    mobility_seed: int,
    epsilon_decay_episodes: int,
    target_update_every: int,
    checkpoint_every: int,
    learning_rate: float,
    acrm_eta: float,
    prereg: Path,
    tle_root: Path,
    c1_exp_corpus_manifest: Path | None,
) -> tuple[GateLedger, dict[str, Any]]:
    """Validate one predeclared 1500/3000 trend-screen arm."""

    authority_path = Path(path).expanduser().resolve()
    try:
        request = json.loads(authority_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError("intermediate trend authority is unreadable") from error
    validated = validate_intermediate_trend_authority(
        request,
        tle_root=Path(tle_root).expanduser().resolve(),
    )
    if arm not in validated["arms"]:
        raise RuntimeError("arm is outside intermediate trend authority")
    if (
        validated["episodes"] != int(episodes)
        or not math.isclose(
            float(validated["learning_rate"]),
            float(learning_rate),
            rel_tol=0.0,
            abs_tol=1e-15,
        )
    ):
        raise RuntimeError("runner configuration drifted from trend authority")
    seeds = validated["seeds"]
    if (
        seeds["training"] != int(train_seed)
        or seeds["environment"] != int(env_seed)
        or seeds["mobility"] != int(mobility_seed)
    ):
        raise RuntimeError("runner seeds drifted from trend authority")
    config = validated["config"]
    if (
        config["users"] != int(users)
        or config["epsilon_decay_episodes"] != int(epsilon_decay_episodes)
        or config["target_update_every"] != int(target_update_every)
        or config["checkpoint_every_episodes"] != int(checkpoint_every)
        or config["specialist_bundle_replay_capacity"]
        != SPECIALIST_BUNDLE_REPLAY_CAPACITY
        or not math.isclose(
            float(config["acrm_eta"]),
            float(acrm_eta),
            rel_tol=0.0,
            abs_tol=1e-15,
        )
    ):
        raise RuntimeError("runner schedule drifted from trend authority")
    if Path(prereg).expanduser().resolve() != Path(
        validated["authority"]["canonical_prereg"]
    ).resolve():
        raise RuntimeError("runner preregistration drifted from trend authority")
    if arm != "B000":
        if c1_exp_corpus_manifest is None or Path(
            c1_exp_corpus_manifest
        ).expanduser().resolve() != Path(
            validated["authority"]["c1_exp_corpus_manifest"]
        ).resolve():
            raise RuntimeError("runner C1 corpus drifted from trend authority")

    gates = (
        GateLedger()
        if arm == "B000"
        else GateLedger(
            **{
                source: (
                    "route" if source in ARM_ACTIVE_SOURCES[arm] else "shadow"
                )
                for source in ("C1", "C2", "C3")
            }
        )
    )
    return gates, {
        "schema": validated["schema"],
        "status": "AUTHORIZED_FOR_BOUNDED_INTERMEDIATE_TREND",
        "authority_manifest": str(authority_path),
        "authority_manifest_sha256": sha256_file(authority_path),
        "validated": validated,
        "active_sources": sorted(ARM_ACTIVE_SOURCES.get(arm, ())),
        "formal_training_authorized": False,
    }


def _mask_block(masks: Sequence[Any]) -> np.ndarray:
    return np.stack([np.asarray(row.mask, dtype=bool) for row in masks])


def _assert_single_focal_override(
    main_actions: Sequence[int],
    role_actions: Sequence[int],
    focal_user: int | None,
) -> dict[str, Any]:
    """Fail closed unless a focal specialist changes at most its own row."""

    main = np.asarray(main_actions, dtype=np.int64)
    role = np.asarray(role_actions, dtype=np.int64)
    if main.ndim != 1 or role.shape != main.shape:
        raise RuntimeError("role and frozen-Main joint actions disagree in shape")
    differing = np.flatnonzero(main != role)
    if focal_user is None:
        if differing.size:
            raise RuntimeError("a role without focal authority changed Main actions")
        focal: int | None = None
    else:
        focal = int(focal_user)
        if not 0 <= focal < main.size:
            raise RuntimeError("role focal user is outside the joint action")
        if any(int(uid) != focal for uid in differing):
            raise RuntimeError("role changed a nonfocal frozen-Main action")
    return {
        "focal_user": focal,
        "differing_users": [int(uid) for uid in differing],
        "difference_count": int(differing.size),
        "maximum_allowed_differences": 1,
        "nonfocal_identity": True,
        "main_actions_sha256": hashlib.sha256(
            main.tobytes(order="C")
        ).hexdigest(),
        "executed_actions_sha256": hashlib.sha256(
            role.tobytes(order="C")
        ).hexdigest(),
    }


def _bundle(
    *,
    arm: str,
    train_seed: int,
    source: str,
    policy_version: int,
    episode: int,
    step_index: int,
    encoded: np.ndarray,
    actions: np.ndarray,
    outcome: Any,
    next_encoded: np.ndarray,
    masks: Sequence[Any],
    next_masks: Sequence[Any],
    focal_user: int | None,
    specialist_rewards: np.ndarray | None,
    probabilities: np.ndarray,
    provenance: Mapping[str, Any],
) -> AtomicBundle:
    return AtomicBundle(
        bundle_id=(
            f"{arm}-seed{int(train_seed)}-ep{int(episode):03d}-"
            f"step{int(step_index):02d}-{source}"
        ),
        source_id=source,
        source_policy_version=int(policy_version),
        block_id=int(episode),
        step_index=int(step_index),
        states=encoded,
        actions=actions,
        rewards=outcome.reward_matrix,
        next_states=next_encoded,
        masks=_mask_block(masks),
        next_masks=_mask_block(next_masks),
        done=bool(outcome.done),
        focal_user=focal_user,
        specialist_rewards=specialist_rewards,
        behavior_probabilities=probabilities,
        provenance=dict(provenance),
    )


def _admit_main_rows_exactly_as_baseline(
    main: MODQNTrainer,
    bundle: AtomicBundle,
) -> None:
    """Mirror canonical Main replay admission for zero-dose parity.

    Main-origin experience keeps the unchanged row replay and random batch
    update.  Specialist-origin experience, if separately gate-authorised, is
    applied afterwards as complete atomic bundles.  With zero routed
    specialists this reduces exactly to the baseline training loop.
    """

    for uid in range(bundle.users):
        main._decision_steps_seen += 1
        action = int(bundle.actions[uid])
        if is_no_op(action):
            main._no_op_transitions_skipped += 1
            continue
        next_mask = bundle.next_masks[uid]
        if not bundle.done and not bool(next_mask.any()):
            main._all_invalid_next_transitions_skipped += 1
            continue
        reward_train = apply_reward_calibration(bundle.rewards[uid], main.config)
        main.replay.push(
            bundle.states[uid],
            action,
            reward_train.astype(np.float32),
            bundle.next_states[uid],
            bundle.masks[uid].copy(),
            next_mask.copy(),
            bundle.done,
        )
        main._emit_runtime_real_emission_hook("transition_stored")


def _incumbent_keys(environment: TrainerEnvironment) -> tuple[Any, ...]:
    keys: list[tuple[int, int] | None] = []
    for association in environment.environment._previous_association:
        if isinstance(association, Association):
            keys.append((int(association.norad_id), int(association.cell_id)))
        else:
            keys.append(None)
    return tuple(keys)


def _update_stats(
    stats: dict[str, Any],
    *,
    source: str,
    outcome: Any,
    trigger: str,
    support_size: int,
    routed: bool,
    specialist_loss: float | None,
) -> None:
    row = stats[source]
    row["steps_observed"] += 1
    row["routed_bundles"] += int(routed)
    row["support_actions"] += int(support_size)
    row["trigger_counts"][trigger] += 1
    row["reward_sum"] += outcome.reward_matrix.sum(axis=0)
    row["useful_bits"] += float(outcome.energy.system_throughput_bps) * DECISION_STEP_S
    row["energy_j"] += float(outcome.energy.system_consumed_power_w) * DECISION_STEP_S
    row["served_user_intervals"] += int(outcome.resolution.served_count)
    row["user_intervals"] += int(outcome.resolution.served.size)
    if specialist_loss is not None:
        row["specialist_updates"] += int(specialist_loss > 0.0)
        row["specialist_loss_sum"] += float(specialist_loss)


def _empty_stats() -> dict[str, Any]:
    return {
        source: {
            "steps_observed": 0,
            "routed_bundles": 0,
            "support_actions": 0,
            "trigger_counts": Counter(),
            "reward_sum": np.zeros(3, dtype=np.float64),
            "useful_bits": 0.0,
            "energy_j": 0.0,
            "served_user_intervals": 0,
            "user_intervals": 0,
            "specialist_updates": 0,
            "specialist_loss_sum": 0.0,
        }
        for source in SOURCE_ORDER
    }


def _serialise_stats(stats: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for source, row in stats.items():
        energy = float(row["energy_j"])
        payload[source] = {
            "steps_observed": int(row["steps_observed"]),
            "routed_bundles": int(row["routed_bundles"]),
            "support_actions": int(row["support_actions"]),
            "trigger_counts": dict(row["trigger_counts"]),
            "reward_sum": np.asarray(row["reward_sum"], dtype=float).tolist(),
            "useful_bits": float(row["useful_bits"]),
            "energy_j": energy,
            "ratio_of_sums_ee_bits_per_j": (
                float(row["useful_bits"]) / energy if energy > 0.0 else 0.0
            ),
            "served_fraction": (
                float(row["served_user_intervals"]) / int(row["user_intervals"])
                if row["user_intervals"]
                else 0.0
            ),
            "specialist_updates": int(row["specialist_updates"]),
            "mean_specialist_loss": (
                float(row["specialist_loss_sum"]) / int(row["specialist_updates"])
                if row["specialist_updates"]
                else 0.0
            ),
        }
    return payload


def _prefill_c1(
    *,
    specialist: ObjectiveSpecialist,
    replay: BundleReplay,
    informed: bool,
    corpus: VerifiedC1Corpus,
) -> dict[str, Any]:
    reward_sum = np.zeros(3, dtype=np.float64)
    losses: list[float] = []
    bundles: list[str] = []
    matched_contexts: list[list[int]] = []
    sampled_bundles: list[str] = []
    selected = corpus.prefill_bundles(informed=informed)
    for bundle in selected:
        replay.push(bundle)
        loss, sampled = specialist.update_from_replay(replay)
        losses.append(float(loss))
        bundles.append(bundle.bundle_id)
        matched_contexts.append(list(bundle.provenance["matched_context"]))
        sampled_bundles.extend(sampled)
        reward_sum += bundle.rewards.sum(axis=0)
    return {
        "generator": "local_snr_greedy" if informed else "masked_uniform",
        "corpus_branch": "local" if informed else "control",
        "corpus_manifest": str(corpus.manifest_path),
        "corpus_manifest_sha256": corpus.manifest_sha256,
        "corpus_sha256": corpus.corpus_sha256,
        "selection": "paired_high_mid_context_intersection",
        "bundles": len(bundles),
        "bundle_ids": bundles,
        "matched_contexts": matched_contexts,
        "sampled_bundle_ids": sampled_bundles,
        "reward_sum": reward_sum.tolist(),
        "mean_specialist_loss": float(np.mean(losses)) if losses else 0.0,
        "enters_main": False,
    }


def _save_carrier_state(
    path: Path,
    *,
    main: MODQNTrainer,
    specialists: Mapping[str, ObjectiveSpecialist],
    replays: Mapping[str, BundleReplay],
    gates: GateLedger,
    trajectories: Mapping[str, Trajectory],
    consumed_ledger: ConsumedBundleLedger,
    episodes_completed: int,
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save(
        {
            "schema": "smc-er-carrier-state-v1",
            "episodes_completed": int(episodes_completed),
            "main_training_state": main.training_state_dict(),
            "specialists": {
                source: specialist.state_dict()
                for source, specialist in specialists.items()
            },
            "bundle_replays": {
                source: replay.state_dict() for source, replay in replays.items()
            },
            "main_consumed_specialist_bundles": consumed_ledger.state_dict(),
            "gates": asdict(gates),
            "source_rng_states": {
                source: {
                    "environment": copy.deepcopy(trajectory.env_rng.bit_generator.state),
                    "mobility": copy.deepcopy(
                        trajectory.mobility_rng.bit_generator.state
                    ),
                }
                for source, trajectory in trajectories.items()
            },
        },
        temporary,
    )
    temporary.replace(path)


def _save_training_state(path: Path, state: Mapping[str, Any]) -> None:
    """Atomically replace the rolling exact-resume state."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save(dict(state), temporary)
    temporary.replace(path)


def _save_periodic_main_checkpoint(
    *,
    trainer: MODQNTrainer,
    output_dir: Path,
    episodes_completed: int,
    logs: Sequence[Any] | None = None,
) -> dict[str, Any]:
    """Persist and immediately reload one Main-only policy trend snapshot."""

    if episodes_completed < 1:
        raise ValueError("episodes_completed must be positive")
    checkpoint = (
        Path(output_dir)
        / "checkpoints"
        / f"ep-{int(episodes_completed):06d}-main.pt"
    )
    trainer.save_checkpoint(
        checkpoint,
        episode=int(episodes_completed) - 1,
        checkpoint_kind="periodic-main-policy-trend",
        logs=list(logs) if logs is not None else None,
        include_optimizers=True,
    )
    payload = read_checkpoint(checkpoint, map_location="cpu")
    if payload.episode != int(episodes_completed) - 1:
        raise RuntimeError("periodic checkpoint episode failed round-trip")
    if payload.checkpoint_kind != "periodic-main-policy-trend":
        raise RuntimeError("periodic checkpoint kind failed round-trip")
    return {
        "episodes_completed": int(episodes_completed),
        "episode_index": int(payload.episode),
        "path": str(checkpoint),
        "sha256": sha256_file(checkpoint),
        "checkpoint_kind": payload.checkpoint_kind,
        "load_round_trip": "PASS",
    }


def run_baseline(
    *,
    output_dir: Path,
    archive: TleArchive,
    config: TrainerConfig,
    users: int,
    train_seed: int,
    env_seed: int,
    mobility_seed: int,
    checkpoint_every: int,
) -> dict[str, Any]:
    environment = _make_environment(archive, users=users)
    trainer = MODQNTrainer(
        environment,
        config,
        train_seed=train_seed,
        env_seed=env_seed,
        mobility_seed=mobility_seed,
        device="cpu",
    )
    periodic_checkpoints: list[dict[str, Any]] = []
    observed_logs: list[Any] = []
    rolling_state = output_dir / "resume" / "latest-training-state.pt"

    def checkpoint_callback(log: Any) -> None:
        observed_logs.append(log)
        episodes_completed = int(log.episode) + 1
        if episodes_completed % int(checkpoint_every) != 0:
            return
        periodic_checkpoints.append(
            _save_periodic_main_checkpoint(
                trainer=trainer,
                output_dir=output_dir,
                episodes_completed=episodes_completed,
                logs=observed_logs,
            )
        )
        _save_training_state(rolling_state, trainer.training_state_dict())

    logs = trainer.train(progress_every=1, episode_callback=checkpoint_callback)
    checkpoint = output_dir / "final-checkpoint.pt"
    trainer.save_checkpoint(
        checkpoint,
        episode=config.episodes - 1,
        checkpoint_kind="final-episode-policy",
        logs=logs,
        include_optimizers=True,
    )
    training_state = output_dir / "training-state.pt"
    _save_training_state(training_state, trainer.training_state_dict())
    _write_json(output_dir / "episode-logs.json", [asdict(row) for row in logs])
    return {
        "dispatch": "unchanged_MODQNTrainer.train",
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": sha256_file(checkpoint),
        "training_state": str(training_state),
        "training_state_sha256": sha256_file(training_state),
        "episodes": len(logs),
        "checkpoint_every_episodes": int(checkpoint_every),
        "periodic_checkpoints": periodic_checkpoints,
        "periodic_checkpoint_count": len(periodic_checkpoints),
        "rolling_resume_state": (
            {
                "episodes_completed": int(periodic_checkpoints[-1]["episodes_completed"]),
                "path": str(rolling_state),
                "sha256": sha256_file(rolling_state),
            }
            if periodic_checkpoints
            else None
        ),
        "masking_diagnostics": trainer.get_masking_diagnostics(),
    }


def run_treatment(
    *,
    arm: str,
    output_dir: Path,
    archive: TleArchive,
    config: TrainerConfig,
    users: int,
    train_seed: int,
    env_seed: int,
    mobility_seed: int,
    gates: GateLedger,
    acrm_eta: float,
    c1_corpus_manifest: Path,
    checkpoint_every: int,
) -> dict[str, Any]:
    lanes = ARM_LANES[arm]
    if lanes is None:
        raise ValueError("baseline is not a treatment arm")
    c1_informed, c2_informed, c3_informed = lanes
    active_sources = ARM_ACTIVE_SOURCES[arm]

    main_environment = _make_environment(archive, users=users)
    main = MODQNTrainer(
        main_environment,
        config,
        train_seed=train_seed,
        env_seed=env_seed,
        mobility_seed=mobility_seed,
        device="cpu",
    )
    c1_corpus = load_verified_c1_corpus(
        c1_corpus_manifest,
        expected_state_dim=main.state_dim,
        expected_action_dim=main.action_dim,
        tle_root=archive.root,
    )
    trajectories = {
        "Main": Trajectory(
            main_environment,
            main._env_rng,
            main._mobility_rng,
        )
    }
    for source in ("C1", "C2", "C3"):
        trajectories[source] = Trajectory(
            _make_environment(archive, users=users),
            np.random.default_rng(env_seed),
            np.random.default_rng(mobility_seed),
        )

    specialists = {
        "C1": ObjectiveSpecialist(
            objective_index=0,
            state_dim=main.state_dim,
            action_dim=main.action_dim,
            config=config,
            seed=train_seed + 10_001,
        ),
        "C2": ObjectiveSpecialist(
            objective_index=1,
            state_dim=main.state_dim,
            action_dim=main.action_dim,
            config=config,
            seed=train_seed + 20_003,
        ),
        "C3": ObjectiveSpecialist(
            objective_index=2,
            state_dim=main.state_dim,
            action_dim=main.action_dim,
            config=config,
            seed=train_seed + 30_007,
        ),
    }
    # Canonical Main learning already owns its row replay.  Specialist replay
    # is measured in complete U-user bundles, so reusing the 50k row capacity
    # would retain several GB per role.  Keep a separately frozen 2k-bundle
    # FIFO (roughly the most recent 200 ten-step episodes).
    replays = {
        source: BundleReplay(SPECIALIST_BUNDLE_REPLAY_CAPACITY)
        for source in ("C1", "C2", "C3")
    }
    consumed_ledger = ConsumedBundleLedger()
    prefill = _prefill_c1(
        specialist=specialists["C1"],
        replay=replays["C1"],
        informed=c1_informed,
        corpus=c1_corpus,
    )

    stats = _empty_stats()
    main_losses: list[dict[str, Any]] = []
    specialist_replay_receipts: list[dict[str, Any]] = []
    eligibility_receipts: list[dict[str, Any]] = []
    episode_rows: list[dict[str, Any]] = []
    periodic_checkpoints: list[dict[str, Any]] = []
    rolling_carrier_state = output_dir / "resume" / "latest-carrier-state.pt"

    for episode in range(config.episodes):
        epsilon = main.epsilon(episode)
        frozen_main = FrozenMainComparator.from_main(main)
        for trajectory in trajectories.values():
            trajectory.reset()
        c2_option = OptionCommitment()
        c3_option = OptionCommitment()
        episode_reward = np.zeros(3, dtype=np.float64)

        for step_index in range(main_environment.config.steps_per_episode):
            block_bundles: dict[str, AtomicBundle] = {}

            # Main source: unchanged scalarized epsilon-greedy behaviour.
            main_traj = trajectories["Main"]
            assert main_traj.states is not None and main_traj.masks is not None
            main_encoded = main.encode_states(main_traj.states)
            main_actions = main.select_actions(
                main_encoded,
                main_traj.masks,
                epsilon,
                raw_states=main_traj.states,
            )
            main_probabilities = epsilon_greedy_probabilities(
                main,
                main_encoded,
                main_traj.masks,
                main_actions,
                epsilon=epsilon,
            )
            # Canonical training samples greedy collapse diagnostics at both
            # episode ends through `_select_unconstrained_actions(..., 0.0)`.
            # That helper still consumes one Main RNG draw per user.  Mirror
            # the read exactly or a zero-specialist carrier diverges from the
            # baseline action stream after the first decision.
            if step_index in {
                0,
                main_environment.config.steps_per_episode - 1,
            }:
                scalarized_for_parity = main._scalarize_q_values(
                    main._predict_objective_q_values(main_encoded),
                    config.objective_weights,
                )
                main._select_unconstrained_actions(
                    scalarized_for_parity,
                    main_traj.masks,
                    0.0,
                )
            main_result = main_traj.environment.step(
                main_actions, main_traj.env_rng
            )
            main_outcome = main_traj.environment.last_outcome
            main_next = main.encode_states(main_result.user_states)
            main_bundle = _bundle(
                arm=arm,
                train_seed=train_seed,
                source="Main",
                policy_version=episode // config.target_update_every_episodes,
                episode=episode,
                step_index=step_index,
                encoded=main_encoded,
                actions=main_actions,
                outcome=main_outcome,
                next_encoded=main_next,
                masks=main_traj.masks,
                next_masks=main_result.action_masks,
                focal_user=None,
                specialist_rewards=None,
                probabilities=main_probabilities,
                provenance={"behavior": "Main_scalarized_epsilon_greedy"},
            )
            block_bundles["Main"] = main_bundle
            _admit_main_rows_exactly_as_baseline(main, main_bundle)
            _update_stats(
                stats,
                source="Main",
                outcome=main_outcome,
                trigger="scheduled",
                support_size=int(_mask_block(main_traj.masks).sum()),
                routed=True,
                specialist_loss=None,
            )
            episode_reward += main_outcome.reward_matrix.sum(axis=0)
            main_traj.advance(main_result)

            # C1 source and private ACRM comparator.
            c1_traj = trajectories["C1"]
            assert c1_traj.states is not None and c1_traj.masks is not None
            c1_encoded = main.encode_states(c1_traj.states)
            comparator_actions = main_greedy_actions(
                frozen_main, c1_encoded, c1_traj.masks
            )
            c1_actions, c1_probabilities = specialist_joint_actions(
                specialists["C1"],
                c1_encoded,
                c1_traj.masks,
                epsilon=epsilon,
                informed=c1_informed,
            )
            comparator = c1_traj.environment.environment.evaluate_actions(
                comparator_actions, c1_traj.env_rng
            )
            c1_result = c1_traj.environment.step(c1_actions, c1_traj.env_rng)
            c1_outcome = c1_traj.environment.last_outcome
            c1_next = main.encode_states(c1_result.user_states)
            c1_private = (
                acrm_rewards(
                    c1_outcome.reward_matrix[:, 0],
                    comparator.reward_matrix[:, 0],
                    eta=acrm_eta,
                )
                if c1_informed
                else c1_outcome.reward_matrix[:, 0].copy()
            )
            c1_bundle = _bundle(
                arm=arm,
                train_seed=train_seed,
                source="C1",
                policy_version=specialists["C1"].policy_version,
                episode=episode,
                step_index=step_index,
                encoded=c1_encoded,
                actions=c1_actions,
                outcome=c1_outcome,
                next_encoded=c1_next,
                masks=c1_traj.masks,
                next_masks=c1_result.action_masks,
                focal_user=None,
                specialist_rewards=c1_private,
                probabilities=c1_probabilities,
                provenance={
                    "behavior": "Q1_specialist" if c1_informed else "uniform_control",
                    "acrm_enabled": bool(c1_informed),
                    "acrm_eta": float(acrm_eta) if c1_informed else 0.0,
                    "main_counterfactual_selected_before_outcome": True,
                    "frozen_main_comparator_sha256": frozen_main.version_sha256,
                    "comparator_block": episode,
                },
            )
            replays["C1"].push(c1_bundle)
            c1_loss, c1_sampled = specialists["C1"].update_from_replay(
                replays["C1"]
            )
            specialist_replay_receipts.append(
                {
                    "episode": episode,
                    "step": step_index,
                    "source": "C1",
                    "collected_bundle_id": c1_bundle.bundle_id,
                    "sampled_bundle_ids": list(c1_sampled),
                    "frozen_main_comparator_sha256": frozen_main.version_sha256,
                    "comparator_block": episode,
                }
            )
            block_bundles["C1"] = c1_bundle
            _update_stats(
                stats,
                source="C1",
                outcome=c1_outcome,
                trigger="scheduled_informed" if c1_informed else "scheduled_control",
                support_size=int(_mask_block(c1_traj.masks).sum()),
                routed=(gates.routes("C1") and "C1" in active_sources),
                specialist_loss=c1_loss,
            )
            c1_traj.advance(c1_result)

            # C2 focal persistence option.
            c2_traj = trajectories["C2"]
            assert (
                c2_traj.states is not None
                and c2_traj.masks is not None
                and c2_traj.observation is not None
            )
            c2_encoded = main.encode_states(c2_traj.states)
            c2_main_actions = main_greedy_actions(
                frozen_main, c2_encoded, c2_traj.masks
            )
            c2_incumbents = _incumbent_keys(c2_traj.environment)
            c2_supports = (
                {}
                if c2_option.open
                else observable_c2_supports(
                    states=c2_traj.states,
                    main_actions=c2_main_actions,
                    slot_tables=c2_traj.observation.candidates.slot_tables,
                    incumbents=c2_incumbents,
                )
            )
            c2_decision = c2_observable_decision(
                specialist=specialists["C2"],
                encoded=c2_encoded,
                main_actions=c2_main_actions,
                slot_tables=c2_traj.observation.candidates.slot_tables,
                eligible_supports=c2_supports,
                commitment=c2_option,
                epsilon=epsilon,
                informed=c2_informed,
                step_index=step_index,
            )
            c2_identity = _assert_single_focal_override(
                c2_main_actions,
                c2_decision.actions,
                c2_decision.focal_user,
            )
            c2_result = c2_traj.environment.step(
                c2_decision.actions, c2_traj.env_rng
            )
            c2_outcome = c2_traj.environment.last_outcome
            c2_next = main.encode_states(c2_result.user_states)
            c2_termination = None
            if c2_decision.focal_user is not None:
                c2_termination = advance_option_after_execution(
                    c2_option,
                    focal_served=bool(
                        c2_outcome.resolution.served[c2_decision.focal_user]
                    ),
                    done=bool(c2_result.done),
                )
            c2_bundle = _bundle(
                arm=arm,
                train_seed=train_seed,
                source="C2",
                policy_version=specialists["C2"].policy_version,
                episode=episode,
                step_index=step_index,
                encoded=c2_encoded,
                actions=c2_decision.actions,
                outcome=c2_outcome,
                next_encoded=c2_next,
                masks=c2_traj.masks,
                next_masks=c2_result.action_masks,
                focal_user=c2_decision.focal_user,
                specialist_rewards=None,
                probabilities=c2_decision.probabilities,
                provenance={
                    "behavior": "Q2_option" if c2_informed else "uniform_option_control",
                    "trigger": c2_decision.trigger,
                    "selected_key": c2_decision.selected_key,
                    "support_actions": c2_decision.support_actions,
                    "selection_termination": c2_decision.termination,
                    "post_execution_termination": c2_termination,
                    "support_version": ROLE_SUPPORT_VERSION,
                    "support_rule": (
                        "Main cold-beam activation onset; incumbent plus "
                        "state-visible warm alternatives"
                    ),
                    "future_outcome_used_for_admission": False,
                    "counterfactual_certificate_used_for_admission": False,
                    "focal_override_identity": c2_identity,
                    "frozen_main_comparator_sha256": frozen_main.version_sha256,
                    "comparator_block": episode,
                },
            )
            c2_loss: float | None = None
            c2_sampled: tuple[str, ...] = ()
            if c2_decision.focal_user is not None:
                replays["C2"].push(c2_bundle)
                c2_loss, c2_sampled = specialists["C2"].update_from_replay(
                    replays["C2"]
                )
                block_bundles["C2"] = c2_bundle
            specialist_replay_receipts.append(
                {
                    "episode": episode,
                    "step": step_index,
                    "source": "C2",
                    "collected_bundle_id": (
                        c2_bundle.bundle_id
                        if c2_decision.focal_user is not None
                        else None
                    ),
                    "sampled_bundle_ids": list(c2_sampled),
                    "shortage": c2_decision.focal_user is None,
                    "focal_override_identity": c2_identity,
                }
            )
            _update_stats(
                stats,
                source="C2",
                outcome=c2_outcome,
                trigger=c2_decision.trigger,
                support_size=len(c2_decision.support_actions),
                routed=(
                    gates.routes("C2")
                    and "C2" in active_sources
                    and c2_decision.focal_user is not None
                ),
                specialist_loss=c2_loss,
            )
            eligibility_receipts.append(
                {
                    "episode": episode,
                    "step": step_index,
                    "source": "C2",
                    "support_version": ROLE_SUPPORT_VERSION,
                    "trigger": c2_decision.trigger,
                    "focal_user": c2_decision.focal_user,
                    "support_actions": list(c2_decision.support_actions),
                    "selected_key": c2_decision.selected_key,
                    "eligible_supports": {
                        str(uid): list(support)
                        for uid, support in sorted(c2_supports.items())
                    },
                    "future_outcome_used_for_admission": False,
                    "focal_override_identity": c2_identity,
                }
            )
            c2_traj.advance(c2_result)

            # C3 H=3 observable load-relocation option.
            c3_traj = trajectories["C3"]
            assert (
                c3_traj.states is not None
                and c3_traj.masks is not None
                and c3_traj.observation is not None
            )
            c3_encoded = main.encode_states(c3_traj.states)
            c3_main_actions = main_greedy_actions(
                frozen_main, c3_encoded, c3_traj.masks
            )
            c3_incumbents = _incumbent_keys(c3_traj.environment)
            c3_supports = (
                {}
                if c3_option.open
                else observable_c3_supports(
                    states=c3_traj.states,
                    main_actions=c3_main_actions,
                    slot_tables=c3_traj.observation.candidates.slot_tables,
                    incumbents=c3_incumbents,
                )
            )
            c3_decision = c3_relocation_decision(
                specialist=specialists["C3"],
                encoded=c3_encoded,
                main_actions=c3_main_actions,
                slot_tables=c3_traj.observation.candidates.slot_tables,
                eligible_supports=c3_supports,
                commitment=c3_option,
                epsilon=epsilon,
                informed=c3_informed,
                step_index=step_index,
            )
            c3_identity = _assert_single_focal_override(
                c3_main_actions,
                c3_decision.actions,
                c3_decision.focal_user,
            )
            c3_result = c3_traj.environment.step(
                c3_decision.actions, c3_traj.env_rng
            )
            c3_outcome = c3_traj.environment.last_outcome
            c3_next = main.encode_states(c3_result.user_states)
            c3_termination = None
            if c3_decision.focal_user is not None:
                c3_termination = advance_option_after_execution(
                    c3_option,
                    focal_served=bool(
                        c3_outcome.resolution.served[c3_decision.focal_user]
                    ),
                    done=bool(c3_result.done),
                )
            c3_bundle = _bundle(
                arm=arm,
                train_seed=train_seed,
                source="C3",
                policy_version=specialists["C3"].policy_version,
                episode=episode,
                step_index=step_index,
                encoded=c3_encoded,
                actions=c3_decision.actions,
                outcome=c3_outcome,
                next_encoded=c3_next,
                masks=c3_traj.masks,
                next_masks=c3_result.action_masks,
                focal_user=c3_decision.focal_user,
                specialist_rewards=None,
                probabilities=c3_decision.probabilities,
                provenance={
                    "behavior": "Q3_relocation" if c3_informed else "uniform_relocation_control",
                    "trigger": c3_decision.trigger,
                    "selected_key": c3_decision.selected_key,
                    "support_actions": c3_decision.support_actions,
                    "frozen_main_comparator_sha256": frozen_main.version_sha256,
                    "comparator_block": episode,
                    "selection_termination": c3_decision.termination,
                    "post_execution_termination": c3_termination,
                    "support_version": ROLE_SUPPORT_VERSION,
                    "support_rule": (
                        "defer-to-Main plus already-active same-satellite "
                        "destination with lagged ungated-demand gap >= 2"
                    ),
                    "future_outcome_used_for_admission": False,
                    "counterfactual_certificate_used_for_admission": False,
                    "focal_override_identity": c3_identity,
                },
            )
            c3_loss: float | None = None
            c3_sampled: tuple[str, ...] = ()
            if c3_decision.focal_user is not None:
                replays["C3"].push(c3_bundle)
                c3_loss, c3_sampled = specialists["C3"].update_from_replay(
                    replays["C3"]
                )
                block_bundles["C3"] = c3_bundle
            specialist_replay_receipts.append(
                {
                    "episode": episode,
                    "step": step_index,
                    "source": "C3",
                    "collected_bundle_id": (
                        c3_bundle.bundle_id
                        if c3_decision.focal_user is not None
                        else None
                    ),
                    "sampled_bundle_ids": list(c3_sampled),
                    "shortage": c3_decision.focal_user is None,
                    "focal_override_identity": c3_identity,
                }
            )
            _update_stats(
                stats,
                source="C3",
                outcome=c3_outcome,
                trigger=c3_decision.trigger,
                support_size=len(c3_decision.support_actions),
                routed=(
                    gates.routes("C3")
                    and "C3" in active_sources
                    and c3_decision.focal_user is not None
                ),
                specialist_loss=c3_loss,
            )
            eligibility_receipts.append(
                {
                    "episode": episode,
                    "step": step_index,
                    "source": "C3",
                    "support_version": ROLE_SUPPORT_VERSION,
                    "informed": bool(c3_informed),
                    "decision_trigger": c3_decision.trigger,
                    "focal_user": c3_decision.focal_user,
                    "support_actions": list(c3_decision.support_actions),
                    "selected_key": c3_decision.selected_key,
                    "eligible_supports": {
                        str(uid): list(support)
                        for uid, support in sorted(c3_supports.items())
                    },
                    "future_outcome_used_for_admission": False,
                    "focal_override_identity": c3_identity,
                }
            )
            c3_traj.advance(c3_result)

            routed_sources = tuple(
                source
                for source in ("C1", "C2", "C3")
                if gates.routes(source) and source in active_sources
            )
            specialist_routed = [
                block_bundles[source]
                for source in routed_sources
                if source in block_bundles
            ]
            combined_losses, quota_receipt = update_main_with_role_targeted_donors(
                main,
                specialist_routed,
                source_quota=routed_sources,
                beta=0.25,
                consumed_ledger=consumed_ledger,
                consumer_block_id=episode,
            )
            # The updater API permits a caller to resubmit warm-up donors, but
            # this fixed-dose runner deliberately does not.  Record the actual
            # runner disposition so "deferred" cannot be mistaken for a later
            # dose in this experiment.
            quota_receipt["runner_resubmits_deferred_bundles"] = False
            quota_receipt["runner_dropped_after_warmup_bundle_ids"] = list(
                quota_receipt.get("deferred_specialist_bundle_ids", [])
            )
            main_losses.append(
                {
                    "episode": episode,
                    "step": step_index,
                    "main_bundle_id": main_bundle.bundle_id,
                    "losses": list(combined_losses),
                    "quota_receipt": quota_receipt,
                }
            )

        if (episode + 1) % config.target_update_every_episodes == 0:
            main.sync_targets()
            for specialist in specialists.values():
                specialist.sync_target()
        episode_rows.append(
            {
                "episode": episode,
                "epsilon": epsilon,
                "main_source_reward_sum": episode_reward.tolist(),
                "main_update_count": main_environment.config.steps_per_episode,
                "gate_ledger": asdict(gates),
                "frozen_main_comparator_sha256": frozen_main.version_sha256,
            }
        )
        episodes_completed = episode + 1
        if episodes_completed % int(checkpoint_every) == 0:
            periodic_checkpoints.append(
                _save_periodic_main_checkpoint(
                    trainer=main,
                    output_dir=output_dir,
                    episodes_completed=episodes_completed,
                    logs=None,
                )
            )
            _save_carrier_state(
                rolling_carrier_state,
                main=main,
                specialists=specialists,
                replays=replays,
                gates=gates,
                trajectories=trajectories,
                consumed_ledger=consumed_ledger,
                episodes_completed=episodes_completed,
            )
        print(
            f"[{arm} ep {episode + 1:3d}/{config.episodes}] "
            f"epsilon={epsilon:.4f} routes="
            + ",".join(source for source in ("C1", "C2", "C3") if gates.routes(source))
        )

    checkpoint = output_dir / "final-checkpoint.pt"
    main.save_checkpoint(
        checkpoint,
        episode=config.episodes - 1,
        checkpoint_kind="final-episode-policy",
        include_optimizers=True,
    )
    carrier_state = output_dir / "carrier-state.pt"
    _save_carrier_state(
        carrier_state,
        main=main,
        specialists=specialists,
        replays=replays,
        gates=gates,
        trajectories=trajectories,
        consumed_ledger=consumed_ledger,
        episodes_completed=config.episodes,
    )
    _write_json(output_dir / "episode-logs.json", episode_rows)
    _write_json(output_dir / "main-update-receipts.json", main_losses)
    _write_json(
        output_dir / "specialist-replay-receipts.json",
        specialist_replay_receipts,
    )
    _write_json(
        output_dir / "role-eligibility-receipts.json",
        eligibility_receipts,
    )
    return {
        "dispatch": "Multi-Catfish-MCRL_four_independent_trajectories",
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": sha256_file(checkpoint),
        "carrier_state": str(carrier_state),
        "carrier_state_sha256": sha256_file(carrier_state),
        "episodes": config.episodes,
        "specialist_bundle_replay_capacity": SPECIALIST_BUNDLE_REPLAY_CAPACITY,
        "checkpoint_every_episodes": int(checkpoint_every),
        "periodic_checkpoints": periodic_checkpoints,
        "periodic_checkpoint_count": len(periodic_checkpoints),
        "rolling_resume_state": (
            {
                "episodes_completed": int(periodic_checkpoints[-1]["episodes_completed"]),
                "path": str(rolling_carrier_state),
                "sha256": sha256_file(rolling_carrier_state),
            }
            if periodic_checkpoints
            else None
        ),
        "lanes_informed": {
            "C1": bool(c1_informed),
            "C2": bool(c2_informed),
            "C3": bool(c3_informed),
        },
        "gates": asdict(gates),
        "consumed_specialist_bundle_count": len(consumed_ledger),
        "c1_prefill": prefill,
        "source_dashboard": _serialise_stats(stats),
        "role_support_version": ROLE_SUPPORT_VERSION,
        "counterfactual_used_for_runtime_admission": False,
    }


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=tuple(ARM_LANES), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument("--users", type=int, default=100)
    parser.add_argument("--train-seed", type=int, required=True)
    parser.add_argument("--env-seed", type=int, required=True)
    parser.add_argument("--mobility-seed", type=int, required=True)
    parser.add_argument("--epsilon-decay-episodes", type=int)
    parser.add_argument("--target-update-every", type=int)
    parser.add_argument("--checkpoint-every", type=int)
    parser.add_argument("--learning-rate", type=float, default=DEFAULT_LEARNING_RATE)
    parser.add_argument("--acrm-eta", type=float, default=DEFAULT_ACRM_ETA)
    parser.add_argument("--gate-manifest", type=Path)
    parser.add_argument("--intermediate-trend-authority", type=Path)
    parser.add_argument(
        "--development-route-all",
        action="store_true",
        help=(
            "route enabled arm roles for a development-only trend screen; "
            "cannot be combined with a formal gate manifest"
        ),
    )
    parser.add_argument("--c1-exp-corpus-manifest", type=Path)
    parser.add_argument("--prereg", type=Path, default=CANONICAL_PREREG)
    parser.add_argument(
        "--tle-root", type=Path, default=Path(TLE_ROOT_DEFAULT).expanduser()
    )
    args = parser.parse_args(argv)
    if args.episodes < 1 or args.users < 1:
        parser.error("--episodes and --users must be positive")
    if not math.isfinite(args.acrm_eta) or args.acrm_eta < 0.0:
        parser.error("--acrm-eta must be finite and non-negative")
    if args.epsilon_decay_episodes is None:
        args.epsilon_decay_episodes = (
            2000
            if args.intermediate_trend_authority is not None
            else (8 if args.episodes == 10 else max(1, args.episodes - 2))
        )
    if args.target_update_every is None:
        args.target_update_every = (
            50 if args.intermediate_trend_authority is not None else 2
        )
    if args.checkpoint_every is None:
        args.checkpoint_every = (
            TREND_CHECKPOINT_EVERY_EPISODES
            if args.intermediate_trend_authority is not None
            else DEFAULT_CHECKPOINT_EVERY_EPISODES
        )
    if args.target_update_every < 1:
        parser.error("--target-update-every must be positive")
    if args.checkpoint_every < 1:
        parser.error("--checkpoint-every must be positive")
    if args.epsilon_decay_episodes < 1:
        parser.error("--epsilon-decay-episodes must be positive")
    if args.arm == "B000" and args.gate_manifest is not None:
        parser.error("B000 cannot consume a Catfish gate manifest")
    if args.arm == "B000" and args.development_route_all:
        parser.error("B000 cannot route development Catfish sources")
    routing_modes = sum(
        bool(value)
        for value in (
            args.gate_manifest,
            args.development_route_all,
            args.intermediate_trend_authority,
        )
    )
    if routing_modes > 1:
        parser.error(
            "formal, development, and intermediate routing are mutually exclusive"
        )
    if args.development_route_all and args.episodes > DEVELOPMENT_MAX_EPISODES:
        parser.error(
            "development routing is bounded to at most "
            f"{DEVELOPMENT_MAX_EPISODES} episodes; use sealed formal gates "
            "for any larger run"
        )
    if args.arm == "B000" and args.c1_exp_corpus_manifest is not None:
        parser.error("B000 cannot consume a C1 EXP corpus")
    if args.arm != "B000" and args.c1_exp_corpus_manifest is None:
        parser.error("treatment arms require --c1-exp-corpus-manifest")
    if args.arm != "B000" and args.users != EXPECTED_C1_CORPUS_USERS:
        parser.error("the frozen C1 EXP corpus supports exactly 100 training users")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    output_dir = args.output_dir.expanduser().resolve()
    if args.intermediate_trend_authority is not None:
        gates, gate_payload = load_intermediate_trend_authority(
            args.intermediate_trend_authority,
            arm=args.arm,
            episodes=args.episodes,
            users=args.users,
            train_seed=args.train_seed,
            env_seed=args.env_seed,
            mobility_seed=args.mobility_seed,
            epsilon_decay_episodes=args.epsilon_decay_episodes,
            target_update_every=args.target_update_every,
            checkpoint_every=args.checkpoint_every,
            learning_rate=args.learning_rate,
            acrm_eta=args.acrm_eta,
            prereg=args.prereg,
            tle_root=args.tle_root,
            c1_exp_corpus_manifest=args.c1_exp_corpus_manifest,
        )
    elif args.development_route_all:
        gates = GateLedger(C1="route", C2="route", C3="route")
        gate_payload = {
            "schema": "multi-catfish-development-routing-v1",
            "status": "DEVELOPMENT_ONLY_NOT_FORMAL_GATE",
            "claim_ceiling": (
                "short-EP engineering trend only; no scientific efficacy, "
                "formal training, or deployment authorization"
            ),
            "active_sources": sorted(ARM_ACTIVE_SOURCES[args.arm]),
        }
    else:
        gates, gate_payload = load_gate_ledger(args.gate_manifest)
    if args.arm == "B000":
        gates = GateLedger()
    prereg, archive, ephemeris_authority = _canonical_ephemeris_authority(
        args.prereg, args.tle_root
    )
    if args.intermediate_trend_authority is not None and (
        gate_payload["validated"]["authority"]["tle_file_set_sha256"]
        != ephemeris_authority["tle_file_set_sha256"]
    ):
        raise RuntimeError("runtime TLE archive drifted from trend authority")
    output_dir.mkdir(parents=True, exist_ok=False)
    config = _short_config(
        prereg,
        arm=args.arm,
        episodes=args.episodes,
        epsilon_decay_episodes=args.epsilon_decay_episodes,
        target_update_every=args.target_update_every,
        learning_rate=args.learning_rate,
    )
    common = {
        "output_dir": output_dir,
        "archive": archive,
        "config": config,
        "users": args.users,
        "train_seed": args.train_seed,
        "env_seed": args.env_seed,
        "mobility_seed": args.mobility_seed,
        "checkpoint_every": args.checkpoint_every,
    }
    if args.arm == "B000":
        result = run_baseline(**common)
    else:
        result = run_treatment(
            arm=args.arm,
            gates=gates,
            acrm_eta=args.acrm_eta,
            c1_corpus_manifest=args.c1_exp_corpus_manifest.expanduser().resolve(),
            **common,
        )
    status = {
        "schema": SCHEMA,
        "status": "complete",
        "arm": args.arm,
        "label": ARM_LABELS[args.arm],
        "episodes": args.episodes,
        "users": args.users,
        "seeds": {
            "training": args.train_seed,
            "environment": args.env_seed,
            "mobility": args.mobility_seed,
        },
        "config": asdict(config),
        "checkpointing": {
            "every_episodes": int(args.checkpoint_every),
            "trend_snapshots": "all-periodic-Main-only-policy",
            "exact_resume_state": "rolling-latest-only",
            "specialist_bundle_replay_capacity": SPECIALIST_BUNDLE_REPLAY_CAPACITY,
        },
        "gate_manifest": gate_payload,
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "torch": torch.__version__,
        },
        "authority": ephemeris_authority,
        "source_files_sha256": {
            path.name: sha256_file(path)
            for path in (
                HERE / "run_short_ep.py",
                HERE / "smc_er_core.py",
                HERE / "smc_er_roles.py",
                HERE / "c1_exp_corpus.py",
                STAGE0 / "c2_activation_churn_core.py",
                STAGE0 / "c2_activation_churn_runtime_adapter.py",
                STAGE0 / "c2_activation_churn_dev_support.py",
                STAGE0 / "c3_reward_aligned_v3_core.py",
                STAGE0 / "c3_reward_aligned_v3_runtime_adapter.py",
                STAGE0 / "c3_reward_aligned_v3_shadow_runner.py",
                STAGE0 / "c3_reward_aligned_v3_trainer_backend.py",
                HERE / "sweep_evaluation.py",
                HERE / "intermediate_trend_authority.py",
                REPO / "docs" / "MULTI-CATFISH-PAPER-ALGORITHM-V0.4-2026-08-27.md",
                REPO / "docs" / "MULTI-CATFISH-CONCEPT-ALGORITHM-FREEZE-V0.1-2026-08-27.md",
                REPO / "docs" / "THREE-CATFISH-EE-POSITIVE-ACCEPTANCE-CONTRACT-V0.1-2026-08-28.md",
                REPO / "docs" / "CATFISH-V0.2-OBSERVABLE-SUPPORT-SPEC-2026-08-28.md",
                REPO / "docs" / "CATFISH-V0.2-OBSERVABLE-SUPPORT-FREEZE-2026-08-28.json",
                prereg,
            )
        },
        "result": result,
        "claim_ceiling": (
            INTERMEDIATE_TREND_CLAIM_CEILING
            if args.intermediate_trend_authority is not None
            else "ONE-SEED-SHORT-EP-DEVELOPMENTAL-NOT-CHAPTER5"
        ),
    }
    _write_json(output_dir / "status.json", status)
    print(output_dir / "status.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
