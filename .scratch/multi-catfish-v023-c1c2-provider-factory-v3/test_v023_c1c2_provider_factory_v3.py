"""Producer-derived contract tests for the C1/C2 successor provider factory."""

from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import replace
from functools import lru_cache
import hashlib
import importlib
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))

import v023_c1c2_provider_factory_v3 as FACTORY

from mcrl.env.action_contract import NUM_ACTIONS
from mcrl.runtime.ee_axis_c1_selector import (
    C1_CLUSTER_NEUTRAL_SOURCE_RULE,
    C1_INFORMED_SOURCE_RULE,
)
from mcrl.runtime.ee_axis_c2_neutral_source import C2_INFORMED_SOURCE_RULE
from mcrl.runtime.ee_axis_opening_dataset import (
    EEAxisOpeningDataset,
    EEAxisOpeningDatasetRow,
    write_opening_dataset,
)
from mcrl.runtime.ee_axis_opening_runner import C3_NEUTRAL_SOURCE_RULE
from mcrl.runtime.ee_axis_opening_source import (
    EEAxisOpeningRawPair,
    _canonical_sha256 as opening_sha256,
    _raw_payload as opening_raw_payload,
)
from mcrl.runtime.ee_axis_state import (
    EE_AXIS_STATE_DIM,
    EE_AXIS_STATE_SCHEMA,
    EE_AXIS_STATE_SCHEMA_SHA256,
)
from mcrl.runtime.ee_axis_temporal_pairs import C2_NEUTRAL_SOURCE_RULE


GENERATOR_PATH = (
    REPO
    / ".scratch/multi-catfish-v023-c1c2-target-generation/"
    "generate_v023_c1c2_targets.py"
)
LAUNCH_DIR = REPO / ".scratch/multi-catfish-v023-c1c2-target-generation-launch"
REAL_EXCERPT = LAUNCH_DIR / "fixtures-real-shard/c2-neutral-world-2026121708.excerpt.json"
FROZEN_LEARNER_EXECUTING_ROOTS = {
    ".scratch/multi-catfish-v023-two-route-source-training-runner/ee_axis_two_route_model.py": "ee_axis_two_route_model",
    ".scratch/multi-catfish-v023-two-route-source-training-runner/v023_two_route_learner_orchestrator.py": "v023_two_route_learner_orchestrator",
    ".scratch/multi-catfish-v023-two-route-source-training-runner/v023_two_route_source_training_runner.py": "v023_two_route_source_training_runner",
    ".scratch/multi-catfish-v023-heterogeneous-trainer/v023_heterogeneous_trainer.py": "v023_heterogeneous_trainer",
}


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def _canonical(payload: object) -> bytes:
    return (
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
        + b"\n"
    )


def _independent_module_path(module_name: str) -> Path | None:
    if module_name == "mcrl" or module_name.startswith("mcrl."):
        base = REPO / "src" / Path(*module_name.split("."))
        candidates = (base.with_suffix(".py"), base / "__init__.py")
    else:
        candidates = tuple(
            REPO / relative
            for relative, declared_name in FROZEN_LEARNER_EXECUTING_ROOTS.items()
            if declared_name == module_name
        )
    return next(
        (
            candidate.resolve(strict=True)
            for candidate in candidates
            if candidate.is_file() and not candidate.is_symlink()
        ),
        None,
    )


def _independent_module_name(path: Path) -> str:
    relative = path.relative_to(REPO)
    if relative.parts[:2] != ("src", "mcrl"):
        return FROZEN_LEARNER_EXECUTING_ROOTS[relative.as_posix()]
    parts = list(relative.with_suffix("").parts[1:])
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _independent_absolute_import(
    *, current_module: str, current_path: Path, imported: str | None, level: int
) -> str:
    if level == 0:
        return imported or ""
    package = (
        current_module
        if current_path.name == "__init__.py"
        else current_module.rpartition(".")[0]
    )
    parts = package.split(".") if package else []
    if level > len(parts) + 1:
        return ""
    prefix = parts[: len(parts) - level + 1]
    if imported:
        prefix.extend(imported.split("."))
    return ".".join(prefix)


