#!/usr/bin/env python3
"""Run the server's older abl9k EE sweep against a periodic checkpoint.

The server copy predates the ``--ckpt-rel`` CLI flag.  This wrapper loads that
unchanged evaluator, injects the checkpoint relative path in memory, and then
calls its normal CLI entry point.  It never writes or patches the evaluator.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path


EXTRA_ARMS = {
    "abl9k_strategy3_annealed": {
        "dir": "abl9k_strategy3_annealed",
        "yaml": "configs/shared_q_isolation/v3/abl9k_strategy3_annealed.yaml",
        "label": "Experience shaping",
    },
    "abl9k_strategy3_acrm": {
        "dir": "abl9k_strategy3_acrm",
        "yaml": "configs/shared_q_isolation/v3/abl9k_strategy3_acrm.yaml",
        "label": "Reward shaping",
    },
    "abl9k_capacity": {
        "dir": "abl9k_capacity",
        "yaml": "configs/shared_q_isolation/v3/abl9k_capacity.yaml",
        "label": "Penalty shaping",
    },
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("axis", choices=("num_users", "p_base"))
    parser.add_argument("--arm", required=True)
    parser.add_argument("--arms-root", required=True)
    parser.add_argument("--out-stem", required=True)
    parser.add_argument("--episodes", type=int, default=48)
    parser.add_argument(
        "--checkpoint-rel",
        default="checkpoints-periodic/ep-01700.pt",
    )
    parser.add_argument(
        "--evaluator",
        default="analysis/family-b-collapse-diagnosis/catfish-v2/abl9k_ee_vs_param.py",
    )
    args = parser.parse_args()

    os.environ["EP"] = str(args.episodes)
    evaluator = Path(args.evaluator).resolve()
    spec = importlib.util.spec_from_file_location("abl9k_ee_vs_param_server", evaluator)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load evaluator: {evaluator}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.CKPT_REL = args.checkpoint_rel
    module.ARM_REGISTRY.update(EXTRA_ARMS)
    sys.argv = [
        str(evaluator),
        args.axis,
        "--arms",
        args.arm,
        "--arms-root",
        args.arms_root,
        "--out-stem",
        args.out_stem,
    ]
    return int(module.main())


if __name__ == "__main__":
    raise SystemExit(main())
