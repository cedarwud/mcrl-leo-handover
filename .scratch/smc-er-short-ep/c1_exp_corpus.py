"""Fail-closed loader for the immutable C1 EXP/control replay corpus.

This module is deliberately independent of the corpus builder.  It verifies
the sealed manifest and every array surface before converting the selected
high/mid branch into :class:`AtomicBundle` objects.  Corpus bundles may prefill
the C1 specialist only; this module has no Main-replay API.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "src"))

from smc_er_core import AtomicBundle  # noqa: E402
from mcrl.env.action_contract import NO_OP_ACTION  # noqa: E402
from mcrl.env.tle import TleArchive  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    CANONICAL_PREREG,
    CANONICAL_PREREG_BYTE_SHA256,
    assert_ephemeris_matches_record,
)


MANIFEST_SCHEMA = "smc-er-c1-exp-corpus-manifest-v2"
LEGACY_MANIFEST_SCHEMA = "smc-er-c1-exp-corpus-manifest-v1"
REPOSITORY_PATH_BINDING = "repository_relative_posix_v1"
RUNTIME_TLE_ROOT_BINDING = "runtime_argument"
CANONICAL_CHECKPOINT_RELATIVE = (
    "artifacts/training-2026-08-25-rerun01/main/final-checkpoint.pt"
)
CANONICAL_SOURCE_GATE_RESULT_RELATIVE = (
    "artifacts/smc-er-c1-authority-20260828/"
    "smc-er-c1-source-gate-a-canonical-tle-20260828-v3/"
    "c1-source-gate-a-result.json"
)
CANONICAL_SEED_MANIFEST_RELATIVE = (
    ".scratch/smc-er-short-ep/c1-exp-build-seeds-canonical-tle-v3.json"
)
CANONICAL_PREREG_RELATIVE = "artifacts/PREREG-FROZEN-2026-08-25-R2.json"
SEED_SCHEMA = "smc-er-c1-exp-build-seeds-v1"
SOURCE_GATE_SCHEMA = "smc-er-c1-source-gate-a-result-v1"
EXPECTED_BRANCHES = ("local", "control")
EXPECTED_USERS = 100
EXPECTED_BUNDLES = 50
EXPECTED_STEPS = 10
EXPECTED_STRATA = {"high": 17, "mid": 17, "low": 16}
EXPECTED_MATCHED_PREFILL = 31
EXPECTED_MATCHED_PREFILL_STRATA = {"high": 17, "mid": 14}
ARRAY_FIELDS = (
    "bundle_ids",
    "seeds",
    "steps",
    "strata",
    "states",
    "actions",
    "rewards",
    "next_states",
    "masks",
    "next_masks",
    "dones",
    "probabilities",
    "physical_norad_ids",
    "physical_cell_ids",
    "system_throughput_bps",
    "system_power_w",
    "system_ee_bits_per_j",
    "served",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _is_digest(value: object) -> bool:
    return bool(
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _resolve_repository_path(
    repo: Path,
    raw: object,
    *,
    field: str,
    kind: str,
) -> Path:
    """Resolve one strict repository-relative POSIX authority path."""

    if not isinstance(raw, str) or not raw or raw.strip() != raw:
        raise RuntimeError(
            f"C1 corpus authority {field} must be repository-relative"
        )
    relative = PurePosixPath(raw)
    if (
        relative.is_absolute()
        or "\\" in raw
        or not relative.parts
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise RuntimeError(
            f"C1 corpus authority {field} must be repository-relative"
        )
    root = Path(repo).expanduser().resolve()
    path = (root / Path(*relative.parts)).resolve()
    if not path.is_relative_to(root):
        raise RuntimeError(f"C1 corpus authority {field} escapes repository")
    if kind == "file" and not path.is_file():
        raise RuntimeError(f"C1 corpus authority {field} is unavailable")
    if kind == "dir" and not path.is_dir():
        raise RuntimeError(f"C1 corpus authority {field} is unavailable")
    if kind not in {"file", "dir"}:
        raise ValueError(f"unsupported C1 authority path kind: {kind}")
    return path


def _resolve_authority_path(
    manifest_path: Path,
    raw: object,
    *,
    field: str,
    repo: Path = REPO,
    fallback_relative: str | None = None,
) -> Path:
    if not isinstance(raw, str) or not raw:
        raise RuntimeError(f"C1 corpus authority {field} is missing")
    if fallback_relative is not None:
        return _resolve_repository_path(
            repo,
            fallback_relative,
            field=field,
            kind="file",
        )
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = manifest_path.parent / path
    path = path.resolve()
    if not path.is_file():
        raise RuntimeError(f"C1 corpus authority {field} is unavailable")
    return path


def _resolve_authority_dir(manifest_path: Path, raw: object, *, field: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise RuntimeError(f"C1 corpus authority {field} is missing")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = manifest_path.parent / path
    path = path.resolve()
    if not path.is_dir():
        raise RuntimeError(f"C1 corpus authority {field} is unavailable")
    return path


def _require_bound_file(
    manifest_path: Path,
    authority: Mapping[str, Any],
    *,
    path_field: str,
    digest_field: str,
    repo: Path = REPO,
    fallback_relative: str | None = None,
    repository_relative: bool = False,
) -> Path:
    if repository_relative:
        path = _resolve_repository_path(
            repo,
            authority.get(path_field),
            field=path_field,
            kind="file",
        )
    else:
        path = _resolve_authority_path(
            manifest_path,
            authority.get(path_field),
            field=path_field,
            repo=repo,
            fallback_relative=fallback_relative,
        )
    expected = authority.get(digest_field)
    if not _is_digest(expected) or sha256_file(path) != expected:
        raise RuntimeError(f"C1 corpus authority {digest_field} drift")
    return path


def _expected_strata(ee: np.ndarray, seeds: np.ndarray, steps: np.ndarray, ids: np.ndarray) -> np.ndarray:
    ordered = sorted(
        range(EXPECTED_BUNDLES),
        key=lambda index: (
            -float(ee[index]),
            int(seeds[index]),
            int(steps[index]),
            str(ids[index]),
        ),
    )
    expected = np.empty(EXPECTED_BUNDLES, dtype="U8")
    for rank, index in enumerate(ordered):
        expected[index] = "high" if rank < 17 else "mid" if rank < 34 else "low"
    return expected


@dataclass(frozen=True)
class VerifiedC1Corpus:
    manifest_path: Path
    corpus_path: Path
    manifest_sha256: str
    corpus_sha256: str
    checkpoint_sha256: str
    tle_file_set_sha256: str
    state_dim: int
    action_dim: int
    arrays: Mapping[str, np.ndarray]

    def prefill_bundles(self, *, informed: bool) -> tuple[AtomicBundle, ...]:
        """Return the exact paired high/mid specialist-only contexts.

        The source and neutral corpora each contain 34 branch-local high/mid
        rows, but six of those rows do not share the same ``(seed, step)``
        context across branches.  The efficacy carrier uses the 31-row
        intersection so treatment and neutral prefill differ only in executed
        branch content, never in the exogenous context denominator.
        """

        branch = "local" if informed else "control"
        strata = self.arrays[f"{branch}_strata"]
        qualified: dict[str, dict[tuple[int, int], int]] = {}
        for candidate_branch in EXPECTED_BRANCHES:
            prefix = candidate_branch + "_"
            candidate_strata = self.arrays[prefix + "strata"]
            indices = np.flatnonzero(np.isin(candidate_strata, ("high", "mid")))
            qualified[candidate_branch] = {
                (
                    int(self.arrays[prefix + "seeds"][index]),
                    int(self.arrays[prefix + "steps"][index]),
                ): int(index)
                for index in indices
            }
        matched_contexts = sorted(
            set(qualified["local"]) & set(qualified["control"])
        )
        if len(matched_contexts) != EXPECTED_MATCHED_PREFILL:
            raise RuntimeError("C1 corpus paired high/mid prefill denominator drift")
        selected = np.asarray(
            [qualified[branch][context] for context in matched_contexts],
            dtype=np.int64,
        )
        matched_counts = {
            name: int(np.count_nonzero(strata[selected] == name))
            for name in EXPECTED_MATCHED_PREFILL_STRATA
        }
        if matched_counts != EXPECTED_MATCHED_PREFILL_STRATA:
            raise RuntimeError("C1 corpus paired high/mid stratum composition drift")
        bundles: list[AtomicBundle] = []
        for context, index in zip(matched_contexts, selected, strict=True):
            prefix = f"{branch}_"
            seed = int(self.arrays[prefix + "seeds"][index])
            step = int(self.arrays[prefix + "steps"][index])
            bundles.append(
                AtomicBundle(
                    bundle_id=str(self.arrays[prefix + "bundle_ids"][index]),
                    source_id="C1",
                    source_policy_version=0,
                    block_id=-1,
                    step_index=step,
                    states=self.arrays[prefix + "states"][index],
                    actions=self.arrays[prefix + "actions"][index],
                    rewards=self.arrays[prefix + "rewards"][index],
                    next_states=self.arrays[prefix + "next_states"][index],
                    masks=self.arrays[prefix + "masks"][index],
                    next_masks=self.arrays[prefix + "next_masks"][index],
                    done=bool(self.arrays[prefix + "dones"][index]),
                    focal_user=None,
                    specialist_rewards=None,
                    behavior_probabilities=self.arrays[prefix + "probabilities"][index],
                    provenance={
                        "phase": "C1_EXP_PREFILL_IMMUTABLE",
                        "branch": branch,
                        "stratum": str(strata[index]),
                        "seed": seed,
                        "matched_context": [int(context[0]), int(context[1])],
                        "physical_norad_ids": self.arrays[prefix + "physical_norad_ids"][index].tolist(),
                        "physical_cell_ids": self.arrays[prefix + "physical_cell_ids"][index].tolist(),
                        "corpus_sha256": self.corpus_sha256,
                        "manifest_sha256": self.manifest_sha256,
                        "enters_main": False,
                    },
                )
            )
        return tuple(bundles)


def load_verified_c1_corpus(
    manifest_path: Path,
    *,
    expected_checkpoint_sha256: str | None = None,
    expected_state_dim: int | None = None,
    expected_action_dim: int | None = None,
    tle_root: Path | None = None,
    repo: Path = REPO,
) -> VerifiedC1Corpus:
    """Verify manifest, authority, corpus bytes, dimensions, and lineage."""

    root = Path(repo).expanduser().resolve()
    manifest_path = Path(manifest_path).expanduser().resolve()
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    schema = manifest.get("schema") if isinstance(manifest, Mapping) else None
    if (
        not isinstance(manifest, Mapping)
        or schema not in {MANIFEST_SCHEMA, LEGACY_MANIFEST_SCHEMA}
        or manifest.get("status") != "complete"
        or manifest.get("claim_ceiling") != "C1_SPECIALIST_PREFILL_ONLY_NEVER_MAIN"
    ):
        raise RuntimeError("C1 corpus manifest is not a sealed specialist-only corpus")
    portable = schema == MANIFEST_SCHEMA
    if portable and (
        manifest.get("path_binding") != REPOSITORY_PATH_BINDING
        or manifest.get("tle_root_binding") != RUNTIME_TLE_ROOT_BINDING
    ):
        raise RuntimeError("C1 corpus manifest portable binding is invalid")
    authority = manifest.get("authority")
    shape = manifest.get("shape")
    if not isinstance(authority, Mapping) or not isinstance(shape, Mapping):
        raise RuntimeError("C1 corpus manifest authority or shape is missing")

    checkpoint = _require_bound_file(
        manifest_path,
        authority,
        path_field="checkpoint_path",
        digest_field="checkpoint_sha256",
        repo=root,
        fallback_relative=None if portable else CANONICAL_CHECKPOINT_RELATIVE,
        repository_relative=portable,
    )
    source_gate = _require_bound_file(
        manifest_path,
        authority,
        path_field="source_gate_result_path",
        digest_field="source_gate_result_sha256",
        repo=root,
        fallback_relative=None if portable else CANONICAL_SOURCE_GATE_RESULT_RELATIVE,
        repository_relative=portable,
    )
    seed_manifest = _require_bound_file(
        manifest_path,
        authority,
        path_field="seed_manifest_path",
        digest_field="seed_manifest_sha256",
        repo=root,
        fallback_relative=None if portable else CANONICAL_SEED_MANIFEST_RELATIVE,
        repository_relative=portable,
    )
    prereg = _require_bound_file(
        manifest_path,
        authority,
        path_field="prereg_path",
        digest_field="prereg_sha256",
        repo=root,
        fallback_relative=None if portable else CANONICAL_PREREG_RELATIVE,
        repository_relative=portable,
    )
    expected_prereg = _resolve_repository_path(
        root,
        CANONICAL_PREREG_RELATIVE,
        field="prereg_path",
        kind="file",
    )
    if (
        prereg != expected_prereg
        or sha256_file(prereg) != CANONICAL_PREREG_BYTE_SHA256
    ):
        raise RuntimeError("C1 corpus prereg authority is noncanonical")
    if portable and "tle_root_path" in authority:
        raise RuntimeError("C1 corpus portable manifest retains physical tle_root_path")
    if portable and tle_root is None:
        raise RuntimeError("C1 corpus portable manifest requires runtime tle_root")
    if tle_root is None:
        resolved_tle_root = _resolve_authority_dir(
            manifest_path,
            authority.get("tle_root_path"),
            field="tle_root_path",
        )
    else:
        resolved_tle_root = Path(tle_root).expanduser().resolve()
        if not resolved_tle_root.is_dir():
            raise RuntimeError("C1 corpus authority runtime tle_root is unavailable")
    ephemeris = assert_ephemeris_matches_record(
        read_prereg(prereg), archive=TleArchive(resolved_tle_root)
    )
    if (
        authority.get("tle_file_set_sha256") != ephemeris["file_set_sha256"]
        or authority.get("tle_file_count")
        != int(ephemeris["archive"]["file_count"])
    ):
        raise RuntimeError("C1 corpus TLE authority drift")
    checkpoint_sha = sha256_file(checkpoint)
    if expected_checkpoint_sha256 is not None and checkpoint_sha != expected_checkpoint_sha256:
        raise RuntimeError("C1 corpus checkpoint does not match the requested training authority")

    local_authorities = {
        "source_gate_spec_sha256": root
        / ".scratch/smc-er-short-ep/C1-SOURCE-GATE-A-SPEC-2026-08-27.md",
        "build_spec_sha256": root
        / ".scratch/smc-er-short-ep/C1-EXP-CORPUS-BUILD-SPEC-2026-08-27.md",
        "builder_sha256": root / ".scratch/smc-er-short-ep/build_c1_exp_corpus.py",
    }
    for digest_field, path in local_authorities.items():
        expected = authority.get(digest_field)
        if not path.is_file() or not _is_digest(expected) or sha256_file(path) != expected:
            raise RuntimeError(f"C1 corpus authority {digest_field} drift")

    gate_payload = json.loads(source_gate.read_text(encoding="utf-8"))
    if (
        not isinstance(gate_payload, Mapping)
        or gate_payload.get("schema") != SOURCE_GATE_SCHEMA
        or gate_payload.get("status") != "PASS"
        or gate_payload.get("decision") != "PASS_TO_C1_CONSUMER_GATE"
    ):
        raise RuntimeError("C1 corpus predecessor Source Gate A is not authoritative")
    gate_authority = gate_payload.get("authority")
    if not isinstance(gate_authority, Mapping) or (
        gate_authority.get("prereg_sha256") != sha256_file(prereg)
        or gate_authority.get("tle_file_set_sha256")
        != ephemeris["file_set_sha256"]
        or gate_authority.get("tle_file_count")
        != int(ephemeris["archive"]["file_count"])
    ):
        raise RuntimeError("C1 corpus and Source Gate A TLE lineage differ")
    seeds_payload = json.loads(seed_manifest.read_text(encoding="utf-8"))
    if not isinstance(seeds_payload, Mapping) or seeds_payload.get("schema") != SEED_SCHEMA:
        raise RuntimeError("C1 corpus seed manifest schema mismatch")
    for field, expected in (
        ("checkpoint_sha256", checkpoint_sha),
        ("source_gate_result_sha256", sha256_file(source_gate)),
        ("spec_sha256", authority.get("build_spec_sha256")),
    ):
        if seeds_payload.get(field) != expected:
            raise RuntimeError(f"C1 corpus seed manifest {field} drift")
    frozen_seeds = seeds_payload.get("seeds")
    if (
        not isinstance(frozen_seeds, list)
        or len(frozen_seeds) != 5
        or any(type(seed) is not int or seed < 0 for seed in frozen_seeds)
        or len(set(frozen_seeds)) != 5
    ):
        raise RuntimeError("C1 corpus seed manifest must contain five unique seeds")

    try:
        manifest_relative = manifest_path.relative_to(root)
    except ValueError:
        corpus_fallback = None
    else:
        corpus_fallback = str(
            PurePosixPath(*manifest_relative.parts[:-1]) / "c1-exp-corpus.npz"
        )
    if portable:
        corpus_path = _resolve_repository_path(
            root,
            manifest.get("corpus_path"),
            field="corpus_path",
            kind="file",
        )
    else:
        corpus_path = _resolve_authority_path(
            manifest_path,
            manifest.get("corpus_path"),
            field="corpus_path",
            repo=root,
            fallback_relative=corpus_fallback,
        )
    corpus_sha = manifest.get("corpus_sha256")
    if not _is_digest(corpus_sha) or sha256_file(corpus_path) != corpus_sha:
        raise RuntimeError("C1 corpus byte hash drift")
    if (
        shape.get("users") != EXPECTED_USERS
        or shape.get("bundles_per_branch") != EXPECTED_BUNDLES
        or {key: shape.get(key) for key in EXPECTED_STRATA} != EXPECTED_STRATA
    ):
        raise RuntimeError("C1 corpus frozen denominator drift")
    state_dim = shape.get("state_dim")
    action_dim = shape.get("action_dim")
    if type(state_dim) is not int or state_dim < 1 or type(action_dim) is not int or action_dim < 1:
        raise RuntimeError("C1 corpus dimensions are invalid")
    if expected_state_dim is not None and state_dim != expected_state_dim:
        raise RuntimeError("C1 corpus encoder state dimension mismatch")
    if expected_action_dim is not None and action_dim != expected_action_dim:
        raise RuntimeError("C1 corpus action dimension mismatch")

    with np.load(corpus_path, allow_pickle=False) as archive:
        expected_keys = {
            f"{branch}_{field}" for branch in EXPECTED_BRANCHES for field in ARRAY_FIELDS
        }
        if set(archive.files) != expected_keys:
            raise RuntimeError("C1 corpus array surface mismatch")
        arrays = {key: np.array(archive[key], copy=True) for key in archive.files}

    scalar_shapes = {
        "bundle_ids": (EXPECTED_BUNDLES,),
        "seeds": (EXPECTED_BUNDLES,),
        "steps": (EXPECTED_BUNDLES,),
        "strata": (EXPECTED_BUNDLES,),
        "dones": (EXPECTED_BUNDLES,),
        "system_throughput_bps": (EXPECTED_BUNDLES,),
        "system_power_w": (EXPECTED_BUNDLES,),
        "system_ee_bits_per_j": (EXPECTED_BUNDLES,),
        "served": (EXPECTED_BUNDLES,),
    }
    user_shapes = {
        "actions": (EXPECTED_BUNDLES, EXPECTED_USERS),
        "probabilities": (EXPECTED_BUNDLES, EXPECTED_USERS),
        "physical_norad_ids": (EXPECTED_BUNDLES, EXPECTED_USERS),
        "physical_cell_ids": (EXPECTED_BUNDLES, EXPECTED_USERS),
    }
    for branch in EXPECTED_BRANCHES:
        prefix = branch + "_"
        for field, expected in scalar_shapes.items():
            if arrays[prefix + field].shape != expected:
                raise RuntimeError(f"C1 corpus {branch} {field} shape drift")
        for field, expected in user_shapes.items():
            if arrays[prefix + field].shape != expected:
                raise RuntimeError(f"C1 corpus {branch} {field} shape drift")
        expected_state_shape = (EXPECTED_BUNDLES, EXPECTED_USERS, state_dim)
        expected_mask_shape = (EXPECTED_BUNDLES, EXPECTED_USERS, action_dim)
        if arrays[prefix + "states"].shape != expected_state_shape or arrays[prefix + "next_states"].shape != expected_state_shape:
            raise RuntimeError(f"C1 corpus {branch} state shape drift")
        if arrays[prefix + "rewards"].shape != (EXPECTED_BUNDLES, EXPECTED_USERS, 3):
            raise RuntimeError(f"C1 corpus {branch} reward shape drift")
        if arrays[prefix + "masks"].shape != expected_mask_shape or arrays[prefix + "next_masks"].shape != expected_mask_shape:
            raise RuntimeError(f"C1 corpus {branch} mask shape drift")

        ids = arrays[prefix + "bundle_ids"].astype(str)
        seeds = arrays[prefix + "seeds"]
        steps = arrays[prefix + "steps"]
        strata = arrays[prefix + "strata"].astype(str)
        if len(set(ids.tolist())) != EXPECTED_BUNDLES:
            raise RuntimeError(f"C1 corpus {branch} duplicate bundle ID")
        if set(map(int, seeds.tolist())) != set(frozen_seeds):
            raise RuntimeError(f"C1 corpus {branch} seed lineage drift")
        lineage = {(int(seed), int(step)) for seed, step in zip(seeds, steps, strict=True)}
        expected_lineage = {(int(seed), step) for seed in frozen_seeds for step in range(EXPECTED_STEPS)}
        if lineage != expected_lineage:
            raise RuntimeError(f"C1 corpus {branch} seed/step denominator drift")
        ee = arrays[prefix + "system_ee_bits_per_j"].astype(np.float64)
        if not np.array_equal(strata, _expected_strata(ee, seeds, steps, ids)):
            raise RuntimeError(f"C1 corpus {branch} deterministic strata drift")
        if {name: int(np.count_nonzero(strata == name)) for name in EXPECTED_STRATA} != EXPECTED_STRATA:
            raise RuntimeError(f"C1 corpus {branch} stratum count drift")

        finite_fields = (
            "states",
            "next_states",
            "rewards",
            "probabilities",
            "system_throughput_bps",
            "system_power_w",
            "system_ee_bits_per_j",
        )
        if any(not np.all(np.isfinite(arrays[prefix + field])) for field in finite_fields):
            raise RuntimeError(f"C1 corpus {branch} contains non-finite values")
        throughput = arrays[prefix + "system_throughput_bps"].astype(np.float64)
        power = arrays[prefix + "system_power_w"].astype(np.float64)
        if np.any(throughput < 0.0) or np.any(power < 0.0):
            raise RuntimeError(f"C1 corpus {branch} has negative physical totals")
        recomputed_ee = np.divide(throughput, power, out=np.zeros_like(throughput), where=power > 0.0)
        if np.any((power == 0.0) & (throughput != 0.0)) or not np.allclose(
            ee, recomputed_ee, rtol=1e-12, atol=1e-9
        ):
            raise RuntimeError(f"C1 corpus {branch} EE identity drift")
        probabilities = arrays[prefix + "probabilities"]
        if np.any((probabilities < 0.0) | (probabilities > 1.0)):
            raise RuntimeError(f"C1 corpus {branch} behavior probability drift")
        served = arrays[prefix + "served"]
        if np.any((served < 0) | (served > EXPECTED_USERS)):
            raise RuntimeError(f"C1 corpus {branch} served-count drift")
        actions = arrays[prefix + "actions"].astype(np.int64)
        masks = arrays[prefix + "masks"].astype(bool)
        action_exists = actions != NO_OP_ACTION
        if np.any(action_exists & ((actions < 0) | (actions >= action_dim))):
            raise RuntimeError(f"C1 corpus {branch} action index drift")
        rows, users = np.nonzero(action_exists)
        if np.any(~masks[rows, users, actions[rows, users]]):
            raise RuntimeError(f"C1 corpus {branch} executed action is mask-invalid")
        norad = arrays[prefix + "physical_norad_ids"]
        cell = arrays[prefix + "physical_cell_ids"]
        if np.any((norad == -1) != (cell == -1)) or np.any((~action_exists) != (norad == -1)):
            raise RuntimeError(f"C1 corpus {branch} physical action lineage drift")

    all_ids = np.concatenate(
        [arrays[f"{branch}_bundle_ids"].astype(str) for branch in EXPECTED_BRANCHES]
    )
    if len(set(all_ids.tolist())) != len(all_ids):
        raise RuntimeError("C1 corpus branch bundle IDs overlap")
    for array in arrays.values():
        array.setflags(write=False)
    return VerifiedC1Corpus(
        manifest_path=manifest_path,
        corpus_path=corpus_path,
        manifest_sha256=sha256_file(manifest_path),
        corpus_sha256=str(corpus_sha),
        checkpoint_sha256=checkpoint_sha,
        tle_file_set_sha256=str(ephemeris["file_set_sha256"]),
        state_dim=int(state_dim),
        action_dim=int(action_dim),
        arrays=arrays,
    )


__all__ = ["VerifiedC1Corpus", "load_verified_c1_corpus", "sha256_file"]
