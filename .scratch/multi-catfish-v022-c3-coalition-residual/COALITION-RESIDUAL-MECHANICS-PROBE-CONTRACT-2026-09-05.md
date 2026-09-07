# V0.22 C3 two-user coalition-residual mechanics probe contract

Date: 2026-09-05  
Status: **PRE-OUTCOME FROZEN CANDIDATE / TRAIN-DEVELOPMENT ONLY**

Claim ceiling: one topology-selected two-user current-slot formula and native
composition falsifier.  No efficacy, no learner, no source promotion, no
episode training, and no TEST split.

## 1. Question

Can a predeclared two-user spatial proposal expose a real public-good beam
shutdown interaction, reconstruct its joint current-slot EE surplus with a
two-player residual/Shapley identity, and survive the unchanged row-wise
`Q1+Q2+Q3` masked argmax without a deployment coordinator?

## 2. Frozen inputs

- Split: `TRAIN_DEVELOPMENT` only.
- Fresh ordered world candidates: `2026121701`, `2026121702`,
  `2026121703`, `2026121704`.
- Repriced lineage: `2026092101` with its already authenticated combined
  Q1/Q2 checkpoint.
- Fading component: `MCRL_V022_C3_COALITION_RESIDUAL_V1`, keyed by world.
- Candidate anchors: noninitial `t = 1,...,9` only.
- Multiplier: `lambda = 0x1.c3c0a7b6b86d3p+26` bit/J.
- Normalization: `kappa = 0x1.2cea89d260f2ap+33` bit.
- Interval: the canonical decision interval from the environment.
- All profiles at the selected anchor use the same frozen keyed field and
  non-advancing `evaluate_actions()` calls.

Worlds, anchors, or fields may not be replaced after an outcome is opened.

## 3. Outcome-blind topology proposal

For each world, follow the literal repriced learned `Q1+Q2` policy from the
initial anchor.  At each noninitial anchor:

1. Compute the native mask, Q1 surface, provisional OPS-3 state carrier, learned
   Q2 surface, and reference `x0 = argmax(Q1+Q2)` exactly as in V0.20.
2. Map every reference action to its physical `(NORAD, cell)` key using only
   the current candidate table.  A reference action contributes to the
   topology only when the predecision opening-service predicate is true.
3. A source key qualifies only when exactly two reference users select it.
4. For each of those two users, legal destination actions are restricted to
   predecision-opening-feasible actions on a different key that is already
   occupied by at least one reference user outside the pair.  No new
   destination beam is proposed.
5. Each member's destination is the highest `Q1+Q2` action within that fixed
   set; ties use the native lowest action index.
6. Choose the lexicographically first qualifying source key at the earliest
   qualifying anchor in the earliest world.  Candidate outcomes, bits, energy,
   and service may not enter this selection.

If none of the four worlds contains a qualifying pair, stop with
`NO_QUALIFIED_PAIR_CASE`.  That is an inconclusive topology result, not a
negative mechanism result.

## 4. Four fixed physical profiles

For ordered pair members `u1 < u2`, evaluate exactly:

- `00`: reference `x0`;
- `10`: only `u1` takes its proposed destination;
- `01`: only `u2` takes its proposed destination;
- `11`: both users take their proposed destinations (`xC`).

No profile may change any other user's action.  Record per-user bits, total
energy, served vector, active beam keys, active satellites, RF power, and
ratio-of-sums EE.  All four evaluations must leave live state and RNG
unchanged.

## 5. Frozen formula

Use current-slot per-user delivered bits `B_v(x)` and energy `E(x)`:

```text
G(x) = sum_v B_v(x) - lambda E(x)
l_i  = B_ui(xi) - B_ui(00) - lambda [E(xi) - E(00)]
e_i  = sum_{v != ui} [B_v(xi) - B_v(00)]
d_i  = l_i + e_i
Psi_B = [sum_v B_v(11) - sum_v B_v(00)]
        - sum_i [sum_v B_v(xi) - sum_v B_v(00)]
Psi_E = [E(11) - E(00)] - sum_i [E(xi) - E(00)]
Psi   = Psi_B - lambda Psi_E
z3_i  = e_i + Psi / 2
```

Here `x1=10` and `x2=01`.  The result must verify

```text
sum_i (l_i + z3_i) = G(11) - G(00)
```

to a floating-point tolerance derived from the magnitudes of its terms.
`z3_i/kappa` is written only to member `ui`'s proposed action.  Reference,
illegal, nonmember, and every other action cell is exactly zero.

## 6. Literal deployment-composition diagnostic

Without fitting a Q3 network, form the sparse oracle surface above and compute

```text
x* = masked_argmax(Q1 + Q2 + z3/kappa)
```

once.  There is no iterative allocation, re-proposal, threshold, fallback,
joint decoder, or post-selection repair.  Record whether `x*` is exactly `11`,
`10`, `01`, or neither, and evaluate `x*` under the same keyed field.

## 7. Required mechanics and physical signature

All of the following must hold for a mechanics pass:

1. contract, runner, Q1/Q2 checkpoint, preregistration, and TLE identities are
   authenticated;
2. the topology proposal follows Section 3 without reading candidate outcomes;
3. `00`, `10`, and `01` keep the named source beam active;
4. `11` removes that source beam, opens no new beam, and reduces the active
   beam count by exactly one;
5. both pair members are served in all four profiles, and total served users in
   `11` are not below `00`;
6. all values are finite and the Section 5 identity passes;
7. live state, networks, and RNG are unchanged by all counterfactual work;
8. the sparse Q3 surface has exact reference/illegal/other-action zeros.

The ratio check is an evaluation condition, not a target redefinition:

```text
EE(11) > EE(00)
```

and its sign must agree with

```text
[B(11)-B(00)] - EE(00)[E(11)-E(00)] > 0.
```

The training target continues to use the frozen `lambda`, not `EE(00)`.

## 8. Decisions

`GO_LC_SRS_OBSERVABILITY_GATE` requires all Section 7 mechanics, positive
`EE(11)-EE(00)`, and literal composition selecting the complete `11` profile.
It authorizes only a separate causal-state/observability contract and a local
coalition-Shapley source design.  It does not authorize a learner or episode
training.

`REDESIGN_COALITION_INTERFACE` applies when the physical signature and joint EE
gain pass but literal composition adopts only part of the pair or otherwise
does not select `11`.  No allocation may be tuned against this outcome.

`STOP_THIS_COALITION_PROPOSAL` applies when a qualified topology proposal fails
the required public-good signature, service guard, identity, or joint EE sign.
This stops the fixed proposal; it does not prove every coalition C3 impossible.

`NO_QUALIFIED_PAIR_CASE` is defined in Section 3.

No result from this probe permits 100, 500, 1500, 3000, or 9000 episode
training.  Any next stage needs a new pre-outcome contract.

