from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys

import numpy as np
import pytest

from mcrl.runtime.ee_axis_coalition_residual_c3 import build_coalition_residual_c3


VERIFIER_PATH = (
    Path(__file__).resolve().parents[1]
    / ".scratch"
    / "multi-catfish-v023-c3-observability"
    / "verify_v023_lcsrs_scientific.py"
)
_SPEC = importlib.util.spec_from_file_location("v023_scientific_verifier_test", VERIFIER_PATH)
assert _SPEC is not None and _SPEC.loader is not None
verifier = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = verifier
_SPEC.loader.exec_module(verifier)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _array_digest(array: np.ndarray, *, domain: str) -> str:
    value = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(domain.encode("ascii"))
    digest.update(value.dtype.str.encode("ascii"))
    digest.update(repr(tuple(value.shape)).encode("ascii"))
    digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def _q12_fixture_receipts() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    authority_path = (
        verifier.REPO
        / ".scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit"
        / "lineage-2026092101/authority.json"
    )
    authority = json.loads(authority_path.read_text(encoding="ascii"))
    checkpoint_path = (
        authority_path.parent
        / "checkpoints/lineage-2026092101-q2init-2026108101-rung-003000.pt"
    )
    checkpoint_relative = checkpoint_path.relative_to(verifier.REPO).as_posix()
    checkpoint_sha = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
    q1_receipt: dict[str, object] = {
        "checkpoint_path": str(checkpoint_path.resolve()),
        "checkpoint_sha256": checkpoint_sha,
        "combined_checkpoint": True,
        "head_index": 0,
        "update_count": 10,
        "train_seed": verifier.Q12_LINEAGE,
        "config": authority["q1_config"],
    }
    q2_receipt: dict[str, object] = {
        "checkpoint_path": str(checkpoint_path.resolve()),
        "checkpoint_sha256": checkpoint_sha,
        "combined_checkpoint": True,
        "update_count": 3000,
        "train_seed": 2026108101,
        "config": authority["q2_config"],
    }
    target_hashes = authority["q2_repriced_target_file_sha256s"]
    binding: dict[str, object] = {
        "schema": "multi-catfish-mcrl-v023-q12-authority-binding-v1",
        "authority_path": authority_path.relative_to(verifier.REPO).as_posix(),
        "authority_file_sha256": verifier.Q12_AUTHORITY_FILE_SHA256,
        "authority_body_sha256": verifier.Q12_AUTHORITY_BODY_SHA256,
        "execution_contract_path": ".scratch/multi-catfish-v020-c3-source-audit/Q1-Q2-REPRICED-SUPERVISED-EXECUTION-CONTRACT-2026-09-04.md",
        "execution_contract_sha256": verifier.Q12_EXECUTION_CONTRACT_SHA256,
        "repricing_contract_path": ".scratch/multi-catfish-v020-c3-source-audit/Q1-Q2-LAMBDA-REPRICING-PREOUTCOME-CONTRACT-2026-09-04.md",
        "repricing_contract_sha256": verifier.Q12_REPRICING_CONTRACT_SHA256,
        "fit_runner_path": ".scratch/multi-catfish-v020-c3-source-audit/run_v020_repriced_q1_q2.py",
        "fit_runner_sha256": verifier.Q12_FIT_RUNNER_SHA256,
        "ops3_formula_path": "src/mcrl/runtime/ee_axis_ops3.py",
        "ops3_formula_sha256": verifier.OPS3_FORMULA_SHA256,
        "ops3_live_path": "src/mcrl/runtime/ee_axis_ops3_live.py",
        "ops3_live_sha256": verifier.OPS3_LIVE_SHA256,
        "q2_state_path": "src/mcrl/runtime/ee_axis_v014_q2_state.py",
        "q2_state_file_sha256": verifier.Q2_STATE_FILE_SHA256,
        "checkpoint_path": checkpoint_relative,
        "checkpoint_sha256": checkpoint_sha,
        "q2_target_file_count": 7,
        "q2_target_files_sha256": verifier.canonical_sha256(target_hashes),
        "source_sha256": authority["source_sha256"],
        "lambda_bits_per_j_hex": verifier.LAMBDA_BITS_PER_J.hex(),
        "ops3_runtime_default_lambda_hex": verifier.OPS3_RUNTIME_DEFAULT_LAMBDA_HEX,
        "ops3_runtime_default_used_for_diagnostic_target": False,
        "ops3_horizon": verifier.OPS3_HORIZON,
        "ops3_interval_s_hex": verifier.OPS3_INTERVAL_S.hex(),
        "q2_state_schema": verifier.Q2_STATE_SCHEMA,
        "q2_state_schema_sha256": verifier.Q2_STATE_SCHEMA_SHA256,
        "q2_state_dim": verifier.Q2_STATE_DIM,
        "target_free_inference": True,
    }
    return q1_receipt, q2_receipt, binding


def _write_npz(
    root: Path,
    name: str,
    arrays: dict[str, np.ndarray],
    *,
    domain: str,
) -> dict[str, object]:
    path = root / name
    np.savez_compressed(path, **arrays)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    digest_name = f"{name}.sha256"
    (root / digest_name).write_text(f"{digest}  {name}\n", encoding="ascii")
    return {
        "allow_pickle": False,
        "npz_relative_path": name,
        "npz_sha256": digest,
        "npz_sha256_file": digest_name,
        "array_metadata": {
            key: {
                "dtype": value.dtype.str,
                "shape": list(value.shape),
                "sha256": _array_digest(value, domain=domain),
            }
            for key, value in arrays.items()
        },
    }


