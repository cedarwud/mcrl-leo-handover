# Start here: Multi-Catfish MCRL V0.3

Package date: 2026-08-31  
Purpose: self-contained context for algorithm explanation, Chapter 4 writing,
scientific figure/deck authoring, and implementation/evidence audit.

## Current status in one paragraph

Multi-Catfish MCRL V0.3 keeps canonical ratio-of-sums EE as its sole endpoint
and decomposes one matched focal intervention into focal opening surplus
(C1/Q1), downstream full-system surplus (C2/Q2), and non-focal opening rate
externality (C3/Q3). Three independent online Q functions learn route-local
pairwise targets and are summed before one safe masked Main argmax. The formulas
and authoring architecture are current. EE efficacy is not proven and training
is `NO-GO`. The fixed-hold C2 keyed gate is sealed `INDETERMINATE`.
The hold-while-legal, monotone branch-local release amendment is implemented
in the isolated V0.3B path and 256/256 targeted tests passed, but its fresh-seed
physical-headroom gate is still pending.

The retained pre-V0.3 C1 lineage also has a sealed one-seed, four-episode
developmental-screen decision of `STOP_AND_REDESIGN_C1`, with the strict
ceiling `ONE_SEED_4EP_DIRECTIONAL_SCREEN_NOT_ROUTING_AUTHORITY_NOT_CHAPTER5`.
Treat it as diagnostic history only: it neither proves current V0.3 efficacy
nor authorizes Catfish routing or training.

## Authority precedence

When two files appear to disagree, use this order and report the lower-level
text as superseded rather than merging it silently:

1. `docs/CURRENT-MULTI-CATFISH-AUTHORITY.md`
2. `docs/MULTI-CATFISH-MCRL-V03-C2-POSTGATE-DESIGN-DECISION-2026-08-31.md`
   `docs/MULTI-CATFISH-MCRL-V03-C2-REACTIVE-RELEASE-IMPLEMENTATION-2026-08-31.md`,
   and `docs/MULTI-CATFISH-MCRL-V03-C2-GATE-RESULT-2026-08-31.md`
3. `docs/MULTI-CATFISH-MCRL-V03-ALGORITHM-SPEC-2026-08-31.md`
4. `docs/MULTI-CATFISH-MCRL-V03-PAPER-AUTHORING-CONTRACT-2026-08-31.md`
5. `docs/ACTIVE-SYMBOL-TABLE-2026-08-31.md`
6. `docs/MULTI-CATFISH-MCRL-V03-FIGURE-DECK-HANDOFF-2026-08-31.md`
7. EE-axis rationale, co-design, source-control, C3 census, implementation,
   tests, and raw receipts.

Nothing outside this package is needed for concept/authoring work. A source
path mentioned inside a copied receipt is provenance, not permission to load a
different or archived algorithm description.

## Read paths by task

### Explain the complete algorithm or write Chapter 4

Read, in order:

1. current authority;
2. algorithm spec;
3. paper-authoring contract;
4. C2 post-gate design decision;
5. EE-axis redesign contract for rationale.

### Draw figures or build the English deck

Read the concept path, then the figure/deck handoff. Preserve its F1--F8
semantics, Times New Roman sizing contract, editable formulas, one-action
deployment, neutral-source ablations, and `TBD` result boundary. The C2 figure
must show planned or support-triggered monotone release and remain editable
until the fresh-seed gate is sealed.

Use the paper symbols in the active symbol table: \(i\) is a non-focal user
index, while \(v\) remains a beam index; \(\zeta_j\) is a route target, while
\(z_{s,v}\) remains beam activation; \(\mathcal B/\mathcal E\) are aggregate
bits/energy; and \(\Phi_u\) is the deployment score. Receipt fields named
`z1`/`z2`/`z3` are schema identifiers, not paper notation.

### Audit formula or code conformance

Read the paper notation table and EE-axis contract, then inspect:

- `implementation/src/ee_surplus_targets.py`;
- `implementation/src/ee_axis_pairwise.py`;
- `implementation/src/keyed_fading.py` and `step.py`;
- `implementation/c2/` and `implementation/probes/`;
- the matching files under `tests/`.

The implementation bundle proves only the behavior covered by those tests.
It shows the V0.3B release policy is coded and targeted-test green; it does not
prove fresh-seed physical headroom, learnability, or efficacy.

### Judge evidence or efficacy

- C1: read `evidence/c1/README.md` first; retained legacy receipts are lineage
  and diagnostic evidence, not current V0.3 efficacy.
- C2: read the gate-result and post-gate decision docs, then
  `evidence/c2/prereg.json` and `result.json`.
- C3: read the formula-first census doc and `evidence/c3/` receipt.

No evidence branch currently proves held-out Multi-Catfish EE improvement.

## Package limitations

The package is sufficient to understand and review the current algorithm,
write the method chapter, and author scientifically correct figures/slides. It
is also sufficient to inspect the implemented formula, learner, keyed-fading,
and fixed-hold C2 gate surfaces. It is not a runnable full simulator checkout,
does not include the large C1 NPZ corpus or baseline checkpoints, and cannot by
itself reproduce long training.

## Understanding check

Before claiming complete understanding, answer these with file-level evidence:

1. What is the sole endpoint, and why is it ratio-of-sums?
2. Why are C1/C2/C3 not three legacy objectives?
3. What are \(\zeta_{1,u}\), \(\zeta_{2,u}\), and \(\zeta_{3,u}\), including their units and exact
   non-overlap identity?
4. What informed and neutral source mechanism belongs to each route?
5. What do `D^o`, `D^t`, and `D^a` store, and which may send gradients?
6. How does the pairwise zero-bootstrap loss update exactly one Q function?
7. Why are there three Q outputs but only one executed action?
8. What do `M0`, `N000`, `F111`, `A011`, `A101`, and `A110` mean?
9. Why is the sealed C2 result `INDETERMINATE` even though positives appear in
   5/5 seeds?
10. Why is hold-while-legal release causal and non-look-ahead, what is already
    implemented/tested, and what fresh scientific gate remains pending?
11. Which claims are specified, implemented, gate-observed, or still `TBD`?
12. Are all paper symbols drawn from the notation contract, with code/schema
    identifiers kept outside the mathematical symbol set?
