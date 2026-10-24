"""Numerical queue-load sensitivity using the unchanged canonical plant.

Extra initial queue is explicitly hypothetical and inside the evaluation area.
Existing transit stocks retain its overflow and count its waiting time. This is
not a VISSIM run or a native urban OD multiplier experiment.
"""
from collections import defaultdict
import copy
import csv
import hashlib
import json
import math
from pathlib import Path
import pickle
import sys
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from diagnostics.probe_model_area_integration import build_projected, replay_provenance
from diagnostics.rule_baseline_20260914.compare import scheduled_endpoint
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers import control_area_objective as area, physical_ramp_branches as physical
from evaluation.controllers.shared_approach import demand_amount
from src.models.demand import DemandStep
from src.models.state import ControlAction
from src.simulation import coupling


def write(path,value):
    with path.open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False)


def table(path,rows):
    with path.open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def shift_schedule(rows,start,factor):
    result=copy.deepcopy(rows)
    if not any(r['start_sec']==start for r in result):
        row=copy.deepcopy(max((r for r in rows if r['start_sec']<start),key=lambda r:r['start_sec']))
        row['start_sec']=start;result.append(row);result.sort(key=lambda r:r['start_sec'])
    for row in result:
        if row['start_sec']>=start:row['rate_veh_h']*=factor
    return result


