"""Locate saved current-baseline arrival errors using existing native frames."""
import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from evaluation.controllers import offramp_routing as routing

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
I = ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
PINS = {}


def read(path):
    data = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(data).hexdigest()
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)


def mean(values):
    return sum(values)/len(values) if values else None


def main():
    assert not (HERE/'spatial.json').exists()
    evidence = read(HERE/'assessment.json')
    runtime = read(HERE.parent/'entry10643/native_cohorts.json')['route_runtime']
    cases = {}
    specs = {
        '43_nc': ('D:/VISSIM_runs/20260929_seed43_observation2700/nc/decisions_sdmpc31_nc2700_s43',
                  'closedloop_recorded2250_lever450_trace10681_retained43'),
        '47_hold': ('D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47',
                    'closedloop_recorded2700_select_check_trace10681_entry10643')}
    for name, (folder, model) in specs.items():
        trace = read(I/model/'held_actual_RM_C10681_trace.json.gz')
        diagnostics = trace['mainline_diagnostics']
        rows = []
        for snapshot in diagnostics['initial_and_block_states']:
            t = int(snapshot['time_sec'])
            raw = read(Path(folder)/f'state_{t:06d}.json')
            frame = read(Path(raw['lane_plant_observation']['directory'])/f'frame_{t:06d}.json')
            cells = defaultdict(list)
            for v in frame['vehicles']:
                if str(v[1]) not in runtime['physical']:
                    continue
                road, pos, cell = routing._position(runtime, v[1], v[3])
                if road == 'FW_E' and 8 <= cell <= 12:
                    cells[cell].append(v)
            for cell in range(8, 13):
                vehicles = cells[cell]
                lanes = defaultdict(list)
                for v in vehicles:
                    lanes[int(v[2])].append(v)
                rows.append(dict(time_sec=t, cell=cell, native_n=len(vehicles),
                    native_mean_speed=mean([v[4] for v in vehicles]), model_speed=snapshot['speed'][cell],
                    native_known_10682_n=sum(v[6:8] == [1130., 3.] for v in vehicles),
                    by_native_lane={str(lane):dict(count=len(vs), mean_speed=mean([v[4] for v in vs]),
                        known10682_count=sum(v[6:8] == [1130.,3.] for v in vs)) for lane,vs in sorted(lanes.items())}))
        initial = [row for row in rows if row['time_sec'] == evidence['cases'][name]['start_sec']]
        assert max(abs(row['native_mean_speed']-row['model_speed']) for row in initial) < 1e-7
        case = evidence['cases'][name]
        before = case['current_baseline_port']
        native = case['native_port']
        entry_error = before['entry']-native['entry']
        stock_error = before['final_stock']-native['final_stock']
        drain_error = before['drain']-native['drain']
        assert abs(drain_error-(entry_error-stock_error)) < 1e-7
        cases[name] = dict(model='current retained10638 baseline', rows=rows,
            boundary_balance_error_model_minus_native=dict(entry=entry_error,drain=drain_error,final_stock=stock_error),
            initial_speed_matches_native=True)
        print(name, 'CURRENT_BASELINE_BALANCE', cases[name]['boundary_balance_error_model_minus_native'])
        print('END', [(r['cell'],r['native_n'],round(r['native_mean_speed'],3),round(r['model_speed'],3))
                      for r in rows if r['time_sec']==case['end_sec']])
    (HERE/'spatial.json').write_text(json.dumps(dict(status='completed_current_baseline_spatial_check',
        cases=cases,source_pins=PINS,new_native=0,new_fzp_scans=0,new_forecasts=0,
        limitations=['Snapshot speeds and retained cohorts locate an error; they do not isolate merge, anticipation or lane-access causes.',
                     'Native lane means aggregate physical links within the same reviewed mainline cell.']),
        ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
