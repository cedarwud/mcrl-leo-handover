#!/usr/bin/env python3
"""Materialize one V0.5 C2 controlled-tape physical probe.

This runner is intentionally a new consumer; it does not modify or reuse the
sealed V0.4 Phase-B rows.  It authenticates the existing Phase-A/Q13 inputs,
creates one frozen reference tape per anchor (either the deployed Main policy
or the frozen Q1+Q3 policy, selected explicitly at the CLI), and then replays
one candidate branch with the same physical actions for every nonfocal user.
Only the focal hold/release action is changed.  A missing or duplicated
physical binding fails the probe closed.  The runner does not select a tape
policy winner.

The command performs physical source generation only.  It never trains a
network, opens TEST, computes held-out EE, or launches a long update run.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from types import ModuleType
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for path in (HERE, REPO, REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module {name}: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


phase_b = _load_module(
    "mcrl_v05_c2_controlled_tape_phase_b",
    HERE / "run_v04_c2_phase_b.py",
)
# The server pilot may load the additive V0.5 seam from outside ``src/mcrl``.
# That keeps the sealed V0.4 whole-tree source manifest byte-exact while this
# new consumer authenticates it.  The module still receives its package name,
# so its relative imports retain normal ``mcrl.runtime`` semantics.
_controlled_override = os.environ.get("MCRL_V05_CONTROLLED_TAPE_MODULE")
if _controlled_override:
    import mcrl.runtime  # noqa: E402,F401

    controlled = _load_module(
        "mcrl.runtime.ee_axis_v05_c2_controlled_tape",
        Path(_controlled_override).expanduser().resolve(),
    )
else:
    from mcrl.runtime import ee_axis_v05_c2_controlled_tape as controlled  # noqa: E402


DEFAULT_PHASE_A_DIR = phase_b.DEFAULT_PHASE_A_DIR
DEFAULT_GATE_DIR = phase_b.DEFAULT_GATE_DIR
DEFAULT_C3_SOURCE_DIR = phase_b.DEFAULT_C3_SOURCE_DIR
DEFAULT_V03_ROOT = phase_b.DEFAULT_V03_ROOT
DEFAULT_PREREG = phase_b.DEFAULT_PREREG
DEFAULT_TLE_ROOT = phase_b.DEFAULT_TLE_ROOT


class ControlledTapeProbeError(RuntimeError):
    """A controlled-tape physical probe failed closed."""


Q13_POLICY_COMPONENT_SCHEMA = "multi-catfish-mcrl-v05-q13-policy-components-v1"
MAIN_POLICY_COMPONENT_SCHEMA = "multi-catfish-mcrl-v05-main-policy-components-v1"


def _canonical_sha256(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def _network_parameter_sha256(network: Any) -> str:
    """Hash one Q network without optimizer, pickle, or sibling routes."""

    state = getattr(network, "state_dict", None)
    if not callable(state):
        raise ControlledTapeProbeError("Q policy component lacks a state_dict")
    values = state()
    if not isinstance(values, Mapping) or not values:
        raise ControlledTapeProbeError("Q policy component state_dict is malformed")
    digest = hashlib.sha256()
    for name in sorted(values):
        tensor = values[name]
        detach = getattr(tensor, "detach", None)
        if not callable(detach):
            raise ControlledTapeProbeError("Q policy component contains a non-tensor")
        array = tensor.detach().cpu().contiguous().numpy()
        metadata = json.dumps(
            {
                "name": str(name),
                "dtype": array.dtype.str,
                "shape": list(array.shape),
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("ascii")
        raw = array.tobytes(order="C")
        digest.update(len(metadata).to_bytes(8, "big"))
        digest.update(metadata)
        digest.update(len(raw).to_bytes(8, "big"))
        digest.update(raw)
    return digest.hexdigest()


def _reference_policy_components(
    *,
    tape_policy: str,
    main_policy_sha256: str,
    hybrid: Any | None,
    initialization_seed: int | None,
) -> dict[str, object]:
    if tape_policy == "main":
        payload: dict[str, object] = {
            "schema": MAIN_POLICY_COMPONENT_SCHEMA,
            "policy_kind": "main",
            "main_policy_sha256": main_policy_sha256,
        }
    elif tape_policy == "q13":
        if hybrid is None or initialization_seed is None:
            raise ControlledTapeProbeError("Q1+Q3 component receipt requires a hybrid seed")
        q_nets = getattr(hybrid, "q_nets", None)
        if q_nets is None or len(q_nets) != 3:
            raise ControlledTapeProbeError("Q1+Q3 hybrid must expose exactly three Q networks")
        payload = {
            "schema": Q13_POLICY_COMPONENT_SCHEMA,
            "policy_kind": "q1-plus-q3",
            "initialization_seed": int(initialization_seed),
            "q1_parameters_sha256": _network_parameter_sha256(q_nets[0]),
            "q3_parameters_sha256": _network_parameter_sha256(q_nets[2]),
            "q2_excluded_from_policy": True,
        }
    else:
        raise ControlledTapeProbeError(f"unknown tape policy: {tape_policy}")
    return {**payload, "policy_components_sha256": _canonical_sha256(payload)}


def _validate_reference_policy_components(
    value: Mapping[str, object],
    *,
    tape_policy: str,
    reference_policy_sha256: str,
) -> dict[str, object]:
    components = dict(value)
    claimed = components.pop("policy_components_sha256", None)
    if claimed != _canonical_sha256(components) or claimed != reference_policy_sha256:
        raise ControlledTapeProbeError("reference policy-component digest disagrees")
    if tape_policy == "main":
        if (
            components.get("schema") != MAIN_POLICY_COMPONENT_SCHEMA
            or components.get("policy_kind") != "main"
            or set(components) != {"schema", "policy_kind", "main_policy_sha256"}
        ):
            raise ControlledTapeProbeError("Main policy-component receipt is malformed")
    elif tape_policy == "q13":
        required = {
            "schema",
            "policy_kind",
            "initialization_seed",
            "q1_parameters_sha256",
            "q3_parameters_sha256",
            "q2_excluded_from_policy",
        }
        if (
            components.get("schema") != Q13_POLICY_COMPONENT_SCHEMA
            or components.get("policy_kind") != "q1-plus-q3"
            or components.get("q2_excluded_from_policy") is not True
            or set(components) != required
        ):
            raise ControlledTapeProbeError("Q1+Q3 policy-component receipt is malformed")
    else:
        raise ControlledTapeProbeError(f"unknown tape policy: {tape_policy}")
    return {**components, "policy_components_sha256": claimed}


def _trace_arrays(trace: list[Any]) -> tuple[np.ndarray, np.ndarray]:
    rates = np.asarray([step.link_rate_bps for step in trace], dtype=np.float64)
    power = np.asarray([step.system_power_w for step in trace], dtype=np.float64)
    return rates, power


def _branch_slot_tables(backend: Any, branch: Any) -> tuple[Any, ...]:
    users = len(branch.states)
    tables = tuple(backend._slot_tables(branch.observation, users=users))
    if len(tables) != users:
        raise ControlledTapeProbeError("branch slot-table count disagrees with users")
    return tables


def _materialize_controlled_pair(
    *,
    prepared: Any,
    source_seed: int,
    hybrid: Any | None,
    modules: Mapping[str, Any],
    lambda_bits_per_j: float,
    interval_s: float,
    anchor_schedule_sha256: str,
    source_manifest_sha256: str,
    reference_policy_sha256: str,
    reference_policy_components: Mapping[str, object],
    tape_policy: str,
) -> dict[str, object]:
    """Run one reference-tape/candidate pair and return a sealed mapping."""

    if tape_policy not in {"main", "q13"}:
        raise ControlledTapeProbeError(f"unknown tape policy: {tape_policy}")
    if tape_policy == "q13" and hybrid is None:
        raise ControlledTapeProbeError("Q1+Q3 tape policy requires a loaded hybrid")
    if type(source_seed) is not int or source_seed < 0:
        raise ControlledTapeProbeError("source_seed must be a nonnegative exact integer")
    policy_components = _validate_reference_policy_components(
        reference_policy_components,
        tape_policy=tape_policy,
        reference_policy_sha256=reference_policy_sha256,
    )
    backend = modules["backend"]
    anchor = prepared.anchor
    if int(anchor.evaluation_seed) != source_seed:
        raise ControlledTapeProbeError(
            "scheduled source seed disagrees with the materialized opening anchor"
        )
    field, field_receipt = backend._derive_fading_field(anchor)
    if field is None or not isinstance(field_receipt, Mapping):
        raise ControlledTapeProbeError("V0.5 requires keyed common-random fading")
    common_field_sha256 = str(field.root_digest)
    rngs, _initial_rng_receipt = backend._derive_forecast_rngs(
        anchor,
        fading_field_receipt=field_receipt,
    )
    reference = backend._branch_from_anchor(
        anchor,
        role="reference",
        env_rng=rngs["reference_env"],
        mobility_rng=rngs["reference_mobility"],
        fading_field=field,
    )
    candidate = backend._branch_from_anchor(
        anchor,
        role="candidate",
        env_rng=rngs["candidate_env"],
        mobility_rng=rngs["candidate_mobility"],
        fading_field=field,
    )
    reference_trace: list[Any] = []
    candidate_trace: list[Any] = []
    reference_slot_tables: list[tuple[Any, ...]] = []
    candidate_slot_tables: list[tuple[Any, ...]] = []
    reference_decisions: list[dict[str, object]] = []
    support_counts: list[int] = []
    holding = True
    release_offset: int | None = None
    release_reason: str | None = None
    focal = int(anchor.focal_user)

    for offset in range(controlled.TEMPORAL_HORIZON_STEPS):
        reference_slot_tables.append(_branch_slot_tables(backend, reference))
        candidate_slot_tables.append(_branch_slot_tables(backend, candidate))
        if offset == 0:
            reference_actions = np.asarray(anchor.main_actions, dtype=np.int32)
            reference_physical = tuple(anchor.main_physical_actions)
        else:
            if tape_policy == "q13":
                assert hybrid is not None
                decision = phase_b._select_frozen_q13_continuation(
                    hybrid,
                    reference.wrapped,
                    reference.observation,
                    interval_s=interval_s,
                    kappa_bits=float(hybrid.v04_config.kappa_bits),
                )
                reference_decisions.append(
                    phase_b._decision_mapping(decision, offset=offset)
                )
                reference_actions = np.asarray(decision.actions, dtype=np.int32)
                reference_physical = backend._physical_vector(
                    reference_actions.tolist(),
                    reference.observation,
                    users=len(reference.states),
                )
            else:
                reference_actions, reference_physical = backend._main_actions(
                    anchor.trainer,
                    reference,
                )
                reference_decisions.append(
                    {
                        "offset": offset,
                        "policy": "main",
                        "actions": [int(value) for value in reference_actions],
                    }
                )

        if holding:
            count = backend._candidate_support_count(
                candidate.observation,
                focal_user=focal,
                candidate_key=prepared.candidate_key,
            )
            support_counts.append(int(count))
            if offset == 0 and count != 1:
                raise ControlledTapeProbeError(
                    "opening candidate physical action is not uniquely supported"
                )
            if offset > 0 and count != 1:
                holding = False
                release_offset = offset
                release_reason = "support_expired"
            elif offset == controlled.TEMPORAL_HORIZON_STEPS - 1:
                holding = False
                release_offset = offset
                release_reason = "horizon"
        else:
            count = backend._candidate_support_count(
                candidate.observation,
                focal_user=focal,
                candidate_key=prepared.candidate_key,
            )
            support_counts.append(int(count))

        # While the focal hold is active, the reference focal key is not a
        # required candidate binding.  Replace just that physical component
        # before remapping; every nonfocal component still comes from the
        # frozen reference tape.  Once released, the complete taped vector is
        # required, so a missing/duplicate focal binding fails closed too.
        candidate_taped_physical = list(reference_physical)
        if holding:
            candidate_taped_physical[focal] = prepared.candidate_key
        candidate_taped_actions = np.asarray(
            controlled.remap_physical_actions_for_branch(
                tuple(candidate_taped_physical),
                candidate_slot_tables[-1],
                field=f"candidate_slot_tables[{offset}]",
            ),
            dtype=np.int32,
        )

        executed, _executed_physical = backend._compose_candidate_actions(
            observation=candidate.observation,
            main_actions=candidate_taped_actions,
            main_physical=tuple(candidate_taped_physical),
            candidate_key=prepared.candidate_key,
            focal_user=focal,
            offset=offset,
            hold=holding,
        )
        reference_trace.append(
            backend._step_payload(
                reference,
                offset=offset,
                detached_main_actions=reference_actions.tolist(),
                detached_main_physical=reference_physical,
                executed_actions=reference_actions.tolist(),
            )
        )
        candidate_trace.append(
            backend._step_payload(
                candidate,
                offset=offset,
                detached_main_actions=candidate_taped_actions.tolist(),
                detached_main_physical=tuple(candidate_taped_physical),
                executed_actions=executed.tolist(),
                held_physical_key=prepared.candidate_key,
                held_key_match_count=int(support_counts[-1]),
                release_offset=release_offset,
                release_reason=release_reason,
            )
        )

    if release_offset is None or release_reason is None:
        raise ControlledTapeProbeError("controlled tape did not produce one release")
    # Match the existing forecast receipt convention: bind one final release
    # decision to every candidate trace step after the complete support scan.
    candidate_trace = [
        phase_b.replace(
            payload,
            held_physical_key=prepared.candidate_key,
            held_key_match_count=support_counts[payload.offset],
            release_offset=release_offset,
            release_reason=release_reason,
        )
        for payload in candidate_trace
    ]

    reference_raw = phase_b._trace_mapping(reference_trace)
    candidate_raw = phase_b._trace_mapping(candidate_trace)
    tape = controlled.build_reference_action_tape(
        reference_raw,
        anchor_sha256=anchor.anchor_sha256,
        reference_policy_sha256=reference_policy_sha256,
        common_random_field_sha256=common_field_sha256,
        focal_user=focal,
    )
    plan = controlled.remap_controlled_tape_pair(
        tape,
        reference_slot_tables,
        candidate_slot_tables,
        held_physical_key=prepared.candidate_key,
        release_offset=release_offset,
        release_reason=release_reason,
        support_counts=support_counts,
    )
    # The persisted plan is an audit receipt for the actions actually sent to
    # the simulator, not merely a re-computation from slot tables.
    for index, (plan_step, reference_step, candidate_step) in enumerate(
        zip(plan.steps, reference_trace, candidate_trace, strict=True)
    ):
        if tuple(plan_step.reference_actions) != tuple(reference_step.executed_actions):
            raise ControlledTapeProbeError("reference action receipt disagrees with simulator trace")
        if tuple(plan_step.candidate_actions) != tuple(candidate_step.executed_actions):
            raise ControlledTapeProbeError("candidate action receipt disagrees with simulator trace")

    reference_rates, reference_power = _trace_arrays(reference_trace)
    candidate_rates, candidate_power = _trace_arrays(candidate_trace)
    target = controlled.build_controlled_tape_target(
        tape_sha256=tape.tape_sha256,
        reference_rates_bps=reference_rates,
        candidate_rates_bps=candidate_rates,
        reference_system_power_w=reference_power,
        candidate_system_power_w=candidate_power,
        lambda_bits_per_j=lambda_bits_per_j,
        interval_s=interval_s,
    )
    return {
        "schema": "multi-catfish-mcrl-v05-c2-controlled-tape-physical-row-v2",
        "source_route": "C2",
        "tape_policy": tape_policy,
        "anchor_sha256": anchor.anchor_sha256,
        "anchor_schedule_sha256": anchor_schedule_sha256,
        "source_manifest_sha256": source_manifest_sha256,
        "source_seed": int(source_seed),
        "evaluation_seed": int(anchor.evaluation_seed),
        "initialization_seed": (
            None if hybrid is None else int(hybrid.initialization_seed)
        ),
        "focal_user": focal,
        "candidate_physical_key": list(prepared.candidate_key),
        "reference_policy_sha256": reference_policy_sha256,
        "reference_policy_components": policy_components,
        "common_random_field_sha256": common_field_sha256,
        "tape": tape.as_mapping(),
        "pair_plan": plan.as_mapping(tape),
        "target": target.as_mapping(),
        "raw_trace": {
            "reference": reference_raw,
            "candidate": candidate_raw,
            "reference_policy_decisions": reference_decisions,
            "support_counts": support_counts,
            "release_offset": release_offset,
            "release_reason": release_reason,
            "continuation_start_offset": 1,
        },
        "training_run": False,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
    }

def _select_batch_anchors(prepared_schedule: Any, *, count: int) -> tuple[Any, ...]:
    """Select a deterministic, outcome-blind anchor prefix for a short screen."""

    if count != 12:
        raise ControlledTapeProbeError(
            "the lockstep short screen is fixed at exactly 12 anchors"
        )
    anchors = tuple(
        sorted(
            prepared_schedule.anchors,
            key=lambda anchor: (
                int(anchor.source_seed),
                int(anchor.anchor_step),
                int(anchor.focal_user),
                str(anchor.anchor_sha256),
            ),
        )
    )
    if len(anchors) < count:
        raise ControlledTapeProbeError(
            f"sealed Phase-A schedule has only {len(anchors)} anchors; need {count}"
        )
    return anchors[:count]


def _scheduled_first_candidate(anchor: Any) -> tuple[int, int]:
    """Use the first preregistered legal non-Main key, without outcomes."""

    candidates = tuple(anchor.candidate_physical_keys)
    if not candidates:
        raise ControlledTapeProbeError(
            f"anchor {anchor.anchor_sha256} has no scheduled candidate key"
        )
    key = tuple(int(value) for value in candidates[0])
    if len(key) != 2:
        raise ControlledTapeProbeError("scheduled candidate physical key is malformed")
    return key


def _materialize_one_anchor(
    *,
    anchor: Any,
    candidate_key: tuple[int, int],
    hybrid: Any | None,
    modules: Mapping[str, Any],
    context: Mapping[str, Any],
    reference_policy_sha256: str,
    reference_policy_components: Mapping[str, object],
    tape_policy: str,
) -> dict[str, object]:
    """Replay and materialize one anchor in lockstep.

    The candidate slot tables are captured immediately before each candidate
    step inside ``_materialize_controlled_pair``.  They are never precomputed
    from a future candidate trace, so state-dependent topology cannot create a
    circular dependency.
    """

    if candidate_key not in tuple(
        tuple(int(value) for value in key) for key in anchor.candidate_physical_keys
    ):
        raise ControlledTapeProbeError(
            "candidate key is not one of the sealed legal non-Main siblings"
        )
    replay = phase_b.support._replay_main_to_step(
        source_seed=anchor.source_seed,
        target_step=anchor.anchor_step,
        modules=modules,
        context=context,
    )
    service = phase_b.support._real_service_for_sealed_anchor(
        anchor=anchor,
        replay=replay,
        modules=modules,
        context=context,
    )
    prepared = service.prepare_one_candidate(
        focal_user=anchor.focal_user,
        candidate_key=candidate_key,
    )
    lambda_bits_per_j, interval_s, _calibration_sha = phase_b.support._production_calibration(modules)
    return _materialize_controlled_pair(
        prepared=prepared,
        source_seed=int(anchor.source_seed),
        hybrid=hybrid,
        modules=modules,
        lambda_bits_per_j=lambda_bits_per_j,
        interval_s=interval_s,
        anchor_schedule_sha256=anchor.anchor_schedule_sha256,
        source_manifest_sha256=context["source_manifest_sha256"],
        reference_policy_sha256=reference_policy_sha256,
        reference_policy_components=reference_policy_components,
        tape_policy=tape_policy,
    )


def _write_once_output(output: Path, result: Mapping[str, object]) -> dict[str, object]:
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"refusing to overwrite controlled-tape output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
            "ascii"
        )
        + b"\n"
    )
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(output)
    return {
        "output_file": str(output.resolve()),
        "training_run": False,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
    }


def _run(args: argparse.Namespace) -> dict[str, object]:
    if args.tape_policy not in {"main", "q13"}:
        raise ControlledTapeProbeError(f"unknown tape policy: {args.tape_policy}")
    if args.tape_policy == "q13" and args.initialization_seed is None:
        raise ControlledTapeProbeError(
            "Q1+Q3 tape policy requires --initialization-seed"
        )
    if args.tape_policy == "main" and args.initialization_seed is not None:
        raise ControlledTapeProbeError(
            "Main tape policy does not consume a Q1+Q3 initialization seed"
        )
    if args.anchor_sha256 is None and args.anchor_count != 12:
        raise ControlledTapeProbeError(
            "provide --anchor-sha256 for one row, or --anchor-count 12 for the lockstep screen"
        )
    if args.anchor_sha256 is not None and args.anchor_count is not None:
        raise ControlledTapeProbeError(
            "--anchor-sha256 and --anchor-count are mutually exclusive"
        )
    if args.anchor_sha256 is not None and args.candidate_physical_key is None:
        raise ControlledTapeProbeError(
            "single-anchor mode requires --candidate-physical-key"
        )
    if args.anchor_count == 12 and args.candidate_physical_key is not None:
        raise ControlledTapeProbeError(
            "lockstep mode chooses sealed candidate keys; omit --candidate-physical-key"
        )
    phase_a = phase_b._authenticate_phase_a(
        Path(args.phase_a_dir),
        prereg_path=Path(args.prereg),
    )
    q13_gate: Mapping[str, Any] | None = None
    if args.tape_policy == "q13":
        q13_gate = phase_b._authenticate_q13_gate(
            Path(args.gate_dir),
            source_dir=Path(args.c3_source_dir),
            prereg_path=Path(args.prereg),
            v03_root=Path(args.v03_root),
        )
    modules = phase_a["modules"]
    with tempfile.TemporaryDirectory(prefix="mcrl-v05-c2-controlled-tape-tle-") as temporary:
        context = phase_b.support._production_main_context(
            modules=modules,
            prereg_path=Path(args.prereg),
            tle_root=Path(args.tle_root),
            temporary=Path(temporary),
        )
        hybrid = None
        hybrid_before = None
        if args.tape_policy == "q13":
            assert q13_gate is not None
            hybrid = phase_b._screen_module().load_gate_selected_hybrid(
                q13_gate,
                v03_root=Path(args.v03_root),
                initialization_seed=int(args.initialization_seed),
            )
            for network in hybrid.q_nets:
                network.eval()
            hybrid_before = phase_b._snapshot_hybrid(hybrid)
        reference_policy_components = _reference_policy_components(
            tape_policy=args.tape_policy,
            main_policy_sha256=context["policy_sha256"],
            hybrid=hybrid,
            initialization_seed=args.initialization_seed,
        )
        reference_policy_sha256 = str(
            reference_policy_components["policy_components_sha256"]
        )
        anchors = _select_batch_anchors(
            phase_a["prepared"].schedule,
            count=12,
        ) if args.anchor_count == 12 else tuple(
            anchor
            for anchor in phase_a["prepared"].schedule.anchors
            if anchor.anchor_sha256 == args.anchor_sha256
        )
        if args.anchor_sha256 is not None and len(anchors) != 1:
            raise ControlledTapeProbeError("anchor_sha256 does not identify one sealed anchor")
        rows = []
        for anchor in anchors:
            candidate_key = (
                tuple(args.candidate_physical_key)
                if args.candidate_physical_key is not None
                else _scheduled_first_candidate(anchor)
            )
            rows.append(
                _materialize_one_anchor(
                    anchor=anchor,
                    candidate_key=candidate_key,
                    hybrid=hybrid,
                    modules=modules,
                    context=context,
                    reference_policy_sha256=reference_policy_sha256,
                    reference_policy_components=reference_policy_components,
                    tape_policy=args.tape_policy,
                )
            )
        if hybrid is not None:
            assert hybrid_before is not None
            phase_b._assert_hybrid_unchanged(hybrid, hybrid_before)
            after_components = _reference_policy_components(
                tape_policy=args.tape_policy,
                main_policy_sha256=context["policy_sha256"],
                hybrid=hybrid,
                initialization_seed=args.initialization_seed,
            )
            if after_components != reference_policy_components:
                raise ControlledTapeProbeError(
                    "Q1/Q3 policy-component digest changed during controlled replay"
                )
    if args.anchor_sha256 is not None:
        result: dict[str, object] = rows[0] | {
            "status": "V05_CONTROLLED_TAPE_PHYSICAL_ROW_COMPLETE",
        }
    else:
        result = {
            "schema": "multi-catfish-mcrl-v05-c2-controlled-tape-lockstep-12-v2",
            "status": "V05_CONTROLLED_TAPE_LOCKSTEP_12_COMPLETE",
            "initialization_seed": (
                None
                if args.initialization_seed is None
                else int(args.initialization_seed)
            ),
            "tape_policy": args.tape_policy,
            "reference_policy_components": reference_policy_components,
            "anchor_count": len(rows),
            "candidate_selection": "first-sealed-legal-nonmain-key",
            "rows": rows,
            "training_run": False,
            "test_split_opened": False,
            "held_out_ee_evaluated": False,
        }
    return {
        "status": result["status"],
        **_write_once_output(Path(args.output_file), result),
    }


def _cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase-a-dir", type=Path, default=DEFAULT_PHASE_A_DIR)
    parser.add_argument("--gate-dir", type=Path, default=DEFAULT_GATE_DIR)
    parser.add_argument("--c3-source-dir", type=Path, default=DEFAULT_C3_SOURCE_DIR)
    parser.add_argument("--v03-root", type=Path, default=DEFAULT_V03_ROOT)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--tle-root", type=Path, default=DEFAULT_TLE_ROOT)
    parser.add_argument(
        "--anchor-sha256",
        help="one sealed anchor; mutually exclusive with --anchor-count 12",
    )
    parser.add_argument(
        "--anchor-count",
        type=int,
        choices=(12,),
        help="run the deterministic 12-anchor lockstep short screen",
    )
    parser.add_argument(
        "--initialization-seed",
        type=int,
        required=False,
        choices=phase_b.Q13_INIT_SEEDS,
        help="one frozen Q1+Q3 initialization; required only for --tape-policy q13",
    )
    parser.add_argument(
        "--tape-policy",
        choices=("main", "q13"),
        default="q13",
        help="reference policy that generates the physical tape; do not preselect a winner",
    )
    parser.add_argument(
        "--candidate-physical-key",
        type=int,
        nargs=2,
        required=False,
        metavar=("NORAD", "CELL"),
    )
    parser.add_argument("--output-file", type=Path, required=True)
    args = parser.parse_args()
    result = _run(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_cli())


__all__ = [
    "ControlledTapeProbeError",
    "_materialize_controlled_pair",
]