@lru_cache(maxsize=1)
def _independent_expected_learner_runtime_modules() -> dict[str, str]:
    """Static import scan rooted in the test's frozen producer donor list."""

    pending = [
        (REPO / relative).resolve(strict=True)
        for relative in FROZEN_LEARNER_EXECUTING_ROOTS
    ]
    discovered: dict[Path, str] = {}
    src = (REPO / "src").resolve(strict=True)
    while pending:
        path = pending.pop()
        if path in discovered:
            continue
        module_name = _independent_module_name(path)
        discovered[path] = module_name
        if path.is_relative_to(src / "mcrl"):
            parent = path.parent
            while parent != src:
                initializer = parent / "__init__.py"
                if initializer.is_file() and not initializer.is_symlink():
                    pending.append(initializer.resolve(strict=True))
                parent = parent.parent
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                base = _independent_absolute_import(
                    current_module=module_name,
                    current_path=path,
                    imported=node.module,
                    level=node.level,
                )
                if base:
                    imported_names.add(base)
                if node.module is None and base:
                    imported_names.update(
                        f"{base}.{alias.name}" for alias in node.names
                    )
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "importlib"
                and node.func.attr == "import_module"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                imported_names.add(node.args[0].value)
        for imported_name in imported_names:
            imported_path = _independent_module_path(imported_name)
            if imported_path is not None and imported_path not in discovered:
                pending.append(imported_path)
    return {
        path.relative_to(REPO).as_posix(): module
        for path, module in sorted(discovered.items())
    }


def _load_path_module(path: Path):
    natural_name = path.stem
    directory = str(path.parent)
    sys.path.insert(0, directory)
    try:
        module = importlib.import_module(natural_name)
    finally:
        sys.path.remove(directory)
    assert Path(module.__file__).resolve() == path.resolve()
    return module


@lru_cache(maxsize=1)
def _producer_modules():
    controller = _load_path_module(
        LAUNCH_DIR / "run_v023_c1c2_targets_server.py",
    )
    generator = controller._load_generator()
    assert Path(generator.__file__).resolve() == GENERATOR_PATH.resolve()
    sealer = _load_path_module(
        LAUNCH_DIR / "seal_v023_c1c2_target_output.py",
    )
    return generator, controller, sealer


@lru_cache(maxsize=1)
def _producer_authority() -> dict[str, object]:
    """Read fixture constants from the frozen producer authority, independently."""

    manifest_path = (
        REPO / ".scratch/multi-catfish-v023-r6-fit-binding-fix/PREFLIGHT-MANIFEST.json"
    )
    manifest_sha = _sha_file(manifest_path)
    assert manifest_path.with_suffix(".sha256").read_text(encoding="ascii") == (
        f"{manifest_sha}  {manifest_path.name}\n"
    )
    manifest = json.loads(manifest_path.read_text(encoding="ascii"))
    prereg_binding = [
        row for row in manifest["bindings"] if row["role"] == "preregistration"
    ]
    assert len(prereg_binding) == 1
    prereg_path = REPO / prereg_binding[0]["path"]
    assert _sha_file(prereg_path) == prereg_binding[0]["sha256"]
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    ephemeris = prereg["sections"]["ephemeris"]
    configuration = manifest["configuration"]
    return {
        "worlds": tuple(configuration["worlds"]),
        "lambda_hex": configuration["lambda_hex"],
        "kappa_hex": configuration["kappa_hex"],
        "interval_hex": float(ephemeris["config"]["time_step_s"]).hex(),
        "prereg_sha256": prereg_binding[0]["sha256"],
        "tle_file_set_sha256": ephemeris["file_set_sha256"],
    }


