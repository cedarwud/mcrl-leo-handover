#!/usr/bin/env python3
"""Frozen three-stage runner for the single V0.6 C2-k1 learner screen.

``freeze-update0`` is target-free and must run before T1 reveal.  It seals the
plan, runner/code bytes, and three deterministic update-0 Q2 checkpoints.
``train-lineage`` refuses to run without an authenticated authorising verdict
and trains exactly one 336-row Q2 for exactly 100 full-batch updates.
``evaluate`` accepts exactly three sealed update-100 lineages and runs the one
fixed 10-world matched FULL versus DROP_C2 DESIGN-EVAL block.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time
from typing import Any

import numpy as np

try:
    import torch
except ModuleNotFoundError:  # pragma: no cover - --help in a contract-only env
    torch = None  # type: ignore[assignment]


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.algorithms.ee_axis_v06_c2_k1 import (  # noqa: E402
    EEAxisV06C2K1Trainer,
    V06_C2_K1_LINEAGES,
    V06_C2_K1_SEED_BY_LINEAGE,
    V06_C2_K1_UPDATES,
    q2_parameter_sha256,
)
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_state import encode_ee_axis_state  # noqa: E402
from mcrl.runtime.ee_axis_v04_c3_state import (  # noqa: E402
    encode_ee_axis_v04_c3_state,
)
from mcrl.runtime.ee_axis_v06_c2_k1_q13 import (  # noqa: E402
    q13_surfaces_without_q2,
)
from mcrl.runtime.ee_axis_v06_c2_k1_learner import (  # noqa: E402
    DESIGN_EVAL_ROW_SCHEMA,
    G_L_RECEIPT_SCHEMA,
    adjudicate_design_eval,
    build_lineage_batch,
    canonical_sha256,
    compose_actions,
)
from mcrl.runtime.ee_axis_v06_c2_k1_learner_contract_v2 import (  # noqa: E402
    DESIGN_EVAL_FIELD_COMPONENT,
    DESIGN_EVAL_SEEDS,
    FORMAL_LEARNER_VERDICT,
    FROZEN_FREEZE_ROOT_RELATIVE,
    LINEAGES,
    Q2_UPDATE0_PARAMETER_SHA256,
    canonical_bytes,
    check_postgate_learner_plan,
    learner_plan_v2,
    verify_learner_plan_v2,
)
from mcrl.runtime.ee_axis_v06_c2_k1_state_authority import (  # noqa: E402
    build_state_sidecar,
    capture_code_authority,
    file_sha256,
    read_exact_json,
    verify_formal_prepare_files,
    verify_live_verification_bundle,
    verify_sidecar_file_seal,
    verify_state_sidecar,
)


FREEZE_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-pre-reveal-freeze-v1"
FREEZE_SEAL_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-pre-reveal-freeze-seal-v1"
PLAN_SEAL_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-bounded-learner-plan-seal-v2"
TRAIN_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-lineage-train-v1"
TRAIN_SEAL_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-lineage-train-seal-v1"
TRAIN_ATTEMPT_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-lineage-attempt-v1"
EVAL_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-bounded-evaluation-v1"
EVAL_SEAL_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-bounded-evaluation-seal-v1"
EVAL_ATTEMPT_SCHEMA = "multi-catfish-mcrl-v06-c2-k1-evaluation-attempt-v1"
FROZEN_FREEZE_ROOT = (
    REPO / FROZEN_FREEZE_ROOT_RELATIVE
).resolve()


class BoundedLearnerRunnerError(RuntimeError):
    """A bounded learner stage is stale, unauthorised, or malformed."""


def _require_torch() -> None:
    if torch is None:
        raise BoundedLearnerRunnerError("torch is required for learner execution")


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise BoundedLearnerRunnerError(f"{field} must be a lowercase SHA-256")
    return value


def _no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate JSON keys instead of silently keeping the last one."""

    result: dict[str, Any] = {}
    for key, item in pairs:
        if key in result:
            raise BoundedLearnerRunnerError(f"duplicate JSON key: {key}")
        result[key] = item
    return result


def _read_canonical(path: Path) -> tuple[dict[str, Any], str]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise BoundedLearnerRunnerError(f"missing regular JSON: {source}")
    raw = source.read_bytes()
    try:
        payload = json.loads(
            raw.decode("ascii"),
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
            object_pairs_hook=_no_duplicate_object,
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
        BoundedLearnerRunnerError,
    ) as error:
        raise BoundedLearnerRunnerError(f"invalid JSON: {source}") from error
    if not isinstance(payload, dict) or raw != canonical_bytes(payload):
        raise BoundedLearnerRunnerError(f"noncanonical JSON: {source}")
    return payload, hashlib.sha256(raw).hexdigest()


def _write_once_json(path: Path, payload: Mapping[str, Any]) -> str:
    destination = Path(path)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"refusing to overwrite: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_bytes(payload)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return hashlib.sha256(raw).hexdigest()


def _write_once_torch(path: Path, payload: Mapping[str, Any]) -> str:
    _require_torch()
    destination = Path(path)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"refusing to overwrite: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(descriptor)
    temporary = Path(name)
    try:
        torch.save(dict(payload), temporary)
        with temporary.open("rb") as stream:
            os.fsync(stream.fileno())
        os.link(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return file_sha256(destination)


def _read_torch(path: Path) -> Mapping[str, Any]:
    _require_torch()
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise BoundedLearnerRunnerError(f"missing regular checkpoint: {source}")
    try:
        payload = torch.load(source, map_location="cpu", weights_only=True)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        raise BoundedLearnerRunnerError(f"invalid checkpoint: {source}") from error
    if not isinstance(payload, Mapping):
        raise BoundedLearnerRunnerError("checkpoint root is not a mapping")
    return payload


def _refuse_output_dir(path: Path) -> None:
    destination = Path(path)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"refusing to overwrite output directory: {destination}")


def _require_output_path(path: Path, expected: Path, *, field: str) -> Path:
    candidate = Path(path).resolve(strict=False)
    authority = Path(expected).resolve(strict=False)
    if candidate != authority:
        raise BoundedLearnerRunnerError(
            f"{field} must be the single frozen path: {authority}"
        )
    return candidate


