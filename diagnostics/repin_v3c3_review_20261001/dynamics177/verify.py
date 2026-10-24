"""Independent score checks and 5-second stopped-stock vehicle-ID ledger."""
import collections
import gzip
import hashlib
import json
from pathlib import Path

H=Path(__file__).resolve().parent
def read(p):
    with (gzip.open(p,'rt',encoding='utf8') if p.suffix=='.gz' else p.open(encoding='utf-8-sig')) as f:return json.load(f)
def save(name,obj):(H/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
r=read(H/'results.json');data=read(H/'data.json');pred=read(H/'predictions.json')
assert len(data)==56 and len(pred)==960
assert len({(x['arm'],x['t']) for x in data})==56
assert len({(x['arm'],x['t'],x['target'],x['model'],x['fold']) for x in pred})==960
for s in r['scores']:
    a=[p for p in pred if all(p[k]==s[k] for k in ('target','fold','model'))]
    assert len(a)==s['n']
    assert abs(sum(abs(p['predicted']-p['actual']) for p in a)/len(a)-s['mae'])<1e-12
for s in r['forward_responses']:
    a=[p for p in pred if p['target']=='exit_next30' and p['fold']=='forward' and p['model']==s['model']]
    for name,key in [('actual','actual_difference'),('predicted','prediction_difference')]:
        value=sum(p[name]*(1 if p['arm']==s['a'] else -1) for p in a if p['arm'] in (s['a'],s['b']))
        assert abs(value-s[key])<1e-10
assert max(x['target_time'] for x in data if x['t']<=2880.1)<min(x['t'] for x in data if x['t']>=2940.1)
ledgers=[];checks=0
for arm in ('hold','release','hold_vsl90','release_vsl90'):
    fr=read(H.parent/f'blocking176/{arm}_frames.json.gz')['frames']
    fr={float(t):v for t,v in fr.items()}
    for cell in (10,20,24,25):
        for threshold in (1,5):
            totals=collections.Counter()
            slow=lambda v:v[1]<=1 if threshold==1 else v[1]<5
            for j in range(84):
                t=round(2700.1+5*j,6);tn=round(t+5,6)
                a={i:v for i,v in fr[t].items() if v[0]==cell and v[3]==1}
                b={i:v for i,v in fr[tn].items() if v[0]==cell and v[3]==1}
                common=a.keys()&b.keys()
                onset=sum(not slow(a[i]) and slow(b[i]) for i in common)
                recovery=sum(slow(a[i]) and not slow(b[i]) for i in common)
                entry=sum(slow(b[i]) for i in b.keys()-a.keys())
                leave=sum(slow(a[i]) for i in a.keys()-b.keys())
                delta=sum(map(slow,b.values()))-sum(map(slow,a.values()))
                assert delta==onset-recovery+entry-leave
                totals.update(onset=onset,recovery=recovery,slow_entry=entry,slow_leave=leave,delta=delta)
                checks+=1
            ledgers.append(dict(arm=arm,cell=cell,lane=1,threshold='<=1' if threshold==1 else '<5',**totals))
for p,digest in r['input_sha256'].items():
    assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest,p
parent=read(H.parent/'blocking176/summary.json')
for p,digest in {**parent['protected_sha256'],parent['STOP']['path']:parent['STOP']['sha256']}.items():
    assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest,p
save('five_second_ledger.json',dict(window=[2700.1,3120.1],rows=ledgers,
    definitions='Endpoint same-vehicle transitions within the same cell/lane; entries/leaves include longitudinal and lateral movement. Counts may include repeat events, not unique people or continuous episodes. Does not observe changes between 5s samples.'))
save('verification.json',dict(completed=True,score_checks=len(r['scores']),response_checks=len(r['forward_responses']),
    unique_predictions=960,temporal_embargo=True,stop_mass_checks=checks,input_and_protected_STOP_unchanged=True,
    raw_FZP_reads=0,VISSIM_runs=0,production_edits=0))
print('verified',checks,'stock balances')
for x in ledgers:
    if x['cell']==20 and x['threshold']=='<5':print(x)
