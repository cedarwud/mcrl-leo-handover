"""Focused tests for the lazy sealed V0.23 source provider."""

from __future__ import annotations

from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace

import numpy as np
import pytest

from mcrl.runtime.ee_axis_lcsrs_c3_dataset import (
    LCSRSPairTargets,
    LCSRSAnchorRecord,
    assemble_lcsrs_anchor_surface,
)
from mcrl.runtime.ee_axis_lcsrs_c3_placebo import (
    LCSRSPlaceboMapping,
    build_lcsrs_matched_placebo,
)
from mcrl.runtime.ee_axis_lcsrs_c3_state import assemble_c3_view


HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "v023_sealed_source_provider.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "v023_sealed_source_provider_test",
        MODULE_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


provider = _load_module()


def _surface(*, users: int = 2):
    actions = 28
    action_context = np.zeros((users, actions, 29), dtype=np.float32)
    action_context[:, 1, 3] = 1.0
    action_context[:, 1, 27] = 1.0 / users
    action_mask = np.ones((users, actions), dtype=np.bool_)
    token_mask = np.zeros((users, actions, users + 1), dtype=np.bool_)
    token_mask[:, :, users] = True
    tokens = np.zeros((users, actions, users + 1, 38), dtype=np.float32)
    tokens[:, :, users, 1] = 1.0
    tokens[:, 1, users, 2:5] = 1.0
    reference_actions = np.zeros(users, dtype=np.int64)
    view = assemble_c3_view(
        action_context=action_context,
        tokens=tokens,
        token_mask=token_mask,
        action_mask=action_mask,
        reference_actions=reference_actions,
    )
    draws = np.tile(np.asarray([[0.5, -0.25]], dtype=np.float64), (32, 1))
    pair = LCSRSPairTargets(
        pair_id=f"pair-{users}",
        user_ids=np.asarray([0, 1], dtype=np.int64),
        action_ids=np.asarray([1, 1], dtype=np.int64),
        normalized_targets_by_draw=draws,
    )
    return assemble_lcsrs_anchor_surface(view, [pair])


def _panel(*, users: int = 2, drift: bool = False):
    artifacts = []
    for index, world in enumerate(provider.V023_GATE_WORLDS):
        surface = _surface(users=users + 1 if drift and index == 1 else users)
        record = LCSRSAnchorRecord(
            world_id=world,
            phase=1,
            anchor_id=f"anchor-{world}",
            surface=surface,
            q12_values=np.zeros(surface.view.action_mask.shape, dtype=np.float64),
        )
        artifacts.append(SimpleNamespace(world=world, records=(record,)))
    return provider.SealedV023SourcePanel(
        source_directory=Path("/sealed/source"),
        source_manifest_path=Path("/sealed/source-manifest.json"),
        source_manifest_sha256="c" * 64,
        source_manifest_file_sha256="d" * 64,
        preflight_manifest_sha256="e" * 64,
        artifacts=tuple(artifacts),
    )


def test_panel_binding_builds_informed_and_equal_budget_neutral_arms() -> None:
    sources = provider.build_authenticated_v023_sources(
        _panel(),
        result_sha256="a" * 64,
        result_manifest_sha256="b" * 64,
    )
    informed = sources["INFORMED"]
    neutral = sources["NEUTRAL_SOURCE"]
    assert informed.arm == "INFORMED"
    assert neutral.arm == "NEUTRAL_SOURCE"
    assert informed.source_manifest_sha256 == neutral.source_manifest_sha256
    assert informed.source_manifest_file_sha256 == "d" * 64
    assert informed.result_sha256 == "a" * 64
    assert informed.result_manifest_sha256 == "b" * 64
    assert informed.source_row_count == neutral.source_row_count == 16
    assert informed.update_budget == neutral.update_budget == 2000
    assert informed.source_anchor_sha256s == neutral.source_anchor_sha256s
    assert any(
        not np.array_equal(left, right)
        for left, right in zip(informed.targets, neutral.targets, strict=True)
    )


def test_panel_binding_rejects_cross_world_placebo_mapping(monkeypatch) -> None:
    original = build_lcsrs_matched_placebo(_panel().records, placebo_key=provider.V023_PLACEBO_KEY)
    mapping = original.mappings[0]
    cross_world = replace(mapping, destination_anchor=mapping.destination_anchor + 1)
    forged = replace(original, mappings=(cross_world, *original.mappings[1:]))
    monkeypatch.setattr(provider, "build_lcsrs_matched_placebo", lambda *args, **kwargs: forged)
    with pytest.raises(provider.V023SealedSourceProviderError, match="leaks across worlds"):
        provider.build_authenticated_v023_sources(
            _panel(),
            result_sha256="a" * 64,
            result_manifest_sha256="b" * 64,
        )


def test_panel_binding_rejects_target_mask_shape_drift() -> None:
    with pytest.raises(provider.V023SealedSourceProviderError, match="target/mask shape"):
        provider.build_authenticated_v023_sources(
            _panel(drift=True),
            result_sha256="a" * 64,
            result_manifest_sha256="b" * 64,
        )


