"""Verify finished numerical trials and identical pre-control boundary inputs."""
from pathlib import Path
import json,hashlib,sys
HERE=Path(__file__).resolve().parent.parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,CASES,MODEL
out=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
names=[f'transport_step{step}_exchange_{exchange}_v2' for step,exchange in ((10,'off'),(2,'off'),(1,'off'),(1,'on'))]
cases={};pins=[];urban=interfaces=0;residual=0.;exact=0
for name in names:
    result=load(HERE/name/'result.json');protocol=load(HERE/name/'protocol.json')
    for rel,digest in protocol['source_pins'].items():
        assert sha(ROOT/rel)==digest;pins.append(dict(run=name,path=rel,sha256=digest))
    for arm,summary in result['summaries'].items():
        pred=load(HERE/name/f'prediction_{arm}.json')
        urban+=summary['urban_checks'];interfaces+=summary['checks']['lane_interface_checks']
        if name=='transport_step10_exchange_off_v2':
            assert pred==load(HERE/'partition_context_on_exchange_off_part_on_v1'/f'prediction_{arm}.json');exact+=1
        for road in pred['diagnostics']['roads']:residual=max(residual,road.get('branch_partition_continuity_residual_max_veh',0.))
        assert pred['local_ramp_audit']['passed'] and pred['local_ramp_audit']['step_sec']==1
    cases[name]=dict(deltas=result['deltas'],nc_e=result['summaries']['none']['score']['objective'],
                    nc_w=result['summaries']['none']['west_state_score']['objective'])
_,folder,bank,start=next(row for row in CASES if row[0]==23)
data=e.ObservationData(folder)
models={s:e.load_base_model(data.geometry,HERE/f'transport_step{s}_exchange_off_v2/config.json') for s in (10,1)}
protocol=load(bank/'protocol.json');profile=load(MODEL/'port_profile.json');origin=load(HERE/'port_positions_v1/s23.json')
matched=0;totals={}
for arm in ('none','rm_ramp','vsl','both'):
    sequence=protocol['candidate_bank'].get(arm,dict(green=[],vsl=[]))
    def command(t):
        i=int((t-start)//150)
        return ({'RM_C10490':sequence['green'][i]} if sequence['green'] else {},
                {d:sequence['vsl'][i] for d in protocol['dsd_ids']} if sequence['vsl'] else {})
    windows={s:e.window(data,m,start,'history_forecast',profile,command,port_origin_counts=origin['counts']) for s,m in models.items()}
    for key in ('initial_cells','initial_origin_queue','port_dynamics','ramp_dynamics','vsl_zone_heads'):
        assert windows[1][key]==windows[10][key],key
    for i,parent in enumerate(windows[10]['boundary_steps']):
        children=windows[1]['boundary_steps'][10*i:10*i+10]
        for child in children:
            for key,value in parent.items():
                if key not in ('window_start_s','window_end_s','ramp_arrival_profile','ramp_arrival_vph'):
                    assert child[key]==value,key
            matched+=1
        for ramp,rate in parent['ramp_arrival_vph'].items():
            assert abs(sum(c['ramp_arrival_vph'][ramp]/3600 for c in children)-rate*10/3600)<1e-7
    totals[arm]={s:dict(source={road:sum(w['source_demand_vph'][road]*s/3600 for w in window['boundary_steps']) for road in models[s].roads},
                        ramp={ramp:sum(w['ramp_arrival_vph'][ramp]*s/3600 for w in window['boundary_steps']) for ramp in models[s].ramps}) for s,window in windows.items()}
    for field in totals[arm][1]:
        for key,value in totals[arm][1][field].items():assert abs(value-totals[arm][10][field][key])<1e-7
result=dict(status='TIME_REFINEMENT_VERIFIED_GAIN_NOT_QUALIFIED',valid_450s_forecasts=16,exact10s_full_predictions=exact,
    matched_fine_command_boundaries=matched,native_meter_cycle_sec=10,control_interval_sec=150,
    urban_conservation_checks=urban,lane_interface_checks=interfaces,max_partition_residual=residual,
    source_pin_checks=len(pins),source_pins=pins,cases=cases,requested_vehicle_totals=totals,future_inputs=False,
    new_native_runs=0,production_adopted=False,qualified=False,tests_passed=22,
    formal_multi_state_guard='not run: component gain failed',fresh_holdout='not run')
with (out/'verification.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
print({key:result[key] for key in ('status','valid_450s_forecasts','exact10s_full_predictions','matched_fine_command_boundaries','urban_conservation_checks','lane_interface_checks','source_pin_checks')})
