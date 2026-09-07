#!/usr/bin/env python3
"""Canonical-fading entry point for the C2 V0.3 matched-fork viability probe."""

from __future__ import annotations

from pathlib import Path

from run_c2_v03_deterministic_plumbing_probe import (
    KEYED_FADING_VERSION,
    main,
)


DEFAULT_OUTPUT = Path(__file__).resolve().parent / "c2-v03-keyed-fading-viability-smoke.json"


if __name__ == "__main__":
    raise SystemExit(
        main(
            default_fading_mode=KEYED_FADING_VERSION,
            default_output=DEFAULT_OUTPUT,
        )
    )
