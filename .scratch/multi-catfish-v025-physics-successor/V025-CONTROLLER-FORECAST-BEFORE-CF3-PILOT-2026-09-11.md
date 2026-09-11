# Controller forecast, written before any CF3 pilot result exists

Date: 2026-09-11, ~10:00Z UTC. Nothing launched yet (CF3PILOT at step 5). Written so the forecast cannot be
revised in hindsight. Owner asked: what will the result be, would a week make it better, what is not seen.

## Forecast (qualitative; no probabilities, for lack of any catfish ON/OFF data)

1. **A1 OFF beats A0 BASELINE — more likely than not.** A1 removes the `r2` handover price and trains on
   `B − eta E`; FEASFRONT showed the headroom sits in exactly that misalignment. Expected mechanism: A1 drifts
   toward high-gain behaviour with a higher handover rate; `lambda` may start binding near C-H 0.6016.
2. **A2 CF3 vs A1 OFF at the final checkpoint — most likely indistinguishable at 3 seeds x 1000 episodes.**
   Reasons: C1's source is close to what A1 learns on its own; C3's consolidation value is poorly credited
   under equal-share `E_u`; C2's head is likely inactive (`lambda` = 0).
3. **If catfish shows anything, it is most likely in learning speed** (calibration EE at episodes 100-500),
   not final EE — because demonstration/competition methods mainly help exploration, and item B below says
   exploration is not this problem's bottleneck.

Most likely declared branch: "A1 ≥ A2 — no catfish effect at pilot scale", together with "A1 > A0".

## Blind spots not previously raised

**A. Dense reward, 10-step horizon, 28 actions — demonstration methods have little to offer.** DQfD, CER,
JSRL, R2D3 and the RIS catfish are built for sparse-reward, hard-exploration problems. Here every step is
rewarded and episodes are 10 steps. The measured headroom (hysteresis rule beats the learner) is most
plausibly **objective misalignment plus trainer defects**, not an exploration deficit. **If A1 closes the gap,
catfish has nothing left to do in this problem.** This is the largest risk to the thesis as framed, and it is
structural, not a tuning matter.

**B. Per-user decisions, system-level EE — a credit-assignment problem neither catfish nor Dinkelbach fixes.**
One shared Q is applied per user; each user's action changes others' interference and beam sharing, and system
energy cannot be attributed per user with equal share. Consolidation (C3) is a coordination effect; CFSCREEN's
closed-loop probe reproduced only ~70% of it from per-user decisions.

**C. The success gate can now be met without catfish.** The owner's gate is "beat baseline MODQN". If A1 beats
A0, A2 will too — and that must **not** be read as a catfish success. Attribution is A2 vs A1 and A3 only.

**D. Higher EE may come with more handovers.** With `r2` gone, the learner may churn up to C-H, which only
limits inter-satellite handovers (intra-satellite is unconstrained). DR-2/ASK-2 put 1.42/min above the published
envelope; a referee will ask. `H_intra` must be reported beside every EE.

**E. Three seeds.** DQN seed variance is large; differences under a few percent will not resolve.

**F. My own error rate.** 29 errata in two days; this pilot's declaration had errors caught by an external
review. 13 tests pass, but tests cover what was anticipated.

## Would a week make it better?

**A week buys certainty and attribution, not effect size.** More seeds, full length, drop-one arms and better
energy credit would make the answer trustworthy. They cannot create a catfish effect if blind spot A holds. The
risk of more time is the opposite one: repeated redesign until something appears (forking paths).

## Pre-result addition (reporting only, not a gate)

Learning-speed readings: calibration-seed greedy pooled EE of every arm at episodes 100, 250, 500, 750, 1000,
and the area under that curve, reported beside the declared final-checkpoint reading. The declared reading is
unchanged.

## Addendum ~10:40Z — first progress reading, and a corrected timetable

An owner-supplied external review (`gpt4.md`) read the server workspace. Recorded facts (to be confirmed in
CF3PILOT's report): pinned-archive source premeasure — C1 112.196, C2 100.988, C3 104.190, trained 93.903,
random 51.866 Mbit/J, all sources within the former C-H and C-S; episode-100 greedy, seed 0 —
**A1 95.21 > A2 84.55 > A3 82.39 Mbit/J**. This is a progress reading and changes nothing: no new stop rule,
no design change. It is consistent with the forecast above (A2 not ahead of A1; any catfish effect, if one
exists, not visible early). `lambda = 0` and the `Q_H` term's share = 0 at episode 100, as expected.
C3 energy-contrast diagnostic: 35.8% of C3 moves change system energy by exactly 0; 59.5% within ±1% —
equal-share credit is weak, so a later null for C3 would not show that consolidation fails.

Launch-control defects found (off-by-one on the gate failure path, `DECISION.json` race, code missing from
the resume fingerprint, no process-level resume test, 5 GB cap margin at full buffers, launcher PID reuse)
are assigned to CF3PILOT before launch. **Timetable corrected**: A2/A3 run ~6.6 s/episode, so the full
pilot takes ~2-4 h after launch, not the ~1.7 h I told the owner.
