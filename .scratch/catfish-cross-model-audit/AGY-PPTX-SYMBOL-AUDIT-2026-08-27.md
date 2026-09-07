# agy PPTX symbol/formula audit receipt

- Date: 2026-08-27
- Mode: read-only structural/OMML audit
- Symbol authority:
  `/home/u24/papers/modqn-paper-reproduction/docs/research/ee-definition-cleanup/2026-08-17-simplified-ee-symbol-table.md`
- No PPTX was edited.

## Inventory

| Deck | Slides | Native OfficeMath | Formula pictures |
|---|---:|---:|---:|
| `chapter4-0826.pptx` | 27 | 102 | 0 |
| `chapter5-0826.pptx` | 14 | 29 | 0 |

## Verdict

- Chapter 4: 9 slides with mismatches — 8, 9, 17, 18, 20, 21, 23, 25, 27.
- Chapter 5: 3 slides with mismatches — 6, 7, 8.
- Two Chapter-4 findings change scientific meaning and must be repaired before
  the decks are treated as formula authority.

## Critical scientific mismatches

1. **Chapter 4 slide 17 — P3 is wrong.** It shows the retired max--min beam
   throughput gap. The active objective is
   `min sum_t sum_{s in S} sum_{v in V} U_{s,v}(t)^2`.
2. **Chapter 4 slide 20 — r3 is wrong.** It shows the retired normalized
   max--min rate-gap/fairness reward. The active reward is
   `r_{3,u}(t)=-U_{b_u(t)}(t)`, expressed with the physical serving beam and
   active load notation.

## Remaining mismatches

- Chapter 4 slides 8 and 9 use elevation `alpha_{u,s,v}`; authority uses
  `alpha_{u,s}`. Slide 9 also renders direction vectors as scalars rather than
  bold vectors.
- Chapter 4 slides 17 and 20 and Chapter 5 slide 8 use retired product-set
  notation `mathcal K` / `kappa`; use explicit sums over `mathcal S` and
  `mathcal V`.
- Chapter 4 slides 18 and 21 and Chapter 5 slides 6, 7, and 8 bind aggregated
  beam/system quantities to one link angle `theta_{u,s,v}`. `p_{s,v}`,
  `P^p_{s,v}`, `xi_{s,v}`, `P^N`, `r_{1,u}`, and the reward vector require the
  full system angle state `boldsymbol theta` where specified by the authority.
- Chapter 4 slide 21 uses an incomplete reward-vector accent/argument scope.
- Chapter 4 slide 23 retains Sun-baseline `s_t^u`, global `A`, and `zeta`
  rather than the current thesis state, feasible set, and value notation.
- Chapter 4 slide 25 has a TD dummy-action scoping typo: the maximized action
  and the action passed into `Q_j` are not the same bound variable.
- Chapter 4 slide 27 still says beam-throughput fairness rather than load
  balancing.

## Clean checks

- Both decks consistently use `theta_{3dB}` as the beam-angle symbol.
- No formula images were found; corrections can remain native OfficeMath.
- Retired execution-mask, RF-slot, target/estimated-SINR, congestion-context,
  and satellite-cap symbols were absent from the audited formulas.

## Claim boundary

This audit establishes deck-versus-authority differences only. It does not
authorize edits, validate the proposed Multi-Catfish method, or provide
PowerPoint desktop visual acceptance.
