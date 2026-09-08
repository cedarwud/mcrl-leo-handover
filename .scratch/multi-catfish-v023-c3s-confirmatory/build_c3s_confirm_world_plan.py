#!/usr/bin/env python3
"""Build the fresh, collision-refusing C3-S confirmatory world plan."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from typing import Any


HERE = Path(__file__).resolve().parent  # Provenance: confirmatory package location.
REPO = HERE.parents[1]  # Provenance: workspace package layout.
SCHEMA = "multi-catfish-mcrl-v023-c3s-confirmatory-world-plan-v1"  # Provenance: pre-built plan schema retained by v2.
SPLIT = "TRAIN"  # Provenance: astra C exact estimand.
ARMS = ("FULL2", "FULL2+C3-S")  # Provenance: astra C exact estimand.
EPISODES = 9000  # Provenance: amended A plan allocation ceiling.
MIN_EPISODES = 3000  # Provenance: astra C contribution boundary.
DOMAIN_PREFIX = "C3S_CONFIRM/world/"  # Provenance: amended A plan seed rule.
FIELD_COMPONENT = "MCRL_V020_REPRICED_C3_GATE_V1"  # Provenance: amended A plan keyed-field namespace.
MASK63 = (1 << 63) - 1  # Provenance: project SHA-256 seed derivation rule.
E1_INVENTORY = REPO / ".scratch/multi-catfish-v023-c3-existence-e1/E1-WORLD-DERIVATION-2026-09-08.json"  # Provenance: freshness census A plan.
C3S_INVENTORY = REPO / ".scratch/multi-catfish-v023-c3s-screen/C3S-WORLD-DERIVATION-2026-09-08.json"  # Provenance: freshness census A plan.
V024_INVENTORY = REPO / ".scratch/multi-catfish-v024-regime-b-design/V024-WORLD-DERIVATION-2026-09-08.json"  # Provenance: freshness census A plan.
STAGEC_BUILDER = REPO / ".scratch/multi-catfish-v023-c1c2-successor-physical-evaluation/build_v023_c1c2_successor_world_plan.py"  # Provenance: stage-C allocated-world census.


class WorldPlanError(ValueError):
    """The generated plan or its exclusion census is invalid."""


def canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as error:
        raise WorldPlanError("plan is not finite canonical ASCII JSON") from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise WorldPlanError(f"inventory is absent or symlinked: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def derive_seed(domain: str) -> int:
    try:
        encoded = domain.encode("ascii")
    except UnicodeEncodeError as error:
        raise WorldPlanError("world domains must be ASCII") from error
    return int.from_bytes(hashlib.sha256(encoded).digest()[:8], "big") & MASK63


def keyed_field_root_digest(seed: int) -> str:
    try:
        from mcrl.env.keyed_fading import KeyedFadingField
    except ImportError:
        payload = json.dumps(
            ["keyed-branch-independent-v1", FIELD_COMPONENT, int(seed)],
            ensure_ascii=True, separators=(",", ":"),
        ).encode("utf-8")
        root_key = hashlib.sha256(payload).hexdigest()
        return hashlib.sha256(root_key.encode("utf-8")).hexdigest()
    return KeyedFadingField.from_components(FIELD_COMPONENT, seed).root_digest


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise WorldPlanError(f"cannot read world inventory: {path}") from error
    if not isinstance(payload, dict):
        raise WorldPlanError(f"world inventory is not an object: {path}")
    return payload


def _domain_seed_map(payload: Mapping[str, object], *, label: str) -> dict[str, int]:
    candidates = (
        payload.get("world_seeds"), payload.get("worlds"),
        payload.get("domains_and_seeds"),
    )
    raw = next((value for value in candidates if isinstance(value, Mapping)), None)
    if raw is None:
        raise WorldPlanError(f"{label} inventory has no declared domain/seed mapping")
    result: dict[str, int] = {}
    for domain, seed in raw.items():
        if not isinstance(domain, str) or type(seed) is not int or seed < 0:
            raise WorldPlanError(f"{label} inventory contains a malformed world")
        if derive_seed(domain) != seed:
            raise WorldPlanError(f"{label} world derivation disagrees for {domain}")
        result[domain] = seed
    if not result:
        raise WorldPlanError(f"{label} inventory is empty")
    return result


def exclusion_inventory(
    *,
    e1_path: Path = E1_INVENTORY,
    c3s_path: Path = C3S_INVENTORY,
    v024_path: Path = V024_INVENTORY,
) -> tuple[dict[int, list[str]], list[dict[str, object]]]:
    """Return all allocated seed owners, including the stage-C 9000 plan."""

    owners: dict[int, list[str]] = {}
    bindings: list[dict[str, object]] = []
    spec = importlib.util.spec_from_file_location(
        "c3s_confirm_stagec_plan_donor", STAGEC_BUILDER
    )
    if spec is None or spec.loader is None:
        raise WorldPlanError("cannot import the stage-C world-plan builder")
    donor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(donor)
    stagec_plan = donor.build_world_plan()
    stagec_worlds = stagec_plan.get("worlds")
    if not isinstance(stagec_worlds, list) or len(stagec_worlds) != 9000:
        raise WorldPlanError("stage-C donor does not reproduce its 9000-world plan")
    stagec_rows = {
        f"STAGE_C_9000/world/{row['episode_index']}": int(row["world_seed"])
        for row in stagec_worlds
    }
    for domain, seed in stagec_rows.items():
        owners.setdefault(seed, []).append(domain)
    bindings.append({
        "role": "stage_c_9000_plan_rule",
        "path": str(STAGEC_BUILDER.resolve()),
        "sha256": file_sha256(STAGEC_BUILDER),
        "world_count": 9000,
        "seed_rule": "2026090600 + episode_index",
        "plan_sha256": stagec_plan["plan_sha256"],
    })
    for label, path in (("E1", e1_path), ("C3S_SCREEN", c3s_path), ("V024", v024_path)):
        mapping = _domain_seed_map(_read_json(path), label=label)
        for domain, seed in mapping.items():
            owners.setdefault(seed, []).append(domain)
        bindings.append({
            "role": label,
            "path": str(path.resolve()),
            "sha256": file_sha256(path),
            "world_count": len(mapping),
        })
    return owners, bindings


def build_world_plan(
    episodes: int = EPISODES,
    *,
    e1_path: Path = E1_INVENTORY,
    c3s_path: Path = C3S_INVENTORY,
    v024_path: Path = V024_INVENTORY,
) -> dict[str, object]:
    if type(episodes) is not int or episodes < MIN_EPISODES:
        raise WorldPlanError("confirmatory plan requires at least 3000 episodes")
    allocated, bindings = exclusion_inventory(
        e1_path=e1_path, c3s_path=c3s_path, v024_path=v024_path,
    )
    worlds: list[dict[str, object]] = []
    seen: dict[int, str] = {}
    for index in range(1, episodes + 1):
        domain = f"{DOMAIN_PREFIX}{index}"
        seed = derive_seed(domain)
        if seed in seen:
            raise WorldPlanError(
                f"internal seed collision: {domain} collides with {seen[seed]} at {seed}"
            )
        if seed in allocated:
            raise WorldPlanError(
                f"allocated seed collision: {domain} collides with {allocated[seed]} at {seed}"
            )
        seen[seed] = domain
        worlds.append({
            "episode_index": index,
            "world_id": f"c3s-confirm-world-{index:06d}",
            "domain": domain,
            "world_seed": seed,
            "field_root_digest": keyed_field_root_digest(seed),
        })
    body: dict[str, object] = {
        "schema": SCHEMA,
        "split": SPLIT,
        "episode_budget": episodes,
        "analysis_prefix_episodes": 3000,
        "arms": list(ARMS),
        "field_component": FIELD_COMPONENT,
        "world_rule": {
            "domain_format": "C3S_CONFIRM/world/{i}",
            "world_id_format": "c3s-confirm-world-{i:06d}",
            "seed_rule": "int.from_bytes(SHA256(domain.encode('ascii')).digest()[:8], 'big') & ((1<<63)-1)",
        },
        "collision_census": {
            "status": "PASS_NO_COLLISIONS",
            "checked_new_worlds": episodes,
            "checked_allocated_seeds": len(allocated),
            "inventory_bindings": bindings,
            "collision_hits": [],
        },
        "worlds": worlds,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
    }
    body["plan_sha256"] = canonical_sha256(body)
    return body


def verify_world_plan(value: Mapping[str, object]) -> str:
    if not isinstance(value, Mapping):
        raise WorldPlanError("world plan must be an object")
    supplied = value.get("plan_sha256")
    body = dict(value)
    body.pop("plan_sha256", None)
    if not isinstance(supplied, str) or len(supplied) != 64 or canonical_sha256(body) != supplied:
        raise WorldPlanError("plan digest disagrees with its contents")
    episodes = value.get("episode_budget")
    if type(episodes) is not int or episodes < MIN_EPISODES:
        raise WorldPlanError("plan episode budget is below 3000")
    expected = build_world_plan(episodes)
    # The sealed package may be copied between worktrees. Absolute inventory
    # paths are provenance labels; role, bytes, counts, seeds, and plan digest
    # remain authoritative. Relocation must not require rewriting the seal.
    def relocation_neutral(payload: Mapping[str, object]) -> dict[str, object]:
        normalized = json.loads(json.dumps(payload))
        normalized.pop("plan_sha256", None)
        for record in normalized["collision_census"]["inventory_bindings"]:
            record.pop("path", None)
        return normalized

    if relocation_neutral(value) != relocation_neutral(expected):
        raise WorldPlanError("plan differs from the declared domain rule or collision census")
    return supplied


def read_world_plan(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    payload = _read_json(source)
    verify_world_plan(payload)
    return payload


def write_once(path: Path, payload: Mapping[str, object]) -> str:
    target = Path(path)
    sidecar = Path(f"{target}.sha256")
    if target.exists() or target.is_symlink() or sidecar.exists() or sidecar.is_symlink():
        raise WorldPlanError(f"refusing to overwrite world-plan artifact: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = canonical_bytes(payload) + b"\n"
    descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, target)
    except FileExistsError as error:
        raise WorldPlanError(f"world plan was published concurrently: {target}") from error
    finally:
        Path(temporary).unlink(missing_ok=True)
    digest = file_sha256(target)
    sidecar.write_text(f"{digest}  {target.name}\n", encoding="ascii")
    target.chmod(0o444)
    sidecar.chmod(0o444)
    return digest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--output", type=Path)
    group.add_argument("--check", type=Path)
    parser.add_argument("--episodes", type=int, default=EPISODES)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.check is not None:
            payload = read_world_plan(args.check)
            print(f"C3S_CONFIRM_WORLD_PLAN_OK plan_sha256={payload['plan_sha256']}")
        else:
            payload = build_world_plan(args.episodes)
            digest = write_once(args.output, payload)
            print(f"C3S_CONFIRM_WORLD_PLAN_WRITTEN path={args.output} sha256={digest}")
    except WorldPlanError as error:
        print(f"C3S_CONFIRM_WORLD_PLAN_ERROR: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ARMS", "EPISODES", "FIELD_COMPONENT", "WorldPlanError", "build_world_plan",
    "derive_seed", "read_world_plan", "verify_world_plan", "write_once",
]
