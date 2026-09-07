# Package manifest

**Package:** `multi-catfish-v04-web-agent-package-20260901-rc`  
**Created:** 2026-09-01  
**Scope:** Web-agent method/figure/paper understanding and current C3 claim
status. Existing V0.3 packages are not modified. No implementation source,
training output, or five-arm outcome is included.

`MANIFEST.sha256` is the byte-level checksum manifest for every file in this
package except itself. Verify it from this directory with:

```bash
sha256sum -c MANIFEST.sha256
```

## Package-controlled files

- `START-HERE.md`: sole entrypoint and fresh-reader completion criterion.
- `CLAIM-STATUS.md`: current confirmed/pending/prohibited claims.
- `SUPERSESSION-MAP.md`: package precedence map for V0.3/V0.4 conflicts.
- `AGENTS.md`: read-only package handling rules.
- `FRESH-READER-QA.md`: performed structural and receipt checks.

## Authority snapshots

`docs/` contains byte-preserved copies of the current authority snapshot, the
V0.3 EE-axis rationale, algorithm, paper-authoring, figure-handoff,
presentation-layer, and active-symbol documents, plus the V0.4 C3
victim-burden decision, screen result, confirmatory preregistration/result,
and five-arm preregistration. Their original live paths are the same names
under `docs/`, except the active symbol table is the existing active-symbol
snapshot from the prior V0.3 Web-agent package because no live root copy was
present at packaging time. The copied file hash is still verified here; do not
silently create a second symbol table.

Included documentation snapshots:

```text
docs/ACTIVE-SYMBOL-TABLE-2026-08-31.md
docs/CURRENT-MULTI-CATFISH-AUTHORITY.md
docs/MULTI-CATFISH-EE-AXIS-OPUS-MAX-CODESIGN-V0.3-2026-08-31.md
docs/MULTI-CATFISH-EE-AXIS-REDESIGN-CONTRACT-V0.3-2026-08-31.md
docs/MULTI-CATFISH-MCRL-V03-ALGORITHM-SPEC-2026-08-31.md
docs/MULTI-CATFISH-MCRL-V03-FIGURE-DECK-HANDOFF-2026-08-31.md
docs/MULTI-CATFISH-MCRL-V03-PAPER-AUTHORING-CONTRACT-2026-08-31.md
docs/MULTI-CATFISH-MCRL-V03-PRESENTATION-LAYER-2026-08-31.md
docs/MULTI-CATFISH-MCRL-V04-C3-CONFIRMATORY-PREREG-2026-09-01.md
docs/MULTI-CATFISH-MCRL-V04-C3-CONFIRMATORY-RESULT-2026-09-01.md
docs/MULTI-CATFISH-MCRL-V04-C3-SCREEN-RESULT-2026-09-01.md
docs/MULTI-CATFISH-MCRL-V04-C3-VICTIM-BURDEN-DECISION-2026-09-01.md
docs/MULTI-CATFISH-MCRL-V04-FIVE-ARM-ABLATION-PREREG-2026-09-01.md
```

## Evidence receipts

- `evidence/c3-screen/`: bounded screen `result.json`, `result-seal.json`,
  and `primary-evaluation.json`, copied byte-for-byte from
  `artifacts/multi-catfish-v04-c3-500-update-screen-20260901-r1/`.
- `evidence/c3-confirmatory/`: confirmatory `result.json`, `result-seal.json`,
  `prepare.json`, `prepare-seal.json`, and evaluator-code manifest. These are
  copied byte-for-byte from
  `artifacts/multi-catfish-v04-c3-confirmatory-20260901-r1/`. They are receipt
  context only; they do not authorize editing or rerunning the frozen
  evaluator.

The primary copied receipt hashes are: screen result
`ab232f72e562e5a9aa4b68ec8074c5556691ffb1272ae92ec5efd651e76a2177`,
confirmatory result
`bb1a46a8a782a5fb6d3c37391c17866ac0dbbb9bcc7c42bd2c9d8a9f0dd396dd`, and
confirmatory result seal
`d569049cf648d5d261306ad27d850755070b851a8aecf723f0ebd60d085ee54b`.

The copied confirmatory result is the source for the `CONFIRM_C3` claim. The
five-arm preregistration is included, but its result is intentionally absent.

## Exclusions

No `.pt` checkpoint, simulator source, replay, training log, TEST data, or
five-arm result is part of this Web-agent package. Existing packages under
`artifacts/multi-catfish-v03-web-agent-package-*` are untouched.
