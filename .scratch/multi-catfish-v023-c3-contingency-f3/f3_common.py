"""Shared fail-closed bindings for the pre-outcome V0.23 C3 F3 package."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SRC = REPO / "src"
F2_DIR = REPO / ".scratch" / "multi-catfish-v023-c3-contingency-f2"
R7_DIR = REPO / ".scratch" / "multi-catfish-v023-r7-launch-ready"
for _path in (SRC, F2_DIR, R7_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_v023_c3_contingency_f2 as f2  # noqa: E402
from mcrl.algorithms.ee_axis_lcsrs_c3_head import LCSRSC3HeadConfig  # noqa: E402
from mcrl.runtime.ee_axis_lcsrs_c3_state import (  # noqa: E402
    LCSRS_C3_CONFIG_SHA256,
    LCSRS_C3_SCHEMA_SHA256,
)


SCHEMA = "multi-catfish-mcrl-v023-c3-contingency-f3-v1"
PREFLIGHT_SCHEMA = f"{SCHEMA}-preflight-manifest"
LAUNCH_AUTHORITY_SCHEMA = f"{SCHEMA}-launch-authority"
SOURCE_CLAIM_CEILING = "TRAIN_DEVELOPMENT_C3_CONTINGENCY_F3_SOURCE_NO_EFFICACY_NO_TEST"
LEARNER_CLAIM_CEILING = "TRAIN_DEVELOPMENT_C3_CONTINGENCY_F3_LEARNER_SCREEN_NO_EFFICACY_NO_TEST"
DESIGN_CLAIM_CEILING = (
    "TRAIN_DEVELOPMENT_C3_F3_SOURCE_LEARNER_COMPOSITION_GATE_"
    "NO_TEST_NO_EPISODE_TRAINING_NO_EFFICACY"
)
OBSERVABILITY_STATEMENT = "F3 passing is observability, not efficacy"

WORLDS = f2.WORLDS
LINEAGES = f2.LINEAGES
ANCHORS = tuple(range(1, 10))
ARMS = ("INFORMED", "NEUTRAL")
CHECKPOINTS = tuple(range(0, 2001, 100))
UPDATES = 2000
BATCH_SIZE = 256
SIGN_THRESHOLD = 0.02
MIN_CLASS_ROWS = 24
MEAN_INFORMED_BACC_MIN = 0.60
BACC_GAP_MIN = 0.05
MEAN_INFORMED_SPEARMAN_MIN = 0.20
INFORMED_WORLD_WINS_MIN = 3
PER_SEED_NONNEGATIVE_WORLDS_MIN = 3
PLACEBO_COVERAGE_MIN = 0.80
KAPPA_BITS = f2.f1.KAPPA_BITS
PROCESS_ENVIRONMENT = {
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
}

SEED_DOMAINS = tuple(
    f"MCRL_V023_C3_F3_LEARNER_SEED_{index}_V1" for index in range(1, 4)
)

Q3_CONFIG_RECORD = {
    "action_dim": 28,
    "action_context_dim": 29,
    "token_dim": 38,
    "hidden_layers": [64, 64],
    "activation": "relu",
    "output_unit": "normalized_bits_per_kappa",
    "config_sha256": "c406a6a2a0da78a855c8f850c45803cfa1763a3e7e40823693b39207f14c3324",
}


class F3Error(RuntimeError):
    """An F3 binding, artifact, fit, or decision failed closed."""


class F3NotAdmitted(F3Error):
    """F2 supplied no valid D/F survivor for F3."""


def canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii") + b"\n"
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise F3Error("value is not finite canonical ASCII JSON") from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value).rstrip(b"\n")).hexdigest()


def file_sha256(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise F3Error(f"expected regular file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise F3Error(f"{field} must be a lowercase SHA-256 digest")
    return value


def load_json(path: Path, *, field: str) -> dict[str, Any]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise F3Error(f"{field} is missing or symlinked")
    raw = source.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise F3Error(f"{field} is not canonical ASCII JSON") from error
    if not isinstance(payload, dict) or raw not in (
        canonical_bytes(payload),
        canonical_bytes(payload).rstrip(b"\n"),
    ):
        raise F3Error(f"{field} is not a canonical JSON object")
    return payload


def write_once_bytes(path: Path, payload: bytes, *, readonly: bool = True) -> str:
    target = Path(path)
    if target.exists() or target.is_symlink():
        raise F3Error(f"refusing to overwrite write-once path: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(target, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        raise
    if readonly:
        target.chmod(0o444)
    return file_sha256(target)


def write_once_json(path: Path, payload: Mapping[str, object]) -> str:
    return write_once_bytes(path, canonical_bytes(dict(payload)))


def derive_seed(domain: str) -> int:
    if domain not in SEED_DOMAINS:
        raise F3Error("learner seed domain is outside the frozen three-domain set")
    return int.from_bytes(hashlib.sha256(domain.encode("ascii")).digest()[:8], "big") & (
        (1 << 63) - 1
    )


def learner_seeds() -> tuple[int, int, int]:
    return tuple(derive_seed(domain) for domain in SEED_DOMAINS)  # type: ignore[return-value]


def model_bindings() -> dict[str, object]:
    config = LCSRSC3HeadConfig()
    observed = {
        "action_dim": config.action_dim,
        "action_context_dim": config.action_context_dim,
        "token_dim": config.token_dim,
        "hidden_layers": list(config.hidden_layers),
        "activation": config.activation,
        "output_unit": config.output_unit,
        "config_sha256": config.config_sha256,
    }
    if observed != Q3_CONFIG_RECORD or LCSRS_C3_CONFIG_SHA256 != Q3_CONFIG_RECORD["config_sha256"]:
        raise F3Error("copied Q3 model record disagrees with the imported structured head")
    return {
        "q3": observed,
        "c3_view_schema_sha256": LCSRS_C3_SCHEMA_SHA256,
        "learner_seed_domains": list(SEED_DOMAINS),
        "learner_seeds": list(learner_seeds()),
    }


def panel_bindings() -> dict[str, object]:
    return {
        "worlds": list(WORLDS),
        "lineages": list(LINEAGES),
        "anchors": list(ANCHORS),
        "fold_rule": "LEAVE_ONE_WORLD_OUT_ALL_THREE_LINEAGES",
        "arms": list(ARMS),
        "updates_per_fit": UPDATES,
        "checkpoints": list(CHECKPOINTS),
        "batch_size": BATCH_SIZE,
        "loss": {
            "name": "MEAN_SQUARED_ERROR_LEGAL_NONREFERENCE_CELLS",
            "provenance": "panel_adaptation",
        },
        "fit_count": len(WORLDS) * len(learner_seeds()) * len(ARMS),
        "total_updates": len(WORLDS) * len(learner_seeds()) * len(ARMS) * UPDATES,
        "kappa_bits_hex": KAPPA_BITS.hex(),
        "split": "TRAIN_DEVELOPMENT",
        "test_split_opened": False,
        "episode_training": False,
        "process_environment": PROCESS_ENVIRONMENT,
    }


def threshold_bindings() -> dict[str, object]:
    return {
        "r7_copy": {
            "sign_eligibility_absolute_target_min": SIGN_THRESHOLD,
            "informed_mean_spearman_min": MEAN_INFORMED_SPEARMAN_MIN,
            "informed_mean_balanced_accuracy_min": MEAN_INFORMED_BACC_MIN,
            "informed_minus_neutral_balanced_accuracy_min": BACC_GAP_MIN,
            "positive_rows_min": MIN_CLASS_ROWS,
            "negative_rows_min": MIN_CLASS_ROWS,
            "neutral_permutation_coverage_per_fold_min": PLACEBO_COVERAGE_MIN,
        },
        "panel_adaptation": {
            "informed_over_neutral_mean_seed_spearman_wins_min": INFORMED_WORLD_WINS_MIN,
            "per_seed_nonnegative_spearman_worlds_min": PER_SEED_NONNEGATIVE_WORLDS_MIN,
        },
        "composition": {
            "applicability": (
                "D/F are unilateral continuous corrections, not closure pairs; "
                "closure-pair diagnostics are nondecisive and zero selected-11 cannot veto"
            ),
            "r7_copy": {"informed_service_per_world_margin": 0.01},
            "panel_adaptation": {
                "teacher_ee_above_base_worlds_min": 2,
                "informed_ee_above_base_worlds_min": 2,
            },
        },
    }


def validate_process_environment(environment: Mapping[str, str]) -> dict[str, str]:
    observed = {key: environment.get(key) for key in PROCESS_ENVIRONMENT}
    if observed != PROCESS_ENVIRONMENT:
        raise F3Error("deterministic BLAS/OpenMP process environment drifted")
    return dict(PROCESS_ENVIRONMENT)


def _repo_record(path: Path) -> str:
    resolved = Path(path).resolve()
    return (
        resolved.relative_to(REPO.resolve()).as_posix()
        if resolved.is_relative_to(REPO.resolve())
        else str(resolved)
    )


def authority_keys() -> frozenset[str]:
    return frozenset(
        {
            "schema",
            "status",
            "claim_ceiling",
            "preflight_manifest",
            "f2_terminal_receipt",
            "survivor",
            "test_split_opened",
            "episode_training",
            "efficacy_claim",
        }
    )


def validate_f2_terminal_receipt(path: Path, *, expected_sha256: str, survivor: str) -> dict[str, Any]:
    source = Path(path)
    if survivor not in {"D", "F"}:
        raise F3NotAdmitted("F3_NOT_ADMITTED: survivor must be D or F")
    if file_sha256(source) != digest(expected_sha256, field="F2 terminal receipt sha256"):
        raise F3Error("sealed F2 terminal receipt digest disagrees")
    if source.stat().st_mode & 0o222:
        raise F3Error("sealed F2 terminal receipt remains writable")
    receipt = load_json(source, field="sealed F2 terminal receipt")
    required_outcome = f"F2_PASS_{survivor}"
    if receipt.get("outcome") in {"F2_NO_SUPPORT", None}:
        raise F3NotAdmitted("F3_NOT_ADMITTED: sealed F2 result has no survivor")
    if (
        receipt.get("schema") != f2.TERMINAL_RECEIPT_SCHEMA
        or receipt.get("status") != "COMPLETE"
        or receipt.get("outcome") != required_outcome
        or receipt.get("claim_ceiling") != f2.CLAIM_CEILING
        or receipt.get("panel_bindings") != f2.panel_bindings()
        or receipt.get("lineage_authorities") != f2.lineage_authority_bindings()
        or receipt.get("formula_digests") != f2.formula_digests()
        or receipt.get("priority_applied") != list(f2.CANDIDATE_ORDER)
        or any(
            receipt.get(field) is not False
            for field in ("test_split_opened", "episode_training", "learner_update", "efficacy_claim")
        )
    ):
        raise F3Error("sealed F2 terminal receipt semantics disagree")
    preflight_sha = digest(receipt.get("preflight_manifest_sha256"), field="F2 preflight sha256")
    f1_binding = receipt.get("f1_result")
    if not isinstance(f1_binding, Mapping):
        raise F3Error("sealed F2 terminal receipt lacks F1 provenance")
    f2._validate_existing_terminal(
        source,
        preflight_sha256=preflight_sha,
        f1_binding=f1_binding,
    )
    return receipt


def validate_launch_authority(
    path: Path,
    *,
    preflight_path: Path,
    preflight_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = load_json(path, field="F3 launch authority")
    if set(payload) != authority_keys():
        raise F3Error("launch authority keys differ from the exact F3 schema")
    preflight = payload.get("preflight_manifest")
    f2_record = payload.get("f2_terminal_receipt")
    if not isinstance(preflight, Mapping) or set(preflight) != {"path", "sha256"}:
        raise F3Error("launch authority preflight binding has non-exact keys")
    if not isinstance(f2_record, Mapping) or set(f2_record) != {"path", "sha256"}:
        raise F3Error("launch authority F2 binding has non-exact keys")
    survivor = payload.get("survivor")
    if survivor not in {"D", "F"}:
        raise F3NotAdmitted("F3_NOT_ADMITTED: launch authority has no D/F survivor")
    if (
        payload.get("schema") != LAUNCH_AUTHORITY_SCHEMA
        or payload.get("status") != "FROZEN_LAUNCH_AUTHORITY"
        or payload.get("claim_ceiling") != DESIGN_CLAIM_CEILING
        or dict(preflight)
        != {
            "path": _repo_record(preflight_path),
            "sha256": digest(preflight_sha256, field="F3 preflight sha256"),
        }
        or any(
            payload.get(field) is not False
            for field in ("test_split_opened", "episode_training", "efficacy_claim")
        )
    ):
        raise F3Error("launch authority does not pin the exact F3 boundaries")
    f2_path = f2_record.get("path")
    if not isinstance(f2_path, str) or not Path(f2_path).is_absolute():
        raise F3Error("launch authority F2 receipt path must be absolute")
    receipt = validate_f2_terminal_receipt(
        Path(f2_path),
        expected_sha256=digest(f2_record.get("sha256"), field="F2 terminal receipt sha256"),
        survivor=str(survivor),
    )
    return payload, receipt


def expected_code_bindings() -> list[dict[str, str]]:
    roles = (
        ("common", HERE / "f3_common.py"),
        ("neutral_rule", HERE / "f3_neutral_rule.py"),
        ("source_builder", HERE / "build_f3_source_artifact.py"),
        ("learner_runner", HERE / "run_v023_c3_contingency_f3_learner_screen.py"),
        ("preflight_builder", HERE / "build_f3_preflight_manifest.py"),
        ("tests", HERE / "test_v023_c3_contingency_f3.py"),
        ("readme", HERE / "README.md"),
        ("f2_runner_import", F2_DIR / "run_v023_c3_contingency_f2.py"),
        ("r7_metric_import", R7_DIR / "r7_balanced_successor_gate.py"),
        ("r7_source_import", R7_DIR / "v023_lcsrs_source_adapter.py"),
        ("structured_q3_head", REPO / "src/mcrl/algorithms/ee_axis_lcsrs_c3_head.py"),
        ("c3_view", REPO / "src/mcrl/runtime/ee_axis_lcsrs_c3_state.py"),
        ("r7_placebo", REPO / "src/mcrl/runtime/ee_axis_lcsrs_c3_placebo.py"),
    )
    return [
        {"role": role, "path": _repo_record(path), "sha256": file_sha256(path)}
        for role, path in roles
    ]


def authority_document_bindings() -> list[dict[str, str]]:
    roles = (
        (
            "successor_common_brief",
            REPO / ".scratch/multi-catfish-v023-c1c2-successor/SUCCESSOR-BRIEF-COMMON-2026-09-07.md",
        ),
        (
            "preoutcome_f3_ladder",
            REPO / ".scratch/multi-catfish-v023-c3-observability/V023-C3-RAPID-CONTINGENCY-LADDER-PREOUTCOME-2026-09-06.md",
        ),
        (
            "binding_f3_design_memo",
            REPO / ".scratch/multi-catfish-v023-controller-handoff-20260907/DESIGN-F3-LEARNER-SCREEN-PREOUTCOME-R2-CODEX-GPT6-ASTRA-2026-09-07.md",
        ),
        (
            "r7_balanced_contract",
            REPO / "docs/MULTI-CATFISH-MCRL-V023-LC-SRS-SUCCESSOR-GATE-CONTRACT-R7-BALANCED-2026-09-06.md",
        ),
        (
            "q3_model_config_record",
            REPO / ".scratch/multi-catfish-v023-100e-screen-preoutcome-v2/V023-100E-MODEL-CONFIG.json",
        ),
        (
            "c1c2_neutral_materialization_readme",
            REPO / ".scratch/multi-catfish-v023-c1c2-neutral-materialization/README.md",
        ),
        (
            "c1c2_neutral_adapter_readme",
            REPO / ".scratch/multi-catfish-v023-c1c2-neutral-adapters/README.md",
        ),
    )
    return [
        {"role": role, "path": _repo_record(path), "sha256": file_sha256(path)}
        for role, path in roles
    ]


def static_bindings() -> dict[str, object]:
    return {
        "panel": panel_bindings(),
        "model": model_bindings(),
        "thresholds": threshold_bindings(),
        "f2_preflight": {
            "path": _repo_record(f2.DEFAULT_PREFLIGHT),
            "sha256": f2.file_sha256(f2.DEFAULT_PREFLIGHT),
        },
        "f2_tape_schema": f2.UNIT_TAPE_SCHEMA,
        "f2_terminal_receipt_schema": f2.TERMINAL_RECEIPT_SCHEMA,
        "observability_statement": OBSERVABILITY_STATEMENT,
        "authority_documents": authority_document_bindings(),
    }


def validate_preflight_manifest(path: Path) -> tuple[dict[str, Any], str]:
    payload = load_json(path, field="F3 preflight manifest")
    expected = {
        "schema": PREFLIGHT_SCHEMA,
        "status": "FROZEN_PRE_OUTCOME",
        "claim_ceiling": DESIGN_CLAIM_CEILING,
        **static_bindings(),
        "code_files": expected_code_bindings(),
    }
    if payload != expected:
        raise F3Error("F3 preflight manifest disagrees with exact code/bindings")
    sha = file_sha256(path)
    sidecar = Path(path).with_suffix(".sha256")
    if sidecar.is_symlink() or not sidecar.is_file():
        raise F3Error("F3 preflight digest sidecar is missing or symlinked")
    if sidecar.read_text(encoding="ascii").split() != [sha, Path(path).name]:
        raise F3Error("F3 preflight digest sidecar disagrees")
    return payload, sha


__all__ = [name for name in globals() if name.isupper()] + [
    "F3Error",
    "F3NotAdmitted",
    "canonical_bytes",
    "canonical_sha256",
    "file_sha256",
    "digest",
    "load_json",
    "write_once_bytes",
    "write_once_json",
    "derive_seed",
    "learner_seeds",
    "model_bindings",
    "panel_bindings",
    "threshold_bindings",
    "validate_process_environment",
    "validate_f2_terminal_receipt",
    "validate_launch_authority",
    "expected_code_bindings",
    "authority_document_bindings",
    "static_bindings",
    "validate_preflight_manifest",
    "f2",
]
