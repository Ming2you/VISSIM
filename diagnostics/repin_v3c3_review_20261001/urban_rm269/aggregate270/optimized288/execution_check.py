"""Two ordinary responses to the completed237-axis choice; no new optimization."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key] = '1'
import copy
import gzip
import hashlib
import importlib.util
import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
receipt = read(HERE/'full_decision_execution_r3.json')
FULL = Path(receipt['output'])
OUT = FULL.parent/'execution3300'
SOURCE = Path(receipt['decisions'])


def save(name, value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')


def clean(x):
    if isinstance(x,dict):
        return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(tuple,list)):
        return [clean(v) for v in x]
    if isinstance(x,str):
        if x.startswith('<evaluation.controllers.') and ' object at 0x' in x:
            return re.sub(r' object at 0x[0-9A-Fa-f]+>', ' object>',x)
        return x
    if isinstance(x,(int,float,bool)) or x is None:
        return x
    if hasattr(x,'tolist'):
        return x.tolist()
    return clean(repr(x)[:600])


def main():
    assert receipt['status'] == 'complete_pending_review'
    assert not OUT.exists()
    assert not any((p/'STOP').exists() for p in (ROOT,HERE,HERE.parent,OUT.parent))
    pins = dict(receipt['source_pins'])
    for p in (Path(__file__),FULL/'unused.json',FULL/'reference.json',FULL/'state.json',FULL/'network.json'):
        pins[str(p)] = sha(p)
    assert all(sha(p) == h for p,h in pins.items())
    sys.path[:0] = [str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    sys.argv = ['verify.py','--at','3300','--out',str(OUT),'--no-prediction',
                '--tuning',str(HERE/'config.json'),'--decisions',str(SOURCE)]
    spec = importlib.util.spec_from_file_location('retained_verifier288',ROOT/'diagnostics/repin_v3c3_review_20261001/urban260/verify.py')
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter, sdmpc_pfo, sdmpc_sequence as seq
    from evaluation.controllers import physical_ramp_branches as ramps, signal_actuation_contract as signals
    from evaluation.controllers import area_leader_objective as constraints
    from evaluation.controllers.control_area_objective import get_ledger
    from evaluation.controllers.area_runtime import model_inventory
    from src.controllers import rollout_endpoint as endpoint
    from src.models.state import ControlAction
    original_main = adapter.main

    def wrapped_main():
        captured = {}
        original_bounds, original_forecast = ramps.configure_operating_bounds, adapter.demand_from_state
        def capture_bounds(state,cfg,reference):
            captured.update(state=state,cfg=cfg)
            return original_bounds(state,cfg,reference)
        def capture_forecast(*a,**kw):
            result = original_forecast(*a,**kw)
            captured['forecast'] = result
            return result
        ramps.configure_operating_bounds, adapter.demand_from_state = capture_bounds, capture_forecast
        def audit(reference,coord,policy,options,evaluate,derivative,quantities,check_budget,emit):
            state,cfg = captured['state'],captured['cfg']
            assert state.time_sec == 3300 and cfg.simulation.T_f_sec == 5 and cfg.simulation.T_u_sec == 10
            assert len(coord.axes) == 237 and sum(a['kind']=='vsl' for a in coord.axes) == 24
            assert not policy.get('fixed_vsl')
            assert clean(vars(state)) == clean(read(FULL/'state.json'))
            assert clean(vars(cfg.network)) == clean(read(FULL/'network.json'))
            old_reference = read(FULL/'reference.json')
            for k in ('green_times','offsets','vsl','ramp_metering','inflow_outflow_allocation'):
                assert getattr(reference,k) == old_reference[k],k
            initial_stock = copy.deepcopy(get_ledger(state).stocks)
            selected = adapter.control_from_json(FULL/'unused.json',cfg,ControlAction)
            held = reference.copy()
            held.N_P_star,held.N_UF_star = selected.N_P_star,selected.N_UF_star
            results = {}
            for arm,action in (('hold',held),('selected',selected)):
                coord.validate(action)
                blocks = seq.actions(action,3)
                for block in blocks:
                    signals.validate_writer(block,cfg,adapter.load_signal_group_actuation_plan(),'experiment')
                started = time.perf_counter()
                with seq.prediction_scope(action,cfg,3300,3) as visits:
                    point = endpoint.evaluate_price_point(state,action,copy.deepcopy(captured['forecast'][:3]),(),
                        endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
                assert not point.aborted and len(point.states)==3 and visits==[0,1,2]
                response = point.control_area_response
                assert response['model_constraint_coverage']['complete'] and response['conditional_model_feasibility_witness']
                exceed = max((r['exceedance_veh'] for r in response['resource_allocations']),default=0.)
                assert exceed < 1e-7
                for current in (state,*point.states):
                    get_ledger(current).assert_stocks(model_inventory(current,cfg))
                assert get_ledger(state).stocks == initial_stock
                costs = {}
                for row in response['residence']:
                    for key,value in row['inside_veh'].items():
                        costs[key] = costs.get(key,0.)+value*row['dt_h']
                assert abs(sum(costs.values())-point.ttt)<1e-7
                follower = adapter._PHASE_VECTOR_FOLLOWER['ref']
                shared = constraints.shared_urban_quantities(follower,response,start_sec=3300,horizon_steps=3)
                feasibility = constraints.shared_quantity_constraints(follower,action,shared,start_sec=3300,horizon_steps=3,
                    np_mode='cap',target_np_veh=action.N_P_star,np_tolerance_veh=options['shared_tolerance'],
                    nuf_mode='cap',target_nuf_veh_h=action.N_UF_star,nuf_tolerance_veh_h=options['shared_tolerance'])
                results[arm] = dict(omega_ttt_veh_h=point.ttt,costs_by_stock=costs,shared_constraints=feasibility,
                    predicted_merge=point.control_area['predicted_ramp_merge'],resource_max_exceedance=exceed,
                    writer_three_blocks=True,conservation_states=4,wall_sec=time.perf_counter()-started,
                    vsl_by_block=[b.vsl for b in blocks])
                (OUT/(arm+'.response.json.gz')).write_bytes(gzip.compress(json.dumps(response,allow_nan=False).encode('utf8')))
                save(arm+'.json',results[arm])
                print('ORDINARY237',arm,point.ttt,feasibility['feasible'],flush=True)
            assert all(sha(p)==h for p,h in pins.items())
            save('summary.json',dict(status='complete',start_sec=3300,end_sec=3750,forecasts=2,optimizer_calls=0,
                native_runs=0,fits=0,future_observation_inputs=False,
                application=dict(same_full_selection_state=True,same_reference=True,axes=237,vsl_axes=24),
                source_pins=pins,results=results))
            raise verifier.Done()
        sdmpc_pfo.solve = audit
        return original_main()
    adapter.main = wrapped_main
    verifier.main()


if __name__ == '__main__':
    main()
