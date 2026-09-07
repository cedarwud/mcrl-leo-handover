#!/usr/bin/env python3
"""Canonical physical callbacks for the V0.19 five-arm TRAIN screen.

This module is the post-gate binding layer for
``v019_five_arm_screen.run_five_arm_screen``.  It deliberately has no default
experiment invocation: constructing an adapter only authenticates the
supplied frozen Q3 panel and stores callback dependencies.  A caller must
explicitly provide the gate result, all three learned-Q3 checkpoint paths and
hashes, the already-frozen Q1/Q2 loaders, a TLE archive/environment factory,
and the independent frozen MAIN policy.

The route callback follows the physical V0.15/V0.16 path for Q1 and Q2 and
replaces only the old C3 state/decoder:

``r12 = argmax_safe(Q1 + Q2)`` is computed once at each predecision anchor.
The V0.19 relational state and learned Q3 surface are built from that same
reference for ``FULL``, ``DROP_C1`` and ``DROP_C2``.  Those arms differ only
in their final score sum.  ``DROP_C3`` never constructs or calls Q3.

Every loaded network is switched to eval/no-gradient mode.  The episode
method only executes the selected action in the canonical environment and
returns an additive bits/energy receipt.  It has no optimizer, replay, TEST,
or source-harvesting path.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, TypeAlias

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
V019_ROOT = HERE.parent
REPO = V019_ROOT.parents[1]
LEARNER_ROOT = V019_ROOT / "learner"
for _path in (REPO, REPO / "src", LEARNER_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.errors import MCRLContractError  # noqa: E402
from mcrl.runtime.ee_axis_ops3 import OPS3_KAPPA_BITS  # noqa: E402
from mcrl.runtime.ee_axis_ops3_live import (  # noqa: E402
    build_ops3_live_surfaces,
    project_ops3_anchor,
    snapshot_ops3_anchor,
)
from mcrl.runtime.ee_axis_relational_zr_c3 import (  # noqa: E402
    encode_relational_zr_c3_state,
)
from mcrl.runtime.ee_axis_state import encode_ee_axis_state  # noqa: E402
from mcrl.env.link_budget import BEAM_POWER_MAX_W  # noqa: E402

from relational_q3_learner_v019 import (  # noqa: E402
    NORMALIZED_BITS_PER_KAPPA,
    RelationalLearnerError,
    RelationalZRC3LearnerConfig,
    RelationalZRC3PairwiseLearner,
)
from relational_source_schema import (  # noqa: E402
    FEATURE_FIELDS,
    RelationalSourceError,
    RelationalZRC3Source,
)


SCREEN_PATH = HERE / "v019_five_arm_screen.py"
SCREEN_SPEC = importlib.util.spec_from_file_location(
    "mcrl_v019_five_arm_screen_physical_binding", SCREEN_PATH
)
if SCREEN_SPEC is None or SCREEN_SPEC.loader is None:  # pragma: no cover - import guard
    raise RuntimeError(f"cannot load V0.19 five-arm screen: {SCREEN_PATH}")
screen = importlib.util.module_from_spec(SCREEN_SPEC)
sys.modules[SCREEN_SPEC.name] = screen
SCREEN_SPEC.loader.exec_module(screen)


PHYSICAL_RUNNER_SCHEMA = "multi-catfish-mcrl-v019-relational-zr-five-arm-physical-v1"
GATE_RESULT_SCHEMA = "multi-catfish-mcrl-v019-relational-q3-gate-orchestrator-v1"
GATE_DECISION = "PASS_LEARNER_GATE"
Q3_CHECKPOINT_SCHEMA = "multi-catfish-mcrl-v019-relational-zr-c3-checkpoint-v1"
Q3_ALGORITHM = "multi-catfish-mcrl-v019-relational-zr-c3-pairwise-learner"
Q3_OUTPUT_UNIT_MODE = NORMALIZED_BITS_PER_KAPPA
Q3_UPDATE_RUNG = 100
USERS = 100
STEPS = 10
TRAIN_SPLIT = "TRAIN"
CLAIM_CEILING = screen.CLAIM_CEILING


class V019PhysicalAdapterError(MCRLContractError):
    """A V0.19 physical binding or receipt boundary failed."""


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V019PhysicalAdapterError(f"{field} must be a lowercase SHA-256")
    return value


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise V019PhysicalAdapterError(f"{field} must be a positive integer")
    result = int(value)
    if result <= 0:
        raise V019PhysicalAdapterError(f"{field} must be a positive integer")
    return result


def file_sha256(path: str | Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V019PhysicalAdapterError(f"expected a regular file: {source}")
    digest = hashlib.sha256()
    try:
        with source.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as error:
        raise V019PhysicalAdapterError(f"cannot read file: {source}") from error
    return digest.hexdigest()


def _read_json(path: str | Path, *, field: str) -> dict[str, Any]:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise V019PhysicalAdapterError(f"cannot read {field}: {source}") from error
    if not isinstance(payload, dict):
        raise V019PhysicalAdapterError(f"{field} must be a JSON object")
    return payload


def _array_sha256(value: object) -> str:
    array = np.ascontiguousarray(np.asarray(value))
    digest = hashlib.sha256()
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


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
        raise V019PhysicalAdapterError("payload is not finite canonical JSON") from error


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _parameter_sha256(network: Any) -> str:
    state = getattr(network, "state_dict", None)
    if not callable(state):
        raise V019PhysicalAdapterError("frozen network has no state_dict")
    digest = hashlib.sha256()
    try:
        values = state()
        for name, value in values.items():
            tensor = value.detach().cpu().contiguous()
            digest.update(str(name).encode("utf-8"))
            digest.update(str(tensor.dtype).encode("ascii"))
            digest.update(repr(tuple(tensor.shape)).encode("ascii"))
            digest.update(tensor.numpy().tobytes(order="C"))
    except (AttributeError, TypeError, ValueError, RuntimeError) as error:
        raise V019PhysicalAdapterError("cannot hash frozen network parameters") from error
    return digest.hexdigest()


def _optimizer_sha256(learner: Any) -> str:
    optimizer = getattr(learner, "optimizer", None)
    if optimizer is None or not callable(getattr(optimizer, "state_dict", None)):
        raise V019PhysicalAdapterError("frozen Q3 learner has no optimizer state")
    buffer = io.BytesIO()
    try:
        torch.save(optimizer.state_dict(), buffer)
    except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as error:
        raise V019PhysicalAdapterError("cannot hash frozen Q3 optimizer") from error
    return hashlib.sha256(buffer.getvalue()).hexdigest()


def _snapshots_equal(left: object, right: object) -> bool:
    """Compare tensor-containing frozen-policy snapshots without tensor ``!=``."""

    if isinstance(left, torch.Tensor) and isinstance(right, torch.Tensor):
        return bool(torch.equal(left, right))
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        return set(left) == set(right) and all(
            _snapshots_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, (tuple, list)) and isinstance(right, (tuple, list)):
        return len(left) == len(right) and all(
            _snapshots_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    try:
        return bool(left == right)
    except (TypeError, ValueError):
        return False


def _surface(network: Any, states: object, masks: object, *, field: str) -> np.ndarray:
    values = np.asarray(states, dtype=np.float32)
    legal = np.asarray(masks)
    if values.ndim != 2 or legal.dtype != np.bool_ or legal.shape != (
        values.shape[0],
        screen.ACTION_DIM,
    ):
        raise V019PhysicalAdapterError(f"{field} state/mask input is malformed")
    if not np.all(np.isfinite(values)) or not np.all(np.any(legal, axis=1)):
        raise V019PhysicalAdapterError(f"{field} state/mask input is invalid")
    try:
        network.eval()
        network.requires_grad_(False)
        with torch.no_grad():
            output = network(
                torch.tensor(values, dtype=torch.float32),
                torch.tensor(legal, dtype=torch.bool),
            )
    except (AttributeError, TypeError, RuntimeError, ValueError) as error:
        raise V019PhysicalAdapterError(f"{field} inference failed") from error
    result = np.asarray(output.detach().cpu().numpy(), dtype=np.float64)
    if result.shape != legal.shape or not np.all(np.isfinite(result)):
        raise V019PhysicalAdapterError(f"{field} surface is malformed")
    return result


def _action_trace_update(digest: "hashlib._Hash", actions: object) -> None:
    values = np.ascontiguousarray(np.asarray(actions, dtype=np.int64))
    digest.update(values.dtype.str.encode("ascii"))
    digest.update(repr(tuple(values.shape)).encode("ascii"))
    digest.update(values.tobytes(order="C"))


def _validate_action_vector(actions: object, masks: object, *, field: str) -> np.ndarray:
    values = np.asarray(actions)
    legal = np.asarray(masks)
    if legal.dtype != np.bool_ or legal.ndim != 2 or legal.shape[1] != screen.ACTION_DIM:
        raise V019PhysicalAdapterError(f"{field} safe mask is malformed")
    if not np.all(np.any(legal, axis=1)):
        raise V019PhysicalAdapterError(f"{field} safe mask has an empty row")
    if values.shape != (legal.shape[0],) or values.dtype.kind not in "iu" or values.dtype.kind == "b":
        raise V019PhysicalAdapterError(f"{field} action vector is malformed")
    result = np.asarray(values, dtype=np.int64)
    if np.any(result < 0) or np.any(result >= screen.ACTION_DIM):
        raise V019PhysicalAdapterError(f"{field} action is outside native range")
    rows = np.arange(result.shape[0])
    if np.any(~legal[rows, result]):
        raise V019PhysicalAdapterError(f"{field} action is outside the common safe mask")
    return np.array(result, dtype=np.int64, copy=True, order="C")


@dataclass(frozen=True)
class V019GateBinding:
    """Authenticated source-only PASS result that unlocks Q3 checkpoint use."""

    result_path: Path
    result_sha256: str
    contract_sha256: str
    source_sha256: str
    code_manifest_sha256: str
    independent_verification_sha256: str

    def verify(self) -> None:
        for field in (
            "result_sha256",
            "contract_sha256",
            "source_sha256",
            "code_manifest_sha256",
            "independent_verification_sha256",
        ):
            _digest(getattr(self, field), field=field)
        if file_sha256(self.result_path) != self.result_sha256:
            raise V019PhysicalAdapterError("gate result bytes changed after authentication")


def authenticate_gate_result(
    result_path: str | Path,
    *,
    expected_result_sha256: str,
    expected_contract_sha256: str | None = None,
    expected_source_sha256: str | None = None,
    expected_code_manifest_sha256: str | None = None,
) -> V019GateBinding:
    """Require an exact, source-only ``PASS_LEARNER_GATE`` result."""

    path = Path(result_path)
    expected_result = _digest(expected_result_sha256, field="expected_result_sha256")
    actual = file_sha256(path)
    if actual != expected_result:
        raise V019PhysicalAdapterError("gate result does not match supplied digest")
    payload = _read_json(path, field="V0.19 learner-gate result")
    if payload.get("schema") != GATE_RESULT_SCHEMA:
        raise V019PhysicalAdapterError("gate result schema is not V0.19 orchestrator result")
    if payload.get("decision") != GATE_DECISION:
        raise V019PhysicalAdapterError("physical screen requires PASS_LEARNER_GATE")
    if payload.get("output_unit_mode") != Q3_OUTPUT_UNIT_MODE:
        raise V019PhysicalAdapterError("gate result is not normalized_bits_per_kappa")
    for field in ("test_split_opened", "episode_training", "learner_update"):
        if bool(payload.get(field, False)):
            raise V019PhysicalAdapterError(f"gate result crossed forbidden {field} boundary")
    contract = _digest(payload.get("contract_sha256"), field="contract_sha256")
    source = _digest(payload.get("source_panel_sha256"), field="source_panel_sha256")
    manifest = _digest(payload.get("code_manifest_sha256"), field="code_manifest_sha256")
    verification = _digest(
        payload.get("independent_verification_sha256"),
        field="independent_verification_sha256",
    )
    for supplied, actual_value, field in (
        (expected_contract_sha256, contract, "contract_sha256"),
        (expected_source_sha256, source, "source_panel_sha256"),
        (expected_code_manifest_sha256, manifest, "code_manifest_sha256"),
    ):
        if supplied is not None and _digest(supplied, field=f"expected_{field}") != actual_value:
            raise V019PhysicalAdapterError(f"gate {field} disagrees with supplied digest")
    binding = V019GateBinding(
        result_path=path,
        result_sha256=actual,
        contract_sha256=contract,
        source_sha256=source,
        code_manifest_sha256=manifest,
        independent_verification_sha256=verification,
    )
    binding.verify()
    return binding


def _q3_config_from_payload(value: object, *, kappa_bits: float) -> RelationalZRC3LearnerConfig:
    if not isinstance(value, Mapping):
        raise V019PhysicalAdapterError("Q3 checkpoint config is missing")
    expected_keys = {
        "action_dim",
        "action_context_dim",
        "victim_token_dim",
        "hidden_layers",
        "activation",
        "learning_rate",
        "kappa_bits",
        "beta",
        "output_unit_mode",
    }
    if set(value) != expected_keys:
        raise V019PhysicalAdapterError("Q3 checkpoint config fields are noncanonical")
    try:
        config = RelationalZRC3LearnerConfig(
            action_dim=int(value["action_dim"]),
            action_context_dim=int(value["action_context_dim"]),
            victim_token_dim=int(value["victim_token_dim"]),
            hidden_layers=tuple(int(item) for item in value["hidden_layers"]),
            activation=str(value["activation"]),
            learning_rate=float(value["learning_rate"]),
            kappa_bits=float(value["kappa_bits"]),
            beta=float(value["beta"]),
            output_unit_mode=str(value["output_unit_mode"]),
        )
    except (KeyError, TypeError, ValueError, RelationalLearnerError) as error:
        raise V019PhysicalAdapterError("Q3 checkpoint config is malformed") from error
    expected = RelationalZRC3LearnerConfig(
        action_dim=screen.ACTION_DIM,
        action_context_dim=7,
        victim_token_dim=6,
        hidden_layers=(100, 50, 50),
        activation="tanh",
        learning_rate=0.001,
        kappa_bits=float(kappa_bits),
        beta=0.0,
        output_unit_mode=Q3_OUTPUT_UNIT_MODE,
    )
    if config != expected:
        raise V019PhysicalAdapterError("Q3 checkpoint config is not the frozen V0.19 profile")
    return config


@dataclass(frozen=True)
class V019Q3Head:
    """One frozen normalized Q3 checkpoint selected by the learner gate."""

    initialization_seed: int
    source_lineage: int
    checkpoint_path: Path
    checkpoint_sha256: str
    learner: RelationalZRC3PairwiseLearner
    parameter_sha256: str

    def verify_frozen(self) -> None:
        if self.learner.train_seed != self.initialization_seed:
            raise V019PhysicalAdapterError("Q3 train seed disagrees with panel")
        if self.learner.update_count != Q3_UPDATE_RUNG:
            raise V019PhysicalAdapterError("Q3 checkpoint is not the required 100-update rung")
        if self.learner.config.output_unit_mode != Q3_OUTPUT_UNIT_MODE:
            raise V019PhysicalAdapterError("Q3 checkpoint is not normalized_bits_per_kappa")
        self.learner.q3.eval()
        self.learner.q3.requires_grad_(False)
        if any(parameter.requires_grad for parameter in self.learner.q3.parameters()):
            raise V019PhysicalAdapterError("selected Q3 remains trainable")
        _digest(self.checkpoint_sha256, field="Q3 checkpoint sha256")
        _digest(self.parameter_sha256, field="Q3 parameter sha256")
        try:
            observed = self.learner.parameter_sha256()
        except (AttributeError, RuntimeError, TypeError, ValueError) as error:
            raise V019PhysicalAdapterError("cannot hash selected Q3 parameters") from error
        if observed != self.parameter_sha256:
            raise V019PhysicalAdapterError("Q3 parameter digest disagrees with checkpoint")


def load_q3_head(
    checkpoint_path: str | Path,
    *,
    expected_checkpoint_sha256: str,
    initialization_seed: int,
    source_lineage: int,
    contract_sha256: str,
    source_sha256: str,
    code_manifest_sha256: str,
    kappa_bits: float = float(OPS3_KAPPA_BITS),
) -> V019Q3Head:
    """Load and freeze one authenticated post-gate V0.19 Q3 checkpoint."""

    path = Path(checkpoint_path)
    expected_hash = _digest(expected_checkpoint_sha256, field="expected Q3 checkpoint sha256")
    actual_hash = file_sha256(path)
    if actual_hash != expected_hash:
        raise V019PhysicalAdapterError("Q3 checkpoint bytes do not match supplied digest")
    contract = _digest(contract_sha256, field="contract_sha256")
    source = _digest(source_sha256, field="source_sha256")
    manifest = _digest(code_manifest_sha256, field="code_manifest_sha256")
    init = _positive_int(initialization_seed, field="initialization_seed")
    lineage = _positive_int(source_lineage, field="source_lineage")
    try:
        payload = torch.load(path, map_location="cpu", weights_only=False)
    except (OSError, EOFError, RuntimeError, TypeError, ValueError) as error:
        raise V019PhysicalAdapterError(f"cannot load Q3 checkpoint: {path}") from error
    if not isinstance(payload, Mapping):
        raise V019PhysicalAdapterError("Q3 checkpoint must be a mapping")
    expected_meta = {
        "schema": Q3_CHECKPOINT_SCHEMA,
        "algorithm": Q3_ALGORITHM,
        "train_seed": init,
        "update_count": Q3_UPDATE_RUNG,
        "contract_sha256": contract,
        "source_sha256": source,
        "code_manifest_sha256": manifest,
        "output_unit_mode": Q3_OUTPUT_UNIT_MODE,
        "test_split_opened": False,
        "episode_training": False,
    }
    for field, expected in expected_meta.items():
        if payload.get(field) != expected:
            raise V019PhysicalAdapterError(f"Q3 checkpoint metadata mismatch: {field}")
    config = _q3_config_from_payload(payload.get("config"), kappa_bits=float(kappa_bits))
    try:
        learner = RelationalZRC3PairwiseLearner(config, train_seed=init, device="cpu")
        learner.load_checkpoint(
            path,
            contract_sha256=contract,
            source_sha256=source,
            code_manifest_sha256=manifest,
        )
    except (KeyError, TypeError, ValueError, RuntimeError, RelationalLearnerError) as error:
        raise V019PhysicalAdapterError("Q3 checkpoint learner state is malformed") from error
    claimed_parameter = _digest(payload.get("parameter_sha256"), field="parameter_sha256")
    try:
        observed_parameter = learner.parameter_sha256()
    except (AttributeError, RuntimeError, TypeError, ValueError) as error:
        raise V019PhysicalAdapterError("cannot hash loaded Q3 parameters") from error
    if observed_parameter != claimed_parameter:
        raise V019PhysicalAdapterError("Q3 parameter digest disagrees with checkpoint payload")
    head = V019Q3Head(
        initialization_seed=init,
        source_lineage=lineage,
        checkpoint_path=path,
        checkpoint_sha256=actual_hash,
        learner=learner,
        parameter_sha256=observed_parameter,
    )
    head.verify_frozen()
    return head


@dataclass(frozen=True)
class V019Q3Panel:
    """Three-head panel plus its authenticated learner-gate authority."""

    gate: V019GateBinding
    heads_by_initialization: Mapping[int, V019Q3Head]

    def verify(self) -> None:
        self.gate.verify()
        if len(self.heads_by_initialization) != 3:
            raise V019PhysicalAdapterError("Q3 panel must contain exactly three heads")
        lineages: set[int] = set()
        for init, head in self.heads_by_initialization.items():
            if int(init) != head.initialization_seed:
                raise V019PhysicalAdapterError("Q3 panel key disagrees with head seed")
            head.verify_frozen()
            if head.source_lineage in lineages:
                raise V019PhysicalAdapterError("Q3 panel lineages must be distinct")
            lineages.add(head.source_lineage)


Q1Loader: TypeAlias = Callable[[int], tuple[Any, Mapping[str, Any]]]
Q2Loader: TypeAlias = Callable[[int], tuple[Any, Mapping[str, Any]]]
EnvironmentFactory: TypeAlias = Callable[[Any, int], Any]
RngFactory: TypeAlias = Callable[[int], Sequence[Any]]
MainActionCallback: TypeAlias = Callable[..., object]
Q2StateEncoder: TypeAlias = Callable[[Any], Any]
PowerOpeningHelper: TypeAlias = Callable[..., tuple[np.ndarray, np.ndarray]]
FieldFactory: TypeAlias = Callable[[str, int], KeyedFadingField]


def _attach_field(environment: Any, field: KeyedFadingField) -> Any:
    step_environment = getattr(environment, "environment", environment)
    if not hasattr(step_environment, "_fading_field"):
        raise V019PhysicalAdapterError("environment lacks canonical fading-field boundary")
    step_environment._fading_field = field
    return step_environment


def _reset(environment: Any, rngs: Sequence[Any]) -> tuple[Any, Any, Any]:
    if len(rngs) < 2:
        raise V019PhysicalAdapterError("rng_factory must return environment and mobility RNGs")
    try:
        result = environment.reset(rngs[0], rngs[1])
    except (AttributeError, RuntimeError, TypeError, ValueError) as error:
        raise V019PhysicalAdapterError("canonical environment reset failed") from error
    if not isinstance(result, tuple) or len(result) != 3:
        raise V019PhysicalAdapterError("canonical reset must return states, masks, observation")
    return result[0], result[1], result[2]


def _last_outcome(environment: Any) -> Any:
    outcome = getattr(environment, "last_outcome", None)
    if outcome is None:
        raise V019PhysicalAdapterError("canonical environment did not expose last_outcome")
    return outcome


def _next_observation(outcome: Any) -> Any:
    observation = getattr(outcome, "observation", None)
    if observation is None:
        raise V019PhysicalAdapterError("canonical outcome did not expose next observation")
    return observation


class V019PhysicalAdapter:
    """Bind canonical simulator callbacks after a PASS learner gate."""

    def __init__(
        self,
        *,
        panel: V019Q3Panel,
        archive: Any,
        q1_loader: Q1Loader,
        q2_loader: Q2Loader,
        make_environment: EnvironmentFactory,
        rng_factory: RngFactory,
        main_trainer: Any,
        main_actions: MainActionCallback,
        main_policy_sha256: str,
        q2_state_encoder: Q2StateEncoder,
        required_power_and_opening: PowerOpeningHelper,
        field_component: str,
        field_factory: FieldFactory | None = None,
        main_network_snapshot: Callable[[Any], Any] | None = None,
        main_network_equal: Callable[[Any, Any], bool] | None = None,
        main_replay_size: Callable[[Any], int] | None = None,
        users: int = USERS,
        steps: int = STEPS,
        kappa_bits: float = float(OPS3_KAPPA_BITS),
        pmax_w: float = float(BEAM_POWER_MAX_W),
    ) -> None:
        panel.verify()
        if not callable(q1_loader) or not callable(q2_loader):
            raise V019PhysicalAdapterError("Q1/Q2 loaders must be callable")
        if not callable(make_environment) or not callable(rng_factory):
            raise V019PhysicalAdapterError("environment/RNG factories must be callable")
        if not callable(main_actions):
            raise V019PhysicalAdapterError("MAIN action callback must be callable")
        if not callable(q2_state_encoder) or not callable(required_power_and_opening):
            raise V019PhysicalAdapterError("Q2 state/power helpers must be callable")
        if users != USERS or steps != STEPS:
            raise V019PhysicalAdapterError("V0.19 physical episodes use 100 users and ten steps")
        if not isinstance(field_component, str) or not field_component.strip():
            raise V019PhysicalAdapterError("field_component must be nonempty")
        if not math.isfinite(float(kappa_bits)) or float(kappa_bits) <= 0.0:
            raise V019PhysicalAdapterError("kappa_bits must be finite and positive")
        if not math.isfinite(float(pmax_w)) or float(pmax_w) <= 0.0:
            raise V019PhysicalAdapterError("pmax_w must be finite and positive")
        self.panel = panel
        self.archive = archive
        self.q1_loader = q1_loader
        self.q2_loader = q2_loader
        self.make_environment = make_environment
        self.rng_factory = rng_factory
        self.main_trainer = main_trainer
        self.main_actions = main_actions
        self.main_policy_sha256 = _digest(main_policy_sha256, field="main_policy_sha256")
        self.q2_state_encoder = q2_state_encoder
        self.required_power_and_opening = required_power_and_opening
        self.field_component = field_component
        self.field_factory = field_factory or (
            lambda component, seed: KeyedFadingField.from_components(component, seed)
        )
        if not callable(self.field_factory):
            raise V019PhysicalAdapterError("field_factory must be callable")
        self.main_network_snapshot = main_network_snapshot or _parameter_sha256
        self.main_network_equal = main_network_equal
        self.main_replay_size = main_replay_size or (
            lambda trainer: int(len(getattr(trainer, "replay", ())))
        )
        if not callable(self.main_network_snapshot) or not callable(self.main_replay_size):
            raise V019PhysicalAdapterError("MAIN mutation helpers must be callable")
        self.users = int(users)
        self.steps = int(steps)
        self.kappa_bits = float(kappa_bits)
        self.pmax_w = float(pmax_w)
        self._q1: dict[int, tuple[Any, Mapping[str, Any]]] = {}
        self._q2: dict[int, tuple[Any, Mapping[str, Any]]] = {}

    def field_for(self, *, evaluation_seed: int, expected_root_digest: str) -> KeyedFadingField:
        seed = _positive_int(evaluation_seed, field="evaluation_seed")
        expected_root = _digest(expected_root_digest, field="expected field_root_digest")
        try:
            field = self.field_factory(self.field_component, seed)
        except (TypeError, ValueError, RuntimeError) as error:
            raise V019PhysicalAdapterError("field_factory failed") from error
        if not isinstance(field, KeyedFadingField):
            raise V019PhysicalAdapterError("field_factory must return KeyedFadingField")
        canonical = KeyedFadingField.from_components(self.field_component, seed)
        if field.root_digest != canonical.root_digest or field.root_digest != expected_root:
            raise V019PhysicalAdapterError("field root does not match canonical world binding")
        return field

    def _load_q1(self, lineage: screen.LineageBinding) -> tuple[Any, Mapping[str, Any]]:
        key = int(lineage.source_lineage)
        if key not in self._q1:
            try:
                loaded = self.q1_loader(key)
            except Exception as error:  # pragma: no cover - live loader-specific failures
                raise V019PhysicalAdapterError(f"Q1 loader failed for lineage {key}") from error
            if not isinstance(loaded, tuple) or len(loaded) != 2 or not isinstance(loaded[1], Mapping):
                raise V019PhysicalAdapterError("q1_loader must return (network, receipt)")
            network, receipt = loaded
            try:
                network.eval()
                network.requires_grad_(False)
                parameter = _parameter_sha256(network)
            except (AttributeError, RuntimeError, TypeError, ValueError) as error:
                raise V019PhysicalAdapterError("Q1 loader returned a malformed network") from error
            if receipt.get("checkpoint_sha256") != lineage.q1_checkpoint_sha256:
                raise V019PhysicalAdapterError("Q1 receipt checkpoint disagrees with lineage")
            claimed_parameter = receipt.get("parameter_sha256")
            if claimed_parameter is not None and _digest(claimed_parameter, field="Q1 parameter_sha256") != parameter:
                raise V019PhysicalAdapterError("Q1 receipt does not authenticate network parameters")
            self._q1[key] = (network, receipt)
        return self._q1[key]

    def _load_q2(self, lineage: screen.LineageBinding) -> tuple[Any, Mapping[str, Any]]:
        key = int(lineage.source_lineage)
        if key not in self._q2:
            try:
                loaded = self.q2_loader(key)
            except Exception as error:  # pragma: no cover - live loader-specific failures
                raise V019PhysicalAdapterError(f"Q2 loader failed for lineage {key}") from error
            if not isinstance(loaded, tuple) or len(loaded) != 2 or not isinstance(loaded[1], Mapping):
                raise V019PhysicalAdapterError("q2_loader must return (network, receipt)")
            network, receipt = loaded
            config = getattr(network, "config", None)
            expected_config = {
                "action_dim": screen.ACTION_DIM,
                "local_feature_dim": 16,
                "global_feature_dim": 0,
                "hidden_layers": (100, 50, 50),
                "activation": "tanh",
            }
            if any(getattr(config, field, None) != expected for field, expected in expected_config.items()):
                raise V019PhysicalAdapterError("Q2 loader returned a noncanonical frozen Q2 network")
            try:
                network.eval()
                network.requires_grad_(False)
                parameter = _parameter_sha256(network)
            except (AttributeError, RuntimeError, TypeError, ValueError) as error:
                raise V019PhysicalAdapterError("Q2 loader returned a malformed network") from error
            if receipt.get("checkpoint_sha256") != lineage.q2_checkpoint_sha256:
                raise V019PhysicalAdapterError("Q2 receipt checkpoint disagrees with lineage")
            claimed_parameter = receipt.get("parameter_sha256")
            if claimed_parameter is not None and _digest(claimed_parameter, field="Q2 parameter_sha256") != parameter:
                raise V019PhysicalAdapterError("Q2 receipt does not authenticate network parameters")
            self._q2[key] = (network, receipt)
        return self._q2[key]

    def _q3_source(
        self,
        state: Any,
        *,
        world_seed: int,
        source_lineage: int,
        field_root_digest: str,
    ) -> RelationalZRC3Source:
        """Wrap one live state for inference without manufacturing a label.

        ``RelationalZRC3PairwiseLearner.q_values`` consumes the shared source
        container but never reads ``target_surface_bits``.  The all-zero
        target below is therefore a shape-valid inference placeholder; no
        physical outcome or teacher target is produced by this adapter.
        """

        try:
            targets = np.zeros_like(np.asarray(state.action_mask, dtype=np.float64))
            source = RelationalZRC3Source(
                action_context=state.action_context,
                victim_tokens=state.victim_tokens,
                action_mask=state.action_mask,
                victim_mask=state.victim_mask,
                positive_credit_compatible=state.positive_credit_compatible,
                reference_actions=state.reference_actions,
                target_surface_bits=targets,
                world_seed=int(world_seed),
                lineage=int(source_lineage),
                split=TRAIN_SPLIT,
                field_root_digest=field_root_digest,
                kappa_bits=self.kappa_bits,
                feature_fields=FEATURE_FIELDS,
            )
        except (RelationalSourceError, TypeError, ValueError) as error:
            raise V019PhysicalAdapterError("cannot bind live relational state as Q3 input") from error
        return source

    def _anchor_surfaces(
        self,
        step_environment: Any,
        observation: Any,
        q1: Any,
        q2: Any,
        *,
        world_seed: int,
        source_lineage: int,
        field_root_digest: str,
        need_q3: bool,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, Any | None, np.ndarray | None, screen.Q3InputBinding | None]:
        try:
            native = encode_ee_axis_state(step_environment, observation)
            masks = np.asarray(native.action_masks, dtype=np.bool_)
            q1_values = _surface(q1, native.state_matrix, masks, field="Q1")
            q1_reference = screen.masked_argmax(q1_values, masks)
            anchor = snapshot_ops3_anchor(step_environment, observation)
            projection = project_ops3_anchor(anchor)
            q2_carrier = build_ops3_live_surfaces(anchor, projection, q1_reference)
            q2_state = self.q2_state_encoder(q2_carrier)
            q2_state_masks = np.asarray(q2_state.action_masks, dtype=np.bool_)
            if not np.array_equal(q2_state_masks, masks):
                raise V019PhysicalAdapterError("Q2 carrier mask differs from native mask")
            q2_values = _surface(q2, q2_state.state_matrix, q2_state_masks, field="Q2")
            refs = screen.q3_reference_actions(q1_values, q2_values, masks)
        except V019PhysicalAdapterError:
            raise
        except (AttributeError, RuntimeError, TypeError, ValueError) as error:
            raise V019PhysicalAdapterError("canonical Q1/Q2 anchor construction failed") from error
        if not need_q3:
            return q1_values, q2_values, masks, None, None, None
        try:
            # The canonical helper's default p0 is the frozen
            # SEGMENT_START_POWER_W.  Supplying only pmax keeps the adapter
            # independent of a helper's module-level constant spelling.
            required_power, opening = self.required_power_and_opening(
                current_gain_linear=anchor.current_gain_linear,
                segment_start_gain_linear=anchor.segment_start_gain_linear,
                action_masks=masks,
                pmax_w=self.pmax_w,
            )
        except (AttributeError, RuntimeError, TypeError, ValueError) as error:
            raise V019PhysicalAdapterError("required-power/opening surface failed") from error
        try:
            state = encode_relational_zr_c3_state(
                step_environment,
                observation,
                reference_actions=refs,
                current_required_power_w=required_power,
                opening_service_feasible=opening,
                pmax_w=self.pmax_w,
            )
            binding = screen.Q3InputBinding(
                reference_actions_sha256=_array_sha256(refs),
                state_sha256=str(state.state_sha256),
            )
            binding.verify()
        except V019PhysicalAdapterError:
            raise
        except (AttributeError, RuntimeError, TypeError, ValueError, RelationalSourceError) as error:
            raise V019PhysicalAdapterError("relational Q3 state construction failed") from error
        return q1_values, q2_values, masks, state, refs, binding

    def route_episode_runner(
        self,
        *,
        arm: str,
        episode_index: int,
        evaluation_seed: int,
        lineage: screen.LineageBinding,
        field_root_digest: str,
    ) -> screen.V019EpisodeReceipt:
        """Execute one physical route episode for the pure screen loop."""

        if arm not in screen.ROUTE_ARMS:
            raise V019PhysicalAdapterError(f"unknown route arm: {arm}")
        lineage.verify()
        episode = _positive_int(episode_index, field="episode_index")
        world = _positive_int(evaluation_seed, field="evaluation_seed")
        if int(lineage.initialization_seed) not in self.panel.heads_by_initialization:
            raise V019PhysicalAdapterError("route lineage is outside the authenticated Q3 panel")
        head = self.panel.heads_by_initialization[int(lineage.initialization_seed)]
        if head.source_lineage != lineage.source_lineage or head.checkpoint_sha256 != lineage.q3_checkpoint_sha256:
            raise V019PhysicalAdapterError("lineage/Q3 panel disagreement")
        field = self.field_for(evaluation_seed=world, expected_root_digest=field_root_digest)
        q1, q1_receipt = self._load_q1(lineage)
        q2, q2_receipt = self._load_q2(lineage)
        q1_before = _parameter_sha256(q1)
        q2_before = _parameter_sha256(q2)
        q3_before = _parameter_sha256(head.learner.q3)
        q3_optimizer_before = _optimizer_sha256(head.learner)
        q3_updates_before = int(head.learner.update_count)
        try:
            environment = self.make_environment(self.archive, self.users)
            step_environment = _attach_field(environment, field)
            rngs = tuple(self.rng_factory(world))
            _states, _masks, observation = _reset(environment, rngs)
            env_rng = rngs[0]
            interval_s = float(step_environment.driver.config.ephemeris.time_step_s)
        except (AttributeError, RuntimeError, TypeError, ValueError) as error:
            raise V019PhysicalAdapterError("route environment setup failed") from error
        if not math.isfinite(interval_s) or interval_s <= 0.0:
            raise V019PhysicalAdapterError("decision interval is not finite and positive")
        total_bits = 0.0
        total_energy = 0.0
        served = 0
        trace = hashlib.sha256()
        q3_binding: screen.Q3InputBinding | None = None
        q3_anchor_bindings: list[tuple[str, str]] = []
        with torch.no_grad():
            for step_index in range(self.steps):
                need_q3 = arm in screen.Q3_ACTIVE_ARMS
                q1_values, q2_values, masks, state, refs, binding = self._anchor_surfaces(
                    step_environment,
                    observation,
                    q1,
                    q2,
                    world_seed=world,
                    source_lineage=lineage.source_lineage,
                    field_root_digest=field.root_digest,
                    need_q3=need_q3,
                )
                q3_values: np.ndarray | None = None
                if need_q3:
                    assert state is not None and refs is not None and binding is not None
                    source = self._q3_source(
                        state,
                        world_seed=world,
                        source_lineage=lineage.source_lineage,
                        field_root_digest=field.root_digest,
                    )
                    try:
                        q3_values = np.asarray(head.learner.q_values(source), dtype=np.float64)
                    except (RelationalLearnerError, RelationalSourceError, RuntimeError, TypeError, ValueError) as error:
                        raise V019PhysicalAdapterError("frozen learned Q3 inference failed") from error
                    if q3_values.shape != masks.shape or not np.all(np.isfinite(q3_values)):
                        raise V019PhysicalAdapterError("learned Q3 surface is malformed")
                    q3_binding = binding
                    q3_anchor_bindings.append(
                        (binding.reference_actions_sha256, binding.state_sha256)
                    )
                decoded = screen.compose_route_scores(
                    q1_values,
                    q2_values,
                    q3_values,
                    masks,
                    arm,
                    reference_actions=refs if need_q3 else None,
                    q3_input=q3_binding if need_q3 else None,
                )
                actions = _validate_action_vector(decoded.selected_actions, masks, field=f"{arm} route")
                _action_trace_update(trace, actions)
                try:
                    result = environment.step(actions, env_rng)
                    outcome = _last_outcome(environment)
                except (AttributeError, RuntimeError, TypeError, ValueError) as error:
                    raise V019PhysicalAdapterError("canonical route step failed") from error
                rates = np.asarray(getattr(outcome, "link_rate_bps", None), dtype=np.float64)
                power = float(getattr(outcome, "system_power_w", np.nan))
                if rates.shape != (self.users,) or not np.all(np.isfinite(rates)) or np.any(rates < 0.0):
                    raise V019PhysicalAdapterError("canonical link-rate outcome is malformed")
                if not math.isfinite(power) or power <= 0.0:
                    raise V019PhysicalAdapterError("canonical system power must be positive")
                total_bits += interval_s * math.fsum(float(value) for value in rates)
                total_energy += interval_s * power
                served += int(getattr(getattr(outcome, "resolution", None), "served_count", 0))
                if step_index != self.steps - 1:
                    if bool(getattr(result, "done", False)):
                        raise V019PhysicalAdapterError("route episode terminated before ten steps")
                    observation = _next_observation(outcome)
        if _parameter_sha256(q1) != q1_before or _parameter_sha256(q2) != q2_before:
            raise V019PhysicalAdapterError("physical route evaluation mutated frozen Q1/Q2")
        if (
            _parameter_sha256(head.learner.q3) != q3_before
            or _optimizer_sha256(head.learner) != q3_optimizer_before
            or int(head.learner.update_count) != q3_updates_before
        ):
            raise V019PhysicalAdapterError("physical route evaluation mutated frozen Q3")
        if arm in screen.Q3_ACTIVE_ARMS and len(q3_anchor_bindings) != self.steps:
            raise V019PhysicalAdapterError("active route did not bind one Q3 state per step")
        # The receipt carries an episode-level digest of every predecision
        # anchor, not only the final step.  The pure screen compares this
        # digest across FULL/DROP_C1/DROP_C2 to protect the complete ten-step
        # ablation panel.
        q3_reference_receipt = (
            canonical_sha256([item[0] for item in q3_anchor_bindings])
            if q3_anchor_bindings
            else None
        )
        q3_state_receipt = (
            canonical_sha256([item[1] for item in q3_anchor_bindings])
            if q3_anchor_bindings
            else None
        )
        return screen.V019EpisodeReceipt(
            arm=arm,
            episode_index=episode,
            evaluation_seed=world,
            total_bits=float(total_bits),
            total_energy_j=float(total_energy),
            decision_count=self.users * self.steps,
            served_user_steps=int(served),
            field_root_digest=field.root_digest,
            initialization_seed=int(lineage.initialization_seed),
            source_lineage=int(lineage.source_lineage),
            q1_checkpoint_sha256=lineage.q1_checkpoint_sha256,
            q2_checkpoint_sha256=lineage.q2_checkpoint_sha256,
            q3_checkpoint_sha256=lineage.q3_checkpoint_sha256,
            q3_evaluated=arm in screen.Q3_ACTIVE_ARMS,
            q3_reference_mode=screen.Q3_REFERENCE_MODE if arm in screen.Q3_ACTIVE_ARMS else "NOT_APPLICABLE",
            q3_reference_actions_sha256=q3_reference_receipt,
            q3_state_sha256=q3_state_receipt,
            q3_state_schema=(screen.Q3_STATE_SCHEMA if q3_binding else None),
            q3_output_unit_mode=Q3_OUTPUT_UNIT_MODE,
            action_trace_sha256=trace.hexdigest(),
        )

    def main_episode_runner(
        self,
        *,
        arm: str,
        episode_index: int,
        evaluation_seed: int,
        field_root_digest: str,
        main_policy_sha256: str,
    ) -> screen.V019EpisodeReceipt:
        """Execute one independent frozen MAIN episode."""

        if arm != screen.MAIN_ARM:
            raise V019PhysicalAdapterError("MAIN callback received a route arm")
        if _digest(main_policy_sha256, field="main_policy_sha256") != self.main_policy_sha256:
            raise V019PhysicalAdapterError("MAIN policy digest disagrees with adapter binding")
        episode = _positive_int(episode_index, field="episode_index")
        world = _positive_int(evaluation_seed, field="evaluation_seed")
        field = self.field_for(evaluation_seed=world, expected_root_digest=field_root_digest)
        try:
            network_before = self.main_network_snapshot(self.main_trainer)
            replay_before = int(self.main_replay_size(self.main_trainer))
            environment = self.make_environment(self.archive, self.users)
            step_environment = _attach_field(environment, field)
            rngs = tuple(self.rng_factory(world))
            states, masks, observation = _reset(environment, rngs)
            env_rng = rngs[0]
            interval_s = float(step_environment.driver.config.ephemeris.time_step_s)
        except (AttributeError, RuntimeError, TypeError, ValueError) as error:
            raise V019PhysicalAdapterError("MAIN environment setup failed") from error
        if not math.isfinite(interval_s) or interval_s <= 0.0:
            raise V019PhysicalAdapterError("decision interval is not finite and positive")
        total_bits = 0.0
        total_energy = 0.0
        served = 0
        trace = hashlib.sha256()
        with torch.no_grad():
            for step_index in range(self.steps):
                try:
                    actions = self.main_actions(
                        self.main_trainer,
                        environment,
                        states,
                        masks,
                        observation,
                        env_rng,
                    )
                except (AttributeError, RuntimeError, TypeError, ValueError) as error:
                    raise V019PhysicalAdapterError("frozen MAIN inference failed") from error
                legal = np.asarray(getattr(observation, "masks", masks))
                if legal.dtype != np.bool_:
                    legal = np.asarray(masks, dtype=np.bool_)
                actions_array = _validate_action_vector(actions, legal, field="MAIN")
                _action_trace_update(trace, actions_array)
                try:
                    result = environment.step(actions_array, env_rng)
                    outcome = _last_outcome(environment)
                except (AttributeError, RuntimeError, TypeError, ValueError) as error:
                    raise V019PhysicalAdapterError("canonical MAIN step failed") from error
                rates = np.asarray(getattr(outcome, "link_rate_bps", None), dtype=np.float64)
                power = float(getattr(outcome, "system_power_w", np.nan))
                if rates.shape != (self.users,) or not np.all(np.isfinite(rates)) or np.any(rates < 0.0):
                    raise V019PhysicalAdapterError("canonical MAIN link-rate outcome is malformed")
                if not math.isfinite(power) or power <= 0.0:
                    raise V019PhysicalAdapterError("canonical MAIN system power must be positive")
                total_bits += interval_s * math.fsum(float(value) for value in rates)
                total_energy += interval_s * power
                served += int(getattr(getattr(outcome, "resolution", None), "served_count", 0))
                if step_index != self.steps - 1:
                    if bool(getattr(result, "done", False)):
                        raise V019PhysicalAdapterError("MAIN episode terminated before ten steps")
                    states = getattr(result, "user_states", None)
                    masks = getattr(result, "action_masks", None)
                    if states is None or masks is None:
                        raise V019PhysicalAdapterError("MAIN step lacks next policy states/masks")
                    observation = _next_observation(outcome)
        try:
            network_after = self.main_network_snapshot(self.main_trainer)
            replay_after = int(self.main_replay_size(self.main_trainer))
        except (AttributeError, RuntimeError, TypeError, ValueError) as error:
            raise V019PhysicalAdapterError("MAIN mutation check failed") from error
        if self.main_network_equal is not None:
            try:
                network_unchanged = bool(
                    self.main_network_equal(self.main_trainer, network_before)
                )
            except (AttributeError, RuntimeError, TypeError, ValueError) as error:
                raise V019PhysicalAdapterError("MAIN network equality check failed") from error
        else:
            network_unchanged = _snapshots_equal(network_after, network_before)
        if not network_unchanged or replay_after != replay_before:
            raise V019PhysicalAdapterError("physical MAIN evaluation mutated frozen policy state")
        return screen.V019EpisodeReceipt(
            arm=screen.MAIN_ARM,
            episode_index=episode,
            evaluation_seed=world,
            total_bits=float(total_bits),
            total_energy_j=float(total_energy),
            decision_count=self.users * self.steps,
            served_user_steps=int(served),
            field_root_digest=field.root_digest,
            main_policy_sha256=self.main_policy_sha256,
            action_trace_sha256=trace.hexdigest(),
            q3_output_unit_mode="NOT_APPLICABLE",
        )

    def callbacks(self) -> tuple[Callable[..., screen.V019EpisodeReceipt], Callable[..., screen.V019EpisodeReceipt]]:
        """Return callbacks with the exact pure-screen protocol."""

        return self.route_episode_runner, self.main_episode_runner


@dataclass(frozen=True)
class V019PostPassRuntime:
    """A prepared spec/adapter pair; ``run`` is the only execution method."""

    spec: screen.V019FiveArmScreenSpec
    adapter: V019PhysicalAdapter

    def run(self, *, output_dir: str | Path) -> dict[str, object]:
        route, main = self.adapter.callbacks()
        return screen.run_five_arm_screen(
            spec=self.spec,
            route_episode_runner=route,
            main_episode_runner=main,
            output_dir=output_dir,
        )


__all__ = [
    "CLAIM_CEILING",
    "GATE_DECISION",
    "GATE_RESULT_SCHEMA",
    "PHYSICAL_RUNNER_SCHEMA",
    "Q3_OUTPUT_UNIT_MODE",
    "V019GateBinding",
    "V019PhysicalAdapter",
    "V019PhysicalAdapterError",
    "V019PostPassRuntime",
    "V019Q3Head",
    "V019Q3Panel",
    "authenticate_gate_result",
    "canonical_sha256",
    "file_sha256",
    "load_q3_head",
    "screen",
]
