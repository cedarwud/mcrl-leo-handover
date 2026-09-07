# Fresh-reader QA

Date: 2026-09-01  
Scope: package structure, notation, C1/C3 claims, receipt integrity, and
pending boundaries. No episode was opened and no training was run.

## Required reader answers

| Question | Fresh-reader answer | Check |
|---|---|---|
| What is C1? | C1/Q1 is the focal opening net-surplus route. It retains RIS EXP/ACRM lineage; its current five-arm `FULL` vs `DROP-C1` result is +254.596%, 3/3 initializations and 30/30 worlds. | PASS |
| What is C3? | C3/Q3 is the V0.4 non-focal opening rate-externality route. It uses lagged action-aligned victim-rate burdens for the candidate beam and satellite. | PASS |
| Why is there no energy term in C3? | Opening shared energy is charged to the sole focal intervention in C1. Repeating it in C3 would double count the same opening energy; C3 remains rate-only while the world can still change energy indirectly. | PASS |
| What is deployed? | Exactly three independent Q networks are summed, one common legal/service-safe mask is applied, one argmax is taken, and one Main action executes. | PASS |
| What is still pending? | C2 is mandatory and unresolved; the whole method is not all confirmed; Chapter 5, long training, and TEST/result authoring remain pending and untouched. | PASS |
| What claims are forbidden? | Do not merge the +21.970% five-arm C3 result with the separate +21.216% confirmatory result; do not use the superseded V0.3 C3 observation/source; do not claim whole-method finalization, C2 confirmation, long training, Chapter 5 completion, or an extra controller/override. | PASS |

## Structural checks

- One entrypoint exists: `START-HERE.md`.
- Required package files exist, including `MANIFEST.sha256`.
- `docs/` contains the new delta, current authority snapshot, active symbol
  snapshot, C1/C3 method/result authorities, V0.4 C3 authorities, and the
  route-interaction work-order boundary.
- `evidence/` contains only the selected five-arm and C3 confirmatory receipt
  files. There is no `implementation/` directory, no checkpoint, no historical
  C1 developmental efficacy file, and no standalone C2 result directory.
- The combined five-arm receipt is labelled frozen-policy traceability and is
  not treated as a completed Chapter 5 narrative.

## Executed verification commands

From this directory:

```bash
sha256sum -c MANIFEST.sha256
```

The final run reported every listed file as `OK` (27/27). A small read-only
JSON probe also checked the exact statuses, no TEST split, the separate C3
values, and the absence of forbidden package paths. The stale-claim scan
checked that no copied historical C1 efficacy artifact, superseded C3
observation/source claim, whole-method completion claim, C2 completion claim,
or Chapter 5 completion claim is present as a current positive assertion.

## Result

**PASS.**
