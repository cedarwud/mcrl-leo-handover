#!/usr/bin/env bash
# build_all.sh — coherently build the current ZH, EN, and bilingual thesis DOCX
# files from one unchanged source set, then write a source/output receipt.
#
# The bilingual DOCX is not made by merging two DOCX packages. It is assembled
# from the exact ZH and EN Markdown authorities used by build_ris.sh and
# build_en.sh. This wrapper proves that:
#   1. all manuscript, reference, figure, and build-tool inputs stayed unchanged
#      across the three builds;
#   2. the generated bi-*.md files byte-match a second deterministic regeneration
#      from those same ZH/EN inputs; and
#   3. only after all checks pass are the three DOCX files published, with the
#      receipt invalidated during replacement and restored last.
#
# Usage: build_all.sh [OUTPUT_DIR]
# Default: <repo>/thesis-mc/outputs
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$(cd "$HERE/.." && pwd)"
REPO="$(cd "$SRC/.." && pwd)"
SKILL="$HOME/.claude/skills/to-ris-docx"

OUTDIR="${1:-$SRC/outputs}"
PY="$REPO/.venv/bin/python"
[[ -x "$PY" ]] || PY="$(command -v python3)"
PY_BIN="$(readlink -f "$PY")"
PANDOC_BIN="$(command -v pandoc)"
PYTHON_VERSION="$("$PY" -VV 2>&1 | tr '\n' ' ')"
PANDOC_VERSION="$("$PANDOC_BIN" --version | head -n 1)"

BUILD="$(mktemp -d)"
trap 'rm -rf "$BUILD"' EXIT
STAGE="$BUILD/stage"
SNAPSHOT="$BUILD/source-snapshot"
VERIFY_BI="$BUILD/bilingual-verify"
DOCX_VERIFY_REPORT="$BUILD/docx-structure-parity.txt"
SOURCE_BEFORE="$BUILD/source-before.sha256"
SOURCE_SNAPSHOT="$BUILD/source-snapshot.sha256"
SOURCE_SNAPSHOT_AFTER="$BUILD/source-snapshot-after.sha256"
SOURCE_AFTER="$BUILD/source-after.sha256"
TOOLS_BEFORE="$BUILD/tools-before.sha256"
TOOLS_AFTER="$BUILD/tools-after.sha256"
mkdir -p "$STAGE" "$SNAPSHOT" "$VERIFY_BI" "$OUTDIR"

# Serialize cooperating three-version builds for the same output directory.
# Lock the directory inode itself so a successful build leaves no runtime file
# beside the four published deliverables.
exec 9<"$OUTDIR"
flock -n 9 || {
  echo "error: another MC thesis three-version build is active in $OUTDIR" >&2
  exit 1
}

TEXT_INPUTS=(
  "mc-modqn-base.md"
  "ch4-method.md"
  "ch5-experimental-result.md"
  "ch6-conclusion.md"
  "en/mc-modqn-base.en.md"
  "en/ch4-method.en.md"
  "en/ch5-experimental-result.en.md"
  "en/ch6-conclusion.en.md"
  "en/abstract-bilingual-SAMPLE.md"
  "REFERENCES.md"
  "assets/ntpu_header.xml"
  "assets/ntpu-watermark.jpeg"
  "outputs/thesis-cover.docx"
)

TOOL_INPUTS=(
  "assemble_english.py"
  "build_all.sh"
  "build_ris.sh"
  "build_en.sh"
  "build_bilingual.sh"
  "build_bilingual.py"
  "ris_preprocess.py"
  "ris_postprocess.py"
  "test_ris_postprocess.py"
  "test_build_bilingual.py"
  "bilingual_postprocess.py"
  "apply_cover.py"
  "test_apply_cover.py"
  "verify_three_docx.py"
)

BI_OUTPUTS=(
  "bi-mc-modqn-base.md"
  "bi-ch4-method.md"
  "bi-ch5-experimental-result.md"
  "bi-ch6-conclusion.md"
)

DOCX_OUTPUTS=(
  "mcrl-thesis-ZH.docx"
  "mcrl-thesis-EN.docx"
  "mcrl-thesis-bilingual.docx"
)

