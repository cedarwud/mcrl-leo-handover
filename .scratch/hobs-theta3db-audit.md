# HOBS / Chen `theta_3dB` audit (2026-08-26)

## Scope and primary sources

The primary HOBS paper is Chen, Shen, Feng, Yang, and Wu, “Energy-Efficient Joint Handover and Beam Switching Scheme for Multi-LEO Networks,” *2024 IEEE VTC-Spring*, DOI [10.1109/VTC2024-Spring62846.2024.10683088](https://doi.org/10.1109/VTC2024-Spring62846.2024.10683088), [publisher PDF](https://ieeevtc.org/vtc2024spring/DATA/PID2024002205.pdf). The local copy audited is `/home/u24/papers/all-papers-pdf/Energy-Efficient_Joint_Handover_and_Beam_Switching_Scheme_for_Multi-LEO_Networks.pdf` (7 PDF pages).

Chen et al. cite Sharma, Chatzinotas, and Ottersten [16]. The authors' expanded primary article is available as the [author preprint](https://orbilu.uni.lu/bitstream/10993/16849/1/Jsatbeamhop.pdf), DOI [10.1002/sat.1073](https://doi.org/10.1002/sat.1073).

## Source evidence

* Chen PDF p. 2, Eq. (3), defines the Bessel pattern
  `G(theta) = G0 [J1(mu)/(2 mu) + 36 J3(mu)/mu^3]^2`, calls `theta` the boresight angle, and sets `mu(theta) = 2.07123 sin(theta) / sin(theta_3dB)`. The following sentence calls `theta_3dB` the antenna's “3 dB half-power beamwidth angle.” The equation has no factor of two and no `+/-` edge convention.
* Chen PDF p. 6, Table I, independently lists: `M = 37`, `LEO altitude = 550 km`, `LEO serving radius = 500 km`, and `3dB beamwidth theta_3dB = 0.058 rad`. These four tabulated values are source facts; the table does not give a cell radius or a derivation tying the four values together. Section V (same page) says users are uniformly distributed within the service coverage of all LEOs, but does not define a beam-cell tiling.
* Sharma et al. expanded article PDF p. 10, Eq. (15), defines the 3-dB angle as `theta_3dB = atan(r/D)`, where `r` is the **radius** corresponding to the 3-dB beamwidth and `D` is satellite height from the beam centre. Its PDF p. 11, Sec. 6.2, says the cell radius is obtained by accommodating the number of beams in the coverage area. This is direct primary-source support that the parameter in the cited pattern is a centre-to-edge (one-sided) angle, despite the authors' use of “beamwidth.”

## Numerical half-power check

Let `A(u) = J1(u)/(2u) + 36 J3(u)/u^3`. Using the limiting value `A(0)=1` and the constant in Chen Eq. (3):

```
u = 2.07123
A(u)       = 0.7071070699213712
A(u)^2     = 0.5000004083327869
10 log10 A(u)^2 = -3.0102964099 dB
```

At `theta = theta_3dB`, Chen's `mu(theta)` is exactly `2.07123`; hence `theta_3dB` is the one-sided off-axis half-power angle in the implemented equation. Therefore the raw Table-I value is `0.058 rad = 3.323155 deg` one-sided, and the corresponding symmetric full HPBW is `2(0.058) = 0.116 rad = 6.646310 deg`. Calling the raw `0.058 rad` a *full* HPBW would silently halve the physical beam radius.

For the stated 550-km altitude, a nadir tangent projection gives:

```
one-sided half-power ground radius = 550 tan(0.058)       = 31.9358 km
full half-power diameter           = 2*31.9358             = 63.8716 km
if 0.058 were (incorrectly) full HPBW: radius = 550 tan(.029) = 15.9545 km
```

As a diagnostic only (not a source claim), 37 non-overlapping equal half-power disks of radius 31.9358 km have total area 118,551.7 km^2, versus `pi*500^2 = 785,398.2 km^2` for a 500-km service-radius disk: 15.09% of that area, or an equal-area radius of 194.26 km. The simple disk ratio would require about 245 such beams before overlap/edge margins. If 0.058 were treated as full HPBW, the corresponding figures are 3.77%, 97.05-km equal-area radius, and about 982 disks. Because Chen never says that the 500-km serving radius is a half-power footprint nor supplies a tiling, this is an internal-consistency warning, not proof that the simulation is impossible.

## Sentence-by-sentence claim verdict

The following expanded sentences cover the quoted interpretation under review; “correct” distinguishes a literal source fact from an equation-implied result.

| Sentence | Verdict | Basis |
|---|---|---|
| “Chen et al. Table I uses 37 beams, 550 km altitude, 500 km LEO serving radius, and `theta_3dB = 0.058 rad`.” | **Correct** | Chen PDF p. 6, Table I (all four rows). |
| “Chen calls `theta_3dB` the 3-dB half-power beamwidth angle.” | **Correct (literal wording)** | Chen PDF p. 2, immediately after Eq. (3). The wording itself does not state full versus one-sided. |
| “In Chen Eq. (3), `0.058 rad` is the one-sided off-axis angle at which the gain is −3 dB; the symmetric full HPBW is `0.116 rad`.” | **Correct (equation-implied)** | Substitution into `mu = 2.07123 sin(theta)/sin(theta_3dB)` and the half-power check above; corroborated by Sharma Eq. (15)'s `theta_3dB = atan(r/D)` with `r` a 3-dB radius. This is not an explicit `+/-` sentence in Chen. |
| “HOBS/Chen explicitly defines `0.058 rad` as the full HPBW, so the pattern should receive `theta_3dB/2 = 0.029 rad`.” | **Incorrect as a source/equation claim** | Chen's equation receives `theta_3dB` in the denominator; using `/2` is a project reparameterization, not Chen's raw convention. It is physically equivalent only if the project stores `0.116 rad` (6.646 deg) as the new full width. |
| “At 550 km, the 0.058-rad HOBS beam has a 15.95-km half-power radius.” | **Incorrect for Chen Eq. (3)** | 15.95 km follows from incorrectly treating 0.058 as full width. The equation-implied one-sided radius is 31.94 km. |
| “The 37 beams cover a 500-km service-radius footprint/cell set.” | **Unsupported** | Table I lists `M=37` and `LEO serving radius=500 km` separately; no cell radius, grid, overlap rule, or coverage derivation is supplied. The equal-area check is strongly inconsistent with a 500-km half-power disk, but does not prove what the authors intended. |
| “The source explicitly states `+/-theta_3dB/2` beam edges.” | **Unsupported** | Chen p. 2 has no `+/-` edge statement. The one-sided reading follows from the formula and Sharma's radius definition, not that quoted sentence. |

## Bottom line

The defensible source-faithful statement is: **HOBS Table I records `0.058 rad`; in the cited Bessel equation that numeric parameter is the centre-to-3-dB-radius angle (one-sided), so it corresponds to a 0.116-rad (6.646-deg) full HPBW.** A project may store the equivalent full width as 6.646 deg and pass half of it to the pattern, but must label that as a reparameterization/adaptation rather than claiming Chen Table I itself reports a full HPBW. A project that instead stores 3.32 deg as the full width and passes 1.66 deg to the pattern implements a beam half as wide as Chen's equation-implied beam. The 37/550-km/500-km triple is a simulation parameter bundle with no source-provided beam-cell derivation.