def _load_module(path: Path, label: str) -> Any:
    source = Path(path)
    name = label + "_" + hashlib.sha256(source.read_bytes()).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        raise BoundedLearnerRunnerError(f"cannot load {label}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def _t1_runner() -> Any:
    return _load_module(HERE / "run_v06_c2_k1_t1.py", "v06_t1_for_learner")


def _state_runner() -> Any:
    return _load_module(
        HERE / "run_v06_c2_k1_state_authority.py", "v06_state_for_learner"
    )


def _simulator_baseline_helper() -> Any:
    return _load_module(
        HERE / "v06_c2_k1_simulator_baseline.py",
        "v06_simulator_baseline_for_learner",
    )


def _learner_extension_sha256() -> dict[str, str]:
    helper = _simulator_baseline_helper()
    return {
        path: file_sha256(REPO / path)
        for path in helper.LEARNER_EXTENSION_PATHS
    }


def _authenticate_simulator_extension(
    *,
    t1: Any,
    prepare_path: Path,
    simulator_baseline: Path,
    simulator_baseline_seal: Path,
) -> dict[str, Any]:
    helper = _simulator_baseline_helper()
    return helper.verify_baseline_extension(
        support=t1._support_census_loader(),
        prepare_path=prepare_path,
        baseline_path=simulator_baseline,
        baseline_seal_path=simulator_baseline_seal,
        expected_extension_sha256=_learner_extension_sha256(),
    )


def _code_authority() -> dict[str, Any]:
    return capture_code_authority(
        {
            "bounded_runner": Path(__file__).resolve(),
            "errors": REPO / "src/mcrl/errors.py",
            "action_contract": REPO / "src/mcrl/env/action_contract.py",
            "keyed_fading": REPO / "src/mcrl/env/keyed_fading.py",
            "action_shared_meanmax": REPO
            / "src/mcrl/algorithms/ee_axis_action_shared_meanmax.py",
            "pairwise_trainer": REPO
            / "src/mcrl/algorithms/ee_axis_pairwise.py",
            "q2_only_trainer": REPO / "src/mcrl/algorithms/ee_axis_v06_c2_k1.py",
            "finiteness": REPO / "src/mcrl/runtime/finiteness.py",
            "learner_data": REPO / "src/mcrl/runtime/ee_axis_v06_c2_k1_learner.py",
            "learner_contract": REPO
            / "src/mcrl/runtime/ee_axis_v06_c2_k1_learner_contract_v2.py",
            "formal_verdict_writer": REPO
            / "src/mcrl/runtime/ee_axis_v06_c2_k1_formal_verdict_writer.py",
            "learner_prep": REPO
            / "src/mcrl/runtime/ee_axis_v06_c2_k1_learner_prep.py",
            "state_authority": REPO
            / "src/mcrl/runtime/ee_axis_v06_c2_k1_state_authority.py",
            "state_runner": HERE / "run_v06_c2_k1_state_authority.py",
            "state_encoder": REPO / "src/mcrl/runtime/ee_axis_state.py",
            "c3_state_encoder": REPO / "src/mcrl/runtime/ee_axis_v04_c3_state.py",
            "q13_without_q2": REPO
            / "src/mcrl/runtime/ee_axis_v06_c2_k1_q13.py",
            "live_adapter": HERE / "v06_c2_k1_live_adapter.py",
            "t1_runner": HERE / "run_v06_c2_k1_t1.py",
            "simulator_baseline_helper": HERE
            / "v06_c2_k1_simulator_baseline.py",
            "test_w102_t1_runner": REPO
            / "tests/test_w102_v06_c2_k1_t1_runner.py",
            "test_w103_live_adapter": REPO
            / "tests/test_w103_v06_c2_k1_live_adapter.py",
            "test_w104_learner_prep": REPO
            / "tests/test_w104_v06_c2_k1_learner_prep.py",
            "test_w105_state_authority": REPO
            / "tests/test_w105_v06_c2_k1_state_authority.py",
            "test_w105_learner_contract": REPO
            / "tests/test_w105_v06_c2_k1_learner_contract_v2.py",
            "test_w106_q2_only": REPO
            / "tests/test_w106_v06_c2_k1_q2_only.py",
            "test_w107_formal_verdict": REPO
            / "tests/test_w107_v06_c2_k1_formal_verdict_writer.py",
            "test_w107_learner_data": REPO
            / "tests/test_w107_v06_c2_k1_learner_data.py",
            "test_w108_bounded_freeze": REPO
            / "tests/test_w108_v06_c2_k1_bounded_runner_freeze.py",
            "test_w108_q13_without_q2": REPO
            / "tests/test_w108_v06_c2_k1_q13_without_q2.py",
            "test_w109_bounded_episode": REPO
            / "tests/test_w109_v06_c2_k1_bounded_episode.py",
            "test_w110_simulator_baseline": REPO
            / "tests/test_w110_v06_c2_k1_simulator_baseline.py",
        }
    )


def freeze_update0(
    *,
    learner_prereg: Path,
    prepare_path: Path,
    simulator_baseline: Path,
    simulator_baseline_seal: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Seal exact plan, code, and all fresh Q2 initial weights pre-reveal."""

    _require_torch()
    _refuse_output_dir(output_dir)
    root = _require_output_path(
        output_dir, FROZEN_FREEZE_ROOT, field="pre-reveal freeze output"
    )
    plan = learner_plan_v2()
    plan_sha = verify_learner_plan_v2(plan)
    prereg_sha = file_sha256(learner_prereg)
    code = _code_authority()
    prepare_resolved = Path(prepare_path).resolve()
    baseline_resolved = Path(simulator_baseline).resolve()
    baseline_seal_resolved = Path(simulator_baseline_seal).resolve()
    simulator_receipt = _authenticate_simulator_extension(
        t1=_t1_runner(),
        prepare_path=prepare_resolved,
        simulator_baseline=baseline_resolved,
        simulator_baseline_seal=baseline_seal_resolved,
    )
    simulator_receipt_sha = canonical_sha256(simulator_receipt)
    plan_path = root / "learner-plan-v2.json"
    plan_file_sha = _write_once_json(plan_path, plan)
    plan_seal = {
        "schema": PLAN_SEAL_SCHEMA,
        "plan_sha256": plan_sha,
        "plan_file_sha256": plan_file_sha,
        "learner_prereg_file_sha256": prereg_sha,
        "code_authority_sha256": code["sha256"],
        "prepare_sha256": simulator_receipt["prepare_sha256"],
        "simulator_baseline_sha256": simulator_receipt["baseline_sha256"],
        "simulator_extension_receipt_sha256": simulator_receipt_sha,
        "source_outcome_opened": False,
        "training_started": False,
        "test_split_opened": False,
    }
    plan_seal_path = root / "learner-plan-v2-seal.json"
    plan_seal_file_sha = _write_once_json(plan_seal_path, plan_seal)
    checkpoints: dict[str, Any] = {}
    for lineage in V06_C2_K1_LINEAGES:
        trainer = EEAxisV06C2K1Trainer(
            lineage=lineage, train_seed=V06_C2_K1_SEED_BY_LINEAGE[lineage]
        )
        expected = Q2_UPDATE0_PARAMETER_SHA256[lineage]
        if trainer.update0_parameter_sha256 != expected:
            raise BoundedLearnerRunnerError(
                f"update-0 Q2 digest drifted for {lineage}"
            )
        checkpoint_path = root / f"{lineage}-q2-update-000000.pt"
        checkpoint_file_sha = _write_once_torch(
            checkpoint_path, trainer.checkpoint_state()
        )
        checkpoints[lineage] = {
            "lineage": lineage,
            "train_seed": trainer.train_seed,
            "update": 0,
            "parameter_sha256": expected,
            "checkpoint_path": str(checkpoint_path.resolve()),
            "checkpoint_file_sha256": checkpoint_file_sha,
        }
    body: dict[str, Any] = {
        "schema": FREEZE_SCHEMA,
        "status": "PRE_REVEAL_FROZEN",
        "freeze_root": str(root),
        "plan_sha256": plan_sha,
        "plan_path": str(plan_path.resolve()),
        "plan_file_sha256": plan_file_sha,
        "plan_seal_path": str(plan_seal_path.resolve()),
        "plan_seal_file_sha256": plan_seal_file_sha,
        "learner_prereg_file_sha256": prereg_sha,
        "code_authority": code,
        "prepare_path": str(prepare_resolved),
        "prepare_file_sha256": file_sha256(prepare_resolved),
        "simulator_baseline_path": str(baseline_resolved),
        "simulator_baseline_seal_path": str(baseline_seal_resolved),
        "simulator_extension_receipt": simulator_receipt,
        "simulator_extension_receipt_sha256": simulator_receipt_sha,
        "update0_checkpoints": checkpoints,
        "lineages": list(V06_C2_K1_LINEAGES),
        "source_outcome_opened": False,
        "training_started": False,
        "test_split_opened": False,
        "outcome_selection": False,
        "retry": False,
        "replacement": False,
    }
    payload = body | {"freeze_sha256": canonical_sha256(body)}
    result_path = root / "pre-reveal-freeze.json"
    result_file_sha = _write_once_json(result_path, payload)
    seal = {
        "schema": FREEZE_SEAL_SCHEMA,
        "freeze_root": str(root),
        "freeze_sha256": payload["freeze_sha256"],
        "freeze_file_sha256": result_file_sha,
        "plan_sha256": plan_sha,
        "code_authority_sha256": code["sha256"],
        "learner_prereg_file_sha256": prereg_sha,
        "prepare_sha256": simulator_receipt["prepare_sha256"],
        "simulator_baseline_sha256": simulator_receipt["baseline_sha256"],
        "current_extended_manifest_sha256": simulator_receipt[
            "current_extended_manifest_sha256"
        ],
        "simulator_extension_receipt_sha256": simulator_receipt_sha,
        "source_outcome_opened": False,
        "training_started": False,
        "retry": False,
    }
    _write_once_json(root / "pre-reveal-freeze-seal.json", seal)
    return payload


def authenticate_freeze(
    freeze_dir: Path,
    *,
    learner_prereg: Path,
    prepare_path: Path | None = None,
    simulator_baseline: Path | None = None,
    simulator_baseline_seal: Path | None = None,
) -> dict[str, Any]:
    root = _require_output_path(
        freeze_dir, FROZEN_FREEZE_ROOT, field="authenticated pre-reveal freeze"
    )
    payload, payload_file_sha = _read_canonical(root / "pre-reveal-freeze.json")
    seal, _ = _read_canonical(root / "pre-reveal-freeze-seal.json")
    body = dict(payload)
    supplied = _digest(body.pop("freeze_sha256", None), field="freeze_sha256")
    code = _code_authority()
    prereg_sha = file_sha256(learner_prereg)
    frozen_prepare = Path(str(payload.get("prepare_path"))).resolve()
    frozen_baseline = Path(str(payload.get("simulator_baseline_path"))).resolve()
    frozen_baseline_seal = Path(
        str(payload.get("simulator_baseline_seal_path"))
    ).resolve()
    for supplied_path, frozen_path, field in (
        (prepare_path, frozen_prepare, "prepare"),
        (simulator_baseline, frozen_baseline, "simulator baseline"),
        (
            simulator_baseline_seal,
            frozen_baseline_seal,
            "simulator baseline seal",
        ),
    ):
        if supplied_path is not None and Path(supplied_path).resolve() != frozen_path:
            raise BoundedLearnerRunnerError(
                f"{field} path differs from the pre-reveal freeze"
            )
    simulator_receipt = _authenticate_simulator_extension(
        t1=_t1_runner(),
        prepare_path=frozen_prepare,
        simulator_baseline=frozen_baseline,
        simulator_baseline_seal=frozen_baseline_seal,
    )
    simulator_receipt_sha = canonical_sha256(simulator_receipt)
    if (
        payload.get("schema") != FREEZE_SCHEMA
        or payload.get("status") != "PRE_REVEAL_FROZEN"
        or payload.get("freeze_root") != str(root)
        or supplied != canonical_sha256(body)
        or payload.get("code_authority") != code
        or payload.get("learner_prereg_file_sha256") != prereg_sha
        or payload.get("prepare_file_sha256") != file_sha256(frozen_prepare)
        or payload.get("simulator_extension_receipt") != simulator_receipt
        or payload.get("simulator_extension_receipt_sha256")
        != simulator_receipt_sha
        or payload.get("source_outcome_opened") is not False
        or payload.get("training_started") is not False
        or payload.get("test_split_opened") is not False
        or payload.get("outcome_selection") is not False
        or payload.get("retry") is not False
        or payload.get("replacement") is not False
        or seal
        != {
            "schema": FREEZE_SEAL_SCHEMA,
            "freeze_root": str(root),
            "freeze_sha256": supplied,
            "freeze_file_sha256": payload_file_sha,
            "plan_sha256": payload.get("plan_sha256"),
            "code_authority_sha256": code["sha256"],
            "learner_prereg_file_sha256": prereg_sha,
            "prepare_sha256": simulator_receipt["prepare_sha256"],
            "simulator_baseline_sha256": simulator_receipt["baseline_sha256"],
            "current_extended_manifest_sha256": simulator_receipt[
                "current_extended_manifest_sha256"
            ],
            "simulator_extension_receipt_sha256": simulator_receipt_sha,
            "source_outcome_opened": False,
            "training_started": False,
            "retry": False,
        }
    ):
        raise BoundedLearnerRunnerError("pre-reveal freeze is stale or malformed")
    plan_path = Path(str(payload.get("plan_path")))
    plan_seal_path = Path(str(payload.get("plan_seal_path")))
    plan, plan_file_sha = _read_canonical(plan_path)
    plan_seal, plan_seal_file_sha = _read_canonical(plan_seal_path)
    plan_sha = verify_learner_plan_v2(plan)
    if (
        plan_sha != payload.get("plan_sha256")
        or plan_file_sha != payload.get("plan_file_sha256")
        or plan_seal_file_sha != payload.get("plan_seal_file_sha256")
        or plan_seal
        != {
            "schema": PLAN_SEAL_SCHEMA,
            "plan_sha256": plan_sha,
            "plan_file_sha256": plan_file_sha,
            "learner_prereg_file_sha256": prereg_sha,
            "code_authority_sha256": code["sha256"],
            "prepare_sha256": simulator_receipt["prepare_sha256"],
            "simulator_baseline_sha256": simulator_receipt["baseline_sha256"],
            "simulator_extension_receipt_sha256": simulator_receipt_sha,
            "source_outcome_opened": False,
            "training_started": False,
            "test_split_opened": False,
        }
    ):
        raise BoundedLearnerRunnerError("frozen learner plan is stale")
    checkpoints = payload.get("update0_checkpoints")
    if not isinstance(checkpoints, Mapping) or set(checkpoints) != set(LINEAGES):
        raise BoundedLearnerRunnerError("update-0 checkpoint coverage drifted")
    for lineage in LINEAGES:
        item = checkpoints[lineage]
        if not isinstance(item, Mapping):
            raise BoundedLearnerRunnerError("update-0 checkpoint receipt malformed")
        path = Path(str(item.get("checkpoint_path")))
        if (
            item.get("lineage") != lineage
            or item.get("train_seed") != V06_C2_K1_SEED_BY_LINEAGE[lineage]
            or item.get("update") != 0
            or item.get("parameter_sha256")
            != Q2_UPDATE0_PARAMETER_SHA256[lineage]
            or item.get("checkpoint_file_sha256") != file_sha256(path)
        ):
            raise BoundedLearnerRunnerError("update-0 checkpoint authority drifted")
        trainer = EEAxisV06C2K1Trainer(
            lineage=lineage, train_seed=V06_C2_K1_SEED_BY_LINEAGE[lineage]
        )
        trainer.load_checkpoint_state(_read_torch(path))
        if trainer.update_count != 0 or q2_parameter_sha256(trainer.q2) != Q2_UPDATE0_PARAMETER_SHA256[lineage]:
            raise BoundedLearnerRunnerError("update-0 checkpoint bytes drifted")
    return {
        "payload": payload,
        "plan": plan,
        "root": root,
        "prepare_path": frozen_prepare,
        "simulator_baseline_path": frozen_baseline,
        "simulator_baseline_seal_path": frozen_baseline_seal,
        "simulator_extension_receipt": simulator_receipt,
    }


def _state_authority_bundle(
    *,
    prepare_path: Path,
    prepare_seal_path: Path,
    t1_prereg_path: Path,
    learner_prereg_path: Path,
    sidecar_path: Path,
    sidecar_seal_path: Path,
    live_verification_path: Path,
    live_verification_seal_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    authority = verify_formal_prepare_files(
        prepare_path=prepare_path,
        prepare_seal_path=prepare_seal_path,
        t1_prereg_path=t1_prereg_path,
    )
    sidecar = read_exact_json(sidecar_path)
    state_code = _state_runner()._code_authority()
    learner_sha = file_sha256(learner_prereg_path)
    verify_state_sidecar(
        sidecar,
        authority=authority,
        learner_prereg_file_sha256=learner_sha,
        code_authority=state_code,
    )
    verify_sidecar_file_seal(
        sidecar=sidecar,
        sidecar_path=sidecar_path,
        seal_path=sidecar_seal_path,
    )
    verify_live_verification_bundle(
        receipt_path=live_verification_path,
        seal_path=live_verification_seal_path,
        sidecar=sidecar,
        sidecar_path=sidecar_path,
        sidecar_seal_path=sidecar_seal_path,
    )
    return authority, sidecar


def train_lineage(
    *,
    lineage: str,
    freeze_dir: Path,
    learner_prereg: Path,
    formal_verdict: Path,
    formal_verdict_seal: Path,
    source_path: Path,
    source_seal_path: Path,
    prepare_path: Path,
    prepare_seal_path: Path,
    t1_prereg: Path,
    sidecar_path: Path,
    sidecar_seal_path: Path,
    live_verification_path: Path,
    live_verification_seal_path: Path,
    simulator_baseline: Path,
    simulator_baseline_seal: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Train one exact Q2 lineage only after formal source authorization."""

    _require_torch()
    if lineage not in LINEAGES:
        raise BoundedLearnerRunnerError("lineage is not frozen")
    _refuse_output_dir(output_dir)
    frozen = authenticate_freeze(
        freeze_dir,
        learner_prereg=learner_prereg,
        prepare_path=prepare_path,
        simulator_baseline=simulator_baseline,
        simulator_baseline_seal=simulator_baseline_seal,
    )
    root = _require_output_path(
        output_dir,
        frozen["root"] / f"train-{lineage}",
        field="lineage training output",
    )
    expected_verdict_dir = Path(frozen["root"]).resolve() / "formal-verdict"
    if (
        Path(formal_verdict).resolve().parent != expected_verdict_dir
        or Path(formal_verdict_seal).resolve().parent != expected_verdict_dir
    ):
        raise BoundedLearnerRunnerError(
            "formal verdict must use the single frozen formal-verdict directory"
        )
    authorization = check_postgate_learner_plan(
        frozen["plan"],
        formal_verdict_artifact_path=formal_verdict,
        formal_verdict_seal_path=formal_verdict_seal,
        expected_source_path=source_path,
        expected_source_seal_path=source_seal_path,
    )
    if authorization.get("formal_verdict") != FORMAL_LEARNER_VERDICT:
        raise BoundedLearnerRunnerError("formal verdict did not authorize learner")
    authority, sidecar = _state_authority_bundle(
        prepare_path=prepare_path,
        prepare_seal_path=prepare_seal_path,
        t1_prereg_path=t1_prereg,
        learner_prereg_path=learner_prereg,
        sidecar_path=sidecar_path,
        sidecar_seal_path=sidecar_seal_path,
        live_verification_path=live_verification_path,
        live_verification_seal_path=live_verification_seal_path,
    )
    if (
        authorization.get("verifier_code_authority_sha256")
        != authority["prepare"]["code_authority"]["sha256"]
    ):
        raise BoundedLearnerRunnerError(
            "formal-verdict verifier code differs from frozen PREPARE"
        )
    t1 = _t1_runner()
    prepared = t1._read_formal_prepare(prepare_path, t1_prereg)
    simulator_receipt = _authenticate_simulator_extension(
        t1=t1,
        prepare_path=prepare_path,
        simulator_baseline=simulator_baseline,
        simulator_baseline_seal=simulator_baseline_seal,
    )
    if (
        simulator_receipt["simulator_source_manifest_sha256"]
        != prepared["simulator_source_manifest_sha256"]
        or simulator_receipt != frozen["simulator_extension_receipt"]
    ):
        raise BoundedLearnerRunnerError(
            "lineage training simulator baseline disagrees with PREPARE"
        )
    source = t1._canonical_read(source_path)
    receipt = t1.verify_source(source, prepared)
    if receipt.get("disposition") != FORMAL_LEARNER_VERDICT:
        raise BoundedLearnerRunnerError("T1 source re-verification did not authorize")
    batch, batch_receipt = build_lineage_batch(
        source=source, sidecar=sidecar, lineage=lineage
    )
    checkpoint_item = frozen["payload"]["update0_checkpoints"][lineage]
    trainer = EEAxisV06C2K1Trainer(
        lineage=lineage, train_seed=V06_C2_K1_SEED_BY_LINEAGE[lineage]
    )
    trainer.load_checkpoint_state(
        _read_torch(Path(checkpoint_item["checkpoint_path"]))
    )
    attempt = {
        "schema": TRAIN_ATTEMPT_SCHEMA,
        "lineage": lineage,
        "freeze_sha256": frozen["payload"]["freeze_sha256"],
        "plan_sha256": frozen["payload"]["plan_sha256"],
        "formal_verdict_sha256": authorization["formal_verdict_sha256"],
        "source_sha256": source["source_sha256"],
        "sidecar_sha256": sidecar["sidecar_sha256"],
        "simulator_baseline_sha256": simulator_receipt["baseline_sha256"],
        "current_extended_manifest_sha256": simulator_receipt[
            "current_extended_manifest_sha256"
        ],
        "updates_authorized": 100,
        "training_started": True,
        "test_split_opened": False,
        "attempt": 1,
        "retry": False,
        "replacement": False,
    }
    attempt_path = root / "attempt.json"
    attempt_file_sha = _write_once_json(attempt_path, attempt)
    loss0 = trainer.loss_diagnostics(batch)
    started = time.perf_counter()
    last: dict[str, Any] | None = None
    for _ in range(V06_C2_K1_UPDATES):
        last = trainer.update(batch)
    if last is None or trainer.update_count != 100:
        raise BoundedLearnerRunnerError("Q2 did not complete exactly 100 updates")
    loss100 = trainer.loss_diagnostics(batch)
    checkpoint_path = root / f"{lineage}-q2-update-000100.pt"
    checkpoint_file_sha = _write_once_torch(
        checkpoint_path, trainer.checkpoint_state()
    )
    reloaded = EEAxisV06C2K1Trainer(
        lineage=lineage, train_seed=V06_C2_K1_SEED_BY_LINEAGE[lineage]
    )
    reloaded.load_checkpoint_state(_read_torch(checkpoint_path))
    parameter_sha = q2_parameter_sha256(reloaded.q2)
    body = {
        "schema": TRAIN_SCHEMA,
        "status": "LINEAGE_TRAINED_UPDATE_100",
        "lineage": lineage,
        "train_seed": trainer.train_seed,
        "updates": 100,
        "rows": 336,
        "freeze_sha256": frozen["payload"]["freeze_sha256"],
        "plan_sha256": frozen["payload"]["plan_sha256"],
        "formal_verdict_sha256": authorization["formal_verdict_sha256"],
        "source_sha256": source["source_sha256"],
        "prepare_sha256": authority["prepare_sha256"],
        "sidecar_sha256": sidecar["sidecar_sha256"],
        "simulator_baseline_sha256": simulator_receipt["baseline_sha256"],
        "current_extended_manifest_sha256": simulator_receipt[
            "current_extended_manifest_sha256"
        ],
        "batch_receipt": batch_receipt,
        "attempt_path": str(attempt_path.resolve()),
        "attempt_file_sha256": attempt_file_sha,
        "loss_update_0": loss0,
        "loss_update_100": loss100,
        "update100_parameter_sha256": parameter_sha,
        "checkpoint_path": str(checkpoint_path.resolve()),
        "checkpoint_file_sha256": checkpoint_file_sha,
        "elapsed_s": float(time.perf_counter() - started),
        "q1_q3_loaded": False,
        "resident_legacy_q2_loaded": False,
        "q2_only_optimizer": True,
        "training_started": True,
        "test_split_opened": False,
        "episode_training": False,
        "retry": False,
        "replacement": False,
    }
    payload = body | {"train_sha256": canonical_sha256(body)}
    result_path = root / "train-result.json"
    result_file_sha = _write_once_json(result_path, payload)
    _write_once_json(
        root / "train-seal.json",
        {
            "schema": TRAIN_SEAL_SCHEMA,
            "train_sha256": payload["train_sha256"],
            "train_file_sha256": result_file_sha,
            "lineage": lineage,
            "checkpoint_file_sha256": checkpoint_file_sha,
            "source_sha256": source["source_sha256"],
            "formal_verdict_sha256": authorization["formal_verdict_sha256"],
            "updates": 100,
            "test_split_opened": False,
            "retry": False,
        },
    )
    return payload


def authenticate_train_dir(
    path: Path, *, expected_lineage: str, frozen: Mapping[str, Any]
) -> tuple[dict[str, Any], EEAxisV06C2K1Trainer]:
    frozen_payload = frozen.get("payload")
    if not isinstance(frozen_payload, Mapping) or "root" not in frozen:
        raise BoundedLearnerRunnerError("authenticated freeze bundle is malformed")
    root = Path(path)
    payload, payload_file_sha = _read_canonical(root / "train-result.json")
    seal, _ = _read_canonical(root / "train-seal.json")
    body = dict(payload)
    supplied = _digest(body.pop("train_sha256", None), field="train_sha256")
    if (
        payload.get("schema") != TRAIN_SCHEMA
        or payload.get("status") != "LINEAGE_TRAINED_UPDATE_100"
        or payload.get("lineage") != expected_lineage
        or payload.get("train_seed")
        != V06_C2_K1_SEED_BY_LINEAGE[expected_lineage]
        or payload.get("updates") != 100
        or payload.get("rows") != 336
        or payload.get("freeze_sha256") != frozen_payload["freeze_sha256"]
        or payload.get("plan_sha256") != frozen_payload["plan_sha256"]
        or supplied != canonical_sha256(body)
        or payload.get("q1_q3_loaded") is not False
        or payload.get("resident_legacy_q2_loaded") is not False
        or payload.get("q2_only_optimizer") is not True
        or payload.get("training_started") is not True
        or payload.get("test_split_opened") is not False
        or payload.get("episode_training") is not False
        or payload.get("retry") is not False
        or payload.get("replacement") is not False
        or seal
        != {
            "schema": TRAIN_SEAL_SCHEMA,
            "train_sha256": supplied,
            "train_file_sha256": payload_file_sha,
            "lineage": expected_lineage,
            "checkpoint_file_sha256": payload.get("checkpoint_file_sha256"),
            "source_sha256": payload.get("source_sha256"),
            "formal_verdict_sha256": payload.get("formal_verdict_sha256"),
            "updates": 100,
            "test_split_opened": False,
            "retry": False,
        }
    ):
        raise BoundedLearnerRunnerError("lineage training receipt drifted")
    expected_root = Path(frozen["root"]).resolve() / f"train-{expected_lineage}"
    if root.resolve() != expected_root:
        raise BoundedLearnerRunnerError("lineage training directory is not frozen")
    attempt_path = Path(str(payload.get("attempt_path")))
    attempt, attempt_file_sha = _read_canonical(attempt_path)
    if (
        attempt_path.resolve() != root.resolve() / "attempt.json"
        or attempt_file_sha != payload.get("attempt_file_sha256")
        or attempt
        != {
            "schema": TRAIN_ATTEMPT_SCHEMA,
            "lineage": expected_lineage,
            "freeze_sha256": frozen_payload["freeze_sha256"],
            "plan_sha256": frozen_payload["plan_sha256"],
            "formal_verdict_sha256": payload.get("formal_verdict_sha256"),
            "source_sha256": payload.get("source_sha256"),
            "sidecar_sha256": payload.get("sidecar_sha256"),
            "simulator_baseline_sha256": payload.get(
                "simulator_baseline_sha256"
            ),
            "current_extended_manifest_sha256": payload.get(
                "current_extended_manifest_sha256"
            ),
            "updates_authorized": 100,
            "training_started": True,
            "test_split_opened": False,
            "attempt": 1,
            "retry": False,
            "replacement": False,
        }
    ):
        raise BoundedLearnerRunnerError("lineage training attempt seal drifted")
    checkpoint_path = Path(str(payload.get("checkpoint_path")))
    if file_sha256(checkpoint_path) != payload.get("checkpoint_file_sha256"):
        raise BoundedLearnerRunnerError("update-100 checkpoint file drifted")
    trainer = EEAxisV06C2K1Trainer(
        lineage=expected_lineage,
        train_seed=V06_C2_K1_SEED_BY_LINEAGE[expected_lineage],
    )
    trainer.load_checkpoint_state(_read_torch(checkpoint_path))
    if trainer.update_count != 100 or q2_parameter_sha256(trainer.q2) != payload.get("update100_parameter_sha256"):
        raise BoundedLearnerRunnerError("update-100 checkpoint parameters drifted")
    return payload, trainer


def _array_sha256(*arrays: object) -> str:
    digest = hashlib.sha256()
    for raw in arrays:
        value = np.ascontiguousarray(np.asarray(raw))
        digest.update(str(value.dtype).encode("ascii"))
        digest.update(json.dumps(list(value.shape), separators=(",", ":")).encode("ascii"))
        digest.update(value.tobytes())
    return digest.hexdigest()


def _snapshot_q13_networks(
    hybrid: Any,
) -> dict[str, dict[str, np.ndarray]]:
    """Copy only Q1/Q3 parameters; never access resident legacy Q2."""

    snapshot: dict[str, dict[str, np.ndarray]] = {}
    for route in ("q1", "q3"):
        network = getattr(hybrid, route, None)
        if network is None:
            raise BoundedLearnerRunnerError(
                f"DESIGN-EVAL hybrid lacks frozen {route.upper()}"
            )
        state = network.state_dict()
        if not isinstance(state, Mapping):
            raise BoundedLearnerRunnerError(
                f"DESIGN-EVAL frozen {route.upper()} state is malformed"
            )
        snapshot[route] = {
            str(name): np.asarray(value.detach().cpu().numpy()).copy()
            for name, value in state.items()
        }
    return snapshot


def _same_q13_networks(
    hybrid: Any, before: Mapping[str, Mapping[str, np.ndarray]]
) -> bool:
    after = _snapshot_q13_networks(hybrid)
    return set(after) == set(before) and all(
        set(after[route]) == set(before[route])
        and all(
            np.array_equal(after[route][name], before[route][name])
            for name in before[route]
        )
        for route in before
    )


def _design_field(prepare: Mapping[str, Any], seed: int) -> KeyedFadingField:
    return KeyedFadingField.from_components(
        DESIGN_EVAL_FIELD_COMPONENT,
        prepare["simulator_source_manifest_sha256"],
        prepare["main_checkpoint_sha256"],
        prepare["simulator_prereg_file_sha256"],
        int(seed),
    )


def _episode(
    *,
    live: Any,
    runtime: Any,
    hybrid: Any,
    trainer: EEAxisV06C2K1Trainer,
    prepare: Mapping[str, Any],
    evaluation_seed: int,
    arm: str,
) -> dict[str, Any]:
    if arm not in {"FULL", "DROP_C2"}:
        raise BoundedLearnerRunnerError("unknown evaluation arm")
    field = _design_field(prepare, evaluation_seed)
    wrapped = runtime.make_environment(runtime.archive, users=100)
    runtime.bind_field(wrapped, field)
    env_rng, mobility_rng, *_ = runtime.evaluation_rngs(evaluation_seed)
    states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    environment = getattr(wrapped, "environment", wrapped)
    interval_s = float(environment.driver.config.ephemeris.time_step_s)
    total_bits = 0.0
    total_energy = 0.0
    served_user_steps = 0
    action_trace: list[list[int]] = []
    q2_samples: list[float] = []
    q13_samples: list[float] = []
    complete_support = 0
    decision_rows = 0
    first_state_sha = ""
    first_c3_state_sha = ""
    first_mask_sha = ""
    for step in range(10):
        environment = getattr(wrapped, "environment", wrapped)
        legacy = encode_ee_axis_state(environment, observation)
        c3 = encode_ee_axis_v04_c3_state(
            environment,
            observation,
            interval_s=interval_s,
            kappa_bits=float(prepare["formula_contract"]["kappa_bits"]),
        )
        q1, q3, legal = q13_surfaces_without_q2(
            hybrid,
            legacy.state_matrix,
            c3.state_matrix,
            np.asarray(observation.masks),
        )
        if step == 0:
            first_state_sha = _array_sha256(legacy.state_matrix)
            first_c3_state_sha = _array_sha256(c3.state_matrix)
            first_mask_sha = _array_sha256(legal)
        q2 = None
        if arm == "FULL":
            q2 = trainer.q2_values(
                np.asarray(legacy.state_matrix), np.asarray(legal, dtype=np.bool_)
            )
        actions = compose_actions(
            q1=q1,
            q3=q3,
            masks=legal,
            q2=q2,
        )
        action_trace.append([int(value) for value in actions.tolist()])
        legal_array = np.asarray(legal, dtype=np.bool_)
        eligible = np.any(legal_array, axis=1)
        if bool(np.any(eligible)) and q2 is not None:
            q2_samples.extend(
                np.abs(q2[eligible][legal_array[eligible]]).astype(float).tolist()
            )
        if bool(np.any(eligible)):
            q13 = np.asarray(q1 + q3)
            q13_samples.extend(
                np.abs(q13[eligible][legal_array[eligible]]).astype(float).tolist()
            )
        complete_support += int(np.count_nonzero(np.all(legal_array, axis=1)))
        decision_rows += int(legal_array.shape[0])
        result = wrapped.step(actions, env_rng)
        outcome = wrapped.last_outcome
        rates = np.asarray(outcome.link_rate_bps, dtype=np.float64)
        power = float(outcome.system_power_w)
        if rates.shape != (100,) or not np.all(np.isfinite(rates)) or np.any(rates < 0.0) or not math.isfinite(power) or power <= 0.0:
            raise BoundedLearnerRunnerError("DESIGN-EVAL physical output malformed")
        total_bits += math.fsum(float(value) for value in rates) * interval_s
        total_energy += power * interval_s
        served_user_steps += int(outcome.resolution.served_count)
        if step < 9:
            if bool(result.done):
                raise BoundedLearnerRunnerError("DESIGN-EVAL ended before ten steps")
            observation = outcome.observation
        elif not bool(result.done):
            raise BoundedLearnerRunnerError("DESIGN-EVAL did not end at ten steps")
    body = {
        "schema": DESIGN_EVAL_ROW_SCHEMA,
        "evaluation_seed": evaluation_seed,
        "lineage": trainer.lineage,
        "arm": arm,
        "steps": 10,
        "users": 100,
        "decision_count": 1000,
        "total_bits": float(total_bits),
        "total_energy_j": float(total_energy),
        "served_user_steps": int(served_user_steps),
        "ratio_of_sums_ee_bits_per_j": float(total_bits / total_energy),
        "fading_field_sha256": field.root_digest,
        "initial_state_sha256": first_state_sha,
        "initial_c3_state_sha256": first_c3_state_sha,
        "initial_mask_sha256": first_mask_sha,
        "actions": action_trace,
        "action_trace_sha256": canonical_sha256(action_trace),
        "q2_surface_median_abs": float(np.median(q2_samples)) if q2_samples else 0.0,
        "q13_surface_median_abs": float(np.median(q13_samples)) if q13_samples else 0.0,
        "q2_to_q13_magnitude": (
            float(np.median(q2_samples) / np.median(q13_samples))
            if (
                q2_samples
                and q13_samples
                and float(np.median(q13_samples)) > 0.0
            )
            else 0.0
        ),
        "complete_28_action_support_fraction": float(complete_support / decision_rows),
        "resident_legacy_q2_consulted": False,
        "route_state_contract": "Q1_Q2_V03__Q3_V04C3",
        "test_split_opened": False,
        "episode_training": False,
    }
    return body | {"row_sha256": canonical_sha256(body)}


def evaluate(
    *,
    freeze_dir: Path,
    learner_prereg: Path,
    train_dirs: Mapping[str, Path],
    formal_verdict: Path,
    formal_verdict_seal: Path,
    source_path: Path,
    source_seal_path: Path,
    prepare_path: Path,
    prepare_seal_path: Path,
    t1_prereg: Path,
    sidecar_path: Path,
    sidecar_seal_path: Path,
    live_verification_path: Path,
    live_verification_seal_path: Path,
    tle_root: Path,
    simulator_prereg: Path,
    main_dir: Path,
    gate_dir: Path,
    q13_source_dir: Path,
    v03_root: Path,
    simulator_baseline: Path,
    simulator_baseline_seal: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Run the one heavy matched DESIGN-EVAL only after all Q2 seals exist."""

    _require_torch()
    _refuse_output_dir(output_dir)
    frozen = authenticate_freeze(
        freeze_dir,
        learner_prereg=learner_prereg,
        prepare_path=prepare_path,
        simulator_baseline=simulator_baseline,
        simulator_baseline_seal=simulator_baseline_seal,
    )
    root = _require_output_path(
        output_dir,
        frozen["root"] / "design-eval",
        field="DESIGN-EVAL output",
    )
    expected_verdict_dir = Path(frozen["root"]).resolve() / "formal-verdict"
    if (
        Path(formal_verdict).resolve().parent != expected_verdict_dir
        or Path(formal_verdict_seal).resolve().parent != expected_verdict_dir
    ):
        raise BoundedLearnerRunnerError(
            "DESIGN-EVAL formal verdict is outside the frozen directory"
        )
    authorization = check_postgate_learner_plan(
        frozen["plan"],
        formal_verdict_artifact_path=formal_verdict,
        formal_verdict_seal_path=formal_verdict_seal,
        expected_source_path=source_path,
        expected_source_seal_path=source_seal_path,
    )
    authority, sidecar = _state_authority_bundle(
        prepare_path=prepare_path,
        prepare_seal_path=prepare_seal_path,
        t1_prereg_path=t1_prereg,
        learner_prereg_path=learner_prereg,
        sidecar_path=sidecar_path,
        sidecar_seal_path=sidecar_seal_path,
        live_verification_path=live_verification_path,
        live_verification_seal_path=live_verification_seal_path,
    )
    if (
        authorization.get("verifier_code_authority_sha256")
        != authority["prepare"]["code_authority"]["sha256"]
    ):
        raise BoundedLearnerRunnerError(
            "formal-verdict verifier code differs from frozen PREPARE"
        )
    t1 = _t1_runner()
    prepared = t1._read_formal_prepare(prepare_path, t1_prereg)
    if prepared != authority["prepare"]:
        raise BoundedLearnerRunnerError("DESIGN-EVAL prepare verifiers disagree")
    simulator_receipt = _authenticate_simulator_extension(
        t1=t1,
        prepare_path=prepare_path,
        simulator_baseline=simulator_baseline,
        simulator_baseline_seal=simulator_baseline_seal,
    )
    if (
        simulator_receipt["simulator_source_manifest_sha256"]
        != prepared["simulator_source_manifest_sha256"]
        or simulator_receipt != frozen["simulator_extension_receipt"]
    ):
        raise BoundedLearnerRunnerError(
            "DESIGN-EVAL simulator baseline disagrees with PREPARE"
        )
    source = t1._canonical_read(source_path)
    source_receipt = t1.verify_source(source, prepared)
    if source_receipt.get("disposition") != FORMAL_LEARNER_VERDICT:
        raise BoundedLearnerRunnerError("DESIGN-EVAL source no longer authorizes")
    if set(train_dirs) != set(LINEAGES):
        raise BoundedLearnerRunnerError("evaluate requires exactly three train dirs")
    train_receipts: dict[str, Any] = {}
    trainers: dict[str, EEAxisV06C2K1Trainer] = {}
    for lineage in LINEAGES:
        receipt, trainer = authenticate_train_dir(
            train_dirs[lineage], expected_lineage=lineage, frozen=frozen
        )
        train_receipts[lineage] = receipt
        trainers[lineage] = trainer
        _, batch_receipt = build_lineage_batch(
            source=source,
            sidecar=sidecar,
            lineage=lineage,
        )
        if receipt.get("batch_receipt") != batch_receipt:
            raise BoundedLearnerRunnerError(
                f"trained Q2 batch authority drifted for {lineage}"
            )
    if len({receipt["formal_verdict_sha256"] for receipt in train_receipts.values()}) != 1 or len({receipt["source_sha256"] for receipt in train_receipts.values()}) != 1 or len({receipt["sidecar_sha256"] for receipt in train_receipts.values()}) != 1:
        raise BoundedLearnerRunnerError("three train lineages do not share one authority")
    for receipt in train_receipts.values():
        if (
            receipt.get("formal_verdict_sha256")
            != authorization["formal_verdict_sha256"]
            or receipt.get("source_sha256") != source["source_sha256"]
            or receipt.get("prepare_sha256") != authority["prepare_sha256"]
            or receipt.get("sidecar_sha256") != sidecar["sidecar_sha256"]
            or receipt.get("plan_sha256") != frozen["payload"]["plan_sha256"]
            or receipt.get("simulator_baseline_sha256")
            != simulator_receipt["baseline_sha256"]
            or receipt.get("current_extended_manifest_sha256")
            != simulator_receipt["current_extended_manifest_sha256"]
        ):
            raise BoundedLearnerRunnerError(
                "trained Q2 artifact provenance drifted"
            )
    live = t1._live_adapter_loader()
    rows: list[dict[str, Any]] = []
    before_q2 = {lineage: q2_parameter_sha256(trainers[lineage].q2) for lineage in LINEAGES}
    attempt = {
        "schema": EVAL_ATTEMPT_SCHEMA,
        "freeze_sha256": frozen["payload"]["freeze_sha256"],
        "plan_sha256": frozen["payload"]["plan_sha256"],
        "formal_verdict_sha256": authorization["formal_verdict_sha256"],
        "source_sha256": source["source_sha256"],
        "sidecar_sha256": sidecar["sidecar_sha256"],
        "simulator_baseline_sha256": simulator_receipt["baseline_sha256"],
        "current_extended_manifest_sha256": simulator_receipt[
            "current_extended_manifest_sha256"
        ],
        "train_sha256_by_lineage": {
            lineage: train_receipts[lineage]["train_sha256"]
            for lineage in LINEAGES
        },
        "design_eval_seed_count": len(DESIGN_EVAL_SEEDS),
        "design_eval_started": True,
        "test_split_opened": False,
        "attempt": 1,
        "retry": False,
        "replacement": False,
    }
    attempt_path = root / "attempt.json"
    attempt_file_sha = _write_once_json(attempt_path, attempt)
    started = time.perf_counter()
    with live.authenticated_runtime(
        tle_root=tle_root,
        prereg_path=simulator_prereg,
        main_dir=main_dir,
        gate_dir=gate_dir,
        source_dir=q13_source_dir,
        v03_root=v03_root,
    ) as runtime:
        if runtime.checkpoint_sha256 != prepared["main_checkpoint_sha256"] or runtime.prereg_file_sha256 != prepared["simulator_prereg_file_sha256"]:
            raise BoundedLearnerRunnerError("DESIGN-EVAL runtime authority drifted")
        if (
            runtime.q13_gate_source_manifest_sha256
            != prepared["q13_gate_source_manifest_sha256"]
        ):
            raise BoundedLearnerRunnerError("DESIGN-EVAL Q1+Q3 authority drifted")
        expected_hybrid_hashes = {
            lineage: {
                cell[lineage]["hybrid_sha256"]
                for cell in prepared["lineage_bindings"].values()
            }
            for lineage in LINEAGES
        }
        if any(len(values) != 1 for values in expected_hybrid_hashes.values()):
            raise BoundedLearnerRunnerError(
                "DESIGN-EVAL PREPARE hybrid authority is inconsistent"
            )
        expected_hybrid_hashes_flat = {
            lineage: next(iter(values))
            for lineage, values in expected_hybrid_hashes.items()
        }
        if runtime.hybrid_hashes != expected_hybrid_hashes_flat:
            raise BoundedLearnerRunnerError(
                "DESIGN-EVAL selected hybrid digests drifted from PREPARE"
            )
        for lineage in LINEAGES:
            hybrid = runtime.hybrids[lineage]
            before_hybrid = _snapshot_q13_networks(hybrid)
            for seed in DESIGN_EVAL_SEEDS:
                pair: dict[str, dict[str, Any]] = {}
                for arm in ("FULL", "DROP_C2"):
                    pair[arm] = _episode(
                        live=live,
                        runtime=runtime,
                        hybrid=hybrid,
                        trainer=trainers[lineage],
                        prepare=prepared,
                        evaluation_seed=seed,
                        arm=arm,
                    )
                if pair["FULL"]["fading_field_sha256"] != pair["DROP_C2"]["fading_field_sha256"] or pair["FULL"]["initial_state_sha256"] != pair["DROP_C2"]["initial_state_sha256"] or pair["FULL"]["initial_c3_state_sha256"] != pair["DROP_C2"]["initial_c3_state_sha256"] or pair["FULL"]["initial_mask_sha256"] != pair["DROP_C2"]["initial_mask_sha256"]:
                    raise BoundedLearnerRunnerError("matched DESIGN-EVAL initial world drifted")
                full_actions = np.asarray(pair["FULL"]["actions"], dtype=np.int64)
                drop_actions = np.asarray(pair["DROP_C2"]["actions"], dtype=np.int64)
                flips = int(np.count_nonzero(full_actions != drop_actions))
                for arm in ("FULL", "DROP_C2"):
                    pair[arm]["action_flip_count"] = flips
                    pair[arm]["action_flip_rate"] = float(flips / 1000)
                    unsigned = dict(pair[arm])
                    unsigned.pop("row_sha256", None)
                    pair[arm]["row_sha256"] = canonical_sha256(unsigned)
                    rows.append(pair[arm])
            if not _same_q13_networks(hybrid, before_hybrid):
                raise BoundedLearnerRunnerError("frozen Q1/Q3 lineage changed in evaluation")
    for lineage in LINEAGES:
        if q2_parameter_sha256(trainers[lineage].q2) != before_q2[lineage]:
            raise BoundedLearnerRunnerError("Q2 changed during DESIGN-EVAL")
    rows_per_lineage = {
        lineage: int(train_receipts[lineage]["rows"]) for lineage in LINEAGES
    }
    optimizer_steps = {
        lineage: int(train_receipts[lineage]["updates"]) for lineage in LINEAGES
    }
    finite_all_steps = all(
        all(
            not isinstance(receipt[stage][metric], bool)
            and isinstance(receipt[stage][metric], (int, float))
            and math.isfinite(float(receipt[stage][metric]))
            for stage in ("loss_update_0", "loss_update_100")
            for metric in ("loss", "pair_mse", "gauge_mse")
        )
        for receipt in train_receipts.values()
    )
    g_l_receipt: dict[str, Any] = {
        "schema": G_L_RECEIPT_SCHEMA,
        "formal_verdict_authenticated": (
            authorization.get("formal_verdict") == FORMAL_LEARNER_VERDICT
        ),
        "verifier_code_authority_authenticated": (
            authorization.get("verifier_code_authority_sha256")
            == authority["prepare"]["code_authority"]["sha256"]
        ),
        "simulator_closure_authenticated": (
            simulator_receipt.get("old_files_byte_identical") is True
            and simulator_receipt.get("only_declared_extensions_present") is True
            and simulator_receipt == frozen["simulator_extension_receipt"]
        ),
        "single_global_freeze_root": Path(frozen["root"]).resolve()
        == FROZEN_FREEZE_ROOT,
        "source_rows": sum(rows_per_lineage.values()),
        "rows_per_lineage": rows_per_lineage,
        "optimizer_steps_by_lineage": optimizer_steps,
        "checkpoints": [0, 100],
        "update100_reloaded_by_lineage": {
            lineage: trainers[lineage].update_count == 100 for lineage in LINEAGES
        },
        "finite_all_steps": finite_all_steps,
        "q1_q3_byte_identical": True,
        "q1_q3_receive_no_gradient": all(
            receipt.get("q1_q3_loaded") is False
            and receipt.get("q2_only_optimizer") is True
            for receipt in train_receipts.values()
        ),
        "q2_unchanged_during_design_eval": True,
        "design_eval_rows": len(rows),
        "drop_c2_prepare_cells": int(sidecar["counts"]["anchors"])
        * len(LINEAGES),
        "resident_legacy_q2_evaluated_or_summed": any(
            row.get("resident_legacy_q2_consulted") is not False for row in rows
        ),
        "resident_legacy_q2_read_or_copied": False,
        "test_split_opened": any(
            row.get("test_split_opened") is not False for row in rows
        ),
        "outcome_selection": False,
        "retry": any(receipt.get("retry") is not False for receipt in train_receipts.values()),
        "replacement": any(
            receipt.get("replacement") is not False
            for receipt in train_receipts.values()
        ),
        "extra_arm": {str(row["arm"]) for row in rows}
        != {"FULL", "DROP_C2"},
    }
    g_l_receipt["passed"] = (
        g_l_receipt["formal_verdict_authenticated"] is True
        and g_l_receipt["verifier_code_authority_authenticated"] is True
        and g_l_receipt["simulator_closure_authenticated"] is True
        and g_l_receipt["single_global_freeze_root"] is True
        and g_l_receipt["source_rows"] == 1008
        and g_l_receipt["rows_per_lineage"]
        == {lineage: 336 for lineage in LINEAGES}
        and g_l_receipt["optimizer_steps_by_lineage"]
        == {lineage: 100 for lineage in LINEAGES}
        and g_l_receipt["update100_reloaded_by_lineage"]
        == {lineage: True for lineage in LINEAGES}
        and g_l_receipt["finite_all_steps"] is True
        and g_l_receipt["q1_q3_byte_identical"] is True
        and g_l_receipt["q1_q3_receive_no_gradient"] is True
        and g_l_receipt["q2_unchanged_during_design_eval"] is True
        and g_l_receipt["design_eval_rows"] == 60
        and g_l_receipt["drop_c2_prepare_cells"] == 36
        and g_l_receipt["resident_legacy_q2_evaluated_or_summed"] is False
        and g_l_receipt["resident_legacy_q2_read_or_copied"] is False
        and g_l_receipt["test_split_opened"] is False
        and g_l_receipt["outcome_selection"] is False
        and g_l_receipt["retry"] is False
        and g_l_receipt["replacement"] is False
        and g_l_receipt["extra_arm"] is False
    )
    gates = adjudicate_design_eval(rows, g_l_receipt=g_l_receipt)
    disposition = (
        "AUTHORIZE_FRESH_C2_K1_CONFIRMATORY_ABLATION_ONLY"
        if gates["gates"]["launchable"]
        else "C2_K1_LEARNER_NOT_CONFIRMED"
    )
    body = {
        "schema": EVAL_SCHEMA,
        "status": "DESIGN_EVAL_COMPLETE",
        "disposition": disposition,
        "freeze_sha256": frozen["payload"]["freeze_sha256"],
        "formal_verdict_sha256": next(iter(train_receipts.values()))["formal_verdict_sha256"],
        "source_sha256": next(iter(train_receipts.values()))["source_sha256"],
        "sidecar_sha256": next(iter(train_receipts.values()))["sidecar_sha256"],
        "simulator_baseline_sha256": simulator_receipt["baseline_sha256"],
        "current_extended_manifest_sha256": simulator_receipt[
            "current_extended_manifest_sha256"
        ],
        "train_sha256_by_lineage": {lineage: train_receipts[lineage]["train_sha256"] for lineage in LINEAGES},
        "attempt_path": str(attempt_path.resolve()),
        "attempt_file_sha256": attempt_file_sha,
        "rows": rows,
        "adjudication": gates,
        "g_l_receipt": g_l_receipt,
        "elapsed_s": float(time.perf_counter() - started),
        "test_split_opened": False,
        "episode_training": False,
        "retry": False,
        "replacement": False,
        "no_9000ep": True,
    }
    payload = body | {"evaluation_sha256": canonical_sha256(body)}
    result_path = root / "evaluation-result.json"
    result_file_sha = _write_once_json(result_path, payload)
    _write_once_json(
        root / "evaluation-seal.json",
        {
            "schema": EVAL_SEAL_SCHEMA,
            "evaluation_sha256": payload["evaluation_sha256"],
            "evaluation_file_sha256": result_file_sha,
            "disposition": disposition,
            "formal_verdict_sha256": payload["formal_verdict_sha256"],
            "source_sha256": payload["source_sha256"],
            "rows": 60,
            "test_split_opened": False,
            "retry": False,
        },
    )
    return payload


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    freeze = sub.add_parser("freeze-update0")
    freeze.add_argument("--learner-prereg", type=Path, required=True)
    freeze.add_argument("--prepare", type=Path, required=True)
    freeze.add_argument("--simulator-baseline", type=Path, required=True)
    freeze.add_argument(
        "--simulator-baseline-seal", type=Path, required=True
    )
    freeze.add_argument("--output-dir", type=Path, required=True)
    train = sub.add_parser("train-lineage")
    train.add_argument("--lineage", choices=LINEAGES, required=True)
    train.add_argument("--freeze-dir", type=Path, required=True)
    train.add_argument("--learner-prereg", type=Path, required=True)
    train.add_argument("--formal-verdict", type=Path, required=True)
    train.add_argument("--formal-verdict-seal", type=Path, required=True)
    train.add_argument("--source", type=Path, required=True)
    train.add_argument("--source-seal", type=Path, required=True)
    train.add_argument("--prepare", type=Path, required=True)
    train.add_argument("--prepare-seal", type=Path, required=True)
    train.add_argument("--t1-prereg", type=Path, required=True)
    train.add_argument("--sidecar", type=Path, required=True)
    train.add_argument("--sidecar-seal", type=Path, required=True)
    train.add_argument("--live-verification", type=Path, required=True)
    train.add_argument("--live-verification-seal", type=Path, required=True)
    train.add_argument("--simulator-baseline", type=Path, required=True)
    train.add_argument("--simulator-baseline-seal", type=Path, required=True)
    train.add_argument("--output-dir", type=Path, required=True)
    evaluate_parser = sub.add_parser("evaluate")
    evaluate_parser.add_argument("--freeze-dir", type=Path, required=True)
    evaluate_parser.add_argument("--learner-prereg", type=Path, required=True)
    for lineage in LINEAGES:
        evaluate_parser.add_argument(f"--train-{lineage}", type=Path, required=True)
    evaluate_parser.add_argument("--formal-verdict", type=Path, required=True)
    evaluate_parser.add_argument("--formal-verdict-seal", type=Path, required=True)
    evaluate_parser.add_argument("--source", type=Path, required=True)
    evaluate_parser.add_argument("--source-seal", type=Path, required=True)
    evaluate_parser.add_argument("--prepare", type=Path, required=True)
    evaluate_parser.add_argument("--prepare-seal", type=Path, required=True)
    evaluate_parser.add_argument("--t1-prereg", type=Path, required=True)
    evaluate_parser.add_argument("--sidecar", type=Path, required=True)
    evaluate_parser.add_argument("--sidecar-seal", type=Path, required=True)
    evaluate_parser.add_argument("--live-verification", type=Path, required=True)
    evaluate_parser.add_argument("--live-verification-seal", type=Path, required=True)
    evaluate_parser.add_argument("--tle-root", type=Path, required=True)
    evaluate_parser.add_argument("--simulator-prereg", type=Path, required=True)
    evaluate_parser.add_argument("--main-dir", type=Path, required=True)
    evaluate_parser.add_argument("--gate-dir", type=Path, required=True)
    evaluate_parser.add_argument("--q13-source-dir", type=Path, required=True)
    evaluate_parser.add_argument("--v03-root", type=Path, required=True)
    evaluate_parser.add_argument("--simulator-baseline", type=Path, required=True)
    evaluate_parser.add_argument(
        "--simulator-baseline-seal", type=Path, required=True
    )
    evaluate_parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "freeze-update0":
            payload = freeze_update0(
                learner_prereg=args.learner_prereg,
                prepare_path=args.prepare,
                simulator_baseline=args.simulator_baseline,
                simulator_baseline_seal=args.simulator_baseline_seal,
                output_dir=args.output_dir,
            )
            print(json.dumps({"status": payload["status"], "freeze_sha256": payload["freeze_sha256"]}, sort_keys=True))
            return 0
        if args.command == "train-lineage":
            payload = train_lineage(
                lineage=args.lineage,
                freeze_dir=args.freeze_dir,
                learner_prereg=args.learner_prereg,
                formal_verdict=args.formal_verdict,
                formal_verdict_seal=args.formal_verdict_seal,
                source_path=args.source,
                source_seal_path=args.source_seal,
                prepare_path=args.prepare,
                prepare_seal_path=args.prepare_seal,
                t1_prereg=args.t1_prereg,
                sidecar_path=args.sidecar,
                sidecar_seal_path=args.sidecar_seal,
                live_verification_path=args.live_verification,
                live_verification_seal_path=args.live_verification_seal,
                simulator_baseline=args.simulator_baseline,
                simulator_baseline_seal=args.simulator_baseline_seal,
                output_dir=args.output_dir,
            )
            print(json.dumps({"status": payload["status"], "train_sha256": payload["train_sha256"]}, sort_keys=True))
            return 0
        train_dirs = {
            lineage: getattr(args, f"train_{lineage.replace('-', '_')}")
            for lineage in LINEAGES
        }
        payload = evaluate(
            freeze_dir=args.freeze_dir,
            learner_prereg=args.learner_prereg,
            train_dirs=train_dirs,
            formal_verdict=args.formal_verdict,
            formal_verdict_seal=args.formal_verdict_seal,
            source_path=args.source,
            source_seal_path=args.source_seal,
            prepare_path=args.prepare,
            prepare_seal_path=args.prepare_seal,
            t1_prereg=args.t1_prereg,
            sidecar_path=args.sidecar,
            sidecar_seal_path=args.sidecar_seal,
            live_verification_path=args.live_verification,
            live_verification_seal_path=args.live_verification_seal,
            tle_root=args.tle_root,
            simulator_prereg=args.simulator_prereg,
            main_dir=args.main_dir,
            gate_dir=args.gate_dir,
            q13_source_dir=args.q13_source_dir,
            v03_root=args.v03_root,
            simulator_baseline=args.simulator_baseline,
            simulator_baseline_seal=args.simulator_baseline_seal,
            output_dir=args.output_dir,
        )
        print(json.dumps({"status": payload["status"], "disposition": payload["disposition"], "evaluation_sha256": payload["evaluation_sha256"]}, sort_keys=True))
        return 0
    except Exception as error:
        print(
            json.dumps(
                {
                    "status": "C2_K1_LEARNER_INVALID_NO_RETRY",
                    "error": str(error),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(_main())
