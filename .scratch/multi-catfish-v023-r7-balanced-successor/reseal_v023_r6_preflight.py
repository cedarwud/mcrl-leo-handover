#!/usr/bin/env python3
"""Compatibility entrypoint for mechanically resealing the R7 draft."""

from reseal_r7_preflight import build


if __name__ == "__main__":
    print(build())
