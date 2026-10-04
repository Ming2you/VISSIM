"""Local lane/boundary diagnosis from existing caches and native MER bundles.

No FZP scan, COM, calibration, forecast, or production configuration writes.
Five-second crossings are bracketed witnesses, not exact detector counts.
"""
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from evaluation.controllers import obs150_contract as oc
from evaluation.controllers import offramp_routing as routing

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REVIEW = HERE.parent
I = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'
CACHE = I / 'baseline_reproduction_20260929/cellwise_calibration/freeway_first/cohort_early'
PINS = {}


def read(path):
    data = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(data).hexdigest()
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)


def mean(values):
    return sum(values) / len(values) if values else None


def lane_rows(vehicles, bounds):
    groups = defaultdict(list)
    for vid, (cell, speed, pos, lane) in vehicles.items():
        if cell not in (10, 11, 12):
            continue
        assert bounds[cell] - 1e-4 <= pos <= bounds[cell + 1] + 1e-4
        groups[(cell, lane)].append((vid, speed, pos))
    rows = []
    for cell in (10, 11, 12):
        for lane in range(1, 5):
            vs = groups[cell, lane]
            slow = [v for v in vs if v[1] < 20.]
            rows.append(dict(cell=cell, lane=lane, n=len(vs), v_kmh=mean([v[1] for v in vs]),
                slow_n=len(slow), slow_first_offset_m=min((v[2]-bounds[cell] for v in slow), default=None),
                slow_last_gap_m=min((bounds[cell+1]-v[2] for v in slow), default=None),
                slow_within_first25m=sum(v[2] <= bounds[cell]+25 for v in slow)))
    return rows


