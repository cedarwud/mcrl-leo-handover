# V0.8 C2 clean-room — Stage 1b formula/oracle interaction screen contract

Date frozen: 2026-09-02 (before any oracle-screen outcome is opened)
Status: `PRE_OUTCOME_CONTRACT`
Claim ceiling: `FAIL_FAST_INTERACTION_SCREEN_ONLY__NO_EFFICACY__NO_TRAINING`

## 1. Candidate under test (H-A, deterministic hold-horizon segment-timing surplus)

For predecision anchor (world, step t, focal user u) and legal action a naming
physical pair (s_a, c_a), with horizon offsets k = 1, 2, 3 (H^c = 4), dt = 30.08 s:

- theta_a(t+k): off-axis angle of (s_a, c_a) toward u using SGP4 positions at t+k
  (`ScenarioDriver.satellite_ecef_at(k)`) and the current user ECEF.
- G_a(k) = transmit_gain_linear(theta_a(t+k)); start_a = the incumbent segment's
  start_transmit_gain if a continues the served (norad, cell), else G_a(0).
- p_a(k) = p0 * start_a / G_a(k), p0 = 0.825 W; infeasible if G_a(k) <= 0 or
  p_a(k) > 1.65 W; the hold is censored to zero rate and zero marginal power from
  the first infeasible offset onward.
- Frozen non-focal context from the committed previous step: n_a (non-focal users
  served on (s_a,c_a)), m_a (their max link power), sat_active_a. Step-0 anchors
  use an empty context and are flagged.
- R_a(k) = (B^w/(n_a+1)) log2(1 + p0*start_a*path_a(t+k)/(I_a+N)), path at the
  future slant/elevation of (u, s_a), unit fading/shadowing, I_a+N frozen at its
  decision-time value recovered from the observation gamma block.
- P_a(k) = Psup(max(m_a, p_a(k))) - Psup(m_a) + [n_a=0](0.338 + [sat inactive] 0.200),
  Psup(p) = p / xi(p) from the live link-budget functions.
- ZETA2*_a = sum_{k=1..3} dt [ R_a(k) - lambda0 * P_a(k) ]   (native bits)
- Q2*(s,a) = ZETA2*_a / kappa for legal a.  No learned scaling, no gauge shift,
  no clipping, no sign filter.

Frozen constants: lambda0 = 0x1.443a8f481639ap+26 bit/J (sealed TRAIN-only value,
`.scratch/c3-v04/run_v04_c3_source.py`), kappa = 0x1.2cea89d260f2ap+33 bits.
Q1, Q3: the sealed gate-selected V0.4 hybrids, initialization lineages
2026092101, 2026092102, 2026092103, Q3 rung 100, bytes unchanged.  The old
learned Q2 checkpoints are not loaded.

## 2. Frozen evaluation design

- Split: TRAIN only.  TEST is not opened.  No gradient, no replay write.
- Physical worlds: six fresh evaluation seeds 2026090221 .. 2026090226
  (verified unused in artifacts/, .scratch/, docs/ on 2026-09-02).
- Keyed fading field root: ("V08_C2_ORACLE_SCREEN_V1", evaluation_seed);
  initialization seed and policy label excluded, so every arm and lineage sees the
  identical physical world.
- Arms: P1 = Q1, P2 = Q2*, P3 = Q3, P12 = Q1+Q2*, P13 = Q1+Q3, P23 = Q2*+Q3,
  P123 = Q1+Q2*+Q3 (7 route arms x 3 lineages), MAIN (frozen Main, 1 row/world).
- Endpoint: pooled ratio-of-sums EE = sum(bits)/sum(energy) over rows; percentage
  contrast X vs Y = EE_X/EE_Y - 1.  Reported pooled over all rows and separately
  per initialization lineage.  Served fraction reported likewise.

## 3. Predeclared primary directions (fail-fast)

  D-C2: eta(P123) > eta(P13)     (C2 marginal in the frozen Q1+Q3 context)
  D-C3: eta(P123) > eta(P12)     (C3 marginal in the new-Q2 context)
  D-C1: eta(P123) > eta(P23)     (C1 marginal in the new-Q2 context)
  S:    pooled served fraction of P123 is not below that of P13, P12, and P23,
        and at least two of three lineage served-fraction contrasts are
        nonnegative for each pair (mirrors the V0.4 confirmatory guard item 5).

## 4. Predeclared decision

- `PASS_STAGE1B`: D-C2, D-C3, D-C1 all strictly positive pooled AND in 3/3
  lineages, and S passes.  Authorizes only Stage 1 step 3 (observability census,
  i.e. a deterministic-feature predictability check) and step 4 (small learner
  gate).  No episode training.
- `C2_DIRECTION_FAIL`: D-C2 non-positive pooled, or non-positive in >= 2/3
  lineages.  H-A as formulated STOPS.  No rescaling, horizon, threshold, seed, or
  context change may rescue it.  The next admissible step is a fresh census for
  H-C (energy/cliff-only subset) or H-B (dwell-boundary window control).
- `C2_MIXED`: D-C2 positive pooled and in exactly 2/3 lineages.  REVISE: no
  promotion; the only admissible follow-up is a larger fresh block with the
  identical formula.
- `C3_CONTEXT_FAIL` / `C1_CONTEXT_FAIL`: D-C2 passes but D-C3 (or D-C1) fails.
  Record `C3_CONTEXT_DEPENDENT` (or `C1_...`).  C1/C3 are not altered by this
  document; the finding is escalated to the user as a method-level blocker.
- `INVALID_RUN`: authentication, non-finite value, hybrid tensor change, replay
  write, TEST opening, or broken world pairing.

## 5. Diagnostics (reported, never decisional)

All remaining lattice contrasts, per-world paired contrasts and sign counts,
hold fraction and infeasible-hold counts per arm, energy and bits separately,
paired-world bootstrap of the three primary contrasts (2000 replicates, seed
2026090299).  No scale-sensitivity variants are run in this screen.

## 6. Compute routing

Projected 132 ten-step episodes.  Non-heavy if the smoke projects <= 30 min on
the local machine; otherwise route to the Ubuntu server with this contract's
SHA-256 embedded in the result.
