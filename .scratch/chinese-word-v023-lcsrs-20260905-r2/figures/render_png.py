#!/usr/bin/env python3
"""把 figkit 的 SVG 渲染成論文用 PNG（2× viewBox，約 418 DPI @ 175mm）。

**為什麼需要這支腳本**：直接 `google-chrome --headless --screenshot <file.svg>` 會壞，而且是
**看起來成功、尺寸也對**的那種壞——2026-07-20 同一天踩了兩次：

  (a) SVG 內建尺寸是 `mm`（如 `width="173.78mm"`≈657px），視窗卻依 viewBox 像素（1430）開
      ⟹ 內容只填約 46%，其餘一大片空白。
  (b) 把 width/height 改成 viewBox 像素後仍會**裁掉底部約 64 CSS px**（body 邊距／視窗與
      viewport 的落差）⟹ 最下面一個框被切掉。

兩種壞況下 PNG 尺寸都「正確」，byte 數也在合理範圍 ⟹ **只驗尺寸或檔案大小會全部放行**。
正解＝HTML wrapper（margin:0）＋ width/height 改 viewBox 像素 ＋ 視窗開高再裁回 viewBox 尺寸。

等價性已驗證：拿 git 中已知正確的 `fig-cdrl-vs-mccrl.png` 用本腳本重繪，**sha256 位元相同**。

用法：
    python3 figures/render_png.py figures/fig-xxx.editable.svg          # → figures/fig-xxx.png
    python3 figures/render_png.py figures/fig-xxx.editable.svg out.png
    python3 figures/render_png.py --all                                 # 重繪所有 editable SVG

渲染後會印出「內容列範圍」——若上緣不是小數字、或下緣貼著圖高，就是又裁到了。
"""
import argparse
import pathlib
import re
import subprocess
import sys
import tempfile

CHROME = "google-chrome"
SCALE = 2               # 2× viewBox ⇒ 175mm 下約 418 DPI
HEADROOM = 200          # 視窗多開的高度，之後裁回；用來閃開 (b) 的底部裁切


def render(svg_path: pathlib.Path, out_png: pathlib.Path) -> None:
    from PIL import Image
    import numpy as np

    svg = svg_path.read_text(encoding="utf-8")
    m = re.search(r'viewBox="0 0 (\d+(?:\.\d+)?) (\d+(?:\.\d+)?)"', svg)
    if not m:
        sys.exit(f"{svg_path}: 找不到 viewBox，無法決定渲染尺寸")
    w, h = (int(float(x)) for x in m.groups())

    # 關鍵一：包進 margin:0 的 HTML；關鍵二：內建 mm 尺寸換成 viewBox 像素
    html = (f'<!doctype html><style>html,body{{margin:0;padding:0}}'
            f'svg{{display:block}}</style>{svg}')
    html = re.sub(r'width="[\d.]+mm"', f'width="{w}"', html, count=1)
    html = re.sub(r'height="[\d.]+mm"', f'height="{h}"', html, count=1)

    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        page, shot = tmp / "page.html", tmp / "shot.png"
        page.write_text(html, encoding="utf-8")
        r = subprocess.run(
            [CHROME, "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
             f"--force-device-scale-factor={SCALE}",
             f"--window-size={w},{h + HEADROOM}",       # 關鍵三：開高
             f"--screenshot={shot}", f"file://{page}"],
            capture_output=True)
        if not shot.is_file():
            sys.exit(f"chrome 渲染失敗：{r.stderr.decode()[:400]}")
        im = Image.open(shot).crop((0, 0, w * SCALE, h * SCALE))   # 關鍵四：裁回 viewBox
        im.save(out_png)

    a = np.array(Image.open(out_png).convert("L"))
    rows = np.where((a < 250).any(axis=1))[0]
    cols = np.where((a < 250).any(axis=0))[0]
    flag = ""
    if rows.max() >= a.shape[0] - 2 or cols.max() >= a.shape[1] - 2:
        flag = "  ⚠ 內容貼到邊界＝可能仍被裁切，請開圖確認"
    print(f"{out_png}  {im.size}  內容列={rows.min()}..{rows.max()} "
          f"欄={cols.min()}..{cols.max()}{flag}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("svg", nargs="?", help="來源 .editable.svg")
    ap.add_argument("out", nargs="?", help="輸出 .png（預設同名去掉 .editable）")
    ap.add_argument("--all", action="store_true", help="重繪本資料夾所有 *.editable.svg")
    args = ap.parse_args()

    here = pathlib.Path(__file__).resolve().parent
    if args.all:
        for s in sorted(here.glob("*.editable.svg")):
            render(s, s.with_name(s.name.replace(".editable.svg", ".png")))
        return
    if not args.svg:
        ap.error("需要一個 SVG 路徑，或用 --all")
    s = pathlib.Path(args.svg)
    render(s, pathlib.Path(args.out) if args.out
           else s.with_name(s.name.replace(".editable.svg", ".png")))


if __name__ == "__main__":
    main()
