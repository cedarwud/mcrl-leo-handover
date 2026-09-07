# Sol Ultra fresh review of ADR-003

## Material Passport

- Reviewer route: new fresh-context Sol Ultra sub-session
- Review date: 2026-08-27
- Reviewed target: `docs/decisions/ADR-003-proposed-specialist-multi-catfish.md`
- Reviewed SHA-256: `aecafdc4c43bc65d8d64390ff918a66af0126920d1af318f45e03c393111d0d8`
- Verdict: `REVISE_BEFORE_FABLE`
- Runtime/reward/training authority: none

## Blockers

1. R2's own physical endpoint is ledger-based `eta_HO`, while the draft asked
   it to improve only the unchanged steady-state `eta0`. Reducing interruption
   can improve the former without changing the latter, so both endpoints and
   their separate claims must be explicit.
2. The reciprocal C3 proposal ranked only the two moved users even though the
   power identity requires all users on both affected beams. Shared-cost credit
   can reverse the ranking: moved-user shares may improve while total power
   worsens.
3. `C_out` is not an incentive-safety proof. It only ties the most expensive
   legal one-user service cost, and a current outage can reset a power segment
   and create future benefit that a one-step barrier does not dominate.
4. Complete joint-transition lineage is necessary but insufficient for Main's
   local-action Bellman consumer to reproduce a coordinated reciprocal action.

## Major required boundaries

- State the R2 algebra domain and allocate shared event energy exactly once.
- Evaluate cross-time temporal EE as ratio of accumulated useful bits to
  accumulated energy, not a sum of one-step ratios.
- Make outage handling a hard/lexicographic service or discounted-horizon gate,
  not a claim derived from `C_out`.
- Separate old/new reward effect, sham carrier effect, and informed Catfish
  effect with matched causal cells.
- Give every absent factorial role a frozen sham slot; do not reallocate its
  dose to an active role.
- Freeze replay source schedule, age, checkpoints, trigger probability,
  pre-state clustering, and behavior lineage.
- Add a joint-action representability gate if any paired C3 action survives.

## Identities independently verified

Subject to `E0>0`, nonnegative rates/times/energies, and no physical double
count, the reviewer reproduced

```text
sum_u r2_temporal,u = eta_HO - eta0.
```

For served users under the live per-beam/per-satellite power model, the reviewer
also reproduced

```text
sum_u C_bu/U_bu = P_system.
```

With `N_inf` avoidable execution-infeasible users and the proposed barrier, the
full reward sum would instead be

```text
sum_u r3_power,u = -P_system - N_inf*C_out.
```

## Revision direction

The response to the pair-credit and representability blockers is not merely to
change the pair score. ADR-003 will replace reciprocal exchange as the proposed
training mechanism with a one-focal-user, service-preserving power-bottleneck
relocation whose complete system-power decrease is certified pre-outcome.
Reciprocal support may remain a diagnostic receipt but grants no role or
training authority.
