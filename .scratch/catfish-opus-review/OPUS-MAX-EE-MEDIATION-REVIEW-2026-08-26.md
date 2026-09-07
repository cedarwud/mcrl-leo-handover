# Opus Max review: R2/R3 mediation of system EE

Status: completed external-model read-only review; controller fact-check complete
for the central structural claims; proposed numeric thresholds remain unvalidated.

Date: 2026-08-26

## Verified receipt

- Requested route: Claude `opus`, effort `max`.
- Canonical returned model: `claude-opus-5`.
- Runtime: 875,274 API ms (about 14 min 35 s), 26 turns.
- Output: 61,288 tokens, including 43,666 thinking tokens.
- Subagents: 0. Permission denials: 0. Web requests: 0.
- Allowed tools: `Read`, `Glob`, and `Grep` only.
- Prompt SHA-256:
  `733499bfda1a54ae9ef92e2f1c5507311c8bbb4b8d60a22651426dec40b307a7`.
- Structured receipt:
  `OPUS-MAX-EE-MEDIATION-RECEIPT-2026-08-26.json`.

## Opus verdict

`MERGE_OR_DROP`

Opus rejected the mapping "one Catfish per existing reward head" as the final
EE mechanism. It recommended retaining the current rewards as the frozen
baseline contract for causal diagnosis, dropping R2 as an EE-specialist under
the current physics, and coupling R3's useful physical channels back to R1
rather than presenting raw load count as an independent EE optimiser.

## Direct R2 ruling

The present R2 remains a valid secondary objective for handover incidence:
`r2` is exactly `0`, `-phi1`, or `-phi2`. It is not presently a physical EE
cost. A handover subtracts no transmission time or useful bits and adds no
signalling/access energy anywhere in the live rate, power, or EE chain.

The only live coupling is indirect through association and segment reset.
Continuing an association carries the segment power recurrence, while changing
association starts a new segment at `p0`. The live 112-dimensional state does
not contain segment-start gain or segment age, and candidate SINR evaluates all
candidates at `p0`; therefore the policy cannot identify the full continued
segment-power state from one observation.

Consequence: changing the numerical R2 reward alone cannot create a defensible
R2-to-EE mechanism. To reopen an R2 EE claim requires a separate v2 physical
model with handover interruption and/or handover energy, plus a representable
temporal state. That change would alter R1 and require a fresh baseline.

## Direct R3 ruling

The present `r3_u = -U_b` remains a valid load-balancing potential because
`sum_u r3_u = -sum_b U_b^2`. It is not a monotone EE proxy.

Within one beam,

```text
sum_{u in b} R_u
  = sum_{u in b} (B / U_b) log2(1 + gamma_u)
  = B * mean_{u in b} log2(1 + gamma_u).
```

Thus the direct aggregate `B/U_b` count effect cancels. R3 can affect system EE
only by changing beam composition/channel quality, the active-beam set,
interference, maximum per-beam transmit power, or service feasibility. Those
are system-level R1 channels, not information encoded by raw `-U_b` alone.

Consequence: do not replace `-U_b` with a larger coefficient or another blind
load penalty. Keep it frozen for the objective-inclusion diagnostic, but treat
any useful R3 Catfish mechanism as a coupled EE/beam-physics challenger unless
matched evidence establishes independent information.

## Audit of the proposed two-layer scores

The earlier temporal score

```text
A2 = DeltaB[t:t+H] - eta_ref * DeltaE[t:t+H]
```

is an EE certificate, not an R2 reward. Under the current simulator it contains
no explicit handover interruption or handover-energy term, and the required
segment state is aliased. It therefore cannot by itself preserve an independent
R2 role.

The earlier spatial score

```text
A3 = sum_{v != u} DeltaB_v - eta_ref * DeltaE_system
```

is a useful system counterfactual diagnostic, but it also uses the R1 EE
criterion. It should be interpreted as a spatial mechanism channel under a
common EE endpoint, not automatically as proof of an independent R3 optimiser.

