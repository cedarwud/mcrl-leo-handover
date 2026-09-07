#!/usr/bin/env python3
"""Red-capable micro-loop for the V0.18 nominal-C3 branch explosion.

The three-user W173 fixture has ten legal focal-action branches.  A cached
implementation needs at most one full reference-interference construction per
public surface; the current implementation reconstructs it for every branch.
This check deliberately exits non-zero until that repeated full-network work
is removed.  Numerical equivalence belongs to the paired differential test in
the eventual fix, not to this call-budget detector.
"""

from __future__ import annotations

import runpy
from pathlib import Path
from unittest.mock import patch

import mcrl.runtime.ee_axis_relational_zr_c3 as relational


REPO = Path(__file__).resolve().parents[3]
FIXTURE = runpy.run_path(str(REPO / "tests/test_w173_ee_axis_relational_zr_c3.py"))


def main() -> int:
    environment, observation, references, opening, powers = FIXTURE["_base_fixture"]()
    calls = 0
    original = relational._nominal_interference

    def counted(*args: object, **kwargs: object):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    with patch.object(relational, "_nominal_interference", counted):
        relational.nominal_relational_zr_surface(
            environment,
            observation,
            reference_actions=references,
            required_power_surface=powers,
            opening_feasibility_surface=opening,
            interval_s=1.0,
            kappa_bits=1.0,
        )

    budget = 1
    verdict = "PASS" if calls <= budget else "FAIL"
    print(f"{verdict} full_network_interference_calls={calls} budget={budget}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
