"""Mean fixed (hardware) power share, 3 episodes, MAX_NOMINAL_GAIN + TRAINED.
Read-only; reuses power_accounting.py's recorder unchanged."""
import sys
SCRATCH = ("/tmp/claude-1000/-home-u24-papers-mcrl-leo-handover/"
           "e9fba164-4724-465f-8afa-7891b4efee90/scratchpad")
sys.path.insert(0, SCRATCH)
sys.argv = ["x", "0"]
import power_accounting_lib as P

import statistics as st
for name, fn, ck in [("MAX_NOMINAL_GAIN", P.arm_maxgain, False),
                     ("TRAINED e6b063ef", P.arm_trained, True)]:
    env = P.build_env(); rec = env.environment
    tr = P.MODQNTrainer(env, P.cfg, train_seed=42, env_seed=1337, mobility_seed=7)
    if ck:
        tr.load_checkpoint(P.CKPT, load_optimizers=False)
    fixed = []; tot = {a: [] for a in P.ACCTS}
    for _ in range(3):
        states, masks, _ = env.reset(tr._env_rng, tr._mobility_rng)
        enc = tr._encode_states(states)
        for _t in range(env.config.steps_per_episode):
            a = fn(tr, enc, masks, states)
            rec.capture.clear()
            res = env.step(a, tr._env_rng)
            c = rec.capture[0]
            fixed.append(c["fixed"])
            for acct in P.ACCTS:
                tot[acct].append(c["totals"][acct])
            states = res.user_states; enc = tr._encode_states(states)
            masks = res.action_masks
            if res.done:
                break
    mf = st.mean(fixed)
    print(f"{name}: mean fixed P^f = {mf:.4f} W")
    for acct in P.ACCTS:
        mt = st.mean(tot[acct])
        print(f"   {acct:12s} mean P^N {mt:9.4f} W  fixed share {100*mf/mt:5.2f}%  "
              f"PA share {100*(1-mf/mt):5.2f}%")
