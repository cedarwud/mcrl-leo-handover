#!/usr/bin/env python3
"""Apply the paper-facing R1 notation overlay to a private thesis mirror.

The live thesis and authority table are outside this workspace and are never
written by this script.  Only the copied source chain is changed.  The
replacement set deliberately contains the short role marks approved by the
2026-09-05 R1 mapping; MODQN-only symbols are not in the set.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
THESIS = ROOT / "input" / "thesis-mc"
TABLE = ROOT / "input" / "active-symbol-table.md"

# These are paper-facing R1 physical symbols.  The order matters for the two
# prose PA substitutions and for replacing the long active marker before any
# smaller substring can be considered.
REPLACEMENTS = (
    (r"\theta_{3dB}", r"\theta_3"),
    (r"theta_(3dB)", r"theta_3"),
    (r"p_{\max}", r"p^{+}"),
    (r"p_{\mathrm{sat}}", r"p^{s}"),
    (r"\xi_{\max}", r"\xi^{+}"),
    (r"N^{\mathrm{act}}", r"N^{a}"),
    (r"P_{\mathrm{cir}}", r"P^{c}"),
    (r"P_{\mathrm{BB}}", r"P^{b}"),
    (r"P_{\mathrm{RF}}", r"p_{s,v}"),
    (r"P_{\mathrm{DC}}", r"P^{p}_{s,v}"),
    (r"G_{R,\min}", r"G^{R}_{-}"),
    (r"G_{R,\max}", r"G^{R}_{+}"),
    (r"\theta^{R}_{\min}", r"\theta^{R}_{-}"),
    (r"\theta^R_{\min}", r"\theta^R_{-}"),
    (r"A_{\mathrm{zen}}", r"A^{z}"),
    (r"I^{\mathrm{intra}}", r"I^{i}"),
    (r"I^{\mathrm{inter}}", r"I^{x}"),
    (r"B_{\mathrm{sys}}", r"B^{g}"),
    (r"L_{fs}", r"L_f"),
    (r"L_{sc}", r"L_c"),
    (r"L_{sf}", r"L_s"),
)


def replace_file(path: Path) -> dict[str, int]:
    text = path.read_text(encoding="utf-8")
    counts: dict[str, int] = {}
    for old, new in REPLACEMENTS:
        count = text.count(old)
        if count:
            text = text.replace(old, new)
            counts[old] = count

    # The remaining standalone names occur only inside math in the copied
    # source.  Keep ordinary prose words untouched.
    for old, new in ((r"^{NF/10}", r"^{N_f/10}"), (r"$NF$", r"$N_f$"),
                     (r",NF$", r",N_f$"), (r"^{BO/10}", r"^{b_o/10}"),
                     (r"$BO$", r"$b_o$")):
        count = text.count(old)
        if count:
            text = text.replace(old, new)
            counts[old] = count

    path.write_text(text, encoding="utf-8")
    return counts


def main() -> None:
    source_files = [
        THESIS / "mc-modqn-base.md",
        THESIS / "ch4-method.md",
        THESIS / "ch5-experimental-result.md",
        THESIS / "ch6-conclusion.md",
    ]
    before = TABLE.read_text(encoding="utf-8")
    table_counts: dict[str, int] = {}
    table = before
    for old, new in REPLACEMENTS:
        count = table.count(old)
        if count:
            table = table.replace(old, new)
            table_counts[old] = count
    for old, new in ((r"^{NF/10}", r"^{N_f/10}"), (r"$NF$", r"$N_f$"),
                     (r",NF$", r",N_f$"), (r"^{BO/10}", r"^{b_o/10}"),
                     (r"$BO$", r"$b_o$")):
        count = table.count(old)
        if count:
            table = table.replace(old, new)
            table_counts[old] = count

    overlay = r"""

## 2026-09-05 紙面 R1 單字母記號覆蓋層

本份鏡像表是給純中文版論文與 Word 紙面使用的版本化副本。它只更新新版
角度感知能量效率／功率主鏈的記號；原始 MODQN-only 公式、歷史來源與程式
欄位名稱不因本覆蓋層改寫。新版紙面使用下列單字母上下標：

| 舊紙面記號 | 本版紙面記號 | 定義 |
|---|---|---|
| $\theta_{3dB}$ | $\theta_3$ | 全 3 dB 半功率波束寬；半功率單邊角為 $\theta_3/2$ |
| $p_{\max}$ | $p^{+}$ | 每波束 RF 輸出上限 |
| $p_{\mathrm{sat}}$ | $p^{s}$ | 飽和功率參考值 |
| $\xi_{\max}$ | $\xi^{+}$ | 最大轉換效率 |
| $N^{\mathrm{act}}_s$ | $N^a_s$ | 衛星 $s$ 的啟用波束數 |
| $P_{\mathrm{cir}}$, $P_{\mathrm{BB}}$ | $P^c$, $P^b$ | 電路與基頻固定功率 |
| $P_{\mathrm{RF}}$, $P_{\mathrm{DC}}$ | $p_{s,v}$, $P^p_{s,v}$ | 射頻輸出與電源端功率 |
| $G_{R,\min}$, $G_{R,\max}$ | $G^R_{-}$, $G^R_{+}$ | 接收增益下、上界 |
| $\theta^R_{\min}$ | $\theta^R_{-}$ | 接收型樣的下限角 |
| $A_{\mathrm{zen}}$ | $A^z$ | 天頂大氣吸收常數 |
| $I^{\mathrm{intra}}$, $I^{\mathrm{inter}}$ | $I^i$, $I^x$ | 同衛星與跨衛星干擾 |
| $B_{\mathrm{sys}}$ | $B^g$ | 系統總頻寬 |
| $NF$, $BO$ | $N_f$, $b_o$ | 雜訊指數與輸出回退 |

這些替換不改變物理關係、數值結果或 Chapter 5 的結果資料；它們只把新 R1
紙面符號統一到本版表格。C2、C3、Expected-ZR、$\lambda$、學習器公式與
效能結論不屬於本次 Word 更新範圍。
"""
    # If a previous run already inserted the overlay, remove that generated
    # block before reapplying replacements.  This keeps the script idempotent
    # and prevents the old-notation column in the overlay from being rewritten.
    overlay_heading = "## 2026-09-05 紙面 R1 單字母記號覆蓋層"
    if overlay_heading in table:
        prefix, rest = table.split(overlay_heading, 1)
        marker = "\n## 1. 使用規則\n"
        if marker not in rest:
            raise SystemExit("active table structure changed: overlay end marker missing")
        table = prefix.rstrip("\n") + "\n" + rest[rest.index(marker):].lstrip("\n")

    # Keep the original table as the body and make the overlay explicit near
    # the beginning so a reader does not confuse archived rows with the paper
    # surface.
    if overlay_heading not in table:
        marker = "\n## 1. 使用規則\n"
        if marker not in table:
            raise SystemExit("active table structure changed: insertion marker missing")
        table = table.replace(marker, overlay + marker, 1)
    TABLE.write_text(table, encoding="utf-8")

    report = ROOT / "reports" / "notation-apply-counts.txt"
    lines = ["active-symbol-table:"]
    lines.extend(f"  {old} -> {new}: {table_counts.get(old, 0)}"
                 for old, new in REPLACEMENTS)
    for path in source_files:
        counts = replace_file(path)
        lines.append(f"{path.relative_to(ROOT)}:")
        lines.extend(f"  {old}: {count}" for old, count in counts.items())
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
