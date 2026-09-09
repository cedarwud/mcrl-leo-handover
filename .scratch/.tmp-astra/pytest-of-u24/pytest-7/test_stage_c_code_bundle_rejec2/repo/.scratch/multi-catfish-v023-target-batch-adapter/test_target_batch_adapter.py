"""Fast contract tests for the isolated V0.23 target-batch adapter."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from functools import lru_cache
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent))

from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch
from mcrl.algorithms.ee_axis_v014_head import EEAxisV014NormalizedPairBatch
from mcrl.env.action_contract import NUM_ACTIONS
from mcrl.runtime.ee_axis_c1_selector import (
    C1_CLUSTER_NEUTRAL_SOURCE_RULE,
    C1_INFORMED_SOURCE_RULE,
)
from mcrl.runtime.ee_axis_lcsrs_c3_dataset import (
    LCSRSPairTargets,
    assemble_lcsrs_anchor_surface,
)
from mcrl.runtime.ee_axis_lcsrs_c3_learner import (
    LCSRSC3ClassBalancedSampler,
    LCSRSC3SampledBatch,
)
from mcrl.runtime.ee_axis_lcsrs_c3_state import assemble_c3_view
from mcrl.runtime.ee_axis_opening_dataset import (
    EEAxisOpeningDataset,
    EEAxisOpeningDatasetRow,
    write_opening_dataset,
)
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
from mcrl.runtime.ee_axis_c2_neutral_source import C2_INFORMED_SOURCE_RULE
from mcrl.runtime.ee_axis_opening_runner import C3_NEUTRAL_SOURCE_RULE

from target_batch_adapter import (
    V023C3Inputs,
    V023TargetBatchAdapterError,
    build_route_schedule,
    load_completed_target_artifact,
    load_lcsrs_c3_inputs,
)


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


def _c1_dataset(*, mode: str, world: int, source_rule: str | None = None) -> EEAxisOpeningDataset:
    manifest = _digest("target-source-manifest")
    checkpoint = _digest("target-checkpoint")
    field = _digest(f"target-field-{mode}-{world}")
    state = np.zeros(EE_AXIS_STATE_DIM, dtype=np.float32)
    state[0] = np.float32(world)
    mask = np.zeros(NUM_ACTIONS, dtype=np.bool_)
    mask[[0, 1]] = True
    reference_joint = np.asarray([0, 1], dtype=np.int64)
    candidate_joint = np.asarray([1, 1], dtype=np.int64)
    raw_placeholder = EEAxisOpeningRawPair(
        source_policy_version=1,
        anchor_sha256=_digest(f"c1-anchor-{mode}-{world}"),
        source_manifest_sha256=manifest,
        checkpoint_sha256=checkpoint,
        common_random_field_sha256=field,
        state_schema=EE_AXIS_STATE_SCHEMA,
        state_schema_sha256=EE_AXIS_STATE_SCHEMA_SHA256,
        state_observation_sha256=_digest(f"c1-state-observation-{mode}-{world}"),
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
        lambda_bits_per_j=2.0,
        interval_s=1.0,
        comparison_sha256="0" * 64,
    )
    raw = replace(
        raw_placeholder,
        comparison_sha256=opening_sha256(opening_raw_payload(raw_placeholder)),
    )
    from mcrl.runtime.ee_axis_opening_pairs import build_opening_pair

    c1 = build_opening_pair(
        source_route="C1",
        source_rule=source_rule
        or (C1_INFORMED_SOURCE_RULE if mode == "informed" else C1_CLUSTER_NEUTRAL_SOURCE_RULE),
        source_policy_version=raw.source_policy_version,
        anchor_sha256=raw.anchor_sha256,
        source_manifest_sha256=manifest,
        checkpoint_sha256=checkpoint,
        common_random_field_sha256=field,
        focal_user=0,
        state=state,
        action_mask=mask,
        reference_action=0,
        candidate_action=1,
        reference_joint_actions=reference_joint,
        candidate_joint_actions=candidate_joint,
        reference_rates_bps=raw.reference_rates_bps,
        candidate_rates_bps=raw.candidate_rates_bps,
        reference_system_power_w=raw.reference_system_power_w,
        candidate_system_power_w=raw.candidate_system_power_w,
        lambda_bits_per_j=raw.lambda_bits_per_j,
        interval_s=raw.interval_s,
    )
    c3 = build_opening_pair(
        source_route="C3",
        source_rule=C3_NEUTRAL_SOURCE_RULE,
        source_policy_version=raw.source_policy_version,
        anchor_sha256=raw.anchor_sha256,
        source_manifest_sha256=manifest,
        checkpoint_sha256=checkpoint,
        common_random_field_sha256=field,
        focal_user=0,
        state=state,
        action_mask=mask,
        reference_action=0,
        candidate_action=1,
        reference_joint_actions=reference_joint,
        candidate_joint_actions=candidate_joint,
        reference_rates_bps=raw.reference_rates_bps,
        candidate_rates_bps=raw.candidate_rates_bps,
        reference_system_power_w=raw.reference_system_power_w,
        candidate_system_power_w=raw.candidate_system_power_w,
        lambda_bits_per_j=raw.lambda_bits_per_j,
        interval_s=raw.interval_s,
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
        source_manifest_sha256=manifest,
        checkpoint_sha256=checkpoint,
        common_random_field_sha256=field,
        state_schema=EE_AXIS_STATE_SCHEMA,
        state_schema_sha256=EE_AXIS_STATE_SCHEMA_SHA256,
        rows=(row,),
    )


HERE = Path(__file__).resolve().parent
REAL_R5_C2_EXCERPT = HERE / "fixtures-real-r5" / "c2-neutral-world-2026121708.excerpt.json"
GENERATOR_PATH = (
    HERE.parent
    / "multi-catfish-v023-c1c2-target-generation"
    / "generate_v023_c1c2_targets.py"
)
LAUNCH_DIR = HERE.parent / "multi-catfish-v023-c1c2-target-generation-launch"


def _load_path_module(name: str, path: Path):
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=1)
def _producer_modules():
    controller = _load_path_module(
        "v023_target_fixture_controller",
        LAUNCH_DIR / "run_v023_c1c2_targets_server.py",
    )
    generator = controller._load_generator()
    assert Path(generator.__file__).resolve() == GENERATOR_PATH.resolve()
    sealer = _load_path_module(
        "v023_target_fixture_sealer",
        LAUNCH_DIR / "seal_v023_c1c2_target_output.py",
    )
    return generator, controller, sealer


def _c1_binding(dataset: EEAxisOpeningDataset, *, mode: str, world: int) -> dict[str, object]:
    row = dataset.rows[0]
    raw = row.raw_pair
    candidate = raw.candidate_physical_keys[raw.focal_user]
    assert candidate is not None
    return {
        "mode": mode,
        "source_anchor_sha256": raw.anchor_sha256,
        "source_record_sha256": _digest(f"source-record-{mode}"),
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


def _c2_dataset_and_binding(*, mode: str, world: int) -> tuple[dict[str, object], dict[str, object]]:
    excerpt = json.loads(REAL_R5_C2_EXCERPT.read_text(encoding="ascii"))
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
    return (
        {
            "schema": excerpt["schema"],
            "source_manifest_sha256": _digest("target-source-manifest"),
            "checkpoint_sha256": _digest("target-checkpoint"),
            "lambda_bits_per_j": float(2.0).hex(),
            "kappa_bits": float(3.0).hex(),
            "target_unit": excerpt["target_unit"],
            "rows": [row],
        },
        binding,
    )


def _schedule_row(binding: dict[str, object], *, route: str) -> dict[str, object]:
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


def _write_artifact(
    root: Path,
    *,
    bad_c1_neutral_identity: bool = False,
    bad_c2_neutral_identity: bool = False,
    receipt_patch: dict[str, object] | None = None,
) -> Path:
    generator, controller, sealer = _producer_modules()
    world = 1
    shards: dict[str, Path] = {}
    expected_schedule: dict[str, dict[str, object]] = {}
    sealed = SimpleNamespace(
        capture_path=root.parent / "capture.json",
        capture_sha256=_digest("capture"),
        materialization_dir=root.parent / "materialization",
        materialization_manifest_sha256=_digest("materialization-manifest"),
        pool_sha256=_digest("pool"),
        source_manifest_sha256=_digest("target-source-manifest"),
        checkpoint_sha256=_digest("target-checkpoint"),
    )
    ctx = SimpleNamespace(
        modules=SimpleNamespace(
            opening_dataset=SimpleNamespace(write_opening_dataset=write_opening_dataset)
        ),
        source_family="fixture-source-family",
        lambda_bits_per_j=2.0,
        kappa_bits=3.0,
        interval_s=1.0,
    )
    for mode in ("informed", "neutral"):
        c1_rule = C1_INFORMED_SOURCE_RULE if mode == "informed" else (
            C1_INFORMED_SOURCE_RULE if bad_c1_neutral_identity else C1_CLUSTER_NEUTRAL_SOURCE_RULE
        )
        c1_dataset = _c1_dataset(mode=mode, world=world, source_rule=c1_rule)
        c1_binding = _c1_binding(c1_dataset, mode=mode, world=world)
        c2_dataset, c2_binding = _c2_dataset_and_binding(mode=mode, world=world)
        key = f"{mode}:{world}"
        shard_schedule = {
            key: {
                "mode": mode,
                "world": world,
                "C1": [_schedule_row(c1_binding, route="C1")],
                "C2": [_schedule_row(c2_binding, route="C2")],
            }
        }
        shard = root.parent / f"{root.name}-{mode}-shard"
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

    if bad_c2_neutral_identity:
        path = root / f"c2-neutral-world-{world}.json"
        payload = json.loads(path.read_text(encoding="ascii"))
        payload["rows"][0]["mode"] = "informed"
        path.write_bytes(_canonical(payload))
        receipt = json.loads((root / "receipt.json").read_text(encoding="ascii"))
        receipt["datasets"]["C2"][f"neutral:{world}"]["dataset_sha256"] = hashlib.sha256(
            _canonical(payload)[:-1]
        ).hexdigest()
        (root / "receipt.json").write_bytes(_canonical(receipt))
        _reseal(root)

    if receipt_patch:
        receipt = json.loads((root / "receipt.json").read_text(encoding="ascii"))
        receipt.update(receipt_patch)
        (root / "receipt.json").write_bytes(_canonical(receipt))
        _reseal(root)
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
    manifest_sha = hashlib.sha256(manifest).hexdigest()
    (root / "COMPLETE").write_text(f"{manifest_sha}  MANIFEST.sha256\n", encoding="ascii")


def _c3_inputs():
    users = 2
    action_context = np.zeros((users, NUM_ACTIONS, 29), dtype=np.float32)
    tokens = np.zeros((users, NUM_ACTIONS, users + 1, 38), dtype=np.float32)
    token_mask = np.zeros((users, NUM_ACTIONS, users + 1), dtype=np.bool_)
    action_mask = np.zeros((users, NUM_ACTIONS), dtype=np.bool_)
    action_mask[:, :3] = True
    reference_actions = np.zeros(users, dtype=np.int64)
    pair_token = tokens[:, :, users]
    pair_token[:, :, 1] = action_mask
    pair_token[:, :, 2:5] = action_mask[:, :, None]
    token_mask[:, :, users] = action_mask
    view = assemble_c3_view(
        action_context=action_context,
        tokens=tokens,
        token_mask=token_mask,
        action_mask=action_mask,
        reference_actions=reference_actions,
    )
    pair = LCSRSPairTargets(
        pair_id="fixture-pair",
        user_ids=np.asarray([0, 1], dtype=np.int64),
        action_ids=np.asarray([1, 1], dtype=np.int64),
        normalized_targets_by_draw=np.ones((32, 2), dtype=np.float64),
    )
    surface = assemble_lcsrs_anchor_surface(view, (pair,))
    sampled = LCSRSC3ClassBalancedSampler((surface,), student_seed=17).draw(6)
    return load_lcsrs_c3_inputs((surface,), (sampled,))


def test_completed_root_returns_exact_typed_c1_c2_batches_and_separates_modes(tmp_path):
    artifact = load_completed_target_artifact(_write_artifact(tmp_path / "targets"))
    informed = artifact.for_mode("informed")
    neutral = artifact.for_mode("neutral")

    assert isinstance(informed.c1_pair_batch, EEAxisPairBatch)
    assert isinstance(informed.c2_pair_batch, EEAxisV014NormalizedPairBatch)
    assert informed.c1_pair_batch.states.shape == (1, EE_AXIS_STATE_DIM)
    assert informed.c2_pair_batch.states.shape == (1, 448)
    assert informed.c1_pair_batch.target_surplus_bits.tolist() == [8.0]
    assert informed.c2_pair_batch.normalized_target_deltas.tolist() == [
        informed.c2_datasets[0].dataset.rows[0]["target_delta"]
    ]
    assert not informed.c1_pair_batch.states.flags.writeable
    assert not informed.c2_pair_batch.states.flags.writeable
    assert informed.c1_route_batches[0].route == "C1"
    assert informed.c2_route_batches[0].route == "C2"
    assert informed.c1_datasets[0].dataset.rows[0].c1_source_rule == C1_INFORMED_SOURCE_RULE
    assert neutral.c1_datasets[0].dataset.rows[0].c1_source_rule == C1_CLUSTER_NEUTRAL_SOURCE_RULE
    assert informed.c2_datasets[0].dataset.rows[0]["mode"] == "informed"
    assert neutral.c2_datasets[0].dataset.rows[0]["mode"] == "neutral"
    assert neutral.c2_datasets[0].dataset.rows[0]["source_rule"] == C2_NEUTRAL_SOURCE_RULE


@pytest.mark.parametrize("failure", ("complete", "manifest", "file"))
def test_authentication_rejects_incomplete_or_digest_drift(tmp_path, failure):
    root = _write_artifact(tmp_path / "targets")
    if failure == "complete":
        (root / "COMPLETE").unlink()
    elif failure == "manifest":
        (root / "MANIFEST.sha256").write_bytes(b"0" * 64 + b"  receipt.json\n")
    else:
        path = root / "c1-informed-world-1.json"
        path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(V023TargetBatchAdapterError):
        load_completed_target_artifact(root)


def test_route_identity_rejects_mixed_informed_neutral_rows(tmp_path):
    root = _write_artifact(tmp_path / "targets", bad_c1_neutral_identity=True)
    with pytest.raises(V023TargetBatchAdapterError, match="mixed source identity"):
        load_completed_target_artifact(root)

    root = _write_artifact(tmp_path / "targets-c2", bad_c2_neutral_identity=True)
    with pytest.raises(V023TargetBatchAdapterError, match="row mode disagrees"):
        load_completed_target_artifact(root)


def test_family_level_c2_receipt_rule_does_not_replace_concrete_typed_row(tmp_path):
    root = _write_artifact(tmp_path / "targets")
    artifact = load_completed_target_artifact(root)
    informed = artifact.for_mode("informed")
    row = informed.c2_datasets[0].dataset.rows[0]
    schedule_row = artifact.receipt["schedule"]["shards"]["informed:1"]["C2"][0]
    assert informed.c2_route_batches[0].route == "C2"
    assert row["source_rule"] == C2_INFORMED_SOURCE_RULE
    assert schedule_row["source_rule"] == row["source_rule"]

    path = root / "c2-informed-world-1.json"
    payload = json.loads(path.read_text(encoding="ascii"))
    payload["rows"][0]["source_rule"] = "C2"
    path.write_bytes(_canonical(payload))
    receipt = json.loads((root / "receipt.json").read_text(encoding="ascii"))
    receipt["datasets"]["C2"]["informed:1"]["dataset_sha256"] = hashlib.sha256(
        _canonical(payload)[:-1]
    ).hexdigest()
    (root / "receipt.json").write_bytes(_canonical(receipt))
    _reseal(root)
    with pytest.raises(V023TargetBatchAdapterError, match="missing its authenticated binding"):
        load_completed_target_artifact(root)


def test_malformed_receipt_and_manifest_closure_are_rejected(tmp_path):
    root = _write_artifact(
        tmp_path / "bad-receipt",
        receipt_patch={"datasets": {"C1": {}, "C2": {}}},
    )
    with pytest.raises(V023TargetBatchAdapterError):
        load_completed_target_artifact(root)

    root = _write_artifact(tmp_path / "extra-file")
    extra = root / "extra.json"
    extra.write_text("{}", encoding="ascii")
    with pytest.raises(V023TargetBatchAdapterError):
        load_completed_target_artifact(root)


def test_batch_order_and_schedule_are_deterministic(tmp_path):
    root = _write_artifact(tmp_path / "targets")
    first = load_completed_target_artifact(root).for_mode("informed")
    second = load_completed_target_artifact(root).for_mode("informed")
    assert np.array_equal(first.c1_pair_batch.states, second.c1_pair_batch.states)
    assert np.array_equal(
        first.c2_pair_batch.normalized_target_deltas,
        second.c2_pair_batch.normalized_target_deltas,
    )

    c3 = _c3_inputs()
    one = build_route_schedule(first, c3, episodes=1)
    hundred = build_route_schedule(first, c3, episodes=100)
    assert one.dispatches == (
        one.dispatches[0],
        one.dispatches[1],
        one.dispatches[2],
    )
    assert [(item.route, item.batch_index) for item in one.dispatches] == [
        ("C1", 0),
        ("C2", 0),
        ("C3", 0),
    ]
    assert len(hundred.dispatches) == 300
    assert hundred.dispatches[:3] == one.dispatches
    assert hundred.dispatches[-1].episode_index == 99


def test_c3_loader_preserves_exact_typed_surface_and_sampled_batch():
    inputs = _c3_inputs()
    assert len(inputs.surfaces) == 1
    assert isinstance(inputs.surfaces[0].content_digest, str)
    assert isinstance(inputs.sampled_batches[0], LCSRSC3SampledBatch)
    assert inputs.sampled_batches[0].normalized_targets.dtype == np.float32
    assert len(inputs.normalized_targets_by_anchor) == 1
    assert inputs.normalized_targets_by_anchor[0].dtype == np.float32
    assert np.array_equal(
        inputs.normalized_targets_by_anchor[0], inputs.surfaces[0].normalized_targets
    )
    bad = replace(
        inputs.sampled_batches[0],
        anchor_indices=np.asarray([99] * inputs.sampled_batches[0].rows, dtype=np.int64),
    )
    with pytest.raises(V023TargetBatchAdapterError, match="outside surfaces"):
        load_lcsrs_c3_inputs(inputs.surfaces, (bad,))


def test_c3_input_legacy_two_argument_constructor_defaults_to_surface_targets():
    inputs = _c3_inputs()
    legacy = V023C3Inputs(inputs.surfaces, inputs.sampled_batches)
    assert legacy.normalized_targets_by_anchor is not None
    assert np.array_equal(
        legacy.normalized_targets_by_anchor[0], inputs.surfaces[0].normalized_targets
    )


def _c3_selected_target_inputs(value: float = 0.25):
    """Build a paired batch whose labels come from an explicit target surface."""

    base = _c3_inputs()
    selected = np.array(
        base.surfaces[0].normalized_targets, dtype=np.float32, copy=True, order="C"
    )
    selected[base.surfaces[0].row_class == 3] = np.float32(value)
    batch = base.sampled_batches[0]
    labels = np.asarray(
        [
            selected[int(user), int(action)]
            for _anchor, user, action in zip(
                batch.anchor_indices.tolist(),
                batch.user_indices.tolist(),
                batch.action_indices.tolist(),
                strict=True,
            )
        ],
        dtype=np.float32,
    )
    selected_batch = replace(batch, normalized_targets=labels)
    return base.surfaces, selected, selected_batch


def test_c3_loader_accepts_explicit_neutral_targets_without_rewriting_surface():
    surfaces, selected, batch = _c3_selected_target_inputs()
    inputs = load_lcsrs_c3_inputs(
        surfaces,
        (batch,),
        normalized_targets_by_anchor={0: selected},
    )
    assert np.array_equal(inputs.normalized_targets_by_anchor[0], selected)
    assert np.array_equal(inputs.sampled_batches[0].normalized_targets, batch.normalized_targets)
    assert not np.array_equal(
        inputs.normalized_targets_by_anchor[0], surfaces[0].normalized_targets
    )
    assert not inputs.normalized_targets_by_anchor[0].flags.writeable


def test_c3_loader_rejects_sample_label_that_matches_surface_but_not_selected_target():
    surfaces, selected, _batch = _c3_selected_target_inputs()
    with pytest.raises(V023TargetBatchAdapterError, match="target disagrees"):
        load_lcsrs_c3_inputs(
            surfaces,
            (_c3_inputs().sampled_batches[0],),
            normalized_targets_by_anchor=(selected,),
        )


@pytest.mark.parametrize(
    "override, pattern",
    (
        ((np.zeros((2, 2), dtype=np.float32),), "shape disagrees"),
        ((np.full((2, NUM_ACTIONS), np.nan, dtype=np.float32),), "non-finite"),
        ((np.eye(2, NUM_ACTIONS, dtype=np.float32),), "nonzero only"),
    ),
)
def test_c3_loader_rejects_malformed_or_illegal_target_overrides(override, pattern):
    surfaces = _c3_inputs().surfaces
    with pytest.raises(V023TargetBatchAdapterError, match=pattern):
        load_lcsrs_c3_inputs(
            surfaces,
            (),
            normalized_targets_by_anchor=override,
        )


def test_c3_loader_rejects_target_override_count_and_mapping_order_drift():
    surfaces = _c3_inputs().surfaces
    with pytest.raises(V023TargetBatchAdapterError, match="count must equal"):
        load_lcsrs_c3_inputs(surfaces, (), normalized_targets_by_anchor=())
    with pytest.raises(V023TargetBatchAdapterError, match="exactly cover anchor order"):
        load_lcsrs_c3_inputs(
            surfaces,
            (),
            normalized_targets_by_anchor={1: surfaces[0].normalized_targets},
        )


# --- 2026-09-07: real r5 shard rows through the OPS-3 route batch (dress-rehearsal regression) ---

def _load_adapter_for_real_rows():
    import importlib.util, sys as _sys
    spec = importlib.util.spec_from_file_location(
        "v023_target_batch_adapter_real_rows", Path(__file__).resolve().parent / "target_batch_adapter.py"
    )
    module = importlib.util.module_from_spec(spec)
    _sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_ops3_route_batch_stacks_real_r5_rows_into_448d_panel():
    """Three real producer rows must become a (3, 448) float32 panel with (3, 28) masks."""

    import json as _json
    adapter = _load_adapter_for_real_rows()
    payload = _json.loads(REAL_R5_C2_EXCERPT.read_text(encoding="ascii"))
    assert payload["schema"] == adapter.OPS3_SELECTED_PAIR_SCHEMA
    batch = adapter._ops3_route_batch(payload["rows"]).pair_batch
    assert batch.states.shape == (3, 448) and batch.states.dtype == np.float32
    assert batch.action_masks.shape == (3, 28) and batch.action_masks.dtype == np.bool_
    assert batch.normalized_target_deltas.shape == (3,)
    assert batch.reference_actions.shape == (3,) and batch.candidate_actions.shape == (3,)
    rows = payload["rows"]
    assert np.array_equal(
        batch.normalized_target_deltas, np.asarray([row["target_delta"] for row in rows], dtype=np.float64)
    )
    assert all(row["target_unit"] == adapter.OPS3_TARGET_UNIT for row in rows)
    # every row keeps its own mask and its legal reference/candidate
    for index, row in enumerate(rows):
        assert np.array_equal(batch.action_masks[index], np.asarray(row["action_mask"], dtype=np.bool_))
        assert batch.action_masks[index, row["reference_action"]] and batch.action_masks[index, row["candidate_action"]]


def test_ops3_route_batch_rejects_truncated_real_state_and_empty_rows():
    import json as _json
    adapter = _load_adapter_for_real_rows()
    payload = _json.loads(REAL_R5_C2_EXCERPT.read_text(encoding="ascii"))
    broken = [dict(payload["rows"][0])]
    broken[0]["q2_state"] = broken[0]["q2_state"][:-1]
    with pytest.raises(Exception, match="448-D"):
        adapter._ops3_route_batch(broken)
    with pytest.raises(Exception, match="no rows"):
        adapter._ops3_route_batch([])
