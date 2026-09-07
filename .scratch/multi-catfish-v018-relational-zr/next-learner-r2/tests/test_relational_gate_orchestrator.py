"""Pure orchestration tests; no simulator, learner update, or TEST split."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace


R2_ROOT = Path(__file__).resolve().parents[1]
REPO = R2_ROOT.parents[2]
sys.path.insert(0, str(R2_ROOT))
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(R2_ROOT.parent / "next-learner-draft"))

import relational_gate_orchestrator as gate  # noqa: E402


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def test_gate_orchestrator_fixes_config_before_report_and_verifies(
    tmp_path: Path, monkeypatch
) -> None:
    contract = tmp_path / "contract.md"
    contract.write_text("Status: `FROZEN_BEFORE_OUTCOME`\n", encoding="utf-8")
    manifest = tmp_path / "code-manifest.sha256"
    manifest.write_text("synthetic manifest\n", encoding="ascii")
    learner_config = tmp_path / "learner-config.json"
    learner_config.write_bytes(_canonical({"synthetic": True}))
    contract_sha = hashlib.sha256(contract.read_bytes()).hexdigest()
    manifest_sha = hashlib.sha256(manifest.read_bytes()).hexdigest()
    lineages = (2026092101, 2026092102, 2026092103)
    seeds = (2026120511, 2026120512, 2026120513)
    config = SimpleNamespace(
        contract_sha256=contract_sha,
        code_manifest_sha256=manifest_sha,
        train_worlds=(2026120501, 2026120502, 2026120503, 2026120504),
        validation_worlds=(2026120505, 2026120506, 2026120507),
        initialization_lineages=tuple(zip(seeds, lineages, strict=True)),
        initialization_seeds=seeds,
        q1_checkpoint_sha256_by_lineage=tuple(
            (lineage, "a" * 64) for lineage in lineages
        ),
        q2_checkpoint_sha256_by_lineage=tuple(
            (lineage, "b" * 64) for lineage in lineages
        ),
        kappa_bits=float.fromhex("0x1.2cea89d260f2ap+33"),
    )
    panel = SimpleNamespace(source_sha256="c" * 64)
    calls: list[str] = []

    monkeypatch.setattr(
        gate,
        "read_run_config",
        lambda _path: (config, (Path("train"),), (Path("validation"),)),
    )
    monkeypatch.setattr(
        gate,
        "load_verified_source_panel",
        lambda *_args, **_kwargs: panel,
    )

    def verify_harvest(*_args, **_kwargs):
        calls.append("harvest")
        return "d" * 64

    def write_background(*, output_root, **_kwargs):
        calls.append("background")
        root = Path(output_root)
        root.mkdir(parents=True)
        (root / gate.BACKGROUND_PANEL_FILENAME).write_bytes(
            _canonical({"synthetic": True})
        )
        return (
            {seed: root / f"init-{seed}" for seed in seeds},
            {"background_panel_sha256": "e" * 64},
        )

    def generate_report(**_kwargs):
        assert (tmp_path / "gate" / gate.VALIDATION_CONFIG_FILENAME).is_file()
        calls.append("report")
        return {
            "gate": {"decision": "PASS_LEARNER_GATE"},
            "result_sha256": "f" * 64,
        }

    def independent_verify(*_args, **_kwargs):
        calls.append("verify")
        return {"status": "VERIFIED"}

    monkeypatch.setattr(gate, "verify_harvest_source_panel_bindings", verify_harvest)
    monkeypatch.setattr(
        gate, "write_background_surface_packages_from_harvests", write_background
    )
    monkeypatch.setattr(gate, "generate_validation_report", generate_report)
    monkeypatch.setattr(gate, "verify", independent_verify)

    result = gate.run_gate(
        contract_path=contract,
        code_manifest_path=manifest,
        learner_config_path=learner_config,
        learner_output_root=tmp_path / "learner-output",
        output_root=tmp_path / "gate",
    )
    assert calls == ["harvest", "background", "report", "verify"]
    assert result["decision"] == "PASS_LEARNER_GATE"
    assert result["test_split_opened"] is False
    assert result["episode_training"] is False
    assert (tmp_path / "gate" / gate.SUMMARY_FILENAME).is_file()
    assert (tmp_path / "gate" / gate.VERIFICATION_FILENAME).is_file()