hash_sources() {
  local root="$1"
  (
    cd "$root"
    {
      printf '%s\n' "${TEXT_INPUTS[@]}"
      find figures \( -type f -o -type l \) \
        ! -path '*/__pycache__/*' ! -name '*.pyc' -print
    } | LC_ALL=C sort | while IFS= read -r path; do
      sha256sum -- "$path"
    done
  )
}

hash_tools() {
  (
    cd "$HERE"
    for path in "${TOOL_INPUTS[@]}"; do
      sha256sum -- "$path"
    done
  )
  sha256sum -- "$SKILL/md2docx.sh" "$SKILL/ris-style.docx"
  sha256sum -- "$PY_BIN" "$PANDOC_BIN"
}

snapshot_sources() {
  local path
  for path in "${TEXT_INPUTS[@]}"; do
    mkdir -p "$SNAPSHOT/$(dirname "$path")"
    cp -- "$SRC/$path" "$SNAPSHOT/$path"
  done
  cp -a -- "$SRC/figures" "$SNAPSHOT/figures"
  mkdir -p "$SNAPSHOT/en/bilingual"
  # Files are read-only; directories stay writable so wrappers can copy the
  # tree into their own temp dirs and clean those dirs normally. The post-build
  # snapshot hash is the fail-closed guard against replacement via directory
  # writes.
  find "$SNAPSHOT" -type f -exec chmod a-w {} +
}

hash_sources "$SRC" > "$SOURCE_BEFORE"
hash_tools > "$TOOLS_BEFORE"
"$PY" -B "$HERE/test_build_bilingual.py"
"$PY" -B "$HERE/test_ris_postprocess.py"
"$PY" -B "$HERE/test_apply_cover.py"
snapshot_sources
hash_sources "$SNAPSHOT" > "$SOURCE_SNAPSHOT"
cmp -- "$SOURCE_BEFORE" "$SOURCE_SNAPSHOT"

# Build into a private staging directory. No public DOCX is replaced unless all
# three builds and all coherence checks finish successfully. Every wrapper reads
# the immutable temporary snapshot rather than rereading the live source tree.
THESIS_MC_SOURCE_DIR="$SNAPSHOT" THESIS_REPO_DIR="$REPO" \
THESIS_MC_COVER_DOCX="$SNAPSHOT/outputs/thesis-cover.docx" \
  bash "$HERE/build_ris.sh" "$STAGE"
THESIS_MC_SOURCE_DIR="$SNAPSHOT" THESIS_REPO_DIR="$REPO" \
THESIS_MC_COVER_DOCX="$SNAPSHOT/outputs/thesis-cover.docx" \
  bash "$HERE/build_en.sh" "$STAGE"
THESIS_MC_SOURCE_DIR="$SNAPSHOT" THESIS_REPO_DIR="$REPO" \
THESIS_MC_COVER_DOCX="$SNAPSHOT/outputs/thesis-cover.docx" \
THESIS_MC_ASSET_DIR="$SNAPSHOT/assets" \
  bash "$HERE/build_bilingual.sh" "$STAGE"

# Regenerate the bilingual Markdown a second time and require byte identity with
# the files that build_bilingual.sh just consumed.
"$PY" "$HERE/build_bilingual.py" "$SNAPSHOT" "$VERIFY_BI"
for name in "${BI_OUTPUTS[@]}"; do
  cmp -- "$SNAPSHOT/en/bilingual/$name" "$VERIFY_BI/$name"
done

for name in "${DOCX_OUTPUTS[@]}"; do
  [[ -s "$STAGE/$name" ]] || {
    echo "error: missing or empty staged output: $STAGE/$name" >&2
    exit 1
  }
done

"$PY" "$HERE/verify_three_docx.py" \
  "$SNAPSHOT" \
  "$STAGE/mcrl-thesis-ZH.docx" \
  "$STAGE/mcrl-thesis-EN.docx" \
  "$STAGE/mcrl-thesis-bilingual.docx" | tee "$DOCX_VERIFY_REPORT"

# Recheck the live inputs only after every staged-output validation has
# completed, immediately before publication.
hash_sources "$SNAPSHOT" > "$SOURCE_SNAPSHOT_AFTER"
hash_sources "$SRC" > "$SOURCE_AFTER"
hash_tools > "$TOOLS_AFTER"
cmp -- "$SOURCE_SNAPSHOT" "$SOURCE_SNAPSHOT_AFTER"
cmp -- "$SOURCE_BEFORE" "$SOURCE_AFTER"
cmp -- "$TOOLS_BEFORE" "$TOOLS_AFTER"

