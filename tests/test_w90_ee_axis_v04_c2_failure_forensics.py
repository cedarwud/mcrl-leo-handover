"""W-90 -- core contracts for the V0.4 C2 failure forensic audit."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest


REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "v04_c2_forensics",
    REPO / ".scratch/c3-v04/run_v04_c2_failure_forensics.py",
)
assert SPEC is not None and SPEC.loader is not None
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def test_support_metrics_detect_off_pair_argmax() -> None:
    q = np.asarray([[0.0, 1.0, 4.0], [2.0, 0.0, 3.0]], dtype=np.float64)
    masks = np.ones((2, 3), dtype=np.bool_)
    references = np.asarray([0, 1], dtype=np.int64)
    candidates = np.asarray([1, 0], dtype=np.int64)
    targets = np.asarray([1.0, 1.0], dtype=np.float64)

    result = audit.q2_support_metrics(q, masks, references, candidates, targets)

    assert result["pair_sign_accuracy"] == 1.0
    assert result["top_is_supervised_pair_count"] == 0
    assert result["top_is_off_pair_count"] == 2
    assert result["top_is_off_pair_fraction"] == 1.0
    assert result["off_pair_top_margin_positive_count"] == 2


def test_support_metrics_respects_legal_mask() -> None:
    q = np.asarray([[0.0, 1.0, 99.0]], dtype=np.float64)
    masks = np.asarray([[True, True, False]], dtype=np.bool_)
    result = audit.q2_support_metrics(
        q,
        masks,
        np.asarray([0]),
        np.asarray([1]),
        np.asarray([1.0]),
    )
    assert result["top_is_candidate_count"] == 1
    assert result["top_is_off_pair_count"] == 0


def test_support_metrics_rejects_illegal_supervised_action() -> None:
    with pytest.raises(audit.C2ForensicsError, match="supervised actions must be legal"):
        audit.q2_support_metrics(
            np.asarray([[0.0, 1.0]], dtype=np.float64),
            np.asarray([[True, False]], dtype=np.bool_),
            np.asarray([0]),
            np.asarray([1]),
            np.asarray([1.0]),
        )
