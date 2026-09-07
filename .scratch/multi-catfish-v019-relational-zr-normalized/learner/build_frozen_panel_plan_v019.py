#!/usr/bin/env python3
"""Write the canonical pre-outcome V0.19 normalized learned-Q3 panel plan once."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from mcrl.env.keyed_fading import KeyedFadingField
from mcrl.runtime.ee_axis_ops3 import OPS3_KAPPA_BITS

import relational_source_panel_config_builder_v019 as panel


TRAIN_WORLDS = (2026120701, 2026120702, 2026120703, 2026120704)
VALIDATION_WORLDS = (2026120705, 2026120706, 2026120707)
LINEAGES = (2026092101, 2026092102, 2026092103)
INITIALIZATIONS = (2026120711, 2026120712, 2026120713)
SCHEDULE_SEEDS = (2026120721, 2026120722, 2026120723)

Q1_CHECKPOINTS = (
    "f26aab2fab6d31d6f3e4acd97782beeb0bba055ec94611dc9f3ed47038a231f0",
    "6930534d90840807c4dda1eda9c0ecf58793175053a37a43b75e38a7b6d310ba",
    "507b871f2536097b400b099b9dcb666e8445e9aee921001d61e70ff6042646b2",
)
Q2_CHECKPOINTS = (
    "d981232a9e56e6ce71c8e8b1fda789efc69852d4a6a22e918a2992ddc58a533d",
    "9a45f5bc125d6ba453d7d74dbc640ec3d2e927fffb161518e383e6b3aabbe8ef",
    "8f9d2e5d1749515a0896137082b1430419ae1b8a794d28ea772a23c86648be81",
)
Q1_PARAMETERS = (
    "4eba7ed1d89bcd41f68716ba25c739ce4132d79e722ce4a3313c342e8a0097a0",
    "e79fa1512eebd3f6fdfad753459bd6819c36e56f07ce8df28b61c557ab2da5e1",
    "807d31778203cdf3e7848e22d23ef8f450244eb9b8fe4f309dbb478c4cfa3e37",
)
Q2_PARAMETERS = (
    "d8330a381781d9af35269adf2266cf17101135a372d012fd0aa29d481ef2a430",
    "b5d8e82eca8b70378211a0de84c7f1348c32c7a57d84e4063c24f15e1efac5d7",
    "169bcc5cb1702daa3823c3d903d343445d6fa3ebffc3f2cf839f88a84e6d5683",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _bindings(values: tuple[str, ...]) -> list[dict[str, object]]:
    return [
        {"lineage": lineage, "sha256": value}
        for lineage, value in zip(LINEAGES, values, strict=True)
    ]


def _canonical(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def build_payload(args: argparse.Namespace) -> dict[str, object]:
    worlds = (*TRAIN_WORLDS, *VALIDATION_WORLDS)
    return {
        "schema": panel.PANEL_PLAN_SCHEMA,
        "schema_version": panel.PANEL_PLAN_VERSION,
        "learner_contract_path": str(args.contract.absolute()),
        "learner_contract_sha256": _sha256(args.contract),
        "code_manifest_path": str(args.code_manifest.absolute()),
        "code_manifest_sha256": _sha256(args.code_manifest),
        "q1_checkpoint_root": str(args.q1_root.absolute()),
        "q2_checkpoint_root": str(args.q2_root.absolute()),
        "q1_checkpoint_sha256_by_lineage": _bindings(Q1_CHECKPOINTS),
        "q2_checkpoint_sha256_by_lineage": _bindings(Q2_CHECKPOINTS),
        "q1_parameter_sha256_by_lineage": _bindings(Q1_PARAMETERS),
        "q2_parameter_sha256_by_lineage": _bindings(Q2_PARAMETERS),
        "prereg_path": str(args.prereg.absolute()),
        "tle_root": str(args.tle_root.absolute()),
        "output_root": str(args.output_root.absolute()),
        "train_worlds": list(TRAIN_WORLDS),
        "validation_worlds": list(VALIDATION_WORLDS),
        "lineages": list(LINEAGES),
        "initialization_lineages": [
            {
                "initialization_seed": initialization,
                "lineage": lineage,
                "schedule_seed": schedule,
            }
            for initialization, lineage, schedule in zip(
                INITIALIZATIONS, LINEAGES, SCHEDULE_SEEDS, strict=True
            )
        ],
        "field_component": panel.EXPECTED_FIELD_COMPONENT,
        "field_root_digest_by_world": [
            {
                "world_seed": world,
                "sha256": KeyedFadingField.from_components(
                    panel.EXPECTED_FIELD_COMPONENT, world
                ).root_digest,
            }
            for world in worlds
        ],
        "users": panel.EXPECTED_USERS,
        "steps": panel.EXPECTED_STEPS,
        "action_dim": panel.EXPECTED_ACTION_DIM,
        "kappa_bits_hex": float(OPS3_KAPPA_BITS).hex(),
        "output_unit_mode": panel.EXPECTED_OUTPUT_UNIT_MODE,
        "contract_status": panel.FROZEN_CONTRACT_STATUS,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "outcome_opened": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--code-manifest", type=Path, required=True)
    parser.add_argument("--q1-root", type=Path, required=True)
    parser.add_argument("--q2-root", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--plan-path", type=Path, required=True)
    args = parser.parse_args()
    if args.plan_path.exists() or args.plan_path.is_symlink():
        parser.error(f"refusing to overwrite {args.plan_path}")
    payload = build_payload(args)
    panel.validate_plan(payload)
    args.plan_path.parent.mkdir(parents=True, exist_ok=True)
    args.plan_path.write_bytes(_canonical(payload))
    print(json.dumps({"plan_path": str(args.plan_path), "sha256": _sha256(args.plan_path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
