# Package manifest

**Package:** `multi-catfish-v04-web-agent-package-20260901-c1-c3-r1`  
**Created:** 2026-09-01  
**Scope:** current C1/C3 method writing and exact frozen-policy traceability.
The package does not finalize the three-Catfish method.

`MANIFEST.sha256` is generated from the actual bytes of every package file
except itself. Verify it from this directory with:

```bash
sha256sum -c MANIFEST.sha256
```

## Package-controlled files

- `START-HERE.md`: sole entrypoint.
- `AGENTS.md`: read-only handling rules.
- `CLAIM-STATUS.md`: confirmed, pending, and prohibited claim boundary.
- `SUPERSESSION-MAP.md`: current C1/C3 precedence map.
- `FRESH-READER-QA.md`: executed reader and integrity checks.
- `PACKAGE-MANIFEST.md`: this inventory.

## Documentation snapshots and current method authorities

The following are the selected package documents:

```text
docs/MULTI-CATFISH-MCRL-C1-C3-PAPER-AUTHORING-DELTA-2026-09-01.md
docs/CURRENT-MULTI-CATFISH-AUTHORITY.md
docs/ACTIVE-SYMBOL-TABLE-2026-08-31.md
docs/C1-CURRENT-METHOD-AUTHORITY.md
docs/C3-CURRENT-METHOD-AUTHORITY.md
docs/C1-RIS-EXP-ACRM-LINEAGE.md
docs/C1-C3-RESULT-AUTHORITY.md
docs/MULTI-CATFISH-MCRL-V04-C3-VICTIM-BURDEN-DECISION-2026-09-01.md
docs/MULTI-CATFISH-MCRL-V04-C3-CONFIRMATORY-RESULT-2026-09-01.md
docs/MULTI-CATFISH-MCRL-V04-FIVE-ARM-ABLATION-RESULT-2026-09-01.md
docs/MULTI-CATFISH-MCRL-V04-ROUTE-INTERACTION-DIAGNOSTIC-2026-09-01.md
```

The root current-authority and current V0.4 documents are byte-preserved
snapshots. The active symbol table is byte-preserved from the existing RC
package because no live root copy was present in this checkout. The three
package-local method/result notes are deliberately narrow condensations; they
do not copy C2 implementation or historical C1 efficacy files.

## Evidence receipts

`evidence/frozen-policy-five-arm/` contains only the selected current
five-arm receipt files needed to trace the C1 and five-arm C3 comparisons:

```text
evidence/frozen-policy-five-arm/prepare.json
evidence/frozen-policy-five-arm/prepare-seal.json
evidence/frozen-policy-five-arm/result.json
evidence/frozen-policy-five-arm/result-seal.json
evidence/frozen-policy-five-arm/evaluator-code-manifest.json
```

`evidence/c3-confirmatory/` contains the selected current confirmatory receipt
files:

```text
evidence/c3-confirmatory/prepare.json
evidence/c3-confirmatory/prepare-seal.json
evidence/c3-confirmatory/result.json
evidence/c3-confirmatory/result-seal.json
evidence/c3-confirmatory/evaluator-code-manifest.json
```

The five-arm result SHA-256 is
`9142da31690927fe853765b9dfc0c807d4202738784961b44be393a77c608224`.
The separate C3 confirmatory result SHA-256 is
`bb1a46a8a782a5fb6d3c37391c17866ac0dbbb9bcc7c42bd2c9d8a9f0dd396dd`.
The exact seal and supporting-file hashes are in `MANIFEST.sha256`.

No old C1 developmental efficacy file, C2 implementation file, standalone C2
result, checkpoint, training log, or TEST data is included. The route-
interaction work-order text is retained as a boundary reference; its result
artifact is omitted because it is diagnostic-only and includes single-route
C2 outputs not needed for C1/C3 traceability.

## Claim boundary

The package contains frozen-policy evidence for C1 and C3 only. It contains no
Chapter 5 narrative and authorizes no long training. C2 remains mandatory and
unresolved, and the scientific status remains
`MULTI_CATFISH_NOT_ALL_CONFIRMED`.

