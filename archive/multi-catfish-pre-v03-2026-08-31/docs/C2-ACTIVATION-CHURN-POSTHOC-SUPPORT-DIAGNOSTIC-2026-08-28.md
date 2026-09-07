# C2 activation-churn posthoc support diagnostic

Date: 2026-08-28  
Status: read-only posthoc design diagnostic; not a preregistered role gate,
training result, or efficacy claim

## Source and question

Source receipt:

```text
.scratch/catfish-oracle-gate/state-only-confirmation-seeds-10-k10-v2.json
SHA-256 cd88d8c5b17d163a957d8c2e56c2995080c4bb1636cbcc93fae13b234ba50658
```

The source contains 758 previously evaluated `r2_access_exact_stay` one-focal
rows across ten already revealed seeds. It uses the historical one-step,
Q1-reference, legacy-narrow diagnostic. The present read-only query asks only
whether those old rows contain any one-step physical support resembling the
new activation-stability hypothesis.

This query is posthoc and reads realised outcomes. Its filter must never be
copied into online admission, replay weighting, or confirmatory evidence.

## Descriptive counts

Among the 758 exact-stay rows:

| Descriptive property | Count | Share |
|---|---:|---:|
| alternative system power lower than reference | 166 | 21.8997% |
| alternative throughput not lower than reference | 595 | 78.4960% |
| alternative immediate EE higher than reference | 393 | 51.8470% |
| alternative active-beam count lower | 33 | 4.3536% |
| alternative active-satellite count lower | 5 | 0.6596% |

The broad posthoc intersection

```text
(active-beam count lower OR active-satellite count lower)
AND immediate EE positive
AND service safe
```

contains 21/758 rows (2.7704%) and appears in nine of ten old seeds. Within
those 21 rows, the descriptive means are:

- `Delta EE = +0.774780 Mbit/J`;
- alternative-minus-reference system power `= -5.315015 W`; and
- alternative-minus-reference throughput `= -0.110010 Gbit/s`.

Adding strict realised throughput nonloss leaves 9/758 rows, appearing in five
of ten old seeds. Their descriptive means are `+1.133600 Mbit/J` and
`-4.274915 W`.

## Interpretation

The old data do not show that activation-churn C2 works. They show only that
the underlying environment sometimes exposes a one-step state where staying
avoids an active resource and improves immediate EE. The broad proxy is sparse
but nonzero and cross-seed; the strict throughput-nonloss subset is much
sparser.

This supports a cheap new Stage-0 opportunity census before any learner or
carrier test. It also warns against assuming that a strict useful-bits floor
will have adequate support without a prospective census.

## Missing evidence

The receipt does not test:

- scalarized Main rather than the historical Q1 reference;
- `off -> on -> off` short-lived churn across multiple intervals;
- the hold and first-release event ledger;
- a pre-outcome fading-off forecast proxy;
- two or more certified persistence choices at an anchor;
- learned Q2 ranking versus same-support random/stay controls;
- diagonal Main transfer; or
- fresh-seed Main-only ratio-of-sums EE after training.

Therefore the only allowed conclusion is:

> Activation-related C2 support is physically plausible but likely sparse;
> proceed only to a prospective support census and deterministic fixtures.

## Prospective developmental follow-up

A later one-anchor, pre-outcome developmental scan used the frozen 373-file
TLE authority, the final Main checkpoint, development seed `2026082801`, step
1, nine departure focal users, and eight deterministic candidates per focal.
It is still neither a preregistered census nor an efficacy test.

```text
receipt .scratch/catfish-stage0/receipts/c2-anchor-seed2026082801-9x8.json
receipt SHA-256 b2272894705de737e7d6c2a61c6173c397744c8df10055feeaea57c08a6d5607
support code SHA-256 7bd728c3a6ae093fd700e55383662c0ae512025004de00729165ac3719dccc47
smoke runner SHA-256 c0d44466e10bb66ffbf2f683f98908edb252f84813aab9bd29b0a6453058b64b
```

The scan evaluated 72 candidates in 463.9016 seconds. Nine candidates
strictly improved both the hold-window and full-window system `r2`, but only
two survived every V0.1 activation, useful-bits, non-focal, and surplus guard.
Those two belonged to different focal users (`10` and `67`), leaving no focal
user with the two-choice learned support required by V0.1. Failure first
layers were 46 hard-safe, 20 activation-or-energy, and four strict-system-r2;
two candidates passed.

This prospective result strengthens two distinct statements and no more:

1. the C2 mechanism signal is nonzero under real TLE because 9/72 candidates
   improved the target reward window; and
2. per-action V0.1 certification is both too sparse for learned routing at
   this anchor and too expensive for an online 9000-episode carrier.

It therefore supports moving the four-step counterfactual from online replay
admission to sampled Stage-0 mechanism validation. It does not by itself
authorize V0.2 routing or claim that C2 improves Main-only EE.
