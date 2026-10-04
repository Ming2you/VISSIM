"""Reuse matched native component totals and the four completed predictions."""
import gzip
import csv
import hashlib
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
C=HERE.parent/'sc1001_connection'


def read(path):
    if str(path).endswith('.gz'):
        with gzip.open(path,'rt',encoding='utf-8') as f:return json.load(f)
    return json.loads(path.read_bytes())


def main():
    target=HERE/'fixed_assessment.json'
    if target.exists():raise FileExistsError(target)
    comp=read(HERE/'comparison.json')
    native=read(I/'seed43_fullplant_20260929/decomposition.json')
    summary=read(I/'closedloop_recorded2250_lever450_sc1001_shared_history_s43/summary.json')
    old=read(I/'closedloop_recorded2250_lever450_gate_full_four_s43_v3/summary.json')
    binding=read(C/'sc1001_shared_history_s43.json')
    arms={};resources={}
    for i,(name,key) in enumerate((('nc','held_actual'),('rm','rm'),('vsl','vsl'),('both','both'))):
        p=summary['results'][key];base=old['results'][key]
        assert p['commands']==base['commands']
        assert p['physical_cell_states'][0]==base['physical_cell_states'][0]
        assert all(abs(r['residual'])<1e-7 for r in p['ramps'].values())
        cost=p['cost_by_stock']
        model={road:cost['freeway:'+road] for road in ('FW_E','FW_W')}
        model['eight_on_ramps']=sum(v for k,v in cost.items() if k.startswith('ramp:'))
        actual=native['arms'][name]
        arms[name]=dict(predicted_veh_h=model,native_30s_veh_h=actual['native_30s_veh_h'],
            native_removal_count=actual['removal_count'],delta_omega=comp['costs'][name]['delta_vs_nc'],
            ramps=[x for x in comp['ramps'] if x['arm']==name])
        trace=read(C/f'sc1001_shared_history_s43_response_{i}.json.gz')
        q=trace['quantities'];assert len(q['owners'])==17
        resources[name]=dict(NP_upper=sum(o['net_inflow_veh'] for o in q['owners'].values()),
            NUF_veh_h=q['predicted_ramp_merge']['total_rate_veh_h'],
            initial_source_only_NP_uncertainty_bound_veh=binding['binding']['initial_sources'].get('initial_unresolved',0),
            maximum_physical_resource_exceedance_veh=trace['resource_max_exceedance'])
        assert trace['resource_max_exceedance']<1e-7
    for name,row in arms.items():
        for field in ('predicted_veh_h','native_30s_veh_h'):
            row['delta_'+field]={k:v-arms['nc'][field][k] for k,v in row[field].items()}
    marginal={}
    for label,field in (('actual','native_omega_veh_h'),('model','predicted_omega_veh_h')):
        values={arm:comp['costs'][arm][field] for arm in arms}
        marginal[label]=dict(RM_without_VSL=values['rm']-values['nc'],
            RM_with_VSL=values['both']-values['vsl'],VSL_without_RM=values['vsl']-values['nc'],
            VSL_with_RM=values['both']-values['rm'],
            interaction=values['both']-values['rm']-values['vsl']+values['nc'])
    result=dict(status='FOUR_ARM_RESPONSE_COMPLETE_COMBINED_GAIN_MISSED',seed=43,
        start_sec=2250,horizon_sec=450,previously_inspected_seed=True,
        exact_commands_and_initial_physical_state=True,arms=arms,resources=resources,marginal_omega_veh_h=marginal,
        best_of_four_matches=comp['omega_rank']['prediction'][0]==comp['omega_rank']['native'][0],
        ranking=comp['omega_rank'],native_regret_for_predicted_best_veh_h=comp['selected_native_regret_veh_h'],
        all_8_ramp_4_arm_mae_veh=comp['ramp_mae_vehicles'],
        interpretation=['RM alone best and VSL alone harmful are retained.',
            'Adding VSL to RM increases cost in both native and model; this state does not support forcing a VSL reward.',
            'RM benefit is severely underestimated and joint-vs-NC sign remains wrong.',
            'Fixed-arm feasibility/NP-NUF caps and actual SDMPC choice are separate checks.',
            'Native full-Omega uses5s, component totals30s; subtraction is not exact urban cost.',
            'Native matched uninserted delay integral is unavailable; external total waiting qualification remains incomplete.',
            'Earlier reference differs by multiple preceding corrections: no isolated attribution of overall MAE improvement to SC1001.'],
        native_runs=0,fitting=0,forecasts=4,
        source_pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            (HERE/'comparison.json',I/'seed43_fullplant_20260929/decomposition.json',
             I/'closedloop_recorded2250_lever450_sc1001_shared_history_s43/summary.json',C/'sc1001_shared_history_s43.json')})
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],marginal=marginal,
        components={a:r['delta_predicted_veh_h'] for a,r in arms.items()},resources=resources),ensure_ascii=False))


