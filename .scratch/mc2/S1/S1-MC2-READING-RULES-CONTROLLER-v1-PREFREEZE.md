# S1 MC2 reading rules — controller v1, PRE-FREEZE

Date 2026-09-12, controller. **Not frozen yet**: two fields are still open and are marked `⟨FREEZE⟩`. Everything else is
decided here and will not move. When the two fields are filled, this file is hashed into the formal manifest
(`s1_manifest.py --reading-rules`), committed **before** any formal run starts, and nothing in it may change afterwards.

## 1. Adopted by reference, verbatim

**§4 of `S1-MC2-MANIFEST-PLAN.md` (lane E) is adopted as the body of these rules**: §4.1 estimand and quantities
(seed-wise relative pooled `Σbits/Σjoules` at ep 1000 on the 24 formal episodes, ratio of sums divided once, seed-mean as
the arithmetic mean over k ∈ {0,1,2} with all three per-seed ratios always reported, the 72 paired per-episode values and
their positive count reported beside every seed-mean, four fields + three condition columns on every number); §4.2 the
fixed comparison list; §4.3 the unrelaxed per-seed QoS floors; §4.4 the survival conjunction including the same-budget
MODQN eq-(16) gate; §4.5 what does not count; §4.6 nothing chosen after seeing formal data, the formal set read once at
ep 1000; §4.7 what is reported beside every reading.

I have checked each clause against the project's standing rules: the **only** success gate is the same-budget MODQN
eq-(16) comparison (non-learned rules and the frozen 9000-episode checkpoint are diagnostics and references, never
gates); the backbone/Catfish split (`D3T0_vs_D0` beside `FULL_vs_D0`) is reported and never merged into one headline
number; and every judge-side quantity — override or win rate, margin dose, judge evaluations, `ρ_info` — is a diagnostic,
never evidence.

## 2. Controller decisions made now (these close lane E's open items 2, 4, 5)

1. **Optional cells: both are INCLUDED** — `D3-null` (Amendment 4's matched hard null of the anchor) and `D3-XEP`
   (Amendment 12's plausible-but-uninformative null of the anchor). Reason: the paper must carry the backbone/Catfish
   decomposition, so the anchor's own nulls belong on the formal set rather than being left at E1 depth; they add ≈ 4
   worker-hours and ≈ 0 to the makespan because they fill wave gaps; and they are **anchor** questions that can neither
   rescue nor sink the MC2 claim, so they add no multiplicity to it. `D3-XEP`'s `ρ_info` decides **wording only**, and the
   measured DEV leak (`t0xep_agreement` 0.196 against an exact random-legal 0.039) makes it a lower bound — it can only
   make the anchor's information claim harder to pass, which is the right direction.
2. **Calibration pinned**: `/home/sat/mcrl-v025-cf3-pilot-ws/premeasure/calibration.json`, sha256
   `59952214a68469d9eccef292fa0eadf41e897ff74abd4b6cbff0635ee1a4562d` — the file every E0 / E1 / k8 / MC2 DEV run used.
3. **Formal evaluation stays at 24 episodes** `9_111_000+i / 9_112_000+i`, one read at ep 1000, one checkpoint, depth
   1000 episodes × 3 S1-TRAIN seeds, ε-decay 222. Unchanged from Amendment 13; no extension, no second read.
4. **No formal run may start** until: the DEV screen passes on three fresh seeds, this file is frozen and hashed into the
   committed manifest, and one fresh-context review of that manifest returns no unresolved INVALIDATES.
5. **Additional diagnostics to carry into the S1 record** (diagnostics, not evidence): the ep-100 dose-response
   (EE against challenger-override rate at a fixed anchor dose) and the output-change measurement (greedy agreement with
   `a^A` and `a^F`, split by gate-approved and gate-rejected rows). They are the reason the frozen mechanism is what it
   is, so the formal record should contain them.

## 3. The two fields still open

- `⟨FREEZE⟩ mechanism_id` — the DEV screen decides it. As of now **neither `MC2-JGO-v1` nor `MC2-ARB-v2` qualified** at
  ep 100 (`CONTROLLER-EP100-DECISION-2026-09-12.md`), a third version (`MC2-SEL-EXP-v3`, the experience channel) is
  proposed and awaits the owner, and the depth diagnostic on the selection seeds is still running. Until a version passes
  a three-fresh-seed ep-300 screen there is no mechanism id to freeze and therefore no formal manifest.
- `⟨FREEZE⟩ drop-one-of-B cell` — follows mechanically from the mechanism id: `D3-T0` for `MC2-JGO-v1` and for
  `MC2-SEL-EXP-v3` (both keep the anchor's label unconditional, so their A-only arm *is* the frozen single-Catfish arm);
  `A-only-v2` for `MC2-ARB-v2`.
- **Corrected 2026-09-12 per the owner ruling of 15:36 (§5, §7), before any v3 counted outcome:** `R-ungated` is a
  **secondary mechanism analysis, NOT a formal cell and NOT a gate** — the earlier sentence here that added it to the
  matrix and to §4.4 as a sixth gate is withdrawn. Under `MC2-SEL-EXP-v3` the S1 matrix is the core five (`D0`,
  `A-only` = `D3-T0`, `B-only-v3`, `FULL-v3`, gated `B-null-v3`) + same-budget `MODQN-eq16` + `D2-T0 τ = 0.3` +
  `D3-null` + `D3-XEP`, equivalent cells deduplicated; the survival conjunction is §4.4 with its gated-null clause, and
  "beats same-budget MODQN" alone is never sufficient for a multi-Catfish claim. The v3 action-collection seam, its
  planning random stream and its replay format must be wired into the formal driver and verified before the manifest
  is frozen.

## 4. What this file is not

It is not an authorisation to launch, not a claim that any version will survive, and not a substitute for the owner's
ruling on whether a third mechanism version may be built at all.
