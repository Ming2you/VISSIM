"""Audit closed 2400--2850 replays using the canonical obs150 boundaries.

No rollout, fitting, FZP rescan or live-process interaction. Require the native
execution/common-history proof before comparing the previously frozen forecast.
"""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from evaluation.controllers import obs150_contract as oc
from evaluation.controllers.obs150_observation import check_rule_crosscheck

RUNS = Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29')
OUT = HERE / 'native2400_analysis'
PROTOCOL = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926/native_urbanrm269_2400/protocol.json'
PHYSICAL_GROUPS = {'approach52_with58': (52, 58), 'approach66': (66,),
                   'shared_W_out': (68, 121, 10625, 10629, 10633)}
PINS = {}


def read(path):
    data = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(data).hexdigest()
    return json.loads(data)


def count_link(frame, link):
    assert frame['complete'] and tuple(oc.FRAME_ROW_FIELDS[:4]) == ('veh', 'link', 'lane', 'pos')
    return dict(sorted(Counter(v[2] for v in frame['vehicles'] if v[1] == link).items()))


def ramp_stock(frame, link, head_positions):
    return {side: [sum(v[1] == link and v[2] == lane and
                      ((v[3] < position) == (side == 'pre'))
                      for v in frame['vehicles'])
                   for lane, position in sorted(head_positions.items())]
            for side in ('pre', 'post')}


def grouped_model_stock(stocks, footprints):
    # New gate cohorts on66 are physical stock before they reach its reservoir.
    # They were absent in the initial projection; omitting them biases the
    # comparison even though the global Omega objective already counts them.
    return {group: sum(stocks.get(k, 0.) for k in row['initial_model_stock_keys']) +
            (stocks.get('transit:gate:in_SC1004_S', 0.) if group == 'approach66' else 0.)
            for group, row in footprints.items()}


def ramp_balance(before, after, *, arrival, head_by_lane, removed):
    """Each stock has pre/post lane lists; lateral moves cancel only in sum."""
    stock = lambda row: sum(row['pre']) + sum(row['post'])
    merged = stock(before) + arrival - stock(after) - removed
    assert merged >= 0, 'Negative balance-derived ramp outflow'
    result = dict(arrival=arrival, head=sum(head_by_lane), head_by_lane=head_by_lane,
                  removals=removed, merge=merged, initial_stock=stock(before),
                  final_stock=stock(after), before=before, after=after)
    # The native removal log has no lane/position. Do not assign removals to a
    # post-head lane or call a lateral move an actual merge.
    if removed == 0:
        net = [h + a - b for h, a, b in zip(head_by_lane, before['post'], after['post'])]
        assert sum(net) == merged, 'Head/post-head and whole-ramp balances disagree'
        result['merge_plus_net_posthead_lateral_outflow_by_lane'] = net
    else:
        result['merge_plus_net_posthead_lateral_outflow_by_lane'] = None
    return result


