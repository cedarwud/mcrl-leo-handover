# Amendment 11 to Ruling 2 — no absolute rate threshold; C-Q / C-RC re-specified on the project's own tail convention, or dropped

Date: 2026-09-12 (23:20 UTC 2026-09-11). **Controller decision**, answering the blocking question the
`CATFISH2-DISCOVERY` lane raised in `.scratch/catfish2-discovery/PROGRESS.md` "Finding 2". It changes no
Amendment 4, 5 or 10 gate. It is written **before any candidate outcome at any threshold exists** in that lane
(its own step log records step 6 running and step 7 pending), so no part of it can have been chosen from a result.

## 1. The lane's finding is upheld, and an absolute `R_min` is refused

The audit is correct and I have not found a counter-example to it:

- `docs/CONTROLLER-RULINGS-2026-08-22.md:52-54` (**C-2**) forbids introducing a target-SINR inversion, beam /
  satellite caps, PA clamps and min/max projections; the only live ceiling is the per-beam RF feasibility check
  `BEAM_POWER_MAX_W = 1.65 W` (`env/link_budget.py:175`), a **power** test, and it is already what decides `served`.
- `docs/CONTROLLER-RULINGS-2026-08-22.md:180` (**C-12**) puts `R^m = 1 Mbit/s` in the *Legacy provenance* column.
- `env/link_budget.py` carries no rate threshold and no ACM/MODCOD table; rate exists only as
  `shannon_rate_bps`. There is **no absolute rate constant anywhere in `src/`**.
- `RATE_TARGET_BPS = 50e6` lives only on unmerged `server/v025/*` branches, is not an ancestor of `05aadf1b`, and
  its own provenance audit calls it a **power-control setpoint with no delivered-rate or demand guarantee**.

**Decision: no absolute rate threshold may be declared — by this lane or any successor — without an owner
decision that explicitly reopens C-2.** The lane's second, design-level objection is adopted as a **standing
project constraint**: an absolute `R_min` used to gate actions against a predicted share is one algebraic step
from the inversion `γ_req = 2^(R^m·U/B^w) − 1` that PATCH P-22 deleted, so declaring one reopens a closed ruling
rather than setting a parameter. A candidate is not worth smuggling a demand model into a physics that has none;
a reviewer would find it, and would be right.

## 2. One prospective re-specification, using only quantities the project already defines

The project's existing rate-tail statistic is the **10th percentile**, present in every DEVVAL record as
`per_served_user_rate_p10_bps` and already used as a QoS floor in Amendment 4 and Amendment 10 (`p10 ≥ 0.5 ×`
the comparison arm). That convention — and nothing else — is what the two candidates may use. `r̂(a) =
(B_w/(n_a+1))·log2(1+γ_a)` keeps the definition the brief already fixed.

- **C-Q′-local** (deployable). At each step, for user `u`, let `q10^u(t)` be the 10th percentile of `r̂_u(a)` over
  that user's own masked candidate actions. Choose `argmax_a T0-score(a)` over `{a : r̂_u(a) ≥ q10^u(t)}`; if that
  set is empty, `argmax_a r̂_u(a)`. Uses only the user's own observation, so it is deployable as it stands.
- **C-Q′-global** (not deployable; must clone at `R_repr ≥ 0.5` to advance). Same rule with `q10(t)` = the 10th
  percentile of `r̂` over the users **T0's own joint action serves at that step** — the same reference assignment
  the lane already ported from `oracle_cells.py::best_response_step` for its QoS-invalidity definition. This is
  the form that matches C-Q's stated purpose (protect the weak user against consolidation overload), and it needs
  a cross-user order statistic to express it; the brief's existing clone screen is exactly the price for that.
- **C-RC′** (deployable). Among candidates with `r̂_u(a) ≥ q10^u(t)`, prefer one whose beam was already lit
  (`n_a > 0`), ties broken by `log2(1+γ_a)`; if no lit candidate qualifies, `argmax_a log2(1+γ_a)` over the
  qualifying set; if none qualifies, the unrestricted `argmax_a log2(1+γ_a)`. It uses the local tail only: its
  purpose — spend activation energy only when the throughput sacrifice is acceptable — is a per-user judgement.

No absolute rate, no target SINR, no inversion: `q10` is a same-step order statistic **of the very quantity being
compared**, and 10 % is the project's existing tail convention, not a new free parameter. Nothing here is tunable
without changing this document first.

**The two C-Q′ variants count as one candidate source, not two.** The deployable local form is primary; the
global form advances only if the local form fails and the global form clones at `R_repr ≥ 0.5`. If both pass,
one survivor slot is consumed and the deployable form is the one carried forward. This is stated now so that
running both cannot become a two-shot search.

## 3. Everything else in the brief is unchanged

The reference / control set, the T0 decomposition diagnostic, the five advancement conditions (deployable-or-
clones, non-dominated in (EE, served, p10) or clearly complementary with `p10 ≥ 1.10 × T0` and served ≥ 0.995 and
EE ≥ 0.95 × T0, disagreement ≥ 25 %, `CR = Σmax(Δ,0)/Σ|min(Δ,0)| ≥ 0.5` with candidate-better ≥ 0.30, and no QoS
collapse), the `CR` ranking with the 10 % p10 tie-break, **at most two survivors**, and "zero is a legitimate
answer" all stand exactly as committed at `bbaf5ea0`.

## 4. The escape hatch, which is a result and not a failure

If evaluating C-Q′ or C-RC′ still requires a number that is not already in the project, **both are DROPPED with
the reason recorded**, and Stage 0 reports zero prospectively-specified new candidates alongside the completed
controls, the T0 decomposition endpoints and the complementarity diagnostic. "This physics admits no rate-tail
specialist without importing a demand model the project has deliberately excluded" is a publishable sentence and
a better outcome than a fabricated threshold.

## 5. Provenance guard

`STAGE0-2026-09-12.md` must state explicitly that **no candidate outcome at any threshold had been computed** when
the lane received this amendment. `RHAT-INSTRUMENT.json` may report the *distribution* of `r̂` as characterisation;
it may not be used to pick a threshold — and under §2 there is no threshold left to pick.