def flow_ledger():
    """Account for stock-change error; do not infer capacity or fit future flows."""
    target=HERE/'freeway_flow_ledger.json'
    if target.exists():raise FileExistsError(target)
    prediction=I/'closedloop_recorded2250_lever450_sc1001_shared_history_s43/summary.json'
    summary=read(prediction)
    old=ROOT.parent/'control-full-review/diagnostics'
    sources=[prediction,Path(__file__)]
    off_nodes={'10481':'OR_D_E_storage','10483':'lane_off_10483',
               '10643':'OR_F_E_storage','10682':'lane_off_10682'}
    arms={}
    for arm,key in (('nc','held_actual'),('rm','rm'),('vsl','vsl'),('both','both')):
        folder=(old/'dsd110_20260923/response_recalibration_20260924/gain_response/seed43/none'
                if arm=='nc' else old/'metanet_net_gain_goal_20260924/heldout43/observations'/arm)
        tables={}
        for filename in ('flows_30s.csv','boundaries_30s.csv'):
            path=folder/filename;sources.append(path)
            with path.open(encoding='utf-8-sig',newline='') as f:
                tables[filename]=[r for r in csv.DictReader(f) if r['road']=='FW_E'
                    and float(r['window_start_s'])>=2250.1-1e-7
                    and float(r['window_end_s'])<=2700.1+1e-7]
        rows=tables['flows_30s.csv'];assert len(rows)==15*31
        assert len({(r['window_start_s'],r['cell']) for r in rows})==15*31
        fields=('source_admissions','ramp_merges','off_departures','terminal_exits_inferred',
                'unexplained_entries','unexplained_losses','native_removals')
        native={k:sum(float(r[k]) for r in rows) for k in fields}
        for k in ('unexplained_entries','unexplained_losses','native_removals'):
            assert native[k]==0
        assert max(abs(float(r['conservation_residual_veh'])) for r in rows)==0
        native['initial_stock']=sum(float(r['start_n_veh']) for r in rows
                                    if abs(float(r['window_start_s'])-2250.1)<1e-7)
        native['final_stock']=sum(float(r['end_n_veh']) for r in rows
                                  if abs(float(r['window_end_s'])-2700.1)<1e-7)
        native['stock_change']=native['final_stock']-native['initial_stock']
        assert native['stock_change']==native['source_admissions']+native['ramp_merges']-native['off_departures']-native['terminal_exits_inferred']
        native_off={c:sum(float(r['crossings']) for r in tables['boundaries_30s.csv']
                         if r['connector']==c) for c in off_nodes}
        assert sum(native_off.values())==native['off_departures']
        flows=summary['results'][key]['control_area']['flow_counts']
        model_off={c:flows[f'freeway:FW_E->storage:{node}'] for c,node in off_nodes.items()}
        model=dict(source_admissions=flows['origin:FW_E->freeway:FW_E'],
                   ramp_merges=sum(v for k,v in flows.items() if k.startswith('merge_pending:') and k.endswith('->freeway:FW_E')),
                   off_departures=sum(model_off.values()),
                   terminal_exits_inferred=flows['freeway:FW_E->external:terminal:FW_E'])
        signs={'source_admissions':1,'ramp_merges':1,'off_departures':-1,'terminal_exits_inferred':-1}
        model['stock_change_from_flows']=sum(signs[k]*model[k] for k in signs)
        errors={k:signs[k]*(model[k]-native[k]) for k in signs}
        assert abs(sum(errors.values())-(model['stock_change_from_flows']-native['stock_change']))<1e-8
        arms[arm]=dict(native=native,predicted=model,stock_change_error_contributions_veh=errors,
            native_off=native_off,predicted_off=model_off,
            off_count_errors_veh={c:model_off[c]-native_off[c] for c in off_nodes})
    result=dict(arms=arms,native_interval_s=[2250.1,2700.1],model_interval_s=[2250,2700],
        interpretation=[
            'This is a stock-change ledger, not a causal TTT decomposition or a capacity estimate.',
            'Two direct off-ramp overflows dominate the NC aggregate stock-change error; raising freeway speed alone is not a supported correction.',
            'Native accepted source counts differ after the shared prefix. Attempted demand/uninserted delay is unavailable; no assignment to acceptance versus generation.',
            'Previous route-inventory candidates improved some absolute states but failed VSL gain tests; do not repeat an indiscriminate route toggle or coefficient grid.',
            'No future observations were supplied to the model. Future native counts are evaluation only.'],
        new_forecasts=0,new_native=0,fitting=0,
        source_pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({a:r['stock_change_error_contributions_veh'] for a,r in arms.items()}))


