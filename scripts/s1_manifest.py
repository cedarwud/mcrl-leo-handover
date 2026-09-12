"""Emit the frozen S1 declaration and its sha256, BEFORE any formal outcome exists.

Amendment 13 section 7 item 7: the six-arm manifest, the S1-TRAIN / S1-NULL
namespaces, the 1000-episode depth, the frozen hyperparameters and the formal
evaluation namespace must be committed and hashed before any S1 number exists.

This writes ``artifacts/s1/S1-MANIFEST-<date>.json`` plus a ``.sha256`` sidecar and
prints the digest.  It runs no episode, trains nothing and reads no evaluation set --
the evaluation seed list it records is generated arithmetically.

Usage: s1_manifest.py --out FILE --calibration FILE [--check]
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
    ap.add_argument("--episodes", type=int, default=S.EPISODES)
    ap.add_argument("--eval-episodes", type=int, default=S.N_EVAL)
    ap.add_argument("--check", action="store_true",
                    help="regenerate and compare with the committed manifest")
    a = ap.parse_args()
    S.assert_environment()

    from mcrl.runtime import training_pipeline as tp
    record = tp.read_prereg(tp.CANONICAL_PREREG)
    calib = json.loads(a.calibration.read_text())
    manifest = S.declared_manifest(record, calib, C.sha256_file(a.calibration),
                                   episodes=int(a.episodes),
                                   eval_episodes=int(a.eval_episodes))
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
          f"{len(manifest['specs'])} trained runs, {manifest['episodes']} episodes, "
          f"code digest {manifest['code_digest'][:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
