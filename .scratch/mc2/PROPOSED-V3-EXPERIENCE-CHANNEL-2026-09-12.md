# PROPOSED third version `MC2-SEL-EXP-v3` — the experience / exploration channel

Date 2026-09-12. **Proposal only. Not authorised, not implemented, nothing launched.** A third mechanism version is an
owner decision (contract r2 allows two). This file exists so that an authorisation costs minutes, not an hour of design.
Written before the depth diagnostic (the ep-300 extension of the selection seeds) is read, so it cannot be tuned to it.

## 1. Why this channel and not another patch of the old one

ep-100 measured (`CONTROLLER-EP100-DECISION-2026-09-12.md`): replacing the anchor's label costs about as much as the
replacement rate and is indifferent to the replacement's content — `D3-T0` 112.98 at 0 % override, `v1 B-null` 110.33 at
17.6 % (content-free proposals), `v1 FULL` 109.85 at 30.3 % (`T_NEXT`'s proposals), with FULL-vs-its-own-null at
−0.43 % seed-mean, i.e. inside seed noise. Meanwhile the same judge arbitrating the same two specialists as a **rule**
is +6.13 % over T0 (24/24 paired, non-learned), and `B-only` alone is +7.6 % over `D0`. Read together: the source has
information, the arbitration is a better rule, and the **label** is the wrong pipe.

The channel below never touches the anchor's label. `A`'s loss term stays the frozen unconditional `D3-T0` margin, so the
only difference from `D3-T0` is **which transitions are in the replay**, and the measured damage mechanism is absent by
construction.

## 2. The mechanism

Roles unchanged (contract §1): `π^A` = T0 anchor, `π^F` = T_NEXT foresight challenger, both scripted, neither an RL agent.
Judge unchanged (§2): `κ_u(a) = (n_served, B − η₀E)` on `evaluate_actions((a, x_{-u}), deepcopy(env_rng))`, strict
lexicographic, ties to the incumbent, fixed `η₀`, training-only, ≤ 3 proposals.

```
for each decision step t, after x = ε-greedy(S) and before env.step:
    a^F = π^F(s_u, ctx)  if t < T−1  else ABSTAIN          # challenger source (a^R for the null cell)
    for each user u with a legal action:
        if challenger enabled and a^F ≠ x_u and κ_u(a^F) ≻ κ_u(x_u):
            x_u ← a^F                                       # EXECUTED, not a label
            mark row as B-executed
    env.step(x)                                             # one step, the real joint action
    push (s_u, x_u, r_u, s'_u, …) + the anchor's label a^A   # the transition is the executed one
update: L = Σ_heads TD_k + λ_E · (1/|batch|) Σ_rows [ max_a(S + m·1(a ≠ a^A)) − S(s, a^A) ]      # unchanged D3-T0
```

Dose: **every judge-approved substitution is executed** (ρ = 1). Reason, so that no new constant enters: the gate already
restricts to the states where the challenger strictly beats what the learner was about to do on the same state and the
same other-user actions — that *is* CDRL's "high-value stimulus" selection; throttling it would add an unjustified
coefficient. The realised substitution rate is then a measured quantity (≈ 30 % of decision rows at a trained anchor
background, ≈ 39 % under ε ≈ 1, from the controller probe), not a tuned one.

Two properties worth stating because they are structural, not hoped for:
- **Service cannot be damaged by a substitution at the step level**: `κ`'s first component is the system served count and
  the comparison is strict, so a substitution never takes a candidate that serves fewer users than the action it replaces.
- **The label-noise mechanism measured at ep 100 cannot appear**: the target is always `a^A`, a deterministic function of
  the raw state, so two identical observations always carry the same label.

What replaces it as the risk, declared now: the judge's privileged information (step-`t` fading, the other users'
executed actions) now selects **which experiences are collected** instead of what the label says. Label noise is gone; a
**data-selection bias** takes its place, and the comparison against `D3-T0` is no longer a same-trajectory comparison —
the executed joint action, and therefore the env RNG path and the state distribution, differ. That is inherent to any
exploration intervention and is why the two nulls below exist.

## 3. Cells (6 × 2 selection seeds = 12 runs, ep 100)

| cell | anchor label | what is executed | what it answers |
|---|---|---|---|
| `D0` | none | learner's ε-greedy | the no-Catfish floor, rerun under the new code identity |
| `A-only` = `D3-T0` | unconditional | learner's ε-greedy | the strong single Catfish; **identical to arm 4 by construction** |
| `FULL-v3` | unconditional | ε-greedy + every judge-approved `a^F` | the round's claim |
| `B-null-v3` | unconditional | ε-greedy + every judge-approved **uniform legal** proposal | is it `π^F`'s content, or any judge-approved deviation? |
| `B-only-v3` | **none** | ε-greedy + every judge-approved `a^F` | the retrained drop-one of A |
| `R-ungated` | unconditional | ε-greedy + a uniform legal action at the **measured substitution rate of `FULL-v3`**, no judge | is it the judge's selection, or just more exploration at that rate? |

`R-ungated`'s rate is frozen from `FULL-v3`'s realised rate before `R-ungated` runs (one number, declared, exactly as the
k = 8 Bernoulli null froze `p_singleton`), and it is the first dose-matched null this round would have.

## 4. Readings (same shape as r2 §7, so nothing is chosen after the fact)

Estimand unchanged: seed-wise relative pooled EE on the 24 DEVVAL episodes. Qualification at ep 100 on the selection
seeds k = 10, 11: (i) seed-mean `FULL-v3` vs `A-only` ≥ +0.5 % — which for v3 is also the comparison against `D3-T0`,
so r2's clause (ii) collapses into (i); (iii) vs `B-only-v3` > 0; (iv) vs `B-null-v3` > 0; (iv-b) vs `R-ungated` > 0;
(v) per-seed QoS floors against same-seed `D0`; (vi) substitution rate ≥ 1 % of decision rows per seed. Confirmation at
ep 300 on the **fresh** seeds k = 12, 13, 14 under the owner's unrelaxed gate (≥ +1.0 % with ≥ 2/3 seeds positive on each
drop-one, nulls positive, QoS floors per seed). Reported beside: substitution counts and rates, the realised reward of
substituted steps, the share of sampled batch rows that are B-executed, bits / joules / served / p10 against `D3-T0`,
and the DEVVAL greedy agreement with `a^A` and `a^F`.

## 5. Cost

Implementation ≈ 1 h (the judge, the sources, the logging and the launcher all exist; this adds a substitution point in
the collection loop, one tag, one null and one ungated null). ep 100: 12 runs, the judge-bearing ones ≈ 17–25 min each,
so ≈ 40 min wall at the 8-worker cap. ep 300 confirmation on three fresh seeds: 15–18 runs, ≈ 1.5–2 h. Formal S1 after
that is unchanged in shape (lane E's port is already built for a parameterised mechanism id).

## 6. What would make me withdraw this proposal

If the depth diagnostic shows the ep-100 shortfall against `D3-T0` **inverting** by ep 300 on both selection seeds, then
the label channel is not closed after all and the right next step is a fresh-seed confirmation of v2 (or v1), not a third
version. That reading is fixed in `CONTROLLER-EP100-DECISION-2026-09-12.md` §5 and is due ≈ 08:00Z.
