You are doing an independent design review of a learner's target definitions. Work in the current directory. Interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, `nice -n 15`. Never modify `/home/sat/mcrl-leo-handover` or its virtual environment.

`DIAGNOSTIC_NOT_CLAIM`. No training run and no policy run is authorised. Change no constant, threshold, sign, seed, horizon, price, guard or acceptance rule; do not modify any sealed artefact. This is a design analysis; you may write throwaway analysis scripts, but you are not implementing a redesign.

# Context

A coordinator ranks candidate joint association changes with a score built from per-user components. Two scalar heads supply per-user quantities:
- `c1_difference_surplus` — the change in the sealed objective when one user unilaterally deviates from the reference configuration;
- `c2_persistence_forecast` — a forward-looking persistence quantity over projected offsets.

Both are defined in `src/mcrl/stagec_v025/`; read the exact production definitions and cite `file:line`. The sealed objective is of the form `F = B - eta*E`, with a coordinator-level potential term added only at ranking time.

Each head is a scalar readout over one fixed numeric feature vector (16 values for the first, 22 for the second) and nothing else.

# The question I want answered

**Not** "which features should we add". A separate piece of work is already answering that. Your question is one level up:

**Given only information available before the candidate configuration is evaluated, what is the best-predictable object for these heads to predict — and is the currently chosen object a good choice?**

The concern is structural. The first head's target is a difference of whole-network outcomes between two coupled-power fixed points. Computing it requires solving the candidate configuration's coupled fixed point, which is exactly the expensive step the head exists to avoid. If that difference is not well-approximable from pre-decision state, then no admissible feature set will make the head accurate, and the correct response is to change **what the head predicts**, not what it sees.

Work through, with evidence from the code and from cheap numerical experiments on existing rows where available:

**Q1. Decomposition.** Write the first head's target as a sum of parts and identify which parts are cheap and which require the coupled solve. Is there a decomposition where the expensive part is small, slowly varying, or common across the candidates being compared at one anchor? If a term is common to all candidates at an anchor, it cancels in the ranking and need not be predicted at all. Quantify this on real rows if you can.

**Q2. Level versus order.** The coordinator uses these values to rank. Determine whether the pipeline needs calibrated values or only a correct ordering — read the code and say which, with citations. If ordering suffices anywhere, say where, and estimate how much easier the ordering problem is on real rows (for example, pairwise-ordering accuracy achievable versus explained variance of the value).

**Q3. Anchor-relative targets.** Consider predicting the target centred within its anchor, or as a rank within the anchor's candidate pool, rather than as an absolute value. Estimate on real rows how much of the total target variance is between anchors versus within anchors. If most variance is between anchors, an absolute-value target is spending the model's capacity on a quantity the ranking never uses.

**Q4. The second head.** Do the same for the persistence forecast. Its target involves per-offset survival with an absorbing rule; assess whether a survival/hazard formulation over offsets is better posed than a single scalar regression, and whether the absorbing structure makes the scalar target discontinuous in a way that a smooth regressor cannot represent.

**Q5. Verdict.** State whether the current target definitions are well-posed for learning from pre-decision information. Choose exactly one per head: `TARGET_WELL_POSED`, `TARGET_REFORMULATE`, or `INDETERMINATE`. If `TARGET_REFORMULATE`, give the specific alternative object and say precisely what would have to change in the pipeline — file by file — and whether any sealed artefact or frozen manifest would be touched. If any would, say so and STOP there rather than proposing to touch it.

# Honesty requirements

- If the current targets are fine and the problem really is only features, say so plainly and early. Do not manufacture a redesign.
- Distinguish what you verified by running code, what you derived on paper, and what you inferred.
- Where you estimate something numerically, give the command and leave the script behind.
- If you cannot reach a question, complete the earlier ones fully and say plainly which you did not reach.

Write `C1C2-TARGET-DESIGN-2026-09-10.md` in this workspace root and print it in full as your final message, leading with the two verdicts on one line.
