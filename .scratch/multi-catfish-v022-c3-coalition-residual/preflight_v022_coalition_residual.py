#!/usr/bin/env python3
"""External, non-circular preflight for the V0.22 mechanics probe.

The JSON manifest is deliberately not self-hashed.  Its companion
``PREFLIGHT-MANIFEST.sha256`` file seals the manifest bytes, while the
manifest seals every source, contract, checkpoint, fit, and preregistration
file consumed by the runner.  This module has no import path through the
runner and performs no simulator, TLE, learner, or training work.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


MANIFEST_SCHEMA = "multi-catfish-mcrl-v022-c3-coalition-residual-preflight-v1"
MANIFEST_NAME = "PREFLIGHT-MANIFEST.json"
MANIFEST_DIGEST_NAME = "PREFLIGHT-MANIFEST.sha256"
EXPECTED_WORLD_COUNT = 4
EXPECTED_STEPS = 10
EXPECTED_LINEAGE = 2026092101
EXPECTED_ACTIONS = 28
EXPECTED_USERS = 100
EXPECTED_SPLIT = "TRAIN_DEVELOPMENT"
EXPECTED_FIELD_COMPONENT = "MCRL_V022_C3_COALITION_RESIDUAL_V1"


class V022PreflightError(RuntimeError):
    """The external V0.22 manifest or one of its bindings failed closed."""


def file_sha256(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V022PreflightError(f"expected a regular file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V022PreflightError(f"{field} is not a lowercase SHA-256")
    return value


def _canonical_json(path: Path) -> dict[str, Any]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V022PreflightError(f"manifest is missing or non-regular: {source}")
    raw = source.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V022PreflightError(f"manifest is not valid ASCII JSON: {source}") from error
    if not isinstance(payload, dict):
        raise V022PreflightError("manifest root is not an object")
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    if raw not in (canonical, canonical + b"\n"):
        raise V022PreflightError("manifest is not canonical JSON")
    return payload


def _relative_file(value: object, *, field: str, repo: Path) -> tuple[str, Path]:
    if not isinstance(value, str) or not value.strip():
        raise V022PreflightError(f"{field}.path is empty")
    relative = Path(value)
    if relative.is_absolute() or any(part == ".." for part in relative.parts):
        raise V022PreflightError(f"{field}.path must stay repository-relative")
    resolved = (Path(repo).resolve() / relative).resolve()
    if not resolved.is_relative_to(Path(repo).resolve()):
        raise V022PreflightError(f"{field}.path escapes the repository")
    return relative.as_posix(), resolved


def _validate_digest_file(path: Path, manifest_digest: str) -> None:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V022PreflightError(f"manifest digest file is missing: {source}")
    lines = source.read_text(encoding="ascii").splitlines()
    if len(lines) != 1:
        raise V022PreflightError("manifest digest file must contain exactly one line")
    parts = lines[0].split()
    if len(parts) != 2 or parts[1] != MANIFEST_NAME:
        raise V022PreflightError("manifest digest file has a noncanonical filename binding")
    if _digest(parts[0], field="manifest_sha256") != manifest_digest:
        raise V022PreflightError("manifest digest file disagrees with manifest bytes")


def _require_mapping(value: object, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise V022PreflightError(f"{field} is not an object")
    return value


def validate_manifest(
    manifest_path: Path,
    *,
    manifest_digest_path: Path | None = None,
    repo: Path,
    prereg_path: Path,
) -> dict[str, Any]:
    """Validate the external manifest and return a receipt for result.json.

    ``prereg_path`` is a caller input and must equal the manifest's declared
    preregistration binding.  The TLE root is intentionally not hashed here:
    the canonical runtime ``assert_ephemeris_matches_record`` validator is
    called after the temporary frozen TLE view is built by the runner.
    """

    repo_root = Path(repo).resolve()
    source = Path(manifest_path)
    manifest = _canonical_json(source)
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise V022PreflightError("manifest schema is stale")
    if manifest.get("manifest_version") != 1:
        raise V022PreflightError("manifest version is not 1")
    manifest_digest = file_sha256(source)
    digest_path = (
        Path(manifest_digest_path)
        if manifest_digest_path is not None
        else source.with_name(MANIFEST_DIGEST_NAME)
    )
    _validate_digest_file(digest_path, manifest_digest)

    configuration = _require_mapping(manifest.get("configuration"), field="configuration")
    if configuration.get("split") != EXPECTED_SPLIT:
        raise V022PreflightError("manifest split is not TRAIN_DEVELOPMENT")
    if configuration.get("lineage") != EXPECTED_LINEAGE:
        raise V022PreflightError("manifest lineage is not the selected V0.20 lineage")
    if configuration.get("worlds") != [
        2026121701,
        2026121702,
        2026121703,
        2026121704,
    ]:
        raise V022PreflightError("manifest world panel drifted")
    if configuration.get("steps_per_episode") != EXPECTED_STEPS:
        raise V022PreflightError("manifest episode length drifted")
    if configuration.get("users") != EXPECTED_USERS:
        raise V022PreflightError("manifest user count drifted")
    if configuration.get("action_count") != EXPECTED_ACTIONS:
        raise V022PreflightError("manifest action width drifted")
    if configuration.get("field_component") != EXPECTED_FIELD_COMPONENT:
        raise V022PreflightError("manifest keyed-fading component drifted")

    bindings_raw = manifest.get("bindings")
    if not isinstance(bindings_raw, list) or not bindings_raw:
        raise V022PreflightError("manifest has no file bindings")
    bindings: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, raw in enumerate(bindings_raw):
        entry = _require_mapping(raw, field=f"bindings[{index}]")
        role = entry.get("role")
        if not isinstance(role, str) or not role:
            raise V022PreflightError(f"bindings[{index}].role is empty")
        relative, resolved = _relative_file(
            entry.get("path"), field=f"bindings[{index}]", repo=repo_root
        )
        if relative in seen:
            raise V022PreflightError(f"manifest repeats file binding: {relative}")
        seen.add(relative)
        expected = _digest(entry.get("sha256"), field=f"bindings[{index}].sha256")
        actual = file_sha256(resolved)
        if actual != expected:
            raise V022PreflightError(
                f"manifest binding drifted for {relative}: expected {expected}, got {actual}"
            )
        bindings.append({"role": role, "path": relative, "sha256": actual})

    by_role = {entry["role"]: entry for entry in bindings}
    required_roles = {
        "runner",
        "preflight",
        "contract",
        "formula",
        "preregistration",
        "fit_merged",
        "selected_q1_q2_checkpoint",
        "v020_runner",
        "v018_runner",
        "v015_runner",
        "v013_runner",
        "screen_runner",
        "screen_gate",
        "screen_source",
        "runtime_training_pipeline",
        "runtime_tle",
    }
    missing = sorted(required_roles - set(by_role))
    if missing:
        raise V022PreflightError("manifest is missing required roles: " + ", ".join(missing))

    expected_paths = {
        "runner": ".scratch/multi-catfish-v022-c3-coalition-residual/run_v022_coalition_residual_probe.py",
        "preflight": ".scratch/multi-catfish-v022-c3-coalition-residual/preflight_v022_coalition_residual.py",
        "contract": ".scratch/multi-catfish-v022-c3-coalition-residual/COALITION-RESIDUAL-MECHANICS-PROBE-CONTRACT-2026-09-05.md",
        "formula": "src/mcrl/runtime/ee_axis_coalition_residual_c3.py",
        "preregistration": "artifacts/PREREG-FROZEN-2026-08-25-R2.json",
        "fit_merged": ".scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/merged/result.json",
        "selected_q1_q2_checkpoint": ".scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/lineage-2026092101/checkpoints/lineage-2026092101-q2init-2026108101-rung-003000.pt",
        "v020_runner": ".scratch/multi-catfish-v020-c3-source-audit/run_v020_repriced_c3_gate.py",
        "v018_runner": ".scratch/multi-catfish-v018-relational-zr/run_v018_analytic_diagnostic.py",
        "v015_runner": ".scratch/multi-catfish-v015-c3-learned-context/run_v015_c3_learned_context_oracle.py",
        "v013_runner": ".scratch/zero-energy-c3-v013/run_v013_zero_energy_c3_oracle.py",
        "screen_runner": ".scratch/c3-v04/run_v04_c3_500_update_screen.py",
        "screen_gate": ".scratch/c3-v04/run_v04_c3_learnability_gate.py",
        "screen_source": ".scratch/c3-v04/run_v04_c3_source.py",
        "runtime_training_pipeline": "src/mcrl/runtime/training_pipeline.py",
        "runtime_tle": "src/mcrl/env/tle.py",
    }
    for role, expected_path in expected_paths.items():
        if by_role[role]["path"] != expected_path:
            raise V022PreflightError(
                f"manifest path for {role} is not the frozen source: "
                f"{by_role[role]['path']}"
            )

    supplied_prereg = Path(prereg_path)
    if supplied_prereg.is_absolute():
        prereg_resolved = supplied_prereg.resolve()
        if not prereg_resolved.is_relative_to(repo_root):
            raise V022PreflightError(
                "--prereg absolute path must resolve inside the repository"
            )
        prereg_relative = prereg_resolved.relative_to(repo_root).as_posix()
    else:
        prereg_relative, prereg_resolved = _relative_file(
            str(supplied_prereg), field="preregistration_argument", repo=repo_root
        )
    if by_role["preregistration"]["path"] != prereg_relative:
        raise V022PreflightError(
            "--prereg must be the manifest's frozen repository-relative preregistration"
        )
    if file_sha256(prereg_resolved) != by_role["preregistration"]["sha256"]:
        raise V022PreflightError("preregistration argument digest disagrees with manifest")

    fit = _require_mapping(configuration.get("fit_merged"), field="configuration.fit_merged")
    checkpoint = _require_mapping(
        configuration.get("selected_checkpoint"), field="configuration.selected_checkpoint"
    )
    for config, role, name in (
        (fit, "fit_merged", "fit_merged"),
        (checkpoint, "selected_q1_q2_checkpoint", "selected_checkpoint"),
    ):
        if config.get("path") != by_role[role]["path"]:
            raise V022PreflightError(f"configuration.{name}.path disagrees with binding")
        if config.get("sha256") != by_role[role]["sha256"]:
            raise V022PreflightError(f"configuration.{name}.sha256 disagrees with binding")

    tle = _require_mapping(configuration.get("tle"), field="configuration.tle")
    tle_file_set = _digest(tle.get("file_set_sha256"), field="configuration.tle.file_set_sha256")
    receipt = {
        "schema": MANIFEST_SCHEMA,
        "status": "PASS",
        "manifest_path": str(source.resolve()),
        "manifest_file_sha256": manifest_digest,
        "manifest_digest_path": str(digest_path.resolve()),
        "manifest_binding_count": len(bindings),
        "bindings": bindings,
        "configuration": {
            "split": configuration["split"],
            "lineage": configuration["lineage"],
            "worlds": list(configuration["worlds"]),
            "steps_per_episode": configuration["steps_per_episode"],
            "users": configuration["users"],
            "action_count": configuration["action_count"],
            "field_component": configuration["field_component"],
            "tle_file_set_sha256": tle_file_set,
            "fit_merged": dict(fit),
            "selected_checkpoint": dict(checkpoint),
        },
    }
    return receipt


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--manifest-digest", type=Path)
    args = parser.parse_args()
    receipt = validate_manifest(
        args.manifest,
        manifest_digest_path=args.manifest_digest,
        repo=args.repo,
        prereg_path=args.prereg,
    )
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