def _source_arrays(*, corrupt_formula: bool = False) -> dict[str, np.ndarray]:
    draws, users, actions, anchors = verifier.DRAW_COUNT, 4, verifier.ACTION_COUNT, 9
    reference = np.zeros((anchors, users), dtype=np.int64)
    reference[0] = np.asarray([0, 0, 1, 2], dtype=np.int64)
    reference[1:] = np.asarray([0, 1, 2, 3], dtype=np.int64)
    physical = np.zeros((anchors, users, actions, 2), dtype=np.int64)
    physical[..., 0] = 10
    physical[..., 1] = np.arange(actions, dtype=np.int64)
    # Both pair members share source (10,0), then choose distinct active beams.
    pair_users = np.asarray([[0, 1]], dtype=np.int64)
    pair_actions = np.asarray([[1, 2]], dtype=np.int64)
    profile_actions = np.tile(reference[0][None, None, :], (draws, 4, 1))
    profile_actions[:, 1, 0] = 1
    profile_actions[:, 2, 1] = 2
    profile_actions[:, 3, 0] = 1
    profile_actions[:, 3, 1] = 2
    base_bits = np.asarray(
        [
            [10.0, 10.0, 5.0, 5.0],
            [12.0, 10.0, 5.0, 5.0],
            [10.0, 13.0, 5.0, 5.0],
            [12.0, 13.0, 5.0, 5.0],
        ],
        dtype=np.float64,
    )
    profile_bits = np.stack([base_bits + draw * 0.001 for draw in range(draws)])
    profile_energy = np.tile(
        np.asarray([[10.0, 9.8, 9.9, 9.5]], dtype=np.float64), (draws, 1)
    )
    profile_g = np.sum(profile_bits, axis=2) - verifier.LAMBDA_BITS_PER_J * profile_energy
    served = np.ones((draws, 4, users), dtype=np.bool_)
    active_keys = np.full((draws, 4, 3, 2), -1, dtype=np.int64)
    active_counts = np.zeros((draws, 4), dtype=np.int64)
    for draw in range(draws):
        for profile in range(3):
            active_keys[draw, profile] = np.asarray([[10, 0], [10, 1], [10, 2]])
            active_counts[draw, profile] = 3
        active_keys[draw, 3, :2] = np.asarray([[10, 1], [10, 2]])
        active_counts[draw, 3] = 2
    formula = [
        verifier._formula(profile_bits[index], profile_energy[index], pair_users[0])
        for index in range(draws)
    ]
    own = np.stack([value.own for value in formula])
    nonfocal = np.stack([value.nonfocal for value in formula])
    d_value = np.stack([value.d for value in formula])
    joint_bits = np.asarray([value.joint_delta_bits for value in formula])
    joint_energy = np.asarray([value.joint_delta_energy for value in formula])
    joint_surplus = np.asarray([value.joint_surplus for value in formula])
    interaction_bits = np.asarray([value.interaction_bits for value in formula])
    interaction_energy = np.asarray([value.interaction_energy for value in formula])
    interaction_surplus = np.asarray([value.interaction_surplus for value in formula])
    equal_share = np.asarray([value.equal_share for value in formula])
    z3 = np.stack([value.z3 for value in formula])
    residual = np.asarray([value.residual for value in formula])
    if corrupt_formula:
        z3[0, 0] += 1000.0
    totals = np.sum(profile_bits, axis=2)
    left = totals[:, 3] * profile_energy[:, 0]
    right = totals[:, 0] * profile_energy[:, 3]
    cross = left - right
    tolerance = np.asarray(
        [verifier.comparison_tolerance(lvalue, rvalue) for lvalue, rvalue in zip(left, right, strict=True)]
    )
    ratio_sign = np.where(cross > tolerance, 1, np.where(cross < -tolerance, -1, 0)).astype(np.int8)
    local = (totals[:, 3] - totals[:, 0]) - (totals[:, 0] / profile_energy[:, 0]) * (
        profile_energy[:, 3] - profile_energy[:, 0]
    )
    local_tolerance = tolerance / profile_energy[:, 0]
    q1 = np.zeros((anchors, users, actions), dtype=np.float64)
    q2 = np.full_like(q1, -1.0)
    for anchor in range(anchors):
        q2[anchor, np.arange(users), reference[anchor]] = 0.0
    q1[0, 0, 1] = float(np.mean(own[:, 0] / verifier.KAPPA_BITS))
    q1[0, 1, 2] = float(np.mean(own[:, 1] / verifier.KAPPA_BITS))
    q2[0, 0, 1] = -0.03
    q2[0, 0, 2] = -0.04
    q2[0, 1, 1] = -0.04
    q2[0, 1, 2] = -0.03
    q12 = np.asarray(
        np.asarray(q1, dtype=np.float32) + np.asarray(q2, dtype=np.float32),
        dtype=np.float64,
    )
    action_mask = np.ones((anchors, users, actions), dtype=np.bool_)
    opening = action_mask.copy()
    q2_feature = np.zeros(
        (anchors, users, actions, verifier.Q2_FEATURE_DIM), dtype=np.float64
    )
    q2_horizon = np.asarray(
        [min(verifier.OPS3_HORIZON, max(0, 9 - phase)) for phase in range(1, anchors + 1)],
        dtype=np.int64,
    )
    for anchor, h in enumerate(q2_horizon.tolist()):
        for offset in range(h):
            q2_feature[anchor, :, :, 4 + 4 * offset] = 1.0
    q2_state = q2_feature.astype(np.float32).transpose(0, 1, 3, 2).reshape(
        anchors, users, verifier.Q2_STATE_DIM
    )
    q2_teacher = np.zeros((anchors, users, actions), dtype=np.float64)
    q2_persistence = np.zeros(
        (anchors, users, verifier.OPS3_HORIZON, actions), dtype=np.float64
    )
    q2_rate = np.zeros_like(q2_persistence)
    q2_power = np.zeros_like(q2_persistence)
    q2_required = np.zeros_like(q2_persistence)
    contexts = np.zeros((anchors, users, actions, 29), dtype=np.float32)
    contexts[:, :, :, 3] = 1.0
    contexts[0, 0, 1, 27] = np.float32(1.0 / users)
    contexts[0, 1, 2, 27] = np.float32(1.0 / users)
    row = np.arange(users)
    for anchor in range(anchors):
        contexts[anchor, :, :, 23] = np.asarray(
            np.tanh(q12[anchor] - q12[anchor, row, reference[anchor], None]),
            dtype=np.float32,
        )
    tokens = np.zeros((anchors, users, actions, users + 1, 38), dtype=np.float32)
    token_mask = np.zeros((anchors, users, actions, users + 1), dtype=np.bool_)
    token_mask[:, :, :, users] = action_mask
    tokens[:, :, :, users, 1] = 1.0
    tokens[0, 0, 1, users, 2:5] = 1.0
    tokens[0, 1, 2, users, 2:5] = 1.0
    view_digest = np.asarray(
        [
            verifier.c3_view_sha256(
                contexts[anchor],
                tokens[anchor],
                token_mask[anchor],
                action_mask[anchor],
                reference[anchor],
            ).encode("ascii")
            for anchor in range(anchors)
        ],
        dtype="S64",
    )
    action_digest = np.asarray(
        [
            [verifier.action_sha256(profile_actions[draw, profile]).encode("ascii") for profile in range(4)]
            for draw in range(draws)
        ],
        dtype="S64",
    )
    return {
        "anchor_phase": np.arange(1, anchors + 1, dtype=np.int64),
        "anchor_status": np.asarray([1] + [0] * (anchors - 1), dtype=np.uint8),
        "anchor_retained": np.asarray([True] + [False] * (anchors - 1), dtype=np.bool_),
        "anchor_content_digest": np.asarray([b"c" * 64] * anchors, dtype="S64"),
        "anchor_view_content_digest": view_digest,
        "anchor_topology_content_digest": np.asarray([b"d" * 64] * anchors, dtype="S64"),
        "action_context": contexts,
        "tokens": tokens,
        "token_mask": token_mask,
        "action_mask": action_mask,
        "opening_feasibility": opening,
        "reference_actions": reference,
        "physical_keys": physical,
        "q1_values": q1,
        "q2_values": q2,
        "q12_values": q12,
        "q2_state_matrix": q2_state,
        "q2_feature_surface": q2_feature,
        "q2_teacher_values": q2_teacher,
        "q2_persistence": q2_persistence,
        "q2_rate_bps": q2_rate,
        "q2_marginal_power_w": q2_power,
        "q2_required_power_w": q2_required,
        "q2_horizon": q2_horizon,
        "pair_anchor_index": np.zeros(1, dtype=np.int64),
        "pair_retained": np.ones(1, dtype=np.bool_),
        "pair_id": np.asarray([b"pair-0"], dtype="S256"),
        "pair_user_ids": pair_users,
        "pair_action_ids": pair_actions,
        "pair_target_by_draw": (z3 / verifier.KAPPA_BITS)[None, :, :],
        "pair_target_mean": np.mean(z3 / verifier.KAPPA_BITS, axis=0)[None, :],
        "pair_class": np.full((1, 2), 3, dtype=np.uint8),
        "draw_pair_index": np.zeros(draws, dtype=np.int64),
        "draw_pair_id": np.asarray([b"pair-0"] * draws, dtype="S256"),
        "draw_index": np.arange(draws, dtype=np.int64),
        "profile_actions": profile_actions,
        "profile_bits": profile_bits,
        "profile_energy_j": profile_energy,
        "profile_g_bits": profile_g,
        "profile_served": served,
        "profile_active_beam_keys": active_keys,
        "profile_active_beam_counts": active_counts,
        "z3_bits_by_draw": z3,
        "z3_normalized_by_draw": z3 / verifier.KAPPA_BITS,
        "formula_identity_residual_bits": residual,
        "ratio_identity_value_bits": local,
        "ratio_cross_product": cross,
        "ratio_sign": ratio_sign,
        "ratio_tolerance": tolerance,
        "ratio_local_tolerance": local_tolerance,
        "joint_ee_bits_per_j": totals[:, 3] / profile_energy[:, 3],
        "nonmutation_flags": np.ones((draws, 5), dtype=np.bool_),
        "common_field_digest": np.asarray([b"1" * 64] * draws, dtype="S64"),
        "action_digest": action_digest,
        "formula_own_bits": own,
        "formula_nonfocal_bits": nonfocal,
        "formula_d_bits": d_value,
        "formula_joint_delta_bits": joint_bits,
        "formula_joint_delta_energy_j": joint_energy,
        "formula_joint_surplus_bits": joint_surplus,
        "formula_interaction_bits": interaction_bits,
        "formula_interaction_energy_j": interaction_energy,
        "formula_interaction_surplus_bits": interaction_surplus,
        "formula_equal_share_bits": equal_share,
    }