def main():
    start=1650; duration=int(sys.argv[2]) if len(sys.argv)>2 else 900
    queue_levels=tuple(map(int,sys.argv[3].split(','))) if len(sys.argv)>3 else (0,10,30,60,120)
    policies=tuple(sys.argv[4].split(',')) if len(sys.argv)>4 else ('open','hold_g8','progressive')
    assert queue_levels and all(q>=0 for q in queue_levels)
    assert 'open' in policies and set(policies)<= {'open','hold_g8','progressive'}
    out=ROOT/sys.argv[1]
    assert not out.exists();out.mkdir(parents=True)
    assert duration in (450,900)
    name='rule100_none3000_s13_v1';dec=ROOT/'evaluation/runs'/name/('decisions_'+name)
    config=ROOT/f'diagnostics/selected_control_demand/{name}/config.json'
    state_path=dec/f'state_{start:06d}.json';prev_path=dec/'action_001500.json'
    cfg,initial,det,tuning,raw,mapping,meta=build_projected(config,state_path,prev_path,fixture_inputs=False)
    cal=adapter.deep_update(adapter.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json')),tuning.get('calibration_override',{}))
    steps=duration//150
    baseline_forecast=adapter.demand_from_state(raw,cfg,DemandStep,steps,cal,det)
    reference=adapter.control_from_json(prev_path,cfg,ControlAction)
    reference=physical.prepare_control(reference,cfg)
    targets=tuple(r for r in cfg.network.ramps if cfg.network.ramp_to_freeway[r]=='FW_E')
    assert set(targets)=={'RM_C10639','RM_C10681','RM_C10490','RM_C10484'}
    assert all(reference.diagnostics['rw_meter_green_'+r]==10 for r in cfg.network.ramps)
    schedules={'open':[10]*steps,'hold_g8':[8]*steps,'progressive':[max(2,8-2*i) for i in range(steps)]}
    schedules={k:v for k,v in schedules.items() if k in policies}
    controls={};writer={}
    for policy,greens in schedules.items():
        actions=[];previous=reference
        for g in greens:
            desired={r:(g if r in targets else 10) for r in cfg.network.ramps}
            candidate=physical.candidate_from_greens(previous,previous,cfg,desired)
            rows=physical.physical_commands(candidate,cfg)
            assert all(rows[r]['green_sec']==desired[r] for r in desired)
            assert all(abs(desired[r]-previous.diagnostics['rw_meter_green_'+r])<=2 for r in desired)
            actions.append(candidate);previous=candidate
        controls[policy]=actions;writer[policy]=[physical.physical_commands(a,cfg) for a in actions]
    initial_hash=hashlib.sha256(pickle.dumps(initial,protocol=5)).hexdigest()
    source_pins=replay_provenance(tuning,config,state_path,prev_path,Path(__file__))
    original_schedules={fw:copy.deepcopy(cfg.network.native_input_schedule['inputs'][row['input']]['schedule'])
        for fw,row in cfg.network.offramp_route_inventory['inputs'].items()}
    write(out/'setup.json',{'kind':'hypothetical_initial_queue_sensitivity','native_run':False,'solver_calls':0,
        'start_sec':start,'duration_sec':duration,'targets':targets,'extra_initial_queue_per_ramp':queue_levels,
        'mainline_future_factors':[1.,.75],'meter_greens':schedules,'writer_commands':writer,
        'physical_ramps':cfg.network.physical_ramp_branches['ramps'],'source_sha256':source_pins,
        'limitations':['This is initial queued demand, not sustained native urban input or static-route scaling.',
            'Extra queue is represented in existing inside-area transit storage with one-for-one waiting cost.',
            'Overflow remains queued, but its physical urban road length/lane blocking is not reconstructed.',
            'Extra queue enters available connector space before ordinary urban allocation each substep; same order for all policies.',
            'No solver or N_UF equality filters are used for the physical cost comparison.',
            '450s held g8 is a one-decision candidate; progressive plans require repeated150s decisions.']})
    results=[];details=[];started=time.perf_counter()
    for fw_factor in (1.,.75):
        for fw,row in cfg.network.offramp_route_inventory['inputs'].items():
            cfg.network.native_input_schedule['inputs'][row['input']]['schedule']=shift_schedule(original_schedules[fw],start,fw_factor)
        forecast=copy.deepcopy(baseline_forecast)
        for i,d in enumerate(forecast):
            for fw,row in cfg.network.offramp_route_inventory['inputs'].items():
                timetable=cfg.network.native_input_schedule['inputs'][row['input']]['schedule']
                d.freeway_mainline[fw]=demand_amount(timetable,start+i*150,start+(i+1)*150)*24
        for amount in queue_levels:
            state=initial.copy()
            for ramp in targets:
                if not amount:continue
                key='diagnostic_extra_ramp:'+ramp
                assert key not in state.urban_inflow_transit_buffer
                state.urban_inflow_transit_buffer[key]={0:float(amount)}
                area.emit_transfer(state,cfg,None,'transit:'+key,amount,source_inside=True,target_inside=True,route_key='diagnostic_initial_queue:'+ramp)
            initial_total=math.fsum(v['inside'] for v in state._control_area_ledger.stocks.values())
            for policy,actions in controls.items():
                original= coupling.urban_substep
                admission=defaultdict(float);max_buffer={r:0. for r in targets};hook_calls=0
                def substep(current,control,demand,config,*args,**kwargs):
                    nonlocal hook_calls
                    hook_calls+=1
                    for ramp in targets:
                        key='diagnostic_extra_ramp:'+ramp
                        buffer=current.urban_inflow_transit_buffer.get(key)
                        if not buffer:continue
                        waiting=math.fsum(buffer.values());max_buffer[ramp]=max(max_buffer[ramp],waiting)
                        accepted=min(waiting,max(0.,config.network.ramp_queue_cap(ramp)-current.ramp_queue[ramp]))
                        if accepted:
                            buffer[0]=waiting-accepted
                            current.ramp_queue[ramp]+=accepted
                            area.emit_transfer(current,config,'transit:'+key,'ramp:'+ramp,accepted,preserve_area=True,route_key='diagnostic_queued_admission:'+ramp)
                            admission[ramp]+=accepted
                    return original(current,control,demand,config,*args,**kwargs)
                t=time.perf_counter()
                with patch.object(coupling,'urban_substep',substep):
                    point,cells=scheduled_endpoint(state,actions,forecast,cfg)
                assert coupling.urban_substep is original
                assert hook_calls==steps*cfg.simulation.K_cu
                response=point.control_area_response
                assert response['model_constraint_coverage']['complete']
                terminal=point.states[-1]
                cost=defaultdict(float)
                for row in response['residence']:
                    for key,n in row['inside_veh'].items():
                        group=('FW_E' if key=='freeway:FW_E' else 'FW_W' if key=='freeway:FW_W' else
                            'extra_waiting' if key.startswith('transit:diagnostic_extra_ramp:') else
                            'ramp' if key.startswith(('ramp:','merge_pending:')) else 'urban_other')
                        cost[group]+=n*row['dt_h']
                total=math.fsum(cost.values());assert math.isclose(total,point.control_area['ttt_veh_h'],abs_tol=1e-7)
                merges=defaultdict(float)
                for frame in response['freeway_frames']:
                    for ramp,rate in frame['actual_ramp_release_veh_h'].items():
                        merges[ramp]+=rate*(frame['end_sec']-frame['start_sec'])/3600
                end_total=math.fsum(v['inside'] for v in terminal._control_area_ledger.stocks.values())
                # All new generic queues use existing stock/residence assertions.
                pending={r:sum(terminal.urban_inflow_transit_buffer.get('diagnostic_extra_ramp:'+r,{}).values()) for r in targets}
                assert all(math.isclose(amount,admission[r]+pending[r],abs_tol=1e-7) for r in targets)
                record={'mainline_factor':fw_factor,'extra_queue_per_E_ramp':amount,'policy':policy,
                    'duration_sec':duration,'TTT_veh_h':total,'TTD_veh':point.control_area['ttd_veh'],
                    'initial_omega_n':initial_total,'end_omega_n':end_total,
                    'E_merge_veh':sum(merges[r] for r in targets),'all_merge_veh':sum(merges.values()),
                    'end_extra_waiting_veh':sum(pending.values()),'end_E_ramp_veh':sum(terminal.ramp_queue[r] for r in targets),
                    'FW_E_TTT':cost['FW_E'],'FW_W_TTT':cost['FW_W'],'ramp_TTT':cost['ramp'],
                    'urban_other_TTT':cost['urban_other'],'extra_waiting_TTT':cost['extra_waiting'],
                    'wall_sec':time.perf_counter()-t}
                results.append(record)
                tag=f'fw{int(fw_factor*100)}_q{amount}_{policy}'
                detail={'result':record,'merges_by_ramp':dict(merges),'extra_admitted':dict(admission),'extra_pending':pending,
                    'terminal_ramp_queues':terminal.ramp_queue,'control_area':point.control_area,
                    'coverage':response['model_constraint_coverage'],
                    'meter_bounds':[r for r in response['resource_allocations'] if r['kind'].startswith('ramp_release_query_')],
                    'terminal_freeway_density':terminal.freeway_density,'terminal_freeway_speed':terminal.freeway_speed,
                    'freeway_frames':response['freeway_frames']}
                write(out/(tag+'.json'),detail)
                print(json.dumps({k:record[k] for k in ('mainline_factor','extra_queue_per_E_ramp','policy','duration_sec','TTT_veh_h','E_merge_veh')}),flush=True)
    by={(r['mainline_factor'],r['extra_queue_per_E_ramp'],r['policy']):r for r in results}
    for row in results:
        base=by[row['mainline_factor'],row['extra_queue_per_E_ramp'],'open']
        row['delta_TTT_veh_h']=row['TTT_veh_h']-base['TTT_veh_h']
        row['improvement_percent']=100*(1-row['TTT_veh_h']/base['TTT_veh_h'])
        row['delta_E_merge_veh']=row['E_merge_veh']-base['E_merge_veh']
        row['delta_all_merge_veh']=row['all_merge_veh']-base['all_merge_veh']
        row['mean_merge_delta_within40vph_only']=abs(row['delta_all_merge_veh'])*3600/duration<=40+1e-7
    assert initial_hash==hashlib.sha256(pickle.dumps(initial,protocol=5)).hexdigest()
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in source_pins.items())
    table(out/'results.csv',results)
    write(out/'completed.json',{'completed':True,'queries':len(results),'wall_sec':time.perf_counter()-started,
        'source_files_unchanged':True,'initial_observation_unchanged':True,'native_run':False,'results':results})


if __name__=='__main__':main()
