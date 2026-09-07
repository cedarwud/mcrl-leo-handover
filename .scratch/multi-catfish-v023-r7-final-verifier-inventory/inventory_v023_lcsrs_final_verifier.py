#!/usr/bin/env python3
"""Read-only, non-authoritative inventory of the frozen V0.23 R7 verifier."""
from __future__ import annotations
import argparse, ast
from contextlib import contextmanager
import hashlib, importlib.util, inspect, json, os
from pathlib import Path
import sys, textwrap
from types import ModuleType
from typing import Any, Callable, Mapping, Sequence
sys.dont_write_bytecode = True
ORIGINAL_SHA256 = "3cc573717f010d8b67ede027d05ef79f4c69497e9654d6766df50e88e9aa4717"
R3_SHA256 = "7d242eb2ca31835ba2471334b7ab90f8d68f4c817a367a5f3f2c72fb518fff2d"
PREFLIGHT_SHA256 = "9b08e3acc1d1d9b0cf506c3137f8e4013345ed8fb6f54c385a312ddb8570772a"
R7_RELATIVE = Path(".scratch/multi-catfish-v023-r7-launch-ready")
R3_RELATIVE = Path(".scratch/multi-catfish-v023-r7-domain-repair-r3")
ORIGINAL_NAME, R3_NAME = "verify_v023_lcsrs_final.py", "verify_v023_lcsrs_final_domain_repair.py"
WORLDS = tuple(range(2026121801, 2026121809))
SEEDS = tuple(range(2026135201, 2026135204))
ARMS = ("informed", "matched_placebo")
EXPECTED_LOADS = {"source": 8, "composition": 48}
FINAL_TRANSFORM_TARGETS = (
    ("_authenticate_launch_manifest", 5), ("_read_manifest", 9), ("_source_raw_identity", 2),
    ("_verify_composition_shard", 5), ("_validate_composition_arrays", 34), ("_validate_ratio_arrays", 3),
    ("_join_composition_source", 8), ("_fit_panel_metrics", 7), ("_composition_metrics", 1),
    ("_context_status", 7), ("verify_cross_arm_identity", 4), ("verify_v023_final_gate", 17))
SCIENTIFIC_TRANSFORM_TARGETS = (("verify_source_world_science", 23),
                                ("verify_source_panel_science", 2), ("verify_fit_science", 14))
FIT_TRANSFORM_TARGETS = (("verify_v023_fit_artifact", 12),)
class InventoryError(RuntimeError):
    """The inventory harness itself failed closed."""
