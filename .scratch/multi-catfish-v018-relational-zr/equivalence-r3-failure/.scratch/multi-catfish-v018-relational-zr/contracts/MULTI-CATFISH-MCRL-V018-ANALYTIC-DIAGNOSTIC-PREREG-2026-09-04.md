# Multi-Catfish MCRL V0.18 C3 analytic-diagnostic gate

Status: `FROZEN_BEFORE_OUTCOME`.

Claim ceiling: fresh-TRAIN matched oracle/parameter-free diagnostic evidence.
This contract authorizes no learner update, episode training, TEST access, or
final efficacy claim.

## 1. Single question

Does the unchanged zero-marginal-redistribution (ZR) C3 target remain positive
under the actual frozen learned Q1+Q2 background, and do permitted predecision
relational variables carry enough of that signal for one victim-relational Q3
learner attempt?

V0.17 already closes B402, SoftKL retry, loss/seed/rung selection, rescaling,
threshold relaxation, clipping, support filtering, and further flat feature
expansion. Q1, learned Q2, canonical EE, ZR algebra, shared kappa, native mask,
and unweighted deployment score are immutable here.

## 2. Fixed worlds, lineages, and compute

- Split: TRAIN only; TEST remains unopened.
- The four newly frozen TRAIN worlds are `2026120401`, `2026120402`,
  `2026120403`, and `2026120404`.
- Q1 lineages: `2026092101`, `2026092102`, `2026092103`.
- Learned-Q2 checkpoints: the matching sealed OPS-3 Q2 rung-3000 checkpoint
  already used by V0.17 for each lineage.
- Episode length: ten canonical decision steps.
- Fading: one keyed common-random field per world, shared by every matched arm
  and lineage.
- Contexts for source diagnostics: h=12, h=1, h=2. Trajectory arms use h=12.
- Compute class: matched pilot; execute on the Ubuntu server, not local WSL.

The pre-freeze local and Ubuntu-server censuses are recorded in
`LOCAL-SEED-CENSUS.md` and `SERVER-SEED-CENSUS.md`; both found zero prior
experimental use. Any later textual occurrence caused by this frozen contract,
its runner, or its receipts is not a prior outcome use.

## 3. Three fixed arms

At each arm-specific predecision anchor, compute the frozen Q1 values and frozen
learned-Q2 values. OPS-3 projection may be used only to encode the already sealed
Q2 state; its oracle score may not enter an action score.

```text
BASE       = argmax_safe(Q1 + Q2_hat)
EXACT_ZR   = argmax_safe(Q1 + Q2_hat + Z3_exact / kappa)
NOMINAL_ZR = argmax_safe(Q1 + Q2_hat + Z3_nominal / kappa)
```

Each arm sends exactly one joint action vector to the environment. There is no
coordinator, vote, veto, second executed decoder, route weight, or post-training
override.

`Z3_exact` is the unchanged live ZR teacher measured under the keyed common
field. `Z3_nominal` is parameter-free and predecision-only: it reconstructs
current reference/candidate service, load, beam power, wanted power, and
co-channel interference using current geometry, fading exactly one, shadowing
exactly zero, and no realised `ActionEvaluation` value. It then applies the same
ZR positive-credit compatibility rule and centres on the detached reference.

The nominal decoder is diagnostic only. It is never a deployable Q3 and must be
absent from the later execution graph.

## 4. Exact information and compatibility boundary

Before any matched arm may execute, a step-0 mechanics prerequisite must persist
the immutable relational observation, native mask, detached references, and
causal compatibility array with digests, then open the exact counterfactual
measurement only for the proof below.

Causal compatibility is reconstructed from reference/candidate opening bits,
physical `(norad_id, cell_id)` keys, and the exact float64 current recurrence-
power surface. The live teacher separately persists its five component arrays:

1. served-user vector;
2. canonical active-beam keys;
3. active-satellite keys;
4. canonical per-beam RF-power bytes;
5. canonical total network-power bytes.

For every legal focal action, the reconstructed final compatibility bit must
equal the live teacher's conjunction of those five components exactly. The
reconstructed and live arrays are both hashed. Any mismatch is immediate
`STOP_V018_MECHANICS`; no affected trajectory may be treated as evidence.
Compatibility is positive-credit support only and may never replace or narrow
the native action mask.

Forbidden nominal/learner inputs include the keyed `"physics"` fading or shadow
draw, realised rate/SINR/interference/energy/power signatures, any
`ActionEvaluation`, future state, teacher action, target, target sign, or outcome-
derived filter.

## 5. Source-side decision diagnostics

For every world, lineage, step, and context, compare

```text
teacher = argmax_safe(B_h + Z3_exact / kappa)
nominal = argmax_safe(B_h + Z3_nominal / kappa)
base    = argmax_safe(B_h)
```

Report per lineage and pooled:

- base and nominal teacher-action agreement;
- pivotal agreement on rows where teacher differs from base;
- stable preservation where teacher equals base;
- nominal change count and rate;
- fraction of nominal changes with strictly positive causal-compatible ZR
  support;
- h=1 and h=2 agreement relative to their base backgrounds;
- nonfinite counts and digest checks. Victim/user/action permutation, mask, and
  centring invariances are prelaunch code-manifest tests, not outcome metrics.

Every lineage must satisfy all of:

1. h=12 nominal agreement is strictly above base agreement;
2. h=12 pivotal agreement is at least 0.50;
3. h=12 stable preservation is at least 0.95;
4. at least one h=12 action changes and at least 0.80 of changes have positive
   causal-compatible support;
5. h=1 and h=2 nominal agreement are noninferior to base;
6. all frozen prelaunch tests plus runtime mask, finiteness, and digest checks
   pass.

## 6. Matched trajectory endpoints

For every arm accumulate canonical total delivered bits and canonical total
network energy over all ten steps, then compute only

```text
eta_arm = sum(bits_arm) / sum(energy_arm).
delta_arm = eta_arm / eta_BASE - 1.
```

Both `EXACT_ZR` and `NOMINAL_ZR` must independently satisfy:

1. pooled `delta_arm > 0`;
2. at least two of three lineage-pooled directions are positive;
3. at least three of four world-pooled directions are positive;
4. the pooled served fraction is noninferior to BASE within a fixed absolute
   margin of `0.001` (at most one additional unserved decision per 1000 user-
   decisions on average);
5. all matched-field, canonical-accounting, action-mask, and one-action-vector
   checks pass.

## 7. Mechanical decision

`PASS_ANALYTIC_DIAGNOSTIC` requires the Section 4 prerequisite and every clause
in Sections 5--6. It authorizes exactly one separately preregistered,
fresh-source victim-relational learned-Q3 gate. It does not authorize episode
training.

If `EXACT_ZR` fails Section 6, return `STOP_ZR_IN_LEARNED_Q2_CONTEXT`: the frozen
teacher's prior sign did not reproduce in the deployable base-head context. If
`EXACT_ZR` passes but `NOMINAL_ZR` or Section 5 fails, return
`STOP_RELATIONAL_OBSERVABILITY`: the permitted predecision variables did not
carry enough decision signal. Any other integrity failure returns
`STOP_V018_MECHANICS`.

No failure permits redrawing worlds, replacing a lineage, tuning this decoder,
changing its nominal fading/shadow convention, adding features, relaxing a
threshold, altering ZR, or trying a second relational architecture against the
opened outcomes. On pass, the later relational-Q3 input set is frozen to exactly
the predecision variables used by `NOMINAL_ZR`; it may not add an outcome-derived
or newly invented field.
