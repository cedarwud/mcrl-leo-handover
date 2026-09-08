# SOURCES — package path → original path → sha256 → size

Every file in this package with its provenance. `sha256` and `size` are of the **file as shipped**
(recomputed after staging). Original paths are relative to the repository root
`/home/u24/papers/mcrl-leo-handover`, except the `09-PRIOR-DESIGN-ADJUDICATIONS/` entries, which
come from the project's dated memory notes rather than from the repository tree.

Three files are marked `DERIVED`: they were written for this package rather than copied. Their
inputs are named in the third column. All other entries are byte-identical copies; where the
package filename differs from the source filename the row says so.

What was deliberately excluded: everything under `artifacts/` except
`V023-100E-MODEL-CONFIG.json` (named explicitly in the packaging brief, and shipped from its
`.scratch/` location, not from `artifacts/`); any file larger than 5 MB (none of the requested
files exceeded 141 KB); credentials of any kind (a scan for private keys, API keys, passwords and
bearer tokens over the staged tree returned nothing); and the user's email address (scanned for,
zero occurrences). Server and workstation filesystem paths such as `/home/sat/...` and
`/home/u24/...` do appear inside the documents — they are provenance references in sealed
receipts and adjudications, and were kept because removing them would break the audit trail.

| # | Package path | Original path | sha256 (as shipped) | Size (bytes) |
|---|---|---|---|---|
| 1 | `00-README.md` | `.scratch/multi-catfish-v023-controller-handoff-20260907/../multi-catfish-v023-c3-chatgpt-review-package-20260908/00-README.md` — (authored in the staging dir before this packaging run) | `e68b8c0359b12810a32c29bca72968ac72bc72fb9eb8260e6f903688b9411437` | 2265 |
| 2 | `01-CHRONOLOGY.md` | **DERIVED** — written for this package from MEMORY.md, the C3 memory notes, and docs/MULTI-CATFISH-MCRL-V0* | `8de70bd0571d86bb5d4c9abe0113231effe21a919933282467df6330f4036047` | 28690 |
| 3 | `02-R7-STOP-PHYSICS-RESULT.md` | **DERIVED** — .scratch/multi-catfish-v023-controller-handoff-20260907/R7-STOP-PHYSICS-RESULT-2026-09-07.md + .scratch/multi-catfish-v023-controller-handoff-20260907/ADJUDICATION-R7-STOP-PHYSICS-CODEX-GPT6-ASTRA-2026-09-07.md (appendix) | `5076a7c27b491ca258476eef4d22dc1ddac7845cd3c01e224a00469c471b9758` | 13514 |
| 4 | `03-F1-KILL-SCREEN-RESULT.md` | `.scratch/multi-catfish-v023-controller-handoff-20260907/F1-KILL-SCREEN-RUN-REPORT-2026-09-07.md` | `3d520709439cbfd667429814b1ac3aa1bee6cd5e76d13abe36d1e68dc4ec6985` | 15648 |
| 5 | `03b-F1-r2-receipt.json` | `.scratch/multi-catfish-v023-controller-handoff-20260907/f1-r2-receipts/receipt.json` | `d1cd30cec922c730cf95d832b0078f76ecd3f27c2ad7103d5297f843fa0eea2c` | 5611 |
| 6 | `03c-F1-ULTRA-ADJUDICATION.md` | `.scratch/multi-catfish-v023-controller-handoff-20260907/ADJUDICATION-F1-R2-RESULT-CODEX-GPT6-ASTRA-ULTRA-2026-09-07.md` | `004be44d8458bb7caf6a315316a3fb642cb0111bac3d90f1b755547730cfd5e7` | 4426 |
| 7 | `04-CONTINGENCY-LADDER.md` | `.scratch/multi-catfish-v023-c3-observability/V023-C3-RAPID-CONTINGENCY-LADDER-PREOUTCOME-2026-09-06.md` | `e75222c27cf10c8197f022344d726d0614109d534acaf73f20fa75175531161b` | 5447 |
| 8 | `05-R7-CONTRACT.md` | `docs/MULTI-CATFISH-MCRL-V023-LC-SRS-SUCCESSOR-GATE-CONTRACT-R7-BALANCED-2026-09-06.md` | `027e09a75a2e775b81b570cd49f6637dd10d55220d3ace2cf26a5b37ab002be5` | 6870 |
| 9 | `06-COMPOSITION-RULING.md` | `.scratch/multi-catfish-v023-controller-handoff-20260907/ADJUDICATION-F1-COMPOSITION-UNITS-CODEX-GPT6-ASTRA-2026-09-07.md` | `76e9b52e747bd922061b9a80467cb297f0a65b7883bb1b1015fc2ff768fa2879` | 4728 |
| 10 | `07-C1C2-SUCCESSOR-DECLARATION.md` | `.scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-SCIENTIFIC-DECLARATION-2026-09-07.md` | `f27d0500525aa6569c42299d81d3debdc48ef32d79a140d31854dc31f79bb8ea` | 10630 |
| 11 | `08-F3-DESIGN-R2.md` | `.scratch/multi-catfish-v023-controller-handoff-20260907/DESIGN-F3-LEARNER-SCREEN-PREOUTCOME-R2-CODEX-GPT6-ASTRA-2026-09-07.md` | `8747b1aa8e91917e2fbc59acb081e068d2a27012ccee4a794c5dc566f589c3c5` | 9121 |
| 12 | `09-PRIOR-DESIGN-ADJUDICATIONS/v014-gate-stop-adjudication-2026-09-03.md` | `(project memory) v014-gate-stop-adjudication-2026-09-03.md` | `58eb8ca02f65d58d18702d1acddf24febaef8ce5cd976771e00bce10c21dd782` | 2981 |
| 13 | `09-PRIOR-DESIGN-ADJUDICATIONS/v014-learner-path-review-2026-09-03.md` | `(project memory) v014-learner-path-review-2026-09-03.md` | `23d635330892939bf74e64287a2787c92521ae95b46ddbaabbc6b93768e14c13` | 1935 |
| 14 | `09-PRIOR-DESIGN-ADJUDICATIONS/v014-q3-probe-stop-design-adjudication-2026-09-03.md` | `(project memory) v014-q3-probe-stop-design-adjudication-2026-09-03.md` | `7969546edb0dbae887b73160d23ee97239e8a8388e30d8baa2d6658fdf1fa331` | 3971 |
| 15 | `09-PRIOR-DESIGN-ADJUDICATIONS/v014-route-audit-2026-09-03.md` | `(project memory) v014-route-audit-2026-09-03.md` | `767faf343dd5c154056a7460e16dd9b544b6030429f8ca9042536044a7736527` | 2409 |
| 16 | `09-PRIOR-DESIGN-ADJUDICATIONS/v015-learned-context-oracle-gate-review-2026-09-03.md` | `(project memory) v015-learned-context-oracle-gate-review-2026-09-03.md` | `3bbff07366cd5e4aae72a15de439f741d493ba9bbca12f5354fe50d686d93e11` | 1752 |
| 17 | `09-PRIOR-DESIGN-ADJUDICATIONS/v015r-fail-origin-adjudication-2026-09-03.md` | `(project memory) v015r-fail-origin-adjudication-2026-09-03.md` | `4a17379e4f36c2619a5009ad4cbd3639b9aa6b22af6f40746fbd0252a75e49e0` | 2318 |
| 18 | `09-PRIOR-DESIGN-ADJUDICATIONS/v015r-reference-gate-launch-audit-2026-09-03.md` | `(project memory) v015r-reference-gate-launch-audit-2026-09-03.md` | `c7d5cf8789d0a65a3c2cef6129009fc86ed4426d341c62547ac2060ba7c9ccfa` | 1683 |
| 19 | `09-PRIOR-DESIGN-ADJUDICATIONS/v020-repriced-c3-gate-adjudication-2026-09-05.md` | `(project memory) v020-repriced-c3-gate-adjudication-2026-09-05.md` | `fb01a7a1a76f3bf66338888eb76523eb8d9051e53deee85fdf7cde57d8d6dbc1` | 2489 |
| 20 | `10-PHYSICS-AND-CODE/F1-PREFLIGHT-MANIFEST.json` | `.scratch/multi-catfish-v023-c3-contingency-f1/F1-PREFLIGHT-MANIFEST.json` | `3711b9307b8cd12002df5bd9d4caacf9f96b5b5633dbf1fe4a4a062f421ff887` | 7556 |
| 21 | `10-PHYSICS-AND-CODE/F1-README.md` | `.scratch/multi-catfish-v023-c3-contingency-f1/README.md` — copy (renamed) | `66a084ef5c04603c67d0f6b73936cd29c89a410838a8e45e9e4b067f20b75439` | 4733 |
| 22 | `10-PHYSICS-AND-CODE/V023-100E-MODEL-CONFIG.json` | `.scratch/multi-catfish-v023-100e-screen-preoutcome-v2/V023-100E-MODEL-CONFIG.json` | `81e30b716ce996fb69e57ec9c1c3a4806f93598e6c009216287dd6a7dbde5df7` | 853 |
| 23 | `10-PHYSICS-AND-CODE/action_contract.py` | `src/mcrl/env/action_contract.py` | `ada0eba7aee6e47241248f927636593e8a45eb32f89e980a287787f42f3004a8` | 23139 |
| 24 | `10-PHYSICS-AND-CODE/c3_contingency_f0.py` | `.scratch/multi-catfish-v023-c3-contingency/c3_contingency_f0.py` | `9a8a97c02d2f0833cda6878a5327d5bd94662c95b662ee8b6c9aa138e0a806d2` | 40218 |
| 25 | `10-PHYSICS-AND-CODE/ee_axis_coalition_residual_c3.py` | `src/mcrl/runtime/ee_axis_coalition_residual_c3.py` | `daec8a2f82e644d1bede2a5f0787247e3abc01f8c667ac10ed9d4fef32d1ddde` | 35763 |
| 26 | `10-PHYSICS-AND-CODE/ee_axis_ops3.py` | `src/mcrl/runtime/ee_axis_ops3.py` | `68251ff750410ff74abfb412df83bafef459831874abfcfbee6e1e04d1adea02` | 35468 |
| 27 | `10-PHYSICS-AND-CODE/ee_axis_ops3_live.py` | `src/mcrl/runtime/ee_axis_ops3_live.py` | `6847069235ce3789c9f2f76bfd1de9f7a4e02402788eed0fabcc0ab57faed35a` | 37900 |
| 28 | `10-PHYSICS-AND-CODE/generate_v023_c1c2_targets.py` | `.scratch/multi-catfish-v023-c1c2-target-generation/generate_v023_c1c2_targets.py` | `ead7b056f30be3d26ce4405ccc11c8aaa21ab00e18580cadced98d47e8f0e001` | 60388 |
| 29 | `10-PHYSICS-AND-CODE/link_budget.py` | `src/mcrl/env/link_budget.py` | `8f5a48e068dd185f9ad043c8c5eac4ef76fd074af134890a432d92b96ba21890` | 33165 |
| 30 | `10-PHYSICS-AND-CODE/run_v023_c3_contingency_f1.py` | `.scratch/multi-catfish-v023-c3-contingency-f1/run_v023_c3_contingency_f1.py` | `e59a0db0a2465b9c2d79e5a24e1467460324fb151ae00b29c772cbafe832dc21` | 67862 |
| 31 | `10-PHYSICS-AND-CODE/step.py` | `src/mcrl/env/step.py` | `9548304bf5c9382004adc576f3c7540b22a130d95302d52534f409aa35f117b0` | 63789 |
| 32 | `10-PHYSICS-AND-CODE/v023_lcsrs_source_adapter.py` | `.scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py` | `26a3ebba03a26e8df95c1f39b78bfdc715a595f056198365fdc94daa3451167e` | 124632 |
| 33 | `11-HANDOFF-SECTIONS.md` | **DERIVED** — verbatim extracts (sections 0/2/13/17) from .scratch/multi-catfish-v023-controller-handoff-20260907/HANDOFF-EXECUTION-CLOSURE-AUDIT-2026-09-07.md | `36a095ba780c683c57f0941a18a2b2b059a3fdb544900bf119e858fc56023030` | 13491 |
| 34 | `PROMPT-CHATGPT-QA.md` | `.scratch/multi-catfish-v023-controller-handoff-20260907/../multi-catfish-v023-c3-chatgpt-review-package-20260908/PROMPT-CHATGPT-QA.md` — (authored in the staging dir before this packaging run) | `5a8c04061280d28bfb557ca01c3ece4350c0f198eb1867c1e1b5a6185f898a12` | 5599 |
| 35 | `PROMPT-CHATGPT-DEEP-RESEARCH.md` | `.scratch/multi-catfish-v023-controller-handoff-20260907/../multi-catfish-v023-c3-chatgpt-review-package-20260908/PROMPT-CHATGPT-DEEP-RESEARCH.md` — (authored in the staging dir before this packaging run) | `8501e702e3d3d0d67ed45227299e41d3a9026fc016d18b8f0184d8f9207014f2` | 4847 |

## Note on `09-PRIOR-DESIGN-ADJUDICATIONS/`

The packaging brief also asked for any adjudication memos under `.scratch/` that these memory
notes reference by `.md` path. A grep of all eight notes for `.md` paths returned **zero matches**
— the notes cross-reference each other by wiki-link (`[[name]]`) and cite artifact directories,
runner scripts and contract SHAs, but never a `.md` file path. Nothing was therefore added beyond
the eight memory notes themselves. The per-version lanes those notes describe do exist in the
repository (`.scratch/multi-catfish-v014-learner/`, `…-v015-c3-reference-gate/`,
`…-v016-c3-origin-gate/`, `…-v017-c3-softkl-gate/`, `…-v018-relational-zr/`,
`…-v019-relational-zr-normalized/`, `…-v020-c3-source-audit/`, `…-v021-expected-zr/`,
`…-v022-c3-coalition-residual/`) and can be supplied on request.

This file (`SOURCES.md`) is the 36th file in the package and is not listed in its own table.
