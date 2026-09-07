"""Pure provenance checks for the V0.18 analytic-R2 execution closure.

The tests authenticate only already-persisted receipts.  They do not open a
TLE, execute an environment action, invoke the exact teacher, train a learner,
or access TEST.
"""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[1]
RUNNER_PATH = (
    REPO / ".scratch" / "multi-catfish-v018-relational-zr"
    / "run_v018_analytic_diagnostic.py"
)
_SPEC = importlib.util.spec_from_file_location("test_v018_r2_provenance_runner", RUNNER_PATH)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover - import failure
    raise RuntimeError(f"cannot import V0.18 runner: {RUNNER_PATH}")
runner = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(runner)


ADDENDUM = REPO / ".scratch/multi-catfish-v018-relational-zr/contracts/" \
    "MULTI-CATFISH-MCRL-V018-PERFORMANCE-EQUIVALENCE-ADDENDUM-R2-2026-09-04.md"
ABORT = REPO / ".scratch/multi-catfish-v018-relational-zr/r1-abort/ABORT-RECEIPT.md"
R4_ROOT = REPO / "artifacts/multi-catfish-v018-r4-equivalence-20260904-r1/server-run-r2"
R4_RESULT = R4_ROOT / "result/result.json"
R4_RECEIPT = R4_ROOT / "result/receipt.json"
R4_MANIFEST = REPO / "artifacts/multi-catfish-v018-r4-equivalence-20260904-r1/MANIFEST-R2.sha256"
R4_CODE = R4_ROOT / "closure/code-manifest-r4-equivalence.sha256"
R4_VALIDATION = R4_ROOT / "independent-validation.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _kwargs() -> dict[str, object]:
    # pyproject is a small synthetic code-manifest *file* for this pure unit
    # test.  The production closure supplies the separate analytic-R2
    # manifest path and digest at launch.
    return {
        "performance_addendum": Path(str(ADDENDUM.relative_to(REPO))),
        "performance_addendum_sha256": _sha(ADDENDUM),
        "r2_code_manifest": Path("pyproject.toml"),
        "r2_code_manifest_sha256": _sha(REPO / "pyproject.toml"),
        "r1_abort_receipt": Path(str(ABORT.relative_to(REPO))),
        "r1_abort_receipt_sha256": _sha(ABORT),
        "r4_result": Path(str(R4_RESULT.relative_to(REPO))),
        "r4_result_sha256": _sha(R4_RESULT),
        "r4_receipt": Path(str(R4_RECEIPT.relative_to(REPO))),
        "r4_receipt_sha256": _sha(R4_RECEIPT),
        "r4_artifact_manifest": Path(str(R4_MANIFEST.relative_to(REPO))),
        "r4_artifact_manifest_sha256": _sha(R4_MANIFEST),
        "r4_code_manifest": Path(str(R4_CODE.relative_to(REPO))),
        "r4_code_manifest_sha256": _sha(R4_CODE),
        "r4_independent_validation": Path(str(R4_VALIDATION.relative_to(REPO))),
        "r4_independent_validation_sha256": _sha(R4_VALIDATION),
    }


def test_r2_provenance_binds_r1_r4_and_addendum_receipts() -> None:
    provenance = runner.build_r2_provenance(**_kwargs())

    assert provenance["schema"] == runner.PROVENANCE_SCHEMA
    assert provenance["execution_attempt"] == "r2"
    assert provenance["r1_abort_receipt"]["sha256"] == _sha(ABORT)
    assert provenance["performance_addendum"]["sha256"] == _sha(ADDENDUM)
    assert provenance["r4_pass"]["decision"] == "PASS_R2_CACHE_EQUIVALENCE"
    assert provenance["r4_pass"]["code_manifest"]["sha256"] == runner.R4_CODE_MANIFEST_SHA256
    runner.validate_r2_provenance(provenance)


def test_r2_provenance_has_a_self_digest_and_rejects_mutation() -> None:
    provenance = runner.build_r2_provenance(**_kwargs())
    runner.validate_r2_provenance(provenance)

    changed = dict(provenance)
    changed["provenance_sha256"] = "0" * 64
    with pytest.raises(runner.V018OracleError, match="self-digest"):
        runner.validate_r2_provenance(changed)


def test_r2_provenance_rejects_non_r4_pass_or_wrong_file_digest() -> None:
    bad = _kwargs()
    bad["r4_result_sha256"] = "0" * 64
    with pytest.raises(runner.V018OracleError, match="r4_result digest mismatch"):
        runner.build_r2_provenance(**bad)

    bad = _kwargs()
    bad["r4_code_manifest_sha256"] = "0" * 64
    with pytest.raises(runner.V018OracleError, match="r4_code_manifest digest mismatch"):
        runner.build_r2_provenance(**bad)


def test_r2_wrappers_default_to_isolated_r2_and_bind_provenance() -> None:
    root = REPO / ".scratch/multi-catfish-v018-relational-zr"
    sync = (root / "sync_v018_analytic_server.sh").read_text(encoding="utf-8")
    run = (root / "run_v018_analytic_panel_server.sh").read_text(encoding="utf-8")
    finalize = (root / "finalize_v018_analytic_server.sh").read_text(encoding="utf-8")
    for text in (sync, run, finalize):
        assert "/home/sat/mcrl-v018-relational-zr-20260904-r2" in text
        assert 'V018R_RUN_LABEL:-r2' in text
        assert "code-manifest-r2-analytic.sha256" in text
        assert "r1_abort_receipt" in text
        assert "r4_artifact_manifest" in text
    assert "--r4-independent-validation-sha256" in run
