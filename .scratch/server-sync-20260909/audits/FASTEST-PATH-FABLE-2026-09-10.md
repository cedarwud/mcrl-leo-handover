Note written to `/home/sat/mcrl-v023-codex-audits/parallel-20260909/FASTEST-PATH-FABLE-2026-09-10.md`. Full text follows.

---

**The requirement cannot be met in this system under any arrangement of decision objects, because the set-level residual is small at both objects that have been measured: about +0.7 % to +1.3 % on association under the corrected rule, and about +2.1 % on power and mode. One evaluation-only experiment, already three-quarters running, closes the one loophole left.**

`DIAGNOSTIC_NOT_CLAIM` — planning note, Fable, 2026-09-10. Read only; nothing modified.

## Why the answer is no

The requirement needs three leave-one-out marginals, each substantial, inside one learned system. A marginal cannot exceed the room the decision object leaves above the non-learned reference every arm shares. Today's measurements of that room:

| Decision object | Room above the shared reference | Source | Of which non-additive (set-level) |
|---|---:|---|---:|
| Association, corrected `MARGIN_Q` | +0.72 % over 30 dates, CI [+0.44, +1.00]; +1.29 % on the 20-anchor reseeded panel, 6/20 anchors negative | CEILING30-MARGIN, RESEEDED-SPAN | essentially all of it, and it is the whole pie for C1, C2 and C3 together |
| Association, defective `SEALED` | +4.6 % to +5.9 % | same | irrelevant: this rule credits nothing on three quarters of transmissions |
| Power and mode, capacity numerator | +113 % at fixed assignment | CONTROL-LAW-FAST-LOOK | +2.1 %: an independent per-beam probe reaches 97.9 % of the coupled search |
| Power and mode, demand-capped | pending (DEMANDCAP) | — | still bounded by the same 2.1 % local-versus-coupled split |

Three facts make the small residual structural rather than a sampling accident. First, the coordination span collapsed by a factor of four to eight when the provisioning defect was repaired, so most of the "coordination room" ever observed was an artefact of the defective rule. Second, the one mechanism that fires at real anchors is consolidation, a step function of summed beam occupancy; that is expressible as a per-user feature and need not be a residual at all. Third, at the power object the interference coupling that would make the set-level term necessary is weak relative to the local amplifier and mode-threshold effects, which is exactly what the 2.1 % says.

The +15.6 % pilot gap for C3 is not counter-evidence. The pie above the fixed point is about 1 %, so any leave-one-out contrast clearing 5 % is the DROP arm falling below the fixed point (six of ten decisions chose the size-100 coalition, outside training support). The pre-declared degeneracy screen will strip it.

## Answers

**1. Which decision object gives all three substantial room?** None. Association gives about 1 % in total under the corrected rule. Power and mode gives C1 large room, but C2 has nothing to add there because the gain is per slot with no temporal component, and C3 gets about 2 %. Splitting the objects (C1 on power, C3 on association, C2 on something else) does not help: C3's association ceiling is 1.3 % even with a perfect oracle, and no object with measured room exists for C2.

**2. Is there an arrangement in which the set-level route has substantial room?** No. The residual after summing per-user terms is intrinsically small in this system: about 1 % on association and 2 % on power and mode, both measured with an exact oracle standing in for the learner, so no amount of training changes them. The only untested possibility is that the 1 % association figure is understated because the joint selector was certified against the fixed-price boundary-zero proxy rather than the reported 48-boundary objective. That is the loophole the experiment below closes. If it also comes back under 5 %, the owner should treat the three-component requirement as unmeetable today.

**3. The single fastest experiment.** `ORACLE-PSI-CEILING`: no learner, evaluation only, two halves, at most 2 processes each.

- **Association half.** On the 20-anchor panel under both rules, start from the first-improvement fixed point and evaluate every bounded-catalogue row under the *reported* objective (48-boundary pooled committed efficiency, unchanged guard). Report the pooled best-row span over the fixed point. This is the maximum any C3 head could add in the deployed selector. It is O2/O3 of the running OBJMISMATCH job; the only addition needed is to label that span as the oracle-Ψ ceiling and print it in the first line, both rules.
- **Power half.** On the eight CTRLCEIL anchors, rerun the fast look's coupled search and its independent per-beam probe under the `DEMAND_CAPPED` numerator. Report coupled minus local. About two minutes per anchor by the fast look's own timing.
- **Pre-declared decision rule.** If both halves are below 5 % pooled under `MARGIN_Q`, the set-level route has no substantial room anywhere in this system and the panel should not be run. If the association half exceeds 5 %, the proxy was hiding real coordination room and the panel becomes worth its cost for C3 only.

Expected outcome, stated before the result: both under 5 %.

**4. What to stop.**

- **Stop C3SCREEN now.** Its harness is self-declared incomplete (MARGIN_Q proposal path not integrated, tape digests differ), it projects 185 worker-hours plus 15.5 s per epoch at full scale, and it is measuring marginals inside a 1 % pie. Every contrast it can show above the margin is degeneracy by arithmetic. Let PANELAUDITA and PANELAUDITF finish only if the owner intends to run the panel after question 3 resolves; otherwise stop them too. They cost no machine time, only attention.
- **Cut MULTISTART to M2 only.** M1 and M3 measure how much a better non-learned search could gain, which the owner has declared irrelevant. M2 (2-swap optimality of the endpoints) is the one part that bears on set-level room outside the bounded catalogue; keep it.
- **Keep OBJMISMATCH, DEMANDCAP, MODEGAP.** OBJMISMATCH is the decisive experiment. DEMANDCAP sizes the only large room in the system honestly. MODEGAP is twenty minutes and tells whether the control gain is a per-beam mode fix, in which case even C1's room belongs to a one-line rule.
- **Keep CTRLCEIL but read only its C5 line.** The framing review is right that its "ceiling" is ill-posed without a causal policy contract. Its one useful output is whether the improved settings need cross-beam information; the fast look already says mostly not.

## One sentence the owner should hear

The learned layer sits on top of a non-learned search that produces all of the +450 %, and every honest measurement of what is left above that search under the corrected rule is about one per cent; the requirement asks for three substantial slices of a pie that is smaller than one slice.