def _source_fixture(
    tmp_path: Path,
    *,
    corrupt_formula: bool = False,
    world: int = 2026121705,
) -> Path:
    arrays = _source_arrays(corrupt_formula=corrupt_formula)
    users = int(arrays["reference_actions"].shape[1])
    binding = _write_npz(
        tmp_path,
        "world.arrays.npz",
        arrays,
        domain=verifier.SOURCE_ARRAY_DOMAIN,
    )
    teacher_draws = [
        {
            "draw_index": draw,
            "profile_actions": arrays["profile_actions"][draw].tolist(),
            "profile_bits": arrays["profile_bits"][draw].tolist(),
            "profile_energy_j": arrays["profile_energy_j"][draw].tolist(),
            "common_field_sha256_by_profile": ["1" * 64] * 4,
            "action_sha256_by_profile": [
                bytes(value).decode("ascii")
                for value in arrays["action_digest"][draw].tolist()
            ],
            "formula": {},
        }
        for draw in range(verifier.DRAW_COUNT)
    ]
    teacher_pair: dict[str, object] = {
        "pair_id": "pair-0",
        "member_users": [0, 1],
        "proposed_actions": [1, 2],
        "pair_targets_by_draw": arrays["pair_target_by_draw"][0].tolist(),
        "pair_target_mean": arrays["pair_target_mean"][0].tolist(),
        "draws": teacher_draws,
    }
    teacher_pair["content_digest"] = verifier._teacher_digest(
        pair_id="pair-0",
        users=np.asarray([0, 1], dtype=np.int64),
        actions=np.asarray([1, 2], dtype=np.int64),
        draws=teacher_draws,
        targets=arrays["pair_target_by_draw"][0],
    )
    enumeration = {"schema": "test-enumeration", "world": world, "anchors": []}
    topology = {"schema": "test-topology", "world": world, "anchors": []}
    teacher_anchors = [
        {"schema": "test-anchor-teacher", "pairs": [teacher_pair]}
    ] + [
        {"schema": "test-anchor-teacher", "pairs": []}
        for _ in verifier.WORLD_PHASES[1:]
    ]
    teacher = {
        "schema": "test-teacher",
        "world": world,
        "anchors": teacher_anchors,
    }
    surface = {"schema": "test-surface", "world": world, "anchors": []}
    anchor_ids = [f"w{world}:t{phase}" for phase in verifier.WORLD_PHASES]
    q1_reference = np.argmax(arrays["q1_values"], axis=2).astype(np.int64)
    q12_reference = np.argmax(arrays["q12_values"], axis=2).astype(np.int64)
    start = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)

    def q2_context(index: int, phase: int) -> dict[str, object]:
        h = int(arrays["q2_horizon"][index])
        first = start + dt.timedelta(
            seconds=phase * verifier.OPS3_INTERVAL_S + 0.640
        )
        sample_times = [
            first + dt.timedelta(seconds=offset * 0.640)
            for offset in range(h * 47)
        ]
        return {
            "schema": "multi-catfish-mcrl-v023-q2-context-v1",
            "q2_state_schema": verifier.Q2_STATE_SCHEMA,
            "q2_state_schema_sha256": verifier.Q2_STATE_SCHEMA_SHA256,
            "q2_state_sha256": verifier._q2_state_sha256(
                arrays["q2_state_matrix"][index], arrays["action_mask"][index]
            ),
            "ops3_anchor_sha256": "b" * 64,
            "ops3_tracker_seed_sha256": "c" * 64,
            "ops3_projection_sha256": "d" * 64,
            "horizon": h,
            "future_d2_indices": list(range((phase + 1) * 47, (phase + 1 + h) * 47)),
            "sample_times_utc": [value.isoformat() for value in sample_times],
            "offset_times_utc": [
                sample_times[(offset + 1) * 47 - 1].isoformat()
                for offset in range(h)
            ],
            "q1_reference_actions_sha256": _array_digest(
                q1_reference[index], domain="v023-q1-reference-actions"
            ),
            "q12_reference_actions_sha256": _array_digest(
                q12_reference[index], domain="v023-reference-actions"
            ),
            "q1_to_q12_argmax_change_count": int(
                np.count_nonzero(q1_reference[index] != q12_reference[index])
            ),
            "served_user_count": users,
            "target_values_sha256": _array_digest(
                arrays["q2_teacher_values"][index],
                domain="v023-repriced-ops3-target-values",
            ),
            "feature_surface_sha256": _array_digest(
                arrays["q2_feature_surface"][index],
                domain="v023-ops3-feature-surface",
            ),
            "persistence_sha256": _array_digest(
                arrays["q2_persistence"][index], domain="v023-ops3-persistence"
            ),
            "target_free_inference": True,
            "absorbing_persistence_checked": True,
            "terminal_zero_checked": True,
            "opening_mask_checked": True,
            "frozen_background_formula_checked": True,
            "diagnostic_lambda_bits_per_j_hex": verifier.LAMBDA_BITS_PER_J.hex(),
            "ops3_runtime_default_lambda_hex": verifier.OPS3_RUNTIME_DEFAULT_LAMBDA_HEX,
            "runtime_default_lambda_used_for_target": False,
        }

    source_anchors = [
        {
            "anchor_id": anchor_ids[index],
            "phase": phase,
            "retained_for_fitting": index == 0,
            "q2_context": q2_context(index, phase),
            "surface": {"record": {"content_digest": "e" * 64}}
            if index == 0
            else None,
        }
        for index, phase in enumerate(verifier.WORLD_PHASES)
    ]
    stratum = (world, 0, 1, 1, 0, 1)
    shift = verifier._placebo_shift(stratum, 2)
    assert shift == 1
    cells = [(0, 0, 1), (0, 1, 2)]
    mappings = []
    for destination_index, destination in enumerate(cells):
        source = cells[(destination_index - shift) % len(cells)]
        mappings.append(
            {
                "stratum": list(stratum),
                "source_anchor": source[0],
                "source_user": source[1],
                "source_action": source[2],
                "destination_anchor": destination[0],
                "destination_user": destination[1],
                "destination_action": destination[2],
                "shift": shift,
            }
        )
    permuted_target = np.zeros((4, verifier.ACTION_COUNT), dtype=np.float32)
    permuted_target[0, 1] = np.float32(arrays["pair_target_mean"][0, 1])
    permuted_target[1, 2] = np.float32(arrays["pair_target_mean"][0, 0])
    placebo_digest = hashlib.sha256()
    placebo_digest.update(b"multi-catfish-mcrl-v023-matched-placebo-v1")
    placebo_digest.update(verifier.PLACEBO_KEY_SHA256.encode("ascii"))
    placebo_digest.update(("e" * 64).encode("ascii"))
    placebo_digest.update(permuted_target.tobytes(order="C"))
    for mapping in mappings:
        placebo_digest.update(struct.pack(">6qI", *stratum, shift))
        placebo_digest.update(
            struct.pack(
                ">6q",
                mapping["source_anchor"],
                mapping["source_user"],
                mapping["source_action"],
                mapping["destination_anchor"],
                mapping["destination_user"],
                mapping["destination_action"],
            )
        )
    placebo_receipt = {
        "schema": f"{verifier.SOURCE_ARTIFACT_SCHEMA}-placebo-strata-v1",
        "strata": [
            {
                "stratum": list(stratum),
                "rows": [
                    {
                        "anchor_index": 0,
                        "world": world,
                        "anchor_id": anchor_ids[0],
                        "user": 0,
                        "action": 1,
                    },
                    {
                        "anchor_index": 0,
                        "world": world,
                        "anchor_id": anchor_ids[0],
                        "user": 1,
                        "action": 2,
                    },
                ],
                "count": 2,
                "placebo_eligible": True,
            }
        ],
        "mappings": mappings,
        "supported_count": 2,
        "placebo_eligible_count": 2,
        "coverage": 1.0,
        "within_world_only": True,
        "placebo_key": verifier.PLACEBO_KEY,
        "placebo_key_sha256": verifier.PLACEBO_KEY_SHA256,
        "content_digest": placebo_digest.hexdigest(),
        "outcome_filter_applied": False,
    }
    q1_receipt, q2_receipt, q12_authority = _q12_fixture_receipts()
    payload: dict[str, object] = {
        "schema": verifier.SOURCE_SCHEMA,
        "status": "PASS",
        "claim_ceiling": verifier.CLAIM_CEILING,
        "split": "TRAIN_DEVELOPMENT",
        "world": world,
        "contract_sha256": verifier.CONTRACT_SHA256,
        "preflight_manifest_sha256": "2" * 64,
        "execution_addendum_sha256": verifier.EXECUTION_ADDENDUM_SHA256,
        "placebo_key": verifier.PLACEBO_KEY,
        "placebo_key_sha256": verifier.PLACEBO_KEY_SHA256,
        "source_artifact_schema": verifier.SOURCE_ARTIFACT_SCHEMA,
        "source_artifact_version": verifier.SOURCE_ARTIFACT_VERSION,
        "q12_background": {
            "lineage": verifier.Q12_LINEAGE,
            "checkpoint_sha256": verifier.Q12_CHECKPOINT_SHA256,
            "q1_checkpoint_sha256": verifier.Q12_CHECKPOINT_SHA256,
            "q2_checkpoint_sha256": verifier.Q12_CHECKPOINT_SHA256,
            "q1_receipt": q1_receipt,
            "q2_receipt": q2_receipt,
            "q12_authority": q12_authority,
            "q1_parameter_sha256": "3" * 64,
            "q2_parameter_sha256": "4" * 64,
            "q12_model_sha256": "5" * 64,
            "lambda_bits_per_j_hex": verifier.LAMBDA_BITS_PER_J.hex(),
            "kappa_bits_hex": verifier.KAPPA_BITS.hex(),
            "q12_unit": "authenticated-normalized-q1-plus-q2-float32",
            "state_schema": "native-ee-axis-state-v1",
        },
        "world_receipt": {
            "world": world,
            "field_component": verifier.FIELD_COMPONENT,
            "field_root_digest": "6" * 64,
            "phase_count": 9,
            "anchor_ids": anchor_ids,
            "q1_parameter_sha256": "3" * 64,
            "q2_parameter_sha256": "4" * 64,
            "q1_parameter_sha256_after": "3" * 64,
            "q2_parameter_sha256_after": "4" * 64,
            "environment_initial_digest": "7" * 64,
            "environment_final_digest": "8" * 64,
            "rng_initial_digest": "9" * 64,
            "rng_final_digest": "a" * 64,
            "test_split_opened": False,
            "learner_update": False,
            "episode_training": False,
        },
        "field_manifest": {
            "family": verifier.FIELD_COMPONENT,
            "key_axes": ["family", "world", "anchor", "draw", "event", "step_index", "norad_id"],
            "root_excludes": ["pair", "profile"],
            "profile_order": list(verifier.PROFILE_ORDER),
            "world_rollout_root_digest": "6" * 64,
            "draw_root_rule": "KeyedFadingField.from_components(family, world, anchor_id, draw_index)",
        },
        "ephemeris_validation": {
            "file_set_sha256": "427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9",
        },
        "anchors": source_anchors,
        "enumeration": enumeration,
        "topology": topology,
        "teacher": teacher,
        "surface": surface,
        "enumeration_sha256": verifier.canonical_sha256(enumeration),
        "topology_sha256": verifier.canonical_sha256(topology),
        "teacher_sha256": verifier.canonical_sha256(teacher),
        "surface_sha256": verifier.canonical_sha256(surface),
        "arrays": binding,
        "pair_count": 1,
        "supported_count": 2,
        "placebo_eligible_count": 2,
        "placebo_strata": placebo_receipt,
        "c1_c2_parameter_unchanged": True,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
    }
    payload["receipt_sha256"] = verifier.canonical_sha256(payload)
    path = tmp_path / "world.json"
    path.write_bytes(_canonical(payload))
    return path


