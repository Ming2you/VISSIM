"""Existing lane physics at matched2550 states, initialized only from past FZP."""
from pathlib import Path
from collections import defaultdict
import copy
import hashlib
import json
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import matched_resolution_response as r
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import marginal_boundary_timing as scanner
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.lane_group_response_20260919 import extract as lanes

K, e, m = r.K, r.e, r.m
OUT = K / 'matched_lane_response_v1'
SPLIT = set(range(5, 21))


def observe(path, data):
    """Use the existing geometry/group convention; end the scan at the cutoff."""
    profile = lanes.geometry_profile(data.geometry, SPLIT)
    observer = lanes.Observer(data.geometry)
    exposures, exchanges = defaultdict(float), defaultdict(float)
    previous = {}
    stamp = path.stat()
    start, end = scanner.START, scanner.END
    scanner.START, scanner.END = m.START-150, m.START
    count = 0
    try:
        for t, frame in scanner.frames(path, {c['link'] for c in data.geometry['chains']['FW_E']}):
            moments = defaultdict(lambda: [0., 0.])
            located = {}
            for vid, row in frame.items():
                loc = observer.locate((row['link'], row['lane'], row['pos'], row['speed']))
                if loc is None:
                    continue
                assert loc[0] == 'FW_E'
                cell, group = loc[1], lanes.group(loc[1], row['lane'], SPLIT)
                located[vid] = (row['link'], cell, group)
                moments[cell, group][0] += 1
                moments[cell, group][1] += row['speed']
                if t > m.START-150:
                    exposures[cell, group] += 1
                    before = previous.get(vid)
                    if before and before[:2] == (row['link'], cell) and before[2] != group:
                        exchanges[cell, before[2], group] += 1
            previous = located
            count += 1
    finally:
        scanner.START, scanner.END = start, end
    assert count == 151 and t == m.START
    assert (stamp.st_size, stamp.st_mtime_ns) == (path.stat().st_size, path.stat().st_mtime_ns)
    initial, rates = [], []
    for cell, widths in enumerate(profile['widths']):
        groups = []
        for g in range(len(widths)):
            n, total = moments[cell, g]
            groups.append(dict(n_veh=n, v_kmh=total/n if n else None))
        actual = next(v for v in data.cells[m.START] if v['road'] == 'FW_E' and v['cell'] == cell)
        assert sum(v['n_veh'] for v in groups) == actual['n_veh']
        if actual['n_veh']:
            assert abs(sum(moments[cell, g][1] for g in range(len(widths)))/actual['n_veh']-actual['v_kmh']) < 1e-8
        initial.append(groups)
        rates.append([[exchanges[cell, g, h]/exposures[cell, g] if exposures[cell, g] else 0.
                       for h in range(len(widths))] for g in range(len(widths))])
    return dict(**profile, initial_groups=initial, exchange_rates_per_sec=rates,
                observation_end_s=m.START, history_start_s=m.START-150), dict(
                    path=path.relative_to(e.ROOT).as_posix(), bytes=stamp.st_size,
                    mtime_ns=stamp.st_mtime_ns, frames_read=151, last_state_s=m.START,
                    note='No future rows parsed into observations; lane changes across link/cell boundaries excluded.')


