#!/usr/bin/env python3
"""Engineering-lane check: does an offline real-artifact gate report (run in a workspace) cover the code that a checkout
will launch? Compares every file digest recorded in the report's input_identities/closure against the same relative paths in
the target checkout. Read-only. Exit 0 = every recorded file matches (prints MATCH n), exit 3 = mismatch list, exit 2 = usage."""
import hashlib, json, sys, pathlib

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def walk(o, out):
    if isinstance(o, dict):
        if "path" in o and "sha256" in o and isinstance(o.get("sha256"), str):
            out.append((str(o["path"]), o["sha256"]))
        for v in o.values():
            walk(v, out)
    elif isinstance(o, list):
        for v in o:
            walk(v, out)

def main(argv):
    if len(argv) != 3:
        print("usage: compare_gate_closure_to_checkout.py <dryrun-report.json> <target checkout>", file=sys.stderr); return 2
    rep = json.loads(pathlib.Path(argv[1]).read_text()); target = pathlib.Path(argv[2]).resolve()
    repo = pathlib.Path(rep["repo"]).resolve()
    recorded = []
    walk(rep.get("input_identities"), recorded); walk(rep.get("input_integrity"), recorded)
    seen, bad, n = set(), [], 0
    for path, digest in recorded:
        p = pathlib.Path(path)
        try:
            rel = p.resolve().relative_to(repo)
        except ValueError:
            continue  # artifact outside the repo (e.g. the sealed target root): not a code file
        if rel in seen or not (target / rel).exists():
            if not (target / rel).exists() and rel not in seen:
                bad.append((str(rel), digest, "MISSING_IN_TARGET"))
            seen.add(rel); continue
        seen.add(rel); n += 1
        got = sha(target / rel)
        if got != digest:
            bad.append((str(rel), digest, got))
    if bad:
        for b in bad: print("MISMATCH", *b)
        return 3
    print(f"MATCH {n} files spec={rep['spec']['sha256']} verdict={rep.get('verdict')}"); return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