def _c1_dataset(*, mode: str, world: int) -> EEAxisOpeningDataset:
    source_manifest = _digest("successor-target-source-manifest")
    checkpoint = _digest("successor-target-checkpoint")
    common_field = _digest(f"successor-common-field-{mode}-{world}")
    state = np.zeros(EE_AXIS_STATE_DIM, dtype=np.float32)
    state[0] = np.float32(world % 1000)
    mask = np.zeros(NUM_ACTIONS, dtype=np.bool_)
    mask[[0, 1]] = True
    reference_joint = np.asarray([0, 1], dtype=np.int64)
    candidate_joint = np.asarray([1, 1], dtype=np.int64)
    raw_placeholder = EEAxisOpeningRawPair(
        source_policy_version=1,
        anchor_sha256=_digest(f"c1-anchor-{mode}-{world}"),
        source_manifest_sha256=source_manifest,
        checkpoint_sha256=checkpoint,
        common_random_field_sha256=common_field,
        state_schema=EE_AXIS_STATE_SCHEMA,
        state_schema_sha256=EE_AXIS_STATE_SCHEMA_SHA256,
        state_observation_sha256=_digest(f"c1-observation-{mode}-{world}"),
        focal_user=0,
        state=state,
        action_mask=mask,
        reference_action=0,
        candidate_action=1,
        reference_joint_actions=reference_joint,
        candidate_joint_actions=candidate_joint,
        reference_physical_keys=((500, 1), (501, 1)),
        candidate_physical_keys=((501, 1), (501, 1)),
        reference_rates_bps=np.asarray([100.0, 50.0], dtype=np.float64),
        candidate_rates_bps=np.asarray([110.0, 50.0], dtype=np.float64),
        reference_system_power_w=10.0,
        candidate_system_power_w=11.0,
        lambda_bits_per_j=float.fromhex(str(_producer_authority()["lambda_hex"])),
        interval_s=float.fromhex(str(_producer_authority()["interval_hex"])),
        comparison_sha256="0" * 64,
    )
    raw = replace(
        raw_placeholder,
        comparison_sha256=opening_sha256(opening_raw_payload(raw_placeholder)),
    )
    from mcrl.runtime.ee_axis_opening_pairs import build_opening_pair

    c1_rule = (
        C1_INFORMED_SOURCE_RULE
        if mode == "informed"
        else C1_CLUSTER_NEUTRAL_SOURCE_RULE
    )
    kwargs = {
        "source_policy_version": raw.source_policy_version,
        "anchor_sha256": raw.anchor_sha256,
        "source_manifest_sha256": source_manifest,
        "checkpoint_sha256": checkpoint,
        "common_random_field_sha256": common_field,
        "focal_user": 0,
        "state": state,
        "action_mask": mask,
        "reference_action": 0,
        "candidate_action": 1,
        "reference_joint_actions": reference_joint,
        "candidate_joint_actions": candidate_joint,
        "reference_rates_bps": raw.reference_rates_bps,
        "candidate_rates_bps": raw.candidate_rates_bps,
        "reference_system_power_w": raw.reference_system_power_w,
        "candidate_system_power_w": raw.candidate_system_power_w,
        "lambda_bits_per_j": raw.lambda_bits_per_j,
        "interval_s": raw.interval_s,
    }
    c1 = build_opening_pair(source_route="C1", source_rule=c1_rule, **kwargs)
    c3 = build_opening_pair(
        source_route="C3", source_rule=C3_NEUTRAL_SOURCE_RULE, **kwargs
    )
    row = EEAxisOpeningDatasetRow(
        raw_pair=raw,
        admitted_route="C1",
        c1_source_rule=c1.source_rule,
        c3_source_rule=c3.source_rule,
        c1_comparison_sha256=c1.comparison_sha256,
        c3_comparison_sha256=c3.comparison_sha256,
        zeta1_focal_surplus_bits=c1.zeta1_focal_surplus_bits,
        zeta3_nonfocal_externality_bits=c3.zeta3_nonfocal_externality_bits,
        identity_residual_bits=c1.identity_residual_bits,
    )
    return EEAxisOpeningDataset(
        source_policy_version=1,
        source_manifest_sha256=source_manifest,
        checkpoint_sha256=checkpoint,
        common_random_field_sha256=common_field,
        state_schema=EE_AXIS_STATE_SCHEMA,
        state_schema_sha256=EE_AXIS_STATE_SCHEMA_SHA256,
        rows=(row,),
    )


def _c1_binding(
    dataset: EEAxisOpeningDataset, *, mode: str, world: int
) -> dict[str, object]:
    row = dataset.rows[0]
    raw = row.raw_pair
    candidate = raw.candidate_physical_keys[raw.focal_user]
    assert candidate is not None
    return {
        "mode": mode,
        "source_anchor_sha256": raw.anchor_sha256,
        "source_record_sha256": _digest(f"source-record-{mode}-{world}"),
        "world": world,
        "step_index": 0,
        "focal_user": raw.focal_user,
        "reference_action": raw.reference_action,
        "candidate_action": raw.candidate_action,
        "candidate_physical_key": list(candidate),
        "source_rule": row.c1_source_rule,
        "source_seed": world,
        "common_random_field_sha256": raw.common_random_field_sha256,
        "comparison_sha256": raw.comparison_sha256,
    }


