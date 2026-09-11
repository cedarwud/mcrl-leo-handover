import sys
SC="/tmp/claude-1000/-home-u24-papers-mcrl-leo-handover/e9fba164-4724-465f-8afa-7891b4efee90/scratchpad"
sys.path.insert(0,"/home/u24/papers/mcrl-leo-handover/src"); sys.path.insert(0,SC)
import numpy as np
from c3s_physics_override import DiagnosticStepEnvironment, get_physics_override
from mcrl.algorithms.modqn import MODQNTrainer
from mcrl.env.action_contract import NO_OP_ACTION, no_op_actions
from mcrl.env.link_budget import SEGMENT_START_POWER_W
from mcrl.runtime.trainer_spec import TrainerConfig
from mcrl.runtime.training_pipeline import make_training_environment
print("SEGMENT_START_POWER_W =", SEGMENT_START_POWER_W)
cfg=TrainerConfig(learning_rate=0.001, episodes=1)
def mg(tr,enc,masks,states):
    out=no_op_actions(len(masks))
    for u in range(len(masks)):
        v=np.where(masks[u].mask)[0]
        out[u]=int(v[int(np.argmax(states[u].channel_quality[v]))]) if v.size else NO_OP_ACTION
    return out
def trained(tr,enc,masks,states): return tr.select_actions(enc,masks,0.0)
for ov in ("none","ablate_anchor"):
    for nm,fn,ck in (("MAX_NOMINAL_GAIN",mg,False),("TRAINED",trained,True)):
        e=make_training_environment(users=100)
        e.environment=DiagnosticStepEnvironment.construct(e.environment.driver,
            physics_override=get_physics_override(ov))
        tr=MODQNTrainer(e,cfg,train_seed=42,env_seed=1337,mobility_seed=7)
        if ck: tr.load_checkpoint("/home/u24/papers/mcrl-leo-handover/artifacts/training-2026-08-25-rerun01/main/final-checkpoint.pt", load_optimizers=False)
        s,m,_=e.reset(tr._env_rng,tr._mobility_rng); enc=tr._encode_states(s)
        vals=[]
        for t in range(3):
            a=fn(tr,enc,m,s); r=e.step(a,tr._env_rng); o=e.last_outcome
            served=o.resolution.served
            lp=np.asarray(o.link_power_w)[served]
            vals.append((t,len(lp),float(lp.min()),float(lp.max()),float(np.mean(np.abs(lp-SEGMENT_START_POWER_W)<1e-12))))
            s=r.user_states; enc=tr._encode_states(s); m=r.action_masks
        print(f"{ov:14s} {nm:18s} " + " | ".join(
            f"t{t}: n={n} p in [{lo:.4f},{hi:.4f}] frac_at_p0={fr:.3f}" for t,n,lo,hi,fr in vals))
