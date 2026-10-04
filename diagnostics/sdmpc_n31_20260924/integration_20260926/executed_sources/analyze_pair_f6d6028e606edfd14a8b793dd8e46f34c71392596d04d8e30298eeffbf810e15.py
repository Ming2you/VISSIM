"""Closed-run SDMPC connection checks and matched traffic comparisons.

Reuses native-execution and physical-area measurement utilities. No simulator,
optimizer, model fit, or process control. The finite native queue must be closed.
"""
import csv
import argparse
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from diagnostics.com_execution_equivalence.verify_pair import verify_native_execution
from diagnostics.fast_fixed_profile_verify import prefix_digest
from diagnostics.capture_native_runtime_errors import parse_bytes
from scripts.measure_control_area import read_fzp_frames, measure_frames, terminal_lengths, sha256
from evaluation.controllers.control_area_objective import physical_membership_from_ledger

RUNS = Path('D:/VISSIM_runs/20260926_selected1200_replay')
ORIGINAL = Path('D:/VISSIM_runs/20260924_sd31_gain/sdmpc31_g_gain_s29_r3')


def load(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def save(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def table(p, rows):
    with p.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def native_network_cost(run, end):
    data = load(run/'native_network_performance.json')
    assert data['schema'] == 'vissim_native_network_performance_v1'
    assert data['from_sec'] == 0 and data['to_sec'] == end
    assert data['read_at_sim_sec'] >= end and data['all_links_included'] is True
    assert data['evaluated_links'] > 0 and data['time_unit'] == 'veh*s'
    values = data['native']
    for key in ('TravTmTot', 'DelayLatent', 'DemandLatent', 'VehAct', 'VehArr'):
        assert type(values[key]) in (int, float) and math.isfinite(values[key]) and values[key] >= 0, key
    return {
        'native_physical_network_time_veh_h': values['TravTmTot']/3600,
        'native_uninserted_delay_veh_h': values['DelayLatent']/3600,
        'native_total_time_including_uninserted_veh_h': (values['TravTmTot']+values['DelayLatent'])/3600,
        'native_uninserted_at_end': values['DemandLatent'],
        'native_network_end_vehicles': values['VehAct'],
        'native_arrived_vehicles': values['VehArr'],
    }


def decision_summary(decisions, start, end):
    """Read completed decisions only, keeping proposed commands distinct from native proof."""
    rows = []
    for sec in range(start, end, 150):
        stem = decisions / f'action_{sec:06d}'
        report = load(stem.with_suffix('.joint.json'))
        assert report['completed'] is True, f'Incomplete SDMPC decision: {sec}'
        selected = report['selection']
        pfo = selected['pfo_warm_start']
        with stem.with_suffix('.csv').open(encoding='utf-8-sig', newline='') as stream:
            commands = list(csv.DictReader(stream))
        vsl, meters = {}, {}
        for command in commands:
            if command['kind'] == 'vsl':
                key, speed = command['id'], float(command['speed_kph'])
                assert key not in vsl or vsl[key] == speed, (sec, key)
                vsl[key] = speed
            elif command['kind'] == 'ramp_meter':
                meters[command['id']] = float(command['green_sec'])
        assert len(meters) == 8, (sec, meters)
        rows.append({
            'sim_sec': sec, 'vsl_commands_kph': vsl, 'meter_green_commands_sec': meters,
            'restricted_vsl': {k: v for k, v in vsl.items() if v < 110},
            'restricted_meters': {k: v for k, v in meters.items() if v < 10},
            # In cap mode the progress event's held_objective is the PFO warm start.
            # The selection record preserves the separate original held command.
            'held_surrogate_objective_veh_h': selected['held_objective'],
            'pfo_warm_start_surrogate_objective_veh_h': selected['warm_start_objective'],
            'selected_surrogate_objective_veh_h': selected['selected_objective'],
            'predicted_reduction_from_held_veh_h': selected['prediction_ttt_reduction'],
            'pfo': {k: pfo[k] for k in ('max_iterations', 'executed_iterations',
                                      'accepted_iterations', 'converged', 'status', 'seconds')},
            'sdmpc_candidates': selected['candidates'],
            'sdmpc_converged': selected['converged'],
            'sdmpc_after_pfo_seconds': selected['sdmpc_after_pfo_seconds'],
            'model_constraints': selected['final_constraints'],
        })
    return {'scope': 'Model decision and CSV command summary; native execution is verified separately.',
            'warning': 'Rolling predicted reductions have different initial states; do not sum them as realized gain.',
            'decisions': rows}


def short_connection(runs, nc_run, output, status_path):
    """Check a closed 1200s connection trial, without claiming congestion gain.

    The caller must separately confirm the owner/native processes have closed.
    Reuse the native command oracle and observation contracts, not new models.
    """
    from evaluation.controllers import obs150_contract as oc

    status = load(status_path)
    assert status['stage'] == 'requested_native_arms_complete_unanalyzed', status
    assert Path(status['details']['out_dir']).resolve() == runs.resolve()
    assert status['details']['arms'] == ['sdmpc'] and status['details']['terminal'] == 1200
    assert not (runs/'STOP').exists() and not (nc_run.parent/'STOP').exists()
    assert not (output/'summary.json').exists(), 'Preserve completed connection check'
    name = 'sdmpc31_sdmpc1200_s29'
    run = runs/'sdmpc'
    decisions = run/f'decisions_{name}'
    result = {'scope': 'SDMPC1200 connection only; not congestion or net-gain qualification',
              'passed': False, 'whole_omega_gain_qualified': False,
              'process_exit_verified_by_this_function': False,
              'status_path': str(status_path), 'status_sha256': sha256(status_path)}
    try:
        assert f'OK {name} attempt=1 ' in (run/'launch.log').read_text(encoding='utf-8-sig')
        execution = verify_native_execution(run, 1200, run_name=name)
        save(output/'execution.json', execution)
        result['native_execution_passed'] = execution['native_execution_passed']
        result['native_lsa_com_coverage_passed'] = execution['native_lsa_com_coverage_passed']
        assert execution['native_execution_passed'], 'Native LDP/readback verification failed'
        report = decision_summary(decisions, 900, 1200)
        save(output/'decisions.json', report)
        for sec in (900, 1050):
            joint = load(decisions/f'action_{sec:06d}.joint.json')
            assert joint['selection']['feasible'] is True, sec
            binding = load(decisions/f'action_{sec:06d}.joint_written.json')
            assert binding['prewrite_binding_passed'] and binding['written_command_binding_passed'], sec
            for key in ('action_csv', 'action_json'):
                assert sha256(Path(binding[key]['path'])) == binding[key]['sha256'], (sec, key)
        provenance = load(run/f'run_provenance_{name}.json')
        tuning_pin = provenance['files']['tuning']
        assert sha256(Path(tuning_pin['path'])) == tuning_pin['sha256']
        tuning = load(Path(tuning_pin['path']))
        frozen = Path(provenance['files']['main_vbs_runner']['path']).parent.parent
        manifest_sha = sha256(frozen/tuning['freeway']['lane_plant'])
        windows = []
        for sec in (1, *range(150, 1200, 150)):
            raw = load(decisions/f'state_{sec:06d}.json')
            obs = raw[oc.RAW_STATE_KEY]
            oc.validate_raw(obs, expected_simres=10)
            derived = load(decisions/f'obs150/derived_{sec:06d}.json')
            oc.validate_derived(derived)
            assert obs['run_id'] == derived['run_id'] == provenance['run_id']
            assert derived['inputs']['raw_sha256'] == oc.canonical_sha256(obs)
            for kind, item in obs['frames'].items():
                assert sha256(oc.resolve(obs, item['path'])) == item['sha256'], (sec, kind)
                assert derived['inputs'][f'frame_{kind}_sha256'] == item['sha256']
            history = load(decisions/f'obs150/vsl_cohorts_{sec:06d}.json')
            assert history['run_id'] == obs['run_id'] and history['manifest_sha256'] == manifest_sha
            assert history['cutoff'] == sec and history['frame_sha256'] == obs['frames']['current']['sha256']
            assert history['derived_sha256'] == oc.canonical_sha256(derived)
            start, _, _ = oc.bundle_interval(sec)
            previous = decisions/f'obs150/vsl_cohorts_{start:06d}.json'
            assert history['previous_sha256'] == (sha256(previous) if previous.exists() else None)
            for road, audit in history['audit'].items():
                assert audit['conservation_max'] < 1e-7, (sec, road)
                stock = sum(sum(row.values()) for row in history['cohorts'][road])
                assert abs(stock-audit['end_stock']) < 1e-7, (sec, road)
            windows.append({'sim_sec': sec, 'history_sha256': sha256(decisions/f'obs150/vsl_cohorts_{sec:06d}.json'),
                            'audit': history['audit']})
        save(output/'observation_history.json', {'manifest_sha256': manifest_sha, 'windows': windows})
        nc_name = 'sdmpc31_nc9000_s29'
        nc_prov = load(nc_run/f'run_provenance_{nc_name}.json')
        assert nc_prov['seed'] == provenance['seed'] == 29
        assert nc_prov['files']['network']['sha256'] == provenance['files']['network']['sha256']
        assert f'OK {nc_name} attempt=1 ' in (nc_run/'launch.log').read_text(encoding='utf-8-sig')
        prefixes = {}
        for arm, folder in (('sdmpc', run), ('nc', nc_run)):
            fzp, = (folder/'vissim_eval').glob('*.fzp')
            prefixes[arm] = prefix_digest(fzp, 900, recording_grid=(5, .1))
        result.update(prefixes=prefixes, matched_nc=str(nc_run),
                      precontrol_prefix_exact=prefixes['sdmpc'] == prefixes['nc'],
                      completed_decisions=2, observed_history_windows=len(windows))
        assert result['precontrol_prefix_exact'], 'First900s native data differs from matched NC'
        result['passed'] = True
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        save(output/'summary.json', result)
    print(json.dumps(result, ensure_ascii=False), flush=True)


def cached_diagnostics(runs, output, nc_run=None):
    """Use completed decision snapshots and the existing FZP aggregates only."""
    import bisect
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    summary = load(output/'summary.json')
    end = summary['end_sec']
    assert end >= 900 and end % 150 == 0 and summary['paired_prefix_exact']
    assert not (output/'spatial_decision_audit.json').exists(), 'Preserve completed audit'
    manifest = load(HERE.parent/'selected/plant_n31_v2.json')
    geometry_path = ROOT/manifest['sources']['geometry']['path']
    assert sha256(geometry_path) == manifest['sources']['geometry']['sha256']
    geometry = load(geometry_path)
    chains = {int(x['link']): (road, x['offset_m'])
              for road, chain in geometry['chains'].items() for x in chain}
    times = list(range(900, end+1, 150))
    costs, gradients, snapshots = {}, [], {}
    for arm in ('nc', 'sdmpc'):
        run = nc_run if arm == 'nc' and nc_run is not None else runs/arm
        name = summary.get('run_names', {}).get(arm, f'sdmpc31_{arm}{end}_s29')
        folder = run/f'decisions_{name}'
        matrices = {r: np.full((len(geometry['bounds'][r])-1, len(times)), np.nan)
                    for r in ('FW_E', 'FW_W')}
        for ti, sec in enumerate(times):
            state = load(folder/f'state_{sec:06d}.json')
            records = state['vehicle_records']
            assert records['complete'] and records['paused_at_sim_sec'] == sec
            sums = {r: np.zeros((2, len(matrices[r]))) for r in matrices}
            for vehicle in records['records']:
                address = chains.get(int(vehicle['link_no']))
                if address is None:
                    continue
                road, offset = address
                bounds = geometry['bounds'][road]
                position = offset + vehicle['position_m']
                # Native position may slightly overshoot a physical terminal.
                cell = min(len(bounds)-2, max(0, bisect.bisect_right(bounds, position)-1))
                sums[road][0, cell] += 1
                sums[road][1, cell] += vehicle['speed_kph']
            for road in matrices:
                count, speed = sums[road]
                np.divide(speed, count, out=matrices[road][:, ti], where=count > 0)
            if arm == 'sdmpc' and sec < end:
                selection = load(folder/f'action_{sec:06d}.joint.json')['selection']
                rows = [r for r in selection['gradient_rows'] if r['kind'] == 'meter']
                east = [r for r in rows if r['owner'] == 'FW_E']
                gradients.append({'sim_sec': sec, 'east_meter_gradient_rows': len(east),
                    'east_exact_zero_cost_and_resource_rows': sum(
                        r['total'] == 0 and all(v == 0 for v in r['resource_derivatives_scaled']) for r in east),
                    'rows': rows,
                    'finite_neighbor_audit_performed': selection['finite_neighbor_audit_performed']})
        snapshots[arm] = matrices
        residence = load(output/arm/'area_metrics.json')['physical_link_residence']
        groups = {}
        for link, row in residence.items():
            if int(link) in chains:
                group = chains[int(link)][0] + '_mainline'
            else:
                group = 'other_inside_Omega' if row['inside'] else 'outside_Omega'
            groups[group] = groups.get(group, 0.) + row['ttt_veh_h']
        costs[arm] = groups
    delta = {key: costs['sdmpc'][key]-costs['nc'][key] for key in costs['nc']}
    assert abs(sum(delta.values())-summary['delta_TTT_veh_h']-
               summary['delta_outside_Omega_residence_veh_h']) < 1e-7
    save(output/'spatial_decision_audit.json', {
        'cost_scope': f'0..{end}s, cached5s FZP residence including last-frame tail; excludes uninserted queue-time integral',
        'cost_veh_h': costs, 'delta_sdmpc_minus_nc_veh_h': delta,
        'meter_gradients': gradients,
        'heatmap_scope': f'Instantaneous observed native snapshots every150s,900..{end}; physical31cell geometry. Not a5s or150s averaged FZP heatmap.',
        'interpretation': 'A zero local derivative does not establish that a finite legal metering change has zero effect.'})
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), sharex=True)
    for row, road in enumerate(('FW_E', 'FW_W')):
        for col, arm in enumerate(('nc', 'sdmpc')):
            ax = axes[row, col]
            # Nearest-neighbour display around measured instants; no temporal averaging.
            edges = np.array([times[0]-75] + [t+75 for t in times])
            p = ax.pcolormesh(edges, np.array(geometry['bounds'][road])/1000,
                              snapshots[arm][road], cmap='RdYlBu', vmin=0, vmax=110)
            ax.set_title(f'{road} | {arm.upper()}')
            ax.set_xlim(900, end)
            ax.set_ylabel('Distance downstream [km]')
            ax.set_xlabel('Simulation time [s]')
            for boundary in geometry['boundaries']:
                if boundary['road'] == road and boundary['kind'] in ('ramp', 'offramp'):
                    ax.axhline(boundary['chain_pos_m']/1000, color='k', lw=.4, alpha=.35)
    fig.colorbar(p, ax=axes, label='Observed speed [km/h]', fraction=.025)
    fig.suptitle(f'Matched native{end} | seed29 | instantaneous150s snapshots,31physical cells')
    fig.savefig(output/'observed_snapshot_heatmap.png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(json.dumps({'delta_cost_components': delta,
        'east_zero_meter_rows': [(r['sim_sec'], r['east_exact_zero_cost_and_resource_rows'],
                                  r['east_meter_gradient_rows']) for r in gradients]}), flush=True)


