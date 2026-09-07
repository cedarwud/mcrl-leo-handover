# Evidence map

This map separates direct copied sources from current handoff facts and
reviewer inferences. Package paths are relative to this directory.

| Review question / claim | Evidence label | Package source | Original source or provenance | Boundary |
|---|---|---|---|---|
| LC-SRS method definition and Chapter-4 freeze | COPIED-AUTHORITY | `authority/METHOD-FREEZE.md` | `docs/MULTI-CATFISH-MCRL-V023-C3-METHOD-FREEZE-2026-09-05.md` | Method core only; no efficacy |
| One-shot observability/source-to-learner contract | COPIED-AUTHORITY | `authority/LC-SRS-GATE-CONTRACT.md` | `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md` | TRAIN development; TEST/episode training closed |
| R6 correction, preflight, and relaunch boundary | COPIED-AUTHORITY | `authority/R6-RELAUNCH-DECISION.md` | `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-GATE-RELAUNCH-DECISION-R6-FIT-BINDING-2026-09-06.md` | Prepared/conditional launch record; not outcome efficacy |
| Locked response/contingency candidate order | COPIED-AUTHORITY | `authority/CONTINGENCY-LADDER.md` | `.scratch/multi-catfish-v023-c3-observability/V023-C3-RAPID-CONTINGENCY-LADDER-PREOUTCOME-2026-09-06.md` | Pre-outcome design; no current candidate promotion |
| Fable V0.22 C3 post-gate review | COPIED-AUTHORITY | `authority/FABLE-51-C3-POSTGATE-AUDIT.md` | `.scratch/multi-catfish-v022-c3-coalition-residual/FABLE-51-V022-POSTGATE-ADJUDICATION-2026-09-05.md` | Scoped current-slot identity; no learned-Q or population claim |
| Fable C3 source audit and CSE/EC proposals | COPIED-AUTHORITY | `authority/FABLE-C3-SOURCE-AUDIT.md` | `artifacts/multi-catfish-c3-fable-cleanroom-20260904-r1/FABLE-C3-SOURCE-AUDIT.md` | Proposal/audit lane; not canonical authority |
| Root mathematical boundary on Fable CSE exactness | COPIED-AUTHORITY | `authority/ROOT-FABLE-C3-ADJUDICATION.md` | `.scratch/multi-catfish-v020-c3-source-audit/ROOT-FABLE-C3-ADJUDICATION-2026-09-04.md` | Rejects summed-unilateral “exact additivity” overclaim |
| Frozen raw fit-screen metric implementation | COPIED-AUTHORITY | `fast-screen/compute_fit_screen.py` | `.scratch/multi-catfish-v023-r6-fast-screen/compute_fit_screen.py` | Early fit-only screen; not efficacy |
| Five-arm admission and receipt runner | COPIED-AUTHORITY | `five-arm/v023_real_five_arm_episode_runner.py` plus binding/results modules | `.scratch/multi-catfish-v023-episode-screen/` and `.scratch/multi-catfish-v023-five-arm-evaluation/` | Adapter seam; no default real execution |
| Five-arm binding README and episode-screen spec | COPIED-AUTHORITY | `five-arm/FIVE-ARM-EVALUATION-README.md`, `five-arm/EPISODE-SCREEN-SPEC.md` | `.scratch/multi-catfish-v023-five-arm-evaluation/README.md`, `.scratch/multi-catfish-v023-episode-screen/spec.md` | Explicit pre-execution boundary |
| R6 raw sign predicate and exact values | HANDOFF-VERIFIED | `CURRENT-STATUS.md` | Root-agent handoff, 2026-09-06 | Direct result JSON absent at initial check; no rescue |
| Development-only balanced accuracies and label prevalence | HANDOFF-VERIFIED | `CURRENT-STATUS.md` | Root-agent handoff, 2026-09-06 | Diagnostic only; metric must be prospective if used |
| R6 composition/runtime defect separation | HANDOFF-VERIFIED | `CURRENT-STATUS.md` | Root-agent handoff, 2026-09-06 | Repair cannot reverse raw predicate |
| C1/C2 target-generation module-level failure and correction | HANDOFF-VERIFIED | `CURRENT-STATUS.md` | Root-agent handoff, 2026-09-06 | In progress; not a scientific result |
| Astra Ultra direction and CSE caution | HANDOFF-VERIFIED | `CURRENT-STATUS.md` | Fresh root-reported read-only adjudication, 2026-09-06 | Direct review file absent at initial check |
| Late direct R6 verification, if it arrives | CONDITIONAL | `evidence/R6-FIT-SCREEN-VERIFIED.json` | `evidence/R6-FIT-SCREEN-VERIFIED.json` | Added only if present before sealing |
| Late Astra process adjudication, if it arrives | CONDITIONAL | `reviews/ASTRA-ULTRA-PROCESS-ADJUDICATION.md` | `reviews/ASTRA-ULTRA-PROCESS-ADJUDICATION.md` | Added only if present before sealing |

## How to weigh conflicts

For copied project sources, use the current frozen contract and method freeze
before older design prose. For R6 outcome values and Astra direction, use the
late direct artifacts if present; otherwise preserve the handoff label and do
not silently upgrade it to a direct receipt. Distinguish execution readiness,
scientific validity, and human/controller acceptance.
