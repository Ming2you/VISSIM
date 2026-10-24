"""Compare saved forecasts and closed native evidence; no simulation or fitting."""
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'

def read(path):
    if str(path).endswith('.gz'):
        with gzip.open(path,'rt',encoding='utf-8') as f:return json.load(f)
    return json.loads(path.read_bytes())

def main():
    target=HERE/'assessment.json'
    if target.exists():raise FileExistsError(target)
    case=I/'closedloop_recorded2700_lever450_sc1001_pair3'
    new=read(case/'summary.json')['results']
    prior=I/'closedloop_recorded2700_lever450_trace10484_residualclass_ind47'
    old={name:read(prior/(name+'.json')) for name in new}
    parity=read(I/'closedloop_recorded2700_lever450_sc1001_pair1/summary.json')['results']
    for name,row in new.items():
        for key in ('ttt_omega_veh_h','tracked_outside_residence_veh_h','ramps','commands','physical_cell_states'):
            assert row[key]==parity[name][key],(name,key)
        assert row['commands']==old[name]['commands']
        assert row['physical_cell_states'][0]==old[name]['physical_cell_states'][0]
    native=read(I/'expanded036_9000_20260930/loss_onset2250/source_sc101/residual_timing/independent47.json')
    native_ports={'10491':dict(initial=3,arrival=127,drain=128,final=2),
                  '10481':dict(initial=1,arrival=36,drain=37,final=0)}
    responses=[read(HERE/f'sc1001_pair3_response_{i}.json.gz') for i in (0,1)]
    ports={};hold=responses[0]
    for off,road,group in (('10491','FW_W','OR_D_W'),('10481','FW_E','OR_D_E')):
        stock='storage:'+group+'_storage'
        take=lambda rows:dict(initial=hold['states'][0]['ports'][off],
            arrival=sum(r['vehicles'] for r in rows if r['target']==stock and r['source']=='freeway:'+road),
            drain=sum(r['vehicles'] for r in rows if r['source']==stock),
            final=hold['states'][-1]['ports'][off])
        revised=take(hold['transfers'])
        assert abs(revised['initial']+revised['arrival']-revised['drain']-revised['final'])<1e-7
        flow=old['held_actual']['control_area']['flow_counts']
        initial=revised['initial'];arrival=flow['freeway:'+road+'->'+stock]
        drain=sum(v for k,v in flow.items() if k.startswith('movement:SC1001_off'+('W' if off=='10491' else 'E')+'_to_'))
        ports[off]=dict(actual=native_ports[off],before=dict(initial=initial,arrival=arrival,drain=drain,
            final=initial+arrival-drain),after=revised)
    for arm,response in zip(new,responses):
        q=response['quantities']['served_by_movement_veh']
        for side,off in (('W','10491'),('E','10481')):
            key='storage:OR_D_'+side+'_storage'
            drain=sum(r['vehicles'] for r in response['transfers'] if r['source']==key)
            assert abs(sum(v for m,v in q.items() if m.startswith('SC1001_off'+side+'_to_'))-drain)<1e-7
        assert all(abs(r['residual'])<1e-7 for r in new[arm]['ramps'].values())
    events=read(HERE.parent/'stopline/s47_rm_hold_visits.json.gz')['events']
    guaranteed=sum(e['lower']>=2700 and e['upper']<=3140 for e in events)
    possible=sum(e['upper']>2700 and e['lower']<3140 for e in events)
    head=sum(r['vehicles'] for r in hold['transfers'] if r['source']=='storage:lane_shared_SC1001'
             and r['start_sec']>=2700 and r['end_sec']<=3140)
    native_frame=Path('D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47/lane_observations/frame_003150.json')
    frame=read(native_frame)
    assert frame['time_s']==3150
    def delta(rows,key):return rows['release_actual'][key]-rows['held_actual'][key]
    cost_delta=lambda rows,prefix:sum(v for k,v in rows['release_actual']['cost_by_stock'].items() if k.startswith(prefix))-sum(v for k,v in rows['held_actual']['cost_by_stock'].items() if k.startswith(prefix))
    result=dict(status='BOUNDARY_IMPROVED_NOT_GAIN_QUALIFIED',ports=ports,
        common_commands_and_initial_freeway_ramps=True,quantity_only_fix_traffic_exact=True,
        rm_delta_veh_h=dict(actual_Omega=native['native_delta_omega'],before_Omega=delta(old,'ttt_omega_veh_h'),
            after_Omega=delta(new,'ttt_omega_veh_h'),actual_FW_E=native['native_delta_by_group']['FW_E'],
            after_FW_E=cost_delta(new,'freeway:FW_E'),actual_ramps=native['native_delta_by_group']['ramps'],
            after_ramps=cost_delta(new,'ramp:'),after_outside=delta(new,'tracked_outside_residence_veh_h')),
        shared_head=dict(window_sec=[2700,3140],native_count_bracket=[guaranteed,possible],model_departures=head,
            initial_veh=69,final_model_veh=hold['states'][-1]['shared'],
            final_native127_10777_veh=sum(r[1] in (127,10777) for r in frame['vehicles']),
            final_native_frame_sha256=hashlib.sha256(native_frame.read_bytes()).hexdigest(),
            caveat='5s crossing bracket, not exact lane/time census. Similar final stock does not prove correct arrival/discharge.'),
        quantity=dict(real_17_owner_catalog_checked=True,port_service_once_checked=True,
            initial_unknown_source_veh=58,unknown_source_rule='Legacy city-inflow upper interpretation; not qualified for selection',
            totals=[sum(o['net_inflow_veh'] for o in d['quantities']['owners'].values()) for d in responses]),
        physical_resource_max_exceedance=max(d['resource_max_exceedance'] for d in responses),
        new_native_runs=0,fit=0,new_fzp_scans=0,sdmpc_selections=0,
        forecasts_completed=5,forecast_attempts_note='pair1 two; pair2 first completed before diagnostic missing-follower error; pair3 two, same traffic as pair1',
        source_pins={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            [case/'summary.json',prior/'held_actual.json',prior/'release_actual.json',HERE/'candidate_config.json',
             HERE/'sc1001_pair3_response_0.json.gz',HERE/'sc1001_pair3_response_1.json.gz']})
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
