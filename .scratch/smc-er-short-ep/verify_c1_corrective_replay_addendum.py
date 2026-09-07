#!/usr/bin/env python3
"""Independently verify the pre-reveal C1 canonical-TLE replay addendum."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src"))

from mcrl.env.tle import TleArchive  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    CANONICAL_PREREG,
    CANONICAL_PREREG_BYTE_SHA256,
    assert_ephemeris_matches_record,
)


ADDENDUM_SCHEMA = "smc-er-c1-canonical-tle-corrective-replay-addendum-v1"
VERIFICATION_SCHEMA = (
    "smc-er-c1-canonical-tle-corrective-replay-addendum-verification-v1"
)
CLAIM_CEILING = (
    "C1_SPECIALIST_PREFILL_CORPUS_AUTHORITY_ONLY_NOT_NEW_EVIDENCE_"
    "NOT_MAIN_ROUTING_NOT_EE_EFFICACY"
)
HISTORICAL_SOURCE_SHA256 = (
    "9eca695349a65694131c2d7ad4ec1318bc93aecbd7286c17d2e2ebaea3fba0cc"
)
CANONICAL_SOURCE_SHA256 = (
    "25463681f598f62f1486b5889ab1192c2192c97fb83565c609419f7cc77f6774"
)
CANONICAL_TLE_SHA256 = (
    "427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9"
)
CANONICAL_TLE_COUNT = 373
EXPECTED_BUILD_SOURCE_CHAIN = (
    HISTORICAL_SOURCE_SHA256,
    "cc4e8c880044f1ca8ab819793af4a5536583025705b58f8717462cf77ccb3ee2",
    CANONICAL_SOURCE_SHA256,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _mapping(value: Any, label: str, failures: list[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        failures.append(f"{label}: object required")
        return {}
    return value


def _bound_path(
    binding: Mapping[str, Any],
    path_field: str,
    digest_field: str,
    *,
    label: str,
    failures: list[str],
) -> Path | None:
    raw = binding.get(path_field)
    expected = binding.get(digest_field)
    path = Path(raw).expanduser().resolve() if isinstance(raw, str) and raw else None
    if path is None or not path.is_file():
        failures.append(f"{label}: bound file missing")
        return None
    if not isinstance(expected, str) or sha256_file(path) != expected:
        failures.append(f"{label}: SHA-256 mismatch")
        return None
    return path


def _json(path: Path, label: str, failures: list[str]) -> Mapping[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        failures.append(f"{label}: unreadable ({type(exc).__name__})")
        return {}
    return _mapping(payload, label, failures)


def verify_addendum(addendum_path: Path) -> dict[str, Any]:
    """Verify every predecessor, same-seed, TLE, Source, and corpus binding."""

    addendum_path = Path(addendum_path).expanduser().resolve()
    failures: list[str] = []
    addendum = _json(addendum_path, "addendum", failures)
    if addendum.get("schema") != ADDENDUM_SCHEMA:
        failures.append("addendum.schema: mismatch")
    if addendum.get("status") != "FROZEN_PRE_EFFICACY_SEED_REVEAL":
        failures.append("addendum.status: mismatch")
    if addendum.get("correction_kind") != "EXOGENOUS_CANONICAL_TLE_AUTHORITY_REPLAY":
        failures.append("addendum.correction_kind: mismatch")
    if addendum.get("claim_ceiling") != CLAIM_CEILING:
        failures.append("addendum.claim_ceiling: mismatch")

    attestations = _mapping(addendum.get("attestations"), "attestations", failures)
    expected_attestations = {
        "algorithm_or_threshold_changed": False,
        "corpus_selection_rule_changed": False,
        "new_build_seed_or_sample_selected": False,
        "outcome_conditioned_selection": False,
        "previously_revealed_build_seeds_reused": True,
        "original_frozen_build_spec_preserved": True,
    }
    if dict(attestations) != expected_attestations:
        failures.append("attestations: exact correction boundary mismatch")

    frozen = _mapping(addendum.get("frozen_build_spec"), "frozen_build_spec", failures)
    spec_path = _bound_path(
        frozen, "path", "sha256", label="frozen_build_spec", failures=failures
    )
    if frozen.get("declared_source_gate_result_sha256") != HISTORICAL_SOURCE_SHA256:
        failures.append("frozen_build_spec: historical predecessor mismatch")
    if spec_path is not None:
        spec_text = spec_path.read_text(encoding="utf-8")
        if HISTORICAL_SOURCE_SHA256 not in spec_text:
            failures.append("frozen_build_spec: predecessor is not declared in bytes")

    supersession = _mapping(addendum.get("supersession"), "supersession", failures)
    if (
        supersession.get("superseded_source_gate_result_sha256")
        != HISTORICAL_SOURCE_SHA256
        or supersession.get("canonical_replay_source_gate_result_sha256")
        != CANONICAL_SOURCE_SHA256
        or supersession.get("scope") != "SOURCE_AND_CORPUS_AUTHORITY_REPLAY_ONLY"
        or not isinstance(supersession.get("reason"), str)
        or not supersession.get("reason")
    ):
        failures.append("supersession: invalid authority-only correction")

    prereg_binding = _mapping(
        addendum.get("canonical_preregistration"),
        "canonical_preregistration",
        failures,
    )
    prereg_path = _bound_path(
        prereg_binding,
        "path",
        "sha256",
        label="canonical_preregistration",
        failures=failures,
    )
    if (
        prereg_path is not None
        and (
            prereg_path != Path(CANONICAL_PREREG).resolve()
            or prereg_binding.get("sha256") != CANONICAL_PREREG_BYTE_SHA256
        )
    ):
        failures.append("canonical_preregistration: noncanonical authority")

    tle_binding = _mapping(
        addendum.get("canonical_tle_archive"), "canonical_tle_archive", failures
    )
    tle_raw = tle_binding.get("path")
    tle_path = (
        Path(tle_raw).expanduser().resolve()
        if isinstance(tle_raw, str) and tle_raw
        else None
    )
    ephemeris: Mapping[str, Any] = {}
    if tle_path is None or not tle_path.is_dir() or prereg_path is None:
        failures.append("canonical_tle_archive: missing")
    else:
        try:
            ephemeris = assert_ephemeris_matches_record(
                read_prereg(prereg_path), archive=TleArchive(tle_path)
            )
        except Exception as exc:
            failures.append(
                "canonical_tle_archive: prereg replay failed "
                f"({type(exc).__name__}: {exc})"
            )
        else:
            if (
                tle_binding.get("file_set_sha256") != CANONICAL_TLE_SHA256
                or tle_binding.get("file_count") != CANONICAL_TLE_COUNT
                or ephemeris.get("file_set_sha256") != CANONICAL_TLE_SHA256
                or ephemeris.get("archive", {}).get("file_count")
                != CANONICAL_TLE_COUNT
            ):
                failures.append("canonical_tle_archive: exact file set mismatch")

    source_binding = _mapping(
        addendum.get("canonical_source_gate"), "canonical_source_gate", failures
    )
    source_path = _bound_path(
        source_binding,
        "result_path",
        "result_sha256",
        label="canonical_source_gate.result",
        failures=failures,
    )
    source_seed_path = _bound_path(
        source_binding,
        "source_seed_manifest_path",
        "source_seed_manifest_sha256",
        label="canonical_source_gate.seed_manifest",
        failures=failures,
    )
    source = _json(source_path, "canonical_source_gate.result", failures) if source_path else {}
    source_authority = _mapping(
        source.get("authority"), "canonical_source_gate.authority", failures
    )
    if (
        source_binding.get("result_sha256") != CANONICAL_SOURCE_SHA256
        or source.get("status") != "PASS"
        or source.get("decision") != "PASS_TO_C1_CONSUMER_GATE"
        or source.get("claim_ceiling")
        != "SOURCE_QUALITY_ONLY_NOT_LEARNING_NOT_MAIN_ROUTING_NOT_EE_EFFICACY"
        or source_authority.get("prereg_sha256") != CANONICAL_PREREG_BYTE_SHA256
        or source_authority.get("tle_file_set_sha256") != CANONICAL_TLE_SHA256
        or source_authority.get("tle_file_count") != CANONICAL_TLE_COUNT
        or source_seed_path is None
        or source_authority.get("seed_manifest_sha256")
        != source_binding.get("source_seed_manifest_sha256")
    ):
        failures.append("canonical_source_gate: result authority mismatch")

    lineage = _mapping(addendum.get("build_seed_lineage"), "build_seed_lineage", failures)
    manifest_bindings = lineage.get("manifests")
    if not isinstance(manifest_bindings, list) or len(manifest_bindings) != 3:
        failures.append("build_seed_lineage: exactly three manifests required")
        manifest_bindings = []
    seed_lists: list[list[int]] = []
    manifest_paths: list[Path] = []
    checkpoint_digests: list[str] = []
    for index, item in enumerate(manifest_bindings):
        binding = _mapping(item, f"build_seed_lineage.manifests[{index}]", failures)
        path = _bound_path(
            binding,
            "path",
            "sha256",
            label=f"build_seed_lineage.manifests[{index}]",
            failures=failures,
        )
        if path is None:
            continue
        manifest_paths.append(path)
        payload = _json(path, f"build_seed_manifest[{index}]", failures)
        seeds = payload.get("seeds")
        if (
            payload.get("schema") != "smc-er-c1-exp-build-seeds-v1"
            or payload.get("status") != "frozen"
            or spec_path is None
            or payload.get("spec_sha256") != frozen.get("sha256")
            or payload.get("source_gate_result_sha256")
            != EXPECTED_BUILD_SOURCE_CHAIN[index]
            or binding.get("source_gate_result_sha256")
            != EXPECTED_BUILD_SOURCE_CHAIN[index]
            or not isinstance(seeds, list)
            or len(seeds) != 5
            or any(type(seed) is not int or seed < 0 for seed in seeds)
            or len(set(seeds)) != 5
        ):
            failures.append(f"build_seed_manifest[{index}]: malformed authority")
            continue
        seed_lists.append(list(map(int, seeds)))
        checkpoint_digests.append(str(payload.get("checkpoint_sha256")))
        if index > 0:
            predecessor = manifest_bindings[index - 1]
            predecessor_path = Path(str(payload.get("predecessor_seed_manifest_path", ""))).expanduser().resolve()
            if (
                predecessor_path != Path(str(predecessor.get("path"))).expanduser().resolve()
                or payload.get("predecessor_seed_manifest_sha256")
                != predecessor.get("sha256")
            ):
                failures.append(f"build_seed_manifest[{index}]: predecessor mismatch")

    ordered_seed_sha256: str | None = None
    if len(seed_lists) == 3:
        ordered_seed_sha256 = hashlib.sha256(_canonical_bytes(seed_lists[0])).hexdigest()
        if seed_lists[1] != seed_lists[0] or seed_lists[2] != seed_lists[0]:
            failures.append("build_seed_lineage: ordered seed lists differ")
        if lineage.get("ordered_seed_list_sha256") != ordered_seed_sha256:
            failures.append("build_seed_lineage: ordered seed digest mismatch")
        if len(set(checkpoint_digests)) != 1:
            failures.append("build_seed_lineage: checkpoint authority differs")
        if spec_path is not None:
            digest_bytes = bytes.fromhex(str(frozen.get("sha256")))
            derived = [
                int.from_bytes(digest_bytes[offset : offset + 4], "big")
                for offset in range(0, 20, 4)
            ]
            if seed_lists[0] != derived:
                failures.append("build_seed_lineage: original deterministic derivation mismatch")

    corpus_binding = _mapping(
        addendum.get("canonical_corpus"), "canonical_corpus", failures
    )
    corpus_manifest_path = _bound_path(
        corpus_binding,
        "manifest_path",
        "manifest_sha256",
        label="canonical_corpus.manifest",
        failures=failures,
    )
    corpus_path = _bound_path(
        corpus_binding,
        "corpus_path",
        "corpus_sha256",
        label="canonical_corpus.bytes",
        failures=failures,
    )
    corpus_verification_path = _bound_path(
        corpus_binding,
        "verification_path",
        "verification_sha256",
        label="canonical_corpus.verification",
        failures=failures,
    )
    corpus_manifest = (
        _json(corpus_manifest_path, "canonical_corpus.manifest", failures)
        if corpus_manifest_path
        else {}
    )
    corpus_authority = _mapping(
        corpus_manifest.get("authority"), "canonical_corpus.authority", failures
    )
    corpus_verification = (
        _json(corpus_verification_path, "canonical_corpus.verification", failures)
        if corpus_verification_path
        else {}
    )
    canonical_build_manifest = manifest_bindings[-1] if manifest_bindings else {}
    if (
        corpus_manifest.get("status") != "complete"
        or corpus_manifest.get("claim_ceiling")
        != "C1_SPECIALIST_PREFILL_ONLY_NEVER_MAIN"
        or corpus_path is None
        or corpus_manifest.get("corpus_sha256") != corpus_binding.get("corpus_sha256")
        or Path(str(corpus_manifest.get("corpus_path", ""))).expanduser().resolve()
        != corpus_path
        or corpus_authority.get("build_spec_sha256") != frozen.get("sha256")
        or corpus_authority.get("source_gate_result_sha256") != CANONICAL_SOURCE_SHA256
        or corpus_authority.get("seed_manifest_sha256")
        != canonical_build_manifest.get("sha256")
        or corpus_authority.get("prereg_sha256") != CANONICAL_PREREG_BYTE_SHA256
        or corpus_authority.get("tle_file_set_sha256") != CANONICAL_TLE_SHA256
        or corpus_authority.get("tle_file_count") != CANONICAL_TLE_COUNT
    ):
        failures.append("canonical_corpus: manifest authority mismatch")
    if (
        corpus_verification.get("status") != "PASS"
        or corpus_verification.get("manifest_sha256")
        != corpus_binding.get("manifest_sha256")
        or corpus_verification.get("corpus_sha256")
        != corpus_binding.get("corpus_sha256")
        or corpus_verification.get("tle_file_set_sha256") != CANONICAL_TLE_SHA256
        or corpus_verification.get("enters_main") is not False
        or corpus_verification.get("claim_ceiling")
        != "C1_SPECIALIST_PREFILL_ONLY_NEVER_MAIN"
    ):
        failures.append("canonical_corpus: verification authority mismatch")

    adjudication = _mapping(addendum.get("adjudication"), "adjudication", failures)
    expected_adjudication = {
        "original_spec_predecessor_is_historical_not_current": True,
        "canonical_source_result_is_the_only_current_corpus_predecessor": True,
        "same_seed_replay_is_not_an_independent_sample": True,
        "existing_corpus_bytes_are_retained": True,
        "screen_freeze_requires_this_addendum_and_an_exact_independent_verification_receipt": True,
    }
    if dict(adjudication) != expected_adjudication:
        failures.append("adjudication: exact boundary mismatch")

    unique = list(dict.fromkeys(failures))
    return {
        "schema": VERIFICATION_SCHEMA,
        "status": "PASS" if not unique else "FAIL",
        "failures": unique,
        "addendum_path": str(addendum_path),
        "addendum_sha256": sha256_file(addendum_path) if addendum_path.is_file() else None,
        "frozen_build_spec_sha256": frozen.get("sha256"),
        "historical_source_gate_result_sha256": HISTORICAL_SOURCE_SHA256,
        "canonical_source_gate_result_sha256": CANONICAL_SOURCE_SHA256,
        "canonical_corpus_manifest_sha256": corpus_binding.get("manifest_sha256"),
        "canonical_corpus_sha256": corpus_binding.get("corpus_sha256"),
        "ordered_seed_list_sha256": ordered_seed_sha256,
        "build_seed_manifest_count": len(manifest_paths),
        "build_seed_count": len(seed_lists[0]) if seed_lists else 0,
        "tle_file_set_sha256": ephemeris.get("file_set_sha256"),
        "tle_file_count": ephemeris.get("archive", {}).get("file_count"),
        "new_seed_or_sample_selected": False,
        "outcome_conditioned_selection": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--addendum", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    verification = verify_addendum(args.addendum)
    args.output.write_text(
        json.dumps(verification, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(verification, sort_keys=True))
    return 0 if verification["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
