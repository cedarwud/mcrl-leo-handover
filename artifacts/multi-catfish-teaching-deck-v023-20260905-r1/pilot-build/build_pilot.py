#!/usr/bin/env python3
"""Author the one-slide WMNLab LC-SRS pilot before native-math injection."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = Path("/home/u24/pptx-craft/assets/wmnlab.pptx")
OUTPUT = ROOT / "pilot-build" / "lc-srs-pilot-authored.pptx"

FONT = "Times New Roman"
BLUE = RGBColor(0x32, 0x32, 0x83)
DEEP_BLUE = RGBColor(0x00, 0x33, 0x66)
INK = RGBColor(0x1F, 0x29, 0x37)
MUTED = RGBColor(0x4B, 0x55, 0x63)
LINE = RGBColor(0xCB, 0xD5, 0xE1)
PANEL = RGBColor(0xF8, 0xFA, 0xFC)
PALE_BLUE = RGBColor(0xF0, 0xF4, 0xF8)
PALE_GREEN = RGBColor(0xE8, 0xF5, 0xE9)
GREEN = RGBColor(0x16, 0xA3, 0x4A)
AMBER = RGBColor(0xFF, 0xF3, 0xCD)
AMBER_TEXT = RGBColor(0x85, 0x64, 0x04)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)


def _remove_shape(shape) -> None:
    element = shape._element
    element.getparent().remove(element)


def _set_text(
    shape,
    text: str,
    *,
    size: int,
    bold: bool = False,
    color: RGBColor = INK,
    align: PP_ALIGN = PP_ALIGN.LEFT,
    valign: MSO_ANCHOR = MSO_ANCHOR.MIDDLE,
    margin: float = 0.08,
) -> None:
    frame = shape.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.margin_left = Inches(margin)
    frame.margin_right = Inches(margin)
    frame.margin_top = Inches(margin)
    frame.margin_bottom = Inches(margin)
    frame.vertical_anchor = valign
    paragraph = frame.paragraphs[0]
    paragraph.alignment = align
    paragraph.space_before = Pt(0)
    paragraph.space_after = Pt(0)
    run = paragraph.add_run()
    run.text = text
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = False
    run.font.color.rgb = color


def _text_box(slide, x, y, w, h, text, *, size=20, bold=False, color=INK, align=PP_ALIGN.LEFT):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    _set_text(shape, text, size=size, bold=bold, color=color, align=align)
    return shape


def _card(slide, x, y, w, h, *, fill=PANEL, line=LINE, radius=True):
    kind = MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE if radius else MSO_AUTO_SHAPE_TYPE.RECTANGLE
    shape = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.color.rgb = line
    shape.line.width = Pt(1)
    return shape


def _formula_host(slide, marker: str, name: str, x, y, w, h, *, fill=WHITE, line=LINE):
    shape = _card(slide, x, y, w, h, fill=fill, line=line, radius=True)
    shape.name = name
    _set_text(shape, marker, size=20, color=INK, align=PP_ALIGN.CENTER, margin=0.04)
    return shape


def _profile(slide, x, y, code: str, caption: str, *, active_left: bool, active_right: bool):
    card = _card(slide, x, y, 1.93, 1.22, fill=WHITE, line=LINE)
    _text_box(slide, x + 0.08, y + 0.04, 0.45, 0.34, code, size=20, bold=True, color=DEEP_BLUE)
    _text_box(slide, x + 0.53, y + 0.04, 1.30, 0.48, caption, size=20, color=INK)
    beam = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.ISOSCELES_TRIANGLE,
        Inches(x + 0.72),
        Inches(y + 0.55),
        Inches(0.48),
        Inches(0.46),
    )
    beam.rotation = 180
    beam.fill.solid()
    beam.fill.fore_color.rgb = RGBColor(0xE0, 0xE7, 0xFF)
    beam.line.color.rgb = BLUE
    for offset, active in ((0.36, active_left), (1.34, active_right)):
        dot = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.OVAL,
            Inches(x + offset),
            Inches(y + 0.87),
            Inches(0.28),
            Inches(0.28),
        )
        dot.fill.solid()
        dot.fill.fore_color.rgb = GREEN if active else RGBColor(0x94, 0xA3, 0xB8)
        dot.line.color.rgb = WHITE
    return card


def build() -> Path:
    prs = Presentation(TEMPLATE)
    slide = prs.slides[2]

    # Preserve the template's slide master, logo, rules and slide-number field.
    # Remove only the authored slide-level title/body placeholders.
    for shape in list(slide.shapes):
        _remove_shape(shape)

    title = _text_box(
        slide,
        0.70,
        0.13,
        9.35,
        0.62,
        "Two-Player LC-SRS Teacher",
        size=28,
        bold=True,
        color=BLUE,
    )
    title.name = "Pilot title"

    badge = _card(slide, 9.73, 0.18, 2.87, 0.43, fill=AMBER, line=RGBColor(0xFF, 0xEE, 0xBA))
    badge.name = "Status badge"
    _set_text(
        badge,
        "C3 GATE — HOLD",
        size=20,
        bold=True,
        color=AMBER_TEXT,
        align=PP_ALIGN.CENTER,
        margin=0.02,
    )

    subtitle = _text_box(
        slide,
        0.72,
        0.94,
        11.85,
        0.44,
        "Four matched profiles expose joint beam-closing surplus.",
        size=24,
        color=INK,
    )
    subtitle.name = "Pilot subtitle"

    left = _card(slide, 0.62, 1.45, 4.25, 5.15, fill=PANEL, line=LINE)
    left.name = "Matched profile panel"
    _text_box(slide, 0.82, 1.58, 3.80, 0.42, "Matched physical profiles", size=20, bold=True, color=DEEP_BLUE)
    _profile(slide, 0.82, 2.08, "00", "stay", active_left=False, active_right=False)
    _profile(slide, 2.84, 2.08, "10", "move 1", active_left=True, active_right=False)
    _profile(slide, 0.82, 3.43, "01", "move 2", active_left=False, active_right=True)
    _profile(slide, 2.84, 3.43, "11", "move 1+2", active_left=True, active_right=True)

    callout = _card(slide, 0.82, 4.91, 3.95, 1.40, fill=PALE_BLUE, line=BLUE)
    callout.name = "Matched field callout"
    _set_text(
        callout,
        "Sealed anchor\nMatched fading\nMember actions only",
        size=20,
        bold=False,
        color=INK,
        align=PP_ALIGN.CENTER,
        margin=0.08,
    )

    right = _card(slide, 5.08, 1.45, 7.63, 5.15, fill=PALE_BLUE, line=BLUE)
    right.name = "Teacher formula panel"
    _text_box(slide, 5.28, 1.57, 7.15, 0.38, "From local terms to an exact coalition residual", size=20, bold=True, color=DEEP_BLUE)

    _text_box(slide, 5.25, 2.12, 0.78, 0.34, "Own", size=20, bold=True, color=MUTED)
    _formula_host(slide, "[[PPT_NATIVE_MATH:local]]", "Math host local", 6.03, 1.92, 6.41, 0.78)

    _text_box(slide, 5.25, 2.94, 0.78, 0.34, "Spill", size=20, bold=True, color=MUTED)
    _formula_host(slide, "[[PPT_NATIVE_MATH:externality]]", "Math host externality", 6.03, 2.74, 6.41, 0.78)

    _text_box(slide, 5.25, 3.80, 0.78, 0.34, "C3", size=20, bold=True, color=MUTED)
    _formula_host(slide, "[[PPT_NATIVE_MATH:target]]", "Math host target", 6.03, 3.56, 6.41, 0.82)

    _text_box(slide, 5.25, 4.73, 0.78, 0.34, "Sum", size=20, bold=True, color=GREEN)
    _formula_host(
        slide,
        "[[PPT_NATIVE_MATH:identity]]",
        "Math host identity",
        6.03,
        4.43,
        6.41,
        0.96,
        fill=PALE_GREEN,
        line=GREEN,
    )

    boundary = _card(slide, 5.30, 5.61, 7.14, 0.78, fill=AMBER, line=RGBColor(0xD9, 0x77, 0x06))
    boundary.name = "Teacher runtime boundary"
    _set_text(
        boundary,
        "Teacher only: four profiles are offline. Runtime keeps one masked argmax and no coordinator.",
        size=20,
        color=INK,
        align=PP_ALIGN.CENTER,
        margin=0.08,
    )

    # Keep only the pilot slide while retaining its original layout/master.
    slide_ids = prs.slides._sldIdLst
    for item in list(slide_ids)[:2]:
        slide_ids.remove(item)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    print(build())