## Carrier retained by Opus

Opus retained a narrower training-time carrier:

1. make every challenge decision before observing reward;
2. use a fixed per-episode intervention budget and an independent challenger
   RNG;
3. execute the selected action on the real trajectory;
4. store every valid realised full `(r1,r2,r3)` transition in the unchanged
   replay path;
5. use the single existing Bellman update for all three heads;
6. set challenger dose to zero at evaluation/deployment.

It rejected per-objective replay banks, Q-head-only auxiliary gradients, a
second Bellman path, and outcome-filtered admission.

Instead of reward-named roles, it proposed two mutually exclusive physical
proposal subspaces:

- same active-beam set: improve user composition, channel quality, interference,
  and maximum beam power without changing beam count;
- changed active-beam set: open/close or split/merge beams only when the
  throughput change pays for the activation-power change.

Both use one system-EE certificate. This is a mechanism decomposition, not a
three-reward symmetry claim.

## Smallest non-heavy falsifier

Before any new training:

1. measure how often removing `w2 Q2` or `w3 Q3` changes the physical greedy
   action on the ten fixed checkpoint seeds;
2. for each pivotal flip, use common random numbers to evaluate the alternative
   joint action and record system `DeltaEE`, `Delta throughput`, `Delta power`,
   `Delta active beams`, `Delta mean sqrt(p_b)`, beam spectral-efficiency
   composition, and `Delta sum_b U_b^2`;
3. drop R2 as an EE role unless Q2-pivotal flips have positive paired EE
   movement on at least 8 of 10 seeds;
4. test whether R3-pivotal flips operate through composition or active-beam
   count, and whether raw load movement predicts the EE sign;
5. require bit-identical module-absent versus challenger-`K=0` execution.

This is a local, evaluation-only prototype. It does not require long training.

## Heavy gate if the prototype survives

The existing four-arm objective-inclusion factorial remains useful only after
the local pivotality/mediation probe:

- `full`, `minus-r2`, `minus-r3`, `r1-only`;
- about 16--18 hours sequential on the Ubuntu server;
- unchanged reward definitions and full reward logging;
- at least three independent training seeds before a causal learning claim.

A later challenger experiment must compare each informed intervention against
a random intervention at the same trigger states, intervention dose, environment
steps, and update count.

## Controller fact-check and claim boundary

Confirmed from live code and artifacts:

- the per-beam `B/U_b` factor cancels from aggregate throughput when summed over
  users on that beam;
- handover does not directly subtract bits or add joules;
- R2 is only the realised event-class penalty;
- the live state is 112-dimensional and excludes the optional contract block;
- it does not contain segment-start gain or age;
- candidate SINR uses `p0` for every candidate;
- final main replay has 27.90% handover incidence versus 17.41% for
  stay-if-possible, so current data do not establish superior handover control;
- no repository file was changed by Opus and no training was launched.

Not yet accepted as measured results:

- the proposed 3.403 bit/s/Hz activation break-even;
- the claim that the average beam is exactly 99.5% of that threshold;
- the inferred 4--5% persistence power difference;
- the claimed single-digit-percent maximum EE headroom;
- any positive or negative effect of the proposed challenger.

Those quantities require a deterministic calculation/probe with saved inputs
and receipts before they can govern the design.

## Current controller disposition

Revise the previous recommendation as follows:

- do not change the frozen R2/R3 base reward before diagnosis;
- do not freeze three reward-specialist Catfish roles;
- run the non-heavy head-pivotality and common-random-number mediation probe;
- expect R2 to be dropped as an EE role unless that probe overturns the current
  structural and descriptive evidence;
- treat R3 as a coupled beam-physics channel under R1 unless it shows independent
  predictive value beyond the full EE counterfactual.

The maximum current claim is a reviewed, falsifiable design direction. It is
not evidence that any Catfish improves EE, that three roles are necessary, or
that a reward-v2 change is justified.
