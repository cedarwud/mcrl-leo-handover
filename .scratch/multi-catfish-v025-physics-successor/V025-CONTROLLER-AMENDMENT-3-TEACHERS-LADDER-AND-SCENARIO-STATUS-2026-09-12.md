# Amendment 3 to Ruling 2 — scenario status after parity; the teacher (catfish) ladder; soft-advantage targets; teacher cost; B2 is a contract change

Date: 2026-09-12 ~01:10 Asia/Taipei (17:10 UTC 2026-09-11). Amends
`V025-CONTROLLER-RULING-CEILING-PARITY-B-CHAIN-AND-CATFISH-COUNT-2026-09-11.md` and its Amendments 1–2. Written after the
ceiling agent recorded parity PASS and the base / variant results, and after the LP probe report; **before** any oracle cell
(A-real / B-real) has been read. Sources and verification: `.scratch/reviews/external-gpt/DR19-GPT6-CONTROLLER-CHECK-2026-09-12.md`.

## 1. Scenario status (reading the declared rules; no threshold changed)

| item | value (pinned, sat, 24 evaluation episodes unless stated; `A m=2dB` = 107.00 M bit/J on that set) | reading |
|---|---|---|
| parity | counterfactual == committed, max Δ = 0, 580 steps, every variant | **PASS** (ruling §1 satisfied; search numbers citable as lower bounds) |
| constrained search | +41.4 % pooled (paired +41.9 ± 1.5 %, 24/24); p10 rate 50.2 % of the rule's; 240/240 steps at budget | **A excluded**; the +41 % has a thin rate tail |
| rate-floored search | +23.9 % (6 ep), bits −1.9 % | defensible joint lower bound |
| nominal-information search | +11.0 % (6 ep), bits −51.7 % | throughput-degenerate: fails B's bits condition |
| LP-prev(1,0) (simultaneous, observation-only rule) | eval +6.66 % (paired +6.85 ± 0.65 %, 24/24), served 0.9985, bits 0.954; cal +4.75 % (24/24), bits 0.952 | **B's nominal condition met by a deployable witness** on both sets |
| coordination depth | 74 % of the search's gain after sweep 1, 93 % after sweep 2; compound move +0.27 % | shallow coordination; information (realised vs nominal) is the larger gap |
| A-real / B-real | running | decide B1 vs B2 vs C (Amendment 1 rules 1–4) |

Standard wording: "a budget-limited local central search finds at least +41 % one-step pooled-EE headroom above the best
simple rule (+24 % with a per-user rate floor); a simultaneous per-user observation-only rule with a beam-lighting price
reaches +5–7 %. These are lower bounds, not ceilings."

## 2. The teacher ladder (the catfish, redefined; count still measured per ruling §4)

Candidate teachers, ordered by privilege; each admitted only through the oracle-first screen (Amendment 1), the
representability screen (Amendment 2 §3, metric in §3 below) and the three count criteria (ruling §4):

| teacher | privilege | status | cost as an on-student-state teacher (7.5 ms per counterfactual evaluation) |
|---|---|---|---|
| **T0 — LP lighting-price rule** (LP-prev(1,0)) | none (exact function of the student's observation) | passed the oracle-first screen (+6.66 % / +4.75 %) | free |
| **T_DR — unilateral exact difference-reward best response** (A-real) | others' current actions + realised counterfactuals | running | ~2,700 evaluations per step ≈ 20 s per step → subsample |
| **T_SEQ — sequential sweep** (B-real) | earlier users' same-step choices + realised counterfactuals | running | similar to T_DR |
| **T_JOINT — rate-floored central search** | joint decision, realised counterfactuals, 3 sweeps | lower bound +24 % (6 ep) | ~20 min per episode → offline labels only, not on-student-state queries |

The old three rule sources are not on the ladder: under ruling §4 `A m=12dB` fails distinctness against `A m=2dB`,
`B1_NO_NEW_BEAM` is dominated, and `A m=2dB` is the reference.

## 3. Representability metric and targets (refines Amendment 2 §3)

- **Metric**: `R_repr = (EE(clone) − EE(rule)) / (EE(teacher) − EE(rule))` in closed loop on the evaluation set, with
  the clone trained on the student's own observation (the learner's architecture). Report beside it the teacher's
  conditional action entropy given the student observation and top-1/top-k accuracy. Action accuracy alone is not the
  criterion (a 70 % classifier can keep the gain if its errors are on low-stakes decisions).
- **Two clones per teacher**: one-hot behaviour cloning, and **soft-advantage distillation** (regress the teacher's 28-action
  advantage vector per user; under aliasing it targets the conditional expected utility given the student's information).
  T_DR / T_SEQ produce these vectors as a by-product of their best responses; they are saved from now on.
- Admission (unchanged number): `R_repr ≥ 0.5` for at least one of the two clones.

## 4. When training is authorised: the causal ladder (proposal adopted from `dr19.md`; order fixed now)

All arms: difference-reward (or validated lighting-price) credit, pinned archive, the CF3 evaluation, 3 seeds × 1000
episodes unless the owner sets otherwise, matched random-teacher controls where a teacher is present.
- **D0** — difference-reward RL, no teacher (the new no-demonstration control).
- **D1** — + teacher transitions as static replay (the pilot's mechanism; its random control = the pilot's A3 analogue).
- **D2** — + teacher labels on student-visited states (DAgger-style; soft advantage distillation where available).
- **D3** — + unconditional DQfD large-margin loss toward the teacher (required comparator).
- **D4** — + gated margin (active only where the teacher label is representable and has positive counterfactual advantage;
  Q-filter / ADVISOR logic).
- Multiple teachers only after the best D arm beats D0 on the declared rule: T0, T0+T_DR, T0+T_DR+T_SEQ (…), plus drop-one.
- Training question for every arm: does the learner reach its own oracle, read as
  `ρ = (EE(learner) − EE(rule)) / (EE(teacher) − EE(rule))` **relative to the teacher's `R_repr`**. **Proposal for the
  owner** (the 50 % is the owner's number, still unconfirmed): pass iff `ρ ≥ 0.5 × R_repr` (the learner reaches half of what
  is representable); report `ρ` and `ρ / R_repr` for every arm. A learner cannot be asked to exceed the representable
  ceiling.
- Naming: "catfish" stays as the method label ("privileged catfish teachers"); the theory is grounded in LUPI / CTDE /
  RL-from-demonstrations / counterfactual credit; the competitive element's lineage is CER / CuSP / Sukhbaatar (erratum 26);
  faithful RIS catfish (grey literature) is the lineage comparator, never the theoretical basis.

## 5. B2 is a deployment-contract change (correction to Ruling 2 §3)

B2 gives the student same-step information about earlier users' choices at execution. That is a change to the execution
contract (lighter than a coordinator, heavier than a credit change) and a referee will ask for it to be declared.
**Entering B2 is an owner decision**, like C. B1 (credit only) keeps the contract.

## 6. Still not authorised

No learner training until A-real / B-real are read against Amendment 1 §3 (ruling §5 stands). Allowed meanwhile: oracle
cells, the representability screen on T0 (it needs no oracle), action-dump re-runs for T_JOINT labels, B1 code and tests,
curation, writing.
