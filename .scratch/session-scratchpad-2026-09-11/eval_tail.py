# ---- HARNESS-CORE END ----


def _driver(argv):
    global CKPT
    arms = []
    if "--random" in argv:
        arms.append(("RANDOM_MASKED (harness check)", arm_random, None))
    for item in argv:
        if item.startswith("--"):
            continue
        label, _, path = item.partition("=")
        arms.append((label, arm_trained, path))
    t0 = time.time()
    print(f"# N_EP={N_EP}/arm, seeds 42/1337/7, dt={DT} s, no update() call; "
          f"estimand sum(bits)/sum(joules) divided once", flush=True)
    for label, fn, path in arms:
        CKPT = path
        t_arm = time.time()
        o = run(fn, load_ckpt=path is not None)
        ee_ep = o.pop("ee_ep")
        o.update(
            label=label,
            checkpoint=path,
            ee_ep_mean=st.mean(ee_ep),
            ee_ep_sd=st.pstdev(ee_ep),
            ee_ep_sem=st.pstdev(ee_ep) / len(ee_ep) ** 0.5,
            n_episodes=len(ee_ep),
            wall_s=time.time() - t_arm,
        )
        print("RESULT " + json.dumps(o, sort_keys=True), flush=True)
    print(f"# total wall {time.time() - t0:.1f} s", flush=True)


if __name__ == "__main__":
    _driver(sys.argv[1:])
