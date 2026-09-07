#!/usr/bin/env python3
"""Run a declarative consumer chain against real artifacts, offline and read-only.

Each callable is attempted in order.  Independent steps continue after a
failure; steps whose inputs are unavailable are BLOCKED.  Artifact roots are
hashed before and after the chain, and a Python audit hook rejects attempted
writes beneath them.  All permitted output is confined to a new scratch root.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import sys
import traceback
from types import ModuleType
from typing import Any, Iterable, Mapping, Sequence


sys.dont_write_bytecode = True

CLAIM_CEILING = "ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT"
SPEC_SCHEMA = "multi-catfish-v023-offline-realartifact-chain-spec-v1"
REPORT_SCHEMA = "multi-catfish-v023-offline-realartifact-dryrun-v1"


class DryRunError(RuntimeError):
    """The dry-run harness itself is invalid."""


class StepBlocked(RuntimeError):
    """A step cannot run because an input or implementation is unavailable."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii") + b"\n"


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root)
    except ValueError:
        return False
    return True


def _artifact_identity(path: Path) -> dict[str, Any]:
    resolved = path.resolve(strict=False)
    identity: dict[str, Any] = {"path": str(resolved)}
    if path.is_symlink():
        identity.update(status="INVALID_SYMLINK", sha256=None, files=[])
        return identity
    if not path.exists():
        identity.update(status="MISSING", sha256=None, files=[])
        return identity
    if path.is_file():
        digest = _sha256_file(path)
        identity.update(status="PRESENT", kind="file", sha256=digest, files=[{
            "path": str(resolved), "relative_path": path.name, "sha256": digest,
            "size": path.stat().st_size,
        }])
        return identity
    if not path.is_dir():
        identity.update(status="INVALID_TYPE", sha256=None, files=[])
        return identity
    files: list[dict[str, Any]] = []
    for candidate in sorted(path.rglob("*"), key=lambda item: item.as_posix()):
        if candidate.is_symlink():
            identity.update(status="INVALID_SYMLINK", sha256=None, files=files)
            identity["invalid_path"] = str(candidate)
            return identity
        if candidate.is_file():
            relative = candidate.relative_to(path).as_posix()
            files.append({
                "path": str(candidate.resolve()),
                "relative_path": relative,
                "sha256": _sha256_file(candidate),
                "size": candidate.stat().st_size,
            })
    tree_payload = [
        [entry["relative_path"], entry["sha256"], entry["size"]] for entry in files
    ]
    identity.update(
        status="PRESENT",
        kind="directory",
        sha256=hashlib.sha256(_canonical(tree_payload)).hexdigest(),
        files=files,
    )
    return identity


