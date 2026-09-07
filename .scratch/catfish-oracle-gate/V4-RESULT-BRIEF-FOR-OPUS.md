# Frozen v4 ARLP result brief for independent review

Date: 2026-08-26

## Scope and non-negotiable constraints

- Goal: decide whether a third, independently useful training-time Catfish
  role can be justified for R3 and indirectly improve system EE.
- R1 remains the direct system-EE objective.
- R2 is intended to cover temporal continuity/handover, but physical
  `T_HO/E_HO` parameters are still absent, so its end-to-end EE effect is not
  identified.
- No post-training auction, coordinator, acceptance gate, or action override is
  allowed. The desired final mechanism has three reward-specific training-time
  roles only if each role is empirically useful.
- The formal v4 seeds may not be reused for retuning, coefficient sweeps,
  subgroup rescue, or a replacement candidate.

## Evidence carried from v3.1

The old R3 previous-inactive split endpoint existed, but a fixed Q-shaped
state-only learner failed on 1,000 held-out rows:

- AUROC `0.549769` against a frozen `0.65` threshold;
- AP `0.249874` against `0.30`, at prevalence `0.211`;
- accepted precision `0.268707`, recall `0.3744`;
- accepted mean DeltaEE `+0.030714 Mbit/J`, but its seed-t95 interval was
  `[-0.154952, +0.212658]`, with only 7/10 positive seeds;
- within-action proxy AUROC was `0.512117` (post-failure exploratory only),
  implying most apparent signal came from action identity rather than state.

The old inactive role-positive subset was also descriptively adverse:

- held-out mean DeltaEE `-0.18695 Mbit/J`;
- mean DeltaPower `+6.3101 W`;
- EE-positive rate `45.28%`, versus `55.62%` outside the role-positive subset.

The analytic minimum one-beam activation cost is `6.265900454 W` at segment
start. This explained why a generic load-spreading endpoint could open a beam
and incur a dominant cost omitted from old R3.

## Frozen v4 hypothesis

V4 changed the candidate R3 role to activation-regularised spatial load
potential:

```text
C3 = sum_b U_b^2 / 6 + B_active
r3_u = -[(2 U_bu - 1)/6 + I{U_bu = 1}]
```

For a served focal user, the reward is exactly the negative accounting
difference `C3(all)-C3(all except u)`. The runner verified that identity row by
row. `B_active` is one abstract activation unit; the 6.2659 W figure is only a
physical anchor, not silently inserted into C3.

The outcome-blind proposal used only the focal live mask, access vector,
previous demand, and candidate SINR. Before Q1 or any outcome it selected the
candidate minimising

```text
m3(a) = (2 n_a + 1)/6 + I{n_a = 0},
```

where previous demand excluded the focal user for its visible incumbent.
SINR and action index were deterministic tie-breakers. After this proposal was
frozen, the episode-8999 Q1-only reference was computed. A row was eligible
only when the ARLP proposal's physical key differed from Q1. The 83 matching
rows were retained as ineligible and excluded from every matched endpoint; no
evaluated ARLP row equals Q1. For each eligible row, a dedicated RNG uniformly
selected a valid physical candidate different from Q1 as a matched-random
control, also before outcomes. Random was allowed to equal ARLP. Reference,
ARLP, and random changed at most the same focal user and used neutral
common-random-number previews; only Q1 committed. Thus both alternatives in
the 917-row ARLP-versus-random comparison are subject to the same
different-from-Q1 eligibility constraint.

The live R1 denominator already includes realised PA supply power, per-active-
beam circuit power, and once-per-active-satellite baseband power. The
`6.265900454 W` anchor is therefore already physically priced by R1 when a
beam actually activates. V4's abstract `B_active` was an R3 proxy, not a power
term missing from R1; recommending that it be "added to R1" without this fact
would risk double-counting.

## Verification

- Spec SHA-256:
  `a5400b970812eaf2a8489f5ff70e083e78a28eef6cc78794ae3a2e6ffe6f4f2d`.
- Runner SHA-256:
  `35219a1353c44644d0f1acf7e78f3277497aa447fab7f3be01b3383779e2a82e`.
- Formal receipt SHA-256:
  `8efb3068537a10dd8896d07d5410986976b40a6181532ded876648c4474e01a2`.
- Server and local independent receipt verification passed.
- 45 focused server tests passed; the formal run had 10 new seeds, 1,000
  sampled rows, and 917 eligible rows (84--97 per seed).

## Frozen formal result

Decision: `FAIL_DROP_ARLP_R3_DIRECTION`.

| Frozen condition | Result |
|---|---|
| engineering and coverage | PASS |
| realised `C3_ref-C3_ARLP` | FAIL |
| `EE_ARLP-EE_Q1` | FAIL |
| `EE_ARLP-EE_random` | PASS |
| service safety | PASS |

Exact endpoints over 917 eligible matched rows:

- `C3_ref-C3_ARLP`: pooled mean `-0.048528`; only 4/10 seed means positive;
  seed-t95 `[-0.101805, +0.009075]`.
- `EE_ARLP-EE_Q1`: pooled mean `-190,278.84 bits/J` (`-0.190279 Mbit/J`);
  0/10 seed means positive; seed-t95
  `[-276,337.76, -104,870.61] bits/J`.
- `EE_ARLP-EE_random`: pooled mean `+387,609.48 bits/J`
  (`+0.387609 Mbit/J`); 10/10 seed means positive; seed-t95
  `[+316,836.06, +456,570.76] bits/J`.
- ARLP unsafe: `1/917 = 0.1091%`; random unsafe:
  `48/917 = 5.2345%`.

Thus the proxy contains useful structure relative to random, but it neither
beats Q1 nor reliably improves its own realised potential. A likely inference
is that previous demand is stale relative to simultaneous current actions;
that inference is not itself a measured causal decomposition.

## Questions for the reviewer

1. Is the formal pass/fail application logically valid, with any material
   leakage, comparator, identity, or clustered-inference defect visible from
   this brief?
2. What exactly has been falsified: this focal previous-demand proposal, the
   ARLP reward direction, or any independent R3 Catfish under the current
   observation/action contract? State the narrowest defensible claim.
3. Given the constraint against deployment-time coordination, should the next
   primary decision be to drop independent R3 and couple spatial activation
   into R1, or is there one materially different independent R3 mechanism
   worth preregistering on wholly new seeds? Do not offer a menu.
4. What is the current honest status of the desired three-role story
   (`R1 direct EE`, `R2 continuity`, `R3 spatial efficiency`)?

Give one primary recommendation. Keep verified evidence, inference, and any
future falsifier visibly separate. Do not edit files, run code/training, browse,
or use subagents.
