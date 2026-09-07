#!/usr/bin/env python3
"""角度感知的視覺骨幹：發射端波束型樣 G^T(θ) 示意圖（§3.1.2 式 (3.7a)）。

★ 這是 matplotlib 數據曲線，不是 figkit 方塊圖——另一條工具鏈：
  - 不走 figkit 的 check_layout / check figure / validate svg 四道 gate（那是給方塊圖的）。
  - 遵「圖表繪製標準」：plain line、無信賴帶、無捏造、每圖附 CSV。
  - 圖上文字＝英文（房規：圖上英文、圖說繁中）；字型用 Liberation Serif（Times metric-compatible）。

★ 章節紀律「第五章前不出現數字」：本圖為**示意**——
  橫軸正規化為 θ/θ_3dB（無量綱、非實驗值），縱軸為正規化增益(dB)、峰值定為 0 dB；
  不出現任何環境設定值（θ_3dB=3.32°、G_0 等一律不入圖，留待第 5.1 節）。

真相源：thesis-mc/mc-modqn-base.md §3.1.2 式 (3.7a)：
    G^T(θ) = G_0 [ J_1(μ)/(2μ) + 36 J_3(μ)/μ^3 ]^2,  μ = 2.07123 · sinθ / sinθ_3dB
常數 2.07123 使半功率(−3 dB)恰落在 θ = θ_3dB（本腳本輸出會印出實際值核對）。

輸出：deliverable/model-illustration-figures/{png,svg,data}/fig-beam-pattern.*
"""
import pathlib
import numpy as np
from scipy.special import jv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

HERE = pathlib.Path(__file__).parent
OUT = HERE.parent / "deliverable" / "model-illustration-figures"
for sub in ("png", "svg", "data"):
    (OUT / sub).mkdir(parents=True, exist_ok=True)
STEM = "fig-beam-pattern"

# ---- house style: serif = Liberation Serif (Times New Roman metric-compatible) ----
SERIF = "Liberation Serif" if any(f.name == "Liberation Serif" for f in font_manager.fontManager.ttflist) else "DejaVu Serif"
plt.rcParams.update({
    "font.family": "serif", "font.serif": [SERIF], "mathtext.fontset": "cm",
    "font.size": 13, "axes.linewidth": 0.9, "svg.fonttype": "none",
})
STROKE = "#2f5d80"    # 與論文方塊圖同一藍
GREY = "#8a939c"

# ---- the pattern (small-angle: sinθ ≈ θ, so μ = 2.07123 · θ/θ_3dB) ----
def pattern(mu):
    mu = np.asarray(mu, dtype=float)
    out = np.empty_like(mu)
    small = mu < 1e-6
    out[small] = 1.0                                   # μ→0 limit: (1/4 + 3/4)^2 = 1
    m = mu[~small]
    val = jv(1, m) / (2 * m) + 36.0 * jv(3, m) / m**3
    out[~small] = val**2
    return out

x = np.linspace(0, 4, 2000)                            # x = θ/θ_3dB
mu = 2.07123 * x
g = pattern(mu)
g_db = 10 * np.log10(np.clip(g, 1e-6, None))

# half-power check
hp_db = 10 * np.log10(pattern(2.07123 * 1.0))
print(f"[check] gain at θ=θ_3dB (x=1): {float(hp_db):+.3f} dB  (should be ≈ −3.0)")

# ---- plot ----
fig, ax = plt.subplots(figsize=(6.5, 3.7))
ax.plot(x, g_db, color=STROKE, lw=2.0, zorder=3)

# half-power reference: −3 dB line + θ_3dB vertical
ax.axhline(-3.0, color=GREY, ls=(0, (5, 4)), lw=1.0, zorder=1)
ax.axvline(1.0, color=GREY, ls=(0, (5, 4)), lw=1.0, zorder=1)
ax.plot([1.0], [hp_db], "o", color=STROKE, ms=5, zorder=4)
ax.annotate(r"half-power point:  $\theta = \theta_{\mathrm{3dB}}$",
            xy=(1.0, float(hp_db)), xytext=(1.55, -1.4),
            fontsize=11.5, color="#222",
            arrowprops=dict(arrowstyle="->", color="#555", lw=0.9))
ax.annotate("gain falls as the\noff-axis angle grows",
            xy=(0.62, float(10*np.log10(pattern(2.07123*0.62)))), xytext=(1.9, -12.5),
            fontsize=11.5, color="#222", ha="left",
            arrowprops=dict(arrowstyle="->", color="#555", lw=0.9))

ax.set_xlim(0, 4)
ax.set_ylim(-30, 2)
ax.set_xticks([0, 1, 2, 3, 4])
ax.set_yticks([0, -3, -10, -20, -30])
ax.set_xlabel(r"Off-axis angle  $\theta\,/\,\theta_{\mathrm{3dB}}$  (normalized)")
ax.set_ylabel(r"Normalized transmit gain  $G^{T}(\theta)/G_0$  (dB)")
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)
ax.tick_params(length=4)
fig.tight_layout()

png = OUT / "png" / f"{STEM}.png"
svg = OUT / "svg" / f"{STEM}.svg"
fig.savefig(png, dpi=300)
fig.savefig(svg)
plt.close(fig)

# ---- CSV (figure drawing standard: every figure ships its data) ----
csv = OUT / "data" / f"{STEM}.csv"
np.savetxt(csv, np.column_stack([x, g_db]), delimiter=",",
           header="theta_over_theta3dB,normalized_gain_dB", comments="")

print("wrote:", png, svg, csv, sep="\n  ")