def selection_assessment():
    target=HERE/'selection_assessment.json'
    if target.exists():raise FileExistsError(target)
    selected=I/'closedloop_recorded2250_select_sc1001_shared_history_s43_r2'
    replay=I/'closedloop_recorded2250_select_check_sc1001_shared_history_s43_r2_replay_v3'
    report=read(selected/'unused_action.joint.json');s=report['selection']
    receipt=read(selected/'summary.json');r=read(replay/'summary.json')
    assert report['completed'] and read(selected/'unused_action.decision_budget.json')['output_completed']
    assert r['selection_completed_before_validation'] and not r['native_started']
    h,p=(r['results'][k] for k in ('held_actual','selected'))
    fixed=read(I/'closedloop_recorded2250_lever450_sc1001_shared_history_s43/summary.json')['results']['held_actual']
    assert h['ttt_omega_veh_h']==fixed['ttt_omega_veh_h']
    assert h['commands']==fixed['commands']
    assert h['ramps']==fixed['ramps'] and h['cost_by_stock']==fixed['cost_by_stock']
    resources=read(HERE/'selection_replay_resources.json')
    assert len(resources['rows'])==2
    assert all(row['max_resource_exceedance_veh']<1e-7 for row in resources['rows'])
    policy_changes=[]
    for before,after in zip(h['commands'],p['commands']):
        policy_changes.append({k:{x:dict(before=before[k][x],after=y) for x,y in after[k].items()
            if before[k].get(x)!=y} for k in ('vsl','meters','green_times','offsets')})
    cost_delta={k:p['cost_by_stock'].get(k,0)-h['cost_by_stock'].get(k,0)
                for k in p['cost_by_stock'].keys()|h['cost_by_stock'].keys()}
    partitions={road:cost_delta['freeway:'+road] for road in ('FW_E','FW_W')}
    partitions['eight_ramps']=sum(v for k,v in cost_delta.items() if k.startswith('ramp:'))
    partitions['other_omega']=sum(cost_delta.values())-sum(partitions.values())
    result=dict(status='SDMPC_SELECTION_AND_CANONICAL_REPLAY_COMPLETE_NOT_NATIVE_GAIN_QUALIFIED',
        held=dict(surrogate=s['held_objective'],canonical=h['ttt_omega_veh_h']),
        selected=dict(surrogate=s['selected_objective'],canonical=p['ttt_omega_veh_h']),
        delta=dict(surrogate=s['selected_objective']-s['held_objective'],
                   canonical=p['ttt_omega_veh_h']-h['ttt_omega_veh_h'],
                   outside=p['tracked_outside_residence_veh_h']-h['tracked_outside_residence_veh_h'],
                   tracked_total=p['ttt_with_tracked_outside_veh_h']-h['ttt_with_tracked_outside_veh_h']),
        canonical_delta_components_veh_h=partitions,command_changes=policy_changes,
        native_response_of_selected_command_available=False,
        pfo={k:s['pfo_warm_start'][k] for k in ('max_iterations','executed_iterations','accepted_iterations','converged','status')},
        sdmpc_candidates=s['candidates'],wall_sec=receipt['controller_wall_sec'],
        internal_prediction_counts={k:v for k,v in report['physical_response_cache'].items() if k!='rows'},
        tangent_axes=[dict(axes=len(t['cost_jacobian'][0]),cost_partitions=len(t['cost_jacobian'])) for t in s['tangent_derivatives']],
        independent_derivative_witness=s['independent_ad_witness_performed'],
        surrogate_final_constraints=s['final_constraints'],
        canonical_writer_and_resources_passed=True,canonical_quantity_caps_independently_recomputed=False,
        fixed_held_reproduced_exact=True,new_native=0,fitting=0,push=0,
        failure_history=['Initial selection CLI suffix rejected before init.',
            'Second selection init passed but SciPy access denied before optimization; existing dependency read approved, third completed.',
            'First replay path spelling failed before init; second preserved existing failure directory.',
            'Third replay computed held but observer intercepted raw endpoint before ledger attachment; no usable response file.',
            'Fourth replay attached observer after runtime install: two completed canonical forecasts.'],
        limitations=['Smooth signal/cycle-mean surrogate differs from exact execution model; no exact cost equality claimed.',
            'Tangent completion is not an independent Jacobian-vs-finite-difference check.',
            'Selected city/VSL joint gain is not proof of RM gain or native benefit.',
            'PFO and SDMPC finite iteration limits reached/no further executable step; not converged.'],
        source_pins={str(q):hashlib.sha256(q.read_bytes()).hexdigest() for q in
            (selected/'summary.json',selected/'unused_action.joint.json',replay/'summary.json',HERE/'selection_replay_resources.json')})
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    old=read(HERE.parent/'sc1001_service_history/verification.json')
    pins=dict(old['unchanged_core_pins'])
    pins.update({k:v for k,v in old['source_pins'].items() if k.startswith('evaluation/')})
    pins.update(read(HERE/'protocol.json')['source_pins'])
    pins.update(read(HERE/'selection_protocol.json')['source_pins'])
    for name,digest in pins.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    verification=dict(status='SAVED_EVIDENCE_VERIFIED_NOT_GAIN_QUALIFIED',source_pins=pins,
        completed_fixed450_forecasts=4,completed_selection_decisions=1,
        internal_selection_predictions=report['physical_response_cache']['total_rollouts'],
        completed_canonical_replay_forecasts=2,failed_observer_after_held_forecast=1,
        unit_tests_reused=23,unit_tests_rerun=0,new_native=0,new_fzp_scans=0,fit=0,push=0,
        model_parameters_changed_in_this_step=False,production_default_enabled=False,
        remaining_owned_processes=0,goal='ACTIVE / NOT_QUALIFIED',
        artifacts={q.name:hashlib.sha256(q.read_bytes()).hexdigest() for q in
            (target,HERE/'comparison.json',HERE/'fixed_assessment.json',HERE/'freeway_flow_ledger.json',
             HERE/'assess.py',HERE/'verify_selection.py')})
    (HERE/'verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],delta=result['delta'],components=partitions,
                         pfo=result['pfo'],sdmpc=result['sdmpc_candidates']),ensure_ascii=False))


if __name__=='__main__':
    if sys.argv[1:]==['--flow-ledger']:flow_ledger()
    elif sys.argv[1:]==['--selection']:selection_assessment()
    elif not sys.argv[1:]:main()
    else:raise SystemExit('usage: assess.py [--flow-ledger|--selection]')
