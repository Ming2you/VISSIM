"""Independent sample partitions and common-initial-ID contrasts; no simulation."""
import ast
from collections import Counter, defaultdict
import gzip
import hashlib
import itertools
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
R=HERE.parent
ROOT=HERE.parents[2]


def load(p):
    b=p.read_bytes()
    return json.loads(gzip.decompress(b) if b[:2]==b'\x1f\x8b' else b)


def save(name,data):
    (HERE/name).write_text(json.dumps(data,indent=2,allow_nan=False),encoding='utf-8')


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    summary=load(HERE/'summary.json');es=load(HERE/'episodes.json.gz')
    actual=defaultdict(dict);fields={};common=None
    for path,digest in summary['input_sha256'].items():
        path=Path(path);assert sha(path)==digest
        arm=path.name.removesuffix('_frames.json.gz');d=load(path)
        ix={k:i for i,k in enumerate(d['fields'])};fields[arm]=ix
        actual[arm]={round(float(t),6):fr for t,fr in d['frames'].items()}
        initial=actual[arm][2670.1]
        if common is None:common=initial
        else:assert common==initial
    expected=Counter();observed=Counter();common_rows=[];paired=[]
    checks=0
    for arm,frames in actual.items():
        ix=fields[arm]
        for threshold in (5,20):
            for t,fr in frames.items():
                if not 2700.1<=t<3120.1:continue
                for vid,z in fr.items():
                    if 19<=z[ix['cell']]<=25 and z[ix['speed']]<threshold:
                        expected[arm,threshold,vid,t]+=1
    by_vehicle=defaultdict(list)
    for e in es:
        arm,threshold,vid=e['arm'],e['threshold'],e['id'];ix=fields[arm];frames=actual[arm]
        tt=[z[0] for z in e['samples']]
        assert all(abs(b-a-5)<1e-8 for a,b in zip(tt,tt[1:]))
        assert e['start']==tt[0] and e['end_sample']==tt[-1]
        assert e['sampled_seconds']==5*len(tt)
        prev=frames[round(tt[0]-5,6)].get(vid)
        nxt=frames[round(tt[-1]+5,6)].get(vid)
        start=('window_left' if tt[0]==2700.1 else 'missing_previous' if prev is None
               else 'spatial_entry' if not 19<=prev[ix['cell']]<=25 else 'observed_onset')
        end=('window_right' if tt[-1]==3115.1 else 'missing_next' if nxt is None
             else 'spatial_exit' if not 19<=nxt[ix['cell']]<=25 else 'observed_restart')
        assert e['start_kind']==start and e['end_kind']==end
        if start=='observed_onset':assert prev[ix['speed']]>=threshold
        if end=='observed_restart':assert nxt[ix['speed']]>=threshold
        for t,cell,lane,v in e['samples']:
            z=frames[t][vid]
            assert [cell,lane,v]==[z[ix['cell']],z[ix['lane']],z[ix['speed']]]
            observed[arm,threshold,vid,t]+=1;checks+=1
        by_vehicle[arm,threshold,vid].append(e)
    assert expected==observed and max(observed.values())==1
    for key,episodes in by_vehicle.items():
        assert [e['ordinal'] for e in episodes]==list(range(1,len(episodes)+1))
    for row in summary['totals']:
        subset=[e for e in es if (e['arm'],e['threshold'])==(row['arm'],row['threshold'])]
        per=Counter(e['id'] for e in subset)
        assert row['episodes']==len(subset) and row['vehicles']==len(per)
        assert row['repeat_episodes']==len(subset)-len(per)
        assert row['sampled_seconds']==sum(e['sampled_seconds'] for e in subset)
    # Fixed cohort is chosen before all interventions, never on later stop status.
    for arm in actual:
        for threshold in (5,20):
            subset=[e for e in es if e['arm']==arm and e['threshold']==threshold and e['id'] in common]
            per=Counter(e['id'] for e in subset)
            common_rows.append(dict(arm=arm,threshold=threshold,
                initial_all_mainline_cohort=len(common),slow_involved_vehicles=len(per),
                episodes=len(subset),repeat_episodes=len(subset)-len(per),
                sampled_seconds=sum(e['sampled_seconds'] for e in subset),
                end_censoring=dict(Counter(e['end_kind'] for e in subset))))
    for left,right in [('release','release_vsl90'),('release','hold')]:
        for threshold in (5,20):
            def per_arm(arm):
                result=Counter()
                for e in es:
                    if e['arm']==arm and e['threshold']==threshold and e['id'] in common:
                        result[e['id']]+=e['sampled_seconds']
                return result
            x,y=per_arm(left),per_arm(right)
            delta=[y[k]-x[k] for k in common]
            paired.append(dict(left=left,right=right,threshold=threshold,
                improved=sum(v<0 for v in delta),worsened=sum(v>0 for v in delta),
                unchanged=sum(v==0 for v in delta),delta_sampled_seconds=sum(delta)))
    for row in summary['accounting_decomposition']:
        assert abs(sum(row['accounting_parts_seconds'].values())-row['delta_sampled_seconds'])<1e-8
        pair=[next(r for r in summary['totals'] if r['threshold']==row['threshold'] and r['arm']==arm)
              for arm in (row['left'],row['right'])]
        names=['vehicles','episodes_per_vehicle','seconds_per_episode']
        # Independent subset Shapley formula: weights 1/3,1/6,1/3.
        for i,name in enumerate(names):
            others=[j for j in range(3) if j!=i];part=0.
            for mask in itertools.product((0,1),repeat=2):
                multiplier=1.
                for j,side in zip(others,mask):multiplier*=pair[side][names[j]]
                part+=(1/6 if sum(mask)==1 else 1/3)*(pair[1][name]-pair[0][name])*multiplier
            assert abs(part-row['accounting_parts_seconds'][name])<1e-8
    old=ast.parse((HERE/'assess_before208.py.txt').read_text(encoding='utf-8-sig'))
    current_path=R/'regional_audit202/assess.py';new=ast.parse(current_path.read_text(encoding='utf-8-sig'))
    f=lambda tree:{n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.FunctionDef)}
    assert all(f(new)[k]==v for k,v in f(old).items())
    core=load(R/'recovery_memory206/protocol.json')['source_sha256']
    assert all(sha(ROOT/p)==digest for p,digest in core.items())
    assert sha(Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP'))=='91b2163b02b01447242909dee8e7f773d18e76a6594bd9db8de64d2a48246fc3'
    save('common_initial_cohort.json',dict(initial_time=2670.1,evaluation_time=[2700.1,3120.1],
        scope='Identical pre-intervention mainline vehicle IDs; only their observed19--25 slow residence. Not complete trip delay/OmegaTTT.',
        rows=common_rows,paired=paired))
    save('verification.json',dict(status='PASS',samples=checks,episodes=len(es),
        source_frames_identical_at_initial=True,unambiguous_partition=True,
        old_functions_AST_preserved=True,core_files_unchanged=len(core),old_STOP_preserved=True,
        no_native_or_FZP=True,source_sha256={str(p):sha(p) for p in (Path(__file__),current_path)}))
    print(json.dumps(dict(samples=checks,episodes=len(es),common=common_rows,paired=paired)))


if __name__=='__main__':main()
