#!/usr/bin/env python3
"""CONVSCORE step 1b (v2): are the training rows of each run the same decision
states as the view rows its panel was built from?

Panel receipts record (view_path, view_sha256).  The file now at a recorded
path may have been replaced after the panel was built, so the comparison target
is the file whose bytes carry the *recorded* sha256, searched among the
training corpora's own view files.  Read-only; writes one JSON to out/."""
import collections, hashlib, json, resource
from pathlib import Path
L = json.load(open('/home/sat/mcrl-v025-convscore-ws/out/leakage-check.json'))

def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()

by_sha = {}
for rn, r in L['runs'].items():
    for f in r['source_view_files']:
        by_sha.setdefault(f['sha256'], f['path'])

def flatten(d, pre=''):
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(flatten(v, f'{pre}.{k}' if pre else k))
    else:
        out[pre] = d
    return out

PAIRS = [('exact22', 'panel-q1v1'), ('q1v3', 'panel-q1v3'), ('q1v3_control', 'panel-q1v3-control'),
         ('zscore_q1v1', 'panel-q1v1')]
result = {'recorded_vs_current_panel_view_sha': {}, 'pairs': {}}
for pn in ['panel-q1v1', 'panel-q1v2', 'panel-q1v3', 'panel-q1v3-control', 'panel-q1v2z']:
    sv = L['panels'][pn]['source_view_by_key']
    drift = [k for k, (p, s) in sv.items() if p and sha(p) != s]
    result['recorded_vs_current_panel_view_sha'][pn] = {'anchors': len(sv), 'path_now_holds_different_bytes': len(drift)}
    print(pn, 'recorded view sha != current bytes at recorded path:', len(drift), '/', len(sv))
for rn, pn in PAIRS:
    train_files = {f['header_key']: f['path'] for f in L['runs'][rn]['source_view_files']}
    sv = L['panels'][pn]['source_view_by_key']
    diffc = collections.Counter(); n_rows = 0; missing = []; rowcount_eq = 0
    state_equal_rows = 0
    for k in L['panels'][pn]['panel_anchor_ids']:
        rec_sha = sv[k][1]
        built_from = by_sha.get(rec_sha)
        if built_from is None:
            missing.append(k); continue
        with open(built_from) as a, open(train_files[k]) as b:
            a.readline(); b.readline()
            ra = [json.loads(x) for x in a]; rb = [json.loads(x) for x in b]
        rowcount_eq += len(ra) == len(rb)
        for x, y in zip(ra, rb):
            n_rows += 1
            fx, fy = flatten(x), flatten(y)
            for f in set(fx) | set(fy):
                if fx.get(f) != fy.get(f):
                    diffc[f] += 1
            if all(x.get(f) == y.get(f) for f in ('anchor_id', 'user_id', 'action', 'action_index', 'action_mask',
                                                  'q1_state', 'q2_state', 'decision_time_utc', 'world_seed')):
                state_equal_rows += 1
    result['pairs'][f'{rn}__{pn}'] = {
        'panel_anchors_whose_recorded_view_bytes_were_found': 20 - len(missing), 'missing': missing,
        'anchors_with_equal_row_count': rowcount_eq, 'rows_compared': n_rows,
        'rows_with_identical_decision_state(anchor,user,action,mask,q1_state,q2_state,time,world_seed)': state_equal_rows,
        'flattened_fields_that_differ_with_row_counts': dict(diffc)}
    print(rn, pn, json.dumps(result['pairs'][f'{rn}__{pn}'])[:1500])
result['peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
Path('/home/sat/mcrl-v025-convscore-ws/out/state-identity.json').write_text(json.dumps(result, indent=1, sort_keys=True))
print(f"PEAK_RSS_BYTES={result['peak_rss_bytes']}")
