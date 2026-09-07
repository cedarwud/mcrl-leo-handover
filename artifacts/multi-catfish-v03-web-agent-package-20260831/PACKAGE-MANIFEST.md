# Multi-Catfish MCRL V0.3 package manifest

Package date: 2026-08-31  
Purpose: self-contained concept, paper, figure/deck, implementation-audit, and
evidence-boundary handoff for a fresh web agent.

## Entry points

- `AGENTS.md`: binding package behavior and claim limits.
- `START-HERE.md`: authority order, task-specific read paths, and the
  12-question understanding check.
- `WEB-AGENT-PROMPT.md`: copy-paste prompt for a fresh agent.
- `FRESH-READER-QA.md`: independent fresh-context result and final-delta
  verification boundary.
- `MANIFEST.sha256`: exact integrity list for every other package file.

## Authoring authority

The `docs/` directory contains:

- the current authority index;
- the V0.3 EE-axis formula contract and Opus co-design rationale;
- the algorithm specification;
- the paper-authoring contract;
- the active cross-chapter symbol table with the V0.3 notation extension;
- the F1--F8 figure/deck handoff;
- the source-control and C2 cross-model reviews;
- the sealed fixed-hold C2 result, reactive-release decision, and V0.3B
  implementation receipt;
- the C3 formula-first census.

For paper, slide, and figure math, use the active symbol table and paper
contract. In particular:

\[
i=\text{generic/non-focal user},\quad
v=\text{beam},\quad
\zeta_{j,u}=\text{route target},\quad
\eta^N=\frac{\mathcal B}{\mathcal E},\quad
\Phi_u=\sum_{j=1}^{3}Q_j.
\]

Schema keys such as `z1`, `z2`, and `z3` are retained in receipts and code only.

## Implementation and tests

The `implementation/` and `tests/` directories are selected source snapshots,
not a full runnable simulator checkout. They cover:

- EE-surplus target accounting;
- three-route pairwise zero-bootstrap learning;
- canonical branch-independent keyed fading;
- the fixed-hold C2 chronology/core/runtime/trainer path used by the sealed
  gate;
- the isolated V0.3B hold-while-legal release, option, learner, persistence,
  and training-step path;
- the C2 gate runner and C3 formula-first probes;
- matching targeted tests.

### Repository-to-package path map

Paths in provenance receipts refer to the live repository. Use this map when
reading the self-contained snapshot:

| Live repository path | Package snapshot path |
|---|---|
| `src/mcrl/algorithms/ee_axis_pairwise.py` | `implementation/src/ee_axis_pairwise.py` |
| `src/mcrl/runtime/ee_surplus_targets.py` | `implementation/src/ee_surplus_targets.py` |
| `src/mcrl/env/keyed_fading.py` | `implementation/src/keyed_fading.py` |
| `src/mcrl/env/step.py` | `implementation/src/step.py` |
| `.scratch/c2-v03/*.py` | `implementation/c2/*.py` or `tests/test_c2_*.py` |
| `.scratch/ee-axis-redesign/run_*.py` | `implementation/probes/run_*.py` |
| `tests/test_w36_*.py`--`tests/test_w40_*.py` | `tests/test_w36_*.py`--`tests/test_w40_*.py` |
| `artifacts/c2-v03-gate-20260831/*` | `evidence/c2/*` |
| selected `artifacts/smc-er-c1-authority-20260828/*` receipts | `evidence/c1/*` |

The mapping is for navigation only; it does not turn the package into a full
runnable checkout.

At package freeze, the hold-while-legal C2 release amendment is implemented in
the isolated V0.3B path and 256/256 targeted tests passed. It is not yet
represented by a new sealed fresh-seed physical-headroom receipt. Do not infer
physical headroom, learnability, or efficacy from implementation tests or the
old fixed-hold evidence.

## Evidence

- `evidence/c1/`: compact lineage, source-gate, pretransfer, and development
  receipts; not a current V0.3 held-out efficacy proof.
- `evidence/c2/`: sealed five-seed fixed-hold preregistration, schedules, result,
  and hashes; outcome is `INDETERMINATE`.
- `evidence/c3/`: formula-first physical-opportunity receipt; not learned
  efficacy.

No file in this package proves that Multi-Catfish improves held-out EE.
Chapter 5 efficacy curves remain `TBD`.

## Integrity and reproducibility boundary

Verify `MANIFEST.sha256` before use. The package intentionally omits large C1
NPZ corpora, baseline checkpoints, TLE bundles, Python environments, and the
rest of the simulator. It is sufficient for understanding, method writing,
figure/deck authoring, and bounded source/test inspection; it is not sufficient
to reproduce long training from scratch.
