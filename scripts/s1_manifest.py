"""Emit the frozen S1 declaration and its sha256, BEFORE any formal outcome exists.

Amendment 13 section 7 item 7: the cell list, the S1-TRAIN / S1-NULL namespaces, the
1000-episode depth, the frozen hyperparameters and the formal evaluation namespace must
be committed and hashed before any S1 number exists.  The MC2 round adds two things to
that list: the frozen ``mechanism_id`` (which version runs) and the digest of the
controller's frozen READING RULES, so that what the numbers will be read against is
hashed at the same moment as the configuration.

This writes ``artifacts/s1/S1-MC2-MANIFEST-<date>.json`` plus a ``.sha256`` sidecar and
prints the digest.  It runs no episode, trains nothing and reads no evaluation set --
the evaluation seed list it records is generated arithmetically.

Usage::

    s1_manifest.py --out FILE --calibration FILE --mechanism-id MC2-JGO-v1
                   --reading-rules FILE [--optional D3-null,D3-XEP] [--check]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import cf3_common as C
import s1_common as S


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--calibration", type=Path, required=True)
    ap.add_argument("--mechanism-id", required=True, choices=S.MECHANISM_IDS)
    ap.add_argument("--reading-rules", type=Path, required=True,
                    help="the controller's FROZEN S1 reading rules (hashed in)")
    ap.add_argument("--optional", default=None,
                    help="OPTIONAL cells included at freeze (D3-null,D3-XEP)")
    ap.add_argument("--episodes", type=int, default=S.EPISODES)
    ap.add_argument("--eval-episodes", type=int, default=S.N_EVAL)
    ap.add_argument("--check", action="store_true",
                    help="regenerate and compare with the committed manifest")
    a = ap.parse_args()
    S.assert_environment()

    from mcrl.runtime import training_pipeline as tp
    record = tp.read_prereg(tp.CANONICAL_PREREG)
    calib = json.loads(a.calibration.read_text())
    optional = tuple(x for x in (p.strip() for p in (a.optional or "").split(","))
                     if x)
    reading_rules = {
        "document": str(a.reading_rules),
        "sha256": C.sha256_file(a.reading_rules),
        "frozen_before": "any formal outcome exists",
    }
    manifest = S.declared_manifest(
        record, calib, C.sha256_file(a.calibration),
        mechanism_id=a.mechanism_id, episodes=int(a.episodes),
        eval_episodes=int(a.eval_episodes), optional=optional,
        reading_rules=reading_rules)
    body = json.dumps(manifest, indent=2, sort_keys=True, default=str) + "\n"
    digest = hashlib.sha256(body.encode()).hexdigest()

    if a.check:
        have = a.out.read_text() if a.out.is_file() else ""
        print(f"regenerated sha256 {digest}")
        print(f"committed   sha256 {hashlib.sha256(have.encode()).hexdigest()}")
        return 0 if have == body else 1

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(body)
    a.out.with_suffix(a.out.suffix + ".sha256").write_text(f"{digest}  {a.out.name}\n")
    print(f"{a.out}\nsha256 {digest}\n"
          f"{manifest['mechanism_id']}: {len(manifest['specs'])} trained runs, "
          f"{manifest['episodes']} episodes, drop-one of B = "
          f"{manifest['drop_one_of_B']}, optional {list(optional)}, "
          f"code digest {manifest['code_digest'][:12]}, "
          f"reading rules {reading_rules['sha256'][:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
