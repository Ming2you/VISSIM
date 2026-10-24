"""Independent joins and graph checks for the bounded205 native-cache diagnosis."""
import ast
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
R=HERE.parent
ROOT=R.parents[1]

def read(path):
    raw=path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix=='.gz' else raw)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    assert not (HERE/'verification.json').exists()
    summary=read(HERE/'summary.json')
    rows=read(HERE/'rows.json.gz');chains=read(HERE/'slow_chains.json.gz')
    raw={};ix=None
    for arm in summary['source_stats']:
        d=read(R/'blocking176'/f'{arm}_frames.json.gz')
        raw[arm]={round(float(t),6):f for t,f in d['frames'].items()}
        ix={s:i for i,s in enumerate(d['fields'])}
    # Six pre-intervention frames: all physical attributes and vehicle IDs identical.
    for t in sorted(raw['hold'])[:6]:
        assert all(fr[t]==raw['hold'][t] for fr in raw.values())
    active={'Brake AX','Brake BX','Follow','Close up'}
    joins=0;by_key={};aggregated=defaultdict(Counter)
    for r in rows:
        fr=raw[r['arm']][r['t']];z=fr[r['id']];trg=fr.get(str(z[ix['target']]))
        key=r['arm'],r['t'],r['id'];assert key not in by_key;by_key[key]=r
        for old,new in [('cell','cell'),('lane','lane'),('link','link'),('x','x'),('v','speed'),
                        ('a','accel'),('nextlink','nextlink'),('lnchg','lnchg'),('state','interaction')]:
            assert r[old]==z[ix[new]];joins+=1
        assert 19<=r['cell']<=25 and r['t']<3120.1
        assert r['active']==(z[ix['interaction']] in active)
        if z[ix['target_type']]!='Vehicle': rel='not_vehicle'
        elif str(z[ix['target']])==r['id']: rel='self'
        elif trg is None:rel='unobserved_vehicle'
        elif trg[ix['link']]!=z[ix['link']]:rel='other_link'
        elif trg[ix['lane']]!=z[ix['lane']]:rel='other_lane_same_link'
        else:rel='same_lane_ahead' if trg[ix['x']]>z[ix['x']] else 'same_lane_not_ahead'
        assert rel==r['relation'];joins+=1
        f=raw[r['arm']][round(r['t']+5,6)].get(r['id'])
        assert r['future_v']==(f[ix['speed']] if f else None);joins+=1
        labels=['all']
        if r['v']>=5 and r['a']<-.5:labels.append('braking')
        if r['v']<5:labels.append('stopped')
        if f and r['v']>=5 and f[ix['speed']]<5:labels.append('stop_onset')
        if f and r['v']<5 and f[ix['speed']]>=5:labels.append('restart')
        for cell in (None,r['cell']):
            for block in (None,r['block']):
                for label in labels:
                    a=aggregated[r['arm'],cell,block,label]
                    a['n']+=1;a['relation:'+rel]+=1
                    if r['active']:a['active_n']+=1;a['active:'+rel]+=1
    for s in summary['populations']:
        a=aggregated[s['arm'],s['cell'],s['block'],s['population']]
        assert a['n']==s['n'] and a['active_n']==s['active_n']
        assert sum(s['relations'].values())==s['n']
        assert sum(s['active_relations'].values())==s['active_n']
        for k,v in s['relations'].items():assert a['relation:'+k]==v
        for k,v in s['active_relations'].items():assert a['active:'+k]==v
    assert len(chains)==sum(z['v']<5 for z in rows)==summary['chains']
    edges=0;root_checks=0
    for c in chains:
        fr=raw[c['arm']][c['t']];path=c['path']
        assert path[0]==c['id'] and path[-1]==c['root'] and len(set(path))==len(path)
        assert len(c['edges'])==len(path)-1
        for a,b,edge in zip(path,path[1:],c['edges']):
            z,trg=fr[a],fr[b]
            assert z[ix['speed']]<5 and z[ix['interaction']] in active
            assert str(z[ix['target']])==b and z[ix['target_type']]=='Vehicle'
            assert trg[ix['x']]>z[ix['x']]
            expected=('other_link' if z[ix['link']]!=trg[ix['link']] else
                      'other_lane_same_link' if z[ix['lane']]!=trg[ix['lane']] else 'same_lane_ahead')
            assert edge==expected;edges+=1
        root=fr[path[-1]]
        if c['reason']=='moving_target':assert root[ix['speed']]>=5
        elif c['reason']=='inactive_native_state':assert root[ix['speed']]<5 and root[ix['interaction']] not in active
        else:raise AssertionError('Unexpected observed chain endpoint; add explicit verification')
        assert c['crosses_lane']==('other_lane_same_link' in c['edges'])
        assert c['span_m']==root[ix['x']]-fr[path[0]][ix['x']]
        root_checks+=1
    old=ast.parse((HERE/'assess_before205.py.txt').read_text(encoding='utf-8'))
    new=ast.parse((R/'regional_audit202/assess.py').read_text(encoding='utf-8'))
    functions=lambda tree:{n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.FunctionDef)}
    before,after=functions(old),functions(new)
    assert all(after[k]==v for k,v in before.items())
    for p,digest in summary['input_sha256'].items():assert sha(Path(p))==digest
    core=read(R/'regional_audit202/protocol.json')['source_sha256']
    for p,digest in core.items():assert sha(ROOT/p)==digest
    stop=Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')
    assert sha(stop)=='91b2163b02b01447242909dee8e7f773d18e76a6594bd9db8de64d2a48246fc3'
    result=dict(status='PASS',rows=len(rows),scalar_joins=joins,chain_edges=edges,chain_roots=root_checks,
        common_prefix_frames=6,aggregation_rows=len(summary['populations']),
        prior_functions_AST_unchanged=True,core_files=len(core),input_pins=len(summary['input_sha256']),
        source_sha256={str(p):sha(p) for p in (Path(__file__),R/'regional_audit202/assess.py')},
        goal='ACTIVE_NOT_QUALIFIED')
    (HERE/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'}))

if __name__=='__main__':main()