def _fit_fixture(
    tmp_path: Path,
    *,
    reported_spearman: float | None = None,
    world: int = 2026121705,
    seed: int = 2026135101,
    arm: str = "INFORMED",
) -> Path:
    prediction = np.asarray([-2.0, -1.0, 1.0, 2.0], dtype=np.float64)
    if arm == "MATCHED_PLACEBO":
        prediction = prediction[::-1].copy()
    target = np.asarray([-1.0, -0.5, 0.5, 1.0], dtype=np.float64)
    arrays = {
        "identity_world": np.full(4, world, dtype=np.int64),
        "identity_anchor": np.asarray([b"a"] * 4, dtype="S256"),
        "identity_user": np.arange(4, dtype=np.int64),
        "identity_action": np.ones(4, dtype=np.int64),
        "prediction": prediction,
        "target": target,
        "loss": np.zeros(2000, dtype=np.float64),
    }
    binding = _write_npz(
        tmp_path,
        "fit.metrics.npz",
        arrays,
        domain=verifier.FIT_PREDICTION_ARRAY_DOMAIN,
    )
    rho = verifier.tie_aware_spearman(prediction, target)
    sign = verifier.sign_receipt(prediction, target)
    metrics = {
        "schema": "multi-catfish-mcrl-v023-lcsrs-fit-metrics-v1",
        "spearman": rho if reported_spearman is None else reported_spearman,
        "sign": sign,
        "arrays": binding["array_metadata"],
    }
    metrics_path = tmp_path / "fit.metrics.json"
    metrics_path.write_bytes(_canonical(metrics))
    metrics_sha = hashlib.sha256(metrics_path.read_bytes()).hexdigest()
    receipt: dict[str, object] = {
        "schema": verifier.FIT_SCHEMA,
        "status": "PASS",
        "claim_ceiling": verifier.CLAIM_CEILING,
        "split": "TRAIN_DEVELOPMENT",
        "held_out_world": world,
        "student_seed": seed,
        "arm": arm,
        "update_count": 2000,
        "learner_update": True,
        "episode_training": False,
        "test_split_opened": False,
        "metrics": {
            "path": metrics_path.name,
            "sha256": metrics_sha,
            "npz_path": binding["npz_relative_path"],
            "npz_sha256": binding["npz_sha256"],
            "npz_sha256_file": binding["npz_sha256_file"],
        },
    }
    receipt["receipt_sha256"] = verifier.canonical_sha256(receipt)
    path = tmp_path / "fit.json"
    path.write_bytes(_canonical(receipt))
    return path


