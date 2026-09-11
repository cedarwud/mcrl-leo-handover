from pathlib import Path

p = Path('/home/sat/mcrl-v025-specprofile-ws/.scratch/specprofile/merge_specprofile.py')
s = p.read_text()
start = s.index("    def fmt(v, spec='+.4f'):")
end = s.index("    return 0\n\n\nif __name__")
block = '''    def fmt(v, spec='+.4f'):
        return 'undef' if v is None else format(v, spec)
    for row in result['guards_cluster_by_anchor']:
        cs, ho, ph = row['complete_service'], row['handover_rate'], row['phi_cost']
        print(
            row['arm'] + ' vs ' + row['reference'] + ': '
            + 'comp ' + fmt(cs['point_pp']) + 'pp ['
            + fmt(cs['ci95_pp'][0]) + ',' + fmt(cs['ci95_pp'][1]) + '] '
            + cs['verdict'] + ' | '
            + 'ho ' + fmt(ho['point_relative_pct'], '+.2f') + '% ['
            + fmt(ho['ci95_relative_pct'][0], '+.2f') + ','
            + fmt(ho['ci95_relative_pct'][1], '+.2f') + '] '
            + ho['verdict'] + ' | '
            + 'phi ' + fmt(ph['point_relative_pct'], '+.2f') + '% ['
            + fmt(ph['ci95_relative_pct'][0], '+.2f') + ','
            + fmt(ph['ci95_relative_pct'][1], '+.2f') + '] '
            + ph['verdict'])
'''
s = s[:start] + block + s[end:]
p.write_text(s)
print('ok')
