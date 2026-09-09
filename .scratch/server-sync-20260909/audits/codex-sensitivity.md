# How much of the coordination headroom survives if the per-chain circuit power is wrong?

`DIAGNOSTIC_NOT_CLAIM`. Budget 90 minutes. This is a rescoring, not a re-run: the configurations are already selected and recorded.

## Why
The perfect-knowledge ceiling reported **+6.359 % pooled energy efficiency over the certified unilateral optimum** across 20 real anchors, with the served count increased. Seven of ten reported anchors selected `complete-beam-evacuation` and three selected `beam-occupant-subset`.

The evacuation mechanism has value only because a beam's per-chain circuit power is saved when its last occupant leaves. An outside hardware review has now challenged both the constant and the switching assumption:

* the pair `0.338 W` per chain and `0.200 W` per satellite traces to a Ku-band hybrid-precoding simulation where `338 mW` covers only **DAC, mixer, low-pass filter and baseband amplifier**, with the power amplifier counted separately, and `200 mW` is a **baseband digital precoder**, not all shared satellite overhead;
* component evidence puts a complete ready-biased Ka transmit chain nearer **3 to 15 W**, with power-amplifier quiescent consumption alone at 2.75 to 7 W;
* more fundamentally, the fixed cost belongs to a **hardware power domain, not a logical beam**. In an active array several beams share element amplifiers, so emptying one beam need not power anything down. The implication "last user leaves the beam therefore the hardware sleeps" is **unestablished**.

So the headline number may rest on a constant with the wrong magnitude, or on a saving that does not exist at all.

## What to compute
Take the configurations the oracle already selected, recorded in `/home/sat/mcrl-v025-oracle-ws` and its report, and **rescore them** under a sweep of the per-chain circuit constant. Do not re-select and do not re-run the physics: the assignments are fixed, so only the energy accounting changes.

Sweep the per-chain term over at least `0.0`, `0.338` (current), `1.0`, `3.0`, `7.0`, `15.0` W. Independently sweep the per-satellite term over `0.0`, `0.200` (current) and `2.0` W.

**The critical case is `0.0` per chain.** That represents the architecture where beams share amplifiers and emptying one saves nothing. If the headroom survives at zero, the result does not depend on the disputed assumption at all.

## Report
1. **Pooled energy efficiency for BASELINE, UNILATERAL and ORACLE_SET at each sweep point**, and the ORACLE-over-UNILATERAL relative gain. Lead with the gain at `0.0` per chain.
2. **Decompose the current +6.359 %** into the part attributable to circuit-power savings and the part attributable to credited bits and amplifier energy. That single decomposition answers the question more directly than the sweep does.
3. **Split the result by mechanism family.** Report the ORACLE-over-UNILATERAL gain restricted to anchors whose selected coalition was `complete-beam-evacuation`, and separately for the others. The occupancy-activation mechanism depends on decode thresholds rather than circuit power and should be unaffected; confirm or refute that.
4. State the served counts at each sweep point so it stays visible that no variant buys efficiency by serving fewer users.

## Constraints
Workspace `/home/sat/mcrl-v025-sensitivity-ws`: `cp -a /home/sat/mcrl-v025-oracle-ws` once that job has finished, else build from `git -C /home/sat/mcrl-v025-codex-ws-engine archive 75c5c78c`; then `rm -rf .git`, `git init`, commit. Never modify `/home/sat/mcrl-v025-oracle-ws` or any other workspace. Never write into `/home/sat/mcrl-leo-handover` or its venv, `/home/sat/mcrl-hub`, or `/home/sat/mcrl-v025-codex-ws-engine`. Python `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`. Large files under `/home/sat/bigtmp`, never `/tmp`, a RAM-backed tmpfs here. At most 3 processes, `nice -n 12`.

**The sealed constants are not being changed.** This is a sensitivity report on a diagnostic, and `0.338` and `0.200` remain the declared values regardless of what the sweep shows. Do not alter any file under `.scratch/multi-catfish-v025-physics-successor/`, and change no threshold, sign, seed, horizon, price, service guard or acceptance rule.

Write `CIRCUIT-SENSITIVITY-2026-09-09.md` in the workspace root and print it as your final message. Lead with the ORACLE-over-UNILATERAL gain when the per-chain circuit power is zero.
