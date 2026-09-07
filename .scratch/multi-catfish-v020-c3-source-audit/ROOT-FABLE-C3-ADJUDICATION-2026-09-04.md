# Root adjudication of the Fable C3 source audit

Date: 2026-09-04

Scope: read-only scientific adjudication. No simulator, learner, episode run, or
TEST split was opened. This note does not amend shared authority.

## Inputs and integrity

- Fable report:
  `artifacts/multi-catfish-c3-fable-cleanroom-20260904-r1/FABLE-C3-SOURCE-AUDIT.md`
- Verified SHA-256:
  `1fa03f7f62fe7277c6e31b762b09c9bf2e6a2723ba5a2b0d19c2cf4c603737be`
- Independent numeric recheck:
  `.scratch/multi-catfish-v020-c3-source-audit/fable-core-claim-recheck.json`
- Independent fresh-context mathematical verdict:
  `REPRICE_ALL_HEADS_THEN_COMPARE_TARGETS`

## Accepted findings

1. **Verified fact:** the current multiplier is
   \(\lambda_0=84{,}994{,}621.12635651\) bit/J, whereas the V0.18 pooled BASE
   EE is \(118{,}424{,}222.8550065\) bit/J. Therefore
   \(\lambda_0/\eta_{\mathrm{BASE}}=0.717713\); energy is underpriced by
   28.23% at that operating point.
2. **Verified fact:** V0.18 EXACT_ZR versus BASE changes total bits by
   -4.2578%, total energy by -5.2344%, and ratio-of-sums EE by +1.0306%, with
   unchanged service. The associated reduction in active beams is real.
3. **Inference accepted with a claim ceiling:** ZR induces a beam-consolidation
   outcome. This is a valid EE-improving outcome on the opened TRAIN panel, but
   it does not by itself prove that the unilateral ZR rate target is an exact
   attribution of that joint gain or that C3 is portable to a correctly priced
   background.
4. **Verified design consequence:** changing \(\lambda\) changes both C1 and
   C2 labels. OPS-3 contains terms of the form \(R-\lambda P\). A Q1-only
   repricing is therefore not a coherent background intervention.
5. **Verified implementation diagnosis:** the V0.19 seventh relational feature
   is unbounded because it stores an uncapped recurrence-power request for all
   native-legal actions, including opening-infeasible actions. Values near
   \(-2.4\times10^6\) are physical over-ceiling recurrence calculations, not
   sentinels. This affects learned-head conditioning only; the ZR oracle does
   not consume that feature. If the relational head is retained, bound the
   encoded feature (for example at the physical \(p_{\max}\) ceiling) without
   changing the native mask, raw physics, or target.
6. **Correction to the Fable report:** the quoted 7.5% value is not a
   route-local Q2 teacher-change agreement. It comes from V0.14's *joint*
   Q2+Q3 teacher/student diagnostic, whose learned Q3 failed. The same sealed
   result reports route-local Q2 validation skill 0.8283, 0.8297, and 0.8483
   at rung 3000 (mean 0.8354). This does not prove positive EE marginality for
   C2, but it does mean the existing Q2 learner is not accurately described
   as having only 7.5% route-local agreement.

## Rejected finding: CSE exact additivity

The Fable report correctly states the same-configuration identity

\[
\sum_u h_u(x)=P^N(x),
\]

where \(h_u\) is the proposed equal cost share. It then uses this identity to
claim exactness for targets whose share changes are evaluated on *different
unilateral branches* \(c^u=b^0_{-u}\oplus a_u\). That implication is false:

\[
\sum_u\left[h_u(c^u)-h_u(b^0)\right]
\ne
P^N(c)-P^N(b^0)
\]

in general, where \(c\) is the simultaneously executed joint action.

With unchanged V0.3 C1,

\[
z_{1,u}=\Delta B_{u}-\lambda\Delta P^N_u,
\]

and Fable's proposed CSE correction,

\[
z^{\mathrm{CSE}}_{3,u}=\Delta B_{-u}
-\lambda(\Delta h_u-\Delta P^N_u),
\]

the unilateral sum is only

\[
z_{1,u}+z^{\mathrm{CSE}}_{3,u}
=\Delta B_{\mathrm{all}}-\lambda\Delta h_u.
\]

It is neither the exact unilateral global surplus unless
\(\Delta h_u=\Delta P^N_u\), nor an exact simultaneous-deployment potential.

### Explicit sign-reversal counterexample

Take two users, two non-cochannel beams, one step, \(\lambda=1\), beam costs
one, and aggregate beam capacities \(C_A=1\), \(C_B=0.75\). The reference is
\((A,A)\): total bits one, energy one, shares \((0.5,0.5)\). For either
separately evaluated unilateral move to B,

\[
\Delta B_u=0.25,\quad \Delta B_{-u}=0.5,\quad
\Delta P^N=1,\quad\Delta h_u=0.5,
\]

so \(z_1=-0.75\), \(z_3^{\mathrm{CSE}}=1\), and each unilateral combined
target is +0.25. Summing the two separately evaluated targets gives +0.5.
Simultaneous deployment produces \((B,B)\), whose true surplus is
\(0.75-1-(1-1)=-0.25\). Thus CSE can reverse the joint sign.

**Decision:** CSE may remain a heuristic congestion/cost-sharing candidate,
but it cannot be called an exact EE decomposition or accepted as the canonical
R3 target on the present derivation.

## Correct next gate

The next gate is not episode training and not another learner-only repair.

The existing source payloads are sufficient for a fast first pass. A direct
reconstruction over all four already opened E1 opening datasets reproduced
the 1,452 C1 targets at the old multiplier to a maximum absolute difference
of \(3.82\times10^{-6}\) bit. Repricing those same raw rate/power components
at the proposed development value
\(\lambda'=118{,}424{,}222.8550065\) bit/J
(`0x1.c3c0a7b6b86d3p+26`) flips the sign of 75/1,452 C1 rows (5.17%). This is
large enough that reusing the old Q1 checkpoint would not be a neutral
approximation.

1. Freeze one development-only \(\lambda'=\eta_{\mathrm{BASE}}\) from an
   already opened TRAIN reference, including its binary64 hexadecimal value and
   provenance.
2. Rebuild/relabel **both** C1 and C2 from their stored raw TRAIN rate and power
   components at \(\lambda'\); retrain matched Q1 and Q2 checkpoints with the
   already frozen schedules.
3. Reconstruct Q1+Q2 reference actions under that matched background.
4. On identical TRAIN anchors, compare:
   - re-referenced ZR as the consolidation control;
   - symmetric non-focal externality under correct pricing;
   - any amended cost-share/congestion target, explicitly labelled heuristic
     unless a valid potential identity is supplied.
5. Only survivors proceed to a source-only learner gate and then a fresh
   physical panel. Episode training remains blocked until a learned C3 has a
   positive marginal FULL-vs-DROP-C3 result in the matched three-head context.

This gate isolates the actual fork: whether ZR survives coherent pricing, and
whether a distinct, learnable C3 exists. It does not require changing the
canonical ratio-of-sums EE formula or the three-Q one-argmax deployment rule.

## Current decision token

`REPRICE_ALL_HEADS_THEN_COMPARE_TARGETS`
