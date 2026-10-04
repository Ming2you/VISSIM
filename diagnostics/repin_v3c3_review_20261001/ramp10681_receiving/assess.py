"""Native lane evidence and bounded local replay, never a control forecast.

Future native arrivals and frozen predicted receiving budgets below are explicitly
conditional diagnostics. No full-network TTT or autonomous gain is inferred.
"""
import copy
import gzip
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
I = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'
sys.path.insert(0, str(ROOT))
from evaluation.controllers import obs150_contract as oc
from evaluation.controllers.physical_ramp_boundary import LaneResolvedRampBoundary

PINS = {}


def read(path):
    content = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(content).hexdigest()
    return json.loads(gzip.decompress(content) if path.suffix == '.gz' else content)


def native(arm, audit, head_position):
    windows, arrival_events, heads, past_arrivals = [], [], [], defaultdict(list)
    for path in sorted(Path(p) for p in audit['input_sha256'] if arm in Path(p).parts):
        raw = read(path)
        assert PINS[str(path)] == audit['input_sha256'][str(path)]
        bundle = oc.load_bundle(raw)
        detectors, _ = oc.read_detector_csv(bundle.obs['detector_config']['path'],
                                             bundle.obs['detector_config']['sha256'])
        assigned = oc.assign_window(bundle.obs, bundle.mer_rows)
        incoming, crossing = [], []
        for d in detectors:
            if d.link != 10681 or d.role not in ('meter_head', 'ramp_arrival'):
                continue
            assert assigned.tails[d.dcp_no] == 0
            for row in assigned.entries[d.dcp_no]:
                event = dict(veh=row.veh, time=row.t_entry, lane=d.lane)
                (crossing if d.role == 'meter_head' else incoming).append(event)
        for event in incoming:
            past_arrivals[event['veh']].append(event)
        end = raw['sim_sec']
        def stocks(frame):
            return {stage: [sum(v[1] == 10681 and v[2] == lane and
                              ((v[3] < head_position) == (stage == 'pre'))
                              for v in frame['vehicles']) for lane in (1, 2)]
                    for stage in ('pre', 'post')}
        if end == 2700:
            initial = {v[0]: v for v in bundle.frame_end['vehicles'] if v[1] == 10681}
            continue
        assert end in (2850, 3000, 3150)
        h = [sum(e['lane'] == lane for e in crossing) for lane in (1, 2)]
        a = [sum(e['lane'] == lane for e in incoming) for lane in (1, 2)]
        before, after = stocks(bundle.frame_start), stocks(bundle.frame_end)
        observed = audit['arms'][arm]['RM_C10681']['actual']['windows'][len(windows)]
        assert sum(a) == observed['arrival'] and sum(h) == observed['head']
        assert observed['removals'] == 0
        # This includes net lateral outflow; it is NOT lane-specific merging.
        merge_plus_lateral = [h[j]+before['post'][j]-after['post'][j] for j in (0, 1)]
        assert sum(merge_plus_lateral) == observed['merge']
        windows.append(dict(start_sec=end-150, end_sec=end, arrival_by_lane=a,
            head_by_lane=h, start_stock=before, end_stock=after,
            merge_plus_net_posthead_lateral_outflow=merge_plus_lateral,
            total_merge=observed['merge']))
        arrival_events.extend(incoming)
        heads.extend(crossing)
    pairs, unknown = [], []
    for event in heads:
        possible = [e for e in past_arrivals[event['veh']] if e['time'] <= event['time']]
        if possible:
            a = max(possible, key=lambda e: e['time'])
            pairs.append(dict(veh=event['veh'], arrival_lane=a['lane'], head_lane=event['lane'],
                              arrival_sec=a['time'], head_sec=event['time']))
        elif event['veh'] not in initial:
            unknown.append(event)
    return dict(windows=windows, arrival_events=arrival_events, head_events=heads,
                completed_arrival_head_pairs=pairs, unmatched_heads=unknown,
                pair_lane_counts=dict(Counter(f"{p['arrival_lane']}->{p['head_lane']}" for p in pairs)))


def buffer_from(trace):
    meta = trace['initial_buffer']
    fields = ('connector_id', 'length_m', 'head_position_m', 'lanes', 'spacing_m',
              'travel_speed_kmh', 'initial_cohorts', 'lane_arrival_shares')
    args = {k: meta[k] for k in fields}
    if 'posthead_travel_speed_kmh' in meta:
        args['posthead_travel_speed_kmh'] = meta['posthead_travel_speed_kmh']
    assert meta['lane_exchange'] == 'None; independent lane FIFO inventories'
    return LaneResolvedRampBoundary(time_sec=trace['start_sec'], **args)


