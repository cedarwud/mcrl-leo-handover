#!/usr/bin/env bash
# guard_thesis_build.sh — PreToolUse(Bash) guard.
#
# Blocks a direct `md2docx` / `pandoc`->docx invocation on thesis-mc Markdown
# sources, because that path skips the repo's table-width / 三線表 borders /
# equation-numbering / A4 fixes. The correct path is `build_ris.sh`.
#
# build_ris.sh's OWN internal md2docx call runs on COPIES in a tmpdir, so it
# never matches "thesis-mc/...md" and is never blocked. Invoking build_ris.sh
# itself (the script path) also does not match.
#
# Fail-open: any internal error -> exit 0 (never break a legitimate Bash call).
set +e

cmd="$(cat 2>/dev/null | python3 -c 'import sys, json
try:
    print(json.load(sys.stdin).get("tool_input", {}).get("command", ""))
except Exception:
    pass' 2>/dev/null)"

[ -z "$cmd" ] && exit 0

# only docx-building invocations are candidates
case "$cmd" in
  *md2docx*|*pandoc*) : ;;
  *) exit 0 ;;
esac

# must reference a thesis-mc markdown source
if printf '%s' "$cmd" | grep -qE 'thesis-mc/[^ ]*\.md|thesis-mc/en/'; then
  # md2docx is always a docx build; pandoc only counts if producing a docx
  if printf '%s' "$cmd" | grep -q 'md2docx' \
     || printf '%s' "$cmd" | grep -qE '\.docx|reference-doc'; then
    echo "⚠ BLOCKED: direct md2docx/pandoc on thesis-mc sources skips the repo's" >&2
    echo "  table column-width + 三線表 borders + equation-numbering + A4 fixes." >&2
    echo "  Use the wrapper instead:  bash thesis-mc/tools/build_ris.sh" >&2
    echo "  (how-to: thesis-mc/tools/README.md). build_ris.sh calls md2docx on" >&2
    echo "  copies internally, so the fixes are applied automatically." >&2
    exit 2
  fi
fi
exit 0
