# Multi-Catfish MCRL V0.4 C2 failure forensics

Date: 2026-09-01  
Status: `DIAGNOSTIC_COMPLETE`  
Claim ceiling: post-outcome diagnostic only; no remediation efficacy

## Question

The sealed five-arm evaluation found `CONFIRM_C1`, `CONFIRM_C3`, but
`C2_NOT_CONFIRMED`.  This audit asks whether the frozen Q2 learner had enough
within-state action support to perform the 28-action deployment argmax.  It
does not alter the EE formula, train a network, open TEST, or choose a new
checkpoint.

## Sealed receipt

- runner:
  `.scratch/c3-v04/run_v04_c2_failure_forensics.py`;
- contract tests:
  `tests/test_w90_ee_axis_v04_c2_failure_forensics.py`;
- artifact:
  `artifacts/multi-catfish-v04-c2-failure-forensics-20260901-r1`;
- result SHA-256:
  `4433a923764940a2991a799784b446ba5cd412205099a02aa976fdf6228db87b`;
- result-seal SHA-256:
  `092d80aa3865caa070f266020156aa7d267fb2b457b511af62e9c39e17d17c19`;
- receipt-only recomputation: pass locally;
- validation rows: 36, from the already-opened TRAIN/validation source split;
- TEST opened: no;
- training performed: no;
- held-out EE recomputed: no.

The runner authenticates the five-arm result, the prior masked mean/max gate,
the three exact rung-10 checkpoints, and all three C2 validation datasets
before recomputing every statistic.

## Established evidence

The old C2 learnability gate was only weakly positive:

- 96 training pairs;
- 36 held-out validation pairs;
- 13 active training action slots out of 28;
- mean skill over the strongest state-independent null: `+0.0198745`;
- positive skill in three of three initializations.

The gate therefore established a small held-out MAE improvement.  It did not
establish correct ranking of every legal action within a state.

For each validation row, the forensic audit evaluated all 28 Q2 outputs and
compared the legal argmax with the one candidate/reference pair whose temporal
counterfactual was actually supervised.

| Initialization | Pair sign accuracy | Pair correlation | Q2 argmax inside supervised pair | Q2 argmax outside supervised pair |
|---:|---:|---:|---:|---:|
| 2026092101 | 58.33% | 0.248 | 1/36 | 35/36 |
| 2026092102 | 55.56% | 0.255 | 1/36 | 35/36 |
| 2026092103 | 58.33% | 0.261 | 1/36 | 35/36 |

The candidate action itself was the Q2 argmax in `0/36` rows for every
initialization.  The median amount by which the off-pair argmax exceeded the
better of the supervised candidate and reference was `0.323`, `0.236`, and
`0.147` normalized Q units.  Thus the result is not a tie-breaking artifact.

This evidence is consistent with the sealed five-arm outcome: adding Q2 made
the policy consume less energy but lose substantially more delivered bits and
service, producing `-30.397%` pooled EE, zero positive initializations, and
zero positive physical worlds.

## Interpretation boundary

The following is established:

> On the exact old C2 validation anchors, the frozen Q2 legal-action argmax is
> outside the only temporally supervised candidate/reference pair in 97.22%
> of rows for all three initializations.

The strongest supported hypothesis is action-support extrapolation: sparse
pairwise temporal supervision leaves other legal actions unconstrained, while
deployment nevertheless asks Q2 to rank all legal actions.

The audit does **not** establish that the C2 formula is wrong.  The temporal
pair validator already recomputes every rate term, energy term, offset, and
sum.  No sign, unit, release-offset, or arithmetic defect was found.  The
audit also does not prove that adding full sibling coverage will improve EE;
that claim requires a fresh, preregistered physical probe.

Because the masked mean/max scorer shares weights across action slots, the
problem must not be described merely as unseen action identifiers.  The
scientific issue is missing within-state counterfactual labels for most legal
action feature vectors and their ranking, not a fixed output-neuron identity
bug.

## Single candidate remediation

The only candidate carried forward is **support-complete temporal C2**:

1. preserve the canonical ratio-of-sums EE, fixed \(\lambda_0\), shared
   \(\kappa\), \(H^c=4\), and the existing downstream target \(\zeta_{2,u}\);
2. preserve hold-while-legal followed by monotone branch-local Main release;
3. at each sealed C2 anchor/focal state, keep the contemporaneous Main action
   as the common reference and enumerate every legal non-Main action as a
   matched temporal sibling;
4. train only a fresh Q2 on these siblings with the same pairwise loss and
   architecture; keep Q1 and Q3 byte-frozen;
5. retain the direct unweighted `Q1 + Q2 + Q3`, common mask, and one argmax at
   deployment.

This is not yet an authorized implementation or efficacy claim.  It is the
minimal design that aligns the C2 training question with the action ranking
Q2 is required to perform.

## Falsifiable continuation and stop rule

Before any C2 retraining, one fresh TRAIN-only action-census probe must be
sealed.  It must enumerate legal temporal siblings on a small non-overlapping
world block and report the old Q2 ranking against the physical \(\zeta_2\)
ranking.  Its thresholds, seeds, anchors, and service diagnostics must be
fixed before outcomes are opened.

- If fresh sibling outcomes show that the old Q2 off-pair choices have
  material temporal regret and that positive better-ranked siblings exist,
  one support-complete Q2 remediation cycle is authorized.
- If the fresh probe does not support that mechanism, this exact
  support-complete-temporal formulation stops immediately; no learning-rate,
  rung, or state search is allowed for it.  C2 itself is mandatory and returns
  to a newly preregistered formula/physics redesign rather than being removed.
- After one support-complete Q2 is trained, it receives one frozen marginal
  C2 gate.  A second stable failure ends this C2 formulation.

C1 and C3 remain frozen throughout.  No parameter sweep or
1500/3000/9000-episode run is authorized by this diagnostic.

The method-level acceptance condition is three useful Catfish routes, not a
two-route fallback.  Therefore formulation-level stopping is a guard against
post-outcome tuning, never an authorization to publish or deploy without C2.
