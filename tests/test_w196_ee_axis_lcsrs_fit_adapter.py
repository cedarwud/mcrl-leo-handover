"""W-196 -- non-heavy V0.23 learner-adapter receipt and isolation checks.

All source files below are synthetic immutable fixtures.  The injected fit
function constructs a valid frozen network and receipt without optimizer
updates; this test therefore exercises the adapter boundary without opening
the simulator, TLE, TEST split, or a real 2,000-update fit.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.runtime.ee_axis_lcsrs_c3_dataset import (
    LCSRS_DRAW_COUNT,
    LCSRSAnchorRecord,
    LCSRSPairTargets,
    assemble_lcsrs_anchor_surface,
)
from mcrl.runtime.ee_axis_lcsrs_c3_gate_fit import (
    V023_GATE_WORLDS,
    V023_PLACEBO_KEY,
    prepare_lcsrs_loo_fold,
)
from mcrl.runtime.ee_axis_lcsrs_c3_learner import (
    LCSRSC3FitReceipt,
    make_lcsrs_c3_student,
    lcsrs_c3_network_sha256,
)
from mcrl.runtime.ee_axis_lcsrs_c3_state import assemble_c3_view


ADAPTER_PATH = (
    Path(__file__).resolve().parents[1]
    / ".scratch"
    / "multi-catfish-v023-c3-observability"
    / "v023_lcsrs_fit_adapter.py"
)
_SPEC = importlib.util.spec_from_file_location("v023_lcsrs_fit_adapter_test", ADAPTER_PATH)
assert _SPEC is not None and _SPEC.loader is not None
adapter = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = adapter
_SPEC.loader.exec_module(adapter)


PRE_FLIGHT = "2" * 64
SOURCE_SCHEMA = "multi-catfish-mcrl-v023-lcsrs-observability-gate-v1-source-shard"
MANIFEST_SCHEMA = "multi-catfish-mcrl-v023-lcsrs-observability-gate-v1-source-manifest"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _array_digest(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(b"source-array-v1")
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _world_source(root: Path, world: int) -> Path:
    users, actions, anchors = 4, 28, 9
    context = np.zeros((anchors, users, actions, 29), dtype=np.float32)
    tokens = np.zeros(
        (anchors, users, actions, users + 1, 38), dtype=np.float32
    )
    mask = np.zeros((anchors, users, actions), dtype=np.bool_)
    mask[:, :, :4] = True
    token_mask = np.zeros((anchors, users, actions, users + 1), dtype=np.bool_)
    token_mask[:, :, :, users] = mask
    tokens[:, :, :, users, 1][mask] = 1.0
    # Two disjoint supported pairs use action 1 and action 2.
    tokens[:, 0:2, 1, users, 2:5] = 1.0
    tokens[:, 2:4, 2, users, 2:5] = 1.0
    context[:, :, :4, 3] = 1.0
    context[:, 0:2, 1, 27] = np.float32(1.0 / users)
    context[:, 2:4, 2, 27] = np.float32(1.0 / users)
    # Source artifacts retain the authenticated float32 Q1+Q2 surface; the
    # typed loader widens it to float64 only when constructing the record.
    q12 = np.zeros((anchors, users, actions), dtype=np.float32)
    q12[:, :, 1:] = -0.005
    context[:, :, :4, 23] = np.asarray(
        np.tanh(q12[:, :, :4] - q12[:, :, [0]]), dtype=np.float32
    )
    views = [
        assemble_c3_view(
            action_context=context[index],
            tokens=tokens[index],
            token_mask=token_mask[index],
            action_mask=mask[index],
            reference_actions=np.zeros(users, dtype=np.int64),
        )
        for index in range(anchors)
    ]
    pair_ids = [
        (f"w{world}-t{index + 1}-p0", f"w{world}-t{index + 1}-p1")
        for index in range(anchors)
    ]
    records: list[LCSRSAnchorRecord] = []
    pair_rows: list[tuple[int, str, np.ndarray, np.ndarray]] = []
    for index, view in enumerate(views):
        value = float(index + 1)
        first = LCSRSPairTargets(
            pair_id=pair_ids[index][0],
            user_ids=np.asarray([0, 1], dtype=np.int64),
            action_ids=np.asarray([1, 1], dtype=np.int64),
            normalized_targets_by_draw=np.tile(
                np.asarray([[value, -value]], dtype=np.float64),
                (LCSRS_DRAW_COUNT, 1),
            ),
        )
        second = LCSRSPairTargets(
            pair_id=pair_ids[index][1],
            user_ids=np.asarray([2, 3], dtype=np.int64),
            action_ids=np.asarray([2, 2], dtype=np.int64),
            normalized_targets_by_draw=np.tile(
                np.asarray([[value + 0.25, -(value + 0.25)]], dtype=np.float64),
                (LCSRS_DRAW_COUNT, 1),
            ),
        )
        surface = assemble_lcsrs_anchor_surface(view, [first, second])
        records.append(
            LCSRSAnchorRecord(
                world_id=world,
                phase=index + 1,
                anchor_id=f"w{world}:t{index + 1}",
                surface=surface,
                q12_values=q12[index],
            )
        )
    physical_keys = np.zeros((anchors, users, actions, 2), dtype=np.int64)
    physical_keys[..., 0] = 10
    physical_keys[..., 1] = np.arange(actions, dtype=np.int64)
    pair_anchor: list[int] = []
    pair_id: list[str] = []
    pair_users: list[list[int]] = []
    pair_actions: list[list[int]] = []
    pair_draws: list[np.ndarray] = []
    for index in range(anchors):
        for offset, (users_pair, actions_pair) in enumerate(
            (((0, 1), (1, 1)), ((2, 3), (2, 2)))
        ):
            value = float(index + 1 + offset * 0.25)
            pair_anchor.append(index)
            pair_id.append(pair_ids[index][offset])
            pair_users.append(list(users_pair))
            pair_actions.append(list(actions_pair))
            pair_draws.append(
                np.tile(
                    np.asarray([[value, -value]], dtype=np.float64),
                    (LCSRS_DRAW_COUNT, 1),
                )
            )
    arrays = {
        "anchor_phase": np.arange(1, 10, dtype=np.int64),
        "anchor_retained": np.ones(anchors, dtype=np.bool_),
        "anchor_view_content_digest": np.asarray(
            [view.content_digest.encode("ascii") for view in views], dtype="S64"
        ),
        "action_context": context,
        "tokens": tokens,
        "token_mask": token_mask,
        "action_mask": mask,
        "reference_actions": np.zeros((anchors, users), dtype=np.int64),
        "opening_feasibility": mask.copy(),
        "physical_keys": physical_keys,
        "q1_values": q12.copy(),
        "q2_values": np.zeros_like(q12),
        "q12_values": q12.copy(),
        # The current typed source-artifact contract carries the complete
        # target-free Q2 context alongside the C3 fitting records.  This
        # learner-adapter fixture does not exercise Q2 arithmetic, but it must
        # still model the production sidecar schema exactly.
        "q2_state_matrix": np.zeros((anchors, users, 448), dtype=np.float32),
        "q2_feature_surface": np.zeros(
            (anchors, users, actions, 16), dtype=np.float64
        ),
        "q2_teacher_values": np.zeros(
            (anchors, users, actions), dtype=np.float64
        ),
        "q2_persistence": np.zeros(
            (anchors, users, 3, actions), dtype=np.float64
        ),
        "q2_rate_bps": np.zeros(
            (anchors, users, 3, actions), dtype=np.float64
        ),
        "q2_marginal_power_w": np.zeros(
            (anchors, users, 3, actions), dtype=np.float64
        ),
        "q2_required_power_w": np.zeros(
            (anchors, users, 3, actions), dtype=np.float64
        ),
        "q2_horizon": np.asarray(
            [min(3, 9 - phase) for phase in range(1, 10)], dtype=np.int64
        ),
        "pair_anchor_index": np.asarray(pair_anchor, dtype=np.int64),
        "pair_id": np.asarray([value.encode("ascii") for value in pair_id], dtype="S256"),
        "pair_user_ids": np.asarray(pair_users, dtype=np.int64),
        "pair_action_ids": np.asarray(pair_actions, dtype=np.int64),
        "pair_target_by_draw": np.stack(pair_draws),
        "pair_target_mean": np.mean(np.stack(pair_draws), axis=1),
        "pair_class": np.full((len(pair_id), 2), 3, dtype=np.uint8),
    }
    sidecar = root / f"world-{world}.arrays.npz"
    np.savez_compressed(sidecar, **arrays)
    sidecar_sha = hashlib.sha256(sidecar.read_bytes()).hexdigest()
    (root / f"{sidecar.name}.sha256").write_text(
        f"{sidecar_sha}  {sidecar.name}\n", encoding="ascii"
    )
    metadata = {
        name: {
            "dtype": value.dtype.str,
            "shape": list(value.shape),
            "sha256": _array_digest(value),
        }
        for name, value in arrays.items()
    }
    anchors_payload = []
    for index, record in enumerate(records):
        anchors_payload.append(
            {
                "anchor_id": record.anchor_id,
                "phase": index + 1,
                "retained_for_fitting": True,
                "topology": {
                    "pairs": [
                        {"pair_id": pair_ids[index][0]},
                        {"pair_id": pair_ids[index][1]},
                    ]
                },
                "surface": {
                    "record": {
                        "surface_digest": record.surface.content_digest,
                        "content_digest": record.content_digest,
                    }
                },
            }
        )
    payload: dict[str, object] = {
        "schema": SOURCE_SCHEMA,
        "status": "PASS",
        "claim_ceiling": adapter.V023_FIT_CLAIM_CEILING,
        "contract_sha256": adapter.V023_CONTRACT_SHA256,
        "preflight_manifest_sha256": PRE_FLIGHT,
        "execution_addendum_sha256": adapter.V023_EXECUTION_ADDENDUM_SHA256,
        "placebo_key_sha256": adapter.V023_PLACEBO_KEY_SHA256,
        "split": "TRAIN_DEVELOPMENT",
        "world": world,
        "source_artifact_schema": adapter.V023_SOURCE_ARTIFACT_SCHEMA,
        "source_artifact_version": adapter.V023_SOURCE_ARTIFACT_VERSION,
        "anchors": anchors_payload,
        "arrays": {
            "allow_pickle": False,
            "npz_relative_path": sidecar.name,
            "npz_sha256": sidecar_sha,
            "npz_sha256_file": f"{sidecar.name}.sha256",
            "array_metadata": metadata,
        },
        "record_count": len(records),
        "pair_count": len(pair_id),
        "supported_count": len(pair_id) * 2,
        "placebo_eligible_count": len(pair_id) * 2,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
    }
    payload["receipt_sha256"] = hashlib.sha256(_canonical(payload)).hexdigest()
    index = root / f"world-{world}.json"
    index.write_bytes(_canonical(payload))
    return index


def _source_root(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "sources"
    root.mkdir()
    source_dir = root / "source"
    source_dir.mkdir()
    entries = []
    for world in V023_GATE_WORLDS:
        index = _world_source(source_dir, world)
        entries.append(
            {
                "world": world,
                "relative_name": f"source/world-{world}.json",
                "sha256": hashlib.sha256(index.read_bytes()).hexdigest(),
            }
        )
    body: dict[str, object] = {
        "schema": MANIFEST_SCHEMA,
        "status": "PASS",
        "claim_ceiling": adapter.V023_FIT_CLAIM_CEILING,
        "contract_sha256": adapter.V023_CONTRACT_SHA256,
        "preflight_manifest_sha256": PRE_FLIGHT,
        "split": "TRAIN_DEVELOPMENT",
        "worlds": list(V023_GATE_WORLDS),
        "source_count": 8,
        "shards": [
            {"world": world, "relative_name": f"source/world-{world}.json"}
            for world in V023_GATE_WORLDS
        ],
        "entries": entries,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
    }
    body["source_manifest_sha256"] = adapter.canonical_sha256(body)
    body["manifest_sha256"] = adapter.canonical_sha256(body)
    manifest = root / "source-manifest.json"
    manifest.write_bytes(_canonical(body))
    return root, manifest


def _fake_fit(
    source,
    *,
    arm: str,
    student_seed: int,
    device,
):
    network, _optimizer = make_lcsrs_c3_student(student_seed=student_seed, device=device)
    targets = (
        tuple(record.surface.normalized_targets for record in source.training_records)
        if arm == "INFORMED"
        else tuple(source.matched_placebo.normalized_targets_by_anchor)
    )
    digest = hashlib.sha256()
    digest.update(b"multi-catfish-mcrl-v023-lcsrs-fitting-source-v1")
    for record, target in zip(source.training_records, targets, strict=True):
        digest.update(record.surface.content_digest.encode("ascii"))
        digest.update(np.ascontiguousarray(target, dtype=np.float32).tobytes())
    logical = lcsrs_c3_network_sha256(network)
    receipt = LCSRSC3FitReceipt(
        arm=arm,
        student_seed=student_seed,
        source_anchor_sha256s=tuple(
            record.content_digest for record in source.training_records
        ),
        target_source_sha256=digest.hexdigest(),
        initial_network_sha256=logical,
        final_network_sha256=logical,
        losses=np.zeros(2000, dtype=np.float64),
    )
    return network, receipt


def _spec(root: Path, manifest: Path, output: Path, *, arm: str = "INFORMED"):
    return SimpleNamespace(
        held_out_world=V023_GATE_WORLDS[0],
        student_seed=2026135101,
        arm=arm,
        source_directory=root,
        source_manifest=manifest,
        output=output,
        preflight_manifest_sha256=PRE_FLIGHT,
    )


def test_source_panel_and_loo_fit_persist_true_heldout_rows(tmp_path: Path) -> None:
    root, manifest = _source_root(tmp_path)
    output = tmp_path / "fit" / "world.json"
    calls: list[tuple[str, int]] = []

    def fake(source, *, arm, student_seed, device):
        calls.append((arm, student_seed))
        return _fake_fit(
            source, arm=arm, student_seed=student_seed, device=device
        )

    fitted = adapter.V023LearnerAdapter(fit_function=fake).fit_shard(
        _spec(root, manifest, output)
    )
    assert calls == [("INFORMED", 2026135101)]
    assert fitted["schema"] == adapter.V023_FIT_SCHEMA
    assert fitted["update_count"] == 2000
    assert fitted["test_split_opened"] is False
    assert fitted["episode_training"] is False
    assert fitted["learner_update"] is True
    assert fitted["metrics"]["heldout_supported_rows"] == 36
    assert fitted["metrics"]["denominators"]["sign_total_rows"] == 36
    for key in ("model_sha256", "metrics_sha256"):
        assert isinstance(fitted[key], str) and len(fitted[key]) == 64
    assert output.with_suffix(".model.npz").is_file()
    assert output.with_suffix(".fit-receipt.json").is_file()
    assert output.with_suffix(".metrics.npz").is_file()
    assert output.with_suffix(".metrics.json").is_file()
    assert output.with_suffix(".placebo.json").is_file()
    with np.load(output.with_suffix(".metrics.npz"), allow_pickle=False) as values:
        assert all(values[name].dtype != object for name in values.files)
        assert values["identity_world"].shape == (36,)
        assert values["prediction"].shape == (36,)
        assert values["target"].shape == (36,)


def test_adapter_receipt_is_accepted_by_runner_writer(tmp_path: Path) -> None:
    root, manifest = _source_root(tmp_path)
    output = tmp_path / "fit" / "world.json"
    payload = adapter.V023LearnerAdapter(fit_function=_fake_fit).fit_shard(
        _spec(root, manifest, output)
    )
    runner_path = ADAPTER_PATH.parent / "run_v023_lcsrs_observability_gate.py"
    runner_spec = importlib.util.spec_from_file_location(
        "v023_runner_for_w196", runner_path
    )
    assert runner_spec is not None and runner_spec.loader is not None
    runner = importlib.util.module_from_spec(runner_spec)
    import sys

    sys.modules[runner_spec.name] = runner
    runner_spec.loader.exec_module(runner)
    written = runner.write_fit_shard(
        runner.FitShardSpec(
            held_out_world=V023_GATE_WORLDS[0],
            student_seed=2026135101,
            arm="INFORMED",
            source_directory=root,
            output=output,
            source_manifest=manifest,
            preflight_manifest_sha256=PRE_FLIGHT,
        ),
        payload=payload,
        preflight_sha256=PRE_FLIGHT,
        source_manifest_sha256=payload["source_manifest_sha256"],
    )
    assert written == output
    assert json.loads(output.read_text(encoding="ascii"))["status"] == "PASS"
    verified = adapter.verify_v023_fit_sidecars(output)
    assert verified["status"] == "PASS_FIT_SIDECARS"


def test_fit_sidecar_verifier_rejects_model_tampering(tmp_path: Path) -> None:
    root, manifest = _source_root(tmp_path)
    output = tmp_path / "fit" / "world.json"
    payload = adapter.V023LearnerAdapter(fit_function=_fake_fit).fit_shard(
        _spec(root, manifest, output)
    )
    runner_path = ADAPTER_PATH.parent / "run_v023_lcsrs_observability_gate.py"
    runner_spec = importlib.util.spec_from_file_location(
        "v023_runner_for_w196_tamper", runner_path
    )
    assert runner_spec is not None and runner_spec.loader is not None
    runner = importlib.util.module_from_spec(runner_spec)
    import sys

    sys.modules[runner_spec.name] = runner
    runner_spec.loader.exec_module(runner)
    runner.write_fit_shard(
        runner.FitShardSpec(
            held_out_world=V023_GATE_WORLDS[0],
            student_seed=2026135101,
            arm="INFORMED",
            source_directory=root,
            output=output,
            source_manifest=manifest,
            preflight_manifest_sha256=PRE_FLIGHT,
        ),
        payload=payload,
        preflight_sha256=PRE_FLIGHT,
        source_manifest_sha256=payload["source_manifest_sha256"],
    )
    model = output.with_suffix(".model.npz")
    model.write_bytes(model.read_bytes() + b"tamper")
    with pytest.raises(adapter.V023LearnerAdapterError, match="model"):
        adapter.verify_v023_fit_sidecars(output)


def test_fit_sidecar_verifier_rejects_metrics_tampering(tmp_path: Path) -> None:
    root, manifest = _source_root(tmp_path)
    output = tmp_path / "fit" / "world.json"
    payload = adapter.V023LearnerAdapter(fit_function=_fake_fit).fit_shard(
        _spec(root, manifest, output)
    )
    runner_path = ADAPTER_PATH.parent / "run_v023_lcsrs_observability_gate.py"
    runner_spec = importlib.util.spec_from_file_location(
        "v023_runner_for_w196_metrics_tamper", runner_path
    )
    assert runner_spec is not None and runner_spec.loader is not None
    runner = importlib.util.module_from_spec(runner_spec)
    import sys

    sys.modules[runner_spec.name] = runner
    runner_spec.loader.exec_module(runner)
    runner.write_fit_shard(
        runner.FitShardSpec(
            held_out_world=V023_GATE_WORLDS[0],
            student_seed=2026135101,
            arm="INFORMED",
            source_directory=root,
            output=output,
            source_manifest=manifest,
            preflight_manifest_sha256=PRE_FLIGHT,
        ),
        payload=payload,
        preflight_sha256=PRE_FLIGHT,
        source_manifest_sha256=payload["source_manifest_sha256"],
    )
    metrics = output.with_suffix(".metrics.npz")
    metrics.write_bytes(metrics.read_bytes() + b"tamper")
    with pytest.raises(adapter.V023LearnerAdapterError, match="metrics"):
        adapter.verify_v023_fit_sidecars(output)


def test_placebo_uses_same_budget_and_fold_rows_but_different_targets(
    tmp_path: Path,
) -> None:
    root, manifest = _source_root(tmp_path)
    informed_output = tmp_path / "fit" / "informed.json"
    placebo_output = tmp_path / "fit" / "placebo.json"
    informed = adapter.V023LearnerAdapter(fit_function=_fake_fit).fit_shard(
        _spec(root, manifest, informed_output, arm="INFORMED")
    )
    placebo = adapter.V023LearnerAdapter(fit_function=_fake_fit).fit_shard(
        _spec(root, manifest, placebo_output, arm="MATCHED_PLACEBO")
    )
    assert informed["update_count"] == placebo["update_count"] == 2000
    assert informed["student_seed"] == placebo["student_seed"]
    assert informed["fold"]["training_anchor_sha256s"] == placebo["fold"][
        "training_anchor_sha256s"
    ]
    assert (
        informed["fit_receipt"]["target_source_sha256"]
        != placebo["fit_receipt"]["target_source_sha256"]
    )
    assert placebo["placebo"]["meets_coverage_gate"] is True


def test_exact_fit_schedule_has_48_unique_fold_seed_arm_identities() -> None:
    identities = adapter.V023LearnerAdapter.expected_fit_identities()
    assert len(identities) == 48
    assert len(set(identities)) == 48
    assert {world for world, _seed, _arm in identities} == set(V023_GATE_WORLDS)


def test_fit_refuses_output_or_sidecar_overwrite(tmp_path: Path) -> None:
    root, manifest = _source_root(tmp_path)
    output = tmp_path / "fit" / "world.json"
    output.parent.mkdir()
    output.write_bytes(b"already-owned")
    with pytest.raises(adapter.V023LearnerAdapterError, match="overwrite"):
        adapter.V023LearnerAdapter(fit_function=_fake_fit).fit_shard(
            _spec(root, manifest, output)
        )


def test_fit_rejects_tampered_source_manifest_child(tmp_path: Path) -> None:
    root, manifest = _source_root(tmp_path)
    child = root / "source" / f"world-{V023_GATE_WORLDS[0]}.json"
    child.write_bytes(child.read_bytes().replace(b'"pair_count":18', b'"pair_count":19'))
    with pytest.raises(adapter.V023LearnerAdapterError, match="byte hash"):
        adapter.V023LearnerAdapter(fit_function=_fake_fit).fit_shard(
            _spec(root, manifest, tmp_path / "fit" / "world.json")
        )
