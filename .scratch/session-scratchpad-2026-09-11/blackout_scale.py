"""Arithmetic on the declared constants and the already-measured event mix.

This is NOT a measurement of the interruption treatment and produces no
interruption-scored EE.  It reports how many seconds of blackout the declared
`_blackouts` condition would open, as a fraction of the decision interval.
"""
import json

D = '/home/sat/mcrl-v025-specprofile-ws/.scratch/specprofile/'
SAME = 0.062
SAT = 0.142
INTERVAL = 30.08

m1 = json.load(open(D + 'specprofile-merged.json'))
m2 = json.load(open(D + 'specprofile-declared-rules-merged.json'))

rows = [
    ('geometric base (BASE)', m1['pooled']['BASE']),
    ('declared incumbent, held', m1['pooled']['INCUMBENT_HELD']),
    ('RSS_MAX', m1['pooled']['RSS_MAX']),
    ('strongest declared rule (S2|A2)', m2['pooled']['BEST_DECLARED_RULE']),
    ('CAP_050 search winner', m1['pooled']['GAIN_IN_SET']),
    ('search winner, budgeted vs base', m1['pooled']['GAIN_IN_SET_BUDGET_VS_BASE']),
    ('declared rule, budgeted vs base', m2['pooled']['BEST_DECLARED_RULE_BUDGET_VS_BASE']),
]

print('%-34s %8s %8s %8s %10s %9s %10s' % (
    'arm', 'beam ch', 'sat ch', 'events', 'blackout s', 'of tape', 'EE Mbit/J'))
out = {}
for name, p in rows:
    kinds = p['events_by_kind']
    beam = kinds['beam_change']
    sat = kinds['satellite_change']
    other = {k: v for k, v in kinds.items()
             if v and k not in ('beam_change', 'satellite_change', 'unchanged')}
    assert not other, (name, other)
    seconds = beam * SAME + sat * SAT
    tape_seconds = p['user_steps'] * INTERVAL
    frac = seconds / tape_seconds
    out[name] = (seconds, frac, p['pooled_ee_mbit_per_j'])
    print('%-34s %8d %8d %8d %10.3f %8.4f%% %10.6f' % (
        name, beam, sat, beam + sat, seconds, 100 * frac, p['pooled_ee_mbit_per_j']))

print()
print('declared window as a fraction of one decision interval:')
print('  same-satellite beam change  %.3f s / %.2f s = %.4f%%' % (SAME, INTERVAL, 100 * SAME / INTERVAL))
print('  satellite change            %.3f s / %.2f s = %.4f%%' % (SAT, INTERVAL, 100 * SAT / INTERVAL))
print()
w = out['CAP_050 search winner']
b = out['search winner, budgeted vs base']
g = out['geometric base (BASE)']
print('spread in blackout fraction, churniest arm minus budgeted arm: %.4f pp'
      % (100 * (w[1] - b[1])))
print('spread, churniest arm minus base: %.4f pp' % (100 * (w[1] - g[1])))
print('measured EE ratio, search winner / budgeted: %.4fx' % (w[2] / b[2]))
print('blackout-fraction ratio needed to close that gap: %.1fx of the interval'
      % (w[2] / b[2]))
