# Multi-Catfish V0.3 package instructions

This package is the current read-only understanding and authoring authority for
Multi-Catfish MCRL V0.3. It does not authorize training, change scientific
gates, or prove EE efficacy.

## Required process

1. Verify `MANIFEST.sha256` before relying on package contents.
2. Read `START-HERE.md` completely.
3. Apply the authority precedence in `START-HERE.md`; report conflicts instead
   of silently blending versions.
4. Follow the branch matching the task:
   - concept or method writing: current authority, algorithm spec, paper contract;
   - figures or slides: add the figure/deck handoff;
   - formula rationale: add the EE-axis redesign and co-design records;
   - implementation audit: add `implementation/` and `tests/`;
   - evidence claim: add the matching `evidence/` receipts and gate-result doc.
5. Keep four statuses separate in every answer: specified, implemented,
   gate-observed, and held-out efficacy-proven.

## Binding invariants

- Canonical ratio-of-sums EE is the only endpoint.
- C1/Q1 is focal-now, C2/Q2 is everyone-later, and C3/Q3 is non-focal-now.
- Catfish routes generate training comparisons; they are not deployment agents
  or additional Q networks.
- V0.3 has exactly three independent online Q functions and executes one
  service-masked Main action from their summed score.
- C1/C2/C3 are non-overlapping views of one matched focal intervention, not
  three legacy rewards that must all improve.
- Deployment contains no auction, coordinator, vote, joint decoder, matching,
  or post-training override.
- The sealed fixed-hold C2 gate remains `INDETERMINATE`. The selected
  hold-while-legal release amendment is implemented in the isolated V0.3B path
  and 256/256 targeted tests passed, but its fresh physical-headroom gate is
  pending.
- Numerical efficacy, Chapter 5 curves, unfrozen hyperparameters, and any claim
  that Multi-Catfish improves EE remain `TBD`.

Use mathematical symbols from
`docs/ACTIVE-SYMBOL-TABLE-2026-08-31.md` and the notation table in the
paper-authoring contract. In particular, preserve \(i\) for non-focal users,
\(v\) for beams, \(\zeta_j\) for route targets, \(\mathcal B/\mathcal E\) for
aggregate bits/energy, and \(\Phi_u\) for the deployment score. Code/schema
fields such as `z1`, `release_offset`, and `candidate_sinr` are identifiers,
not new mathematical notation.

## Completion criterion

Do not claim complete understanding until all questions in the
`Understanding check` section of `START-HERE.md` can be answered consistently
with file-level evidence, and the answer contains no archived topology,
legacy-r2/r3 objective, six-Q, or post-training-coordination interpretation.