def _reseal_source_json(path: Path, mutate) -> None:
    payload = json.loads(path.read_text(encoding="ascii"))
    mutate(payload)
    payload.pop("receipt_sha256", None)
    payload["receipt_sha256"] = verifier.canonical_sha256(payload)
    path.write_bytes(_canonical(payload))


def _rewrite_source_arrays(path: Path, mutate) -> None:
    payload = json.loads(path.read_text(encoding="ascii"))
    binding = payload["arrays"]
    assert isinstance(binding, dict)
    npz_name = binding["npz_relative_path"]
    assert isinstance(npz_name, str)
    with np.load(path.parent / npz_name, allow_pickle=False) as archive:
        arrays = {name: np.array(archive[name], copy=True) for name in archive.files}
    mutate(payload, arrays)
    payload["arrays"] = _write_npz(
        path.parent, npz_name, arrays, domain=verifier.SOURCE_ARRAY_DOMAIN
    )
    payload.pop("receipt_sha256", None)
    payload["receipt_sha256"] = verifier.canonical_sha256(payload)
    path.write_bytes(_canonical(payload))


def test_source_world_recomputes_formula_actions_mechanics_and_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(verifier, "USER_COUNT", 4)
    result = verifier.verify_source_world_science(_source_fixture(tmp_path))
    assert result["status"] == "VERIFIED_SOURCE_NUMERICS"
    assert result["gate_decision"] is None
    assert result["mechanics_fraction"] == 1.0
    assert result["world_joint_direction"] == 1
    assert result["c1"]["row_count"] == 2
    assert result["c2"]["exposure"] == 1.0
    assert result["c2"]["world_only_not_final_predicate"] is True
    assert result["scientific_claim"] is False


