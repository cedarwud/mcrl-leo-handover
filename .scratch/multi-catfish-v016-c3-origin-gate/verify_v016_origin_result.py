#!/usr/bin/env python3
"""Independently verify a completed V0.16-O origin-gate receipt.

This checker does not import the gate runner or any learner implementation.
It recomputes the frozen update-3000 clauses from result.json, authenticates
the result/checkpoint bytes, and enforces the declared TRAIN-only boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


EXPECTED_CONTRACT_SHA256 = (
    "4dfeb9154983ee12ec6690e61c92a19e6893b27c811b0b84352a5d52c28b6784"
)
EXPECTED_INITIALIZATIONS = (2026111101, 2026111102, 2026111103)
EXPECTED_SOURCE_LINEAGES = (2026092101, 2026092102, 2026092103)
EXPECTED_TRAIN_WORLDS = (2026111001, 2026111002, 2026111003)
EXPECTED_VALIDATION_WORLDS = (2026111004, 2026111005, 2026111006)
EXPECTED_RUNGS = (3, 10, 30, 100, 300, 1000, 3000)
EXPECTED_CONTEXTS = (12, 1, 2)


class VerificationError(RuntimeError):
    """The persisted result is inconsistent with its frozen contract."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def recompute_clauses(contexts: dict[str, Any]) -> dict[str, bool]:
    require(set(contexts) == {"12", "1", "2"}, "unexpected context set")
    full = contexts["12"]
    h1 = contexts["1"]
    h2 = contexts["2"]
    return {
        "full_teacher_agreement_improved": (
            float(full["learned_teacher_agreement"])
            > float(full["background_teacher_agreement"])
        ),
        "full_pivotal_agreement_at_least_0_50": (
            full["pivotal_agreement"] is not None
            and float(full["pivotal_agreement"]) >= 0.50
        ),
        "full_stable_preservation_at_least_0_95": (
            full["stable_preservation"] is not None
            and float(full["stable_preservation"]) >= 0.95
        ),
        "full_has_change_exposure": int(full["student_change_count"]) > 0,
        "full_positive_compatible_support_at_least_0_80": (
            full["positive_compatible_support_fraction"] is not None
            and float(full["positive_compatible_support_fraction"]) >= 0.80
        ),
        "h1_teacher_agreement_noninferior": (
            float(h1["learned_teacher_agreement"])
            >= float(h1["background_teacher_agreement"])
        ),
        "h2_teacher_agreement_noninferior": (
            float(h2["learned_teacher_agreement"])
            >= float(h2["background_teacher_agreement"])
        ),
        "integrity_and_split_checks_passed": True,
    }


def resolve_checkpoint(result_path: Path, recorded: str) -> Path:
    candidate = Path(recorded)
    if candidate.is_absolute():
        candidate = Path(candidate.name)
    else:
        candidate = result_path.parent.parent / candidate
    if candidate.is_file():
        return candidate
    fallback = result_path.parent / "checkpoints" / Path(recorded).name
    require(fallback.is_file(), f"missing checkpoint: {recorded}")
    return fallback


