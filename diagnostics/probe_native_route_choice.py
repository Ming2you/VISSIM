"""Bounded held-action source-generation audit using the actual shared runtime."""
from pathlib import Path
import hashlib,json,pickle
from diagnostics.test_native_route_choice import fixture,endpoint_worker,base
from evaluation.controllers import route_choice_corridor as rc
from evaluation.controllers.fixed_signal_schedule import _union_green_overlap
ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    paths=[ROOT/p for p in ('evaluation/controllers/route_choice_corridor.py','evaluation/controllers/native_internal_input.py',
        'evaluation/controllers/runtime_setup.py','evaluation/controllers/urban_flow_accounting.py',
        'diagnostics/route_choice_corridor_1099_ver2.json','diagnostics/route_choice_corridor_1100_ver2.json',
        'diagnostics/native_internal_input_1091_ver2.json','diagnostics/area_candidate_configs/n7_area_beta0.json',
        'diagnostics/test_native_route_choice.py','diagnostics/native_sc15_clock_audit.json')]+[Path(__file__)]
    before={str(p.relative_to(ROOT)):sha(p) for p in paths};runs=[]
    for second in (900,2700):
        cfg,state,control,raw,detectors=fixture(second=second);initial=pickle.dumps(state.route_choice_corridor_state)
        point,local,native=endpoint_worker(pickle.dumps((cfg,state,control,raw,detectors,3)))
        if pickle.dumps(state.route_choice_corridor_state)!=initial:raise AssertionError('Input candidate was mutated')
        (original,action)=base(second);tuning=original[3]
        generation=json.loads((ROOT/tuning['urban']['native_internal_inputs']).read_text())
        decision_dir=ROOT/'evaluation/runs/codex_area_observed_nc_s13_20260910/decisions_codex_area_observed_nc_s13_20260910'
        rawpath=decision_dir/(f'state_{second:06d}.json' if second==900 else f'anchor_{second:06d}.json')
        rows={}
        for spec in rc._specs(cfg):
            if not spec.get('generated_inputs'):continue
            no=next(iter(spec['generated_inputs']));storage=spec['prefix_storage']
            service=spec['native_fixed_service'];program=rc._native_program(service)
            rows[no]={'source':spec['decision_link'],'decision':spec['decision'],'storage':storage,'capacity_veh':spec['capacity_veh'][storage],
                'initial_veh':rc._tracked(state.route_choice_corridor_state,storage),'final_veh':sum(c['vehicles'] for c in local['cohorts'] if c['storage']==storage),
                'generation':native['inputs'][no],'final_route_veh':{route:sum(c['vehicles'] for c in local['cohorts'] if c['storage']==storage and c['route']==route) for route in spec['branches']},
                'accepted_by_receiver_veh':{branch['destination']:point['flow_counts'].get('storage:'+storage+'->storage:'+branch['destination'],0) for branch in spec['branches'].values()},
                'inherited_service_per_lane_veh_h':spec['per_lane_capacity_veh_h'],'native_cycle_sec':program.cycle_length_sec,
                'native_green_per_cycle_sec':_union_green_overlap(program,(service['signal_group'],),0.,program.cycle_length_sec,service['controller_offset_sec'])}
            x=rows[no]
            if abs(x['initial_veh']+x['generation']['admitted_veh']-sum(x['accepted_by_receiver_veh'].values())-x['final_veh'])>1e-8:raise AssertionError('Native source stock closure')
        runs.append({'start_sec':second,'duration_sec':450,'raw_sha256':sha(rawpath),'raw_path':str(rawpath.relative_to(ROOT)),
            'previous_action_path':str((decision_dir/'action_000001.json').relative_to(ROOT)),'previous_action_sha256':sha(decision_dir/'action_000001.json'),
            'initial_omega_veh':sum(v['inside'] for v in state._control_area_ledger.stocks.values()),'source_stocks':rows,
            'held_unknown_route_veh':sum(c['vehicles'] for c in local['cohorts'] if c['stage']=='unknown'),
            'endpoint':{k:v for k,v in point.items() if k!='flow_counts'},'effective_native_generation_contract':generation,
            'all_model_stocks_closed_each_150s':True,'candidate_input_unchanged':True})
    report={'schema':'native-route-choice-integration/v1','scope':'Actual configuration/projection, existing fixed source timing and held native/open action for450s; no optimizer or VISSIM',
        'runs':runs,'source_sha256':before,'source_changes':[k for k,v in before.items() if sha(ROOT/k)!=v],
        'limits':['Source200:150 is the conditional native route prior; current route labels are preserved.',
            'Inherited per-lane206.530612 capacity times native green35/160 gives45.178571veh/h. This has not been identified as actual SC15 saturation capacity.',
            'The low inherited model scale causes substantial finite-source backlog against native desired280veh/h in the900s fixture; do not report this as calibrated physical fidelity.',
            'Before-head source gate is applied at accepted branch discharge; the2–4m gap is not a separate reservoir. Already past-head observed vehicles skip a second signal crossing.',
            'Finite typed mass uses the existing accepted receiver allocator; exact microscopic one-lane FIFO blocking between route tags is not reconstructed from aggregate predictions.',
            'Downstream existing receiver dynamics resume after native route endpoints; additional native input repairs are inherited from the explicitly embedded test contract, not inferred here.']}
    (ROOT/'diagnostics/native_route_choice_integration.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'runs':[{'start_sec':r['start_sec'],'sources':r['source_stocks'],'held_unknown':r['held_unknown_route_veh']} for r in runs],'source_changes':report['source_changes']},ensure_ascii=False))
if __name__=='__main__':main()