def replay_ramp_audit(runs, output, protocol_path):
    """Compare frozen predictions with closed native detector bundles, without FZP scans."""
    from evaluation.controllers import obs150_contract as oc
    from evaluation.controllers.obs150_observation import check_rule_crosscheck

    protocol, comparison = load(protocol_path), load(output/'summary.json')
    assert comparison['counterfactual_valid']
    assert comparison['protocol_sha256'] == sha256(protocol_path)
    assert load(runs/'task_status.json')['phase'] == 'complete'
    assert not (runs/'STOP').exists()
    target = output/'ramp_response_audit.json'
    assert not target.exists(), 'Preserve completed ramp audit'
    prediction_path = Path(protocol['prediction_source'])
    assert sha256(prediction_path) == protocol['prediction_sha256']
    predictions = load(prediction_path)['results']
    cases = {'hold': 'held_actual', 'release': 'vsl_FW_E__seg13_release'}
    assert set(cases) == set(protocol['arms'])
    start, end = protocol['start_sec'], protocol['end_sec']
    assert end-start == 450
    report = dict(scope='Eight physical ramp connectors under the completed fixed VSL pair',
                  start_sec=start, end_sec=end, prediction_source=str(prediction_path),
                  prediction_sha256=sha256(prediction_path), arms={}, input_sha256={},
                  new_model_predictions=0, new_native_runs=0, fzp_rescans=0,
                  limitations=['Actual entries use native detector counts with the canonical boundary correction.',
                               'Merge = initial connector stock + entries - final stock - native removals; head crossings are separate.',
                               'Future native observations are evaluation targets only; predictions were frozen before these runs.',
                               'The VSL pair does not by itself establish an RM intervention benefit.'])
    csv_rows = []
    for arm, case in cases.items():
        assert comparison['arms'][arm]['native_execution_passed']
        run = runs/arm
        name = f'sdmpc31_g_{start}_{arm}_s{protocol["seed"]}'
        decisions = run/f'decisions_{name}'
        prediction = predictions[case]['ramps']
        assert len(prediction) == 8
        initial_path = decisions/f'state_{start:06d}.json'
        initial = load(initial_path)
        assert initial['sim_sec'] == start and initial['vehicle_records']['complete']
        report['input_sha256'][str(initial_path)] = sha256(initial_path)

        def stock(raw, ramp):
            assert raw['vehicle_records']['complete']
            return sum(int(v['link_no']) == int(ramp.removeprefix('RM_C'))
                       for v in raw['vehicle_records']['records'])

        actual = {r: dict(initial_stock=stock(initial, r), arrival=0, head=0, merge=0,
                          removals=0, final_stock=stock(initial, r), windows=[])
                  for r in prediction}
        for sec in range(start+150, end+1, 150):
            path = decisions/f'state_{sec:06d}.json'
            raw = load(path)
            assert raw['sim_sec'] == sec
            report['input_sha256'][str(path)] = sha256(path)
            obs = raw[oc.RAW_STATE_KEY]
            detectors, _ = oc.read_detector_csv(obs['detector_config']['path'],
                                                 obs['detector_config']['sha256'])
            oc.validate_raw(obs, detectors, expected_simres=oc.EXPECTED_SIMRES)
            check_rule_crosscheck(obs, detectors)
            bundle = oc.load_bundle(raw)
            boundaries = oc.evaluate_boundaries(obs, detectors, bundle.frame_end,
                                                bundle.frame_start, bundle.err_rows)
            removals = oc.window_removals(bundle.err_rows, sec-150, sec)
            for ramp, row in actual.items():
                link = int(ramp.removeprefix('RM_C'))
                arrival = boundaries['ramp_arrival:'+ramp].cross
                heads = {d.boundary_ref for d in detectors if d.role == 'meter_head' and d.link == link}
                assert heads, ramp
                head = sum(boundaries[ref].cross for ref in heads)
                removed = sum(int(r['link']) == link for r in removals)
                ending = stock(raw, ramp)
                merge = row['final_stock']+arrival-ending-removed
                assert merge >= 0, (arm, ramp, sec, merge)
                row['windows'].append(dict(start_sec=sec-150, end_sec=sec, arrival=arrival,
                                           head=head, merge=merge, final_stock=ending, removals=removed))
                for key, value in dict(arrival=arrival, head=head, merge=merge, removals=removed).items():
                    row[key] += value
                row['final_stock'] = ending
        rows = {}
        for ramp, observed in actual.items():
            predicted = prediction[ramp]
            assert abs(observed['initial_stock']+predicted['arrival']-predicted['merge']-predicted['final_stock']) < 1e-7
            assert observed['initial_stock']+observed['arrival']-observed['merge']-observed['removals']-observed['final_stock'] == 0
            delta = {k: predicted[k]-observed[k] for k in ('arrival', 'merge', 'final_stock')}
            rows[ramp] = dict(actual=observed, predicted=predicted, prediction_minus_actual_veh=delta)
            csv_rows.append(dict(arm=arm, ramp=ramp, initial_stock=observed['initial_stock'],
                                 actual_arrival=observed['arrival'], predicted_arrival=predicted['arrival'],
                                 actual_merge=observed['merge'], predicted_merge=predicted['merge'],
                                 actual_final_stock=observed['final_stock'], predicted_final_stock=predicted['final_stock'],
                                 native_removals=observed['removals']))
        report['arms'][arm] = rows
    save(target, report)
    table(output/'ramp_response_audit.csv', csv_rows)
    print(json.dumps(dict(report=str(target), rows=csv_rows)), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--short-connection', action='store_true')
    modes.add_argument('--closed-loop-3000', action='store_true')
    modes.add_argument('--closed-loop-9000', action='store_true')
    modes.add_argument('--replay-protocol', type=Path)
    parser.add_argument('--runs-root', type=Path)
    parser.add_argument('--nc-run-dir', type=Path, help='Reuse a completed matched NC run without copying or rerunning it')
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--status-json', type=Path)
    parser.add_argument('--cached-diagnostics', action='store_true')
    parser.add_argument('--cached-replay-ramp-audit', action='store_true')
    args = parser.parse_args()
    if args.short_connection:
        if any(x is None for x in (args.runs_root, args.nc_run_dir, args.output_dir, args.status_json)):
            parser.error('--short-connection requires --runs-root, --nc-run-dir, --output-dir, --status-json')
        if args.cached_diagnostics or args.cached_replay_ramp_audit:
            parser.error('--short-connection cannot be combined with cached analysis')
        short_connection(args.runs_root, args.nc_run_dir, args.output_dir, args.status_json)
        return
    if args.cached_replay_ramp_audit and (not args.replay_protocol or args.cached_diagnostics):
        parser.error('--cached-replay-ramp-audit requires --replay-protocol, without --cached-diagnostics')
    closed_loop = args.closed_loop_3000 or args.closed_loop_9000
    if args.nc_run_dir is not None and not closed_loop:
        parser.error('--nc-run-dir requires a closed-loop comparison')
    if closed_loop:
        end = 9000 if args.closed_loop_9000 else 3000
        if end == 9000 and args.runs_root is None:
            parser.error('--closed-loop-9000 requires --runs-root')
        runs = args.runs_root or Path('D:/VISSIM_runs/20260926_sd31_closedloop3000')
        arms, start = ('nc', 'sdmpc'), 900
        output = HERE.parent/f'closedloop{end}_analysis'
        status_path = HERE.parent/f'closedloop{end}_status.json'
        names = {arm: f'sdmpc31_{arm}{end}_s29' for arm in arms}
        scope = f'matched no-control and actual receding-horizon SDMPC{end}; execution alone does not establish gain'
    elif args.replay_protocol:
        if args.runs_root is None:
            parser.error('--replay-protocol requires --runs-root')
        protocol=load(args.replay_protocol)
        runs, arms = args.runs_root, tuple(protocol['arms'])
        start,end=protocol['start_sec'],protocol['end_sec']
        assert len(arms)==2 and end-start==450 and type(protocol['seed']) is int
        output,status_path=args.replay_protocol.parent/'analysis',args.replay_protocol.parent/'status.json'
        names={arm:f'sdmpc31_g_{start}_{arm}_s{protocol["seed"]}' for arm in arms}
        scope=protocol['scope']
    else:
        runs, arms, start, end = RUNS, ('hold', 'selected'), 1200, 1650
        output, status_path = HERE/'analysis', HERE/'status.json'
        names = {arm: f'sdmpc31_g_1200_{arm}_s29' for arm in arms}
        scope = 'one frozen SDMPC450s decision replay; not closed-loop performance'
    if args.output_dir is not None:
        output = args.output_dir
    if args.status_json is not None:
        status_path = args.status_json
    if args.cached_replay_ramp_audit:
        replay_ramp_audit(runs, output, args.replay_protocol)
        return
    if args.cached_diagnostics:
        assert closed_loop
        cached_diagnostics(runs, output, args.nc_run_dir)
        return
    status = load(status_path)
    assert status['stage'] in ('both_native_complete_unanalyzed', 'requested_native_arms_complete_unanalyzed'), status
    if closed_loop:
        assert Path(status['details']['out_dir']).resolve() == runs.resolve(), 'Completed queue belongs to another result directory'
        if 'arms' in status['details']:
            expected_arms = ['sdmpc'] if args.nc_run_dir is not None else list(arms)
            assert status['details']['arms'] == expected_arms, 'Requested native arms must have completed'
    assert not (runs/'STOP').exists(), 'User STOP exists'
    assert not (output/'summary.json').exists(), 'Preserve existing completed comparison'
    protocol = load(args.replay_protocol or HERE/'protocol.json')
    rm_observation_pair = bool(args.replay_protocol and protocol.get('controller')=='diagnostic-ramp-profile')
    if rm_observation_pair:
        assert arms==('hold','release') and start==2700 and end==3150 and protocol['seed']==47
        for path,digest in protocol['command_pins'].items():
            assert sha256(Path(path))==digest, path
    ledger_path = HERE.parent/'selected/scenario/control_area_membership_213a5d.json'
    ledger = load(ledger_path)
    for item in [ledger['network'], *ledger['sources']]:
        assert sha256(ROOT/item['path']) == item['sha256'], item['path']
    membership = physical_membership_from_ledger(ledger)
    terminals = terminal_lengths(ledger)
    summary = {'scope': scope,
               'start_sec': start, 'end_sec': end, 'arms': {},
               'reused_nc_run': str(args.nc_run_dir.resolve()) if args.nc_run_dir is not None else None,
               'whole_omega_gain_qualified': False, 'new_calibration': False}
    if closed_loop:
        decisions = decision_summary(runs/'sdmpc'/f"decisions_{names['sdmpc']}", start, end)
        save(output/'sdmpc_decisions.json', decisions)
    original_prefix = None
    if not rm_observation_pair:
        original_run=Path(protocol['original_run']) if args.replay_protocol else ORIGINAL
        original_fzp, = (original_run/'vissim_eval').glob('*.fzp')
        original_prefix = prefix_digest(original_fzp, start, recording_grid=(5, .1))
    prefixes = {}
    for arm in arms:
        run = args.nc_run_dir if arm == 'nc' and args.nc_run_dir is not None else runs/arm
        name = names[arm]
        if args.nc_run_dir is not None and arm == 'nc':
            assert not (run.parent/'STOP').exists(), 'Reused NC belongs to a stopped job'
            log = (run/f'runlog_{name}.txt').read_text(encoding='utf-8-sig').splitlines()
            assert 'STAGE=SIM_DONE' in log and f'SIM_SEC={end}' in log, 'Reused NC is incomplete'
            assert f'OK {name} attempt=1 ' in (run/'launch.log').read_text(encoding='utf-8-sig')
        provenance = load(run/f'run_provenance_{name}.json')
        assert provenance['files']['network']['sha256'] == protocol['network_sha256']
        assert provenance['seed'] == protocol['seed'] and provenance['sim_period_sec'] == end
        if rm_observation_pair:
            decisions=run/f'decisions_{name}'
            for sec in (1,*range(150,end+1,150)):
                for suffix in ('.csv','.json'):
                    planned=args.replay_protocol.parent/arm/'commands'/f'action_{sec:06d}{suffix}'
                    assert sha256(decisions/planned.name)==sha256(planned), (arm,sec,suffix)
            log=(run/f'runlog_{name}.txt').read_text(encoding='utf-8-sig').splitlines()
            native=[line for line in log if line.startswith('PROFILE_NATIVE_SIGNAL_READBACK ')]
            expected=[f'PROFILE_NATIVE_SIGNAL_READBACK sim_sec={sec} checked=160 non_native=0 missing=0'
                      for sec in (1,end)]
            assert native==expected, 'Native urban signal ownership missing at initialization or termination'
        out = output/arm
        execution = verify_native_execution(run, end, run_name=name)
        save(out/'execution.json', execution)
        if args.replay_protocol:
            assert execution['native_execution_passed'], f'Native replay execution failed: {out}'
        errors = []
        events = []
        for p in sorted(run.rglob('*.err')):
            parsed = parse_bytes(p.read_bytes())
            assert not parsed['unparsed_removal_lines'], str(p)
            errors.append({'path': str(p), 'sha256': sha256(p), **parsed})
            events.extend(parsed['events'])
        # Some native .err files are copied into the run root: count each event once.
        events = [json.loads(s) for s in sorted({json.dumps(e, sort_keys=True) for e in events})]
        removals = {str(e['vehicle_id']): e for e in events if e['kind'] == 'lane_change_removal'}
        save(out/'native_errors.json', {'files': errors, 'unique_events': events})
        fzp, = (run/'vissim_eval').glob('*.fzp')
        prefixes[arm] = prefix_digest(fzp, start, recording_grid=(5, .1))
        before = fzp.stat()
        previous = None

        def audited_frames():
            nonlocal previous
            for frame in read_fzp_frames(fzp):
                if previous:
                    dt = frame.time_sec - previous.time_sec
                    for no in previous.vehicles.keys() - frame.vehicles.keys():
                        v = previous.vehicles[no]
                        if no in removals and v.link in terminals:
                            reach = v.speed_kph/3.6*dt + 1.5*dt*dt + 10
                            overshoot = v.speed_kph/3.6*.1 + .015 + 10
                            assert not -overshoot <= terminals[v.link]-v.position_m <= reach, (
                                'Explicit removal would be counted as terminal TTD', no)
                previous = frame
                yield frame

        metrics, times = measure_frames(audited_frames(), membership, terminals,
                                       end_sec=end, simulation_step_sec=.1)
        after = fzp.stat()
        assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
        assert metrics['sampling']['nominal_step_sec'] == 5 and metrics['sampling']['missing_snapshot_gaps'] == 0
        save(out/'area_metrics.json', metrics)
        table(out/'area_timeseries.csv', times)
        at_start = next(r for r in times if abs(r['sim_sec']-(start+.1)) < 1e-7)
        row = {'native_execution_passed': execution['native_execution_passed'],
               'lsa_passed': execution['native_lsa_com_coverage_passed'],
               f'TTT_0_{end}_veh_h': metrics['ttt_veh_h'],
               f'TTT_{start}p1_{end}_veh_h': metrics['ttt_veh_h']-at_start['ttt_veh_h_cumulative'],
               'Omega_TTD_events': metrics['ttd_observed_plus_terminal_events'],
               'Omega_end_vehicles': metrics['censored_last_observed_inside_vehicles'],
               'native_removals': len(removals),
               'uninserted_at_end': sum(e['remaining_vehicles'] for e in events if e['kind']=='unfinished_vehicle_input'),
               'unresolved_Omega_disappearances': metrics['unresolved_inside_disappearances'],
               'outside_Omega_residence_veh_h': sum(r['ttt_veh_h'] for r in metrics['physical_link_residence'].values() if not r['inside']),
               'last_fzp_sec': metrics['boundaries']['last_fzp_sec'],
               'tail_hold_veh_h': metrics['ttt_censored_tail_extrapolation_veh_h']}
        if args.closed_loop_9000 or (run/'native_network_performance.json').exists():
            row.update(native_network_cost(run, end))
        summary['arms'][arm] = row
        print(json.dumps({arm: row}), flush=True)
    a, b = (summary['arms'][arm] for arm in arms)
    summary.update(prefixes=prefixes, original_prefix=original_prefix,
                   paired_prefix_exact=prefixes[arms[0]]==prefixes[arms[1]],
                   original_initial_history_exact=(all(x==original_prefix for x in prefixes.values())
                                                   if original_prefix is not None else None),
                   delta_definition=f'{arms[1]} minus {arms[0]}',
                   delta_TTT_veh_h=b[f'TTT_0_{end}_veh_h']-a[f'TTT_0_{end}_veh_h'],
                   delta_outside_Omega_residence_veh_h=b['outside_Omega_residence_veh_h']-a['outside_Omega_residence_veh_h'],
                   limitations=['5s sampled residence; final4.9s holds last observed stock.',
                                'Urban signals and freeway commands are jointly controlled; not VSL-only attribution.',
                                'Native whole-network time and sampled Omega time have different scopes and must not be substituted.',
                                'Completion of a simulation does not establish controller gain or independent-seed robustness.',
                                'Native LSA coverage failure remains separate; user authorized LDP as execution evidence.'])
    key = 'native_total_time_including_uninserted_veh_h'
    if key in a and key in b:
        summary['delta_native_total_time_including_uninserted_veh_h'] = b[key]-a[key]
        summary['delta_native_uninserted_delay_veh_h'] = b['native_uninserted_delay_veh_h']-a['native_uninserted_delay_veh_h']
    else:
        summary['limitations'].append('Uninserted terminal count is not the external input-queue time integral; native delay is missing.')
    if rm_observation_pair:
        summary.update(protocol_path=str(args.replay_protocol),protocol_sha256=sha256(args.replay_protocol),
            prediction_source=None,matched_prior_run_claimed=False,
            counterfactual_valid=summary['paired_prefix_exact'],
            native_urban_ownership_readback_scope='Initialization and termination; no per-decision ownership readback claimed. Every actual CSV is checked against the pinned plan without urban rows; native LDP covers the intervening states.')
        summary['limitations'][1]='Only10484 RM changes after the common paired prefix; native urban signals and VSL110 held. No original fast-run trajectory identity claimed.'
    elif args.replay_protocol:
        summary.update(protocol_path=str(args.replay_protocol),protocol_sha256=sha256(args.replay_protocol),
            prediction_source=protocol['prediction_source'],
            predicted_delta_omega_veh_h=protocol['predicted_delta_omega_veh_h'],
            predicted_delta_tracked_total_veh_h=protocol['predicted_delta_tracked_total_veh_h'],
            counterfactual_valid=summary['paired_prefix_exact'] and summary['original_initial_history_exact'])
        summary['limitations'][1]='Only the protocol VSL zone changes after the common prefix; city signals,offset and all RM commands are held.'
    save(output/'summary.json', summary)
    if args.replay_protocol:
        assert summary['counterfactual_valid'], 'Replay does not recover the same initial microscopic history; result is not a valid paired effect'
    print(json.dumps({k:v for k,v in summary.items() if k not in ('arms','limitations')}), flush=True)


if __name__ == '__main__':
    main()
