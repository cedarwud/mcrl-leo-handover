"""Does dwell N control anything geometric?  Q-E's premise, checked."""
import sys, math
sys.path.insert(0, "src")
import numpy as np
from mcrl.env.cells import build_cell_grid, cell_radius_km
from mcrl.env.mobility import USER_SPEED_KMH

R_b = cell_radius_km(483.0)
print(f"cell radius R_b = {R_b:.3f} km, user speed = {USER_SPEED_KMH} km/h\n")
print(f"{'dt':>4} | " + " | ".join(f"N={n}" for n in (2,3,4)))
print("-"*46)
for dt_s in (1, 5, 10, 30, 60):
    row = []
    for n in (2, 3, 4):
        travel_km = USER_SPEED_KMH / 3600.0 * dt_s * n
        row.append(f"{travel_km:6.3f} km ({100*travel_km/R_b:4.1f}%)")
    print(f"{dt_s:4d} | " + " | ".join(row))
print("\n(distance a user travels within ONE dwell segment, as a share of R_b)")
print("\nA re-key can only move j=0 if the user has crossed a Voronoi boundary.")
print("Worst case: the user starts exactly on a boundary and moves perpendicular.")
print(f"Even then it takes {R_b:.1f} km of travel to cross a whole cell.")
for dt_s in (30, 60):
    t_cross = R_b / (USER_SPEED_KMH/3600.0)
    print(f"  at dt={dt_s}s, crossing one cell radius takes "
          f"{t_cross:.0f} s = {t_cross/dt_s:.0f} steps = {t_cross/(dt_s*4):.0f} dwell segments at N=4")
