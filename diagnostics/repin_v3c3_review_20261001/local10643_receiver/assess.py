"""Finite receipt audit; no optimizer, fitting or native simulation."""
import collections
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
pins={}

def read(path):
    raw=path.read_bytes();pins[str(path)]=hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if path.suffix=='.gz' else raw)

def main():
    target=HERE/'assessment.json'
    if target.exists():raise FileExistsError(target)
    protocol=read(HERE/'protocol.json')
    for text,sha in protocol['source_before'].items():
        if Path(text).name!='probe_selected_arrival_path.py':
            assert hashlib.sha256(Path(text).read_bytes()).hexdigest()==sha,text
    native=read(HERE/'native_audit.json');heads=read(HERE/'head_audit.json')
    previous=read(HERE.parent/'unrouted10646/assessment.json')
    cases={};wall=0.;maximum_resource=0.;exact_cases=0
    for seed in ('47','43'):
        prefix=('closedloop_recorded2700_select_check_trace10681_' if seed=='47'
                else 'closedloop_recorded2250_lever450_trace10681_')
        baseline=I/(prefix+'unrouted'+seed);folder=I/(prefix+'receiver'+seed)
        before=read(baseline/'summary.json');after=read(folder/'summary.json')
        cases[seed]={}
        for key,summary in after['results'].items():
            reference=before['results'][key]
            assert {k:v for k,v in summary.items() if k!='wall_sec'}=={k:v for k,v in reference.items() if k!='wall_sec'}
            wall+=summary['wall_sec']
            trace=read(folder/(key+'_RM_C10681_trace.json.gz'))
            local=trace.pop('local_receiver_diagnostics')
            assert trace==read(baseline/(key+'_RM_C10681_trace.json.gz'))
            exact_cases+=1
            maximum_resource=max(maximum_resource,max(r['exceedance_veh'] for r in local['resources']))
            arm=('hold' if key=='held_actual' else key) if seed=='47' else ('nc' if key=='held_actual' else key)
            native_key=seed+arm
            rows=local['resources'];lane_drain={}
            for lane in (1,2):
                offered=[r for r in rows if r['kind']=='lane_urban_sending' and r['resource']==str(('external',f'off:{lane-1}'))]
                receiving=[r for r in rows if r['kind']=='lane_urban_receiving' and r['resource']==str((126,lane,7))]
                recv={r['start_sec']:r for r in receiving}
                assert len(offered)==len(receiving)==450
                lane_drain[str(lane)]=dict(drained_veh=sum(r['accepted_total_veh'] for r in offered),
                    offer_exceeds_receipt_seconds=sum(r['available_veh']>r['accepted_total_veh']+1e-7 for r in offered),
                    mean_receiving_veh_per_step=sum(r['available_veh'] for r in receiving)/450,
                    receiving_below_point1_while_offered_seconds=sum(recv[r['start_sec']]['available_veh']<.1 and r['available_veh']>.1 for r in offered))
            snapshots=[]
            for s in local['states']:
                counts=collections.Counter()
                for c in s['cells']:counts[str(c['cell'][0])]+=c['stock']
                snapshots.append(dict(time_sec=s['time_sec'],roads=dict(counts),
                    off_stock=sum(p['stock'] for p in s['off_lanes']),
                    off_departed=sum(p['departed'] for p in s['off_lanes'])))
            green={r['start_sec'] for r in rows if r['kind']=='lane_urban_exit_receiving'
                   and r['resource']=='10634' and r['available_veh']>1e-8}
            discharge={};native_head=heads['cases'].get(native_key)
            for lane in (1,2,3):
                offered=[r for r in rows if r['kind']=='lane_urban_sending' and r['resource']==str((71,lane,3)) and r['start_sec'] in green]
                exit_key=str(('exit',10634))
                actual=sum(r['accepted_by_source_veh'].get(exit_key,0.) for r in offered)
                discharge[str(lane)]=dict(model_exit_on_green_veh=actual,
                    modeled_green_receiving_seconds=len(green),
                    offer_without_exit_seconds=sum(r['available_veh']>1e-8 and r['accepted_by_source_veh'].get(exit_key,0)<1e-8 for r in offered))
                if native_head:
                    selected=[h for w in native_head for h in w['heads'] if h['lane']==lane]
                    assert len(selected)==3
                    discharge[str(lane)].update(native_green_head_crossings=sum(h['qualified_crossings'] for h in selected),
                        native_total_head_crossings=sum(h['crossings'] for h in selected),
                        native_green_seconds=sum(h['green_sec'] for h in selected),
                        native_boundary_ambiguous=sum(h['boundary_ambiguous'] for h in selected))
            row=dict(port=previous['cases'][seed][arm]['ports']['10643'],
                lane_drain=lane_drain,model_snapshots=snapshots,straight_discharge=discharge,
                model_future_shares=local['states'][0]['future_shares'],
                endpoint_blocked_events=local['states'][-1]['blocked'])
            if native_key in native['cases']:row['native_snapshots']=native['cases'][native_key]
            cases[seed][arm]=row
    assert exact_cases==6 and maximum_resource<1e-7
    a=cases['47']['hold']['port'];b=cases['47']['selected']['port']
    result=dict(status='SHARED_RECEIVER_AND_ROUTE_CLASS_LOSS_IDENTIFIED_NOT_CALIBRATED',cases=cases,
        same_results_and_old_response_fields_exact=exact_cases,forecasts=exact_cases,wall_sec=wall,
        max_local_resource_exceedance_veh=maximum_resource,
        city_selection_drain_delta=dict(native=b['native']['drain']-a['native']['drain'],
                                        model=b['after']['drain']-a['after']['drain']),
        limitations=['Native head counts and modeled connector exits are nearby distinct cross-sections; not identical event counts.',
                     'Zero modeled straight discharge with sending on green is not automatically caused by mandatory lane change.',
                     'Repeated blocked offered volumes are not unique vehicles or a capacity estimate.',
                     '15 active-route witnesses are snapshot records, not15 distinct vehicles.',
                     'Route-class correction has not yet been integrated across the downstream queues.'],
        source_pins=pins,new_native=0,new_fzp_scan=0,fit=0,optimizer=0,goal_complete=False)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('EXACT',exact_cases,'wall',wall,'resource',maximum_resource)
    print('47city drain delta',result['city_selection_drain_delta'])
    for seed,arms in cases.items():
        for arm,row in arms.items():
            print(seed,arm,'port',row['port']['native'],row['port']['after'],'lane2',row['lane_drain']['2'])
    for seed,arm in [('47','hold'),('47','selected'),('43','nc')]:print(seed,arm,'head',cases[seed][arm]['straight_discharge'])

if __name__=='__main__':main()
