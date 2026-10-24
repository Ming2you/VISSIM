"""Compare the finite saved-state service-wiring experiment, without new simulation."""
import ast
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
R=HERE.parent
ROOT=R.parents[1]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
C=R/'sc1001_connection'
PINS={}


def read(p):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)


def main():
    target=HERE/'assessment.json'
    if target.exists():raise FileExistsError(target)
    spec=importlib.util.spec_from_file_location('saved_scorer',R/'sc1001_route_inventory_s47/assess.py')
    scorer=importlib.util.module_from_spec(spec);spec.loader.exec_module(scorer)
    old_routed=read(R/'routed_ramp_conflict/assessment.json')
    static={};seconds=0.;max_resource=0.
    before_folder=I/'closedloop_recorded2700_select_check_trace10681_mainline_terms47'
    after_folder=I/'closedloop_recorded2700_select_check_trace10681_declared_drain47'
    native=read(R/'ramp10681_mainline/assessment.json')
    native_off=read(R/'ramp10681_mainline/drain_audit.json')
    for name,arm in (('held_actual','hold'),('selected','selected')):
        a=read(before_folder/(name+'.json'));b=read(after_folder/(name+'.json'))
        assert a['commands']==b['commands']
        if name=='held_actual':assert b['validation']['all_actuator_and_step_constraints_checked']
        else:
            assert b['validation']['prewrite_binding_passed'] and b['validation']['written_command_binding_passed']
        assert b['canonical_quantity_constraints']['feasible'] and b['saved_state_stock_witness']['passed']
        seconds+=b['wall_sec'];max_resource=max(max_resource,b['max_resource_exceedance_veh'])
        before=read(before_folder/(name+'_RM_C10681_trace.json.gz'))
        after=read(after_folder/(name+'_RM_C10681_trace.json.gz'))
        assert before['mainline_diagnostics']['initial_and_block_states'][0]==after['mainline_diagnostics']['initial_and_block_states'][0]
        off=after['offramp_diagnostics'];assert off['description']['drain_service_veh_h']==2250
        service=[r for r in off['resources'] if r['kind']=='physical_offramp_target_service']
        room=[r for r in off['resources'] if r['kind']=='physical_offramp_target_room']
        assert len(service)==len(room)==450 and all(abs(r['available_veh']-2250/3600)<1e-12 for r in service)
        states=off['states']
        for s in states:
            assert abs(s['stock']-states[0]['stock']-s['admitted']+s['departed'])<1e-7
            assert 0<=s['stock']<=off['description']['storage_capacity_veh']+1e-7
        final=after['mainline_diagnostics']['initial_and_block_states'][-1]
        final_old=before['mainline_diagnostics']['initial_and_block_states'][-1]
        terms=[r for r in after['mainline_diagnostics']['speed_terms'] if r['cell']==11]
        static[arm]=dict(before=scorer.summarize(a),after=scorer.summarize(b),
            off_entry_before=a['control_area']['flow_counts']['freeway:FW_E->storage:lane_off_10682'],
            off_entry_after=states[-1]['admitted'],native_entry=147,
            off_states=states,min_target_room_veh=min(r['available_veh'] for r in room),
            negative_post_equation_seconds=sum(r['post_equation_change'] < -1e-7 for r in terms),
            final_cell11_speed_kmh=dict(before=final_old['speed'][11],after=final['speed'][11],
                native=native['arms'][name]['snapshots']['3150.0']['11']['native']['speed']),
            native_off_samples=native_off['arms'][arm]['native_samples'])
    routed={}
    for seed,start,pairs in ((43,2250,(('nc','held_actual'),('rm','rm'),('vsl','vsl'),('both','both'))),
                             (47,2700,(('hold','held_actual'),('release','release_actual')))):
        a=read(I/f'closedloop_recorded{start}_lever450_routed_gap{seed}_v1/summary.json')
        b=read(I/f'closedloop_recorded{start}_lever450_declared_drain{seed}_v1/summary.json')
        receipt=read(C/f'declared_drain{seed}_v1.json')
        assert receipt['mass_ledger_matches']
        cases={};route_error=ramp_error=0.
        for i,(arm,key) in enumerate(pairs):
            x,y=a['results'][key],b['results'][key]
            assert x['commands']==y['commands'] and x['physical_cell_states'][0]==y['physical_cell_states'][0]
            assert y['validation']['all_actuator_and_step_constraints_checked']
            seconds+=y['wall_sec']
            proof=read(C/f'declared_drain{seed}_v1_response_{i}.json.gz')
            previous=read(C/f'routed_gap{seed}_v1_response_{i}.json.gz')
            assert previous['route_inventory_checks'][0]==proof['route_inventory_checks'][0]
            assert len(proof['quantities']['owners'])==17
            max_resource=max(max_resource,proof['resource_max_exceedance'])
            route_error=max(route_error,max(c['max_cell_residual'] for s in proof['route_inventory_checks'] for c in s['roads'].values()))
            ramp_error=max(ramp_error,max(abs(r['residual']) for r in y['ramps'].values()))
            cases[arm]=dict(before=scorer.summarize(x),after=scorer.summarize(y),
                off10682_entry=y['control_area']['flow_counts']['freeway:FW_E->storage:lane_off_10682'],
                final_cell11_speed_kmh=y['physical_cell_states'][-1]['speed_kmh']['FW_E'][11])
        assert max(route_error,ramp_error)<1e-7
        reference=pairs[0][0]
        deltas={arm:{mode:{k:cases[arm][mode][k]-cases[reference][mode][k] for k in cases[arm][mode]}
                     for mode in ('before','after')} for arm in cases if arm!=reference}
        for arm,d in deltas.items():d['native']=old_routed['seeds'][str(seed)]['deltas'][arm]['native']
        routed[seed]=dict(cases=cases,deltas=deltas,max_route_residual=route_error,max_ramp_residual=ramp_error)
    assert max_resource<1e-7
    changed={}
    for path in read(HERE/'protocol.json')['source_before']:
        p=ROOT/path;before=HERE/(p.name+'.before')
        def funcs(data):
            return {n.name:ast.dump(n,include_attributes=False) for n in ast.walk(ast.parse(data))
                    if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
        left,right=funcs(before.read_bytes()),funcs(p.read_bytes())
        changed[path]=sorted(k for k in left.keys()|right.keys() if left.get(k)!=right.get(k))
        PINS[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    assert changed['evaluation/controllers/lane_plant_runtime.py']==['initialize','install_direct_drain_services']
    assert changed['evaluation/controllers/lane_offramp_runtime.py']==['drain']
    assert changed[str((I/'probe_selected_arrival_path.py').relative_to(ROOT)).replace('\\','/')]==['probe_levers']
    out=dict(status='DECLARED_SERVICE_CONNECTED_BUT_GAIN_NOT_QUALIFIED',static47=static,routed=routed,
        full_forecasts=8,forecast_seconds=seconds,changed_functions=changed,max_resource_exceedance=max_resource,
        new_native=0,new_fzp_scan=0,coefficient_fit=0,autonomous_forecasts=True,source_pins=PINS,
        limitations=['A service-wiring repair is not validation of 2250 as physical saturation capacity.',
            'Static exits still over-request10682 and recovery is too fast after the artificial queue clears.',
            'Routed comparisons use the earlier SC1001 candidate, not the later SC105 candidate.',
            'No new independent seed;43 and47 are existing separate-state checks. No optimizer or native run.'])
    target.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(status=out['status'],seconds=seconds,static47={a:static[a]['final_cell11_speed_kmh'] for a in static},
        deltas={s:r['deltas'] for s,r in routed.items()}),ensure_ascii=False))


if __name__=='__main__':main()
