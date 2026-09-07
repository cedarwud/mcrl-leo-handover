# Sol Ultra C3 formal-result adjudication — 2026-08-27

## Review identity

- Reviewer: `gpt-5.6-sol`, reasoning effort ultra, fresh context
- Scope: read-only scientific audit; no training and no file edits by reviewer
- Formal JSON:
  `c3-disjoint-median-shadow-seeds-2026082801-2026082805-v1.json`
- Independently recomputed SHA-256:
  `99915d786b5b00ad5e44dd4db6007113687588d99a9d82c0043c09de086938b3`
- Exact requested verdict: **`NEW_DISJOINT_PERSISTENT_C3_GATE`**

## Independently verified facts

- All 5,000 source rows, 174 candidate rows, and 13 paired rows were parsed
  and recomputed.
- The frozen formal decision is correctly `FAIL_DROP_C3_EE_DIRECTION`.
- Selected support by seed is `1/0/6/4/2`: 13 total rather than the required
  20, with support in four of five seeds.
- Pooled paired-horizon mean is `+81,462.810051 bits/J`.
- Seed means are `+247,542.513`, undefined, `-250,068.857`, `+423,554.438`,
  and `+308,834.703 bits/J`; only three seed means are positive.
- Seed-t95 is correctly unavailable because one seed has zero selected
  support; no value may be imputed.
- All 13 selected first steps have positive realised EE and throughput deltas
  and strictly negative power deltas. The one-to-three-step endpoint is mixed:
  nine positive and four negative, spanning `-1,533,158.871` to
  `+1,162,982.069 bits/J`.
- All engineering, service, power, clone, preview/commit, helper, and source
  checks pass. Maximum power/reward identity residual is `8.704e-14 W`, below
  `1e-10 W`.
- The reviewed source-drift contract properly mediates
  `analysis_source_matches_training = false`. The omitted PyYAML version is a
  residual documentation gap, not a way to rescue the conservative failure.

## Scientific scope

The frozen outcome-blind median rule is permanently dead. It may not be
retuned, relabelled, rescued on the same seeds, or described as advancing.

The result is not a family-wide impossibility proof. The unilateral
denominator identity survives and every selected immediate intervention
improves EE while preserving service. The failed elements are support density
and persistence into the short horizon. A genuinely different persistence
hypothesis is therefore defensible only under a new ADR/spec and wholly new
seeds.

## Smallest permitted next non-training gate

### State/action hypothesis

Use a fixed `H = 3` deterministic, fading-off, pre-outcome roll-forward. Admit
one focal same-satellite relocation only when unique-source-bottleneck relief
persists through all three steps, the destination maximum is not raised,
served and active sets remain fixed, non-focal actions remain identical, and
no event beyond the unavoidable initial `phi1` is introduced. No fitted
numeric threshold is allowed.

### Reward and ranking

Retain the natural-unit focal private reward

```text
r3_marginal,u = -(P_system - P_minus_u)    [W].
```

Rank the newly certified support by preregistered cumulative avoided payload
energy

```text
G_P = Delta * sum_h (P_reference,h - P_candidate,h)    [J],
```

not by immediate realised EE.

Potential-based shaping is not appropriate at this gate. It cannot establish
physical persistence, would telescope rather than supply new causal evidence,
and lacks an authorised Markov state because Main's 112-D observation omits
the exact bottleneck variables.

### Causal EE mechanism and safeguards

Persistent denominator reduction plus
`B_time,candidate >= B_time,reference > 0` implies higher time-accounted EE
when candidate payload energy is strictly lower. Bits and event counts are
safeguards, not the C3 objective.

The new spec must be hashed before choosing unseen seeds; retain the full
census and every selected branch; preserve clone/RNG/parity and `1e-10 W`
checks; keep `E_HO` uninstantiated and 62/142 ms explicitly conditional; and
prohibit fitting, subgroup selection, margins, or threshold adjustment using
the failed five seeds.

### Falsification

Require at least 20 pairs, support in at least four of five wholly new seeds,
at least four positive seed means, a seed-t95 lower endpoint above zero, strict
first-step service/power validity, and a positive persistent-energy mechanism.
Any failure permanently drops this persistent variant; there is no fifth
guard iteration.

## Role separation and claim ceiling

C1 directly targets the immediate rate/power ratio. C2 values association
persistence and avoided handover. The proposed C3 deliberately pays one
intra-satellite event to obtain persistent structural beam-bottleneck energy
relief; rate and event quantities remain safeguards.

Novelty and effectiveness remain unestablished. The verdict authorizes only a
sealed, independently reviewed, non-training C3 persistence shadow. It does
not authorize reward implementation, Main transfer, short RL pilots, heavy
training, or a Multi-Catfish effectiveness claim.
