"""Paired held-action time-holdout evaluation; no optimizer or VISSIM."""
from pathlib import Path
import hashlib,json,pickle,time
from diagnostics.test_native_route_choice import fixture
from evaluation.controllers import route_choice_corridor as rc,area_runtime
ROOT=Path(__file__).resolve().parents[1]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def evaluate(payload):
    cfg,state,control,raw,detectors=pickle.loads(payload)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,runtime_setup
    from src.models.demand import DemandStep
    runtime_setup.install_worker_runtime(adapter,cfg,raw,detectors)
    from src.controllers.rollout_endpoint import ObjectiveSpec,evaluate_price_point
    result=evaluate_price_point(state,control,adapter.demand_from_state(raw,cfg,DemandStep,3),[],ObjectiveSpec(cfg,depth_override=3,score_mode='raw'))
    for item in result.states:item._control_area_ledger.assert_stocks(area_runtime.model_inventory(item,cfg))
    sources={}
    for spec in rc._specs(cfg):
        if not spec.get('generated_inputs'):continue
        no=next(iter(spec['generated_inputs']));storage=spec['prefix_storage'];cap=spec['capacity_veh'][storage]
        sources[no]={'initial_veh':cap-state.urban_link_storage[storage],'final_veh':cap-result.states[-1].urban_link_storage[storage],
            'state_n_150sec':[(n+1)*150 for n in range(len(result.states))],
            'trajectory_n_veh':[cap-s.urban_link_storage[storage] for s in result.states],
            'generation':result.states[-1].native_internal_input_state['inputs'][no],
            'accepted_by_receiver_veh':{b['destination']:result.control_area['flow_counts'].get('storage:'+storage+'->storage:'+b['destination'],0) for b in spec['branches'].values()},
            'source_service_veh_h':spec['native_fixed_service'].get('calibrated_service_veh_h',spec['per_lane_capacity_veh_h'])}
        x=sources[no];x['stock_closure_veh']=x['initial_veh']+x['generation']['admitted_veh']-sum(x['accepted_by_receiver_veh'].values())-x['final_veh']
        if abs(x['stock_closure_veh'])>1e-8:raise AssertionError('Source closure')
    return {'sources':sources,'endpoint':{k:v for k,v in result.control_area.items() if k!='flow_counts'},
        'route_diagnostics':rc.diagnostics(result.states[-1],cfg),'inventory_closed_every_150_sec':True,
        'final_inventory':area_runtime.model_inventory(result.states[-1],cfg)}

def main():
    paths=[Path(__file__),ROOT/'diagnostics/test_native_route_choice.py',ROOT/'diagnostics/native_internal_input_1091_ver2.json',
        ROOT/'diagnostics/area_candidate_configs/n7_area_beta0.json',ROOT/'diagnostics/native_sc15_service_calibration.json',
        ROOT/'diagnostics/route_choice_corridor_1099_sc15_calibrated.json',ROOT/'diagnostics/route_choice_corridor_1100_sc15_calibrated.json',
        ROOT/'diagnostics/native_sc15_source_discharge.json']+list((ROOT/'evaluation/controllers').glob('*.py'))
    before={str(p.relative_to(ROOT)):sha(p) for p in paths};started=time.monotonic();rows=[]
    measured=json.loads((ROOT/'diagnostics/native_sc15_source_discharge.json').read_text(encoding='utf-8'))
    for second in (900,2700):
        cases={}
        for calibrated in (False,True):
            cfg,state,control,raw,detectors=fixture(second=second,calibrated=calibrated);payload=pickle.dumps((cfg,state,control,raw,detectors));result=evaluate(payload)
            if payload!=pickle.dumps((cfg,state,control,raw,detectors)):raise AssertionError('Original candidate changed')
            cases['calibrated' if calibrated else 'inherited']=result
        rows.append({'start_sec':second,'duration_sec':450,'cases':cases,
            'measured':{no:next(w for w in data['windows'] if w['start_sec']==second and w['end_sec']==second+450) for no,data in measured['inputs'].items()}})
    result={'schema':'sc15-service-time-holdout/v1','rows':rows,'source_sha256':before,'source_changes':[p for p,h in before.items() if sha(ROOT/p)!=h],
        'elapsed_sec':time.monotonic()-started,'scope':'Same-seed time holdouts excluded from fit; held observed native/open command, no optimizer, all other source/model settings identical.',
        'limits':['Realized stochastic source arrivals differ from deterministic nominal forecast; changes in whole-network metrics are descriptive and not isolated observed control performance.',
            'The source-specific queued-discharge lower prior also replaces the directly serial branch cap; global per-lane scale and all other controller service budgets remain unchanged.',
            'Seed14 validation remains pending. Current native branch proportions are preserved and no future route observation is used by the rollout.']}
    (ROOT/'diagnostics/native_sc15_service_holdout.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'rows':[{'start_sec':r['start_sec'],'model':{k:v['sources'] for k,v in r['cases'].items()},'measured':r['measured']} for r in rows],'source_changes':result['source_changes'],'elapsed_sec':result['elapsed_sec']}))

if __name__=='__main__':main()
