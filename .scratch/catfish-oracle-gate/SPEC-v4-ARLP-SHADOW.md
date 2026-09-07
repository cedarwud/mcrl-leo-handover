# Frozen v4 activation-regularised load-potential shadow gate

Status: frozen before implementing the formal runner, running an engineering
pilot, or reading any outcome from the new evaluation seeds. Evaluation only;
this does not modify the runtime reward, train a policy, or authorise a
deployment-time selector.

Date: 2026-08-26

## Ruling carried forward

The v3.1 held-out result is final: the previous-inactive split opportunity
exists, but the fixed Q-head-shaped scorer failed state sufficiency. The old
split endpoint is also descriptively adverse to immediate EE. This v4 gate is
a new reward/proposal hypothesis and may not rescue or relabel v3.1.

## Candidate R3 role

R3 becomes an **activation-regularised spatial load-potential Catfish**. It
does not use throughput, EE, Q1 values, another user's simultaneous action, or
post-action acceptance. Its system cost is

```text
C3 = sum_b U_b^2 / c_U + B_active
c_U = 6
```

where `U_b` is the served load of physical beam `(norad_id, cell_id)` and
`B_active` is the number of served/radiating physical beams. `c_U=6` is the
already-frozen P3 p95 load scale, fixed before the v2/v3 outcome labels.

One active beam is one activation unit. Its physical anchor is the analytic
minimum consumed power of a beam at segment start:

```text
p0 = 0.825 W
PA supply at p0 = 5.927900454219554 W
P_cir = 0.338 W
P_on,min = 6.265900454219554 W
```

The once-per-active-satellite `P_BB=0.200 W` and power above segment start are
reported as an unmodelled residual in this first gate. They are not silently
claimed by `B_active`.

The proposed served-user reward is the negative difference reward

```text
r3_ARLP,u = -[(2 U_bu - 1)/c_U + I{U_bu = 1}].
```

It must satisfy, exactly,

```text
-r3_ARLP,u = C3(all served users) - C3(all except u).
```

This gives focal credit for its marginal congestion and beam activation. The
population sum of these difference rewards is not `-C3` and must never be
reported as such. The reward uses the joint post-action load only inside the
environment reward calculation; it is not a pre-action coordinator.

## Outcome-blind focal proposal

For each valid focal physical candidate `a`, use only the live focal
observation available before any current-slot outcome:

- action mask;
- access vector (to identify a visible incumbent);
- previous demand for the candidate physical beam;
- candidate SINR for deterministic tie-breaking.

Let `n_a` be the candidate's previous demand excluding the focal user when
`a` is its visible incumbent, otherwise the unchanged previous demand. The
projected marginal cost is

```text
m3(a) = (2 n_a + 1)/6 + I{n_a = 0}.
```

Choose the physical candidate with the lexicographically smallest
`(m3(a), -candidate_sinr, action_index)`. Duplicate physical keys are
forbidden. Q1 is not an input to this choice.

After the proposal is frozen, compute the checkpoint Q1-only reference. A row
is eligible only when the proposal physical key differs from the reference
physical key. This comparison defines an intervention, not the proposal.
Ineligible rows are retained and never replaced.

At each eligible state, independently draw one matched-random valid physical
candidate whose key differs from the Q1 reference. The draw uses a dedicated
frozen control RNG and is completed before any outcome. It may equal the ARLP
proposal; retaining that possibility makes the comparator conservative and
keeps its sampling rule uniform.

## Frozen collection

- Checkpoint: the same episode-8999 receipt used by v2/v3, SHA-256
  `e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b`.
- New untouched seeds: `2026082601` through `2026082610`.
- 100 users, ten steps, ten data-blind focal users per step without
  replacement: 1,000 sampled rows.
- Reference: masked-greedy Q1-only joint action.
- ARLP and random alternatives change exactly the same one focal physical
  action; every other user retains the reference action.
- Reference, ARLP, and random actions are evaluated from the same pre-decision
  environment and common RNG. Only the Q1 reference commits.
- No outcome sign, reward, EE, service result, or current other-user intent may
  affect eligibility, proposal choice, random control, or row retention.

## Reported endpoints

For all sampled and eligible rows, and per evaluation seed, report:

1. coverage and proposal/random action identities;
2. realised `C3`, `sum_b U_b^2`, physical active beams, and active satellites;
3. system EE, throughput, consumed power, service count, focal service, and
   common-random-number EE identities for ARLP and random versus reference;
4. paired ARLP-minus-random differences in EE, throughput, power, and `C3`;
5. service-unsafe rates, where unsafe means fewer served users than reference
   or the focal user becomes unserved;
6. seed-clustered descriptive t95 intervals using the ten seed means and
   `t_0.975,9=2.2621571628540993`.

## Frozen pass rule

The v4 shadow gate passes only if every condition holds:

1. engineering/replay checks pass and at least 100/1,000 rows are eligible,
   with at least five eligible rows in every seed;
2. realised `reference_C3 - ARLP_C3` has positive pooled mean, positive mean
   in at least 8/10 seeds, and a seed-t95 lower endpoint above zero;
3. ARLP-versus-reference DeltaEE has positive pooled mean, positive mean in at
   least 8/10 seeds, and a seed-t95 lower endpoint above zero;
4. paired `EE_ARLP - EE_random` has positive pooled mean, positive mean in at
   least 8/10 seeds, and a seed-t95 lower endpoint above zero;
5. ARLP service-unsafe rate is at most 1% and no more than random's unsafe
   rate plus 0.5 percentage point.

No borderline rescue, alternate coefficient, alternate proposal, threshold
sweep, or subgroup selection is allowed after the new outcomes are read.

## Decision boundary

- Pass: advance only to an implementation/state audit of `r3_ARLP` and a
  separately frozen short RL pilot. It does not prove learnability,
  composition, long-horizon benefit, or final three-Catfish effectiveness.
- Fail: drop this independent R3-to-EE direction. Do not run R3 reward training
  or try another candidate on these seeds. A three-role design then remains
  blocked unless a materially different, newly justified R3 mechanism is
  preregistered and tested on another untouched seed set.
