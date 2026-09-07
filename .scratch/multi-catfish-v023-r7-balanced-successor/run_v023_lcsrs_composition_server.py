#!/usr/bin/env python3
"""Draft-bound R7 composition seam with a blocked executable entrypoint.

Importing this module is inert.  It does not import the composition adapter,
the callback module, a simulator, TLE data, a learner, or TEST.  Those modules
remain available to the importable seam, while :func:`main` stops with
``R7_NO_LAUNCH`` before parsing a server invocation.
The production adapter owns source/fit authentication, Q3 evaluation, model
digests, and write-once sidecars; the runtime callback module owns only the
authenticated replay and complete physical evaluator seams.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Callable, Mapping, Sequence


HERE = Path(__file__).resolve().parent
ADAPTER_PATH = HERE / "v023_lcsrs_composition_adapter.py"
CLAIM_CEILING = (
    "TRAIN_DEVELOPMENT_SOURCE_AND_LEARNER_GATE_NO_TEST_NO_EPISODE_TRAINING_NO_EFFICACY"
)
V023_WORLDS = tuple(range(2026121801, 2026121809))
V023_STUDENT_SEEDS = (2026135201, 2026135202, 2026135203)
V023_ARMS = ("INFORMED", "MATCHED_PLACEBO")


class V023CompositionServerError(RuntimeError):
    """A deliberate composition-server boundary or receipt failed."""


@dataclass(frozen=True)
class CompositionServerSpec:
    """The complete identity supplied to one explicit server invocation."""

    held_out_world: int
    student_seed: int
    arm: str
    source_directory: Path
    source_manifest: Path
    preflight_manifest_sha256: str
    source_manifest_sha256: str
    fit_receipt: Path
    fit_receipt_sha256: str
    model_bytes_sha256: str | None
    model_sha256: str | None
    output: Path
    device: str
    runtime_module: Path
    runtime_factory: str
    contract_sha256: str | None = None

    @property
    def declared_hashes(self) -> Mapping[str, str | None]:
        return {
            "contract_sha256": self.contract_sha256,
            "preflight_manifest_sha256": self.preflight_manifest_sha256,
            "source_manifest_sha256": self.source_manifest_sha256,
            "fit_receipt_sha256": self.fit_receipt_sha256,
            "model_bytes_sha256": self.model_bytes_sha256,
            "model_sha256": self.model_sha256,
        }


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V023CompositionServerError(f"{field} is not a lowercase SHA-256")
    return value


def _file_sha256(path: Path, *, field: str) -> str:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise V023CompositionServerError(f"{field} is missing or is a symlink: {target}")
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V023CompositionServerError("value is not finite canonical JSON") from error


def _read_canonical_json(path: Path, *, field: str) -> dict[str, Any]:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise V023CompositionServerError(f"{field} is missing or is a symlink")
    raw = target.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V023CompositionServerError(f"{field} is not ASCII JSON") from error
    if not isinstance(payload, dict) or raw not in (
        _canonical_bytes(payload),
        _canonical_bytes(payload) + b"\n",
    ):
        raise V023CompositionServerError(f"{field} is not canonical JSON")
    return payload


def _safe_child(root: Path, child: Path, *, field: str) -> Path:
    root_resolved = Path(root).resolve()
    target = Path(child)
    if target.is_symlink() or not target.is_file():
        raise V023CompositionServerError(f"{field} is missing or is a symlink")
    resolved = target.resolve()
    if not resolved.is_relative_to(root_resolved):
        raise V023CompositionServerError(f"{field} escapes its root")
    return resolved


def _load_module(name: str, path: Path) -> ModuleType:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise V023CompositionServerError(f"module is missing or is a symlink: {target}")
    spec = importlib.util.spec_from_file_location(name, target)
    if spec is None or spec.loader is None:
        raise V023CompositionServerError(f"cannot load module: {target}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        raise V023CompositionServerError(f"module import failed: {target}") from error
    return module


def _lookup(source: object, names: Sequence[str]) -> object | None:
    for name in names:
        if isinstance(source, Mapping):
            value = source.get(name)
        else:
            value = getattr(source, name, None)
        if value is not None:
            return value
    return None


def _required_callable(source: object, names: Sequence[str], *, field: str) -> Callable[..., Any]:
    value = _lookup(source, names)
    if not callable(value):
        joined = ", ".join(names)
        raise V023CompositionServerError(
            f"{field} callback is not exposed ({joined})"
        )
    return value


def _call_factory(factory: Callable[..., Any], *, spec: CompositionServerSpec, adapter: ModuleType) -> object:
    """Call a runtime factory without guessing through callback exceptions."""

    try:
        signature = inspect.signature(factory)
    except (TypeError, ValueError) as error:
        raise V023CompositionServerError("runtime factory signature is unavailable") from error
    context: dict[str, object] = {"spec": spec, "adapter": adapter}
    parameters = list(signature.parameters.values())
    if any(parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in parameters):
        return factory(**context)
    if all(
        parameter.kind
        in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
        and (parameter.name in context or parameter.default is not inspect.Parameter.empty)
        for parameter in parameters
    ):
        kwargs = {
            parameter.name: context[parameter.name]
            for parameter in parameters
            if parameter.name in context
        }
        return factory(**kwargs)
    positional = [parameter for parameter in parameters if parameter.kind is inspect.Parameter.POSITIONAL_ONLY]
    if positional:
        if len(positional) > 2:
            raise V023CompositionServerError("runtime factory accepts too many positional arguments")
        return factory(spec, adapter) if len(positional) == 2 else factory(spec)
    raise V023CompositionServerError(
        "runtime factory must accept spec, adapter, or **kwargs"
    )


def _load_runtime(
    *,
    spec: CompositionServerSpec,
    adapter: ModuleType,
) -> object:
    callbacks = _load_module("mcrl_v023_composition_runtime", spec.runtime_module)
    factory = _lookup(callbacks, (spec.runtime_factory,)) if spec.runtime_factory else None
    if factory is None:
        # A callback module may itself be the factory object.  This fallback is
        # still explicit because replay/evaluation callbacks are checked below.
        return callbacks
    if not callable(factory):
        raise V023CompositionServerError(
            f"runtime factory is not callable: {spec.runtime_factory}"
        )
    return _call_factory(factory, spec=spec, adapter=adapter)


def _invoke_named(callback: Callable[..., Any], *, context: Mapping[str, object], field: str) -> object:
    """Invoke a seam using declared parameter names, never TypeError retries."""

    try:
        signature = inspect.signature(callback)
    except (TypeError, ValueError) as error:
        raise V023CompositionServerError(f"{field} signature is unavailable") from error
    parameters = list(signature.parameters.values())
    if any(parameter.kind is inspect.Parameter.VAR_POSITIONAL for parameter in parameters):
        raise V023CompositionServerError(f"{field} may not use variadic positional arguments")
    if any(parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in parameters):
        return callback(**dict(context))
    kwargs: dict[str, object] = {}
    missing: list[str] = []
    for parameter in parameters:
        if parameter.kind is inspect.Parameter.POSITIONAL_ONLY:
            raise V023CompositionServerError(
                f"{field} must expose named keyword parameters"
            )
        if parameter.name in context:
            kwargs[parameter.name] = context[parameter.name]
        elif parameter.default is inspect.Parameter.empty:
            missing.append(parameter.name)
    if missing:
        raise V023CompositionServerError(
            f"{field} has unsupported required parameters: {', '.join(missing)}"
        )
    return callback(**kwargs)


def _validate_source_manifest(spec: CompositionServerSpec, *, adapter: ModuleType) -> dict[str, Any]:
    source_root = Path(spec.source_directory)
    if source_root.is_symlink() or not source_root.is_dir():
        raise V023CompositionServerError("source directory is missing or is a symlink")
    manifest_input = Path(spec.source_manifest)
    if not manifest_input.is_absolute():
        manifest_input = source_root / manifest_input
    manifest = _safe_child(source_root, manifest_input, field="source manifest")
    payload = _read_canonical_json(manifest, field="source manifest")
    declared = _digest(payload.get("source_manifest_sha256"), field="source_manifest_sha256")
    unsigned_body = dict(payload)
    unsigned_body.pop("source_manifest_sha256", None)
    unsigned_body.pop("manifest_sha256", None)
    if hashlib.sha256(_canonical_bytes(unsigned_body)).hexdigest() != declared:
        raise V023CompositionServerError("source manifest body seal disagrees")
    manifest_seal = _digest(payload.get("manifest_sha256"), field="manifest_sha256")
    unsigned_manifest = dict(payload)
    unsigned_manifest.pop("manifest_sha256", None)
    if hashlib.sha256(_canonical_bytes(unsigned_manifest)).hexdigest() != manifest_seal:
        raise V023CompositionServerError("source manifest seal disagrees")
    if declared != spec.source_manifest_sha256:
        raise V023CompositionServerError("source manifest body hash disagrees with declaration")
    if payload.get("preflight_manifest_sha256") != spec.preflight_manifest_sha256:
        raise V023CompositionServerError("source manifest preflight hash disagrees")
    worlds = tuple(getattr(adapter, "V023_WORLDS", ()))
    if worlds and payload.get("worlds") != list(worlds):
        raise V023CompositionServerError("source manifest world panel drifted")
    expected_contract = spec.contract_sha256 or getattr(adapter, "V023_CONTRACT_SHA256", None)
    if expected_contract is not None and payload.get("contract_sha256") != expected_contract:
        raise V023CompositionServerError("source manifest contract hash disagrees")
    if payload.get("split") != "TRAIN_DEVELOPMENT":
        raise V023CompositionServerError("source manifest is not TRAIN_DEVELOPMENT")
    if (
        payload.get("test_split_opened") is not False
        or payload.get("episode_training") is not False
        or payload.get("learner_update") is not False
    ):
        raise V023CompositionServerError("source manifest crossed a closed boundary")
    return payload


def _validate_fit_identity(
    fitted: object,
    *,
    spec: CompositionServerSpec,
    adapter: ModuleType,
) -> None:
    expected_type = getattr(adapter, "AuthenticatedFitArtifact", None)
    if expected_type is not None and not isinstance(fitted, expected_type):
        raise V023CompositionServerError("fit authenticator returned an untyped artifact")
    checks = {
        "held_out_world": spec.held_out_world,
        "student_seed": spec.student_seed,
        "arm": spec.arm,
        "preflight_manifest_sha256": spec.preflight_manifest_sha256,
        "source_manifest_sha256": spec.source_manifest_sha256,
    }
    for field, expected in checks.items():
        if getattr(fitted, field, None) != expected:
            raise V023CompositionServerError(f"fit artifact {field} disagrees")
    if getattr(fitted, "fit_receipt_sha256", None) != spec.fit_receipt_sha256:
        raise V023CompositionServerError("fit receipt digest disagrees")
    for field, expected in (
        ("model_bytes_sha256", spec.model_bytes_sha256),
        ("model_sha256", spec.model_sha256),
    ):
        if expected is not None and getattr(fitted, field, None) != expected:
            raise V023CompositionServerError(f"fit artifact {field} disagrees")
    if getattr(fitted, "update_count", None) != 2000:
        raise V023CompositionServerError("fit artifact update count is not exactly 2000")


def _extract_declared_anchors(
    value: object,
    *,
    adapter: ModuleType,
    expected_world: int,
) -> tuple[object, ...]:
    anchors_value = value.get("anchors") if isinstance(value, Mapping) else value
    if isinstance(anchors_value, Mapping):
        anchors_value = anchors_value.get("anchors")
    if isinstance(anchors_value, (str, bytes)) or not isinstance(anchors_value, Sequence):
        raise V023CompositionServerError("source authenticator did not return an anchor sequence")
    expected_type = getattr(adapter, "DeclaredAnchor", None)
    anchors = tuple(anchors_value)
    if expected_type is not None and any(not isinstance(anchor, expected_type) for anchor in anchors):
        raise V023CompositionServerError("source authenticator returned an untyped anchor")
    if len(anchors) != 9:
        raise V023CompositionServerError("held-out source must contain exactly anchors 1..9")
    if tuple(getattr(anchor, "phase", None) for anchor in anchors) != tuple(range(1, 10)):
        raise V023CompositionServerError("held-out anchors are not ordered phases 1..9")
    if any(getattr(anchor, "world", None) != expected_world for anchor in anchors):
        raise V023CompositionServerError("held-out anchors disagree with requested world")
    return anchors


def _composition_success_payload(
    *,
    spec: CompositionServerSpec,
    output_sha256: str,
    anchor_count: int,
) -> dict[str, object]:
    return {
        "schema": "multi-catfish-mcrl-v023-lcsrs-composition-server-receipt-v1",
        "status": "PASS_COMPOSITION_EVIDENCE",
        "scientific_claim": False,
        "decision": None,
        "claim_ceiling": CLAIM_CEILING,
        "split": "TRAIN_DEVELOPMENT",
        "held_out_world": spec.held_out_world,
        "student_seed": spec.student_seed,
        "arm": spec.arm,
        "source_manifest_sha256": spec.source_manifest_sha256,
        "fit_receipt_sha256": spec.fit_receipt_sha256,
        "model_bytes_sha256": spec.model_bytes_sha256,
        "model_sha256": spec.model_sha256,
        "anchor_count": anchor_count,
        "output_sha256": output_sha256,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
    }


def run_composition_shard(
    spec: CompositionServerSpec,
    *,
    adapter_module: ModuleType | None = None,
) -> Mapping[str, object]:
    """Authenticate, compose, and persist one explicit held-out shard."""

    if spec.held_out_world not in V023_WORLDS:
        raise V023CompositionServerError("held-out world is outside the frozen panel")
    if spec.student_seed not in V023_STUDENT_SEEDS:
        raise V023CompositionServerError("student seed is outside the frozen panel")
    if spec.arm not in V023_ARMS:
        raise V023CompositionServerError("composition arm is outside the frozen panel")
    _digest(spec.preflight_manifest_sha256, field="preflight_manifest_sha256")
    _digest(spec.source_manifest_sha256, field="source_manifest_sha256")
    _digest(spec.fit_receipt_sha256, field="fit_receipt_sha256")
    if spec.model_bytes_sha256 is not None:
        _digest(spec.model_bytes_sha256, field="model_bytes_sha256")
    if spec.model_sha256 is not None:
        _digest(spec.model_sha256, field="model_sha256")
    if spec.contract_sha256 is not None:
        _digest(spec.contract_sha256, field="contract_sha256")
    if spec.output.exists() or spec.output.is_symlink():
        raise V023CompositionServerError(f"refusing to overwrite composition output: {spec.output}")
    adapter = adapter_module or _load_module("mcrl_v023_lcsrs_composition_adapter", ADAPTER_PATH)
    _validate_source_manifest(spec, adapter=adapter)
    source_manifest_path = Path(spec.source_manifest)
    if not source_manifest_path.is_absolute():
        source_manifest_path = Path(spec.source_directory) / source_manifest_path
    fit_receipt = _safe_child(spec.fit_receipt.parent, spec.fit_receipt, field="fit receipt")
    if _file_sha256(fit_receipt, field="fit receipt") != spec.fit_receipt_sha256:
        raise V023CompositionServerError("fit receipt byte hash disagrees with declaration")
    source_auth = _required_callable(
        adapter,
        ("authenticate_source_artifact",),
        field="source authentication",
    )
    fit_auth = _required_callable(
        adapter,
        ("authenticate_fit_artifact",),
        field="fit authentication",
    )
    q3_evaluator = _required_callable(
        adapter,
        ("default_q3_evaluator", "production_q3_evaluator", "q3_evaluator"),
        field="default Q3",
    )
    model_digestor = _required_callable(
        adapter,
        ("default_model_digestor",),
        field="model digest",
    )
    adapter_type = _lookup(adapter, ("V023CompositionAdapter",))
    spec_type = _lookup(adapter, ("CompositionShardSpec",))
    if not callable(adapter_type) or not callable(spec_type):
        raise V023CompositionServerError("composition adapter/spec type is not exposed")

    try:
        adapter_spec = spec_type(
            held_out_world=spec.held_out_world,
            student_seed=spec.student_seed,
            arm=spec.arm,
            source_directory=spec.source_directory,
            source_manifest=source_manifest_path,
            fit_receipt=fit_receipt,
            preflight_manifest_sha256=spec.preflight_manifest_sha256,
            source_manifest_sha256=spec.source_manifest_sha256,
            output=spec.output,
        )
        source = source_auth(adapter_spec)
        fitted = fit_auth(adapter_spec, device=spec.device)
    except Exception as error:
        raise V023CompositionServerError("composition artifact authentication failed") from error
    _validate_fit_identity(fitted, spec=spec, adapter=adapter)
    if getattr(source, "world", None) != spec.held_out_world:
        raise V023CompositionServerError("source artifact world disagrees")
    if getattr(source, "preflight_manifest_sha256", None) != spec.preflight_manifest_sha256:
        raise V023CompositionServerError("source artifact preflight digest disagrees")
    if getattr(source, "source_manifest_sha256", None) != spec.source_manifest_sha256:
        raise V023CompositionServerError("source artifact manifest digest disagrees")

    runtime = _load_runtime(spec=spec, adapter=adapter)
    replay_anchor = _required_callable(runtime, ("replay_anchor",), field="anchor replay")
    evaluate_physical = _required_callable(
        runtime, ("evaluate_physical",), field="physical evaluation"
    )
    try:
        worker = adapter_type(
            source_authenticator=lambda _spec: source,
            fit_authenticator=lambda _spec: fitted,
            anchor_replayer=replay_anchor,
            q3_evaluator=q3_evaluator,
            physical_evaluator=evaluate_physical,
            model_digestor=model_digestor,
        )
        artifacts = worker.compose_shard(adapter_spec)
    except Exception as error:
        raise V023CompositionServerError("composition shard failed closed") from error
    output_sha256 = _file_sha256(Path(artifacts.index_path), field="composition output")
    index = getattr(artifacts, "index", None)
    if not isinstance(index, Mapping) or (
        index.get("scientific_decision_opened") is not False
        or index.get("c3_decision") is not None
        or index.get("test_split_opened") is not False
        or index.get("episode_training") is not False
    ):
        raise V023CompositionServerError("composition output crossed a closed boundary")
    return _composition_success_payload(
        spec=spec,
        output_sha256=output_sha256,
        anchor_count=int(index.get("inference", {}).get("anchor_count", 0)),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--held-out-world",
        "--world",
        dest="held_out_world",
        type=int,
        required=True,
        help="one frozen held-out TRAIN world",
    )
    parser.add_argument(
        "--student-seed", "--seed", dest="student_seed", type=int, required=True
    )
    parser.add_argument("--arm", required=True, choices=("INFORMED", "MATCHED_PLACEBO"))
    parser.add_argument("--source-directory", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--preflight-sha256", "--preflight-manifest-sha256", required=True)
    parser.add_argument("--source-manifest-sha256", "--declared-source-manifest-sha256", required=True)
    parser.add_argument("--fit-receipt", "--fit-receipt-path", type=Path, required=True)
    parser.add_argument("--fit-receipt-sha256", required=True)
    parser.add_argument("--model-bytes-sha256")
    parser.add_argument("--model-sha256")
    parser.add_argument("--contract-sha256")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--runtime-module", "--callback-module", type=Path, required=True)
    parser.add_argument("--runtime-factory", default="build_runtime")
    return parser


def _spec_from_args(args: argparse.Namespace) -> CompositionServerSpec:
    return CompositionServerSpec(
        held_out_world=args.held_out_world,
        student_seed=args.student_seed,
        arm=args.arm,
        source_directory=args.source_directory,
        source_manifest=args.source_manifest,
        preflight_manifest_sha256=args.preflight_sha256,
        source_manifest_sha256=args.source_manifest_sha256,
        fit_receipt=args.fit_receipt,
        fit_receipt_sha256=args.fit_receipt_sha256,
        model_bytes_sha256=args.model_bytes_sha256,
        model_sha256=args.model_sha256,
        output=args.output,
        device=args.device,
        runtime_module=args.runtime_module,
        runtime_factory=args.runtime_factory,
        contract_sha256=args.contract_sha256,
    )


def main(argv: list[str] | None = None) -> int:
    """Parse an explicit server request; no work occurs on import."""

    del argv
    print(
        "R7_NO_LAUNCH: composition server is bound but not authorized",
        file=sys.stderr,
    )
    return 2

    # Unreachable until a separately authorized revision replaces the draft
    # guard and reseals the complete manifest.
    argv = None
    args = _parser().parse_args(argv)
    try:
        receipt = run_composition_shard(_spec_from_args(args))
    except V023CompositionServerError as error:
        print(f"COMPOSITION_ERROR: {error}", file=sys.stderr)
        return 2
    print("COMPOSITION_PASS: " + _canonical_bytes(receipt).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
