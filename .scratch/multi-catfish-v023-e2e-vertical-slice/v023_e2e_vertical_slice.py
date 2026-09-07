#!/usr/bin/env python3
"""One-world, five-arm V0.23 integration plumbing slice.

This is expressly not a Gate, policy evaluation, or efficacy experiment.  The
only allowed result marker is ``PLUMBING_ONLY_NOT_GATE_NOT_EFFICACY``; no
controller, admission, GO, or scientific result is written by this module.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ADAPTER_PATH = REPO / ".scratch/multi-catfish-v023-five-arm-real-adapter/v023_real_five_arm_execution_adapter.py"


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load vertical-slice dependency: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


adapter_api = _load("v023_five_arm_real_adapter_vertical_slice", ADAPTER_PATH)
ARMS = adapter_api.ARMS
PLUMBING_STATUS = "PLUMBING_ONLY_NOT_GATE_NOT_EFFICACY"


class V023VerticalSliceError(RuntimeError):
    """The one-world plumbing boundary was crossed or underspecified."""


@dataclass(slots=True)
class InitialNetworkPlumbingPolicy:
    """Typed initial-network fixture, explicitly not an evaluable artifact."""

    arm: str
    checkpoint_sha256: str
    source_arm_sha256: str
    policy_family: str
    action: int
    head_drop: bool = False
    evaluable_policy_artifact: bool = False
    fixture_kind: str = "INITIAL_NETWORK_PLUMBING_ONLY"

    def select_actions(self, *, native_state: object, c3_view: object, native_observation_event_digest: str) -> np.ndarray:
        del native_state, c3_view, native_observation_event_digest
        return np.full(100, self.action, dtype=np.int64)


@dataclass(slots=True)
class CurrentInitialNetworkPlumbingPolicy:
    """Current d40-backed three-route model with a domain-separated fixture ID."""

    arm: str
    checkpoint_sha256: str
    source_arm_sha256: str
    policy_family: str
    model: Any
    bridge: Any
    head_drop: bool = False
    evaluable_policy_artifact: bool = False
    fixture_kind: str = "D40_Q12_PLUS_INITIAL_LCSRS_C3_PLUMBING_ONLY"

    def select_actions(self, *, native_state: object, c3_view: object, native_observation_event_digest: str) -> np.ndarray:
        return np.asarray(
            self.bridge.select_actions(
                native_state=native_state,
                c3_view=c3_view,
                native_observation_event_digest=native_observation_event_digest,
            ),
            dtype=np.int64,
        )


def build_initial_network_plumbing_policies(binding: Any) -> dict[str, InitialNetworkPlumbingPolicy]:
    """Adapt a source-plan-bound five-arm binding to non-evaluable fixtures.

    This deliberately does not load or claim five trained checkpoints.  It is
    legal only for an integration slice whose output is marked plumbing-only.
    """

    frozen = tuple(getattr(binding, "policies", ()))
    if tuple(getattr(item, "arm", None) for item in frozen) != ARMS:
        raise V023VerticalSliceError("source-plan binding lacks the exact five-arm order")
    policies: dict[str, InitialNetworkPlumbingPolicy] = {}
    for index, item in enumerate(frozen):
        for field in ("checkpoint_sha256", "source_arm_sha256", "policy_family"):
            if not isinstance(getattr(item, field, None), str) or not getattr(item, field):
                raise V023VerticalSliceError(f"source-plan policy {item.arm} lacks {field}")
        if getattr(item, "head_drop", False) is not False:
            raise V023VerticalSliceError(f"source-plan policy {item.arm} uses head-drop")
        policies[item.arm] = InitialNetworkPlumbingPolicy(
            arm=item.arm,
            checkpoint_sha256=item.checkpoint_sha256,
            source_arm_sha256=item.source_arm_sha256,
            policy_family=item.policy_family,
            action=index,
        )
    return policies


def load_current_d40_q12_background(model: Any, q12_artifact: Any) -> Any:
    """Use the current authenticated d40 loader; no compatibility fallback.

    The returned model still lacks a per-arm structured-Q3 payload until a
    separate current five-policy loader supplies it.  This is deliberately not
    an initial-network fixture and never selects actions by itself.
    """

    return adapter_api._runner.load_d40_q12_background(model, q12_artifact)


def _q12_config_from_authenticated_payload(q12_artifact: Any) -> Any:
    """Read only the d40 config needed before the existing loader can run."""

    try:
        # The current helper verifies again immediately before loading.  Verify
        # here too because its configuration has to be inspected to construct
        # the current three-route model; unverified bytes must not influence
        # even a plumbing-only fixture.
        q12_artifact.verify()
        if getattr(q12_artifact, "sha256", None) != adapter_api._runner.CURRENT_Q12_CHECKPOINT_SHA256:
            raise V023VerticalSliceError("Q1/Q2 artifact is not the authenticated current d40 checkpoint")
        import torch
        from mcrl.algorithms.ee_axis_action_shared import EEAxisActionSharedConfig
        payload = torch.load(q12_artifact.path, map_location="cpu", weights_only=False)
    except V023VerticalSliceError:
        raise
    except Exception as error:
        raise V023VerticalSliceError("cannot read authenticated d40 Q1/Q2 payload") from error
    raw = payload.get("config") if isinstance(payload, Mapping) else None
    if not isinstance(raw, Mapping):
        if isinstance(payload, Mapping) and isinstance(payload.get("q1"), Mapping) and isinstance(payload.get("q2"), Mapping):
            raise V023VerticalSliceError(
                "authenticated d40 payload is V0.20 split q1/q2 format; current "
                "LC-SRS loader requires one authenticated action-shared top-level payload"
            )
        raise V023VerticalSliceError("authenticated d40 payload lacks action-shared config")
    try:
        values = dict(raw)
        if isinstance(values.get("hidden_layers"), list):
            values["hidden_layers"] = tuple(values["hidden_layers"])
        if isinstance(values.get("loss_weights"), list):
            values["loss_weights"] = tuple(values["loss_weights"])
        return EEAxisActionSharedConfig(**values)
    except Exception as error:
        raise V023VerticalSliceError("d40 action-shared config is incompatible with current LC-SRS") from error


def _fixture_digest(*, arm: str, source_arm_sha256: str, d40_sha256: str, seed: int) -> str:
    return hashlib.sha256(json.dumps({
        "domain": "v023-e2e-initial-network-plumbing-fixture-v1",
        "arm": arm,
        "source_arm_sha256": source_arm_sha256,
        "d40_q12_sha256": d40_sha256,
        "initial_c3_seed": seed,
        "not_evaluable": True,
    }, sort_keys=True, separators=(",", ":")).encode("ascii")).hexdigest()


def build_current_initial_network_policy_fixtures(
    *,
    source_binding: Any,
    q12_artifact: Any,
    seed_base: int = 2026135300,
) -> dict[str, CurrentInitialNetworkPlumbingPolicy]:
    """Create five distinct current LC-SRS initial networks after d40 loading.

    The fixture identity is cryptographically domain-separated from every
    future learned checkpoint.  It must never be inserted into an evaluation
    binding or represented as an evaluable policy artifact.
    """

    frozen = tuple(getattr(source_binding, "policies", ()))
    if tuple(getattr(item, "arm", None) for item in frozen) != ARMS:
        raise V023VerticalSliceError("source binding lacks exact five-arm metadata")
    try:
        from mcrl.algorithms.ee_axis_lcsrs_c3_head import LCSRSC3QNetwork
        from mcrl.algorithms.ee_axis_lcsrs_three_route import EEAxisLCSRSThreeRoute, LCSRSThreeRouteConfig
    except ImportError as error:
        raise V023VerticalSliceError("current LC-SRS three-route classes are unavailable") from error
    q12_config = _q12_config_from_authenticated_payload(q12_artifact)
    output: dict[str, CurrentInitialNetworkPlumbingPolicy] = {}
    for index, item in enumerate(frozen):
        for field in ("checkpoint_sha256", "source_arm_sha256", "policy_family"):
            if not isinstance(getattr(item, field, None), str) or not getattr(item, field):
                raise V023VerticalSliceError(f"source binding policy {item.arm} lacks {field}")
        if getattr(item, "head_drop", False) is not False:
            raise V023VerticalSliceError(f"source binding {item.arm} uses head-drop")
        seed = seed_base + index
        model = EEAxisLCSRSThreeRoute(LCSRSThreeRouteConfig(q12=q12_config), train_seed=seed, device="cpu")
        load_current_d40_q12_background(model, q12_artifact)
        if not isinstance(model.q3, LCSRSC3QNetwork) or len(model.q_networks) != 3:
            raise V023VerticalSliceError("current model is not Q1/Q2/structured-Q3")
        bridge = adapter_api._runner.V023LCSRSThreeRoutePolicy(model)
        checkpoint = _fixture_digest(
            arm=item.arm,
            source_arm_sha256=item.source_arm_sha256,
            d40_sha256=q12_artifact.sha256,
            seed=seed,
        )
        output[item.arm] = CurrentInitialNetworkPlumbingPolicy(
            arm=item.arm,
            checkpoint_sha256=checkpoint,
            source_arm_sha256=item.source_arm_sha256,
            policy_family=f"INITIAL_NETWORK::{getattr(item, 'policy_family', 'UNSPECIFIED')}",
            model=model,
            bridge=bridge,
        )
    return output


def make_current_structured_c3_view_factory(
    *,
    q12_model: Any,
    world_id: int,
    anchor_prefix: str,
    opening_feasibility_factory: Callable[[Any, Any], Any],
) -> Callable[[Any, Any, str], Any]:
    """Make the public LC-SRS encoder seam for one fixed initial-network Q12.

    The caller must supply the outcome-blind opening-feasibility surface.  The
    current public encoder validates it against its own physics recomputation;
    this module never substitutes an all-true/zero synthetic surface.
    """

    if not callable(opening_feasibility_factory):
        raise V023VerticalSliceError("current C3View factory needs an outcome-blind opening-feasibility provider")
    try:
        from mcrl.runtime.ee_axis_lcsrs_c3_encoder import capture_lcsrs_c3_predecision
        from mcrl.runtime.ee_axis_state import encode_ee_axis_state
    except ImportError as error:
        raise V023VerticalSliceError("current LC-SRS encoder imports are unavailable") from error

    def factory(step_environment: Any, observation: Any, observation_digest: str) -> Any:
        native = encode_ee_axis_state(step_environment, observation)
        snapshot = q12_model.capture_q12(native, native_observation_event_digest=observation_digest)
        masks = np.asarray(native.action_masks, dtype=np.bool_)
        references = np.argmax(np.where(masks, snapshot.q12, -np.inf), axis=1).astype(np.int64)
        opening = opening_feasibility_factory(step_environment, observation)
        capture = capture_lcsrs_c3_predecision(
            step_environment,
            observation,
            world_id=world_id,
            anchor_id=f"{anchor_prefix}:t{getattr(observation, 'step_index', 'unknown')}",
            detached_q12=snapshot,
            reference_actions=references,
            opening_feasibility_surface=opening,
        )
        return capture.view

    return factory


def require_real_five_policy_loader(policies: Mapping[str, Any]) -> None:
    """Reject plumbing fixtures when a real vertical slice is requested."""

    if set(policies) != set(ARMS):
        raise V023VerticalSliceError("real slice requires exactly five loaded policies")
    for arm in ARMS:
        policy = policies[arm]
        if isinstance(policy, InitialNetworkPlumbingPolicy) or not bool(getattr(policy, "evaluable_policy_artifact", False)):
            raise V023VerticalSliceError(
                f"real slice policy.{arm} is not a current evaluable structured-Q3 artifact"
            )


def run_one_world_plumbing_slice(
    *,
    adapter: Any,
    world: Any,
    policies: Mapping[str, InitialNetworkPlumbingPolicy | CurrentInitialNetworkPlumbingPolicy],
    split: str = "TRAIN_DEVELOPMENT",
) -> dict[str, object]:
    """Run exactly five physical receipts for one declared TRAIN world."""

    if split != "TRAIN_DEVELOPMENT" or "TEST" in split.upper():
        raise V023VerticalSliceError("vertical slice is TRAIN-only; TEST is rejected")
    if set(policies) != set(ARMS):
        raise V023VerticalSliceError("vertical slice requires all five explicit policies")
    rows = []
    for arm in ARMS:
        policy = policies[arm]
        if not isinstance(policy, (InitialNetworkPlumbingPolicy, CurrentInitialNetworkPlumbingPolicy)) or policy.evaluable_policy_artifact:
            raise V023VerticalSliceError("vertical slice accepts only typed initial-network plumbing fixtures")
        if policy.head_drop:
            raise V023VerticalSliceError("head-drop policy is forbidden")
        try:
            row = adapter.run_episode(
                arm=arm, world=world, policy=policy,
                resume_state=adapter.resume_state_for(arm),
            )
        except Exception as error:
            raise V023VerticalSliceError(f"physical plumbing failed for {arm}: {error}") from error
        if not isinstance(row, adapter_api._results.FiveArmEpisodeReceipt):
            raise V023VerticalSliceError("legacy/synthetic receipt rejected")
        if row.learner_update or row.episode_training or row.test_split_opened or row.head_drop:
            raise V023VerticalSliceError("receipt crossed a forbidden plumbing boundary")
        rows.append(row)
    if tuple(row.arm for row in rows) != ARMS:
        raise V023VerticalSliceError("one world did not receive exact five-arm coverage")
    roots = {row.field_root_digest for row in rows}
    worlds = {(row.episode_index, row.world_id, row.world_seed) for row in rows}
    if len(roots) != 1 or len(worlds) != 1:
        raise V023VerticalSliceError("five arms did not share one keyed physical world")
    return {
        "schema": "multi-catfish-mcrl-v023-e2e-vertical-slice-v1",
        "status": PLUMBING_STATUS,
        "split": split,
        "world": {"episode_index": rows[0].episode_index, "world_id": rows[0].world_id, "world_seed": rows[0].world_seed, "field_root_digest": rows[0].field_root_digest},
        "receipt_count": len(rows),
        "arms": list(ARMS),
        "receipts": [row.to_dict() for row in rows],
        "zero_learner_updates": True,
        "evaluable_policy_artifacts": False,
        "scientific_decision": None,
    }


def real_launch_blocker(*, policy_loader: Callable[..., Any] | None = None) -> None:
    """Explain the missing production binding before opening a real TLE world."""

    if policy_loader is None:
        raise V023VerticalSliceError(
            "real launch blocked: the authenticated d40 bytes are V0.20 split "
            "q1/q2 rather than the action-shared payload required by "
            "load_current_d40_q12_background(); after that exact format binding "
            "exists, a non-gate five-policy loader must bind each domain-separated "
            "initial fixture (arm/checkpoint/source-arm/family/head_drop) without "
            "pretending it is a FrozenPolicyBinding, and an outcome-blind current "
            "structured C3View provider must be registered"
        )
