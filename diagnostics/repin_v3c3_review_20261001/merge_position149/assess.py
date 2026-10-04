"""Bounded post-run assessment from existing30s truth and cached5s positions."""
import csv
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    out=HERE/'forecast/key_repair';baseline=h.R/'spatial_context148/forecast'
    status=h.read(out/'status.json');assert status['status'].startswith('complete_') and status['forecasts']==9
    protocol=h.read(out/'protocol.json');preserved=h.read(out/'preservation.json')
    assert all(h.read(out/'parity.json').values()) and all(preserved[k] for k in ('core','inputs','STOP','hooks_restored'))
    pins={**protocol['protected_sha256'],**preserved['input_sha256']}
    def read(p):pins[str(p)]=h.sha(p);return h.read(p)
    def csvread(p):
        pins[str(p)]=h.sha(p)
        with open(p,encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
    rows=read(out/'training/rows.json');old=read(baseline/'training/rows.json')
    contrasts=[];windows=[];off=[];parts=[]
    for case in ('s29_late','s67_late'):
        a={r['arm']:r for r in rows if r['case']==case};b={r['arm']:r for r in old if r['case']==case}
        for left,right in [('hold','release'),('hold','hold_vsl90'),('release','release_vsl90')]:
            contrasts.append(dict(case=case,left=left,right=right,actual=a[right]['actual']['ttt']-a[left]['actual']['ttt'],
                corrected148=b[right]['predicted']['ttt']-b[left]['predicted']['ttt'],interior149=a[right]['predicted']['ttt']-a[left]['predicted']['ttt']))
    split=read(h.R/'flow_regime147/geometry_verification.json')['native_chain_position_m']
    for arm in ('release','release_vsl90'):
        truth=h.I/'heldout67_freeway_20260930/observations'/arm
        native=csvread(truth/'flows_30s.csv');cells=csvread(truth/'cells_30s.csv')
        cache=read(h.F/'flow67'/f'{arm}_frames.json.gz')['frames']
        frames={round(float(t),6):d for t,d in cache.items()}
        versions={'corrected148':read(baseline/'training'/f's67_late_{arm}.json.gz'),
                  'interior149':read(out/'training'/f's67_late_{arm}.json.gz')}
        spatial=read(out/'training'/f's67_late_{arm}_merge_spatial.json.gz')
        initial=next(r for r in rows if r['case']=='s67_late' and r['arm']==arm)['spatial149']['initial']
        for p in (0,1):
            for lane in (1,2,3):
                z=[v for v in frames[2670.1].values() if v[0]==23 and v[3]==lane and int(v[2]>=split)==p]
                assert sum(initial['stocks'][p][lane-1].values())==len(z)
                if z:assert abs(initial['speeds'][p][lane-1]-sum(v[1] for v in z)/len(z))<1e-8
        for lo,hi in ((2670.1,2820.1),(2820.1,2970.1),(2970.1,3120.1)):
            for i in (20,21,22,23,24,25):
                rr=[r for r in native if r['road']=='FW_E' and int(r['cell'])==i and float(r['window_start_s'])>=lo-1e-6 and float(r['window_end_s'])<=hi+1e-6]
                assert len(rr)==5
                endpoint=next(r for r in cells if r['road']=='FW_E' and int(r['cell'])==i and abs(float(r['time_s'])-hi)<1e-6)
                item=dict(arm=arm,lo=lo,hi=hi,cell=i,actual=dict(inflow=sum(float(r['upstream_crossings']) for r in rr),
                    outflow=sum(float(r['downstream_crossings']) for r in rr),merge=sum(float(r['ramp_merges']) for r in rr),
                    end_n=float(endpoint['n_veh']),end_v=float(endpoint['v_kmh'])))
                for version,pred in versions.items():
                    trace=pred['diagnostics']['roads'][0]['joint_lane_region']['rows']
                    selected=[r for r in trace if r['cell']==i and lo+1e-6<r['time_s']<=hi+1e-6]
                    assert len(selected)==450
                    endpoint=next(r for r in pred['cells'] if r['cell']==i and abs(r['time_s']-hi)<1e-6)
                    item[version]=dict(inflow=sum(r['mainline_in_veh'] for r in selected),outflow=sum(r['mainline_out_veh'] for r in selected),
                        merge=sum(r['merge_veh'] for r in selected),end_n=endpoint['n_veh'],end_v=endpoint['v_kmh'])
                windows.append(item)
            for version,pred in versions.items():
                rr=[r for r in pred['diagnostics']['roads'][0]['joint_lane_region']['junction_rows'] if lo-1e-6<=r['time_s']<hi-1e-6]
                assert len(rr)==150
                off.append(dict(arm=arm,lo=lo,hi=hi,version=version,request=sum(r['off_request_veh'] for r in rr),accepted=sum(r['off_accepted_veh'] for r in rr)))
        for time in (2675.1,2700.1,2820.1,2970.1,3120.1):
            for p in (0,1):
                z=[v for v in frames[time].values() if v[0]==23 and int(v[2]>=split)==p]
                m=[r for r in spatial if r['part']==p and abs(r['time_s']-time)<1e-6]
                assert len(m)==3
                n=sum(r['n_veh'] for r in m)
                parts.append(dict(arm=arm,time_s=time,part=p,actual_n=len(z),actual_v=sum(v[1] for v in z)/len(z) if z else None,
                    predicted_n=n,predicted_v=sum(r['n_veh']*r['v_kmh'] for r in m)/n if n else None))
    for path,digest in pins.items():assert h.sha(path)==digest,path
    assert h.sha(protocol['STOP']['path'])==protocol['STOP']['sha256']
    assert h.sha(h.__file__)==read(HERE/'key_repair_preflight.json')['helper_sha256']==h.sha(HERE/'executed_helper_key_repair.py.txt')
    result=dict(status=status,contrasts=contrasts,windows=windows,off=off,parts=parts,initial_partition_exact=True,
        gate=read(out/'training_assessment.json'),max_mass=max(r['conservation_max'] for r in rows),
        max_route=max(r['route_error'] for r in rows),max_part=max(r['spatial149']['max_class_partition_error'] for r in rows),
        part_samples=sum(r['spatial149']['samples'] for r in rows),verified_pin_count=len(pins),
        model_adopted=False,goal='ACTIVE/NOT_QUALIFIED',new_forecasts=0,new_native=0,new_FZP=0,new_9000_analysis=0,push=0)
    assert max(result[k] for k in ('max_mass','max_route','max_part'))<1e-7
    h.save(HERE/'assessment.json',result);h.save(HERE/'assessment_pins.json',pins)
    for row in contrasts:print(row)
    for row in windows:
        if row['arm']=='release' and row['cell']==23:print('CELL23',row)
    for row in off:
        if row['lo']==2820.1:print('OFF',row)
    print('verified',len(pins),'pins','mass',result['max_mass'],'part samples',result['part_samples'])


if __name__=='__main__':main()
