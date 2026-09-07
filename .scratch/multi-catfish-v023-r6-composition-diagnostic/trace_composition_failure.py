#!/usr/bin/env python3
"""Run one composition shard while preserving the full exception chain."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import sys
import traceback


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("v023_composition_server_diagnostic", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load composition server: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-module", type=Path, required=True)
    known, remainder = parser.parse_known_args()
    module = load_module(known.server_module)
    args = module._parser().parse_args(remainder)
    try:
        receipt = module.run_composition_shard(module._spec_from_args(args))
    except BaseException:
        traceback.print_exc(chain=True)
        return 2
    print("DIAGNOSTIC_UNEXPECTED_PASS", receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