def test_source_world_rejects_formula_drift_even_when_artifact_is_resealed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(verifier, "USER_COUNT", 4)
    with pytest.raises(verifier.V023ScientificVerificationError, match="z3_bits"):
        verifier.verify_source_world_science(
            _source_fixture(tmp_path, corrupt_formula=True)
        )


@pytest.mark.parametrize("empty", [False, True])
def test_source_world_treats_mutation_flags_as_integrity_not_mechanics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, empty: bool
) -> None:
    monkeypatch.setattr(verifier, "USER_COUNT", 4)
    path = _source_fixture(tmp_path)

    def mutate(_payload: dict[str, object], arrays: dict[str, np.ndarray]) -> None:
        if empty:
            arrays["nonmutation_flags"] = np.ones(
                (verifier.DRAW_COUNT, 0), dtype=np.bool_
            )
        else:
            arrays["nonmutation_flags"][0, 0] = False

    _rewrite_source_arrays(path, mutate)
    with pytest.raises(
        verifier.V023ScientificVerificationError,
        match="shape drifted|mutation flag failed",
    ):
        verifier.verify_source_world_science(path)


def test_source_world_requires_11_to_remove_only_the_source_beam(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(verifier, "USER_COUNT", 4)
    path = _source_fixture(tmp_path)

    def mutate(_payload: dict[str, object], arrays: dict[str, np.ndarray]) -> None:
        old = arrays["profile_active_beam_keys"]
        expanded = np.full((old.shape[0], old.shape[1], 4, 2), -1, dtype=np.int64)
        expanded[:, :, : old.shape[2]] = old
        expanded[:, :3, 3] = np.asarray([10, 3], dtype=np.int64)
        arrays["profile_active_beam_keys"] = expanded
        arrays["profile_active_beam_counts"][:, :3] = 4

    _rewrite_source_arrays(path, mutate)
    result = verifier.verify_source_world_science(path)
    assert result["status"] == "VERIFIED_SOURCE_NUMERICS"
    assert result["mechanics_pass_count"] == 0
    assert result["mechanics_fraction"] == 0.0


def test_source_world_rejects_resealed_placebo_mapping_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(verifier, "USER_COUNT", 4)
    path = _source_fixture(tmp_path)

    def mutate(payload: dict[str, object]) -> None:
        placebo = payload["placebo_strata"]
        assert isinstance(placebo, dict)
        mappings = placebo["mappings"]
        assert isinstance(mappings, list) and isinstance(mappings[0], dict)
        mappings[0]["destination_action"] = 2

    _reseal_source_json(path, mutate)
    with pytest.raises(verifier.V023ScientificVerificationError, match="placebo strata"):
        verifier.verify_source_world_science(path)


def test_source_world_rejects_resealed_repriced_q2_target_arithmetic_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(verifier, "USER_COUNT", 4)
    path = _source_fixture(tmp_path)

    def mutate(payload: dict[str, object], arrays: dict[str, np.ndarray]) -> None:
        arrays["q2_teacher_values"][0, 0, 1] += 1.0
        anchors = payload["anchors"]
        assert isinstance(anchors, list) and isinstance(anchors[0], dict)
        context = anchors[0]["q2_context"]
        assert isinstance(context, dict)
        context["target_values_sha256"] = _array_digest(
            arrays["q2_teacher_values"][0], domain="v023-repriced-ops3-target-values"
        )

    _rewrite_source_arrays(path, mutate)
    with pytest.raises(verifier.V023ScientificVerificationError, match="repriced OPS-3 target"):
        verifier.verify_source_world_science(path)


def test_source_world_rejects_resealed_target_leak_into_q2_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(verifier, "USER_COUNT", 4)
    path = _source_fixture(tmp_path)

    def mutate(payload: dict[str, object], arrays: dict[str, np.ndarray]) -> None:
        arrays["q2_state_matrix"][0, 0, 0] = np.float32(0.25)
        anchors = payload["anchors"]
        assert isinstance(anchors, list) and isinstance(anchors[0], dict)
        context = anchors[0]["q2_context"]
        assert isinstance(context, dict)
        context["q2_state_sha256"] = verifier._q2_state_sha256(
            arrays["q2_state_matrix"][0], arrays["action_mask"][0]
        )

    _rewrite_source_arrays(path, mutate)
    with pytest.raises(verifier.V023ScientificVerificationError, match="target-free OPS-3 features"):
        verifier.verify_source_world_science(path)


def test_source_world_rejects_resealed_q2_native_clock_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(verifier, "USER_COUNT", 4)
    path = _source_fixture(tmp_path)

    def mutate(payload: dict[str, object]) -> None:
        anchors = payload["anchors"]
        assert isinstance(anchors, list) and isinstance(anchors[0], dict)
        context = anchors[0]["q2_context"]
        assert isinstance(context, dict)
        indices = context["future_d2_indices"]
        assert isinstance(indices, list)
        indices[0] += 1

    _reseal_source_json(path, mutate)
    with pytest.raises(verifier.V023ScientificVerificationError, match="D2 index schedule"):
        verifier.verify_source_world_science(path)


def test_source_world_rejects_resealed_authority_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(verifier, "USER_COUNT", 4)
    path = _source_fixture(tmp_path)
    _reseal_source_json(path, lambda payload: payload.__setitem__("contract_sha256", "f" * 64))
    with pytest.raises(verifier.V023ScientificVerificationError, match="contract digest"):
        verifier.verify_source_world_science(path)


def test_fit_metrics_are_independently_recomputed(tmp_path: Path) -> None:
    result = verifier.verify_fit_science(_fit_fixture(tmp_path))
    assert result["spearman"] == pytest.approx(1.0)
    assert result["sign"]["accuracy"] == pytest.approx(1.0)
    assert result["rows"] == 4
    assert result["scientific_claim"] is False


def test_fit_rejects_reported_metric_drift(tmp_path: Path) -> None:
    with pytest.raises(verifier.V023ScientificVerificationError, match="Spearman"):
        verifier.verify_fit_science(_fit_fixture(tmp_path, reported_spearman=0.25))


def test_action_hash_binds_vector_length() -> None:
    assert verifier.action_sha256(np.asarray([0, 1], dtype=np.int64)) != verifier.action_sha256(
        np.asarray([0, 1, 0], dtype=np.int64)
    )


def test_frozen_strict_direction_does_not_promote_a_tolerance_tie() -> None:
    tolerance = verifier.comparison_tolerance(1.0, 1.0)
    assert verifier.strict_direction(1.0 + 0.5 * tolerance, 1.0) == 0


def test_formula_recomputation_matches_production_under_physical_scale_cancellation() -> None:
    """Prevent profile-total subtraction from drifting from delta-domain physics."""

    reference_bits = np.asarray([605035526899.4789, 35818623467.93558])
    unilateral_bits = np.asarray(
        [
            [605022863453.9861, 35831688300.729614],
            [605063155861.6459, 35824157607.71982],
        ]
    )
    joint_bits = np.asarray([605040645185.1671, 35834419392.13486])
    reference_energy = 1000.0
    unilateral_energy = np.asarray([1000.804215736796, 1000.9537805128198])
    joint_energy = 1000.1763631196809
    members = np.asarray([0, 1], dtype=np.int64)
    legal = np.asarray([[True, True, False, False], [True, False, True, False]])
    production = build_coalition_residual_c3(
        B0_v=reference_bits,
        E0=reference_energy,
        Bu=unilateral_bits,
        Eu=unilateral_energy,
        BC=joint_bits,
        EC=joint_energy,
        coalition_user_ids=members,
        proposed_actions=np.asarray([1, 2], dtype=np.int64),
        lambda_bits_per_j=verifier.LAMBDA_BITS_PER_J,
        kappa_bits=verifier.KAPPA_BITS,
        action_count=4,
        reference_actions=np.asarray([0, 0], dtype=np.int64),
        legal_mask=legal,
    )
    independent = verifier._formula(
        np.vstack((reference_bits, unilateral_bits, joint_bits)),
        np.asarray(
            [reference_energy, unilateral_energy[0], unilateral_energy[1], joint_energy]
        ),
        members,
    )

    assert independent.joint_delta_bits == production.joint_delta_bits
    assert independent.joint_delta_energy == production.joint_delta_energy_j
    assert independent.joint_surplus == production.joint_surplus_bits
    assert independent.interaction_bits == production.interaction_bits
    assert independent.interaction_energy == production.interaction_energy_j
    assert independent.interaction_surplus == production.interaction_surplus_bits
    assert independent.equal_share == production.equal_share_bits
    np.testing.assert_array_equal(independent.own, production.own_bits)
    np.testing.assert_array_equal(independent.nonfocal, production.nonfocal_bits)
    np.testing.assert_array_equal(independent.z3, production.z3_bits)
    assert independent.residual == production.identity_residual_bits


def test_source_panel_uses_all_eight_worlds_and_does_not_hide_low_coverage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verifier, "USER_COUNT", 4)
    paths = []
    for world in verifier.WORLDS:
        root = tmp_path / str(world)
        root.mkdir()
        paths.append(_source_fixture(root, world=world))
    result = verifier.verify_source_panel_science(paths)
    assert result["pair_count"] == 8
    assert result["predicates"]["pair_coverage"] is False
    assert result["predicates"]["mechanics"] is True
    assert result["predicates"]["physical_signature"] is True
    assert result["positive_world_count"] == 8


def test_fit_panel_recomputes_exact_48_shards_and_placebo_separation(
    tmp_path: Path,
) -> None:
    paths = []
    for world in verifier.WORLDS:
        for seed in verifier.STUDENT_SEEDS:
            for arm in verifier.FIT_ARMS:
                root = tmp_path / str(world) / str(seed) / arm.lower()
                root.mkdir(parents=True)
                paths.append(
                    _fit_fixture(root, world=world, seed=seed, arm=arm)
                )
    result = verifier.verify_fit_panel_science(paths)
    assert result["fit_count"] == 48
    assert result["target_support_count"] == 32
    assert result["predicates"] == {
        "target_support": True,
        "held_out_learner": True,
        "world_stability": True,
    }
    assert result["informed_world_wins"] == 8
    assert result["aggregate"]["mean_informed_spearman"] == pytest.approx(1.0)
    assert result["aggregate"]["mean_placebo_sign_accuracy"] == pytest.approx(0.0)
