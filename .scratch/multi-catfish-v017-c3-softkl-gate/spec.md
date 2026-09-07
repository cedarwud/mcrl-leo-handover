# V0.17 C3 Soft-KL gate execution criterion

The current debugging loop targets the observed V0.16 symptom: a learned C3
can fit pivotal reference pairs while corrupting more than half of decisions
that the exact ZR teacher leaves stable.

Completion is one immutable V0.17 server result for the frozen contract that:

1. uses fresh declared TRAIN/VALIDATION source worlds only;
2. passes the W170/W171/W172 local and server test closure;
3. persists all seven declared rungs for all three initializations;
4. is authenticated and independently re-adjudicated by
   `verify_v017_softkl_result.py`; and
5. ends in exactly `PASS_SOFTKL_GATE` or `FAIL_SOFTKL_GATE` without tuning or
   outcome-conditioned retry.

Only a PASS authorizes drafting a separate 100-episode five-arm contract.
