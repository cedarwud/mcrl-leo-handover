# Goal

Perform a fresh-context, read-only process audit of the current Multi-Catfish V0.23 R7 launch-repair flow. Determine whether the revised flow is the smallest sufficient route to a scientifically valid LC-SRS gate, whether it still allows late integration failures, or whether it has overcorrected into unnecessary production hardening.

This is an implementation/process audit, not a new C3 design exercise.

# Repository and primary evidence

Work in `/home/u24/papers/mcrl-leo-handover`. Read the current files rather than relying on this summary, especially:

- `.scratch/multi-catfish-v023-r7-launch-ready/`
- `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-SUCCESSOR-GATE-CONTRACT-R7-BALANCED-2026-09-06.md`
- `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-R7-LAUNCH-DECISION-2026-09-06.md`
- `.scratch/multi-catfish-v023-r7-launch-ready/R7-INVALID-RUN-I0.json`
- `docs/CURRENT-MULTI-CATFISH-AUTHORITY.md`, only as needed to check that the repair does not alter scientific authority

Inspect `AGENTS.md` and applicable instructions. Resolve conflicts by instruction hierarchy.

# Verified incident sequence to check against the files

1. A first real R7 attempt started all eight source workers but they failed before writing source artifacts because the validated preflight receipt omitted `configuration` and `bindings`; the source adapter also expected a mismatched binding role.
2. That invalid attempt produced no source artifact, no fit/composition result, and no scientific outcome. It is recorded as `R7-INVALID-RUN-I0.json`.
3. The receipt fields and role mismatch were repaired, and a pre-root source-consumer smoke was added.
4. The next pre-root smoke found that the fresh sparse checkout did not contain the package initializers, so the server virtualenv resolved `mcrl` from a different checkout.
5. A local isolated sparse-checkout closure test then found first a missing static import (`mcrl.errors`) and, after static closure repair, a dynamic Path-loaded dependency: `.scratch/multi-catfish-v020-c3-source-audit/run_v020_repriced_c3_gate.py`.
6. A separate interface audit now reports two certain delivery bugs: the dynamic V020 -> V018 -> V015 -> V014/V013 provenance/authentication closure is not fully in the transfer manifest; and an early TLE precheck still inspects `/home/sat/mcrl-leo-handover/src` instead of the fresh `$SERVER_ROOT/src`. It also reports a plausible preregistration path-binding weakness and insufficient R7-specific seam-test coverage.
7. The current intended route is: freeze all science; repair only delivery/interfaces; run a local isolated transfer-closure smoke against the actual source-adapter `_authenticate()`; run a remote pre-root smoke checking `mcrl.__file__`, preflight receipt, TLE, and Q1/Q2 authority; create a run root only after those pass; then launch R7 once. A valid R7 non-GO stops the LC-SRS family; GO proceeds to the already planned five-arm 100-epoch learner screen.
8. C1/C2 target generation is a separate already-running job. C3 neutral-bridge, schedule, and five-arm runner focused tests are green. Do not infer efficacy from those engineering facts.

# Non-negotiable boundaries

- Read only. Do not edit files, SSH, run a simulator, run training, access TEST data, or create a new gate.
- Do not redesign C1, C2, C3, LC-SRS, targets, rewards, formulas, thresholds, worlds, seeds, lambda, kappa, learners, update counts, or acceptance predicates.
- Do not turn optional robustness ideas into launch blockers.
- Scientific authority must remain frozen. Only plumbing fixes are eligible: receipt completeness, role/path alignment, Python import provenance, exact transfer dependencies, preregistration identity binding if definitely required, R7 current-path seam checks, and fresh identities for invalid attempts.
- A prior failure or a green test is not scientific evidence. Keep verified fact, inference, and proposal distinct.

# Questions to adjudicate

1. Is the proposed vertical-slice sequence sufficient to prevent the same class of late integration failures? Name the exact checks that are mandatory before one R7 relaunch.
2. For this inherited dynamic authentication chain, should R7 transfer an exact manifest-bound closure, or copy/refactor it into a self-contained R7 adapter? Choose the fastest safe option for the immediate relaunch; distinguish any later cleanup.
3. Is the preregistration caller-path issue a definite launch-integrity blocker now, or a later hardening item? Base the answer on the actual normal controller path.
4. What is the explicit stop rule for integration hardening—i.e., after which concrete green checks must the controller stop adding gates/tests and launch?
5. Does any current repair appear to change scientific semantics or invalidate the frozen comparison? Cite exact file/line evidence if so.
6. Is the current process genuinely accelerated relative to the prior failure pattern, or merely moving failures earlier while retaining avoidable sequential work? Recommend only bounded changes that shorten time-to-outcome without weakening provenance or scientific validity.

# Output

Start with a 3-6 sentence verdict. Then give:

- `Mandatory before relaunch` — a minimal ordered checklist
- `Do not block relaunch` — optional/deferred items
- `Science-contamination check`
- `Stop rule`
- `One immediate next action`

Be concise but evidence-specific. End with exactly one token on its own final line:

- `FLOW_GO_AFTER_LISTED_FIXES`
- `FLOW_REVISE_MINIMALLY`
- `FLOW_OVERENGINEERED_STOP_AND_SIMPLIFY`
- `FLOW_SCIENCE_CONTAMINATED_STOP`
