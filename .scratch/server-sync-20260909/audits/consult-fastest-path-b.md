You are being asked a planning question, not a technical audit. Answer briefly and decisively. Read what you need in `/home/sat/mcrl-v023-codex-audits/parallel-20260909/` (today's reports) and `.scratch/multi-catfish-v025-physics-successor/` in any `mcrl-v025-*-ws`. Modify nothing. **At most 2 concurrent processes.** `DIAGNOSTIC_NOT_CLAIM`.

# The owner's requirement, restated exactly

Three learned components, and **each one individually must produce a substantial improvement in pooled energy efficiency** — not one per cent. The owner has explicitly said the complete system does **not** need to beat a classical local search; what matters is that each of the three components contributes substantially **within** the learned system.

The owner wants the fastest possible determination of whether that is achievable, and is willing to run things in parallel.

# What today established

- The whole improvement over a geometry-only baseline, about **+450 %**, is produced by a **non-learned** iterated best-response search. The learned layer sits downstream of it.
- The exhaustive bounded joint search sits about **+1 %** above that search's certified fixed point — **but an adjudication has just found that figure is certified against a different objective from the one it reports** (fixed-price at one boundary, versus pooled efficiency over forty-eight), so the association layer's true room is unknown and being measured.
- The amplifier is **94.8 %** of consumed power and its draw is set by the **power and mode control law**. A two-anchor coarse search, with the assignment held fixed, found **+113 %** over the declared law — but bits rose 115 % while joules rose 0.9 %, so most of it is capacity delivered above what users requested; a demand-capped rescoring is running. That same fast look reported the gain looks **mostly reachable by a per-beam local rule**, with cross-beam search adding only about **2.1 %**.
- Removing one component's informative training changed twelve to twenty-six proposed assignments for the first route, twenty-nine to sixty-nine for the second, and **zero** for the third, which enters only the ranking.
- A pilot measured a full-minus-drop gap of **+15.6 %** for the third route, on two seeds and five anchors with six of ten decisions outside training support.

Currently running in parallel: the first screening run of the source-training contrast; two independent audits of its harness; the association ceiling; the control-law ceiling; the objective-mismatch check; the demand-capped rescoring; and a mode-selection diagnosis.

# The question

**What is the shortest path to determining whether each of three learned components can individually produce a substantial gain — and if you believe it cannot be achieved under any arrangement of this system, say so and give the reason.**

Specifically:

1. **Which decision object gives all three components substantial room?** Association, power and mode, something else, or none. Note that the fast look suggests the control law's gain is mostly *local*, which would suit the two per-user routes but leave the set-level route with about two per cent.
2. **Is there an arrangement in which the set-level route has substantial room?** That route predicts what is left after summing the per-user terms. If that residual is intrinsically small in this system, say so plainly — it would mean the three-component requirement cannot be met regardless of decision object, and the owner needs to know that today rather than after a two-hundred-worker-hour panel.
3. **What is the single fastest experiment** that would settle question 2? Name it concretely enough to dispatch.
4. **What currently-running work is not worth its cost** given the owner's restated requirement, and should be stopped?

Be blunt and brief. A short answer that names the decisive experiment is worth more than a thorough survey. If the honest answer is that the requirement cannot be met, say that first.

Write your note as `FASTEST-PATH-<yourname>-2026-09-10.md` and print it in full as your final message.