def _sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise InventoryError(f"expected regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("ascii") + b"\n"
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise InventoryError("inventory is not canonical finite JSON") from error
def _verify_frozen_hashes(checkout: Path) -> dict[str, str]:
    original = checkout / R7_RELATIVE / ORIGINAL_NAME
    adapter = checkout / R3_RELATIVE / R3_NAME
    actual_original = _sha256(original)
    if actual_original != ORIGINAL_SHA256:
        raise InventoryError("frozen original final verifier digest drifted")
    actual_adapter = _sha256(adapter)
    if actual_adapter != R3_SHA256:
        raise InventoryError("frozen R3 adapter digest drifted")
    return {"original_verifier": actual_original, "r3_adapter": actual_adapter}
def _validated_output(run_root: Path, output: Path) -> Path:
    if not output.is_absolute():
        raise InventoryError("--output must be absolute")
    if output.exists() or output.is_symlink():
        raise InventoryError("--output already exists")
    run_resolved = run_root.resolve()
    output_resolved = output.resolve(strict=False)
    if output_resolved == run_resolved or output_resolved.is_relative_to(run_resolved):
        raise InventoryError("--output must not be inside --run-root")
    if output.parent.is_symlink() or not output.parent.is_dir():
        raise InventoryError("--output parent must be an existing regular directory")
    return output_resolved
class Recorder:
    def __init__(self) -> None:
        self.findings: list[dict[str, Any]] = []
        self.stage, self.shard = "decision", "panel"
    @contextmanager
    def scope(self, stage: str, shard: str):
        previous = self.stage, self.shard
        self.stage, self.shard = stage, shard
        try:
            yield
        finally:
            self.stage, self.shard = previous
    def primary(self, message: object, exception_type: str | None = None) -> None:
        finding = {"kind": "primary_verifier_message", "message": str(message),
                   "primary": True, "shard": self.shard, "stage": self.stage}
        if exception_type:
            finding["exception_type"] = exception_type
        self.findings.append(finding)
    def exception(self, error: BaseException) -> None:
        name = type(error).__name__
        self.findings.append({"exception_type": name, "kind": "cascade_exception",
                              "message": str(error), "primary": False,
                              "shard": self.shard, "stage": self.stage})
    def dictionary(self, values: Any, key_function: Callable[[Any], Any],
                   value_function: Callable[[Any], Any]) -> dict[Any, Any]:
        result: dict[Any, Any] = {}
        for value in values:
            try:
                result[key_function(value)] = value_function(value)
            except Exception as error:
                self.exception(error)
        return result
class _RecordRaisesAndIsolateLoops(ast.NodeTransformer):
    def __init__(self, exception_name: str) -> None:
        self.exception_name = exception_name
        self.replacements = 0
    def visit_Raise(self, node: ast.Raise) -> ast.AST:
        self.generic_visit(node)
        call = node.exc
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                and call.func.id == self.exception_name):
            return node
        message: ast.expr = call.args[0] if call.args else ast.Constant(self.exception_name)
        self.replacements += 1
        return ast.copy_location(ast.Expr(ast.Call(func=ast.Name(id="_inventory_record", ctx=ast.Load()),
            args=[ast.Call(func=ast.Name(id="str", ctx=ast.Load()), args=[message], keywords=[])],
            keywords=[])), node)
    @staticmethod
    def _isolated_body(body: list[ast.stmt]) -> list[ast.stmt]:
        handler = ast.ExceptHandler(type=ast.Name(id="Exception", ctx=ast.Load()),
            name="_inventory_loop_error", body=[ast.Expr(ast.Call(
                func=ast.Name(id="_inventory_exception", ctx=ast.Load()),
                args=[ast.Name(id="_inventory_loop_error", ctx=ast.Load())], keywords=[]))])
        return [ast.Try(body=body, handlers=[handler], orelse=[], finalbody=[])]
    def visit_For(self, node: ast.For) -> ast.AST:
        node = self.generic_visit(node); node.body = self._isolated_body(node.body)
        return node
    def visit_While(self, node: ast.While) -> ast.AST:
        node = self.generic_visit(node); node.body = self._isolated_body(node.body)
        return node
    def visit_DictComp(self, node: ast.DictComp) -> ast.AST:
        node = self.generic_visit(node)
        if len(node.generators) != 1:
            return node
        generator = node.generators[0]
        if generator.ifs or generator.is_async or not isinstance(generator.target, ast.Name):
            return node
        arguments = ast.arguments(posonlyargs=[], args=[ast.arg(arg=generator.target.id)],
            vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[])
        return ast.copy_location(ast.Call(func=ast.Name(id="_inventory_dict_comp", ctx=ast.Load()),
            args=[generator.iter, ast.Lambda(arguments, node.key), ast.Lambda(arguments, node.value)],
            keywords=[]), node)
def _transform_function(module: ModuleType, function_name: str, recorder: Recorder, *,
    exception_name: str = "V023FinalVerificationError", expected_sites: int | None = None,
    module_label: str = "synthetic") -> dict[str, Any]:
    function = getattr(module, function_name, None)
    if not callable(function):
        raise InventoryError(f"validator is missing: {module_label}.{function_name}")
    try:
        source = textwrap.dedent(inspect.getsource(function))
        tree = ast.parse(source, filename=inspect.getsourcefile(function) or "<inventory>")
    except (OSError, TypeError, SyntaxError) as error:
        raise InventoryError(f"cannot inspect validator: {function_name}") from error
    transformer = _RecordRaisesAndIsolateLoops(exception_name)
    tree = transformer.visit(tree)
    if expected_sites is not None and transformer.replacements != expected_sites:
        raise InventoryError(
            f"raise-site count drifted for {function_name}: "
            f"{transformer.replacements} != {expected_sites}"
        )
    ast.fix_missing_locations(tree)
    module.__dict__["_inventory_record"] = recorder.primary
    module.__dict__["_inventory_exception"] = recorder.exception
    module.__dict__["_inventory_dict_comp"] = recorder.dictionary
    exec(compile(tree, inspect.getsourcefile(function) or "<inventory>", "exec"), module.__dict__)
    return {"function": function_name, "module": module_label,
            "raise_sites_rewritten": transformer.replacements,
            "rewrite": "verifier raise -> recorder; loop/dict-comprehension isolation"}
def _run_isolated(
    recorder: Recorder, stage: str, shard: str, function: Callable[..., Any],
    *args: Any, **kwargs: Any,
) -> Any:
    with recorder.scope(stage, shard):
        try:
            return function(*args, **kwargs)
        except Exception as error:
            recorder.exception(error)
            return None
