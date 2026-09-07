"""Focused checks for the additive R7 final-verifier domain repair."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("v023_r7_domain_repair_test", HERE / "verify_v023_lcsrs_final_domain_repair.py")
assert SPEC is not None and SPEC.loader is not None
adapter = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = adapter
SPEC.loader.exec_module(adapter)


def _fake_original(loader):
    module = ModuleType("fake_frozen_final_verifier")
    module.V023_ARRAY_DOMAIN = adapter.COMPOSITION_ARRAY_DOMAIN
    module._load_npz = loader
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
    assert fake.V023_ARRAY_DOMAIN == adapter.COMPOSITION_ARRAY_DOMAIN


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
