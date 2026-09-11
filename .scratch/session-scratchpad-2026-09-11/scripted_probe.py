"""Read-only scripted-policy probe on the MODQN env.

NO training: update() is never called, no gradient step, no file written by
this script into the repo.  It replays the trainer's own episode protocol
(reset -> select -> step -> reward_vector_from_step_result) with scripted
action rules in place of the epsilon-greedy Q argmax, and reports the same
`r1_mean` statistic that `EpisodeLog` records, so the numbers are directly
comparable with artifacts/training-2026-08-25-rerun01/main/episode-logs.json.
"""
import sys
sys.path.insert(0, "/home/u24/papers/mcrl-leo-handover/src")

import numpy as np

from mcrl.algorithms.modqn import MODQNTrainer
from mcrl.env.action_contract import NO_OP_ACTION, no_op_actions
from mcrl.runtime.trainer_spec import TrainerConfig
from mcrl.runtime.training_pipeline import make_training_environment

N_EP = int(sys.argv[1]) if len(sys.argv) > 1 else 20

cfg = TrainerConfig(learning_rate=0.001, episodes=N_EP)
env = make_training_environment(users=100)


def pick_random(tr, encoded, masks, states):
    return tr.select_actions(encoded, masks, 1.0)


def pick_greedy_q(tr, encoded, masks, states):
    return tr.select_actions(encoded, masks, 0.0)


def _masked_arg(values, mask, biggest):
    U = len(mask)
    out = no_op_actions(U)
    for uid in range(U):
        valid = np.where(mask[uid].mask)[0]
        if valid.size == 0:
            out[uid] = NO_OP_ACTION
            continue
        v = values[uid][valid]
        out[uid] = int(valid[int(np.argmax(v) if biggest else np.argmin(v))])
    return out


def pick_maxsnr(tr, encoded, masks, states):
    """A2 / RSS_MAX analogue: greatest nominal channel quality among legal options."""
    return _masked_arg([s.channel_quality for s in states], masks, True)


def pick_leastload(tr, encoded, masks, states):
    """A3 analogue: least-loaded legal option."""
    return _masked_arg([s.beam_loads for s in states], masks, False)


def pick_maxsnr_per_load(tr, encoded, masks, states):
    """Crude congestion-aware gain rule: snr / (1 + load)."""
    vals = [s.channel_quality / (1.0 + s.beam_loads) for s in states]
    return _masked_arg(vals, masks, True)


ARMS = {
    "RANDOM_MASKED (eps=1)": pick_random,
    "UNTRAINED_Q_GREEDY": pick_greedy_q,
    "MAX_NOMINAL_GAIN (A2/RSS_MAX analogue)": pick_maxsnr,
    "LEAST_LOADED (A3 analogue)": pick_leastload,
    "GAIN_PER_LOAD": pick_maxsnr_per_load,
}

print(f"episodes per arm = {N_EP}; users={env.config.num_users} "
      f"steps/ep={env.config.steps_per_episode} actions={env.num_beams_total}")
print(f"{'arm':42s} {'r1_mean':>14s} {'r2_mean':>9s} {'r3_mean':>9s} "
      f"{'active_beams':>13s} {'served_frac':>12s}")

for name, fn in ARMS.items():
    trainer = MODQNTrainer(env, cfg, train_seed=42, env_seed=1337, mobility_seed=7)
    r1s, r2s, r3s, actives, served = [], [], [], [], []
    for ep in range(N_EP):
        states, masks, _ = env.reset(trainer._env_rng, trainer._mobility_rng)
        encoded = trainer._encode_states(states)
        ep_reward = np.zeros(3)
        for _ in range(env.config.steps_per_episode):
            actions = fn(trainer, encoded, masks, states)
            result = env.step(actions, trainer._env_rng)
            for uid in range(env.config.num_users):
                ep_reward += trainer.reward_vector_from_step_result(result, uid)
            served.append(float(np.mean([a != NO_OP_ACTION for a in actions])))
            actives.append(float(np.unique([a for a in actions if a != NO_OP_ACTION]).size))
            states = result.user_states
            encoded = trainer._encode_states(states)
            masks = result.action_masks
            if result.done:
                break
        avg = ep_reward / env.config.num_users
        r1s.append(avg[0]); r2s.append(avg[1]); r3s.append(avg[2])
    print(f"{name:42s} {np.mean(r1s):14.6e} {np.mean(r2s):9.3f} "
          f"{np.mean(r3s):9.3f} {np.mean(actives):13.2f} {np.mean(served):12.4f}")