def _memoized(recorder: Recorder, cache: dict[Any, Any], function: Callable[..., Any],
    key_and_context: Callable[..., tuple[Any, str, str]], *,
    retry_on_error: bool = False) -> Callable[..., Any]:
    def call(*args: Any, **kwargs: Any) -> Any:
        key, stage, shard = key_and_context(*args, **kwargs)
        with recorder.scope(stage, shard):
            if key in cache:
                result = cache[key]
            else:
                try:
                    result = function(*args, **kwargs)
                    cache[key] = result
                except Exception as error:
                    recorder.exception(error)
                    result = None
                    if not retry_on_error:
                        cache[key] = None
        recorder.stage, recorder.shard = stage, shard
        return result
    return call
def _panel_paths(run_root: Path) -> tuple[list[Path], list[Path], list[Path]]:
    sources = [run_root / "source" / f"world-{world}.json" for world in WORLDS]
    fits, compositions = [], []
    for world in WORLDS:
        for seed in SEEDS:
            for arm in ARMS:
                relative = Path(f"world-{world}") / f"seed-{seed}" / f"{arm}.json"
                fits.append(run_root / "fit" / relative)
                compositions.append(run_root / "composition" / relative)
    return sources, fits, compositions
def _identity(path: Path, stage: str) -> str:
    if stage == "source":
        return f"world={path.stem.removeprefix('world-')} path={path}"
    return (
        f"world={path.parents[1].name.removeprefix('world-')} "
        f"seed={path.parent.name.removeprefix('seed-')} arm={path.stem} path={path}"
    )
def _load_frozen(checkout: Path) -> tuple[ModuleType, ModuleType]:
    _verify_frozen_hashes(checkout)
    adapter_path = checkout / R3_RELATIVE / R3_NAME
    spec = importlib.util.spec_from_file_location("v023_r7_inventory_r3_adapter", adapter_path)
    if spec is None or spec.loader is None:
        raise InventoryError("cannot load frozen R3 adapter")
    adapter = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = adapter
    spec.loader.exec_module(adapter)
    _verify_frozen_hashes(checkout)
    frozen = adapter._load_original()
    return adapter, frozen
def _load_r4_adapter(path: Path) -> tuple[ModuleType, str]:
    candidate = Path(path)
    if candidate.is_symlink() or not candidate.is_file():
        raise InventoryError("optional R4 adapter must be a regular file")
    target = candidate.resolve()
    digest = _sha256(target)
    spec = importlib.util.spec_from_file_location("v023_r7_inventory_r4_adapter", target)
    if spec is None or spec.loader is None:
        raise InventoryError("cannot load optional R4 adapter")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    if _sha256(target) != digest:
        raise InventoryError("optional R4 adapter changed while loading")
    if getattr(module, "R3_ADAPTER_SHA256", None) != R3_SHA256:
        raise InventoryError("optional R4 adapter does not bind the frozen R3 adapter")
    for name in (
        "_install_pair_key_reconstruction",
        "_install_c2_diagnostic_normalization",
        "_install_q2_delta_precision",
    ):
        if not callable(getattr(module, name, None)):
            raise InventoryError(f"optional R4 adapter install is missing: {name}")
    return module, digest
@contextmanager
def _patched(module: ModuleType, replacements: Mapping[str, Any]):
    originals = {name: getattr(module, name) for name in replacements}
    for name, value in replacements.items():
        setattr(module, name, value)
    try:
        yield
    finally:
        for name, value in originals.items():
            setattr(module, name, value)
