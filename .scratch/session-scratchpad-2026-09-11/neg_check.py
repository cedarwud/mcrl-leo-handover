import sys
SCRATCH=("/tmp/claude-1000/-home-u24-papers-mcrl-leo-handover/"
         "e9fba164-4724-465f-8afa-7891b4efee90/scratchpad")
sys.path.insert(0, SCRATCH)
import power_accounting_lib as P
env = P.build_env(); rec = env.environment
tr = P.MODQNTrainer(env, P.cfg, train_seed=42, env_seed=1337, mobility_seed=7)
marg = {a: [] for a in P.ACCTS}
for _ in range(2):
    states, masks, _ = env.reset(tr._env_rng, tr._mobility_rng)
    enc = tr._encode_states(states)
    for _t in range(env.config.steps_per_episode):
        a = P.arm_maxgain(tr, enc, masks, states)
        rec.capture.clear(); res = env.step(a, tr._env_rng)
        P.loo_marginals(rec.capture[0], marg)
        states = res.user_states; enc = tr._encode_states(states); masks = res.action_masks
        if res.done: break
for a in P.ACCTS:
    neg = [x for x in marg[a] if x < 0.0]
    print(f"{a:12s} n={len(marg[a])} neg={len(neg)} "
          f"min={min(marg[a]):.3e} most_neg={min(neg) if neg else 0:.3e} "
          f"neg_max_abs={max(abs(x) for x in neg) if neg else 0:.3e}")
