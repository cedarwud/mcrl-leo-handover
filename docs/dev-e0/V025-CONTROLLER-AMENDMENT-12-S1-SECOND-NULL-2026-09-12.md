# Amendment 12 to Ruling 2 — the plausible-but-uninformative second null for S1: `T0-XEP`

Date: 2026-09-12 (23:30 UTC 2026-09-11). **Controller declaration**, filling the slot Amendment 10 §2 reserved
("the plausible-but-uninformative second null is declared before S1, not improvised inside E1"). Written **blind to
E1's ep-300 result** — the nine E1 runs are at roughly ep 100 as this is committed. It opens no new experiment
family: a matched null is a control that Amendment 4 already requires, and this fills that slot rather than adding
to it.

## 1. Why the existing null is not enough

`D3-null` — the same margin loss, weight, schedule, masks and gradient path aimed at a **random legal action** — is
the load-bearing control of the E0 freeze, and it is emphatic: −39 to −55 % against D0, served ≈ 0.92, 0/24 on every
development seed. But it is a **low bar**. It shows that a random hard teacher is bad; it cannot separate

- (a) the gain comes from T0's **state-specific** advice — it reads *this* geometry and *this* lit set — from
- (b) the gain comes from the **form** of the advice — a generic structural prior ("prefer an already-lit slot with a
  good nominal link") that would help even if it were wrong about the current state — amplified by the hard margin.

(b) is a live possibility precisely because hard injection amplifies teacher quality so strongly (soft-null cost
≈ 2 %, hard-null cost 39–55 %). A reviewer will ask this question. It is cheaper to answer it than to be asked.

## 2. The declaration: `T0-XEP`, cross-episode T0

**Arm name `D3-XEP`. Mechanism unchanged (D3, `m = 0.15`, `λ_E = 1.0`). Teacher replaced by `T0-XEP`:**

At step `t` of the learner's episode, `T0-XEP` computes T0's ordinary score
`log2(1 + γ_a) − c·[beam a unlit]` with `c = 1, m = 0` — the frozen T0 definition, unmodified — on the state
recorded at **step `t` of a fixed pre-recorded reference episode**, then restricts the resulting argmax to the
learner's **current** legal action mask.

Why this is the right null:

- **Plausible.** Same functional form, same hyperparameters, same score scale and margin-magnitude distribution,
  same episode-phase statistics (step `t` is matched to step `t`, so the geometry epoch and the remaining-time
  feature line up). It is a well-formed teacher, not noise.
- **Uninformative.** The reference episode is a different constellation and user realisation, so the advice is
  decorrelated from the state the learner is actually in. The 28 candidate slots are satellite-major beam-minor over
  the *visible* set, so slot `k` in the reference episode is not the same physical beam as slot `k` now — that is
  the point, and it must be said plainly in the write-up rather than discovered by a reviewer.
- **Causal and cheap.** One reference trajectory, recorded once, no counterfactual, no search.

**Provenance.** The reference trajectory is recorded once under the **DEV-NULL** seed namespace, never DEV, DEVVAL
or CONFIRM; its identity and file sha256 are recorded **before the first S1 run** and it may not be regenerated
afterwards.

**Residual-leakage diagnostic, declared now.** Both `t0_agreement` and `t0_score_regret` already exist in every
DEVVAL record. Report `T0-XEP`'s agreement with the real T0 on the same states. If it sits materially above the
random-legal baseline, the null carries residual information, the measured contrast is a **lower bound** on T0's
information share, and it must be reported as such.

## 3. The reading rule, fixed before any number exists

With `G = EE(D3-T0) − EE(D0)` on paired seeds, define the **information share**

    ρ_info = ( EE(D3-T0) − EE(D3-XEP) ) / ( EE(D3-T0) − EE(D0) )

- **`ρ_info ≥ 0.5`** — the plausible null recovers less than half the gain. The gain is attributable to T0's
  state-specific information. The catfish claim stands **as currently worded**.
- **`0 < ρ_info < 0.5`** — most of the gain survives a teacher that is well-formed but wrong about the current
  state. The claim must be **restated**: what helps is a structural prior delivered by hard margin injection, of
  which T0 is one convenient carrier. That is a weaker claim, still publishable, and it is reported that way — not
  quietly kept in the strong wording.
- **`ρ_info ≤ 0`** — the plausible null matches or beats `D3-T0`. The teacher's content is then irrelevant and the
  mechanism is the injection channel plus a structural prior. The catfish framing for T0 **fails** and goes to
  controller and owner review before anything else is written.

## 4. The null must earn the word "plausible"

`T0-XEP` counts as a plausible null only if its own arm is **not destructive**: `served ≥ 0.99` and
`EE(D3-XEP) ≥ 0.98 × EE(D0)`. If it collapses to the same destruction as `D3-null`, then it is a second hard null,
the "low bar" caveat is **unresolved**, and that is what the report says. A destructive `T0-XEP` may not be
presented as a passed strong-null screen.

## 5. Scope, and what this does not change

- One additional arm at S1, paired to the S1 `D3-T0` arm on the same seeds and the same depth. The S1 seed count
  and depth are set by the S1 configuration, not here.
- **S1 carries both nulls.** `D3-null` remains the matched null that Amendment 4's conjunctive gate is read
  against, exactly as already specified. `D3-XEP` adds **no new pass/fail gate**; it determines **how the claim is
  worded**. The single exception in §3 (`ρ_info ≤ 0` → review) is not a new gate but the standing discipline that
  the framing must match the evidence.
- No change to the frozen backbone, the observation, the credit mode, `η`, the learner, D3's or D2's
  hyperparameters, B2 (closed), exact-DR (closed), or any Amendment 4, 5, 8 or 10 threshold.
