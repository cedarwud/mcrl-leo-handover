"""W-156 -- independent V0.14 learner-gate receipt verification."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest


REPO = Path(__file__).resolve().parents[1]
GATE_PATH = REPO / ".scratch" / "multi-catfish-v014-learner" / "run_v014_learner_gate.py"
VERIFY_PATH = REPO / ".scratch" / "multi-catfish-v014-learner" / "verify_v014_learner_gate.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


GATE = _load("mcrl_v014_gate_w156", GATE_PATH)
VERIFY = _load("mcrl_v014_gate_verify_w156", VERIFY_PATH)


def _source(*, world: int, lineage: int, rows: int = 4):
    source_runner = GATE._SOURCE_MODULE
    masks = np.ones((rows, 28), dtype=np.bool_)
    q2 = np.zeros((rows, 28), dtype=np.float64)
    q3 = np.zeros((rows, 28), dtype=np.float64)
    q2[:, 1] = np.arange(1, rows + 1, dtype=np.float64)
    q3[:, 2] = np.arange(1, rows + 1, dtype=np.float64)
    compatibility = np.zeros((rows, 28), dtype=np.bool_)
    compatibility[:, 2] = True
    anchors = np.asarray(
        [format(world * 1000 + lineage * 10 + row + 1, "064x") for row in range(rows)],
        dtype="S64",
    )
    return source_runner.assemble_source_arrays(
        q1_values=np.zeros((rows, 28), dtype=np.float64),
        q2_states=np.arange(rows * GATE.V014_Q2_STATE_DIM, dtype=np.float32).reshape(
            rows, GATE.V014_Q2_STATE_DIM
        ) / 1000.0,
        q2_masks=masks,
        q2_reference_actions=np.zeros(rows, dtype=np.int64),
        q2_target_bits=q2,
        q3_states=np.arange(rows * GATE.V014_Q3_STATE_DIM, dtype=np.float32).reshape(
            rows, GATE.V014_Q3_STATE_DIM
        ) / 1000.0,
        q3_masks=masks.copy(),
        q3_reference_actions=np.ones(rows, dtype=np.int64),
        q3_target_bits=q3,
        q3_compatibility=compatibility,
        source_seeds=np.full(rows, world, dtype=np.int64),
        anchor_sha256s=anchors,
        step_indices=np.arange(rows, dtype=np.int64),
        user_indices=np.zeros(rows, dtype=np.int64),
        world_seed=world,
        lineage=lineage,
        field_root_digest=format(world + lineage, "064x"),
        kappa_bits=GATE.OPS3_KAPPA_BITS,
    )


def _write_sources(root: Path) -> list[Path]:
    paths = []
    for world in (11, 12, 13):
        for lineage in (1, 2, 3):
            path = root / f"w{world}-l{lineage}"
            GATE._SOURCE_MODULE.write_source_shard(
                path, _source(world=world, lineage=lineage)
            )
            paths.append(path)
    return paths


def test_verifier_recomputes_decisions_and_checkpoint_hashes(tmp_path: Path) -> None:
    sources = _write_sources(tmp_path / "sources")
    spec = GATE.V014GateSpec(
        initialization_seeds=(101, 102, 103),
        source_lineages=(1, 2, 3),
        update_rungs=(1, 2),
        train_world_seeds=(11, 12),
        validation_world_seeds=(13,),
        batch_size=4,
        q2_hidden_layers=(4,),
        q3_hidden_layers=(4,),
    )
    output = tmp_path / "gate"
    GATE.run(source_paths=sources, output_dir=output, spec=spec)
    receipt = VERIFY.verify(output)
    assert receipt["status"] == "VERIFIED"
    assert receipt["checkpoint_files_verified"] == 6
    assert receipt["test_split_opened"] is False

    checkpoint = next((output / "checkpoints").glob("*.pt"))
    checkpoint.write_bytes(checkpoint.read_bytes() + b"tamper")
    with pytest.raises(VERIFY.V014GateVerificationError, match="checkpoint"):
        VERIFY.verify(output)

