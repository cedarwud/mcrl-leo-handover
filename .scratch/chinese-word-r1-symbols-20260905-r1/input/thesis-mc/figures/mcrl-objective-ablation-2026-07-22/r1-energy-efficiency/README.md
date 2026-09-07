# ep1700 Full-MCRL EE ablation diagnostic

The primary requested assets are five-line EE ablation charts at the selected
`ep 1700` checkpoint. The first two show EE versus number of users and
per-beam base power; four literature-aligned sensitivity panels add per-beam
power cap, per-satellite beam capacity, bandwidth, and noise PSD. A seventh,
separately disclosed mechanism panel uses users per active beam. The charts
show only five mean curves: no confidence band, error bar, seed scatter, bar
chart, or smoothing.

Its displayed arms are the Full-MCRL leave-one-strategy-out ablation:

1. MODQN (raw, no Z-score);
2. MCRL w/o experience shaping;
3. MCRL w/o reward shaping;
4. MCRL w/o penalty shaping;
5. MCRL.

All four MCRL-family curves use the Z-score substrate. The display labels omit
that repeated detail; only the raw baseline is unnormalized. Full MCRL is
higher than every ablation at every displayed point.

The requested five-line parameter figures for the post-hoc
`ep-01700.pt` checkpoint are:

- EE versus number of users;
- EE versus per-beam base power $P_{\mathrm{base}}$;
- EE versus per-beam power cap $P_{max}$;
- EE versus active-beam capacity $v_{max}$, beginning at the feasible minimum
  of three beams per satellite;
- EE versus system bandwidth;
- EE versus receiver noise power spectral density (PSD).
- EE versus users per active beam (controlled load-mechanism diagnostic).

Each figure is a derived composite assembled per seed from completed
measurements: its anchor is the arm's observed ep1700 EE; its curve shape is
the observed positive sensitivity ratio around the axis-specific nominal setting
(`U=100`, `P_base=0.25 W`, `v_max=3`, `B=500 MHz`, or `N_0=-174 dBm/Hz`).
The raw baseline
sensitivity shape comes from the completed raw L1 sweep. The plotted arm order
is:

1. baseline MODQN (L1; raw, no Z-score);
2. w/o experience shaping (Full minus the observed L3−L2 experience increment);
3. w/o reward shaping (L8; Full without ACRM);
4. w/o penalty shaping (L4; experience plus reward shaping, without capacity penalty);
5. full MCRL (L6; experience, reward, and penalty shaping).

The CSVs retain exactly the five plotted means at every point, so importing a
CSV into OriginLab reproduces the PNG without extra curves. This is not a new
matched parameter-sweep result; the manifest records the exact source files,
anchor, and construction rule.

Every panel transfers a **positive normalized scenario ratio** around its
nominal point to the observed ep1700 arm anchor. This preserves the measured
scenario shape without producing impossible negative EE. For bandwidth and
noise specifically, the available corrected-EE source sweep retains only method
means, not the six ladder arms; those two panels remain derived visual
diagnostics rather than six-seed matched sweeps.

The noise panel deliberately shows only `-180` through `-160 dBm/Hz`: at
noisier values every method collapses toward zero EE, concealing the meaningful
ablation separation. Its displayed 2 dB points are linear interpolations of the
completed 4 dB source shape and carry the CSV status
`derived_composite_interpolated_noise`; they are presentation points, not new
measurements.

The bandwidth panel uses MHz (`bandwidth_mhz` in its CSV) rather than scientific
notation, while the manifest retains the source-side nominal value in Hz.

The power-cap panel uses the completed corrected-EE KC1 mean scenario shape,
normalized at the nominal 10 W cap and applied to the ep1700 anchors. Like the
bandwidth and noise panels, its source retains method means rather than the
current ladder arms' per-seed sweep values. It retains the measured low-cap knee
and subsequent plateau rather than manufacturing a stronger trend; its CSV
status is `derived_composite_legacy_power_cap_shape`.

The beam-load panel is the one exception to the policy-sweep construction. It
uses the completed controlled probe that holds a beam, user, geometry, and
fading fixed while varying only the number of users sharing that beam across
three episode contexts. Its mean positive shape is normalized at eight users per
active beam and transferred to the ep1700 anchors. The displayed domain stops at
16 users per active beam, with integer loads 1--8 plus 10, 12, 14, and 16;
non-measured integer display points are linear interpolations between completed
controlled measurements. The CSV status is
`derived_composite_interpolated_controlled_load_mechanism`. It demonstrates the
physical EE load mechanism, not a new five-arm policy evaluation.

Power terminology is intentionally separated. `P_base` is the fixed active-beam
power floor. `P_max` is the per-beam ceiling, shown separately because it has a
measured low-cap knee followed by a plateau. The beam-load exponent `alpha`
controls the curvature of `P_base + P_scale * load^alpha` before that cap
applies; it remains an implementation-level power-model assumption rather than
a direct system condition and is not drawn as a separate panel.

Scope boundary: `ep1700` was selected after the trajectory was observed. These
assets are therefore derived visual diagnostics only; they are not Chapter 5
endpoint figures and do not establish a durable benefit claim. The renderer
follows the CDRL thesis result-chart grammar: measured-point lines, a compact
top legend, and no smoothing or confidence band.

`user_speed_kmh` is deliberately not plotted: its completed sweep is flat
because a 10-step episode is too short for user mobility to materially change
the measurement. The source-side handoff records that limitation; a sentence in
the thesis is more informative than a featureless chart.
