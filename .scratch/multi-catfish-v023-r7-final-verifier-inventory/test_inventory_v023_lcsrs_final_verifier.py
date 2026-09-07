"""Focused tests for the read-only R7 final-verifier inventory harness."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys

import pytest


sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location(
    "v023_r7_final_inventory_tested",
    HERE / "inventory_v023_lcsrs_final_verifier.py",
)
assert SPEC is not None and SPEC.loader is not None
inventory = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = inventory
SPEC.loader.exec_module(inventory)


def _load_module(path: Path, name: str):
    specification = importlib.util.spec_from_file_location(name, path)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


def test_ast_transform_records_target_raise_and_leaves_other_raises(
    tmp_path: Path,
) -> None:
    path = tmp_path / "synthetic_validator.py"
    path.write_text(
        "class SyntheticVerificationError(RuntimeError):\n"
        "    pass\n\n"
        "def target(flag):\n"
        "    if flag:\n"
        "        raise SyntheticVerificationError('recorded')\n"
        "    raise ValueError('unrelated')\n\n"
        "def untouched():\n"
        "    raise SyntheticVerificationError('untouched')\n",
        encoding="ascii",
    )
    module = _load_module(path, "inventory_synthetic_transform")
    recorder = inventory.Recorder()
    transformed = inventory._transform_function(
        module,
        "target",
        recorder,
        exception_name="SyntheticVerificationError",
        expected_sites=1,
    )

    with recorder.scope("source", "synthetic"):
        with pytest.raises(ValueError, match="unrelated"):
            module.target(True)
    with pytest.raises(module.SyntheticVerificationError, match="untouched"):
        module.untouched()

    assert transformed["raise_sites_rewritten"] == 1
    assert [item["message"] for item in recorder.findings] == ["recorded"]
    assert recorder.findings[0]["primary"] is True


def test_two_synthetic_shards_are_both_recorded(tmp_path: Path) -> None:
    path = tmp_path / "two_shards.py"
    path.write_text(
        "class SyntheticVerificationError(RuntimeError):\n"
        "    pass\n\n"
        "def validate(name):\n"
        "    raise SyntheticVerificationError('bad-' + name)\n",
        encoding="ascii",
    )
    module = _load_module(path, "inventory_synthetic_shards")
    recorder = inventory.Recorder()
    inventory._transform_function(
        module,
        "validate",
        recorder,
        exception_name="SyntheticVerificationError",
        expected_sites=1,
    )

    inventory._run_isolated(recorder, "composition", "shard-1", module.validate, "one")
    inventory._run_isolated(recorder, "composition", "shard-2", module.validate, "two")

    assert [(item["shard"], item["message"]) for item in recorder.findings] == [
        ("shard-1", "bad-one"),
        ("shard-2", "bad-two"),
    ]


def test_output_inside_run_root_or_already_existing_is_refused(
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run"
    run_root.mkdir()
    with pytest.raises(inventory.InventoryError, match="must not be inside"):
        inventory._validated_output(run_root, run_root / "inventory")

    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(inventory.InventoryError, match="already exists"):
        inventory._validated_output(run_root, existing)


def _fake_checkout(tmp_path: Path) -> tuple[Path, Path, Path]:
    checkout = tmp_path / "checkout"
    original = checkout / inventory.R7_RELATIVE / inventory.ORIGINAL_NAME
    adapter = checkout / inventory.R3_RELATIVE / inventory.R3_NAME
    original.parent.mkdir(parents=True)
    adapter.parent.mkdir(parents=True)
    original.write_bytes(b"frozen-original")
    adapter.write_bytes(b"frozen-adapter")
    return checkout, original, adapter


def test_both_frozen_hash_checks_refuse_drift(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    checkout, original, adapter = _fake_checkout(tmp_path)
    original_hash = hashlib.sha256(original.read_bytes()).hexdigest()
    adapter_hash = hashlib.sha256(adapter.read_bytes()).hexdigest()
    monkeypatch.setattr(inventory, "ORIGINAL_SHA256", original_hash)
    monkeypatch.setattr(inventory, "R3_SHA256", adapter_hash)
    inventory._verify_frozen_hashes(checkout)

    original.write_bytes(b"drifted-original")
    with pytest.raises(inventory.InventoryError, match="original final verifier digest drifted"):
        inventory._verify_frozen_hashes(checkout)
    original.write_bytes(b"frozen-original")
    adapter.write_bytes(b"drifted-adapter")
    with pytest.raises(inventory.InventoryError, match="R3 adapter digest drifted"):
        inventory._verify_frozen_hashes(checkout)


def test_frozen_verifier_bytes_unchanged_after_synthetic_run() -> None:
    frozen_path = REPO / inventory.R7_RELATIVE / inventory.ORIGINAL_NAME
    before = frozen_path.read_bytes()
    adapter, frozen = inventory._load_frozen(REPO)
    original_loader, _counts = adapter._install_domain_dispatch(frozen)
    original_pair = adapter._install_pair_profile_broadcast(frozen)
    recorder = inventory.Recorder()
    try:
        inventory._transform_function(
            frozen,
            "_source_raw_identity",
            recorder,
            expected_sites=2,
            module_label="frozen_final",
        )
        result = inventory._run_isolated(
            recorder, "source", "synthetic empty panel", frozen._source_raw_identity, (),
        )
    finally:
        frozen._load_npz = original_loader
        frozen._validate_pair_arrays = original_pair

    assert result == {}
    assert recorder.findings[0]["message"] == "source panel is not the exact eight worlds"
    assert frozen_path.read_bytes() == before
    assert hashlib.sha256(before).hexdigest() == inventory.ORIGINAL_SHA256


def test_adapter_r4_flag_loads_and_installs_on_top_of_r3() -> None:
    r4_path = (
        REPO
        / ".scratch/multi-catfish-v023-r7-domain-repair-r4"
        / "verify_v023_lcsrs_final_domain_repair_r4.py"
    )
    args = inventory.build_parser().parse_args(
        [
            "--run-root",
            "/tmp/run",
            "--checkout",
            str(REPO),
            "--output",
            "/tmp/inventory",
            "--adapter-r4",
            str(r4_path),
        ]
    )
    assert args.adapter_r4 == r4_path

    r3, frozen = inventory._load_frozen(REPO)
    frozen_loader = frozen._load_npz
    frozen_pair = frozen._validate_pair_arrays
    frozen_join = frozen._join_composition_source
    frozen_diagnostic = frozen._diagnostic_rows
    frozen_context = frozen._context_status
    r3_loader, _counts = r3._install_domain_dispatch(frozen)
    r3_pair = r3._install_pair_profile_broadcast(frozen)
    r4, digest = inventory._load_r4_adapter(args.adapter_r4)
    r4_join = r4_diagnostic = r4_context = None
    try:
        assert frozen._load_npz is not frozen_loader
        assert frozen._validate_pair_arrays is not frozen_pair
        r4_join, _pair_state = r4._install_pair_key_reconstruction(frozen)
        r4_diagnostic, _diagnostic_state = (
            r4._install_c2_diagnostic_normalization(frozen)
        )
        r4_context, _q2_state = r4._install_q2_delta_precision(frozen)
        assert frozen._join_composition_source is not frozen_join
        assert frozen._diagnostic_rows is not frozen_diagnostic
        assert frozen._context_status is not frozen_context
        assert digest == hashlib.sha256(r4_path.read_bytes()).hexdigest()
    finally:
        if r4_context is not None:
            frozen._context_status = r4_context
        if r4_diagnostic is not None:
            frozen._diagnostic_rows = r4_diagnostic
        if r4_join is not None:
            frozen._join_composition_source = r4_join
        frozen._load_npz = r3_loader
        frozen._validate_pair_arrays = r3_pair

    assert frozen._load_npz is frozen_loader
    assert frozen._validate_pair_arrays is frozen_pair
    assert frozen._join_composition_source is frozen_join
    assert frozen._diagnostic_rows is frozen_diagnostic
    assert frozen._context_status is frozen_context


def test_adapter_r4_flag_is_optional_and_rejects_symlinks(tmp_path: Path) -> None:
    args = inventory.build_parser().parse_args(
        [
            "--run-root",
            "/tmp/run",
            "--checkout",
            str(REPO),
            "--output",
            "/tmp/inventory",
        ]
    )
    assert args.adapter_r4 is None

    r4_path = (
        REPO
        / ".scratch/multi-catfish-v023-r7-domain-repair-r4"
        / "verify_v023_lcsrs_final_domain_repair_r4.py"
    )
    linked = tmp_path / "r4-adapter.py"
    linked.symlink_to(r4_path)
    with pytest.raises(inventory.InventoryError, match="must be a regular file"):
        inventory._load_r4_adapter(linked)
