# Ambiguities in the declared physics

This ledger is populated from the named documents before comparing with the
environment.  The reference implementation follows the literal choice stated
after each ambiguity.

1. **S.465-6 near-axis domain.**  Thesis eq. (3.10c) and
   `LINK-BUDGET-NOTES.md` extend `32 - 25 log10(theta_deg)` below the
   recommendation's `theta_min`, clipping only at the separately sourced
   35 dBi terminal maximum.  S.465-6 itself does not define the reference
   envelope below `theta_min`.  The reference follows the thesis extension,
   but computes `theta_min` using the recommendation's actual branch:
   `max(1 deg, 100 lambda/D)` for `D/lambda >= 50`, otherwise
   `max(2 deg, 114(D/lambda)^-1.09)`.  The local docstring instead applies
   the first branch to a 0.6 m, 20 GHz terminal whose `D/lambda` is about 40.
2. **Wanted power versus beam radiation.**  Eq. (3.13) uses link power in the
   wanted numerator although eqs. (3.12a-b) say an active beam radiates one
   `max`-aggregated power.  The reference preserves the written asymmetry.
3. **Shadowing sign.**  `L_s` is named a loss but is a zero-mean dB Gaussian,
   hence negative draws are gains and its linear mean exceeds one.  The
   reference adds the signed dB draw to loss exactly as documented and does
   not mean-normalise it.
4. **Rician draw identity.**  The documents specify a unit-mean Rician power
   gain but do not freeze the normal-draw ordering.  Differential replay takes
   the environment's realised per-path gain as an input; standalone sampling
   uses two independent standard normals per element.
5. **All-dark pooled EE.**  Notes define an individual all-dark 0/0 step as
   zero, while pooled ratio-of-sums is undefined if every step is all-dark.
   The reference returns zero only when both pooled bits and energy are zero;
   positive bits with zero energy fails closed.
6. **Target replay state sufficiency.**  The sealed C1/C2 rows retain derived
   per-user rates and system/marginal powers, but not ECEF geometry, active
   beam geometry, shadow draws, or Rician draws.  The target equations can be
   independently rebuilt exactly from the retained observables, but the link
   budget cannot be rerun from those rows alone.  The replay therefore treats
   those retained physical observables as inputs and reports this limitation.
7. **What is the “declared C3” after the successor decision?**  The final
   successor declaration explicitly removes C3, while earlier frozen V0.23
   documents define C3 as LC-SRS pair interaction and a later contingency
   ladder defines different cost-shared/energy targets.  The comparison uses
   the last frozen LC-SRS definition and separately records that it is absent
   from the final successor learner.
8. **The two historical SINR medians are not one paired experiment.**  W17's
   16.4 dB and W27's 6.60 dB came from different probe panels and sampling
   descriptions.  The audit may identify interference as the mechanism and
   measure its paired penalty on fresh traces, but cannot causally decompose
   the literal 9.8 dB difference between unpaired medians.
