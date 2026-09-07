"""Validate or run the corrected P6-to-main server training pipeline.

This is the only supported long-run entry point.  The default ``pipeline``
mode verifies the corrected frozen record and live environment, runs all
three P6 learning-rate arms, applies the predeclared mapping, and then starts
the independent main run.  ``main`` deliberately has no learning-rate
default: a caller must supply the value selected by P6.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from mcrl.runtime.probe_p6 import P6_LEARNING_RATES  # noqa: E402

CANONICAL_PREREG = REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json"
CORRECTED_PROBE_SUMMARY = (
    REPO / "artifacts" / "probes-2026-08-25-rerun01" / "summary.json"
)
DEFAULT_OUTPUT_DIR = REPO / "artifacts" / "training-2026-08-25-rerun01"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        choices=("validate", "pipeline", "p6", "main"),
        nargs="?",
        default="pipeline",
    )
    parser.add_argument("--prereg", type=Path, default=CANONICAL_PREREG)
    parser.add_argument(
        "--probe-summary",
        type=Path,
        default=CORRECTED_PROBE_SUMMARY,
        help="corrected-probe evidence that the R2 seal deterministically applies",
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--learning-rate",
        type=float,
        choices=P6_LEARNING_RATES,
        help="required only for a manual main run; normally selected by P6",
    )
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.mode == "main" and args.learning_rate is None:
        parser.error("main mode requires --learning-rate selected by P6")
    if args.mode != "main" and args.learning_rate is not None:
        parser.error("--learning-rate is accepted only in manual main mode")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    # Keep --help and argument validation usable in a lightweight controller
    # environment.  Torch is required only after a valid run mode is known.
    from mcrl.runtime.training_pipeline import (
        run_main_training,
        run_p6_sweep,
        run_training_pipeline,
        validate_server_setup,
    )

    if args.mode == "pipeline":
        result = run_training_pipeline(
            args.prereg,
            args.out_dir,
            probe_summary_path=args.probe_summary,
        )
        print(
            "pipeline complete: "
            f"learning_rate={result['selected_learning_rate']} "
            f"prereg_digest={result['prereg_digest']}"
        )
        return 0

    record = validate_server_setup(
        args.prereg,
        probe_summary_path=args.probe_summary,
    )
    if args.mode == "validate":
        print(f"server guards PASS: prereg_digest={record.digest}")
        return 0
    if args.mode == "p6":
        selected, _summary = run_p6_sweep(record, args.out_dir)
        print(f"P6 complete: selected_learning_rate={selected}")
        return 0

    result = run_main_training(
        record,
        args.out_dir,
        learning_rate=float(args.learning_rate),
    )
    if result.get("status") != "complete":
        print(
            "main did not complete: "
            f"status={result.get('status')} "
            f"learning_rate={args.learning_rate}",
            file=sys.stderr,
        )
        return 2
    print(
        f"main complete: learning_rate={result['learning_rate']} "
        f"prereg_digest={result['prereg_digest']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
