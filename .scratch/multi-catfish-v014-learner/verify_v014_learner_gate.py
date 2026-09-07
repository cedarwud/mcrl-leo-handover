#!/usr/bin/env python3
"""Independently verify a completed V0.14 learner-gate directory.

The verifier never fits a learner or opens simulator/TLE data.  It authenticates
the write-once receipts and recomputes every mechanical selection and gate
decision from the persisted reports.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.runtime.ee_axis_v014_gate import (  # noqa: E402
    adjudicate_head,
    adjudicate_joint,
    select_head_rung,
)


RUNNER_PATH = HERE / "run_v014_learner_gate.py"
_RUNNER_SPEC = importlib.util.spec_from_file_location(
    "mcrl_v014_gate_runner_for_verifier", RUNNER_PATH
)
if _RUNNER_SPEC is None or _RUNNER_SPEC.loader is None:
    raise RuntimeError(f"cannot load V0.14 gate runner: {RUNNER_PATH}")
_RUNNER = importlib.util.module_from_spec(_RUNNER_SPEC)
sys.modules[_RUNNER_SPEC.name] = _RUNNER
_RUNNER_SPEC.loader.exec_module(_RUNNER)


VERIFY_SCHEMA = "multi-catfish-mcrl-v014-learnability-independent-verification-v1"


class V014GateVerificationError(RuntimeError):
    """A persisted gate receipt does not reproduce."""


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise V014GateVerificationError(f"missing regular JSON file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise V014GateVerificationError(f"unreadable JSON file: {path}") from error
    if not isinstance(payload, dict):
        raise V014GateVerificationError(f"JSON root is not an object: {path}")
    return payload


def _reports(raw: Mapping[str, Any]) -> dict[int, dict[int, SimpleNamespace]]:
    try:
        return {
            int(seed): {
                int(rung): SimpleNamespace(**dict(report))
                for rung, report in dict(rows).items()
            }
            for seed, rows in raw.items()
        }
    except (AttributeError, TypeError, ValueError) as error:
        raise V014GateVerificationError("head report table is malformed") from error


def _joint_reports(raw: Mapping[str, Any]) -> dict[int, dict[int, dict[str, Any]]]:
    try:
        return {
            int(seed): {int(rung): dict(report) for rung, report in dict(rows).items()}
            for seed, rows in raw.items()
        }
    except (AttributeError, TypeError, ValueError) as error:
        raise V014GateVerificationError("joint report table is malformed") from error


def _require_equal(actual: object, expected: object, *, field: str) -> None:
    if actual != expected:
        raise V014GateVerificationError(
            f"{field} does not reproduce: {actual!r} != {expected!r}"
        )


def verify(output_dir: str | Path) -> dict[str, object]:
    root = Path(output_dir)
    if root.is_symlink() or not root.is_dir():
        raise V014GateVerificationError(f"gate output is not a regular directory: {root}")
    authority_path = root / "authority.json"
    result_path = root / "result.json"
    seal_path = root / "result-seal.json"
    authority = _read_object(authority_path)
    result = _read_object(result_path)
    seal = _read_object(seal_path)

    _require_equal(
        _file_sha256(result_path), seal.get("result_file_sha256"), field="result file SHA-256"
    )
    authority_body = {key: value for key, value in authority.items() if key != "authority_sha256"}
    _require_equal(
        _RUNNER.canonical_sha256(authority_body),
        authority.get("authority_sha256"),
        field="authority body SHA-256",
    )
    for field in ("authority_sha256", "run_spec_sha256"):
        _require_equal(result.get(field), seal.get(field), field=f"seal {field}")
    for field in ("test_split_opened", "held_out_ee_evaluated", "episode_training"):
        _require_equal(result.get(field), False, field=field)

    spec = dict(result.get("spec", {}))
    initializations = tuple(int(value) for value in spec.get("initialization_seeds", ()))
    rungs = tuple(int(value) for value in spec.get("update_rungs", ()))
    if len(initializations) != 3 or not rungs:
        raise V014GateVerificationError("persisted gate spec is incomplete")
    q2 = _reports(dict(result.get("q2_reports", {})))
    q3 = _reports(dict(result.get("q3_reports", {})))
    joint = _joint_reports(dict(result.get("joint_reports", {})))

    common_rung, common_means = _RUNNER.select_common_rung(
        q2, q3, initialization_seeds=initializations, update_rungs=rungs
    )
    q2_best, q2_means = select_head_rung(
        q2, initialization_seeds=initializations, update_rungs=rungs
    )
    q3_best, q3_means = select_head_rung(
        q3, initialization_seeds=initializations, update_rungs=rungs
    )
    selection = dict(result.get("selection", {}))
    _require_equal(selection.get("deployment_rung"), common_rung, field="deployment rung")
    _require_equal(selection.get("common_joint_rung"), common_rung, field="joint rung")
    _require_equal(selection.get("q2_diagnostic_best_rung"), q2_best, field="Q2 diagnostic rung")
    _require_equal(selection.get("q3_diagnostic_best_rung"), q3_best, field="Q3 diagnostic rung")
    _require_equal(
        selection.get("common_mean_ratios"),
        {str(key): value for key, value in common_means.items()},
        field="common mean ratios",
    )
    _require_equal(
        selection.get("q2_mean_ratios"),
        {str(key): value for key, value in q2_means.items()},
        field="Q2 mean ratios",
    )
    _require_equal(
        selection.get("q3_mean_ratios"),
        {str(key): value for key, value in q3_means.items()},
        field="Q3 mean ratios",
    )

    q2_decision = adjudicate_head(
        q2, selected_rung=common_rung, initialization_seeds=initializations
    )
    q3_decision = adjudicate_head(
        q3, selected_rung=common_rung, initialization_seeds=initializations
    )
    joint_decision = adjudicate_joint(
        {seed: joint[seed][common_rung] for seed in initializations},
        initialization_seeds=initializations,
    )
    _require_equal(result.get("q2_decision"), q2_decision, field="Q2 decision")
    _require_equal(result.get("q3_decision"), q3_decision, field="Q3 decision")
    _require_equal(result.get("joint_decision"), joint_decision, field="joint decision")
    passed = bool(
        q2_decision["passed"] and q3_decision["passed"] and joint_decision["passed"]
    )
    _require_equal(
        result.get("status"),
        "PASS_LEARNABILITY_GATE" if passed else "STOP_LEARNABILITY_GATE",
        field="gate status",
    )

    checkpoint_hashes = dict(result.get("checkpoint_file_sha256s", {}))
    checked = 0
    for seed in initializations:
        rows = dict(checkpoint_hashes.get(str(seed), {}))
        if set(rows) != {str(rung) for rung in rungs}:
            raise V014GateVerificationError(f"checkpoint rung closure is incomplete for {seed}")
        for rung in rungs:
            path = root / "checkpoints" / f"init-{seed}-rung-{rung:06d}.pt"
            if path.is_symlink() or not path.is_file():
                raise V014GateVerificationError(f"missing checkpoint: {path}")
            _require_equal(
                _file_sha256(path), rows[str(rung)], field=f"checkpoint {seed}/{rung}"
            )
            checked += 1

    return {
        "schema": VERIFY_SCHEMA,
        "status": "VERIFIED",
        "gate_status": result["status"],
        "deployment_rung": common_rung,
        "checkpoint_files_verified": checked,
        "result_file_sha256": _file_sha256(result_path),
        "authority_file_sha256": _file_sha256(authority_path),
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "episode_training": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    print(json.dumps(verify(args.output_dir), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

