"""Four local cause-isolation replays, not autonomous gain validation.

Reuse the REVIEW226 lane-buffer diagnostic with dynamic window bounds and the
current predicted post-head speed cap. Native future events enter only these
explicitly conditional local replays. No coefficient fitting or network rollout.
"""
import copy
import gzip
import hashlib
import importlib.util
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE/'component10681_v2'
sys.path.insert(0, str(ROOT))
from evaluation.controllers import obs150_contract as oc

PINS = {}
def read(path):
    data = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(data).hexdigest()
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)

def save(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf8')

def native(arm, audit, trace):
    selected = arm == 'selected'
    paths = [Path(p) for p in audit['input_sha256'] if ('selected' in Path(p).parts) == selected]
    assert len(paths) == 4
    head_position = trace['initial_buffer']['head_position_m']
    def stocks(frame):
        return {stage: [sum(v[1] == 10681 and v[2] == lane and
                            ((v[3] < head_position) == (stage == 'pre'))
                            for v in frame['vehicles']) for lane in (1, 2)]
                for stage in ('pre', 'post')}
    result = dict(windows=[], arrival_events=[], head_events=[])
    for path in sorted(paths):
        raw = read(path)
        assert PINS[str(path)] == audit['input_sha256'][str(path)]
        bundle = oc.load_bundle(raw)
        end = raw['sim_sec']
        if end == trace['start_sec']:
            result['initial_stock'] = stocks(bundle.frame_end)
            continue
        assert end in range(trace['start_sec']+150, trace['end_sec']+1, 150)
        detectors, _ = oc.read_detector_csv(bundle.obs['detector_config']['path'],
                                             bundle.obs['detector_config']['sha256'])
        assigned = oc.assign_window(bundle.obs, bundle.mer_rows)
        incoming, heads = [], []
        for d in detectors:
            if d.link != 10681 or d.role not in ('meter_head', 'ramp_arrival'):
                continue
            assert assigned.tails[d.dcp_no] == 0
            for row in assigned.entries[d.dcp_no]:
                event = dict(veh=row.veh, time=row.t_entry, lane=d.lane)
                (heads if d.role == 'meter_head' else incoming).append(event)
        h = [sum(e['lane'] == lane for e in heads) for lane in (1, 2)]
        a = [sum(e['lane'] == lane for e in incoming) for lane in (1, 2)]
        before, after = stocks(bundle.frame_start), stocks(bundle.frame_end)
        observed = audit['arms'][arm]['RM_C10681']['actual']['windows'][len(result['windows'])]
        assert sum(h) == observed['head']
        assert observed['removals'] == 0
        # Lateral moves are not observed between snapshots; only sum is merge.
        merge_plus_lateral = [h[j]+before['post'][j]-after['post'][j] for j in (0, 1)]
        assert sum(merge_plus_lateral) == observed['merge']
        result['windows'].append(dict(start_sec=end-150, end_sec=end, arrival_by_lane=a,
            audited_connector_entries=observed['arrival'],
            detector_minus_boundary_entries=sum(a)-observed['arrival'],
            head_by_lane=h, start_stock=before, end_stock=after, total_merge=observed['merge'],
            merge_plus_net_posthead_lateral_outflow=merge_plus_lateral))
        result['arrival_events'].extend(incoming)
        result['head_events'].extend(heads)
    assert len(result['windows']) == 3
    # The entry detector is at1m, not the link boundary. A crossing can fall in
    # the adjacent150s window. Preserve this discrepancy; require the complete
    #450s count to agree rather than silently relabeling detector timestamps.
    assert len(result['arrival_events']) == audit['arms'][arm]['RM_C10681']['actual']['arrival']
    return result

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

def replay(trace, observed, mode, buffer_from):
    buffer = buffer_from(trace)
    arrivals = defaultdict(lambda: [0., 0.])
    if mode == 'baseline':
        for row in trace['transfers']:
            if row['target'] == 'ramp:RM_C10681':
                for lane, share in enumerate(buffer.lane_arrival_shares):
                    arrivals[row['start_sec']][lane] += row['vehicles']*share
    else:
        assert mode == 'native_arrival_timing_and_lane'
        for e in observed['arrival_events']:
            arrivals[math.floor(e['time'])][e['lane']-1] += 1.
    backlog, windows, rows, error = [0., 0.], [], [], 0.
    for saved in trace['lane_interval_receipts']:
        args = saved['arguments']; t = args['start_sec']
        assert args['request_arrivals_veh'] == 0
        row = buffer.advance_local_interval(**args)
        if mode == 'baseline':
            error = max(error, difference(row, saved['receipt']))
        for j, lane in enumerate(buffer._lane_buffers):
            backlog[j] += arrivals[t][j]
            accepted = min(backlog[j], lane.current_admission_space())
            lane.admit_current(accepted); backlog[j] -= accepted
        rows.append(row)
        if (t+1-trace['start_sec']) % 150 == 0:
            windows.append(dict(start_sec=t-149, end_sec=t+1,
                head_by_lane=[sum(r['lane_receipts'][j]['head_service_veh'] for r in rows[-150:]) for j in (0, 1)],
                merge_by_lane=[sum(r['lane_receipts'][j]['accepted_merge_veh'] for r in rows[-150:]) for j in (0, 1)],
                end_stock=[b.snapshot() for b in buffer._lane_buffers], upstream_backlog=list(backlog)))
    assert error < 1e-8, error
    ending = buffer.snapshot(); requested = sum(map(sum, arrivals.values()))
    merged = sum(r['accepted_merge_veh'] for r in rows)
    balance = trace['initial_stock']['connector_veh']+requested-merged-ending['connector_veh']-sum(backlog)
    assert abs(balance) < 1e-8, balance
    return dict(conditional_only=True, future_native_arrivals=mode != 'baseline',
        requested=requested, head=sum(r['head_service_veh'] for r in rows), merge=merged,
        final_stock=ending, upstream_backlog=backlog, conservation_residual=balance,
        baseline_receipt_error=error, windows=windows)

def posthead(trace, observed, mode):
    meta = trace['initial_buffer']; speed = meta.get('posthead_travel_speed_kmh', meta['travel_speed_kmh'])
    travel = (meta['length_m']-meta['head_position_m'])/(speed/3.6)
    cohorts = [[(trace['start_sec']+(meta['length_m']-pos)/(speed/3.6), 1.)
                for pos, _, lane in meta['initial_cohorts']
                if lane == j+1 and pos >= meta['head_position_m']] for j in (0, 1)]
    initial = [sum(n for _, n in rows) for rows in cohorts]
    ready, total, admitted = [0., 0.], [0., 0.], [0., 0.]
    events = defaultdict(lambda: [0., 0.])
    if mode == 'native_head':
        for e in observed['head_events']:
            events[math.floor(e['time'])][e['lane']-1] += 1.
    else:
        assert mode == 'model_head'
    rows, windows, error, balance_error = [], [], 0., 0.
    for saved in trace['lane_interval_receipts']:
        args = saved['arguments']; t = args['start_sec']; flows = []
        assert args['duration_sec'] == 1
        delay = 1.-args.get('posthead_speed_kmh', speed)/speed
        for j in (0, 1):
            lane = saved['receipt']['lane_receipts'][j]
            moving = [(eta+delay, n) for eta, n in cohorts[j]]
            ready[j] += sum(n for eta, n in moving if eta <= t+1)
            cohorts[j] = [(eta, n) for eta, n in moving if eta > t+1]
            flow = min(ready[j], lane['receiving_budget_veh'])
            ready[j] -= flow; total[j] += flow; flows.append(flow)
            head = lane['head_service_veh'] if mode == 'model_head' else events[t][j]
            admitted[j] += head
            if head: cohorts[j].append((t+1+travel, head))
            stock = ready[j]+sum(n for _, n in cohorts[j])
            balance_error = max(balance_error, abs(initial[j]+admitted[j]-total[j]-stock))
            if mode == 'model_head':
                error = max(error, abs(flow-lane['accepted_merge_veh']),
                    abs(stock-lane['end']['merge_ready_veh']-lane['end']['downstream_travelling_veh']))
        rows.append(flows)
        if (t+1-trace['start_sec']) % 150 == 0:
            windows.append(dict(start_sec=t-149, end_sec=t+1,
                merge_by_lane=[sum(r[j] for r in rows[-150:]) for j in (0, 1)],
                post_stock_by_lane=[ready[j]+sum(n for _, n in cohorts[j]) for j in (0, 1)]))
    assert error < 1e-8 and balance_error < 1e-8, (error, balance_error)
    return dict(conditional_only=True, future_native_head=mode == 'native_head',
        head_by_lane=admitted, merge_by_lane=total, merge=sum(total), windows=windows,
        baseline_receipt_error=error, conservation_residual=balance_error)

def main():
    assert not (OUT/'assessment.json').exists(), 'Do not repeat a completed component diagnosis'
    assert read(OUT/'trace_completion.json')['outputs_equal_to_prior']
    plan = read(OUT/'plan.json')
    for p, h in plan['source_pins'].items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest() == h, p
    old_path = HERE.parent/'ramp10681_receiving/assess.py'
    PINS[str(old_path)] = hashlib.sha256(old_path.read_bytes()).hexdigest()
    spec = importlib.util.spec_from_file_location('prior_lane_diagnosis', old_path)
    previous = importlib.util.module_from_spec(spec); spec.loader.exec_module(previous)
    audit = read(HERE.parent/'rm_restart219/native238/analysis/ramp_response_audit.json')
    traces = {arm: read(OUT/(arm+'_trace.json.gz')) for arm in ('hold', 'selected')}
    actual = {arm: native(arm, audit, traces[arm]) for arm in traces}
    assert actual['hold']['initial_stock'] == actual['selected']['initial_stock']
    trace = traces['selected']; observed = actual['selected']
    local = {mode: replay(trace, observed, mode, previous.buffer_from)
             for mode in ('baseline', 'native_arrival_timing_and_lane')}
    downstream = {mode: posthead(trace, observed, mode) for mode in ('model_head', 'native_head')}
    result = dict(status='conditional_component_diagnosis', input_sha256=PINS,
        actual=actual, local=local, posthead=downstream, conditional_replays=4,
        new_network_predictions=0, new_native_runs=0, coefficient_fits=0,
        limitations=['Future native arrival/head events used only for cause isolation, not autonomous prediction or TTT gain.',
            'Predicted receiving and merge-cell speed are frozen; this is not a self-consistent whole-network counterfactual.',
            'Per-lane merge plus lateral outflow cannot separate lane changing from merging with150s snapshots.',
            'Arrival detectors at1m shift one entry between adjacent windows; full450s count agrees with boundary audit.',
            'Historical hold0s is outside the current2s minimum; inherited releaseNUFcap is violated.'])
    save(OUT/'assessment.json', result)
    print(json.dumps(dict(local={k:{f:v[f] for f in ('requested','head','merge')} for k,v in local.items()},
                          posthead={k:v['merge'] for k,v in downstream.items()}), indent=2))

if __name__ == '__main__': main()
