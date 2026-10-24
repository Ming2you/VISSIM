"""Isolate gap-input error with frozen head transfers, not an MPC forecast."""
import copy
import importlib.util
import json
import math
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('lane_receiving_assessment', HERE.parent/'assess.py')
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
from evaluation.controllers.physical_ramp_boundary import gap_acceptance_supply_vph


def invert_gap(rate, node):
    gap = lambda q: gap_acceptance_supply_vph(q, node['critical_gap_sec'], node['followup_sec'])
    assert 0 < rate < gap(0)
    lo, hi = 0., 20000.
    assert gap(hi) < rate
    for _ in range(60):
        mid = (lo+hi)/2
        if gap(mid) > rate:
            lo = mid
        else:
            hi = mid
    q = (lo+hi)/2
    assert abs(gap(q)-rate) < 1e-8
    return q


def assess():
    read, I, oc = local.read, local.I, local.oc
    audit = read(I/'closedloop_recorded2700_native_selected_sc1001_corrected47/analysis/ramp_response_audit.json')
    previous = read(HERE.parent/'assessment.json')
    manifest = read(local.ROOT/previous['configuration_authority']['manifest_path'])
    geometry = read(local.ROOT/manifest['sources']['geometry']['path'])
    assert local.PINS[str(local.ROOT/manifest['sources']['geometry']['path'])] == manifest['sources']['geometry']['sha256']
    cells = {c['cell']: c for c in geometry['cells'] if c['road'] == 'FW_E'}
    ramp = next(b for b in geometry['boundaries'] if b['id'] == 'RM_C10681')
    off = next(b for b in geometry['boundaries'] if b['connector'] == 10682)
    assert ramp['to_cell'] == 12 and off['from_cell'] == 11
    result = dict(status='conditional_input_diagnosis_not_gain_qualified', full_forecasts=0,
        new_native_runs=0, fitting=0, future_native_inputs=True, feedback_frozen=True,
        input_sha256=local.PINS, arms={}, measurement={})
    for name, arm in (('held_actual', 'hold'), ('selected', 'selected')):
        trace = read(I/'closedloop_recorded2700_select_check_trace10681_lane_receiving47_v2'/
                     (name+'_RM_C10681_trace.json.gz'))
        traced = read(I/'closedloop_recorded2700_select_check_trace10681_gap_inputs47'/
                      (name+'_RM_C10681_trace.json.gz'))
        old_result = read(I/'closedloop_recorded2700_select_check_trace10681_lane_receiving47_v2'/(name+'.json'))
        new_result = read(I/'closedloop_recorded2700_select_check_trace10681_gap_inputs47'/(name+'.json'))
        old_result.pop('wall_sec'); wall = new_result.pop('wall_sec')
        assert old_result == new_result
        stripped = copy.deepcopy(traced)
        states = {}
        for sample in stripped['lane_interval_receipts']:
            state = sample.pop('freeway_before')
            states[sample['arguments']['start_sec']] = state
        assert stripped == trace
        node = trace['lane_runtime']['receiving_node']
        assert trace['lane_runtime']['mainline_lane_mapping'] is None
        canonical = {r['start_sec']: r['available_veh'] for r in trace['resources']
                     if r['kind'] == 'physical_ramp_merge_canonical_receiving'}
        model_q = {}
        for sample in trace['lane_interval_receipts']:
            t = sample['arguments']['start_sec']
            budget = sample['arguments']['receiving_budget_veh']
            assert budget < canonical[t] and 'density_supply' not in node
            model_q[t] = invert_gap(budget/2*3600, node)
            state = states[t]
            assert not state['lane_group_plant'] and state['merge_cell'] == 12
            split = sum(v['ratio'] for v in state['offramp_splits'].values() if v['cell'] == 11)
            direct_q = state['density'][11]*state['speed'][11]*(1-split)
            assert abs(direct_q-model_q[t]) < 1e-8
        native_counts = {width: defaultdict(lambda: [0]*4) for width in (30, 150)}
        snapshots, native_windows = [], []
        for path in sorted(Path(p) for p in audit['input_sha256'] if arm in Path(p).parts):
            raw = read(path)
            assert local.PINS[str(path)] == audit['input_sha256'][str(path)]
            bundle = oc.load_bundle(raw)
            ds, _ = oc.read_detector_csv(bundle.obs['detector_config']['path'], bundle.obs['detector_config']['sha256'])
            assigned = oc.assign_window(bundle.obs, bundle.mer_rows)
            through = sorted((d for d in ds if d.boundary_ref == 'through:10682'), key=lambda d: d.lane)
            assert [d.lane for d in through] == [1, 2, 3, 4]
            assert all(d.orientation == 'at' and d.link == 2 for d in through)
            assert all(abs(d.pos-through[0].pos) < 1e-8 for d in through)
            assert off['from_pos_m'] < through[0].pos < ramp['to_pos_m']
            result['measurement'] = dict(boundary='through:10682', link=2, position_m=through[0].pos,
                ramp_merge_position_m=ramp['to_pos_m'], downstream_of_offramp=True,
                distance_upstream_of_merge_m=ramp['to_pos_m']-through[0].pos,
                lanes=4, definition='Measured through flow already excludes diverted vehicles; no second split factor.')
            end = raw['sim_sec']
            counts, tails = [], []
            assert assigned.lag_ok
            for d in through:
                entries = assigned.entries[d.dcp_no]
                tail = assigned.tails[d.dcp_no]
                assert len(entries)+tail == bundle.obs['detectors'][str(d.dcm_no)]
                counts.append(len(entries)+tail)
                tails.append(tail)
                for e in entries:
                    for width in (30, 150):
                        # Ordinals assign exact150s membership. A rounded event
                        # at the closing boundary belongs to its closing bin.
                        start = min(end-width, math.floor(e.t_entry/width)*width)
                        assert end-150 <= start < end
                        native_counts[width][start][d.lane-1] += 1
                for width in (30, 150):
                    # Validated missing MER tails lie in (end-1,end]; their
                    # bin is known even though individual times are unavailable.
                    native_counts[width][end-width][d.lane-1] += tail
            native_windows.append(dict(start_sec=end-150, flow_veh_h_by_lane=[v*24 for v in counts],
                validated_tail_counts_by_lane=tails))
            row = dict(time_sec=end, cells={})
            for i in (11, 12):
                cell = cells[i]
                vehicles = [v for v in bundle.frame_end['vehicles'] if v[1] == 2 and
                    cell['start_m'] <= v[3]+geometry['addresses']['2'][1] < cell['end_m']]
                n = len(vehicles)
                row['cells'][i] = dict(n=n, rho=n/cell['lane_km'],
                    speed=sum(v[4] for v in vehicles)/n if n else None,
                    rho_speed=sum(v[4] for v in vehicles)/cell['lane_km'],
                    lane_rho_speed=[sum(v[4] for v in vehicles if v[2] == j)/cell['length_km'] for j in (1, 2, 3, 4)])
            snapshots.append(row)
        grouped = {start: sum(q for t, q in model_q.items() if start <= t < start+150)/150
                   for start in (2700, 2850, 3000)}
        profiles = {'model_mean150': {t: grouped[math.floor(t/150)*150] for t in model_q}}
        for width in (150, 30):
            profiles['native_mean'+str(width)] = {
                t: sum(native_counts[width][math.floor(t/width)*width])*3600/width/4 for t in model_q}
        observed = previous['arms'][name]['actual']
        outcomes = {'model_instantaneous': previous['arms'][name]['posthead']['native_head']}
        for key, profile in profiles.items():
            conditional = copy.deepcopy(trace)
            for sample in conditional['lane_interval_receipts']:
                t = sample['arguments']['start_sec']
                amount = min(canonical[t], 2*gap_acceptance_supply_vph(profile[t],
                    node['critical_gap_sec'], node['followup_sec'])/3600)
                sample['arguments']['receiving_budget_veh'] = amount
                for lane in sample['receipt']['lane_receipts']:
                    lane['receiving_budget_veh'] = amount/2
            outcomes[key] = local.posthead_replay(conditional, observed, 'native_head')
            outcomes[key]['receiving_input'] = key
        result['arms'][name] = dict(node=node, native_windows=native_windows, native_snapshots=snapshots,
            model_conflict_vph_per_lane_by_second=model_q, mean_model_conflict_by150=grouped,
            native_conflict_counts_by30=dict(native_counts[30]), conditional=outcomes,
            native_actual_merges=[w['total_merge'] for w in observed['windows']],
            native_final_posthead_stock=observed['windows'][-1]['end_stock']['post'],
            full_output_exact=True, original_receipts_exact=True, full_forecast_wall_sec=wall,
            model_states_at_native_frame={t: states[t] for t in (2700, 2850, 3000)},
            model_means_by150={start: {i: dict(
                density=sum(s['density'][i] for t,s in states.items() if start<=t<start+150)/150,
                speed=sum(s['speed'][i] for t,s in states.items() if start<=t<start+150)/150,
                rho_speed=sum(s['density'][i]*s['speed'][i] for t,s in states.items() if start<=t<start+150)/150)
                for i in (11,12)} for start in (2700,2850,3000)})
    result['full_forecasts'] = 2
    result['limitations'] = [
        'Instantaneous inferred q is valid here because the gap bound is active and no other receiving clipping or lane mapping applies.',
        'The detector is147.51m before the merge; interval travel/storage effects remain. Measured flow is not an instantaneous same-time conflict state.',
        'Native150/30s inputs are conditional future truth. They do not qualify an autonomous candidate, changed FD, control ranking or full-network TTT.',
        'Snapshot rho*v is a spatial estimate; measured through counts are a temporal flux, not interchangeable at each instant.',
        'Native150s counts include validated last-second MER tails.30s binning remains sensitive to rounded internal boundary events.',
        'Lane-specific native q is reported but not substituted into an unvalidated new lane-coupling law.']
    return result


if __name__ == '__main__':
    result = assess()
    (HERE/'assessment.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({arm: {k: dict(merge=v['merge'], by_window=[sum(w['merge_by_lane']) for w in v['windows']],
        final_post=v['windows'][-1]['post_stock_by_lane']) for k, v in row['conditional'].items()}
        for arm, row in result['arms'].items()}, indent=2))
