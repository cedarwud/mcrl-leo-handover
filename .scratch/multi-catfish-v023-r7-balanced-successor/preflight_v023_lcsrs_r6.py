#!/usr/bin/env python3
"""Compatibility entrypoint: validate the R7 draft and authorize no launch."""

from preflight_r7_balanced import main


if __name__ == "__main__":
    raise SystemExit(main())
