from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / ".scratch" / "c3-v04" / "seal_v05_c2_controlled_support_failure.py"


def _load():
    spec = importlib.util.spec_from_file_location("v05_support_failure_seal", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_expected_inventory_is_48_with_exact_seven_failures() -> None:
    module = _load()
    expected = module._expected_entries()
    assert len(expected) == 48
    assert len(module.EXPECTED_FAILURES) == 7
    assert len({row[0] for row in expected}) == 48
    assert set(module.EXPECTED_FAILURES).issubset({row[0] for row in expected})


def test_failure_log_requires_exact_native_support_error(tmp_path: Path) -> None:
    module = _load()
    log = tmp_path / "main-anchor-10.log"
    log.write_text(
        "Traceback (most recent call last):\n"
        "ControlledTapeContractError: candidate_slot_tables[3][15] "
        "physical key is missing; matches=[]\n",
        encoding="utf-8",
    )
    receipt = module._authenticate_failure_log(
        log,
        stem="main-anchor-10",
        policy="main",
        seed=None,
        anchor=10,
    )
    assert receipt["candidate_offset"] == 3
    assert receipt["nonfocal_user"] == 15

    log.write_text(
        "Traceback (most recent call last):\n"
        "ControlledTapeContractError: candidate_slot_tables[2][15] "
        "physical key is missing; matches=[]\n",
        encoding="utf-8",
    )
    with pytest.raises(module.SupportFailureSealError, match="identity drifted"):
        module._authenticate_failure_log(
            log,
            stem="main-anchor-10",
            policy="main",
            seed=None,
            anchor=10,
        )


def test_write_once_rejects_existing_target(tmp_path: Path) -> None:
    module = _load()
    target = tmp_path / "receipt.json"
    first = module._write_once(target, {"a": 1})
    assert len(first) == 64
    assert json.loads(target.read_text(encoding="ascii")) == {"a": 1}
    with pytest.raises(module.SupportFailureSealError, match="refusing to overwrite"):
        module._write_once(target, {"a": 2})
