# V0.18 proposed TRAIN seed census

Status: LOCAL PRE-FREEZE CENSUS, NOT SUFFICIENT TO AUTHORIZE A RUN.

Date: 2026-09-04 (Asia/Taipei)

Proposed worlds: `2026120401`, `2026120402`, `2026120403`, `2026120404`.

The current local checkout was searched with:

```text
rg -n "202612040[1-4]" . --glob '!artifacts/**/source.npz' --glob '!*.pt'
```

Result: no occurrence (`rg` exit status 1). The server checkout must repeat the
same census before the draft contract is frozen. This local negative result does
not prove that the server has not opened one of these worlds.