SOURCE_SET_SHA256="$(sha256sum "$SOURCE_BEFORE" | cut -d ' ' -f 1)"
TOOL_SET_SHA256="$(sha256sum "$TOOLS_BEFORE" | cut -d ' ' -f 1)"
RECEIPT="$STAGE/mcrl-thesis-build-receipt.txt"
{
  echo "MC thesis three-version build receipt"
  echo "built_at_utc=$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "source_set_sha256=$SOURCE_SET_SHA256"
  echo "tool_set_sha256=$TOOL_SET_SHA256"
  echo "python_version=$PYTHON_VERSION"
  echo "pandoc_version=$PANDOC_VERSION"
  echo "source_snapshot_byte_identity=PASS"
  echo "snapshot_inputs_stable_during_build=PASS"
  echo "source_stable_during_build=PASS"
  echo "hashed_build_inputs_stable_during_build=PASS"
  echo "bilingual_source_alignment=PASS"
  echo "inline_math_expression_multiset_alignment=PASS"
  echo "bilingual_markdown_rebuild_byte_identity=PASS"
  echo "docx_structure_parity=PASS"
  echo
  echo "[docx_structure_parity]"
  cat "$DOCX_VERIFY_REPORT"
  echo
  echo "[docx_outputs]"
  (
    cd "$STAGE"
    sha256sum -- "${DOCX_OUTPUTS[@]}"
  )
  echo
  echo "[bilingual_markdown]"
  (
    cd "$SNAPSHOT/en/bilingual"
    sha256sum -- "${BI_OUTPUTS[@]}"
  )
  echo
  echo "[source_inputs]"
  cat "$SOURCE_BEFORE"
  echo
  echo "[build_tools]"
  cat "$TOOLS_BEFORE"
} > "$RECEIPT"

# Prepare same-filesystem temporary outputs. Remove the canonical receipt before
# replacing any member of the set, then publish the new receipt last. A crash
# can leave no canonical receipt, but cannot leave a mixed set appearing valid
# under a stale canonical receipt.
PUBLISH_SUFFIX=".new.$$"
for name in "${BI_OUTPUTS[@]}"; do
  cp -- "$SNAPSHOT/en/bilingual/$name" \
    "$SRC/en/bilingual/$name$PUBLISH_SUFFIX"
done
for name in "${DOCX_OUTPUTS[@]}"; do
  cp -- "$STAGE/$name" "$OUTDIR/$name$PUBLISH_SUFFIX"
done
cp -- "$RECEIPT" \
  "$OUTDIR/mcrl-thesis-build-receipt.txt$PUBLISH_SUFFIX"

CANONICAL_RECEIPT="$OUTDIR/mcrl-thesis-build-receipt.txt"
PREVIOUS_RECEIPT="$OUTDIR/.mcrl-thesis-build-receipt.previous.txt"
if [[ -f "$CANONICAL_RECEIPT" ]]; then
  mv -f -- "$CANONICAL_RECEIPT" "$PREVIOUS_RECEIPT"
fi
for name in "${BI_OUTPUTS[@]}"; do
  mv -f -- "$SRC/en/bilingual/$name$PUBLISH_SUFFIX" \
    "$SRC/en/bilingual/$name"
done
for name in "${DOCX_OUTPUTS[@]}"; do
  mv -f -- "$OUTDIR/$name$PUBLISH_SUFFIX" "$OUTDIR/$name"
done
mv -f -- "$OUTDIR/mcrl-thesis-build-receipt.txt$PUBLISH_SUFFIX" \
  "$CANONICAL_RECEIPT"
rm -f -- "$PREVIOUS_RECEIPT"

echo "SOURCE SET -> $SOURCE_SET_SHA256"
echo "COHERENCE  -> PASS (read-only snapshot; stable hashed inputs; bilingual Markdown byte-identical)"
for name in "${DOCX_OUTPUTS[@]}"; do
  echo "BUILT      -> $OUTDIR/$name"
done
echo "RECEIPT    -> $OUTDIR/mcrl-thesis-build-receipt.txt"
