"""Separate head-service and post-head stock errors without fitting or FZP reads.

The isolated clock check freezes the saved model's receiving budgets and lane
arrival requests. It is a conditional numerical diagnostic, not an autonomous
network prediction or native counterfactual. Native future snapshots are used
only to score the completed forecast, never as replay inputs.
"""
import copy
import gzip
import hashlib
import json
import math
import pickle
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
RESULT = Path('E:/VISSIM_analysis/20261010_rm10681_transfer346')
FORECAST = RESULT / 'forecast4650_v8'
NATIVE = Path('D:/VISSIM_runs/20261005_rm10681_reopen4650_s29/selected/decisions_sdmpc31_g_4650_selected_s29')
AUDIT = ROOT / 'diagnostics/repin_v3c3_review_20261001/rm_restart219/native238/analysis/ramp_response_audit.json'
RAMP = 'RM_C10681'
PINS = {}


def read(path):
    data = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(data).hexdigest()
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)


def replay(initial, rows, dt):
    """Same predicted receiving/arrival envelopes, with one- or five-second clock."""
    lanes = copy.deepcopy(initial._lane_buffers)
    supplies = {int(r['start_sec']): r['available_veh'] for r in rows
                if r['kind'] == 'physical_ramp_merge_physical_receiving' and r['resource'] == RAMP}
    arrivals = {(int(r['end_sec']), int(r['resource'].split(':')[-1])): r['accepted_total_veh']
                for r in rows if r['kind'] == 'known_wout_ramp_lane_receiving' and r['resource'].startswith(RAMP + ':')}
    windows = []
    before = [b.snapshot() for b in lanes]
    for t in range(4650, 5100, dt):
        green = (2, 4, 6)[(t - 4650) // 150]
        supply = supplies[4650 + ((t - 4650) // 5) * 5] * dt / 5
        for i, b in enumerate(lanes):
            args = dict(start_sec=t, duration_sec=dt, cycle_sec=10,
                        receiving_budget_veh=supply / 2, service_veh=green / 2,
                        mode='GREEN', green_sec=green,
                        request_arrivals_veh=arrivals.get((t + dt, i), 0.))
            if dt == 1:
                b.advance_local_interval(**args, allow_partial_cycle=True)
            else:
                b.advance_coarse_interval(**args)
            assert abs(b.snapshot()['conservation_residual_veh']) < 1e-7
        if (t + dt - 4650) % 150 == 0:
            after = [b.snapshot() for b in lanes]
            delta = lambda key: math.fsum(a[key] - z[key] for a, z in zip(after, before))
            windows.append(dict(end=t + dt, head=delta('cumulative_head_service_veh'),
                merge=delta('cumulative_merge_veh'), requests=delta('cumulative_requested_veh'),
                admitted=delta('cumulative_admitted_veh'),
                backlog=math.fsum(a['outside_component_backlog_veh'] for a in after),
                posthead=math.fsum(a['downstream_travelling_veh'] + a['merge_ready_veh'] for a in after)))
            before = after
    return dict(step_sec=dt, windows=windows,
                head=sum(w['head'] for w in windows), merge=sum(w['merge'] for w in windows),
                limitations='Receiving and incoming lane requests frozen from previous model rollout. Upstream feedback is not rerun; unused admissions remain conserved backlog. Not native validation.')


def main():
    out = RESULT / 'head_merge_diagnosis.json'
    assert not out.exists(), 'Reuse completed diagnosis; do not overwrite.'
    raw = (FORECAST / 'initial.pickle').read_bytes()
    PINS[str(FORECAST / 'initial.pickle')] = hashlib.sha256(raw).hexdigest()
    cfg, state, _ = pickle.loads(raw)
    buffer = state.lane_ramp_runtime.buffers[RAMP]
    audit = read(AUDIT)['arms']['selected'][RAMP]['actual']
    response = read(FORECAST / 'selected.response.json.gz')
    rows = response['resource_allocations']
    initial_post = buffer.snapshot()['downstream_travelling_veh'] + buffer.snapshot()['merge_ready_veh']
    assert initial_post == 0 and audit['removals'] == 0
    native_stock = {}
    for t in (4650, 4800, 4950, 5100):
        frame = read(NATIVE / f'lane_observations/frame_{t:06}.json')
        assert frame['complete'] and frame['time_s'] == t
        ramp = [v for v in frame['vehicles'] if v[1] == 10681]
        post = [v for v in ramp if v[3] > buffer.head_position_m]
        native_stock[t] = dict(total=len(ramp), posthead=len(post), prehead=len(ramp) - len(post),
            posthead_mean_speed_kmh=math.fsum(v[4] for v in post) / len(post) if post else None,
            posthead_stopped=sum(v[4] < 1 for v in post),
            posthead_by_lane={str(i): sum(v[2] == i for v in post) for i in (1, 2)})
    model_post = native_post = initial_post
    windows = []
    for i, t in enumerate((4650, 4800, 4950)):
        relevant = [r for r in rows if t <= r['start_sec'] < t + 150 and r['resource'].startswith(RAMP)]
        heads = [r for r in relevant if r['kind'] == 'physical_ramp_head_service']
        merges = [r for r in relevant if r['kind'] == 'physical_ramp_merge_physical_receiving']
        head = math.fsum(r['accepted_total_veh'] for r in heads)
        merge = math.fsum(r['accepted_total_veh'] for r in merges)
        actual = audit['windows'][i]
        model_post += head - merge
        native_post += actual['head'] - actual['merge']
        assert native_post == native_stock[t + 150]['posthead']
        windows.append(dict(start=t, end=t + 150, model_head=head, actual_head=actual['head'],
            model_merge=merge, actual_merge=actual['merge'], model_posthead=model_post,
            actual_posthead=native_post,
            head_limit=math.fsum(r['available_veh'] for r in heads)))
    head_error = math.fsum(w['model_head'] - w['actual_head'] for w in windows)
    merge_error = math.fsum(w['model_merge'] - w['actual_merge'] for w in windows)
    post_stock_error = native_post - model_post
    assert abs(merge_error - head_error - post_stock_error) < 1e-7
    clocks = [replay(buffer, rows, dt) for dt in (1, 5)]
    assert all(abs(c['head'] - 180) < 1e-7 for c in clocks)
    for p in (Path(__file__), ROOT / 'evaluation/controllers/lane_ramp_runtime.py',
              ROOT / 'evaluation/controllers/physical_ramp_boundary.py',
              ROOT / 'evaluation/controllers/multirate_ramp_boundary.py'):
        PINS[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    report = dict(status='complete_conditional_diagnosis', goal_complete=False,
        windows=windows, native_stock=native_stock,
        exact_error_identity=dict(merge_overprediction=merge_error,
            head_overprediction=head_error, posthead_inventory_underprediction=post_stock_error),
        clock_checks=clocks,
        clock_merge_delta_5_minus_1=clocks[1]['merge'] - clocks[0]['merge'],
        current_model=dict(posthead_speed_kmh=buffer.posthead_travel_speed_kmh,
            posthead_distance_m=buffer.length_m - buffer.head_position_m,
            posthead_travel_sec=(buffer.length_m - buffer.head_position_m) / buffer._posthead_speed_mps,
            receiving_node=state.lane_ramp_runtime.receiving_nodes[RAMP],
            physical_lane_mapping=state.lane_ramp_runtime.lane_coupling.get(RAMP)),
        caveats=['Error identity is accounting, not an independent causal split.',
            'Faster post-head drainage can itself release head service; do not fit both errors independently.',
            'Native per-lane stocks indicate asymmetry; aggregate mainline supply is equally divided between ramp lanes.',
            'No newly fitted parameter, full network forecast, native run, optimizer, AD or FZP scan.'],
        source_pins=PINS)
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p, h in PINS.items())
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')
    print(json.dumps({k: report[k] for k in ('status', 'exact_error_identity', 'clock_merge_delta_5_minus_1')}, ensure_ascii=False))
    print('clock_checks', [(c['step_sec'], c['head'], c['merge'], c['windows'][-1]['backlog']) for c in clocks])


if __name__ == '__main__':
    main()
