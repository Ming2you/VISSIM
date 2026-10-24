"""Verify two saved RM-only forecasts against the completed native pair."""
import gzip
import hashlib
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
REVIEW=HERE.parents[1]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
OUTPUT=I/'closedloop_recorded2700_lever450_trace10484_rm224_native_routes'
PINS={}


def read(path):
    raw=path.read_bytes();PINS[str(path)]=hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if path.suffix=='.gz' else raw)


def costs(point):
    c=point['cost_by_stock'];f=point['control_area']['flow_counts']
    assert abs(math.fsum(c.values())-point['ttt_omega_veh_h'])<1e-7
    return dict(omega=point['ttt_omega_veh_h'],east=c['freeway:FW_E'],west=c['freeway:FW_W'],
        ramps=math.fsum(v for k,v in c.items() if k.startswith('ramp:')),
        outside=point['tracked_outside_residence_veh_h'],
        source=f['origin:FW_E->freeway:FW_E'],
        merge=math.fsum(v for k,v in f.items() if k.startswith('merge_pending:') and k.endswith('->freeway:FW_E')),
        off=math.fsum(v for k,v in f.items() if k.startswith('freeway:FW_E->storage:')),
        terminal=f['freeway:FW_E->external:terminal:FW_E'])


def main():
    protocol=read(HERE/'protocol.json')
    for path,digest in protocol['source_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
    for pin in (protocol['model'],protocol['STOP']):
        path=Path(pin.get('config',pin.get('path')))
        assert hashlib.sha256(path.read_bytes()).hexdigest()==pin['sha256']
    native=read(Path(protocol['native_summary']))
    assert PINS[protocol['native_summary']]==protocol['native_summary_sha256']
    assert native['paired_prefix_exact'] and native['counterfactual_valid']
    assert all(v['native_execution_passed'] for v in native['arms'].values())
    old=read(REVIEW/'rm47_service66_response/assessment.json')
    assert old['release_minus_hold']['native']['omega']==native['delta_TTT_veh_h']
    summary=read(OUTPUT/'summary.json')
    assert summary['duration_sec']==450 and not summary['future_observation_inputs']
    assert summary['optimizer_iterations']==0 and not summary['native_started']
    points=summary['results'];assert set(points)=={'held_actual','release_actual'}
    cached=read(I/'closedloop_recorded2700_select_check_trace10681_rm223_candidate/held_actual.json')
    for key in ('commands','cost_by_stock','ramps','ttt_omega_veh_h'):
        assert points['held_actual'][key]==cached[key],key
    for j,(a,b) in enumerate(zip(points['held_actual']['commands'],points['release_actual']['commands'])):
        for field in ('vsl','green_times','offsets'):assert a[field]==b[field]
        assert all(value==110 for value in a['vsl'].values())
        changed={r for r in a['meters'] if a['meters'][r]!=b['meters'][r]}
        assert changed=={'RM_C10484'}
        assert a['meters']['RM_C10484']==2 and b['meters']['RM_C10484']==4+2*j
    assert points['held_actual']['physical_cell_states'][0]==points['release_actual']['physical_cell_states'][0]
    cases={};initial=None;balance=resource=route_residual=0.
    for name,label in (('held_actual','hold'),('release_actual','release')):
        point=points[name];assert point['validation']['all_actuator_and_step_constraints_checked']
        assert point['executed_control_blocks']==[0,1,2]
        for interval in point['executed_intervals']:
            assert not interval['future_observation_inputs']
            for ramp,row in interval['ramps'].items():
                error=abs(row['initial_stock']+row['arrival']-row['merge']-row['final_stock'])
                balance=max(balance,error)
            for row in interval['offramps'].values():
                balance=max(balance,abs(row['initial_stock']+row['arrival']-row['drain']-row['final_stock']))
        route_residual=max(route_residual,max(r['max_cell_residual'] for r in point['offramp_route_inventory_checks']))
        trace=read(OUTPUT/(name+'_RM_C10484_trace.json.gz'))
        if initial is None:initial=trace['initial_stock']
        else:assert initial==trace['initial_stock']
        rec=[x['receipt'] for x in trace['lane_interval_receipts']]
        assert len(rec)==450
        balance=max(balance,max(abs(x['conservation_residual_veh']) for x in rec))
        resource=max(resource,max(x['exceedance_veh'] for x in trace['resources']))
        assert abs(math.fsum(x['accepted_merge_veh'] for x in rec)-point['ramps']['RM_C10484']['merge'])<1e-7
        windows=[]
        for j,interval in enumerate(point['executed_intervals']):
            rr=[x for x in rec if interval['start_sec']<=x['start_sec']<interval['end_sec']]
            assert len(rr)==150
            r=interval['ramps']['RM_C10484']
            for key,field in (('head','head_service_veh'),('merge','accepted_merge_veh')):
                assert abs(r[key]-math.fsum(x[field] for x in rr))<1e-7
            windows.append(dict(start_sec=interval['start_sec'],green=point['commands'][j]['meters']['RM_C10484'],
                **r,head_limit=math.fsum(x['head_service_limit_veh'] for x in rr),
                receiving_budget=math.fsum(x['receiving_budget_veh'] for x in rr)))
        cases[label]=dict(costs=costs(point),ramp10484=point['ramps']['RM_C10484'],windows=windows,
            wall_sec=point['wall_sec'],initial=initial)
    assert max(balance,resource,route_residual)<1e-7
    delta={k:cases['release']['costs'][k]-cases['hold']['costs'][k] for k in cases['hold']['costs']}
    actual=old['release_minus_hold']['native']
    report=dict(status='COMPLETE_RM_ONLY_RESPONSE_NOT_FULL_GAIN_QUALIFICATION',seed=47,start_sec=2700,horizon_sec=450,
        forecasts=2,prediction_wall_sec=sum(x['wall_sec'] for x in cases.values()),fit=0,optimizer=0,new_native=0,FZP=0,
        cases=cases,release_minus_hold=dict(current=delta,previous=old['release_minus_hold']['current'],native=actual),
        direction_matches={k:(delta[k]>0)==(actual[k]>0) for k in ('omega','east','ramps','merge','off','terminal')},
        held_matches_review223_exact=True,commands_only10484_differ=True,
        max_ramp_offramp_balance_residual=balance,max_target_ramp_resource_exceedance=resource,max_offramp_route_residual=route_residual,
        input_sha256=PINS,limitations=['Existing seed47 regression; independent of new route initialization fit but not an untouched overall-model holdout.',
            'Only10484 release2to4/6/8 tested; no assertion of all-RM/VSL gain accuracy or SDMPC global optimality.',
            'Native5s residence and last4.9s held tail; original removal/unresolved event limitations retained.',
            'Model tracked outside and native outside/uninserted cover different scopes. No full external-cost equality claimed.'])
    (HERE/'assessment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('status','prediction_wall_sec','release_minus_hold','direction_matches','max_ramp_offramp_balance_residual')}))


if __name__=='__main__':main()
