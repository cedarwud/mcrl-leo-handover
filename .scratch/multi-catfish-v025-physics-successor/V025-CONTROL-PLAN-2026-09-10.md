# Control plan — the decision tree, the critical path, and the standing obligations

**2026-09-10 09:10 UTC. This is the document that has been missing.** Until now the controller
has been running a queue: each result suggested the next job and the next job was dispatched.
That is reactive. This holds the decisions, what each needs, and what is parked — and every
subsequent report is written **against this**, not against whatever last landed.

---

## A. The goal, as it currently stands

Six strict inequalities, all on **pooled demand-capped EE**, exact terms first, learned heads
after:

`C1_ONLY > BASELINE` · `C2_ONLY > BASELINE` · `C3_ONLY > BASELINE`
`FULL > DROP_C1` · `FULL > DROP_C2` · `FULL > DROP_C3`

Magnitudes may be unequal; one route may be small. **Zero and negative are excluded in both
positions.** Full system need not beat classical search.

**Status: 4 of 6 pass on exact terms** (`FACTORIAL`): C2 conditional `+0.00%`, C3 alone
`-0.06%`.

---

## B. Decisions that must be made, and who makes each

| # | Decision | Owner or controller | Evidence needed | Status |
|---|---|---|---|---|
| **D1** | **Which decomposition** — incumbent `Psi` residual, fable's physical-term split, or astra's information innovations | **Owner** (it decides what the paper claims: whether "coordination" survives as a named route) | The bakeoff metrics pre-declared on 2026-09-10; plus `C2WIRING` and `SIGNFORK` on the incumbent | **Blocked** on those two |
| **D2** | Whether to train | Controller, against a pre-declared gate | G1 exact marginals justify it; G2 target is learnable | **Blocked** on `C1REAL`, and on `C2WIRING` for G1's validity |
| **D3** | Provisioning fix | **Owner** | Must be framed as a declared policy change acknowledging v1.9 §1, with rationale independent of any route's sign | **Blocked on framing since 2026-09-09.** Not re-raised. |
| **D4** | Mode-selection policy change (stale-CQI, `+78.02%` demand-capped) | **Owner** | `MODEDEPLOY` complete. Needs a declared-policy-change framing like D3 | **Ready to put to the owner.** Not yet put. |
| **D5** | Panel spine move set re-declaration | Controller | `FACTORIAL` + `C2WIRING`; erratum 16 | **Blocked**, and only matters if a panel is funded |
| **D6** | Whether the paper's claim is the three routes at all | **Owner** | Today's headroom sits mostly outside the three heads: assignment `9.87%`, mode selection `+78%` vs whole-system span `+17.03%` | **Not yet put to the owner.** `SWEEP` Q3 asks both reviewers this. |

---

## C. Critical path

```
C2WIRING ──┐
           ├──> G1 valid ──> D2 (train?) ──> short-ep run ──> learned-vs-ceiling gap
C1REAL  ───┘ (G2)
EXACTGEN ─────────────────> corpus for any training, under any decomposition
SIGNFORK ─────────────────> resolves residual sign ──> D1
SWEEPA/F ─────────────────> may invalidate any of the above ──> read first
```

**`C2WIRING` is the single highest-value item running.** If C2's `+0.00%` is a wiring defect,
`FACTORIAL` is void and so is the `+17.03%` span. If it is a magnitude fact, D1 gains a
concrete reason to prefer a replacement decomposition.

**`OBJMISMATCH` has run 5h15m** — longest of the day. It is not on the critical path for D2 but
it is the independent half of `SIGNFORK`'s question.

---

## D. Standing obligations the controller keeps re-discovering

These are recorded because each was already written down and then not applied.

1. **Demand-capped is the field convention.** The literature credits `min(capacity, demand)`;
   crediting surplus above contract is non-standard and flatters us. Recorded 2026-09-10,
   unused all day until 09:05.
2. **Reporting only pooled is against convention.** Papers that care about heterogeneity report
   the **summed-per-user** form alongside and criticise pooled for hiding per-link allocation.
   **Every number reported today is pooled-only.** From now on, summed-per-user is a required
   column in every measurement prompt, and is to be backfilled on any rerun.
3. **The owed-repair register** in `V025-CONTROLLER-FINDING-CORPUS-IS-SURROGATE-2026-09-10.md`
   §5 is read before any work is proposed, not when prompted.
4. **No arm pair runs without a fixture proving the arms can differ.** Written 2026-09-08,
   violated by `MARGIN_Q`, and `C2WIRING` exists because it was not applied to C2 either.
5. **Both contradiction numbers travel together** — `+5.62%` and `-60%` — until `SIGNFORK`.
6. **Every exact-term number is a ceiling**, never an achievable value, and is labelled so.
7. **Worker prompts constrain peak RSS, not only process count.** Cost 57.4 GB and a near-OOM.
8. **The square-root amplifier law is not in this literature.** The controller told the owner it
   was standard practice; it is a recognised model but not what this corpus uses.

---

## E. Parked, with the reason

| Item | Why parked |
|---|---|
| Mechanism-paper framing | **Closed on novelty.** Chen et al. VTC2024-Spring — a paper in our own repository, which we cite for the beam pattern — already has the occupancy-coupled power loop, equal intra-beam sharing, per-user rate floor, per-beam cap and pooled EE. Stop investing here. |
| DR round 18 | **Written, never sent, and the topic is now wrong.** Retarget to near-cancelling value decompositions (VDN/QMIX/QTRAN, Harsanyi/Möbius conditioning) so it informs D1. Owner runs it. |
| The C3 panel | Not authorised, and should not be built before D1 |
| `CTRLCAP` | Killed for memory. Re-dispatch with per-anchor batching after the critical path clears |
| Learned-route novelty reading | Record says "still running" — **verify whether it ever landed** |

---

## F. How the controller reports from now on

Every report states: which decision it advances, what it changes on the critical path, and
what is still blocking. Not "here is the number that just arrived".
