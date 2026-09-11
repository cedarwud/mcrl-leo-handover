#!/usr/bin/env python3
"""CONVSCORE step 1d: C3 coalition label identity across the six corpora,
row-by-row in file order (keys are not unique), plus file-sha equality.
Read-only; writes one JSON to out/."""
import collections, hashlib, json, resource
from pathlib import Path
L = json.load(open('/home/sat/mcrl-v025-convscore-ws/out/leakage-check.json'))
LAB = ('anchor_id', 'decomposition_id', 'original_changed_users', 'c1_normalized_hex', 'psi_normalized_hex',
       'objective_delta_normalized_hex', 'physical_c1_normalized_hex', 'physical_delta_normalized_hex',
       'physical_psi_normalized_hex', 'decomposition_weight_hex', 'credit_split', 'capped_decomposition')
def files(rn):
    r = L['runs'][rn]; root = Path(r['corpus_root'])
    rec = json.load(open(Path(r['run_dir']) / 'launch-receipt.json'))
    return [(root / f['path'], f['sha256']) for f in rec['corpus']['files'] if 'COALITION' in f['path']]
def rows(p):
    with open(p) as fh:
        fh.readline()
        return [tuple(json.dumps(json.loads(l)[k], sort_keys=True) for k in LAB) for l in fh]
ref = files('exact22'); ref_rows = [rows(p) for p, _ in ref]
out = {'runs': {}}
for rn in L['runs']:
    if rn == 'exact22': continue
    fs = files(rn)
    same_sha = sum(1 for (a, sa), (b, sb) in zip(ref, fs) if sa == sb)
    n = seqdiff = 0; msdiff = 0; fields = collections.Counter()
    for (p, _), rr in zip(fs, ref_rows):
        xr = rows(p)
        n += len(xr)
        for a, b in zip(xr, rr):
            if a != b:
                seqdiff += 1
                for i, k in enumerate(LAB):
                    if a[i] != b[i]: fields[k] += 1
        msdiff += (collections.Counter(xr) != collections.Counter(rr))
    out['runs'][rn] = {'coalition_files': len(fs), 'files_sha_equal_to_exact22': same_sha, 'rows': n,
                       'rows_differing_in_label_fields_in_file_order': seqdiff, 'fields': dict(fields),
                       'files_whose_label_multiset_differs': msdiff}
    print(rn, json.dumps(out['runs'][rn]))
out['exact22_rows'] = sum(len(r) for r in ref_rows)
out['peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
Path('/home/sat/mcrl-v025-convscore-ws/out/coalition-label-identity.json').write_text(json.dumps(out, indent=1, sort_keys=True))
print('exact22 rows', out['exact22_rows'], f"PEAK_RSS_BYTES={out['peak_rss_bytes']}")
