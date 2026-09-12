# Fresh-context review of the complete MC2 S1 harness — the last gate before a one-way door

You are an independent reviewer with no prior context on this project. **Read the actual files. Do
not review the reports, summaries or commit messages — they are the thing most likely to be wrong.**
Every claim you make must cite `file:line`.

Repository: `<<<REPO PATH>>>`, branch `<<<BRANCH>>>`, **commit `<<<COMMIT SHA>>>`**.
The frozen declaration under review: `<<<MANIFEST PATH>>>`, sha256 `<<<MANIFEST SHA256>>>`.
The frozen reading rules it hashes: `<<<READING RULES PATH>>>`, sha256 `<<<RULES SHA256>>>`.
Frozen mechanism id: `<<<MC2-JGO-v1 | MC2-ARB-v2>>>`. Optional cells included: `<<<none | D3-null |
D3-XEP | both>>>`.

## Why this review exists

S1 is the project's **frozen formal screen**. Running it consumes the formal evaluation episode set
(`9_111_000+i` / `9_112_000+i`), which may never be used for development tuning. That is a **one-way
door**: once S1 runs, that evidence is spent and the configuration is frozen. Your review is the last
thing between the preparation work and that door. A defect you miss is not recoverable by re-running.

## Verdict vocabulary — use exactly these

- **INVALIDATE** — a defect that would make an S1 result wrong, unreadable, or not what it claims.
- **BIAS** — anything that could tilt the result toward the desired conclusion: a choice made after
  seeing a number, a comparison that is not like-for-like, a control weaker than it is described as.
- **NOTE** — anything else worth saying.

Amendment 13 §7 authorises the launch **only if you return 0 INVALIDATES and 0 BIASES**. Do not
soften a finding to let the launch through, and do not invent one to look thorough. If you are
unsure, say so explicitly and classify it as a NOTE with your reasoning.

## What is being screened

Two scripted specialists outside a single RL learner, and a **training-only** judge that gates which
specialist's action becomes a supervised large-margin target on the learner's own replay rows:

- **Catfish-A** = `T0`, a frozen rule: `argmax_{a legal} log2(1+max(γ_a,0)) − 1[N_a = 0]`.
- **Catfish-B** = `T_NEXT`, a one-step ephemeris-only lookahead (same physical `(norad, cell)`
  visible at `t+1`), which **abstains** at the last decision step.
- **The judge** scores a candidate by `κ(a) = (n_served, B − η₀·E)` of a pre-step counterfactual
  evaluation of `(a, x_{−u})` on a deep copy of the environment generator, lexicographic, ties to the
  incumbent, `η₀` frozen. It is never deployed. **A judge win is not an EE improvement.**
- The frozen version is one of two declared rules (`MC2-JGO-v1`: unconditional anchor, B may only
  override; `MC2-ARB-v2`: `{x_u, a^A, a^B}` arbitration). The declaration names which one.

Deployment is the learner's masked argmax of three Q networks at a fixed `η` — no specialist, no
judge, no oracle at inference.

## Authority documents

- `.scratch/mc2/MC2-CATFISH-IDENTITY-AND-INTERVENTION-CONTRACT-2026-09-12.md` (r2) — the cells, what
  each ablates, and the declared readings.
- `docs/dev-e0/V025-CONTROLLER-AMENDMENT-13-S1-FROZEN-CONFIGURATION-2026-09-12.md` — the S1
  namespaces, the 1000-episode depth, the same-budget MODQN win gate, the rolled 9000-episode
  reference, "the complete matrix or nothing", and the launch conditions.
- `docs/dev-e0/V025-CONTROLLER-AMENDMENT-12-S1-SECOND-NULL-2026-09-12.md` — the optional `D3-XEP`
  null and its reading rule.
