#!/usr/bin/env python3
"""Server-facing alias for the V0.23 one-world plumbing dry-run/preflight.

It deliberately delegates only to the no-execution CLI.  No SSH, TLE open,
environment construction, checkpoint deserialisation, learner update, result
write, or scientific decision occurs from this entrypoint.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Sequence


HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "v023_real_one_world_plumbing.py"
SPEC = importlib.util.spec_from_file_location("v023_real_one_world_plumbing_server_api", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
API = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = API
SPEC.loader.exec_module(API)


def main(argv: Sequence[str] | None = None) -> int:
    return int(API._main(argv))


if __name__ == "__main__":  # pragma: no cover - entrypoint is not run in this task
    raise SystemExit(main())
