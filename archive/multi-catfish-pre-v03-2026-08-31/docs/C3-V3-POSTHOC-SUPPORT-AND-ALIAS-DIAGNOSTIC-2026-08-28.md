# C3 V3 posthoc support and alias diagnostic

Date: 2026-08-28  
Status: historical descriptive premise screen; not V3 support, learnability,
efficacy, or training evidence

## Question

Before building the prospective C3 V3 runner, do already-opened historical C3
rows show either of the following premises?

1. more than one strict high-to-low candidate can sometimes exist at the same
   anchor; and
2. the current Main state's lagged-demand block may alias the current
   post-feasibility eligible-load distinction used by C3.

The source campaign predates V3. It used Q1-only Main, a one-step power/
median-rate guard, different candidate semantics, and historical revealed
seeds. It cannot be promoted into a V3 census or result.

## Bound inputs and executable receipt

| Input | SHA-256 |
|---|---|
| historical C3 result JSON | `99915d786b5b00ad5e44dd4db6007113687588d99a9d82c0043c09de086938b3` |
| historical 112-D observation NPZ | `970ee3ed5df2f7330c7fb7e8e46a0f15d54ec3fcaeb36aed9b220e01466461b0` |
| analysis script | `469ae8bf24e57b9007f9405f6280f4b0b61e705866a9a4709afca3407bd41353` |
| focused tests | `40116a6777df94c89af2787f32c6e85cd423cc6c6300059bffd78732eba05d49` |

The two focused recomputation tests pass. The script is
`.scratch/catfish-design-data/analyze_c3_v3_posthoc_support.py`.

## Recomputed facts

The historical inputs contain 5,000 user-steps, 174 candidate rows, and 136
candidate rows with the source/destination eligible loads needed for this
posthoc identity check.

Applying only the future C3 strict-load condition

```text
U_src >= U_dst + 2
```

to those 136 rows yields:

- 34 strict-load candidate rows;
- 15 anchors with at least one strict-load row inside the historical
  one-step power-screened carrier (not V3 certification);
- 10 anchors with at least two such choices; and
- 9 of those 10 multi-choice anchors have nonconstant lagged-demand gaps, so
  the observable load field is not always a pure tie within the old support.

Only one strict-load row also survived the historical median-rate guard. That
old guard is not the V3 complete-power/useful-bits/EE-surplus certificate, so
the count is a warning about filter interaction, not a V3 support estimate.

For every load-bearing candidate, the last 28 entries of the canonical 112-D
observation were decoded as previous-step demand and compared with the later
current eligible-load `+2` label. The confusion counts are:

| | Current strict | Current not strict |
|---|---:|---:|
| Lagged demand predicts strict | 10 | 43 |
| Lagged demand predicts not strict | 24 | 59 |

This gives 50.74% agreement, 18.87% precision, 29.41% recall, and a lagged-
versus-current load-gap correlation of 0.0349. The mean absolute gap error is
1.441 users, and only 22.06% of gaps agree exactly.

## Ruling

The old rows support two limited conclusions:

1. a multi-choice strict-load C3 mask is not algebraically empty; and
2. the lagged-demand/current-eligible-load consumer alias is serious rather
   than merely terminological.

They do **not** establish that the V3 `H=3` plus release, complete-power,
useful-bits, and EE-surplus support is frequent enough. They also do not prove
that the full 112-D state is uninformative: current access, SINR, angle, action
identity, and nonlinear combinations were not tested by this narrow check.

Therefore C3 V3 may proceed only to deterministic semantics and a prospective
support/consumer gate. C3-to-Main routing remains forbidden. If the consumer
gate cannot extract held-out action value from the unchanged state, the
smallest compliant redesign is a separately preregistered pre-action
observability feature or forecast summary; post-action eligible load may not
be leaked into Main state.

## Claim ceiling

This diagnostic shows a plausible but sparse opportunity premise and a
concrete representability risk. It shows neither a learned C3, canonical
`r_3` improvement, fresh-seed Main-only EE improvement, nor a successful
third Catfish.
