import re
def rows_of(path):
    out=[]
    for line in open(path):
        if re.match(r'^\| [A-Z0-9]+-[A-Z0-9]+(-\d+)? \|', line) or re.match(r'^\| [A-Z]{2,4}-\d', line):
            out.append(line.rstrip('\n'))
    return out
def split(line):
    # split on ' | ' boundaries not escaped
    inner=line.strip()[1:-1]
    parts=re.split(r'(?<!\\)\|', inner)
    return [p.strip() for p in parts]
def join(c): return '| '+' | '.join(c)+' |'
allrows=[]
for f in ['rows-D.md','rows-B.md','rows-A.md','rows-C.md']:
    for r in rows_of(f):
        for a,b in [('|r^CF − r^M|','\\|r^CF − r^M\\|'),('|r3|','\\|r3\\|'),('|A|≤1','\\|A\\|≤1'),('|C| 965','\\|C\\| 965')]:
            r=r.replace(a,b)
        c=split(r)
        if len(c)!=12:
            print('BADCOLS',f,len(c),r[:80]); continue
        allrows.append(c)
ids=[c[0] for c in allrows]
dups=set(i for i in ids if ids.count(i)>1)
print('rows',len(allrows),'dups',dups)
# normalisations
for c in allrows:
    ID,val,what,phys,est,power,host,tree,pol,n,src,st=c
    P=phys.lower()
    # V025 rows wrongly given max accounting (fork B)
    if ('v025' in P or 'v0.25' in P) and 'modqn' not in P and power.startswith('consumed (max'):
        c[5]='consumed TDM (a-r0) [CURATE: corrected from "max" — V0.25 a-r0 is time-division, CROWDING-COST:23-31]'
    if 'modqn' in P:
        h=host
        if 'L-unpinned' in h and 'e07f3e1e' not in h:
            h=h.replace('L-unpinned','L-unpinned (`e07f3e1e…`)',1)
        elif 'S-frozen' in h and '427e6a91' not in h:
            h=h.replace('S-frozen','S-frozen (content = pinned `427e6a91…`)',1)
        elif 'S-2026-08-25' in h and '427e6a91' not in h:
            h=h.replace('S-2026-08-25','S-2026-08-25 (frozen run, pinned-archive content `427e6a91…`)',1)
        elif h.startswith('local') and not h.startswith('local tree') and not h.startswith('local code') and 'e07f3e1e' not in h and 'unpinned' not in h and 'pinned' not in h:
            h=h+' → = local unpinned archive `e07f3e1e…` [CURATE, per b0 PROGRESS pin note]'
        c[6]=h
    if ID=='CS-33':
        c[11]=st+'; **paired statistic INVALID-AS-PAIRED** (cells share seeds, not episodes, after ep 0 — SC-08)'
    if ID in ('CS-31','DR-09'):
        c[11]=st+'; host+archive: local unpinned eval vs pinned-archive training log'
    if ID=='ZC-06':
        c[11]=st+'; pairing validity UNKNOWN (P6 per-scenario seeds; CFSCREEN checked only the FEASFRONT harness)'
    if ID in ('CS-01','CS-02','CS-03','CS-04'):
        c[11]=st+'; arm-order (`_age_rng`) defect: only RANDOM ran at positions 0–23 (B0 R.5)'
    if ID.startswith('SC-') and 'IN-FLIGHT' in st:
        c[11]=st+' — report since written (`catfish-screens/CATFISH-SCREENS-2026-09-11.md`; controller RECORD-CATFISH-SCREENS-2026-09-11); diagnostic, not a gate'
    if ID=='CH-35':
        c[11]=st+'; `A m=2dB` is not "gain only" — it reads the incumbent (CFSCREEN)'
def group(c):
    P=c[3].lower(); H=c[6]
    if 'sibling' in P and 'modqn-harness rollouts' not in P: return 'SIB'
    if P.startswith('literature') or P=='literature': return 'LIT'
    if 'modqn' in P:
        if 'unpinned' in H or 'e07f3e1e' in H or 'local ephemeris' in H: return 'MQ-L'
        if re.search(r'\bsat\b',H) or 'pinned' in H or 'S-frozen' in H or 'S-2026' in H or 'training host' in H: return 'MQ-S'
        return 'MQ-O'
    if 'v0.23' in P and 'v025' not in P: return 'V23'
    if 'rate-target' in P: return 'V25R'
    if 'v025' in P or 'v0.25' in P or 'stage-c' in P: return 'V25'
    return 'OTH'
