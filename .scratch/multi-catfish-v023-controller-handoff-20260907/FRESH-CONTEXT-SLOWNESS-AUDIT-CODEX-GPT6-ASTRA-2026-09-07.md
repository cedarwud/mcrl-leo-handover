**Multi-Catfish slowness audit — 2026-09-07**

Read-only local review; no files modified, network, SSH, simulations, or training. Historical timings below come from local records, not a live server check. Cost estimates overlap and must not be summed.

**(A) Five structural causes**

1. **Long jobs are functioning as integration tests.** The [handoff §1b–§3](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-controller-handoff-20260907/HANDOFF-EXECUTION-CLOSURE-AUDIT-2026-09-07.md:143) documents six R7 verifier defects and seven C1/C2 consumer mismatches. Tests authenticated their own assumptions: wrong verifier copy, mocked factory boundaries, duplicated receipt literals, and benchmarks bypassing writing. Real artifacts exposed array-layout, provenance-length, merge-receipt, and serialization failures.

   **Cost:** R7’s decisive source arrays existed September 6 at 15:10 UTC; the verdict arrived September 7 at 12:54—**21h44m later**. C1/C2 r5 spent **80–178 minutes per completed shard**; r6 failed after approximately **94 minutes**. One-minute offline probes subsequently exposed additional defects. This is directly recoverable engineering latency.

2. **Every experiment carries another execution system.** The requested scratch census gives **97 entries, 94 directories**: 51 V0.23, 13 other versioned Multi-Catfish, one other Multi-Catfish, and 29 other directories. These include audits and fixtures, so 94 is not an implementation-package count.

   The requested glue patterns span **90 files across 31 directories**:

   | Glue | Lines |
   |---|---:|
   | `sync_launch*.sh` | 4,275 |
   | `preflight*.py` | 7,058 |
   | `seal*.py` | 3,000 |
   | `verify*.py` | 54,101 |
   | **Total** | **68,434** |

   Exact-content deduplication still leaves **46,538 lines**. Volume alone proves neither waste nor defects; the demonstrated divergent literals, manifests, and imports establish the maintenance problem. The 228/448 change also broke authentication’s assumption that historical producer and current learner inhabit identical code trees.

   **Cost:** multiple hours of same-day integration/review; an independent total is unavailable.

3. **C3 eligibility became a prerequisite for useful progress elsewhere.** There are **66 matching design documents**. The dated progression is V0.3 on August 31; V0.4–5 September 1; V0.6–9 September 1–2; V0.10–17 September 3; V0.18–19 September 4; V0.20–23 September 4–5; then V0.23 repair/adjudication through September 7.

   The [memory index](/home/u24/.claude/projects/-home-u24-papers-mcrl-leo-handover/memory/MEMORY.md:19), supplemented by local gate receipts, supports **seven unsuccessful C3 design/learner tracks across September 3–4**: V0.14, V0.15, V0.15-R, V0.16, V0.17, V0.18 learner, and V0.19 learner. This counts V0.14 and its probe together and excludes infrastructure STOPs. Five are dated September 3, two September 4: **same-day or next-day iteration**, not seven multi-day training runs. Later stops include Expected-ZR and R7.

   **Cost:** roughly **five calendar days of continued C3 gating, September 2–7**, overlapping implementation work. The supplied records do not explain every hour since August 23.

4. **Cheap rejection and expensive qualification are insufficiently separated.** The [contingency ladder](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-c3-observability/V023-C3-RAPID-CONTINGENCY-LADDER-PREOUTCOME-2026-09-06.md) already specifies shared-tape, two-step rejection before larger screens. The [R7 contract](/home/u24/papers/mcrl-leo-handover/docs/MULTI-CATFISH-MCRL-V023-LC-SRS-SUCCESSOR-GATE-CONTRACT-R7-BALANCED-2026-09-06.md) requires eight worlds, three learner seeds, and extensive composition checks. It correctly forbids retroactive shortcuts. However, the execution chain withheld an already-determinable necessary-condition failure behind unrelated verifier crashes.

   **Cost:** approximately **22 hours of delayed knowledge** in R7; future savings depend on prospective staging. Faster verification would have delivered STOP sooner, not permitted training.

