# C1 pre-transfer representation and atomic-bundle consumer gate V1

Date: 2026-08-28  
Status: candidate implementation contract; deterministic and seedless

## Question and boundary

This gate asks whether the unchanged scalarized Main learner can consume one
complete, unshaped C1 environment bundle without observing or leaking C1's
private ACRM reward, generator label, trigger metadata, or provenance.  It is
an implementation/representation gate before transfer.  It does not train a
persistent Main policy, compare held-out EE, or authorize any C2/C3 route.

The previously named four-episode C1 "consumer gate" is outside this gate and
must be treated only as a post-gate developmental carrier-efficacy
micro-screen.

## Frozen authorities

- the corrected scalarized Main checkpoint and its embedded configuration;
- the independently verified immutable C1 EXP/control corpus;
- an exact zero-dose parity v3 receipt that hash-binds the baseline training
  state, all-shadow carrier state, both complete run-status receipts, parity
  checker, and current short-EP runner.  Both status receipts must bind the
  same canonical sealed preregistration and the same exact 373-file TLE
  archive, and the validator must reproduce that ephemeris authority;
- the production atomic updater, durable consumed-bundle ledger, this runner,
  its tests, the corpus loader, and the active multi-Catfish method.

The independent validator reloads both bound state artifacts and run-status
receipts, reproduces the sealed preregistration/TLE contract, and recomputes
the exact parity comparison; a self-attested `PASS` JSON is insufficient.
No new training, environment, mobility, or evaluation seed is used.  All
fixtures are deterministic transformations of already sealed corpus bundles
and immutable Main clones.  The persistent Main checkpoint is never changed.

## Required fixtures

1. **Representation/private-signal alias.** Two C1 bundles have byte-identical
   canonical state, mask, action, natural `U x 3` reward, successor, and done
   surfaces, but opposite/extreme C1-private rewards and different hidden
   trigger/provenance labels.  Main losses, gradients, parameters, targets,
   optimizer state, and RNG must remain identical.
2. **Independent atomic reference.** Starting from equal immutable Main
   clones, compare the production source-quota updater against a separately
   implemented reference that gives the Main bundle and C1 bundle total weight
   one each and averages admissible rows within each bundle.  The loss is the
   canonical Main mean-squared TD loss; this gate does not change the MODQN
   loss family.  FP32 numeric comparisons use `rtol=1e-6`, `atol=1e-7`; IDs,
   masks, counts, targets, RNG lineage, and structural state are exact.
3. **One-row perturbation.** Change one admissible C1 row at a time in a
   deterministic fixture.  The delta of the trusted focal-row gradient and
   the delta of the complete-bundle gradient must have nonnegative inner
   product for every objective, and the executed-action versus frozen-Main
   comparator preference must not reverse direction between focal and atomic
   updates.
4. **Atomic accounting.** Every admissible row appears exactly once, every
   bundle has total weight one, invalid/no-op rows receive no hidden weight,
   and row permutation cannot materially change the result.
5. **Durable at-most-once routing.** A specialist bundle ID admitted once must
   be rejected on the next call and after save/load of the consumed-ID ledger.

Any missing informative fixture, private-reward leakage, reference mismatch,
credit/preference reversal, duplicate acceptance, authority drift, or failed
zero-dose prerequisite returns `SHADOW`.

## Claim ceiling

A pass means only: `C1` atomic transfer is mechanically representable for the
exact bound Main/checkpoint/configuration and runner revision.  It permits the
separately seeded four-episode developmental efficacy micro-screen.  It is not
EE benefit, stability, convergence, generalization, Chapter 5 evidence, or a
C2/C3 ruling.
