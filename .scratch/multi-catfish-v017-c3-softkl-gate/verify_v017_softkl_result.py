#!/usr/bin/env python3
"""Independently verify a completed V0.17 masked soft-KL gate receipt.

This checker imports neither the gate runner nor the learner.  It authenticates
the persisted result and checkpoints, recomputes every update-3000 decision
clause, and enforces the frozen TRAIN/VALIDATION source-only boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


EXPECTED_CONTRACT_SHA256 = (
    "ef7e6abd3c2a657cf718a09b5169f652609f65c0c41e30b2257245920fdea70b"
)
EXPECTED_INITIALIZATIONS = (2026112101, 2026112102, 2026112103)
EXPECTED_SOURCE_LINEAGES = (2026092101, 2026092102, 2026092103)
EXPECTED_TRAIN_WORLDS = (2026112001, 2026112002, 2026112003)
EXPECTED_VALIDATION_WORLDS = (2026112004, 2026112005, 2026112006)
EXPECTED_RUNGS = (3, 10, 30, 100, 300, 1000, 3000)
EXPECTED_CONTEXTS = (12, 1, 2)
EXPECTED_CLAIM_CEILING = (
    "TRAIN_VALIDATION_SOURCE_ONLY_NO_TRAJECTORY_EE_OR_EFFICACY_CLAIM"
)


class VerificationError(RuntimeError):
    """The persisted result is inconsistent with its frozen contract."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def require_finite_metric(value: object, field: str) -> None:
    require(
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value)),
        f"{field} must be finite",
    )


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
    require(result["claim_ceiling"] == EXPECTED_CLAIM_CEILING, "claim ceiling drifted")
    require(receipt["claim_ceiling"] == EXPECTED_CLAIM_CEILING, "receipt claim ceiling drifted")
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
    require(result["balanced_batch"] == {
        "context_order": [12, 1, 2], "per_context": 170, "total": 510
    }, "balanced batch drifted")
    require(result["objective"] == {
        "all_legal_actions": True,
        "name": "masked-row-mean-soft-teacher-kl",
        "one_action_rows_included": True,
        "reference_gauge_beta": 0.1,
        "temperature": 1.0,
    }, "objective drifted")
    require(result["source_only"] is True, "source-only flag is false")
    require(result["test_split_opened"] is False, "TEST was opened")
    require(result["held_out_ee_evaluated"] is False, "held-out EE was evaluated")
    require(result["episode_training"] is False, "episode training flag is true")

    code_manifest = result["code_manifest"]
    require(
        canonical_sha256({"schema": code_manifest["schema"], "files": code_manifest["files"]})
        == code_manifest["manifest_sha256"],
        "code manifest body digest mismatch",
    )
    require(
        all(
            isinstance(entry.get("sha256"), str)
            and len(entry["sha256"]) == 64
            for entry in code_manifest["files"]
        ),
        "code manifest contains a malformed digest",
    )
    field_roots = result["field_root_digest_by_world"]
    require(
        set(field_roots) == {str(seed) for seed in (*EXPECTED_TRAIN_WORLDS, *EXPECTED_VALIDATION_WORLDS)},
        "keyed-field world closure drifted",
    )

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
        require(
            set(report["train_rows_by_context"]) == {"12", "1", "2"},
            "training context closure drifted",
        )
        rungs = report["rungs"]
        require(set(rungs) == {str(rung) for rung in EXPECTED_RUNGS}, "rung report set drifted")
        for rung in EXPECTED_RUNGS:
            persisted = rungs[str(rung)]
            checkpoint = resolve_checkpoint(result_path, persisted["checkpoint"])
            require(
                sha256(checkpoint) == persisted["checkpoint_sha256"],
                f"checkpoint SHA-256 mismatch: init={initialization}, rung={rung}",
            )
            contexts = persisted["validation_contexts"]
            require(
                set(contexts) == {str(code) for code in EXPECTED_CONTEXTS},
                f"context set drifted: init={initialization}, rung={rung}",
            )
            for code, metrics in contexts.items():
                for field in (
                    "background_teacher_agreement",
                    "learned_teacher_agreement",
                    "student_change_rate",
                    "teacher_distribution_mean_entropy",
                    "student_distribution_mean_entropy",
                ):
                    require_finite_metric(metrics[field], f"rung {rung} context {code} {field}")
                for field in ("loss", "row_mean_kl", "gauge_mse"):
                    require_finite_metric(
                        metrics["softkl_measure"][field],
                        f"rung {rung} context {code} softkl {field}",
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
    expected_decision = "PASS_SOFTKL_GATE" if panel_pass else "FAIL_SOFTKL_GATE"
    require(result["decision"] == expected_decision, "overall decision mismatch")
    require(receipt["decision"] == expected_decision, "receipt decision mismatch")
    expected_next = (
        "AUTHORIZE_100EP_FIVE_ARM_PREREG_ONLY"
        if panel_pass
        else "STOP_C3_B402_ACTION_SHARED_STRUCTURALLY"
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
