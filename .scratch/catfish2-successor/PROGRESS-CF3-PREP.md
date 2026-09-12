# PROGRESS — CF3-PREP (design-only lane)

Lane: CF3-PREP. Design-only, read-only. Deliverable is a single design note,
`.scratch/catfish2-successor/CF3-PREP-DESIGN-NOTE-2026-09-12.md`.

Constraints acknowledged and held: **no candidate outcome collection of any
kind** (no P0, no disagreement measurement, no `A_repr` fit, no clone, no
rollout), no learner training, no new threshold/constant/coefficient, no source
admission, no Amendment-15 reopening, **no `sat` compute**, no writes to
`-cf2s*` / `-dev` / `-b1` / `-cf3` worktrees (read only).

## Log

- [step 1] Lane opened. Progress file created. Beginning the required reads.
- [step 2] Read, in full: `PHASE-B0-TDELTA-2026-09-12.md` (found in the
  `cf2s-b0` worktree, not in the main tree), `CONTROLLER-TDELTA-CLOSE`,
  `CONTROLLER-TTAIL-CLOSE`, `CONTROLLER-TNEXT-ADMIT`, Amendment 15, Amendment 11.
- [step 3] Code audit, read-only, from the `cf2s-b0` worktree (base `27f69edf`;
  `cf_credit.py` byte-identical to the b1 tip `63b02dc0`):
  `src/mcrl/algorithms/cf_credit.py`, `cf_teacher.py`, `src/mcrl/env/step.py`
  (`evaluate_actions`, `evaluate_actions_without_user`, `_evaluate_selected_actions`,
  `_resolve_physics`), `src/mcrl/env/service.py::resolve_service`,
  `src/mcrl/env/action_contract.py`, `src/mcrl/runtime/state_encoding.py`,
  `src/mcrl/env/link_budget.py` (power constants only).
  Lane scripts read: `cf2s_common.py`, `cf2s_tdelta.py` (B0), and the structure
  of `ttail_common.py` / `ttail_clone.py` (Lane Q) for the `A_repr` and
  T0-imitation-floor protocol.
- [step 4] Context reads for existing measurements of the nearest relatives:
  `.scratch/catfish2-discovery/STAGE0-2026-09-12.md` §2 arm table
  (`B1_NO_NEW_BEAM` = LP-prev(c→∞) and `MAX_NOMINAL_GAIN` = LP-prev(0) rows) and
  `RESULTS-REGISTRY.md` LP-09 / LP-16 / EC-01 / EC-02. **This turned up the
  precedent the note nearly missed**: Stage 0 §6(a) already ran this exact
  bisection of T0 into a pure-bits and a pure-energy endpoint, and rejected it
  ("the `c = 1` mixture, not either term, is where the value sits"). Written up
  as note §6.4, including the required check of whether the cause of that old
  failure exists at the counterfactual information level.
- [step 5] Note written and committed. **Nothing was executed**: no script was
  run, no environment constructed, no episode rolled, no fit performed, no `sat`
  process started. Every number in the note is either quoted from a committed
  report `[R]` or plain arithmetic on such numbers `[D]`.
