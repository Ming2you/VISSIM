"""Independent saved-count, transfer, and gain audit for192. No re-fitting."""
import collections
import math
from pathlib import Path
import numpy as np
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h
from .fit import region, transition

HERE = Path(__file__).resolve().parent


def main():
    out = HERE/'forecast'
    assert h.read(out/'status.json') == dict(status='complete', forecasts=13)
    assert all(h.read(out/'old178_parity.json').values())
    proto = h.read(HERE/'protocol.json')
    coeff = h.read(HERE/'coefficients.json')
    counts = h.read(HERE/'endpoint_counts.json')
    native_checks = 0
    summaries = []
    for case, entry in h.read(h.R/'state_information92/protocol.json')['inputs'].items():
        d = h.read(h.ROOT/entry['path'])
        ix = {k:i for i,k in enumerate(d['fields'])}
        frames = {float(t):v for t,v in d['frames'].items()}
        c = np.zeros((2,3,3), dtype=int)
        s = np.zeros_like(c)
        excluded = collections.Counter()
        for t,u in zip(sorted(frames),sorted(frames)[1:]):
            for vid,a in frames[t].items():
                reg = region(a[ix['cell']])
                if reg is None:
                    continue
                b = frames[u].get(vid)
                if b is None:
                    excluded['missing_next'] += 1
                elif region(b[ix['cell']]) != reg:
                    excluded['leaves_region'] += 1
                else:
                    i,j = int(a[ix['lane']])-1,int(b[ix['lane']])-1
                    c[reg,i,j] += 1
                    if a[ix['cell']] == b[ix['cell']]:
                        s[reg,i,j] += 1
        assert c.tolist()==counts[case]['counts'] and s.tolist()==counts[case]['same_cell_counts']
        assert dict(excluded)==counts[case]['excluded']
        native_checks += int(c.sum())
        for reg in (0,1):
            summaries.append(dict(case=case,region=reg,pairs=int(c[reg].sum()),
                endpoint_changes=int(c[reg].sum()-np.trace(c[reg])),
                same_cell_changes=int(s[reg].sum()-np.trace(s[reg])),
                cross_cell_changes=int((c[reg]-s[reg]).sum()-np.trace(c[reg]-s[reg]))))
    for reg in (0,1):
        c = sum(np.array(v['counts'][reg]) for k,v in counts.items() if k.startswith('29_'))
        assert c.tolist()==coeff['fits'][reg]['counts']
        z=np.array(coeff['regional'][4*reg:4*reg+4]);eps=1e-4;grad=[]
        def score(x):return -float(np.sum(c*np.log(transition(x)))/c.sum())
        for j in range(4):
            a,b=z.copy(),z.copy();a[j]+=eps;b[j]-=eps
            grad.append((score(a)-score(b))/(2*eps))
        assert max(abs(x) for x in grad)<1e-6
        assert abs(score(z)-coeff['fits'][reg]['normalized_nll'])<1e-12
    rows=h.read(out/'rows.json')
    bounds=h.read(h.F/'route_inventory/mapping31.json')['freeway_model_links']['FW_E']['segment_bounds_m']
    checks=0;maximum=0.
    def exact(a,b):
        nonlocal checks,maximum
        e=abs(a-b);assert e<1e-8,(a,b);checks+=1;maximum=max(maximum,e)
    for r in [x for x in rows if x['mode']=='sampling' and x['horizon']==450]:
        d=h.read(out/'sampling'/(r['case']+'_'+r['arm']+'_lateral.json.gz'))
        assert len(d['transfers'])==2700
        lanes={(round(z['time_s'],6),z['cell'],z['lane']):z for z in d['lanes']}
        for z in d['transfers']:
            i=z['cell'];ns=z['donor_stock'];rates=coeff['rate_matrices'][int(i>=22)]
            matrix=[]
            for g,rr in enumerate(rates):
                total=sum(rr)
                matrix.append([ns[g]*(1-math.exp(-total))*v/total if total else 0. for v in rr])
            for k in range(3):
                total=sum(a[k] for a in matrix)
                space=max(0.,180*(bounds[i+1]-bounds[i])/1000-ns[k])
                f=min(1.,space/total) if total else 0.
                for g in range(3):matrix[g][k]*=f
            for g in range(3):
                for k in range(3):exact(matrix[g][k],z['accepted'][g][k])
                assert sum(matrix[g])<=ns[g]+1e-9
                n=ns[g]-sum(matrix[g])+sum(row[g] for row in matrix)
                exact(n,lanes[round(z['time_s']+1,6),i,g+1]['n_veh'])
            exact(sum(ns),sum(lanes[round(z['time_s']+1,6),i,g+1]['n_veh'] for g in range(3)))
    assessment=h.read(out/'assessment.json');gates={};regrets={}
    for horizon in (150,450):
        losses={mode:h.losses([x for x in rows if x['horizon']==horizon and x['mode']==mode],[]) for mode in ('baseline','sampling')}
        assert losses==assessment['losses'][str(horizon)]
        a,b=losses['baseline'],losses['sampling'];regrets[str(horizon)]=[]
        for case in sorted({x['case'] for x in rows}):
            rs=[x for x in rows if x['case']==case and x['mode']=='sampling' and x['horizon']==horizon]
            chosen=min(rs,key=lambda x:x['predicted']['ttt'])
            regrets[str(horizon)].append(dict(case=case,chosen=chosen['arm'],actual_regret=chosen['actual']['ttt']-min(x['actual']['ttt'] for x in rs)))
        gates[str(horizon)]=dict(meaningful_signs=all(x['sign_correct'] for x in b['pairs'] if x['meaningful']),
            response=b['response']<=.9*a['response'],absolute=b['absolute']<=1.1*a['absolute'],
            regret=all(x['actual_regret']<=.5 for x in regrets[str(horizon)]))
    pins=h.read(out/'preservation.json')['input_sha256']
    for p,digest in {**pins,**proto['protected_sha256'],proto['STOP']['path']:proto['STOP']['sha256']}.items():
        assert h.sha(p)==digest,p
    earlier=h.read(h.R/'exit_refit191/preservation.json')['input_sha256']
    runner=h.R/'state_lateral168/run.py'
    assert h.sha(HERE/'runner_before192.py.txt')==earlier[str(runner)]
    result=dict(status='pass',native_endpoint_pairs=native_checks,transfer_checks=checks,max_transfer_error=maximum,
                native_counts_reproduced=True,fitted_only29=True,coefficients_unchanged=True,prior191_runner_archived_exact=True,
                protected_STOP_preserved=True,gate=gates,regrets=regrets)
    h.save(HERE/'verification.json',result);h.save(HERE/'sampling_summary.json',summaries)
    h.save(HERE/'completion.json',dict(status='complete',completed450=13,seconds=assessment['seconds'],
        result='REJECTED' if not all(gates['450'].values()) else 'SCREEN_PASSED_ONLY',production_adopted=False,
        native=0,FZP_reads=0,push=False,full_goal='ACTIVE_NOT_QUALIFIED'))
    print(result)


if __name__=='__main__':main()
