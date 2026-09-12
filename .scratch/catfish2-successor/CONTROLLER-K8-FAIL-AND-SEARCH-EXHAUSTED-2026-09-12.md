# Controller adjudication — `T_NEXT` fails the k = 8 drop-one; the bounded Catfish-2 search is EXHAUSTED

Date 2026-09-12. Read against Amendment 15 §7 and §9. Every figure re-derived by me from the five
`devval-ep00100.json` files in `/home/sat/mcrl-v025-cf2s-multi-ws/runs-k8/`, not from the lane's report.

## 1. The k = 8 matrix, verified

All five cells: DEV seed index **8**, pinned TLE `427e6a91…`, ep 100 of a frozen 300-episode schedule.

| arm | EE (M bit/J) | vs D0 | served | p10 / D0 | bits / D0 |
|---|---|---|---|---|---|
| `D0` | 100.789 | — | 0.99671 | 1.000 | 1.0000 |
| **`T0-only`** | **112.487** | **+11.606 %** | 0.99762 | 1.348 | 1.1046 |
| `T_NEXT-only` | 109.086 | +8.232 % | 0.99504 | 1.183 | 0.9264 |
| **`FULL{T0,T_NEXT}`** | **107.852** | +7.008 % | 0.99613 | 1.327 | 1.0136 |
| `2-null` (Bernoulli) | 79.746 | −20.878 % | 0.98938 | 0.283 | 0.5471 |

| frozen gate | required | observed | |
|---|---|---|---|
| `FULL − T0-only` | ≥ +1.0 % | **−4.120 %**, paired **0/24** | **FAIL** |
| `FULL − T_NEXT-only` | ≥ +1.0 % | **−1.131 %**, paired 8/24 | **FAIL** |
| `FULL >` matched null | > | +35.244 %, paired 24/24 | pass |
| served vs D0 | ≥ −0.5 pp | −0.058 pp | pass |
| p10 vs D0 | ≥ 0.5 × | 1.327 × | pass |
| bits vs D0 | ≥ 0.95 × | 1.0136 | pass |

**Two of the three drop-one gates fail. `T_NEXT` is not Catfish #2.**

`FULL − T0-only` at **0 of 24 paired episodes** is not a marginal miss. There is no episode in which adding `T_NEXT`
to T0 helped.

## 2. The finding is sharper than "it did not help": FULL is worse than **both** single-teacher arms

`FULL` 107.852 < `T_NEXT-only` 109.086 < `T0-only` 112.487.

Giving the learner a *choice* between two teachers' actions is worse than giving it **either one alone**. That is not
averaging, and it is not noise at 0/24.

The mechanism is legible in the set-valued loss. With `A_CF(s) = unique({a_T0, a_TNEXT})`, the margin is satisfied by
whichever member the learner's own TD score already prefers. `|A_CF| = 2` in ~61 % of states, so in the majority of
decisions **the T0 constraint becomes escapable** — the learner can satisfy the loss by choosing `T_NEXT`'s action
instead. The set-valued mechanism does not combine two teachers; **it dilutes the better one.**

This is mechanically the concern I raised when recommending against a `T_H` FULL run, and it is worse than I argued
then. I predicted the *upside* would be bounded to states where the second teacher is right and T0 is wrong. The
measurement shows a *downside* as well: the second teacher's presence weakens the first teacher's signal everywhere
the two disagree. **Recorded because I got the direction half wrong** — I anticipated a capped gain, not a loss.

**The mechanism itself is sound and this is not a harness failure.** FULL beats its matched null by **+35.244 %,
24/24**, and clears every QoS floor. Lane M's twelve contract tests passed with bit-identity on loss and gradient, the
source receipt reproduced Lane N's action-trace digest `0568b222…` with **0** mismatches over 24,000 decisions, and
the null's realised singleton rate **0.392740** matched the frozen `p_singleton` **0.391458** to 0.13 pp on the
learner's own states. The declared step-structure divergence appeared exactly as predicted (`t = 9` = 1.0000 by
construction) and **cannot** affect the reading, because neither failing gate involves the null.

`T_NEXT-only`'s bits ratio of 0.9264 is below the 0.95 floor — the floor is specified against `D0` for the FULL arm,
so this breaches nothing, but it says `T_NEXT` alone buys its EE partly by shedding throughput, consistent with its
+8.232 % over `D0` still being 3.0 % below `T0-only`.

