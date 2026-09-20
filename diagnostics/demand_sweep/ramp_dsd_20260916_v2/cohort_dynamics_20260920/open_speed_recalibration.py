"""Bounded NC-only speed fit, followed by causal open-outlet450s rejection gates.

Uses existing state-response hooks and the existing component transition.
Recorded next speeds/accepted merges are training labels/exposures only. Every
rollout uses pre-cutoff observations and predicts all future states and flows.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e, H, MODEL, CASES, ARMS
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.fit_local_speed import records, NAMES, stats
import numpy as np
import copy
import hashlib
import itertools
import time
import json
import argparse

HERE = Path(__file__).resolve().parent
LANE = H/'lane_group_response_20260919'


def fields(rows, p):
    a = {k: np.asarray([r[k] for r in rows], dtype=float) for k in rows[0]}
    desired = a['vfree']*p['v_free_multiplier']*np.exp(-((a['rho']/(a['critical']*p['rho_crit_multiplier']))**a['a'])/a['a'])
    desired = np.minimum(desired, a['cap'])
    convection = 10/3600/a['length']*a['v']*(a['up']-a['v'])
    merge = -p['delta_merge']*a['merge_veh']*a['v']/(a['length']*a['width']*(a['rho']+p['kappa_veh_km_lane']))
    return a, desired-a['v'], -(a['down']-a['rho'])/(a['length']*(a['rho']+p['kappa_veh_km_lane'])), convection+merge


def prediction(rows, p, spec):
    a, relaxation, gradient, transport = fields(rows, p)
    tau = np.where(relaxation >= 0, spec['relaxation']['acceleration_sec'], spec['relaxation']['deceleration_sec'])
    nu = np.where(a['down'] >= a['rho'], spec['anticipation']['downstream_ge_local'], spec['anticipation']['downstream_lt_local'])
    return np.maximum(a['v_min'], a['v']+transport+10/tau*(relaxation+nu*gradient))


def score(rows, p, spec):
    predicted = prediction(rows, p, spec)
    target = np.array([r['target'] for r in rows])
    current = np.array([r['v'] for r in rows])
    return dict(samples=len(rows), rmse=float(np.sqrt(np.mean((predicted-target)**2))),
                bias=float(np.mean(predicted-target)), persistence_rmse=float(np.sqrt(np.mean((current-target)**2))))


def fit(rows, p, split):
    a, relaxation, gradient, transport = fields(rows, p)
    trials = []
    grid = [12., 18., 24., 40., 60.]
    pairs = itertools.product(grid, grid) if split else ((t, t) for t in grid)
    for acc, dec in pairs:
        tau = np.where(relaxation >= 0, acc, dec)
        x = 10/tau*gradient
        y = a['target']-a['v']-transport-10/tau*relaxation
        groups = [a['down'] >= a['rho'], a['down'] < a['rho']] if split else [np.ones(len(rows), dtype=bool)]
        nus = []
        for mask in groups:
            denominator = float(np.dot(x[mask], x[mask]))
            assert denominator > 0
            nus.append(float(np.clip(np.dot(x[mask], y[mask])/denominator, 3., 90.)))
        spec = dict(relaxation=dict(acceleration_sec=acc, deceleration_sec=dec),
                    anticipation=dict(downstream_ge_local=nus[0], downstream_lt_local=nus[-1]))
        trials.append(dict(spec=spec, score=score(rows, p, spec)))
    return min(trials, key=lambda r: r['score']['rmse']), trials


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=HERE/'open_speed_fit_v2')
    out = parser.parse_args().output.resolve()
    out.mkdir(exist_ok=False)
    begun = time.perf_counter()
    config_path = HERE/'port_origin_split_v1/config.json'
    params_path = HERE/'port_travel_fit_v1/selected_parameters.json'
    params = e.load(params_path)['parameters']
    p = params['by_direction']['FW_E']
    source_pins = {str(f.relative_to(e.ROOT)): hashlib.sha256(f.read_bytes()).hexdigest() for f in
                  [Path(__file__), HERE/'fit_local_speed.py', config_path, params_path,
                   e.CAL/'canonical_harness.py', H/'evaluate_response.py',
                   e.ROOT/'evaluation/controllers/physical_lane_groups.py',
                   e.ROOT/'evaluation/controllers/freeway_fd.py',
                   e.ROOT/'evaluation/controllers/vissim_stackelberg_adapter.py']}
    banks = {seed: records(seed, 'none', include_downstream=True) for seed in (23, 33)}
    train = [r for r in banks[23] if r['time_s'] < 2400]
    reference_spec = dict(relaxation=dict(acceleration_sec=p['tau_sec'], deceleration_sec=p['tau_sec']),
                          anticipation=dict(downstream_ge_local=p['nu_km2_h'], downstream_lt_local=p['nu_km2_h']))
    fitted = {}
    for name, split in [('single', False), ('regime', True)]:
        selected, trials = fit(train, p, split)
        fitted[name] = selected
        e.save(out/f'fit_{name}.json', dict(selected=selected, trials=trials,
            validation={f'{seed}_{region}': score([r for r in bank if (seed!=23 or r['time_s']>=2400) and
                (r['cell']>=15 if region=='downstream' else r['cell']<15)], p, selected['spec'])
                for seed, bank in banks.items() for region in ('upstream', 'downstream')}))
        print('FIT', name, selected, flush=True)
    # Baseline calculation agreement at default diagnostic sampling scope.
    default_rows = [r for r in train if r['cell'] < 15]
    old = stats(default_rows, [p[k] for k in NAMES])
    assert abs(old['rmse']-score(default_rows, p, reference_spec)['rmse']) < 1e-10
    protocol = dict(training='Seed23 NC900..2390, cells5..20; next10s speed and observed merges are training targets/exposures only',
        selection='5 scalar and25 asymmetric tau pairs; analytic bounded nu per branch, selected on training speed RMSE only',
        guards='12 NC450s states, <=1.10 times established internal_cost state objective; also report previous failed candidate comparator',
        held_out='Seed33 is previously inspected development data, not an unused holdout',
        open_outlet='Diagnostic instance FW_E terminal_zero_gradient=True; source/internal limits unchanged',
        future_rollout_inputs=False, new_native_runs=0, capacity_bonus=False, source_pins=source_pins,
        baseline_local_score=score(train, p, reference_spec), candidate_specs={k:v['spec'] for k,v in fitted.items()})
    e.save(out/'protocol.json', protocol)
    base_config = e.load(config_path)
    paths = {'open_reference':config_path}
    for name, row in fitted.items():
        cfg = copy.deepcopy(base_config)
        cfg['freeway']['state_response'] = {'FW_E':row['spec']}
        path = out/f'{name}_config.json'
        e.save(path, cfg)
        paths[name] = path
    profile = e.load(MODEL/'port_profile.json')
    base_params = e.load(MODEL/'selected_parameters.json')['parameters']
    actual = e.load(H/'merge_drain_response_20260919/native_audit_v1/result.json')
    # Correct the known whole-link/located difference where exact same-scope
    # component identities are available; label the remaining historical arms.
    located = e.load(HERE/'terminal_response_validation_v1.json')['comparisons']
    for row in located:
        if row['treatment'] in ARMS:
            actual[str(row['seed'])]['delta_1s'][row['treatment']]['FW_E'] = row['actual_1s']
    result = {}; baseline_guards = {}
    for seed, folder, bank, start in CASES:
        data = e.ObservationData(folder)
        lane = e.load(LANE/f'observations_v1/s{seed}.json')
        origin = e.load(HERE/f'port_positions_v1/s{seed}.json')
        command_bank = e.load(bank/'protocol.json')
        def window(model, cutoff, command):
            w = e.window(data, model, cutoff, 'history_forecast', profile, command, port_origin_counts=origin['counts'])
            if model.lane_groups_enabled:
                w['lane_group_dynamics'] = {'FW_E':{**lane['geometry'], **lane['cutoffs'][str(cutoff)],
                    'initial_ramp_origin':origin['counts'][str(cutoff)],
                    'initial_off_eligible':origin['eligible_before_off'][str(cutoff)]}}
            return w
        base = e.load_base_model(data.geometry, MODEL/'config.json')
        baseline_guards[str(seed)] = {}
        for cutoff in [900,1650,2400,3600]:
            pred = e.simulate(base, window(base, cutoff, lambda _: ({},{})), base_params)
            baseline_guards[str(seed)][str(cutoff)] = e.score_rollout(data, cutoff, pred, 'FW_E')
        result[str(seed)] = {}
        for label, path in paths.items():
            model = e.load_base_model(data.geometry, path)
            original_config = model._config
            def configured(road, override):
                cfg = original_config(road, override)
                if road == 'FW_E':cfg.network.terminal_zero_gradient = True
                return cfg
            model._config = configured
            guards = {}; forecasts = {}
            for cutoff in [900,1650,2400,3600]:
                pred = e.simulate(model, window(model, cutoff, lambda _: ({},{})), params)
                s = e.score_rollout(data, cutoff, pred, 'FW_E')
                assert not s['invalid']
                guards[str(cutoff)] = dict(score=s, vs_default_ratio=s['objective']/baseline_guards[str(seed)][str(cutoff)]['objective'])
            for arm in ARMS:
                seq = command_bank['candidate_bank'].get(arm, {'green':[], 'vsl':[]})
                def commands(t):
                    i = int((t-start)//150)
                    return ({'RM_C10490':seq['green'][i]} if seq['green'] else {},
                        {d:seq['vsl'][i] for d in command_bank.get('dsd_ids',[59,60,61,62])} if seq['vsl'] else {})
                pred = e.simulate(model, window(model, start, commands), params)
                forecasts[arm] = parts(pred)
                previous = e.load(HERE/f'terminal_probe_v1/prediction_s{seed}_open_outlet_{arm}.json')
                for key in ['cells', 'flows']:
                    assert [r for r in pred[key] if r['road']=='FW_W'] == [r for r in previous[key] if r['road']=='FW_W']
                if label == 'open_reference':assert json.loads(json.dumps(pred)) == previous
                else:e.save(out/f'prediction_{seed}_{label}_{arm}.json', pred)
                for row in pred['diagnostics']['roads']:
                    assert row['continuity_residual_max_veh'] < 1e-7 and row['negative_density_count'] == row['jam_density_exceedance_count'] == 0
            deltas = {arm:{k:v-forecasts['none'][k] for k,v in forecasts[arm].items()} for arm in ARMS[1:]}
            for row in deltas.values():row['total'] = sum(row.values())
            result[str(seed)][label] = dict(guards=guards, parts=forecasts, deltas=deltas,
                actual={arm:actual[str(seed)]['delta_1s'][arm]['FW_E'] for arm in ARMS[1:]},
                state_guards_passed=sum(r['vs_default_ratio']<=1.1 for r in guards.values()))
            print('ROLLOUT', seed, label, 'guards', result[str(seed)][label]['state_guards_passed'],
                  {arm:round(r['total'],6) for arm,r in deltas.items()}, flush=True)
        e.save(out/f'result_s{seed}.json', result[str(seed)])
    for name, pin in source_pins.items():assert hashlib.sha256((e.ROOT/name).read_bytes()).hexdigest() == pin
    e.save(out/'results.json', dict(results=result, baseline_state_scores=baseline_guards,
        source_pins_unchanged=True, default_open_outlet_predictions_exact=12,
        scope='Causal development trial, no independent-seed qualification; native mainline timing convention note in protocol',
        promoted=False, elapsed_s=time.perf_counter()-begun))


if __name__ == '__main__':
    main()
