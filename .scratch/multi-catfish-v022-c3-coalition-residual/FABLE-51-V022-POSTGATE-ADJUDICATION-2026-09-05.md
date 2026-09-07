# Fable 5.1 V0.22 post-gate adjudication

Date: 2026-09-05  
Status: **NON-AUTHORITY READ-ONLY REVIEW / NO NEW OUTCOME OR TRAINING**  
Session: `cf9414e1-2174-43ce-b80d-9973957099d2`

## Review boundary

The reviewer inspected the frozen V0.22 mechanics contract, formula source,
immutable result, Deep Research report, and relevant current source.  It made
no file edit, simulator call, learner update, episode-training run, web request,
or TEST access.

## Verdict

`GO_OBSERVABILITY_CONTRACT`

The reviewer independently accepted the stored
`GO_LC_SRS_OBSERVABILITY_GATE` under its narrow contract.  It classified the
two-player formula as an exact Shapley allocation of the explicitly named
current-slot C1-residual game.  It did not accept any claim of decentralized
exactness, partial-adoption exactness, learned-Q decomposition, population
benefit, or trajectory-level efficacy.

## Reproduced facts

- Selected anchor: TRAIN world `2026121701`, step `1`.
- Named source key: `(62836, 27)`; members: users `27` and `79`.
- The source beam remains active in `00`, `10`, and `01`, disappears in `11`,
  and no destination beam is newly opened.
- All four profiles serve all 100 users.
- `EE(00) = 118.0067176 Mbit/J`.
- `EE(11) = 118.1404140 Mbit/J`, or `+0.1132956%` relative to `00`.
- Joint bits change by `-3.1390865%`; joint energy changes by `-3.2487015%`.
- The identity residual is approximately `9.5e-7 bit`.
- Literal native `masked_argmax(Q1+Q2+Q3)` selects the complete `11` profile.

## Important inference and risk

For the two members, the independently recomputed current-slot terms in Gbit
equivalent are:

| User | `l_i` | `e_i` | `Psi/2` | `z3_i` | `l_i + z3_i` | `z3_i/kappa` | learned `Q1+Q2` proposal margin |
|---|---:|---:|---:|---:|---:|---:|---:|
| 27 | -8.29 | +6.68 | +1.12 | +7.81 | -0.48 | 0.773 | -0.154 |
| 79 | -7.81 | +8.15 | +1.12 | +9.27 | +1.47 | 0.918 | -0.487 |

The full composition pass is therefore structurally fragile: user 27 has a
negative exact immediate `C1-owned + C3` value, while the learned Q1+Q2 margin
is much less negative.  The result does not preserve separate Q1 and Q2
surfaces, so it cannot determine whether the complete pair relies on Q1
underpricing, a legitimate positive future Q2 term, or both.  Partial profile
`10` is harmful (`-0.200%` EE versus `00`), while `01` is only `+0.042%`.

This is a learner/interface risk, not an algebraic failure.  It must be tested
before episode training.

The reviewer also noted that `Psi/2` is only about 12--14% of each stored C3
target in this case.  Much of `z3_i` is a large unilateral non-focal bandwidth
effect later cancelled by the joint interaction term.  A student may therefore
need to learn relatively large terms whose policy value depends on joint
composition.

## Authorized next question

The next contract should ask whether deployable predecision information can:

1. identify a last-pair source-beam closure opportunity and a feasible partner;
2. predict the LC-SRS member credit better than matched action-identity
   placebos on held-out TRAIN worlds;
3. reproduce complete-pair adoption often enough under the unchanged literal
   final `Q1+Q2+Q3` masked argmax;
4. separate C1 calibration from Q2 future support on the same member actions;
5. stop rather than continue when the physical signature, observability, or
   composition mechanism does not generalize.

The reviewer proposed an eight-world leave-one-world-out development panel and
classified it as heavy CPU work (approximately 3--5 hours total).  That budget
is a proposal for the next pre-outcome contract, not a result or current
authorization.  It should run on the Ubuntu server if adopted.

## Paper boundary

The C3 formula may now be treated as a **stable Chapter 4 candidate** described
as a training-only local coalition-Shapley spatial residual.  The paper must
remove the old ZR compatibility-gate story and must not claim that the formula
guarantees complete decentralized adoption.  A future interface failure would
reopen coalition construction/state, not automatically invalidate the scoped
two-player identity.