def main():
    assert not (HERE / 'assessment.json').exists(), 'Preserve previous audit'
    manifest = read(REVIEW / 'retained10638/candidate_manifest.json')
    geometry = read(ROOT / manifest['sources']['geometry']['path'])
    assert PINS[str(ROOT / manifest['sources']['geometry']['path'])] == manifest['sources']['geometry']['sha256']
    bounds = geometry['bounds']['FW_E']
    runtime = read(REVIEW / 'entry10643/native_cohorts.json')['route_runtime']
    cache_cases = {}
    starts = {}
    for seed in (29, 43):
        for arm in ('none', 'vsl'):
            key = f's{seed}_{arm}'
            source = read(CACHE / (key + '_frames.json.gz'))
            assert source['fields'] == ['cell', 'speed_kmh', 'x_m', 'lane']
            frames = sorted((float(t), vs) for t, vs in source['frames'].items())
            starts[key] = frames[0][1]
            assert len(frames) == 151
            snapshots, crossings, strata = [], [], defaultdict(list)
            for t, vs in frames:
                rows = lane_rows(vs, bounds)
                snapshots.append(dict(time_sec=t, lanes=rows))
                lane2 = next(r for r in rows if r['cell'] == 11 and r['lane'] == 2)
                near = lane2['slow_within_first25m'] > 0
                for c in (10, 11, 12):
                    for lane in range(1, 5):
                        r = next(r for r in rows if r['cell'] == c and r['lane'] == lane)
                        strata[(near, c, lane)].append(r)
            for (ta, before), (tb, after) in zip(frames, frames[1:]):
                assert abs(tb - ta - 5) < 1e-6
                for vid in before.keys() & after.keys():
                    ca, va, xa, la = before[vid]
                    cb, vb, xb, lb = after[vid]
                    # Positions in this local region belong to native link2. Do not
                    # infer a trajectory through a connector or a missing snapshot.
                    if not (10 <= ca <= 12 and 10 <= cb <= 12):
                        continue
                    assert xb >= xa - 1e-4, (key, ta, vid, xa, xb)
                    for c in (11, 12):
                        if xa < bounds[c] <= xb:
                            crossings.append(dict(vehicle=vid, bracket=[ta, tb], boundary_cell=c,
                                lane_before=la, lane_after=lb, lane_unchanged_at_samples=la==lb,
                                v_before=va, v_after=vb))
            summary = []
            for (near, cell, lane), rows in sorted(strata.items()):
                n = sum(r['n'] for r in rows)
                summary.append(dict(cell11_lane2_slow_within_first25m=near, cell=cell, lane=lane,
                    samples=len(rows), vehicle_samples=n, mean_n=mean([r['n'] for r in rows]),
                    vehicle_weighted_v=sum((r['v_kmh'] or 0)*r['n'] for r in rows)/n if n else None))
            counts = {}
            for c in (11, 12):
                xs = [r for r in crossings if r['boundary_cell'] == c]
                counts[str(c)] = dict(total_bracketed=len(xs),
                    same_sample_lane=dict(Counter(str(r['lane_after']) for r in xs if r['lane_unchanged_at_samples'])),
                    different_sample_lane=dict(Counter(f"{r['lane_before']}->{r['lane_after']}" for r in xs if not r['lane_unchanged_at_samples'])))
            cache_cases[key] = dict(window_sec=[frames[0][0], frames[-1][0]], snapshots=snapshots,
                crossings=crossings, crossing_counts=counts, conditional_lane_summary=summary)
            print(key, 'BRACKETED', counts)
            print('C10L2_BY_NEAR_SLOW', [r for r in summary if r['cell']==10 and r['lane']==2])
        assert starts[f's{seed}_none'] == starts[f's{seed}_vsl'], 'Paired cache initial states differ'

    detectors, digest = oc.read_detector_csv(I / 'selected/obs150/obs150_detectors_v2.csv')
    PINS[str(I / 'selected/obs150/obs150_detectors_v2.csv')] = digest
    groups = oc.group_boundaries(detectors)
    specs = {
        '43_nc': (2250, 'D:/VISSIM_runs/20260929_seed43_observation2700/nc/decisions_sdmpc31_nc2700_s43'),
        '47_hold': (2700, 'D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47')}
    mer_cases = {}
    for key, (start, folder) in specs.items():
        snapshots, windows = [], []
        for t in range(start, start + 451, 150):
            raw = read(Path(folder) / f'state_{t:06d}.json')
            frame = read(Path(raw['lane_plant_observation']['directory']) / f'frame_{t:06d}.json')
            vs = {}
            for v in frame['vehicles']:
                if str(v[1]) in runtime['physical']:
                    road, x, c = routing._position(runtime, v[1], v[3])
                    if road == 'FW_E' and 10 <= c <= 12:
                        assert v[1] == 2, 'Local lane numbers must refer to one physical link'
                        vs[str(v[0])] = [c, v[4], x, v[2]]
            snapshots.append(dict(time_sec=t, lanes=lane_rows(vs, bounds)))
            if t == start:
                continue
            bundle = oc.load_bundle(raw)  # verifies MER chunks and frames using original pinned hashes
            window = oc.assign_window(bundle.obs, bundle.mer_rows)
            rows = []
            for ref in ('through:10682', 'off_entry:10682'):
                for det in groups[ref]:
                    if ref == 'through:10682':
                        assert det.link == 2 and abs(runtime['physical']['2'][1]+det.pos-bounds[12]) < 1e-3
                    entries = window.entries[det.dcp_no]
                    rows.append(dict(ref=ref, lane=det.lane, count=len(entries),
                        mean_entry_speed_kmh=mean([e.v_kmh for e in entries if e.v_kmh is not None]),
                        tails=window.tails[det.dcp_no],
                        events=[dict(vehicle=e.veh, t_entry=e.t_entry, v_kmh=e.v_kmh) for e in entries]))
            windows.append(dict(start_sec=t-150, end_sec=t, detectors=rows))
        mer_cases[key] = dict(snapshots=snapshots, windows=windows)
        print(key, 'MER', [(w['end_sec'],[(r['ref'],r['lane'],r['count'],round(r['mean_entry_speed_kmh'] or 0,2),r['tails']) for r in w['detectors']]) for w in windows])

    previous = read(REVIEW / 'entry10682/verification.json')
    for path, digest in previous['production_unchanged'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
    stop = Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')
    assert hashlib.sha256(stop.read_bytes()).hexdigest() == previous['stop_sha256']
    out = dict(status='completed_observational_boundary_audit', cache_cases=cache_cases, native_mer_cases=mer_cases,
        geometry_bounds_m={str(c):[bounds[c],bounds[c+1]] for c in (10,11,12)}, source_pins=PINS,
        production_unchanged=previous['production_unchanged'], stop_sha256=previous['stop_sha256'],
        new_forecasts=0, new_native=0, new_fzp_scans=0, calibration_performed=False,
        limitations=['Five-second common-ID crossing witnesses may miss vehicles crossing the whole local region between samples.',
        'Equal lanes at two samples do not rule out lane changes between them. Different lanes make crossing lane unknown.',
        '20km/h and first25m describe observed slow occupancy only; neither a calibrated queue-tail nor a causal threshold.',
        'Seed47 has only150s snapshots; MER provides actual boundary entries, not a continuous spatial queue trajectory.',
        'Archived5s caches and native obs150 runs are separately pinned; their events are not merged or assumed byte-identical.',
        'Future observations are retrospective diagnostics only; no autonomous model consumes them.'])
    (HERE / 'assessment.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('COMPLETE_NO_PRODUCTION_CHANGE')


if __name__ == '__main__':
    main()