def _c2_dataset_and_binding(
    *, mode: str, world: int
) -> tuple[dict[str, object], dict[str, object]]:
    excerpt = json.loads(REAL_EXCERPT.read_text(encoding="ascii"))
    row = deepcopy(excerpt["rows"][0])
    row["world"] = world
    row["mode"] = mode
    row["source_rule"] = (
        C2_INFORMED_SOURCE_RULE if mode == "informed" else C2_NEUTRAL_SOURCE_RULE
    )
    binding = {
        "mode": mode,
        "source_anchor_sha256": row["source_anchor_sha256"],
        "world": world,
        "step_index": row["step_index"],
        "focal_user": row["focal_user"],
        "reference_action": row["reference_action"],
        "candidate_action": row["candidate_action"],
        "candidate_physical_key": row["candidate_physical_key"],
        "source_rule": row["source_rule"],
        "schedule_sha256": row["schedule_sha256"],
        "ops3_anchor_sha256": row["provenance"]["ops3_anchor_sha256"],
        "ops3_projection_sha256": row["provenance"]["ops3_projection_sha256"],
        "target_delta": row["target_delta"],
        "target_unit": row["target_unit"],
    }
    dataset = {
        "schema": excerpt["schema"],
        "source_manifest_sha256": _digest("successor-target-source-manifest"),
        "checkpoint_sha256": _digest("successor-target-checkpoint"),
        "lambda_bits_per_j": _producer_authority()["lambda_hex"],
        "kappa_bits": _producer_authority()["kappa_hex"],
        "target_unit": excerpt["target_unit"],
        "rows": [row],
    }
    return dataset, binding


def _schedule_row(binding: Mapping[str, object], *, route: str) -> dict[str, object]:
    excluded = (
        {"mode", "common_random_field_sha256", "comparison_sha256"}
        if route == "C1"
        else {
            "mode",
            "schedule_sha256",
            "ops3_anchor_sha256",
            "ops3_projection_sha256",
            "target_delta",
            "target_unit",
        }
    )
    return {key: value for key, value in binding.items() if key not in excluded}


def _write_artifact(root: Path) -> Path:
    generator, controller, sealer = _producer_modules()
    shards: dict[str, Path] = {}
    expected_schedule: dict[str, dict[str, object]] = {}
    sealed = SimpleNamespace(
        capture_path=root.parent / "capture.json",
        capture_sha256=_digest("capture"),
        materialization_dir=root.parent / "materialization",
        materialization_manifest_sha256=_digest("materialization-manifest"),
        pool_sha256=_digest("pool"),
        source_manifest_sha256=_digest("successor-target-source-manifest"),
        checkpoint_sha256=_digest("successor-target-checkpoint"),
    )
    ctx = SimpleNamespace(
        modules=SimpleNamespace(
            opening_dataset=SimpleNamespace(
                write_opening_dataset=write_opening_dataset
            )
        ),
        source_family="producer-derived-successor-fixture",
        lambda_bits_per_j=float.fromhex(str(_producer_authority()["lambda_hex"])),
        kappa_bits=float.fromhex(str(_producer_authority()["kappa_hex"])),
        interval_s=float.fromhex(str(_producer_authority()["interval_hex"])),
    )
    for mode in ("informed", "neutral"):
        for world in _producer_authority()["worlds"]:
            c1_dataset = _c1_dataset(mode=mode, world=world)
            c1_binding = _c1_binding(c1_dataset, mode=mode, world=world)
            c2_dataset, c2_binding = _c2_dataset_and_binding(
                mode=mode, world=world
            )
            key = f"{mode}:{world}"
            shard_schedule = {
                key: {
                    "mode": mode,
                    "world": world,
                    "C1": [_schedule_row(c1_binding, route="C1")],
                    "C2": [_schedule_row(c2_binding, route="C2")],
                }
            }
            shard = root.parent / f"{root.name}-{mode}-{world}-shard"
            generator._write_outputs(
                shard,
                sealed=sealed,
                ctx=ctx,
                schedule=shard_schedule,
                c1_datasets={(mode, world): c1_dataset},
                c2_datasets={(mode, world): c2_dataset},
                c1_bindings=(c1_binding,),
                c2_bindings=(c2_binding,),
            )
            shards[key] = shard
            expected_schedule.update(shard_schedule)
    controller._merge(shards, root, expected_schedule=expected_schedule)
    sealer.seal(root)
    return root


