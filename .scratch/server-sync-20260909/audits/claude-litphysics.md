Read papers and answer three questions about whether a project's physics and its measurement conventions match the field. The PDFs are in `/home/sat/litref-20260910/`. Workspace: the current directory; write your report here. Do not modify `/home/sat/mcrl-leo-handover` or its virtual environment.

`DIAGNOSTIC_NOT_CLAIM`. No code, no run. This is a reading task with a verdict.

Read at minimum, in full where they bear on the questions:
- `2023_09_Downlink_Analysis_of_LEO_Multi-Beam_Satellite_Communication_in_Shadowed_Rician_Channels.pdf`
- `2022_11_Analysis_of_SINR_according_to_Elevation_Angle_in_Earth_Fixed_Beam.pdf`
- `2022_04_Reliable_and_Energy-Efficient_LEO_Satellite_Commun.pdf`
- `2017_07_Energy-Efficient_Beam_Coordination_Strategies_With_Rate-Dependent_Processing_Power.pdf`
- `2024_09_Energy-Efficient_Joint_Handover_and_Beam_Switching_Scheme_for_Multi-LEO_Networks.pdf`
- `2026_01_Resource_Allocation_in_Multibeam_LEO_Satellite_Systems_Based_on_Beam_Hopping_and_Frequency_Reuse.pdf`
- `2025_07_Energy-Efficiency-Based_Joint_Uplink_Resources_Allocation_for_LEO_Satellite_Beam-Hopping_System.pdf`
Skim the rest of the directory for anything bearing on the questions and say what you used.

## The project's construction, stated neutrally so you can compare it
Ka-band LEO, multi-beam, frequency reuse 3, per-beam bandwidth 166.67 MHz. Each beam's members share airtime equally, so a beam with `n` users requires spectral efficiency `n × 50 Mbit/s / 166.67 MHz` per user while on air. A discrete modulation-and-coding table (EN 302 307-1) with a 1.7 dB receiver implementation margin already folded into every threshold supplies the mode. The channel has Rician fading times lognormal shadowing times scintillation; the tenth-percentile multiplier of that product is about 0.51 at 30 degrees elevation. Transmit power is solved so the **nominal** signal-to-noise ratio equals the selected mode's threshold exactly; the mode actually transmitted is then chosen from that same ratio **after** multiplying by the tenth-percentile multiplier. Per-beam radiated power is capped at 1.65 W. Amplifier supply power is the square root of radiated times saturation power, divided by 0.35; each radiating chain costs 0.338 W and each active satellite 0.200 W.

## Q1 — Fade margin: is provisioning to the nominal threshold defensible?
Determine from the papers how transmit power is set relative to a decoding threshold when the channel fades.
- Does the field provision to the nominal threshold, or to the threshold plus a link margin, or to a threshold evaluated at an outage percentile?
- What availability or outage probability is conventional for Ka-band LEO, and what margin in decibels does that correspond to in these papers?
- Is applying a fade quantile at mode selection while provisioning power at the nominal value a construction that appears anywhere? If not, say so plainly.
- Is the 1.7 dB implementation margin the same kind of quantity as a fade margin, or a different one?
State whether the project's construction is a recognised design, an unusual one, or an error, and give the evidence.

## Q2 — Metric conventions
- Is pooled energy efficiency — summed bits over summed joules — the field's convention, or is a per-user or summed-per-user quantity used? What do the papers say about the difference?
- When a discrete mode delivers **more** than the user's contracted rate, does the field credit the delivered capacity or only the contracted rate? Find explicit statements.
- How is a user that cannot meet its rate target treated — outage and excluded, admission-controlled and never admitted, or served at a degraded rate and still counted?
- Do papers report rate-target attainment separately from "has a connection"? Give examples of how service is defined.
- Is amplifier supply power modelled as a square-root law elsewhere, and is a fixed per-chain cost standard?

## Q3 — The closest prior art
For each of the three energy-efficiency papers above, state in a few lines: its setting, its decision variables, its objective, its baselines, its reported gains and against what. Then answer: **what, precisely, would be left as new if a project modelled joint handover decisions with occupancy-dependent power control and a discrete mode table, and reported pooled energy efficiency?** Be specific about what is already covered and what is not. If the honest answer is that very little is left, say that.

## Output
Write `LIT-PHYSICS-CONVENTIONS-2026-09-10.md` and print it in full as your final message. Lead with three one-line answers, one per question. Cite paper and section for every substantive claim. Where the corpus does not answer a question, say so rather than generalising. Do not soften a negative finding.
