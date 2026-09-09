"""Typed checkpoint payloads."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Sequence

from ..errors import MCRLContractError

CHECKPOINT_FORMAT_VERSION: int = 1
"""The only format this project writes, and the only one it will read."""


def _copy_mapping(value: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(dict(value))


def _copy_sequence(value: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    return [copy.deepcopy(dict(entry)) for entry in value]


@dataclass(frozen=True)
class CheckpointRuleV1:
    """Which checkpoint a run reports, and whether the secondary one exists.

    ASSUME-MODQN-REP-015.  ``secondary_implemented`` is the honest half: a
    run without an evaluation seed set has no best-eval checkpoint, and
    saying so beats writing a file that silently duplicates the final one.
    """

    assumption_id: str
    primary_report: str
    secondary_report: str
    secondary_implemented: bool
    secondary_status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "assumption_id": self.assumption_id,
            "primary_report": self.primary_report,
            "secondary_report": self.secondary_report,
            "secondary_implemented": bool(self.secondary_implemented),
            "secondary_status": self.secondary_status,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> CheckpointRuleV1:
        return cls(
            assumption_id=str(payload["assumption_id"]),
            primary_report=str(payload["primary_report"]),
            secondary_report=str(payload["secondary_report"]),
            secondary_implemented=bool(payload["secondary_implemented"]),
            secondary_status=str(payload["secondary_status"]),
        )


@dataclass(frozen=True)
class CheckpointPayloadV1:
    """Everything needed to reconstruct a trained policy and say where it came from.

    The three seeds and the full ``trainer_config`` travel with the weights on
    purpose: a checkpoint whose provenance has to be reconstructed from a
    directory name is not reproducible.
    """

    format_version: int
    checkpoint_kind: str
    episode: int
    train_seed: int
    env_seed: int
    mobility_seed: int
    state_dim: int
    action_dim: int
    trainer_config: dict[str, Any]
    checkpoint_rule: CheckpointRuleV1
    q_networks: list[dict[str, Any]]
    target_networks: list[dict[str, Any]]
    optimizers: list[dict[str, Any]] | None = None
    last_episode_log: dict[str, Any] | None = None
    evaluation_summary: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "format_version": int(self.format_version),
            "checkpoint_kind": self.checkpoint_kind,
            "episode": int(self.episode),
            "train_seed": int(self.train_seed),
            "env_seed": int(self.env_seed),
            "mobility_seed": int(self.mobility_seed),
            "state_dim": int(self.state_dim),
            "action_dim": int(self.action_dim),
            "trainer_config": _copy_mapping(self.trainer_config),
            "checkpoint_rule": self.checkpoint_rule.to_dict(),
            "q_networks": _copy_sequence(self.q_networks),
            "target_networks": _copy_sequence(self.target_networks),
        }
        if self.optimizers is not None:
            payload["optimizers"] = _copy_sequence(self.optimizers)
        if self.last_episode_log is not None:
            payload["last_episode_log"] = _copy_mapping(self.last_episode_log)
        if self.evaluation_summary is not None:
            payload["evaluation_summary"] = _copy_mapping(self.evaluation_summary)
        return payload

    def __getitem__(self, key: str) -> Any:
        if key == "checkpoint_rule":
            return self.checkpoint_rule.to_dict()
        return self.to_dict()[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.to_dict().get(key, default)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> CheckpointPayloadV1:
        version = int(payload["format_version"])
        if version != CHECKPOINT_FORMAT_VERSION:
            # W-12 addition: the source reconstructs whatever version it is
            # handed, so a newer file would load with fields silently absent.
            raise MCRLContractError(
                f"checkpoint format version {version} is not "
                f"{CHECKPOINT_FORMAT_VERSION}; refusing to reconstruct a "
                "payload whose fields this reader does not know"
            )
        return cls(
            format_version=version,
            checkpoint_kind=str(payload["checkpoint_kind"]),
            episode=int(payload["episode"]),
            train_seed=int(payload["train_seed"]),
            env_seed=int(payload["env_seed"]),
            mobility_seed=int(payload["mobility_seed"]),
            state_dim=int(payload["state_dim"]),
            action_dim=int(payload["action_dim"]),
            trainer_config=_copy_mapping(payload["trainer_config"]),
            checkpoint_rule=CheckpointRuleV1.from_dict(payload["checkpoint_rule"]),
            q_networks=_copy_sequence(payload["q_networks"]),
            target_networks=_copy_sequence(payload["target_networks"]),
            optimizers=(
                None
                if payload.get("optimizers") is None
                else _copy_sequence(payload["optimizers"])
            ),
            last_episode_log=(
                None
                if payload.get("last_episode_log") is None
                else _copy_mapping(payload["last_episode_log"])
            ),
            evaluation_summary=(
                None
                if payload.get("evaluation_summary") is None
                else _copy_mapping(payload["evaluation_summary"])
            ),
        )
