"""Localize the completed144 control response without another prediction."""
import csv
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
R=HERE.parent
U=R.parents[1]
I=U/'diagnostics/sdmpc_n31_20260924/integration_20260926'
F=I/'baseline_reproduction_20260929/cellwise_calibration/freeway_first'
PINS={}


def read(path):
    b=path.read_bytes();PINS[str(path)]=hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if path.suffix=='.gz' else b)


def delta_by_cells(left,right):
    series=[]
    for cells in (range(19),[19],range(20,26),range(26,31)):
        total=0.;old=0.;told=2670.1
        for t in (round(2700.1+30*k,1) for k in range(15)):
            d=sum(right[t,i]-left[t,i] for i in cells)
            total+=(old+d)/2*(t-told)/3600;old=d;told=t
        series.append(dict(cells=list(cells),delta_ttt=total,end_delta_n=old))
    return series


def main():
    out=HERE/'audit_repair'
    assert read(out/'status.json')['status']=='complete_macro_gate_failed'
    result={}
    for label,folder in [('baseline132',R/'lane_state132/autonomous_diagnostic'),('spatial144',out)]:
        arms={};bycell={}
        for arm in ('release','release_vsl90'):
            p=read(folder/'training'/f's67_late_{arm}.json.gz')
            reg=p['diagnostics']['roads'][0]['joint_lane_region']
            first=[]
            for cell in (19,20,21):
                q=[x for x in reg['rows'] if x['cell']==cell and x['lane']==1 and x['time_s']<=2700.1+1e-6]
                first.append(dict(cell=cell,n1=q[-1]['n_veh'],v1=q[-1]['v_kmh'],
                    incoming=sum(x['mainline_in_veh'] for x in q),outgoing=sum(x['mainline_out_veh'] for x in q)))
            middle=[x for x in reg['junction_rows'] if 2820.1-1e-6<=x['time_s']<2970.1-1e-6]
            arms[arm]=dict(first30=first,middle150_exit_request=sum(x['off_request_veh'] for x in middle),
                middle150_exit_accepted=sum(x['off_accepted_veh'] for x in middle),
                middle150_lane19_out=sum(x['mainline_out_veh'] for x in reg['rows']
                    if x['cell']==19 and x['lane']==1 and 2820.1<x['time_s']<=2970.1+1e-6))
            bycell[arm]={(round(x['time_s'],1),x['cell']):x['n_veh'] for x in p['cells']}
        records=read(folder/'training/rows.json')
        pair={x['arm']:x for x in records if x['case']=='s67_late'}
        deltas={k:pair['release_vsl90']['predicted'][k]-pair['release']['predicted'][k]
                for k in ('ttt','mainline_ttt','ramp_ttt','off_ttt','end_n','exits')}
        regional=delta_by_cells(bycell['release'],bycell['release_vsl90'])
        assert abs(sum(x['delta_ttt'] for x in regional)-deltas['mainline_ttt'])<1e-8
        result[label]=dict(arms=arms,delta=deltas,regional=regional,
            max_conservation=max(x['conservation_max'] for x in records),max_route=max(x['route_error'] for x in records))
        if label=='spatial144':
            result[label]['spatial_samples']=sum(x['spatial144']['samples'] for x in records)
            result[label]['max_half_class_partition_error']=max(x['spatial144']['max_class_partition_error'] for x in records)
            half_errors=[]
            bounds=read(F/'route_inventory/mapping31.json')['freeway_model_links']['FW_E']['segment_bounds_m']
            middle=(bounds[19]+bounds[20])/2
            for arm in ('release','release_vsl90'):
                frame=read(F/'flow67'/f'{arm}_frames.json.gz')['frames']
                half=read(out/'training'/f's67_late_{arm}_spatial.json.gz')
                for z in half:
                    t=round(z['time_s'],1)
                    if str(t) not in frame or abs((t-2670.1)/30-round((t-2670.1)/30))>1e-6:continue
                    actual=[x for x in frame[str(t)].values() if x[0]==19 and x[3]==z['lane'] and int(x[2]>=middle)==z['part']]
                    half_errors.append(dict(arm=arm,time_s=t,lane=z['lane'],part=z['part'],actual_n=len(actual),model_n=z['n_veh'],
                        actual_v=sum(x[1] for x in actual)/len(actual) if actual else None,model_v=z['v_kmh']))
            result[label]['half_state_pairs']=half_errors
    native={}
    for arm in ('release','release_vsl90'):
        p=I/'heldout67_freeway_20260930/observations'/arm/'cells_30s.csv'
        PINS[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
        with p.open(encoding='utf-8-sig') as f:native[arm]={(round(float(x['time_s']),1),int(x['cell'])):float(x['n_veh']) for x in csv.DictReader(f) if x['road']=='FW_E'}
    assert all(native['release'][2670.1,i]==native['release_vsl90'][2670.1,i] for i in range(31))
    result['native_regional']=delta_by_cells(native['release'],native['release_vsl90'])
    result['input_sha256']=PINS
    result['limitations']='Spatial half observations used only after completed rollouts. Physical31 output retained. Native departure-lane ambiguity from143 remains. Regional decomposition is accounting, not causal contribution.'
    (out/'local_assessment.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    for name in ('baseline132','spatial144'):
        print(name,result[name]['delta'],result[name]['regional'])
    print('actual',result['native_regional'])


if __name__=='__main__':main()
