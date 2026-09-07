#!/usr/bin/env bash
# build_en.sh — English-only ris-style .docx from thesis-mc/en/*.en.md.
# Mirrors build_ris.sh (same ris_preprocess + md2docx-on-copies + ris_postprocess
# pipeline, figures copied so figures/figN.png resolves), but the inputs are the
# English chapter files and references stay the shared REFERENCES.md. The EN
# base source intentionally retains bilingual front matter/abstract blocks for
# the bilingual workflow; assemble_english.py removes those blocks from the
# temporary English-only copy and fails if any visible CJK remains.
# Sources are READ-ONLY; only COPIES are transformed.
# Usage:  build_en.sh [OUTPUT_DIR]   (default: <repo>/thesis-mc/outputs)
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
DEFAULT_SRC="$(cd "$HERE/.." && pwd)"
SRC="${THESIS_MC_SOURCE_DIR:-$DEFAULT_SRC}"
SRC="$(cd "$SRC" && pwd)"
DEFAULT_REPO="$(cd "$DEFAULT_SRC/.." && pwd)"
REPO="${THESIS_REPO_DIR:-$DEFAULT_REPO}"
REPO="$(cd "$REPO" && pwd)"
SKILL="$HOME/.claude/skills/to-ris-docx"

OUTDIR="${1:-$SRC/outputs}"
mkdir -p "$OUTDIR"
OUT="$OUTDIR/mcrl-thesis-EN.docx"

PY="$REPO/.venv/bin/python"
[[ -x "$PY" ]] || PY="$(command -v python3)"
[[ -f "$SKILL/md2docx.sh" ]] || { echo "error: to-ris-docx skill missing at $SKILL" >&2; exit 1; }

BUILD="$(mktemp -d)"
trap 'rm -rf "$BUILD"' EXIT

# 1. assemble the pure-English base, then preprocess COPIES of all EN chapters
"$PY" "$HERE/assemble_english.py" assemble-base \
  "$SRC/en/mc-modqn-base.en.md" "$BUILD/mc-modqn-base.assembled.md"
"$PY" "$HERE/ris_preprocess.py" "$BUILD/mc-modqn-base.assembled.md"     "$BUILD/mc-modqn-base.md"
"$PY" "$HERE/ris_preprocess.py" "$SRC/en/ch4-method.en.md"              "$BUILD/ch4-method.md"
"$PY" "$HERE/ris_preprocess.py" "$SRC/en/ch5-experimental-result.en.md" "$BUILD/ch5-experimental-result.md"
"$PY" "$HERE/ris_preprocess.py" "$SRC/en/ch6-conclusion.en.md"          "$BUILD/ch6-conclusion.md"
"$PY" "$HERE/ris_preprocess.py" --references "$SRC/REFERENCES.md"        "$BUILD/REFERENCES.md"
"$PY" "$HERE/assemble_english.py" check \
  "$BUILD/mc-modqn-base.md" \
  "$BUILD/ch4-method.md" \
  "$BUILD/ch5-experimental-result.md" \
  "$BUILD/ch6-conclusion.md" \
  "$BUILD/REFERENCES.md"

# 1b. copy figures so relative image paths (figures/figN.png, figures/results/*) resolve
[[ -d "$SRC/figures" ]] && cp -r "$SRC/figures" "$BUILD/figures"

# 2. pandoc via the skill (run from $BUILD so figures/ resolves; references last)
( cd "$BUILD" && bash "$SKILL/md2docx.sh" -o "$OUT" \
  mc-modqn-base.md \
  ch4-method.md \
  ch5-experimental-result.md \
  ch6-conclusion.md \
  REFERENCES.md )

# 3. postprocess docx geometry + page numbers + table borders + caption styling
"$PY" "$HERE/ris_postprocess.py" "$OUT"
"$PY" "$HERE/bilingual_postprocess.py" --watermark-only "$OUT"

# 4. use the same canonical bilingual cover page as every thesis version
COVER="${THESIS_MC_COVER_DOCX:-$SRC/outputs/thesis-cover.docx}"
[[ -f "$COVER" ]] || { echo "error: canonical thesis cover missing at $COVER" >&2; exit 1; }
"$PY" "$HERE/apply_cover.py" "$COVER" "$OUT"

echo "BUILT -> $OUT"
