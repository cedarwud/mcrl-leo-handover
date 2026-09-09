"""How much does figure 1 over-credit by omitting the sealed q10 wanted-link reserve?

v1.9 item 1: the selection view predicts SINR_pred = q * h_nominal * p / (N0W + I),
and the transmitted mode is the highest whose threshold SINR_pred clears.
figure1_compute.py instead uses q = 1. Since the rate-target controller solves p so
that the nominal SINR lands exactly on gamma_{m_r}, any q < 1 strictly lowers the
transmitted mode. This quantifies by how much, without inventing a value for q10.
"""
import importlib.util, math, sys
from pathlib import Path

HERE = Path("/home/u24/papers/mcrl-leo-handover/.scratch/multi-catfish-v023-controller-handoff-20260907/paper-lane-20260909/figures")
spec = importlib.util.spec_from_file_location("f1", HERE / "figure1_compute.py")
f1 = importlib.util.module_from_spec(spec)
sys.modules["f1"] = f1
spec.loader.exec_module(f1)

print(f"modes in table: {len(f1.MODES)}")
print(f"rate target r* = {f1.RATE_TARGET_BPS/1e6:.0f} Mbit/s, W = {f1.BANDWIDTH_HZ/1e6:.4f} MHz\n")

# consecutive threshold spacing, to show how many modes a given reserve costs
gaps = []
for a, b in zip(f1.MODES, f1.MODES[1:]):
    gaps.append(10*math.log10(b.gamma/a.gamma))
print(f"ACM threshold spacing dB: min {min(gaps):.3f}  median {sorted(gaps)[len(gaps)//2]:.3f}  max {max(gaps):.3f}\n")

RESERVES_DB = [0.0, 1.0, 1.7, 2.0, 3.0, 4.0, 5.0, 6.0]
print("Per-occupancy effect of the wanted-link reserve, at the rate-target operating point")
print("(power unchanged in every column: v1.9 says the quantile must NOT re-solve power)\n")
hdr = f"{'n_b':>3} {'m_target':>14} {'SE_tgt':>7} |" + "".join(f"{r:>7.1f}dB" for r in RESERVES_DB)
print(hdr); print("-"*len(hdr))
rows = []
for n in (1, 2, 3, 4):
    m_r = f1.rate_target_mode(n)
    gamma_nom = f1.gamma_required(n)
    line = f"{n:>3} {m_r.name:>14} {m_r.se:>7.4f} |"
    ratios = []
    for r_db in RESERVES_DB:
        q = 10.0 ** (-r_db/10.0)
        m_tx = f1.select_mode(gamma_nom * q)
        se = m_tx.se if m_tx else 0.0
        ratios.append(se / m_r.se)
        line += f"{se/m_r.se:>9.3f}"
    rows.append(ratios)
    print(line)
print("\nEach cell is credited bits as a fraction of what figure 1 currently reports.")
print("Bits scale linearly with spectral efficiency and energy is unchanged, so the")
print("same fraction applies to the energy-efficiency values on the figure's y-axis.\n")
for i, r_db in enumerate(RESERVES_DB):
    col = [row[i] for row in rows]
    print(f"reserve {r_db:>4.1f} dB -> EE multiplier across occupancies 1..12: "
          f"min {min(col):.3f}  mean {sum(col)/len(col):.3f}  max {max(col):.3f}")

print("\n" + "="*72)
print("MODE TABLE COVERAGE against the sealed priority declaration")
print("="*72)
se_max_fig = max(m.se for m in f1.MODES)
SE_MAX_SEALED = 3.7109
print(f"modes in this figure:      {len(f1.MODES)}   (all QPSK)")
print(f"modes in the declaration:  28   (QPSK, 8PSK, 16APSK, 32APSK)")
print(f"SE_max in this figure:     {se_max_fig:.4f} bit/s/Hz")
print(f"SE_max in the declaration: {SE_MAX_SEALED:.4f} bit/s/Hz")
print(f"ratio:                     {SE_MAX_SEALED/se_max_fig:.3f}x")
print()
print("Highest occupancy at which the 50 Mbit/s rate target is reachable:")
n = 1
while True:
    try:
        f1.rate_target_mode(n); n += 1
    except ValueError:
        break
print(f"  with this figure's table: {n-1}")
print(f"  with SE_max = {SE_MAX_SEALED}: {int(SE_MAX_SEALED*f1.BANDWIDTH_HZ//f1.RATE_TARGET_BPS)}")
print(f"  engine census (stage 4h): 12 feasible, 13 infeasible")
print()
print(f"occupancies actually plotted by the figure: {f1.OCCUPANCIES}")
