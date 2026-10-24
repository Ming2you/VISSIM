"""Assess completed146 forecasts and their current-state regime occupancy."""
import copy
from collections import defaultdict
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent
PINS={}


def read(p):
    PINS[str(p)]=h.sha(p)
    return h.read(p)


def main():
    out=HERE/'forecast';status=read(out/'status.json')
    assert status['status'].startswith('complete') and status['forecasts']==9
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    from evaluation.controllers import lane_plant_runtime as lpr
    context,_,_=common.setup()
    manifest=h.R/'lane_state132/eval_01/manifest.json';read(manifest)
    cfg=lpr.load_sources(manifest)['component']._config('FW_E',context['parameters']['by_direction']['FW_E'])
    params=cfg.network.freeway_segment_params['FW_E'];critical=[params[i]['rho_crit'] for i in (22,23)]
    raw=read(h.R/'recovery_terms137/rows.json.gz')
    lookup={(r['case'],r['arm'],round(r['time_s'],6),r['cell'],r['lane']):r for r in raw}
    assert len(lookup)==len(raw)
    rows=read(out/'training/rows.json');baseline=read(h.R/'spatial_speed144/audit_repair/training/rows.json')
    groups=defaultdict(list);first=[];middle=[];cases=[]
    for r in rows:
        case,arm=r['case'],r['arm']
        pred=read(out/'training'/f'{case}_{arm}.json.gz')
        old=read(h.R/'spatial_speed144/audit_repair/training'/f'{case}_{arm}.json.gz')
        reg=pred['diagnostics']['roads'][0]['joint_lane_region']
        oldreg=old['diagnostics']['roads'][0]['joint_lane_region']
        oldstates={(round(x['time_s'],6),x['cell'],x['lane']):x for x in oldreg['rows']}
        trace=read(out/'training'/f'{case}_{arm}_pressure.json.gz')
        for x in trace:
            t=round(x['time_s']-1,6);lane=x['lane']
            a=lookup.get((case,arm,t,22,lane));b=lookup.get((case,arm,t,23,lane))
            if a is None or b is None:continue
            nr=[v['n0']/params[i]['segment_length_km'] for i,v in ((22,a),(23,b))]
            native_active=nr[0]<=critical[0] and nr[1]>critical[1] and nr[1]>nr[0]
            base=[oldstates.get((t,i,lane)) for i in (22,23)]
            br=[q['n_veh']/params[i]['segment_length_km'] if q is not None else nr[j] for j,(i,q) in enumerate(zip((22,23),base))]
            base_active=br[0]<=critical[0] and br[1]>critical[1] and br[1]>br[0]
            z=dict(time_s=t,lane=lane,native_rho=nr,baseline_rho=br,candidate_rho=[x['rho'],x['downstream_rho']],
                   native_active=native_active,baseline_active=base_active,candidate_active=x['active'])
            groups[case,arm,'all'].append(z)
            groups[case,arm,str(int(round((t-2670.1)/5))//30)].append(z)
        for label,region in [('baseline144',oldreg),('candidate146',reg)]:
            for cell in (19,20,21,22,23,24,25):
                a=[x for x in region['rows'] if x['cell']==cell and x['lane']==1 and x['time_s']<=2700.1+1e-6]
                assert len(a)==30
                first.append(dict(case=case,arm=arm,model=label,cell=cell,n=a[-1]['n_veh'],v=a[-1]['v_kmh']))
            a=[x for x in region['junction_rows'] if 2820.1-1e-6<=x['time_s']<2970.1-1e-6]
            assert len(a)==150
            middle.append(dict(case=case,arm=arm,model=label,request=sum(x['off_request_veh'] for x in a),
                accepted=sum(x['off_accepted_veh'] for x in a)))
    regime=[]
    for (case,arm,window),rr in sorted(groups.items()):
        summary=dict(case=case,arm=arm,window=window,samples=len(rr))
        for label in ('native','baseline','candidate'):
            summary[label+'_active']=sum(x[label+'_active'] for x in rr)
            if label!='native':
                summary[label+'_false_activation']=sum(x[label+'_active'] and not x['native_active'] for x in rr)
                summary[label+'_missed_activation']=sum(not x[label+'_active'] and x['native_active'] for x in rr)
        regime.append(summary)
    for case in sorted({r['case'] for r in rows}):
        a={x['arm']:x for x in rows if x['case']==case};b={x['arm']:x for x in baseline if x['case']==case}
        for left,right in [('hold','release'),('hold','hold_vsl90'),('release','release_vsl90')]:
            cases.append(dict(case=case,left=left,right=right,
                actual={k:a[right]['actual'][k]-a[left]['actual'][k] for k in ('ttt','ramp_ttt','end_n','exits')},
                baseline={k:b[right]['predicted'][k]-b[left]['predicted'][k] for k in ('ttt','ramp_ttt','end_n','exits')},
                candidate={k:a[right]['predicted'][k]-a[left]['predicted'][k] for k in ('ttt','ramp_ttt','end_n','exits')}))
    protocol=read(out/'protocol.json');preservation=read(out/'preservation.json')
    assert all(preservation[k] for k in ('core','inputs','STOP','hooks_restored'))
    assert all(read(out/'parity.json').values())
    for p,digest in {**PINS,**protocol['protected_sha256'],**preservation['input_sha256']}.items():assert h.sha(p)==digest,p
    assert h.sha(protocol['STOP']['path'])==protocol['STOP']['sha256']
    result=dict(status=status,contrast=cases,regime_occupancy=regime,first30=first,middle150=middle,
        conservation_max=max(x['conservation_max'] for x in rows),route_max=max(x['route_error'] for x in rows),
        half_class_partition_max=max(x['spatial144']['max_class_partition_error'] for x in rows),
        half_state_checks=sum(x['spatial144']['samples'] for x in rows),pressure_checks=sum(x['pressure146']['samples'] for x in rows),
        input_sha256=copy.deepcopy(PINS),limits='Regime labels after rollout are diagnostics only. Activation disagreements reflect self-generated trajectory differences and do not establish a single causal source. No coefficient chosen from these outcomes.',
        new_forecasts=0,new_native=0,new_FZP=0,new_9000_analysis=0,push=0)
    h.save(HERE/'assessment.json',result)
    h.save(HERE/'regime_samples.json',[dict(case=case,arm=arm,**x)
        for (case,arm,window),rr in groups.items() if window=='all' for x in rr])
    print('CONSERVATION',result['conservation_max'],'PRESSURE',result['pressure_checks'])
    for x in cases:print('CONTRAST',x)
    for x in regime:
        if x['window']=='all':print('REGIME',x)
    for x in middle:
        if x['case']=='s67_late' and x['arm'].startswith('release'):print('MIDDLE',x)


if __name__=='__main__':main()
