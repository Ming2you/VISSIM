"""Review the completed comparison from saved aggregates; never rescan FZP."""
import collections
import bisect
import csv
import hashlib
import gzip
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / 'analysis'
pins = {}


def read(path):
    data = path.read_bytes()
    pins[str(path)] = hashlib.sha256(data).hexdigest()
    return json.loads(data)


def main():
    recovery = read(HERE / 'recovered_native_status.json')
    assert recovery['details']['terminal'] == 9000
    assert all(row['exit'] == 0 for row in recovery['recovery']['child_exit_codes'])
    assert read(HERE / 'postprocess_recovery_status.json')['stage'] == 'complete'
    summary = read(OUT / 'summary.json')
    assert summary['paired_prefix_exact'] and summary['original_initial_history_exact']
    spatial = read(OUT / 'spatial_decision_audit.json')
    decisions = read(OUT / 'sdmpc_decisions.json')['decisions']
    assert len(decisions) == 54
    metrics, removals, executions, series = {}, {}, {}, {}
    for arm in ('nc', 'sdmpc'):
        metrics[arm] = m = read(OUT / arm / 'area_metrics.json')
        executions[arm] = e = read(OUT / arm / 'execution.json')
        assert e['native_execution_passed']
        assert m['sampling']['nominal_step_sec'] == 5
        assert m['sampling']['missing_snapshot_gaps'] == 0
        assert m['closure']['max_abs_residual_veh'] == 0
        events = read(OUT / arm / 'native_errors.json')['unique_events']
        removed = [x for x in events if x['kind'] == 'lane_change_removal']
        removals[arm] = {
            'by_link': dict(collections.Counter(x['link'] for x in removed)),
            'event_count': len(removed),
            'unique_vehicle_count': len({x['vehicle_id'] for x in removed}),
            'other_route_warnings': sum(x['kind'] == 'route_next_link_not_found' for x in events),
        }
        assert removals[arm]['unique_vehicle_count'] == summary['arms'][arm]['native_removals']
        p = OUT / arm / 'area_timeseries.csv'
        pins[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
        with p.open(encoding='utf-8-sig', newline='') as stream:
            series[arm] = {round(float(x['sim_sec']), 6): float(x['ttt_veh_h_cumulative'])
                           for x in csv.DictReader(stream)}
        series[arm][0.] = 0.

    periods = []
    cuts = (0., 900.1, 1950.1, 4200.1, 6300.1, 8995.1, 9000.)
    for lo, hi in zip(cuts, cuts[1:]):
        costs = {arm: series[arm][hi] - series[arm][lo] for arm in series}
        periods.append({'from_sec': lo, 'to_sec': hi, **costs,
                        'delta_omega_veh_h': costs['sdmpc'] - costs['nc']})
    assert abs(sum(x['delta_omega_veh_h'] for x in periods) - summary['delta_TTT_veh_h']) < 1e-7

    links = []
    a = metrics['nc']['physical_link_residence']
    b = metrics['sdmpc']['physical_link_residence']
    for key in a.keys() | b.keys():
        x, y = a.get(key), b.get(key)
        if x and y:
            assert x['inside'] == y['inside']
        nc, controlled = (x or {}).get('ttt_veh_h', 0.), (y or {}).get('ttt_veh_h', 0.)
        links.append({'link': key, 'inside_Omega': (x or y)['inside'],
                      'nc_veh_h': nc, 'sdmpc_veh_h': controlled, 'delta_veh_h': controlled - nc})
    assert abs(sum(x['delta_veh_h'] for x in links if x['inside_Omega']) - summary['delta_TTT_veh_h']) < 1e-7
    nc, controlled = summary['arms']['nc'], summary['arms']['sdmpc']
    review = {
        'status': 'NATIVE_COMPLETE_PERFORMANCE_WORSE_GAIN_NOT_QUALIFIED',
        'scope': 'One seed29 matched 9000s closed-loop pair; no new fit, forecast or native run.',
        'omega_cost_increase_percent': 100 * summary['delta_TTT_veh_h'] / nc['TTT_0_9000_veh_h'],
        'whole_cost_increase_percent': 100 * summary['delta_native_total_time_including_uninserted_veh_h'] / nc['native_total_time_including_uninserted_veh_h'],
        'cost_components': spatial['delta_sdmpc_minus_nc_veh_h'],
        'periods': periods,
        'largest_increases': sorted(links, key=lambda x: -x['delta_veh_h'])[:15],
        'largest_decreases': sorted(links, key=lambda x: x['delta_veh_h'])[:10],
        'removals': removals,
        'ttd': {arm: {k: m[k] for k in ('ttd_observed_exit_events', 'ttd_terminal_exit_inferred_events',
                                       'ttd_observed_plus_terminal_events', 'unresolved_inside_disappearances')}
                for arm, m in metrics.items()},
        'decisions': {
            'applied_control_intervals': len(decisions),
            'rm_restricted_intervals': sum(bool(x['restricted_meters']) for x in decisions),
            'vsl_restricted_intervals': sum(bool(x['restricted_vsl']) for x in decisions),
            'vsl_values': sorted({v for x in decisions for v in x['vsl_commands_kph'].values()}),
            'all_east_meter_derivative_rows_zero': all(x['east_exact_zero_cost_and_resource_rows'] == x['east_meter_gradient_rows'] for x in spatial['meter_gradients']),
            'finite_neighbor_audit_performed': any(x['finite_neighbor_audit_performed'] for x in spatial['meter_gradients']),
            'sdmpc_converged_intervals': sum(x['sdmpc_converged'] for x in decisions),
            'pfo_iteration_cap': max(x['pfo']['max_iterations'] for x in decisions),
            'pfo_executed_range': [min(x['pfo']['executed_iterations'] for x in decisions), max(x['pfo']['executed_iterations'] for x in decisions)],
            'pfo_accepted_range': [min(x['pfo']['accepted_iterations'] for x in decisions), max(x['pfo']['accepted_iterations'] for x in decisions)],
            'pfo_converged_intervals': sum(x['pfo']['converged'] for x in decisions),
            'after_pfo_seconds_range': [min(x['sdmpc_after_pfo_seconds'] for x in decisions), max(x['sdmpc_after_pfo_seconds'] for x in decisions)],
        },
        'execution': {arm: {'native_ldp_readback_passed': e['native_execution_passed'],
                            'lsa_coverage_passed': e['native_lsa_com_coverage_passed']}
                      for arm, e in executions.items()},
        'limitations': [
            'Urban signals and VSL changed together; spatial cost differences do not isolate a VSL causal effect.',
            'TTD contains observed and terminal-inferred events. Unresolved disappearances are excluded, not counted as completions.',
            'Sampled mass ledger closes including unresolved disappearance; this is not proof of complete event identification.',
            'The final4.9s cost holds the8995.1s stock; the9000s command has no subsequent simulated interval.',
            'Native whole-network cost plus uninserted delay has a different scope from Omega TTT.',
            'An execution pass does not establish plant response/ranking validity or solver convergence.',
            'Legacy action.json prediction_error is not automatically a31-cell SDMPC forecast; its source must be verified before using it.',
        ],
        'source_sha256': pins,
    }
    (OUT / 'completed_review.json').write_text(json.dumps(review, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: review[k] for k in ('status', 'omega_cost_increase_percent', 'whole_cost_increase_percent', 'periods', 'decisions')}, ensure_ascii=False))