def _reseal(root: Path) -> None:
    files = {
        path.name: path.read_bytes()
        for path in root.iterdir()
        if path.name not in {"MANIFEST.sha256", "COMPLETE"}
    }
    manifest = "".join(
        f"{hashlib.sha256(files[name]).hexdigest()}  {name}\n"
        for name in sorted(files)
    ).encode("ascii")
    (root / "MANIFEST.sha256").write_bytes(manifest)
    (root / "COMPLETE").write_bytes(
        f"{hashlib.sha256(manifest).hexdigest()}  MANIFEST.sha256\n".encode(
            "ascii"
        )
    )


def _write_learner_manifest(path: Path) -> Path:
    bindings = [
        {
            "path": relative,
            "module": module,
            "sha256": _sha_file(REPO / relative),
        }
        for relative, module in sorted(
            _independent_expected_learner_runtime_modules().items()
        )
    ]
    path.write_bytes(
        _canonical(
            {
                "schema": FACTORY.LEARNER_MANIFEST_SCHEMA,
                "status": FACTORY.LEARNER_MANIFEST_STATUS,
                "claim_ceiling": FACTORY.CLAIM_CEILING,
                "bindings": bindings,
            }
        )
    )
    return path


@pytest.fixture(scope="module")
def sealed_inputs(tmp_path_factory):
    base = tmp_path_factory.mktemp("provider-fixture")
    target = _write_artifact(base / "targets")
    learner_manifest = _write_learner_manifest(base / "learner-manifest.json")
    return target, learner_manifest


def _config_payload(target: Path, learner_manifest: Path) -> dict[str, object]:
    return {
        "schema": FACTORY.CONFIG_SCHEMA,
        "contract_sha256": _sha_file(FACTORY.CONTRACT_PATH),
        "target_root": str(target),
        "target_manifest_sha256": _sha_file(target / "MANIFEST.sha256"),
        "target_receipt_sha256": _sha_file(target / "receipt.json"),
        "learner_manifest_sha256": _sha_file(learner_manifest),
        "model_config_sha256": FACTORY.MODEL_CONFIG_SHA256,
        "train_seed": FACTORY.TRAIN_SEED,
        "epoch_budget": FACTORY.EPOCH_BUDGET,
    }


def _provider(monkeypatch, target: Path, learner_manifest: Path):
    monkeypatch.setenv(
        FACTORY.LEARNER_MANIFEST_PATH_ENV, str(learner_manifest)
    )
    config = FACTORY.C1C2ProviderConfig.from_payload(
        _config_payload(target, learner_manifest)
    )
    return FACTORY.build_provider(config)


def test_frozen_model_seed_and_complete_successor_closure_are_required():
    assert FACTORY.TRAIN_SEED == 2927175120652069826
    assert FACTORY.MODEL_CONFIG_SHA256 == (
        "9eafcd184bd0ec015498832be61b5c95a71373e98f63ab804c9654775a8b1d5d"
    )
    producer = _producer_authority()
    assert FACTORY.EXPECTED_WORLDS == producer["worlds"]
    assert FACTORY.EXPECTED_LAMBDA_HEX == producer["lambda_hex"]
    assert FACTORY.EXPECTED_KAPPA_HEX == producer["kappa_hex"]
    assert FACTORY.EXPECTED_INTERVAL_HEX == producer["interval_hex"]
    required = _independent_expected_learner_runtime_modules()
    assert required == dict(FACTORY.derive_learner_runtime_modules())
    assert required[
        ".scratch/multi-catfish-v023-two-route-source-training-runner/"
        "ee_axis_two_route_model.py"
    ] == "ee_axis_two_route_model"
    assert required[
        ".scratch/multi-catfish-v023-two-route-source-training-runner/"
        "v023_two_route_learner_orchestrator.py"
    ] == "v023_two_route_learner_orchestrator"
    assert required[
        ".scratch/multi-catfish-v023-two-route-source-training-runner/"
        "v023_two_route_source_training_runner.py"
    ] == "v023_two_route_source_training_runner"
    assert required[
        ".scratch/multi-catfish-v023-heterogeneous-trainer/"
        "v023_heterogeneous_trainer.py"
    ] == "v023_heterogeneous_trainer"
    assert required["src/mcrl/algorithms/ee_axis_lcsrs_three_route.py"] == (
        "mcrl.algorithms.ee_axis_lcsrs_three_route"
    )
    assert required["src/mcrl/algorithms/ee_axis_lcsrs_c3_head.py"] == (
        "mcrl.algorithms.ee_axis_lcsrs_c3_head"
    )
    assert required["src/mcrl/runtime/ee_axis_lcsrs_c3_state.py"] == (
        "mcrl.runtime.ee_axis_lcsrs_c3_state"
    )


