"""Current V0.23 real five-arm development episode runner.

This module is the physical-execution seam for the current LC-SRS method.  It
does not contain a simulator implementation and it does not make a gate or
scientific decision.  A real adapter must provide the repository's
``TrainerEnvironment``/TLE execution and return the current
``FiveArmEpisodeReceipt``.  The runner owns admission, arm ordering,
checkpoint cadence, resume validation, and receipt aggregation.

The older ``multi-catfish-v023-physical`` runner is intentionally not imported
here: that runner is a provisional V0.20 Q1/Q2, two-arm DROP_C3 seam and its
receipt cannot be promoted to the current V0.23 three-route method.  Passing
one of its receipts to this runner is a hard error.

No default invocation runs a simulator.  In particular, the command-line
entry point below performs preflight only.  A production caller must first
obtain a separately sealed V0.23 episode-screen admission artifact and then
construct a ``V023RealSimulatorTleAdapter`` around the real environment.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Protocol, runtime_checkable


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
_BINDING_PATH = REPO / ".scratch" / "multi-catfish-v023-five-arm-evaluation" / "v023_five_arm_eval_binding.py"
_RESULTS_PATH = REPO / ".scratch" / "multi-catfish-v023-five-arm-evaluation" / "v023_five_arm_eval_results.py"


def _load_sibling(name: str, path: Path) -> Any:
    """Load the receipt layer when this scratch module is imported by path."""

    loaded = sys.modules.get(name)
    if loaded is not None:
        loaded_path = Path(str(getattr(loaded, "__file__", ""))).resolve()
        if loaded_path != path.resolve():
            raise RuntimeError(f"{name} is already loaded from a different path")
        return loaded
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load V0.23 receipt layer: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_binding = _load_sibling("v023_five_arm_eval_binding", _BINDING_PATH)
_results = _load_sibling("v023_five_arm_eval_results", _RESULTS_PATH)

ARMS: tuple[str, ...] = tuple(_binding.ARMS)
CHECKPOINT_EVERY = int(_binding.CHECKPOINT_EVERY)

SCHEMA = "multi-catfish-mcrl-v023-real-five-arm-episode-runner-v1"
SCHEMA_VERSION = 1
MANIFEST_SCHEMA = "multi-catfish-mcrl-v023-real-five-arm-manifest-v1"
CHECKPOINT_SCHEMA = "multi-catfish-mcrl-v023-real-five-arm-checkpoint-v1"
RESULT_SCHEMA = "multi-catfish-mcrl-v023-real-five-arm-result-v1"
STATUS = "SEALED_PENDING_GATE"
REAL_ADAPTER_IDENTITY = "v023-real-simulator-tle-adapter-v1"
TEST_FIXTURE_ADAPTER_IDENTITY = "v023-test-fixture-simulator-tle-v1"
SUPPORTED_EPISODE_COUNTS = frozenset({100, 500})

# This is the currently authenticated d40 Q1/Q2 background named by the V0.23
# method/gate contracts.  It is an artifact identity, not a claim that the
# current C3 gate or episode admission has passed.
CURRENT_Q12_CHECKPOINT_SHA256 = (
    "d40a0f3095f9bb9010d0146a88a77b3c8a824fb9bd3e5aee2205f3ae8be592dc"
)
CURRENT_GATE_CONTRACT_SHA256 = (
    "1e69a2e7242198adce97e6357e4205a29fe6d1fb06a48dc7e1839a675529811a"
)
CURRENT_C3_VIEW_SCHEMA_SHA256 = (
    "c1c455c7207048c29b3b58218a59dd67852ec8d2077c417181f1f7e07300cbe6"
)
CURRENT_C3_VIEW_CONFIG_SHA256 = (
    "c406a6a2a0da78a855c8f850c45803cfa1763a3e7e40823693b39207f14c3324"
)


class V023RealFiveArmError(ValueError):
    """Base error for the fail-closed current V0.23 physical seam."""


class V023RealFiveArmAdmissionError(V023RealFiveArmError):
    """The current source/policy/gate artifacts are not admitted."""

    def __init__(self, issues: Sequence[str]) -> None:
        self.issues = tuple(str(issue) for issue in issues if str(issue).strip())
        if not self.issues:
            self.issues = ("unknown V0.23 admission failure",)
        super().__init__(
            "V0.23 real five-arm admission failed:\n"
            + "\n".join(f"- {issue}" for issue in self.issues)
        )


class V023LCSRSPolicyError(V023RealFiveArmError):
    """The current three-route model cannot be used as a policy adapter."""


def _jsonable(value: object) -> object:
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, child in value.items():
            if not isinstance(key, str):
                raise V023RealFiveArmError("canonical JSON mapping keys must be strings")
            result[key] = _jsonable(child)
        return result
    if isinstance(value, (tuple, list)):
        return [_jsonable(child) for child in value]
    if isinstance(value, Path):
        return value.as_posix()
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise V023RealFiveArmError(
        f"unsupported canonical value: {type(value).__name__}"
    )


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            _jsonable(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V023RealFiveArmError("payload is not finite canonical ASCII JSON") from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V023RealFiveArmError(f"{field} must be a lowercase SHA-256")
    return value


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise V023RealFiveArmError(f"{field} must be non-empty trimmed text")
    return value


def file_sha256(path: str | Path) -> str:
    """Hash one regular file; symlink indirection is never accepted."""

    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V023RealFiveArmError(f"artifact is not a regular file: {source}")
    digest = hashlib.sha256()
    try:
        with source.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as error:
        raise V023RealFiveArmError(f"cannot read artifact: {source}") from error
    return digest.hexdigest()


class V023LCSRSThreeRoutePolicy:
    """Current one-pass policy bridge for a real simulator adapter.

    The bridge is intentionally small: it evaluates the native 228-D Q1/Q2
    state once, accepts an already captured structured :class:`C3View`, and
    delegates to ``EEAxisLCSRSThreeRoute.select_greedy_actions``.  It cannot
    add a coordinator, drop a head, or select a policy from an outcome.  The
    model is supplied by the caller because loading a checkpoint is an
    artifact-admission decision owned by the five-arm request.
    """

    algorithm = "multi-catfish-mcrl-v023-lcsrs-three-route"

    def __init__(self, model: Any) -> None:
        try:
            from mcrl.algorithms.ee_axis_lcsrs_three_route import (
                EEAxisLCSRSThreeRoute,
            )
            from mcrl.algorithms.ee_axis_lcsrs_c3_head import LCSRSC3QNetwork
        except ImportError as error:  # pragma: no cover - project train extra
            raise V023LCSRSPolicyError(
                "current V0.23 three-route model imports are unavailable"
            ) from error
        if not isinstance(model, EEAxisLCSRSThreeRoute):
            raise V023LCSRSPolicyError(
                "policy must be current EEAxisLCSRSThreeRoute, not legacy MODQN"
            )
        if len(model.q_networks) != 3 or not isinstance(model.q3, LCSRSC3QNetwork):
            raise V023LCSRSPolicyError(
                "current policy must contain exactly Q1, Q2, and structured Q3"
            )
        self.model = model

    def select_actions(
        self,
        *,
        native_state: object,
        c3_view: object,
        native_observation_event_digest: str,
    ) -> Any:
        """Select one masked action vector from the current three-route model."""

        try:
            snapshot = self.model.capture_q12(
                native_state,
                native_observation_event_digest=native_observation_event_digest,
            )
            return self.model.select_greedy_actions(snapshot, c3_view)
        except Exception as error:
            raise V023LCSRSPolicyError(
                "current V0.23 three-route action selection failed"
            ) from error


def load_d40_q12_background(
    model: Any,
    q12_artifact: ArtifactBinding,
) -> Any:
    """Load only the authenticated d40 Q1/Q2 background into a V0.23 model.

    This helper never loads a C3 target, chooses a checkpoint, or performs an
    episode.  The caller must still bind a current C3 model artifact before a
    ``FULL`` policy can be admitted.
    """

    if q12_artifact.sha256 != CURRENT_Q12_CHECKPOINT_SHA256:
        raise V023LCSRSPolicyError(
            "Q1/Q2 artifact is not the authenticated current d40 checkpoint"
        )
    try:
        q12_artifact.verify()
        import torch

        payload = torch.load(
            q12_artifact.path,
            map_location="cpu",
            weights_only=False,
        )
    except Exception as error:  # pragma: no cover - exercised with real artifact
        raise V023LCSRSPolicyError("cannot load authenticated d40 Q1/Q2 checkpoint") from error
    if not isinstance(payload, Mapping):
        raise V023LCSRSPolicyError("d40 Q1/Q2 checkpoint payload is not a mapping")
    try:
        model.load_q12_background(payload)
    except Exception as error:
        raise V023LCSRSPolicyError(
            "d40 Q1/Q2 checkpoint does not match current V0.23 Q1/Q2 configuration"
        ) from error
    return model


@dataclass(frozen=True, slots=True)
class ArtifactBinding:
    """A path and its pre-registered bytes digest."""

    role: str
    path: Path
    sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", Path(self.path))

    def verify(self) -> str:
        _text(self.role, field="artifact.role")
        claimed = _digest(self.sha256, field=f"{self.role}.sha256")
        actual = file_sha256(self.path)
        if actual != claimed:
            raise V023RealFiveArmError(
                f"{self.role}: bytes changed (claimed {claimed}, observed {actual})"
            )
        return actual

    def to_dict(self, *, base: Path | None = None) -> dict[str, object]:
        path = self.path
        if base is not None:
            try:
                path = path.resolve().relative_to(base.resolve())
            except ValueError:
                path = path.resolve()
        return {"role": self.role, "path": path.as_posix(), "sha256": self.sha256}


def _artifact_from_payload(
    value: object,
    *,
    role: str,
    base: Path,
) -> ArtifactBinding:
    if not isinstance(value, Mapping):
        raise V023RealFiveArmError(f"{role}: artifact binding must be an object")
    supplied_role = value.get("role", role)
    if supplied_role != role:
        raise V023RealFiveArmError(
            f"{role}: artifact role drifted to {supplied_role!r}"
        )
    raw_path = value.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise V023RealFiveArmError(f"{role}: artifact path is missing")
    path = Path(raw_path)
    if not path.is_absolute():
        path = base / path
    return ArtifactBinding(role=role, path=path, sha256=value.get("sha256", ""))


@dataclass(frozen=True, slots=True)
class V023RealFiveArmRequest:
    """All immutable inputs required before opening a real episode stream."""

    screen_id: str
    binding: Any
    source_plan_artifact: ArtifactBinding
    tle_archive: ArtifactBinding
    q12_checkpoint: ArtifactBinding
    c3_target_artifact: ArtifactBinding
    policy_artifacts: Mapping[str, ArtifactBinding]
    sealed_gate_admission: ArtifactBinding | None
    episode_count: int
    split: str = "TRAIN_DEVELOPMENT"
    checkpoint_every: int = CHECKPOINT_EVERY

    def _binding_sha(self, issues: list[str]) -> str | None:
        if not isinstance(self.binding, _binding.FiveArmEvaluationBinding):
            issues.append("evaluation_binding: expected FiveArmEvaluationBinding")
            return None
        try:
            return str(self.binding.verify())
        except Exception as error:
            issues.append(f"evaluation_binding: {error}")
            return None

    def _verify_path_binding(
        self,
        artifact: object,
        *,
        role: str,
        issues: list[str],
    ) -> str | None:
        if not isinstance(artifact, ArtifactBinding):
            issues.append(f"{role}: missing ArtifactBinding")
            return None
        try:
            return artifact.verify()
        except Exception as error:
            issues.append(f"{role}: {error}")
            return None

    def _verify_source_plan(self, issues: list[str], binding_sha: str | None) -> str | None:
        observed = self._verify_path_binding(
            self.source_plan_artifact,
            role="source_plan",
            issues=issues,
        )
        if observed is None:
            return None
        try:
            payload = json.loads(self.source_plan_artifact.path.read_text(encoding="ascii"))
            if not isinstance(payload, Mapping):
                raise V023RealFiveArmError("source plan JSON must be an object")
            plan_sha = str(_binding.verify_source_plan_payload(payload))
            bound_sha = str(self.binding.source_plan.get("plan_sha256")) if binding_sha else ""
            if plan_sha != bound_sha:
                raise V023RealFiveArmError(
                    f"source plan digest {plan_sha} disagrees with evaluation binding {bound_sha}"
                )
        except Exception as error:
            issues.append(f"source_plan: {error}")
        return observed

    def _verify_gate(
        self,
        *,
        issues: list[str],
        binding_sha: str | None,
        source_plan_sha: str | None,
        c3_sha: str | None,
    ) -> str | None:
        if self.sealed_gate_admission is None:
            issues.append(
                "sealed_gate_admission: missing sealed V0.23 episode-screen admission "
                "artifact (current contract remains execution-NO-GO)"
            )
            return None
        observed = self._verify_path_binding(
            self.sealed_gate_admission,
            role="sealed_gate_admission",
            issues=issues,
        )
        if observed is None:
            return None
        try:
            payload = json.loads(
                self.sealed_gate_admission.path.read_text(encoding="ascii")
            )
            if not isinstance(payload, Mapping):
                raise V023RealFiveArmError("sealed gate admission JSON must be an object")
            if payload.get("sealed") is not True:
                raise V023RealFiveArmError("sealed flag is not true")
            if payload.get("gate_contract_sha256") != CURRENT_GATE_CONTRACT_SHA256:
                raise V023RealFiveArmError(
                    "gate_contract_sha256 is not the current V0.23 LC-SRS gate contract"
                )
            if payload.get("episode_screen_authorized") is not True:
                raise V023RealFiveArmError(
                    "episode_screen_authorized is not true"
                )
            split = payload.get("split")
            if not isinstance(split, str) or not split.upper().startswith("TRAIN") or "TEST" in split.upper():
                raise V023RealFiveArmError("admission split is not TRAIN-only")
            if payload.get("episode_count") != self.episode_count:
                raise V023RealFiveArmError("admission episode_count disagrees")
            if payload.get("checkpoint_every") != CHECKPOINT_EVERY:
                raise V023RealFiveArmError("admission checkpoint cadence is not 100")
            if binding_sha is not None and payload.get("evaluation_binding_sha256") != binding_sha:
                raise V023RealFiveArmError("admission evaluation binding digest disagrees")
            if source_plan_sha is not None and payload.get("source_plan_sha256") != source_plan_sha:
                raise V023RealFiveArmError("admission source plan digest disagrees")
            if payload.get("q12_checkpoint_sha256") != CURRENT_Q12_CHECKPOINT_SHA256:
                raise V023RealFiveArmError("admission Q1/Q2 d40 checkpoint digest disagrees")
            if payload.get("c3_view_schema_sha256") != CURRENT_C3_VIEW_SCHEMA_SHA256:
                raise V023RealFiveArmError(
                    "admission C3View schema digest is not the current LC-SRS layout"
                )
            if payload.get("c3_view_config_sha256") != CURRENT_C3_VIEW_CONFIG_SHA256:
                raise V023RealFiveArmError(
                    "admission C3View config digest is not the current structured head"
                )
            if c3_sha is not None and payload.get("c3_target_sha256") != c3_sha:
                raise V023RealFiveArmError("admission C3 target digest disagrees")
            contract_sha = payload.get("evaluation_contract_sha256")
            if contract_sha != self.binding.evaluation_contract_sha256:
                raise V023RealFiveArmError("admission evaluation contract digest disagrees")
        except Exception as error:
            issues.append(f"sealed_gate_admission: {error}")
        return observed

    def verify(self) -> str:
        """Verify every binding and return the deterministic run fingerprint."""

        issues: list[str] = []
        try:
            _text(self.screen_id, field="screen_id")
        except Exception as error:
            issues.append(f"screen_id: {error}")
        if type(self.episode_count) is not int or self.episode_count not in SUPPORTED_EPISODE_COUNTS:
            issues.append(
                "episode_count: only pre-registered 100 or 500 episodes are admitted"
            )
        if self.split != "TRAIN_DEVELOPMENT" or "TEST" in self.split.upper():
            issues.append("split: real development runs must use TRAIN_DEVELOPMENT")
        if self.checkpoint_every != CHECKPOINT_EVERY:
            issues.append("checkpoint_every: V0.23 physical checkpoints are fixed at 100")

        binding_sha = self._binding_sha(issues)
        if binding_sha is not None:
            if len(self.binding.worlds) != self.episode_count:
                issues.append(
                    "evaluation_binding: world grid length does not equal episode_count"
                )
            if tuple(policy.arm for policy in self.binding.policies) != ARMS:
                issues.append("evaluation_binding: policy arm order is not the fixed five-arm order")

        source_plan_sha = self._verify_source_plan(issues, binding_sha)
        tle_sha = self._verify_path_binding(self.tle_archive, role="tle_archive", issues=issues)
        q12_sha = self._verify_path_binding(
            self.q12_checkpoint,
            role="q12_checkpoint",
            issues=issues,
        )
        if q12_sha is not None and q12_sha != CURRENT_Q12_CHECKPOINT_SHA256:
            issues.append(
                "q12_checkpoint: current V0.23 binding requires authenticated d40 "
                f"bytes {CURRENT_Q12_CHECKPOINT_SHA256}"
            )
        c3_sha = self._verify_path_binding(
            self.c3_target_artifact,
            role="c3_target_artifact",
            issues=issues,
        )

        expected_arms = set(ARMS)
        supplied_arms = set(self.policy_artifacts)
        if supplied_arms != expected_arms:
            missing = ",".join(sorted(expected_arms - supplied_arms)) or "none"
            extra = ",".join(sorted(supplied_arms - expected_arms)) or "none"
            issues.append(
                f"policy_artifacts: exact five-arm coverage required (missing={missing}; extra={extra})"
            )
        if isinstance(self.binding, _binding.FiveArmEvaluationBinding):
            policies = {policy.arm: policy for policy in self.binding.policies}
            for arm in ARMS:
                artifact = self.policy_artifacts.get(arm)
                actual = self._verify_path_binding(
                    artifact,
                    role=f"policy_artifacts.{arm}",
                    issues=issues,
                )
                if actual is not None and actual != policies[arm].checkpoint_sha256:
                    issues.append(
                        f"policy_artifacts.{arm}: bytes digest does not match its frozen "
                        "policy checkpoint binding"
                    )

        self._verify_gate(
            issues=issues,
            binding_sha=binding_sha,
            source_plan_sha=(str(self.binding.source_plan.get("plan_sha256")) if isinstance(self.binding, _binding.FiveArmEvaluationBinding) else source_plan_sha),
            c3_sha=c3_sha,
        )
        if issues:
            raise V023RealFiveArmAdmissionError(issues)

        assert binding_sha is not None
        assert tle_sha is not None and q12_sha is not None and c3_sha is not None
        return canonical_sha256(
            {
                "schema": SCHEMA,
                "schema_version": SCHEMA_VERSION,
                "screen_id": self.screen_id,
                "split": self.split,
                "episode_count": self.episode_count,
                "checkpoint_every": self.checkpoint_every,
                "evaluation_binding_sha256": binding_sha,
                "source_plan_sha256": source_plan_sha,
                "tle_sha256": tle_sha,
                "q12_checkpoint_sha256": q12_sha,
                "c3_target_sha256": c3_sha,
                "policy_artifacts": {
                    arm: self.policy_artifacts[arm].sha256 for arm in ARMS
                },
                "sealed_gate_admission_sha256": (
                    self.sealed_gate_admission.sha256
                    if self.sealed_gate_admission is not None
                    else None
                ),
            }
        )

    def admit(self) -> "V023RealFiveArmAdmission":
        return V023RealFiveArmAdmission(request=self, run_fingerprint=self.verify())


@dataclass(frozen=True, slots=True)
class V023RealFiveArmAdmission:
    request: V023RealFiveArmRequest
    run_fingerprint: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "screen_id": self.request.screen_id,
            "run_fingerprint": self.run_fingerprint,
            "split": self.request.split,
            "episode_count": self.request.episode_count,
            "checkpoint_every": self.request.checkpoint_every,
            "evaluation_binding_sha256": self.request.binding.verify(),
            "source_plan_sha256": self.request.source_plan_artifact.sha256,
            "tle_archive_sha256": self.request.tle_archive.sha256,
            "q12_checkpoint_sha256": self.request.q12_checkpoint.sha256,
            "c3_target_sha256": self.request.c3_target_artifact.sha256,
            "policy_artifacts": {
                arm: self.request.policy_artifacts[arm].sha256 for arm in ARMS
            },
            "sealed_gate_admission_sha256": self.request.sealed_gate_admission.sha256
            if self.request.sealed_gate_admission is not None
            else None,
        }


@runtime_checkable
class RealFiveArmExecutionAdapter(Protocol):
    """Boundary for a true simulator/TLE execution adapter.

    The adapter must return the current ``FiveArmEpisodeReceipt`` from the
    sibling receipt layer.  An old V0.20/V0.3 receipt, synthetic row, or
    untyped mapping is rejected by the runner.
    """

    identity: str
    is_test_fixture: bool

    def run_episode(
        self,
        *,
        arm: str,
        world: Any,
        policy: Any,
        resume_state: Mapping[str, object] | None,
    ) -> Any: ...

    def resume_state_for(self, arm: str) -> Mapping[str, object] | None: ...

    def restore_resume_states(self, states: Mapping[str, object]) -> None: ...


class V023RealSimulatorTleAdapter:
    """Thin production callback adapter; no simulator is imported here.

    ``run_episode`` must be the current physical implementation.  It is
    deliberately injected so the old provisional DROP_C3 runner cannot be
    mistaken for a current five-arm implementation.  Optional state callbacks
    are needed for deterministic checkpoint/resume.
    """

    identity = REAL_ADAPTER_IDENTITY
    is_test_fixture = False

    def __init__(
        self,
        *,
        run_episode_callback: Any,
        resume_state_for_callback: Any,
        restore_resume_states_callback: Any,
    ) -> None:
        if not callable(run_episode_callback):
            raise TypeError("run_episode_callback must be callable")
        if not callable(resume_state_for_callback) or not callable(restore_resume_states_callback):
            raise TypeError("resume callbacks are required for checkpoint/resume")
        self._run_episode_callback = run_episode_callback
        self._resume_state_for_callback = resume_state_for_callback
        self._restore_resume_states_callback = restore_resume_states_callback

    def run_episode(self, **kwargs: Any) -> Any:
        return self._run_episode_callback(**kwargs)

    def resume_state_for(self, arm: str) -> Mapping[str, object] | None:
        return self._resume_state_for_callback(arm)

    def restore_resume_states(self, states: Mapping[str, object]) -> None:
        self._restore_resume_states_callback(states)


def _write_once(path: Path, payload: object) -> None:
    """Atomically create one canonical JSON file without overwriting it."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise V023RealFiveArmError(f"refusing to overwrite existing output: {path}")
    data = _canonical_bytes(payload) + b"\n"
    temporary = path.with_name(f".{path.name}.tmp-{path.stat().st_ino if path.exists() else 'new'}")
    # The path is unique to this call and is removed on failure.  The target
    # itself is created with O_EXCL so concurrent writers cannot overwrite it.
    import os
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    except FileExistsError as error:
        raise V023RealFiveArmError(f"refusing to overwrite concurrently-created output: {path}") from error
    finally:
        temporary.unlink(missing_ok=True)


