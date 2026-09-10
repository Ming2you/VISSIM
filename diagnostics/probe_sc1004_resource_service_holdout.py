"""Bounded held-control 450s resource-rate comparison; no optimizer/VISSIM.

SC1004 is seeded so its SG2 resource matches the actual native timeline. Others retain
the recorded warmup JSON's nominal vectors. This is a resource-clock matched
model counterfactual, not a replay of the whole physical native network.
"""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import hashlib,json,os,pickle,tempfile,time
from diagnostics.probe_model_area_integration import build_projected,replay_provenance
from diagnostics.sc1004_head_service_identifiability import geometry
from evaluation.controllers import route_choice_corridor as rc,area_runtime,signal_actuation_contract as sac
ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'diagnostics/area_candidate_configs/n7_area_beta0.json'
CALIBRATED='diagnostics/route_choice_corridor_sc1004_calibrated.json'
MEMBERS=('SC1004_W_to_E_SC1005','SC1004_offE_to_E_SC1005','SC1004_offW_to_E_SC1005')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))


def clock_aligned_control(cfg,recorded,program):
    control=recorded.copy()
    values=cfg.network.signal_actuation_contract['nodes']['SC1004']['axis_green_sec']
    control.green_times.update({'SC1004_'+k:v for k,v in values.items()})
    control.offsets['SC1004']=0.
    sac.validate_control(control,cfg)
    probe=SimpleNamespace(network=cfg.network,simulation=SimpleNamespace(T_u_sec=1.))
    authority={'1':['4','8'],'2':['3','7'],'3':['2'],'4':['5']}
    mismatch=[]
    for phase,groups in authority.items():
        for second in range(450):
            model=sac.phase_fraction(control,probe,{'phase':'SC1004_p'+phase},second)
            for group in groups:
                measured=float(program.state_at(second,group,controller_offset_sec=0.)=='GREEN')
                if abs(model-measured)>1e-10:mismatch.append([phase,group,second,model,measured])
    resource_mismatch=[x for x in mismatch if x[1]=='2']
    if resource_mismatch:raise AssertionError('SC1004 SG2 resource clock differs: '+str(resource_mismatch[:4]))
    return control,{'SC1004_green_sec':values,'SC1004_offset_sec':0.,'checked_integer_seconds':450,
        'matched_resource_group':'2','resource_clock_mismatches':resource_mismatch,
        'other_native_group_mismatch_counts':{g:sum(x[1]==g for x in mismatch) for g in ('3','4','5','7','8')},
        'changed_recorded_values':{k:{'recorded':recorded.green_times[k],'matched_native':v} for k,v in control.green_times.items() if recorded.green_times.get(k)!=v},
        'other_recorded_green_offset_VSL_meter_vectors_held':True}


