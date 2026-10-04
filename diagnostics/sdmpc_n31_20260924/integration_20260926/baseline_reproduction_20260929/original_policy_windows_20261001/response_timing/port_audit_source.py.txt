"""Head/merge/storage balance audit of already saved original-policy forecasts."""
import csv
import gzip
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from diagnostics.sdmpc_n31_20260924.integration_20260926 import replay_congested_component as r
from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
HERE=Path(__file__).resolve().parent
OUT=HERE/'response_timing'
assert not (OUT/'port_response.json').exists()
cap=r.load(HERE/'capture.json');summary=r.load(HERE/'summary.json')
tree=ET.parse(next(p for p in cap['source_pins'] if p.endswith('none.inpx')))
records=[z for z in cap['records'] if z['mode']=='own_state150'];result=[];pins={}
obs={z['truth']:ObservationData(z['truth']) for z in records}
for rec in records:
    data=obs[rec['truth']];a,k=r.read_primitive_capture(rec['input'],rec['sha256'])
    p=HERE/'predictions'/(rec['case']+'.json.gz');pins[str(p)]=r.sha(p)
    with gzip.open(p,'rt') as f:pred=json.load(f)
    start=rec['cutoff'];end=round(start+rec['horizon'],6)
    for connector in ['10639','10681','10490','10484']:
        mid='RM_C'+connector;spec=k['ramp_dynamics']['ramps'][mid];head=spec['head_position_m']
        nativeheads=[h for h in tree.findall('./signalHeads/signalHead') if h.get('lane').split()[0]==connector]
        assert nativeheads and all(abs(float(h.get('pos'))-head)<1e-7 for h in nativeheads)
        def parts(t):
            co=data.port_cohorts[str(t)][connector]
            assert len(co)==int(float(data.ports[t,connector]['end_n_veh']))
            return dict(pre=sum(float(z[0])<head for z in co),post=sum(float(z[0])>=head for z in co))
        n0,n1=parts(start),parts(end)
        rr=[z for (t,c),z in data.ports.items() if c==connector and start<t<=end]
        arrivals=sum(float(z['arrivals_veh']) for z in rr);merge=sum(float(z['departures_veh']) for z in rr)
        unknown=sum(float(z['unresolved_absences_veh']) for z in rr)
        valid=unknown==0
        head_cross=arrivals+n0['pre']-n1['pre']
        if valid:
            assert head_cross>=0 and n0['post']+head_cross-merge==n1['post']
        pp=[z for z in pred['ramps'] if z['ramp']==mid]
        pre=lambda z:z['upstream_travelling_veh']+z['head_ready_veh']
        post=lambda z:z['downstream_travelling_veh']+z['merge_ready_veh']
        assert abs(pre(pp[0]['start'])-n0['pre'])<1e-7
        assert abs(post(pp[0]['start'])-n0['post'])<1e-7
        pa=sum(z['admitted_arrivals_veh'] for z in pp);ph=sum(z['head_service_veh'] for z in pp);pm=sum(z['accepted_merge_veh'] for z in pp)
        assert abs(n0['pre']+pa-ph-pre(pp[-1]['end']))<1e-7
        assert abs(n0['post']+ph-pm-post(pp[-1]['end']))<1e-7
        actual=dict(arrivals=arrivals,head=head_cross,merge=merge,pre_end=n1['pre'],post_end=n1['post'])
        prediction=dict(arrivals=pa,head=ph,merge=pm,pre_end=pre(pp[-1]['end']),post_end=post(pp[-1]['end']))
        errors={key:prediction[key]-value for key,value in actual.items()}
        if valid:
            assert abs(errors['pre_end']-(errors['arrivals']-errors['head']))<1e-7
            assert abs(errors['post_end']-(errors['head']-errors['merge']))<1e-7
        result.append(dict(case=rec['case'],arm=rec['arm'],cutoff=start,connector=connector,initial=n0,
            actual=actual,predicted=prediction,error=errors,unknown_absences=unknown,
            head_count_is_balance_inferred=True,valid_head_balance=valid))
for p,h in pins.items():assert r.sha(p)==h
metrics=[]
for c in ['10639','10681','10490','10484']:
    rr=[z for z in result if z['connector']==c and z['valid_head_balance']]
    metrics.append(dict(connector=c,count=len(rr),mae={key:sum(abs(z['error'][key]) for z in rr)/len(rr) for key in rr[0]['error']},
        bias={key:sum(z['error'][key] for z in rr)/len(rr) for key in rr[0]['error']}))
r.save(OUT/'port_response.json',dict(rows=result,metrics=metrics,pins=pins,forecasts_reused=28,new_forecasts=0,
    limitations='Head crossings derived from connector balances and equal native head positions. Unknown absence windows not used for this head balance. Endpoint errors are not alone a receiving-law calibration.',
    source_head_positions_verified=True))
(OUT/'port_audit_source.py.txt').write_bytes(Path(__file__).read_bytes())
print(json.dumps(metrics))
for z in result:
    if z['connector']=='10681' and z['cutoff'] in [2700.1,4500.1]:print(json.dumps(z))

