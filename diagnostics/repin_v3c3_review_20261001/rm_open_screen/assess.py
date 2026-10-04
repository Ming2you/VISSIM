"""Assess the five finite RM responses; no model calls or native data scans."""
import hashlib
import json
from pathlib import Path

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
I = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'
OUT = I / 'closedloop_recorded2250_lever450_trace10681_rmopen66_after43'
def load(p): return json.loads(p.read_bytes())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, data): p.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')

def main():
    assert not (D/'assessment.json').exists()
    protocol = load(D/'protocol.json')
    for p,h in protocol['source_pins'].items(): assert sha(Path(p)) == h, p
    summary = load(OUT/'summary.json')
    assert not summary['future_observation_inputs'] and not summary['native_started']
    assert summary['optimizer_iterations'] == 0
    assert not summary['prediction_conditioned_on_executed_commands']
    axes = load(OUT/'meter_screen_axes.json')
    names = ['held_actual', *(r+'_first8' for r in axes)]
    assert set(names) == set(summary['results']) and len(names) == 5
    rows = {name: load(OUT/(name+'.json')) for name in names}
    base = rows['held_actual']
    old = load(I/'closedloop_recorded2250_lever450_trace10681_service66_after43/held_actual.json')
    parity = ('ttt_omega_veh_h','cost_by_stock','tracked_outside_residence_veh_h',
              'control_area','ramps','commands','physical_cell_states')
    for key in parity: assert base[key] == old[key], key
    results = {}
    east = tuple(axes)
    all_ramps = tuple(base['ramps'])
    for name,row in rows.items():
        assert row['executed_control_blocks'] == [0,1,2]
        assert row['validation']['all_actuator_and_step_constraints_checked']
        assert abs(sum(row['cost_by_stock'].values())-row['ttt_omega_veh_h']) < 1e-7
        assert max(abs(r['residual']) for r in row['ramps'].values()) < 1e-7
        changed = name.removesuffix('_first8') if name != 'held_actual' else None
        for block,(oldc,c) in enumerate(zip(base['commands'],row['commands'])):
            for key in ('vsl','green_times','offsets'): assert c[key] == oldc[key], (name,block,key)
            for r in all_ramps:
                expected = 8 if r == changed and block == 0 else oldc['meters'][r]
                assert c['meters'][r] == expected, (name,block,r,c['meters'][r])
        dc = {k: row['cost_by_stock'][k]-v for k,v in base['cost_by_stock'].items()}
        ramp_cost = sum(v for k,v in dc.items() if k.startswith(('ramp:','merge_pending:')))
        fw = {r: dc.get('freeway:'+r,0.) for r in ('FW_E','FW_W')}
        delta = row['ttt_omega_veh_h']-base['ttt_omega_veh_h']
        results[name] = dict(delta_omega_veh_h=delta,delta_east_veh_h=fw['FW_E'],
            delta_west_veh_h=fw['FW_W'],delta_ramps_veh_h=ramp_cost,
            delta_other_omega_veh_h=delta-sum(fw.values())-ramp_cost,
            delta_outside_tracked_veh_h=row['tracked_outside_residence_veh_h']-base['tracked_outside_residence_veh_h'],
            delta_merge_by_ramp={r:row['ramps'][r]['merge']-base['ramps'][r]['merge'] for r in all_ramps},
            delta_final_ramp_stock={r:row['ramps'][r]['final_stock']-base['ramps'][r]['final_stock'] for r in all_ramps},
            material_omega_benefit=delta < -protocol['materiality_veh_h'])
    local = load(D/'after43_local.json')
    assert len(local)==5 and max(r['resource_max'] for r in local)<1e-7
    result = dict(status='complete',cases=results,held_exact_previous=True,
        first_block_sec=150,horizon_sec=450,profile=[8,10,10],fixed_city_and_vsl=True,
        model='current retained U7/service66, exact actuator timing',
        native_response_for_these_candidates=False,shared_NP_NUF_caps_not_evaluated=True,
        stock_scope='All ramp balances and Omega residence partition; not full network trajectory witness',
        physical_resource_max=max(r['resource_max'] for r in local),
        max_ramp_mass_residual=max(abs(r['residual']) for x in rows.values() for r in x['ramps'].values()),
        forecast_compute_seconds=sum(x['wall_sec'] for x in rows.values()),
        source_pins_unchanged=True,actual_g8_probe_implemented_but_disabled_in_current_run=True,
        no_material_missed_benefit_in_these_four=not any(x['material_omega_benefit'] for x in results.values()),
        evidence_pins={str(p):sha(p) for p in (OUT/'summary.json', OUT/'meter_screen_axes.json', D/'after43_local.json', *(OUT/(n+'.json') for n in names))})
    save(D/'assessment.json',result)
    print(json.dumps(dict(status=result['status'],compute_seconds=result['forecast_compute_seconds'],
        delta_omega={n:r['delta_omega_veh_h'] for n,r in results.items()},
        delta_merge={n:r['delta_merge_by_ramp'].get(n.removesuffix('_first8'),0.) for n,r in results.items()})))

if __name__ == '__main__': main()