- `.scratch/mc2/B/CONTRACT-COSIGN.md` — the method owner's co-sign (R1-1 … R1-4, F-1 … F-3).
- `.scratch/mc2/S1/S1-MC2-PORT.md` and `S1-MC2-MANIFEST-PLAN.md` — **the lane's own claims; treat
  them as the hypothesis to test, not as evidence.**

## What you must verify, each independently

**1. Episode-set isolation — the one-way door.**
Confirm **from the code**, not from a claim, that during preparation no formal evaluation
(`9_111_000+i` / `9_112_000+i`), calibration (`9_121_000+i` / `9_122_000+i`) or CONFIRM
(`9_311_000+i` / `9_312_000+i`) episode was ever stepped. Search the result roots, logs and
`.scratch` for those ranges. Any occurrence outside the declared S1 evaluation protocol is an
INVALIDATE. Note that the preparation deliberately ran the formal driver in a DEVELOPMENT lane
(`--preflight-dev`): check that this mode cannot construct a formal stream
(`src/mcrl/algorithms/cf_s1_lane.py`, `scripts/run_s1.py`), and that a preflight root and a formal
root cannot be the same root.

**2. Fresh formal namespaces, including the new one.**
Every trained cell must use the same-index S1-TRAIN triple `9_251_000+k / 9_252_000+k / 9_253_000+k`,
k = 0,1,2. The optional `D3-null` must draw from `(9_261_000, k)`. The MC2 `B-null` must draw from
`(9_263_000, k)` — a namespace **this lane declared**; verify it is genuinely unused elsewhere in the
project and that no development stream is reused anywhere in S1. Check the trainer-derived
substreams (`train + 70_001`, `train + 90_211`): two cells at the same k must not draw the same
stream for different purposes, and two different k must not collide. **Check the composite-key
aliasing claim yourself**: `numpy.random.default_rng((B, 0))` versus `default_rng(B)`.

**3. The judge cannot perturb what it measures.**
Verify from the code that every judge evaluation deep-copies the environment generator, runs inside
frozen driver positions, commits nothing, and advances no generator; that the base evaluation is
asserted equal to the committed step (bits, joules, served flags); and that the number of judge
evaluations therefore cannot move the trajectory. A judge that consumes the environment generator is
an INVALIDATE.

**4. The ablation cells are what their names say.**
- `FULL` with B disabled must be the declared drop-one: under `MC2-JGO-v1` the frozen `D3-T0` arm
  (check the parameter-level identity claim), under `MC2-ARB-v2` the `A-only-v2` cell. If the
  declaration's `drop_one_of_B` does not match the code's disable semantics, that is an INVALIDATE.
- `B-only` must carry **no** anchor and must not inject T0 through `T_NEXT`'s final-step fallback
  (B abstains at `t = T−1`).
- `B-null` must be the same anchor, judge, gate and abstention with a content-free uniform legal
  proposal from its own stream, reading no `T_NEXT` quantity. It is **not** dose-matched — verify the
  declaration says so where the comparison is stated, and flag as BIAS any wording that lets
  `FULL > B-null` mean "foresight is the active ingredient" or "the judge is valuable".
- Under v1, A-only and the single-Catfish baseline are deliberately ONE cell. Check that this is the
  same configuration and not two names for it, and that nothing reads it twice as if independent.

**5. The two baseline paths.**
`MODQN eq-(16)` must train at 1000 episodes on the same S1-TRAIN triple in the same tree as the other
cells, with the same budget-scaled ε schedule (222) — a different exploration schedule on one side of
the win gate is a BIAS. The frozen `e6b063ef…` checkpoint must roll **without any training or
optimizer step** under the **same** evaluation protocol. Any difference in the evaluation path
between cells is a BIAS.

**6. Like-for-like evaluation, and deployment purity.**
Every cell and the rolled reference must be evaluated identically: same episodes, same estimand
(pooled ratio-of-sums, Σbits/Σjoules divided once, full-buffer Shannon, no demand cap), same power
accounting (consumed, per-beam max over served users), same greedy setting, same checkpoint rule.
**There must be no checkpoint shopping** — verify there is exactly one checkpoint and one read per
run. Verify that the read consults no Catfish source and no judge (the harness unregisters sources
and disables the judge for the read: check this is real and that it is applied to every cell
including the MODQN ones and the rolled reference).

