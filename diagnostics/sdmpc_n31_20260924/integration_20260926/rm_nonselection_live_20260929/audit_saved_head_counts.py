"""Screen saved obs150 counts against the head ceiling; no FZP or live reads."""
from pathlib import Path
import collections
import csv
import hashlib
import json

HERE = Path(__file__).resolve().parent
RUNS = {
    'nc_seed29': Path('D:/VISSIM_runs/20260927_sd31_wiring9000/nc/decisions_sdmpc31_nc9000_s29'),
    'rm_hold_seed47': Path('D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47'),
}


def main(*, runs=None, output=None):
    runs = RUNS if runs is None else runs
    output = HERE/'saved_head_ceiling_screen.json' if output is None else Path(output)
    assert not output.exists(), 'Preserve completed screening'
    pins = {}

    def read(path):
        raw = path.read_bytes()
        pins[str(path)] = hashlib.sha256(raw).hexdigest()
        return raw

    detector_path = HERE.parent/'selected/obs150/obs150_detectors_v2.csv'
    detectors = [r for r in csv.DictReader(read(detector_path).decode('utf-8-sig').splitlines())
                 if r['role'] == 'meter_head']
    assert len(detectors) == 10
    records = []; skipped = []
    for label, folder in runs.items():
        paths = sorted(folder.glob('state_*.json'))
        assert paths
        previous = None
        for path in paths:
            state = json.loads(read(path)); obs = state['obs150']
            assert obs['detector_config']['sha256'] == pins[str(detector_path)]
            if obs['window'] is None:
                skipped.append(dict(run=label, path=str(path), reason='initial observation has no completed window'))
                previous = obs
                continue
            end = obs['window']['end_s']; start = obs['window']['start_s']
            if previous is None or end-start != 150 or previous['sim_sec'] != start:
                skipped.append(dict(run=label, path=str(path), reason='no adjacent complete150s predecessor'))
                previous = obs
                continue
            commands = list(csv.DictReader(read(folder/f'action_{int(start):06d}.csv').decode('utf-8-sig').splitlines()))
            greens = {r['id']: float(r['green_sec']) for r in commands if r['kind'] == 'ramp_meter'}
            for d in detectors:
                key = d['dcp_no']; count = obs['detectors'][key]
                assert isinstance(count, (int, float)) and count >= 0
                assert count == obs['detectors_cum'][key]-previous['detectors_cum'][key]
                green = greens['RM_C'+d['link']]
                if green < 9:
                    continue
                if label == 'nc_seed29':
                    assert green == 10
                # The east active table has g9=g10=4.2 per lane/cycle.
                # West g9 differs: screen only full-open west g10.
                east = int(d['link']) in (10639,10681,10490,10484)
                if not east and green != 10:
                    continue
                ceiling = 4.2*(end-start)/10
                records.append(dict(run=label, start_sec=start, end_sec=end,
                    connector=int(d['link']), lane=int(d['lane']), green_sec=green,
                    detector=int(key), count=count, model_ceiling=ceiling,
                    exceeds=count>ceiling+1e-9, excess_veh=count-ceiling))
            previous = obs
    grouped = collections.defaultdict(list)
    for r in records:
        grouped[(r['run'],r['connector'],r['lane'],r['green_sec'])].append(r)
    summary = []
    for (label,con,lane,green), rows in sorted(grouped.items()):
        peak = max(rows,key=lambda r:r['count'])
        summary.append(dict(run=label,connector=con,lane=lane,green_sec=green,
            windows=len(rows),exceeding_windows=sum(r['exceeds'] for r in rows),
            maximum_count=peak['count'],peak_start_sec=peak['start_sec'],
            model_ceiling=peak['model_ceiling']))
    report = dict(scope='Saved completed-run obs150 detector-count screening only',
        source_sha256=pins, summary=summary, windows=records, skipped_initial_windows=skipped,
        limitations=[
            'CSV records commanded green, not a new LDP execution certification.',
            'Counts are detector entry events. Full MER event integrity/vehicle deduplication is required before treating any exceedance as a physical contradiction.',
            'A count below a ceiling cannot identify that ceiling: demand, queue and downstream receiving may limit throughput.',
            'A single integer count exceeding a fluid average slightly need not invalidate an effective mean service law.',
            'This is not a same-initial-state causal comparison of green9 versus10.',
            'No future observation is supplied to a model. No calibration or prediction is performed.'
        ], fzp_scans=0, live_state_reads=0, new_native_runs=0)
    with output.open('x',encoding='utf-8') as f:
        json.dump(report,f,ensure_ascii=False,indent=2)
    print(json.dumps(dict(output=str(output),windows=len(records),summary=summary),ensure_ascii=False))


if __name__ == '__main__':
    main()
