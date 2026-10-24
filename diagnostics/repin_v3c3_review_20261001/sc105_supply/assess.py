"""Bounded SC105 native-choice repair: source, supply and gain checks."""
import ast
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
PINS={}


def read(path):
    content=path.read_bytes();PINS[str(path)]=hashlib.sha256(content).hexdigest()
    return json.loads(gzip.decompress(content) if path.suffix=='.gz' else content)


def budget(trace):
    extra=trace['supply_diagnostics'];rows=[]
    for i,start in enumerate((2700,2850,3000)):
        movements={}
        for m in extra['movements']:
            incoming=sum(t['vehicles'] for t in extra['transfers'] if start<=t['start_sec']<start+150 and t['target']=='movement:'+m)
            outgoing=sum(t['vehicles'] for t in extra['transfers'] if start<=t['start_sec']<start+150 and t['source']=='movement:'+m)
            q0,q1=(extra['states'][j]['queues'][m] for j in (i,i+1))
            assert abs(q0+incoming-outgoing-q1)<1e-8
            movements[m]=dict(initial_queue=q0,arrivals=incoming,departures=outgoing,final_queue=q1)
        rows.append(dict(start_sec=start,movements=movements))
    return rows


def main():
    # Mutable completion receipt is not an immutable source pin.
    protocol=json.loads((HERE/'protocol.json').read_bytes())
    for p,expected in protocol['production_pins'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==expected,p
    base_cfg=read(HERE.parent/'sc1001_connection/candidate_config.json');new_cfg=read(HERE/'candidate_config.json')
    old_path=base_cfg['urban']['movements']['physical_route_topology']
    new_path=new_cfg['urban']['movements']['physical_route_topology']
    new_cfg['urban']['movements']['physical_route_topology']=old_path
    assert new_cfg==base_cfg
    before_doc=read(ROOT/old_path);after_doc=read(ROOT/new_path)
    additions={k:after_doc['native_choice_groups'].pop(k) for k in ('SC105_N_SC1002','SC105_W_SC1003')}
    assert before_doc==after_doc
    assert hashlib.sha256((ROOT/before_doc['network']['path']).read_bytes()).hexdigest()==before_doc['network']['sha256']
    result=dict(status='native_choice_connection_verified_gain_not_qualified',goal_complete=False,
        previous_goal_turn='no_progress_existing_results_restatement',new_native_runs=0,fitting=0,optimizer_calls=0,
        autonomous_future_traffic_inputs=False,forecast_count=8,trace_forecasts=2,candidate_forecasts=6,
        sessions={'35405':'exit0','86994':'exit0','10012':'exit0'},init_only_reused_session='89473 exit0',
        config_change='One evidence reference; two native choice groups added; demand/network/objective unchanged.',
        native_choice_groups=additions,seed47={},seed43={},input_sha256=PINS)
    changed={}
    for original,current in [('driver_before.txt',I/'probe_selected_arrival_path.py'),('physical_movement_routes_before.txt',ROOT/'evaluation/controllers/physical_movement_routes.py')]:
        funcs=lambda p:{n.name:ast.dump(n) for n in ast.parse(p.read_text(encoding='utf-8-sig')).body if isinstance(n,ast.FunctionDef)}
        a,b=funcs(HERE/original),funcs(current)
        names=sorted(k for k in a.keys()|b.keys() if a.get(k)!=b.get(k));changed[str(current)]=names
        assert names==(['probe_levers'] if original=='driver_before.txt' else ['configure_native_choice_groups'])
    result['changed_functions']=changed
    old_dir=I/'closedloop_recorded2700_select_check_trace10681_sc1004_response47'
    trace_dir=I/'closedloop_recorded2700_select_check_trace10681_sc105_supply47'
    new_dir=I/'closedloop_recorded2700_select_check_trace10681_sc105_native_choice47'
    native=read(HERE.parent/'sc1004_response/assessment.json')
    wall=0.;max_residual=0.
    for arm in ('held_actual','selected'):
        reference=read(old_dir/(arm+'.json'));traced=read(trace_dir/(arm+'.json'));candidate=read(new_dir/(arm+'.json'))
        wall+=traced.pop('wall_sec')+candidate['wall_sec'];reference.pop('wall_sec');assert traced==reference
        name=arm+'_RM_C10681_trace.json.gz'
        original_trace=read(old_dir/name);new_trace=read(trace_dir/name);candidate_trace=read(new_dir/name)
        diagnostic=new_trace.pop('supply_diagnostics');assert new_trace==original_trace;new_trace['supply_diagnostics']=diagnostic
        assert candidate_trace['initial_stock']==original_trace['initial_stock']
        assert candidate['commands']==traced['commands']
        assert candidate['executed_control_blocks']==traced['executed_control_blocks']
        assert candidate['saved_state_stock_witness']['passed']
        max_residual=max(max_residual,*(abs(v['residual']) for v in candidate['ramps'].values()))
        assert candidate['max_resource_exceedance_veh']<1e-7
        before_budget,after_budget=budget(new_trace),budget(candidate_trace)
        source='SC1005_N_SC105_to_W_SC1004'
        result['seed47'][arm]=dict(
            native_10565=[r['native_10565_flow'] for r in native['arms'][arm]['windows']],
            before_10565=[r['movements'][source]['departures'] for r in before_budget],
            after_10565=[r['movements'][source]['departures'] for r in after_budget],
            before_supply=before_budget,after_supply=after_budget,
            before_ramps=traced['ramps'],after_ramps=candidate['ramps'],
            before_omega=traced['ttt_omega_veh_h'],after_omega=candidate['ttt_omega_veh_h'],
            before_tracked_outside=traced['tracked_outside_residence_veh_h'],after_tracked_outside=candidate['tracked_outside_residence_veh_h'])
    runtime=read(new_dir/'runtime.json')
    old_runtime=read(trace_dir/'runtime.json')
    for group,values in old_runtime['metadata']['native_choice_groups'].items():
        assert runtime['metadata']['native_choice_groups'][group]==values
    result['installed_choices47']={k:runtime['metadata']['native_choice_groups'][k] for k in additions}
    old43=read(HERE.parent/'sc1001_independent_s43/comparison.json')
    new43=I/'closedloop_recorded2250_lever450_sc105_native_choice43'
    old43dir=Path(old43['prediction_source_dir'])
    new43runtime=read(new43/'runtime.json');old43runtime=read(old43dir/'runtime.json')
    assert new43runtime['initial_source_sha256']==old43runtime['initial_source_sha256']
    out43={arm:read(new43/(('held_actual' if arm=='nc' else arm)+'.json')) for arm in ('nc','rm','vsl','both')}
    errors={m:[] for m in ('arrival','merge','final_stock')}
    for arm,row in out43.items():
        name='held_actual' if arm=='nc' else arm
        old=read(old43dir/(name+'.json'))
        assert row['commands']==old['commands'] and row['executed_control_blocks']==old['executed_control_blocks']
        wall+=row['wall_sec'];max_residual=max(max_residual,*(abs(v['residual']) for v in row['ramps'].values()))
        native_row=old43['costs'][arm]
        result['seed43'][arm]=dict(native_omega=native_row['native_omega_veh_h'],historical_omega=native_row['predicted_omega_veh_h'],
            after_omega=row['ttt_omega_veh_h'],native_delta=native_row['delta_vs_nc']['native_omega_veh_h'],
            historical_delta=native_row['delta_vs_nc']['predicted_omega_veh_h'],after_delta=row['ttt_omega_veh_h']-out43['nc']['ttt_omega_veh_h'],
            tracked_outside=row['tracked_outside_residence_veh_h'],ramps=row['ramps'])
        for pair in old43['ramps']:
            if pair['arm']==arm:
                for m in errors:errors[m].append(abs(row['ramps'][pair['ramp']][m]-pair['actual'][m]))
    assert max_residual<1e-7
    result.update(wall_forecasts_sec=wall,max_ramp_balance_residual=max_residual,
        seed43_ramp_mae={k:sum(v)/len(v) for k,v in errors.items()},
        seed43_native_rank=sorted(out43,key=lambda k:result['seed43'][k]['native_omega']),
        seed43_candidate_rank=sorted(out43,key=lambda k:result['seed43'][k]['after_omega']),
        interpretation='Native static choice mismatch repaired. Supply improves modestly;10681 control response and joint RM/VSL gain remain unqualified.',
        limitations=['Native43 reference is a previously inspected different seed, not a blind holdout.',
            'Historical43 baseline reused from prior compatible scalar implementation; not a fresh rerun of all earlier code.',
            'Execution-command-conditioned predictions, not new SDMPC optimization or VISSIM runs.',
            'Tracked outside cost is not identical to full native network plus uninserted waiting.',
            'No claim that current initial chosen destinations or position/lane travel are fully repaired.'])
    result['input_sha256']=dict(PINS)
    (HERE/'assessment.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    protocol.update(status='complete_not_gain_qualified',candidate_forecasts_completed=6,sessions=result['sessions'],
        wall_forecasts_sec=wall,assessment_sha256=hashlib.sha256((HERE/'assessment.json').read_bytes()).hexdigest())
    (HERE/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','forecast_count','wall_forecasts_sec','max_ramp_balance_residual','seed43_ramp_mae','seed43_native_rank','seed43_candidate_rank')}))
    print(json.dumps({k:{f:v[f] for f in ('native_delta','historical_delta','after_delta')} for k,v in result['seed43'].items()}))


if __name__=='__main__':main()
