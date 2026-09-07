"""Build the frozen V0.19 normalized-output source-panel configurations.

This module only materializes canonical identities and paths.  It does not
open a simulator, TLE archive, checkpoint, learner, outcome, or TEST split.
The input plan is the sole source of panel identity; the seven-by-three
rectangle is validated before any write-once output is created.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile

_R2_ROOT = Path(__file__).resolve().parent
_REPO = _R2_ROOT.parents[2]
_DRAFT_ROOT = _R2_ROOT.parent / "next-learner-draft"
_SOURCE_ROOT = _REPO / "src"
for _path in (_R2_ROOT, _DRAFT_ROOT, _SOURCE_ROOT, _REPO):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_ops3 import OPS3_KAPPA_BITS  # noqa: E402
from mcrl.algorithms.ee_axis_relational_zr_c3_head_v019 import (  # noqa: E402
    NORMALIZED_BITS_PER_KAPPA,
    OUTPUT_UNIT_MODES,
)


PANEL_PLAN_SCHEMA = "multi-catfish-mcrl-v019-relational-zr-source-panel-plan-v1"
PANEL_PLAN_VERSION = 1
PANEL_MANIFEST_SCHEMA = "multi-catfish-mcrl-v019-relational-zr-source-panel-manifest-v1"
PANEL_MANIFEST_VERSION = 1
ADAPTER_SCHEMA = "multi-catfish-mcrl-v019-relational-zr-simulator-source-config-v1"
ADAPTER_SCHEMA_VERSION = 1
RUN_PLAN_SCHEMA = "multi-catfish-mcrl-v019-relational-q3-run-plan-v1"
RUN_PLAN_VERSION = 1
SCHEDULE_ALGORITHM = "round-robin-world-independent-without-replacement-v1"
FROZEN_CONTRACT_STATUS = "FROZEN_BEFORE_OUTCOME"
EXPECTED_TRAIN_WORLDS = 4
EXPECTED_VALIDATION_WORLDS = 3
EXPECTED_LINEAGES = 3
FORBIDDEN_PRIOR_WORLDS = frozenset(
    {
        2026120401,
        2026120402,
        2026120403,
        2026120404,
        2026120501,
        2026120502,
        2026120503,
        2026120504,
        2026120505,
        2026120506,
        2026120507,
    }
)
EXPECTED_INITIALIZATIONS = 3
EXPECTED_USERS = 100
EXPECTED_STEPS = 10
EXPECTED_ROWS = 1000
EXPECTED_ACTION_DIM = 28
EXPECTED_ACTION_CONTEXT_DIM = 7
EXPECTED_VICTIM_TOKEN_DIM = 6
EXPECTED_BATCH_SIZE = 512
EXPECTED_UPDATES = 100
EXPECTED_KAPPA_HEX = "0x1.2cea89d260f2ap+33"
EXPECTED_FIELD_COMPONENT = "MCRL_V015_ZR_C3_LEARNED_CONTEXT_ORACLE_V1"
EXPECTED_OUTPUT_UNIT_MODE = NORMALIZED_BITS_PER_KAPPA

_PLAN_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "learner_contract_path",
        "learner_contract_sha256",
        "code_manifest_path",
        "code_manifest_sha256",
        "q1_checkpoint_root",
        "q2_checkpoint_root",
        "q1_checkpoint_sha256_by_lineage",
        "q2_checkpoint_sha256_by_lineage",
        "q1_parameter_sha256_by_lineage",
        "q2_parameter_sha256_by_lineage",
        "prereg_path",
        "tle_root",
        "output_root",
        "train_worlds",
        "validation_worlds",
        "lineages",
        "initialization_lineages",
        "field_component",
        "field_root_digest_by_world",
        "users",
        "steps",
        "action_dim",
        "kappa_bits_hex",
        "output_unit_mode",
        "contract_status",
        "test_split_opened",
        "episode_training",
        "learner_update",
        "outcome_opened",
    }
)


class SourcePanelConfigBuilderError(ValueError):
    """The panel plan or write-once materialization boundary failed."""


def _canonical_bytes(payload: object) -> bytes:
    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise SourcePanelConfigBuilderError("payload is not finite canonical JSON") from error


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _file_sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise SourcePanelConfigBuilderError(f"expected a regular file: {path}")
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as error:
        raise SourcePanelConfigBuilderError(f"cannot read file: {path}") from error
    return digest.hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise SourcePanelConfigBuilderError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise SourcePanelConfigBuilderError(f"{field} must be a positive integer")
    return value


def _path(value: object, *, field: str, base: Path) -> Path:
    if not isinstance(value, str) or not value:
        raise SourcePanelConfigBuilderError(f"{field} must be a nonempty path")
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = base / candidate
    candidate = candidate.absolute()
    if candidate.is_symlink():
        raise SourcePanelConfigBuilderError(f"{field} must not be a symlink")
    return candidate


def _identity_list(value: object, *, field: str, count: int) -> tuple[int, ...]:
    if not isinstance(value, list) or len(value) != count:
        raise SourcePanelConfigBuilderError(f"{field} must contain exactly {count} identities")
    result = tuple(_positive_int(item, field=field) for item in value)
    if len(set(result)) != len(result):
        raise SourcePanelConfigBuilderError(f"{field} contains duplicates")
    return result


def _digest_records(
    value: object,
    *,
    field: str,
    identities: Sequence[int],
) -> tuple[tuple[int, str], ...]:
    if not isinstance(value, list) or len(value) != len(identities):
        raise SourcePanelConfigBuilderError(
            f"{field} must contain exactly {len(identities)} bindings"
        )
    result: list[tuple[int, str]] = []
    for item in value:
        if not isinstance(item, Mapping) or set(item) != {"lineage", "sha256"}:
            raise SourcePanelConfigBuilderError(f"{field} contains a malformed binding")
        result.append(
            (
                _positive_int(item["lineage"], field=f"{field}.lineage"),
                _digest(item["sha256"], field=f"{field}.sha256"),
            )
        )
    if tuple(lineage for lineage, _digest_value in result) != tuple(identities):
        raise SourcePanelConfigBuilderError(f"{field} is not in the declared lineage order")
    return tuple(result)


def _world_digest_records(
    value: object,
    *,
    worlds: Sequence[int],
) -> tuple[tuple[int, str], ...]:
    if not isinstance(value, list) or len(value) != len(worlds):
        raise SourcePanelConfigBuilderError(
            f"field_root_digest_by_world must contain exactly {len(worlds)} bindings"
        )
    result: list[tuple[int, str]] = []
    for item in value:
        if not isinstance(item, Mapping) or set(item) != {"world_seed", "sha256"}:
            raise SourcePanelConfigBuilderError("field root binding is malformed")
        result.append(
            (
                _positive_int(item["world_seed"], field="field_root_digest_by_world.world_seed"),
                _digest(item["sha256"], field="field_root_digest_by_world.sha256"),
            )
        )
    if tuple(world for world, _digest_value in result) != tuple(worlds):
        raise SourcePanelConfigBuilderError("field roots are not in the declared world order")
    return tuple(result)


def _initializations(value: object, *, lineages: Sequence[int]) -> tuple[dict[str, int], ...]:
    if not isinstance(value, list) or len(value) != EXPECTED_INITIALIZATIONS:
        raise SourcePanelConfigBuilderError("initialization_lineages must contain exactly three entries")
    result: list[dict[str, int]] = []
    for item in value:
        if not isinstance(item, Mapping) or set(item) != {
            "initialization_seed",
            "lineage",
            "schedule_seed",
        }:
            raise SourcePanelConfigBuilderError("initialization_lineages entry is malformed")
        result.append(
            {
                "initialization_seed": _positive_int(item["initialization_seed"], field="initialization_seed"),
                "lineage": _positive_int(item["lineage"], field="initialization_lineages.lineage"),
                "schedule_seed": _positive_int(item["schedule_seed"], field="schedule_seed"),
            }
        )
    if tuple(item["lineage"] for item in result) != tuple(lineages):
        raise SourcePanelConfigBuilderError("initialization lineages do not match the declared order")
    if len({item["initialization_seed"] for item in result}) != len(result) or len({item["schedule_seed"] for item in result}) != len(result):
        raise SourcePanelConfigBuilderError("initialization seeds or schedule seeds are duplicated")
    return tuple(result)


@dataclass(frozen=True)
class PanelPlan:
    plan_sha256: str
    learner_contract_path: Path
    learner_contract_sha256: str
    code_manifest_path: Path
    code_manifest_sha256: str
    q1_checkpoint_root: Path
    q2_checkpoint_root: Path
    q1_checkpoint_sha256_by_lineage: tuple[tuple[int, str], ...]
    q2_checkpoint_sha256_by_lineage: tuple[tuple[int, str], ...]
    q1_parameter_sha256_by_lineage: tuple[tuple[int, str], ...]
    q2_parameter_sha256_by_lineage: tuple[tuple[int, str], ...]
    prereg_path: Path
    tle_root: Path
    output_root: Path
    train_worlds: tuple[int, ...]
    validation_worlds: tuple[int, ...]
    lineages: tuple[int, ...]
    initializations: tuple[dict[str, int], ...]
    field_component: str
    field_root_digest_by_world: tuple[tuple[int, str], ...]
    kappa_bits: float
    output_unit_mode: str
    plan_status: str = FROZEN_CONTRACT_STATUS
    users: int = EXPECTED_USERS
    steps: int = EXPECTED_STEPS
    action_dim: int = EXPECTED_ACTION_DIM

    @property
    def worlds(self) -> tuple[int, ...]:
        return (*self.train_worlds, *self.validation_worlds)

    def field_roots(self) -> dict[int, str]:
        expected = {
            world: KeyedFadingField.from_components(self.field_component, world).root_digest
            for world in self.worlds
        }
        supplied = dict(self.field_root_digest_by_world)
        if supplied != expected:
            raise SourcePanelConfigBuilderError("field root digest is not the deterministic keyed-field root")
        return expected

    def digest_maps(self) -> dict[str, dict[int, str]]:
        return {
            "q1_checkpoint_sha256": dict(self.q1_checkpoint_sha256_by_lineage),
            "q2_checkpoint_sha256": dict(self.q2_checkpoint_sha256_by_lineage),
            "q1_parameter_sha256": dict(self.q1_parameter_sha256_by_lineage),
            "q2_parameter_sha256": dict(self.q2_parameter_sha256_by_lineage),
        }


def validate_plan(
    payload: Mapping[str, object],
    *,
    plan_sha256: str = "0" * 64,
    base: Path | None = None,
) -> PanelPlan:
    """Validate a strict plan without touching simulator or checkpoint bytes."""

    if set(payload) != _PLAN_FIELDS:
        raise SourcePanelConfigBuilderError("panel plan fields are not closed")
    if payload["schema"] != PANEL_PLAN_SCHEMA or payload["schema_version"] != PANEL_PLAN_VERSION:
        raise SourcePanelConfigBuilderError("panel plan schema is stale")
    if payload["contract_status"] != FROZEN_CONTRACT_STATUS:
        raise SourcePanelConfigBuilderError("learner contract is not frozen before outcome access")
    if any(payload[field] is not False for field in ("test_split_opened", "episode_training", "learner_update", "outcome_opened")):
        raise SourcePanelConfigBuilderError("panel plan crosses a forbidden boundary")
    path_base = Path.cwd() if base is None else Path(base).absolute()
    contract_path = _path(payload["learner_contract_path"], field="learner_contract_path", base=path_base)
    code_manifest_path = _path(payload["code_manifest_path"], field="code_manifest_path", base=path_base)
    q1_root = _path(payload["q1_checkpoint_root"], field="q1_checkpoint_root", base=path_base)
    q2_root = _path(payload["q2_checkpoint_root"], field="q2_checkpoint_root", base=path_base)
    if q1_root == q2_root:
        raise SourcePanelConfigBuilderError("Q1 and Q2 checkpoint roots must be distinct")
    prereg_path = _path(payload["prereg_path"], field="prereg_path", base=path_base)
    tle_root = _path(payload["tle_root"], field="tle_root", base=path_base)
    output_root = _path(payload["output_root"], field="output_root", base=path_base)
    train_worlds = _identity_list(payload["train_worlds"], field="train_worlds", count=EXPECTED_TRAIN_WORLDS)
    validation_worlds = _identity_list(payload["validation_worlds"], field="validation_worlds", count=EXPECTED_VALIDATION_WORLDS)
    lineages = _identity_list(payload["lineages"], field="lineages", count=EXPECTED_LINEAGES)
    if set(train_worlds) & set(validation_worlds):
        raise SourcePanelConfigBuilderError("TRAIN and VALIDATION worlds overlap")
    worlds = (*train_worlds, *validation_worlds)
    if set(worlds) & FORBIDDEN_PRIOR_WORLDS:
        raise SourcePanelConfigBuilderError("panel reuses a prior opened world")
    field_roots = _world_digest_records(payload["field_root_digest_by_world"], worlds=worlds)
    initializations = _initializations(payload["initialization_lineages"], lineages=lineages)
    try:
        kappa_hex = payload["kappa_bits_hex"]
        if not isinstance(kappa_hex, str):
            raise TypeError("kappa_bits_hex must be text")
        kappa = float.fromhex(kappa_hex)
    except (TypeError, ValueError, OverflowError) as error:
        raise SourcePanelConfigBuilderError("kappa_bits_hex is malformed") from error
    if not math.isfinite(kappa) or kappa <= 0.0 or kappa_hex != EXPECTED_KAPPA_HEX:
        raise SourcePanelConfigBuilderError("kappa_bits_hex disagrees with OPS3")
    if float(OPS3_KAPPA_BITS).hex() != kappa_hex:
        raise SourcePanelConfigBuilderError("runtime OPS3 kappa disagrees with the plan")
    if payload["output_unit_mode"] not in OUTPUT_UNIT_MODES:
        raise SourcePanelConfigBuilderError("output_unit_mode is unknown")
    if payload["output_unit_mode"] != EXPECTED_OUTPUT_UNIT_MODE:
        raise SourcePanelConfigBuilderError(
            "V0.19 panel plan must explicitly select normalized_bits_per_kappa"
        )
    for field, value in (
        ("learner_contract_sha256", payload["learner_contract_sha256"]),
        ("code_manifest_sha256", payload["code_manifest_sha256"]),
    ):
        _digest(value, field=field)
    maps = {
        name: _digest_records(payload[name], field=name, identities=lineages)
        for name in (
            "q1_checkpoint_sha256_by_lineage",
            "q2_checkpoint_sha256_by_lineage",
            "q1_parameter_sha256_by_lineage",
            "q2_parameter_sha256_by_lineage",
        )
    }
    if not isinstance(payload["field_component"], str) or not payload["field_component"]:
        raise SourcePanelConfigBuilderError("field_component must be a nonempty string")
    if payload["field_component"] != EXPECTED_FIELD_COMPONENT:
        raise SourcePanelConfigBuilderError("field_component disagrees with V0.15 keyed-field authority")
    users = _positive_int(payload["users"], field="users")
    steps = _positive_int(payload["steps"], field="steps")
    action_dim = _positive_int(payload["action_dim"], field="action_dim")
    if (users, steps, action_dim) != (EXPECTED_USERS, EXPECTED_STEPS, EXPECTED_ACTION_DIM):
        raise SourcePanelConfigBuilderError("users/steps/action_dim disagree with the frozen source shape")
    _digest(plan_sha256, field="plan_sha256")
    return PanelPlan(
        plan_sha256=plan_sha256,
        learner_contract_path=contract_path,
        learner_contract_sha256=str(payload["learner_contract_sha256"]),
        code_manifest_path=code_manifest_path,
        code_manifest_sha256=str(payload["code_manifest_sha256"]),
        q1_checkpoint_root=q1_root,
        q2_checkpoint_root=q2_root,
        q1_checkpoint_sha256_by_lineage=maps["q1_checkpoint_sha256_by_lineage"],
        q2_checkpoint_sha256_by_lineage=maps["q2_checkpoint_sha256_by_lineage"],
        q1_parameter_sha256_by_lineage=maps["q1_parameter_sha256_by_lineage"],
        q2_parameter_sha256_by_lineage=maps["q2_parameter_sha256_by_lineage"],
        prereg_path=prereg_path,
        tle_root=tle_root,
        output_root=output_root,
        train_worlds=train_worlds,
        validation_worlds=validation_worlds,
        lineages=lineages,
        initializations=initializations,
        field_component=str(payload["field_component"]),
        field_root_digest_by_world=field_roots,
        kappa_bits=kappa,
        output_unit_mode=str(payload["output_unit_mode"]),
        plan_status=str(payload["contract_status"]),
        users=users,
        steps=steps,
        action_dim=action_dim,
    )


def _source_relative(split: str, world: int, lineage: int) -> str:
    return f"sources/{split}/{world}-{lineage}"


def _adapter_config(plan: PanelPlan, *, split: str, world: int, lineage: int, field_root: str) -> dict[str, object]:
    maps = plan.digest_maps()
    return {
        "schema": ADAPTER_SCHEMA,
        "schema_version": ADAPTER_SCHEMA_VERSION,
        "contract_path": str(plan.learner_contract_path),
        "contract_sha256": plan.learner_contract_sha256,
        "code_manifest_path": str(plan.code_manifest_path),
        "code_manifest_sha256": plan.code_manifest_sha256,
        "split": split,
        "world_seed": world,
        "lineage": lineage,
        "declared_worlds": [world],
        "declared_lineages": [lineage],
        "field_root_digest": field_root,
        "q1_checkpoint_root": str(plan.q1_checkpoint_root),
        "q2_checkpoint_root": str(plan.q2_checkpoint_root),
        "prereg_path": str(plan.prereg_path),
        "tle_root": str(plan.tle_root),
        "output_dir": str(plan.output_root / "sources" / split / f"{world}-{lineage}"),
        "q1_checkpoint_sha256": maps["q1_checkpoint_sha256"][lineage],
        "q2_checkpoint_sha256": maps["q2_checkpoint_sha256"][lineage],
        "q1_parameter_sha256": maps["q1_parameter_sha256"][lineage],
        "q2_parameter_sha256": maps["q2_parameter_sha256"][lineage],
        "kappa_bits_hex": float(plan.kappa_bits).hex(),
        "output_unit_mode": plan.output_unit_mode,
        "users": plan.users,
        "steps": plan.steps,
        "action_dim": plan.action_dim,
        "contract_status": FROZEN_CONTRACT_STATUS,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
    }


def _learner_plan(plan: PanelPlan) -> dict[str, object]:
    return {
        "schema": RUN_PLAN_SCHEMA,
        "schema_version": RUN_PLAN_VERSION,
        "contract_sha256": plan.learner_contract_sha256,
        "code_manifest_sha256": plan.code_manifest_sha256,
        "output_unit_mode": plan.output_unit_mode,
        "train_worlds": list(plan.train_worlds),
        "validation_worlds": list(plan.validation_worlds),
        "initialization_lineages": [dict(item) for item in plan.initializations],
        "q1_checkpoint_sha256_by_lineage": [
            {"lineage": lineage, "sha256": value}
            for lineage, value in plan.q1_checkpoint_sha256_by_lineage
        ],
        "q2_checkpoint_sha256_by_lineage": [
            {"lineage": lineage, "sha256": value}
            for lineage, value in plan.q2_checkpoint_sha256_by_lineage
        ],
        "train_source_paths": [
            _source_relative("TRAIN", world, lineage)
            for world in plan.train_worlds
            for lineage in plan.lineages
        ],
        "validation_source_paths": [
            _source_relative("VALIDATION", world, lineage)
            for world in plan.validation_worlds
            for lineage in plan.lineages
        ],
        "rows_per_source": EXPECTED_ROWS,
        "batch_size": EXPECTED_BATCH_SIZE,
        "update_count": EXPECTED_UPDATES,
        "schedule_algorithm": SCHEDULE_ALGORITHM,
        "network": {
            "action_dim": EXPECTED_ACTION_DIM,
            "action_context_dim": EXPECTED_ACTION_CONTEXT_DIM,
            "victim_token_dim": EXPECTED_VICTIM_TOKEN_DIM,
            "hidden_layers": [100, 50, 50],
            "activation": "tanh",
            "learning_rate": 0.001,
            "kappa_bits_hex": float(plan.kappa_bits).hex(),
            "beta": 0.0,
            "output_unit_mode": plan.output_unit_mode,
        },
        "outcome_opened": False,
        "test_split_opened": False,
        "episode_training": False,
    }


@dataclass(frozen=True)
class PanelBuild:
    configs: tuple[tuple[Path, dict[str, object], str], ...]
    learner_plan: dict[str, object]
    learner_config: dict[str, object]
    manifest: dict[str, object]


def build_panel(plan: PanelPlan) -> PanelBuild:
    """Build 21 adapter configs and the learner plan/config in memory."""

    if not isinstance(plan, PanelPlan):
        raise SourcePanelConfigBuilderError("plan must be PanelPlan")
    if plan.plan_status != FROZEN_CONTRACT_STATUS:
        raise SourcePanelConfigBuilderError("panel plan is not frozen before outcome access")
    if (plan.users, plan.steps, plan.action_dim) != (
        EXPECTED_USERS,
        EXPECTED_STEPS,
        EXPECTED_ACTION_DIM,
    ):
        raise SourcePanelConfigBuilderError("panel plan shape is not 100 users x 10 steps x 28 actions")
    field_roots = plan.field_roots()
    configs: list[tuple[Path, dict[str, object], str]] = []
    for split, worlds in (("TRAIN", plan.train_worlds), ("VALIDATION", plan.validation_worlds)):
        for world in worlds:
            for lineage in plan.lineages:
                payload = _adapter_config(
                    plan,
                    split=split,
                    world=world,
                    lineage=lineage,
                    field_root=field_roots[world],
                )
                path = plan.output_root / "adapter-configs" / split / f"{world}-{lineage}.json"
                configs.append((path, payload, hashlib.sha256(_canonical_bytes(payload)).hexdigest()))
    if len(configs) != 21 or len({str(path) for path, _payload, _sha in configs}) != 21:
        raise SourcePanelConfigBuilderError("adapter config rectangle is not exactly 21 unique entries")
    learner_plan = _learner_plan(plan)
    try:
        import relational_run_config_builder_v019 as run_config_builder

        learner_config = run_config_builder.materialize_plan(learner_plan)
    except Exception as error:
        raise SourcePanelConfigBuilderError("learner run-plan materialization failed") from error
    if learner_config.get("train_source_paths") != learner_plan["train_source_paths"] or learner_config.get("validation_source_paths") != learner_plan["validation_source_paths"]:
        raise SourcePanelConfigBuilderError("learner run config source path lists drifted")
    manifest_body = {
        "schema": PANEL_MANIFEST_SCHEMA,
        "schema_version": PANEL_MANIFEST_VERSION,
        "plan_sha256": plan.plan_sha256,
        "learner_contract_path": str(plan.learner_contract_path),
        "learner_contract_sha256": plan.learner_contract_sha256,
        "code_manifest_path": str(plan.code_manifest_path),
        "code_manifest_sha256": plan.code_manifest_sha256,
        "q1_checkpoint_root": str(plan.q1_checkpoint_root),
        "q2_checkpoint_root": str(plan.q2_checkpoint_root),
        "q1_checkpoint_sha256_by_lineage": [
            {"lineage": lineage, "sha256": value}
            for lineage, value in plan.q1_checkpoint_sha256_by_lineage
        ],
        "q2_checkpoint_sha256_by_lineage": [
            {"lineage": lineage, "sha256": value}
            for lineage, value in plan.q2_checkpoint_sha256_by_lineage
        ],
        "q1_parameter_sha256_by_lineage": [
            {"lineage": lineage, "sha256": value}
            for lineage, value in plan.q1_parameter_sha256_by_lineage
        ],
        "q2_parameter_sha256_by_lineage": [
            {"lineage": lineage, "sha256": value}
            for lineage, value in plan.q2_parameter_sha256_by_lineage
        ],
        "prereg_path": str(plan.prereg_path),
        "tle_root": str(plan.tle_root),
        "output_root": str(plan.output_root),
        "train_worlds": list(plan.train_worlds),
        "validation_worlds": list(plan.validation_worlds),
        "lineages": list(plan.lineages),
        "field_component": plan.field_component,
        "field_root_digest_by_world": [
            {"world_seed": world, "sha256": digest}
            for world, digest in plan.field_root_digest_by_world
        ],
        "users": plan.users,
        "steps": plan.steps,
        "rows": EXPECTED_ROWS,
        "action_dim": plan.action_dim,
        "kappa_bits_hex": float(plan.kappa_bits).hex(),
        "output_unit_mode": plan.output_unit_mode,
        "adapter_configs": [
            {
                "split": payload["split"],
                "world_seed": payload["world_seed"],
                "lineage": payload["lineage"],
                "path": str(path),
                "config_sha256": config_sha,
            }
            for path, payload, config_sha in configs
        ],
        "learner_run_plan_path": str(plan.output_root / "learner-run-plan.json"),
        "learner_run_plan_sha256": hashlib.sha256(_canonical_bytes(learner_plan)).hexdigest(),
        "learner_run_config_path": str(plan.output_root / "learner-run-config.json"),
        "learner_run_config_sha256": hashlib.sha256(_canonical_bytes(learner_config)).hexdigest(),
        "learner_train_source_paths": learner_plan["train_source_paths"],
        "learner_validation_source_paths": learner_plan["validation_source_paths"],
        "contract_status": FROZEN_CONTRACT_STATUS,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "outcome_opened": False,
    }
    manifest = {**manifest_body, "manifest_sha256": canonical_sha256(manifest_body)}
    return PanelBuild(
        configs=tuple(configs),
        learner_plan=learner_plan,
        learner_config=learner_config,
        manifest=manifest,
    )


def _read_plan(path: Path, *, expected_sha256: str) -> tuple[dict[str, object], str]:
    supplied = _digest(expected_sha256, field="expected plan_sha256")
    actual = _file_sha256(path)
    if actual != supplied:
        raise SourcePanelConfigBuilderError("panel plan file digest mismatch")
    raw = path.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SourcePanelConfigBuilderError("panel plan is not canonical JSON") from error
    if not isinstance(payload, dict) or raw != _canonical_bytes(payload):
        raise SourcePanelConfigBuilderError("panel plan is not canonical JSON")
    return payload, actual


def _verify_external_inputs(plan: PanelPlan) -> None:
    if _file_sha256(plan.learner_contract_path) != plan.learner_contract_sha256:
        raise SourcePanelConfigBuilderError("learner contract digest mismatch")
    try:
        contract_text = plan.learner_contract_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise SourcePanelConfigBuilderError("learner contract is not readable text") from error
    if "Status: `FROZEN_BEFORE_OUTCOME`" not in contract_text:
        raise SourcePanelConfigBuilderError("learner contract is not frozen before outcome access")
    if _file_sha256(plan.code_manifest_path) != plan.code_manifest_sha256:
        raise SourcePanelConfigBuilderError("code manifest digest mismatch")
    for path, field in (
        (plan.q1_checkpoint_root, "q1_checkpoint_root"),
        (plan.q2_checkpoint_root, "q2_checkpoint_root"),
        (plan.tle_root, "tle_root"),
    ):
        if path.is_symlink() or not path.is_dir():
            raise SourcePanelConfigBuilderError(f"{field} must be a regular directory")
    if plan.prereg_path.is_symlink() or not plan.prereg_path.is_file():
        raise SourcePanelConfigBuilderError("prereg_path must be a regular file")


def _write_once(path: Path, payload: bytes) -> str:
    if path.exists() or path.is_symlink():
        raise SourcePanelConfigBuilderError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        temporary.write_bytes(payload)
        os.link(temporary, path)
    except FileExistsError as error:
        raise SourcePanelConfigBuilderError(f"refusing to overwrite {path}") from error
    finally:
        temporary.unlink(missing_ok=True)
    return _file_sha256(path)


def write_panel(plan_path: str | Path, *, expected_sha256: str) -> dict[str, object]:
    """Authenticate inputs and write the complete panel closure once."""

    source = Path(plan_path)
    payload, plan_sha256 = _read_plan(source, expected_sha256=expected_sha256)
    plan = validate_plan(
        payload,
        plan_sha256=plan_sha256,
        base=source.absolute().parent,
    )
    _verify_external_inputs(plan)
    if plan.output_root.exists() or plan.output_root.is_symlink():
        raise SourcePanelConfigBuilderError(f"refusing to overwrite output root: {plan.output_root}")
    build = build_panel(plan)
    plan.output_root.mkdir(parents=True, exist_ok=False)
    for path, config, _config_sha in build.configs:
        _write_once(path, _canonical_bytes(config))
    learner_plan_path = plan.output_root / "learner-run-plan.json"
    learner_config_path = plan.output_root / "learner-run-config.json"
    manifest_path = plan.output_root / "panel-manifest.json"
    _write_once(learner_plan_path, _canonical_bytes(build.learner_plan))
    _write_once(learner_config_path, _canonical_bytes(build.learner_config))
    manifest_sha256 = _write_once(manifest_path, _canonical_bytes(build.manifest))
    return {
        "plan_sha256": plan_sha256,
        "manifest_sha256": manifest_sha256,
        "config_count": len(build.configs),
        "learner_run_plan_sha256": hashlib.sha256(learner_plan_path.read_bytes()).hexdigest(),
        "learner_run_config_sha256": hashlib.sha256(learner_config_path.read_bytes()).hexdigest(),
        "output_root": str(plan.output_root),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        result = write_panel(args.plan, expected_sha256=args.plan_sha256)
    except SourcePanelConfigBuilderError as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - explicit write boundary
    raise SystemExit(main())


__all__ = [
    "ADAPTER_SCHEMA",
    "EXPECTED_ACTION_DIM",
    "EXPECTED_KAPPA_HEX",
    "EXPECTED_ROWS",
    "EXPECTED_STEPS",
    "EXPECTED_USERS",
    "FORBIDDEN_PRIOR_WORLDS",
    "PANEL_MANIFEST_SCHEMA",
    "PANEL_PLAN_SCHEMA",
    "PanelBuild",
    "PanelPlan",
    "SourcePanelConfigBuilderError",
    "build_panel",
    "canonical_sha256",
    "main",
    "validate_plan",
    "write_panel",
]
