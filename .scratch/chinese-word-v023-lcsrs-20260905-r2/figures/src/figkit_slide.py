#!/usr/bin/env python3
"""thesis-mc 概念圖共用工具 — 【口試簡報／SLIDE-GRADE 版】。

這是 `figkit.py` 的簡報孿生：**只改幾何到簡報尺度，其餘閘門不變式全部照舊**。
規格權威：`~/.claude/skills/flowchart/styles/academic-craft-guide.md` §0（SLIDE/DECK CONTEXT）
＋本 repo 的論文圖視覺鍵（藏青＝主要代理／部署；赭＝鯰魚／僅訓練期機制；墨＝中性＋連線；
sand 填色＝本論文貢獻框；虛線 section＝僅訓練期）。

**與 `figkit.py`（論文圖）唯一的差別＝字級與版面常數**（讓字大到後排能讀）：
  * FS_NODE=42、FS_SMALL=34（論文圖是 24／22）。LINE_H = 42·1.2 = 50.4。
  * BOX_H = 100 / 150 / 202（1/2/3 行）——由 check_layout 規則 7 反推：
    vpad = (h − n·50.4)/2 = 24.8 / 24.6 / 25.4，spread 0.8 ≤ 8，且皆為偶數（中心線整數對齊）。
  * HPAD = 60（單側固定內距）。
  * 線寬加粗到 2.0（一般）／3.0（強調）、arrowSize 13——投影機上細線讀不出來。

**保持不變（＝與論文圖同一套視覺鍵，thesis↔talk 一致）**：
  * 語意色 INK/MAIN/CF/MUTE 與貢獻填色 CONTRIB（sand #f3efe6）完全沿用 `figkit.py`。
  * `box()` 的 2 行上限與非 ASCII 上下標守衛、`_lum` 載入期自檢、`gates()`、`crop()` 全部照抄。
  * `note()` 對 ≥2 行硬 raise（academic.md rule 9：圖不放頁尾散文；簡報圖也不放，一個 message 一張圖）。

字級雖大，實體 pt 仍過 check_layout R28 地板：crop() 維持 175mm↔1440px 密度 ⇒
節點 42px≈14.5pt、其餘 34px≈11.7pt，皆遠高於 7.0／6.5pt。
"""
import json
import pathlib
import re
import subprocess

from PIL import ImageFont

SKILL = "/home/u24/.claude/skills/flowchart"
CHECK_LAYOUT = f"{SKILL}/checks/check_layout.py"
CLI = f"{SKILL}/src/cli/index.mjs"
FONT = f"{SKILL}/assets/fonts/LiberationSerif-Regular.ttf"

FS_NODE, FS_SMALL = 42, 34
LINE_H = FS_NODE * 1.2            # 50.4
HPAD = 60                        # 單側固定內距
BOX_H = {1: 100, 2: 150, 3: 202}  # 見檔頭：vpad 24.8 / 24.6 / 25.4，且皆為偶數
ANCHOR_DX = 35                   # bottom-left / bottom-right 相對中心的固定位移（引擎常數，與字級無關）

# FIGURE-MANIFEST §2 語意色（只上邊框，不填底）——與論文圖 figkit.py 完全相同，不得改。
INK = "#333941"    # 中性元件與所有連線
MAIN = "#2f5d80"   # 主要代理／部署路徑
CF = "#8a5740"     # 鯰魚角色與各訓練期機制
MUTE = "#78818a"   # 去強調（捨棄、區塊框線）

# USER-SET 2026-07-19：貢獻框填色。單一 tint、單一語意（本論文貢獻 vs 沿用自基準）。
CONTRIB = "#f3efe6"   # sand
MIN_FILL_LUM = 0.55   # check_layout 的 dark-fill 閘（ERROR 級）——這裡自檢，不等到閘才發現


def _lum(hexc):
    """check_layout.lum() 的同式複製：WCAG 相對亮度。"""
    h = hexc.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