## 3. Amendment 15 §9 applies: the search is exhausted

| source | outcome |
|---|---|
| `T_H` | CLOSED — no separation from seed variation on two seeds |
| `T_DELTA` | CLOSED — clone reached `R_repr ≥ 0.5` only by shedding 18 % of the bits; also only +0.011 over its own trivial baseline |
| `T_TAIL` | CLOSED — `A_repr` 0.4635, below the floor *and* 0.125 below its own trivial baseline |
| **`T_NEXT`** | **CLOSED — passed both pre-training gates, failed the drop-one at k = 8: −4.120 %, 0/24** |

The portfolio was sealed to three families and a fourth may not be added. **k = 9 was correctly not sealed and not
launched** — the unambiguous-pass condition was not met, and Lane M stopped rather than reinterpreting a gate.

Per Amendment 15 §9, all of the following are now prohibited: adding another source; relaxing or re-reading any gate;
sweeping a coefficient, margin or hyperparameter; reopening `T_H`, `T_DELTA` or `T_TAIL`; and **launching the
single-source S1 under a "Multi-Catfish" framing.** Nothing in this document does any of them.

## 4. What was actually established, and it is not nothing

Four sources were specified prospectively, screened without training wherever possible, and closed on pre-declared
criteria. The line produced results that are publishable as findings rather than as failures:

1. **A privileged counterfactual teacher can be genuinely better than both the deployed rule and T0 — and still be
   unusable.** `T_DELTA`'s joint rollout beat T0 by 4.06 % at 100 % service, with no herding, and a 113-dim
   deployable student could not carry it. Two privileged teachers died at that screen (`T_SEQ` 0.13–0.15, `T_DELTA`
   degenerate), before a single learner episode was spent on either.
2. **Temporal foresight is a real and distinct information axis in this physics.** Moving the same gain criterion
   from `t` to `t+1` takes disagreement with T0 from 0.1982 to 0.5964 — and the `t+1` quantity is the *cleaner*
   signal, with both stochastic terms absent. `T_NEXT` transfers positively on its own (+8.232 % over `D0`).
3. **But it is not additive with T0**, and the set-valued combination is worse than either teacher alone.
4. **Association persistence over one step is inert in v023**: 0 of 21,600 decisions, because D2 offers only
   high-elevation satellites and one 30.08 s step moves elevation by a mean 11.2°, never across the horizon.
5. **`T_E` is degenerate by construction**: joules are interference-free, so `ΔE` is exactly zero for any candidate
   joining a lit beam below its maximum.
6. **A methodological result the project should keep**: a fixed `A_repr` floor is not source-independent, and must be
   read against each candidate's own pure-T0-imitation baseline. Of the four candidates, exactly one clears its own
   baseline — `T_NEXT`, by +0.168, against `T_DELTA` +0.011 and `T_TAIL` −0.125.

**The honest one-line summary: this project has one catfish, T0, and a bounded well-specified search for a second one
did not find it.**

## 5. What returns to the owner

Amendment 15 §11 reserved exactly this decision. The single-source S1 manifest is complete, committed and hashed
(`7646bb00…`, 18 runs, 18 distinct config hashes, `T0-XEP` reference sealed at `9bb0c01e…`), and formal S1 remains
**PARKED and untouched** — verified again: no S1 result root exists and no formal evaluation episode has been
stepped.

The owner chooses between:

1. **Proceed with the single-Catfish / teacher-injected algorithm and change the paper framing** — the frozen
   provisional algorithm is B1 execution contract + ratio learner + T0 + D3 large-margin injection, with E1 evidence
   on three fresh seeds (+9.42 %, 144/144 paired episodes positive). The framing must drop "Multi-Catfish", and must
   carry the decomposition finding: roughly half the headline gain over the published baseline is the backbone, not
   the catfish (`D0` alone is +9.92 % over it; the catfish adds +9.42 % on top).
2. **Explicitly authorise a new research direction** — which would need a new information axis, not another
   reweighting of the two observation blocks, and would be a new sealed declaration rather than an extension of
   Amendment 15.

Both remaining live decisions — the S1 fresh-context review, which I have held since Amendment 14, and the final S1
manifest — depend on that choice. Nothing else is running: `sat` is clear and every lane is closed.
