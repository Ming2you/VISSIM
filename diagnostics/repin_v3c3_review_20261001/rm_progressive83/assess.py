"""Assess completed finite RM paths; never run a model or read FZP."""
import hashlib
import json
from pathlib import Path

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
I = ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
OUT = I/'closedloop_recorded2250_lever450_trace10681_rmprog83_after43'
load = lambda p: json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert not (D/'assessment.json').exists(), 'Preserve previous assessment'
    protocol = load(D/'protocol.json')
    for p, h in protocol['source_pins'].items(): assert sha(Path(p)) == h, p
    assert sha(Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')) == protocol['stop_sha256']
    report = load(OUT/'summary.json')
    assert not report['native_started'] and not report['future_observation_inputs']
    assert not report['prediction_conditioned_on_executed_commands']
    assert report['optimizer_iterations'] == 0 and report['candidate_profile'] == [8,6,4]
    east = tuple(load(OUT/'meter_screen_axes.json'))
    names = ['held_actual', *(r+'_progressive' for r in east), 'all_east_progressive']
    assert tuple(report['results']) == tuple(names)
    rows = {n: load(OUT/(n+'.json')) for n in names}
    base = rows['held_actual']
    old = load(I/'closedloop_recorded2250_lever450_trace10681_rmopen66_after43/held_actual.json')
    for key in ('ttt_omega_veh_h','cost_by_stock','tracked_outside_residence_veh_h',
                'control_area','ramps','commands','physical_cell_states'):
        assert base[key] == old[key], ('baseline changed',key)
    local = load(D/'after43_local.json')
    assert len(local) == 6 and max(p['resource_max'] for p in local) < 1e-7
    cases = {}
    max_on_residual = max_off_residual = 0.
    for number, (name,row) in enumerate(rows.items()):
        assert row['executed_control_blocks'] == [0,1,2]
        assert row['validation']['all_actuator_and_step_constraints_checked']
        assert abs(sum(row['cost_by_stock'].values())-row['ttt_omega_veh_h']) < 1e-7
        assert len(local[number]['full_stock_witness']) == 4
        assert local[number]['full_stock_witness'][0] == local[0]['full_stock_witness'][0]
        targets = east if name == 'all_east_progressive' else () if name == 'held_actual' else (name.removesuffix('_progressive'),)
        for block,(bc,c) in enumerate(zip(base['commands'],row['commands'])):
            for key in ('vsl','green_times','offsets'): assert c[key] == bc[key]
            for r in base['ramps']:
                assert c['meters'][r] == (8-2*block if r in targets else bc['meters'][r])
                previous = base['commands'][0]['meters'][r] if block == 0 else row['commands'][block-1]['meters'][r]
                assert abs(c['meters'][r]-previous) <= 2
        dc = {k: row['cost_by_stock'][k]-v for k,v in base['cost_by_stock'].items()}
        east_cost,west_cost = (dc['freeway:'+r] for r in ('FW_E','FW_W'))
        ramps_cost = sum(v for k,v in dc.items() if k.startswith(('ramp:','merge_pending:')))
        delta = row['ttt_omega_veh_h']-base['ttt_omega_veh_h']
        intervals = []
        for part, bp in zip(row['executed_intervals'],base['executed_intervals']):
            for r,v in part['ramps'].items():
                max_on_residual=max(max_on_residual,abs(v['initial_stock']+v['arrival']-v['merge']-v['final_stock']))
            for r,v in part['offramps'].items():
                max_off_residual=max(max_off_residual,abs(v['initial_stock']+v['arrival']-v['drain']-v['final_stock']))
            intervals.append(dict(start_sec=part['start_sec'],end_sec=part['end_sec'],
                delta_omega=part['ttt_omega_veh_h']-bp['ttt_omega_veh_h'],
                delta_east=part['cost_by_stock']['freeway:FW_E']-bp['cost_by_stock']['freeway:FW_E'],
                ramp_changes={r:{k:v[k]-bp['ramps'][r][k] for k in v} for r,v in part['ramps'].items()},
                off_changes={r:{k:v[k]-bp['offramps'][r][k] for k in ('arrival','drain','final_stock')} for r,v in part['offramps'].items()}))
        assert abs(sum(p['delta_omega'] for p in intervals)-delta)<1e-7
        for r in base['ramps']:
            assert abs(sum(p['ramps'][r]['merge'] for p in row['executed_intervals'])-row['ramps'][r]['merge'])<1e-7
        cases[name]=dict(targets=list(targets),delta_omega_veh_h=delta,
            delta_east_veh_h=east_cost,delta_west_veh_h=west_cost,delta_ramps_veh_h=ramps_cost,
            delta_other_omega_veh_h=delta-east_cost-west_cost-ramps_cost,
            delta_tracked_outside_veh_h=row['tracked_outside_residence_veh_h']-base['tracked_outside_residence_veh_h'],
            merge_delta_by_ramp={r:v['merge']-base['ramps'][r]['merge'] for r,v in row['ramps'].items()},
            final_ramp_stock_delta={r:v['final_stock']-base['ramps'][r]['final_stock'] for r,v in row['ramps'].items()},
            intervals=intervals,material_benefit=delta < -protocol['materiality_veh_h'])
    assert max(max_on_residual,max_off_residual)<1e-7
    # The joint profile already has a native counterpart. Individual paths do
    # not. Reuse that evidence rather than treating all six as new comparisons.
    old_joint_path=I/'closedloop_recorded2250_lever450_trace10681_service66_after43/rm.json'
    old_joint=load(old_joint_path)
    joint=rows['all_east_progressive']
    for key in ('ttt_omega_veh_h','cost_by_stock','tracked_outside_residence_veh_h',
                'control_area','ramps','commands','physical_cell_states'):
        assert joint[key] == old_joint[key], ('joint replay changed',key)
    native_path=I/'seed43_fullplant_20260929/comparison.json'
    native=load(native_path)
    assert native['seed']==43
    native_joint=dict(source=str(native_path),source_sha256=sha(native_path),
        window_sec=native['native_window_sec'],
        delta_omega_veh_h=native['costs']['rm']['delta_vs_nc']['native_omega_veh_h'],
        delta_inserted_network_veh_h=native['costs']['rm']['delta_vs_nc']['native_inserted_network_veh_h'],
        delta_observed_outside_veh_h=native['costs']['rm']['delta_vs_nc']['native_outside_omega_veh_h'],
        current_model_delta_omega_veh_h=cases['all_east_progressive']['delta_omega_veh_h'],
        old_joint_commands_and_results_exact=True,matched_uninserted_cost_available=False,
        scope='Cached four-arm evidence; individual ramp interventions have no native counterpart. Not a fresh holdout.')
    result=dict(status='complete',new_exact_forecasts=6,new_native=0,optimizer=0,fit=0,
        held_exact_previous=True,all_saved_model_ledger_stocks_checked=True,
        resource_max=max(p['resource_max'] for p in local),onramp_interval_residual=max_on_residual,
        offramp_interval_residual=max_off_residual,source_pins_unchanged=True,
        forecast_compute_seconds=sum(r['wall_sec'] for r in rows.values()),cases=cases,
        material_candidates=[n for n,r in cases.items() if r['material_benefit']],
        quantity_caps_evaluated=False,native_candidate_response_evaluated=False,
        native_joint_reused=native_joint,
        joint_minus_sum_individual_omega_veh_h=cases['all_east_progressive']['delta_omega_veh_h']-sum(cases[r+'_progressive']['delta_omega_veh_h'] for r in east),
        outside_scope='Tracked model cohorts only; native uninserted cost not available for these commands',
        evidence_pins={str(p):sha(p) for p in (OUT/'summary.json',OUT/'meter_screen_axes.json',D/'after43_local.json',*(OUT/(n+'.json') for n in names))})
    (D/'assessment.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(status='complete',material=result['material_candidates'],compute_seconds=result['forecast_compute_seconds'],
        cases={n:{k:r[k] for k in ('delta_omega_veh_h','delta_east_veh_h','delta_ramps_veh_h','merge_delta_by_ramp')} for n,r in cases.items()})))


if __name__=='__main__': main()
