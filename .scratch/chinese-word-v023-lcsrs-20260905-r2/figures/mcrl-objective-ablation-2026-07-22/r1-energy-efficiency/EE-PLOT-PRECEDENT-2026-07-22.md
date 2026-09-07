# EE plot precedent and project fit

This note is a local-paper scan used to choose the supplementary five-line EE
ablation axes in this directory. It does not turn the derived `ep1700`
composites into matched parameter-sweep claims.

| Local paper | EE-result axes used in the paper | Consequence for this project |
|---|---|---|
| `ee/Energy-Efficient_Joint_Handover_and_Beam_Switching_Scheme_for_Multi-LEO_Networks.pdf` | Time-frame size and user density; EE is plotted with 3--6 methods (Figs. 6--7). | `num_users` is directly conventional. A time-window sweep would require a separately justified experiment. |
| `ee/Energy-Efficiency-Based_Joint_Uplink_Resources_Allocation_for_LEO_Satellite_Beam-Hopping_System.pdf` | Maximum transmit power, traffic-demand scale, terminal-bias parameter, positioning/SINR error, and iterations (Figs. 10--16). | `p_base` is the closest available power-budget axis. Bandwidth and noise are directly interpretable link-budget axes. `p_exp` is a clearly labelled hardware/load-model sensitivity, not a tuning recommendation. |
| `ee/Energy-Efficient_Beam_Coordination_Strategies_With_Rate-Dependent_Processing_Power.pdf` | Rate-dependent processing-power parameter, number of transmit antennas, iteration budget, and pilot resources (Figs. 3, 5, 6, 9). | `k_cap` belongs to the conventional resource-capacity family; `p_exp` is analogous to a power-model sensitivity. |
| `ee/Reliable_and_Energy-Efficient_LEO_Satellite_Communications_With_IR-HARQ.pdf` | Outage target, transmission rate, HARQ rounds, and Rician factor (Figs. 6--10). | Parameter-sweep lines are normal for EE, but the x-axis must be a real, varying mechanism. |
| Sun2024 MODQN source paper | Number of users, number of satellites, user speed, and satellite speed. | Use the users panel. Do not copy the speed panels: the present 10-step evaluator makes user speed metric-inert, and satellite speed is not a valid free parameter in the frozen environment. |

## Figures retained here

1. EE versus number of users -- load/system scale.
2. EE versus transmit power -- power budget.
3. EE versus per-beam power cap $P_{max}$ -- physical power ceiling; the source
   shows a low-cap knee followed by a plateau.
4. EE versus active-beam capacity $v_{max}$ -- resource capacity; the feasible
   displayed range begins at $v_{max}=3$.
5. EE versus system bandwidth -- available spectral resource.
6. EE versus noise PSD -- receiver/channel-noise stress.
7. EE versus users per active beam -- controlled physical load mechanism; it is
   separately disclosed because the source is not a policy-level sweep.

All use the same five displayed ablation lines, measured-point style, a compact
top legend, no smoothing, and no confidence band. The corresponding CSV keeps
all six derived seed values and the plotted mean at each point.

The beam-load panel is based on the completed three-episode controlled probe,
which fixes the beam, target user, geometry, and fading while changing only the
number of sharing users. It stops at 16 users per active beam, and shows only
integer load values: 1--8 plus 10, 12, 14, and 16. The non-measured integer
display points are linear interpolations between its completed measurements. It
is a mechanism diagnostic, not evidence that the five policies were separately
re-evaluated at every load.

`P_base` is a fixed active-beam power floor. `P_max` is the ceiling that clips
the load-dependent term, and is retained as a separate power-cap panel even
though it plateaus after the low-cap knee. `alpha`, the exponent in
`P_base + P_scale * load^alpha`, remains a hardware/load-model sensitivity, not
a directly interpretable system-condition panel.

## Axes deliberately omitted

- **User speed:** the completed curve is featureless under a 10-step episode;
  describing that limitation is clearer than publishing a flat line.
- **Constellation size:** values below 180 are infeasible for the evaluator's
  four-satellite window requirement, leaving only a one-sided, non-comparable
  sweep. It is unsuitable as a balanced main panel.
- **Satellite speed:** orbital velocity is fixed by altitude in the frozen
  environment, so a speed sweep would not be physically well-defined.
- **Peak transmit cap $P_{max}$:** it is an available sweep, but the observed
  response is almost flat beyond the low-cap knee. The panel would not earn its
  space beside the clearer bandwidth and noise sensitivity plots.
- **Beam-load exponent $alpha$:** it is a power-model assumption, not a direct
  scenario condition. Explaining it requires the full nonlinear power equation,
  so it is deliberately excluded from the primary five-axis figure set.
