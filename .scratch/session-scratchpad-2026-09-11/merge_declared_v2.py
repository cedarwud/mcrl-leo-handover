#!/usr/bin/env python3
"""Merge the SPECPROFILE declared-rule receipt and apply the sealed QoS guard."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, '/home/sat/mcrl-v025-specprofile-ws/.scratch/specprofile')
from merge_specprofile import guard, pooled, SEED  # noqa: E402

OUTDIR = Path('/home/sat/mcrl-v025-specprofile-ws/.scratch/specprofile')
DECLARED = [
    'CAP_050__S1_ascending_coverage|A1_coverage_first',
    'CAP_050__S1_ascending_coverage|A2_max_nominal_gain',
    'CAP_050__S1_ascending_coverage|A3_least_loaded',
    'CAP_050__S2_descending_coverage|A1_coverage_first',
    'CAP_050__S2_descending_coverage|A2_max_nominal_gain',
    'CAP_050__S2_descending_coverage|A3_least_loaded',
    'CAP_050__S3_descending_nominal_gain|A1_coverage_first',
    'CAP_050__S3_descending_nominal_gain|A2_max_nominal_gain',
    'CAP_050__S3_descending_nominal_gain|A3_least_loaded',
]
BEST = ['BEST_DECLARED_RULE', 'BEST_DECLARED_RULE_SAT_LOCK',
        'BEST_DECLARED_RULE_ZERO_HANDOVER', 'BEST_DECLARED_RULE_BUDGET_VS_BASE']
ARMS = ['BASE', 'INCUMBENT_HELD'] + DECLARED + BEST


def fmt(value, spec='+.4f'):
    return 'undef' if value is None else format(value, spec)


def main() -> int:
    path = OUTDIR / 'specprofile-declared-rules.json'
    payload = json.loads(path.read_text(encoding='utf-8'))
    if payload['status'] != 'COMPLETE' or payload['scalar_evaluate_calls'] != 0:
        raise SystemExit('declared-rule receipt is not clean and complete')
    anchors = payload['anchors']
    if len(anchors) != 12:
        raise SystemExit(f'expected 12 anchors, found {len(anchors)}')

    result = {
        'schema': 'mcrl-v025-specialist-qos-profile-declared-rules-merge-v1',
        'claim_status': 'DESIGN_PHASE_MEASUREMENT_NOT_A_CLAIM',
        'seed': SEED,
        'source_receipt_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'pooled': {arm: pooled(anchors, arm) for arm in ARMS},
        'pooled_steps_1_3_only': {
            arm: pooled([a for a in anchors if a['step_index'] > 0], arm) for arm in ARMS},
        'per_anchor': [
            {'anchor_id': a['anchor_id'], 'step_index': a['step_index'],
             'carrier': a['carrier'], 'construction': a['constrained_construction'],
             'arms': {arm: {'ee_mbit_per_j': a['arms'][arm]['ee_bit_per_j'] / 1e6,
                            'served_phy': a['arms'][arm]['served_phy'],
                            'complete_service_user_steps':
                                a['arms'][arm]['complete_service_user_steps'],
                            'rate_target_attained': a['arms'][arm]['rate_target_attained'],
                            'active_beams': a['arms'][arm]['active_beams_mapping'],
                            'qos': a['arms'][arm]['qos']} for arm in ARMS}}
            for a in anchors],
        'guards_cluster_by_anchor': [],
        'guards_cluster_by_step': [],
    }
    contrasts = [(arm, 'BASE') for arm in DECLARED]
    contrasts += [(arm, ref) for arm in BEST for ref in ('BASE', 'INCUMBENT_HELD')]
    for arm, ref in contrasts:
        result['guards_cluster_by_anchor'].append(
            guard(anchors, arm, ref, lambda a: a['anchor_id'], np.random.default_rng(SEED)))
        result['guards_cluster_by_step'].append(
            guard(anchors, arm, ref, lambda a: a['step_index'], np.random.default_rng(SEED)))

    out = OUTDIR / 'specprofile-declared-rules-merged.json'
    out.write_text(json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + '\n',
                   encoding='utf-8')
    print('wrote ' + str(out))
    for arm in ARMS:
        p = result['pooled'][arm]
        print('%-56s EE=%10.6f served=%4d complete=%4d attain=%4d ho=%4d ho/us=%.6f phi/us=%.6f'
              % (arm, p['pooled_ee_mbit_per_j'], p['served_phy'],
                 p['complete_service_user_steps'], p['rate_target_attained'],
                 p['handover_events'], p['handover_rate_per_user_step'],
                 p['phi_cost_per_user_step_kappa']))
    for row in result['guards_cluster_by_anchor']:
        cs, ho, ph = row['complete_service'], row['handover_rate'], row['phi_cost']
        print(row['arm'] + ' vs ' + row['reference'] + ': '
              + 'comp ' + fmt(cs['point_pp']) + 'pp ['
              + fmt(cs['ci95_pp'][0]) + ',' + fmt(cs['ci95_pp'][1]) + '] ' + cs['verdict']
              + ' | ho ' + fmt(ho['point_relative_pct'], '+.2f') + '% ['
              + fmt(ho['ci95_relative_pct'][0], '+.2f') + ','
              + fmt(ho['ci95_relative_pct'][1], '+.2f') + '] ' + ho['verdict']
              + ' | phi ' + fmt(ph['point_relative_pct'], '+.2f') + '% ['
              + fmt(ph['ci95_relative_pct'][0], '+.2f') + ','
              + fmt(ph['ci95_relative_pct'][1], '+.2f') + '] ' + ph['verdict'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
