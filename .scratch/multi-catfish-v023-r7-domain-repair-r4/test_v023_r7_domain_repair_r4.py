"""Focused checks for the additive R7 final-verifier R4 repair."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
FIXTURES = REPO / ".scratch/multi-catfish-v023-r7-domain-repair-r4-fixtures"
SPEC = importlib.util.spec_from_file_location(
    "v023_r7_domain_repair_r4_tested",
    HERE / "verify_v023_lcsrs_final_domain_repair_r4.py",
)
assert SPEC is not None and SPEC.loader is not None
adapter = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = adapter
SPEC.loader.exec_module(adapter)
_FROZEN_VALIDATOR = adapter._load_original()._validate_pair_arrays


def _fixture_inputs() -> tuple[dict[str, object], dict[str, np.ndarray]]:
    payload = json.loads(
        (FIXTURES / "r7-world-2026121801-anchor0.json").read_text(encoding="ascii")
    )
    with np.load(
        FIXTURES / "r7-world-2026121801-anchor0.npz", allow_pickle=False
    ) as archive:
        arrays = {name: np.array(archive[name], copy=True, order="C") for name in archive.files}
    return payload, arrays


def _fixture_reconstruction(
    payload: dict[str, object], arrays: dict[str, np.ndarray]
) -> adapter.PairKeyReconstruction:
    selected = np.flatnonzero(arrays["pair_anchor_index"] == 0)
    return adapter.reconstruct_pair_keys_from_source(
        topology_pairs_by_anchor=[payload["topology_pairs"]],
        pair_anchor_index=np.zeros(selected.size, dtype=np.int64),
        pair_user_ids=arrays["pair_user_ids"][selected],
        pair_action_ids=arrays["pair_action_ids"][selected],
        pair_id=arrays["pair_id"][selected],
        physical_keys=arrays["physical_keys_anchor0"][None, ...],
        reference_actions=arrays["reference_actions_anchor0"][None, ...],
        action_mask=arrays["action_mask_anchor0"][None, ...],
    )


def test_real_fixture_reconstructs_both_derivations_and_composition_rows() -> None:
    payload, arrays = _fixture_inputs()
    reconstruction = _fixture_reconstruction(payload, arrays)
    selected = arrays["comp_pair_anchor_index"] == 0

    assert reconstruction.json_source_keys.shape == (17, 2)
    assert reconstruction.json_destination_keys.shape == (17, 2, 2)
    assert reconstruction.json_source_keys.dtype == np.dtype(np.int64)
    assert reconstruction.json_destination_keys.dtype == np.dtype(np.int64)
    assert reconstruction.json_source_keys.flags.c_contiguous
    assert reconstruction.json_destination_keys.flags.c_contiguous
    assert np.array_equal(
        reconstruction.json_source_keys, reconstruction.npz_source_keys
    )
    assert np.array_equal(
        reconstruction.json_destination_keys, reconstruction.npz_destination_keys
    )
    assert np.array_equal(
        reconstruction.pair_source_key, arrays["comp_pair_source_key"][selected]
    )
    assert np.array_equal(
        reconstruction.pair_destination_keys,
        arrays["comp_pair_destination_keys"][selected],
    )


def test_topology_destination_mutation_fails_closed() -> None:
    payload, arrays = _fixture_inputs()
    changed = copy.deepcopy(payload)
    changed["topology_pairs"][0]["destination_keys"][0][0] += 1

    with pytest.raises(
        adapter.V023R7DomainRepairR4Error,
        match="source JSON/NPZ pair-key derivations disagree",
    ):
        _fixture_reconstruction(changed, arrays)


def test_source_physical_key_mutation_fails_closed() -> None:
    payload, arrays = _fixture_inputs()
    first = payload["topology_pairs"][0]
    user = int(first["member_users"][0])
    action = int(first["designated_actions"][0])
    arrays["physical_keys_anchor0"][user, action, 0] += 1

    with pytest.raises(
        adapter.V023R7DomainRepairR4Error,
        match="source JSON/NPZ pair-key derivations disagree",
    ):
        _fixture_reconstruction(payload, arrays)


def test_zero_pair_shapes_are_explicit_int64_c_order() -> None:
    reconstruction = adapter.reconstruct_pair_keys_from_source(
        topology_pairs_by_anchor=[[]],
        pair_anchor_index=np.zeros((0,), dtype=np.int64),
        pair_user_ids=np.zeros((0, 2), dtype=np.int64),
        pair_action_ids=np.zeros((0, 2), dtype=np.int64),
        pair_id=np.zeros((0,), dtype="S256"),
        physical_keys=np.zeros((1, 1, 1, 2), dtype=np.int64),
        reference_actions=np.zeros((1, 1), dtype=np.int64),
        action_mask=np.ones((1, 1, 1), dtype=np.bool_),
    )

    for value, shape in (
        (reconstruction.json_source_keys, (0, 2)),
        (reconstruction.npz_source_keys, (0, 2)),
        (reconstruction.json_destination_keys, (0, 2, 2)),
        (reconstruction.npz_destination_keys, (0, 2, 2)),
    ):
        assert value.shape == shape
        assert value.dtype == np.dtype(np.int64)
        assert value.flags.c_contiguous


def _fixture_diagnostics() -> list[dict[str, object]]:
    payload, _arrays = _fixture_inputs()
    diagnostics = copy.deepcopy(payload["c2_diagnostic_first2_truncated"])
    for item in diagnostics:
        assert item.pop("rows_total") == len(item["rows"])
    return diagnostics


def test_real_fixture_c2_normalization_preserves_rows_and_provenance() -> None:
    diagnostics = _fixture_diagnostics()
    original_rows = [row for item in diagnostics for row in item["rows"]]
    normalized, counts = adapter.normalize_c2_diagnostic_list(
        diagnostics, label="real fixture anchor 0"
    )

    assert normalized["rows"] == original_rows
    assert len(normalized["rows"]) == 2
    assert counts == {
        "pair_objects": 2,
        "rows": 2,
        "exposure_count": 4,
        "nontrivial_count": 4,
    }
    assert normalized["exposure_count"] == 4
    assert normalized["nontrivial_count"] == 4
    assert normalized["r4_normalization_schema"] == "c2-per-pair-list-to-object-v1"
    provenance = normalized["r4_per_pair_provenance"]
    assert [item["pair_offset"] for item in provenance] == [0, 1]
    assert [item["row_offset"] for item in provenance] == [0, 1]
    assert [item["row_count"] for item in provenance] == [1, 1]
    for index, item in enumerate(provenance):
        for name in (*adapter.C2_SHARED_FIELDS, *adapter.C2_COUNT_FIELDS):
            assert item[name] == diagnostics[index][name]


def test_mapping_diagnostic_passes_through_unchanged() -> None:
    fake = ModuleType("fake_c2_diagnostic_accessor")

    def diagnostic_rows(diag, *, label):
        assert label == "mapping"
        return diag, diag["rows"]

    fake._diagnostic_rows = diagnostic_rows
    original, state = adapter._install_c2_diagnostic_normalization(fake)
    mapping = {"rows": [{"preserved": True}], "custom": object()}
    try:
        returned, rows = fake._diagnostic_rows(mapping, label="mapping")
    finally:
        fake._diagnostic_rows = original

    assert returned is mapping
    assert rows is mapping["rows"]
    assert state["mapping_passthrough"] == 1
    assert state["list_containers"] == 0
    assert fake._diagnostic_rows is diagnostic_rows


def test_empty_c2_list_fails_without_inventing_provenance() -> None:
    with pytest.raises(
        adapter.V023R7DomainRepairR4Error,
        match="required pair-level provenance is unavailable",
    ):
        adapter.normalize_c2_diagnostic_list([], label="empty anchor")


def _precision_module() -> tuple[ModuleType, object]:
    fake = ModuleType("fake_q2_delta_precision_verifier")
    fake.np = np

    def _context_status(q2, index, users_row, actions_row, expected_refs):
        expected_q2_delta = np.asarray(
            [
                q2[index, user, action] - q2[index, user, reference]
                for user, action, reference in zip(
                    users_row, actions_row, expected_refs, strict=True
                )
            ],
            dtype=np.float64,
        )
        return expected_q2_delta

    fake._context_status = _context_status
    return fake, _context_status


def _precision_operands() -> tuple[np.ndarray, np.ndarray]:
    widened = np.asarray(
        [[[np.float32(0.1), np.float32(0.3)]]], dtype=np.float64
    )
    writer_delta = np.asarray(
        [float(np.float32(0.3) - np.float32(0.1))], dtype=np.float64
    )
    return widened, writer_delta


def test_q2_delta_original_rejects_writer_precision_and_r4_accepts() -> None:
    frozen = adapter._load_original()
    fake, original = _precision_module()
    q2, writer_delta = _precision_operands()
    original_expected = original(q2, 0, (0,), (1,), (0,))

    assert abs(float(writer_delta[0] - original_expected[0])) > 1e-12
    with pytest.raises(frozen.V023FinalVerificationError, match="q2 delta differs"):
        frozen._assert_numeric_equal(
            writer_delta, original_expected, label="synthetic C2 q2 delta"
        )

    installed_original, state = adapter._install_q2_delta_precision(fake)
    try:
        corrected_expected = fake._context_status(q2, 0, (0,), (1,), (0,))
        frozen._assert_numeric_equal(
            writer_delta, corrected_expected, label="synthetic C2 q2 delta"
        )
    finally:
        fake._context_status = installed_original

    assert installed_original is original
    assert state == {"rows_checked": 1, "member_deltas_checked": 1}


def test_q2_delta_corrected_path_rejects_genuinely_different_serialized_value() -> None:
    frozen = adapter._load_original()
    fake, original = _precision_module()
    q2, writer_delta = _precision_operands()
    changed = np.asarray(
        [float(np.float32(writer_delta[0]) + np.float32(1e-6))],
        dtype=np.float64,
    )

    installed_original, _state = adapter._install_q2_delta_precision(fake)
    try:
        corrected_expected = fake._context_status(q2, 0, (0,), (1,), (0,))
        with pytest.raises(
            frozen.V023FinalVerificationError, match="q2 delta differs"
        ):
            frozen._assert_numeric_equal(
                changed, corrected_expected, label="synthetic C2 q2 delta"
            )
    finally:
        fake._context_status = installed_original

    assert fake._context_status is original


def _synthetic_source(world: int) -> tuple[dict[str, object], dict[str, np.ndarray]]:
    anchor_count, users, actions = 9, 2, 2
    keys = np.zeros((anchor_count, users, actions, 2), dtype=np.int64)
    references = np.zeros((anchor_count, users), dtype=np.int64)
    masks = np.ones((anchor_count, users, actions), dtype=np.bool_)
    pair_ids: list[bytes] = []
    anchors: list[dict[str, object]] = []
    topology_digests: list[bytes] = []
    for anchor in range(anchor_count):
        source_key = [world + anchor, 10 + anchor]
        keys[anchor, :, 0] = source_key
        keys[anchor, 0, 1] = [world + 100 + anchor, 20]
        keys[anchor, 1, 1] = [world + 100 + anchor, 21]
        pair_name = f"w{world}:a{anchor}:u0-1".encode("ascii")
        pair_ids.append(pair_name)
        topology_digest = f"{world + anchor:064x}".encode("ascii")
        topology_digests.append(topology_digest)
        anchors.append(
            {
                "phase": anchor + 1,
                "topology": {
                    "content_digest": topology_digest.decode("ascii"),
                    "pairs": [
                        {
                            "pair_id": pair_name.decode("ascii"),
                            "member_users": [0, 1],
                            "designated_actions": [1, 1],
                            "source_key": source_key,
                            "destination_keys": [
                                [world + 100 + anchor, 20],
                                [world + 100 + anchor, 21],
                            ],
                        }
                    ],
                },
            }
        )
    arrays = {
        "pair_anchor_index": np.arange(anchor_count, dtype=np.int64),
        "pair_user_ids": np.tile(np.asarray([[0, 1]], dtype=np.int64), (anchor_count, 1)),
        "pair_action_ids": np.tile(np.asarray([[1, 1]], dtype=np.int64), (anchor_count, 1)),
        "pair_id": np.asarray(pair_ids, dtype="S256"),
        "physical_keys": keys,
        "reference_actions": references,
        "action_mask": masks,
        "anchor_topology_content_digest": np.asarray(topology_digests, dtype="S64"),
    }
    return {"world": world, "anchors": anchors}, arrays


def _synthetic_original(*, fail: bool = False):
    fake = ModuleType("fake_frozen_r4_verifier")
    fake.V023_ARRAY_DOMAIN = adapter.COMPOSITION_ARRAY_DOMAIN
    fake.np = np
    sources = {
        world: _synthetic_source(world)
        for world in range(2026121801, 2026121809)
    }
    observations = {"q2_precision_installed_during_verifier_call": False}

    def loader(_root, _binding, *, label):
        if label.startswith("source-"):
            index = int(label.removeprefix("source-"))
            return sources[2026121801 + index][1]
        return {}

    def join(_shard, source):
        payload, arrays = source
        assert "pair_source_key" in arrays
        assert "pair_destination_keys" in arrays
        assert "pair_source_key" not in sources[payload["world"]][1]
        assert "pair_destination_keys" not in sources[payload["world"]][1]
        return None

    def diagnostic_rows(diag, *, label):
        del label
        if not isinstance(diag, dict) or not isinstance(diag.get("rows"), list):
            raise ValueError("diagnostic must be an object")
        return diag, diag["rows"]

    def _context_status(q2, index, users_row, actions_row, expected_refs):
        expected_q2_delta = np.asarray(
            [
                q2[index, user, action] - q2[index, user, reference]
                for user, action, reference in zip(
                    users_row, actions_row, expected_refs, strict=True
                )
            ],
            dtype=np.float64,
        )
        return expected_q2_delta

    fake._load_npz = loader
    fake._validate_pair_arrays = _FROZEN_VALIDATOR
    fake._join_composition_source = join
    fake._diagnostic_rows = diagnostic_rows
    fake._context_status = _context_status

    diagnostic = {
        "diagnostic_lambda_bits_per_j_hex": "0x1.c3c0a7b6b86d3p+26",
        "exposure_count": 2,
        "kind": "C2_REPRICED_OPS3_CONTEXT_DIAGNOSTIC",
        "nontrivial_count": 1,
        "rows": [{"synthetic": True}],
        "runtime_default_lambda_used_for_target": False,
        "target_filter_applied": False,
        "target_free_inference": True,
    }

    def verify_v023_final_gate(**kwargs):
        if fail:
            raise RuntimeError("synthetic verifier failure")
        observations["q2_precision_installed_during_verifier_call"] = (
            fake._context_status is not _context_status
        )
        for index, path in enumerate(kwargs["source_paths"]):
            fake._load_npz(
                path.parent,
                {"schema": adapter.SOURCE_ARRAY_SCHEMA},
                label=f"source-{index}",
            )
        for index, path in enumerate(kwargs["composition_paths"]):
            fake._load_npz(
                path.parent,
                {"array_domain": adapter.COMPOSITION_ARRAY_DOMAIN},
                label=f"composition-{index}",
            )
        for world in range(2026121801, 2026121809):
            source = sources[world]
            for application in range(6):
                fake._join_composition_source((world, application), source)
            for anchor in range(9):
                fake._diagnostic_rows(
                    [copy.deepcopy(diagnostic)], label=f"world={world},phase={anchor + 1}"
                )
                fake._context_status(
                    np.asarray(
                        [
                            [
                                [np.float32(0.1), np.float32(0.3)],
                                [np.float32(0.1), np.float32(0.3)],
                            ]
                        ],
                        dtype=np.float64,
                    ),
                    0,
                    (0, 1),
                    (1, 1),
                    (0, 0),
                )
        return {
            "status": "PASS_FINAL_INTEGRITY",
            "integrity_status": "VERIFIED",
            "source_count": 8,
            "fit_count": 48,
            "composition_count": 48,
            "scientific_claim": False,
            "test_split_opened": False,
            "episode_training": False,
        }

    fake.verify_v023_final_gate = verify_v023_final_gate
    originals = {
        "loader": loader,
        "validator": _FROZEN_VALIDATOR,
        "join": join,
        "diagnostic": diagnostic_rows,
        "context": _context_status,
        "observations": observations,
    }
    return fake, originals


def _run_synthetic(monkeypatch, tmp_path: Path, *, fail: bool = False):
    fake, originals = _synthetic_original(fail=fail)
    monkeypatch.setattr(adapter, "_load_r3_adapter", lambda: adapter.R3)
    monkeypatch.setattr(adapter, "_load_original", lambda: fake)
    monkeypatch.setattr(
        adapter.R3, "_verify_invalid_attempt", lambda _path: "a" * 64
    )
    contract = tmp_path / "contract.md"
    contract.write_text("synthetic contract", encoding="ascii")
    kwargs = {
        "source_paths": [tmp_path / f"source-{index}.json" for index in range(8)],
        "fit_paths": [tmp_path / f"fit-{index}.json" for index in range(48)],
        "composition_paths": [
            tmp_path / f"composition-{index}.json" for index in range(48)
        ],
        "source_manifest": tmp_path / "source-manifest.json",
        "launch_manifest": tmp_path / "launch-manifest.json",
        "launch_manifest_digest": tmp_path / "launch-manifest.sha256",
        "invalid_verification": tmp_path / "invalid.json",
        "contract": contract,
        "output": tmp_path / "corrected.json",
        "receipt": tmp_path / "receipt.json",
    }
    return fake, originals, kwargs


def test_synthetic_run_restores_all_hooks_and_frozen_files(
    monkeypatch, tmp_path: Path
) -> None:
    frozen_paths = (
        adapter.ORIGINAL_VERIFIER,
        adapter.R3_ADAPTER,
    )
    before = {path: path.read_bytes() for path in frozen_paths}
    original_path = list(sys.path)
    fake, originals, kwargs = _run_synthetic(monkeypatch, tmp_path)

    receipt = adapter.run(**kwargs)

    assert receipt["status"] == adapter.STATUS
    assert receipt["pair_key_reconstruction"]["source_pair_rows"] == 72
    assert receipt["pair_key_reconstruction"]["join_applications"] == 48
    assert receipt["c2_diagnostic_normalization"]["rows"] == 72
    assert receipt["c2_diagnostic_normalization"]["list_containers"] == 72
    assert receipt["q2_delta_precision"] == {
        "expected_computed_in": "float32-as-writer",
        "member_deltas_checked": 144,
        "rows_checked": 72,
        "scoped_target": "_context_status expected_q2_delta",
    }
    assert fake._load_npz is originals["loader"]
    assert fake._validate_pair_arrays is originals["validator"]
    assert fake._join_composition_source is originals["join"]
    assert fake._diagnostic_rows is originals["diagnostic"]
    assert fake._context_status is originals["context"]
    assert fake.V023_ARRAY_DOMAIN == adapter.COMPOSITION_ARRAY_DOMAIN
    assert sys.path == original_path
    for path, data in before.items():
        assert path.read_bytes() == data
        assert hashlib.sha256(data).hexdigest() == adapter._sha256(path)


def test_synthetic_failure_restores_all_hooks(monkeypatch, tmp_path: Path) -> None:
    original_path = list(sys.path)
    fake, originals, kwargs = _run_synthetic(monkeypatch, tmp_path, fail=True)

    with pytest.raises(RuntimeError, match="synthetic verifier failure"):
        adapter.run(**kwargs)

    assert fake._load_npz is originals["loader"]
    assert fake._validate_pair_arrays is originals["validator"]
    assert fake._join_composition_source is originals["join"]
    assert fake._diagnostic_rows is originals["diagnostic"]
    assert fake._context_status is originals["context"]
    assert fake.V023_ARRAY_DOMAIN == adapter.COMPOSITION_ARRAY_DOMAIN
    assert sys.path == original_path
    assert not kwargs["output"].exists()
    assert not kwargs["receipt"].exists()


def test_q2_precision_correction_is_scoped_to_verifier_call(
    monkeypatch, tmp_path: Path
) -> None:
    fake, originals, kwargs = _run_synthetic(monkeypatch, tmp_path)
    assert fake._context_status is originals["context"]

    receipt = adapter.run(**kwargs)

    assert originals["observations"]["q2_precision_installed_during_verifier_call"]
    assert receipt["q2_delta_precision"]["rows_checked"] == 72
    assert fake._context_status is originals["context"]


def test_q2_precision_install_leaves_frozen_verifier_bytes_unchanged() -> None:
    frozen_path = adapter.ORIGINAL_VERIFIER
    before = frozen_path.read_bytes()
    frozen = adapter._load_original()
    original = frozen._context_status

    installed_original, _state = adapter._install_q2_delta_precision(frozen)
    try:
        assert installed_original is original
        assert frozen._context_status is not original
    finally:
        frozen._context_status = installed_original

    assert frozen._context_status is original
    assert frozen_path.read_bytes() == before
    assert hashlib.sha256(before).hexdigest() == adapter.ORIGINAL_VERIFIER_SHA256


def test_write_once_refuses_regular_files_and_symlinks(tmp_path: Path) -> None:
    existing = tmp_path / "existing.json"
    existing.write_bytes(b"original")
    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        adapter._write_once(existing, b"replacement")
    assert existing.read_bytes() == b"original"

    target = tmp_path / "target.json"
    target.write_bytes(b"target")
    link = tmp_path / "link.json"
    link.symlink_to(target)
    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        adapter._write_once(link, b"replacement")
    assert target.read_bytes() == b"target"


def test_launcher_syntax_compile_and_no_contact_dry_run(tmp_path: Path) -> None:
    launcher = HERE / "sync_launch_v023_r7_domain_repair_server_r4.sh"
    subprocess.run(["bash", "-n", str(launcher)], check=True)
    environment = dict(os.environ)
    environment["PYTHONPYCACHEPREFIX"] = str(tmp_path / "pycache")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "py_compile",
            str(HERE / "verify_v023_lcsrs_final_domain_repair_r4.py"),
            str(HERE / "run_v023_r7_domain_repair_server_r4.py"),
        ],
        check=True,
        env=environment,
    )
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    marker = tmp_path / "network-contact"
    for command in ("ssh", "rsync"):
        executable = fake_bin / command
        executable.write_text(
            "#!/usr/bin/env bash\nprintf contacted > \"$V023_CONTACT_MARKER\"\nexit 99\n",
            encoding="ascii",
        )
        executable.chmod(0o755)
    environment["PATH"] = f"{fake_bin}:{environment['PATH']}"
    environment["V023_CONTACT_MARKER"] = str(marker)
    completed = subprocess.run(
        ["bash", str(launcher), "--dry-run"],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert completed.returncode == 0, completed.stderr
    assert "V023_R7_DOMAIN_REPAIR_R4_DRY_RUN_PASS" in completed.stdout
    assert not marker.exists()
