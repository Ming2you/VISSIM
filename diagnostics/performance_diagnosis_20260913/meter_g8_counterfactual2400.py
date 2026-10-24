"""Nine canonical endpoints: actual hold and one g8 change for each physical ramp."""
from pathlib import Path
import copy
import hashlib
import json
import os
import pickle
import subprocess
import sys
import time
import traceback

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).with_name('lever_counterfactual2400')/'meter_g8_attempt01'
RUN=ROOT/'evaluation/runs/codex_fid_cl9000_s13_v3/decisions_codex_fid_cl9000_s13_v3'
CONFIG=ROOT/'diagnostics/selected_control_demand/codex_fid_cl9000_s13_v3/config.json'
FIELDS=('N_P_star','N_UF_star','ramp_metering','vsl','green_times','offsets','inflow_outflow_allocation')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
psha=lambda v:hashlib.sha256(pickle.dumps(v,protocol=5)).hexdigest()


def worker():
    started=time.perf_counter();os.chdir(ROOT)
    os.environ['RW_OFFSET_WRITER']='experiment'
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    paths=[Path(__file__),CONFIG,RUN/'state_002400.json',RUN/'action_002250.json',RUN/'action_002250.csv',RUN/'action_002400.joint.json']
    paths+=list((ROOT/'evaluation/controllers').glob('*.py'))
    pins={str(p.relative_to(ROOT)):sha(p) for p in paths}
    report={'schema':'physical-meter-g8-single-change2400/v1','completed':False,'native_runs':0,'solver_runs':0,'price_fits':0,
        'endpoint_limit':9,'source_sha256':pins,'rows':[],
        'scope':'Same recorded2400 input,450s held response,original NP2400 and actual-hold NUF +/-40. Exactly8 pure meter g8 endpoints and1hold; not63-candidate evaluation or53-decision generalization.'}
    try:
        from diagnostics.probe_model_area_integration import build_projected
        from evaluation.controllers import vissim_stackelberg_adapter as a,area_follower_objective as area,joint_owner_game as game
        from evaluation.controllers.area_leader_objective import install_joint_price_field,fixed_joint_price_terms,shared_quantity_constraints
        from src.models.state import ControlAction,segment_vsl
        from src.models.demand import DemandStep
        joint=json.loads((RUN/'action_002400.joint.json').read_text())
        cfg,state,det,tuning,raw,mapping,metadata=build_projected(CONFIG,RUN/'state_002400.json',RUN/'action_002250.json',fixture_inputs=False)
        cal=a.deep_update(dict(a.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))),tuning.get('calibration_override',{}))
        forecast=a.demand_from_state(raw,cfg,DemandStep,3,cal,det)
        follower=a.build_priced_wu_link_controller(cfg,tuning).nash_solver
        historical=a.control_from_json(RUN/'action_002250.json',cfg,ControlAction)
        historical,_=area.expand_shared_vsl_action(historical,cfg,segment_vsl_func=segment_vsl)
        hold=historical.copy();hold.N_P_star=2400.0;hold.N_UF_star=2996.9313872526645
        assert cfg.mpc.horizon_steps==3 and cfg.simulation.T_c_sec==150
        field=copy.deepcopy(joint['selected_price_field'])
        assert field['context']['beta_seconds']==0.0
        assert all(getattr(hold,k)==v for k,v in field['reference_levers'].items())
        nodes={s:n for s,n in cfg.network.signal_actuation_contract['nodes'].items() if n.get('native_clock_basis') is not None}
        assert json.dumps(field['context']['native_clock_nodes'],sort_keys=True)==json.dumps(nodes,sort_keys=True)
        field['context']['native_clock_nodes']=copy.deepcopy(nodes)
        report['native_nodes_json_values_exact_before_tuple_rehydration']=True
        report['price_installation']=install_joint_price_field(follower,hold,field,
            expected_owners=tuple(cfg.network.signals)+tuple(cfg.network.freeway_links),expected_context=field['context'],nuf_mode='equality')
        callbacks,context,fingerprint=area._joint_runtime_callbacks(follower,state,forecast,historical,hold,mapping,pins,
            reference=hold,total_budget=None,directional={},tolerance=40.)
        controls={'hold':hold};indices={}
        for owner in ('FW_W','FW_E'):
            domain=callbacks['neighbors'](owner,hold,context)
            assert len(domain.candidates)==63
            for index,candidate in enumerate(domain.candidates):
                changed=game.assert_owner_transition(callbacks['ownership'],owner,hold,candidate)
                if len(changed)!=1 or changed[0][0]!='ramp_metering':continue
                mid=changed[0][1]
                if candidate.diagnostics['rw_meter_green_'+mid]!=8.:continue
                assert mid not in controls
                controls[mid]=candidate;indices[mid]={'owner':owner,'candidate_index':index,'generated_domain_count':63}
        assert len(controls)==9 and set(controls)-{'hold'}==set(cfg.network.ramps)
        report['canonical_candidate_indices']=indices
        spec=cfg.network.physical_ramp_branches
        report['ramp_context']={mid:{'definition':spec['ramps'][mid],
            'initial_connector_queue_veh':state.ramp_queue[mid],
            'upstream_movement_queue_veh':{m:state.urban_movement_queue.get(m,0.) for m in cfg.network.on_ramp_to_movement[mid]},
            'external_ramp_forecast_veh_h':[d.ramp_arrival.get(mid,0.) for d in forecast],
            'service_hold_veh_h':hold.ramp_metering[mid],
            'service_g8_veh_h':controls[mid].ramp_metering[mid],
            'queue_scope':'Connector inventory and separately owned upstream movement queues are distinct stocks. Direct forecast excludes model corridor-generated arrivals; aggregate throughput is not desired demand.'} for mid in cfg.network.ramps}
        def find_regions(value):
            if isinstance(value,dict):
                if 'physical_ramp_observed_regions' in value:return value['physical_ramp_observed_regions']
                for sub in value.values():
                    found=find_regions(sub)
                    if found is not None:return found
            return None
        report['existing_projected_observation_regions']=find_regions(metadata)
        report['model_shared_approach_state']=getattr(state,'shared_approach_state',None)
        report['model_sc2001_corridor_state']=getattr(state,'sc2001_corridor_state',None)
        policy={'leader_present':True,'np_mode':'cap','nuf_mode':'equality',
            'inactive_price_addresses':dict.fromkeys(('phase','offset','vsl','meter'),())}
        fixed=pickle.dumps((follower,state,historical,hold,forecast,policy),protocol=5)
        report['frozen_model_inputs_sha256']=hashlib.sha256(fixed).hexdigest()
        report['state_sha256']=psha(state);report['forecast_sha256']=psha(forecast)
        commands={}
        for name,control in controls.items():
            callbacks['move_box'].validate(control)
            rows=callbacks['command_evidence'](control)['ordered_rows'];assert len(rows)==213
            commands[name]=rows
            if name!='hold':
                changed=[(x,y) for x,y in zip(commands['hold'],rows) if {k:v for k,v in x.items() if k!='metadata'}!={k:v for k,v in y.items() if k!='metadata'}]
                assert len(changed)==1 and changed[0][1]['kind']=='ramp_meter' and changed[0][1]['id']==name and changed[0][1]['green_sec']==8.
        report['setup_sec']=time.perf_counter()-started
        print(json.dumps({'stage':'setup_complete','seconds':report['setup_sec'],'endpoint_limit':9}),flush=True)
        batch=area.evaluate_shared_owner_batch(follower,state,hold,forecast,tuple(controls.values()),horizon_steps=3)
        report['endpoint_calls']=batch['endpoint_calls'];assert batch['endpoint_calls']==9
        for (name,control),item in zip(controls.items(),batch['results']):
            assert item['action_token']==psha(control)
            price=fixed_joint_price_terms(follower,control,item['quantities'],lambda_p=follower._lambda_P,lambda_uf=follower._lambda_UF,
                target_np_veh=2400.,target_nuf_veh_h=hold.N_UF_star,price_context=policy)
            costs={o:item['local_base_costs'][o]+price['owners'][o]['total'] for o in item['local_base_costs']}
            q=shared_quantity_constraints(follower,control,item['quantities'],start_sec=state.time_sec,horizon_steps=3,
                np_mode='cap',target_np_veh=2400.,np_tolerance_veh=1e-7,nuf_mode='equality',target_nuf_veh_h=hold.N_UF_star,nuf_tolerance_veh_h=40.)
            feasible=item['conditional_model_feasibility_witness'] and item['model_constraint_coverage']['complete'] and item['resource_summary']['max_exceedance_veh']<=1e-7 and q['feasible']
            report['rows'].append({'name':name,'TTT_veh_h':item['objective_veh_h'],'control_area':item['control_area'],
                'quantity_constraints':q,'feasible':feasible,'owner_costs':costs,'local_base_costs':item['local_base_costs'],'price_terms':price,
                'fields':{k:getattr(control,k) for k in FIELDS},'physical_meter_rows':[r for r in commands[name] if r['kind']=='ramp_meter'],
                'action_token':item['action_token'],'response_token':item['response_token'],'model_inputs_token':item['frozen_context_token'],
                'model_constraint_coverage':item['model_constraint_coverage'],'resource_summary':item['resource_summary']})
        base=report['rows'][0]
        checks={'hold_TTT_matches_prior_replay':abs(base['TTT_veh_h']-326.0873745673935)<=1e-7,
            'hold_NP_matches_native_decision':abs(base['quantity_constraints']['np']['actual']-316.1265184070456)<=1e-7,
            'hold_NUF_matches_native_decision':abs(base['quantity_constraints']['nuf']['actual']-2996.9313872526645)<=1e-7,
            'hold_FW_E_cost_matches_native_decision':abs(base['owner_costs']['FW_E']-120.83859787978206)<=1e-7,
            'hold_FW_W_cost_matches_native_decision':abs(base['owner_costs']['FW_W']-124.8934140223018)<=1e-7,
            'same_model_input_token':len({r['model_inputs_token'] for r in report['rows']})==1,
            'source_model_operands_preserved':pickle.dumps((follower,state,historical,hold,forecast,policy),protocol=5)==fixed}
        report['replay_checks']=checks
        for row in report['rows']:
            row['delta_TTT_veh_h']=row['TTT_veh_h']-base['TTT_veh_h']
            row['delta_TD_veh']=row['control_area']['ttd_veh']-base['control_area']['ttd_veh']
            row['delta_NUF_veh_h']=row['quantity_constraints']['nuf']['actual']-base['quantity_constraints']['nuf']['actual']
            row['all_aggregate_control_area_equal_hold']=row['control_area']==base['control_area']
            row['delta_owner_cost']={o:v-base['owner_costs'][o] for o,v in row['owner_costs'].items()}
            print(json.dumps({'name':row['name'],'dTTT':row['delta_TTT_veh_h'],'dNUF':row['delta_NUF_veh_h'],'feasible':row['feasible']}),flush=True)
        report['completed']=all(checks.values())
    except Exception:
        report['error']=traceback.format_exc();print(report['error'],flush=True)
    finally:
        report['source_changes']=[p for p,h in pins.items() if sha(ROOT/p)!=h]
        report['completed']=report['completed'] and not report['source_changes']
        report['wall_sec']=time.perf_counter()-started
        (OUT/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    return 0 if report['completed'] else 1


def main():
    if sys.argv[1:]==['--worker']:return worker()
    if sys.argv[1:]:raise ValueError('No user options')
    OUT.mkdir(exist_ok=False);started=time.perf_counter()
    receipt={'completed':False,'timeout_sec':300,'native_run':False,'owned_child_only':True}
    try:
        with (OUT/'stdout.txt').open('xb') as out,(OUT/'stderr.txt').open('xb') as err:
            result=subprocess.run([sys.executable,'-B','-X','utf8',str(Path(__file__).resolve()),'--worker'],cwd=ROOT,stdout=out,stderr=err,timeout=300)
        receipt.update(exit_code=result.returncode,completed=result.returncode==0)
    except subprocess.TimeoutExpired:receipt['failure']='Owned offline child exceeded300s and was terminated.'
    finally:
        receipt['wall_sec']=time.perf_counter()-started
        (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(receipt),flush=True)
    return 0 if receipt['completed'] else 1


if __name__=='__main__':sys.exit(main())