titles={
 'MQ-L':'### 1a. MODQN harness — local host, **unpinned** TLE archive `e07f3e1e…` (RANDOM_MASKED signature 53,060,175.56)',
 'MQ-S':'### 1b. MODQN harness — sat host: pinned archive `427e6a91…` (RANDOM_MASKED 52,420,510.10) or sat\'s pre-pin default (the same frozen content), incl. the frozen run\'s training logs; a row whose host cell says `TLE archive UNKNOWN` keeps that caveat',
 'MQ-O':'### 1c. MODQN harness — constants, code facts and rows whose host/archive is not archive-dependent or UNKNOWN',
 'V25':'### 1d. V0.25 successor engine (a-r0; 12-anchor / 93-anchor / 22 TRAIN / 20-anchor scoring panels; stage-C learner)',
 'V25R':'### 1e. V0.25 rate-target probe panels of the morning of 2026-09-10 (sealed vs corrected provisioning)',
 'V23':'### 1f. V0.23 physics (reference only for V0.25 — "no V0.23 percentage states a V0.25 expectation", erratum 17)',
 'LIT':'### 1g. Literature constants',
 'OTH':'### 1h. Other / mixed-condition rows (including withdrawn cross-quantity rows)',
}
hdr='| ID | value | what it is | physics / harness | estimand | power accounting | host + TLE archive | tree / commit / flags | policy / checkpoint | n | source (file:line) | status |\n|---|---|---|---|---|---|---|---|---|---|---|---|'
g={}
prev=None
for c in allrows:
    P=c[3].strip().lower()
    k=prev if (P.startswith('as ') and prev) else group(c)
    prev=k
    g.setdefault(k,[]).append(c)
out=[open('reg-head.md').read()]
out.append('## 1. Registry rows — this project\n\nSource paths are relative to `.scratch/` unless absolute (`/home/sat/…` = read over ssh). `…` in a source path repeats the previous row\'s file.\n')
n_main=0
for k in ['MQ-L','MQ-S','MQ-O','V25','V25R','V23','LIT','OTH']:
    if k in g:
        out.append(titles[k]+f' — {len(g[k])} rows\n\n'+hdr+'\n'+'\n'.join(join(c) for c in g[k])+'\n')
        n_main+=len(g[k])
sib=g.get('SIB',[])
out.append(f'''---

## 2. Old-project (sibling) numbers — **REFERENCE-ONLY — NOT COMPARABLE** — {len(sib)} rows

Why none of these may be compared with any number in §1 (per `.scratch/ee-magnitude/EE-MAGNITUDE-RECONCILIATION-2026-09-11.md` and erratum 28):

- **Estimand.** The cited July numbers (2026-07-11 … 07-21; 146–620) are the sibling's `argmax_EE`: a mean over users → steps →
  episodes of η_u = R_u·N_b/P_b (rev `0082683d`, `family_b_recalibration.py:121-167`), unserved users counting as zero, /1e6.
  Numbers produced after commit `60807490` (2026-08-05) use system EE ÷ U — a third scale (~1/100 of pooled consumed EE).
  Tag: `SIBLING-familyb-JULY` vs `SIBLING-post-2026-08-05`.
- **Denominator.** Radiated RF power only (no PA supply, no circuit, no baseband). On this project's own rollouts consumed
  power is **7.60×** radiated (EM-01).
- **Environment.** `k_cap = 3` beams **per window satellite** (≤ 12 beams; cap-bumped users score 0), G0 40 dBi, different
  noise, Walker-180 constellation, concave load-dependent RF power; this project has no cap, TLE constellation, 33 dBi.
- **Learning rate.** The collapsed "baseline MODQN" (~146–150) ran at lr 0.01; at lr 1e-3 the sibling baseline reads
  428.60 (6 seeds) / 493.18 (3 seeds). Several sibling negatives also used a "best checkpoint" selected on the uncalibrated
  scalar (CH-17).
- **Code era.** The sibling itself marked the capacity-penalty results as predating later fixes and invalid for its current
  protocol (CP report §1; CH-27).
- The only bridge is a **formula** bridge (EM-03: this project's trained checkpoint reads 693.87 on the sibling's July formula,
  random 373.61) — not a ranking of the two projects.

''' + hdr + '\n' + '\n'.join(join(c) for c in sib) + '\n')
out.append(open('reg-cmp.md').read())
out.append(f'\n---\n\n**Counts.** {n_main} rows for this project (§1) + {len(sib)} sibling reference-only rows (§2) = {n_main+len(sib)} rows.\n')
open('/home/u24/papers/mcrl-leo-handover/.scratch/RESULTS-REGISTRY.md','w').write('\n'.join(out))
for k,v in g.items(): print(k,len(v), ' '.join(x[0] for x in v) if k in ('OTH','MQ-O','SIB','LIT','V23','V25R') else '')
print('main',n_main,'sib',len(sib),'total',n_main+len(sib))
