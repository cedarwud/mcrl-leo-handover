# Controller review of the E1 contract draft (2026-09-08 00:15 UTC) — UNSEALED

Draft: `V023-C3-EXISTENCE-TEST-CONTRACT-E1-2026-09-08.md` (astra, gpt-6-astra high, read-only; verbatim copy of
`…/controller-handoff-20260907/DRAFT-C3-EXISTENCE-TEST-CONTRACT-E1-CODEX-GPT6-ASTRA-2026-09-08.md`).
Status: contract body ACCEPTED as written, pending (i) the implementation landing (codex gpt-5.6-sol, this directory),
(ii) one implementation review (astra or agy) against §2/§4/§7, (iii) preflight binding of every `<<BIND_AT_FREEZE:…>>`.
No panel computation is authorised until the body is sealed (`.sha256` sidecar) and the preflight manifest is written.
Nothing in this file changes a formula, threshold, seed, horizon, λ, κ or acceptance rule of the draft.

## Interpretations the draft flagged as under-specified — controller decision: ACCEPT ALL
1. Catalog origin membership = BASE's realised served occupancy; unserved users are not origin members; singleton origins
   and empty destinations included; realised profiles retained without a favourable-success filter; lexicographic order;
   exact duplicate profiles recorded as aliases; empty catalog leaves BASE alone.
2. Arithmetic: per-profile binary64 B/E/C scalars from F1's accounting, serialised losslessly, then treated as exact
   rationals in the optimisation; "exact" refers to the frozen tape; no epsilon, no rounded-ratio comparison; ties
   lexicographic, BASE first.
3. Interruption / budget exhaustion = `INCOMPLETE` (no adjudication, not evidence of closure); cap 16 worker-hours
   (12.8 acquisition + 3.2 solver/verifier); resource-only amendments logged.
4. Pooling: one global ratio and one global service constraint over all 120 anchors; per-world/lineage breakdowns
   descriptive only; F2's direction-vote gates not inherited.
5. Certified procedure: Dinkelbach iterations whose inner problem is solved EXACTLY by dynamic programming over
   (anchor index, cumulative served count); the per-anchor choice set may be reduced by exact dominance INSIDE each
   Dinkelbach iteration, for the current q (for each anchor and each distinct served count keep the profile maximising
   B − qE; ties by the lexicographic rule) — never statically before the iterations, because B − qE depends on q
   (agy review 2026-09-08, item 2); done per iteration this is an exact reduction, not a relaxation; the certificate must include the census before and after reduction,
   the final q, the DP values/backpointers and an independent recomputation of the selected totals in exact rationals.
   Termination only at exact zero residual (Fraction arithmetic or integer scaling by a common power of two).

## Panel binding — worlds derived, collision scan clean
Rule (matches `…-c3-contingency-f3/f3_common.py`): `int.from_bytes(sha256(domain.encode('ascii')).digest()[:8],'big') & ((1<<63)-1)`.

| domain | world seed |
|---|---|
| `C3_EXISTENCE_E1/world/1` | 861587764845384088 |
| `C3_EXISTENCE_E1/world/2` | 3943897440191533562 |
| `C3_EXISTENCE_E1/world/3` | 5747196377242098234 |
| `C3_EXISTENCE_E1/world/4` | 4004348767321774260 |

Mutually distinct. Text scan of `.scratch/`, `artifacts/`, `docs/` for the four decimal strings: 0 hits
(`E1-WORLD-DERIVATION-2026-09-08.json`). The stage-C 9000-world plan (digest 866d28e0…) is a different derivation domain;
an additional check against its seed list is performed at preflight and recorded there.

## What E1 is not (restated so nobody upgrades it later)
Not an admission gate, not a scientific gate of the paper, not efficacy, not TEST. Its only downstream effect is the
authorisation table in §3 (which candidate family may declare a kill screen). Ch5's two-Catfish path does not depend on it.

## Independent consistency review
agy (Gemini, read-only, documents inlined): `AGY_E1_REVIEW=CONSISTENT` — closure ⇒ optimum = BASE is implied; admission cells match E1 §3; constants identical across the five documents; no residual ranking / tuning / regime selection found; memo's eligibility list and disclosure present in all four drafts. Record: `…/controller-handoff-20260907/REVIEW-E1-CONSISTENCY-AGY-2026-09-08.md`.
