#!/usr/bin/env python3
"""Static producer/consumer contract scanner for the unfrozen engineering lane.

The scanner parses Python source with :mod:`ast`; it never imports either
module.  A JSON spec selects writer/reader callables and may bind differently
named constants to one semantic item.  Results are diagnostic only.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence


CLAIM_CEILING = "ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT"
REPORT_SCHEMA = "multi-catfish-v023-engineering-contract-scan-v1"
SPEC_SCHEMA = "multi-catfish-v023-engineering-contract-spec-v1"
STATUSES = ("MATCH", "MISMATCH", "CONSUMER_ONLY", "PRODUCER_ONLY")


class ContractScanError(RuntimeError):
    """The scanner or its configuration is invalid."""


@dataclass(frozen=True)
class Occurrence:
    value: Any
    line: int
    context: str

    def payload(self, path: Path) -> dict[str, Any]:
        return {
            "value": _jsonable(self.value),
            "file": str(path),
            "line": self.line,
            "location": f"{path}:{self.line}",
            "context": self.context,
        }


@dataclass
class Facts:
    path: Path
    sha256: str
    constants: dict[str, Occurrence] = field(default_factory=dict)
    tokens: dict[str, list[Occurrence]] = field(default_factory=dict)
    fields: dict[str, list[Occurrence]] = field(default_factory=dict)
    npz_arrays: dict[str, list[Occurrence]] = field(default_factory=dict)
    dtypes: dict[str, list[Occurrence]] = field(default_factory=dict)
    shapes: dict[str, list[Occurrence]] = field(default_factory=dict)
    layouts: dict[str, list[Occurrence]] = field(default_factory=dict)
    numerics: dict[str, list[Occurrence]] = field(default_factory=dict)
    functions_found: list[str] = field(default_factory=list)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _jsonable(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


def _literal(node: ast.AST) -> Any:
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError):
        return None


def _name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def _dtype_name(node: ast.AST | None) -> str | None:
    if node is None:
        return None
    value = _name(node)
    if value:
        return value.removeprefix("numpy.").removeprefix("np.")
    literal = _literal(node)
    return str(literal) if literal is not None else None


def _shape_value(node: ast.AST) -> Any:
    value = _literal(node)
    if isinstance(value, (int, tuple, list)):
        return value
    return None


def _call_name(node: ast.Call) -> str:
    return _name(node.func) or ""


def _subscript_string(node: ast.Subscript) -> str | None:
    value = _literal(node.slice)
    return value if isinstance(value, str) else None


def _constant_category(name: str) -> str | None:
    upper = name.upper()
    if "CLAIM" in upper and "CEILING" in upper:
        return "token.claim_ceiling"
    if "SCHEMA" in upper:
        return "token.schema"
    if "STATUS" in upper:
        return "token.status"
    if "MODE" in upper:
        return "token.mode"
    if "ROUTE" in upper:
        return "token.route"
    if "UNIT" in upper:
        return "token.unit"
    return None


def _flatten_strings(value: Any) -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield "", value
    elif isinstance(value, (tuple, list, set, frozenset)):
        for index, item in enumerate(value):
            for suffix, text in _flatten_strings(item):
                yield f"[{index}]{suffix}", text
    elif isinstance(value, dict):
        for key, item in value.items():
            for suffix, text in _flatten_strings(item):
                yield f"[{key!r}]{suffix}", text


class _FunctionIndex(ast.NodeVisitor):
    def __init__(self) -> None:
        self.stack: list[str] = []
        self.functions: dict[str, ast.AST] = {}

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def _function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        qualified = ".".join((*self.stack, node.name))
        self.functions[qualified] = node
        if not self.stack:
            self.functions.setdefault(node.name, node)
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    visit_FunctionDef = _function
    visit_AsyncFunctionDef = _function


def _top_assignments(tree: ast.Module) -> dict[str, ast.AST]:
    result: dict[str, ast.AST] = {}
    for statement in tree.body:
        if isinstance(statement, (ast.Assign, ast.AnnAssign)):
            value = statement.value
            targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
            if value is None:
                continue
            for target in targets:
                if isinstance(target, ast.Name):
                    result[target.id] = value
    return result


class _RoleAnalyzer(ast.NodeVisitor):
    def __init__(
        self,
        role: str,
        facts: Facts,
        selected_constants: set[str],
        module_spec: Mapping[str, Any],
    ) -> None:
        self.role = role
        self.facts = facts
        self.selected_constants = selected_constants
        self.load_variables: set[str] = set()
        self.array_variables: dict[str, str] = {}
        self.array_expressions: dict[str, ast.AST] = {}
        self.context = "module"
        writer_calls = module_spec.get("writer_calls", [])
        reader_attributes = module_spec.get("reader_attributes", [])
        if not isinstance(writer_calls, list) or not all(isinstance(item, str) for item in writer_calls):
            raise ContractScanError(f"{role}.writer_calls must be a string list")
        if not isinstance(reader_attributes, list) or not all(isinstance(item, str) for item in reader_attributes):
            raise ContractScanError(f"{role}.reader_attributes must be a string list")
        self.writer_calls = set(writer_calls)
        self.reader_attributes = set(reader_attributes)

    def analyze(self, nodes: Sequence[tuple[str, ast.AST]]) -> None:
        for context, node in nodes:
            self.context = context
            self._discover_arrays(node)
            self.visit(node)

    def _add(self, mapping: dict[str, list[Occurrence]], key: str, value: Any, node: ast.AST) -> None:
        mapping.setdefault(key, []).append(Occurrence(value, getattr(node, "lineno", 0), self.context))

    def _discover_arrays(self, node: ast.AST) -> None:
        for child in ast.walk(node):
            if not isinstance(child, (ast.Assign, ast.AnnAssign)) or child.value is None:
                continue
            targets = child.targets if isinstance(child, ast.Assign) else [child.target]
            if not isinstance(child.value, ast.Call):
                continue
            call = child.value
            call_name = _call_name(call)
            call_leaf = call_name.rsplit(".", 1)[-1]
            for target in targets:
                if not isinstance(target, ast.Name):
                    continue
                if call_name.endswith(".load") or call_name == "load":
                    self.load_variables.add(target.id)
                if call_leaf in {"asarray", "array", "reshape", "zeros", "ones", "empty", "full"}:
                    self.array_expressions[target.id] = call
                if call_leaf in {"asarray", "array"}:
                    if call.args and isinstance(call.args[0], ast.Subscript):
                        key = _subscript_string(call.args[0])
                        owner = _name(call.args[0].value)
                        if key and owner in self.load_variables:
                            self.array_variables[target.id] = key

    def visit_Dict(self, node: ast.Dict) -> None:
        if self.role == "producer":
            for key in node.keys:
                value = _literal(key) if key is not None else None
                if isinstance(value, str):
                    self._add(self.facts.fields, value, True, key)
        for key, value_node in zip(node.keys, node.values, strict=True):
            key_value = _literal(key) if key is not None else None
            value = _literal(value_node)
            if isinstance(key_value, str) and isinstance(value, str):
                category = _constant_category(key_value)
                if category:
                    self._add(self.facts.tokens, f"{category}:{key_value}", value, value_node)
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        key = _subscript_string(node)
        if key is not None:
            if self.role == "consumer" and isinstance(node.ctx, ast.Load):
                self._add(self.facts.fields, key, True, node)
            elif self.role == "producer" and isinstance(node.ctx, ast.Store):
                self._add(self.facts.fields, key, True, node)
            owner = _name(node.value)
            if self.role == "consumer" and owner in self.load_variables:
                self._add(self.facts.npz_arrays, key, True, node)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        call_name = _call_name(node)
        call_leaf = call_name.rsplit(".", 1)[-1]
        if self.role == "producer" and call_leaf in self.writer_calls:
            for keyword in node.keywords:
                if keyword.arg is not None:
                    self._add(self.facts.fields, keyword.arg, True, keyword.value)
        if self.role == "consumer" and call_name.endswith(".get") and node.args:
            key = _literal(node.args[0])
            if isinstance(key, str):
                self._add(self.facts.fields, key, True, node.args[0])
        if self.role == "consumer" and call_leaf == "getattr" and len(node.args) >= 2:
            key = _literal(node.args[1])
            if isinstance(key, str):
                self._add(self.facts.fields, key, True, node.args[1])
        if self.role == "producer" and call_name.rsplit(".", 1)[-1] in {"savez", "savez_compressed"}:
            for keyword in node.keywords:
                if keyword.arg is None:
                    continue
                self._add(self.facts.npz_arrays, keyword.arg, True, keyword.value)
                dtype, shape = self._array_expression(keyword.value)
                if dtype:
                    self._add(self.facts.dtypes, keyword.arg, dtype, keyword.value)
                if shape is not None:
                    self._add(self.facts.shapes, keyword.arg, shape, keyword.value)
        if self.role == "consumer" and call_name.endswith((".asarray", ".array")) and node.args:
            source = node.args[0]
            if isinstance(source, ast.Subscript):
                key = _subscript_string(source)
                if key and _name(source.value) in self.load_variables:
                    dtype = next((_dtype_name(k.value) for k in node.keywords if k.arg == "dtype"), None)
                    if dtype:
                        self._add(self.facts.dtypes, key, dtype, node)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if self.role == "consumer" and node.attr in self.reader_attributes:
            self._add(self.facts.fields, node.attr, True, node)
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        operands = [node.left, *node.comparators]
        for left, right in zip(operands, operands[1:]):
            for variable_node, shape_node in ((left, right), (right, left)):
                if (
                    isinstance(variable_node, ast.Attribute)
                    and variable_node.attr == "shape"
                    and isinstance(variable_node.value, ast.Name)
                    and variable_node.value.id in self.array_variables
                ):
                    shape = _shape_value(shape_node)
                    if shape is not None:
                        self._add(
                            self.facts.shapes,
                            self.array_variables[variable_node.value.id],
                            shape,
                            shape_node,
                        )
        self.generic_visit(node)

    def _array_expression(self, node: ast.AST) -> tuple[str | None, Any]:
        dtype: str | None = None
        shape: Any = None
        current = node
        if isinstance(current, ast.Name) and current.id in self.array_expressions:
            current = self.array_expressions[current.id]
        if isinstance(current, ast.Call) and _call_name(current).rsplit(".", 1)[-1] == "reshape":
            if len(current.args) == 1:
                shape = _shape_value(current.args[0])
            else:
                values = tuple(_literal(argument) for argument in current.args)
                if all(isinstance(value, int) for value in values):
                    shape = values
            current = current.func.value if isinstance(current.func, ast.Attribute) else current
            if isinstance(current, ast.Name) and current.id in self.array_expressions:
                current = self.array_expressions[current.id]
        if isinstance(current, ast.Call):
            dtype = next((_dtype_name(item.value) for item in current.keywords if item.arg == "dtype"), None)
            if _call_name(current).rsplit(".", 1)[-1] in {"zeros", "ones", "empty", "full"} and current.args:
                shape = _shape_value(current.args[0])
        return dtype, shape


def _extract(
    path: Path,
    role: str,
    module_spec: Mapping[str, Any],
    pair_spec: Mapping[str, Any],
) -> Facts:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError) as error:
        raise ContractScanError(f"cannot parse {path}: {error}") from error
    index = _FunctionIndex()
    index.visit(tree)
    requested = module_spec.get("functions", [])
    if not isinstance(requested, list) or not all(isinstance(name, str) for name in requested):
        raise ContractScanError(f"{role}.functions must be a string list")
    missing = [name for name in requested if name not in index.functions]
    if missing:
        raise ContractScanError(f"missing {role} functions in {path}: {', '.join(missing)}")
    assignments = _top_assignments(tree)
    nodes = [(name, index.functions[name]) for name in requested]
    referenced = {
        child.id
        for _name_, node in nodes
        for child in ast.walk(node)
        if isinstance(child, ast.Name)
    }
    explicit = module_spec.get("constants", [])
    if not isinstance(explicit, list) or not all(isinstance(name, str) for name in explicit):
        raise ContractScanError(f"{role}.constants must be a string list")
    selected_constants = (referenced | set(explicit)) & set(assignments)
    facts = Facts(path=path, sha256=_sha256(path), functions_found=list(requested))
    for name in sorted(selected_constants):
        node = assignments[name]
        value = _literal(node)
        occurrence = Occurrence(value, getattr(node, "lineno", 0), f"constant {name}")
        facts.constants[name] = occurrence
        category = _constant_category(name)
        if category:
            for suffix, text in _flatten_strings(value):
                facts.tokens.setdefault(f"{category}:{name}{suffix}", []).append(
                    Occurrence(text, occurrence.line, occurrence.context)
                )
        upper = name.upper()
        if re.search(r"(LAYOUT|FEATURE_MAJOR|ACTION_MAJOR|DIM|SUBSTEPS|SAMPLES|HORIZON)", upper):
            facts.layouts.setdefault(name, []).append(occurrence)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            facts.numerics.setdefault(name, []).append(occurrence)
        if role == "consumer" and "FIELD" in upper and isinstance(value, (set, frozenset, tuple, list)):
            for item in value:
                if isinstance(item, str):
                    facts.fields.setdefault(item, []).append(occurrence)
    analyzer = _RoleAnalyzer(role, facts, selected_constants, module_spec)
    analyzer.analyze(nodes + [(f"constant {name}", assignments[name]) for name in sorted(selected_constants)])
    allowed_layouts = pair_spec.get("layout_constants")
    if isinstance(allowed_layouts, list):
        facts.layouts = {key: value for key, value in facts.layouts.items() if key in allowed_layouts}
    allowed_numerics = pair_spec.get("numeric_constants")
    if isinstance(allowed_numerics, list):
        facts.numerics = {key: value for key, value in facts.numerics.items() if key in allowed_numerics}
    return facts


def _single_value(values: list[Occurrence]) -> Any:
    unique = {_stable_value(item.value) for item in values}
    if len(unique) == 1:
        return next(iter(unique))
    return sorted(unique)


def _stable_value(value: Any) -> str:
    return json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"))


def _status(producer: list[Occurrence] | None, consumer: list[Occurrence] | None) -> str:
    if producer is None:
        return "CONSUMER_ONLY"
    if consumer is None:
        return "PRODUCER_ONLY"
    return "MATCH" if _single_value(producer) == _single_value(consumer) else "MISMATCH"


def _compare_category(
    category: str,
    producer: Mapping[str, list[Occurrence]],
    consumer: Mapping[str, list[Occurrence]],
    producer_path: Path,
    consumer_path: Path,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for key in sorted(set(producer) | set(consumer)):
        left, right = producer.get(key), consumer.get(key)
        item_category = key.split(":", 1)[0] if category == "token" else category
        items.append(
            {
                "category": item_category,
                "item": key,
                "status": _status(left, right),
                "producer": [item.payload(producer_path) for item in left or []],
                "consumer": [item.payload(consumer_path) for item in right or []],
            }
        )
    return items


def _binding_item(
    binding: Mapping[str, Any], producer: Facts, consumer: Facts
) -> dict[str, Any]:
    name = binding.get("name")
    category = binding.get("category")
    left_name, right_name = binding.get("producer"), binding.get("consumer")
    if not all(isinstance(value, str) and value for value in (name, category, left_name, right_name)):
        raise ContractScanError("each binding needs category/name/producer/consumer strings")
    left = producer.constants.get(left_name)
    right = consumer.constants.get(right_name)
    left_values = [left] if left else None
    right_values = [right] if right else None
    return {
        "category": category,
        "item": name,
        "status": _status(left_values, right_values),
        "producer_symbol": left_name,
        "consumer_symbol": right_name,
        "producer": [left.payload(producer.path)] if left else [],
        "consumer": [right.payload(consumer.path)] if right else [],
    }


def _resolve_path(repo: Path, value: Any) -> Path:
    if not isinstance(value, str) or not value:
        raise ContractScanError("module path must be a nonempty string")
    path = Path(value)
    return (path if path.is_absolute() else repo / path).resolve()


def scan_pair(repo: Path, pair: Mapping[str, Any]) -> dict[str, Any]:
    name = pair.get("name")
    if not isinstance(name, str) or not name:
        raise ContractScanError("pair name must be a nonempty string")
    producer_spec, consumer_spec = pair.get("producer"), pair.get("consumer")
    if not isinstance(producer_spec, Mapping) or not isinstance(consumer_spec, Mapping):
        raise ContractScanError(f"pair {name} requires producer and consumer objects")
    producer_path = _resolve_path(repo, producer_spec.get("path"))
    consumer_path = _resolve_path(repo, consumer_spec.get("path"))
    missing = [str(path) for path in (producer_path, consumer_path) if not path.is_file()]
    if missing:
        return {
            "name": name,
            "status": "BLOCKED",
            "blocked_reason": "module file missing",
            "missing": missing,
            "producer_path": str(producer_path),
            "consumer_path": str(consumer_path),
            "items": [],
        }
    try:
        producer = _extract(producer_path, "producer", producer_spec, pair)
        consumer = _extract(consumer_path, "consumer", consumer_spec, pair)
    except ContractScanError as error:
        return {
            "name": name,
            "status": "BLOCKED",
            "blocked_reason": str(error),
            "producer_path": str(producer_path),
            "consumer_path": str(consumer_path),
            "items": [],
        }
    items: list[dict[str, Any]] = []
    bindings = pair.get("bindings", [])
    if not isinstance(bindings, list):
        raise ContractScanError(f"pair {name} bindings must be a list")
    items.extend(_binding_item(binding, producer, consumer) for binding in bindings)
    bound_symbols = {
        (binding.get("producer"), binding.get("consumer")) for binding in bindings
        if isinstance(binding, Mapping)
    }
    categories = (
        ("token", producer.tokens, consumer.tokens),
        ("receipt_json_field", producer.fields, consumer.fields),
        ("npz_array", producer.npz_arrays, consumer.npz_arrays),
        ("npz_dtype", producer.dtypes, consumer.dtypes),
        ("npz_shape", producer.shapes, consumer.shapes),
        ("layout_constant", producer.layouts, consumer.layouts),
        ("numeric_constant", producer.numerics, consumer.numerics),
    )
    for category, left, right in categories:
        compared = _compare_category(category, left, right, producer.path, consumer.path)
        # A semantic binding is the authoritative comparison for differently
        # named constants; retain automatic extraction for every other item.
        if category in {"layout_constant", "numeric_constant"}:
            compared = [
                item for item in compared
                if not any(item["item"] in symbols for symbols in bound_symbols)
            ]
        items.extend(compared)
    counts = {status: sum(item["status"] == status for item in items) for status in STATUSES}
    return {
        "name": name,
        "status": "MISMATCH" if counts["MISMATCH"] else "COMPLETE",
        "producer": {
            "path": str(producer.path),
            "sha256": producer.sha256,
            "functions": producer.functions_found,
        },
        "consumer": {
            "path": str(consumer.path),
            "sha256": consumer.sha256,
            "functions": consumer.functions_found,
        },
        "counts": counts,
        "items": items,
    }


def scan_spec(spec_path: Path, repo: Path, selected_pairs: set[str] | None = None) -> dict[str, Any]:
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ContractScanError(f"cannot read spec {spec_path}: {error}") from error
    if not isinstance(spec, dict) or spec.get("schema") != SPEC_SCHEMA:
        raise ContractScanError(f"spec schema must be {SPEC_SCHEMA}")
    pairs = spec.get("pairs")
    if not isinstance(pairs, list):
        raise ContractScanError("spec pairs must be a list")
    if selected_pairs:
        pairs = [pair for pair in pairs if isinstance(pair, dict) and pair.get("name") in selected_pairs]
        found = {pair.get("name") for pair in pairs}
        if found != selected_pairs:
            raise ContractScanError(f"unknown pair(s): {', '.join(sorted(selected_pairs - found))}")
    reports = [scan_pair(repo, pair) for pair in pairs]
    status = (
        "MISMATCH" if any(pair["status"] == "MISMATCH" for pair in reports)
        else "BLOCKED" if any(pair["status"] == "BLOCKED" for pair in reports)
        else "COMPLETE"
    )
    return {
        "schema": REPORT_SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "scientific_output": False,
        "spec": str(spec_path.resolve()),
        "spec_sha256": _sha256(spec_path),
        "repo": str(repo),
        "status": status,
        "pairs": reports,
    }


def _markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# Static producer/consumer contract scan",
        "",
        f"Claim ceiling: `{CLAIM_CEILING}`.",
        "",
        "This is read-only engineering diagnostics and is not evidence of scientific efficacy.",
        "",
        f"Overall status: **{report['status']}**",
        "",
    ]
    for pair in report["pairs"]:
        lines.extend([f"## {pair['name']}", "", f"Status: **{pair['status']}**", ""])
        if pair["status"] == "BLOCKED":
            lines.extend([f"Reason: {pair['blocked_reason']}", ""])
            for path in pair.get("missing", []):
                lines.append(f"- Missing: `{path}`")
            lines.append("")
            continue
        lines.extend(
            [
                f"Producer: `{pair['producer']['path']}` (`{pair['producer']['sha256']}`)",
                "",
                f"Consumer: `{pair['consumer']['path']}` (`{pair['consumer']['sha256']}`)",
                "",
                "| Category | Item | Status | Producer locations | Consumer locations |",
                "|---|---|---|---|---|",
            ]
        )
        for item in pair["items"]:
            left = "<br>".join(
                f"`{entry['value']}` @ `{entry['location']}`" for entry in item["producer"]
            ) or "—"
            right = "<br>".join(
                f"`{entry['value']}` @ `{entry['location']}`" for entry in item["consumer"]
            ) or "—"
            safe_item = str(item["item"]).replace("|", "\\|")
            lines.append(f"| {item['category']} | `{safe_item}` | {item['status']} | {left} | {right} |")
        lines.append("")
    return "\n".join(lines) + "\n"


def _write_once(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise ContractScanError(f"refusing to overwrite report: {path}")
    path.write_bytes(data)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--pair", action="append", dest="pairs")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = args.output.resolve()
    if output.exists() or output.is_symlink():
        print(f"CONTRACT_SCAN_ERROR: output already exists: {output}")
        return 2
    output.mkdir(parents=True)
    try:
        report = scan_spec(args.spec.resolve(), args.repo.resolve(), set(args.pairs or []) or None)
        payload = json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False).encode("ascii") + b"\n"
        _write_once(output / "contract-scan.json", payload)
        _write_once(output / "contract-scan.md", _markdown(report).encode("utf-8"))
    except Exception as error:
        print(f"CONTRACT_SCAN_ERROR: {type(error).__name__}: {error}")
        return 2
    print(f"CONTRACT_SCAN_{report['status']} pairs={len(report['pairs'])}")
    return {"COMPLETE": 0, "MISMATCH": 1, "BLOCKED": 3}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
