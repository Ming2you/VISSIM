"""Summarize completed141/142 without any additional rollout or FZP access."""
import gzip
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
R=HERE.parent
U=R.parents[1]
I=U/'diagnostics/sdmpc_n31_20260924/integration_20260926'
F=I/'baseline_reproduction_20260929/cellwise_calibration/freeway_first'
PINS={}


def read(p):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)


def main():
    previous=read(R/'inlet_receiving140/local_assessment.json')
    native_first30=[x for x in previous['native'] if x['lane']==1]
    results={}
    for label,folder in [('frozen132',R/'lane_state132/autonomous_diagnostic'),
                         ('inlet141',R/'inlet_flux141'),('class142',HERE)]:
        rows=read(folder/'training/rows.json')
        arms={}
        for arm in ('release','release_vsl90'):
            p=read(folder/'training'/f's67_late_{arm}.json.gz')
            reg=p['diagnostics']['roads'][0]['joint_lane_region'];first=[]
            for cell in (19,20,21):
                rr=[x for x in reg['rows'] if x['cell']==cell and x['lane']==1 and x['time_s']<=2700.1+1e-6]
                assert len(rr)==30
                first.append(dict(cell=cell,n1=rr[-1]['n_veh'],v1=rr[-1]['v_kmh'],
                    incoming=sum(x['mainline_in_veh'] for x in rr),outgoing=sum(x['mainline_out_veh'] for x in rr)))
            middle=[x for x in reg['junction_rows'] if 2820.1-1e-6<=x['time_s']<2970.1-1e-6]
            assert len(middle)==150
            arms[arm]=dict(first30=first,middle150_off_request=sum(x['off_request_veh'] for x in middle),
                middle150_off_accepted=sum(x['off_accepted_veh'] for x in middle))
        result=dict(arms=arms,max_conservation=max(x['conservation_max'] for x in rows),
            max_route_error=max(x['route_error'] for x in rows))
        if label=='inlet141':result['initial_shares']={x['case']:x['inlet141'] for x in rows if x['arm']=='release'}
        if label=='class142':
            result['source_142']={x['case']:x['source142'] for x in rows if x['arm']=='release'}
            result['first30_requests']={}
            for arm in ('release','release_vsl90'):
                rr=read(folder/'training'/f's67_late_{arm}_source.json.gz')
                keys={k for x in rr for k in x['classes']};part={}
                for key in keys:
                    part[key]={metric:sum(x['classes'].get(key,{}).get(metric,0.) for x in rr if x['time_s']<2700.1-1e-6)
                        for metric in ('old_request','new_request')}
                result['first30_requests'][arm]=part
        results[label]=result
    # Initial route and speed evidence only. No future destination labels.
    raw=read(F/'route_inventory/s67_late/initial_raw.json')
    frame=read(F/'flow67/release_frames.json.gz')['frames']['2670.1']
    routes={str(x['veh_no']):x for x in raw['vehicle_routes']['records']}
    network=I/'selected/network/native_seed29.inpx';data=network.read_bytes()
    PINS[str(network)]=hashlib.sha256(data).hexdigest()
    assert PINS[str(network)]=='64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
    tree=ET.fromstring(data)
    paths={d.get('no')+':'+p.get('no'):[d.get('link')]+[x.get('key') for x in p.findall('./linkSeq/intObjectRef')]+[p.get('destLink')]
        for d in tree.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic') for p in d.findall('./vehRoutSta/vehicleRouteStatic')}
    groups={}
    for vid,x in frame.items():
        if x[0]!=18:continue
        route=routes[vid];key=str(route['route_decision_no'])+':'+str(route['route_no']);path=paths[key]
        assert key in ('1131:1','1131:3')
        target='10483' if '10483' in path else '1131_through'
        groups.setdefault(target,[]).append(dict(vehicle=vid,lane=x[3],speed=x[1],route=key))
    summary={k:dict(n=len(v),mean_speed=sum(x['speed'] for x in v)/len(v),vehicles=v) for k,v in groups.items()}
    assert summary['10483']['n']==5 and summary['1131_through']['n']==13
    result=dict(status='BOTH_REJECTED_NOT_ADOPTED',native_first30=native_first30,models=results,
        initial_route_speed=summary,new_rollouts=0,new_native=0,new_FZP=0,input_sha256=PINS,
        limits='Observed routes/speeds are initial-only. Model request tables are not actual desired demand.142 old-request is a within-state comparison, not132 trajectory. Both are frozen initial-statistic hypotheses, not dynamic lane/class state models.')
    (HERE/'local_assessment.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    for label,z in results.items():
        print(label,z['arms'])
    print('142 request',results['class142']['first30_requests'])
    print('native initial',{k:{q:z[q] for q in ('n','mean_speed')} for k,z in summary.items()})


if __name__=='__main__':main()
