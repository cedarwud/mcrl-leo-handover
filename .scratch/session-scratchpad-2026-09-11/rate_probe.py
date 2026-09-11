import sys, time
sys.path.insert(0,"/home/u24/papers/mcrl-leo-handover/src")
import numpy as np
from mcrl.algorithms.modqn import MODQNTrainer
from mcrl.env.action_contract import NO_OP_ACTION, no_op_actions
from mcrl.runtime.trainer_spec import TrainerConfig
from mcrl.runtime.training_pipeline import make_training_environment
cfg=TrainerConfig(learning_rate=0.001, episodes=3); env=make_training_environment(users=100)
tr=MODQNTrainer(env,cfg,train_seed=42,env_seed=1337,mobility_seed=7)
t=time.time(); N=3
for ep in range(N):
    states,masks,_=env.reset(tr._env_rng,tr._mobility_rng)
    for _ in range(env.config.steps_per_episode):
        acts=no_op_actions(100)
        for uid in range(100):
            v=np.where(masks[uid].mask)[0]
            acts[uid]=int(v[int(np.argmax(states[uid].channel_quality[v]))]) if v.size else NO_OP_ACTION
        r=env.step(acts,tr._env_rng)
        for uid in range(100): tr.reward_vector_from_step_result(r,uid)
        states=r.user_states; masks=r.action_masks
        if r.done: break
d=time.time()-t
print("scripted rollout (no gradient step): %.3f s for %d episodes = %.4f s/ep"%(d,N,d/N))
print("500 demo episodes = %.1f s = %.2f min"%(d/N*500, d/N*500/60))