def first_interval_audit():
    """Compare two executed prefixes with existing native detector receipts."""
    root = HERE.parents[3]
    sys.path.insert(0, str(root))
    from evaluation.controllers import obs150_contract as oc
    from evaluation.controllers.obs150_observation import check_rule_crosscheck
    output = OUT/'first150_response.json'
    if output.exists():
        raise FileExistsError(output)
    run = Path('E:/VISSIM_runs/20260929_sd31_head10119_9000/sdmpc')
    folder = run/'decisions_sdmpc31_sdmpc9000_s29'
    geometry = read(HERE.parent/'selected/port_gain/geometry.json')
    assert geometry['network']['sha256'] == '64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
    assert read(OUT/'sdmpc/execution.json')['native_execution_passed']
    provenance = read(next(run.glob('run_provenance_*.json')))
    frozen = Path(provenance['workspace_root'])
    changes = []
    for row in provenance['controller_sources']:
        source = Path(row['path'])
        assert hashlib.sha256(source.read_bytes()).hexdigest() == row['sha256']
        relative = source.relative_to(frozen)
        current = root/relative
        digest = hashlib.sha256(current.read_bytes()).hexdigest()
        pins[str(current)] = digest
        if digest != row['sha256']:
            changes.append(str(relative).replace('\\','/'))
    assert set(changes) <= {'evaluation/controllers/sdmpc.py','evaluation/controllers/sdmpc_sequence.py'}, changes
    tuning = read(HERE.parent/'sc1001_sources_20260929/candidate_config.json')
    assert not tuning.get('adapter',{}).get('sdmpc_meter_activation_secant',False)
    with (OUT/'sdmpc/area_timeseries.csv').open(encoding='utf-8-sig',newline='') as stream:
        actual_cost = {round(float(x['sim_sec']),6):float(x['ttt_veh_h_cumulative']) for x in csv.DictReader(stream)}
    pins[str(OUT/'sdmpc/area_timeseries.csv')] = hashlib.sha256((OUT/'sdmpc/area_timeseries.csv').read_bytes()).hexdigest()

    def count(raw, link):
        assert raw['vehicle_records']['complete']
        return sum(int(v['link_no'])==int(link) for v in raw['vehicle_records']['records'])

    def cells(raw):
        rows = {r:[[] for _ in range(31)] for r in geometry['bounds']}
        for vehicle in raw['vehicle_records']['records']:
            address = geometry['addresses'].get(str(vehicle['link_no']))
            if address is None:
                continue
            road, offset = address
            pos = offset+vehicle['position_m']
            index = min(30,bisect.bisect_right(geometry['bounds'][road],pos)-1)
            assert index >= 0
            rows[road][index].append(vehicle['speed_kph'])
        return {r:dict(vehicle_count=[len(v) for v in series],
                       speed_kmh=[sum(v)/len(v) if v else None for v in series]) for r,series in rows.items()}

    windows = []
    for start in (1950,4500):
        end = start+150
        prediction = read(HERE.parent/f'closedloop_recorded{start}_select_check_live29_first150_v1/summary.json')
        selected = prediction['results']['selected']['first_interval']
        held = prediction['results']['held_actual']['first_interval']
        raw0,raw1 = (read(folder/f'state_{t:06d}.json') for t in (start,end))
        assert (raw0['sim_sec'],raw1['sim_sec']) == (start,end)
        obs = raw1[oc.RAW_STATE_KEY]
        detectors,_ = oc.read_detector_csv(obs['detector_config']['path'],obs['detector_config']['sha256'])
        oc.validate_raw(obs,detectors,expected_simres=10)
        check_rule_crosscheck(obs,detectors)
        bundle = oc.load_bundle(raw1)
        boundary = oc.evaluate_boundaries(obs,detectors,bundle.frame_end,bundle.frame_start,bundle.err_rows)
        removed = oc.window_removals(bundle.err_rows,start,end)
        ramps,offs = {},{}
        for ramp,pred in selected['ramps'].items():
            link = int(ramp.removeprefix('RM_C'))
            initial,final = count(raw0,link),count(raw1,link)
            assert abs(pred['initial_stock']-initial) < 1e-7
            arrival = boundary['ramp_arrival:'+ramp].cross
            heads = {d.boundary_ref for d in detectors if d.role=='meter_head' and d.link==link}
            assert heads
            head = sum(boundary[ref].cross for ref in heads)
            removal = sum(int(r['link'])==link for r in removed)
            merge = initial+arrival-final-removal
            assert merge >= 0
            actual = dict(initial_stock=initial,arrival=arrival,head=head,merge=merge,final_stock=final,removals=removal)
            ramps[ramp] = dict(actual=actual,predicted=pred,error={k:pred[k]-actual[k] for k in pred})
        for off,pred in selected['offramps'].items():
            initial,final = count(raw0,pred['connector']),count(raw1,pred['connector'])
            assert abs(pred['initial_stock']-initial) < 1e-7
            arrival = boundary['off_entry:'+off].cross
            removal = sum(int(r['link'])==int(pred['connector']) for r in removed)
            drain = initial+arrival-final-removal
            assert drain >= 0
            if off=='10643':
                assert drain == boundary['x10643_exit:10643'].cross
            actual = dict(initial_stock=initial,arrival=arrival,drain=drain,final_stock=final,removals=removal)
            offs[off] = dict(actual=actual,predicted=pred,
                            error={k:pred[k]-actual[k] for k in actual if k!='removals'})
        initial_cells,final_cells = cells(raw0),cells(raw1)
        roads = {}
        for road,actual in final_cells.items():
            s0,s1 = selected['physical_cell_states']
            assert max(abs(a-b) for a,b in zip(initial_cells[road]['vehicle_count'],s0['vehicle_count'][road])) < 1e-7
            rows = [dict(cell=i,initial_count=initial_cells[road]['vehicle_count'][i],
                         actual_count=n,predicted_count=s1['vehicle_count'][road][i],
                         count_error=s1['vehicle_count'][road][i]-n,
                         initial_speed_kmh=initial_cells[road]['speed_kmh'][i],
                         actual_speed_kmh=actual['speed_kmh'][i],predicted_speed_kmh=s1['speed_kmh'][road][i],
                         speed_error=(s1['speed_kmh'][road][i]-actual['speed_kmh'][i]) if n else None)
                    for i,n in enumerate(actual['vehicle_count'])]
            admission = sum(x['vehicles'] for x in selected['transfers'] if x['source']=='origin:'+road and x['target']=='freeway:'+road)
            exit_flow = sum(x['vehicles'] for x in selected['transfers'] if x['source']=='freeway:'+road and x['target']=='external:terminal:'+road)
            roads[road] = dict(cells=rows,initial_count=sum(initial_cells[road]['vehicle_count']),
                               actual_final_count=sum(actual['vehicle_count']),predicted_final_count=sum(s1['vehicle_count'][road]),
                               actual_admission=boundary['source:'+road].cross,predicted_admission=admission,
                               actual_terminal_exit=boundary['chain_end:'+road].cross,predicted_terminal_exit=exit_flow)
        cost = actual_cost[end+.1]-actual_cost[start+.1]
        windows.append(dict(start_sec=start,end_sec=end,ramps=ramps,offramps=offs,roads=roads,
            cost=dict(predicted_selected_omega_veh_h=selected['ttt_omega_veh_h'],
                      predicted_held_omega_veh_h=held['ttt_omega_veh_h'],
                      predicted_first150_delta=selected['ttt_omega_veh_h']-held['ttt_omega_veh_h'],
                      actual_selected_omega_veh_h_sampled_01phase=cost,
                      prediction_minus_actual_veh_h=selected['ttt_omega_veh_h']-cost,
                      surrogate450_delta=prediction['surrogate']['delta_ttt'],
                      execution450_delta=prediction['results']['selected']['delta_ttt_omega_veh_h'])))
    report = dict(status='FIRST150_EXECUTED_RESPONSE_AUDIT_COMPLETE_NOT_GAIN_QUALIFIED',
                  native_runs=0,new_fits=0,forecasts=4,controller_source_changes=changes,windows=windows,
                  limitations=['Native observations only evaluate predictions; no future observations enter forecasts.',
                    'Held command counterfactual has no same-state native run. Actual-minus-predicted is not causal control gain.',
                    'Actual TTT uses completed5s FZP aggregation on start+.1 to end+.1; not exact identical timestamp integration.',
                    'Physical cell speeds are endpoint snapshots, not150s averages; empty cells have no speed error.',
                    'Ramp merge and off-ramp drainage are boundary/stock identities with explicit removals.',
                    'Tracked model outside residence excludes native uninserted queues; Omega objective is unchanged.'],
                  source_sha256=pins)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=report['status'],costs=[w['cost'] for w in windows]),ensure_ascii=False))