def test_omitted_transitive_learner_dependency_is_detected(tmp_path: Path):
    expected = _independent_expected_learner_runtime_modules()
    omitted = "src/mcrl/runtime/bessel.py"
    assert omitted in expected
    assert omitted not in FROZEN_LEARNER_EXECUTING_ROOTS
    bindings = [
        {
            "path": relative,
            "module": module,
            "sha256": _sha_file(REPO / relative),
        }
        for relative, module in sorted(expected.items())
        if relative != omitted
    ]
    manifest = tmp_path / "omitted-transitive-learner-manifest.json"
    manifest.write_bytes(
        _canonical(
            {
                "schema": FACTORY.LEARNER_MANIFEST_SCHEMA,
                "status": FACTORY.LEARNER_MANIFEST_STATUS,
                "claim_ceiling": FACTORY.CLAIM_CEILING,
                "bindings": bindings,
            }
        )
    )
    with pytest.raises(
        FACTORY.V023C1C2ProviderFactoryError, match="derived import graph"
    ):
        FACTORY._authenticate_learner_manifest(
            manifest, expected_sha256=_sha_file(manifest)
        )


def _call(provider, cursor: int, route: str):
    neutral = provider.next_batch(
        route=route, source="neutral", update_cursor=cursor
    )
    informed = provider.next_batch(
        route=route, source="informed", update_cursor=cursor
    )
    return neutral, informed


def test_positive_load_identity_and_exact_resume(sealed_inputs, monkeypatch):
    target, learner_manifest = sealed_inputs
    first = _provider(monkeypatch, target, learner_manifest)
    second = _provider(monkeypatch, target, learner_manifest)
    assert isinstance(first, FACTORY.DeterministicRouteBatchProvider)
    assert first.provider_identity == second.provider_identity
    assert first.planned_epoch_budget == 100
    identity = first.provider_identity_payload
    assert set(identity) == set(FACTORY.PROVIDER_IDENTITY_FIELDS)
    assert len(identity) == 22
    assert identity["routes"] == ["C1", "C2"]
    assert identity["train_seed"] == FACTORY.TRAIN_SEED
    assert len(identity["learner_runtime"]) == len(
        _independent_expected_learner_runtime_modules()
    )
    assert all(
        record["loaded_from"].startswith(str(REPO))
        for record in identity["learner_runtime"]
    )

    _call(first, 0, "C1")
    partial = first.next_batch(route="C2", source="neutral", update_cursor=1)
    saved = first.sampler_state()
    continuation = first.next_batch(
        route="C2", source="informed", update_cursor=1
    )

    second.load_sampler_state(saved)
    restored = second.next_batch(
        route="C2", source="informed", update_cursor=1
    )
    assert restored.file_id == continuation.file_id
    assert np.array_equal(restored.batch.states, continuation.batch.states)
    assert np.array_equal(
        restored.batch.normalized_target_deltas,
        continuation.batch.normalized_target_deltas,
    )
    assert partial.source == "neutral"
    assert len(second.sampler_state()["consumed_file_order"]) == 4


def test_third_route_request_is_rejected(sealed_inputs, monkeypatch):
    target, learner_manifest = sealed_inputs
    provider = _provider(monkeypatch, target, learner_manifest)
    with pytest.raises(FACTORY.V023C1C2ProviderFactoryError, match="C1/C2"):
        provider.next_batch(route="C3", source="neutral", update_cursor=0)


@pytest.mark.parametrize("field", ("r7_root", "extra"))
def test_closed_config_rejects_r7_and_extra_fields(sealed_inputs, field):
    target, learner_manifest = sealed_inputs
    payload = _config_payload(target, learner_manifest)
    payload[field] = "/tmp/authority" if field == "r7_root" else True
    with pytest.raises(FACTORY.V023C1C2ProviderFactoryError):
        FACTORY.C1C2ProviderConfig.from_payload(payload)


