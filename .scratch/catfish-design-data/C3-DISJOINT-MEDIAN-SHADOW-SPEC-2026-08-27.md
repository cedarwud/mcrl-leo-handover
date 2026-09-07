# Frozen disjoint-seed C3 median-guard shadow campaign

Status: frozen before implementing the dedicated runner or reading any listed
seed. New non-training hypothesis authorised only by the Fable Max
`PASS_TO_NEXT_SHADOW` review. Legacy-narrow sensitivity; no reward, runtime,
Main-transfer, manuscript, or training authority.

Date: 2026-08-27

## Disclosure carried forward

The original median-development protocol permanently decided
`REJECT_MEDIAN_RATE_RULE` because its selected rows had negative mean realised
throughput. This campaign does not overturn or relabel that result. It registers
the unchanged median rule as a new hypothesis with a different claim:

- primary: conditional time-accounted EE;
- throughput: descriptive only, with no margin and no non-inferiority claim;
- `E_HO`: unresolved and never assigned a value.

The median rule was the third guard examined on the one-seed development pool
and selected exactly its five immediate-EE-positive rows. That multiplicity and
selection history remain attached to every result.

## Frozen inputs

- Completed legacy Main checkpoint and preregistration already used by the v1
  C3 shadow, with their existing SHA receipts.
- Five disjoint evaluation seeds: `2026082801` through `2026082805`.
- 100 users, ten steps, every user-step censused: 5,000 focal opportunities.
- Main reference: masked-greedy Q1-only joint action.
- No fitting, RL update, parameter sweep, threshold, margin, or subgroup
  selection.

## Power support and unchanged median guard

The source/candidate conditions are exactly those in the frozen v1
intra-satellite shadow:

1. reference is a served continuing incumbent with class `NONE`;
2. source load is at least two and focal is its strict unique power maximum;
3. candidate is a valid different cell on the same satellite with class
   `phi1`, and its destination is already active;
4. candidate is service-feasible, does not exceed the destination maximum, and
   changes no non-focal action/link power or served/active set; and
5. the strict PA identity certifies `Delta P_system < 0`.

Eligibility uses a training-only branch with Rician power gain fixed to one and
shadow loss fixed to zero dB. This branch reads no realised fading, rate,
reward, EE, or successor. The candidate survives the unchanged median guard iff

```text
R_median(candidate) - R_median(reference) >= 0.
```

For a focal state with multiple survivors, select the largest certified power
reduction, then the lexicographically smallest physical `(norad, cell, action)`
identifier. This selection is fixed before any realised outcome. Ineligible
and guard-rejected rows are retained in receipts and never replaced.

## Paired short-window evaluation

For each selected proposal, clone the complete pre-state and both environment
and mobility RNG states. Branch A executes the Main reference; branch B changes
only the focal action. Thereafter each branch independently executes the frozen
Q1-only Main policy for at most two additional intervals. The paired horizon is
`min(3, remaining episode intervals)`; no further Catfish action occurs.

Both branches start from identical RNG states. Report when divergent candidate
sets/actions prevent an exact draw-by-draw common-random-number interpretation;
do not silently claim CRN beyond the cloned streams.

For each branch and interval, with decision interval `Delta=30.08 s`, record:

```text
B_nominal = Delta * sum_u R_u
E_payload = Delta * P_system
L_phi1    = sum_{u: class phi1} R_u
L_phi2    = sum_{u: class phi2} R_u
N_phi1, N_phi2
```

The parameter-free temporal surface is

```text
eta(T1,T2,E1,E2)
  = [sum B_nominal - T1*sum L_phi1 - T2*sum L_phi2]
    / [sum E_payload + E1*sum N_phi1 + E2*sum N_phi2].
```

No `E1/E2` is instantiated. As a disclosed, non-primary sensitivity only,
evaluate the current provenance-matrix timing proxy `T1=0.062 s`,
`T2=0.142 s`, `E1=E2=0`. Also report nominal EE, cumulative payload-energy
saving, event-count differences, and the net additional-event energy budget

```text
E_extra_star = B_time,candidate / eta_time,reference - E_payload,candidate.
```

`E_extra_star` is a break-even ledger quantity, not an `E_HO` estimate.

## State/alias logging

Save every Main 112-D user observation with seed, step, user, reference action,
and labels for source-qualified, power-certified, guard-retained, selected,
realised immediate EE sign, and focal marginal-power reward. The observation
artifact is separate and hashed. This campaign does not decide Main transfer;
it only supplies the frozen data for a subsequent collision and leave-one-seed-
out 1-NN/permutation audit.

## Frozen engineering and advance rule

The campaign is `CERTIFICATE_FAILURE` if any power identity residual exceeds
`1e-10 W`, any selected branch changes the first-step served/active set, any
non-focal first-step action/link power changes, preview/commit parity fails, or
proposal timing reads a realised outcome.

Otherwise it advances only to R2 closure and the offline aliasing/credit audit
when all conditions hold:

1. at least 20 selected paired proposals in total and at least one in four of
   five seeds;
2. the conditional 62/142-ms, `E_HO=0` paired horizon `Delta eta_time` has a
   positive pooled mean, positive seed mean in at least four of five seeds, and
   a seed-t95 lower endpoint above zero using `t_0.975,4=2.776445105`;
3. every selected first step preserves service and strictly lowers power; and
4. all engineering identities and artifact hashes pass.

Decision labels:

- `PASS_TO_R2_AND_ALIASING_GATES_ONLY`;
- `FAIL_DROP_C3_EE_DIRECTION`;
- `CERTIFICATE_FAILURE`.

Even a pass is conditional timing sensitivity evidence, not an accepted
temporal-EE result. It does not authorise reward implementation, Main replay,
short RL pilots, heavy training, or a Multi-Catfish claim.
