"""Verify the finite153 experiment and preserve the local failure evidence."""
import csv
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE = Path(__file__).resolve().parent


def main():
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    assert not (HERE/'assessment.json').exists()
    pins = {}
    def read(p):
        pins[str(p)] = h.sha(p)
        return h.read(p)
    status = read(HERE/'forecast/status.json')
    assert status['status'] == 'complete_macro_gate_failed' and status['forecasts'] == 9
    assert all(read(HERE/'forecast/parity.json').values())
    preservation = read(HERE/'forecast/preservation.json')
    assert all(preservation[k] for k in ('core', 'inputs', 'STOP', 'hooks_restored'))
    preflight = read(HERE/'preflight.json')
    assert h.sha(h.__file__) == preflight['helper_sha256']
    assert read(HERE/'forecast/executed_function_sources.json') == read(h.R/'spatial_context148/forecast/executed_function_sources.json')
    comparison = read(HERE/'forecast/training_assessment.json')
    rows = read(HERE/'forecast/training/rows.json')
    assert len(rows) == 8
    max_mass, max_route, part_checks = 0., 0., 0
    windows = []
    records = {r['arm']: r for r in common.records(False)}
    for row in rows:
        key = row['case']+'_'+row['arm']
        pred = read(HERE/'forecast/training'/(key+'.json.gz'))
        diag = pred['diagnostics']['roads'][0]
        max_mass = max(max_mass, diag['continuity_residual_max_veh'])
        max_route = max(max_route, diag['joint_lane_region']['route_marginal_max_error'])
        assert diag['negative_density_count'] == 0
        part_checks += row['spatial144']['samples']
        assert row['spatial144']['max_class_partition_error'] < 1e-8
        if row['case'] != 's67_late' or row['arm'] not in ('release', 'release_vsl90'): continue
        fp = Path(records[row['arm']]['truth'])/'flows_30s.csv'
        pins[str(fp)] = h.sha(fp)
        truth = list(csv.DictReader(fp.open(encoding='utf-8-sig')))
        baseline = read(h.R/'spatial_context148/forecast/training'/(key+'.json.gz'))
        for start, end in ((2670.1, 2700.1), (2820.1, 2970.1), (2970.1, 3120.1)):
            item = dict(arm=row['arm'], start=start, end=end)
            for label, data in [('baseline', baseline), ('candidate', pred)]:
                ll = data['diagnostics']['roads'][0]['joint_lane_region']['rows']
                state = {}
                for cell in (20, 21):
                    z = [x for x in ll if x['cell'] == cell and x['lane'] == 1 and start+1e-6 < x['time_s'] <= end+1e-6]
                    state[str(cell)] = dict(incoming=sum(x['mainline_in_veh'] for x in z), outgoing=sum(x['mainline_out_veh'] for x in z),
                        merges=sum(x['merge_veh'] for x in z), end_n=z[-1]['n_veh'], end_v=z[-1]['v_kmh'])
                z = [x for x in data['flows'] if x['cell'] == 20 and start+1e-6 < x['window_end_s'] <= end+1e-6]
                state['off20'] = sum(x['off_departures'] for x in z)
                item[label] = state
            z = [x for x in truth if x['road'] == 'FW_E' and int(x['cell']) == 20 and start+1e-6 < float(x['window_end_s']) <= end+1e-6]
            item['actual_off20'] = sum(float(x['off_departures']) for x in z)
            windows.append(item)
    assert part_checks == 21600 and max_mass < 1e-7 and max_route < 1e-7
    protocol = read(HERE/'forecast/protocol.json')
    for p, digest in {**pins, **protocol['protected_sha256'], **preservation['input_sha256']}.items(): assert h.sha(p) == digest, p
    assert h.sha(protocol['STOP']['path']) == protocol['STOP']['sha256']
    result = dict(status='rejected_no_production_adoption', forecasts=9, new_fits=0,
        paired_component_TTT=comparison['candidate']['pairs'], gates=comparison['checks'],
        scores={k:{v:comparison[k][v] for v in ('absolute', 'local', 'response')} for k in ('baseline', 'candidate')},
        windows=windows, max_mass_error=max_mass, max_route_error=max_route, half_partition_checks=part_checks,
        physical_source_exact148=True, unmodified_FD=True, changed_coefficients=read(HERE/'proposal.json')['differences'],
        native=0, FZP=0, full_run_analysis=0, push=0, goal_complete=False,
        score_caution='Do not interpret inherited132 coefficient prior or total fitting objective as a fresh153 fit. No fitting done. Acceptance uses listed unregularized errors and physical responses.')
    h.save(HERE/'assessment.json', result)
    h.save(HERE/'assessment_pins.json', pins)
    h.save(HERE/'completion.json', dict(status='complete_rejected', previous_goal_turn='NO_PROGRESS', current_turn='PROGRESS',
        forecasts=9, elapsed_prediction_sec=status['elapsed_sec'], process_session=49666, process_exit_code=0,
        goal_status='ACTIVE/NOT_QUALIFIED', production_adopted=False, checks=comparison['checks'],
        next='No combination/parameter-grid expansion. Examine why nonlinear downstream21/22 recovery and native merge/arrival pulse dispersion remain wrong after local early-state corrections; review existing merge-phase112 and pressure137/146 before any new experiment.',
        remaining=['Independent state/seed and wholeOmega cost/flow qualification', 'Latest SDMPC AD/selection/constraints and observations', 'Short native then matched9000 after physical benefit qualification']))
    h.save(h.R/'receiving_lane152/completion.json', dict(status='complete_cached_diagnostic', current_turn='PROGRESS',
        lane_state_rows=540, native_block_lane_rows=24, total_flow_checks=24,
        new_forecasts=0, new_fits=0, native=0, FZP=0, full_run_analysis=0, push=0,
        production_adopted=False, goal_status='ACTIVE/NOT_QUALIFIED'))
    print(result['gates'], 'mass', max_mass, 'route', max_route, 'part checks', part_checks)
    for x in windows: print(x)


if __name__ == '__main__': main()