if _lum(CONTRIB) < MIN_FILL_LUM:   # 有人日後換深色 tint 時，在這裡就炸，不要等 render 完
    raise SystemExit(f"CONTRIB={CONTRIB} lum={_lum(CONTRIB):.3f} < {MIN_FILL_LUM}：dark-fill 會被閘擋下")

SERIF = "Times New Roman, Times, serif"
STYLE = {
    "node": {"fill": "#ffffff", "stroke": INK, "strokeWidth": 2.0, "rx": 4,
             "fontFamily": SERIF, "fontSize": FS_NODE, "textFill": "#000000"},
    "edge": {"stroke": INK, "strokeWidth": 2.0, "arrowSize": 13,
             "labelFontFamily": SERIF, "labelFontSize": FS_SMALL, "labelFill": "#000000"},
    "section": {"fill": "#ffffff", "stroke": MUTE, "strokeWidth": 2.0, "rx": 6,
                "fontFamily": SERIF, "fontSize": FS_SMALL, "textFill": "#000000"},
    "annotation": {"fontFamily": SERIF, "fontSize": FS_SMALL, "textFill": "#000000",
                   "lineHeight": 48},
}

_FONTS = {}


def _font(size):
    if size not in _FONTS:
        _FONTS[size] = ImageFont.truetype(FONT, size)
    return _FONTS[size]


def text_w(line, size=FS_NODE):
    """check_layout 規則 8 量的同一個東西：原字串在釘選字型下的寬度。"""
    return _font(size).getlength(str(line))


def wrap(paragraphs, px, size=FS_SMALL):
    """把整段文字斷成不超過 px 寬的多行（圖例用；簡報圖一般不用）。"""
    lines = []
    for para in paragraphs:
        cur = ""
        for word in para.split():
            probe = f"{cur} {word}".strip()
            if cur and text_w(probe, size) > px:
                lines.append(cur)
                cur = word
            else:
                cur = probe
        if cur:
            lines.append(cur)
    return lines


def box(nid, lines, x, y, stroke=INK, contrib=False, **extra):
    """依標籤算出寬高的方框。w = 最寬行 + 2·HPAD 取偶數 ⇒ hpad 恆 60、中心為整數。

    contrib=True ⇒ 填 CONTRIB tint（本論文貢獻框）。留白＝沿用基準。
    """
    if len(lines) > 2:
        raise SystemExit(f"box {nid}: {len(lines)} 行 — craft-guide §10 rule 1 上限 2 行")
    for ln in lines:
        # autoNotation 只認 ASCII 的 `_x` / `^x`。上下標接非 ASCII（`s^χ_u`）時不會轉成
        # notation run，插入號／底線會**原樣印在圖上**，而兩道機器閘都判它 PASS。
        bad = re.search(r"[_^][^\x00-\x7f]", str(ln))
        if bad:
            raise SystemExit(
                f"box {nid!r}: 標籤含 {bad.group()!r} — autoNotation 只認 ASCII 的下標／上標，"
                f"非 ASCII 會讓 `_`／`^` 原樣印出。改寫標籤。\n  {ln}")
    w = 2 * round((max(text_w(l) for l in lines) + 2 * HPAD) / 2)
    n = {"id": nid, "label": list(lines), "x": int(x), "y": int(y),
         "w": int(w), "h": BOX_H[len(lines)]}
    style = {"stroke": stroke}
    if contrib:
        style["fill"] = CONTRIB
    style.update(extra.pop("style", {}))
    n["style"] = style
    n.update(extra)
    return n