def test_fabricated_contract_digest_cannot_authenticate_provider(
    sealed_inputs, monkeypatch
):
    target, learner_manifest = sealed_inputs
    monkeypatch.setenv(FACTORY.LEARNER_MANIFEST_PATH_ENV, str(learner_manifest))
    payload = _config_payload(target, learner_manifest)
    payload["contract_sha256"] = _digest("fabricated-successor-contract")
    config = FACTORY.C1C2ProviderConfig.from_payload(payload)
    with pytest.raises(FACTORY.V023C1C2ProviderFactoryError, match="contract on disk"):
        FACTORY.build_provider(config)


def test_missing_neutral_mode_fails_closed(sealed_inputs, monkeypatch, tmp_path):
    source, learner_manifest = sealed_inputs
    target = tmp_path / "targets"
    shutil.copytree(source, target)
    receipt_path = target / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="ascii"))
    for route in ("C1", "C2"):
        receipt["datasets"][route] = {
            key: value
            for key, value in receipt["datasets"][route].items()
            if key.startswith("informed:")
        }
        receipt["row_bindings"][route] = [
            item
            for item in receipt["row_bindings"][route]
            if item["mode"] == "informed"
        ]
    for path in target.glob("*-neutral-world-*.json"):
        path.unlink()
    receipt_path.write_bytes(_canonical(receipt))
    _reseal(target)
    with pytest.raises(FACTORY.V023C1C2ProviderFactoryError):
        _provider(monkeypatch, target, learner_manifest)


def test_one_flipped_shard_byte_fails_closed(sealed_inputs, monkeypatch, tmp_path):
    source, learner_manifest = sealed_inputs
    target = tmp_path / "targets"
    shutil.copytree(source, target)
    shard = target / f"c1-informed-world-{_producer_authority()['worlds'][0]}.json"
    raw = bytearray(shard.read_bytes())
    raw[len(raw) // 2] ^= 1
    shard.write_bytes(bytes(raw))
    with pytest.raises(FACTORY.V023C1C2ProviderFactoryError, match="digest drifted"):
        _provider(monkeypatch, target, learner_manifest)


def test_manifest_drift_after_load_is_detected(sealed_inputs, monkeypatch, tmp_path):
    source, learner_manifest = sealed_inputs
    target = tmp_path / "targets"
    shutil.copytree(source, target)
    provider = _provider(monkeypatch, target, learner_manifest)
    manifest = target / "MANIFEST.sha256"
    manifest.write_bytes(manifest.read_bytes() + b"\n")
    with pytest.raises(FACTORY.V023C1C2ProviderFactoryError):
        provider.next_batch(route="C1", source="neutral", update_cursor=0)


def test_c2_target_delta_is_never_divided_again(sealed_inputs, monkeypatch):
    target, learner_manifest = sealed_inputs
    loaded = FACTORY._TARGET.load_completed_target_artifact(target)
    expected = loaded.for_mode("neutral").c2_pair_batch.normalized_target_deltas
    provider = _provider(monkeypatch, target, learner_manifest)
    _call(provider, 0, "C1")
    delivered = provider.next_batch(
        route="C2", source="neutral", update_cursor=1
    ).batch.normalized_target_deltas
    assert delivered.dtype == expected.dtype
    assert delivered.shape == expected.shape
    assert delivered.tobytes() == expected.tobytes()


def test_uppercase_test_path_is_rejected(sealed_inputs):
    target, learner_manifest = sealed_inputs
    payload = _config_payload(target, learner_manifest)
    payload["target_root"] = "/tmp/closed-TEST-targets"
    with pytest.raises(FACTORY.V023C1C2ProviderFactoryError, match="TEST"):
        FACTORY.C1C2ProviderConfig.from_payload(payload)


def test_make_provider_uses_digest_bound_environment_config(
    sealed_inputs, monkeypatch, tmp_path
):
    target, learner_manifest = sealed_inputs
    config_path = tmp_path / "provider-config.json"
    config_path.write_bytes(_canonical(_config_payload(target, learner_manifest)))
    monkeypatch.setenv(FACTORY.CONFIG_PATH_ENV, str(config_path))
    monkeypatch.setenv(FACTORY.CONFIG_SHA256_ENV, _sha_file(config_path))
    monkeypatch.setenv(
        FACTORY.LEARNER_MANIFEST_PATH_ENV, str(learner_manifest)
    )
    provider = FACTORY.make_provider()
    assert provider.planned_epoch_budget == FACTORY.EPOCH_BUDGET
    assert provider.provider_identity_payload["provider_config_sha256"] == (
        _sha_file(config_path)
    )
