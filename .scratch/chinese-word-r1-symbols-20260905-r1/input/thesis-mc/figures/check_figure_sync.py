#!/usr/bin/env python3
"""圖 ↔ 論文正文 同步檢查器（thesis-mc）。

**為什麼存在。** 圖重繪之後，正文與圖說可能還在描述舊版本。本腳本為每一張「已嵌入論文」
的圖記錄內容雜湊，之後任何 session 只要跑一次，就知道哪張圖動過、對應該回頭重讀論文的
哪一節——不必憑記憶，也不必逐張開圖比對。

**為什麼記雜湊，不只記修改時間。** `git checkout` 不保留 mtime；重繪但內容沒變也會讓
mtime 前進。mtime 只適合給人看，判斷「內容真的變了嗎」要靠雜湊。兩者都記。

**為什麼連 builder 和 editable SVG 一起記。** 2026-07-20 實際發生過：builder 修好了、
deliverable 那份副本重繪了，但論文真正嵌入的那張 PNG 沒重繪——只比對 PNG 抓不到這一類
漂移，比對 builder 才抓得到。

用法：
    python3 figures/check_figure_sync.py            # 檢查；偵測到漂移則 exit 1
    python3 figures/check_figure_sync.py --update   # 確認正文已同步後，重設基準

在 thesis-mc/ 目錄下執行。
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys
from datetime import datetime

HERE = pathlib.Path(__file__).resolve().parent          # thesis-mc/figures
ROOT = HERE.parent                                       # thesis-mc
STATE = HERE / "figure-sync.json"
MANIFEST = HERE / "FIGURE-SYNC-MANIFEST.md"

CHAPTERS = [
    "mc-modqn-base.md",          # 題名頁＋摘要＋第一～三章
    "ch4-method.md",
    "ch5-experimental-result.md",
    "ch6-conclusion.md",
]

# builder 檔名多數可由圖檔名推得；推不出來的列在這裡。
BUILDER_OVERRIDE = {
    "fig-periodic-intervention": "build_fig_intervention.py",
    "fig-intervention-annealing": "build_fig_intervention.py",
    "fig4-2-mccrl-architecture": "build_fig4_2.py",
    "fig4-7-training-deployment-flow": "build_fig4_7.py",
}

EMBED_RE = re.compile(r"^!\[[^\]]*\]\((figures/[^)]+?)\)")
CAPTION_RE = re.compile(r"^圖 (\d+-\d+)：")
HEADER_RE = re.compile(r"^#{1,3} (.+)$")


def sha256(path: pathlib.Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def mtime(path: pathlib.Path) -> str | None:
    if not path.is_file():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")


def builder_for(stem: str, png: pathlib.Path) -> pathlib.Path | None:
    name = BUILDER_OVERRIDE.get(stem, "build_" + stem.replace("-", "_") + ".py")
    # Redrawn figures keep their builder beside the PNG so the whole iteration
    # remains self-contained. Prefer that builder; falling back to figures/src
    # preserves the layout used by the established figure set.
    adjacent = png.parent / name
    if adjacent.is_file():
        return adjacent
    p = HERE / "src" / name
    return p if p.is_file() else None


def scan() -> dict:
    """掃過各章，找出所有已嵌入的圖，連同它所在的節與圖說一起記錄。"""
    found = {}
    for chapter in CHAPTERS:
        path = ROOT / chapter
        if not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        section = "(章首)"
        pending = None
        for lineno, line in enumerate(lines, 1):
            h = HEADER_RE.match(line)
            if h:
                section = h.group(1).strip()
            m = EMBED_RE.match(line)
            if m:
                pending = (m.group(1), lineno, section)
                continue
            c = CAPTION_RE.match(line)
            if c and pending:
                rel, lineno_img, sec = pending
                png = ROOT / rel
                stem = pathlib.Path(rel).stem
                svg = png.with_suffix("").with_name(stem + ".editable.svg")
                bld = builder_for(stem, png)
                found[f"圖 {c.group(1)}"] = {
                    "png": rel,
                    "png_sha256": sha256(png),
                    "png_mtime": mtime(png),
                    "svg": svg.name if svg.is_file() else None,
                    "svg_sha256": sha256(svg),
                    "builder": bld.name if bld else None,
                    "builder_sha256": sha256(bld) if bld else None,
                    "caption_sha256": hashlib.sha256(line.encode()).hexdigest()[:16],
                    "chapter": chapter,
                    "section": sec,
                    "embed_line": lineno_img,
                }
                pending = None
    return found


def write_manifest(figs: dict, stamped: str) -> None:
    rows = [
        "# 圖 ↔ 正文 同步基準（自動產生，勿手改）",
        "",
        f"> 基準設定時間：**{stamped}**。以 `python3 figures/check_figure_sync.py` 檢查漂移，",
        "> `--update` 重設基準（**先確認正文與圖說已同步**再重設，否則等於把漂移蓋掉）。",
        "> 雜湊為 sha256 前 16 碼。`png_mtime` 只供人閱讀，判斷是否真的改變請看雜湊。",
        "",
        "| 圖 | 檔案 | 最後修改 | PNG 雜湊 | builder | 論文位置 |",
        "|---|---|---|---|---|---|",
    ]
    for key in sorted(figs, key=lambda k: [int(x) for x in k.split()[1].split("-")]):
        f = figs[key]
        rows.append(
            f"| {key} | `{pathlib.Path(f['png']).name}` | {f['png_mtime']} | `{f['png_sha256']}` | "
            f"{('`' + f['builder'] + '`') if f['builder'] else '—（既有點陣圖，無 builder）'} | "
            f"{f['chapter']} §{f['section'].split()[0]} |"
        )
    rows += [
        "",
        "## 偵測到漂移時要做什麼",
        "",
        "1. **PNG 變了** → 該圖的內容改過：重讀「論文位置」那一節的正文與圖說，確認仍相符。",
        "2. **builder 或 editable SVG 變了、PNG 沒變** → 多半是改了圖但忘記重繪論文實際嵌入的",
        "   那一張（2026-07-20 發生過）。重跑 builder，再重新檢查。",
        "3. **圖說變了、圖沒變** → 正常（改文字），確認新圖說仍描述得到圖上的東西即可。",
        "",
        "確認同步後再跑 `--update` 重設基準。",
        "",
    ]
    MANIFEST.write_text("\n".join(rows), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--update", action="store_true", help="重設基準（確認正文已同步後才用）")
    args = ap.parse_args()

    now = scan()
    if not now:
        print("找不到任何已嵌入的圖——請在 thesis-mc/ 目錄下執行。")
        return 2

    if args.update or not STATE.is_file():
        stamped = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        STATE.write_text(json.dumps(
            {"baseline_set_at": stamped,
             "_note": "自動產生；以 check_figure_sync.py --update 更新。",
             "figures": now}, ensure_ascii=False, indent=2), encoding="utf-8")
        write_manifest(now, stamped)
        print(f"已設定基準：{len(now)} 張圖 @ {stamped}")
        print(f"  {STATE.relative_to(ROOT)}\n  {MANIFEST.relative_to(ROOT)}")
        return 0

    old = json.loads(STATE.read_text(encoding="utf-8"))
    base, drift, warn, info = old["figures"], [], [], []

    for key, f in sorted(now.items()):
        if key not in base:
            drift.append(f"{key}  新增的圖（{pathlib.Path(f['png']).name}）— 基準裡沒有")
            continue
        b = base[key]
        if b["png_sha256"] != f["png_sha256"]:
            drift.append(f"{key}  圖檔內容已改（{f['chapter']} §{f['section'].split()[0]}）"
                         f" → 重讀該節正文與圖說")
        else:
            for kind in ("builder", "svg"):
                if b.get(kind + "_sha256") != f.get(kind + "_sha256"):
                    warn.append(f"{key}  {kind} 改了但 PNG 沒變 → 圖可能改了卻忘記重繪論文嵌入的那張")
        if b.get("caption_sha256") != f.get("caption_sha256"):
            info.append(f"{key}  圖說文字有改（圖檔未變）")

    for key in base:
        if key not in now:
            drift.append(f"{key}  已不在論文中（被移除或改號）")

    print(f"基準：{old['baseline_set_at']}    現有已嵌入的圖：{len(now)} 張")
    for tag, items in (("需處理", drift), ("警告", warn), ("備註", info)):
        for it in items:
            print(f"  [{tag}] {it}")
    if not (drift or warn):
        print("  圖與基準一致，正文無需因圖而調整。" + ("" if not info else ""))
    return 1 if drift or warn else 0


if __name__ == "__main__":
    sys.exit(main())