def _read_json(path: Path, *, field: str) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise V023RealFiveArmError(f"cannot read {field}: {path}") from error
    if not isinstance(payload, dict):
        raise V023RealFiveArmError(f"{field} must be a JSON object")
    return payload


def _read_checkpoint(path: Path) -> dict[str, object]:
    payload = _read_json(path, field="V0.23 real five-arm checkpoint")
    claimed = payload.pop("checkpoint_sha256", None)
    if _digest(claimed, field="checkpoint_sha256") != canonical_sha256(payload):
        raise V023RealFiveArmError("checkpoint canonical hash disagrees with bytes")
    if payload.get("schema") != CHECKPOINT_SCHEMA or payload.get("status") != STATUS:
        raise V023RealFiveArmError("checkpoint schema/status is not current V0.23")
    return payload


def _receipt_from_mapping(value: object) -> Any:
    if not isinstance(value, Mapping):
        raise V023RealFiveArmError("current five-arm checkpoint receipt is not an object")
    try:
        return _results.FiveArmEpisodeReceipt(**dict(value))
    except (TypeError, ValueError) as error:
        raise V023RealFiveArmError("current five-arm receipt fields are malformed") from error


class V023RealFiveArmEpisodeRunner:
    """Run exactly BASELINE/FULL/DROP_C1/DROP_C2/DROP_C3 on matched worlds."""

    def __init__(
        self,
        *,
        request: V023RealFiveArmRequest,
        adapter: RealFiveArmExecutionAdapter,
        allow_test_fixture: bool = False,
    ) -> None:
        self.admission = request.admit()
        if not isinstance(adapter, RealFiveArmExecutionAdapter):
            raise V023RealFiveArmError(
                "adapter must implement the real simulator/TLE execution protocol"
            )
        if adapter.identity != REAL_ADAPTER_IDENTITY:
            if not (
                allow_test_fixture
                and bool(getattr(adapter, "is_test_fixture", False))
                and adapter.identity == TEST_FIXTURE_ADAPTER_IDENTITY
            ):
                raise V023RealFiveArmError(
                    "only the current v023-real-simulator-tle adapter is admitted; "
                    "synthetic/legacy adapters are rejected"
                )
        if not callable(getattr(adapter, "resume_state_for", None)) or not callable(
            getattr(adapter, "restore_resume_states", None)
        ):
            raise V023RealFiveArmError(
                "real five-arm adapter must expose deterministic resume-state callbacks"
            )
        self.adapter = adapter
        self.binding = self.admission.request.binding
        self._policies = {policy.arm: policy for policy in self.binding.policies}

    def _adapter_states(self) -> dict[str, object]:
        return {
            arm: self.adapter.resume_state_for(arm)
            for arm in ARMS
        }

    def _checkpoint_payload(
        self,
        *,
        completed_episode: int,
        receipts: Sequence[Any],
    ) -> dict[str, object]:
        evaluation = _results.build_checkpoint_payload(
            binding=self.binding,
            receipts=receipts,
            through_episode=completed_episode,
        )
        payload: dict[str, object] = {
            "schema": CHECKPOINT_SCHEMA,
            "status": STATUS,
            "screen_id": self.admission.request.screen_id,
            "run_fingerprint": self.admission.run_fingerprint,
            "completed_episode": completed_episode,
            "planned_episodes": self.admission.request.episode_count,
            "checkpoint_every": CHECKPOINT_EVERY,
            "adapter_identity": self.adapter.identity,
            "evaluation_binding_sha256": self.binding.verify(),
            "receipts": [row.to_dict() for row in receipts],
            "evaluation": evaluation,
            "adapter_resume_states": self._adapter_states(),
            "test_split_opened": False,
            "learner_update": False,
            "episode_training": False,
            "scientific_decision": None,
        }
        payload["checkpoint_sha256"] = canonical_sha256(payload)
        return payload

    def _restore_checkpoint(
        self,
        path: Path,
    ) -> tuple[int, list[Any]]:
        payload = _read_checkpoint(path)
        if payload.get("screen_id") != self.admission.request.screen_id:
            raise V023RealFiveArmError("checkpoint screen_id disagrees with current request")
        if payload.get("run_fingerprint") != self.admission.run_fingerprint:
            raise V023RealFiveArmError("checkpoint run fingerprint disagrees with current request")
        if payload.get("evaluation_binding_sha256") != self.binding.verify():
            raise V023RealFiveArmError("checkpoint evaluation binding digest disagrees")
        if payload.get("adapter_identity") != self.adapter.identity:
            raise V023RealFiveArmError("checkpoint adapter identity disagrees")
        completed = payload.get("completed_episode")
        if type(completed) is not int or completed <= 0 or completed % CHECKPOINT_EVERY:
            raise V023RealFiveArmError("checkpoint completed_episode is not a 100 boundary")
        if completed > self.admission.request.episode_count:
            raise V023RealFiveArmError("checkpoint exceeds the admitted episode budget")
        for field in ("test_split_opened", "learner_update", "episode_training"):
            if payload.get(field) is not False:
                raise V023RealFiveArmError(f"checkpoint crossed forbidden boundary: {field}")
        rows_payload = payload.get("receipts")
        if not isinstance(rows_payload, list):
            raise V023RealFiveArmError("checkpoint has no current five-arm receipts")
        rows = [_receipt_from_mapping(row) for row in rows_payload]
        # The receipt layer verifies matched worlds, arm provenance, and exact
        # ratio-of-sums identities for the entire prefix.
        _results.build_checkpoint_payload(
            binding=self.binding,
            receipts=rows,
            through_episode=completed,
        )
        states = payload.get("adapter_resume_states")
        if not isinstance(states, Mapping) or any(arm not in states for arm in ARMS):
            raise V023RealFiveArmError("checkpoint lacks one resume state per arm")
        self.adapter.restore_resume_states(states)
        return completed, rows

    def run(
        self,
        *,
        output_dir: str | Path,
        resume_checkpoint: str | Path | None = None,
        stop_after: int | None = None,
    ) -> dict[str, object]:
        """Run a pre-admitted matched five-arm physical grid.

        ``stop_after`` is only a development/testing pause at a 100-episode
        checkpoint.  This method never opens a scientific result; final data
        remain ``COMPLETE_UNADJUDICATED`` until an external controller admits
        them.
        """

        output = Path(output_dir)
        if output.exists():
            if output.is_symlink() or not output.is_dir():
                raise V023RealFiveArmError(f"output is not a regular directory: {output}")
            if resume_checkpoint is None and any(output.iterdir()):
                raise V023RealFiveArmError(f"refusing to overwrite non-empty output: {output}")
            if resume_checkpoint is not None and (output / "result.json").exists():
                raise V023RealFiveArmError(f"refusing to resume a completed output: {output}")
        else:
            output.mkdir(parents=True, exist_ok=False)
        checkpoint_dir = output / "checkpoints"
        receipts: list[Any] = []
        start = 0
        if resume_checkpoint is not None:
            start, receipts = self._restore_checkpoint(Path(resume_checkpoint))

        target = self.admission.request.episode_count if stop_after is None else stop_after
        if type(target) is not int or target <= 0 or target > self.admission.request.episode_count:
            raise V023RealFiveArmError("stop_after is outside the admitted episode range")
        if target % CHECKPOINT_EVERY:
            raise V023RealFiveArmError("stop_after must land on a 100-episode checkpoint")
        if target < start:
            raise V023RealFiveArmError("stop_after precedes the resume checkpoint")

        worlds = {world.episode_index: world for world in self.binding.worlds}
        binding_sha = self.binding.verify()
        for episode in range(start + 1, target + 1):
            world = worlds[episode]
            group: list[Any] = []
            for arm in ARMS:
                try:
                    row = self.adapter.run_episode(
                        arm=arm,
                        world=world,
                        policy=self._policies[arm],
                        resume_state=self.adapter.resume_state_for(arm),
                    )
                except Exception as error:
                    raise V023RealFiveArmError(
                        f"current real adapter failed for {arm}/episode-{episode}: {error}"
                    ) from error
                if not isinstance(row, _results.FiveArmEpisodeReceipt):
                    raise V023RealFiveArmError(
                        f"{arm}/episode-{episode}: adapter did not return current "
                        "FiveArmEpisodeReceipt; legacy or synthetic receipt rejected"
                    )
                try:
                    row.verify(
                        world=world,
                        policy=self._policies[arm],
                        binding_sha256=binding_sha,
                    )
                except Exception as error:
                    raise V023RealFiveArmError(
                        f"{arm}/episode-{episode}: current receipt verification failed: {error}"
                    ) from error
                group.append(row)
                receipts.append(row)
            if tuple(row.arm for row in group) != ARMS:
                raise V023RealFiveArmError("one physical world did not receive exact five-arm coverage")
            if episode % CHECKPOINT_EVERY == 0:
                payload = self._checkpoint_payload(
                    completed_episode=episode,
                    receipts=receipts,
                )
                _write_once(checkpoint_dir / f"checkpoint-{episode:06d}.json", payload)

        if target < self.admission.request.episode_count:
            return {
                "schema": CHECKPOINT_SCHEMA,
                "status": STATUS,
                "screen_id": self.admission.request.screen_id,
                "run_fingerprint": self.admission.run_fingerprint,
                "completed_episode": target,
                "planned_episodes": self.admission.request.episode_count,
                "checkpoints": sorted(
                    str(path.relative_to(output)) for path in checkpoint_dir.glob("*.json")
                ),
                "scientific_decision": None,
            }

        evaluation = _results.build_result_payload(
            binding=self.binding,
            receipts=receipts,
        )
        result: dict[str, object] = {
            "schema": RESULT_SCHEMA,
            "status": "COMPLETE_UNADJUDICATED",
            "screen_id": self.admission.request.screen_id,
            "run_fingerprint": self.admission.run_fingerprint,
            "completed_episode": target,
            "planned_episodes": self.admission.request.episode_count,
            "checkpoint_every": CHECKPOINT_EVERY,
            "adapter_identity": self.adapter.identity,
            "evaluation_binding_sha256": binding_sha,
            "evaluation": evaluation,
            "scientific_decision": None,
            "claim_ceiling": "TRAIN_DEVELOPMENT_DESCRIPTIVE_ONLY_NO_EFFICACY_DECISION",
            "test_split_opened": False,
            "learner_update": False,
            "episode_training": False,
        }
        result["result_sha256"] = canonical_sha256(result)
        _write_once(output / "receipts.json", [row.to_dict() for row in receipts])
        _write_once(output / "result.json", result)
        return result


