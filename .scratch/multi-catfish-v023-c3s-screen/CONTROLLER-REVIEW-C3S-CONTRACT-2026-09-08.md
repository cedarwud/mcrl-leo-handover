# Controller review — C3-S set-level coordinator kill-screen contract (2026-09-08 07:25 UTC) — UNSEALED

Draft: `V023-C3S-SET-LEVEL-COORDINATOR-KILL-SCREEN-CONTRACT-2026-09-08.md` (astra ultra, xhigh, read-only; verbatim copy of the handoff draft).
Status: body ACCEPTED as written; seal after (i) the runner implementation lands and passes one astra implementation review, (ii) the
placeholders are bound by the preflight. No computation before the seal. Nothing here changes a scientific choice of the draft.

Accepted interpretations (the draft's plainest readings): C3-S = deployable model-based set-level coordinator over the learned Q1+Q2 (no
third additive head); nominal channel = OPS-3 median/no-fading convention (unit Rician gain, zero-dB shadowing); catalog = BASE ∪ every legal
non-NOOP non-BASE-equivalent unilateral change ∪ every full-origin evacuation to a commonly legal destination (fixed enumeration order; ties
lexicographic with BASE first); objective B̂ − η_ref·Ê with nominal served ≥ BASE nominal served; **η_ref fixed to the E1 η_BASE constant
124075740.54723135 bits/J (hex 0x1.d94fb72305d6ap+26)** shared by all worlds/lineages/steps; origin membership from the pre-decision nominal
service resolution; atomic commit of the chosen complete profile; closed-loop arms BASE and BASE+C3-S each advancing their own trajectory;
panel 4 fresh derived worlds (`C3S_SCREEN/world/{1..4}` = 8464287092499831892, 7305539127129390835, 7691130988233444596,
5887834234954284271 — verified by recomputation; text-collision scan clean) × 3 E1 lineages, T = 30 steps, 100 users, 24 episodes; endpoint
pooled ratio-of-sums over 36 000 opportunities; single kill rule SUPPORT iff η_C3S > η_BASE and s ≥ s_BASE − 0.001; INVALID_RUN / INCOMPLETE;
claim ceiling `TRAIN_DEVELOPMENT_C3S_CLOSED_LOOP_KILL_SCREEN_NO_LEARNER_NO_EFFICACY_NO_TEST`.

Downstream (declared now, not authorised): SUPPORT → a confirmatory-grade plan `FULL2+C3-S vs FULL2` on the stage-C-style ladder; the owner's
"three positive contributions" = FULL2 vs DROP_C1, FULL2 vs DROP_C2 (two-Catfish ladder) and FULL2+C3-S vs FULL2. NO_SUPPORT closes this
constant/catalog/BASE/horizon configuration only.

Disclosure carried into the contract: S0 and oracle-marginal diagnostics (development evidence on the E1 anchors) were opened before this
declaration; the design is informed by them; the additive third head is closed at the oracle level for the tested targets/regimes.

## Addendum A accepted (07:45 UTC)
Second configuration C3-S(lite): BASE ∪ top-2 Q1+Q2 actions per user (BASE + runner-up, physically distinct, lowest-slot ties) ∪ full-origin evacuations; identical rule/η_ref/guard/ties/atomic execution; arms BASE, C3-S(full), C3-S(lite), 36 episodes; independent kill rule per arm; progression rule fixed now (both SUPPORT → lite proceeds, full reported; one → that one; none → family closed for this configuration). Timing reported, never a gate.

## Seal (controller, 2026-09-08 10:25 UTC)
Contract body sealed as v1: sha256 1b19e0f4c6c5f1591e3ca670da368fea0e785ec70fc51af5a9fe9edfdbfc7a7f. Scientific content final. The implementation is run as a VERTICAL SLICE now (owner principle: prove the whole path end to end before hardening); the outstanding astra R2 items are integrity plumbing (evaluator-input authentication, loader/census completeness, invalidation precedence, BASE timing, test realism) that do not change any number. Fix pass 2 continues in parallel; if the slice supports, the hardened v2 runner re-runs the screen for the record before the FULL2 ladder.
