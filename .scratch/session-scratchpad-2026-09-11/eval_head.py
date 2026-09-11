"""B0 greedy pooled-EE evaluation -- the catfish-surface harness, reused.

Source: ``.scratch/catfish-surface/CATFISH-ATTACHMENT-SURFACE-2026-09-11.md``,
section "Pooled EE -- the declared primary endpoint", script ``pooled_ee.py``
(sha256 9b469c64...).  The block between the two HARNESS-CORE markers below
is copied from that script **byte for byte** (its lines 53-143: ``preds``,
``argmax_masked``, ``scalar_arm``, ``arm_maxgain``, ``arm_random``,
``arm_trained``, ``run``), and the header constants are its own.  Only three
things differ, all outside the core:

  * the repo path is this script's own tree, not a hardcoded local path;
  * ``CKPT`` is set per arm from the command line;
  * the driver prints one JSON line per arm instead of the fixed five-arm table.

Estimand (unchanged): pooled_EE = sum(bits) / sum(joules) over all
24 episodes x 10 steps, divided ONCE; bits and joules come from
``env.last_outcome.energy``, not from the reward fields.  READ-ONLY: no
``update()``, no gradient step, no optimizer step.

Usage::

    b0_pooled_ee_eval.py LABEL=PATH [LABEL=PATH ...] [--random]
"""
import json
import statistics as st
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import numpy as np

from mcrl.algorithms.modqn import MODQNTrainer
from mcrl.env.action_contract import NO_OP_ACTION, NUM_BEAM_SLOTS, PHI1, PHI2, no_op_actions
from mcrl.env.constants import DECISION_STEP_S
from mcrl.env.link_budget import BEAM_BANDWIDTH_HZ
from mcrl.runtime.trainer_spec import TrainerConfig
from mcrl.runtime.training_pipeline import make_training_environment

W = (0.5, 0.3, 0.2)
SC = (2029238.4328742754, 1.0, 6.0)
B = float(BEAM_BANDWIDTH_HZ)
KAPPA = 8.394622e-10 * 0.1          # kappa* x m*, frozen from scalar_demo.py
DT = float(DECISION_STEP_S)
N_EP = 24
CKPT = None  # set per arm by the driver below

cfg = TrainerConfig(learning_rate=0.001, episodes=1)
env = make_training_environment(users=100)
U, T = env.config.num_users, env.config.steps_per_episode


# ---- HARNESS-CORE BEGIN (verbatim from pooled_ee.py lines 53-143) ----
