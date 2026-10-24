"""Saved five-second mainline/merge timing audit, without future-input rollout."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
from collections import defaultdict
import csv
import ctypes
import gzip
import json
import math
from pathlib import Path
import time
import sys
import numpy as np
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent
if '--port-endpoints' in sys.argv:HERE=HERE/'port_endpoint_repair'


def csv_rows(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def metric(rows, main):
    a=np.array([r[main] for r in rows],float);m=np.array([r['merge10490'] for r in rows],float)
    assert len(a)==30
    ac=a.reshape(5,6);mc=m.reshape(5,6)
    expected=float(np.sum(ac.sum(axis=1)*mc.sum(axis=1)/6.))
    observed=float(a@m)
    # Five alternate cyclic alignments preserve each30s count and every5s value.
    # This is a descriptive phase reference, NOT a randomization p-value.
    cyclic=[float(np.sum(ac*np.roll(mc,k,axis=1))) for k in range(6)]
    variance=float(np.mean((ac-ac.mean(axis=1)[:,None])**2))
    return dict(main=sum(a),merge=sum(m),same5s_product=observed,
        same30s_independent_phase_product=expected,overlap_excess=observed-expected,
        within30s_covariance=(observed-expected)/30.,cyclic_reference=cyclic,
        main5s_variance_within30=variance,
        native_uniform_multinomial_variance_reference=float(a.mean()*5/6),
        mean_n21_lane1=float(np.mean([r['n21_lane1'] for r in rows])),
        mean_slow21_lane1=float(np.mean([r['slow21_lane1'] for r in rows])) if all('slow21_lane1' in r for r in rows) else None,
        main19=sum(r['main19_all'] for r in rows),main20=sum(r['main20_all'] for r in rows),
        main21=sum(r['main21_all'] for r in rows),
        off10483=sum(r['off10483'] for r in rows) if all(r['off10483'] is not None for r in rows) else None)


def main():
    assert not (HERE/'protocol.json').exists(), 'Preserve existing result/failure'
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype=ctypes.c_void_p
    kernel.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000)
    began=time.perf_counter()
    protected={str(p):h.sha(p) for p in (h.ROOT/'evaluation/controllers').glob('*.py')}
    stop=h.read(h.R/'vsl_response243/lateral_friction244/protocol.json')['STOP']
    cases=[]
    catalog=h.read(h.C/'data_catalog.json')['checked_records']
    for r in catalog:
        if r['case']=='s29_late' and r['arm'] in ('hold','hold_vsl90'):
            cases.append(dict(case=r['case'],arm=r['arm'],cutoff=r['cutoff'],truth=Path(r['truth']),frames=h.F/f"vsl_native_exposure/{r['case']}_{r['arm']}_frames.json.gz"))
        if r['case']=='s43_early' and r['arm'] in ('none','vsl'):
            cases.append(dict(case=r['case'],arm=r['arm'],cutoff=r['cutoff'],truth=Path(r['truth']),frames=h.F/f"cohort_early/s43_{r['arm']}_frames.json.gz"))
    for arm in ('hold','hold_vsl90','release','release_vsl90'):
        cases.append(dict(case='s67_late',arm=arm,cutoff=2670.1,truth=h.I/f'heldout67_freeway_20260930/observations/{arm}',frames=h.R/f'blocking176/{arm}_frames.json.gz'))
    assert len(cases)==8
    protocol=dict(previous_goal_turn='PROGRESS244:33predictions bounded friction/merge fit rejected; mechanical checks passed. Live9000 native survived wrapper loss.',
        question='Does five-second mainline/10490 accepted-merge overlap change with VSL and distinguish beneficial versus adverse states?',
        cells='Physical19--21,zero-based; lane1 VISSIMone-based.',
        scope='Eight saved policy records,450s each, three150s blocks. Known29late/43early/67late; not blind.',
        metrics='Both pre-crossing and post-crossing endpoint-lane assignments. Overlap=sum(A5*M5)-sum(A30*M30/6); six within30s cyclic alignments as descriptive reference only. Stock/slow counts at right5s endpoints in both native/model.',
        limits=['Observed crossings are endogenous accepted flow, NOT desired arrivals or exogenous demand.',
                'Five-second endpoint lane does not establish lane at the crossing; neither assignment is a rigorous microscopic bound.',
                'Known same-bin10490 departures ending beyond21 and10483 arrivals beginning before20 imply intervening mainline boundaries; preserve these port-supported crossings, never infer disappearance as a normal exit.',
                'Native integer variation includes count noise: do not interpret model fractional smoothing alone as missing dynamics.',
                'Temporal association is not a causal explanation of VSL gain; no capacity/reward coefficient fitted from it.',
                'All future values are posthoc labels, never operational prediction inputs.'],
        prior='Claude FWW_STRUCT_CHECK on burst/p95 noise; completed109/112 sub5s merge timing span0.0355vehh;188 conditioned merge/head timing;229 gap distribution. Do not repeat those trials.',
        budget=dict(native=0,FZP=0,forecasts=0,fits=0),protected_sha256=protected,STOP=stop)
    h.save(HERE/'protocol.json',protocol)
    pins={str(Path(__file__)):h.sha(__file__)};checks=[];bins=[];groups=[];initial={}
    try:
        for case in cases:
            tag=case['case']+'_'+case['arm'];start=case['cutoff'];end=start+450
            frame_path=case['frames'];event_path=case['truth']/'port_events.csv';flow_path=case['truth']/'flows_30s.csv'
            pred_path=h.R/f'queue_dynamics178/forecast/baseline/{tag}.json.gz'
            for p in (frame_path,event_path,flow_path,pred_path):pins[str(p)]=h.sha(p)
            raw=h.read(frame_path);ix={k:i for i,k in enumerate(raw['fields'])}
            speed=ix.get('speed',ix.get('speed_kmh'));cell=ix['cell'];lane=ix['lane'];pos=ix.get('x',ix.get('x_m'))
            frames={round(float(t),1):({str(k):v for k,v in z.items()} if isinstance(z,dict) else {str(int(v[ix['vehicle']])):v for v in z}) for t,z in raw['frames'].items()}
            signature={vid:[z[cell],z[lane],z[speed],z[pos]] for vid,z in frames[start].items()}
            if case['case'] in initial:assert initial[case['case']]==signature
            else:initial[case['case']]=signature
            events=csv_rows(event_path);nativeflows=csv_rows(flow_path)
            current=[]
            for j in range(90):
                t=round(start+5*j,1);nxt=round(t+5,1);a=frames[t];b=frames[nxt]
                row=dict(case=case['case'],arm=case['arm'],kind='native',time_start=t,time_end=nxt,block=j//30,
                    **{f'main{i}_all':0 for i in (19,20,21)},main20_pre_lane1=0,main20_post_lane1=0,merge10490=0,off10483=0,port_supported_crossings=0)
                for vid,z in a.items():
                    w=b.get(vid)
                    if w is None:continue
                    if not isinstance(z[cell],(int,float)) or not isinstance(w[cell],(int,float)):continue
                    for i in (19,20,21):
                        if z[cell]<=i<w[cell]:
                            row[f'main{i}_all']+=1
                            if i==20:
                                row['main20_pre_lane1']+=z[lane]==1
                                row['main20_post_lane1']+=w[lane]==1
                for i in (20,21):
                    occupants=[z for z in b.values() if z[cell]==i and z[lane]==1]
                    row[f'n{i}_lane1']=len(occupants)
                    row[f'slow{i}_lane1']=sum(z[speed]<5 for z in occupants)
                for e in events:
                    et=float(e['time_s'])
                    if t+1e-7<et<=nxt+1e-7:
                        if e['connector']=='10490' and e['kind']=='departure':row['merge10490']+=1
                        if e['connector']=='10483' and e['kind']=='departure':row['off10483']+=1
                        if '--port-endpoints' in sys.argv:
                            vid=e['vehicle'];prev=a.get(vid);after=b.get(vid)
                            if e['connector']=='10490' and e['kind']=='departure' and prev is None and after is not None and after[cell]>21:
                                row['main21_all']+=1;row['port_supported_crossings']+=1
                            if e['connector']=='10483' and e['kind']=='arrival' and prev is not None and after is None and prev[cell]<=19:
                                row['main19_all']+=1;row['port_supported_crossings']+=1
                current.append(row)
            # Compare reconstructed boundaries against the existing full native ledger.
            for j in range(15):
                stop_t=round(start+30*(j+1),1);part=current[6*j:6*j+6]
                by={int(z['cell']):z for z in nativeflows if z['road']=='FW_E' and abs(float(z['window_end_s'])-stop_t)<1e-6}
                for i in (19,20,21):
                    got=sum(r[f'main{i}_all'] for r in part);want=float(by[i]['downstream_crossings'])
                    checks.append(dict(case=tag,end=stop_t,field=f'main{i}',actual=got,reference=want))
                    assert got==want,(tag,stop_t,i,got,want)
                got=sum(r['merge10490'] for r in part);want=float(by[21]['ramp_merges'])
                checks.append(dict(case=tag,end=stop_t,field='merge10490',actual=got,reference=want));assert got==want
            predicted=h.read(pred_path);lanes=predicted['diagnostics']['roads'][0]['joint_lane_region']['rows']
            for block in range(3):
                part=current[30*block:30*(block+1)]
                for assignment in ('main20_pre_lane1','main20_post_lane1'):
                    groups.append(dict(case=case['case'],arm=case['arm'],kind='native',block=block,assignment=assignment,**metric(part,assignment)))
            pb=[]
            for j in range(90):
                lo=round(start+5*j,1);hi=round(lo+5,1)
                lr=[r for r in lanes if lo+1e-7<r['time_s']<=hi+1e-7]
                assert len(lr)==5*7*3
                row=dict(case=case['case'],arm=case['arm'],kind='model',block=j//30,time_start=lo,time_end=hi,
                    **{f'main{i}_all':sum(r['mainline_out_veh'] for r in lr if r['cell']==i) for i in (19,20,21)},
                    main20_post_lane1=sum(r['mainline_out_veh'] for r in lr if r['cell']==20 and r['lane']==1),
                    merge10490=sum(r['merge_veh'] for r in lr if r['cell']==21),
                    n21_lane1=next(r['n_veh'] for r in lr if r['cell']==21 and r['lane']==1 and abs(r['time_s']-hi)<1e-6),
                    off10483=None)
                # The off field is not needed for overlap; leave it unreported
                # rather than equating sparse30s drain to5s source admission.
                pb.append(row)
            for block in range(3):
                z=metric(pb[30*block:30*(block+1)],'main20_post_lane1');z.pop('off10483')
                z.pop('native_uniform_multinomial_variance_reference')
                groups.append(dict(case=case['case'],arm=case['arm'],kind='model',block=block,assignment='main20_post_lane1',**z))
            bins.extend(current);bins.extend(pb)
            h.save(HERE/'checks.json',checks);h.save(HERE/'status.json',dict(status='running',last=tag,cases_done=len(bins)//180))
        for p,d in {**pins,**protected,stop['path']:stop['sha256']}.items():assert h.sha(p)==d,p
        with gzip.open(HERE/'bins.json.gz','wt',encoding='utf8') as f:json.dump(bins,f,allow_nan=False)
        h.save(HERE/'groups.json',groups);h.save(HERE/'pins.json',pins)
        contrasts=[]
        for case,a,b in [('s29_late','hold','hold_vsl90'),('s43_early','none','vsl'),('s67_late','hold','hold_vsl90'),('s67_late','release','release_vsl90')]:
            for kind,assignment in [('native','main20_pre_lane1'),('native','main20_post_lane1'),('model','main20_post_lane1')]:
                for block in range(3):
                    pair={g['arm']:g for g in groups if g['case']==case and g['kind']==kind and g['assignment']==assignment and g['block']==block}
                    keys=('main','merge','overlap_excess','within30s_covariance','main5s_variance_within30','mean_n21_lane1','main19','main20','main21')
                    contrasts.append(dict(case=case,change=b+'-'+a,kind=kind,assignment=assignment,block=block,
                        delta={k:pair[b][k]-pair[a][k] for k in keys}))
        h.save(HERE/'contrasts.json',contrasts)
        result=dict(status='complete',cases=8,bins=len(bins),native_ledger_checks=len(checks),seconds=time.perf_counter()-began,
            native=0,FZP=0,fits=0,forecasts=0,production_adopted=False,goal='ACTIVE_NOT_QUALIFIED')
        h.save(HERE/'completion.json',result);h.save(HERE/'status.json',result);print(json.dumps(result))
    except BaseException as e:
        h.save(HERE/'pins_partial.json',pins);h.save(HERE/'checks_partial.json',checks)
        h.save(HERE/'status.json',dict(status='failed',error=repr(e),cases_done=len(bins)//180));raise


if __name__=='__main__':main()