def replay(trace, observed, mode):
    buffer = buffer_from(trace)
    arrivals = defaultdict(lambda: [0., 0.])
    if mode == 'baseline':
        for row in trace['transfers']:
            if row['target'] == 'ramp:RM_C10681':
                for lane, share in enumerate(buffer.lane_arrival_shares):
                    arrivals[row['start_sec']][lane] += row['vehicles']*share
    else:
        for event in observed['arrival_events']:
            second = math.floor(event['time'])
            assert trace['start_sec'] <= second < trace['end_sec']
            if mode == 'native_arrival_timing':
                for lane, share in enumerate(buffer.lane_arrival_shares):
                    arrivals[second][lane] += share
            else:
                assert mode == 'native_arrival_timing_and_lane'
                arrivals[second][event['lane']-1] += 1.
    backlog = [0., 0.]
    windows, rows, max_difference = [], [], 0.
    for saved in trace['lane_interval_receipts']:
        args = saved['arguments']
        t = args['start_sec']
        assert args['request_arrivals_veh'] == 0
        if t in (2700, 2850, 3000):
            start_stock = [b.snapshot() for b in buffer._lane_buffers]
        result = buffer.advance_local_interval(**args)
        if mode == 'baseline':
            def difference(a, b):
                if isinstance(a, dict):
                    assert a.keys() == b.keys()
                    return max((difference(a[k], b[k]) for k in a), default=0.)
                if isinstance(a, (list, tuple)):
                    assert len(a) == len(b)
                    return max((difference(x, y) for x, y in zip(a, b)), default=0.)
                if isinstance(a, (int, float)):
                    return abs(a-b)
                assert a == b
                return 0.
            max_difference = max(max_difference, difference(result, saved['receipt']))
        for j, lane in enumerate(buffer._lane_buffers):
            backlog[j] += arrivals[t][j]
            accepted = min(backlog[j], lane.current_admission_space())
            lane.admit_current(accepted)
            backlog[j] -= accepted
        rows.append(result)
        if t+1 in (2850, 3000, 3150):
            end_stock = [b.snapshot() for b in buffer._lane_buffers]
            selected = rows[-150:]
            windows.append(dict(start_sec=t-149, end_sec=t+1,
                start_stock=start_stock, end_stock=end_stock,
                merge_by_lane=[sum(r['lane_receipts'][j]['accepted_merge_veh'] for r in selected) for j in (0, 1)],
                head_by_lane=[sum(r['lane_receipts'][j]['head_service_veh'] for r in selected) for j in (0, 1)],
                receiving_by_lane=[sum(r['lane_receipts'][j]['receiving_budget_veh'] for r in selected) for j in (0, 1)],
                eligible_stock_exposure_by_lane=[sum(r['lane_receipts'][j]['eligible_merge_veh'] for r in selected) for j in (0, 1)],
                upstream_backlog=list(backlog)))
    if mode == 'baseline':
        assert max_difference < 1e-8, max_difference
    ending = buffer.snapshot()
    requested = sum(sum(v) for v in arrivals.values())
    merged = sum(r['accepted_merge_veh'] for r in rows)
    balance = trace['initial_stock']['connector_veh']+requested-merged-ending['connector_veh']-sum(backlog)
    assert abs(balance) < 1e-8, balance
    return dict(mode=mode, conditional_only=True, full_network_gain_claimed=False,
        future_native_arrivals=mode != 'baseline', receiving_feedback_frozen=True,
        requested=requested, head=sum(r['head_service_veh'] for r in rows), merge=merged,
        final_stock=ending, upstream_backlog=backlog, balance_residual=balance,
        max_baseline_receipt_difference=max_difference, windows=windows)


