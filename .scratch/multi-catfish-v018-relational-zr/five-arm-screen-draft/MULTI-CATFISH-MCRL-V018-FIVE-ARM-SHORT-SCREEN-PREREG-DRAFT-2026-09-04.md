# Multi-Catfish MCRL V0.18 — five-arm short physical screen

**Status:** `DRAFT_NOT_FROZEN_NO_OUTCOME_OPENED`  
**Claim ceiling:** `TRAIN_DEVELOPMENT_EE_RECEIPTS_ONLY_NO_TEST_EFFICACY_CLAIM`  
**Purpose:** post-`PASS_LEARNER_GATE` preparation only.

This is a pre-outcome draft for the first physical screen of the learned
V0.18 relational C3 head. It is not an authorization to open a simulator,
consume a fresh world, run an episode, update a learner, or open TEST. The
parent learner contract and its source-only gate remain authoritative. This
draft owns only the later five-arm score-ablation seam.

## 1. Exact route definition

At one predecision anchor, all route arms use the same native Boolean safe mask
\(\mathcal A_{\mathrm{safe}}(s)\) and one masked argmax. The route score
surfaces are literal unweighted sums:

\[
\begin{aligned}
S_{\mathrm{FULL}} &= Q_1 + Q_2 + Q_3,\\
S_{\mathrm{DROP\_C1}} &= Q_2 + Q_3,\\
S_{\mathrm{DROP\_C2}} &= Q_1 + Q_3,\\
S_{\mathrm{DROP\_C3}} &= Q_1 + Q_2.
\end{aligned}
\]

Each route executes exactly

\[
a^* = \arg\max_{a\in\mathcal A_{\mathrm{safe}}(s)} S(s,a).
\]

`MAIN` is not another Catfish and is not decoded from these surfaces. It is
an independently supplied frozen legacy baseline policy with its own explicit
policy digest and one masked argmax.

The required arm set is exactly:

`FULL`, `DROP_C1`, `DROP_C2`, `DROP_C3`, `MAIN`.

There is no route-count normalization, score rescaling, vote, coordinator,
auction, post-training override, or second action-selection stage.

## 2. Q3 input/reference invariant

The learned Q3 head was trained from the detached reference

\[
r_{12}(s) = \arg\max_{a\in\mathcal A_{\mathrm{safe}}(s)}
               [Q_1(s,a)+Q_2(s,a)].
\]

For `FULL`, `DROP_C1`, and `DROP_C2`, the physical evaluator MUST build the
V0.18 relational Q3 state once at the anchor using this same \(r_{12}\), and
must reuse the same state/reference for all three active-Q3 arms. The
evaluator records a reference-action digest and complete Q3-state digest and
rejects any active-arm mismatch.

This is deliberately a score-head ablation. `DROP_C1` and `DROP_C2` remove
the named Q head only from the final action-score sum; they do not recompute
Q3 under Q2-only or Q1-only context. Recomputing the Q3 input would test a
different state-definition intervention and invalidate the marginal
comparison. `DROP_C3` does not evaluate Q3 and carries no Q3 input digest.

The same three frozen Q1/Q2/learned-Q3 checkpoint lineages are used for every
route arm. `DROP_C3` still records the selected Q3 checkpoint identity for
lineage completeness, but its `q3_evaluated` flag is false. `MAIN` uses only
the independent baseline policy.

## 3. Physical panel, identities, and common randomness

The following values remain explicit placeholders until the source-only
learner gate returns `PASS_LEARNER_GATE`:

```text
learner_gate_result_sha256: <FILL_AFTER_PASS_LEARNER_GATE>
learner_code_manifest_sha256: <FILL_AFTER_PASS_LEARNER_GATE>
evaluation_seeds: <100 fresh TRAIN world seeds, not previously opened>
field_component: <FILL_AFTER_PASS_LEARNER_GATE>
field_root_digests: <one canonical keyed-field root per evaluation seed>
lineage_bindings: <exactly three init/source/Q1/Q2/Q3 checkpoint records>
main_policy_sha256: <FILL_AFTER_PASS_LEARNER_GATE>
```

