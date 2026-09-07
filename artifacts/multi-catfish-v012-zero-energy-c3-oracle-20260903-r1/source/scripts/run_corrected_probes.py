"""Validate or run the corrected frozen-grid P2/P3/P7 server pass.

``validate`` is lightweight and is the safe default.  ``run`` executes 1,400
matched real-ephemeris episodes and therefore belongs on the Ubuntu server.
Every run requires a fresh output directory; historical probe artifacts are
never overwritten.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from mcrl.runtime.corrected_probes import (  # noqa: E402
    CANONICAL_PREREG,
    DEFAULT_OUTPUT_DIR,
    run_corrected_probes,
    validate_corrected_probe_setup,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        choices=("validate", "run"),
        nargs="?",
        default="validate",
    )
    parser.add_argument("--prereg", type=Path, default=CANONICAL_PREREG)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.mode == "validate":
        record, plan, _archive, epochs = validate_corrected_probe_setup(args.prereg)
        print(
            "corrected probe guards PASS: "
            f"prereg_digest={record.digest} "
            f"schedule={len(epochs)} "
            f"P2={plan['P2']['episodes']} "
            f"P3={plan['P3']['episodes']}x{len(plan['P3']['policies'])} "
            f"P7={plan['P7']['episodes']}x{len(plan['P7']['arms'])}"
        )
        return 0

    summary = run_corrected_probes(args.prereg, args.out_dir)
    if not summary.get("p6_unlocked"):
        gate = summary.get("calibration_gate", {})
        next_action = (
            gate.get("required_next_action", "corrective_refreeze")
            if isinstance(gate, dict)
            else "corrective_refreeze"
        )
        print(
            "corrected probes complete, but P6 remains BLOCKED: "
            f"required_next_action={next_action}; results={args.out_dir}",
            file=sys.stderr,
        )
        return 2

    print(f"corrected probes complete; P6 gate PASS; results={args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