**7. Aggregation identity.**
A result's identity must include at least `run_root + config_hash + cell + seed_index +
checkpoint_episode`. A weaker key silently overwrites distinct runs — this has already happened once
in this project. Verify collision-safety, and that the configuration hash actually covers: the
mechanism/rule id, the source set, the source identities (including `cf_tnext.py`'s sha256), the
judge id with `η₀`, the null id with its key, τ, the lane, and the `T0-XEP` reference identity if
that cell is included. Verify the declaration's per-run hashes are all distinct.

**8. Resume logic.**
If a run is interrupted and resumed, either its seed stream is bit-identical to an uninterrupted run,
or the difference is detectable in the output. A silent divergence on resume is an INVALIDATE. Check
the judge's own null generator is saved and restored, and that a resume against a different reference
trajectory, lane or judge spec is refused.

**9. TLE archive.**
Pinned `427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9`, asserted **per run**,
never compared across archives. There is a second, unpinned archive in this project whose numbers are
not comparable.

**10. Declaration ordering.**
The cell list, the namespaces, the depth, the frozen hyperparameters, the formal evaluation namespace
**and the reading rules' digest** must be committed and hashed **before any formal outcome exists**.
Verify from git history that the manifest commit precedes any S1 result, and that
`s1_manifest.py --check` regenerates the committed manifest byte for byte.

**11. The reading rules themselves.**
Read `<<<READING RULES PATH>>>` and check each of: the estimand is stated unambiguously (ratio of
sums, one division, at ep 1000, 24 episodes, greedy); every gate has a threshold, a direction and a
seed-agreement requirement; the QoS floors are per seed and unrelaxed; what does **not** count as
surviving is stated (including: beating only `D0`, or only the 9000-episode reference, is not a
pass); diagnostics (override rate, dose, judge evaluations, ρ_info) are excluded from the gates.
Anything that would let a failed screen be re-read as a success is a BIAS.

**12. Anything chosen after seeing a number.**
The whole point of the frozen configuration. The development screen that selected this version has
already run, so pay particular attention: if any threshold, cell, seed, depth or estimand appears to
have been chosen to fit the development result, or if the S1 gates are weaker than the development
gates that the version already passed, that is a BIAS regardless of how reasonable the value is.

**13. The port itself (new in this round).**
The S1 lane was added as a subclass (`cf_s1.py`, `cf_s1_lane.py`) rather than as fields on the
development settings, so that the development screen's configuration hashes are unchanged. Verify:
(a) `cf_dev.DevSettings` has no S1 field and the development arms' hashes are unchanged (a test
claims this against goldens from commit `6136c514` — recompute at least one yourself); (b) the S1
trainer's `D3-XEP` loss is the same `d3_margin_loss` with the same `m` and `λ_E` as `D3-T0`, only the
target differing; (c) the `D3-XEP` step index is taken from the training-time step seam and fails
closed if that seam is absent — a wrong step index would silently change the null; (d) the shared-file
hunks listed in `S1-MC2-PORT.md` §2 are the only ones (diff the tree against lane A's mechanism
commit and say so if there are more).

## Output

Write your review to `S1-MC2-REVIEW.md` in your working directory. Structure:

1. **Verdict line, first line of the file**: `INVALIDATES: <n> | BIASES: <n> | NOTES: <n>`.
2. One section per finding: the class, the `file:line`, what is wrong, and the concrete scenario in
   which it produces a wrong or misleading S1 result.
3. A section listing, for each of the thirteen checks above, what you actually read to check it — so
   a reader can tell a real check from a skipped one.
4. A final section: **what you could not verify and why**.

Do not propose fixes. Do not edit any file other than your own review.
