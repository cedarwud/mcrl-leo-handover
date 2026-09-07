"""Small deterministic benchmark for the W-177 relational C3 fixture."""

from __future__ import annotations

import runpy
import statistics
import time
from pathlib import Path

import mcrl.runtime.ee_axis_relational_zr_c3 as relational


ROOT = Path(__file__).resolve().parents[3]
TEST = runpy.run_path(str(ROOT / "tests/test_w177_ee_axis_relational_zr_c3_performance.py"))
FIXTURE = TEST["_W173"]["_base_fixture"]
SLOW = TEST["_slow_nominal_surface"]


def measure(callable_, repeats: int = 9) -> tuple[float, float]:
    samples: list[float] = []
    for _ in range(repeats):
        start = time.perf_counter()
        callable_()
        samples.append(time.perf_counter() - start)
    return statistics.median(samples), min(samples)


def main() -> None:
    environment, observation, references, opening, powers = FIXTURE()

    def slow_surface() -> None:
        SLOW(environment, observation, references, opening, powers)

    def cached_surface() -> None:
        relational.nominal_relational_zr_surface(
            environment,
            observation,
            reference_actions=references,
            required_power_surface=powers,
            opening_feasibility_surface=opening,
            interval_s=1.0,
            kappa_bits=1.0,
        )

    def cached_encoder() -> None:
        relational.encode_relational_zr_c3_state(
            environment,
            observation,
            reference_actions=references,
            required_power_surface=powers,
            opening_feasibility_surface=opening,
        )

    slow_median, slow_best = measure(slow_surface)
    fast_median, fast_best = measure(cached_surface)
    encoder_median, encoder_best = measure(cached_encoder)
    print(f"slow_surface_median_s={slow_median:.9f}")
    print(f"cached_surface_median_s={fast_median:.9f}")
    print(f"surface_speedup={slow_median / fast_median:.3f}")
    print(f"slow_surface_best_s={slow_best:.9f}")
    print(f"cached_surface_best_s={fast_best:.9f}")
    print(f"cached_encoder_median_s={encoder_median:.9f}")
    print(f"cached_encoder_best_s={encoder_best:.9f}")


if __name__ == "__main__":
    main()
