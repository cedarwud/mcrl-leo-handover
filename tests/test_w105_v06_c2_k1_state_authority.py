"""W-105 -- authenticated target-free V0.6 C2-k1 state authority."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from mcrl.runtime.ee_axis_state import EE_AXIS_STATE_DIM
from mcrl.runtime.ee_axis_v06_c2_k1 import (
    CLAIM_CEILING,
    POLICY_RULE,
    SCHEMA as ALGORITHM_SCHEMA,
    SOURCE_RULE,
)
from mcrl.runtime.ee_axis_v06_c2_k1_state_authority import (
    C2K1StateAuthorityError,
    FORMULA_CONTRACT,
    GATE_CONTRACT,
    LINEAGES,
    LINEAGE_SEEDS,
    PREPARE_SCHEMA,
    PREPARE_SEAL_SCHEMA,
    SOURCE_AUTHORITY,
    build_state_sidecar,
    canonical_sha256,
    capture_code_authority,
    file_sha256,
    live_verification_receipt,
    live_verification_seal,
    sidecar_seal,
    verify_formal_prepare_files,
    verify_live_verification_bundle,
    verify_sidecar_file_seal,
    verify_state_sidecar,
    write_once_json,
)


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def _write(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ),
        encoding="ascii",
    )


def _formal_prepare(tmp_path: Path) -> tuple[dict[str, object], Path, Path, Path]:
    t1 = tmp_path / "t1-prereg.md"
    t1.write_text("frozen t1 prereg\n", encoding="ascii")
    t1_sha = file_sha256(t1)
    files = {
        name: _digest(name)
        for name in (
            "live_adapter",
            "main_loader",
            "phase_b_loader",
            "runner",
            "runtime",
            "server_launcher",
            "support_scanner",
        )
    }
    anchors: list[dict[str, object]] = []
    bindings: dict[str, dict[str, object]] = {}
    for pool, worlds, step in (
        ("early", range(2026101001, 2026101005), 1),
        ("mid", range(2026101011, 2026101015), 3),
        ("late", range(2026101021, 2026101025), 5),
    ):
        for world in worlds:
            focal = (world % 97) + 1
            reference = world % 28
            actions = [action for action in range(28) if action != reference]
            physical = [[world + action + 1000, action] for action in range(28)]
            anchor = {
                "anchor_sha256": _digest(f"anchor-{world}"),
                "candidate_actions": actions,
                "candidate_physical_keys": [physical[action] for action in actions],
                "checkpoint_sha256": _digest("checkpoint"),
                "complete_forecast_horizon": True,
                "evaluation_seed": world,
                "focal_user": focal,
                "incumbent_physical_key": [world + 9000, 0],
                "legal_action_mask": [True] * 28,
                "physical_main_departure": True,
                "policy_sha256": _digest(f"policy-{world}"),
                "pool": pool,
                "predecision_only": True,
                "reference_action": reference,
                "reference_physical_key": physical[reference],
                "simulator_source_manifest_sha256": _digest("simulator"),
                "step": step,
                "world_anchor_sha256": _digest(f"world-{world}"),
                "world_id": world,
            }
            anchors.append(anchor)
            key = f"{pool}:{world}:{step}:{focal}"
            cell: dict[str, object] = {}
            for lineage, seed in zip(LINEAGES, LINEAGE_SEEDS, strict=True):
                scores = [float(action) for action in range(28)]
                cell[lineage] = {
                    "a_D": 27,
                    "crn_sha256": _digest(f"crn-{world}"),
                    "hybrid_sha256": _digest(f"hybrid-{lineage}"),
                    "initialization_seed": seed,
                    "q13_score_vector": scores,
                    "q1_sha256": _digest(f"q1-{lineage}"),
                    "q3_sha256": _digest(f"q3-{lineage}"),
                }
            bindings[key] = cell
    body: dict[str, object] = {
        "algorithm_schema": ALGORITHM_SCHEMA,
        "anchors": anchors,
        "claim_ceiling": CLAIM_CEILING,
        "code_authority": {"files": files, "sha256": canonical_sha256(files)},
        "counts": {
            "expected_controls": 36,
            "expected_pairs": 1008,
            "lineages": 3,
            "openings_per_anchor_lineage": 28,
            "pools": 3,
            "users": 100,
            "worlds": 12,
        },
        "formula_contract": FORMULA_CONTRACT,
        "gate_contract": GATE_CONTRACT,
        "lineage_bindings": bindings,
        "lineages": list(LINEAGES),
        "main_checkpoint_sha256": _digest("checkpoint"),
        "main_dir": "/sealed/main",
        "outcome_selection": False,
        "policy_rule": POLICY_RULE,
        "prepared_before_generation": True,
        "q13_gate_source_manifest_sha256": _digest("q13-source"),
        "q2_consulted": False,
        "schema": PREPARE_SCHEMA,
        "simulator_prereg_file_sha256": _digest("sim-prereg"),
        "simulator_source_manifest_sha256": _digest("simulator"),
        "source_authority": SOURCE_AUTHORITY,
        "source_rule": SOURCE_RULE,
        "t1_prereg_file_sha256": t1_sha,
        "test_split_opened": False,
        "training": False,
    }
    prepare = body | {"prepare_sha256": canonical_sha256(body)}
    prepare_path = tmp_path / "prepare-live.json"
    _write(prepare_path, prepare)
    seal = {
        "schema": PREPARE_SEAL_SCHEMA,
        "prepare_sha256": prepare["prepare_sha256"],
        "prepare_file_sha256": file_sha256(prepare_path),
        "training": False,
        "test_split_opened": False,
        "outcome_selection": False,
    }
    seal_path = tmp_path / "prepare-live-seal.json"
    _write(seal_path, seal)
    return prepare, prepare_path, seal_path, t1


def _captures(authority: dict[str, object], *, fill: float = 0.0) -> dict[str, dict[str, object]]:
    prepare = authority["prepare"]
    result: dict[str, dict[str, object]] = {}
    for index, (key, anchor) in enumerate(authority["anchor_map"].items()):
        cell = prepare["lineage_bindings"][key]
        result[key] = {
            "state": np.full(EE_AXIS_STATE_DIM, fill + index, dtype=np.float32),
            "action_mask": np.asarray(anchor["legal_action_mask"], dtype=np.bool_),
            "crn_sha256": cell["q13-a"]["crn_sha256"],
            "all_user_encoder_sha256": _digest(f"encoder-{fill}-{index}"),
            "main_reference_vector_sha256": _digest(f"reference-{index}"),
        }
    return result


def _code(tmp_path: Path) -> dict[str, object]:
    first = tmp_path / "capture.py"
    second = tmp_path / "encoder.py"
    first.write_text("capture-v1\n", encoding="ascii")
    second.write_text("encoder-v1\n", encoding="ascii")
    return capture_code_authority({"capture": first, "encoder": second})


def test_exact_prepare_and_float32_hex_sidecar_round_trip(tmp_path: Path) -> None:
    _, prepare_path, seal_path, t1 = _formal_prepare(tmp_path)
    authority = verify_formal_prepare_files(
        prepare_path=prepare_path,
        prepare_seal_path=seal_path,
        t1_prereg_path=t1,
    )
    learner = tmp_path / "learner.md"
    learner.write_text("frozen learner\n", encoding="ascii")
    code = _code(tmp_path)
    sidecar = build_state_sidecar(
        authority=authority,
        learner_prereg_file_sha256=file_sha256(learner),
        code_authority=code,
        captures=_captures(authority),
    )
    assert len(sidecar["anchors"]) == 12
    assert len(sidecar["anchors"][0]["state_float32_hex"]) == EE_AXIS_STATE_DIM
    assert all(
        isinstance(value, str)
        for value in sidecar["anchors"][0]["state_float32_hex"]
    )
    assert verify_state_sidecar(
        sidecar,
        authority=authority,
        learner_prereg_file_sha256=file_sha256(learner),
        code_authority=code,
        live_captures=_captures(authority),
    ) == sidecar["sidecar_sha256"]


def test_independent_live_replay_rejects_self_consistent_wrong_states(tmp_path: Path) -> None:
    _, prepare_path, seal_path, t1 = _formal_prepare(tmp_path)
    authority = verify_formal_prepare_files(
        prepare_path=prepare_path,
        prepare_seal_path=seal_path,
        t1_prereg_path=t1,
    )
    learner = tmp_path / "learner.md"
    learner.write_text("frozen learner\n", encoding="ascii")
    code = _code(tmp_path)
    zero = _captures(authority, fill=0.0)
    one = _captures(authority, fill=1.0)
    sidecar = build_state_sidecar(
        authority=authority,
        learner_prereg_file_sha256=file_sha256(learner),
        code_authority=code,
        captures=zero,
    )
    with pytest.raises(C2K1StateAuthorityError, match="live replay"):
        verify_state_sidecar(
            sidecar,
            authority=authority,
            learner_prereg_file_sha256=file_sha256(learner),
            code_authority=code,
            live_captures=one,
        )


def test_prepare_nested_unknown_outcome_field_fails_exact_schema(tmp_path: Path) -> None:
    prepare, prepare_path, seal_path, t1 = _formal_prepare(tmp_path)
    tampered = copy.deepcopy(prepare)
    tampered["source_authority"]["nested"] = {"target": 1.0}
    unsigned = dict(tampered)
    unsigned.pop("prepare_sha256")
    tampered["prepare_sha256"] = canonical_sha256(unsigned)
    _write(prepare_path, tampered)
    seal = {
        "schema": PREPARE_SEAL_SCHEMA,
        "prepare_sha256": tampered["prepare_sha256"],
        "prepare_file_sha256": file_sha256(prepare_path),
        "training": False,
        "test_split_opened": False,
        "outcome_selection": False,
    }
    _write(seal_path, seal)
    with pytest.raises(C2K1StateAuthorityError, match="source_authority"):
        verify_formal_prepare_files(
            prepare_path=prepare_path,
            prepare_seal_path=seal_path,
            t1_prereg_path=t1,
        )


def test_sidecar_file_seal_and_learner_prereg_are_bound(tmp_path: Path) -> None:
    _, prepare_path, prepare_seal_path, t1 = _formal_prepare(tmp_path)
    authority = verify_formal_prepare_files(
        prepare_path=prepare_path,
        prepare_seal_path=prepare_seal_path,
        t1_prereg_path=t1,
    )
    learner = tmp_path / "learner.md"
    learner.write_text("frozen learner\n", encoding="ascii")
    code = _code(tmp_path)
    sidecar = build_state_sidecar(
        authority=authority,
        learner_prereg_file_sha256=file_sha256(learner),
        code_authority=code,
        captures=_captures(authority),
    )
    sidecar_path = tmp_path / "state-sidecar.json"
    write_once_json(sidecar_path, sidecar)
    seal_path = tmp_path / "state-sidecar-seal.json"
    write_once_json(seal_path, sidecar_seal(sidecar, sidecar_path=sidecar_path))
    assert verify_sidecar_file_seal(
        sidecar=sidecar,
        sidecar_path=sidecar_path,
        seal_path=seal_path,
    ) == file_sha256(sidecar_path)
    receipt = live_verification_receipt(
        sidecar=sidecar,
        sidecar_path=sidecar_path,
        sidecar_seal_path=seal_path,
    )
    receipt_path = tmp_path / "state-live-verification.json"
    write_once_json(receipt_path, receipt)
    live_seal_path = tmp_path / "state-live-verification-seal.json"
    write_once_json(
        live_seal_path,
        live_verification_seal(receipt, receipt_path=receipt_path),
    )
    assert verify_live_verification_bundle(
        receipt_path=receipt_path,
        seal_path=live_seal_path,
        sidecar=sidecar,
        sidecar_path=sidecar_path,
        sidecar_seal_path=seal_path,
    ) == receipt["verification_sha256"]
    with pytest.raises(C2K1StateAuthorityError, match="learner_prereg"):
        verify_state_sidecar(
            sidecar,
            authority=authority,
            learner_prereg_file_sha256=_digest("other-learner"),
            code_authority=code,
        )
