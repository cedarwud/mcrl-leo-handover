# Adjudication round (codex gpt-6-astra, read-only): attribution of the C3-S v1 gain and its consequence for the V025 C3 design

You are an adversarial peer reviewer. The controller states its position below and expects you to argue, not defer. Working directory `/home/sat/mcrl-v023-astra-attribution/` holds the package; the receipts are readable at `/home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/multi-catfish-v023-c3s-screen/diag2-run-*/units/*/receipt.json` (immutable) and the code at `/home/sat/mcrl-v023-codex-ws-c3s-baselines/`. Recompute anything you rely on; do not trust the controller's aggregation.

## Package
- `DIAG-RESULT-SUMMARY-2026-09-08.md` — diag2 final numbers and the controller's verified/inferred split.
- `C3S-CADENCE-AUDIT-2026-09-08.md` — fresh-context code audit (gpt-5.6-sol) of decision cadence and information parity.
- `DIAG3-MECHANISM-SEPARATION-DECLARATION-2026-09-08.md` — the pre-declared reading for the running diag3 arms.
- `diag2_summary2.py` — the controller's independent aggregation (so you can check it against the receipts).
- `OUTSIDE-ROUND6-CHATGPT-QA-2026-09-08.md` — the outside opinion whose "deployable information gap" and "double counting" points bear on this.

## Controller position (argue against it)
1. The v1 gain (+2.9 %) is attributed away from renewal premium, churn and harness defect with high confidence: forced renewal collapses to exactly zero under anchor ablation while LITE is unchanged; NULL is bit-exact.
2. The phase-monotone slope reflects the growing value of exact current-slot evaluation as the frozen dwell representation ages; it is not a cadence artefact (verified) and not accounting misalignment (audited).
3. Whether the value is multi-user coordination (b) or exact single-user rescoring (d) is undetermined; diag3 will decide under the declared ⅔/⅓ reading.
4. **Design consequence:** if (d) dominates, the successor C3 cannot be sold as "coordination"; it is an exact-model evaluator that corrects the learned heads. Under the V025 successor the correct response is then to (i) give the learned heads the information LITE uses (current-profile joint physics features, not lagged background), and (ii) define C3's target strictly as the interaction share (Ψ/2; stage-2 decision item 5) so that the coordinator's claimed marginal is only what the heads cannot express. If (b) dominates, the sealed set-level coordinator stands.
5. The controller does not intend any additional legacy-physics diagnostic after diag3; the V025 matrix is the next evidence.

## Questions
A. Is the attribution in point 1 sound? Name any remaining artefact hypothesis consistent with all four arms and the placebo (e.g. beam-count accounting, served-set differences under the anchored physics, the 29 outage user-steps in anchored BASE).
B. Is the diag3 reading (⅔/⅓ of g) a defensible pre-declared decomposition, given that unilateral-only and evacuation-only catalogues are not nested interventions and their gains need not add? Propose the exact statistic you would accept instead, before the results exist.
C. Under (d), is the controller's design consequence (features to the heads + interaction-only C3 target) the right response, or does it make C3 unfalsifiable (the heads absorb everything and C3's marginal becomes zero by construction)? What would a genuine, falsifiable C3 claim look like in that regime?
D. For the V025 matrix: which certificates from the physics regime map (U1, J1, S0, per-cell usable-energy range) must be positive before training is admitted, and which of them would a (d)-dominant reading of diag3 change?
E. Rank the three hypotheses (b), (d), mixed, with your prior probabilities and the single observation that would most move you.

Deliverable: write your verdict as the final message (the wrapper stores it). One line at the end: `VERDICT: ATTRIBUTION={SOUND|UNSOUND:<why>} | DIAG3_READING={ACCEPT|REPLACE:<statistic>} | DESIGN_UNDER_D={ACCEPT|REJECT:<why>} | ADMISSION_CERTIFICATES=<list>`.
