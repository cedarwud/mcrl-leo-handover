"""Thin V0.18 simulator-to-source adapter.

The adapter owns only the wiring from the already frozen V0.18/V0.15 runtime
to :func:`relational_source_harvester.harvest_source_shard`.  It has no
defaults for panel identity or checkpoint roots: a canonical external config
and its expected file digest are required.  Importing this module never opens
an environment or reads a checkpoint.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile
from types import ModuleType
from typing import Any

import numpy as np


_R2_ROOT = Path(__file__).resolve().parent
_REPO = _R2_ROOT.parents[2]
_DRAFT_ROOT = _R2_ROOT.parent / "next-learner-draft"
_SOURCE_ROOT = _REPO / "src"
for _path in (_R2_ROOT, _DRAFT_ROOT, _SOURCE_ROOT, _REPO):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.runtime.ee_axis_ops3 import OPS3_KAPPA_BITS  # noqa: E402
from relational_source_harvester import (  # noqa: E402
    ACTION_DIM,
    EXPECTED_STEPS,
    EXPECTED_USERS,
    AnchorInput,
    ExactZ3Label,
    SourceHarvestConfig,
    SourceHarvesterError,
    AuthenticatedHarvest,
    harvest_source_shard,
    make_v018_anchor_input,
)


ADAPTER_SCHEMA = "multi-catfish-mcrl-v018-relational-zr-simulator-source-config-v1"
ADAPTER_SCHEMA_VERSION = 1
FROZEN_CONTRACT_STATUS = "FROZEN_BEFORE_OUTCOME"
ALLOWED_SPLITS = frozenset({"TRAIN", "VALIDATION"})
CONFIG_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "contract_path",
        "contract_sha256",
        "code_manifest_path",
        "code_manifest_sha256",
        "split",
        "world_seed",
        "lineage",
        "declared_worlds",
        "declared_lineages",
        "field_root_digest",
        "q1_checkpoint_root",
        "q2_checkpoint_root",
        "prereg_path",
        "tle_root",
        "output_dir",
        "q1_checkpoint_sha256",
        "q2_checkpoint_sha256",
        "q1_parameter_sha256",
        "q2_parameter_sha256",
        "kappa_bits_hex",
        "users",
        "steps",
        "action_dim",
        "contract_status",
        "test_split_opened",
        "episode_training",
        "learner_update",
    }
)


class SimulatorSourceAdapterError(ValueError):
    """An external config, frozen binding, or adapter boundary failed."""


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
        raise SimulatorSourceAdapterError("config is not finite canonical JSON") from error


def _file_sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise SimulatorSourceAdapterError(f"expected a regular file: {path}")
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as error:
        raise SimulatorSourceAdapterError(f"cannot read file: {path}") from error
    return digest.hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise SimulatorSourceAdapterError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise SimulatorSourceAdapterError(f"{field} must be a positive integer")
    return value


def _path(value: object, *, field: str, base: Path) -> Path:
    if not isinstance(value, str) or not value:
        raise SimulatorSourceAdapterError(f"{field} must be a nonempty path")
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = base / candidate
    candidate = candidate.absolute()
    if candidate.is_symlink():
        raise SimulatorSourceAdapterError(f"{field} must not be a symlink")
    return candidate


@dataclass(frozen=True)
class SimulatorShardConfig:
    """Fully external source-shard identity and frozen input roots."""

    config_sha256: str
    contract_path: Path
    contract_sha256: str
    code_manifest_path: Path
    code_manifest_sha256: str
    split: str
    world_seed: int
    lineage: int
    declared_worlds: tuple[int, ...]
    declared_lineages: tuple[int, ...]
    field_root_digest: str
    q1_checkpoint_root: Path
    q2_checkpoint_root: Path
    prereg_path: Path
    tle_root: Path
    output_dir: Path
    q1_checkpoint_sha256: str
    q2_checkpoint_sha256: str
    q1_parameter_sha256: str
    q2_parameter_sha256: str
    kappa_bits: float
    users: int = EXPECTED_USERS
    steps: int = EXPECTED_STEPS
    action_dim: int = ACTION_DIM

    def __post_init__(self) -> None:
        _digest(self.config_sha256, field="config_sha256")
        _digest(self.contract_sha256, field="contract_sha256")
        _digest(self.code_manifest_sha256, field="code_manifest_sha256")
        for field in (
            "field_root_digest",
            "q1_checkpoint_sha256",
            "q2_checkpoint_sha256",
            "q1_parameter_sha256",
            "q2_parameter_sha256",
        ):
            _digest(getattr(self, field), field=field)
        _positive_int(self.world_seed, field="world_seed")
        _positive_int(self.lineage, field="lineage")
        if self.split not in ALLOWED_SPLITS:
            raise SimulatorSourceAdapterError("split must be TRAIN or VALIDATION")
        if not self.declared_worlds or len(set(self.declared_worlds)) != len(self.declared_worlds):
            raise SimulatorSourceAdapterError("declared_worlds must be unique and nonempty")
        if not self.declared_lineages or len(set(self.declared_lineages)) != len(self.declared_lineages):
            raise SimulatorSourceAdapterError("declared_lineages must be unique and nonempty")
        if self.world_seed not in self.declared_worlds or self.lineage not in self.declared_lineages:
            raise SimulatorSourceAdapterError("world/lineage is outside the external declaration")
        if self.users != EXPECTED_USERS or self.steps != EXPECTED_STEPS:
            raise SimulatorSourceAdapterError("source shard must be exactly 10 steps x 100 users")
        if self.action_dim != ACTION_DIM:
            raise SimulatorSourceAdapterError("action_dim is not the native 28-action surface")
        if float(self.kappa_bits).hex() != float(OPS3_KAPPA_BITS).hex():
            raise SimulatorSourceAdapterError("kappa_bits differs from the native frozen scale")

    def harvest_config(self) -> SourceHarvestConfig:
        return SourceHarvestConfig(
            contract_sha256=self.contract_sha256,
            config_sha256=self.config_sha256,
            code_manifest_sha256=self.code_manifest_sha256,
            world_seed=self.world_seed,
            lineage=self.lineage,
            split=self.split,
            field_root_digest=self.field_root_digest,
            q1_checkpoint_sha256=self.q1_checkpoint_sha256,
            q2_checkpoint_sha256=self.q2_checkpoint_sha256,
            q1_parameter_sha256=self.q1_parameter_sha256,
            q2_parameter_sha256=self.q2_parameter_sha256,
            kappa_bits=self.kappa_bits,
            declared_worlds=self.declared_worlds,
            declared_lineages=self.declared_lineages,
            users=self.users,
            steps=self.steps,
            action_dim=self.action_dim,
        )


def load_shard_config(path: str | Path, *, expected_sha256: str) -> SimulatorShardConfig:
    """Read one canonical config and require its externally supplied digest."""

    config_path = Path(path)
    supplied = _digest(expected_sha256, field="expected config_sha256")
    actual = _file_sha256(config_path)
    if actual != supplied:
        raise SimulatorSourceAdapterError("config file digest mismatch")
    raw = config_path.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SimulatorSourceAdapterError("config is not canonical JSON") from error
    if not isinstance(payload, dict) or raw != _canonical_bytes(payload):
        raise SimulatorSourceAdapterError("config is not canonical JSON")
    if set(payload) != CONFIG_FIELDS:
        raise SimulatorSourceAdapterError("config fields are not closed")
    base = config_path.absolute().parent
    try:
        declared_worlds = tuple(
            _positive_int(value, field="declared_worlds")
            for value in payload["declared_worlds"]
        )
        declared_lineages = tuple(
            _positive_int(value, field="declared_lineages")
            for value in payload["declared_lineages"]
        )
        kappa_hex = payload["kappa_bits_hex"]
        if not isinstance(kappa_hex, str):
            raise TypeError("kappa_bits_hex is not text")
        kappa_bits = float.fromhex(kappa_hex)
        if not math.isfinite(kappa_bits) or kappa_bits <= 0.0:
            raise ValueError("kappa_bits_hex is not finite and positive")
        config = SimulatorShardConfig(
            config_sha256=actual,
            contract_path=_path(payload["contract_path"], field="contract_path", base=base),
            contract_sha256=str(payload["contract_sha256"]),
            code_manifest_path=_path(
                payload["code_manifest_path"], field="code_manifest_path", base=base
            ),
            code_manifest_sha256=str(payload["code_manifest_sha256"]),
            split=str(payload["split"]),
            world_seed=_positive_int(payload["world_seed"], field="world_seed"),
            lineage=_positive_int(payload["lineage"], field="lineage"),
            declared_worlds=declared_worlds,
            declared_lineages=declared_lineages,
            field_root_digest=str(payload["field_root_digest"]),
            q1_checkpoint_root=_path(
                payload["q1_checkpoint_root"], field="q1_checkpoint_root", base=base
            ),
            q2_checkpoint_root=_path(
                payload["q2_checkpoint_root"], field="q2_checkpoint_root", base=base
            ),
            prereg_path=_path(payload["prereg_path"], field="prereg_path", base=base),
            tle_root=_path(payload["tle_root"], field="tle_root", base=base),
            output_dir=_path(payload["output_dir"], field="output_dir", base=base),
            q1_checkpoint_sha256=str(payload["q1_checkpoint_sha256"]),
            q2_checkpoint_sha256=str(payload["q2_checkpoint_sha256"]),
            q1_parameter_sha256=str(payload["q1_parameter_sha256"]),
            q2_parameter_sha256=str(payload["q2_parameter_sha256"]),
            kappa_bits=kappa_bits,
            users=_positive_int(payload["users"], field="users"),
            steps=_positive_int(payload["steps"], field="steps"),
            action_dim=_positive_int(payload["action_dim"], field="action_dim"),
        )
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        if isinstance(error, SimulatorSourceAdapterError):
            raise
        raise SimulatorSourceAdapterError("config values are malformed") from error
    if payload["schema"] != ADAPTER_SCHEMA or payload["schema_version"] != ADAPTER_SCHEMA_VERSION:
        raise SimulatorSourceAdapterError("adapter config schema is stale")
    if payload["contract_status"] != FROZEN_CONTRACT_STATUS:
        raise SimulatorSourceAdapterError("contract is not frozen before outcome access")
    if any(payload[field] is not False for field in ("test_split_opened", "episode_training", "learner_update")):
        raise SimulatorSourceAdapterError("adapter config crosses a forbidden boundary")
    return config


@dataclass(frozen=True)
class RuntimeBindings:
    """Lazily loaded V0.18/V0.15 modules, injectable by pure tests."""

    v018: ModuleType
    v015: ModuleType
    zr_builder: Callable[..., Any]


def load_runtime() -> RuntimeBindings:
    """Load the existing V0.18 runner and its V0.15 helper module."""

    path = _REPO / ".scratch" / "multi-catfish-v018-relational-zr" / "run_v018_analytic_diagnostic.py"
    spec = importlib.util.spec_from_file_location("mcrl_v018_source_runtime", path)
    if spec is None or spec.loader is None:
        raise SimulatorSourceAdapterError(f"cannot import V0.18 runner: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        v015 = module._V015
        builder = v015._V013.build_zr_surface
    except (AttributeError, ImportError, OSError, RuntimeError) as error:
        raise SimulatorSourceAdapterError("cannot load V0.18/V0.15 runtime helpers") from error
    if not callable(builder):
        raise SimulatorSourceAdapterError("V0.15 exact ZR builder is not callable")
    return RuntimeBindings(v018=module, v015=v015, zr_builder=builder)


def build_exact_zr_label(
    measurements: Any,
    interval_s: float,
    *,
    kappa_bits: float,
    zr_builder: Callable[..., Any],
) -> ExactZ3Label:
    """Build native centered ``z3_bits`` through the canonical ZR builder."""

    try:
        references = np.asarray(measurements.reference_actions, dtype=np.int64)
        legal = np.asarray(measurements.legal_mask, dtype=np.bool_)
        compatibility = np.asarray(measurements.compatible, dtype=np.bool_)
        baseline = np.asarray(measurements.reference_rate_bps, dtype=np.float64)
        candidate = np.asarray(measurements.candidate_rate_bps, dtype=np.float64)
    except (AttributeError, TypeError, ValueError) as error:
        raise SimulatorSourceAdapterError("exact measurement payload is malformed") from error
    if (
        references.ndim != 1
        or legal.shape != (references.size, ACTION_DIM)
        or compatibility.shape != legal.shape
        or baseline.shape != (references.size, references.size)
        or candidate.shape != (references.size, ACTION_DIM, references.size)
        or not np.all(np.isfinite(baseline))
        or not np.all(np.isfinite(candidate))
    ):
        raise SimulatorSourceAdapterError("exact measurement surfaces are malformed")
    rows: list[np.ndarray] = []
    for uid in range(references.size):
        try:
            surface = zr_builder(
                baseline_rate_bps=baseline[uid],
                candidate_rate_bps=candidate[uid],
                compatibility=compatibility[uid],
                legal_mask=legal[uid],
                reference_action=int(references[uid]),
                interval_s=float(interval_s),
                kappa_bits=float(kappa_bits),
            )
            bits = np.asarray(surface.z3_bits, dtype=np.float64)
        except (AttributeError, TypeError, ValueError, RuntimeError) as error:
            raise SimulatorSourceAdapterError("canonical exact ZR surface failed") from error
        if bits.shape != (ACTION_DIM,) or not np.all(np.isfinite(bits)):
            raise SimulatorSourceAdapterError("canonical exact ZR z3_bits is malformed")
        rows.append(bits)
    z3_bits = np.asarray(rows, dtype=np.float64)
    if np.any((z3_bits > 0.0) & ~compatibility):
        raise SimulatorSourceAdapterError("positive exact z3_bits escaped compatibility")
    return ExactZ3Label(z3_bits=z3_bits, positive_credit_compatible=compatibility)


def _checkpoint_digests(
    runtime: RuntimeBindings,
    q1_receipt: Mapping[str, Any],
    q2_receipt: Mapping[str, Any],
) -> tuple[str, str]:
    try:
        return (
            runtime.v015.file_sha256(Path(str(q1_receipt["checkpoint_path"]))),
            runtime.v015.file_sha256(Path(str(q2_receipt["checkpoint_path"]))),
        )
    except (AttributeError, KeyError, OSError, TypeError, ValueError) as error:
        raise SimulatorSourceAdapterError("frozen checkpoint receipt is malformed") from error


def _validate_frozen_bindings(
    config: SimulatorShardConfig,
    runtime: RuntimeBindings,
) -> tuple[Any, Mapping[str, Any], Any, Mapping[str, Any], Any]:
    if _file_sha256(config.code_manifest_path) != config.code_manifest_sha256:
        raise SimulatorSourceAdapterError("code manifest file digest mismatch")
    if _file_sha256(config.contract_path) != config.contract_sha256:
        raise SimulatorSourceAdapterError("contract file digest mismatch")
    try:
        contract_text = config.contract_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise SimulatorSourceAdapterError("learner contract is not readable text") from error
    if "Status: `FROZEN_BEFORE_OUTCOME`" not in contract_text:
        raise SimulatorSourceAdapterError(
            "learner contract is not frozen before outcome access"
        )
    try:
        # Authenticate the already frozen analytic/formula authority at its
        # own pinned path.  The new learner contract has a different digest
        # and vocabulary and must not be passed to that validator.
        runtime.v018.validate_v018_contract()
        runtime.v015.validate_v015_contract()
        gate = runtime.v015.validate_v014_gate_receipts(config.q2_checkpoint_root)
        q1, q1_receipt = runtime.v015.load_frozen_q1(
            config.q1_checkpoint_root, config.lineage
        )
        q2, q2_receipt = runtime.v015.load_frozen_q2(
            config.q2_checkpoint_root,
            lineage=config.lineage,
            gate_receipt=gate,
        )
    except Exception as error:  # pragma: no cover - live helper-specific failures
        if isinstance(error, SimulatorSourceAdapterError):
            raise
        raise SimulatorSourceAdapterError("frozen Q1/Q2 loading failed") from error
    for field, receipt in (
        ("q1_checkpoint_sha256", q1_receipt),
        ("q2_checkpoint_sha256", q2_receipt),
    ):
        if receipt.get("checkpoint_sha256") != getattr(config, field):
            raise SimulatorSourceAdapterError(f"{field} disagrees with frozen receipt")
    try:
        q1_parameter = runtime.v015._q_parameter_sha256(q1)
        q2_parameter = runtime.v015._q_parameter_sha256(q2)
    except (AttributeError, TypeError, ValueError, RuntimeError) as error:
        raise SimulatorSourceAdapterError("frozen Q1/Q2 parameter digest failed") from error
    if q1_parameter != config.q1_parameter_sha256 or q2_parameter != config.q2_parameter_sha256:
        raise SimulatorSourceAdapterError("frozen Q1/Q2 parameter digest mismatch")
    return q1, q1_receipt, q2, q2_receipt, gate


def _anchor_provider(
    config: SimulatorShardConfig,
    runtime: RuntimeBindings,
    *,
    environment: Any,
    step_env: Any,
    env_rng: np.random.Generator,
    observation: Any,
    q1: Any,
    q1_receipt: Mapping[str, Any],
    q2: Any,
    q2_receipt: Mapping[str, Any],
    interval_s: float,
) -> Callable[[int], AnchorInput]:
    current_observation = observation

    def provider(step_index: int) -> AnchorInput:
        nonlocal current_observation
        if step_index < 0 or step_index >= config.steps:
            raise SimulatorSourceAdapterError("step index is outside the ten-step shard")
        try:
            native = runtime.v018.encode_ee_axis_state(step_env, current_observation)
            masks = np.asarray(native.action_masks, dtype=np.bool_)
            q1_values = runtime.v018._q1_values(q1, native.state_matrix, masks)
            q1_reference = runtime.v015.select_actions(
                q1_values,
                np.zeros_like(q1_values),
                np.zeros_like(q1_values),
                masks,
                include_c3=False,
            )
            ops3_anchor = runtime.v018.snapshot_ops3_anchor(step_env, current_observation)
            projection = runtime.v018.project_ops3_anchor(ops3_anchor)
            ops3_surfaces = runtime.v018.build_ops3_live_surfaces(
                ops3_anchor, projection, q1_reference
            )
            q2_state = runtime.v015.encode_ee_axis_v014_q2_states(ops3_surfaces)
            q2_state.verify()
            if not np.array_equal(q2_state.action_masks, masks):
                raise SimulatorSourceAdapterError("Q1/Q2 native masks disagree")
            learned_q2 = runtime.v018._q2_values(
                q2, q2_state.state_matrix, q2_state.action_masks
            )
            anchor = runtime.v018._current_required_power_and_opening(
                current_gain_linear=ops3_anchor.current_gain_linear,
                segment_start_gain_linear=ops3_anchor.segment_start_gain_linear,
                action_masks=masks,
            )
            required_power, opening = anchor
            background = np.argmax(
                np.where(masks, np.asarray(q1_values) + np.asarray(learned_q2), -np.inf),
                axis=1,
            ).astype(np.int64)
        except (AttributeError, TypeError, ValueError, RuntimeError) as error:
            if isinstance(error, SimulatorSourceAdapterError):
                raise
            raise SimulatorSourceAdapterError("V0.18 anchor construction failed") from error

        def exact_provider(_capture: Any) -> ExactZ3Label:
            try:
                measurements = runtime.v018.measure_zero_marginal_c3(
                    step_env,
                    observation=current_observation,
                    reference_actions=background,
                    rng=env_rng,
                    include_insertion=False,
                    interval_s=interval_s,
                )
                label = build_exact_zr_label(
                    measurements,
                    interval_s,
                    kappa_bits=config.kappa_bits,
                    zr_builder=runtime.zr_builder,
                )
                # The analytic runner remains the independent canonical Q3
                # wiring check; persisted source receives only native z3_bits.
                canonical_q3, _method = runtime.v018._exact_zr_surface(
                    measurements, interval_s
                )
                if not np.array_equal(
                    label.z3_bits / float(config.kappa_bits),
                    np.asarray(canonical_q3, dtype=np.float64),
                ):
                    raise SimulatorSourceAdapterError("exact ZR helper disagrees with z3_bits")
                return label
            except (AttributeError, TypeError, ValueError, RuntimeError) as error:
                if isinstance(error, SimulatorSourceAdapterError):
                    raise
                raise SimulatorSourceAdapterError("exact ZR measurement failed") from error

        def execute(actions: np.ndarray) -> None:
            nonlocal current_observation
            try:
                result = environment.step(actions, env_rng)
                if bool(result.done) and step_index != config.steps - 1:
                    raise SimulatorSourceAdapterError("environment terminated before ten steps")
                current_observation = environment.last_outcome.observation
            except (AttributeError, TypeError, ValueError, RuntimeError) as error:
                if isinstance(error, SimulatorSourceAdapterError):
                    raise
                raise SimulatorSourceAdapterError("background action/advance failed") from error

        return make_v018_anchor_input(
            step_index=step_index,
            environment=step_env,
            observation=current_observation,
            q1=q1_values,
            learned_q2=learned_q2,
            action_mask=masks,
            required_power_surface=required_power,
            opening_feasibility_surface=opening,
            pmax_w=runtime.v018.BEAM_POWER_MAX_W,
            exact_target_provider=exact_provider,
            live_rng_digest=lambda: runtime.v018._live_digest(environment, env_rng),
            checkpoint_digests=lambda: _checkpoint_digests(runtime, q1_receipt, q2_receipt),
            parameter_digests=lambda: (
                runtime.v015._q_parameter_sha256(q1),
                runtime.v015._q_parameter_sha256(q2),
            ),
            execute_background_action=execute,
        )

    return provider


def run_source_shard(
    config: SimulatorShardConfig,
    *,
    runtime: RuntimeBindings | None = None,
) -> AuthenticatedHarvest:
    """Load frozen inputs, create one keyed TLE environment, and harvest ten steps."""

    if not isinstance(config, SimulatorShardConfig):
        raise SimulatorSourceAdapterError("config must be SimulatorShardConfig")
    runtime = load_runtime() if runtime is None else runtime
    q1, q1_receipt, q2, q2_receipt, _gate = _validate_frozen_bindings(config, runtime)
    try:
        field = runtime.v018.field_for_world(config.world_seed)
        if field.root_digest != config.field_root_digest:
            raise SimulatorSourceAdapterError("keyed field root digest mismatch")
        record = runtime.v015._V013.read_prereg(config.prereg_path)
        env_rng, mobility_rng, _action_rng, _control_rng = runtime.v015._V013.screen._evaluation_rngs(
            config.world_seed
        )
    except (AttributeError, TypeError, ValueError, RuntimeError) as error:
        if isinstance(error, SimulatorSourceAdapterError):
            raise
        raise SimulatorSourceAdapterError("frozen world/helper setup failed") from error

    with tempfile.TemporaryDirectory(prefix="mcrl-v018-source-tle-") as temporary:
        try:
            archive = runtime.v015._V013.screen._frozen_archive(
                record, config.tle_root, Path(temporary) / "frozen-tle"
            )
            environment = runtime.v015._V013.screen._make_environment(
                archive, users=config.users
            )
            environment.environment._fading_field = field
            _states, _masks, observation = environment.reset(env_rng, mobility_rng)
            step_env = environment.environment
            interval_s = float(step_env.driver.config.ephemeris.time_step_s)
        except (AttributeError, TypeError, ValueError, RuntimeError) as error:
            if isinstance(error, SimulatorSourceAdapterError):
                raise
            raise SimulatorSourceAdapterError("TLE environment construction failed") from error
        provider = _anchor_provider(
            config,
            runtime,
            environment=environment,
            step_env=step_env,
            env_rng=env_rng,
            observation=observation,
            q1=q1,
            q1_receipt=q1_receipt,
            q2=q2,
            q2_receipt=q2_receipt,
            interval_s=interval_s,
        )
        try:
            return harvest_source_shard(config.harvest_config(), provider, config.output_dir)
        except SourceHarvesterError:
            raise
        except Exception as error:  # pragma: no cover - adapter-specific failures
            raise SimulatorSourceAdapterError("source shard harvest failed") from error


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--config-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        config = load_shard_config(args.config, expected_sha256=args.config_sha256)
        result = run_source_shard(config)
    except (SimulatorSourceAdapterError, SourceHarvesterError) as error:
        parser.error(str(error))
    print(
        json.dumps(
            {
                "schema": ADAPTER_SCHEMA,
                "output_dir": str(config.output_dir),
                "harvest_metadata_sha256": result.metadata["harvest_metadata_sha256"],
                "rows": result.source.rows,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI is an explicit run boundary
    raise SystemExit(main())


__all__ = [
    "ADAPTER_SCHEMA",
    "ADAPTER_SCHEMA_VERSION",
    "CONFIG_FIELDS",
    "RuntimeBindings",
    "SimulatorShardConfig",
    "SimulatorSourceAdapterError",
    "build_exact_zr_label",
    "load_runtime",
    "load_shard_config",
    "main",
    "run_source_shard",
]