def main():
    protocol = json.loads((HERE/'protocol.json').read_bytes())
    for p, pin in protocol['production_pins'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == pin
    audit = read(I/'closedloop_recorded2700_native_selected_sc1001_corrected47/analysis/ramp_response_audit.json')
    before = I/'closedloop_recorded2700_select_check_trace10681_sc105_native_choice47'
    after = I/'closedloop_recorded2700_select_check_trace10681_lane_receiving47_v2'
    config = read(HERE.parent/'sc105_supply/candidate_config.json')
    manifest = read(ROOT/config['freeway']['lane_plant'])
    reference = read(ROOT/manifest['sources']['reference_config']['path'])
    assert PINS[str(ROOT/manifest['sources']['reference_config']['path'])] == manifest['sources']['reference_config']['sha256']
    assert manifest['lane_groups'] is False
    result = dict(status='conditional_diagnosis_not_gain_qualified', previous_goal_turn='no_progress',
        full_forecasts=2, new_native_runs=0, fit=0, input_sha256=PINS, arms={},
        limits=['Native ramp entry detectors are at1m, with events binned to model1s; not exact0m arrival times.',
                'Per-lane native merging is not identified from150s frames: lateral posthead transfers remain unknown.',
                'Frozen model receiving is a conditional component test, not a self-consistent candidate or TTT gain.',
                'Native head pairs contain completed trips only; future arrivals never enter autonomous predictions.'])
    for name, arm in (('held_actual', 'hold'), ('selected', 'selected')):
        old, new = read(before/(name+'.json')), read(after/(name+'.json'))
        old.pop('wall_sec'); wall = new.pop('wall_sec'); assert old == new
        filename = name+'_RM_C10681_trace.json.gz'
        trace, original = read(after/filename), read(before/filename)
        stripped = {k: v for k, v in trace.items() if k not in ('lane_runtime', 'lane_interval_receipts')}
        assert stripped == original
        assert len(trace['lane_interval_receipts']) == 450
        assert trace['lane_runtime']['mainline_lane_mapping'] is None
        assert trace['lane_runtime']['receiving_node'] == reference['freeway']['physical_ramp_receiving_nodes']['RM_C10681']
        for sample in trace['lane_interval_receipts']:
            assert 'receiving_budget_by_lane_veh' not in sample['arguments']
            assert abs(sum(r['accepted_merge_veh'] for r in sample['receipt']['lane_receipts'])
                       - sample['receipt']['accepted_merge_veh']) < 1e-10
            assert all(r['receiving_budget_veh'] == sample['arguments']['receiving_budget_veh']/2
                       for r in sample['receipt']['lane_receipts'])
        actual = native(arm, audit, trace['initial_buffer']['head_position_m'])
        cases = {mode: replay(trace, actual, mode) for mode in
                 ('baseline', 'native_arrival_timing', 'native_arrival_timing_and_lane')}
        posthead = {mode: posthead_replay(trace, actual, mode) for mode in ('model_head', 'native_head')}
        result['arms'][name] = dict(full_forecast_wall_sec=wall, full_output_exact=True,
            actual_runtime=trace['lane_runtime'], actual=actual, local=cases, posthead=posthead)
    result['configuration_authority'] = dict(manifest_path=config['freeway']['lane_plant'],
        lane_groups=False, reference_config=manifest['sources']['reference_config'],
        inactive_outer_config_lane_mapping=config['freeway']['physical_ramp_lane_coupling'],
        explanation='The v2 loader takes freeway physics from the pinned reference and rejects lane-group features. Outer config entries do not describe installed lane coupling.')
    (HERE/'assessment.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({arm: {mode: {k: v for k, v in row.items() if k in
        ('head', 'merge', 'requested', 'upstream_backlog', 'max_baseline_receipt_difference')}
        for mode, row in data['local'].items()} for arm, data in result['arms'].items()}, indent=2))


def posthead_replay(trace, observed, mode):
    """Posthead conservation with known transfers, frozen budget, no lane exchange.

    The model-head case must reproduce every original merge/posthead stock before
    using future native head counts to isolate this component. No upstream cost
    or feasible whole-network control is inferred from this diagnostic.
    """
    meta = trace['initial_buffer']
    nominal = meta.get('posthead_travel_speed_kmh', meta['travel_speed_kmh'])/3.6
    travel = (meta['length_m']-meta['head_position_m'])/nominal
    initial = [[(trace['start_sec']+(meta['length_m']-pos)/nominal, 1.)
                for pos, speed, lane in meta['initial_cohorts']
                if lane == j+1 and pos >= meta['head_position_m']] for j in (0, 1)]
    cohorts = copy.deepcopy(initial)
    ready = [0., 0.]
    events = defaultdict(lambda: [0., 0.])
    if mode == 'native_head':
        for e in observed['head_events']:
            events[math.floor(e['time'])][e['lane']-1] += 1.
    total, windows, rows, error, admitted = [0., 0.], [], [], 0., [0., 0.]
    for saved in trace['lane_interval_receipts']:
        t = saved['arguments']['start_sec']
        assert 'posthead_speed_kmh' not in saved['arguments']
        merges = []
        for j in (0, 1):
            lane = saved['receipt']['lane_receipts'][j]
            ready[j] += sum(n for eta, n in cohorts[j] if eta <= t+1)
            cohorts[j] = [(eta, n) for eta, n in cohorts[j] if eta > t+1]
            flow = min(ready[j], lane['receiving_budget_veh'])
            ready[j] -= flow
            total[j] += flow
            merges.append(flow)
            head = lane['head_service_veh'] if mode == 'model_head' else events[t][j]
            admitted[j] += head
            if head:
                cohorts[j].append((t+1+travel, head))
            stock = ready[j]+sum(n for eta, n in cohorts[j])
            if mode == 'model_head':
                error = max(error, abs(flow-lane['accepted_merge_veh']),
                    abs(stock-lane['end']['merge_ready_veh']-lane['end']['downstream_travelling_veh']))
            assert abs(len(initial[j])+admitted[j]-total[j]-stock) < 1e-8
        rows.append(merges)
        if t+1 in (2850, 3000, 3150):
            windows.append(dict(start_sec=t-149, merge_by_lane=[sum(r[j] for r in rows[-150:]) for j in (0, 1)],
                post_stock_by_lane=[ready[j]+sum(n for eta, n in cohorts[j]) for j in (0, 1)]))
    assert error < 1e-8, error
    return dict(mode=mode, conditional_only=True, future_native_head=mode == 'native_head',
        head_by_lane=admitted, merge_by_lane=total, merge=sum(total), windows=windows,
        max_model_head_parity_error=error,
        limitations='Frozen predicted receiving; no feedback, no inferred native lateral flow, not autonomous gain validation')


if __name__ == '__main__':
    main()