def evaluate(cfg,state,control,raw,detectors,calibration,*,deadline):
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,runtime_setup
    from src.models.demand import DemandStep
    runtime_setup.install_worker_runtime(adapter,cfg,raw,detectors)
    from src.controllers.rollout_endpoint import ObjectiveSpec,evaluate_price_point
    forecast=adapter.demand_from_state(raw,cfg,DemandStep,3,calibration,detectors)
    initial=pickle.dumps((state,control,forecast));events=[];real=rc.receive_accepted
    from src.simulation import coupling
    from evaluation.controllers import area_meter_finalization
    # Finalize the same observed decision context before asserting held vectors.
    physical=area_meter_finalization.finalize(control.copy(),cfg)
    vector_keys=('N_P_star','N_UF_star','green_times','offsets','vsl','ramp_metering')
    expected={k:deepcopy(getattr(physical,k)) for k in vector_keys};held=[]
    freeway_step=coupling.freeway_substep
    def freeway(s,c,d,config,**kwargs):
        actual={k:deepcopy(getattr(c,k)) for k in vector_keys}
        if actual!=expected:raise AssertionError('Physical held control changed inside rollout')
        held.append(s.time_sec)
        return freeway_step(s,c,d,config,**kwargs)
    def accepted(s,c,m,n,index):
        result=real(s,c,m,n,index)
        if m in MEMBERS and n>0:events.append({'second':index*c.simulation.T_u_sec,'member':m,'vehicles':n})
        if time.monotonic()>deadline:raise TimeoutError('Bounded SC1004 comparison exceeded90seconds')
        return result
    with patch.object(rc,'receive_accepted',accepted),patch.object(coupling,'freeway_substep',freeway):
        point=evaluate_price_point(state,control,forecast,[],ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'))
    if initial!=pickle.dumps((state,control,forecast)):raise AssertionError('Held endpoint mutated input')
    for snapshot in point.states:snapshot._control_area_ledger.assert_stocks(area_runtime.model_inventory(snapshot,cfg))
    turns=cfg.network.route_choice_corridor['turns'];receiver=cfg.network.urban_movements[MEMBERS[0]]['receiving_link']
    capacity=cfg.network.urban_link_storage_veh[receiver]
    prefix=[capacity-x.urban_link_storage[receiver] for x in [state]+point.states]
    result={'resource_rate_veh_h':turns[MEMBERS[0]]['service_veh_h'],
            'accepted_by_member_veh':{m:sum(e['vehicles'] for e in events if e['member']==m) for m in MEMBERS},
            'accepted_total_veh':sum(e['vehicles'] for e in events),
            'accepted_by_150sec_veh':[sum(e['vehicles'] for e in events if state.time_sec+i*150<=e['second']<state.time_sec+(i+1)*150) for i in range(3)],
            'resource_receiving_prefix_stock_veh':prefix,
            'same_initial_state_control_forecast_immutable':True,'closing_inventory_verified_each150sec':True,
            'held_physical_vector_checks':len(held),'physical_meter_vph':dict(physical.ramp_metering),
            'area':{k:v for k,v in point.control_area.items() if k!='flow_counts'},
            'event_count':len(events),'resource_accepted_events':events,
            'final_ramp_queue_veh':dict(point.states[-1].ramp_queue),
            'final_route_information':rc.diagnostics(point.states[-1],cfg)}
    # Every source event consumes the same physical budget exactly once.
    used={}
    for e in events:used[e['second']]=used.get(e['second'],0.)+e['vehicles']
    for second,amount in used.items():
        fraction=sac.phase_fraction(control,cfg,cfg.network.urban_movements[MEMBERS[0]],round(second/cfg.simulation.T_u_sec))
        if amount>result['resource_rate_veh_h']*cfg.simulation.T_u_h*fraction+1e-8:
            raise AssertionError('Three members exceeded the one physical GREEN resource budget')
    if len(held)!=45:raise AssertionError('Expected45 held freeway steps')
    result['single_resource_budget_every5sec']=True
    return result


def main():
    os.environ['RW_MAINLINE_SG_ONLY']='1';os.environ['RW_OFFSET_WRITER']='experiment'
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from src.models.state import ControlAction
    program=geometry()[2];started=time.monotonic();rows=[]
    run=ROOT/'evaluation/runs/codex_area_observed_nc_s13_20260910/decisions_codex_area_observed_nc_s13_20260910'
    paths=[Path(__file__),CONFIG,ROOT/CALIBRATED,ROOT/'diagnostics/sc1004_resource_service_calibration.json',
           ROOT/'evaluation/controllers/route_choice_corridor.py',run/'action_000001.json',run/'state_000900.json',run/'anchor_002700.json']
    tuning=load(CONFIG)
    calibration_path=ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'
    calibration=adapter.deep_update(dict(load(calibration_path)),tuning.get('calibration_override',{}))
    sources=replay_provenance({'active':tuning,'proposed_evidence':load(ROOT/CALIBRATED)},*paths,calibration_path)
    sources.update({str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'evaluation/controllers').glob('*.py')})
    for second in (900,2700):
        arms={};fingerprints=[]
        for label,calibrated in [('inherited',False),('train_lower_bound',True)]:
            private=deepcopy(tuning)
            private['urban']['shared_local_service_pool']=True
            if calibrated:
                key=private['urban']['route_choice_corridor']['evidence_paths']
                key[key.index('diagnostics/route_choice_corridor_ver2.json')]=CALIBRATED
            with tempfile.TemporaryDirectory(dir=ROOT/'diagnostics') as directory:
                config=Path(directory)/'config.json';config.write_text(json.dumps(private),encoding='utf-8')
                cfg,state,detectors,_,raw,_,metadata=build_projected(config,run/('state_000900.json' if second==900 else 'anchor_002700.json'),run/'action_000001.json',fixture_inputs=False)
            control,clock=clock_aligned_control(cfg,adapter.control_from_json(run/'action_000001.json',cfg,ControlAction),program)
            forecast=adapter.demand_from_state(raw,cfg,__import__('src.models.demand',fromlist=['DemandStep']).DemandStep,3,calibration,detectors)
            fingerprints.append(hashlib.sha256(pickle.dumps((state,control,forecast))).hexdigest())
            if metadata.get('route_choice_held_unknown_route_veh',0):raise AssertionError('Unknown current route')
            arms[label]=evaluate(cfg,state,control,raw,detectors,calibration,deadline=started+90)
        if len(set(fingerprints))!=1:raise AssertionError('Rate arms changed initial state/control/forecast')
        rows.append({'start_sec':second,'end_sec':second+450,'clock':clock,'same_initial_state_control_forecast_sha256':fingerprints[0],'arms':arms})
    result={'schema':'sc1004-resource-service-holdout/v1','rows':rows,'source_sha256':sources,
        'source_changes':[k for k,h in sources.items() if sha(ROOT/k)!=h], 'elapsed_sec':time.monotonic()-started,
        'scope':'450sec deterministic model counterfactuals in held seed13 time windows. Only rate differs between arms; no full optimizer, no VISSIM.',
        'limitation':'SC1004 SG2 resource timeline is exact. Other phase/native-group pairs and recorded warmup vectors do not all replay native clocks. Whole-network metrics are model differences, not native holdout prediction accuracy or observed treatment effects.'}
    if result['source_changes']:raise AssertionError('Pinned source/config changed')
    (ROOT/'diagnostics/sc1004_resource_service_holdout_integrated.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'elapsed_sec':result['elapsed_sec'],'source_changes':result['source_changes'],
        'rows':[{'start_sec':r['start_sec'],'arms':{k:{n:v for n,v in a.items() if n not in ('resource_accepted_events','area')} for k,a in r['arms'].items()}} for r in rows]},indent=2))


if __name__=='__main__':main()
