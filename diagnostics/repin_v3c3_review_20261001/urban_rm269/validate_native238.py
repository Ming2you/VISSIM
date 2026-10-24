"""Reuse the completed same-initial 10681 experiment; no native run or fit.

Prepare reclassifies existing per-link residence to Omega701. A run performs
only two canonical 450s discrete forecasts with the actually executed blocks.
The historical zero-green baseline is an actuator diagnostic, not a feasible
candidate under the current minimum-green policy.
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import argparse
import copy
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
R = HERE.parent
OLD = R / 'rm_restart219/native238'
PROTOCOL = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926/native_rm10681_reopen4650_238/protocol.json'
F = Path('D:/VISSIM_runs/20261005_rm219_fixed90_s29_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
DEST = HERE / 'native238_validation'
read = lambda p: json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def save(path, doc):
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')


def prepare_evidence():
    from evaluation.controllers.control_area_objective import physical_membership_from_ledger
    assert not DEST.exists(), 'Preserve an existing validation attempt'
    protocol, proof = read(PROTOCOL), read(OLD / 'analysis/summary.json')
    assert proof['protocol_sha256'] == sha(PROTOCOL)
    assert all(proof[k] is True for k in ('counterfactual_valid', 'paired_prefix_exact',
                                         'common_start_vehicle_records_exact', 'original_initial_history_exact'))
    assert all(proof['arms'][a]['native_execution_passed'] for a in ('hold', 'selected'))
    assert proof['prefixes']['hold'] == proof['prefixes']['selected'] == proof['original_prefix']
    config = read(HERE / 'config_candidate.json')
    membership_path = ROOT / config['control_area_objective']['membership_path']
    membership = read(membership_path)
    assert membership['network']['sha256'] == protocol['network_sha256']
    assert sha(ROOT / membership['network']['path']) == protocol['network_sha256']
    inside = physical_membership_from_ledger(membership)
    pins = {str(p): sha(p) for p in (PROTOCOL, OLD/'analysis/summary.json', membership_path,
                                    HERE/'config_candidate.json', Path(__file__))}
    for relative, expected in read(HERE/'selection2400_launch.json')['source_pins'].items():
        p = ROOT/relative
        assert sha(p) == expected, p
        pins[str(p)] = expected
    perlink, totals = {}, {}
    for arm in ('hold', 'selected'):
        p = OLD / 'analysis' / arm / 'area_metrics.json'
        data = read(p); pins[str(p)] = sha(p)
        assert data['boundaries']['requested_end_sec'] == 5100
        assert data['boundaries']['last_fzp_sec'] == 5095.1
        assert data['boundaries']['tail_method'] == 'hold last stock; no inferred exit'
        links = data['physical_link_residence']
        assert set(links) <= set(inside)
        assert abs(sum(r['ttt_veh_h'] for r in links.values() if r['inside']) - data['ttt_veh_h']) < 1e-7
        perlink[arm] = {k: r['ttt_veh_h'] for k, r in links.items() if inside[k]}
        totals[arm] = sum(perlink[arm].values())
    delta_links = {k: perlink['selected'].get(k, 0) - perlink['hold'].get(k, 0)
                   for k in set(perlink['hold']) | set(perlink['selected'])}
    for t in (4650, 4800, 4950):
        for folder in (OLD/'held_writer', PROTOCOL.parent/'selected/commands'):
            p = folder/f'action_{t:06}.json'
            assert sha(p) == protocol['command_pins'][str(p)]
            pins[str(p)] = sha(p)
        h, s = (read(folder/f'action_{t:06}.json') for folder in
                (OLD/'held_writer', PROTOCOL.parent/'selected/commands'))
        for key in ('N_P_star', 'N_UF_star', 'vsl', 'green_times', 'offsets', 'inflow_outflow_allocation'):
            assert h[key] == s[key], (t, key)
        assert {k for k in h['ramp_metering'] if h['ramp_metering'][k] != s['ramp_metering'][k]} == {'RM_C10681'}
    raw = read(F/'state_004650.json')
    frame_path = F/raw['obs150']['frames']['current']['path']
    assert sha(frame_path) == raw['obs150']['frames']['current']['sha256']
    frame = read(frame_path)
    assert frame['complete'] and frame['time_s'] == 4650
    assert len(frame['vehicles']) == raw['vehicle_records']['record_count']
    assert all(len(v) >= 9 for v in frame['vehicles']), 'Need captured current-route columns, not future inference'
    pins.update({str(F/'state_004650.json'): sha(F/'state_004650.json'), str(frame_path): sha(frame_path)})
    DEST.mkdir()
    baseline = copy.deepcopy(config)
    assert baseline['urban'].pop('known_wout_local_queue') is True
    save(DEST/'baseline_config.json', baseline)
    save(DEST/'candidate_config.json', config)
    save(DEST/'plan.json', dict(status='prepared', budget=dict(configurations=2, predictions_per_configuration=2,
        horizon_sec=450, full_selections=0, native_runs=0, coefficient_candidates=0),
        evidence='Exact prefix, actual route columns, current Omega701 reaggregation from cached per-link residence',
        source_pins=pins, configuration_difference='Only urban.known_wout_local_queue; no other retuning',
        scope='Old zero-green hold and executed2/4/6 reopening; not a current minimum2s feasible SDMPC choice',
        limitations=['Same seed29 but unused4650 state, not independent-seed validation',
                     'Native final4.9s uses last-stock hold; LSA missing and existing approved LDP proof retained',
                     'Do not tune to the small net-gain sign; inspect mainline versus urban cost and accepted merge']))
    save(DEST/'native_omega701.json', dict(start_sec=4650, end_sec=5100,
        native_execution_reused=True, exact_common_prefix=True, FZP_scans=0,
        total_0_5100_veh_h=totals, delta_4650_5100_veh_h=sum(delta_links.values()),
        delta_by_link_veh_h=delta_links, initial_routes_in_pinned_frame=True,
        method='Reclassify per-link residence; identical0–4650 prefix cancels. Absolute window costs not reconstructed.',
        old_scope_delta_veh_h=proof['delta_TTT_veh_h'], native_ramp_audit=str(OLD/'analysis/ramp_response_audit.json')))
    print('Prepared four forecasts; native Omega701 delta', sum(delta_links.values()), flush=True)


def run(model):
    OUT = DEST/(model+'_native_command')
    assert not OUT.exists(), 'No overwrite or automatic retry'
    plan = read(DEST/'plan.json')
    for p, expected in plan['source_pins'].items():
        assert sha(Path(p)) == expected, p
    os.environ.update(NUMSIM_REPO_ROOT=str(ROOT/'vendor/NumSim-mine'), PYTHONDONTWRITEBYTECODE='1')
    tuning = DEST/(model+'_config.json')
    sys.argv = ['verify.py', '--at', '4650', '--out', str(OUT), '--no-prediction', '--cold-prices',
                '--tuning', str(tuning), '--decisions', str(F)]
    loader = importlib.util.spec_from_file_location('canonical_verifier', R/'urban260/verify.py')
    v = importlib.util.module_from_spec(loader); loader.loader.exec_module(v)
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
    rebuild_history = probe.replay_vsl_history
    previous_history = read(OLD/'vsl_history_replay.json')
    missing = [r['cutoff'] for r in previous_history['checks'] if not r['online_cache_compared']]
    assert missing == [4500, 4650]
    assert all(not (F/'obs150'/f'vsl_cohorts_{t:06}.json').exists() for t in missing)
    def replay_history(*a, **kw):
        assert kw['known_missing_online_cutoffs'] == []
        # REVIEW237/238 already qualified these two absent online witnesses.
        # Canonical code reconstructs actual past frames/readbacks, checks all
        # other witnesses exactly and retains explicit missing-cache receipts.
        kw['known_missing_online_cutoffs'] = missing
        return rebuild_history(*a, **kw)
    probe.replay_vsl_history = replay_history
    from evaluation.controllers import vissim_stackelberg_adapter as adapter, sdmpc_pfo
    from evaluation.controllers import physical_ramp_branches as ramps, sdmpc_sequence as sequence
    from evaluation.controllers import signal_actuation_contract as signals, area_leader_objective as constraints
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_area_objective import get_ledger
    from src.controllers import rollout_endpoint as endpoint
    from src.models.state import ControlAction
    original_main = adapter.main

    def main():
        capture = {}
        bound = ramps.configure_operating_bounds
        forecast = adapter.demand_from_state

        def capture_bound(state, cfg, reference):
            capture.update(state=state, cfg=cfg)
            return bound(state, cfg, reference)

        def capture_forecast(*a, **kw):
            value = forecast(*a, **kw); capture['forecast'] = value
            return value

        ramps.configure_operating_bounds = capture_bound
        adapter.demand_from_state = capture_forecast

        def audit(reference, coord, policy, options, evaluate, derivative, quantities, check_budget, emit):
            state, cfg = capture['state'], capture['cfg']
            assert state.time_sec == 4650 and len(capture['forecast']) == 3
            assert cfg.network.known_legsplit_routes.get('local_queue_gate', False) == (model == 'candidate')
            assert hasattr(state, 'known_legsplit_route_state')
            from evaluation.controllers.control_area_objective import physical_membership_from_ledger
            member = physical_membership_from_ledger(read(ROOT/read(tuning)['control_area_objective']['membership_path']))
            observed = sum(member[str(r['link_no'])] for r in read(F/'state_004650.json')['vehicle_records']['records'])
            assert abs(sum(s['inside'] for s in get_ledger(state).stocks.values()) - observed) < 1e-6
            save(OUT/'initial.json', dict(observed_inside=observed, cohorts=state.known_legsplit_route_state['cohorts'],
                current_route_source='Canonical adapter loads the pinned decision frame; no future route input'))
            def historical_action(path):
                # These verified native238 commands used an older metadata tag
                # not accepted by the online parser. Retain the files verbatim;
                # explicitly check their physical CSV rather than forge an
                # online/applied receipt or weaken the production parser.
                data = read(path)
                action = ControlAction(**{k:copy.deepcopy(data[k]) for k in
                    ('N_P_star','N_UF_star','ramp_metering','vsl','green_times','offsets',
                     'inflow_outflow_allocation','diagnostics')})
                table = cfg.network.physical_ramp_branches['ramps']
                rows = [r for r in csv.DictReader(path.with_suffix('.csv').read_text(encoding='utf-8-sig').splitlines())
                        if r['kind'] == 'ramp_meter']
                assert len(rows) == 8 and {r['id'] for r in rows} == set(table)
                for r in rows:
                    m = table[r['id']]; g = float(r['green_sec'])
                    assert r['metadata'].split(';')[0] == 'diagnostic_fixed_sequence'
                    assert int(r['sc_no']) == m['sc_no']
                    assert float(r['rate_vph']) == g*m['capacity_vph']/m['cycle_sec']
                    assert action.diagnostics['rw_meter_green_'+r['id']] == g
                return ramps.prepare_control(signals.prepare_control(action, cfg), cfg)
            results = {}
            for arm, folder in [('hold', OLD/'held_writer'), ('selected', PROTOCOL.parent/'selected/commands')]:
                controls = [historical_action(folder/f'action_{t:06}.json') for t in (4650, 4800, 4950)]
                for b in controls:
                    signals.validate_writer(b, cfg, adapter.load_signal_group_actuation_plan(), 'experiment')
                action = sequence.pack(controls)
                began = time.perf_counter()
                with sequence.prediction_scope(action, cfg, 4650, 3) as visits:
                    point = endpoint.evaluate_price_point(state, action, copy.deepcopy(capture['forecast']), (),
                        endpoint.ObjectiveSpec(cfg, depth_override=3, box_walk=False, score_mode='raw'), capture_response=True)
                assert not point.aborted and len(point.states) == 3 and visits == [0, 1, 2]
                response = point.control_area_response
                assert response['model_constraint_coverage']['complete']
                assert response['conditional_model_feasibility_witness']
                exceed = max((r['exceedance_veh'] for r in response['resource_allocations']), default=0.)
                assert exceed <= 1e-7
                for s in (state, *point.states): get_ledger(s).assert_stocks(model_inventory(s, cfg))
                stock_costs = {}
                for row in response['residence']:
                    for k, n in row['inside_veh'].items(): stock_costs[k] = stock_costs.get(k, 0.) + n*row['dt_h']
                assert abs(sum(stock_costs.values()) - point.ttt) < 1e-7
                follower = adapter._PHASE_VECTOR_FOLLOWER['ref']
                qs = constraints.shared_urban_quantities(follower, response, start_sec=4650, horizon_steps=3)
                constraint = constraints.shared_quantity_constraints(follower, action, qs, start_sec=4650, horizon_steps=3,
                    np_mode='cap', target_np_veh=action.N_P_star, np_tolerance_veh=1e-7,
                    nuf_mode='cap', target_nuf_veh_h=action.N_UF_star, nuf_tolerance_veh_h=1e-7)
                item = dict(omega_ttt_veh_h=point.ttt, costs_by_stock=stock_costs,
                    predicted_ramp_merge=point.control_area['predicted_ramp_merge'],
                    flow_counts=point.control_area['flow_counts'], inherited_cap_check=constraint,
                    resource_max_exceedance=exceed, conservation_checks=4, wall_sec=time.perf_counter()-began,
                    greens=[b.diagnostics['rw_meter_green_RM_C10681'] for b in controls],
                    current_minimum_policy_valid=False, reason='Historical hold0s, outside current2s RM lower bound')
                save(OUT/(arm+'.json'), item); results[arm] = item
                print(model, arm, point.ttt, flush=True)
            save(OUT/'summary.json', dict(results=results,
                delta_omega_ttt_veh_h=results['selected']['omega_ttt_veh_h']-results['hold']['omega_ttt_veh_h'],
                native_runs=0, coefficient_fits=0, optimization=False, future_observation_as_input=False))
            raise v.Done()
        sdmpc_pfo.solve = audit
        return original_main()
    adapter.main = main
    v.main()


if __name__ == '__main__':
    sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]
    ap = argparse.ArgumentParser(); ap.add_argument('--prepare', action='store_true')
    ap.add_argument('--model', choices=['baseline', 'candidate']); args = ap.parse_args()
    if args.prepare: prepare_evidence()
    else:
        assert args.model
        run(args.model)