def verify(result_path: Path) -> dict[str, Any]:
    result_path = result_path.resolve()
    require(result_path.is_file() and not result_path.is_symlink(), "bad result path")
    receipt_path = result_path.with_name("receipt.json")
    require(receipt_path.is_file() and not receipt_path.is_symlink(), "missing receipt")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    result_digest = sha256(result_path)
    require(receipt["result_sha256"] == result_digest, "result SHA-256 mismatch")
    require(result["contract_sha256"] == EXPECTED_CONTRACT_SHA256, "contract mismatch")
    require(result["q3_state_dim"] == 402, "state dimension is not 402")
    require(tuple(result["train_world_seeds"]) == EXPECTED_TRAIN_WORLDS, "train worlds drifted")
    require(
        tuple(result["validation_world_seeds"]) == EXPECTED_VALIDATION_WORLDS,
        "validation worlds drifted",
    )
    require(tuple(result["source_lineages"]) == EXPECTED_SOURCE_LINEAGES, "lineages drifted")
    require(
        tuple(result["initialization_seeds"]) == EXPECTED_INITIALIZATIONS,
        "initializations drifted",
    )
    require(tuple(result["update_rungs"]) == EXPECTED_RUNGS, "rungs drifted")
    require(result["source_only"] is True, "source-only flag is false")
    require(result["test_split_opened"] is False, "TEST was opened")
    require(result["held_out_ee_evaluated"] is False, "held-out EE was evaluated")
    require(result["episode_training"] is False, "episode training flag is true")

    reports = result["reports"]
    require(set(reports) == {str(seed) for seed in EXPECTED_INITIALIZATIONS}, "report set drifted")
    recomputed_pass: dict[str, bool] = {}
    diagnostics: dict[str, Any] = {}
    for initialization, lineage in zip(
        EXPECTED_INITIALIZATIONS, EXPECTED_SOURCE_LINEAGES, strict=True
    ):
        report = reports[str(initialization)]
        require(report["initialization_seed"] == initialization, "initialization mismatch")
        require(report["source_lineage"] == lineage, "initialization-lineage mismatch")
        rungs = report["rungs"]
        require(set(rungs) == {str(rung) for rung in EXPECTED_RUNGS}, "rung report set drifted")
        for rung in EXPECTED_RUNGS:
            persisted = rungs[str(rung)]
            checkpoint = resolve_checkpoint(result_path, persisted["checkpoint"])
            require(
                sha256(checkpoint) == persisted["checkpoint_sha256"],
                f"checkpoint SHA-256 mismatch: init={initialization}, rung={rung}",
            )
            require(
                set(persisted["validation_contexts"]) == {str(code) for code in EXPECTED_CONTEXTS},
                f"context set drifted: init={initialization}, rung={rung}",
            )
            require(
                (persisted["decision"] is None) == (rung != 3000),
                f"decision appeared at wrong rung: init={initialization}, rung={rung}",
            )

        final = rungs["3000"]
        clauses = recompute_clauses(final["validation_contexts"])
        require(final["decision"]["clauses"] == clauses, f"clause mismatch: init={initialization}")
        passed = all(clauses.values())
        require(final["decision"]["passed"] is passed, f"pass mismatch: init={initialization}")
        require(result["per_initialization_pass"][str(initialization)] is passed, "panel pass mismatch")
        recomputed_pass[str(initialization)] = passed
        diagnostics[str(initialization)] = {
            "full_background_teacher_agreement": final["validation_contexts"]["12"][
                "background_teacher_agreement"
            ],
            "full_learned_teacher_agreement": final["validation_contexts"]["12"][
                "learned_teacher_agreement"
            ],
            "full_pivotal_agreement": final["validation_contexts"]["12"][
                "pivotal_agreement"
            ],
            "full_stable_preservation": final["validation_contexts"]["12"][
                "stable_preservation"
            ],
            "full_positive_compatible_support_fraction": final[
                "validation_contexts"
            ]["12"]["positive_compatible_support_fraction"],
            "origin_peer_zero_change_rate": final["validation_contexts"]["12"][
                "student_change_rate_when_origin_peer_zero"
            ],
            "clauses": clauses,
        }

    panel_pass = all(recomputed_pass.values())
    require(result["passed"] is panel_pass, "overall pass mismatch")
    expected_decision = "PASS_ORIGIN_GATE" if panel_pass else "FAIL_ORIGIN_GATE"
    require(result["decision"] == expected_decision, "overall decision mismatch")
    require(receipt["decision"] == expected_decision, "receipt decision mismatch")
    expected_next = (
        "AUTHORIZE_100EP_FIVE_ARM_PREREG_ONLY"
        if panel_pass
        else "STOP_C3_B402_STRUCTURALLY"
    )
    require(result["next_authority"] == expected_next, "next authority mismatch")

    return {
        "verified": True,
        "result_sha256": result_digest,
        "decision": expected_decision,
        "next_authority": expected_next,
        "per_initialization_pass": recomputed_pass,
        "update_3000": diagnostics,
        "claim_ceiling": result["claim_ceiling"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.result), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
