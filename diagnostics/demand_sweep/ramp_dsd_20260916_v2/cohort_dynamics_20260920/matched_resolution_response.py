"""Compare existing integration clocks on two frozen same-state RM contrasts.

No parameter fitting, new physical model, native run, or future input. The
10-second path must reproduce the full predictions frozen before native runs.
"""
from pathlib import Path
from collections import Counter
import copy
import hashlib
import json
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import matched_meter_increment as m

e = m.e
K = Path(__file__).resolve().parent
OUT = K / 'matched_resolution_response_v1'
COMMANDS = {'rm8': [8, 8, 8], 'rm6': [6, 6, 6], 'rm_ramp': [6, 4, 4]}


def cutoff_only(data):
    cut = copy.deepcopy(data)
    for field in ('events', 'heads', 'port_events'):
        if hasattr(cut, field):
            setattr(cut, field, [r for r in getattr(cut, field) if float(r['time_s']) <= m.START])
    cut.cells = {t: r for t, r in cut.cells.items() if t <= m.START}
    cut.port_cohorts = {t: r for t, r in cut.port_cohorts.items() if float(t) <= m.START}
    for field in ('flows', 'boundaries', 'ports', 'headstocks', 'arrivals', 'departures', 'head_counts'):
        value = getattr(cut, field)
        selected = {k: v for k, v in value.items() if k[0] <= m.START}
        setattr(cut, field, Counter(selected) if isinstance(value, Counter) else selected)
    return cut


def main():
    OUT.mkdir(exist_ok=False)
    begun = time.perf_counter()
    params = e.load(m.MODEL / 'selected_parameters.json')['parameters']
    profile = e.load(m.MODEL / 'port_profile.json')
    original = e.load(m.MODEL / 'config.json')
    configs = {}
    for step in (10, 1):
        config = copy.deepcopy(original)
        if step != 10:
            config['freeway']['physical_integration_step_sec'] = step
        configs[step] = OUT / f'config_step{step}.json'
        e.save(configs[step], config)
    sources = [Path(__file__), m.MODEL / 'config.json', m.MODEL / 'selected_parameters.json',
               m.MODEL / 'port_profile.json', e.CAL / 'canonical_harness.py',
               e.CAL / 'boundary_factory.py', K.parent / 'evaluate_response.py',
               e.ROOT / 'evaluation/controllers/physical_ramp_boundary.py',
               e.ROOT / 'evaluation/controllers/vissim_stackelberg_adapter.py']
    exact = matched = 0
    results = {}
    for seed in (23, 33):
        folder = (m.BANK / 'observations/rm8' if seed == 23 else
                  K.parent / 'state_response_20260919/native_s33_v1/observations/rm_ramp')
        reference = e.load(K / ('matched_meter_midpoint_v1/result_v2.json' if seed == 23
                               else 'matched_meter_midpoint_s33_v2/result.json'))
        data = m.prepare_data(folder)
        cut = cutoff_only(data)
        sources += [folder / name for name in ('geometry.json', 'cells_30s.csv', 'ports_30s.csv',
                     'flows_30s.csv', 'boundaries_30s.csv', 'port_cohorts_30s.json', 'port_events.csv',
                     'head_crossings.csv', 'head_stock_1s.csv')]
        cases = {}
        coarse_windows = {}
        for step in (10, 1):
            model = e.load_base_model(data.geometry, configs[step])
            cases[str(step)] = {}
            for arm, sequence in COMMANDS.items():
                command = lambda t: ({'RM_C10490': sequence[int((t-m.START)//150)]}, {})
                window = e.window(cut, model, m.START, 'history_forecast', profile, command)
                assert window == e.window(data, model, m.START, 'history_forecast', profile, command)
                if step == 10:
                    coarse_windows[arm] = copy.deepcopy(window)
                else:
                    coarse = coarse_windows[arm]
                    for key in ('initial_cells', 'initial_origin_queue', 'port_dynamics', 'ramp_dynamics', 'vsl_zone_heads'):
                        assert window[key] == coarse[key], key
                    for i, parent in enumerate(coarse['boundary_steps']):
                        children = window['boundary_steps'][10*i:10*i+10]
                        assert len(children) == 10
                        for child in children:
                            for key, value in parent.items():
                                if key not in ('window_start_s', 'window_end_s'):
                                    assert child[key] == value, key
                            matched += 1
                        for ramp, rate in parent['ramp_arrival_vph'].items():
                            assert abs(sum(c['ramp_arrival_vph'][ramp]/3600 for c in children)-rate*10/3600) < 1e-8
                prediction = e.simulate(model, window, params)
                assert prediction['local_ramp_audit']['passed']
                assert all(r['continuity_residual_max_veh'] < 1e-7 for r in prediction['diagnostics']['roads'])
                if step == 10:
                    if seed == 33:
                        prior_path = K / 'matched_meter_midpoint_s33_v2' / f'prediction_{arm}.json'
                        window_path = K / 'matched_meter_midpoint_s33_v2' / f'window_{arm}.json'
                        assert window == e.load(window_path)
                    elif arm == 'rm6':
                        prior_path = K / 'matched_meter_midpoint_v1/prediction_rm6.json'
                        assert window == e.load(K / 'matched_meter_midpoint_v1/forecast_window.json')
                    else:
                        prior_path = K / 'matched_meter2550_v1' / f'prediction_{arm}.json'
                    assert json.loads(json.dumps(prediction)) == e.load(prior_path), (seed, arm)
                    sources.append(prior_path)
                    exact += 1
                component = m.parts(prediction)
                merges = {r['ramp']: r['end']['cumulative_merge_veh'] for r in prediction['ramps']
                          if r['road'] == 'FW_E' and r['end_sec'] == m.END}
                terminal = sum(r['terminal_exits'] for r in prediction['flows'] if r['road'] == 'FW_E')
                cases[str(step)][arm] = dict(component=component, merges=merges, terminal=terminal,
                    continuity_max=max(r['continuity_residual_max_veh'] for r in prediction['diagnostics']['roads']))
                e.save(OUT / f'window_s{seed}_step{step}_{arm}.json', window)
                e.save(OUT / f'prediction_s{seed}_step{step}_{arm}.json', prediction)
                print(json.dumps(dict(seed=seed, step=step, arm=arm, cost=component)), flush=True)
            for arm in ('rm6', 'rm_ramp'):
                delta = {k: cases[str(step)][arm]['component'][k] - cases[str(step)]['rm8']['component'][k]
                         for k in ('mainline', 'on', 'off')}
                cases[str(step)][arm]['delta_vs_g8'] = dict(**delta, total=sum(delta.values()))
        results[str(seed)] = dict(predicted=cases, actual=reference['actual'], actual_deltas=reference['actual_deltas_vs_g8'])
        e.save(OUT / f'result_s{seed}.json', results[str(seed)])
    e.save(OUT / 'result.json', dict(qualified=False, future_inputs=False, fitted_parameters=0,
        native_runs=0, full_default_predictions_exact=exact, fine_command_intervals_matched=matched,
        cases=results, elapsed_sec=time.perf_counter()-begun,
        scope='FW_E mainline/four on/four off; not Omega; g8 baseline is metered,not NC',
        change='Only existing numerical integration flag10s->1s; unchanged physical coefficients and boundary requests.',
        source_pins={p.relative_to(e.ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}))


if __name__ == '__main__':
    main()