class Fig:
    """一張圖：收方框、算幾何、輸出 spec。"""

    def __init__(self, title, w, h, claim):
        self.spec = {
            "title": title,
            "metadata": {"truthMode": "implemented", "claimBoundary": claim},
            "canvas": {"width": w, "height": h, "backgroundFill": "#ffffff"},
            "targetWidthMm": 175,
            "autoNotation": True,
            "validateLayout": True,
            "style": STYLE,
            "sections": [],
            "nodes": [],
            "edges": [],
            "annotations": [],
        }
        self._by_id = {}

    def add(self, node):
        self.spec["nodes"].append(node)
        self._by_id[node["id"]] = node
        return node

    def sec(self, sid, label, x, y, w, h, dash=None):
        s = {"id": sid, "label": label, "x": int(x), "y": int(y), "w": int(w), "h": int(h)}
        if dash:
            s["style"] = {"dash": dash}
        self.spec["sections"].append(s)
        return s

    def edge(self, eid, a, b, **kw):
        e = {"id": eid, "from": a, "to": b}
        e.update(kw)
        self.spec["edges"].append(e)
        return e

    def note(self, nid, lines, x, y, allow_multiline=False, **kw):
        # academic.md rule 9（USER-SET）：圖不放頁尾散文；簡報圖亦然（一個 message 一張圖）。
        if len(lines) > 1 and not allow_multiline:
            raise SystemExit(
                f"annotation {nid!r}: {len(lines)} 行 — academic.md rule 9：圖不放多行散文。"
                f"細節搬進簡報講稿或論文圖說。若真的只是一行短鍵，改成 1 行。")
        # autoNotation 不作用於 annotation ⇒ `ρ_I` 會原樣印出底線。用無框節點承載帶下標的標籤。
        for ln in lines:
            bad = re.search(r"[_^][A-Za-z0-9]", str(ln))
            if bad:
                raise SystemExit(
                    f"annotation {nid!r}: 標籤含 {bad.group()!r} — annotation 不吃 autoNotation，"
                    f"下標會原樣印出底線。改寫成不帶符號的敘述，或改用無框節點承載。\n  {ln}")
        a = {"id": nid, "label": list(lines), "x": int(x), "y": int(y)}
        a.update(kw)
        self.spec["annotations"].append(a)
        return a

    # 幾何存取
    def n(self, nid):
        return self._by_id[nid]

    def w(self, nid):
        return self._by_id[nid]["w"]

    def cx(self, nid):
        n = self._by_id[nid]
        return n["x"] + n["w"] // 2

    def cy(self, nid):
        n = self._by_id[nid]
        return n["y"] + n["h"] // 2

    def right(self, nid):
        n = self._by_id[nid]
        return n["x"] + n["w"]

    def bot(self, nid):
        n = self._by_id[nid]
        return n["y"] + n["h"]

    def center_on(self, nid, target):
        """把 nid 的水平中心對到 target 的水平中心。"""
        self._by_id[nid]["x"] = int(self.cx(target) - self._by_id[nid]["w"] // 2)

    def fit_height(self, margin=40):
        bottoms = [n["y"] + n["h"] for n in self.spec["nodes"]]
        bottoms += [s["y"] + s["h"] for s in self.spec["sections"]]
        bottoms += [a["y"] + FS_SMALL * 2 for a in self.spec["annotations"]]
        self.spec["canvas"]["height"] = int(max(bottoms)) + margin
        return self.spec["canvas"]["height"]

    def crop(self, margin=30):
        """把畫布四邊收到貼合內容。targetWidthMm 依畫布寬同比例縮（維持 175mm↔1440px 密度）。"""
        xs, ys = [], []
        for n in self.spec["nodes"]:
            xs += [n["x"], n["x"] + n["w"]]
            ys += [n["y"], n["y"] + n["h"]]
        for s in self.spec["sections"]:
            xs += [s["x"], s["x"] + s["w"]]
            ys += [s["y"], s["y"] + s["h"]]
        for a in self.spec["annotations"]:
            w = max((text_w(l, FS_SMALL) for l in a["label"]), default=0)
            xs += [a["x"], a["x"] + w]
            ys += [a["y"], a["y"] + len(a["label"]) * 48]
        for e in self.spec["edges"]:
            for wp in e.get("waypoints", []):
                xs.append(wp["x"])
                ys.append(wp["y"])
        if not xs:
            return
        cxmin, cxmax, cymin, cymax = min(xs), max(xs), min(ys), max(ys)
        dx, dy = margin - cxmin, margin - cymin
        for n in self.spec["nodes"]:
            n["x"] += dx
            n["y"] += dy
        for s in self.spec["sections"]:
            s["x"] += dx
            s["y"] += dy
        for a in self.spec["annotations"]:
            a["x"] += dx
            a["y"] += dy
        for e in self.spec["edges"]:
            for wp in e.get("waypoints", []):
                wp["x"] += dx
                wp["y"] += dy
        w = int(round((cxmax - cxmin) + 2 * margin))
        h = int(round((cymax - cymin) + 2 * margin))
        self.spec["canvas"]["width"] = w
        self.spec["canvas"]["height"] = h
        self.spec["targetWidthMm"] = round(w / 1440 * 175, 2)
        return w, h

    def write(self, path):
        pathlib.Path(path).write_text(
            json.dumps(self.spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path


def row(fig, ids_lines, y, x0, gap, stroke=INK, strokes=None, contribs=None):
    """把一列方框依固定間隔排開；同一列強制同行數（中心線才對得齊）。"""
    counts = {len(l) for _, l in ids_lines}
    if len(counts) != 1:
        raise SystemExit(f"row at y={y}: 混用 {counts} 行的方框 — 同列必須同行數")
    x = x0
    for nid, lines in ids_lines:
        st = (strokes or {}).get(nid, stroke)
        cb = nid in (contribs or set())
        n = fig.add(box(nid, lines, x, y, st, contrib=cb))
        x = n["x"] + n["w"] + gap
    return x - gap


def spread_row(fig, ids_lines, y, left, right, stroke=INK, strokes=None, contribs=None):
    """把一列方框在 [left,right] 內置中、間隔平均分配（同列同行數 ⇒ 中心線自動對齊）。"""
    widths = [2 * round((max(text_w(l) for l in lines) + 2 * HPAD) / 2) for _, lines in ids_lines]
    span = right - left
    gap = (span - sum(widths)) // max(1, (len(ids_lines) - 1))
    x = left
    for (nid, lines), w in zip(ids_lines, widths):
        st = (strokes or {}).get(nid, stroke)
        cb = nid in (contribs or set())
        fig.add(box(nid, lines, x, y, st, contrib=cb))
        x += w + gap
    return gap


def gates(spec_path, svg_path):
    """check_layout --preset academic → check figure → render → validate svg。回傳 (ok, 全文)。"""
    out = []
    r = subprocess.run(["python3", CHECK_LAYOUT, "--preset", "academic", spec_path],
                       capture_output=True, text=True)
    out.append("$ check_layout --preset academic")
    out.append(r.stdout.strip() or "(no output)")
    if r.returncode != 0:
        return False, "\n".join(out)

    r = subprocess.run(["node", CLI, "check", "figure", "--spec", spec_path,
                        "--out", "/tmp/_figcheck_slide.json"], capture_output=True, text=True)
    out.append("$ check figure")
    out.append(r.stdout.strip() or r.stderr.strip())
    if "FAIL" in r.stdout or r.returncode != 0:
        return False, "\n".join(out)

    r = subprocess.run(["node", CLI, "render", "paper", "--spec", spec_path, "--out", svg_path],
                       capture_output=True, text=True)
    if r.returncode != 0:
        out.append("$ render paper\n" + (r.stderr.strip() or r.stdout.strip()))
        return False, "\n".join(out)

    r = subprocess.run(["node", CLI, "validate", "svg", "--svg", svg_path, "--spec", spec_path,
                        "--out", "/tmp/_figvalid_slide.json"], capture_output=True, text=True)
    out.append("$ validate svg")
    out.append(r.stdout.strip() or r.stderr.strip())
    return r.returncode == 0, "\n".join(out)
