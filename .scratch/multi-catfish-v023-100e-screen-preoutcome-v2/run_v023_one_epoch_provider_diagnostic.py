#!/usr/bin/env python3
"""Non-formal one-epoch real-provider plumbing diagnostic for the V0.23 five-arm seam.

This command loads the sealed R7 root and the sealed C1/C2 target root through
the real post-R7 provider factory, advances exactly one complete
``C1 -> C2 -> C3`` source-training epoch across the five current arms, then
verifies the execution plumbing only:

* Q1 consumes 228-D action-shared states, Q2 consumes 448-D OPS-3 action-set
  states with Boolean action masks, and every update keeps the three heads
  isolated;
* the C2 learner receives the producer's ``target_delta`` values unchanged
  (already divided by kappa exactly once at target generation);
* all five arms receive the closed source-ablation mapping;
* the five-arm checkpoint (model + optimizer + provider sampler state) survives
  a disk round trip and continues bit-identically for one more epoch; and
* ``q1 + q2 + q3`` masked deployment scoring runs on real provider tensors.

It is expressly outside the formal 100E contract: it writes to its own root,
never publishes ``COMPLETE``, and its loss values are execution evidence only.
Nothing here is an EE, efficacy, or scientific claim.  TEST stays closed.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
from dataclasses import asdict
from hashlib import sha256
import importlib.util
import inspect
import json
import os
from pathlib import Path
import platform
import socket
import sys
import time
import traceback
from types import ModuleType
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
# The server venv's editable install points at a stale tree without the
# EE-axis modules; the checkout's own ``src`` must win before mcrl is imported.
_SRC = REPO / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import numpy as np  # noqa: E402
import torch  # noqa: E402

from mcrl.algorithms.ee_axis_lcsrs_three_route import LCSRSThreeRouteConfig  # noqa: E402
from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch  # noqa: E402
from mcrl.algorithms.ee_axis_v014_head import (  # noqa: E402
    EEAxisV014NormalizedPairBatch,
    V014ActionSetQNetwork,
)
from mcrl.runtime.ee_axis_lcsrs_c3_dataset import LCSRSAnchorSurface  # noqa: E402
from mcrl.runtime.ee_axis_lcsrs_c3_learner import LCSRSC3SampledBatch  # noqa: E402
from mcrl.runtime.ee_axis_lcsrs_c3_state import assemble_c3_view  # noqa: E402


SCHEMA = "multi-catfish-mcrl-v023-one-epoch-provider-plumbing-diagnostic-v1"
STATUS_PASS = "PASS_ONE_EPOCH_PROVIDER_PLUMBING_DIAGNOSTIC"
STATUS_FAIL = "FAIL_ONE_EPOCH_PROVIDER_PLUMBING_DIAGNOSTIC"
CLAIM_CEILING = (
    "NON_FORMAL_ONE_EPOCH_PROVIDER_PLUMBING_DIAGNOSTIC_"
    "NO_TEST_NO_EPISODE_TRAINING_NO_EFFICACY_NO_SCIENTIFIC_CLAIM"
)
DIAGNOSTIC_LINEAGE = "v023-three-route-one-epoch-provider-diagnostic"
FROZEN_100E_TRAIN_SEED = 2927175120652069826
OPS3_TARGET_UNIT = "normalized-repriced-ops3-delta-over-kappa"
EXPECTED_Q1_STATE_DIM = 228
EXPECTED_Q2_STATE_DIM = 448
EXPECTED_ACTIONS = 28
EXPECTED_Q2_LOCAL_FEATURES = 16
UPDATES_PER_EPOCH = 3
ROUTES = ("C1", "C2", "C3")
SOURCES = ("neutral", "informed")
RECEIPT_NAME = "one-epoch-provider-diagnostic.json"
CHECKPOINT_NAME = "one-epoch.five-arm-orchestrator-checkpoint.pt"

RUNNER_PATH = (
    REPO
    / ".scratch/multi-catfish-v023-five-arm-training-runner"
    / "v023_five_arm_source_training_runner.py"
)
FACTORY_PATH = (
    REPO
    / ".scratch/multi-catfish-v023-post-r7-provider-factory"
    / "v023_post_r7_provider_factory_v2.py"
)
TRAINER_PATH = (
    REPO
    / ".scratch/multi-catfish-v023-heterogeneous-trainer"
    / "v023_heterogeneous_trainer.py"
)


class V023OneEpochDiagnosticError(RuntimeError):
    """The non-formal diagnostic could not be executed as specified."""


def _load_module(name: str, path: Path) -> ModuleType:
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    if path.is_symlink() or not path.is_file():
        raise V023OneEpochDiagnosticError(f"required module is unavailable: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise V023OneEpochDiagnosticError(f"cannot import required module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_runner_module() -> ModuleType:
    """Load the existing five-arm runner; it carries the orchestrator seam."""

    return _load_module("v023_five_arm_runner_for_one_epoch_diagnostic", RUNNER_PATH)


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii") + b"\n"


def _write_once(path: Path, payload: bytes) -> str:
    if path.exists() or path.is_symlink():
        raise V023OneEpochDiagnosticError(f"refusing to overwrite: {path}")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    return sha256(payload).hexdigest()


def _jsonable(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return _jsonable(value.tolist())
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if np.isfinite(number) else repr(number)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (bytes, bytearray)):
        return {"bytes_sha256": sha256(bytes(value)).hexdigest(), "length": len(value)}
    if isinstance(value, (set, frozenset)):
        return sorted(_jsonable(item) for item in value)
    if isinstance(value, torch.Tensor):
        return {"tensor_shape": list(value.shape), "dtype": str(value.dtype)}
    if value is None or isinstance(value, (bool, int, str)):
        return value
    return repr(value)[:400]


class RecordingProvider:
    """Delegate every call to the real provider and retain the typed batches.

    The wrapper adds no sampling, ordering, or state of its own; it only keeps
    the first ``ProvidedRouteBatch`` seen for every ``(route, source)`` so the
    diagnostic can inspect shapes, masks, and target units after the
    orchestrator has consumed them.
    """

    def __init__(self, inner: object) -> None:
        self._inner = inner
        self.recorded: dict[tuple[str, str], object] = {}
        self.calls: list[tuple[str, str, int]] = []

    @property
    def provider_identity(self) -> object:
        return getattr(self._inner, "provider_identity")

    @property
    def planned_epoch_budget(self) -> object:
        return getattr(self._inner, "planned_epoch_budget")

    @property
    def provider_identity_payload(self) -> object:
        return getattr(self._inner, "provider_identity_payload", None)

    def next_batch(self, *, route: str, source: str, update_cursor: int) -> object:
        provided = self._inner.next_batch(
            route=route, source=source, update_cursor=update_cursor
        )
        self.calls.append((route, source, update_cursor))
        self.recorded.setdefault((route, source), provided)
        return provided

    def sampler_state(self) -> Mapping[str, Any]:
        return self._inner.sampler_state()

    def load_sampler_state(self, state: Mapping[str, Any]) -> None:
        self._inner.load_sampler_state(state)


def _identity(provider: object) -> str:
    candidate = getattr(provider, "provider_identity", None)
    identity = candidate() if callable(candidate) else candidate
    if (
        not isinstance(identity, str)
        or not identity
        or identity != identity.strip()
        or len(identity) > 512
    ):
        raise V023OneEpochDiagnosticError(
            "provider must expose a nonempty trimmed provider_identity of at most 512 characters"
        )
    return identity


def _budget(provider: object) -> int:
    candidate = getattr(provider, "planned_epoch_budget", None)
    budget = candidate() if callable(candidate) else candidate
    if type(budget) is not int or budget <= 0:
        raise V023OneEpochDiagnosticError("provider exposes no positive planned_epoch_budget")
    return budget


def _hex_digest(text: str) -> str:
    return sha256(text.encode("ascii")).hexdigest()


def _slice_view_arrays(view: object, users: int) -> dict[str, np.ndarray]:
    """Restrict one authenticated C3View to its first ``users`` users.

    Tokens carry one ordinary slot per user plus one trailing pair slot, so the
    pair slot is re-appended after the ordinary slots are truncated.
    """

    total = int(np.asarray(view.action_context).shape[0])
    if not 1 <= users <= total:
        raise V023OneEpochDiagnosticError("scoring user count is outside the view")
    context = np.asarray(view.action_context)
    tokens = np.asarray(view.tokens)
    token_mask = np.asarray(view.token_mask)
    action_mask = np.asarray(view.action_mask)
    if users == total:
        return {
            "action_context": context,
            "tokens": tokens,
            "token_mask": token_mask,
            "action_mask": action_mask,
        }
    return {
        "action_context": np.ascontiguousarray(context[:users]),
        "tokens": np.ascontiguousarray(
            np.concatenate((tokens[:users, :, :users, :], tokens[:users, :, total : total + 1, :]), axis=2)
        ),
        "token_mask": np.ascontiguousarray(
            np.concatenate((token_mask[:users, :, :users], token_mask[:users, :, total : total + 1]), axis=2)
        ),
        "action_mask": np.ascontiguousarray(action_mask[:users]),
    }


def _masked_argmax(scores: np.ndarray, masks: np.ndarray) -> np.ndarray:
    return np.argmax(np.where(masks, scores, -np.inf), axis=1).astype(np.int64)


def _score_arm(
    model: object,
    *,
    q1_states: np.ndarray,
    q2_states: np.ndarray,
    view: object,
    users: int,
    event_digest: str,
) -> dict[str, Any]:
    arrays = _slice_view_arrays(view, users)
    action_mask = arrays["action_mask"]
    snapshot = model.capture_q12(
        np.asarray(q1_states[:users], dtype=np.float32),
        q2_states=np.asarray(q2_states[:users], dtype=np.float32),
        q2_action_masks=action_mask,
        native_observation_event_digest=event_digest,
    )
    references = _masked_argmax(snapshot.q12, action_mask)
    scoring_view = assemble_c3_view(
        action_context=arrays["action_context"],
        tokens=arrays["tokens"],
        token_mask=arrays["token_mask"],
        action_mask=action_mask,
        reference_actions=references,
    )
    q1, q2, q3 = model.q_values(snapshot, scoring_view)
    scores = model.deployment_scores(snapshot, scoring_view)
    actions = model.select_greedy_actions(snapshot, scoring_view)
    rows = np.arange(users)
    legal = bool(np.all(action_mask[rows, actions]))
    expected_actions = _masked_argmax(scores, action_mask)
    return {
        "users": int(users),
        "q1_shape": list(np.asarray(q1).shape),
        "q2_shape": list(np.asarray(q2).shape),
        "q3_shape": list(np.asarray(q3).shape),
        "all_finite": bool(
            np.all(np.isfinite(q1)) and np.all(np.isfinite(q2)) and np.all(np.isfinite(q3))
        ),
        "q12_is_q1_plus_q2": bool(np.array_equal(snapshot.q12, np.asarray(q1 + q2, dtype=np.float32))),
        "scores_are_q1_q2_q3_sum": bool(np.array_equal(scores, np.asarray(q1 + q2 + q3, dtype=np.float32))),
        "selected_actions_legal_under_mask": legal,
        "selected_actions_are_masked_argmax": bool(np.array_equal(actions, expected_actions)),
        "masked_action_count_per_user_min": int(np.min(np.sum(action_mask, axis=1))),
        "masked_action_count_per_user_max": int(np.max(np.sum(action_mask, axis=1))),
        "selected_actions_sha256": _hex_digest(json.dumps(actions.tolist())),
        "scores_sha256": sha256(np.ascontiguousarray(scores).tobytes()).hexdigest(),
        "_scores": np.asarray(scores, dtype=np.float32),
    }


def run_diagnostic(
    *,
    make_provider: Callable[[], object],
    model_config: LCSRSThreeRouteConfig,
    train_seed: int,
    output_root: Path,
    load_target_artifact: Callable[[], object] | None = None,
    scoring_users: int = 0,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute the diagnostic and write one write-once receipt under output_root."""

    started = time.time()
    runner = load_runner_module()
    orchestrator_api = runner.ORCHESTRATOR
    trainer_module = _load_module(
        "v023_heterogeneous_trainer_for_one_epoch_diagnostic", TRAINER_PATH
    )
    root = Path(output_root)
    if root.exists() or root.is_symlink():
        raise V023OneEpochDiagnosticError("diagnostic output root must be absent")
    root.mkdir(mode=0o700)

    checks: dict[str, dict[str, Any]] = {}
    notes: list[str] = []

    def record(name: str, passed: bool, **detail: Any) -> bool:
        checks[name] = {"pass": bool(passed), **_jsonable(detail)}
        return bool(passed)

    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "status": STATUS_FAIL,
        "claim_ceiling": CLAIM_CEILING,
        "formal_100e_contract": False,
        "test_split_opened": False,
        "episode_training": False,
        "simulator_opened": False,
        "scientific_claim": False,
        "efficacy_claim": False,
        "loss_values_are_execution_evidence_only": True,
        "train_seed": int(train_seed),
        "updates_per_epoch": UPDATES_PER_EPOCH,
        "diagnostic_lineage": DIAGNOSTIC_LINEAGE,
        "metadata": dict(metadata or {}),
        "environment": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "numpy": np.__version__,
            "hostname": socket.gethostname(),
            "device": "cpu",
        },
        "checks": checks,
        "notes": notes,
    }

    def finish(error: str | None = None) -> dict[str, Any]:
        all_pass = bool(checks) and all(item["pass"] for item in checks.values())
        receipt["status"] = STATUS_PASS if all_pass and error is None else STATUS_FAIL
        receipt["failed_checks"] = sorted(name for name, item in checks.items() if not item["pass"])
        receipt["error"] = error
        receipt["elapsed_s"] = round(time.time() - started, 3)
        try:
            payload = _canonical_bytes(_jsonable(receipt))
        except (TypeError, ValueError) as serialisation_error:
            # A receipt must always exist; fall back to a minimal failure record.
            receipt["status"] = STATUS_FAIL
            receipt["error"] = (
                f"{error or ''}; receipt serialisation failed: "
                f"{type(serialisation_error).__name__}: {serialisation_error}"
            ).strip("; ")
            payload = _canonical_bytes(
                {
                    "schema": SCHEMA,
                    "status": STATUS_FAIL,
                    "claim_ceiling": CLAIM_CEILING,
                    "error": receipt["error"],
                    "failed_checks": receipt["failed_checks"],
                    "elapsed_s": receipt["elapsed_s"],
                }
            )
        receipt["receipt_sha256"] = _write_once(root / RECEIPT_NAME, payload)
        _write_once(
            root / (RECEIPT_NAME + ".sha256"),
            f"{receipt['receipt_sha256']}  {RECEIPT_NAME}\n".encode("ascii"),
        )
        return receipt

    try:
        # ---- model configuration -------------------------------------------------
        if not isinstance(model_config, LCSRSThreeRouteConfig):
            raise V023OneEpochDiagnosticError("model_config must be LCSRSThreeRouteConfig")
        record(
            "model_config_q1_228_q2_448",
            model_config.q1.state_dim == EXPECTED_Q1_STATE_DIM
            and model_config.q1.action_dim == EXPECTED_ACTIONS
            and model_config.q2.state_dim == EXPECTED_Q2_STATE_DIM
            and model_config.q2.action_dim == EXPECTED_ACTIONS
            and model_config.q2.local_feature_dim == EXPECTED_Q2_LOCAL_FEATURES
            and model_config.q2.global_feature_dim == 0,
            q1_state_dim=model_config.q1.state_dim,
            q2_state_dim=model_config.q2.state_dim,
            q2_local_feature_dim=model_config.q2.local_feature_dim,
            q2_global_feature_dim=model_config.q2.global_feature_dim,
            q1_kappa_bits=float(model_config.q1.kappa_bits),
            q2_kappa_bits=float(model_config.q2.kappa_bits),
        )
        receipt["model_config"] = _jsonable(asdict(model_config))

        # ---- provider ---------------------------------------------------------------
        provider_a = RecordingProvider(make_provider())
        identity = _identity(provider_a)
        budget = _budget(provider_a)
        receipt["provider_identity"] = identity
        receipt["provider_planned_epoch_budget"] = budget
        payload = getattr(provider_a, "provider_identity_payload", None)
        receipt["provider_identity_payload"] = _jsonable(dict(payload)) if isinstance(payload, Mapping) else None
        record("provider_identity_present", bool(identity), identity=identity, planned_epoch_budget=budget)

        # ---- orchestrator, one epoch -------------------------------------------------
        config = orchestrator_api.V023FiveArmOrchestratorConfig(
            model_config=model_config,
            train_seed=int(train_seed),
            lineage=DIAGNOSTIC_LINEAGE,
            checkpoint_cadence_updates=UPDATES_PER_EPOCH,
            formal_use=False,
        )
        orchestrator_a = orchestrator_api.V023FiveArmLearnerOrchestrator(config, provider_a)
        receipt["initialization_sha256"] = orchestrator_a.initialization_sha256
        # Q2 parameters before any update: the C2 update of epoch 1 must be a pure
        # function of these weights and of the delivered already-normalized deltas.
        q2_before = {
            arm: {
                key: value.detach().clone()
                for key, value in orchestrator_a.models[arm].q2.state_dict().items()
            }
            for arm in orchestrator_api.ARMS
        }
        round_receipts = orchestrator_a.advance_many(UPDATES_PER_EPOCH)
        routes = tuple(item.route for item in round_receipts)
        record("epoch_route_order_c1_c2_c3", routes == ROUTES, observed=list(routes))
        record(
            "epoch_closed_at_c1",
            orchestrator_a.update_cursor == UPDATES_PER_EPOCH
            and orchestrator_a.completed_source_training_epochs == 1
            and orchestrator_a.next_route == "C1"
            and orchestrator_a.checkpoint_due(),
            update_cursor=orchestrator_a.update_cursor,
        )
        expected_map = orchestrator_api.SOURCE_ABLATION_MAP
        arm_rows: list[dict[str, Any]] = []
        mapping_ok = True
        finite_ok = True
        for item in round_receipts:
            for update in item.arm_updates:
                expected_source = expected_map[update.arm][update.route]
                mapping_ok &= update.source == expected_source
                loss = float(update.update.get("loss", float("nan")))
                finite_ok &= bool(np.isfinite(loss))
                arm_rows.append(
                    {
                        "update_cursor": item.update_cursor,
                        "route": update.route,
                        "arm": update.arm,
                        "source": update.source,
                        "expected_source": expected_source,
                        "file_id": update.file_id,
                        "update": dict(update.update),
                    }
                )
        record(
            "five_arm_source_mapping_exact",
            mapping_ok and len(arm_rows) == UPDATES_PER_EPOCH * len(orchestrator_api.ARMS),
            arm_order=list(orchestrator_api.ARMS),
            source_ablation_map={arm: dict(routes_) for arm, routes_ in expected_map.items()},
            rows=len(arm_rows),
        )
        record("all_route_losses_finite", finite_ok)
        receipt["epoch_updates"] = arm_rows
        receipt["provider_calls_epoch_1"] = [list(call) for call in provider_a.calls]

        # ---- recorded batches: shapes, types, masks ------------------------------------
        batches = provider_a.recorded
        c1_ok = True
        c2_ok = True
        c3_ok = True
        batch_detail: dict[str, Any] = {}
        for source in SOURCES:
            c1 = batches.get(("C1", source))
            c2 = batches.get(("C2", source))
            c3 = batches.get(("C3", source))
            if c1 is None or c2 is None or c3 is None:
                raise V023OneEpochDiagnosticError(f"provider did not deliver all routes for {source}")
            c1_batch = c1.batch
            c2_batch = c2.batch
            c3_batch = c3.batch
            c1_states = np.asarray(c1_batch.states)
            c1_masks = np.asarray(c1_batch.action_masks)
            c1_this = (
                isinstance(c1_batch, EEAxisPairBatch)
                and c1_states.ndim == 2
                and c1_states.shape[1] == EXPECTED_Q1_STATE_DIM
                and c1_states.dtype == np.float32
                and c1_masks.dtype == np.bool_
                and c1_masks.shape == (c1_states.shape[0], EXPECTED_ACTIONS)
                and bool(np.all(c1_masks[np.arange(c1_states.shape[0]), np.asarray(c1_batch.reference_actions)]))
                and bool(np.all(c1_masks[np.arange(c1_states.shape[0]), np.asarray(c1_batch.candidate_actions)]))
            )
            c2_states = np.asarray(c2_batch.states)
            c2_masks = np.asarray(c2_batch.action_masks)
            c2_deltas = np.asarray(c2_batch.normalized_target_deltas)
            c2_this = (
                isinstance(c2_batch, EEAxisV014NormalizedPairBatch)
                and c2_states.ndim == 2
                and c2_states.shape[1] == EXPECTED_Q2_STATE_DIM
                and c2_states.dtype == np.float32
                and c2_masks.dtype == np.bool_
                and c2_masks.shape == (c2_states.shape[0], EXPECTED_ACTIONS)
                and bool(np.all(np.any(c2_masks, axis=1)))
                and c2_deltas.shape == (c2_states.shape[0],)
                and bool(np.all(np.isfinite(c2_deltas)))
                and bool(np.all(c2_masks[np.arange(c2_states.shape[0]), np.asarray(c2_batch.reference_actions)]))
                and bool(np.all(c2_masks[np.arange(c2_states.shape[0]), np.asarray(c2_batch.candidate_actions)]))
            )
            try:
                c2_batch.validate(config=model_config.q2)
            except Exception as error:  # noqa: BLE001 - recorded as a failed check
                c2_this = False
                notes.append(f"C2/{source} batch failed current Q2 config validation: {error}")
            surfaces = tuple(c3.c3_surfaces)
            c3_this = (
                isinstance(c3_batch, LCSRSC3SampledBatch)
                and c3_batch.rows >= 1
                and len(surfaces) >= 1
                and all(isinstance(surface, LCSRSAnchorSurface) for surface in surfaces)
                and int(np.max(np.asarray(c3_batch.anchor_indices))) < len(surfaces)
            )
            first_view = surfaces[0].view if surfaces else None
            batch_detail[source] = {
                "c1_file_id": c1.file_id,
                "c1_rows": int(c1_states.shape[0]),
                "c1_state_dim": int(c1_states.shape[1]) if c1_states.ndim == 2 else None,
                "c1_target_unit": "raw-surplus-bits (divided by kappa inside the C1 trainer)",
                "c2_file_id": c2.file_id,
                "c2_rows": int(c2_states.shape[0]),
                "c2_state_dim": int(c2_states.shape[1]) if c2_states.ndim == 2 else None,
                "c2_mask_true_min": int(np.min(np.sum(c2_masks, axis=1))) if c2_masks.size else None,
                "c2_mask_true_max": int(np.max(np.sum(c2_masks, axis=1))) if c2_masks.size else None,
                "c2_normalized_delta_abs_max": float(np.max(np.abs(c2_deltas))) if c2_deltas.size else None,
                "c3_file_id": c3.file_id,
                "c3_sampled_rows": int(c3_batch.rows),
                "c3_surfaces": len(surfaces),
                "c3_first_view_users": int(np.asarray(first_view.action_context).shape[0]) if first_view is not None else None,
                "c3_first_view_tokens_shape": list(np.asarray(first_view.tokens).shape) if first_view is not None else None,
            }
            c1_ok &= c1_this
            c2_ok &= c2_this
            c3_ok &= c3_this
        record("c1_batches_are_228d_action_shared_with_legal_masks", c1_ok, **{k: v for k, v in batch_detail.items()})
        record("c2_batches_are_448d_ops3_normalized_with_masks", c2_ok)
        record("c3_batches_are_structured_sampled_with_surfaces", c3_ok)

        # ---- C2 normalization exactly once ---------------------------------------------
        c2_source = inspect.getsource(trainer_module.V023HeterogeneousTrainer.update_c2)
        c1_source = inspect.getsource(trainer_module.V023HeterogeneousTrainer.update_c1)
        record(
            "c2_trainer_path_has_no_kappa_division",
            "kappa_bits" not in c2_source and "normalized_target_deltas" in c2_source,
            c1_path_divides_raw_bits_by_kappa="kappa_bits" in inspect.getsource(
                trainer_module.V023HeterogeneousTrainer._update_c1_pairwise
            ),
            c1_entry_delegates=("_update_c1_pairwise" in c1_source),
        )
        # Behavioural check (independent of source text): recompute each arm's C2
        # loss from the pre-update Q2 weights and the delivered normalized deltas
        # exactly as the frozen objective defines it, and compare with the loss the
        # trainer reported.  A second division by kappa (or any rescaling) inside
        # the trainer would change the residual and fail this check.
        c2_round = next(item for item in round_receipts if item.route == "C2")
        behavioural: dict[str, Any] = {}
        behavioural_ok = True
        for update in c2_round.arm_updates:
            c2_batch = batches[("C2", update.source)].batch
            network = V014ActionSetQNetwork(model_config.q2)
            network.load_state_dict(q2_before[update.arm])
            network.eval()
            with torch.no_grad():
                states = torch.tensor(np.asarray(c2_batch.states), dtype=torch.float32)
                masks = torch.tensor(np.asarray(c2_batch.action_masks), dtype=torch.bool)
                reference = torch.tensor(np.asarray(c2_batch.reference_actions), dtype=torch.int64)
                candidate = torch.tensor(np.asarray(c2_batch.candidate_actions), dtype=torch.int64)
                deltas = torch.tensor(np.asarray(c2_batch.normalized_target_deltas), dtype=torch.float32)
                surface = network(states, masks)
                rows = torch.arange(states.shape[0])
                q_reference = surface[rows, reference]
                residual = surface[rows, candidate] - q_reference - deltas
                pair_mse = float(torch.mean(residual.square()))
                gauge_mse = float(torch.mean(q_reference.square()))
                loss = pair_mse + float(model_config.q2.beta) * gauge_mse
            reported = dict(update.update)
            def _close(expected: float, actual: object) -> bool:
                try:
                    actual_value = float(actual)
                except (TypeError, ValueError):
                    return False
                return abs(actual_value - expected) <= 1e-6 * max(1.0, abs(expected))
            arm_ok = (
                _close(pair_mse, reported.get("pair_mse"))
                and _close(gauge_mse, reported.get("gauge_mse"))
                and _close(loss, reported.get("loss"))
            )
            behavioural_ok &= arm_ok
            behavioural[update.arm] = {
                "source": update.source,
                "recomputed": {"pair_mse": pair_mse, "gauge_mse": gauge_mse, "loss": loss},
                "reported": {k: reported.get(k) for k in ("pair_mse", "gauge_mse", "loss", "batch_size")},
                "match": arm_ok,
            }
        record(
            "c2_update_loss_reproduced_from_delivered_deltas_without_rescaling",
            behavioural_ok,
            tolerance="1e-6 relative",
            arms=behavioural,
        )

        if load_target_artifact is not None:
            artifact = load_target_artifact()
            per_source: dict[str, Any] = {}
            once_ok = True
            for source in SOURCES:
                inputs = artifact.for_mode(source)
                rows: list[float] = []
                units: set[str] = set()
                files: list[str] = []
                for entry in inputs.c2_datasets:
                    files.append(Path(entry.path).name)
                    for row in entry.dataset.rows:
                        units.add(str(row.get("target_unit")))
                        rows.append(float(row["target_delta"]))
                producer_deltas = np.asarray(rows, dtype=np.float64)
                delivered = np.asarray(batches[("C2", source)].batch.normalized_target_deltas, dtype=np.float64)
                equal = bool(
                    producer_deltas.shape == delivered.shape and np.array_equal(producer_deltas, delivered)
                )
                once_ok &= equal and units == {OPS3_TARGET_UNIT}
                per_source[source] = {
                    "producer_rows": int(producer_deltas.size),
                    "delivered_rows": int(delivered.size),
                    "byte_equal_target_delta": equal,
                    "target_units": sorted(units),
                    "files": files,
                }
            record(
                "c2_labels_delivered_equal_producer_target_delta_no_second_division",
                once_ok,
                expected_target_unit=OPS3_TARGET_UNIT,
                **per_source,
            )
        else:
            record(
                "c2_labels_delivered_equal_producer_target_delta_no_second_division",
                False,
                reason="no target artifact loader supplied; the producer-vs-delivered check is mandatory",
            )

        # ---- checkpoint: disk round trip, exact reload ---------------------------------
        state_a = orchestrator_a.checkpoint_state()
        checkpoint_path = root / CHECKPOINT_NAME
        with checkpoint_path.open("xb") as stream:
            torch.save(state_a, stream)
            stream.flush()
            os.fsync(stream.fileno())
        checkpoint_sha = _file_sha256(checkpoint_path)
        _write_once(root / (CHECKPOINT_NAME + ".sha256"), f"{checkpoint_sha}  {CHECKPOINT_NAME}\n".encode("ascii"))
        receipt["checkpoint"] = {
            "path": CHECKPOINT_NAME,
            "sha256": checkpoint_sha,
            "update_cursor": int(state_a["update_cursor"]),
            "completed_source_training_epochs": int(state_a["completed_source_training_epochs"]),
        }
        loaded = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        provider_b = RecordingProvider(make_provider())
        record("second_provider_identity_stable", _identity(provider_b) == identity)
        orchestrator_b = orchestrator_api.V023FiveArmLearnerOrchestrator(config, provider_b)
        orchestrator_b.load_checkpoint_state(loaded)
        state_b = orchestrator_b.checkpoint_state()
        record(
            "checkpoint_reload_exact_model_optimizer_provider_state",
            runner._tree_equal(state_a, state_b)
            and orchestrator_b.update_cursor == UPDATES_PER_EPOCH
            and orchestrator_b.completed_source_training_epochs == 1
            and orchestrator_b.next_route == "C1"
            and dict(provider_a.sampler_state()) == dict(provider_b.sampler_state()),
            reloaded_update_cursor=orchestrator_b.update_cursor,
            provider_sampler_state=dict(provider_b.sampler_state()),
        )

        # ---- masked deployment scoring on real provider tensors -------------------------
        c1_informed = batches[("C1", "informed")].batch
        c2_informed = batches[("C2", "informed")].batch
        c3_view = tuple(batches[("C3", "informed")].c3_surfaces)[0].view
        view_users = int(np.asarray(c3_view.action_context).shape[0])
        available = min(view_users, int(np.asarray(c1_informed.states).shape[0]), int(np.asarray(c2_informed.states).shape[0]))
        users = available if scoring_users <= 0 else min(scoring_users, available)
        event_digest = _hex_digest(f"{SCHEMA}:scoring:{identity}")
        scoring: dict[str, Any] = {}
        scoring_ok = True
        reload_forward_ok = True
        for arm in orchestrator_api.ARMS:
            result_b = _score_arm(
                orchestrator_b.models[arm],
                q1_states=np.asarray(c1_informed.states),
                q2_states=np.asarray(c2_informed.states),
                view=c3_view,
                users=users,
                event_digest=event_digest,
            )
            result_a = _score_arm(
                orchestrator_a.models[arm],
                q1_states=np.asarray(c1_informed.states),
                q2_states=np.asarray(c2_informed.states),
                view=c3_view,
                users=users,
                event_digest=event_digest,
            )
            reload_forward_ok &= bool(np.array_equal(result_a.pop("_scores"), result_b.pop("_scores")))
            scoring_ok &= (
                result_b["q1_shape"] == [users, EXPECTED_ACTIONS]
                and result_b["q2_shape"] == [users, EXPECTED_ACTIONS]
                and result_b["q3_shape"] == [users, EXPECTED_ACTIONS]
                and result_b["all_finite"]
                and result_b["q12_is_q1_plus_q2"]
                and result_b["scores_are_q1_q2_q3_sum"]
                and result_b["selected_actions_legal_under_mask"]
                and result_b["selected_actions_are_masked_argmax"]
            )
            scoring[arm] = result_b
        record(
            "q1_q2_q3_masked_deployment_scoring",
            scoring_ok,
            users=users,
            view_users=view_users,
            note=(
                "plumbing check only: Q1/Q2 rows are the first informed C1/C2 panel rows, "
                "the mask and structured context come from the first informed C3 anchor view, "
                "and C3View references are recomputed as the current masked Q1+Q2 argmax; "
                "action-context relation fields are not re-encoded, so this is not a physical "
                "deployment decision"
            ),
            arms=scoring,
        )
        record("reloaded_models_reproduce_forward_scores", reload_forward_ok)

        # ---- bit-identical continuation for one more epoch -------------------------------
        more_a = orchestrator_a.advance_many(UPDATES_PER_EPOCH)
        more_b = orchestrator_b.advance_many(UPDATES_PER_EPOCH)
        same_updates = all(
            [dict(u.update) for u in ra.arm_updates] == [dict(u.update) for u in rb.arm_updates]
            and ra.source_files == rb.source_files
            for ra, rb in zip(more_a, more_b, strict=True)
        )
        record(
            "resume_continues_bit_identically_for_one_more_epoch",
            same_updates and runner._tree_equal(orchestrator_a.checkpoint_state(), orchestrator_b.checkpoint_state()),
            epoch_two_routes=[item.route for item in more_b],
            final_update_cursor=orchestrator_b.update_cursor,
        )
        receipt["epoch_two_updates_reloaded"] = [
            {
                "update_cursor": item.update_cursor,
                "route": item.route,
                "arm_losses": {u.arm: float(u.update.get("loss", float("nan"))) for u in item.arm_updates},
            }
            for item in more_b
        ]
        return finish()
    except Exception as error:  # noqa: BLE001 - the receipt must record the failure
        notes.append(traceback.format_exc()[-4000:])
        return finish(error=f"{type(error).__name__}: {error}")