def main():
    target = OUT / 'component_audit.json'
    assert not target.exists(), 'Preserve the completed audit'
    protocol = read(PROTOCOL)
    proof = read(OUT / 'summary.json')
    closure = read(OUT / 'runtime_closure.json')
    assert closure['all_owned_processes_closed'] and closure['owner_exit_code'] == 0
    assert Path(closure['runs_root']).resolve() == RUNS.resolve()
    assert read(PROTOCOL.parent / 'status.json')['stage'] == 'both_native_complete_unanalyzed'
    assert protocol['arms'] == ['hold', 'selected']
    assert (protocol['start_sec'], protocol['end_sec']) == (2400, 2850)
    from qualify_native2400 import validate_scope
    qualification = read(OUT / 'observed_input_qualification.json')
    comparison_scope = validate_scope(proof, qualification)
    for path, digest in qualification['source_pins'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
    assert proof['protocol_sha256'] == PINS[str(PROTOCOL)]
    assert all(proof['arms'][arm]['native_execution_passed'] for arm in protocol['arms'])
    assert not (RUNS / 'STOP').exists()
    prediction_path = HERE / 'selection2400_discrete/summary.json'
    prediction = read(prediction_path)
    context = read(HERE / 'selection2400_discrete_verification.json')
    assert PINS[str(prediction_path)] == context['source_summary_sha256']
    assert context['status'] == 'verified_discrete_model_selection'
    footprint = read(HERE / 'native2400_component_footprint.json')
    assert hashlib.sha256(Path(footprint['source']).read_bytes()).hexdigest() == footprint['sha256']
    predicted_stocks = read(HERE / 'native2400_predicted_stocks.json')
    predicted_ramps = read(HERE / 'native2400_predicted_ramp_components.json')
    assert predicted_stocks['source_pins'] == predicted_ramps['source_pins']
    for path, digest in predicted_stocks['source_pins'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
    report = dict(start_sec=2400, end_sec=2850, arms={}, source_pins=PINS,
                  new_forecasts=0, fits=0, fzp_scans=0, scope=comparison_scope,
                  limitations=[
                      'Merge is balance-derived connector outflow, not the distinct meter-head crossing.',
                      'Per-lane post-head balances include lateral movement; only their sum is merge.',
                      'Physical link counts are total vehicles, not queue length or arrivals.',
                      '52 shares its model approach storage with58; observed grouped stocks are also retained.',
                      'Shared model W_out includes68,121 and connectors; do not compare it with68 alone.',
                      'Local stock comparisons use the documented initial physical support and add66 gate transit; they do not resolve every within-link travel/queue position.',
                      'One previously used seed29 state; not independent-seed or closed-loop qualification.'])
    for arm in protocol['arms']:
        run = RUNS / arm
        assert not (run / 'STOP').exists()
        folder = run / f'decisions_sdmpc31_g_2400_{arm}_s29'
        predicted = prediction['results'][arm]['predicted_merge']
        assert predicted['boundary'] == 'ramp_to_mainline'
        predicted = predicted['accepted_vehicles_by_ramp']
        actual = dict(ramps={r: [] for r in predicted}, physical_link_stocks=[])
        for end in (2400, 2550, 2700, 2850):
            raw = read(folder / f'state_{end:06d}.json')
            assert raw['sim_sec'] == end and raw['vehicle_records']['complete']
            bundle = oc.load_bundle(raw)
            assert len(bundle.frame_end['vehicles']) == raw['vehicle_records']['record_count']
            lanes = {str(link): count_link(bundle.frame_end, link)
                     for links in PHYSICAL_GROUPS.values() for link in links}
            actual['physical_link_stocks'].append(dict(sim_sec=end, lanes_by_link=lanes,
                grouped_total_vehicles={group: sum(sum(lanes[str(link)].values()) for link in links)
                                       for group, links in PHYSICAL_GROUPS.items()}))
            if end == 2400:
                continue
            obs = bundle.obs
            detectors, _ = oc.read_detector_csv(obs['detector_config']['path'], obs['detector_config']['sha256'])
            oc.validate_raw(obs, detectors, expected_simres=oc.EXPECTED_SIMRES)
            check_rule_crosscheck(obs, detectors)
            boundary = oc.evaluate_boundaries(obs, detectors, bundle.frame_end, bundle.frame_start, bundle.err_rows)
            removed = oc.window_removals(bundle.err_rows, end - 150, end)
            for ramp in predicted:
                link = int(ramp.removeprefix('RM_C'))
                heads = sorted((d for d in detectors if d.link == link and d.role == 'meter_head'), key=lambda d: d.lane)
                assert heads and [d.lane for d in heads] == list(range(1, len(heads) + 1))
                positions = {d.lane: d.geometry_assert['head_position_m'] for d in heads}
                row = ramp_balance(ramp_stock(bundle.frame_start, link, positions),
                    ramp_stock(bundle.frame_end, link, positions),
                    arrival=boundary['ramp_arrival:' + ramp].cross,
                    head_by_lane=[boundary[d.boundary_ref].cross for d in heads],
                    removed=sum(int(r['link']) == link for r in removed))
                row.update(start_sec=end - 150, end_sec=end)
                actual['ramps'][ramp].append(row)
        actual['merge_comparison'] = {r: dict(actual=sum(w['merge'] for w in windows),
            predicted=predicted[r], prediction_minus_actual=predicted[r]-sum(w['merge'] for w in windows))
            for r, windows in actual['ramps'].items()}
        for ramp, windows in actual['ramps'].items():
            model_windows = predicted_ramps['arms'][arm][ramp]
            assert len(model_windows) == len(windows) == 3
            assert abs(sum(w['merge'] for w in model_windows) - predicted[ramp]) < 1e-7
            for observed, model in zip(windows, model_windows):
                assert (observed['start_sec'], observed['end_sec']) == (model['start_sec'], model['end_sec'])
                actual_post_change = sum(observed['after']['post']) - sum(observed['before']['post'])
                observed['predicted'] = {k: model[k] for k in ('arrival', 'head', 'merge', 'final_stock', 'posthead_stock_change')}
                observed['prediction_minus_actual'] = {
                    k: model[k] - observed[k] for k in ('arrival', 'head', 'merge', 'final_stock')}
                observed['actual_posthead_stock_change'] = actual_post_change
                observed['prediction_minus_actual']['posthead_stock_change'] = model['posthead_stock_change'] - actual_post_change
                # Native deletions, if any, remain explicit in each observed row;
                # do not attribute their effect to an unknown head/merge lane.
        points = {p['time_sec']: p for p in predicted_stocks['arms'][arm]}
        for row in actual['physical_link_stocks']:
            model = grouped_model_stock(points[row['sim_sec']]['model_stock_veh'], footprint['groups'])
            row['predicted_group_total_vehicles'] = model
            row['prediction_minus_actual_by_group'] = {
                group: model[group] - row['grouped_total_vehicles'][group] for group in model}
            if row['sim_sec'] == 2400:
                assert max(map(abs, row['prediction_minus_actual_by_group'].values())) < 1e-7
        report['arms'][arm] = actual
    mapping = read(ROOT / 'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json')
    freeway_links = {int(link) for row in mapping['freeway_model_links'].values() for link in row['chain_links']}
    physical_groups = {**PHYSICAL_GROUPS, 'ramp10681': (10681,), 'ramp10646': (10646,),
                       'mainline': tuple(freeway_links)}
    all_links = [link for links in physical_groups.values() for link in links]
    assert len(all_links) == len(set(all_links)), 'Cost groups overlap'
    stock_groups = {name: set(row['initial_model_stock_keys']) for name, row in footprint['groups'].items()}
    stock_groups['approach66'].add('transit:gate:in_SC1004_S')
    stock_groups.update(ramp10681={'ramp:RM_C10681'}, ramp10646={'ramp:RM_C10646'})
    native_costs, model_costs = {}, {}
    for arm in protocol['arms']:
        metrics = read(OUT / arm / 'area_metrics.json')
        residence = metrics['physical_link_residence']
        for link in all_links:
            assert residence[str(link)]['inside'], ('Physical group outside Omega', link)
        native_costs[arm] = {name: sum(residence[str(link)]['ttt_veh_h'] for link in links)
                             for name, links in physical_groups.items()}
        native_costs[arm]['remaining_omega'] = metrics['ttt_veh_h'] - sum(native_costs[arm].values())
        native_costs[arm]['omega'] = metrics['ttt_veh_h']
        cost = prediction['results'][arm]['costs_by_stock']
        model_costs[arm] = {name: sum(cost.get(k, 0.) for k in keys) for name, keys in stock_groups.items()}
        model_costs[arm]['mainline'] = sum(v for k, v in cost.items() if k.startswith('freeway:'))
        model_costs[arm]['remaining_omega'] = prediction['results'][arm]['omega_ttt_veh_h'] - sum(model_costs[arm].values())
        model_costs[arm]['omega'] = prediction['results'][arm]['omega_ttt_veh_h']
    delta = lambda rows: {k: rows['selected'][k] - rows['hold'][k] for k in rows['hold']}
    native_delta, model_delta = delta(native_costs), delta(model_costs)
    assert abs(native_delta['omega'] - proof['delta_TTT_veh_h']) < 1e-7
    assert abs(model_delta['omega'] - prediction['delta_omega_ttt_veh_h']) < 1e-7
    report['cost_comparison'] = dict(native_selected_minus_hold_veh_h=native_delta,
        predicted_selected_minus_hold_veh_h=model_delta,
        scope='Native0--2850 difference cancels verified common0--2400 history; compare with model2400--2850 difference only.',
        quadrature='Native5s sampled residence and last-frame tail versus model substep integral; not identical quadrature.',
        interpretation='Joint city/RM response; the shared_W_out decrease is not proof of isolated10681 causation.')
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')
    print(json.dumps({a: r['merge_comparison']['RM_C10681'] for a, r in report['arms'].items()}, indent=2))


if __name__ == '__main__':
    main()
