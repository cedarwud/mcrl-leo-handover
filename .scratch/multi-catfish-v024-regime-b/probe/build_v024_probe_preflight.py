#!/usr/bin/env python3
"""Build the immutable V0.24 regime-probe preflight after controller seals."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import run_v024_regime_probe as probe


def build(output: Path) -> tuple[Path, str]:
    target = Path(output)
    payload = probe.build_preflight_payload()
    digest = probe._write_once(target, payload)
    sidecar = Path(f"{target}.sha256")
    sidecar_payload = f"{digest}  {target.name}\n".encode("ascii")
    if sidecar.exists() or sidecar.is_symlink():
        raise probe.ProbeError(f"refusing to overwrite write-once artifact: {sidecar}")
    with sidecar.open("xb") as handle:
        handle.write(sidecar_payload)
        handle.flush()
        os.fsync(handle.fileno())
    sidecar.chmod(0o444)
    if sidecar.read_bytes() != sidecar_payload or sidecar.stat().st_mode & 0o777 != 0o444:
        raise probe.ProbeError("preflight sidecar failed immutable readback")
    return target, digest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=probe.DEFAULT_PREFLIGHT)
    args = parser.parse_args()
    try:
        path, digest = build(args.output)
    except Exception as error:
        print(f"V024_PREFLIGHT_ERROR: {error}")
        return 2
    print(f"V024_PREFLIGHT_WRITTEN path={path} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