class _ReadOnlyGuard:
    """Reject Python-audited mutation attempts below artifact roots."""

    _MUTATION_EVENTS = {
        "os.remove", "os.rmdir", "os.rename", "os.replace", "os.mkdir",
        "os.chmod", "os.chown", "os.utime", "os.link", "os.symlink", "os.truncate",
    }

    def __init__(self, roots: Iterable[Path]) -> None:
        self.roots = tuple(path.resolve(strict=False) for path in roots if path.exists())

    def _protected(self, value: object) -> bool:
        if not isinstance(value, (str, bytes, os.PathLike)):
            return False
        try:
            path = Path(os.fsdecode(value))
            resolved = path.resolve(strict=False)
        except (OSError, TypeError, ValueError):
            return False
        return any(resolved == root or _inside(resolved, root) for root in self.roots)

    def __call__(self, event: str, args: tuple[Any, ...]) -> None:
        if event == "open" and args:
            mode = args[1] if len(args) > 1 else None
            flags = args[2] if len(args) > 2 else 0
            write_mode = isinstance(mode, str) and any(token in mode for token in "wax+")
            write_flags = isinstance(flags, int) and bool(
                flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
            )
            if (write_mode or write_flags) and self._protected(args[0]):
                raise PermissionError(f"engineering dry-run blocked write into input artifact: {args[0]}")
        elif event in self._MUTATION_EVENTS:
            targets = args[:2] if event in {"os.rename", "os.replace", "os.link", "os.symlink"} else args[:1]
            if any(self._protected(target) for target in targets):
                raise PermissionError(f"engineering dry-run blocked {event} in input artifact")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DryRunError(f"cannot read JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise DryRunError(f"JSON root must be an object: {path}")
    return value


def _artifact_overrides(values: Sequence[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        name, separator, path = value.partition("=")
        if not separator or not name or not path:
            raise DryRunError("--artifact must use NAME=PATH")
        if name in result:
            raise DryRunError(f"duplicate artifact override: {name}")
        result[name] = Path(path).resolve(strict=False)
    return result


class ChainRuntime:
    def __init__(
        self,
        *,
        repo: Path,
        output: Path,
        spec: Mapping[str, Any],
        artifacts: Mapping[str, Path],
        identities: Mapping[str, Mapping[str, Any]],
    ) -> None:
        self.repo = repo
        self.output = output
        self.spec = spec
        self.artifacts = dict(artifacts)
        self.identities = identities
        self.results: dict[str, Any] = {}
        self.modules: dict[str, ModuleType] = {}
        self.module_defs = spec.get("modules", {})
        if not isinstance(self.module_defs, dict):
            raise DryRunError("spec modules must be an object")
        python_paths = spec.get("python_paths", [])
        if not isinstance(python_paths, list) or not all(isinstance(value, str) for value in python_paths):
            raise DryRunError("python_paths must be a string list")
        for value in reversed(python_paths):
            path = self._repo_path(value)
            if str(path) not in sys.path:
                sys.path.insert(0, str(path))

    def _repo_path(self, value: str) -> Path:
        path = Path(value)
        return (path if path.is_absolute() else self.repo / path).resolve(strict=False)

    def module(self, key: str) -> ModuleType:
        if key in self.modules:
            return self.modules[key]
        definition = self.module_defs.get(key)
        if not isinstance(definition, dict):
            raise StepBlocked(f"module definition is absent: {key}")
        raw_path = definition.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            raise StepBlocked(f"module path is absent: {key}")
        path = self._repo_path(raw_path)
        if path.is_symlink() or not path.is_file():
            raise StepBlocked(f"module does not exist yet: {path}")
        natural_name = definition.get("name", path.stem)
        if not isinstance(natural_name, str) or not natural_name:
            raise DryRunError(f"module name is invalid: {key}")
        parent = str(path.parent)
        if parent not in sys.path:
            sys.path.insert(0, parent)
        existing = sys.modules.get(natural_name)
        if existing is not None:
            origin = getattr(existing, "__file__", None)
            if not isinstance(origin, str) or Path(origin).resolve() != path.resolve():
                raise StepBlocked(f"natural module name collision: {natural_name}")
            module = existing
        else:
            try:
                module = importlib.import_module(natural_name)
            except (ImportError, OSError) as error:
                raise StepBlocked(f"cannot import {natural_name} from {path}: {error}") from error
            origin = getattr(module, "__file__", None)
            if not isinstance(origin, str) or Path(origin).resolve() != path.resolve():
                raise StepBlocked(f"module resolved from unexpected origin: {natural_name}")
        self.modules[key] = module
        return module

    @staticmethod
    def _attribute(value: Any, dotted: str) -> Any:
        current = value
        for part in dotted.split("."):
            current = getattr(current, part)
        return current

    def resolve(self, value: Any) -> Any:
        if isinstance(value, list):
            return [self.resolve(item) for item in value]
        if not isinstance(value, dict):
            return value
        if set(value) == {"artifact"}:
            name = value["artifact"]
            if name not in self.artifacts:
                raise StepBlocked(f"artifact is not configured: {name}")
            if self.identities[name]["status"] != "PRESENT":
                raise StepBlocked(f"artifact is unavailable: {name} ({self.identities[name]['status']})")
            return self.artifacts[name]
        if set(value) == {"scratch"}:
            relative = Path(str(value["scratch"]))
            if relative.is_absolute() or ".." in relative.parts:
                raise DryRunError("scratch references must be safe relative paths")
            path = (self.output / relative).resolve(strict=False)
            if not _inside(path, self.output):
                raise DryRunError("scratch reference escapes output root")
            return path
        if set(value) == {"result"}:
            name = value["result"]
            if name not in self.results:
                raise StepBlocked(f"required prior result is unavailable: {name}")
            return self.results[name]
        if "path_join" in value and len(value) == 1:
            pieces = value["path_join"]
            if not isinstance(pieces, list) or not pieces:
                raise DryRunError("path_join requires a nonempty list")
            base = Path(self.resolve(pieces[0]))
            return base.joinpath(*(str(self.resolve(item)) for item in pieces[1:]))
        if "sha256" in value and len(value) == 1:
            path = Path(self.resolve(value["sha256"]))
            identity = _artifact_identity(path)
            if identity["status"] != "PRESENT":
                raise StepBlocked(f"cannot hash unavailable path: {path}")
            return identity["sha256"]
        if set(value) == {"module_constant"}:
            reference = value["module_constant"]
            if not isinstance(reference, dict):
                raise DryRunError("module_constant must be an object")
            return self._attribute(self.module(str(reference["module"])), str(reference["name"]))
        if set(value) == {"module_object"}:
            return self.module(str(value["module_object"]))
        if set(value) == {"literal"}:
            return value["literal"]
        if "attr" in value and "name" in value and len(value) == 2:
            return self._attribute(self.resolve(value["attr"]), str(value["name"]))
        if "item" in value and "key" in value and len(value) == 2:
            return self.resolve(value["item"])[self.resolve(value["key"])]
        return {key: self.resolve(item) for key, item in value.items()}

    def callable(self, definition: Mapping[str, Any]) -> Any:
        if "module" in definition:
            target = self.module(str(definition["module"]))
        elif "method_of" in definition:
            name = str(definition["method_of"])
            if name not in self.results:
                raise StepBlocked(f"method receiver is unavailable: {name}")
            target = self.results[name]
        else:
            raise DryRunError("callable requires module or method_of")
        name = definition.get("name")
        if not isinstance(name, str) or not name:
            raise DryRunError("callable name must be nonempty")
        try:
            function = self._attribute(target, name)
        except AttributeError as error:
            raise StepBlocked(f"callable does not exist yet: {name}") from error
        if not callable(function):
            raise StepBlocked(f"configured target is not callable: {name}")
        return function


def _referenced_artifacts(value: Any) -> set[str]:
    result: set[str] = set()
    if isinstance(value, dict):
        if set(value) == {"artifact"} and isinstance(value["artifact"], str):
            result.add(value["artifact"])
        for item in value.values():
            result.update(_referenced_artifacts(item))
    elif isinstance(value, list):
        for item in value:
            result.update(_referenced_artifacts(item))
    return result


@contextmanager
def _environment(runtime: ChainRuntime, values: Mapping[str, Any]):
    previous: dict[str, str | None] = {}
    try:
        for key, raw in values.items():
            if not isinstance(key, str) or not key:
                raise DryRunError("environment keys must be nonempty strings")
            previous[key] = os.environ.get(key)
            os.environ[key] = str(runtime.resolve(raw))
        yield
    finally:
        for key, old in previous.items():
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old


def _result_summary(value: Any) -> dict[str, Any]:
    summary = {"type": f"{type(value).__module__}.{type(value).__qualname__}"}
    if isinstance(value, Path):
        summary["path"] = str(value)
    if isinstance(value, Mapping) and isinstance(value.get("identities"), Mapping):
        summary["identities"] = value["identities"]
    return summary


def _result_input_identity(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping) and isinstance(value.get("identities"), Mapping):
        return {"status": "PRESENT", "identities": value["identities"]}
    if isinstance(value, Path):
        return _artifact_identity(value)
    return {"status": "PRESENT", "type": f"{type(value).__module__}.{type(value).__qualname__}"}


def _run_step(runtime: ChainRuntime, step: Mapping[str, Any]) -> dict[str, Any]:
    name = step.get("name")
    if not isinstance(name, str) or not name:
        raise DryRunError("each step needs a nonempty name")
    inputs = set(step.get("inputs", []))
    if not all(isinstance(value, str) for value in inputs):
        raise DryRunError(f"step {name} inputs must be artifact names")
    inputs.update(_referenced_artifacts(step.get("args", [])))
    inputs.update(_referenced_artifacts(step.get("kwargs", {})))
    identities = {key: runtime.identities[key] for key in sorted(inputs) if key in runtime.identities}
    input_results = step.get("input_results", [])
    if not isinstance(input_results, list) or not all(isinstance(item, str) for item in input_results):
        raise DryRunError(f"step {name} input_results must be a string list")
    for result_name in input_results:
        if result_name in runtime.results:
            identities[f"result:{result_name}"] = _result_input_identity(
                runtime.results[result_name]
            )
        else:
            identities[f"result:{result_name}"] = {"status": "UNAVAILABLE"}
    record: dict[str, Any] = {"name": name, "status": "FAIL", "input_identities": identities}
    try:
        condition = step.get("when")
        if condition is not None:
            if not isinstance(condition, dict) or set(condition) != {"spec_flag", "equals"}:
                raise DryRunError(f"step {name} when must contain spec_flag and equals")
            flags = runtime.spec.get("flags", {})
            if not isinstance(flags, dict):
                raise DryRunError("spec flags must be an object")
            flag_name = condition["spec_flag"]
            if not isinstance(flag_name, str) or not flag_name:
                raise DryRunError(f"step {name} spec_flag must be a nonempty string")
            actual = flags.get(flag_name)
            if actual != condition["equals"]:
                raise StepBlocked(
                    f"spec flag {flag_name} is {actual!r}; requires {condition['equals']!r}"
                )
        dependencies = step.get("depends_on", [])
        if not isinstance(dependencies, list) or not all(isinstance(item, str) for item in dependencies):
            raise DryRunError(f"step {name} depends_on must be a string list")
        unavailable = [item for item in dependencies if item not in runtime.results]
        if unavailable:
            raise StepBlocked(f"required prior result is unavailable: {', '.join(unavailable)}")
        function_spec = step.get("callable")
        if not isinstance(function_spec, dict):
            raise DryRunError(f"step {name} callable must be an object")
        function = runtime.callable(function_spec)
        args = runtime.resolve(step.get("args", []))
        kwargs = runtime.resolve(step.get("kwargs", {}))
        if not isinstance(args, list) or not isinstance(kwargs, dict):
            raise DryRunError(f"step {name} args/kwargs have invalid types")
        environment = step.get("env", {})
        if not isinstance(environment, dict):
            raise DryRunError(f"step {name} env must be an object")
        with _environment(runtime, environment):
            result = function(*args, **kwargs)
        runtime.results[name] = result
        record.update(status="PASS", result=_result_summary(result), exception=None)
    except StepBlocked as error:
        record.update(
            status="BLOCKED",
            exception={"type": type(error).__name__, "text": str(error)},
        )
    except Exception as error:
        record.update(
            status="FAIL",
            exception={
                "type": type(error).__name__,
                "text": str(error),
                "traceback": "".join(traceback.format_exception(error))[-12000:],
            },
        )
    return record


def _configure_artifacts(
    spec: Mapping[str, Any], repo: Path, overrides: Mapping[str, Path]
) -> dict[str, Path]:
    definitions = spec.get("artifacts", [])
    if not isinstance(definitions, list):
        raise DryRunError("spec artifacts must be a list")
    result: dict[str, Path] = {}
    for definition in definitions:
        if not isinstance(definition, dict) or not isinstance(definition.get("name"), str):
            raise DryRunError("each artifact definition needs a name")
        name = definition["name"]
        raw = overrides.get(name, definition.get("path"))
        if raw is None:
            result[name] = repo / f".__missing_artifact__/{name}"
        else:
            path = Path(raw)
            result[name] = (path if path.is_absolute() else repo / path).resolve(strict=False)
    unknown = set(overrides) - set(result)
    if unknown:
        raise DryRunError(f"unknown artifact override(s): {', '.join(sorted(unknown))}")
    return result


def run_chain(spec_path: Path, repo: Path, output: Path, overrides: Mapping[str, Path]) -> tuple[dict[str, Any], str]:
    spec = _load_json(spec_path)
    if spec.get("schema") != SPEC_SCHEMA:
        raise DryRunError(f"spec schema must be {SPEC_SCHEMA}")
    name = spec.get("name")
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_]+", name):
        raise DryRunError("spec name must contain only letters, digits, and underscores")
    artifacts = _configure_artifacts(spec, repo, overrides)
    for artifact in artifacts.values():
        if output == artifact or _inside(output, artifact):
            raise DryRunError("scratch output must be outside every input artifact root")
    identities_before = {key: _artifact_identity(path) for key, path in artifacts.items()}
    runtime = ChainRuntime(
        repo=repo, output=output, spec=spec, artifacts=artifacts, identities=identities_before
    )
    sys.addaudithook(_ReadOnlyGuard(artifacts.values()))
    steps_spec = spec.get("steps")
    if not isinstance(steps_spec, list):
        raise DryRunError("spec steps must be a list")
    steps = [_run_step(runtime, step) for step in steps_spec]
    identities_after = {key: _artifact_identity(path) for key, path in artifacts.items()}
    integrity = {
        key: {
            "status": "PASS" if identities_before[key] == identities_after[key] else "FAIL",
            "before": identities_before[key],
            "after": identities_after[key],
        }
        for key in artifacts
    }
    if any(item["status"] == "FAIL" for item in integrity.values()):
        steps.append({
            "name": "input_integrity_final",
            "status": "FAIL",
            "exception": {"type": "InputArtifactMutation", "text": "an input identity changed"},
            "input_identities": identities_after,
        })
    verdict = (
        "FAIL" if any(step["status"] == "FAIL" for step in steps)
        else "BLOCKED" if any(step["status"] == "BLOCKED" for step in steps)
        else "PASS"
    )
    report = {
        "schema": REPORT_SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "scientific_output": False,
        "name": name,
        "verdict": verdict,
        "spec": {"path": str(spec_path), "sha256": _sha256_file(spec_path)},
        "repo": str(repo),
        "scratch_output": str(output),
        "input_identities": identities_before,
        "input_integrity": integrity,
        "steps": steps,
        "summary": {
            "passed": sum(step["status"] == "PASS" for step in steps),
            "failed": sum(step["status"] == "FAIL" for step in steps),
            "blocked": sum(step["status"] == "BLOCKED" for step in steps),
        },
    }
    return report, name


def list_real_artifacts(path: Path) -> int:
    payload = _load_json(path)
    entries = payload.get("artifacts")
    if not isinstance(entries, list):
        raise DryRunError("artifact candidate JSON requires an artifacts list")
    report = []
    for entry in entries:
        if isinstance(entry, str):
            name, candidate = Path(entry).name, Path(entry)
        elif isinstance(entry, dict) and isinstance(entry.get("path"), str):
            name, candidate = str(entry.get("name", Path(entry["path"]).name)), Path(entry["path"])
        else:
            raise DryRunError("artifact candidate entries must be paths or name/path objects")
        identity = _artifact_identity(candidate)
        report.append({"name": name, **identity})
    print(json.dumps({
        "claim_ceiling": CLAIM_CEILING,
        "scientific_output": False,
        "source": str(path.resolve()),
        "artifacts": report,
    }, sort_keys=True, indent=2))
    return 0


def _write_report(output: Path, report: Mapping[str, Any]) -> None:
    path = output / "dryrun-report.json"
    if path.exists() or path.is_symlink():
        raise DryRunError(f"refusing to overwrite report: {path}")
    path.write_bytes(json.dumps(
        report, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False
    ).encode("ascii") + b"\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    parser.add_argument("--artifact", action="append", default=[], metavar="NAME=PATH")
    parser.add_argument("--list-real-artifacts", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.list_real_artifacts is not None:
        if args.spec is not None or args.output is not None or args.artifact:
            print("--list-real-artifacts cannot be combined with a chain run", file=sys.stderr)
            return 2
        try:
            return list_real_artifacts(args.list_real_artifacts)
        except Exception as error:
            print(f"REAL_ARTIFACT_LIST_ERROR: {type(error).__name__}: {error}", file=sys.stderr)
            return 2
    name = "UNKNOWN"
    verdict = "FAIL"
    try:
        if args.spec is None or args.output is None:
            raise DryRunError("--spec and --output are required for a chain run")
        repo = args.repo.resolve()
        output = args.output.resolve(strict=False)
        if output.exists() or output.is_symlink():
            raise DryRunError(f"scratch output already exists: {output}")
        output.mkdir(parents=True)
        report, name = run_chain(args.spec.resolve(), repo, output, _artifact_overrides(args.artifact))
        verdict = report["verdict"]
        _write_report(output, report)
    except Exception as error:
        print(f"DRYRUN_HARNESS_ERROR: {type(error).__name__}: {error}", file=sys.stderr)
        verdict = "FAIL"
    print(f"DRYRUN_{name}_{verdict}")
    return {"PASS": 0, "FAIL": 2, "BLOCKED": 3}[verdict]


if __name__ == "__main__":
    raise SystemExit(main())
