# Fresh-reader QA

Date: 2026-09-01  
Scope: package structure, claim boundary, and receipt integrity; no episode
was opened.

## Checkable results

- One entrypoint exists: `START-HERE.md`.
- `START-HERE.md` points to the claim authority, precedence map, V0.3 method
  and figure/presentation authorities, V0.4 C3 receipts, and the five-arm
  preregistration.
- The package states the three routes as C1=focal-now, C2=everyone-later,
  C3=non-focal-now; it states exactly three Q networks and one masked argmax.
- The package states the V0.4 C3 victim-burden change and selected rung-100
  candidate.
- `CLAIM-STATUS.md` says C3 is confirmed while C1, C2, and FULL-versus-Main
  remain pending; it explicitly says no five-arm outcome is present.
- `SUPERSESSION-MAP.md` separates the C3 update from unchanged V0.3
  invariants and preserves the training NO-GO boundary.
- No file path in `evidence/` names a five-arm result, and no five-arm result
  is copied.

## Commands used for final verification

From this directory:

```bash
sha256sum -c MANIFEST.sha256
python - <<'PY'
import json
from pathlib import Path

root = Path('.')
confirm = json.loads((root/'evidence/c3-confirmatory/result.json').read_text())
seal = json.loads((root/'evidence/c3-confirmatory/result-seal.json').read_text())
assert confirm['scientific_status'] == 'CONFIRM_C3'
assert confirm['test_split_opened'] is False
assert confirm['selected_q3_rung'] == 100
assert seal['test_split_opened'] is False
assert not list(root.rglob('*five*result*'))
print('fresh-reader/receipt checks: PASS')
PY
```

The checksum command is the final byte-integrity gate. A fresh agent should
not need the old V0.3 package, implementation source, or any training command
to understand the current method and claim boundary.
