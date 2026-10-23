"""New recorded interaction-state/acceleration evidence; no simulation or fit."""
import collections
import datetime
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import sys

A = Path(__file__).resolve().parent
H = A.parent
O = A / 'interaction_response'
ROOT = Path('D:/VISSIM_packages/vsl_multizone355_20261015')
OLD = Path('E:/VISSIM_analysis/20261011_vsl_response349/causal_off2250_analysis_v2/native_analysis')
RUNS = {
    'hold': Path('E:/VISSIM_runs/20261011_vsl349_off2250_s29/hold'),
    'single90': Path('E:/VISSIM_runs/20261011_vsl349_off2250_s29/vsl90'),
    'selected': Path('D:/VISSIM_runs/20261016_vsl_multizone2250_repaired_s29/selected'),
}
NAMES = {'hold': 'hold', 'single90': 'vsl90', 'selected': 'selected'}
PINS = {}


def read(path):
    blob = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(blob).hexdigest()
    return json.loads(blob)


def save(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')


def main():
    assert not O.exists() and not (A / 'STOP').exists()
    for path in (OLD / 'runtime_closure.json', H / 'native_analysis_repaired_20261016/runtime_closure.json'):
        doc = read(path)
        assert doc['all_owned_processes_closed'] and doc['owner_exit_code'] == 0 and doc['normal_native_end_sec'] == 2700
    for path in (OLD / 'hold/execution.json', OLD / 'vsl90/execution.json', H / 'native_analysis_repaired_20261016/selected/execution.json'):
        doc = read(path)
        assert doc['native_execution_passed']
    # The old joint Carlson fit is evidence against blindly repeating that trial.
    old_fit = read(ROOT / 'diagnostics/repin_v3c3_review_20261001/vsl_fd253/verified/assessment.json')
    assert not old_fit['adopted']
    sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
    from evaluation.controllers import offramp_routing as route
    contract = read(ROOT / 'diagnostics/repin_v3c3_review_20261001/unrouted10646/route_contract.json')
    runtime = route.compile_inventory(contract, read(ROOT / contract['mapping']['path']))
    bounds = runtime['bounds']['FW_E']
    O.mkdir()
    save(O / 'protocol.json', dict(
        question='Does a desired-speed change directly alter acceleration of already constrained vehicles, and is downstream loss caused by available sending or blocked receiving?',
        scope='Completed seed29 hold/single90/twozone90; physical cells14..25; 2240.1..2695.1 at5s. New interaction/acceleration fields, not a repetition of TTT integration.',
        budget=dict(new_native=0, forecasts=0, fits=0, fzp_streams=3),
        fields=['time', 'vehicle', 'cell', 'lane', 'chain_m', 'speed_kph', 'desired_kph', 'acceleration_m_s2', 'interaction', 'target_type', 'target_number', 'lane_change', 'destination_lane'],
        interpretation='Native states are literal labels. Matching a vehicle across policies alone does not hold its leader or gap fixed. Later observed states are never rollout inputs. No acceleration coefficient or VSL gain is fitted.',
        reference='https://cgi.ptvgroup.com/vision-help/VISSIM_11_ENG/Content/9_SimulationundTest/Fz-Interaktionszustand.htm',
        earlier_fd_fit=dict(path=str(ROOT / 'diagnostics/repin_v3c3_review_20261001/vsl_fd253/verified/assessment.json'), adopted=False),
        source_pins=dict(PINS), created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    save(O / 'launch.json', dict(pid=os.getpid(), command=sys.argv, started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    counts = {}
    for case, run in RUNS.items():
        source = run / f'vissim_eval/sdmpc31_g_2250_{NAMES[case]}_s29_001.fzp'
        stat = (source.stat().st_size, source.stat().st_mtime_ns)
        digest = hashlib.sha256()
        rows = []
        header = None
        labels = collections.Counter()
        source_rows = 0
        offgrid = 0
        with source.open('rb') as stream:
            for line in stream:
                digest.update(line)
                if line.startswith(b'$VEHICLE:'):
                    header = {v: i for i, v in enumerate(line.strip().split(b':', 1)[1].split(b';'))}
                    assert all(k in header for k in (b'SIMSEC', b'NO', b'LANE\\LINK\\NO', b'LANE\\INDEX', b'POS', b'SPEED', b'DESSPEED', b'ACCELERATION', b'INTERACTSTATE', b'INTERACTTARGTYPE', b'INTERACTTARGNO', b'LNCHG', b'DESTLANE'))
                    assert header[b'SIMSEC'] == 0
                    continue
                if header is None or not line.strip() or line.startswith((b'*', b'$')):
                    continue
                source_rows += 1
                t = float(line.split(b';', 1)[0])
                if not 2240 <= t < 2700:
                    continue
                tick = round((t - .1) / 5)
                if abs(t - (tick * 5 + .1)) > 1e-6:
                    offgrid += 1
                    continue
                fields = line.strip().split(b';')
                link = fields[header[b'LANE\\LINK\\NO']].decode('ascii')
                if link not in runtime['physical']:
                    continue
                road, offset = runtime['physical'][link]
                position = offset + float(fields[header[b'POS']])
                if road != 'FW_E' or not bounds[14] <= position < bounds[26]:
                    continue
                _, _, cell = route._position(runtime, link, float(fields[header[b'POS']]))
                number = lambda key: float(fields[header[key]])
                text = lambda key: fields[header[key]].decode('ascii')
                row = [t, int(fields[header[b'NO']]), cell, int(fields[header[b'LANE\\INDEX']]), position,
                       number(b'SPEED'), number(b'DESSPEED'), number(b'ACCELERATION'), text(b'INTERACTSTATE'),
                       text(b'INTERACTTARGTYPE'), text(b'INTERACTTARGNO'), text(b'LNCHG'), text(b'DESTLANE')]
                assert all(math.isfinite(v) for v in row[:8])
                assert row[5] >= 0 and row[6] > 0
                rows.append(row)
                labels[row[8]] += 1
        assert (source.stat().st_size, source.stat().st_mtime_ns) == stat
        assert len({(r[0], r[1]) for r in rows}) == len(rows)
        assert len({r[0] for r in rows}) == 92
        PINS[str(source)] = digest.hexdigest()
        if case == 'hold':
            previous = read(A / 'refine15_calibration/native_hold_cells.json')
            assert previous['source_pins'][str(source)] == PINS[str(source)]
        payload = dict(case=case, columns=read(O / 'protocol.json')['fields'], rows=rows,
                       bounds_m=bounds, source=str(source), sha256=PINS[str(source)])
        output = O / (case + '_records.json.gz')
        output.write_bytes(gzip.compress(json.dumps(payload, allow_nan=False).encode('utf8')))
        counts[case] = dict(records=len(rows), frames=92, interaction_counts=dict(labels),
                            source_rows=source_rows, offgrid_terminal_rows_excluded=offgrid,
                            source_sha256=PINS[str(source)], output_sha256=hashlib.sha256(output.read_bytes()).hexdigest())
        save(O / 'progress.json', counts)
        print('EXTRACTED', case, json.dumps(counts[case]), flush=True)
    save(O / 'completion.json', dict(status='complete_new_interaction_measurement', cases=counts,
        new_native=0, new_forecasts=0, new_fits=0, new_fzp_streams=3, ttt_reanalysis=0,
        source_pins=PINS, script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))


if __name__ == '__main__':
    try:
        main()
    except BaseException as exc:
        if O.is_dir():
            import traceback
            save(O / 'failure.json', dict(error=repr(exc), traceback=traceback.format_exc()))
        raise
