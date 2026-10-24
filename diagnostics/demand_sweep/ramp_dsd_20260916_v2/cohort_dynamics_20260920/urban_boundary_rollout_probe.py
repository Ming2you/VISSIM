"""Test a frozen current-state receiving forecast in the existing plant.

This is a bounded causal boundary diagnostic, not a coupled urban model or
an adopted controller option. No future urban observations reset the plant.
"""
from pathlib import Path
import sys
import json
import hashlib
import argparse
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e, H, MODEL, CASES, ARMS
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.urban_receiving_probe import dataset, features
from evaluation.controllers.physical_lane_groups import PhysicalLaneGroups


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--lane-resolved', action='store_true')
    parser.add_argument('--initial-intent-oracle', action='store_true')
    args = parser.parse_args()
    assert not (args.lane_resolved and args.initial_intent_oracle)
    folder = ('initial_intent_rollout_oracle_v1' if args.initial_intent_oracle else
              'urban_boundary_rollout_lanes_v1' if args.lane_resolved else 'urban_boundary_rollout_v1')
    out = HERE/folder
    out.mkdir(exist_ok=False)
    calibration = HERE/'urban_receiving_lag_probe_v1/result.json'
    selected = next(m for m in e.load(calibration)['models'] if m['name'] == 'history_signal_state')
    coef = np.array(selected['coefficients_by_lane'])
    lag = selected['signal_lag_s']
    config = HERE/'port_origin_split_v1/config.json'
    lane_config = out/'lane_config.json'
    if args.lane_resolved or args.initial_intent_oracle:
        candidate = e.load(config)
        candidate['freeway']['physical_offramp_lanes'] = {'10643': {'entry_groups': [0,1], 'history_sec': 150}}
        e.save(lane_config, candidate)
    params_file = HERE/'port_travel_fit_v1/selected_parameters.json'
    params = e.load(params_file)['parameters']
    profile = e.load(MODEL/'port_profile.json')
    files = [Path(__file__), calibration, config, params_file, MODEL/'port_profile.json',
             e.CAL/'canonical_harness.py', H/'evaluate_response.py',
             e.ROOT/'evaluation/controllers/physical_lane_groups.py']
    if args.lane_resolved or args.initial_intent_oracle:
        files.append(lane_config)
    if args.initial_intent_oracle:
        files.extend(HERE/f'initial_exit_intent_audit_v1/s{s}.json' for s in (23,33))
    pins = {str(p.relative_to(e.ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    results = {}
    for seed, folder, bank, start in CASES:
        if seed not in (23, 33):
            continue
        assert start == 2400
        data = e.ObservationData(folder)
        lane = e.load(H/'lane_group_response_20260919'/f'observations_v1/s{seed}.json')
        origins = e.load(HERE/f'port_positions_v1/s{seed}.json')
        protocol = e.load(bank/'protocol.json')
        urban = HERE/'urban_drain_observations_v5'
        observed, program, offset = dataset(urban/f's{seed}_none.csv', urban/f's{seed}_none_evidence.json')
        # Delete every future traffic row before generating any boundary.
        past = {t: row for t, row in observed.items() if t <= start}
        anchor = features(past, program, offset, start, lag)
        modes = {}
        mode_names = ('reference', 'lane_history', 'lane_anchor') if args.lane_resolved else ('reference', 'current_state_anchor')
        if args.initial_intent_oracle:
            mode_names = ('reference', 'initial_intent_oracle', 'lane_intent_oracle')
            intent = e.load(HERE/f'initial_exit_intent_audit_v1/s{seed}.json')
            branch = [intent['groups'][f'8:{g}'] for g in range(3)]
            assert all(r['unknown_by3000'] == 0 for r in branch)
            true_counts = [r['known_off10643'] for r in branch]
        for mode in mode_names:
            model = e.load_base_model(data.geometry, lane_config if mode.startswith('lane_') else config)
            modes[mode] = {}
            for arm in ARMS:
                seq = protocol['candidate_bank'].get(arm, {'green': [], 'vsl': []})
                def commands(t):
                    i = int((t-start)//150)
                    return ({'RM_C10490': seq['green'][i]} if seq['green'] else {},
                            {d: seq['vsl'][i] for d in protocol.get('dsd_ids', [59,60,61,62])} if seq['vsl'] else {})
                w = e.window(data, model, start, 'history_forecast', profile, commands,
                             port_origin_counts=origins['counts'])
                w['lane_group_dynamics'] = {'FW_E': {**lane['geometry'], **lane['cutoffs'][str(start)],
                    'initial_ramp_origin': origins['counts'][str(start)],
                    'initial_off_eligible': origins['eligible_before_off'][str(start)]}}
                if mode in ('current_state_anchor', 'lane_anchor'):
                    for step in w['boundary_steps']:
                        x = anchor.copy()
                        t, end = step['window_start_s'], step['window_end_s']
                        for i, sg in enumerate((2,5)):
                            x[3+i] = sum(program.state_at(s, sg, controller_offset_sec=offset) == 'GREEN'
                                         for s in range(t-lag+1, end-lag+1)) / (end-t)
                        service = np.maximum(0., x@coef)*3600
                        step['off_drain_vph']['10643'] = float(service.sum())
                        if mode == 'lane_anchor':
                            step['off_lane_drain_vph']['10643'] = service.tolist()
                original_label = PhysicalLaneGroups._label
                if args.initial_intent_oracle and mode != 'reference':
                    def initial_label(self, arrivals, ratios, eligible_by_off=None):
                        original_label(self, arrivals, ratios, eligible_by_off)
                        if not self.initialized_destinations and self.road == 'FW_E':
                            assert all(x <= y+1e-9 for x, y in zip(true_counts, eligible_by_off['10643']))
                            self.off['10643'] = list(map(float, true_counts))
                    PhysicalLaneGroups._label = initial_label
                try:
                    pred = e.simulate(model, w, params)
                finally:
                    PhysicalLaneGroups._label = original_label
                if mode == 'reference':
                    old = e.load(HERE/f'port_origin_split_qualification_v2/prediction_{seed}_{arm}.json')
                    assert json.loads(json.dumps(pred)) == old, (seed, arm, 'reference replay')
                road = next(r for r in pred['diagnostics']['roads'] if r['road'] == 'FW_E')
                assert road['continuity_residual_max_veh'] < 1e-7
                assert road['lane_group_continuity_residual_max_veh'] < 1e-7
                modes[mode][arm] = {'parts': parts(pred), 'state_score': e.score_rollout(data, start, pred, 'FW_E')}
                e.save(out/f'prediction_{seed}_{mode}_{arm}.json', pred)
            modes[mode]['deltas'] = {a: {k: v-modes[mode]['none']['parts'][k] for k,v in modes[mode][a]['parts'].items()} for a in ARMS[1:]}
            for delta in modes[mode]['deltas'].values():
                delta['total'] = sum(delta.values())
            print(seed, mode, {k: round(v['total'], 6) for k,v in modes[mode]['deltas'].items()}, flush=True)
        results[str(seed)] = modes
        e.save(out/f'result_s{seed}.json', modes)
    for path, pin in pins.items():
        assert hashlib.sha256((e.ROOT/path).read_bytes()).hexdigest() == pin
    e.save(out/'result.json', {'status': 'DIAGNOSTIC_NOT_ADOPTED', 'results': results,
        'pins': pins, 'cutoff_safe': not args.initial_intent_oracle, 'future_urban_rows_deleted_before_forecast': True,
        'initial_destination_future_path_oracle': args.initial_intent_oracle,
        'scope': 'Existing conserved component model with current71-state anchored10643 service; urban states frozen, fixed native signal only; not a coupled urban forecast.',
        'full_qualification': False, 'new_native_runs': 0})


if __name__ == '__main__':
    main()
