"""Seal the PREREG.  **One deliberate act, run once.**

Every script until now has built the record in memory and thrown it away
(`run_probes.py`, `run_probe_p3.py` both say so at the top).  This one
writes it to disk, and after that any change to a threshold or a selection
mapping is a change made with knowledge of the data — which is exactly what
§7.1 exists to prevent.

So it refuses to overwrite.  A frozen record that can be re-frozen is not
frozen; if the file already exists this script prints its digest and stops,
and reopening it has to be a visible, argued act rather than a re-run.

    python scripts/freeze_prereg.py [--out PATH]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from mcrl.runtime.prereg import open_questions, read_prereg, write_prereg  # noqa: E402
from mcrl.runtime.prereg_draft import freeze  # noqa: E402

DEFAULT_OUT = REPO / "artifacts" / "PREREG-FROZEN-2026-08-23.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    if args.out.exists():
        existing = read_prereg(args.out)
        print(f"⛔ {args.out.relative_to(REPO)} already exists — REFUSING.")
        print(f"   digest {existing.digest}")
        print("   A frozen record that can be re-frozen is not frozen.")
        print("   Reopening it is a visible act, not a re-run of this script.")
        return 1

    record = freeze()
    path = write_prereg(args.out, record)
    read_prereg(path).verify()   # round-trips and re-hashes

    print(f"✅ PREREG frozen → {path.relative_to(REPO)}")
    print(f"   schema  {record.schema}")
    print(f"   digest  {record.digest}")
    print(f"   holdout {record.holdout.digest[:16]}…  (salt {record.holdout.salt})")
    print(f"   bytes   {path.stat().st_size:,}")
    print()
    print("   sections:")
    for name in sorted(record.sections):
        body = json.dumps(record.sections[name], ensure_ascii=False)
        print(f"     {name:<26} {len(body):>7,} chars")
    print()
    print("   open questions (True = closed and frozen):")
    for name, closed in sorted(open_questions().items()):
        print(f"     {'✓' if closed else '✗'} {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
