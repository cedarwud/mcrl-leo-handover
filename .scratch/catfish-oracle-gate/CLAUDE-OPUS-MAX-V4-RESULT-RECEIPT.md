# Native Claude Opus Max review receipt for frozen v4 result

Date: 2026-08-26

Status: completed through the user-specified native Claude CLI route. This is
the authoritative external-model review for v4 and supersedes the earlier
`agy`/Opus-4.6 review.

## Invocation

```text
claude -p "<bounded XML task>" --model opus --effort max --output-format json --dangerously-skip-permissions
```

The exact task text is preserved in
`CLAUDE-OPUS-MAX-V4-RESULT-PROMPT.md`. The corrected review brief SHA-256 was
`9766c80cf2cc15c11318953e30af36f5cdec74674ec379a0efe4dbb2dd373694`.

## JSON execution receipt

- `is_error`: `false`
- `terminal_reason`: `completed`
- `session_id`: `3735cb75-92da-4e67-b3b0-e63ea76bf842`
- requested model alias: `opus`
- canonical model: `claude-opus-5`
- requested effort: `max`
- output tokens: `14,418`
- thinking tokens: `11,732`
- duration API: `215,995 ms`
- cost: `$0.573916`
- web searches/fetches: `0/0`
- subagents spawned: `0`
- permission denials: `0`

## Adjudication

The following are Opus reviewer judgments, not new experimental measurements:

1. Maintain `FAIL_DROP_ARLP_R3_DIRECTION`. It found no visible leakage,
   proposal-timing, comparator-symmetry, difference-reward, or seed-clustering
   defect that could reverse the decision.
2. The corrected eligibility fact matters: all 917 evaluated ARLP and random
   alternatives differ from Q1. The earlier suggestion of comparator
   asymmetry was withdrawn.
3. It cautioned that the ARLP-versus-random PASS should not be described as
   proof of a useful C3 signal because ARLP also uses an SINR tie-break and has
   far fewer unsafe rows; the EE difference may therefore be dominated by
   feasibility/safety rather than C3 structure.
4. The narrow falsification is the previous-demand, myopic C3 proposal as a
   one-step override on the episode-8999 Q1 state distribution. It does not
   falsify every possible training-time R3 reward or every observation
   contract.
5. Primary recommendation: drop independent R3 and do not add `B_active` or C3
   to R1, because R1 already prices realised PA, circuit, baseband, and
   congestion effects. It proposed an R1 EE difference reward as a separate,
   untested future hypothesis requiring new preregistration and seeds.
6. Three-role status remains negative: R1 is direct EE; R2 is specified but
   unidentified without `T_HO/E_HO`; evaluated R3 is a negative result.

The frozen machine decision remains the authority. The proposed R1 difference
reward is reviewer advice only; it has not been designed, implemented, or
tested by this gate.
