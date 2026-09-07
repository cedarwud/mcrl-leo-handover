# GPT closure rulings for B6, P6, and the corrected re-freeze (2026-08-24)

**Conclusion first:** the controller instruction `直接按照你的建議進`
authorizes the previously proposed conservative closure below.  It authorizes
one corrected, traceable re-freeze and the resulting server run; it does not
turn missing Q-C or G-5 definitions into invented gates.  The 2026-08-23
artifact remains byte-preserved as historical evidence.

This record is explicit about provenance: the controller authorized adoption
of the assistant's recommendation, but did not dictate every operational
constant verbatim.

## R-1 — B6 candidate identity cadence

The four NORAD slot identities are rebuilt from the latest D2 snapshot at each
dwell boundary, then remain fixed until the next boundary.

- D2 continues its 640 ms internal updates throughout the dwell.
- At every 30.08 s decision, current D2 eligibility, margin, TTT counter,
  range rate, ECEF geometry, visibility, pointing, and masks are refreshed for
  the four cached identities.
- A cached identity that becomes D2-ineligible stays in the same slot but that
  slot is immediately unoccupied/masked.  A newly eligible satellite cannot
  replace it before the next dwell boundary.
- If the same cached identity becomes eligible again before the boundary, its
  same row becomes selectable again.
- If all four cached identities are ineligible, the user is declared starved
  and executes the existing no-op contract.  There is no silent replacement.
- At the next boundary, the latest D2 state rebuilds the four identities.  The
  normal incumbent-first rule applies if the incumbent is currently eligible.
- Passing a within-dwell frozen window into a boundary resolve is a contract
  error; it must not conceal a missed rebuild.

This separates identity presence from current eligibility: a NORAD ID can be
present in the cached window while its action rows are invalid.

## R-2 — P6 operational protocol and LR selection

P6 has exactly three arms, in declared order:
`alpha = (0.01, 0.003, 0.001)`.  Each arm trains for the frozen 9000 episodes
with one matched training/environment/mobility seed triplet.  This preserves
the authorized approximately 40-hour budget for three P6 arms plus one main
run; adding three full training replicates per arm would be a new experiment,
not this closure.

- Evaluate only the final-episode policy; do not select an observed-best
  checkpoint.
- Evaluate all finite arms on the same ten train-split seeds.  Holdout data is
  excluded.
- The primary score is the mean final-policy **calibrated scalar reward** over
  those ten seeds.  Raw objective and scalar rewards remain reported.
- Exclude an arm if training is non-finite, incomplete, or lacks all ten finite
  primary scores.  `alpha = 0.01` is expected, but not forced, to terminate on
  the existing non-finite guard.  If no arm remains, stop; do not launch main.
- Maximize the primary mean.  An exact tie follows the declared sweep order
  `(0.01, 0.003, 0.001)`.
- Near-tie, perturbation, and cross-seed rankings are diagnostics only.  They
  never override the primary score or exact-tie order.

The random near-tie control is defined per user and decision over currently
valid actions.  Action `a` joins the near-tie set when
`(Q_top - Q_a) / (Q_top - Q_bottom) <= 0.01`; a flat valid-Q row puts every
valid action in the set.  Selection is uniform from a dedicated RNG while the
paired greedy rollout uses matched environment and mobility streams.

Perturbation applies iid zero-mean Gaussian noise with
`sigma = 0.01 * (Q_top - Q_bottom)` to the valid scalarized-Q row, using 32
replicates per user/decision.  Report greedy-action retention and Kendall tau
over originally non-tied action pairs.  Across evaluation seeds, report modal
LR order fraction and Kendall W.  None has a pass threshold in this run.

After P6 selects the learning rate, start a separate 9000-episode main run
with the frozen main seeds.  No CLI or runtime default may choose the main
learning rate.

## R-3 — One corrected re-freeze, without rewriting history

Create `artifacts/PREREG-FROZEN-2026-08-24.json` as the new canonical contract.
It must:

1. supersede, but never edit or delete,
   `artifacts/PREREG-FROZEN-2026-08-23.json`;
2. record the old self-digest
   `d35ddaffda580c8c109f758372956d41aa947b9eb3915d742f3f5f9b7aaecf08`;
3. correct the stale P2 sentence from `N = 3` to the already resolved `N = 4`;
4. include R-1 and the executable P6 protocol in R-2; and
5. carry its own valid self-digest and remain overwrite-refusing.

This is a correction/protocol completion made visible after the original
freeze.  It must not be described as if the 2026-08-23 digest had already
committed to these missing definitions.

## R-4 — Q-C and G-5 audit boundary

The currently permitted authority set contains no active Q-C owner and no
current G-5 definition.  Therefore:

- `assert_ready_to_train()` continues to gate Q-D/Q-E/Q-F/Q-G;
- behavioral acceptance remains G-1–G-4 and G-6–G-12; and
- Q-C/G-5 are recorded as authority/coverage gaps, not failed runtime gates.

No placeholder behavior, test, threshold, or synthetic closure is added for
either label.  A future controller definition would be new authority and a
separate change.
