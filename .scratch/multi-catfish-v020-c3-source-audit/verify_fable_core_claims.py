"""Recompute the high-impact numeric claims in the Fable C3 audit.

This reads only already-opened development result JSON.  It does not import a
simulator or learner and does not inspect TEST data.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
V012 = ROOT / "artifacts/multi-catfish-v012-zero-energy-c3-oracle-20260903-r1/server-run/merged/result.json"
V013 = ROOT / "artifacts/multi-catfish-v013-zr-c3-fresh-confirmation-20260903-r1/server-run/merged/result.json"
V018 = ROOT / "artifacts/multi-catfish-v018-relational-zr-20260904-r2/server-run-r2/analytic-panel-r2/merged/result.json"
V019 = ROOT / "artifacts/multi-catfish-v019-relational-q3-learner-20260904-r1/server-run/gate-output/report/result.json"
OUTPUT = Path(__file__).with_name("fable-core-claim-recheck.json")


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} is not a JSON object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relative(candidate: float, reference: float) -> float:
    return candidate / reference - 1.0


def _contrast(
    result: dict[str, Any], *, candidate: str, reference: str
) -> dict[str, float | int]:
    arms = result["summaries"]["pooled_by_arm"]
    c = arms[candidate]
    r = arms[reference]
    output: dict[str, float | int] = {
        "bits_relative": _relative(float(c["total_bits"]), float(r["total_bits"])),
        "energy_relative": _relative(
            float(c["total_energy_j"]), float(r["total_energy_j"])
        ),
        "ee_relative": _relative(
            float(c["ratio_of_sums_ee_bits_per_j"]),
            float(r["ratio_of_sums_ee_bits_per_j"]),
        ),
        "candidate_ee_bits_per_j": float(c["ratio_of_sums_ee_bits_per_j"]),
        "reference_ee_bits_per_j": float(r["ratio_of_sums_ee_bits_per_j"]),
        "candidate_served_user_steps": int(c["served_user_steps"]),
        "reference_served_user_steps": int(r["served_user_steps"]),
    }
    if "active_beam_steps" in c and "active_beam_steps" in r:
        output["candidate_active_beam_steps"] = int(c["active_beam_steps"])
        output["reference_active_beam_steps"] = int(r["active_beam_steps"])
    return output


def main() -> None:
    v012 = _load(V012)
    v013 = _load(V013)
    v018 = _load(V018)
    v019 = _load(V019)
    lambda_hex = str(v013["contract"]["lambda_bits_per_j_hex"])
    kappa_hex = str(v013["contract"]["kappa_bits_hex"])
    lambda_value = float.fromhex(lambda_hex)
    kappa_value = float.fromhex(kappa_hex)
    v018_base = float(
        v018["summaries"]["pooled_by_arm"]["BASE"][
            "ratio_of_sums_ee_bits_per_j"
        ]
    )
    initializations = v019["initializations"]
    output = {
        "schema": "multi-catfish-v020-fable-core-claim-recheck-v1",
        "evidence_class": "OPENED_DEVELOPMENT_JSON_ONLY_NO_TEST_NO_RUN",
        "inputs": {
            str(path.relative_to(ROOT)): _sha256(path)
            for path in (V012, V013, V018, V019)
        },
        "oracle_contrasts": {
            "v012_full_zr_vs_drop_c3": _contrast(
                v012, candidate="FULL_ZR", reference="DROP_C3"
            ),
            "v013_full_zr_vs_drop_c3": _contrast(
                v013, candidate="FULL_ZR", reference="DROP_C3"
            ),
            "v018_exact_zr_vs_base": _contrast(
                v018, candidate="EXACT_ZR", reference="BASE"
            ),
            "v018_nominal_zr_vs_base": _contrast(
                v018, candidate="NOMINAL_ZR", reference="BASE"
            ),
        },
        "multiplier": {
            "lambda_bits_per_j_hex": lambda_hex,
            "lambda_bits_per_j": lambda_value,
            "kappa_bits_hex": kappa_hex,
            "kappa_bits": kappa_value,
            "v018_base_ee_bits_per_j": v018_base,
            "lambda_over_v018_base_ee": lambda_value / v018_base,
            "relative_shortfall": 1.0 - lambda_value / v018_base,
        },
        "v019_gate": {
            "decision": v019["gate"]["decision"],
            "mean_validation_skill": float(v019["gate"]["mean_validation_skill"]),
            "pooled_student_change_exposure": int(
                v019["gate"]["pooled_student_change_exposure"]
            ),
            "pooled_supported_positive_changes": int(
                v019["gate"]["pooled_supported_positive_changes"]
            ),
            "pooled_supported_change_rate": float(
                v019["gate"]["pooled_supported_change_rate"]
            ),
            "per_initialization": [
                {
                    "initialization_seed": int(item["initialization_seed"]),
                    "lineage": int(item["lineage"]),
                    "validation_skill": float(item["validation"]["validation_skill"]),
                    "pivotal_rows": int(item["validation"]["pivotal_rows"]),
                    "pivotal_agreement": float(
                        item["validation"]["pivotal_agreement"]
                    ),
                    "changed_action_count": int(
                        item["validation"]["background_changed_action_count"]
                    ),
                    "supported_positive_change_count": int(
                        item["validation"]["supported_positive_change_count"]
                    ),
                }
                for item in initializations
            ],
        },
        "interpretation_boundary": {
            "verified": [
                "ZR oracle policies lower bits and energy, with energy falling proportionally more, so ratio-of-sums EE rises on these development panels.",
                "The frozen lambda is about 28 percent below the V0.18 BASE operating EE.",
                "The V0.19 learned Q3 gate failed with negative skill and sparse supported changes.",
            ],
            "not_proved_by_these_numbers": [
                "That stale lambda is the cause of the ZR oracle gain.",
                "That ZR is an invalid R3 target rather than an indirect consolidation mechanism.",
                "That the proposed CSE unilateral target is an exact potential for simultaneous deployment.",
            ],
        },
    }
    OUTPUT.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(OUTPUT)
    print(hashlib.sha256(OUTPUT.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
