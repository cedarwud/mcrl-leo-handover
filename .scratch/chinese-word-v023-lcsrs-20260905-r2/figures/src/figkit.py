#!/usr/bin/env python3
"""thesis-mc 概念圖共用工具 — 版面常數、樣式、閘門。

規格權威：thesis-mc/figures/FIGURE-MANIFEST.md §2（175mm／24px 節點／22px 其餘／
藏青-赭-墨-灰四色／白底白框／實線＝部署、虛線＝僅訓練期）。

幾何是「算出來的」不是抄的（2026-07-19 重寫）：
  * check_layout 規則 7 `inner-vpad`：vpad = (h − n·fontSize·1.2)/2，全圖 spread ≤ 8 才不 ERROR。
    fs=24 ⇒ 行高 28.8。取 **h = 78 / 106 / 134**（1/2/3 行）得 vpad 24.6 / 24.2 / 23.8，spread 0.8。
    ⚠ 家規備忘裡的 80/100/120 是別的字級推出來的，在 fs=24 下 spread = 8.8 會直接 ERROR。
  * h 取偶數 ⇒ 半高為整數。渲染器把 x/y 取整、h 不取整，同一列若混行數又用奇數高，
    中心線會差 0.5px 而產生斜段被 R27-orthogonal-path 擋下；偶數高讓混行數也能整數對齊。
  * check_layout 規則 8 `inner-hpad`：hpad = (w − maxTextWidth)/2，spread ≤ 12 才不 ERROR，
    且 **量的是 label 原字串**（`autoNotation` 在載入期才展開，spec 裡沒有 notation runs）。
    所以這裡用同一支 PIL 字型量同一個字串 ⇒ hpad 恆為 50，不需要探針迭代。
    渲染後的下標比原字串窄，R13 因此自帶餘裕。

USER-SET override（2026-07-19 第二輪，USER 為論文作者，其裁決上位於 house style）：
  * **逐框填色**，語意軸＝「本論文貢獻 vs 沿用自基準」。填 CONTRIB（sand #f3efe6）＝本論文加的；
    留白＝沿用 MODQN 基準。**不是所有框都填，只填該圖真正的貢獻框。**
    牴觸 academic.md rule 1（box fills WHITE/none）＝ USER 明示推翻。
    rule 2 的色彩預算**沒有**牴觸：該規則本就允許「一個淺色 tint 對應一個宣告過的語意」，
    且 #f3efe6 正是它自己舉的例；差別只在本套用逐框填而非 section band。
    lum(#f3efe6)=0.865 ≫ check_layout MIN_FILL_LUM=0.55，且在 SAFE_COLORS 內（0 個 R18 warning）。
  * **論文圖不放頁尾說明文字**（academic.md rule 9）。圖到最後一個方框為止，整段散文改進論文圖說。
    `Fig.note()` 現在對 ≥2 行直接 raise——這條規則做不成機器檢查就不會被遵守（前一輪即是如此）。

其餘引擎事實（實測）：
  * bottom-left / bottom-right 錨點 = 方框水平中心 ∓ 35px（固定位移，不是比例）。
  * 下標／上標寫在 label 內（`_x` / `^x`）並開 autoNotation；直接餵 notation runs 會被
    R20-notation-reconstruction 擋下。
  * autoNotation **不作用於 annotation**：註記寫 `_x` 會原樣印出底線。註記要帶下標時改用
    無框節點（fill 與 stroke 皆 "none" ＋ crossSection: true）承載。
  * check_layout 規則 15：node/edge label 裡出現 `\\d+\\.\\d+` 會判 magic-number WARN
    ⇒ **式號一律只進 annotation／圖說，不進方框**。
  * check_layout 規則 14：node label ≤ 2 行、每行 ≤ 36 字元（user-set，不得以個人判斷推翻）。
  * 共用主幹的邊不掛標籤（規則 17b 對同幹兄弟距離 = 0）；回線走畫布邊緣不走 section 內部。
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

FS_NODE, FS_SMALL = 24, 22
LINE_H = FS_NODE * 1.2          # 28.8
HPAD = 50                       # 單側固定內距
BOX_H = {1: 78, 2: 106, 3: 134}  # 見檔頭：vpad 24.6 / 24.2 / 23.8，且皆為偶數
ANCHOR_DX = 35                  # bottom-left / bottom-right 相對中心的固定位移

# FIGURE-MANIFEST §2 語意色（只上邊框，不填底）
INK = "#333941"    # 中性元件與所有連線
MAIN = "#2f5d80"   # 主要代理／部署路徑
CF = "#8a5740"     # 鯰魚角色與各訓練期機制
MUTE = "#78818a"   # 去強調（捨棄、區塊框線）

# USER-SET 2026-07-19：貢獻框填色。單一 tint、單一語意（見檔頭）。
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
    "node": {"fill": "#ffffff", "stroke": INK, "strokeWidth": 1.5, "rx": 3,
             "fontFamily": SERIF, "fontSize": FS_NODE, "textFill": "#000000"},
    "edge": {"stroke": INK, "strokeWidth": 1.5, "arrowSize": 9,
             "labelFontFamily": SERIF, "labelFontSize": FS_SMALL, "labelFill": "#000000"},
    "section": {"fill": "#ffffff", "stroke": MUTE, "strokeWidth": 1.5, "rx": 4,
                "fontFamily": SERIF, "fontSize": FS_SMALL, "textFill": "#000000"},
    "annotation": {"fontFamily": SERIF, "fontSize": FS_SMALL, "textFill": "#000000",
                   "lineHeight": 30},
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
    """把整段文字斷成不超過 px 寬的多行。

    annotation **不會自動換行**：label 陣列每一筆就是一條 <text>，太長會直接被
    R57-text-within-canvas 判 ERROR。圖例一律經過這裡。
    """
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
    """依標籤算出寬高的方框。w = 最寬行 + 2·HPAD 取偶數 ⇒ hpad 恆 50、中心為整數。

    contrib=True ⇒ 填 CONTRIB tint（USER-SET：本論文貢獻框；見檔頭）。留白＝沿用基準。
    """
    if len(lines) > 2:
        raise SystemExit(f"box {nid}: {len(lines)} 行 — craft-guide §10 rule 1 上限 2 行")
    for ln in lines:
        # autoNotation 只認 ASCII 的 `_x` / `^x`。上下標接非 ASCII（`s^χ_u`）時不會轉成
        # notation run，插入號／底線會**原樣印在圖上**，而兩道機器閘都判它 PASS。
        # 2026-07-19 圖 4-7 實際印出了 `s^χ`，只有眼檢抓到 ⇒ 在這裡擋掉。
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
        # academic.md rule 9（USER-SET 2026-07-19 明確要求）：論文圖不放頁尾散文。
        # 圖到最後一個方框為止；框線／填色／虛線的語意一律進論文圖說，不進畫布。
        # 前一輪就是把 slide idiom 的 footer-legend 套進論文圖，13 張成品有 10 張本應零註記。
        # 「規則做不成機器檢查就不會在生成壓力下被遵守」——所以這裡硬擋，不靠記性。
        # 唯一放行：真正的「一行短鍵」（rule 9 允許）。多行＝那是圖說文字。
        if len(lines) > 1 and not allow_multiline:
            raise SystemExit(
                f"annotation {nid!r}: {len(lines)} 行 — academic.md rule 9：論文圖不放多行散文。"
                f"整段搬進論文圖說（ch*.md）。若真的只是一行短鍵，改成 1 行；"
                f"確有例外再傳 allow_multiline=True（論文圖幾乎不該用到）。")
        # autoNotation 不作用於 annotation ⇒ `ρ_I` 會原樣印出底線。兩道機器閘都看不到，
        # 只有眼檢會抓到（2026-07-19 圖 4-6 實際踩過一次）。在這裡擋掉，不靠記性。
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
        """畫布高 = 最低元素底緣 + margin。移除頁尾圖例後，各圖高度改由內容決定。"""
        bottoms = [n["y"] + n["h"] for n in self.spec["nodes"]]
        bottoms += [s["y"] + s["h"] for s in self.spec["sections"]]
        # annotation 沒有 h；一行約 FS_SMALL·1.4，保守估
        bottoms += [a["y"] + FS_SMALL * 2 for a in self.spec["annotations"]]
        self.spec["canvas"]["height"] = int(max(bottoms)) + margin
        return self.spec["canvas"]["height"]

    def crop(self, margin=24):
        """把畫布四邊收到貼合內容（USER 2026-07-19：四週留白太多、畫布往內收）。

        平移所有座標讓內容左上角 → (margin, margin)，畫布 = 內容範圍 + 2·margin。
        **targetWidthMm 依畫布寬同比例縮**（保持 1440px↔175mm 的 px/mm 密度不變）⇒ 節點實體字級
        （24px≈8.3pt）不因收邊而改變，check_layout 的 pt 地板照樣過；圖只是變窄（≤175mm），不變糊。
        """
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
            ys += [a["y"], a["y"] + len(a["label"]) * 30]
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


def row(fig, ids_lines, y, x0, gap, stroke=INK, strokes=None):
    """把一列方框依固定間隔排開；同一列強制同行數（中心線才對得齊）。"""
    counts = {len(l) for _, l in ids_lines}
    if len(counts) != 1:
        raise SystemExit(f"row at y={y}: 混用 {counts} 行的方框 — 同列必須同行數")
    x = x0
    for nid, lines in ids_lines:
        st = (strokes or {}).get(nid, stroke)
        n = fig.add(box(nid, lines, x, y, st))
        x = n["x"] + n["w"] + gap
    return x - gap


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
                        "--out", "/tmp/_figcheck.json"], capture_output=True, text=True)
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
                        "--out", "/tmp/_figvalid.json"], capture_output=True, text=True)
    out.append("$ validate svg")
    out.append(r.stdout.strip() or r.stderr.strip())
    return r.returncode == 0, "\n".join(out)
