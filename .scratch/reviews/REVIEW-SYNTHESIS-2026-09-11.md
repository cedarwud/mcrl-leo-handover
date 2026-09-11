# Cross-model review synthesis — the three-sides narrative

Date: 2026-09-11 ~01:05Z · Controller
Six reviews, three model families x {blind derivation, adversarial}, one shared evidence bundle
containing only measurement reports, sealed declarations and code — no controller writing.

| family | BLIND (derive the claim from evidence, narrative unseen) | ADVERSARY (attack the narrative) |
|---|---|---|
| Claude | **no three-route claim**; one-route method (C1) with unresolved C2 and negative C3; "the three routes are one misaligned scalar objective viewed three ways" | **reject** — decomposition defined after its optima were measured; necessity vs BASE passed by RANDOM |
| GPT (astra) | **no demonstrated three-route EE benefit or superiority to MODQN**; method proposal with diagnostic and bounded negative findings | **reject** — non-learned configuration trade-offs substituted for learned route complementarity; C3 lowers EE |
| Gemini | **no empirical claim** that the method or its routes improve EE; defensible contribution is representational, diagnostic, methodological | **reject** — post-hoc circular outcome-fitting; static constructions misrepresented as learned routes on a Pareto frontier |

## The red-flag test, as pre-declared

The design was: if the blind derivations independently land near the proposed narrative, it is not
merely a product of the conversation; if they land elsewhere, that is a red flag. **All three blind
derivations landed elsewhere, and none reconstructed the bits / energy / time decomposition.** The
owner's suspicion that the narrative was shaped by the conversation is supported.

## Points on which the reviews converge

1. **By the stage contract's own definitions, C1 + C3 = F(a_A) - F(a0) identically, and C2 is the
   same F continued three steps.** The routes are one scalar objective viewed three ways, not three
   objectives; a "trade-off between objectives" framing is excluded by construction. That objective
   F cannot order configurations by EE at any eta (ETAFIX).
2. **Relabelling routes contradicts their sealed definitions.** v1.1 item 4 defines C1 as a
   whole-network difference surplus whose benefit is expected "through energy and service, not
   surplus bits"; calling C3 an "energy side" route sidesteps its sealed joint-headroom condition,
   which fails. The sealed declarations forbid changing a target after outcomes are opened.
3. **The decomposition was defined after its optima were measured** (RSS_MAX 41.62 and crowded
   46.11 were on record 6-8 h before the definitions file).
4. **The necessity test against BASE is non-discriminating**: RANDOM (11.23, 1,102 served) beats
   BASE (11.03, 960 served); so does an unconverged head trained on zero targets.
5. **Both "sides" are energy levers**: 71% of RSS_MAX's log-EE gain over BASE comes from joules,
   103% for the crowded point (whose bits fall). The time side has no route into EE in the primary
   cell.
6. **The Pareto pair is two non-learned configurations, each the optimum of one objective alone** —
   the opposite of "points no single route reaches".
7. **The trained evidence shows substitution and dominance, not trade-off**: DROP_C3 beats FULL on
   EE, served and attainment (Q1 v1, 16/16); C2's marginal flips sign with C1's features on identical
   exact labels; single-route marginals sum to near zero while joint effects are large.
8. **The sealed success criterion is conditional contribution** — FULL vs DROP_X with the other routes
   informative, lower bound above +0.5% — **not "each route alone"**. The owner's "each alone must
   raise EE" is a new criterion.
9. **v1.9 item 5 already makes physics-selector C2 a tie-break** and declares a zero oracle C2
   selection marginal admissible, with C2 certified by forecast validity instead. The
   "contradiction" I put to the owner (`e89880a2`) is resolved by the latest amendment governing.

## What survives, by consensus

- **A diagnostic paper, supported now, learner-free**: EE here is dominated by joules; the baseline's
  load-balance objective (r3) works against EE in this physics; a fixed linear price (the deployed
  objective) mis-ranks configurations; coordination has no necessity at the sealed point (clean
  ceiling +0.84%); an EE-vs-attainment frontier exists among non-learned rules.
- **A method hypothesis, not a result**: physical levers generate candidates, a deployable
  ratio-consistent score selects among them, persistence and attainment as declared constraints,
  tested out-of-sample against a retrained MODQN with and without r3.
- **C1 as a one-route result, pending**: its value beyond a gain heuristic is unmeasured — 83/93 of
  exact C1's selections are the catalogue's gain-ranked `s0` proposals. `C1VSGAIN` (dispatched 01:00Z)
  measures it.

## Errors in my own design-state document, found by the Claude blind reviewer

`DESIGN-STATE-2026-09-10.md` states (a) the EE numerator is demand-capped — **false**, declaration
v1.8 item 5 and every report use full-buffer; (b) per-beam power is the max over served users —
**false** for the a-r0 path, which is TDM (CROWDCOST). Corrected there.
