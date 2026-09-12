# v3 handover for the paper / deck editor — minimal, per the owner ruling of 2026-09-12 15:36 §8

The editor owns the paper, symbols, deck and figures (`.scratch/multi-catfish-v025-paper-lane-20260909/CURRENT-PAPER-DECK-OUTPUTS.md`);
this file does not touch any editor document. It gives exactly four things.

## 1. Mechanism ID

`MC2-SEL-EXP-v3` — the experience / exploration channel. Authorised for DEV; **not validated; no v3 learner result exists.**
v1 `MC2-JGO-v1` and v2 `MC2-ARB-v2` (judge-gated relabelling) failed the ep-100 selection and the ep-300 depth diagnostic.

## 2. Shortest pseudocode

```
per step: x = learner ε-greedy joint action; z = copy(x); a^F = π^F(s) for all users (once; abstain at last step)
          g = one planning draw (independent of the execution RNG)
          for u in fixed order (one pass):  if a^F[u] ≠ z[u] and κ_g(a^F[u], z_{-u}) ≻ κ_g(z): z[u] = a^F[u]
          env.step(z) once; store (s, z, real reward, real next state); label = T0(s)   (anchor label never overwritten)
loss:     TD + frozen D3-T0 large margin toward a^A = T0(s)
deploy:   the main learner's masked argmax only (no specialist, no judge)
κ = (served count, B − η₀E): a fixed-price training surrogate, not EE.
```

## 3. Tested / untested — see the live table

`/home/u24/papers/mcrl-leo-handover-mc2/.scratch/mc2/PROPOSED-V3-EXPERIENCE-CHANNEL-2026-09-12.md` §5 (updated by the
controller as lanes report). At the time of writing: implementation in progress; required tests pending; nothing counted.

## 4. Controller readout locations (the only sources for any v3 number)

- ep-100 selection of v1/v2 (neither qualified): `/home/u24/papers/mcrl-leo-handover-mc2/.scratch/mc2/CONTROLLER-EP100-DECISION-2026-09-12.md`
- ep-300 depth diagnostic of v1/v2 (neither qualified): `…/.scratch/mc2/CONTROLLER-EP300-DEPTH-READOUT-2026-09-12.md`
- non-learned judge probe (rule level): `…/.scratch/mc2/CONTROLLER-PROBE-READOUT-2026-09-12.md`
- v3 ep-100 selection and ep-300 confirmation readouts will be written beside these, as
  `CONTROLLER-V3-EP100-READOUT-*.md` and `CONTROLLER-V3-EP300-CONFIRMATION-*.md`. **Until those exist, nothing about v3
  may be written as successful.**