def load_request_manifest(path: str | Path) -> V023RealFiveArmRequest:
    """Load a fully explicit request manifest for preflight.

    The embedded ``evaluation_binding`` is intentionally required; a path to
    an unknown or archived binding is not enough to silently reconstruct a
    current run.
    """

    manifest_path = Path(path)
    payload = _read_json(manifest_path, field="V0.23 real five-arm manifest")
    if payload.get("schema") != MANIFEST_SCHEMA:
        raise V023RealFiveArmError("manifest schema is not current V0.23")
    base = manifest_path.parent
    raw_binding = payload.get("evaluation_binding")
    if not isinstance(raw_binding, Mapping):
        raise V023RealFiveArmError("manifest evaluation_binding object is required")
    source_plan = raw_binding.get("source_plan")
    if not isinstance(source_plan, Mapping):
        raise V023RealFiveArmError("manifest evaluation_binding.source_plan is required")
    raw_policies = raw_binding.get("policies")
    raw_worlds = raw_binding.get("worlds")
    if not isinstance(raw_policies, list) or not isinstance(raw_worlds, list):
        raise V023RealFiveArmError("manifest evaluation binding policies/worlds are required")
    try:
        policies = tuple(_binding.FrozenPolicyBinding(**dict(row)) for row in raw_policies)
        worlds = tuple(_binding.EvaluationWorldBinding(**dict(row)) for row in raw_worlds)
        binding = _binding.FiveArmEvaluationBinding(
            source_plan=dict(source_plan),
            policies=policies,
            worlds=worlds,
            evaluation_contract_sha256=raw_binding["evaluation_contract_sha256"],
            checkpoint_every=raw_binding.get("checkpoint_every", CHECKPOINT_EVERY),
            split=raw_binding.get("split", "TRAIN_DEVELOPMENT"),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise V023RealFiveArmError("manifest evaluation binding fields are malformed") from error
    raw_artifacts = payload.get("artifacts")
    if not isinstance(raw_artifacts, Mapping):
        raise V023RealFiveArmError("manifest artifacts object is required")
    policies_raw = raw_artifacts.get("policies")
    if not isinstance(policies_raw, Mapping):
        raise V023RealFiveArmError("manifest artifacts.policies object is required")
    policy_artifacts = {
        arm: _artifact_from_payload(policies_raw.get(arm), role=f"policy_artifacts.{arm}", base=base)
        for arm in ARMS
    }
    gate_value = raw_artifacts.get("sealed_gate_admission")
    gate = (
        None
        if gate_value is None
        else _artifact_from_payload(gate_value, role="sealed_gate_admission", base=base)
    )
    return V023RealFiveArmRequest(
        screen_id=payload.get("screen_id", ""),
        binding=binding,
        source_plan_artifact=_artifact_from_payload(raw_artifacts.get("source_plan"), role="source_plan", base=base),
        tle_archive=_artifact_from_payload(raw_artifacts.get("tle_archive"), role="tle_archive", base=base),
        q12_checkpoint=_artifact_from_payload(raw_artifacts.get("q12_checkpoint"), role="q12_checkpoint", base=base),
        c3_target_artifact=_artifact_from_payload(raw_artifacts.get("c3_target_artifact"), role="c3_target_artifact", base=base),
        policy_artifacts=policy_artifacts,
        sealed_gate_admission=gate,
        episode_count=payload.get("episode_count", 0),
        split=payload.get("split", "TRAIN_DEVELOPMENT"),
        checkpoint_every=payload.get("checkpoint_every", CHECKPOINT_EVERY),
    )


def _main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="V0.23 real five-arm preflight (no simulator launch)")
    subparsers = parser.add_subparsers(dest="command", required=True)
    preflight = subparsers.add_parser("preflight", help="verify artifacts and sealed episode admission")
    preflight.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.command == "preflight":
        try:
            request = load_request_manifest(args.manifest)
            admission = request.admit()
        except V023RealFiveArmError as error:
            print(str(error), file=sys.stderr)
            return 2
        print(json.dumps(admission.to_dict(), sort_keys=True, indent=2))
        return 0
    return 2


if __name__ == "__main__":  # pragma: no cover - command-line preflight only
    raise SystemExit(_main())


__all__ = [
    "ARMS",
    "ArtifactBinding",
    "CHECKPOINT_EVERY",
    "CURRENT_C3_VIEW_CONFIG_SHA256",
    "CURRENT_C3_VIEW_SCHEMA_SHA256",
    "CURRENT_GATE_CONTRACT_SHA256",
    "CURRENT_Q12_CHECKPOINT_SHA256",
    "MANIFEST_SCHEMA",
    "REAL_ADAPTER_IDENTITY",
    "RESULT_SCHEMA",
    "STATUS",
    "TEST_FIXTURE_ADAPTER_IDENTITY",
    "V023RealFiveArmAdmission",
    "V023RealFiveArmAdmissionError",
    "V023RealFiveArmEpisodeRunner",
    "V023RealFiveArmError",
    "V023RealFiveArmRequest",
    "V023RealSimulatorTleAdapter",
    "V023LCSRSPolicyError",
    "V023LCSRSThreeRoutePolicy",
    "canonical_sha256",
    "file_sha256",
    "load_d40_q12_background",
    "load_request_manifest",
]