def _write_report(output: Path, report: Mapping[str, Any]) -> None:
    data = _canonical_bytes(report)
    output.mkdir(mode=0o755)
    inventory = output / "inventory.json"
    descriptor = os.open(inventory, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)
    digest = hashlib.sha256(data).hexdigest()
    sidecar = output / "inventory.json.sha256"
    descriptor = os.open(sidecar, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(f"{digest}  inventory.json\n".encode("ascii"))
def run_inventory(*, run_root: Path, checkout: Path, output: Path,
                  adapter_r4: Path | None = None) -> dict[str, Any]:
    if run_root.is_symlink() or not run_root.is_dir():
        raise InventoryError("--run-root must be an existing regular directory")
    if checkout.is_symlink() or not checkout.is_dir():
        raise InventoryError("--checkout must be an existing regular directory")
    run_root, checkout = run_root.resolve(), checkout.resolve()
    output = _validated_output(run_root, output)
    frozen_hashes = _verify_frozen_hashes(checkout)
    sources, fits, compositions = _panel_paths(run_root)
    source_manifest = run_root / "source-manifest.json"
    launch_manifest = checkout / R7_RELATIVE / "R7-PREFLIGHT-MANIFEST.json"
    launch_digest = checkout / R7_RELATIVE / "R7-PREFLIGHT-MANIFEST.sha256"
    recorder, transformed = Recorder(), []
    original_sys_path = list(sys.path)
    sys.path.insert(0, str((checkout / "src").resolve()))
    adapter = frozen = None
    original_loader = original_pair = None
    r4_adapter = None
    r4_adapter_sha: str | None = None
    r4_original_join = r4_original_diagnostic = r4_original_context = None
    r4_q2_delta_state: dict[str, int] | None = None
    r4_pair_state: dict[str, Any] | None = None
    r4_diagnostic_state: dict[str, int] | None = None
    counts = {"source": 0, "composition": 0}
    first_arrays: dict[str, list[str]] = {"source": [], "composition": []}
    try:
        adapter, frozen = _load_frozen(checkout)
        original_loader, counts = adapter._install_domain_dispatch(frozen)
        original_pair = adapter._install_pair_profile_broadcast(frozen)
        dispatch = frozen._load_npz
        def observed_load(root: Path, binding: Mapping[str, Any], *, label: str):
            arrays = dispatch(root, binding, label=label)
            kind = "source" if binding.get("schema") == adapter.SOURCE_ARRAY_SCHEMA else "composition"
            if not first_arrays[kind]:
                first_arrays[kind] = sorted(arrays)
            return arrays
        with adapter._temporary_import_path((checkout / R7_RELATIVE).resolve()):
            scientific = frozen._load_independent(
                frozen._SCIENTIFIC_PATH, "v023_inventory_scientific",
            )
            fit_independent = frozen._load_independent(
                frozen._FIT_INDEPENDENT_PATH, "v023_inventory_fit_independent",
            )
            # R4's third correction rebuilds ``_context_status`` from the frozen source;
            # a prior harness AST rewrite of the same function makes that target
            # non-unique, so with an R4 adapter the function keeps its frozen raise
            # sites and its failures are captured by the memoized isolation wrapper.
            final_targets = tuple(
                target for target in FINAL_TRANSFORM_TARGETS
                if not (adapter_r4 is not None and target[0] == "_context_status")
            )
            for name, sites in final_targets:
                transformed.append(_transform_function(
                    frozen, name, recorder, expected_sites=sites,
                    module_label="frozen_final",
                ))
            for name, sites in SCIENTIFIC_TRANSFORM_TARGETS:
                transformed.append(_transform_function(
                    scientific, name, recorder,
                    exception_name="V023ScientificVerificationError",
                    expected_sites=sites, module_label="frozen_scientific",
                ))
            for name, sites in FIT_TRANSFORM_TARGETS:
                transformed.append(_transform_function(
                    fit_independent, name, recorder,
                    exception_name="V023FitIndependentVerificationError",
                    expected_sites=sites, module_label="frozen_fit_independent",
                ))
            if adapter_r4 is not None:
                r4_adapter, r4_adapter_sha = _load_r4_adapter(adapter_r4)
                r4_original_join, r4_pair_state = (
                    r4_adapter._install_pair_key_reconstruction(frozen)
                )
                r4_original_diagnostic, r4_diagnostic_state = (
                    r4_adapter._install_c2_diagnostic_normalization(frozen)
                )
                # Correction 3 must be installed before the memoized _context_status
                # wrapper below captures frozen._context_status.
                r4_original_context, r4_q2_delta_state = (
                    r4_adapter._install_q2_delta_precision(frozen)
                )
            caches: dict[str, dict[Any, Any]] = {
                name: {} for name in (
                    "launch", "manifest", "source_raw", "source", "source_panel",
                    "fit", "fit_science", "fit_metrics", "composition", "join",
                    "cross", "composition_metrics", "context",
                )
            }
            path_key = lambda path, *_args, **_kwargs: Path(path).resolve()
            original_independent = frozen._load_independent
            original_json = frozen._read_json
            def cached_independent(path: Path, name: str):
                resolved = Path(path).resolve()
                if resolved == Path(frozen._SCIENTIFIC_PATH).resolve():
                    return scientific
                if resolved == Path(frozen._FIT_INDEPENDENT_PATH).resolve():
                    return fit_independent
                return original_independent(path, name)
            def observed_json(path: Path, *, label: str):
                target = Path(path)
                if label.startswith("source ") and target.name.startswith("world-"):
                    context = "source", _identity(target, "source")
                elif label.startswith("fit ") and target.parent.name.startswith("seed-"):
                    context = "fit", _identity(target, "fit")
                else:
                    return original_json(path, label=label)
                with recorder.scope(*context):
                    return original_json(path, label=label)
            final_replacements = {
                "_load_npz": observed_load,
                "_read_json": observed_json,
                "_load_independent": cached_independent,
                "_authenticate_launch_manifest": _memoized(
                    recorder, caches["launch"], frozen._authenticate_launch_manifest,
                    lambda manifest, digest: ("one", "decision", str(manifest)),
                ),
                "_read_manifest": _memoized(
                    recorder, caches["manifest"], frozen._read_manifest,
                    lambda path: (path_key(path), "source", str(path)),
                ),
                "_source_raw_identity": _memoized(
                    recorder, caches["source_raw"], frozen._source_raw_identity,
                    lambda paths: ("panel", "source", str(run_root / "source")),
                ),
                "_verify_composition_shard": _memoized(
                    recorder, caches["composition"], frozen._verify_composition_shard,
                    lambda path: (path_key(path), "composition", _identity(Path(path), "composition")),
                ),
                "_join_composition_source": _memoized(
                    recorder, caches["join"], frozen._join_composition_source,
                    lambda shard, source: (
                        Path(shard.path).resolve(), "identity_join",
                        _identity(Path(shard.path), "composition"),
                    ),
                ),
                "_fit_panel_metrics": _memoized(
                    recorder, caches["fit_metrics"], frozen._fit_panel_metrics,
                    lambda reports: ("panel", "fit", str(run_root / "fit")),
                    retry_on_error=True,
                ),
                "verify_cross_arm_identity": _memoized(
                    recorder, caches["cross"], frozen.verify_cross_arm_identity,
                    lambda informed, placebo: (
                        (informed.world, informed.seed), "identity_join",
                        f"world={informed.world} seed={informed.seed} cross-arm",
                    ),
                ),
                "_composition_metrics": _memoized(
                    recorder, caches["composition_metrics"], frozen._composition_metrics,
                    lambda shards: ("panel", "composition", str(run_root / "composition")),
                    retry_on_error=True,
                ),
                "_context_status": _memoized(
                    recorder, caches["context"], frozen._context_status,
                    lambda source: ("panel", "decision", str(run_root / "source")),
                    retry_on_error=True,
                ),
            }
            scientific_replacements = {
                "verify_source_world_science": _memoized(
                    recorder, caches["source"], scientific.verify_source_world_science,
                    lambda path: (path_key(path), "source", _identity(Path(path), "source")),
                ),
                "verify_source_panel_science": _memoized(
                    recorder, caches["source_panel"], scientific.verify_source_panel_science,
                    lambda paths: ("panel", "source", str(run_root / "source")),
                    retry_on_error=True,
                ),
                "verify_fit_science": _memoized(
                    recorder, caches["fit_science"], scientific.verify_fit_science,
                    lambda path: (path_key(path), "fit", _identity(Path(path), "fit")),
                ),
            }
            fit_replacements = {
                "verify_v023_fit_artifact": _memoized(
                    recorder, caches["fit"], fit_independent.verify_v023_fit_artifact,
                    lambda path, **kwargs: (path_key(path), "fit", _identity(Path(path), "fit")),
                ),
            }
            with _patched(frozen, final_replacements), _patched(
                scientific, scientific_replacements,
            ), _patched(fit_independent, fit_replacements):
                _run_isolated(
                    recorder, "decision", "frozen top-level verifier", frozen.verify_v023_final_gate,
                    source_paths=sources, fit_paths=fits, composition_paths=compositions,
                    source_manifest_path=source_manifest,
                    expected_preflight_manifest_sha256=PREFLIGHT_SHA256,
                    launch_manifest_path=launch_manifest,
                    launch_manifest_digest_path=launch_digest,
                    raise_on_invalid=True,
                )
                frozen._authenticate_launch_manifest(launch_manifest, launch_digest)
                manifest_result = frozen._read_manifest(source_manifest)
                source_raw = frozen._source_raw_identity(tuple(sources))
                source_raw = source_raw if isinstance(source_raw, dict) else {}
                for path in sources:
                    scientific.verify_source_world_science(path)
                scientific.verify_source_panel_science(tuple(sources))
                manifest_sha = manifest_result[1] if isinstance(manifest_result, tuple) else None
                for path in fits:
                    fit_independent.verify_v023_fit_artifact(
                        path, source_manifest_path=source_manifest,
                        source_index_paths=sources,
                        expected_source_manifest_sha256=manifest_sha,
                        preflight_manifest_sha256=PREFLIGHT_SHA256,
                    )
                    scientific.verify_fit_science(path)
                frozen._fit_panel_metrics([
                    caches["fit_science"].get(path.resolve()) for path in fits
                ])
                for path in compositions:
                    frozen._verify_composition_shard(path)
                comp_values = [
                    caches["composition"].get(path.resolve()) for path in compositions
                ]
                for shard in (value for value in comp_values if value is not None):
                    if shard.world in source_raw:
                        frozen._join_composition_source(shard, source_raw[shard.world])
                comp_by_key = {
                    (value.world, value.seed, value.arm): value
                    for value in comp_values if value is not None
                }
                for world in WORLDS:
                    for seed in SEEDS:
                        pair = (world, seed, "INFORMED"), (world, seed, "MATCHED_PLACEBO")
                        if all(key in comp_by_key for key in pair):
                            frozen.verify_cross_arm_identity(
                                comp_by_key[pair[0]], comp_by_key[pair[1]],
                            )
                frozen._composition_metrics(comp_by_key)
                frozen._context_status(source_raw)
    finally:
        if frozen is not None and r4_original_context is not None:
            frozen._context_status = r4_original_context
        if frozen is not None and r4_original_diagnostic is not None:
            frozen._diagnostic_rows = r4_original_diagnostic
        if frozen is not None and r4_original_join is not None:
            frozen._join_composition_source = r4_original_join
        if frozen is not None and original_loader is not None:
            frozen._load_npz = original_loader
        if frozen is not None and original_pair is not None:
            frozen._validate_pair_arrays = original_pair
        sys.path[:] = original_sys_path
    if counts != EXPECTED_LOADS:
        with recorder.scope("decision", "NPZ dispatch"):
            recorder.primary(f"NPZ domain dispatch count drifted: {counts}")
    if _verify_frozen_hashes(checkout) != frozen_hashes:
        raise InventoryError("frozen verifier hashes changed during inventory")
    report = {
        "schema": "multi-catfish-v023-r7-final-verifier-inventory-v1",
        "status": "INVENTORY_COMPLETE", "verdict": None, "verdict_authority": False,
        "purpose": "read-only diagnostic inventory; not a repair and not a seal",
        "run_root": str(run_root), "checkout": str(checkout),
        "panel": {"worlds": list(WORLDS), "seeds": list(SEEDS), "arms": list(ARMS),
                  "source": len(sources), "fit": len(fits), "composition": len(compositions)},
        "frozen_sha256": frozen_hashes,
        "transformed_functions": transformed,
        "npz_dispatch": {"actual": dict(counts), "expected": EXPECTED_LOADS,
                         "matches_expected": counts == EXPECTED_LOADS},
        "identity_join_array_names": {
            "first_source_npz": first_arrays["source"],
            "first_composition_npz": first_arrays["composition"],
        },
        "findings": recorder.findings,
        "top_level_run": {"invocations": 1, "verdict_authority": False},
        "writes_limited_to_output": ["inventory.json", "inventory.json.sha256"],
    }
    if adapter_r4 is not None:
        if r4_adapter_sha is None or _sha256(Path(adapter_r4).resolve()) != r4_adapter_sha:
            raise InventoryError("optional R4 adapter hash changed during inventory")
        report["adapter_r4"] = {
            "path": str(Path(adapter_r4).resolve()),
            "sha256": r4_adapter_sha,
            "pair_key_reconstruction": r4_pair_state,
            "c2_diagnostic_normalization": r4_diagnostic_state,
            "q2_delta_precision": r4_q2_delta_state,
            "context_status_record_transform_skipped": True,
        }
    _write_report(output, report)
    return report
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--checkout", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--adapter-r4", type=Path)
    return parser
def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = run_inventory(run_root=args.run_root, checkout=args.checkout,
                               output=args.output, adapter_r4=args.adapter_r4)
    except Exception as error:
        print(f"V023_R7_FINAL_VERIFIER_INVENTORY_FAILED: {error}", file=sys.stderr)
        return 2
    print(f"V023_R7_FINAL_VERIFIER_INVENTORY_COMPLETE findings={len(report['findings'])}")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
