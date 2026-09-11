#!/usr/bin/env python3
"""CONVSCORE step 1c: do the six training corpora carry the same C1/C2/C3
training labels?  Keys: source rows by (anchor_id,user_id,action_index);
coalition rows by (anchor_id,decomposition_id).  Label fields are the base
row fields the runners read (the exact_source_view extension is stripped by
both runners).  Read-only; writes one JSON to out/."""
import json, resource
from pathlib import Path
L = json.load(open('/home/sat/mcrl-v025-convscore-ws/out/leakage-check.json'))
SRC_LABELS = ('c1_label_bits_hex', 'c1_label_normalized_hex', 'c1_phi_difference_hex',
              'c2_label_bits_hex', 'c2_label_normalized_hex')
COAL_LABELS = ('c1_normalized_hex', 'psi_normalized_hex', 'objective_delta_normalized_hex',
               'physical_c1_normalized_hex', 'physical_delta_normalized_hex', 'physical_psi_normalized_hex',
               'decomposition_weight_hex', 'credit_split', 'original_changed_users')

def load(rn):
    r = L['runs'][rn]
    root = Path(r['corpus_root'])
    rec = json.load(open(Path(r['run_dir']) / 'launch-receipt.json'))
    src, coal = {}, {}
    for f in rec['corpus']['files']:
        p = root / f['path']
        with open(p) as fh:
            head = json.loads(fh.readline())
            for line in fh:
                x = json.loads(line)
                if 'exact-source-anchor' in f['path']:
                    src[(x['anchor_id'], x['user_id'], x['action_index'])] = tuple(x[k] for k in SRC_LABELS)
                else:
                    coal[(x['anchor_id'], x['decomposition_id'])] = tuple(json.dumps(x[k]) for k in COAL_LABELS)
    return src, coal

ref_src, ref_coal = load('exact22')
out = {'reference_run': 'exact22', 'reference_source_rows': len(ref_src), 'reference_coalition_rows': len(ref_coal), 'runs': {}}
for rn in L['runs']:
    if rn == 'exact22':
        continue
    s, c = load(rn)
    per_field = {k: 0 for k in SRC_LABELS}
    common = set(s) & set(ref_src)
    for key in common:
        for i, k in enumerate(SRC_LABELS):
            if s[key][i] != ref_src[key][i]:
                per_field[k] += 1
    cc = set(c) & set(ref_coal)
    coal_diff = {k: 0 for k in COAL_LABELS}
    for key in cc:
        for i, k in enumerate(COAL_LABELS):
            if c[key][i] != ref_coal[key][i]:
                coal_diff[k] += 1
    out['runs'][rn] = {'source_rows': len(s), 'source_keys_common_with_exact22': len(common),
                       'source_label_field_mismatches_vs_exact22': per_field,
                       'coalition_rows': len(c), 'coalition_keys_common_with_exact22': len(cc),
                       'coalition_label_field_mismatches_vs_exact22': coal_diff}
    print(rn, json.dumps(out['runs'][rn]))
out['peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
Path('/home/sat/mcrl-v025-convscore-ws/out/label-identity.json').write_text(json.dumps(out, indent=1, sort_keys=True))
print(f"PEAK_RSS_BYTES={out['peak_rss_bytes']}")
