import json

D = '/home/sat/mcrl-v025-specprofile-ws/.scratch/specprofile/'
m1 = json.load(open(D + 'specprofile-merged.json'))
m2 = json.load(open(D + 'specprofile-declared-rules-merged.json'))

print('=== part 1 pooled events_by_kind ===')
for arm, p in m1['pooled'].items():
    print('%-30s %s  beams=%.2f' % (arm, {k: v for k, v in p['events_by_kind'].items() if v}, p['mean_active_beams']))
print()
print('=== per-anchor BASE / incumbent reference handovers and Phi ===')
for a in m1['per_anchor']:
    b = a['arms']['BASE']['qos']
    g = a['arms']['GAIN_IN_SET']['qos']
    bd = a['arms']['GAIN_IN_SET_BUDGET_VS_BASE']
    print('%-42s step=%d base_ho=%3d base_phi=%5.1f  gain_ho=%3d gain_phi=%5.1f  budget_ho=%3d budget_ee=%8.6f budget_served=%3d budget_att=%3d'
          % (a['anchor_id'], a['step_index'], b['handover_events'], b['phi_priced_handover_cost_kappa'],
             g['handover_events'], g['phi_priced_handover_cost_kappa'],
             bd['qos']['handover_events'], bd['ee_mbit_per_j'], bd['served_phy'], bd['rate_target_attained']))
print()
print('=== per-anchor GAIN_IN_SET kinds + EE + complete-service ===')
for a in m1['per_anchor']:
    g = a['arms']['GAIN_IN_SET']
    print('%-42s EE=%9.6f served=%3d comp=%3d att=%3d bc=%3d sc=%3d ho/us=%.2f phi/us=%.3f'
          % (a['anchor_id'], g['ee_mbit_per_j'], g['served_phy'], g['complete_service_user_steps'],
             g['rate_target_attained'], g['qos']['events_by_kind']['beam_change'],
             g['qos']['events_by_kind']['satellite_change'],
             g['qos']['handover_rate_per_user_step'],
             g['qos']['phi_priced_handover_cost_per_user_step_kappa']))
print()
print('=== part 1 steps 1-3 only pooled ===')
for arm, p in m1['pooled_steps_1_3_only'].items():
    print('%-30s EE=%10.6f served=%4d comp=%4d att=%4d ho=%4d ho/us=%.6f phi/us=%.6f'
          % (arm, p['pooled_ee_mbit_per_j'], p['served_phy'], p['complete_service_user_steps'],
             p['rate_target_attained'], p['handover_events'],
             p['handover_rate_per_user_step'], p['phi_cost_per_user_step_kappa']))
print()
print('=== part 1 guards clustered BY PHYSICAL STEP (4 clusters) ===')


def fmt(v, s='+.4f'):
    return 'undef' if v is None else format(v, s)


for row in m1['guards_cluster_by_step'] + m2['guards_cluster_by_step']:
    cs, ho, ph = row['complete_service'], row['handover_rate'], row['phi_cost']
    print('%s vs %s: comp %spp [%s,%s] %s | ho %s%% [%s,%s] %s | phi %s%% [%s,%s] %s'
          % (row['arm'], row['reference'], fmt(cs['point_pp']), fmt(cs['ci95_pp'][0]),
             fmt(cs['ci95_pp'][1]), cs['verdict'],
             fmt(ho['point_relative_pct'], '+.2f'), fmt(ho['ci95_relative_pct'][0], '+.2f'),
             fmt(ho['ci95_relative_pct'][1], '+.2f'), ho['verdict'],
             fmt(ph['point_relative_pct'], '+.2f'), fmt(ph['ci95_relative_pct'][0], '+.2f'),
             fmt(ph['ci95_relative_pct'][1], '+.2f'), ph['verdict']))
print()
print('=== nonfinite bootstrap draw counts (anchor clustering) ===')
for row in m1['guards_cluster_by_anchor'] + m2['guards_cluster_by_anchor']:
    if row['handover_rate']['nonfinite_draws'] or row['phi_cost']['nonfinite_draws']:
        print('%s vs %s: ho_undef=%d phi_undef=%d of 10000'
              % (row['arm'], row['reference'], row['handover_rate']['nonfinite_draws'],
                 row['phi_cost']['nonfinite_draws']))
print()
print('=== part 2 per-anchor budget construction ===')
for a in m2['per_anchor']:
    c = a['construction']
    r = a['arms']['BEST_DECLARED_RULE']
    print('%-42s ref_ho=%3d cap=%3d admitted=%3d rule_ee=%9.6f rule_ho=%3d satlock_exempt=%d'
          % (a['anchor_id'], c['budget_reference_handovers'], c['budget_count_cap'],
             c['budget_admitted_users'], r['ee_mbit_per_j'], r['qos']['handover_events'],
             c['sat_lock_exempt_users']))
print()
print('=== part 2 steps 1-3 only pooled (key arms) ===')
for arm in ('BASE', 'INCUMBENT_HELD', 'BEST_DECLARED_RULE', 'BEST_DECLARED_RULE_SAT_LOCK',
            'BEST_DECLARED_RULE_BUDGET_VS_BASE'):
    p = m2['pooled_steps_1_3_only'][arm]
    print('%-38s EE=%10.6f served=%4d comp=%4d att=%4d ho=%4d ho/us=%.6f phi/us=%.6f'
          % (arm, p['pooled_ee_mbit_per_j'], p['served_phy'], p['complete_service_user_steps'],
             p['rate_target_attained'], p['handover_events'],
             p['handover_rate_per_user_step'], p['phi_cost_per_user_step_kappa']))
print()
print('=== shard runtime ===')
for shard, meta in m1['shard_meta'].items():
    print(shard, 'wall=%.1fs' % meta['runtime']['wall_seconds'],
          'rss=%.3f GiB' % (meta['runtime']['peak_rss_bytes'] / 2**30),
          'nice=%d' % meta['runtime']['niceness'], 'sha256=' + meta['file_sha256'][:16])
