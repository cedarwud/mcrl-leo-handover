#!/usr/bin/env python3
"""Orchestrate the one-seed five-arm SMC-ER short-EP preview on a server."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))

from run_short_ep import ARM_LABELS, load_gate_ledger  # noqa: E402


SCHEMA = "smc-er-one-seed-preview-matrix-v1"
ARMS = ("B000", "F111", "A011", "A101", "A110")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _run(command: list[str], *, log: Path) -> dict[str, Any]:
    started = dt.datetime.now(dt.timezone.utc)
    with log.open("w", encoding="utf-8") as stream:
        completed = subprocess.run(
            command,
            cwd=REPO,
            stdout=stream,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    ended = dt.datetime.now(dt.timezone.utc)
    receipt = {
        "command": command,
        "started_utc": started.isoformat(),
        "ended_utc": ended.isoformat(),
        "elapsed_s": (ended - started).total_seconds(),
        "exit_code": int(completed.returncode),
        "log": str(log),
        "log_sha256": _sha256(log),
    }
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed with exit {completed.returncode}; inspect {log}"
        )
    return receipt


def _runner_command(
    *,
    arm: str,
    output: Path,
    episodes: int,
    train_seed: int,
    env_seed: int,
    mobility_seed: int,
    gate_manifest: Path | None,
    c1_exp_corpus_manifest: Path | None,
    prereg: Path,
    tle_root: Path,
) -> list[str]:
    command = [
        sys.executable,
        str(HERE / "run_short_ep.py"),
        "--arm",
        arm,
        "--output-dir",
        str(output),
        "--episodes",
        str(episodes),
        "--epsilon-decay-episodes",
        "8" if episodes == 10 else str(max(1, episodes - 2)),
        "--target-update-every",
        "2" if episodes == 10 else "1",
        "--users",
        "100",
        "--train-seed",
        str(train_seed),
        "--env-seed",
        str(env_seed),
        "--mobility-seed",
        str(mobility_seed),
        "--prereg",
        str(prereg),
        "--tle-root",
        str(tle_root),
    ]
    if arm != "B000" and gate_manifest is not None:
        command.extend(["--gate-manifest", str(gate_manifest)])
    if arm != "B000":
        if c1_exp_corpus_manifest is None:
            raise ValueError("treatment arm requires the frozen C1 EXP corpus")
        command.extend(
            ["--c1-exp-corpus-manifest", str(c1_exp_corpus_manifest)]
        )
    return command


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--gate-manifest", type=Path, required=True)
    parser.add_argument("--c1-exp-corpus-manifest", type=Path, required=True)
    parser.add_argument("--train-seed", type=int, required=True)
    parser.add_argument("--env-seed", type=int, required=True)
    parser.add_argument("--mobility-seed", type=int, required=True)
    parser.add_argument("--evaluation-seeds", type=int, nargs=3, required=True)
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument(
        "--prereg",
        type=Path,
        default=REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json",
    )
    parser.add_argument("--tle-root", type=Path, required=True)
    parser.add_argument("--skip-server-parity", action="store_true")
    parser.add_argument(
        "--allow-all-shadow-engineering-smoke", action="store_true"
    )
    args = parser.parse_args(argv)
    if args.episodes < 1:
        parser.error("--episodes must be positive")
    if len(set(args.evaluation_seeds)) != 3:
        parser.error("--evaluation-seeds must contain three distinct values")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    output_root = args.output_root.expanduser().resolve()
    gate_manifest = args.gate_manifest.expanduser().resolve()
    c1_exp_corpus_manifest = args.c1_exp_corpus_manifest.expanduser().resolve()
    prereg = args.prereg.expanduser().resolve()
    tle_root = args.tle_root.expanduser().resolve()
    ledger, gate_payload = load_gate_ledger(gate_manifest)
    routed = [source for source in ("C1", "C2", "C3") if ledger.routes(source)]
    if not routed and not args.allow_all_shadow_engineering_smoke:
        raise RuntimeError(
            "all specialist gates are shadow; a five-line preview would collapse "
            "to baseline and is not informative"
        )
    output_root.mkdir(parents=True, exist_ok=False)
    logs = output_root / "logs"
    logs.mkdir()
    receipts: list[dict[str, Any]] = []

    test_command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        ".scratch/smc-er-short-ep/test_smc_er_core.py",
        ".scratch/smc-er-short-ep/test_smc_er_roles.py",
        ".scratch/smc-er-short-ep/test_run_short_ep.py",
        ".scratch/smc-er-short-ep/test_sweep_evaluation.py",
        ".scratch/catfish-stage0/test_c3_reward_aligned_core.py",
    ]
    receipts.append(_run(test_command, log=logs / "00-tests.log"))

    if not args.skip_server_parity:
        baseline_parity = output_root / "parity-baseline"
        carrier_parity = output_root / "parity-carrier-all-shadow"
        receipts.append(
            _run(
                _runner_command(
                    arm="B000",
                    output=baseline_parity,
                    episodes=2,
                    train_seed=args.train_seed,
                    env_seed=args.env_seed,
                    mobility_seed=args.mobility_seed,
                    gate_manifest=None,
                    c1_exp_corpus_manifest=None,
                    prereg=prereg,
                    tle_root=tle_root,
                ),
                log=logs / "01-parity-baseline.log",
            )
        )
        receipts.append(
            _run(
                _runner_command(
                    arm="F111",
                    output=carrier_parity,
                    episodes=2,
                    train_seed=args.train_seed,
                    env_seed=args.env_seed,
                    mobility_seed=args.mobility_seed,
                    gate_manifest=None,
                    c1_exp_corpus_manifest=c1_exp_corpus_manifest,
                    prereg=prereg,
                    tle_root=tle_root,
                ),
                log=logs / "02-parity-carrier.log",
            )
        )
        parity_output = output_root / "zero-dose-parity.json"
        receipts.append(
            _run(
                [
                    sys.executable,
                    str(HERE / "check_zero_dose_parity.py"),
                    "--baseline-state",
                    str(baseline_parity / "training-state.pt"),
                    "--carrier-state",
                    str(carrier_parity / "carrier-state.pt"),
                    "--output",
                    str(parity_output),
                ],
                log=logs / "03-zero-dose-parity.log",
            )
        )

    checkpoints: dict[str, Path] = {}
    for index, arm in enumerate(ARMS, start=10):
        arm_output = output_root / arm
        receipts.append(
            _run(
                _runner_command(
                    arm=arm,
                    output=arm_output,
                    episodes=args.episodes,
                    train_seed=args.train_seed,
                    env_seed=args.env_seed,
                    mobility_seed=args.mobility_seed,
                    gate_manifest=gate_manifest,
                    c1_exp_corpus_manifest=(
                        None if arm == "B000" else c1_exp_corpus_manifest
                    ),
                    prereg=prereg,
                    tle_root=tle_root,
                ),
                log=logs / f"{index:02d}-{arm}.log",
            )
        )
        checkpoint = arm_output / "final-checkpoint.pt"
        if not checkpoint.is_file():
            raise RuntimeError(f"{arm} did not produce a final checkpoint")
        checkpoints[arm] = checkpoint

    sweep_output = output_root / "ee-sweep"
    sweep_command = [sys.executable, str(HERE / "sweep_evaluation.py")]
    for arm in ARMS:
        sweep_command.extend(
            ["--arm", f"{ARM_LABELS[arm]}={checkpoints[arm]}"]
        )
    sweep_command.extend(
        [
            "--users",
            "60",
            "80",
            "100",
            "120",
            "140",
            "--seeds",
            *(str(seed) for seed in args.evaluation_seeds),
            "--output-dir",
            str(sweep_output),
            "--prereg",
            str(prereg),
            "--tle-root",
            str(tle_root),
        ]
    )
    receipts.append(_run(sweep_command, log=logs / "20-ee-sweep.log"))
    plot = sweep_output / "ee-vs-users-short-ep.png"
    if not plot.is_file():
        receipts.append(
            _run(
                [
                    "python3",
                    str(HERE / "render_sweep_plot.py"),
                    "--summary",
                    str(sweep_output / "sweep-summary.json"),
                    "--output",
                    str(plot),
                ],
                log=logs / "21-render-plot.log",
            )
        )

    receipt = {
        "schema": SCHEMA,
        "status": "complete",
        "claim_ceiling": "ONE-SEED-10EP-PREVIEW" if args.episodes == 10 else "ENGINEERING-SMOKE",
        "episodes": args.episodes,
        "training_seed": args.train_seed,
        "environment_seed": args.env_seed,
        "mobility_seed": args.mobility_seed,
        "evaluation_seeds": list(args.evaluation_seeds),
        "gate_manifest": str(gate_manifest),
        "gate_manifest_sha256": _sha256(gate_manifest),
        "c1_exp_corpus_manifest": str(c1_exp_corpus_manifest),
        "c1_exp_corpus_manifest_sha256": _sha256(c1_exp_corpus_manifest),
        "prereg": str(prereg),
        "prereg_sha256": _sha256(prereg),
        "tle_root": str(tle_root),
        "gate_payload": gate_payload,
        "routed_sources": routed,
        "checkpoints": {
            arm: {"path": str(path), "sha256": _sha256(path)}
            for arm, path in checkpoints.items()
        },
        "plot": str(plot),
        "plot_sha256": _sha256(plot),
        "commands": receipts,
    }
    _write_json(output_root / "matrix-receipt.json", receipt)
    print(output_root / "matrix-receipt.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
