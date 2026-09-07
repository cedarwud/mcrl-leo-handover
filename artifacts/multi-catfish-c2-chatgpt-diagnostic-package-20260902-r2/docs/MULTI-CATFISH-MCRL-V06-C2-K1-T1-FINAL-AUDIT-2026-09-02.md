# Multi-Catfish MCRL V0.6 C2-k1 T1 final pre-outcome audit

Date: 2026-09-02  
Disposition: `PASS_NO_BLOCKERS`

## Scope

The final audit was intentionally limited to four executable invariants:

1. all-user k1 actions are recomputed from persisted Q1+Q3 sums and masks,
   including `NO_OP=-1` for an empty mask;
2. the k0 candidate differs from Main only for the focal user and the 28 rows
   share one reference opening evidence digest;
3. formal shard, merge, and verify commands authenticate target-free
   `PREPARE_LIVE`, its file seal, and the current T1 preregistration before
   reading outcome-bearing inputs; and
4. the Ubuntu launcher atomically claims one attempt and requires successful
   upstream receipts.

## Independent reviews

- Fresh-context Sol audit: `PASS` after its one call-order blocker was fixed
  and covered by a regression test.
- Claude Opus Max audit: `PASS`, `blockers=[]`.
- Opus session: `317feccf-e6c2-46a2-981b-b6cedd2e92d5`.

## Frozen bytes audited

- T1 preregistration SHA-256:
  `e9fe8e83ba01f99076ce435b2499ae919cabbf55659433549a6a576e7a6c065f`
- runner SHA-256:
  `d1f67020632c7d165d90eb75aac92ea2a615d56cede279010d11cd10abb8cd68`
- live adapter SHA-256:
  `240bc17889e6f7641e25034a3f798848046df9f7d1ceb6bc0a52543364588b19`
- Ubuntu launcher SHA-256:
  `a26aba5d2bfe83d5842591efb1dbecb0f43ed78bc8e8917b8202bf5b5d5ffedf`
- unchanged V0.4 support scanner SHA-256:
  `b36a04762aa8538d5830e7b16584b6a3603ee87b75cd2461d1c74dded56d3bab`

Local conformance completed with one optional-dependency skip.  The Ubuntu
environment completed all 53 focused tests.  This is implementation and
pre-outcome audit evidence, not evidence that C2 improves EE.
