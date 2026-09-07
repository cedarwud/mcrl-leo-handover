#!/usr/bin/env bash
# build_bilingual.sh — produce the EN->ZH interleaved bilingual MC thesis .docx.
#
# Same conversion pipeline as build_ris.sh, but the inputs are the bilingual
# chapter files assembled by build_bilingual.py:
#   1. build_bilingual.py  -> thesis-mc/en/bilingual/bi-*.md  (interleaved EN/ZH)
#   2. ris_preprocess.py on COPIES of each bilingual file (B1 \tag eq numbers,
#      B2 glued-pair split) + --references trim on REFERENCES.md -> a temp dir.
#   3. pandoc via the to-ris-docx skill's md2docx.sh (reference = ris-style.docx).
#   4. ris_postprocess.py on the output docx (B4 A4 pgSz + ris pgMar, B5 footer
#      page numbers).
#
# Thesis sources (thesis-mc/*.md, thesis-mc/en/*.en.md) are READ-ONLY; only the
# bilingual copies + transformed temp copies are written. Output goes to
# thesis-mc/outputs/.
#
# Usage:  build_bilingual.sh [OUTPUT_DIR]   (default: <repo>/thesis-mc/outputs)
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"          # thesis-mc/tools
DEFAULT_SRC="$(cd "$HERE/.." && pwd)"           # live thesis-mc
SRC="${THESIS_MC_SOURCE_DIR:-$DEFAULT_SRC}"
SRC="$(cd "$SRC" && pwd)"
DEFAULT_REPO="$(cd "$DEFAULT_SRC/.." && pwd)"   # live repo root
REPO="${THESIS_REPO_DIR:-$DEFAULT_REPO}"
REPO="$(cd "$REPO" && pwd)"
SKILL="$HOME/.claude/skills/to-ris-docx"
BIDIR="$SRC/en/bilingual"

OUTDIR="${1:-$SRC/outputs}"
mkdir -p "$OUTDIR"
OUT="$OUTDIR/mcrl-thesis-bilingual.docx"

PY="$REPO/.venv/bin/python"
[[ -x "$PY" ]] || PY="$(command -v python3)"

[[ -f "$SKILL/md2docx.sh" ]] || { echo "error: to-ris-docx skill missing at $SKILL" >&2; exit 1; }

# 1. assemble the bilingual chapter files (sources untouched)
"$PY" "$HERE/build_bilingual.py" "$SRC" "$BIDIR"

BUILD="$(mktemp -d)"
trap 'rm -rf "$BUILD"' EXIT

# 1b. copy figures so the bilingual markdown's relative image paths
#     (figures/figN.png) resolve when pandoc runs with cwd=$BUILD.
[[ -d "$SRC/figures" ]] && cp -r "$SRC/figures" "$BUILD/figures"

# 2. preprocess COPIES of the bilingual files (B1 \tag, B2 glued split)
"$PY" "$HERE/ris_preprocess.py" "$BIDIR/bi-mc-modqn-base.md"           "$BUILD/bi-mc-modqn-base.md"
"$PY" "$HERE/ris_preprocess.py" "$BIDIR/bi-ch4-method.md"              "$BUILD/bi-ch4-method.md"
"$PY" "$HERE/ris_preprocess.py" "$BIDIR/bi-ch5-experimental-result.md" "$BUILD/bi-ch5-experimental-result.md"
"$PY" "$HERE/ris_preprocess.py" "$BIDIR/bi-ch6-conclusion.md"          "$BUILD/bi-ch6-conclusion.md"
"$PY" "$HERE/ris_preprocess.py" --references "$SRC/REFERENCES.md"      "$BUILD/REFERENCES.md"

# 3. pandoc (run from $BUILD so `figures/figN.png` resolves; order = thesis order, references last)
( cd "$BUILD" && bash "$SKILL/md2docx.sh" -o "$OUT" \
  bi-mc-modqn-base.md \
  bi-ch4-method.md \
  bi-ch5-experimental-result.md \
  bi-ch6-conclusion.md \
  REFERENCES.md )

# 4. postprocess docx geometry + page numbers
"$PY" "$HERE/ris_postprocess.py" "$OUT"

# 5. bilingual-specific ris fidelity: body spacing, table autofit, ref indent
"$PY" "$HERE/bilingual_postprocess.py" "$OUT"

# 6. replace the generated front matter with the canonical cover DOCX body
COVER="${THESIS_MC_COVER_DOCX:-$SRC/outputs/thesis-cover.docx}"
[[ -f "$COVER" ]] || { echo "error: canonical thesis cover missing at $COVER" >&2; exit 1; }
"$PY" "$HERE/apply_cover.py" "$COVER" "$OUT"

echo "BUILT -> $OUT"
