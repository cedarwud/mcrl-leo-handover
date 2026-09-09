You are building the tool that makes every future question in this project cheap. Work in the current directory. Interpreter `/home/sat/mcrl-leo-handover/.venv/bin/python`, `PYTHONPATH=src`, `nice -n 15`. Never modify `/home/sat/mcrl-leo-handover` or its virtual environment.

`DIAGNOSTIC_NOT_CLAIM`. **No scientific claim, no efficacy measurement and no training run is authorised.** You are building and validating a measurement instrument. Change no constant, threshold, sign, seed, horizon, price, service guard or acceptance rule in the sealed physics, and modify no sealed artefact or frozen manifest.

# The problem you are solving

Over the last day this project answered roughly a dozen questions, and each one cost a separate agent between twenty and ninety minutes. Almost all of that time went into work that was identical every time: rebuilding a workspace, re-reading the same physics, re-writing an evaluation loop, and re-deriving pooled figures from receipt JSON by hand. The scientific content of each answer was a few numbers.

Build the standing harness that removes that cost.

# What exists to build on

Scattered across sibling workspaces `/home/sat/mcrl-v025-*-ws` are working implementations of the pieces: a bounded coalition/oracle set selector, an iterated unilateral selector with a complete-neighbourhood certificate, a neutral control arm, real world tapes, and a twenty-anchor evaluation panel whose receipts are at `/home/sat/mcrl-v025-ladder-ws/.scratch/ladder-floor-20260910/original-result.json` and `margin-result.json` (same schema, twenty anchors, arms `BASELINE`, `UNILATERAL`, `ORACLE_SET`, each carrying `bits`, `joules`, `served_count`, `ee_bit_per_j`). Read those first; they define the output contract you must preserve.

Copy what you need into this workspace. Do not modify the sibling workspaces.

# Deliverables

**H1 — one command, one panel, one table.** A single entry point that takes a named physics variant and a set of arms and returns pooled bits, joules, energy efficiency, served count and the arm-over-arm relative gains on a fixed anchor panel, plus per-anchor rows. It must write a receipt JSON in the schema above, with a SHA-256, the world digests, and the variant name recorded inside. Reproducing an existing published number must be a single command; demonstrate that by reproducing the archived `+6.3590%` oracle-over-unilateral figure from the original formulation and printing the match.

**H2 — a named physics-variant seam.** Register variants by name, defaulting to `SEALED`, which must be **bit-identical** to the sealed path — prove it with an assertion over bits, transmissions, mode counts and maximum radiated power, exactly as the ladder work did. Register a second variant `MARGIN_Q` that provisions against the threshold divided by the same fading quantile the mode selection is later judged at. Adding a third variant later must be one small file, touching nothing else.

**H3 — make the second and later runs cheap.** Profile where the time actually goes on this panel, then cache whatever is invariant across variants and arms — the geometry, the gains, the per-boundary link inputs — keyed by a digest of its inputs, so that changing only the provisioning rule does not recompute what the provisioning rule cannot affect. Report the measured before-and-after wall time for a full panel run and state exactly what is cached and what is proved to be variant-independent. If something you expected to be cacheable is not, say so and say why.

**H4 — a declared screen ladder.** Define a two-anchor screen and the fixed rule by which a screen result promotes to the full panel. The rule must be written down **before** any use and must be stated in the report, so no future result can be promoted because it looked good. Measure the screen's agreement with the full panel on the two variants you have.

**H5 — a query layer.** A small command that answers, from stored receipts without recomputation: pooled figures for any stored run, the difference between any two runs, and the per-anchor distribution of any arm-over-arm gain including the count of negative anchors. Today those were computed by hand each time.

# Rules

- Every number the harness prints must be reproducible from a receipt it wrote.
- The `SEALED` bit-identity proof is the deliverable that matters most; without it nothing the harness says can be trusted.
- Do not tune, rank or recommend anything. This is an instrument, not an experiment.
- Prefer boring, reviewable code over cleverness.
- Report exact command lines and their output.
- Say plainly what you did not build.

Write `EVAL-HARNESS-2026-09-10.md` in this workspace root and print it in full as your final message, leading with one line: whether `SEALED` is bit-identical and what a full panel run now costs.
