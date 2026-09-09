#!/usr/bin/env python3
"""Native OfficeMath injection for the V0.25 deck skeleton.

Why this file exists
--------------------
The V0.23 pilot build (`pilot-build/build_pilot.py` + `native-formulas.json`)
authored `[[PPT_NATIVE_MATH:<id>]]` markers into named autoshapes and then
handed the deck to a second stage that replaced each marker paragraph with a
native `a14:m` / OMML math zone.  That second stage lived in
`/home/u24/pptx-craft/`, which is **not present on this machine**.  This module
reimplements it against the exact OMML dialect recovered from the shipped
artefact `pilot-build/lc-srs-pilot-native-v4.pptx` (slide 3), so the emitted
XML matches the V0.23 pipeline structure element for element:

    <a:p><a:pPr algn="ctr"/>
      <a14:m><m:oMathPara><m:oMath> ... </m:oMath></m:oMathPara></a14:m>
    </a:p>

with every math run carrying `a:rPr` (`sz`, `i`, `dirty`) plus explicit
`a:latin` / `a:ea` / `a:cs` typefaces.

The manifest schema (`native-formulas-v025.json`) is the V0.23 schema
unchanged: id, slide, shape_name, match_text, latex, font_face, font_size_pt,
force_italic, align, insets_in, require_autoshape.

Scope: this converter accepts the bounded LaTeX subset actually used by the
deck manifest.  It is deliberately not a general LaTeX engine; unknown macros
fail closed with `MathError` rather than silently dropping tokens.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

A = "http://schemas.openxmlformats.org/drawingml/2006/main"
A14 = "http://schemas.microsoft.com/office/drawing/2010/main"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NSMAP = {"a": A, "a14": A14, "m": M, "p": P}

# Times New Roman has no Mathematical Script / Double-Struck block.  Those two
# glyph classes -- and only those -- get a per-run Cambria Math override so the
# calligraphic set letters the symbol authority relies on (script K vs upright
# capital K) survive; everything else stays Times New Roman.
MATH_GLYPH_FONT = "Cambria Math"

SCRIPT = {
    "A": "\U0001d49c", "B": "ℬ", "C": "\U0001d49e", "D": "\U0001d49f",
    "E": "ℰ", "F": "ℱ", "G": "\U0001d4a2", "H": "ℋ",
    "I": "ℐ", "J": "\U0001d4a5", "K": "\U0001d4a6", "L": "ℒ",
    "M": "ℳ", "N": "\U0001d4a9", "O": "\U0001d4aa", "P": "\U0001d4ab",
    "Q": "\U0001d4ac", "R": "ℛ", "S": "\U0001d4ae", "T": "\U0001d4af",
    "U": "\U0001d4b0", "V": "\U0001d4b1", "W": "\U0001d4b2", "X": "\U0001d4b3",
    "Y": "\U0001d4b4", "Z": "\U0001d4b5",
}
BLACKBOARD = {"1": "\U0001d7d9", "R": "ℝ", "N": "ℕ"}

MACROS = {
    # Greek -- all present in Times New Roman.
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ",
    "epsilon": "ε", "zeta": "ζ", "eta": "η", "theta": "θ",
    "kappa": "κ", "lambda": "λ", "mu": "μ", "nu": "ν",
    "xi": "ξ", "pi": "π", "rho": "ρ", "sigma": "σ",
    "tau": "τ", "phi": "φ", "varphi": "φ", "chi": "χ",
    "psi": "ψ", "omega": "ω",
    "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ",
    "Xi": "Ξ", "Pi": "Π", "Sigma": "Σ", "Upsilon": "Υ",
    "Phi": "Φ", "Psi": "Ψ", "Omega": "Ω",
    # Relations and operators.
    "ge": "≥", "le": "≤", "ne": "≠", "neq": "≠",
    "in": "∈", "notin": "∉", "subseteq": "⊆", "subset": "⊂",
    "cdot": "⋅", "times": "×", "pm": "±", "approx": "≈",
    "to": "→", "rightarrow": "→", "mapsto": "↦",
    "varnothing": "∅", "emptyset": "∅", "infty": "∞",
    "star": "⋆", "circ": "∘", "equiv": "≡",
    "{": "{", "}": "}", "|": "|", "%": "%", "&": "&", "_": "_",
}
UPRIGHT_FUNCTIONS = {"min", "max", "log", "arg", "mean", "sign", "exp", "dB"}
SPACING = {",": " ", ";": " ", "!": "", " ": " ", "quad": "  ", "qquad": "    "}
DELIMS = {"(": "(", ")": ")", "[": "[", "]": "]", "\\{": "{", "\\}": "}",
          "\\lvert": "|", "\\rvert": "|", "|": "|", ".": ""}


class MathError(ValueError):
    """Raised when the manifest contains LaTeX outside the accepted subset."""


# --------------------------------------------------------------------------
# AST
# --------------------------------------------------------------------------

@dataclass
class Run:
    text: str
    italic: bool = True
    bold: bool = False
    math_font: bool = False


@dataclass
class Row:
    items: list = field(default_factory=list)


@dataclass
class Frac:
    num: object
    den: object


@dataclass
class Nary:
    char: str
    sub: object
    sup: object
    body: object


@dataclass
class Delim:
    beg: str
    end: str
    body: object


@dataclass
class Script:
    base: object
    sub: object = None
    sup: object = None


# --------------------------------------------------------------------------
# Tokenizer + parser
# --------------------------------------------------------------------------

TOKEN_RE = re.compile(r"\\[A-Za-z]+|\\.|[{}_^]|\s+|.", re.DOTALL)


def _tokenize(latex: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(latex) if not (t.isspace() and t != " ")]


class _Parser:
    def __init__(self, tokens: list[str], latex: str):
        self.t = tokens
        self.i = 0
        self.latex = latex

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def next(self):
        tok = self.peek()
        self.i += 1
        return tok

    def fail(self, msg: str):
        raise MathError(f"{msg} (at token {self.i} of {self.latex!r})")

    # -- entry -------------------------------------------------------------
    def parse(self):
        row = self.parse_row(stop=None)
        if self.i < len(self.t):
            self.fail(f"unconsumed token {self.peek()!r}")
        return row

    def parse_row(self, stop):
        items = []
        while True:
            tok = self.peek()
            if tok is None:
                break
            if stop is not None and tok == stop:
                break
            if tok == "}":
                break
            if tok in ("_", "^"):
                self.next()
                arg = self.parse_atom()
                if not items:
                    self.fail("script with no base")
                base = items.pop()
                if isinstance(base, Script):
                    if tok == "_" and base.sub is None:
                        base.sub = arg
                    elif tok == "^" and base.sup is None:
                        base.sup = arg
                    else:
                        self.fail("duplicate script")
                    items.append(base)
                else:
                    items.append(Script(base, sub=arg if tok == "_" else None,
                                        sup=arg if tok == "^" else None))
                continue
            if tok == r"\right":
                break
            items.append(self.parse_atom())
        return Row(items)

    def parse_group(self):
        if self.peek() != "{":
            return self.parse_atom()
        self.next()
        row = self.parse_row(stop=None)
        if self.next() != "}":
            self.fail("unterminated group")
        return row

    def parse_atom(self):
        tok = self.next()
        if tok is None:
            self.fail("unexpected end of input")

        if tok == "{":
            row = self.parse_row(stop=None)
            if self.next() != "}":
                self.fail("unterminated group")
            return row

        if tok == r"\frac":
            return Frac(self.parse_group(), self.parse_group())

        if tok == r"\sum":
            return self._nary("∑")
        if tok == r"\prod":
            return self._nary("∏")
        if tok == r"\int":
            return self._nary("∫")

        if tok == r"\left":
            beg_tok = self.next()
            beg = DELIMS.get(beg_tok)
            if beg is None:
                self.fail(f"unsupported \\left delimiter {beg_tok!r}")
            body = self.parse_row(stop=None)
            if self.next() != r"\right":
                self.fail("unmatched \\left")
            end_tok = self.next()
            end = DELIMS.get(end_tok)
            if end is None:
                self.fail(f"unsupported \\right delimiter {end_tok!r}")
            return Delim(beg, end, body)

        if tok in (r"\mathcal", r"\mathscr"):
            return self._alphabet(SCRIPT, tok)
        if tok == r"\mathbb":
            return self._alphabet(BLACKBOARD, tok)
        if tok == r"\mathrm" or tok == r"\operatorname" or tok == r"\text":
            return self._styled(self.parse_group(), italic=False)
        if tok == r"\mathbf":
            return self._styled(self.parse_group(), bold=True)

        if tok.startswith("\\"):
            name = tok[1:]
            if name in UPRIGHT_FUNCTIONS:
                return Run(name, italic=False)
            if tok[1:] in SPACING or (len(tok) == 2 and tok[1] in SPACING):
                key = name if name in SPACING else tok[1]
                text = SPACING[key]
                return Run(text, italic=False) if text else Row([])
            if name in MACROS:
                return Run(MACROS[name])
            if tok[1:] in MACROS:
                return Run(MACROS[tok[1:]])
            self.fail(f"unsupported macro {tok!r}")

        if tok == "-":
            return Run("−")
        if tok == " ":
            return Run(" ", italic=False)
        return Run(tok)

    def _nary(self, char: str):
        sub = sup = None
        while self.peek() in ("_", "^"):
            marker = self.next()
            arg = self.parse_group()
            if marker == "_":
                sub = arg
            else:
                sup = arg
        body = self.parse_atom()
        # carry postfix scripts on the nary body (e.g. \sum_i P^{N})
        while self.peek() in ("_", "^"):
            marker = self.next()
            arg = self.parse_atom()
            if isinstance(body, Script):
                if marker == "_":
                    body.sub = arg
                else:
                    body.sup = arg
            else:
                body = Script(body, sub=arg if marker == "_" else None,
                              sup=arg if marker == "^" else None)
        return Nary(char, sub, sup, body)

    def _alphabet(self, table: dict, tok: str):
        arg = self.parse_group()
        letters = _flatten_text(arg)
        out = []
        for ch in letters:
            if ch not in table:
                self.fail(f"{tok}{{{ch}}} has no mapped glyph")
            out.append(Run(table[ch], italic=False, math_font=True))
        return out[0] if len(out) == 1 else Row(out)

    @staticmethod
    def _styled(node, *, italic: bool = True, bold: bool = False):
        def walk(n):
            if isinstance(n, Run):
                n.italic = italic
                n.bold = bold
            elif isinstance(n, Row):
                for c in n.items:
                    walk(c)
            elif isinstance(n, Script):
                for c in (n.base, n.sub, n.sup):
                    if c is not None:
                        walk(c)
        walk(node)
        return node


def _flatten_text(node) -> str:
    if isinstance(node, Run):
        return node.text
    if isinstance(node, Row):
        return "".join(_flatten_text(c) for c in node.items)
    raise MathError("expected a plain letter group")


def parse_latex(latex: str):
    return _Parser(_tokenize(latex), latex).parse()


# --------------------------------------------------------------------------
# OMML emitter -- dialect recovered from lc-srs-pilot-native-v4.pptx
# --------------------------------------------------------------------------

def _q(ns: str, local: str) -> str:
    return f"{{{ns}}}{local}"


class _Emitter:
    def __init__(self, *, font_face: str, size_pt: float, force_italic: bool):
        self.font = font_face
        self.sz = str(int(round(size_pt * 100)))
        self.force_italic = force_italic

    def run_props(self, node: Run) -> etree._Element:
        rpr = etree.Element(_q(A, "rPr"))
        rpr.set("lang", "en-US")
        rpr.set("altLang", "en-US")
        rpr.set("sz", self.sz)
        if node.bold:
            rpr.set("b", "1")
        rpr.set("i", "1" if (node.italic and self.force_italic) else "0")
        rpr.set("dirty", "0")
        face = MATH_GLYPH_FONT if node.math_font else self.font
        for tag in ("latin", "ea", "cs"):
            etree.SubElement(rpr, _q(A, tag)).set("typeface", face)
        return rpr

    def run(self, node: Run) -> etree._Element:
        r = etree.Element(_q(M, "r"))
        r.append(self.run_props(node))
        t = etree.SubElement(r, _q(M, "t"))
        t.text = node.text
        if node.text != node.text.strip():
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        return r

    def emit_into(self, parent: etree._Element, node) -> None:
        if node is None:
            return
        if isinstance(node, Run):
            if node.text == "":
                return
            parent.append(self.run(node))
        elif isinstance(node, Row):
            for child in node.items:
                self.emit_into(parent, child)
        elif isinstance(node, Frac):
            f = etree.SubElement(parent, _q(M, "f"))
            fpr = etree.SubElement(f, _q(M, "fPr"))
            etree.SubElement(fpr, _q(M, "type")).set(_q(M, "val"), "bar")
            self.emit_into(etree.SubElement(f, _q(M, "num")), node.num)
            self.emit_into(etree.SubElement(f, _q(M, "den")), node.den)
        elif isinstance(node, Delim):
            d = etree.SubElement(parent, _q(M, "d"))
            dpr = etree.SubElement(d, _q(M, "dPr"))
            etree.SubElement(dpr, _q(M, "begChr")).set(_q(M, "val"), node.beg)
            etree.SubElement(dpr, _q(M, "sepChr")).set(_q(M, "val"), "")
            etree.SubElement(dpr, _q(M, "endChr")).set(_q(M, "val"), node.end)
            etree.SubElement(dpr, _q(M, "grow"))
            self.emit_into(etree.SubElement(d, _q(M, "e")), node.body)
        elif isinstance(node, Nary):
            n = etree.SubElement(parent, _q(M, "nary"))
            npr = etree.SubElement(n, _q(M, "naryPr"))
            etree.SubElement(npr, _q(M, "chr")).set(_q(M, "val"), node.char)
            etree.SubElement(npr, _q(M, "limLoc")).set(_q(M, "val"), "undOvr")
            etree.SubElement(npr, _q(M, "subHide")).set(
                _q(M, "val"), "off" if node.sub is not None else "on")
            etree.SubElement(npr, _q(M, "supHide")).set(
                _q(M, "val"), "off" if node.sup is not None else "on")
            sub = etree.SubElement(n, _q(M, "sub"))
            if node.sub is not None:
                self.emit_into(sub, node.sub)
            else:  # the V0.23 artefact keeps a zero-width placeholder run
                sub.append(self.run(Run("​")))
            sup = etree.SubElement(n, _q(M, "sup"))
            if node.sup is not None:
                self.emit_into(sup, node.sup)
            else:
                sup.append(self.run(Run("​")))
            self.emit_into(etree.SubElement(n, _q(M, "e")), node.body)
        elif isinstance(node, Script):
            if node.sub is not None and node.sup is not None:
                tag, parts = "sSubSup", (("e", node.base), ("sub", node.sub), ("sup", node.sup))
            elif node.sub is not None:
                tag, parts = "sSub", (("e", node.base), ("sub", node.sub))
            elif node.sup is not None:
                tag, parts = "sSup", (("e", node.base), ("sup", node.sup))
            else:
                self.emit_into(parent, node.base)
                return
            s = etree.SubElement(parent, _q(M, tag))
            for name, value in parts:
                self.emit_into(etree.SubElement(s, _q(M, name)), value)
        else:  # pragma: no cover - defensive
            raise MathError(f"cannot emit node {node!r}")

    def omath(self, ast) -> etree._Element:
        omath = etree.Element(_q(M, "oMath"), nsmap={"m": M})
        self.emit_into(omath, ast)
        if len(omath) == 0:
            raise MathError("empty math zone")
        return omath


def latex_to_omath(latex: str, *, font_face: str, font_size_pt: float,
                   force_italic: bool = True) -> etree._Element:
    emitter = _Emitter(font_face=font_face, size_pt=font_size_pt,
                       force_italic=force_italic)
    return emitter.omath(parse_latex(latex))


# --------------------------------------------------------------------------
# Injection into an authored deck
# --------------------------------------------------------------------------

ALIGN = {"center": "ctr", "left": "l", "right": "r"}


def _iter_shapes(shapes):
    for shape in shapes:
        yield shape
        if shape.shape_type is not None and getattr(shape, "shapes", None) is not None:
            yield from _iter_shapes(shape.shapes)


def inject(prs, manifest: list[dict]) -> list[dict]:
    """Replace every marker paragraph with a native a14:m / OMML math zone."""
    slides = list(prs.slides)
    report: list[dict] = []

    for spec in manifest:
        slide_no = int(spec["slide"])
        if not 1 <= slide_no <= len(slides):
            raise MathError(f"formula {spec['id']}: slide {slide_no} out of range")
        slide = slides[slide_no - 1]

        target = None
        for shape in _iter_shapes(slide.shapes):
            if shape.name == spec["shape_name"]:
                target = shape
                break
        if target is None:
            raise MathError(f"formula {spec['id']}: no shape named {spec['shape_name']!r} "
                            f"on slide {slide_no}")
        if spec.get("require_autoshape", True):
            if target._element.find(_q(P, "spPr") + "/" + _q(A, "prstGeom")) is None:
                raise MathError(f"formula {spec['id']}: host shape is not an autoshape")

        tx_body = target._element.find(_q(P, "txBody"))
        if tx_body is None:
            raise MathError(f"formula {spec['id']}: host shape has no text body")

        marker = spec["match_text"]
        para = None
        for candidate in tx_body.findall(_q(A, "p")):
            text = "".join(t.text or "" for t in candidate.iter(_q(A, "t")))
            if marker in text:
                para = candidate
                break
        if para is None:
            raise MathError(f"formula {spec['id']}: marker {marker!r} not found in "
                            f"{spec['shape_name']!r}")

        for child in list(para):
            para.remove(child)
        ppr = etree.SubElement(para, _q(A, "pPr"))
        ppr.set("algn", ALIGN[spec.get("align", "center")])
        wrapper = etree.SubElement(para, _q(A14, "m"), nsmap={"a14": A14, "m": M})
        omath_para = etree.SubElement(wrapper, _q(M, "oMathPara"))
        omath_para.append(latex_to_omath(
            spec["latex"],
            font_face=spec.get("font_face", "Times New Roman"),
            font_size_pt=spec.get("font_size_pt", 20),
            force_italic=bool(spec.get("force_italic", True)),
        ))
        end = etree.SubElement(para, _q(A, "endParaRPr"))
        end.set("lang", "en-US")
        end.set("altLang", "en-US")
        end.set("sz", str(int(round(spec.get("font_size_pt", 20) * 100))))
        end.set("dirty", "0")

        insets = spec.get("insets_in")
        if insets:
            body_pr = tx_body.find(_q(A, "bodyPr"))
            if body_pr is not None:
                left, top, right, bottom = insets
                for attr, inches in (("lIns", left), ("tIns", top),
                                     ("rIns", right), ("bIns", bottom)):
                    body_pr.set(attr, str(int(round(inches * 914400))))

        report.append({
            "id": spec["id"],
            "slide": slide_no,
            "shape_name": spec["shape_name"],
            "latex": spec["latex"],
            "omml_runs": len(omath_para.findall(f".//{_q(M, 't')}")),
        })

    return report


def load_manifest(path: str | Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data["formulas"]


if __name__ == "__main__":  # smoke test of the converter alone
    import sys
    for spec in load_manifest(Path(__file__).with_name("native-formulas-v025.json")):
        omath = latex_to_omath(spec["latex"], font_face="Times New Roman",
                               font_size_pt=20)
        text = "".join(t.text or "" for t in omath.iter(_q(M, "t")))
        print(f"{spec['id']:<14} {text}")
    sys.exit(0)
