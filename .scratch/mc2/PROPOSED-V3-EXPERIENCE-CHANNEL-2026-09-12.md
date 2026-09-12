# `MC2-SEL-EXP-v3` — the experience / exploration channel: AUTHORISED DEV specification

**Status: authorised for DEV** by the owner ruling of 2026-09-12 15:36 Taipei
(`/home/u24/papers/mcrl-leo-handover/MCRL-v3-owner-ruling-updated-20260912-1536.md`), with the modifications below. This
file replaces the earlier proposal text of the same name (commit `a0585c21`) wherever they conflict; the earlier text is
kept in git history. Nothing here is a result: no v3 learner run existed when this was written.

## 1. Why this channel (stated within what the evidence supports)

At ep 100 and at the ep-300 depth diagnostic (`CONTROLLER-EP100-DECISION-2026-09-12.md`,
`CONTROLLER-EP300-DEPTH-READOUT-2026-09-12.md`), every judge-gated **relabelling** of the anchor's margin target sat
below the unconditional anchor (`D3-T0` 113.41 M bit/J at ep 300; v1 FULL −2.51 %, v2 FULL −4.94 %), and on identical
states the relabelled learner drifted toward the challenger by about the same amount on gate-approved and gate-rejected
rows. That **supports** poor transfer of the gate's condition to a 113-dim student; it does **not** prove the gated policy
is unrepresentable, and three points that differ in both dose and source do **not** prove the cost is independent of the
proposal's content.

v3 changes the pipe, not the sources: the anchor's loss term stays the frozen unconditional `D3-T0` margin, and the
second specialist enters through **executed experience** instead of a label. What that does and does not buy:
- it does not introduce the label-conflict mechanism measured at ep 100 — the label is T0 on the pre-step raw state, a
  deterministic function of the state, and is never overwritten;
- an unchanged anchor loss does **not** guarantee EE cannot fall — the replay distribution and the trajectory change;
- real transitions do **not** by themselves remove data-selection bias — the judge now decides which experiences are
  collected, and that is disclosed, not solved.

## 2. The mechanism (owner ruling §2 and §3, exact)

Roles unchanged: `π^A` = T0 anchor, `π^F` = T_NEXT foresight challenger, both scripted, neither an RL agent. Code
letter `B` = `π^F`.

```
per decision step t, after x = ε-greedy(S) (the learner's joint action):
    z = copy(x)                                         # x is kept unchanged for accounting
    a^F = π^F(s, ctx) for ALL users, once, at the pre-step state      (B/R abstain at t = T−1)
    g   = one planning draw for this step from the registered PLANNING stream
          (independent of the execution RNG; never previews the step's fading/shadowing)
    for u in the fixed user order recorded in the mechanism identity:           # one pass, no iteration
        if a^F[u] ≠ z[u] and κ_g((a^F[u], z_{-u})) ≻ κ_g(z):   z[u] ← a^F[u]   # vs the CURRENT z, strict
    z is now immutable
    env.step(z, execution_rng)                          # the only execution draw; all rewards / next states from z
    push (s_u, z_u, r_u, s'_u, …) with label a^A = T0(s_u)   # every outcome kept; no redraw / reselection / dropping
    (execution parity of z may be checked here, after immutability; nothing from it feeds back; planning scores are
     NOT asserted equal to execution scores)
update: L = Σ_heads TD_k + λ_E · mean_rows [ max_a (S + m·1(a ≠ a^A)) − S(s, a^A) ]     # frozen D3-T0, unchanged
```

`κ_g(z) = (n_served, B − η₀E)` evaluated with the planning draw `g` (common random numbers across the step's trials),
`η₀` fixed, strict lexicographic, ties to the incumbent. This is a **training-only sequential intervention**, not a
deployment-side coordinator; deployment is the main learner's masked argmax only. The order and the rule are part of
the mechanism identity. The planning stream uses named, deterministic domain separation, is kept separate from the
null-proposal stream, has a fixed advance-and-resume rule, and is tested for distinctness from every declared stream,
including the `default_rng((B, 0)) == default_rng(B)` alias.

## 3. Cells

Core five (the selection and confirmation matrix): `D0`; `A-only` = arm 4 `D3-T0` (unchanged); `B-only-v3` (real
substitution, **no** A loss and no dependence on A's comparison); `FULL-v3`; gated uniform-legal `B-null-v3` (same
judge, same rule, content replaced — not strictly dose-matched, and reported as such).

**`R-ungated` is a secondary mechanism analysis, not a gate** for selection, confirmation or S1 (owner ruling §5,
recorded before any v3 counted outcome). It does not block the core five. If it is ever run, its rate rule is declared
first, and matching a marginal probability is not per-state or per-step dose matching.

## 4. Seeds and readings (owner ruling §6)

- **Selection: DEV k = 18, 19**, ep 100, always `--episodes 300 --stop-after 100`, the five cells queued together.
- **Confirmation: DEV k = 12, 13, 14**, three fresh training seeds never used for selection, ep 300 fixed (no best
  checkpoint). They go to v3 because neither old version qualified at the ep-300 depth diagnostic.
- ep-100 continuation: seed-mean FULL/A-only ≥ +0.5 %; FULL/B-only and FULL/gated-null seed-means > 0; QoS floors on
  every seed; realised F substitution rate ≥ 1 % per seed, denominator = all legal user-steps including the last step.
- ep-300 confirmation: FULL vs each drop-one and vs strong T0 (here the same cell, `D3-T0`) seed-mean ≥ +1.0 % with
  ≥ 2/3 seeds positive; gated-null seed-mean > 0 with ≥ 2/3 positive; per seed served drop ≤ 0.5 pp, p10 ≥ 0.5 × D0,
  bits ≥ 0.95 × D0. A DEV screen, not a significance guarantee. No v4, no weight sweep.

## 5. Tested / untested (updated by the controller as lanes report)

| item | status |
|---|---|
| sequential single-pass substitution (lane A) | implementation in progress, uncommitted WIP being moved to its own worktree |
| planning / execution RNG separation (lane A) | required change, not yet implemented at the time of writing |
| replay format + executed-action pairing (lane A) | in the WIP; tests pending |
| owner's required tests (§4 of the ruling) | pending, to run on sat |
| lane B seam check | pending lane A's commit |
| formal-driver wiring (lane E) | pending lane A's commit |
| any v3 learner result | **none** |
