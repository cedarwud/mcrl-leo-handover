"""W-203 -- source-stage coverage decision before any fit worker starts."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


REPO = Path(__file__).resolve().parents[1]
OBS = REPO / ".scratch" / "multi-catfish-v023-c3-observability"
SOURCE_STAGE_PATH = OBS / "verify_v023_lcsrs_source_stage.py"
CONTRACT_SHA256 = "1e69a2e7242198adce97e6357e4205a29fe6d1fb06a48dc7e1839a675529811a"
PREFLIGHT = "a" * 64
WORLDS = list(range(2026121705, 2026121713))


def _load_module():
    spec = importlib.util.spec_from_file_location("test_w203_source_stage", SOURCE_STAGE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _panel(*, coverage: bool) -> dict[str, object]:
    return {
        "status": "VERIFIED_SOURCE_PANEL_NUMERICS",
        "contract_sha256": CONTRACT_SHA256,
        "preflight_manifest_sha256": PREFLIGHT,
        "worlds": WORLDS,
        "predicates": {"pair_coverage": coverage},
        "pair_count": 24 if coverage else 23,
    }


def test_source_stage_returns_exact_insufficient_pairs_token() -> None:
    module = _load_module()
    assert module.classify_source_panel(_panel(coverage=False)) == "INSUFFICIENT_PAIRS"


def test_source_stage_ready_token_does_not_claim_training() -> None:
    module = _load_module()
    assert module.classify_source_panel(_panel(coverage=True)) == "SOURCE_STAGE_READY_FOR_FIT"
    receipt = module.build_source_stage_receipt(_panel(coverage=True), preflight_sha256=PREFLIGHT)
    assert receipt["decision"] == "SOURCE_STAGE_READY_FOR_FIT"
    assert receipt["fit_launched"] is False
    assert receipt["learner_update"] is False
    assert receipt["episode_training"] is False
    assert receipt["test_split_opened"] is False


def test_source_stage_insufficient_receipt_is_canonical_and_sealed() -> None:
    module = _load_module()
    receipt = module.build_source_stage_receipt(_panel(coverage=False), preflight_sha256=PREFLIGHT)
    assert receipt["decision"] == "INSUFFICIENT_PAIRS"
    raw = module._canonical_bytes(receipt)
    assert json.loads(raw.decode("ascii")) == receipt
    unsigned = dict(receipt)
    seal = unsigned.pop("receipt_sha256")
    assert seal == module.canonical_sha256(unsigned)


def test_source_stage_rejects_contract_or_preflight_mismatch() -> None:
    module = _load_module()
    bad_contract = _panel(coverage=False)
    bad_contract["contract_sha256"] = "b" * 64
    with pytest.raises(module.V023SourceStageError, match="contract digest"):
        module.build_source_stage_receipt(bad_contract, preflight_sha256=PREFLIGHT)
    with pytest.raises(module.V023SourceStageError, match="preflight digest"):
        module.build_source_stage_receipt(_panel(coverage=False), preflight_sha256="c" * 64)


def test_cached_receipt_is_recomputed_not_trusted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_module()
    panel = _panel(coverage=False)
    monkeypatch.setattr(
        module,
        "_load_scientific",
        lambda: SimpleNamespace(verify_source_panel_science=lambda _paths: panel),
    )
    receipt = module.build_source_stage_receipt(panel, preflight_sha256=PREFLIGHT)
    path = tmp_path / "source-stage.json"
    path.write_bytes(module._canonical_bytes(receipt))
    sources = [tmp_path / f"source-{world}.json" for world in WORLDS]
    assert module.verify_existing_source_stage(
        sources,
        preflight_sha256=PREFLIGHT,
        receipt_path=path,
    ) == path.resolve()

    tampered = dict(receipt)
    tampered["decision"] = "SOURCE_STAGE_READY_FOR_FIT"
    path.write_bytes(module._canonical_bytes(tampered))
    with pytest.raises(module.V023SourceStageError, match="recomputed source numerics"):
        module.verify_existing_source_stage(
            sources,
            preflight_sha256=PREFLIGHT,
            receipt_path=path,
        )
