# Fresh-context review of the complete S1 harness — the last gate before a one-way door

You are an independent reviewer with no prior context on this project. **Read the actual files. Do not review the
reports, summaries or commit messages — they are the thing most likely to be wrong.** Every claim you make must cite
`file:line`.

Repository: `/home/u24/papers/mcrl-leo-handover`, branch `wip/multi-catfish-v023-20260907`. The S1 harness also exists
as a server tree; the manifest artefact names its path and digest.

## Why this review exists

S1 is the project's **frozen formal screen**. Running it consumes the formal evaluation episode set
(`9_111_000+i` / `9_112_000+i`), which may never be used for development tuning. That is a **one-way door**: once S1
runs, that evidence is spent and the configuration is frozen. Your review is the last thing between the preparation
work and that door. A defect you miss is not recoverable by re-running.

## Verdict vocabulary — use exactly these

- **INVALIDATE** — a defect that would make an S1 result wrong, unreadable, or not what it claims to be.
- **BIAS** — anything that could tilt the result toward the desired conclusion, including a choice made after seeing a
  number, a comparison that is not like-for-like, or a control that is weaker than it is described as.
- **NOTE** — anything else worth saying.

Amendment 13 §7 authorises the launch **only if you return 0 INVALIDATES and 0 BIASES**. Do not soften a finding to
let the launch through, and do not invent one to look thorough. If you are unsure, say so explicitly and classify it
as a NOTE with your reasoning.

## The declared configuration you are checking it against

Authority: `.scratch/multi-catfish-v025-physics-successor/V025-CONTROLLER-AMENDMENT-13-S1-FROZEN-CONFIGURATION-2026-09-12.md`.
Supporting: Amendments 4, 8 (§3b), 10 and 12 in the same directory; `.scratch/dev-training/E1-RESULT-2026-09-12.md`;
`.scratch/dev-training/S1-PREFLIGHT-2026-09-12.md`.

Six trained arms, 3 seeds, 1000 episodes each: `D0`, `D3-T0`, `D3-null`, `D3-XEP`, `D2-T0 τ=0.3`,
`MODQN eq.(16) @1000`. Plus the frozen checkpoint `e6b063ef…` @9000 **rolled once, no training**, as a separately
labelled published reference.

## What you must verify, each independently

**1. Episode-set isolation — the one-way door.**
Confirm from the code, not from a claim, that during preparation **no** formal evaluation (`9_111_000+i` /
`9_112_000+i`), calibration (`9_121_000+i` / `9_122_000+i`) or CONFIRM (`9_311_000+i` / `9_312_000+i`) episode was
ever stepped. Search the result roots and logs for these ranges. Any occurrence outside the declared S1 evaluation
protocol is an INVALIDATE.

**2. Fresh formal namespaces.**
All six trained arms must use the **same-index** S1-TRAIN triple: train `9_251_000+k`, env `9_252_000+k`, mobility
`9_253_000+k`, for k = 0,1,2. `D3-null` must draw from `S1-NULL = default_rng((9_261_000, k))`. Verify that DEV
streams (`9_201_000` / `9_202_000` / `9_203_000`) and the development null stream `(9_241_000, k)` are **not** reused
anywhere in S1. Also check the **trainer-derived substreams**: if the trainer derives per-episode or per-layer seeds
from the declared seed, verify two different arms at the same k cannot end up drawing the same stream for different
purposes, and that two different k cannot collide.

**3. `T0-XEP` against Amendment 12 §2, clause by clause.**
- The teacher scores on the state of a **fixed pre-recorded reference episode at the same step index `t`** — and the
  substitution must cover the **whole teacher input state, including the lit set**, not only the channel term. A
  version that shifts `γ` but leaves the current lit set in place is **informative**, not a null: that is an
  INVALIDATE, and it is the single most likely defect in this harness.
- The learner's **current** action mask is applied after scoring.
- The reference trajectory is recorded **once**, under DEV-NULL, its identity and sha256 sealed, and never
  regenerated. Verify the sha256 yourself.
- The reference identity is part of the config hash.
- The residual-leakage diagnostic reports `T0-XEP`'s agreement with the **real** T0, not with itself.

**4. `D3-null` against Amendment 8 §3b.**
Same D3 loss, margin, `λ_E`, schedule, masks and gradient path; target = a seeded uniform random **legal** action.
T0 may be computed for diagnostics only — verify that **neither T0's action nor its scores can reach any D3-null loss
input**, by following the data flow, not by reading a comment.

**5. The two baseline paths.**
`MODQN eq.(16)` must train at 1000 episodes on the same S1-TRAIN triple in the same tree as the other arms. The
frozen `e6b063ef…` must roll **without any training or optimizer step** under the **same** evaluation protocol as the
trained arms. Any difference in the evaluation path between arms is a BIAS.

**6. Like-for-like evaluation.**
Every arm and the rolled reference must be evaluated identically: same episodes, same estimand (pooled
ratio-of-sums, Σbits/Σjoules divided once, full-buffer Shannon, no demand cap), same power accounting (consumed,
per-beam max over served users), same greedy/ε setting, same checkpoint selection rule. **There must be no checkpoint
shopping**: verify the checkpoint used is fixed in advance and identical in rule across arms.

**7. Aggregation identity.**
A result's identity must include at least `run_root + config_hash + seed_index + checkpoint_episode`. A weaker key
silently overwrites distinct runs — this has already happened once in this project. Verify collision-safety by
reading the aggregator, and check that the config hash actually covers mechanism, teacher identity, τ, the null key
and the reference-trajectory identity.

**8. Resume logic.**
If a run is interrupted and resumed, either its seed stream must be bit-identical to an uninterrupted run, or the
difference must be detectable in the output. A silent divergence on resume is an INVALIDATE.

**9. TLE archive.**
Pinned `427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9`, asserted **per run**, never compared across
archives. There is a second, unpinned archive in this project whose numbers are not comparable.

**10. Manifest ordering.**
The six-arm manifest, the namespaces, the 1000-episode depth, the frozen hyperparameters and the formal evaluation
namespace must be **committed and hashed before any formal outcome exists**. Verify from git history that the
manifest commit precedes any S1 result.

**11. Anything chosen after seeing a number.**
The whole point of the frozen configuration. If any hyperparameter, threshold, arm, seed, checkpoint or episode count
appears to have been selected from an observed result, that is a BIAS regardless of how reasonable the value is.

## Output

Write your review to `S1-REVIEW.md` in your working directory. Structure:

1. **Verdict line, first line of the file**: `INVALIDATES: <n> | BIASES: <n> | NOTES: <n>`.
2. One section per finding: the class, the `file:line`, what is wrong, and the concrete scenario in which it produces
   a wrong or misleading S1 result.
3. A section listing, for each of the eleven checks above, what you actually read to check it — so a reader can tell a
   real check from a skipped one.
4. A final section: **what you could not verify and why**.

Do not propose fixes. Do not edit any file other than your own review.
