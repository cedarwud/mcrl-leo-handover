# Package manifest

Package: `multi-catfish-v023-successor-gate-chatgpt-review-20260906-r1`  
Snapshot date: 2026-09-06  
Status: `REVIEW_INPUT__R6_RAW_GATE_FAILED__FRESH_GATE_REVIEW`  
Compute class: non-heavy, read-only review/package assembly  
Package-wide integrity file: `MANIFEST.sha256`

`MANIFEST.sha256` lists every regular file in this package except itself,
using a path relative to the package root. The manifest is generated only
after all package files and any late evidence copies are final. The package
digest reported to the parent is the SHA-256 of `MANIFEST.sha256` itself.

## Entry files

| Path | Role |
|---|---|
| `START-HERE.md` | Purpose, reading order, current headline, and stop boundary |
| `CURRENT-STATUS.md` | Handoff facts with explicit provenance labels |
| `EVIDENCE-MAP.md` | Claim-to-source and evidence-boundary index |
| `SOURCE-PATH-MAP.md` | Original-to-package path translation |
| `CLAIM-CEILING.md` | Permitted and forbidden scientific/process upgrades |
| `CHATGPT-QA-PROMPT.md` | Model-ready package-grounded adjudication prompt |
| `CHATGPT-DEEP-RESEARCH-PROMPT.md` | Model-ready primary-literature adjudication prompt |
| `PACKAGE-MANIFEST.md` | Package inventory and manifest rule |
| `MANIFEST.sha256` | SHA-256 list for all other package regular files |

## Directory roles

| Directory | Contents | Evidence level |
|---|---|---|
| `authority/` | Method freeze, gate contract, R6 decision, contingency ladder, Fable C3 audits | Mixed frozen design and read-only review; no new authority |
| `fast-screen/` | Frozen fit-screen calculator | Development/read-only metric implementation |
| `five-arm/` | Five-arm binding, receipt, runner, README, spec, and seam tests | Admission/receipt plumbing; no real physical run |

## Integrity and use

The copied files are regular files, not symlinks. Originals remain untouched.
The two prompts must be run independently in fresh contexts. A reviewer may
read package files and, for the Deep Research prompt, retrieve primary
literature, but may not perform project actions or alter the package.
