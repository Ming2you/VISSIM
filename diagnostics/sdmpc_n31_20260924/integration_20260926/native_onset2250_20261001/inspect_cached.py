"""Closed, cached onset evidence only. No COM, FZP scan, forecast or calibration."""
import bisect
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from evaluation.controllers import obs150_contract as oc

HERE = Path(__file__).resolve().parent
OUT = HERE/'analysis'
I = HERE.parent
RUNS = Path('D:/VISSIM_runs/20261001_onset2250_s29')
OLD = Path('D:/VISSIM_runs/20260930_expanded036_s29_9000_r2/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
PINS = {}


def read(path):
    data = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(data).hexdigest()
    return json.loads(data)


def save(name, value):
    (OUT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def table(name, rows):
    with (OUT/name).open('w', encoding='utf-8-sig', newline='') as stream:
        w = csv.DictWriter(stream, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def decisions(arm):
    return RUNS/arm/f'decisions_sdmpc31_g_2250_{arm}_s29'


def main():
    assert not (OUT/'cached_mechanism.json').exists(), 'Preserve completed audit'
    assert not (RUNS/'STOP').exists()
    summary = read(OUT/'summary.json')
    audit = read(OUT/'ramp_response_audit.json')
    guard = read(OUT/'paired_scope_guard_verification.json')
    assert PINS[str(OUT/'summary.json')] == guard['original_summary_sha256']
    assert summary['counterfactual_valid'] is False
    assert summary['paired_prefix_exact'] and summary['common_start_vehicle_records_exact']
    assert audit['native_comparison_scope'] == 'within_four_new_replays_only'
    arms = tuple(audit['arms'])
    geometry = read(I/'selected/port_gain/geometry.json')
    addresses = geometry['addresses']
    membership = read(I/'selected/scenario/control_area_membership_213a5d.json')
    inside = set(map(str, membership['inside_links']))
    cells = {road: sorted([c for c in geometry['cells'] if c['road'] == road], key=lambda c: c['cell'])
             for road in ('FW_E', 'FW_W')}
    ends = {road: [c['end_m'] for c in cc] for road, cc in cells.items()}
    areas, cell_rows, flows = {}, [], []
    for arm in arms:
        metrics = read(OUT/arm/'area_metrics.json')
        assert summary['arms'][arm]['native_execution_passed']
        grouped = defaultdict(float)
        for link, row in metrics['physical_link_residence'].items():
            if link in inside:
                group = addresses[link][0] if link in addresses else 'other_Omega'
                grouped[group] += row['ttt_veh_h']
        assert abs(sum(grouped.values())-summary['arms'][arm]['TTT_0_2700_veh_h']) < 1e-7
        areas[arm] = dict(grouped)
        for end in range(2250, 2701, 150):
            raw = read(decisions(arm)/f'state_{end:06d}.json')
            records = raw['vehicle_records']
            assert records['complete'] and records['unobservable_count'] == 0
            assert records['record_count'] == len(records['records'])
            bins = defaultdict(list)
            for v in records['records']:
                link = str(v['link_no'])
                if link not in addresses:
                    continue
                road, offset = addresses[link]
                pos = offset+v['position_m']
                cell = min(bisect.bisect_right(ends[road], pos), len(ends[road])-1)
                bins[road, cell].append(v['speed_kph'])
            for road, cc in cells.items():
                for c in cc:
                    vv = bins[road, c['cell']]
                    cell_rows.append(dict(arm=arm, sim_sec=end, road=road, cell=c['cell'],
                        vehicles=len(vv), speed_kph=sum(vv)/len(vv) if vv else None))
            if end == 2250:
                continue
            obs = raw[oc.RAW_STATE_KEY]
            detectors, _ = oc.read_detector_csv(obs['detector_config']['path'], obs['detector_config']['sha256'])
            bundle = oc.load_bundle(raw)
            boundaries = oc.evaluate_boundaries(obs, detectors, bundle.frame_end, bundle.frame_start, bundle.err_rows)
            flows.extend(dict(arm=arm, start_sec=end-150, end_sec=end, boundary=ref, cross=value.cross)
                         for ref, value in boundaries.items()
                         if ref.startswith(('source:', 'terminal:', 'through:', 'off_entry:')))
    area_delta = {a: {g: areas[a][g]-areas['held_actual'][g] for g in areas[a]} for a in arms}
    for a in arms:
        assert abs(sum(area_delta[a].values())-summary['comparisons'][a]['delta_TTT_veh_h']) < 1e-7

    # Do not excuse the failed raw-prefix reproduction. Inspect only the inputs
    # that can explain whether the previously frozen forecast remains comparable.
    history = []
    for end in range(150, 2251, 150):
        old = read(OLD/f'state_{end:06d}.json')
        new = read(decisions('held_actual')/f'state_{end:06d}.json')
        a, b = oc.load_bundle(old), oc.load_bundle(new)
        frame_diff = {}
        for key in ('frame_start', 'frame_end'):
            fa, fb = getattr(a, key), getattr(b, key)
            frame_diff[key] = [k for k in fa if k != 'run_id' and fa[k] != fb[k]]
        ignored = {'sim_period_sec', 'network_path', 'run_provenance', 'obs150', 'lane_plant_observation'}
        history.append(dict(end_sec=end,
            raw_physical_differing_fields=[k for k in old if k not in ignored and old[k] != new[k]],
            obs_differing_fields=[k for k in old['obs150'] if old['obs150'][k] != new['obs150'][k]],
            mer_rows_exact=a.mer_rows == b.mer_rows, err_rows_exact=a.err_rows == b.err_rows,
            frame_physical_differences=frame_diff))
    report = dict(scope='Four new native replays only; original reproduction failure retained',
        area_delta_veh_h=area_delta, areas_0_2700_veh_h=areas, history_checks=history,
        original_summary_unchanged=True, original_reproduction_qualified=False,
        prediction_full_history_equivalence_qualified=False,
        limitation='Raw/150s bundles are checked; head-history and VSL-cohort initialization were not rerun here. Frozen forecast comparisons remain conditional.',
        new_native_runs=0, new_forecasts=0, fzp_rescans=0, calibration=0,
        input_sha256=PINS)
    assert hashlib.sha256((OUT/'summary.json').read_bytes()).hexdigest() == guard['original_summary_sha256']
    table('mainline_snapshots.csv', cell_rows)
    table('mainline_boundary_counts.csv', flows)
    save('cached_mechanism.json', report)
    print(json.dumps(dict(area_delta_veh_h=area_delta,
        history_not_exact=[r for r in history if r['raw_physical_differing_fields'] or not r['mer_rows_exact']
                          or not r['err_rows_exact'] or any(r['frame_physical_differences'].values())])))


if __name__ == '__main__':
    main()
