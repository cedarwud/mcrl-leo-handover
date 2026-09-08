"""Explicit-calibration boundary for OPS-3 target construction."""

from __future__ import annotations

from typing import Any, Callable


def build_ops3_surface_explicit(
    *, lambda_bits_per_j: float, builder: Callable[..., Any] | None = None, **inputs: Any
) -> Any:
    """Build a surface while making silent lambda fallback impossible.

    ``builder`` is injectable so a successor engine can use the same assertion
    without importing the V0.23 implementation.  The calibration keyword has
    deliberately no default.
    """

    if builder is None:
        from mcrl.runtime.ee_axis_ops3 import build_ops3_surface as builder
    return builder(lambda_bits_per_j=float(lambda_bits_per_j), **inputs)
