"""Record the ONE T0-XEP reference trajectory (Amendment 12 section 2).

**Run once, ever.**  The reference episode is rolled under T0 on the declared
DEV-NULL seed pair, its raw ``channel_quality`` / ``beam_loads`` are written to
``artifacts/dev-e0/t0-xep-reference.json``, and its file sha256 is printed.  That
sha256 is then pasted into ``dev_e0_common.XEP_REFERENCE_SHA256``, which puts it in
every ``D3-XEP`` run's configuration hash; from that point every consumer verifies the
file against it and refuses anything else.

This script refuses to overwrite an existing reference: Amendment 12 says the
trajectory "may not be regenerated afterwards", so regeneration has to be a deliberate
act of deleting the committed file, not an accident of re-running a script.

``--verify`` re-records into a temporary file and compares the bytes against the
committed one, which is how a reviewer checks the reference is what it claims to be
without destroying it.

Usage::

    dev_e0_xep_reference.py [--out FILE] [--verify]
"""

from __future__ import annotations

import argparse
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import cf3_common as C
import dev_e0_common as D

from mcrl.algorithms import cf_teacher as cft
from mcrl.algorithms import cf_xep as cfx


def _record() -> dict:
    factory = C.env_factory()
    policy = cft.t0_policy()
    return cfx.record_reference(
        factory, env_seed=D.XEP_REF_ENV_SEED, mobility_seed=D.XEP_REF_MOB_SEED,
        policy=policy, policy_name=D.XEP_REF_POLICY,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=D.XEP_REFERENCE_PATH)
    ap.add_argument("--verify", action="store_true",
                    help="re-record and compare with the existing file; write nothing")
    a = ap.parse_args()
    tle = D.assert_environment()
    payload = _record()

    if a.verify:
        with tempfile.TemporaryDirectory() as tmp:
            probe = Path(tmp) / "probe.json"
            digest = cfx.write_reference(probe, payload)
        have = cfx.file_sha256(a.out)
        ok = digest == have
        print(f"re-recorded sha256 {digest}\ncommitted   sha256 {have}\n"
              f"{'MATCH' if ok else 'MISMATCH'}")
        return 0 if ok else 1

    digest = cfx.write_reference(a.out, payload)
    provenance = {
        "reference_file": str(a.out),
        "reference_sha256": digest,
        "schema": payload["schema"],
        "policy": payload["policy"],
        "env_seed": payload["env_seed"],
        "mobility_seed": payload["mobility_seed"],
        "steps": payload["steps"], "users": payload["users"],
        "data_sha256": payload["data_sha256"],
        "tle_file_set_sha256": tle,
        "code": D.code_manifest(),
        "recorded_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "authority": ("V025-CONTROLLER-AMENDMENT-12-S1-SECOND-NULL-2026-09-12.md "
                      "section 2"),
        "lane": ("DEV-NULL: recorded once, never regenerated; never DEV, DEVVAL, "
                 "formal evaluation, calibration or CONFIRM"),
        "note": ("The reference file itself carries only content that is a function of "
                 "(schema, policy, seeds, users, steps), so re-recording on the pinned "
                 "archive reproduces its bytes; this sidecar holds the volatile "
                 "provenance and is NOT part of the identity."),
    }
    side = a.out.with_name(a.out.stem + "-provenance.json")
    C.write_json(side, provenance)
    print(json.dumps({"reference": str(a.out), "sha256": digest,
                      "provenance": str(side)}, indent=2))
    print("\nPaste this into dev_e0_common.XEP_REFERENCE_SHA256:\n" + digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
