"""Locate gain-response error with explicit diagnostic-only future substitutions."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.ramp_response_20260919.verify import CASES
import copy
import json
import hashlib
from collections import Counter

HERE = Path(__file__).resolve().parent
H = HERE.parent
MODEL = H/'merge_drain_response_20260919/decisions_v1/internal_cost'
ARMS = ['none', 'rm_ramp', 'vsl', 'both']


def main():
    out = HERE/'isolation_v2'
    out.mkdir(exist_ok=False)
    actual = e.load(H/'merge_drain_response_20260919/native_audit_v1/result.json')
    params = e.load(MODEL/'selected_parameters.json')['parameters']
    profile = e.load(MODEL/'port_profile.json')
    results = {}
    for seed, folder, bank, start in CASES:
        nc = e.ObservationData(folder)
        model = e.load_base_model(nc.geometry, MODEL/'config.json')
        protocol = e.load(bank/'protocol.json')
        result = {mode: {} for mode in ['causal', 'actual_merges', 'actual_boundaries']}
        for arm in ARMS:
            data = nc if arm == 'none' else e.ObservationData(bank/'observations'/arm)
            assert data.cells[start] == nc.cells[start], (seed, arm, 'initial freeway states')
            assert data.port_cohorts[str(start)] == nc.port_cohorts[str(start)]
            seq = protocol['candidate_bank'].get(arm, {'green': [], 'vsl': []})
            def commands(t):
                i = int((t-start)//150)
                return ({'RM_C10490': seq['green'][i]} if seq['green'] else {},
                        {d: seq['vsl'][i] for d in protocol.get('dsd_ids', [59,60,61,62])} if seq['vsl'] else {})
            departures = Counter((int(float(r['time_s'])), r['connector'])
                                 for r in e.rows(data.folder/'port_events.csv') if r['kind'] == 'departure')
            for mode in result:
                w = e.window(nc if mode != 'actual_boundaries' else data, model, start,
                             'conditioned_diagnostic' if mode == 'actual_boundaries' else 'history_forecast',
                             profile, commands)
                if mode == 'causal':
                    pred = e.simulate(model, w, params)
                else:
                    for step in w['boundary_steps']:
                        for mid, ramp in model.ramps.items():
                            c = str(ramp['connector'])
                            step['ramp_release_vph'][mid] = sum(departures[t,c] for t in
                                range(step['window_start_s']+1, step['window_end_s']+1))*360.
                    nodes = model.ramp_receiving_nodes
                    model.ramp_receiving_nodes = {}  # Already accepted measured flow bypasses its predictor.
                    try:
                        pred = model.rollout(w['initial_cells'], w['boundary_steps'], params, w['initial_origin_queue'],
                            port_dynamics=w['port_dynamics'], vsl_zone_heads=w['vsl_zone_heads'], residence_audit=True)
                    finally:
                        model.ramp_receiving_nodes = nodes
                result[mode][arm] = {'mainline': {r['road']: r['model_residence_10s_veh_h']
                                                for r in pred['diagnostics']['roads']},
                                     'score': e.score_rollout(data, start, pred, 'FW_E'),
                                     'vsl_binding': next(r['vsl_binding_audit'] for r in pred['diagnostics']['roads'] if r['road']=='FW_E')}
                e.save(out/f'prediction_{seed}_{mode}_{arm}.json', pred)
        result['delta'] = {arm: {'actual': actual[str(seed)]['delta_1s'][arm]['FW_E']['mainline'],
            **{mode: result[mode][arm]['mainline']['FW_E']-result[mode]['none']['mainline']['FW_E']
               for mode in ['causal','actual_merges','actual_boundaries']}} for arm in ARMS[1:]}
        results[str(seed)] = result
        print(seed, result['delta'], flush=True)
    e.save(out/'results.json', results)
    e.save(out/'protocol.json', {
        'causal': 'Existing internal_cost model, all future states predicted',
        'actual_merges': 'Diagnostic only: each arm actual accepted ramp merge counts in10s; all other boundaries causal',
        'actual_boundaries': 'Diagnostic only: additionally actual future source, split and drainage proxies',
        'purpose': 'Separate actuator/merge prediction from freeway propagation and other boundary prediction. Only mainline response compared in these substitutions.',
        'fit': 'No parameter fitting, no altered objective, no native runs',
        'initial_states_equal': True,
        'pins': {str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in [MODEL/'config.json', MODEL/'selected_parameters.json', e.CAL/'canonical_harness.py', H/'evaluate_response.py']}})


if __name__ == '__main__':
    main()
