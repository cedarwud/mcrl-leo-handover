#!/usr/bin/env bash
# build_ris.sh — repo-local wrapper that produces the ris-style .docx for the
# MC thesis WITHOUT editing any thesis-mc/*.md source.
#
# Pipeline:
#   1. copy the 4 chapter sources + REFERENCES.md, run ris_preprocess.py on each
#      (B1 \tag eq-numbers, B2 glued-pair split, references trim) -> a temp dir.
#   2. pandoc via the to-ris-docx skill's md2docx.sh (reference = ris-style.docx).
#   3. ris_postprocess.py on the output docx (B4 A4 pgSz + ris pgMar, B5 footer
#      page numbers).
#
# Sources are READ-ONLY; only COPIES are transformed (a translation workflow is
# concurrently reading the .md sources). Output goes to thesis-mc/outputs/.
#
# Usage:  build_ris.sh [OUTPUT_DIR]   (default: <repo>/thesis-mc/outputs)
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"          # thesis-mc/tools
DEFAULT_SRC="$(cd "$HERE/.." && pwd)"           # live thesis-mc
SRC="${THESIS_MC_SOURCE_DIR:-$DEFAULT_SRC}"
SRC="$(cd "$SRC" && pwd)"
DEFAULT_REPO="$(cd "$DEFAULT_SRC/.." && pwd)"   # live repo root
REPO="${THESIS_REPO_DIR:-$DEFAULT_REPO}"
REPO="$(cd "$REPO" && pwd)"
SKILL="$HOME/.claude/skills/to-ris-docx"

OUTDIR="${1:-$SRC/outputs}"
mkdir -p "$OUTDIR"
OUT="$OUTDIR/mcrl-thesis-ZH.docx"

PY="$REPO/.venv/bin/python"
[[ -x "$PY" ]] || PY="$(command -v python3)"

[[ -f "$SKILL/md2docx.sh" ]] || { echo "error: to-ris-docx skill missing at $SKILL" >&2; exit 1; }

BUILD="$(mktemp -d)"
trap 'rm -rf "$BUILD"' EXIT

# 1. preprocess COPIES (sources untouched)
"$PY" "$HERE/ris_preprocess.py" "$SRC/mc-modqn-base.md"           "$BUILD/mc-modqn-base.md"
"$PY" "$HERE/ris_preprocess.py" "$SRC/ch4-method.md"              "$BUILD/ch4-method.md"
"$PY" "$HERE/ris_preprocess.py" "$SRC/ch5-experimental-result.md" "$BUILD/ch5-experimental-result.md"
"$PY" "$HERE/ris_preprocess.py" "$SRC/ch6-conclusion.md"          "$BUILD/ch6-conclusion.md"
"$PY" "$HERE/ris_preprocess.py" --references "$SRC/REFERENCES.md" "$BUILD/REFERENCES.md"

# 1b. copy figures so the markdown's relative image paths (figures/figN.png)
#     resolve when pandoc runs with cwd=$BUILD (sources live in a temp dir).
[[ -d "$SRC/figures" ]] && cp -r "$SRC/figures" "$BUILD/figures"

# 2. pandoc (run from $BUILD so `figures/figN.png` resolves; order = thesis order, references last)
( cd "$BUILD" && bash "$SKILL/md2docx.sh" -o "$OUT" \
  mc-modqn-base.md \
  ch4-method.md \
  ch5-experimental-result.md \
  ch6-conclusion.md \
  REFERENCES.md )

# 3. postprocess docx geometry + page numbers
"$PY" "$HERE/ris_postprocess.py" "$OUT"
"$PY" "$HERE/bilingual_postprocess.py" --watermark-only "$OUT"

# 4. replace the Markdown-generated cover with the canonical cover DOCX body
COVER="${THESIS_MC_COVER_DOCX:-$SRC/outputs/thesis-cover.docx}"
[[ -f "$COVER" ]] || { echo "error: canonical thesis cover missing at $COVER" >&2; exit 1; }
"$PY" "$HERE/apply_cover.py" "$COVER" "$OUT"

echo "BUILT -> $OUT"