5. **Scheduling and review optimize individual tasks rather than completed decisions.** Sixteen shards consumed approximately **77 GB of 91 GB**; an inventory needed another 8–9 GB. The controller initially waited on one child while another had already failed. Reviews repeatedly discovered the next boundary rather than closing a fixed consumer checklist. The successor contract review itself found seven defects, including circular sealing and incompatible continuation semantics.

   **Cost:** r5 failure notification lagged its first failure by approximately **97 minutes**; reboot-to-relaunch added **17 minutes**, excluding lost computation. Review overhead is evident but not separately timed.

**(B) Is there a core problem nobody has caught?**

**No—not on the inspected evidence.** The core scientific problem was already identified: a scoped oracle/teacher benefit does not guarantee observable, learnable, independently composable C3 action choices. R7 passed held-out prediction but failed physical and learned composition conditions. That is a valid scientific STOP.

The unresolved process problem is that these known risks still trigger bespoke, serial integration and qualification cycles.

Also, **“no learner training has started” is literally inaccurate**: V0.18/V0.19 receipts record 100 updates per initialization, and later diagnostic updates occurred. The current formal successor remains unstarted in the supplied snapshot; fixed-policy episode evaluation must not be called episode-based learning.

**(C) Top five changes for the next 72 hours**

1. **PROCESS — controller; hours 0–6.** Finish the already-adopted [Route C](/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-controller-handoff-20260907/ADJUDICATION-SUCCESSOR-ROUTE-CODEX-GPT6-ASTRA-ULTRA-2026-09-07.md): independent C1/C2 successor, C3 outside its critical path. Close the existing contract-review checklist and bind authenticated implementation/artifact digests before successor computation. **Must NOT** reopen R7, silently substitute a neutral C3, or claim three-head efficacy.

2. **ENGINEERING-PARALLEL — implementation model; hours 0–12.** Exercise the same consumer chain against all available compatible real artifacts: authentication → row loading → merge/seal verification → provider → export/reload/resume → physical adapter. Report PASS/FAIL/BLOCKED without stopping the inventory at the first independent failure. **Must NOT** fabricate passing receipts, weaken checks, or overwrite preserved artifacts.

3. **ENGINEERING-PARALLEL — read-only reviewer; hours 0–12.** Independently inspect producer–consumer schemas, normalization, dimensions, serialization, imported code origins, baseline separation, and exact transfer closure. Return one consolidated blocker list; reopen only for changed boundaries or new evidence. **Must NOT** introduce new scientific thresholds or an expanding general hardening audit.

4. **ENGINEERING-PARALLEL — implementation model; hours 12–72.** After required freeze, time one real vertical slice and proceed through the authorized source schedule when mechanical admission passes. Record loading, updates, export, resume, and world stepping separately. Use resource-bounded concurrency. **Must NOT** select checkpoints by loss/EE, restart valid units, or promise episode-learning throughput from fixed-policy measurements.

5. **PROCESS — controller; hours 0–24.** Separate INVALID_RUN repair from scientific termination. Predetermine smallest-unit replay, checkpoint recovery, and C3 spending limits. Prepare existing kill-screen plumbing concurrently. **Must NOT** treat the contingency document as launch authority, race D/F and pick favorable outcomes, or tune any formula, sign, threshold, seed, horizon, lambda, budget, or acceptance rule. Any admission route must satisfy the owner’s stricter prohibition on hypothesis selection by outcome.

**(D) Three changes for subsequent weeks**

1. **Build one reusable execution library:** typed artifact schemas, independent producer-derived fixtures, deterministic scheduling, checkpointing, and verification. New experiments supply frozen configuration and scoped adapters; historical packages remain immutable.

2. **Separate the research and engineering dependency graphs:** engineering rehearsals proceed independently; scientific spending follows prospectively declared necessary-condition screens. C1/C2 progress does not imply C3 admission.

3. **Maintain one current authority index and latency ledger:** distinguish scientific failure, infrastructure failure, source learning, fixed-policy evaluation, and episode learning. Track time to first real consumer pass and valid decision. Keep TEST closed and all sealed artifacts and frozen manifests unchanged.

ASTRA_SLOWNESS_AUDIT=DONE