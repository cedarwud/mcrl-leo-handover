"""Decision-A successor of the fail-closed post-R7 provider factory."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import importlib
import importlib.util
import os
from pathlib import Path
import sys
from types import MappingProxyType
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
_V1_SPEC = importlib.util.spec_from_file_location(
    "v023_post_r7_provider_factory_v1_for_v2", (HERE / "v023_post_r7_provider_factory.py").resolve())
if _V1_SPEC is None or _V1_SPEC.loader is None:
    raise RuntimeError("cannot import post-R7 provider factory v1")
_V1 = importlib.util.module_from_spec(_V1_SPEC)
sys.modules[_V1_SPEC.name] = _V1
_V1_SPEC.loader.exec_module(_V1)

# Reuse these exact v1 objects; only the Decision-A seams below are successors.
for _reused_name in (
    "_verify_result_manifest", "_verify_r7_authority_snapshot",
    "_verify_launch_metadata", "_essential_result_fields",
    "_schedule_receipt_identity", "_read_canonical_json", "_file_sha256",
    "_digest", "_regular_dir", "_regular_file", "_fail", "_FIT", "_R7_GATE",
    "_PREFLIGHT", "_SCHEDULE", "_BRIDGE",
):
    globals()[_reused_name] = getattr(_V1, _reused_name)
del _reused_name

V023PostR7ProviderFactoryError = _V1.V023PostR7ProviderFactoryError
V023PostR7Provider = _V1.V023PostR7Provider

CONFIG_PATH_ENV = _V1.CONFIG_PATH_ENV
CONFIG_SHA256_ENV = _V1.CONFIG_SHA256_ENV
CONFIG_SCHEMA = "multi-catfish-mcrl-v023-post-r7-provider-factory-config-v2"
FACTORY_SCHEMA = "multi-catfish-mcrl-v023-post-r7-provider-factory-v2"
IDENTITY_SCHEMA = "multi-catfish-mcrl-v023-post-r7-provider-identity-v2"
for _constant_name in (
    "R7_ROOT_RESULT", "R7_ROOT_VERIFICATION", "R7_ROOT_SOURCE_MANIFEST",
    "R7_ROOT_AUTHORITY", "R7_ROOT_PREFLIGHT", "R7_ROOT_PREFLIGHT_DIGEST",
    "R7_PREFLIGHT_SCHEMA", "R7_PREFLIGHT_STATUS", "R7_PREFLIGHT_LAUNCH",
    "R7_PREFLIGHT_RECEIPT_SCHEMA", "R7_PREFLIGHT_RECEIPT_STATUS",
    "_R7_COMMON_FIELDS",
):
    globals()[_constant_name] = getattr(_V1, _constant_name)
del _constant_name
_CONFIG_FIELDS = frozenset({"schema", "r7_root", "target_root", "epoch_budget",
                            "schedule_seed", "r7_code_root"})
R7_AUTHENTICATION_RUNTIME_MODULES = MappingProxyType({
    ".scratch/multi-catfish-v023-r7-launch-ready/preflight_r7_balanced.py":
        "v023_r7_preflight_for_post_r7_provider_factory",
    ".scratch/multi-catfish-v023-r7-launch-ready/r7_balanced_successor_gate.py":
        "r7_balanced_successor_gate",
    ".scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_fit_adapter.py":
        "v023_fit_adapter_for_post_r7_provider_factory",
    "src/mcrl/__init__.py": "mcrl",
    "src/mcrl/errors.py": "mcrl.errors",
    "src/mcrl/algorithms/__init__.py": "mcrl.algorithms",
    "src/mcrl/algorithms/ee_axis_lcsrs_c3_head.py":
        "mcrl.algorithms.ee_axis_lcsrs_c3_head",
    "src/mcrl/env/__init__.py": "mcrl.env",
    "src/mcrl/env/action_contract.py": "mcrl.env.action_contract",
    "src/mcrl/runtime/__init__.py": "mcrl.runtime",
    "src/mcrl/runtime/ee_axis_lcsrs_c3_dataset.py":
        "mcrl.runtime.ee_axis_lcsrs_c3_dataset",
    "src/mcrl/runtime/ee_axis_lcsrs_c3_gate_fit.py":
        "mcrl.runtime.ee_axis_lcsrs_c3_gate_fit",
    "src/mcrl/runtime/ee_axis_lcsrs_c3_gate_metrics.py":
        "mcrl.runtime.ee_axis_lcsrs_c3_gate_metrics",
    "src/mcrl/runtime/ee_axis_lcsrs_c3_learner.py":
        "mcrl.runtime.ee_axis_lcsrs_c3_learner",
    "src/mcrl/runtime/ee_axis_lcsrs_c3_placebo.py":
        "mcrl.runtime.ee_axis_lcsrs_c3_placebo",
    "src/mcrl/runtime/ee_axis_lcsrs_c3_source_artifact.py":
        "mcrl.runtime.ee_axis_lcsrs_c3_source_artifact",
    "src/mcrl/runtime/ee_axis_lcsrs_c3_state.py":
        "mcrl.runtime.ee_axis_lcsrs_c3_state",
    "src/mcrl/runtime/finiteness.py": "mcrl.runtime.finiteness",
})
R7_AUTHENTICATION_RUNTIME_PATHS = tuple(R7_AUTHENTICATION_RUNTIME_MODULES)
R7_BOUND_LEARNER_RUNTIME_MODULES = MappingProxyType({
    "src/mcrl/algorithms/ee_axis_action_shared.py":
        "mcrl.algorithms.ee_axis_action_shared",
    "src/mcrl/algorithms/ee_axis_lcsrs_three_route.py":
        "mcrl.algorithms.ee_axis_lcsrs_three_route",
    "src/mcrl/algorithms/ee_axis_pairwise.py":
        "mcrl.algorithms.ee_axis_pairwise",
    "src/mcrl/algorithms/ee_axis_v014_head.py":
        "mcrl.algorithms.ee_axis_v014_head",
    "src/mcrl/env/antenna.py": "mcrl.env.antenna",
    "src/mcrl/env/candidates.py": "mcrl.env.candidates",
    "src/mcrl/env/cells.py": "mcrl.env.cells",
    "src/mcrl/env/constants.py": "mcrl.env.constants",
    "src/mcrl/env/d2.py": "mcrl.env.d2",
    "src/mcrl/env/dwell.py": "mcrl.env.dwell",
    "src/mcrl/env/ephemeris.py": "mcrl.env.ephemeris",
    "src/mcrl/env/geometry.py": "mcrl.env.geometry",
    "src/mcrl/env/interference.py": "mcrl.env.interference",
    "src/mcrl/env/keyed_fading.py": "mcrl.env.keyed_fading",
    "src/mcrl/env/link_budget.py": "mcrl.env.link_budget",
    "src/mcrl/env/mobility.py": "mcrl.env.mobility",
    "src/mcrl/env/observation_provenance.py":
        "mcrl.env.observation_provenance",
    "src/mcrl/env/pointing.py": "mcrl.env.pointing",
    "src/mcrl/env/scenario.py": "mcrl.env.scenario",
    "src/mcrl/env/service.py": "mcrl.env.service",
    "src/mcrl/env/step.py": "mcrl.env.step",
    "src/mcrl/env/step_types.py": "mcrl.env.step_types",
    "src/mcrl/env/tle.py": "mcrl.env.tle",
    "src/mcrl/runtime/bessel.py": "mcrl.runtime.bessel",
    "src/mcrl/runtime/ee_axis_opening_pairs.py":
        "mcrl.runtime.ee_axis_opening_pairs",
    "src/mcrl/runtime/ee_axis_ops3.py": "mcrl.runtime.ee_axis_ops3",
    "src/mcrl/runtime/ee_axis_state.py": "mcrl.runtime.ee_axis_state",
    "src/mcrl/runtime/ee_axis_v014_q2_state.py":
        "mcrl.runtime.ee_axis_v014_q2_state",
    "src/mcrl/runtime/ee_surplus_targets.py":
        "mcrl.runtime.ee_surplus_targets",
    "src/mcrl/runtime/energy_efficiency.py":
        "mcrl.runtime.energy_efficiency",
    "src/mcrl/runtime/q_network.py": "mcrl.runtime.q_network",
    "src/mcrl/runtime/state_encoding.py": "mcrl.runtime.state_encoding",
    "src/mcrl/runtime/trainer_spec.py": "mcrl.runtime.trainer_spec",
})
R7_BOUND_LEARNER_RUNTIME_PATHS = tuple(R7_BOUND_LEARNER_RUNTIME_MODULES)

if (
    len(R7_AUTHENTICATION_RUNTIME_MODULES) != 18
    or len(R7_BOUND_LEARNER_RUNTIME_MODULES) != 33
    or set(R7_AUTHENTICATION_RUNTIME_MODULES)
    & set(R7_BOUND_LEARNER_RUNTIME_MODULES)
    or len(set(R7_AUTHENTICATION_RUNTIME_MODULES.values())) != 18
    or len(set(R7_BOUND_LEARNER_RUNTIME_MODULES.values())) != 33
):
    raise RuntimeError("the pinned R7 18/33 runtime declarations are invalid")


def _validated_code_root(path: Path) -> Path:
    if not isinstance(path, Path) or not path.is_absolute():
        _fail("config r7_code_root must be an absolute path")
    if not path.is_dir():
        _fail("config r7_code_root must be an existing directory")
    try:
        resolved = path.resolve(strict=True)
        learner = REPO.resolve(strict=True)
    except OSError as cause:
        _fail("config r7_code_root cannot be resolved", cause=cause)
    if resolved == learner or resolved.is_relative_to(learner):
        _fail("r7_code_root must be separate from the learner checkout")
    return resolved


@dataclass(frozen=True, slots=True)
class PostR7ProviderConfig:
    """Canonical v2 inputs, including the historical R7 code root."""

    r7_root: Path
    target_root: Path
    epoch_budget: int
    schedule_seed: int
    r7_code_root: Path

    def __post_init__(self) -> None:
        _V1.PostR7ProviderConfig(
            r7_root=self.r7_root, target_root=self.target_root,
            epoch_budget=self.epoch_budget, schedule_seed=self.schedule_seed,
        )
        _validated_code_root(self.r7_code_root)

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "PostR7ProviderConfig":
        if not isinstance(payload, Mapping) or set(payload) != _CONFIG_FIELDS:
            _fail("post-R7 provider config has an unexpected key set")
        if payload.get("schema") != CONFIG_SCHEMA:
            _fail("post-R7 provider config schema drifted")
        paths: list[Path] = []
        for field in ("r7_root", "target_root", "r7_code_root"):
            value = payload.get(field)
            if not isinstance(value, str) or not value or not Path(value).is_absolute():
                _fail(f"config {field} must be an absolute path")
            paths.append(Path(value))
        return cls(
            r7_root=paths[0], target_root=paths[1],
            epoch_budget=payload.get("epoch_budget"),
            schedule_seed=payload.get("schedule_seed"), r7_code_root=paths[2],
        )


def _config_from_environment() -> PostR7ProviderConfig:
    config_text = os.environ.get(CONFIG_PATH_ENV)
    expected_text = os.environ.get(CONFIG_SHA256_ENV)
    if not config_text or not expected_text:
        _fail(f"{CONFIG_PATH_ENV} and {CONFIG_SHA256_ENV} are both required")
    config_path = Path(config_text)
    if not config_path.is_absolute():
        _fail(f"{CONFIG_PATH_ENV} must be an absolute path")
    expected = _digest(expected_text, field=CONFIG_SHA256_ENV)
    actual = _file_sha256(config_path, field="post-R7 provider config")
    if actual != expected:
        _fail("post-R7 provider config SHA-256 disagrees")
    return PostR7ProviderConfig.from_payload(
        _read_canonical_json(config_path, field="post-R7 provider config")
    )


def _v1_relative(path: str | Path, *, field: str) -> Path:
    try:
        return Path(path).resolve().relative_to(_V1.REPO.resolve())
    except (OSError, ValueError) as cause:
        _fail(f"{field} is not fixed beneath the v1 repository", cause=cause)


def _require_same_bytes(left: Path, right: Path, *, field: str) -> None:
    _regular_file(left, field=f"sealed {field}")
    _regular_file(right, field=f"code-root {field}")
    try:
        same = left.read_bytes() == right.read_bytes()
    except OSError as cause:
        _fail(f"cannot compare {field} authority copies", cause=cause)
    if not same:
        _fail(f"code-root {field} differs from sealed authority copy")


def _require_exact(
    actual: Mapping[str, Any], expected: Mapping[str, Any], *, message: str
) -> None:
    if any((actual.get(key) is not value if type(value) is bool
            else actual.get(key) != value) for key, value in expected.items()):
        _fail(message)


def _verify_r7_preflight(root: Path, *, expected_sha256: str,
                         expected_code_manifest_sha256: str,
                         r7_code_root: Path) -> str:
    """Validate the sealed authority against the complete historical closure."""

    code_root = _validated_code_root(Path(r7_code_root))
    preflight = Path(root) / R7_ROOT_PREFLIGHT
    preflight_digest = Path(root) / R7_ROOT_PREFLIGHT_DIGEST
    actual = _file_sha256(preflight, field="R7 authority preflight manifest")
    if actual != _digest(expected_sha256, field="R7 preflight manifest sha256"):
        _fail("R7 result and authority preflight manifest disagree")
    _regular_file(preflight_digest, field="R7 authority preflight digest")
    try:
        sidecar = preflight_digest.read_text(encoding="ascii")
    except (OSError, UnicodeError) as cause:
        _fail("R7 authority preflight digest is unreadable", cause=cause)
    if sidecar != f"{actual}  R7-PREFLIGHT-MANIFEST.json\n":
        _fail("R7 authority preflight digest disagrees")

    manifest_rel = _v1_relative(_PREFLIGHT.MANIFEST, field="R7 preflight manifest")
    manifest_sha_rel = _v1_relative(_PREFLIGHT.MANIFEST_SHA, field="R7 preflight digest")
    _require_same_bytes(preflight, code_root / manifest_rel, field="preflight manifest")
    _require_same_bytes(preflight_digest, code_root / manifest_sha_rel,
                        field="preflight digest sidecar")

    payload = _read_canonical_json(preflight, field="R7 authority preflight manifest")
    expected_fields = {
        "bindings", "code_manifest", "configuration", "contract",
        "initial_network_sha256_by_seed", "launch", "manifest_version",
        "process_environment", "schema", "status", "student_seeds", "worlds",
    }
    if set(payload) != expected_fields:
        _fail("R7 preflight manifest field set drifted")
    _require_exact(payload, {
        "schema": R7_PREFLIGHT_SCHEMA, "manifest_version": 1,
        "status": R7_PREFLIGHT_STATUS, "launch": R7_PREFLIGHT_LAUNCH,
        "worlds": list(_PREFLIGHT.WORLDS),
        "student_seeds": list(_PREFLIGHT.STUDENT_SEEDS),
        "process_environment": _PREFLIGHT.PROCESS_ENVIRONMENT,
    }, message="R7 preflight schema/status/world/seed boundary drifted")
    if payload.get("initial_network_sha256_by_seed") != _PREFLIGHT.INITIAL_DIGESTS:
        _fail("R7 preflight initial network seed digests drifted")
    if payload.get("contract") != {"path": _PREFLIGHT.CONTRACT,
                                   "sha256": _SCHEDULE.R7_CONTRACT_SHA256}:
        _fail("R7 preflight contract binding drifted")

    code_manifest_rel = _v1_relative(_PREFLIGHT.CODE_MANIFEST,
                                     field="R7 launch code manifest")
    code_manifest_sha_rel = _v1_relative(_PREFLIGHT.CODE_MANIFEST_SHA,
                                         field="R7 launch code-manifest digest")
    expected_code_sha = _digest(expected_code_manifest_sha256,
                                field="R7 launch code manifest sha256")
    code_link = payload.get("code_manifest")
    if not isinstance(code_link, Mapping) or set(code_link) != {"path", "sha256"}:
        _fail("R7 preflight code-manifest binding is missing")
    if code_link != {"path": code_manifest_rel.as_posix(), "sha256": expected_code_sha}:
        _fail("R7 preflight code-manifest binding disagrees")
    if _file_sha256(code_root / code_manifest_rel,
                    field="R7 launch code manifest") != expected_code_sha:
        _fail("R7 launch code manifest bytes disagree with sealed R7")
    code_manifest_digest_sha = _file_sha256(code_root / code_manifest_sha_rel,
                                            field="R7 launch code-manifest digest")

    configuration = payload.get("configuration")
    if not isinstance(configuration, Mapping):
        _fail("R7 preflight configuration is missing")
    critical_configuration = {
        "split": "TRAIN_DEVELOPMENT", "test_split_opened": False,
        "episode_training": False, "scientific_efficacy": False,
        "claim_ceiling": _PREFLIGHT.CLAIM_CEILING,
        "worlds": list(_PREFLIGHT.WORLDS),
        "student_seeds": list(_PREFLIGHT.STUDENT_SEEDS),
        "steps_per_episode": 10, "users": 100, "action_count": 28,
        "draw_count": 32, "fold_count": 8, "fit_updates": 2000,
        "lineage": 2026092101,
        "field_component": "MCRL_V023_LCSRS_C3_OBSERVABILITY_V1",
        "placebo_key": "MCRL_V023_LCSRS_MATCHED_PLACEBO_V1",
        "placebo_key_sha256": "7dc54ab9323b60b30a1bfdbde60872b1f825e4b142dac2c0c0f2269d147a0825",
        "source_artifact_schema": "multi-catfish-mcrl-v023-lcsrs-source-artifact-v1",
        "lambda_hex": "0x1.c3c0a7b6b86d3p+26",
        "kappa_hex": "0x1.2cea89d260f2ap+33",
        "process_environment": _PREFLIGHT.PROCESS_ENVIRONMENT,
        "source_jobs": 8, "fit_jobs": 8, "composition_jobs": 8,
        "selected_checkpoint_role":
            "FROZEN_GATE_BACKGROUND_PROVENANCE_ONLY_NOT_CURRENT_LEARNER_INITIALIZATION",
    }
    for field, expected in critical_configuration.items():
        if configuration.get(field) != expected:
            _fail(f"R7 preflight configuration.{field} drifted")
    if configuration.get("learner") != _PREFLIGHT.EXPECTED_LEARNER:
        _fail("R7 preflight learner configuration drifted")

    bindings = payload.get("bindings")
    if not isinstance(bindings, list) or not bindings:
        _fail("R7 preflight bindings are missing")
    by_role: dict[str, Mapping[str, Any]] = {}
    for index, item in enumerate(bindings):
        if not isinstance(item, Mapping) or set(item) != {"path", "role", "sha256"}:
            _fail(f"R7 preflight binding {index} is malformed")
        role = item.get("role")
        if not isinstance(role, str) or not role or role in by_role:
            _fail("R7 preflight binding roles are missing or repeated")
        by_role[role] = item
    expected_bindings = {
        "base_contract": (_PREFLIGHT.BASE_CONTRACT, _SCHEDULE.R7_BASE_CONTRACT_SHA256),
        "code_manifest": (code_manifest_rel.as_posix(), expected_code_sha),
        "code_manifest_digest": (
            code_manifest_sha_rel.as_posix(), code_manifest_digest_sha
        ),
    }
    for role, (expected_path, expected_binding_sha) in expected_bindings.items():
        binding = by_role.get(role)
        if not isinstance(binding, Mapping):
            _fail(f"R7 preflight lacks {role} binding")
        if binding.get("path") != expected_path or binding.get("sha256") != expected_binding_sha:
            _fail(f"R7 preflight {role} binding disagrees")
        _digest(binding.get("sha256"), field=f"R7 preflight {role} sha256")

    prereg = code_root / Path(_PREFLIGHT.PREREGISTRATION)
    try:
        receipt = _PREFLIGHT.validate_manifest(
            preflight, manifest_digest_path=preflight_digest, repo=code_root,
            prereg_path=prereg)
    except Exception as cause:
        _fail("R7 preflight authoritative validation failed", cause=cause)
    if not isinstance(receipt, Mapping):
        _fail("R7 preflight authoritative validator returned no receipt")
    _require_exact(receipt, {
        "schema": R7_PREFLIGHT_RECEIPT_SCHEMA,
        "status": R7_PREFLIGHT_RECEIPT_STATUS,
        "manifest_status": R7_PREFLIGHT_STATUS, "launch": R7_PREFLIGHT_LAUNCH,
        "manifest_file_sha256": actual, "code_manifest_sha256": expected_code_sha,
        "worlds": list(_PREFLIGHT.WORLDS),
        "student_seeds": list(_PREFLIGHT.STUDENT_SEEDS),
        "claim_ceiling": _PREFLIGHT.CLAIM_CEILING, "test_split_opened": False,
        "episode_training": False, "scientific_efficacy": False,
    }, message="R7 preflight authoritative receipt crossed a frozen boundary")
    return _digest(by_role["base_contract"].get("sha256"), field="R7 base contract sha256")


def _runtime_list_sha256(records: object) -> str:
    """Hash the complete list as compact sorted-key finite ASCII JSON.

    ``_SCHEDULE.canonical_sha256`` deliberately adds no trailing newline; both
    runtime-list digests and the complete provider identity use that encoding.
    """

    return _SCHEDULE.canonical_sha256(records)


def _r7_runtime_bindings(preflight_bindings: object) -> dict[str, Mapping[str, Any]]:
    if not isinstance(preflight_bindings, list) or not preflight_bindings:
        _fail("R7 preflight bindings are unavailable for runtime authentication")
    by_path: dict[str, Mapping[str, Any]] = {}
    for index, item in enumerate(preflight_bindings):
        if not isinstance(item, Mapping) or set(item) != {"path", "role", "sha256"}:
            _fail(f"R7 preflight runtime binding {index} is malformed")
        path = item.get("path")
        if not isinstance(path, str) or not path or path in by_path:
            _fail("R7 preflight runtime binding paths are missing or repeated")
        _digest(item.get("sha256"), field=f"R7 preflight runtime binding {path}")
        by_path[path] = item
    return by_path


def _runtime_module(relative: str, module_name: str) -> object:
    scratch_modules = {
        ".scratch/multi-catfish-v023-r7-launch-ready/preflight_r7_balanced.py":
            _PREFLIGHT,
        ".scratch/multi-catfish-v023-r7-launch-ready/r7_balanced_successor_gate.py":
            _R7_GATE,
        ".scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_fit_adapter.py":
            _FIT,
    }
    pinned = scratch_modules.get(relative)
    loaded = sys.modules.get(module_name)
    if pinned is not None:
        if loaded is not None and loaded is not pinned:
            _fail(f"conflicting loaded runtime module object: {module_name}")
        return pinned
    if loaded is not None:
        return loaded
    try:
        return importlib.import_module(module_name)
    except Exception as cause:
        _fail(f"cannot import declared runtime module: {module_name}", cause=cause)


def _exact_runtime_origin(
    learner: Path,
    *,
    relative: str,
    module_name: str,
    module: object,
) -> Path:
    """Return an exact regular origin, rejecting foreign paths before filtering."""

    expected = learner / relative
    module_file = getattr(module, "__file__", None)
    if not isinstance(module_file, str) or not module_file:
        _fail(f"loaded runtime module has no file origin: {module_name}")
    raw_origin = Path(module_file)
    if not raw_origin.is_absolute() or raw_origin != expected:
        _fail(
            "loaded runtime module origin disagrees with learner checkout: "
            f"{module_name}"
        )
    if raw_origin.is_symlink() or not raw_origin.is_file():
        _fail(f"loaded runtime module origin is not a regular file: {module_name}")
    try:
        origin = raw_origin.resolve(strict=True)
    except OSError as cause:
        _fail(f"loaded runtime module origin is unavailable: {module_name}", cause=cause)
    if origin != expected or not origin.is_relative_to(learner):
        _fail(
            "loaded runtime module origin disagrees with learner checkout: "
            f"{module_name}"
        )
    return origin


def _verify_declared_runtime(
    learner: Path,
    *,
    declarations: Mapping[str, str],
    by_path: Mapping[str, Mapping[str, Any]],
    require_r7_hash: bool,
    field: str,
    sort_records: bool,
) -> list[dict[str, str]]:
    items = list(declarations.items())
    if sort_records:
        items.sort(key=lambda item: (item[0], item[1]))
    observed: list[tuple[str, str, Path]] = []
    for relative, module_name in items:
        if relative not in by_path:
            _fail(f"{field} path is not R7-bound: {relative}")
        module = _runtime_module(relative, module_name)
        origin = _exact_runtime_origin(
            learner,
            relative=relative,
            module_name=module_name,
            module=module,
        )
        observed.append((relative, module_name, origin))

    checked: list[dict[str, str]] = []
    for relative, module_name, origin in observed:
        actual = _file_sha256(origin, field=f"{field} {relative}")
        r7_declared = _digest(
            by_path[relative].get("sha256"),
            field=f"{field} R7 binding {relative}",
        )
        if require_r7_hash and actual != r7_declared:
            _fail(f"{field} R7 binding drifted: {relative}")
        checked.append({
            "path": relative,
            "module": module_name,
            "loaded_from": str(origin),
            "sha256": actual,
        })
    return checked


def _verify_r7_authentication_runtime(learner_repo: str | Path,
                                      r7_code_root: str | Path,
                                      preflight_bindings: object) -> tuple[list[dict[str, str]], str]:
    """Bind A: the ordered 18-file R7 authentication responsibility."""

    learner = _regular_dir(Path(learner_repo), field="learner checkout")
    _validated_code_root(Path(r7_code_root))
    checked = _verify_declared_runtime(
        learner,
        declarations=R7_AUTHENTICATION_RUNTIME_MODULES,
        by_path=_r7_runtime_bindings(preflight_bindings),
        require_r7_hash=True,
        field="R7 authentication runtime",
        sort_records=False,
    )
    return checked, _runtime_list_sha256(checked)


def _verify_r7_bound_learner_runtime(
    learner_repo: str | Path,
    preflight_bindings: object,
) -> tuple[list[dict[str, str]], str]:
    """Bind L: the explicit 33-file R7-bound live learner responsibility."""

    learner = _regular_dir(Path(learner_repo), field="learner checkout")
    checked = _verify_declared_runtime(
        learner,
        declarations=R7_BOUND_LEARNER_RUNTIME_MODULES,
        by_path=_r7_runtime_bindings(preflight_bindings),
        require_r7_hash=False,
        field="R7-bound learner runtime",
        sort_records=True,
    )
    return checked, _runtime_list_sha256(checked)


def _r7_module_path(module_name: str, by_path: Mapping[str, object]) -> str | None:
    if module_name != "mcrl" and not module_name.startswith("mcrl."):
        return None
    base = Path("src").joinpath(*module_name.split("."))
    candidates = (base.with_suffix(".py").as_posix(),
                  (base / "__init__.py").as_posix())
    found = [candidate for candidate in candidates if candidate in by_path]
    if len(found) > 1:
        _fail(f"R7 module path is ambiguous: {module_name}")
    return found[0] if found else None


def _verify_r7_bound_runtime_closure(
    learner_repo: str | Path,
    preflight_bindings: object,
) -> None:
    """Reject foreign, conflicting, missing, or undeclared R7-bound origins."""

    learner = _regular_dir(Path(learner_repo), field="learner checkout")
    by_path = _r7_runtime_bindings(preflight_bindings)
    declared = dict(R7_AUTHENTICATION_RUNTIME_MODULES)
    declared.update(R7_BOUND_LEARNER_RUNTIME_MODULES)
    declared_by_module = {module: path for path, module in declared.items()}
    discovered: dict[str, str] = {}

    # Resolve project module names first.  A foreign mcrl module is rejected
    # before the later checkout-location filter can hide it.
    for module_name, module in tuple(sys.modules.items()):
        relative = _r7_module_path(module_name, by_path)
        if relative is None:
            continue
        if declared_by_module.get(module_name) != relative:
            _fail(f"loaded R7-bound module has an undeclared origin: {module_name}")
        _exact_runtime_origin(
            learner,
            relative=relative,
            module_name=module_name,
            module=module,
        )

    for module_name, module in tuple(sys.modules.items()):
        module_file = getattr(module, "__file__", None)
        if not isinstance(module_file, str) or not Path(module_file).is_absolute():
            continue
        try:
            origin = Path(module_file).resolve(strict=True)
        except OSError:
            continue
        if not origin.is_relative_to(learner):
            continue
        relative = origin.relative_to(learner).as_posix()
        if relative not in by_path:
            continue
        if declared.get(relative) != module_name:
            _fail(
                "loaded R7-bound module has a conflicting or undeclared origin: "
                f"{module_name}"
            )
        if relative in discovered:
            _fail(f"loaded R7-bound path has duplicate module origins: {relative}")
        discovered[relative] = module_name

    if discovered != declared:
        missing = sorted(set(declared) - set(discovered))
        additional = sorted(set(discovered) - set(declared))
        _fail(
            "R7-bound runtime closure differs from the pinned 18/33 declarations; "
            f"missing={missing}, additional={additional}"
        )


@dataclass(frozen=True, slots=True)
class R7GoAuthentication:
    """A sealed R7 GO result plus historical and executing-code provenance."""

    root: Path
    result_path: Path
    result_sha256: str
    result: Mapping[str, Any]
    source_panel: object
    records: tuple[object, ...]
    binding: object
    r7_code_root: Path
    r7_preflight_manifest_sha256: str
    r7_code_manifest_sha256: str
    r7_result_manifest_sha256: str
    r7_gate_result_sha256: str
    r7_authentication_runtime: tuple[Mapping[str, str], ...]
    r7_authentication_runtime_sha256: str
    r7_bound_learner_runtime: tuple[Mapping[str, str], ...]
    r7_bound_learner_runtime_sha256: str


def authenticate_r7_go(root: str | Path, *, r7_code_root: str | Path) -> R7GoAuthentication:
    """Reopen sealed R7 data against distinct historical and live code roots."""

    code_root = _validated_code_root(Path(r7_code_root))
    root_path = _regular_dir(Path(root), field="R7 result root")
    listed = _verify_result_manifest(root_path)
    result_manifest_sha = _file_sha256(
        root_path / "MANIFEST.sha256", field="R7 MANIFEST.sha256"
    )
    result_path = root_path / R7_ROOT_RESULT
    verification_path = root_path / R7_ROOT_VERIFICATION
    source_manifest_path = root_path / R7_ROOT_SOURCE_MANIFEST
    for path, field in (
        (result_path, "R7 result.json"),
        (verification_path, "R7 verification.json"),
        (source_manifest_path, "R7 source-manifest.json"),
    ):
        relative = path.relative_to(root_path).as_posix()
        if relative not in listed:
            _fail(f"{field} is not manifest-listed")
        _regular_file(path, field=field)
    result = _read_canonical_json(result_path, field="R7 result.json")
    verification = _read_canonical_json(
        verification_path, field="R7 verification.json"
    )
    _essential_result_fields(result)
    launch_metadata = _verify_launch_metadata(root_path, listed)
    split = launch_metadata["split"]
    if "split" in result and result["split"] != split:
        _fail("R7 final result split disagrees with launch metadata")
    for result_field, metadata_field in (
        ("contract_sha256", "contract_sha256"),
        ("launch_decision_sha256", "launch_decision_sha256"),
        ("code_manifest_sha256", "code_manifest_sha256"),
        ("preflight_manifest_sha256", "preflight_manifest_sha256"),
        ("launch_manifest_sha256", "preflight_manifest_sha256"),
    ):
        if launch_metadata.get(metadata_field) != result.get(result_field):
            _fail(f"R7 final result and launch metadata disagree at {result_field}")
    for field in _R7_COMMON_FIELDS:
        if verification.get(field) != result.get(field):
            _fail(f"R7 result and verification disagree at {field}")

    preflight_sha = str(result["preflight_manifest_sha256"])
    _verify_r7_authority_snapshot(
        root_path,
        listed,
        expected_preflight_sha256=preflight_sha,
        expected_contract_sha256=result["contract_sha256"],
        expected_execution_addendum_sha256=result["execution_addendum_sha256"],
    )
    base_contract_sha = _verify_r7_preflight(
        root_path,
        expected_sha256=preflight_sha,
        expected_code_manifest_sha256=result["code_manifest_sha256"],
        r7_code_root=code_root,
    )
    if base_contract_sha != _SCHEDULE.R7_BASE_CONTRACT_SHA256:
        _fail("R7 base contract does not equal the current frozen contract")
    preflight_payload = _read_canonical_json(
        root_path / R7_ROOT_PREFLIGHT, field="R7 authority preflight manifest"
    )
    runtime, runtime_sha = _verify_r7_authentication_runtime(
        REPO, code_root, preflight_payload.get("bindings")
    )
    learner_runtime, learner_runtime_sha = _verify_r7_bound_learner_runtime(
        REPO, preflight_payload.get("bindings")
    )

    try:
        source_panel = _FIT.load_v023_source_panel(
            source_directory=root_path,
            source_manifest=source_manifest_path,
            preflight_manifest_sha256=preflight_sha,
        )
    except Exception as cause:
        _fail("sealed R7 source panel failed typed reauthentication", cause=cause)
    if source_panel.source_manifest_sha256 != result["source_manifest_sha256"]:
        _fail("R7 source panel manifest digest disagrees with final result")
    records_by_world = source_panel.records_by_world
    if tuple(sorted(records_by_world)) != _SCHEDULE.R7_WORLDS:
        _fail("R7 source panel does not cover the exact frozen worlds")
    records = tuple(record for world in _SCHEDULE.R7_WORLDS
                    for record in records_by_world[world])
    if any(not records_by_world[world] for world in _SCHEDULE.R7_WORLDS):
        _fail("R7 source panel contains an empty world")
    try:
        record_panel_sha = _SCHEDULE.canonical_record_panel_sha256(records)
    except Exception as cause:
        _fail("R7 source record panel failed canonical reauthentication", cause=cause)
    result_sha = _file_sha256(result_path, field="R7 result.json")
    if listed["result.json"] != result_sha:
        _fail("R7 result manifest entry disagrees")
    try:
        copied_fields = (
            "schema", "status", "integrity_status", "c3_decision", "context_status",
            "claim_ceiling", "source_count", "fit_count", "composition_count",
            "contract_sha256", "execution_addendum_sha256", "launch_decision_sha256",
            "code_manifest_sha256", "preflight_manifest_sha256",
            "launch_manifest_sha256", "source_manifest_sha256", "test_split_opened",
            "episode_training", "scientific_claim", "no_rescue",
            "no_scientific_token_before_integrity",
        )
        binding_values = {field: result[field] for field in copied_fields}
        binding = _SCHEDULE.R7GoDecisionBinding(**binding_values, split=split,
            worlds=_SCHEDULE.R7_WORLDS, base_contract_sha256=base_contract_sha,
            gate_result_sha256=result_sha, record_panel_sha256=record_panel_sha)
        binding.verify()
    except Exception as cause:
        _fail("sealed R7 result could not form a valid GO binding", cause=cause)
    _verify_r7_bound_runtime_closure(REPO, preflight_payload.get("bindings"))
    frozen_runtime = tuple(MappingProxyType(dict(item)) for item in runtime)
    frozen_learner_runtime = tuple(
        MappingProxyType(dict(item)) for item in learner_runtime
    )
    return R7GoAuthentication(
        root=root_path, result_path=result_path, result_sha256=result_sha,
        result=MappingProxyType(dict(result)), source_panel=source_panel,
        records=records, binding=binding, r7_code_root=code_root,
        r7_preflight_manifest_sha256=preflight_sha,
        r7_code_manifest_sha256=str(result["code_manifest_sha256"]),
        r7_result_manifest_sha256=result_manifest_sha,
        r7_gate_result_sha256=result_sha,
        r7_authentication_runtime=frozen_runtime,
        r7_authentication_runtime_sha256=runtime_sha,
        r7_bound_learner_runtime=frozen_learner_runtime,
        r7_bound_learner_runtime_sha256=learner_runtime_sha,
    )


def build_provider(config: PostR7ProviderConfig) -> V023PostR7Provider:
    """Authenticate inputs and preserve v1 scientific construction unchanged."""

    if type(config) is not PostR7ProviderConfig:
        _fail("build_provider requires PostR7ProviderConfig")
    r7 = authenticate_r7_go(config.r7_root, r7_code_root=config.r7_code_root)
    code_root = _validated_code_root(config.r7_code_root)
    if Path(r7.r7_code_root).resolve() != code_root:
        _fail("authenticated R7 code root disagrees with config")
    runtime = [dict(item) for item in r7.r7_authentication_runtime]
    runtime_sha = _runtime_list_sha256(runtime)
    if runtime_sha != r7.r7_authentication_runtime_sha256:
        _fail("R7 authentication runtime receipt digest disagrees")
    learner_runtime = [dict(item) for item in r7.r7_bound_learner_runtime]
    learner_runtime_sha = _runtime_list_sha256(learner_runtime)
    if learner_runtime_sha != r7.r7_bound_learner_runtime_sha256:
        _fail("R7-bound learner runtime receipt digest disagrees")
    target_root = _regular_dir(config.target_root, field="C1/C2 target root")
    target_manifest_sha = _file_sha256(target_root / "MANIFEST.sha256",
                                       field="C1/C2 target MANIFEST.sha256")
    try:
        target_artifact = _BRIDGE.load_completed_target_artifact(target_root)
        if _file_sha256(
            target_root / "MANIFEST.sha256", field="C1/C2 target manifest"
        ) != target_manifest_sha:
            _fail("C1/C2 target root changed during authentication")
        schedule = _SCHEDULE.build_v023_c3_source_schedule(
            r7.records, r7_go=r7.binding, epoch_budget=config.epoch_budget,
            schedule_seed=config.schedule_seed,
        )
        receipt_sha = _schedule_receipt_identity(
            schedule, expected_epoch_budget=config.epoch_budget,
            expected_schedule_seed=config.schedule_seed, expected_gate=r7.binding,
            expected_records=r7.records,
        )
        neutral_inputs = _BRIDGE.load_lcsrs_c3_inputs(
            schedule.surfaces, schedule.neutral_batches,
            normalized_targets_by_anchor=schedule.neutral_targets_by_anchor,
        )
        informed_inputs = _BRIDGE.load_lcsrs_c3_inputs(
            schedule.surfaces, schedule.informed_batches,
            normalized_targets_by_anchor=schedule.informed_targets_by_anchor,
        )
        neutral = _BRIDGE.C3SourceBinding(
            source="neutral", source_id=schedule.neutral_source_id, inputs=neutral_inputs
        )
        informed = _BRIDGE.C3SourceBinding(
            source="informed", source_id=schedule.informed_source_id,
            inputs=informed_inputs,
        )
        delegate = _BRIDGE.V023ProviderOrchestratorBridge(
            target_artifact, c3_neutral=neutral, c3_informed=informed,
            planned_source_training_epochs=config.epoch_budget,
        )
        if not isinstance(delegate, _BRIDGE.DeterministicRouteBatchProvider):
            _fail("post-R7 bridge does not satisfy the runner provider protocol")
    except V023PostR7ProviderFactoryError:
        raise
    except Exception as cause:
        _fail("post-R7 provider construction failed closed", cause=cause)

    identity_payload = {
        "schema": IDENTITY_SCHEMA,
        "target_manifest_sha256": target_manifest_sha,
        "c3_schedule_receipt_sha256": receipt_sha,
        "epoch_budget": config.epoch_budget,
        "c3_source_ids": {
            "neutral": schedule.neutral_source_id,
            "informed": schedule.informed_source_id,
        },
        "r7_code_root": str(code_root),
        "r7_preflight_manifest_sha256": _digest(
            r7.r7_preflight_manifest_sha256,
            field="r7_preflight_manifest_sha256",
        ),
        "r7_code_manifest_sha256": _digest(
            r7.r7_code_manifest_sha256,
            field="r7_code_manifest_sha256",
        ),
        "r7_result_manifest_sha256": _digest(
            r7.r7_result_manifest_sha256,
            field="r7_result_manifest_sha256",
        ),
        "r7_gate_result_sha256": _digest(
            r7.r7_gate_result_sha256,
            field="r7_gate_result_sha256",
        ),
        "r7_authentication_runtime": runtime,
        "r7_authentication_runtime_sha256": _digest(
            runtime_sha, field="R7 authentication runtime sha256"
        ),
        "r7_bound_learner_runtime": learner_runtime,
        "r7_bound_learner_runtime_sha256": _digest(
            learner_runtime_sha, field="R7-bound learner runtime sha256"
        ),
    }
    identity = f"{FACTORY_SCHEMA}:{_runtime_list_sha256(identity_payload)}"
    if len(identity) > 512:
        _fail("provider identity exceeds runner limit")
    return V023PostR7Provider(_delegate=delegate,
                              _identity_payload=MappingProxyType(identity_payload),
                              _identity=identity)


def make_provider() -> V023PostR7Provider:
    return build_provider(_config_from_environment())
__all__ = [
    "CONFIG_PATH_ENV", "CONFIG_SCHEMA", "CONFIG_SHA256_ENV", "FACTORY_SCHEMA", "IDENTITY_SCHEMA",
    "PostR7ProviderConfig", "R7GoAuthentication", "R7_AUTHENTICATION_RUNTIME_MODULES",
    "R7_AUTHENTICATION_RUNTIME_PATHS", "R7_BOUND_LEARNER_RUNTIME_MODULES",
    "R7_BOUND_LEARNER_RUNTIME_PATHS", "V023PostR7Provider", "V023PostR7ProviderFactoryError",
    "authenticate_r7_go", "build_provider", "make_provider"]