def main():
    OUT.mkdir(exist_ok=False)
    begun = time.perf_counter()
    base = e.load(r.OUT / 'config_step1.json')
    variants = {'lane': False, 'lane_momentum': True, 'lane_momentum_off': True}
    configs = {}
    for name, momentum in variants.items():
        config = copy.deepcopy(base)
        config['freeway'].update(physical_mainline_lane_groups=True,
                                 physical_lane_momentum_advection=momentum)
        if name.endswith('_off'):
            config['freeway']['physical_offramp_lanes'] = {'10643': dict(entry_groups=[0, 1], history_sec=150)}
        configs[name] = OUT / (name + '.json')
        e.save(configs[name], config)
    params = e.load(m.MODEL / 'selected_parameters.json')['parameters']
    ports = e.load(m.MODEL / 'port_profile.json')
    results, receipts = {}, {}
    sources = [Path(__file__), Path(r.__file__), Path(lanes.__file__), Path(scanner.__file__),
        r.OUT / 'result.json', m.MODEL / 'selected_parameters.json', m.MODEL / 'port_profile.json',
        e.CAL / 'canonical_harness.py', K.parent / 'evaluate_response.py',
        e.ROOT / 'evaluation/controllers/physical_lane_groups.py',
        e.ROOT / 'evaluation/controllers/physical_ramp_boundary.py',
        e.ROOT / 'evaluation/controllers/vissim_stackelberg_adapter.py']
    west_exact = 0
    for seed in (23, 33):
        bank = m.BANK if seed == 23 else K.parent / 'state_response_20260919/native_s33_v1'
        arm0 = 'rm8' if seed == 23 else 'rm_ramp'
        data = m.prepare_data(bank / 'observations' / arm0)
        cut = r.cutoff_only(data)
        spec, receipts[str(seed)] = observe(bank / ('run_'+arm0) / 'vissim_eval/baseline_001.fzp', cut)
        e.save(OUT / f'initial_s{seed}.json', spec)
        sources += [data.folder / n for n in ('geometry.json', 'cells_30s.csv', 'ports_30s.csv',
            'flows_30s.csv', 'boundaries_30s.csv', 'port_cohorts_30s.json', 'port_events.csv',
            'head_crossings.csv', 'head_stock_1s.csv')]
        results[str(seed)] = {}
        print('OBSERVED', seed, 'cutoff', spec['observation_end_s'], flush=True)
        for name in variants:
            model = e.load_base_model(data.geometry, configs[name])
            cases = {}
            for arm, sequence in r.COMMANDS.items():
                command = lambda t: ({'RM_C10490': sequence[int((t-m.START)//150)]}, {})
                w = e.window(cut, model, m.START, 'history_forecast', ports, command)
                assert w == e.window(data, model, m.START, 'history_forecast', ports, command)
                w['lane_group_dynamics'] = {'FW_E': copy.deepcopy(spec)}
                pred = e.simulate(model, w, params)
                e.save(OUT / f'prediction_s{seed}_{name}_{arm}.json', pred)
                baseline = e.load(r.OUT / f'prediction_s{seed}_step1_{arm}.json')
                for field in ('cells', 'flows', 'ports', 'ramps'):
                    assert [v for v in pred[field] if v['road']=='FW_W'] == [v for v in baseline[field] if v['road']=='FW_W']
                west_exact += 1
                assert all(x['continuity_residual_max_veh'] < 1e-7 and x['negative_density_count'] == 0
                           for x in pred['diagnostics']['roads'])
                assert all(abs(x['conservation_residual_veh']) < 1e-7 for x in pred['ports']+pred['ramps'])
                if seed == 23:
                    folder = K / 'matched_meter_midpoint_v1/observations/rm6' if arm == 'rm6' else bank / 'observations' / arm
                else:
                    folder = bank / 'observations/rm_ramp' if arm == 'rm_ramp' else K / 'matched_meter_midpoint_s33_v2/observations' / arm
                score = e.score_rollout(e.ObservationData(folder), m.START, pred, 'FW_E')
                cases[arm] = dict(component=m.parts(pred), state_score=score,
                    merges={x['ramp']: x['end']['cumulative_merge_veh'] for x in pred['ramps'] if x['road']=='FW_E' and x['end_sec']==m.END},
                    terminal=sum(x['terminal_exits'] for x in pred['flows'] if x['road']=='FW_E'))
                print(json.dumps(dict(seed=seed, candidate=name, arm=arm, cost=cases[arm]['component'],
                                      invalid=score['invalid'])), flush=True)
            for arm in ('rm6', 'rm_ramp'):
                delta = {k: cases[arm]['component'][k]-cases['rm8']['component'][k] for k in ('mainline','on','off')}
                cases[arm]['delta_vs_g8'] = dict(**delta, total=sum(delta.values()))
            results[str(seed)][name] = cases
            e.save(OUT / f'result_s{seed}_{name}.json', cases)
    e.save(OUT / 'result.json', dict(qualified=False, production_adopted=False, future_inputs=False,
        fitted_parameters=0, native_runs=0, elapsed_sec=time.perf_counter()-begun,
        exact_west_cases=west_exact, initial_receipts=receipts, cases=results,
        hypotheses=['Current lane stocks/speeds and past exchange rates distinguish the two RM response states.',
                    'Conservative longitudinal speed transfer restores downstream response duration.',
                    'Observed off10643 lane storage/drainage changes the response to the downstream RM.'],
        limitations=['Three existing model options; no full urban drain coupling or observed future route labels.',
                     'Frozen past150s lane exchange is an approximation.', 'Both seeds are development; not qualification.'],
        source_pins={p.relative_to(e.ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}))


if __name__ == '__main__':
    main()
