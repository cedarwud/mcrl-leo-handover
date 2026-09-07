#!/usr/bin/env python3
"""Run the cheap P0/B2 C2 direction screen on live matched physics.

This is deliberately a development runner, not a D2 evidence runner.  It
uses one frozen Q1+Q3 lineage and two fixed physical anchors.  The default
``fast4`` panel bounds each opening/successor comparison to four actions; the
optional ``native28`` panel enumerates every legal opening action for the
selected focal user.  A negative or degenerate arm can therefore be discarded
before Q2 training or held-out evaluation.

The output may describe direction and support only.  It cannot authorize a
paper efficacy claim or replace full B2 confirmation.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
import time
from types import ModuleType
from typing import Any, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.env.action_contract import NO_OP_ACTION, NUM_ACTIONS  # noqa: E402
from mcrl.runtime.ee_axis_state import EE_AXIS_BASE_STATE_DIM  # noqa: E402
from mcrl.runtime.ee_axis_v07_c2_d2 import (  # noqa: E402
    D2_DEFAULT_KAPPA_BITS,
    D2_INTERVAL_S,
    D2_LAMBDA_BITS_PER_J,
)
from mcrl.runtime.ee_axis_v07_c2_fast_proxy import (  # noqa: E402
    select_b2_proxy_action_panel,
    successor_proxy_option_set_target,
)
from mcrl.runtime.ee_axis_v07_c2_focal_next import (  # noqa: E402
    focal_next_surplus_target,
)
from mcrl.runtime.ee_axis_v07_c2_policy import (  # noqa: E402
    focal_candidate_vector,
)


CLAIM_CEILING = "DEVELOPMENT_DIRECTION_SCREEN_ONLY__NOT_FINAL_EVIDENCE"
ANCHORS = (
    (2026104011, "early", (1, 2)),
    (2026104012, "late", (5, 6)),
)
RADIAL_START = EE_AXIS_BASE_STATE_DIM + NUM_ACTIONS
RADIAL_STOP = RADIAL_START + NUM_ACTIONS
ACTION_PANEL_MODES = ("fast4", "native28")

DEFAULT_TLE_ROOT = Path("~/demo/tle_data/starlink/tle").expanduser()
DEFAULT_PREREG = REPO / "artifacts/PREREG-FROZEN-2026-08-25-R2.json"
DEFAULT_MAIN = REPO / "artifacts/training-2026-08-25-rerun01/main"
DEFAULT_GATE = REPO / "artifacts/multi-catfish-v04-c3-learnability-20260901-r2"
DEFAULT_Q13_SOURCE = REPO / "artifacts/multi-catfish-v04-c3-source-20260901-r2"
DEFAULT_V03 = REPO / "artifacts/multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1"


class FastIterationError(RuntimeError):
    """The development screen cannot produce a comparable row."""


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise FastIterationError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _finite_nonnegative(value: object, *, field: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result < 0.0:
        raise FastIterationError(f"{field} must be finite and non-negative")
    return result


def _validate_native28_panel(
    *,
    panel: Sequence[int],
    legal_actions: np.ndarray,
    reference_action: int,
) -> tuple[int, ...]:
    """Fail closed unless a native panel is an exact legal-action set."""

    values = tuple(panel)
    legal = tuple(int(action) for action in np.asarray(legal_actions).tolist())
    if not legal:
        raise FastIterationError("native28 panel requires at least one legal action")
    if len(set(legal)) != len(legal):
        raise FastIterationError("native28 legal-action set contains duplicates")
    if any(type(action) is not int for action in values):
        raise FastIterationError("native28 panel contains a non-native action")
    if len(values) != len(legal) or len(set(values)) != len(values):
        raise FastIterationError("native28 panel contains duplicate or missing actions")
    if set(values) != set(legal):
        raise FastIterationError("native28 panel is not the exact legal-action set")
    if type(reference_action) is not int or reference_action not in values:
        raise FastIterationError("native28 panel does not include the legal reference")
    return values


def _native28_action_panel(decision: Any, *, focal_user: int) -> tuple[int, ...]:
    """Enumerate every legal native action exactly once for one focal user."""

    masks = np.asarray(getattr(decision, "masks", None))
    if masks.dtype != np.bool_ or masks.ndim != 2 or masks.shape[1] != NUM_ACTIONS:
        raise FastIterationError("native28 decision masks have the wrong shape/type")
    if type(focal_user) is not int or not 0 <= focal_user < masks.shape[0]:
        raise FastIterationError("native28 focal user is outside the decision")
    legal_actions = np.flatnonzero(masks[focal_user])
    actions = np.asarray(getattr(decision, "actions", None))
    if actions.ndim != 1 or actions.shape[0] != masks.shape[0]:
        raise FastIterationError("native28 decision actions have the wrong shape")
    reference_raw = actions[focal_user]
    if isinstance(reference_raw, (bool, np.bool_)) or not isinstance(
        reference_raw, (int, np.integer)
    ):
        raise FastIterationError("native28 reference action is not native")
    reference_action = int(reference_raw)
    panel = tuple(int(action) for action in legal_actions.tolist())
    return _validate_native28_panel(
        panel=panel,
        legal_actions=legal_actions,
        reference_action=reference_action,
    )


def _panel(
    observation: Any,
    decision: Any,
    q2_state: np.ndarray,
    *,
    focal_user: int,
    action_panel: str = "fast4",
) -> tuple[int, ...]:
    if action_panel == "native28":
        return _native28_action_panel(decision, focal_user=focal_user)
    if action_panel != "fast4":
        raise FastIterationError(f"unknown action panel mode: {action_panel}")
    radial = np.asarray(
        q2_state[focal_user, RADIAL_START:RADIAL_STOP], dtype=np.float64
    )
    selected = select_b2_proxy_action_panel(
        legal_mask=np.asarray(decision.masks[focal_user], dtype=np.bool_),
        reference_action=int(decision.actions[focal_user]),
        candidate_sinr=np.asarray(
            observation.candidate_sinr[focal_user], dtype=np.float64
        ),
        signed_range_rate_km_s=radial,
    )
    return selected.actions


def _select_focal_user(
    *,
    decision: Any,
    q2_state: np.ndarray,
    default_focal_user: int,
    mode: str,
) -> tuple[int, dict[str, object]]:
    """Choose one focal user from predecision motion only, never outcomes."""

    masks = np.asarray(decision.masks, dtype=np.bool_)
    actions = np.asarray(decision.actions, dtype=np.int64)
    radial = np.asarray(
        q2_state[:, RADIAL_START:RADIAL_STOP], dtype=np.float64
    )
    eligible = np.flatnonzero(np.count_nonzero(masks, axis=1) >= 3)
    if eligible.size < 1:
        raise FastIterationError("anchor has no focal user with at least 3 actions")
    if mode == "lowest-eligible":
        focal = int(default_focal_user)
        if focal not in eligible.tolist():
            raise FastIterationError("default focal is outside eligible users")
        return focal, {
            "mode": mode,
            "selected_user": focal,
            "selection_outcome_blind": True,
        }
    if mode != "motion-gap":
        raise FastIterationError("unknown focal selector mode")
    scores: list[tuple[int, float, float, float]] = []
    for user in eligible.tolist():
        reference = int(actions[user])
        if reference < 0 or not bool(masks[user, reference]):
            raise FastIterationError("eligible focal has invalid reference action")
        legal_radial = radial[user, masks[user]]
        reference_radial = float(radial[user, reference])
        most_approaching = float(np.min(legal_radial))
        opportunity = reference_radial - most_approaching
        scores.append((int(user), opportunity, reference_radial, most_approaching))
    # Greatest motion opportunity, then lowest user ID.  All inputs are
    # predecision geometry; no rate, power, target, or EE value is consulted.
    focal, opportunity, reference_radial, most_approaching = min(
        scores, key=lambda item: (-item[1], item[0])
    )
    return focal, {
        "mode": mode,
        "selected_user": focal,
        "motion_opportunity_km_s": opportunity,
        "reference_signed_range_rate_km_s": reference_radial,
        "most_approaching_signed_range_rate_km_s": most_approaching,
        "eligible_user_count": int(eligible.size),
        "selection_outcome_blind": True,
        "formula": "rho_reference-minus-minimum_legal_rho",
    }


def _physical_actions(
    observation: Any,
    actions: Sequence[int],
) -> tuple[tuple[int, int] | None, ...]:
    values: list[tuple[int, int] | None] = []
    for user, action in enumerate(actions):
        native = int(action)
        if native == NO_OP_ACTION:
            values.append(None)
            continue
        association = observation.candidates.slot_tables[user].association(native)
        values.append((int(association.norad_id), int(association.cell_id)))
    return tuple(values)


def _remap_nonfocal_tape(
    *,
    observation: Any,
    masks: np.ndarray,
    behavior_actions: np.ndarray,
    nonfocal_tape: Sequence[tuple[int, int] | None],
    focal_user: int,
) -> np.ndarray:
    remapped = np.asarray(behavior_actions, dtype=np.int64).copy()
    if len(nonfocal_tape) != remapped.size:
        raise FastIterationError("non-focal tape has the wrong user count")
    for user, key in enumerate(nonfocal_tape):
        if user == focal_user:
            continue
        mask = np.asarray(masks[user], dtype=np.bool_)
        if key is None:
            if np.any(mask):
                raise FastIterationError(
                    f"non-focal user {user} tape no-op is not branch-valid"
                )
            remapped[user] = NO_OP_ACTION
            continue
        table = observation.candidates.slot_tables[user]
        matches = np.flatnonzero(
            mask
            & (np.asarray(table.norad_ids, dtype=np.int64) == key[0])
            & (np.asarray(table.cell_ids, dtype=np.int64) == key[1])
        )
        if matches.size != 1:
            raise FastIterationError(
                f"non-focal physical tape unsupported for user {user}"
            )
        remapped[user] = int(matches[0])
    return remapped


def _raw_option_measurements(
    environment: Any,
    env_rng: np.random.Generator,
    *,
    base_actions: np.ndarray,
    masks: np.ndarray,
    focal_user: int,
    actions: Sequence[int],
) -> tuple[list[float], list[float], list[float]]:
    rates: list[float] = []
    full_power: list[float] = []
    without_power: list[float] = []
    for action in actions:
        vector = focal_candidate_vector(
            reference_actions=base_actions,
            masks=masks,
            focal_user=focal_user,
            candidate_action=int(action),
        )
        full = environment.evaluate_actions(vector, env_rng)
        removed = environment.evaluate_actions_without_user(
            vector, env_rng, focal_user=focal_user
        )
        rates.append(
            _finite_nonnegative(
                np.asarray(full.link_rate_bps, dtype=np.float64)[focal_user],
                field="focal rate",
            )
        )
        full_power.append(
            _finite_nonnegative(full.system_power_w, field="full power")
        )
        without_power.append(
            _finite_nonnegative(removed.system_power_w, field="without power")
        )
    return rates, full_power, without_power


def _b2_branch(
    *,
    live_v07: Any,
    runtime: Any,
    hybrid: Any,
    field: Any,
    source_seed: int,
    history: Sequence[np.ndarray],
    target_step: int,
    focal_user: int,
    opening_actions: np.ndarray,
    nonfocal_tape: Sequence[tuple[int, int] | None] | None,
) -> tuple[dict[str, object], tuple[tuple[int, int] | None, ...]]:
    wrapped, env_rng, _ = live_v07._replay_to_anchor(
        runtime,
        runtime.archive,
        source_seed=source_seed,
        field=field,
        history=history,
        target_step=target_step,
    )
    if live_v07._advance(wrapped, opening_actions, env_rng):
        raise FastIterationError("B2 successor is terminal")
    observation = wrapped.last_outcome.observation
    decision, q2_state = live_v07._decision(
        hybrid,
        None,
        wrapped,
        observation,
        interval_s=D2_INTERVAL_S,
        kappa_bits=D2_DEFAULT_KAPPA_BITS,
    )
    masks = np.asarray(decision.masks, dtype=np.bool_)
    if not np.any(masks[focal_user]):
        raise FastIterationError("B2 focal successor has no legal native action")
    behavior_actions = np.asarray(decision.actions, dtype=np.int64)
    if nonfocal_tape is None:
        tape = _physical_actions(observation, behavior_actions)
        base_actions = behavior_actions.copy()
    else:
        tape = tuple(nonfocal_tape)
        base_actions = _remap_nonfocal_tape(
            observation=observation,
            masks=masks,
            behavior_actions=behavior_actions,
            nonfocal_tape=tape,
            focal_user=focal_user,
        )
    actions = _panel(
        observation,
        decision,
        np.asarray(q2_state, dtype=np.float32),
        focal_user=focal_user,
    )
    rates, full, without = _raw_option_measurements(
        live_v07._environment(wrapped),
        env_rng,
        base_actions=base_actions,
        masks=masks,
        focal_user=focal_user,
        actions=actions,
    )
    return (
        {
            "actions": [int(action) for action in actions],
            "rates_bps": rates,
            "full_power_w": full,
            "without_focal_power_w": without,
        },
        tape,
    )


def _build_b1_reference_tape(
    *,
    b1_live: Any,
    live_v07: Any,
    runtime: Any,
    hybrid: Any,
    field: Any,
    source_seed: int,
    history: Sequence[np.ndarray],
    target_step: int,
    focal_user: int,
    reference_opening_actions: np.ndarray,
) -> Any:
    """Precommit the three-step Q1+Q3 physical tape before pair outcomes."""

    wrapped, env_rng, _ = live_v07._replay_to_anchor(
        runtime,
        runtime.archive,
        source_seed=source_seed,
        field=field,
        history=history,
        target_step=target_step,
    )
    if live_v07._advance(wrapped, reference_opening_actions, env_rng):
        raise FastIterationError("B1 reference opening terminated before k=1")
    decisions: list[np.ndarray] = []
    tables: list[tuple[Any, ...]] = []
    for offset in (1, 2, 3):
        observation = wrapped.last_outcome.observation
        decision, _q2_state = live_v07._decision(
            hybrid,
            None,
            wrapped,
            observation,
            interval_s=D2_INTERVAL_S,
            kappa_bits=D2_DEFAULT_KAPPA_BITS,
        )
        decisions.append(np.asarray(decision.actions, dtype=np.int64).copy())
        tables.append(tuple(observation.candidates.slot_tables))
        if offset < 3 and live_v07._advance(
            wrapped, np.asarray(decision.actions, dtype=np.int64), env_rng
        ):
            raise FastIterationError(
                f"B1 reference behavior terminated before k={offset + 1}"
            )
    return b1_live.precommit_q13_nonfocal_tape(
        reference_actions=tuple(decisions),
        reference_slot_tables=tuple(tables),
        focal_user=focal_user,
    )


def _b1_pair(
    *,
    b1_live: Any,
    live_v07: Any,
    runtime: Any,
    field: Any,
    source_seed: int,
    history: Sequence[np.ndarray],
    target_step: int,
    focal_user: int,
    reference_opening_actions: np.ndarray,
    candidate_opening_actions: np.ndarray,
    anchor_observation: Any,
    reference_tape: Any,
) -> Any:
    reference_branch, reference_rng, _ = live_v07._replay_to_anchor(
        runtime,
        runtime.archive,
        source_seed=source_seed,
        field=field,
        history=history,
        target_step=target_step,
    )
    candidate_branch, candidate_rng, _ = live_v07._replay_to_anchor(
        runtime,
        runtime.archive,
        source_seed=source_seed,
        field=field,
        history=history,
        target_step=target_step,
    )

    def validation_action(
        _branch: object, observation: object, _offset: int
    ) -> int:
        mask = np.asarray(getattr(observation, "masks")[focal_user], dtype=np.bool_)
        legal = np.flatnonzero(mask)
        if legal.size < 1:
            raise FastIterationError(
                "focal removal validation has no legal native carrier"
            )
        return int(legal[0])

    return b1_live.capture_b1_pair(
        reference_branch=reference_branch,
        candidate_branch=candidate_branch,
        reference_rng=reference_rng,
        candidate_rng=candidate_rng,
        reference_opening_actions=reference_opening_actions,
        candidate_opening_actions=candidate_opening_actions,
        reference_opening_physical_actions=_physical_actions(
            anchor_observation, reference_opening_actions
        ),
        candidate_opening_physical_actions=_physical_actions(
            anchor_observation, candidate_opening_actions
        ),
        reference_tape=reference_tape,
        focal_user=focal_user,
        lambda_bits_per_j=D2_LAMBDA_BITS_PER_J,
        interval_s=D2_INTERVAL_S,
        focal_removal_validation_action=validation_action,
    )


def _screen_anchor(
    *,
    live_v07: Any,
    runner_v07: Any,
    runner_v06: Any,
    runtime: Any,
    simulator_manifest_sha256: str,
    source_seed: int,
    window: str,
    eligible_steps: tuple[int, ...],
    lineage: str,
    b1_live: Any,
    run_b1: bool,
    run_b2: bool,
    focal_mode: str,
    action_panel: str,
) -> dict[str, object]:
    started = time.monotonic()
    field = runner_v06._physical_world_field(
        checkpoint_sha256=runtime.checkpoint_sha256,
        source_manifest_sha256=simulator_manifest_sha256,
        simulator_prereg_file_sha256=runtime.prereg_file_sha256,
        source_seed=source_seed,
    )
    selected = runner_v07._scan_carrier_anchor(
        runtime,
        source_seed=source_seed,
        field=field,
        eligible_steps=eligible_steps,
    )
    hybrid = runtime.hybrids[lineage]
    history, decision, q2_state = live_v07.bind_behavior_action_at_anchor(
        runtime,
        runtime.archive,
        hybrid,
        None,
        source_seed=source_seed,
        field=field,
        carrier_history=selected.carrier_history,
        target_step=selected.target_step,
        interval_s=D2_INTERVAL_S,
        kappa_bits=D2_DEFAULT_KAPPA_BITS,
    )
    wrapped, _rng, observation = live_v07._replay_to_anchor(
        runtime,
        runtime.archive,
        source_seed=source_seed,
        field=field,
        history=history,
        target_step=selected.target_step,
    )
    del wrapped
    focal, focal_selector = _select_focal_user(
        decision=decision,
        q2_state=np.asarray(q2_state, dtype=np.float32),
        default_focal_user=selected.focal_user,
        mode=focal_mode,
    )
    opening_panel = _panel(
        observation,
        decision,
        np.asarray(q2_state, dtype=np.float32),
        focal_user=focal,
        action_panel=action_panel,
    )
    reference_actions = np.asarray(decision.actions, dtype=np.int64)
    reference_action = int(reference_actions[focal])

    reference_b1_tape = (
        _build_b1_reference_tape(
            b1_live=b1_live,
            live_v07=live_v07,
            runtime=runtime,
            hybrid=hybrid,
            field=field,
            source_seed=source_seed,
            history=history,
            target_step=selected.target_step,
            focal_user=focal,
            reference_opening_actions=reference_actions,
        )
        if run_b1
        else None
    )

    reference_p0 = live_v07._measure_branch_successor(
        runtime,
        runtime.archive,
        hybrid,
        None,
        source_seed=source_seed,
        field=field,
        history=history,
        target_step=selected.target_step,
        focal_user=focal,
        opening_actions=reference_actions,
        interval_s=D2_INTERVAL_S,
        kappa_bits=D2_DEFAULT_KAPPA_BITS,
    )
    if run_b2:
        reference_b2, tape = _b2_branch(
            live_v07=live_v07,
            runtime=runtime,
            hybrid=hybrid,
            field=field,
            source_seed=source_seed,
            history=history,
            target_step=selected.target_step,
            focal_user=focal,
            opening_actions=reference_actions,
            nonfocal_tape=None,
        )
    else:
        reference_b2 = None
        tape = None

    rows: list[dict[str, object]] = []
    for action in opening_panel:
        opening = focal_candidate_vector(
            reference_actions=reference_actions,
            masks=decision.masks,
            focal_user=focal,
            candidate_action=action,
        )
        candidate_p0 = (
            reference_p0
            if action == reference_action
            else live_v07._measure_branch_successor(
                runtime,
                runtime.archive,
                hybrid,
                None,
                source_seed=source_seed,
                field=field,
                history=history,
                target_step=selected.target_step,
                focal_user=focal,
                opening_actions=opening,
                interval_s=D2_INTERVAL_S,
                kappa_bits=D2_DEFAULT_KAPPA_BITS,
            )
        )
        p0 = focal_next_surplus_target(
            lambda_bits_per_j=D2_LAMBDA_BITS_PER_J,
            interval_s=D2_INTERVAL_S,
            candidate_focal_rate_bps=candidate_p0.focal_rate_bps,
            reference_focal_rate_bps=reference_p0.focal_rate_bps,
            candidate_full_power_w=candidate_p0.full_power_w,
            candidate_without_focal_power_w=candidate_p0.without_focal_power_w,
            reference_full_power_w=reference_p0.full_power_w,
            reference_without_focal_power_w=reference_p0.without_focal_power_w,
        )
        if run_b2:
            if action == reference_action:
                candidate_b2 = reference_b2
            else:
                candidate_b2, _ = _b2_branch(
                    live_v07=live_v07,
                    runtime=runtime,
                    hybrid=hybrid,
                    field=field,
                    source_seed=source_seed,
                    history=history,
                    target_step=selected.target_step,
                    focal_user=focal,
                    opening_actions=opening,
                    nonfocal_tape=tape,
                )
            assert candidate_b2 is not None and reference_b2 is not None
            b2 = successor_proxy_option_set_target(
                lambda_bits_per_j=D2_LAMBDA_BITS_PER_J,
                interval_s=D2_INTERVAL_S,
                candidate_actions=candidate_b2["actions"],
                candidate_action_rates_bps=candidate_b2["rates_bps"],
                candidate_action_full_power_w=candidate_b2["full_power_w"],
                candidate_action_without_focal_power_w=candidate_b2[
                    "without_focal_power_w"
                ],
                reference_actions=reference_b2["actions"],
                reference_action_rates_bps=reference_b2["rates_bps"],
                reference_action_full_power_w=reference_b2["full_power_w"],
                reference_action_without_focal_power_w=reference_b2[
                    "without_focal_power_w"
                ],
            )
            b2_value: float | None = b2.z2_proxy_surplus_bits
            b2_candidate_panel = list(b2.candidate_actions)
            b2_reference_panel = list(b2.reference_actions)
            b2_error: str | None = None
        else:
            b2_value = None
            b2_candidate_panel = []
            b2_reference_panel = []
            b2_error = "SKIPPED_AFTER_FAST_REJECT"
        b1_value: float | None
        b1_capture: dict[str, object] | None
        b1_error: str | None
        if not run_b1:
            b1_value = None
            b1_capture = None
            b1_error = "SKIPPED_AFTER_Q13_A_FAST_REJECT"
        elif action == reference_action:
            b1_value = 0.0
            b1_capture = None
            b1_error = None
        else:
            try:
                captured = _b1_pair(
                    b1_live=b1_live,
                    live_v07=live_v07,
                    runtime=runtime,
                    field=field,
                    source_seed=source_seed,
                    history=history,
                    target_step=selected.target_step,
                    focal_user=focal,
                    reference_opening_actions=reference_actions,
                    candidate_opening_actions=opening,
                    anchor_observation=observation,
                    reference_tape=reference_b1_tape,
                )
                b1_value = captured.z2_focal_segment_surplus_bits
                b1_capture = captured.as_mapping()
                b1_error = None
            except b1_live.B1FastLiveError as error:
                b1_value = None
                b1_capture = None
                b1_error = str(error)
        rows.append(
            {
                "opening_action": int(action),
                "is_reference": action == reference_action,
                "p0_surplus_bits": p0.z2_focal_next_surplus_bits,
                "b1_surplus_bits": b1_value,
                "b1_supported": b1_value is not None,
                "b1_error": b1_error,
                "b1_capture": b1_capture,
                "b2_proxy_surplus_bits": b2_value,
                "b2_supported": b2_value is not None,
                "b2_error": b2_error,
                "b2_candidate_panel": b2_candidate_panel,
                "b2_reference_panel": b2_reference_panel,
            }
        )

    def _summary(field_name: str) -> dict[str, object]:
        nonreference = [
            float(row[field_name]) for row in rows if not row["is_reference"]
        ]
        return {
            "nonreference_count": len(nonreference),
            "positive_count": sum(value > 0.0 for value in nonreference),
            "negative_count": sum(value < 0.0 for value in nonreference),
            "zero_count": sum(value == 0.0 for value in nonreference),
            "minimum_bits": min(nonreference) if nonreference else 0.0,
            "maximum_bits": max(nonreference) if nonreference else 0.0,
            "nondegenerate": len(set(nonreference)) > 1,
        }

    def _optional_summary(field_name: str) -> dict[str, object]:
        values = [
            row[field_name]
            for row in rows
            if not row["is_reference"] and row[field_name] is not None
        ]
        numeric = [float(value) for value in values]
        attempted = sum(not row["is_reference"] for row in rows)
        return {
            "attempted_nonreference_count": attempted,
            "supported_count": len(numeric),
            "unsupported_count": attempted - len(numeric),
            "positive_count": sum(value > 0.0 for value in numeric),
            "negative_count": sum(value < 0.0 for value in numeric),
            "zero_count": sum(value == 0.0 for value in numeric),
            "minimum_bits": min(numeric) if numeric else None,
            "maximum_bits": max(numeric) if numeric else None,
            "nondegenerate": len(set(numeric)) > 1,
        }

    return {
        "source_seed": source_seed,
        "window": window,
        "target_step": selected.target_step,
        "focal_user": focal,
        "focal_selector": focal_selector,
        "lineage": lineage,
        "action_panel_mode": action_panel,
        "action_panel_actions": list(opening_panel),
        "reference_action": reference_action,
        "opening_panel": list(opening_panel),
        "q2_state_float32_hex": [
            float(value).hex()
            for value in np.asarray(q2_state[focal], dtype=np.float32).tolist()
        ],
        "action_mask": [bool(value) for value in decision.masks[focal].tolist()],
        "rows": rows,
        "p0": _summary("p0_surplus_bits"),
        "b1": _optional_summary("b1_surplus_bits"),
        "b1_run": run_b1,
        "b2_proxy": _optional_summary("b2_proxy_surplus_bits"),
        "b2_run": run_b2,
        "elapsed_wall_seconds": time.monotonic() - started,
    }


def run(args: argparse.Namespace) -> dict[str, object]:
    runner_v07 = _load("v07_fast_runner_authority", HERE / "run_v07_c2_d2.py")
    b1_live = _load("v07_c2_b1_fast_live", HERE / "v07_c2_b1_fast_live.py")
    live_v06, runner_v06, live_v07, simulator_manifest_sha256 = (
        runner_v07._modules()
    )
    started = time.monotonic()
    anchors: list[dict[str, object]] = []
    requested = ANCHORS
    if args.anchor:
        parsed: list[tuple[int, str, tuple[int, ...]]] = []
        for raw in args.anchor:
            try:
                seed_text, window = raw.split(":", 1)
                source_seed = int(seed_text)
            except (ValueError, TypeError) as error:
                raise FastIterationError(
                    "--anchor must be formatted SEED:early or SEED:late"
                ) from error
            if window == "early":
                eligible = (1, 2)
            elif window == "late":
                eligible = (5, 6)
            else:
                raise FastIterationError("--anchor window must be early or late")
            parsed.append((source_seed, window, eligible))
        requested = tuple(parsed)
    with live_v06.authenticated_runtime(
        tle_root=args.tle_root,
        prereg_path=args.prereg,
        main_dir=args.main_dir,
        gate_dir=args.gate_dir,
        source_dir=args.q13_source_dir,
        v03_root=args.v03_root,
    ) as runtime:
        for source_seed, window, eligible_steps in requested:
            print(
                json.dumps(
                    {
                        "status": "FAST_ANCHOR_STARTED",
                        "lineage": args.lineage,
                        "source_seed": source_seed,
                        "window": window,
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
            anchors.append(
                _screen_anchor(
                    live_v07=live_v07,
                    runner_v07=runner_v07,
                    runner_v06=runner_v06,
                    runtime=runtime,
                    simulator_manifest_sha256=simulator_manifest_sha256,
                    source_seed=source_seed,
                    window=window,
                    eligible_steps=eligible_steps,
                    lineage=args.lineage,
                    b1_live=b1_live,
                    run_b1=not args.skip_b1,
                    run_b2=not args.skip_b2,
                    focal_mode=args.focal_mode,
                    action_panel=args.action_panel,
                )
            )
            partial = {
                "schema": "multi-catfish-mcrl-v07-c2-fast-live-direction-screen-v1",
                "claim_ceiling": CLAIM_CEILING,
                "status": "RUNNING",
                "lineage": args.lineage,
                "action_panel_mode": args.action_panel,
                "anchors": anchors,
                "action_panel_actions": [
                    anchor["action_panel_actions"] for anchor in anchors
                ],
                "elapsed_wall_seconds": time.monotonic() - started,
                "training": False,
                "heldout_evaluation": False,
                "test_split_opened": False,
                "b2_full_native_28_confirmation": False,
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(partial, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            print(
                json.dumps(
                    {
                        "status": "FAST_ANCHOR_COMPLETE",
                        "lineage": args.lineage,
                        "source_seed": source_seed,
                        "window": window,
                        "elapsed_wall_seconds": anchors[-1][
                            "elapsed_wall_seconds"
                        ],
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
    payload: dict[str, object] = {
        "schema": "multi-catfish-mcrl-v07-c2-fast-live-direction-screen-v1",
        "claim_ceiling": CLAIM_CEILING,
        "status": "COMPLETE",
        "lineage": args.lineage,
        "action_panel_mode": args.action_panel,
        "anchors": anchors,
        "action_panel_actions": [
            anchor["action_panel_actions"] for anchor in anchors
        ],
        "elapsed_wall_seconds": time.monotonic() - started,
        "training": False,
        "heldout_evaluation": False,
        "test_split_opened": False,
        "b2_full_native_28_confirmation": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tle-root", type=Path, default=DEFAULT_TLE_ROOT)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--main-dir", type=Path, default=DEFAULT_MAIN)
    parser.add_argument("--gate-dir", type=Path, default=DEFAULT_GATE)
    parser.add_argument("--q13-source-dir", type=Path, default=DEFAULT_Q13_SOURCE)
    parser.add_argument("--v03-root", type=Path, default=DEFAULT_V03)
    parser.add_argument(
        "--lineage", choices=("q13-a", "q13-b", "q13-c"), default="q13-a"
    )
    parser.add_argument(
        "--anchor",
        action="append",
        help="development anchor SEED:early or SEED:late; repeat as needed",
    )
    parser.add_argument(
        "--skip-b1",
        action="store_true",
        help="skip B1 only after its q13-a two-anchor development rejection",
    )
    parser.add_argument(
        "--skip-b2",
        action="store_true",
        help="skip B2 after its development rejection when collecting P0 coverage",
    )
    parser.add_argument(
        "--focal-mode",
        choices=("lowest-eligible", "motion-gap"),
        default="lowest-eligible",
        help="outcome-blind focal selector for the development screen",
    )
    parser.add_argument(
        "--action-panel",
        choices=ACTION_PANEL_MODES,
        default="fast4",
        help="opening P0 panel: bounded fast4 (default) or exact native28",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run(args)
    print(
        json.dumps(
            {
                "status": "FAST_DIRECTION_SCREEN_COMPLETE",
                "anchors": len(result["anchors"]),
                "elapsed_wall_seconds": result["elapsed_wall_seconds"],
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
