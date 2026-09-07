"""Focused checks for the additive R7 final-verifier R3 repair."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import dis
from pathlib import Path
import sys
from types import ModuleType

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("v023_r7_domain_repair_test", HERE / "verify_v023_lcsrs_final_domain_repair.py")
assert SPEC is not None and SPEC.loader is not None
adapter = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = adapter
SPEC.loader.exec_module(adapter)
_FROZEN_VALIDATOR = adapter._load_original()._validate_pair_arrays


def test_pair_profile_broadcast_accepts_equivalent_draws() -> None:
    expected = np.arange(4 * 5, dtype=np.int64).reshape(1, 4, 5)
    actual = np.broadcast_to(expected, (32, 4, 5)).copy()

    assert adapter._broadcast_pair_profile_expected(actual, expected)


def test_pair_profile_broadcast_rejects_one_changed_draw() -> None:
    expected = np.arange(4 * 5, dtype=np.int64).reshape(1, 4, 5)
    actual = np.broadcast_to(expected, (32, 4, 5)).copy()
    actual[17, 2, 4] += 1

    assert not adapter._broadcast_pair_profile_expected(actual, expected)


def test_pair_profile_broadcast_keeps_other_validation_strict() -> None:
    expected = np.arange(4 * 5, dtype=np.int64).reshape(1, 4, 5)
    actual = np.broadcast_to(expected, (32, 4, 5)).copy()

    assert not adapter._broadcast_pair_profile_expected(actual, expected[:, :3, :])


def test_pair_profile_install_changes_only_the_target_call() -> None:
    frozen = adapter._load_original()
    original = frozen._validate_pair_arrays
    original_equal_calls = sum(
        instruction.opname == "LOAD_ATTR" and instruction.argval == "array_equal"
        for instruction in dis.get_instructions(original)
    )

    installed_original = adapter._install_pair_profile_broadcast(frozen)
    try:
        repaired = frozen._validate_pair_arrays
        repaired_equal_calls = sum(
            instruction.opname == "LOAD_ATTR" and instruction.argval == "array_equal"
            for instruction in dis.get_instructions(repaired)
        )
        broadcast_calls = sum(
            instruction.opname == "LOAD_ATTR" and instruction.argval == "broadcast_to"
            for instruction in dis.get_instructions(repaired)
        )
        assert installed_original is original
        assert repaired is not original
        assert repaired_equal_calls == original_equal_calls
        assert broadcast_calls == 1
    finally:
        frozen._validate_pair_arrays = installed_original
    assert frozen._validate_pair_arrays is original


def test_pair_profile_repair_runs_target_and_preserves_other_checks(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "fake_verifier.py"
    module_path.write_text(
        "import numpy as np\n"
        "def _validate_pair_arrays(profile_actions, expected_profiles, p, other, expected_other):\n"
        "    if not np.array_equal(other, expected_other):\n"
        "        raise ValueError('other check')\n"
        "    if not np.array_equal(profile_actions[p], expected_profiles[None, :, :]):\n"
        "        raise ValueError('pair check')\n",
        encoding="ascii",
    )
    spec = importlib.util.spec_from_file_location("fake_verifier", module_path)
    assert spec is not None and spec.loader is not None
    fake = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = fake
    spec.loader.exec_module(fake)
    original = fake._validate_pair_arrays
    adapter._install_pair_profile_broadcast(fake)
    expected = np.arange(4 * 5, dtype=np.int64).reshape(4, 5)
    actual = np.broadcast_to(expected[None, :, :], (32, 4, 5)).copy()
    try:
        fake._validate_pair_arrays(actual[None, ...], expected, 0, [1, 2], [1, 2])
        changed = actual.copy()
        changed[7, 3, 1] += 1
        with pytest.raises(ValueError, match="pair check"):
            fake._validate_pair_arrays(
                changed[None, ...], expected, 0, [1, 2], [1, 2]
            )
        with pytest.raises(ValueError, match="other check"):
            fake._validate_pair_arrays(
                actual[None, ...], expected, 0, [1, 2], [1, 3]
            )
    finally:
        fake._validate_pair_arrays = original
    assert fake._validate_pair_arrays is original


def _fake_original(loader):
    module = ModuleType("fake_frozen_final_verifier")
    module.V023_ARRAY_DOMAIN = adapter.COMPOSITION_ARRAY_DOMAIN
    module._load_npz = loader
    module._validate_pair_arrays = _FROZEN_VALIDATOR
    return module


def test_domain_dispatch_uses_each_authenticated_array_domain() -> None:
    seen: list[tuple[str, str]] = []

    def loader(_root, _binding, *, label):
        seen.append((label, fake.V023_ARRAY_DOMAIN))
        return {}

    fake = _fake_original(loader)
    original_loader, counts = adapter._install_domain_dispatch(fake)
    try:
        fake._load_npz(Path("."), {"schema": adapter.SOURCE_ARRAY_SCHEMA}, label="source")
        fake._load_npz(
            Path("."),
            {"array_domain": adapter.COMPOSITION_ARRAY_DOMAIN},
            label="composition",
        )
    finally:
        fake._load_npz = original_loader

    assert seen == [
        ("source", adapter.SOURCE_ARRAY_DOMAIN),
        ("composition", adapter.COMPOSITION_ARRAY_DOMAIN),
    ]
    assert counts == {"source": 1, "composition": 1}


@pytest.mark.parametrize(
    "binding",
    (
        {"schema": adapter.SOURCE_ARRAY_SCHEMA, "array_domain": adapter.COMPOSITION_ARRAY_DOMAIN},
        {"schema": adapter.SOURCE_ARRAY_SCHEMA, "array_domain": None},
        {"schema": "unknown", "array_domain": adapter.SOURCE_ARRAY_DOMAIN},
        {"array_domain": "unknown"},
        {"array_domain": adapter.COMPOSITION_ARRAY_DOMAIN, "schema": "composition"},
        {"schema": adapter.SOURCE_ARRAY_SCHEMA, "array_domain": "unknown"},
    ),
)
def test_domain_dispatch_rejects_every_other_schema_domain_pair(binding) -> None:
    fake = _fake_original(lambda *_args, **_kwargs: {})
    adapter._install_domain_dispatch(fake)
    with pytest.raises(adapter.V023R7DomainRepairError, match="unsupported NPZ schema/domain"):
        fake._load_npz(Path("."), binding, label="tampered")


def test_invalid_attempt_is_authenticated_before_repair(monkeypatch, tmp_path: Path) -> None:
    payload = {
        "status": "INVALID_RUN",
        "integrity_status": "INVALID",
        "scientific_claim": False,
        "test_split_opened": False,
        "episode_training": False,
        "no_scientific_token_before_integrity": True,
        "c3_decision": "INVALID_RUN",
        "errors": [adapter.EXPECTED_INVALID_ERROR],
    }
    path = tmp_path / "verification.json"
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii") + b"\n"
    path.write_bytes(encoded)
    digest = hashlib.sha256(encoded).hexdigest()
    monkeypatch.setattr(adapter, "INVALID_VERIFICATION_SHA256", digest)

    assert adapter._verify_invalid_attempt(path) == digest
    payload["errors"] = ["different error"]
    changed = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii") + b"\n"
    path.write_bytes(changed)
    monkeypatch.setattr(adapter, "INVALID_VERIFICATION_SHA256", hashlib.sha256(changed).hexdigest())
    with pytest.raises(adapter.V023R7DomainRepairError, match="invalid verification receipt drifted at errors"):
        adapter._verify_invalid_attempt(path)


def test_frozen_original_verifier_is_authenticated_and_loaded() -> None:
    assert adapter.ORIGINAL_VERIFIER.is_file()
    assert adapter._sha256(adapter.ORIGINAL_VERIFIER) == adapter.ORIGINAL_VERIFIER_SHA256
    frozen = adapter._load_original()
    assert callable(frozen.verify_v023_final_gate)
    assert frozen.V023_ARRAY_DOMAIN == adapter.COMPOSITION_ARRAY_DOMAIN


def test_original_sibling_import_path_is_scoped_and_restored(tmp_path: Path) -> None:
    package = tmp_path / "frozen-verifier-package"
    package.mkdir()
    original = list(sys.path)

    with adapter._temporary_import_path(package):
        assert sys.path[0] == str(package.resolve())

    assert sys.path == original


def test_run_forwards_exact_panel_and_writes_additive_receipts(
    monkeypatch, tmp_path: Path
) -> None:
    source = [tmp_path / f"source-{index}.json" for index in range(8)]
    fit = [tmp_path / f"fit-{index}.json" for index in range(48)]
    composition = [tmp_path / f"composition-{index}.json" for index in range(48)]
    contract = tmp_path / "contract.md"
    contract.write_text("frozen contract", encoding="utf-8")
    output = tmp_path / "corrected-verification.json"
    receipt = tmp_path / "repair-receipt.json"
    events: list[str] = []
    calls: dict[str, object] = {}

    def loader(_root, _binding, *, label):
        calls.setdefault("loads", []).append((label, fake.V023_ARRAY_DOMAIN))
        return {}

    fake = _fake_original(loader)

    def verify(**kwargs):
        events.append("verify")
        calls["kwargs"] = kwargs
        for index, path in enumerate(kwargs["source_paths"]):
            fake._load_npz(path.parent, {"schema": adapter.SOURCE_ARRAY_SCHEMA}, label=f"source-{index}")
        for index, path in enumerate(kwargs["composition_paths"]):
            fake._load_npz(
                path.parent,
                {"array_domain": adapter.COMPOSITION_ARRAY_DOMAIN},
                label=f"composition-{index}",
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

    fake.verify_v023_final_gate = verify
    monkeypatch.setattr(adapter, "_verify_invalid_attempt", lambda _path: events.append("invalid") or "a" * 64)
    monkeypatch.setattr(adapter, "_load_original", lambda: events.append("load") or fake)

    result = adapter.run(
        source_paths=source,
        fit_paths=fit,
        composition_paths=composition,
        source_manifest=tmp_path / "source-manifest.json",
        launch_manifest=tmp_path / "launch-manifest.json",
        launch_manifest_digest=tmp_path / "launch-manifest.sha256",
        invalid_verification=tmp_path / "invalid.json",
        contract=contract,
        output=output,
        receipt=receipt,
    )

    assert events == ["invalid", "load", "verify"]
    assert calls["kwargs"]["source_paths"] == tuple(source)
    assert calls["kwargs"]["fit_paths"] == tuple(fit)
    assert calls["kwargs"]["composition_paths"] == tuple(composition)
    assert (
        calls["kwargs"]["expected_preflight_manifest_sha256"]
        == adapter.EXPECTED_PREFLIGHT_MANIFEST_SHA256
    )
    assert [domain for _label, domain in calls["loads"][:8]] == [adapter.SOURCE_ARRAY_DOMAIN] * 8
    assert [domain for _label, domain in calls["loads"][8:]] == [adapter.COMPOSITION_ARRAY_DOMAIN] * 48
    assert result["status"] == adapter.STATUS
    assert result["claim_ceiling"] == adapter.CLAIM_CEILING
    assert result["test_split_opened"] is False
    assert result["episode_training"] is False
    assert result["learner_update"] is False
    assert result["scientific_claim"] is False
    assert json.loads(output.read_text(encoding="ascii"))["status"] == "PASS_FINAL_INTEGRITY"
    assert json.loads(receipt.read_text(encoding="ascii"))["status"] == adapter.STATUS
    assert fake._load_npz is loader
    assert fake._validate_pair_arrays is _FROZEN_VALIDATOR
    assert fake.V023_ARRAY_DOMAIN == adapter.COMPOSITION_ARRAY_DOMAIN


def test_invalid_result_errors_precede_dispatch_count_assertion(
    monkeypatch, tmp_path: Path
) -> None:
    source = [tmp_path / f"source-{index}.json" for index in range(8)]
    fit = [tmp_path / f"fit-{index}.json" for index in range(48)]
    composition = [tmp_path / f"composition-{index}.json" for index in range(48)]
    contract = tmp_path / "contract.md"
    contract.write_text("frozen contract", encoding="utf-8")
    output = tmp_path / "corrected-verification.json"
    receipt = tmp_path / "repair-receipt.json"
    fake = _fake_original(lambda *_args, **_kwargs: {})

    def verify(**_kwargs):
        return {
            "status": "INVALID_RUN",
            "integrity_status": "INVALID",
            "errors": ["composition pair profile actions disagree"],
        }

    fake.verify_v023_final_gate = verify
    monkeypatch.setattr(adapter, "_verify_invalid_attempt", lambda _path: "a" * 64)
    monkeypatch.setattr(adapter, "_load_original", lambda: fake)

    with pytest.raises(
        adapter.V023R7DomainRepairError,
        match="INVALID_RUN before dispatch-count assertion: composition pair profile actions disagree",
    ):
        adapter.run(
            source_paths=source,
            fit_paths=fit,
            composition_paths=composition,
            source_manifest=tmp_path / "source-manifest.json",
            launch_manifest=tmp_path / "launch-manifest.json",
            launch_manifest_digest=tmp_path / "launch-manifest.sha256",
            invalid_verification=tmp_path / "invalid.json",
            contract=contract,
            output=output,
            receipt=receipt,
        )

    assert not output.exists()
    assert not receipt.exists()
    assert fake._validate_pair_arrays is _FROZEN_VALIDATOR


def test_write_once_preserves_existing_outputs_and_symlink_targets(tmp_path: Path) -> None:
    existing = tmp_path / "existing.json"
    existing.write_bytes(b"original")
    with pytest.raises(adapter.V023R7DomainRepairError, match="refusing to overwrite"):
        adapter._write_once(existing, b"replacement")
    assert existing.read_bytes() == b"original"

    target = tmp_path / "target.json"
    target.write_bytes(b"target")
    link = tmp_path / "link.json"
    link.symlink_to(target)
    with pytest.raises(adapter.V023R7DomainRepairError, match="refusing to overwrite"):
        adapter._write_once(link, b"replacement")
    assert target.read_bytes() == b"target"