def first_interval_terms_audit():
    """Check observational hooks preserve forecasts and close native road stocks."""
    root = HERE.parents[3]
    sys.path.insert(0,str(root))
    from evaluation.controllers import obs150_contract as oc
    output = OUT/'first150_terms.json'
    if output.exists():
        raise FileExistsError(output)
    report = read(OUT/'first150_response.json')
    geometry = read(HERE.parent/'selected/port_gain/geometry.json')
    network = root/geometry['network']['path']
    pins[str(network)] = hashlib.sha256(network.read_bytes()).hexdigest()
    assert pins[str(network)] == geometry['network']['sha256']
    links = {x.get('no'):x for x in ET.parse(network).findall('./links/link')}
    windows = []
    for window in report['windows']:
        start,end = window['start_sec'],window['end_sec']
        old = HERE.parent/f'closedloop_recorded{start}_select_check_live29_first150_v1'
        new = HERE.parent/f'closedloop_recorded{start}_select_check_live29_first150_terms_v2'
        for name in ('held_actual','selected'):
            a,b = read(old/(name+'.json')),read(new/(name+'.json'))
            a.pop('wall_sec');b.pop('wall_sec')
            assert a==b, 'Observational term tracing changed a prediction'
        p = new/'selected_first150_speed_terms.json.gz'
        pins[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
        with gzip.open(p,'rt',encoding='utf-8') as stream:
            terms = json.load(stream)
        assert len(terms)==19*150
        cells = {}
        for index in sorted({r['cell'] for r in terms}):
            rows = [r for r in terms if r['cell']==index]
            assert [r['time_sec'] for r in rows] == list(range(start,end))
            cells[index] = dict(first=rows[0],last=rows[-1],
                mean={k:sum(r[k] for r in rows)/len(rows) for k in (
                    'relaxation','convection','anticipation','lane_drop_raw','post_equation_change')},
                drop_active_steps=sum(r['lane_drop_raw']>1e-8 for r in rows),
                post_equation_limited_steps=sum(r['post_equation_change'] < -1e-8 for r in rows))
        folder = Path('E:/VISSIM_runs/20260929_sd31_head10119_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
        raw = read(folder/f'state_{end:06d}.json')
        bundle = oc.load_bundle(raw)
        removed = oc.window_removals(bundle.err_rows,start,end)
        closure = {}
        for road,row in window['roads'].items():
            ramps = [r for r in window['ramps'] if geometry['addresses'][
                links[r.removeprefix('RM_C')].find('toLinkEndPt').get('lane').split()[0]][0]==road]
            offs = [o for o in window['offramps'] if geometry['addresses'][
                links[o].find('fromLinkEndPt').get('lane').split()[0]][0]==road]
            removals = sum(str(r['link']) in geometry['addresses'] and
                           geometry['addresses'][str(r['link'])][0]==road for r in removed)
            actual = (row['initial_count']+row['actual_admission']+
                sum(window['ramps'][r]['actual']['merge'] for r in ramps)-
                sum(window['offramps'][o]['actual']['arrival'] for o in offs)-
                row['actual_terminal_exit']-removals-row['actual_final_count'])
            predicted = (row['initial_count']+row['predicted_admission']+
                sum(window['ramps'][r]['predicted']['merge'] for r in ramps)-
                sum(window['offramps'][o]['predicted']['arrival'] for o in offs)-
                row['predicted_terminal_exit']-row['predicted_final_count'])
            assert actual==0 and abs(predicted)<1e-7
            closure[road] = dict(ramps=ramps,offramps=offs,mainline_removals=removals,
                                native_residual=actual,predicted_residual=predicted)
        windows.append(dict(start_sec=start,end_sec=end,cells=cells,road_closure=closure))
    result = dict(status='TRACE_PRESERVES_ALL_FOUR_FORECAST_RESULTS_EXACTLY',
                  forecasts=4,new_fits=0,new_native_runs=0,windows=windows,source_sha256=pins,
                  limitations=['Equation terms are model diagnostics, not measured accelerations.',
                    'Raw lane-drop penalty precedes the speed floor; it is not automatically an additive net loss.',
                    'Post-equation change combines merge and receiving clamps; cell-specific context is required.',
                    'No coefficient ablation or calibration has been performed.'])
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],cells17_18=[{i:w['cells'][i] for i in (17,18)} for w in windows]),ensure_ascii=False))


if __name__ == '__main__':
    if sys.argv[1:] == ['--first-interval-audit']:
        first_interval_audit()
    elif sys.argv[1:] == ['--first-interval-terms']:
        first_interval_terms_audit()
    else:
        assert not sys.argv[1:]
        main()
