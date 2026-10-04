"""One bounded check of passive stopped-tag transport, not9000 analysis."""
import ast
import difflib
import gzip
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OLD=HERE.parent/'stop_population114'
HELPER=HERE.parent/'stop_law113/passive.py'
read=lambda p:json.loads(Path(p).read_text(encoding='utf8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,x):(HERE/name).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')

def main():
    assert not (HERE/'protocol.json').exists(), 'Do not repeat or extend this trial'
    protocol=read(OLD/'protocol.json')
    protocol.update(previous_turn='PROGRESS115;1169000 analysis now stopped by explicit user steering',
        hypothesis='Stopped labels should not advect at the same speed as all vehicles; isolate transport from existing stop/restart rates.',
        budget=dict(moment_estimates=1,rate_fits=0,new_parameters_searched=0,forecasts_if_native_transport_supported=4),
        conditional='Current-origin vehicles with known next mainline record; use actual postreaction labels ONLY to isolate transport, not as forecast inputs.',
        transport_candidate='qB=clip(q*B*vB/(N*max(v,vB)), max(0,q-N+B), min(q,B)); per-source shares, exact tag conservation',
        interpretation='Two-pool flux allocation hypothesis, not a reproduced Zhou equation; no feedback to physical flow or cost yet.',
        gate='Native transport MAE improves>=10% separately43/67; then4fixed450. vs114 require>=20% reduction of both material67delta errors and no43 meanB RMSE worsening. No more parameters/grid if failed.',
        helper_sha256=sha(HELPER),STOP_sha256=sha(Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')))
    save('protocol.json',protocol)
    caches={}
    for case,s in protocol['input_pins'].items():
        path=ROOT/s['path'];assert sha(path)==s['sha256']
        with gzip.open(path,'rt',encoding='utf8') as f:raw=json.load(f)
        caches[case]={float(t):r for t,r in raw['frames'].items()}
    samples=[r[1] for case,frames in caches.items() if case.startswith('29_') for f in frames.values()
             for r in f.values() if 16<=r[0]<24 and r[1]<5]
    vB=statistics.mean(samples);assert 0<vB<5
    conditional=[]
    for case,frames in caches.items():
        totals=dict(rows=0,known=0,censored=0,crossings=0,stopped_crossings=0,mixed=0.,weighted=0.,
                    mixed_abs_error=0.,weighted_abs_error=0.)
        times=sorted(frames)
        for t,tn in zip(times,times[1:]):
            old,new=frames[t],frames[tn];assert abs(tn-t-5)<1e-7
            for i in range(16,24):
                present={k:r for k,r in old.items() if r[0]==i}
                known={k:r for k,r in present.items() if k in new}
                totals['censored']+=len(present)-len(known)
                if not known:continue
                n=len(known);b=sum(new[k][1]<5 for k in known)
                q=sum(new[k][0]>i for k in known)
                actual=sum(new[k][0]>i and new[k][1]<5 for k in known)
                v=statistics.mean(r[1] for r in known.values())
                mixed=q*b/n
                weighted=min(q,b,max(0,q-n+b,mixed*vB/max(v,vB)))
                for key,value in dict(rows=1,known=n,crossings=q,stopped_crossings=actual,mixed=mixed,weighted=weighted,
                    mixed_abs_error=abs(mixed-actual),weighted_abs_error=abs(weighted-actual)).items():totals[key]+=value
        conditional.append(dict(case=case,**totals))
    gates=[]
    for seed in ('43','67'):
        subset=[r for r in conditional if r['case'].startswith(seed+'_')]
        old=sum(r['mixed_abs_error'] for r in subset);new=sum(r['weighted_abs_error'] for r in subset)
        gates.append(dict(seed=seed,mixed_l1=old,weighted_l1=new,improvement=1-new/old,passed=new<=.9*old))
    save('conditional.json',dict(stopped_speed_kph=vB,training_vehicle_samples=len(samples),cases=conditional,gates=gates,
         limitation='Uses actual future transition labels solely for transport isolation; NOT autonomous performance'))
    if not all(g['passed'] for g in gates):
        save('completion.json',dict(status='REJECT_TRANSPORT',forecasts=0,conditional_gates=gates,gain_qualified=False));return
    # Reuse the exact existing diagnostic with only the single transport expression
    # replaced in memory. Original source and physical runner/adapter stay unchanged.
    text=HELPER.read_text(encoding='utf8')
    old='fraction=[bi/ni if ni>0 else 0. for bi,ni in zip(after,old_n)]'
    new=('fraction=[min(q,bi,max(0.,q-ni+bi,q*bi/ni*V_B/max(vi,V_B)))/q if q>0 and ni>0 else 0. '
         'for bi,ni,q,vi in zip(after,old_n,total_out,v)]')
    assert text.count(old)==1
    patched=text.replace(old,new)
    (HERE/'transport_candidate.patch').write_text(''.join(difflib.unified_diff(text.splitlines(True),patched.splitlines(True),
        fromfile=str(HELPER),tofile='in_memory_diagnostic')),encoding='utf8')
    (HERE/'macro_results.json').write_bytes((OLD/'macro_results.json').read_bytes())
    tree=ast.parse(patched,str(HELPER));scope={'__file__':str(HELPER),'__name__':'transport117'}
    exec(compile(tree,str(HELPER),'exec'),scope)
    scope['HERE']=HERE;scope['V_B']=vB
    begun=time.perf_counter();scope['main']()
    prior=read(OLD/'passive_results.json');current=read(HERE/'passive_results.json')
    comparisons=[]
    for seed in ('43','67'):
        x=next(g for g in prior['gates'] if g['seed']==seed);y=next(g for g in current['gates'] if g['seed']==seed)
        comparisons.append(dict(seed=seed,old_rmse=x['rmse']['state'],new_rmse=y['rmse']['state'],old_delta=x['delta'],new_delta=y['delta']))
    c67=next(x for x in comparisons if x['seed']=='67');c43=next(x for x in comparisons if x['seed']=='43')
    response_pass=all(abs(y['actual']-y['state'])<=.8*abs(x['actual']-x['state'])
        for x,y in zip(c67['old_delta'],c67['new_delta']) if abs(y['actual'])>=5)
    passed=response_pass and c43['new_rmse']<=c43['old_rmse']
    assert sha(HELPER)==protocol['helper_sha256']
    assert all(sha(p)==h for p,h in protocol['core_pins'].items())
    assert sha(Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP'))==protocol['STOP_sha256']
    save('completion.json',dict(status='STATE_TRANSPORT_CANDIDATE_ONLY' if passed else 'REJECT_TRANSPORT',
        forecasts=4,new_rate_fits=0,comparisons=comparisons,response_gate=passed,
        elapsed_seconds=time.perf_counter()-begun,original_sources_preserved=True,physical_parity=True,gain_qualified=False))
    print(json.dumps(read(HERE/'completion.json'),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