The implementation refuses missing or implicit values. The three lineage
records must bind distinct initialization seeds and source lineages and must
carry the exact Q1, Q2, and learned-Q3 checkpoint SHA-256 values selected by
the post-gate authority. The post-gate binding step must also authenticate
the learner-gate result as `PASS_LEARNER_GATE`, its contract/code-manifest
closure, the three checkpoint payloads, and the Q3 state schema/config.

The proposed short screen has 100 paired world indices, 100 users, and ten
decision steps per physical episode. For each world index, every route arm is
run once under each of the three frozen route lineages. `MAIN` is run once
with the same world and keyed-fading root; its frozen policy is independent
of route lineage. Thus each route arm has \(100\times3=300\) physical
episodes and `MAIN` has 100 baseline episodes. The same world/field identity
is required across all arms; environment and mobility RNG streams are reset
from the canonical world seed for each matched episode.

The `episode_index` is the paired world index, not an optimizer update. A
checkpoint is written for every arm at each 100-world-index boundary. The
first short screen therefore writes the `episode-000100` checkpoint after all
three route lineages and the matched `MAIN` row for index 100 are complete.

## 4. Endpoint and service metrics

For arm \(m\), pool additive delivered bits and positive total energy across
all of its receipts before computing EE:

\[
\eta_m =
\frac{\sum_{e} B_{m,e}}{\sum_{e} E_{m,e}}.
\]

The evaluator reports, but never substitutes as the endpoint:

- total bits and total energy;
- pooled ratio-of-sums EE in bit/J;
- served user-steps and served fraction;
- outage fraction;
- mean per-episode EE as a descriptive diagnostic only;
- per-lineage route summaries and marginal contrasts;
- action-trace digests and Q3 input/reference digests when supplied.

## 5. Pre-registered acceptance and exact ordering

The desired scientific ordering is **partial**, not a fabricated total order
among the three drops:

\[
\boxed{\eta_{\mathrm{FULL}}>\eta_{\mathrm{DROP\_C1}},\quad
\eta_{\mathrm{FULL}}>\eta_{\mathrm{DROP\_C2}},\quad
\eta_{\mathrm{FULL}}>\eta_{\mathrm{DROP\_C3}}}
\]

and

\[
\boxed{\eta_{\mathrm{DROP\_C1}},
\eta_{\mathrm{DROP\_C2}},
\eta_{\mathrm{DROP\_C3}}
>\eta_{\mathrm{MAIN}}.}
\]

Equivalently, `FULL` must be the highest arm, `MAIN` the lowest arm, and no
rank among the three drop arms is required. The three pooled marginal
contrasts are:

```text
C1 marginal: FULL - DROP_C1 > 0
C2 marginal: FULL - DROP_C2 > 0
C3 marginal: FULL - DROP_C3 > 0
```

For robustness across the three frozen route lineages, each marginal must be
positive in at least two of the three lineage-specific pooled contrasts. The
pooled comparisons are primary for this short development screen; a single
negative lineage is retained as a diagnostic and is not silently discarded.

The physical service guard is pooled service non-inferiority of `FULL` to
each comparator (`DROP_C1`, `DROP_C2`, `DROP_C3`, and `MAIN`). All raw service
losses remain visible. A screen passes only when all four pooled EE/order
comparisons, all three two-of-three lineage marginal conditions, and all four
pooled service conditions pass. The result is still development evidence; it
does not establish held-out efficacy or authorize 9000-episode training.

No sign, seed, threshold, horizon, fading component, route formula, or
acceptance condition may be tuned after any screen outcome. If the screen
fails, the result is recorded under this contract and a new pre-outcome
contract is required before redesign.

## 6. Checkpoint and claim boundaries

Every 100-world-index checkpoint contains the arm, configured episode count,
receipt count, pooled additive summary, split, and all forbidden-boundary
flags. It is an evaluation-progress checkpoint, not a learner checkpoint.

The evaluator and its callbacks must attest:

```text
evaluation_split = TRAIN
test_split_opened = false
episode_training = false
learner_update = false
efficacy_claim = false
```

The evaluator never opens TEST, never updates Q1/Q2/Q3, and never changes a
frozen checkpoint. A passed physical screen authorizes only the next
pre-registered development decision; it does not by itself authorize a
1500/3000/9000 promotion.
