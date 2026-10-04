"""Bounded saved-result/obs150 cohort audit; no rollout, fit, COM, or FZP read."""
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

from evaluation.controllers import obs150_contract as oc, offramp_routing as routing

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REVIEW = HERE.parent
I = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'
PINS = {}


def read(path):
    data = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(data).hexdigest()
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)


def main():
    assert not (HERE / 'assessment.json').exists(), 'Preserve prior audit'
    evidence = read(REVIEW / 'compatible71/assessment.json')
    runtime = read(REVIEW / 'entry10643/native_cohorts.json')['route_runtime']
    detectors, digest = oc.read_detector_csv(I / 'selected/obs150/obs150_detectors_v2.csv')
    PINS[str(I / 'selected/obs150/obs150_detectors_v2.csv')] = digest
    groups = oc.group_boundaries(detectors)
    specs = {
        '43_nc': (43, 'nc', 2250,
            'D:/VISSIM_runs/20260929_seed43_observation2700/nc/decisions_sdmpc31_nc2700_s43',
            'closedloop_recorded2250_lever450_trace10681_compatible71_43',
            'archived rejected compatible71 candidate, not current production'),
        '47_hold': (47, 'hold', 2700,
            'D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47',
            'closedloop_recorded2700_select_check_trace10681_entry10643',
            'current retained10638 baseline with observation-only route export'),
    }
    cases = {}
    for case, (seed, arm, start, folder, prediction_dir, model_scope) in specs.items():
        times = list(range(start, start + 451, 150))
        raws = {t: read(Path(folder) / f'state_{t:06d}.json') for t in times}
        frames = {t: read(Path(raw['lane_plant_observation']['directory']) / f'frame_{t:06d}.json')
                  for t, raw in raws.items()}
        trace = read(I / prediction_dir / 'held_actual_RM_C10681_trace.json.gz')['offramp_network_diagnostics']
        result = read(I / prediction_dir / 'summary.json')['results']['held_actual']
        assert trace['route_runtime'] == runtime
        initial_all = {v[0]: v for v in frames[start]['vehicles']}
        physical = {vid: v for vid, v in initial_all.items() if str(v[1]) in runtime['physical']}
        known, uncertain = {}, {}
        target_chain = runtime['branches']['10682']['source_chain_m']
        for vid, v in physical.items():
            road, pos, cell = routing._position(runtime, v[1], v[3])
            if road != 'FW_E' or pos > target_chain:
                continue
            if v[6] is None:
                weights = routing._future_distribution(runtime, road, pos)
            else:
                weights = routing._route_distribution(runtime, runtime['routes'][f'{int(v[6])}:{int(v[7])}'], road, pos)
            weight = weights.get('10682', 0.)
            detail = dict(vehicle=vid, cell=cell, chain_m=pos, link=v[1], lane=v[2], route=v[6:9])
            if v[6] is not None and weight == 1.:
                known[vid] = detail
            elif weight > 0:
                uncertain[vid] = dict(detail, weight=weight)
        events = {ref: [] for ref in ('off_entry:10682', 'source:FW_E', 'ramp_arrival:RM_C10639')}
        tails = []
        for t in times[1:]:
            bundle = oc.load_bundle(raws[t])  # existing implementation verifies chunk and frame SHA
            window = oc.assign_window(bundle.obs, bundle.mer_rows)
            for ref, rows in events.items():
                for det in groups[ref]:
                    if window.tails[det.dcp_no]:
                        tails.append(dict(end_sec=t, ref=ref, dcp=det.dcp_no, count=window.tails[det.dcp_no]))
                    rows.extend(dict(vehicle=e.veh, time_sec=e.t_entry, lane=det.lane, window_end=t)
                                for e in window.entries[det.dcp_no])
        exits = events['off_entry:10682']
        assert len({e['vehicle'] for e in exits}) == len(exits)
        assert not any(t['ref'] == 'off_entry:10682' for t in tails)
        native = evidence['cases'][str(seed)][arm]['ports']['10682']['native']
        assert len(exits) == native['entry'], 'Missing boundary correction must be investigated'
        source_ids = {e['vehicle'] for e in events['source:FW_E']}
        ramp_ids = {e['vehicle'] for e in events['ramp_arrival:RM_C10639']}
        witnesses = []
        for event in exits:
            vid = event['vehicle']
            group = ('initial_assigned' if vid in known else 'initial_future_choice' if vid in uncertain
                     else 'initial_other_mainline' if vid in physical else 'not_initial_mainline')
            witnesses.append(dict(event, group=group, source_witness=vid in source_ids,
                                  ramp_arrival_witness=vid in ramp_ids, initial=initial_all.get(vid)))
        snapshots = []
        for t, snap, port in zip(times, trace['route_states'], trace['states']):
            assert abs(snap['time_sec'] - t) < 1e-8
            lookup = {v[0]: v for v in frames[t]['vehicles']}
            exited_ids = {e['vehicle'] for e in exits if e['window_end'] <= t}
            remaining, unaccounted = [], []
            for vid in known:
                if vid in exited_ids:
                    continue
                row = lookup.get(vid)
                if row is not None and str(row[1]) in runtime['physical']:
                    road, pos, cell = routing._position(runtime, row[1], row[3])
                    remaining.append(dict(vehicle=vid, road=road, cell=cell, chain_m=pos))
                else:
                    unaccounted.append(dict(vehicle=vid, current=row))
            stock = Counter()
            for row in snap['inventory']['cells']['FW_E']:
                for label, n in row.items():
                    if label.endswith('|10682'):
                        stock[label] += n
            known_stock = sum(n for label, n in stock.items() if label.startswith('observed_route:'))
            null_stock = sum(n for label, n in stock.items() if label.startswith('observed_null|'))
            future_stock = sum(n for label, n in stock.items() if label.startswith('expected_input:'))
            other_stock = {k: v for k, v in stock.items()
                           if not k.startswith(('observed_route:', 'observed_null|', 'expected_input:')) and v > 1e-9}
            assert not other_stock, other_stock
            known_exit = len(known) - known_stock
            uncertain_expected = sum(r['weight'] for r in uncertain.values())
            uncertain_exit = uncertain_expected - null_stock
            admitted = port['ports']['10682']['admitted']
            snapshots.append(dict(time_sec=t, native_known_exited=len(set(known) & exited_ids),
                native_known_retained=remaining, native_known_unaccounted=unaccounted,
                model_known_exited=known_exit, model_uncertain_exited=uncertain_exit,
                model_future_exited=admitted-known_exit-uncertain_exit,
                model_future_retained=future_stock, model_target_stock_by_label=dict(stock),
                model_origin_stock=snap['inventory']['origins']['FW_E']))
        retained, unknown = [], []
        for v in frames[times[-1]]['vehicles']:
            if v[0] in physical or str(v[1]) not in runtime['physical']:
                continue
            road, pos, cell = routing._position(runtime, v[1], v[3])
            if road != 'FW_E' or pos > target_chain:
                continue
            if v[6] is None:
                unknown.append(dict(vehicle=v[0], cell=cell, chain_m=pos, source_witness=v[0] in source_ids))
            else:
                route = runtime['routes'][f'{int(v[6])}:{int(v[7])}']
                if route['target'] == '10682':
                    retained.append(dict(vehicle=v[0], cell=cell, chain_m=pos,
                                         source_witness=v[0] in source_ids, initial=initial_all.get(v[0])))
        new_exit = [e for e in witnesses if e['group'] == 'not_initial_mainline']
        new_target_observed = len(new_exit) + len(retained)
        final = snapshots[-1]
        model_source = result['control_area']['flow_counts']['origin:FW_E->freeway:FW_E']
        probability = runtime['inputs']['FW_E']['weights']['10682']
        model_target_generated = final['model_future_exited'] + final['model_future_retained']
        assert abs(model_target_generated-model_source*probability) < 1e-7
        population_delta = new_target_observed-model_target_generated
        stock_delta = len(retained)-final['model_future_retained']
        exit_delta = len(new_exit)-final['model_future_exited']
        assert abs(exit_delta-(population_delta-stock_delta)) < 1e-7
        new_source_ids = source_ids-set(physical)
        before_station = {v[0] for v in frames[times[-1]]['vehicles']
                          if v[0] not in physical and v[1] == 74 and v[3] < 40.}
        cases[case] = dict(seed=seed, start_sec=start, end_sec=times[-1], model_scope=model_scope,
            native_port=native, current_baseline_port=evidence['cases'][str(seed)][arm]['ports']['10682']['before'],
            audited_model_port=trace['states'][-1]['ports']['10682'],
            initial_assigned=list(known.values()), initial_uncertain=list(uncertain.values()),
            entry_cohorts=dict(Counter(e['group'] for e in witnesses)), witnesses=witnesses,
            native_future_exited=len(new_exit), native_future_retained=retained, native_unknown_retained=unknown,
            native_future_target_observed=new_target_observed,
            new_exits_without_source_witness=[e for e in new_exit if not e['source_witness']],
            new_retained_without_source_witness=[e for e in retained if not e['source_witness']],
            native_new_source_generation_lower_bound=len(new_source_ids | before_station),
            model_source_generated=model_source, configured_target_probability=probability,
            model_future_target_generated=model_target_generated,
            decomposition_actual_minus_model=dict(future_target_population=population_delta,
                future_target_retained=stock_delta, future_target_exited=exit_delta),
            station_tails=tails, snapshots=snapshots,
            windows=[dict(start_sec=t-150,end_sec=t,entries=sum(e['window_end']==t for e in exits)) for t in times[1:]])
        print(case, json.dumps({k: cases[case][k] for k in ('entry_cohorts','native_future_exited',
            'native_future_target_observed','model_source_generated','model_future_target_generated',
            'decomposition_actual_minus_model','station_tails')}))
        print('native_retained',len(retained),'unknown',len(unknown),'no_source',len(cases[case]['new_exits_without_source_witness']))
        print('initial_snapshots',[(s['time_sec'],s['native_known_exited'],len(s['native_known_retained']),
            len(s['native_known_unaccounted']),s['model_known_exited']) for s in snapshots])
    output = dict(status='completed_readonly_10682_cohort_decomposition', cases=cases, source_pins=PINS,
        new_native_runs=0, new_fzp_scans=0, new_forecasts=0, fitted_parameters=0, adopted_changes=0,
        limitations=[
            'Seed43 route-class snapshots come from a rejected compatible71 candidate. Current baseline totals are shown separately.',
            'Future observations are diagnostic only; no future boundary is supplied to an autonomous forecast.',
            'New-target population counts exclude unresolved future choices and possible unobserved losses; they are not an unbiased routing-probability estimator.',
            'Remaining-stock algebra does not independently prove a speed-dynamics error.',
            'Different seeds also use different initial times and conditions; no paired seed causal effect is asserted.'])
    (HERE/'assessment.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def assess_destination_speed():
    """Conditional stock-mixing check; no guessed future route identities."""
    import math
    from evaluation.controllers.projection_support import complete_records
    from evaluation.controllers.vehicle_routes import complete_vehicle_routes

    dest = REVIEW / 'destination_speed86'
    protocol = read(dest / 'protocol.json')
    assert not (dest / 'assessment.json').exists(), 'Preserve completed assessment'
    for path, digest in protocol['source_pins'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
    runtime = read(REVIEW / 'entry10643/native_cohorts.json')['route_runtime']
    base = I / 'baseline_reproduction_20260929/cellwise_calibration/freeway_first'
    specs = [(29, 'none', 'early'), (29, 'vsl', 'early'),
             (43, 'none', 'early'), (43, 'vsl', 'early'),
             (67, 'release', 'late'), (67, 'release_vsl90', 'late')]
    branches = {k: b for k, b in runtime['branches'].items() if b['freeway'] == 'FW_E'}

    def shares(rows):
        n = len(rows)
        stock = sum(r['is_target'] for r in rows) / n if n else None
        speed_sum = math.fsum(r['speed'] for r in rows)
        speed = (math.fsum(r['speed'] for r in rows if r['is_target']) / speed_sum
                 if speed_sum else stock)
        return stock, speed

    # Nonzero velocity covariance must matter; all-stopped fallback stays finite.
    assert shares([dict(is_target=True, speed=10), dict(is_target=False, speed=90)]) == (.5, .1)
    assert shares([dict(is_target=True, speed=0), dict(is_target=False, speed=0)]) == (.5, .5)
    assert shares([dict(is_target=True, speed=40), dict(is_target=False, speed=40)]) == (.5, .5)
    details = []
    cases = {}
    for seed, arm, era in specs:
        raw = read(base / f'route_inventory/s{seed}_{era}/initial_raw.json')
        routes = complete_vehicle_routes(raw, required=True)
        records = complete_records(raw)
        initial = {}
        labels = {key: {} for key in branches}
        for v in records:
            if str(v['link_no']) not in runtime['physical']:
                continue
            fw, x, cell = routing._position(runtime, v['link_no'], v['position_m'])
            if fw != 'FW_E':
                continue
            vid = str(v['veh_no'])
            initial[vid] = dict(cell=cell, x=x, speed=v['speed_kph'], lane=int(v['lane_index']))
            r = routes[v['veh_no']]
            if r['route_decision_no'] is None:
                continue
            key = str(r['route_decision_no']) + ':' + str(r['route_no'])
            route = runtime['routes'][key]
            assert r['route_decision_type'].upper() == 'STATIC'
            if route['target'] in runtime['branches']:
                end = runtime['branches'][route['target']]['source_chain_m']
            else:
                end = route['end'][1]
            # Do not use routes already completed/missed or infer a subsequent decision.
            if x > end + 1e-6:
                continue
            for target, branch in branches.items():
                if end + 1e-6 < branch['source_chain_m']:
                    continue
                labels[target][vid] = dict(is_target=route['target'] == target, route_end=end)
        cache_path = (base / f'cohort_early/s{seed}_{arm}_frames.json.gz' if era == 'early'
                      else base / f'flow67/{arm}_frames.json.gz')
        cache = read(cache_path)
        assert cache['fields'][:4] == ['cell', 'speed_kmh', 'x_m', 'lane']
        frames = sorted((float(t), row) for t, row in cache['frames'].items())
        assert abs(frames[0][0] - raw['sim_sec']) < 1e-7
        assert set(initial) == set(frames[0][1]), (seed, arm, 'initial identity')
        max_initial = {'speed': 0., 'position': 0.}
        for vid, v in initial.items():
            a = frames[0][1][vid]
            assert (v['cell'], v['lane']) == (a[0], a[3]), (seed, vid)
            max_initial['speed'] = max(max_initial['speed'], abs(v['speed'] - a[1]))
            max_initial['position'] = max(max_initial['position'], abs(v['x'] - a[2]))
        # Cached native text is millimetre / .001 km/h rounded; no model-state rewrite.
        assert max_initial['speed'] < .001 and max_initial['position'] < .002, max_initial
        alive = set(initial)
        case_rows = []
        for (ta, a), (tb, b) in zip(frames, frames[1:]):
            assert abs(tb-ta-5) < 1e-7
            alive.intersection_update(a)
            for target, branch in branches.items():
                c = branch['source_cell']
                cell_ids = {vid for vid, v in a.items() if v[0] == c}
                selected = []
                for vid in cell_ids & alive & labels[target].keys():
                    label = labels[target][vid]
                    if a[vid][2] > label['route_end'] + .002:
                        continue
                    selected.append(dict(vehicle=vid, speed=a[vid][1], lane=a[vid][3],
                        x=a[vid][2], is_target=label['is_target']))
                n_target = sum(r['is_target'] for r in selected)
                if not n_target or n_target == len(selected):
                    continue
                departures = [r for r in selected if r['vehicle'] not in b or b[r['vehicle']][0] != c]
                through_seen = [r for r in departures if r['vehicle'] in b]
                # Absence is not called an off-ramp event or normal Omega exit.
                absent = [r for r in departures if r['vehicle'] not in b]
                s_stock, s_speed = shares(selected)
                groups = {str(k): [r for r in selected if r['is_target'] == k] for k in (False, True)}
                case_rows.append(dict(seed=seed, arm=arm, start_sec=ta, end_sec=tb,
                    target=target, cell=c, total_cell_vehicles=len(cell_ids),
                    known_labeled_vehicles=len(selected), target_vehicles=n_target,
                    coverage=len(selected)/len(cell_ids),
                    target_mean_speed=math.fsum(r['speed'] for r in groups['True'])/len(groups['True']),
                    through_mean_speed=math.fsum(r['speed'] for r in groups['False'])/len(groups['False']),
                    target_share_stock=s_stock, target_share_speed=s_speed,
                    departures=len(departures), target_departures=sum(r['is_target'] for r in departures),
                    downstream_seen=len(through_seen), absent_unclassified=len(absent),
                    target_absent_unclassified=sum(r['is_target'] for r in absent),
                    stock_expected_departures=len(departures)*s_stock,
                    speed_expected_departures=len(departures)*s_speed))
            # Once a vehicle leaves the recorded mainline episode, never revive its old route.
            alive.intersection_update(b)
        summary = {}
        for target in branches:
            rows = [r for r in case_rows if r['target'] == target]
            if not rows:
                summary[target] = dict(mixed_windows=0)
                continue
            actual = sum(r['target_departures'] for r in rows)
            by_method = {}
            for name in ('stock', 'speed'):
                errors = [r[name+'_expected_departures']-r['target_departures'] for r in rows]
                by_method[name] = dict(sum_expected=sum(r[name+'_expected_departures'] for r in rows),
                    bias=sum(errors), window_mae=sum(abs(e) for e in errors)/len(errors))
            summary[target] = dict(mixed_windows=len(rows), observed_target_cell_departures=actual,
                labeled_departures=sum(r['departures'] for r in rows),
                absent_unclassified=sum(r['absent_unclassified'] for r in rows),
                mean_labeled_coverage=sum(r['coverage'] for r in rows)/len(rows),
                mean_target_minus_through_speed=sum(r['target_mean_speed']-r['through_mean_speed'] for r in rows)/len(rows),
                closure=by_method)
        cases[f'{seed}_{arm}'] = dict(initial_sec=raw['sim_sec'], last_sec=frames[-1][0],
            initial_identity_equal=True, initial_precision_error=max_initial, branches=summary)
        details.extend(case_rows)
        print(seed, arm, json.dumps(summary, ensure_ascii=False))
    result = dict(status='complete_conditional_destination_mixing', cases=cases,
        windows=len(details), synthetic_checks=3, new_forecasts=0, new_native=0,
        fitted_parameters=0, fzp_scans=0, adopted=False, gain_qualified=False,
        limitations=protocol['limitations'], source_pins=PINS)
    for name, obj in (('details.json', details), ('assessment.json', result)):
        (dest/name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def assess_current_destination_snapshots():
    """Current routes/speeds from the same completed67 runs; no cache stitching."""
    import math
    dest = REVIEW / 'destination_speed86'
    assert not (dest/'current_snapshots.json').exists()
    protocol = read(dest/'current_protocol.json')
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest() == protocol['source_sha256']
    runtime = read(REVIEW/'entry10643/native_cohorts.json')['route_runtime']
    cases = {}
    for arm in ('release', 'release_vsl90'):
        folder = Path('D:/VISSIM_runs/20261003_s67_vsl_observation2700')/arm/f'decisions_sdmpc31_g_2700_{arm}_s67'
        rows = []
        for t in (2700, 2850, 3000, 3150):
            raw = read(folder/f'state_{t:06d}.json')
            ref = raw['lane_plant_observation']
            frame = read(Path(ref['directory'])/f'frame_{t:06d}.json')
            assert frame['complete'] and frame['time_s'] == ref['time_s'] == raw['sim_sec'] == t
            assert frame['run_id'] == ref['run_id']
            assert len(frame['vehicles']) == raw['total_vehicles']
            cells = {c: [] for c in range(31)}
            for v in frame['vehicles']:
                if str(v[1]) not in runtime['physical']:
                    continue
                fw, x, cell = routing._position(runtime, v[1], v[3])
                if fw != 'FW_E':
                    continue
                if v[6] is None:
                    route = None
                else:
                    assert str(v[8]).upper() == 'STATIC'
                    route = runtime['routes'][f'{int(v[6])}:{int(v[7])}']
                cells[cell].append(dict(id=v[0], speed=v[4], lane=v[2], x=x, route=route))
            for target, branch in runtime['branches'].items():
                if branch['freeway'] != 'FW_E':
                    continue
                # Source cell plus one upstream cell: same fixed geometry in each arm.
                for cell in (branch['source_cell']-1, branch['source_cell']):
                    target_rows, through_rows, unknown = [], [], []
                    for v in cells[cell]:
                        route = v['route']
                        if route is None:
                            unknown.append(v)
                            continue
                        end = (runtime['branches'][route['target']]['source_chain_m']
                               if route['target'] in runtime['branches'] else route['end'][1])
                        if v['x'] > end+.002 or end+1e-6 < branch['source_chain_m']:
                            unknown.append(v)
                        elif route['target'] == target:
                            target_rows.append(v)
                        else:
                            through_rows.append(v)
                    known = target_rows + through_rows
                    sum_v = math.fsum(v['speed'] for v in known)
                    vs = lambda vv: math.fsum(v['speed'] for v in vv)/len(vv) if vv else None
                    rows.append(dict(time_sec=t, cell=cell, target=target,
                        target_ids=[v['id'] for v in target_rows], through_ids=[v['id'] for v in through_rows],
                        unknown_ids=[v['id'] for v in unknown], total=len(cells[cell]),
                        target_n=len(target_rows), through_n=len(through_rows), unknown_n=len(unknown),
                        target_speed=vs(target_rows), through_speed=vs(through_rows),
                        stock_share=len(target_rows)/len(known) if known else None,
                        speed_share=math.fsum(v['speed'] for v in target_rows)/sum_v if sum_v else None,
                        target_lane_counts=dict(Counter(v['lane'] for v in target_rows)),
                        through_lane_counts=dict(Counter(v['lane'] for v in through_rows))))
            assert all(r['target_n']+r['through_n']+r['unknown_n']==r['total'] for r in rows if r['time_sec']==t)
        cases[arm] = rows
    assert cases['release'][:8] == cases['release_vsl90'][:8], 'Actual common initial route/speed state differs'
    out = dict(status='complete_same_run_current_snapshots', seed=67, cases=cases,
        exact_common_initial_partitions=True, actual_native_identity_not_cross_run_cache=True,
        source_pins=PINS, native=0, forecasts=0, fitting=0,
        limitation='Actual post-intervention states are diagnostic labels, not identical local initial states or causal coefficients. Future routes are never inferred. Unknown routes remain separate. Nv shares are spatial quantities, not measured split ratios.')
    (dest/'current_snapshots.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    for arm, rows in cases.items():
        print(arm)
        for r in rows:
            if r['cell']==runtime['branches'][r['target']]['source_cell']:
                print(r['time_sec'],r['target'],r['target_n'],r['through_n'],r['unknown_n'],r['target_speed'],r['through_speed'],r['stock_share'],r['speed_share'])


def assess_approach10483_90():
    """Localize a completed native paired response; never change or fit the plant."""
    import bisect
    import math
    import statistics
    import xml.etree.ElementTree as ET
    from diagnostics.probe_e8_lane_receiving import IndexedFzp

    dest = REVIEW/'approach10483_90'
    assert not (dest/'assessment.json').exists(), 'Preserve completed analysis'
    protocol = read(dest/'protocol.json')
    for name, sha in {**protocol['inputs_sha256'], **protocol['protected_sha256']}.items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == sha, name
    choices = read(REVIEW/'cohort_departure89/native_choices.json')
    witnesses = {v['vehicle']: v for v in choices['vehicle_witnesses']['same_exit']
                 if v['baseline_exit'] == v['vsl_exit'] == 'off_entry:10483'}
    assert len(witnesses) == 84
    geometry = read(I/'selected/port_gain/geometry.json')
    runtime = read(REVIEW/'entry10643/native_cohorts.json')['route_runtime']
    cells = [c for c in geometry['cells'] if c['road'] == 'FW_E']
    bounds = [c['start_m'] for c in cells]
    source_x = runtime['branches']['10483']['source_chain_m']
    network = ET.parse(ROOT/geometry['network']['path']).getroot()
    signs = [d for d in network.findall('.//desSpeedDecision') if d.get('no') in ('63','64','65','66')]
    sign_x = [runtime['physical'][d.get('lane').split()[0]][1]+float(d.get('pos')) for d in signs]
    assert len(sign_x) == 4 and max(sign_x) == min(sign_x)
    thresholds = [('sign63_66', sign_x[0])] + [(f'cell{c}_start', bounds[c]) for c in (17,18,19,20)]
    cache = dest/'tracks.json.gz'
    if cache.exists():
        saved = read(cache)
        assert saved['protocol_sha256'] == PINS[str(dest/'protocol.json')]
    else:
        saved = dict(protocol_sha256=PINS[str(dest/'protocol.json')], cases={})
        for arm in protocol['cases']:
            fzp = Path('D:/VISSIM_runs/20261003_s67_vsl_observation2700')/arm/'vissim_eval'/f'sdmpc31_g_2700_{arm}_s67_001.fzp'
            before = fzp.stat()
            reader = IndexedFzp(fzp, max_bytes=protocol['budget_bytes_per_arm'])
            tracks = {str(v): [] for v in witnesses}
            try:
                for t in protocol['times_sec']:
                    values = reader.snapshot(t, extra_columns=protocol['extras'])
                    for vid in witnesses:
                        if vid not in values:
                            continue
                        link, lane, pos, speed, extra = values[vid]
                        tracks[str(vid)].append(dict(t=t,link=link,lane=lane,pos=pos,speed=speed,extra=extra))
                after = fzp.stat()
                assert (before.st_size,before.st_mtime_ns) == (after.st_size,after.st_mtime_ns)
                saved['cases'][arm] = dict(tracks=tracks,source=str(fzp),size=after.st_size,
                    mtime_ns=after.st_mtime_ns,bytes_read=reader.bytes_read,snapshots=reader.selected)
                print(arm,'bounded bytes',reader.bytes_read,'of',after.st_size,flush=True)
            finally:
                reader.handle.close()
        cache.write_bytes(gzip.compress(json.dumps(saved,ensure_ascii=False,allow_nan=False).encode('utf-8')))
    results = {}
    for vid, witness in witnesses.items():
        results[str(vid)] = {}
        for arm, time_key in [('release','baseline_time'),('release_vsl90','vsl_time')]:
            end = witness[time_key]
            points = []
            for row in saved['cases'][arm]['tracks'][str(vid)]:
                if row['t'] > end:
                    continue
                physical = runtime['physical'].get(str(row['link']))
                if physical and physical[0] == 'FW_E':
                    x = physical[1]+row['pos']
                elif row['link'] == 10483:
                    x = source_x+row['pos']
                else:
                    raise AssertionError(('unexpected pre-exit path',vid,arm,row))
                points.append(dict(row,x=x,cell=bisect.bisect_right(bounds,x)-1))
            assert points[0]['t'] == 2700.1 and points[0]['x'] < sign_x[0]
            assert all(b['t']-a['t'] <= 5.000001 for a,b in zip(points,points[1:]))
            assert 0 <= end-points[-1]['t'] <= 5.000001
            event = dict(t=end,x=source_x+1.)  # native MER is 1m inside connector
            path = points+[event]
            crossings = [dict(label='start',lo=2700.1,hi=2700.1,estimate=2700.1)]
            for label, x in thresholds:
                matches = [(a,b) for a,b in zip(path,path[1:]) if a['x'] < x <= b['x']]
                assert len(matches) == 1, (vid,arm,label,len(matches))
                a,b = matches[0]
                crossings.append(dict(label=label,chain_m=x,lo=a['t'],hi=b['t'],
                    estimate=a['t']+(b['t']-a['t'])*(x-a['x'])/(b['x']-a['x'])))
            crossings.append(dict(label='10483_detector_1m',lo=end,hi=end,estimate=end))
            # Same-link endpoint changes only; 5s samples miss intervening changes.
            lane_changes = [dict(time_lo=a['t'],time_hi=b['t'],x=b['x'],old=a['lane'],new=b['lane'])
                for a,b in zip(points,points[1:]) if a['link']==b['link'] and a['lane']!=b['lane']]
            dwell = {k: sum(5. for a,b in zip(points,points[1:])
                if a['speed']<k and b['speed']<k) for k in (5,20,40)}
            results[str(vid)][arm] = dict(crossings=crossings,same_link_net_lane_changes=lane_changes,
                both_endpoint_low_speed_intervals_s=dwell,final_mainline_sample=next(p for p in reversed(points) if p['link']!=10483))
    zones=[]
    labels=[c['label'] for c in results[str(next(iter(witnesses)))]['release']['crossings']]
    for j in range(1,len(labels)):
        deltas=[]; durations={'release':[],'release_vsl90':[]}; arrivals=[]; lower=[]; upper=[]
        for pair in results.values():
            for arm in durations:
                cc=pair[arm]['crossings'];durations[arm].append(cc[j]['estimate']-cc[j-1]['estimate'])
            deltas.append(durations['release_vsl90'][-1]-durations['release'][-1])
            base=pair['release']['crossings'][j]; vsl=pair['release_vsl90']['crossings'][j]
            arrivals.append(vsl['estimate']-base['estimate']);lower.append(vsl['lo']-base['hi']);upper.append(vsl['hi']-base['lo'])
        zones.append(dict(segment=f'{labels[j-1]} -> {labels[j]}',n=len(deltas),
            mean_duration_s={a:statistics.mean(v) for a,v in durations.items()},mean_delta_duration_s=statistics.mean(deltas),
            median_delta_duration_s=statistics.median(deltas),mean_delta_arrival_s=statistics.mean(arrivals),
            mean_delta_arrival_bracket_s=[statistics.mean(lower),statistics.mean(upper)]))
    exact=statistics.mean(w['vsl_time']-w['baseline_time'] for w in witnesses.values())
    assert abs(math.fsum(z['mean_delta_duration_s'] for z in zones)-exact)<1e-9
    for name,sha in protocol['protected_sha256'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==sha,name
    assessment=dict(status='complete_diagnostic_not_gain_qualification',vehicles=84,seed=67,
        exact_mean_exit_delta_s=exact,segments=zones,paired=results,source_pins=PINS,
        limits=protocol['limits'],physics_unchanged=True,native_runs=0,forecasts=0,fits=0)
    (dest/'assessment.json').write_text(json.dumps(assessment,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(exact_mean_exit_delta_s=exact,segments=zones),ensure_ascii=False,indent=2))


def assess_state_information92():
    """Held-out diagnostic of extra current-state information, not a plant."""
    import math
    import numpy as np
    dest=REVIEW/'state_information92';protocol=read(dest/'protocol.json')
    assert not (dest/'assessment.json').exists()
    geo=read(I/'selected/port_gain/geometry.json')
    geometry={c['cell']:c for c in geo['cells'] if c['road']=='FW_E'}
    for path,sha in protocol['protected_sha256'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==sha,path
    rows=[];excluded={}
    for case,pin in protocol['inputs'].items():
        path=Path(pin['path']);assert hashlib.sha256(path.read_bytes()).hexdigest()==pin['sha256']
        doc=read(path);assert doc['fields'][:4]==['cell','speed_kmh','x_m','lane']
        frames={round(float(t)-.1):f for t,f in doc['frames'].items()};stats={}
        for t,frame in frames.items():
            grouped={c:[] for c in range(18,22)}
            for v in frame.values():
                if v[0] in grouped:grouped[v[0]].append(v)
            stats[t]={}
            for c,values in grouped.items():
                g=geometry[c];n=len(values)
                if not n:continue
                speeds=np.array([v[1] for v in values]);vmean=float(speeds.mean())
                lanes=g['canonical_segment_lanes'];length=g['length_km']
                lane_values=[[v[1] for v in values if v[3]==lane] for lane in range(1,lanes+1)]
                assert sum(map(len,lane_values))==n
                within_lane=math.fsum(len(vs)*(sum(vs)/len(vs)-vmean)**2 for vs in lane_values if vs)/n
                half=(g['start_m']+g['end_m'])/2
                front=[v[1] for v in values if v[2]>=half];back=[v[1] for v in values if v[2]<half]
                # Undefined contrast carries no invented head/tail speed.
                contrast=(sum(front)/len(front)-sum(back)/len(back)) if front and back else 0.
                stats[t][c]=dict(n=n,rho=n/(length*lanes),v=vmean,
                    extra=[float(speeds.std()),float(np.std([len(vs)/length for vs in lane_values])),
                        math.sqrt(within_lane),contrast,
                        float(np.mean([(v[2]-g['start_m'])/(g['end_m']-g['start_m']) for v in values])),
                        float(np.mean(speeds<20)),float(np.mean(speeds<5))],empty_half=not(front and back))
        excluded[case]=dict(time_edges=0,sparse=0,empty_half_zero_contrast=0)
        for t in sorted(frames):
            for c in protocol['cells']:
                if t-5 not in stats or t+30 not in stats:
                    excluded[case]['time_edges']+=1;continue
                if any(k not in stats[t] for k in (c-1,c,c+1)) or c not in stats[t-5] or c not in stats[t+30]:
                    excluded[case]['sparse']+=1;continue
                up,own,dn=(stats[t][k] for k in (c-1,c,c+1))
                if own['n']<9 or min(up['n'],dn['n'])<3:
                    excluded[case]['sparse']+=1;continue
                lag=stats[t-5][c];target=stats[t+30][c]['v']-own['v']
                x=[up['rho'],up['v'],own['rho'],own['v'],dn['rho'],dn['v'],
                   own['rho']**2,own['rho']*own['v'],own['rho']-lag['rho'],own['v']-lag['v']]
                assert len(x)==len(protocol['macro_features']) and len(own['extra'])==len(protocol['extra_features'])
                excluded[case]['empty_half_zero_contrast']+=int(own['empty_half'])
                rows.append(dict(case=case,seed=int(case.split('_')[0]),cell=c,time_sec=t+.1,
                    latest_feature_sec=t+.1,label_sec=t+30.1,macro=x,extra=own['extra'],
                    current_speed=own['v'],actual_delta_speed=target))
    coefficients={}
    for c in protocol['cells']:
        train=[r for r in rows if r['seed']==29 and r['cell']==c]
        assert len(train)>40
        for name in ('macro','augmented'):
            vector=lambda r:r['macro']+(r['extra'] if name=='augmented' else [])
            x=np.asarray([vector(r) for r in train],dtype=float);y=np.asarray([r['actual_delta_speed'] for r in train])
            center=x.mean(axis=0);scale=x.std(axis=0);scale[scale<1e-12]=1.
            z=np.column_stack((np.ones(len(x)),(x-center)/scale))
            penalty=np.eye(z.shape[1]);penalty[0,0]=0.
            beta=np.linalg.solve(z.T@z+penalty,z.T@y)
            coefficients[f'{c}_{name}']=dict(train_rows=len(train),center=center.tolist(),scale=scale.tolist(),beta=beta.tolist())
            for r in rows:
                if r['cell']!=c:continue
                features=(np.asarray(vector(r))-center)/scale
                r['prediction_'+name]=float(beta[0]+features@beta[1:])
                assert r['latest_feature_sec']<r['label_sec']
    def score(group):
        return dict(n=len(group),**{name:dict(
            rmse=math.sqrt(math.fsum((r.get('prediction_'+name,0.)-r['actual_delta_speed'])**2 for r in group)/len(group)),
            mae=math.fsum(abs(r.get('prediction_'+name,0.)-r['actual_delta_speed']) for r in group)/len(group),
            negative_speed_predictions=sum(r['current_speed']+r.get('prediction_'+name,0.)<0 for r in group))
            for name in ('persistence','macro','augmented')})
    cases={case:score([r for r in rows if r['case']==case]) for case in protocol['inputs']}
    seeds={str(s):score([r for r in rows if r['seed']==s]) for s in (29,43,67)}
    improvements={s:{name:1-score_['augmented']['rmse']/score_[name]['rmse']
        for name in ('macro','persistence')} for s,score_ in seeds.items()}
    passes=all(improvements[str(s)][name]>=.1 for s in (43,67) for name in ('macro','persistence'))
    passes=passes and all(v['augmented']['rmse']<=1.1*v['macro']['rmse'] for k,v in cases.items() if not k.startswith('29_'))
    out=dict(status='COMPLETE_STATE_INFORMATION_DIAGNOSTIC',passes_predeclared_information_gate=passes,
        cases=cases,seeds=seeds,rmse_reductions=improvements,excluded=excluded,
        coefficients=coefficients,inputs_sha256=PINS,limitations=protocol['limitations'],
        plant_adopted=False,plant_fits=0,diagnostic_regression_fits=4,native_runs=0,autonomous_forecasts=0)
    (dest/'rows.json.gz').write_bytes(gzip.compress(json.dumps(rows,allow_nan=False).encode('utf-8')))
    (dest/'assessment.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(cases=cases,seeds=seeds,rmse_reductions=improvements,passes=passes),indent=2))


if __name__ == '__main__':
    import sys
    if '--state-information92' in sys.argv:
        assess_state_information92()
    elif '--approach10483-90' in sys.argv:
        assess_approach10483_90()
    elif '--current-destination-snapshots86' in sys.argv:
        assess_current_destination_snapshots()
    elif '--destination-speed86' in sys.argv:
        assess_destination_speed()
    else:
        main()
