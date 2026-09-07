# Build the efficiency–equity 2×2 in OriginLab

4 panel CSVs (already scaled to clean units; column order = legend order, MCCRL first,
MODQN last). Same 8-column structure in every file → one styled template restyles all 4.

| CSV | panel position | X (scale) | Y title |
| :-- | :-- | :-- | :-- |
| `panel_ee_vs_bandwidth.csv`        | top-left  | Bandwidth_MHz (**Log10**) | Energy efficiency (×10¹² bits/Hz/Joule) |
| `panel_ee_vs_noise.csv`            | top-right | NoisePSD_dBmHz (linear)   | Energy efficiency (×10¹² bits/Hz/Joule) |
| `panel_worstrate_vs_bandwidth.csv` | bot-left  | Bandwidth_MHz (**Log10**) | Worst-user rate (Mbit/s) |
| `panel_worstrate_vs_noise.csv`     | bot-right | NoisePSD_dBmHz (linear)   | Worst-user rate (Mbit/s) |

Story: TOP row EE → DQN (scalar) on top. BOTTOM row worst-user rate → MCCRL/AF/inf-only on
top, MODQN/Round-robin/RSS-max = 0. Same DQN (scalar) that wins EE falls behind on equity =
"efficiency bought by starving users". Keep all 8 columns — do NOT delete DQN (scalar).

## Fast workflow (style once, reuse 3×)
1. **Import**: drag the 4 CSVs into Origin → 4 worksheets. First row auto-maps to Long Names.
   In each sheet right-click the X column → **Set As → X** (the method columns stay Y).
2. **Build panel 1** (`panel_ee_vs_bandwidth`): select all cols → **Plot → Line + Symbol**.
   Style every curve per the table below (Plot Details → Line color + Symbol).
   X axis → double-click → **Scale → Type = Log10**; custom ticks 100 200 300 500 700 1000.
3. **Save as template**: right-click the graph → **Save Template As…** → `cdrl_panel.otp`.
4. **Plot the other 3**: in each sheet highlight all cols → right-click → **Plot with Template
   → cdrl_panel.otp**. Colors/symbols auto-apply (identical column order). Then fix per panel:
   Y-axis title, and for the two noise panels switch X **Scale → Linear**.
5. **Merge to 2×2**: **Graph menu → Merge All Graphs in Active Folder** → arrange **2 rows ×
   2 cols** (EE row on top, worst-rate row on bottom). Keep ONE legend (delete the other 3),
   drag it above the panels.

## Style table (the cdrl.png scheme)
| column / method | line colour | symbol | line width |
| :-- | :-- | :-- | :-- |
| MCCRL              | red    (#E41A1C) | ● circle        | 3.0 (thickest, draw on top) |
| MCCRL (inf-only)  | purple (#7D3CB5) | ▲ up-triangle   | 1.5 |
| Coord. Alloc (AF) | green  (#2CA02C) | ▼ down-triangle | 1.5 |
| DQN (scalar)      | cyan   (#17BECF) | ★ star          | 1.5 |
| DQN (throughput)  | blue   (#1F77B4) | ◆ diamond       | 1.5 |
| Round-robin       | grey   (#8C8C8C) | line only / ×   | 1.5 |
| RSS-max           | brown  (#A65628) | + plus          | 1.5 |
| MODQN             | black  (#000000) | ■ square        | 2.4 |

Tips: after styling panel 1, also **Tools → Save/Apply Theme** for one-click reuse. Make MCCRL
the last-plotted layer so red sits on top of the AF/inf-only cluster (they overlap = honest).

## Dense version
After the densify run finishes, regenerate these CSVs with more x-points (smoother) via:
`MODQN_CDRL_SRC=scratch/final_figures/cdrl_style_dense .venv/bin/python scratch/export_cdrl_origin_csv.py`
then re-import (or just refresh the worksheets) — the template keeps the styling.

(Shortcut: if Origin styling is too fiddly, the matplotlib `cdrl_combined_ee_minrate_2x2.png`
already matches the cdrl look and is thesis-ready.)
