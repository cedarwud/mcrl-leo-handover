# Fable Max SMC-ER v0.4 delta review

Date: 2026-08-27

## Reviewed object

- `docs/MULTI-CATFISH-PAPER-ALGORITHM-V0.4-2026-08-27.md`
- Verified SHA-256:
  `174f29a65384cd470a4e974c23bad3034269283e510b7088960fa76b29f282b8`
- Model: Claude Fable 5
- Effort: max
- CLI session: `4c13d2a3-063e-4963-b8e0-d27ae4f59241`
- Review mode: read-only, scoped delta against the v0.3 Fable and Sol receipts

## Verdict

`PASS_TO_STAGE0_SPECS`

The reviewer found no blocking defect and judged all seven v0.3 blockers
closed:

1. C1 behavior, frozen EXP generator, and separated EXP/ACRM controls;
2. Bellman-complete C2/C3 augmented option state and physical-ID continuation;
3. atomic `U x 3` bundle credit, focal private updates, and no duplicate Main
   routing;
4. C2 random/stay controls with post-release and episode-total accounting;
5. C3 pre-implementation shadow authority and separate ranking/certificate
   controls;
6. deterministic path fixtures and correct independent-arm matching language;
7. frozen directional short-screen rules and claim ceiling.

The review found no new contradiction, hidden outcome-oracle leakage,
infeasible control, or empirical claim above the available evidence.

## Items to freeze in the Stage-0 specifications

- Describe C2 as reducing cumulative canonical R2 **penalty** and use
  `Delta_R2 = sum(r2_C2-PRE) - sum(r2_control)` as the only sign convention.
- Use the single term `first post-release interval`.
- Name the exact `C2-STAY` fallback action.
- Freeze whether post-selection C2 paired forks are deterministic fading-off
  or common-RNG stochastic, identically for treatment and controls.
- Later, before a learning pilot, define whether removal of a role symmetrically
  shrinks both `ALL-I` and `ALL-R`.

## Authority boundary

This verdict authorizes only writing sealed, non-training C2/C3 Stage-0 role
gate specifications before revealing new seeds. It does not authorize Catfish
implementation, C3 code, Main transfer, carrier smoke, training, an
effectiveness claim, or a G-6 change. A C3 shadow pass still needs a separate
explicit implementation ruling.