def _canonical(payload: dict[str, object]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii") + b"\n"


def _sealed_result_tree(tmp_path: Path, *, test_split_opened: bool = False):
    root = tmp_path / "gate"
    root.mkdir()
    source_hash = "c" * 64
    preflight_hash = "e" * 64
    result_payload = {
        "schema": "multi-catfish-mcrl-v023-lcsrs-result-v1",
        "status": "PASS_FINAL_INTEGRITY",
        "claim_ceiling": provider.V023_SOURCE_CLAIM_CEILING,
        "source_manifest_sha256": source_hash,
        "preflight_manifest_sha256": preflight_hash,
        "split": "TRAIN_DEVELOPMENT",
        "worlds": list(provider.V023_GATE_WORLDS),
        "source_count": 8,
        "test_split_opened": test_split_opened,
        "episode_training": False,
    }
    result_path = root / "result.json"
    result_path.write_bytes(_canonical(result_payload))
    result_sha = provider.file_sha256(result_path)
    entries = f"{result_sha}  result.json\n".encode("ascii")
    manifest_path = root / "MANIFEST.sha256"
    manifest_path.write_bytes(entries)
    manifest_sha = provider.file_sha256(manifest_path)
    complete_path = root / "COMPLETE"
    complete_path.write_bytes(f"{manifest_sha}  MANIFEST.sha256\n".encode("ascii"))
    return root, result_path, manifest_path, complete_path, result_payload, source_hash, preflight_hash


def test_result_manifest_and_complete_bind_result_bytes(tmp_path: Path) -> None:
    root, result_path, manifest_path, complete_path, payload, source_hash, preflight_hash = _sealed_result_tree(tmp_path)
    loaded, result_sha, manifest_sha = provider._verify_result_manifest(
        result_directory=root,
        result_path=result_path,
        result_manifest_path=manifest_path,
        complete_path=complete_path,
    )
    assert loaded == payload
    assert result_sha == provider.file_sha256(result_path)
    assert manifest_sha == provider.file_sha256(manifest_path)
    provider._verify_closed_result(
        loaded,
        source_manifest_sha256=source_hash,
        source_manifest_file_sha256="d" * 64,
        preflight_manifest_sha256=preflight_hash,
        result_manifest_sha256=manifest_sha,
        source_row_count=16,
    )


def test_result_boundary_rejects_test_artifact(tmp_path: Path) -> None:
    root, result_path, manifest_path, complete_path, _payload, source_hash, preflight_hash = _sealed_result_tree(
        tmp_path,
        test_split_opened=True,
    )
    loaded, _result_sha, manifest_sha = provider._verify_result_manifest(
        result_directory=root,
        result_path=result_path,
        result_manifest_path=manifest_path,
        complete_path=complete_path,
    )
    with pytest.raises(provider.V023SealedSourceProviderError, match="test_split_opened"):
        provider._verify_closed_result(
            loaded,
            source_manifest_sha256=source_hash,
            source_manifest_file_sha256="d" * 64,
            preflight_manifest_sha256=preflight_hash,
            result_manifest_sha256=manifest_sha,
            source_row_count=16,
        )


def test_provider_is_lazy_and_validates_arm_seed_before_io(tmp_path: Path) -> None:
    adapter = provider.SealedV023SourceProvider(
        source_directory=tmp_path / "does-not-exist",
        source_manifest=tmp_path / "does-not-exist/source-manifest.json",
        preflight_manifest_sha256="e" * 64,
        result_directory=tmp_path / "does-not-exist",
    )
    with pytest.raises(provider.V023SealedSourceProviderError, match="source arm"):
        adapter.provide(arm="MATCHED_PLACEBO", student_seed=provider.V023_STUDENT_SEEDS[0])
    with pytest.raises(provider.V023SealedSourceProviderError, match="student seed"):
        adapter.provide(arm="INFORMED", student_seed=0)


def test_provider_module_import_does_not_load_ladder_or_torch() -> None:
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import importlib.util, pathlib, sys; "
                f"p=pathlib.Path({str(MODULE_PATH)!r}); "
                "s=importlib.util.spec_from_file_location('sealed_probe', p); "
                "m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; "
                "assert s.loader is not None; s.loader.exec_module(m); "
                "print('torch' in sys.modules, 'mcrl_v023_postgate_update_ladder' in sys.modules)"
            ),
        ],
        cwd=HERE.parents[2],
        check=True,
        capture_output=True,
        text=True,
    )
    assert probe.stdout.strip() == "False False"


def test_provider_rejects_symlinked_source_root(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    adapter = provider.SealedV023SourceProvider(
        source_directory=link,
        source_manifest=link / "source-manifest.json",
        preflight_manifest_sha256="e" * 64,
        result_directory=real,
    )
    with pytest.raises(provider.V023SealedSourceProviderError, match="source directory"):
        adapter.provide(arm="INFORMED", student_seed=provider.V023_STUDENT_SEEDS[0])
