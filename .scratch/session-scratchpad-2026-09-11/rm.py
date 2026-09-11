import json,glob,os,collections
root='/home/u24/papers/modqn-paper-reproduction/artifacts'
rows=collections.OrderedDict()
def find(x,key,out,p=''):
    if isinstance(x,dict):
        for k,v in x.items():
            if k==key: out.append((p+'.'+k,v))
            find(v,key,out,p+'.'+k)
    elif isinstance(x,list):
        for i,v in enumerate(x[:3]): find(v,key,out,p+f'[{i}]')
for f in sorted(glob.glob(root+'/**/run_metadata.json',recursive=True)):
    try: d=json.load(open(f))
    except Exception as e: continue
    grp=os.path.dirname(os.path.dirname(f)).replace(root+'/','')
    lr=[];find(d,'learning_rate',lr)
    gv=[];find(d,'gamma_vec',gv)
    cal=[];find(d,'reward_calibration_enabled',cal)
    tc=[];find(d,'trainer_class',tc)
    keys=set(d.keys()) if isinstance(d,dict) else set()
    mech=[]
    for k in ['injection_rung1','catfish','catfish_faithful','penalty','capacity_penalty','concat_input','external_inject','value_stratified','acrm','e5_variance_logging','ablation','treatment','input_standardization','shared_q_isolation']:
        if k in keys:
            v=d[k]
            en=v.get('enabled') if isinstance(v,dict) else v
            mech.append(f'{k}={en}' if en is not None else k)
    arm=d.get('arm') if isinstance(d,dict) else None
    key=(grp,)
    s=(str(arm)[:60], sorted(set(str(v) for _,v in lr))[:3], [str(v)[:20] for _,v in gv][:1], sorted(set(str(v) for _,v in cal)), sorted(set(str(v) for _,v in tc))[:2], mech)
    rows.setdefault(grp,[]).append(s)
for g,ss in rows.items():
    uniq=[]
    for s in ss:
        if s not in uniq: uniq.append(s)
    print(f'{g} (n={len(ss)})')
    for s in uniq[:2]: print('   ',s)