def _real_wiring(arguments: argparse.Namespace) -> dict[str, Any]:
    factory = _load_module("v023_post_r7_factory_for_one_epoch_diagnostic", FACTORY_PATH)
    runner = load_runner_module()
    provider_config = Path(arguments.provider_config).resolve()
    model_config_path = Path(arguments.model_config).resolve()
    config_sha = _file_sha256(provider_config)
    parsed = factory.PostR7ProviderConfig.from_payload(
        factory._read_canonical_json(provider_config, field="post-R7 provider config")
    )
    os.environ[factory.CONFIG_PATH_ENV] = str(provider_config)
    os.environ[factory.CONFIG_SHA256_ENV] = config_sha
    model_config = runner._load_model_config(model_config_path)
    metadata = {
        "provider_config_path": str(provider_config),
        "provider_config_sha256": config_sha,
        "model_config_path": str(model_config_path),
        "model_config_sha256": _file_sha256(model_config_path),
        "r7_root": str(parsed.r7_root),
        "target_root": str(parsed.target_root),
        "provider_epoch_budget": parsed.epoch_budget,
        "schedule_seed": parsed.schedule_seed,
        "factory_sha256": _file_sha256(FACTORY_PATH),
        "runner_sha256": _file_sha256(RUNNER_PATH),
        "trainer_sha256": _file_sha256(TRAINER_PATH),
        "diagnostic_sha256": _file_sha256(Path(__file__).resolve()),
        "mcrl_src": str(_SRC),
        "command": "run_v023_one_epoch_provider_diagnostic",
    }
    return {
        "make_provider": factory.make_provider,
        "load_target_artifact": lambda: factory._BRIDGE.load_completed_target_artifact(parsed.target_root),
        "model_config": model_config,
        "metadata": metadata,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider-config", required=True)
    parser.add_argument("--model-config", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--train-seed", type=int, default=FROZEN_100E_TRAIN_SEED)
    parser.add_argument(
        "--scoring-users",
        type=int,
        default=0,
        help="cap the deployment-scoring user count; 0 scores every user of the first C3 view",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    wiring = _real_wiring(arguments)
    receipt = run_diagnostic(
        make_provider=wiring["make_provider"],
        load_target_artifact=wiring["load_target_artifact"],
        model_config=wiring["model_config"],
        train_seed=arguments.train_seed,
        output_root=Path(arguments.output_root),
        scoring_users=arguments.scoring_users,
        metadata=wiring["metadata"],
    )
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "failed_checks": receipt.get("failed_checks"),
                "error": receipt.get("error"),
                "receipt": str(Path(arguments.output_root) / RECEIPT_NAME),
                "provider_identity": receipt.get("provider_identity"),
                "elapsed_s": receipt.get("elapsed_s"),
            },
            sort_keys=True,
        )
    )
    return 0 if receipt["status"] == STATUS_PASS else 3


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CLAIM_CEILING",
    "RECEIPT_NAME",
    "SCHEMA",
    "STATUS_FAIL",
    "STATUS_PASS",
    "RecordingProvider",
    "V023OneEpochDiagnosticError",
    "build_parser",
    "main",
    "run_diagnostic",
]
