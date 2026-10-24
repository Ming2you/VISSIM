"""Future-arrival diagnostic only: isolate10484 arrival timing from its law.

No native run, parameter fit, inventory reset or deployable prediction claim.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.direct10484_probe import (
    e, H, MODEL, HERE, OUT, NC, START, END, check_pins, sha)
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.rm_attribution import model_ports
from collections import Counter


def main():
    check_pins(); out = OUT/'arrival_diagnostic'; out.mkdir(exist_ok=False)
    data = e.ObservationData(NC)
    origins = e.load(HERE/'port_positions_v1/s23.json')
    lane = e.load(H/'lane_group_response_20260919/observations_v1/s23.json')
    config = HERE/'port_origin_split_v1/config.json'
    params = e.load(HERE/'port_travel_fit_v1/selected_parameters.json')['parameters']
    port_profile = e.load(MODEL/'port_profile.json')
    folders = {'none':NC, 'rm10484':OUT/'observations/rm10484'}
    counts = {a:Counter(int(float(r['time_s'])) for r in e.rows(p/'port_events.csv')
                         if r['connector']=='10484' and r['kind']=='arrival') for a,p in folders.items()}
    files = [Path(__file__)]+[p/'port_events.csv' for p in folders.values()]
    pins = {str(p.relative_to(e.ROOT)):sha(p) for p in files}
    results = {}
    for mode in ['history', 'paired_future_arrivals', 'same_nc_future_arrivals']:
        rows = {}
        for arm in ['none','rm10484']:
            model = e.load_base_model(data.geometry, config); original = model._config
            def configured(road, override):
                cfg = original(road, override)
                if road == 'FW_E': cfg.network.terminal_zero_gradient = True
                return cfg
            model._config = configured
            def commands(t):
                return ({'RM_C10484':[8,6,4][int((t-START)//150)]} if arm=='rm10484' else {}, {})
            w = e.window(data, model, START, 'history_forecast', port_profile, commands,
                         port_origin_counts=origins['counts'])
            w['lane_group_dynamics'] = {'FW_E':{**lane['geometry'], **lane['cutoffs'][str(START)],
                'initial_ramp_origin':origins['counts'][str(START)],
                'initial_off_eligible':origins['eligible_before_off'][str(START)]}}
            if mode != 'history':
                arrivals = counts[arm if mode=='paired_future_arrivals' else 'none']
                for step in w['boundary_steps']:
                    start, end = int(step['window_start_s']), int(step['window_end_s'])
                    profile = [arrivals[t] for t in range(start+1,end+1)]
                    step['ramp_arrival_profile'] = {'RM_C10484':profile}
                    step['ramp_arrival_vph']['RM_C10484'] = sum(profile)*3600/(end-start)
            pred = e.simulate(model, w, params)
            reference = e.load(OUT/f'prediction_open_candidate_{arm}.json')
            for key in ['cells','flows']:
                assert [r for r in pred[key] if r['road']=='FW_W']==[r for r in reference[key] if r['road']=='FW_W']
            if mode=='history':
                import json
                assert json.loads(json.dumps(pred)) == reference
            for r in pred['diagnostics']['roads']:
                assert r['continuity_residual_max_veh']<1e-7 and r['negative_density_count']==r['jam_density_exceedance_count']==0
            e.save(out/f'{mode}_{arm}.json', pred)
            rows[arm] = dict(parts=parts(pred), ports=model_ports(pred))
        delta = {k:rows['rm10484']['parts'][k]-rows['none']['parts'][k] for k in rows['none']['parts']}
        delta['total'] = sum(delta.values())
        results[mode] = dict(arms=rows,delta=delta)
        print(mode,delta,flush=True)
    check_pins()
    for p,h in pins.items(): assert sha(e.ROOT/p)==h
    e.save(out/'results.json',dict(results=results, source_pins=pins,
        status='ORACLE_DIAGNOSTIC_NOT_CAUSAL_OR_QUALIFIED', fitted_parameters=0,
        future_inputs='10484 connector arrivals by second only; same initial states, other causal boundaries and physical laws.',
        controls='Paired future inputs include one fewer actual arrival; same_nc_future_arrivals removes that external change.',
        exact_history_replays=2, conservation_passed=True))


if __name__=='__main__':main()
