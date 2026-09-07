# C3 pre-outcome rate-guard development protocol

Status: frozen development analysis on the already-read seed `2026082701`.
This seed may select a guard but may not validate it. Evaluation-only,
legacy-narrow sensitivity; no implementation or training authority.

Date: 2026-08-27

## Fixed support

Reuse exactly the certified one-focal intra-satellite support from the v1 C3
shadow protocol. Eligibility and retention remain independent of rate, reward,
EE, fading outcome, and successor. This analysis only attaches pre-decision
features already present in the live observation.

## Pre-outcome joint throughput proxy

For the frozen Main reference actions, let `gamma_obs,u(a)` be the candidate
SINR in the current 112-dimensional observation. Given a hypothetical joint
action and its deterministic served loads `U_b`, define

```text
R_proxy = sum_u [B / U_bu] log2(1 + gamma_obs,u(a_u)).
```

The candidate branch changes only the focal action and changes loads from
`(U_src,U_dst)` to `(U_src-1,U_dst+1)`. It reuses every non-focal observed SINR
and uses the focal candidate's observed SINR. The proxy does not read the
current-slot fading/rate outcome and does not claim to equal realised
throughput.

## Two prespecified guards

For every already-certified power-relief candidate, compute:

```text
G_rate = R_proxy,candidate - R_proxy,reference

eta_proxy,0 = R_proxy,reference / P_reference
G_ee = G_rate - eta_proxy,0 * Delta P_system
```

The two development guards are:

1. `RATE_NONINFERIOR`: retain iff `G_rate >= 0`;
2. `PROXY_EE_POSITIVE`: retain iff `G_ee > 0`.

No margin, coefficient, quantile, subgroup, or threshold sweep is allowed.

## Development report

For the power-only support and each guard, report coverage and the descriptive
precision for positive realised immediate EE, positive realised throughput,
mean/median deltas, and a 2x2 confusion table. Because outcomes from this seed
are already known, these figures may choose at most one rule for a later frozen
different-seed gate. They are not evidence that the chosen rule generalises.

If neither rule removes the strongly adverse mean immediate EE direction while
retaining at least two candidates, do not advance a rate guard from this
development seed. If both qualify, prefer `RATE_NONINFERIOR` because its
constraint is physically simpler and does not turn C3 into a second direct EE
optimizer.
