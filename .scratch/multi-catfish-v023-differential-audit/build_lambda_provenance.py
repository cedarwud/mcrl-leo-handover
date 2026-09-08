"""Inventory every scoped OPS-3 construction call and frozen-lambda default."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "lambda-provenance.json"
CALIBRATION_NAMES = {"lambda_", "lambda_bits_per_j", "eta", "price"}
BUILDERS = {"build_ops3_surface", "build_ops3_live_surfaces"}
STALE_HEX = "0x1.443a8f481639ap+26"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _python_files() -> list[Path]:
    roots = [REPO / "src/mcrl/runtime"]
    roots.extend(sorted((REPO / ".scratch").glob("multi-catfish-v023-*")))
    return sorted(path for root in roots if root.is_dir() for path in root.rglob("*.py"))


def _inventory() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    calls: list[dict[str, object]] = []
    defaults: list[dict[str, object]] = []
    for path in _python_files():
        relative = path.relative_to(REPO).as_posix()
        source = path.read_text()
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for line, text in enumerate(source.splitlines(), 1):
            if STALE_HEX in text:
                defaults.append({"path": relative, "line": line, "text": text.strip()})
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or _call_name(node) not in BUILDERS:
                continue
            keywords = sorted(word.arg for word in node.keywords if word.arg is not None)
            calls.append(
                {
                    "path": relative,
                    "line": node.lineno,
                    "builder": _call_name(node),
                    "explicit_calibration": bool(CALIBRATION_NAMES.intersection(keywords)),
                    "keywords": keywords,
                    "test_only": "/tests/" in relative or Path(relative).name.startswith("test_"),
                }
            )
    return calls, defaults


def main() -> None:
    calls, defaults = _inventory()
    evidence_paths = [
        REPO / "artifacts/multi-catfish-v014-learnability-20260903-r1/server-run/source-panel/shards/2026108001-2026092101/metadata.json",
        REPO / ".scratch/multi-catfish-v020-c3-source-audit/q2-batch-repricing/result.json",
        Path("/home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8/receipt.json"),
        REPO / ".scratch/multi-catfish-v023-controller-handoff-20260907/r7-sealed-receipts/result.json",
        Path("/home/sat/mcrl-v023-c3-existence-e1-20260908-r1/terminal-receipt.json"),
        Path("/home/sat/mcrl-v023-c3-probe-s0-20260908-r1/probe-s0-result.json"),
        REPO / ".scratch/multi-catfish-v023-c3s-screen/c3s_config.json",
        Path("/home/sat/mcrl-v023-c3s-run/.scratch/multi-catfish-v023-c3s-screen/runs/c3s-20260908-r1/terminal/terminal-receipt.json"),
        Path("/home/sat/mcrl-v023-pipeline-20260908/STATUS.md"),
    ]
    evidence = [
        {"path": str(path), "sha256": _sha256(path)} for path in evidence_paths if path.is_file()
    ]
    payload = {
        "schema": "v023-lambda-fallback-provenance-v1",
        "scope": ["src/mcrl/runtime/**/*.py", ".scratch/multi-catfish-v023-*/**/*.py"],
        "stale_lambda_hex": STALE_HEX,
        "calls": calls,
        "stale_constant_occurrences": defaults,
        "evidence_files": evidence,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"{len(calls)} calls; {len(defaults)} stale-constant occurrences; {OUTPUT}")


if __name__ == "__main__":
    main()
