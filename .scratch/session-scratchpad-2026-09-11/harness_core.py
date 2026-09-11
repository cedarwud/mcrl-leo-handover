def preds(states):
    n = len(states)
    r1 = np.zeros((n, 28)); r2 = np.zeros((n, 28)); r3 = np.zeros((n, 28))
    for u, s in enumerate(states):
        load = np.asarray(s.beam_loads, dtype=np.float64)
        sinr = np.maximum(np.asarray(s.channel_quality, dtype=np.float64), 0.0)
        r1[u] = (B / (load + 1.0)) * np.log2(1.0 + sinr)
        r3[u] = -(load + 1.0)
        inc = np.flatnonzero(np.asarray(s.access_vector) > 0.5)
        if inc.size == 0:
            r2[u] = -PHI2
        else:
            i = int(inc[0]); ls = i // NUM_BEAM_SLOTS
            row = np.full(28, -PHI2)
            row[ls * NUM_BEAM_SLOTS:(ls + 1) * NUM_BEAM_SLOTS] = -PHI1
            row[i] = 0.0
            r2[u] = row
    return r1, r2, r3


def argmax_masked(score, masks):
    out = no_op_actions(len(masks))
    for u in range(len(masks)):
        v = np.where(masks[u].mask)[0]
        out[u] = int(v[int(np.argmax(score[u][v]))]) if v.size else NO_OP_ACTION
    return out


def scalar_arm(use_r2=True, use_r3=True):
    def pick(tr, enc, masks, states):
        r1, r2, r3 = preds(states)
        s = W[0] * KAPPA * r1
        if use_r2:
            s = s + W[1] * (r2 / SC[1])
        if use_r3:
            s = s + W[2] * (r3 / SC[2])
        return argmax_masked(s, masks)
    return pick


def arm_maxgain(tr, enc, masks, states):
    return argmax_masked([s.channel_quality for s in states], masks)


def arm_random(tr, enc, masks, states):
    return tr.select_actions(enc, masks, 1.0)


def arm_trained(tr, enc, masks, states):
    return tr.select_actions(enc, masks, 0.0)          # deployed = greedy


def run(fn, load_ckpt=False):
    tr = MODQNTrainer(env, cfg, train_seed=42, env_seed=1337, mobility_seed=7)
    if load_ckpt:
        tr.load_checkpoint(CKPT, load_optimizers=False)
    bits = 0.0; joules = 0.0
    served = 0; usersteps = 0; ho = 0
    per_ep_scalar = []
    per_ep_ee = []
    for _ in range(N_EP):
        states, masks, _ = env.reset(tr._env_rng, tr._mobility_rng)
        enc = tr._encode_states(states)
        r = np.zeros(3); eb = 0.0; ej = 0.0
        for _t in range(T):
            a = fn(tr, enc, masks, states)
            res = env.step(a, tr._env_rng)
            e = env.last_outcome.energy
            eb += float(e.system_throughput_bps) * DT
            ej += float(e.system_consumed_power_w) * DT
            served += int(e.served)
            for uid in range(U):
                r += tr.reward_vector_from_step_result(res, uid)
                usersteps += 1
                if res.rewards[uid].r2_handover < 0:
                    ho += 1
            states = res.user_states
            enc = tr._encode_states(states)
            masks = res.action_masks
            if res.done:
                break
        bits += eb; joules += ej
        avg = r / U
        per_ep_scalar.append(sum(W[i] * avg[i] / SC[i] for i in range(3)))
        per_ep_ee.append(eb / ej if ej > 0 else float("nan"))
    return dict(bits=bits, joules=joules, ee=bits / joules,
                served_rate=served / usersteps, ho_rate=ho / usersteps,
                scalar=st.mean(per_ep_scalar),
                scalar_sem=st.pstdev(per_ep_scalar) / len(per_ep_scalar) ** 0.5,
                ee_ep=per_ep_ee)

