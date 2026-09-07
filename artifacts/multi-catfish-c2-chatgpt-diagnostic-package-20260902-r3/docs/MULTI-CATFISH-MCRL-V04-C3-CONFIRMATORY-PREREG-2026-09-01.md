# Multi-Catfish MCRL V0.4 C3 confirmatory preregistration

Date: 2026-09-01  
Status: frozen pre-outcome work order; no confirmatory episode opened

## Question and frozen candidate

This evaluation asks one question only:

> Does the already sealed gate-selected C3 head improve canonical
> ratio-of-sums EE when added to the same frozen Q1/Q2 heads?

The candidate is fixed before opening any new episode:

- source authority:
  `artifacts/multi-catfish-v04-c3-source-20260901-r2`;
- learnability authority:
  `artifacts/multi-catfish-v04-c3-learnability-20260901-r2`;
- selected Q3 rung: 100 for initialization seeds `2026092101`,
  `2026092102`, and `2026092103`;
- Q1/Q2: the same authenticated V0.3 rung-10 heads already embedded in each
  selected hybrid;
- prior bounded screen result SHA-256:
  `ab232f72e562e5a9aa4b68ec8074c5556691ffb1272ae92ec5efd651e76a2177`.

No source-training update, checkpoint selection, source regeneration,
architecture change, learned route weight, or post-action coordinator is
allowed.  The rejected additional-update checkpoints from the bounded screen
are inadmissible.

## Why a fresh confirmatory block is required

The first bounded screen was promising but not confirmatory.  Its primary
pooled EE contrast was `+20.73%`, but one initialization was negative and the
strict per-pair service guard failed once.  In addition, its keyed-fading root
included the initialization seed.  FULL and DROP-C3 were correctly matched
inside each initialization, but different Q3 initializations did not see the
same physical fading worlds.  This follow-up removes that avoidable source of
cross-initialization variance without changing the model or endpoint.

## Frozen evaluation design

- arms: `FULL = Q1 + Q2 + Q3` and `DROP_C3 = Q1 + Q2` only;
- evaluation seeds: exactly `2026092501`--`2026092530`;
- ephemeris split: TRAIN only; no validation-source row and no TEST split;
- three frozen initialization-specific hybrids;
- 100 users, 10 decision steps per episode;
- one common safe action mask and one masked argmax in both arms;
- identical environment RNG, mobility RNG, episode start, and keyed-fading
  field for both arms and all three model initializations at one evaluation
  seed;
- keyed-field root components:
  `V04_C3_CONFIRMATORY_V1`, sealed gate authority SHA-256, and evaluation seed;
  initialization seed and policy label are deliberately excluded;
- no gradient and no replay write.

This creates 30 physical worlds, each evaluated by three frozen models under
two matched arms, for 180 ten-step episodes.

## Endpoints and estimators

The primary endpoint is the canonical pooled ratio-of-sums contrast:

\[
\Delta_{\eta}
=
\frac{\sum B^{\mathrm{FULL}}}{\sum E^{\mathrm{FULL}}}
-
\frac{\sum B^{\mathrm{DROP\text{-}C3}}}{\sum E^{\mathrm{DROP\text{-}C3}}}.
\]

Report the absolute contrast and percentage contrast.  Also report:

- the same ratio-of-sums contrast separately for all three initializations;
- per-world paired EE contrasts and their median/sign count;
- total delivered bits and total energy;
- served fraction and outage;
- action-trace digests and exact shared fading-field digests.

Use a deterministic paired seed bootstrap with 10,000 replicates and bootstrap
seed `2026092599`.  Each replicate resamples the 30 physical-world seeds with
replacement, retains all three frozen initializations for every sampled world,
and recomputes the pooled ratio-of-sums percentage contrast.  The reported 95%
interval is the 2.5th and 97.5th percentile.  The bootstrap does not select a
model, threshold, seed, or checkpoint.

## Predeclared decision rule

`CONFIRM_C3` requires all of the following:

1. pooled `FULL` ratio-of-sums EE is strictly greater than `DROP_C3`;
2. at least two of three initialization-specific ratio-of-sums contrasts are
   strictly positive;
3. the median per-world paired EE contrast is strictly positive;
4. the lower bound of the deterministic paired-seed 95% bootstrap interval is
   strictly positive;
5. pooled FULL served fraction is not below pooled DROP-C3 served fraction,
   and at least two of three initialization-specific served-fraction contrasts
   are nonnegative.

Per-world service losses remain mandatory diagnostics but are not a fatal
guard.  Requiring zero service loss in every one of an enlarged set of physical
worlds would test policy identity rather than pooled service non-inferiority.
This rule is frozen before the fresh seed block is opened and does not
reinterpret the prior one-of-30 strict-guard failure.

Any failed item yields `C3_PROMISING_NOT_CONFIRMED`.  Authentication,
non-finiteness, broken matching, a changed tensor, a replay write, or any TEST
opening yields `INVALID_CONFIRMATORY_RUN` rather than a scientific result.

## Promotion boundary

`CONFIRM_C3` authorizes implementation and execution of one frozen-policy
matched route ablation with `FULL`, frozen Main baseline, `DROP_C1`, `DROP_C2`,
and `DROP_C3`.  It does not authorize additional C3 training or a
1500/3000/9000 run.  A non-confirming outcome keeps the formula-first C3
mechanism as measured but unresolved and blocks the broader efficacy claim.
