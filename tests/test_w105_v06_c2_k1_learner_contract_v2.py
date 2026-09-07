"""W-105 -- result-blind bounded C2-k1 learner contract v2.

The synthetic bundle in this file is deliberately a structurally valid,
non-authorising source verdict (G-E fails).  No real T1 outcome or
``AUTHORIZE_*`` verdict artifact is created.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import mcrl.runtime.ee_axis_v06_c2_k1_learner_contract_v2 as contract
from mcrl.runtime.ee_axis_v06_c2_k1_learner_contract_v2 import (
    ADAM_PARAMETERS,
    ACTION_DIM,
    BETA,
    BETA_HEX,
    C2K1LearnerContractV2Error,
    DESIGN_EVAL_SEEDS,
    FORMAL_LEARNER_VERDICT,
    FORMAL_VERDICT_ARTIFACT_SCHEMA,
    FORMAL_VERDICT_SEAL_SCHEMA,
    FROZEN_FREEZE_ROOT_RELATIVE,
    HIDDEN_WIDTHS,
    KAPPA_BITS,
    KAPPA_BITS_HEX,
    LEARNER_PLAN_SCHEMA,
    LINEAGES,
    Q13_INITIALIZATION_SEEDS,
    Q2_INITIALIZATION_SEEDS,
    Q2_UPDATE0_PARAMETER_SHA256,
    Q2_CLASS,
    ROWS_PER_LINEAGE,
    SOURCE_FALSIFIED_VERDICT,
    STATE_DIM,
    T1_ALGORITHM_SCHEMA,
    T1_SOURCE_SCHEMA,
    T1_SOURCE_RULE,
    TRAINING_CHECKPOINTS,
    TRAINING_STEPS,
    canonical_bytes,
    canonical_sha256,
    check_postgate_learner_plan,
    learner_plan_v2,
    verify_authenticated_formal_verdict,
    verify_learner_plan_v2,
)
from mcrl.runtime.ee_axis_state import (
    EE_AXIS_STATE_SCHEMA,
    EE_AXIS_STATE_SCHEMA_SHA256,
)


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def _payload_sha(payload: object) -> str:
    return canonical_sha256(payload)


def _write_json(path: Path, payload: dict[str, object]) -> str:
    path.write_bytes(canonical_bytes(payload))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _synthetic_bundle(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    """Write a non-authorising but fully authenticated synthetic bundle."""

    source_path = (tmp_path / "source.json").resolve()
    source_seal_path = (tmp_path / "source-seal.json").resolve()
    source_body: dict[str, object] = {
        "schema": T1_SOURCE_SCHEMA,
        "algorithm_schema": T1_ALGORITHM_SCHEMA,
        "source_rule": T1_SOURCE_RULE,
        "prepare_sha256": _digest("prepare"),
        "counts": {"anchors": 12, "lineages": 3, "opening_actions": 28,
                    "pairs": 1008, "controls": 36},
        "gates": {
            "G-M": {"passed": True},
            "G-E": {"passed": False},
            "G-S": {"passed": True},
            "launchable": False,
        },
        "training": False,
        "test_split_opened": False,
        "outcome_selection": False,
        "q2_consulted": False,
    }
    source_body["source_sha256"] = _payload_sha(source_body)
    source_file_sha = _write_json(source_path, source_body)
    source_seal: dict[str, object] = {
        "schema": "multi-catfish-mcrl-v06-c2-k1-t1-source-seal-v1",
        "source_sha256": _payload_sha(source_body),
        "source_file_sha256": source_file_sha,
        "prepare_sha256": source_body["prepare_sha256"],
        "training": False,
        "test_split_opened": False,
        "outcome_selection": False,
    }
    _write_json(source_seal_path, source_seal)
    source_seal_file_sha = hashlib.sha256(source_seal_path.read_bytes()).hexdigest()

    artifact_path = (tmp_path / "formal-verdict.json").resolve()
    artifact_body: dict[str, object] = {
        "schema": FORMAL_VERDICT_ARTIFACT_SCHEMA,
        "status": "VERIFIED",
        "disposition": SOURCE_FALSIFIED_VERDICT,
        "source_schema": T1_SOURCE_SCHEMA,
        "source_seal_schema": "multi-catfish-mcrl-v06-c2-k1-t1-source-seal-v1",
        "source_path": str(source_path),
        "source_file_sha256": source_file_sha,
        "source_payload_sha256": source_body["source_sha256"],
        "source_seal_path": str(source_seal_path),
        "source_seal_file_sha256": source_seal_file_sha,
        "prepare_sha256": source_body["prepare_sha256"],
        "t1_prereg_file_sha256": _digest("t1-prereg"),
        "verifier_code_authority_sha256": _digest("t1-verifier-code"),
        "counts": {"pairs": 1008, "controls": 36},
        "gates": source_body["gates"],
        "training": False,
        "test_split_opened": False,
        "outcome_selection": False,
        "q2_consulted": False,
        "write_once": True,
        "attempt": 1,
        "retry": False,
        "replacement": False,
    }
    artifact_body["verdict_sha256"] = _payload_sha(artifact_body)
    artifact_file_sha = _write_json(artifact_path, artifact_body)

    verdict_seal_path = (tmp_path / "formal-verdict-seal.json").resolve()
    verdict_seal: dict[str, object] = {
        "schema": FORMAL_VERDICT_SEAL_SCHEMA,
        "verdict_sha256": artifact_body["verdict_sha256"],
        "verdict_file_sha256": artifact_file_sha,
        "verdict_path": str(artifact_path),
        "source_path": str(source_path),
        "source_file_sha256": source_file_sha,
        "source_seal_path": str(source_seal_path),
        "source_seal_file_sha256": source_seal_file_sha,
        "prepare_sha256": source_body["prepare_sha256"],
        "t1_prereg_file_sha256": artifact_body["t1_prereg_file_sha256"],
        "verifier_code_authority_sha256": artifact_body[
            "verifier_code_authority_sha256"
        ],
        "write_once": True,
        "attempt": 1,
        "retry": False,
        "replacement": False,
        "training": False,
        "test_split_opened": False,
        "outcome_selection": False,
        "q2_consulted": False,
    }
    _write_json(verdict_seal_path, verdict_seal)
    return artifact_path, verdict_seal_path, source_path, source_seal_path


def test_plan_v2_is_exact_and_binds_all_frozen_learner_choices() -> None:
    plan = learner_plan_v2()

    assert plan["schema"] == LEARNER_PLAN_SCHEMA
    assert verify_learner_plan_v2(plan) == plan["plan_sha256"]
    assert plan["hyperparameters_bound"] is True
    assert plan["state"] == {
        "schema": EE_AXIS_STATE_SCHEMA,
        "schema_sha256": EE_AXIS_STATE_SCHEMA_SHA256,
        "dimension": STATE_DIM,
        "dtype": "float32",
        "action_dim": ACTION_DIM,
    }
    assert [item["lineage"] for item in plan["lineages"]] == list(LINEAGES)
    assert [item["q13_initialization_seed"] for item in plan["lineages"]] == list(
        Q13_INITIALIZATION_SEEDS
    )
    assert [item["q2_initialization_seed"] for item in plan["lineages"]] == list(
        Q2_INITIALIZATION_SEEDS
    )
    assert {
        item["lineage"]: item["q2_update0_parameter_sha256"]
        for item in plan["lineages"]
    } == Q2_UPDATE0_PARAMETER_SHA256
    assert plan["q2_architecture"] == {
        "name": "MaskedMeanMax",
        "class": Q2_CLASS,
        "hidden_widths": list(HIDDEN_WIDTHS),
        "activation": "tanh",
        "construction": (
            "torch.manual_seed(q2_seed); immediately instantiate exactly "
            "one MaskedMeanMaxQNetwork"
        ),
        "resident_legacy_q2_retained_in_authenticated_hybrid_container": True,
        "resident_legacy_q2_excluded_from_training_and_decision_path": True,
        "resident_legacy_q2_evaluated_or_summed": False,
    }
    assert plan["optimizer"] == ADAM_PARAMETERS
    assert plan["target_scale"] == {
        "kappa_bits": KAPPA_BITS,
        "kappa_bits_hex": KAPPA_BITS_HEX,
    }
    assert plan["gauge"] == {"beta": BETA, "beta_hex": BETA_HEX}
    assert plan["batch"] == {
        "worlds": 12,
        "actions": ACTION_DIM,
        "rows_per_lineage": ROWS_PER_LINEAGE,
        "total_rows": 1008,
        "mode": "full_batch",
        "order": "prepare_anchor_order_then_action_0_to_27",
        "shuffle": False,
        "replacement": False,
        "sign_filter": False,
    }
    assert plan["execution"] == {
        "freeze_root_relative": FROZEN_FREEZE_ROOT_RELATIVE,
        "single_global_freeze_root": True,
        "train_output_rule": "freeze/train-{lineage}",
        "design_eval_output_rule": "freeze/design-eval",
        "no_alternate_root": True,
    }
    assert plan["training"] == {
        "steps": TRAINING_STEPS,
        "checkpoints": list(TRAINING_CHECKPOINTS),
        "primary_checkpoint": 100,
        "device": "cpu",
        "deterministic": True,
        "torch_deterministic_algorithms": True,
        "torch_num_threads": 1,
        "update0_parameter_digests_sealed_pre_reveal": True,
        "output_path_rule": "freeze/train-{lineage}",
        "attempt_sealed_before_first_optimizer": True,
    }
    assert plan["design_eval"]["seeds"] == list(DESIGN_EVAL_SEEDS)
    assert plan["design_eval"]["arms"] == ["FULL", "DROP_C2"]
    assert (
        plan["design_eval"][
            "resident_legacy_q2_retained_in_authenticated_hybrid_container"
        ]
        is True
    )
    assert (
        plan["design_eval"]["resident_legacy_q2_evaluated_or_summed"]
        is False
    )
    assert plan["design_eval"]["route_state_inputs"]["Q3"] == "V0.4 C3 228-D state"
    assert plan["gates"]["G-E"]["positive_world_contrasts_min"] == 7
    assert plan["gates"]["G-S"]["nonnegative_lineage_contrasts_min"] == 2


@pytest.mark.parametrize("mutation", [
    "q2_seed",
    "hidden_width",
    "adam_eps",
    "row_count",
    "checkpoint",
    "design_eval_seed",
    "hyperparameters_bound",
])
def test_plan_verifier_rejects_any_choice_drift(mutation: str) -> None:
    plan = learner_plan_v2()
    if mutation == "q2_seed":
        plan["lineages"][0]["q2_initialization_seed"] = 1
    elif mutation == "hidden_width":
        plan["q2_architecture"]["hidden_widths"][0] = 99
    elif mutation == "adam_eps":
        plan["optimizer"]["eps"] = 1e-7
    elif mutation == "row_count":
        plan["batch"]["rows_per_lineage"] = 335
    elif mutation == "checkpoint":
        plan["training"]["checkpoints"][1] = 50
    elif mutation == "design_eval_seed":
        plan["design_eval"]["seeds"][0] = 1
    elif mutation == "hyperparameters_bound":
        plan["hyperparameters_bound"] = False
    else:  # pragma: no cover - protects the test itself
        raise AssertionError(mutation)
    with pytest.raises(C2K1LearnerContractV2Error):
        verify_learner_plan_v2(plan)


def test_plan_verifier_rejects_unknown_field_and_stale_digest() -> None:
    plan = learner_plan_v2()
    plan["unexpected"] = True
    with pytest.raises(C2K1LearnerContractV2Error, match="unknown"):
        verify_learner_plan_v2(plan)

    stale = learner_plan_v2()
    stale["plan_sha256"] = _digest("stale")
    with pytest.raises(C2K1LearnerContractV2Error, match="digest"):
        verify_learner_plan_v2(stale)


def test_authenticated_nonauthorising_bundle_is_accepted_without_training(tmp_path: Path) -> None:
    artifact_path, seal_path, source_path, source_seal_path = _synthetic_bundle(tmp_path)

    receipt = verify_authenticated_formal_verdict(
        artifact_path,
        seal_path,
        expected_source_path=source_path,
        expected_source_seal_path=source_seal_path,
    )
    assert receipt["status"] == "VERIFIED"
    assert receipt["disposition"] == SOURCE_FALSIFIED_VERDICT
    with pytest.raises(C2K1LearnerContractV2Error, match="authori[sz]ation"):
        check_postgate_learner_plan(
            learner_plan_v2(),
            formal_verdict_artifact_path=artifact_path,
            formal_verdict_seal_path=seal_path,
        )


def test_caller_literal_is_not_a_verdict_artifact(tmp_path: Path) -> None:
    plan = learner_plan_v2()
    with pytest.raises(C2K1LearnerContractV2Error):
        check_postgate_learner_plan(
            plan,
            formal_verdict_artifact_path=FORMAL_LEARNER_VERDICT,
            formal_verdict_seal_path=tmp_path / "missing-seal.json",
        )


def test_authorising_verdict_must_bind_the_plan_t1_prereg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        contract,
        "verify_authenticated_formal_verdict",
        lambda *_args, **_kwargs: {
            "disposition": FORMAL_LEARNER_VERDICT,
            "t1_prereg_file_sha256": _digest("wrong-t1-prereg"),
        },
    )
    with pytest.raises(C2K1LearnerContractV2Error, match="T1 preregistration"):
        contract.check_postgate_learner_plan(
            learner_plan_v2(),
            formal_verdict_artifact_path=tmp_path / "verdict.json",
            formal_verdict_seal_path=tmp_path / "verdict-seal.json",
        )


def test_authorization_receipt_exposes_verifier_code_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    verifier_sha = _digest("t1-verifier-code")
    monkeypatch.setattr(
        contract,
        "verify_authenticated_formal_verdict",
        lambda *_args, **_kwargs: {
            "disposition": FORMAL_LEARNER_VERDICT,
            "t1_prereg_file_sha256": learner_plan_v2()[
                "t1_prereg_file_sha256"
            ],
            "verdict_sha256": _digest("verdict"),
            "verdict_path": str((tmp_path / "verdict.json").resolve()),
            "formal_verdict_seal_path": str(
                (tmp_path / "verdict-seal.json").resolve()
            ),
            "verifier_code_authority_sha256": verifier_sha,
            "source_path": str((tmp_path / "source.json").resolve()),
        },
    )
    receipt = contract.check_postgate_learner_plan(
        learner_plan_v2(),
        formal_verdict_artifact_path=tmp_path / "verdict.json",
        formal_verdict_seal_path=tmp_path / "verdict-seal.json",
    )
    assert receipt["verifier_code_authority_sha256"] == verifier_sha


def test_authenticated_verdict_rejects_invalid_seal(tmp_path: Path) -> None:
    artifact_path, seal_path, _, _ = _synthetic_bundle(tmp_path)
    seal = json.loads(seal_path.read_text(encoding="ascii"))
    seal["verdict_file_sha256"] = _digest("wrong-file")
    seal_path.write_bytes(canonical_bytes(seal))
    with pytest.raises(C2K1LearnerContractV2Error, match="seal"):
        verify_authenticated_formal_verdict(artifact_path, seal_path)


def test_authenticated_verdict_rejects_source_drift(tmp_path: Path) -> None:
    artifact_path, seal_path, source_path, _ = _synthetic_bundle(tmp_path)
    source = json.loads(source_path.read_text(encoding="ascii"))
    source["prepare_sha256"] = _digest("drifted-source")
    source_path.write_bytes(canonical_bytes(source))
    with pytest.raises(C2K1LearnerContractV2Error, match="source"):
        verify_authenticated_formal_verdict(artifact_path, seal_path)


def test_authenticated_verdict_rejects_expected_source_path_drift(tmp_path: Path) -> None:
    artifact_path, seal_path, _, _ = _synthetic_bundle(tmp_path)
    with pytest.raises(C2K1LearnerContractV2Error, match="expected source path"):
        verify_authenticated_formal_verdict(
            artifact_path,
            seal_path,
            expected_source_path=(tmp_path / "different-source.json").resolve(),
        )


def test_fake_authorization_literal_cannot_override_authenticated_gate(tmp_path: Path) -> None:
    artifact_path, seal_path, _, _ = _synthetic_bundle(tmp_path)
    artifact = json.loads(artifact_path.read_text(encoding="ascii"))
    artifact["disposition"] = FORMAL_LEARNER_VERDICT
    body = dict(artifact)
    body.pop("verdict_sha256")
    artifact["verdict_sha256"] = _payload_sha(body)
    artifact_path.write_bytes(canonical_bytes(artifact))
    seal = json.loads(seal_path.read_text(encoding="ascii"))
    seal["verdict_sha256"] = artifact["verdict_sha256"]
    seal["verdict_file_sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    seal_path.write_bytes(canonical_bytes(seal))
    with pytest.raises(C2K1LearnerContractV2Error, match="G-E|disposition|launchable"):
        verify_authenticated_formal_verdict(artifact_path, seal_path)
