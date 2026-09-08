# Addendum B — V-E expected configuration scoring (DRAFT, do not seal)

Status: pre-outcome draft dated 2026-09-08. This document does not authorize execution.
It supplements, but does not alter, the sealed nine-arm variant-matrix contract.

## Definition

V-E is a separately opt-in tenth trajectory: `BASE` plus the unchanged C3-S(lite)
catalog, unchanged deterministic nominal service guard, exact tie order, atomic commit,
physics, horizon, TRAIN panel, and information-isolation rules. `ALL_NEUTRAL_CONTROL`
retains that name and is never relabelled `BASELINE`.

Only the ranking score changes. For complete candidate configuration `x`, V-E uses

`F_E,t(x) = K^-1 sum_k [B_hat_t,k(x) - eta_ref E_hat_t,k(x)]`.

The service guard remains the lite rule
`C_hat_t(x) >= C_hat_t(b_t)` under the deterministic nominal convention. It is not
redefined as an average or chance constraint. The realised committed configuration is
evaluated once by the unchanged screen environment and its keyed world fading field.

`K = 4` is fixed by declaration. Provenance: four is the smallest even count providing
a two-sided spread while capping stochastic scoring at four times the lite candidate
scoring pass. K must not be changed after any result exposure.

## Scenario authority and common random numbers

The fixed domains are `C3S_VE/scenario/{1..4}`. Each seed is derived once by the
repository world-seed rule:

`int.from_bytes(sha256(domain.encode("ascii")).digest()[:8], "big") & ((1<<63)-1)`.

Provenance: the first eight SHA-256 bytes and signed-int63 mask are the existing
project world-seed convention, not values chosen from outcomes. Scenario seeds do not
include a world, lineage, candidate, step result, or realised field identifier.

Each seed roots a fresh canonical keyed fading field. Its event, step, NORAD, and stable
user axes apply the same Rician and elevation-dependent shadowing draw to every candidate
path at a decision. Thus candidates use common random numbers even when their active
satellite sets differ. Inputs are only the simulator's declared Rician K-factor and
shadowing distribution; the world's realised keyed field is never visible to selection.

Cost planning is approximately four stochastic physical evaluations per distinct lite
candidate, plus the existing deterministic nominal work needed for catalog construction
and the unchanged service guard. Report both counts and end-to-end latency; no timeout,
pruning, or outcome-dependent reduction of K is permitted.

## Panel, kill rule, and multiplicity

V-E uses the same four worlds, three frozen lineages, users, horizon, and matched initial
state construction as the sealed matrix. These are reused TRAIN clusters, not fresh
confirmatory evidence.

Its sole endpoint rule is identical:

`SUPPORT iff eta_V-E > eta_BASE and s_V-E >= s_BASE - 0.001`.

Provenance: `0.001` is inherited unchanged from the sealed variant-matrix service rule;
it is not tuned for V-E. Use exact pooled ratio-of-sums accounting and report every
failure reason. SUPPORT gives planning eligibility only; it is not efficacy.

V-E is a tenth arm added pre-outcome, producing a ninth coordinator-versus-BASE contrast.
The nine-arm results MUST NOT be consulted before the V-E launch authority is built.
The controller must record (a) V-E declaration timestamp, (b) launch-authority timestamp,
and (c) timestamp and identity of any exposure to nine-arm results. If exposure precedes
authority, V-E must be disclosed as a separately timestamped second development screen,
not as part of the original prespecified matrix. No multiplicity correction is claimed.

The runner keeps V-E disabled in config and absent from default `ARMS`. Execution requires
the explicit `--enable-ve` flag, which must be bound verbatim by the launch authority and
must use a separate output root from the sealed nine-arm run.

## Required reporting

- Config projection digest proving the sealed nine-arm constants and default panel stayed unchanged.
- Addendum/config/code/authority digests and all exposure timestamps.
- K, scenario domains, derived seeds, keyed-field convention, and distribution constants used.
- Per-step catalog size, distinct nominal evaluations, synthetic scenario evaluations, and aliases.
- Selected and BASE expected scores, nominal served counts, overrides, fallbacks, and guard rejections.
- Mean, median, p95, maximum total latency, deadline exceedances, phase timings, and peak RSS.
- Pooled and per-world/per-lineage bits, joules, EE, service, action changes, and cumulative curves.
- Nominal-versus-realised paired gains and all previously required variant-matrix diagnostics.
- The unchanged kill disposition, every failure reason, and the development-only claim ceiling.

No TEST split, learner update, realised-information selection, result-conditioned redesign,
seed search, K search, rerun selection, or confirmatory claim is authorized.
