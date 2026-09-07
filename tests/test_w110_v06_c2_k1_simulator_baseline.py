"""W-110 -- frozen simulator baseline plus exact learner-only extension."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest


HELPER = (
    Path(__file__).resolve().parents[1]
    / ".scratch/c3-v04/v06_c2_k1_simulator_baseline.py"
)
SPEC = importlib.util.spec_from_file_location("v06_c2_k1_baseline_w110", HELPER)
assert SPEC is not None and SPEC.loader is not None
baseline = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = baseline
SPEC.loader.exec_module(baseline)


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def _manifest(files: dict[str, str]) -> dict[str, object]:
    rows = [
        {"path": path, "sha256": files[path]}
        for path in sorted(files)
    ]
    body = {"schema": "synthetic-production-manifest-v1", "files": rows}
    return body | {"source_manifest_sha256": baseline._canonical_sha256(body)}


class _Support:
    def __init__(self, files: dict[str, str]) -> None:
        self.files = files

    def _production_modules(self) -> object:
        return object()

    def _production_source_manifest(self, _modules: object) -> dict[str, object]:
        return _manifest(self.files)


def _prepare(tmp_path: Path, manifest_sha: str) -> Path:
    payload = {
        "prepare_sha256": _digest("prepare"),
        "simulator_source_manifest_sha256": manifest_sha,
        "training": False,
        "test_split_opened": False,
        "outcome_selection": False,
        "prepared_before_generation": True,
    }
    path = tmp_path / "prepare.json"
    path.write_bytes(baseline._canonical_bytes(payload))
    return path


def _frozen_bundle(tmp_path: Path) -> tuple[_Support, Path, Path, Path]:
    support = _Support(
        {
            "pyproject.toml": _digest("pyproject"),
            "src/mcrl/env/step.py": _digest("step"),
        }
    )
    manifest_sha = _manifest(support.files)["source_manifest_sha256"]
    assert isinstance(manifest_sha, str)
    prepare = _prepare(tmp_path, manifest_sha)
    root = tmp_path / "baseline"
    payload = baseline.capture_baseline(
        support=support, prepare_path=prepare, output_dir=root
    )
    assert payload["extension_paths_present_at_capture"] == []
    return support, prepare, root / "simulator-baseline.json", root / "simulator-baseline-seal.json"


def test_exact_old_bytes_plus_sealed_learner_extension_passes(tmp_path: Path) -> None:
    support, prepare, artifact, seal = _frozen_bundle(tmp_path)
    extension = {
        path: _digest(f"extension:{path}")
        for path in baseline.LEARNER_EXTENSION_PATHS
    }
    support.files = support.files | extension

    receipt = baseline.verify_baseline_extension(
        support=support,
        prepare_path=prepare,
        baseline_path=artifact,
        baseline_seal_path=seal,
        expected_extension_sha256=extension,
    )

    assert receipt["old_files_byte_identical"] is True
    assert receipt["only_declared_extensions_present"] is True
    assert receipt["learner_extension_sha256"] == extension


@pytest.mark.parametrize("failure", ["old-byte", "extra-path", "extension-byte"])
def test_extension_verifier_fails_closed(failure: str, tmp_path: Path) -> None:
    support, prepare, artifact, seal = _frozen_bundle(tmp_path)
    extension = {
        path: _digest(f"extension:{path}")
        for path in baseline.LEARNER_EXTENSION_PATHS
    }
    support.files = support.files | extension
    expected = dict(extension)
    if failure == "old-byte":
        support.files["src/mcrl/env/step.py"] = _digest("changed-step")
    elif failure == "extra-path":
        support.files["src/mcrl/runtime/undeclared.py"] = _digest("undeclared")
    elif failure == "extension-byte":
        expected[baseline.LEARNER_EXTENSION_PATHS[0]] = _digest("wrong")
    else:  # pragma: no cover - protects the parametrization
        raise AssertionError(failure)

    with pytest.raises(baseline.SimulatorBaselineError):
        baseline.verify_baseline_extension(
            support=support,
            prepare_path=prepare,
            baseline_path=artifact,
            baseline_seal_path=seal,
            expected_extension_sha256=expected,
        )

